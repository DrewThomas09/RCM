# Analysis

Deal-level analysis engine: packet construction, screening, risk assessment, diligence automation, and cross-deal search. The `DealAnalysisPacket` is the spine of the product — every UI route, API endpoint, and export renders from this single canonical object.

---

## `packet.py` — DealAnalysisPacket Dataclass

**What it does:** Defines the canonical, JSON-serializable container for one deal's complete analysis. Every UI route, API endpoint, and export renders from this single object — nothing renders independently. If a number appears on a page, it came from here.

**How it works:** A hierarchy of `@dataclass` classes covering every analysis section: `HospitalProfile`, `ComparableSet`, `CompletenessAssessment`, `EBITDABridgeResult`, `SimulationSummary`, `RiskFlag`, `DiligenceQuestion`, and `ProvenanceSnapshot`. Includes `to_json()` / `from_json()` round-trip methods (collapsing `NaN`/`Inf` to `None`), a `hash_inputs()` function for cache keying, and `SectionStatus` enum guards (`OK / INCOMPLETE / FAILED / SKIPPED`) so partial builder failures degrade gracefully. `MetricSource` enum tags every value with its provenance tier (`OBSERVED > EXTRACTED > AUTO_POPULATED > PREDICTED > BENCHMARK`).

**Data in:** Written by `packet_builder.py` across 12 sequential build steps.

**Data out:** Consumed by `server.py` routes, `exports/packet_renderer.py`, `ui/analysis_workbench.py`, and all API handlers under `/api/analysis/<id>/`.

---

## `packet_builder.py` — 12-Step Packet Orchestrator

**What it does:** Master orchestrator that walks twelve sequential steps to build a `DealAnalysisPacket`. A failure in any single section marks that section `INCOMPLETE` or `FAILED` — it does not kill the packet. Partners see everything that succeeded.

**How it works:** Each step is a private function (`_step_1_load_profile`, `_step_2_observed_metrics`, etc.). Steps are: (1) load deal profile from SQLite, (2) merge observed metrics, (3) score completeness, (4) find comparables via `ml.comparable_finder`, (5) predict missing metrics via `ml.ridge_predictor` with conformal CIs, (6) build reimbursement profile via `finance.reimbursement_engine`, (7) run v1 EBITDA bridge, (8) run v2 unit-economics bridge, (9) run two-source Monte Carlo, (10) generate risk flags, (11) build provenance snapshot, (12) generate diligence questions. Returns a complete `DealAnalysisPacket` with `run_id`, `build_time_seconds`, and a per-section status map.

**Data in:** `deal_id` from the caller → pulls deal row from `portfolio/store.py` SQLite (`deals` table), analyst-entered metrics from `deal_overrides`, public HCRIS/CMS benchmarks from `hospital_benchmarks` table, comparable hospitals from the ML layer.

**Data out:** A `DealAnalysisPacket` that is cached in the `analysis_runs` SQLite table and returned to the caller.

---

## `analysis_store.py` — Packet Run Cache

**What it does:** SQLite-backed append-only cache for completed `DealAnalysisPacket` runs. Partners can diff "what we thought on Feb 3" against today's run.

**How it works:** Stores packets as gzip-compressed JSON blobs in the `analysis_runs` table, keyed by `(deal_id, scenario_id, as_of, hash_inputs)`. Provides `save_run()`, `load_run()`, `list_runs()`, and `latest_run()` methods. The `hash_inputs` key means re-running with identical inputs returns the cached packet without recomputing. Append-only: existing rows are never overwritten.

**Data in:** `DealAnalysisPacket` objects from `packet_builder.py`. Cache key derived from `packet.hash_inputs()`.

**Data out:** Serialized `DealAnalysisPacket` dicts to any caller requesting a historical or current analysis run.

---

## `anomaly_detection.py` — Calibration Input Anomaly Detector

**What it does:** Automated anomaly detection on deal calibration inputs. Flags values that fall outside expected ranges or violate cross-metric consistency rules, catching data-entry errors before they propagate into the bridge.

**How it works:** Three detection strategies: (1) **statistical** — z-score against the comparable peer cohort, flagging values beyond ±2.5σ; (2) **causal consistency** — uses the `domain/econ_ontology.py` DAG edges to verify that parent/child metric pairs are directionally coherent (e.g., high denial rate should correlate with high AR days); (3) **temporal discontinuity** — detects implausible period-over-period jumps. Returns a list of `AnomalyFlag` objects with severity and a human-readable explanation.

**Data in:** Observed metrics dict from the packet profile; comparable hospital pool from `ml/comparable_finder.py`; ontology edges from `domain/econ_ontology.py`.

**Data out:** List of `AnomalyFlag` objects written into the `DealAnalysisPacket.anomalies` field.

---

