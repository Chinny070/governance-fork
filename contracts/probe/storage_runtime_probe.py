# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# =============================================================================
# Storage Runtime Capability Probe
#
# Isolated, minimal probe contract. Does NOT import or reference
# contracts/governance_fork.py in any way. Exists only to answer, against
# the ACTUAL pinned GenVM runtime (same "Depends" hash as governance_fork.py),
# the open storage-construction questions raised by the audit in
# docs/STORAGE_CONSTRUCTION_AUDIT.md:
#
#   A. Can a DynArray field nested inside an @allow_storage dataclass be
#      given a plain Python list at construction time and persist
#      correctly, without gl.storage.inmem_allocate?
#   B. Does a TreeMap[K, DynArray[V]] value auto-vivify as an empty
#      DynArray for a key that has never been assigned, so .append() can
#      be called directly on a fresh key?
#   C. Do ordinary transient Python list operations (build/append/iterate)
#      work fine for purely local, deterministic computation that never
#      touches persistent DynArray-typed storage at all?
#   D. Can a plain Python list be assigned directly into a top-level,
#      Contract-level DynArray-typed storage field?
#   E. Can a view method whose declared return structure contains a
#      DynArray field be satisfied by a freshly-built transient Python
#      list, never touching persistent storage?
#
# Each hypothesis lives in its own write/view method pair so that one
# failure never prevents testing the others -- per project direction, no
# experiment is combined with another in a single transaction, and no
# hypothesis has a same-transaction fallback that would mask a failure.
#
# ALREADY KNOWN LIVE (on governance_fork.py, same pinned runtime):
#   DynArray[T]()                         -> TypeError: this class can't
#                                             be instantiated by user
#   gl.storage.inmem_allocate(DynArray[T]) -> TypeError:
#                                             _GenericAlias.__init__()
#                                             missing 1 required
#                                             positional argument: 'args'
#
# probe_x_negative_control_inmem_allocate reproduces the second failure
# deliberately, in this exact isolated contract, as a same-runtime,
# same-moment-in-time sanity check -- not to re-litigate whether it
# fails, but to confirm the runtime version observed by this probe is
# the same one that produced the two production failures. It is its own
# isolated method; its failure (expected) cannot block or interfere with
# probes A-E.
#
# Schema acceptance is not runtime success. Every hypothesis here must be
# judged by its actual live Execution Result, not by whether Studio
# accepts the schema load.
# =============================================================================

from genlayer import *
from dataclasses import dataclass

import collections.abc
import hashlib


# -----------------------------------------------------------------------
# Probe A: DynArray field nested inside an @allow_storage dataclass
# -----------------------------------------------------------------------

@allow_storage
@dataclass
class Record:
    id: u256
    items: DynArray[u256]


# -----------------------------------------------------------------------
# Probe E: DynArray field inside a return-only (never persisted) dataclass
# -----------------------------------------------------------------------

@allow_storage
@dataclass
class ProbeEResult:
    items: DynArray[u256]


