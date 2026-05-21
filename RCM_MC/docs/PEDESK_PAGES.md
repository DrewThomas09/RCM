# PE Desk — Pages & Routes

> Every user-facing page in PE Desk: route → renderer → purpose → data → visuals → drill-throughs. All routing is in `rcm_mc/server.py` (`do_GET`/`do_POST`); every page renders through `chartis_shell`. See [PEDESK_OVERVIEW.md](PEDESK_OVERVIEW.md) for architecture, [PEDESK_ALGORITHMS.md](PEDESK_ALGORITHMS.md) for the math behind the numbers, [PEDESK_DATA.md](PEDESK_DATA.md) for the data.

**Two page families:**
1. **Handcrafted partner workbenches** (`ui/` + `ui/chartis/`) — deal-centric, driven by the `DealAnalysisPacket`.
2. **~150 corpus/CMS analytic "modules"** (`ui/data_public/`) — one URL slug each, surfaced via the Cmd-K palette and `/module-index`.

The 6-section top nav (Home / Pipeline / Diligence / Library / Research / Portfolio) is far smaller than the full route surface — most analytics are reached via section landing pages, Cmd-K, and deal-profile drill-through links.

---

## Landing & auth flow
- **Auth gate** (`_auth_ok`): public paths are `/`, `/health`, `/login`, `/forgot`, `/api/login`, `/static/*`. **Open mode:** if no auth is configured and zero `users` rows exist → single-user laptop mode (no login). Creating the first user switches on multi-user (scrypt + sessions + CSRF).
- **`/`** — branching landing: authed + editorial → redirect **`/app`**; anonymous → `marketing_page.py` (public splash). `?v2`/`?legacy` and `RCM_MC_HOMEPAGE` env select dashboard generations.
- **`/login`** (`chartis/login_page.py`), **`/forgot`** (`chartis/forgot_page.py`).
- **`/app`** (`_route_app_page` → `chartis/app_page.py`) — **the editorial Command Center**, primary signed-in landing. `?deal=<id>` focuses a deal; `?stage=` filters. Blocks: return hero (Weighted MOIC), KPI strip, morning brief, pipeline funnel, deals table, alerts, covenant heatmap, EBITDA drag, initiative tracker, deliverables, quick access.
- **Dashboards:** `/dashboard` (`dashboard_v3` default, `?v2`/`?legacy` variants), `/home`/`/seekingchartis` (seven-panel partner home).

---

## HOME section
| Route | Renderer | Purpose / data / visuals |
|---|---|---|
| `/app` | `chartis/app_page.py` | Command Center (above) |
| `/my/<owner>` | `my_dashboard_page.py` | Personal pulse + health mix for an owner's deals |
| `/alerts` | `alerts_page.py` | Active alerts list (ack/snooze/escalate lifecycle) |
| `/escalations` | `escalations_page.py` | Escalated alerts |
| `/watchlist` | watchlist | Starred deals |
| `/activity`, `/initiatives`, `/ops`, `/cohorts`, `/owners`, `/deadlines`, `/notes`, `/variance`, `/team` | various | Audit/event feed, initiative rollup, ops console, cohort/owner/deadline slicing, notes search, variance drill-down, team workspace |
| `/lp-update` | `_route_lp_update` | Partner-ready LP digest (HTML + download) |

## PIPELINE section
| Route | Renderer | Purpose |
|---|---|---|
| `/pipeline` | `pipeline_page.py` | Deal pipeline funnel + saved searches |
| `/pipeline/bridge` | `portfolio_bridge_page.py` | Portfolio-level EBITDA bridge over HCRIS |
| `/screen` | `_route_screener_page` | Metric-based hospital screener over HCRIS |
| `/screening/dashboard` | `rcm_mc/screening` | Filterable deal-universe with scores |
| `/predictive-screener` | `predictive_screener.py` | ML-uplift-ranked hospital screen → `/hospital/<ccn>`, `/ebitda-bridge/<ccn>` |
| `/pe-intelligence` | `chartis/pe_intelligence_hub_page.py` | Hub for the "PE Brain": partner reflexes, archetypes, reasonableness matrix, red-flag catalog → per-deal `/deal/<id>/partner-review` |
| `/deal-screening` | `chartis/deal_screening_page.py` | Runs the screening engine over the corpus → PASS/WATCH/FAIL mix; live-tunable thresholds |
| `/find-comps`, `/conferences`, `/news` | various | Comparable finder, conference/news catalogs |
| `/screening/bankruptcy-survivor` | `bankruptcy_survivor_page.py` | Bankruptcy-survival scan (GET form + POST) |
| `/new-deal`, `/import`, `/quick-import`, `/upload` | `onboarding_wizard.py` + bulk import | Deal creation wizard + bulk CSV/JSON ingest |

