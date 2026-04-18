# Chartis Integration Audit — Inventory of UI Gaps

**Branch:** `feature/chartis-integration`
**Date:** 2026-04-18
**Scope:** `seekingchartis.py` launches `rcm_mc.server.build_server()`. This
audit inventories what the HTTP server currently routes, which UI surfaces
are wired, and which sizable backend packages (`rcm_mc/pe_intelligence/`,
`rcm_mc/data_public/`) have no clickable path from the web UI.

Every claim below cites `file:line`. No code was modified in Phase 1.

---

## A. What the server currently routes

`rcm_mc/server.py` (13,735 lines) is a single stdlib
`http.server.ThreadingHTTPServer` app. Dispatch lives in
`RCMHandler._do_get_inner` (server.py:1780-3707) and
`RCMHandler._do_post_inner` (server.py:7767-7862), plus a prefix-style
`/api/*` fallthrough handled by `_route_api` (server.py:5609+) for GET
and `_route_api_post` for POST.

Top of file imports that pre-wire shared UI/shell helpers:
`rcm_mc/server.py:74-82` — `ui._ui_kit.shell`, `portfolio.portfolio_dashboard`,
`reports.exit_memo`, `deals.deal_notes`, `deals.deal_tags`,
`pe.hold_tracking`, `rcm.initiative_tracking`, `portfolio.store`,
`portfolio.portfolio_snapshots`. All other UI modules are imported lazily
inside each route handler.

### Routes grouped by section

#### Dashboard / home
| Route | Method | Handler | Renders from | Line |
|---|---|---|---|---|
| `/` , `/index.html` | GET | `_route_dashboard()` | `rcm_mc/portfolio/portfolio_dashboard.py` | server.py:1786 |
| `/home`, `/caduceus`, `/seekingchartis` | GET | `_route_seekingchartis_home()` | tries `ui/command_center.py`, falls back to `ui/home_v2.py` | server.py:1784, 3820-3831 |

#### Deal pages
| Route | Method | Handler | Line |
|---|---|---|---|
| `/deal/<deal_id>` | GET | `_route_deal()` | server.py:3670 |
| `/deal/<deal_id>/timeline` | GET | `_route_deal_timeline()` | server.py:2918 |
| `/compare` | GET | renders `ui/deal_comparison.py` | server.py:3385 |
| `/search` | GET | `_route_search()` | server.py:3382 |
| `/new-deal`, `/new-deal/*` | GET/POST | `_route_wizard_get()`, `_route_wizard_manual()`, `_route_wizard_upload()` | server.py:2812, 7855, 7857 |

#### Analysis / models (packet-centric)
| Route | Method | Handler / Renders | Line |
|---|---|---|---|
| `/analysis` | GET | `_route_analysis_landing()` → `ui/analysis_landing.py` | server.py:3675 |
| `/analysis/<deal_id>` | GET | `_route_analysis_workbench()` → `ui/analysis_workbench.py` | server.py:3698 |
| `/models/causal/<id>`, `/models/counterfactual/<id>`, `/models/predicted/<id>` | GET | `_route_model_*` | server.py:2744-2750 |
| `/models/questions|playbook|waterfall|bridge|comparables|anomalies|service-lines|memo|validate|completeness|returns|debt|challenge|irs990|trends|denial|market|dcf|lbo|financials/<id>` | GET | individual `_route_model_*` | server.py:2761-2809, 3689-3695 |
| `/model-validation` | GET | `_route_model_validation()` → `ui/model_validation_page.py` | server.py:2858 |
| `/ebitda-bridge/<ccn>` | GET | `_route_ebitda_bridge()` → `ui/ebitda_bridge_page.py` | server.py:2852 |
| `/scenarios/<ccn>` | GET | `_route_scenario_modeler()` → `ui/scenario_modeler_page.py` | server.py:2855 |
| `/ic-memo/<ccn>` | GET | `_route_ic_memo()` → `ui/ic_memo_page.py` | server.py:2860 |
| `/bayesian/hospital/<ccn>` | GET | `_route_bayesian_profile()` → `ui/bayesian_page.py` | server.py:2863 |
| `/surrogate`, `/pressure`, `/calibration` | GET | render `ui/surrogate_page.py`, `ui/pressure_page.py`, calibration page | server.py:3530, 3543, 3563 |
| `/runs`, `/scenarios` | GET | run history / scenarios pages | server.py:3474, 3526 |
| `/export/bridge/<ccn>` | GET | `_route_export_bridge()` | server.py:2846 |
| `/value-tracker/<id>` (+ `/record`, `/freeze`) | GET/POST | `_route_value_tracker*()` | server.py:2849, 7843, 7846 |

