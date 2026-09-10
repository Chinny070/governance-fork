"""LOCAL ONLY static / source-shape checks for
contracts/probe/semantic_adjudication_probe.py.

Verifies Python syntax, ASCII/LF discipline, isolation from
contracts/governance_fork.py, the expected ABI shape, that the probe
actually exercises BOTH candidate semantic primitives plus exec_prompt,
and that it uses no banned pattern (web retrieval, GEN value/transfer,
dataclass-typed public inputs).

These checks do NOT and CANNOT prove anything about live GenVM semantic
behavior -- consensus over LLM output, response_format="json" return
shape, Undetermined frequency, or 49 KB-prompt viability. That is exactly
what this probe exists to determine once it is deployed and exercised
manually in Studio (see docs/STAGE_7_SEMANTIC_PROBE_RUNBOOK.md). Stage 7
itself is NOT implemented.
"""

from __future__ import annotations
import ast
import hashlib
import pathlib
import sys


PROBE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "contracts" / "probe" / "semantic_adjudication_probe.py"
)
PROD_PATH = pathlib.Path(__file__).resolve().parents[1] / "contracts" / "governance_fork.py"


def _read():
    raw = PROBE_PATH.read_bytes()
    return raw.decode("ascii"), raw


def _strip_comments(source):
    out = []
    for line in source.split("\n"):
        i = line.find("#")
        out.append(line if i < 0 else line[:i])
    return "\n".join(out)


def _code_only(source):
    code = _strip_comments(source)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            d = ast.get_docstring(node, clean=False)
            if d:
                code = code.replace(d, "")
    return code


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
        return False, "CRLF present"
    if b"\r" in raw:
        return False, "bare CR present"
    return True, "LF only"


def check_isolated_from_production_contract(source):
    code = _code_only(source)
    if "governance_fork" in code:
        return False, "code references governance_fork -- probe must stay isolated"
    return True, "no code reference to governance_fork.py (comments/docstrings may name it)"


def check_no_import_of_governance_fork(source):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if "governance_fork" in a.name:
                    return False, f"import of {a.name}"
        if isinstance(node, ast.ImportFrom):
            if node.module and "governance_fork" in node.module:
                return False, f"import from {node.module}"
    return True, "no import of governance_fork"


def check_uses_both_candidate_primitives(source):
    code = _code_only(source)
    need = [
        "gl.nondet.exec_prompt(",
        "gl.eq_principle.prompt_non_comparative(",
        "gl.eq_principle.prompt_comparative(",
        "gl.eq_principle.strict_eq(",
    ]
    missing = [n for n in need if n not in code]
    if missing:
        return False, "missing required primitive call(s): " + ", ".join(missing)
    return True, "exec_prompt + prompt_non_comparative + prompt_comparative + strict_eq all present"


def check_no_banned_patterns(source):
    code = _code_only(source)
    banned = [
        ("gl.nondet.web.render(", "web render (probe feeds in-contract text only)"),
        ("web.get(", "web get"),
        ("transfer(", "GEN transfer"),
        ("gl.message.value", "native GEN value read"),
    ]
    for needle, label in banned:
        if needle in code:
            return False, f"found banned pattern '{needle}' ({label}) in code"
    return True, "no web retrieval / GEN value / transfer in code"


def check_no_try_except_around_semantic_calls(source):
    # Same discipline as the Stage 6a probe: no try/except wrapping the
    # nondet / equivalence-principle calls -- failure and Undetermined
    # must surface at the transaction/consensus level.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            seg = ast.get_source_segment(source, node) or ""
            if ("exec_prompt" in seg or "prompt_non_comparative" in seg
                    or "prompt_comparative" in seg or "strict_eq" in seg):
                return False, "try/except wraps a semantic/nondet call"
    return True, "no try/except around semantic/nondet calls"


def check_parameterless_constructor(source):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Contract":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    args = [a.arg for a in item.args.args if a.arg != "self"]
                    if args:
                        return False, f"__init__ has args: {args}"
                    if item.returns is not None:
                        return False, "__init__ has a return annotation (Studio schema-load gotcha)"
                    return True, "def __init__(self): -- parameterless, no -> None"
    return False, "Contract.__init__ not found"