## DILIGENCE section
Landing **`/diligence`** (`diligence_index_page.py`) groups ~25 RCM surfaces into 4 pillars (Profile/Health, Thesis/Playbook, Audit/Stress, Exit/Synthesis).

**Deal Profile (single source of truth):** `/diligence/deal`, `/diligence/deal/<slug>` (`deal_profile_page.py`) — per-deal metadata captured once, persisted to localStorage + URL, pre-fills every analytic card.

**RCM ingest / QoE pipeline** (`?dataset=<fixture>` drives a live pipeline; renderers in `rcm_mc/diligence/`):
- `/diligence/ingest` — live CCD ingest + transformation log
- `/diligence/benchmarks` — KPI vs benchmark bands
- `/diligence/root-cause` — denial/leakage root-cause
- `/diligence/value` — value-opportunity sizing
- `/diligence/qoe-memo` — printable partner-signed QoE memo
- `/diligence/snapshot` — live VDR 835/837 upload → revenue-leakage findings + Data Confidence Score + Markdown memo (aggregates only, PHI-safe)

**Analytic workbenches** (`rcm_mc/ui/`, most accept `?dataset=` + deal params):
- `/diligence/risk-workbench` — 9-panel Tier 1–3 regulatory risk
- `/diligence/counterfactual` — "what would change your mind"
- `/diligence/compare` — side-by-side deal compare
- `/diligence/ic-packet` — one-click IC memo assembler
- `/diligence/deal-mc` — 5-year forward Monte Carlo
- `/diligence/denial-prediction` — claim-level denial predictor
- `/diligence/deal-autopsy` — matches target to prior blow-ups (Steward-style)
- `/diligence/physician-attrition`, `/diligence/physician-eu` — provider flight-risk / P&L
- `/diligence/management` — management-forecast reliability scorecard
- `/diligence/exit-timing`, `/diligence/regulatory-calendar`, `/diligence/covenant-stress`, `/diligence/bridge-audit`, `/diligence/bear-case`, `/diligence/payer-stress`, `/diligence/hcris-xray`, `/diligence/checklist`, `/diligence/thesis-pipeline`, `/diligence/questions`
- `/diligence/sponsor-detail` — single-sponsor MOIC distribution + vintage + per-deal list
- `/diligence/comparable-outcomes` — target profile → corpus matches + outcome distribution

## LIBRARY section
| Route | Renderer | Purpose |
|---|---|---|
| `/library` | `data_public/deals_library_page.py` | The deal corpus (~1,041 entries); filters by sector/regime/MOIC; rows → `/library/<source_id>` detail |
| `/methodology`, `/methodology/calculations` | `library_page.py`, `methodology_page.py` | Reference catalog + calculation explainer |
| `/metric-glossary` | `metric_glossary_page.py` | Canonical metric reference; pages deep-link `#<metric_key>` |
| `/rcm-benchmarks` | `chartis/rcm_benchmarks_page.py` | P25/P50/P75 RCM benchmark bands by hospital-type segment |
| `/data`, `/data/catalog`, `/cms-sources`, `/cms-data-browser` | various | Data intelligence + CMS source catalog/browser |
| `/comparables` | `data_public/comparables_page.py` | Comparable transactions + entry-multiple × realized-MOIC scatter |
| `/market-rates` | `data_public/market_rates_page.py` | Market reimbursement rates by group/sector/payer/region |

## RESEARCH section
`/research` (curated research catalog), `/market-intel` (public comps + PE news), `/comparable-outcomes`, `/regulatory-calendar`, `/bear-cases`, `/backtest`, `/corpus-backtest` (cross-matches platform forecasts vs corpus realized MOIC/IRR).

