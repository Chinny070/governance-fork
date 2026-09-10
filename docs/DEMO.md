# Governance Fork — end-to-end demo

A full run of the production contract through the dApp, using a real governance
proposal: **ratifying the Arbitrum Constitution**.

- Live dApp: `https://chinny070.github.io/governance-fork/`
- Contract: `0xbA06003F2C254232E4D440B89425abc7Afd4c11A` (StudioNet)
- You need MetaMask with **GenLayer StudioNet** added and a small amount of test
  GEN (the app's "Switch / add network" button configures the chain for you).

Each numbered step is one on-chain transaction unless noted.

## 0 · Explore (no wallet)

Open the dApp. The **Explore** tab reads the registry straight from StudioNet —
DAOs, root proposals, forks, cases, verdicts, challenges, bonds, and the
proposal tree. The **About** tab shows live contract constants (bond sizes,
treasury pool, pause state). This all works with no wallet connected.

## 1 · Connect

Click **Connect wallet**. If the network badge is red, click it to switch/add
StudioNet.

## 2 · Build the proposal (Build tab)

Click **Pre-fill demo proposal**, then walk the stepper:

| Step | Call | Notes |
|---|---|---|
| 1 · DAO | `register_dao("Arbitrum DAO", …)` | or pick an existing DAO |
| 2 · Import root | `import_root_proposal(dao_id, "AIP-1", …)` | title, authoritative URL, structured params |
| 3 · Intent envelope | `lock_bond("ENVELOPE")` **+** `submit_root_envelope(bond_id, …)` | objective, scope, essential constraints, mutable/immutable dimensions, and 2 evidence URLs (Wikipedia — chosen for reliable rendering) |

After step 3 the root has an **open evidence case**. Click through to the
proposal page.

## 3 · Evidence (proposal page → Evidence case)

1. **Close evidence** — `close_evidence(case_id)` locks membership (owner only).
2. **Fetch** each evidence item — `fetch_evidence(evidence_id)`. This is the
   nondeterministic `gl.nondet.web.render` call; one item per transaction. Watch
   the retrieval status go `NOT_FETCHED → FETCHED` and a content fingerprint
   appear.
3. **Seal evidence** — `seal_evidence(case_id)`. The case freezes
   (`CASE_FROZEN`) and the evidence-set fingerprint is written.

## 4 · Adjudication (Semantic adjudication panel)

1. **Arm: adjudicate** — `adjudicate(case_id)`. Case → `ADJUDICATING`,
   root → `ENVELOPE_ADJUDICATING`.
2. **Run adjudication** — `run_adjudication(case_id)`. The single semantic step.
   Validators compare the envelope to the sealed evidence with
   `eq_principle.prompt_comparative`.
   - **Success:** a `VerdictRecord` with six ROOT dimension findings and an
     overall verdict — for a faithful envelope, **FAITHFUL**.
   - **Undetermined:** the UI shows a distinct amber state, *no state changed*.
     Click **Re-arm** and **Run** again (3 retries, then a deterministic UNCLEAR
     terminal).

## 5 · (optional) Challenge

Before finality, open the **Challenges** panel:

1. `lock_bond("CHALLENGE")` **+** `challenge_verdict(bond_id, root_id,
   "ROOT_ENVELOPE", ground_code, argument)` — assert one dimension is wrong.
2. **Arm challenge** → **Run re-adjudication** on the challenge case.
   - Verdict flips → `RESOLVED_FLIPPED`, the governing verdict moves, the
     challenger bond is refunded **+ 0.05 GEN reward** from the treasury pool.
   - Verdict stands → `RESOLVED_UNCHANGED`, half the challenger bond is slashed.

## 6 · Finality

**Finalize root** — `finalize(root_id, "ROOT_ENVELOPE")`. Owner-gated (or forced
once the 3-challenge budget is spent). A FAITHFUL envelope → `ENVELOPE_FAITHFUL`
and the root becomes **forkable**.

## 7 · Bond settlement (Bonds panel or the proposal page)

`settle_bond(bond_id)` for the ENVELOPE bond. Deterministic disposition:
FAITHFUL → `SETTLED_FULL_REFUND`. The panel shows `refund / slash / reward`
amounts. A second `settle_bond` is rejected (replay-safe).

## 8 · Fork

On a finalized-FAITHFUL proposal, the **Create a semantic-descendant fork**
panel appears:

1. `lock_bond("FORK_CREATION")` **+** `create_fork(bond_id, parent_id,
   "PARENT_ROOT", parent_fingerprint, delta…, body…)`. The demo fork *narrows* a
   mutable dimension (a fixed 3-day voting period) without touching an immutable
   one.
2. Submit fork evidence, then repeat **close → fetch → seal → adjudicate → run →
   finalize → settle** for the fork.
3. A finalized-FAITHFUL fork is itself forkable — build a second level and watch
   the **proposal tree** grow.

## What to point at in a review

- **Explore + About** prove the frontend reads real production state with no
  backend and no wallet.
- **Step 4** is the whole thesis: an LLM, run as on-chain consensus, deciding
  semantic faithfulness — with the Undetermined path handled honestly.
- **Step 5** shows "challenge, don't vote": disagreement re-runs the
  adjudication instead of tallying.
- **Step 8 + the tree** show governance as a lineage of provable, bonded edits.
