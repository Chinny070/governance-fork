"""Stage 10 tests -- steward-requested fixes.

LOCAL LOGIC TESTS ONLY, covering the one fix that is expensive to prove live
on a real deployment (fork adjudication context at depth >= 2 requires a
real FAITHFUL semantic verdict two levels deep, which needs governance-
authoritative evidence no synthetic test proposal can supply -- see
docs/STAGE_10_STEWARD_FIXES.md for the live-verification results on the
other three fixes: envelope binding, required source evidence, and the
two-step finality commit, all reproduced on a fresh StudioNet deployment).

This file targets exactly the new code: does a depth-2 fork's adjudication
prompt actually contain the root's canonical intent AND the immediate
parent fork's complete body, verbatim? The mock semantic registry records
every prompt it's asked to judge (see _MockSemanticRegistry.calls in
_genlayer_shim.py), so this is a direct, deterministic assertion on the
real prompt-assembly code path (_fork_parent_context / _fork_subject_block
/ _intent_lines) -- not a description of intended behavior.
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


class ForkContextTests(unittest.TestCase):
    def test_depth2_prompt_includes_root_intent_and_parent_body(self):
        # ---- root: FAITHFUL (harness-flip, matches h._fresh_fork_case) ----
        c = h._fresh()
        did = c.register_dao("A", "https://a")
        rid = c.import_root_proposal(
            did, "EP", "T", "https://x/1",
            *h._params_kv([("allocation", "100000")]),
        )
        args = h._evidence_arrays(("https://gov.example.com/root-evidence",))
        c.submit_root_envelope(rid, *h._envelope_fields(), *args)
        r = c.get_root_proposal(rid)
        r.envelope_status = gf.ENVELOPE_FAITHFUL  # test-harness flip only
        c.roots[rid] = r
        root_objective = r.envelope.objective
        self.assertTrue(root_objective, "fixture must set a non-empty objective")

        # ---- fork 1 (parent = root), distinctive body, harness-flip FAITHFUL ----
        creator1 = shim.Address("0x" + "c1" * 20)
        shim.set_sender(creator1)
        fid1 = c.create_fork(
            rid, gf.PARENT_KIND_ROOT, r.import_fingerprint,
            *h._delta_fields([("allocation", gf.CLAIM_NARROWED, "100000", "50000")]),
            "Parent Fork Distinctive Title",
            "Parent Fork Distinctive Summary Sentence",
            *h._params_kv([("allocation", "50000")]),
            "Parent Fork Distinctive Reasoning Sentence",
        )
        f1 = c.get_fork(fid1)
        f1.status = gf.FORK_FINALIZED_FAITHFUL  # test-harness flip only
        c.forks[fid1] = f1

        # ---- fork 2 (parent = fork 1, depth 2) ----
        creator2 = shim.Address("0x" + "c2" * 20)
        shim.set_sender(creator2)
        fid2 = c.create_fork(
            fid1, gf.PARENT_KIND_FORK, f1.body_fingerprint,
            *h._delta_fields([("allocation", gf.CLAIM_NARROWED, "50000", "25000")]),
            "Child Fork Own Title",
            "Child Fork Own Summary",
            *h._params_kv([("allocation", "25000")]),
            "Child Fork Own Reasoning",
        )
        f2 = c.get_fork(fid2)
        self.assertEqual(int(f2.depth), 2)
        self.assertEqual(f2.parent_kind, gf.PARENT_KIND_FORK)

        case_id = c.submit_fork_evidence(
            fid2, *h._evidence_arrays(("https://child.example.com/1",))
        )
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response(c.get_evidence(eid).url, s7._USEFUL)
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)

        c.adjudicate(case_id)
        shim.get_mock_semantic().set_default(s8._mk_fork_output(case_id, eid))
        c.run_adjudication(case_id)

        prompt = shim.get_mock_semantic().calls[-1]

        # The root's canonical intent is present regardless of depth.
        self.assertIn("ROOT INTENT", prompt)
        self.assertIn(root_objective, prompt)

        # The IMMEDIATE PARENT's complete body is present -- not just a
        # flat parameter list (the pre-fix behaviour).
        self.assertIn("IMMEDIATE PARENT", prompt)
        self.assertIn("Parent Fork Distinctive Title", prompt)
        self.assertIn("Parent Fork Distinctive Summary Sentence", prompt)
        self.assertIn("Parent Fork Distinctive Reasoning Sentence", prompt)

        # The fork being adjudicated still describes itself.
        self.assertIn("Child Fork Own Title", prompt)
        self.assertIn("Child Fork Own Reasoning", prompt)

        shim.get_mock_semantic().reset()

    def test_depth1_prompt_labels_parent_as_root_with_no_duplicate_body(self):
        # parent_kind == ROOT: IMMEDIATE PARENT points back at ROOT INTENT
        # rather than rendering a (nonexistent) separate fork body.
        c, did, rid, fid, case_id, creator = h._fresh_fork_case()
        c.close_evidence(case_id)
        eid = list(c.evidence_by_case[case_id])[0]
        shim.get_mock_web().set_response(c.get_evidence(eid).url, s7._USEFUL)
        c.fetch_evidence(eid)
        c.seal_evidence(case_id)
        shim.set_sender(creator)
        c.adjudicate(case_id)
        shim.get_mock_semantic().set_default(s8._mk_fork_output(case_id, eid))
        c.run_adjudication(case_id)

        prompt = shim.get_mock_semantic().calls[-1]
        self.assertIn("ROOT INTENT", prompt)
        self.assertIn("IMMEDIATE PARENT: root proposal", prompt)
        self.assertIn("the parent is the root proposal above", prompt)
        shim.get_mock_semantic().reset()
        shim.reset_message_context()


if __name__ == "__main__":
    unittest.main()
