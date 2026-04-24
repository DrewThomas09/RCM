# Coding Prompts Backlog — Blueprint → Action

Derived from [STRATEGIC_BLUEPRINT.md](STRATEGIC_BLUEPRINT.md) (partial — awaiting Part 4 Moat Layer 6 continuation + remaining parts) and cross-referenced against the 190+ modules already shipped in [`rcm_mc/data_public/`](../rcm_mc/data_public/).

Every prompt follows the established additive pattern from [FEATURE_DEALS_CORPUS.md](../FEATURE_DEALS_CORPUS.md):

1. Backend: `rcm_mc/data_public/<module>.py` — stdlib-only + pandas/numpy, `@dataclass` wrappers, single `compute_<module>()` entry point
2. UI: `rcm_mc/ui/data_public/<module>_page.py` — Chartis dark shell via `_chartis_kit`
3. Route: additive block in `rcm_mc/server.py`
4. Nav: entries in `_chartis_kit.py::_CORPUS_NAV` + `brand.py::NAV_ITEMS`
5. Smoke test: `python3 -c "from ...data_public.<module> import compute_<module>; print(compute_<module>({}))"`
6. Commit: `auto: <title> at /<route> (N deals)` on `feature/deals-corpus`

All prompts are additive — never touch `main`, never modify existing files except the three established hook points.

---

## Tier 0 — Knowledge Graph Foundation (Blueprint Moat Layer 1)

The codified-knowledge moat. None of these exist yet.

### P0.1 — HFMA MAP Keys knowledge file
**Module:** `rcm_mc/data_public/hfma_map_keys.py` · **Route:** `/hfma-map-keys`
Encode the HFMA MAP Keys (Patient Access / Clinical Charge Capture / Pre-Billing / Claims Adjudication / Customer Service) as a structured YAML-backed knowledge file with numerator, denominator, exclusion logic, and calculation notes per KPI. Load via stdlib `tomllib`-adjacent pattern (use `json.load` on a committed JSON file under `rcm_mc/data_public/knowledge/hfma_map_keys.json`). UI renders a searchable KPI reference table with effective-date provenance. Cross-link every KPI to any live corpus module that already computes it (`rcm_benchmarks.py`, `revenue_leakage.py`, `denials_management.py` if present).

### P0.2 — NCCI edits loader + edit-compliance scanner
**Module:** `rcm_mc/data_public/ncci_edits.py` · **Route:** `/ncci-scanner`
Ingest the quarterly NCCI PTP (procedure-to-procedure) edit tables and MUE (medically unlikely edit) tables from CMS. Store in a SQLite table under `rcm_mc/data_public/knowledge/ncci.db`. For every corpus deal with a CPT/HCPCS service mix, compute the % of services that would trigger an NCCI edit if billed together. UI: per-deal edit-risk score + top-10 highest-risk code-pair patterns. The blueprint explicitly calls this out as "a killer feature because no consulting firm does this at scale pre-close."

### P0.3 — OIG Work Plan audit-topic tracker
**Module:** `rcm_mc/data_public/oig_workplan.py` · **Route:** `/oig-workplan`
Curated historical index (2015–current) of OIG Work Plan items, tagged by provider type × service line × compliance topic. Each entry: `{year, item_id, title, provider_type, service_line, status, relevance_tags[]}`. For every corpus deal, surface which open Work Plan items match its specialty/geography. Seed with 2024 + 2025 items (manually curated JSON) and leave a `refresh_workplan()` function for future automation.

### P0.4 — OIG Corporate Integrity Agreements (CIA) tracker
**Module:** `rcm_mc/data_public/oig_cia_tracker.py` · **Route:** `/oig-cia`
Index every public OIG CIA since 2010 with entity, execution date, term years, trigger allegation, and monitor type. Cross-reference corpus deal entities (by name similarity) to flag targets with active or recent CIAs as hard red-flag. Seed with ~50 recent healthcare CIAs from the OIG public list.

### P0.5 — DOJ False Claims Act settlement tracker
**Module:** `rcm_mc/data_public/doj_fca_tracker.py` · **Route:** `/doj-fca`
Structured index of healthcare FCA settlements and qui tam unsealings by defendant, dollar amount, allegation type, year. Cross-reference corpus entities to surface any named involvement. Seed with the top 200 healthcare FCA settlements 2015–2026.

