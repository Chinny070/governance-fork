# Stage 4 — Fork Foundation (Deterministic Fork Machinery)

**Scope.** The deterministic core of Semantic Proposal Forking: typed delta validation, deterministic delta application, undeclared-mutation detection, immutable-dimension enforcement, canonical delta and body fingerprints, parent binding, tree invariants (root/DAO isolation, depth cap, children cap, per-root fork cap), and the `create_fork` FAITHFUL gate. Everything a fork needs to be constructed safely — with public `create_fork` remaining unavailable until a root reaches `ENVELOPE_FAITHFUL`.

**Explicitly not in scope.** Any `gl.nondet.*`; web retrieval; semantic adjudication; native GEN reading / capture / refund / slash / reward; challenger reward source decision; fork evidence submission; fork case freeze; fork verdict; challenge.

## 1. Semantic Proposal Forking, deterministic layer

Every fork answers **deterministic** questions before any semantic judgment happens:

- Does the parent exist and does its authoritative fingerprint match?
- Is the declared delta structurally valid under the parent's Intent Envelope?
- Does the resulting child body **exactly** match the deterministic application of that delta to the parent's structured parameters?
- Was any parameter mutated without a declared delta (`UNCLAIMED_MUTATION`)?
- Was any immutable-classified dimension changed (`IMMUTABLE_DIMENSION_MUTATION`)?
- Is the child within all tree caps (depth, children, per-root total)?
- Is the child's root/DAO lineage consistent with the parent's?

None of these are semantic questions. All of them are deterministic. Stage 4 answers them all.

Semantic questions — is the fork faithful to governance intent, is the modification reasonable, is the evidence authoritative, should the community adopt — are Stage 7's concern.

## 2. `create_fork` is gated until a root reaches `ENVELOPE_FAITHFUL`

**Hard rule, source-level:** the first check on the parent's authority in `create_fork` is:

- For `parent_kind == PARENT_KIND_ROOT`: `root.envelope_status == ENVELOPE_FAITHFUL`. Any other value refuses with `root intent envelope not finalized faithful`.
- For `parent_kind == PARENT_KIND_FORK`: `parent_fork.status == FORK_FINALIZED_FAITHFUL`. Any other value refuses with `parent fork not finalized faithful`.

Neither status can currently be produced by any code path in the contract. Envelope adjudication is Stage 7's deliverable; only Stage 7 sets `ENVELOPE_FAITHFUL`. Fork adjudication + finalization is also Stage 7+; only that path sets `FORK_FINALIZED_FAITHFUL`.

**No production bypass exists.** The contract source contains:

- No `envelope_status_override`, no `faithful_bypass`, no `test_only`, no `TESTING_MODE` — grep-verified in test `test_no_production_override_symbol`.
- No public write method that sets `envelope_status` outside `import_root_proposal` (which sets `ENVELOPE_NOT_SUBMITTED`) and `submit_root_envelope` (which sets `ENVELOPE_EVIDENCE_OPEN`).
- No admin path that flips envelope status.
- No hidden helper that the FAITHFUL gate would defer to.

Tests exercise the deterministic machinery by (a) calling module-level pure helpers directly, and (b) using an **in-test-process only** fixture that mutates `contract.roots[rid].envelope_status = ENVELOPE_FAITHFUL` after Stage 3 flows finish. The mutation lives entirely in `tests/test_stage_4.py`; nothing in `contracts/governance_fork.py` enables it. Production behavior of `create_fork` is refusal.

## 3. Root vs fork parent

Both parent kinds are supported in the schema; only the FAITHFUL-gated path exists in production.

| Aspect | `PARENT_KIND_ROOT` | `PARENT_KIND_FORK` |
|---|---|---|
| Existence check | `parent_id in self.roots` | `parent_id in self.forks` |
| Eligibility gate | `envelope_status == ENVELOPE_FAITHFUL` | `status == FORK_FINALIZED_FAITHFUL` |
| Authoritative parent fingerprint | `root.import_fingerprint` | `parent_fork.body_fingerprint` |
| Resolved `root_id` | `parent_id` | `parent_fork.root_id` |
| Resolved `dao_id` | `root.dao_id` | `parent_fork.dao_id` |
| Parent `depth` | conceptual root depth 0 | `parent_fork.depth` |
| Envelope for delta authorization | `root.envelope` | `self.roots[parent_fork.root_id].envelope` (single envelope per root) |

