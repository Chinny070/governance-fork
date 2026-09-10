# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# =============================================================================
# Value Transfer Runtime Probe  (Stage 9 / bond-economics pre-implementation)
#
# Isolated, minimal probe. Does NOT import or reference
# contracts/governance_fork.py. Parameterless constructor.
#
# Purpose: establish, against the ACTUAL pinned GenVM runtime
# (py-genlayer:1jb45aa8...), the native-GEN facts the bond stage depends on
# and that are NOT yet live-verified for this contract:
#
#   1. A @gl.public.write.payable method can read gl.message.value (u256)
#      and the amount actually arrives.
#   2. self.balance reads the contract's own GEN balance inside a write.
#   3. The exact idiom for sending native GEN OUT to an EOA on this runtime
#      version -- candidates, tried one per mode so a single deploy tests
#      all of them:
#        mode 1: gl.get_contract_at(Address(to)).emit_transfer(value=amt)
#        mode 2: gl.Account(Address(to)).emit_transfer(value=amt)
#        mode 3: Account(Address(to)).emit_transfer(value=amt)   (star import)
#        mode 4: gl.contract.get_at(Address(to)).emit_transfer(value=amt)
#   4. Whether emit_transfer's balance effect is observable on StudioNet
#      (docs say Studio simulates balances in a local DB -- confirm).
#   5. Whether a transfer of more than self.balance reverts cleanly.
#
# NO web retrieval, NO LLM / semantic calls, NO governance logic.
# =============================================================================

from genlayer import *
from dataclasses import dataclass

MAX_NOTE_LEN = 200


@allow_storage
@dataclass
class ProbeState:
    call_count: u256
    last_action: str
    last_received: u256
    last_balance_seen: u256
    last_transfer_mode: u256
    last_transfer_amount: u256
    last_note: str


class Contract(gl.Contract):
    call_count: u256
    last_action: str
    last_received: u256
    last_balance_seen: u256
    last_transfer_mode: u256
    last_transfer_amount: u256
    last_note: str

    def __init__(self):
        self.call_count = u256(0)
        self.last_action = "none"
        self.last_received = u256(0)
        self.last_balance_seen = u256(0)
        self.last_transfer_mode = u256(0)
        self.last_transfer_amount = u256(0)
        self.last_note = "none"

    def _bump(self, action: str, note: str) -> None:
        self.call_count = u256(int(self.call_count) + 1)
        self.last_action = action
        self.last_note = note[:MAX_NOTE_LEN]

    @gl.public.write.payable
    def deposit(self) -> None:
        # Fact 1 + 2: read incoming value and own balance.
        v = gl.message.value
        self.last_received = u256(int(v))
        bal = self.balance
        self.last_balance_seen = u256(int(bal))
        self._bump("deposit", "received=" + str(int(v)) + " balance=" + str(int(bal)))

    @gl.public.write.payable
    def __receive__(self) -> None:
        v = gl.message.value
        self.last_received = u256(int(v))
        self.last_balance_seen = u256(int(self.balance))
        self._bump("__receive__", "bare value received=" + str(int(v)))

    @gl.public.write
    def payout(self, to_addr: str, amount: u256, mode: u256) -> None:
        # Fact 3: the send idiom. One mode per call; whichever raises,
        # the transaction reverts and we learn that idiom is unavailable
        # on this runtime version.
        amt = u256(int(amount))
        m = int(mode)
        self.last_transfer_mode = u256(m)
        self.last_transfer_amount = amt
        # Runtime fact: an address-shaped public str param arrives already
        # decoded as an Address on this runtime -- do not re-wrap it.
        target = to_addr
        if m == 1:
            gl.get_contract_at(target).emit_transfer(value=amt)
        elif m == 2:
            gl.Account(target).emit_transfer(value=amt)
        elif m == 3:
            Account(target).emit_transfer(value=amt)
        elif m == 4:
            gl.contract.get_at(target).emit_transfer(value=amt)
        else:
            raise gl.vm.UserError("unknown mode")
        self.last_balance_seen = u256(int(self.balance))
        self._bump("payout", "mode=" + str(m) + " amount=" + str(int(amt)) + " ok")

    @gl.public.view
    def get_state(self) -> ProbeState:
        return ProbeState(
            call_count=self.call_count,
            last_action=self.last_action,
            last_received=self.last_received,
            last_balance_seen=self.last_balance_seen,
            last_transfer_mode=self.last_transfer_mode,
            last_transfer_amount=self.last_transfer_amount,
            last_note=self.last_note,
        )

    @gl.public.view
    def get_balance(self) -> u256:
        return u256(int(self.balance))
