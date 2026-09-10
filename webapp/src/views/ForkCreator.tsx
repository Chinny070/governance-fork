import { useState } from "react";
import * as api from "../lib/api";
import { getActiveWriteClient as g } from "../lib/activeClient";
import { BOND_PURPOSE, CLAIM_KINDS, PARENT_KIND } from "../lib/enums";
import { formatGen } from "../lib/format";
import { useTx } from "../lib/useTx";
import { Card, HexChip, Notice } from "../components/ui";
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
  const [paramKeys, setParamKeys] = useState<string[]>([]);
  const [paramValues, setParamValues] = useState<string[]>([]);
  const [deltas, setDeltas] = useState<DeltaRow[]>([emptyDelta()]);

  const parentKindConst =
    parentKind === "root" ? PARENT_KIND.ROOT : PARENT_KIND.FORK;

  const liveDeltas = deltas.filter((d) => d.dimension_name.trim());
  const canSubmit =
    title.trim().length > 0 &&
    summary.trim().length > 0 &&
    liveDeltas.length > 0;

  const submit = async () => {
    const c = g();
    const { bondId } = await api.lockBond(c, BOND_PURPOSE.FORK_CREATION);
    const { forkId, write } = await api.createFork(c, bondId, {
      parentId,
      parentKind: parentKindConst,
      parentFingerprintHex,
      deltaDimensionNames: liveDeltas.map((d) => d.dimension_name.trim()),
      deltaParentValues: liveDeltas.map((d) => d.parent_value.trim()),
      deltaForkValues: liveDeltas.map((d) => d.fork_value.trim()),
      deltaClaimKinds: liveDeltas.map((d) => d.claim_kind),
      bodyTitle: title.trim(),
      bodySummary: summary.trim(),
      bodyParamKeys: paramKeys.filter((_, i) => paramKeys[i]?.trim()),
      bodyParamValues: paramValues.slice(0, paramKeys.length),
      bodyReasoning: reasoning.trim(),
    });
    // stash for the afterConfirm navigation
    (submit as any)._newForkId = forkId;
    return write;
  };

  return (
    <Card title="Create a semantic-descendant fork">
      <p className="muted tiny" style={{ marginTop: 0 }}>
        "Don't vote YES or NO. Change the proposal." A fork keeps the parent's
        intent and declares exactly what it changes. It costs a 0.1 GEN
        FORK_CREATION bond and then goes through the same evidence → adjudication
        → finality pipeline.
      </p>

      <div className="tiny faint" style={{ marginBottom: 10 }}>
        parent: {parentKind} #{parentId.toString()} · fingerprint{" "}
        <HexChip hex={parentFingerprintHex} label="parent" />
      </div>

      {!open ? (
        <button className="primary" onClick={() => setOpen(true)}>
          New fork of this {parentKind}
        </button>
      ) : (
        <div className="stack">
          <div>
            <label>Fork title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label>Summary</label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
            />
          </div>
          <div>
            <label>Reasoning (why this change preserves the intent)</label>
            <textarea
              value={reasoning}
              onChange={(e) => setReasoning(e.target.value)}
            />
          </div>

          <div className="grid2">
            <ArrayInput
              label="Structured parameter keys"
              values={paramKeys}
              onChange={setParamKeys}
              max={32}
            />
            <ArrayInput
              label="Structured parameter values"
              values={paramValues}
              onChange={setParamValues}
              max={32}
            />
          </div>

          <div>
            <label>Declared delta vs parent</label>
            {deltas.map((d, i) => (
              <div
                key={i}
                className="card"
                style={{ margin: "0 0 8px", padding: 10, background: "var(--bg-sunken)" }}
              >
                <div className="grid2">
                  <div>
                    <label>Dimension name</label>
                    <input
                      value={d.dimension_name}
                      onChange={(e) =>
                        setDeltas((xs) =>
                          xs.map((x, idx) =>
                            idx === i
                              ? { ...x, dimension_name: e.target.value }
                              : x,
                          ),
                        )
                      }
                    />
                  </div>
                  <div>
                    <label>Claim kind</label>
                    <select
                      value={d.claim_kind}
                      onChange={(e) =>
                        setDeltas((xs) =>
                          xs.map((x, idx) =>
                            idx === i
                              ? { ...x, claim_kind: e.target.value }
                              : x,
                          ),
                        )
                      }
                    >
                      {CLAIM_KINDS.map((k) => (
                        <option key={k}>{k}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="grid2" style={{ marginTop: 8 }}>
                  <div>
                    <label>Parent value</label>
                    <input
                      value={d.parent_value}
                      onChange={(e) =>
                        setDeltas((xs) =>
                          xs.map((x, idx) =>
                            idx === i
                              ? { ...x, parent_value: e.target.value }
                              : x,
                          ),
                        )
                      }
                    />
                  </div>
                  <div>
                    <label>Fork value</label>
                    <input
                      value={d.fork_value}
                      onChange={(e) =>
                        setDeltas((xs) =>
                          xs.map((x, idx) =>
                            idx === i
                              ? { ...x, fork_value: e.target.value }
                              : x,
                          ),
                        )
                      }
                    />
                  </div>
                </div>
                <button
                  type="button"
                  className="small ghost"
                  style={{ marginTop: 8 }}
                  onClick={() =>
                    setDeltas((xs) => xs.filter((_, idx) => idx !== i))
                  }
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
          </div>

          <Notice tone="info">
            Bond required: {formatGen(api.BOND_AMOUNT_WEI)}. Locked with{" "}
            <code>lock_bond("FORK_CREATION")</code>, then consumed by{" "}
            <code>create_fork</code>.
          </Notice>

          <Guarded>
            <div className="row">
              <button
                className="primary"
                disabled={tx.busy || !canSubmit}
                onClick={() =>
                  tx.run(submit, {
                    afterConfirm: () => {
                      const id = (submit as any)._newForkId as bigint | undefined;
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
    </Card>
  );
}
