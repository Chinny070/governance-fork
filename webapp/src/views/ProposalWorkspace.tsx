import { useCallback, useEffect, useState } from "react";
import * as api from "../lib/api";
import { getActiveWriteClient as g } from "../lib/activeClient";
import {
  CASE_STATE,
  CHALLENGE_GROUNDS_FORK,
  CHALLENGE_GROUNDS_ROOT_ENVELOPE,
  ENVELOPE_STATUS,
  FORK_STATUS,
  RETRIEVAL_STATUS,
} from "../lib/enums";
import { formatGen, isEmptyHex } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { useTx } from "../lib/useTx";
import { buildRootTree } from "../lib/tree";
import {
  loadTarget,
  type TargetKindName,
  type TargetView,
} from "../lib/targetView";
import type { IntentEnvelope } from "../lib/types";
import {
  AddrChip,
  DL,
  Empty,
  HexChip,
  Note,
  Row,
  SectionHead,
  Spinner,
  StatusTag,
  Tag,
} from "../components/ui";
import { Guarded } from "../components/Guarded";
import { TxProgress } from "../components/TxProgress";
import { LineageTree } from "../components/LineageTree";
import { ForkCreatorPanel } from "./ForkCreator";

type Act = (fn: () => Promise<unknown>) => void;

export function ProposalWorkspace({
  kind,
  id,
}: {
  kind: TargetKindName;
  id: bigint;
}) {
  const [nonce, setNonce] = useState(0);
  const tv = useAsync(() => loadTarget(kind, id), [kind, id, nonce]);
  const tx = useTx();

  const refresh = useCallback(async () => setNonce((n) => n + 1), []);
  const act: Act = useCallback(
    (fn) =>
      void tx.run(
        async () => {
          const r = await fn();
          return (r && typeof r === "object" && "write" in r
            ? (r as { write: api.WriteResult }).write
            : (r as api.WriteResult));
        },
        { afterConfirm: refresh },
      ),
    [tx, refresh],
  );

  if (tv.loading && !tv.data)
    return (
      <div className="row muted">
        <Spinner /> Reading {kind} #{id.toString()}…
      </div>
    );
  if (tv.error) return <div className="note red">{tv.error}</div>;
  if (!tv.data)
    return (
      <div className="stack">
        <Empty>
          {kind} #{id.toString()} not found on the production contract.
        </Empty>
        <button className="small" onClick={() => navigate({ name: "explore" })}>
          ← Registry
        </button>
      </div>
    );

  const t = tv.data;

  return (
    <div className="stack-lg">
      <div className="between">
        <button className="link" onClick={() => navigate({ name: "explore" })}>
          ← Registry
        </button>
        <button className="small" onClick={refresh} disabled={tv.loading}>
          {tv.loading ? "Refreshing…" : "Refresh state"}
        </button>
      </div>

      <CaseHeader t={t} />

      <TxProgress tx={tx} />

      <OriginalIntent t={t} />

      {t.kind === "fork" && <WhatChanged t={t} />}

      <EvidenceSection t={t} act={act} busy={tx.busy} />

      <AdjudicationSection t={t} act={act} busy={tx.busy} />

      <ChallengeSection t={t} act={act} busy={tx.busy} />

      <FinalitySection t={t} act={act} busy={tx.busy} />

      {t.isFaithfulFinal && (
        <div className="section">
          <SectionHead eyebrow="Fork" title="Build an alternative" />
          <ForkCreatorPanel
            parentKind={t.kind}
            parentId={t.id}
            parentFingerprintHex={
              t.kind === "root"
                ? (t.root!.import_fingerprint as string)
                : (t.fork!.body_fingerprint as string)
            }
            onCreated={(fid) => navigate({ name: "fork", id: fid })}
          />
        </div>
      )}

      <LineageSection rootId={t.rootId} id={t.id} kind={t.kind} reloadKey={nonce} />
    </div>
  );
}

/* ------------------------------------------------------------------ header */

