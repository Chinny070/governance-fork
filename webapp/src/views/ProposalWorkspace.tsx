import { useCallback, useState } from "react";
import * as api from "../lib/api";
import { getActiveWriteClient as g } from "../lib/activeClient";
import {
  BOND_PURPOSE,
  CASE_STATE,
  CHALLENGE_GROUNDS_FORK,
  CHALLENGE_GROUNDS_ROOT_ENVELOPE,
  RETRIEVAL_STATUS,
} from "../lib/enums";
import { formatGen, isEmptyHex } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { useTx } from "../lib/useTx";
import { loadTarget, type TargetKindName, type TargetView } from "../lib/targetView";
import {
  AddrChip,
  Card,
  Empty,
  HexChip,
  KV,
  Notice,
  Row,
  Spinner,
  StatusBadge,
} from "../components/ui";
import { Guarded } from "../components/Guarded";
import { TxProgress } from "../components/TxProgress";
import { ProposalTree } from "./ProposalTree";
import { ForkCreatorPanel } from "./ForkCreator";

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

  const refresh = useCallback(async () => {
    setNonce((n) => n + 1);
  }, []);

  const act = useCallback(
    (fn: () => Promise<api.WriteResult | { write: api.WriteResult }>) =>
      tx.run(
        async () => {
          const r = await fn();
          return "write" in r ? r.write : r;
        },
        { afterConfirm: refresh },
      ),
    [tx, refresh],
  );

  if (tv.loading && !tv.data) {
    return (
      <div className="card row">
        <Spinner /> <span className="muted">Loading {kind} #{id.toString()}…</span>
      </div>
    );
  }
  if (tv.error) return <div className="notice bad">{tv.error}</div>;
  if (!tv.data)
    return (
      <div className="card">
        <Empty>
          {kind} #{id.toString()} not found on the production contract.
        </Empty>
        <button className="small" onClick={() => navigate({ name: "explore" })}>
          ← Back to registry
        </button>
      </div>
    );

  const t = tv.data;

  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <button className="small ghost" onClick={() => navigate({ name: "explore" })}>
          ← Registry
        </button>
        <button className="small" onClick={refresh} disabled={tv.loading}>
          {tv.loading ? "Refreshing…" : "Refresh state"}
        </button>
      </div>

      <HeaderCard t={t} />

      <TxProgress tx={tx} />

      {tv.data && (
        <>
          {t.kind === "root" ? <EnvelopePanel t={t} /> : <ForkBodyPanel t={t} />}

          <EvidencePanel t={t} act={act} busy={tx.busy} />

          <AdjudicationPanel t={t} act={act} busy={tx.busy} />

          <VerdictHistoryPanel t={t} />

          <ChallengePanel t={t} act={act} busy={tx.busy} />

          <FinalityPanel t={t} act={act} busy={tx.busy} />

          <BondsPanel t={t} act={act} busy={tx.busy} />

          {t.isFaithfulFinal && (
            <ForkCreatorPanel
              parentKind={t.kind}
              parentId={t.id}
              parentFingerprintHex={
                t.kind === "root"
                  ? (t.root!.import_fingerprint as string)
                  : (t.fork!.body_fingerprint as string)
              }
              onCreated={(forkId) => navigate({ name: "fork", id: forkId })}
            />
          )}

          <ProposalTree
            rootId={t.rootId}
            selected={{ kind: t.kind, id: t.id }}
            reloadKey={nonce}
          />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

function HeaderCard({ t }: { t: TargetView }) {
  return (
    <Card>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h2 style={{ margin: "0 0 6px" }}>{t.title}</h2>
          <div className="tiny faint">
            {t.kind === "root" ? "Root proposal" : "Fork"} #{t.id.toString()} ·{" "}
            DAO #{t.daoId.toString()}
            {t.kind === "fork" && (
              <>
                {" · "}
                <a href={`#/root/${t.rootId}`}>root #{t.rootId.toString()}</a>
                {" · depth "}
                {t.fork!.depth}
              </>
            )}
          </div>
        </div>
        <StatusBadge value={t.status} />
      </div>

      <hr className="sep" />

      {t.kind === "root" ? (
        <KV>
          <Row k="External id">{t.root!.external_proposal_id}</Row>
          <Row k="Proposal URL">
            <a href={t.root!.proposal_url} target="_blank" rel="noreferrer">
              {t.root!.proposal_url}
            </a>
          </Row>
          <Row k="Proposer">
            <AddrChip addr={t.root!.proposer} />
          </Row>
          <Row k="Identity">{t.root!.identity_status}</Row>
          <Row k="Import fingerprint">
            <HexChip hex={t.root!.import_fingerprint} label="import" />
          </Row>
          <Row k="Web content fingerprint">
            <HexChip hex={t.root!.web_content_fingerprint} label="web render" />
          </Row>
          <Row k="Governing verdict">
            {t.currentVerdictId > 0n ? `#${t.currentVerdictId}` : "none yet"}
          </Row>
        </KV>
      ) : (
        <KV>
          <Row k="Creator">
            <AddrChip addr={t.fork!.creator} />
          </Row>
          <Row k="Parent">
            {t.fork!.parent_kind === "PARENT_ROOT" ? (
              <a href={`#/root/${t.fork!.parent_id}`}>
                root #{t.fork!.parent_id.toString()}
              </a>
            ) : (
              <a href={`#/fork/${t.fork!.parent_id}`}>
                fork #{t.fork!.parent_id.toString()}
              </a>
            )}
          </Row>
          <Row k="Body fingerprint">
            <HexChip hex={t.fork!.body_fingerprint} label="body" />
          </Row>
          <Row k="Delta fingerprint">
            <HexChip hex={t.fork!.delta_fingerprint} label="delta" />
          </Row>
          <Row k="Parent fingerprint (snapshot)">
            <HexChip hex={t.fork!.parent_fingerprint} label="parent" />
          </Row>
          <Row k="Governing verdict">
            {t.currentVerdictId > 0n ? `#${t.currentVerdictId}` : "none yet"}
          </Row>
          <Row k="Children">{t.fork!.child_count}</Row>
        </KV>
      )}
    </Card>
  );
}

function EnvelopePanel({ t }: { t: TargetView }) {
  const e = t.root!.envelope;
  const submitted = t.status !== "ENVELOPE_NOT_SUBMITTED";
  return (
    <Card title="Intent envelope">
      {!submitted ? (
        <Empty>
          No envelope submitted yet. The proposer submits the semantic intent
          envelope (with a 0.1 GEN bond) from the Build tab.
        </Empty>
      ) : (
        <KV>
          <Row k="Objective">{e.objective}</Row>
          <Row k="Beneficiary class">{e.beneficiary_class}</Row>
          <Row k="Resource type">{e.resource_type}</Row>
          <Row k="Scope">{e.scope}</Row>
          <Row k="Essential constraints">
            <ChipList items={e.essential_constraints} />
          </Row>
          <Row k="Mutable dimensions">
            <ChipList items={e.mutable_dimensions} />
          </Row>
          <Row k="Immutable dimensions">
            <ChipList items={e.immutable_dimensions} />
          </Row>
          <Row k="Envelope version">{e.envelope_version}</Row>
        </KV>
      )}
      {t.root!.structured_parameters.length > 0 && (
        <>
          <hr className="sep" />
          <label>Structured parameters (from import)</label>
          <KV>
            {t.root!.structured_parameters.map((p, i) => (
              <Row k={p.key} key={i}>
                {p.value}
              </Row>
            ))}
          </KV>
        </>
      )}
    </Card>
  );
}

function ForkBodyPanel({ t }: { t: TargetView }) {
  const f = t.fork!;
  return (
    <Card title="Fork body & delta">
      <KV>
        <Row k="Summary">{f.body.summary}</Row>
        <Row k="Reasoning">{f.body.reasoning}</Row>
      </KV>
      {f.body.structured_parameters.length > 0 && (
        <>
          <hr className="sep" />
          <label>Structured parameters</label>
          <KV>
            {f.body.structured_parameters.map((p, i) => (
              <Row k={p.key} key={i}>
                {p.value}
              </Row>
            ))}
          </KV>
        </>
      )}
      <hr className="sep" />
      <label>Declared changes vs parent ({f.delta.length})</label>
      {f.delta.length === 0 ? (
        <Empty>No delta entries.</Empty>
      ) : (
        <div className="list">
          {f.delta.map((d, i) => (
            <div className="list-item" key={i} style={{ cursor: "default" }}>
              <div className="grow">
                <div className="primary-line">
                  {d.dimension_name}{" "}
                  <span className="badge neutral tiny">{d.claim_kind}</span>
                </div>
                <div className="tiny faint">
                  <span style={{ textDecoration: "line-through" }}>
                    {d.parent_value || "∅"}
                  </span>{" "}
                  → {d.fork_value || "∅"}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function ChipList({ items }: { items: string[] }) {
  if (!items.length) return <span className="faint">none</span>;
  return (
    <div className="chips">
      {items.map((it, i) => (
        <span className="badge neutral" key={i}>
          {it}
        </span>
      ))}
    </div>
  );
}

// ---- evidence -----------------------------------------------------------

function EvidencePanel({
  t,
  act,
  busy,
}: {
  t: TargetView;
  act: (fn: () => Promise<any>) => void;
  busy: boolean;
}) {
  if (t.evidenceCaseId === 0n) {
    return (
      <Card title="Evidence case">
        <Empty>
          No evidence case yet.{" "}
          {t.kind === "root"
            ? "It is created when the envelope is submitted."
            : "Submit fork evidence from the Build tab to open one."}
        </Empty>
      </Card>
    );
  }
  const c = t.case;
  const state = c?.state ?? "?";
  const canClose = state === CASE_STATE.OPEN;
  const canSeal = state === CASE_STATE.EVIDENCE_CLOSED;
  const anyFetchable =
    state === CASE_STATE.EVIDENCE_CLOSED &&
    t.evidence.some(
      (e) => e.ev.retrieval_status === RETRIEVAL_STATUS.NOT_FETCHED,
    );

  return (
    <Card
      title={
        <span>
          Evidence case #{t.evidenceCaseId.toString()}{" "}
          {c && <StatusBadge value={c.state} />}
        </span>
      }
    >
      {c && (
        <KV>
          <Row k="Case type">{c.case_type}</Row>
          <Row k="Case fingerprint">
            <HexChip hex={c.case_fingerprint} label="case" />
          </Row>
          <Row k="Membership fingerprint">
            <HexChip hex={c.membership_fingerprint} label="membership" />
          </Row>
          <Row k="Evidence set fingerprint">
            <HexChip hex={c.evidence_set_fingerprint} label="evidence set" />
          </Row>
          <Row k="Retry count">{c.retry_count}</Row>
        </KV>
      )}

      <hr className="sep" />
      <label>Evidence items ({t.evidence.length})</label>
      {t.evidence.length === 0 ? (
        <Empty>No evidence submitted.</Empty>
      ) : (
        <div className="list">
          {t.evidence.map(({ id, ev }) => (
            <div className="list-item" key={id.toString()} style={{ cursor: "default", alignItems: "flex-start" }}>
              <div className="grow">
                <div className="primary-line">
                  <a href={ev.url} target="_blank" rel="noreferrer">
                    {ev.url}
                  </a>
                </div>
                <div className="tiny faint">
                  #{id.toString()} · {ev.evidence_class} · {ev.render_profile} ·
                  submitter <AddrChip addr={ev.submitter} />
                </div>
                {ev.frozen && !isEmptyHex(ev.content_fingerprint) && (
                  <div className="tiny faint">
                    content <HexChip hex={ev.content_fingerprint} />
                    {ev.frozen_content
                      ? ` · ${ev.frozen_content.length} chars frozen`
                      : ""}
                  </div>
                )}
              </div>
              <div className="stack" style={{ gap: 4, alignItems: "flex-end" }}>
                <StatusBadge value={ev.retrieval_status} />
                {c?.state === CASE_STATE.EVIDENCE_CLOSED &&
                  ev.retrieval_status === RETRIEVAL_STATUS.NOT_FETCHED && (
                    <Guarded>
                      <button
                        className="small"
                        disabled={busy}
                        onClick={() =>
                          act(() => api.fetchEvidence(g(), id))
                        }
                      >
                        Fetch (web render)
                      </button>
                    </Guarded>
                  )}
              </div>
            </div>
          ))}
        </div>
      )}

      <hr className="sep" />
      <Guarded>
        <div className="row">
          <button
            className="small primary"
            disabled={busy || !canClose}
            onClick={() => act(() => api.closeEvidence(g(), t.evidenceCaseId))}
            title={
              canClose
                ? "Lock evidence membership (owner only)"
                : "Only while the case is OPEN"
            }
          >
            1 · Close evidence
          </button>
          <button
            className="small"
            disabled
            title="Use the per-item Fetch buttons above"
          >
            2 · Fetch each item {anyFetchable ? "(pending)" : "✓"}
          </button>
          <button
            className="small primary"
            disabled={busy || !canSeal}
            onClick={() => act(() => api.sealEvidence(g(), t.evidenceCaseId))}
            title={
              canSeal
                ? "Freeze the case (permissionless)"
                : "Only after close + required items fetched"
            }
          >
            3 · Seal evidence
          </button>
          {c &&
            (c.state === CASE_STATE.OPEN ||
              c.state === CASE_STATE.EVIDENCE_CLOSED) && (
              <button
                className="small danger"
                disabled={busy}
                onClick={() => act(() => api.abortCase(g(), t.evidenceCaseId))}
                title="Abort a case that can never seal"
              >
                Abort case
              </button>
            )}
        </div>
      </Guarded>
    </Card>
  );
}

// ---- adjudication -----------------------------------------------------

function AdjudicationPanel({
  t,
  act,
  busy,
}: {
  t: TargetView;
  act: (fn: () => Promise<any>) => void;
  busy: boolean;
}) {
  const caseId = t.evidenceCaseId;
  const c = t.case;
  const canArm = c?.state === CASE_STATE.CASE_FROZEN;
  const canRun = c?.state === CASE_STATE.ADJUDICATING;
  const terminalUndetermined = c?.state === CASE_STATE.UNDETERMINED_TERMINAL;

  return (
    <Card title="Semantic adjudication">
      <p className="muted tiny" style={{ marginTop: 0 }}>
        Two transactions: <code>adjudicate</code> arms the case (owner), then
        <code> run_adjudication</code> is the single nondeterministic step —
        validators reach semantic consensus with{" "}
        <code>eq_principle.prompt_comparative</code>. An Undetermined outcome
        commits nothing; re-arm and run again (up to 3 retries).
      </p>

      {terminalUndetermined && (
        <Notice tone="warn">
          Retry budget exhausted — the case is in the deterministic
          <strong> UNDETERMINED_TERMINAL </strong> state. The target finalizes as
          UNCLEAR and the proposer/creator bond is fully refundable.
        </Notice>
      )}

      {t.verdict ? (
        <>
          <div className="row" style={{ marginTop: 6 }}>
            <strong>Verdict #{t.verdict.verdict_id.toString()}:</strong>
            <StatusBadge value={t.verdict.verdict} />
            {BigInt(t.verdict.replaced_by) > 0n && (
              <span className="badge info tiny">
                replaced by #{t.verdict.replaced_by.toString()}
              </span>
            )}
          </div>
          <KV>
            <Row k="Dimensions version">
              {t.verdict.adjudication_dimensions_version}
            </Row>
            <Row k="Prompt fingerprint">
              <HexChip hex={t.verdict.prompt_fingerprint} label="prompt" />
            </Row>
            <Row k="Reasoning hash">
              <HexChip hex={t.verdict.reasoning_hash} label="reasoning" />
            </Row>
            <Row k="Reason codes">
              <ChipList items={t.verdict.reason_codes} />
            </Row>
          </KV>
          <hr className="sep" />
          <label>Dimension findings</label>
          <div className="list">
            {t.verdict.dimensions.map((d, i) => (
              <div className="list-item" key={i} style={{ cursor: "default", alignItems: "flex-start" }}>
                <div className="grow">
                  <div className="primary-line">{d.name}</div>
                  <div className="tiny muted">{d.reasoning}</div>
                  {d.evidence_ids.length > 0 && (
                    <div className="tiny faint">
                      evidence:{" "}
                      {d.evidence_ids.map((e) => `#${e.toString()}`).join(", ")}
                    </div>
                  )}
                </div>
                <StatusBadge value={d.finding} />
              </div>
            ))}
          </div>
        </>
      ) : (
        <Empty>No verdict yet.</Empty>
      )}

      {caseId > 0n && (
        <>
          <hr className="sep" />
          <Guarded>
            <div className="row">
              <button
                className="small primary"
                disabled={busy || !canArm}
                onClick={() => act(() => api.adjudicate(g(), caseId))}
                title={canArm ? "Arm (owner only)" : "Only when case is CASE_FROZEN"}
              >
                Arm: adjudicate
              </button>
              <button
                className="small primary"
                disabled={busy || !canRun}
                onClick={() => act(() => api.runAdjudication(g(), caseId))}
                title={canRun ? "Run the semantic step" : "Arm the case first"}
              >
                Run adjudication
              </button>
              {canRun && (
                <button
                  className="small"
                  disabled={busy}
                  onClick={() => act(() => api.adjudicate(g(), caseId))}
                  title="Re-arm after an Undetermined run (advances retry counter)"
                >
                  Re-arm (retry {c ? c.retry_count : 0}/3)
                </button>
              )}
            </div>
          </Guarded>
        </>
      )}
    </Card>
  );
}

// ---- verdict history --------------------------------------------------

function VerdictHistoryPanel({ t }: { t: TargetView }) {
  if (t.verdictHistory.length <= 1) return null;
  return (
    <Card title="Verdict history">
      <div className="list">
        {t.verdictHistory.map((vid) => (
          <div
            className="list-item"
            key={vid.toString()}
            style={{ cursor: "default" }}
          >
            <div className="grow primary-line">Verdict #{vid.toString()}</div>
            {vid === t.currentVerdictId && (
              <span className="badge ok tiny">governing</span>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

// ---- challenges -------------------------------------------------------

function ChallengePanel({
  t,
  act,
  busy,
}: {
  t: TargetView;
  act: (fn: () => Promise<any>) => void;
  busy: boolean;
}) {
  const grounds =
    t.kind === "root"
      ? CHALLENGE_GROUNDS_ROOT_ENVELOPE
      : CHALLENGE_GROUNDS_FORK;
  const [ground, setGround] = useState<string>(grounds[0]);
  const [argument, setArgument] = useState("");

  const decisiveVerdict =
    !!t.verdict &&
    t.case?.state === CASE_STATE.SUCCESS &&
    t.verdict.verdict !== "INVALID";
  const canOpen =
    decisiveVerdict &&
    !t.isFinal &&
    !t.openChallenge &&
    t.challenges.length < 3;

  const openChallenge = async () => {
    const c = g();
    // lock CHALLENGE bond, then challenge_verdict(bond_id, …)
    const { bondId } = await api.lockBond(c, BOND_PURPOSE.CHALLENGE);
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
    <Card title={`Challenges (${t.challenges.length}/3)`}>
      {t.challenges.length === 0 && <Empty>No challenges opened.</Empty>}

      {t.challenges.map(({ id, challenge, case: cCase }) => (
        <div
          className="card"
          key={id.toString()}
          style={{ margin: "0 0 10px", background: "var(--bg-sunken)" }}
        >
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong>Challenge #{id.toString()}</strong>
            <StatusBadge value={challenge.status} />
          </div>
          <KV>
            <Row k="Challenger">
              <AddrChip addr={challenge.challenger} />
            </Row>
            <Row k="Ground">{challenge.ground_code}</Row>
            <Row k="Argument">{challenge.argument}</Row>
            <Row k="Original verdict">
              #{challenge.original_verdict_id.toString()}
            </Row>
            {BigInt(challenge.replacement_verdict_id) > 0n && (
              <Row k="Replacement verdict">
                #{challenge.replacement_verdict_id.toString()}
              </Row>
            )}
            <Row k="Challenge case">
              #{challenge.case_id.toString()}
              {cCase && <> · <StatusBadge value={cCase.state} /></>}
            </Row>
          </KV>

          {cCase &&
            (challenge.status === "OPEN" ||
              challenge.status === "ADJUDICATING") && (
              <Guarded>
                <div className="row" style={{ marginTop: 8 }}>
                  <button
                    className="small primary"
                    disabled={busy || cCase.state !== CASE_STATE.CASE_FROZEN}
                    onClick={() =>
                      act(() => api.adjudicate(g(), BigInt(challenge.case_id)))
                    }
                  >
                    Arm challenge
                  </button>
                  <button
                    className="small primary"
                    disabled={busy || cCase.state !== CASE_STATE.ADJUDICATING}
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
        <>
          <hr className="sep" />
          <label>Open a challenge — 0.1 GEN bond</label>
          <p className="muted tiny">
            "Don't vote YES or NO." A challenge doesn't reject the proposal — it
            asserts the semantic adjudication got a specific dimension wrong and
            triggers a re-adjudication. Flip → bond refunded + 0.05 GEN reward;
            unchanged → half the bond is slashed.
          </p>
          <div className="grid2">
            <div>
              <label>Ground</label>
              <select value={ground} onChange={(e) => setGround(e.target.value)}>
                {grounds.map((gnd) => (
                  <option key={gnd} value={gnd}>
                    {gnd}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div style={{ marginTop: 8 }}>
            <label>Argument (≤ 512 chars)</label>
            <textarea
              value={argument}
              maxLength={512}
              onChange={(e) => setArgument(e.target.value)}
              placeholder="Explain precisely which dimension finding is wrong and why the evidence supports a different finding."
            />
          </div>
          <Guarded>
            <button
              className="primary"
              style={{ marginTop: 8 }}
              disabled={busy || argument.trim().length < 1}
              onClick={() => act(openChallenge)}
            >
              Lock bond & open challenge
            </button>
          </Guarded>
        </>
      )}
    </Card>
  );
}

// ---- finality --------------------------------------------------------

function FinalityPanel({
  t,
  act,
  busy,
}: {
  t: TargetView;
  act: (fn: () => Promise<any>) => void;
  busy: boolean;
}) {
  const hasVerdict = t.currentVerdictId > 0n;
  const canFinalize = hasVerdict && !t.isFinal && !t.openChallenge;

  return (
    <Card title="Finality">
      {t.isFinal ? (
        <Notice tone={t.isFaithfulFinal ? "ok" : "info"}>
          This {t.kind} is <strong>final</strong> ({t.status}).
          {t.isFaithfulFinal
            ? " It is now forkable — anyone can create a semantic-descendant fork below."
            : t.status.includes("FAITHFUL")
              ? ""
              : " It is not forkable."}
        </Notice>
      ) : (
        <>
          <p className="muted tiny" style={{ marginTop: 0 }}>
            Once a decisive verdict exists and no challenge is open, the owner
            finalizes. After the challenge budget is spent, anyone may force
            finality so an absent owner can't brick the target.
          </p>
          <Guarded>
            <button
              className="primary"
              disabled={busy || !canFinalize}
              onClick={() =>
                act(() => api.finalize(g(), t.id, t.targetKindConst))
              }
              title={
                !hasVerdict
                  ? "No verdict yet"
                  : t.openChallenge
                    ? "Resolve the open challenge first"
                    : "Finalize"
              }
            >
              Finalize {t.kind}
            </button>
          </Guarded>
        </>
      )}
    </Card>
  );
}

// ---- bonds ----------------------------------------------------------

function BondsPanel({
  t,
  act,
  busy,
}: {
  t: TargetView;
  act: (fn: () => Promise<any>) => void;
  busy: boolean;
}) {
  return (
    <Card title="Bonds & settlement">
      {t.bonds.length === 0 ? (
        <Empty>No bonds assigned to this {t.kind}.</Empty>
      ) : (
        <div className="list">
          {t.bonds.map(({ id, bond }) => {
            const settleable = !bond.settled && t.isFinal;
            return (
              <div
                className="list-item"
                key={id.toString()}
                style={{ cursor: "default", alignItems: "flex-start" }}
              >
                <div className="grow">
                  <div className="primary-line">
                    Bond #{id.toString()} · {bond.purpose} ·{" "}
                    {formatGen(bond.amount)}
                  </div>
                  <div className="tiny faint">
                    owner <AddrChip addr={bond.owner} />
                    {bond.settled && (
                      <>
                        {" · refund "}
                        {formatGen(bond.refund_amount)}
                        {" · slash "}
                        {formatGen(bond.slash_amount)}
                        {BigInt(bond.reward_amount) > 0n &&
                          ` · reward ${formatGen(bond.reward_amount)}`}
                      </>
                    )}
                  </div>
                </div>
                <div className="stack" style={{ gap: 4, alignItems: "flex-end" }}>
                  <StatusBadge value={bond.settlement_kind} />
                  {settleable && (
                    <Guarded>
                      <button
                        className="small primary"
                        disabled={busy}
                        onClick={() => act(() => api.settleBond(g(), id))}
                      >
                        Settle
                      </button>
                    </Guarded>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {!t.isFinal && t.bonds.some((b) => !b.bond.settled) && (
        <p className="muted tiny">
          Bonds settle after the {t.kind} is finalized. A CHALLENGE bond settles
          only after the proposer/creator bond.
        </p>
      )}
    </Card>
  );
}
