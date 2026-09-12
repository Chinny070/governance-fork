"""Stage 8 tests for governance_fork.py -- challenge + finality.

LOCAL LOGIC TESTS ONLY. The one semantic call (reused Stage 7
run_adjudication) is mocked via tests/_genlayer_shim.py's
_MockSemanticRegistry. Everything else in Stage 8 is a deterministic
state machine and is exercised directly. No GEN economics in Stage 8.
"""

from __future__ import annotations

import json
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
import test_stage_6b as h  # noqa: E402
import test_stage_7 as s7  # noqa: E402

UserError = shim.get_user_error()

_USEFUL = s7._USEFUL


def _mk_root_output(case_id, overrides=None):
    return s7._mk_output(case_id, gf.ADJ_SCHEMA_ROOT, gf._RE_DIMS, overrides, 1)


def _mk_fork_output(case_id, eid, overrides=None):
    return s7._mk_output(case_id, gf.ADJ_SCHEMA_FORK, gf._FORK_DIMS, overrides, eid)


# ---------------------------------------------------------------------------
# reach: root/fork with a committed initial verdict, pre-finality
# ---------------------------------------------------------------------------

def _root_with_verdict(overrides=None):
    c, rid, case_id, eids = s7._seal_root()
    c.adjudicate(case_id)
    shim.get_mock_semantic().set_default(_mk_root_output(case_id, overrides))
    c.run_adjudication(case_id)
    shim.get_mock_semantic().reset()
    return c, rid, case_id, eids


def _fork_with_verdict(overrides=None):
    c, rid, fid, case_id, creator, eids = s7._seal_fork()
    shim.set_sender(creator)
    c.adjudicate(case_id)
    shim.get_mock_semantic().set_default(_mk_fork_output(case_id, eids[0], overrides))
    c.run_adjudication(case_id)
    shim.get_mock_semantic().reset()
    shim.reset_message_context()
    return c, rid, fid, case_id, creator, eids


_RE_NOT_FAITHFUL = {gf.RE_DIM_SCOPE_FIDELITY: gf.FINDING_NOT_SATISFIED}


# ===========================================================================
# challenge_verdict validation
# ===========================================================================

class ChallengeValidationTests(unittest.TestCase):
    def test_unknown_target_kind(self):
        c, rid, case_id, eids = _root_with_verdict()
        with self.assertRaises(UserError):
            c.challenge_verdict(rid, "NOPE", gf.CG_RE_SCOPE_MISCHARACTERIZED, "x")

    def test_target_not_found(self):
        c, rid, case_id, eids = _root_with_verdict()
        with self.assertRaises(UserError):
            c.challenge_verdict(shim.u256(999), gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_SCOPE_MISCHARACTERIZED, "x")

    def test_no_verdict_yet(self):
        c, rid, case_id, eids = s7._seal_root()
        c.adjudicate(case_id)  # armed but not run
        with self.assertRaises(UserError):
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_SCOPE_MISCHARACTERIZED, "arg")

    def test_bad_ground_code(self):
        c, rid, case_id, eids = _root_with_verdict()
        with self.assertRaises(UserError):
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_FORK_INTENT_MISREAD, "wrong enum for kind")

    def test_empty_argument(self):
        c, rid, case_id, eids = _root_with_verdict()
        with self.assertRaises(UserError):
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_SCOPE_MISCHARACTERIZED, "")

    def test_oversized_argument(self):
        c, rid, case_id, eids = _root_with_verdict()
        with self.assertRaises(UserError):
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_SCOPE_MISCHARACTERIZED,
                                "x" * (gf.MAX_CHALLENGE_ARG_LEN + 1))

    def test_newline_argument(self):
        c, rid, case_id, eids = _root_with_verdict()
        with self.assertRaises(UserError):
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_SCOPE_MISCHARACTERIZED, "line\nbreak")

    def test_one_open_at_a_time(self):
        c, rid, case_id, eids = _root_with_verdict()
        c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                            gf.CG_RE_SCOPE_MISCHARACTERIZED, "first")
        with self.assertRaises(UserError):
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_OBJECTIVE_MISREPRESENTED, "second while open")

    def test_paused_blocks_challenge(self):
        c, rid, case_id, eids = _root_with_verdict()
        c.pause()
        with self.assertRaises(UserError):
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_SCOPE_MISCHARACTERIZED, "x")

    def test_max_challenges_bound(self):
        c, rid, case_id, eids = _root_with_verdict()
        for i in range(gf.MAX_CHALLENGES_PER_TARGET):
            ch_case = c.next_case_id
            cid = c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                      gf.CG_RE_SCOPE_MISCHARACTERIZED, "attempt %d" % i)
            # resolve it UNCHANGED so the next may open
            shim.set_sender(shim.get_gl().message.sender_address)
            c.adjudicate(ch_case)
            shim.get_mock_semantic().set_default(_mk_root_output(ch_case))
            c.run_adjudication(ch_case)
            shim.get_mock_semantic().reset()
        with self.assertRaises(UserError):
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_SCOPE_MISCHARACTERIZED, "one too many")