## `challenge.py` — Reverse Challenge Solver

**What it does:** Given a target EBITDA outcome (e.g., "management claims $18M improvement"), finds what the underlying metric assumptions would have to be to produce that result. Used in IC prep to challenge management plan projections.

**How it works:** Bisection search over the key driver metric (e.g., denial rate) holding all other inputs fixed. Calls the v1 bridge in a tight loop until the EBITDA output converges to the target within tolerance. Returns the implied metric value along with a "how realistic is this?" assessment cross-referenced against the comparable peer distribution.

**Data in:** A `DealAnalysisPacket` (for current metrics and bridge configuration) plus the analyst's target EBITDA delta.

**Data out:** `ChallengeResult` with the implied metric value, a percentile rank against the peer cohort, and a plain-English achievability assessment.

---

## `cohorts.py` — Tag-Based Portfolio Cohort Analytics

**What it does:** Groups portfolio deals by tag and rolls up weighted-average metrics across each cohort. Answers "how are all my 'behavioral health' deals performing versus my 'acute hospital' deals?"

**How it works:** Pulls all deals with their latest health scores and financial metrics from the portfolio store. Groups by tag (using `deals/deal_tags.py`). Computes NPR-weighted averages of denial rate, AR days, EBITDA margin, MOIC, and health score per cohort. Returns a `CohortSummary` list that the `/cohorts` UI page renders.

**Data in:** `portfolio/store.py` for deal financials; `deals/deal_tags.py` for tag assignments; `deals/health_score.py` for health scores.

**Data out:** `CohortSummary` objects for UI rendering and the `/api/cohorts` JSON endpoint.

---

## `compare_runs.py` — Run Comparison and Year-Over-Year Trend

**What it does:** Side-by-side diff of two `DealAnalysisPacket` runs for the same deal, highlighting which metrics, risk flags, or bridge levers changed between runs.

**How it works:** Loads two runs from `analysis_store.py` by run_id. Computes metric-level deltas (absolute and percentage change). Classifies each change as `IMPROVEMENT / REGRESSION / NEUTRAL` based on the metric's directionality from the ontology. Flags newly appeared or resolved risk flags. Returns a structured diff object the `/api/analysis/<id>/compare` endpoint serves.

**Data in:** Two `DealAnalysisPacket` JSON blobs from `analysis_store.py`; metric directionality from `domain/econ_ontology.py`.

**Data out:** A `RunComparison` dict with per-section diffs, suitable for the comparison UI panel.

---

## `completeness.py` — Data Quality and Coverage Grader

**What it does:** Assesses how complete a deal's data is — which metrics are observed vs predicted vs missing — and ranks the gaps by their EBITDA sensitivity.

**How it works:** Iterates the metric registry and classifies each metric by source tier (`OBSERVED / EXTRACTED / AUTO_POPULATED / PREDICTED / BENCHMARK`). Computes a coverage score weighted by each metric's EBITDA sensitivity coefficient (from `domain/econ_ontology.py`). Assigns an overall `DATA_GRADE` (`A / B / C / D`) and returns a ranked list of the top 5 "most impactful gaps." Also sets `trust_flags` when high-sensitivity metrics fall below the confidence threshold.

**Data in:** The merged metric profile from step 2 of the packet builder; metric registry from `domain/econ_ontology.py`; EBITDA sensitivity weights from the v1 bridge coefficients.

**Data out:** `CompletenessAssessment` dataclass written into the `DealAnalysisPacket`.

---

## `cross_deal_search.py` — Full-Text Cross-Deal Search

**What it does:** Full-text search across deal notes, analyst overrides, risk flags, diligence questions, and packets. Understands RCM jargon so a search for "denial" also matches "IDR", "initial denial rate", "claims denied."

**How it works:** Builds an in-memory inverted index over all deals' text fields on first call (cached in-process). Applies a RCM jargon expansion table (~80 synonym mappings) to the query. Scores matches by TF-IDF. Returns ranked `SearchResult` objects with deal_id, match type (note / risk_flag / packet), excerpt, and highlight offsets.

**Data in:** `deals/deal_notes.py`, `analysis/deal_overrides.py`, and cached `DealAnalysisPacket` blobs from `analysis_store.py`.

**Data out:** Ranked `SearchResult` list served by `GET /api/search?q=...`.

---

## `deal_overrides.py` — Per-Deal Analyst Overrides

**What it does:** Persists analyst-entered metric overrides (e.g., "set denial_rate to 8.5% — seller provided updated billing data") in SQLite across five validated namespaces: `metrics`, `targets`, `assumptions`, `bridge_params`, `mc_params`.

