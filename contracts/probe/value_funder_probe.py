# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# Isolated helper for the value-transfer probe: funded via sim_fundAccount,
# then forwards native GEN into another Intelligent Contract's payable
# method (IC -> IC internal message with value) -- the path that may work
# on StudioNet where IC -> EOA does not. No governance logic.

from genlayer import *


class Contract(gl.Contract):
    call_count: u256
    last_note: str

    def __init__(self):
        self.call_count = u256(0)
        self.last_note = "none"

    @gl.public.write.payable
    def __receive__(self) -> None:
        self.call_count = u256(int(self.call_count) + 1)
        self.last_note = "recv " + str(int(gl.message.value))

    @gl.public.write
    def forward_deposit(self, target: str, amount: u256) -> None:
        amt = u256(int(amount))
        gl.get_contract_at(target).emit(value=amt).deposit()
        self.call_count = u256(int(self.call_count) + 1)
        self.last_note = "fwd " + str(int(amt)) + " bal=" + str(int(self.balance))

    @gl.public.write
    def forward_transfer(self, target: str, amount: u256) -> None:
        amt = u256(int(amount))
        gl.get_contract_at(target).emit_transfer(value=amt)
        self.call_count = u256(int(self.call_count) + 1)
        self.last_note = "xfer " + str(int(amt)) + " bal=" + str(int(self.balance))

    @gl.public.view
    def get_balance(self) -> u256:
        return u256(int(self.balance))

    @gl.public.view
    def get_note(self) -> str:
        return self.last_note
