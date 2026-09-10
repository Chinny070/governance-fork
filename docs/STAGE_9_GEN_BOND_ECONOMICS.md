# Stage 9 — Native GEN Bond Economics

Adds the complete bond lifecycle on top of the Stage 8 challenge/finality
state machine. Stage 7 and Stage 8 behaviour is unchanged.

## 1. Live-proven primitives only

Everything here uses exactly what `contracts/probe/value_transfer_probe.py`
proved live on the pinned runtime (`py-genlayer:1jb45aa8...`):

| need | primitive | proof |
|---|---|---|
| receive a bond | `@gl.public.write.payable` + `gl.message.value` (u256) | probe `deposit()` saw the exact amount |
| accounting | `self.balance` | matched `eth_getBalance` (3.0 GEN) |
| pay out | `gl.get_contract_at(<Address>).emit_transfer(value=<u256>)` | deducted exactly the amount (3.0 → 2.9 GEN); `gl.Account`, bare `Account`, `gl.contract.get_at` do **not** exist on this runtime |

**The contract IS the treasury.** Slashed GEN is retained in
`self.balance` and tracked by `self.treasury_pool`; the admin
(`treasury_addr`) drains it with `withdraw_treasury`. This avoids an
external-EOA treasury the contract could never spend from, and it means
the challenger-flip reward is always funded by a real prior slash.

> **StudioNet limitation (network, not contract):** on StudioNet an
> IC→EOA `emit_transfer` child tx finalizes as `Contract <eoa> not found`
> and does not credit the EOA (GenLayer docs: "no EVM layer or ghost
> contracts in Studio"). The bond stage is therefore validated on
> **Testnet Bradbury**, which has the real chain layer.

## 1a. Capture model — corrected after a live StudioNet finding

Live test: a `@gl.public.write.payable` call that **reverts** on the
pinned runtime **keeps the attached native value in the contract** while
rolling back all state — the value is trapped with no `Bond` record
(observed: sender −0.1 GEN, contract +0.1 GEN, `create_fork` reverted,
no fork, no bond). So "check `gl.message.value` up front, revert on
mismatch" traps a correctly-sized bond the moment any *later* validation
fails.

Capture is therefore split into lock → consume:

1. **`lock_bond(purpose) -> u256`** — the **only** payable method. Records
   a `Bond` for whatever value was sent and returns its id. It cannot
   revert once value is attached: the only rejections are an unknown
   `purpose` or a **zero** value, neither of which traps GEN. The bond
   starts **UNASSIGNED** (`target_id == 0`), owned by the sender.
2. **`create_fork` / `submit_root_envelope` / `challenge_verdict`** — now
   **non-payable**, each takes a leading `bond_id`. They `_consume_bond`
   (owner match, purpose match, unassigned, exact amount, not settled) and
   then `_assign_bond` (set `target_id`, index into
   `bonds_by_target["<KIND>/<id>"]`). Being non-payable, any revert in
   these is safe — no value is attached. A wrong-amount / wrong-purpose /
   unused / rejected bond stays UNASSIGNED and is **always 100 %
   refundable** via `settle_bond`.

## 2. Bonds

| bond | flow | amount | owner |
|---|---|---|---|
| `ENVELOPE` | `lock_bond("ENVELOPE")` → `submit_root_envelope(bond_id, …)` | `ENVELOPE_BOND` (0.1 GEN) | root proposer |
| `FORK_CREATION` | `lock_bond("FORK_CREATION")` → `create_fork(bond_id, …)` | `FORK_CREATION_BOND` (0.1 GEN) | fork creator |
| `CHALLENGE` | `lock_bond("CHALLENGE")` → `challenge_verdict(bond_id, …)` | `CHALLENGE_BOND` (0.1 GEN) | challenger |

`Fork.creator_bond_id` and `Challenge.bond_id` point back to the record.
An UNASSIGNED bond (`target_id == 0`) settles as a plain 100 % refund with
no finalize check.

### 2a. Retry-exhaustion terminal (live-fix)

If adjudication exhausts its retry budget without ever producing a verdict
the target becomes final (`ENVELOPE_UNCLEAR` / `FORK_FINALIZED_UNCLEAR`)
with `current_verdict_id == 0`. `_target_final_verdict_str` returns
`UNCLEAR_VERDICT` in that case, so the creator/proposer bond settles as a
plain 100 % refund and is never trapped. (A CHALLENGE bond cannot exist
here — `challenge_verdict` needs a decisive verdict to challenge.)

## 3. Disposition (deterministic, from the finalized verdict)

`settle_bond(bond_id)` — **not paused-gated** (pause blocks new exposure,
never traps finalized funds). Preconditions: bond exists; not already
settled; the bond's target is **finalized**; for a `CHALLENGE` bond the
challenge is resolved **and** the target's creator/proposer bond is
already settled (ordering guard — see §4).

**Creator / proposer bond**, keyed on the target's final verdict:

| final verdict | refund → owner | slash → treasury_pool | settlement_kind |
|---|---|---|---|
| `FAITHFUL` | 100% | 0 | `SETTLED_FULL_REFUND` |
| `UNCLEAR_VERDICT` | 100% | 0 | `SETTLED_FULL_REFUND` |
| `INVALID` | 100% | 0 | `SETTLED_FULL_REFUND` |
| `NOT_FAITHFUL` | 50% | 50% | `SETTLED_PARTIAL_SLASH` |

**Challenger bond**, keyed on that challenge's resolution:

| resolution | refund → owner | slash → treasury_pool | reward → owner | settlement_kind |
|---|---|---|---|---|
| `RESOLVED_FLIPPED` | 100% | 0 | `min(CHALLENGER_FLIP_REWARD, treasury_pool)` (0.05 GEN) | `SETTLED_CHALLENGER_REWARD` (or `FULL_REFUND` if reward 0) |
| `RESOLVED_UNCHANGED` | 50% | 50% | 0 | `SETTLED_PARTIAL_SLASH` |
| `RESOLVED_INVALID` | 100% | 0 | 0 | `SETTLED_FULL_REFUND` |
| `RESOLVED_UNCLEAR` | 100% | 0 | 0 | `SETTLED_FULL_REFUND` |

`refund + slash == amount` for **every** bond, always. The reward is a
separate bonus drawn from `treasury_pool` and capped at it.

This is a deliberate, deterministic V1 of the `STAGE_1` §16 model:
the creator-bond disposition depends only on the final verdict (not on
per-challenge recomputation), and the challenger reward is a fixed
0.05 GEN rather than "25% of the creator's slashed portion" — simpler,
order-independent, and always funded by a real slash.

## 4. Ordering guard makes the reward deterministic

A `CHALLENGE` bond can be settled only after the target's
creator/proposer bond. That bond's slash (50% of it, 0.05 GEN, when the
final verdict is `NOT_FAITHFUL`) is exactly the reward size, so by the
time a flipped-challenge bond settles the pool holds ≥ the reward. If the
flip went the other way (to `FAITHFUL`) there is no slash and the reward
is 0 — deterministic either way, independent of the order challenge bonds
are settled among themselves.