# ===========================================================================
# challenge lifecycle
# ===========================================================================

class ChallengeLifecycleTests(unittest.TestCase):
    def _open(self, c, rid):
        ch_case = c.next_case_id
        cid = c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                  gf.CG_RE_SCOPE_MISCHARACTERIZED, "the scope is wrong")
        return cid, ch_case

    def test_open_sets_state(self):
        c, rid, case_id, eids = _root_with_verdict()
        cid, ch_case = self._open(c, rid)
        ch = c.get_challenge(cid)
        self.assertEqual(ch.status, gf.CHALLENGE_OPEN)
        self.assertEqual(int(ch.case_id), int(ch_case))
        self.assertEqual(c.get_case(ch_case).state, gf.CASE_CASE_FROZEN)
        self.assertEqual(c.get_case(ch_case).case_type, gf.CASE_TYPE_CHALLENGE)
        self.assertEqual(int(c.get_case(ch_case).challenge_id), int(cid))
        self.assertEqual(c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_CHALLENGE_OPEN)
        # cloned frozen inputs
        oc = c.get_case(case_id)
        cc = c.get_case(ch_case)
        self.assertEqual(cc.evidence_set_fingerprint, oc.evidence_set_fingerprint)
        self.assertEqual(list(cc.evidence_ids), list(oc.evidence_ids))

    def test_arm_requires_challenger(self):
        c, rid, case_id, eids = _root_with_verdict()
        cid, ch_case = self._open(c, rid)
        shim.set_sender(shim.Address("0x" + "77" * 20))
        with self.assertRaises(UserError):
            c.adjudicate(ch_case)

    def test_unchanged_resolution(self):
        c, rid, case_id, eids = _root_with_verdict()
        orig_vid = c.get_root_proposal(rid).current_verdict_id
        cid, ch_case = self._open(c, rid)
        c.adjudicate(ch_case)
        self.assertEqual(c.get_challenge(cid).status, gf.CHALLENGE_ADJUDICATING)
        shim.get_mock_semantic().set_default(_mk_root_output(ch_case))  # all SATISFIED -> FAITHFUL, same
        c.run_adjudication(ch_case)
        ch = c.get_challenge(cid)
        self.assertEqual(ch.status, gf.CHALLENGE_RESOLVED_UNCHANGED)
        self.assertNotEqual(int(ch.replacement_verdict_id), 0)
        # governing verdict unchanged; original.replaced_by set; history grew
        self.assertEqual(int(c.get_root_proposal(rid).current_verdict_id), int(orig_vid))
        self.assertEqual(int(c.get_verdict(orig_vid).replaced_by), int(ch.replacement_verdict_id))
        hist = c.get_verdict_history(rid, gf.TARGET_KIND_ROOT_ENVELOPE, shim.u256(0), shim.u32(10))
        self.assertEqual(len(hist.items), 2)
        self.assertEqual(c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_ADJUDICATING)

    def test_flipped_resolution_moves_pointer(self):
        c, rid, case_id, eids = _root_with_verdict()
        orig_vid = c.get_root_proposal(rid).current_verdict_id
        cid, ch_case = self._open(c, rid)
        c.adjudicate(ch_case)
        shim.get_mock_semantic().set_default(_mk_root_output(ch_case, _RE_NOT_FAITHFUL))
        c.run_adjudication(ch_case)
        ch = c.get_challenge(cid)
        self.assertEqual(ch.status, gf.CHALLENGE_RESOLVED_FLIPPED)
        self.assertEqual(int(c.get_root_proposal(rid).current_verdict_id),
                         int(ch.replacement_verdict_id))
        self.assertEqual(c.get_verdict(ch.replacement_verdict_id).verdict, gf.VERDICT_NOT_FAITHFUL)

    def test_unclear_replacement(self):
        c, rid, case_id, eids = _root_with_verdict()
        orig_vid = c.get_root_proposal(rid).current_verdict_id
        cid, ch_case = self._open(c, rid)
        c.adjudicate(ch_case)
        shim.get_mock_semantic().set_default(
            _mk_root_output(ch_case, {gf.RE_DIM_EVIDENCE_SUPPORT: gf.FINDING_UNCLEAR})
        )
        c.run_adjudication(ch_case)
        ch = c.get_challenge(cid)
        self.assertEqual(ch.status, gf.CHALLENGE_RESOLVED_UNCLEAR)
        self.assertEqual(int(c.get_root_proposal(rid).current_verdict_id), int(orig_vid))

    def test_challenge_undetermined_then_exhaust(self):
        c, rid, case_id, eids = _root_with_verdict()
        cid, ch_case = self._open(c, rid)
        for _ in range(gf.MAX_RETRIES_PER_CASE):
            c.adjudicate(ch_case)
            shim.get_mock_semantic().set_undetermined(True)
            with self.assertRaises(Exception):
                c.run_adjudication(ch_case)
            shim.get_mock_semantic().reset()
        c.adjudicate(ch_case)  # exhausted -> terminal
        self.assertEqual(c.get_case(ch_case).state, gf.CASE_UNDETERMINED_TERMINAL)
        self.assertEqual(c.get_challenge(cid).status, gf.CHALLENGE_RESOLVED_UNCLEAR)
        self.assertEqual(c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_ADJUDICATING)

    def test_fingerprint_mismatch_aborts_challenge(self):
        c, rid, case_id, eids = _root_with_verdict()
        cid, ch_case = self._open(c, rid)
        c.adjudicate(ch_case)
        ev = c.evidence[eids[0]]
        ev.content_fingerprint = b"\x01" * 32
        c.evidence[eids[0]] = ev
        shim.get_mock_semantic().set_default(_mk_root_output(ch_case))
        with self.assertRaises(UserError):
            c.run_adjudication(ch_case)

    def test_challenge_run_not_paused_gated(self):
        c, rid, case_id, eids = _root_with_verdict()
        cid, ch_case = self._open(c, rid)
        c.adjudicate(ch_case)
        c.pause()
        shim.get_mock_semantic().set_default(_mk_root_output(ch_case))
        c.run_adjudication(ch_case)
        self.assertEqual(c.get_challenge(cid).status, gf.CHALLENGE_RESOLVED_UNCHANGED)


