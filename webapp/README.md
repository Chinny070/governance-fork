# Governance Fork — webapp

Production dApp for the Governance Fork Intelligent Contract on GenLayer
StudioNet.

- **Contract:** `0xbA06003F2C254232E4D440B89425abc7Afd4c11A` (StudioNet)
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
| Typed wrapper for all 35 methods; `lock_bond` → consume helpers | `src/lib/api.ts` |
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

### Undetermined handling

`run_adjudication` is the one nondeterministic call. If validators don't reach
consensus, **zero state is committed**. The UI surfaces this as a distinct
"Undetermined" outcome (not a contract rejection) and offers a re-arm/retry —
matching the contract's 3-retry-then-UNCLEAR-terminal behaviour.

## Deployment

GitHub Actions (`.github/workflows/deploy-pages.yml`) runs typecheck + lint +
test + build and publishes `dist/` to GitHub Pages on every push to `main` that
touches `webapp/`. The build sets `VITE_BASE=/governance-fork/` for the project
site path; a `404.html` copy of `index.html` keeps hash-router deep links
working.

To deploy elsewhere, build with `VITE_BASE=/` (or your sub-path) and serve
`dist/` as static files with an SPA fallback to `index.html`.
