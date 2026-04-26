# Report 0092: Map Next Directory — `rcm_mc/ml/`

## Scope

`RCM_MC/rcm_mc/ml/` — entirely unmapped per Report 0091 top-priority list. Phase-1 regression prediction engine per CLAUDE.md.

## Findings

### HIGH-PRIORITY DISCOVERY

**`rcm_mc/ml/` is the largest unmapped subpackage in the project — 41 modules, 13,423 lines of code.** That's ~16× the size of `auth/` (Report 0062: 810 lines) and roughly 1.2× the size of `server.py`. Until this report it had **zero coverage** across 91 prior reports.

### Inventory (41 .py files, sorted by size)

| File | Lines | Purpose (per filename + __init__ context) |
|---|---|---|
| `labor_efficiency.py` | 537 | Labor-cost vs throughput modeling |
| `ridge_predictor.py` | 510 | Ridge regression core (Phase-1 predictor per CLAUDE.md) |
| `model_quality.py` | 506 | Model fit / residual quality scoring |
| `regime_detection.py` | 505 | Market-regime detection (recession / expansion?) |
| `rcm_predictor.py` | 505 | Top-level predict_missing() API entry-point |
| `temporal_forecaster.py` | 498 | Time-series forecasting |
| `payer_mix_cascade.py` | 474 | Payer-mix cascade modeling |
| `geographic_clustering.py` | 474 | Geographic clustering of hospitals |
| `trained_rcm_predictor.py` | 468 | Pre-trained variant of rcm_predictor |
| `ensemble_methods.py` | 442 | Ensemble math primitives |
| `ensemble_predictor.py` | 422 | Ensemble predictor wrapper |
| `contract_strength.py` | 420 | Payer-contract strength scoring |
| `prediction_ledger.py` | 390 | Audit trail of predictions |
| `investability_scorer.py` | 377 | Composite investability score |
| `anomaly_detector.py` | 371 | Statistical anomaly detection |
| `volume_trend_forecaster.py` | 367 | Procedural volume trend forecast |
| `rcm_performance_predictor.py` | 361 | RCM-perf-specific predictor |
| `portfolio_learning.py` | 353 | Cross-deal learning (warm-start priors?) |
| `margin_predictor.py` | 343 | Margin / EBITDA predictor |
| `backtester.py` | 342 | Public API: `backtest()`, `run_cohort_backtest()` |
| `service_line_profitability.py` | 311 | Per-service-line P&L |
| `forward_distress_predictor.py` | 304 | Forward-looking distress |
| `bayesian_calibration.py` | 303 | Bayesian prior calibration |
| `improvement_potential.py` | 299 | Upside-capture estimator |
| `feature_engineering.py` | 295 | Public API: `derive_features`, `normalize_metrics`, `detect_outliers` |
| `distress_predictor.py` | 295 | Hospital distress (post-event) |
| `rcm_opportunity_scorer.py` | 285 | RCM-improvement opportunity score |
| `hospital_clustering.py` | 262 | Hospital-level clustering (peer find?) |
| `conformal.py` | 253 | Conformal-prediction intervals |
| `days_in_ar_predictor.py` | 223 | DSO predictor |
| `realization_predictor.py` | 217 | Net-realization-rate predictor |
| `feature_importance.py` | 215 | Feature-importance scoring |
| `collection_rate_predictor.py` | 202 | Collection-rate predictor |
| `fund_learning.py` | 200 | Fund-level learning |
| `market_intelligence.py` | 198 | Market-intel signals |
| `queueing_model.py` | 195 | Queueing-theory math |
| `denial_rate_predictor.py` | 194 | Denial-rate predictor |
| `efficiency_frontier.py` | 175 | Pareto efficiency frontier |
| `comparable_finder.py` | 155 | Public API: `find_comparables`, `similarity_score` |
| `survival_analysis.py` | 147 | Time-to-event modeling |
| `__init__.py` | 30 | Public re-exports (10 names) |

### Documented public surface (per `__init__.py`)

10 names re-exported:
- `find_comparables`, `similarity_score` (from `comparable_finder.py`)
- `derive_features`, `normalize_metrics`, `detect_outliers` (from `feature_engineering.py`)
- `RCM_METRICS`, `PredictedMetric`, `predict_missing` (from `rcm_predictor.py`)
- `BacktestResult`, `backtest`, `run_cohort_backtest` (from `backtester.py`)

**41 modules; only 4 are publicly re-exported.** 37 modules are internal — accessible only by their module path (`from rcm_mc.ml.X import Y`). Per CLAUDE.md package-layout convention, this is acceptable, but **the asymmetry is striking**: 37 large modules with no documented entry-point.

### CLAUDE.md says ml/ has TWO files

CLAUDE.md (Phase 4 list, line "Key modules added in Phase 4") names:
- `rcm_mc/ml/ridge_predictor.py`
- `rcm_mc/ml/conformal.py`

Plus, Phase 1 says: "Probabilistic models of per-KPI outcomes... fit via `rcm_mc/calibration.py`."

**Reality:** 41 files, not 2. CLAUDE.md is **catastrophically out of date** for `rcm_mc/ml/`. Either Phase 1 or Phase 4 quietly grew this subpackage with no doc update.

