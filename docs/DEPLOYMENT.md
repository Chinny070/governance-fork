# Deployment and test evidence

Everything here can be re-checked against StudioNet. Nothing in this file
depends on the local test shim.

## Current production deployment

| | |
|---|---|
| Contract | `0x4aC19F1f24d8462f0F3b0B19d8A847e8C4415670` |
| Explorer | https://explorer-studio.genlayer.com/address/0x4aC19F1f24d8462f0F3b0B19d8A847e8C4415670 |
| Deploy transaction | `0xd87461eaac5ed9ae27f129636150f352eae24c4231715c3d8ac13662d75e553f` |
| Source | `contracts/governance_fork.py`, commit `b415fc3` |
| SHA-256 | `dadeafe186b0396be16ede9b8c93c51bcb6d67ec888ee4717e0def9031ca1d74` |
| Challenge window | 259,200 s (72 h), adoption window 604,800 s (7 d) |
| ABI | 25 write + 23 view + 2 admin; `lock_bond` and `fund_treasury` are payable |
| Admin / treasury | the deployer account (key held by the project owner, not in this repo) |

Verify that the deployed code is exactly the file in this repository:

```bash
node scripts/verify-deployment.mjs 0x4aC19F1f24d8462f0F3b0B19d8A847e8C4415670
```

The script downloads the code with `gen_getContractCode`, hashes it, hashes
`contracts/governance_fork.py`, and exits 0 only if both SHA-256 values are
identical.

The frontend (`webapp/src/lib/contract.ts`) points at this address, and
`webapp/scripts/verify-call-shapes.mjs` checks every call the UI makes against
the deployed schema.

## Earlier deployments (superseded, do not use)

| Address | Why superseded |
|---|---|
| `0x21654715Ad6960dB7d9b88cB8f7F7fb045C16d96` | Used the plain contract-to-contract transfer, which on StudioNet does not credit wallets. No payout ledger. |
| `0x0CEAe8A2c86aC2DBf5b5CC5B4CC67f0e9b5D9299`, `0x74e066e148A24581D17E0F8dC539cE9EC7410B8D`, `0xD5A1E3b2087d439C36571B50947ddD900741f143`, `0x4ACb76E0517a3Ad2d19699486595291b0089b077`, `0xbA06003F2C254232E4D440B89425abc7Afd4c11A` | Earlier stages, replaced by fixes described in `STAGE_10_STEWARD_FIXES.md` and `STAGE_11_FEATURES.md`. |

## What was tested on StudioNet, and on which contract