### P0.6 — Medicare Claims Processing Manual section index
**Module:** `rcm_mc/data_public/cms_manual_index.py` · **Route:** `/cms-manual`
Build a section-level index of Pub 100-04 (Claims Processing), 100-02 (Benefit Policy), and 100-08 (Program Integrity). Each section: `{pub, chapter, section, title, url, last_updated}`. No full-text ingestion in this pass (RAG comes later) — this is the regulatory-navigation skeleton. UI: searchable table grouped by pub/chapter, deep-linked to CMS.gov.

### P0.7 — CFR Title 42 section tracker
**Module:** `rcm_mc/data_public/cfr_title42.py` · **Route:** `/cfr-42`
Index the regulatory sections of 42 CFR most relevant to RCM diligence (Parts 405 Medicare FFS, 411 Exclusions, 413 Reasonable Cost, 414 Fee Schedule, 422 MA, 423 Part D, 482 Hospital CoPs, 489 Provider Agreements, 1001 OIG exclusions, 1003 CMP). Skeleton with section numbers, titles, effective dates. Feed into future regulatory RAG layer.

---

## Tier 1 — Public Data Ingestion (Blueprint Part 2)

Net-new datasets the blueprint calls out that don't appear in the shipped modules.

### P1.1 — Open Payments (Sunshine Act) ingestion
**Module:** `rcm_mc/data_public/open_payments.py` · **Route:** `/open-payments`
Download + parse CMS Open Payments annual files. Compute per-physician payment concentration (Herfindahl on manufacturer share), total dollars by physician NPI × year × category. For corpus deals with physician rosters, surface loyalty/conflict risk (top-docs highly paid by a single manufacturer = switching risk post-close).

### P1.2 — NPPES NPI registry ingestion
**Module:** `rcm_mc/data_public/nppes_registry.py` · **Route:** `/nppes`
Monthly full-refresh + nightly incremental of NPPES. Build a searchable NPI → (name, taxonomy, practice locations) index. For corpus deals, reconcile billed NPIs vs claimed staff (synthetic-FTE detection). Blueprint explicitly calls this out.

### P1.3 — IRS 990 Schedule J (compensation) ingestion
**Module:** `rcm_mc/data_public/irs990_schedule_j.py` · **Route:** `/irs990-compensation`
AWS Open Data S3 pull of Form 990 Schedule J XML. Parse officer/director/key-employee comp per org × year. Build compensation benchmark distributions by NTEE code × region × org-size. Blueprint: "substitutes substantially for MGMA/Sullivan Cotter data for nonprofit and academic medical centers — a huge piece of the benchmark moat."

### P1.4 — IRS 990 Schedule H (hospital community benefit) ingestion
**Module:** `rcm_mc/data_public/irs990_schedule_h.py` · **Route:** `/irs990-community-benefit`
Parse Schedule H for hospital orgs: charity care %, bad debt, Medicaid shortfall, unreimbursed costs. Annual benchmark distributions by state × bed-size × teaching status.

### P1.5 — AHRQ Quality Indicators runner
**Module:** `rcm_mc/data_public/ahrq_qi_runner.py` · **Route:** `/ahrq-qi`
Wrap the AHRQ QI software (Python/SQL port) as a runtime dependency. For any deal with inpatient discharge volumes, run PQI/IQI/PSI/PDI and project HRRP + HAC-Reduction penalty exposure. Existing `quality_scorecard.py` covers composite scoring but doesn't run the actual AHRQ specs.

### P1.6 — HHS OCR breach portal ingestion
**Module:** `rcm_mc/data_public/hhs_ocr_breaches.py` · **Route:** `/ocr-breaches`
Nightly refresh of the OCR breach portal CSV (500+-individual breaches since 2009). Per-covered-entity breach history + per-business-associate cascade-risk score. Cross-reference corpus deals' vendor lists (future) to surface BAA cascade risk. Complements existing `cyber_risk.py`.

