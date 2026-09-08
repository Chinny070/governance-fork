# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass

import hashlib


# =========================================================================
# Constants (bounded caps, immutable at deploy)
# =========================================================================

MAX_DAOS = 1024
MAX_ROOTS_PER_DAO = 256
MAX_FORKS_PER_ROOT = 512
MAX_CHILDREN_PER_PARENT = 32
MAX_DEPTH_PER_ROOT = 8
MAX_EVIDENCE_PER_CASE = 16
MAX_CHALLENGES_PER_TARGET = 3
MAX_EVIDENCE_SLICE = 16384  # bytes; provisional, subject to Stage 6a probe
PAGINATION_LIMIT_MAX = 50

MAX_URL_LEN = 512
MAX_TITLE_LEN = 256
MAX_OBJECTIVE_LEN = 512
MAX_SCOPE_LEN = 256
MAX_BENEFICIARY_CLASS_LEN = 128
MAX_ESSENTIAL_CONSTRAINT_ITEMS = 8
MAX_ESSENTIAL_CONSTRAINT_LEN = 128
MAX_MUTABLE_DIMENSIONS = 16
MAX_IMMUTABLE_DIMENSIONS = 16
MAX_DIMENSION_NAME_LEN = 64
MAX_DELTA_ENTRIES = 16
MAX_DELTA_VALUE_LEN = 256
MAX_STRUCTURED_PARAMS = 32
MAX_KV_KEY_LEN = 64
MAX_KV_VAL_LEN = 256
MAX_REASONING_LEN = 1024
MAX_CHALLENGE_ARG_LEN = 512
MAX_EXTERNAL_ID_LEN = 128
MAX_DAO_NAME_LEN = 128
MAX_NORMALIZED_SOURCE_LEN = 128
MAX_RELEVANCE_CLAIM_LEN = 256
MAX_AUTHORITY_CLAIM_LEN = 128
MAX_TEMPORAL_MARKER_LEN = 64
MAX_DIMENSION_REASONING_LEN = 512

RETRY_COOLDOWN_SECONDS = 3600
CHALLENGE_WINDOW_SECONDS = 259200  # 72 hours
MAX_RETRIES_PER_CASE = 3

FORK_CREATION_BOND = 100000000000000000  # 0.1 * 10**18, provisional
ENVELOPE_BOND = 100000000000000000
CHALLENGE_BOND = 100000000000000000

ADJUDICATION_DIMENSIONS_VERSION_FORK = 1
ADJUDICATION_DIMENSIONS_VERSION_ROOT_ENVELOPE = 1


# =========================================================================
# Enum values (string constants; fields typed `str` in dataclasses)
# =========================================================================

# Root identity
IDENTITY_COMMUNITY_IMPORTED = "COMMUNITY_IMPORTED"
IDENTITY_DAO_VERIFIED_LATER = "DAO_VERIFIED_LATER"
IDENTITY_UNVERIFIED = "UNVERIFIED"

# Envelope status
ENVELOPE_NOT_SUBMITTED = "ENVELOPE_NOT_SUBMITTED"
ENVELOPE_EVIDENCE_OPEN = "ENVELOPE_EVIDENCE_OPEN"
ENVELOPE_EVIDENCE_FROZEN = "ENVELOPE_EVIDENCE_FROZEN"
ENVELOPE_ADJUDICATING = "ENVELOPE_ADJUDICATING"
ENVELOPE_FAITHFUL = "ENVELOPE_FAITHFUL"
ENVELOPE_REJECTED = "ENVELOPE_REJECTED"
ENVELOPE_UNCLEAR = "ENVELOPE_UNCLEAR"

# Fork status
FORK_DRAFT = "DRAFT"
FORK_EVIDENCE_OPEN = "EVIDENCE_OPEN"
FORK_EVIDENCE_FROZEN = "EVIDENCE_FROZEN"
FORK_CASE_FROZEN = "CASE_FROZEN"
FORK_ADJUDICATING = "ADJUDICATING"
FORK_VERDICT_PROPOSED = "VERDICT_PROPOSED"
FORK_CHALLENGE_WINDOW = "CHALLENGE_WINDOW"
FORK_CHALLENGE_OPEN = "CHALLENGE_OPEN"
FORK_FINALIZED_FAITHFUL = "FINALIZED_FAITHFUL"
FORK_FINALIZED_NOT_FAITHFUL = "FINALIZED_NOT_FAITHFUL"
FORK_FINALIZED_UNCLEAR = "FINALIZED_UNCLEAR"
FORK_FINALIZED_INVALID = "FINALIZED_INVALID"

# Evidence class
EC_OFFICIAL_GOVERNANCE = "OFFICIAL_GOVERNANCE"
EC_OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
EC_OFFICIAL_TREASURY = "OFFICIAL_TREASURY"
EC_FINALIZED_DECISION = "FINALIZED_DECISION"
EC_GOVERNANCE_DISCUSSION = "GOVERNANCE_DISCUSSION"
EC_IMPLEMENTATION_SPEC = "IMPLEMENTATION_SPEC"
EC_AUDIT = "AUDIT"
EC_THIRD_PARTY_ANALYSIS = "THIRD_PARTY_ANALYSIS"

# Case type
CASE_TYPE_ROOT_ENVELOPE = "ROOT_ENVELOPE"
CASE_TYPE_FORK = "FORK"
CASE_TYPE_CHALLENGE = "CHALLENGE"

# Case state
CASE_OPEN = "OPEN"
CASE_EVIDENCE_FROZEN = "EVIDENCE_FROZEN"
CASE_CASE_FROZEN = "CASE_FROZEN"
CASE_ADJUDICATING = "ADJUDICATING"
CASE_SUCCESS = "SUCCESS"
CASE_UNDETERMINED = "UNDETERMINED"
CASE_UNDETERMINED_TERMINAL = "UNDETERMINED_TERMINAL"
CASE_INVALID = "INVALID"

# Verdict
VERDICT_FAITHFUL = "FAITHFUL"
VERDICT_NOT_FAITHFUL = "NOT_FAITHFUL"
VERDICT_UNCLEAR = "UNCLEAR_VERDICT"
VERDICT_INVALID = "INVALID"

# Semantic finding
FINDING_SATISFIED = "SATISFIED"
FINDING_NOT_SATISFIED = "NOT_SATISFIED"
FINDING_UNCLEAR = "UNCLEAR"

# Fork adjudication dimensions
FORK_DIM_INTENT_PRESERVATION = "INTENT_PRESERVATION"
FORK_DIM_DELTA_ACCURACY = "DELTA_ACCURACY"
FORK_DIM_UNDECLARED_SEMANTIC_CHANGE = "UNDECLARED_SEMANTIC_CHANGE"
FORK_DIM_EVIDENCE_SUPPORT = "EVIDENCE_SUPPORT"
FORK_DIM_SOURCE_AUTHORITY = "SOURCE_AUTHORITY"
FORK_DIM_TEMPORAL_RELEVANCE = "TEMPORAL_RELEVANCE"
FORK_DIM_INTERNAL_CONSISTENCY = "INTERNAL_CONSISTENCY"

