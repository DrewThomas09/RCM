# ML (Machine Learning)

Machine learning layer for metric prediction, anomaly detection, backtesting, and forecasting. All models are numpy-only (no sklearn/scipy) — Ridge regression is implemented from the closed-form solution, and conformal prediction provides distribution-free uncertainty intervals.

---

## `ridge_predictor.py` — Conformal-Calibrated Ridge Predictor

**What it does:** The primary metric prediction engine used in the Deal Analysis Packet. For each missing RCM metric on a deal, produces a point estimate and a 90% conformal prediction interval. This is the module that answers "what is this hospital's denial rate, and how certain are we?"

**How it works:** Three-tier fallback ladder keyed on comparable cohort size: (1) **Ridge + conformal** (≥15 peers with the target metric): fits closed-form Ridge regression `β = (XᵀX + αI)⁻¹Xᵀy` with `α=1.0`, splits the comparables 70/30 into train/calibrate sets, runs split conformal calibration (`conformal.py`) to compute a residual quantile `q` that achieves the nominal 90% coverage. CI: `[ŷ − q, ŷ + q]`. Grade A (n≥30, R²≥0.60) or B (n≥15). (2) **Weighted median + bootstrap** (5–14 peers): similarity-weighted median prediction; 1,000 bootstrap resamples for symmetric percentile CI. Grade B (n≥10) or C. (3) **Benchmark fallback** (<5 peers): uses the metric registry P25/P50/P75 as point estimate and CI band. Grade D. Dollar-valued metrics (`net_revenue`, `gross_revenue`, `current_ebitda`, `total_operating_expenses`) are never predicted — they are always analyst inputs.

**Data in:** Comparable hospital pool from `ml/comparable_finder.py` (list of dicts with metric values); target metric name; metric registry from `domain/econ_ontology.py`; coverage target (default 0.90).

**Data out:** `PredictedMetric` dataclass per metric: `value`, `ci_low`, `ci_high`, `method` (ridge_regression / weighted_median / benchmark), `coverage_target`, `n_comparables_used`, `r_squared`, `feature_importances`, `reliability_grade`. Written into `DealAnalysisPacket.predicted_metrics`.

---

## `rcm_predictor.py` — Original Ridge Prediction Engine (Phase 1)

**What it does:** The original Phase 1 metric predictor. Still used as the default by the backtester and legacy CLI callers. Predicts missing RCM metrics from a comparable hospital pool using Ridge regression and weighted median fallback.

**How it works:** Functionally similar to `ridge_predictor.py` but returns simpler output: `(predicted_value, lower_bound, upper_bound)` tuples without conformal calibration. Uses sklearn-compatible API surface (fit/predict pattern) without actually importing sklearn. The Ridge closed-form is the same numpy implementation. This module remains as the stable interface for the backtester and CLI to avoid breaking existing test contracts.

**Data in:** Same as `ridge_predictor.py`: comparable hospital pool, target metric, metric registry.

**Data out:** `(value, lower, upper)` tuple per metric — simpler than `PredictedMetric` but sufficient for legacy callers.

---

## `conformal.py` — Split Conformal Prediction

**What it does:** Implements split conformal prediction — a distribution-free method for constructing honest uncertainty intervals with no normality assumption, only exchangeability.

**How it works:** Given a fitted base model `f̂` and a calibration set `{(x_j, y_j)}`: computes residuals `R_j = |y_j − f̂(x_j)|`, takes the `⌈(1−α)(n+1)⌉`-th quantile `q` of the residuals. For any new input `x*`: the interval `[f̂(x*) − q, f̂(x*) + q]` covers `y*` with probability ≥ `1−α` under exchangeability. Also provides `bootstrap_interval()` (percentile bootstrap for small cohorts) and `percentile_interval()` (benchmark band). `split_train_calibration(data, split=0.70)` handles the 70/30 split. Empirically verified: 90% intervals cover 85–96% of held-out samples in the regression test suite.

**Data in:** Calibration set `(X, y)` arrays; fitted Ridge model weights; coverage target `α`.

