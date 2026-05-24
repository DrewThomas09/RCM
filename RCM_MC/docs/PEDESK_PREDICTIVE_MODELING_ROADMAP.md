# PEdesk predictive-modeling roadmap & boundaries

The modeling techniques PEdesk may use, the assumptions each requires, and
the hard line between **describe / predict** and **claim causality**. The
Guide must be able to explain each plainly and state when it does NOT apply.

> Prediction is not causation. CMS public data is a Medicare-certified
> provider slice, not commercial performance. Models inform diligence
> questions; they do not replace target documents or confirmatory diligence.

## Model families

### Linear regression (OLS)
```
y_i = beta_0 + beta_1 x_{i1} + ... + beta_p x_{ip} + epsilon_i
beta_hat = (X'X)^(-1) X'y          # only if X'X is invertible
```
Use for interpretable association. Check residuals, multicollinearity,
heteroskedasticity. Coefficients are associational, not causal.

### Regularized regression
```
Ridge:        min_beta  sum_i (y_i - X_i beta)^2 + lambda * sum_j beta_j^2
Lasso:        min_beta  sum_i (y_i - X_i beta)^2 + lambda * sum_j |beta_j|
Elastic Net:  min_beta  sum_i (y_i - X_i beta)^2
                        + lambda * [ alpha * sum_j |beta_j|
                                     + (1-alpha)/2 * sum_j beta_j^2 ]
```
Use when p is large or predictors are correlated. Tune `lambda` (and `alpha`)
by cross-validation; report the grid and the chosen value.

### Logistic regression (binary outcome)
```
Pr(y_i = 1 | X_i) = 1 / (1 + exp(-(beta_0 + X_i beta)))
```
Report ROC-AUC, PR-AUC, calibration, and baseline prevalence.

### Fixed effects / panel
```
y_it = alpha_i + gamma_t + X_it beta + epsilon_it
```
Use only with repeated observations per provider over time; absorbs
time-invariant provider effects and common time shocks.

### Multilevel / hierarchical
```
y_ij = beta_0 + X_ij beta + u_j + epsilon_ij ,   u_j ~ N(0, sigma_u^2)
```
Use for providers nested in state/county/sector — partial pooling stabilizes
small groups.

### Survival / hazard
```
h_i(t) = h_0(t) * exp(X_i beta)
```
Use **only** if genuine time-to-event labels exist (e.g. time to closure,
exit). Do not fabricate event times.

## Validation requirements (non-negotiable)

- Regression: out-of-sample R², MAE/RMSE vs a baseline, residual diagnostics.
- Classification: ROC-AUC, PR-AUC, calibration, confusion matrix at threshold,
  baseline-prevalence comparison.
- Uncertainty: CIs where assumptions hold; bootstrap for robustness;
  prediction intervals for forecasts; Monte Carlo for scenario sensitivity.

## Bias / leakage checklist

selection · omitted-variable · survivorship · lookahead/leakage ·
small-sample overfitting · missing-not-at-random · state/regional confounding.

## Boundaries — what a model output may and may not say

- **May:** "providers with X tend to have Y in this sample (associational,
  out-of-sample R²=…)."
- **May:** "predicted Z with interval […]; validated on held-out data."
- **May NOT:** "X causes Y." (no causal identification here)
- **May NOT:** imply commercial revenue/performance from Medicare data.
- **May NOT:** present a thin-sample or single-outlier result as a signal.
- **May NOT:** state an investment recommendation.

A predictive result becomes **investable evidence** only when it clears the
threshold in `PEDESK_INVESTABLE_EVIDENCE_FRAMEWORK.md` — including
out-of-sample validation.