function CaseHeader({ t }: { t: TargetView }) {
  const verdict = t.verdict?.verdict;
  return (
    <header>
      <p className="eyebrow">
        {t.kind === "root" ? "Root proposal" : `Fork · depth ${t.fork!.depth}`}{" "}
        {t.id.toString()} · DAO {t.daoId.toString()}
        {t.kind === "fork" && (
          <>
            {" · "}
            <button
              className="link"
              onClick={() => navigate({ name: "root", id: t.rootId })}
            >
              root {t.rootId.toString()}
            </button>
          </>
        )}
      </p>
      <h1 className="display" style={{ fontSize: "clamp(24px,3.4vw,34px)", margin: "6px 0 14px" }}>
        {t.title}
      </h1>
      <div className="row" style={{ gap: 10 }}>
        <StatusTag value={t.status} />
        {verdict && <StatusTag value={verdict} />}
        {t.bonds.length > 0 && (
          <Tag tone="neutral" dot={false}>
            {t.bonds.filter((b) => !b.bond.settled).length
              ? `${t.bonds.filter((b) => !b.bond.settled).length} bond locked`
              : "bonds settled"}
          </Tag>
        )}
        {t.openChallenge && (
          <Tag tone="coral" dot>
            challenge #{t.openChallenge.id.toString()} open
          </Tag>
        )}
      </div>
    </header>
  );
}

/* ---------------------------------------------------------- original intent */

function IntentBody({ e }: { e: IntentEnvelope }) {
  return (
    <DL>
      <Row k="Objective">{e.objective}</Row>
      <Row k="Beneficiary">{e.beneficiary_class}</Row>
      <Row k="Resource type">{e.resource_type}</Row>
      <Row k="Scope">{e.scope}</Row>
      <Row k="Essential constraints">
        <ChipList items={e.essential_constraints} />
      </Row>
      <Row k="Mutable dimensions">
        <ChipList items={e.mutable_dimensions} tone="coral" />
      </Row>
      <Row k="Immutable dimensions">
        <ChipList items={e.immutable_dimensions} />
      </Row>
    </DL>
  );
}

function OriginalIntent({ t }: { t: TargetView }) {
  if (t.kind === "root") {
    const submitted = t.status !== "ENVELOPE_NOT_SUBMITTED";
    return (
      <div className="section">
        <SectionHead eyebrow="Original intent" title="Intent envelope" />
        {!submitted ? (
          <Empty>
            No envelope submitted. The proposer submits it (with a{" "}
            {formatGen(api.BOND_AMOUNT_WEI)} bond) from the Build tab.
          </Empty>
        ) : (
          <IntentBody e={t.root!.envelope} />
        )}
        {t.root!.structured_parameters.length > 0 && (
          <>
            <hr className="rule" style={{ margin: "16px 0" }} />
            <p className="eyebrow" style={{ marginBottom: 8 }}>
              Imported parameters
            </p>
            <DL>
              {t.root!.structured_parameters.map((p, i) => (
                <Row k={p.key} key={i}>
                  {p.value}
                </Row>
              ))}
            </DL>
          </>
        )}
        <hr className="rule" style={{ margin: "16px 0" }} />
        <DL>
          <Row k="Proposal URL">
            <a href={t.root!.proposal_url} target="_blank" rel="noreferrer">
              {t.root!.proposal_url}
            </a>
          </Row>
          <Row k="External id">{t.root!.external_proposal_id}</Row>
          <Row k="Proposer">
            <AddrChip addr={t.root!.proposer} />
          </Row>
          <Row k="Import fingerprint">
            <HexChip hex={t.root!.import_fingerprint} label="import" />
          </Row>
          <Row k="Web content fingerprint">
            <HexChip hex={t.root!.web_content_fingerprint} label="web render" />
          </Row>
        </DL>
      </div>
    );
  }

  // fork — show the root's intent it must preserve
  const rp = t.rootProposal;
  return (
    <div className="section">
      <SectionHead
        eyebrow="Original intent"
        title={`Inherited from root ${t.rootId.toString()}`}
        right={
          <button
            className="link"
            onClick={() => navigate({ name: "root", id: t.rootId })}
          >
            open root →
          </button>
        }
      />
      {rp && rp.envelope.objective ? (
        <IntentBody e={rp.envelope} />
      ) : (
        <Empty>Root intent unavailable.</Empty>
      )}
      <hr className="rule" style={{ margin: "16px 0" }} />
      <p className="eyebrow" style={{ marginBottom: 8 }}>
        This fork's rationale
      </p>
      <DL>
        <Row k="Summary">{t.fork!.body.summary}</Row>
        <Row k="Reasoning">{t.fork!.body.reasoning}</Row>
      </DL>
    </div>
  );
}

