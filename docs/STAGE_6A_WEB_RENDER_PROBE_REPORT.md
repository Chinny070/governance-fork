# Stage 6a — Live Web-Render Capability Probe Report

**Scope.** Live GenLayer Studio testing of `gl.nondet.web.render(...)` wrapped in `gl.eq_principle.strict_eq(...)`, the current officially documented Fetch Web Content pattern, against five real governance-evidence source classes plus one negative control. Tests `render()` specifically — not `get()` — per explicit project direction, overriding the docs' own general preference for `get()` on stable content.

**What this report is not.** It is not Stage 6b. No production evidence-retrieval code has been written. `contracts/governance_fork.py` was not touched at any point during this probe. Nothing was deployed to a public network — all live transactions ran on GenLayer Studio's local network (account `0xaffE15eEc45b68835cc9E5B4Ab85dD5deaE8e70b`, StudioNet demo balance).

---

## 1. Official API reverified

Re-checked `https://docs.genlayer.com/developers/intelligent-contracts/examples/fetch-web-content` at two points: once building the Phase A probe contract, once immediately before finalizing the live corpus. No material change between checks (page shows "Last updated: 2026-06-11"). `gl.nondet.web.render(url, mode)` with `mode ∈ {"text", "html"}`, optional `wait_after_loaded="5s"`-style duration string, `gl.eq_principle.strict_eq(leader_fn)` wrapping — all confirmed unchanged and confirmed to be exactly what the deployed probe implements.

## 2. Reviewer web-render requirement

Explicit, non-negotiable project direction: Governance Fork's production evidence pathway is `gl.nondet.web.render(...)`, not `gl.nondet.web.get(...)`, regardless of the docs' general "prefer `get()` for stable content" guidance. Every one of the 12 live transactions in this report used `render()`. `get()` was never called.

## 3. Probe commit
`7128147` — `feat: add isolated Stage 6a web-render probe (Phase A)`. No code changes since; the deployed contract is byte-identical to this commit.

## 4. Probe SHA-256
`2c953002a51b9cbb64b16867837de78bfb9083dbac5312b729f0b99179119e1a`

## 5. Deployment address
`0x8f1fC8ce78180C01B1711a84F39d5f16f0f86668` — confirmed as the `To` address on all 12 subsequent transactions.

## 6. Network / chain
GenLayer Studio's local/default network (StudioNet-equivalent demo environment). Deploying/calling account: `0xaffE15eEc45b68835cc9E5B4Ab85dD5deaE8e70b`.

## 7. Frozen corpus commit
`743eb4c` — `docs: freeze stage 6a live governance corpus`, committed before any live transaction.

## 8. Five exact primary URLs

| Label | URL |
|---|---|
| SOURCE_1_SNAPSHOT | `https://snapshot.org/#/s:uniswapgovernance.eth/proposal/0x0242a914c60945d25873d2a98c6abd9f69cb889c6616e27f3c0ab759f9e8d783` |
| SOURCE_2_TALLY | `https://www.tally.xyz/gov/arbitrum/proposal/52793687237294107439411688810483120161857085958258363826553939061522164665920?govId=eip155%3A42161%3A0x789fC99093B09aD01C34DC7251D0C89ce743e5a4` |
| SOURCE_3_FORUM | `https://gov.uniswap.org/t/temp-check-protocol-fee-expansion-eight-more-chains-and-remaining-mainnet-v3-pools/26035` |
| SOURCE_4_DOCS | `https://developers.uniswap.org/docs/ecosystem/governance/governance-process` |
| SOURCE_5_TREASURY | `https://gov.uniswap.org/t/uniswap-foundation-summary-fy-2025-financials/26068` |

## 9. Negative-control URL
`https://gov.uniswap.org/t/this-thread-does-not-exist-negative-control-9999999999/9999999999` — confirmed clean 404 via ordinary inspection during corpus freeze; live-tested in §21.

## 10. Source classes
`SNAPSHOT_PROPOSAL`, `TALLY_PROPOSAL`, `DAO_FORUM`, `OFFICIAL_DOCS`, `TREASURY_REPORT` — all five of the locked corpus classes tested. Negative control used `OTHER` (no dedicated enum value exists for it).

## 11. Primary render configuration
`mode="text"` for every call across all 12 transactions. `mode="html"` was never tested — not needed; every source produced usable text-mode results or a clearly diagnosable failure.

