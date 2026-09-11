import {
  collectAll,
  getConstants,
  getDao,
  listDaos,
  listRootsByDao,
} from "../lib/api";
import { formatGen } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { buildRootTree, type TreeNode } from "../lib/tree";
import type { Dao } from "../lib/types";
import { SectionHead, Spinner } from "../components/ui";
import { LineageTree } from "../components/LineageTree";
import { Mark } from "../components/Logo";

interface RootEntry {
  daoId: bigint;
  dao: Dao;
  tree: TreeNode;
}

async function loadTrees(): Promise<RootEntry[]> {
  const daoIds = await collectAll((c) => listDaos(c));
  const out: RootEntry[] = [];
  for (const daoId of daoIds) {
    const dao = await getDao(daoId);
    if (!dao) continue;
    const rootIds = await collectAll((c) => listRootsByDao(daoId, c));
    for (const rid of rootIds) {
      const tree = await buildRootTree(rid);
      if (tree) out.push({ daoId, dao, tree });
    }
  }
  return out;
}

function HeroBranch() {
  return (
    <svg
      className="hero-branch"
      width="220"
      height="86"
      viewBox="0 0 220 86"
      fill="none"
      aria-hidden="true"
    >
      <path d="M8 6 V80" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M8 24 H70 Q92 24 92 46 V60"
        stroke="var(--coral)"
        strokeWidth="1.5"
      />
      <path
        d="M8 44 H150 Q172 44 172 66 V78"
        stroke="var(--coral)"
        strokeWidth="1.5"
        opacity="0.7"
      />
      <path d="M8 62 H54" stroke="var(--coral)" strokeWidth="1.5" opacity="0.5" />
      <circle cx="8" cy="6" r="3" fill="var(--blue)" />
      <circle cx="92" cy="61" r="3" fill="var(--coral)" />
      <circle cx="172" cy="79" r="3" fill="var(--coral)" opacity="0.7" />
      <circle cx="56" cy="62" r="2.4" fill="var(--coral)" opacity="0.5" />
      <circle cx="8" cy="80" r="3" fill="currentColor" />
    </svg>
  );
}

export function Explorer() {
  const trees = useAsync(loadTrees, []);
  const consts = useAsync(getConstants, []);

  const totalForks = (trees.data ?? []).reduce(
    (n, e) => n + (e.tree.children.length ? countDescendants(e.tree) : 0),
    0,
  );

  return (
    <div className="stack-lg">
      <section className="hero">
        <p className="eyebrow">Governance Fork</p>
        <h1 className="display">
          Governance doesn't have to end at <span className="em">yes</span> or{" "}
          <span className="em">no</span>.
        </h1>
        <p className="lede">
          Explore real governance proposals and the alternatives communities
          built from them — each one adjudicated on GenLayer for whether it stays
          faithful to the original intent.
        </p>
        <HeroBranch />
      </section>

      <div className="count-strip">
        {consts.data ? (
          <>
            <span>
              <b>{(trees.data ?? []).length}</b> root proposal
              {(trees.data ?? []).length === 1 ? "" : "s"}
            </span>
            <span>
              <b>{totalForks}</b> fork{totalForks === 1 ? "" : "s"}
            </span>
            <span>
              envelope bond <b>{formatGen(consts.data.envelope_bond)}</b>
            </span>
            <span>
              fork bond <b>{formatGen(consts.data.fork_creation_bond)}</b>
            </span>
            <span>
              challenge bond <b>{formatGen(consts.data.challenge_bond)}</b>
            </span>
            <span>
              treasury pool <b>{formatGen(consts.data.treasury_pool)}</b>
            </span>
            {consts.data.paused && <span style={{ color: "var(--red-ink)" }}>PAUSED</span>}
          </>
        ) : (
          <span className="faint">reading contract…</span>
        )}
      </div>

      <div className="section">
        <SectionHead
          eyebrow="Registry"
          title="Proposal lineage"
          right={
            <button
              className="small"
              onClick={trees.refresh}
              disabled={trees.loading}
            >
              {trees.loading ? "Reading…" : "Refresh"}
            </button>
          }
        />

        {trees.loading && !trees.data && (
          <div className="row muted">
            <Spinner /> Walking the tree from StudioNet…
          </div>
        )}
        {trees.error && <div className="note red">{trees.error}</div>}

        {trees.data && trees.data.length === 0 && (
          <div className="panel-inset">
            <div className="row" style={{ gap: 14 }}>
              <Mark size={26} />
              <div>
                <div style={{ fontWeight: 550 }}>Nothing imported yet.</div>
                <div className="muted tiny">
                  Import the first governance proposal from the{" "}
                  <button className="link" onClick={() => navigate({ name: "build" })}>
                    Build
                  </button>{" "}
                  tab.
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="stack-lg">
          {(trees.data ?? []).map((e) => (
            <div key={e.tree.id.toString()}>
              <div
                className="between"
                style={{ marginBottom: 12, alignItems: "baseline" }}
              >
                <span className="eyebrow">
                  {e.dao.name} · DAO {e.daoId.toString()}
                </span>
                <a
                  className="tiny mono faint"
                  href={e.dao.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {e.dao.url}
                </a>
              </div>
              <LineageTree root={e.tree} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function countDescendants(node: TreeNode): number {
  return node.children.length + node.children.reduce((n, c) => n + countDescendants(c), 0);
}
