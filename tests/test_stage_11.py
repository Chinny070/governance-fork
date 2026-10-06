"""Stage 11 tests -- adoption signalling, creator reputation, escalated appeal.

LOCAL LOGIC TESTS ONLY (mock clock + mock semantic registry from the shim).
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

shim.autopay_bonds(gf)
import test_stage_6b as h  # noqa: E402
import test_stage_8 as s8  # noqa: E402

UserError = shim.get_user_error()

PROPOSER = shim.Address("0x" + "aa" * 20)


def _root_with_two_faithful_forks():
    """FAITHFUL root plus two finalized-FAITHFUL forks (harness flips for the
    statuses -- the real verdict/finalize paths are covered in stages 7-10)."""
    c = h._fresh()
    shim.reset_message_context()
    did = c.register_dao("A", "https://a")
    rid = c.import_root_proposal(
        did, "EP", "T", "https://x/1", *h._params_kv([("allocation", "100000")])
    )
    c.submit_root_envelope(
        rid, *h._envelope_fields(), *h._evidence_arrays(("https://x/1",))
    )
    r = c.get_root_proposal(rid)
    r.envelope_status = gf.ENVELOPE_FAITHFUL
    c.roots[rid] = r

    fids, creators = [], []
    for i, amt in enumerate(("50000", "40000")):
        creator = shim.Address("0x" + ("c%d" % (i + 1)) * 20)
        shim.set_sender(creator)
        fid = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *h._delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", amt)]),
            *h._body_fields(title="Fork %d" % i, params=(("allocation", amt),)),
        )
        f = c.get_fork(fid)
        f.status = gf.FORK_FINALIZED_FAITHFUL
        c.forks[fid] = f
        fids.append(fid)
        creators.append(creator)
    shim.reset_message_context()
    return c, rid, fids, creators


class AdoptionTests(unittest.TestCase):
    def test_open_requires_faithful_root_and_proposer(self):
        c, rid, fids, _ = _root_with_two_faithful_forks()
        shim.set_sender(shim.Address("0x" + "99" * 20))
        with self.assertRaises(UserError):
            c.open_adoption(rid)
        shim.reset_message_context()
        r = c.get_root_proposal(rid)
        r.envelope_status = gf.ENVELOPE_ADJUDICATING
        c.roots[rid] = r
        with self.assertRaises(UserError):
            c.open_adoption(rid)

    def test_signal_requires_open_adoption(self):
        c, rid, fids, _ = _root_with_two_faithful_forks()
        with self.assertRaises(UserError):
            c.signal_adoption(fids[0])

    def test_double_open_rejected(self):
        c, rid, fids, _ = _root_with_two_faithful_forks()
        c.open_adoption(rid)
        with self.assertRaises(UserError):
            c.open_adoption(rid)

    def test_signal_only_for_finalized_faithful_fork(self):
        c, rid, fids, _ = _root_with_two_faithful_forks()
        c.open_adoption(rid)
        f = c.get_fork(fids[1])
        f.status = gf.FORK_FINALIZED_NOT_FAITHFUL
        c.forks[fids[1]] = f
        with self.assertRaises(UserError):
            c.signal_adoption(fids[1])

    def test_full_adoption_flow_and_reputation(self):
        c, rid, fids, creators = _root_with_two_faithful_forks()
        c.open_adoption(rid)
        info = c.get_adoption(rid)
        self.assertGreater(int(info.opened_at), 0)
        self.assertFalse(info.closed)

        voters = [shim.Address("0x" + ("%02x" % (0x10 + i)) * 20) for i in range(3)]
        shim.set_sender(voters[0])
        c.signal_adoption(fids[0])
        shim.set_sender(voters[1])
        c.signal_adoption(fids[1])
        shim.set_sender(voters[2])
        c.signal_adoption(fids[1])
        self.assertEqual(int(c.get_fork_signal_count(fids[0])), 1)
        self.assertEqual(int(c.get_fork_signal_count(fids[1])), 2)

        # same address, same fork twice -> rejected; moving a signal works
        with self.assertRaises(UserError):
            c.signal_adoption(fids[1])
        shim.set_sender(voters[2])
        c.signal_adoption(fids[0])
        self.assertEqual(int(c.get_fork_signal_count(fids[0])), 2)
        self.assertEqual(int(c.get_fork_signal_count(fids[1])), 1)

        # cannot close early
        with self.assertRaises(UserError):
            c.close_adoption(rid)

        shim.advance_clock(gf.ADOPTION_WINDOW_SECONDS + 1)
        # cannot signal after the window
        shim.set_sender(shim.Address("0x" + "77" * 20))
        with self.assertRaises(UserError):
            c.signal_adoption(fids[1])

        c.close_adoption(rid)  # permissionless
        info = c.get_adoption(rid)
        self.assertTrue(info.closed)
        # fork 0 has 2 signals, fork 1 has 1 -> fork 0 adopted
        self.assertEqual(int(info.adopted_fork_id), int(fids[0]))
        rep = c.get_reputation(creators[0].as_hex)
        self.assertEqual(int(rep.forks_adopted), 1)
        self.assertEqual(int(c.get_reputation(creators[1].as_hex).forks_adopted), 0)
        with self.assertRaises(UserError):
            c.close_adoption(rid)

    def test_tie_goes_to_lowest_fork_id(self):
        c, rid, fids, _ = _root_with_two_faithful_forks()
        c.open_adoption(rid)
        shim.set_sender(shim.Address("0x" + "21" * 20))
        c.signal_adoption(fids[1])
        shim.set_sender(shim.Address("0x" + "22" * 20))
        c.signal_adoption(fids[0])
        shim.advance_clock(gf.ADOPTION_WINDOW_SECONDS + 1)
        c.close_adoption(rid)
        self.assertEqual(int(c.get_adoption(rid).adopted_fork_id), int(fids[0]))

    def test_no_signals_closes_with_no_winner(self):
        c, rid, fids, _ = _root_with_two_faithful_forks()
        c.open_adoption(rid)
        shim.advance_clock(gf.ADOPTION_WINDOW_SECONDS + 1)
        c.close_adoption(rid)
        info = c.get_adoption(rid)
        self.assertTrue(info.closed)
        self.assertEqual(int(info.adopted_fork_id), 0)


class ReputationTests(unittest.TestCase):
    def test_finalize_faithful_fork_counts(self):
        c, rid, fid, case_id, creator, eids = s8._fork_with_verdict()
        shim.set_sender(creator)
        c.open_finality_window(fid, gf.TARGET_KIND_FORK)
        shim.advance_clock(gf.CHALLENGE_WINDOW_SECONDS + 1)
        c.finalize(fid, gf.TARGET_KIND_FORK)
        rep = c.get_reputation(creator.as_hex)
        self.assertEqual(int(rep.forks_faithful), 1)
        self.assertEqual(int(rep.forks_not_faithful), 0)

    def test_finalize_not_faithful_fork_counts(self):
        c, rid, fid, case_id, creator, eids = s8._fork_with_verdict(
            {gf.FORK_DIM_UNDECLARED_SEMANTIC_CHANGE: gf.FINDING_NOT_SATISFIED}
        )
        shim.set_sender(creator)
        c.open_finality_window(fid, gf.TARGET_KIND_FORK)
        shim.advance_clock(gf.CHALLENGE_WINDOW_SECONDS + 1)
        c.finalize(fid, gf.TARGET_KIND_FORK)
        rep = c.get_reputation(creator.as_hex)
        self.assertEqual(int(rep.forks_not_faithful), 1)
        self.assertEqual(int(rep.forks_faithful), 0)

    def test_unknown_creator_is_all_zero(self):
        c = h._fresh()
        rep = c.get_reputation("0x" + "ee" * 20)
        self.assertEqual(
            (int(rep.forks_faithful), int(rep.forks_not_faithful), int(rep.forks_adopted)),
            (0, 0, 0),
        )


class EscalatedAppealTests(unittest.TestCase):
    def test_only_final_allowed_challenge_uses_strict_principle(self):
        c, rid, case_id, eids = s8._root_with_verdict()
        used = shim._EqPrincipleNamespace.principles_used
        for i in range(gf.MAX_CHALLENGES_PER_TARGET):
            ch_case = c.next_case_id
            c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                gf.CG_RE_SCOPE_MISCHARACTERIZED, "n%d" % i)
            c.adjudicate(ch_case)
            shim.get_mock_semantic().set_default(s8._mk_root_output(ch_case))
            c.run_adjudication(ch_case)
            shim.get_mock_semantic().reset()
            last = used[-1]
            if i < gf.MAX_CHALLENGES_PER_TARGET - 1:
                self.assertEqual(last, gf._ADJ_PRINCIPLE)
            else:
                self.assertEqual(last, gf._ADJ_PRINCIPLE_STRICT)
        self.assertIn("evidence_ids", gf._ADJ_PRINCIPLE_STRICT)
        self.assertNotEqual(gf._ADJ_PRINCIPLE, gf._ADJ_PRINCIPLE_STRICT)


if __name__ == "__main__":
    unittest.main()