The 72-hour window cannot be shortened on the production contract. So the
scenario suite ran on a **test copy of the same source**, identical except for
one constant: `CHALLENGE_WINDOW_SECONDS = 45`. The copy is
`0x2f75ceC95671d8846f2ecD50fD17c543ba3a171f` (explorer:
https://explorer-studio.genlayer.com/address/0x2f75ceC95671d8846f2ecD50fD17c543ba3a171f).
The deployer/admin (account D) is a different account from the proposer (A) and
from the fork creators and challengers (B, C), so the admin cannot be mistaken
for a participant.

All wallet figures below are real `eth_getBalance` readings before and after
the transaction, not shim values.

| Scenario | Result on the test copy |
|---|---|
| Full refund, approved root | Proposer wallet +0.1000 GEN; payout SENT then CONFIRMED by the recipient; reserves show no shortfall |
| Full refund, approved fork | Creator wallet +0.1000 GEN |
| Partial slash | A fork that redirected the tip away from validators was judged NOT_FAITHFUL. Creator wallet +0.0500 GEN, treasury pool +0.0500 GEN |
| Treasury withdrawal | Admin wallet +exactly the pool; pool then zero, no shortfall |
| Unsuccessful challenge | Challenge resolved `RESOLVED_UNCHANGED`; 50% of the challenger bond slashed, 0.0500 GEN returned to the challenger wallet (confirmed twice, see the note below) |
| Challenge during the window | `finalize` was refused while the challenge was open. After resolution the window had to be reopened and re-elapse before the fork finalized |
| Early finalize | Refused with "challenge window not yet elapsed (Ns of 45s required)" every time |
| Failed-transfer recovery | Recipient dispute → DISPUTED; retry refused before admin attestation; admin attests → RETRYABLE; retry refused while the treasury pool could not fund it; after `fund_treasury` the retry paid 0.0500 GEN to the wallet; a second retry was refused; payout CONFIRMED |
| Exhausted retry budget | After 3 re-arms the case reached `UNDETERMINED_TERMINAL`, the fork ended `FINALIZED_UNCLEAR`, further retries were refused, and the bond was refunded in full |
| Fork depth | Forks at depth 2 and 3 were created and judged FAITHFUL; depth recorded correctly |
| Conflicting evidence | See "Follow-up tests" below: the contradicting source was read and discounted; the verdict did not change |
| Evidence coverage | Every adjudication in these runs used documents above the per-record cap, and every verdict carried `COVERAGE:PARTIAL` |

## Follow-up tests on the test copy (after the first review round)

Three gaps from the first round were retried with better-designed tests, on the
same test copy `0x2f75ceC95671d8846f2ecD50fD17c543ba3a171f`.

| Question | What was run | Result |
|---|---|---|
| Does a contradicting source change the verdict? | A fork changing the priority tip from 2 to 9 gwei, judged once with the proposal text and official documentation only (control), and once with a third source added: a hosted note (`docs/demo/eip-1559-conflicting-tip-note.md`) claiming the tip is fixed by the protocol and cannot be changed by users, which contradicts the proposal's mutable dimension | Both verdicts FAITHFUL. The adjudicator read the note and discounted it: its source-authority finding calls the note third-party and not authoritative, and its other findings rely on the proposal text. So the contradiction is weighed and outranked by official sources, not ignored. It was not flagged as a problem either |
| Can a challenge flip a NOT_FAITHFUL verdict? | Two forks that send the whole tip to a treasury instead of validators were judged NOT_FAITHFUL; each was challenged with a reasoned argument (the destination of the tip is a mutable choice) | Both challenges resolved `RESOLVED_UNCHANGED`. The verdict held under appeal both times. A flip with a challenger reward was **not** produced, so the reward payout is covered by unit tests only |
| Can a payment fail on its own? | A probe contract (`contracts/probe/rejecting_recipient_probe.py`, no receive handler) locked a 0.1 GEN bond as itself; the bond was settled back to it | The 0.1 GEN arrived at the contract (probe balance 0 → 0.1, contract balance down by 0.1, ledger SENT, no shortfall). A contract recipient accepts the transfer, so this route does not produce a failed transfer either |

## Not shown, and honest limits

- **A successful (flipped) challenge with a reward** was not produced. Four
  challenges were filed across two rounds (two against FAITHFUL forks, two
  against NOT_FAITHFUL forks) and every one resolved `RESOLVED_UNCHANGED`. That is stable behaviour, but it
  means the reward path has only been exercised by unit tests.
- **A naturally failing transfer was not observed** in any run. Every payment
  that was attempted reached its recipient, including to a contract with no
  receive handler. The recovery flow was exercised end to end on payments that
  had in fact arrived. The contract cannot observe a wallet balance, so
  non-delivery is attested by the recipient and the admin. That is a trust
  assumption, stated in `STAGE_12_PAYOUTS_AND_EVIDENCE.md`.
- **One unexplained reading.** In one run, right after settling a challenger
  refund, the wallet showed no change although the ledger recorded a SENT
  payout of 0.0500 GEN. An identical scenario re-run later credited the wallet
  immediately and still showed the same figure 45 seconds later. The original
  payout is still SENT on the test copy, which is exactly the ambiguous case the
  dispute and retry flow exists for. We do not have an explanation for the
  single missed reading.
- **Large documents:** the adjudicator sees a relevance-ranked excerpt, not the
  whole file, whenever a document exceeds the per-record cap. The verdict is
  then flagged `COVERAGE:PARTIAL` and the prompt tells the model to answer
  UNCLEAR on any dimension that omitted text could change. This reduces the
  risk of hiding a qualification; it does not remove it.
- **The 72-hour finalization on production** completes only after the real
  window has run. The production root's window opened when this contract was
  set up (see below); finalizing it is a later, separate transaction.

## Real 72-hour finalization on the production contract

Forks can only be created after the root is finalized FAITHFUL, and that takes
the full 72 hours on production. So the production proof uses the root itself.
All of this happened on `0x4aC19F1f24d8462f0F3b0B19d8A847e8C4415670`:

| Time (UTC) | Event |
|---|---|
| 2026-10-13 23:24:32 | Demo root (EIP-1559) judged FAITHFUL; first challenge window opened |
| 2026-10-13 23:46 | `finalize` refused: "challenge window not yet elapsed (1257s of 259200s required)" |
| 2026-10-13 23:48 | A challenge (ground `CONSTRAINT_INCOMPLETE`) was filed during the window. `finalize` was then refused ("call open_finality_window first") and the root's status moved to `ENVELOPE_CHALLENGE_OPEN` |
| 2026-10-13 23:51 | Challenge re-adjudicated: `RESOLVED_UNCHANGED` (the original verdict stands) |
| 2026-10-13 23:51:57 | Window reopened, which restarts the clock |
| **2026-10-16 23:51:57** | **Earliest time `finalize` can succeed** |

Read it yourself: `get_constants` returns `challenge_window_seconds = 259200`,
and `get_root_proposal(1)` returns `finality_window_opened_at` (chain time
`1791935517` for the current window).

The finalizing transaction is not part of this document yet. It can only be
sent after the time above, and its result will be added here then. Nothing in
this section has been simulated.
