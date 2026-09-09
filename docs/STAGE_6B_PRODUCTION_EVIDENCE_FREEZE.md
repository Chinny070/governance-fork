# Stage 6b — Production Evidence Retrieval, Content Fingerprinting & Atomic Evidence Freeze

> **Correction applied after review of commit `28c42c1`.** The original Stage 6b design made ALL evidence — creator and community alike — a symmetric seal blocker, and enforced a seal-time total-content cap (`MAX_FROZEN_CONTENT_PER_CASE`). Both created a real griefing/bricking risk: a single unavailable community URL, or an ordinary sequence of successful fetches that happened to cross the cap, could permanently prevent a case from ever sealing, with `abort_case` as the only (destructive-feeling) way out. This correction makes community evidence **non-blocking** at seal (§4, §11, §18) and **removes the seal-blocking content cap entirely** (§11a), while keeping creator/root-envelope evidence strictly required and every submitted record fully auditable, never deleted or rewritten. Sections below marked **[CORRECTED]** reflect this fix; the rest of the document (render-only retrieval, profiles, retrieval-status model, `WEBPAGE_LOAD_FAILED`/`Undetermined` handling, per-evidence bound, stored-content immutability, lifecycle mechanics, authorization, pause behavior) is unchanged and remains architecturally approved.

**Scope.** Implements `contracts/governance_fork.py`'s first production web-evidence pathway: `close_evidence` → `fetch_evidence` → `seal_evidence`, plus the `abort_case` escape valve. Uses `gl.nondet.web.render(...)` wrapped in `gl.eq_principle.strict_eq(...)` — the exact pattern Stage 6a validated live, per the current official Fetch Web Content docs, re-checked immediately before this stage began (no material change since Stage 6a).

**Explicitly not in scope.** Semantic proposal-fidelity adjudication, Intent Envelope semantic adjudication, verdict generation, challenges, finalization, GEN bonds, payouts, frontend, production deployment.

## 1. Stage 6a findings driving this design

- 4/5 source classes reached `REPEATABLE_PASS`; `SOURCE_3_FORUM` remained `UNSTABLE` under both tested configurations. **Conclusion: not every source can be guaranteed retrievable; the architecture must treat retrieval failure as a first-class, non-catastrophic outcome, not an edge case.**
- `wait_after_loaded` mattered decisively for two of five sources (Snapshot, Treasury) and did **not** save the sixth attempt (Forum diagnostic went `Undetermined`). **Conclusion: wait is necessary but not sufficient — no configuration can be assumed universally safe.**
- Both observed failure paths (`Undetermined` consensus, and an agreed-`Accepted` consensus on a raised `WEBPAGE_LOAD_FAILED` exception) resulted in **zero committed state**, confirmed via direct `get_probe_count()` re-reads. **Conclusion: a failing `fetch_evidence` transaction can safely be trusted to leave no partial state — this is the atomicity foundation the whole freeze lifecycle depends on.**
- `hashlib.sha256` is LIVE VERIFIED at runtime. **Conclusion: `content_fingerprint = SHA-256(bounded_text)` is safe to use as designed, no fallback needed.**
- No render call in Stage 6a exceeded ~79% of the 16,384-char per-item bound. **Conclusion: `MAX_EVIDENCE_SLICE` stays at 16,384; a case-level total cap is new and separately justified (§11).**

## 2. Production retrieval API — reverified before implementation

Re-checked `https://docs.genlayer.com/developers/intelligent-contracts/examples/fetch-web-content` immediately before writing `fetch_evidence`. No material change from Stage 6a's last check. Confirmed: `gl.nondet.web.render(url, mode)`, `mode ∈ {"text", "html"}`, optional `wait_after_loaded="5s"`-style duration string, `gl.eq_principle.strict_eq(leader_fn)` wrapping. Production uses `mode="text"` exclusively; `gl.nondet.web.get(...)` is never called (grep-enforced, `tests/stage_2_checks.py::check_no_prohibited_calls`).

## 3. Render-only, no arbitrary parameters

`fetch_evidence` never accepts caller-supplied `mode`, wait duration, retry count, or renderer options. Two contract-controlled leader functions exist:

```python
def _fetch_standard() -> str:
    return gl.nondet.web.render(url, mode="text")

def _fetch_dynamic() -> str:
    return gl.nondet.web.render(url, mode="text", wait_after_loaded=DYNAMIC_WAIT_SECONDS)
```

`DYNAMIC_WAIT_SECONDS = "5s"` — a fixed module constant, matching Stage 6a's tested value exactly. The submitter selects which leader function runs via `render_profile` (§5), never the duration itself.

## 4. Option A vs Option B — explicit comparison (required)

**Option A — fetch all evidence in one atomic transaction.** Rejected. Stage 6a observed that even a *single* `render()` call inside `strict_eq` can cost 3 validator rotations before `Undetermined`. Scaling to up to `MAX_EVIDENCE_PER_CASE` (16) sequential nondet calls inside one leader function multiplies that risk combinatorially, and a single failing item would discard the entire transaction's accumulated work — the worst possible outcome given what was already observed live. No evidence supports nested/sequential multi-render transactions being schema-safe or execution-safe at this scale; introducing it would be speculative.

**Option B — Close → Fetch → Seal, one evidence item per transaction.** Adopted. Isolates every nondeterministic render to its own transaction, matches Stage 6a's actual observed granularity exactly (one render per transaction, in every one of the 12 live transactions), and turns partial failure into a legible, independently retriable per-item state instead of an opaque whole-case failure.