**How it works:** All overrides stored in the `deal_overrides` table with namespace, key, value (JSON), analyst username, timestamp, and optional rationale. The packet builder's step 2 merges these overrides into the profile, tagging them as `MetricSource.OBSERVED`. Provides `set_override()`, `get_overrides()`, `clear_override()`, and a full audit trail via `list_history()`. Uses `BEGIN IMMEDIATE` to prevent concurrent-write races.

**Data in:** Analyst-entered key/value pairs via the UI override form (`POST /api/deals/<id>/overrides`) or CLI `rcm-mc pe override set`.

**Data out:** Override dict consumed by `packet_builder.py` step 2; full override log for the deal's audit trail panel.

---

## `deal_query.py` — Natural-Language Deal Filter

**What it does:** Rule-based natural-language query parser for filtering deals. Turns a string like "denial_rate > 10 AND payer_mix.commercial < 30" into a structured query executed against the portfolio store.

**How it works:** Tokenizes the query string, identifies field/operator/value triples, maps field names to their canonical metric keys using the ontology alias table, and compiles to a safe parameterized SQL WHERE clause. Supports `AND / OR / NOT`, comparison operators, and a set of named shorthand queries ("high_denial", "ar_watch", "covenant_risk"). Returns matching deal_ids for the `/api/deals?filter=...` endpoint.

**Data in:** Query string from the API request; field aliases from `domain/econ_ontology.py`; deal data from `portfolio/store.py`.

**Data out:** List of deal_ids matching the query.

---

## `deal_screener.py` — Fast Public-Data Deal Screener

**What it does:** Scores hospitals from public data only — no ML prediction, no Monte Carlo — to quickly rank candidates against a fund's investment criteria. Used at the top of the funnel before a CIM arrives.

**How it works:** Queries the `hospital_benchmarks` table for HCRIS and Care Compare data. Scores each hospital across five axes: denial rate percentile, AR days percentile, CMI vs peers, payer-mix commercial exposure, and star-rating quality signal. Aggregates into a composite "investability score" (0–100). Returns a ranked `ScreenResult` list with a pass/watch/pass verdict per hospital.

**Data in:** CMS HCRIS benchmarks and Care Compare data from the `hospital_benchmarks` SQLite table (loaded by `data/data_refresh.py`).

**Data out:** Ranked `ScreenResult` list for the `/screen` UI page and `/api/screen` JSON endpoint.

---

## `deal_sourcer.py` — Thesis-Driven Deal Sourcing

**What it does:** Predictive deal sourcing that scores every HCRIS hospital against a fund's thesis criteria and returns a prioritized outreach list.

**How it works:** Loads the full HCRIS hospital universe (~6,000 records) from the `hospital_benchmarks` table. For each hospital, computes thesis fit across configurable dimensions (payer mix targets, denial rate gap, revenue scale, geography, bed count). Applies the fund's thesis weights (loaded from `configs/fund_thesis.yaml` or the API). Returns a ranked list with fit score, key supporting metrics, and a brief thesis-match rationale.

**Data in:** `hospital_benchmarks` table (HCRIS data); fund thesis config from YAML or API parameters.

**Data out:** Ranked sourcing list for the `/source` UI page.

---

## `diligence_questions.py` — Auto-Generated Diligence Questionnaire

**What it does:** Generates a prioritized P0/P1/P2 diligence question list that cites the specific triggering metric and threshold (e.g., "At 14.5% denial rate, please provide the root-cause breakdown by payer and denial category").

**How it works:** Rule-driven generator: iterates the packet's `risk_flags` and `completeness.gaps` lists, maps each flag/gap to a question template, fills in the triggering metric value and peer comparison, and assigns priority (P0 = blocks IC, P1 = required pre-LOI, P2 = nice to have). Deduplicates overlapping questions and sorts by priority + EBITDA sensitivity. Returns a `DiligenceQuestion` list that the workbench Question tab renders.

**Data in:** `DealAnalysisPacket.risk_flags`, `DealAnalysisPacket.completeness`, and metric values from the profile.

**Data out:** `DiligenceQuestion` list written into the `DealAnalysisPacket` and rendered on the workbench Question tab.

---

## `playbook.py` — Archetype Playbook Builder

**What it does:** Finds historical portfolio deals sharing the same archetype as the current deal and surfaces per-lever success rates and timing benchmarks, so the IC team can say "denial turnaround deals average 14 months to full realization in our portfolio."

**How it works:** Classifies the current deal's dominant thesis archetype (payer-mix shift / back-office / CMI uplift / etc.) by scoring the bridge lever stack. Queries the `public_deals` corpus and portfolio history for deals with the same archetype classification. Aggregates realized MOIC, IRR, hold years, and per-lever realization rates. Returns a `PlaybookSummary` with historical benchmarks and red-flag patterns from failed deals in the archetype.

**Data in:** Current deal's `DealAnalysisPacket` bridge levers; historical deal data from `data_public/deals_corpus.py` and portfolio `analysis_runs` cache.

