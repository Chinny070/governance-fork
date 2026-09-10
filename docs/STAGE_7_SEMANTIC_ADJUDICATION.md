# Stage 7 — Semantic Adjudication (as built + live preflight)

Implemented in `contracts/governance_fork.py` at commit `e10c63f`
(`feat: implement Stage 7 semantic adjudication`).
`governance_fork.py` SHA-256 `153bd62be9c3b23d76450d79f074161349d6c54a4083b9818d24226ed0f9a31c`
— 141688 bytes, 3302 newlines, ABI 32 (14 write + 16 view + 2 admin).

Stage 7 adds semantic adjudication on top of the Stage 6b sealed-evidence
lifecycle. It does **not** implement challenge resolution, finalization,
or any GEN economics — those are Stage 8+. `challenge_verdict`,
`finalize`, `settle_bond` and the challenge/bond views remain
placeholders.

---

## 1. Consensus primitive (chosen from the isolated live probe)

```
gl.eq_principle.prompt_comparative(fn, _ADJ_PRINCIPLE)
  where fn == lambda: gl.nondet.exec_prompt(prompt, response_format="json")
```

This is the **only** nondeterministic call in the whole stage (one site,
in `run_adjudication`, no `try/except` around it).

- `response_format="json"` returns a Python `dict` on the pinned runtime.
- `_ADJ_PRINCIPLE` defines agreement at the **finding level**:
  identical `schema_version`, identical `case_id`, same set of dimension
  names, and identical `finding` value for every dimension. Rationale
  wording and `evidence_ids` ordering never cause disagreement.
- `TOTAL_SEMANTIC_EVIDENCE_BUDGET = 16384` (one `MAX_EVIDENCE_SLICE`). Per
  eligible record the excerpt cap is `min(16384, 16384 // n_eligible)`;
  above the cap a deterministic head/tail excerpt (3/5 split, fixed
  marker) is used. `<<<` / `>>>` inside untrusted evidence text are
  neutralised to `(EVID-OPEN)` / `(EVID-CLOSE)`; subject fields are
  newline-flattened; only the message's own delimiter lines are real.

## 2. Two-transaction flow

| tx | determinism | who | effect |
|---|---|---|---|
| `adjudicate(case_id)` | deterministic, **always commits** | case owner only (`_case_owner`, same gate as `close_evidence`) | `CASE_CASE_FROZEN → CASE_ADJUDICATING`, `retry_count → 1`, root `ENVELOPE_EVIDENCE_OPEN → ENVELOPE_ADJUDICATING` / fork `FORK_EVIDENCE_OPEN → FORK_ADJUDICATING`. Re-arm: `retry_count += 1` while `< MAX_RETRIES_PER_CASE`; the arm past the budget → `CASE_UNDETERMINED_TERMINAL` + root `ENVELOPE_UNCLEAR` / fork `FORK_FINALIZED_UNCLEAR`. |
| `run_adjudication(case_id)` | the single nondet step | permissionless (progress op, like `fetch_evidence` / `seal_evidence`); **not** paused-gated | one `prompt_comparative` call; strict-parse; deterministic aggregation; persist `VerdictRecord`. Undetermined **or** strict-parse rejection → `raise` → revert → **zero state committed** → owner may re-arm. |

There is no wall-clock cooldown: the pinned runtime exposes no block-time
source (every timestamp field is `u256(0)`). Retry pacing is the owner's
explicit manual decision via `adjudicate`.

## 3. Root-finality correction

A successful **FAITHFUL** initial verdict does **not** set
`ENVELOPE_FAITHFUL`. It records the `VerdictRecord`, sets
`case.state = CASE_SUCCESS`, and leaves `envelope_status =
ENVELOPE_ADJUDICATING`. `create_fork` still requires exactly
`ENVELOPE_FAITHFUL`, so the root stays non-forkable until Stage 8
`finalize()` clears the challenge/finality boundary. No orphanable
descendants.

`NOT_FAITHFUL` and `UNCLEAR_VERDICT` semantic verdicts also leave the
envelope at `ENVELOPE_ADJUDICATING` (they are challengeable in Stage 8);
forks move to `FORK_VERDICT_PROPOSED`. The only **immediate** terminals
are deterministic and unchallengeable: no-eligible-evidence `INVALID` →
`ENVELOPE_REJECTED` / `FORK_FINALIZED_INVALID`, and retry-budget
exhaustion → `ENVELOPE_UNCLEAR` / `FORK_FINALIZED_UNCLEAR`.

