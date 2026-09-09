"""LOCAL ONLY static/source-shape checks for
contracts/probe/storage_runtime_probe.py.

These checks verify Python syntax, ASCII/LF source-shape discipline,
isolation from contracts/governance_fork.py, and the expected ABI shape.

They do NOT and CANNOT prove anything about live GenVM runtime storage
behavior -- that is exactly what this probe exists to determine once it
is deployed and exercised manually in Studio. A clean pass here means
only "this file is syntactically valid and shaped as intended locally";
it says nothing about whether any of Probes A-E actually succeed against
the real pinned runtime. Do not treat a pass here as runtime evidence.
"""

from __future__ import annotations
import ast
import hashlib
import pathlib
import sys


PROBE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "contracts" / "probe" / "storage_runtime_probe.py"
)
PROD_PATH = pathlib.Path(__file__).resolve().parents[1] / "contracts" / "governance_fork.py"


def _read():
    raw = PROBE_PATH.read_bytes()
    return raw.decode("ascii"), raw


def check_python_syntax(source):
    try:
        ast.parse(source)
        return True, "ast.parse ok"
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"


def check_ascii_only(raw):
    for i, b in enumerate(raw):
        if b > 127:
            return False, f"non-ASCII byte 0x{b:02x} at offset {i}"
    return True, f"{len(raw)} bytes, ASCII-only"


def check_lf_line_endings(raw):
    if b"\r\n" in raw:
        return False, "CRLF sequences present"
    if b"\r" in raw:
        return False, "bare CR present"
    return True, "LF only"


def _strip_comments(source):
    # Naive but sufficient for this controlled source: no string literal
    # in this file contains a "#". Used only to distinguish prose in
    # comments/docstrings (which may legitimately name governance_fork.py
    # for documentation purposes) from actual code references.
    lines = []
    for line in source.split("\n"):
        idx = line.find("#")
        lines.append(line if idx < 0 else line[:idx])
    return "\n".join(lines)


def check_isolated_from_production_contract(source):
    # Checks CODE, not comments/docstrings -- this file's own header
    # comment intentionally names governance_fork.py to document why the
    # probe exists, which is not an isolation violation. An actual code
    # reference (import, attribute access, string literal used as a
    # path, etc.) outside of comments would be.
    code_only = _strip_comments(source)
    tree = ast.parse(source)
    docstring_texts = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                docstring_texts.add(doc)
    # Remove any docstring content from the code-only text before
    # searching, since docstrings are prose, not executable references.
    for doc in docstring_texts:
        code_only = code_only.replace(doc, "")
    if "governance_fork" in code_only:
        return False, "code references governance_fork -- probe must stay isolated"
    return True, "no code reference to governance_fork.py (comments/docstrings may name it)"


def check_no_import_of_governance_fork(source):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "governance_fork" in alias.name:
                    return False, f"import of {alias.name} found"
        if isinstance(node, ast.ImportFrom):
            if node.module and "governance_fork" in node.module:
                return False, f"import from {node.module} found"
    return True, "no import of governance_fork"


def check_each_hypothesis_isolated_no_fallback(source):
    # Probe B must not have a same-transaction fallback (no "if key not
    # in self.index" guard before the append, no try/except) -- a
    # fallback would mask a genuine autovivification failure. Checked
    # structurally via the AST (ast.Try, ast.If nodes), not by searching
    # the method's source text, since the method's own explanatory
    # comment prose legitimately discusses "no try/except" without that
    # being a code-level try/except statement.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "probe_b_append_fresh_key":
            for child in ast.walk(node):
                if isinstance(child, ast.Try):
                    return False, "probe_b_append_fresh_key contains a try/except -- must be a bare append"
                if isinstance(child, ast.If):
                    return False, "probe_b_append_fresh_key contains a conditional guard -- must be a bare append"
            code_only = _strip_comments(ast.get_source_segment(source, node) or "")
            if "self.index[key].append(value)" not in code_only:
                return False, "probe_b_append_fresh_key does not contain the expected bare append call"
            return True, "probe_b_append_fresh_key is a bare, unguarded append (verified via AST: no Try/If nodes)"
    return False, "probe_b_append_fresh_key not found"


def check_negative_control_present_and_isolated(source):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "probe_x_negative_control_inmem_allocate":
            src = ast.get_source_segment(source, node) or ""
            if "gl.storage.inmem_allocate(DynArray[u256])" not in src:
                return False, "negative control does not reproduce the known-failing pattern"
            return True, "negative control present, reproduces gl.storage.inmem_allocate(DynArray[u256])"
    return False, "probe_x_negative_control_inmem_allocate not found"


def extract_abi(source):
    tree = ast.parse(source)
    writes = []
    views = []
    contract_cls = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Contract":
            contract_cls = node
            break
    assert contract_cls is not None

    def deco_matches(decorators, want):
        for d in decorators:
            path = []
            cur = d
            while isinstance(cur, ast.Attribute):
                path.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                path.append(cur.id)
            path.reverse()
            if tuple(path) == want:
                return True
        return False

    for item in contract_cls.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        if item.name.startswith("__"):
            continue
        if deco_matches(item.decorator_list, ("gl", "public", "view")):
            views.append(item.name)
        elif deco_matches(item.decorator_list, ("gl", "public", "write")):
            writes.append(item.name)
    return writes, views


def check_abi_shape(source):
    writes, views = extract_abi(source)
    expected_writes = [
        "probe_a_create_and_append",
        "probe_b_append_fresh_key",
        "probe_c_transient_hash",
        "probe_d_assign_list",
        "probe_x_negative_control_inmem_allocate",
    ]
    expected_views = [
        "probe_a_read",
        "probe_b_read",
        "probe_c_read",
        "probe_d_read",
        "probe_e_return_list",
    ]
    ok = sorted(writes) == sorted(expected_writes) and sorted(views) == sorted(expected_views)
    detail = f"writes={writes}, views={views}"
    return ok, detail


def main():
    source, raw = _read()
    sha = hashlib.sha256(raw).hexdigest()
    print(f"probe contract: {PROBE_PATH}")
    print(f"sha256:         {sha}")
    print(f"bytes:          {len(raw)}")
    print(f"lines:          {source.count(chr(10)) + (0 if source.endswith(chr(10)) else 1)}")
    print()

    checks = [
        ("python syntax", check_python_syntax(source)),
        ("ascii only", check_ascii_only(raw)),
        ("lf line endings", check_lf_line_endings(raw)),
        ("isolated from governance_fork.py (text)", check_isolated_from_production_contract(source)),
        ("no import of governance_fork", check_no_import_of_governance_fork(source)),
        ("probe B has no same-transaction fallback", check_each_hypothesis_isolated_no_fallback(source)),
        ("negative control present and isolated", check_negative_control_present_and_isolated(source)),
        ("abi shape", check_abi_shape(source)),
    ]
    passed = 0
    failed = 0
    for name, (ok, detail) in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")
        if ok:
            passed += 1
        else:
            failed += 1
    print()
    print(f"summary: {passed}/{passed + failed} checks passed")
    print()
    print("NOTE: LOCAL ONLY. These are static/source-shape checks. They do")
    print("NOT and CANNOT prove GenVM runtime storage behavior -- that is")
    print("exactly the open question this probe exists to answer once it")
    print("is deployed and exercised manually in Studio. Schema acceptance")
    print("is not runtime success; only a live Execution Result settles")
    print("each hypothesis.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