**Data out:** Scalar quantile `q` for the symmetric interval; or bootstrap CI tuple.

---

## `comparable_finder.py` — Weighted 6-Dimension Hospital Similarity

**What it does:** Finds the most similar hospitals in the benchmark database to a target deal. The comparables feed the Ridge predictor and are displayed on the workbench as "peer hospitals."

**How it works:** Scores similarity on six weighted dimensions: (1) **Bed count** (weight 0.25) — `1 − |a−b| / max(a,b)`, continuous; (2) **Region** (0.20) — binary match on 4-region US census grouping; (3) **Payer mix** (0.25) — cosine similarity of 6-component payer vectors; (4) **System affiliation** (0.10) — binary match; (5) **Teaching status** (0.10) — binary match; (6) **Urban/rural** (0.10) — binary match. Missing dimension → 0.5 (neutral, not NaN). Weighted sum produces a [0,1] similarity score. Returns top-K comparables sorted by score, filtered to those above a minimum threshold.

**Data in:** Target hospital profile (bed count, region, payer mix, etc.) from the `DealAnalysisPacket`; benchmark hospital pool from `hospital_benchmarks` SQLite table (HCRIS data).

**Data out:** List of `ComparableHospital` objects with similarity score, hospital name, and metric values.

---

## `feature_engineering.py` — Interaction Terms and Z-Score Normalization

**What it does:** Creates derived interaction features for the Ridge predictor and normalizes all features against peer medians. The interaction terms capture non-linear relationships the raw metrics miss.

**How it works:** Five interaction terms: `denial_to_collection_ratio = denial_rate / net_collection_rate`, `ar_efficiency = 1 / days_in_ar × net_collection_rate`, `first_pass_gap = first_pass_rate − industry_benchmark`, `avoidable_denial_burden = denial_rate × avoidable_share`, `payer_complexity_score = 0.4×commercial_pct + 0.35×medicaid_pct + 0.25×MA_pct`. `revenue_per_bed = net_revenue / bed_count`. All features z-scored against the comparable set's mean and std: `z = (x − peer_mean) / peer_std`. Values beyond ±2.5σ are winsorized. Missing feature inputs set to 0.0 (peer median in z-score space) rather than excluded.

**Data in:** Hospital metric dicts from the comparable pool; peer statistics from `comparable_finder.py`.

**Data out:** Normalized feature matrix (numpy array) for the Ridge predictor.

---

## `anomaly_detector.py` — Three-Strategy Anomaly Detection

**What it does:** Detects unusual metric values in the deal calibration inputs across three strategies. Catches data errors before they propagate into the bridge and MC.

**How it works:** (1) **Statistical (z-score)**: flags values beyond ±2.5σ against the comparable peer distribution; (2) **Causal consistency**: uses the `domain/econ_ontology.py` DAG to check directionally coherent pairs (high denial_rate should correlate with high days_in_ar — if both are entered and they conflict, flag it); (3) **Temporal discontinuity**: flags period-over-period changes exceeding 3× the historical standard deviation. Returns `AnomalyFlag` objects with strategy, severity, triggering metric, value, expected range, and a human-readable explanation.

**Data in:** Deal metric profile from the packet; comparable peer statistics from `comparable_finder.py`; causal edges from `domain/econ_ontology.py`; prior-period metrics from `deals/deal_sim_inputs.py`.

**Data out:** `AnomalyFlag` list written into `DealAnalysisPacket.anomalies`.

---

## `backtester.py` — Hold-Out Backtester

**What it does:** Validates prediction accuracy by masking hospital metrics and testing whether the predictor's CI contains the true value. The critical output is the empirical coverage rate — if <85%, conformal calibration is broken.

**How it works:** Two modes: (1) **Legacy LOO (leave-one-out)**: for each hospital in the benchmark pool, masks that hospital's metrics and predicts from the remaining peers. Scores MAE, R², MAPE per metric. (2) **Conformal coverage**: masks `holdout_fraction` (default 20%) of a hospital's metrics, predicts them, checks whether the true value falls within the 90% CI. Coverage rate is the primary signal. Returns a `BacktestReport` with per-metric grades (A–F) and an overall coverage assertion.

