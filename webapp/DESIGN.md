---
version: alpha
name: governance-fork-design
description: "Governance Fork's design system, adapted from an independent analysis of Linear's marketing-site visual language (via getdesign.md/linear.app) for a dense, data-heavy governance application rather than a marketing page. Near-black canvas (#010102), a four-step charcoal surface ladder, hairline borders, and a single chromatic brand accent — Linear's lavender-blue (#5e6ad2) — used scarcely on the brand mark, primary actions, and focus rings. Because this is an in-product UI (proposals, verdicts, bonds, challenges) rather than marketing chrome, it additionally carries a small, disciplined status-tag palette (green / red / orange) for governance outcomes — the same allowance Linear's own real product makes for issue-priority and label colors, which its marketing site doesn't need. Display type is dense and tightly tracked; body copy favors small sizes (12-14px) for data density over the marketing-scale type Linear ships on its homepage."

source: "Independent analysis of linear.app via getdesign.md, adapted for an application UI. Not affiliated with or endorsed by Linear; Linear and its logo are trademarks of their respective owner."

colors:
  primary: "#5e6ad2"
  on-primary: "#ffffff"
  primary-hover: "#828fff"
  primary-focus: "#5e69d1"
  ink: "#f7f8f8"
  ink-muted: "#d0d6e0"
  ink-subtle: "#8a8f98"
  ink-tertiary: "#62666d"
  canvas: "#010102"
  surface-1: "#0f1011"
  surface-2: "#141516"
  surface-3: "#18191a"
  hairline: "#23252a"
  hairline-strong: "#34343a"
  success: "#27a644"
  danger: "#eb5757"
  divergence: "#f2994a" # forks, challenges — Governance Fork's one addition to Linear's palette

typography:
  fontFamily-display: "Inter" # documented substitute for Linear's proprietary display cut
  fontFamily-text: "Inter"
  fontFamily-mono: "JetBrains Mono"
  display-lg: { size: 44px, weight: 600, lineHeight: 1.08, tracking: -1.8px }
  display-md: { size: 30px, weight: 600, lineHeight: 1.15, tracking: -1.0px }
  headline: { size: 20px, weight: 600, lineHeight: 1.25, tracking: -0.4px }
  body: { size: 14px, weight: 400, lineHeight: 1.55, tracking: -0.05px }
  body-sm: { size: 13px, weight: 400, lineHeight: 1.5, tracking: 0 }
  caption: { size: 11.5px, weight: 400, lineHeight: 1.4, tracking: 0 }
  eyebrow: { size: 11px, weight: 500, lineHeight: 1.3, tracking: 0.5px, family: text }
  mono: { size: 11.5px, weight: 400, lineHeight: 1.5, tracking: 0, use: "addresses, hashes, ids, tx status — data, not chrome" }

rounded: { xs: 4px, sm: 6px, md: 8px, lg: 12px, xl: 16px, pill: 9999px }
spacing: { xxs: 4px, xs: 8px, sm: 12px, md: 16px, lg: 24px, xl: 32px, section: 64px }
---

## Why Linear

Governance Fork is a precision instrument — bonds, verdicts, lineage — not a
storefront. Linear's marketing language (near-black canvas, one scarce accent,
hairline-bordered surface ladder, aggressively tight display type) reads as
"software-craft documentation," which is exactly the register a semantic
adjudication registry needs. It replaces the earlier bespoke editorial-serif
theme with a single, externally documented reference so every future screen
stays consistent by construction rather than by memory.

## What changed from the raw Linear analysis

Linear's site is marketing chrome for a SaaS product; Governance Fork **is**
the product. Two deliberate departures, both called out as acceptable by the
source analysis itself ("Known Gaps: Linear's actual product UI uses a richer
color-tag palette... those colors live in the in-product surfaces"):

1. **A status-tag palette.** Marketing-Linear ships one semantic color
   (`success` green). Product-Linear (issue priorities, labels) does not.
   Governance Fork is product surface, so it uses three: `success` (green —
   faithful / settled / refunded), `danger` (red — rejected / slashed /
   invalid), and `divergence` (orange — fork / challenge / open dispute).
   `primary` lavender is reserved, as Linear specifies, for the brand mark,
   primary actions, and active/in-progress state — never decoration.
2. **Denser type.** Linear's marketing scale (80px hero, 16px body) is sized
   for a landing page. Governance Fork's body copy runs 13-14px and captions
   11-12px so proposal lists, ledgers, and lineage trees stay information-
   dense; the display sizes are scaled down to match (see `typography:`
   above) while keeping Linear's signature negative tracking and 600-weight
   display / 400-weight body voice.

## Rules carried over unchanged

- `primary` lavender never fills a card or section background — accent only.
- No gradients, no glow, no drop shadows on dark. Hierarchy comes from the
  surface ladder (`canvas` → `surface-1` → `surface-2` → `surface-3`) plus
  1px hairline borders.
- Buttons are `rounded.md` (8px), never pill. Pills are reserved for status
  badges and toggle chips, per Linear's own usage.
- One typographic voice: display and body share one family (Inter), only the
  weight changes.
- Iterate one `components:` token at a time; this file is the reference for
  every future screen, not just the redesign that introduced it.
