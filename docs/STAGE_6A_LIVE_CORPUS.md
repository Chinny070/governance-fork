# Stage 6a — Frozen Live Probe Corpus

**Status: corpus frozen before any live transaction.** This document is committed BEFORE any live probe transaction is issued, per the Phase B instruction. If a primary URL later disappears or becomes unavailable, that is recorded as a result in the eventual `STAGE_6A_WEB_RENDER_PROBE_REPORT.md` — this corpus is **not** silently replaced to improve the pass rate.

**Verification method disclosure:** every finding below comes from **ordinary public inspection** (WebSearch + a non-JS-executing text-fetch tool) performed purely for corpus selection. This inspection proves the pages are real, specific, public, and currently reachable by *some* client. **It is not evidence of what GenLayer's `gl.nondet.web.render(...)` will do** — several notes below flag exactly where the two are expected to diverge (e.g., a plain HTTP fetch cannot execute JavaScript or resolve a client-side hash route; GenLayer's renderer is expected to run a real browser and may behave very differently). Only the live GenLayer probe (Phase B, not yet run) counts as capability evidence.

## 0. API re-verification (immediately before finalizing this corpus)

Re-fetched `https://docs.genlayer.com/developers/intelligent-contracts/examples/fetch-web-content` moments before writing this document.

| Item | Phase A (prior check) | Now | Changed? |
|---|---|---|---|
| `gl.nondet.web.render(url, mode)`, modes `text`/`html` | Confirmed | Confirmed | No |
| `wait_after_loaded="5s"`-style duration string | Confirmed | Confirmed | No |
| `gl.eq_principle.strict_eq(leader_fn)` wrapping | Confirmed | Confirmed | No |
| `gl.nondet.web.get()` preferred for stable/static content | Documented | Documented, page shows "Last updated: 2026-06-11" | No material change |
| `prompt_comparative`/`prompt_non_comparative` wrapping web fetch | Not shown | Not shown | No |

**No material change since Phase A.** The probe contract in `contracts/probe/web_render_probe.py` remains an accurate implementation of the current documented pattern. Proceeding on that basis.

## 1. Primary corpus (5 sources, fixed execution order)

### SOURCE_1_SNAPSHOT

