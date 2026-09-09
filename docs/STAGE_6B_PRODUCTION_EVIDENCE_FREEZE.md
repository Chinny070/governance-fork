# Stage 6b — Production Evidence Retrieval, Content Fingerprinting & Atomic Evidence Freeze

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

## 11. Case-level total content cap — new, provisional

```python
MAX_FROZEN_CONTENT_PER_CASE = 65536
```

**Rationale.** 16 evidence items × 16,384 chars = 262,144 chars worst case per case — excessive for storage, Explorer usability, and eventual Stage 7 prompt size. 65,536 is roughly 4× Stage 6a's largest single observed source, giving headroom for several rich evidence items per case without approaching the theoretical worst case. **Explicitly marked provisional** per this stage's own instruction ("if current evidence is insufficient to safely select a cap: mark provisional and create a later live stress gate") — Stage 6b has no live data on realistic *multi*-evidence case sizes, only single-source data from Stage 6a.

**Enforcement.** Checked at `seal_evidence`, not at `fetch_evidence` — an individual fetch always commits if it succeeds (content and fingerprint are never discarded after the fact, per the immutability rule in §13). If the sum of all frozen content in a case exceeds the cap, `seal_evidence` rejects and the case remains `CASE_EVIDENCE_CLOSED` — not bricked; `abort_case` remains available (§14). Verified by `test_total_content_cap_blocks_seal`.

## 12. Fingerprint layering — three distinct, never-blurred identities

| Field | Binds | Computed at |
|---|---|---|
| `Evidence.content_fingerprint` | `SHA-256(bounded_rendered_text)` **alone** | `fetch_evidence` |
| `Case.membership_fingerprint` | ordered (evidence_id, normalized_url, render_profile, submitter, evidence_class) — **before any content exists** | `close_evidence` |
| `Case.evidence_set_fingerprint` | ordered (evidence_id, content_fingerprint, retrieval_status) — **after all fetches resolve** | `seal_evidence` |
| `Case.case_fingerprint` | target-specific identity (fork or root envelope) + both fingerprints above | `seal_evidence` |

**Why `content_fingerprint` is pure content identity, with no metadata mixed in.** Anyone who independently fetches the same URL under the same render profile can reproduce the exact same `content_fingerprint` by hashing the result themselves — a directly auditable property. Source identity (who submitted it, what class they claimed) and case identity (which case, which target) live one layer up, in `membership_fingerprint` and `case_fingerprint` respectively. Domain-separation tags (`"gf-delta/v1"`-style prefixes: `"gf-case-membership/v1"`, `"gf-evidence-set/v1"`, `"gf-case/v1"`) prevent any cross-purpose fingerprint collision even if byte content happened to coincide.

**`case_fingerprint` for `CASE_TYPE_FORK`** binds: case type/version, case_id, `adjudication_dimensions_version`, `fork_id`, `fork.body_fingerprint`, `root_id`, `root.import_fingerprint`, `membership_fingerprint`, `evidence_set_fingerprint`.

**`case_fingerprint` for `CASE_TYPE_ROOT_ENVELOPE`** binds: case type/version, case_id, `adjudication_dimensions_version`, `root_id`, `root.import_fingerprint`, and the **complete** frozen envelope (`objective`, `beneficiary_class`, `resource_type`, `scope`, `essential_constraints`, `mutable_dimensions`, `immutable_dimensions`, `envelope_version`) — not a subset. An earlier draft of this stage bound only four envelope fields; a test (`test_case_fingerprint_root_envelope_binds_envelope_fields`) caught that two envelopes differing only in dimension classification produced identical fingerprints, and the canonicalization was corrected to bind the full envelope before this stage was considered complete.

## 13. Stored content — exact, immutable, never refetched

