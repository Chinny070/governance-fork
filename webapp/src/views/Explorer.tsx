import { useMemo } from "react";
import {
  collectAll,
  getConstants,
  getDao,
  getRootProposal,
  listDaos,
  listRootsByDao,
} from "../lib/api";
import { formatGen } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import type { Dao, RootProposal } from "../lib/types";
import { Card, Empty, Spinner, StatusBadge } from "../components/ui";

interface DaoWithRoots {
  id: bigint;
  dao: Dao;
  roots: { id: bigint; root: RootProposal }[];
}

async function loadRegistry(): Promise<DaoWithRoots[]> {
  const daoIds = await collectAll((c) => listDaos(c));
  const out: DaoWithRoots[] = [];
  for (const id of daoIds) {
    const dao = await getDao(id);
    if (!dao) continue;
    const rootIds = await collectAll((c) => listRootsByDao(id, c));
    const roots: { id: bigint; root: RootProposal }[] = [];
    for (const rid of rootIds) {
      const root = await getRootProposal(rid);
      if (root) roots.push({ id: rid, root });
    }
    out.push({ id, dao, roots });
  }
  return out;
}

export function Explorer() {
  const reg = useAsync(loadRegistry, []);
  const consts = useAsync(getConstants, []);

  const totalRoots = useMemo(
    () => (reg.data ?? []).reduce((n, d) => n + d.roots.length, 0),
    [reg.data],
  );

  return (
    <div className="stack">
      <Card
        title="Registry"
        actions={
          <button className="small" onClick={reg.refresh} disabled={reg.loading}>
            {reg.loading ? "Refreshing…" : "Refresh"}
          </button>
        }
      >
        <p className="muted" style={{ marginTop: 0 }}>
          Every DAO, root proposal and semantic-descendant fork recorded on the
          production contract. Read directly from GenLayer StudioNet — no wallet
          required.
        </p>

        {consts.data && (
          <div className="chips" style={{ marginBottom: 12 }}>
            <span className="badge neutral">
              envelope bond {formatGen(consts.data.envelope_bond)}
            </span>
            <span className="badge neutral">
              fork bond {formatGen(consts.data.fork_creation_bond)}
            </span>
            <span className="badge neutral">
              challenge bond {formatGen(consts.data.challenge_bond)}
            </span>
            <span className="badge neutral">
              flip reward {formatGen(consts.data.challenger_flip_reward)}
            </span>
            <span className="badge neutral">
              treasury pool {formatGen(consts.data.treasury_pool)}
            </span>
            <span
              className={`badge ${consts.data.paused ? "bad" : "ok"}`}
              title="Contract pause switch"
            >
              {consts.data.paused ? "PAUSED" : "active"}
            </span>
          </div>
        )}

        {reg.loading && (
          <div className="row">
            <Spinner /> <span className="muted">Loading registry…</span>
          </div>
        )}
        {reg.error && <div className="notice bad">{reg.error}</div>}
        {reg.data && (
          <div className="tiny muted">
            {reg.data.length} DAO{reg.data.length === 1 ? "" : "s"} · {totalRoots}{" "}
            root proposal{totalRoots === 1 ? "" : "s"}
          </div>
        )}
      </Card>

      {(reg.data ?? []).map((d) => (
        <Card
          key={d.id.toString()}
          title={
            <span>
              {d.dao.name}{" "}
              <span className="faint tiny">DAO #{d.id.toString()}</span>
            </span>
          }
        >
          <div className="tiny muted" style={{ marginBottom: 10 }}>
            <a href={d.dao.url} target="_blank" rel="noreferrer">
              {d.dao.url}
            </a>
          </div>
          {d.roots.length === 0 ? (
            <Empty>No root proposals imported for this DAO yet.</Empty>
          ) : (
            <div className="list">
              {d.roots.map(({ id, root }) => (
                <button
                  key={id.toString()}
                  className="list-item"
                  onClick={() => navigate({ name: "root", id })}
                >
                  <div className="grow">
                    <div className="primary-line">{root.title}</div>
                    <div className="tiny faint">
                      root #{id.toString()} · {root.external_proposal_id} ·{" "}
                      {root.identity_status}
                    </div>
                  </div>
                  <StatusBadge value={root.envelope_status} />
                </button>
              ))}
            </div>
          )}
        </Card>
      ))}

      {reg.data && reg.data.length === 0 && (
        <Card>
          <Empty>
            No DAOs registered yet. Switch to <strong>Build</strong> to import
            the first governance proposal.
          </Empty>
        </Card>
      )}
    </div>
  );
}
