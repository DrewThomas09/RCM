# IFT pages — redesign audit & plan (2026-07-10 overnight run)

Working log for the IFT-suite rehaul. Append findings per cycle; this is the
single place that says what was wrong, what the target architecture is, and
what each overnight cycle shipped.

## Cycle 0 — audit findings (all 9 pages rendered offline + screenshotted)

Pages: `/ift-markets` `/ift-mmt` `/ift-clinical` `/ift-study` `/ift-research`
`/ift-diligence` `/ift-sourcing` `/ift-demand` `/ift-hs-demand`
(3.5 MB HTML total; all render, none 500).

### Defects found

1. **Missing CSS for every section header (root cause of the "poor look").**
   `ck_section_header` emits `.sc-eyebrow` / `.sc-h2` — neither class had a
   ruleset anywhere, so on every page the eyebrow rendered as bare full-size
   text stacked over the title ("THE NUMBERS, VISUALLY" + "At a glance" read
   as two headings). 18 headers on `/ift-markets` alone; affects 68 files.
   → FIXED in `_chartis_kit.py` (Cycle 1).
2. **Double-escaping bug**: `/ift-markets` source note showed literal `&AMP;`
   (pre-escaped `&amp;` passed into an escaping helper). → FIXED.
3. **ILLUSTRATIVE saturation**: 473 ILLUSTRATIVE markers across the suite
   (152 on `/ift-markets`, 82 `/ift-clinical`, 60 `/ift-hs-demand`, 49
   `/ift-mmt`). The demand workbook was already purged (GOV/SOURCED/ACADEMIC/
   DERIVED only) but the pages were not. Headline TAM/SAM/SOM KPIs on
   `/ift-markets` all carry ILLUSTRATIVE chips — the opposite of credible.
4. **Content duplication** (measured, shared sentences excluding shell
   chrome ≈25):
   - `/ift-study` ↔ `/ift-diligence`: **118 shared sentences**
   - `/ift-research` ↔ `/ift-diligence`: 79; `/ift-research` ↔ `/ift-study`: 79
     (the insource/outsource archetype taxonomy + operator profiles are
     repeated verbatim on three pages)
   - `/ift-demand`, `/ift-hs-demand`, `/ift-clinical` are three separate
     demand engines with overlapping national funnels and different answers.
5. **Footprint conflict**: `/ift-markets` presents a 20-metro / 6-state
   "target operator footprint" (Omaha…Cleveland, Cincinnati, KC, Wichita,
   Madison, Milwaukee, Twin Cities, Rochester, Des Moines, Crown Point,
   Louisville, NoVA, Cheyenne/Casper) while `/ift-mmt` + the workbooks model
   MMT as 7 CBSAs / 22 counties in NE+IA. Both claim to be "the target".
   The demand-by-region chart on `/ift-demand` mixes the two. Resolve with
   research (which footprint is really MMT's) and label the other honestly
   as the *expansion/roll-up screen*, not the operator footprint.
6. **Chart label truncation**: hbar labels clip ("Crow Point / NW Indi…",
   "share-shi…") — width budget too small; fix in `_chart_kit` label sizing.
7. **KPI strip clutter** on `/ift-mmt`: floating bracket labels
   (`[MSA/µSA] [COUNTY] [POP] [65+] [LEGS] [$]`) render right-aligned in the
   KPI row and read as debris.
8. **All-caps mono paragraph blocks** (source notes, chart subtitles) render
   as shouting; long lede lines ragged. Tone down to sentence case.
9. No page-level horizontal overflow at 1440px (Playwright-verified), but
   long unwrapped tokens exist (~150/page); tables lack scroll containers at
   narrow widths. Add `overflow-x:auto` wrappers.

### Target information architecture (rehaul)

Keep all existing routes live (no dead links), but reorganize around a hub
with 5 clear surfaces + 1 meta page, each with ONE job:

| Surface | Job | Sources of truth |
|---|---|---|
| `/ift` (new hub) | Reading order, what's where, freshness | — |
| `/ift-market` → alias of `/ift-research` rebuilt | The industry: national market size, structural growth drivers (consolidation, specialization, demographics, payment), competitive landscape | evidence registry + new research |
| `/ift-demand` (absorbs `/ift-clinical`, `/ift-hs-demand` as sections) | The demand: national funnel → footprint counties: CDC PLACES prevalence, Census pop/growth, NEDS transfer trends, HCRIS discharge base | `ift_demand_evidence` + new county data modules |
| `/ift-mmt` (absorbs MMT slice of `/ift-markets`) | The company: MMT operations, footprint, hospital-system customers, competitors-in-claims, litigation, model | new `ift_mmt_research` module |
| `/ift-markets` | The geography: metro-by-metro market structure — relabelled honestly (operator footprint vs roll-up screen) | `ift_geo` |
| `/ift-diligence` (absorbs `/ift-study`, `/ift-sourcing`) | The workplan: questions, study synthesis, sourcing prompts | `ift_diligence` |

Old routes 301/alias to their new section anchors. The shared insourcing
taxonomy renders from ONE module in ONE place.

### Grounding rules (no illustrative)

- Adopt the demand-workbook basis contract suite-wide: **GOV / SOURCED /
  ACADEMIC / DERIVED** only. Anything currently ILLUSTRATIVE either (a) gets
  re-derived from a cited input with the equation shown → DERIVED, or (b) is
  cut.
- Every headline number must exist in an evidence registry entry with URL +
  verbatim quote (pattern: `ift_demand_evidence.py`).
- New research (overnight agents) lands as data modules with citations:
  MMT company dossier, NE/IA competitor NPI census, hospital-system
  profiles, CDC PLACES county prevalence, Census county population +
  growth, consolidation/specialization/REH trends.

## Cycle log

- **Cycle 0 (this)**: audit + this plan. Fixed `.sc-eyebrow`/`.sc-h2` CSS,
  `&AMP;` double-escape. 5 research agents launched (MMT dossier,
  competitors/claims, hospital systems, CDC/NEDS/Census linkage,
  consolidation/specialization trends).