## 4. Strict parser + deterministic aggregation

`_parse_adjudication_output` never raises; it returns `(ok, ordered, reason)`.
Rejects: bad JSON, wrong top-level key set, `schema_version` / `case_id`
mismatch, wrong dimension count, unknown / duplicate dimension, bad
`finding` enum, `evidence_ids` not a subset of the eligible frozen set or
with duplicates, a decisive (`SATISFIED` / `NOT_SATISFIED`) finding citing
no evidence, rationale over `MAX_DIM_RATIONALE_LEN` (600) or containing a
newline, any extra key.

- ROOT (6 dims): core = {OBJECTIVE_REPRESENTATION, SCOPE_FIDELITY,
  CONSTRAINT_COMPLETENESS, DIMENSION_CLASSIFICATION}; support =
  {EVIDENCE_SUPPORT, SOURCE_AUTHORITY}. Any core `NOT_SATISFIED` →
  `NOT_FAITHFUL`; else any support `NOT_SATISFIED` → `UNCLEAR_VERDICT`;
  else any `UNCLEAR` → `UNCLEAR_VERDICT`; else `FAITHFUL`.
- FORK (7 dims): hard = {UNDECLARED_SEMANTIC_CHANGE}; core =
  {INTENT_PRESERVATION, DELTA_ACCURACY, INTERNAL_CONSISTENCY}; support =
  {EVIDENCE_SUPPORT, SOURCE_AUTHORITY, TEMPORAL_RELEVANCE}. hard or core
  `NOT_SATISFIED` → `NOT_FAITHFUL`; else support `NOT_SATISFIED` →
  `UNCLEAR_VERDICT`; else any `UNCLEAR` → `UNCLEAR_VERDICT`; else
  `FAITHFUL`.

`_rederive_eligible_ids` replays the seal REQUIRED / NON-BLOCKING lane
filter and cross-checks `_evidence_set_fingerprint` against the sealed
`Case.evidence_set_fingerprint`; a mismatch is a hard abort, not an
`INVALID` verdict.

`VerdictRecord` binds `verdict_id`, `case_fingerprint`,
`prompt_fingerprint`, `adjudication_dimensions_version`, `reasoning_hash`,
`evidence_refs`, canonical `reason_codes`, `replaced_by = 0`.

---

## 5. Live CLI preflight

- **CLI** genlayer `0.39.2` · **network** `studionet` (Genlayer Studio
  Network) · **chain id** `61999` · **RPC** `https://studio.genlayer.com/api`
- **Deployer** `continuum` = `0x13ae0c28d06716d2908b5d84c3c0c3d815378f3b`
  (safe throwaway CLI account; **not** the operator wallet; production
  `0x644C750e07b321900550FE426AD2C8E20556eaA7` untouched)
- **Deploy tx** `0x1753c9997df979b5b81f131a52df4dbb0a8a193cdc7c4d98ecd195352b26bd14`
- **Stage 7 CLI test contract** `0xC4b885bC2466eE634BfF6A2961061E4d2Baa04F9`
- Deploy consensus `MAJORITY_AGREE` / `ACCEPTED`, 1 round; leader + 3
  validators genuine `SUCCESS` (empty stderr), 2 benign quorum-idle;
  `get_constants().treasury_addr` == deployer; live ABI = 32
  (14 write + 16 view + 2 admin), `ctor: { params: [] }`.

### Stage 6b regression (new contract)

DAO 1 `Arbitrum DAO`; roots 2 & 3 import → envelope → close → **real
`gl.nondet.web.render`** of `https://docs.arbitrum.foundation/dao-constitution`
(~11 KB frozen, `content_fingerprint 0x6d397577…`, deterministic across
both fetches) → seal. Every step `SUCCESS` + `MAJORITY_AGREE`, 1 round.
Sealed cases carry populated `membership_fingerprint`,
`retrieval_disposition_fingerprint`, `evidence_set_fingerprint`,
`case_fingerprint`; `root.web_content_fingerprint` derived from the
matching evidence. Identical behaviour to the Stage 6b reference.

### Stage 7

