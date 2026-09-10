"""Stage 2 static checks for contracts/governance_fork.py.

Runs local, deployment-free validations only:
    - Python syntax (compile)
    - ASCII-only source
    - LF line endings (no CRLF)
    - Duplicate top-level identifier detection
    - Prohibited substring gates (gl.nondet, web.render, web.get, .value, transfer)
    - ABI method count (write / view / admin)
    - Enum-value uniqueness within known groups

Reports available vs unavailable tooling honestly; does not fabricate results.
"""

from __future__ import annotations
import ast
import hashlib
import pathlib
import re
import shutil
import sys


CONTRACT_PATH = pathlib.Path(__file__).resolve().parents[1] / "contracts" / "governance_fork.py"


def _read() -> tuple[str, bytes]:
    raw = CONTRACT_PATH.read_bytes()
    return raw.decode("ascii"), raw


def check_python_syntax(source: str) -> tuple[bool, str]:
    try:
        ast.parse(source)
        return True, "ast.parse ok"
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"


def check_ascii_only(raw: bytes) -> tuple[bool, str]:
    for i, b in enumerate(raw):
        if b > 127:
            return False, f"non-ASCII byte 0x{b:02x} at offset {i}"
    return True, f"{len(raw)} bytes, ASCII-only"


def check_lf_line_endings(raw: bytes) -> tuple[bool, str]:
    if b"\r\n" in raw:
        return False, "CRLF sequences present"
    if b"\r" in raw:
        return False, "bare CR present"
    return True, "LF only"


def _code_only(source: str) -> str:
    """source with '#' comments and def/class/module docstrings removed, so
    substring gates match real code, not prose that discusses banned APIs."""
    out_lines = []
    for line in source.split("\n"):
        i = line.find("#")
        out_lines.append(line if i < 0 else line[:i])
    code = "\n".join(out_lines)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            d = ast.get_docstring(node, clean=False)
            if d:
                code = code.replace(d, "")
    return code


def check_no_prohibited_calls(source: str) -> tuple[bool, str]:
    # Baseline at Stage 7:
    #   - gl.nondet.web.render(...) wrapped in gl.eq_principle.strict_eq(...)
    #     is the sanctioned evidence-retrieval pathway (fetch_evidence).
    #   - gl.eq_principle.prompt_comparative(fn, ...) with
    #     fn == lambda: gl.nondet.exec_prompt(prompt, response_format="json")
    #     is the sanctioned semantic-adjudication pathway (run_adjudication);
    #     the primitive + evidence budget were chosen from a live isolated
    #     probe, not pre-decided (see the Stage 7 semantic probe report).
    # Stage 9: native GEN economics -- gl.message.value (payable capture)
    # and gl.get_contract_at(<Address>).emit_transfer(value=<u256>) (payout)
    # are the ONLY sanctioned value APIs; both were live-proven by
    # contracts/probe/value_transfer_probe.py on the pinned runtime.
    # Still banned: web.get; prompt_non_comparative (probe-rejected:
    # markdown-fenced JSON -> strict-parse failures); a bare `transfer(`
    # that is not `emit_transfer(` (no unsupported / ad-hoc value API).
    code = _code_only(source)
    banned = [
        r"web\.get\(",
        r"gl\.eq_principle\.prompt_non_comparative",
        r"(?<!emit_)transfer\(",
    ]
    hits = []
    for pat in banned:
        for m in re.finditer(pat, code):
            line = code[: m.start()].count("\n") + 1
            hits.append(f"{pat} at line {line}")
    if hits:
        return False, "; ".join(hits)
    # Positive checks: the sanctioned pathways must actually be present.
    for needle in (
        "gl.nondet.web.render(",
        "gl.eq_principle.strict_eq(",
        "gl.eq_principle.prompt_comparative(",
        "gl.nondet.exec_prompt(",
        'response_format="json"',
        "gl.get_contract_at(",
        ".emit_transfer(value=",
    ):
        if needle not in code:
            return False, f"expected sanctioned call/arg not found: {needle}"
    return True, (
        "render/strict_eq + prompt_comparative/exec_prompt(json) + "
        "get_contract_at/emit_transfer present; web.get / "
        "prompt_non_comparative / bare transfer absent"
    )


