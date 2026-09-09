# Stage 2 — Schema, Storage & ABI Compatibility

**Purpose.** Establish a clean, bounded, Studio-compatible production contract scaffold. Prove the schema/storage/ABI can load correctly before business logic is added. **No business logic. No `gl.nondet.*`. No web retrieval. No native GEN settlement.**

## 1. Runtime / Syntax findings

Verified against current official GenLayer documentation and one known-good local reference (`../RealityLock/contracts/reality_lock.py`).

| Concern | Finding |
|---|---|
| Dependency header | Single-line preamble comment: `# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }`. Copied from the same version pinned in the local reference. **Stage 15 must live-verify this hash against the runtime SDK version at deployment time.** |
| Import | `from genlayer import *` (documented; primary pattern). Exposes `gl.Contract`, `gl.public.*`, `gl.vm.UserError`, `gl.message.sender_address`, `TreeMap`, `DynArray`, `Address`, `u256`, `u32`, `bytes`, `bool`, `str`, `@allow_storage`, `@dataclass`. |
| Base class | `class Contract(gl.Contract):`. |
| Decorators | `@gl.public.view` (read-only), `@gl.public.write` (state-changing), `@gl.public.write.payable` (state-changing + `value`). |
| Constructor | `def __init__(self):` — **no `-> None` return annotation** (Studio schema-load gotcha; documented in prior work). **Updated post-Stage-6b:** originally `def __init__(self, treasury_addr: Address):`; changed to parameterless after a live Studio deploy failure (`AttributeError: 'int' object has no attribute 'as_bytes'` in the storage setter) traced to the deploy-calldata decoder not reconstructing an `Address` from constructor arguments — it delivers a raw `int` instead. `treasury_addr` is now sourced from `gl.message.sender_address` (the deploying account) inside `__init__`, avoiding constructor calldata for `Address` entirely. Treasury/admin is therefore always the account that deploys the contract. See the "fix: initialize treasury from deployer" commit. |
| Storage primitives used | `u32`, `u256`, `bool`, `str`, `bytes`, `Address`, `TreeMap[K, V]`, `DynArray[T]`. All in the current confirmed primitive list. |
| Custom storage classes | `@allow_storage @dataclass` on every dataclass. Applied uniformly to keep the same shape whether used as stored value or as view return. |
| Enums | Represented as **module-level `str` constants** with fields typed `str`. Deliberately not using Python `Enum` / `IntEnum` — string constants have historically loaded cleanly through the Studio schema extractor, and every enum is bounded semantically by validation on the write path (Stage 3+). |
| Errors | `gl.vm.UserError("...")` — matches local reference and current SDK. |
| Caller | `gl.message.sender_address` — matches local reference. |
| Native GEN value read | `gl.message.value` (mentioned in docs narrative). **Not called in Stage 2.** |
| ASCII / LF constraints | Source is ASCII-only; LF line endings (Windows `git` core.autocrlf is left as-is; Python parses either). No leading comment wall beyond the single-line `Depends` preamble. |

**No conflicts found** between current official documentation and Stage 1 assumptions on the surface Stage 2 depends on. The `NOT LIVE VERIFIED` items from §10.3 of the Stage 1 doc (bit-exact strict_eq over rich content, prompt_comparative at scale, native GEN read/send APIs) are Stage 6a / Stage 10 dependencies and are **not exercised** by Stage 2.

## 2. Final enums (implemented as `str` constants)

