# ML

Machine learning layer for metric prediction, anomaly detection, backtesting, and forecasting. All models are numpy-only (no sklearn/scipy) -- Ridge regression is implemented from the closed-form solution, and conformal prediction provides distribution-free uncertainty intervals.

| File | Purpose |
|------|---------|
| `rcm_predictor.py` | Ridge-regression engine that fills missing RCM metrics using comparable hospitals; falls back to weighted median or benchmark |
| `ridge_predictor.py` | Conformal-calibrated Ridge predictor with size-gated fallback ladder (Ridge >= 15 comps, median >= 5, benchmark < 5) |
| `conformal.py` | Split conformal prediction: distribution-free 90% coverage intervals with no normality assumption |
| `ensemble_predictor.py` | Auto-selecting ensemble (Ridge, k-NN, weighted median) that picks the best model per metric via held-out MAE |
| `comparable_finder.py` | Weighted six-dimension similarity scoring (bed count, region, payer mix, system, teaching, urban/rural) for peer hospitals |
| `feature_engineering.py` | Interaction terms, z-score normalization against peer medians, and >2.5-sigma outlier detection |
| `anomaly_detector.py` | Three-strategy anomaly detection: statistical z-score, causal consistency via ontology edges, and temporal discontinuity |
| `backtester.py` | Hold-out backtesting with per-hospital and cohort-wide modes; outputs a letter grade (A-F) per metric |
| `temporal_forecaster.py` | Time-series trend detection with auto-selected method: linear OLS (>=6 periods), Holt-Winters (>=8 + seasonality), or weighted-recent |
| `portfolio_learning.py` | Cross-deal learning: detects systematic prediction bias across the fund's history and shrinks new predictions accordingly |

## Key Concepts

- **No sklearn dependency**: Ridge is one line of numpy; conformal prediction is ~50 lines. The stdlib+numpy invariant is preserved.
- **Conformal coverage guarantee**: 90% intervals that contain the truth 90% of the time with no distributional assumptions, calibrated per-metric.
- **Graceful fallback ladder**: When there aren't enough comparables for Ridge, the system falls back to weighted median, then to benchmark percentiles.