### P1.7 — PACER bankruptcy docket extractor (named-failure backbone)
**Module:** `rcm_mc/data_public/pacer_bankruptcies.py` · **Route:** `/pacer-bankruptcies`
For each named-failure case (Steward SDTX, Envision SDTX, APP DE, Cano DE, Prospect NDTX, Wellpath SDTX), ingest first-day declarations, schedules A/B/D/E/F, and any examiner/independent-director report via RECAP (free) with PACER fallback. Extract capital-structure snapshots, largest-20 unsecured, liquidity trajectory. This feeds the named-failure library (Tier 2).

### P1.8 — BLS QCEW wage tracker
**Module:** `rcm_mc/data_public/bls_qcew_wages.py` · **Route:** `/bls-wages`
County × NAICS quarterly wage data. For each corpus deal, project a labor-inflation forecast by role based on facility-MSA QCEW trend. Feeds `workforce_planning.py` / `workforce_retention.py` (which exist but need the wage-trend input).

### P1.9 — NLRB union election tracker
**Module:** `rcm_mc/data_public/nlrb_elections.py` · **Route:** `/nlrb-elections`
Per-facility union-election history + unfair-labor-practice charges. Per-deal union-risk score. Complements workforce modules.

### P1.10 — Healthcare REIT lease schedule extractor
**Module:** `rcm_mc/data_public/reit_lease_extractor.py` · **Route:** `/reit-leases`
Parse 10-K exhibit lease schedules from MPT, Omega, Healthpeak, Sabra, CareTrust, Ventas, Welltower. Output: tenant × property × annual-rent × escalator × maturity. Existing `reit_analyzer.py` likely covers portfolio overlap analysis but probably not lease-level extraction. Replaces Green Street/CBRE for the specific use case of "which targets have which REIT landlord and what are their rent terms."

### P1.11 — State transaction-review filing scraper
**Module:** `rcm_mc/data_public/state_transaction_reviews.py` · **Route:** `/state-reviews`
Quarterly scrape of CA OHCA, OR HCMO, MA HPC, CT OHS material-change filings. Per-filing: parties, transaction value, sector, review status, conditions imposed. Forward-looking regulatory-calendar + comp-template for live deals.

### P1.12 — Medicare Provider Utilization & Payment Data ingestion
**Module:** `rcm_mc/data_public/medicare_utilization.py` · **Route:** `/medicare-utilization`
Annual Part B / Part D / DME / Referring-Physician provider summary files. Per-NPI × HCPCS × year volume + allowed amounts. Lets the platform baseline a physician group's CPT-level revenue profile before any data room opens. Blueprint: "enough to build a baseline CPT-level revenue and utilization profile for most mid-to-large physician groups before they even open a data room."

---

## Tier 2 — Moat Layer Modules (Blueprint Part 4)

Modules that compose the five declared moat layers. Several have seed versions — prompts below are for expansion to moat-grade, not replacement.

### P2.1 — Named-Failure Library (expand `corpus_red_flags.py`)
**Module:** `rcm_mc/data_public/named_failure_library.py` (new; coexists with `corpus_red_flags.py`)
Structured library of every healthcare PE bankruptcy since 2015 decomposed into: (a) what went wrong, (b) pre-facto signals, (c) specific thresholds & test patterns, (d) citation. Seed with the nine patterns named in the blueprint (Steward, Envision, APP, Cano, Prospect, Wellpath, Envision-USAP-TeamHealth, Cano-CareMax-Babylon, Adeptus variant). Each pattern is a Python `NamedFailurePattern` dataclass with a `match(deal) -> PatternMatch` method returning match-score + triggered-signals. Cross-link to the PACER ingest from P1.7.

### P2.2 — Backtesting Harness (expand `backtester.py` / `value_backtester.py`)
**Module:** `rcm_mc/data_public/deal_outcome_backtester.py`
For every deal in the corpus with a known outcome (IPO, dividend-recap, distressed sale, bankruptcy), replay the platform's verdict as of the deal-announcement date. Compute sensitivity on bankruptcies, specificity on successful exits, calibration (Brier score), and per-signal lift. Publish the sensitivity/specificity numbers on `/backtester-results` as the public credibility artifact. Target: 85%+ sensitivity on bankruptcies, 80%+ specificity on exits.

