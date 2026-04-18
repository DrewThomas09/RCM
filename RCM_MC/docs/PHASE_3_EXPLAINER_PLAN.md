# Phase 3 Explainer Plan — coverage map per chartis page

**Branch:** `chore/ui-polish-and-sanity-guards`
**Scratch file — delete at the end of Phase 3E.**

Goal: every chartis page gets an explainer. Every threshold cited
must trace to a real source. Conservative WHAT-only is better than
fake authoritative.

## Citation sources available

These are the authoritative references I'll draw from:

- **Backend module docstrings**, specifically:
  - `rcm_mc/pe_intelligence/deal_archetype.py` — 10 archetype definitions
  - `rcm_mc/pe_intelligence/regime_classifier.py` — 5 regime definitions + playbooks
  - `rcm_mc/pe_intelligence/market_structure.py` — HHI thresholds (1500 / 2500) with explicit "DOJ/FTC guideline" citation in the module constants
  - `rcm_mc/pe_intelligence/investability_scorer.py` — 0-100 composite, letter-grade map, axis weights (30/40/30)
  - `rcm_mc/pe_intelligence/exit_readiness.py` — 0-100 dimensional scorer
  - `rcm_mc/pe_intelligence/white_space.py` — 3-dimension 0-1 attractiveness scale
  - `rcm_mc/pe_intelligence/stress_test.py` — A/B/C/D/F robustness grade
  - `rcm_mc/pe_intelligence/partner_review.py` — 4 narrative recommendations
  - `rcm_mc/pe_intelligence/ic_memo.py` + `master_bundle.py` — memo structure
  - `rcm_mc/pe_intelligence/reasonableness.py` — IRR / margin / multiple bands with cited per-row sources ("HFMA MAP", "AHA + CMS cost reports", "HC-PE exit comps")
  - `rcm_mc/data_public/sponsor_track_record.py` — consistency score definition
  - `rcm_mc/data_public/rcm_benchmarks.py` — HFMA MAP, Advisory Board, Black Book, CMS HCRIS, Waystar/Experian cited
  - `rcm_mc/data_public/deal_screening_engine.py` — PASS/WATCH/FAIL criteria
- **`rcm_mc/ui/chartis/_sanity.py` REGISTRY** — every metric range is
  already cited to a named source.
- **Named industry authorities** for specific thresholds when they
  come from a publication the module explicitly credits:
  - FTC/DOJ Horizontal Merger Guidelines (HHI 1500/2500)
  - HFMA MAP 2024 (denial, DAR, clean-claim, net-collection, cost-to-collect)
  - CMS HCRIS / CMS IPPS
  - Preqin (hold distribution)
  - S&P LCD (leverage)

If a page's metric doesn't clearly tie to a cited source after the
module check, the explainer ships WHAT-only with a
`TODO(phase-3): source for <metric>` comment.

---

## Coverage map

### Group 1 — Landing / hub pages (5)

| Page | Type | Plan |
|---|---|---|
| `/home` | conservative (WHAT-only) | Seven-panel partner landing; no single metric to cite. WHAT: "Portfolio status at a glance — pipeline, alerts, health, deadlines, PE intelligence highlights, corpus comps." SCALE: n/a. USE: n/a. No source — describes itself. |
| `/pe-intelligence` | full 3-part | Hub for the 278-module PE brain. WHAT: "Entry point into the codified PE-partner judgment layer — 7 reflexes + module catalog." SCALE: the 7 reflexes listed. USE: "Use the sidebar or the per-deal pages to run any brain module." SOURCE: `rcm_mc/pe_intelligence/README.md`. |
| `/library` | conservative (WHAT + brief scale) | Browsable 655-deal corpus. WHAT: "All healthcare-PE transactions in the SeekingChartis seed corpus, with realized MOIC / IRR / hold / sponsor / sector." SCALE: "Data-grade A–D column reflects completeness of the row, per `data_public/deal_quality_score.py`." USE: "Filter and sort to build comparables for a target." SOURCE: the quality scorer module. |
| `/methodology` | WHAT-only (it IS the documentation) | The methodology hub. No partner-facing data to interpret. WHAT: "Reference library of valuation models, market-intelligence methods, and benchmark sources used across the platform." No SCALE / USE — this page IS the source for other pages' explanations. |
| `/methodology/calculations` | WHAT-only | Detailed calculation explainer. WHAT: "Step-by-step explanations of how each number on the platform is computed." Same rationale as above. |

