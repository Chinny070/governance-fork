import { useMemo, useState } from "react";
import * as api from "../lib/api";
import { getActiveWriteClient as g } from "../lib/activeClient";
import { collectAll, getDao, listDaos } from "../lib/api";
import { BOND_PURPOSE, RESOURCE_TYPES } from "../lib/enums";
import { formatGen } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { useTx } from "../lib/useTx";
import type { Dao } from "../lib/types";
import { Note, SectionHead, StatusTag } from "../components/ui";
import { Guarded } from "../components/Guarded";
import { TxProgress } from "../components/TxProgress";
import { ArrayInput } from "../components/ArrayInput";
import {
  EvidenceForm,
  emptyEvidenceRow,
  evidenceRowsToArrays,
  type EvidenceRow,
} from "../components/EvidenceForm";
import { DEMO_PROPOSAL } from "../lib/demo";

type Step = 1 | 2 | 3 | 4 | 5;
const RAIL: [Step, string][] = [
  [1, "DAO"],
  [2, "Root"],
  [3, "Intent"],
  [4, "Review"],
];

async function loadDaos(): Promise<{ id: bigint; dao: Dao }[]> {
  const ids = await collectAll((c) => listDaos(c));
  const out: { id: bigint; dao: Dao }[] = [];
  for (const id of ids) {
    const dao = await getDao(id);
    if (dao) out.push({ id, dao });
  }
  return out;
}