**Data in:** Benchmark hospital pool from `hospital_benchmarks` SQLite table; metric registry; coverage target.

**Data out:** `BacktestReport` with per-metric MAE/R²/MAPE and empirical coverage rates.

---

## `ensemble_predictor.py` — Auto-Selecting Ensemble

**What it does:** Selects the best prediction model per metric by comparing Ridge, k-nearest-neighbors, and weighted-median on held-out MAE. Returns the ensemble's prediction using the selected best model.

**How it works:** For each target metric: runs all three models on a held-out validation split of the comparable set. Selects the model with lowest MAE. Uses that model's prediction and CI for the final output. Falls back to the weighted median if no model achieves R² > 0.30. The ensemble picker is re-run per deal (not pre-fitted globally) since comparable sets differ.

**Data in:** Comparable hospital pool from `comparable_finder.py`; target metric; validation split from the comparables.

**Data out:** `PredictedMetric` using the best-performing model for that metric.

---

## `temporal_forecaster.py` — Time-Series Metric Trend Detection

**What it does:** Forecasts future metric values using historical quarterly snapshots. Used for "where will denial rate be in 18 months at the current trajectory?" projections.

**How it works:** Auto-selects the forecasting method based on data length: (1) **Linear OLS** (≥6 periods): fits `y = β₀ + β₁t` via least squares, returns point forecast and prediction interval; (2) **Holt-Winters** (≥8 periods + detected seasonality): applies additive exponential smoothing with trend and seasonal components; (3) **Weighted recent** (<6 periods): exponentially down-weights older observations, uses weighted mean as forecast with bootstrap CI. Method selection logged for transparency.

**Data in:** Historical quarterly metric snapshots from `deals/deal_sim_inputs.py`; target metric name; forecast horizon in quarters.

**Data out:** `TemporalForecast` with method, point estimate, CI, and confidence grade.

---

## `portfolio_learning.py` — Cross-Deal Prediction Bias Shrinkage

**What it does:** Detects systematic prediction bias across the fund's deal history (e.g., "we consistently underpredict denial rates by 2pp for behavioral health deals") and shrinks new predictions toward the corrected prior.

**How it works:** Loads all historical `(predicted, actual)` metric pairs from the portfolio's `predicted_vs_actual.py` records. Computes per-metric, per-segment (vertical, region) bias as `mean(predicted − actual)`. If bias exceeds a materiality threshold (default 1pp for rates, 5% for dollar metrics), applies a shrinkage correction to new predictions: `adj_prediction = prediction − λ × bias` where `λ = 0.5` (partial shrinkage to avoid overcorrecting). Reports the bias map and correction factors applied.

**Data in:** Historical prediction/actual pairs from `pe/predicted_vs_actual.py`; new deal's `PredictedMetric` objects.

**Data out:** Bias-corrected `PredictedMetric` objects; `BiasReport` for the model improvement panel.

---

## Additional ML Modules

### `distress_predictor.py`
**What it does:** Predicts the probability that a held deal will breach covenants or require operational intervention within 12 months.
**How it works:** Logistic regression (closed-form numpy) over features: cumulative variance from plan, alert count, health score trend, payer mix shift. Calibrated on portfolio history. Returns a distress probability and top-3 risk drivers.
**Data in:** Deal health history from `deals/health_score.py`; alerts from `alerts/alert_history.py`.
**Data out:** Distress probability score for the portfolio monitor.

### `efficiency_frontier.py`
**What it does:** Plots the Pareto frontier of (expected MOIC, downside risk) across all active scenarios for a deal. Identifies which scenario is optimal for a given risk-tolerance level.
**How it works:** Runs MC under each scenario, computes (mean MOIC, downside σ) coordinates. Identifies Pareto-dominant scenarios. Returns the frontier points for the scenario comparison chart.
**Data in:** Multiple `MonteCarloResult` objects from `mc/scenario_comparison.py`.
**Data out:** Frontier point list for the scenario comparison visualization.

