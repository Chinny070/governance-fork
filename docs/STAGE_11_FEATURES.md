# Stage 11 — Adoption, reputation, escalated appeals, verification UX

Additive on top of the Stage 10 contract. No existing method changed
signature; 6 methods added (3 write, 3 view) -> 20 write + 20 view + 2 admin.

## Contract

**Adoption signalling.** A FAITHFUL verdict says a fork stayed true to the
intent; it does not say anyone wants it. `open_adoption(root_id)` (root's
proposer, root final-FAITHFUL) stamps the on-chain transaction time and opens
a 7-day window (`ADOPTION_WINDOW_SECONDS`, timed by `gl.message_raw["datetime"]`
like the finality window). `signal_adoption(fork_id)`: any address signals one
finalized-FAITHFUL fork per root; re-signalling moves the signal.
`close_adoption(root_id)` (permissionless, after the window) records the
most-signalled fork (ties -> lowest fork id; no signals -> closed, no winner).
Views: `get_adoption`, `get_fork_signal_count`.

*Limit, stated plainly:* one address = one signal, not stake-weighted, so it is
Sybil-able. It is a coordination signal, not a binding vote.

**Creator reputation.** `finalize` and `close_adoption` increment per-creator
counters (faithful / not-faithful / adopted). View: `get_reputation(addr_hex)`.

**Escalated final appeal.** The last challenge a target may receive
(`MAX_CHALLENGES_PER_TARGET`) is judged under `_ADJ_PRINCIPLE_STRICT`: on top of
identical findings, validators must also agree on the exact evidence-id set per
dimension. Harder to reach consensus on, so a last-resort appeal can only
overturn a verdict on tightly-agreed grounds. (The contract cannot choose the
validator set or model mix; strictness of the equivalence principle is the
lever it controls.)

## Frontend

- **Verify hash** on each frozen evidence item: SHA-256 recomputed in the
  browser, compared to the on-chain fingerprint. Proves the text was not
  altered after sealing. (The full adjudication prompt is not stored on-chain,
  only its fingerprint, so a complete replay is not possible yet.)
- **Fork vs parent** table: parameter-level diff (added/removed/changed) next to
  the adjudicator's reasoning for the three fork-fidelity dimensions.
- **Adoption** section on finalized-FAITHFUL roots, plus creator reputation chip.
- **Import from Snapshot** in the Build flow (parses snapshot.org / snapshot.box
  links). Fills DAO and root fields only; the intent envelope is left for the
  proposer to write.

## Verification status

> Superseded: the current production contract is the Stage 12 deployment in
> [`DEPLOYMENT.md`](DEPLOYMENT.md). The text below describes the earlier
> Stage 11 deployment and its proofs, which remain valid for that contract.

Stage 11 production: `0x21654715Ad6960dB7d9b88cB8f7F7fb045C16d96` (commit `ff0f222`,
SHA-256 `266d46d2...48e7`, real 72h / 7d windows). Its demo root
(EIP-1559, with the proposal text in `docs/demo/eip-1559-proposal.md` as its
canonical source) was adjudicated FAITHFUL and its real 72-hour finality window
opened 2026-10-13 06:35:32 UTC (finalize unlocks 2026-10-16 06:35:32 UTC).

**Full live circle on a StudioNet copy of the identical source** (only the
timers shortened: 45s finality, 600s adoption). 24 checks passed:

- root adjudicated FAITHFUL; finalize before the window rejected
  ("challenge window not yet elapsed (42s of 45s required)"); finalized after it
- two forks adjudicated FAITHFUL and finalized (again rejected when early)
- reputation reads back correctly for a checksummed (mixed-case) address
- parent index: children of the root exclude a grandchild; a fork's only child is
  that child, and the fork no longer lists itself
- adoption: close before opening rejected; only the proposer can open; a
  non-finalized fork cannot be signalled; the same fork twice rejected; four
  signals with one voter moving theirs tallied correctly (1 / 3); close before the
  window rejected; a signal after the window rejected; the most-signalled fork won;
  a second close rejected
- winner reputation shows 1 adopted + 1 faithful; unknown address reads zero

Notes from the run: one "early finalize" on a fork was not rejected only because
the chain was slow enough that the 45s window had really elapsed (a test-timing
artifact, not a defect). The adjudicator answered UNCLEAR on
`DIMENSION_CLASSIFICATION` for earlier demo drafts because no source stated which
dimensions were mutable; the demo now carries its own proposal text that does.

Other: 416 Python tests, 14/14 static checks; frontend typecheck, lint, 63 unit
tests (Snapshot parsing/mapping, error messages). Snapshot import verified against
the live hub (off-chain) and `api.snapshot.box` (on-chain) with real links.
NOT run live: the Snapshot import flow end to end through to an on-chain root.

## Fixed: parent index collision

`forks_by_parent` used to be keyed by the bare parent id, so root #N and fork #N
shared one slot (fork #1 listed itself as its own child; the child cap was shared
too). It is now keyed by kind + id, and `list_forks_of_parent` takes a
`parent_kind` argument (4 args instead of 3). Regression test:
`ParentIndexTests` in `tests/test_stage_11.py`; the UI also keeps a defensive
filter in `webapp/src/lib/tree.ts`.

## Fixed: adjudication parser rejected runs that omitted evidence for INTERNAL_CONSISTENCY

Found live on the Stage 11 contract: fork adjudications were repeatedly rolled
back with "decisive finding cites no evidence". `INTERNAL_CONSISTENCY` judges
whether the fork agrees with itself, so the model often cites no evidence for it,
and the strict parser rejected the whole run. Source now exempts only that
dimension from the citation rule (all others still must cite) and tells the model
so. Tests: `ParserCitationRuleTests`. Deployed in the production contract above.