## 5. Render profile

Two bounded, contract-controlled values only:

```python
RENDER_PROFILE_STANDARD = "STANDARD"   # gl.nondet.web.render(url, mode="text")
RENDER_PROFILE_DYNAMIC  = "DYNAMIC"    # + wait_after_loaded="5s"
```

**Selected by the evidence submitter**, at submission time (`submit_root_envelope` / `submit_fork_evidence`, both extended with a new `render_profiles: DynArray[str]` parallel array), validated against `_ALLOWED_RENDER_PROFILES`, stored on `Evidence.render_profile`, **immutable thereafter** (never touched by `fetch_evidence` or `seal_evidence`; verified by test `test_profile_immutable_after_close`).

**Why the submitter, not the fetcher or a host-specific hardcode.** The submitter is the one who identified the URL and, in practice, is the person most likely to know whether it's JS-heavy — matching the architecture's own preferred V1 model. Host-specific hardcoding (`snapshot.org → wait`) was explicitly rejected: it would tie the contract to specific domains and break the moment a new DAO uses a different Snapshot-like platform. Evidence class (`evidence_class`) and render profile are kept fully orthogonal — an `OFFICIAL_GOVERNANCE` evidence item may be `STANDARD` or `DYNAMIC` depending on the actual page, never inferred from its class (verified by test `test_evidence_class_independent_of_profile`).

## 6. Retrieval status — deterministic and committable only

```python
RETRIEVAL_NOT_FETCHED = "NOT_FETCHED"       # initial state
RETRIEVAL_FETCHED     = "FETCHED"           # committed, len >= MIN_USEFUL_CONTENT_LEN
RETRIEVAL_UNUSABLE_SHORT = "UNUSABLE_SHORT" # committed, len < MIN_USEFUL_CONTENT_LEN
```

**There is deliberately no `UNAVAILABLE` committed status.** A render failure — whether `WEBPAGE_LOAD_FAILED`, `Undetermined`, or any other cause — simply fails the whole `fetch_evidence` transaction; nothing commits, and `retrieval_status` stays `RETRIEVAL_NOT_FETCHED` indefinitely until a retry succeeds or the case is aborted. This directly reflects the two live-observed failure paths (§1) and, critically, **avoids introducing any speculative exception-catching** (§7).

## 7. `WEBPAGE_LOAD_FAILED` — investigated, deliberately not caught

Per this stage's explicit instruction not to guess: whether a production contract can safely catch a `NondetException` (with `causes: ['WEBPAGE_LOAD_FAILED']`) inside a write method and convert it into a committed deterministic outcome was **not verified live** — Stage 6a's probe deliberately did not test exception-catching around the nondet call (a documented Phase A design choice), and no other source in this project has verified it either.

