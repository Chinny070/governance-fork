import { CONTRACT_ADDRESS, explorerAddressUrl } from "../lib/contract";
import { shortAddr } from "../lib/format";
import { useWallet } from "../lib/wallet";
import { Badge } from "./ui";

export function WalletBar() {
  const w = useWallet();

  return (
    <div className="row" style={{ gap: 10 }}>
      <a
        className="tiny mono"
        href={explorerAddressUrl(CONTRACT_ADDRESS)}
        target="_blank"
        rel="noreferrer"
        title="Production contract on the GenLayer explorer"
      >
        {shortAddr(CONTRACT_ADDRESS, 6)}
      </a>

      {w.account ? (
        <>
          {w.onStudionet ? (
            <Badge tone="ok" title="Wallet is on GenLayer StudioNet">
              StudioNet
            </Badge>
          ) : (
            <button className="small danger" onClick={w.switchNetwork}>
              Wrong network — switch to StudioNet
            </button>
          )}
          <Badge tone="neutral" title={w.account}>
            {shortAddr(w.account)}
          </Badge>
          <button className="small ghost" onClick={w.disconnect}>
            Disconnect
          </button>
        </>
      ) : (
        <button
          className="primary small"
          onClick={w.connect}
          disabled={w.connecting}
        >
          {w.connecting ? "Connecting…" : "Connect wallet"}
        </button>
      )}
    </div>
  );
}

export function WalletNotice() {
  const w = useWallet();
  if (w.error) {
    return <div className="notice bad">{w.error}</div>;
  }
  if (!w.hasProvider) {
    return (
      <div className="notice info">
        No browser wallet detected. You can explore everything read-only. To
        submit transactions, install{" "}
        <a href="https://metamask.io" target="_blank" rel="noreferrer">
          MetaMask
        </a>{" "}
        and add GenLayer StudioNet.
      </div>
    );
  }
  if (w.account && !w.onStudionet) {
    return (
      <div className="notice warn">
        Your wallet is on chain <code>{w.chainId ?? "?"}</code>. Governance Fork
        runs on GenLayer StudioNet (<code>0xf22f</code> / 61999).{" "}
        <button className="small" onClick={w.switchNetwork}>
          Switch / add network
        </button>
      </div>
    );
  }
  return null;
}
