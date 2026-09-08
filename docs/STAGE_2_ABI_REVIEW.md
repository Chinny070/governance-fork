# Stage 2 — ABI Review

**Baseline:** Stage 1 reduced ABI = 32 methods (12 write + 18 view + 2 admin).

**Stage 2 outcome:** 29 methods (11 write + 16 view + 2 admin). Reduction of 3.

Each method reviewed against the four purposes: full Proposal Tree UX, evidence traceability, challenge traceability, integration-friendly reads, safe transaction lifecycle. Nothing removed merely to chase a number.

## Legend

- **E** — Essential: retained.
- **M** — Mergeable: folded into another retained method.
- **I** — Internal: removed from public ABI (would be a private helper only).
- **P** — Premature: not needed until a later stage.

## Write methods

| # | Method | Stage impl | Class | Final | Rationale |
|---|---|---|---|---|---|
| W1 | `register_dao(name, url) -> u256` | 3 | E | KEEP | Ecosystem primitive; must exist to register any DAO. |
| W2 | `import_root_proposal(dao_id, external_proposal_id, title, proposal_url, structured_parameters) -> u256` | 3 | E | KEEP | Freezes root proposal body via `gl.nondet.web.render`; unavoidable entry point. |
| W3 | `submit_root_envelope(root_id, envelope, evidence_urls, evidence_classes, relevance_claims, authority_claims, temporal_markers) -> u256` | 3 | E | KEEP (**payable**) | Opens envelope adjudication case; captures `ENVELOPE_BOND`. |
| W4 | `create_fork(parent_id, parent_fingerprint, delta, body) -> u256` | 4 | E | KEEP (**payable**) | Opens fork lifecycle; captures `FORK_CREATION_BOND`; runs deterministic delta-application pre-check. |
| W5 | `submit_fork_evidence(fork_id, evidence_urls, evidence_classes, relevance_claims, authority_claims, temporal_markers) -> u256` | 5 | E | KEEP | Opens fork evidence case; distinct from `create_fork` because it is a separate submission phase and carries no bond. |
| W6 | `freeze_evidence(evidence_id) -> None` | 6 | E | KEEP | Per-evidence-item deterministic freeze; called once per item; idempotent when frozen. |
| W7 | `freeze_case(case_id) -> None` | 6 | E | KEEP | Freezes the entire case fingerprint; required to be a separate tx because adjudication may `Undetermined`. |
| W8 | `adjudicate(case_id) -> None` | 7 | E | KEEP | **Unified.** Dispatches by `case.case_type ∈ {ROOT_ENVELOPE, FORK, CHALLENGE}` to distinct prompt templates and output schemas. Now also handles the retry path — an `UNDETERMINED` case after `RETRY_COOLDOWN` calls `adjudicate` again; the method checks state and increments `retry_count`. |
| W9 | `challenge_verdict(target_id, target_kind, ground_code, argument) -> u256` | 9 | E | KEEP (**payable**) | Unified over fork + envelope targets; captures `CHALLENGE_BOND`. |
| W10 | `finalize(target_id, target_kind) -> None` | 11 | E | KEEP | Unified over fork + envelope targets; ends the challenge window and locks the verdict. |
| W11 | `settle_bond(bond_id) -> None` | 10 | E | KEEP | Bond payout; idempotent via `bond.settled`. |
| — | ~~`retry_adjudication(case_id)`~~ | — | M | REMOVE | **Folded into `adjudicate`.** Retry is state-driven (case must be in `UNDETERMINED` and past `RETRY_COOLDOWN`); no separate entry point needed. |

Write count: 11 (was 12).

## Admin methods

| # | Method | Stage impl | Class | Final | Rationale |
|---|---|---|---|---|---|
| A1 | `pause() -> None` | 2 (minimal) | E | KEEP | Safety-only, blocks new writes only (withdrawal-safe pause is a Stage 11 concern). |
| A2 | `unpause() -> None` | 2 (minimal) | E | KEEP | Recovery path. |

Admin count: 2 (unchanged). Implemented at Stage 2 as minimal skeleton: caller must equal `treasury_addr`. No further logic.

## View methods

