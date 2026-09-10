import type { ReactNode } from "react";
import { STATUS_HELP } from "../lib/enums";
import { explorerAddressUrl } from "../lib/contract";
import { shortAddr, shortHex, isEmptyHex } from "../lib/format";

type Tone = "ok" | "warn" | "bad" | "info" | "neutral";

// Several contract enums share bare string values ("OPEN", "ADJUDICATING",
// "INVALID", …). A single lookup table can't hold them, so classify by
// recognisable substrings — good enough for status colouring.
const BAD = /REJECTED$|NOT_FAITHFUL$|^INVALID$|_INVALID$|^ABORTED$/;
const OK = /(?<!NOT_)FAITHFUL$|^SUCCESS$|^FETCHED$|FULL_REFUND$|CHALLENGER_REWARD$|RESOLVED_FLIPPED$/;
const WARN = /ADJUDICATING$|CHALLENGE_OPEN$|CHALLENGE_WINDOW$|VERDICT_PROPOSED$|^OPEN$|UNUSABLE_SHORT$|PARTIAL_SLASH$/;
const INFO = /EVIDENCE_OPEN$|EVIDENCE_CLOSED$|EVIDENCE_FROZEN$|CASE_FROZEN$|^UNSETTLED$/;

export function toneFor(value: string): Tone {
  if (BAD.test(value)) return "bad";
  if (OK.test(value)) return "ok";
  if (WARN.test(value)) return "warn";
  if (INFO.test(value)) return "info";
  return "neutral";
}

export function StatusBadge({ value }: { value: string }) {
  const tone = toneFor(value);
  const help = STATUS_HELP[value];
  return (
    <span className={`badge ${tone}`} title={help ?? value}>
      <span className="pill-dot" />
      {value}
    </span>
  );
}

export function Badge({
  children,
  tone = "neutral",
  title,
}: {
  children: ReactNode;
  tone?: Tone;
  title?: string;
}) {
  return (
    <span className={`badge ${tone}`} title={title}>
      {children}
    </span>
  );
}

export function Card({
  children,
  title,
  actions,
}: {
  children: ReactNode;
  title?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="card">
      {(title || actions) && (
        <div
          className="row"
          style={{ justifyContent: "space-between", marginBottom: 12 }}
        >
          {title ? <h3 style={{ margin: 0 }}>{title}</h3> : <span />}
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}

export function KV({ children }: { children: ReactNode }) {
  return <dl className="kv">{children}</dl>;
}

export function Row({ k, children }: { k: string; children: ReactNode }) {
  return (
    <>
      <dt>{k}</dt>
      <dd>{children}</dd>
    </>
  );
}

export function AddrChip({ addr }: { addr?: string | null }) {
  if (!addr) return <span className="faint">—</span>;
  return (
    <a
      className="mono"
      href={explorerAddressUrl(addr)}
      target="_blank"
      rel="noreferrer"
      title={addr}
    >
      {shortAddr(addr)}
    </a>
  );
}

export function HexChip({ hex, label }: { hex?: string | null; label?: string }) {
  if (isEmptyHex(hex)) return <span className="faint">— {label ? `(${label} not set)` : ""}</span>;
  return (
    <span className="mono" title={hex ?? ""}>
      {shortHex(hex)}
    </span>
  );
}

export function Notice({
  tone = "info",
  children,
}: {
  tone?: "ok" | "warn" | "bad" | "info";
  children: ReactNode;
}) {
  return <div className={`notice ${tone}`}>{children}</div>;
}

export function Spinner() {
  return <span className="spinner" aria-label="loading" />;
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="muted tiny" style={{ padding: "8px 2px" }}>
      {children}
    </div>
  );
}
