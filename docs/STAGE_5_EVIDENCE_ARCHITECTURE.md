# Stage 5 — Community Evidence Architecture

**Scope.** The deterministic evidence architecture for FORK cases: a community-compatible bounded contribution model, a single canonical case per fork with reuse on subsequent submissions, provenance retention, corrected URL canonicalization (Stage 3 was too aggressive), per-case and per-contributor quotas enforced atomically per batch, and case allocation on first submission. Zero fetching, zero freeze, zero fingerprinting of external content.

**Explicitly not in scope.** Any `gl.nondet.*`; web retrieval; content fingerprinting from fetched pages; `Case.evidence_set_fingerprint` / `Case.case_fingerprint` sealing; freeze; semantic adjudication; native GEN reading / capture / refund / slash / reward; challenger reward source decision.

## 1. Why evidence is not creator-only

Governance Fork's purpose is community-facing: a wallet-free Proposal Tree, evidence that other people can inspect and challenge. If only `fork.creator` could submit evidence, the fork's own record would be inherently one-sided — GenLayer's semantic adjudicator would judge on a curated set, and challenges could only target defects in that set, not omissions of contrary evidence available in public.

The V1 model therefore accepts both **creator evidence** and **community evidence**, each bounded so that neither can dominate or grief the other:

- `CREATOR_EVIDENCE_CAP = 8` — the fork creator can submit up to 8 items.
- `COMMUNITY_EVIDENCE_CAP = 8` — the collective community can submit up to 8 items.
- `MAX_COMMUNITY_EVIDENCE_PER_CONTRIBUTOR = 2` — any single non-creator address can submit at most 2 items.
- `MAX_EVIDENCE_PER_CASE = 16` — total. Automatically `CREATOR_EVIDENCE_CAP + COMMUNITY_EVIDENCE_CAP`.
- `MAX_EVIDENCE_BATCH = 8` — a single call cannot submit more than this in one shot.

**Consequences:**

- Creator cannot fill the whole case: after 8, they hit `CREATOR_EVIDENCE_CAP`.
- Community cannot be starved: 8 slots reserved regardless of creator activity.
- No community contributor can monopolize the community reserve: 2 items per address caps the whole population at 8 items only if at least 4 distinct addresses participate.
- First-submitter cap capture: any single community submitter can only claim 2 of the 8 community slots; a rush of duplicate contributors is throttled by the per-contributor cap.
- Batch inflation: `MAX_EVIDENCE_BATCH = 8` prevents a single call from exceeding a caller's own reserve; the batch-atomic validation then enforces the tighter of the caller's quota, the case cap, and the per-contributor cap.

## 2. Contributor policy

Classification is derived from `gl.message.sender_address == fork.creator`. Caller-supplied contributor type is not accepted.

- **Creator submissions** consume the creator reserve up to `CREATOR_EVIDENCE_CAP`.
- **Community submissions** consume the community reserve up to `COMMUNITY_EVIDENCE_CAP` and the submitter's individual quota up to `MAX_COMMUNITY_EVIDENCE_PER_CONTRIBUTOR`.

No DAO membership required. No fork ownership required. No voting power created. Evidence contribution is provenance and challengeability, not governance authority.

## 3. Contributor counter storage

Two new maps:

```
fork_case_counters:      TreeMap[u256, CaseCounters]
    # case_id -> {creator_count: u32, community_count: u32}

fork_case_contrib_count: TreeMap[str, u32]
    # "<case_id>:<addr_hex>" -> per-contributor community count on that case
```

`CaseCounters` is a new `@allow_storage @dataclass`. Only populated for FORK cases; root-envelope cases do not touch it (their contributor rules differ).

The composite string key uses `":"` as separator. Address hex form is obtained via `gl.message.sender_address.as_hex` — the exact idiom used by the local reference contract (RealityLock). The decimal `case_id` and hex address cannot collide with each other or with each other's characters, so the split is unambiguous.

**No unbounded contributor list.** We do not maintain a per-case `DynArray[Address]` of contributors — the composite map key is enough for the O(1) per-contributor lookup we need. Duplicate detection over evidence URLs is an O(≤16) scan against `evidence_by_case[case_id]`, which is fine given the cap.

## 4. Case creation vs reuse

Every fork has at most one FORK case for its evidence lifecycle.