| Field | Value |
|---|---|
| `url_class` | `SNAPSHOT_PROPOSAL` |
| URL | `https://snapshot.org/#/s:uniswapgovernance.eth/proposal/0x0242a914c60945d25873d2a98c6abd9f69cb889c6616e27f3c0ab759f9e8d783` |
| Protocol/DAO | Uniswap (space `uniswapgovernance.eth`) |
| Page title (per source) | "[Temp Check] Protocol Fee Expansion: Eight More Chains and Remaining Mainnet v3 Pools" |
| Discovery path | Found via the corresponding governance-forum thread (SOURCE_3), which embeds this exact Snapshot link verbatim — not guessed, not constructed. |
| Why representative | A live, specific, currently-referenced off-chain governance vote on Snapshot, the canonical "Snapshot-style governance proposal" class. |
| Expected useful content if render succeeds | Proposal title, description of the 8-chain fee expansion, tier-based fee structure, vote choices, current vote tallies. |
| JS-heavy / dynamic? | **Confirmed JS-heavy by direct inspection.** A plain fetch of this exact URL returned only the string `"Snapshot"` and decorative dashes — no proposal-specific text of any kind. Same empty-shell result was independently observed on the bare `uniswapgovernance.eth` space page during corpus research. |
| Technical risk flag | This URL uses a **client-side hash route** (`#/s:.../proposal/...`). A plain HTTP GET always returns the same base `index.html` regardless of the fragment — the server never sees it. Only a JS-capable renderer that executes client-side routing based on `window.location.hash` can resolve the specific proposal. This is a **likely** (not yet observed under GenLayer) failure mode distinct from "page unavailable": even a technically successful fetch could return the *space's default view* rather than this specific proposal if the renderer doesn't fully execute the SPA's router. |
| Predeclared primary config | `mode="text"`, `wait_after_loaded="5s"` — **wait included in the primary attempt**, not held back as a diagnostic, because client-rendering is already confirmed rather than merely suspected (per Phase B §7's explicit allowance for predeclaring a wait-inclusive primary when a source is *known* to be client-rendered). |

### SOURCE_2_TALLY

| Field | Value |
|---|---|
| `url_class` | `TALLY_PROPOSAL` |
| URL | `https://www.tally.xyz/gov/arbitrum/proposal/52793687237294107439411688810483120161857085958258363826553939061522164665920?govId=eip155%3A42161%3A0x789fC99093B09aD01C34DC7251D0C89ce743e5a4` |
| Protocol/DAO | Arbitrum DAO |
| Page title (per source) | "ARB Staking: Unlock ARB Utility and Align Governance" |
| Why representative | A specific, real on-chain governance proposal on Tally, the canonical "Tally / on-chain governance interface" class. |
| Expected useful content if render succeeds | Proposal abstract, motivation, $200,000 ARB funding breakdown (smart contract dev, Tally integration, Karma score integration, audits, working-group operations), timeline, specification. |
| JS-heavy / dynamic? | Tally is a React single-page app, but a plain fetch of this URL **unexpectedly returned full, meaningful proposal text** (abstract, motivation, rationale, specification, timeline, cost breakdown) — not an empty shell. This suggests server-side rendering or static pre-rendering for this route, but is not certain; GenLayer's actual renderer may still behave differently. |
| Predeclared primary config | `mode="text"`, no wait — matches the default recommendation for a source not conclusively confirmed to need client-side wait time. |

### SOURCE_3_FORUM

| Field | Value |
|---|---|
| `url_class` | `DAO_FORUM` |
| URL | `https://gov.uniswap.org/t/temp-check-protocol-fee-expansion-eight-more-chains-and-remaining-mainnet-v3-pools/26035` |
| Protocol/DAO | Uniswap Governance (Discourse forum) |
| Page title (per source) | "[Temp Check] Protocol Fee Expansion: Eight More Chains and Remaining Mainnet v3 Pools" — same underlying proposal as SOURCE_1, different platform (the Discourse discussion thread vs. the Snapshot voting page). Deliberately paired: this gives Stage 6a a reviewer-legible narrative (same real proposal, two platforms, two render outcomes) without weakening either as an independent technical test. |
| Why representative | A specific, substantive governance-forum discussion thread, the canonical "DAO governance forum" class. |
| Expected useful content if render succeeds | Proposal rationale, community discussion, the embedded Snapshot link itself, technical details of the fee-tier changes across 8 chains. |
| JS-heavy / dynamic? | Discourse forums are typically server-rendered for crawlability. A plain fetch of this URL returned full substantive content (proposal text, chain list, fee mechanism description) without any wait or JS execution. |
| Predeclared primary config | `mode="text"`, no wait. |

### SOURCE_4_DOCS

| Field | Value |
|---|---|
| `url_class` | `OFFICIAL_DOCS` |
| URL | `https://developers.uniswap.org/docs/ecosystem/governance/governance-process` |
| Protocol/DAO | Uniswap (official developer documentation domain) |
| Page title (per source, via search index) | "Governance Process \| Uniswap Developers" |
| Why representative | Official protocol governance-process documentation, the canonical "official DAO/protocol governance documentation" class. |
| Expected useful content if render succeeds | The three-phase governance process (RFC → Temperature Check → on-chain Governance Proposal), vote thresholds (10M UNI temperature-check threshold, 40M UNI proposal threshold), and timeframes (7-day RFC discussion, 5-day temperature check). |
| JS-heavy / dynamic? | **Verification caveat:** my own fetch tool was repeatedly 303-redirected to an `llms.mdx` machine-readable content variant at this domain — a content-negotiation artifact (the docs site appears to serve a markdown variant to automated/bot-identifying clients) rather than a JS-gating issue. A real browser (and, presumably, GenLayer's renderer) would not trigger this redirect and should reach the normal HTML page directly. Documentation sites of this kind (Docusaurus/Nextra-style) are typically statically generated and not JS-gated for content. Existence, title, and official-domain status are confirmed via search index; full-content confirmation via direct fetch was not obtained due to the redirect behavior described. |
| Predeclared primary config | `mode="text"`, no wait. |

### SOURCE_5_TREASURY

| Field | Value |
|---|---|
| `url_class` | `TREASURY_REPORT` |
| URL | `https://gov.uniswap.org/t/uniswap-foundation-summary-fy-2025-financials/26068` |
| Protocol/DAO | Uniswap Foundation (published on the official governance forum) |
| Page title (per source) | "Uniswap Foundation: Summary FY'2025 Financials" |
| Why representative | The Uniswap Foundation's own published annual financial summary — an official treasury/budget report, the canonical "treasury / financial governance report" class. |
| Expected useful content if render succeeds | Treasury composition ($49.9M cash/stables, 15.1M UNI, 240 ETH; $85.8M total), grant activity ($26M committed, $11M disbursed, $106.2M total allocated), operating expenses ($9.7M), and runway (through January 2027). |
| JS-heavy / dynamic? | Confirmed by direct fetch: "fully static/rendered HTML with embedded images and tables." Full figures were retrievable without any wait or JS execution. |
| Predeclared primary config | `mode="text"`, no wait. |

## 2. Negative control (not one of the five classes)

| Field | Value |
|---|---|
| Label | `NEGATIVE_CONTROL` |
| URL | `https://gov.uniswap.org/t/this-thread-does-not-exist-negative-control-9999999999/9999999999` |
| Purpose | Observe how `gl.nondet.web.render(...)` + `gl.eq_principle.strict_eq(...)` behaves when the target page cannot be retrieved (does not exist). |
| Verified via ordinary inspection | Confirmed: plain HTTP fetch returns a clean `404 Not Found` at the Discourse forum's own domain — a deterministic, stable, safe unavailable-page target under a domain already part of the corpus. |
| Predeclared config | `mode="text"`, no wait. |
| Assumed failure mode | **None assumed in advance.** Per instruction, the actual behavior (revert, error, hang, Undetermined, or something else) is recorded as observed, not predicted. |

## 3. Execution order (fixed)

```
1. SOURCE_1_SNAPSHOT   (mode=text, wait=5s)
2. SOURCE_2_TALLY      (mode=text, no wait)
3. SOURCE_3_FORUM      (mode=text, no wait)
4. SOURCE_4_DOCS       (mode=text, no wait)
5. SOURCE_5_TREASURY   (mode=text, no wait)
6. NEGATIVE_CONTROL    (mode=text, no wait)
```

Each of the five primary sources that succeeds once will be re-run a second independent time with the identical configuration to test repeatability, per the Phase B repeatability gate. Wait-enabled or HTML-mode diagnostic retries are permitted only after a primary attempt underperforms, and are labeled `DIAGNOSTIC_WAIT` / `DIAGNOSTIC_HTML` — they never replace or erase the primary result.

## 4. What this document does NOT do

- Does not report any live GenLayer render result — none has been attempted.
- Does not deploy anything.
- Does not modify `contracts/governance_fork.py` or `contracts/probe/web_render_probe.py`.
- Does not substitute `gl.nondet.web.get()`, a backend scraper, a proxy, or manually pasted content for any source.
