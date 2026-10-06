// Stage 11 UI: verify-a-verdict, fork diff, adoption signalling, reputation.
import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { getActiveWriteClient as g } from "../lib/activeClient";
import { FORK_STATUS } from "../lib/enums";
import { isEmptyHex } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { Evidence, ParamKV } from "../lib/types";
import type { TargetView } from "../lib/targetView";
import { Guarded } from "../components/Guarded";
import { navigate } from "../lib/router";
import {
  AddrChip,
  Empty,
  Note,
  SectionHead,
  Spinner,
  StatusTag,
  Tag,
} from "../components/ui";

type Act = (fn: () => Promise<unknown>) => void;

/* ------------------------------------------------------------- verify hash */

async function sha256Hex(text: string): Promise<string> {
  const buf = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return (
    "0x" +
    Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("")
  );
}

/** Recomputes SHA-256 of the frozen evidence in the browser and compares it
 *  with the fingerprint stored on-chain. */
export function VerifyEvidence({ ev }: { ev: Evidence }) {
  const [state, setState] = useState<"idle" | "ok" | "bad">("idle");
  const [computed, setComputed] = useState("");
  if (!ev.frozen || isEmptyHex(ev.content_fingerprint)) return null;
  const run = async () => {
    const h = await sha256Hex(ev.frozen_content);
    setComputed(h);
    setState(h.toLowerCase() === String(ev.content_fingerprint).toLowerCase() ? "ok" : "bad");
  };
  return (
    <div className="sub" style={{ marginTop: 4 }}>
      <button className="small" onClick={run}>
        Verify hash
      </button>{" "}
      {state === "ok" && (
        <Tag tone="green" dot>
          matches on-chain fingerprint — evidence unchanged since sealing
        </Tag>
      )}
      {state === "bad" && (
        <Tag tone="red" dot title={computed}>
          MISMATCH — frozen text does not hash to the on-chain fingerprint
        </Tag>
      )}
    </div>
  );
}

/* --------------------------------------------------------------- reputation */

export function ReputationChip({ creator }: { creator?: string | null }) {
  const rep = useAsync(
    () => (creator ? api.getReputation(creator) : Promise.resolve(undefined)),
    [creator],
  );
  const r = rep.data;
  if (!creator || !r) return null;
  const total = Number(r.forks_faithful) + Number(r.forks_not_faithful);
  if (total === 0 && Number(r.forks_adopted) === 0) {
    return <span className="tiny faint">no finalized forks yet</span>;
  }
  return (
    <span className="tiny muted" title="Finalized-fork track record of this creator">
      {r.forks_faithful} faithful · {r.forks_not_faithful} not faithful ·{" "}
      {r.forks_adopted} adopted
    </span>
  );
}

/* ---------------------------------------------------------------- fork diff */

const DIFF_DIMS = [
  "INTENT_PRESERVATION",
  "DELTA_ACCURACY",
  "UNDECLARED_SEMANTIC_CHANGE",
];

function toMap(ps: ParamKV[]): Map<string, string> {
  const m = new Map<string, string>();
  for (const p of ps) m.set(p.key, p.value);
  return m;
}

