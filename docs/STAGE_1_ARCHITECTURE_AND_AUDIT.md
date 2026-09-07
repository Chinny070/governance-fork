# GOVERNANCE FORK — Stage 1 Architecture & Audit

**Status:** Stage 1 only. No production contract has been implemented. No frontend has been built. Nothing has been deployed or broadcast. Stage 2 has not begun.

**Tagline:** *"Don't vote YES or NO. Change the proposal."*

---

## 1. Product Thesis

DAO governance is routinely reduced to a binary choice (YES / NO / ABSTAIN) even when the underlying proposal has multiple independent, opinionated dimensions — amount, duration, eligibility, recipient class, milestones, payout schedule, execution timing, scope, and implementation constraints. A voter who supports the proposal's underlying objective but disagrees with one dimension has no clean action: they either accept the whole thing, reject the whole thing, argue in a forum, hope the author rewrites it, or manually author a new proposal from scratch.

**Governance Fork turns governance proposals into branching, inspectable objects.** Every root proposal becomes the root of a fork tree. Any community member may create a *fork*: a bounded, evidence-backed descendant of a parent proposal that declares exactly what changed and what stayed the same, and claims that its changes remain faithful to the parent's declared governance objective.

```
                    ROOT PROPOSAL
                   /      |      \
                 F1       F2       F3
                / \                  \
              F4   F5                 F6
```

The product is neither a voting system nor an amendment system. It is a **semantic descendant registry with immutable branching provenance**. The DAO still votes wherever the DAO already votes. Governance Fork changes what the DAO can vote *on*.

---

## 2. Core Trust Problem

**GenLayer does NOT decide** whether a proposal is good, whether a fork should be adopted, or whether a DAO should approve anything. Governance Fork is not a replacement for DAO voting.

**GenLayer answers exactly one bounded question per fork:**

> *"Does the proposed fork remain materially faithful to the frozen parent proposal's declared governance objective and essential constraints, while accurately representing the declared changes, based only on the frozen submitted evidence?"*