## PORTFOLIO section
| Route | Renderer | Purpose |
|---|---|---|
| `/portfolio` | `portfolio_overview.py` | Portfolio overview + regression |
| `/portfolio/monitor` | `portfolio_monitor_page.py` | Cross-portfolio health bar, alerts, pred-vs-actual, **launched-vs-realized value creation** |
| `/portfolio/risk-scan` | `portfolio_risk_scan_page.py` | Morning scan: health/covenant/alerts/freshness/deadlines per deal |
| `/portfolio/regression`, `/portfolio/regression/hospital/<ccn>` | `_route_regression_page` | OLS regression + coefficient forest plot |
| `/portfolio-analytics` | `chartis/portfolio_analytics_page.py` | Corpus scorecard, vintage cohorts, deals-by-type (median-MOIC bars), return distribution, concentration |
| `/sponsor-track-record`, `/sponsor-league` | `chartis/sponsor_track_record_page.py`, `data_public/sponsor_league_page.py` | Sponsor league table + consistency score + Return-vs-Consistency scatter (dots drill to `/diligence/sponsor-detail`) |
| `/payer-intelligence` | `chartis/payer_intelligence_page.py` | Payer-mix averages, mix↔MOIC correlation, regime bands |
| `/portfolio/map`, `/portfolio/heatmap`, `/portfolio/monte-carlo`, `/lp-update`, `/fund-learning`, `/day-one`, `/hold/<deal_id>` | various | Map, heatmap, MC, LP digest, cross-deal accuracy, day-one plan, hold dashboard |
| `/deal-risk-scores` | `data_public/deal_risk_scores_page.py` | 5-factor risk tiers + **Risk-vs-Realized-Return scatter** |

## Per-deal pages (`/deal/<id>/...`)
Each loads the cached `DealAnalysisPacket` and runs a `pe_intelligence` module:
- `/deal/<id>` — main deal page (snapshot trail, variance, initiatives, notes, tags, owner, deadlines, health score + sparkline, rerun)
- `/deal/<id>/profile` (`deal_profile_v2.py`) — profile + EBITDA bridge (lever-contribution chart)
- `/deal/<id>/partner-review` (`chartis/partner_review_page.py`) — IC recommendation banner, bull/bear, IC-memo paragraph, "3 things that would change my mind", reasonableness band grid (with band-position bullets), heuristic hits
- `/deal/<id>/red-flags`, `/archetype`, `/investability` (composite 0–100 + 12-dim exit readiness), `/market-structure` (HHI/CR3/CR5 + consolidation score), `/white-space`, `/stress`, `/ic-packet`, `/timeline`
- **Models:** `/models/{dcf,lbo,financials}/<id>`; **`/analysis/<id>`** (Bloomberg-style packet workbench, `analysis_workbench.py`)
- **Model-namespace JSON/render:** `/models/{causal,counterfactual,predicted,questions,playbook,waterfall,bridge,comparables,anomalies,memo,validate,completeness,returns,debt,denial,market}/<deal_id>`

## Hospital pages (`/hospital/<ccn>/...`)
`/hospital/<ccn>` (`hospital_profile.py`), `/demand`, `/history`, `/providers` (specialty-mix concentration chart), `/start-diligence` (POST). Plus `/ml-insights`, `/bayesian/hospital/<ccn>`, `/competitive-intel/<ccn>`, `/data-room/<ccn>`, `/ebitda-bridge/<ccn>`, `/scenarios/<ccn>`, `/ic-memo/<ccn>`, `/market-data/state/<st>`.