# Root envelope adjudication dimensions
RE_DIM_OBJECTIVE_REPRESENTATION = "OBJECTIVE_REPRESENTATION"
RE_DIM_SCOPE_FIDELITY = "SCOPE_FIDELITY"
RE_DIM_CONSTRAINT_COMPLETENESS = "CONSTRAINT_COMPLETENESS"
RE_DIM_DIMENSION_CLASSIFICATION = "DIMENSION_CLASSIFICATION"
RE_DIM_EVIDENCE_SUPPORT = "EVIDENCE_SUPPORT"
RE_DIM_SOURCE_AUTHORITY = "SOURCE_AUTHORITY"

# Delta claim kind (UNCHANGED intentionally omitted per Stage 2 recommendation)
CLAIM_NARROWED = "NARROWED"
CLAIM_BROADENED = "BROADENED"
CLAIM_RESHAPED = "RESHAPED"
CLAIM_REMOVED = "REMOVED"
CLAIM_ADDED = "ADDED"

# Challenge grounds (fork)
CG_FORK_INTENT_MISREAD = "INTENT_MISREAD"
CG_FORK_DELTA_MISCLASSIFIED = "DELTA_MISCLASSIFIED"
CG_FORK_UNDECLARED_CHANGE_IGNORED = "UNDECLARED_CHANGE_IGNORED"
CG_FORK_SOURCE_AUTHORITY_ERROR = "SOURCE_AUTHORITY_ERROR"
CG_FORK_TEMPORAL_EVIDENCE_ERROR = "TEMPORAL_EVIDENCE_ERROR"
CG_FORK_CONTRADICTORY_EVIDENCE_OMITTED = "CONTRADICTORY_EVIDENCE_OMITTED"
CG_FORK_MALFORMED_ADJUDICATION = "MALFORMED_ADJUDICATION"

# Challenge grounds (root envelope)
CG_RE_OBJECTIVE_MISREPRESENTED = "OBJECTIVE_MISREPRESENTED"
CG_RE_SCOPE_MISCHARACTERIZED = "SCOPE_MISCHARACTERIZED"
CG_RE_CONSTRAINT_INCOMPLETE = "CONSTRAINT_INCOMPLETE"
CG_RE_DIMENSION_MISCLASSIFIED = "DIMENSION_MISCLASSIFIED"
CG_RE_SOURCE_AUTHORITY_ERROR = "ENVELOPE_SOURCE_AUTHORITY_ERROR"
CG_RE_EVIDENCE_SUPPORT_ERROR = "ENVELOPE_EVIDENCE_SUPPORT_ERROR"
CG_RE_MALFORMED_ADJUDICATION = "ENVELOPE_MALFORMED_ADJUDICATION"

# Challenge status
CHALLENGE_OPEN = "OPEN"
CHALLENGE_ADJUDICATING = "ADJUDICATING"
CHALLENGE_RESOLVED_FLIPPED = "RESOLVED_FLIPPED"
CHALLENGE_RESOLVED_UNCHANGED = "RESOLVED_UNCHANGED"
CHALLENGE_RESOLVED_INVALID = "RESOLVED_INVALID"
CHALLENGE_RESOLVED_UNCLEAR = "RESOLVED_UNCLEAR"

# Bond purpose
BOND_PURPOSE_FORK_CREATION = "FORK_CREATION"
BOND_PURPOSE_ENVELOPE = "ENVELOPE"
BOND_PURPOSE_CHALLENGE = "CHALLENGE"

# Bond settlement kind
BOND_UNSETTLED = "UNSETTLED"
BOND_SETTLED_FULL_REFUND = "SETTLED_FULL_REFUND"
BOND_SETTLED_PARTIAL_SLASH = "SETTLED_PARTIAL_SLASH"
BOND_SETTLED_CHALLENGER_REWARD = "SETTLED_CHALLENGER_REWARD"

# Target kind (for unified challenge/verdict endpoints)
TARGET_KIND_FORK = "FORK"
TARGET_KIND_ROOT_ENVELOPE = "ROOT_ENVELOPE"

# Parent kind (for a Fork's parent reference)
PARENT_KIND_ROOT = "PARENT_ROOT"
PARENT_KIND_FORK = "PARENT_FORK"

# Resource type
RESOURCE_TREASURY = "TREASURY"
RESOURCE_PROTOCOL_PARAMETER = "PROTOCOL_PARAMETER"
RESOURCE_POLICY = "POLICY"
RESOURCE_GRANT_POOL = "GRANT_POOL"
RESOURCE_INCENTIVE_BUDGET = "INCENTIVE_BUDGET"
RESOURCE_OTHER = "OTHER"


# Bounded validation sets
_ALLOWED_RESOURCE_TYPES = (
    RESOURCE_TREASURY,
    RESOURCE_PROTOCOL_PARAMETER,
    RESOURCE_POLICY,
    RESOURCE_GRANT_POOL,
    RESOURCE_INCENTIVE_BUDGET,
    RESOURCE_OTHER,
)

_ALLOWED_EVIDENCE_CLASSES = (
    EC_OFFICIAL_GOVERNANCE,
    EC_OFFICIAL_DOCUMENTATION,
    EC_OFFICIAL_TREASURY,
    EC_FINALIZED_DECISION,
    EC_GOVERNANCE_DISCUSSION,
    EC_IMPLEMENTATION_SPEC,
    EC_AUDIT,
    EC_THIRD_PARTY_ANALYSIS,
)


# =========================================================================
# Deterministic helpers (module-level, pure functions)
# =========================================================================

def _reject_newline(value: str, label: str) -> None:
    if "\n" in value or "\r" in value:
        raise gl.vm.UserError("newline forbidden in " + label)


def _check_len(value: str, min_len: int, max_len: int, label: str) -> None:
    n = len(value)
    if n < min_len or n > max_len:
        raise gl.vm.UserError("length out of bounds: " + label)


def _hex_of(b: bytes) -> str:
    # Deterministic lowercase hex; stable across runtimes.
    return b.hex()


def _normalize_url(url: str) -> str:
    # Case-insensitive scheme+host normalization + trailing-slash strip.
    # Deliberately does not touch query strings, fragments, or ports.
    lowered = url.strip().lower()
    if lowered.endswith("/"):
        lowered = lowered[:-1]
    return lowered


def _extract_host(url: str) -> str:
    lowered = url.lower().strip()
    if "://" in lowered:
        rest = lowered.split("://", 1)[1]
    else:
        rest = lowered
    for sep in ("/", "?", "#"):
        if sep in rest:
            rest = rest.split(sep, 1)[0]
    if ":" in rest:
        rest = rest.split(":", 1)[0]
    if len(rest) > MAX_NORMALIZED_SOURCE_LEN:
        rest = rest[:MAX_NORMALIZED_SOURCE_LEN]
    return rest


