# Stage 3 — Root Foundation (DAO registry, root import, Intent Envelope)

**Scope.** DAO registration, deterministic root proposal import, deterministic root import fingerprint, Intent Envelope submission, root-envelope evidence metadata, ROOT_ENVELOPE case creation, and the indexes / bounds / deterministic validation those flows require.

**Explicitly not in scope.** Web retrieval; `gl.nondet.*`; semantic adjudication; native GEN reading/capture/settlement/refund/slash/reward; fork creation logic; verdict logic; frontend.

## 1. DAO namespace semantics

The DAO registry is a **namespace / discovery mechanism, not a claim of DAO ownership**. A registered `Dao(name, url)` record is a Governance Fork community reference. It is not an assertion that the registrant officially represents the DAO. Downstream UIs must never treat a DAO registration as authoritative.

`register_dao(name, url) -> u256` behavior:

- Bounds: `1 ≤ len(name) ≤ MAX_DAO_NAME_LEN`, `1 ≤ len(url) ≤ MAX_URL_LEN`.
- Newline rejection: no `\n` or `\r` in either field.
- Global cap: `next_dao_id ≤ MAX_DAOS`.
- Duplicate policy: **none.** Any (name, url) pair may be registered any number of times, by any address. Rationale in §2.
- Storage: `Dao(name, url, importer = gl.message.sender_address, imported_at = u256(0))`. `imported_at` is `0` because the v0.2.16 runtime does not confirm a safe timestamp source; Stage 15 or a later caller-note pattern will populate it.
- Returns the allocated `dao_id` after the write succeeds.

## 2. DAO duplicate policy (documented decision)

**Chosen rule: allow all registrations; only `MAX_DAOS` applies.**

Alternatives considered:

- **Reject exact (name, url) duplicates.** Prevents accidental double-clicks but establishes a "first mover" claim that anyone can seize by re-registering an off-by-one URL. Signals nothing useful.
- **Reject same normalized URL.** Establishes URL-first-registrant ownership — falsely implies the first registrant represents that DAO. Fails the honesty rule §17 of Stage 1.
- **Allow all registrations** (chosen). Governance Fork does not certify DAO ownership; `identity_status` stays `COMMUNITY_IMPORTED` for every root under any DAO record. UI is required to render `identity_status` and never treat a DAO row as authoritative.

Anti-spam is `MAX_DAOS = 1024` only. A future `IDENTITY_DAO_VERIFIED_LATER` status can attach to specific DAO rows through a separate verification mechanism when one exists; V1 does not implement one.

## 3. Root import lifecycle

`import_root_proposal(dao_id, external_proposal_id, title, proposal_url, structured_parameters) -> u256`:

- All string bounds enforced up front (`external_proposal_id`, `title`, `proposal_url`).
- Newlines rejected in every string field.
- `dao_id` must exist.
- Per-DAO cap: `MAX_ROOTS_PER_DAO`.
- Structured parameters validated (§7).
- Canonical form computed and SHA-256 hashed → `import_fingerprint`.
- Global uniqueness index (`import_fingerprint_index[hex(fp)]`) rejects exact duplicates.
- Successful import writes:
  - `RootProposal.import_fingerprint = fp` (never empty after this point).
  - `RootProposal.web_content_fingerprint = b""` (Stage 6 fills).
  - `RootProposal.envelope = <empty IntentEnvelope>`, `envelope_status = ENVELOPE_NOT_SUBMITTED`, `envelope_case_id = 0`.
  - `RootProposal.identity_status = IDENTITY_COMMUNITY_IMPORTED`.
  - `RootProposal.imported_at = u256(0)`.
  - Appends `root_id` to `roots_by_dao[dao_id]`.
  - Registers `import_fingerprint_index[hex(fp)] = root_id`.

**No URL is fetched.** `proposal_url` is a metadata field. Authenticity is NOT claimed just because a URL was submitted.

## 4. Canonical fingerprint encoding

Implementation of Stage 2B §17.1. Domain-separation tag `"gf-root/v1"`.

Fields bound (in order, newline-delimited):

```
gf-root/v1
dao_id=<decimal ASCII of int(dao_id)>
external_proposal_id=<utf-8>
title=<utf-8>
proposal_url=<utf-8>
structured_parameters=
  <key>=<value>
  <key>=<value>
  ...
```