- **Root identity:** `IDENTITY_COMMUNITY_IMPORTED`, `IDENTITY_DAO_VERIFIED_LATER`, `IDENTITY_UNVERIFIED`.
- **Envelope status:** `ENVELOPE_NOT_SUBMITTED`, `ENVELOPE_ADJUDICATING`, `ENVELOPE_FAITHFUL`, `ENVELOPE_REJECTED`, `ENVELOPE_UNCLEAR`.
- **Fork status:** `FORK_DRAFT`, `FORK_EVIDENCE_OPEN`, `FORK_EVIDENCE_FROZEN`, `FORK_CASE_FROZEN`, `FORK_ADJUDICATING`, `FORK_VERDICT_PROPOSED`, `FORK_CHALLENGE_WINDOW`, `FORK_CHALLENGE_OPEN`, `FORK_FINALIZED_FAITHFUL`, `FORK_FINALIZED_NOT_FAITHFUL`, `FORK_FINALIZED_UNCLEAR`, `FORK_FINALIZED_INVALID`.
- **Evidence class:** `EC_OFFICIAL_GOVERNANCE`, `EC_OFFICIAL_DOCUMENTATION`, `EC_OFFICIAL_TREASURY`, `EC_FINALIZED_DECISION`, `EC_GOVERNANCE_DISCUSSION`, `EC_IMPLEMENTATION_SPEC`, `EC_AUDIT`, `EC_THIRD_PARTY_ANALYSIS`.
- **Case type:** `CASE_TYPE_ROOT_ENVELOPE`, `CASE_TYPE_FORK`, `CASE_TYPE_CHALLENGE`.
- **Case state:** `CASE_OPEN`, `CASE_EVIDENCE_FROZEN`, `CASE_CASE_FROZEN`, `CASE_ADJUDICATING`, `CASE_SUCCESS`, `CASE_UNDETERMINED`, `CASE_UNDETERMINED_TERMINAL`, `CASE_INVALID`.
- **Verdict:** `VERDICT_FAITHFUL`, `VERDICT_NOT_FAITHFUL`, `VERDICT_UNCLEAR`, `VERDICT_INVALID`.
- **Semantic finding:** `FINDING_SATISFIED`, `FINDING_NOT_SATISFIED`, `FINDING_UNCLEAR`.
- **Fork dimensions:** `FORK_DIM_INTENT_PRESERVATION`, `FORK_DIM_DELTA_ACCURACY`, `FORK_DIM_UNDECLARED_SEMANTIC_CHANGE`, `FORK_DIM_EVIDENCE_SUPPORT`, `FORK_DIM_SOURCE_AUTHORITY`, `FORK_DIM_TEMPORAL_RELEVANCE`, `FORK_DIM_INTERNAL_CONSISTENCY`.
- **Root-envelope dimensions:** `RE_DIM_OBJECTIVE_REPRESENTATION`, `RE_DIM_SCOPE_FIDELITY`, `RE_DIM_CONSTRAINT_COMPLETENESS`, `RE_DIM_DIMENSION_CLASSIFICATION`, `RE_DIM_EVIDENCE_SUPPORT`, `RE_DIM_SOURCE_AUTHORITY`. **Kept structurally distinct** from fork dimensions.
- **Delta claim kind:** `CLAIM_NARROWED`, `CLAIM_BROADENED`, `CLAIM_RESHAPED`, `CLAIM_REMOVED`, `CLAIM_ADDED`. **`UNCHANGED` intentionally omitted** — see §5.
- **Fork challenge grounds:** `CG_FORK_INTENT_MISREAD`, `CG_FORK_DELTA_MISCLASSIFIED`, `CG_FORK_UNDECLARED_CHANGE_IGNORED`, `CG_FORK_SOURCE_AUTHORITY_ERROR`, `CG_FORK_TEMPORAL_EVIDENCE_ERROR`, `CG_FORK_CONTRADICTORY_EVIDENCE_OMITTED`, `CG_FORK_MALFORMED_ADJUDICATION`.
- **Root-envelope challenge grounds:** `CG_RE_OBJECTIVE_MISREPRESENTED`, `CG_RE_SCOPE_MISCHARACTERIZED`, `CG_RE_CONSTRAINT_INCOMPLETE`, `CG_RE_DIMENSION_MISCLASSIFIED`, `CG_RE_SOURCE_AUTHORITY_ERROR`, `CG_RE_EVIDENCE_SUPPORT_ERROR`, `CG_RE_MALFORMED_ADJUDICATION`. **Distinct enum** from fork grounds.
- **Challenge status:** `CHALLENGE_OPEN`, `CHALLENGE_ADJUDICATING`, `CHALLENGE_RESOLVED_FLIPPED`, `CHALLENGE_RESOLVED_UNCHANGED`, `CHALLENGE_RESOLVED_INVALID`, `CHALLENGE_RESOLVED_UNCLEAR`.
- **Bond purpose:** `BOND_PURPOSE_FORK_CREATION`, `BOND_PURPOSE_ENVELOPE`, `BOND_PURPOSE_CHALLENGE`.
- **Bond settlement kind:** `BOND_UNSETTLED`, `BOND_SETTLED_FULL_REFUND`, `BOND_SETTLED_PARTIAL_SLASH`, `BOND_SETTLED_CHALLENGER_REWARD`. **No `SETTLED_FULL_SLASH`** — V1 has no full-slash transition.
- **Target kind:** `TARGET_KIND_FORK`, `TARGET_KIND_ROOT_ENVELOPE`.
- **Resource type:** `RESOURCE_TREASURY`, `RESOURCE_PROTOCOL_PARAMETER`, `RESOURCE_POLICY`, `RESOURCE_GRANT_POOL`, `RESOURCE_INCENTIVE_BUDGET`, `RESOURCE_OTHER`.

## 3. Final data structures

All decorated `@allow_storage @dataclass`:

- `ParamKV(key: str, value: str)`
- `Dao(name, url, importer: Address, imported_at: u256)`
- `IntentEnvelope(objective, beneficiary_class, resource_type, scope, essential_constraints, mutable_dimensions, immutable_dimensions, parent_proposal_fingerprint: bytes, envelope_version: u32)`
- `RootProposal(dao_id, external_proposal_id, title, proposal_url, proposer: Address, import_fingerprint: bytes, web_content_fingerprint: bytes, structured_parameters: DynArray[ParamKV], envelope: IntentEnvelope, envelope_status, envelope_case_id, identity_status, imported_at)` — see §17 for the two-fingerprint model.
- `DeltaEntry(dimension_name, parent_value, fork_value, claim_kind)`
- `ForkBody(title, summary, structured_parameters: DynArray[ParamKV], reasoning)`
- `Fork(parent_id, root_id, dao_id, creator: Address, depth: u32, body: ForkBody, delta: DynArray[DeltaEntry], status, body_fingerprint: bytes, delta_fingerprint: bytes, evidence_case_id, current_verdict_id, child_count: u32, created_at, creator_bond_id)`
- `Evidence(case_id, submitter: Address, url, normalized_source, evidence_class, relevance_claim, authority_claim, temporal_marker, content_fingerprint: bytes, submitted_at, frozen: bool)`
- `Case(case_type, target_id, target_kind, target_fingerprint: bytes, evidence_ids: DynArray[u256], evidence_set_fingerprint: bytes, adjudication_dimensions_version: u32, case_fingerprint: bytes, state, retry_count: u32, last_attempt_at)`
- `DimensionFinding(name, finding, reasoning)`
- `VerdictRecord(case_id, target_id, target_kind, verdict, dimensions: DynArray[DimensionFinding], evidence_refs: DynArray[u256], reason_codes: DynArray[str], reasoning_hash: bytes, replaced_by, created_at)`
- `Challenge(target_id, target_kind, challenger: Address, ground_code, argument, case_id, original_verdict_id, replacement_verdict_id, status, bond_id, opened_at)`
- `Bond(owner: Address, amount: u256, target_id, target_kind, purpose, settlement_kind, settled: bool, settled_at)`
- `PageIds(items: DynArray[u256], next_cursor: u256)` — the sole pagination return shape.
- `ConstantsView(...)` — cheap catch-all: every cap, every window, every bond amount, `paused`, `treasury_addr`.