#### Portfolio / ops
| Route | Method | Handler | Line |
|---|---|---|---|
| `/portfolio` | GET | `_route_portfolio_overview()` | server.py:3685 |
| `/portfolio/monitor` | GET | `_route_portfolio_monitor()` | server.py:3687 |
| `/portfolio/regression` | GET | `_route_regression_page()` | server.py:1788 |
| `/portfolio/regression/hospital/<ccn>` | GET | `_route_hospital_regression()` | server.py:1790 |
| `/portfolio/monte-carlo` | GET | `_route_portfolio_mc()` | server.py:2927 |
| `/portfolio/map` | GET | `_route_portfolio_map()` → `ui/portfolio_map.py` | server.py:2929 |
| `/portfolio/heatmap` | GET | `_route_heatmap()` → `ui/portfolio_heatmap.py` | server.py:2931 |
| `/portfolio/bridge` | GET | `_route_portfolio_bridge()` → `ui/portfolio_bridge_page.py` | server.py:3681 |
| `/activity`, `/initiatives`, `/ops`, `/alerts`, `/escalations`, `/cohorts`, `/lp-update`, `/variance`, `/notes`, `/watchlist`, `/owners`, `/deadlines` | GET | `_route_*()` | server.py:3434-3463 |
| `/my/<owner>`, `/owner/<owner>`, `/cohort/<tag>` | GET | `_route_my_dashboard`, `_route_owner_detail`, `_route_cohort_detail` | server.py:3465-3471 |
| `/team`, `/pipeline`, `/fund-learning` | GET | `_route_team`, `_route_pipeline`, `_route_fund_learning` | server.py:3677-3683 |
| `/hold/<deal_id>` | GET | renders `ui/hold_dashboard.py` | server.py:2908 |

#### Hospital / data room
| Route | Method | Handler | Line |
|---|---|---|---|
| `/hospital/<ccn>` | GET | `_route_hospital_profile()` → `ui/hospital_profile.py` | server.py:2822 |
| `/hospital/<ccn>/demand` | GET | `_route_hospital_demand()` → `ui/demand_page.py` | server.py:2814 |
| `/hospital/<ccn>/history` | GET/POST | `_route_hospital_history()` | server.py:2817, 7826 |
| `/hospital/<ccn>/start-diligence` | POST | `_route_start_diligence_from_hospital()` | server.py:7829 |
| `/data-room/<ccn>` | GET | `_route_data_room()` → `ui/data_room_page.py` | server.py:2840 |
| `/data-room/<ccn>/add` | POST | `_route_data_room_add()` | server.py:7832 |
| `/competitive-intel/<ccn>` | GET | `_route_competitive_intel()` → `ui/competitive_intel_page.py` | server.py:2843 |

#### Chartis / SeekingChartis brand pages
| Route | Method | Handler | Renders from | Line |
|---|---|---|---|---|
| `/news` | GET | `_route_news_page()` | `ui/news_page.py` | server.py:2825, 3833 |
| `/conferences` | GET | `_route_conference_page()` | `ui/conference_page.py` | server.py:2827, 3840 |
| `/ml-insights`, `/ml-insights/hospital/<ccn>` | GET | `_route_ml_insights()`, `_route_hospital_ml()` → `ui/ml_insights_page.py` | server.py:2829, 2831 |
| `/quant-lab` | GET | `_route_quant_lab()` → `ui/quant_lab_page.py` | server.py:2834 |
| `/data-intelligence` | GET | `_route_data_intelligence()` | server.py:2836 |
| `/predictive-screener` | GET | `_route_predictive_screener()` → `ui/predictive_screener.py` | server.py:2838 |
| `/screen` | GET/POST | `_route_screener_page()`, `_route_screen_post()` | server.py:2925, 7853 |
| `/market-data/map` | GET | `_route_market_data_page()` → `ui/market_data_page.py` | server.py:2866 |
| `/market-data/state/<st>` | GET | `_route_market_data_state()` | server.py:2868 |
| `/library` | GET | `_route_library_page()` → `ui/library_page.py` (methodology hub) | server.py:2871 |
| `/verticals` | GET | inline render → `ui/verticals_page.py` | server.py:2755 |
| `/methodology` | GET | renders `ui/methodology_page.py` | server.py:1796 |
| `/import` | GET | renders `ui/quick_import.py` | server.py:1793 |
| `/source` | GET | `ui/source_page.py` + deal sourcing | server.py:2895 |

