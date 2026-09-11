import { explorerTxUrl } from "../lib/contract";
import type { TxState } from "../lib/useTx";

const STEPS = ["signing", "mining", "reading", "done"] as const;

export function TxProgress({ tx }: { tx: TxState }) {
  if (tx.phase === "idle") return null;

  const bad =
    tx.phase === "undetermined" ||
    tx.phase === "reverted" ||
    tx.phase === "error";
  const done = tx.phase === "done";
  const activeIdx = STEPS.indexOf(tx.phase as (typeof STEPS)[number]);

  const kind = done
    ? "ok"
    : tx.phase === "undetermined"
      ? "warn"
      : bad
        ? "err"
        : "";

  return (
    <div className={`tx ${kind}`}>
      <div className="tx-track">
        {STEPS.map((_, i) => {
          let c = "";
          if (bad) c = i === 0 ? "bad" : "";
          else if (done || i <= activeIdx) c = "on";
          return <span key={i} className={`s ${c}`} />;
        })}
      </div>
      {tx.message && <div className={`tx-msg ${kind}`}>{tx.message}</div>}
      {tx.hash && (
        <div className="tiny faint mono" style={{ marginTop: 6 }}>
          <a href={explorerTxUrl(tx.hash)} target="_blank" rel="noreferrer">
            {tx.hash.slice(0, 12)}…{tx.hash.slice(-8)}
          </a>
        </div>
      )}
    </div>
  );
}
