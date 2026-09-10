import { collectAll, getFork, getRootProposal, listForksOfParent } from "./api";
import type { Fork, RootProposal } from "./types";

export interface TreeNode {
  kind: "root" | "fork";
  id: bigint;
  label: string;
  status: string;
  depth: number;
  root?: RootProposal;
  fork?: Fork;
  children: TreeNode[];
}

/** Build the full lineage tree for a root proposal id. */
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

  async function attachChildren(parentId: bigint, parent: TreeNode) {
    if (parent.depth > 12) return;
    const childIds = await collectAll((c) => listForksOfParent(parentId, c));
    for (const fid of childIds) {
      const fork = await getFork(fid);
      if (!fork) continue;
      const child: TreeNode = {
        kind: "fork",
        id: fid,
        label: fork.body.title || `Fork #${fid}`,
        status: fork.status,
        depth: parent.depth + 1,
        fork,
        children: [],
      };
      parent.children.push(child);
      await attachChildren(fid, child);
    }
  }

  await attachChildren(rootId, node);
  return node;
}

export function flatten(node: TreeNode): TreeNode[] {
  return [node, ...node.children.flatMap(flatten)];
}
