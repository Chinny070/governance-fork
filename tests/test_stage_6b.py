"""Stage 6b tests for governance_fork.py.

LOCAL LOGIC TESTS ONLY. These exercise the contract's deterministic
storage, fingerprint, and lifecycle logic around evidence retrieval using
a mocked gl.nondet.web.render (see tests/_genlayer_shim.py's
_MockWebRegistry). They do NOT exercise, simulate, or prove anything
about live render() behavior, consensus, or Undetermined handling --
that is Stage 6a's exclusive domain
(docs/STAGE_6A_WEB_RENDER_PROBE_REPORT.md), and its live evidence is not
re-derived or re-claimed here.
"""

from __future__ import annotations

import hashlib
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_ROOT, "contracts"))

import _genlayer_shim as shim  # noqa: E402

shim.install()

import governance_fork as gf  # noqa: E402


UserError = shim.get_user_error()
RenderFailure = shim.get_render_failure()


def _params(pairs):
    return shim.DynArray([gf.ParamKV(key=k, value=v) for k, v in pairs])


def _delta(entries):
    return shim.DynArray([
        gf.DeltaEntry(dimension_name=n, parent_value=pv, fork_value=fv, claim_kind=ck)
        for (n, ck, pv, fv) in entries
    ])


def _envelope(mutable=("allocation", "duration"), immutable=("beneficiary_class",)):
    return gf.IntentEnvelope(
        objective="Fund ecosystem developer work.",
        beneficiary_class="Developers",
        resource_type=gf.RESOURCE_TREASURY,
        scope="ecosystem-wide",
        essential_constraints=shim.DynArray(["must be for developer work"]),
        mutable_dimensions=shim.DynArray(list(mutable)),
        immutable_dimensions=shim.DynArray(list(immutable)),
        parent_proposal_fingerprint=b"",
        envelope_version=shim.u32(0),
    )


def _body(title="Fork A", params=(("allocation", "50000"), ("duration", "6 months"))):
    return gf.ForkBody(
        title=title, summary="", structured_parameters=_params(params), reasoning="",
    )


def _params_kv(pairs):
    """ABI-compatibility replacement for _params(): returns the parallel
    (keys, values) arrays import_root_proposal now takes directly.
    """
    return (
        shim.DynArray([k for k, v in pairs]),
        shim.DynArray([v for k, v in pairs]),
    )


def _delta_fields(entries):
    """ABI-compatibility replacement for _delta(): returns the four
    parallel arrays create_fork now takes directly, instead of a single
    DynArray[DeltaEntry].
    """
    return (
        shim.DynArray([n for (n, ck, pv, fv) in entries]),
        shim.DynArray([pv for (n, ck, pv, fv) in entries]),
        shim.DynArray([fv for (n, ck, pv, fv) in entries]),
        shim.DynArray([ck for (n, ck, pv, fv) in entries]),
    )


def _envelope_fields(mutable=("allocation", "duration"), immutable=("beneficiary_class",)):
    """ABI-compatibility replacement for _envelope(): returns the flattened
    positional arguments submit_root_envelope now takes directly.
    """
    return (
        "Fund ecosystem developer work.",
        "Developers",
        gf.RESOURCE_TREASURY,
        "ecosystem-wide",
        shim.DynArray(["must be for developer work"]),
        shim.DynArray(list(mutable)),
        shim.DynArray(list(immutable)),
    )


def _body_fields(title="Fork A", params=(("allocation", "50000"), ("duration", "6 months"))):
    """ABI-compatibility replacement for _body(): returns the flattened
    positional arguments create_fork now takes directly for the body.
    """
    keys, values = _params_kv(params)
    return (title, "", keys, values, "")


def _evidence_arrays(urls, classes=None, rel=None, auth=None, tm=None, profiles=None):
    n = len(urls)
    if classes is None:
        classes = [gf.EC_OFFICIAL_GOVERNANCE] * n
    if rel is None:
        rel = ["r"] * n
    if auth is None:
        auth = ["a"] * n
    if tm is None:
        tm = ["t"] * n
    if profiles is None:
        profiles = [gf.RENDER_PROFILE_STANDARD] * n
    return (
        shim.DynArray(list(urls)),
        shim.DynArray(list(classes)),
        shim.DynArray(list(rel)),
        shim.DynArray(list(auth)),
        shim.DynArray(list(tm)),
        shim.DynArray(list(profiles)),
    )


def _fresh():
    shim.reset_message_context()
    shim.get_mock_web().reset()
    return gf.Contract()


def _fresh_root_case(urls=("https://x/1",), profiles=None, mutable=("allocation",),
                     immutable=("beneficiary_class",)):
    """DAO + root + submitted envelope -> ROOT_ENVELOPE case in CASE_OPEN,
    owned by the default sender (root.proposer).
    """
    c = _fresh()
    did = c.register_dao("A", "https://a")
    rid = c.import_root_proposal(
        did, "EP", "T", "https://x/1", *_params_kv([("allocation", "100000")]),
    )
    args = _evidence_arrays(urls, profiles=profiles)
    case_id = c.submit_root_envelope(rid, *_envelope_fields(mutable=mutable, immutable=immutable), *args)
    return c, did, rid, case_id


def _fresh_fork_case(urls=("https://a.example.com/1",), profiles=None):
    """DAO + FAITHFUL root (test-harness flip) + fork + one evidence
    submission -> FORK case in CASE_OPEN, owned by the fork creator.
    """
    c = _fresh()
    did = c.register_dao("A", "https://a")
    rid = c.import_root_proposal(
        did, "EP", "T", "https://x/1",
        *_params_kv([("allocation", "100000"), ("duration", "6 months")]),
    )
    args = _evidence_arrays(("https://gov.example.com/root-evidence",))
    c.submit_root_envelope(rid, *_envelope_fields(), *args)
    r = c.get_root_proposal(rid)
    r.envelope_status = gf.ENVELOPE_FAITHFUL  # test-harness flip only
    c.roots[rid] = r
    creator = shim.Address("0x" + "cc" * 20)
    shim.set_sender(creator)
    fid = c.create_fork(
        rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
        *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
        *_body_fields(),
    )
    fork_args = _evidence_arrays(urls, profiles=profiles)
    case_id = c.submit_fork_evidence(fid, *fork_args)
    return c, did, rid, fid, case_id, creator


# ============================================================================
# close_evidence
# ============================================================================


