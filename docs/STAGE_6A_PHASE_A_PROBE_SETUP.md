# Stage 6a — Phase A: Isolated Web-Render Probe Contract

**Status: Phase A only.** This document covers the isolated probe contract, its local/static verification, and the exact live-probe plan for Phase B. **No live probe transaction has been issued. No deployment has occurred.** Phase B (actually running probes against Studio/StudioNet) requires your explicit approval after this contract's schema loads cleanly in Studio.

**Correction incorporated.** Per your explicit instruction, this probe tests `gl.nondet.web.render(...)` specifically — not `gl.nondet.web.get(...)`. Governance Fork's production evidence direction is `render()`, per your reviewer's requirement, regardless of the docs' own general preference for `get()` on stable content (see §1 below). The probe does not redesign around get-vs-render; it measures whether `render()` itself is production-viable for the five governance-source classes.

---

## 1. Verified current official API (re-checked before writing code)

Re-fetched from `https://docs.genlayer.com/developers/intelligent-contracts/examples/fetch-web-content` and `https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism` immediately before implementation.

| Item | Finding |
|---|---|
| `gl.nondet.web.render(url, mode)` | Confirmed current. `mode` is a required-by-convention keyword; documented values are `"text"` and `"html"`. |
| `gl.nondet.web.render(url, mode, wait_after_loaded="5s")` | Confirmed current. `wait_after_loaded` is an optional keyword, duration-string format (e.g. `"5s"`). Docs: "the browser waits briefly after the page load event before returning content." Docs explicitly warn dynamic pages may still vary between validators even with this set. |
| Equivalence wrapping | Docs show `gl.eq_principle.strict_eq(leader_fn)` wrapping a single-line leader function that returns the fetch result directly — no branching inside the leader function in the documented example. |
| `gl.nondet.web.get(url)` | Still documented, described as the **preferred default for stable APIs and static pages**. **Not used in this probe** per your explicit instruction — production direction is `render()` regardless of this general guidance. This is a noted tension, not an oversight. |
| `prompt_comparative` / `prompt_non_comparative` | Not shown wrapping any web-fetch call in current docs. Not used in this probe. |
| Undetermined / timeout | **Not explicitly documented** for web fetch specifically. This absence is itself one of the things Stage 6a Phase B is meant to establish empirically. |

**Design consequence:** the probe's leader functions are kept to a single `return gl.nondet.web.render(...)` line each, matching the documented shape exactly, with mode/wait-variant selection happening in plain deterministic Python *before* any leader function is chosen — never as a branch inside a leader function.

## 2. Probe contract

**Path:** [contracts/probe/web_render_probe.py](contracts/probe/web_render_probe.py)

**Isolation guarantee:** this file is not imported by, does not reference, and is not referenced by `contracts/governance_fork.py`. Verified by static check `production contract unaffected` — `governance_fork.py` contains zero occurrences of `gl.nondet.`, `gl.eq_principle.`, or `web_render_probe`.

### 2.1 Shape

```python
# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass

import hashlib
```

