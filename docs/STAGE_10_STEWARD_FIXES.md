# Stage 10 — Steward-Requested Fixes

A GenLayer Project Explorer steward reviewed the production contract
(`0xbA06003F2C254232E4D440B89425abc7Afd4c11A`, commit `2d7ce42`) and returned
it with:

> Please update the contract so fork adjudication includes the canonical
> root intent envelope and complete parent fork body, and require the
> imported proposal source in the sealed adjudication evidence. Bind
> root-envelope submission and case ownership to the same authorized
> account, enforce a challenge period before finalization, and link the
> corrected source with tests covering these flows.

All four points were verified against the actual source (not assumed) before
being fixed, and one was independently reproduced live: our own test run
sealed and adjudicated a root envelope whose `web_content_fingerprint` was
never set, because nothing required the canonical `proposal_url` to be
included as evidence.

Stage 7, 8 and 9 behaviour is otherwise unchanged. No new ABI-breaking
changes to existing methods — one method added (`open_finality_window`),
one method's semantics changed (`finalize`, see below).

## 1. Fork adjudication now sees the full lineage, not a parameter list

**Before:** `_fork_subject_block` received only the immediate parent's flat
`structured_parameters` key/value list. A fork three levels deep was judged
against a thin parameter snapshot, never the root's actual `IntentEnvelope`
(objective, scope, essential constraints, mutable/immutable dimensions) and
never the immediate parent's complete body when that parent was itself a
fork.

**After:** `_fork_parent_context(fork)` resolves `(root, parent_label,
parent_fork_or_None)` from `fork.root_id` / `fork.parent_kind` /
`fork.parent_id`. `_fork_subject_block` now renders:

- **ROOT INTENT** — the complete canonical envelope (`_intent_lines`,
  factored out of `_root_subject_block` so both paths render it
  identically), always present regardless of depth.
