import { useState } from "react";
import * as api from "../lib/api";
import { getActiveWriteClient as g } from "../lib/activeClient";
import { formatGen, sameAddr } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { useTx } from "../lib/useTx";
import { useWallet } from "../lib/wallet";
import type { Bond } from "../lib/types";
import { AddrChip, Card, Empty, Notice, Spinner, StatusBadge } from "../components/ui";
import { Guarded } from "../components/Guarded";
import { TxProgress } from "../components/TxProgress";

const SCAN_CAP = 400;

async function scanBonds(): Promise<{ id: bigint; bond: Bond }[]> {
  const out: { id: bigint; bond: Bond }[] = [];
  for (let i = 1n; i <= BigInt(SCAN_CAP); i++) {
    const bond = await api.getBond(i);
    if (!bond) break; // dense ids — first gap = end
    out.push({ id: i, bond });
  }
  return out;
}

export function BondsPanel() {
  const w = useWallet();
  const all = useAsync(scanBonds, []);
  const tx = useTx();
  const [lookupId, setLookupId] = useState("");

  const mine = (all.data ?? []).filter((b) =>
    sameAddr(b.bond.owner, w.account),
  );
  const unassigned = mine.filter((b) => BigInt(b.bond.target_id) === 0n);
  const assigned = mine.filter((b) => BigInt(b.bond.target_id) !== 0n);

  return (
    <div className="stack">
      <Card
        title="Bonds"
        actions={
          <button className="small" onClick={all.refresh} disabled={all.loading}>
            {all.loading ? "Scanning…" : "Rescan"}
          </button>
        }
      >
        <p className="muted" style={{ marginTop: 0 }}>
          Every bond is 0.1 GEN, locked with the single payable method{" "}
          <code>lock_bond(purpose)</code> and then consumed by the matching
          action. <code>refund + slash</code> always equals the locked amount; a
          successful challenge also earns a 0.05 GEN reward from the treasury
          pool. Settlement is replay-safe.
        </p>
        {!w.account && (
          <Notice tone="info">
            Connect a wallet to see and settle your bonds.
          </Notice>
        )}
        {all.loading && (
          <div className="row">
            <Spinner /> <span className="muted">Reading bonds 1…{SCAN_CAP}</span>
          </div>
        )}
        {all.error && <div className="notice bad">{all.error}</div>}
      </Card>

      <TxProgress tx={tx} />

      {w.account && (
        <>
          <Card title={`Unassigned bonds (${unassigned.length})`}>
            <p className="muted tiny" style={{ marginTop: 0 }}>
              Locked but never consumed (or locked with a wrong amount / unknown
              purpose). Always 100% refundable — settle any time.
            </p>
            {unassigned.length === 0 ? (
              <Empty>None.</Empty>
            ) : (
              <BondList
                items={unassigned}
                tx={tx}
                onSettled={all.refresh}
                canSettle={() => true}
              />
            )}
          </Card>

          <Card title={`Assigned bonds (${assigned.length})`}>
            {assigned.length === 0 ? (
              <Empty>None.</Empty>
            ) : (
              <BondList
                items={assigned}
                tx={tx}
                onSettled={all.refresh}
                canSettle={(b) => !b.bond.settled}
                showTarget
              />
            )}
          </Card>
        </>
      )}

      <Card title="Look up a bond by id">
        <div className="row">
          <input
            style={{ maxWidth: 160 }}
            value={lookupId}
            onChange={(e) => setLookupId(e.target.value.replace(/\D/g, ""))}
            placeholder="bond id"
          />
          <button
            className="small"
            disabled={!lookupId}
            onClick={() => setLookupId(lookupId)}
          >
            Look up
          </button>
        </div>
        {lookupId && <SingleBond id={BigInt(lookupId)} tx={tx} onSettled={all.refresh} />}
      </Card>
    </div>
  );
}

function BondList({
  items,
  tx,
  onSettled,
  canSettle,
  showTarget,
}: {
  items: { id: bigint; bond: Bond }[];
  tx: ReturnType<typeof useTx>;
  onSettled: () => void;
  canSettle: (b: { id: bigint; bond: Bond }) => boolean;
  showTarget?: boolean;
}) {
  return (
    <div className="list">
      {items.map((b) => (
        <div
          className="list-item"
          key={b.id.toString()}
          style={{ cursor: "default", alignItems: "flex-start" }}
        >
          <div className="grow">
            <div className="primary-line">
              Bond #{b.id.toString()} · {b.bond.purpose} ·{" "}
              {formatGen(b.bond.amount)}
            </div>
            <div className="tiny faint">
              owner <AddrChip addr={b.bond.owner} />
              {showTarget && BigInt(b.bond.target_id) !== 0n && (
                <>
                  {" · "}
                  <a
                    href={`#/${b.bond.target_kind === "FORK" ? "fork" : "root"}/${b.bond.target_id}`}
                    onClick={() =>
                      navigate(
                        b.bond.target_kind === "FORK"
                          ? { name: "fork", id: BigInt(b.bond.target_id) }
                          : { name: "root", id: BigInt(b.bond.target_id) },
                      )
                    }
                  >
                    {b.bond.target_kind} #{b.bond.target_id.toString()}
                  </a>
                </>
              )}
              {b.bond.settled && (
                <>
                  {" · refund "}
                  {formatGen(b.bond.refund_amount)}
                  {" · slash "}
                  {formatGen(b.bond.slash_amount)}
                  {BigInt(b.bond.reward_amount) > 0n &&
                    ` · reward ${formatGen(b.bond.reward_amount)}`}
                </>
              )}
            </div>
          </div>
          <div className="stack" style={{ gap: 4, alignItems: "flex-end" }}>
            <StatusBadge value={b.bond.settlement_kind} />
            {!b.bond.settled && canSettle(b) && (
              <Guarded>
                <button
                  className="small primary"
                  disabled={tx.busy}
                  onClick={() =>
                    tx.run(() => api.settleBond(g(), b.id), {
                      afterConfirm: onSettled,
                    })
                  }
                >
                  Settle
                </button>
              </Guarded>
            )}
            {!b.bond.settled && !canSettle(b) && (
              <span className="tiny faint">
                settle after the target is finalized
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function SingleBond({
  id,
  tx,
  onSettled,
}: {
  id: bigint;
  tx: ReturnType<typeof useTx>;
  onSettled: () => void;
}) {
  const q = useAsync(() => api.getBond(id), [id.toString()]);
  if (q.loading) return <div className="row" style={{ marginTop: 8 }}><Spinner /></div>;
  if (!q.data) return <Empty>Bond #{id.toString()} not found.</Empty>;
  return (
    <div style={{ marginTop: 10 }}>
      <BondList
        items={[{ id, bond: q.data }]}
        tx={tx}
        onSettled={() => {
          q.refresh();
          onSettled();
        }}
        canSettle={(b) => !b.bond.settled}
        showTarget
      />
    </div>
  );
}
