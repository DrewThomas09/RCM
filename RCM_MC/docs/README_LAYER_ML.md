# Layer: ML — Comparables + Prediction (`rcm_mc/ml/`)

## TL;DR

Two jobs: (1) find comparable hospitals for one target, and (2) use
those comparables to predict missing RCM metrics with honest
uncertainty intervals. Uses numpy closed-form Ridge regression + split
conformal prediction — **no sklearn**. Ships a backtester that
verifies conformal coverage on real data.

## What this layer owns

- Weighted similarity scoring over hospital profiles.
- Ridge regression fits using known metrics as features.
- Split-conformal prediction for 90% coverage intervals.
- Bootstrap intervals for the weighted-median fallback.
- Benchmark P25-P75 fallback for thin cohorts.
- Per-metric reliability grading (A/B/C/D).

## Files

### `comparable_finder.py` (~155 lines)

**Purpose.** Rank peer hospitals by weighted similarity to a target.

**Key exports.**
- `WEIGHTS = {bed_count: 0.25, region: 0.20, payer_mix: 0.25,
  system_affiliation: 0.10, teaching_status: 0.10, urban_rural: 0.10}`.
- `similarity_score(target, peer) -> {"score": float, "components": dict}`.
- `find_comparables(target, all_hospitals, max_results=50) ->
  list[dict]` — top-K peers with `similarity_score` and
  `similarity_components` injected.

**Similarity mechanics.**
- `_bed_similarity(a, b) = 1 - |a-b|/max(a,b)`.
- `_payer_mix_similarity(a, b)` = cosine similarity of payer-pct
  vectors.
- `_equal_similarity(a, b)` = 1.0 if strings match (case-insensitive,
  stripped), else 0.0.
- Missing dimension → contributes 0.5 (neutral), not NaN.

### `ridge_predictor.py` (~470 lines)

**Purpose.** The conformal-calibrated Ridge predictor. Size-gated
fallback ladder — the `reliability_grade` on every output tells
partners how much signal the cohort had.

**Constants.**
- `_MIN_FOR_RIDGE = 15` — need ≥15 peers with the target metric to
  attempt Ridge.
- `_MIN_FOR_MEDIAN = 5` — below Ridge but above this, use
  similarity-weighted median + bootstrap CI.
- `_RIDGE_ALPHA = 1.0` — the regularization.
- `_DEFAULT_COVERAGE = 0.90`.

**Key dataclass.** `PredictedMetric` with `value`, `method`,
`ci_low`, `ci_high`, `coverage_target`, `n_comparables_used`,
`r_squared`, `feature_importances`, `reliability_grade`.

**Core `_RidgeModel` class.**
- Closed-form `(X'X + αI)⁻¹X'y` on z-scored features with intercept.
- `fit(X, y) -> self`, `predict(X) -> np.ndarray`.
- Zero-variance columns handled by replacing sd with 1.0.

**Public function.**
- `predict_missing_metrics(known_metrics, comparables,
  metric_registry, *, coverage=0.90, seed=42) ->
  dict[str, PredictedMetric]`.

**Branch selection.**
- `>= 15` peers with metric + usable features → **Ridge + conformal**.
  70/30 train/cal split via `split_train_calibration()` in
  `conformal.py`. Fits Ridge on train, computes residuals on cal,
  applies the `ceil((1-α)(n+1))/n` quantile as the margin. LOO R² on
  the full cohort for the reliability-grade check. Feature
  importances = |z-scored coefficients| normalized to sum 1.0.
- `5-14` peers → **similarity-weighted median + bootstrap CI**. 1,000
  resamples; per-sim weighted-median statistic; symmetric-percentile
  bounds at `(1-α)/2` and `1-(1-α)/2`.
- `< 5` peers → **benchmark P50 with P25-P75 as the band**.
  `reliability_grade="D"`, `n_comparables_used=0`.

