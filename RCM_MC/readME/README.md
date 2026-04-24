# RCM-MC Documentation

Organized documentation for the RCM-MC healthcare PE diligence platform.

**Completely new?** Read the plain-English explainer at the repo root: **[../../README.md](../../README.md)** — assumes zero prior knowledge of PE or healthcare finance.

**Want to see the tool in action?** Read **[../../WALKTHROUGH.md](../../WALKTHROUGH.md)** — a 13-step case study walking through every module on a real Alabama hospital.

**Hands-on tutorial inside this folder?** Start with **[00 Walkthrough Tutorial](00_Walkthrough_Tutorial.md)** — copy-paste commands that exercise every major feature.

---

## How to Use This Folder

Start with the document that matches your role:

| You are a... | Start here |
|--------------|-----------|
| **Anyone (first time)** | **[00 Walkthrough Tutorial](00_Walkthrough_Tutorial.md)** |
| **New user / partner** | [04 Getting Started](04_Getting_Started.md) then [07 Partner Workflow](07_Partner_Workflow.md) |
| **API integrator** | [01 API Reference](01_API_Reference.md) |
| **Ops / deployer** | [02 Configuration and Operations](02_Configuration_and_Operations.md) |
| **Developer** | [03 Developer Guide](03_Developer_Guide.md) then [05 Architecture](05_Architecture.md) |
| **Data scientist** | [06 Analysis Packet](06_Analysis_Packet.md) then [08 Metric Provenance](08_Metric_Provenance.md) |

---

## Document Index

### Core Documentation

| # | File | Description |
|---|------|-------------|
| 01 | [API Reference](01_API_Reference.md) | All API endpoints with parameters, responses, and examples |
| 02 | [Configuration and Operations](02_Configuration_and_Operations.md) | Database, auth, deployment, backup, monitoring, security |
| 03 | [Developer Guide](03_Developer_Guide.md) | Architecture, testing, coding conventions, module map |
| 04 | [Getting Started](04_Getting_Started.md) | Installation, first run, basic workflow |
| 05 | [Architecture](05_Architecture.md) | System design, data flow, design decisions |

### Domain Documentation

| # | File | Description |
|---|------|-------------|
| 06 | [Analysis Packet](06_Analysis_Packet.md) | The canonical DealAnalysisPacket dataclass |
| 07 | [Partner Workflow](07_Partner_Workflow.md) | End-to-end partner usage: screen to exit |
| 08 | [Metric Provenance](08_Metric_Provenance.md) | How each metric traces back to source data |
| 09 | [Benchmark Sources](09_Benchmark_Sources.md) | CMS HCRIS, Care Compare, IRS 990 data pipeline |
| 10 | [Model Improvement](10_Model_Improvement.md) | Monte Carlo model calibration and improvement |
| 11 | [Glossary](11_Glossary.md) | Terms: IDR, FWR, DAR, MOIC, IRR, covenant, etc. |

### Technical Deep-Dives

| # | File | Description |
|---|------|-------------|
| 12 | [Data Flow](12_Data_Flow.md) | How data moves through the system |
| 13 | [Build Status](13_Build_Status.md) | Current build state and test results |
| 14 | [Full Summary](14_Full_Summary.md) | Complete feature inventory |
| 15 | [Documentation Index](15_Documentation_Index.md) | Cross-references across all docs |

### Layer-by-Layer Architecture

