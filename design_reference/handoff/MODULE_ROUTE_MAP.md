# Module Route Map

Every module surface in the SeekingChartis mockup, grouped by lifecycle stage. Use this to walk the platform page by page and verify the reworked shell renders cleanly at each route.

**Total:** 79 surfaces across 5 groups.

**How to read:**
- **Module** — the label shown in the Platform Index grid on Home.
- **Route** — the URL path served by `rcm_mc/server.py`.
- **Kind** — the layout variant the mockup's `ModulePage` renders (dashboard / workbench / wizard / long-form / compare / deal-dashboard / etc).
- **Source .py** — best-guess renderer file in `rcm_mc/ui/`. If a route resolves to a different file, update this table in your PR.

---

## Deal lifecycle

| Module | Route | Kind | Source .py |
|---|---|---|---|
| Screener | `/screen` | screener | — |
| Source | `/source` | filter-list | — |
| New deal | `/new-deal` | wizard | — |
| Deal dashboard | `/deal/<id>` | deal-dashboard | — |
| Analysis workbench | `/analysis/<id>` | workbench | — |
| Compare | `/compare` | compare | deal_comparison.py |
| IC memo | `/api/deals/<id>/memo` | long-form | ic_memo.py |
| IC packet | `/deal/<id>/ic-packet` | long-form | — |
| Partner review | `/deal/<id>/partner-review` | deal-verdict | — |
| Red flags | `/deal/<id>/red-flags` | red-flags | — |
| Archetype & regime | `/deal/<id>/archetype` | deal-classifier | — |
| Investability & exit | `/deal/<id>/investability` | deal-score | — |
| Market structure | `/deal/<id>/market-structure` | market | — |
| White space | `/deal/<id>/white-space` | whitespace | — |
| Stress grid | `/deal/<id>/stress` | stress | — |
| Packet export | `/api/deals/<id>/package` | export | — |
| Thesis card | `/thesis/<ccn>` | deal-verdict | thesis_card.py |
| Data room | `/data-room/<deal>` | long-form | data_room_page.py, data/data_room.py |
| Predictive screener | `/predictive-screen` | screener | predictive_screener.py |
| Diligence questions | `/diligence/<deal>/questions` | long-form | diligence_page.py, analysis/diligence_questions.py |
| Deal timeline | `/deal/<id>/timeline` | long-form | deal_timeline.py |
| Deal quick view | `/deal/<id>/quick` | deal-dashboard | deal_quick_view.py |

## Portfolio ops

| Module | Route | Kind | Source .py |
|---|---|---|---|
| Partner dashboard | `/` | dashboard | — |
| Portfolio overview | `/portfolio/overview` | portfolio-rollup | portfolio_overview.py |
| Portfolio heatmap | `/portfolio/heatmap` | heatmap | portfolio_heatmap.py |
| Geographic map | `/portfolio/map` | map | portfolio_map.py |
| Portfolio Monte Carlo | `/portfolio/monte-carlo` | monte-carlo | — |
| Portfolio bridge | `/portfolio/bridge` | bridge | portfolio_bridge_page.py |
| LP digest | `/lp-update` | long-form | — |
| Hold dashboard | `/hold` | hold | hold_dashboard.py |
| Value creation tracker | `/value/<deal>` | bridge | value_tracking_page.py, pe/value_tracker.py |
| Value-creation playbook | `/playbook/<deal>` | long-form | diligence_page.py, analysis/playbook.py |

## Analytics & models