- Parameters are sorted by `key` ascending before encoding. Caller ordering does not affect the fingerprint.
- All string fields are pre-checked for `\n` and `\r` rejection at validation time, so newline delimiters are unambiguous.
- Excluded (by design): `proposer` address, `imported_at` timestamp. Re-importing the same proposal from a different address at a different time yields the same fingerprint. This is desired: identity of the imported proposal is not identity of the import event.

**Algorithm: SHA-256 via `hashlib.sha256`.** `import hashlib` at module top; the runtime accepts it (confirmed by RealityLock/seedling patterns and by Studio schema-load on this exact source).

Classification: **PROVISIONAL CRYPTOGRAPHIC** in Stage 2B is upgraded to **CRYPTOGRAPHIC** here at Stage 3 for schema-load-time behavior (the module imports successfully). Runtime `hashlib.sha256` behavior is exercised by tests via the shim and verified to match `hashlib` reference computations. Live runtime behavior remains Stage 15's verification.

## 5. Duplicate root policy

**Rule: exact duplicate imports of the same canonical form are rejected globally.**

Because `dao_id` is part of the canonical bytes, "global" uniqueness naturally scopes to the DAO — two DAOs importing byte-identical remaining fields still produce different fingerprints because the `dao_id=` line differs. Within a single DAO, byte-identical (external_proposal_id, title, proposal_url, structured_parameters) is rejected.

**Similar titles / different external_proposal_ids are allowed.** Two proposals with coincidentally similar titles or URLs are distinct as long as any canonical field differs. Verified by test.

## 6. Structured parameter rules

- `MAX_STRUCTURED_PARAMS = 32` entries.
- Each key: `1 ≤ len ≤ MAX_KV_KEY_LEN` (64), no newlines.
- Each value: `0 ≤ len ≤ MAX_KV_VAL_LEN` (256), no newlines.
- Duplicate keys within the submission are rejected.
- **Ordering does not change `import_fingerprint`** — the fingerprint sorts by key ascending before encoding. The stored `RootProposal.structured_parameters`, however, preserves caller order for display convenience; the ordering does not affect fingerprint identity. Verified by test.

## 7. Intent Envelope schema (structural)

`IntentEnvelope`:

- `objective`: `1 ≤ len ≤ MAX_OBJECTIVE_LEN` (512), no newlines.
- `beneficiary_class`: `1 ≤ len ≤ MAX_BENEFICIARY_CLASS_LEN` (128), no newlines.
- `resource_type`: must be one of `_ALLOWED_RESOURCE_TYPES` (bounded enum, 6 values).
- `scope`: `0 ≤ len ≤ MAX_SCOPE_LEN` (256), no newlines. May be empty for envelopes with no explicit scope restriction beyond the objective.
- `essential_constraints`: `DynArray[str]`, `≤ MAX_ESSENTIAL_CONSTRAINT_ITEMS` (8), each `1 ≤ len ≤ MAX_ESSENTIAL_CONSTRAINT_LEN` (128), no newlines, no duplicates.
- `mutable_dimensions`: `DynArray[str]`, `≤ MAX_MUTABLE_DIMENSIONS` (16), each `1 ≤ len ≤ MAX_DIMENSION_NAME_LEN` (64), no newlines, no duplicates.
- `immutable_dimensions`: `DynArray[str]`, `≤ MAX_IMMUTABLE_DIMENSIONS` (16), same per-entry rules.
- `mutable_dimensions ∩ immutable_dimensions == ∅`. Enforced by set-membership check during immutable-dimension validation.
- `parent_proposal_fingerprint`: **server-side bound** to the root's own `import_fingerprint`. The caller-supplied field is ignored. This prevents a submitter from claiming an envelope against a different root's fingerprint.
- `envelope_version` set to `u32(1)` on successful submission (Stage 3 schema version).

**Semantic questions Stage 3 does NOT answer:** whether the objective faithfully represents the underlying proposal; whether beneficiary class matches the DAO's intent; whether mutable/immutable classification is semantically defensible. Those are ROOT_ENVELOPE adjudication (Stage 7). Stage 3 performs structural validation only.