export function ForkDiff({ t }: { t: TargetView }) {
  const f = t.fork!;
  const parentParams =
    f.parent_kind === "PARENT_FORK" && t.parentFork
      ? t.parentFork.body.structured_parameters
      : (t.rootProposal?.structured_parameters ?? []);
  const before = toMap(parentParams);
  const after = toMap(f.body.structured_parameters);
  const keys = Array.from(new Set([...before.keys(), ...after.keys()]));
  const rows = keys.map((k) => {
    const b = before.get(k);
    const a = after.get(k);
    const status =
      b === undefined ? "added" : a === undefined ? "removed" : a !== b ? "changed" : "same";
    return { k, b, a, status };
  });
  const changed = rows.filter((r) => r.status !== "same");
  const reasoning = (t.verdict?.dimensions ?? []).filter((d) =>
    DIFF_DIMS.includes(d.name),
  );
  const tone = (s: string) =>
    s === "added" ? "green" : s === "removed" ? "red" : s === "changed" ? "coral" : "neutral";

  return (
    <div className="section">
      <SectionHead
        eyebrow="Fork vs parent"
        title={`${changed.length} parameter${changed.length === 1 ? "" : "s"} differ from the ${
          f.parent_kind === "PARENT_FORK" ? "parent fork" : "root proposal"
        }`}
      />
      <div className="ledger-scroll">
        <table className="ledger">
          <thead>
            <tr>
              <th>Parameter</th>
              <th>Parent</th>
              <th>This fork</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.k} style={r.status === "same" ? { opacity: 0.55 } : undefined}>
                <td className="mono">{r.k}</td>
                <td>{r.b ?? "∅"}</td>
                <td>{r.a ?? "∅"}</td>
                <td>
                  <Tag tone={tone(r.status)} dot={false}>
                    {r.status}
                  </Tag>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {reasoning.length > 0 && (
        <>
          <hr className="rule" style={{ margin: "16px 0" }} />
          <p className="eyebrow" style={{ marginBottom: 8 }}>
            Why the adjudicator judged it this way
          </p>
          {reasoning.map((d) => (
            <div key={d.name} style={{ marginBottom: 10 }}>
              <div className="row" style={{ gap: 8 }}>
                <span className="mono tiny">{d.name}</span>
                <StatusTag value={d.finding} />
              </div>
              <div className="tiny muted" style={{ marginTop: 2 }}>
                {d.reasoning}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

/* ----------------------------------------------------------------- adoption */

function fmtTime(sec: bigint): string {
  return new Date(Number(sec) * 1000).toUTCString();
}

export function AdoptionSection({
  t,
  act,
  busy,
  reloadKey,
}: {
  t: TargetView;
  act: Act;
  busy: boolean;
  reloadKey: number;
}) {
  const rootId = t.id;
  const data = useAsync(async () => {
    const info = await api.getAdoption(rootId);
    const ids = await api.collectAll((c) => api.listForksOfRoot(rootId, c));
    const forks = [];
    for (const fid of ids) {
      const fork = await api.getFork(fid);
      if (!fork || fork.status !== FORK_STATUS.FINALIZED_FAITHFUL) continue;
      const count = await api.getForkSignalCount(fid);
      forks.push({ id: fid, fork, count: Number(count) });
    }
    return { info, forks };
  }, [rootId, reloadKey]);

  const [now, setNow] = useState(() => BigInt(Math.floor(Date.now() / 1000)));
  useEffect(() => {
    const i = setInterval(() => setNow(BigInt(Math.floor(Date.now() / 1000))), 15000);
    return () => clearInterval(i);
  }, []);

  if (!t.isFaithfulFinal) return null;

  const info = data.data?.info;
  const opened = !!info && BigInt(info.opened_at) > 0n;
  const closed = !!info?.closed;
  const windowOver = opened && info && now >= BigInt(info.closes_at);
  const forks = data.data?.forks ?? [];

  return (
    <div className="section">
      <SectionHead
        eyebrow="Adoption"
        title={
          closed
            ? BigInt(info!.adopted_fork_id) > 0n
              ? `Fork #${info!.adopted_fork_id} adopted`
              : "Closed — no winner"
            : opened
              ? "Signalling open"
              : "Not opened"
        }
      />
      <p className="muted tiny" style={{ marginTop: 0 }}>
        A FAITHFUL verdict says a fork stayed true to the intent — not that the
        DAO wants it. Anyone may signal one finalized-FAITHFUL fork; after the
        window the most-signalled fork is adopted. Signals are one-address-one-
        signal (not stake-weighted), so treat them as coordination, not a
        binding vote.
      </p>
      {data.loading && !data.data && (
        <div className="row muted">
          <Spinner /> Reading adoption state…
        </div>
      )}
      {opened && info && (
        <Note tone={closed ? "green" : "blue"}>
          Opened {fmtTime(BigInt(info.opened_at))} · closes{" "}
          {fmtTime(BigInt(info.closes_at))}
        </Note>
      )}
      {forks.length === 0 ? (
        <Empty>No finalized-FAITHFUL forks to signal for yet.</Empty>
      ) : (
        <div className="records" style={{ marginTop: 10 }}>
          {forks.map(({ id, fork, count }) => (
            <div className="record" key={id.toString()}>
              <span className="idx">#{id.toString()}</span>
              <div className="body">
                <div className="title">
                  <a onClick={() => navigate({ name: "fork", id })} style={{ cursor: "pointer" }}>
                    {fork.body.title}
                  </a>
                </div>
                <div className="sub">
                  by <AddrChip addr={fork.creator} /> ·{" "}
                  <ReputationChip creator={fork.creator} />
                </div>
              </div>
              <div className="aside">
                <Tag tone={BigInt(info?.adopted_fork_id ?? 0) === id ? "green" : "neutral"} dot={false}>
                  {count} signal{count === 1 ? "" : "s"}
                </Tag>
                {opened && !windowOver && !closed && (
                  <Guarded>
                    <button
                      className="small"
                      disabled={busy}
                      onClick={() => act(() => api.signalAdoption(g(), id))}
                    >
                      Signal
                    </button>
                  </Guarded>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      <Guarded>
        <div className="row" style={{ marginTop: 14 }}>
          {!opened && (
            <button
              className="primary small"
              disabled={busy}
              onClick={() => act(() => api.openAdoption(g(), rootId))}
              title="Only the root's proposer can open adoption"
            >
              Open adoption (proposer)
            </button>
          )}
          {opened && !closed && (
            <button
              className="primary small"
              disabled={busy || !windowOver}
              onClick={() => act(() => api.closeAdoption(g(), rootId))}
              title={windowOver ? "Anyone may close it now" : "Window still running"}
            >
              Close adoption
            </button>
          )}
        </div>
      </Guarded>
    </div>
  );
}