**Reliability grade.** `_grade(method, n, r_squared)`.
- `benchmark_fallback` → always D.
- `weighted_median` → B if n≥10, else C.
- `ridge_regression` → A if n≥30 and R²≥0.60; B if n≥20 and R²≥0.45;
  C if n≥15 and R²≥0.25; else D.

**Dollar-valued metrics never predicted.** `net_revenue`,
`gross_revenue`, `current_ebitda`, `total_operating_expenses` are
financial inputs partners supply — the predictor skips them so the
model never fabricates EBITDA from comparable medians.

### `conformal.py` (~230 lines)

**Purpose.** Distribution-free uncertainty intervals via split
conformal prediction. Independent of Ridge — any object with
`.fit(X, y)` and `.predict(X)` works.

**Key class.** `ConformalPredictor(base_model, coverage=0.90)`.
- `fit(X_train, y_train, X_cal, y_cal)` — trains base model on train
  split, computes absolute residuals on cal split, stores the
  `ceil((1-α)(n+1))/n` quantile as the margin.
- `predict_interval(X_new) -> (point, low, high)` — point ±
  precomputed margin.

**Why conformal over bootstrap / parametric CIs.**
- Gives finite-sample coverage guarantees. If the predictor is
  exchangeable on the calibration set and new point, the 90%
  interval really contains the truth 90% of the time. No normality
  assumption.
- One page of numpy — no sklearn / scipy dep.
- Calibrates per-metric: a poorly-fit Ridge gets a wide margin; a
  well-fit one gets a tight one.

**Helpers.**
- `bootstrap_interval(values, weights, *, coverage, n_bootstrap,
  statistic, random_state) -> (point, low, high)` — for the weighted-
  median fallback.
- `percentile_interval(p25, p50, p75)` — `(p50, p25, p75)` for the
  benchmark fallback.
- `split_train_calibration(X, y, *, cal_fraction=0.3, random_state)` —
  deterministic train/cal split.
- Inline `_erf` (Abramowitz & Stegun 7.1.26) and `_erfinv`
  (Winitzki) — so we can transform uniforms ↔ normals without scipy.

### `feature_engineering.py` (~290 lines)

**Purpose.** Per-metric derived features that lift Ridge R² on
held-out hospitals.

**Public functions.**
- `derive_interaction_features(known_metrics) -> dict` — 6 terms:
  `denial_to_collection_ratio`, `ar_efficiency`, `first_pass_gap`,
  `avoidable_denial_burden`, `payer_complexity_score` (weighted by
  typical payer denial difficulty — 0.4×commercial_pct +
  0.35×medicaid_pct + 0.25×medicare_advantage_pct),
  `revenue_per_bed`.
- `normalize_features(features, benchmark_stats) -> dict` — z-score
  against pre-computed `{metric: {mean, std}}`.
- `derive_features(raw_metrics)` — older 4-term version retained for
  back-compat with `rcm_predictor.py`.
- `normalize_metrics(...)` — older z-score against peer medians.
- `detect_outliers(metrics, comparables, *, threshold_sd=2.5) ->
  list[str]` — flags metrics >threshold σ from cohort mean.

### `backtester.py` (~290 lines)

**Purpose.** Verify the predictor's accuracy + conformal coverage on
held-out data.

**Two styles.**

1. **Legacy LOO backtest** — `backtest(hospital_data)` /
   `run_cohort_backtest()`. For each hospital: mask its metrics,
   predict from the rest of the cohort, score MAE / R² / MAPE. Emits
   per-metric grades. Built for the older `rcm_predictor.py`.

2. **Prompt-5 conformal backtest** — `backtest_predictions(
   hospital_pool, *, holdout_fraction=0.3, n_trials=50,
   coverage=0.90, seed=1337) -> PredictionBacktestResult`. For each
   trial: pick a hospital, hide `holdout_fraction` of its metrics,
   call `ridge_predictor.predict_missing_metrics`, score MAE / R² /
   **coverage rate** (what % of the truth fell inside the
   conformal CI). Coverage health is the critical signal — if 90%
   intervals cover <85% of truth, the conformal calibration is
   broken.