class Contract(gl.Contract):
    # Probe A storage
    records: TreeMap[u256, Record]
    next_record_id: u256

    # Probe B storage
    index: TreeMap[u256, DynArray[u256]]

    # Probe C storage (deterministic result only; no transient list ever
    # touches this field's type -- it is bytes, not DynArray)
    probe_c_last_hash: bytes

    # Probe D storage
    probe_d_items: DynArray[u256]

    # Negative-control storage (mirrors Probe A's shape, used only by
    # probe_x_negative_control_inmem_allocate)
    negative_control_items: DynArray[u256]

    def __init__(self):
        self.next_record_id = u256(1)

    # -------------------------------------------------------------------
    # Probe A -- nested persisted DynArray field
    # -------------------------------------------------------------------

    @gl.public.write
    def probe_a_create_and_append(self, value: u256) -> u256:
        # Hypothesis under test: a nested DynArray field can be given a
        # plain Python list literal at dataclass-construction time and
        # still persist correctly as a DynArray once the whole
        # dataclass is assigned into storage -- with no
        # gl.storage.inmem_allocate call anywhere in this method.
        record_id = self.next_record_id
        self.next_record_id = u256(int(record_id) + 1)
        record = Record(id=record_id, items=[])
        self.records[record_id] = record
        self.records[record_id].items.append(value)
        return record_id

    @gl.public.view
    def probe_a_read(self, record_id: u256) -> Record:
        if record_id not in self.records:
            raise gl.vm.UserError("record not found")
        return self.records[record_id]

    # -------------------------------------------------------------------
    # Probe B -- TreeMap[u256, DynArray[u256]] fresh-key autovivification
    # -------------------------------------------------------------------

    @gl.public.write
    def probe_b_append_fresh_key(self, key: u256, value: u256) -> None:
        # Hypothesis under test: self.index[key] auto-vivifies as an
        # empty, zero-initialized DynArray for a key that has never been
        # assigned, so .append() can be called directly with no prior
        # explicit assignment and no gl.storage.inmem_allocate call.
        #
        # Deliberately no guard, no fallback, no try/except: if the
        # hypothesis is false, this call is EXPECTED to fail (e.g. with
        # a KeyError or similar) -- that failure is itself the result
        # being measured, not a bug to work around in this probe.
        self.index[key].append(value)

    @gl.public.view
    def probe_b_read(self, key: u256) -> collections.abc.Sequence[u256]:
        if key not in self.index:
            raise gl.vm.UserError("key not found")
        return self.index[key]

    # -------------------------------------------------------------------
    # Probe C -- transient Python list for purely local computation
    # -------------------------------------------------------------------

    @gl.public.write
    def probe_c_transient_hash(self, a: u256, b: u256, c: u256) -> bytes:
        # Hypothesis under test: ordinary transient Python list
        # operations (build, append, iterate) execute successfully and
        # their result can feed a deterministic computation whose OUTPUT
        # (bytes) is stored -- while the transient list itself never
        # touches any DynArray-typed storage slot.
        values = []
        values.append(int(a))
        values.append(int(b))
        values.append(int(c))
        buf = b"probe-c/v1\n"
        for v in values:
            buf = buf + str(v).encode("ascii") + b"\n"
        digest = hashlib.sha256(buf).digest()
        self.probe_c_last_hash = digest
        return digest

    @gl.public.view
    def probe_c_read(self) -> bytes:
        return self.probe_c_last_hash

    # -------------------------------------------------------------------
    # Probe D -- plain Python list assigned into persistent DynArray field
    # -------------------------------------------------------------------

    @gl.public.write
    def probe_d_assign_list(self, a: u256, b: u256) -> None:
        # Hypothesis under test: a plain Python list can be assigned
        # directly into a top-level, Contract-level DynArray[u256]
        # storage field, with the runtime performing its own coercion
        # into the real storage representation -- no
        # gl.storage.inmem_allocate involved at all.
        self.probe_d_items = [a, b]

    @gl.public.view
    def probe_d_read(self) -> collections.abc.Sequence[u256]:
        return self.probe_d_items

    # -------------------------------------------------------------------
    # Probe E -- transient Python list satisfying a DynArray-typed return
    # -------------------------------------------------------------------

    @gl.public.view
    def probe_e_return_list(self, n: u32) -> ProbeEResult:
        # Hypothesis under test: a view method whose declared return
        # structure contains a DynArray[u256] field can be satisfied by
        # a freshly-built transient plain Python list -- never touching
        # persistent storage at all -- correctly ABI-encoded as the
        # declared type. Mirrors governance_fork.py's PageIds(items=...)
        # pagination-return pattern.
        out = []
        i = 0
        while i < int(n):
            out.append(u256(i))
            i = i + 1
        return ProbeEResult(items=out)

    # -------------------------------------------------------------------
    # Negative control -- reproduces the already-known-failing pattern,
    # in this exact isolated contract, on this exact pinned runtime, as
    # a same-moment-in-time sanity check only. Expected to fail. Its own
    # isolated method: cannot block or interfere with probes A-E.
    # -------------------------------------------------------------------

    @gl.public.write
    def probe_x_negative_control_inmem_allocate(self, value: u256) -> None:
        allocated = gl.storage.inmem_allocate(DynArray[u256])
        allocated.append(value)
        self.negative_control_items = allocated
