# GenLayer submission — Governance Fork

Copy-paste fields for the submission form.

---

**Project name**

Governance Fork

**One-liner**

Don't vote YES or NO. Change the proposal. A semantic-descendant DAO governance
registry where an on-chain LLM adjudication decides whether each forked version
faithfully represents its parent's intent.

**Category**

Governance / DAO tooling / Intelligent Contracts

**Live demo**

https://chinny070.github.io/governance-fork/

**Repository**

https://github.com/Chinny070/governance-fork

**Deployed contract (StudioNet)**

`0xbA06003F2C254232E4D440B89425abc7Afd4c11A`
chain 61999 · RPC https://studio.genlayer.com/api
Explorer: https://genlayer-explorer.vercel.app/address/0xbA06003F2C254232E4D440B89425abc7Afd4c11A

**Contract source / integrity**

`contracts/governance_fork.py` @ commit `004dbd4`
SHA-256 `dfe6ebc85cbb38ae1d7a4dcc07924af0facaa819c87289e4fe838c12e7c6e5f5`
ABI: 16 write + 17 view + 2 admin (35 methods)

---

## What it does

A DAO imports a real governance proposal. The proposer submits an **intent
envelope** (objective, scope, essential constraints, mutable vs immutable
dimensions). Community evidence — real web pages — is fetched on-chain with
`gl.nondet.web.render` and frozen. Then **semantic adjudication** runs:
GenLayer validators reach consensus, via `gl.eq_principle.prompt_comparative`,
on whether the envelope faithfully represents the proposal, scoring six named
dimensions.

Instead of voting a proposal up or down, a participant **forks** it: a
semantic-descendant that keeps the intent and declares exactly what it changes.
Each fork runs the same evidence → adjudication pipeline. Anyone can **challenge**
a verdict — which re-runs the adjudication rather than counting a vote. The
output is a **proposal tree**: a root and its descendants, each with a provable,
bonded verdict.

## Why GenLayer

The core mechanic is impossible without an LLM that runs as consensus:
"does this edited proposal still mean what the original meant?" is a semantic
judgement, and GenLayer's optimistic democracy makes that judgement a
first-class on-chain operation with a deterministic, auditable result (including
an honest "Undetermined" when the validators can't agree).

## GenLayer features used

- `gl.eq_principle.prompt_comparative` + `gl.nondet.exec_prompt(response_format="json")` — semantic adjudication
- `gl.nondet.web.render` — on-chain retrieval + freeze of real governance web pages
- `@gl.public.write.payable` + `gl.message.value` + `self.balance` + `gl.get_contract_at(addr).emit_transfer(value=…)` — native GEN bond economics
- deterministic domain-separated SHA-256 fingerprinting throughout for auditability
- `@gl.public.view` dataclass returns with nested `DynArray` fields

## Frontend

Vite + React + TypeScript, `genlayer-js` 1.1.8, **no backend**. Reads stream
from the StudioNet RPC (works with no wallet); writes go through MetaMask on
StudioNet. Covers the full lifecycle, distinguishes contract-revert from
Undetermined, re-reads authoritative state after every write, and visualises the
proposal tree. Deployed to GitHub Pages via CI that also runs typecheck, lint
and tests.

## Verification

- Contract: `python -m unittest discover -s tests` (Stage 7/8/9 suites +
  static ABI checks) — all pass.
- Live end-to-end proven on StudioNet across successive CLI deployments:
  capture, real web render (deterministic content fingerprint), FAITHFUL /
  Undetermined / retry-terminal adjudication, challenge resolution, fork
  lineage to depth 2, and every bond disposition (full refund / partial slash /
  flip reward / replay rejection / pause safety).
- Frontend: `npm run verify:shapes` checks all 35 call shapes against the live
  contract schema; the deployed dApp was verified reading real production state.

## Demo script

`docs/DEMO.md` — a full run using a real proposal (ratifying the Arbitrum
Constitution).

## Known limitation

On StudioNet (no full EVM layer) the final EOA credit of a bond refund does not
land — every **contract-side** movement (capture into balance, deduction on
settlement, treasury accounting) is exact and on-chain, and the EOA leg lands on
a full chain layer (Testnet Bradbury / mainnet). Documented in
`docs/STAGE_9_GEN_BOND_ECONOMICS.md`.