### P2.3 — Adversarial (Bear Case) Diligence Engine
**Module:** `rcm_mc/data_public/bear_case_engine.py` · **Route:** `/bear-case/<deal_id>`
Given a management thesis for a deal (free-text input or structured fields), automatically: (i) identify every assumption, (ii) stress-test each against the named-failure library (P2.1), (iii) run the v2 bridge + Monte Carlo at worst-quartile inputs, (iv) produce a structured "red team" memo, (v) quantify probability-weighted bear outcome. Uses existing `ic_memo*.py` generators but with inverted framing.

### P2.4 — Benchmark Curve Library aggregator
**Module:** `rcm_mc/data_public/benchmark_curve_library.py` · **Route:** `/benchmark-curves`
Aggregator that pulls from `rcm_benchmarks.py` + `specialty_benchmarks.py` + `subsector_benchmarks.py` + new P1.3 (990-J comp) + P1.4 (990-H community benefit) + HCRIS worksheet-level data into a single curve-registry. Each curve: `{specialty, payer, region, facility_type, year, metric, distribution: {p10..p90, mean, n}}`. Target: 2,500+ curves. UI: curve explorer with multi-slice filters.

### P2.5 — Knowledge Graph binder
**Module:** `rcm_mc/data_public/knowledge_graph.py` · **Route:** `/knowledge-graph`
Stitch P0.1–P0.7 (HFMA, NCCI, OIG, CMS manuals, CFR) + P2.1 (named-failure library) + P2.4 (benchmark curves) into a single queryable graph. Each node: `{id, type, source, effective_date, payload}`. Each edge: `{from, to, relation, weight}`. Query API: `query(deal_profile) -> [relevant_nodes]`. This is the substrate the bear-case engine and the backtester consume.

### P2.6 — Velocity Compound instrumentation
**Module:** `rcm_mc/data_public/velocity_metrics.py` · **Route:** `/velocity`
Track the moat-compound rate: new corpus deals / week, new knowledge-graph nodes / week, new named-failure patterns / month, new benchmark curves / month, backtesting-harness accuracy drift. Plotted as weekly trend lines with targets. Makes the compounding advantage visible.

---

## Tier 3 — Adjacent Analytical Modules

Not strictly moat layers, but called out in the blueprint and not yet covered.

### P3.1 — TUVA Health bridge
**Module:** `rcm_mc/data_public/tuva_bridge.py`
Adapter that ingests TUVA-project dbt-transformed outputs and emits the platform's Canonical Claims Dataset format. Doesn't bring in dbt as a runtime dep — bridge runs offline and checks in JSON/parquet artifacts. Honors the "zero new runtime dependencies" rule.

### P3.2 — Synthea synthetic-population loader
**Module:** `rcm_mc/data_public/synthea_loader.py`
Ingestion helper for MITRE Synthea-generated FHIR/claims bundles. Extends the existing messy-data fixture library with realistic large-scale synthetic populations. Used by the backtesting harness (P2.2) for stress-testing.

### P3.3 — MSSP / ACO REACH / BPCI-A performance ingest
**Module:** `rcm_mc/data_public/cmmi_model_performance.py`
Annual performance files for CMS Innovation Center models. Complements existing `aco_economics.py` + `cms_apm_tracker.py` by ingesting the actual public performance CSVs rather than modeled outputs.

### P3.4 — Medicare Fee Schedule ingest
**Module:** `rcm_mc/data_public/medicare_fee_schedule.py`
Quarterly PFS + HOPPS + ASC payment-rate lookup. Payment-rate reference for unbundling detection + rate-modeling. Complements existing `cms_rate_monitor.py` (which tracks rate changes) but not the base-rate lookup itself.

### P3.5 — Federal Register healthcare-rule calendar
**Module:** `rcm_mc/data_public/federal_register_calendar.py` · **Route:** `/regulatory-calendar`
Daily scrape of Federal Register API; tag healthcare-relevant rules; forward-looking calendar of proposed/final rules with comment deadlines. Feeds `regulatory_risk.py`.

