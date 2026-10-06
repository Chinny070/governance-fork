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

- 412 Python tests pass (11 new in `tests/test_stage_11.py`); 14/14 static checks.
- Frontend: typecheck, lint, 60 unit tests (4 new for Snapshot parsing/mapping).
- Live (StudioNet): contract deploys and loads; new views respond. NOT live-
  proven: a full adoption round (needs a FAITHFUL root plus faithful forks, which
  synthetic evidence cannot reach — covered by deterministic tests with harness
  status flips instead), and the Snapshot hub fetch (unreachable from the dev
  sandbox; parsing/mapping unit-tested only).
