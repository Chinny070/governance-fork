import type { ReactNode } from "react";
import { STATUS_HELP } from "../lib/enums";
import { explorerAddressUrl } from "../lib/contract";
import { shortAddr, shortHex, isEmptyHex } from "../lib/format";

export type Tone = "green" | "red" | "coral" | "blue" | "neutral";

// Semantic colour, per the design system:
//   green  — successful / finalized-good only
//   red    — rejected / danger only
//   coral  — forks, challenges, divergence, penalties
//   blue   — active / in-progress
//   neutral — everything else (draft, unclear, not-yet)
const RED =
  /REJECTED$|NOT_FAITHFUL$|^INVALID$|_INVALID$|^ABORTED$|RESOLVED_INVALID$/;
const GREEN =
  /(?<!NOT_)FAITHFUL$|^SUCCESS$|^FETCHED$|FULL_REFUND$|CHALLENGER_REWARD$|RESOLVED_FLIPPED$/;
const CORAL =
  /CHALLENGE_OPEN$|CHALLENGE_WINDOW$|^OPEN$|PARTIAL_SLASH$|UNUSABLE_SHORT$|^FORK$/;
const BLUE =
  /ADJUDICATING$|VERDICT_PROPOSED$|EVIDENCE_OPEN$|EVIDENCE_CLOSED$|EVIDENCE_FROZEN$|CASE_FROZEN$|^UNSETTLED$|^ROOT_ENVELOPE$/;

export function toneFor(value: string): Tone {
  if (RED.test(value)) return "red";
  if (GREEN.test(value)) return "green";
  if (CORAL.test(value)) return "coral";
  if (BLUE.test(value)) return "blue";
  return "neutral";
}

export function Tag({
  children,
  tone = "neutral",
  dot,
  title,
}: {
  children: ReactNode;
  tone?: Tone;
  dot?: boolean;
  title?: string;
}) {
  return (
    <span className={`tag ${tone === "neutral" ? "" : tone}`} title={title}>
      {dot && <span className="dot" />}
      {children}
    </span>
  );
}

export function StatusTag({
  value,
  tone,
  dot = true,
}: {
  value: string;
  tone?: Tone;
  dot?: boolean;
}) {
  return (
    <Tag tone={tone ?? toneFor(value)} dot={dot} title={STATUS_HELP[value] ?? value}>
      {value}
    </Tag>
  );
}

export function SectionHead({
  eyebrow,
  title,
  right,
}: {
  eyebrow: string;
  title?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="section-head">
      <span className="eyebrow">{eyebrow}</span>
      {title && <h3>{title}</h3>}
      <span className="spacer" />
      {right}
    </div>
  );
}

export function DL({ children }: { children: ReactNode }) {
  return <dl className="dl">{children}</dl>;
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
  if (isEmptyHex(hex))
    return (
      <span className="faint tiny">
        — {label ? `${label} not set` : ""}
      </span>
    );
  return (
    <span className="mono" title={hex ?? ""}>
      {shortHex(hex)}
    </span>
  );
}

export function Note({
  tone = "neutral",
  children,
}: {
  tone?: "blue" | "coral" | "green" | "red" | "neutral";
  children: ReactNode;
}) {
  return <div className={`note ${tone === "neutral" ? "" : tone}`}>{children}</div>;
}

export function Spinner() {
  return <span className="spinner" aria-label="loading" />;
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="muted tiny" style={{ padding: "10px 0" }}>
      {children}
    </div>
  );
}
