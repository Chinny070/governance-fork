import { useState } from "react";
import * as api from "../lib/api";
import { getActiveWriteClient as g } from "../lib/activeClient";
import { formatGen, sameAddr } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { useTx } from "../lib/useTx";
import { useWallet } from "../lib/wallet";
import type { Bond } from "../lib/types";
import { AddrChip, Empty, Note, SectionHead, Spinner, StatusTag } from "../components/ui";
import { Guarded } from "../components/Guarded";
import { TxProgress } from "../components/TxProgress";

const SCAN_CAP = 400;

async function scanBonds(): Promise<{ id: bigint; bond: Bond }[]> {
  const out: { id: bigint; bond: Bond }[] = [];
  for (let i = 1n; i <= BigInt(SCAN_CAP); i++) {
    const bond = await api.getBond(i);
    if (!bond) break;
    out.push({ id: i, bond });
  }
  return out;
}

function targetHref(bond: Bond): { label: string; go: () => void } | null {
  if (BigInt(bond.target_id) === 0n) return null;
  const isFork = bond.target_kind === "FORK";
  return {
    label: `${bond.target_kind} #${bond.target_id.toString()}`,
    go: () =>
      navigate(
        isFork
          ? { name: "fork", id: BigInt(bond.target_id) }
          : { name: "root", id: BigInt(bond.target_id) },
      ),
  };
}