## 5. `withdraw_treasury(amount)`

Admin-only (`treasury_addr`), not paused-gated. Moves up to
`treasury_pool` of accumulated slash out to `treasury_addr` via
`emit_transfer`; decrements the pool. `amount > treasury_pool` reverts.

## 6. Replay / safety

- `bond.settled` is checked, then set **before** any `emit_transfer`.
  A second `settle_bond` reverts `bond already settled`.
- Payout destinations are frozen at capture (`bond.owner`) or fixed
  (`treasury_addr`). No caller-selected recipient anywhere.
- `settle_bond` before finalize reverts; on an open/unresolved challenge
  reverts.
- No double slash / double reward: a bond settles exactly once and its
  `refund_amount` / `slash_amount` / `reward_amount` are frozen at that
  moment.
- Global invariant, checked in tests at every step:
  `self.balance == Σ(unsettled bond amounts) + treasury_pool`.

## 7. ABI / storage

- `+lock_bond` + `+withdraw_treasury` (write), `+list_bonds_by_target`
  (view); the three formerly-payable methods gain a leading `bond_id` and
  drop `.payable`. ABI 35 (16 write + 17 view + 2 admin).
- `Bond` gains `challenge_id`, `refund_amount`, `slash_amount`,
  `reward_amount`. `Contract` gains `bonds_by_target` and `treasury_pool`.
  `ConstantsView` gains `challenger_flip_reward` and `treasury_pool`.
- `get_bond` / `settle_bond` implemented (were placeholders). No
  `stage-2: not implemented` placeholder remains anywhere in the contract.

## 8. Tests

`tests/test_stage_9.py` (22): capture + exact-amount rejection (wrong /
zero / over), challenge-bond capture + linkage, economic paths A–H
(faithful full refund, not-faithful partial slash, flip-challenge reward,
failed-challenge partial slash, unclear full refund, settlement replay
rejection, settle-before-finalize rejection, pause-does-not-trap), pause
blocks new exposure, ordering-guard rejection, refund+slash==amount
invariant, no-balance-drift full cycle, `withdraw_treasury` (happy path /
admin-only / over-pool).

`tests/_genlayer_shim.py` gains `_MockChain` (payable credit,
`emit_transfer` deduction, double-entry when the sender is funded) and a
`payable`-decorator autopay so pre-Stage-9 test call sites that pass no
value keep working; wrong-bond tests call `shim.set_value(...)`.
