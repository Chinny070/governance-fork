# Governance Fork

**Don't vote YES or NO. Change the proposal.**

Governance Fork is a semantic-descendant DAO governance registry, built as a
[GenLayer](https://genlayer.com) Intelligent Contract. Instead of an up/down
vote, a participant creates a **fork** of a proposal — a new version that keeps
the original intent and declares exactly what it changes. An on-chain LLM
adjudication (GenLayer's optimistic-democracy consensus) decides whether each
version *faithfully represents its parent's intent*. Anyone can **challenge** a
verdict; the challenge is re-adjudicated, never counted as a vote.

| | |
|---|---|
| **Production contract** | [`0xbA06003F2C254232E4D440B89425abc7Afd4c11A`](https://genlayer-explorer.vercel.app/address/0xbA06003F2C254232E4D440B89425abc7Afd4c11A) |
| **Network** | GenLayer StudioNet (chain `61999` / `0xf22f`, RPC `https://studio.genlayer.com/api`) |
| **Contract source** | [`contracts/governance_fork.py`](contracts/governance_fork.py) — commit `004dbd4` |
| **Source SHA-256** | `dfe6ebc85cbb38ae1d7a4dcc07924af0facaa819c87289e4fe838c12e7c6e5f5` |
| **ABI** | 16 write + 17 view + 2 admin (35 methods); `lock_bond` is the only payable method |
| **Frontend** | [`webapp/`](webapp/) — Vite + React + TypeScript, deployed to GitHub Pages |

---

## The idea

Traditional token voting collapses a rich proposal into a single bit. Governance
Fork keeps the proposal editable:

1. A DAO **imports** a real governance proposal and its authoritative URL.
2. The proposer submits an **intent envelope**: the objective, scope, essential
   constraints, and which dimensions are *mutable* vs *immutable*.
3. Community **evidence** (real web pages) is fetched and frozen on-chain via
   `gl.nondet.web.render`, then the envelope is **adjudicated** — validators
   reach semantic consensus on whether it faithfully represents the proposal.
4. Anyone can **fork** a FAITHFUL proposal: a descendant that preserves the
   intent and declares its delta (`NARROWED`, `BROADENED`, `RESHAPED`,
   `REMOVED`, `ADDED`). The fork runs the same evidence → adjudication pipeline.
5. A **challenge** asserts that a specific adjudication dimension is wrong and
   triggers a re-adjudication — it does not "vote against" anything. A
   successful challenge (verdict flips) earns a reward; a failed one is slashed.
6. **Finality** freezes a proposal or fork. The result is a **proposal tree**:
   the root and every semantic descendant, each with a provable verdict.

Every economically meaningful action is backed by a **0.1 GEN bond** with a
deterministic, replay-safe disposition (`refund + slash == amount` always).

---

## Repository layout

```
contracts/governance_fork.py     the production Intelligent Contract (final)
contracts/probe/                 isolated runtime probes (value transfer, storage)
tests/                           Python unittest suite + static ABI checks
docs/STAGE_*.md                  per-stage design + audit notes
webapp/                          the production dApp (this is what gets deployed)
docs/DEMO.md                     end-to-end demo script
docs/SUBMISSION.md               GenLayer submission fields
```

## The contract

`contracts/governance_fork.py` is a single-file GenLayer Intelligent Contract
(`# v0.2.16`). Highlights:

- **Semantic adjudication** — `adjudicate` (arm) then `run_adjudication` (the one
  nondeterministic step) using `gl.eq_principle.prompt_comparative` over
  `gl.nondet.exec_prompt(response_format="json")`, evidence budget 16384. Six
  ROOT dimensions / seven FORK dimensions, each with a per-dimension finding.
- **Undetermined = zero state.** A run with no validator consensus commits
  nothing; re-arm and run again (3 retries, then a deterministic UNCLEAR
  terminal).
- **Challenge + finality state machine** — bounded challenge count, verdict
  history, forced finality once the challenge budget is spent so an absent owner
  can't brick a proposal.
- **Native GEN bond economics** — `lock_bond` (the sole payable method, and it
  *never* reverts for a policy reason — see below) then a non-payable action
  consumes the bond. The contract is its own treasury; a challenger-flip reward
  is drawn from real prior slashes.

### Runtime findings baked into the design

These were discovered by live probing the pinned GenVM runtime and each shaped
the final contract (full detail in `docs/`):

| Finding | Consequence |
|---|---|
| A reverted **payable** call keeps the attached value while rolling back state | `lock_bond` is the only payable method and has exactly one rejection (`value == 0`, which traps nothing); every gated action is non-payable |
| `DynArray[T]()` / `gl.storage.inmem_allocate` fail on this runtime | plain `[]` literals for in-body array construction |
| `TreeMap[K, DynArray[V]]` does not autovivify | explicit `if key not in m: m[key] = []` guards |
| Dataclass-typed **method parameters** arrive as plain `dict` | envelope/body/delta cross the ABI as parallel primitive arrays |
| No block-time source | challenge windows are owner-gated actions, not timestamps |
| StudioNet has no full EVM layer | contract-side GEN accounting is exact and on-chain; the final EOA credit of a refund is a documented StudioNet simulation gap that lands on a full chain layer |

### Running the contract tests

```bash
python -m unittest discover -s tests -v
python tests/stage_2_checks.py
```

## The frontend

See [`webapp/README.md`](webapp/README.md). Quick start:

```bash
cd webapp
npm install
npm run dev            # http://localhost:5173
npm run typecheck && npm run lint && npm test && npm run build
npm run verify:shapes  # checks every call shape against the live contract
```

The dApp reads directly from StudioNet (no backend, no wallet needed for
exploration) and writes through an injected wallet (MetaMask) on StudioNet. It
covers the full lifecycle: DAO → root proposal → bond lock → intent envelope →
evidence (close / fetch / seal) → adjudication → verdict → challenge → finality →
bond settlement → fork → proposal tree.

## Demo

[`docs/DEMO.md`](docs/DEMO.md) walks a real proposal (ratifying the Arbitrum
Constitution) through every stage in the UI.

## License

MIT
