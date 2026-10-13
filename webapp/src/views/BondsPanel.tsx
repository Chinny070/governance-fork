import { useState } from "react";
import * as api from "../lib/api";
import { getActiveWriteClient as g } from "../lib/activeClient";
import { formatGen, sameAddr } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { useTx } from "../lib/useTx";
import { useWallet } from "../lib/wallet";
import type { Bond, Payout } from "../lib/types";
import { AddrChip, Empty, Note, SectionHead, Spinner, StatusTag } from "../components/ui";
import { Guarded } from "../components/Guarded";
import { TxProgress } from "../components/TxProgress";

const SCAN_CAP = 400;

type BondRow = { id: bigint; bond: Bond; payoutId: bigint; payout?: Payout };

async function scanBonds(): Promise<BondRow[]> {
  const out: BondRow[] = [];
  for (let i = 1n; i <= BigInt(SCAN_CAP); i++) {
    const bond = await api.getBond(i);
    if (!bond) break;
    let payoutId = 0n;
    let payout: Payout | undefined;
    if (bond.settled) {
      payoutId = BigInt(await api.getPayoutOfBond(i));
      if (payoutId > 0n) payout = await api.getPayout(payoutId);
    }
    out.push({ id: i, bond, payoutId, payout });
  }
  return out;
}

const PAYOUT_HELP: Record<string, string> = {
  SENT: "Transfer sent; delivery not yet confirmed.",
  CONFIRMED: "Delivery confirmed (final).",
  DISPUTED: "Recipient reports it did not arrive; awaiting admin review.",
  RETRYABLE: "Admin attested non-delivery; one more send is allowed.",
};

function PayoutCell({
  row,
  account,
  admin,
  tx,
  refresh,
}: {
  row: BondRow;
  account?: string | null;
  admin?: string;
  tx: ReturnType<typeof useTx>;
  refresh: () => void;
}) {
  const po = row.payout;
  if (!row.bond.settled) return <span className="faint tiny">—</span>;
  if (!po) return <span className="faint tiny">none (nothing owed)</span>;
  const isRecipient = sameAddr(po.recipient, account);
  const isAdmin = sameAddr(admin, account);
  const act = (fn: () => Promise<unknown>) =>
    void tx.run(async () => {
      const r = (await fn()) as { hash: string };
      return r as never;
    }, { afterConfirm: refresh });
  return (
    <div className="stack" style={{ gap: 4 }}>
      <div className="row" style={{ gap: 6 }}>
        <StatusTag value={po.status} dot={false} />
        <span className="tiny faint" title={PAYOUT_HELP[po.status] ?? ""}>
          #{row.payoutId.toString()} · {po.attempts} attempt{Number(po.attempts) === 1 ? "" : "s"}
        </span>
      </div>
      <Guarded>
        <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>
          {(po.status === "SENT" || po.status === "DISPUTED") && (isRecipient || isAdmin) && (
            <button className="small" disabled={tx.busy}
              onClick={() => act(() => api.confirmPayout(g(), row.payoutId))}>
              Confirm received
            </button>
          )}
          {po.status === "SENT" && isRecipient && (
            <button className="small" disabled={tx.busy}
              onClick={() => act(() => api.reportPayoutNotReceived(g(), row.payoutId))}>
              Not received
            </button>
          )}
          {(po.status === "SENT" || po.status === "DISPUTED") && isAdmin && (
            <button className="small" disabled={tx.busy}
              onClick={() => act(() => api.resolvePayout(g(), row.payoutId, false))}>
              Admin: not delivered
            </button>
          )}
          {po.status === "RETRYABLE" && (isRecipient || isAdmin) && (
            <button className="small primary" disabled={tx.busy}
              onClick={() => act(() => api.retryPayout(g(), row.payoutId))}>
              Retry send
            </button>
          )}
        </div>
      </Guarded>
    </div>
  );
}

function ReservesCard() {
  const r = useAsync(api.getReserves, []);
  if (!r.data) return null;
  const d = r.data;
  const short = BigInt(d.shortfall) > 0n;
  return (
    <div className="section">
      <SectionHead eyebrow="Reconciliation" title="Contract reserves" />
      <div className="dl">
        <dt>Contract balance</dt>
        <dd className="num">{formatGen(d.contract_balance)}</dd>
        <dt>Locked bonds</dt>
        <dd className="num">{formatGen(d.locked_bonds)}</dd>
        <dt>Treasury pool</dt>
        <dd className="num">{formatGen(d.treasury_pool)}</dd>
        <dt>Payments awaiting confirmation</dt>
        <dd className="num">{formatGen(d.in_flight_payouts)}</dd>
        <dt>Shortfall</dt>
        <dd>
          <StatusTag value={short ? "SHORTFALL" : "COVERED"} dot={false} />{" "}
          <span className="num">{formatGen(d.shortfall)}</span>
        </dd>
      </div>
      <p className="tiny faint" style={{ marginTop: 8 }}>
        Balance must cover locked bonds plus the treasury pool. A payment that
        did not arrive can be retried only after the treasury admin attests it,
        and only from the treasury pool, never from other participants' bonds.
      </p>
    </div>
  );
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
  const consts = useAsync(api.getConstants, []);
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

      <ReservesCard />

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
                  <th>Payout</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map(({ id, bond, payoutId, payout }) => {
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
                        <PayoutCell
                          row={{ id, bond, payoutId, payout }}
                          account={w.account}
                          admin={consts.data?.treasury_addr as string | undefined}
                          tx={tx}
                          refresh={all.refresh}
                        />
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