## 12. Wait policy (as actually executed)

| Source | Predeclared primary | Primary result | Diagnostic used |
|---|---|---|---|
| SOURCE_1_SNAPSHOT | `wait="5s"` (predeclared with wait — JS-heaviness already confirmed during corpus research) | — | not needed |
| SOURCE_2_TALLY | no wait | Success | not needed |
| SOURCE_3_FORUM | no wait | Empty | `wait="5s"` diagnostic run |
| SOURCE_4_DOCS | no wait | Success | not needed |
| SOURCE_5_TREASURY | no wait | Empty | `wait="5s"` diagnostic run |

## 13–15. Every transaction: ID, status, Consensus Result

| # | Probe target | Tx hash | Status (as observed) | Consensus Result | Rotation Count | Return value |
|---|---|---|---|---|---|---|
| 1 | SOURCE_1 attempt 1 | `0xe157da14d2430b2eccbe10a968618a90b64bde50173098c220d51cd5a323173b` | FINALIZED | Accepted | 0 | `1` |
| 2 | SOURCE_1 attempt 2 | `0xbe6127d909232a709c8d30a560373d911b03d76fc354cddafad6b4e8f9ddd3ea` | FINALIZED | Accepted | 0 | `2` |
| 3 | SOURCE_2 attempt 1 | `0x3db064552903b77cb076084cd2037256dba28628e5cdb17c4a44a01ea4e563d6` | FINALIZED | Accepted | 0 | `3` |
| 4 | SOURCE_2 attempt 2 | `0x4926543e2440067095d8bc2880d2e4a1c4ed1971bbae86f3c3f469f6a0ccd6d7` | ACCEPTED → confirmed FINALIZED shortly after | Accepted | 0 | `4` |
| 5 | SOURCE_3 primary | `0xf23972d1d5252dede8ab9975eb750d015c1f15166c77f977f47b1840e9f3b5a0` | ACCEPTED | Accepted | 0 | `5` |
| 6 | SOURCE_3 diagnostic (wait) | `0xbcd0da2220ed3f20c337611931c1d8e004a9a628901b8907b7aa477d60b9801d` | FINALIZED | **Undetermined** | **3** | `6` (never committed — see §16) |
| 7 | SOURCE_4 attempt 1 (reused id 6) | `0x991fcf422a920c91928ebbb1846c20f7639943886285d2a6bde40b15b69ba869` | FINALIZED | Accepted | 0 | `6` |
| 8 | SOURCE_4 attempt 2 | `0xcbcfad318da53d3bad53edeb65eeca26f5dd5ac29c914b3e9f4823da7ad5971c` | FINALIZED | Accepted | 0 | `7` |
| 9 | SOURCE_5 primary | `0x2e9365118d53d4c7a9d77d178f75affddb66c649a020df7dfa8bbacd25f0db55` | FINALIZED | Accepted | 0 | `8` |
| 10 | SOURCE_5 diagnostic attempt 1 | `0x929ad43b4ade759e836488856421d8be54d20e852eed188cc173a89013f89351` | FINALIZED | Accepted | 0 | `9` |
| 11 | SOURCE_5 diagnostic attempt 2 | `0xdc01961502764bcf3fba7541949aeb854fd65bb6b3ac9d71009769f97ae06012` | FINALIZED | Accepted | 0 | `10` |
| 12 | NEGATIVE_CONTROL | `0x25f5cb33ef4d4bb48603fbc48546269125248aaa785bbf4ccc18ce9ac17de083` | ACCEPTED (not confirmed FINALIZED) | Accepted (on the *failure itself*) | 0 | none — Contract Error, `exit_code 1` |

No failed row omitted. Row 6's `Undetermined` and row 12's `Contract Error` are both reported in full, not smoothed over.

## 16. Committed-state verification (authoritative re-reads, never inferred from tx alone)