### `fund_learning.py`
**What it does:** Aggregates prediction accuracy and bridge realization patterns across the entire fund portfolio to generate playbook-level insights (e.g., "CDI initiatives in behavioral health have realized at 65% of the underwritten uplift on average").
**How it works:** Groups all hold-period variance data by initiative type and deal vertical. Computes realization rates and their confidence intervals. Flags systematic playbook issues (realization < 50% for any initiative/vertical combination).
**Data in:** Hold-period variance data from `pe/hold_tracking.py`; initiative definitions from `rcm/initiatives.py`.
**Data out:** Fund-level realization rate table for the Fund Learning page.

### `hospital_clustering.py`
**What it does:** Clusters the HCRIS hospital universe into peer groups using k-means on the 6 comparable dimensions. Used for deal screening and benchmark calibration.
**How it works:** Applies k-means (numpy implementation, k=12 default) to the 6-dimensional feature space after z-score normalization. Returns cluster assignments and centroid profiles. Cluster labels are human-readable (e.g., "Large urban teaching hospital, commercial-heavy").
**Data in:** `hospital_benchmarks` HCRIS data for all ~6,000 hospitals.
**Data out:** Cluster assignment per hospital; centroid profiles for the benchmark calibration page.

### `investability_scorer.py`
**What it does:** Produces a 0–100 investability score for a hospital based purely on public data, representing how attractive it is as a PE target for an RCM turnaround thesis.
**How it works:** Scores 5 dimensions: denial rate gap vs. peer median, AR days gap, commercial payer mix, revenue scale ($50M–$400M sweet spot), and quality signal (Care Compare stars). Weighted sum with hand-tuned weights based on fund experience. Returns score + per-dimension component breakdown.
**Data in:** `hospital_benchmarks` HCRIS + Care Compare data.
**Data out:** `InvestabilityScore` for the deal sourcing and screening pages.

### `margin_predictor.py`
**What it does:** Predicts a hospital's EBITDA margin from structural features when margin is not directly observed. Used as a sanity check against analyst-entered margins.
**How it works:** Ridge regression with features: bed count, payer mix, teaching status, CMI, operational efficiency metrics. Conformal CI via `conformal.py`. Returns predicted margin ± CI alongside a "plausibility flag" if the analyst-entered margin is outside the CI.
**Data in:** Hospital structural features from the profile; comparable hospitals from `comparable_finder.py`.
**Data out:** Predicted margin and plausibility assessment.

### `market_intelligence.py`
**What it does:** Aggregates market-level signals (payer mix trends, regional wage inflation, MA penetration rates) to provide deal-specific market context.
**How it works:** Queries CMS utilization and HCRIS data for the hospital's MSA/state. Computes 3-year trends in commercial-to-MA mix shift, regional wage inflation proxy (CMS wage index), and HHI market concentration. Returns a `MarketIntelligence` summary for the deal workbench.
**Data in:** `hospital_benchmarks` utilization and HCRIS data; CMS wage index from HCRIS wage cost lines.
**Data out:** `MarketIntelligence` dict for the deal workbench Market tab.

### `prediction_ledger.py`
**What it does:** Append-only SQLite ledger recording every metric prediction made by the platform, enabling systematic accuracy tracking and model improvement.
**How it works:** Writes a `prediction_events` row for every `PredictedMetric` produced: deal_id, metric, predicted value, CI, method, timestamp. When actuals are later entered (via deal snapshots), a second `outcome_events` row is linked. The backtester and portfolio learning modules query this ledger.
**Data in:** `PredictedMetric` objects from `ridge_predictor.py`; actual values from `deals/deal_sim_inputs.py`.
**Data out:** Historical prediction/outcome pairs for `backtester.py` and `portfolio_learning.py`.

