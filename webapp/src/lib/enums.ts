// Mirrors the string-constant enums in contracts/governance_fork.py.
// Only the values the frontend needs to *send* or *label* are listed.

// ----- bond purposes / amount -----------------------------------------------
export const BOND_PURPOSE = {
  FORK_CREATION: "FORK_CREATION",
  ENVELOPE: "ENVELOPE",
  CHALLENGE: "CHALLENGE",
} as const;
export type BondPurpose = (typeof BOND_PURPOSE)[keyof typeof BOND_PURPOSE];

// All three bonds are 0.1 GEN on the live contract (confirmed via
// get_constants). Wei value passed to lock_bond.
export const BOND_AMOUNT_WEI = 100_000_000_000_000_000n; // 0.1 * 10^18
export const CHALLENGER_FLIP_REWARD_WEI = 50_000_000_000_000_000n; // 0.05 GEN

// ----- target / parent kinds ----------------------------------------------
export const TARGET_KIND = {
  ROOT_ENVELOPE: "ROOT_ENVELOPE",
  FORK: "FORK",
} as const;
export type TargetKind = (typeof TARGET_KIND)[keyof typeof TARGET_KIND];

export const PARENT_KIND = {
  ROOT: "PARENT_ROOT",
  FORK: "PARENT_FORK",
} as const;

// ----- resource types (envelope) -----------------------------------------
export const RESOURCE_TYPES = [
  "TREASURY",
  "PROTOCOL_PARAMETER",
  "POLICY",
  "GRANT_POOL",
  "INCENTIVE_BUDGET",
  "OTHER",
] as const;

// ----- evidence classes -------------------------------------------------
export const EVIDENCE_CLASSES = [
  "OFFICIAL_GOVERNANCE",
  "OFFICIAL_DOCUMENTATION",
  "OFFICIAL_TREASURY",
  "FINALIZED_DECISION",
  "GOVERNANCE_DISCUSSION",
  "IMPLEMENTATION_SPEC",
  "AUDIT",
  "THIRD_PARTY_ANALYSIS",
] as const;

// ----- render profiles ------------------------------------------------
export const RENDER_PROFILES = ["STANDARD", "DYNAMIC"] as const;

// ----- delta claim kinds -------------------------------------------------
export const CLAIM_KINDS = [
  "NARROWED",
  "BROADENED",
  "RESHAPED",
  "REMOVED",
  "ADDED",
] as const;

// ----- challenge grounds, per target kind ------------------------------
export const CHALLENGE_GROUNDS_ROOT_ENVELOPE = [
  "OBJECTIVE_MISREPRESENTED",
  "SCOPE_MISCHARACTERIZED",
  "CONSTRAINT_INCOMPLETE",
  "DIMENSION_MISCLASSIFIED",
  "ENVELOPE_SOURCE_AUTHORITY_ERROR",
  "ENVELOPE_EVIDENCE_SUPPORT_ERROR",
  "ENVELOPE_MALFORMED_ADJUDICATION",
] as const;

export const CHALLENGE_GROUNDS_FORK = [
  "INTENT_MISREAD",
  "DELTA_MISCLASSIFIED",
  "UNDECLARED_CHANGE_IGNORED",
  "SOURCE_AUTHORITY_ERROR",
  "TEMPORAL_EVIDENCE_ERROR",
  "CONTRADICTORY_EVIDENCE_OMITTED",
  "MALFORMED_ADJUDICATION",
] as const;

// ----- status groups (for read-side rendering) -------------------------

export const ENVELOPE_STATUS = {
  NOT_SUBMITTED: "ENVELOPE_NOT_SUBMITTED",
  EVIDENCE_OPEN: "ENVELOPE_EVIDENCE_OPEN",
  EVIDENCE_FROZEN: "ENVELOPE_EVIDENCE_FROZEN",
  ADJUDICATING: "ENVELOPE_ADJUDICATING",
  CHALLENGE_OPEN: "ENVELOPE_CHALLENGE_OPEN",
  FAITHFUL: "ENVELOPE_FAITHFUL",
  REJECTED: "ENVELOPE_REJECTED",
  UNCLEAR: "ENVELOPE_UNCLEAR",
} as const;

export const ENVELOPE_FINAL_STATUSES = new Set<string>([
  ENVELOPE_STATUS.FAITHFUL,
  ENVELOPE_STATUS.REJECTED,
  ENVELOPE_STATUS.UNCLEAR,
]);