That question is **constrained** (fixed schema, fixed evidence set, fixed parent), **auditable** (every input is frozen and citable), and **materially dependent on semantic consensus** (no deterministic string diff can decide whether "$50k over 3 months" is a faithful narrowing of "$100k over 6 months for developer grants" — that requires reading the parent's intent envelope, the delta, and the evidence together).

The architecture rejects the naive shape *"user edits proposal → LLM reads it → LLM says faithful → store result"*. Instead:

1. The parent proposal, its Intent Envelope, and its parameter set are **frozen** before any fork can be created against it.
2. The fork's declared delta and evidence set are **frozen** in a separate transaction before adjudication runs.
3. Adjudication receives a bounded, pre-committed input and must return a schema-conformant judgment along fixed semantic dimensions.
4. A deterministic validator checks the model output against the frozen inputs; any deviation rolls back atomically.
5. Challenges target specific defect classes, not popularity.
6. Bond disposition is deterministic given the finalized verdict; bond size never enters semantic reasoning.

---

## 3. Why GenLayer Is Necessary

A non-GenLayer stack (deterministic smart contract + off-chain LLM) cannot solve this problem safely:

- **Semantic faithfulness cannot be reduced to a deterministic diff.** "Ecosystem developer funding, $100k, 6 months" vs "Ecosystem developer funding, $50k, 3 months" is faithful; "Ecosystem developer funding, $50k, 3 months, restricted to one specific team" changes the beneficiary class and is not. A deterministic contract cannot distinguish these.
- **Off-chain LLM oracles are unaccountable.** They give one operator unilateral control of the semantic verdict and cannot be adjudicated on-chain.
- **Live authoritative evidence must be readable at adjudication time.** Only GenLayer's `gl.nondet.web.get` / `gl.nondet.web.render` inside `gl.eq_principle.*` gives on-chain semantic consensus over web-authoritative content.
- **Challenges require on-chain re-adjudication with the same frozen inputs.** GenLayer's Optimistic Democracy semantics make this a first-class construct.
- **Bond slashing and refunds must be governed by the finalized verdict.** That requires the verdict, its inputs, and the bond ledger to live in the same trust boundary — a single Intelligent Contract with native GEN.

GenLayer is not decoration here. Remove it and the product collapses into "please trust the LLM host."

---

## 4. Reusable Primitive: Semantic Proposal Forking

**Definition.** A reusable primitive for creating bounded, evidence-backed descendants of governance proposals while preserving semantic intent, exact deltas, and immutable branching provenance.

**Primitive shape.**

```
Parent → Declared Intent → Fork → Delta → Evidence → GenLayer Judgment
       → Challenge → Finality → Bond Disposition
```

**Intended reuse surfaces** (not V1 obligations): treasury allocations, grant programs, incentive programs, fee proposals, risk parameters, contributor programs, protocol policy, ecosystem funding, governance-process changes.

V1 stays tightly scoped to a single generic proposal shape. The primitive is designed so that a later specialization (e.g. `RiskParameterFork` with typed numeric dimensions) can be layered on the same tree/evidence/adjudication substrate without breaking the branching model.

---

## 5. Branching, Not Linear Versioning

This is architecturally mandatory and drives most of the storage decisions.

- Multiple forks of the same parent **coexist**. Creating F2 does not invalidate F1.
- A fork **does not automatically supersede** its parent, nor its siblings, nor any ancestor.
- Lineage is a **tree**, not a chain. Every fork has exactly one parent (which may be the root proposal itself or another finalized fork).
- Parent linkage is immutable. There is no rebase, reparent, or move operation.
- Every fork stores or derives: `fork_id`, `parent_id`, `root_proposal_id`, `depth`, `creator`, `status`, `child_count`, `frozen_parent_fingerprint`, `originating_case_id`, `finality`.

**Recommended tree caps (V1):**

- `MAX_DEPTH_PER_ROOT = 8`
- `MAX_CHILDREN_PER_PARENT = 32`
- `MAX_TOTAL_FORKS_PER_ROOT = 512`

These are conservative starting values chosen so that (a) trees stay renderable in a bounded UI, (b) pagination is trivial, and (c) an attacker cannot cheaply blow up storage. They are configurable at deployment.

**Fork-of-disputed-parent rule (V1 recommendation):** Only forks whose parent is `FINALIZED_FAITHFUL` may themselves be forked. This eliminates the "child of a NOT_FAITHFUL parent" ambiguity, keeps children's inputs stable, and avoids cascading invalidation. Documented in §20.

---

## 6. Intent Envelope

The Intent Envelope is the single largest differentiator of Governance Fork. It is the parent's declared, structured governance intent, frozen at import time. All fork adjudication is done against it.

### 6.1 V1 Envelope Schema

| Field | Type | Semantic vs Deterministic | Notes |
|---|---|---|---|
| `objective` | `str` (bounded 512 chars) | semantic | Prose statement of the proposal's governance goal. |
| `beneficiary_class` | `str` (bounded 128 chars) | semantic | Who benefits (e.g. "ecosystem developers", "liquidity providers"). |
| `resource_type` | enum `{TREASURY, PROTOCOL_PARAMETER, POLICY, GRANT_POOL, INCENTIVE_BUDGET, OTHER}` | deterministic | Bounded enum. |
| `scope` | `str` (bounded 256 chars) | semantic | Scope statement. |
| `essential_constraints` | `DynArray[str]` (≤ 8 items, each ≤ 128 chars) | semantic | Constraints the fork must preserve. |
| `mutable_dimensions` | `DynArray[str]` (≤ 16 items, each ≤ 64 chars) | semantic-tagged, checked | Dimensions a fork MAY change (e.g. "allocation", "duration"). |
| `immutable_dimensions` | `DynArray[str]` (≤ 16 items, each ≤ 64 chars) | semantic-tagged, checked | Dimensions a fork MAY NOT change (e.g. "beneficiary_class", "resource_type"). |
| `parent_proposal_fingerprint` | `bytes32` | deterministic | keccak256 of the imported proposal body slice. |
| `envelope_version` | `u32` | deterministic | Schema version for forward compat. |

### 6.2 Envelope Bootstrapping (Recommended Path)

Four candidates were considered:

- **A. Importer declares; GenLayer verifies against official evidence.** Simple, but importer chooses envelope wording.
- **B. GenLayer derives envelope directly from proposal URL.** Removes human control; hard to audit; brittle if a page format changes.
- **C. Importer proposes envelope; GenLayer adjudicates whether it faithfully represents the root proposal, using the same evidence machinery as fork adjudication.** More work, but reuses the same primitive and keeps human authorship auditable.
- **D. Deterministic template.** Only works for narrow proposal families.

**V1 recommendation: C.** Importer submits envelope + at least one `OFFICIAL_GOVERNANCE` evidence URL. A dedicated adjudication case (`case_type = ROOT_ENVELOPE`) runs the same `INTENT_PRESERVATION` / `EVIDENCE_SUPPORT` / `SOURCE_AUTHORITY` / `INTERNAL_CONSISTENCY` dimensions against a slightly reworded question:

> *"Does the submitted Intent Envelope faithfully represent the declared governance objective, beneficiary class, resource type, and essential constraints of the frozen root proposal, based only on the frozen submitted evidence?"*

If the envelope is `FAITHFUL`, it is frozen and forks may be created against it. If `NOT_FAITHFUL`, the envelope may be resubmitted (fresh case, fresh bond) or the root proposal is left with `envelope_status = REJECTED`.

Envelope challenges are supported and use the same challenge grounds as fork challenges.

---

## 7. Root Proposal Ingestion

### 7.1 Data Model

| Field | Type | Notes |
|---|---|---|
| `root_id` | `u64` | Auto-assigned. |
| `dao_id` | `u64` | Foreign key. |
| `external_proposal_id` | `str` (bounded 128) | ID in the source system, e.g. Snapshot proposal ID. |
| `title` | `str` (bounded 256) | |
| `proposal_url` | `str` (bounded 512) | Canonical source URL. |
| `proposer` | `Address` | Submitting community member (not the original DAO proposer unless proven). |
| `body_fingerprint` | `bytes32` | keccak256 of the fetched proposal body slice. |
| `structured_parameters` | `DynArray[ParamKV]` (≤ 32) | Optional deterministic key/value pairs. |
| `envelope` | `IntentEnvelope` | Per §6. |
| `envelope_status` | enum | `PROPOSED / ADJUDICATING / FINALIZED_FAITHFUL / REJECTED`. |
| `evidence_ids` | `DynArray[u64]` (≤ 8) | Evidence used for envelope adjudication. |
| `imported_at` | `u64` | Block time. |
| `identity_status` | enum | `COMMUNITY_IMPORTED / DAO_VERIFIED_LATER / UNVERIFIED`. Default `COMMUNITY_IMPORTED`. |

### 7.2 Identity Honesty

The frontend and any read method that returns a root proposal MUST label it by `identity_status`. A `COMMUNITY_IMPORTED` proposal is not the DAO's official proposal — it is a public governance proposal that a community member imported for forking. V1 has no verified path to a DAO's own signing key; that is a later stage. Any UI that displays "Official DAO proposal" without the verified status is a product bug.

---

## 8. Fork Delta Model

Every fork must declare exactly what it changes. Free-form "I changed some things" is disallowed as the sole delta representation.

### 8.1 Structured Delta

```
DeltaEntry {
  dimension_name: str (≤ 64)         # must match a name from envelope.mutable_dimensions
  parent_value:   str (≤ 256)         # frozen from parent's structured_parameters or resulting_state
  fork_value:     str (≤ 256)
  claim_kind:     enum { NARROWED, BROADENED, RESHAPED, REMOVED, ADDED, UNCHANGED }
}
```

- A fork produces `DynArray[DeltaEntry]` (≤ 16).
- Every dimension a fork claims to change MUST appear as a `DeltaEntry` with `claim_kind != UNCHANGED`.
- Every dimension in `envelope.immutable_dimensions` MUST either be absent or appear with `claim_kind = UNCHANGED` and identical values.
- Any dimension present in the resulting fork body that is not listed as a `DeltaEntry` (change or unchanged) is a **candidate undeclared change** and flagged by the adjudicator under `UNDECLARED_SEMANTIC_CHANGE`.

### 8.2 Resulting Fork State

The fork also stores its resulting proposal body:

```
ForkBody {
  title: str (≤ 256)
  summary: str (≤ 1024)
  structured_parameters: DynArray[ParamKV] (≤ 32)
  reasoning: str (≤ 1024)             # why this fork exists
}
```

`ForkBody.structured_parameters` MUST be derivable from `parent.structured_parameters` by applying the declared `DeltaEntries`. This is a deterministic pre-check performed by the contract before evidence freeze; if it fails, the fork is rejected at freeze time with reason `DELTA_APPLICATION_MISMATCH`.

---

## 9. Semantic Adjudication Question & Dimensions

**Exact V1 question:**

> *"Given the frozen parent Intent Envelope E, the frozen parent structured parameters P, the fork's declared delta D and resulting body B, and the frozen evidence set V, does fork body B remain materially faithful to E while accurately representing D, considering ONLY V? Do not consider popularity, bond size, author identity, or evidence outside V."*

**Final dimensions.** Seven candidate dimensions were listed; after review the V1 set is:

| # | Dimension | Kept? | Notes |
|---|---|---|---|
| 1 | `INTENT_PRESERVATION` | ✅ | Core question. |
| 2 | `DELTA_ACCURACY` | ✅ | Do declared deltas match B vs P? |
| 3 | `UNDECLARED_SEMANTIC_CHANGE` | ✅ | Any change in B not declared in D. |
| 4 | `EVIDENCE_SUPPORT` | ✅ | Does V actually support the claims? |
| 5 | `SOURCE_AUTHORITY` | ✅ | Are cited sources authoritative for their claims? |
| 6 | `TEMPORAL_RELEVANCE` | ✅ | Is the evidence current relative to the parent? |
| 7 | `INTERNAL_CONSISTENCY` | ✅ | Does D + B + E cohere? |

All seven are retained. Each dimension is scored as one of three bounded findings:

`SATISFIED / NOT_SATISFIED / UNCLEAR`

No weighted numeric scores.

### 9.1 Verdict Gates (Deterministic)

Given the seven findings, the deterministic verdict is:

- If `INTENT_PRESERVATION == NOT_SATISFIED` **or** `UNDECLARED_SEMANTIC_CHANGE == NOT_SATISFIED` **or** `DELTA_ACCURACY == NOT_SATISFIED` → `NOT_FAITHFUL`.
- Else if any of `EVIDENCE_SUPPORT`, `SOURCE_AUTHORITY`, `TEMPORAL_RELEVANCE`, `INTERNAL_CONSISTENCY` is `NOT_SATISFIED` → `NOT_FAITHFUL`.
- Else if any dimension is `UNCLEAR` → `UNCLEAR_VERDICT` (see §14).
- Else all seven `SATISFIED` → `FAITHFUL`.
- If model output is schema-malformed → `INVALID`.

The gate is computed by the deterministic validator, not the model. The model returns only per-dimension findings and per-dimension reasoning; the validator applies the gate.

---

## 10. Fetch Web Content — Verified Pattern

### 10.1 What the current official docs assert

Source: `https://docs.genlayer.com/developers/intelligent-contracts/examples/fetch-web-content` and `.../features/non-determinism`.

- Import: `from genlayer import *`.
- Two verified functions:
  - `gl.nondet.web.get(url: str)` → response object with `.body: bytes` (decode with UTF-8).
  - `gl.nondet.web.render(url: str, mode: str, wait_after_loaded: str | None = None)` → `str`. `mode ∈ {"html", "text"}`.
- Must be called inside a nondeterministic block. The idiomatic pattern is to wrap the fetching function in `gl.eq_principle.strict_eq(...)` when we want bit-exact validator agreement, or in `gl.eq_principle.prompt_comparative(...)` / `.prompt_non_comparative(...)` for semantic-tolerance agreement.
- Nondet blocks **cannot be nested**.
- Storage writes must happen **outside** the nondet block, after consensus.
- Docs explicitly note web content should be "relatively stable" for consensus.
- Docs are silent on hard size / timeout limits.

### 10.2 What Governance Fork will use

- **Evidence page fetching (deterministic content):** `gl.nondet.web.render(url, "text")` wrapped in `gl.eq_principle.strict_eq(...)`. The fetched text is sliced to `MAX_EVIDENCE_SLICE = 16 KiB` inside the nondet function so the return value is bounded before consensus. A content fingerprint (`keccak256` of the slice) is stored on the evidence record.
- **Semantic adjudication:** The bounded evidence set is materialized into a single deterministic prompt (parent envelope + delta + fork body + evidence slices), and adjudication runs as `gl.eq_principle.prompt_comparative(adjudicate_fn, principle_str)`, where `adjudicate_fn` calls `gl.nondet.exec_prompt(prompt)`. The comparison principle is a fixed constant string embedded in the contract, not user-controlled.
- **No custom renderer, no backend scraping, no frontend-provided content, no Supabase/Firebase.**

### 10.3 Capability Classification

| Capability | Status |
|---|---|
| `from genlayer import *`, `@gl.public.view`, `@gl.public.write`, `@gl.public.write.payable` | **CONFIRMED CURRENT OFFICIAL DOCS** |
| `gl.nondet.web.get`, `gl.nondet.web.render(url, mode, wait_after_loaded)` | **CONFIRMED CURRENT OFFICIAL DOCS** |
| `gl.eq_principle.strict_eq`, `gl.eq_principle.prompt_comparative`, `gl.eq_principle.prompt_non_comparative` | **CONFIRMED CURRENT OFFICIAL DOCS** |
| `gl.nondet.exec_prompt` | **CONFIRMED CURRENT OFFICIAL DOCS** |
| Storage types `u32`, `u64`, `bigint`, `bool`, `str`, `bytes`, `Address`, `DynArray[T]`, `TreeMap[K, V]` | **CONFIRMED CURRENT OFFICIAL DOCS** |
| `@allow_storage` + `@dataclass` for custom storage classes | **CONFIRMED CURRENT OFFICIAL DOCS** |
| `@gl.public.write.payable` accepts incoming value | **CONFIRMED CURRENT OFFICIAL DOCS** |
| Exact API to read incoming native GEN (e.g. `gl.message.value`) | **DOCUMENTED BUT NOT LIVE VERIFIED** — mentioned in narrative form; exact API to be confirmed in Stage 10 against live SDK. |
| Exact API to transfer native GEN outbound | **UNKNOWN** — no dedicated page fetched; treated as UNKNOWN until Stage 10 live verification. |
| Nondet nesting prohibition | **CONFIRMED CURRENT OFFICIAL DOCS** |
| Static lint tool `genvm-lint check` | **CONFIRMED CURRENT OFFICIAL DOCS** |
| Studio schema-load gotchas (long leading comment blocks, non-ASCII bytes, typed `__init__`) | **LIVE VERIFIED ELSEWHERE** (my prior Continuum / Treasury Trial work). Applied preemptively to V1. |

Nothing in Stage 1 silently promotes an `UNKNOWN` to an implementation assumption. The two `UNKNOWN` / not-live-verified items (native GEN read/send APIs) are called out again in §16 and become explicit blockers for Stage 10.

---

## 11. Evidence Architecture & Authority Model

### 11.1 Evidence Record

```
Evidence {
  evidence_id:        u64
  case_id:            u64
  submitter:          Address
  url:                str (≤ 512)
  normalized_source:  str (≤ 128)     # eTLD+1 of URL, lowercased
  evidence_class:     EvidenceClass    # enum below
  relevance_claim:    str (≤ 256)      # why the submitter thinks this evidence matters
  authority_claim:    str (≤ 128)      # what authority the submitter claims for the source
  temporal_marker:    str (≤ 64)       # date/version claim
  content_fingerprint: bytes32         # keccak256 of the fetched slice; 0x0 if not yet frozen
  submitted_at:       u64
  frozen:             bool
}
```

### 11.2 EvidenceClass Enum (Bounded)

```
OFFICIAL_GOVERNANCE      # DAO-controlled proposal/vote record
OFFICIAL_DOCUMENTATION   # DAO- or protocol-controlled docs
OFFICIAL_TREASURY        # DAO treasury reports, dashboards
FINALIZED_DECISION       # A ratified governance vote result
GOVERNANCE_DISCUSSION    # Forum threads, not decisions
IMPLEMENTATION_SPEC      # RFC/spec/whitepaper
AUDIT                    # Security audit
THIRD_PARTY_ANALYSIS     # Anything else the submitter classifies as analysis
```

The submitter picks the class; the adjudicator scores whether the class is defensible under `SOURCE_AUTHORITY`. A misclassified evidence item (e.g. a forum comment tagged `FINALIZED_DECISION`) is grounds for `NOT_SATISFIED` on `SOURCE_AUTHORITY` and, if severe, `INVALID`.

### 11.3 Authority Rules Baked Into the Adjudicator Prompt

- A governance *proposal* is **not** a finalized governance *decision*.
- A forum comment is **not** an official governance record even if authored by a known contributor.
- Two evidence items on different subdomains of the same eTLD+1 are **not** independent.
- Third-party analysis is a supporting source, never authoritative for a fact about the DAO's own state.

These rules are constants in the contract and are visible on-chain.

---

## 12. Evidence Freeze

Freeze is a **separate transaction** from adjudication. This is mandatory because nondeterministic consensus can fail or return `Undetermined`, and we cannot afford to lose the case if that happens.

**On freeze the contract commits:**

- `fork_id`, `root_id`, `parent_id`
- `parent_fingerprint`, `parent_envelope_fingerprint`
- `declared_delta_fingerprint` (keccak of canonically serialized `DynArray[DeltaEntry]`)
- `resulting_body_fingerprint`
- `evidence_ids` (frozen ordered list)
- `evidence_content_fingerprints` (populated by a preceding `freeze_evidence` call per URL)
- `adjudication_dimensions_version`
- `case_fingerprint` = keccak of all the above

**Adjudication is called on a frozen case only.** If adjudication fails or `Undetermined`, the frozen case remains committed; a new adjudication attempt can be triggered without re-freezing.

**Evidence pages are fetched during the `freeze_evidence(evidence_id)` call**, once per evidence item. Each `freeze_evidence` runs inside `gl.eq_principle.strict_eq(fetch)` and writes back `content_fingerprint` and `frozen = true`. Repeat freeze is a no-op if `frozen == true`.

---

## 13. Untrusted Web Content & Prompt Injection

Fetched pages are **data, not instructions**. The adjudicator prompt is constructed so that no evidence content can rewrite the task.

Mitigations, all baked into the adjudication prompt template:

1. **Fixed system instructions** at the top of the prompt, prohibiting execution of instructions found in evidence.
2. **Explicit delimiters** around each evidence slice: `<<<EVIDENCE evidence_id=N BEGIN>>> … <<<EVIDENCE evidence_id=N END>>>`.
3. **Bounded slices** (`MAX_EVIDENCE_SLICE = 16 KiB`) prevent prompt-scale attacks.
4. **Frozen evidence set** — the model cannot fetch anything else; there is no live browsing tool available to it.
5. **Deterministic output schema** — the model returns a JSON-shaped object with fixed fields; any deviation fails the validator and rolls back atomically.
6. **Known reason codes** — reasoning free text is bounded and reason codes are drawn from a fixed enum.
7. **No caller-provided prompt fragments.** The submitter's `relevance_claim` and `authority_claim` are treated as claims about the evidence, not as instructions, and are rendered inside explicit `SUBMITTER_CLAIM` delimiters.

The model MUST NOT: follow embedded instructions, invent URLs, browse outside V, use bond size in reasoning, treat popularity as authority, rewrite E, hide contradictory evidence, or invent authorities.

---

## 14. Verdict Vocabulary

Final verdict enum:

```
FAITHFUL          # descendant remains inside parent's semantic intent envelope
NOT_FAITHFUL      # fork materially changes core intent or makes undeclared changes
UNCLEAR_VERDICT   # semantic dimensions returned UNCLEAR — no finding on faithfulness
INVALID           # malformed model output; case rolls back
```

Chosen over `ACCEPTED / REJECTED` because Governance Fork is **not** deciding political merit. `FAITHFUL` explicitly means "inside the intent envelope"; it does not mean "should be adopted." The frontend copy is written to reflect this.

`UNCLEAR_VERDICT` is a first-class outcome, not fake certainty. It carries an itemized list of the dimensions that returned `UNCLEAR` and the reasons. A fork with `UNCLEAR_VERDICT` may be resubmitted for adjudication with additional evidence (fresh case, fresh bond), or the DAO may still consider it, understanding that GenLayer did not conclude.

`INVALID` is narrow — only schema-malformed model output or violation of deterministic pre-checks. It never means "the fork is bad."

---

## 15. Challenge Model

Challenges target specific adjudication defects, not "I dislike this fork."

**Challenge grounds (bounded enum):**

```
INTENT_MISREAD                   # envelope was misinterpreted
DELTA_MISCLASSIFIED              # DELTA_ACCURACY got a fact wrong
UNDECLARED_CHANGE_IGNORED        # UNDECLARED_SEMANTIC_CHANGE missed a real change
SOURCE_AUTHORITY_ERROR           # an evidence class was overweighted or underweighted
TEMPORAL_EVIDENCE_ERROR          # stale evidence was accepted, or fresh evidence was ignored
CONTRADICTORY_EVIDENCE_OMITTED   # relevant contradiction inside V was ignored
MALFORMED_ADJUDICATION           # output failed structural expectations that slipped past the validator
```

### 15.1 Rules

- Any address may challenge a fork's verdict during its `CHALLENGE_WINDOW` (V1: 72 hours).
- Challenger posts `CHALLENGE_BOND` (V1: same as fork bond, so griefing costs match griefer's target).
- **One open challenge at a time per fork.** Serial, not parallel — simpler state, and the second challenger's reasoning may benefit from the first challenger's outcome anyway.
- Max 3 challenges per fork lifetime.
- A challenge triggers a fresh adjudication case (`case_type = CHALLENGE`) with the original frozen inputs plus the challenger's ground code and free-text argument (bounded 512 chars, rendered inside `<<<CHALLENGE BEGIN>>>` delimiters).
- The replacement verdict is stored **alongside** the original, not overwritten. The fork's current `finalized_verdict` pointer moves to the newest verdict; historical verdicts remain readable through `get_fork_verdict_history(fork_id)`.
- If the new verdict differs from the challenged verdict, challenger is refunded; original creator's bond disposition is recomputed against the new verdict. If the verdict stands, challenger's bond is slashed (or partially slashed per §16).

### 15.2 Finality

A fork is finalized when either (a) its challenge window elapses with no open challenge and no unresolved challenge, or (b) it has hit `MAX_CHALLENGES_PER_FORK`. Finalization triggers bond disposition and locks the verdict.

---

## 16. Native GEN Economics

**Design principle:** bonds create accountability for spam and for adjudicative misrepresentation. Bonds MUST NOT create accountability for honest political disagreement. A community member proposing an alternative should not fear losing a large stake merely because their fork is semantically bounded but politically unpopular.

### 16.1 V1 Recommendation

- `FORK_CREATION_BOND` (small anti-spam, e.g. `0.1 GEN` initial, configurable).
- `ENVELOPE_BOND` for root-envelope adjudication (same size).
- `CHALLENGE_BOND` equal to `FORK_CREATION_BOND`.

**Disposition table:**

| Finalized Verdict | Fork Creator Bond | Notes |
|---|---|---|
| `FAITHFUL` | Refund 100% | The fork was inside the envelope. |
| `NOT_FAITHFUL` | Refund 50%, slash 50% to `TREASURY_ADDR` | Partial slash: penalizes undeclared changes and misrepresentation without punishing honest but unsuccessful alternatives. |
| `UNCLEAR_VERDICT` | Refund 100% | GenLayer did not conclude; do not punish. |
| `INVALID` | Slash 100% | Malformed or deceptive submissions only. |

Rationale for partial slash on `NOT_FAITHFUL`: the whole point of Governance Fork is to encourage proposing alternatives. Full slashing on any `NOT_FAITHFUL` verdict creates a chilling effect that undermines the primitive. A malicious actor pushing junk still pays through the anti-spam bond and the partial slash; an honest submitter whose fork was semantically over-reach still recovers half.

**Challenger disposition (same partial-slash logic):**

| Challenge Outcome | Challenger Bond |
|---|---|
| New verdict differs from prior verdict | Refund 100% + reward = 25% of prior fork creator's slashed portion. |
| New verdict matches prior verdict | Refund 50%, slash 50% to `TREASURY_ADDR`. |

**Hard rules:**

- Bond amount MUST NOT appear anywhere in the adjudication prompt.
- Bond payout destination is fixed (`fork.creator` for refund, `TREASURY_ADDR` for slash). **No caller-selected payout recipient.**
- Every bond has an idempotency flag (`bond.settled: bool`) so double payout is impossible.
- Refund + slash percentages MUST sum to exactly 100% per bond.
- `TREASURY_ADDR` is set at contract deployment and immutable.

### 16.2 Native GEN API — Status

Reading incoming value and outbound transfer of native GEN are the two remaining unknowns from §10.3. Stage 10 (native GEN economics) will:

1. Live-verify the exact SDK surface against the current runtime — likely `gl.message.value`, likely a `.transfer` primitive, but Stage 1 does **not** assume the exact names.
2. Implement bond capture in the payable method and bond disposition in a separate deterministic call.
3. Add a full unit test for double-payout impossibility.

Stage 1 does not claim these APIs are proven; they are `UNKNOWN` until Stage 10.

---

## 17. DAO Decision vs GenLayer Decision

**Explicit language, propagated to contract read methods, frontend, and Portal copy:**

> **GenLayer determines** whether a fork is a faithful semantic descendant of its parent under the frozen Intent Envelope and submitted evidence.
>
> **The DAO / community determines** whether the fork should actually be adopted.

A `FAITHFUL` fork is **not** approved, enacted, superior, financially sound, or politically popular. It is a faithful descendant, and that is all.

This limitation is fundamental to the product. Any UI, contract event, or copy that blurs the line is a bug to fix, not a feature to lean into.

---

## 18. Adoption Status (Deferred)

Candidate states considered: `FORK_FINALIZED`, `EXTERNALLY_ADOPTED`, `NOT_ADOPTED`, `UNKNOWN`.

**Recommendation: NOT in V1.** Verifying real-world adoption requires either (a) trust in the community reporter (which weakens the honesty guarantee), or (b) a second GenLayer adjudication case with new evidence classes. Either belongs in a later stage.

V1 exposes only `finalized_verdict ∈ {FAITHFUL, NOT_FAITHFUL, UNCLEAR_VERDICT, INVALID}`. Adoption is out of scope.

---

## 19. Tree Safety & Concurrency

### 19.1 Structural Invariants Enforced On Fork Creation

- `parent_id` must reference an existing fork or the root proposal itself.
- `parent.dao_id == fork.dao_id == root.dao_id`.
- `parent.root_id == fork.root_id`.
- No self-parent, no cycles (impossible because `parent_id` must reference an already-finalized fork, and finalization order is strictly historical).
- `parent_fingerprint` supplied at creation must equal the stored `parent.body_fingerprint` at that block; otherwise reject with `STALE_PARENT`.
- Depth check: `fork.depth = parent.depth + 1 ≤ MAX_DEPTH_PER_ROOT`.
- Children cap: `parent.child_count < MAX_CHILDREN_PER_PARENT`.
- Root total cap: `root.total_fork_count < MAX_TOTAL_FORKS_PER_ROOT`.

### 19.2 Fork-of-Disputed-Parent

**V1 recommendation: only `FINALIZED_FAITHFUL` forks may themselves be forked.** This is a deliberate simplification. Rationale:

- Eliminates cascading invalidation trees.
- Guarantees a fork's frozen `parent_envelope_fingerprint` refers to a verdict-stable ancestor.
- Trivially prevents forking off `INVALID` or `NOT_FAITHFUL` ancestors.
- Preserves the semantic guarantee that any node in the tree can be traced along a fully `FAITHFUL` chain back to the root.

The alternative (allow forking off non-final parents and cascade-invalidate on parent status change) is more expressive but multiplies the state machine's edges and creates race conditions that Stage 1 does not want to underwrite. The `FINALIZED_FAITHFUL`-only rule can be relaxed later without breaking historical data.

### 19.3 Semantic Duplicate Detection

Two different forks may declare the same delta. V1 does NOT enforce semantic uniqueness — this is a governance activity, not a chain-integrity concern. The read layer offers `similar_deltas(fork_id)` for UX, but the contract accepts duplicates so the tree remains an honest record of what people submitted.

---

## 20. Root Proposal Selection Criteria (Highlight Prep)

For the eventual highlight demo, target root proposals meeting:

- Accessible through supported GenLayer web rendering (`gl.nondet.web.render` returns useful text).
- Clear, stable proposal text (not a live-edit page).
- Official governance source (Snapshot / Tally / a DAO's own governance portal).
- Understandable mutable parameters (amount, duration, eligibility, milestones).
- Enough public evidence for at least three fork adjudications.
- No private data dependency (no gated forum, no discord-only sources).

**Stage 1 does NOT select or deploy a specific live proposal.** Concrete selection happens in Stage 19.

---

## 21. Read-Only Proposal Explorer (Hero UX)

The Proposal Tree is the product's identity. It must be usable without a wallet.

**Tree layout (indicative wireframe):**

```
PROPOSAL #91 · Developer Grants        [envelope: FAITHFUL] · $100k · 6 months
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
      FORK A            FORK B            FORK C
      $50k · 3mo        $100k · 6mo        $100k · 12mo
      NARROWED          RESHAPED           BROADENED
      FAITHFUL          NOT_FAITHFUL       UNCLEAR_VERDICT
        │                 │
     ┌──┴──┐              │
     │     │              │
   A1     A2            B1  (challenge #1 open)
```

**Per-node card fields:**

- title
- changed dimensions (compact chips)
- creator (truncated address)
- status (`DRAFT / EVIDENCE_FROZEN / ADJUDICATING / FINAL`)
- verdict (`FAITHFUL / NOT_FAITHFUL / UNCLEAR / INVALID / —`)
- evidence count
- open challenges count
- bond disposition badge (`bonded / refunded / slashed`)

**On node click, a detail pane shows:**

Parent · Intent Envelope · Declared Delta · Resulting Proposal · Evidence (with source class chips) · GenLayer per-dimension findings · Challenges (with grounds) · Finality · Bond Disposition · Children.

Every field is a bounded read from the contract.

---

## 22. Product Pages (Proposed Routes)

```
/                          — Explore (recent activity, tree previews)
/dao/:daoId                — DAO summary and imported roots
/proposal/:rootId          — Root proposal + top-level tree
/fork/:forkId              — Fork detail + subtree
/fork/:forkId/evidence     — Evidence trail
/fork/:forkId/challenges   — Challenge history
/methodology               — How adjudication works (public transparency)
/integrate                 — Read-method docs for other frontends
/create                    — Import proposal / create fork (wallet-gated)
```

Priority: **read-only discovery first.** `/create` is last.

---

## 23. Highlight-Worthy UX

Stage 1 commitments the eventual frontend must honor:

- **Proposal Tree hero.** No landing page that looks like "a form + contract address + tx list."
- **Branch expansion with animation.** Clicking a node expands children in place.
- **Parent-vs-child delta visualization.** Side-by-side chips with green `NARROWED`, blue `RESHAPED`, purple `BROADENED`, gray `UNCHANGED`.
- **Evidence trace.** Every dimension finding links to the evidence slice it was based on.
- **Semantic verdict trace.** Per-dimension `SATISFIED / NOT_SATISFIED / UNCLEAR` displayed inline with reasoning, not hidden behind a modal.
- **Challenge indicators.** Ground code badges on the fork node.
- **Finality state.** Clear "final" vs "in adjudication" vs "in challenge window" ribbons.
- **"What changed?" widget.** Above every fork detail card, before anything else.

A steward should understand the product in under 15 seconds of looking at the tree.

---

## 24. Usage Loop

```
new DAO proposal
  → community member imports proposal + envelope
  → users create alternatives (bonded forks)
  → evidence accumulates
  → forks adjudicated
  → challenges occur
  → community compares finalized faithful alternatives
  → new descendants emerge from finalized faithful forks
  → DAO votes on adoption using the tree
```

**Concrete user actions:**

| User | Action |
|---|---|
| DAO voter | Reads the tree before voting; picks a specific faithful fork to endorse. |
| Delegate | Publishes the fork they'll vote for and why (linking a Governance Fork node). |
| Governance researcher | Studies branching patterns across DAOs. |
| Proposal author | Imports own proposal; watches faithful forks emerge; incorporates strongest ones into a revised submission. |
| Grant committee | Imports a grant program proposal; solicits bounded forks (e.g. narrower eligibility, longer milestones). |
| Treasury committee | Same pattern applied to treasury allocations. |
| Governance platform | Consumes read methods to render trees inside their own UI. |
| Protocol community | Uses tree as long-term governance memory across amendments. |

No vague "ecosystem" claims.

---

## 25. Integration Potential

**Bounded read methods** enable another interface to consume the tree without a custom indexer for basic use:

- `get_root_proposal(root_id) → RootProposalView`
- `get_intent_envelope(root_id) → IntentEnvelopeView`
- `get_fork(fork_id) → ForkView`
- `list_forks_of_parent(parent_id, cursor, limit) → PaginatedForkList`
- `list_children(fork_id, cursor, limit) → PaginatedForkList`
- `get_delta(fork_id) → DynArray[DeltaEntry]`
- `get_fork_verdict(fork_id) → VerdictView`
- `get_fork_verdict_history(fork_id, cursor, limit) → PaginatedVerdictList`
- `list_evidence(case_id, cursor, limit) → PaginatedEvidenceList`
- `get_evidence(evidence_id) → EvidenceView`
- `list_challenges(fork_id, cursor, limit) → PaginatedChallengeList`
- `get_finality(fork_id) → FinalityView`
- `get_bond_disposition(fork_id) → BondDispositionView`

All lists are paginated with `cursor` (u64) and `limit` (u8 ≤ 50).

---

## 26. No Backend

Target stack: **Frontend + Intelligent Contract only.** No Supabase, Firebase, custom API, indexer, or serverless functions.

If Stage 2+ discovers a genuine unavoidable technical limitation, work stops and the user is asked before adding one. No stealth backend.

---

## 27. Storage Caps (V1)

| Cap | Value |
|---|---|
| `MAX_DAOS` | 1024 |
| `MAX_ROOT_PROPOSALS_PER_DAO` | 256 |
| `MAX_FORKS_PER_ROOT` | 512 |
| `MAX_CHILDREN_PER_PARENT` | 32 |
| `MAX_DEPTH_PER_ROOT` | 8 |
| `MAX_EVIDENCE_PER_CASE` | 16 |
| `MAX_CHALLENGES_PER_FORK` | 3 |
| `MAX_URL_LEN` | 512 |
| `MAX_PROPOSAL_TITLE_LEN` | 256 |
| `MAX_OBJECTIVE_LEN` | 512 |
| `MAX_SCOPE_LEN` | 256 |
| `MAX_BENEFICIARY_CLASS_LEN` | 128 |
| `MAX_ESSENTIAL_CONSTRAINTS` | 8 × 128 chars each |
| `MAX_MUTABLE_DIMENSIONS` | 16 × 64 chars each |
| `MAX_IMMUTABLE_DIMENSIONS` | 16 × 64 chars each |
| `MAX_DELTA_ENTRIES` | 16 |
| `MAX_DELTA_VALUE_LEN` | 256 |
| `MAX_REASONING_LEN` | 1024 |
| `MAX_EVIDENCE_SLICE` | 16 KiB per evidence item |
| `MAX_CHALLENGE_ARGUMENT_LEN` | 512 |
| `PAGINATION_LIMIT_MAX` | 50 |

Tradeoffs: caps are chosen so that the entire adjudication prompt (envelope + delta + fork body + 16 evidence × 16 KiB) stays well under any reasonable model context, and so that any single read never returns unbounded data. Every cap is a deployment-time constant so Stage 15 (live capability verification) can tune them if the runtime forces changes.

---

## 28. Deterministic Validator

The semantic model NEVER writes storage directly. Between model output and any state change, the deterministic validator MUST verify:

1. Output is valid JSON matching the fixed schema.
2. Verdict enum is one of `{FAITHFUL, NOT_FAITHFUL, UNCLEAR_VERDICT, INVALID}`.
3. Exactly the seven expected dimensions appear, no duplicates, no unknown keys.
4. Each dimension's finding is one of `{SATISFIED, NOT_SATISFIED, UNCLEAR}`.
5. Every evidence reference cited in dimension reasoning is a member of the frozen `evidence_ids`.
6. `fork_id`, `parent_id`, `root_id` in output match the frozen case.
7. `envelope_fingerprint`, `delta_fingerprint`, `evidence_set_fingerprint` in output match the frozen case.
8. Reasoning strings are within bounds (per-dimension ≤ 512 chars, total ≤ 4096).
9. Reason codes belong to the fixed enum.
10. Deterministic verdict gate (§9.1) is re-applied on the validator side; if it disagrees with the model's declared verdict, verdict is set from the gate and a `VERDICT_GATE_OVERRIDE` event is emitted.

Any validation failure → `INVALID` verdict, atomic state rollback, evidence remains frozen, bond disposition per §16.

---

## 29. Undetermined Consensus Handling

Treated as a first-class condition, not a bug.

Contract side:
- `adjudicate(case_id)` returns a `verdict_status ∈ {SUCCESS, UNDETERMINED, INVALID}`.
- On `UNDETERMINED`, no verdict is stored; case remains in `ADJUDICATING`.
- A public `retry_adjudication(case_id)` can be called after a `RETRY_COOLDOWN` (V1: 1 hour) to trigger a new consensus attempt against the same frozen inputs. Max retries per case: 3.

Frontend side (contract for later stage):
1. Submit tx.
2. Poll consensus result.
3. Distinguish success, `UNDETERMINED`, timeout, and canceled.
4. **Re-read authoritative state** before claiming success — never trust the returned semantic value.
5. Verify the expected state transition (`case.verdict != None`).
6. Only then show success in UI.

Evidence freeze and semantic adjudication are separate txs specifically because freeze is deterministic and always succeeds; if adjudication is `UNDETERMINED`, evidence is not lost.

---

## 30. Threat Model

| # | Threat | Impact | Mitigation | Residual Limitation |
|---|---|---|---|---|
| 1 | Fake DAO identity | Users trust bogus DAO | `identity_status` labels; `COMMUNITY_IMPORTED` is default and visible | V1 has no cryptographic proof of DAO ownership |
| 2 | Fake root proposal | Adjudication runs on fabricated proposal | Envelope adjudication requires `OFFICIAL_GOVERNANCE` evidence, frozen with fingerprint | Submitter can still cite a plausible but fake page — mitigated by `SOURCE_AUTHORITY` scoring |
| 3 | Manipulated proposal text between import and adjudication | Wrong envelope frozen | `parent_body_fingerprint` frozen at import; envelope is bound to it | Source page can change post-freeze; content_fingerprint remains stable in our record |
| 4 | Malicious Intent Envelope | Envelope reshapes proposal to allow anything | Envelope adjudication case with same seven dimensions; challenge grounds cover `INTENT_MISREAD` | UNCLEAR envelope leaves fork adjudications blocked until resolved |
| 5 | Misleading fork delta | Delta hides real change | `DELTA_ACCURACY` and `UNDECLARED_SEMANTIC_CHANGE` dimensions; deterministic pre-check on delta application | Semantic tricks (renaming a dimension) still catchable only semantically |
| 6 | Undeclared semantic change | Fork claims cosmetic change while altering core intent | `UNDECLARED_SEMANTIC_CHANGE` dimension; every dimension in body must appear in delta or be UNCHANGED | Model may miss subtle rewording |
| 7 | Fake authoritative evidence | Bogus URL treated as official | `EvidenceClass` submitter-declared, adjudicator scores `SOURCE_AUTHORITY` | Same-eTLD+1 sock puppetry can slip through single-source cases |
| 8 | Mutable URLs (page changes after freeze) | Adjudication input drifts from what a later reader sees | `content_fingerprint` frozen on `freeze_evidence`; adjudication uses the frozen slice, not a fresh fetch | Original URL can 404 later — historical record still cites content fingerprint |
| 9 | Prompt injection in evidence | Model executes attacker instructions | §13 defenses (delimiters, fixed system, no browsing, bounded slice, schema validator, reason-code enum) | No mitigation is complete; combination is deep defense |
| 10 | Evidence flooding | Adjudicator swamped with weak sources | `MAX_EVIDENCE_PER_CASE = 16`; submitter must classify each | Submitter can still pick 16 weak items — reflected in low `SOURCE_AUTHORITY` |
| 11 | Duplicate evidence | Padding the case | Contract deduplicates by normalized URL within a case | Semantic duplicates across different URLs not detected |
| 12 | Circular citations | Two sources cite each other | `SOURCE_AUTHORITY` guidance treats same-eTLD+1 as one source | Explicit citation graph tracking is out of scope |
| 13 | Stale evidence | Old data used for current claim | `TEMPORAL_RELEVANCE` dimension; submitter declares `temporal_marker` | Model must judge relevance from prose |
| 14 | Governance proposal treated as decision | Confuses "proposed" with "adopted" | Prompt constant: proposal ≠ decision; `EvidenceClass` separates them | Submitter can still misclassify |
| 15 | Semantic fork spam | Cheap noise floods the tree | Anti-spam `FORK_CREATION_BOND`; `MAX_FORKS_PER_ROOT`; `MAX_CHILDREN_PER_PARENT` | Motivated attacker can pay the bond |
| 16 | Tree explosion | Storage / render blowup | Depth cap 8, per-parent cap 32, per-root cap 512 | Adjustable per-deployment |
| 17 | Deep-tree griefing | Attacker maxes depth before honest users can | Depth cap; per-parent cap | Community can block by refusing to finalize child forks |
| 18 | Challenge spam | Bond griefing via challenges | `CHALLENGE_BOND`; `MAX_CHALLENGES_PER_FORK = 3`; challenger's bond at risk | Rich attacker can still exhaust challenges |
| 19 | Cross-DAO confusion | Fork of parent from a different DAO | Structural invariant `parent.dao_id == fork.dao_id` | Enforced at fork creation |
| 20 | Cross-root parent | Fork claims a parent from a different root | `parent.root_id == fork.root_id` invariant | Enforced |
| 21 | Forged lineage | Fork claims a fake parent fingerprint | `parent_fingerprint` supplied must match `parent.body_fingerprint` at creation block | Enforced |
| 22 | Stale parent | Fork uses an out-of-date parent fingerprint | Same fingerprint check | Reject with `STALE_PARENT` |
| 23 | Malformed adjudication | Model returns garbage | Deterministic validator → `INVALID`, rollback | Bond disposition per §16 |
| 24 | Evidence hallucination | Model cites URL not in V | Validator checks evidence refs are members of frozen `evidence_ids` | Enforced |
| 25 | Double payout | Bond paid twice | `bond.settled: bool` idempotency flag | Enforced |
| 26 | Replay | Same case executed twice | Case `state ∈ {FROZEN, ADJUDICATING, VERDICT_PROPOSED, FINAL}`; transitions guarded | Enforced |
| 27 | Undetermined consensus | Case stuck | `retry_adjudication` with cooldown; max 3 retries; case can be marked `UNDETERMINED_TERMINAL` | Bond disposition: full refund on terminal undetermined |
| 28 | Popularity used as authority | Model rewards viral sources | Prompt constant forbids popularity as authority | Semantic pressure only |
| 29 | Bond size used in reasoning | Rich attackers "buy" a verdict | Bond amount not in prompt; visible in read methods only | Enforced |
| 30 | Caller-selected payout recipient | Redirecting slashed bond | Payout destinations fixed | Enforced |
| 31 | Amount inflation on refund | Overpaying refund | Deterministic math: refund_pct + slash_pct == 100 | Enforced |

---

## 31. Differentiation Audit (At Least Seven Substantive Differences)

Compared to existing governance / amendment-style projects (including linear proposal-versioning systems and generic on-chain proposal registries):

1. **Branching tree lineage, not linear amendment lineage.** Multiple alternatives coexist as siblings and can themselves be forked. Amendment systems collapse everything into `v1 → v2 → v3`.
2. **Immutable structured Intent Envelope per root**, adjudicated by GenLayer, not free-form prose. No existing user project on the Portal ships this construct.
3. **Structured, typed Fork Delta with per-dimension `claim_kind`**, verified by both a deterministic pre-check and a semantic adjudicator.
4. **Semantic descendant validation** — GenLayer decides "faithful to parent's declared objective," not "is this proposal good."
5. **No automatic policy replacement.** A finalized fork does not supersede its parent or siblings. The DAO's own voting process remains authoritative.
6. **Bounded, evidence-frozen adjudication** with an explicit seven-dimension schema and deterministic verdict gates. Evidence is frozen with content fingerprints before adjudication runs.
7. **Community comparison UI as hero experience.** The Proposal Tree is the product, not a form.
8. **Read-only usefulness without a wallet.** Almost every existing dApp needs a wallet to see anything.
9. **Deterministic partial-slash economics** designed explicitly to encourage honest alternatives — most staking / bond systems in governance apps assume full slash on failure.
10. **DAO retains adoption decision** as an explicit product principle, propagated to on-chain events, read methods, and copy.

Ten substantive differences; the requirement was ≥ 7. Governance Fork is not a renamed amendment system.

---

## 32. Current GenLayer Capability Audit (Re-cap)

See §10.3 above. In summary:

- All contract shape, storage type, decorator, non-determinism, and web-fetch APIs used in Stage 2+ are **CONFIRMED CURRENT OFFICIAL DOCS**.
- Native GEN incoming-value read API is **DOCUMENTED BUT NOT LIVE VERIFIED** (Stage 10 dependency).
- Native GEN outbound transfer API is **UNKNOWN** (Stage 10 dependency).
- Studio schema-load gotchas (long leading comments, non-ASCII bytes, typed `__init__`) are **LIVE VERIFIED ELSEWHERE** — Stage 2 will preemptively avoid them: no leading docstring wall, ASCII-only source, no `__init__(self) -> None` annotation.
- `genvm-lint check` will be part of the Stage 12 test plan.

Nothing `UNKNOWN` has been silently upgraded to an assumption.

---

## 33. Proposed ABI

### 33.1 Write Methods

| Method | Caller | Payable | Purpose |
|---|---|---|---|
| `register_dao(name, url) -> u64` | any | no | Registers a DAO record; returns `dao_id`. |
| `import_root_proposal(dao_id, external_proposal_id, title, proposal_url, structured_parameters) -> u64` | any | no | Freezes root proposal and its body fingerprint via `gl.nondet.web.render(proposal_url, "text")`. |
| `submit_root_envelope(root_id, envelope, evidence_urls, temporal_markers) -> u64` | any | payable (`ENVELOPE_BOND`) | Opens envelope adjudication case. |
| `freeze_evidence(evidence_id)` | any | no | Fetches the URL, computes content fingerprint, marks frozen. |
| `adjudicate_envelope(case_id)` | any | no | Runs envelope adjudication via `gl.eq_principle.prompt_comparative`. |
| `create_fork(parent_id, parent_fingerprint, delta, resulting_body) -> u64` | any | payable (`FORK_CREATION_BOND`) | Creates a fork against a `FINALIZED_FAITHFUL` parent; runs deterministic delta-application pre-check. |
| `submit_fork_evidence(fork_id, evidence_urls, evidence_classes, relevance_claims, authority_claims, temporal_markers) -> u64` | fork creator only | no | Opens fork adjudication case. |
| `freeze_case(case_id)` | any | no | Freezes the entire case fingerprint (envelope, delta, evidence set). |
| `adjudicate_fork(case_id)` | any | no | Runs fork adjudication. |
| `retry_adjudication(case_id)` | any | no | After `RETRY_COOLDOWN`; max 3. |
| `challenge_verdict(fork_id, ground_code, argument) -> u64` | any | payable (`CHALLENGE_BOND`) | Opens challenge case. |
| `adjudicate_challenge(case_id)` | any | no | Runs challenge adjudication. |
| `finalize_fork(fork_id)` | any | no | After challenge window closes with no open challenge; triggers bond disposition. |
| `settle_bond(fork_id)` | any | no | Idempotent; pays out per §16. |
| `pause()` / `unpause()` | `TREASURY_ADDR` only | no | Emergency pause; only blocks new writes. |

### 33.2 View Methods

All are `@gl.public.view`, bounded return, paginated where applicable.

`get_dao`, `list_daos`, `get_root_proposal`, `list_root_proposals_by_dao`, `get_intent_envelope`, `get_fork`, `list_forks_of_root`, `list_forks_of_parent`, `list_children`, `get_delta`, `get_fork_body`, `get_fork_verdict`, `get_fork_verdict_history`, `list_evidence`, `get_evidence`, `list_challenges`, `get_challenge`, `get_finality`, `get_bond_disposition`, `get_case`, `get_constants` (all storage caps and bond amounts), `get_pause_state`.

### 33.3 Validation Rules Applied To Every Write

- Caller not blocked (V1: no block list; hook exists for later).
- Contract not paused (except `unpause`).
- All string lengths within caps.
- All enum values valid.
- All referenced IDs exist.
- All fingerprints match frozen values.
- Payable methods: `msg.value == required_bond` exactly, no over/under.
- Idempotency for finalization / settlement.

---

## 34. State Machines

### 34.1 Root Proposal

```
IMPORTED
  → envelope_status transitions independently:
    ENVELOPE_NOT_SUBMITTED
      → ENVELOPE_ADJUDICATING
        → ENVELOPE_FAITHFUL      (forks may be created)
        → ENVELOPE_REJECTED      (may re-submit envelope)
        → ENVELOPE_UNCLEAR       (may re-submit envelope)
```

### 34.2 Fork

```
DRAFT
  → EVIDENCE_OPEN
    → EVIDENCE_FROZEN
      → CASE_FROZEN
        → ADJUDICATING
          → VERDICT_PROPOSED
            → CHALLENGE_WINDOW
              → CHALLENGE_OPEN
                → CHALLENGE_ADJUDICATING
                  → VERDICT_PROPOSED   (loop, up to MAX_CHALLENGES_PER_FORK)
              → FINALIZED_FAITHFUL
              → FINALIZED_NOT_FAITHFUL
              → FINALIZED_UNCLEAR
              → FINALIZED_INVALID
                → BOND_SETTLED         (terminal)
```

### 34.3 Evidence Case

```
OPEN
  → EVIDENCE_FROZEN     (each evidence item independently transitions)
    → CASE_FROZEN
      → ADJUDICATING
        → SUCCESS
        → UNDETERMINED  → (retry, up to 3) → SUCCESS or UNDETERMINED_TERMINAL
        → INVALID
```

### 34.4 Adjudication

```
INIT
  → FETCHING_SEMANTIC
    → VALIDATOR_CHECK
      → PASS   → VERDICT_STORED
      → FAIL   → VERDICT_INVALID
```

### 34.5 Challenge

```
OPEN
  → ADJUDICATING
    → NEW_VERDICT_DIFFERS      → challenger_refunded + rewarded, creator recomputed
    → NEW_VERDICT_MATCHES      → challenger partial slash
    → INVALID                  → challenger partial slash
```

### 34.6 Bond

```
BONDED
  → SETTLEMENT_PENDING
    → SETTLED (idempotent; guarded by bond.settled flag)
```

---

## 35. Test Plan

Unit tests must NOT require live internet or real GEN. Live capability checks are Stage 15.

Coverage per §35 items:

- DAO registration (happy path, duplicate name).
- Proposal import (URL length caps, fingerprint stability under identical body).
- Envelope submission (schema validation, mutable/immutable set overlap rejected).
- Root proposal fingerprint deterministic across identical bodies.
- Fork creation happy path, wrong parent DAO, wrong root, depth cap, per-parent cap, per-root cap.
- Deterministic delta-application pre-check: reject if `ForkBody.structured_parameters` differ from parent's after applying declared deltas.
- Unchanged-fields enforcement (immutable dimensions).
- Evidence add / dedup by normalized URL.
- Evidence freeze pathway with mocked `gl.nondet.web.render` returning a canned slice.
- Unavailable page, malformed page, oversized page (slice at 16 KiB boundary).
- Prompt injection payload embedded in evidence slice; verify adjudicator response schema unchanged.
- Authority classification stress tests (proposal vs decision, same eTLD+1, forum vs docs).
- Semantic adjudication with mocked `gl.eq_principle.prompt_comparative` returning fixed structured responses (each verdict class).
- Malformed model output → `INVALID`, atomic rollback, evidence still frozen, bond not settled.
- Unknown evidence ref in model output → `INVALID`.
- Envelope fingerprint mismatch, delta fingerprint mismatch, evidence set fingerprint mismatch.
- Undeclared semantic change flagged even when model would otherwise accept.
- Challenge happy path (verdict flips, verdict stands, malformed challenge).
- Verdict replacement writes new record without overwriting history.
- Finality: settle after window elapses, cannot settle before, cannot settle twice.
- Bond capture (payable), refund path, slash path, refund + slash == 100%, idempotent settle.
- Double-payout impossible test.
- Replay-guard test on `finalize_fork` and `settle_bond`.
- Cross-DAO isolation, cross-root isolation.
- Pagination boundary, invalid cursor, limit > 50.
- Pause/unpause: only `TREASURY_ADDR`; blocks writes only; reads unaffected.
- Undetermined consensus: retry cooldown enforced; max retries; terminal path.
- Atomic rollback on validator failure: no partial state written.

Additionally, a `genvm-lint check` gate in CI (Stage 12).

---

## 36. Portal / Steward Quality Gate

| # | Question | Grade | Rationale |
|---|---|---|---|
| 1 | Solves a real trust problem? | **PASS** | Binary voting hides multi-dimensional intent; forking is a real primitive many DAOs need. |
| 2 | GenLayer materially necessary? | **PASS** | Semantic descendant judgment cannot be reduced to deterministic diff; live web evidence required. |
| 3 | Uses live/authoritative data? | **PASS** | Fetches real governance URLs at freeze time via official `gl.nondet.web.render`. |
| 4 | Uses official Fetch Web Content? | **PASS** | Exact mechanism verified in §10. |
| 5 | Different from boilerplate governance? | **PASS** | Branching tree + Intent Envelope + typed delta + partial-slash economics. |
| 6 | Different from existing user projects? | **PASS** | ≥ 10 substantive differences in §31. |
| 7 | Substantially more than better LLM response? | **PASS** | Envelope adjudication, deterministic validator, frozen evidence, on-chain challenge, bonded economics. |
| 8 | Frontend can call contract through full lifecycle? | **PASS (architected)** | Read + write + payable + pagination + Undetermined handling all in ABI. |
| 9 | Credible path to continued usage? | **PASS** | Every new governance cycle is fresh input. |
| 10 | Strong community-facing use case? | **PASS** | Voters, delegates, researchers, authors, committees each have a concrete action. |
| 11 | Reason to return repeatedly? | **PASS** | New DAO proposals continuously import; existing trees accept new forks. |
| 12 | Another app can consume outputs? | **PASS** | Bounded read methods designed for external frontends. |
| 13 | Read-only browsing valuable? | **PASS** | Proposal Tree is the hero UX with no wallet needed. |
| 14 | Proposal Tree immediately understandable? | **PASS** | Chip-based delta viz + verdict badges + parent-child relationships. |
| 15 | Steward-verifiable outcome? | **PASS** | See §37. |
| 16 | Credible highlight potential? | **PASS (contingent)** | Contingent on Stage 19 selecting a strong real proposal for the demo. |

No `FAIL`, no `WEAK`. One `PASS (contingent)`.

---

## 37. Preliminary Submission Positioning

**Project name:** Governance Fork

**Tagline:** *"Don't vote YES or NO. Change the proposal."*

**Primary Portal tag:** `Governance` (secondary: `Reputation/Curation` if tag exists). Rationale: the project is DAO-governance-adjacent but does not replace voting; a Governance tag is the closest fit and matches how DAO voters and delegates will search.

**One-liner:**
Governance Fork turns DAO proposals into branching, evidence-backed trees of bounded alternatives — each fork adjudicated by GenLayer for semantic faithfulness to its parent's declared intent, never for political merit.

**Short description (≈ 60 words):**
Governance Fork is a semantic descendant registry for DAO proposals. Community members import a proposal, GenLayer freezes its Intent Envelope, and any user can create bonded forks that declare exactly what changed. GenLayer adjudicates whether each fork remains faithful to the parent's declared objective under the frozen evidence. Challenges target specific defects. The DAO still decides adoption.

**Full description (≈ 220 words):**
DAO governance often reduces multi-dimensional proposals to YES / NO / ABSTAIN, forcing voters to accept or reject the whole thing when they'd rather change one dimension. Governance Fork replaces "argue about it or write your own proposal" with a first-class primitive: fork any imported governance proposal, declare exactly what you changed and left unchanged, attach evidence, and let GenLayer adjudicate whether your fork remains materially faithful to the parent's declared objective. Every fork lives at a specific node in an immutable branching tree — parents, siblings, and descendants all coexist. Forks never automatically supersede parents or siblings; the DAO's own voting process remains authoritative for adoption. Evidence is fetched through GenLayer's official Fetch Web Content pattern, frozen with content fingerprints before adjudication runs. Adjudication scores seven fixed semantic dimensions with three bounded findings each, and a deterministic verdict gate computes the final `FAITHFUL / NOT_FAITHFUL / UNCLEAR_VERDICT / INVALID`. Challenges must target one of seven specific defect classes and are bonded. Bond economics use partial slashing so honest but unsuccessful alternatives are not chilled. A Proposal Tree hero UI makes the whole record readable without a wallet. Read methods are designed so other governance interfaces can render Governance Fork trees inside their own product without a custom indexer.

**How-to steps (steward-verifiable):**

1. Register a DAO or select an existing one.
2. Import a real public governance proposal (real URL, real title). The contract freezes its body fingerprint via `gl.nondet.web.render`.
3. Submit a proposed Intent Envelope with at least one `OFFICIAL_GOVERNANCE` evidence URL.
4. Freeze envelope evidence; adjudicate the envelope. Observe `ENVELOPE_FAITHFUL`.
5. Create three forks with visibly different bonded structured deltas — one clearly faithful narrowing, one borderline reshape, one with an undeclared shift.
6. Attach at least two authoritative evidence URLs to each fork case.
7. Freeze evidence; freeze case; adjudicate each fork.
8. Challenge one verdict on a specific ground code (e.g. `UNDECLARED_CHANGE_IGNORED`).
9. Wait for the challenge window; call `finalize_fork` and `settle_bond` for each fork.
10. Read the full tree via `list_forks_of_root`, `list_children`, `get_fork_verdict_history`, `get_bond_disposition` and reconstruct the branching lineage.

**Steward-verifiable outcome:**
A steward can inspect a real governance proposal, verify its frozen Intent Envelope, create multiple bonded descendant forks with explicit deltas and authoritative evidence, observe GenLayer adjudicate whether each fork remains faithful to its parent, challenge a verdict on a specific semantic defect, and reconstruct the immutable branching lineage from the root proposal through finalized descendants — using only the deployed Intelligent Contract and the read-only frontend.

**No website URL, no contract address invented. Both are Stage 14 / Stage 20 deliverables.**

---

## 38. Intelligent Contract Submission Warning

Governance Fork is being built as a **project**. Its production contract is domain-specific and does **not** meet the current IC (Intelligent Contract) contribution bar for reusable primitives.

Do NOT propose the production contract as an IC submission. Do NOT optimize the design around IC-eligibility. Should a genuinely independent reusable primitive later emerge (e.g. a generic "Semantic Descendant Registry" library another builder could integrate outside Governance Fork without dragging in project-specific storage), that library — not the project contract — would be the candidate.

No dual-reward optimization.

---

## 39. Highlight Demo Plan (Stage 19)

**Not built in Stage 1.** Designed here so Stage 2+ knows what it's building toward.

1. Load one real public governance proposal — Snapshot- or Tally-hosted, with stable text.
2. Show its frozen Intent Envelope (adjudicated `FAITHFUL`).
3. Create three visibly different forks:
    - **Fork A**: clearly faithful parameter change (e.g. duration 6 → 3 months, allocation halved proportionally).
    - **Fork B**: borderline reshape requiring genuine semantic judgment (e.g. milestone-based payout replacing lump sum).
    - **Fork C**: fork with a hidden / undeclared intent change (e.g. declares only allocation change while covertly restricting `beneficiary_class`).
4. Attach real authoritative evidence: original governance proposal, official DAO docs, prior treasury report, related finalized decision.
5. Fetch each evidence page through official `gl.nondet.web.render`.
6. Adjudicate all three forks. Expected: A → `FAITHFUL`, B → `UNCLEAR_VERDICT` or `FAITHFUL` with narrow reasoning, C → `NOT_FAITHFUL` with `UNDECLARED_SEMANTIC_CHANGE = NOT_SATISFIED`.
7. Challenge fork B on `INTENT_MISREAD` or similar; observe replacement verdict.
8. Wait for challenge window; finalize each.
9. Settle bonds — refund for A, partial slash for C, refund for B under `UNCLEAR_VERDICT`.
10. Show the full branching tree with per-node verdicts, per-dimension findings, evidence trace, and bond disposition.
11. Highlight the semantic step in the tree where GenLayer's judgment mattered: it's the one no deterministic contract could have made.

---

## 40. Roadmap

| Stage | Deliverable | Notes |
|---|---|---|
| 1 | Architecture & audit | **This document.** No code, no deploy. |
| 2 | Contract scaffold, storage layout, ABI signatures | Empty method bodies with type signatures and validation stubs. |
| 3 | DAO / root proposal / Intent Envelope | Import + fingerprint + envelope schema. |
| 4 | Branching fork model + delta pre-check | Structural invariants + deterministic delta application. |
| 5 | Evidence architecture | Evidence records, freeze pathway, dedup. |
| 6 | Official web retrieval | `gl.nondet.web.render` inside `gl.eq_principle.strict_eq`. |
| 7 | GenLayer adjudication | Envelope + fork + challenge adjudication with `prompt_comparative`. |
| 8 | Deterministic validator | Schema, fingerprint, verdict-gate checks. |
| 9 | Challenge system | Grounds, bond capture, replacement verdict, history. |
| 10 | Native GEN economics | **Live-verify** value read/send APIs; partial-slash logic. |
| 11 | Security caps, pagination, pause | Storage caps, cursor pagination, admin pause path. |
| 12 | Full tests | Unit tests + `genvm-lint check` in CI. |
| 13 | Manual StudioNet deployment preparation | Env, ABI export, deployment doc. |
| 14 | **User manually deploys production contract** | Claude does NOT deploy. |
| 15 | Live capability / lifecycle verification | Confirm all `UNKNOWN` / `DOCUMENTED BUT NOT LIVE VERIFIED` items. |
| 16 | Proposal Tree frontend | Read-only Explorer first. |
| 17 | Full transaction lifecycle + consensus revalidation | Wallet paths, Undetermined handling, state re-read. |
| 18 | Integration / read-only UX polish | External-frontend friendly reads. |
| 19 | Real governance proposal demo | Per §39. |
| 20 | GitHub / Vercel / release package | Stable URLs, README, license, video. |
| 21 | Portal / Explorer submission assets | Copy, screenshots, submission form fill. |

Sequencing rationale: contract shape (2–4) before economics (10); evidence (5–6) before adjudication (7–8); adjudication before challenge (9); everything on-chain before frontend (16); manual user deployment (14) before any live verification (15).

**Claude will NOT auto-deploy the production Intelligent Contract at any stage.** The user signs the deployment tx themselves.

---

## 41. Open Decisions Requiring Approval

The following are architecture calls Stage 1 has recommended a position on, but which the user should explicitly confirm before Stage 2 begins:

1. **Envelope bootstrapping model = C (importer proposes; GenLayer adjudicates).** Alternative: A (importer declares; GenLayer verifies).
2. **Fork-of-disputed-parent rule = FINALIZED_FAITHFUL only.** Alternative: allow forking off any status with cascade rules.
3. **Bond economics = partial slash (50% on NOT_FAITHFUL, 100% refund on UNCLEAR).** Alternatives: full slash / full refund binary.
4. **Verdict enum includes `UNCLEAR_VERDICT` as first-class.** Alternative: collapse UNCLEAR into a challenge signal.
5. **Challenges are serial, max 3 per fork.** Alternative: parallel challenges with independent bonds.
6. **`TREASURY_ADDR` is fixed at deployment.** Alternative: DAO-governed treasury address (would require a full governance step of its own).
7. **Adoption tracking excluded from V1.** Alternative: include a minimal `EXTERNALLY_ADOPTED` status with an authoritative-evidence adjudication case.
8. **Primary Portal tag = Governance.** If the Portal has a better-suited tag, choose it.
9. **`MAX_EVIDENCE_SLICE = 16 KiB`.** Confirm the number is compatible with the model context Stage 7 will target.
10. **`FORK_CREATION_BOND = 0.1 GEN` initial.** Adjust at deployment time based on GEN price.

---

## 42. Confirmations

- ✅ Nothing has been deployed or broadcast.
- ✅ The production Intelligent Contract has not been implemented.
- ✅ The frontend has not been built.
- ✅ Stage 2 has not begun.

Stop after Stage 1 and wait for explicit approval.