**Data out:** `PlaybookSummary` for the workbench Playbook panel.

---

## `pressure_test.py` — Management Plan Pressure Test

**What it does:** Given a management plan (target metrics), classifies each initiative as "achievable / stretch / unrealistic" and runs the MC under a missed-targets scenario to show the downside.

**How it works:** For each target metric delta in the management plan, computes a percentile rank against the comparable peer set (bottom-quartile improvement = achievable, top-decile = stretch). Runs a second Monte Carlo pass where all metrics miss by their historical miss rate. Returns a `PressureTestResult` with per-initiative achievability grades, a miss-scenario MOIC distribution, and a "if management is 30% wrong across the board, P50 MOIC drops from X to Y" summary.

**Data in:** Management plan targets from the packet profile; comparable peer distributions from `ml/comparable_finder.py`; MC engine from `mc/ebitda_mc.py`.

**Data out:** `PressureTestResult` written into the `DealAnalysisPacket.pressure_test` field.

---

## `refresh_scheduler.py` — Stale Packet Detector

**What it does:** Identifies cached analysis packets that were built before their underlying data sources (HCRIS, CMS refreshes, analyst overrides) were last updated. Optionally triggers a rebuild.

**How it works:** Queries the `analysis_runs` cache for each deal's `built_at` timestamp. Compares against the latest `loaded_at` timestamps in `hospital_benchmarks` and the latest override `created_at` in `deal_overrides`. Flags runs where the source data is newer than the cached packet. Supports an `auto_rebuild=True` mode that re-queues stale packets through the job queue.

**Data in:** `analysis_runs` table timestamps; `hospital_benchmarks.loaded_at`; `deal_overrides.created_at` — all from SQLite via `portfolio/store.py`.

**Data out:** Stale packet list and optionally a rebuild job queue entry.

---

## `risk_flags.py` — Automated Risk Flag Generator

**What it does:** Classifies deal risk across six categories (Operational / Regulatory / Payer / Coding / Data Quality / Financial) with CRITICAL / HIGH / MEDIUM / LOW severity. Includes OBBBA and Medicaid work-requirement amplification logic for Medicaid-heavy deals in specific states.

**How it works:** Rule-based evaluators: each evaluator inspects a specific metric or combination of metrics against calibrated thresholds (e.g., denial rate > 12% = HIGH Operational, commercial payer mix < 20% AND state in OBBBA risk list = CRITICAL Regulatory). Returns `RiskFlag` objects with the triggering metric value, peer percentile, and a one-sentence context string. OBBBA state list (AR / GA / KY / NH / OH / UT / WI / IA / MT) amplifies Medicaid-volume flags to CRITICAL.

**Data in:** `DealAnalysisPacket` metric profile; state field from the hospital profile; peer percentiles from the comparable set.

**Data out:** `RiskFlag` list written into `DealAnalysisPacket.risk_flags` and rendered on the Risk tab.

---

## `stress.py` — Monte Carlo Stress Testing Utilities

**What it does:** Runs beta-distributed parameter shocks against the MC simulator to produce a stress distribution — "what happens if every lever underperforms by 1 standard deviation simultaneously?"

**How it works:** Takes the current MC configuration and applies correlated downward shocks to all target metrics simultaneously (beta-distributed shocks with α and β calibrated to the desired stress level). Runs a second MC pass under the shocked config. Returns the stressed P10/P50/P90 MOIC distribution alongside the base-case distribution for side-by-side comparison.

**Data in:** Current `DealAnalysisPacket` MC configuration; shock parameters from the `scenarios/scenario_shocks.py` preset library.

**Data out:** `StressResult` with base-case and stressed MOIC distributions.

---

## `surrogate.py` — Fast MC Surrogate Placeholder

**What it does:** Placeholder for a fast ML surrogate model trained on historical MC runs, intended to return a P50 MOIC estimate in milliseconds without running the full simulation. Not currently wired into the main pipeline.

**How it works:** Stub implementation returns `None`. The design intent is a Ridge/tree model trained offline on (metric inputs → MC P50 MOIC) pairs from the `analysis_runs` corpus. Present in the codebase to reserve the interface for a future fast-path screening use case.

**Data in:** N/A (stub).

**Data out:** N/A (stub).

---

## Key Concepts

- **Single source of truth**: The `DealAnalysisPacket` is the only object renderers consume. If a number shows up on a page, it came from here.
- **Graceful degradation**: Each of the twelve builder steps can fail independently without killing the packet. Partners always see a partial result.
- **Append-only caching**: Analysis runs are never overwritten — partners can diff "what we thought on Feb 3" vs. today.
- **Rule-based risk**: Risk flags are explicit, auditable rules — not ML predictions. Every flag cites its trigger value and the threshold it crossed.