/* --------------------------------------------------------------- what changed */

function WhatChanged({ t }: { t: TargetView }) {
  const f = t.fork!;
  return (
    <div className="section">
      <SectionHead
        eyebrow="What changed"
        title={`${f.delta.length} declared change${f.delta.length === 1 ? "" : "s"}`}
      />
      {f.delta.length === 0 ? (
        <Empty>No delta declared.</Empty>
      ) : (
        <div>
          <div className="delta" style={{ borderBottom: "1px solid var(--line-2)" }}>
            <span className="eyebrow">Before</span>
            <span />
            <span className="eyebrow" style={{ color: "var(--coral-ink)" }}>
              This fork
            </span>
          </div>
          {f.delta.map((d, i) => (
            <div className="delta" key={i}>
              <span className="dim">
                {d.dimension_name} · {d.claim_kind}
              </span>
              <span className="was">{d.parent_value || "∅"}</span>
              <span className="arrow">→</span>
              <span className="now">{d.fork_value || "∅"}</span>
            </div>
          ))}
        </div>
      )}
      {f.body.structured_parameters.length > 0 && (
        <>
          <hr className="rule" style={{ margin: "16px 0" }} />
          <p className="eyebrow" style={{ marginBottom: 8 }}>
            Fork parameters
          </p>
          <DL>
            {f.body.structured_parameters.map((p, i) => (
              <Row k={p.key} key={i}>
                {p.value}
              </Row>
            ))}
          </DL>
        </>
      )}
    </div>
  );
}