def check_semantic_calls_unwrapped(source: str) -> tuple[bool, str]:
    """The semantic / nondet calls must NOT be wrapped in try/except -- an
    Undetermined outcome or a strict-parse rejection must surface as a
    transaction revert (zero state committed), never be swallowed."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            seg = ast.get_source_segment(source, node) or ""
            for needle in ("exec_prompt", "prompt_comparative", "strict_eq",
                           "web.render"):
                if needle in seg:
                    return False, f"try/except wraps a nondet/semantic call ({needle})"
    return True, "no try/except around nondet/semantic calls"


def check_message_value_only_in_writes(source: str) -> tuple[bool, str]:
    # Stage 9: gl.message.value IS the sanctioned bond-capture read. It must
    # be present, and it must never appear inside a @gl.public.view method
    # (view methods take no value).
    code = _code_only(source)
    if "gl.message.value" not in code:
        return False, "gl.message.value expected (bond capture) but not found"
    tree = ast.parse(source)
    contract = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Contract":
            contract = node
            break
    assert contract is not None
    for item in contract.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        is_view = False
        for d in item.decorator_list:
            path = []
            cur = d
            while isinstance(cur, ast.Attribute):
                path.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                path.append(cur.id)
            if tuple(reversed(path)) == ("gl", "public", "view"):
                is_view = True
        if is_view:
            seg = ast.get_source_segment(source, item) or ""
            if "gl.message.value" in seg:
                return False, f"gl.message.value read inside view method {item.name}"
    return True, "gl.message.value present, never in a view method"


def extract_abi(source: str) -> tuple[list[str], list[str], list[str]]:
    """Return (write_methods, view_methods, admin_methods) from the AST."""
    tree = ast.parse(source)
    writes: list[str] = []
    views: list[str] = []
    admins = {"pause", "unpause"}
    write_names: list[str] = []
    view_names: list[str] = []
    admin_names: list[str] = []

    contract_cls = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Contract":
            contract_cls = node
            break
    assert contract_cls is not None, "Contract class not found"

    def deco_matches(decorators: list[ast.expr], want: tuple[str, ...]) -> bool:
        # want is a tuple of attribute-path components e.g. ("gl","public","view")
        for d in decorators:
            path: list[str] = []
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
        if item.name in admins:
            admin_names.append(item.name)
            continue
        if deco_matches(item.decorator_list, ("gl", "public", "view")):
            view_names.append(item.name)
        elif deco_matches(item.decorator_list, ("gl", "public", "write")) or deco_matches(
            item.decorator_list, ("gl", "public", "write", "payable")
        ):
            write_names.append(item.name)
    return write_names, view_names, admin_names


def check_abi_counts(source: str) -> tuple[bool, str]:
    writes, views, admins = extract_abi(source)
    total = len(writes) + len(views) + len(admins)
    expected_write = 15  # Stage 6b: +close_evidence, +fetch_evidence,
                         # +seal_evidence, +abort_case, -freeze_evidence,
                         # -freeze_case (11 - 2 + 4 = 13).
                         # Stage 7: +run_adjudication (-> 14).
                         # Stage 9: +withdraw_treasury (-> 15).
    expected_view = 17   # Stage 9: +list_bonds_by_target (16 -> 17).
    expected_admin = 2
    expected_total = expected_write + expected_view + expected_admin
    ok = (
        len(writes) == expected_write
        and len(views) == expected_view
        and len(admins) == expected_admin
        and total == expected_total
    )
    detail = (
        f"writes={len(writes)}(exp {expected_write}), "
        f"views={len(views)}(exp {expected_view}), "
        f"admin={len(admins)}(exp {expected_admin}), "
        f"total={total}(exp {expected_total})"
    )
    if not ok:
        detail += (
            f"\n  write: {writes}\n  view:  {views}\n  admin: {admins}"
        )
    return ok, detail


def check_no_dataclass_inputs(source: str) -> tuple[bool, str]:
    """ABI compatibility guard (item I of the ABI correction's required
    tests): no public write/admin method may declare a parameter typed as
    a custom @allow_storage dataclass, or as DynArray[<custom dataclass>].
    This is exactly the class of parameter that a live struct-argument
    probe and the live submit_root_envelope failure confirmed this pinned
    GenVM runtime cannot reconstruct from calldata (it arrives as a plain
    dict, not the declared type). See docs/STORAGE_CONSTRUCTION_AUDIT.md
    and the struct-argument probe report for the full investigation.

    View-method inputs are also checked (they were already all scalars
    per the audit, and must stay that way); dataclass-typed VIEW RETURN
    values are explicitly fine and are not checked here -- output
    reconstruction is a separate, already-confirmed-safe code path.
    """
    tree = ast.parse(source)
    contract_cls = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Contract":
            contract_cls = node
            break
    assert contract_cls is not None, "Contract class not found"

    safe_scalars = {
        "u8", "u16", "u32", "u64", "u128", "u256",
        "i8", "i16", "i32", "i64",
        "bigint", "str", "bytes", "bool", "float",
    }

    def deco_matches(decorators: list[ast.expr], want: tuple[str, ...]) -> bool:
        for d in decorators:
            path: list[str] = []
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

    def classify(ann: ast.expr | None) -> str:
        if ann is None:
            return "UNANNOTATED"
        if isinstance(ann, ast.Name):
            return "SAFE" if ann.id in safe_scalars else f"UNSAFE_CUSTOM({ann.id})"
        if isinstance(ann, ast.Subscript):
            base = ast.unparse(ann.value)
            if base == "DynArray":
                inner = ann.slice
                inner_name = inner.id if isinstance(inner, ast.Name) else ast.unparse(inner)
                if inner_name in safe_scalars:
                    return "SAFE"
                return f"UNSAFE_ARRAY_OF_CUSTOM({inner_name})"
            return f"UNKNOWN_SUBSCRIPT({ast.unparse(ann)})"
        return f"UNKNOWN({ast.unparse(ann)})"

    offenders = []
    for item in contract_cls.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        if item.name.startswith("__"):
            continue
        is_public = deco_matches(item.decorator_list, ("gl", "public", "view")) or deco_matches(
            item.decorator_list, ("gl", "public", "write")
        ) or deco_matches(item.decorator_list, ("gl", "public", "write", "payable")) or item.name in ("pause", "unpause")
        if not is_public:
            continue
        for a in item.args.args:
            if a.arg == "self":
                continue
            cls = classify(a.annotation)
            if cls.startswith("UNSAFE") or cls.startswith("UNKNOWN"):
                offenders.append(f"{item.name}.{a.arg}: {cls}")

    if offenders:
        return False, "runtime-unsafe public input(s) found: " + "; ".join(offenders)
    return True, "every public write/admin/view input is a safe scalar or DynArray-of-scalar"


def check_no_duplicate_abi_names(source: str) -> tuple[bool, str]:
    writes, views, admins = extract_abi(source)
    seen: dict[str, str] = {}
    for name in writes:
        seen[name] = "write"
    dups = []
    for name in views:
        if name in seen:
            dups.append(f"{name} ({seen[name]} + view)")
        seen[name] = "view"
    for name in admins:
        if name in seen:
            dups.append(f"{name} ({seen[name]} + admin)")
        seen[name] = "admin"
    if dups:
        return False, "duplicate ABI names: " + ", ".join(dups)
    return True, "no duplicate ABI names"


def check_no_unchanged_delta_kind(source: str) -> tuple[bool, str]:
    # Stage 2 recommendation: CLAIM_UNCHANGED must not exist.
    if "CLAIM_UNCHANGED" in source:
        return False, "CLAIM_UNCHANGED enum value present"
    if '"UNCHANGED"' in source:
        return False, 'literal "UNCHANGED" present'
    return True, "no CLAIM_UNCHANGED"


ENUM_GROUPS: dict[str, tuple[str, ...]] = {
    "Verdict": (
        "VERDICT_FAITHFUL",
        "VERDICT_NOT_FAITHFUL",
        "VERDICT_UNCLEAR",
        "VERDICT_INVALID",
    ),
    "SemanticFinding": (
        "FINDING_SATISFIED",
        "FINDING_NOT_SATISFIED",
        "FINDING_UNCLEAR",
    ),
    "ForkDimensions": (
        "FORK_DIM_INTENT_PRESERVATION",
        "FORK_DIM_DELTA_ACCURACY",
        "FORK_DIM_UNDECLARED_SEMANTIC_CHANGE",
        "FORK_DIM_EVIDENCE_SUPPORT",
        "FORK_DIM_SOURCE_AUTHORITY",
        "FORK_DIM_TEMPORAL_RELEVANCE",
        "FORK_DIM_INTERNAL_CONSISTENCY",
    ),
    "RootEnvelopeDimensions": (
        "RE_DIM_OBJECTIVE_REPRESENTATION",
        "RE_DIM_SCOPE_FIDELITY",
        "RE_DIM_CONSTRAINT_COMPLETENESS",
        "RE_DIM_DIMENSION_CLASSIFICATION",
        "RE_DIM_EVIDENCE_SUPPORT",
        "RE_DIM_SOURCE_AUTHORITY",
    ),
    "ClaimKind": (
        "CLAIM_NARROWED",
        "CLAIM_BROADENED",
        "CLAIM_RESHAPED",
        "CLAIM_REMOVED",
        "CLAIM_ADDED",
    ),
    "TargetKind": ("TARGET_KIND_FORK", "TARGET_KIND_ROOT_ENVELOPE"),
    "ChallengeStatus": (
        "CHALLENGE_OPEN",
        "CHALLENGE_ADJUDICATING",
        "CHALLENGE_RESOLVED_FLIPPED",
        "CHALLENGE_RESOLVED_UNCHANGED",
        "CHALLENGE_RESOLVED_INVALID",
        "CHALLENGE_RESOLVED_UNCLEAR",
    ),
    "ChallengeGroundsFork": (
        "CG_FORK_INTENT_MISREAD",
        "CG_FORK_DELTA_MISCLASSIFIED",
        "CG_FORK_UNDECLARED_CHANGE_IGNORED",
        "CG_FORK_SOURCE_AUTHORITY_ERROR",
        "CG_FORK_TEMPORAL_EVIDENCE_ERROR",
        "CG_FORK_CONTRADICTORY_EVIDENCE_OMITTED",
        "CG_FORK_MALFORMED_ADJUDICATION",
    ),
    "ChallengeGroundsRootEnvelope": (
        "CG_RE_OBJECTIVE_MISREPRESENTED",
        "CG_RE_SCOPE_MISCHARACTERIZED",
        "CG_RE_CONSTRAINT_INCOMPLETE",
        "CG_RE_DIMENSION_MISCLASSIFIED",
        "CG_RE_SOURCE_AUTHORITY_ERROR",
        "CG_RE_EVIDENCE_SUPPORT_ERROR",
        "CG_RE_MALFORMED_ADJUDICATION",
    ),
    "BondSettlement": (
        "BOND_UNSETTLED",
        "BOND_SETTLED_FULL_REFUND",
        "BOND_SETTLED_PARTIAL_SLASH",
        "BOND_SETTLED_CHALLENGER_REWARD",
    ),
}


def check_enum_uniqueness(source: str) -> tuple[bool, str]:
    tree = ast.parse(source)
    assigned: dict[str, str] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, str
            ):
                assigned[tgt.id] = node.value.value
    problems: list[str] = []
    for group, keys in ENUM_GROUPS.items():
        values: dict[str, str] = {}
        for k in keys:
            if k not in assigned:
                problems.append(f"{group}: missing {k}")
                continue
            v = assigned[k]
            if v in values:
                problems.append(f"{group}: value {v!r} shared by {values[v]} and {k}")
            values[v] = k
    if problems:
        return False, "; ".join(problems)
    return True, f"{len(ENUM_GROUPS)} enum groups verified"


def check_no_slashed_full_kind(source: str) -> tuple[bool, str]:
    # V1 has no SETTLED_FULL_SLASH transition.
    if "SETTLED_FULL_SLASH" in source:
        return False, "SETTLED_FULL_SLASH present (V1 has no full-slash transition)"
    return True, "no SETTLED_FULL_SLASH"


def check_reward_is_pool_funded(source: str) -> tuple[bool, str]:
    # Stage 9: a challenger-flip reward is allowed, but it must be drawn
    # from (and capped by) the on-contract treasury_pool -- never an
    # unfunded liability. Guard against the old unresolved-source names,
    # and require the pool-cap + pool-debit pattern around the reward.
    code = _code_only(source)
    for banned in ("reward_due", "challenger_reward_amount", "reward_owed"):
        if banned in code:
            return False, f"unfunded reward field present: {banned}"
    if "reward_amount" in code:
        need = [
            "pool >= CHALLENGER_FLIP_REWARD",          # cap at pool balance
            "treasury_pool = u256(int(self.treasury_pool) - reward)",  # pool debit
        ]
        missing = [n for n in need if n not in code]
        if missing:
            return False, "reward present but not pool-capped/debited: " + "; ".join(missing)
    return True, "challenger reward (if any) is treasury_pool-funded and capped"


def try_genvm_lint() -> tuple[str, str]:
    binary = shutil.which("genvm-lint")
    if binary is None:
        return "UNAVAILABLE", "genvm-lint not on PATH; deferred to Stage 12 CI"
    return "UNAVAILABLE", "detection would run here in a Stage 12 environment"


def main() -> int:
    source, raw = _read()
    sha = hashlib.sha256(raw).hexdigest()
    print(f"contract:      {CONTRACT_PATH}")
    print(f"sha256:        {sha}")
    print(f"bytes:         {len(raw)}")
    print(f"lines:         {source.count(chr(10)) + (0 if source.endswith(chr(10)) else 1)}")
    print()

    checks = [
        ("python syntax", check_python_syntax(source)),
        ("ascii only", check_ascii_only(raw)),
        ("lf line endings", check_lf_line_endings(raw)),
        ("no prohibited calls", check_no_prohibited_calls(source)),
        ("semantic/nondet calls not try-wrapped", check_semantic_calls_unwrapped(source)),
        ("gl.message.value only in writes", check_message_value_only_in_writes(source)),
        ("no duplicate abi names", check_no_duplicate_abi_names(source)),
        ("abi counts", check_abi_counts(source)),
        ("no dataclass-typed public inputs", check_no_dataclass_inputs(source)),
        ("no unchanged delta kind", check_no_unchanged_delta_kind(source)),
        ("enum uniqueness", check_enum_uniqueness(source)),
        ("no full-slash kind", check_no_slashed_full_kind(source)),
        ("challenger reward is treasury-pool funded", check_reward_is_pool_funded(source)),
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
    tool_status, tool_note = try_genvm_lint()
    print(f"  [{tool_status}] genvm-lint: {tool_note}")
    print(f"  [UNAVAILABLE] genlayer-studio schema-load: no local instance in this env")

    print()
    print(f"summary: {passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