Notes:

- `Case` intentionally does **not** encode adjudication-specific structure (fork vs envelope). The distinction lives in the `case_type` + `adjudication_dimensions_version` + `case_fingerprint`. Unified storage; **not** unified semantics.
- `VerdictRecord.dimensions` is a `DynArray[DimensionFinding]` of exactly 7 items (fork) or exactly 6 items (root envelope). Count is enforced by the deterministic validator in Stage 8, not by the storage type.
- `Fork.delta` stores **only changed dimensions** — no `CLAIM_UNCHANGED` entries (§5).
- `Bond` carries `target_kind` because a bond may back a fork creator, an envelope submitter, or a challenger.

## 4. Tree / index storage layout

```
daos:                TreeMap[u256, Dao]
roots:               TreeMap[u256, RootProposal]
forks:               TreeMap[u256, Fork]
evidence:            TreeMap[u256, Evidence]
cases:               TreeMap[u256, Case]
verdicts:            TreeMap[u256, VerdictRecord]
challenges:          TreeMap[u256, Challenge]
bonds:               TreeMap[u256, Bond]

roots_by_dao:        TreeMap[u256, DynArray[u256]]   # dao_id -> [root_ids]
forks_by_root:       TreeMap[u256, DynArray[u256]]   # root_id -> [fork_ids]
forks_by_parent:     TreeMap[u256, DynArray[u256]]   # parent_id -> [fork_ids] (parent may be root or fork)
evidence_by_case:    TreeMap[u256, DynArray[u256]]   # case_id -> [evidence_ids]
verdicts_by_fork:    TreeMap[u256, DynArray[u256]]   # fork_id -> [verdict_ids]
verdicts_by_root:    TreeMap[u256, DynArray[u256]]   # root_id -> [envelope-verdict_ids]
challenges_by_fork:  TreeMap[u256, DynArray[u256]]
challenges_by_root:  TreeMap[u256, DynArray[u256]]
```

**Rationale for the fork/root split** in verdicts and challenges: fork IDs and root IDs live in independent counter namespaces and could collide numerically. Splitting the indexes is the least clever, most auditable disambiguation. Cost is two extra `TreeMap`s; benefit is zero cross-target ambiguity.

**Unbounded reads impossible.** Every list view returns `PageIds` — a bounded slice of the underlying `DynArray` plus a `next_cursor`. Frontends iterate.

## 5. `DeltaEntry` UNCHANGED recommendation

**Recommendation: DO NOT store `CLAIM_UNCHANGED` entries.** Only changed dimensions are stored (`NARROWED`, `BROADENED`, `RESHAPED`, `REMOVED`, `ADDED`).

**Rationale:**

- A fork body's `structured_parameters` is a full set derived deterministically from `parent.structured_parameters` + declared changed dimensions. Any parent parameter not appearing in `Fork.delta` with a non-`UNCHANGED` claim is **implicitly unchanged** and must match parent-side exactly. The deterministic pre-check verifies this at freeze time.
- Immutable-dimension preservation is verified by walking `envelope.immutable_dimensions` and confirming each key's value in `fork.body.structured_parameters` equals the parent's — an explicit `UNCHANGED` entry adds no signal.
- Storing UNCHANGED entries at the cap (16 × ~350 bytes) is up to ~5 KiB of dead weight per fork.

**Downstream impact:**

- The `CLAIM_UNCHANGED` enum value is removed from Stage 2.
- The Stage 8 deterministic validator's delta-application check drives its "unchanged" verification from the parent's `structured_parameters`, not from stored deltas.
- The adjudicator prompt is updated (Stage 7) to explicitly state that any parent parameter not present in the delta list is unchanged; the model must not treat absence as ambiguity.

Stage 1 §8.1's `claim_kind ∈ {NARROWED, BROADENED, RESHAPED, REMOVED, ADDED, UNCHANGED}` is superseded to `{NARROWED, BROADENED, RESHAPED, REMOVED, ADDED}` on the strength of this recommendation. This is a Stage 2 architectural change, called out for approval.

## 6. ID strategy

Monotonic `u256` counters, one per entity type:

`next_dao_id`, `next_root_id`, `next_fork_id`, `next_evidence_id`, `next_case_id`, `next_verdict_id`, `next_challenge_id`, `next_bond_id`.

All initialized to `u256(1)` in `__init__`. IDs are strictly deterministic and derived from tx order. No off-chain ID generation, no randomness.

Bonds get their own counter because a target may have multiple bonds (creator + up to 3 challenge bonds); a bond ID is not derivable from the target ID alone.

Verdicts get their own counter because verdict history is append-only across challenges — indices into a per-target array are less convenient than global IDs when the frontend wants to fetch one specific record.