All fork descendants under a given root are bound to the **same** envelope. Envelope classifications (mutable / immutable) apply uniformly through the tree.

## 4. Typed delta model

`DeltaEntry(dimension_name, parent_value, fork_value, claim_kind)`.

Allowed `claim_kind` values (bounded, final):

- `CLAIM_NARROWED`
- `CLAIM_BROADENED`
- `CLAIM_RESHAPED`
- `CLAIM_REMOVED`
- `CLAIM_ADDED`

`CLAIM_UNCHANGED` remains omitted per Stage 2B §20. Absent from delta = claimed unchanged.

### 4.1 Structural validation (`_validate_delta_entries`)

- `1 ≤ len(delta) ≤ MAX_DELTA_ENTRIES` (16).
- Each `dimension_name`: `1..MAX_DIMENSION_NAME_LEN` (64), no newlines.
- Each `parent_value` / `fork_value`: `0..MAX_DELTA_VALUE_LEN` (256), no newlines.
- `claim_kind` must be in the allowed set.
- **Duplicate `dimension_name` rejected** (`DUPLICATE_DELTA_DIMENSION`).
- **Immutable-dimension mutation rejected** (`IMMUTABLE_DIMENSION_MUTATION`).
- **Dimension not classified by envelope rejected** (`DIMENSION_NOT_IN_ENVELOPE`).

Order-independent: validation does not depend on caller order; canonical fingerprinting sorts before hashing.

## 5. Mutable vs immutable enforcement

- A delta may only target a dimension in `envelope.mutable_dimensions`.
- A delta targeting `envelope.immutable_dimensions` is rejected **deterministically at the validation step** — never reaches semantic adjudication.
- A delta targeting a name that is in neither set is rejected as `DIMENSION_NOT_IN_ENVELOPE`.

The rule is purely structural. No LLM enforces it.

## 6. Structured vs prose dimensions

Governance proposals sometimes encode a dimension as a structured parameter (e.g. `amount = 100000`), sometimes as prose (e.g. "eligibility is open-source developers"). Both are legitimate.

`_apply_delta` distinguishes them by whether the dimension name appears as a key in the parent's structured_parameters:

