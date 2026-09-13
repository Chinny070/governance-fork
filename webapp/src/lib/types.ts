// TypeScript shapes for the values genlayer-js decodes from the contract.
//
// Decoding conventions observed live (genlayer-js 1.1.8 against StudioNet):
//   - small ints  -> number
//   - u256        -> bigint
//   - bytes       -> "0x"-prefixed lowercase hex string ("0x" when empty)
//   - address     -> "0x"-prefixed lowercase hex string
//   - DynArray    -> array
//   - @dataclass  -> plain object

export type Hex = string;
export type Address = string;

export interface ParamKV {
  key: string;
  value: string;
}

export interface Dao {
  name: string;
  url: string;
  importer: Address;
  imported_at: bigint;
}

export interface IntentEnvelope {
  objective: string;
  beneficiary_class: string;
  resource_type: string;
  scope: string;
  essential_constraints: string[];
  mutable_dimensions: string[];
  immutable_dimensions: string[];
  parent_proposal_fingerprint: Hex;
  envelope_version: number;
}

export interface RootProposal {
  dao_id: bigint;
  external_proposal_id: string;
  title: string;
  proposal_url: string;
  proposer: Address;
  import_fingerprint: Hex;
  web_content_fingerprint: Hex;
  structured_parameters: ParamKV[];
  envelope: IntentEnvelope;
  envelope_status: string;
  envelope_case_id: bigint;
  identity_status: string;
  imported_at: bigint;
  current_verdict_id: bigint;
  finality_window_opened_at: bigint;
}

export interface DeltaEntry {
  dimension_name: string;
  parent_value: string;
  fork_value: string;
  claim_kind: string;
}

export interface ForkBody {
  title: string;
  summary: string;
  structured_parameters: ParamKV[];
  reasoning: string;
}

export interface Fork {
  parent_id: bigint;
  parent_kind: string;
  root_id: bigint;
  dao_id: bigint;
  creator: Address;
  depth: number;
  body: ForkBody;
  delta: DeltaEntry[];
  status: string;
  body_fingerprint: Hex;
  delta_fingerprint: Hex;
  parent_fingerprint: Hex;
  evidence_case_id: bigint;
  current_verdict_id: bigint;
  child_count: number;
  created_at: bigint;
  creator_bond_id: bigint;
  finality_window_opened_at: bigint;
}

export interface Evidence {
  case_id: bigint;
  submitter: Address;
  url: string;
  normalized_source: string;
  evidence_class: string;
  relevance_claim: string;
  authority_claim: string;
  temporal_marker: string;
  render_profile: string;
  retrieval_status: string;
  content_fingerprint: Hex;
  frozen_content: string;
  submitted_at: bigint;
  frozen: boolean;
}

export interface Case {
  case_type: string;
  target_id: bigint;
  target_kind: string;
  target_fingerprint: Hex;
  evidence_ids: bigint[];
  membership_fingerprint: Hex;
  retrieval_disposition_fingerprint: Hex;
  evidence_set_fingerprint: Hex;
  adjudication_dimensions_version: number;
  case_fingerprint: Hex;
  state: string;
  retry_count: number;
  last_attempt_at: bigint;
  verdict_id: bigint;
  challenge_id: bigint;
}

export interface DimensionFinding {
  name: string;
  finding: string;
  reasoning: string;
  evidence_ids: bigint[];
}

export interface VerdictRecord {
  case_id: bigint;
  target_id: bigint;
  target_kind: string;
  verdict: string;
  dimensions: DimensionFinding[];
  evidence_refs: bigint[];
  reason_codes: string[];
  reasoning_hash: Hex;
  replaced_by: bigint;
  created_at: bigint;
  verdict_id: bigint;
  case_fingerprint: Hex;
  prompt_fingerprint: Hex;
  adjudication_dimensions_version: number;
}

export interface Challenge {
  target_id: bigint;
  target_kind: string;
  challenger: Address;
  ground_code: string;
  argument: string;
  case_id: bigint;
  original_verdict_id: bigint;
  replacement_verdict_id: bigint;
  status: string;
  bond_id: bigint;
  opened_at: bigint;
}

export interface Bond {
  owner: Address;
  amount: bigint;
  target_id: bigint;
  target_kind: string;
  purpose: string;
  settlement_kind: string;
  settled: boolean;
  settled_at: bigint;
  challenge_id: bigint;
  refund_amount: bigint;
  slash_amount: bigint;
  reward_amount: bigint;
}

export interface PageIds {
  items: bigint[];
  next_cursor: bigint;
}

export interface ConstantsView {
  max_daos: number;
  max_roots_per_dao: number;
  max_forks_per_root: number;
  max_children_per_parent: number;
  max_depth_per_root: number;
  max_evidence_per_case: number;
  max_challenges_per_target: number;
  max_evidence_slice: number;
  pagination_limit_max: number;
  max_delta_entries: number;
  fork_creation_bond: bigint;
  envelope_bond: bigint;
  challenge_bond: bigint;
  challenge_window_seconds: number;
  retry_cooldown_seconds: number;
  max_retries_per_case: number;
  challenger_flip_reward: bigint;
  treasury_pool: bigint;
  treasury_addr: Address;
  paused: boolean;
}
