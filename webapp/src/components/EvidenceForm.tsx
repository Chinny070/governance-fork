import { EVIDENCE_CLASSES, RENDER_PROFILES } from "../lib/enums";

export interface EvidenceRow {
  url: string;
  evidenceClass: string;
  relevanceClaim: string;
  authorityClaim: string;
  temporalMarker: string;
  renderProfile: string;
}

export function emptyEvidenceRow(): EvidenceRow {
  return {
    url: "",
    evidenceClass: EVIDENCE_CLASSES[0],
    relevanceClaim: "",
    authorityClaim: "",
    temporalMarker: "",
    renderProfile: RENDER_PROFILES[0],
  };
}

export function evidenceRowsToArrays(rows: EvidenceRow[]) {
  const live = rows.filter((r) => r.url.trim());
  return {
    evidenceUrls: live.map((r) => r.url.trim()),
    evidenceClasses: live.map((r) => r.evidenceClass),
    relevanceClaims: live.map((r) => r.relevanceClaim.trim()),
    authorityClaims: live.map((r) => r.authorityClaim.trim()),
    temporalMarkers: live.map((r) => r.temporalMarker.trim()),
    renderProfiles: live.map((r) => r.renderProfile),
  };
}

interface Props {
  rows: EvidenceRow[];
  onChange: (rows: EvidenceRow[]) => void;
  max?: number;
}

export function EvidenceForm({ rows, onChange, max = 8 }: Props) {
  const set = (i: number, patch: Partial<EvidenceRow>) => {
    const next = rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r));
    onChange(next);
  };
  const add = () => onChange([...rows, emptyEvidenceRow()]);
  const remove = (i: number) => onChange(rows.filter((_, idx) => idx !== i));

  return (
    <div className="stack" style={{ gap: 10 }}>
      {rows.map((r, i) => (
        <div key={i} className="panel-inset">
          <div className="between" style={{ alignItems: "center" }}>
            <strong className="mono tiny">SOURCE {String(i + 1).padStart(2, "0")}</strong>
            <button
              type="button"
              className="small ghost"
              onClick={() => remove(i)}
              disabled={rows.length <= 1}
            >
              Remove
            </button>
          </div>
          <div className="field" style={{ marginTop: 8 }}>
            <label>Source URL — a real, renderable page</label>
            <input
              value={r.url}
              placeholder="https://…"
              onChange={(e) => set(i, { url: e.target.value })}
            />
          </div>
          <div className="grid-2" style={{ marginTop: 8 }}>
            <div>
              <label>Evidence class</label>
              <select
                value={r.evidenceClass}
                onChange={(e) => set(i, { evidenceClass: e.target.value })}
              >
                {EVIDENCE_CLASSES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>Render profile</label>
              <select
                value={r.renderProfile}
                onChange={(e) => set(i, { renderProfile: e.target.value })}
              >
                {RENDER_PROFILES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div style={{ marginTop: 8 }}>
            <label>Relevance claim</label>
            <input
              value={r.relevanceClaim}
              placeholder="Why this source is relevant to the intent"
              onChange={(e) => set(i, { relevanceClaim: e.target.value })}
            />
          </div>
          <div className="grid-2" style={{ marginTop: 8 }}>
            <div>
              <label>Authority claim</label>
              <input
                value={r.authorityClaim}
                placeholder="e.g. official forum, DAO docs"
                onChange={(e) => set(i, { authorityClaim: e.target.value })}
              />
            </div>
            <div>
              <label>Temporal marker</label>
              <input
                value={r.temporalMarker}
                placeholder="e.g. 2026-Q1, current"
                onChange={(e) => set(i, { temporalMarker: e.target.value })}
              />
            </div>
          </div>
        </div>
      ))}
      <div>
        <button
          type="button"
          className="small"
          onClick={add}
          disabled={rows.length >= max}
        >
          + Add evidence ({rows.length}/{max})
        </button>
      </div>
    </div>
  );
}
