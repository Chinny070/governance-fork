# Stage 7 Semantic Adjudication Probe — Studio Runbook

**Probe contract:** `contracts/probe/semantic_adjudication_probe.py`
**Commit / SHA / size / ABI:** see the accompanying final report.
**Constructor:** `__init__(self)` — **no arguments** (do not fill any constructor field).

Stage 7 is **not implemented**. This probe only measures live GenVM
semantic-runtime behavior so the production primitive and evidence budget
can be chosen from real data. `contracts/governance_fork.py` is untouched
and must not be called during this runbook.

For **every write**: after Studio finalizes it, open the transaction
detail and record — **Execution Result** (SUCCESS / ERROR), **Consensus
Result** (Accepted / Undetermined), **Rotation Count / rounds**, any
**stderr**, and any **Equivalence Principle Outputs** shown. Then run the
`get_observation` view and paste its full result. Do one step, paste
results, wait for the PASS/FAIL read before the next step.

---

## Phase 0 — deploy & baseline

**Step 0.1 — Deploy.** Schema-load `contracts/probe/semantic_adjudication_probe.py`, deploy with an empty Constructor Inputs panel, `Value (GEN) = 0`. Record deploy tx + contract address. Expect Execution Result `SUCCESS`.

**Step 0.2 — `get_call_count`** (View, no inputs). Expect `0`.

---

## Phase 1 — deterministic prompt construction (no LLM, no cost)

**Step 1.1 — `probe_input_determinism`** (Write). Input `scenario_code = 0`. `Value (GEN) = 0`. Expect `SUCCESS`, return `null`.

**Step 1.2 — `get_observation`** (View). Record `last_principle` (= `input_only`), `last_scenario` (= `mini/faithful`), `last_input_len`, `last_input_fingerprint`, `call_count` (= `1`).

**Step 1.3 — `probe_input_determinism`** again, `scenario_code = 0`. Then `get_observation`. **PASS iff** `last_input_fingerprint` is **identical** to Step 1.2 and `last_input_len` is identical. (Deterministic prompt construction — the property every validator and every retry depends on.)

**Step 1.4 — `probe_input_determinism`**, `scenario_code = 13` (the 49 KB scenario). Then `get_observation`. **PASS iff** `last_input_len` is between ~45000 and ~55000 (the ~49 KB production-candidate budget actually materialised) and `last_scenario` = `scale/49k`.

---

## Phase 2 — what `response_format="json"` actually returns

**Step 2.1 — `probe_raw_json`** (Write). Input `mode = 0`. `Value (GEN) = 0`.

**Step 2.2 — `get_observation`.** Record `last_raw_output` (the stringified value the contract received) and `last_findings` (contains `python_type=<name>` — e.g. `python_type=dict` or `python_type=str`). **This resolves item #5** — whether the pinned runtime hands the contract a `dict` or a parseable string for `response_format="json"`, and whether `strict_eq` over that value reached `Accepted`.

**Step 2.3 — `probe_raw_json`**, `mode = 1` (a JSON object shaped like the real adjudication schema). Then `get_observation`. Record the same fields + Consensus Result.

---

## Phase 3 — MINI semantic correctness (small deterministic evidence)

For each step: Write, `Value (GEN) = 0`, then `get_observation`, then paste.

| Step | Method | `scenario_code` | Scenario | Expected `last_derived_verdict` | Expected `last_parse_ok` |
|---|---|---|---|---|---|
| 3.1 | `probe_non_comparative` | `0` | mini/faithful | `FAITHFUL` | `true` |
| 3.2 | `probe_non_comparative` | `1` | mini/not_faithful | `NOT_FAITHFUL` | `true` |
| 3.3 | `probe_non_comparative` | `2` | mini/unclear | `UNCLEAR_VERDICT` | `true` |
| 3.4 | `probe_non_comparative` | `3` | mini/injection | `NOT_FAITHFUL` (**not** FAITHFUL — injection resisted) | `true` |
| 3.5 | `probe_comparative` | `0` | mini/faithful | `FAITHFUL` | `true` |
| 3.6 | `probe_comparative` | `1` | mini/not_faithful | `NOT_FAITHFUL` | `true` |
| 3.7 | `probe_comparative` | `3` | mini/injection | `NOT_FAITHFUL` | `true` |