### `queueing_model.py`
**What it does:** Models the backlog dynamics of a denial-appeals queue under different staffing and work-in-progress scenarios. Used for the capacity planning panel.
**How it works:** Discrete-time simulation of a M/G/c queue: claims arrive at rate λ (from denial rate × claim volume), are processed at rate μ (per-FTE throughput), and have a timeout (timely filing deadline). Simulates queue depth, wait time, and timeout loss rate over a 12-month horizon. Returns throughput and loss rate under current vs. improved staffing scenarios.
**Data in:** Denial rate and claim volume from the deal profile; staffing FTE count from analyst input or benchmark.
**Data out:** `QueueSimResult` for the capacity planning panel.

### `rcm_opportunity_scorer.py`
**What it does:** Scores the total RCM improvement opportunity for a deal as a dollar amount and as a percentile vs. the comparable peer set. Used in the workbench Overview tab headline KPI.
**How it works:** For each of the 7 bridge levers: computes the gap between the hospital's current metric and the peer P75 (achievable benchmark). Feeds the gap through the v1 bridge to get a dollar opportunity. Aggregates across levers. Returns total opportunity in $M and a percentile rank (e.g., "74th percentile opportunity vs. peers").
**Data in:** Current metrics from the `DealAnalysisPacket` profile; peer P75 benchmarks from `comparable_finder.py`; v1 bridge from `pe/rcm_ebitda_bridge.py`.
**Data out:** `OpportunityScore` for the workbench Overview KPI panel.

### `rcm_performance_predictor.py`
**What it does:** Predicts a hospital's future RCM performance trajectory (12-month forward denial rate, AR days, collection rate) using historical trend data combined with industry benchmarks.
**How it works:** Fits a Holt-Winters model to historical quarterly performance data, adjusted toward the benchmark mean via shrinkage (stronger shrinkage when historical data is sparse). Returns 12-month forward forecasts with 80% prediction intervals.
**Data in:** Historical quarterly snapshots from `deals/deal_sim_inputs.py`; benchmark trends from `hospital_benchmarks`.
**Data out:** 12-month forward metric forecasts for the deal monitoring view.

### `realization_predictor.py`
**What it does:** Predicts the likely realization rate for each RCM initiative based on deal characteristics and historical fund experience.
**How it works:** Logistic regression over features: deal vertical, management quality rating (analyst-entered), union status, IT system age, and comparable fund playbook realization rates. Returns per-initiative predicted realization rate (0–1) and a 3-factor rationale. Used by `pressure_test.py` to set realistic achievement expectations.
**Data in:** Deal characteristics from the profile; fund playbook realization data from `ml/fund_learning.py`.
**Data out:** Per-initiative realization rate predictions for `pressure_test.py`.

### `survival_analysis.py`
**What it does:** Estimates the probability distribution of hold period length and exit timing using Kaplan-Meier survival analysis on the public deals corpus.
**How it works:** Fits a Kaplan-Meier estimator to hold-year data from `data_public/deals_corpus.py`, stratified by subsector and sponsor size. Returns the survival function S(t) = P(hold > t) and the conditional hazard h(t) = P(exit at t | held to t). Used by `pe_math.py` for hold-period-weighted IRR calculations.
**Data in:** Public deals corpus hold years from `data_public/deals_corpus.py`; deal subsector and sponsor size.
**Data out:** Kaplan-Meier survival and hazard functions for hold-period analysis.

---

---

## Predictor expansion cycle (Apr 2026)

Thirteen ML surfaces shipped in the most recent autonomous-loop cycle. All follow the same discipline as the existing modules: closed-form Ridge in numpy, conformal-style intervals via residual quantiles, leave-one-cohort-out CV where the data permits, hard sanity-range clamps on every output, `provenance` flag to distinguish synthetic-priors fits from real-cohort calibration.

### `denial_rate_predictor.py` — Hospital denial-rate model

**What it does:** Predicts a hospital's gross denial rate from 13 structural features (bed count, payer mix, occupancy, net-to-gross, operating margin, case-mix proxy, Care Compare star rating, readmission rate, mortality rate, HCAHPS, MA penetration, state RCM factor). Sanity range `(0.0, 0.40)`.