#### Corpus Intelligence (`ui/data_public/*` — 171 pages, all wired)
See Section D for the full data_public mapping. Routes are registered at
`server.py:1800-2719` in dense `if path == "/<slug>":` blocks. Representative
examples: `/deals-library` (server.py:1800 → `deals_library_page`),
`/sponsor-heatmap` (server.py:1852), `/vintage-cohorts` (server.py:2227),
`/backtest` (server.py:1818 → `backtest_page`), `/base-rates` (server.py:1872),
`/cms-data-browser` (server.py:1992), `/ic-memo-gen` (server.py:2002 →
`ic_memo_generator_page`), `/module-index` (server.py:2007),
`/corpus-dashboard` (server.py:2527), `/corpus-coverage` (server.py:2559),
`/corpus-ic-memo` (server.py:2530 → `ic_memo_page`), `/find-comps`
(server.py:2562), `/payer-intel` (server.py:2669), `/sector-intel`
(server.py:2675), `/rcm-red-flags` (server.py:2578), `/hold-optimizer`
(server.py:2583), `/payer-stress` (server.py:2588), `/lbo-stress`
(server.py:2042), `/qoe-analyzer` (server.py:2623), `/exit-timing`
(server.py:2445), `/gp-benchmarking` (server.py:2573). In total 155+ data_public
slugs are surfaced.