**Structured mutation** (dimension in parent's structured params):

- `CLAIM_ADDED` → reject as `ADDED_DIMENSION_ALREADY_EXISTS`.
- `CLAIM_REMOVED` → `parent_value` must match stored; key removed from resulting_params.
- `CLAIM_NARROWED / BROADENED / RESHAPED` → `parent_value` must match stored; resulting_params updated to `fork_value`.
- Any `parent_value` mismatch → `PARENT_VALUE_MISMATCH`. The caller cannot rewrite parent history.

**Prose mutation** (dimension NOT in parent's structured params):

- `CLAIM_ADDED` → `parent_value` must be `""` (there was no prior structured version); a new structured parameter is added to resulting_params with the declared `fork_value`. This is how a fork explicitly promotes a prose dimension into structured form.
- `CLAIM_REMOVED` → reject as `CANNOT_REMOVE_PROSE_DIMENSION` (nothing to structurally remove; a prose "removal" is a NARROWED/RESHAPED).
- `CLAIM_NARROWED / BROADENED / RESHAPED` → recorded in delta_entries but produce no change to resulting_params. `parent_value` is a caller-claimed representation of the prior prose state and is NOT verified against stored data. Adjudication (Stage 7) evaluates the claim.

The distinction is captured by returning both `(resulting_params, prose_dims)` from `_apply_delta`.

## 7. Undeclared mutation detection (`UNCLAIMED_MUTATION`)

After deriving `computed_params` from the parent + declared deltas, `_check_body_matches_computed` compares it byte-for-byte against `body.structured_parameters`:

- Extra key in body → `UNCLAIMED_MUTATION: unexpected key <k>`.
- Missing key in body → `UNCLAIMED_MUTATION: parameter count differs`.
- Value differs → `UNCLAIMED_MUTATION: value differs at <k>`.

Hidden parameter changes are impossible under this rule. If the caller wants to change a parameter, they must declare it in the delta; if they want it unchanged, they must not touch it in `body`. Comparison is order-independent (dicts).

## 8. Delta canonical encoding + fingerprint

Domain-separated encoding (`_canonicalize_delta`):

```
gf-delta/v1
dao_id=<decimal>
root_id=<decimal>
parent_kind=<PARENT_ROOT|PARENT_FORK>
parent_id=<decimal>
parent_fingerprint=<hex>
deltas=
  d:<dimension_name>
  k:<claim_kind>
  p:<parent_value>
  f:<fork_value>
  d:<dimension_name>
  k:<claim_kind>
  p:<parent_value>
  f:<fork_value>
```

Delta entries are sorted by `dimension_name` ascending before encoding. All string fields have been newline-rejected at validation, so the newline delimiters are unambiguous. Each delta contributes exactly four lines; the `d:`/`k:`/`p:`/`f:` line-prefixes prevent inter-field ambiguity.

**Algorithm:** SHA-256 via `hashlib.sha256`. `_delta_fingerprint` returns the 32-byte digest.

**Invariants (verified by test):**

- Same delta content, different caller order → same fingerprint (`test_delta_input_order_independent`).
- Any changed `dimension_name`, `parent_value`, `fork_value`, `claim_kind`, `parent_kind`, `parent_id`, `parent_fingerprint`, `root_id`, or `dao_id` changes the fingerprint.
- Matches `hashlib.sha256` reference (`test_delta_fingerprint_matches_hashlib_reference`).

## 9. Fork body canonical encoding + fingerprint

Domain-separated encoding (`_canonicalize_fork_body`):

```
gf-fork-body/v1
dao_id=<decimal>
root_id=<decimal>
parent_kind=<PARENT_ROOT|PARENT_FORK>
parent_id=<decimal>
title=<utf-8>
summary=<utf-8>
reasoning=<utf-8>
structured_parameters=
  <key>=<value>
  <key>=<value>  # sorted by key ascending
```

**Excluded (by design):** fork creator address, timestamps. The body is content-identified, not identity-identified. Two callers submitting byte-identical fork bodies produce the same body_fingerprint even if their addresses or clocks differ.

**Algorithm:** SHA-256 via `hashlib.sha256`.

**Invariants:** parameter-order-independent, stable across calls, sensitive to any field change.

## 10. Parent fingerprint semantics

At `create_fork` the caller supplies `parent_fingerprint`. It MUST equal:

- `root.import_fingerprint` when `parent_kind == PARENT_KIND_ROOT`.
- `parent_fork.body_fingerprint` when `parent_kind == PARENT_KIND_FORK`.

Any mismatch rejects with `parent_fingerprint mismatch (stale parent?)`. This is the deterministic "you know which parent you claim to descend from" check — if the parent has drifted since the caller last inspected it, the fork must be resubmitted.

**We do NOT use `root.web_content_fingerprint` as a lineage fingerprint.** That field is about the authoritative external page (§17.2 of the Stage 2 doc); it is populated later by Stage 6 and is unrelated to imported canonical identity. `Stage 4` uses `import_fingerprint` because it is the fingerprint of the canonical Governance Fork submitted root, which is what a fork actually descends from.

The child's `Fork.parent_fingerprint` is stored as an immutable snapshot at creation time. A future change to the parent's own fingerprint (e.g. envelope-schema version bump) does not silently reinterpret existing children — their frozen `parent_fingerprint` remains the anchor.

## 11. Deterministic delta application rules (all enforced)

- Only `envelope.mutable_dimensions` may appear as delta targets.
- Each delta entry's `parent_value` must match parent state for structured dimensions (`PARENT_VALUE_MISMATCH` otherwise).
- `CLAIM_ADDED` requires the dimension NOT already in parent structured params.
- `CLAIM_REMOVED` requires the dimension IS in parent structured params.
- Prose dimensions cannot be structurally removed.
- The resulting body must exactly match `_apply_delta(parent_params, delta)` — any diff is `UNCLAIMED_MUTATION`.

## 12. `ADDED` and `REMOVED` behavior

**`CLAIM_ADDED`:**
- If dimension is in parent structured params → reject `ADDED_DIMENSION_ALREADY_EXISTS`.
- If dimension is prose → `parent_value` MUST be `""`; a new structured parameter is added with `fork_value`. Documented and enforced (`test_added_prose_parent_must_be_empty`).
- Must appear in `envelope.mutable_dimensions`.

**`CLAIM_REMOVED`:**
- If dimension is in parent structured params → `parent_value` must match stored; key removed from resulting_params.
- If dimension is prose → reject `CANNOT_REMOVE_PROSE_DIMENSION`.
- Must appear in `envelope.mutable_dimensions`.

The canonical `fork_value` for `CLAIM_REMOVED` is `""` by convention (empty). The canonical `parent_value` for `CLAIM_ADDED` of a prose promotion is `""` by rule.

## 13. Root / DAO isolation

- On `parent_kind == PARENT_KIND_ROOT`: `root_id = parent_id`, `dao_id = root.dao_id`. Both are derived from stored parent state, never from caller input.
- On `parent_kind == PARENT_KIND_FORK`: `root_id = parent_fork.root_id`, `dao_id = parent_fork.dao_id`. Both derived from stored parent.
- No caller-supplied `root_id` or `dao_id` exists in the ABI. Cross-lineage forks are structurally impossible.

## 14. Depth calculation and cap

- ROOT parent → child.depth = 1.
- FORK parent → child.depth = parent_fork.depth + 1.
- `MAX_DEPTH_PER_ROOT = 8`. Any child that would exceed this rejects (`MAX_DEPTH_PER_ROOT exceeded`). Verified by `test_depth_stack_via_finalized_forks`, which builds a chain to depth 8 and confirms depth 9 refuses.

## 15. Children cap and per-root fork cap

- `MAX_CHILDREN_PER_PARENT = 32`. `create_fork` reads `len(self.forks_by_parent[parent_id])` and rejects on saturation. Verified by `test_children_cap_enforced` (fills to 32, confirms 33rd refuses).
- `MAX_FORKS_PER_ROOT = 512`. Read from `len(self.forks_by_root[root_id])`.

## 16. Cycle prevention (by construction)

- `fork_id` is a fresh monotonic allocation from `next_fork_id`.
- `parent_id` must reference an already-existing entity in `self.roots` or `self.forks`.
- All existing forks have IDs strictly less than the new `fork_id`.
- Therefore no fork can ever be its own ancestor: no cycle is representable.

No graph traversal or ancestor walk is needed at write time. Documented in test `test_new_id_always_greater_than_parent`.

## 17. Indexes maintained

- `forks_by_root[root_id]` appended.
- `forks_by_parent[parent_id]` appended.
- `parent_fork.child_count` incremented for `PARENT_KIND_FORK`.
- `next_fork_id` incremented after allocation.

Every failed `create_fork` raises before any of these writes, so no orphan is created.

## 18. Fork status at creation

`Fork.status = FORK_DRAFT` (already in the enum). The evidence-open / evidence-frozen / adjudicating / verdict-proposed / challenge / finalized transitions belong to Stages 5+.

## 19. ABI

**No public ABI additions.** `create_fork`'s signature gained a required parameter `parent_kind: str`. `get_fork`, `list_forks_of_root`, `list_forks_of_parent` were implemented (previously raising). ABI method count remains **29** (11 write + 2 admin + 16 view).

`create_fork`'s new signature:

```
create_fork(parent_id: u256, parent_kind: str, parent_fingerprint: bytes,
            delta: DynArray[DeltaEntry], body: ForkBody) -> u256
```

Payable ABI retained. Body does not read incoming value.

## 20. Schema compatibility

- Same `# v0.2.16` version tag on line 1; same `Depends` on line 2.
- Same `from genlayer import *` / `from dataclasses import dataclass` / `import hashlib`.
- ASCII-only (51 743 bytes), LF endings.
- One new field on `Fork` dataclass: `parent_kind: str` and `parent_fingerprint: bytes`. Same primitive types Studio has already accepted.
- Two new module-level string constants: `PARENT_KIND_ROOT`, `PARENT_KIND_FORK`. Same pattern Stage 2/3 used.
- Six new module-level pure helper functions (`_validate_delta_entries`, `_apply_delta`, `_check_body_matches_computed`, `_canonicalize_delta`, `_canonicalize_fork_body`, `_delta_fingerprint`, `_body_fingerprint`). Module-level helpers were verified to load in Studio during Stage 3.

**Fresh manual Studio schema-load recommended** before Stage 5. The `Fork` dataclass shape changed and `create_fork` gained a parameter; both are visible in the extracted schema. Confirming a green load rules out any v0.2.16 sensitivity to the two-field addition on `Fork`.

## 21. Deferred

- Envelope adjudication that produces `ENVELOPE_FAITHFUL` — Stage 7 (blocked on Stage 5, 6, 6a).
- Fork evidence submission, freeze, adjudication, challenge, finality — Stages 5–9.
- Native GEN read, bond capture, refund/slash/reward, challenger reward source decision — Stage 10.
- Web retrieval (`gl.nondet.web.render` inside `gl.eq_principle.strict_eq`) — Stage 6 (mandatory pattern from the official docs).
- Live capability probe — Stage 6a.
- Runtime timestamp for `Fork.created_at` — Stage 15 or a caller-supplied note.

## 22. Roadmap (unchanged)

- **Stage 5** — Evidence architecture (deterministic freeze skeleton, no web retrieval yet).
- **Stage 6** — Web retrieval integration using the mandatory official pattern.
- **Stage 6a** — Live capability probe. Hard blocker on Stage 7.
- **Stage 7** — ROOT_ENVELOPE adjudication → first root becomes `ENVELOPE_FAITHFUL` → `create_fork` becomes usable with no source change to the gate. Fork adjudication also lands here.
- **Stage 8** — Deterministic validator hardening.
- **Stage 9** — Challenge system.
- **Stage 10** — Native GEN economics; challenger reward source decision.
- **Stages 11+** as previously planned.

The FAITHFUL gate is a permanent contract-level rule, not a temporary shim. When Stage 7 lands, `create_fork` starts working for legitimate FAITHFUL roots without any change to the gate itself.

## 23. Known limitations

- SHA-256 via `hashlib` remains schema-load-verified only; runtime execution is Stage 15's live check.
- `Fork.created_at = 0` sentinel; runtime timestamp source not confirmed for v0.2.16.
- Prose-dimension mutations write no structured change; the caller's declared `parent_value` for prose is not verified against stored data (there is nothing to verify against).
- `_apply_delta`'s prose vs structured distinction assumes the parent's structured_parameters faithfully represent the parent's structured state — which it does by construction, since we require `body.structured_parameters == computed` on every fork creation.
- Fork body evidence is not yet submittable (Stage 5); a fork can be created and inspected but cannot yet accumulate its own case evidence.

## 24. Stage 5 recommendation

Stage 5 = evidence architecture, still deterministic.

Deliverables:

- `submit_fork_evidence(fork_id, evidence_urls, evidence_classes, relevance_claims, authority_claims, temporal_markers)`: validate bounds, allocate a `FORK` case, allocate `Evidence` records with `content_fingerprint = b""` and `frozen = False`, update indexes. Fork must be in `FORK_DRAFT`; transitions to `FORK_EVIDENCE_OPEN`. Callable only by `fork.creator`.
- `freeze_evidence(evidence_id)`: **schema-only** at Stage 5 — computes and stores the deterministic content_fingerprint = SHA-256 of a placeholder empty slice, marks `frozen = True`. Actual web fetching enters at Stage 6, where the empty slice is replaced by `gl.nondet.web.render(url, "text")[:MAX_EVIDENCE_SLICE]` inside `gl.eq_principle.strict_eq`.

Actually — reconsider. Freezing a bytes value of `b""` and calling it a "content fingerprint" is misleading. Cleaner Stage 5 scope: implement `submit_fork_evidence` (metadata registration, no fetch, no freeze), and defer both `freeze_evidence` and `freeze_case` to Stage 6 where they can be implemented alongside the actual retrieval pathway. Testable Stage 5 deliverables:

- Fork evidence bundle registration for a fork.
- Duplicate normalized URL detection within a fork's case.
- Envelope-adjudication case's evidence still lives on its ROOT_ENVELOPE case; fork evidence is a separate `FORK` case.
- Views: no ABI additions.
- Tests: fork evidence happy path, cap, dedup, wrong fork status (only `FORK_DRAFT` accepts), only creator can submit.

I recommend this Stage 5 scope; alternative would be to also land the "empty freeze" placeholder, which I do not recommend.

## 25. Confirmations

- ✅ Zero `gl.nondet.*` calls; grep-checked in Stage 4 tests.
- ✅ Zero web retrieval.
- ✅ Zero semantic adjudication.
- ✅ Zero `gl.message.value` reads.
- ✅ Zero native GEN logic (no capture, no transfer, no refund, no slash, no reward, no `Bond` allocation in Stage 4).
- ✅ No production override symbols in source (`envelope_status_override`, `faithful_bypass`, `test_only`, `TESTING_MODE` all absent).
- ✅ `create_fork` refuses on every envelope status except `ENVELOPE_FAITHFUL` (test class `CreateForkGateTests` covers all six other statuses).
- ✅ Nothing was deployed or broadcast.
- ✅ Frontend not built.
- ✅ Stage 5 not started.
