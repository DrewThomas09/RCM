# RAG source card — Predictive-modeling boundaries

Applies to: any page or answer that uses a model (regression, classification,
panel/multilevel, survival) over CMS or corpus data. Full detail in
`PEDESK_PREDICTIVE_MODELING_ROADMAP.md`.

Sources: vendored CMS public datasets + the deal corpus (local; no runtime
network). Models are tools for diligence questions, not substitutes for
confirmatory diligence.

Methods & formulas:
- OLS: `y = Xbeta + eps`, `beta_hat = (X'X)^(-1)X'y` (if invertible).
- Ridge / Lasso / Elastic Net (regularized; tune lambda/alpha by CV).
- Logistic: `Pr(y=1|X) = 1/(1+exp(-(b0 + Xb)))`.
- Fixed effects: `y_it = alpha_i + gamma_t + X_it beta + eps`.
- Multilevel: `y_ij = b0 + X_ij beta + u_j + eps`, `u_j ~ N(0, sigma_u^2)`.
- Survival/hazard: `h_i(t) = h_0(t) exp(X_i beta)` (only with real event times).

Validation: regression → OOS R², MAE/RMSE vs baseline, residuals.
Classification → ROC-AUC, PR-AUC, calibration, confusion matrix, baseline
prevalence. Uncertainty → CIs / bootstrap / prediction intervals / Monte
Carlo sensitivity.

How to use: state associations and validated predictions with their
uncertainty; use them to frame management questions, never as conclusions.

Limitations / boundaries:
- Prediction ≠ causation; coefficients here are associational.
- CMS data is a Medicare slice — not commercial performance/revenue.
- Bias checks required: selection, omitted-variable, survivorship,
  lookahead/leakage, small-sample overfitting, missing-not-at-random,
  state/regional confounding.
- No model output is an investment recommendation.

Suggested questions:
- "Is this association or causation?"
- "Was this validated out-of-sample, and how?"
- "What biases could be driving this result?"
- "What's the uncertainty around this prediction?"
- "Does this hold up across states/time, or is it one-sample?"