### Group 2 — Phase 2A per-deal pages (2)

| Page | Type | Plan |
|---|---|---|
| `/deal/<id>/partner-review` | full 3-part | WHAT: "PE-partner review for this deal, composed from 7 reflex modules." SCALE: Recommendation levels "PASS / PROCEED_WITH_CAVEATS / PROCEED / STRONG_PROCEED" (from `partner_review.narrative.recommendation`). USE: "Read the narrative + IC verdict; drill into linked per-metric pages for the supporting math." SOURCE: `rcm_mc/pe_intelligence/partner_review.py`. |
| `/deal/<id>/red-flags` | full 3-part | WHAT: "Focused subset — critical/high heuristic hits + reasonableness band violations for this deal." SCALE: Severity levels "CRITICAL / HIGH / MEDIUM / LOW" per `heuristics.py:SEV_*` constants. Band verdicts "IN_BAND / STRETCH / OUT_OF_BAND / IMPLAUSIBLE" per `reasonableness.py`. USE: "Use this as the 30-second triage — does this deal have stop-work issues before I spend more time on it?" SOURCE: `pe_intelligence/heuristics.py` + `reasonableness.py`. |

### Group 3 — Phase 2B per-deal pages (6)

| Page | Type | Plan |
|---|---|---|
| `/deal/<id>/archetype` | full 3-part | WHAT: "Classifies the deal into sponsor-structure archetype(s) and places it in a performance regime." SCALE: 10 archetypes (platform-rollup / take-private / carve-out / turnaround / buy-and-build / continuation / GP-led secondary / PIPE / operating-lift / growth-equity) and 5 regimes (durable-growth / emerging-volatile / steady / stagnant / declining-risk). USE: "Each archetype has its own playbook and failure modes. Use the matched archetype's 'playbook' + 'risks' lists as your diligence scaffold." SOURCE: `pe_intelligence/deal_archetype.py` + `regime_classifier.py`. |
| `/deal/<id>/investability` | full 3-part | WHAT: "Composite 0-100 investability score + exit-readiness score." SCALE: Axis weights 30 / 40 / 30 (opportunity / value / stability). Composite grades A (>85) / B (70-85) / C (55-70) / D (40-55) / F (<40). USE: "Use the composite as a quick screen; read the subscore breakdown to see which axis is driving the grade." SOURCE: `pe_intelligence/investability_scorer.py` module docstring. |
| `/deal/<id>/market-structure` | full 3-part | WHAT: "HHI (Herfindahl–Hirschman Index), CR3, and CR5 for the target's local market." SCALE: "HHI below 1,500 = unconcentrated; 1,500–2,500 = moderately concentrated; above 2,500 = highly concentrated." USE: "Use to assess pricing power, consolidation-play fit, and antitrust exposure." SOURCE: "DOJ / FTC Horizontal Merger Guidelines — explicitly cited in `pe_intelligence/market_structure.py:HHI_UNCONCENTRATED`." |
| `/deal/<id>/white-space` | full 3-part | WHAT: "Adjacency opportunities ranked on a 0–1 attractiveness scale across geographic, segment, and channel dimensions." SCALE: "Score ≥ 0.75 = strong fit; 0.50–0.75 = fair; below = low-conviction. Score blends addressable size × competitive intensity × proximity-to-core." USE: "Use to size post-close value-creation plans beyond the entry thesis." SOURCE: `pe_intelligence/white_space.py` module docstring. |
| `/deal/<id>/stress` | full 3-part | WHAT: "Runs a grid of rate / volume / multiple / lever / labor shocks against the deal and produces a robustness grade." SCALE: "Grade A–F (A = passes every downside scenario; F = fails multiple)." USE: "Use the downside-pass rate to size covenant headroom and stress reserves." SOURCE: `pe_intelligence/stress_test.py` module docstring. |
| `/deal/<id>/ic-packet` | conservative (WHAT + brief how-to) | WHAT: "IC-ready packet combining the IC memo, analyst cheat-sheet, bear patterns, regulatory items, 100-day plan, and partner discussion." SCALE: none (it's a document, not a metric). USE: "Download the individual sections for pre-IC prep or export the whole packet for committee circulation." SOURCE: `pe_intelligence/master_bundle.py`. |

### Group 4 — Phase 2C portfolio pages (6)

| Page | Type | Plan |
|---|---|---|
| `/sponsor-track-record` | full 3-part | WHAT: "Per-sponsor healthcare-PE performance league table across the 655-deal corpus." SCALE: "Consistency score 0–100 (higher = more repeatable returns); loss rate = fraction of realized deals below 1.0x MOIC; home-run rate = fraction ≥ 3.0x." USE: "Use the consistency + home-run columns together; a sponsor with both high consistency AND high home-run rate is a genuine high-return shop, vs one-hit-wonders." SOURCE: `data_public/sponsor_track_record.py:sponsor_consistency_score_raw`. |
| `/payer-intelligence` | full 3-part | WHAT: "Corpus performance bucketed by commercial-payer percentage into 4 regimes." SCALE: "Gov-heavy (<30% commercial); Balanced (30–50%); Commercial-mix (50–70%); Commercial (>70%). Per-bucket MOIC P25/P50/P75 + IRR median + loss rate." USE: "Use to baseline an underwriting assumption against observed corpus returns for the same payer regime." SOURCE: `data_public/payer_intelligence.py` module docstring + corpus rollup math. |
| `/rcm-benchmarks` | full 3-part | WHAT: "Industry RCM KPI benchmarks (denial, DAR, clean-claim, collection, write-off, cost-to-collect, denial-overturn) per hospital segment at P25 / P50 / P75." SCALE: "HFMA MAP 2024 acute-hospital bands. Behavioral / ASC / critical-access segments have separately-calibrated bands." USE: "Use the per-segment P50 as the base-rate assumption for a target in that segment; flag anything outside P25–P75 as either an outperformer or a broken operation." SOURCE: "HFMA MAP, Advisory Board, Black Book, CMS HCRIS, Waystar/Experian — cited in `data_public/rcm_benchmarks.py` module docstring." |
| `/corpus-backtest` | full 3-part | WHAT: "Platform prediction vs realized MOIC / IRR for every corpus deal we can fuzzy-match to a platform analysis run. Also renders realized-MOIC ground-truth by vintage + sector." SCALE: "Error band `< 0.25x` = in-line; 0.25–0.75x = drift; >0.75x = significantly off. Error = predicted − realized MOIC." USE: "Use to calibrate trust in a prediction: if the platform systematically drifts on sector X, weight X predictions accordingly." SOURCE: `data_public/backtester.py` + `pe_intelligence/reasonableness.py` band thresholds. |
| `/deal-screening` | full 3-part | WHAT: "Runs every corpus deal through PASS / WATCH / FAIL triage against a configurable threshold set." SCALE: "PASS = all checks clear; WATCH = soft flags (high EV/EBITDA, high Medicaid %, missing data); FAIL = hard failure (critical risk or sub-threshold MOIC)." USE: "Tighten thresholds to see the bar a deal would need to clear today; use decision distribution as an index of the corpus under current market assumptions." SOURCE: `data_public/deal_screening_engine.py:ScreeningConfig` docstring. |
| `/portfolio-analytics` | full 3-part | WHAT: "Corpus scorecard — MOIC + IRR percentiles, loss + home-run rates, vintage cohort mix, deal-type mix, concentration across sector / geography / sponsor, outlier deals." SCALE: "Home-run ≥ 3.0x MOIC; loss < 1.0x MOIC (both definitional). Concentration shown as HHI-style share sums." USE: "Use to benchmark a fund's own portfolio against the corpus — mix, pacing, concentration risk, outlier exposure." SOURCE: `data_public/portfolio_analytics.py` + `pe_intelligence/reasonableness.py`. |

### Group 5 — Legacy chartis pages not covered elsewhere

The Phase 2 migration moved ~140 data_public pages onto
`chartis_shell`. Writing an explainer for each one is a large
undertaking and most of them are niche tools. Plan:

**Apply conservative WHAT-only explainers** to the ~15 most-visited
legacy pages (those referenced from the main chartis nav), each with
a single-sentence description drawn from its module docstring. Leave
`TODO(phase-3): consider upgrading to 3-part explainer` comments on
the rest — they'll get explainers in a later focused pass per
sub-module rather than one-shotting 140 short blurbs.

Pages to explainer in this commit:

| Page | Module for WHAT source |
|---|---|
| `/base-rates` | `data_public/base_rates.py` |
| `/sponsor-heatmap` | `data_public/sponsor_heatmap.py` |
| `/vintage-cohorts` | `data_public/vintage_cohorts.py` |
| `/module-index` | `data_public/module_index_page.py` |
| `/cms-data-browser` | `data_public/cms_data_browser.py` |
| `/corpus-dashboard` | `data_public/corpus_dashboard.py` |
| `/deal-search` | `data_public/deal_search.py` |
| `/find-comps` | `data_public/find_comps.py` |
| `/sector-intel` | `data_public/sector_intel.py` |
| `/payer-intel` | `data_public/payer_intel.py` (already has SUMMARY-VIEW cross-link banner; add explainer above it) |
| `/backtester` | `data_public/value_backtester.py` (already has VALUE-BRIDGE disambig banner; add explainer) |
| `/corpus-ic-memo` | `data_public/ic_memo.py` |
| `/ic-memo-gen` | `data_public/ic_memo_generator.py` |
| `/exit-readiness` | `data_public/exit_readiness.py` |
| `/qoe-analyzer` | `data_public/qoe_analyzer.py` |

Everything else (~125 pages): leave as-is with TODO comment on the
first render call. They'll pick up WHAT-only explainers in a
follow-up when someone owns that swath of tools.

---

## Coverage count (plan)

- **Full 3-part explainers:** 14 pages
  (pe-intelligence + 2 Phase 2A + 5 Phase 2B + 6 Phase 2C — 1 conservative for ic-packet)
- **Conservative explainers (WHAT-only or WHAT + minimal scale):** 6 pages
  (/home, /library, /methodology, /methodology/calculations, /deal/<id>/ic-packet — now 5; plus 15 legacy pages = 20 legacy+landing conservative)
- **Legacy chartis pages deferred with TODO:** ~125

## Sources I will cite

Every citation in the planned explainers traces to:

- A backend module file path I've actually read (checked above via
  head / grep). No blind citations.
- A named industry authority that is mentioned in a module
  docstring (HFMA MAP, DOJ/FTC, HCRIS, Preqin, S&P LCD, Advisory
  Board, Black Book, Waystar, Experian Health).

I will NOT cite:
- "Industry best practices" without a named source.
- Numbers pulled from memory without a module reference.
- Any PE-industry thresholds not already codified in the
  reasonableness registry or a data_public module.

---

## Open questions for reviewer

1. **Legacy page scope** — 15 legacy pages with WHAT-only + 125
   deferred to TODO is ~60 min of work. Is this the right cut or
   should I aim for coverage across all 140?

2. **Tone on conservative pages** — for `/methodology` and
   `/methodology/calculations`, the page IS the docs. A WHAT-only
   explainer would just restate the page title. Option: skip the
   explainer entirely on those two pages. Flagging for your call.

3. **IC-packet exception** — ruled conservative because it's a
   compound document (memo + cheatsheet + bear + regulatory +
   100-day + discussion) with no single "scale". Could split into
   per-section micro-explainers later. Going WHAT-only for now.
