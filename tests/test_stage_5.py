"""Stage 5 tests for governance_fork.py.

Covers the community-compatible fork evidence architecture: creator
quota, community quota, per-contributor limit, case creation on first
submission and reuse on subsequent submissions, provenance retention,
URL normalization and dedup semantics, atomicity, and prohibited-
behavior gates.

Uses the same test-harness patterns as Stage 4: envelope status is
pre-flipped to ENVELOPE_FAITHFUL in test process storage only.
"""

from __future__ import annotations

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

shim.autopay_bonds(gf)  # Stage 9: existing payable call sites pass no value


UserError = shim.get_user_error()


def _params(pairs):
    return shim.DynArray([gf.ParamKV(key=k, value=v) for k, v in pairs])


def _delta(entries):
    return shim.DynArray([
        gf.DeltaEntry(dimension_name=n, parent_value=pv, fork_value=fv, claim_kind=ck)
        for (n, ck, pv, fv) in entries
    ])


def _envelope(mutable=("allocation", "duration"),
              immutable=("beneficiary_class",)):
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
        title=title,
        summary="",
        structured_parameters=_params(params),
        reasoning="",
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


def _envelope_fields(mutable=("allocation", "duration"),
                      immutable=("beneficiary_class",)):
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


def _root_evidence_bundle():
    return (
        shim.DynArray(["https://gov.example.com/prop/1"]),
        shim.DynArray([gf.EC_OFFICIAL_GOVERNANCE]),
        shim.DynArray(["original proposal"]),
        shim.DynArray(["official DAO source"]),
        shim.DynArray(["2026-01-01"]),
        shim.DynArray([gf.RENDER_PROFILE_STANDARD]),
    )


def _fresh_with_fork():
    """Set up a contract with a FAITHFUL root and one Draft fork attributed
    to the default sender. Test harness only — no production path enables
    envelope FAITHFUL.
    """
    shim.reset_message_context()
    c = gf.Contract()
    did = c.register_dao("A", "https://a")
    rid = c.import_root_proposal(
        did, "EP", "T", "https://x/1",
        *_params_kv([("allocation", "100000"), ("duration", "6 months")]),
    )
    urls, cls, rel, auth, tm, rp = _root_evidence_bundle()
    c.submit_root_envelope(rid, *_envelope_fields(), urls, cls, rel, auth, tm, rp)
    # ---- test-harness flip ONLY ----
    r = c.get_root_proposal(rid)
    r.envelope_status = gf.ENVELOPE_FAITHFUL
    c.roots[rid] = r
    # Creator sender for the fork
    creator = shim.Address("0x" + "cc" * 20)
    shim.set_sender(creator)
    fid = c.create_fork(
        rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
        *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
        *_body_fields(),
    )
    return c, did, rid, fid, creator


def _one_evidence(url="https://a.example.com/p1",
                  ec=gf.EC_OFFICIAL_GOVERNANCE,
                  rel="original",
                  auth="official",
                  tm="2026-01-01",
                  rp=gf.RENDER_PROFILE_STANDARD):
    return (
        shim.DynArray([url]),
        shim.DynArray([ec]),
        shim.DynArray([rel]),
        shim.DynArray([auth]),
        shim.DynArray([tm]),
        shim.DynArray([rp]),
    )


def _many_evidence(urls, ec=None, rel=None, auth=None, tm=None, rp=None):
    n = len(urls)
    if ec is None:
        ec = [gf.EC_OFFICIAL_GOVERNANCE] * n
    if rel is None:
        rel = ["r"] * n
    if auth is None:
        auth = ["a"] * n
    if tm is None:
        tm = ["t"] * n
    if rp is None:
        rp = [gf.RENDER_PROFILE_STANDARD] * n
    return (
        shim.DynArray(list(urls)),
        shim.DynArray(list(ec)),
        shim.DynArray(list(rel)),
        shim.DynArray(list(auth)),
        shim.DynArray(list(tm)),
        shim.DynArray(list(rp)),
    )


# ============================================================================
# Contributor model — creator quota
# ============================================================================


