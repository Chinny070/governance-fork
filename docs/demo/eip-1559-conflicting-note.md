# Community note: where does the EIP-1559 base fee go? (CONFLICTING ACCOUNT)

This note is published for the Governance Fork conflicting-evidence test. It
deliberately contradicts the proposal text in eip-1559-proposal.md.

Claim made by this note: the base fee is NOT burned. Instead, after every block
the whole base fee is paid out to the validator who proposed that block, in
addition to the priority tip, and users therefore cannot expect any reduction in
the circulating supply from transaction fees.

If this note is correct, the proposal's immutable dimension `base_fee_burned`
is false.
