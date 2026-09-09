"""Local test shim for the `genlayer` module.

Provides just enough of the runtime surface used by
`contracts/governance_fork.py` so its Stage 3 logic can be exercised in
plain CPython. This is a TEST-ONLY substitute: it does not implement
consensus, storage persistence, or any nondeterministic operation.

Install by calling `install()` before importing the contract module.
"""

from __future__ import annotations

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
            return fn

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


class _NondetNamespace:
    def __init__(self, registry):
        self.web = _WebNamespace(registry)


class _EqPrincipleNamespace:
    """LOCAL LOGIC TEST stand-in. strict_eq here just calls the leader
    function directly -- there is no validator set, no rotation, no
    Undetermined outcome in this shim. It exists only to exercise the
    contract's deterministic post-processing of whatever the leader
    function returns (or the failure path if it raises).
    """

    @staticmethod
    def strict_eq(leader_fn):
        return leader_fn()


class _GLNamespace:
    def __init__(self):
        self.vm = _VMNamespace
        self.public = _PublicNamespace
        self.message = _MessageContext()
        self.Contract = _Contract
        self.mock_web = _MockWebRegistry()
        self.nondet = _NondetNamespace(self.mock_web)
        self.eq_principle = _EqPrincipleNamespace()


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
        return instance


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
    """Restore the message context to the default sender + zero value."""
    gl = sys.modules["genlayer"].gl
    gl.message.sender_address = Address("0x" + "aa" * 20)
    gl.message.value = u256(0)


def set_sender(addr: str):
    gl = sys.modules["genlayer"].gl
    gl.message.sender_address = Address(addr)


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


def get_gl():
    return sys.modules["genlayer"].gl


def get_user_error():
    return _UserError
