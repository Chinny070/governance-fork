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

# Community-compatible fork-evidence quotas (Stage 5)
CREATOR_EVIDENCE_CAP = 8
COMMUNITY_EVIDENCE_CAP = 8
MAX_COMMUNITY_EVIDENCE_PER_CONTRIBUTOR = 2
MAX_EVIDENCE_BATCH = 8

ADJUDICATION_DIMENSIONS_VERSION_FORK = 1
ADJUDICATION_DIMENSIONS_VERSION_ROOT_ENVELOPE = 1

# Stage 6b: production evidence retrieval and freeze.
#
# Deterministic minimum-usefulness gate. Stage 6a observed genuinely empty
# (0-char) renders as a real, committable outcome (Accepted consensus,
# content_length=0). 32 chars is far shorter than any real sentence
# fragment; it separates "nothing useful rendered" from "something
# rendered" without risking rejection of legitimately terse evidence.
# This is a length check only -- Stage 6b makes no semantic usefulness
# judgment.
MIN_USEFUL_CONTENT_LEN = 32

# Stage 6b correction: a seal-blocking total-content cap was considered
# and REMOVED. It would have made already-immutable, successfully fetched
# evidence retroactively unsealable once the case's cumulative content
# happened to cross an arbitrary threshold -- an unrecoverable dead end no
# different in kind from the community-bricking defect this correction
# fixes. The theoretical worst case is already finite and bounded without
# any additional cap: MAX_EVIDENCE_PER_CASE (16) * MAX_EVIDENCE_SLICE
# (16384) = 262144 chars per case. Stage 7's prompt-budget concerns (if
# any) are a Stage 7 architecture problem -- bounded per-evidence excerpts,
# staged evaluation, evidence-by-evidence findings -- not a Stage 6b
# storage/freeze-integrity problem. Do not conflate the two.

# Fixed, contract-controlled wait duration for RENDER_PROFILE_DYNAMIC.
# Never caller-supplied -- Stage 6a's negative-control and instability
# findings apply to THIS exact duration; an arbitrary caller-chosen wait
# would be untested and unbounded.
DYNAMIC_WAIT_SECONDS = "5s"


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
# Stage 6b: evidence membership locked; individual fetch_evidence calls
# permitted. New state -- none of the Stage 2-reserved names meant this.
CASE_EVIDENCE_CLOSED = "EVIDENCE_CLOSED"
CASE_EVIDENCE_FROZEN = "EVIDENCE_FROZEN"  # reserved; not used as a Case.state
                                          # value by Stage 6b -- see docs.
CASE_CASE_FROZEN = "CASE_FROZEN"  # Stage 6b's seal_evidence terminal state.
CASE_ADJUDICATING = "ADJUDICATING"
CASE_SUCCESS = "SUCCESS"
CASE_UNDETERMINED = "UNDETERMINED"
CASE_UNDETERMINED_TERMINAL = "UNDETERMINED_TERMINAL"
CASE_INVALID = "INVALID"
# Stage 6b: explicit, auditable escape valve for a closed case that can
# never seal (e.g. a member evidence URL becomes permanently unavailable).
CASE_ABORTED = "ABORTED"

# Stage 6b: evidence retrieval status. Deterministic and committable only
# -- there is no "UNAVAILABLE" value here. A render() call that fails
# (WEBPAGE_LOAD_FAILED, Undetermined, or any other failure) does not let
# this contract commit any outcome for that attempt; the evidence simply
# remains RETRIEVAL_NOT_FETCHED and may be retried. See
# docs/STAGE_6B_PRODUCTION_EVIDENCE_FREEZE.md for the reasoning.
RETRIEVAL_NOT_FETCHED = "NOT_FETCHED"
RETRIEVAL_FETCHED = "FETCHED"
RETRIEVAL_UNUSABLE_SHORT = "UNUSABLE_SHORT"

# Stage 6b: bounded, contract-controlled render profiles. The submitter
# selects one of these two values only -- never an arbitrary mode, wait
# duration, or renderer option.
RENDER_PROFILE_STANDARD = "STANDARD"
RENDER_PROFILE_DYNAMIC = "DYNAMIC"

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