## data_public analytic modules (~150 single-purpose pages)
One pattern: `if path == "/<slug>"` → parse query → `render_<name>` → send. Each renders a PE/healthcare analytic with inline SVG charts + KPI strips + tables driven by the corpus / CMS data / query params. Reached via the **Cmd-K palette** and **`/module-index`** (editorial directory) and **`/corpus-dashboard`**. Themed groups:
- **Valuation / returns:** entry-multiple, exit-multiple, multiple-decomp, peer-valuation, irr-dispersion, return-attribution, vintage-perf, gp-benchmarking, value-creation, underwriting, unit-economics, capital-efficiency, base-rates
- **Debt / capital:** lbo-stress, cap-structure, debt-financing, covenant-headroom, refi-optimizer, dividend-recap, leverage-intel, working-capital, capital-pacing, nav-loan-tracker, direct-lending
- **Risk / red flags:** redflag-scanner, risk-matrix, deal-risk-scores, regulatory-risk, fraud-detection, cyber-risk, concentration-risk, litigation, antitrust-screener
- **Payer / revenue:** payer-concentration, payer-contracts, payer-shift, revenue-leakage, risk-adjustment, nsa-tracker, medicaid-unwinding, ma-star, aco-economics, tracker-340b
- **Operations / workforce / clinical:** cost-structure, supply-chain, workforce-planning, physician-productivity, locum-tracker, clinical-outcomes, clinical-ai, quality-scorecard, specialty-benchmarks, demand-forecast, cin-analyzer
- **Deal lifecycle / exit:** deal-pipeline, deal-origination, deal-quality, deal-postmortem, acq-timing, sellside-process, exit-readiness, continuation-vehicle, secondaries-tracker, qoe-analyzer, earnout
- **Sector / market:** sector-intel, sector-momentum, sector-correlation, geo-market, hcit-platform, telehealth-econ, biosimilars, competitive-intel, growth-runway, ai-operating-model
- **Portfolio / LP / fund ops:** portfolio-optimizer, portfolio-sim, sponsor-heatmap, sponsor-league, hold-analysis, hold-optimizer, lp-dashboard, fundraising, dpi-tracker, operating-partners, coinvest-pipeline
- **Real estate / ESG / tax / compliance:** real-estate, reit-analyzer, esg-dashboard, tax-structure, tax-credits, compliance-attestation, board-governance, pmi-playbook, capex-budget, scenario-mc, insurance-tracker

## Engagement / client portal / admin
- `/engagements`, `/engagements/<id>` (`engagement_pages.py`) — RBAC, members, deliverables, comment stream; POSTs create/add/comment/publish
- `/portal/<id>` — published-only client view (`CLIENT_VIEWER` role)
- `/users` (admin), `/audit`, `/admin/audit-chain`, `/admin/data-sources`, `/settings`, `/settings/ai`, POST `/settings/workspace` (PE-Partner vs Chartis-Consulting mode toggle)

## Workbench / utility
`/scenarios`, `/surrogate`, `/pressure`, `/calibration`, `/runs`, `/cli-runs`, `/jobs`, `/data/refresh`, `/quant-lab`, `/model-validation` (with synthetic-backtest disclaimer + accuracy-vs-reliability scatter), `/models/quality`, `/exports`, `/global-search`, `/compare`, `/tools`, `/module-index`, `/corpus-dashboard`.

## API / JSON (`/api/*`) — summary
- **GET:** `/api`, `/api/docs` (Swagger), `/api/openapi.json` (52-path spec), `/api/health[/deep]`, `/api/metrics`, `/api/system/info`, `/api/search`, `/api/deals/{search,stats,compare}`, `/api/portfolio/{attribution,health,alerts,regression,matrix,summary}`, `/api/portfolio/risk-scan.csv`, `/api/export/portfolio.csv`, `/api/runs`, `/api/scenarios`, `/api/calibration/priors`, `/api/jobs/<id>`, `/api/insights`, `/api/market-pulse`, `/api/counterfactual*`, `/api/diligence/comparable-outcomes(.csv/.memo)`, `/api/backup`.
- **POST:** `/api/login`, `/api/logout`, `/api/upload-{actuals,initiatives,notes}`, `/api/deals/{bulk,import,import-csv,wizard/*}`, `/api/screener/run`, `/api/portfolio/register`, `/api/webhooks`, plus state-changing form POSTs (pipeline add/save-search, team comment, value-tracker record/freeze, data-room add). CSRF-protected for HTML form paths.

## Static / infra
`/static/*` (CSS/fonts/JS incl. `/static/v3/chartis.css`, `/static/chartis_tokens.css`), `/outputs/*`, `/manifest.json`, `/favicon.svg`, `/health`, `/healthz`, `/ready`.

---
*The route surface is large and evolving; `rcm_mc/server.py` is authoritative. The Cmd-K palette (`_DEFAULT_PALETTE_MODULES`) and `/module-index` are the fastest way to reach any analytic page.*