For **every** step also record: Consensus Result, Rotation Count, and `last_raw_output` (the model's JSON) + `last_findings` (the parsed per-dimension findings).

**Interpretation notes (not pass/fail on their own — data for the choice):**
- A `PARSE_FAIL:<reason>` in `last_findings` means the model produced output the strict parser rejected — record the reason; it informs whether the schema/criteria need tightening.
- `last_derived_verdict` differing from the "Expected" column is a **finding to report**, not necessarily a probe failure — it may mean the rubric wording needs work, or the model is weak on this axis.
- If Consensus Result is `Undetermined` for a MINI scenario, that is a strong negative signal for that primitive — record it.

---

## Phase 4 — SCALE tests (does ~49 KB actually work?)

Same 6-dimension rubric, deterministic synthetic evidence at increasing size. The "faithful" signal is embedded at the head and tail of the evidence; a capable model at a viable scale should return `FAITHFUL`.

For each step: Write, `Value (GEN) = 0`. **Record: Execution Result, Consensus Result, Rotation Count / number of rounds, `last_input_len` (from `get_observation`), `last_parse_ok`, `last_derived_verdict`, `last_raw_output`, and any cost/gas/time info Studio exposes.**

| Step | Method | `scenario_code` | Evidence size | Expected verdict if viable |
|---|---|---|---|---|
| 4.1 | `probe_non_comparative` | `10` | ~8 KB | `FAITHFUL` |
| 4.2 | `probe_non_comparative` | `11` | ~16 KB | `FAITHFUL` |
| 4.3 | `probe_non_comparative` | `12` | ~32 KB | `FAITHFUL` |
| 4.4 | `probe_non_comparative` | `13` | ~49 KB | `FAITHFUL` **← the critical viability test** |
| 4.5 | `probe_comparative` | `10` | ~8 KB | `FAITHFUL` |
| 4.6 | `probe_comparative` | `11` | ~16 KB | `FAITHFUL` |
| 4.7 | `probe_comparative` | `12` | ~32 KB | `FAITHFUL` |
| 4.8 | `probe_comparative` | `13` | ~49 KB | `FAITHFUL` |

**What we are looking for:** the largest evidence size at which each primitive still (a) executes `SUCCESS`, (b) reaches `Accepted` consensus, (c) produces parser-valid output, (d) yields the correct verdict — with acceptable rotation count and cost. If 49 KB is not viable, this tells us to lower `TOTAL_SEMANTIC_EVIDENCE_BUDGET` before Stage 7 production is written. **Do not assume 49 KB works.**

---

## Phase 5 — Undetermined atomicity (re-confirm zero state on Undetermined)

**Step 5.1 — `get_call_count`.** Record the value — call it **N**.

**Step 5.2 — `probe_undetermined_control`** (Write). Input `mode = 0`. `Value (GEN) = 0`. This asks, under `strict_eq`, for a random integer — which should **not** converge byte-for-byte across validators. Record Consensus Result (expect `Undetermined`) and Execution Result.

**Step 5.3 — `get_call_count`.** **PASS iff** the value is **still N** (unchanged). Document as:
```
state before : call_count = N
transaction  : probe_undetermined_control(0)
consensus    : <Undetermined | Accepted>
state after  : call_count = <N | N+1>
```
If consensus was `Undetermined`, `call_count` **must** be `N` — proving the Undetermined semantic transaction committed **zero state**. This is the property the Stage 7 two-transaction arm/run retry design rests on.

**Step 5.4 / 5.5 — repeat** with `mode = 1` (creative sentence) and `mode = 2` (current time) **only if** `mode = 0` reached `Accepted` (i.e. we failed to induce Undetermined) — we need at least one reproduced Undetermined + its atomicity confirmation.

---

## After the runbook

Paste all recorded results back. From them we will produce the **Stage 7
Semantic Probe Report** covering: chosen primitive (`prompt_non_comparative`
vs `prompt_comparative`), confirmed `response_format="json"` behavior,
viable evidence budget, MINI correctness + injection resistance, and the
Undetermined-atomicity confirmation — which together unblock (with your
approval) the Stage 7 production implementation, still beginning with no
production write until that report is reviewed.
