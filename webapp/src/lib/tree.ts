import {
  collectAll,
  getBond,
  getCase,
  getFork,
  getRootProposal,
  getVerdict,
  listBondsByTarget,
  listChallenges,
  listEvidenceOfCase,
  listForksOfParent,
} from "./api";
import { CHALLENGE_OPEN_STATES, TARGET_KIND } from "./enums";
import type { Fork, RootProposal } from "./types";

export type BondSummary =
  | "none"
  | "locked"
  | "refunded"
  | "slashed"
  | "rewarded"
  | "mixed";

export interface TreeNode {
  kind: "root" | "fork";
  id: bigint;
  label: string;
  status: string;
  depth: number;
  forkOrdinal?: number; // 1-based position among siblings, forks only
  root?: RootProposal;
  fork?: Fork;
  children: TreeNode[];

  // enrichment (best-effort; undefined if the read failed)
  verdict?: string;
  caseState?: string;
  evidenceCount?: number;
  challengeTotal?: number;
  challengeOpen?: boolean;
  bond?: BondSummary;
}

async function enrich(node: TreeNode): Promise<void> {
  const kindConst =
    node.kind === "root" ? TARGET_KIND.ROOT_ENVELOPE : TARGET_KIND.FORK;
  const verdictId =
    node.kind === "root"
      ? BigInt(node.root!.current_verdict_id)
      : BigInt(node.fork!.current_verdict_id);
  const caseId =
    node.kind === "root"
      ? BigInt(node.root!.envelope_case_id)
      : BigInt(node.fork!.evidence_case_id);

  const jobs: Promise<void>[] = [];

  if (verdictId > 0n) {
    jobs.push(
      getVerdict(verdictId)
        .then((v) => {
          if (v) node.verdict = v.verdict;
        })
        .catch(() => {}),
    );
  }

  if (caseId > 0n) {
    jobs.push(
      getCase(caseId)
        .then((c) => {
          if (c) node.caseState = c.state;
        })
        .catch(() => {}),
    );
    jobs.push(
      collectAll((cur) => listEvidenceOfCase(caseId, cur))
        .then((ids) => {
          node.evidenceCount = ids.length;
        })
        .catch(() => {}),
    );
  }

  jobs.push(
    collectAll((cur) => listChallenges(node.id, kindConst, cur))
      .then(async (ids) => {
        node.challengeTotal = ids.length;
        // resolve open state
        const { getChallenge } = await import("./api");
        for (const cid of ids) {
          const ch = await getChallenge(cid).catch(() => undefined);
          if (ch && CHALLENGE_OPEN_STATES.has(ch.status)) node.challengeOpen = true;
        }
      })
      .catch(() => {}),
  );

  jobs.push(
    collectAll((cur) => listBondsByTarget(node.id, kindConst, cur))
      .then(async (ids) => {
        if (!ids.length) {
          node.bond = "none";
          return;
        }
        let refunded = 0;
        let slashed = 0;
        let rewarded = 0;
        let unsettled = 0;
        for (const bid of ids) {
          const b = await getBond(bid).catch(() => undefined);
          if (!b) continue;
          if (!b.settled) unsettled++;
          else if (BigInt(b.reward_amount) > 0n) rewarded++;
          else if (BigInt(b.slash_amount) > 0n) slashed++;
          else refunded++;
        }
        node.bond = unsettled
          ? "locked"
          : rewarded
            ? "rewarded"
            : slashed && refunded
              ? "mixed"
              : slashed
                ? "slashed"
                : "refunded";
      })
      .catch(() => {}),
  );

  await Promise.all(jobs);
}

/** Build the full, enriched lineage tree for a root proposal id. */
export async function buildRootTree(rootId: bigint): Promise<TreeNode | null> {
  const root = await getRootProposal(rootId);
  if (!root) return null;

  const node: TreeNode = {
    kind: "root",
    id: rootId,
    label: root.title || `Root #${rootId}`,
    status: root.envelope_status,
    depth: 0,
    root,
    children: [],
  };

  async function attach(parentId: bigint, parent: TreeNode) {
    if (parent.depth > 12) return;
    const childIds = await collectAll((c) => listForksOfParent(parentId, c));
    let ordinal = 0;
    for (const fid of childIds) {
      const fork = await getFork(fid);
      if (!fork) continue;
      ordinal += 1;
      const child: TreeNode = {
        kind: "fork",
        id: fid,
        label: fork.body.title || `Fork #${fid}`,
        status: fork.status,
        depth: parent.depth + 1,
        forkOrdinal: ordinal,
        fork,
        children: [],
      };
      parent.children.push(child);
      await attach(fid, child);
    }
  }

  await attach(rootId, node);

  // enrich every node (best-effort, in parallel)
  const all = flatten(node);
  await Promise.all(all.map((n) => enrich(n).catch(() => {})));

  return node;
}

export function flatten(node: TreeNode): TreeNode[] {
  return [node, ...node.children.flatMap(flatten)];
}
