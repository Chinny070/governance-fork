"""Focused ABI compatibility tests for the DynArray/dataclass-input
runtime correction to import_root_proposal, submit_root_envelope, and
create_fork.

These tests specifically cover the scenarios the correction's live-runtime
finding made newly important -- our previous live testing only ever
exercised structured_parameters as an EMPTY array; these tests exercise
the POPULATED case that the correction must actually get right, plus the
new atomic-rejection behavior for mismatched parallel arrays, plus a
direct fingerprint-equivalence check proving the transport change did not
alter any canonical business data.

LOCAL LOGIC TESTS ONLY -- like the rest of this suite, these run against
the Python test shim, not the live GenVM runtime. Item I (no public
write/admin/view input remains dataclass-typed) is a static/source-shape
check, not a runtime unittest -- see tests/stage_2_checks.py's
"no dataclass-typed public inputs" check.
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


def _fresh():
    shim.reset_message_context()
    return gf.Contract()


def _params_kv(pairs):
    return (
        shim.DynArray([k for k, v in pairs]),
        shim.DynArray([v for k, v in pairs]),
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
    return (
        objective,
        beneficiary_class,
        resource_type,
        scope,
        shim.DynArray(essential),
        shim.DynArray(mutable),
        shim.DynArray(immutable),
    )


def _delta_fields(entries):
    return (
        shim.DynArray([n for (n, ck, pv, fv) in entries]),
        shim.DynArray([pv for (n, ck, pv, fv) in entries]),
        shim.DynArray([fv for (n, ck, pv, fv) in entries]),
        shim.DynArray([ck for (n, ck, pv, fv) in entries]),
    )


def _body_fields(title="Fork A", summary="", reasoning="", params=()):
    keys, values = _params_kv(params)
    return (title, summary, keys, values, reasoning)


def _root_evidence_bundle():
    return (
        shim.DynArray(["https://gov.example.com/prop/1"]),
        shim.DynArray([gf.EC_OFFICIAL_GOVERNANCE]),
        shim.DynArray(["original proposal"]),
        shim.DynArray(["official DAO source"]),
        shim.DynArray(["2026-01-01"]),
        shim.DynArray([gf.RENDER_PROFILE_STANDARD]),
    )


def _fresh_with_faithful_root(mutable=("allocation", "duration"),
                              immutable=("beneficiary_class",),
                              parent_params=(("allocation", "100000"),
                                             ("duration", "6 months"))):
    """Test-harness fixture (matches test_stage_4.py's pattern): a FAITHFUL
    root reached only via a test-process-only envelope_status flip. No
    production path enables this; it exists so create_fork can be
    exercised at all before Stage 7 implements real adjudication.
    """
    c = _fresh()
    did = c.register_dao("A", "https://a")
    rid = c.import_root_proposal(
        did, "EP", "T", "https://x/1", *_params_kv(parent_params)
    )
    urls, cls, rel, auth, tm, rp = _root_evidence_bundle()
    c.submit_root_envelope(rid, *_envelope_fields(mutable=mutable, immutable=immutable), urls, cls, rel, auth, tm, rp)
    r = c.get_root_proposal(rid)
    r.envelope_status = gf.ENVELOPE_FAITHFUL  # test-harness flip only
    c.roots[rid] = r
    return c, did, rid


# ============================================================================
# A. import_root_proposal with POPULATED structured parameters
# ============================================================================


class PopulatedStructuredParametersTests(unittest.TestCase):
    def test_populated_structured_parameters_stored_correctly(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        pairs = [("allocation", "100000"), ("duration", "6 months"), ("eligibility", "open")]
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", *_params_kv(pairs))
        r = c.get_root_proposal(rid)
        stored = [(kv.key, kv.value) for kv in r.structured_parameters]
        # Original submission order is preserved (canonical sort is a
        # fingerprint-only concern, per the pre-existing contract comment).
        self.assertEqual(stored, pairs)

    def test_populated_structured_parameters_reject_duplicate_keys(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        with self.assertRaises(UserError):
            c.import_root_proposal(
                did, "EP", "T", "https://x/1",
                *_params_kv([("a", "1"), ("a", "2")]),
            )

    def test_populated_structured_parameters_respect_max_cap(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        too_many = [(f"k{i}", "v") for i in range(gf.MAX_STRUCTURED_PARAMS + 1)]
        with self.assertRaises(UserError):
            c.import_root_proposal(did, "EP", "T", "https://x/1", *_params_kv(too_many))


# ============================================================================
# B. mismatched structured_parameter_keys/values -> atomic rejection
# ============================================================================


class MismatchedStructuredParametersTests(unittest.TestCase):
    def test_mismatched_lengths_rejected(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        keys = shim.DynArray(["a", "b"])
        values = shim.DynArray(["1"])
        with self.assertRaises(UserError):
            c.import_root_proposal(did, "EP", "T", "https://x/1", keys, values)

    def test_mismatched_lengths_rejection_is_atomic(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        next_id_before = int(c.next_root_id)
        keys = shim.DynArray(["a", "b", "c"])
        values = shim.DynArray(["1"])
        with self.assertRaises(UserError):
            c.import_root_proposal(did, "EP", "T", "https://x/1", keys, values)
        self.assertEqual(int(c.next_root_id), next_id_before)


# ============================================================================
# C. submit_root_envelope with populated essential/mutable/immutable arrays
# ============================================================================


class PopulatedEnvelopeArraysTests(unittest.TestCase):
    def test_populated_envelope_arrays_stored_correctly(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", *_params_kv([]))
        urls, cls, rel, auth, tm, rp = _root_evidence_bundle()
        essential = ("must serve developers", "must be time-bounded")
        mutable = ("allocation", "duration", "eligibility")
        immutable = ("beneficiary_class", "resource_type")
        c.submit_root_envelope(
            rid,
            *_envelope_fields(essential=essential, mutable=mutable, immutable=immutable),
            urls, cls, rel, auth, tm, rp,
        )
        r = c.get_root_proposal(rid)
        self.assertEqual(list(r.envelope.essential_constraints), list(essential))
        self.assertEqual(list(r.envelope.mutable_dimensions), list(mutable))
        self.assertEqual(list(r.envelope.immutable_dimensions), list(immutable))
        # Server-derived fields remain server-derived, never caller-controlled.
        self.assertEqual(r.envelope.parent_proposal_fingerprint, r.import_fingerprint)
        self.assertEqual(int(r.envelope.envelope_version), 1)


# ============================================================================
# D. create_fork with multiple populated DeltaEntry records
# ============================================================================


class PopulatedDeltaTests(unittest.TestCase):
    def test_multiple_delta_entries_stored_correctly(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        entries = [
            ("allocation", gf.CLAIM_NARROWED, "100000", "50000"),
            ("duration", gf.CLAIM_NARROWED, "6 months", "3 months"),
        ]
        fid = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *_delta_fields(entries),
            *_body_fields(title="F", params=[("allocation", "50000"), ("duration", "3 months")]),
        )
        f = c.get_fork(fid)
        stored = [(d.dimension_name, d.claim_kind, d.parent_value, d.fork_value) for d in f.delta]
        self.assertEqual(stored, entries)


# ============================================================================
# E. create_fork with populated ForkBody structured parameters
# ============================================================================


class PopulatedForkBodyTests(unittest.TestCase):
    def test_populated_body_structured_parameters_stored_correctly(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        body_params = [("allocation", "50000"), ("duration", "6 months")]
        fid = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
            *_body_fields(title="F", params=body_params),
        )
        f = c.get_fork(fid)
        stored = [(kv.key, kv.value) for kv in f.body.structured_parameters]
        self.assertEqual(stored, body_params)


# ============================================================================
# F. mismatched delta parallel arrays -> rejection
# ============================================================================


class MismatchedDeltaArraysTests(unittest.TestCase):
    def test_mismatched_delta_arrays_rejected(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        next_id_before = int(c.next_fork_id)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
                shim.DynArray(["allocation", "duration"]),
                shim.DynArray(["100000"]),
                shim.DynArray(["50000", "3 months"]),
                shim.DynArray([gf.CLAIM_NARROWED, gf.CLAIM_NARROWED]),
                *_body_fields(),
            )
        self.assertEqual(int(c.next_fork_id), next_id_before)


# ============================================================================
# G. mismatched ForkBody parameter key/value arrays -> rejection
# ============================================================================


class MismatchedForkBodyArraysTests(unittest.TestCase):
    def test_mismatched_body_param_arrays_rejected(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        next_id_before = int(c.next_fork_id)
        with self.assertRaises(UserError):
            c.create_fork(
                rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
                *_delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
                "F", "",
                shim.DynArray(["allocation", "duration"]),
                shim.DynArray(["50000"]),
                "",
            )
        self.assertEqual(int(c.next_fork_id), next_id_before)


# ============================================================================
# H. Reconstructed objects produce the same canonical bytes/fingerprints as
#    equivalent directly-constructed internal dataclass objects
# ============================================================================


class FingerprintEquivalenceTests(unittest.TestCase):
    def test_import_fingerprint_matches_direct_canonicalization(self):
        c = _fresh()
        did = c.register_dao("A", "https://a")
        pairs = [("b", "2"), ("a", "1")]
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", *_params_kv(pairs))
        r = c.get_root_proposal(rid)

        # Directly construct the internal dataclass objects the OLD ABI
        # would have received, and compute the fingerprint via the exact
        # same (unchanged) canonicalization path the contract itself uses.
        direct_params = [gf.ParamKV(key=k, value=v) for k, v in pairs]
        params_sorted = sorted(direct_params, key=lambda kv: kv.key)
        canonical = gf._canonicalize_root(int(did), "EP", "T", "https://x/1", params_sorted)
        expected_fp = gf._sha256(canonical)
        self.assertEqual(r.import_fingerprint, expected_fp)

    def test_fork_body_and_delta_fingerprints_match_direct_construction(self):
        c, did, rid = _fresh_with_faithful_root()
        r = c.get_root_proposal(rid)
        entries = [("allocation", gf.CLAIM_NARROWED, "100000", "50000")]
        body_params = [("allocation", "50000"), ("duration", "6 months")]
        fid = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *_delta_fields(entries),
            *_body_fields(title="F", params=body_params),
        )
        f = c.get_fork(fid)

        direct_delta = [
            gf.DeltaEntry(dimension_name=n, parent_value=pv, fork_value=fv, claim_kind=ck)
            for (n, ck, pv, fv) in entries
        ]
        direct_body_params = [gf.ParamKV(key=k, value=v) for k, v in body_params]

        expected_delta_fp = gf._delta_fingerprint(
            int(f.dao_id), int(f.root_id), gf.PARENT_KIND_ROOT, int(rid),
            r.import_fingerprint, direct_delta,
        )
        expected_body_fp = gf._body_fingerprint(
            int(f.dao_id), int(f.root_id), gf.PARENT_KIND_ROOT, int(rid),
            "F", "", "", direct_body_params,
        )
        self.assertEqual(f.delta_fingerprint, expected_delta_fp)
        self.assertEqual(f.body_fingerprint, expected_body_fp)


if __name__ == "__main__":
    unittest.main()
