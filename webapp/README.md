# Governance Fork — webapp

Production dApp for the Governance Fork Intelligent Contract on GenLayer
StudioNet.

- **Contract:** `0xD5A1E3b2087d439C36571B50947ddD900741f143` (StudioNet) — Stage
  10 (steward-requested fixes, including a real enforced-duration finality
  challenge period), commit `019630d`
- **Stack:** Vite 6 · React 18 · TypeScript (strict) · `genlayer-js` 1.1.8
- **No backend.** Reads go straight to the StudioNet RPC; writes go through an
  injected wallet (MetaMask). Exploration works with no wallet at all.

## Scripts

```bash
npm install
npm run dev             # dev server on :5173
npm run typecheck       # tsc -b, strict
npm run lint            # eslint, zero warnings
npm test                # vitest — receipt classification, formatting, lineage
npm run verify:shapes   # fetch the live contract schema and check every call
npm run build           # tsc + vite build -> dist/
```

## How it talks to the contract

| Concern | Where |
|---|---|
| Address, chain, explorer URLs | `src/lib/contract.ts` |
| Every enum value + amounts (0.1 GEN bond, 0.05 GEN flip reward) | `src/lib/enums.ts` |
| Client factory, receipt classification (ok / reverted / **Undetermined**) | `src/lib/genlayer.ts` |
| Typed wrapper for all 36 methods; `lock_bond` → consume helpers | `src/lib/api.ts` |
| Wallet connect + StudioNet detection / add-network | `src/lib/wallet.tsx` |
| Transaction lifecycle state machine (sign → mine → re-read → done) | `src/lib/useTx.ts` |

### The bond flow

`lock_bond(purpose)` is the **only** payable method and never reverts for a
policy reason (a reverted payable call would trap the value on this runtime). So
every gated action is a two-step:

```ts
const { bondId } = await lockBond(client, "ENVELOPE");   // payable, 0.1 GEN
await submitRootEnvelope(client, bondId, { ... });        // non-payable
```

### Finality is two transactions, with a real enforced wait

`gl.message_raw["datetime"]` is a genuine, consensus-safe on-chain
timestamp on this runtime (live-proven — see
`docs/STAGE_10_STEWARD_FIXES.md` section 4). `open_finality_window`
(owner-gated) stamps it; `finalize` (permissionless) refuses to run until
a real 72 hours (`CHALLENGE_WINDOW_SECONDS`) have elapsed since that
stamp — a challenge landing at any point in that window is guaranteed to
be seen and blocks finalize.

```ts
await openFinalityWindow(client, targetId, targetKind);
// ... at least 72h later, on-chain time ...
await finalize(client, targetId, targetKind);
```

### Undetermined handling

`run_adjudication` is the one nondeterministic call. If validators don't reach
consensus, **zero state is committed**. The UI surfaces this as a distinct
"Undetermined" outcome (not a contract rejection) and offers a re-arm/retry —
matching the contract's 3-retry-then-UNCLEAR-terminal behaviour.

## Deployment

Live at:

- **https://chinny070.github.io/governance-fork/** — GitHub Pages, via
  `.github/workflows/deploy-pages.yml` (typecheck + lint + test + build on
  every push to `main` touching `webapp/`). Builds with
  `VITE_BASE=/governance-fork/`; a `404.html` copy of `index.html` keeps
  hash-router deep links working.
- **https://governance-fork.vercel.app** — Vercel, auto-deploys from the same
  repo/branch (root-relative `VITE_BASE=/`, no extra config needed).

To deploy elsewhere, build with `VITE_BASE=/` (or your sub-path) and serve
`dist/` as static files with an SPA fallback to `index.html`.
