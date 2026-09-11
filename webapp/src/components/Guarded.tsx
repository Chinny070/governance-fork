import type { ReactNode } from "react";
import { useWallet } from "../lib/wallet";

/**
 * Wraps write actions. Renders children only when a wallet is connected on
 * StudioNet; otherwise shows the reason and a fix control.
 */
export function Guarded({ children }: { children: ReactNode }) {
  const w = useWallet();

  if (!w.account) {
    return (
      <div className="note blue">
        Connect a wallet to act.{" "}
        <button
          className="primary small"
          onClick={w.connect}
          disabled={w.connecting}
        >
          {w.connecting ? "Connecting…" : "Connect wallet"}
        </button>
      </div>
    );
  }
  if (!w.onStudionet) {
    return (
      <div className="note coral">
        Wrong network.{" "}
        <button className="small" onClick={w.switchNetwork}>
          Switch to StudioNet
        </button>
      </div>
    );
  }
  return <>{children}</>;
}
