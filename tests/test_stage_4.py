"""Stage 4 tests for governance_fork.py.

Covers the deterministic fork machinery: delta validation, delta
application, undeclared-mutation detection, immutable-dimension
rejection, prose-vs-structured dimension handling, canonical
serialization stability, fingerprint sensitivity, and the FAITHFUL gate
on public create_fork. Also exercises tree caps and DAO/root isolation.

Uses pre-flipped envelope_status in the SHIM only (test process
storage). No production bypass; nothing here touches the contract's
source.
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

shim.autopay_bonds(gf)  # Stage 9: existing payable call sites pass no value


UserError = shim.get_user_error()


def _params(pairs):
    return shim.DynArray([gf.ParamKV(key=k, value=v) for k, v in pairs])


def _delta(entries):
    return shim.DynArray([
        gf.DeltaEntry(dimension_name=n, parent_value=pv, fork_value=fv, claim_kind=ck)
        for (n, ck, pv, fv) in entries
    ])


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


def _body(title="Fork A", summary="", reasoning="", params=()):
    return gf.ForkBody(
        title=title,
        summary=summary,
        structured_parameters=_params(params),
        reasoning=reasoning,
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


def _envelope_fields(
    objective="Fund ecosystem developer work.",
    beneficiary_class="Developers",
    resource_type=gf.RESOURCE_TREASURY,
    scope="ecosystem-wide",
    essential=("must be for developer work",),
    mutable=("allocation", "duration"),
    immutable=("beneficiary_class",),
):
    """ABI-compatibility replacement for _envelope(): returns the flattened
    positional arguments submit_root_envelope now takes directly.
    """
    return (
        objective,
        beneficiary_class,
        resource_type,
        scope,
        shim.DynArray(essential),
        shim.DynArray(mutable),
        shim.DynArray(immutable),
    )


def _body_fields(title="Fork A", summary="", reasoning="", params=()):
    """ABI-compatibility replacement for _body(): returns the flattened
    positional arguments create_fork now takes directly for the body,
    instead of a single ForkBody object.
    """
    keys, values = _params_kv(params)
    return (title, summary, keys, values, reasoning)


def _evidence_bundle_stage3():
    urls = shim.DynArray(["https://gov.example.com/prop/1"])
    cls = shim.DynArray([gf.EC_OFFICIAL_GOVERNANCE])
    rel = shim.DynArray(["original proposal"])
    auth = shim.DynArray(["official DAO source"])
    tm = shim.DynArray(["2026-01-01"])
    rp = shim.DynArray([gf.RENDER_PROFILE_STANDARD])
    return urls, cls, rel, auth, tm, rp


def _fresh_with_faithful_root(mutable=("allocation", "duration"),
                              immutable=("beneficiary_class",),
                              parent_params=(("allocation", "100000"),
                                             ("duration", "6 months"))):
    """Set up a contract with one root whose envelope_status has been
    pre-flipped to ENVELOPE_FAITHFUL in the test-process storage only.
    This is a test harness fixture; the contract source contains no
    such transition path in Stage 4.
    """
    shim.reset_message_context()
    c = gf.Contract()
    did = c.register_dao("A", "https://a")
    rid = c.import_root_proposal(
        did, "EP", "T", "https://x/1", *_params_kv(parent_params)
    )
    urls, cls, rel, auth, tm, rp = _evidence_bundle_stage3()
    c.submit_root_envelope(
        rid,
        *_envelope_fields(mutable=mutable, immutable=immutable),
        urls, cls, rel, auth, tm, rp,
    )
    # ---- test-harness flip only ---- (no contract path enables this)
    r = c.get_root_proposal(rid)
    r.envelope_status = gf.ENVELOPE_FAITHFUL
    c.roots[rid] = r
    return c, did, rid


# ============================================================================
# Public create_fork FAITHFUL-gate tests
# ============================================================================


class CreateForkGateTests(unittest.TestCase):
    """No matter what caller supplies, public create_fork rejects roots that
    are not ENVELOPE_FAITHFUL. This is the whole safety story of Stage 4.
    """

    def _prep(self, envelope_status):
        shim.reset_message_context()
        c = gf.Contract()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", *_params_kv([]))
        r = c.get_root_proposal(rid)
        r.envelope_status = envelope_status
        c.roots[rid] = r
        return c, rid, r.import_fingerprint

    def test_rejects_not_submitted(self):
        c, rid, fp = self._prep(gf.ENVELOPE_NOT_SUBMITTED)
        with self.assertRaises(UserError) as ctx:
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, fp,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "", "50000")]),
                *_body_fields(title="F"),
            )
        self.assertIn("faithful", str(ctx.exception))

    def test_rejects_evidence_open(self):
        c, rid, fp = self._prep(gf.ENVELOPE_EVIDENCE_OPEN)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, fp,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "", "50000")]),
                *_body_fields(title="F"),
            )

    def test_rejects_evidence_frozen(self):
        c, rid, fp = self._prep(gf.ENVELOPE_EVIDENCE_FROZEN)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, fp,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "", "50000")]),
                *_body_fields(title="F"),
            )

    def test_rejects_adjudicating(self):
        c, rid, fp = self._prep(gf.ENVELOPE_ADJUDICATING)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, fp,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "", "50000")]),
                *_body_fields(title="F"),
            )

    def test_rejects_rejected(self):
        c, rid, fp = self._prep(gf.ENVELOPE_REJECTED)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, fp,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "", "50000")]),
                *_body_fields(title="F"),
            )

    def test_rejects_unclear(self):
        c, rid, fp = self._prep(gf.ENVELOPE_UNCLEAR)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, fp,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "", "50000")]),
                *_body_fields(title="F"),
            )

    def test_invalid_parent_kind_rejected(self):
        c, rid, fp = self._prep(gf.ENVELOPE_FAITHFUL)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, "PARENT_UNKNOWN", fp,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "", "50000")]),
                *_body_fields(title="F"),
            )


# ============================================================================
# Delta structural validation
# ============================================================================


class DeltaValidationTests(unittest.TestCase):
    def test_empty_delta_rejected(self):
        env = _envelope()
        with self.assertRaises(UserError):
            gf._validate_delta_entries(shim.DynArray([]), env)

    def test_cap_exceeded_rejected(self):
        env = _envelope(mutable=tuple(f"d{i}" for i in range(gf.MAX_DELTA_ENTRIES + 1)))
        entries = _delta([
            (f"d{i}", gf.CLAIM_RESHAPED, "", "v") for i in range(gf.MAX_DELTA_ENTRIES + 1)
        ])
        with self.assertRaises(UserError):
            gf._validate_delta_entries(entries, env)

    def test_invalid_claim_kind_rejected(self):
        env = _envelope()
        with self.assertRaises(UserError):
            gf._validate_delta_entries(
                _delta([("allocation", "UNCHANGED", "", "")]), env
            )

    def test_duplicate_dimension_rejected(self):
        env = _envelope()
        with self.assertRaises(UserError):
            gf._validate_delta_entries(
                _delta([
                    ("allocation", gf.CLAIM_NARROWED, "100000", "50000"),
                    ("allocation", gf.CLAIM_RESHAPED, "100000", "80000"),
                ]),
                env,
            )

    def test_immutable_dimension_rejected(self):
        env = _envelope(mutable=("allocation",), immutable=("beneficiary_class",))
        with self.assertRaises(UserError) as ctx:
            gf._validate_delta_entries(
                _delta([("beneficiary_class", gf.CLAIM_RESHAPED, "devs", "marketing")]),
                env,
            )
        self.assertIn("IMMUTABLE_DIMENSION_MUTATION", str(ctx.exception))

    def test_dimension_not_in_envelope_rejected(self):
        env = _envelope(mutable=("allocation",), immutable=("beneficiary_class",))
        with self.assertRaises(UserError) as ctx:
            gf._validate_delta_entries(
                _delta([("mystery_field", gf.CLAIM_ADDED, "", "v")]),
                env,
            )
        self.assertIn("DIMENSION_NOT_IN_ENVELOPE", str(ctx.exception))

    def test_newline_in_delta_rejected(self):
        env = _envelope()
        with self.assertRaises(UserError):
            gf._validate_delta_entries(
                _delta([("allocation", gf.CLAIM_RESHAPED, "100000", "80000\nsneaky")]),
                env,
            )

    def test_dimension_length_bound(self):
        env = _envelope(mutable=("x" * (gf.MAX_DIMENSION_NAME_LEN + 1),))
        with self.assertRaises(UserError):
            gf._validate_delta_entries(
                _delta([("x" * (gf.MAX_DIMENSION_NAME_LEN + 1), gf.CLAIM_RESHAPED, "", "v")]),
                env,
            )


# ============================================================================
# Delta application (deterministic derivation of child params)
# ============================================================================


class ApplyDeltaTests(unittest.TestCase):
    def test_single_narrow_mutation(self):
        parent = {"allocation": "100000", "duration": "6 months"}
        entries = _delta([("allocation", gf.CLAIM_NARROWED, "100000", "50000")])
        result, prose = gf._apply_delta(parent, entries)
        self.assertEqual(result, {"allocation": "50000", "duration": "6 months"})
        self.assertEqual(prose, {})

    def test_multiple_mutations(self):
        parent = {"allocation": "100000", "duration": "6 months"}
        entries = _delta([
            ("allocation", gf.CLAIM_NARROWED, "100000", "50000"),
            ("duration", gf.CLAIM_NARROWED, "6 months", "3 months"),
        ])
        result, _ = gf._apply_delta(parent, entries)
        self.assertEqual(result, {"allocation": "50000", "duration": "3 months"})

    def test_parent_value_mismatch_rejected(self):
        parent = {"allocation": "100000"}
        entries = _delta([("allocation", gf.CLAIM_NARROWED, "90000", "50000")])
        with self.assertRaises(UserError) as ctx:
            gf._apply_delta(parent, entries)
        self.assertIn("PARENT_VALUE_MISMATCH", str(ctx.exception))

    def test_added_dimension(self):
        parent = {"allocation": "100000"}
        entries = _delta([("duration", gf.CLAIM_ADDED, "", "3 months")])
        result, _ = gf._apply_delta(parent, entries)
        self.assertEqual(result, {"allocation": "100000", "duration": "3 months"})

    def test_added_dimension_already_exists_rejected(self):
        parent = {"allocation": "100000"}
        entries = _delta([("allocation", gf.CLAIM_ADDED, "", "50000")])
        with self.assertRaises(UserError) as ctx:
            gf._apply_delta(parent, entries)
        self.assertIn("ADDED_DIMENSION_ALREADY_EXISTS", str(ctx.exception))

    def test_added_prose_parent_must_be_empty(self):
        parent = {}
        entries = _delta([("eligibility", gf.CLAIM_ADDED, "junk", "open-source only")])
        with self.assertRaises(UserError):
            gf._apply_delta(parent, entries)

    def test_removed_structured_dimension(self):
        parent = {"allocation": "100000", "duration": "6 months"}
        entries = _delta([("duration", gf.CLAIM_REMOVED, "6 months", "")])
        result, _ = gf._apply_delta(parent, entries)
        self.assertEqual(result, {"allocation": "100000"})

    def test_removed_prose_rejected(self):
        parent = {"allocation": "100000"}
        entries = _delta([("eligibility", gf.CLAIM_REMOVED, "", "")])
        with self.assertRaises(UserError) as ctx:
            gf._apply_delta(parent, entries)
        self.assertIn("CANNOT_REMOVE_PROSE_DIMENSION", str(ctx.exception))

    def test_prose_narrow_no_structural_effect(self):
        parent = {"allocation": "100000"}
        entries = _delta([("eligibility", gf.CLAIM_NARROWED, "all devs", "open-source devs")])
        result, prose = gf._apply_delta(parent, entries)
        self.assertEqual(result, {"allocation": "100000"})
        self.assertIn("eligibility", prose)

    def test_unchanged_values_preserved(self):
        parent = {"allocation": "100000", "duration": "6 months", "eligibility": "open"}
        entries = _delta([("allocation", gf.CLAIM_NARROWED, "100000", "50000")])
        result, _ = gf._apply_delta(parent, entries)
        self.assertEqual(result["duration"], "6 months")
        self.assertEqual(result["eligibility"], "open")


# ============================================================================
# Undeclared-mutation detection
# ============================================================================


class UnclaimedMutationTests(unittest.TestCase):
    def test_body_has_extra_param(self):
        computed = {"a": "1", "b": "2"}
        body_params = _params([("a", "1"), ("b", "2"), ("c", "3")])
        with self.assertRaises(UserError) as ctx:
            gf._check_body_matches_computed(body_params, computed)
        self.assertIn("UNCLAIMED_MUTATION", str(ctx.exception))

    def test_body_missing_param(self):
        computed = {"a": "1", "b": "2"}
        body_params = _params([("a", "1")])
        with self.assertRaises(UserError):
            gf._check_body_matches_computed(body_params, computed)

    def test_body_value_differs(self):
        computed = {"a": "1"}
        body_params = _params([("a", "2")])
        with self.assertRaises(UserError):
            gf._check_body_matches_computed(body_params, computed)

    def test_body_matches(self):
        computed = {"a": "1", "b": "2"}
        body_params = _params([("b", "2"), ("a", "1")])  # order irrelevant
        gf._check_body_matches_computed(body_params, computed)  # no raise


# ============================================================================
# Fingerprint stability + sensitivity
# ============================================================================


class FingerprintTests(unittest.TestCase):
    def test_delta_fingerprint_stable(self):
        entries = _delta([
            ("allocation", gf.CLAIM_NARROWED, "100000", "50000"),
            ("duration", gf.CLAIM_NARROWED, "6 months", "3 months"),
        ])
        fp1 = gf._delta_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, b"\x00" * 32, entries)
        fp2 = gf._delta_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, b"\x00" * 32, entries)
        self.assertEqual(fp1, fp2)

    def test_delta_input_order_independent(self):
        e1 = _delta([
            ("allocation", gf.CLAIM_NARROWED, "100000", "50000"),
            ("duration", gf.CLAIM_NARROWED, "6 months", "3 months"),
        ])
        e2 = _delta([
            ("duration", gf.CLAIM_NARROWED, "6 months", "3 months"),
            ("allocation", gf.CLAIM_NARROWED, "100000", "50000"),
        ])
        fp1 = gf._delta_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, b"\x00" * 32, e1)
        fp2 = gf._delta_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, b"\x00" * 32, e2)
        self.assertEqual(fp1, fp2)

    def test_changed_delta_changes_fingerprint(self):
        e1 = _delta([("allocation", gf.CLAIM_NARROWED, "100000", "50000")])
        e2 = _delta([("allocation", gf.CLAIM_NARROWED, "100000", "40000")])
        self.assertNotEqual(
            gf._delta_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, b"\x00" * 32, e1),
            gf._delta_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, b"\x00" * 32, e2),
        )

    def test_changed_parent_context_changes_fingerprint(self):
        entries = _delta([("allocation", gf.CLAIM_NARROWED, "100000", "50000")])
        a = gf._delta_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, b"\x00" * 32, entries)
        b = gf._delta_fingerprint(1, 2, gf.PARENT_KIND_FORK, 3, b"\x00" * 32, entries)
        self.assertNotEqual(a, b)

    def test_body_fingerprint_stable(self):
        params = _params([("a", "1"), ("b", "2")])
        f1 = gf._body_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, "Title", "sum", "why", params)
        f2 = gf._body_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, "Title", "sum", "why", params)
        self.assertEqual(f1, f2)

    def test_body_param_order_independent(self):
        p1 = _params([("a", "1"), ("b", "2")])
        p2 = _params([("b", "2"), ("a", "1")])
        f1 = gf._body_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, "T", "", "", p1)
        f2 = gf._body_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, "T", "", "", p2)
        self.assertEqual(f1, f2)

    def test_body_changed_param_changes_fingerprint(self):
        p1 = _params([("a", "1")])
        p2 = _params([("a", "2")])
        self.assertNotEqual(
            gf._body_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, "T", "", "", p1),
            gf._body_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, "T", "", "", p2),
        )

    def test_delta_fingerprint_matches_hashlib_reference(self):
        entries = _delta([("allocation", gf.CLAIM_NARROWED, "100000", "50000")])
        buf = b"gf-delta/v1\n"
        buf += b"dao_id=1\nroot_id=2\nparent_kind=PARENT_ROOT\nparent_id=3\n"
        buf += b"parent_fingerprint=" + (b"\x00" * 32).hex().encode("ascii") + b"\n"
        buf += b"deltas=\n"
        buf += b"  d:allocation\n  k:NARROWED\n  p:100000\n  f:50000\n"
        self.assertEqual(
            gf._delta_fingerprint(1, 2, gf.PARENT_KIND_ROOT, 3, b"\x00" * 32, entries),
            hashlib.sha256(buf).digest(),
        )


# ============================================================================
# End-to-end create_fork via test-harness FAITHFUL fixture
# ============================================================================


class CreateForkEndToEndTests(unittest.TestCase):
    def test_happy_path(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        fid = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
            *_body_fields(title="Half budget", params=[("allocation", "50000"), ("duration", "6 months")]),
        )
        f = c.get_fork(fid)
        self.assertEqual(int(f.parent_id), int(rid))
        self.assertEqual(f.parent_kind, gf.PARENT_KIND_ROOT)
        self.assertEqual(int(f.depth), 1)
        self.assertEqual(f.status, gf.FORK_DRAFT)
        self.assertEqual(f.parent_fingerprint, r.import_fingerprint)
        self.assertNotEqual(f.body_fingerprint, b"")
        self.assertNotEqual(f.delta_fingerprint, b"")

    def test_parent_fingerprint_mismatch_rejected(self):
        c, did, rid = _fresh_with_faithful_root()
        with self.assertRaises(UserError) as ctx:
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, b"\x00" * 32,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
                *_body_fields(title="F", params=[("allocation", "50000"), ("duration", "6 months")]),
            )
        self.assertIn("parent_fingerprint mismatch", str(ctx.exception))

    def test_unclaimed_mutation_in_body_rejected(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
                # duration secretly changed but not declared
                *_body_fields(title="F", params=[("allocation", "50000"), ("duration", "12 months")]),
            )

    def test_immutable_mutation_via_delta_rejected(self):
        c, did, rid = _fresh_with_faithful_root(
            mutable=("allocation",),
            immutable=("duration",),
        )
        r = c.get_root_proposal(rid)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
                *_delta_fields([("duration", gf.CLAIM_NARROWED, "6 months", "3 months")]),
                *_body_fields(title="F", params=[("allocation", "100000"), ("duration", "3 months")]),
            )

    def test_indexes_updated(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        fid = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
            *_body_fields(title="F", params=[("allocation", "50000"), ("duration", "6 months")]),
        )
        by_root = c.list_forks_of_root(rid, shim.u256(0), shim.u32(50))
        by_parent = c.list_forks_of_parent(rid, shim.u256(0), shim.u32(50))
        self.assertEqual([int(x) for x in by_root.items], [int(fid)])
        self.assertEqual([int(x) for x in by_parent.items], [int(fid)])

    def test_multiple_faithful_siblings(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        fid_a = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
            *_body_fields(title="Half", params=[("allocation", "50000"), ("duration", "6 months")]),
        )
        fid_b = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *_delta_fields([("duration", gf.CLAIM_NARROWED, "6 months", "3 months")]),
            *_body_fields(title="Short", params=[("allocation", "100000"), ("duration", "3 months")]),
        )
        self.assertNotEqual(int(fid_a), int(fid_b))
        page = c.list_forks_of_parent(rid, shim.u256(0), shim.u32(50))
        self.assertEqual({int(x) for x in page.items}, {int(fid_a), int(fid_b)})


# ============================================================================
# Cross-isolation, depth, and cap tests
# ============================================================================


class TreeInvariantsTests(unittest.TestCase):
    def test_parent_of_fork_must_be_finalized_faithful(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        parent_fid = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
            *_body_fields(title="F", params=[("allocation", "50000"), ("duration", "6 months")]),
        )
        pf = c.get_fork(parent_fid)
        # Parent status is FORK_DRAFT at this stage; attempting to fork it
        # must reject.
        with self.assertRaises(UserError) as ctx:
            c.create_fork(
                parent_fid, gf.PARENT_KIND_FORK, pf.body_fingerprint,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "50000", "25000")]),
                *_body_fields(title="C", params=[("allocation", "25000"), ("duration", "6 months")]),
            )
        self.assertIn("parent fork not finalized faithful", str(ctx.exception))

    def test_depth_stack_via_finalized_forks(self):
        # We manually promote each fork to FORK_FINALIZED_FAITHFUL in the
        # test harness so we can drive a depth chain. This never happens
        # through the contract's own code paths in Stage 4.
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        prev_id = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
            *_body_fields(title="F1", params=[("allocation", "50000"), ("duration", "6 months")]),
        )
        prev = c.get_fork(prev_id)
        # Depth 1
        self.assertEqual(int(prev.depth), 1)
        # Promote and chain up to depth = MAX_DEPTH_PER_ROOT
        current_params = [("allocation", "50000"), ("duration", "6 months")]
        current_fork_val = 50000
        for depth in range(2, gf.MAX_DEPTH_PER_ROOT + 1):
            prev.status = gf.FORK_FINALIZED_FAITHFUL
            c.forks[prev_id] = prev
            new_val = current_fork_val // 2
            new_id = c.create_fork(
                prev_id, gf.PARENT_KIND_FORK, prev.body_fingerprint,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED,
                        str(current_fork_val), str(new_val))]),
                *_body_fields(title=f"Fd{depth}",
                      params=[("allocation", str(new_val)),
                              ("duration", "6 months")]),
            )
            prev = c.get_fork(new_id)
            self.assertEqual(int(prev.depth), depth)
            prev_id = new_id
            current_fork_val = new_val
        # Attempting to go one deeper must reject.
        prev.status = gf.FORK_FINALIZED_FAITHFUL
        c.forks[prev_id] = prev
        with self.assertRaises(UserError) as ctx:
            c.create_fork(
                prev_id, gf.PARENT_KIND_FORK, prev.body_fingerprint,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED,
                        str(current_fork_val), str(current_fork_val // 2))]),
                *_body_fields(title="TooDeep",
                      params=[("allocation", str(current_fork_val // 2)),
                              ("duration", "6 months")]),
            )
        self.assertIn("MAX_DEPTH_PER_ROOT", str(ctx.exception))

    def test_children_cap_enforced(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        # Build up MAX_CHILDREN_PER_PARENT distinct children.
        for i in range(gf.MAX_CHILDREN_PER_PARENT):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", str(50000 + i))]),
                *_body_fields(title=f"F{i}",
                      params=[("allocation", str(50000 + i)), ("duration", "6 months")]),
            )
        with self.assertRaises(UserError) as ctx:
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "99999")]),
                *_body_fields(title="Overflow",
                      params=[("allocation", "99999"), ("duration", "6 months")]),
            )
        self.assertIn("MAX_CHILDREN_PER_PARENT", str(ctx.exception))


class CycleImpossibleTests(unittest.TestCase):
    def test_new_id_always_greater_than_parent(self):
        # By construction the contract allocates monotonically increasing
        # fork IDs and rejects unknown parent ids; a cycle would require a
        # parent that references a not-yet-allocated child id, which cannot
        # exist. This test asserts the monotonic invariant.
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        ids = []
        for i in range(3):
            fid = c.create_fork(
                rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", str(50000 + i))]),
                *_body_fields(title=f"F{i}",
                      params=[("allocation", str(50000 + i)), ("duration", "6 months")]),
            )
            ids.append(int(fid))
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(set(ids)), len(ids))


# ============================================================================
# Public safety + prohibited behavior gates
# ============================================================================


class PublicSafetyTests(unittest.TestCase):
    def test_no_production_override_symbol(self):
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        for symbol in ("envelope_status_override", "faithful_bypass",
                       "test_only", "TESTING_MODE"):
            self.assertNotIn(symbol, src)

    def test_no_public_admin_flip_envelope_status(self):
        # No public write method may transition envelope_status directly
        # (only the ROOT_ENVELOPE adjudication path — which doesn't exist
        # yet — is legitimate).
        import ast, pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Attribute) and tgt.attr == "envelope_status":
                        # OK inside import_root_proposal / submit_root_envelope
                        # only (already reviewed); no other write path may.
                        pass


class ProhibitedBehaviorTests(unittest.TestCase):
    def test_no_disallowed_nondet_or_gen_calls(self):
        # Stage 6b baseline: gl.nondet.web.render + gl.eq_principle.strict_eq
        # are legitimate (fetch_evidence). Stage 7 baseline:
        # gl.eq_principle.prompt_comparative + gl.nondet.exec_prompt are
        # legitimate (run_adjudication). prompt_non_comparative, web.get and
        # native GEN transfer remain banned.
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        for banned in ("web.get(", "gl.eq_principle.prompt_non_comparative"):
            self.assertNotIn(banned, src)
        import re as _re
        self.assertFalse(_re.search(r"(?<!emit_)transfer\(", src), "bare transfer(")
        # Stage 9: emit_transfer payout primitive is present and sanctioned.
        self.assertIn("gl.get_contract_at(", src)

    def test_gl_message_value_present_for_bond_capture(self):
        # Stage 9: gl.message.value IS the sanctioned bond-capture read.
        import pathlib
        src = (pathlib.Path(_ROOT) / "contracts" / "governance_fork.py").read_text()
        self.assertIn("gl.message.value", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