## 7. Storage caps / constants

Centralized in the source (module-level `MAX_*` and bond amount constants) and re-exposed through `get_constants() -> ConstantsView`:

| Constant | Value | Notes |
|---|---|---|
| `MAX_DAOS` | 1024 | |
| `MAX_ROOTS_PER_DAO` | 256 | |
| `MAX_FORKS_PER_ROOT` | 512 | |
| `MAX_CHILDREN_PER_PARENT` | 32 | |
| `MAX_DEPTH_PER_ROOT` | 8 | |
| `MAX_EVIDENCE_PER_CASE` | 16 | |
| `MAX_CHALLENGES_PER_TARGET` | 3 | |
| `MAX_EVIDENCE_SLICE` | 16384 | **Provisional.** Reducible after Stage 6a probe. |
| `PAGINATION_LIMIT_MAX` | 50 | |
| `MAX_DELTA_ENTRIES` | 16 | Only changed entries stored. |
| `RETRY_COOLDOWN_SECONDS` | 3600 | Undetermined retry cooldown. |
| `CHALLENGE_WINDOW_SECONDS` | 259200 | 72 hours. |
| `MAX_RETRIES_PER_CASE` | 3 | |
| `FORK_CREATION_BOND` | `1e17` | Provisional; Stage 10 sets final. |
| `ENVELOPE_BOND` | `1e17` | Same. |
| `CHALLENGE_BOND` | `1e17` | Same. |

`MAX_EVIDENCE_SLICE` is centralized specifically so Stage 6a can reduce it in one place if the live probe demands it.

## 8. Pagination convention

Every list view has the same signature:

```
(cursor: u256, limit: u32) -> PageIds
```

`limit` is clamped to `PAGINATION_LIMIT_MAX = 50`. The result is `PageIds { items: DynArray[u256], next_cursor: u256 }` — a bounded slice of the underlying index `DynArray`. `next_cursor == 0` means the walk is complete; any positive value can be fed into the next call verbatim.

**Chosen over alternatives:**

- Returning `DynArray[SomeRecord]` inline would risk runaway response sizes when records are large (e.g. `Fork` includes body + delta).
- Returning `(DynArray[u256], u256)` as a tuple would require Studio-schema tuple support that we do not want to assume.
- A dedicated `PageIds` dataclass is the smallest, cleanest, uniformly-shaped return type.

## 9. ABI

See `docs/STAGE_2_ABI_REVIEW.md` for per-method review and reduction rationale. Summary:

- **11 write methods** (state-changing, non-admin).
- **2 admin methods** (`pause`, `unpause`).
- **16 view methods** (bounded, paginated where applicable).
- **Total: 29 methods** (down from Stage 1 baseline of 32).

Payable signatures exposed at Stage 2: `submit_root_envelope`, `create_fork`, `challenge_verdict` — three writes, all using `@gl.public.write.payable`. Payable is exposed in the ABI because it affects the schema-visible method type; the **implementations remain `raise gl.vm.UserError("stage-2: not implemented")`** so no `value` is ever accepted.

## 10. Placeholder convention

Every non-admin write and every view method has body `raise gl.vm.UserError("stage-2: not implemented")`.

Why `gl.vm.UserError` and not `NotImplementedError`:

- Matches local reference (`../RealityLock/contracts/reality_lock.py`), which is a known-good Studio-compatible pattern.
- `gl.vm.UserError` produces a proper user-facing error path so any accidental call in a downstream environment surfaces clearly rather than as a raw Python traceback.
- Does not accept a `value`, does not modify storage, does not fetch anything, does not call `gl.nondet.*`. Zero risk of being mistaken for real behavior.

Admin methods (`pause`, `unpause`) are the sole exception — they contain a minimal `sender == treasury_addr` check and toggle `self.paused`. This is Stage 2 scope per the correction-round instruction: "minimal config/admin model needed to support it later."

## 11. Static / schema validation results

Run in this environment:

- Python syntax check (`python -m py_compile`): **available** — see report below.
- ASCII source check: **available** — see report below.
- LF line-ending check: **available** — see report below.
- Duplicate ABI method-name check: **available** — see report below.
- ABI method-count assertions: **available** — see report below.
- Prohibited-substring checks (no `gl.nondet`, no `.web.render`, no `.web.get`, no `transfer(`, no `.value`): **available** — see report below.
- `genvm-lint check`: **unavailable in this environment** — no `genvm-lint` binary on PATH. **Not fabricated.** Left as a Stage 12 CI gate for a machine that has it installed.
- Studio schema-load (`genlayer-studio` local schema extraction): **unavailable in this environment** — no local Studio instance running. Would require the user's own machine to run without deploying anything. **Not fabricated.** Left as a Stage 13 preparation task, or a Stage 2b task if the user wants a purely local schema-load check before Stage 3 starts.

The check script lives at `tests/stage_2_checks.py` and its output is captured in the Stage 2 commit.

## 12. Known limitations / schema/runtime risks