- **First submission** creates the case: allocates `case_id`, writes `Case(case_type = CASE_TYPE_FORK, target_id = fork_id, target_kind = TARGET_KIND_FORK, target_fingerprint = fork.body_fingerprint, evidence_ids = [], evidence_set_fingerprint = b"", adjudication_dimensions_version = ADJUDICATION_DIMENSIONS_VERSION_FORK, case_fingerprint = b"", state = CASE_OPEN, retry_count = 0, last_attempt_at = 0)`, initializes `fork_case_counters[case_id] = CaseCounters(0, 0)` and `evidence_by_case[case_id] = []`, points `fork.evidence_case_id` at it, and transitions `fork.status: FORK_DRAFT → FORK_EVIDENCE_OPEN`.
- **Subsequent submissions** reuse the same case: read `fork.evidence_case_id`, append to `evidence_by_case[case_id]`, update counters. Only permitted while `fork.status == FORK_EVIDENCE_OPEN`.

Any later transition (`FORK_EVIDENCE_FROZEN`, `FORK_ADJUDICATING`, `FORK_VERDICT_PROPOSED`, `FORK_CHALLENGE_WINDOW`, `FORK_CHALLENGE_OPEN`, `FORK_FINALIZED_*`) is a Stage 6+ concern; `submit_fork_evidence` rejects those.

## 5. Fork evidence lifecycle (Stage 5)

```
FORK_DRAFT
   │
   └─── first submit_fork_evidence ──►  FORK_EVIDENCE_OPEN
                                           │
                                           └── further submit_fork_evidence
                                                (reuses same case)
```

No later transition implemented in Stage 5. `freeze_evidence` and `freeze_case` still raise `gl.vm.UserError("stage-2: not implemented")` — they are deferred to Stage 6b alongside real web retrieval (Stage 6a probe gates that first).

## 6. Exact URL validation rules

Per-item, before mutation:

- `1 ≤ len(url) ≤ MAX_URL_LEN` (512).
- No `\n` or `\r` anywhere in the URL.
- Scheme must be `http://` or `https://` (case-insensitive prefix check).
- Non-empty host after scheme.
- All checks are deterministic and offline. No DNS, no HTTP, no redirect follow, no `robots.txt`, no backend, no probing.

Enforcement path: `_check_len` and `_reject_newline` before `_normalize_url` is called; `_normalize_url` itself raises on bad scheme and empty host.

## 7. URL canonicalization algorithm (Stage 5 correction)

Stage 3's `url.strip().lower()` was too aggressive — path and query may be case-sensitive and lowercasing them can merge distinct real resources. Stage 5 replaces it with:

```
trimmed          = url.strip()
scheme           = "https" if lowered starts "https://" else "http" if "http://" else UserError
rest             = trimmed after scheme prefix
fragment stripped: everything from "#" onward is dropped (never sent to server)
host_end         = first "/" or "?" in rest; host = rest[:host_end]; tail = rest[host_end:]
UserError if host is empty
return scheme + "://" + host.lower() + tail
```

Concrete behaviors (verified by `UrlCanonicalizationTests`):

| Input | Normalized |
|---|---|
| `HTTPS://x.com/foo` | `https://x.com/foo` |
| `https://Example.COM/Path` | `https://example.com/Path` |
| `https://x.com/FooBAR` | `https://x.com/FooBAR` (path case preserved) |
| `https://x.com/p?A=1&b=2` | `https://x.com/p?A=1&b=2` (query preserved) |
| `https://x.com/foo/` vs `https://x.com/foo` | **distinct** — trailing slash preserved |
| `https://x.com/p#section-1` | `https://x.com/p` (fragment dropped) |
| `ftp://x.com/foo` | UserError |
| `https:///foo` | UserError |

**Path case behavior.** Preserved. Two URLs differing only by path case are DIFFERENT resources and are NOT deduped (verified in Stage 3 test `test_distinct_path_case_NOT_deduped`).

**Query case / order behavior.** Preserved verbatim. Two URLs with re-ordered query parameters (e.g. `?a=1&b=2` vs `?b=2&a=1`) are treated as distinct at Stage 5. This is deliberately conservative — merging them would require query semantics we cannot deterministically establish without a fetch. Some redundant submissions may result; the cap prevents damage.

**Fragment behavior.** Dropped. Fragments identify a section of an already-retrieved resource and are not sent to the server. Two URLs differing only by fragment are the same resource for evidence purposes.