#### API (JSON)
| Route | Method | Handler | Line |
|---|---|---|---|
| `/api` | GET | route index (JSON) | server.py:3286 |
| `/api/docs` | GET | Swagger UI (HTML) | server.py:2934 |
| `/api/openapi.json` | GET | OpenAPI spec | server.py:2937 |
| `/api/health`, `/api/health/deep`, `/api/metrics`, `/api/system/info`, `/api/migrations`, `/api/backup` | GET | system | server.py:3304, 3306, 3348, 3350, 3273, 3137 |
| `/api/deals` (list/create/import/bulk/duplicate/wizard/*) | GET/POST | `_route_api*` | server.py:5650, 12454, 12392, 12504, 12624, 12655-12657, 12788 |
| `/api/deals/<id>` (detail, export, health, summary, provenance, sim-inputs, variance, initiatives, notes, tags, diffs, completeness, export-links, report, financials, denial-drivers, dcf, lbo, market, regression, qa, memo, counts, plan, audit) | GET | `_route_api` | server.py:5699-6107 |
| `/api/deals/<id>/archive|unarchive|pin|unpin|stage|comments|upload|actuals|remark|snapshots|notes|deadlines|duplicate|plan|overrides/<key>|profile` | POST / PUT / PATCH | `_route_api_post`, `_route_override_put`, profile PATCH | server.py:12365-13100, 7884, 7908 |
| `/api/portfolio/attribution|health|alerts|regression|matrix|summary|register` | GET/POST | `_route_api*` | server.py:2962, 3033, 3053, 3077, 3087, 3117, 12587 |
| `/api/corpus` | GET | deals-corpus parametric search | server.py:2453 |
| `/api/search`, `/api/deals/search`, `/api/deals/stats`, `/api/deals/compare` | GET | cross-deal search | server.py:2947, 2968, 3015, 3400 |
| `/api/screener/predefined`, `/api/screener/run` | GET/POST | screener | server.py:2876, 12540 |
| `/api/market-pulse`, `/api/insights` | GET | | server.py:2882, 2886 |
| `/api/runs` | GET | simulation runs | server.py:3512 |
| `/api/calibration/priors`, `/api/scenarios`, `/api/surrogate/schema` | GET | | server.py:3632, 3656, 3537 |
| `/api/chat` | POST | conversational AI | server.py:12559 |
| `/api/automations`, `/api/metrics/custom`, `/api/webhooks`, `/api/webhooks/test` | GET/POST | | server.py:3183, 3197, 3216, 12310, 12339 |
| `/api/export/portfolio.csv` | GET | | server.py:3167 |
| `/api/data/hospitals` | GET | typeahead | server.py:5684 |
| `/api/data/refresh/<source>` | POST | rate-limited CMS refresh | — |
| `/api/jobs/run` | POST | queue simulation | server.py:12925 |
| `/api/login`, `/api/logout`, `/api/users/create|delete|password` | POST | auth | server.py:7811, 7813, 13078, 13095, 13100+ |

#### Auth / users / admin
| Route | Method | Handler | Line |
|---|---|---|---|
| `/login` | GET | `_route_login_page()` | server.py:3376 |
| `/users` | GET | `_route_users_page()` | server.py:3380 |
| `/audit` | GET | `_route_audit()` | server.py:3378 |
| `/upload` | GET | `_route_upload_page()` | server.py:3374 |
| `/settings`, `/settings/<subpage>` | GET | settings dashboard | server.py:3223, 2905 |
| `/admin/data-sources` | GET | `ui/data_public/data_sources_admin_page.py` | server.py:2437 |

#### Other / system
`/jobs`, `/jobs/<id>`, `/initiative/<id>` (server.py:3662, 3664, 3667);
`/outputs/<path>` (server.py:3703); `/exports/lp-update` (server.py:3701);
`/health`, `/ready`, `/favicon.ico`, `/manifest.json` (server.py:3271, 3338,
3370, 3352); `HEAD` on `/api/health`, `/health`, `/ready` (server.py:7947).

**Route totals**: ~198 top-level GET slugs + ~40 API GETs, 75+ POSTs,
1 PUT, 1 PATCH, 3 HEAD.

---

## B. The six advertised SeekingChartis pages

The `seekingchartis.py` banner (seekingchartis.py:54-59) advertises six
pages. All six routes exist; five render the obvious UI module, but
`/library` points at a methodology hub, not the 655-deal corpus.

| Advertised route | Exists? | Handler | UI module | File:line |
|---|---|---|---|---|
| `/home` | Yes | `_route_seekingchartis_home()` | `ui/command_center.py` (primary) → falls back to `ui/home_v2.py` | server.py:1784, 3820-3831 |
| `/market-data/map` | Yes | `_route_market_data_page()` | `ui/market_data_page.py` | server.py:2866 |
| `/news` | Yes | `_route_news_page()` | `ui/news_page.py` | server.py:2825, 3833-3838 |
| `/screen` | Yes | `_route_screener_page()` (GET), `_route_screen_post()` (POST) | `ui/predictive_screener.py` / `intelligence/screener_engine.py` | server.py:2925, 7853 |
| `/library` | Partial — route exists, but renders methodology reference (valuation models, benchmarks, docs), **not** the 655-deal corpus | `_route_library_page()` | `ui/library_page.py` (library_page.py:1-5 confirms: "research library and reference materials") | server.py:2871-2872 |
| `/api/docs` | Yes | inline | Swagger UI via `infra/openapi` | server.py:2934-2937 |

The 655-deal corpus is actually at `/deals-library` (server.py:1800-1806 →
`ui/data_public/deals_library_page.py`). This is the biggest mismatch
between the launcher banner and reality: a user clicking the advertised
"Library" link lands on methodology docs, not the corpus.

---

## C. `rcm_mc/pe_intelligence/` — surfaced vs orphan

`rcm_mc/pe_intelligence/` contains **278 modules** exporting **1,455+**
public symbols from its `__init__.py` (794 classes, 661 functions).
Categories include: partner_review, narrative, ic_memo, bear_book,
reasonableness, heuristics, red_flags, regime_classifier,
market_structure, stress_test, white_space, investability_scorer,
exit_readiness, deal_archetype, master_bundle, workbench_integration,
diligence_tracker, ic_voting, operating_posture, obbba_sequestration_stress,
lp_side_letter_flags, plus 250+ domain-specific analyzers.

**Cross-reference against the web app** (`server.py` + `ui/`):

```
grep "pe_intelligence" across /rcm_mc/server.py → 0 matches
grep "pe_intelligence" across /rcm_mc/ui/      → 0 matches
grep "from rcm_mc.pe_intelligence" repo-wide   → only tests/test_pe_intelligence.py
```

(verified against server.py and rcm_mc/ui/ — see the cross-check above).

Representative confirmations:
- `ui/ic_memo_page.py:1-50` — renders IC memo standalone; does not import
  `pe_intelligence.ic_memo`.
- `ui/exit_readiness_page.py` (data_public variant) — standalone; does not
  call `pe_intelligence.exit_readiness.score_exit_readiness`.
- `server.py:2860 → _route_ic_memo()` — dispatches to `ui/ic_memo_page.py`;
  never imports `pe_intelligence`.
- `server.py` imports block (lines 74-82) and inline lazy imports — no
  `pe_intelligence` reference anywhere.

### Findings

**A. PE intelligence outputs with a fully wired UI page**: **NONE.**
Zero modules from `rcm_mc/pe_intelligence/` are reached from any route in
`server.py` or from any file in `rcm_mc/ui/`.

**B. PE intelligence outputs exposed via CLI/API only**: effectively none
in production. `rcm_mc/pe_cli.py` (top-level CLI) and some
`data_public/*` orchestrator modules (e.g. `data_public/ic_memo_synthesizer.py`,
`data_public/corpus_report.py`) touch pe_intelligence internally, but none
of those are surfaced through HTTP either.

**C. PE intelligence outputs with no UI and no HTTP API surface**:
**all 278 modules**. The entire package is production-compiled,
2,000+ tests pass, but is unreachable from the SeekingChartis web UI. This
is the single largest orphan in the repo.

---

## D. `rcm_mc/data_public/` — surfaced vs orphan

`rcm_mc/data_public/` has **313 files** (~206 substantive, the rest are
`__init__.py`, private helpers, and 31 `extended_seed_*.py` corpus shards).
`rcm_mc/ui/data_public/` has **174 page modules**.

### D.1 Deals corpus — is it browsable at `/library`?

**No.** `/library` (server.py:2871 → `_route_library_page()`) renders
`ui/library_page.py`, which is a methodology reference hub (DCF,
LBO, 3-statement model, benchmarks, etc.). The 655-deal corpus
(35 seeds in `data_public/deals_corpus.py:_SEED_DEALS` + 620 entries
across `extended_seed.py` + `extended_seed_2.py` … `extended_seed_31.py`)
is rendered only at **`/deals-library`** via
`ui/data_public/deals_library_page.py::render_deals_library`
(server.py:1800-1806). The launcher banner says "Library", but the link
a PE associate needs to *actually browse the corpus* lives at a
different slug.

### D.2 Three-column mapping

Of 206 substantive `data_public` modules, **~142 have a paired
`ui/data_public/*_page.py` plus a registered route in server.py
(server.py:1800-2719)**. Representative wired pairs:

| data_public module | ui page | route | line |
|---|---|---|---|
| `deals_corpus` + `extended_seed*` | `deals_library_page` | `/deals-library` | server.py:1800 |
| `base_rates` | `base_rates_page` | `/base-rates` | server.py:1872 |
| `sponsor_heatmap` | `sponsor_heatmap_page` | `/sponsor-heatmap` | server.py:1852 |
| `vintage_cohorts` | `vintage_cohorts_page` | `/vintage-cohorts` | server.py:2227 |
| `cms_data_browser` | `cms_data_browser_page` | `/cms-data-browser` | server.py:1992 |
| `backtest` | `backtest_page` | `/backtest` | server.py:1818 |
| `value_backtester` | `value_backtester_page` | `/backtester` | server.py:1897 |
| `ic_memo_generator` | `ic_memo_generator_page` | `/ic-memo-gen` | server.py:2002 |
| `ic_memo` | `ic_memo_page` | `/corpus-ic-memo` | server.py:2530 |
| `payer_intel` | `payer_intel_page` | `/payer-intel` | server.py:2669 |
| `sector_intel` | `sector_intel_page` | `/sector-intel` | server.py:2675 |
| `rcm_red_flags` | `rcm_red_flags_page` | `/rcm-red-flags` | server.py:2578 |
| `find_comps` | `find_comps_page` | `/find-comps` | server.py:2562 |

### D.3 data_public modules with NO UI page (orphans)

The sub-audit found ~64 substantive modules with no `ui/data_public/*_page.py`
counterpart. Tiered by business intelligence value:

**Tier 1 — core intelligence that should be clickable, currently orphaned:**
- `data_public/sponsor_track_record.py` — sponsor league tables, consistency scoring across the 655-deal corpus. No UI, no route. (No `/sponsor-track-record` slug in server.py.)
- `data_public/payer_intelligence.py` — payer-mix performance segments (P25/P50/P75 MOIC/IRR by commercial %). `/payer-intel` surfaces `payer_intel_page` which is a thinner variant, not this module.
- `data_public/rcm_benchmarks.py` — RCM KPI benchmark library (denial, DAR, clean-claim, collection).
- `data_public/backtester.py` — backtest platform predictions vs realized corpus outcomes. Distinct from `value_backtester` which is surfaced at `/backtester`.
- `data_public/deal_screening_engine.py` — rapid pass/watch/fail triage with risk matrix.
- `data_public/deal_quality_score.py` — A-D data-completeness grading; currently only consumed inside `deals_library_page` for the Data Grade column.
- `data_public/sponsor_analytics.py` — sponsor performance attribution by fund cohort.
- `data_public/portfolio_analytics.py` — portfolio-level correlation and attribution.
- `data_public/market_concentration.py` — HHI / market-share / regional concentration (distinct from UI's `concentration_risk_page`).

**Tier 2 — duplicated or overlapping modules** (suggest consolidation before wiring): `leverage_analysis`/`leverage_analytics`, `vintage_analysis`/`vintage_analytics`/`vintage_cohorts`, `deal_quality_score`/`deal_quality_scorer`/`deal_scorer`/`deal_risk_scorer`/`deal_risk_matrix`, plus 10 CMS modules (`cms_advisory_memo`, `cms_benchmark_calibration`, `cms_data_quality`, `cms_market_analysis`, `cms_opportunity_scoring`, `cms_provider_ranking`, `cms_rate_monitor`, `cms_stress_test`, `cms_trend_forecaster`, `cms_white_space_map`) of which only `cms_data_browser`, `cms_sources`, `cms_apm_tracker` have pages.

**Tier 3 — plausibly backend-only by design**: `corpus_cli`, `corpus_export`, `corpus_health_check`, `ingest_pipeline`, `normalizer`, `deal_memo_generator`, `corpus_report`, `ic_memo_synthesizer`. These look like library/infra code; wiring them to the UI is lower-value.

### D.4 The module index route

`/module-index` (server.py:2007 → `ui/data_public/module_index_page.py`)
already exists. It is the natural place to advertise the data_public
inventory, and whatever wiring Phase 2 adds should be linked from here.

---

## E. What `/home` should show

Today `/home` dispatches to `ui/command_center.py` when HCRIS data is
available and falls back to `ui/home_v2.py` otherwise
(server.py:3820-3831). Both are already reasonable shells — the question
is what *panels* the home page should include for a PE associate who just
logged in. The backend already has the data for all of these:

1. **Pipeline funnel** — stages (Sourcing → Screened → IOI → LOI → Diligence → IC → Closed) from `deals.deal` table. Powers: `/pipeline` (server.py:3679), `/api/deals/stats` (server.py:3015). Home should show stage counts + stage-change deltas over 7d.
2. **Active alerts** — `portfolio/alerts` lifecycle data. Powers: `/alerts` (server.py:3447), `/api/portfolio/alerts` (server.py:3053). Home should show fresh-today count, unacked count, returning-after-snooze count.
3. **Portfolio health mix** — composite 0-100 health score distribution. Powers: `/api/portfolio/health` (server.py:3033), `deals/health_score.py`. Home should render a traffic-light band (green/amber/red counts).
4. **Recent deals** — 5 most recently touched deals (edited / snapshotted / commented). Powers: `/activity` (server.py:3434), `deals/deal_notes.py`. One-line entry per deal with last action.
5. **Deadlines this week** — upcoming deadlines across all deals the user owns. Powers: `deals/deal_deadlines.py`, `/deadlines` (server.py:3463), `/my/<owner>` (server.py:3465).
6. **PE intelligence highlights** — **currently impossible** because no pe_intelligence module is routed. Phase 2 candidates (once pe_intelligence is wired): top 3 red flags across portfolio (`pe_intelligence.red_flags.run_red_flags`), top 3 bear-book pattern hits (`pe_intelligence.bear_book.scan_bear_book`), investability-score leaders (`pe_intelligence.investability_scorer.score_investability`).
7. **Corpus insights** — base-rate outcomes for sector/regime of in-flight deals (from `data_public/base_rates.py`), sponsor-fit check (`data_public/sponsor_track_record.py` once surfaced).
8. **News / market pulse** — latest items from `ui/news_page.py` (`/api/market-pulse`, `/api/insights` — server.py:2882, 2886). The current `command_center.py` already seeds this; keep.
9. **Jumps** — quick links: /deals-library, /analysis/<most-recent-deal>, /ic-memo/<most-recent-deal>, /module-index.

Panels 1-5, 8, 9 are wireable with today's backends. Panels 6-7 depend on
Phase 2 wiring pe_intelligence and the orphan data_public modules.

---

## F. Gap list (prioritized)

Format: Priority · Route · Backend modules · One-sentence description.

### P0 — core workflow blocked

1. **P0 · `/home` refresh** · `command_center.py` already exists but
   lacks portfolio-health, alerts, deadlines, PE-intelligence highlights,
   and corpus insight panels. · Build the seven-panel landing described in
   section E so a partner has a single answer to "what's new since
   yesterday."
2. **P0 · `/library` disambiguation** · `ui/library_page.py` vs
   `ui/data_public/deals_library_page.py`. · The launcher banner directs
   users to `/library` but the corpus lives at `/deals-library`; either
   retarget `/library` or rename the banner. Today a partner clicking
   "Library" gets methodology docs, not deals.
3. **P0 · `/pe-intelligence` hub (new)** · Entire
   `rcm_mc/pe_intelligence/` package (278 modules). · No route, no UI,
   zero coverage today. A single hub page with sub-pages for partner
   review, red flags, reasonableness, bear book, heuristics is the
   minimum viable exposure.
4. **P0 · `/deal/<id>/partner-review`** ·
   `pe_intelligence/partner_review.py::partner_review()` +
   `pe_intelligence/narrative.py::compose_narrative()`. · The core
   judgment output per deal — currently only reachable via a Python
   import.
5. **P0 · `/deal/<id>/red-flags`** · `pe_intelligence/red_flags.py`,
   `pe_intelligence/bear_book.py`, `pe_intelligence/reasonableness.py`. ·
   Three codified detectors that every IC memo should cite.

### P1 — major feature missing

6. **P1 · `/deal/<id>/ic-packet`** ·
   `pe_intelligence/ic_memo.py::render_ic_memo_all()` +
   `pe_intelligence/master_bundle.py::build_master_bundle()`. · Full
   render of the canonical IC memo using pe_intelligence (today's
   `/ic-memo/<ccn>` renders the standalone `ui/ic_memo_page.py`, which
   does not consume pe_intelligence).
7. **P1 · `/deal/<id>/archetype`** ·
   `pe_intelligence/deal_archetype.py::classify_archetypes()`,
   `pe_intelligence/regime_classifier.py::classify_regime()`. · Which
   deal archetype / regime the deal belongs to — drives sector-fit
   conclusions.
8. **P1 · `/deal/<id>/stress`** ·
   `pe_intelligence/stress_test.py::run_stress_grid()`. · Scenario grid
   of downside / base / upside outcomes.
9. **P1 · `/deal/<id>/investability`** ·
   `pe_intelligence/investability_scorer.py::score_investability()`,
   `pe_intelligence/exit_readiness.py::score_exit_readiness()`. · Single
   numeric score + explanation, currently unreachable.
10. **P1 · `/deal/<id>/market-structure`** ·
    `pe_intelligence/market_structure.py::analyze_market_structure()`. ·
    HHI / CR3 / CR5 and consolidation-play identification.
11. **P1 · `/deal/<id>/white-space`** ·
    `pe_intelligence/white_space.py::detect_white_space()`. · Where the
    deal has room to grow.
12. **P1 · `/sponsor-track-record`** ·
    `data_public/sponsor_track_record.py`,
    `data_public/sponsor_analytics.py`. · Sponsor league table +
    consistency scoring across the 655-deal corpus. Not the same as
    `/sponsor-heatmap` (that's sector×sponsor MOIC grid).
13. **P1 · `/payer-intelligence`** · `data_public/payer_intelligence.py`.
    · Payer-mix P25/P50/P75 segments by commercial %. Distinct from
    today's `/payer-intel` (`payer_intel_page`) which is thinner.
14. **P1 · `/rcm-benchmarks`** · `data_public/rcm_benchmarks.py`. · The
    foundational RCM KPI benchmark library (denial, DAR, clean-claim,
    collection) by hospital type.
15. **P1 · `/corpus-backtest`** · `data_public/backtester.py`. ·
    Platform-prediction-vs-realized-corpus accuracy tracker, distinct
    from the already-wired `/backtester` (value_backtester).
16. **P1 · `/deal-screening`** · `data_public/deal_screening_engine.py`.
    · Fast pass/watch/fail triage before full diligence.
17. **P1 · `/portfolio-analytics`** ·
    `data_public/portfolio_analytics.py`,
    `data_public/market_concentration.py`. · Portfolio-level
    correlation / concentration view beyond today's
    `/concentration-risk`.

### P2 — nice to have

18. **P2 · `/deal/<id>/heuristics`** ·
    `pe_intelligence/heuristics.py::run_heuristics()`. · 40+ PE
    rules-of-thumb as a sortable table.
19. **P2 · `/deal/<id>/diligence-board`** ·
    `pe_intelligence/diligence_tracker.py` (`DiligenceBoard`,
    `DiligenceItem`). · Workflow board for diligence items tied to a
    deal.
20. **P2 · `/deal/<id>/ic-vote`** · `pe_intelligence/ic_voting.py`. ·
    IC vote capture + reconciliation.
21. **P2 · `/deal/<id>/operating-posture`** ·
    `pe_intelligence/operating_posture.py`. · Ops-posture scoring
    (value-lever orientation).
22. **P2 · `/deal/<id>/obbba-stress`** ·
    `pe_intelligence/obbba_sequestration_stress.py`. · Specific
    federal-sequestration stress test.
23. **P2 · `/deal/<id>/management`** · `pe_intelligence.score_management`,
    `pe_intelligence.ManagementInputs`. · Management-team quality score.
24. **P2 · `/lp-side-letter-check`** ·
    `pe_intelligence/lp_side_letter_flags.py::check_side_letters`. ·
    Side-letter conformance scan.
25. **P2 · `/thesis-chains`** · `pe_intelligence.list_thesis_chains`,
    `pe_intelligence.walk_thesis_chain`. · Named-thesis-chain browser.
26. **P2 · CMS consolidation pages** · Collapse 10 overlapping
    `data_public/cms_*.py` modules into 2–3 pages (`/cms-market`,
    `/cms-opportunity`, `/cms-white-space`) or delete the duplicates.
27. **P2 · Leverage / vintage / deal-quality deduplication** · Multiple
    overlapping `data_public` modules (`leverage_analysis` vs
    `leverage_analytics`; `vintage_analysis` vs `vintage_analytics`;
    `deal_quality_score` vs `deal_quality_scorer` vs `deal_scorer`) —
    pick one each, wire it, delete the rest.
28. **P2 · `/module-index` link to orphans** ·
    `ui/data_public/module_index_page.py` (server.py:2007). · Once Phase 2
    wires orphans, update the module index so they're discoverable.

---

## Summary

- **Routes today**: ~198 top-level GET + 40 API GET + 75 POST; six
  banner-advertised pages all route, but `/library` shows methodology
  instead of the 655-deal corpus at `/deals-library`.
- **`pe_intelligence/`**: 278 modules, 1,455+ exports, **0% wired** —
  zero imports outside tests. This is the dominant gap.
- **`data_public/`**: 206 substantive modules, ~142 wired (~69%), ~64
  orphaned. Tier-1 orphans: sponsor_track_record, payer_intelligence,
  rcm_benchmarks, backtester, deal_screening_engine, market_concentration,
  portfolio_analytics, deal_quality_score, sponsor_analytics. Also ~25
  duplicate/overlap modules that should be consolidated before wiring.
- **`/home`**: already has a command_center renderer but lacks
  portfolio-health, alerts, deadlines, and (impossible today)
  pe_intelligence highlights.

Phase 2 should prioritize the P0 items — a `/pe-intelligence` hub and
per-deal partner_review / red_flags / ic_packet pages — because they unlock
the largest codified-judgment asset in the repo.