| case | envelope vs evidence | `run_adjudication` consensus | verdict | envelope after |
|---|---|---|---|---|
| **1** | proposal title ("ARB Staking…") vs objective ("Ratify the Constitution") — internally inconsistent / genuinely ambiguous | `MAJORITY_DISAGREE`, **4 rounds** (rotations exhausted) → Undetermined | none | stays `ENVELOPE_ADJUDICATING`; **zero state** (`verdict_id 0`, no `VerdictRecord`, `case_fingerprint` unchanged) |
| **2** | coherent, accurate Constitution-adoption envelope | `MAJORITY_AGREE` / `ACCEPTED`, **3 rounds**; all exec `SUCCESS` | `FAITHFUL` (6/6 `SATISFIED`) → `verdict_id 1` | stays `ENVELOPE_ADJUDICATING` (**not** `ENVELOPE_FAITHFUL`) |
| **3** | blatant contradiction ("abolish token voting, install one unaccountable administrator") | `MAJORITY_AGREE` / `ACCEPTED`, **1 round**; all exec `SUCCESS` | `NOT_FAITHFUL` (5 core/support `NOT_SATISFIED`, SOURCE_AUTHORITY `SATISFIED`) → `verdict_id 2` | stays `ENVELOPE_ADJUDICATING` |

- **Arm** (case 2 shown): `adjudicate` → `CASE_ADJUDICATING`,
  `retry_count 1`, `verdict_id 0`, root `ENVELOPE_ADJUDICATING`,
  `case_fingerprint` unchanged; `get_verdict` on an unassigned id errors.
- **Nested storage — PROVEN.** `get_verdict(1)` and `get_verdict(2)` each
  return `dimensions[]` (6 `DimensionFinding`, each name once, canonical
  order) with the nested `evidence_ids: [<eligible id>]` `DynArray[u256]`
  read back intact. No fix required.
- **Verdict integrity** (verdicts 1 & 2): `verdict_id != 0`; correct
  `case_id` / `target_id` / `target_kind`; `case_fingerprint` equals the
  frozen `Case.case_fingerprint`; `prompt_fingerprint` populated;
  `adjudication_dimensions_version = 1`; findings in
  {SATISFIED, NOT_SATISFIED, UNCLEAR}; every cited `evidence_id` is an
  eligible frozen id; rationales ≤ 600, single-line; `evidence_refs`
  correct; `reason_codes` canonical (`VERDICT:<v>` + each non-satisfied
  dim); `reasoning_hash` populated; `replaced_by = 0`; the deterministic
  verdict matches the dimension findings.
- **Root finality / `create_fork` gate.** `create_fork` against root 2
  (FAITHFUL verdict, `ENVELOPE_ADJUDICATING`) **and** root 3
  (`NOT_FAITHFUL`) both revert `root intent envelope not finalized
  faithful`; `list_forks_of_root` stays empty; root and case state
  unchanged.
- **Undetermined atomicity + retry.** Case 1's Undetermined committed
  nothing. Re-arm via `adjudicate`: `retry_count 1 → 2 → 3` (state stays
  `CASE_ADJUDICATING`); the 4th `adjudicate` → `CASE_UNDETERMINED_TERMINAL`
  + root `ENVELOPE_UNCLEAR`, `case_fingerprint` unchanged. Terminal is
  sticky: `run_adjudication` → `case not armed for adjudication`;
  `adjudicate` → `case not in an armable state`.

### Runtime fixes made during preflight

None. Zero runtime defects. The deployed bytes are the committed
`e10c63f` source; no redeployment was required.

---

## 6. Known characteristics / limitations

- **Genuinely ambiguous envelopes tend toward `UNCLEAR` terminal, not a
  forced verdict.** Finding-level consensus (`_ADJ_PRINCIPLE`) means a
  subject on which independent validator LLM runs legitimately land on
  different findings (case 1) will not converge; after
  `MAX_RETRIES_PER_CASE` owner re-arms it becomes
  `CASE_UNDETERMINED_TERMINAL` / `ENVELOPE_UNCLEAR`. Clear subjects
  (faithful or not) converge in 1–3 rounds. This is the intended
  contract of "if the validators cannot agree on the findings, there is
  no verdict."
- Semantic consensus can cost multiple rotations even for clear-cut
  faithful cases (case 2 needed 3 of 4). Each `run_adjudication` attempt
  is a real multi-validator LLM transaction.
- No block-time source on the pinned runtime → `adjudicate` retry pacing
  is an owner gate, not a cooldown; all `created_at` / `last_attempt_at`
  are `0`.
- Stage 8 (`challenge_verdict`, `finalize`, `settle_bond`, GEN bond
  economics) is not implemented.