- **IMMEDIATE PARENT** — when the parent is a fork, its full body (title,
  summary, reasoning, structured parameters); when the parent is the root,
  a pointer back to ROOT INTENT above (they're the same thing).
- The fork's own body and declared delta, unchanged.

`case_fingerprint` is untouched by this — it was already bound to
`fork_body_fingerprint` / `root_import_fingerprint` / `parent_fingerprint`
(all immutable at fork-creation time), never to prompt text, so adding
context to the prompt only changes `prompt_fingerprint` (an audit hash of
what was actually sent), not the case's identity binding.

## 2. The canonical proposal source must be sealed evidence

**Before:** `RootProposal.web_content_fingerprint` was populated
opportunistically at `seal_evidence` time — only if the submitter happened
to include the exact `proposal_url` among their evidence and it was
fetched. Nothing required it. A root envelope could be fully adjudicated
without its own authoritative source ever being rendered on-chain.

**After:** `seal_evidence`'s `ROOT_ENVELOPE` branch now requires at least
one evidence item whose normalized URL matches the root's normalized
`proposal_url`, or it reverts with `"the proposal's own source URL must be
included as evidence"`. Since every root-envelope evidence item is already
"required" (must reach `RETRIEVAL_FETCHED` before seal), this match is
guaranteed already fetched by the time the check runs — the old best-effort
derivation loop collapses into an unconditional assignment.

## 3. `submit_root_envelope` is bound to the importing proposer

**Before:** `import_root_proposal` fixes `RootProposal.proposer` at import
time, and `_case_owner` uses it to gate `close_evidence` / `adjudicate` /
`finalize` — but `submit_root_envelope` itself checked no such binding.
Anyone could submit the intent envelope for someone else's imported
proposal, framing it however they chose, while the *original* importer
retained case ownership for everything downstream.

**After:** `submit_root_envelope` now requires
`gl.message.sender_address == root.proposer`, or reverts with `"only the
importing proposer may submit this root's envelope"`.

## 4. A real two-step finality commit

**The constraint:** this pinned GenVM runtime has no block-time source —
every timestamp is `u256(0)` (established live in Stage 6a/9 probes). That
proves no wall-clock *time* is available, but not, by itself, that no
block *number* or sequence counter is available either -- those are a
different question. Rather than extend the earlier conclusion further
than it was actually tested, `contracts/probe/block_time_probe.py` asked
it directly, live: does `gl.block`, `gl.chain`, or any field on
`gl.message` / `gl.vm` expose a block number, height, or sequence value?

Deployed to StudioNet (`0x7594d3D29DabeB4ADd174809B939d4b85e70fB6b`),
`probe()` returned:

```
gl.message.sender_address = Address("0x3A31...")
gl.block.number    ERROR: AttributeError: module 'genlayer.gl' has no attribute 'block'
gl.block.timestamp ERROR: AttributeError: module 'genlayer.gl' has no attribute 'block'
gl.chain.block_number  ERROR: AttributeError: module 'genlayer.gl' has no attribute 'chain'
gl.message.block_number ERROR: AttributeError: 'MessageType' object has no attribute 'block_number'
gl.vm.block_number ERROR: AttributeError: module 'genlayer.gl.vm' has no attribute 'block_number'
```

`gl.block` and `gl.chain` don't exist as namespaces at all (not "exist but
empty" -- an `AttributeError` at the module level). `gl.message` and
`gl.vm` exist but expose no block/height/sequence field. **There is no
monotonic counter of any kind available to an Intelligent Contract on
this runtime.** A literal enforced-duration or enforced-block-count
challenge period is not buildable here, confirmed rather than assumed.

Practically: the original single-transaction `finalize()` let an owner
call it in the very next transaction after `run_adjudication` succeeded,
so a would-be challenger had to win a race against the owner's own
finalize call with no guaranteed window to even see the verdict land
first.

**Honesty about what this fix actually delivers:** the two-step commit
below closes that same-transaction race, but it does **not** enforce a
minimum duration or a minimum number of blocks/transactions between the
two steps -- nothing stops the same owner from calling both back-to-back.
It only helps if a third party's challenge transaction actually lands in
the gap. That's a real improvement, not the literal "enforced period" the
request asked for, and it's worth saying so plainly rather than
implying full compliance.

**The fix:** `finalize()` is split into two transactions, reusing a status
value (`FORK_CHALLENGE_WINDOW`) the original Stage 2 design declared but
never wired up, plus a new mirror for root envelopes
(`ENVELOPE_CHALLENGE_WINDOW`):

1. **`open_finality_window(target_id, target_kind)`** — carries every
   precondition the old `finalize()` had (decisive verdict exists, no open
   challenge, owner-gated with the same forced-finality escape once the
   challenge budget is spent). On success it moves the target to
   `*_CHALLENGE_WINDOW` — nothing else changes yet.
2. **`finalize(target_id, target_kind)`** — now requires the target to
   already be in `*_CHALLENGE_WINDOW` (set by a *prior, separate*
   transaction), or reverts `"call open_finality_window first"`. It is now
   **permissionless**: the owner's intent was already authenticated when
   they opened the window, so anyone may execute the already-decided
   outcome (the same pattern `seal_evidence` already uses).

The actual protection: `challenge_verdict` unconditionally overwrites the
target's status to `*_CHALLENGE_OPEN` regardless of what it was before. If
a challenge lands in the gap between `open_finality_window` and `finalize`,
the target is no longer `*_CHALLENGE_WINDOW` when `finalize` runs, so it
correctly reverts and the challenge must be resolved first. This doesn't
manufacture wall-clock time — it closes the single-transaction front-run
gap the steward flagged, using the same two-step commit pattern this
contract already relies on elsewhere (`adjudicate` / `run_adjudication`,
`close_evidence` / `fetch_evidence` / `seal_evidence`).

Tested directly: `test_challenge_after_open_window_blocks_finalize` opens
the window, submits a challenge, and asserts `finalize` now reverts.

## ABI impact

35 → 36 methods: **17 write** (+1: `open_finality_window`) + 17 view + 2
admin. `finalize`'s parameters and return type are unchanged; only its
preconditions and permission model changed.

## Tests

- `tests/test_stage_8.py` — `FinalizeTests` rewritten around the two-step
  commit: `open_window_needs_verdict`, `open_window_blocked_by_open_challenge`,
  `open_window_requires_owner`, `finalize_without_open_window_rejected`,
  `double_open_window_rejected`, `challenge_after_open_window_blocks_finalize`
  (the actual fix), plus every existing finalize path updated to call
  `open_finality_window` first.
- `tests/test_stage_9.py` — `_finalized_root` / `_finalized_fork` helpers
  and every direct `finalize` call site updated to the two-step form.
- `tests/test_stage_6b.py` — `test_root_seal_rejected_without_canonical_source_evidence`
  (renamed/rewritten from a test that asserted the old opportunistic
  behaviour) and one fixture URL corrected so an unrelated-case-liveness
  test still includes its own canonical source.
- `tests/stage_2_checks.py` — ABI count updated to 17 write methods.

397/397 local tests pass; all 12 static structural checks pass.
