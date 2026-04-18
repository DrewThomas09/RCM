# ML

Condensed public-facing summary. Deep reference with full file-by-
file breakdown: [`RCM_MC/docs/README_LAYER_ML.md`](../RCM_MC/docs/README_LAYER_ML.md).

## Two jobs

1. **Find comparables.** Given a target hospital, rank a pool of
   peer hospitals by weighted similarity.
2. **Predict missing metrics.** Use those comparables to predict
   metrics the partner didn't supply, with honest uncertainty
   intervals and a reliability grade.

**No `sklearn`.** Ridge regression is one closed-form numpy block
(~300 lines); split conformal prediction is ~230 lines of numpy.
The dependency surface stays at `numpy` + `pandas`.

## The files

| File | Purpose |
|---|---|
| [`comparable_finder.py`](../RCM_MC/rcm_mc/ml/comparable_finder.py) | Weighted 6-dimension similarity scoring |
| [`ridge_predictor.py`](../RCM_MC/rcm_mc/ml/ridge_predictor.py) | Conformal-calibrated Ridge with size-gated fallback |
| [`conformal.py`](../RCM_MC/rcm_mc/ml/conformal.py) | Split conformal — distribution-free 90% CIs |
| [`ensemble_predictor.py`](../RCM_MC/rcm_mc/ml/ensemble_predictor.py) | Ridge / kNN / weighted-median picker |
| [`feature_engineering.py`](../RCM_MC/rcm_mc/ml/feature_engineering.py) | Interaction terms + z-score normalization |
| [`anomaly_detector.py`](../RCM_MC/rcm_mc/ml/anomaly_detector.py) | Three strategies: statistical / causal / temporal |
| [`backtester.py`](../RCM_MC/rcm_mc/ml/backtester.py) | Hold-out + coverage backtests; letter grade per metric |
| [`temporal_forecaster.py`](../RCM_MC/rcm_mc/ml/temporal_forecaster.py) | Linear OLS / Holt-Winters / weighted-recent |
| [`portfolio_learning.py`](../RCM_MC/rcm_mc/ml/portfolio_learning.py) | Cross-deal bias shrinkage |
| [`rcm_predictor.py`](../RCM_MC/rcm_mc/ml/rcm_predictor.py) | Legacy predictor (pre-conformal); kept for backtester + CLI `predict` |
| [`margin_predictor.py`](../RCM_MC/rcm_mc/ml/margin_predictor.py) | EBITDA-margin prediction from peer medians |
| [`survival_analysis.py`](../RCM_MC/rcm_mc/ml/survival_analysis.py) | Hazard-rate modelling for hold-period exits |
| [`bayesian_calibration.py`](../RCM_MC/rcm_mc/ml/bayesian_calibration.py) | Prior-shrinkage calibration for thin-cohort metrics |
| [`efficiency_frontier.py`](../RCM_MC/rcm_mc/ml/efficiency_frontier.py) | Per-metric efficient-frontier construction |
| [`queueing_model.py`](../RCM_MC/rcm_mc/ml/queueing_model.py) | Queueing-theory capacity model |
| [`rcm_opportunity_scorer.py`](../RCM_MC/rcm_mc/ml/rcm_opportunity_scorer.py) | Deal-level RCM-opportunity signal composite |
| [`distress_predictor.py`](../RCM_MC/rcm_mc/ml/distress_predictor.py) | Financial-distress signal over the benchmark table |
| [`hospital_clustering.py`](../RCM_MC/rcm_mc/ml/hospital_clustering.py) | k-means-style segmentation over HCRIS features |
| [`investability_scorer.py`](../RCM_MC/rcm_mc/ml/investability_scorer.py) | Investability composite for sourcing |
| [`prediction_ledger.py`](../RCM_MC/rcm_mc/ml/prediction_ledger.py) | Append-only ledger of every prediction + truth (for recalibration) |
| [`realization_predictor.py`](../RCM_MC/rcm_mc/ml/realization_predictor.py) | Predicts exit realization vs plan |
| [`rcm_performance_predictor.py`](../RCM_MC/rcm_mc/ml/rcm_performance_predictor.py) | Per-lever attainment prediction based on comparables |
| [`fund_learning.py`](../RCM_MC/rcm_mc/ml/fund_learning.py) | Fund-level prediction bias learner |
| [`market_intelligence.py`](../RCM_MC/rcm_mc/ml/market_intelligence.py) | Market-level feature engineering (HHI, CON, etc.) |

## Comparable finder

[`comparable_finder.py`](../RCM_MC/rcm_mc/ml/comparable_finder.py).

Weights:

| Dimension | Weight | Similarity function |
|---|---|---|
| Bed count | 0.25 | $1 - \lvert a - b \rvert / \max(a, b)$ |
| Region | 0.20 | 1.0 match / 0.0 else |
| Payer mix | 0.25 | cosine on payer vectors |
| System affiliation | 0.10 | 1.0 match / 0.0 else |
| Teaching status | 0.10 | 1.0 match / 0.0 else |
| Urban / rural | 0.10 | 1.0 match / 0.0 else |

Missing dimension → contributes 0.5 (neutral), not NaN. Returns the
top-K peers with `similarity_score` and `similarity_components`
injected.

