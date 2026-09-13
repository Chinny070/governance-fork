# v0.2.16 -- pinned to the SAME runner hash this whole project already uses
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# =============================================================================
# Datetime/timestamp probe (Stage 10 follow-up)
#
# block_time_probe.py already proved gl.block / gl.chain do not exist as
# namespaces, and that gl.message has no `block_number` field. It never
# tried gl.message.timestamp, gl.message.datetime, or gl.message_raw --
# names suggested by the GenVM host-level "MessageData" schema (which
# documents a `datetime` transaction-timestamp field passed from the node
# to every GenVM execution) and by the newer v0.3.0 SDK's
# `MessageRawType.datetime`. This probe checks whether that same
# host-level field is already reachable from Python on THIS pinned
# runtime, under any plausible attribute name, before concluding a newer
# runtime version is required at all.
#
# RESULT (live, StudioNet): `gl.message_raw` is a real, populated dict at
# the top level of `gl` (distinct from `gl.message`, which has no such
# field). `gl.message_raw["datetime"]` returns a genuine ISO-8601 UTC
# timestamp, e.g. "2026-09-13T01:41:42.341487Z".
#
#   dir(gl.message_raw) = ['clear', 'copy', 'fromkeys', 'get', 'items',
#     'keys', 'pop', 'popitem', 'setdefault', 'update', 'values']  (plain dict)
#   gl.message_raw = {'chain_id': 61999, 'contract_address': Address(...),
#     'datetime': '2026-09-13T01:41:42.341487Z', 'entry_data': b'...',
#     'entry_kind': 0, 'entry_stage_data': None, 'is_init': False,
#     'origin_address': Address(...), 'sender_address': Address(...),
#     'stack': [], 'value': 0}
#
# Called `touch()` (a write) twice, ~60s apart, each storing the value:
# BOTH transactions reached full validator consensus (FINALIZED, no
# disagreement) -- proving the value is fixed per-transaction and
# identical across every validator, matching the GenVM host spec
# ("deterministic mode returns the transaction timestamp, keeping the
# value deterministic across validators"). The two stored values were
# genuinely different and increased by the expected amount. Python's
# `datetime.fromisoformat` + `timedelta.total_seconds()` correctly parsed
# and diffed them inside the sandbox (pure arithmetic on already-fixed
# data, so no consensus risk). This is a REAL, live, consensus-safe clock
# on the currently pinned runtime -- no migration to a newer runner hash
# needed. See governance_fork.py's `_now_epoch_seconds()` /
# `open_finality_window()` / `finalize()` and
# docs/STAGE_10_STEWARD_FIXES.md section 4 for the production fix this
# unlocked (a real, enforced-duration challenge period), further
# confirmed by a full live end-to-end contract deployment.
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
    first_dt: str
    last_dt: str

    def __init__(self):
        self.call_count = u256(0)
        self.last_note = "none"
        self.first_dt = ""
        self.last_dt = ""

    @gl.public.write.payable
    def touch(self) -> None:
        self.call_count = u256(int(self.call_count) + 1)
        self.last_note = "touched, value=" + str(int(gl.message.value))
        dt = str(gl.message_raw["datetime"])
        if self.first_dt == "":
            self.first_dt = dt
        self.last_dt = dt

    @gl.public.view
    def get_state(self) -> ProbeState:
        return ProbeState(call_count=self.call_count, last_note=self.last_note)

    @gl.public.view
    def get_dts(self) -> str:
        return "first=" + self.first_dt + " last=" + self.last_dt

    @gl.public.view
    def probe(self) -> str:
        out = []

        def try_get(label, fn):
            try:
                v = fn()
                out.append(label + " = " + repr(v))
            except Exception as e:
                out.append(label + " ERROR: " + type(e).__name__ + ": " + str(e))

        try_get("dir(gl.message_raw)", lambda: [a for a in dir(gl.message_raw) if not a.startswith("_")])
        try_get("gl.message_raw.datetime", lambda: gl.message_raw.datetime)
        try_get("gl.message_raw.timestamp", lambda: gl.message_raw.timestamp)
        try_get("gl.message_raw", lambda: gl.message_raw)
        try_get("dir(gl.MessageRawType)", lambda: [a for a in dir(gl.MessageRawType) if not a.startswith("_")])

        def parse_and_diff():
            import datetime as _dt
            a = _dt.datetime.fromisoformat(str(self.first_dt).replace("Z", "+00:00"))
            b = _dt.datetime.fromisoformat(str(self.last_dt).replace("Z", "+00:00"))
            return (b - a).total_seconds()

        try_get("import datetime; parse+diff(first,last)", parse_and_diff)
        return "\n".join(out)