def _canonicalize_root(
    dao_id_int: int,
    external_proposal_id: str,
    title: str,
    proposal_url: str,
    params_sorted: list,
) -> bytes:
    # Domain-separated canonical byte encoding of the imported root data.
    # See docs/STAGE_2_SCHEMA_AND_ABI.md sec 17.1. All string fields are
    # newline-rejected by the caller before this function runs, so the
    # newline delimiters below are unambiguous.
    buf = b"gf-root/v1\n"
    buf = buf + b"dao_id=" + str(dao_id_int).encode("ascii") + b"\n"
    buf = buf + b"external_proposal_id=" + external_proposal_id.encode("utf-8") + b"\n"
    buf = buf + b"title=" + title.encode("utf-8") + b"\n"
    buf = buf + b"proposal_url=" + proposal_url.encode("utf-8") + b"\n"
    buf = buf + b"structured_parameters=\n"
    for kv in params_sorted:
        buf = buf + b"  " + kv.key.encode("utf-8") + b"=" + kv.value.encode("utf-8") + b"\n"
    return buf


def _sha256(buf: bytes) -> bytes:
    return hashlib.sha256(buf).digest()


def _paginate_ids(items, cursor_int: int, limit_int: int):
    if limit_int <= 0:
        limit_int = 1
    if limit_int > PAGINATION_LIMIT_MAX:
        limit_int = PAGINATION_LIMIT_MAX
    n = len(items)
    if cursor_int >= n or cursor_int < 0:
        return [], 0
    end = cursor_int + limit_int
    if end >= n:
        return list(items[cursor_int:n]), 0
    return list(items[cursor_int:end]), end


# =========================================================================
# Deterministic fork machinery (Stage 4). Pure helpers only.
# =========================================================================

_ALLOWED_CLAIM_KINDS = (
    CLAIM_NARROWED,
    CLAIM_BROADENED,
    CLAIM_RESHAPED,
    CLAIM_REMOVED,
    CLAIM_ADDED,
)


def _params_to_dict(params):
    out = {}
    for kv in params:
        out[kv.key] = kv.value
    return out


def _validate_delta_entries(delta, envelope):
    n = len(delta)
    if n < 1:
        raise gl.vm.UserError("EMPTY_DELTA")
    if n > MAX_DELTA_ENTRIES:
        raise gl.vm.UserError("MAX_DELTA_ENTRIES exceeded")
    mutable_set = {}
    immutable_set = {}
    for d in envelope.mutable_dimensions:
        mutable_set[d] = True
    for d in envelope.immutable_dimensions:
        immutable_set[d] = True
    seen = {}
    for entry in delta:
        _check_len(entry.dimension_name, 1, MAX_DIMENSION_NAME_LEN, "delta.dimension_name")
        _check_len(entry.parent_value, 0, MAX_DELTA_VALUE_LEN, "delta.parent_value")
        _check_len(entry.fork_value, 0, MAX_DELTA_VALUE_LEN, "delta.fork_value")
        _reject_newline(entry.dimension_name, "delta.dimension_name")
        _reject_newline(entry.parent_value, "delta.parent_value")
        _reject_newline(entry.fork_value, "delta.fork_value")
        ck_ok = False
        for c in _ALLOWED_CLAIM_KINDS:
            if entry.claim_kind == c:
                ck_ok = True
        if not ck_ok:
            raise gl.vm.UserError("INVALID_CLAIM_KIND: " + str(entry.claim_kind))
        if entry.dimension_name in seen:
            raise gl.vm.UserError("DUPLICATE_DELTA_DIMENSION: " + entry.dimension_name)
        seen[entry.dimension_name] = True
        if entry.dimension_name in immutable_set:
            raise gl.vm.UserError("IMMUTABLE_DIMENSION_MUTATION: " + entry.dimension_name)
        if entry.dimension_name not in mutable_set:
            raise gl.vm.UserError("DIMENSION_NOT_IN_ENVELOPE: " + entry.dimension_name)


def _apply_delta(parent_params_dict, delta):
    # Returns (resulting_params_dict, prose_dim_names_set).
    # Assumes _validate_delta_entries has already passed.
    resulting = {}
    for k in parent_params_dict:
        resulting[k] = parent_params_dict[k]
    prose = {}
    for entry in delta:
        dim = entry.dimension_name
        ck = entry.claim_kind
        if dim in parent_params_dict:
            # Structured mutation
            if ck == CLAIM_ADDED:
                raise gl.vm.UserError("ADDED_DIMENSION_ALREADY_EXISTS: " + dim)
            if entry.parent_value != parent_params_dict[dim]:
                raise gl.vm.UserError("PARENT_VALUE_MISMATCH: " + dim)
            if ck == CLAIM_REMOVED:
                del resulting[dim]
            else:
                resulting[dim] = entry.fork_value
        else:
            # Prose (dimension not in parent structured_parameters)
            if ck == CLAIM_REMOVED:
                raise gl.vm.UserError("CANNOT_REMOVE_PROSE_DIMENSION: " + dim)
            if ck == CLAIM_ADDED:
                if entry.parent_value != "":
                    raise gl.vm.UserError("ADDED_PROSE_PARENT_MUST_BE_EMPTY: " + dim)
                resulting[dim] = entry.fork_value
            else:
                # Prose reshape/narrow/broaden. No structural effect; parent
                # value is the caller's claim about prior prose state and is
                # not verified against stored data.
                prose[dim] = True
    return resulting, prose


def _check_body_matches_computed(body_params, computed_params_dict):
    got = _params_to_dict(body_params)
    if len(got) != len(computed_params_dict):
        raise gl.vm.UserError("UNCLAIMED_MUTATION: parameter count differs")
    for k in got:
        if k not in computed_params_dict:
            raise gl.vm.UserError("UNCLAIMED_MUTATION: unexpected key " + k)
        if got[k] != computed_params_dict[k]:
            raise gl.vm.UserError("UNCLAIMED_MUTATION: value differs at " + k)


def _canonicalize_delta(
    dao_id_int,
    root_id_int,
    parent_kind,
    parent_id_int,
    parent_fingerprint,
    delta,
):
    # Sort deltas by dimension_name ascending.
    sorted_delta = sorted(list(delta), key=lambda d: d.dimension_name)
    buf = b"gf-delta/v1\n"
    buf = buf + b"dao_id=" + str(dao_id_int).encode("ascii") + b"\n"
    buf = buf + b"root_id=" + str(root_id_int).encode("ascii") + b"\n"
    buf = buf + b"parent_kind=" + parent_kind.encode("ascii") + b"\n"
    buf = buf + b"parent_id=" + str(parent_id_int).encode("ascii") + b"\n"
    buf = buf + b"parent_fingerprint=" + _hex_of(parent_fingerprint).encode("ascii") + b"\n"
    buf = buf + b"deltas=\n"
    for entry in sorted_delta:
        buf = buf + b"  d:" + entry.dimension_name.encode("utf-8") + b"\n"
        buf = buf + b"  k:" + entry.claim_kind.encode("ascii") + b"\n"
        buf = buf + b"  p:" + entry.parent_value.encode("utf-8") + b"\n"
        buf = buf + b"  f:" + entry.fork_value.encode("utf-8") + b"\n"
    return buf