## Ridge + conformal

[`ridge_predictor.py`](../RCM_MC/rcm_mc/ml/ridge_predictor.py)
+ [`conformal.py`](../RCM_MC/rcm_mc/ml/conformal.py).

Size-gated fallback ladder:

| Cohort $n$ | Method | CI basis | Reliability grade |
|---|---|---|---|
| $n \geq 15$ | Ridge + split conformal (70/30 train/cal) | conformal quantile $q$ | A if $n \geq 30$, $R^2 \geq 0.60$; B if $n \geq 20$, $R^2 \geq 0.45$; C if $n \geq 15$, $R^2 \geq 0.25$; else D |
| $5 \leq n \leq 14$ | Similarity-weighted median + bootstrap (1,000 resamples) | symmetric percentile bounds | B if $n \geq 10$ else C |
| $n < 5$ | Benchmark P50 | P25–P75 as band | D always |

The **reliability grade** surfaces the dominant assumption. Partners
see "D: benchmark fallback, 0 peers" rather than pretending there's
cohort signal.

**Dollar-valued metrics are never predicted** — `net_revenue`,
`gross_revenue`, `current_ebitda`, `total_operating_expenses`. These
are partner inputs. The model never fabricates EBITDA from
comparable medians.

### Conformal prediction primer

For a fitted base model $\hat{f}$ and calibration set
$\{(x_j, y_j)\}_{j=1}^n$:

$$
R_j = \lvert y_j - \hat{f}(x_j) \rvert, \quad
q = R_{(\lceil (1-\alpha)(n+1) \rceil)}
$$

Then for any new exchangeable $x^*$:

$$
\Pr\bigl[\, y^* \in [\,\hat{f}(x^*) - q,\; \hat{f}(x^*) + q\,] \,\bigr] \geq 1 - \alpha
$$

No normality, no tail assumptions. Coverage is *exact* in
expectation over the exchangeability structure.

Empirical coverage on 1,000 simulated held-out samples: **85–96%
for a nominal 90% target**. Locked by
`tests/test_ridge_predictor.py::test_coverage_property_on_simulated_data`.

## Backtester

[`backtester.py`](../RCM_MC/rcm_mc/ml/backtester.py).

Two styles:

1. **Legacy LOO.** For each hospital: mask its metrics, predict
   from the rest, score MAE / R² / MAPE per metric. Emits
   `A` / `B` / `C` / `D` / `F` grade per metric.
2. **Prompt-5 conformal backtest.** Pick a hospital, hide
   `holdout_fraction` of its metrics, call `predict_missing_metrics`,
   score MAE / R² / **coverage rate**. Coverage is the critical
   signal — if 90% intervals cover < 85% of truth, conformal
   calibration is broken. Grade capped at C on coverage miss > 15pp.

## Feature engineering

[`feature_engineering.py`](../RCM_MC/rcm_mc/ml/feature_engineering.py).

Interaction terms that lift Ridge $R^2$ on held-out hospitals:

- `denial_to_collection_ratio`
- `ar_efficiency`
- `first_pass_gap`
- `avoidable_denial_burden`
- `payer_complexity_score` — weighted by typical payer denial
  difficulty:
  $0.4 \cdot \text{commercial\_pct} + 0.35 \cdot \text{medicaid\_pct}
  + 0.25 \cdot \text{MA\_pct}$
- `revenue_per_bed`

Z-scored against a pre-computed `{metric: {mean, std}}` reference.

## Anomaly detection

[`anomaly_detector.py`](../RCM_MC/rcm_mc/ml/anomaly_detector.py).

Three independent strategies:

1. **Statistical z-score.** Flag metrics > threshold σ from cohort
   mean (default threshold = 2.5σ).
2. **Causal consistency.** Walk the ontology's `MechanismEdge`
   graph. If parent metric is anomalous and child metric is not (or
   vice versa), flag the inconsistency.
3. **Temporal discontinuity.** Sharp single-period breaks (>3σ from
   prior trend) flagged.

## Temporal forecaster

[`temporal_forecaster.py`](../RCM_MC/rcm_mc/ml/temporal_forecaster.py).

Auto-selects by history length:

- ≥ 8 periods with seasonal signal → Holt-Winters.
- ≥ 6 periods → linear OLS.
- < 6 periods → weighted-recent average.

Returns the fitted trend + projection with confidence band.

## Known limitations

From [`RCM_MC/docs/README_LAYER_ML.md`](../RCM_MC/docs/README_LAYER_ML.md):

- **Feature importances are $\lvert$ z-scored coefficients $\rvert$**
  — a rough heuristic. Good enough for the UI tooltip; not
  defensible for IC-level attribution. SHAP or similar is a
  follow-up.
- **Cohort construction is static.** `find_comparables` picks top-K
  by similarity without cross-validating on prediction quality.
- **No temporal structure in the cross-sectional Ridge.** The
  temporal forecaster lives separately.
- **Conformal assumes exchangeability.** If the target hospital is
  fundamentally different from the cohort (e.g., a critical-access
  hospital in a 400-bed cohort), the 90% coverage guarantee is
  lost. No automatic detection yet.
- **Single predictor per metric.** No model stacking beyond the
  ensemble picker.
