// Typed wrappers over every contract method the dApp uses.
//
// Reads go through the shared read client (no wallet needed). Writes take a
// GenLayerClient bound to the connected account. The lock_bond -> consume
// pattern (payable lock, then non-payable action with the returned bond_id)
// is encoded in `lockBond` + the *WithBond helpers.

import {
  GenLayerClient,
  view,
  viewOpt,
  writeAndWait,
  hexToBytes,
  WriteResult,
} from "./genlayer";
import { BOND_AMOUNT_WEI, BOND_PURPOSE, TARGET_KIND } from "./enums";
import type {
  Bond,
  Case,
  Challenge,
  ConstantsView,
  Dao,
  Evidence,
  Fork,
  PageIds,
  RootProposal,
  VerdictRecord,
} from "./types";

const PAGE = 50;

// ---------- reads ----------------------------------------------------------

export const getConstants = () => view<ConstantsView>("get_constants");

export const getDao = (id: bigint | number) =>
  viewOpt<Dao>("get_dao", [BigInt(id)]);
export const getRootProposal = (id: bigint | number) =>
  viewOpt<RootProposal>("get_root_proposal", [BigInt(id)]);
export const getFork = (id: bigint | number) =>
  viewOpt<Fork>("get_fork", [BigInt(id)]);
export const getCase = (id: bigint | number) =>
  viewOpt<Case>("get_case", [BigInt(id)]);
export const getEvidence = (id: bigint | number) =>
  viewOpt<Evidence>("get_evidence", [BigInt(id)]);
export const getVerdict = (id: bigint | number) =>
  viewOpt<VerdictRecord>("get_verdict", [BigInt(id)]);
export const getChallenge = (id: bigint | number) =>
  viewOpt<Challenge>("get_challenge", [BigInt(id)]);
export const getBond = (id: bigint | number) =>
  viewOpt<Bond>("get_bond", [BigInt(id)]);

export const listDaos = (cursor = 0n, limit = PAGE) =>
  view<PageIds>("list_daos", [cursor, limit]);
export const listRootsByDao = (daoId: bigint, cursor = 0n, limit = PAGE) =>
  view<PageIds>("list_root_proposals_by_dao", [daoId, cursor, limit]);
export const listForksOfRoot = (rootId: bigint, cursor = 0n, limit = PAGE) =>
  view<PageIds>("list_forks_of_root", [rootId, cursor, limit]);
export const listForksOfParent = (
  parentId: bigint,
  cursor = 0n,
  limit = PAGE,
) => view<PageIds>("list_forks_of_parent", [parentId, cursor, limit]);
export const listEvidenceOfCase = (
  caseId: bigint,
  cursor = 0n,
  limit = PAGE,
) => view<PageIds>("list_evidence_of_case", [caseId, cursor, limit]);
export const listChallenges = (
  targetId: bigint,
  targetKind: string,
  cursor = 0n,
  limit = PAGE,
) => view<PageIds>("list_challenges", [targetId, targetKind, cursor, limit]);
export const getVerdictHistory = (
  targetId: bigint,
  targetKind: string,
  cursor = 0n,
  limit = PAGE,
) =>
  view<PageIds>("get_verdict_history", [targetId, targetKind, cursor, limit]);
export const listBondsByTarget = (
  targetId: bigint,
  targetKind: string,
  cursor = 0n,
  limit = PAGE,
) =>
  view<PageIds>("list_bonds_by_target", [targetId, targetKind, cursor, limit]);

/** Walk every page of a PageIds view into one array. */
export async function collectAll(
  fetchPage: (cursor: bigint) => Promise<PageIds>,
): Promise<bigint[]> {
  const out: bigint[] = [];
  let cursor = 0n;
  for (let guard = 0; guard < 200; guard++) {
    const page = await fetchPage(cursor);
    for (const it of page.items) out.push(BigInt(it));
    const next = BigInt(page.next_cursor);
    if (next === 0n || next === cursor) break;
    cursor = next;
  }
  return out;
}

// ---------- writes: registry & import -----------------------------------

export function registerDao(
  c: GenLayerClient,
  name: string,
  url: string,
): Promise<WriteResult> {
  return writeAndWait(c, "register_dao", [name, url]);
}

export function importRootProposal(
  c: GenLayerClient,
  args: {
    daoId: bigint;
    externalProposalId: string;
    title: string;
    proposalUrl: string;
    paramKeys: string[];
    paramValues: string[];
  },
): Promise<WriteResult> {
  return writeAndWait(c, "import_root_proposal", [
    args.daoId,
    args.externalProposalId,
    args.title,
    args.proposalUrl,
    args.paramKeys,
    args.paramValues,
  ]);
}

// ---------- writes: bonds ----------------------------------------------

/** Payable. Locks BOND_AMOUNT_WEI and returns the new bond id. */
export async function lockBond(
  c: GenLayerClient,
  purpose: (typeof BOND_PURPOSE)[keyof typeof BOND_PURPOSE],
): Promise<{ bondId: bigint; write: WriteResult }> {
  const write = await writeAndWait(c, "lock_bond", [purpose], BOND_AMOUNT_WEI);
  const bondId = parseId(write.returnValue, "lock_bond");
  return { bondId, write };
}

export function settleBond(
  c: GenLayerClient,
  bondId: bigint,
): Promise<WriteResult> {
  return writeAndWait(c, "settle_bond", [bondId]);
}

export function withdrawTreasury(
  c: GenLayerClient,
  amountWei: bigint,
): Promise<WriteResult> {
  return writeAndWait(c, "withdraw_treasury", [amountWei]);
}

