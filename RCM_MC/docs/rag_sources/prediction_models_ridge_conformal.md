# Prediction Models: Ridge + Conformal Intervals

How PEdesk predicts hospital KPIs/financials and attaches honest uncertainty.
Explains the backend so the Guide can answer "how are predictions made / what
does the confidence interval mean / how reliable".

## Point predictions (`rcm_mc/ml/ridge_predictor.py`, `rcm_mc/ml/margin_predictor.py`)
- Ridge regression (L2-regularized linear model) fit on real HCRIS features.
  Ridge is used over plain OLS to stay stable when features are correlated.
- Coefficients are interpretable; the page-level regression surface
  (/portfolio/regression) additionally guards against multicollinearity (VIF +
  Belsley condition number + structural-family de-duplication) so a high R²
  built on collinear predictors is never presented as sound.

## Uncertainty (`rcm_mc/ml/conformal.py`)
- Split conformal prediction: the model is fit on a training split and the
  prediction interval is the (finite-sample) quantile of |residual| on a
  DISJOINT calibration split — so the 90% interval genuinely targets 90%
  coverage, distribution-free. Calibrating on in-sample residuals (which would
  understate the interval) is specifically avoided.
- Each prediction also carries a confidence tier (graded label) and a data-
  completeness signal.

## How to read it
- The interval is the model's honest spread; a wide band means thin/uncertain
  inputs. Coverage holds only if the new point is exchangeable with the
  calibration set.
- These are in-sample/cross-sectional explanatory models over public data —
  use for hypothesis generation and benchmarking, not as a guaranteed forecast.

## Caveats
- Model estimates carry model error; confidence depends on input-data quality.
  The weighted-ridge variant is gated OFF pending validation.