| # | Method | Stage impl | Class | Final | Rationale |
|---|---|---|---|---|---|
| V1 | `get_dao(dao_id) -> Dao` | 3 | E | KEEP | Basic entity read. |
| V2 | `list_daos(cursor, limit) -> PageIds` | 3 | E | KEEP | Discovery for a wallet-free explorer. |
| V3 | `get_root_proposal(root_id) -> RootProposal` | 3 | E | KEEP | Includes `envelope` and `envelope_status` inline. |
| V4 | `list_root_proposals_by_dao(dao_id, cursor, limit) -> PageIds` | 3 | E | KEEP | Tree walk entry. |
| V5 | `get_fork(fork_id) -> Fork` | 4 | E | KEEP | Includes `body`, `delta`, and `current_verdict_id` inline. |
| V6 | `list_forks_of_root(root_id, cursor, limit) -> PageIds` | 4 | E | KEEP | Full-tree paginated fetch by root. |
| V7 | `list_forks_of_parent(parent_id, cursor, limit) -> PageIds` | 4 | E | KEEP | Children of a specific parent (works for root parent and fork parent). |
| V8 | `get_verdict_history(target_id, target_kind, cursor, limit) -> PageIds` | 7 | E | KEEP | Unified over fork verdicts and envelope verdicts; returns verdict IDs. Latest is index 0. |
| V9 | `get_verdict(verdict_id) -> VerdictRecord` | 7 | E | KEEP | Per-record fetch after `get_verdict_history` returns IDs. Natural pair; not a merge target. |
| V10 | `get_evidence(evidence_id) -> Evidence` | 5 | E | KEEP | Per-item read for the evidence trace UI. |
| V11 | `list_evidence_of_case(case_id, cursor, limit) -> PageIds` | 5 | E | KEEP | Ordered evidence set for a case. |
| V12 | `get_case(case_id) -> Case` | 6 | E | KEEP | Integrators need frozen fingerprints + `case_type` + state. |
| V13 | `get_challenge(challenge_id) -> Challenge` | 9 | E | KEEP | Per-record read. |
| V14 | `list_challenges(target_id, target_kind, cursor, limit) -> PageIds` | 9 | E | KEEP | Unified over fork + envelope targets. |
| V15 | `get_bond(bond_id) -> Bond` | 10 | E | KEEP | Bond identity + disposition unified. |
| V16 | `get_constants() -> ConstantsView` | 2 | E | KEEP | Every cap + window + bond amount + `paused` + `treasury_addr` in one call. Merged the previous `get_pause_state`. |
| — | ~~`get_finality(target_id, target_kind)`~~ | — | M | REMOVE | **Folded into `get_fork` and `get_root_proposal`.** Fork finality lives on `fork.status`; envelope finality lives on `root.envelope_status`. Standalone endpoint added a round-trip for no new information. |
| — | ~~`list_bonds_of_target(target_id, target_kind, cursor, limit)`~~ | — | M | REMOVE | **Folded into `get_fork` and `get_challenge`.** Each fork has exactly one creator bond (`fork.creator_bond_id`); each challenge has exactly one challenger bond (`challenge.bond_id`). A dedicated list added no value. |
| — | ~~`get_pause_state()`~~ | — | M | REMOVE | **Folded into `get_constants`.** `paused` and `treasury_addr` are cheap to include alongside the caps. One call, one round-trip. |

View count: 16 (was 18).

## Total

| Bucket | Stage 1 | Stage 2 | Δ |
|---|---|---|---|
| Write | 12 | 11 | −1 |
| Admin | 2 | 2 | 0 |
| View | 18 | 16 | −2 |
| **Total** | **32** | **29** | **−3** |

## Full-tree walk still supported

Reconstructing the full tree from public reads only:

1. `list_daos` → DAO IDs.
2. `get_dao(dao_id)` per DAO.
3. `list_root_proposals_by_dao(dao_id, ...)` → root IDs.
4. `get_root_proposal(root_id)` → root + envelope + envelope_status.
5. `list_forks_of_root(root_id, ...)` or recurse `list_forks_of_parent(parent_id, ...)`.
6. `get_fork(fork_id)` → body + delta + current_verdict_id + status + creator_bond_id.
7. `get_verdict(verdict_id)` → per-dimension findings.
8. `list_evidence_of_case(case_id, ...)` + `get_evidence(id)` → evidence trace.
9. `list_challenges(target_id, target_kind, ...)` + `get_challenge(id)` → challenge trace.
10. `get_bond(bond_id)` → bond disposition.

No custom indexer required for the reference frontend.