export function BondsPanel() {
  const w = useWallet();
  const all = useAsync(scanBonds, []);
  const tx = useTx();
  const [scope, setScope] = useState<"mine" | "all">("mine");
  const [lookup, setLookup] = useState("");

  const rows = (all.data ?? []).filter((b) =>
    scope === "all" ? true : sameAddr(b.bond.owner, w.account),
  );

  return (
    <div className="stack">
      <div>
        <p className="eyebrow">Bonds</p>
        <h1 className="display" style={{ fontSize: "clamp(24px,3.2vw,32px)" }}>
          An accountability ledger.
        </h1>
        <p className="lede">
          Every economically meaningful action posts a{" "}
          {formatGen(api.BOND_AMOUNT_WEI)} bond via the single payable method{" "}
          <code>lock_bond</code>. On settlement <code>refund + slash</code> always
          equals the locked amount; a successful challenge also draws a{" "}
          {formatGen(api.CHALLENGER_FLIP_REWARD_WEI)} reward from the treasury
          pool. Settlement is replay-safe.
        </p>
      </div>

      <TxProgress tx={tx} />

      <div className="section">
        <SectionHead
          eyebrow="Ledger"
          title={
            <span className="row" style={{ gap: 4 }}>
              <button
                className={`link ${scope === "mine" ? "" : "faint"}`}
                onClick={() => setScope("mine")}
                style={{ fontWeight: scope === "mine" ? 600 : 400 }}
              >
                Mine
              </button>
              <span className="faint">/</span>
              <button
                className={`link ${scope === "all" ? "" : "faint"}`}
                onClick={() => setScope("all")}
                style={{ fontWeight: scope === "all" ? 600 : 400 }}
              >
                All
              </button>
            </span>
          }
          right={
            <button className="small" onClick={all.refresh} disabled={all.loading}>
              {all.loading ? "Scanning…" : "Rescan"}
            </button>
          }
        />

        {!w.account && scope === "mine" && (
          <Note tone="blue">Connect a wallet to see and settle your bonds.</Note>
        )}
        {all.loading && !all.data && (
          <div className="row muted">
            <Spinner /> Reading bonds 1…{SCAN_CAP}
          </div>
        )}
        {all.error && <div className="note red">{all.error}</div>}

        {all.data && rows.length === 0 && !all.loading && (
          <Empty>
            {scope === "mine"
              ? "No bonds for this wallet."
              : "No bonds locked on the contract yet."}
          </Empty>
        )}

        {rows.length > 0 && (
          <div className="ledger-scroll">
            <table className="ledger">
              <thead>
                <tr>
                  <th>Bond</th>
                  <th>Purpose</th>
                  <th>Associated with</th>
                  <th>Owner</th>
                  <th>Amount</th>
                  <th>Refund</th>
                  <th>Slash</th>
                  <th>Reward</th>
                  <th>Settlement</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map(({ id, bond }) => {
                  const tgt = targetHref(bond);
                  const unassigned = BigInt(bond.target_id) === 0n;
                  const settleable = !bond.settled;
                  return (
                    <tr key={id.toString()}>
                      <td className="num">#{id.toString()}</td>
                      <td className="mono tiny">{bond.purpose}</td>
                      <td>
                        {tgt ? (
                          <button className="link" onClick={tgt.go}>
                            {tgt.label}
                          </button>
                        ) : (
                          <span className="faint tiny">unassigned</span>
                        )}
                      </td>
                      <td>
                        <AddrChip addr={bond.owner} />
                      </td>
                      <td className="num">{formatGen(bond.amount)}</td>
                      <td className="num">
                        {bond.settled ? formatGen(bond.refund_amount) : "—"}
                      </td>
                      <td className="num">
                        {bond.settled ? formatGen(bond.slash_amount) : "—"}
                      </td>
                      <td className="num">
                        {bond.settled && BigInt(bond.reward_amount) > 0n
                          ? formatGen(bond.reward_amount)
                          : "—"}
                      </td>
                      <td>
                        <StatusTag value={bond.settlement_kind} dot={false} />
                      </td>
                      <td>
                        {settleable &&
                          sameAddr(bond.owner, w.account) &&
                          (unassigned ? (
                            <Guarded>
                              <button
                                className="small primary"
                                disabled={tx.busy}
                                onClick={() =>
                                  void tx.run(() => api.settleBond(g(), id), {
                                    afterConfirm: all.refresh,
                                  })
                                }
                              >
                                Refund
                              </button>
                            </Guarded>
                          ) : (
                            <span className="tiny faint nowrap">
                              after finality
                            </span>
                          ))}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <p className="tiny faint" style={{ marginTop: 12 }}>
          Unassigned bonds (a lock that was never consumed, or a wrong amount)
          are always 100% refundable. Assigned bonds settle once their target is
          finalized; a CHALLENGE bond settles only after the proposer/creator
          bond.
        </p>
      </div>

      <div className="section">
        <SectionHead eyebrow="Look up" title="Bond by id" />
        <div className="row">
          <input
            style={{ maxWidth: 150 }}
            value={lookup}
            onChange={(e) => setLookup(e.target.value.replace(/\D/g, ""))}
            placeholder="bond id"
          />
        </div>
        {lookup && <SingleBond id={BigInt(lookup)} onSettled={all.refresh} tx={tx} />}
      </div>
    </div>
  );
}

function SingleBond({
  id,
  onSettled,
  tx,
}: {
  id: bigint;
  onSettled: () => void;
  tx: ReturnType<typeof useTx>;
}) {
  const w = useWallet();
  const q = useAsync(() => api.getBond(id), [id.toString()]);
  if (q.loading)
    return (
      <div className="row muted" style={{ marginTop: 10 }}>
        <Spinner />
      </div>
    );
  if (!q.data) return <Empty>Bond #{id.toString()} not found.</Empty>;
  const b = q.data;
  return (
    <div className="dl" style={{ marginTop: 12 }}>
      <dt>Purpose</dt>
      <dd className="mono tiny">{b.purpose}</dd>
      <dt>Owner</dt>
      <dd>
        <AddrChip addr={b.owner} />
      </dd>
      <dt>Amount</dt>
      <dd className="num">{formatGen(b.amount)}</dd>
      <dt>Target</dt>
      <dd className="mono tiny">
        {BigInt(b.target_id) === 0n
          ? "unassigned"
          : `${b.target_kind} #${b.target_id.toString()}`}
      </dd>
      <dt>Settlement</dt>
      <dd>
        <StatusTag value={b.settlement_kind} dot={false} />
      </dd>
      {b.settled && (
        <>
          <dt>Disposition</dt>
          <dd className="num">
            refund {formatGen(b.refund_amount)} · slash {formatGen(b.slash_amount)}
            {BigInt(b.reward_amount) > 0n && ` · reward ${formatGen(b.reward_amount)}`}
          </dd>
        </>
      )}
      {!b.settled && sameAddr(b.owner, w.account) && (
        <>
          <dt />
          <dd>
            <Guarded>
              <button
                className="small primary"
                disabled={tx.busy}
                onClick={() =>
                  void tx.run(() => api.settleBond(g(), id), {
                    afterConfirm: () => {
                      q.refresh();
                      onSettled();
                    },
                  })
                }
              >
                Settle
              </button>
            </Guarded>
          </dd>
        </>
      )}
    </div>
  );
}
