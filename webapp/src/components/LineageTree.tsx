import { navigate } from "../lib/router";
import { StatusTag } from "./ui";
import type { TreeNode } from "../lib/tree";

const FINAL_FAITHFUL = new Set(["ENVELOPE_FAITHFUL", "FINALIZED_FAITHFUL"]);

type RailType = "spacer" | "pipe" | "tee" | "ell";

function Rail({ type }: { type: RailType }) {
  return (
    <span className={`lin-rail ${type}`} aria-hidden="true">
      {type === "pipe" && <i className="v-full" />}
      {type === "tee" && (
        <>
          <i className="v-up" />
          <i className="v-down" />
          <i className="h" />
        </>
      )}
      {type === "ell" && (
        <>
          <i className="v-up" />
          <i className="h" />
        </>
      )}
    </span>
  );
}

function verdictLabel(v?: string): { text: string; cls: string } | null {
  if (!v) return null;
  const map: Record<string, string> = {
    FAITHFUL: "faithful",
    NOT_FAITHFUL: "not faithful",
    UNCLEAR_VERDICT: "unclear",
    INVALID: "invalid",
  };
  const cls =
    v === "FAITHFUL" ? "v-faithful" : v === "NOT_FAITHFUL" ? "v-not" : "";
  return { text: map[v] ?? v.toLowerCase(), cls };
}

function Meta({ node }: { node: TreeNode }) {
  const out: React.ReactNode[] = [];
  const add = (n: React.ReactNode) => {
    if (out.length) out.push(<span className="sep" key={`s${out.length}`}>·</span>);
    out.push(<span key={`m${out.length}`}>{n}</span>);
  };

  add(
    node.kind === "root"
      ? "root"
      : `fork ${String(node.forkOrdinal ?? "").padStart(2, "0")} · d${node.depth}`,
  );
  const v = verdictLabel(node.verdict);
  if (v) add(<span className={v.cls}>{v.text}</span>);
  if (typeof node.evidenceCount === "number" && node.evidenceCount > 0)
    add(`${node.evidenceCount} evid`);
  if (node.challengeTotal && node.challengeTotal > 0)
    add(
      <span className={node.challengeOpen ? "v-chal" : undefined}>
        {node.challengeTotal} chal{node.challengeOpen ? " open" : ""}
      </span>,
    );
  if (node.bond && node.bond !== "none")
    add(
      <span
        className={
          node.bond === "slashed" || node.bond === "mixed" ? "v-chal" : undefined
        }
      >
        bond {node.bond}
      </span>,
    );

  return <span className="lin-meta">{out}</span>;
}

function Node({
  node,
  ancestors,
  isLast,
  isRoot,
  currentId,
  currentKind,
}: {
  node: TreeNode;
  ancestors: boolean[];
  isLast: boolean;
  isRoot: boolean;
  currentId?: bigint;
  currentKind?: string;
}) {
  const rails: RailType[] = isRoot
    ? []
    : [
        ...ancestors.map<RailType>((hasNext) => (hasNext ? "pipe" : "spacer")),
        isLast ? "ell" : "tee",
      ];
  const childAncestors = isRoot ? [] : [...ancestors, !isLast];
  const isCurrent =
    currentId != null && node.id === currentId && node.kind === currentKind;

  const go = () =>
    navigate(
      node.kind === "root"
        ? { name: "root", id: node.id }
        : { name: "fork", id: node.id },
    );

  const forkable = FINAL_FAITHFUL.has(node.status);
  const emptyBranch = node.children.length === 0 && (isRoot || forkable);

  return (
    <>
      <div className="lin-row">
        {rails.map((t, i) => (
          <Rail key={i} type={t} />
        ))}
        <button
          className={`lin-node${isCurrent ? " current" : ""}`}
          onClick={go}
        >
          <span className={`lin-marker ${node.kind}`}>
            {node.kind === "root" ? "●" : "◆"}
          </span>
          <span className="lin-title">{node.label}</span>
          <StatusTag value={node.status} dot={false} />
          <Meta node={node} />
        </button>
      </div>

      {node.children.map((c, i) => (
        <Node
          key={`${c.kind}-${c.id}`}
          node={c}
          ancestors={childAncestors}
          isLast={i === node.children.length - 1}
          isRoot={false}
          currentId={currentId}
          currentKind={currentKind}
        />
      ))}

      {emptyBranch && (
        <div className="lin-row">
          {childAncestors.map((hasNext, i) => (
            <Rail key={i} type={hasNext ? "pipe" : "spacer"} />
          ))}
          <Rail type="ell" />
          <span className="lin-empty">
            {isRoot ? (
              <>
                No alternatives yet.{" "}
                <button className="link" onClick={go}>
                  <strong>Fork this proposal.</strong>
                </button>
              </>
            ) : (
              "no descendants"
            )}
          </span>
        </div>
      )}
    </>
  );
}

export function LineageTree({
  root,
  currentId,
  currentKind,
}: {
  root: TreeNode;
  currentId?: bigint;
  currentKind?: "root" | "fork";
}) {
  return (
    <div className="lin">
      <Node
        node={root}
        ancestors={[]}
        isLast
        isRoot
        currentId={currentId}
        currentKind={currentKind}
      />
    </div>
  );
}
