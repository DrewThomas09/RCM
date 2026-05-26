# PEdesk surface ranking system

A repeatable way to decide **which pages deserve to be front-facing** — shown
in the nav bars to PE partners and Chartis PE advisory teams — based on how
much real work went into each page and how useful it is for deal work.

## Why this exists

PEdesk has ~352 routes; 162 are LIVE on real data. But most strong analytic
pages aren't surfaced in the nav — a partner can't find them from the usual
bars. This system ranks every route-backed page so we can (1) see the best per
category and (2) migrate the top ones forward into the nav, mistake-free.

## The two axes (what the partner asked for)

Scored by `scripts/rank_surfaces.py` — deterministic, from real codebase
signals only, **no hand-tuned per-page numbers**:

| Axis | 0–5 | Signal |
|---|---|---|
| **Effort / depth** | renderer LOC (≥1500→5 · ≥800→4 · ≥450→3 · ≥250→2 · ≥100→1) + 0.5 if the page has tests | how much real work the page represents |
| **PE / Chartis-advisory usefulness** | data-honesty tier (green 3 · navy 2 · data-required 1.5 · yellow 1) + 1 if in a core deal-workflow section (Source/Diligence/Portfolio/Pipeline) + 0.5 for a declared `ck_source_purpose` header + 0.5 for real-data wiring | how useful for a partner / advisory team |

**Total = effort + usefulness (0–10).** The full ranked tables — overall top,
per-category, and "buried gems" — live in
[`PEDESK_SURFACE_RANKINGS.md`](PEDESK_SURFACE_RANKINGS.md). Regenerate any time:

```bash
python scripts/rank_surfaces.py
```

## How we use it for front-facing migration

1. **Rank** (this system). Refresh the generated doc.
2. **Read the "buried gems"** — pages that score high but sit in no nav section.
   These are the prime promotion candidates.
3. **Pick the top per category** that aren't already in the sub-nav rail.
4. **Migrate forward**, mistake-free + connected:
   - Add the route to `_SUB_NAV` (its section rail) and `_SUB_SECTION_MAP`
     (so breadcrumbs resolve) in `rcm_mc/ui/_chartis_kit.py`.
   - Confirm the page carries a `ck_source_purpose` header (evidence of what
     it shows + where the data comes from) before promoting it.
   - Verify every inbound/outbound link resolves (no dead `?param` like the
     fixed X-Ray-resolver / market-link bugs — see #921/#922).
   - A promoted page must be green/navy tier (real or honestly-labeled data),
     never yellow/illustrative shown as front-facing fact.
5. **Re-rank** to confirm the nav now leads with the strongest pages.

## Migration gate (front-facing must be "without mistakes")

A page is eligible to be promoted into the nav only if **all** hold:
- Total score ≥ 7.0 (or top-3 of its category).
- Tier is green or navy (real data, or honestly labeled — never illustrative-as-fact).
- Carries a source/purpose header (evidence band).
- All its links resolve (no ignored params / unresolved verticals).
- Has tests.

## Current top (see the generated doc for the full tables)

Overall leaders: `/target-screener` (9.5), `/regulatory-calendar`,
`/payer-stress`, `/diligence/xray`, `/portfolio/risk-scan`. The Source section
already leads with the Target Screener workbench. The clearest promotion
candidates are strong analytic pages that today only have a bare uncategorized
route (e.g. payer-stress, exit-timing, debt-service) — surface them in their
natural section rail.

This is a living system — we iterate on the weights together, then drive the
nav from the result.
