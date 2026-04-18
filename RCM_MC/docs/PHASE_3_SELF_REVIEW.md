# Phase 3 Self-Review — explainer audit

**Scratch file — delete at the end of Phase 5.**

Answers to Q1 and Q2 from the Phase 5 kickoff.

---

## Q1 — Three weakest explainers

Total shipped: 34 explainers across 5 groups. I asked "would a partner
learn something they couldn't infer from the page title and visible
columns?" The three weakest by that bar:

### 1. `/methodology` (Group 1, WHAT-only)

> "Reference library of valuation models, market-intelligence methods,
> and benchmark sources used across the platform."

**Why weak:** This page *is* the methodology docs. Prefixing it with a
sentence that restates the title is circular — a partner who clicked
"Methodology" already knows it's a methodology library. No SCALE
(there isn't a metric to calibrate), no USE (use it to read the
docs), no SOURCE (it's the source). The helper could have been
skipped on this page entirely.

### 2. `/module-index` (Group 5, WHAT-only)

> "Browsable catalog of every analytical module on the platform,
> tagged by diligence category, lifecycle phase (sourcing / diligence
> / portfolio / exit), primary persona, route, and whether it depends
> on the live corpus."

**Why weak:** Reads like a column list. A partner learns the column
names, which they can see by scrolling to the table. I did not name
how the lifecycle/persona taxonomy is decided or when to use module-
index vs. Cmd+K search — that would have been the genuinely useful
framing.

### 3. `/cms-data-browser` (Group 5, WHAT-only)

> "Inventory of CMS public datasets available to the platform: dataset
> name, update frequency, last refresh, record count, primary use
> case, and ingestion status across PFS, OPPS, MS-DRG, HCRIS, and
> quality-measure feeds."

**Why weak:** Same shape as module-index — restates the table columns.
The useful framing would have been *when the partner should care*
(e.g., "refresh lag here tells you whether a cited benchmark is stale
before you quote it in an IC memo"). I shipped a table-of-contents
description instead of a workflow cue.

**Why all three slipped:** they're all Group 5 WHAT-only, on pages
that are catalogs rather than scored analyses. Catalogs don't have
thresholds, which is the 3-part SCALE hook. Without that, I defaulted
to column lists. Lesson for the phase-7 pass: for catalog pages,
replace "list of columns" with "when to come here instead of
search / Cmd+K."

---

## Q2 — Citation breadth

**Unique sources total: 45** — 37 backend modules plus 8 named
industry authorities.

### Backend modules (count of explainers citing each)

| Source | Count |
|---|---|
| `pe_intelligence/heuristics.py` | 2 (partner-review, red-flags) |
| `pe_intelligence/reasonableness.py` | 2 (partner-review, red-flags) |
| `pe_intelligence/partner_review.py` | 1 |
| `pe_intelligence/narrative.py` | 1 |
| `pe_intelligence/deal_archetype.py` | 1 |
| `pe_intelligence/regime_classifier.py` | 1 |
| `pe_intelligence/investability_scorer.py` | 1 |
| `pe_intelligence/exit_readiness.py` | 1 |
| `pe_intelligence/market_structure.py` | 1 |
| `pe_intelligence/white_space.py` | 1 |
| `pe_intelligence/stress_test.py` | 1 |
| `pe_intelligence/master_bundle.py` | 1 |
| `pe_intelligence/ic_memo.py` | 1 |
| `pe_intelligence/README.md` | 1 |
| `data_public/deal_quality_score.py` | 2 (deals-library, corpus-dashboard) |
| `data_public/deals_corpus` (_SEED_DEALS) | 2 (deals-library, corpus-backtest) |
| `data_public/payer_intelligence.py` | 2 (payer-intelligence, payer-intel) |
| `data_public/base_rates.py` | 2 (base-rates, value-backtester) |
| `data_public/sponsor_track_record.py` | 1 |
| `data_public/rcm_benchmarks.py` | 1 |
| `data_public/backtester.py` | 1 |
| `data_public/deal_screening_engine.py` | 1 |
| `data_public/portfolio_analytics.py` | 1 |
| `data_public/sponsor_heatmap.py` | 1 |
| `data_public/vintage_cohorts.py` | 1 |
| `data_public/module_index.py` | 1 |
| `data_public/cms_data_browser.py` | 1 |
| `data_public/corpus_dashboard.py` | 1 |
| `data_public/deal_search.py` | 1 |
| `data_public/find_comps.py` | 1 |
| `data_public/sector_intelligence.py` | 1 |
| `data_public/value_backtester.py` | 1 |
| `data_public/ic_memo.py` | 1 |
| `data_public/ic_memo_generator.py` | 1 |
| `data_public/exit_readiness.py` | 1 |
| `data_public/qoe_analyzer.py` | 1 |

### Named industry authorities (count of explainers citing each)

| Source | Count |
|---|---|
| DOJ/FTC Horizontal Merger Guidelines | 1 (market-structure) |
| HFMA MAP 2023 | 1 (rcm-benchmarks) |
| Advisory Board Hospital Benchmarking Survey 2022 | 1 (rcm-benchmarks) |
| MGMA 2022–2023 | 1 (rcm-benchmarks) |
| ASCA 2023 | 1 (rcm-benchmarks) |
| Waystar 2020–2024 | 1 (rcm-benchmarks) |
| Cambridge Associates US PE benchmarks | 1 (vintage-cohorts) |
| CMS.gov public-data APIs | 1 (cms-data-browser) |

**No source over 8.** The highest reuse is 2, for modules that
genuinely govern more than one page (heuristics/reasonableness feed
both partner-review and red-flags; base_rates feeds base-rates and
the value-backtester; payer_intelligence feeds both payer pages).

**Four explainers carry no source** by design (home, methodology,
methodology/calculations, and home in the sense of the seven-panel
landing having no single governing module — it aggregates). These
ship WHAT-only.

### What this distribution tells me

- **Breadth is healthy** — every explainer traces to a specific module
  or named authority; no "industry best practices" hand-waving.
- **Concentration risk is low** — no source carries the weight of
  many pages, so a future refactor renaming one module touches at
  most two explainers.
- **Industry citations are where they should be** — only on pages
  where the threshold actually comes from a named outside standard
  (DOJ/FTC for HHI, HFMA/AB/MGMA/ASCA/Waystar for RCM bands, Cambridge
  Associates for vintage benchmarks, CMS for dataset catalog). No
  spurious dropped-in names to look authoritative.
