# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


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

# Resource type
RESOURCE_TREASURY = "TREASURY"
RESOURCE_PROTOCOL_PARAMETER = "PROTOCOL_PARAMETER"
RESOURCE_POLICY = "POLICY"
RESOURCE_GRANT_POOL = "GRANT_POOL"
RESOURCE_INCENTIVE_BUDGET = "INCENTIVE_BUDGET"
RESOURCE_OTHER = "OTHER"


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
    body_fingerprint: bytes
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
    root_id: u256
    dao_id: u256
    creator: Address
    depth: u32
    body: ForkBody
    delta: DynArray[DeltaEntry]
    status: str
    body_fingerprint: bytes
    delta_fingerprint: bytes
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
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.write
    def import_root_proposal(
        self,
        dao_id: u256,
        external_proposal_id: str,
        title: str,
        proposal_url: str,
        structured_parameters: DynArray[ParamKV],
    ) -> u256:
        raise gl.vm.UserError("stage-2: not implemented")

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
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.write.payable
    def create_fork(
        self,
        parent_id: u256,
        parent_fingerprint: bytes,
        delta: DynArray[DeltaEntry],
        body: ForkBody,
    ) -> u256:
        raise gl.vm.UserError("stage-2: not implemented")

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
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def list_daos(self, cursor: u256, limit: u32) -> PageIds:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def get_root_proposal(self, root_id: u256) -> RootProposal:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def list_root_proposals_by_dao(
        self, dao_id: u256, cursor: u256, limit: u32
    ) -> PageIds:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def get_fork(self, fork_id: u256) -> Fork:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def list_forks_of_root(
        self, root_id: u256, cursor: u256, limit: u32
    ) -> PageIds:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def list_forks_of_parent(
        self, parent_id: u256, cursor: u256, limit: u32
    ) -> PageIds:
        raise gl.vm.UserError("stage-2: not implemented")

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
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def list_evidence_of_case(
        self, case_id: u256, cursor: u256, limit: u32
    ) -> PageIds:
        raise gl.vm.UserError("stage-2: not implemented")

    @gl.public.view
    def get_case(self, case_id: u256) -> Case:
        raise gl.vm.UserError("stage-2: not implemented")

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
        raise gl.vm.UserError("stage-2: not implemented")