export function BuildFlow() {
  const daos = useAsync(loadDaos, []);
  const tx = useTx();
  const [step, setStep] = useState<Step>(1);

  const [daoMode, setDaoMode] = useState<"existing" | "new">("existing");
  const [daoId, setDaoId] = useState<bigint | null>(null);
  const [daoName, setDaoName] = useState("");
  const [daoUrl, setDaoUrl] = useState("");

  const [extId, setExtId] = useState("");
  const [title, setTitle] = useState("");
  const [proposalUrl, setProposalUrl] = useState("");
  const [rootKeys, setRootKeys] = useState<string[]>([]);
  const [rootVals, setRootVals] = useState<string[]>([]);
  const [rootId, setRootId] = useState<bigint | null>(null);

  const [objective, setObjective] = useState("");
  const [beneficiary, setBeneficiary] = useState("");
  const [resourceType, setResourceType] = useState<string>(RESOURCE_TYPES[0]);
  const [scope, setScope] = useState("");
  const [essential, setEssential] = useState<string[]>([]);
  const [mutable, setMutable] = useState<string[]>([]);
  const [immutable, setImmutable] = useState<string[]>([]);
  const [evidence, setEvidence] = useState<EvidenceRow[]>([emptyEvidenceRow()]);
  const [formError, setFormError] = useState<string | null>(null);

  const daoLabel =
    daoMode === "new"
      ? daoName || "—"
      : daos.data?.find((d) => d.id === daoId)?.dao.name ?? "—";
  const evCount = evidence.filter((e) => e.url.trim()).length;

  const prefillDemo = () => {
    const d = DEMO_PROPOSAL;
    setDaoMode("new");
    setDaoName(d.dao.name);
    setDaoUrl(d.dao.url);
    setExtId(d.root.externalId);
    setTitle(d.root.title);
    setProposalUrl(d.root.url);
    setRootKeys(d.root.params.map((p) => p[0]));
    setRootVals(d.root.params.map((p) => p[1]));
    setObjective(d.envelope.objective);
    setBeneficiary(d.envelope.beneficiaryClass);
    setResourceType(d.envelope.resourceType);
    setScope(d.envelope.scope);
    setEssential(d.envelope.essentialConstraints);
    setMutable(d.envelope.mutableDimensions);
    setImmutable(d.envelope.immutableDimensions);
    setEvidence(
      d.evidence.map((e) => ({
        url: e.url,
        evidenceClass: e.evidenceClass,
        relevanceClaim: e.relevanceClaim,
        authorityClaim: e.authorityClaim,
        temporalMarker: e.temporalMarker,
        renderProfile: e.renderProfile,
      })),
    );
  };

  const LIMITS = { objective: 512, beneficiary: 128, scope: 256, essential: 128, dimension: 64 };
  const lengthProblem = (): string | null => {
    if (objective.trim().length > LIMITS.objective) return `Objective too long (max ${LIMITS.objective}).`;
    if (beneficiary.trim().length > LIMITS.beneficiary) return `Beneficiary class too long (max ${LIMITS.beneficiary}).`;
    if (scope.trim().length > LIMITS.scope) return `Scope too long (max ${LIMITS.scope}).`;
    for (const c of essential)
      if (c.trim().length > LIMITS.essential) return `Constraint "${c.slice(0, 28)}…" too long (max ${LIMITS.essential}).`;
    for (const d of [...mutable, ...immutable])
      if (d.trim().length > LIMITS.dimension) return `Dimension "${d.slice(0, 28)}…" too long (max ${LIMITS.dimension}).`;
    return null;
  };

  const doDao = async () => {
    if (daoMode === "existing") {
      if (daoId) setStep(2);
      return;
    }
    const w = await tx.run(() => api.registerDao(g(), daoName.trim(), daoUrl.trim()));
    if (w?.returnValue) {
      setDaoId(BigInt(w.returnValue.match(/\d+/)?.[0] ?? "0"));
      await daos.refresh();
      setDaoMode("existing");
      setStep(2);
    }
  };

  const doImport = async () => {
    if (!daoId) return;
    const w = await tx.run(() =>
      api.importRootProposal(g(), {
        daoId,
        externalProposalId: extId.trim(),
        title: title.trim(),
        proposalUrl: proposalUrl.trim(),
        paramKeys: rootKeys.filter((k) => k.trim()),
        paramValues: rootVals.slice(0, rootKeys.filter((k) => k.trim()).length),
      }),
    );
    if (w?.returnValue) {
      setRootId(BigInt(w.returnValue.match(/\d+/)?.[0] ?? "0"));
      setStep(3);
    }
  };

  const goReview = () => {
    const p = lengthProblem();
    if (p) {
      setFormError(p);
      return;
    }
    setFormError(null);
    setStep(4);
  };

  const doEnvelope = async () => {
    if (!rootId) return;
    const ev = evidenceRowsToArrays(evidence);
    const w = await tx.run(async () => {
      const c = g();
      const { bondId } = await api.lockBond(c, BOND_PURPOSE.ENVELOPE);
      return api.submitRootEnvelope(c, bondId, {
        rootId,
        objective: objective.trim(),
        beneficiaryClass: beneficiary.trim(),
        resourceType,
        scope: scope.trim(),
        essentialConstraints: essential.filter((x) => x.trim()),
        mutableDimensions: mutable.filter((x) => x.trim()),
        immutableDimensions: immutable.filter((x) => x.trim()),
        evidenceUrls: ev.evidenceUrls,
        evidenceClasses: ev.evidenceClasses,
        relevanceClaims: ev.relevanceClaims,
        authorityClaims: ev.authorityClaims,
        temporalMarkers: ev.temporalMarkers,
        renderProfiles: ev.renderProfiles,
      });
    });
    if (w) setStep(5);
  };

  const railState = (s: Step) =>
    s === step ? "on" : s < step ? "done" : "";

  return (
    <div className="stack">
      <div className="between" style={{ alignItems: "flex-end" }}>
        <div>
          <p className="eyebrow">Build</p>
          <h1 className="display" style={{ fontSize: "clamp(24px,3.2vw,32px)" }}>
            Import a proposal.<br />Then let people change it.
          </h1>
        </div>
        <button className="small" onClick={prefillDemo}>
          Pre-fill demo proposal
        </button>
      </div>

      <TxProgress tx={tx} />

      <div className="build">
        {/* rail */}
        <div className="rail">
          {RAIL.map(([s, label]) => (
            <button
              key={s}
              className={`rail-step ${railState(s)}`}
              onClick={() => s < step && setStep(s)}
              disabled={s > step}
            >
              <span className="n">{String(s).padStart(2, "0")}</span>
              <span className="l">{label}</span>
            </button>
          ))}
        </div>

        {/* canvas */}
        <div className="canvas stack">
          {step === 1 && (
            <div>
              <SectionHead eyebrow="01" title="Governance body" />
              <div className="row" style={{ marginBottom: 14 }}>
                <label className="row" style={{ gap: 6, textTransform: "none", letterSpacing: 0 }}>
                  <input
                    type="radio"
                    style={{ width: "auto" }}
                    checked={daoMode === "existing"}
                    onChange={() => setDaoMode("existing")}
                  />
                  Use existing
                </label>
                <label className="row" style={{ gap: 6, textTransform: "none", letterSpacing: 0 }}>
                  <input
                    type="radio"
                    style={{ width: "auto" }}
                    checked={daoMode === "new"}
                    onChange={() => setDaoMode("new")}
                  />
                  Register new
                </label>
              </div>

              {daoMode === "existing" ? (
                <div className="field">
                  <label>DAO</label>
                  <select
                    value={daoId?.toString() ?? ""}
                    onChange={(e) =>
                      setDaoId(e.target.value ? BigInt(e.target.value) : null)
                    }
                  >
                    <option value="">— select —</option>
                    {(daos.data ?? []).map(({ id, dao }) => (
                      <option key={id.toString()} value={id.toString()}>
                        #{id.toString()} · {dao.name}
                      </option>
                    ))}
                  </select>
                  {daos.loading && <div className="field-help">loading…</div>}
                </div>
              ) : (
                <>
                  <div className="field">
                    <label>DAO name</label>
                    <input value={daoName} onChange={(e) => setDaoName(e.target.value)} />
                  </div>
                  <div className="field">
                    <label>DAO URL</label>
                    <input value={daoUrl} onChange={(e) => setDaoUrl(e.target.value)} />
                  </div>
                </>
              )}

              <Guarded>
                <button
                  className="primary"
                  disabled={
                    tx.busy ||
                    (daoMode === "existing"
                      ? !daoId
                      : !daoName.trim() || !daoUrl.trim())
                  }
                  onClick={doDao}
                >
                  {daoMode === "existing" ? "Continue" : "Register DAO & continue"}
                </button>
              </Guarded>
            </div>
          )}

          {step === 2 && (
            <div>
              <SectionHead eyebrow="02" title={`Import root proposal · DAO ${daoId?.toString()}`} />
              <div className="field">
                <label>External proposal id</label>
                <input value={extId} onChange={(e) => setExtId(e.target.value)} />
              </div>
              <div className="field">
                <label>Title</label>
                <input value={title} onChange={(e) => setTitle(e.target.value)} />
              </div>
              <div className="field">
                <label>Proposal URL — the authoritative page</label>
                <input value={proposalUrl} onChange={(e) => setProposalUrl(e.target.value)} />
              </div>
              <div className="grid-2">
                <ArrayInput label="Parameter keys" values={rootKeys} onChange={setRootKeys} max={32} />
                <ArrayInput label="Parameter values" values={rootVals} onChange={setRootVals} max={32} />
              </div>
              <div className="row">
                <button className="ghost" onClick={() => setStep(1)}>← Back</button>
                <Guarded>
                  <button
                    className="primary"
                    disabled={tx.busy || !extId.trim() || !title.trim() || !proposalUrl.trim()}
                    onClick={doImport}
                  >
                    Import root proposal
                  </button>
                </Guarded>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <SectionHead eyebrow="03" title={`Intent envelope · root ${rootId?.toString()}`} />
              <div className="field">
                <label>Objective — what the proposal is fundamentally for</label>
                <textarea value={objective} onChange={(e) => setObjective(e.target.value)} />
              </div>
              <div className="grid-2">
                <div className="field">
                  <label>Beneficiary class</label>
                  <input value={beneficiary} onChange={(e) => setBeneficiary(e.target.value)} />
                </div>
                <div className="field">
                  <label>Resource type</label>
                  <select value={resourceType} onChange={(e) => setResourceType(e.target.value)}>
                    {RESOURCE_TYPES.map((r) => (
                      <option key={r}>{r}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="field">
                <label>Scope</label>
                <input value={scope} onChange={(e) => setScope(e.target.value)} />
              </div>
              <div className="grid-3">
                <ArrayInput label="Essential constraints" values={essential} onChange={setEssential} max={8} hint="Must survive every fork" />
                <ArrayInput label="Mutable dimensions" values={mutable} onChange={setMutable} max={16} hint="A fork may change these" />
                <ArrayInput label="Immutable dimensions" values={immutable} onChange={setImmutable} max={16} hint="A fork may not" />
              </div>

              <hr className="rule" style={{ margin: "8px 0 16px" }} />
              <p className="eyebrow" style={{ marginBottom: 10 }}>
                Supporting evidence — real, renderable URLs
              </p>
              <EvidenceForm rows={evidence} onChange={setEvidence} max={8} />

              {formError && <Note tone="red">{formError}</Note>}

              <div className="row" style={{ marginTop: 16 }}>
                <button className="ghost" onClick={() => setStep(2)}>← Back</button>
                <button
                  className="primary"
                  disabled={!objective.trim() || !scope.trim() || evCount === 0}
                  onClick={goReview}
                >
                  Review →
                </button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div>
              <SectionHead eyebrow="04" title="Review & commit" />
              <p className="muted" style={{ marginTop: 0 }}>
                Submitting locks a <strong>{formatGen(api.BOND_AMOUNT_WEI)}</strong>{" "}
                ENVELOPE bond. It is refunded in full if the envelope is finalized
                FAITHFUL / UNCLEAR, and half-slashed to the treasury if it is
                finalized NOT_FAITHFUL.
              </p>

              <dl className="dl" style={{ marginTop: 12 }}>
                <dt>DAO</dt>
                <dd>{daoLabel} · #{daoId?.toString()}</dd>
                <dt>Root proposal</dt>
                <dd>#{rootId?.toString()} · {title}</dd>
                <dt>Objective</dt>
                <dd>{objective}</dd>
                <dt>Scope</dt>
                <dd>{scope}</dd>
                <dt>Constraints</dt>
                <dd>{essential.filter((x) => x.trim()).join(" · ") || "—"}</dd>
                <dt>Mutable</dt>
                <dd>{mutable.filter((x) => x.trim()).join(" · ") || "—"}</dd>
                <dt>Immutable</dt>
                <dd>{immutable.filter((x) => x.trim()).join(" · ") || "—"}</dd>
                <dt>Evidence</dt>
                <dd>{evCount} source{evCount === 1 ? "" : "s"} — fetched & sealed on-chain after submit</dd>
              </dl>

              <div className="review cost" style={{ marginTop: 16 }}>
                lock_bond("ENVELOPE") → {formatGen(api.BOND_AMOUNT_WEI)} ·
                then submit_root_envelope(bond_id, …)
              </div>

              <div className="row" style={{ marginTop: 16 }}>
                <button className="ghost" onClick={() => setStep(3)}>← Edit</button>
                <Guarded>
                  <button className="primary" disabled={tx.busy} onClick={doEnvelope}>
                    Lock {formatGen(api.BOND_AMOUNT_WEI)} & submit envelope
                  </button>
                </Guarded>
              </div>
            </div>
          )}

          {step === 5 && rootId != null && (
            <div>
              <SectionHead eyebrow="Done" title="Envelope submitted" />
              <div className="row" style={{ marginBottom: 12 }}>
                <StatusTag value="ENVELOPE_EVIDENCE_OPEN" tone="blue" />
              </div>
              <p className="muted">
                Root #{rootId.toString()} now has an open evidence case. Continue
                on the proposal page: close evidence → fetch each source → seal →
                arm adjudication → run the semantic step → finalize.
              </p>
              <button
                className="primary"
                onClick={() => navigate({ name: "root", id: rootId })}
              >
                Open proposal #{rootId.toString()} →
              </button>
            </div>
          )}
        </div>

        {/* review rail */}
        <ReviewPanel
          step={step}
          dao={daoLabel}
          daoId={daoId}
          extId={extId}
          title={title}
          rootId={rootId}
          objective={objective}
          resourceType={resourceType}
          mutable={mutable.filter((x) => x.trim())}
          immutable={immutable.filter((x) => x.trim())}
          evCount={evCount}
        />
      </div>
    </div>
  );
}

function ReviewPanel(p: {
  step: Step;
  dao: string;
  daoId: bigint | null;
  extId: string;
  title: string;
  rootId: bigint | null;
  objective: string;
  resourceType: string;
  mutable: string[];
  immutable: string[];
  evCount: number;
}) {
  const intentSummary = useMemo(() => {
    if (!p.objective) return "—";
    return p.objective.length > 120 ? p.objective.slice(0, 120) + "…" : p.objective;
  }, [p.objective]);

  return (
    <div className="review">
      <h4>Commit summary</h4>
      <div className="line">
        <span className="k">DAO</span>
        <span className="v">
          {p.dao}
          {p.daoId != null && ` · #${p.daoId}`}
        </span>
      </div>
      <div className="line">
        <span className="k">Proposal</span>
        <span className="v">
          {p.title || p.extId || "—"}
          {p.rootId != null && ` · #${p.rootId}`}
        </span>
      </div>
      <div className="line">
        <span className="k">Resource</span>
        <span className="v">{p.resourceType}</span>
      </div>
      <div className="line">
        <span className="k">Intent</span>
        <span className="v" style={{ maxWidth: 160 }}>
          {intentSummary}
        </span>
      </div>
      <div className="line">
        <span className="k">Mutable</span>
        <span className="v">{p.mutable.length}</span>
      </div>
      <div className="line">
        <span className="k">Immutable</span>
        <span className="v">{p.immutable.length}</span>
      </div>
      <div className="line">
        <span className="k">Evidence</span>
        <span className="v">
          {p.evCount || 0} {p.evCount === 1 ? "source" : "sources"}
        </span>
      </div>

      <div className="cost">
        Bond on submit: {formatGen(api.BOND_AMOUNT_WEI)}
        <br />
        refundable · half-slashed only if NOT_FAITHFUL
      </div>

      {p.step < 4 && (
        <p className="tiny faint" style={{ marginTop: 10 }}>
          No transaction is signed until step 04.
        </p>
      )}
    </div>
  );
}