export const FORK_STATUS = {
  DRAFT: "DRAFT",
  EVIDENCE_OPEN: "EVIDENCE_OPEN",
  EVIDENCE_FROZEN: "EVIDENCE_FROZEN",
  CASE_FROZEN: "CASE_FROZEN",
  ADJUDICATING: "ADJUDICATING",
  VERDICT_PROPOSED: "VERDICT_PROPOSED",
  CHALLENGE_WINDOW: "CHALLENGE_WINDOW",
  CHALLENGE_OPEN: "CHALLENGE_OPEN",
  FINALIZED_FAITHFUL: "FINALIZED_FAITHFUL",
  FINALIZED_NOT_FAITHFUL: "FINALIZED_NOT_FAITHFUL",
  FINALIZED_UNCLEAR: "FINALIZED_UNCLEAR",
  FINALIZED_INVALID: "FINALIZED_INVALID",
} as const;

export const FORK_FINAL_STATUSES = new Set<string>([
  FORK_STATUS.FINALIZED_FAITHFUL,
  FORK_STATUS.FINALIZED_NOT_FAITHFUL,
  FORK_STATUS.FINALIZED_UNCLEAR,
  FORK_STATUS.FINALIZED_INVALID,
]);

export const CASE_STATE = {
  OPEN: "OPEN",
  EVIDENCE_CLOSED: "EVIDENCE_CLOSED",
  CASE_FROZEN: "CASE_FROZEN",
  ADJUDICATING: "ADJUDICATING",
  SUCCESS: "SUCCESS",
  UNDETERMINED_TERMINAL: "UNDETERMINED_TERMINAL",
  INVALID: "INVALID",
  ABORTED: "ABORTED",
} as const;

export const CASE_TYPE = {
  ROOT_ENVELOPE: "ROOT_ENVELOPE",
  FORK: "FORK",
  CHALLENGE: "CHALLENGE",
} as const;

export const RETRIEVAL_STATUS = {
  NOT_FETCHED: "NOT_FETCHED",
  FETCHED: "FETCHED",
  UNUSABLE_SHORT: "UNUSABLE_SHORT",
} as const;

export const VERDICT = {
  FAITHFUL: "FAITHFUL",
  NOT_FAITHFUL: "NOT_FAITHFUL",
  UNCLEAR: "UNCLEAR_VERDICT",
  INVALID: "INVALID",
} as const;

export const CHALLENGE_STATUS = {
  OPEN: "OPEN",
  ADJUDICATING: "ADJUDICATING",
  RESOLVED_FLIPPED: "RESOLVED_FLIPPED",
  RESOLVED_UNCHANGED: "RESOLVED_UNCHANGED",
  RESOLVED_INVALID: "RESOLVED_INVALID",
  RESOLVED_UNCLEAR: "RESOLVED_UNCLEAR",
} as const;

export const CHALLENGE_OPEN_STATES = new Set<string>([
  CHALLENGE_STATUS.OPEN,
  CHALLENGE_STATUS.ADJUDICATING,
]);

export const BOND_SETTLEMENT = {
  UNSETTLED: "UNSETTLED",
  SETTLED_FULL_REFUND: "SETTLED_FULL_REFUND",
  SETTLED_PARTIAL_SLASH: "SETTLED_PARTIAL_SLASH",
  SETTLED_CHALLENGER_REWARD: "SETTLED_CHALLENGER_REWARD",
} as const;

// Human-readable one-liners for the less obvious codes.
export const STATUS_HELP: Record<string, string> = {
  ENVELOPE_NOT_SUBMITTED: "Root imported; intent envelope not yet submitted.",
  ENVELOPE_EVIDENCE_OPEN: "Envelope submitted; evidence can be added / fetched / sealed.",
  ENVELOPE_ADJUDICATING: "Evidence sealed; semantic adjudication armed or running.",
  ENVELOPE_CHALLENGE_OPEN: "A challenge against the verdict is open and being re-adjudicated.",
  ENVELOPE_FAITHFUL: "Final: the envelope faithfully represents the proposal. Forkable.",
  ENVELOPE_REJECTED: "Final: the envelope does not faithfully represent the proposal.",
  ENVELOPE_UNCLEAR: "Final: adjudication could not reach a clear verdict.",
  UNCLEAR_VERDICT: "The adjudicator could not decide — treated as Undetermined.",
  RESOLVED_FLIPPED: "The challenge succeeded: the governing verdict changed.",
  RESOLVED_UNCHANGED: "The challenge failed: the original verdict stands.",
  RESOLVED_INVALID: "Re-adjudication returned INVALID; original verdict stands.",
  RESOLVED_UNCLEAR: "Re-adjudication was Undetermined; original verdict stands.",
  SETTLED_FULL_REFUND: "Bond returned in full.",
  SETTLED_PARTIAL_SLASH: "Half the bond was slashed to the treasury.",
  SETTLED_CHALLENGER_REWARD: "Bond refunded plus a flip reward from the treasury pool.",
};