| # | File | Description |
|---|------|-------------|
| 16 | [Layer: Analysis](16_Layer_Analysis.md) | Packet builder, completeness, risk flags |
| 17 | [Layer: Data](17_Layer_Data.md) | HCRIS, auto-populate, document reader |
| 18 | [Layer: Domain](18_Layer_Domain.md) | Deals, alerts, portfolio, auth |
| 19 | [Layer: Infrastructure](19_Layer_Infrastructure.md) | Migrations, webhooks, job queue, rate limit |
| 20 | [Layer: Monte Carlo](20_Layer_Monte_Carlo.md) | Simulation engine, v1/v2 bridge |
| 21 | [Layer: Machine Learning](21_Layer_Machine_Learning.md) | Ridge predictor, conformal intervals |
| 22 | [Layer: PE Math](22_Layer_PE_Math.md) | MOIC, IRR, value bridge, ramp curves |
| 23 | [Layer: Provenance](23_Layer_Provenance.md) | Metric lineage tracking |
| 24 | [Layer: UI and Exports](24_Layer_UI_and_Exports.md) | Renderers, workbench, shell system |
| 25 | [Architecture Detailed](25_Architecture_Detailed.md) | Extended architecture documentation |

---

## New Diligence Modules (latest cycle)

Seven analytic modules that ship inside `rcm_mc/diligence/`. Each has a module-level README with plain-English explanation + public API snippets + where it plugs in:

| Module | What it does |
|--------|-------------|
| [HCRIS X-Ray](../rcm_mc/diligence/hcris_xray/README.md) | Peer benchmark against 17,701 filed Medicare cost reports |
| [Regulatory Calendar](../rcm_mc/diligence/regulatory_calendar/README.md) | CMS/OIG/FTC events × thesis-driver kill-switch |
| [Covenant Stress Lab](../rcm_mc/diligence/covenant_lab/README.md) | Capital-stack × per-quarter covenant-breach MC |
| [Bridge Auto-Auditor](../rcm_mc/diligence/bridge_audit/README.md) | Banker-bridge realization priors against 3,000 historical outcomes |
| [Bear Case Auto-Gen](../rcm_mc/diligence/bear_case/README.md) | IC memo counter-narrative auto-synthesized from 8 sources |
| [Payer Mix Stress](../rcm_mc/diligence/payer_stress/README.md) | 19-payer rate-shock MC with concentration amplifier |
| [Thesis Pipeline](../rcm_mc/diligence/thesis_pipeline/README.md) | 14-step orchestrator over every analytic |

Plus the **Seeking Alpha Market Intelligence** surface at `/market-intel/seeking-alpha` — 14 public healthcare comps + 12 curated PE transactions + sector sentiment heatmap.

---

## Source Code READMEs

Each package in `rcm_mc/` has its own README.md with full per-file documentation: what each `.py` file does, how it works mechanically, where data comes from, and what it produces.

