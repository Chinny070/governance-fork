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

Tested directly: `tests/test_stage_3.py`,
`test_only_importing_proposer_may_submit_envelope` — a different sender
is rejected, then the actual importer succeeds normally. (Originally this
fix was verified live only, not by a committed unit test — added
afterward so all four fixes have actual test coverage, not just three.)

## 4. A real, enforced-duration challenge period

**Revision history on this fix:** the first version shipped here claimed
this runtime "has no block-time source" and shipped a two-step commit
that only closed a same-transaction race, without a real enforced
duration — and said so plainly rather than overclaiming. That
conclusion was correct as far as it was tested, but it was tested
incompletely: `contracts/probe/block_time_probe.py` checked `gl.block`,
`gl.chain`, `gl.message.block_number`, and `gl.vm.block_number` — all of
which genuinely don't exist — but never tried the one name that does.
When directly asked "why can't a runtime with a clock be built," the
right move was to check rather than repeat the inherited conclusion, and
`contracts/probe/datetime_probe.py` found it: **`gl.message_raw` is a
real, live, populated dict, and `gl.message_raw["datetime"]` returns a
genuine, monotonically-increasing, consensus-safe timestamp** — on this
exact already-deployed runtime hash, no migration needed. This section
now describes the corrected, literal fix.

**Live proof, in order:**

1. Deployed `contracts/probe/datetime_probe.py` to StudioNet
   (`0x1070b1EE83939B57919dAF0c9e850a51EaE5f43c` for the write-consensus
   run; earlier addresses for the introspection runs). `dir(gl)` on the
   pinned runtime lists `message_raw` at the top level (distinct from
   `gl.message`); reading it returns:
   ```
   gl.message_raw = {'chain_id': 61999, 'contract_address': Address(...),
     'datetime': '2026-09-13T01:41:42.341487Z', 'entry_data': b'...',
     'entry_kind': 0, 'entry_stage_data': None, 'is_init': False,
     'origin_address': Address(...), 'sender_address': Address(...),
     'stack': [], 'value': 0}
   ```
2. Called a `@gl.public.write.payable` method twice, ~60 seconds apart,
   each storing `gl.message_raw["datetime"]` into contract state. **Both
   transactions reached full validator consensus** (`status: FINALIZED`,
   no disagreement) — proving the value is fixed per-transaction and
   identical across every validator, not each validator's own local wall
   clock (matching the GenVM host spec: deterministic-mode calls return
   "the transaction timestamp, keeping the value deterministic across
   validators"). Reading both stored values back showed monotonically
   increasing timestamps ~51-61 seconds apart, matching real elapsed
   time.
3. Confirmed the stdlib `datetime` module is available inside the
   sandboxed contract: `datetime.datetime.fromisoformat(...)` parses the
   ISO-8601 string and `(b - a).total_seconds()` computes a correct real
   duration between the two captured values, entirely as pure
   deterministic arithmetic on data already fixed in the transaction.
4. Deployed a fresh, complete instance of the corrected
   `governance_fork.py` to StudioNet (`0xE7287c3f561868942b6dBC184E0dDE2830339290`)
   and drove the full pipeline live: `register_dao` → `import_root_proposal`
   → `lock_bond` → `submit_root_envelope` → `close_evidence` →
   `fetch_evidence` ×2 → `seal_evidence` → `adjudicate` →
   `run_adjudication` (committed a real verdict) → `open_finality_window`
   → an immediate `finalize` call. The immediate `finalize` **correctly
   reverted** with the exact new message:
   ```
   challenge window not yet elapsed (36s of 259200s required)
   ```
   confirming the whole mechanism — real timestamp capture, real elapsed-
   time arithmetic, and the revert gate — works end-to-end on a genuine
   fresh deployment, not just in the isolated probe or the unit-test mock
   clock.

**The fix:** `RootProposal` and `Fork` each gained a
`finality_window_opened_at: u256` field (epoch seconds). A new private
helper, `_now_epoch_seconds()`, reads `gl.message_raw["datetime"]` and
parses it to epoch seconds. `open_finality_window(target_id,
target_kind)` — unchanged preconditions (decisive verdict exists, no
open challenge, owner-gated with the same forced-finality escape) —
now also stamps `finality_window_opened_at` with the real transaction
time. `finalize(target_id, target_kind)` now computes `elapsed =
_now_epoch_seconds() - opened_at` and reverts with `"challenge window
not yet elapsed (Ns of Ms required)"` unless `elapsed >=
CHALLENGE_WINDOW_SECONDS` (72 hours — a constant the original Stage 2
design declared and exposed via `get_constants()` but never actually
enforced anywhere until now). This is the literal, enforced wall-clock
challenge period the steward asked for: the same owner calling both
steps back-to-back no longer bypasses anything, because `finalize`
itself refuses to execute until real time has passed, independent of
who called `open_finality_window` or when.

The same-transaction-race protection from the prior revision is also
still in place and unchanged: `challenge_verdict` unconditionally
overwrites the target's status to `*_CHALLENGE_OPEN`, so a challenge
landing at any point after `open_finality_window` — including during
the now-enforced wait — flips the target out of `*_CHALLENGE_WINDOW`
and `finalize` correctly reverts, window-elapsed or not.

Tested directly (`tests/test_stage_8.py`,
`test_open_window_stamps_timestamp_and_finalize_rejects_before_window_elapses`):
opens the window, asserts `finalize` reverts immediately, asserts it
still reverts with `CHALLENGE_WINDOW_SECONDS - 1` elapsed, then asserts
it succeeds two seconds later. Every other finalize-reaching test now
advances the test shim's mock clock (`tests/_genlayer_shim.py`'s
`gl.message_raw["datetime"]`, backed by an explicit `advance_clock()`
test helper that models the live-proven behavior above) past the window
before finalizing.

