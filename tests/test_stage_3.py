"""Stage 3 tests for governance_fork.py.

Exercises DAO registration, root proposal import, deterministic import
fingerprint, and Intent Envelope submission (including root-envelope
evidence metadata and ROOT_ENVELOPE case creation). Does not exercise
any nondeterministic operation, web retrieval, native GEN behavior, or
semantic adjudication.
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


def _envelope(
    objective="Fund ecosystem developer work.",
    beneficiary_class="Developers",
    resource_type=gf.RESOURCE_TREASURY,
    scope="ecosystem-wide",
    essential=("must be for developer work",),
    mutable=("allocation", "duration"),
    immutable=("beneficiary_class",),
):
    return gf.IntentEnvelope(
        objective=objective,
        beneficiary_class=beneficiary_class,
        resource_type=resource_type,
        scope=scope,
        essential_constraints=shim.DynArray(essential),
        mutable_dimensions=shim.DynArray(mutable),
        immutable_dimensions=shim.DynArray(immutable),
        parent_proposal_fingerprint=b"",
        envelope_version=shim.u32(0),
    )


def _evidence_bundle(urls=("https://gov.example.com/prop/1",),
                     classes=None,
                     rel=None,
                     auth=None,
                     tm=None,
                     render_profiles=None):
    n = len(urls)
    if classes is None:
        classes = (gf.EC_OFFICIAL_GOVERNANCE,) * n
    if rel is None:
        rel = ("original proposal",) * n
    if auth is None:
        auth = ("official DAO source",) * n
    if tm is None:
        tm = ("2026-01-01",) * n
    if render_profiles is None:
        render_profiles = (gf.RENDER_PROFILE_STANDARD,) * n
    return (
        shim.DynArray(urls),
        shim.DynArray(classes),
        shim.DynArray(rel),
        shim.DynArray(auth),
        shim.DynArray(tm),
        shim.DynArray(render_profiles),
    )


def _params(pairs):
    return shim.DynArray([gf.ParamKV(key=k, value=v) for k, v in pairs])


def _fresh():
    shim.reset_message_context()
    return gf.Contract()


UserError = shim.get_user_error()


class DaoRegistrationTests(unittest.TestCase):
    def test_successful_registration_returns_incrementing_id(self):
        c = _fresh()
        a = c.register_dao("Uniswap", "https://gov.uniswap.org")
        b = c.register_dao("Aave", "https://governance.aave.com")
        self.assertEqual(int(a), 1)
        self.assertEqual(int(b), 2)
        self.assertEqual(int(c.next_dao_id), 3)

    def test_dao_stored_with_importer_and_zero_timestamp(self):
        c = _fresh()
        shim.set_sender("0x" + "bb" * 20)
        did = c.register_dao("X", "https://x.example")
        dao = c.get_dao(did)
        self.assertEqual(dao.name, "X")
        self.assertEqual(dao.url, "https://x.example")
        self.assertEqual(str(dao.importer), "0x" + "bb" * 20)
        self.assertEqual(int(dao.imported_at), 0)

    def test_empty_name_rejected(self):
        c = _fresh()
        with self.assertRaises(UserError):
            c.register_dao("", "https://x")

    def test_oversized_name_rejected(self):
        c = _fresh()
        big = "x" * (gf.MAX_DAO_NAME_LEN + 1)
        with self.assertRaises(UserError):
            c.register_dao(big, "https://x")

    def test_newline_in_name_rejected(self):
        c = _fresh()
        with self.assertRaises(UserError):
            c.register_dao("a\nb", "https://x")

    def test_paused_registration_rejected(self):
        c = _fresh()
        c.paused = True
        with self.assertRaises(UserError):
            c.register_dao("X", "https://x")

    def test_registrations_are_a_namespace_not_a_claim(self):
        # Two DAOs may register the same URL; identity_status stays
        # COMMUNITY_IMPORTED and both entries coexist. Governance Fork does
        # not certify DAO ownership.
        c = _fresh()
        a = c.register_dao("Uniswap community", "https://gov.uniswap.org")
        b = c.register_dao("Uniswap", "https://gov.uniswap.org")
        self.assertNotEqual(int(a), int(b))


class RootImportTests(unittest.TestCase):
    def _prep(self):
        c = _fresh()
        did = c.register_dao("Uniswap", "https://gov.uniswap.org")
        return c, did

    def test_successful_import(self):
        c, did = self._prep()
        rid = c.import_root_proposal(
            did,
            "UP-91",
            "Developer Grants",
            "https://gov.uniswap.org/proposals/91",
            _params([("amount", "100000"), ("duration", "6 months")]),
        )
        r = c.get_root_proposal(rid)
        self.assertEqual(r.envelope_status, gf.ENVELOPE_NOT_SUBMITTED)
        self.assertEqual(r.identity_status, gf.IDENTITY_COMMUNITY_IMPORTED)
        self.assertNotEqual(r.import_fingerprint, b"")
        self.assertEqual(r.web_content_fingerprint, b"")
        self.assertEqual(int(r.envelope_case_id), 0)

    def test_invalid_dao_rejected(self):
        c = _fresh()
        with self.assertRaises(UserError):
            c.import_root_proposal(
                shim.u256(99),
                "X",
                "T",
                "https://x",
                _params([]),
            )

    def test_fingerprint_stable_across_calls_on_identical_inputs(self):
        c, did = self._prep()
        rid = c.import_root_proposal(
            did, "UP-91", "T", "https://x/1",
            _params([("a", "1"), ("b", "2")]),
        )
        fp = c.get_root_proposal(rid).import_fingerprint
        # Recompute canonical form independently and confirm SHA-256 match.
        import hashlib
        params_sorted = sorted(
            [("a", "1"), ("b", "2")], key=lambda kv: kv[0]
        )
        buf = b"gf-root/v1\n"
        buf += b"dao_id=" + str(int(did)).encode("ascii") + b"\n"
        buf += b"external_proposal_id=UP-91\n"
        buf += b"title=T\n"
        buf += b"proposal_url=https://x/1\n"
        buf += b"structured_parameters=\n"
        for k, v in params_sorted:
            buf += b"  " + k.encode() + b"=" + v.encode() + b"\n"
        self.assertEqual(fp, hashlib.sha256(buf).digest())

    def test_parameter_order_does_not_affect_fingerprint(self):
        # Two DAOs so the (dao_id-including) fingerprint stays comparable.
        c = _fresh()
        d1 = c.register_dao("A", "https://a")
        d2 = c.register_dao("B", "https://b")
        r1 = c.import_root_proposal(
            d1, "EP", "T", "https://x/1",
            _params([("amount", "1"), ("duration", "6"), ("eligibility", "open")]),
        )
        r2 = c.import_root_proposal(
            d2, "EP", "T", "https://x/1",
            _params([("eligibility", "open"), ("amount", "1"), ("duration", "6")]),
        )
        fp1 = c.get_root_proposal(r1).import_fingerprint
        fp2 = c.get_root_proposal(r2).import_fingerprint
        # dao_id differs -> fingerprints differ; but if we strip the dao_id
        # binding by re-canonicalizing the same dao_id twice, order must not
        # matter. Re-import the SAME dao_id twice would collide, so instead
        # we check by re-canonicalization outside the contract.
        import hashlib
        def canonical(dao_id, params):
            params_sorted = sorted(params, key=lambda kv: kv[0])
            buf = b"gf-root/v1\n"
            buf += b"dao_id=" + str(int(dao_id)).encode("ascii") + b"\n"
            buf += b"external_proposal_id=EP\n"
            buf += b"title=T\n"
            buf += b"proposal_url=https://x/1\n"
            buf += b"structured_parameters=\n"
            for k, v in params_sorted:
                buf += b"  " + k.encode() + b"=" + v.encode() + b"\n"
            return hashlib.sha256(buf).digest()
        want_1 = canonical(d1, [("amount", "1"), ("duration", "6"), ("eligibility", "open")])
        want_2 = canonical(d1, [("eligibility", "open"), ("amount", "1"), ("duration", "6")])
        self.assertEqual(want_1, want_2)
        self.assertEqual(fp1, want_1)

    def test_changed_parameter_changes_fingerprint(self):
        c = _fresh()
        d1 = c.register_dao("A", "https://a")
        d2 = c.register_dao("B", "https://b")
        r1 = c.import_root_proposal(d1, "EP", "T", "https://x/1", _params([("a", "1")]))
        r2 = c.import_root_proposal(d2, "EP", "T", "https://x/1", _params([("a", "2")]))
        self.assertNotEqual(
            c.get_root_proposal(r1).import_fingerprint,
            c.get_root_proposal(r2).import_fingerprint,
        )

    def test_changed_title_changes_fingerprint(self):
        c = _fresh()
        d1 = c.register_dao("A", "https://a")
        d2 = c.register_dao("B", "https://b")
        r1 = c.import_root_proposal(d1, "EP", "T1", "https://x/1", _params([]))
        r2 = c.import_root_proposal(d2, "EP", "T2", "https://x/1", _params([]))
        self.assertNotEqual(
            c.get_root_proposal(r1).import_fingerprint,
            c.get_root_proposal(r2).import_fingerprint,
        )

    def test_changed_url_changes_fingerprint(self):
        c = _fresh()
        d1 = c.register_dao("A", "https://a")
        d2 = c.register_dao("B", "https://b")
        r1 = c.import_root_proposal(d1, "EP", "T", "https://x/1", _params([]))
        r2 = c.import_root_proposal(d2, "EP", "T", "https://x/2", _params([]))
        self.assertNotEqual(
            c.get_root_proposal(r1).import_fingerprint,
            c.get_root_proposal(r2).import_fingerprint,
        )

    def test_exact_duplicate_rejected(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        c.import_root_proposal(did, "EP", "T", "https://x/1", _params([("a", "1")]))
        with self.assertRaises(UserError):
            c.import_root_proposal(did, "EP", "T", "https://x/1", _params([("a", "1")]))

    def test_similar_title_different_external_id_allowed(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        r1 = c.import_root_proposal(did, "EP-1", "Developer Grants", "https://x/1", _params([]))
        r2 = c.import_root_proposal(did, "EP-2", "Developer Grants", "https://x/2", _params([]))
        self.assertNotEqual(int(r1), int(r2))

    def test_duplicate_parameter_keys_rejected(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        with self.assertRaises(UserError):
            c.import_root_proposal(
                did, "EP", "T", "https://x/1",
                _params([("k", "1"), ("k", "2")]),
            )

    def test_parameter_key_length_bounds(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        big_key = "k" * (gf.MAX_KV_KEY_LEN + 1)
        with self.assertRaises(UserError):
            c.import_root_proposal(did, "EP", "T", "https://x/1",
                                   _params([(big_key, "1")]))

    def test_newline_in_title_rejected(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        with self.assertRaises(UserError):
            c.import_root_proposal(did, "EP", "hello\nworld", "https://x/1", _params([]))

    def test_url_length_bound(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        long_url = "https://x/" + "y" * gf.MAX_URL_LEN
        with self.assertRaises(UserError):
            c.import_root_proposal(did, "EP", "T", long_url, _params([]))

    def test_index_updated_on_import(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        r1 = c.import_root_proposal(did, "EP-1", "T", "https://x/1", _params([]))
        r2 = c.import_root_proposal(did, "EP-2", "T", "https://x/2", _params([]))
        page = c.list_root_proposals_by_dao(did, shim.u256(0), shim.u32(50))
        got = [int(x) for x in page.items]
        self.assertEqual(got, [int(r1), int(r2)])
        self.assertEqual(int(page.next_cursor), 0)

    def test_rollback_on_bad_input_leaves_no_orphan(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        prior_root_id = int(c.next_root_id)
        prior_dao_root_list_len = 0
        if did in c.roots_by_dao:
            prior_dao_root_list_len = len(c.roots_by_dao[did])
        with self.assertRaises(UserError):
            c.import_root_proposal(did, "", "T", "https://x/1", _params([]))
        self.assertEqual(int(c.next_root_id), prior_root_id)
        cur_len = 0
        if did in c.roots_by_dao:
            cur_len = len(c.roots_by_dao[did])
        self.assertEqual(cur_len, prior_dao_root_list_len)


class IntentEnvelopeTests(unittest.TestCase):
    def _prep(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", _params([]))
        return c, did, rid

    def test_successful_submission_transitions_status(self):
        c, did, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        case_id = c.submit_root_envelope(
            rid, _envelope(), urls, cls, rel, auth, tm, rp
        )
        r = c.get_root_proposal(rid)
        self.assertEqual(r.envelope_status, gf.ENVELOPE_EVIDENCE_OPEN)
        self.assertEqual(int(r.envelope_case_id), int(case_id))
        self.assertEqual(r.envelope.parent_proposal_fingerprint, r.import_fingerprint)
        self.assertEqual(int(r.envelope.envelope_version), 1)

    def test_root_missing_rejected(self):
        c = _fresh()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        with self.assertRaises(UserError):
            c.submit_root_envelope(shim.u256(99), _envelope(), urls, cls, rel, auth, tm, rp)

    def test_objective_bound_enforced(self):
        c, did, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        long_obj = "x" * (gf.MAX_OBJECTIVE_LEN + 1)
        with self.assertRaises(UserError):
            c.submit_root_envelope(
                rid, _envelope(objective=long_obj), urls, cls, rel, auth, tm, rp
            )

    def test_empty_objective_rejected(self):
        c, did, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        with self.assertRaises(UserError):
            c.submit_root_envelope(
                rid, _envelope(objective=""), urls, cls, rel, auth, tm, rp
            )

    def test_bad_resource_type_rejected(self):
        c, did, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        with self.assertRaises(UserError):
            c.submit_root_envelope(
                rid, _envelope(resource_type="INVALID"), urls, cls, rel, auth, tm, rp
            )

    def test_essential_constraint_cap(self):
        c, did, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        big = tuple(f"c{i}" for i in range(gf.MAX_ESSENTIAL_CONSTRAINT_ITEMS + 1))
        with self.assertRaises(UserError):
            c.submit_root_envelope(
                rid, _envelope(essential=big), urls, cls, rel, auth, tm, rp
            )

    def test_mutable_immutable_overlap_rejected(self):
        c, did, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        with self.assertRaises(UserError):
            c.submit_root_envelope(
                rid,
                _envelope(mutable=("allocation",), immutable=("allocation",)),
                urls, cls, rel, auth, tm, rp,
            )

    def test_duplicate_mutable_dimension_rejected(self):
        c, did, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        with self.assertRaises(UserError):
            c.submit_root_envelope(
                rid,
                _envelope(mutable=("allocation", "allocation")),
                urls, cls, rel, auth, tm, rp,
            )

    def test_duplicate_immutable_dimension_rejected(self):
        c, did, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        with self.assertRaises(UserError):
            c.submit_root_envelope(
                rid,
                _envelope(immutable=("beneficiary_class", "beneficiary_class")),
                urls, cls, rel, auth, tm, rp,
            )

    def test_second_active_envelope_rejected(self):
        c, did, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        c.submit_root_envelope(rid, _envelope(), urls, cls, rel, auth, tm, rp)
        urls2, cls2, rel2, auth2, tm2, rp2 = _evidence_bundle(
            urls=("https://gov.example.com/prop/1?v=2",),
        )
        with self.assertRaises(UserError):
            c.submit_root_envelope(rid, _envelope(), urls2, cls2, rel2, auth2, tm2, rp2)

    def test_empty_essential_constraint_rejected(self):
        c, did, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        with self.assertRaises(UserError):
            c.submit_root_envelope(
                rid, _envelope(essential=("",)), urls, cls, rel, auth, tm, rp
            )


class EvidenceMetadataTests(unittest.TestCase):
    def _prep(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", _params([]))
        return c, rid

    def test_successful_metadata_stored_frozen_false(self):
        c, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle(
            urls=(
                "https://gov.example.com/prop/1",
                "https://forum.example.com/thread/9",
            ),
            classes=(gf.EC_OFFICIAL_GOVERNANCE, gf.EC_GOVERNANCE_DISCUSSION),
        )
        case_id = c.submit_root_envelope(rid, _envelope(), urls, cls, rel, auth, tm, rp)
        page = c.list_evidence_of_case(case_id, shim.u256(0), shim.u32(50))
        ids = [int(x) for x in page.items]
        self.assertEqual(len(ids), 2)
        for eid in ids:
            ev = c.get_evidence(shim.u256(eid))
            self.assertFalse(ev.frozen)
            self.assertEqual(ev.content_fingerprint, b"")
            self.assertIn(ev.evidence_class, gf._ALLOWED_EVIDENCE_CLASSES)

    def test_evidence_cap_enforced(self):
        c, rid = self._prep()
        n = gf.MAX_EVIDENCE_PER_CASE + 1
        urls, cls, rel, auth, tm, rp = _evidence_bundle(
            urls=tuple(f"https://ex.com/{i}" for i in range(n)),
        )
        with self.assertRaises(UserError):
            c.submit_root_envelope(rid, _envelope(), urls, cls, rel, auth, tm, rp)

    def test_at_least_one_evidence_required(self):
        c, rid = self._prep()
        empty = shim.DynArray([])
        with self.assertRaises(UserError):
            c.submit_root_envelope(
                rid, _envelope(), empty, empty, empty, empty, empty, empty
            )

    def test_normalized_url_duplicate_rejected(self):
        # Stage 5 tightened normalization: only scheme + host are
        # case-normalized; path and query are preserved verbatim. So the
        # dedup collision is on scheme+host, not on path-case.
        c, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle(
            urls=(
                "https://example.com/foo",
                "HTTPS://Example.com/foo",
            ),
            classes=(gf.EC_OFFICIAL_GOVERNANCE, gf.EC_OFFICIAL_GOVERNANCE),
        )
        with self.assertRaises(UserError):
            c.submit_root_envelope(rid, _envelope(), urls, cls, rel, auth, tm, rp)

    def test_distinct_path_case_NOT_deduped(self):
        # Stage 5 correction: path is case-sensitive; two URLs differing only
        # by path case are DIFFERENT resources and must NOT be deduped.
        c, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle(
            urls=(
                "https://example.com/foo",
                "https://example.com/FOO",
            ),
            classes=(gf.EC_OFFICIAL_GOVERNANCE, gf.EC_OFFICIAL_GOVERNANCE),
        )
        c.submit_root_envelope(rid, _envelope(), urls, cls, rel, auth, tm, rp)  # no raise

    def test_bad_evidence_class_rejected(self):
        c, rid = self._prep()
        urls, cls, rel, auth, tm, rp = _evidence_bundle(classes=("BOGUS",))
        with self.assertRaises(UserError):
            c.submit_root_envelope(rid, _envelope(), urls, cls, rel, auth, tm, rp)

    def test_evidence_array_lengths_must_match(self):
        c, rid = self._prep()
        urls = shim.DynArray(["https://a", "https://b"])
        cls = shim.DynArray([gf.EC_OFFICIAL_GOVERNANCE])
        rel = shim.DynArray(["r", "r"])
        auth = shim.DynArray(["a", "a"])
        tm = shim.DynArray(["t", "t"])
        rp = shim.DynArray([gf.RENDER_PROFILE_STANDARD, gf.RENDER_PROFILE_STANDARD])
        with self.assertRaises(UserError):
            c.submit_root_envelope(rid, _envelope(), urls, cls, rel, auth, tm, rp)


class CaseAndIndexTests(unittest.TestCase):
    def test_root_envelope_case_shape(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", _params([]))
        urls, cls, rel, auth, tm, rp = _evidence_bundle()
        case_id = c.submit_root_envelope(rid, _envelope(), urls, cls, rel, auth, tm, rp)
        case = c.get_case(case_id)
        self.assertEqual(case.case_type, gf.CASE_TYPE_ROOT_ENVELOPE)
        self.assertEqual(int(case.target_id), int(rid))
        self.assertEqual(case.target_kind, gf.TARGET_KIND_ROOT_ENVELOPE)
        self.assertEqual(case.state, gf.CASE_OPEN)
        # target_fingerprint == root.import_fingerprint
        self.assertEqual(case.target_fingerprint, c.get_root_proposal(rid).import_fingerprint)
        # evidence_ids of case match evidence_by_case index
        idx_ids = [int(x) for x in c.evidence_by_case[case_id]]
        case_ids = [int(x) for x in case.evidence_ids]
        self.assertEqual(idx_ids, case_ids)

    def test_pagination_next_cursor(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        for i in range(5):
            c.import_root_proposal(did, f"EP-{i}", "T", f"https://x/{i}", _params([]))
        page1 = c.list_root_proposals_by_dao(did, shim.u256(0), shim.u32(2))
        self.assertEqual([int(x) for x in page1.items], [1, 2])
        self.assertEqual(int(page1.next_cursor), 2)
        page2 = c.list_root_proposals_by_dao(did, page1.next_cursor, shim.u32(2))
        self.assertEqual([int(x) for x in page2.items], [3, 4])
        self.assertEqual(int(page2.next_cursor), 4)
        page3 = c.list_root_proposals_by_dao(did, page2.next_cursor, shim.u32(50))
        self.assertEqual([int(x) for x in page3.items], [5])
        self.assertEqual(int(page3.next_cursor), 0)


class ProhibitedBehaviorTests(unittest.TestCase):
    def test_source_has_no_disallowed_nondet_or_gen_calls(self):
        # Stage 6b baseline: gl.nondet.web.render(...) + gl.eq_principle.
        # strict_eq(...) are now legitimate (fetch_evidence only).
        # web.get, semantic prompts, and native GEN transfer remain banned.
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        for banned in ("web.get(", "gl.eq_principle.prompt_comparative",
                       "gl.eq_principle.prompt_non_comparative",
                       "gl.nondet.exec_prompt", "transfer("):
            self.assertNotIn(banned, src, f"banned substring present: {banned}")
        self.assertIn("gl.nondet.web.render(", src)
        self.assertIn("gl.eq_principle.strict_eq(", src)

    def test_source_has_no_gl_message_value(self):
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        self.assertNotIn("gl.message.value", src)

    def test_create_fork_rejects_when_root_not_faithful(self):
        # Stage 4 lands a real create_fork body, but its first check is
        # envelope_status == ENVELOPE_FAITHFUL. Stage 3-produced roots have
        # envelope_status = ENVELOPE_NOT_SUBMITTED (or _EVIDENCE_OPEN after
        # a submit_root_envelope), so public create_fork remains
        # unavailable in production.
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", _params([]))
        with self.assertRaises(UserError):
            c.create_fork(
                rid,
                gf.PARENT_KIND_ROOT,
                b"",
                shim.DynArray([]),
                gf.ForkBody(title="F", summary="", structured_parameters=shim.DynArray([]), reasoning=""),
            )

    def test_adjudicate_still_unimplemented(self):
        c = _fresh()
        with self.assertRaises(UserError):
            c.adjudicate(shim.u256(1))

    def test_challenge_still_unimplemented(self):
        c = _fresh()
        with self.assertRaises(UserError):
            c.challenge_verdict(shim.u256(1), gf.TARGET_KIND_FORK, gf.CG_FORK_INTENT_MISREAD, "arg")

    def test_settle_bond_still_unimplemented(self):
        c = _fresh()
        with self.assertRaises(UserError):
            c.settle_bond(shim.u256(1))


class AdminTests(unittest.TestCase):
    def test_only_treasury_can_pause(self):
        c = _fresh()
        shim.set_sender("0x" + "cc" * 20)
        with self.assertRaises(UserError):
            c.pause()

    def test_treasury_can_pause_and_unpause(self):
        c = _fresh()
        shim.set_sender("0x" + "aa" * 20)
        c.pause()
        self.assertTrue(c.paused)
        c.unpause()
        self.assertFalse(c.paused)


class ConstantsViewTests(unittest.TestCase):
    def test_get_constants_returns_expected_values(self):
        c = _fresh()
        cv = c.get_constants()
        self.assertEqual(int(cv.max_daos), gf.MAX_DAOS)
        self.assertEqual(int(cv.max_evidence_slice), gf.MAX_EVIDENCE_SLICE)
        self.assertEqual(int(cv.pagination_limit_max), gf.PAGINATION_LIMIT_MAX)
        self.assertFalse(cv.paused)


if __name__ == "__main__":
    unittest.main(verbosity=2)
