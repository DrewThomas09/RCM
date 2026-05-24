# PEdesk investable-evidence framework

How PEdesk decides when a public-data signal is strong enough to present as
**investable evidence** versus when it must be labeled context, proxy, or
noise. The Guide is expected to explain every concept here in plain terms.

Guiding rule: **a number is not a conclusion.** CMS public data describes
Medicare-certified providers; it is not commercial revenue, not market
share, and not causal. Every signal carries directionality, sample size,
and caveats.

## Core statistics (with guardrails)

### Peer percentile
For provider `i` in peer set `P`:

```
percentile_i = 100 * rank_i / |P|
```

- Rank ascending by value for **higher-is-better** metrics; invert for
  **lower-is-better** metrics. **Always state the directionality.**
- A percentile is *peer deviation*, not an investment conclusion.

### Z-score
```
z_i = (x_i - mean(x_P)) / sd(x_P)
```

- **Require n ≥ 5.** With fewer, show "insufficient peer sample."
- If `sd = 0` (no variation), the z-score is undefined → show "insufficient
  variation," not a fabricated 0.
- A z-score is peer deviation, **not** an investment call.

### Concentration (HHI)
For category shares `s_k` (decimals summing to ~1):

```
HHI = sum_k s_k^2
```

- When shares are provider counts by ownership type / subsector / geography,
  call it **ownership/composition concentration** — **not market share**.
  Market share requires a true market denominator (volume / revenue /
  patients), which CMS provider files do not provide.
- 0 → perfectly diffuse; 1 → single category. Also report CR3/CR5 if useful.

### Quality composite
```
score_i = sum_j w_j * z_{ij}
```

- Show the raw components and the **documented weights**.
- Show missingness; **do not compute** if too many components are missing.
- Never hide a component's source limitation inside a composite.

## Prediction validation (when a model is used)

- **Regression:** train/test split or cross-validation; a baseline model;
  out-of-sample R²; MAE / RMSE; residual checks.
- **Classification:** ROC-AUC, PR-AUC, calibration, confusion matrix at the
  chosen threshold, and comparison to baseline prevalence.
- **Uncertainty:** confidence intervals where assumptions hold; bootstrap
  intervals for robustness; prediction intervals when forecasting; Monte
  Carlo sensitivity for scenarios.

## Bias & limitation checks (always run)

Selection bias · omitted-variable bias · survivorship bias · lookahead /
leakage · small-sample overfitting · missing-not-at-random · state/regional
confounding.

## Investable-evidence threshold

A signal may be presented as **investable evidence** only if it:

1. has an adequate sample size,
2. has an economically interpretable direction,
3. is stable across reasonable peer definitions,
4. is robust across state/time slices when available,
5. is **not** driven by a single outlier,
6. carries visible caveats, and
7. maps to a concrete diligence question or management action,
8. passes out-of-sample validation **if** it is predictive.

If any condition fails, present it as **context / proxy / hypothesis**, not
evidence — and say which condition failed.

## What PEdesk must never claim

- Commercial revenue, unless a dataset actually contains revenue.
- Market share, unless the denominator is true market volume/revenue/patients.
- Causality from a prediction or comparison.
- "Fully covered," when a vertical only has provider-supply proxy data.
- An investment recommendation.
- Private-pay visibility from CMS public datasets.

See also: `PEDESK_PREDICTIVE_MODELING_ROADMAP.md`,
`rag_sources/investable_evidence.md`,
`rag_sources/predictive_modeling_boundaries.md`.