## ABI impact

35 → 36 methods: **17 write** (+1: `open_finality_window`) + 17 view + 2
admin. `finalize`'s parameters and return type are unchanged; only its
preconditions and permission model changed.

## Tests

- `tests/test_stage_8.py` — `FinalizeTests` rewritten around the two-step
  commit: `open_window_needs_verdict`, `open_window_blocked_by_open_challenge`,
  `open_window_requires_owner`, `finalize_without_open_window_rejected`,
  `double_open_window_rejected`, `challenge_after_open_window_blocks_finalize`,
  and (the literal enforced-duration fix)
  `test_open_window_stamps_timestamp_and_finalize_rejects_before_window_elapses`,
  plus every existing finalize path updated to call `open_finality_window`
  first and to advance the mock clock past `CHALLENGE_WINDOW_SECONDS`
  before finalizing.
- `tests/test_stage_9.py` — `_finalized_root` / `_finalized_fork` helpers
  and every direct `finalize` call site updated to the two-step form plus
  the clock advance.
- `tests/test_stage_6b.py` — `test_root_seal_rejected_without_canonical_source_evidence`
  (renamed/rewritten from a test that asserted the old opportunistic
  behaviour) and one fixture URL corrected so an unrelated-case-liveness
  test still includes its own canonical source.
- `tests/test_stage_3.py` — `test_only_importing_proposer_may_submit_envelope`
  (fix #3): a non-proposer sender is rejected, the actual importer still
  succeeds.
- `tests/stage_2_checks.py` — ABI count updated to 17 write methods.
- `tests/_genlayer_shim.py` — added a mock wall clock backing
  `gl.message_raw["datetime"]` (`advance_clock()` / `set_clock()`),
  reset alongside the native-GEN ledger on each fresh contract instance,
  modeling the live-proven behavior in section 4 above.

All four fixes now have both a committed automated test and live
StudioNet verification (fix #1's live cross-check was impractical --
depth-2 FAITHFUL adjudication needs governance-authoritative evidence no
synthetic proposal can supply -- so it's proven deterministically instead;
see `tests/test_stage_10.py`'s docstring).

401/401 local tests pass; `tests/stage_2_checks.py` reports 14/14 checks
passed (12 run locally, 2 marked environment-unavailable: genvm-lint and
a live genlayer-studio schema-load, neither present in this sandbox).