def extract_abi(source):
    tree = ast.parse(source)
    writes, views = [], []
    contract = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Contract":
            contract = node
            break
    assert contract is not None

    def deco(dl, want):
        for d in dl:
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

    for item in contract.body:
        if not isinstance(item, ast.FunctionDef) or item.name.startswith("_"):
            continue
        if deco(item.decorator_list, ("gl", "public", "view")):
            views.append(item.name)
        elif deco(item.decorator_list, ("gl", "public", "write")):
            writes.append(item.name)
    return writes, views


def check_abi_shape(source):
    writes, views = extract_abi(source)
    exp_w = ["probe_input_determinism", "probe_raw_json", "probe_non_comparative",
             "probe_comparative", "probe_undetermined_control"]
    exp_v = ["get_observation", "get_call_count"]
    ok = sorted(writes) == sorted(exp_w) and sorted(views) == sorted(exp_v)
    return ok, f"writes={writes}, views={views}"


def check_scalar_only_public_inputs(source):
    tree = ast.parse(source)
    safe = {"u256", "u32", "u8", "u16", "u64", "u128", "i8", "i16", "i32", "i64",
            "bigint", "str", "bytes", "bool", "float"}
    contract = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Contract":
            contract = node
            break
    bad = []
    for item in contract.body:
        if not isinstance(item, ast.FunctionDef) or item.name.startswith("__"):
            continue
        is_pub = any(
            (lambda p: p in (("gl", "public", "write"), ("gl", "public", "view")))(
                tuple(reversed([c.attr for c in _attr_chain(d)] + ([d.id] if isinstance(d, ast.Name) else [])))
            )
            for d in item.decorator_list
        )
        if not is_pub:
            continue
        for a in item.args.args:
            if a.arg == "self":
                continue
            ann = a.annotation
            nm = ann.id if isinstance(ann, ast.Name) else (ast.unparse(ann) if ann else "NONE")
            if nm not in safe:
                bad.append(f"{item.name}.{a.arg}: {nm}")
    if bad:
        return False, "non-scalar public input(s): " + "; ".join(bad)
    return True, "every public input is a scalar (u256)"


def _attr_chain(node):
    out = []
    cur = node
    while isinstance(cur, ast.Attribute):
        out.append(cur)
        cur = cur.value
    return out


def check_governance_fork_untouched():
    if not PROD_PATH.exists():
        return False, "governance_fork.py missing"
    sha = hashlib.sha256(PROD_PATH.read_bytes()).hexdigest()
    expected = "cbfe8cb0dc89ab3ae5d4aefa31f1a77e1ca47ecf4db737ae4d5264310194f004"
    if sha != expected:
        return False, f"governance_fork.py SHA-256 changed: {sha}"
    return True, f"governance_fork.py unchanged, sha256={sha}"


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
        ("isolated from governance_fork.py (code)", check_isolated_from_production_contract(source)),
        ("no import of governance_fork", check_no_import_of_governance_fork(source)),
        ("parameterless constructor", check_parameterless_constructor(source)),
        ("uses both candidate primitives + exec_prompt + strict_eq", check_uses_both_candidate_primitives(source)),
        ("no banned patterns (web/GEN/transfer)", check_no_banned_patterns(source)),
        ("no try/except around semantic calls", check_no_try_except_around_semantic_calls(source)),
        ("scalar-only public inputs", check_scalar_only_public_inputs(source)),
        ("abi shape", check_abi_shape(source)),
        ("governance_fork.py untouched", check_governance_fork_untouched()),
    ]
    passed = failed = 0
    for name, (ok, detail) in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if ok:
            passed += 1
        else:
            failed += 1
    print()
    print(f"summary: {passed}/{passed + failed} checks passed")
    print()
    print("NOTE: LOCAL ONLY. Proves nothing about live GenVM semantic runtime")
    print("behavior. Stage 7 is NOT implemented -- this is a pre-implementation")
    print("probe to be deployed and exercised manually in Studio.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