class CloseEvidenceTests(unittest.TestCase):
    def test_close_with_zero_evidence_rejected(self):
        # Not directly reachable via the public ABI (submission requires
        # >=1 evidence), but close_evidence's own defensive check is
        # exercised via a case manufactured with empty membership.
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", *_params_kv([]))
        case_id = c.next_case_id
        c.cases[case_id] = gf.Case(
            case_type=gf.CASE_TYPE_ROOT_ENVELOPE, target_id=rid,
            target_kind=gf.TARGET_KIND_ROOT_ENVELOPE, target_fingerprint=b"",
            evidence_ids=shim.DynArray([]), membership_fingerprint=b"",
            retrieval_disposition_fingerprint=b"",
            evidence_set_fingerprint=b"", adjudication_dimensions_version=shim.u32(1),
            case_fingerprint=b"", state=gf.CASE_OPEN, retry_count=shim.u32(0),
            last_attempt_at=shim.u256(0), verdict_id=shim.u256(0),
        )
        with self.assertRaises(UserError):
            c.close_evidence(case_id)

    def test_close_fixes_membership(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1", "https://x/2"))
        c.close_evidence(case_id)
        case = c.get_case(case_id)
        self.assertEqual(case.state, gf.CASE_EVIDENCE_CLOSED)
        self.assertNotEqual(case.membership_fingerprint, b"")

    def test_no_evidence_additions_after_close(self):
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        c.close_evidence(case_id)
        shim.set_sender(creator)
        args = _evidence_arrays(("https://a.example.com/late",))
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *args)

    def test_close_twice_rejected(self):
        c, did, rid, case_id = _fresh_root_case()
        c.close_evidence(case_id)
        with self.assertRaises(UserError):
            c.close_evidence(case_id)

    def test_close_unknown_case_rejected(self):
        c = _fresh()
        with self.assertRaises(UserError):
            c.close_evidence(shim.u256(999))

    def test_close_authorization_root_envelope(self):
        c, did, rid, case_id = _fresh_root_case()
        shim.set_sender("0x" + "ee" * 20)  # not root.proposer
        with self.assertRaises(UserError):
            c.close_evidence(case_id)

    def test_close_authorization_fork(self):
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender("0x" + "ee" * 20)  # not fork.creator
        with self.assertRaises(UserError):
            c.close_evidence(case_id)

    def test_close_paused_rejected(self):
        c, did, rid, case_id = _fresh_root_case()
        shim.set_sender("0x" + "aa" * 20)
        c.pause()
        with self.assertRaises(UserError):
            c.close_evidence(case_id)


# ============================================================================
# fetch_evidence
# ============================================================================


