"""Stage 9 tests -- native GEN bond economics.

LOCAL LOGIC TESTS ONLY. Native GEN is modelled by tests/_genlayer_shim.py's
_MockChain, which mirrors what contracts/probe/value_transfer_probe.py
proved on the pinned runtime (payable credit of self.balance;
gl.get_contract_at(addr).emit_transfer(value=v) deduction). It does NOT
model consensus or message-finalisation timing.
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
import test_stage_7 as s7  # noqa: E402
import test_stage_8 as s8  # noqa: E402

UserError = shim.get_user_error()

BOND = int(gf.FORK_CREATION_BOND)   # == ENVELOPE_BOND == CHALLENGE_BOND
DEFAULT = "0x" + "aa" * 20
CREATOR = "0x" + "cc" * 20
CONTRACT = shim.contract_address()


def _c_bal(c):
    return int(c.get_balance() if hasattr(c, "get_balance") else shim.balance(CONTRACT))


def _finalized_root(overrides=None):
    c, rid, case_id, eids = s8._root_with_verdict(overrides)
    shim.reset_message_context()          # sender back to root.proposer (default)
    c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
    shim.advance_clock(gf.CHALLENGE_WINDOW_SECONDS + 1)
    c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
    return c, rid


def _finalized_fork(overrides=None):
    c, rid, fid, case_id, creator, eids = s8._fork_with_verdict(overrides)
    shim.set_sender(creator)
    c.open_finality_window(fid, gf.TARGET_KIND_FORK)
    shim.advance_clock(gf.CHALLENGE_WINDOW_SECONDS + 1)
    c.finalize(fid, gf.TARGET_KIND_FORK)
    return c, rid, fid, creator


def _bond_ids(c, tid, kind):
    return [int(x) for x in c.list_bonds_by_target(tid, kind, shim.u256(0), shim.u32(20)).items]


# ===========================================================================
# capture
# ===========================================================================

class CaptureTests(unittest.TestCase):
    def test_envelope_bond_captured(self):
        c, rid, case_id, eids = s7._seal_root()
        bids = _bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        self.assertEqual(len(bids), 1)
        b = c.get_bond(bids[0])
        self.assertEqual(int(b.amount), BOND)
        self.assertEqual(b.purpose, gf.BOND_PURPOSE_ENVELOPE)
        self.assertEqual(b.settlement_kind, gf.BOND_UNSETTLED)
        self.assertFalse(b.settled)
        self.assertEqual(shim.balance(CONTRACT), BOND)

    def test_fork_bond_captured_and_linked(self):
        c, rid, fid, case_id, creator, eids = s7._seal_fork()
        fork = c.get_fork(fid)
        self.assertNotEqual(int(fork.creator_bond_id), 0)
        b = c.get_bond(fork.creator_bond_id)
        self.assertEqual(b.purpose, gf.BOND_PURPOSE_FORK_CREATION)
        self.assertEqual(str(b.owner), CREATOR)

    def _root_ready(self):
        c = h._fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(did, "EP", "T", "https://x/1", *h._params_kv([("allocation", "1")]))
        return c, rid

    def test_lock_bond_zero_rejected(self):
        # the ONLY rejection in lock_bond -- and a zero value traps nothing.
        c, rid = self._root_ready()
        shim.set_value(0)
        with self.assertRaises(UserError):
            c.lock_bond(gf.BOND_PURPOSE_ENVELOPE)

    def test_lock_bond_bad_purpose_maps_to_unrecognised(self):
        # lock_bond never reverts once value is attached: an unknown purpose
        # yields an UNRECOGNISED bond that no method will consume but that is
        # fully refundable.
        c, rid = self._root_ready()
        bid = shim.lock(c, "NONSENSE", BOND)
        b = c.get_bond(bid)
        self.assertEqual(b.purpose, gf.BOND_PURPOSE_UNRECOGNISED)
        self.assertEqual(int(b.target_id), 0)
        with self.assertRaises(UserError):
            c.submit_root_envelope(bid, rid, *h._evidence_arrays(("https://x/1",)),
                                   *h._envelope_fields())  # wrong order ok: reverts at consume
        before = shim.balance(DEFAULT)
        c.settle_bond(bid)
        self.assertEqual(c.get_bond(bid).settlement_kind, gf.BOND_SETTLED_FULL_REFUND)
        self.assertEqual(shim.balance(DEFAULT) - before, BOND)

    def test_lock_bond_while_paused_ok_and_refundable(self):
        # pause must NOT revert lock_bond (that would trap the value); it
        # blocks the CONSUMING step instead.
        c, rid = self._root_ready()
        c.pause()
        bid = shim.lock(c, gf.BOND_PURPOSE_ENVELOPE, BOND)
        self.assertEqual(int(c.get_bond(bid).amount), BOND)
        with self.assertRaises(UserError):  # consuming is paused-gated
            c.submit_root_envelope(bid, rid, *h._envelope_fields(),
                                   *h._evidence_arrays(("https://x/1",)))
        c.settle_bond(bid)   # settle is not paused-gated
        self.assertEqual(c.get_bond(bid).settlement_kind, gf.BOND_SETTLED_FULL_REFUND)

    def test_wrong_bond_amount_rejected_at_consume(self):
        # lock_bond accepts any nonzero value; the exact-amount check is in
        # the (safely-revertible) consuming method.
        c, rid = self._root_ready()
        bid = shim.lock(c, gf.BOND_PURPOSE_ENVELOPE, BOND - 1)
        args = h._evidence_arrays(("https://x/1",))
        with self.assertRaises(UserError):
            c.submit_root_envelope(bid, rid, *h._envelope_fields(), *args)
        # the mis-sized bond is fully refundable
        b = c.get_bond(bid)
        self.assertEqual(int(b.target_id), 0)
        self.assertFalse(b.settled)
        before = shim.balance(DEFAULT)
        c.settle_bond(bid)
        self.assertEqual(c.get_bond(bid).settlement_kind, gf.BOND_SETTLED_FULL_REFUND)
        self.assertEqual(shim.balance(DEFAULT) - before, BOND - 1)

    def test_overpay_rejected_at_consume(self):
        c, rid = self._root_ready()
        bid = shim.lock(c, gf.BOND_PURPOSE_ENVELOPE, BOND * 2)
        args = h._evidence_arrays(("https://x/1",))
        with self.assertRaises(UserError):
            c.submit_root_envelope(bid, rid, *h._envelope_fields(), *args)

    def test_wrong_purpose_bond_rejected(self):
        c, rid = self._root_ready()
        bid = shim.lock(c, gf.BOND_PURPOSE_FORK_CREATION, BOND)  # wrong purpose
        args = h._evidence_arrays(("https://x/1",))
        with self.assertRaises(UserError):
            c.submit_root_envelope(bid, rid, *h._envelope_fields(), *args)

    def test_bond_not_owned_by_caller_rejected(self):
        c, rid = self._root_ready()
        shim.set_sender("0x" + "bb" * 20)
        bid = shim.lock(c, gf.BOND_PURPOSE_ENVELOPE, BOND)
        shim.reset_message_context()   # back to default sender
        args = h._evidence_arrays(("https://x/1",))
        with self.assertRaises(UserError):
            c.submit_root_envelope(bid, rid, *h._envelope_fields(), *args)

    def test_challenge_bond_captured(self):
        c, rid, case_id, eids = s8._root_with_verdict()
        cid = c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                  gf.CG_RE_SCOPE_MISCHARACTERIZED, "scope wrong")
        ch = c.get_challenge(cid)
        self.assertNotEqual(int(ch.bond_id), 0)
        b = c.get_bond(ch.bond_id)
        self.assertEqual(int(b.amount), BOND)
        self.assertEqual(b.purpose, gf.BOND_PURPOSE_CHALLENGE)
        self.assertEqual(int(b.challenge_id), int(cid))


# ===========================================================================
# settlement -- economic paths A..H
# ===========================================================================

class SettlementTests(unittest.TestCase):
    def test_A_faithful_full_refund(self):
        c, rid = _finalized_root()                    # all-SATISFIED -> FAITHFUL
        bid = _bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0]
        owner = str(c.get_bond(bid).owner)
        before_owner = shim.balance(owner)
        before_contract = shim.balance(CONTRACT)
        c.settle_bond(bid)
        b = c.get_bond(bid)
        self.assertTrue(b.settled)
        self.assertEqual(b.settlement_kind, gf.BOND_SETTLED_FULL_REFUND)
        self.assertEqual(int(b.refund_amount), BOND)
        self.assertEqual(int(b.slash_amount), 0)
        self.assertEqual(shim.balance(owner) - before_owner, BOND)
        self.assertEqual(before_contract - shim.balance(CONTRACT), BOND)
        self.assertEqual(int(c.get_constants().treasury_pool), 0)

    def test_B_not_faithful_partial_slash(self):
        c, rid, fid, creator = _finalized_fork(
            {gf.FORK_DIM_UNDECLARED_SEMANTIC_CHANGE: gf.FINDING_NOT_SATISFIED}
        )
        self.assertEqual(c.get_fork(fid).status, gf.FORK_FINALIZED_NOT_FAITHFUL)
        bid = int(c.get_fork(fid).creator_bond_id)
        before_owner = shim.balance(creator)
        c.settle_bond(bid)
        b = c.get_bond(bid)
        self.assertEqual(b.settlement_kind, gf.BOND_SETTLED_PARTIAL_SLASH)
        self.assertEqual(int(b.refund_amount), BOND // 2)
        self.assertEqual(int(b.slash_amount), BOND - BOND // 2)
        self.assertEqual(shim.balance(creator) - before_owner, BOND // 2)
        self.assertEqual(int(c.get_constants().treasury_pool), BOND - BOND // 2)
        # slash stays in the contract
        self.assertGreaterEqual(shim.balance(CONTRACT), BOND - BOND // 2)

    def test_C_flip_challenge_reward(self):
        # root initial FAITHFUL, challenge FLIPS to NOT_FAITHFUL.
        c, rid, case_id, eids = s8._root_with_verdict()
        gov0 = int(c.get_root_proposal(rid).current_verdict_id)
        ch_case = c.next_case_id
        cid = c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                  gf.CG_RE_OBJECTIVE_MISREPRESENTED, "objective misstated")
        challenger = str(c.get_challenge(cid).challenger)
        c.adjudicate(ch_case)
        shim.get_mock_semantic().set_default(
            s8._mk_root_output(ch_case, {gf.RE_DIM_OBJECTIVE_REPRESENTATION: gf.FINDING_NOT_SATISFIED})
        )
        c.run_adjudication(ch_case)
        self.assertEqual(c.get_challenge(cid).status, gf.CHALLENGE_RESOLVED_FLIPPED)
        shim.get_mock_semantic().reset()
        shim.reset_message_context()
        c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        shim.advance_clock(gf.CHALLENGE_WINDOW_SECONDS + 1)
        c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        self.assertEqual(c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_REJECTED)

        env_bond = _bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0]
        ch_bond = int(c.get_challenge(cid).bond_id)
        # settle the proposer bond first -> funds the treasury pool
        c.settle_bond(env_bond)
        self.assertEqual(int(c.get_constants().treasury_pool), BOND - BOND // 2)
        before = shim.balance(challenger)
        c.settle_bond(ch_bond)
        b = c.get_bond(ch_bond)
        self.assertEqual(b.settlement_kind, gf.BOND_SETTLED_CHALLENGER_REWARD)
        self.assertEqual(int(b.refund_amount), BOND)
        self.assertEqual(int(b.reward_amount), int(gf.CHALLENGER_FLIP_REWARD))
        self.assertEqual(shim.balance(challenger) - before, BOND + int(gf.CHALLENGER_FLIP_REWARD))
        self.assertEqual(int(c.get_constants().treasury_pool),
                         (BOND - BOND // 2) - int(gf.CHALLENGER_FLIP_REWARD))

    def test_D_failed_challenge_partial_slash(self):
        c, rid, case_id, eids = s8._root_with_verdict()
        ch_case = c.next_case_id
        cid = c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                  gf.CG_RE_SCOPE_MISCHARACTERIZED, "scope wrong")
        challenger = str(c.get_challenge(cid).challenger)
        c.adjudicate(ch_case)
        shim.get_mock_semantic().set_default(s8._mk_root_output(ch_case))  # same -> UNCHANGED
        c.run_adjudication(ch_case)
        self.assertEqual(c.get_challenge(cid).status, gf.CHALLENGE_RESOLVED_UNCHANGED)
        shim.get_mock_semantic().reset()
        shim.reset_message_context()
        c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        shim.advance_clock(gf.CHALLENGE_WINDOW_SECONDS + 1)
        c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        c.settle_bond(_bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0])  # primary first
        ch_bond = int(c.get_challenge(cid).bond_id)
        before = shim.balance(challenger)
        c.settle_bond(ch_bond)
        b = c.get_bond(ch_bond)
        self.assertEqual(b.settlement_kind, gf.BOND_SETTLED_PARTIAL_SLASH)
        self.assertEqual(int(b.refund_amount), BOND // 2)
        self.assertEqual(shim.balance(challenger) - before, BOND // 2)
        self.assertEqual(int(c.get_constants().treasury_pool), BOND - BOND // 2)

    def test_E_unclear_full_refund(self):
        c, rid = _finalized_root({gf.RE_DIM_EVIDENCE_SUPPORT: gf.FINDING_UNCLEAR})
        self.assertEqual(c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_UNCLEAR)
        bid = _bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0]
        c.settle_bond(bid)
        self.assertEqual(c.get_bond(bid).settlement_kind, gf.BOND_SETTLED_FULL_REFUND)
        self.assertEqual(int(c.get_bond(bid).refund_amount), BOND)

    def test_E2_retry_exhaustion_terminal_bond_not_trapped(self):
        # No verdict was ever produced (retry-exhaustion -> ENVELOPE_UNCLEAR
        # with current_verdict_id == 0). The proposer's envelope bond must
        # still be 100%-refundable, not trapped.
        c, rid, case_id, eids = s7._seal_root()
        for _ in range(gf.MAX_RETRIES_PER_CASE):
            c.adjudicate(case_id)
        c.adjudicate(case_id)  # budget spent -> terminal
        self.assertEqual(c.get_case(case_id).state, gf.CASE_UNDETERMINED_TERMINAL)
        self.assertEqual(c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_UNCLEAR)
        self.assertEqual(int(c.get_root_proposal(rid).current_verdict_id), 0)
        bid = _bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0]
        before = shim.balance(DEFAULT)
        c.settle_bond(bid)
        self.assertEqual(c.get_bond(bid).settlement_kind, gf.BOND_SETTLED_FULL_REFUND)
        self.assertEqual(shim.balance(DEFAULT) - before, BOND)

    def test_F_settlement_replay_rejected(self):
        c, rid = _finalized_root()
        bid = _bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0]
        c.settle_bond(bid)
        with self.assertRaises(UserError):
            c.settle_bond(bid)

    def test_G_settle_before_finalize_rejected(self):
        c, rid, case_id, eids = s8._root_with_verdict()
        bid = _bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0]
        with self.assertRaises(UserError):
            c.settle_bond(bid)

    def test_challenge_bond_before_primary_rejected(self):
        c, rid, case_id, eids = s8._root_with_verdict()
        ch_case = c.next_case_id
        cid = c.challenge_verdict(rid, gf.TARGET_KIND_ROOT_ENVELOPE,
                                  gf.CG_RE_SCOPE_MISCHARACTERIZED, "scope wrong")
        c.adjudicate(ch_case)
        shim.get_mock_semantic().set_default(s8._mk_root_output(ch_case))
        c.run_adjudication(ch_case)
        shim.get_mock_semantic().reset()
        shim.reset_message_context()
        c.open_finality_window(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        shim.advance_clock(gf.CHALLENGE_WINDOW_SECONDS + 1)
        c.finalize(rid, gf.TARGET_KIND_ROOT_ENVELOPE)
        ch_bond = int(c.get_challenge(cid).bond_id)
        with self.assertRaises(UserError):
            c.settle_bond(ch_bond)   # primary (envelope) bond not settled yet

    def test_H_pause_does_not_trap_finalized_funds(self):
        c, rid = _finalized_root()
        c.pause()
        bid = _bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0]
        c.settle_bond(bid)   # must succeed despite pause
        self.assertTrue(c.get_bond(bid).settled)

    def test_pause_blocks_new_bond_exposure(self):
        c, rid, case_id, eids = s7._seal_root()
        c.pause()
        r = c.get_root_proposal(rid)
        shim.set_sender(CREATOR)
        with self.assertRaises(UserError):
            c.create_fork(rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
                          *h._delta_fields([("allocation", gf.CLAIM_NARROWED, "1", "2")]),
                          *h._body_fields())


# ===========================================================================
# accounting invariants + treasury withdrawal
# ===========================================================================

class InvariantTests(unittest.TestCase):
    def test_refund_plus_slash_equals_amount(self):
        for ov in (None, {gf.FORK_DIM_UNDECLARED_SEMANTIC_CHANGE: gf.FINDING_NOT_SATISFIED}):
            c, rid, fid, creator = _finalized_fork(ov)
            bid = int(c.get_fork(fid).creator_bond_id)
            c.settle_bond(bid)
            b = c.get_bond(bid)
            self.assertEqual(int(b.refund_amount) + int(b.slash_amount), int(b.amount))

    def test_no_balance_drift_full_cycle(self):
        # global invariant: self.balance == sum(unsettled bond amounts) +
        # treasury_pool, at every step. Uses a fully, properly built root
        # (real adjudication + finalize) so its envelope bond is settleable.
        c, rid = _finalized_root()                       # FAITHFUL, finalized
        self.assertEqual(c.get_root_proposal(rid).envelope_status, gf.ENVELOPE_FAITHFUL)
        r = c.get_root_proposal(rid)
        creator = shim.Address(CREATOR)
        shim.set_sender(creator)
        fid = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *h._delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
            *h._body_fields(params=(("allocation", "50000"),)),
        )
        shim.set_sender(creator)
        c.submit_fork_evidence(fid, *h._evidence_arrays(("https://fork.example.com/e",)))
        fcase = c.forks[fid].evidence_case_id
        shim.set_sender(creator)
        c.close_evidence(fcase)
        feids = list(c.evidence_by_case[fcase])
        for eid in feids:
            shim.get_mock_web().set_response(c.get_evidence(eid).url, s7._USEFUL)
            c.fetch_evidence(eid)
        c.seal_evidence(fcase)
        shim.set_sender(creator)
        c.adjudicate(fcase)
        shim.get_mock_semantic().set_default(
            s8._mk_fork_output(fcase, feids[0],
                               {gf.FORK_DIM_UNDECLARED_SEMANTIC_CHANGE: gf.FINDING_NOT_SATISFIED})
        )
        c.run_adjudication(fcase)
        shim.get_mock_semantic().reset()
        shim.set_sender(creator)
        c.open_finality_window(fid, gf.TARGET_KIND_FORK)
        shim.advance_clock(gf.CHALLENGE_WINDOW_SECONDS + 1)
        c.finalize(fid, gf.TARGET_KIND_FORK)

        ids = (_bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)
               + _bond_ids(c, fid, gf.TARGET_KIND_FORK))
        self.assertEqual(len(ids), 2)

        def invariant():
            unsettled = sum(int(c.get_bond(shim.u256(i)).amount) for i in ids
                            if not c.get_bond(shim.u256(i)).settled)
            self.assertEqual(shim.balance(CONTRACT),
                             unsettled + int(c.get_constants().treasury_pool))

        invariant()
        for i in ids:
            c.settle_bond(shim.u256(i))
            invariant()
        self.assertEqual(shim.balance(CONTRACT), int(c.get_constants().treasury_pool))
        # exactly one 50% slash (the NOT_FAITHFUL fork bond)
        self.assertEqual(int(c.get_constants().treasury_pool), BOND - BOND // 2)

    def test_withdraw_treasury(self):
        c, rid, fid, creator = _finalized_fork(
            {gf.FORK_DIM_UNDECLARED_SEMANTIC_CHANGE: gf.FINDING_NOT_SATISFIED}
        )
        bid = int(c.get_fork(fid).creator_bond_id)
        c.settle_bond(bid)
        pool = int(c.get_constants().treasury_pool)
        self.assertGreater(pool, 0)
        shim.reset_message_context()   # treasury_addr == default deployer
        before = shim.balance(DEFAULT)
        c.withdraw_treasury(shim.u256(pool))
        self.assertEqual(shim.balance(DEFAULT) - before, pool)
        self.assertEqual(int(c.get_constants().treasury_pool), 0)

    def test_withdraw_treasury_only_admin(self):
        c, rid, fid, creator = _finalized_fork(
            {gf.FORK_DIM_UNDECLARED_SEMANTIC_CHANGE: gf.FINDING_NOT_SATISFIED}
        )
        c.settle_bond(int(c.get_fork(fid).creator_bond_id))
        shim.set_sender("0x" + "ee" * 20)
        with self.assertRaises(UserError):
            c.withdraw_treasury(shim.u256(1))

    def test_withdraw_treasury_over_pool_rejected(self):
        c, rid = _finalized_root()
        c.settle_bond(_bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0])  # FAITHFUL -> pool 0
        shim.reset_message_context()
        with self.assertRaises(UserError):
            c.withdraw_treasury(shim.u256(1))

    def test_bond_not_found(self):
        c, rid = _finalized_root()
        with self.assertRaises(UserError):
            c.settle_bond(shim.u256(999))
        with self.assertRaises(UserError):
            c.get_bond(shim.u256(999))


if __name__ == "__main__":
    unittest.main()
