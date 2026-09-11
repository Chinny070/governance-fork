import { useState } from "react";
import { CONTRACT_ADDRESS, explorerAddressUrl } from "../lib/contract";
import { shortAddr } from "../lib/format";
import { navigate, type Route } from "../lib/router";
import { useWallet } from "../lib/wallet";
import { Brand } from "./Logo";
import { Note } from "./ui";

const TABS: { name: Route["name"]; label: string }[] = [
  { name: "explore", label: "Explore" },
  { name: "build", label: "Build" },
  { name: "bonds", label: "Bonds" },
  { name: "about", label: "About" },
];

function WalletControl({ compact }: { compact?: boolean }) {
  const w = useWallet();

  if (!w.account) {
    return (
      <button
        className="primary small"
        onClick={w.connect}
        disabled={w.connecting}
      >
        {w.connecting ? "…" : compact ? "Connect" : "Connect wallet"}
      </button>
    );
  }

  return (
    <span className="wallet-chip">
      <span
        className={`net-dot ${w.onStudionet ? "ok" : "bad"}`}
        title={w.onStudionet ? "GenLayer StudioNet" : "Wrong network — tap switch"}
      />
      {!w.onStudionet && (
        <button className="link" onClick={w.switchNetwork}>
          switch
        </button>
      )}
      <span title={w.account}>{shortAddr(w.account, compact ? 3 : 4)}</span>
      <button
        className="ghost small"
        style={{ padding: "2px 6px" }}
        onClick={w.disconnect}
        title="Disconnect"
      >
        ✕
      </button>
    </span>
  );
}

/**
 * Proactive banner (distinct from Guarded's per-action gate): tells a
 * visitor with no wallet that read-only exploration works anyway, or
 * nudges a connected-but-wrong-network wallet to switch. Renders once,
 * globally, under the header.
 */
export function WalletNotice() {
  const w = useWallet();
  const body = w.error ? (
    <Note tone="red">{w.error}</Note>
  ) : !w.hasProvider ? (
    <Note tone="blue">
      No browser wallet detected — everything here works read-only. To submit
      transactions, install{" "}
      <a href="https://metamask.io" target="_blank" rel="noreferrer">
        MetaMask
      </a>{" "}
      and add GenLayer StudioNet.
    </Note>
  ) : w.account && !w.onStudionet ? (
    <Note tone="coral">
      Your wallet is on chain <code>{w.chainId ?? "?"}</code>. Governance Fork
      runs on GenLayer StudioNet (<code>0xf22f</code> / 61999).{" "}
      <button className="small" onClick={w.switchNetwork}>
        Switch / add network
      </button>
    </Note>
  ) : null;

  if (!body) return null;
  return <div style={{ marginBottom: 24 }}>{body}</div>;
}

export function Header({ tab }: { tab: Route["name"] }) {
  const [open, setOpen] = useState(false);

  const goto = (name: Route["name"]) => {
    navigate({ name } as Route);
    setOpen(false);
  };

  return (
    <header className="masthead">
      <div className="wrap masthead-in">
        <Brand onClick={() => goto("explore")} />

        <nav className="nav desk">
          {TABS.map((t) => (
            <button
              key={t.name}
              className={tab === t.name ? "on" : ""}
              onClick={() => goto(t.name)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <span className="spacer" />

        <a
          className="tiny mono wallet-full"
          href={explorerAddressUrl(CONTRACT_ADDRESS)}
          target="_blank"
          rel="noreferrer"
          title="Production contract on the explorer"
          style={{ color: "var(--ink-3)" }}
        >
          {shortAddr(CONTRACT_ADDRESS, 5)}
        </a>

        <span className="wallet-full">
          <WalletControl />
        </span>

        <span className="wallet-compact">
          <WalletControl compact />
        </span>
        <button
          className="menu-btn"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "✕" : "≡"}
        </button>
      </div>

      {open && (
        <div className="mobile-drawer">
          <div className="wrap">
            <nav className="nav">
              {TABS.map((t) => (
                <button
                  key={t.name}
                  className={tab === t.name ? "on" : ""}
                  onClick={() => goto(t.name)}
                >
                  {t.label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      )}
    </header>
  );
}