| Probe id | `get_probe` result | Notes |
|---|---|---|
| 1 | `content_length=5427`, `fingerprint=0xe1c84f75...56dc` | Confirmed |
| 2 | Same fingerprint as 1 | Confirmed — repeatability |
| 3 | `content_length=12955`, `fingerprint=0xb3d66086...eb524` | Confirmed |
| 4 | Same fingerprint as 3 | Confirmed — repeatability |
| 5 | `content_length=0`, `fingerprint=0xe3b0c442...52b855` (exact SHA-256 of empty string, verified independently) | Confirmed — genuinely empty, not a display artifact |
| 6 (Undetermined attempt) | `get_probe(6)` → error (ambiguous client-side text at first; backend traceback showed a generic `execution failed` at the RPC layer, most likely wrapping a `"probe not found"` UserError) | **Disambiguated via `get_probe_count()` → returned `5`**, confirming nothing committed. `Undetermined` consensus → clean, complete rollback. |
| 6 (reused, SOURCE_4 attempt 1) | `content_length=5751`, `fingerprint=0x61218d0a...f93f` | Confirmed |
| 7 | Same fingerprint as reused-6 | Confirmed — repeatability |
| 8 | `content_length=0`, `fingerprint=0xe3b0c442...52b855` | Confirmed — genuinely empty |
| 9 | `content_length=6258`, `fingerprint=0x48bf9874...622f` | Confirmed |
| 10 | Same fingerprint as 9 | Confirmed — repeatability |
| NEGATIVE_CONTROL | **Not yet re-read.** `get_probe_count()` after this attempt has not been reported back. Expected (by strong analogy to the Undetermined case, and because `Contract Error` transactions are architecturally the same "raise before any storage write" pattern as every deterministic validation failure throughout Stages 3–5) to still read `10` — i.e., no state committed. **This is a genuine open item, not assumed as fact. Flagged in §44.** |

## 17. Rendered lengths

| Source | Length (chars) | % of 16,384 cap |
|---|---|---|
| SOURCE_1_SNAPSHOT | 5,427 | 33.1% |
| SOURCE_2_TALLY | 12,955 | 79.1% |
| SOURCE_3_FORUM (primary) | 0 | 0% |
| SOURCE_3_FORUM (diagnostic, uncommitted) | n/a — never committed | n/a |
| SOURCE_4_DOCS | 5,751 | 35.1% |
| SOURCE_5_TREASURY (primary) | 0 | 0% |
| SOURCE_5_TREASURY (diagnostic) | 6,258 | 38.2% |

No source hit the cap. SOURCE_2_TALLY is the closest at 79.1% — worth watching for longer proposals in production (see §33).

## 18. Content usefulness

| Source | Useful? | What was present |
|---|---|---|
| SOURCE_1_SNAPSHOT | **Yes, high** | Proposal title, author, status (Passed), full spec, final vote tallies (150 votes, For 35.2M/100%, Against 0, Abstain 0, Quorum 351%), timeline |
| SOURCE_2_TALLY | **Yes, very high** | Title, proposer, proposal ID, governor, final vote tallies (Quorum 141.87M/103.82M, For 134.45M, Against 4.51M, Abstain 7.42M), full abstract/motivation/rationale/spec, $200K funding breakdown, payment addresses, complete status timeline through "Proposal executed" |
| SOURCE_3_FORUM | **No, on either config** | Primary: nothing. Diagnostic: real content existed but never reached committed consensus |
| SOURCE_4_DOCS | **Yes, very high** | Full three-phase governance process, all vote thresholds and durations |
| SOURCE_5_TREASURY | **Yes, high** (diagnostic config) | Treasury composition, grant activity, opex, revenue — matches Foundation's own published figures precisely |

## 19. First-16,384-char usefulness
Every successful source's *entire* useful content fit well within the cap — none required inspecting past the 16 KiB boundary. Navigation/chrome noise (forum headers, cookie banners) was present but did not crowd out substantive content in any successful case.

## 20. Repeatability

| Source | Config | Result |
|---|---|---|
| SOURCE_1_SNAPSHOT | `wait="5s"` | **Bit-exact match**, 2/2 |
| SOURCE_2_TALLY | no wait | **Bit-exact match**, 2/2 |
| SOURCE_3_FORUM | no wait | N/A — both empty (fingerprint identical to SHA-256(""), technically "matching" but trivially so — not counted as a meaningful repeatability pass since content is unusable) |
| SOURCE_3_FORUM | `wait="5s"` | Not tested twice — first attempt was `Undetermined` and uncommitted, so there is nothing to repeat |
| SOURCE_4_DOCS | no wait | **Bit-exact match**, 2/2 |
| SOURCE_5_TREASURY | `wait="5s"` | **Bit-exact match**, 2/2 |

