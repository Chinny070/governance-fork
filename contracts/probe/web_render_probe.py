# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass

import hashlib


# =========================================================================
# Stage 6a -- isolated web-render capability probe.
#
# This contract is NOT part of Governance Fork's production contract. It
# exists to answer one question empirically:
#
#   "Can GenLayer's officially supported web-render flow reliably produce
#    useful, consensus-compatible textual evidence from the real governance
#    pages Governance Fork needs?"
#
# It probes gl.nondet.web.render(...) specifically (not gl.nondet.web.get),
# per explicit project direction, wrapped in gl.eq_principle.strict_eq per
# the current official Fetch Web Content example:
# https://docs.genlayer.com/developers/intelligent-contracts/examples/fetch-web-content
#
# PHASE A: this file establishes the probe contract shell and its schema
# only. No live transactions are issued from this session. No deployment.
# =========================================================================

MAX_PROBE_URL_LEN = 512
MAX_PROBE_SLICE = 16384
MAX_PROBE_PREVIEW = 256
PAGINATION_LIMIT_MAX = 50

MODE_TEXT = "text"
MODE_HTML = "html"

URL_CLASS_SNAPSHOT_PROPOSAL = "SNAPSHOT_PROPOSAL"
URL_CLASS_TALLY_PROPOSAL = "TALLY_PROPOSAL"
URL_CLASS_DAO_FORUM = "DAO_FORUM"
URL_CLASS_OFFICIAL_DOCS = "OFFICIAL_DOCS"
URL_CLASS_TREASURY_REPORT = "TREASURY_REPORT"
URL_CLASS_OTHER = "OTHER"

_ALLOWED_URL_CLASSES = (
    URL_CLASS_SNAPSHOT_PROPOSAL,
    URL_CLASS_TALLY_PROPOSAL,
    URL_CLASS_DAO_FORUM,
    URL_CLASS_OFFICIAL_DOCS,
    URL_CLASS_TREASURY_REPORT,
    URL_CLASS_OTHER,
)


@allow_storage
@dataclass
class ProbeResult:
    url: str
    url_class: str
    mode: str
    wait_after_loaded: str
    content_length: u32
    content_fingerprint: bytes
    content_preview: str
    submitted_at: u256


class Contract(gl.Contract):
    probes: TreeMap[u256, ProbeResult]
    probe_order: DynArray[u256]
    next_probe_id: u256

    def __init__(self):
        self.next_probe_id = u256(1)

    @gl.public.write
    def run_probe(
        self,
        url: str,
        url_class: str,
        mode: str,
        wait_after_loaded: str,
    ) -> u256:
        # Deterministic input validation happens BEFORE any nondet call.
        if len(url) < 1 or len(url) > MAX_PROBE_URL_LEN:
            raise gl.vm.UserError("url length out of bounds")
        if "\n" in url or "\r" in url:
            raise gl.vm.UserError("newline forbidden in url")
        lowered = url.lower()
        if not (lowered.startswith("http://") or lowered.startswith("https://")):
            raise gl.vm.UserError("url must use http:// or https://")
        if mode != MODE_TEXT and mode != MODE_HTML:
            raise gl.vm.UserError("mode must be text or html")
        class_ok = False
        for c in _ALLOWED_URL_CLASSES:
            if url_class == c:
                class_ok = True
        if not class_ok:
            raise gl.vm.UserError("url_class out of range")
        if len(wait_after_loaded) > 16:
            raise gl.vm.UserError("wait_after_loaded too long")

        # Two minimal leader functions, chosen deterministically BEFORE
        # entering the nondet block. No branching inside the leader
        # function itself -- this matches the shape of the official
        # documented example as closely as possible.
        def fetch_text_no_wait() -> str:
            return gl.nondet.web.render(url, mode=MODE_TEXT)

        def fetch_text_with_wait() -> str:
            return gl.nondet.web.render(url, mode=MODE_TEXT, wait_after_loaded=wait_after_loaded)

        def fetch_html_no_wait() -> str:
            return gl.nondet.web.render(url, mode=MODE_HTML)

        def fetch_html_with_wait() -> str:
            return gl.nondet.web.render(url, mode=MODE_HTML, wait_after_loaded=wait_after_loaded)

        has_wait = len(wait_after_loaded) > 0

        if mode == MODE_TEXT:
            if has_wait:
                content = gl.eq_principle.strict_eq(fetch_text_with_wait)
            else:
                content = gl.eq_principle.strict_eq(fetch_text_no_wait)
        else:
            if has_wait:
                content = gl.eq_principle.strict_eq(fetch_html_with_wait)
            else:
                content = gl.eq_principle.strict_eq(fetch_html_no_wait)

        # Everything below this line is deterministic post-processing of an
        # already-consensus-agreed string. No further nondet calls.
        sliced = content[:MAX_PROBE_SLICE]
        fp = hashlib.sha256(sliced.encode("utf-8")).digest()
        preview = sliced[:MAX_PROBE_PREVIEW]

        probe_id = self.next_probe_id
        self.next_probe_id = u256(int(probe_id) + 1)
        self.probes[probe_id] = ProbeResult(
            url=url,
            url_class=url_class,
            mode=mode,
            wait_after_loaded=wait_after_loaded,
            content_length=u32(len(sliced)),
            content_fingerprint=fp,
            content_preview=preview,
            submitted_at=u256(0),
        )
        self.probe_order.append(probe_id)
        return probe_id

    @gl.public.view
    def get_probe(self, probe_id: u256) -> ProbeResult:
        if probe_id not in self.probes:
            raise gl.vm.UserError("probe not found")
        return self.probes[probe_id]

    @gl.public.view
    def list_probes(self, cursor: u256, limit: u32) -> DynArray[u256]:
        limit_int = int(limit)
        if limit_int <= 0:
            limit_int = 1
        if limit_int > PAGINATION_LIMIT_MAX:
            limit_int = PAGINATION_LIMIT_MAX
        start = int(cursor)
        n = len(self.probe_order)
        if start < 0 or start >= n:
            return DynArray[u256]()
        end = start + limit_int
        if end > n:
            end = n
        out = DynArray[u256]()
        i = start
        while i < end:
            out.append(self.probe_order[i])
            i = i + 1
        return out

    @gl.public.view
    def get_probe_count(self) -> u256:
        return u256(len(self.probe_order))
