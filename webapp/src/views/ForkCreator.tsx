import { useState } from "react";
import * as api from "../lib/api";
import { getActiveWriteClient as g } from "../lib/activeClient";
import { BOND_PURPOSE, CLAIM_KINDS, PARENT_KIND } from "../lib/enums";
import { formatGen } from "../lib/format";
import { useTx } from "../lib/useTx";
import { HexChip, Note } from "../components/ui";
import { Guarded } from "../components/Guarded";
import { TxProgress } from "../components/TxProgress";
import { ArrayInput } from "../components/ArrayInput";

interface DeltaRow {
  dimension_name: string;
  parent_value: string;
  fork_value: string;
  claim_kind: string;
}
const emptyDelta = (): DeltaRow => ({
  dimension_name: "",
  parent_value: "",
  fork_value: "",
  claim_kind: CLAIM_KINDS[0],
});

export function ForkCreatorPanel({
  parentKind,
  parentId,
  parentFingerprintHex,
  onCreated,
}: {
  parentKind: "root" | "fork";
  parentId: bigint;
  parentFingerprintHex: string;
  onCreated: (forkId: bigint) => void;
}) {
  const tx = useTx();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [reasoning, setReasoning] = useState("");
  const [pKeys, setPKeys] = useState<string[]>([]);
  const [pVals, setPVals] = useState<string[]>([]);
  const [deltas, setDeltas] = useState<DeltaRow[]>([emptyDelta()]);

  const parentKindConst =
    parentKind === "root" ? PARENT_KIND.ROOT : PARENT_KIND.FORK;
  const live = deltas.filter((d) => d.dimension_name.trim());
  const canSubmit = title.trim() && summary.trim() && live.length > 0;

  const setD = (i: number, patch: Partial<DeltaRow>) =>
    setDeltas((xs) => xs.map((x, idx) => (idx === i ? { ...x, ...patch } : x)));

  const submit = async () => {
    const c = g();
    const { bondId } = await api.lockBond(c, BOND_PURPOSE.FORK_CREATION);
    const { forkId, write } = await api.createFork(c, bondId, {
      parentId,
      parentKind: parentKindConst,
      parentFingerprintHex,
      deltaDimensionNames: live.map((d) => d.dimension_name.trim()),
      deltaParentValues: live.map((d) => d.parent_value.trim()),
      deltaForkValues: live.map((d) => d.fork_value.trim()),
      deltaClaimKinds: live.map((d) => d.claim_kind),
      bodyTitle: title.trim(),
      bodySummary: summary.trim(),
      bodyParamKeys: pKeys.filter((k) => k.trim()),
      bodyParamValues: pVals.slice(0, pKeys.filter((k) => k.trim()).length),
      bodyReasoning: reasoning.trim(),
    });
    (submit as unknown as { _id?: bigint })._id = forkId;
    return write;
  };

  return (
    <div>
      <p className="muted tiny" style={{ marginTop: 0 }}>
        A fork keeps the parent's intent and declares exactly what it changes. It
        costs a {formatGen(api.BOND_AMOUNT_WEI)} FORK_CREATION bond, then runs the
        same evidence → adjudication → finality pipeline.
      </p>
      <div className="tiny faint mono" style={{ marginBottom: 12 }}>
        parent: {parentKind} #{parentId.toString()} · fingerprint{" "}
        <HexChip hex={parentFingerprintHex} label="parent" />
      </div>

      {!open ? (
        <button className="coral" onClick={() => setOpen(true)}>
          New fork of this {parentKind}
        </button>
      ) : (
        <div className="stack">
          <div className="field">
            <label>Fork title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="field">
            <label>Summary</label>
            <textarea value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>
          <div className="field">
            <label>Reasoning — why this preserves the intent</label>
            <textarea value={reasoning} onChange={(e) => setReasoning(e.target.value)} />
          </div>
          <div className="grid-2">
            <ArrayInput label="Parameter keys" values={pKeys} onChange={setPKeys} max={32} />
            <ArrayInput label="Parameter values" values={pVals} onChange={setPVals} max={32} />
          </div>

          <p className="eyebrow" style={{ margin: "4px 0" }}>
            Declared delta vs parent
          </p>
          {deltas.map((d, i) => (
            <div className="panel-inset" key={i}>
              <div className="grid-2">
                <div className="field" style={{ margin: 0 }}>
                  <label>Dimension name (≤ 64)</label>
                  <input
                    value={d.dimension_name}
                    maxLength={64}
                    onChange={(e) => setD(i, { dimension_name: e.target.value })}
                  />
                </div>
                <div className="field" style={{ margin: 0 }}>
                  <label>Claim kind</label>
                  <select
                    value={d.claim_kind}
                    onChange={(e) => setD(i, { claim_kind: e.target.value })}
                  >
                    {CLAIM_KINDS.map((k) => (
                      <option key={k}>{k}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid-2" style={{ marginTop: 8 }}>
                <div className="field" style={{ margin: 0 }}>
                  <label>Parent value</label>
                  <input
                    value={d.parent_value}
                    maxLength={256}
                    onChange={(e) => setD(i, { parent_value: e.target.value })}
                  />
                </div>
                <div className="field" style={{ margin: 0 }}>
                  <label>Fork value</label>
                  <input
                    value={d.fork_value}
                    maxLength={256}
                    onChange={(e) => setD(i, { fork_value: e.target.value })}
                  />
                </div>
              </div>
              <button
                type="button"
                className="small ghost"
                style={{ marginTop: 8 }}
                onClick={() => setDeltas((xs) => xs.filter((_, idx) => idx !== i))}
                disabled={deltas.length <= 1}
              >
                Remove delta
              </button>
            </div>
          ))}
          <button
            type="button"
            className="small"
            onClick={() => setDeltas((xs) => [...xs, emptyDelta()])}
            disabled={deltas.length >= 16}
          >
            + Add delta entry
          </button>

          <Note tone="coral">
            Bond: {formatGen(api.BOND_AMOUNT_WEI)} — <code>lock_bond("FORK_CREATION")</code>{" "}
            then <code>create_fork(bond_id, …)</code>.
          </Note>

          <Guarded>
            <div className="row">
              <button
                className="coral"
                disabled={tx.busy || !canSubmit}
                onClick={() =>
                  void tx.run(submit, {
                    afterConfirm: () => {
                      const id = (submit as unknown as { _id?: bigint })._id;
                      if (id) onCreated(id);
                    },
                  })
                }
              >
                Lock bond & create fork
              </button>
              <button className="ghost" onClick={() => setOpen(false)}>
                Cancel
              </button>
            </div>
          </Guarded>

          <TxProgress tx={tx} />
        </div>
      )}
    </div>
  );
}