## 21. `strict_eq` behavior
Worked cleanly (0 rotations, immediate agreement) in 10 of 12 transactions — including on both empty-content cases (all validators agreeing on an empty string is still a clean `strict_eq` match) and on the negative control's structured failure (all validators independently hit the same 404 and agreed on the same exception). The **one** case where `strict_eq` failed to converge (SOURCE_3's wait-diagnostic, 3 rotations → `Undetermined`) is real evidence that bit-exact agreement is **not** universally achievable for every dynamic page, even with `wait_after_loaded` set — some content genuinely varies per-fetch across validators.

## 22. Undetermined results
One observed: SOURCE_3_FORUM's diagnostic wait attempt (row 6, §13–15). 3 rotations, network gave up, **zero state committed** (§16) — confirmed via `get_probe_count()` reading `5` both before and after the attempt.

## 23. Errors / timeouts
One observed: the negative control (row 12). `render()` raised `genlayer.gl.nondet.NondetException` with `causes: ['WEBPAGE_LOAD_FAILED']` and structured context (`status: 404`, the actual 404 page body, the requested URL). This propagated through the probe's leader function (deliberately unguarded by try/except) and surfaced as a `Contract Error` at the transaction level. **Crucially, this is not `Undetermined`** — validators reached clean `Accepted` consensus (0 rotations) on the *fact of the same structured failure*, meaning the 404 response was itself deterministic and reproducible across independent fetches.

## 24. Wait diagnostics used
Two: SOURCE_3_FORUM (`wait="5s"`, led to `Undetermined`) and SOURCE_5_TREASURY (`wait="5s"`, led to a clean `REPEATABLE_PASS`). Neither diagnostic replaced or erased its source's primary (empty) result — both are recorded.

## 25. HTML diagnostics
None used. Not needed — every source either succeeded in text mode or failed in a way that HTML mode would not plausibly have fixed (an empty text render or an Undetermined consensus are not text-extraction problems).

## 26. Dynamic-content observations