| Module | Route | Kind | Source .py |
|---|---|---|---|
| EBITDA bridge | `/analysis/<id>#ebitda` | bridge | ebitda_bridge_page.py |
| Scenarios | `/scenarios` | scenarios | scenarios_page.py |
| Scenario modeler | `/scenario-modeler` | scenario-builder | scenario_modeler_page.py |
| Sensitivity | `/sensitivity` | sensitivity | sensitivity_dashboard.py |
| Regression lab | `/regression` | regression | regression_page.py |
| Bayesian calibration | `/bayesian` | bayesian | bayesian_page.py |
| Surrogate model | `/surrogate` | surrogate | surrogate_page.py |
| Fund learning | `/fund-learning` | fund-learning | fund_learning_page.py |
| Quant lab | `/quant-lab` | quant | quant_lab_page.py |
| Hospital statistics | `/stats/<ccn>` | heatmap | hospital_stats_page.py, regression_page.py |
| ML insights | `/ml-insights` | dashboard | ml_insights_page.py, hospital_clustering.py, distress_predictor.py |
| Model validation | `/model-validation` | backtest | model_validation_page.py, ml/prediction_ledger.py |
| Challenge solver | `/models/challenge/<deal>` | long-form | advanced_tools_page.py, analysis/challenge.py |
| Debt model | `/models/debt/<deal>` | bridge | advanced_tools_page.py, pe/debt_model.py |
| Returns waterfall | `/models/waterfall/<deal>` | bridge | waterfall_page.py, pe/waterfall.py |
| PE returns & covenants | `/models/returns/<deal>` | deal-score | pe_returns_page.py, pe/pe_math.py |
| EBITDA value bridge | `/models/bridge/<deal>` | bridge | pe_tools_page.py, pe/value_bridge.py |
| Causal inference | `/models/causal/<deal>` | long-form | analytics_pages.py, analytics/causal.py |

## Market intelligence

| Module | Route | Kind | Source .py |
|---|---|---|---|
| Market analysis | `/market` | market | market_analysis_page.py |
| Market data | `/market-data` | market | market_data_page.py |
| Competitive intel | `/competitive` | competitive | competitive_intel_page.py |
| Demand | `/demand` | demand | demand_page.py |
| Denial | `/denial` | denial | denial_page.py |
| Pressure | `/pressure` | pressure | pressure_page.py |
| Sponsor track record | `/sponsor-track-record` | sponsor | — |
| Payer intelligence | `/payer-intelligence` | payer | — |
| RCM benchmarks | `/rcm-benchmarks` | benchmarks | — |
| Corpus backtest | `/corpus-backtest` | backtest | — |
| PE intelligence hub | `/pe-intelligence` | hub | pe_intelligence_hub_page.py |
| Deal screening engine | `/deal-screening` | screener | — |
| Hospital profile | `/hospital/<ccn>` | long-form | hospital_profile.py |
| Hospital history | `/history/<ccn>` | long-form | hospital_history.py |
| News feed | `/news` | long-form | news_page.py |
| Conference roadmap | `/conferences` | long-form | conference_page.py |
| Verticals | `/verticals` | long-form | verticals_page.py |

## Tools & admin

| Module | Route | Kind | Source .py |
|---|---|---|---|
| Command center | `/command` | command | command_center.py |
| Data explorer | `/data-explorer` | explorer | data_explorer.py |
| Data dashboard | `/data` | data | data_dashboard.py |
| Library | `/library` | library | library_page.py |
| Provenance | `/provenance` | provenance | provenance.py |
| Methodology | `/methodology` | docs | methodology_page.py |
| Team | `/team` | team | team_page.py |
| Settings | `/settings` | settings | settings_pages.py, settings_ai_page.py |
| Quick import | `/import` | wizard | quick_import.py |
| Home (market-first) | `/home-v2` | dashboard | home_v2.py |
| Dashboard (morning view) | `/dashboard-v2` | dashboard | dashboard_v2.py |
| Analysis landing | `/analysis` | dashboard | analysis_landing.py |

---

## Routes not in the catalog (likely candidates)

These files exist in `rcm_mc/ui/` but don't have a corresponding entry in the module catalog. Decide whether they need their own Platform Index card or whether they're utility routes (partials, JSON APIs, fragment renderers) that don't deserve one.

_Run this grep after landing the rework to see what's uncovered:_

```bash
rg -l 'def render_|def page_' rcm_mc/ui/ | sort
```

If a file's page is user-facing and useful, add a catalog entry to `components/modulesCatalog.js` in the mockup (and to the Python `_CORPUS_NAV` if it belongs in primary nav).

## Feature-flag bake-off

Until you're ready to delete the old shell, keep both under the `CHARTIS_UI_V2` environment flag:

```bash
# new shell (default once merged)
python seekingchartis.py

# legacy dark shell — set anything falsy
CHARTIS_UI_V2=0 python seekingchartis.py
```

Plumb the flag through `_chartis_kit.py` only. Page renderers don't need to know.
