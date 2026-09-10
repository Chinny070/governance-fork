import type { ReactNode } from "react";
import { useWallet } from "../lib/wallet";

/**
 * Wraps write actions. Renders children only when a wallet is connected on
 * StudioNet; otherwise shows the reason and a fix button.
 */
export function Guarded({ children }: { children: ReactNode }) {
  const w = useWallet();

  if (!w.account) {
    return (
      <div className="notice info">
        Connect a wallet to act on this proposal.{" "}
        <button className="small primary" onClick={w.connect} disabled={w.connecting}>
          {w.connecting ? "Connecting…" : "Connect wallet"}
        </button>
      </div>
    );
  }
  if (!w.onStudionet) {
    return (
      <div className="notice warn">
        Wrong network.{" "}
        <button className="small" onClick={w.switchNetwork}>
          Switch to StudioNet
        </button>
      </div>
    );
  }
  return <>{children}</>;
}

export function useWriteClientOrThrow() {
  const w = useWallet();
  return () => {
    if (!w.writeClient) throw new Error("Wallet not connected.");
    return w.writeClient;
  };
}