Same header/import discipline as the production contract (version tag, single-line Depends, `dataclass` imported explicitly — the exact gap that broke Stage 2's first schema-load attempt).

### 2.2 Storage

```
probes:        TreeMap[u256, ProbeResult]
probe_order:   DynArray[u256]
next_probe_id: u256
```

`ProbeResult` fields: `url`, `url_class`, `mode`, `wait_after_loaded`, `content_length: u32`, `content_fingerprint: bytes`, `content_preview: str` (first 256 chars of the bounded slice), `submitted_at: u256` (sentinel `0`; runtime timestamp unconfirmed, same limitation as the production contract).

### 2.3 ABI (3 methods)

- `run_probe(url: str, url_class: str, mode: str, wait_after_loaded: str) -> u256` — **write**. Validates all inputs deterministically, then calls `gl.nondet.web.render(...)` wrapped in `gl.eq_principle.strict_eq(...)`, then deterministically hashes and stores a bounded slice of the result.
- `get_probe(probe_id: u256) -> ProbeResult` — **view**.
- `list_probes(cursor: u256, limit: u32) -> DynArray[u256]` — **view**, bounded pagination (`PAGINATION_LIMIT_MAX = 50`).
- `get_probe_count() -> u256` — **view**.

No payable methods. No native GEN anywhere.

### 2.4 Why no try/except around the nondet call

Deliberately absent. Wrapping `gl.eq_principle.strict_eq(...)` in a `try/except` would let the contract silently swallow exactly the failure/Undetermined signal Stage 6a exists to observe. Phase B instead watches Studio's own transaction result panel (Consensus Result, final contract state, logs) for each probe call — that is the actual measurement instrument, not a contract-internal catch block. Verified by static check `no try/except around nondet calls`.

### 2.5 Content handling

- `content[:MAX_PROBE_SLICE]` (16 KiB) bounds the stored preview before any further processing — same provisional cap as the production contract's `MAX_EVIDENCE_SLICE`, deliberately kept identical so Phase B's findings translate directly to production sizing.
- `hashlib.sha256(sliced.encode("utf-8")).digest()` — same hashing idiom as `governance_fork.py`.
- `content_preview` stores only the first 256 characters for on-chain-cheap human inspection; the full slice is not stored to keep the probe contract itself bounded.

## 3. Local/static verification (Phase A gate)

Run: `python tests/stage_6a_probe_checks.py`

**Result: 13/13 checks passed.**

| Check | Result |
|---|---|
| Python syntax | PASS |
| ASCII-only | PASS (6 124 bytes) |
| LF-only line endings | PASS |
| Uses `gl.nondet.web.render(` | PASS |
| Does NOT use `gl.nondet.web.get(` | PASS |
| Render calls wrapped in `strict_eq` | PASS (4 leader functions, 4 render call sites, 2 `strict_eq` call sites reached via deterministic dispatch) |
| No `prompt_comparative`/`prompt_non_comparative` | PASS |
| No `gl.message.value` | PASS |
| No `transfer(` | PASS |
| Isolated from `governance_fork.py` | PASS |
| No try/except around nondet calls | PASS |
| Production contract unaffected | PASS |
| ABI shape matches design | PASS (`run_probe` write; `get_probe`, `list_probes`, `get_probe_count` views) |

**Contract metrics:** SHA-256 `2c953002a51b9cbb64b16867837de78bfb9083dbac5312b729f0b99179119e1a` · 6 124 bytes · 181 lines.

These checks confirm **shape and schema-safety only**. They cannot and do not verify live `render()` behavior, consensus outcomes, or `Undetermined` handling — that requires an actual Studio schema-load followed by live probe transactions (Phase B), which have not been run.

## 4. Exact probe corpus (Phase B plan — not yet executed)

Five URL classes per the locked corpus. Concrete candidate URLs are proposed here for your review before any live call is made; you may substitute equivalents.

| # | `url_class` | Candidate URL | `mode` | `wait_after_loaded` | Rationale |
|---|---|---|---|---|---|
| 1 | `SNAPSHOT_PROPOSAL` | A specific Snapshot.org proposal page, e.g. `https://snapshot.org/#/uniswap/proposal/<id>` (final id TBD — Snapshot is a client-rendered SPA) | `text` | `"5s"` | Client-rendered; needs render + wait to get past the JS shell. |
| 2 | `TALLY_PROPOSAL` | A specific Tally.xyz governance proposal page, e.g. `https://www.tally.xyz/gov/<dao>/proposal/<id>` | `text` | `"5s"` | Also client-rendered (React SPA); same JS-wait requirement. |
| 3 | `DAO_FORUM` | A specific Discourse-based governance forum thread (e.g. Uniswap's `gov.uniswap.org` or a comparable DAO's Discourse) | `text` | `"3s"` | Mostly server-rendered but often has some client hydration; shorter wait as a first probe, adjustable. |
| 4 | `OFFICIAL_DOCS` | A specific static documentation page (e.g. a DAO's governance-process doc, or GenLayer's own docs page as a stable baseline) | `text` | `""` (no wait) | Static content; tests the render pathway's baseline behavior without the wait-time variable. |
| 5 | `TREASURY_REPORT` | A specific DAO treasury/budget report page (e.g. a Karpatkey or Llama-style treasury dashboard, or a static forum-hosted report) | `text` | `"5s"` | Treasury dashboards are frequently client-rendered (charts, live balances); tests render under realistic dynamic-content load. |

**Exact final URLs are not selected in this document** — picking a specific, currently-live proposal/thread/report is a Phase B action, done immediately before the live run so the page is confirmed reachable and content-bearing at test time. I will propose exact URLs for your sign-off in the Phase B request rather than baking possibly-stale URLs into this Phase A doc.

`mode="html"` is not part of the primary Phase B pass — Governance Fork's evidence pipeline consumes readable text, not markup. If `text` mode underperforms on a given source, an `html`-mode retry on the SAME url_class can be run as a secondary probe using the same contract (already supported by the ABI) before concluding that source is unusable.

## 5. Phase B measurement plan (not yet executed)

For each of the 5 (or more, if `html`-mode retries are needed) probe calls:

1. **Render success/failure** — did the transaction commit, or did it revert/hang?
2. **Committed consensus** — did validators reach agreement under `strict_eq`?
3. **Consensus Result** — Studio's own reported outcome for the transaction (success / error / Undetermined).
4. **Final contract state** — does `get_probe(id)` return a populated `ProbeResult`, or does no record exist because the write never completed?
5. **Rendered text usefulness** — manual inspection of `content_preview` (and, if needed, a temporary larger preview for manual review) for whether the extracted text actually contains the governance-relevant content, not just chrome/cookie-banner/JS-shell noise.
6. **Rendered content length** — `content_length` vs `MAX_PROBE_SLICE`; is the page usefully small, or truncated before anything useful appears?
7. **Repeatability** — call `run_probe` again with identical parameters within a short window; compare `content_fingerprint` across the two `ProbeResult` records.
8. **Dynamic-content instability** — for pages expected to be JS-heavy (Snapshot, Tally, treasury dashboards), does repeatability hold, or does `strict_eq` struggle to converge?
9. **Undetermined behavior** — if a transaction reports Undetermined, record exactly how Studio surfaces it and whether/how retrying behaves.
10. **Timeout behavior** — if a call hangs or errors after a long delay, record the exact duration and Studio's error text.
11. **`wait_after_loaded` appropriateness** — does `"5s"` prove sufficient, insufficient, or excessive for each dynamic source? Adjust and re-run if a source fails only on this parameter.
12. **Content bounding realism** — does `MAX_PROBE_SLICE = 16 KiB` capture the useful part of the page, or truncate before reaching the proposal text (common on pages with large navigation/header HTML before body content)?
13. **`strict_eq` viability** — is bit-exact agreement realistic for this source class at all, or does the source's content genuinely vary per-fetch (ads, randomized IDs, live-updating data) in a way no amount of tuning fixes?

**A render failure on any source is a recorded finding, not a reason to substitute `get()`, a backend scraper, a proxy, or manually pasted content.** If a source class cannot reliably render, Stage 6a's report will say so plainly, and Governance Fork's production scope will be restricted to the source classes that do work — per the documented fail-response options in `docs/STAGE_1_ARCHITECTURE_AND_AUDIT.md` §10.4.

## 6. Expected Studio schema (for your manual verification)

When you load `contracts/probe/web_render_probe.py` in Studio, expect:

- Constructor: `__init__()` — no parameters, no return annotation.
- **1 write method:** `run_probe(url: str, url_class: str, mode: str, wait_after_loaded: str) -> u256`.
- **3 view methods:** `get_probe(probe_id: u256) -> ProbeResult`, `list_probes(cursor: u256, limit: u32) -> DynArray[u256]`, `get_probe_count() -> u256`.
- `ProbeResult` resolves as an `@allow_storage @dataclass` return type with fields `url, url_class, mode, wait_after_loaded, content_length, content_fingerprint, content_preview, submitted_at`.
- No payable methods.
- Storage panel shows `probes` (TreeMap), `probe_order` (DynArray), `next_probe_id` (u256).

## 7. What Phase A does NOT do

- Does not issue any live transaction.
- Does not deploy anything.
- Does not touch `contracts/governance_fork.py`.
- Does not select final live URLs (candidates only, pending your review).
- Does not attempt `gl.nondet.web.get`, `prompt_comparative`, `prompt_non_comparative`, native GEN, or any backend/proxy/scraping substitute.

## 8. Next step — explicit gate

**Stop here for manual Studio schema-load approval**, per your instruction. Please:

1. Load `contracts/probe/web_render_probe.py` in GenLayer Studio (same non-deploy schema-load workflow used for the production contract in prior stages).
2. Confirm the schema matches §6 above.
3. Report the result back.

Once schema-load passes, the next step (still requiring your separate explicit approval) is Phase B: selecting exact live URLs per §4 and running the actual probe transactions, observing them per §5, and producing `docs/STAGE_6A_WEB_RENDER_PROBE_REPORT.md` with the pass/fail decision against the criteria in `docs/STAGE_1_ARCHITECTURE_AND_AUDIT.md` §10.4.

**Stage 6b (production evidence retrieval) does not begin until the Phase B report is complete and approved.**
