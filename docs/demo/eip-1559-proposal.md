# EIP-1559: Fee market reform with a burned base fee

Proposal text used as the canonical source for the Governance Fork demo.
It restates how Ethereum's transaction fee mechanism works, as documented at
https://ethereum.org/en/developers/docs/gas/, and states explicitly which parts
of the design are fixed and which parts may be changed.

## Summary

Every transaction pays a fee made of two parts:

- the **base fee**, which is set by the protocol and adjusts automatically with
  demand; it is burned and is not paid to validators;
- the **priority fee (tip)**, which is set by each user and is paid to the
  validator who includes the transaction.

## Specification

1. The base fee is calculated by the protocol from how full the previous block
   was compared with the target block size. It rises when blocks are fuller than
   the target and falls when they are emptier.
2. The base fee changes by at most 12.5% from one block to the next.
3. The base fee is burned (removed from circulation). It is never paid to a
   validator.
4. Each user chooses their own priority fee (tip) and adds it on top of the base
   fee to make a transaction attractive to validators. The example in the
   documentation uses a tip of 2 gwei.

## What may not change (immutable dimensions)

- `base_fee_burned`: the base fee is always burned and never paid to validators.
- `base_fee_max_change_percent`: the base fee changes by at most 12.5% per block.

These are part of the protocol design. A fork that changes them is not a faithful
version of this proposal.

## What may change (mutable dimensions)

- `priority_fee_tip_gwei`: the priority tip is chosen by the user and may vary
  freely. A fork may suggest a different default tip without changing the design.
