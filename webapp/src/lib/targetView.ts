import {
  collectAll,
  getBond,
  getCase,
  getChallenge,
  getEvidence,
  getFork,
  getRootProposal,
  getVerdict,
  listBondsByTarget,
  listChallenges,
  listEvidenceOfCase,
  getVerdictHistory,
} from "./api";
import { TARGET_KIND, CHALLENGE_OPEN_STATES } from "./enums";
import type {
  Bond,
  Case,
  Challenge,
  Evidence,
  Fork,
  RootProposal,
  VerdictRecord,
} from "./types";

export type TargetKindName = "root" | "fork";

export interface ChallengeView {
  id: bigint;
  challenge: Challenge;
  case?: Case;
}

export interface TargetView {
  kind: TargetKindName;
  targetKindConst: string; // ROOT_ENVELOPE | FORK
  id: bigint;
  root?: RootProposal;
  fork?: Fork;
  /** For a fork: the root proposal it descends from (for "Original intent"). */
  rootProposal?: RootProposal;
  /** For a fork: its immediate parent, when the parent is another fork. */
  parentFork?: Fork;
  status: string;
  title: string;
  daoId: bigint;
  rootId: bigint;
  evidenceCaseId: bigint;
  currentVerdictId: bigint;
  case?: Case;
  evidence: { id: bigint; ev: Evidence }[];
  verdict?: VerdictRecord;
  verdictHistory: bigint[];
  challenges: ChallengeView[];
  openChallenge?: ChallengeView;
  bonds: { id: bigint; bond: Bond }[];
  isFinal: boolean;
  isFaithfulFinal: boolean;
}

const ENVELOPE_FINAL = new Set([
  "ENVELOPE_FAITHFUL",
  "ENVELOPE_REJECTED",
  "ENVELOPE_UNCLEAR",
]);
const FORK_FINAL = new Set([
  "FINALIZED_FAITHFUL",
  "FINALIZED_NOT_FAITHFUL",
  "FINALIZED_UNCLEAR",
  "FINALIZED_INVALID",
]);

export async function loadTarget(
  kind: TargetKindName,
  id: bigint,
): Promise<TargetView | null> {
  const targetKindConst =
    kind === "root" ? TARGET_KIND.ROOT_ENVELOPE : TARGET_KIND.FORK;

  let base: Partial<TargetView> = { kind, targetKindConst, id };

  if (kind === "root") {
    const root = await getRootProposal(id);
    if (!root) return null;
    base = {
      ...base,
      root,
      status: root.envelope_status,
      title: root.title || `Root #${id}`,
      daoId: BigInt(root.dao_id),
      rootId: id,
      evidenceCaseId: BigInt(root.envelope_case_id),
      currentVerdictId: BigInt(root.current_verdict_id),
      isFinal: ENVELOPE_FINAL.has(root.envelope_status),
      isFaithfulFinal: root.envelope_status === "ENVELOPE_FAITHFUL",
    };
  } else {
    const fork = await getFork(id);
    if (!fork) return null;
    base = {
      ...base,
      fork,
      status: fork.status,
      title: fork.body.title || `Fork #${id}`,
      daoId: BigInt(fork.dao_id),
      rootId: BigInt(fork.root_id),
      evidenceCaseId: BigInt(fork.evidence_case_id),
      currentVerdictId: BigInt(fork.current_verdict_id),
      isFinal: FORK_FINAL.has(fork.status),
      isFaithfulFinal: fork.status === "FINALIZED_FAITHFUL",
    };
  }

  if (kind === "fork") {
    base.rootProposal = await getRootProposal(base.rootId!);
    const f = base.fork!;
    if (f.parent_kind === "PARENT_FORK") {
      base.parentFork = await getFork(BigInt(f.parent_id));
    }
  }

  const evidenceCaseId = base.evidenceCaseId!;
  const kase =
    evidenceCaseId > 0n ? await getCase(evidenceCaseId) : undefined;

  const evidence: { id: bigint; ev: Evidence }[] = [];
  if (evidenceCaseId > 0n) {
    const evIds = await collectAll((c) =>
      listEvidenceOfCase(evidenceCaseId, c),
    );
    for (const eid of evIds) {
      const ev = await getEvidence(eid);
      if (ev) evidence.push({ id: eid, ev });
    }
  }

  const currentVerdictId = base.currentVerdictId!;
  const verdict =
    currentVerdictId > 0n ? await getVerdict(currentVerdictId) : undefined;

  const verdictHistory = await collectAll((c) =>
    getVerdictHistory(id, targetKindConst, c),
  );

  const challengeIds = await collectAll((c) =>
    listChallenges(id, targetKindConst, c),
  );
  const challenges: ChallengeView[] = [];
  for (const cid of challengeIds) {
    const challenge = await getChallenge(cid);
    if (!challenge) continue;
    const cCase =
      BigInt(challenge.case_id) > 0n
        ? await getCase(BigInt(challenge.case_id))
        : undefined;
    challenges.push({ id: cid, challenge, case: cCase });
  }
  const openChallenge = challenges.find((c) =>
    CHALLENGE_OPEN_STATES.has(c.challenge.status),
  );

  const bondIds = await collectAll((c) =>
    listBondsByTarget(id, targetKindConst, c),
  );
  const bonds: { id: bigint; bond: Bond }[] = [];
  for (const bid of bondIds) {
    const bond = await getBond(bid);
    if (bond) bonds.push({ id: bid, bond });
  }

  return {
    ...(base as TargetView),
    case: kase,
    evidence,
    verdict,
    verdictHistory,
    challenges,
    openChallenge,
    bonds,
  };
}