**`PredictionBacktestResult` fields.** `per_metric_mae`,
`per_metric_r_squared`, `coverage_rate`, `n_predictions`,
`overall_reliability` (A/B/C/D/F — capped at C on coverage miss >15
pp), `n_trials`, `holdout_fraction`.

### `rcm_predictor.py` (~505 lines)

**Purpose.** The earlier predictor — kept intact for
`backtester.backtest()` compatibility and the CLI's `predict`
subcommand. Functionally similar to `ridge_predictor.py` but with
slightly different conventions:

- Uses `_MIN_FOR_RIDGE = 10` (vs. 15 in the newer module).
- No conformal prediction — uses parametric CI from residual stddev.
- Slightly different `PredictedMetric` shape (confidence_interval_low/
  high vs. ci_low/ci_high).

**Which to use.** New code → `ridge_predictor.py`. Only legacy
backtester + CLI `predict` still reference `rcm_predictor.py`.

### `__init__.py`

Re-exports both predictors, comparable finder, feature engineering,
and backtester. Tests import from here.

## How it fits the system

```
                 ┌────────────────────────────────┐
                 │  hospital_benchmarks (SQLite)   │
                 └───────────┬────────────────────┘
                             │ comparable pool
                             ▼
              ┌──────────────────────────────┐
              │ ml.comparable_finder          │
              │ find_comparables(target, ...) │
              └──────────────┬───────────────┘
                             │ top-K peers
                             ▼
              ┌──────────────────────────────┐
              │ ml.ridge_predictor            │
              │ predict_missing_metrics()     │
              │  ├── Ridge + conformal        │
              │  ├── Weighted median + boot   │
              │  └── Benchmark P25/P50/P75    │
              └──────────────┬───────────────┘
                             │ dict[metric, PredictedMetric]
                             ▼
              ┌──────────────────────────────┐
              │ analysis.packet_builder       │
              │ step 5: packet.predicted_     │
              │ metrics                        │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ mc.ebitda_mc                  │
              │ from_conformal_prediction()   │ ← prediction CIs → MC
              └──────────────────────────────┘

              ┌──────────────────────────────┐
              │ ml.backtester                 │ ← verifies calibration
              │ backtest_predictions()        │   on held-out data
              └──────────────────────────────┘
```

## Current state

### Strong points
- **Conformal coverage verified.** On 1,000 simulated samples, the
  90% interval lands between 85-96% coverage — empirically tight
  (see `tests/test_ridge_predictor.py::test_coverage_property_on_simulated_data`).
- **No sklearn.** Ridge + conformal + bootstrap implemented in ~300
  lines of numpy. Dependency surface stays at numpy + pandas.
- **Reliability grade surfaces dominant assumption.** Partners see
  "D: benchmark fallback, 0 peers" rather than pretending we have
  cohort signal.
- 38 ridge tests + 28 MC tests verify the prediction-to-simulation
  pipeline end-to-end.

### Weak points
- **Feature importances are |z-scored coefficients|** — rough heuristic,
  not a proper SHAP-style decomposition. Good enough for the UI
  tooltip; not defensible for IC-level attribution.
- **Cohort construction is static.** `find_comparables()` picks the
  top-K by similarity without iterating on prediction quality.
  A proper design would use cross-validation to pick the cohort size
  that minimizes LOO error.
- **No temporal structure.** Predictions treat the cohort as a
  point-in-time snapshot; no handling of metrics that trend over
  time (quarterly denial-rate patterns, seasonal A/R cycles).
- **Conformal assumes exchangeability.** If the target hospital is
  fundamentally different from the comparable cohort (e.g., a
  critical-access hospital using a 400-bed cohort), the 90% coverage
  guarantee is lost. No automatic detection.
- **Single predictor per metric.** No model stacking or ensembling;
  Ridge is the only base model.