def _canonicalize_fork_body(
    dao_id_int,
    root_id_int,
    parent_kind,
    parent_id_int,
    title,
    summary,
    reasoning,
    body_params,
):
    sorted_params = sorted(list(body_params), key=lambda kv: kv.key)
    buf = b"gf-fork-body/v1\n"
    buf = buf + b"dao_id=" + str(dao_id_int).encode("ascii") + b"\n"
    buf = buf + b"root_id=" + str(root_id_int).encode("ascii") + b"\n"
    buf = buf + b"parent_kind=" + parent_kind.encode("ascii") + b"\n"
    buf = buf + b"parent_id=" + str(parent_id_int).encode("ascii") + b"\n"
    buf = buf + b"title=" + title.encode("utf-8") + b"\n"
    buf = buf + b"summary=" + summary.encode("utf-8") + b"\n"
    buf = buf + b"reasoning=" + reasoning.encode("utf-8") + b"\n"
    buf = buf + b"structured_parameters=\n"
    for kv in sorted_params:
        buf = buf + b"  " + kv.key.encode("utf-8") + b"=" + kv.value.encode("utf-8") + b"\n"
    return buf


def _delta_fingerprint(dao_id_int, root_id_int, parent_kind, parent_id_int,
                      parent_fingerprint, delta):
    return _sha256(
        _canonicalize_delta(
            dao_id_int, root_id_int, parent_kind, parent_id_int,
            parent_fingerprint, delta,
        )
    )


def _body_fingerprint(dao_id_int, root_id_int, parent_kind, parent_id_int,
                     title, summary, reasoning, body_params):
    return _sha256(
        _canonicalize_fork_body(
            dao_id_int, root_id_int, parent_kind, parent_id_int,
            title, summary, reasoning, body_params,
        )
    )


# =========================================================================
# Data structures (bounded records)
# =========================================================================

@allow_storage
@dataclass
class ParamKV:
    key: str
    value: str


@allow_storage
@dataclass
class Dao:
    name: str
    url: str
    importer: Address
    imported_at: u256


@allow_storage
@dataclass
class IntentEnvelope:
    objective: str
    beneficiary_class: str
    resource_type: str
    scope: str
    essential_constraints: DynArray[str]
    mutable_dimensions: DynArray[str]
    immutable_dimensions: DynArray[str]
    parent_proposal_fingerprint: bytes
    envelope_version: u32


@allow_storage
@dataclass
class RootProposal:
    dao_id: u256
    external_proposal_id: str
    title: str
    proposal_url: str
    proposer: Address
    # Deterministic hash of the canonicalized submitted root data.
    # Populated at Stage 3 on import. Never empty after successful import.
    import_fingerprint: bytes
    # Hash of the rendered authoritative page fetched via the approved
    # GenLayer web-content pathway (see docs, Stage 6). Populated by the
    # evidence-freeze routine. Empty at import.
    web_content_fingerprint: bytes
    structured_parameters: DynArray[ParamKV]
    envelope: IntentEnvelope
    envelope_status: str
    envelope_case_id: u256
    identity_status: str
    imported_at: u256


@allow_storage
@dataclass
class DeltaEntry:
    dimension_name: str
    parent_value: str
    fork_value: str
    claim_kind: str


@allow_storage
@dataclass
class ForkBody:
    title: str
    summary: str
    structured_parameters: DynArray[ParamKV]
    reasoning: str


@allow_storage
@dataclass
class Fork:
    parent_id: u256
    parent_kind: str
    root_id: u256
    dao_id: u256
    creator: Address
    depth: u32
    body: ForkBody
    delta: DynArray[DeltaEntry]
    status: str
    body_fingerprint: bytes
    delta_fingerprint: bytes
    # Immutable snapshot of the parent's authoritative fingerprint at fork
    # creation time. For PARENT_ROOT -> root.import_fingerprint; for
    # PARENT_FORK -> parent_fork.body_fingerprint.
    parent_fingerprint: bytes
    evidence_case_id: u256
    current_verdict_id: u256
    child_count: u32
    created_at: u256
    creator_bond_id: u256


@allow_storage
@dataclass
class Evidence:
    case_id: u256
    submitter: Address
    url: str
    normalized_source: str
    evidence_class: str
    relevance_claim: str
    authority_claim: str
    temporal_marker: str
    content_fingerprint: bytes
    submitted_at: u256
    frozen: bool


@allow_storage
@dataclass
class Case:
    case_type: str
    target_id: u256
    target_kind: str
    target_fingerprint: bytes
    evidence_ids: DynArray[u256]
    evidence_set_fingerprint: bytes
    adjudication_dimensions_version: u32
    case_fingerprint: bytes
    state: str
    retry_count: u32
    last_attempt_at: u256


@allow_storage
@dataclass
class DimensionFinding:
    name: str
    finding: str
    reasoning: str


@allow_storage
@dataclass
class VerdictRecord:
    case_id: u256
    target_id: u256
    target_kind: str
    verdict: str
    dimensions: DynArray[DimensionFinding]
    evidence_refs: DynArray[u256]
    reason_codes: DynArray[str]
    reasoning_hash: bytes
    replaced_by: u256
    created_at: u256


@allow_storage
@dataclass
class Challenge:
    target_id: u256
    target_kind: str
    challenger: Address
    ground_code: str
    argument: str
    case_id: u256
    original_verdict_id: u256
    replacement_verdict_id: u256
    status: str
    bond_id: u256
    opened_at: u256


@allow_storage
@dataclass
class Bond:
    owner: Address
    amount: u256
    target_id: u256
    target_kind: str
    purpose: str
    settlement_kind: str
    settled: bool
    settled_at: u256


@allow_storage
@dataclass
class PageIds:
    items: DynArray[u256]
    next_cursor: u256


@allow_storage
@dataclass
class ConstantsView:
    max_daos: u32
    max_roots_per_dao: u32
    max_forks_per_root: u32
    max_children_per_parent: u32
    max_depth_per_root: u32
    max_evidence_per_case: u32
    max_challenges_per_target: u32
    max_evidence_slice: u32
    pagination_limit_max: u32
    max_delta_entries: u32
    fork_creation_bond: u256
    envelope_bond: u256
    challenge_bond: u256
    challenge_window_seconds: u32
    retry_cooldown_seconds: u32
    max_retries_per_case: u32
    treasury_addr: Address
    paused: bool


# =========================================================================
# Contract
# =========================================================================

