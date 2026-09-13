"""Local test shim for the `genlayer` module.

Provides just enough of the runtime surface used by
`contracts/governance_fork.py` so its Stage 3 logic can be exercised in
plain CPython. This is a TEST-ONLY substitute: it does not implement
consensus, storage persistence, or any nondeterministic operation.

Install by calling `install()` before importing the contract module.
"""

from __future__ import annotations

import json as _json
import sys
import types
from dataclasses import dataclass as _stdlib_dataclass  # noqa: F401 -- for symmetry


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


class _IntWrapper(int):
    """Base int-like wrapper preserving the target type name."""

    def __new__(cls, v=0):
        return super().__new__(cls, int(v))


class u8(_IntWrapper):
    pass


class u16(_IntWrapper):
    pass


class u32(_IntWrapper):
    pass


class u64(_IntWrapper):
    pass


class u128(_IntWrapper):
    pass


class u256(_IntWrapper):
    pass


class i8(_IntWrapper):
    pass


class i16(_IntWrapper):
    pass


class i32(_IntWrapper):
    pass


class i64(_IntWrapper):
    pass


bigint = int


class Address(str):
    def __new__(cls, v=""):
        return super().__new__(cls, str(v))

    @property
    def as_hex(self):
        # Matches the local-reference pattern (gl.message.sender_address.as_hex
        # returns a str). Address values in shim land are already hex-shaped
        # strings, so we just return self.
        return str(self)


# ---------------------------------------------------------------------------
# Storage collections
# ---------------------------------------------------------------------------


class TreeMap(dict):
    def __class_getitem__(cls, item):  # TreeMap[K, V] -> TreeMap
        return cls


class DynArray(list):
    def __class_getitem__(cls, item):  # DynArray[T] -> DynArray
        return cls


class _StorageNamespace:
    """Shim for gl.storage. The live runtime forbids DynArray[T]()/
    TreeMap[K, V]() direct instantiation by contract code (fixed memory
    layout; see the "Live-runtime correction" comment at the top of
    contracts/governance_fork.py) and requires
    gl.storage.inmem_allocate(Type, *args, **kwargs) instead.

    This shim's TreeMap/DynArray are plain dict/list subclasses with no
    such restriction -- deliberately: existing test helpers across
    tests/test_stage_*.py already call shim.DynArray([...]) directly to
    build calldata-shaped inputs (simulating what the framework decodes
    from an external call, which is a different, always-permitted code
    path from a contract's own internal construction). Reproducing the
    live restriction faithfully would require distinguishing those two
    call paths, which this shim does not attempt. inmem_allocate here
    is therefore a pass-through, present only so contract code written
    against the real gl.storage.inmem_allocate API runs unchanged
    locally -- it does NOT verify that direct DynArray[T]()/
    TreeMap[K, V]() calls would fail live. That guarantee comes from
    the contract source itself using inmem_allocate everywhere, not
    from this shim catching a regression.
    """

    @staticmethod
    def inmem_allocate(type_, *args, **kwargs):
        return type_(*args, **kwargs)


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


def allow_storage(cls):
    return cls


# ---------------------------------------------------------------------------
# `gl` namespace
# ---------------------------------------------------------------------------


class _UserError(Exception):
    pass


class _MessageContext:
    """Per-test mutable caller context."""

    def __init__(self):
        self.sender_address = Address("0x" + "aa" * 20)
        self.value = u256(0)


# Stage 10: mock wall clock backing gl.message_raw["datetime"], modeling
# what contracts/probe/datetime_probe.py proved live -- a real, deterministic,
# monotonically-increasing ISO-8601 timestamp fixed per transaction. Reset
# to a fixed base alongside the native-GEN ledger (_CHAIN.reset()) so each
# fresh contract instance starts from the same deterministic point; tests
# advance it explicitly with advance_clock() to simulate elapsed time
# between open_finality_window() and finalize().
_CLOCK_BASE_EPOCH = 1_800_000_000
_CLOCK_STATE = {"epoch": _CLOCK_BASE_EPOCH}