function ChipList({ items, tone }: { items: string[]; tone?: "coral" }) {
  if (!items.length) return <span className="faint">none</span>;
  return (
    <div className="chips">
      {items.map((it, i) => (
        <Tag key={i} tone={tone ?? "neutral"} dot={false}>
          {it}
        </Tag>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ evidence */

function EvidenceSection({
  t,
  act,
  busy,
}: {
  t: TargetView;
  act: Act;
  busy: boolean;
}) {
  const caseId = t.evidenceCaseId;
  const c = t.case;
  const canClose = c?.state === CASE_STATE.OPEN;
  const canSeal = c?.state === CASE_STATE.EVIDENCE_CLOSED;

  return (
    <div className="section">
      <SectionHead
        eyebrow="Evidence"
        title={
          caseId > 0n ? (
            <span className="row" style={{ gap: 8 }}>
              Case {caseId.toString()}
              {c && <StatusTag value={c.state} tone={c.state === "OPEN" ? "blue" : undefined} />}
            </span>
          ) : (
            "No case yet"
          )
        }
      />

      {caseId === 0n ? (
        <Empty>
          {t.kind === "root"
            ? "Created when the intent envelope is submitted."
            : "Submit fork evidence from the Build flow to open the case."}
        </Empty>
      ) : (
        <>
          {t.evidence.length === 0 ? (
            <Empty>No evidence submitted.</Empty>
          ) : (
            <div className="records">
              {t.evidence.map(({ id, ev }, i) => (
                <div className="record" key={id.toString()}>
                  <span className="idx">[{i + 1}]</span>
                  <div className="body">
                    <div className="title">
                      <a href={ev.url} target="_blank" rel="noreferrer">
                        {ev.url}
                      </a>
                    </div>
                    <div className="sub">
                      {ev.evidence_class} · {ev.render_profile} ·{" "}
                      {ev.authority_claim || "—"} · {ev.temporal_marker || "—"} ·
                      submitter <AddrChip addr={ev.submitter} />
                    </div>
                    {ev.relevance_claim && (
                      <div className="tiny muted" style={{ marginTop: 4 }}>
                        “{ev.relevance_claim}”
                      </div>
                    )}
                    {ev.frozen && !isEmptyHex(ev.content_fingerprint) && (
                      <div className="sub" style={{ marginTop: 4 }}>
                        content <HexChip hex={ev.content_fingerprint} />
                        {ev.frozen_content
                          ? ` · ${ev.frozen_content.length} chars frozen`
                          : ""}
                      </div>
                    )}
                  </div>
                  <div className="aside">
                    <StatusTag value={ev.retrieval_status} dot={false} />
                    {c?.state === CASE_STATE.EVIDENCE_CLOSED &&
                      ev.retrieval_status === RETRIEVAL_STATUS.NOT_FETCHED && (
                        <Guarded>
                          <button
                            className="small"
                            disabled={busy}
                            onClick={() => act(() => api.fetchEvidence(g(), id))}
                          >
                            Fetch
                          </button>
                        </Guarded>
                      )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {c && (
            <div className="dl" style={{ marginTop: 16 }}>
              <dt>Case fingerprint</dt>
              <dd>
                <HexChip hex={c.case_fingerprint} label="case" />
              </dd>
              <dt>Evidence set</dt>
              <dd>
                <HexChip hex={c.evidence_set_fingerprint} label="evidence set" />
              </dd>
              <dt>Retries</dt>
              <dd>{c.retry_count}</dd>
            </div>
          )}

          <Guarded>
            <div className="row" style={{ marginTop: 16 }}>
              <button
                className="primary small"
                disabled={busy || !canClose}
                onClick={() => act(() => api.closeEvidence(g(), caseId))}
              >
                1 · Close evidence
              </button>
              <span className="tiny faint">→ 2 · Fetch each item above →</span>
              <button
                className="primary small"
                disabled={busy || !canSeal}
                onClick={() => act(() => api.sealEvidence(g(), caseId))}
              >
                3 · Seal evidence
              </button>
              {c &&
                (c.state === CASE_STATE.OPEN ||
                  c.state === CASE_STATE.EVIDENCE_CLOSED) && (
                  <button
                    className="danger small"
                    disabled={busy}
                    onClick={() => act(() => api.abortCase(g(), caseId))}
                  >
                    Abort case
                  </button>
                )}
            </div>
          </Guarded>
        </>
      )}
    </div>
  );
}

/* -------------------------------------------------------------- adjudication */

function AdjudicationSection({
  t,
  act,
  busy,
}: {
  t: TargetView;
  act: Act;
  busy: boolean;
}) {
  const caseId = t.evidenceCaseId;
  const c = t.case;
  const canArm = c?.state === CASE_STATE.CASE_FROZEN;
  const canRun = c?.state === CASE_STATE.ADJUDICATING;
  const terminal = c?.state === CASE_STATE.UNDETERMINED_TERMINAL;
  const v = t.verdict;

  return (
    <div className="section">
      <SectionHead
        eyebrow="Adjudication"
        title={v ? `Verdict ${v.verdict_id.toString()}` : "Evaluation"}
        right={v ? <StatusTag value={v.verdict} /> : undefined}
      />

      <p className="muted tiny" style={{ marginTop: 0 }}>
        <code>adjudicate</code> arms the case; <code>run_adjudication</code> is
        the single nondeterministic step — validators reach semantic consensus
        with <code>eq_principle.prompt_comparative</code>. An Undetermined run
        commits nothing.
      </p>

      {terminal && (
        <Note tone="coral">
          Retry budget spent — the case is in the deterministic{" "}
          <strong>UNDETERMINED_TERMINAL</strong> state. The target finalizes as
          UNCLEAR and the proposer/creator bond is fully refundable.
        </Note>
      )}

      {v ? (
        <>
          <div className="dl" style={{ margin: "12px 0" }}>
            <dt>Dimensions v.</dt>
            <dd>{v.adjudication_dimensions_version}</dd>
            <dt>Prompt fp.</dt>
            <dd>
              <HexChip hex={v.prompt_fingerprint} label="prompt" />
            </dd>
            <dt>Reasoning hash</dt>
            <dd>
              <HexChip hex={v.reasoning_hash} label="reasoning" />
            </dd>
            <dt>Reason codes</dt>
            <dd>
              <ChipList items={v.reason_codes} />
            </dd>
          </div>

          <div className="records">
            {v.dimensions.map((d, i) => (
              <div className="record" key={i}>
                <span className="idx">{String(i + 1).padStart(2, "0")}</span>
                <div className="body">
                  <div className="title">{d.name}</div>
                  <div className="tiny muted" style={{ marginTop: 3 }}>
                    {d.reasoning}
                  </div>
                  {d.evidence_ids.length > 0 && (
                    <div className="sub" style={{ marginTop: 3 }}>
                      cites {d.evidence_ids.map((e) => `[${e}]`).join(" ")}
                    </div>
                  )}
                </div>
                <div className="aside">
                  <StatusTag
                    value={d.finding}
                    tone={
                      d.finding === "SATISFIED"
                        ? "green"
                        : d.finding === "NOT_SATISFIED"
                          ? "red"
                          : "neutral"
                    }
                    dot={false}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <Empty>No verdict yet.</Empty>
      )}

      {caseId > 0n && (
        <Guarded>
          <div className="row" style={{ marginTop: 16 }}>
            <button
              className="primary small"
              disabled={busy || !canArm}
              onClick={() => act(() => api.adjudicate(g(), caseId))}
            >
              Arm · adjudicate
            </button>
            <button
              className="primary small"
              disabled={busy || !canRun}
              onClick={() => act(() => api.runAdjudication(g(), caseId))}
            >
              Run adjudication
            </button>
            {canRun && (
              <button
                className="small"
                disabled={busy}
                onClick={() => act(() => api.adjudicate(g(), caseId))}
              >
                Re-arm (retry {c ? c.retry_count : 0}/3)
              </button>
            )}
          </div>
        </Guarded>
      )}

      {t.verdictHistory.length > 1 && (
        <div className="tiny faint mono" style={{ marginTop: 12 }}>
          verdict history:{" "}
          {t.verdictHistory
            .map((vid) =>
              vid === t.currentVerdictId ? `[${vid}]` : `${vid}`,
            )
            .join(" → ")}{" "}
          (governing in brackets)
        </div>
      )}
    </div>
  );
}

/* --------------------------------------------------------------- challenges */

function ChallengeSection({
  t,
  act,
  busy,
}: {
  t: TargetView;
  act: Act;
  busy: boolean;
}) {
  const grounds =
    t.kind === "root"
      ? CHALLENGE_GROUNDS_ROOT_ENVELOPE
      : CHALLENGE_GROUNDS_FORK;
  const [ground, setGround] = useState<string>(grounds[0]);
  const [argument, setArgument] = useState("");

  const decisive =
    !!t.verdict &&
    t.case?.state === CASE_STATE.SUCCESS &&
    t.verdict.verdict !== "INVALID";
  const canOpen =
    decisive && !t.isFinal && !t.openChallenge && t.challenges.length < 3;

  const open = async () => {
    const c = g();
    const { bondId } = await api.lockBond(c, api.BOND_PURPOSE.CHALLENGE);
    return api.challengeVerdict(
      c,
      bondId,
      t.id,
      t.targetKindConst,
      ground,
      argument.trim(),
    );
  };

  return (
    <div className="section">
      <SectionHead
        eyebrow="Challenges"
        title={`${t.challenges.length} / 3`}
      />

      <p className="muted tiny" style={{ marginTop: 0 }}>
        A challenge doesn't reject the proposal — it asserts a specific
        adjudication dimension is wrong and triggers a re-adjudication. Flip →
        bond refunded + {formatGen(api.CHALLENGER_FLIP_REWARD_WEI)} reward;
        unchanged → half the bond slashed.
      </p>

      {t.challenges.length === 0 && <Empty>None opened.</Empty>}

      {t.challenges.map(({ id, challenge, case: cc }) => (
        <div className="panel-inset" key={id.toString()} style={{ marginBottom: 10 }}>
          <div className="between" style={{ alignItems: "center" }}>
            <strong className="mono tiny">CHALLENGE {id.toString()}</strong>
            <StatusTag value={challenge.status} />
          </div>
          <div className="dl" style={{ marginTop: 10 }}>
            <dt>Challenger</dt>
            <dd>
              <AddrChip addr={challenge.challenger} />
            </dd>
            <dt>Ground</dt>
            <dd className="mono tiny">{challenge.ground_code}</dd>
            <dt>Argument</dt>
            <dd>{challenge.argument}</dd>
            <dt>Verdicts</dt>
            <dd className="mono tiny">
              {challenge.original_verdict_id.toString()}
              {BigInt(challenge.replacement_verdict_id) > 0n
                ? ` → ${challenge.replacement_verdict_id}`
                : ""}
            </dd>
            <dt>Challenge case</dt>
            <dd className="mono tiny">
              {challenge.case_id.toString()}
              {cc && ` · ${cc.state}`}
            </dd>
          </div>
          {cc &&
            (challenge.status === "OPEN" ||
              challenge.status === "ADJUDICATING") && (
              <Guarded>
                <div className="row" style={{ marginTop: 10 }}>
                  <button
                    className="primary small"
                    disabled={busy || cc.state !== CASE_STATE.CASE_FROZEN}
                    onClick={() =>
                      act(() =>
                        api.adjudicate(g(), BigInt(challenge.case_id)),
                      )
                    }
                  >
                    Arm challenge
                  </button>
                  <button
                    className="primary small"
                    disabled={busy || cc.state !== CASE_STATE.ADJUDICATING}
                    onClick={() =>
                      act(() =>
                        api.runAdjudication(g(), BigInt(challenge.case_id)),
                      )
                    }
                  >
                    Run re-adjudication
                  </button>
                </div>
              </Guarded>
            )}
        </div>
      ))}

      {canOpen && (
        <div className="panel-inset" style={{ marginTop: 4 }}>
          <p className="eyebrow" style={{ marginBottom: 10 }}>
            Open a challenge · {formatGen(api.BOND_AMOUNT_WEI)} bond
          </p>
          <div className="field">
            <label>Ground</label>
            <select value={ground} onChange={(e) => setGround(e.target.value)}>
              {grounds.map((gnd) => (
                <option key={gnd} value={gnd}>
                  {gnd}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Argument (≤ 512 chars)</label>
            <textarea
              value={argument}
              maxLength={512}
              onChange={(e) => setArgument(e.target.value)}
              placeholder="Which dimension finding is wrong, and why the evidence supports a different finding."
            />
          </div>
          <Guarded>
            <button
              className="coral"
              disabled={busy || argument.trim().length < 1}
              onClick={() => act(open)}
            >
              Lock bond & open challenge
            </button>
          </Guarded>
        </div>
      )}
    </div>
  );
}

/* --------------------------------------------------------- finality & bonds */

function formatDuration(totalSeconds: bigint): string {
  const s = totalSeconds < 0n ? 0n : totalSeconds;
  const hours = s / 3600n;
  const minutes = (s % 3600n) / 60n;
  if (hours >= 24n) {
    const days = hours / 24n;
    const remHours = hours % 24n;
    return remHours > 0n ? `${days}d ${remHours}h` : `${days}d`;
  }
  if (hours > 0n) {
    return minutes > 0n ? `${hours}h ${minutes}m` : `${hours}h`;
  }
  return minutes > 0n ? `${minutes}m` : `${s}s`;
}

function FinalitySection({
  t,
  act,
  busy,
}: {
  t: TargetView;
  act: Act;
  busy: boolean;
}) {
  const hasVerdict = t.currentVerdictId > 0n;
  const pending =
    t.status === ENVELOPE_STATUS.CHALLENGE_WINDOW ||
    t.status === FORK_STATUS.CHALLENGE_WINDOW;
  const canOpenWindow = hasVerdict && !t.isFinal && !pending && !t.openChallenge;

  const consts = useAsync(api.getConstants, []);
  const windowSeconds = BigInt(consts.data?.challenge_window_seconds ?? 259200);
  const [nowSec, setNowSec] = useState(() => BigInt(Math.floor(Date.now() / 1000)));
  useEffect(() => {
    if (!pending) return;
    const id = setInterval(() => setNowSec(BigInt(Math.floor(Date.now() / 1000))), 15000);
    return () => clearInterval(id);
  }, [pending]);
  const elapsed = pending ? nowSec - t.finalityWindowOpenedAt : 0n;
  const remaining = windowSeconds - elapsed;
  const windowElapsed = remaining <= 0n;
  const canFinalize = pending && !t.openChallenge && windowElapsed;

  return (
    <div className="section">
      <SectionHead
        eyebrow="Finality & bonds"
        title={t.isFinal ? "Final" : pending ? "Finality window open" : "Open"}
      />

      {t.isFinal ? (
        <Note tone={t.isFaithfulFinal ? "green" : "neutral"}>
          This {t.kind} is final ({t.status}).
          {t.isFaithfulFinal
            ? " It is now forkable — build an alternative below."
            : " It is not forkable."}
        </Note>
      ) : pending ? (
        <>
          <Note tone={windowElapsed ? "coral" : "neutral"}>
            {windowElapsed ? (
              <>
                The {formatDuration(windowSeconds)} challenge window has
                elapsed and finalize is ready to run. Anyone may execute it.
              </>
            ) : (
              <>
                Challenge window open — {formatDuration(remaining)} remaining
                before finalize can run. A challenge submitted now will still
                be honored and will block finalize until it's resolved.
              </>
            )}
          </Note>
          <Guarded>
            <button
              className="primary"
              style={{ marginTop: 10 }}
              disabled={busy || !canFinalize}
              onClick={() => act(() => api.finalize(g(), t.id, t.targetKindConst))}
              title={
                t.openChallenge
                  ? "Resolve the open challenge first"
                  : windowElapsed
                    ? "Anyone may execute finalize now"
                    : `Wait ${formatDuration(remaining)} for the challenge window to elapse`
              }
            >
              Finalize {t.kind}
            </button>
          </Guarded>
        </>
      ) : (
        <>
          <p className="muted tiny" style={{ marginTop: 0 }}>
            Finalizing is two transactions. Opening the window starts a real,
            enforced {formatDuration(windowSeconds)} challenge window — timed
            by the transaction's own on-chain timestamp, not a block count —
            during which finalize cannot run. A challenge submitted at any
            point in that window is guaranteed to be seen and will block
            finalize until it's resolved.
          </p>
          <Guarded>
            <button
              className="primary"
              disabled={busy || !canOpenWindow}
              onClick={() =>
                act(() => api.openFinalityWindow(g(), t.id, t.targetKindConst))
              }
              title={
                !hasVerdict
                  ? "No verdict yet"
                  : t.openChallenge
                    ? "Resolve the open challenge first"
                    : "Open the finality window"
              }
            >
              1 · Open finality window
            </button>
            <button className="small" disabled style={{ marginLeft: 8 }}>
              2 · Finalize (after {formatDuration(windowSeconds)})
            </button>
          </Guarded>
        </>
      )}

      {t.bonds.length > 0 && (
        <div className="ledger-scroll" style={{ marginTop: 16 }}>
          <table className="ledger">
            <thead>
              <tr>
                <th>Bond</th>
                <th>Purpose</th>
                <th>Amount</th>
                <th>Refund</th>
                <th>Slash</th>
                <th>Reward</th>
                <th>Settlement</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {t.bonds.map(({ id, bond }) => {
                const settleable = !bond.settled && t.isFinal;
                return (
                  <tr key={id.toString()}>
                    <td className="num">#{id.toString()}</td>
                    <td className="mono tiny">{bond.purpose}</td>
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
                      {settleable && (
                        <Guarded>
                          <button
                            className="small primary"
                            disabled={busy}
                            onClick={() =>
                              act(() => api.settleBond(g(), id))
                            }
                          >
                            Settle
                          </button>
                        </Guarded>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {!t.isFinal && t.bonds.some((b) => !b.bond.settled) && (
        <p className="tiny faint" style={{ marginTop: 8 }}>
          Bonds settle after the {t.kind} is finalized. A CHALLENGE bond settles
          only after the proposer/creator bond.
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ lineage */

function LineageSection({
  rootId,
  id,
  kind,
  reloadKey,
}: {
  rootId: bigint;
  id: bigint;
  kind: TargetKindName;
  reloadKey: number;
}) {
  const tree = useAsync(() => buildRootTree(rootId), [rootId.toString(), reloadKey]);
  return (
    <div className="section">
      <SectionHead
        eyebrow="Lineage"
        title="Proposal tree"
        right={
          <button className="small" onClick={tree.refresh} disabled={tree.loading}>
            {tree.loading ? "…" : "Refresh"}
          </button>
        }
      />
      {tree.loading && !tree.data && (
        <div className="row muted">
          <Spinner /> Walking lineage…
        </div>
      )}
      {tree.error && (
        <div className="note red">
          {tree.error}{" "}
          <button className="link" onClick={tree.refresh}>
            retry
          </button>
        </div>
      )}
      {tree.data && (
        <LineageTree root={tree.data} currentId={id} currentKind={kind} />
      )}
    </div>
  );
}