**Decision: do not introduce it.** `fetch_evidence` contains no `try`/`except` around the `strict_eq` call (verified structurally by `tests/test_stage_6b.py::test_no_try_except_around_render_call`, an AST-level check mirroring the Stage 6a probe's own check). A `WEBPAGE_LOAD_FAILED` failure — exactly like Stage 6a's negative control — simply fails the transaction. The evidence stays `RETRIEVAL_NOT_FETCHED` and is retriable by any caller at any later time. This is not a workaround; it is the conservative default until a future stage explicitly live-verifies safe exception-catching (a genuinely separate research question, not assumed here).

## 8. `Undetermined` consensus — structurally safe by design

Stage 6a proved a render transaction can reach `Undetermined` and commit no state (SOURCE_3's diagnostic, confirmed via `get_probe_count()`). `fetch_evidence`'s structure requires no additional defensive code for this: since every write to `self.evidence[evidence_id]` happens only after the `strict_eq` call returns successfully, an `Undetermined` transaction — which never returns — cannot produce a partial write. No orphan evidence, no double-incremented counters, no partially-fingerprinted content is possible by construction, not by a runtime check. This is the same "validate everything before any storage write" discipline every prior stage (3–5) already followed.

## 9. Empty / unusable render — deterministic minimum-content gate

```python
MIN_USEFUL_CONTENT_LEN = 32
```

**Rationale.** Stage 6a's actual observed failures were literally 0 characters (both `SOURCE_3` and `SOURCE_5` primary attempts). 32 characters is shorter than nearly any real sentence fragment — it separates "nothing rendered" from "something rendered" without risking rejection of legitimately terse governance evidence. **This is a length check only.** Stage 6b makes no semantic usefulness judgment — "rendered text contains fewer than 32 characters" is exactly the bounded deterministic fact this stage is permitted to compute; "this text contains the actual proposal" is Stage 7's job, not this stage's.

Content at or above the threshold commits `RETRIEVAL_FETCHED`; below it commits `RETRIEVAL_UNUSABLE_SHORT`. Both are committed, terminal, auditable outcomes — never silently dropped, never treated as a retrieval failure.

## 10. Per-evidence content bound — retained at 16,384

`MAX_EVIDENCE_SLICE = 16384` unchanged from Stage 2. Stage 6a's largest single observed source (`SOURCE_2_TALLY`) reached 12,955 characters — 79.1% of this bound — without truncation. No evidence justifies changing it. `fetch_evidence` slices with `content[:MAX_EVIDENCE_SLICE]` before hashing, exactly matching the Stage 6a probe's own slicing rule; the stored content and the hashed content are always byte-identical (verified by `test_fingerprint_matches_stored_content`).

## 11. Case-level total content cap — **[CORRECTED] removed entirely**

The original design's `MAX_FROZEN_CONTENT_PER_CASE = 65536`, enforced at `seal_evidence`, is **removed**. It was a genuine defect, not merely a conservative choice: `fetch_evidence` commits are immutable (§13), so a case that accumulated valid, successfully-fetched evidence past the cap through nothing but ordinary use became **permanently unsealable** — an unrecoverable dead end structurally identical in kind to the community-evidence bricking defect this correction fixes (§18). A late, seal-only cap over already-irreversible writes is unsafe regardless of the specific number chosen.

**No replacement cap was added.** The theoretical maximum frozen storage per case remains finite and bounded by the pre-existing, already-enforced caps alone:

```
MAX_EVIDENCE_PER_CASE (16) × MAX_EVIDENCE_SLICE (16,384) = 262,144 chars per case, worst case
```

This bound was always true; removing `MAX_FROZEN_CONTENT_PER_CASE` does not make storage unbounded, it only removes a *second, redundant, order-dependent* cap that could brick a case before the *first* one was ever approached. `test_theoretical_max_frozen_storage_is_bounded_without_a_cap` asserts this arithmetic directly; `test_large_immutable_fetches_never_prevent_seal` proves seal succeeds even after committing several maximum-size evidence items well past the old cap's threshold.

**Stage 7's prompt-size budget is explicitly a separate, later problem.** If a future stage's semantic adjudication needs a smaller effective input than 262,144 chars, that is solved with Stage 7-side techniques — bounded per-evidence excerpts, staged evaluation, evidence-by-evidence findings, bounded aggregation — never by re-introducing a Stage 6b storage/freeze-integrity cap. Freezing a trustworthy historical evidence snapshot and consuming it semantically are different problems with different failure costs: a storage cap that blocks freezing is unrecoverable (evidence is lost to history); a prompt-budget choice in Stage 7 is revisable per-run.

## 12. Fingerprint layering — **[CORRECTED]** four distinct, never-blurred identities

Three concepts, not one, describe an evidence case's evolving state, and the correction makes all three independently fingerprinted so Stage 7 can never reinterpret which evidence was actually included:

1. **Submitted membership** — every evidence ID frozen at `close_evidence`, creator and community alike, before any content exists.
2. **Retrieved content set** — evidence records with *any* committed terminal `retrieval_status` (`RETRIEVAL_FETCHED` or `RETRIEVAL_UNUSABLE_SHORT`), regardless of lane. Not separately fingerprinted as its own concept — it is fully recoverable from the disposition fingerprint below plus each item's own `content_fingerprint`.
3. **Adjudication input set** — the exact subset Stage 7 may consume: every required (creator, or all-of-root-envelope) item (guaranteed `RETRIEVAL_FETCHED` by the seal gate) **plus** any non-required (community) item that happened to reach `RETRIEVAL_FETCHED` by seal time. Excludes non-required items still `NOT_FETCHED` or `UNUSABLE_SHORT` — present in membership and disposition, absent here.

| Field | Binds | Computed at |
|---|---|---|
| `Evidence.content_fingerprint` | `SHA-256(bounded_rendered_text)` **alone** | `fetch_evidence` |
| `Case.membership_fingerprint` | ordered (evidence_id, normalized_url, render_profile, submitter, evidence_class) for **every submitted member** — **before any content exists** | `close_evidence` |
| `Case.retrieval_disposition_fingerprint` **(new field)** | ordered (evidence_id, retrieval_status) for **every submitted member**, whatever it resolved to (or didn't) | `seal_evidence` |
| `Case.evidence_set_fingerprint` | ordered (evidence_id, content_fingerprint) for the **adjudication-eligible subset only** | `seal_evidence` |
| `Case.case_fingerprint` | target-specific identity + `membership_fingerprint` + `retrieval_disposition_fingerprint` + `evidence_set_fingerprint` + `adjudication_dimensions_version` | `seal_evidence` |

**Why a fourth field (`retrieval_disposition_fingerprint`) was necessary, not optional.** Before the correction, `evidence_set_fingerprint` tried to mean two things at once — "what was submitted" and "what's usable" — which is exactly the kind of overload the original architecture review warned against. Splitting them means: `evidence_set_fingerprint` alone answers "what did Stage 7 actually see," while `retrieval_disposition_fingerprint` alone answers "what happened to everything that was submitted, including what Stage 7 never saw." Neither can substitute for the other, and `case_fingerprint` binds both so a later reader cannot claim one without the other being independently checkable.

**Why `content_fingerprint` is pure content identity, with no metadata mixed in.** Unchanged from the original design: anyone who independently fetches the same URL under the same render profile can reproduce the exact same `content_fingerprint` by hashing the result themselves. Domain-separation tags (`"gf-case-membership/v1"`, `"gf-retrieval-disposition/v1"`, `"gf-evidence-set/v1"`, `"gf-case/v1"`) prevent any cross-purpose fingerprint collision even if byte content happened to coincide.

**`case_fingerprint` for `CASE_TYPE_FORK`** binds: case type/version, case_id, `adjudication_dimensions_version`, `fork_id`, `fork.body_fingerprint`, `root_id`, `root.import_fingerprint`, `membership_fingerprint`, `retrieval_disposition_fingerprint`, `evidence_set_fingerprint`.

**`case_fingerprint` for `CASE_TYPE_ROOT_ENVELOPE`** binds: case type/version, case_id, `adjudication_dimensions_version`, `root_id`, `root.import_fingerprint`, the **complete** frozen envelope (`objective`, `beneficiary_class`, `resource_type`, `scope`, `essential_constraints`, `mutable_dimensions`, `immutable_dimensions`, `envelope_version`) — not a subset (an earlier draft bound only four fields; a test caught the gap before this stage first landed) — `membership_fingerprint`, `retrieval_disposition_fingerprint`, `evidence_set_fingerprint`.

## 12a. Submitted membership vs. retrieved content vs. adjudication input — the required/non-blocking split

**Required lane (must reach `RETRIEVAL_FETCHED`, or seal is rejected):**
- `CASE_TYPE_FORK`: evidence submitted by `fork.creator`.
- `CASE_TYPE_ROOT_ENVELOPE`: **every** submitted item — there is no community-contribution path for root-envelope evidence in V1 (every item currently shares one submitter), so applying the same "required" rule uniformly is the correct parity application of the fork rule, not a double standard (§4 of the correction, §19 of this doc).

Critically, `RETRIEVAL_UNUSABLE_SHORT` does **not** satisfy the required-lane requirement, and neither does `RETRIEVAL_NOT_FETCHED` — only a genuinely useful `RETRIEVAL_FETCHED` result counts. This prevents a proposer from padding a case with broken or empty required URLs and sealing around them (`test_fork_seal_rejects_when_creator_evidence_unusable_short`, `test_root_envelope_seal_rejects_when_required_evidence_unusable_short`).

**Non-blocking lane (community evidence on `CASE_TYPE_FORK` only):** any `retrieval_status` is acceptable at seal time.

- `RETRIEVAL_FETCHED` → included in the adjudication input set (`test_community_fetched_evidence_included_in_adjudication_set`).
- `RETRIEVAL_UNUSABLE_SHORT` → remains in membership and disposition, fully auditable (`frozen_content`/`content_fingerprint` preserved), but **excluded** from the adjudication input set unless a future stage explicitly supports consuming unusable-length evidence (`test_fork_seal_succeeds_with_unusable_short_community_evidence`).
- `RETRIEVAL_NOT_FETCHED` → remains in membership and disposition, excluded from the adjudication input set, **does not block seal** (`test_fork_seal_succeeds_with_unresolved_community_evidence`, `test_stage7_input_excludes_records_without_eligible_content`).

**Exact wording for `NOT_FETCHED` at seal time**, precise on purpose: *"No consensus-approved frozen content was committed for this evidence before sealing."* This is explicitly **not** a claim that the URL is unreachable, that the claim is false, or that retrieval "failed" in any semantic sense — it is a statement about what the contract observed by the time sealing happened, nothing more. A future case could, in principle, still fetch that same evidence item... except it cannot, because `fetch_evidence` requires `case.state == CASE_EVIDENCE_CLOSED` and sealing moves the case to `CASE_CASE_FROZEN`. So in practice, once sealed, a `NOT_FETCHED` community item's disposition is permanent for that case — but the *reason* it never resolved is never claimed to be known, and no semantic weight is attached to it by Stage 6b.

**Community evidence is never silently dropped.** No method exists that deletes an `Evidence` record. `close_evidence` freezes membership (including every community item) into `membership_fingerprint`; `seal_evidence` freezes the true disposition of every member (including community items that stayed `NOT_FETCHED`) into `retrieval_disposition_fingerprint`. Both remain permanently queryable via `get_case`/`get_evidence`/`list_evidence_of_case`. Only inclusion in the *adjudication input set* is conditional — the record itself never is (`test_creator_cannot_delete_or_overwrite_community_membership`, `test_seal_fingerprints_the_true_disposition_of_every_member`).

## 13. Stored content — exact, immutable, never refetched

`Evidence.frozen_content: str` stores the exact bounded, consensus-approved text used to compute `content_fingerprint`. **Stage 7 will read this field — it will never refetch a live (mutable) webpage and assume it is unchanged.** This is the core Governance Fork integrity requirement this stage exists to satisfy: evidence URLs can change after submission (§14), so evidence metadata registration (Stage 5) and evidence content freeze (this stage) are deliberately distinct steps, and once frozen, content is permanently immutable — `fetch_evidence` rejects any second call on an already-resolved evidence item (`test_successful_fetch_cannot_be_overwritten`).

## 14. The mutable-webpage problem, and retry semantics

For an evidence item not yet successfully fetched, `fetch_evidence` may be retried any number of times (§8's atomicity guarantee makes this safe). **After a successful commit — `RETRIEVAL_FETCHED` or `RETRIEVAL_UNUSABLE_SHORT`, both terminal — no refetch, no refresh, no "update to latest page."** A successful freeze captures a historical snapshot. If a newer version of a page matters later, that requires a new case/evidence record, not a mutation of this one.

## 15. Case freeze atomicity — **[CORRECTED]**

Invariant enforced by construction, restated for the corrected rule: a case with N evidence records cannot become `CASE_CASE_FROZEN` unless every **required** member (§12a) has reached `RETRIEVAL_FETCHED`. Non-required (community) members impose **no** condition — any status, including still `RETRIEVAL_NOT_FETCHED`, is acceptable. `seal_evidence` classifies each member as required or not, checks the required ones first (the first required item that isn't `RETRIEVAL_FETCHED` raises immediately, before any fingerprint is computed or any state written), and only then computes the eligible set and both new-and-existing fingerprints. No partial freeze is representable (`test_no_partial_final_freeze_on_reject`); no non-required item can block a freeze that every required item is ready for (`test_fork_seal_succeeds_with_unresolved_community_evidence`).

## 16. Close → Fetch → Seal lifecycle

```
CASE_OPEN
  → close_evidence(case_id)         [deterministic, owner-gated, paused-gated]
CASE_EVIDENCE_CLOSED
  → fetch_evidence(evidence_id) x N [nondeterministic, permissionless, NOT paused-gated,
                                      one evidence item per call, retriable on failure]
  → seal_evidence(case_id)          [deterministic, permissionless, NOT paused-gated,
                                      requires every REQUIRED member RETRIEVAL_FETCHED;
                                      non-required members impose no condition]
CASE_CASE_FROZEN                    [terminal, immutable]

CASE_EVIDENCE_CLOSED
  → abort_case(case_id)             [deterministic, owner-gated, paused-gated]
CASE_ABORTED                        [terminal, explicit, auditable escape valve --
                                      now needed only when REQUIRED evidence is
                                      permanently unfetchable; community evidence
                                      alone can never force this path]
```

`CASE_EVIDENCE_FROZEN` (a Stage 2-reserved enum value) is intentionally **not** used as a `Case.state` value by this design — both `evidence_set_fingerprint` and `case_fingerprint` are pure deterministic computations over already-committed evidence with no nondeterminism between them, so there is no natural moment where a case would sit "all evidence frozen but not yet sealed." The constant remains defined (harmless, avoids implying prior work was wrong) but documented here as unused by Stage 6b's state machine.

## 17. Close authorization

`close_evidence` and `abort_case` are **owner-gated**: `fork.creator` for `CASE_TYPE_FORK`, `root.proposer` for `CASE_TYPE_ROOT_ENVELOPE` (resolved by the new `_case_owner` helper). **Documented tradeoff, not glossed over:** this project has no live-verified trusted-timestamp source (Stage 3/5's own limitation, still open), so a time-windowed automatic close ("evidence submission closes after 72h") cannot currently be implemented honestly — "do not invent time" applies here exactly as it did to challenge windows in earlier stages. Owner-initiated close is therefore the V1 choice, with the acknowledged centralization/liveness cost: the case owner must actively close it to make progress. A future stage with a verified timestamp source could add a permissionless time-based close path without changing this stage's schema.

`fetch_evidence` and `seal_evidence` are **fully permissionless** — any caller may advance a closed case (verified by `test_fetch_permissionless_and_not_paused_gated`, `test_seal_permissionless_and_not_paused_gated`), favoring liveness over restricting who can pay the gas to make progress.

## 18. Community-evidence griefing — **[CORRECTED]** solution and reasoning

**The original defect.** Version `28c42c1` required *every* member — creator and community alike — to reach a terminal `retrieval_status` before a case could seal. This made a single community contributor's unrenderable or intentionally-broken URL a genuine bricking vector: membership closes, the URL never resolves, the case can never seal, and the only escape was `abort_case` — an entire-case-level response to what should have been a single evidence item's problem. Worse, since `abort_case` had no companion fresh-attempt path (§18b), a determined griefer effectively forced the fork/root's evidence effort to a dead end.

**Why the original "resolved, not specifically FETCHED" framing wasn't the real problem, and required-lane status was.** The original design's justification — that `RETRIEVAL_UNUSABLE_SHORT` also counted as "resolved," so the failure mode was symmetric between creator and community — was true as far as it went, but missed the actual fix: the defect was never about *which finding counts as resolved*, it was about *treating creator and community evidence as equally load-bearing for sealing at all*. They are not. A fork's creator chose to stand behind their own evidence; a community contributor's evidence is a voluntary addition the fork does not depend on to exist. Making community evidence load-bearing for seal was the mistake, independent of how strict the "resolved" bar was set.

**The corrected model:**

- **Required lane** (`fork.creator` for `CASE_TYPE_FORK`; *everyone*, i.e. all evidence, for `CASE_TYPE_ROOT_ENVELOPE`, since there is no community concept there): must reach `RETRIEVAL_FETCHED` — not merely resolved. `RETRIEVAL_UNUSABLE_SHORT` **does not** satisfy this (tightened from the original design, not loosened — see §12a).
- **Non-blocking lane** (community evidence on `CASE_TYPE_FORK` only): any status at all, including permanently `RETRIEVAL_NOT_FETCHED`, is acceptable at seal. **This is the actual fix.** A community contributor cannot force a fork into `abort_case` territory merely by contributing a bad URL — their evidence simply becomes ineligible for the adjudication input set, while the case proceeds normally on schedule set by the required (creator) evidence alone.

`abort_case` **remains**, but its role narrows to what it should always have been: the escape valve for **required** evidence becoming permanently unfetchable — a self-inflicted problem (the creator's own broken URL, or, for root-envelope cases, any of the single submitter's own URLs), not a third-party griefing vector. Verified: `test_unavailable_community_evidence_does_not_block_seal` (seal succeeds despite a permanently-broken community URL, no abort needed) vs. `test_unavailable_creator_evidence_still_blocks_seal` (creator's own broken URL still requires `abort_case`, exactly as before).

**No silent exclusion, unchanged principle, now doing more work.** A `RETRIEVAL_UNUSABLE_SHORT` or `RETRIEVAL_NOT_FETCHED` community item is never hidden, deleted, or overwritten — it remains visible with its honest status via `membership_fingerprint` and the new `retrieval_disposition_fingerprint` (§12), permanently queryable through `get_evidence`/`list_evidence_of_case`, forever (`test_transparent_unusable_status_no_silent_drop`, `test_creator_cannot_delete_or_overwrite_community_membership`). Only *eligibility for adjudication* is conditional; the record of what was submitted, by whom, and what happened to it, never is. Stage 6b attaches no semantic penalty to any retrieval outcome — a `NOT_FETCHED` community item is not evidence the claim was false, only that no consensus-approved content was committed before this case sealed (`test_no_semantic_penalty_encoded_in_retrieval_outcome`).

## 18a. Root-envelope parity under the correction

Root-envelope cases have no separate community-contribution path in V1 — every evidence item submitted via `submit_root_envelope` shares one submitter. Applying "the same reasoning" (per the correction's explicit instruction) to a case type with no community lane means: **all** root-envelope evidence is naturally in the required lane, exactly mirroring how a fork's creator lane behaves. This is not a weaker protection for root-envelope cases — `abort_case` remains available identically for both case types — it is the correct, consistent seal-strictness rule applied uniformly, rather than letting root-envelope evidence tolerate `RETRIEVAL_UNUSABLE_SHORT` while a fork's creator lane does not. `test_root_envelope_seal_rejects_when_required_evidence_unusable_short` and `test_root_envelope_seal_succeeds_when_all_required_fetched` cover this directly.

## 18b. Abort/retry semantics — re-evaluated

- **Does `abort_case` remain needed?** Yes — narrower than before (§18), but still the only tool for a case whose *required* evidence becomes permanently unfetchable.
- **Exact allowed states:** only `CASE_EVIDENCE_CLOSED` may be aborted. An `CASE_OPEN` case needs no aborting (the owner can simply stop submitting/never close it); a `CASE_CASE_FROZEN` case is immutable by design (`test_abort_frozen_case_rejected`, pre-existing).
- **Does aborting delete or alter anything?** No. Verified directly (`test_abort_does_not_delete_or_mutate_any_state`): every `Evidence` field and the case's `membership_fingerprint` are byte-identical before and after abort; only `Case.state` changes, to `CASE_ABORTED`.
- **Is the old case/evidence still queryable?** Yes, permanently, via the same `get_case`/`get_evidence`/`list_evidence_of_case` views as any other case (`test_aborted_case_remains_fully_queryable`).
- **Can an aborted case adjudicate?** No — `adjudicate` is Stage 7's unimplemented placeholder regardless, but structurally an aborted case's `case_fingerprint` was never sealed (`case_fingerprint == b""` forever), so there is nothing for a future Stage 7 to adjudicate against even once implemented (`test_aborted_case_cannot_adjudicate`).
- **Is fresh-attempt recovery possible for the same fork/root in V1?** **No, deliberately not implemented.** `fork.evidence_case_id` still points at the aborted case, and `submit_fork_evidence`'s reuse path is gated on `self.cases[case_id].state == CASE_OPEN` (added earlier in Stage 6b to prevent post-close additions) — an aborted case is never `CASE_OPEN` again, so further submission attempts for that fork are permanently rejected (`test_no_fresh_case_recovery_path_in_v1`). **Justification for not building this now:** with the community-bricking defect fixed, the remaining trigger for `abort_case` is narrow and self-inflicted (a creator's own bad URL, or a root importer's own bad URL) — not an adversarial vector requiring urgent mitigation. Building full attempt-numbering (a new `attempt_number` field, preserved-history linking between an aborted case and its successor, an "active attempt" pointer distinct from `fork.evidence_case_id`) is real, non-trivial schema growth for a problem that is now rare and non-adversarial. This is called out as an explicit, acknowledged V1 limitation (§26), not silently accepted.
- **No ID reuse.** `next_case_id` is monotonic and never rewound on abort; a fresh case for a *different* fork/root always gets a strictly greater ID than any aborted case (`test_no_id_reuse_across_cases`).
- **Active-case pointer correctness.** `fork.evidence_case_id` continues to point at the (now aborted) case; there is no second, ambiguous pointer to reconcile, precisely because no fresh case can be created for the same fork in V1.

## 19. Root / fork parity (general genericness, beyond §18a's correction-specific point)

`close_evidence`, `fetch_evidence`, and `abort_case` are fully generic — they operate only on `Case`/`Evidence` records and never branch on `case_type` except to resolve the authorization owner. `seal_evidence` branches on `case.case_type` for the required-lane determination (§12a, §18a) and the final `case_fingerprint` computation (§12), since a fork case and a root-envelope case bind genuinely different target-specific identity. Both case types were tested through the full lifecycle (`test_root_envelope_case_full_lifecycle`, `test_fork_case_full_lifecycle`), not just fork fixtures.

## 20. Root `web_content_fingerprint` — **[reconfirmed]** populated only from `RETRIEVAL_FETCHED`, never a duplicate fetch

`RootProposal.web_content_fingerprint` keeps its narrow Stage 2B meaning: the fingerprint of the root's own canonical `proposal_url`, never an aggregate. At `seal_evidence` for a `CASE_TYPE_ROOT_ENVELOPE` case, if `root.web_content_fingerprint` is still empty, the contract scans the case's frozen evidence for one whose normalized URL matches the root's normalized `proposal_url` **and** whose `retrieval_status == RETRIEVAL_FETCHED`, and copies that evidence's already-computed `content_fingerprint` — no second `render()` call is ever made for this purpose (verified by `test_no_duplicate_fetch_for_root_canonical_url`, which counts render invocations directly). If the submitter never included the canonical URL as evidence, `web_content_fingerprint` stays `b""` (`test_root_web_content_fingerprint_stays_empty_if_no_matching_evidence`) — an honest limitation: V1 does not force-include the canonical URL as mandatory evidence, though submitters are encouraged to do so.

**This rule is now structurally, not just behaviorally, guaranteed for root-envelope cases.** Since §18a makes *all* root-envelope evidence required, and required evidence must reach `RETRIEVAL_FETCHED` (never `RETRIEVAL_UNUSABLE_SHORT`) before `seal_evidence` proceeds past its required-lane check, there is no code path where a root-envelope case could ever reach the `web_content_fingerprint` derivation step while its canonical-URL evidence sits at `RETRIEVAL_UNUSABLE_SHORT` — sealing itself would already have been rejected. `test_root_web_content_fingerprint_never_derived_from_unusable_short` verifies this directly: seal is rejected before the derivation logic is ever reached.

## 21. Pause behavior

`close_evidence` and `abort_case` **are** gated on `self.paused` — both create or lock new exposure (closing new membership; terminally aborting a case). `fetch_evidence` and `seal_evidence` **are not** gated on `self.paused` — both are pure progress/exit operations on already-committed state, and blocking them would trap evidence mid-lifecycle for no safety benefit, violating the "pause should not trap already-committed state unnecessarily" principle established in earlier stages. Verified directly (`test_close_paused_rejected`, `test_abort_paused_rejected`, `test_fetch_permissionless_and_not_paused_gated`, `test_seal_permissionless_and_not_paused_gated`).

## 22. ABI

**Before Stage 6b:** 29 methods (11 write + 2 admin + 16 view).
**After Stage 6b (unchanged by the correction):** 31 methods (13 write + 2 admin + 16 view).

Change: `freeze_evidence` and `freeze_case` (Stage 2 placeholders, whose 2-step name/shape never matched the eventual 3-step Close→Fetch→Seal design) removed and replaced with `close_evidence`, `fetch_evidence`, `seal_evidence` (the exact names this stage's own architecture specifies), plus the new `abort_case` escape valve. Net: −2 +4 = **+2 write methods.** No new view methods were needed — `get_case` and `get_evidence` already return the full (now-extended) `Case`/`Evidence` records; a small, justified ABI increase, not an incoherent API.

`submit_root_envelope` and `submit_fork_evidence` (both pre-existing) gained one new parameter each, `render_profiles: DynArray[str]`, a parallel array to the existing evidence arrays — required so the render profile decision genuinely belongs to the submitter (§5), not bolted on elsewhere. This is a signature change to existing methods, not a new method.

**The correction added zero new ABI methods.** All fixes (required/non-blocking lane split, disposition fingerprint, cap removal) live entirely inside `seal_evidence`'s existing body and the `Case`/`Evidence` dataclasses' existing field sets (plus one new `Case` field, §12). `close_evidence`, `fetch_evidence`, and `abort_case` needed no signature changes at all.

## 23. Studio-schema-safe storage design

`Evidence` fields (unchanged by the correction): `render_profile: str`, `retrieval_status: str`, `frozen_content: str` (bounded to `MAX_EVIDENCE_SLICE`). `Case` fields: `membership_fingerprint: bytes` (from the original Stage 6b design) plus **`retrieval_disposition_fingerprint: bytes` (new, added by this correction)**. All use primitive types (`str`, `bytes`) already accepted by Studio across every prior schema-load gate — no new dataclass nesting, no exotic container shapes, no new decorators. Every canonicalization helper (including the new `_canonicalize_retrieval_disposition`/`_retrieval_disposition_fingerprint`) follows the exact `bytes`-buffer-concatenation pattern already validated in Stages 3–4.

## 24. Local test suite (`tests/test_stage_6b.py`, 84 tests)

**LOCAL LOGIC TESTS ONLY**, explicitly labeled in the file's own docstring and in every relevant test/helper name. They exercise the contract's deterministic storage, fingerprint, and lifecycle logic using a mocked `gl.nondet.web.render` (`tests/_genlayer_shim.py`'s `_MockWebRegistry` — configurable per-URL responses or failures, `strict_eq` implemented as a direct call with no simulated consensus/rotation/Undetermined). **They do not exercise, simulate, or prove anything about live render() behavior, consensus outcomes, or Undetermined handling.** That is Stage 6a's exclusive domain, and its live evidence (`docs/STAGE_6A_WEB_RENDER_PROBE_REPORT.md`) is not re-derived or re-claimed by any test in this file.

**Tests added or rewritten by the correction (17 net new, from 67 to 84):**

- `SealEvidenceTests`: rewrote the old "seal succeeds when all resolved including unusable" test into two explicit root-envelope tests (rejects on required `UNUSABLE_SHORT`; succeeds when all required `FETCHED`); added fork-side tests for community-non-blocking success with `NOT_FETCHED`/`UNUSABLE_SHORT` community items, creator-`UNUSABLE_SHORT` still blocking, community success not substituting for a missing creator item; removed the now-invalid `test_total_content_cap_blocks_seal`; added the theoretical-max-bound test and a large-immutable-content-never-blocks-seal adversarial-shaped test.
- `CommunityGriefingTests`: rewrote the two core tests to assert the corrected outcome (community failure → seal succeeds, no abort needed; creator failure → seal still blocked, abort still needed); added tests for adjudication-set inclusion of `FETCHED` community evidence, exclusion of non-eligible records from the adjudication set with an explicit fingerprint comparison, disposition-fingerprint accuracy, structural non-deletability of community records, and structural absence of any semantic-verdict vocabulary inside `seal_evidence`'s own source.
- `AbortCaseTests`: added full queryability-after-abort, no-mutation-on-abort, cannot-adjudicate-after-abort, no-fresh-case-recovery-path (documenting the deliberate V1 limitation), and no-ID-reuse-across-cases tests.
- `RootForkParityTests`: added the explicit test proving `web_content_fingerprint` can never be derived from `RETRIEVAL_UNUSABLE_SHORT` content (§20).

**Two real bugs found and fixed while building the original suite** (unchanged by this correction, restated for the record):

1. **Pre-existing Stage 5 bug**: `submit_fork_evidence` never populated `Case.evidence_ids` — only the separate `evidence_by_case` index. Fixed by appending to both in lockstep.
2. **Stage 6b's own gap, caught by its own test**: the initial `_canonicalize_case_root_envelope` bound only 4 of the envelope's 8 fields. Fixed to bind the complete frozen envelope.

## 25. Regression across every prior stage

- Stage 3, 4, 5 test suites (148 tests, unchanged by this correction) remain green.
- `tests/stage_2_checks.py`: ABI-count expectation (13/16/2/31) and the render/strict_eq baseline are unchanged by this correction — the fix touched no ABI surface.
- `tests/stage_6a_probe_checks.py`: unchanged.
- **Full regression after the correction: 232 tests (51 + 51 + 46 + 84) pass. 11/11 Stage 2 static checks pass. 13/13 Stage 6a probe checks pass.**

## 26. Known limitations

- Native GEN read/transfer remains `DOCUMENTED BUT NOT LIVE VERIFIED`/`UNKNOWN` — unchanged, out of scope here.
- No trusted timestamp source — `close_evidence` stays owner-gated rather than time-windowed (§17). **Not fixed by this correction** — `close_evidence`'s owner-only gate still means a case with only community evidence submitted so far and an unresponsive fork creator cannot be closed at all. This is a distinct liveness gap from the one this correction fixes (which was about *sealing* an already-closed case, not *closing* one) and remains open.
- `WEBPAGE_LOAD_FAILED` exception-catching remains unverified and deliberately unused (§7).
- **[RESOLVED by this correction]** ~~`MAX_FROZEN_CONTENT_PER_CASE` provisional cap~~ — removed entirely (§11). No replacement cap; the pre-existing `MAX_EVIDENCE_PER_CASE × MAX_EVIDENCE_SLICE` bound was always sufficient.
- **[RESOLVED by this correction]** ~~Community evidence could brick a case's seal~~ — community evidence is now non-blocking at seal (§12a, §18). The only remaining trigger for `abort_case` is required (creator, or all-of-root-envelope) evidence becoming permanently unfetchable — a narrower, self-inflicted, non-adversarial scenario.
- No fresh-case recovery path for a fork/root whose case was aborted (§18b) — deliberately not built in V1, justified by the narrowed, non-adversarial nature of the remaining `abort_case` trigger. Still an accepted, documented gap for a later stage if it proves needed in practice.

## 27. Stage 7 handoff

Stage 7 (semantic adjudication, not started) can rely on:

- `Case.case_fingerprint` uniquely and completely identifying one frozen adjudication input (target identity + membership + retrieval disposition + adjudication-eligible evidence content, all immutable).
- `Case.evidence_set_fingerprint` identifying exactly the adjudication-eligible evidence subset — the set Stage 7 is actually allowed to consume. **Not** the full membership; community items that never reached `RETRIEVAL_FETCHED` are excluded here even though they remain in `Case.membership_fingerprint`/`Case.retrieval_disposition_fingerprint`.
- `Case.retrieval_disposition_fingerprint` as the complete, honest record of what happened to *every* submitted item, including ones Stage 7 will never see content for. Useful for a future Explorer/audit view, not for adjudication input selection.
- `Evidence.frozen_content` as the exact, permanent text to reason over for eligible evidence — never a live refetch.
- `Evidence.retrieval_status` distinguishing usable (`RETRIEVAL_FETCHED`) from resolved-but-unusable (`RETRIEVAL_UNUSABLE_SHORT`) from never-resolved (`RETRIEVAL_NOT_FETCHED`) evidence, none carrying an implicit semantic verdict.
- `RootProposal.web_content_fingerprint` as a narrow, honest signal (may legitimately be empty), now structurally guaranteed to only ever come from `RETRIEVAL_FETCHED` content (§20).
- The atomicity guarantee that `CASE_CASE_FROZEN` is truly terminal and complete — no partial evidence, no partial fingerprint, ever — and that reaching it no longer depends on community evidence resolving at all, only on required evidence doing so.