| Package | Files | What's Documented |
|---------|-------|-------------------|
| [`rcm_mc/ai/`](../rcm_mc/ai/README.md) | 4 | LLM client (Anthropic API wrapper, cost tracking, cache), memo writer with fact-checking, document Q&A (chunk indexing + keyword search), multi-turn portfolio chat |
| [`rcm_mc/alerts/`](../rcm_mc/alerts/README.md) | 3 | Alert evaluators (covenant trip, variance breach, denial spike), ack/snooze with trigger-key-based auto-expiry, escalation history for alerts live >30 days |
| [`rcm_mc/analysis/`](../rcm_mc/analysis/README.md) | 20 | DealAnalysisPacket dataclass, 12-step packet builder, append-only analysis cache, anomaly detection (3 strategies), challenge solver (bisection), cohort analytics, run comparison, completeness grader, cross-deal full-text search, analyst overrides (5 namespaces), natural-language deal filter, fast screener, thesis-driven sourcer, auto diligence questions, playbook builder, management plan pressure test, stale packet detector, risk flags (6 categories + OBBBA amplification), MC stress testing |
| [`rcm_mc/analytics/`](../rcm_mc/analytics/README.md) | 4 | Causal initiative impact (ITS + DiD + pre-post), counterfactual EBITDA modeling, DRG-to-service-line P&L, demand forecasting |
| [`rcm_mc/auth/`](../rcm_mc/auth/README.md) | 4 | scrypt password auth + session tokens + rate-limited login, 6-tier RBAC with flat permission sets, append-only audit log, external portal users (management + LP) |
| [`rcm_mc/core/`](../rcm_mc/core/README.md) | 7 | Monte Carlo simulator (payer-bucket, vectorized), stable kernel API, Beta/Dirichlet/lognormal distributions (stdlib+numpy only), named SeedSequence RNG streams, Bayesian calibration pipeline, schema normalization helpers, Beta posterior update stats |
| [`rcm_mc/data/`](../rcm_mc/data/README.md) | 27 | CMS HCRIS loader (annual zip → `hospital_benchmarks`), HCRIS pre-parsed CSV layer, Care Compare loader (3 endpoints), Utilization loader (HHI + charge ratios), data refresh orchestrator, one-name-to-profile assembly, benchmark drift tracking, claim analytics (denial + aging), seller file metric extractor (alias-aware), EDI 837/835 parser, city/state geocoder, ingest CLI (seller packs → YAML), 11-prompt intake wizard, IRS 990 cross-check + loader, rcm-lookup CLI, market concentration HHI, SEC EDGAR XBRL loader, config provenance tagger, state regulatory registry, hospital system network graph, management team data, data scrubbing/winsorization, disease density, DRG weights, data room index, pipeline orchestrator, CMS download helper |
| [`rcm_mc/deals/`](../rcm_mc/deals/README.md) | 12 | Deal creation orchestrator, stage lifecycle (validated transitions + audit), owner assignment (append-only history), freeform tagging, append-only notes, deadline/task tracking, sim input path storage (enables 1-click rerun), metric-level threaded comments with @-mentions, IC approval workflow, 0–100 health score (4 weighted components), per-note tags, idempotent deal starring |
| [`rcm_mc/domain/`](../rcm_mc/domain/README.md) | 2 | Full MetricNode ontology (8 domains, directionality, causal DAG, P&L pathway, reimbursement sensitivity, EBITDA weight), user-defined custom KPI registry |
| [`rcm_mc/exports/`](../rcm_mc/exports/README.md) | 6 | Central packet renderer (HTML/PPTX/CSV/JSON/LP update + graceful fallback), 6-tab Excel workbook with conditional formatting, IC diligence ZIP (9 docs + manifest), exit data room ZIP, fund-level LP quarterly report, export audit log |
| [`rcm_mc/finance/`](../rcm_mc/finance/README.md) | 7 | Reimbursement engine (method-sensitivity tables, transparent inference, payer-mix-weighted lever realization), DCF model, denial driver decomposition, LBO model, market analysis aggregator, HC3-robust OLS regression, three-statement projection |
| [`rcm_mc/infra/`](../rcm_mc/infra/README.md) | 25 | YAML config loader/validator, centralized logger, idempotent migration registry, single-worker job queue, in-memory sliding-window rate limiter, OpenAPI 3.0 spec + Swagger UI, HMAC-signed webhook dispatch (3 retries + backoff), email + Slack notifications, atomic `VACUUM INTO` backup, startup consistency check, GDPR-compliant data retention, rule-based automation engine, multi-fund deal scoping, driver-to-data-request mapper, TTL response cache, CLI run history, provenance manifest writer, single-draw audit trace, JSON/CSV output formatters, HTML output folder index, config alignment, initiative taxonomy, price transparency MRF parser, capacity/queue modeler, diligence bundle assembler, ANSI terminal styler |
| [`rcm_mc/integrations/`](../rcm_mc/integrations/README.md) | 2 | Portfolio CSV export + idempotent DealCloud/Salesforce/Google Sheets CRM sync, PMS connector interface (Allvue/Cobalt/Investran) |
| [`rcm_mc/mc/`](../rcm_mc/mc/README.md) | 6 | Two-source Monte Carlo (prediction CI × execution Beta per lever family), v2 MC with 4 additional sampled dimensions, correlated portfolio-level MC (Cholesky decomposition), side-by-side scenario comparator with pairwise win probabilities, running-P50 convergence checker, append-only MC run persistence |
| [`rcm_mc/ml/`](../rcm_mc/ml/README.md) | 18+ | Ridge + split conformal predictor (3-tier fallback: Ridge≥15 / median≥5 / benchmark), legacy Phase-1 predictor, distribution-free conformal prediction (~50 lines numpy), 6-dimension weighted hospital similarity, interaction feature engineering + z-score normalization, 3-strategy anomaly detection, hold-out backtester (LOO + conformal coverage), auto-selecting ensemble (Ridge/kNN/median by held-out MAE), time-series trend forecaster (OLS/Holt-Winters/weighted-recent), cross-deal prediction bias shrinkage, and 8 additional scorers and predictors |
| [`rcm_mc/pe/`](../rcm_mc/pe/README.md) | 17 | Core PE returns math (bridge reconciliation invariant, Newton-bisection IRR), CLI auto-compute hook, payer-mix-weighted v2 bridge (4 economic flows per lever), legacy v1 research-band bridge (29 regression tests), cross-lever dependency walk (topological, prevents double-counting), per-lever S-curve ramp curves (identity lock at month 36), OAT dollar attribution, per-payer breakdowns, multi-tranche debt trajectory, fund-level value attribution, hold-period KPI variance tracking, diligence prediction vs. actual, quarterly re-mark, multi-year value creation simulation, 100-day plan builder, target config builder, hold-period value creation tracker, 4-tier GP/LP waterfall |
| [`rcm_mc/portfolio/`](../rcm_mc/portfolio/README.md) | 7 | Core SQLite store (17+ tables, WAL mode, FK enforcement), append-only milestone snapshots, self-contained HTML dashboard (no external JS), change-diff digest, per-deal delta detection, cross-platform synergy math, portfolio CLI |
| [`rcm_mc/provenance/`](../rcm_mc/provenance/README.md) | 4 | Immutable DataPoint atomic unit, per-deal provenance collection (SQLite + JSON graph export), rich explorable DAG with typed edges and traversal APIs, plain-English metric explanation generator |
| [`rcm_mc/rcm/`](../rcm_mc/rcm/README.md) | 5 | Lognormal claim-bucket distribution builder, YAML initiative library loader (8–12 standard initiatives), N+1 ROI optimizer (marginal simulation per initiative), hold-period per-initiative variance tracking, cross-deal playbook rollup |
| [`rcm_mc/reports/`](../rcm_mc/reports/README.md) | 13 | Core utilities (charts, formatters, summary tables), client-facing HTML report, audit-grade full report, Markdown report (GFM), 3-paragraph plain-English narrative, 5-slide PPTX IC deck (graceful fallback), exit-readiness memo, LP update builder, 4-theme CSS system, one-page partner IC brief, shared CSS, formatting helpers, static HTML scaffolding |
| [`rcm_mc/scenarios/`](../rcm_mc/scenarios/README.md) | 3 | Fluent scenario builder (deep-copy + fluent adjustments), pure-function overlay (dot-notation path shocks), preset payer-policy shocks (sequestration, MA rate cut, Medicaid work-requirement, site-neutral) |
| [`rcm_mc/ui/`](../rcm_mc/ui/README.md) | 60+ | Bloomberg 6-tab analysis workbench, shared dark-mode shell, 17 deal lifecycle pages, portfolio dashboard, heatmap, map, Monte Carlo page, LP update, scenario modeler, quant lab, regression page, fund learning page, peer comparison, and all chart/export/tool pages |
| [`rcm_mc/verticals/`](../rcm_mc/verticals/README.md) | 4+ | Vertical dispatch registry (HOSPITAL/ASC/BEHAVIORAL_HEALTH/MSO), ASC-specific metrics (CPT-based, prior-auth-dominant), behavioral health modules (auth management, LOS variance, Medicaid-dominant), MSO modules (collection rate, capitation pmpm) |