**Structured-vs-prose dimension representation.** A `mutable_dimension` or `immutable_dimension` name need NOT correspond to a key present in `RootProposal.structured_parameters`. Some governance proposals encode all their parameters as prose in the body rather than as structured k/v pairs. Stage 3 does not force a mapping between dimension names and structured parameter keys. When a fork is later created (Stage 4), it will need to declare its delta against dimensions the envelope names — but the delta may target prose-derived dimensions too. This flexibility is deliberate; Stage 7 adjudication reasons over the semantic delta regardless of the parameter's representation.

## 8. Active-envelope rule

**One active envelope per root at a time.** `submit_root_envelope` requires `root.envelope_status == ENVELOPE_NOT_SUBMITTED`. Any other value rejects.

Rationale: prevents envelope spam, prevents ambiguous canonical envelope state, prevents duplicate ROOT_ENVELOPE cases per root. After a later Stage 7 outcome of `NOT_FAITHFUL` / `UNCLEAR_VERDICT` / `INVALID`, a controlled retry/replacement mechanism will re-open the slot (Stage 7 concern; not implemented here).

## 9. Root-envelope evidence metadata

At envelope submission, evidence metadata is registered:

- Per-item bounds: URL (1..MAX_URL_LEN), relevance/authority/temporal within bounds, no newlines.
- `evidence_class` must be one of `_ALLOWED_EVIDENCE_CLASSES` (8 values).
- Per-case count: `1 ≤ n ≤ MAX_EVIDENCE_PER_CASE` (16).
- **Deduplication:** normalized URL within a case must be unique. Normalization = `strip + lower + trailing-slash-strip`. Deliberately does not touch queries, fragments, or ports. `https://Example.com/foo/` and `HTTPS://EXAMPLE.COM/foo` collide; `https://x.com/foo?a=1` and `https://x.com/foo?b=2` do not. Documented as conservative.
- Each `Evidence` record is written with `content_fingerprint = b""` and `frozen = False`. **No URL is fetched at Stage 3.** Content fingerprints are Stage 6 concerns.
- `Evidence.normalized_source = _extract_host(url)` — a bounded lowercased host string used later by the Stage 7 adjudicator for "same-source non-independence" reasoning. Extracted deterministically without network access. Not eTLD+1 (which would require a public suffix list); host-level only.

## 10. ROOT_ENVELOPE case creation

`submit_root_envelope` also allocates and writes:

- A `Case` with `case_type = CASE_TYPE_ROOT_ENVELOPE`, `target_id = root_id`, `target_kind = TARGET_KIND_ROOT_ENVELOPE`, `target_fingerprint = root.import_fingerprint`, `state = CASE_OPEN`, `evidence_ids = <ordered ids>`, `evidence_set_fingerprint = b""` (Stage 6 fills), `case_fingerprint = b""` (Stage 6 fills), `adjudication_dimensions_version = ADJUDICATION_DIMENSIONS_VERSION_ROOT_ENVELOPE`, `retry_count = 0`, `last_attempt_at = 0`.
- Index `evidence_by_case[case_id]` is populated with the same ids in order.
- `root.envelope_case_id = case_id`; `root.envelope_status = ENVELOPE_EVIDENCE_OPEN`.

**Explicit non-goals:** no evidence content fetched; no evidence content fingerprint computed; no evidence-set fingerprint computed; no adjudication run; no case-fingerprint sealed; no state advance beyond `EVIDENCE_OPEN`. All of those live in Stages 6–7.

## 11. Implemented state transitions

- `RootProposal.envelope_status`: `ENVELOPE_NOT_SUBMITTED` → `ENVELOPE_EVIDENCE_OPEN` (only). Later transitions (`EVIDENCE_FROZEN`, `ADJUDICATING`, `FAITHFUL`, `REJECTED`, `UNCLEAR`) are Stage 6+ / Stage 7+.
- `Case.state`: created directly at `CASE_OPEN`. No later transitions in Stage 3.

## 12. Indexes

Implemented and maintained by Stage 3 writes:

- `roots_by_dao[dao_id] -> DynArray[root_id]` (append on `import_root_proposal`).
- `evidence_by_case[case_id] -> DynArray[evidence_id]` (append on `submit_root_envelope`).
- `import_fingerprint_index[hex(fp)] -> root_id` (write on `import_root_proposal`).