### Suspicious / flag-worthy

| Item | Note |
|---|---|
| `README.md` (29 KB) | Massive in-package README. Larger than any other subpackage README. Likely contains the actual ml/ map. **Not yet read.** |
| `__pycache__/` with 26 entries | Build artifact; should be `.gitignore`d. Per Report 0001 the repo .gitignore covers `__pycache__/` so this is local-only. |
| Two `_predictor.py` families | `rcm_predictor.py` (505L) AND `trained_rcm_predictor.py` (468L) AND `rcm_performance_predictor.py` (361L). 3 separate "rcm predictors" — overlap risk. |
| Two ensembles | `ensemble_methods.py` (442L) + `ensemble_predictor.py` (422L). Possibly methods-vs-orchestrator split or duplicate work. |
| `distress_predictor.py` (295L) AND `forward_distress_predictor.py` (304L) | Two distress models. Forward-vs-historical split or duplicate. |
| Mtimes split: 25 files at `Apr 17 10:27`, 16 files at `Apr 25 12:01` | The Apr 25 batch is the most recent — coincides with the J2 ship and audit kickoff per Report 0089. **Apr 25 modules are likely the freshest / most-recently-touched.** |

### Apr 25 (most-recent) module set

- `collection_rate_predictor.py`, `conformal.py`, `contract_strength.py`, `days_in_ar_predictor.py`, `denial_rate_predictor.py`, `ensemble_methods.py`, `feature_importance.py`, `forward_distress_predictor.py`, `geographic_clustering.py`, `improvement_potential.py`, `labor_efficiency.py`, `model_quality.py`, `payer_mix_cascade.py`, `regime_detection.py`, `service_line_profitability.py`, `trained_rcm_predictor.py`, `volume_trend_forecaster.py`, `README.md`

These 17 are the diff frontier — likely added or rewritten in the Apr 17→25 cycle.

### Cross-link to architecture

Per CLAUDE.md Phase 1: ML predictions feed simulator priors. Per Phase 4: `ml/ridge_predictor.py + conformal.py` go into `DealAnalysisPacket.predictions`. So `rcm_mc/ml/` is **upstream of** the simulator (Phase 2) AND of the packet (Phase 4) — a foundation layer.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR502** | **41-module subpackage with only 4 modules in public surface** | 37 internal modules — any rename or signature change is a silent breaking change for any caller that imports by path. Inventory needed. | **High** |
| **MR503** | **CLAUDE.md "Phase 4 added ridge_predictor + conformal" claim is incomplete** | 39 OTHER ml/ modules exist that CLAUDE.md doesn't mention. Architecture doc rot is severe here. | **High** |
| **MR504** | **Three `*_predictor.py` files for "rcm" alone (rcm_predictor / trained_rcm_predictor / rcm_performance_predictor)** | High likelihood of overlapping behavior. Merge risk: a feature branch may modify one and not the others. | **Medium** |
| **MR505** | **Two ensemble files** (`ensemble_methods.py` + `ensemble_predictor.py`) | Same overlap pattern. | Low |
| **MR506** | **Two distress files** (`distress_predictor.py` + `forward_distress_predictor.py`) | Same overlap pattern. | Low |
| **MR507** | **`README.md` (29 KB) inside the package — likely is the package map** | If this report skipped reading it, future iterations should. May contain authoritative inventory. | (advisory) |
| **MR508** | **No tests cited** | Per Report 0008 etc. tests/ exists at top level. Whether `rcm_mc/ml/`'s 13K lines have any tests is unknown — Report 0091 listed 280+ unmapped test files. | **High** |

## Dependencies

- **Incoming:** simulator (Phase 1), packet_builder (Phase 4 step likely "predictions"), CLI `rcm-mc analysis`. Not yet line-traced.
- **Outgoing:** numpy (per Report 0046), portfolio.store (likely; not confirmed), stdlib.

## Open questions / Unknowns

- **Q1.** What is in the 29 KB `rcm_mc/ml/README.md`? Likely closes most ml/ questions.
- **Q2.** Which `*_predictor.py` is canonical — `rcm_predictor.py`, `trained_rcm_predictor.py`, or `rcm_performance_predictor.py`?
- **Q3.** What are `ensemble_methods` vs `ensemble_predictor` semantics?
- **Q4.** Test coverage of the 41 modules?
- **Q5.** Did Apr 25 commits introduce 17 new ml/ modules or rewrite existing ones? Per Report 0089 the audit chain started Apr 25; 17 ml/ modules with same mtime is suspicious — possibly batch-touched.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0093** | Read `rcm_mc/ml/README.md` (closes Q1+Q2+Q3 in one file). |
| **0094** | Read `ridge_predictor.py` body (510L) — Phase-1 core per CLAUDE.md. |
| **0095** | `git log --follow rcm_mc/ml/labor_efficiency.py` (largest file) to dispel Q5. |
| **0096** | Test coverage spot-check (closes Q4) — pick ml/comparable_finder.py (smallest public-surface module). |

---

Report/Report-0092.md written.
Next iteration should: read `rcm_mc/ml/README.md` (29 KB, likely contains the authoritative subpackage map).
