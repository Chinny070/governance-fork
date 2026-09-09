"""LOCAL ONLY static/source-shape checks for
contracts/probe/struct_argument_probe.py.

These checks verify Python syntax, ASCII/LF source-shape discipline,
isolation from contracts/governance_fork.py, the expected ABI shape, and
that probe_struct uses plain attribute access with no manual dict
conversion or error-catching.

They do NOT and CANNOT prove anything about live GenVM behavior -- that
is exactly what this probe exists to determine once it is deployed and
exercised manually. A clean pass here means only "this file is
syntactically valid and shaped as intended locally"; it says nothing
about whether GenVM actually reconstructs a dataclass-typed argument.
Do not treat a pass here as runtime evidence.
"""

from __future__ import annotations
import ast
import hashlib
import pathlib
import sys


PROBE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "contracts" / "probe" / "struct_argument_probe.py"
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
    lines = []
    for line in source.split("\n"):
        idx = line.find("#")
        lines.append(line if idx < 0 else line[:idx])
    return "\n".join(lines)


def check_isolated_from_production_contract(source):
    code_only = _strip_comments(source)
    tree = ast.parse(source)
    docstring_texts = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                docstring_texts.add(doc)
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


def _find_method(source, name):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def check_probe_struct_param_is_dataclass_type(source):
    node = _find_method(source, "probe_struct")
    if node is None:
        return False, "probe_struct not found"
    args = [a for a in node.args.args if a.arg != "self"]
    if len(args) != 1:
        return False, f"expected exactly 1 non-self argument, found {len(args)}"
    ann = args[0].annotation
    ann_name = ann.id if isinstance(ann, ast.Name) else ast.dump(ann)
    if ann_name != "ProbeStruct":
        return False, f"probe_struct's argument is typed '{ann_name}', expected 'ProbeStruct'"
    return True, "probe_struct(arg: ProbeStruct) confirmed"


def check_probe_struct_uses_attribute_access(source):
    node = _find_method(source, "probe_struct")
    if node is None:
        return False, "probe_struct not found"
    found_label = False
    found_value = False
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name) and child.value.id == "arg":
            if child.attr == "label":
                found_label = True
            if child.attr == "value":
                found_value = True
    if not (found_label and found_value):
        return False, f"missing attribute access: label={found_label}, value={found_value}"
    return True, "arg.label and arg.value attribute access confirmed"


def check_no_manual_dict_conversion_or_fallback(source):
    node = _find_method(source, "probe_struct")
    if node is None:
        return False, "probe_struct not found"
    for child in ast.walk(node):
        if isinstance(child, ast.Try):
            return False, "probe_struct contains a try/except -- error must not be caught"
        if isinstance(child, ast.Subscript):
            base = child.value
            if isinstance(base, ast.Name) and base.id == "arg":
                return False, "probe_struct uses arg[...] subscript access -- must be attribute access only"
        if isinstance(child, ast.Call):
            fname = child.func.id if isinstance(child.func, ast.Name) else None
            if fname == "dict":
                return False, "probe_struct calls dict(...) -- manual conversion not allowed"
        for kw in getattr(child, "keywords", []):
            if kw.arg is None and isinstance(kw.value, ast.Name) and kw.value.id == "arg":
                return False, "probe_struct unpacks **arg -- manual conversion not allowed"
    return True, "no manual dict conversion, no try/except in probe_struct"


def _code_only(source):
    # Same approach as check_isolated_from_production_contract: strip
    # comments and docstrings so checks over CODE don't false-positive on
    # this file's own explanatory prose (e.g. the header comment
    # discussing TreeMap[K, V] and DynArray[T] by name to document why
    # Method B was omitted and what this probe deliberately avoids).
    code_only = _strip_comments(source)
    tree = ast.parse(source)
    docstring_texts = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                docstring_texts.add(doc)
    for doc in docstring_texts:
        code_only = code_only.replace(doc, "")
    return code_only


def check_no_web_llm_gen_dynarray(source):
    code_only = _code_only(source)
    banned = [
        ("gl.nondet.web.", "web fetch usage"),
        ("prompt_comparative", "LLM semantic prompt"),
        ("prompt_non_comparative", "LLM semantic prompt"),
        ("gl.message.value", "native GEN value read"),
        ("transfer(", "GEN transfer logic"),
        ("DynArray[", "DynArray usage"),
        ("inmem_allocate", "storage inmem_allocate usage"),
        ("TreeMap[", "TreeMap usage"),
    ]
    for needle, label in banned:
        if needle in code_only:
            return False, f"found banned pattern '{needle}' ({label}) in code"
    return True, "no web/LLM/GEN/DynArray/TreeMap/inmem_allocate usage in code"


def check_method_b_absent_and_documented(source):
    if "probe_map" in source:
        return False, "probe_map found -- Method B was supposed to be omitted"
    if "dict[K, V]" not in source and "bare `dict`" not in source and "bare dict" not in source.replace("`", ""):
        return False, "no documentation found explaining why Method B (dict control) was omitted"
    return True, "Method B correctly absent, with documented rationale in header comment"


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
    expected_writes = ["probe_struct", "probe_flat"]
    expected_views = ["get_state", "get_call_count"]
    ok = sorted(writes) == sorted(expected_writes) and sorted(views) == sorted(expected_views)
    detail = f"writes={writes}, views={views}"
    return ok, detail


def check_governance_fork_untouched():
    if not PROD_PATH.exists():
        return False, "governance_fork.py not found"
    raw = PROD_PATH.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    expected = "2e3aef2281b6855a3cc21f7b46f8c5b06598bb842e927ea58c374d894bd5cef9"
    if sha != expected:
        return False, f"governance_fork.py SHA-256 changed: {sha} (expected {expected})"
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
        ("probe_struct param is ProbeStruct", check_probe_struct_param_is_dataclass_type(source)),
        ("probe_struct uses arg.label / arg.value", check_probe_struct_uses_attribute_access(source)),
        ("no manual dict conversion / no try-except", check_no_manual_dict_conversion_or_fallback(source)),
        ("no web/LLM/GEN/DynArray/TreeMap/inmem_allocate", check_no_web_llm_gen_dynarray(source)),
        ("Method B absent, documented", check_method_b_absent_and_documented(source)),
        ("abi shape", check_abi_shape(source)),
        ("governance_fork.py untouched", check_governance_fork_untouched()),
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
    print("NOT and CANNOT prove GenVM runtime struct-argument-reconstruction")
    print("behavior -- that is exactly the open question this probe exists")
    print("to answer once it is deployed and exercised manually. Schema")
    print("acceptance is not runtime success; only a live Execution Result")
    print("settles the hypothesis.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