**How it works:** Closed-form Ridge `(XᵀX + αI)⁻¹Xᵀy`, α=1.0, k-fold CV for R²/MAE, residual-quantile 90% bands, top-3 feature contributions per prediction.

### `days_in_ar_predictor.py` — A/R days predictor

**What it does:** Predicts days-in-AR from the same feature schema as the denial-rate model plus throughput indicators. Used for pre-deal benchmarking against HFMA bands.

**How it works:** Adds **leave-one-cohort-out CV** (cohorts: cohort_id, region, bed-band) so MAE is reported against held-out *cohorts*, not just held-out hospitals. This catches systematic bias the i.i.d. CV misses.

### `collection_rate_predictor.py` — Net collection rate

**What it does:** Predicts net collection rate (cash collected / NPSR). Headline metric for RCM-thesis defensibility.

**How it works:** Standard Ridge + conformal; ships a global feature-importance summary across the calibration set so users see which structural features matter most before drilling into a single deal.

### `forward_distress_predictor.py` — 12–24mo distress probability

**What it does:** Probability a hospital breaches a covenant or files for protection within a forward 12-24 month window. Calibrated against the named-failure case library (Steward, Cano, Envision, etc.).

**How it works:** Logistic regression (closed-form numpy via Newton-IRLS), calibrated by Platt scaling. Top risk drivers per hospital. Distress band labels (`stable / watch / elevated / critical`).

### `improvement_potential.py` — Peer-benchmark gap → $ uplift

**What it does:** For each of the 7 v1 bridge levers, computes the gap between the hospital's current metric and the peer P75 (achievable benchmark) and dollarizes it through the bridge to estimate total RCM improvement opportunity in $M.

**How it works:** Wraps `comparable_finder` + `pe/rcm_ebitda_bridge.py`. Returns per-lever opportunity, total $, and a percentile rank vs the peer pool. Does not double-count cross-lever interactions (caps total at 80% of additive sum).

### `contract_strength.py` — Payer contract strength estimator

**What it does:** Estimates how favorable a hospital's payer contracts are versus market based on Transparency-in-Coverage MRF data + peer comp. Bands: `very_weak / weak / market / strong / very_strong` with thresholds at 0.85 / 0.95 / 1.05 / 1.20.

**How it works:** For each (payer, CPT) cell with sufficient peer coverage, computes the hospital's negotiated rate as a multiple of the peer-median rate. Aggregates weighted by hospital's volume mix. Top-K best/worst contracts surfaced for negotiation prep.

### `service_line_profitability.py` — Service-line P&L + cross-subsidy

**What it does:** Per-service-line contribution margin from DRG-level utilization × charge-to-payment × cost allocation. Surfaces **cross-subsidies** (loss-leader lines kept for strategic reasons) versus genuine value-destroyers.

**How it works:** Reads `cms_utilization` DRG output + HCRIS cost-allocation. Three-tier classification: `profit_center`, `subsidy_candidate`, `drag`. The drag list flows into the `improvement_potential` consideration.

### `labor_efficiency.py` — Labor-efficiency model + scenarios

**What it does:** FTE-per-adjusted-discharge, productivity vs peer P50/P75, and an EBITDA-impact scenario for closing the labor-efficiency gap by N percentage points.

**How it works:** Ridge over wage-index, MA mix, teaching status, beds. Outputs current FTE/AD, peer-implied target, dollar impact at 25%/50%/75% gap closure. Hard-clamps target FTE at 80% of current to avoid recommending unrealistic cuts.

### `volume_trend_forecaster.py` — Service-line volume forecast

**What it does:** 8-quarter forward forecast of DRG-grouped discharge volume with a **trajectory classifier** (`growing`, `stable`, `declining`, `volatile`). Drives the volume-trend assumption in Deal MC.

**How it works:** Auto-selects between Holt-Winters (≥8 quarters of history), linear OLS (≥6), and weighted-recent (<6). Method label is exposed in the output; never silent.

