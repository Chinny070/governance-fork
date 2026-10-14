# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# Test-only helper for the Governance Fork failed-payout test. It locks a bond
# in the governance contract as itself (so the bond owner is this contract),
# and it has NO payable receive handler, so a refund sent back to it is a
# transfer that the recipient cannot accept. No governance logic.

from genlayer import *


class Contract(gl.Contract):
    call_count: u256
    last_note: str

    def __init__(self):
        self.call_count = u256(0)
        self.last_note = "none"

    @gl.public.write.payable
    def fund(self) -> None:
        # Lets the test put GEN into this contract so it can lock a bond.
        self.call_count = u256(int(self.call_count) + 1)
        self.last_note = "funded " + str(int(gl.message.value))

    @gl.public.write
    def lock_in(self, target: str, amount: u256) -> None:
        amt = u256(int(amount))
        gl.get_contract_at(Address(target)).emit(value=amt).lock_bond("FORK_CREATION")
        self.call_count = u256(int(self.call_count) + 1)
        self.last_note = "locked " + str(int(amt))

    @gl.public.view
    def get_balance(self) -> u256:
        return u256(int(self.balance))

    @gl.public.view
    def get_note(self) -> str:
        return self.last_note
