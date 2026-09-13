# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# =============================================================================
# Block/Time Runtime Probe  (Stage 10 / steward-requested challenge period)
#
# Isolated, minimal probe. Does NOT import or reference
# contracts/governance_fork.py.
#
# Question: does this pinned GenVM runtime expose ANY monotonic counter --
# block number, chain height, tx sequence -- that a contract could gate a
# real minimum-gap challenge period on? Every timestamp field in
# governance_fork.py has always read u256(0), live, repeatedly -- that
# proves no wall-clock TIME source exists. It does not by itself prove no
# block-NUMBER or sequence accessor exists; this probe checks that
# directly instead of assuming, per this project's standing rule: probe
# live, don't trust docs or an inherited conclusion from a different
# question.
#
# Deploy note: an earlier, even more minimal version of this file
# (single field, single view method, no dataclass) deployed as
# "invalid_contract" with no diagnostic detail, on every attempt, for
# reasons unrelated to gl.block/gl.chain (a structurally identical
# skeleton with a dataclass + payable + write + view methods deploys
# fine). Never resolved further since it wasn't this probe's question;
# noted here in case it matters to a future probe.
#
# RESULT (live, StudioNet, this exact file at 0x7594d3D29DabeB4ADd174809B939d4b85e70fB6b):
#   gl.message.sender_address = Address("0x3A31...")          -- exists (known)
#   gl.block.number   ERROR: AttributeError: module 'genlayer.gl' has no attribute 'block'
#   gl.block.timestamp ERROR: same -- gl.block does not exist at all
#   gl.chain.block_number ERROR: AttributeError: module 'genlayer.gl' has no attribute 'chain'
#   gl.message.block_number ERROR: AttributeError: 'MessageType' object has no attribute 'block_number'
#   gl.vm.block_number ERROR: AttributeError: module 'genlayer.gl.vm' has no attribute 'block_number'
#
# CONCLUSION: gl.block and gl.chain do not exist as namespaces on this
# runtime at all (not "exist but empty" -- AttributeError at the module
# level). gl.message and gl.vm exist (already known) but expose no block
# number / height / sequence field. There is no monotonic counter of any
# kind available to an Intelligent Contract on this pinned runtime -- a
# literal enforced-duration or enforced-block-count challenge period is
# not buildable here. See docs/STAGE_10_STEWARD_FIXES.md for how
# open_finality_window/finalize's two-step commit substitutes for this.
# =============================================================================

from genlayer import *
from dataclasses import dataclass


@allow_storage
@dataclass
class ProbeState:
    call_count: u256
    last_note: str


class Contract(gl.Contract):
    call_count: u256
    last_note: str

    def __init__(self):
        self.call_count = u256(0)
        self.last_note = "none"

    @gl.public.write.payable
    def touch(self) -> None:
        # Payable + write, matching the shape of every other probe in this
        # directory that has deployed successfully -- kept even though this
        # probe's question doesn't need native value.
        self.call_count = u256(int(self.call_count) + 1)
        self.last_note = "touched, value=" + str(int(gl.message.value))

    @gl.public.view
    def get_state(self) -> ProbeState:
        return ProbeState(call_count=self.call_count, last_note=self.last_note)

    @gl.public.view
    def probe(self) -> str:
        out = []

        def try_get(label, fn):
            try:
                v = fn()
                out.append(label + " = " + repr(v))
            except Exception as e:
                out.append(label + " ERROR: " + type(e).__name__ + ": " + str(e))

        try_get("gl.message.sender_address", lambda: gl.message.sender_address)
        try_get("gl.block.number", lambda: gl.block.number)
        try_get("gl.block.timestamp", lambda: gl.block.timestamp)
        try_get("gl.chain.block_number", lambda: gl.chain.block_number)
        try_get("gl.message.block_number", lambda: gl.message.block_number)
        try_get("gl.vm.block_number", lambda: gl.vm.block_number)
        return "\n".join(out)
