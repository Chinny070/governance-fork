"""Stage 12 tests -- payout ledger, reserve accounting, failed-payment recovery.

LOCAL LOGIC TESTS (mock chain). The wallet-crediting transfer path itself was
verified live on StudioNet with contracts/probe/payout_probe.py (a never-seen
wallet went 0 -> 0.004 GEN and a funded wallet rose by exactly 0.004 GEN);
these tests cover the contract's own ledger rules.
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
import test_stage_9 as s9  # noqa: E402

UserError = shim.get_user_error()
BOND = int(gf.FORK_CREATION_BOND)
CONTRACT = shim.contract_address()
ADMIN = None  # resolved per contract (treasury_addr)


def _settled_root():
    """A finalized FAITHFUL root with its envelope bond settled -> a payout."""
    c, rid = s9._finalized_root()
    bid = s9._bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0]
    owner = str(c.get_bond(bid).owner)
    c.settle_bond(bid)
    pid = int(c.get_payout_of_bond(bid))
    return c, rid, bid, owner, pid


class PayoutLedgerTests(unittest.TestCase):
    def test_settlement_records_a_sent_payout_and_moves_reserves(self):
        c, rid, bid, owner, pid = _settled_root()
        self.assertGreater(pid, 0)
        po = c.get_payout(pid)
        self.assertEqual(po.status, gf.PAYOUT_SENT)
        self.assertEqual(int(po.amount), BOND)
        self.assertEqual(po.source_kind, gf.PAYOUT_SRC_BOND)
        self.assertEqual(int(po.source_id), bid)
        self.assertEqual(int(po.attempts), 1)
        r = c.get_reserves()
        self.assertEqual(int(r.in_flight_payouts), BOND)
        self.assertEqual(int(r.locked_bonds), 0)
        self.assertEqual(int(r.shortfall), 0)
        self.assertGreater(int(c.get_bond(bid).settled_at), 0)

    def test_confirm_by_recipient_is_final_and_releases_reserve(self):
        c, rid, bid, owner, pid = _settled_root()
        shim.set_sender(shim.Address(owner))
        c.confirm_payout(pid)
        self.assertEqual(c.get_payout(pid).status, gf.PAYOUT_CONFIRMED)
        self.assertEqual(int(c.get_reserves().in_flight_payouts), 0)
        with self.assertRaises(UserError):
            c.confirm_payout(pid)           # already final
        with self.assertRaises(UserError):
            c.retry_payout(pid)             # confirmed -> never re-sent

    def test_a_stranger_cannot_confirm_or_resolve(self):
        c, rid, bid, owner, pid = _settled_root()
        shim.set_sender(shim.Address("0x" + "99" * 20))
        with self.assertRaises(UserError):
            c.confirm_payout(pid)
        with self.assertRaises(UserError):
            c.report_payout_not_received(pid)
        with self.assertRaises(UserError):
            c.resolve_payout(pid, True)

    def test_dispute_alone_never_allows_a_resend(self):
        # A fork creator's bond: the recipient is NOT the contract admin.
        c, rid, fid, creator = s9._finalized_fork()
        bid = int(c.get_fork(fid).creator_bond_id)
        c.settle_bond(bid)
        pid = int(c.get_payout_of_bond(bid))
        self.assertNotEqual(str(creator), str(c.get_constants().treasury_addr))
        shim.set_sender(creator)
        c.report_payout_not_received(pid)
        self.assertEqual(c.get_payout(pid).status, gf.PAYOUT_DISPUTED)
        with self.assertRaises(UserError):
            c.retry_payout(pid)             # needs admin attestation first
        with self.assertRaises(UserError):
            c.resolve_payout(pid, False)    # the recipient is not the admin

    def test_admin_attests_delivered_closes_the_dispute(self):
        c, rid, bid, owner, pid = _settled_root()
        shim.set_sender(shim.Address(owner))
        c.report_payout_not_received(pid)
        shim.set_sender(c.get_constants().treasury_addr)
        c.resolve_payout(pid, True)
        self.assertEqual(c.get_payout(pid).status, gf.PAYOUT_CONFIRMED)
        self.assertEqual(int(c.get_reserves().in_flight_payouts), 0)

    def test_lost_payment_recovery_resends_once_when_balance_covers(self):
        # The first transfer leaves the contract but credits nobody. The
        # contract is then short, so a retry is BLOCKED (it would dip into
        # other participants' funds) until the shortfall is covered.
        shim.fail_next_transfer(1)
        c, rid, bid, owner, pid = _settled_root()
        shim.set_sender(shim.Address(owner))
        c.report_payout_not_received(pid)
        shim.set_sender(c.get_constants().treasury_addr)
        c.resolve_payout(pid, False)
        self.assertEqual(c.get_payout(pid).status, gf.PAYOUT_RETRYABLE)
        with self.assertRaises(UserError):
            c.retry_payout(pid)                           # pool empty -> blocked
        shim.set_sender(shim.Address(owner))
        # The pool cannot cover it -> blocked. Top the treasury up and retry.
        shim.set_sender(shim.Address("0x" + "77" * 20))
        shim.set_value(BOND)
        c.fund_treasury()
        shim.reset_message_context()
        shim.set_sender(shim.Address(owner))
        before = shim.balance(owner)
        c.retry_payout(pid)
        self.assertEqual(shim.balance(owner) - before, BOND)   # delivered once
        po = c.get_payout(pid)
        self.assertEqual(po.status, gf.PAYOUT_SENT)
        self.assertEqual(int(po.attempts), 2)
        with self.assertRaises(UserError):
            c.retry_payout(pid)                           # no double send
        shim.set_sender(shim.Address(owner))
        c.confirm_payout(pid)
        self.assertEqual(int(c.get_reserves().in_flight_payouts), 0)
        self.assertEqual(int(c.get_reserves().shortfall), 0)
        self.assertEqual(int(c.get_constants().treasury_pool), 0)   # pool paid the resend

    def test_a_retry_never_dips_into_other_participants_bonds(self):
        shim.fail_next_transfer(1)
        c, rid, bid, owner, pid = _settled_root()
        # A different participant's bond is still locked in the contract.
        other = shim.lock(c, gf.BOND_PURPOSE_FORK_CREATION, BOND)
        shim.set_sender(c.get_constants().treasury_addr)
        c.resolve_payout(pid, False)
        locked_before = int(c.get_reserves().locked_bonds)
        self.assertGreaterEqual(locked_before, BOND)
        with self.assertRaises(UserError):
            c.retry_payout(pid)                           # would use that bond -> blocked
        self.assertEqual(int(c.get_reserves().locked_bonds), locked_before)
        self.assertEqual(int(c.get_bond(other).amount), BOND)

    def test_retry_attempts_are_capped(self):
        shim.fail_next_transfer(1)
        c, rid, bid, owner, pid = _settled_root()
        admin = c.get_constants().treasury_addr
        for attempt in range(1, gf.MAX_PAYOUT_ATTEMPTS):
            shim.set_sender(shim.Address("0x" + "77" * 20))
            shim.set_value(BOND)
            c.fund_treasury()
            shim.reset_message_context()
            shim.set_sender(admin)
            c.resolve_payout(pid, False)
            c.retry_payout(pid)
            self.assertEqual(int(c.get_payout(pid).attempts), attempt + 1)
        shim.set_sender(shim.Address("0x" + "77" * 20))
        shim.set_value(BOND)
        c.fund_treasury()
        shim.reset_message_context()
        shim.set_sender(admin)
        c.resolve_payout(pid, False)
        with self.assertRaises(UserError):
            c.retry_payout(pid)

    def test_fund_treasury_adds_to_the_pool_and_rejects_zero(self):
        c, rid, bid, owner, pid = _settled_root()
        shim.set_sender(shim.Address("0x" + "77" * 20))
        shim.set_value(BOND)
        c.fund_treasury()
        shim.reset_message_context()
        self.assertEqual(int(c.get_constants().treasury_pool), BOND)
        shim.set_value(0)
        with self.assertRaises(UserError):
            c.fund_treasury()
        shim.reset_message_context()

    def test_treasury_withdrawal_is_recorded_and_recoverable(self):
        c, rid, fid, creator = s9._finalized_fork(
            {gf.FORK_DIM_UNDECLARED_SEMANTIC_CHANGE: gf.FINDING_NOT_SATISFIED}
        )
        bid = int(c.get_fork(fid).creator_bond_id)
        c.settle_bond(bid)                                 # partial slash -> pool
        pool = int(c.get_constants().treasury_pool)
        self.assertGreater(pool, 0)
        admin = c.get_constants().treasury_addr
        shim.set_sender(admin)
        c.withdraw_treasury(pool)
        self.assertEqual(int(c.get_constants().treasury_pool), 0)
        pid = int(c.next_payout_id) - 1
        po = c.get_payout(pid)
        self.assertEqual(po.source_kind, gf.PAYOUT_SRC_TREASURY)
        self.assertEqual(po.status, gf.PAYOUT_SENT)
        self.assertEqual(int(po.amount), pool)
        c.confirm_payout(pid)
        self.assertEqual(c.get_payout(pid).status, gf.PAYOUT_CONFIRMED)

    def test_locked_bond_reserve_tracks_lock_and_settle(self):
        c, rid = s9._finalized_root()
        self.assertEqual(int(c.get_reserves().locked_bonds), BOND)   # envelope bond
        bid = s9._bond_ids(c, rid, gf.TARGET_KIND_ROOT_ENVELOPE)[0]
        c.settle_bond(bid)
        self.assertEqual(int(c.get_reserves().locked_bonds), 0)

    def test_payouts_use_the_wallet_crediting_transfer_api(self):
        before = len(shim._EVM_TRANSFER_LOG)
        _settled_root()
        self.assertGreater(len(shim._EVM_TRANSFER_LOG), before)


class EvidenceCoverageTests(unittest.TestCase):
    def _doc(self):
        filler = "Background paragraph about general matters. " * 18   # ~800 chars
        parts = [filler] * 30
        parts[17] = ("IMPORTANT EXCEPTION: the base fee burn does not apply to "
                     "emergency transactions approved by the guardian council. ").ljust(800, ".")
        return "".join(parts)

    def test_short_document_is_used_whole(self):
        text, shown, total = gf._excerpt_for_prompt("short text", 1000, ["fee"])
        self.assertEqual((text, shown, total), ("short text", 10, 10))

    def test_relevant_middle_qualification_survives_truncation(self):
        doc = self._doc()
        self.assertGreater(len(doc), 20000)
        terms = gf._terms_of("Explains how the base fee burn works and any exception")
        text, shown, total = gf._excerpt_for_prompt(doc, 8192, terms)
        self.assertIn("IMPORTANT EXCEPTION", text)          # a head/tail cut would drop it
        self.assertLessEqual(len(text), 8192)
        self.assertEqual(total, len(doc))
        self.assertLess(shown, total)
        self.assertIn("[...omitted...]", text)

    def test_excerpt_is_deterministic_and_keeps_the_opening(self):
        doc = self._doc()
        terms = gf._terms_of("base fee burn exception")
        a = gf._excerpt_for_prompt(doc, 8192, terms)
        b = gf._excerpt_for_prompt(doc, 8192, terms)
        self.assertEqual(a, b)
        self.assertTrue(a[0].startswith(doc[:200]))

    def test_evidence_block_states_exact_coverage_and_partial_note(self):
        class Ev:
            frozen_content = self._doc()
            normalized_source = "example.org"
            evidence_class = "OFFICIAL_DOCUMENTATION"
            temporal_marker = "current"
            relevance_claim = "base fee burn exception"
        block = gf._render_evidence_block(7, Ev(), 8192)
        self.assertIn("coverage=", block)
        self.assertIn("PARTIAL EXCERPT", block)
        self.assertIn("IMPORTANT EXCEPTION", block)
        small = gf._render_evidence_block(7, Ev(), 100000)
        self.assertNotIn("PARTIAL EXCERPT", small)
        self.assertIn("coverage=%d/%d" % (len(Ev.frozen_content), len(Ev.frozen_content)), small)

    def test_prompt_tells_the_model_omitted_text_means_unclear(self):
        self.assertIn("PARTIAL", gf._ADJ_SECURITY_PREAMBLE)
        self.assertIn("UNCLEAR", gf._ADJ_SECURITY_PREAMBLE)

    def test_partial_evidence_is_flagged_on_the_verdict(self):
        class Ev:
            frozen_content = "x" * 20000
        self.assertTrue(gf._evidence_is_partial(Ev(), 8192))
        self.assertFalse(gf._evidence_is_partial(Ev(), 50000))


if __name__ == "__main__":
    unittest.main()