Not touched by Stage 3 (later stages fill): `forks_by_root`, `forks_by_parent`, `verdicts_by_fork`, `verdicts_by_root`, `challenges_by_fork`, `challenges_by_root`.

## 13. Implemented views (8)

- `get_dao(dao_id) -> Dao`
- `list_daos(cursor, limit) -> PageIds` — cursor is a `dao_id` starting point; walks the monotonic id space and returns existing entries.
- `get_root_proposal(root_id) -> RootProposal` — includes envelope + `envelope_status` inline.
- `list_root_proposals_by_dao(dao_id, cursor, limit) -> PageIds` — cursor is an index into `roots_by_dao[dao_id]`.
- `get_evidence(evidence_id) -> Evidence`
- `list_evidence_of_case(case_id, cursor, limit) -> PageIds`
- `get_case(case_id) -> Case`
- `get_constants() -> ConstantsView`

Bounded pagination throughout: `limit` clamped to `PAGINATION_LIMIT_MAX` (50). `PageIds.next_cursor == 0` marks the walk complete.

Other views (`get_fork`, `list_forks_of_root`, `list_forks_of_parent`, `get_verdict_history`, `get_verdict`, `get_challenge`, `list_challenges`, `get_bond`) still raise `gl.vm.UserError("stage-2: not implemented")`. They will be lit up as their entities appear in later stages.

## 14. Atomicity

Every implemented write validates ALL of its inputs before mutating any storage. If any check fails, `raise gl.vm.UserError(...)` is thrown before the first storage write, so the GenLayer runtime's per-tx atomicity guarantees no orphan entity, no orphan index entry, no counter drift.

The Stage 3 test `test_rollback_on_bad_input_leaves_no_orphan` verifies this directly at the Python-shim level: a failed `import_root_proposal` does not advance `next_root_id`, does not append to `roots_by_dao`, and does not register an `import_fingerprint_index` entry.

Runtime atomicity semantics are re-verified in Stage 15 against the live SDK.

## 15. Payable exposure, no economic behavior

`submit_root_envelope` remains `@gl.public.write.payable` for ABI stability. The Stage 3 body does not read the incoming native-GEN value, does not compute a bond, does not capture, refund, slash, transfer, or reward. Bond capture is Stage 10. **This contract is not production-ready and must not be used as production at Stage 3.**

## 16. Deferred

- Web retrieval — Stage 6.
- Semantic adjudication (root envelope or fork) — Stage 7.
- Native GEN read / bond capture / refund / slash / reward — Stage 10.
- Challenger reward source decision — Stage 10 open item, still unresolved.
- Envelope retry/replacement after `NOT_FAITHFUL` / `UNCLEAR` / `INVALID` verdict — Stage 7 concern.
- Runtime timestamp source — Stage 15 verification.
- Fork creation and business logic — Stage 4.

## 17. Stage 4 readiness

Ready. Stage 3 leaves:

- A live `import_fingerprint` for every root — Stage 4's `parent_fingerprint` validation can bind to it.
- A live `envelope` on the root — Stage 4's delta pre-check can consult `envelope.mutable_dimensions` / `immutable_dimensions`.
- The `roots_by_dao` and `forks_by_parent` indexes — Stage 4's tree writes plug into `forks_by_root` and `forks_by_parent`.
- Untouched `next_fork_id` counter.

**Second Studio schema-load check recommended before Stage 4** — Stage 3 added `hashlib` import, an enum value, a storage field, and function bodies. Any of those could in principle affect Studio's schema extractor. A cheap manual reload confirms zero regression before Stage 4 code lands on top.

## 18. Known limitations

- Runtime SHA-256 behavior via `hashlib` is expected but not live-verified.
- Runtime timestamp is not confirmed for v0.2.16; `imported_at = 0`.
- Duplicate DAO registrations are permitted — deliberate design choice per §2.
- Evidence URL normalization is conservative; query-string equivalence is not detected.
- `envelope.essential_constraints` deduplication is exact-string, not normalized.
- Envelope `parent_proposal_fingerprint` is server-bound to `root.import_fingerprint`; a future change to that binding requires an explicit envelope-schema version bump.