### P3.6 — MedPAC / MACPAC report index
**Module:** `rcm_mc/data_public/medpac_reports.py`
Index of MedPAC June/March reports and MACPAC data books. Each recommendation tagged by provider type + payment impact. Cross-reference corpus deals.

### P3.7 — CMMI TEAM model baseline
**Module:** `rcm_mc/data_public/cmmi_team_model.py`
When CMS releases TEAM (Transforming Episode Accountability Model) baseline data, ingest per-hospital baseline spending. Flag corpus deals that will be mandatory participants.

---

## Already-shipped crosswalk — do NOT duplicate

| Blueprint item | Shipped module(s) |
|---|---|
| Deal corpus (1,705 deals) | `deals_corpus.py` + `extended_seed_*.py` |
| Red-flag scanning | `corpus_red_flags.py`, `redflag_scanner.py` |
| Deal risk scoring | `deal_entry_risk_score.py`, `deal_risk_scorer.py`, `deal_quality_score.py`, `deal_screening_engine.py` |
| Vintage-cohort model | `corpus_vintage_risk_model.py`, `vintage_cohorts.py`, `vintage_analytics.py` |
| CMS benchmark calibration | `cms_benchmark_calibration.py` |
| CMS market / white-space / opportunity | `cms_market_analysis.py`, `cms_white_space_map.py`, `cms_opportunity_scoring.py` |
| CMS provider ranking | `cms_provider_ranking.py` |
| CMS stress / trend | `cms_stress_test.py`, `cms_trend_forecaster.py` |
| CMS data quality | `cms_data_quality.py` |
| Antitrust screening | `antitrust_screener.py` |
| Cyber-risk scoring | `cyber_risk.py` |
| Physician comp / productivity | `phys_comp_plan.py`, `physician_labor.py`, `physician_productivity.py`, `mgmt_comp.py` |
| Payer concentration / mix / shift | `payer_concentration.py`, `payer_mix_shift_model.py`, `payer_shift.py`, `payer_sensitivity.py`, `payer_stress.py` |
| REIT analysis | `reit_analyzer.py`, `medical_realestate.py`, `real_estate.py` |
| NSA exposure | `nsa_tracker.py` |
| 340B / drug pricing | `drug_pricing_340b.py`, `tracker_340b.py` |
| Medicaid unwinding | `medicaid_unwinding.py` |
| Risk adjustment (V28) | `risk_adjustment.py` |
| MA Star ratings | `ma_star_tracker.py`, `ma_contracts.py` |
| Rollup / bolt-on | `bolton_analyzer.py`, `rollup_economics.py` |
| LBO stress | `lbo_stress.py`, `lbo_entry_optimizer.py` |
| ESG | `esg_dashboard.py`, `esg_impact.py` |
| Health equity | `health_equity.py` |
| Sponsor analytics | `sponsor_analytics.py`, `sponsor_heatmap.py`, `sponsor_track_record.py` |
| IC memo generation | `ic_memo.py`, `ic_memo_analytics.py`, `ic_memo_synthesizer.py`, `deal_memo_generator.py` |
| Initial backtester skeleton | `backtester.py` (305L), `value_backtester.py` |

Before writing any new prompt, grep the existing module list. If the concept is already present, the action is **expand** (add fields, add test coverage, add UI slice) not **create**.

---

## Execution order

1. **P0.1–P0.2** first (HFMA keys + NCCI scanner). They establish the knowledge-graph foundation pattern and P0.2 alone is blueprint-marked as "a killer feature."
2. **P1.7 + P2.1** paired (PACER ingest + Named-Failure Library). The credibility artifact.
3. **P2.2** (backtesting harness expansion) + publish sensitivity/specificity numbers publicly. The marketing artifact.
4. **P1.3 + P2.4** (990 Schedule J ingest + benchmark curve library). The benchmark moat.
5. **P2.3** (bear-case engine). The differentiation artifact.
6. Everything else opportunistically.

Each prompt closes with the six-step commit cycle from FEATURE_DEALS_CORPUS.md.

---

> **When Part 4 Moat Layer 6 continuation + remaining blueprint parts arrive, splice new prompts into Tiers 0–3 above rather than growing a Tier 4. The tier structure is a stable mental model — blueprint additions should fit the existing tiers.**
