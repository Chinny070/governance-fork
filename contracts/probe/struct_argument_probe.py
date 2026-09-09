# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# =============================================================================
# Struct Argument Runtime Probe
#
# Isolated, minimal probe. Does NOT import or reference
# contracts/governance_fork.py in any way. Answers exactly one question:
#
#   Can a GenVM public method receive an @allow_storage dataclass-typed
#   PARAMETER and have it reconstructed into the declared dataclass type
#   before the method body executes -- or does it arrive as a raw decoded
#   map (dict)?
#
# Background: contracts/governance_fork.py's
# submit_root_envelope(envelope: IntentEnvelope, ...) failed live via the
# genlayer CLI (v0.39.2) / genlayer-js (v1.1.8) with:
#   AttributeError: 'dict' object has no attribute 'objective'
#
# Source-level investigation of both installed client packages (not
# guesswork) confirmed the client-side calldata encoder has no distinct
# "struct" wire type at all -- the complete wire type enum is
# TYPE_SPECIAL/PINT/NINT/BYTES/STR/ARR/MAP, seven types total, and any
# plain JS object -- whether meant for a dataclass-typed parameter or a
# generic dict -- always encodes identically as TYPE_MAP. No ABI/schema is
# consulted client-side when building calldata. So the calldata Governance
# Fork received was already the only possible representation a client can
# produce; the open question is purely server-side (GenVM) behavior, which
# this probe exists to observe directly rather than infer further from
# source reading.
#
# NO WORKAROUNDS: probe_struct below uses plain attribute access
# (arg.label, arg.value) only. No manual dict conversion, no try/except,
# no fallback. If GenVM does not reconstruct `arg` into a ProbeStruct
# instance before this method body runs, this call is EXPECTED to raise
# the same class of AttributeError observed on Governance Fork -- that is
# the result being measured, not a bug to route around here.
#
# Method B (a generic dict/mapping-typed control parameter) was
# deliberately OMITTED. GenLayer's own storage documentation
# (docs.genlayer.com/developers/intelligent-contracts/storage) states
# plainly: "dict[K, V] needs to be replaced with TreeMap[K, V]" -- bare
# `dict` is not a schema-valid type. This is consistent with every
# method/field signature across this entire project (governance_fork.py,
# every prior probe): none ever declares a bare `dict` or `list` parameter
# anywhere. Using TreeMap[str, ...] instead would reintroduce exactly the
# storage-generic construction complexity this probe is explicitly meant
# to avoid, and would not actually test "generic dict calldata" in any
# meaningful sense distinct from Probe A itself (a TreeMap value is a
# persistent storage-backed type, not a transient generic mapping). No
# unsupported typing form was invented to force this control into
# existence.
# =============================================================================

from genlayer import *
from dataclasses import dataclass


@allow_storage
@dataclass
class ProbeStruct:
    label: str
    value: u256


class Contract(gl.Contract):
    last_label: str
    last_value: u256
    call_count: u256

    def __init__(self):
        self.last_label = ""
        self.last_value = u256(0)
        self.call_count = u256(0)

    # -------------------------------------------------------------------
    # Write Method A -- direct dataclass argument (the primary probe)
    # -------------------------------------------------------------------

    @gl.public.write
    def probe_struct(self, arg: ProbeStruct) -> None:
        # Deliberate attribute access only. No dict-style access
        # (arg["label"]), no manual reconstruction, no try/except. If
        # reconstruction does not happen server-side, this raises
        # AttributeError -- exactly the class of failure observed on
        # Governance Fork's submit_root_envelope -- and that failure is
        # not caught here.
        self.last_label = arg.label
        self.last_value = arg.value
        self.call_count = u256(int(self.call_count) + 1)

    # -------------------------------------------------------------------
    # Write Method C -- flattened scalar control (baseline)
    # -------------------------------------------------------------------

    @gl.public.write
    def probe_flat(self, label: str, value: u256) -> None:
        # Ordinary scalar calldata, no struct involved. Proves the same
        # deployment, same wallet, same call mechanism works at all when
        # the target parameters are plain scalars.
        self.last_label = label
        self.last_value = value
        self.call_count = u256(int(self.call_count) + 1)

    # -------------------------------------------------------------------
    # Views -- authoritative state re-read
    # -------------------------------------------------------------------

    @gl.public.view
    def get_state(self) -> ProbeStruct:
        return ProbeStruct(label=self.last_label, value=self.last_value)

    @gl.public.view
    def get_call_count(self) -> u256:
        return self.call_count