def _epoch_to_iso(epoch):
    import datetime as _dt

    return (
        _dt.datetime.fromtimestamp(int(epoch), _dt.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


class _MessageRawDict(dict):
    """Minimal stand-in for gl.message_raw: only 'datetime' is modeled,
    since that's the only key governance_fork.py reads."""

    def __getitem__(self, key):
        if key == "datetime":
            return _epoch_to_iso(_CLOCK_STATE["epoch"])
        return super().__getitem__(key)


def advance_clock(seconds: int) -> None:
    """Test helper: move the mock clock forward, simulating elapsed
    wall-clock time between two write transactions."""
    _CLOCK_STATE["epoch"] += int(seconds)


def set_clock(epoch: int) -> None:
    """Test helper: pin the mock clock to an exact epoch-seconds value."""
    _CLOCK_STATE["epoch"] = int(epoch)


# Stage 9: native-GEN ledger for LOCAL LOGIC TESTS. Models what
# contracts/probe/value_transfer_probe.py proved on the pinned runtime:
# a payable method credits self.balance by gl.message.value, and
# gl.get_contract_at(addr).emit_transfer(value=v) moves v out of the
# executing contract's balance. It does NOT model consensus, message
# finalization timing, or the Studio IC->EOA credit gap.
_CONTRACT_ADDR = Address("0x" + "c0" * 20)


class _MockChain:
    def __init__(self):
        self._bal = {}
        self.current_contract = str(_CONTRACT_ADDR)

    def reset(self):
        self._bal = {}
        self.current_contract = str(_CONTRACT_ADDR)
        _CLOCK_STATE["epoch"] = _CLOCK_BASE_EPOCH

    def fund(self, addr, amount):
        a = str(addr)
        self._bal[a] = self._bal.get(a, 0) + int(amount)

    def balance_of(self, addr):
        return self._bal.get(str(addr), 0)

    def credit(self, addr, amount):
        if int(amount) == 0:
            return
        self.fund(addr, amount)

    def deposit_from(self, sender, contract, amount):
        # A payable call: credit the contract. Debit the sender too when
        # the sender has been funded in the ledger (so accounting-invariant
        # tests get true double-entry); an unfunded sender is treated as an
        # external faucet (keeps pre-Stage-9 tests, which never fund a
        # sender, working unchanged).
        amt = int(amount)
        if amt == 0:
            return
        s = str(sender)
        if self._bal.get(s, 0) >= amt:
            self._bal[s] = self._bal.get(s, 0) - amt
        self._bal[str(contract)] = self._bal.get(str(contract), 0) + amt

    def transfer(self, frm, to, amount):
        amt = int(amount)
        f = str(frm)
        if self._bal.get(f, 0) < amt:
            raise _UserError(
                f"insufficient balance for transfer: have {self._bal.get(f, 0)}, need {amt}"
            )
        self._bal[f] = self._bal.get(f, 0) - amt
        self._bal[str(to)] = self._bal.get(str(to), 0) + amt


_CHAIN = _MockChain()
_MSG_STATE = {"explicit": False}


class _AccountHandle:
    """Return of gl.get_contract_at(addr) -- balance + emit_transfer only."""

    def __init__(self, addr):
        self._addr = str(addr)

    @property
    def balance(self):
        return u256(_CHAIN.balance_of(self._addr))

    def emit_transfer(self, value, on="finalized"):
        _CHAIN.transfer(_CHAIN.current_contract, self._addr, int(value))


class _VMNamespace:
    UserError = _UserError


class _PublicNamespace:
    @staticmethod
    def view(fn):
        return fn

    class _WriteDecorator:
        def __call__(self, fn):
            return fn

        @staticmethod
        def payable(fn):
            def _wrapped(self, *a, **kw):
                gl = sys.modules["genlayer"].gl
                # A payable call moves value from the sender to the contract.
                _CHAIN.deposit_from(
                    gl.message.sender_address, _CHAIN.current_contract,
                    int(gl.message.value),
                )
                return fn(self, *a, **kw)

            _wrapped.__name__ = getattr(fn, "__name__", "payable_method")
            return _wrapped

    write = _WriteDecorator()


class RenderFailure(Exception):
    """Local stand-in for a gl.nondet.web.render failure (e.g. what a live
    WEBPAGE_LOAD_FAILED / Undetermined would look like from the caller's
    side: the leader function never returns, the whole transaction fails).
    LOCAL LOGIC TEST substitute only -- not live capability evidence.
    Stage 6a already supplies the live evidence for this failure mode.
    """
    pass


class _MockWebRegistry:
    """Deterministic, test-configured stand-in for gl.nondet.web.render.

    LOCAL LOGIC TEST infrastructure only. Exercises the contract's
    deterministic storage/fingerprint/lifecycle logic around a render
    call. Does NOT exercise, simulate, or prove anything about live
    render() behavior, consensus, or Undetermined handling -- that is
    Stage 6a's exclusive domain (see
    docs/STAGE_6A_WEB_RENDER_PROBE_REPORT.md).
    """

    def __init__(self):
        self._responses = {}  # url -> str content
        self._failures = set()  # urls that raise RenderFailure

    def set_response(self, url, content):
        self._responses[url] = content
        self._failures.discard(url)

    def set_failure(self, url):
        self._failures.add(url)
        self._responses.pop(url, None)

    def reset(self):
        self._responses.clear()
        self._failures.clear()

    def render(self, url, mode="text", wait_after_loaded=None):
        if url in self._failures:
            raise RenderFailure(f"mock render failure for {url}")
        if url not in self._responses:
            raise RenderFailure(f"no mock response configured for {url}")
        return self._responses[url]


class _WebNamespace:
    def __init__(self, registry):
        self._registry = registry

    def render(self, url, mode="text", wait_after_loaded=None):
        return self._registry.render(url, mode=mode, wait_after_loaded=wait_after_loaded)


class SemanticUndetermined(Exception):
    """Local stand-in for a semantic-consensus Undetermined outcome
    (gl.eq_principle.prompt_comparative fails to converge). On the live
    runtime this surfaces as a transaction revert that commits zero state;
    here it is simply raised out of the nondet call so the contract's
    no-try/except discipline propagates it. LOCAL LOGIC TEST substitute
    only -- the isolated semantic probe supplies the live evidence.
    """
    pass


class _MockSemanticRegistry:
    """Deterministic, test-configured stand-in for gl.nondet.exec_prompt.

    LOCAL LOGIC TEST infrastructure only. Exercises the contract's
    deterministic prompt-assembly, strict-parse, verdict-aggregation and
    state-transition logic around a semantic call. Does NOT exercise,
    simulate, or prove anything about live exec_prompt / prompt_comparative
    behavior, consensus, Undetermined frequency, or response_format="json"
    return shape -- that is the isolated semantic probe's exclusive domain
    (see docs/STAGE_7_SEMANTIC_PROBE_RUNBOOK.md and its report).
    """

    def __init__(self):
        self._queue = []      # FIFO of explicit responses
        self._default = None  # used when the queue is empty
        self._undetermined = False
        self.calls = []       # prompts seen, in order

    def enqueue(self, resp):
        self._queue.append(resp)

    def set_default(self, resp):
        self._default = resp

    def set_undetermined(self, flag=True):
        self._undetermined = flag

    def reset(self):
        self._queue = []
        self._default = None
        self._undetermined = False
        self.calls = []

    def exec_prompt(self, prompt, response_format="text", image=None, images=None):
        self.calls.append(prompt)
        if self._undetermined:
            raise SemanticUndetermined("mock semantic consensus did not converge")
        if self._queue:
            resp = self._queue.pop(0)
        elif self._default is not None:
            resp = self._default
        else:
            raise RenderFailure("no mock semantic response configured")
        if response_format == "json":
            if isinstance(resp, str):
                return _json.loads(resp)
            return resp
        if isinstance(resp, (dict, list)):
            return _json.dumps(resp)
        return resp


class _NondetNamespace:
    def __init__(self, registry, semantic_registry):
        self.web = _WebNamespace(registry)
        self._semantic = semantic_registry

    def exec_prompt(self, prompt, response_format="text", image=None, images=None):
        return self._semantic.exec_prompt(
            prompt, response_format=response_format, image=image, images=images
        )


class _EqPrincipleNamespace:
    """LOCAL LOGIC TEST stand-in. strict_eq / prompt_comparative here just
    call the leader function directly -- there is no validator set, no
    rotation, no Undetermined outcome produced by this shim itself (a
    configured _MockSemanticRegistry may still raise SemanticUndetermined
    from inside the leader fn). Exists only to exercise the contract's
    deterministic handling of whatever the leader function returns or
    raises.
    """

    @staticmethod
    def strict_eq(leader_fn):
        return leader_fn()

    @staticmethod
    def prompt_comparative(leader_fn, principle):
        return leader_fn()


class _GLNamespace:
    def __init__(self):
        self.vm = _VMNamespace
        self.public = _PublicNamespace
        self.message = _MessageContext()
        self.message_raw = _MessageRawDict()
        self.Contract = _Contract
        self.mock_web = _MockWebRegistry()
        self.mock_semantic = _MockSemanticRegistry()
        self.nondet = _NondetNamespace(self.mock_web, self.mock_semantic)
        self.storage = _StorageNamespace
        self.eq_principle = _EqPrincipleNamespace()

    @staticmethod
    def get_contract_at(addr):
        return _AccountHandle(addr)


class _Contract:
    """Base class for storage-annotated contracts.

    Any `TreeMap`- or `DynArray`-typed class annotation is auto-initialised
    to an empty container on the instance before `__init__` runs. This
    matches the semantics assumed by the contract source: storage fields
    are addressable via `self.x[...]` without an explicit allocation in
    `__init__`.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __new__(cls, *args, **kwargs):
        instance = object.__new__(cls)
        anns = {}
        for kls in reversed(cls.__mro__):
            local = getattr(kls, "__annotations__", None)
            if local:
                anns.update(local)
        for name, ann in anns.items():
            if ann is TreeMap:
                setattr(instance, name, TreeMap())
            elif ann is DynArray:
                setattr(instance, name, DynArray())
        # Stage 9: fresh native-GEN ledger per contract instantiation.
        _CHAIN.reset()
        return instance

    @property
    def balance(self):
        return u256(_CHAIN.balance_of(_CHAIN.current_contract))


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------


def install():
    """Register the fake `genlayer` module and expose `gl`."""
    if "genlayer" in sys.modules:
        return sys.modules["genlayer"]
    mod = types.ModuleType("genlayer")
    gl = _GLNamespace()
    mod.gl = gl
    # Primitives
    for name in (
        "u8",
        "u16",
        "u32",
        "u64",
        "u128",
        "u256",
        "i8",
        "i16",
        "i32",
        "i64",
        "bigint",
        "Address",
        "TreeMap",
        "DynArray",
        "allow_storage",
    ):
        setattr(mod, name, globals()[name])
    sys.modules["genlayer"] = mod
    return mod


def reset_message_context():
    """Restore the message context to the default sender + zero value, and
    clear the explicit-value flag so payable-method autopay applies again."""
    gl = sys.modules["genlayer"].gl
    gl.message.sender_address = Address("0x" + "aa" * 20)
    gl.message.value = u256(0)
    _MSG_STATE["explicit"] = False


def set_sender(addr: str):
    gl = sys.modules["genlayer"].gl
    gl.message.sender_address = Address(addr)


# --- Stage 9: native-GEN test helpers (LOCAL LOGIC TESTS only) -----------

def set_value(v):
    """Explicitly set gl.message.value for the next lock_bond call."""
    gl = sys.modules["genlayer"].gl
    gl.message.value = u256(int(v))
    _MSG_STATE["explicit"] = True


def lock(contract, purpose, amount):
    """Lock a bond of `amount` GEN for `purpose` and return its id.
    LOCAL LOGIC TEST helper. Mirrors the real lock_bond -> consume flow."""
    gl = sys.modules["genlayer"].gl
    prev = gl.message.value
    gl.message.value = u256(int(amount))
    try:
        return contract.lock_bond(purpose)
    finally:
        gl.message.value = prev


_AUTOPAY_SPECS = None


def autopay_bonds(gf_module):
    """Monkeypatch create_fork / submit_root_envelope / challenge_verdict so
    that a call made with the PRE-Stage-9 argument count auto-locks the
    right bond and prepends its id. Tests that exercise bond behaviour
    pass an explicit bond_id (one extra leading arg) and bypass this.
    Idempotent."""
    global _AUTOPAY_SPECS
    C = gf_module.Contract
    specs = [
        ("create_fork", 12, gf_module.BOND_PURPOSE_FORK_CREATION, int(gf_module.FORK_CREATION_BOND)),
        ("submit_root_envelope", 14, gf_module.BOND_PURPOSE_ENVELOPE, int(gf_module.ENVELOPE_BOND)),
        ("challenge_verdict", 4, gf_module.BOND_PURPOSE_CHALLENGE, int(gf_module.CHALLENGE_BOND)),
    ]
    _AUTOPAY_SPECS = specs

    def make(name, oldn, purpose, amount):
        orig = getattr(C, "_gforig_" + name, None)
        if orig is None:
            orig = getattr(C, name)
            setattr(C, "_gforig_" + name, orig)

        def wrapped(self, *a, **kw):
            if len(a) == oldn and "bond_id" not in kw:
                bid = lock(self, purpose, amount)
                return orig(self, bid, *a, **kw)
            return orig(self, *a, **kw)

        wrapped.__name__ = name
        return wrapped

    for name, oldn, purpose, amount in specs:
        setattr(C, name, make(name, oldn, purpose, amount))


def fund(addr, amount):
    """Credit an address in the mock native-GEN ledger."""
    _CHAIN.fund(addr, amount)


def balance(addr):
    """Read an address's mock native-GEN balance."""
    return _CHAIN.balance_of(addr)


def contract_address():
    """The fixed address the mock chain uses for the contract under test."""
    return str(_CHAIN.current_contract)


def reset_chain():
    _CHAIN.reset()


def get_render_failure():
    """RenderFailure exception class -- raised by the mock web registry.
    LOCAL LOGIC TEST infrastructure only; see _MockWebRegistry docstring.
    """
    return RenderFailure


def get_mock_web():
    """The active gl.nondet.web mock registry for the installed genlayer
    module. Use set_response(url, content) / set_failure(url) / reset()
    to control fetch_evidence's behavior in local tests.
    """
    return sys.modules["genlayer"].gl.mock_web


def get_mock_semantic():
    """The active gl.nondet.exec_prompt mock registry. Use enqueue(resp) /
    set_default(resp) / set_undetermined(True) / reset() to control
    run_adjudication's behavior in local tests. LOCAL LOGIC TEST only.
    """
    return sys.modules["genlayer"].gl.mock_semantic


def get_semantic_undetermined():
    """SemanticUndetermined exception class -- raised by the mock semantic
    registry when set_undetermined(True). LOCAL LOGIC TEST infrastructure.
    """
    return SemanticUndetermined


def get_gl():
    return sys.modules["genlayer"].gl


def get_user_error():
    return _UserError
