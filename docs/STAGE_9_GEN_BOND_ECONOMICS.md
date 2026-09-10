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

## 2. Bonds

| bond | captured by | amount | owner |
|---|---|---|---|
| `ENVELOPE` | `submit_root_envelope` (payable) | `ENVELOPE_BOND` (0.1 GEN) | root proposer |
| `FORK_CREATION` | `create_fork` (payable) | `FORK_CREATION_BOND` (0.1 GEN) | fork creator |
| `CHALLENGE` | `challenge_verdict` (payable) | `CHALLENGE_BOND` (0.1 GEN) | challenger |

Each payable method checks `gl.message.value == <exact bond>` up front
(a wrong/zero/over amount reverts before any heavy work; a revert returns
the value and writes nothing) and, only after every other validation
passes, writes the `Bond` record via `_capture_bond` and indexes it in
`bonds_by_target["<TARGET_KIND>/<id>"]`. `Fork.creator_bond_id` and
`Challenge.bond_id` point back to the record.

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

- `+withdraw_treasury` (write), `+list_bonds_by_target` (view) → ABI 34
  (15 write + 17 view + 2 admin).
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