class Contract(gl.Contract):
    # Config
    treasury_addr: Address
    paused: bool

    # Entities
    daos: TreeMap[u256, Dao]
    roots: TreeMap[u256, RootProposal]
    forks: TreeMap[u256, Fork]
    evidence: TreeMap[u256, Evidence]
    cases: TreeMap[u256, Case]
    verdicts: TreeMap[u256, VerdictRecord]
    challenges: TreeMap[u256, Challenge]
    bonds: TreeMap[u256, Bond]

    # Indexes for bounded tree walks
    roots_by_dao: TreeMap[u256, DynArray[u256]]
    forks_by_root: TreeMap[u256, DynArray[u256]]
    forks_by_parent: TreeMap[u256, DynArray[u256]]
    evidence_by_case: TreeMap[u256, DynArray[u256]]
    verdicts_by_fork: TreeMap[u256, DynArray[u256]]
    verdicts_by_root: TreeMap[u256, DynArray[u256]]
    challenges_by_fork: TreeMap[u256, DynArray[u256]]
    challenges_by_root: TreeMap[u256, DynArray[u256]]

    # Global uniqueness index for root import canonical form.
    # key = lowercase hex of RootProposal.import_fingerprint, value = root_id.
    # Enforces "exact duplicate imported root proposals rejected" at import.
    import_fingerprint_index: TreeMap[str, u256]

    # Monotonic ID counters
    next_dao_id: u256
    next_root_id: u256
    next_fork_id: u256
    next_evidence_id: u256
    next_case_id: u256
    next_verdict_id: u256
    next_challenge_id: u256
    next_bond_id: u256

    def __init__(self, treasury_addr: Address):
        self.treasury_addr = treasury_addr
        self.paused = False
        self.next_dao_id = u256(1)
        self.next_root_id = u256(1)
        self.next_fork_id = u256(1)
        self.next_evidence_id = u256(1)
        self.next_case_id = u256(1)
        self.next_verdict_id = u256(1)
        self.next_challenge_id = u256(1)
        self.next_bond_id = u256(1)

    # ---------------------------------------------------------------------
    # Admin (minimal skeleton; withdrawal-safe pause behavior is Stage 11)
    # ---------------------------------------------------------------------

    @gl.public.write
    def pause(self) -> None:
        if gl.message.sender_address != self.treasury_addr:
            raise gl.vm.UserError("only treasury can pause")
        self.paused = True

    @gl.public.write
    def unpause(self) -> None:
        if gl.message.sender_address != self.treasury_addr:
            raise gl.vm.UserError("only treasury can unpause")
        self.paused = False

    # ---------------------------------------------------------------------
    # Write ABI (Stage 2: signatures only; bodies raise UserError)
    # ---------------------------------------------------------------------

    @gl.public.write
    def register_dao(self, name: str, url: str) -> u256:
        if self.paused:
            raise gl.vm.UserError("paused")
        _check_len(name, 1, MAX_DAO_NAME_LEN, "dao.name")
        _check_len(url, 1, MAX_URL_LEN, "dao.url")
        _reject_newline(name, "dao.name")
        _reject_newline(url, "dao.url")
        if int(self.next_dao_id) > MAX_DAOS:
            raise gl.vm.UserError("MAX_DAOS reached")
        dao_id = self.next_dao_id
        self.daos[dao_id] = Dao(
            name=name,
            url=url,
            importer=gl.message.sender_address,
            imported_at=u256(0),
        )
        self.next_dao_id = u256(int(dao_id) + 1)
        return dao_id

    @gl.public.write
    def import_root_proposal(
        self,
        dao_id: u256,
        external_proposal_id: str,
        title: str,
        proposal_url: str,
        structured_parameters: DynArray[ParamKV],
    ) -> u256:
        if self.paused:
            raise gl.vm.UserError("paused")
        # Bounds
        _check_len(external_proposal_id, 1, MAX_EXTERNAL_ID_LEN, "external_proposal_id")
        _check_len(title, 1, MAX_TITLE_LEN, "title")
        _check_len(proposal_url, 1, MAX_URL_LEN, "proposal_url")
        _reject_newline(external_proposal_id, "external_proposal_id")
        _reject_newline(title, "title")
        _reject_newline(proposal_url, "proposal_url")
        # DAO must exist
        if dao_id not in self.daos:
            raise gl.vm.UserError("dao not found")
        # Per-DAO root cap
        if dao_id in self.roots_by_dao:
            existing = self.roots_by_dao[dao_id]
            if len(existing) >= MAX_ROOTS_PER_DAO:
                raise gl.vm.UserError("MAX_ROOTS_PER_DAO reached")
        # Structured parameter validation
        n_params = len(structured_parameters)
        if n_params > MAX_STRUCTURED_PARAMS:
            raise gl.vm.UserError("MAX_STRUCTURED_PARAMS exceeded")
        seen_keys = {}
        for kv in structured_parameters:
            _check_len(kv.key, 1, MAX_KV_KEY_LEN, "param.key")
            _check_len(kv.value, 0, MAX_KV_VAL_LEN, "param.value")
            _reject_newline(kv.key, "param.key")
            _reject_newline(kv.value, "param.value")
            if kv.key in seen_keys:
                raise gl.vm.UserError("duplicate structured parameter key")
            seen_keys[kv.key] = True
        # Canonical form + fingerprint
        params_sorted = sorted(list(structured_parameters), key=lambda kv: kv.key)
        canonical = _canonicalize_root(
            int(dao_id),
            external_proposal_id,
            title,
            proposal_url,
            params_sorted,
        )
        fp = _sha256(canonical)
        fp_hex = _hex_of(fp)
        # Global uniqueness on canonical form (dao_id is part of the canonical
        # bytes, so global uniqueness implies per-DAO uniqueness).
        if fp_hex in self.import_fingerprint_index:
            raise gl.vm.UserError("duplicate root import (canonical form already imported)")
        # Allocate and write
        root_id = self.next_root_id
        empty_envelope = IntentEnvelope(
            objective="",
            beneficiary_class="",
            resource_type="",
            scope="",
            essential_constraints=DynArray[str](),
            mutable_dimensions=DynArray[str](),
            immutable_dimensions=DynArray[str](),
            parent_proposal_fingerprint=b"",
            envelope_version=u32(0),
        )
        # Store the original submitted parameter order (before canonical sort);
        # canonicalization is a fingerprint concern only.
        self.roots[root_id] = RootProposal(
            dao_id=dao_id,
            external_proposal_id=external_proposal_id,
            title=title,
            proposal_url=proposal_url,
            proposer=gl.message.sender_address,
            import_fingerprint=fp,
            web_content_fingerprint=b"",
            structured_parameters=structured_parameters,
            envelope=empty_envelope,
            envelope_status=ENVELOPE_NOT_SUBMITTED,
            envelope_case_id=u256(0),
            identity_status=IDENTITY_COMMUNITY_IMPORTED,
            imported_at=u256(0),
        )
        if dao_id not in self.roots_by_dao:
            self.roots_by_dao[dao_id] = DynArray[u256]()
        self.roots_by_dao[dao_id].append(root_id)
        self.import_fingerprint_index[fp_hex] = root_id
        self.next_root_id = u256(int(root_id) + 1)
        return root_id

    @gl.public.write.payable
    def submit_root_envelope(
        self,
        root_id: u256,
        envelope: IntentEnvelope,
        evidence_urls: DynArray[str],
        evidence_classes: DynArray[str],
        relevance_claims: DynArray[str],
        authority_claims: DynArray[str],
        temporal_markers: DynArray[str],
    ) -> u256:
        # Stage 3 does NOT read the incoming native-GEN value. Bond capture
        # is Stage 10. The payable signature is exposed for ABI stability.
        if self.paused:
            raise gl.vm.UserError("paused")
        if root_id not in self.roots:
            raise gl.vm.UserError("root not found")
        root = self.roots[root_id]
        # One-active-envelope rule
        if root.envelope_status != ENVELOPE_NOT_SUBMITTED:
            raise gl.vm.UserError("envelope already active")
        # Envelope structural validation
        _check_len(envelope.objective, 1, MAX_OBJECTIVE_LEN, "envelope.objective")
        _check_len(envelope.beneficiary_class, 1, MAX_BENEFICIARY_CLASS_LEN, "envelope.beneficiary_class")
        _check_len(envelope.scope, 0, MAX_SCOPE_LEN, "envelope.scope")
        _reject_newline(envelope.objective, "envelope.objective")
        _reject_newline(envelope.beneficiary_class, "envelope.beneficiary_class")
        _reject_newline(envelope.scope, "envelope.scope")
        # Resource type must be in bounded set
        rt_ok = False
        for rt in _ALLOWED_RESOURCE_TYPES:
            if envelope.resource_type == rt:
                rt_ok = True
        if not rt_ok:
            raise gl.vm.UserError("envelope.resource_type out of range")
        # Essential constraints
        n_ec = len(envelope.essential_constraints)
        if n_ec > MAX_ESSENTIAL_CONSTRAINT_ITEMS:
            raise gl.vm.UserError("MAX_ESSENTIAL_CONSTRAINT_ITEMS exceeded")
        seen_ec = {}
        for c in envelope.essential_constraints:
            _check_len(c, 1, MAX_ESSENTIAL_CONSTRAINT_LEN, "essential_constraint")
            _reject_newline(c, "essential_constraint")
            if c in seen_ec:
                raise gl.vm.UserError("duplicate essential_constraint")
            seen_ec[c] = True
        # Dimension sets
        n_md = len(envelope.mutable_dimensions)
        n_id_ = len(envelope.immutable_dimensions)
        if n_md > MAX_MUTABLE_DIMENSIONS:
            raise gl.vm.UserError("MAX_MUTABLE_DIMENSIONS exceeded")
        if n_id_ > MAX_IMMUTABLE_DIMENSIONS:
            raise gl.vm.UserError("MAX_IMMUTABLE_DIMENSIONS exceeded")
        seen_md = {}
        for d in envelope.mutable_dimensions:
            _check_len(d, 1, MAX_DIMENSION_NAME_LEN, "mutable_dimension")
            _reject_newline(d, "mutable_dimension")
            if d in seen_md:
                raise gl.vm.UserError("duplicate mutable_dimension")
            seen_md[d] = True
        for d in envelope.immutable_dimensions:
            _check_len(d, 1, MAX_DIMENSION_NAME_LEN, "immutable_dimension")
            _reject_newline(d, "immutable_dimension")
            if d in seen_md:
                raise gl.vm.UserError("dimension in both mutable and immutable sets")
        seen_id = {}
        for d in envelope.immutable_dimensions:
            if d in seen_id:
                raise gl.vm.UserError("duplicate immutable_dimension")
            seen_id[d] = True
        # Evidence arrays: parallel; all must have the same length
        n_evi = len(evidence_urls)
        if n_evi < 1:
            raise gl.vm.UserError("at least one evidence required")
        if n_evi > MAX_EVIDENCE_PER_CASE:
            raise gl.vm.UserError("MAX_EVIDENCE_PER_CASE exceeded")
        if (
            len(evidence_classes) != n_evi
            or len(relevance_claims) != n_evi
            or len(authority_claims) != n_evi
            or len(temporal_markers) != n_evi
        ):
            raise gl.vm.UserError("evidence arrays must have equal length")
        # Per-evidence validation + normalized-URL dedup within this case
        seen_norm = {}
        for i in range(n_evi):
            url = evidence_urls[i]
            ec = evidence_classes[i]
            rc = relevance_claims[i]
            ac = authority_claims[i]
            tm = temporal_markers[i]
            _check_len(url, 1, MAX_URL_LEN, "evidence.url")
            _reject_newline(url, "evidence.url")
            _check_len(rc, 0, MAX_RELEVANCE_CLAIM_LEN, "evidence.relevance_claim")
            _reject_newline(rc, "evidence.relevance_claim")
            _check_len(ac, 0, MAX_AUTHORITY_CLAIM_LEN, "evidence.authority_claim")
            _reject_newline(ac, "evidence.authority_claim")
            _check_len(tm, 0, MAX_TEMPORAL_MARKER_LEN, "evidence.temporal_marker")
            _reject_newline(tm, "evidence.temporal_marker")
            ec_ok = False
            for allowed in _ALLOWED_EVIDENCE_CLASSES:
                if ec == allowed:
                    ec_ok = True
            if not ec_ok:
                raise gl.vm.UserError("evidence_class out of range")
            norm = _normalize_url(url)
            if norm in seen_norm:
                raise gl.vm.UserError("duplicate normalized evidence URL in case")
            seen_norm[norm] = True
        # All validation passed. Bind envelope's parent_proposal_fingerprint
        # server-side to the root's own import_fingerprint; do not trust the
        # caller-supplied field.
        bound_envelope = IntentEnvelope(
            objective=envelope.objective,
            beneficiary_class=envelope.beneficiary_class,
            resource_type=envelope.resource_type,
            scope=envelope.scope,
            essential_constraints=envelope.essential_constraints,
            mutable_dimensions=envelope.mutable_dimensions,
            immutable_dimensions=envelope.immutable_dimensions,
            parent_proposal_fingerprint=root.import_fingerprint,
            envelope_version=u32(1),
        )
        # Allocate case
        case_id = self.next_case_id
        self.next_case_id = u256(int(case_id) + 1)
        evidence_ids = DynArray[u256]()
        # Allocate evidence records
        for i in range(n_evi):
            evidence_id = self.next_evidence_id
            self.next_evidence_id = u256(int(evidence_id) + 1)
            self.evidence[evidence_id] = Evidence(
                case_id=case_id,
                submitter=gl.message.sender_address,
                url=evidence_urls[i],
                normalized_source=_extract_host(evidence_urls[i]),
                evidence_class=evidence_classes[i],
                relevance_claim=relevance_claims[i],
                authority_claim=authority_claims[i],
                temporal_marker=temporal_markers[i],
                content_fingerprint=b"",
                submitted_at=u256(0),
                frozen=False,
            )
            evidence_ids.append(evidence_id)
        if case_id not in self.evidence_by_case:
            self.evidence_by_case[case_id] = DynArray[u256]()
        for eid in evidence_ids:
            self.evidence_by_case[case_id].append(eid)
        # Write the case
        self.cases[case_id] = Case(
            case_type=CASE_TYPE_ROOT_ENVELOPE,
            target_id=root_id,
            target_kind=TARGET_KIND_ROOT_ENVELOPE,
            target_fingerprint=root.import_fingerprint,
            evidence_ids=evidence_ids,
            evidence_set_fingerprint=b"",
            adjudication_dimensions_version=u32(ADJUDICATION_DIMENSIONS_VERSION_ROOT_ENVELOPE),
            case_fingerprint=b"",
            state=CASE_OPEN,
            retry_count=u32(0),
            last_attempt_at=u256(0),
        )
        # Update root
        self.roots[root_id] = RootProposal(
            dao_id=root.dao_id,
            external_proposal_id=root.external_proposal_id,
            title=root.title,
            proposal_url=root.proposal_url,
            proposer=root.proposer,
            import_fingerprint=root.import_fingerprint,
            web_content_fingerprint=root.web_content_fingerprint,
            structured_parameters=root.structured_parameters,
            envelope=bound_envelope,
            envelope_status=ENVELOPE_EVIDENCE_OPEN,
            envelope_case_id=case_id,
            identity_status=root.identity_status,
            imported_at=root.imported_at,
        )
        return case_id

    @gl.public.write.payable
    def create_fork(
        self,
        parent_id: u256,
        parent_kind: str,
        parent_fingerprint: bytes,
        delta: DynArray[DeltaEntry],
        body: ForkBody,
    ) -> u256:
        # Stage 4: payable ABI kept for stability. Stage 4 body does NOT
        # read the incoming native-GEN value. Bond capture is Stage 10.
        if self.paused:
            raise gl.vm.UserError("paused")
        # Resolve parent + eligibility. The FAITHFUL gate is the FIRST
        # check on the parent's authority. There is no bypass.
        if parent_kind == PARENT_KIND_ROOT:
            if parent_id not in self.roots:
                raise gl.vm.UserError("root not found")
            root = self.roots[parent_id]
            # HARD RULE: only ENVELOPE_FAITHFUL may authorize fork creation.
            # ENVELOPE_NOT_SUBMITTED, ENVELOPE_EVIDENCE_OPEN,
            # ENVELOPE_EVIDENCE_FROZEN, ENVELOPE_ADJUDICATING,
            # ENVELOPE_REJECTED, ENVELOPE_UNCLEAR all refuse. No production
            # bypass exists.
            if root.envelope_status != ENVELOPE_FAITHFUL:
                raise gl.vm.UserError("root intent envelope not finalized faithful")
            resolved_root_id = parent_id
            resolved_dao_id = root.dao_id
            resolved_parent_depth = 0
            expected_parent_fp = root.import_fingerprint
            parent_params = root.structured_parameters
            parent_envelope = root.envelope
        elif parent_kind == PARENT_KIND_FORK:
            if parent_id not in self.forks:
                raise gl.vm.UserError("parent fork not found")
            pf = self.forks[parent_id]
            if pf.status != FORK_FINALIZED_FAITHFUL:
                raise gl.vm.UserError("parent fork not finalized faithful")
            resolved_root_id = pf.root_id
            resolved_dao_id = pf.dao_id
            resolved_parent_depth = int(pf.depth)
            expected_parent_fp = pf.body_fingerprint
            parent_params = pf.body.structured_parameters
            # The parent's envelope is the root's envelope; every fork
            # under a root is bound to the same envelope.
            parent_envelope = self.roots[pf.root_id].envelope
        else:
            raise gl.vm.UserError("invalid parent_kind")
        if parent_fingerprint != expected_parent_fp:
            raise gl.vm.UserError("parent_fingerprint mismatch (stale parent?)")
        # Depth cap
        new_depth = resolved_parent_depth + 1
        if new_depth > MAX_DEPTH_PER_ROOT:
            raise gl.vm.UserError("MAX_DEPTH_PER_ROOT exceeded")
        # Per-parent children cap
        if parent_id in self.forks_by_parent:
            if len(self.forks_by_parent[parent_id]) >= MAX_CHILDREN_PER_PARENT:
                raise gl.vm.UserError("MAX_CHILDREN_PER_PARENT reached")
        # Per-root total fork cap
        if resolved_root_id in self.forks_by_root:
            if len(self.forks_by_root[resolved_root_id]) >= MAX_FORKS_PER_ROOT:
                raise gl.vm.UserError("MAX_FORKS_PER_ROOT reached")
        # Body bounds
        _check_len(body.title, 1, MAX_TITLE_LEN, "body.title")
        _check_len(body.summary, 0, MAX_REASONING_LEN, "body.summary")
        _check_len(body.reasoning, 0, MAX_REASONING_LEN, "body.reasoning")
        _reject_newline(body.title, "body.title")
        _reject_newline(body.summary, "body.summary")
        _reject_newline(body.reasoning, "body.reasoning")
        # Body structured_parameters bounds (per-KV)
        n_body_params = len(body.structured_parameters)
        if n_body_params > MAX_STRUCTURED_PARAMS:
            raise gl.vm.UserError("MAX_STRUCTURED_PARAMS exceeded")
        seen_body_keys = {}
        for kv in body.structured_parameters:
            _check_len(kv.key, 1, MAX_KV_KEY_LEN, "body.param.key")
            _check_len(kv.value, 0, MAX_KV_VAL_LEN, "body.param.value")
            _reject_newline(kv.key, "body.param.key")
            _reject_newline(kv.value, "body.param.value")
            if kv.key in seen_body_keys:
                raise gl.vm.UserError("duplicate structured parameter key in body")
            seen_body_keys[kv.key] = True
        # Delta structural validation
        _validate_delta_entries(delta, parent_envelope)
        # Deterministic delta application
        parent_dict = _params_to_dict(parent_params)
        computed_params, _prose = _apply_delta(parent_dict, delta)
        # Enforce no undeclared mutation
        _check_body_matches_computed(body.structured_parameters, computed_params)
        # Fingerprints
        delta_fp = _delta_fingerprint(
            int(resolved_dao_id),
            int(resolved_root_id),
            parent_kind,
            int(parent_id),
            parent_fingerprint,
            delta,
        )
        body_fp = _body_fingerprint(
            int(resolved_dao_id),
            int(resolved_root_id),
            parent_kind,
            int(parent_id),
            body.title,
            body.summary,
            body.reasoning,
            body.structured_parameters,
        )
        # Allocate + write
        fork_id = self.next_fork_id
        self.next_fork_id = u256(int(fork_id) + 1)
        self.forks[fork_id] = Fork(
            parent_id=parent_id,
            parent_kind=parent_kind,
            root_id=resolved_root_id,
            dao_id=resolved_dao_id,
            creator=gl.message.sender_address,
            depth=u32(new_depth),
            body=body,
            delta=delta,
            status=FORK_DRAFT,
            body_fingerprint=body_fp,
            delta_fingerprint=delta_fp,
            parent_fingerprint=parent_fingerprint,
            evidence_case_id=u256(0),
            current_verdict_id=u256(0),
            child_count=u32(0),
            created_at=u256(0),
            creator_bond_id=u256(0),
        )
        if resolved_root_id not in self.forks_by_root:
            self.forks_by_root[resolved_root_id] = DynArray[u256]()
        self.forks_by_root[resolved_root_id].append(fork_id)
        if parent_id not in self.forks_by_parent:
            self.forks_by_parent[parent_id] = DynArray[u256]()
        self.forks_by_parent[parent_id].append(fork_id)
        # Increment parent's child_count if parent is a fork
        if parent_kind == PARENT_KIND_FORK:
            pf = self.forks[parent_id]
            self.forks[parent_id] = Fork(
                parent_id=pf.parent_id,
                parent_kind=pf.parent_kind,
                root_id=pf.root_id,
                dao_id=pf.dao_id,
                creator=pf.creator,
                depth=pf.depth,
                body=pf.body,
                delta=pf.delta,
                status=pf.status,
                body_fingerprint=pf.body_fingerprint,
                delta_fingerprint=pf.delta_fingerprint,
                parent_fingerprint=pf.parent_fingerprint,
                evidence_case_id=pf.evidence_case_id,
                current_verdict_id=pf.current_verdict_id,
                child_count=u32(int(pf.child_count) + 1),
                created_at=pf.created_at,
                creator_bond_id=pf.creator_bond_id,
            )
        return fork_id

    @gl.public.write
    def submit_fork_evidence(
        self,
        fork_id: u256,
        evidence_urls: DynArray[str],
        evidence_classes: DynArray[str],
        relevance_claims: DynArray[str],
        authority_claims: DynArray[str],
        temporal_markers: DynArray[str],
    ) -> u256:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.write
    def freeze_evidence(self, evidence_id: u256) -> None:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.write
    def freeze_case(self, case_id: u256) -> None:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.write
    def adjudicate(self, case_id: u256) -> None:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.write.payable
    def challenge_verdict(
        self,
        target_id: u256,
        target_kind: str,
        ground_code: str,
        argument: str,
    ) -> u256:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.write
    def finalize(self, target_id: u256, target_kind: str) -> None:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.write
    def settle_bond(self, bond_id: u256) -> None:
        raise gl.vm.UserError("stage-2: not implemented")

    # ---------------------------------------------------------------------
    # View ABI (Stage 2: signatures only; bodies raise UserError)
    # ---------------------------------------------------------------------

    @gl.public.view
    def get_dao(self, dao_id: u256) -> Dao:
        if dao_id not in self.daos:
            raise gl.vm.UserError("dao not found")
        return self.daos[dao_id]

    @gl.public.view
    def list_daos(self, cursor: u256, limit: u32) -> PageIds:
        # Cursor is a dao_id starting point (dense monotonic).
        total_next = int(self.next_dao_id)
        start = int(cursor)
        if start < 1:
            start = 1
        limit_int = int(limit)
        if limit_int <= 0:
            limit_int = 1
        if limit_int > PAGINATION_LIMIT_MAX:
            limit_int = PAGINATION_LIMIT_MAX
        items = DynArray[u256]()
        i = start
        count = 0
        while i < total_next and count < limit_int:
            if u256(i) in self.daos:
                items.append(u256(i))
                count = count + 1
            i = i + 1
        next_cursor = u256(0) if i >= total_next else u256(i)
        return PageIds(items=items, next_cursor=next_cursor)

    @gl.public.view
    def get_root_proposal(self, root_id: u256) -> RootProposal:
        if root_id not in self.roots:
            raise gl.vm.UserError("root not found")
        return self.roots[root_id]

    @gl.public.view
    def list_root_proposals_by_dao(
        self, dao_id: u256, cursor: u256, limit: u32
    ) -> PageIds:
        if dao_id not in self.daos:
            raise gl.vm.UserError("dao not found")
        if dao_id not in self.roots_by_dao:
            return PageIds(items=DynArray[u256](), next_cursor=u256(0))
        arr = self.roots_by_dao[dao_id]
        picked, nxt = _paginate_ids(arr, int(cursor), int(limit))
        items = DynArray[u256]()
        for v in picked:
            items.append(v)
        return PageIds(items=items, next_cursor=u256(nxt))

    @gl.public.view
    def get_fork(self, fork_id: u256) -> Fork:
        if fork_id not in self.forks:
            raise gl.vm.UserError("fork not found")
        return self.forks[fork_id]

    @gl.public.view
    def list_forks_of_root(
        self, root_id: u256, cursor: u256, limit: u32
    ) -> PageIds:
        if root_id not in self.roots:
            raise gl.vm.UserError("root not found")
        if root_id not in self.forks_by_root:
            return PageIds(items=DynArray[u256](), next_cursor=u256(0))
        arr = self.forks_by_root[root_id]
        picked, nxt = _paginate_ids(arr, int(cursor), int(limit))
        items = DynArray[u256]()
        for v in picked:
            items.append(v)
        return PageIds(items=items, next_cursor=u256(nxt))

    @gl.public.view
    def list_forks_of_parent(
        self, parent_id: u256, cursor: u256, limit: u32
    ) -> PageIds:
        # Parent may be a root or a fork. If neither exists, error.
        if parent_id not in self.roots and parent_id not in self.forks:
            raise gl.vm.UserError("parent not found")
        if parent_id not in self.forks_by_parent:
            return PageIds(items=DynArray[u256](), next_cursor=u256(0))
        arr = self.forks_by_parent[parent_id]
        picked, nxt = _paginate_ids(arr, int(cursor), int(limit))
        items = DynArray[u256]()
        for v in picked:
            items.append(v)
        return PageIds(items=items, next_cursor=u256(nxt))

    @gl.public.view
    def get_verdict_history(
        self,
        target_id: u256,
        target_kind: str,
        cursor: u256,
        limit: u32,
    ) -> PageIds:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def get_verdict(self, verdict_id: u256) -> VerdictRecord:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def get_evidence(self, evidence_id: u256) -> Evidence:
        if evidence_id not in self.evidence:
            raise gl.vm.UserError("evidence not found")
        return self.evidence[evidence_id]

    @gl.public.view
    def list_evidence_of_case(
        self, case_id: u256, cursor: u256, limit: u32
    ) -> PageIds:
        if case_id not in self.cases:
            raise gl.vm.UserError("case not found")
        if case_id not in self.evidence_by_case:
            return PageIds(items=DynArray[u256](), next_cursor=u256(0))
        arr = self.evidence_by_case[case_id]
        picked, nxt = _paginate_ids(arr, int(cursor), int(limit))
        items = DynArray[u256]()
        for v in picked:
            items.append(v)
        return PageIds(items=items, next_cursor=u256(nxt))

    @gl.public.view
    def get_case(self, case_id: u256) -> Case:
        if case_id not in self.cases:
            raise gl.vm.UserError("case not found")
        return self.cases[case_id]

    @gl.public.view
    def get_challenge(self, challenge_id: u256) -> Challenge:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def list_challenges(
        self,
        target_id: u256,
        target_kind: str,
        cursor: u256,
        limit: u32,
    ) -> PageIds:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def get_bond(self, bond_id: u256) -> Bond:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def get_constants(self) -> ConstantsView:
        return ConstantsView(
            max_daos=u32(MAX_DAOS),
            max_roots_per_dao=u32(MAX_ROOTS_PER_DAO),
            max_forks_per_root=u32(MAX_FORKS_PER_ROOT),
            max_children_per_parent=u32(MAX_CHILDREN_PER_PARENT),
            max_depth_per_root=u32(MAX_DEPTH_PER_ROOT),
            max_evidence_per_case=u32(MAX_EVIDENCE_PER_CASE),
            max_challenges_per_target=u32(MAX_CHALLENGES_PER_TARGET),
            max_evidence_slice=u32(MAX_EVIDENCE_SLICE),
            pagination_limit_max=u32(PAGINATION_LIMIT_MAX),
            max_delta_entries=u32(MAX_DELTA_ENTRIES),
            fork_creation_bond=u256(FORK_CREATION_BOND),
            envelope_bond=u256(ENVELOPE_BOND),
            challenge_bond=u256(CHALLENGE_BOND),
            challenge_window_seconds=u32(CHALLENGE_WINDOW_SECONDS),
            retry_cooldown_seconds=u32(RETRY_COOLDOWN_SECONDS),
            max_retries_per_case=u32(MAX_RETRIES_PER_CASE),
            treasury_addr=self.treasury_addr,
            paused=self.paused,
        )