# ===========================================================================
# finalize
# ===========================================================================

class FinalizeTests(unittest.TestCase):
    # Stage 10 (steward-requested): finalize() is now a two-step commit --
    # open_finality_window() (owner-gated, same forced-finality escape the
    # original single-step finalize had) then finalize() (permissionless,
    # requires the window already open). The preconditions that used to
    # live in finalize() (verdict exists, no open challenge, owner-or-
    # forced-finality) now gate open_finality_window() instead, since
    # that's the step where they're still meaningfully reachable.

    def test_open_window_needs_verdict(self):
        c, rid, case_id, eids = s7._seal_root()
        c.adjudicate(case_id)
        with self.assertRaises(UserError):
            c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)

    def test_open_window_blocked_by_open_challenge(self):
        c, rid, case_id, eids = _root_with_verdict()
        c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                            gf.CG_RE_SCOPE_MISCHARACTERIZED, "pending")
        with self.assertRaises(UserError):
            c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)

    def test_open_window_requires_owner(self):
        c, rid, case_id, eids = _root_with_verdict()
        shim.set_sender(shim.Address("0x" + "99" * 20))
        with self.assertRaises(UserError):
            c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)

    def test_finalize_without_open_window_rejected(self):
        # The single-transaction race the steward flagged: finalize() can
        # no longer run in the same breath as the verdict landing.
        c, rid, case_id, eids = _root_with_verdict()
        with self.assertRaises(UserError):
            c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)

    def test_double_open_window_rejected(self):
        c, rid, case_id, eids = _root_with_verdict()
        c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        with self.assertRaises(UserError):
            c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)

    def test_challenge_after_open_window_blocks_finalize(self):
        # The actual fix: a challenge landing in the gap between
        # open_finality_window and finalize must be seen and honoured.
        c, rid, case_id, eids = _root_with_verdict()
        c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        self.assertEqual(
            c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_CHALLENGE_WINDOW
        )
        c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                            gf.CG_RE_SCOPE_MISCHARACTERIZED, "caught it")
        self.assertEqual(
            c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_CHALLENGE_OPEN
        )
        with self.assertRaises(UserError):
            c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)

    def test_finalize_faithful_root_then_forkable(self):
        c, rid, case_id, eids = _root_with_verdict()
        c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        self.assertEqual(c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_FAITHFUL)
        r = c.get_root_proposal(rid)
        creator = shim.Address("0x" + "cc" * 20)
        shim.set_sender(creator)
        fid = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *h._delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
            *h._body_fields(params=(("allocation", "50000"),)),
        )
        self.assertIn(fid, [x for x in c.list_forks_of_root(rid, shim.u256(0), shim.u32(10)).items])

    def test_finalize_not_faithful_fork(self):
        c, rid, fid, case_id, creator, eids = _fork_with_verdict(
            {gf.FORK_DIM_UNDECLARED_SEMANTIC_CHANGE: gf.FINDING_NOT_SATISFIED}
        )
        shim.set_sender(creator)
        c.open_finality_window(fid, gf.TARGET_KIND_FORK)
        c.finalize(fid, gf.TARGET_KIND_FORK)
        self.assertEqual(c.get_fork(fid).status, gf.FORK_FINALIZED_NOT_FAITHFUL)

    def test_double_finalize_rejected(self):
        c, rid, case_id, eids = _root_with_verdict()
        c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        with self.assertRaises(UserError):
            c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        with self.assertRaises(UserError):
            c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)

    def test_finalized_root_not_challengeable(self):
        c, rid, case_id, eids = _root_with_verdict()
        c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        with self.assertRaises(UserError):
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_SCOPE_MISCHARACTERIZED, "too late")

    def test_forced_finality_after_exhausted_challenges(self):
        c, rid, case_id, eids = _root_with_verdict()
        for i in range(gf.MAX_CHALLENGES_PER_TARGET):
            ch_case = c.next_case_id
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_SCOPE_MISCHARACTERIZED, "n%d" % i)
            c.adjudicate(ch_case)
            shim.get_mock_semantic().set_default(_mk_root_output(ch_case))
            c.run_adjudication(ch_case)
            shim.get_mock_semantic().reset()
        # non-owner can now force the finality window open, then anyone
        # (permissionless) may finalize.
        shim.set_sender(shim.Address("0x" + "42" * 20))
        c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        self.assertEqual(c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_FAITHFUL)

    def test_finalized_fork_child_eligibility(self):
        c, rid, fid, case_id, creator, eids = _fork_with_verdict()
        shim.set_sender(creator)
        c.open_finality_window(fid, gf.TARGET_KIND_FORK)
        c.finalize(fid, gf.TARGET_KIND_FORK)
        self.assertEqual(c.get_fork(fid).status, gf.FORK_FINALIZED_FAITHFUL)
        parent = c.get_fork(fid)
        child_creator = shim.Address("0x" + "ab" * 20)
        shim.set_sender(child_creator)
        child = c.create_fork(
            fid, gf.PARENT_KIND_FORK, parent.body_fingerprint,
            *h._delta_fields([("allocation", gf.CLAIM_NARROWED, "50000", "25000")]),
            *h._body_fields(title="Child fork",
                            params=(("allocation", "25000"), ("duration", "6 months"))),
        )
        self.assertEqual(int(c.get_fork(child).parent_id), int(fid))
        self.assertEqual(int(c.get_fork(child).depth), int(parent.depth) + 1)
        self.assertEqual(c.get_fork(child).parent_kind, gf.PARENT_KIND_FORK)


class RegressionTests(unittest.TestCase):
    def test_stage7_faithful_still_not_forkable_pre_finalize(self):
        c, rid, case_id, eids = _root_with_verdict()
        r = c.get_root_proposal(rid)
        self.assertEqual(r.envelope_status, gf.ENVELOPE_ADJUDICATING)
        shim.set_sender(shim.Address("0x" + "cc" * 20))
        with self.assertRaises(UserError):
            c.create_fork(rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
                          *h._delta_fields([("allocation", gf.CLAIM_NARROWED, "1x", "2x")]),
                          *h._body_fields())

    def test_list_challenges_pagination(self):
        c, rid, case_id, eids = _root_with_verdict()
        page = c.list_challenges(rid, gf.TARGET_KIND_ROOT_ENVELOPE, shim.u256(0), shim.u32(10))
        self.assertEqual(list(page.items), [])
        c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                            gf.CG_RE_SCOPE_MISCHARACTERIZED, "one")
        page = c.list_challenges(rid, gf.TARGET_KIND_ROOT_ENVELOPE, shim.u256(0), shim.u32(10))
        self.assertEqual(len(page.items), 1)


if __name__ == "__main__":
    unittest.main()
