import { useState } from "react";
import * as api from "../lib/api";
import { getActiveWriteClient as g } from "../lib/activeClient";
import {
  BOND_PURPOSE,
  RESOURCE_TYPES,
} from "../lib/enums";
import { formatGen } from "../lib/format";
import { navigate } from "../lib/router";
import { useAsync } from "../lib/useAsync";
import { useTx } from "../lib/useTx";
import { collectAll, getDao, listDaos } from "../lib/api";
import type { Dao } from "../lib/types";
import { Card, Notice, StatusBadge } from "../components/ui";
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

type Step = 1 | 2 | 3 | 4;

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

  // step 1
  const [daoMode, setDaoMode] = useState<"existing" | "new">("existing");
  const [daoId, setDaoId] = useState<bigint | null>(null);
  const [daoName, setDaoName] = useState("");
  const [daoUrl, setDaoUrl] = useState("");

  // step 2
  const [extId, setExtId] = useState("");
  const [title, setTitle] = useState("");
  const [proposalUrl, setProposalUrl] = useState("");
  const [rootParamKeys, setRootParamKeys] = useState<string[]>([]);
  const [rootParamValues, setRootParamValues] = useState<string[]>([]);
  const [rootId, setRootId] = useState<bigint | null>(null);

  // step 3
  const [objective, setObjective] = useState("");
  const [beneficiary, setBeneficiary] = useState("");
  const [resourceType, setResourceType] = useState<string>(RESOURCE_TYPES[0]);
  const [scope, setScope] = useState("");
  const [essential, setEssential] = useState<string[]>([]);
  const [mutable, setMutable] = useState<string[]>([]);
  const [immutable, setImmutable] = useState<string[]>([]);
  const [evidence, setEvidence] = useState<EvidenceRow[]>([emptyEvidenceRow()]);
  const [formError, setFormError] = useState<string | null>(null);

  const prefillDemo = () => {
    const d = DEMO_PROPOSAL;
    setDaoMode("new");
    setDaoName(d.dao.name);
    setDaoUrl(d.dao.url);
    setExtId(d.root.externalId);
    setTitle(d.root.title);
    setProposalUrl(d.root.url);
    setRootParamKeys(d.root.params.map((p) => p[0]));
    setRootParamValues(d.root.params.map((p) => p[1]));
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

  // ---- step actions ----

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
        paramKeys: rootParamKeys.filter((k) => k.trim()),
        paramValues: rootParamValues.slice(
          0,
          rootParamKeys.filter((k) => k.trim()).length,
        ),
      }),
    );
    if (w?.returnValue) {
      setRootId(BigInt(w.returnValue.match(/\d+/)?.[0] ?? "0"));
      setStep(3);
    }
  };

  // Contract string limits (contracts/governance_fork.py). Checked client-side
  // so a too-long field fails here instead of wasting a locked bond on a revert.
  const LIMITS = {
    objective: 512,
    beneficiary: 128,
    scope: 256,
    essential: 128,
    dimension: 64,
  };
  const lengthProblem = (): string | null => {
    if (objective.trim().length > LIMITS.objective)
      return `Objective is too long (max ${LIMITS.objective}).`;
    if (beneficiary.trim().length > LIMITS.beneficiary)
      return `Beneficiary class is too long (max ${LIMITS.beneficiary}).`;
    if (scope.trim().length > LIMITS.scope)
      return `Scope is too long (max ${LIMITS.scope}).`;
    for (const c of essential)
      if (c.trim().length > LIMITS.essential)
        return `Essential constraint "${c.slice(0, 30)}…" is too long (max ${LIMITS.essential}).`;
    for (const d of [...mutable, ...immutable])
      if (d.trim().length > LIMITS.dimension)
        return `Dimension "${d.slice(0, 30)}…" is too long (max ${LIMITS.dimension} chars).`;
    return null;
  };

  const doEnvelope = async () => {
    if (!rootId) return;
    const problem = lengthProblem();
    if (problem) {
      setFormError(problem);
      return;
    }
    setFormError(null);
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
    if (w) setStep(4);
  };

  return (
    <div className="stack">
      <Card
        title="Build a new proposal"
        actions={
          <button className="small" onClick={prefillDemo}>
            Pre-fill demo proposal
          </button>
        }
      >
        <p className="muted" style={{ marginTop: 0 }}>
          Register a DAO, import a real governance proposal, then submit the
          semantic intent envelope with its 0.1 GEN bond. Evidence retrieval,
          adjudication and finality continue on the proposal page.
        </p>
        <div className="chips">
          {([1, 2, 3, 4] as Step[]).map((s) => (
            <span
              key={s}
              className={`badge ${s === step ? "info" : s < step ? "ok" : "neutral"}`}
            >
              {s}.{" "}
              {["DAO", "Import root", "Intent envelope", "Done"][s - 1]}
            </span>
          ))}
        </div>
      </Card>

      <TxProgress tx={tx} />

      {step === 1 && (
        <Card title="1 · DAO">
          <div className="row" style={{ marginBottom: 12 }}>
            <label className="row" style={{ gap: 6 }}>
              <input
                type="radio"
                style={{ width: "auto" }}
                checked={daoMode === "existing"}
                onChange={() => setDaoMode("existing")}
              />
              Use existing
            </label>
            <label className="row" style={{ gap: 6 }}>
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
            <div>
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
              {daos.loading && <div className="tiny muted">loading DAOs…</div>}
            </div>
          ) : (
            <div className="stack">
              <div>
                <label>DAO name</label>
                <input
                  value={daoName}
                  onChange={(e) => setDaoName(e.target.value)}
                />
              </div>
              <div>
                <label>DAO URL</label>
                <input
                  value={daoUrl}
                  onChange={(e) => setDaoUrl(e.target.value)}
                />
              </div>
            </div>
          )}

          <Guarded>
            <button
              className="primary"
              style={{ marginTop: 12 }}
              disabled={
                tx.busy ||
                (daoMode === "existing" ? !daoId : !daoName.trim() || !daoUrl.trim())
              }
              onClick={doDao}
            >
              {daoMode === "existing" ? "Continue" : "Register DAO & continue"}
            </button>
          </Guarded>
        </Card>
      )}

      {step === 2 && (
        <Card title={`2 · Import root proposal into DAO #${daoId?.toString()}`}>
          <div className="stack">
            <div>
              <label>External proposal id</label>
              <input value={extId} onChange={(e) => setExtId(e.target.value)} />
            </div>
            <div>
              <label>Title</label>
              <input value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <div>
              <label>Proposal URL (the authoritative page)</label>
              <input
                value={proposalUrl}
                onChange={(e) => setProposalUrl(e.target.value)}
              />
            </div>
            <div className="grid2">
              <ArrayInput
                label="Structured parameter keys"
                values={rootParamKeys}
                onChange={setRootParamKeys}
                max={32}
              />
              <ArrayInput
                label="Structured parameter values"
                values={rootParamValues}
                onChange={setRootParamValues}
                max={32}
              />
            </div>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button className="ghost" onClick={() => setStep(1)}>
              ← Back
            </button>
            <Guarded>
              <button
                className="primary"
                disabled={
                  tx.busy ||
                  !extId.trim() ||
                  !title.trim() ||
                  !proposalUrl.trim()
                }
                onClick={doImport}
              >
                Import root proposal
              </button>
            </Guarded>
          </div>
        </Card>
      )}

      {step === 3 && (
        <Card title={`3 · Intent envelope for root #${rootId?.toString()}`}>
          <div className="stack">
            <div>
              <label>Objective (what the proposal is fundamentally for)</label>
              <textarea
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
              />
            </div>
            <div className="grid2">
              <div>
                <label>Beneficiary class</label>
                <input
                  value={beneficiary}
                  onChange={(e) => setBeneficiary(e.target.value)}
                />
              </div>
              <div>
                <label>Resource type</label>
                <select
                  value={resourceType}
                  onChange={(e) => setResourceType(e.target.value)}
                >
                  {RESOURCE_TYPES.map((r) => (
                    <option key={r}>{r}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label>Scope</label>
              <input value={scope} onChange={(e) => setScope(e.target.value)} />
            </div>
            <div className="grid3">
              <ArrayInput
                label="Essential constraints"
                values={essential}
                onChange={setEssential}
                max={8}
                hint="Must survive every fork"
              />
              <ArrayInput
                label="Mutable dimensions"
                values={mutable}
                onChange={setMutable}
                max={16}
                hint="A fork may change these"
              />
              <ArrayInput
                label="Immutable dimensions"
                values={immutable}
                onChange={setImmutable}
                max={16}
                hint="A fork may not change these"
              />
            </div>

            <hr className="sep" />
            <label>Supporting evidence (real, renderable URLs)</label>
            <EvidenceForm rows={evidence} onChange={setEvidence} max={8} />

            <Notice tone="info">
              Bond: {formatGen(api.BOND_AMOUNT_WEI)} —{" "}
              <code>lock_bond("ENVELOPE")</code> then{" "}
              <code>submit_root_envelope(bond_id, …)</code>.
            </Notice>

            {formError && <Notice tone="bad">{formError}</Notice>}
          </div>

          <div className="row" style={{ marginTop: 12 }}>
            <button className="ghost" onClick={() => setStep(2)}>
              ← Back
            </button>
            <Guarded>
              <button
                className="primary"
                disabled={
                  tx.busy ||
                  !objective.trim() ||
                  !scope.trim() ||
                  evidence.filter((e) => e.url.trim()).length === 0
                }
                onClick={doEnvelope}
              >
                Lock bond & submit envelope
              </button>
            </Guarded>
          </div>
        </Card>
      )}

      {step === 4 && rootId != null && (
        <Card title="Envelope submitted">
          <div className="row" style={{ marginBottom: 12 }}>
            <StatusBadge value="ENVELOPE_EVIDENCE_OPEN" />
          </div>
          <p className="muted">
            Root proposal #{rootId.toString()} now has an open evidence case.
            Continue on the proposal page: close evidence → fetch each item (real
            web render) → seal → arm adjudication → run the semantic step →
            finalize.
          </p>
          <button
            className="primary"
            onClick={() => navigate({ name: "root", id: rootId })}
          >
            Open proposal #{rootId.toString()} →
          </button>
        </Card>
      )}
    </div>
  );
}