**Trailing slash behavior.** Preserved. `https://x.com/foo/` and `https://x.com/foo` are NOT merged — they may address different real resources (index page vs a `foo` file). Preferring to accept a duplicate over silently merging.

**Port, userinfo, IPv6, unicode host.** Ports are kept as-is (part of `host_part` and lowercased with the host). Userinfo (`user:pass@host`) would be lowercased along with the host — rare in governance URLs, documented as a known-quirk limitation. IPv6 literal hosts `[::1]` are handled by the `/` and `?` scan. Unicode host normalization (IDN → punycode) is NOT performed; callers are expected to submit ASCII-normalized URLs (Stage 5 keeps source ASCII-only regardless).

## 8. Duplicate evidence behavior

Within a single case:

- The same normalized URL may exist **at most once**, regardless of contributor (creator's URL cannot be re-submitted by a community contributor, and vice versa — verified).
- Duplicate detection runs at two levels: within the incoming batch, and against every URL already registered on the case.
- Complexity: O(n) build of the case-URL set (n ≤ 16) once per call, plus O(1) checks per new item. Deliberately no global URL index.

The later contributor cannot claim a slot by rewriting their `authority_claim` or `relevance_claim` on the same source — the source itself is deduped. Their input is preserved for future challenges: any concerns can be raised as a challenge (Stage 9) with `CG_FORK_SOURCE_AUTHORITY_ERROR` or similar.

## 9. Evidence class enum

Retained unchanged from Stage 2: `OFFICIAL_GOVERNANCE`, `OFFICIAL_DOCUMENTATION`, `OFFICIAL_TREASURY`, `FINALIZED_DECISION`, `GOVERNANCE_DISCUSSION`, `IMPLEMENTATION_SPEC`, `AUDIT`, `THIRD_PARTY_ANALYSIS`. These are **submitter-declared** source-type labels. **A submitter selecting `OFFICIAL_GOVERNANCE` does NOT prove the page is official.** That is Stage 7 adjudicator work (`SOURCE_AUTHORITY` finding).

## 10. `relevance_claim` and `authority_claim` semantics

Both are **submitter claims**, not verified state. Stored verbatim (bounded lengths, no newlines) and made available to Stage 7 adjudication. Nothing in Stage 5 flags an evidence record as `verified` or `trusted`. Verified by test (`test_claims_stored_verbatim_no_trust_flag`).

## 11. Temporal marker semantics

`Evidence.temporal_marker` is a submitter-supplied text field. Runtime timestamp is not confirmed available for v0.2.16; even if it were, the timestamp we could record would be "submission time," not "the referenced source's publication time." So the marker stays a bounded caller claim — treated as evidence by Stage 7's `TEMPORAL_RELEVANCE` dimension, not as a proven fact.

## 12. `Evidence.content_fingerprint` behavior

**Stays `b""` for every Stage 5 evidence record.** That field's semantics are precisely defined for Stage 6b: SHA-256 of the actual page content retrieved via the official GenLayer Fetch Web Content pattern, wrapped in `gl.eq_principle.strict_eq`. Not the SHA of the URL, or of metadata, or of claims. Metadata identity and content identity are separate concepts; Stage 5 handles only metadata identity.

## 13. `Case.evidence_set_fingerprint` behavior

Stays `b""` while the case is `CASE_OPEN`. The final ordered evidence membership is not known until freeze; sealing a fingerprint over mutable state would be misleading. Stage 6b or Stage 7 (whichever lands the freeze step) will populate it as SHA-256 of the ordered evidence IDs plus each item's individual `content_fingerprint`.

## 14. `Case.case_fingerprint` behavior

Stays `b""` while the case is `CASE_OPEN`. Same rationale: sealing a fingerprint over a still-mutating case would be a lie. The case fingerprint binds envelope + delta + evidence set together at freeze time (Stage 6b/7).

## 15. Evidence ID ordering

`evidence_by_case[case_id]` preserves **submission order**. IDs are appended, never sorted. This is a record of what happened, not a priority ranking. Stage 7 adjudication reads all evidence uniformly; no evidence item is treated as first-class merely for being submitted first.

The later `Case.evidence_set_fingerprint` will bind the ordered evidence IDs at freeze, so the frozen order is what any later verdict cites.

## 16. Atomicity

Every write is validated in full before any storage mutation. The entire batch is either accepted or rejected:

- Case not yet created + malformed second item → no case allocated (`test_invalid_second_item_causes_zero_allocation_on_first_submission`).
- Batch that would exceed any cap → zero allocation (`test_cap_breach_zero_allocation`).
- Duplicate against existing case → zero allocation (`test_duplicate_across_case_zero_allocation`).
- Per-contributor quota breach → zero counter increment (`test_contributor_quota_breach_no_counter_increment`).

The GenLayer runtime's per-tx atomicity guarantees no orphan on `raise gl.vm.UserError(...)`. Under CPython (test env) we assert directly by checking `next_case_id`, `next_evidence_id`, `fork.status`, and `fork.evidence_case_id` all unchanged.

## 17. Pause behavior

`submit_fork_evidence` respects `self.paused`. When paused, new evidence submissions refuse. Later withdrawal / settlement paths (Stage 10) will be structured so that pause does not trap them; Stage 5 does not implement any such trap.

## 18. Root-envelope regression impact

The corrected `_normalize_url` is shared between `submit_root_envelope` (Stage 3) and `submit_fork_evidence` (Stage 5). All Stage 3 evidence flows continue to work; one Stage 3 test's URL pair had to be updated to reflect the corrected semantics (only scheme + host case-normalized), and a new Stage 3 test asserts that path-case-distinct URLs are correctly NOT deduped. 50 → 51 Stage 3 tests, all passing.

Root-envelope contributor policy is unchanged: still all-in-one at envelope submission, no per-contributor community quota. The community model applies only to FORK cases.

## 19. Stage 4 FAITHFUL gate — unchanged

Confirmed by `FaithfulGateUnchangedTests`: `create_fork` still refuses on `ENVELOPE_NOT_SUBMITTED` (and every other non-`ENVELOPE_FAITHFUL` status). No production bypass. The Stage 5 test harness that manipulates `envelope_status` in-process only never touches the contract source.

## 20. ABI

**No change.** 29 methods total (11 write + 2 admin + 16 view). `submit_fork_evidence` signature unchanged from Stage 2 scaffold: `submit_fork_evidence(fork_id, evidence_urls, evidence_classes, relevance_claims, authority_claims, temporal_markers) -> u256`. No new public views for creator/community counters — integrators can compute them by walking `list_evidence_of_case` + inspecting each `Evidence.submitter`. If Explorer usage reveals genuine value in a dedicated counters view, we can add it in a later cheap ABI extension.

## 21. Schema compatibility

- Same `# v0.2.16` version tag on line 1; same Depends on line 2.
- Same imports (`from genlayer import *`, `from dataclasses import dataclass`, `import hashlib`).
- ASCII-only (62 650 bytes), LF endings.
- New `CaseCounters` dataclass follows the same `@allow_storage @dataclass` pattern Studio has already accepted.
- Two new storage maps on `Contract`: `fork_case_counters: TreeMap[u256, CaseCounters]` and `fork_case_contrib_count: TreeMap[str, u32]` — both use primitive key/value types already accepted by Studio.
- Constants + module-level helpers added; no exotic Python features.
- **Fresh manual Studio schema-load recommended** before Stage 6a. Introduced one new dataclass and two new storage maps; both surface in the extracted schema.

## 22. Deferred

- Freeze (`freeze_evidence`, `freeze_case`) — Stage 6b, alongside actual web retrieval.
- Web retrieval — Stage 6b, gated on Stage 6a probe passing.
- Root-envelope adjudication → first root reaches `ENVELOPE_FAITHFUL` → `create_fork` self-unlocks → fork adjudication also lands — Stage 7.
- Challenger reward source decision — Stage 10 open item.
- Runtime timestamp source — Stage 15 verification.

## 23. Roadmap (locked)

| Stage | Deliverable |
|---|---|
| **5** (this stage) | Deterministic evidence architecture. |
| **6a** | Live GenLayer web-render capability probe against realistic governance sources. **Hard blocker on Stage 6b.** |
| **6b** | Production evidence retrieval, content fingerprinting, and freeze — using the current official Fetch Web Content example VERBATIM: <https://docs.genlayer.com/developers/intelligent-contracts/examples/fetch-web-content>. No custom / off-chain / backend / mocked substitute. |
| **7** | Semantic adjudication (root envelope + fork). First root reaches `ENVELOPE_FAITHFUL`; `create_fork` self-unlocks. |
| **8+** | As previously planned. |

Order 6a → 6b is not reversible: the probe is the gate on whether we ship retrieval at all.

## 24. Stage 6a scope (proposed)

Stage 6a implements and reports the **live capability probe** described in `docs/STAGE_1_ARCHITECTURE_AND_AUDIT.md` §10.4:

1. Corpus: at least one URL per class of {Snapshot-style governance proposal, Tally / on-chain governance interface page, DAO governance forum thread, official DAO documentation, treasury / budget report}.
2. For each URL, call `gl.nondet.web.render(url, "text")` wrapped in `gl.eq_principle.strict_eq(...)` and measure: successful render; useful extracted text; repeatability inside a bounded window; consensus behavior; `Undetermined` behavior; content bounds; failure / unavailable-page behavior.
3. Pass criteria (from §10.4): ≥ 4 of 5 URL classes render usable text under `strict_eq` consensus; repeatability holds; `Undetermined` and failure modes are all observed and mapped to documented contract states; no target requires a workaround outside `gl.nondet.web.*` and `gl.eq_principle.*`.
4. Deliverable: `docs/STAGE_6A_WEB_RENDER_PROBE_REPORT.md` with per-URL results and the pass/fail decision.
5. If the probe fails, Stage 6b halts. **Do not invent a workaround.** Documented options: reduce probe corpus and restrict production use to the subset that works; fall back to `prompt_comparative` (weaker deterministic guarantee, requires reassessment); pause and reassess with the user.

**Stage 6a implementation touches contract source only to add a probe entry point** (either a temporary probe method, or an isolated probe contract). It does NOT modify the fork evidence pathway or wire retrieval into `submit_fork_evidence` / `freeze_evidence` / `freeze_case`. Those wait for Stage 6b.

## 25. Future web-safety carry-forwards (Stage 6b)

Documented here for the record; not implemented in Stage 5:

- Retrieve only frozen submitted URLs; no discovery, no crawling.
- Bound rendered content before prompt inclusion (`MAX_EVIDENCE_SLICE`; provisional 16 KiB, subject to Stage 6a).
- Preserve original URL + metadata separately from fetched content.
- Guard against prompt injection: explicit delimiters, fixed system instructions, bounded slices, no browsing tool exposed to the model (per Stage 1 §13).
- Handle unavailable pages neutrally — a retrieval failure is not evidence for or against a fork's semantic faithfulness; it is a `CASE_OPEN` state condition.
- Per-evidence `content_fingerprint` populated as SHA-256 of the frozen slice.
- `root.web_content_fingerprint` remains distinct from `Evidence.content_fingerprint` (Stage 2B §17.4).
- `Case.evidence_set_fingerprint` binds ordered evidence IDs at freeze.
- Verdict `evidence_refs` must resolve to actual `Evidence` records — Stage 8 deterministic validator enforces (Stage 1 §28).

## 26. Known limitations

- Runtime `hashlib.sha256` still Stage 15's live-check.
- Runtime timestamp source not confirmed for v0.2.16; `Evidence.submitted_at = 0`, `Case.last_attempt_at = 0`.
- URL normalization is deliberately conservative (no query-order normalization, no port normalization, no userinfo handling). Some redundant submissions may be accepted; the cap prevents damage.
- Per-contributor counter storage uses `str` composite keys because `TreeMap[bytes, u32]` was not verified with Studio v0.2.16 in this project. Effective; slightly less compact than a hashed-bytes key.
- Community model is not weighted by any reputation or stake; every non-creator address is equal. Reputation-weighted or bond-gated evidence is a future extension.
- Fork evidence submission does not read `gl.message.value`; the ABI method is `@gl.public.write` (non-payable), unchanged from Stage 2.

## 27. Confirmations

- ✅ Zero `gl.nondet.*` calls (grep-verified).
- ✅ Zero web retrieval.
- ✅ Zero semantic adjudication.
- ✅ Zero `gl.message.value` reads.
- ✅ Zero native GEN accounting / transfer.
- ✅ `Evidence.content_fingerprint = b""` for every Stage 5 evidence record.
- ✅ `Case.evidence_set_fingerprint = b""` and `Case.case_fingerprint = b""` while `CASE_OPEN`.
- ✅ `create_fork` still gated on `ENVELOPE_FAITHFUL`; no bypass introduced.
- ✅ `freeze_evidence` and `freeze_case` still raise (deferred to Stage 6b).
- ✅ Nothing was deployed or broadcast.
- ✅ Frontend not built.
- ✅ Stage 6a not started.