// ---------- writes: envelope ------------------------------------------

export interface EnvelopeInput {
  rootId: bigint;
  objective: string;
  beneficiaryClass: string;
  resourceType: string;
  scope: string;
  essentialConstraints: string[];
  mutableDimensions: string[];
  immutableDimensions: string[];
  evidenceUrls: string[];
  evidenceClasses: string[];
  relevanceClaims: string[];
  authorityClaims: string[];
  temporalMarkers: string[];
  renderProfiles: string[];
}

export function submitRootEnvelope(
  c: GenLayerClient,
  bondId: bigint,
  e: EnvelopeInput,
): Promise<WriteResult> {
  return writeAndWait(c, "submit_root_envelope", [
    bondId,
    e.rootId,
    e.objective,
    e.beneficiaryClass,
    e.resourceType,
    e.scope,
    e.essentialConstraints,
    e.mutableDimensions,
    e.immutableDimensions,
    e.evidenceUrls,
    e.evidenceClasses,
    e.relevanceClaims,
    e.authorityClaims,
    e.temporalMarkers,
    e.renderProfiles,
  ]);
}

// ---------- writes: forks -------------------------------------------

export interface ForkInput {
  parentId: bigint;
  parentKind: string; // PARENT_ROOT | PARENT_FORK
  parentFingerprintHex: string;
  deltaDimensionNames: string[];
  deltaParentValues: string[];
  deltaForkValues: string[];
  deltaClaimKinds: string[];
  bodyTitle: string;
  bodySummary: string;
  bodyParamKeys: string[];
  bodyParamValues: string[];
  bodyReasoning: string;
}

export async function createFork(
  c: GenLayerClient,
  bondId: bigint,
  f: ForkInput,
): Promise<{ forkId: bigint; write: WriteResult }> {
  const write = await writeAndWait(c, "create_fork", [
    bondId,
    f.parentId,
    f.parentKind,
    hexToBytes(f.parentFingerprintHex),
    f.deltaDimensionNames,
    f.deltaParentValues,
    f.deltaForkValues,
    f.deltaClaimKinds,
    f.bodyTitle,
    f.bodySummary,
    f.bodyParamKeys,
    f.bodyParamValues,
    f.bodyReasoning,
  ]);
  return { forkId: parseId(write.returnValue, "create_fork"), write };
}

export interface ForkEvidenceInput {
  forkId: bigint;
  evidenceUrls: string[];
  evidenceClasses: string[];
  relevanceClaims: string[];
  authorityClaims: string[];
  temporalMarkers: string[];
  renderProfiles: string[];
}

export function submitForkEvidence(
  c: GenLayerClient,
  e: ForkEvidenceInput,
): Promise<WriteResult> {
  return writeAndWait(c, "submit_fork_evidence", [
    e.forkId,
    e.evidenceUrls,
    e.evidenceClasses,
    e.relevanceClaims,
    e.authorityClaims,
    e.temporalMarkers,
    e.renderProfiles,
  ]);
}

// ---------- writes: evidence lifecycle -------------------------------

export const closeEvidence = (c: GenLayerClient, caseId: bigint) =>
  writeAndWait(c, "close_evidence", [caseId]);
export const fetchEvidence = (c: GenLayerClient, evidenceId: bigint) =>
  writeAndWait(c, "fetch_evidence", [evidenceId]);
export const sealEvidence = (c: GenLayerClient, caseId: bigint) =>
  writeAndWait(c, "seal_evidence", [caseId]);
export const abortCase = (c: GenLayerClient, caseId: bigint) =>
  writeAndWait(c, "abort_case", [caseId]);

// ---------- writes: adjudication -----------------------------------

export const adjudicate = (c: GenLayerClient, caseId: bigint) =>
  writeAndWait(c, "adjudicate", [caseId]);
export const runAdjudication = (c: GenLayerClient, caseId: bigint) =>
  writeAndWait(c, "run_adjudication", [caseId]);

// ---------- writes: challenge & finality --------------------------

export async function challengeVerdict(
  c: GenLayerClient,
  bondId: bigint,
  targetId: bigint,
  targetKind: string,
  groundCode: string,
  argument: string,
): Promise<{ challengeId: bigint; write: WriteResult }> {
  const write = await writeAndWait(c, "challenge_verdict", [
    bondId,
    targetId,
    targetKind,
    groundCode,
    argument,
  ]);
  return {
    challengeId: parseId(write.returnValue, "challenge_verdict"),
    write,
  };
}

export const finalize = (
  c: GenLayerClient,
  targetId: bigint,
  targetKind: string,
) => writeAndWait(c, "finalize", [targetId, targetKind]);

// ---------- admin ----------------------------------------------------

export const pause = (c: GenLayerClient) => writeAndWait(c, "pause", []);
export const unpause = (c: GenLayerClient) => writeAndWait(c, "unpause", []);

// ---------- helpers -------------------------------------------------

export function parseId(raw: string | undefined, ctx: string): bigint {
  if (raw == null || raw === "") {
    throw new Error(
      `${ctx}: transaction committed but no return value was decoded. ` +
        `Re-read state to locate the new record.`,
    );
  }
  const m = raw.match(/-?\d+/);
  if (!m) throw new Error(`${ctx}: could not parse id from "${raw}"`);
  return BigInt(m[0]);
}

export { BOND_AMOUNT_WEI, BOND_PURPOSE, TARGET_KIND };
export type { GenLayerClient, WriteResult };
