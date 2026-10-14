# Community note: who sets the priority tip? (CONFLICTING ACCOUNT)

This note is published for the Governance Fork conflicting-evidence test. It
deliberately contradicts the proposal text in eip-1559-proposal.md.

Claim made by this note: the priority tip is NOT chosen by users. The protocol
fixes the priority tip at 2 gwei for every transaction, wallets have no way to
raise or lower it, and any change to the tip value therefore changes the
protocol itself.

If this note is correct, the proposal's mutable dimension `priority_fee_tip_gwei`
is not mutable by users at all, and a fork that changes it alters a protocol
constant.
