# Stage 12: payouts you can audit, and honest handling of long evidence

This stage answers three things: does real GEN reach wallets, what happens
when a payment goes wrong, and what the adjudicator does with long documents.
Deployment and test evidence are in [`DEPLOYMENT.md`](DEPLOYMENT.md).

## 1. GEN reaches wallets

On StudioNet a plain contract-to-contract transfer (`gl.get_contract_at(addr)
.emit_transfer(...)`) lowers the contract balance but does not credit an
ordinary wallet. Sending through an EVM interface does:

```python
@gl.evm.contract_interface
class _EvmRecipient:
    class View: pass
    class Write: pass

_EvmRecipient(recipient).emit_transfer(value=u256(amount))
```

Every outgoing payment (bond refunds, slashed remainders, challenger rewards,
treasury withdrawals) now uses this call. A static check fails the build if the
old call style comes back. Wallet balances were read from the chain before and
after each settlement (see `DEPLOYMENT.md`).

## 2. A payout ledger instead of fire-and-forget

Each payment gets a record: recipient, amount, source (bond or treasury), a
status and an attempt count.

```
SENT --confirm_payout--------------------------> CONFIRMED   (final)
SENT --report_payout_not_received--> DISPUTED
DISPUTED --resolve_payout(delivered=false)--> RETRYABLE --retry_payout--> SENT (attempt 2, 3)
DISPUTED --resolve_payout(delivered=true)---> CONFIRMED
```

Rules that stop duplicate or unfunded transfers:

- Only the recipient or the treasury admin can confirm; only the recipient can
  dispute; only the admin can attest; a stranger can do none of these.
- A dispute alone never sends anything. The admin must attest non-delivery.
- A retry is paid only from the **treasury pool**, never from other people's
  bonds, and only while the contract balance still covers all locked bonds plus
  the pool. A retry that the pool cannot fund is refused until someone calls the
  payable `fund_treasury`.
- At most 3 attempts per payout. A payout that was already confirmed cannot be
  retried.

`get_reserves` returns the contract balance, locked bonds, treasury pool,
in-flight payouts and any shortfall, so anyone can reconcile the books. The
Bonds page shows the same figures and a payout column with the allowed actions.

**Trust assumption, stated plainly.** A contract cannot read a wallet balance.
Whether a payment arrived is therefore reported by the recipient and attested by
the admin. If those two are dishonest or wrong, a payment can be repeated (the
admin pays out of the treasury pool, so other participants are still safe), or a
real non-delivery can go unrecovered. The ledger makes every such claim
visible on-chain; it does not make it automatic.

## 3. Long evidence documents

The adjudicator prompt has a size limit, so a long document cannot be shown in
full. The old cut kept only the start and end of a document, which could drop
the one paragraph containing an exception.

Now, when a document is over the per-record cap:

- the document is split into fixed 800-character blocks;
- the first block is always kept;
- the other blocks are ranked by how many words from the submitter's relevance
  claim they contain, and kept until the budget is used;
- kept blocks are shown in their original order with a visible
  `[...omitted...]` marker between non-adjacent ones;
- the header states `coverage=shown/total`, and a `PARTIAL EXCERPT` note is
  added;
- the prompt tells the model that omitted text may hold qualifications,
  exceptions or contradictions, and that any dimension which could change
  because of it must be answered UNCLEAR, not SATISFIED;
- the stored verdict gets the reason code `COVERAGE:PARTIAL`, which the UI shows.

Everything is deterministic, so validators build the same prompt. **This
reduces the chance of a hidden qualification; it does not guarantee that none
exists.** A decisive paragraph that shares no words with the relevance claim can
still be left out, and the verdict then says so through the PARTIAL flag.

## 4. What the UI makes clear

- Community-imported proposals are labelled as community records, not official
  DAO decisions.
- Adoption signals are labelled non-binding.
- Every write waits for FINALIZED and checks that the leader execution
  succeeded before the interface reports success.
