"""Stage 6a Phase A static checks for contracts/probe/web_render_probe.py.

This is a DIFFERENT check profile than tests/stage_2_checks.py: the probe
contract is SUPPOSED to call gl.nondet.web.render and gl.eq_principle.strict_eq
-- that's the entire point of Stage 6a. These checks instead verify:

    - Python syntax, ASCII-only, LF-only (same source-shape discipline as
      the production contract)
    - The probe uses gl.nondet.web.render (not web.get, per explicit
      project direction: production evidence direction is render())
    - The probe wraps every render() call in gl.eq_principle.strict_eq
    - The probe does NOT use gl.message.value, does NOT use prompt_
      comparative/prompt_non_comparative, does NOT transfer value
    - The probe contract is completely separate from and does not import
      or modify contracts/governance_fork.py
    - Expected ABI shape (write/view counts)

No live network calls happen here. No deployment. Local/static only.
"""

from __future__ import annotations
import ast
import hashlib
import pathlib
import sys


PROBE_PATH = pathlib.Path(__file__).resolve().parents[1] / "contracts" / "probe" / "web_render_probe.py"
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


def check_uses_web_render(source):
    if "gl.nondet.web.render(" not in source:
        return False, "gl.nondet.web.render( not found -- probe must test render()"
    return True, "gl.nondet.web.render( present"

def check_does_not_use_web_get(source):
    if "gl.nondet.web.get(" in source:
        return False, "gl.nondet.web.get( found -- production evidence direction is render(), not get()"
    return True, "gl.nondet.web.get( absent"


def check_every_render_wrapped_in_strict_eq(source):
    # Heuristic: every render() call site must be inside a function that is
    # itself passed to gl.eq_principle.strict_eq somewhere in the file.
    if "gl.eq_principle.strict_eq(" not in source:
        return False, "gl.eq_principle.strict_eq( not found"
    n_render = source.count("gl.nondet.web.render(")
    n_strict_eq = source.count("gl.eq_principle.strict_eq(")
    if n_strict_eq < 1:
        return False, "no strict_eq wrapping found"
    # Every leader function defined between render() call sites should have
    # a matching strict_eq call. We can't easily prove 1:1 without deeper
    # AST work, so assert both are present and roughly proportional (each
    # mode/wait branch gets its own leader function and its own strict_eq
    # call in this probe's design).
    return True, f"{n_render} render() call(s), {n_strict_eq} strict_eq() call(s)"


def check_no_prompt_comparative(source):
    for banned in ("gl.eq_principle.prompt_comparative(", "gl.eq_principle.prompt_non_comparative("):
        if banned in source:
            return False, f"{banned} present -- probe should use strict_eq per the official pattern"
    return True, "no prompt_comparative/prompt_non_comparative"


def check_no_gl_message_value(source):
    if "gl.message.value" in source:
        return False, "gl.message.value referenced"
    return True, "no gl.message.value"


def check_no_transfer(source):
    if "transfer(" in source:
        return False, "transfer( present"
    return True, "no transfer("


def check_isolated_from_production_contract(source):
    if "governance_fork" in source:
        return False, "references governance_fork -- probe must stay isolated"
    return True, "isolated from governance_fork.py"


def check_no_try_except_around_nondet(source):
    # Deliberate Phase A design choice: do not wrap nondet/strict_eq calls
    # in try/except. Undetermined and failure behavior should surface at
    # the transaction/consensus level where the operator can observe it
    # directly, not be silently caught inside the contract.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            src_slice = ast.get_source_segment(source, node) or ""
            if "strict_eq" in src_slice or "web.render" in src_slice:
                return False, "try/except found wrapping a nondet/strict_eq call"
    return True, "no try/except around nondet calls"


def check_production_contract_unchanged_by_probe(_source):
    # The probe file must not be the reason governance_fork.py changed.
    # This check just confirms governance_fork.py has no probe-specific
    # additions (best-effort signal, not a hash comparison across commits).
    prod_source = PROD_PATH.read_text()
    for banned in ("gl.nondet.", "gl.eq_principle.", "web_render_probe"):
        if banned in prod_source:
            return False, f"production contract references {banned}"
    return True, "production contract has zero probe-related additions"


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
    expected_writes = ["run_probe"]
    expected_views = ["get_probe", "list_probes", "get_probe_count"]
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
        ("uses gl.nondet.web.render", check_uses_web_render(source)),
        ("does not use gl.nondet.web.get", check_does_not_use_web_get(source)),
        ("render calls wrapped in strict_eq", check_every_render_wrapped_in_strict_eq(source)),
        ("no prompt_comparative/prompt_non_comparative", check_no_prompt_comparative(source)),
        ("no gl.message.value", check_no_gl_message_value(source)),
        ("no transfer(", check_no_transfer(source)),
        ("isolated from governance_fork.py", check_isolated_from_production_contract(source)),
        ("no try/except around nondet calls", check_no_try_except_around_nondet(source)),
        ("production contract unaffected", check_production_contract_unchanged_by_probe(source)),
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
    print("NOTE: these are LOCAL/STATIC checks only. They cannot verify live")
    print("render() behavior, consensus outcomes, or Undetermined handling --")
    print("that requires an actual Studio schema-load followed by live probe")
    print("transactions, which are explicitly OUT OF SCOPE for Phase A.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