- **`MAX_EVIDENCE_SLICE = 16 KiB` is provisional.** Stage 6a may reduce it. Centralized so change is one line.
- **`FORK_CREATION_BOND`, `ENVELOPE_BOND`, `CHALLENGE_BOND` are provisional numeric constants.** Stage 10 sets final values based on GEN price and observed activity.
- **Depends-hash pinned from the reference contract.** May be out of date; Stage 15 live verification will confirm or update.
- **String-enum representation** relies on schema extractor treating `str` fields as opaque. If a future runtime enforces enum-typed fields, migration is a one-shot search-and-replace on the constants; storage layout does not change.
- **`gl.public.write.payable` schema exposure.** The scaffold declares three payable methods but their bodies raise `UserError` before accepting any `value`. In a runtime that pre-validates `value == 0` before dispatch, this is safe. If a runtime debits `value` before body execution, the raise still rolls back atomically. Confirmed pattern from the local reference.
- **`gl.nondet.web.render` capability** for arbitrary rich governance pages remains `NOT LIVE VERIFIED for Governance Fork` (Stage 1 §10.3). Stage 2 does not depend on this.
- **Native GEN read / transfer APIs** remain `DOCUMENTED BUT NOT LIVE VERIFIED` / `UNKNOWN`. Stage 2 does not depend on either.

## 13. Items explicitly deferred

- Business logic for every ABI method (Stages 3–11).
- Any `gl.nondet.*` call (Stage 6 for evidence, Stage 7 for adjudication).
- Any web retrieval (Stage 6).
- Any native GEN accounting or transfer (Stage 10).
- Any bond math (Stage 10).
- Withdrawal-safe pause behavior (Stage 11).
- `genvm-lint check` CI gate (Stage 12).
- Studio schema-load verification (Stage 13 preparation; user-driven).
- Live capability verification (Stage 15).
- Challenger-reward source decision (Stage 10). Recorded as an OPEN ECONOMIC DECISION (§15).

## 14. Stage 3 readiness

**Ready.** Stage 2 has:

- A compilable, ASCII-only, LF-terminated production source at `contracts/governance_fork.py`.
- Every enum, dataclass, storage map, index, ID counter, and cap centralized and consistent with Stage 1 architecture (with the one architectural change in §5, called out for approval).
- An ABI surface with 29 explicit method signatures — no hidden helpers, no shadow endpoints.
- Placeholder bodies that fail loudly rather than pretending to succeed.

**Not ready to skip Stage 6a or Stage 10.** Those probes / decisions remain blockers on their respective downstream stages regardless of Stage 3's progress.

## 15. OPEN ECONOMIC DECISION — Challenger reward source

Carried forward from Stage 1 review, still unresolved.