### `regime_detection.py` — PELT changepoint analysis

**What it does:** Detects regime shifts in a metric's quarterly history (e.g., "denial rate jumped at 2024Q3 — is that a real regime change or noise?"). Used to validate forecaster assumptions.

**How it works:** Pure-numpy PELT (Pruned Exact Linear Time) changepoint algorithm with a quadratic-loss cost function. Returns changepoint indices + per-segment summary stats. No scipy.

### `ensemble_methods.py` — Bag / blend / stack

**What it does:** Three real ensemble methods for combining weak individual predictors: **bagging** (resample-and-average for variance reduction), **blending** (validation-set linear combination), **stacking** (out-of-fold meta-learner). Used when no single base learner crosses the R²≥0.30 threshold.

**How it works:** All three are closed-form numpy. Returns the combined prediction plus per-base-learner weights for interpretability.

### `feature_importance.py` — Unified feature importance

**What it does:** Computes feature importance for any of the Ridge predictors using a unified API so the UI can render a consistent feature-importance chart across models.

**How it works:** Three options: standardized-coefficient magnitude (default for Ridge), permutation importance (held-out MAE delta when feature is permuted), and SHAP-like contributions (linear models only, single-deal explanation). Pairs with `ui/feature_importance_viz.py` for the SVG rendering at `/models/importance`.

### `geographic_clustering.py` — Geographic clusters + hotspots

**What it does:** Clusters hospitals by geography (CBSA → state → region) crossed with structural features, then identifies "hotspots" — areas where a metric (e.g., denial rate, distress probability) is materially worse than national.

**How it works:** Hierarchical k-means on the 6-comparable-dimension feature space, weighted by geographic adjacency. Hotspot detection via z-score against national distribution per metric. Feeds the deal-sourcing screener with "look here" geographic prompts.

### `payer_mix_cascade.py` — Payer mix shift → downstream impact

**What it does:** Simulates the full downstream impact of a payer-mix shift (e.g., "what if commercial drops 5pp and MA picks up 5pp over 36 months?") through denial rate, AR days, contract strength, collection rate, EBITDA, and bridge feasibility — one cascade, four canonical paths.

**How it works:** Wires the four canonical PE-intelligence cascades from `pe_intelligence/` into a single API. Returns time-stepped trajectories, per-step provenance, and a "thesis-still-works" verdict at the end.

### `model_quality.py` + `/models/quality` — Backtest harness

**What it does:** Unified backtesting harness that runs every Ridge predictor through both i.i.d. CV and leave-one-cohort-out CV, computes empirical CI coverage, and renders a model-quality scoreboard at `/models/quality`. Cached via `infra/cache.ttl_cache` for >100,000× speedup on repeat loads.

**How it works:** Iterates predictors registered in `MODEL_QUALITY_REGISTRY`, runs CV, computes MAE/MAPE/R²/coverage, renders a power-table with provenance badges (`real-cohort-N` vs `synthetic-priors`).

---

## Key Concepts

- **No sklearn dependency**: Ridge is one line of numpy; conformal prediction is ~50 lines. The stdlib+numpy invariant is preserved throughout.
- **Conformal coverage guarantee**: 90% intervals that contain the truth 90% of the time with no distributional assumptions, calibrated per-metric.
- **Graceful fallback ladder**: When there aren't enough comparables for Ridge, the system falls back to weighted median, then to benchmark percentiles — always returning a result with an honest grade.
- **Dollar metrics are never predicted**: Net revenue, EBITDA, and operating expenses are always analyst inputs. The model never fabricates revenue from peer medians.
- **Sanity-range clamps**: Every numeric output is clamped to a documented physical range (e.g., denial rate ∈ [0.0, 0.40]) so a misfit model can't return a -200% collection rate.
- **Provenance flag**: Every predictor carries `provenance: "synthetic-priors"` until calibrated against ≥30 real closed-deal labels, at which point it flips to `"real-cohort-N"`. The flag is rendered in the UI.