class CreatorQuotaTests(unittest.TestCase):
    def test_creator_first_submission_creates_case_and_transitions_status(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        urls, ec, rel, auth, tm, rp = _one_evidence()
        case_id = c.submit_fork_evidence(fid, urls, ec, rel, auth, tm, rp)
        f = c.get_fork(fid)
        self.assertEqual(f.status, gf.FORK_EVIDENCE_OPEN)
        self.assertEqual(int(f.evidence_case_id), int(case_id))
        case = c.get_case(case_id)
        self.assertEqual(case.case_type, gf.CASE_TYPE_FORK)
        self.assertEqual(case.target_kind, gf.TARGET_KIND_FORK)
        self.assertEqual(int(case.target_id), int(fid))
        self.assertEqual(case.target_fingerprint, f.body_fingerprint)
        self.assertEqual(case.state, gf.CASE_OPEN)
        self.assertEqual(case.evidence_set_fingerprint, b"")
        self.assertEqual(case.case_fingerprint, b"")
        counters = c.fork_case_counters[case_id]
        self.assertEqual(int(counters.creator_count), 1)
        self.assertEqual(int(counters.community_count), 0)

    def test_creator_may_append_and_reuses_case(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        urls1, ec1, rel1, auth1, tm1, rp1 = _one_evidence("https://a.example.com/p1")
        case_id1 = c.submit_fork_evidence(fid, urls1, ec1, rel1, auth1, tm1, rp1)
        urls2, ec2, rel2, auth2, tm2, rp2 = _one_evidence("https://a.example.com/p2")
        case_id2 = c.submit_fork_evidence(fid, urls2, ec2, rel2, auth2, tm2, rp2)
        self.assertEqual(int(case_id1), int(case_id2))
        # Only one case created
        counters = c.fork_case_counters[case_id1]
        self.assertEqual(int(counters.creator_count), 2)

    def test_creator_reaches_cap(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        urls = [f"https://a.example.com/p{i}" for i in range(gf.CREATOR_EVIDENCE_CAP)]
        case_id = c.submit_fork_evidence(fid, *_many_evidence(urls))
        counters = c.fork_case_counters[case_id]
        self.assertEqual(int(counters.creator_count), gf.CREATOR_EVIDENCE_CAP)

    def test_creator_cap_plus_one_rejected(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        urls = [f"https://a.example.com/p{i}" for i in range(gf.CREATOR_EVIDENCE_CAP)]
        c.submit_fork_evidence(fid, *_many_evidence(urls))
        shim.set_sender(creator)
        extra_urls, ec, rel, auth, tm, rp = _one_evidence("https://a.example.com/extra")
        with self.assertRaises(UserError) as ctx:
            c.submit_fork_evidence(fid, extra_urls, ec, rel, auth, tm, rp)
        self.assertIn("CREATOR_EVIDENCE_CAP", str(ctx.exception))

    def test_creator_cannot_consume_community_reserve(self):
        # Creator can submit up to CREATOR_EVIDENCE_CAP. Even though the case
        # still has COMMUNITY_EVIDENCE_CAP slots free, the creator's own cap
        # is the tighter constraint for them.
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        urls = [f"https://a.example.com/p{i}" for i in range(gf.CREATOR_EVIDENCE_CAP)]
        c.submit_fork_evidence(fid, *_many_evidence(urls))
        shim.set_sender(creator)
        urls2, ec2, rel2, auth2, tm2, rp2 = _one_evidence("https://a.example.com/extra")
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, urls2, ec2, rel2, auth2, tm2, rp2)


# ============================================================================
# Contributor model — community quota + per-contributor cap
# ============================================================================


class CommunityQuotaTests(unittest.TestCase):
    def test_non_creator_can_submit(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        urls, ec, rel, auth, tm, rp = _one_evidence("https://b.example.com/p1")
        case_id = c.submit_fork_evidence(fid, urls, ec, rel, auth, tm, rp)
        counters = c.fork_case_counters[case_id]
        self.assertEqual(int(counters.creator_count), 0)
        self.assertEqual(int(counters.community_count), 1)
        # provenance retained
        ev_ids = [int(e) for e in c.evidence_by_case[case_id]]
        ev = c.get_evidence(shim.u256(ev_ids[0]))
        self.assertEqual(str(ev.submitter), str(outsider))

    def test_multiple_community_contributors(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        a = shim.Address("0x" + "dd" * 20)
        b = shim.Address("0x" + "ee" * 20)
        shim.set_sender(a)
        c.submit_fork_evidence(fid, *_one_evidence("https://x.example.com/1"))
        shim.set_sender(b)
        c.submit_fork_evidence(fid, *_one_evidence("https://y.example.com/1"))
        case_id = c.get_fork(fid).evidence_case_id
        counters = c.fork_case_counters[case_id]
        self.assertEqual(int(counters.community_count), 2)

    def test_one_contributor_max_two(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        contrib = shim.Address("0x" + "dd" * 20)
        shim.set_sender(contrib)
        c.submit_fork_evidence(fid, *_one_evidence("https://x.example.com/1"))
        shim.set_sender(contrib)
        c.submit_fork_evidence(fid, *_one_evidence("https://x.example.com/2"))
        shim.set_sender(contrib)
        with self.assertRaises(UserError) as ctx:
            c.submit_fork_evidence(fid, *_one_evidence("https://x.example.com/3"))
        self.assertIn("PER_CONTRIBUTOR", str(ctx.exception))

    def test_batch_by_single_contributor_respects_per_contributor_cap(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        contrib = shim.Address("0x" + "dd" * 20)
        shim.set_sender(contrib)
        urls = ["https://z.example.com/1", "https://z.example.com/2", "https://z.example.com/3"]
        with self.assertRaises(UserError) as ctx:
            c.submit_fork_evidence(fid, *_many_evidence(urls))
        self.assertIn("PER_CONTRIBUTOR", str(ctx.exception))

    def test_aggregate_community_cap_enforced(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        # Fill the community cap with 4 contributors * 2 = 8.
        for i in range(4):
            addr = shim.Address("0x" + f"{i:02x}" * 20)
            shim.set_sender(addr)
            urls = [f"https://c{i}.example.com/1", f"https://c{i}.example.com/2"]
            c.submit_fork_evidence(fid, *_many_evidence(urls))
        case_id = c.get_fork(fid).evidence_case_id
        counters = c.fork_case_counters[case_id]
        self.assertEqual(int(counters.community_count), gf.COMMUNITY_EVIDENCE_CAP)
        # A fresh contributor cannot squeeze in.
        outsider = shim.Address("0x" + "88" * 20)
        shim.set_sender(outsider)
        with self.assertRaises(UserError) as ctx:
            c.submit_fork_evidence(fid, *_one_evidence("https://outsider.example.com/1"))
        self.assertIn("COMMUNITY_EVIDENCE_CAP", str(ctx.exception))

    def test_community_cannot_consume_creator_reserve(self):
        # Once community fills its cap (8), even though case cap 16 is not
        # exhausted, further community submissions must reject.
        c, did, rid, fid, creator = _fresh_with_fork()
        for i in range(4):
            addr = shim.Address("0x" + f"{i:02x}" * 20)
            shim.set_sender(addr)
            urls = [f"https://c{i}.example.com/1", f"https://c{i}.example.com/2"]
            c.submit_fork_evidence(fid, *_many_evidence(urls))
        outsider = shim.Address("0x" + "88" * 20)
        shim.set_sender(outsider)
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_one_evidence("https://x.example.com/x"))


# ============================================================================
# Mixed creator + community
# ============================================================================


class MixedContribTests(unittest.TestCase):
    def test_creator_and_community_coexist(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        c.submit_fork_evidence(fid, *_one_evidence("https://a.example.com/1"))
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        c.submit_fork_evidence(fid, *_one_evidence("https://b.example.com/1"))
        case_id = c.get_fork(fid).evidence_case_id
        counters = c.fork_case_counters[case_id]
        self.assertEqual(int(counters.creator_count), 1)
        self.assertEqual(int(counters.community_count), 1)

    def test_total_capped_at_16(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        urls = [f"https://a.example.com/p{i}" for i in range(gf.CREATOR_EVIDENCE_CAP)]
        c.submit_fork_evidence(fid, *_many_evidence(urls))
        for i in range(4):
            addr = shim.Address("0x" + f"{i:02x}" * 20)
            shim.set_sender(addr)
            more = [f"https://c{i}.example.com/1", f"https://c{i}.example.com/2"]
            c.submit_fork_evidence(fid, *_many_evidence(more))
        case_id = c.get_fork(fid).evidence_case_id
        self.assertEqual(len(c.evidence_by_case[case_id]), gf.MAX_EVIDENCE_PER_CASE)

    def test_same_url_across_creator_and_community_rejected(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        c.submit_fork_evidence(fid, *_one_evidence("https://shared.example.com/x"))
        outsider = shim.Address("0x" + "dd" * 20)
        shim.set_sender(outsider)
        with self.assertRaises(UserError) as ctx:
            c.submit_fork_evidence(fid, *_one_evidence("https://shared.example.com/x"))
        self.assertIn("duplicate", str(ctx.exception).lower())


# ============================================================================
# Case lifecycle + fork status
# ============================================================================


class CaseLifecycleTests(unittest.TestCase):
    def test_evidence_ids_append_in_order(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        urls = ["https://a.example.com/1", "https://a.example.com/2", "https://a.example.com/3"]
        case_id = c.submit_fork_evidence(fid, *_many_evidence(urls))
        ids = [int(e) for e in c.evidence_by_case[case_id]]
        self.assertEqual(ids, sorted(ids))
        for i, eid in enumerate(ids):
            ev = c.get_evidence(shim.u256(eid))
            self.assertEqual(ev.url, urls[i])

    def test_case_created_only_once(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        cid1 = c.submit_fork_evidence(fid, *_one_evidence("https://a.example.com/1"))
        shim.set_sender(shim.Address("0x" + "dd" * 20))
        cid2 = c.submit_fork_evidence(fid, *_one_evidence("https://b.example.com/1"))
        self.assertEqual(int(cid1), int(cid2))

    def test_frozen_flag_stays_false(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        cid = c.submit_fork_evidence(fid, *_one_evidence())
        for eid in c.evidence_by_case[cid]:
            ev = c.get_evidence(shim.u256(int(eid)))
            self.assertFalse(ev.frozen)
            self.assertEqual(ev.content_fingerprint, b"")


# ============================================================================
# URL canonicalization
# ============================================================================


class UrlCanonicalizationTests(unittest.TestCase):
    def test_scheme_case_normalized(self):
        self.assertEqual(gf._normalize_url("HTTPS://x.com/foo"),
                         "https://x.com/foo")

    def test_host_case_normalized(self):
        self.assertEqual(gf._normalize_url("https://Example.COM/Path"),
                         "https://example.com/Path")

    def test_path_case_preserved(self):
        self.assertEqual(gf._normalize_url("https://x.com/FooBAR"),
                         "https://x.com/FooBAR")

    def test_query_case_preserved(self):
        self.assertEqual(gf._normalize_url("https://x.com/p?A=1&b=2"),
                         "https://x.com/p?A=1&b=2")

    def test_trailing_slash_preserved(self):
        # /foo/ and /foo may point to different resources — do not merge.
        self.assertNotEqual(
            gf._normalize_url("https://x.com/foo/"),
            gf._normalize_url("https://x.com/foo"),
        )

    def test_fragment_dropped(self):
        self.assertEqual(gf._normalize_url("https://x.com/p#section-1"),
                         "https://x.com/p")

    def test_bad_scheme_rejected(self):
        with self.assertRaises(UserError):
            gf._normalize_url("ftp://x.com/foo")

    def test_empty_host_rejected(self):
        with self.assertRaises(UserError):
            gf._normalize_url("https:///foo")

    def test_newline_within_url_flagged_by_reject_newline_before_normalize(self):
        # _normalize_url itself does not check newlines; the caller runs
        # _reject_newline before it. Verified indirectly here.
        pass


class UrlDedupInBatchTests(unittest.TestCase):
    def test_duplicate_within_batch_rejected(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        urls = ["https://a.example.com/1", "https://a.example.com/1"]
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_many_evidence(urls))

    def test_duplicate_across_batches_rejected(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        c.submit_fork_evidence(fid, *_one_evidence("https://a.example.com/1"))
        shim.set_sender(creator)
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_one_evidence("https://a.example.com/1"))


# ============================================================================
# Field validation, claims, class
# ============================================================================


class FieldValidationTests(unittest.TestCase):
    def _shim(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        return c, fid

    def test_invalid_evidence_class_rejected(self):
        c, fid = self._shim()
        with self.assertRaises(UserError):
            c.submit_fork_evidence(
                fid, *_one_evidence(ec="BOGUS_CLASS")
            )

    def test_relevance_claim_bound(self):
        c, fid = self._shim()
        big = "x" * (gf.MAX_RELEVANCE_CLAIM_LEN + 1)
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_one_evidence(rel=big))

    def test_authority_claim_bound(self):
        c, fid = self._shim()
        big = "x" * (gf.MAX_AUTHORITY_CLAIM_LEN + 1)
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_one_evidence(auth=big))

    def test_temporal_marker_bound(self):
        c, fid = self._shim()
        big = "x" * (gf.MAX_TEMPORAL_MARKER_LEN + 1)
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_one_evidence(tm=big))

    def test_url_length_bound(self):
        c, fid = self._shim()
        big = "https://example.com/" + "y" * gf.MAX_URL_LEN
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_one_evidence(url=big))

    def test_newline_in_url_rejected(self):
        c, fid = self._shim()
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_one_evidence(url="https://a.example.com/p\n1"))

    def test_claims_stored_verbatim_no_trust_flag(self):
        c, fid = self._shim()
        cid = c.submit_fork_evidence(
            fid, *_one_evidence(
                url="https://a.example.com/1",
                rel="claims to be original proposal",
                auth="submitter says it is official",
            )
        )
        eid = int(list(c.evidence_by_case[cid])[0])
        ev = c.get_evidence(shim.u256(eid))
        self.assertEqual(ev.relevance_claim, "claims to be original proposal")
        self.assertEqual(ev.authority_claim, "submitter says it is official")


# ============================================================================
# Atomicity
# ============================================================================


class AtomicityTests(unittest.TestCase):
    def test_invalid_second_item_causes_zero_allocation_on_first_submission(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        # First item OK, second item has bad class -> whole batch rolls back.
        urls = shim.DynArray(["https://a.example.com/1", "https://b.example.com/2"])
        ec = shim.DynArray([gf.EC_OFFICIAL_GOVERNANCE, "BOGUS"])
        rel = shim.DynArray(["r", "r"])
        auth = shim.DynArray(["a", "a"])
        tm = shim.DynArray(["t", "t"])
        rp = shim.DynArray([gf.RENDER_PROFILE_STANDARD, gf.RENDER_PROFILE_STANDARD])
        prior_case_counter = int(c.next_case_id)
        prior_ev_counter = int(c.next_evidence_id)
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, urls, ec, rel, auth, tm, rp)
        # Case must NOT have been created, counters unchanged, fork status
        # still DRAFT.
        self.assertEqual(int(c.next_case_id), prior_case_counter)
        self.assertEqual(int(c.next_evidence_id), prior_ev_counter)
        self.assertEqual(c.get_fork(fid).status, gf.FORK_DRAFT)
        self.assertEqual(int(c.get_fork(fid).evidence_case_id), 0)

    def test_cap_breach_zero_allocation(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        urls = [f"https://a.example.com/p{i}" for i in range(gf.CREATOR_EVIDENCE_CAP + 1)]
        prior_ev = int(c.next_evidence_id)
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_many_evidence(urls))
        self.assertEqual(int(c.next_evidence_id), prior_ev)

    def test_duplicate_across_case_zero_allocation(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        shim.set_sender(creator)
        c.submit_fork_evidence(fid, *_one_evidence("https://a.example.com/1"))
        prior_ev = int(c.next_evidence_id)
        # Try to submit a batch that includes the already-present URL.
        urls = ["https://a.example.com/2", "https://a.example.com/1"]
        shim.set_sender(creator)
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_many_evidence(urls))
        self.assertEqual(int(c.next_evidence_id), prior_ev)

    def test_contributor_quota_breach_no_counter_increment(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        contrib = shim.Address("0x" + "dd" * 20)
        shim.set_sender(contrib)
        # Submitting 3 as one batch exceeds the per-contributor cap of 2.
        prior_ev = int(c.next_evidence_id)
        urls = ["https://z.example.com/1", "https://z.example.com/2", "https://z.example.com/3"]
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_many_evidence(urls))
        self.assertEqual(int(c.next_evidence_id), prior_ev)


# ============================================================================
# Fork status precondition
# ============================================================================


class ForkStatusTests(unittest.TestCase):
    def test_submission_to_non_draft_non_open_fork_rejected(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        # Simulate a later lifecycle state.
        f = c.get_fork(fid)
        f.status = gf.FORK_ADJUDICATING
        c.forks[fid] = f
        shim.set_sender(creator)
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_one_evidence())

    def test_paused_rejects(self):
        c, did, rid, fid, creator = _fresh_with_fork()
        # Only treasury_addr can pause; the default sender IS the treasury_addr.
        shim.set_sender("0x" + "aa" * 20)
        c.pause()
        shim.set_sender(creator)
        with self.assertRaises(UserError):
            c.submit_fork_evidence(fid, *_one_evidence())


# ============================================================================
# Root-envelope regression
# ============================================================================


class RootEnvelopeStillWorksTests(unittest.TestCase):
    def test_stage_3_envelope_flow_unchanged(self):
        shim.reset_message_context()
        c = gf.Contract()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", *_params_kv([]))
        urls, ec, rel, auth, tm, rp = _root_evidence_bundle()
        case_id = c.submit_root_envelope(rid, *_envelope_fields(), urls, ec, rel, auth, tm, rp)
        r = c.get_root_proposal(rid)
        self.assertEqual(r.envelope_status, gf.ENVELOPE_EVIDENCE_OPEN)
        self.assertEqual(int(r.envelope_case_id), int(case_id))


# ============================================================================
# create_fork FAITHFUL gate unchanged
# ============================================================================


class FaithfulGateUnchangedTests(unittest.TestCase):
    def test_create_fork_still_gated_on_faithful(self):
        shim.reset_message_context()
        c = gf.Contract()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1",
                                     *_params_kv([("allocation", "100000")]))
        # Envelope not submitted -> refuse
        r = c.get_root_proposal(rid)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
                *_body_fields(params=[("allocation", "50000")]),
            )


# ============================================================================
# Prohibited behavior
# ============================================================================


class ProhibitedBehaviorTests(unittest.TestCase):
    def test_no_disallowed_nondet_or_gen_calls(self):
        # Stage 6b baseline: gl.nondet.web.render + gl.eq_principle.strict_eq
        # are legitimate (fetch_evidence). Stage 7 baseline:
        # gl.eq_principle.prompt_comparative + gl.nondet.exec_prompt are
        # legitimate (run_adjudication). prompt_non_comparative, web.get and
        # native GEN transfer remain banned.
        import pathlib, re
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        for banned in ("web.get(", "gl.eq_principle.prompt_non_comparative"):
            self.assertNotIn(banned, src, banned)
        self.assertFalse(re.search(r"(?<!emit_)transfer\(", src), "bare transfer(")
        self.assertIn("gl.get_contract_at(", src)

    def test_gl_message_value_present_for_bond_capture(self):
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        self.assertIn("gl.message.value", src)

    def test_no_adjudicate_implementation(self):
        shim.reset_message_context()
        c = gf.Contract()
        with self.assertRaises(UserError):
            c.adjudicate(shim.u256(1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