Stage 1 §16 (successful challenge → challenger receives 100% refund + reward = 25% of prior fork creator's slashed portion). **The source of the reward is not yet approved or defined.**

Stage 2 has:

- **Not** implemented reward accounting.
- **Not** created a `reward_due` field or liability.
- **Not** assumed rewards come from contract treasury, another user's bond, protocol balance, newly created value, or slash proceeds.
- The `Bond` structure has `settlement_kind ∈ {UNSETTLED, SETTLED_FULL_REFUND, SETTLED_PARTIAL_SLASH, SETTLED_CHALLENGER_REWARD}` as a state marker only, with no amount field beyond the original `amount` posted.

Stage 10 must explicitly determine whether V1 uses:

- **A.** Refund only (no reward). Simplest; loses the "reward the successful challenger" incentive.
- **B.** Reward sourced strictly from attributable slash proceeds (i.e. from the fork creator's slashed 50%). Provably solvent — the reward is a share of already-locked funds. Preferred subject to Stage 10 review.
- **C.** Intentionally prefunded treasury reward (constructor-supplied reward pool). Requires `TREASURY_ADDR` prefunding; solvency must be explicit.
- **D.** Another provably solvent mechanism.

**Stage 2 stance:** Schema reserves the minimum generic settlement/disposition concept required to represent the four settlement kinds. No reward amount, no reward transfer, no reward accounting, no unfunded liability. This decision is deferred to Stage 10 and remains blocking on any reward-related test that Stage 12 might otherwise write.

## 16. Proposed Stage 3 scope

**Stage 3 = DAO registration + Root proposal import + Intent Envelope submission (no adjudication).**

Concretely:

- `register_dao` — validate name/url bounds, allocate `dao_id`, write `Dao`, append to `roots_by_dao`.
- `import_root_proposal` — validate bounds, validate `dao_id` exists, fetch proposal body via `gl.nondet.web.render(proposal_url, "text")` inside `gl.eq_principle.strict_eq`, compute `body_fingerprint`, write `RootProposal` with `envelope_status = ENVELOPE_NOT_SUBMITTED` and `identity_status = IDENTITY_COMMUNITY_IMPORTED`, append to `roots_by_dao`.

Wait — Stage 3 must not implement `gl.nondet.*`. That is Stage 6.

**Corrected Stage 3 scope:**

- `register_dao` — validate + write + index.
- `import_root_proposal` — validate + write + index, and **compute `import_fingerprint` deterministically at import time** (Stage 2B correction; see §17). `web_content_fingerprint` is left `b""` at import and is populated later by the Stage 6 evidence-freeze pathway; `envelope_status = ENVELOPE_NOT_SUBMITTED`; `identity_status = COMMUNITY_IMPORTED`.
- `submit_root_envelope` — validate envelope schema bounds, validate `dao_id` and `root_id` exist, allocate a `ROOT_ENVELOPE` case, allocate evidence records with `frozen = false`, append to indexes. **Bond capture** is Stage 10 — Stage 3 exposes the payable signature but rejects any non-zero `value` explicitly (until Stage 10, calling with `value > 0` raises `UserError`).

That gives Stage 3 a shippable slice of deterministic behavior with no dependency on Stage 6, Stage 7, or Stage 10.

Stage 3 tests (Stage-3-appropriate only): DAO registration happy path, duplicate name (if we disallow), too-long name/url, DAO-not-found in `import_root_proposal`, structured-parameter cap, envelope schema bounds, essential/mutable/immutable dimension cap enforcement, `envelope_status` initial value, index writes match entity writes.

## 17. Root Proposal Fingerprint Model (Stage 2B)

Two distinct fingerprints live on `RootProposal`, cleanly separated by origin and by when they are populated:

### 17.1 `import_fingerprint: bytes` — always set at import

**Purpose.** Deterministic identifier of what the importer actually submitted. Binds the imported root to its canonical form so that any later reader can verify no field was silently mutated.

**Populated at:** Stage 3, inside `import_root_proposal`, before writing to storage.

**Never empty after successful import.** If canonicalization or hashing fails, the whole `import_root_proposal` call is rejected atomically.

**Canonical fields bound:**

| Field | Encoding |
|---|---|
| `dao_id` | decimal ASCII of the `u256` value |
| `external_proposal_id` | UTF-8, bounded ≤ `MAX_EXTERNAL_ID_LEN` |
| `title` | UTF-8, bounded ≤ `MAX_TITLE_LEN` |
| `proposal_url` | UTF-8, bounded ≤ `MAX_URL_LEN` |
| `structured_parameters` | UTF-8, key/value pairs, sorted by `key` ascending |

The **URL is included** because two proposals with identical text at different URLs are semantically distinct in Governance Fork (the URL is the identity of the authoritative source we will later fetch).

The **`proposer` address and `imported_at` timestamp are excluded** because they are metadata about the import event, not about the proposal itself. Re-importing the same proposal from a different address at a different time yields the same `import_fingerprint`, which is the desired property.

**Canonical serialization (V1):**

```
"gf-root/v1"                                              ASCII, 10 bytes
"\n" "dao_id=" <decimal(dao_id)> "\n"                     ASCII
"external_proposal_id=" <utf8(external_proposal_id)> "\n"
"title=" <utf8(title)> "\n"
"proposal_url=" <utf8(proposal_url)> "\n"
"structured_parameters=" "\n"
  for each ParamKV, sorted by key ascending:
    "  " <utf8(key)> "=" <utf8(value)> "\n"
```

The `"gf-root/v1"` prefix is a domain-separation tag: it makes an `import_fingerprint` unusable as any other kind of fingerprint (evidence, delta, envelope) even if the byte content happened to collide. `v1` is the schema version so a future canonicalization change is distinguishable.

**Bounds guarantee unambiguous parsing.** Every string field has a maximum length enforced at validation before hashing (Stage 3's validation gate). Newlines inside a field are rejected at validation time — governance titles, URLs, and structured parameters never legitimately contain `\n`. Rejection at the validation gate keeps the canonical form unambiguous without length-prefixing.

**Algorithm.** SHA-256, if the GenLayer runtime exposes Python's standard `hashlib`.

**Classification: PROVISIONAL CRYPTOGRAPHIC.**

- Intent is a cryptographic hash. SHA-256 is preferred; keccak-256 or blake2b are acceptable substitutes if the runtime exposes them instead.
- Whether Python `hashlib` is exposed inside the GenLayer contract environment is **NOT YET LIVE VERIFIED**. The local reference (`RealityLock`) uses Python `json` from stdlib successfully, which suggests other stdlib modules including `hashlib` are likely available, but this is inference, not proof.
- Verification is a Stage 3 pre-check and a Stage 2B blocker: the manual Studio schema-load (§18) that imports `hashlib` in the module top-level is the earliest signal we can obtain without deploying. If schema-load rejects `import hashlib`, we fall back to a runtime-exposed alternative primitive.
- No unsupported API is invented in Stage 2. The contract source does **not yet** import `hashlib` — that will be added in Stage 3 once the schema-load gate confirms it, or an alternative primitive is chosen.

**Fallback if no cryptographic hash primitive is exposed:** a documented non-cryptographic deterministic byte encoding (the canonical serialization itself, prefix-tagged) may be used as a stopgap identifier. Classified as **PROVISIONAL NON-CRYPTOGRAPHIC** if that path is taken, and the entire economic threat model (§30 of Stage 1) is re-scored against the loss of collision-resistance. That path is not preferred and would trigger a Stage 6 revisit.

### 17.2 `web_content_fingerprint: bytes` — filled later, from the authoritative page

**Purpose.** Deterministic identifier of the actual page content fetched from `proposal_url` through the approved GenLayer web-content pathway. Distinct from `import_fingerprint` because the importer's submitted title/parameters may or may not match the page's content — that is what envelope adjudication decides.

**Populated at:** Stage 6, by the evidence-freeze routine, when the root's authoritative page is fetched and its rendered text is sliced to `MAX_EVIDENCE_SLICE`.

**Empty at import.** `b""` is the sentinel for "not yet fetched." Envelope adjudication in Stage 7 refuses to run if this is empty for the root envelope's authoritative evidence.

**Algorithm.** SHA-256 over the sliced rendered text, wrapped in `gl.eq_principle.strict_eq` so validator consensus is bit-exact. Same runtime-availability caveat as §17.1.

### 17.3 Never overloaded

The two fingerprints are never confused. `import_fingerprint` is about what the importer canonically submitted; `web_content_fingerprint` is about what the world's authoritative source actually said. Their equality or inequality is never a business-logic signal — the semantic-adjudication path handles alignment. But storing them separately makes any later audit unambiguous.

### 17.4 Fingerprints elsewhere (unchanged)

- `Fork.body_fingerprint` and `Fork.delta_fingerprint` — deterministic hashes of the fork's submitted `ForkBody` and `DynArray[DeltaEntry]`. Not related to any web content. Same algorithm caveat.
- `Evidence.content_fingerprint` — deterministic hash of the fetched slice for that specific evidence item. Web-content-derived, populated by `freeze_evidence` at Stage 6.
- `Case.target_fingerprint`, `Case.evidence_set_fingerprint`, `Case.case_fingerprint` — deterministic hashes of the frozen adjudication inputs.

None of these are `web_content_fingerprint` in the RootProposal-specific sense — that field is unique to the root's own page.

## 18. Studio Schema-Load Procedure (Manual — User Action Required)

Stage 2B leaves this as a **manual step for the user** because the automated environment for this session does not have a running GenLayer Studio instance. Studio's schema-load / compile action does not require a chain broadcast; it extracts the ABI from the source and reports errors without deploying. The user runs this locally.

### 18.1 Exact target

| Item | Value |
|---|---|
| Contract path | `contracts/governance_fork.py` |
| Current SHA-256 | *(see the Stage 2B final report; re-run `python tests/stage_2_checks.py` to reproduce)* |
| Byte count | *(see final report)* |
| Line count | *(see final report)* |
| ABI method count | 29 (11 write + 2 admin + 16 view) |
| Depends header | `# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }` |
| Constructor signature | `__init__(self)` — no `-> None`. **Updated post-Stage-6b**: parameterless; `treasury_addr` is set from `gl.message.sender_address` inside `__init__` (see §1 above). |

### 18.2 Exact steps

1. Start GenLayer Studio locally (e.g. via `genlayer up` or the installer entry point).
2. Open the Studio UI in a browser at its usual local URL (typically `http://localhost:8080/` or `http://127.0.0.1:8000/` — Studio prints the actual URL on start).
3. In the **Contracts** panel, choose **New Contract** or **Load Contract**, then paste the entire content of `contracts/governance_fork.py`.
4. Trigger the **Compile** / **Load Schema** action. This is a local schema extraction only. **Do NOT click Deploy.**
5. Wait for the schema panel to render.

### 18.3 Successful schema extraction should show

- No red error toast or console banner.
- Constructor line: `__init__(self)` (parameterless as of the post-Stage-6b deploy-compatibility correction; treasury/admin resolves to the deployer's own address).
- 29 methods in the method list, with these names (order may vary):

  Writes (11): `register_dao`, `import_root_proposal`, `submit_root_envelope`, `create_fork`, `submit_fork_evidence`, `freeze_evidence`, `freeze_case`, `adjudicate`, `challenge_verdict`, `finalize`, `settle_bond`.

  Admin (2): `pause`, `unpause`.

  Views (16): `get_dao`, `list_daos`, `get_root_proposal`, `list_root_proposals_by_dao`, `get_fork`, `list_forks_of_root`, `list_forks_of_parent`, `get_verdict_history`, `get_verdict`, `get_evidence`, `list_evidence_of_case`, `get_case`, `get_challenge`, `list_challenges`, `get_bond`, `get_constants`.

- `submit_root_envelope`, `create_fork`, `challenge_verdict` each marked **payable**.
- Return type panel resolves `Dao`, `RootProposal`, `Fork`, `Evidence`, `Case`, `VerdictRecord`, `Challenge`, `Bond`, `PageIds`, `ConstantsView` as `@allow_storage @dataclass` records.
- Storage panel shows: 8 entity `TreeMap`s (`daos`, `roots`, `forks`, `evidence`, `cases`, `verdicts`, `challenges`, `bonds`), 8 index `TreeMap`s, 8 `u256` counters, `treasury_addr: Address`, `paused: bool`.

### 18.4 Likely failure signatures to capture

| Symptom | Likely cause | Action |
|---|---|---|
| Toast: "Schema load failed: `__init__`" | Constructor annotation issue | Verify no `-> None` on `__init__`. |
| Toast: "Unknown type `u256`" or `u32` | Runtime primitive mismatch | Report to Stage 2B: primitive list needs revision. |
| Toast: "Cannot serialize `DynArray[str]`" inside `IntentEnvelope` | Generic nesting limitation | Report; may need to promote nested `DynArray[str]` fields to bounded dataclass records. |
| Toast: "Depends: unknown package" | `Depends` hash mismatch with installed SDK | Report the current SDK version so we can update the hash. |
| Toast referencing `@allow_storage @dataclass` | Decorator ordering or import missing | Verify `from genlayer import *` exposes both decorators; verify the class has both decorators in the correct order. |
| Some methods missing from the ABI list | Decorator not recognized or method-name conflict | Capture the exact missing names; compare against §33 of Stage 1. |
| "Payable methods must accept `value` in the body" | Runtime requires body to reference `gl.message.value` when marked payable | Report; Stage 3 will add an explicit `if gl.message.value != u256(0): raise` at the top of each payable body. |
| Any other unfamiliar error | Unknown | Copy the exact error text and file path/line into the Stage 2B report. |

### 18.5 If Studio cannot test schema without deployment

Studio's local compile/schema-load is expected to succeed without broadcasting. If the installed Studio version has removed the local schema-only path and only supports full deploy, the user should **stop and report that**. Deployment is user-controlled and out of Stage 2B scope. Governance Fork Stage 2B does not require deployment to pass.

### 18.6 Reporting back

Whether pass or fail, the user reports the outcome and any error text. Pass → Stage 3 unblocks. Fail → Stage 2B revisits based on the specific error.

### 18.7 Result — PASSED

**MANUAL STUDIO SCHEMA LOAD: PASSED** on `contracts/governance_fork.py` at SHA-256 `14362bb511cd573559b7db78d62d06f9963ec42b2f7065db210d9787209b355e` (bytes 18 430, lines 645). ABI count: **29** (11 write + 2 admin + 16 view). No deployment. No broadcast. The Studio-load path was blocked twice before this pass:

1. First attempt (SHA `b40b02939b750cbbd6538d72443c32996f10a2b7f20caac6058130c8cd0cda1d`) failed with `NameError: name 'dataclass' is not defined` at line 202. Cause: `from genlayer import *` does not re-export `dataclass`; the local reference (`RealityLock`) does not use `@dataclass` at all so this had not been exercised.
2. A `runner comment does not start with version, using default v0.1.0` warning surfaced from the runner log, confirming the memory note about a `# vX.Y.Z` tag on line 1.

**Applied fix (committed as a Stage 2B follow-up):** added `# v0.2.16` as line 1 and `from dataclasses import dataclass` after `from genlayer import *`. No other changes.

**What this proves — and does not prove.** Studio's `gen_getContractSchemaForCode` succeeded, so the source parses, the schema extractor resolves every type in the ABI, and every `@allow_storage @dataclass` record was registered. Every subsequent stage may rely on the shape of the schema.

Runtime business logic — including typed `TreeMap[u256, DataClass]` set/get, `DynArray[u256]` mutation semantics, `hashlib.sha256(...)` invocation, `gl.message.sender_address` usage, `gl.vm.UserError` raising, and every state transition — has **NOT been live verified**. Schema-load and runtime execution are different gates. Runtime verification is Stage 15.

## 19. Payable-Signature Review

**Scope.** `submit_root_envelope`, `create_fork`, `challenge_verdict` are marked `@gl.public.write.payable` in the scaffold, even though bond capture is Stage 10.

**Decision: KEEP payable now.** Reasoning:

1. **ABI stability.** Any integrator that reads the schema between Stage 2B and Stage 10 (frontends, indexers, other Intelligent Contracts) may cache the payable/non-payable classification. Flipping a method from non-payable to payable later is a breaking ABI change for cached clients. Keeping it payable now costs nothing and prevents a needless migration.
2. **Atomic rollback.** Each body raises `gl.vm.UserError("stage-2: not implemented")` on the first line. In the confirmed local-reference pattern (`../RealityLock/contracts/reality_lock.py`), an unhandled raise rolls back the entire transaction atomically — including any `value` that would have been transferred with the call. The state is unchanged and the sender's `value` is not retained. Effectively, calling one of these methods with `value > 0` today reverts and returns the funds, exactly as if the call had never been made.
3. **Belt-and-suspenders arrives in Stage 3.** Stage 3 will add an explicit `if gl.message.value != u256(0): raise gl.vm.UserError("value not yet accepted")` at the top of each payable body, before any Stage 3 logic runs. This is a defensive check that costs 1 line per method and eliminates any possibility of accidental value acceptance during the Stage 3 → Stage 10 window. It is not implemented at Stage 2B because Stage 2B does not touch method bodies beyond the current `raise`.
4. **Alternative rejected.** Making the three methods non-payable now and re-enabling payable at Stage 10 would (a) create the ABI migration risk in point 1, (b) require the user to redeploy or run a schema-only re-load at Stage 10 for integrators to see the change, (c) not remove any real risk today (see point 2).

**No bond capture logic is implemented at Stage 2B.** Payable exposure is ABI shape only.

## 20. `CLAIM_UNCHANGED` — Final V1 Architecture

Approved: `CLAIM_UNCHANGED` is omitted from V1 permanently.

**V1 rules (final):**

1. Only actually changed dimensions appear in `Fork.delta`. Enum values: `NARROWED`, `BROADENED`, `RESHAPED`, `REMOVED`, `ADDED`.
2. A dimension absent from `Fork.delta` is claimed unchanged.
3. Deterministic freeze-time validation confirms every parent parameter not covered by a `DeltaEntry` matches parent-side exactly. Any mismatch rejects the fork with reason `UNCLAIMED_MUTATION`.
4. `envelope.immutable_dimensions` is independently checked against the parent regardless of delta contents; any mismatch is `IMMUTABLE_DIMENSION_MUTATION`, rejected at freeze.
5. Stage 1 §8.1 has been updated to reflect this final decision.
6. Stage 2 contract source and Stage 2B check `no unchanged delta kind` enforce omission going forward.

No further discussion required.

## 21. Confirmations

- ✅ Zero `gl.nondet.*` calls in Stage 2 / 2B (grep-checked; see §11).
- ✅ Zero web retrieval in Stage 2 / 2B.
- ✅ Zero semantic adjudication logic in Stage 2 / 2B.
- ✅ Zero native GEN accounting or transfer in Stage 2 / 2B.
- ✅ Challenger reward source remains unresolved and unimplemented (§15).
- ✅ Root import fingerprint model is defined and never empty after successful import (§17).
- ✅ Payable-signature decision is documented (§19: KEEP).
- ✅ `CLAIM_UNCHANGED` omission is final V1 architecture (§20).
- ✅ Nothing was deployed or broadcast.
- ✅ Frontend was not built.
- ✅ Stage 3 was not started.