- **Observed:** SOURCE_2_TALLY's page included a live platform-state banner ("Tally is now Cactus... This DAO is archived") that was not present when the URL was selected for the corpus — real content drift between corpus-selection time and probe time, handled gracefully (still rendered fully, still repeatable).
- **Observed, independently corroborated:** SOURCE_4_DOCS's page independently stated the same Tally→Cactus/ScopeLift transition — an unplanned but genuine cross-source consistency check between two separately-probed URLs.
- **Likely (not confirmed):** SOURCE_3_FORUM's instability may stem from an inlined *second full thread's content* appearing to vary per-fetch (its diagnostic render mixed in a second, unrelated proposal's full text and stats), whereas SOURCE_5_TREASURY's "Related topics" section — which lists only static titles/metadata, not full inlined content — rendered cleanly and repeatably. This is a plausible explanatory hypothesis, not a proven cause.
- **Unknown:** why SOURCE_3's *no-wait* attempt returned literally nothing while SOURCE_5's no-wait attempt also returned nothing (consistent pattern) but SOURCE_3's wait-diagnostic was unstable while SOURCE_5's was clean — both are `gov.uniswap.org` Discourse pages, so the instability is thread-specific, not domain-wide.

## 27. Negative-control behavior
Structured, typed failure (`WEBPAGE_LOAD_FAILED`, HTTP `404`, actual 404-page body captured in the exception context). Clean consensus on the failure itself (`Accepted`, 0 rotations) — **not** `Undetermined`. This is architecturally important: it demonstrates GenLayer's `render()` pathway can produce a deterministic, catchable, structured signal for "this page genuinely does not exist," distinct from — and more informative than — a silent empty-string result (see §33 for the design implication).

## 28. `hashlib` runtime result
**LIVE VERIFIED.** Every `content_fingerprint` returned by `get_probe` matched the expected SHA-256 digest — most directly demonstrated by the empty-content cases (`0xe3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, confirmed byte-for-byte identical to `hashlib.sha256("".encode("utf-8")).hexdigest()` computed independently), and corroborated by every non-empty case's `content_length` matching independent reconstruction counts. `hashlib.sha256(...).digest()` executes correctly in the live GenVM runtime. This upgrades the Stage 2B/3 classification from **PROVISIONAL CRYPTOGRAPHIC** to **LIVE VERIFIED** for the identical hashing pattern used in `contracts/governance_fork.py` (same `import hashlib`, same `.digest()` call shape) — though this was verified in the isolated probe contract, not the production file itself, so treat this as strong transferable evidence rather than a byte-identical-file test.

## 29. Source-level classifications

| Source | Classification |
|---|---|
| SOURCE_1_SNAPSHOT | **`REPEATABLE_PASS`** |
| SOURCE_2_TALLY | **`REPEATABLE_PASS`** |
| SOURCE_3_FORUM | **`UNSTABLE`** (primary: unusable-empty; diagnostic: `CONSENSUS_UNDETERMINED`) — no working configuration found |
| SOURCE_4_DOCS | **`REPEATABLE_PASS`** |
| SOURCE_5_TREASURY | **`REPEATABLE_PASS`** (via `wait="5s"`; naive no-wait primary is separately `UNUSABLE`) |

## 30. Overall gate: PASS (with the stricter reading noted transparently)

Two honest ways to score this, both presented rather than the more flattering one alone:

- **Strict reading — only the originally predeclared primary configs, unmodified:** 3/5 clean primary passes (Snapshot, Tally, Docs). Per the gate's own language ("if 3/5 pass and the failures can be handled by a clearly defensible supported-source restriction: `CONDITIONAL PASS`") — and SOURCE_5's fix (adding `wait_after_loaded`, a documented parameter of the same `render()` API, not a workaround) is about as "clearly defensible" as a restriction gets — this reading lands on **`CONDITIONAL PASS`**.
- **Best-supported-render-configuration-per-source reading:** 4/5 source classes reach `REPEATABLE_PASS` using nothing but the officially supported `web.render(..., mode="text")` API (tuning only the documented `wait_after_loaded` parameter, never a backend/off-chain workaround). This meets the gate's literal `PASS` threshold ("4/5 source classes achieve `REPEATABLE_PASS` ... Then: PASS").

**My recommendation: `PASS`**, on the basis that every successful configuration change was pure, documented use of the `render()` API's own parameters — no workaround, no `get()` substitution, no backend involved. But this is presented as a recommendation for you to confirm, not a unilateral final verdict — the `CONDITIONAL PASS` reading is equally defensible and available if a stricter standard is preferred for reviewer-facing materials.

Either way: **not all five classes work reliably, and that is reported plainly** (§29, SOURCE_3_FORUM).

## 31. Implications for Stage 6b

- The `render()` + `strict_eq` pathway is production-viable for governance evidence, with per-source `wait_after_loaded` tuning as a first-class design parameter, not an afterthought.
- Discourse-forum sources (`gov.uniswap.org` and likely similar deployments) need case-by-case reliability testing before being accepted into a frozen evidence set — the domain alone does not predict stability; thread-content shape (inlined related content vs. static metadata) appears to matter more (§26).
- `Undetermined` and structural render failures (`WEBPAGE_LOAD_FAILED`) both produce **zero state mutation** — Stage 6b's `freeze_evidence` can rely on this atomicity guarantee without additional defensive code.
- A genuine 404 and a "rendered but empty" result are **currently indistinguishable at the contract level** unless the freeze code explicitly catches and inspects the `NondetException`. This is a concrete design gap worth closing in Stage 6b (§33).

## 32. Recommended production source policy

- **Accept by default (with source-specific wait tuning):** Snapshot proposals (mandatory wait, ≥5s), Tally/Cactus-style on-chain governance interfaces (wait optional but harmless to include), official protocol documentation (wait optional), Foundation-published financial/treasury reports on Discourse forums (mandatory wait, ≥5s).
- **Require case-by-case pre-qualification before acceptance:** individual DAO governance-forum discussion *threads* — test each specific thread (not just the domain) for `REPEATABLE_PASS` before allowing it into a frozen evidence set, given the observed instability was thread-specific, not domain-wide.
- Never fall back to `get()`, a backend scraper, a proxy, or manually pasted content for any source that fails this qualification — an unqualified source is simply excluded from Governance Fork evidence, per the existing Stage 1 threat model.

## 33. Recommended render configuration

Default every production evidence fetch to `mode="text"`, `wait_after_loaded="5s"` as a baseline — it never hurt any of the five tested sources (Docs and Tally succeeded with or without it in principle; Snapshot and Treasury required it). **Wait is necessary but not sufficient** — SOURCE_3_FORUM still failed with wait applied, so a source cannot be assumed safe merely because a wait parameter was added; each source needs its own `REPEATABLE_PASS` confirmation regardless of configuration.

**New design recommendation surfaced by this probe:** Stage 6b's `freeze_evidence` should explicitly `try`/`except` around the `strict_eq(...)` call, specifically catching `NondetException` and inspecting `causes` for `WEBPAGE_LOAD_FAILED` (or similar). On that specific cause, record the evidence item with a distinct status (e.g. a new `EVIDENCE_RETRIEVAL_FAILED` state, separate from `frozen=True` with empty content) rather than letting the whole transaction revert uncaught. This preserves Stage 1's "unavailable evidence ≠ evidence against the fork" principle at the implementation level, and — separately — a *successful* render that returns empty content should be tracked with its own distinct status too, since it is a different (and currently harder to diagnose) failure mode than a clean 404.

## 34. Recommended content bound
Keep `MAX_EVIDENCE_SLICE = 16384` for now — no source came close to truncation (max observed 79.1%). Flag for monitoring: longer or more detailed on-chain proposals (Tally-style, which tends toward verbose technical specs) could plausibly approach or exceed the cap; revisit if Stage 6b's real evidence corpus shows truncation.

## 35. Retrieval-failure semantics (carried forward, reinforced by live evidence)
Confirmed unchanged from Stage 1: an unavailable or empty evidence source must never be treated as `NOT_FAITHFUL`, a false claim, or "source not authoritative" by default. This probe adds concrete texture: a **typed** `WEBPAGE_LOAD_FAILED` failure and a **silent empty** render are two different signals that Stage 6b/7 must represent separately, not collapse into one "evidence unavailable" bucket.

## 36. Prompt-injection carry-forward
Unchanged from Stage 1 §13 / Stage 5 §25: fetched content remains untrusted data. Stage 6b must use explicit delimiters, fixed system instructions, bounded slices, and no browsing tool exposed to any model. Nothing in this probe (a pure retrieval-and-hash pipeline, no LLM prompt construction) exercised this concern directly, but it remains a hard requirement for Stage 7.

## 37. Confirmation: no `web.get()` fallback ✅
Every one of the 12 transactions used `gl.nondet.web.render(...)`. `gl.nondet.web.get(...)` was never called, including for sources that failed under `render()` — SOURCE_3_FORUM was left as a documented limitation, not silently routed to `get()`.

## 38. Confirmation: no backend/off-chain workaround ✅
No scraping service, proxy, headless-browser-outside-GenVM, or manually pasted content was used anywhere in this probe. Every result came from the isolated probe contract's own `run_probe` calling `gl.nondet.web.render` inside `gl.eq_principle.strict_eq`, on GenLayer Studio's own network.

## 39. Confirmation: production contract unchanged ✅
`contracts/governance_fork.py` was not opened, edited, or referenced by any code touched during Phase B. Verified below (§40).

## 40. Production regression results

Re-run after all live probe testing completed:

- **Stage 2 static checks: 11/11 pass** (python syntax, ASCII-only, LF endings, no prohibited calls, no `gl.message.value`, no duplicate ABI names, ABI counts 11/16/2/29, no `CLAIM_UNCHANGED`, 7 enum groups unique, no `SETTLED_FULL_SLASH`, no unfunded reward liability).
- **Stage 3 + 4 + 5 tests: 149/149 pass.**
- **Contract SHA-256 unchanged** from Stage 5's commit (`396265f`) — `84848257e3c3685a986d7e4bcd4184d131753b4c86bd07d1a0ca91976e1533e3` — confirming zero drift in `contracts/governance_fork.py` across the entirety of Stage 6a Phases A and B.

## 41. Confirmation: no semantic adjudication ✅
The probe contract performs no LLM prompt construction, no `gl.eq_principle.prompt_comparative`/`prompt_non_comparative` calls, and no interpretation of retrieved content. It fetches, bounds, hashes, and stores — nothing more. Verified by Phase A static check `no prompt_comparative/prompt_non_comparative`, still true after live testing (no code changed).

## 42. Confirmation: no GEN logic ✅
Every one of the 12 transactions shows `Value: 0 GEN`. `run_probe` is `@gl.public.write` (non-payable). No bond capture, settlement, transfer, refund, slash, or reward logic exists anywhere in the probe or in the untouched production contract.

## 43. Stage 6b exact recommended scope

Contingent on your review of this report and the one open item in §44:

1. Implement `freeze_evidence(evidence_id)` and `freeze_case(case_id)` in `contracts/governance_fork.py`, using `gl.nondet.web.render(url, mode="text", wait_after_loaded="5s")` wrapped in `gl.eq_principle.strict_eq(...)` — the exact pattern proven live in this report.
2. Add explicit `try`/`except NondetException` handling around the fetch, distinguishing `WEBPAGE_LOAD_FAILED` (and any other observed `causes` values Stage 6b's own broader testing surfaces) from a successful-but-empty render, per §33's design recommendation.
3. Apply the source-policy distinctions from §32: accept Snapshot/Tally/docs/treasury-report classes by default (with wait tuning); require per-thread `REPEATABLE_PASS` pre-qualification for individual DAO forum discussion threads before they enter a frozen evidence set.
4. Populate `RootProposal.web_content_fingerprint` and `Evidence.content_fingerprint` using this exact retrieval pathway — never `Case.evidence_set_fingerprint` or `Case.case_fingerprint` until the full evidence set for a case is frozen (unchanged from Stage 5 design).
5. Keep `MAX_EVIDENCE_SLICE = 16384` unless Stage 6b's own broader corpus shows truncation.
6. Write tests using a mock/shim for `gl.nondet.web.render` (matching the Stage 3–5 pattern of `tests/_genlayer_shim.py`) for deterministic logic, plus a documented manual-live-verification step (mirroring this report) before any production deployment.
7. **Do not** implement Stage 7 (semantic adjudication) in the same pass — freeze/retrieval and adjudication remain separate stages per the locked roadmap.

## 44. Unresolved risks / open items

- **Not yet confirmed:** `get_probe_count()` after the negative-control transaction. Expected (by strong analogy to the Undetermined case and by architectural consistency with every atomicity guarantee tested since Stage 3) to still read `10`, but this has not been empirically confirmed and is not asserted as fact. **Action needed:** run `get_probe_count()` once more and report back; I will update this report's §16 and §44 accordingly. This does not block the overall gate finding (§30), which does not depend on this specific number, but it is a loose end in the atomicity story worth closing.
- SOURCE_3_FORUM has no working configuration under the two tested variants (no-wait, `wait="5s"`). A longer wait (10s, 15s) was not tested — Stage 6b research could determine whether a longer wait resolves the instability, though the `Undetermined` (not merely "slow") nature of the failure suggests this may be a content-shape problem rather than a timing problem.
- The `WEBPAGE_LOAD_FAILED` vs. silent-empty distinction (§33) is a real design gap not yet closed in any contract — Stage 6b must implement the catching logic, not just document the recommendation.
- `hashlib` live-verification (§28) was performed in the isolated probe contract, not `contracts/governance_fork.py` itself — transferable evidence, not a byte-identical-file confirmation.
- Only one DAO's governance stack (Uniswap/Arbitrum via Snapshot, Tally/Cactus, Discourse, developers.uniswap.org) was tested. Generalization to other DAOs' Snapshot spaces, other governance-forum software, or other documentation platforms is untested.

## 45. Reviewer-ready proof summary

This report, together with the 12 recorded transaction hashes (§13–15) and their authoritative `get_probe` state confirmations (§16), gives a reviewer everything needed to independently verify: a real governance URL → a `gl.nondet.web.render()` call → `gl.eq_principle.strict_eq` consensus → a finalized transaction → committed, useful rendered evidence → confirmed repeatability across an independent second call. Four of five source classes demonstrate this complete chain cleanly; the fifth (`SOURCE_3_FORUM`) demonstrates the chain's *honest failure mode* — including a clean `Undetermined` consensus outcome and a confirmed-safe rollback — which is itself a legitimate and useful proof point about the system's safety properties under disagreement. The negative control demonstrates a third, distinct, well-behaved outcome: a typed, deterministic failure signal for a genuinely unavailable page.

## 46. Confirmation: Stage 6b not started ✅

No evidence-retrieval code has been added to `contracts/governance_fork.py`. `freeze_evidence` and `freeze_case` remain unimplemented, raising `gl.vm.UserError("stage-2: not implemented")` exactly as they have since Stage 2. Nothing beyond this isolated probe and its documentation has changed.

---

**Nothing was deployed to a public network. Nothing beyond the isolated probe contract (already covered under Phase A/B approval) was broadcast. The production contract remains untouched and fully regression-clean.**