class FetchEvidenceTests(unittest.TestCase):
    def test_fetch_before_close_rejected(self):
        c, did, rid, case_id = _fresh_root_case()
        eid = list(c.evidence_by_case[case_id])[0]
        with self.assertRaises(UserError):
            c.fetch_evidence(eid)

    def test_fetch_unknown_evidence_rejected(self):
        c = _fresh()
        with self.assertRaises(UserError):
            c.fetch_evidence(shim.u256(999))

    def test_successful_fetch_freezes_exact_content(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "A" * 100)
        c.fetch_evidence(eid)
        ev = c.get_evidence(eid)
        self.assertEqual(ev.retrieval_status, gf.RETRIEVAL_FETCHED)
        self.assertEqual(ev.frozen_content, "A" * 100)
        self.assertTrue(ev.frozen)

    def test_fingerprint_matches_stored_content(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "hello world content here")
        c.fetch_evidence(eid)
        ev = c.get_evidence(eid)
        expected = hashlib.sha256(ev.frozen_content.encode("utf-8")).digest()
        self.assertEqual(ev.content_fingerprint, expected)

    def test_successful_fetch_cannot_be_overwritten(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        mock = shim.get_mock_web()
        mock.set_response("https://x/1", "first content")
        c.fetch_evidence(eid)
        mock.set_response("https://x/1", "second different content")
        with self.assertRaises(UserError):
            c.fetch_evidence(eid)
        ev = c.get_evidence(eid)
        self.assertEqual(ev.frozen_content, "first content")

    def test_failed_fetch_leaves_record_unfetched(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_failure("https://x/1")
        with self.assertRaises(RenderFailure):
            c.fetch_evidence(eid)
        ev = c.get_evidence(eid)
        self.assertEqual(ev.retrieval_status, gf.RETRIEVAL_NOT_FETCHED)
        self.assertFalse(ev.frozen)
        self.assertEqual(ev.content_fingerprint, b"")

    def test_failed_fetch_can_be_retried(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        mock = shim.get_mock_web()
        mock.set_failure("https://x/1")
        with self.assertRaises(RenderFailure):
            c.fetch_evidence(eid)
        mock.set_response("https://x/1", "now it works, long enough content")
        c.fetch_evidence(eid)
        ev = c.get_evidence(eid)
        self.assertEqual(ev.retrieval_status, gf.RETRIEVAL_FETCHED)

    def test_empty_render_commits_unusable_short(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "")
        c.fetch_evidence(eid)
        ev = c.get_evidence(eid)
        self.assertEqual(ev.retrieval_status, gf.RETRIEVAL_UNUSABLE_SHORT)
        self.assertTrue(ev.frozen)  # resolved, just not useful
        self.assertEqual(
            ev.content_fingerprint,
            hashlib.sha256(b"").digest(),
        )

    def test_below_min_length_commits_unusable_short(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        short = "x" * (gf.MIN_USEFUL_CONTENT_LEN - 1)
        shim.get_mock_web().set_response("https://x/1", short)
        c.fetch_evidence(eid)
        self.assertEqual(c.get_evidence(eid).retrieval_status, gf.RETRIEVAL_UNUSABLE_SHORT)

    def test_at_min_length_commits_fetched(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        exact = "x" * gf.MIN_USEFUL_CONTENT_LEN
        shim.get_mock_web().set_response("https://x/1", exact)
        c.fetch_evidence(eid)
        self.assertEqual(c.get_evidence(eid).retrieval_status, gf.RETRIEVAL_FETCHED)

    def test_content_sliced_to_max_evidence_slice(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        huge = "y" * (gf.MAX_EVIDENCE_SLICE + 500)
        shim.get_mock_web().set_response("https://x/1", huge)
        c.fetch_evidence(eid)
        ev = c.get_evidence(eid)
        self.assertEqual(len(ev.frozen_content), gf.MAX_EVIDENCE_SLICE)

    def test_fetch_evidence_from_another_case_cannot_contaminate(self):
        c, did, rid, case_id_a = _fresh_root_case(urls=("https://x/1",))
        did2 = c.register_dao("B", "https://b")
        rid2 = c.import_root_proposal(did2, "EP2", "T2", "https://y/1", *_params_kv([]))
        args = _evidence_arrays(("https://y/1",))
        case_id_b = c.submit_root_envelope(rid2, *_envelope_fields(), *args)
        c.close_evidence(case_id_a)
        c.close_evidence(case_id_b)
        eid_a = list(c.evidence_by_case[case_id_a])[0]
        eid_b = list(c.evidence_by_case[case_id_b])[0]
        shim.get_mock_web().set_response("https://x/1", "content for case A only, long enough")
        shim.get_mock_web().set_response("https://y/1", "content for case B only, long enough")
        c.fetch_evidence(eid_a)
        ev_a = c.get_evidence(eid_a)
        ev_b = c.get_evidence(eid_b)
        self.assertEqual(ev_a.retrieval_status, gf.RETRIEVAL_FETCHED)
        self.assertEqual(ev_b.retrieval_status, gf.RETRIEVAL_NOT_FETCHED)
        self.assertEqual(ev_b.frozen_content, "")

    def test_fetch_permissionless_and_not_paused_gated(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.set_sender("0x" + "ff" * 20)  # arbitrary caller, not owner
        shim.get_mock_web().set_response("https://x/1", "permissionless fetch content ok long enough")
        shim.set_sender("0x" + "aa" * 20)
        c.pause()
        shim.set_sender("0x" + "ff" * 20)
        c.fetch_evidence(eid)  # must succeed despite pause and non-owner caller
        self.assertEqual(c.get_evidence(eid).retrieval_status, gf.RETRIEVAL_FETCHED)

    def test_dynamic_profile_does_not_change_committable_semantics(self):
        # LOCAL LOGIC TEST: the mock does not simulate wait timing at all;
        # it only confirms that RENDER_PROFILE_DYNAMIC routes through the
        # same deterministic post-processing path as STANDARD.
        c, did, rid, case_id = _fresh_root_case(
            urls=("https://x/1",), profiles=(gf.RENDER_PROFILE_DYNAMIC,),
        )
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "dynamic profile content long enough")
        c.fetch_evidence(eid)
        self.assertEqual(c.get_evidence(eid).retrieval_status, gf.RETRIEVAL_FETCHED)


# ============================================================================
# seal_evidence
# ============================================================================


class SealEvidenceTests(unittest.TestCase):
    def _closed_two_item_case(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1", "https://x/2"))
        c.close_evidence(case_id)
        return c, did, rid, case_id

    def test_seal_before_close_rejected(self):
        c, did, rid, case_id = _fresh_root_case()
        with self.assertRaises(UserError):
            c.seal_evidence(case_id)

    def test_seal_before_all_fetched_rejected(self):
        # ROOT_ENVELOPE case: every item is in the required lane (no
        # community concept for root evidence), so a still-NOT_FETCHED
        # member blocks seal exactly like a FORK creator item would.
        c, did, rid, case_id = self._closed_two_item_case()
        eids = list(c.evidence_by_case[case_id])
        shim.get_mock_web().set_response("https://x/1", "only first item fetched here")
        c.fetch_evidence(eids[0])
        with self.assertRaises(UserError):
            c.seal_evidence(case_id)

    def test_root_envelope_seal_rejects_when_required_evidence_unusable_short(self):
        # Stage 6b correction: for ROOT_ENVELOPE cases (uniformly
        # required lane), RETRIEVAL_UNUSABLE_SHORT does NOT satisfy the
        # requirement -- only RETRIEVAL_FETCHED does. A resolved-but-
        # useless required item still blocks seal.
        c, did, rid, case_id = self._closed_two_item_case()
        eids = list(c.evidence_by_case[case_id])
        shim.get_mock_web().set_response("https://x/1", "usable content that is definitely long enough here")
        shim.get_mock_web().set_response("https://x/2", "")  # resolves, but unusable
        c.fetch_evidence(eids[0])
        c.fetch_evidence(eids[1])
        with self.assertRaises(UserError) as ctx:
            c.seal_evidence(case_id)
        self.assertIn("required evidence not fetched", str(ctx.exception))
        self.assertEqual(c.get_case(case_id).state, gf.CASE_EVIDENCE_CLOSED)

    def test_root_envelope_seal_succeeds_when_all_required_fetched(self):
        c, did, rid, case_id = self._closed_two_item_case()
        eids = list(c.evidence_by_case[case_id])
        shim.get_mock_web().set_response("https://x/1", "first required item content long enough here")
        shim.get_mock_web().set_response("https://x/2", "second required item content long enough here")
        c.fetch_evidence(eids[0])
        c.fetch_evidence(eids[1])
        c.seal_evidence(case_id)
        self.assertEqual(c.get_case(case_id).state, gf.CASE_CASE_FROZEN)

    def test_fork_seal_succeeds_with_unresolved_community_evidence(self):
        # THE core correction: community (non-required) evidence stuck at
        # NOT_FETCHED forever does not block seal, as long as every
        # creator (required) item is RETRIEVAL_FETCHED.
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        args = _evidence_arrays(("https://community.example.com/never-fetched",))
        c.submit_fork_evidence(fid, *args)
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        mock = shim.get_mock_web()
        for eid in eids:
            ev = c.get_evidence(eid)
            if ev.submitter == creator:
                mock.set_response(ev.url, "creator content that is long enough to be useful")
                c.fetch_evidence(eid)
            # community item deliberately never fetched -- no mock
            # response configured, left permanently NOT_FETCHED.
        c.seal_evidence(case_id)  # must NOT raise
        case = c.get_case(case_id)
        self.assertEqual(case.state, gf.CASE_CASE_FROZEN)
        community_eid = [e for e in eids if c.get_evidence(e).submitter != creator][0]
        self.assertEqual(c.get_evidence(community_eid).retrieval_status, gf.RETRIEVAL_NOT_FETCHED)

    def test_fork_seal_succeeds_with_unusable_short_community_evidence(self):
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        args = _evidence_arrays(("https://community.example.com/weak",))
        c.submit_fork_evidence(fid, *args)
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        mock = shim.get_mock_web()
        for eid in eids:
            ev = c.get_evidence(eid)
            if ev.submitter == creator:
                mock.set_response(ev.url, "creator content that is long enough to be useful")
            else:
                mock.set_response(ev.url, "")  # resolves, unusable
            c.fetch_evidence(eid)
        c.seal_evidence(case_id)  # must NOT raise -- unusable community is non-blocking too
        self.assertEqual(c.get_case(case_id).state, gf.CASE_CASE_FROZEN)

    def test_fork_seal_rejects_when_creator_evidence_unusable_short(self):
        # Required lane (creator) still enforces RETRIEVAL_FETCHED, not
        # merely "resolved" -- symmetric with the ROOT_ENVELOPE rule.
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response(c.get_evidence(eid).url, "")  # unusable
        c.fetch_evidence(eid)
        with self.assertRaises(UserError):
            c.seal_evidence(case_id)

    def test_community_success_cannot_substitute_for_creator_requirement(self):
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        args = _evidence_arrays(("https://community.example.com/good",))
        c.submit_fork_evidence(fid, *args)
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        mock = shim.get_mock_web()
        for eid in eids:
            ev = c.get_evidence(eid)
            if ev.submitter != creator:
                mock.set_response(ev.url, "community content long enough to be fetched fine")
                c.fetch_evidence(eid)
            # creator's own item deliberately left NOT_FETCHED
        with self.assertRaises(UserError) as ctx:
            c.seal_evidence(case_id)
        self.assertIn("required evidence not fetched", str(ctx.exception))

    def test_theoretical_max_frozen_storage_is_bounded_without_a_cap(self):
        # Stage 6b correction removed the seal-blocking total-content cap.
        # The worst case remains finite and bounded by the pre-existing
        # caps alone: MAX_EVIDENCE_PER_CASE * MAX_EVIDENCE_SLICE.
        worst_case = gf.MAX_EVIDENCE_PER_CASE * gf.MAX_EVIDENCE_SLICE
        self.assertEqual(worst_case, 16 * 16384)
        self.assertEqual(worst_case, 262144)
        self.assertFalse(hasattr(gf, "MAX_FROZEN_CONTENT_PER_CASE"))

    def test_large_immutable_fetches_never_prevent_seal(self):
        # Adversarial-shaped check: even after committing several
        # maximally-sized evidence items (well past the old removed
        # cap), seal still succeeds -- no order-dependent, immutable-
        # content-triggered seal failure is possible any more.
        urls = tuple(f"https://x/{i}" for i in range(5))
        c, did, rid, case_id = _fresh_root_case(urls=urls)
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        mock = shim.get_mock_web()
        for i, eid in enumerate(eids):
            mock.set_response(urls[i], "z" * gf.MAX_EVIDENCE_SLICE)
            c.fetch_evidence(eid)
        c.seal_evidence(case_id)  # must not raise despite 5 * 16384 content
        self.assertEqual(c.get_case(case_id).state, gf.CASE_CASE_FROZEN)

    def test_seal_computes_deterministic_final_fingerprints(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "deterministic content for fp check")
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        case = c.get_case(case_id)
        self.assertNotEqual(case.evidence_set_fingerprint, b"")
        self.assertNotEqual(case.case_fingerprint, b"")

    def test_seal_cannot_repeat(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "content for repeat-seal check test")
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        with self.assertRaises(UserError):
            c.seal_evidence(case_id)

    def test_no_partial_final_freeze_on_reject(self):
        c, did, rid, case_id = self._closed_two_item_case()
        eids = list(c.evidence_by_case[case_id])
        shim.get_mock_web().set_response("https://x/1", "only one of two items fetched")
        c.fetch_evidence(eids[0])
        with self.assertRaises(UserError):
            c.seal_evidence(case_id)
        case = c.get_case(case_id)
        self.assertEqual(case.state, gf.CASE_EVIDENCE_CLOSED)  # unchanged
        self.assertEqual(case.evidence_set_fingerprint, b"")
        self.assertEqual(case.case_fingerprint, b"")

    def test_target_fingerprint_unchanged_by_seal(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        before = c.get_case(case_id).target_fingerprint
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "content for target fp check test")
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        after = c.get_case(case_id).target_fingerprint
        self.assertEqual(before, after)

    def test_seal_permissionless_and_not_paused_gated(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "content for permissionless seal test")
        c.fetch_evidence(eid)
        shim.set_sender("0x" + "aa" * 20)
        c.pause()
        shim.set_sender("0x" + "ff" * 20)  # arbitrary caller
        c.seal_evidence(case_id)  # must succeed despite pause and non-owner
        self.assertEqual(c.get_case(case_id).state, gf.CASE_CASE_FROZEN)


# ============================================================================
# abort_case
# ============================================================================


class AbortCaseTests(unittest.TestCase):
    def test_abort_open_case_rejected(self):
        c, did, rid, case_id = _fresh_root_case()
        with self.assertRaises(UserError):
            c.abort_case(case_id)

    def test_abort_closed_case_succeeds(self):
        c, did, rid, case_id = _fresh_root_case()
        c.close_evidence(case_id)
        c.abort_case(case_id)
        self.assertEqual(c.get_case(case_id).state, gf.CASE_ABORTED)

    def test_abort_frozen_case_rejected(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "content so we can seal then abort")
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        with self.assertRaises(UserError):
            c.abort_case(case_id)

    def test_abort_authorization(self):
        c, did, rid, case_id = _fresh_root_case()
        c.close_evidence(case_id)
        shim.set_sender("0x" + "ee" * 20)
        with self.assertRaises(UserError):
            c.abort_case(case_id)

    def test_abort_recovers_from_permanently_unavailable_evidence(self):
        # The griefing scenario: a member URL always fails to fetch, so
        # the case can never seal. abort_case is the explicit, auditable
        # escape valve -- nothing is silently dropped; the evidence
        # record itself remains readable at RETRIEVAL_NOT_FETCHED forever.
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_failure("https://x/1")
        with self.assertRaises(RenderFailure):
            c.fetch_evidence(eid)
        c.abort_case(case_id)
        self.assertEqual(c.get_case(case_id).state, gf.CASE_ABORTED)
        # Evidence record is untouched, auditable, not deleted.
        ev = c.get_evidence(eid)
        self.assertEqual(ev.retrieval_status, gf.RETRIEVAL_NOT_FETCHED)

    def test_abort_paused_rejected(self):
        c, did, rid, case_id = _fresh_root_case()
        c.close_evidence(case_id)
        shim.set_sender("0x" + "aa" * 20)
        c.pause()
        with self.assertRaises(UserError):
            c.abort_case(case_id)

    def test_aborted_case_remains_fully_queryable(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1", "https://x/2"))
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        shim.get_mock_web().set_response("https://x/1", "one item fetched before abort here")
        c.fetch_evidence(eids[0])
        c.abort_case(case_id)
        # The case itself is still readable, with its true final state.
        case = c.get_case(case_id)
        self.assertEqual(case.state, gf.CASE_ABORTED)
        self.assertEqual(len(case.evidence_ids), 2)
        # Every evidence record -- fetched or not -- remains readable.
        ev0 = c.get_evidence(eids[0])
        ev1 = c.get_evidence(eids[1])
        self.assertEqual(ev0.retrieval_status, gf.RETRIEVAL_FETCHED)
        self.assertEqual(ev0.frozen_content, "one item fetched before abort here")
        self.assertEqual(ev1.retrieval_status, gf.RETRIEVAL_NOT_FETCHED)
        page = c.list_evidence_of_case(case_id, shim.u256(0), shim.u32(50))
        self.assertEqual(set(int(e) for e in page.items), set(int(e) for e in eids))

    def test_abort_does_not_delete_or_mutate_any_state(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        before = c.get_evidence(eid)
        before_membership_fp = c.get_case(case_id).membership_fingerprint
        c.abort_case(case_id)
        after = c.get_evidence(eid)
        after_case = c.get_case(case_id)
        self.assertEqual(before.url, after.url)
        self.assertEqual(before.submitter, after.submitter)
        self.assertEqual(before.retrieval_status, after.retrieval_status)
        self.assertEqual(before_membership_fp, after_case.membership_fingerprint)
        # Only state actually changes.
        self.assertEqual(after_case.state, gf.CASE_ABORTED)

    def test_aborted_case_cannot_adjudicate(self):
        c, did, rid, case_id = _fresh_root_case()
        c.close_evidence(case_id)
        c.abort_case(case_id)
        with self.assertRaises(UserError):
            c.adjudicate(case_id)

    def test_no_fresh_case_recovery_path_in_v1(self):
        # Documented, deliberate V1 limitation (see
        # docs/STAGE_6B_PRODUCTION_EVIDENCE_FREEZE.md "abort/retry
        # semantics"): once a fork's evidence case is aborted, there is
        # no contract path to open a second, fresh case for the SAME
        # fork -- fork.evidence_case_id still points at the aborted case,
        # and submit_fork_evidence's only two entry states (FORK_DRAFT
        # for first-time creation, FORK_EVIDENCE_OPEN for reuse) both
        # resolve back to that same aborted case, whose CASE_OPEN gate
        # in submit_fork_evidence now rejects further submissions.
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        c.close_evidence(case_id)
        c.abort_case(case_id)
        self.assertEqual(int(c.get_fork(fid).evidence_case_id), int(case_id))
        shim.set_sender(creator)
        args = _evidence_arrays(("https://a.example.com/fresh-attempt",))
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *args)

    def test_no_id_reuse_across_cases(self):
        c, did, rid, case_id_a = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id_a)
        c.abort_case(case_id_a)
        did2 = c.register_dao("B", "https://b")
        rid2 = c.import_root_proposal(did2, "EP2", "T2", "https://y/1", *_params_kv([]))
        args = _evidence_arrays(("https://y/1",))
        case_id_b = c.submit_root_envelope(rid2, *_envelope_fields(), *args)
        self.assertNotEqual(int(case_id_a), int(case_id_b))
        self.assertGreater(int(case_id_b), int(case_id_a))


# ============================================================================
# Community-griefing scenarios (fork cases)
# ============================================================================


class CommunityGriefingTests(unittest.TestCase):
    def test_unavailable_community_evidence_does_not_block_seal(self):
        # THE fix for the critical defect: a community contributor's
        # permanently-unfetchable URL can no longer block sealing at all
        # -- no abort_case is needed for this scenario any more.
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        args = _evidence_arrays(("https://community.example.com/1",))
        c.submit_fork_evidence(fid, *args)
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        mock = shim.get_mock_web()
        for eid in eids:
            ev = c.get_evidence(eid)
            if ev.submitter == creator:
                mock.set_response(ev.url, "creator evidence content long enough here")
            else:
                mock.set_failure(ev.url)
        for eid in eids:
            ev = c.get_evidence(eid)
            if ev.submitter == creator:
                c.fetch_evidence(eid)
            else:
                with self.assertRaises(RenderFailure):
                    c.fetch_evidence(eid)
        c.seal_evidence(case_id)  # must NOT raise
        self.assertEqual(c.get_case(case_id).state, gf.CASE_CASE_FROZEN)
        # The community item remains permanently queryable, honestly
        # NOT_FETCHED -- never deleted, never claimed false.
        community_eid = [e for e in eids if c.get_evidence(e).submitter != creator][0]
        ev = c.get_evidence(community_eid)
        self.assertEqual(ev.retrieval_status, gf.RETRIEVAL_NOT_FETCHED)
        self.assertEqual(ev.content_fingerprint, b"")

    def test_unavailable_creator_evidence_still_blocks_seal(self):
        # Creator (required-lane) evidence remains a genuine seal
        # requirement -- unlike community evidence, it is NOT made
        # non-blocking. abort_case remains the correct tool here.
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_failure(c.get_evidence(eid).url)
        with self.assertRaises(RenderFailure):
            c.fetch_evidence(eid)
        with self.assertRaises(UserError):
            c.seal_evidence(case_id)
        c.abort_case(case_id)
        self.assertEqual(c.get_case(case_id).state, gf.CASE_ABORTED)

    def test_community_fetched_evidence_included_in_adjudication_set(self):
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        args = _evidence_arrays(("https://community.example.com/good",))
        c.submit_fork_evidence(fid, *args)
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        mock = shim.get_mock_web()
        community_eid = None
        for eid in eids:
            ev = c.get_evidence(eid)
            if ev.submitter == creator:
                mock.set_response(ev.url, "creator content that is long enough here")
            else:
                mock.set_response(ev.url, "community content that is long enough here too")
                community_eid = eid
            c.fetch_evidence(eid)
        c.seal_evidence(case_id)

        def lookup(e):
            return c.evidence[e]

        # The adjudication input set (evidence_set_fingerprint) includes
        # ALL evidence ids since both creator and community ended up
        # FETCHED here.
        expected = gf._evidence_set_fingerprint(int(case_id), eids, lookup)
        self.assertEqual(c.get_case(case_id).evidence_set_fingerprint, expected)
        self.assertIsNotNone(community_eid)

    def test_stage7_input_excludes_records_without_eligible_content(self):
        # The adjudication input set (evidence_set_fingerprint) must
        # differ from a fingerprint computed over ALL membership when a
        # non-required item never reached FETCHED.
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        args = _evidence_arrays(("https://community.example.com/never",))
        c.submit_fork_evidence(fid, *args)
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        mock = shim.get_mock_web()
        creator_eid = None
        for eid in eids:
            ev = c.get_evidence(eid)
            if ev.submitter == creator:
                mock.set_response(ev.url, "creator content that is long enough here")
                c.fetch_evidence(eid)
                creator_eid = eid
            # community item left NOT_FETCHED
        c.seal_evidence(case_id)

        def lookup(e):
            return c.evidence[e]

        full_membership_fp = gf._evidence_set_fingerprint(int(case_id), eids, lookup)
        eligible_only_fp = gf._evidence_set_fingerprint(int(case_id), [creator_eid], lookup)
        actual = c.get_case(case_id).evidence_set_fingerprint
        self.assertNotEqual(actual, full_membership_fp)
        self.assertEqual(actual, eligible_only_fp)

    def test_seal_fingerprints_the_true_disposition_of_every_member(self):
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        args = _evidence_arrays(("https://community.example.com/never2",))
        c.submit_fork_evidence(fid, *args)
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        for eid in eids:
            ev = c.get_evidence(eid)
            if ev.submitter == creator:
                shim.get_mock_web().set_response(ev.url, "creator content long enough here too")
                c.fetch_evidence(eid)
        c.seal_evidence(case_id)

        def lookup(e):
            return c.evidence[e]

        expected_disposition = gf._retrieval_disposition_fingerprint(int(case_id), eids, lookup)
        self.assertEqual(c.get_case(case_id).retrieval_disposition_fingerprint, expected_disposition)
        # The disposition fingerprint covers ALL members (including the
        # still-NOT_FETCHED community one) -- distinct from the
        # adjudication-input-only evidence_set_fingerprint.
        self.assertNotEqual(
            c.get_case(case_id).retrieval_disposition_fingerprint,
            c.get_case(case_id).evidence_set_fingerprint,
        )

    def test_creator_cannot_delete_or_overwrite_community_membership(self):
        # Structural guarantee: no method exists that removes an evidence
        # record or lets the creator rewrite another submitter's data.
        # Membership is frozen at close and every record remains
        # reachable via list_evidence_of_case / get_evidence forever.
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        args = _evidence_arrays(("https://community.example.com/protected",))
        c.submit_fork_evidence(fid, *args)
        shim.set_sender(creator)
        c.close_evidence(case_id)
        before_ids = set(int(e) for e in c.evidence_by_case[case_id])
        # Creator has no privileged write path onto community records --
        # only fetch_evidence exists, and it is content-neutral (executes
        # the SAME render() regardless of caller identity) and permission-
        # less, never submitter-aware in what it writes.
        community_eid = [
            e for e in c.evidence_by_case[case_id]
            if c.get_evidence(e).submitter != creator
        ][0]
        original_submitter = c.get_evidence(community_eid).submitter
        original_url = c.get_evidence(community_eid).url
        shim.get_mock_web().set_response(
            c.get_evidence(community_eid).url, "content fetched by whoever calls fetch_evidence"
        )
        c.fetch_evidence(community_eid)  # creator or anyone may call this
        after = c.get_evidence(community_eid)
        self.assertEqual(after.submitter, original_submitter)  # provenance unchanged
        self.assertEqual(after.url, original_url)  # URL unchanged
        after_ids = set(int(e) for e in c.evidence_by_case[case_id])
        self.assertEqual(before_ids, after_ids)  # nothing added/removed

    def test_no_semantic_penalty_encoded_in_retrieval_outcome(self):
        # Structural: Stage 6b contains no verdict/adjudication logic at
        # all. A NOT_FETCHED or UNUSABLE_SHORT status is a retrieval fact,
        # never a judgment.
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        seal_start = src.index("def seal_evidence")
        seal_end = src.index("def abort_case")
        seal_body = src[seal_start:seal_end]
        for banned in ("NOT_FAITHFUL", "VERDICT_", "FINDING_"):
            self.assertNotIn(banned, seal_body)

    def test_transparent_unusable_status_no_silent_drop(self):
        # A community item that resolves to unusable-short content is
        # still visible with its honest status -- never excluded/hidden.
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        args = _evidence_arrays(("https://community.example.com/weak",))
        c.submit_fork_evidence(fid, *args)
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        mock = shim.get_mock_web()
        for eid in eids:
            ev = c.get_evidence(eid)
            if ev.submitter == creator:
                mock.set_response(ev.url, "creator content is long enough to be useful")
            else:
                mock.set_response(ev.url, "")  # resolves, but unusable
        for eid in eids:
            c.fetch_evidence(eid)
        c.seal_evidence(case_id)  # succeeds -- unusable is a resolved outcome
        community_eid = [
            eid for eid in eids if c.get_evidence(eid).submitter != creator
        ][0]
        ev = c.get_evidence(community_eid)
        self.assertEqual(ev.retrieval_status, gf.RETRIEVAL_UNUSABLE_SHORT)
        self.assertTrue(ev.frozen)
        # No semantic penalty is attached here -- Stage 6b makes no
        # semantic judgment; that's Stage 7's job.

    def test_case_liveness_after_retrieval_failure(self):
        # A single permanently-failing item does not prevent OTHER cases
        # (e.g. a later fork under the same root) from proceeding normally.
        c, did, rid, fid, case_id, creator = _fresh_fork_case()
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_failure(c.get_evidence(eid).url)
        with self.assertRaises(RenderFailure):
            c.fetch_evidence(eid)
        c.abort_case(case_id)
        # Unrelated root/case still fully functional.
        c2, did2, rid2, case_id2 = _fresh_root_case(urls=("https://z/1",))
        c2.close_evidence(case_id2)
        eid2 = list(c2.evidence_by_case[case_id2])[0]
        shim.get_mock_web().set_response("https://z/1", "totally separate, working content")
        c2.fetch_evidence(eid2)
        c2.seal_evidence(case_id2)
        self.assertEqual(c2.get_case(case_id2).state, gf.CASE_CASE_FROZEN)


# ============================================================================
# Render profile
# ============================================================================


class RenderProfileTests(unittest.TestCase):
    def test_standard_profile_stored_exactly(self):
        c, did, rid, case_id = _fresh_root_case(
            urls=("https://x/1",), profiles=(gf.RENDER_PROFILE_STANDARD,),
        )
        eid = list(c.evidence_by_case[case_id])[0]
        self.assertEqual(c.get_evidence(eid).render_profile, gf.RENDER_PROFILE_STANDARD)

    def test_dynamic_profile_stored_exactly(self):
        c, did, rid, case_id = _fresh_root_case(
            urls=("https://x/1",), profiles=(gf.RENDER_PROFILE_DYNAMIC,),
        )
        eid = list(c.evidence_by_case[case_id])[0]
        self.assertEqual(c.get_evidence(eid).render_profile, gf.RENDER_PROFILE_DYNAMIC)

    def test_invalid_profile_rejected(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", *_params_kv([]))
        args = _evidence_arrays(("https://x/1",), profiles=("BOGUS_PROFILE",))
        with self.assertRaises(UserError):
            c.submit_root_envelope(rid, *_envelope_fields(), *args)

    def test_no_arbitrary_wait_or_html_surface(self):
        # Structural: only two profile string constants exist; nothing in
        # the public ABI accepts a caller-supplied wait duration or mode.
        self.assertEqual(
            set(gf._ALLOWED_RENDER_PROFILES),
            {gf.RENDER_PROFILE_STANDARD, gf.RENDER_PROFILE_DYNAMIC},
        )

    def test_profile_immutable_after_close(self):
        c, did, rid, case_id = _fresh_root_case(
            urls=("https://x/1",), profiles=(gf.RENDER_PROFILE_STANDARD,),
        )
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        before = c.get_evidence(eid).render_profile
        shim.get_mock_web().set_response("https://x/1", "content for profile immutability test")
        c.fetch_evidence(eid)
        after = c.get_evidence(eid).render_profile
        self.assertEqual(before, after)

    def test_evidence_class_independent_of_profile(self):
        c, did, rid, case_id = _fresh_root_case(
            urls=("https://x/1",), profiles=(gf.RENDER_PROFILE_DYNAMIC,),
        )
        eid = list(c.evidence_by_case[case_id])[0]
        ev = c.get_evidence(eid)
        self.assertEqual(ev.evidence_class, gf.EC_OFFICIAL_GOVERNANCE)  # default in helper
        self.assertEqual(ev.render_profile, gf.RENDER_PROFILE_DYNAMIC)


# ============================================================================
# Fingerprint tests
# ============================================================================


class FingerprintTests(unittest.TestCase):
    def test_content_fingerprint_same_input_same_output(self):
        a = gf._content_fingerprint("hello world")
        b = gf._content_fingerprint("hello world")
        self.assertEqual(a, b)

    def test_content_fingerprint_changes_with_content(self):
        a = gf._content_fingerprint("hello world")
        b = gf._content_fingerprint("hello world!")
        self.assertNotEqual(a, b)

    def test_content_fingerprint_matches_hashlib_reference(self):
        text = "reference check content"
        got = gf._content_fingerprint(text)
        want = hashlib.sha256(text.encode("utf-8")).digest()
        self.assertEqual(got, want)

    def test_membership_fingerprint_stable(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1", "https://x/2"))

        def lookup(eid):
            return c.evidence[eid]

        ids = list(c.evidence_by_case[case_id])
        fp1 = gf._membership_fingerprint(int(case_id), ids, lookup)
        fp2 = gf._membership_fingerprint(int(case_id), ids, lookup)
        self.assertEqual(fp1, fp2)

    def test_membership_fingerprint_changes_with_evidence_order(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1", "https://x/2"))

        def lookup(eid):
            return c.evidence[eid]

        ids = list(c.evidence_by_case[case_id])
        fp_forward = gf._membership_fingerprint(int(case_id), ids, lookup)
        fp_reversed = gf._membership_fingerprint(int(case_id), list(reversed(ids)), lookup)
        self.assertNotEqual(fp_forward, fp_reversed)

    def test_evidence_set_fingerprint_changes_when_content_changes(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]

        def lookup(eid_):
            return c.evidence[eid_]

        shim.get_mock_web().set_response("https://x/1", "version one of the content here")
        c.fetch_evidence(eid)
        fp1 = gf._evidence_set_fingerprint(int(case_id), [eid], lookup)

        # Simulate a different committed content by constructing a second,
        # independent case with different content (fetched evidence is
        # immutable so we cannot literally refetch this one).
        c2, did2, rid2, case_id2 = _fresh_root_case(urls=("https://y/1",))
        c2.close_evidence(case_id2)
        eid2 = list(c2.evidence_by_case[case_id2])[0]

        def lookup2(eid_):
            return c2.evidence[eid_]

        shim.get_mock_web().set_response("https://y/1", "version TWO of the content here")
        c2.fetch_evidence(eid2)
        fp2 = gf._evidence_set_fingerprint(int(case_id2), [eid2], lookup2)
        self.assertNotEqual(fp1, fp2)

    def test_case_fingerprint_changes_when_target_fingerprint_changes(self):
        # Two different roots (different import_fingerprint) with
        # otherwise-identical envelope/evidence content produce different
        # case_fingerprints.
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "identical evidence content for check")
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        fp1 = c.get_case(case_id).case_fingerprint

        c2 = _fresh()
        did2 = c2.register_dao("B", "https://b")
        rid2 = c2.import_root_proposal(
            did2, "EP-DIFFERENT", "T", "https://x/1", *_params_kv([("allocation", "100000")]),
        )
        args = _evidence_arrays(("https://x/1",))
        case_id2 = c2.submit_root_envelope(rid2, *_envelope_fields(), *args)
        c2.close_evidence(case_id2)
        eid2 = list(c2.evidence_by_case[case_id2])[0]
        shim.get_mock_web().set_response("https://x/1", "identical evidence content for check")
        c2.fetch_evidence(eid2)
        c2.seal_evidence(case_id2)
        fp2 = c2.get_case(case_id2).case_fingerprint
        self.assertNotEqual(fp1, fp2)

    def test_case_fingerprint_root_envelope_binds_envelope_fields(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "content for envelope binding check")
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        fp1 = c.get_case(case_id).case_fingerprint

        c2, did2, rid2, case_id2 = _fresh_root_case(
            urls=("https://x/1",),
            mutable=("duration",),  # different mutable set -> different envelope
            immutable=("beneficiary_class",),
        )
        c2.close_evidence(case_id2)
        eid2 = list(c2.evidence_by_case[case_id2])[0]
        shim.get_mock_web().set_response("https://x/1", "content for envelope binding check")
        c2.fetch_evidence(eid2)
        c2.seal_evidence(case_id2)
        fp2 = c2.get_case(case_id2).case_fingerprint
        self.assertNotEqual(fp1, fp2)


# ============================================================================
# Root / fork parity
# ============================================================================


class RootForkParityTests(unittest.TestCase):
    def test_root_envelope_case_full_lifecycle(self):
        c, did, rid, case_id = _fresh_root_case(urls=("https://x/1",))
        self.assertEqual(c.get_case(case_id).case_type, gf.CASE_TYPE_ROOT_ENVELOPE)
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://x/1", "root envelope lifecycle content ok")
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        self.assertEqual(c.get_case(case_id).state, gf.CASE_CASE_FROZEN)

    def test_fork_case_full_lifecycle(self):
        c, did, rid, fid, case_id, creator = _fresh_fork_case(urls=("https://a.example.com/1",))
        self.assertEqual(c.get_case(case_id).case_type, gf.CASE_TYPE_FORK)
        shim.set_sender(creator)
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response(
            "https://a.example.com/1", "fork case lifecycle content ok, long enough"
        )
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        self.assertEqual(c.get_case(case_id).state, gf.CASE_CASE_FROZEN)

    def test_root_web_content_fingerprint_derived_from_matching_evidence(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(
            did, "EP", "T", "https://canonical.example.com/prop", *_params_kv([]),
        )
        args = _evidence_arrays(
            ("https://canonical.example.com/prop", "https://other.example.com/x"),
        )
        case_id = c.submit_root_envelope(rid, *_envelope_fields(), *args)
        c.close_evidence(case_id)
        eids = list(c.evidence_by_case[case_id])
        mock = shim.get_mock_web()
        mock.set_response("https://canonical.example.com/prop", "the canonical page content here, long enough")
        mock.set_response("https://other.example.com/x", "some other unrelated evidence text")
        for eid in eids:
            c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        root = c.get_root_proposal(rid)
        self.assertNotEqual(root.web_content_fingerprint, b"")
        canonical_eid = [
            e for e in eids
            if c.get_evidence(e).url == "https://canonical.example.com/prop"
        ][0]
        self.assertEqual(
            root.web_content_fingerprint,
            c.get_evidence(canonical_eid).content_fingerprint,
        )

    def test_root_web_content_fingerprint_stays_empty_if_no_matching_evidence(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(
            did, "EP", "T", "https://canonical.example.com/prop", *_params_kv([]),
        )
        args = _evidence_arrays(("https://unrelated.example.com/x",))
        case_id = c.submit_root_envelope(rid, *_envelope_fields(), *args)
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response(
            "https://unrelated.example.com/x", "unrelated evidence content here, long enough"
        )
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        self.assertEqual(c.get_root_proposal(rid).web_content_fingerprint, b"")

    def test_root_web_content_fingerprint_never_derived_from_unusable_short(self):
        # Sec 15 requirement: web_content_fingerprint must only ever come
        # from a RETRIEVAL_FETCHED record. For ROOT_ENVELOPE cases this is
        # now structurally guaranteed: every member of a root-envelope
        # case is in the required lane (sec 4), so seal itself rejects
        # before reaching the web_content_fingerprint derivation step if
        # the canonical URL resolved to UNUSABLE_SHORT -- there is no
        # code path that could derive it from unusable content.
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(
            did, "EP", "T", "https://canonical.example.com/prop", *_params_kv([]),
        )
        args = _evidence_arrays(("https://canonical.example.com/prop",))
        case_id = c.submit_root_envelope(rid, *_envelope_fields(), *args)
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response("https://canonical.example.com/prop", "")  # unusable
        c.fetch_evidence(eid)
        self.assertEqual(c.get_evidence(eid).retrieval_status, gf.RETRIEVAL_UNUSABLE_SHORT)
        with self.assertRaises(UserError):
            c.seal_evidence(case_id)  # required (all) evidence must be FETCHED
        # Case never reached CASE_CASE_FROZEN, so web_content_fingerprint
        # was never touched -- still empty, never derived from unusable
        # content.
        self.assertEqual(c.get_root_proposal(rid).web_content_fingerprint, b"")

    def test_no_duplicate_fetch_for_root_canonical_url(self):
        # The root's own canonical URL, when included as evidence, is
        # fetched exactly once via fetch_evidence -- seal derives
        # web_content_fingerprint from that single frozen record, never
        # triggering a second independent fetch.
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(
            did, "EP", "T", "https://canonical.example.com/prop", *_params_kv([]),
        )
        args = _evidence_arrays(("https://canonical.example.com/prop",))
        case_id = c.submit_root_envelope(rid, *_envelope_fields(), *args)
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        call_count = {"n": 0}
        mock = shim.get_mock_web()
        real_render = mock.render

        def counting_render(url, mode="text", wait_after_loaded=None):
            call_count["n"] += 1
            return real_render(url, mode=mode, wait_after_loaded=wait_after_loaded)

        mock.render = counting_render
        mock.set_response("https://canonical.example.com/prop", "canonical content fetched once, long enough")
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        self.assertEqual(call_count["n"], 1)


# ============================================================================
# Prohibited behavior
# ============================================================================


class ProhibitedBehaviorTests(unittest.TestCase):
    def test_no_web_get_or_semantic_prompt_calls(self):
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        # Stage 7 baseline: gl.eq_principle.prompt_comparative wrapping
        # gl.nondet.exec_prompt(..., response_format="json") is the chosen
        # semantic consensus primitive (run_adjudication only). web.get and
        # prompt_non_comparative remain banned.
        for banned in ("web.get(", "gl.eq_principle.prompt_non_comparative"):
            self.assertNotIn(banned, src)

    def test_no_gl_message_value(self):
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        self.assertNotIn("gl.message.value", src)

    def test_no_transfer(self):
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        self.assertNotIn("transfer(", src)

    def test_uses_render_and_strict_eq(self):
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        self.assertIn("gl.nondet.web.render(", src)
        self.assertIn("gl.eq_principle.strict_eq(", src)

    def test_no_try_except_around_render_call(self):
        # Same discipline as the Stage 6a probe: no speculative exception
        # catching around the nondet call.
        import ast, pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                seg = ast.get_source_segment(src, node) or ""
                if "strict_eq" in seg or "web.render" in seg:
                    self.fail("try/except found wrapping a nondet/strict_eq call")

    def test_adjudicate_still_unimplemented(self):
        c = _fresh()
        with self.assertRaises(UserError):
            c.adjudicate(shim.u256(1))

    def test_no_finalization_or_verdict_logic_present(self):
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        # finalize() and challenge_verdict()/settle_bond() must still raise
        # their Stage-2 placeholder, i.e. no Stage 6b business logic crept
        # into them.
        self.assertIn(
            'def finalize(self, target_id: u256, target_kind: str) -> None:\n'
            '        raise gl.vm.UserError("stage-2: not implemented")',
            src,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