_ALLOWED_RENDER_PROFILES = (
    RENDER_PROFILE_STANDARD,
    RENDER_PROFILE_DYNAMIC,
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
    # Stage 5 correction: preserve path and query case (they may identify
    # distinct real resources). Only scheme and host are lowercased.
    # Fragments are dropped because they never reach the server and do not
    # affect resource identity. Trailing slash on path is preserved: two
    # paths differing only by a trailing "/" may point to different real
    # resources, so we do not merge them here.
    #
    # Enforces http:// or https:// scheme because Governance Fork's future
    # web-retrieval path (Stage 6b) is HTTP(S) only per the official docs.
    trimmed = url.strip()
    head = trimmed.lower()
    if head.startswith("https://"):
        scheme = "https"
        rest = trimmed[8:]
    elif head.startswith("http://"):
        scheme = "http"
        rest = trimmed[7:]
    else:
        raise gl.vm.UserError("URL must use http:// or https:// scheme")
    hash_pos = -1
    for i in range(len(rest)):
        if rest[i] == "#":
            hash_pos = i
            break
    if hash_pos >= 0:
        rest = rest[:hash_pos]
    host_end = len(rest)
    for i in range(len(rest)):
        ch = rest[i]
        if ch == "/" or ch == "?":
            host_end = i
            break
    host_part = rest[:host_end]
    tail = rest[host_end:]
    if len(host_part) == 0:
        raise gl.vm.UserError("URL has empty host")
    return scheme + "://" + host_part.lower() + tail


def _contrib_key(case_id_int: int, sender_hex: str) -> str:
    # Deterministic composite key for the per-contributor community-evidence
    # counter. Uses ":" as separator; the address hex will not contain ":",
    # and decimal digits will not either, so the split is unambiguous.
    return str(case_id_int) + ":" + sender_hex


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
# Evidence retrieval and freeze machinery (Stage 6b). Pure helpers only.
#
# Layered fingerprint model (documented in full in
# docs/STAGE_6B_PRODUCTION_EVIDENCE_FREEZE.md):
#   Evidence.content_fingerprint = SHA-256(bounded_rendered_text) alone.
#     Pure content identity -- reproducible by anyone who fetches the same
#     URL under the same render profile and hashes the result.
#   Case.membership_fingerprint  = binds WHICH evidence (id, url, profile,
#     submitter, class) was closed into the case, before any content exists.
#   Case.evidence_set_fingerprint = binds each evidence's content identity
#     and retrieval outcome, in membership order, after all fetches resolve.
#   Case.case_fingerprint = binds target-specific identity (fork or root
#     envelope) plus both of the above. This is what Stage 7 adjudicates
#     against.
# Content identity, source identity, and case identity are never blurred
# into a single field.
# =========================================================================

def _content_fingerprint(bounded_text: str) -> bytes:
    return _sha256(bounded_text.encode("utf-8"))


def _canonicalize_membership(case_id_int, evidence_id_list, evidence_lookup):
    # Order = case.evidence_ids order (submission order), NOT re-sorted.
    # Membership order is itself part of the deterministic record.
    buf = b"gf-case-membership/v1\n"
    buf = buf + b"case_id=" + str(case_id_int).encode("ascii") + b"\n"
    buf = buf + b"members=\n"
    for eid in evidence_id_list:
        ev = evidence_lookup(eid)
        buf = buf + b"  id:" + str(int(eid)).encode("ascii") + b"\n"
        buf = buf + b"  url:" + _normalize_url(ev.url).encode("utf-8") + b"\n"
        buf = buf + b"  profile:" + ev.render_profile.encode("ascii") + b"\n"
        buf = buf + b"  submitter:" + ev.submitter.as_hex.encode("ascii") + b"\n"
        buf = buf + b"  class:" + ev.evidence_class.encode("ascii") + b"\n"
    return buf


def _membership_fingerprint(case_id_int, evidence_id_list, evidence_lookup):
    return _sha256(_canonicalize_membership(case_id_int, evidence_id_list, evidence_lookup))


def _canonicalize_evidence_set(case_id_int, evidence_id_list, evidence_lookup):
    # Same order as membership -- case.evidence_ids, submission order.
    buf = b"gf-evidence-set/v1\n"
    buf = buf + b"case_id=" + str(case_id_int).encode("ascii") + b"\n"
    buf = buf + b"items=\n"
    for eid in evidence_id_list:
        ev = evidence_lookup(eid)
        buf = buf + b"  id:" + str(int(eid)).encode("ascii") + b"\n"
        buf = buf + b"  fp:" + _hex_of(ev.content_fingerprint).encode("ascii") + b"\n"
        buf = buf + b"  status:" + ev.retrieval_status.encode("ascii") + b"\n"
    return buf


def _evidence_set_fingerprint(case_id_int, evidence_id_list, evidence_lookup):
    return _sha256(_canonicalize_evidence_set(case_id_int, evidence_id_list, evidence_lookup))


def _canonicalize_retrieval_disposition(case_id_int, evidence_id_list, evidence_lookup):
    # Binds the retrieval_status of EVERY submitted member (creator AND
    # community, FETCHED/UNUSABLE_SHORT/NOT_FETCHED alike), in membership
    # order. This is the complete, auditable disposition record -- it
    # does NOT imply anything was included in adjudication; that is what
    # evidence_set_fingerprint (over the adjudication-eligible subset
    # only) is for. See docs/STAGE_6B_PRODUCTION_EVIDENCE_FREEZE.md
    # "submitted membership vs retrieved content vs adjudication input".
    buf = b"gf-retrieval-disposition/v1\n"
    buf = buf + b"case_id=" + str(case_id_int).encode("ascii") + b"\n"
    buf = buf + b"items=\n"
    for eid in evidence_id_list:
        ev = evidence_lookup(eid)
        buf = buf + b"  id:" + str(int(eid)).encode("ascii") + b"\n"
        buf = buf + b"  status:" + ev.retrieval_status.encode("ascii") + b"\n"
    return buf


def _retrieval_disposition_fingerprint(case_id_int, evidence_id_list, evidence_lookup):
    return _sha256(_canonicalize_retrieval_disposition(case_id_int, evidence_id_list, evidence_lookup))


def _canonicalize_case_fork(
    case_id_int, adjudication_dims_version_int, fork_id_int,
    fork_body_fingerprint, root_id_int, root_import_fingerprint,
    membership_fingerprint, retrieval_disposition_fingerprint,
    evidence_set_fingerprint,
):
    buf = b"gf-case/v1\n"
    buf = buf + b"case_type=FORK\n"
    buf = buf + b"case_id=" + str(case_id_int).encode("ascii") + b"\n"
    buf = buf + b"adjudication_dimensions_version=" + str(adjudication_dims_version_int).encode("ascii") + b"\n"
    buf = buf + b"fork_id=" + str(fork_id_int).encode("ascii") + b"\n"
    buf = buf + b"fork_body_fingerprint=" + _hex_of(fork_body_fingerprint).encode("ascii") + b"\n"
    buf = buf + b"root_id=" + str(root_id_int).encode("ascii") + b"\n"
    buf = buf + b"root_import_fingerprint=" + _hex_of(root_import_fingerprint).encode("ascii") + b"\n"
    buf = buf + b"membership_fingerprint=" + _hex_of(membership_fingerprint).encode("ascii") + b"\n"
    buf = buf + b"retrieval_disposition_fingerprint=" + _hex_of(retrieval_disposition_fingerprint).encode("ascii") + b"\n"
    buf = buf + b"evidence_set_fingerprint=" + _hex_of(evidence_set_fingerprint).encode("ascii") + b"\n"
    return buf


def _canonicalize_case_root_envelope(
    case_id_int, adjudication_dims_version_int, root_id_int,
    root_import_fingerprint, envelope, membership_fingerprint,
    retrieval_disposition_fingerprint, evidence_set_fingerprint,
):
    # Binds the COMPLETE frozen envelope -- not just a subset -- since
    # Stage 7 adjudicates against the full envelope, including its
    # mutable/immutable dimension classification and essential
    # constraints, not only objective/scope/beneficiary/resource_type.
    buf = b"gf-case/v1\n"
    buf = buf + b"case_type=ROOT_ENVELOPE\n"
    buf = buf + b"case_id=" + str(case_id_int).encode("ascii") + b"\n"
    buf = buf + b"adjudication_dimensions_version=" + str(adjudication_dims_version_int).encode("ascii") + b"\n"
    buf = buf + b"root_id=" + str(root_id_int).encode("ascii") + b"\n"
    buf = buf + b"root_import_fingerprint=" + _hex_of(root_import_fingerprint).encode("ascii") + b"\n"
    buf = buf + b"objective=" + envelope.objective.encode("utf-8") + b"\n"
    buf = buf + b"beneficiary_class=" + envelope.beneficiary_class.encode("utf-8") + b"\n"
    buf = buf + b"resource_type=" + envelope.resource_type.encode("ascii") + b"\n"
    buf = buf + b"scope=" + envelope.scope.encode("utf-8") + b"\n"
    buf = buf + b"essential_constraints=\n"
    for c in envelope.essential_constraints:
        buf = buf + b"  " + c.encode("utf-8") + b"\n"
    buf = buf + b"mutable_dimensions=\n"
    for d in envelope.mutable_dimensions:
        buf = buf + b"  " + d.encode("utf-8") + b"\n"
    buf = buf + b"immutable_dimensions=\n"
    for d in envelope.immutable_dimensions:
        buf = buf + b"  " + d.encode("utf-8") + b"\n"
    buf = buf + b"envelope_version=" + str(int(envelope.envelope_version)).encode("ascii") + b"\n"
    buf = buf + b"membership_fingerprint=" + _hex_of(membership_fingerprint).encode("ascii") + b"\n"
    buf = buf + b"retrieval_disposition_fingerprint=" + _hex_of(retrieval_disposition_fingerprint).encode("ascii") + b"\n"
    buf = buf + b"evidence_set_fingerprint=" + _hex_of(evidence_set_fingerprint).encode("ascii") + b"\n"
    return buf


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
    # Stage 6b: caller-selected at submission, immutable thereafter. One of
    # RENDER_PROFILE_STANDARD / RENDER_PROFILE_DYNAMIC only.
    render_profile: str
    # Stage 6b: RETRIEVAL_NOT_FETCHED until fetch_evidence commits a
    # terminal outcome (RETRIEVAL_FETCHED or RETRIEVAL_UNUSABLE_SHORT).
    retrieval_status: str
    # SHA-256 of frozen_content alone (pure content identity). Empty until
    # a terminal retrieval_status is committed.
    content_fingerprint: bytes
    # Exact bounded, consensus-approved rendered text used to compute
    # content_fingerprint. Stage 7 reads THIS field -- it never refetches
    # a (mutable) live webpage. Empty until fetched. Bounded to
    # MAX_EVIDENCE_SLICE.
    frozen_content: str
    submitted_at: u256
    # True once retrieval_status has left RETRIEVAL_NOT_FETCHED (content is
    # then immutable), regardless of whether the outcome was usable.
    frozen: bool


@allow_storage
@dataclass
class Case:
    case_type: str
    target_id: u256
    target_kind: str
    target_fingerprint: bytes
    evidence_ids: DynArray[u256]
    # Stage 6b: binds WHICH evidence was closed into the case (id, url,
    # profile, submitter, class), before any content exists. Set by
    # close_evidence. Empty before close.
    membership_fingerprint: bytes
    # Stage 6b correction: binds the retrieval_status of EVERY submitted
    # member (creator and community alike), regardless of whether that
    # member ended up adjudication-eligible. Set by seal_evidence. Empty
    # before seal. See "submitted membership vs retrieved content vs
    # adjudication input" in docs/STAGE_6B_PRODUCTION_EVIDENCE_FREEZE.md.
    retrieval_disposition_fingerprint: bytes
    # Adjudication input set only (required evidence, always FETCHED by
    # the seal gate, plus any non-required/community evidence that
    # happened to reach FETCHED by seal time). NOT the full membership.
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
class CaseCounters:
    # Contributor counters for a FORK case (Stage 5). Root-envelope cases
    # do not populate this record; it stays at zero for them.
    creator_count: u32
    community_count: u32


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

    # Stage 5 fork evidence contributor counters.
    # fork_case_counters:      case_id -> CaseCounters(creator, community)
    # fork_case_contrib_count: "<case_id>:<addr_hex>" -> community count for
    #                          that specific contributor on that case.
    # These are only populated for CASE_TYPE_FORK cases. Root-envelope cases
    # do not use them (contributor policy differs at the envelope layer).
    fork_case_counters: TreeMap[u256, CaseCounters]
    fork_case_contrib_count: TreeMap[str, u32]

    # Monotonic ID counters
    next_dao_id: u256
    next_root_id: u256
    next_fork_id: u256
    next_evidence_id: u256
    next_case_id: u256
    next_verdict_id: u256
    next_challenge_id: u256
    next_bond_id: u256

    def __init__(self):
        # Stage 6b deploy-compatibility correction: treasury/admin is bound
        # to the deploying sender, not a caller-supplied constructor
        # argument. This is not a wrapping/conversion of the value -- every
        # other Address-typed field in this contract (Dao.importer,
        # RootProposal.proposer, Fork.creator, Evidence.submitter) is
        # already assigned directly from gl.message.sender_address with no
        # intermediate conversion, and pause()/unpause() already compare
        # gl.message.sender_address directly against self.treasury_addr
        # (Address-typed) with `!=`. Both facts establish that
        # gl.message.sender_address already returns the same Address type
        # this field expects; assigning it here is consistent with every
        # existing usage in this file, not a new pattern.
        #
        # The prior signature -- __init__(self, treasury_addr: Address) --
        # deployed to a Studio instance whose deploy-calldata decoder does
        # not correctly reconstruct an Address from constructor arguments
        # (it delivers a raw int instead, and the storage setter's
        # val.as_bytes access then fails). Sourcing treasury_addr from the
        # deployment sender instead of constructor calldata avoids that
        # decode path entirely: whoever deploys this contract becomes its
        # treasury/admin, exactly as intended for this deployment.
        self.treasury_addr = gl.message.sender_address
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
        render_profiles: DynArray[str],
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
            or len(render_profiles) != n_evi
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
            rp = render_profiles[i]
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
            rp_ok = False
            for allowed in _ALLOWED_RENDER_PROFILES:
                if rp == allowed:
                    rp_ok = True
            if not rp_ok:
                raise gl.vm.UserError("render_profile out of range")
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
                render_profile=render_profiles[i],
                retrieval_status=RETRIEVAL_NOT_FETCHED,
                content_fingerprint=b"",
                frozen_content="",
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
            membership_fingerprint=b"",
            retrieval_disposition_fingerprint=b"",
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
        render_profiles: DynArray[str],
    ) -> u256:
        if self.paused:
            raise gl.vm.UserError("paused")
        if fork_id not in self.forks:
            raise gl.vm.UserError("fork not found")
        fork = self.forks[fork_id]
        # Only DRAFT (before any evidence) or EVIDENCE_OPEN accept new evidence.
        if fork.status != FORK_DRAFT and fork.status != FORK_EVIDENCE_OPEN:
            raise gl.vm.UserError("fork not accepting new evidence")
        # Stage 6b: once the case's evidence membership has been closed
        # (close_evidence), no further evidence may be added even if
        # fork.status is still EVIDENCE_OPEN.
        if fork.status == FORK_EVIDENCE_OPEN:
            existing_case = self.cases[fork.evidence_case_id]
            if existing_case.state != CASE_OPEN:
                raise gl.vm.UserError("case not open for evidence")
        # Parallel arrays must have equal length; batch must be non-empty and
        # bounded so a single caller cannot bypass per-address caps by
        # inflating the batch.
        n = len(evidence_urls)
        if n < 1:
            raise gl.vm.UserError("empty evidence batch")
        if n > MAX_EVIDENCE_BATCH:
            raise gl.vm.UserError("MAX_EVIDENCE_BATCH exceeded")
        if (
            len(evidence_classes) != n
            or len(relevance_claims) != n
            or len(authority_claims) != n
            or len(temporal_markers) != n
            or len(render_profiles) != n
        ):
            raise gl.vm.UserError("evidence arrays must have equal length")
        # Sender classification (creator vs community). Never accept a
        # caller-supplied contributor type; derive from actual sender.
        sender = gl.message.sender_address
        is_creator = sender == fork.creator
        # Resolve the fork's canonical case (create on first submission).
        creating_case = fork.status == FORK_DRAFT
        if creating_case:
            case_id = self.next_case_id
            existing_creator_count = 0
            existing_community_count = 0
            existing_case_evidence_count = 0
            existing_contrib_count = 0
        else:
            case_id = fork.evidence_case_id
            counters = self.fork_case_counters[case_id]
            existing_creator_count = int(counters.creator_count)
            existing_community_count = int(counters.community_count)
            if case_id in self.evidence_by_case:
                existing_case_evidence_count = len(self.evidence_by_case[case_id])
            else:
                existing_case_evidence_count = 0
            ck = _contrib_key(int(case_id), sender.as_hex)
            if ck in self.fork_case_contrib_count:
                existing_contrib_count = int(self.fork_case_contrib_count[ck])
            else:
                existing_contrib_count = 0
        # Cap enforcement (whole-batch atomic). If any resulting cap would be
        # exceeded, reject the batch entirely.
        if existing_case_evidence_count + n > MAX_EVIDENCE_PER_CASE:
            raise gl.vm.UserError("MAX_EVIDENCE_PER_CASE would be exceeded")
        if is_creator:
            if existing_creator_count + n > CREATOR_EVIDENCE_CAP:
                raise gl.vm.UserError("CREATOR_EVIDENCE_CAP would be exceeded")
        else:
            if existing_community_count + n > COMMUNITY_EVIDENCE_CAP:
                raise gl.vm.UserError("COMMUNITY_EVIDENCE_CAP would be exceeded")
            if existing_contrib_count + n > MAX_COMMUNITY_EVIDENCE_PER_CONTRIBUTOR:
                raise gl.vm.UserError("MAX_COMMUNITY_EVIDENCE_PER_CONTRIBUTOR would be exceeded")
        # Per-item validation + normalized-URL dedup against existing case
        # evidence and against earlier items in this same batch.
        seen_norm_in_batch = {}
        # Prebuild set of already-registered normalized URLs on the case.
        existing_norm = {}
        if not creating_case:
            if case_id in self.evidence_by_case:
                for eid in self.evidence_by_case[case_id]:
                    prior = self.evidence[eid]
                    existing_norm[_normalize_url(prior.url)] = True
        for i in range(n):
            url = evidence_urls[i]
            ec = evidence_classes[i]
            rc = relevance_claims[i]
            ac = authority_claims[i]
            tm = temporal_markers[i]
            rp = render_profiles[i]
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
            rp_ok = False
            for allowed in _ALLOWED_RENDER_PROFILES:
                if rp == allowed:
                    rp_ok = True
            if not rp_ok:
                raise gl.vm.UserError("render_profile out of range")
            norm = _normalize_url(url)
            if norm in seen_norm_in_batch:
                raise gl.vm.UserError("duplicate normalized URL in batch")
            if norm in existing_norm:
                raise gl.vm.UserError("duplicate normalized URL already on case")
            seen_norm_in_batch[norm] = True
        # All validation passed. Commit case creation (if first submission)
        # and all evidence records atomically.
        if creating_case:
            self.next_case_id = u256(int(case_id) + 1)
            self.cases[case_id] = Case(
                case_type=CASE_TYPE_FORK,
                target_id=fork_id,
                target_kind=TARGET_KIND_FORK,
                target_fingerprint=fork.body_fingerprint,
                evidence_ids=DynArray[u256](),
                membership_fingerprint=b"",
                retrieval_disposition_fingerprint=b"",
                evidence_set_fingerprint=b"",
                adjudication_dimensions_version=u32(ADJUDICATION_DIMENSIONS_VERSION_FORK),
                case_fingerprint=b"",
                state=CASE_OPEN,
                retry_count=u32(0),
                last_attempt_at=u256(0),
            )
            self.fork_case_counters[case_id] = CaseCounters(
                creator_count=u32(0),
                community_count=u32(0),
            )
            self.evidence_by_case[case_id] = DynArray[u256]()
        # Allocate evidence records
        new_ids = DynArray[u256]()
        for i in range(n):
            evidence_id = self.next_evidence_id
            self.next_evidence_id = u256(int(evidence_id) + 1)
            self.evidence[evidence_id] = Evidence(
                case_id=case_id,
                submitter=sender,
                url=evidence_urls[i],
                normalized_source=_extract_host(evidence_urls[i]),
                evidence_class=evidence_classes[i],
                relevance_claim=relevance_claims[i],
                authority_claim=authority_claims[i],
                temporal_marker=temporal_markers[i],
                render_profile=render_profiles[i],
                retrieval_status=RETRIEVAL_NOT_FETCHED,
                content_fingerprint=b"",
                frozen_content="",
                submitted_at=u256(0),
                frozen=False,
            )
            new_ids.append(evidence_id)
        # Append in submission order to the case's evidence index AND to
        # the Case record's own evidence_ids (kept in lockstep; Stage 6b's
        # close_evidence/seal_evidence read case.evidence_ids directly).
        for eid in new_ids:
            self.evidence_by_case[case_id].append(eid)
            self.cases[case_id].evidence_ids.append(eid)
        # Update contributor counters.
        old_counters = self.fork_case_counters[case_id]
        if is_creator:
            new_counters = CaseCounters(
                creator_count=u32(int(old_counters.creator_count) + n),
                community_count=old_counters.community_count,
            )
        else:
            new_counters = CaseCounters(
                creator_count=old_counters.creator_count,
                community_count=u32(int(old_counters.community_count) + n),
            )
            ck = _contrib_key(int(case_id), sender.as_hex)
            self.fork_case_contrib_count[ck] = u32(existing_contrib_count + n)
        self.fork_case_counters[case_id] = new_counters
        # Advance fork state on first submission and record case pointer.
        if creating_case:
            self.forks[fork_id] = Fork(
                parent_id=fork.parent_id,
                parent_kind=fork.parent_kind,
                root_id=fork.root_id,
                dao_id=fork.dao_id,
                creator=fork.creator,
                depth=fork.depth,
                body=fork.body,
                delta=fork.delta,
                status=FORK_EVIDENCE_OPEN,
                body_fingerprint=fork.body_fingerprint,
                delta_fingerprint=fork.delta_fingerprint,
                parent_fingerprint=fork.parent_fingerprint,
                evidence_case_id=case_id,
                current_verdict_id=fork.current_verdict_id,
                child_count=fork.child_count,
                created_at=fork.created_at,
                creator_bond_id=fork.creator_bond_id,
            )
        return case_id

    def _case_owner(self, case) -> Address:
        # Resolves the authorization owner for a case, branching on
        # case_type. FORK cases: the fork's creator. ROOT_ENVELOPE cases:
        # the root's original importer/proposer. Used by close_evidence
        # and abort_case only -- fetch_evidence and seal_evidence remain
        # permissionless per Stage 6b's liveness requirement.
        if case.case_type == CASE_TYPE_FORK:
            return self.forks[case.target_id].creator
        if case.case_type == CASE_TYPE_ROOT_ENVELOPE:
            return self.roots[case.target_id].proposer
        raise gl.vm.UserError("unsupported case_type for ownership")

    @gl.public.write
    def close_evidence(self, case_id: u256) -> None:
        # Step 1 of Close -> Fetch -> Seal. Deterministic. Locks evidence
        # membership so individual fetch_evidence calls may begin.
        if self.paused:
            raise gl.vm.UserError("paused")
        if case_id not in self.cases:
            raise gl.vm.UserError("case not found")
        case = self.cases[case_id]
        if case.state != CASE_OPEN:
            raise gl.vm.UserError("case not open")
        if len(case.evidence_ids) < 1:
            raise gl.vm.UserError("case has no evidence")
        owner = self._case_owner(case)
        if gl.message.sender_address != owner:
            raise gl.vm.UserError("only case owner may close evidence")

        def _lookup(eid):
            return self.evidence[eid]

        membership_fp = _membership_fingerprint(int(case_id), case.evidence_ids, _lookup)
        self.cases[case_id] = Case(
            case_type=case.case_type,
            target_id=case.target_id,
            target_kind=case.target_kind,
            target_fingerprint=case.target_fingerprint,
            evidence_ids=case.evidence_ids,
            membership_fingerprint=membership_fp,
            retrieval_disposition_fingerprint=case.retrieval_disposition_fingerprint,
            evidence_set_fingerprint=case.evidence_set_fingerprint,
            adjudication_dimensions_version=case.adjudication_dimensions_version,
            case_fingerprint=case.case_fingerprint,
            state=CASE_EVIDENCE_CLOSED,
            retry_count=case.retry_count,
            last_attempt_at=case.last_attempt_at,
        )

    @gl.public.write
    def fetch_evidence(self, evidence_id: u256) -> None:
        # Step 2 of Close -> Fetch -> Seal. Nondeterministic. One evidence
        # item per transaction -- deliberately NOT batched across up to 16
        # items in a single call (see docs/STAGE_6B_PRODUCTION_EVIDENCE
        # _FREEZE.md sec 3 for the explicit Option A vs Option B comparison
        # that drove this choice). Permissionless: any caller may advance a
        # closed case. NOT gated on self.paused -- this is a progress/exit
        # operation on already-committed membership, not new exposure.
        if evidence_id not in self.evidence:
            raise gl.vm.UserError("evidence not found")
        ev = self.evidence[evidence_id]
        if ev.case_id not in self.cases:
            raise gl.vm.UserError("case not found")
        case = self.cases[ev.case_id]
        if case.state != CASE_EVIDENCE_CLOSED:
            raise gl.vm.UserError("case not evidence-closed")
        if ev.retrieval_status != RETRIEVAL_NOT_FETCHED:
            raise gl.vm.UserError("evidence already fetched")

        url = ev.url
        profile = ev.render_profile

        # Two minimal leader functions, chosen deterministically BEFORE
        # entering the nondet block -- same discipline as the Stage 6a
        # probe. mode is always "text"; wait is a fixed contract constant,
        # never caller-supplied. No try/except around the nondet call: per
        # Stage 6a's own design and this stage's explicit instruction not
        # to introduce speculative exception-catching, a render() failure
        # (WEBPAGE_LOAD_FAILED, Undetermined, or any other cause) simply
        # fails this transaction. No state commits; evidence remains
        # RETRIEVAL_NOT_FETCHED and may be retried later.
        def _fetch_standard() -> str:
            return gl.nondet.web.render(url, mode="text")

        def _fetch_dynamic() -> str:
            return gl.nondet.web.render(url, mode="text", wait_after_loaded=DYNAMIC_WAIT_SECONDS)

        if profile == RENDER_PROFILE_DYNAMIC:
            content = gl.eq_principle.strict_eq(_fetch_dynamic)
        else:
            content = gl.eq_principle.strict_eq(_fetch_standard)

        # Everything below is deterministic post-processing of an already
        # consensus-agreed string. No further nondet calls.
        bounded = content[:MAX_EVIDENCE_SLICE]
        fp = _content_fingerprint(bounded)
        if len(bounded) >= MIN_USEFUL_CONTENT_LEN:
            status = RETRIEVAL_FETCHED
        else:
            status = RETRIEVAL_UNUSABLE_SHORT

        self.evidence[evidence_id] = Evidence(
            case_id=ev.case_id,
            submitter=ev.submitter,
            url=ev.url,
            normalized_source=ev.normalized_source,
            evidence_class=ev.evidence_class,
            relevance_claim=ev.relevance_claim,
            authority_claim=ev.authority_claim,
            temporal_marker=ev.temporal_marker,
            render_profile=ev.render_profile,
            retrieval_status=status,
            content_fingerprint=fp,
            frozen_content=bounded,
            submitted_at=ev.submitted_at,
            frozen=True,
        )

    @gl.public.write
    def seal_evidence(self, case_id: u256) -> None:
        # Step 3 of Close -> Fetch -> Seal. Deterministic. Permissionless.
        # NOT gated on self.paused (progress/exit operation).
        #
        # Stage 6b correction: evidence is split into a REQUIRED lane and
        # a NON-BLOCKING (community) lane at seal time.
        #   FORK case: required = evidence submitted by fork.creator.
        #     non-blocking = evidence submitted by anyone else.
        #   ROOT_ENVELOPE case: required = ALL evidence (there is no
        #     community-contribution path for root-envelope evidence in
        #     V1 -- every item shares the same submitter -- so uniform
        #     "required" parity with a FORK's creator lane is the correct
        #     application of the same reasoning, not a double standard).
        #
        # REQUIRED evidence must reach RETRIEVAL_FETCHED (not merely
        # "resolved" -- RETRIEVAL_UNUSABLE_SHORT does NOT satisfy the
        # requirement) or seal is rejected. This prevents a proposer from
        # padding a case with broken/empty required URLs and sealing
        # around them.
        #
        # NON-BLOCKING (community) evidence may be in ANY retrieval_status
        # at seal time, including still RETRIEVAL_NOT_FETCHED -- seal
        # proceeds regardless. This is the fix for the critical defect:
        # a community contributor's unrenderable/unavailable URL can
        # never block sealing. Nothing is deleted, mutated, or hidden --
        # every submitted record remains permanently queryable with its
        # true status. A community item's retrieval_status of
        # NOT_FETCHED at seal time does NOT mean "retrieval failed" or
        # "the claim is false" -- it means only "no consensus-approved
        # frozen content was committed for this evidence before sealing."
        # See docs/STAGE_6B_PRODUCTION_EVIDENCE_FREEZE.md for the full
        # "submitted membership vs retrieved content vs adjudication
        # input" discussion.
        if case_id not in self.cases:
            raise gl.vm.UserError("case not found")
        case = self.cases[case_id]
        if case.state != CASE_EVIDENCE_CLOSED:
            raise gl.vm.UserError("case not evidence-closed")

        def _lookup(eid):
            return self.evidence[eid]

        if case.case_type == CASE_TYPE_FORK:
            required_owner = self.forks[case.target_id].creator
        elif case.case_type == CASE_TYPE_ROOT_ENVELOPE:
            required_owner = None  # sentinel: every item is required
        else:
            raise gl.vm.UserError("unsupported case_type for seal")

        eligible_ids = DynArray[u256]()
        for eid in case.evidence_ids:
            ev = self.evidence[eid]
            is_required = required_owner is None or ev.submitter == required_owner
            if is_required:
                if ev.retrieval_status != RETRIEVAL_FETCHED:
                    raise gl.vm.UserError("required evidence not fetched: " + str(int(eid)))
                eligible_ids.append(eid)
            elif ev.retrieval_status == RETRIEVAL_FETCHED:
                eligible_ids.append(eid)
            # else: non-required and not FETCHED (NOT_FETCHED or
            # UNUSABLE_SHORT) -- remains in membership/provenance,
            # excluded from the adjudication-eligible set, does not
            # block seal.

        # retrieval_disposition_fingerprint binds the true status of
        # EVERY submitted member, required or not, eligible or not --
        # the complete, auditable disposition record.
        disposition_fp = _retrieval_disposition_fingerprint(
            int(case_id), case.evidence_ids, _lookup
        )
        # evidence_set_fingerprint binds ONLY the adjudication-eligible
        # subset -- what Stage 7 is actually allowed to consume.
        evidence_set_fp = _evidence_set_fingerprint(int(case_id), eligible_ids, _lookup)

        if case.case_type == CASE_TYPE_FORK:
            fork = self.forks[case.target_id]
            root = self.roots[fork.root_id]
            case_fp = _sha256(
                _canonicalize_case_fork(
                    int(case_id),
                    int(case.adjudication_dimensions_version),
                    int(case.target_id),
                    fork.body_fingerprint,
                    int(fork.root_id),
                    root.import_fingerprint,
                    case.membership_fingerprint,
                    disposition_fp,
                    evidence_set_fp,
                )
            )
        elif case.case_type == CASE_TYPE_ROOT_ENVELOPE:
            root = self.roots[case.target_id]
            case_fp = _sha256(
                _canonicalize_case_root_envelope(
                    int(case_id),
                    int(case.adjudication_dimensions_version),
                    int(case.target_id),
                    root.import_fingerprint,
                    root.envelope,
                    case.membership_fingerprint,
                    disposition_fp,
                    evidence_set_fp,
                )
            )
            # Derive RootProposal.web_content_fingerprint from the frozen
            # Evidence record whose URL matches the root's own canonical
            # proposal_url, if the submitter included it as evidence and it
            # was successfully (usefully) fetched. Never a duplicate fetch.
            if root.web_content_fingerprint == b"":
                root_norm = _normalize_url(root.proposal_url)
                for eid in case.evidence_ids:
                    ev = self.evidence[eid]
                    if (
                        ev.retrieval_status == RETRIEVAL_FETCHED
                        and _normalize_url(ev.url) == root_norm
                    ):
                        self.roots[case.target_id] = RootProposal(
                            dao_id=root.dao_id,
                            external_proposal_id=root.external_proposal_id,
                            title=root.title,
                            proposal_url=root.proposal_url,
                            proposer=root.proposer,
                            import_fingerprint=root.import_fingerprint,
                            web_content_fingerprint=ev.content_fingerprint,
                            structured_parameters=root.structured_parameters,
                            envelope=root.envelope,
                            envelope_status=root.envelope_status,
                            envelope_case_id=root.envelope_case_id,
                            identity_status=root.identity_status,
                            imported_at=root.imported_at,
                        )
                        break
        else:
            raise gl.vm.UserError("unsupported case_type for seal")

        self.cases[case_id] = Case(
            case_type=case.case_type,
            target_id=case.target_id,
            target_kind=case.target_kind,
            target_fingerprint=case.target_fingerprint,
            evidence_ids=case.evidence_ids,
            membership_fingerprint=case.membership_fingerprint,
            retrieval_disposition_fingerprint=disposition_fp,
            evidence_set_fingerprint=evidence_set_fp,
            adjudication_dimensions_version=case.adjudication_dimensions_version,
            case_fingerprint=case_fp,
            state=CASE_CASE_FROZEN,
            retry_count=case.retry_count,
            last_attempt_at=case.last_attempt_at,
        )

    @gl.public.write
    def abort_case(self, case_id: u256) -> None:
        # Explicit, auditable escape valve. Stage 6b correction narrowed
        # its purpose: community (non-required) evidence can no longer
        # block sealing at all (see seal_evidence), so this is no longer
        # needed for third-party griefing. It remains useful for the one
        # residual scenario: REQUIRED evidence (a fork creator's own
        # submitted URL, or -- since all root-envelope evidence is
        # required -- any root-envelope evidence) becomes permanently
        # unfetchable, which would otherwise stick the case at
        # CASE_EVIDENCE_CLOSED forever. Owner-gated. Only a CLOSED (not
        # yet sealed) case may be aborted -- an OPEN case doesn't need
        # aborting (evidence submission can simply stop), and a
        # CASE_FROZEN case is immutable by design. Aborting does not
        # delete or alter any evidence record; the case and its evidence
        # remain permanently queryable in their exact prior state. V1
        # does not implement a fresh-case-retry path for the same fork/
        # root -- see docs/STAGE_6B_PRODUCTION_EVIDENCE_FREEZE.md for the
        # explicit justification.
        if self.paused:
            raise gl.vm.UserError("paused")
        if case_id not in self.cases:
            raise gl.vm.UserError("case not found")
        case = self.cases[case_id]
        if case.state != CASE_EVIDENCE_CLOSED:
            raise gl.vm.UserError("only an evidence-closed case may be aborted")
        owner = self._case_owner(case)
        if gl.message.sender_address != owner:
            raise gl.vm.UserError("only case owner may abort")
        self.cases[case_id] = Case(
            case_type=case.case_type,
            target_id=case.target_id,
            target_kind=case.target_kind,
            target_fingerprint=case.target_fingerprint,
            evidence_ids=case.evidence_ids,
            membership_fingerprint=case.membership_fingerprint,
            retrieval_disposition_fingerprint=case.retrieval_disposition_fingerprint,
            evidence_set_fingerprint=case.evidence_set_fingerprint,
            adjudication_dimensions_version=case.adjudication_dimensions_version,
            case_fingerprint=case.case_fingerprint,
            state=CASE_ABORTED,
            retry_count=case.retry_count,
            last_attempt_at=case.last_attempt_at,
        )

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
