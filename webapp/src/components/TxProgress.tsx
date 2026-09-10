import { explorerTxUrl } from "../lib/contract";
import type { TxState } from "../lib/useTx";

const ORDER = ["signing", "mining", "reading", "done"] as const;

const LABEL: Record<string, string> = {
  signing: "Sign in wallet",
  mining: "Validator consensus",
  reading: "Re-read state",
  done: "Confirmed",
};

export function TxProgress({ tx }: { tx: TxState }) {
  if (tx.phase === "idle") return null;

  const terminalBad =
    tx.phase === "undetermined" ||
    tx.phase === "reverted" ||
    tx.phase === "error";

  const activeIdx = ORDER.indexOf(tx.phase as (typeof ORDER)[number]);

  return (
    <div className="stack" style={{ gap: 8, marginTop: 10 }}>
      <div className="tx-steps">
        {ORDER.map((step, i) => {
          let cls = "pending";
          if (terminalBad) {
            cls = i === 0 ? "error" : "pending";
          } else if (tx.phase === "done") {
            cls = "done";
          } else if (i < activeIdx) {
            cls = "done";
          } else if (i === activeIdx) {
            cls = "active";
          }
          return (
            <div key={step} className={`tx-step ${cls}`}>
              <span className="marker">
                {cls === "done" ? "✓" : cls === "error" ? "!" : i + 1}
              </span>
              <span>{LABEL[step]}</span>
            </div>
          );
        })}
      </div>

      {tx.message && (
        <div
          className={`notice ${
            tx.phase === "done"
              ? "ok"
              : tx.phase === "undetermined"
                ? "warn"
                : terminalBad
                  ? "bad"
                  : "info"
          }`}
        >
          {tx.message}
        </div>
      )}

      {tx.hash && (
        <div className="tiny">
          tx{" "}
          <a href={explorerTxUrl(tx.hash)} target="_blank" rel="noreferrer" className="mono">
            {tx.hash.slice(0, 12)}…{tx.hash.slice(-8)}
          </a>
        </div>
      )}
    </div>
  );
}