`Evidence.frozen_content: str` stores the exact bounded, consensus-approved text used to compute `content_fingerprint`. **Stage 7 will read this field — it will never refetch a live (mutable) webpage and assume it is unchanged.** This is the core Governance Fork integrity requirement this stage exists to satisfy: evidence URLs can change after submission (§14), so evidence metadata registration (Stage 5) and evidence content freeze (this stage) are deliberately distinct steps, and once frozen, content is permanently immutable — `fetch_evidence` rejects any second call on an already-resolved evidence item (`test_successful_fetch_cannot_be_overwritten`).

## 14. The mutable-webpage problem, and retry semantics

For an evidence item not yet successfully fetched, `fetch_evidence` may be retried any number of times (§8's atomicity guarantee makes this safe). **After a successful commit — `RETRIEVAL_FETCHED` or `RETRIEVAL_UNUSABLE_SHORT`, both terminal — no refetch, no refresh, no "update to latest page."** A successful freeze captures a historical snapshot. If a newer version of a page matters later, that requires a new case/evidence record, not a mutation of this one.

## 15. Case freeze atomicity

Invariant enforced by construction: a case with N evidence records cannot become `CASE_CASE_FROZEN` unless every one of its N members has resolved to a terminal `retrieval_status`. `seal_evidence` checks `ev.frozen` (true once any terminal status is committed) for every `eid` in `case.evidence_ids` before computing anything; the first unresolved item raises immediately, before any fingerprint is computed or any state written. No partial freeze is representable (`test_no_partial_final_freeze_on_reject`).

## 16. Close → Fetch → Seal lifecycle

```
CASE_OPEN
  → close_evidence(case_id)         [deterministic, owner-gated, paused-gated]
CASE_EVIDENCE_CLOSED
  → fetch_evidence(evidence_id) x N [nondeterministic, permissionless, NOT paused-gated,
                                      one evidence item per call, retriable on failure]
  → seal_evidence(case_id)          [deterministic, permissionless, NOT paused-gated,
                                      requires every member resolved]
CASE_CASE_FROZEN                    [terminal, immutable]

CASE_EVIDENCE_CLOSED
  → abort_case(case_id)             [deterministic, owner-gated, paused-gated]
CASE_ABORTED                        [terminal, explicit, auditable escape valve]
```

`CASE_EVIDENCE_FROZEN` (a Stage 2-reserved enum value) is intentionally **not** used as a `Case.state` value by this design — both `evidence_set_fingerprint` and `case_fingerprint` are pure deterministic computations over already-committed evidence with no nondeterminism between them, so there is no natural moment where a case would sit "all evidence frozen but not yet sealed." The constant remains defined (harmless, avoids implying prior work was wrong) but documented here as unused by Stage 6b's state machine.

## 17. Close authorization

`close_evidence` and `abort_case` are **owner-gated**: `fork.creator` for `CASE_TYPE_FORK`, `root.proposer` for `CASE_TYPE_ROOT_ENVELOPE` (resolved by the new `_case_owner` helper). **Documented tradeoff, not glossed over:** this project has no live-verified trusted-timestamp source (Stage 3/5's own limitation, still open), so a time-windowed automatic close ("evidence submission closes after 72h") cannot currently be implemented honestly — "do not invent time" applies here exactly as it did to challenge windows in earlier stages. Owner-initiated close is therefore the V1 choice, with the acknowledged centralization/liveness cost: the case owner must actively close it to make progress. A future stage with a verified timestamp source could add a permissionless time-based close path without changing this stage's schema.

`fetch_evidence` and `seal_evidence` are **fully permissionless** — any caller may advance a closed case (verified by `test_fetch_permissionless_and_not_paused_gated`, `test_seal_permissionless_and_not_paused_gated`), favoring liveness over restricting who can pay the gas to make progress.

## 18. Community-evidence griefing — solution and reasoning

**The attack:** a contributor (creator or community) submits an apparently valid URL; membership closes; the URL becomes permanently unavailable or unrenderable; the case can never resolve every member to a terminal status, so it can never seal.

**Chosen model, and why the instructions' suggested required/optional split was evaluated and not needed:** the architecture reviewed distinguishing "required" (creator) evidence from "optional" (community) evidence for seal purposes, but found it unnecessary given the actual seal condition. `seal_evidence` requires every member to be **resolved** (`frozen == True`), not specifically `RETRIEVAL_FETCHED` — `RETRIEVAL_UNUSABLE_SHORT` also counts as resolved. The only way a case gets permanently stuck is an item that **never completes any successful `fetch_evidence` call at all** (permanently reverting). This failure mode is exactly symmetric between creator and community evidence — a required-only fix would just shift the griefing vector onto whichever evidence class was deemed "required." Verified directly by `test_unavailable_creator_evidence_treated_identically`, which shows creator-submitted unfetchable evidence blocks seal exactly the same way community evidence does.

**The actual solution:** `abort_case`, the explicit, auditable escape valve (§17). It does not silently drop the stuck evidence — the record remains permanently readable at `RETRIEVAL_NOT_FETCHED` (verified by `test_abort_recovers_from_permanently_unavailable_evidence`) — it simply lets the case owner give up on this particular case and (implicitly, at a later stage) start a fresh one. Other cases, including a different fork under the same root, are entirely unaffected by one case's abort (`test_case_liveness_after_retrieval_failure`).

**No silent exclusion.** A `RETRIEVAL_UNUSABLE_SHORT` community item is never hidden or dropped from the sealed evidence set — it is visible, with its honest status, to anyone reading the case (`test_transparent_unusable_status_no_silent_drop`). Stage 6b attaches no semantic penalty to any retrieval outcome; that judgment belongs to Stage 7.

## 19. Root / fork parity

`close_evidence`, `fetch_evidence`, and `abort_case` are fully generic — they operate only on `Case`/`Evidence` records and never branch on `case_type` except to resolve the authorization owner. `seal_evidence` branches on `case.case_type` only for the final `case_fingerprint` computation (§12), since a fork case and a root-envelope case bind genuinely different target-specific identity. Both case types were tested through the full lifecycle (`test_root_envelope_case_full_lifecycle`, `test_fork_case_full_lifecycle`), not just fork fixtures.

## 20. Root `web_content_fingerprint` — populated without a duplicate fetch

`RootProposal.web_content_fingerprint` keeps its narrow Stage 2B meaning: the fingerprint of the root's own canonical `proposal_url`, never an aggregate. At `seal_evidence` for a `CASE_TYPE_ROOT_ENVELOPE` case, if `root.web_content_fingerprint` is still empty, the contract scans the case's frozen evidence for one whose normalized URL matches the root's normalized `proposal_url` **and** whose `retrieval_status == RETRIEVAL_FETCHED**, and copies that evidence's already-computed `content_fingerprint` — no second `render()` call is ever made for this purpose (verified by `test_no_duplicate_fetch_for_root_canonical_url`, which counts render invocations directly). If the submitter never included the canonical URL as evidence, `web_content_fingerprint` stays `b""` — an honest limitation: V1 does not force-include the canonical URL as mandatory evidence, though submitters are encouraged to do so (`test_root_web_content_fingerprint_stays_empty_if_no_matching_evidence`).

## 21. Pause behavior

`close_evidence` and `abort_case` **are** gated on `self.paused` — both create or lock new exposure (closing new membership; terminally aborting a case). `fetch_evidence` and `seal_evidence` **are not** gated on `self.paused` — both are pure progress/exit operations on already-committed state, and blocking them would trap evidence mid-lifecycle for no safety benefit, violating the "pause should not trap already-committed state unnecessarily" principle established in earlier stages. Verified directly (`test_close_paused_rejected`, `test_abort_paused_rejected`, `test_fetch_permissionless_and_not_paused_gated`, `test_seal_permissionless_and_not_paused_gated`).

## 22. ABI

**Before Stage 6b:** 29 methods (11 write + 2 admin + 16 view).
**After Stage 6b:** 31 methods (13 write + 2 admin + 16 view).

Change: `freeze_evidence` and `freeze_case` (Stage 2 placeholders, whose 2-step name/shape never matched the eventual 3-step Close→Fetch→Seal design) removed and replaced with `close_evidence`, `fetch_evidence`, `seal_evidence` (the exact names this stage's own architecture specifies), plus the new `abort_case` escape valve. Net: −2 +4 = **+2 write methods.** No new view methods were needed — `get_case` and `get_evidence` already return the full (now-extended) `Case`/`Evidence` records; a small, justified ABI increase, not an incoherent API.

`submit_root_envelope` and `submit_fork_evidence` (both pre-existing) gained one new parameter each, `render_profiles: DynArray[str]`, a parallel array to the existing evidence arrays — required so the render profile decision genuinely belongs to the submitter (§5), not bolted on elsewhere. This is a signature change to existing methods, not a new method; all call sites across Stages 3–5's test suites were updated accordingly (§25).

## 23. Studio-schema-safe storage design

New `Evidence` fields: `render_profile: str`, `retrieval_status: str`, `frozen_content: str` (bounded to `MAX_EVIDENCE_SLICE`). New `Case` field: `membership_fingerprint: bytes`. All use primitive types (`str`, `bytes`) already accepted by Studio across every prior schema-load gate — no new dataclass nesting, no exotic container shapes, no new decorators. Every canonicalization helper follows the exact `bytes`-buffer-concatenation pattern already validated in Stages 3–4 (`_canonicalize_root`, `_canonicalize_delta`, etc.).

## 24. Local test suite (`tests/test_stage_6b.py`, 67 tests)

**LOCAL LOGIC TESTS ONLY**, explicitly labeled in the file's own docstring and in every relevant test/helper name. They exercise the contract's deterministic storage, fingerprint, and lifecycle logic using a mocked `gl.nondet.web.render` (`tests/_genlayer_shim.py`'s new `_MockWebRegistry` — configurable per-URL responses or failures, `strict_eq` implemented as a direct call with no simulated consensus/rotation/Undetermined). **They do not exercise, simulate, or prove anything about live render() behavior, consensus outcomes, or Undetermined handling.** That is Stage 6a's exclusive domain, and its live evidence (`docs/STAGE_6A_WEB_RENDER_PROBE_REPORT.md`) is not re-derived or re-claimed by any test in this file.

Coverage: `close_evidence` (7 tests — zero-evidence rejection, membership fixing, no-additions-after-close, double-close rejection, unknown-case rejection, both authorization paths, pause gating), `fetch_evidence` (12 tests — pre-close rejection, unknown-evidence rejection, exact content freezing, fingerprint-matches-stored-content, no-overwrite, failure leaves record unfetched, failed fetch retriable, empty/below-threshold/at-threshold length gating, slicing to the cap, cross-case isolation, permissionless + pause-immunity, dynamic-profile routing), `seal_evidence` (8 tests — pre-close rejection, incomplete-fetch rejection, success with a mix of usable/unusable, deterministic fingerprint computation, no-repeat, no-partial-freeze-on-reject, target-fingerprint stability, permissionless + pause-immunity, total-content-cap enforcement), `abort_case` (6 tests — open-case rejection, closed-case success, frozen-case rejection, authorization, the griefing-recovery scenario, pause gating), community-griefing scenarios (4 tests — unavailable community evidence doesn't block other items and is abortable, unavailable creator evidence treated identically, transparent unusable status with no silent drop, case liveness after one case's retrieval failure), render profile (6 tests), fingerprints (7 tests — stability, content sensitivity, hashlib-reference match, membership order sensitivity, evidence-set content sensitivity, case-fingerprint target sensitivity, case-fingerprint full-envelope binding), root/fork parity (5 tests — both full lifecycles, web_content_fingerprint derivation and its empty-when-unmatched case, no-duplicate-fetch), prohibited behavior (7 tests — no `web.get`/semantic prompts/`gl.message.value`/`transfer(`, presence of `render`+`strict_eq`, AST-verified absence of try/except around the nondet call, `adjudicate` still unimplemented, `finalize` still an untouched Stage-2 placeholder).

**Two real bugs found and fixed while building this suite**, both documented rather than silently patched:

1. **Pre-existing Stage 5 bug**: `submit_fork_evidence` never populated `Case.evidence_ids` — only the separate `evidence_by_case` index — since Stage 5's own tests checked the index, never the field directly. Harmless until Stage 6b's `close_evidence`/`seal_evidence` began reading `case.evidence_ids` directly. Fixed by appending to both in lockstep.
2. **This stage's own gap, caught by its own test**: the initial `_canonicalize_case_root_envelope` bound only 4 of the envelope's 8 fields, so two envelopes differing solely in `mutable_dimensions`/`immutable_dimensions` produced identical `case_fingerprint`s. Fixed to bind the complete frozen envelope (§12).

## 25. Regression across every prior stage

- Stage 3, 4, 5 test suites (148 tests) updated for the `render_profiles` parameter addition and the removed `freeze_evidence` placeholder, then re-verified green.
- `tests/stage_2_checks.py` updated: ABI-count expectation raised to 13/16/2/31; the "no prohibited calls" check's baseline shifted to permit `gl.nondet.web.render(`/`gl.eq_principle.strict_eq(` while continuing to ban `web.get(`, `prompt_comparative`, `prompt_non_comparative`, `exec_prompt`, `transfer(` — with a positive assertion that `render`/`strict_eq` are actually present (so the claim isn't merely "nothing forbidden," but "the sanctioned pathway is genuinely used").
- `tests/stage_6a_probe_checks.py`'s "production contract unaffected" check updated: its premise (zero `gl.nondet.*` in production) was Stage 6a-era and correctly superseded by Stage 6b's approved outcome; narrowed to what actually still matters — production never references the isolated probe file, never falls back to `web.get(`.
- **Full regression: 215 tests (51 + 51 + 46 + 67) pass. 11/11 Stage 2 static checks pass. 13/13 Stage 6a probe checks pass.**

## 26. Known limitations

- Native GEN read/transfer remains `DOCUMENTED BUT NOT LIVE VERIFIED`/`UNKNOWN` — unchanged, out of scope here.
- No trusted timestamp source — `close_evidence` stays owner-gated rather than time-windowed (§17).
- `WEBPAGE_LOAD_FAILED` exception-catching remains unverified and deliberately unused (§7) — a future stage could revisit this if it becomes genuinely important and is properly live-verified first.
- `MAX_FROZEN_CONTENT_PER_CASE = 65536` is provisional, based on single-source Stage 6a data, not multi-evidence live stress data (§11).
- No mechanism yet exists for a fork/root whose case was aborted to "try again" with a fresh case under the same fork/root — `Fork.status`/`RootProposal.envelope_status` are untouched by `abort_case` by design (staying minimal, avoiding overreach into finalization). A stuck fork after abort has no automatic recovery path in V1; this is an accepted, documented gap for a later stage.
- `close_evidence`'s owner-only gate means a case with only community evidence and an unresponsive fork creator cannot be closed at all — a liveness gap symmetric to the one griefing-mitigation (§18) solves on the *seal* side, but not addressed on the *close* side in V1.

## 27. Stage 7 handoff

Stage 7 (semantic adjudication, not started) can rely on:

- `Case.case_fingerprint` uniquely and completely identifying one frozen adjudication input (target identity + membership + evidence content, all immutable).
- `Evidence.frozen_content` as the exact, permanent text to reason over — never a live refetch.
- `Evidence.retrieval_status` distinguishing usable (`RETRIEVAL_FETCHED`) from resolved-but-unusable (`RETRIEVAL_UNUSABLE_SHORT`) evidence, with neither carrying an implicit semantic verdict.
- `RootProposal.web_content_fingerprint` as a narrow, honest signal (may legitimately be empty).
- The atomicity guarantee that `CASE_CASE_FROZEN` is truly terminal and complete — no partial evidence, no partial fingerprint, ever.
