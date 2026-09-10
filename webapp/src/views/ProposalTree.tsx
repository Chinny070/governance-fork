import { buildRootTree, type TreeNode } from "../lib/tree";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { Empty, Spinner, StatusBadge } from "../components/ui";

function Node({
  node,
  selected,
}: {
  node: TreeNode;
  selected?: { kind: string; id: bigint };
}) {
  const isSel =
    selected && selected.kind === node.kind && selected.id === node.id;
  return (
    <li>
      <span
        className={`node ${node.kind === "root" ? "root" : ""} ${
          isSel ? "selected" : ""
        }`}
        onClick={() =>
          navigate(
            node.kind === "root"
              ? { name: "root", id: node.id }
              : { name: "fork", id: node.id },
          )
        }
      >
        <span>
          {node.kind === "root" ? "◆" : "↳"} {node.label}
        </span>
        <span className="faint tiny">
          {node.kind === "root" ? "root" : "fork"} #{node.id.toString()}
        </span>
        <StatusBadge value={node.status} />
      </span>
      {node.children.length > 0 && (
        <ul>
          {node.children.map((c) => (
            <Node
              key={`${c.kind}-${c.id}`}
              node={c}
              selected={selected}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

export function ProposalTree({
  rootId,
  selected,
  reloadKey,
}: {
  rootId: bigint;
  selected?: { kind: string; id: bigint };
  reloadKey?: number;
}) {
  const tree = useAsync(() => buildRootTree(rootId), [rootId, reloadKey]);

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>Proposal tree</h3>
        <button className="small" onClick={tree.refresh} disabled={tree.loading}>
          {tree.loading ? "…" : "Refresh"}
        </button>
      </div>
      <p className="muted tiny" style={{ marginTop: 6 }}>
        The root proposal and every semantic-descendant fork. A fork only
        becomes forkable itself once it is finalized FAITHFUL.
      </p>
      {tree.loading && (
        <div className="row">
          <Spinner /> <span className="muted">Walking lineage…</span>
        </div>
      )}
      {tree.error && (
        <div className="notice bad">
          Could not load the lineage: {tree.error}{" "}
          <button className="small" onClick={tree.refresh}>
            Retry
          </button>
        </div>
      )}
      {tree.data ? (
        <div className="tree">
          <ul>
            <Node node={tree.data} selected={selected} />
          </ul>
        </div>
      ) : (
        !tree.loading && !tree.error && <Empty>Root not found.</Empty>
      )}
    </div>
  );
}
