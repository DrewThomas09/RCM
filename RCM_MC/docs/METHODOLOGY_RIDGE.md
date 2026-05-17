# Ridge Predictor Methodology (2026-05-17 update)

This document explains what the 2026-05-17 methodology update
changed in the per-cohort ridge regression predictor and how to
read the new diagnostic chips and α-disclosure annotations.
Written for partners and analysts using the analysis workbench,
model validation dashboard, and packet exports.

## Summary

Before this update, every ridge fit used a fixed penalty `α = 1.0`.
That constant was a demo-grade default chosen without per-cohort
tuning.

After this update, every ridge fit selects its own α from a
25-value logarithmic grid (`10⁻³` through `10³`) via leave-one-out
cross-validation. The α that minimizes out-of-sample LOO MSE on
the specific cohort wins. Cross-validated R² for most metrics
will shift upward by ~5–15% as a consequence — this is
methodological improvement, not a re-baselining of how R² is
computed. Categorical signals (quality bars, reliability grades,
validation letter grades) have had their thresholds recalibrated
to preserve the partner-facing label distribution across the
methodology change; a metric whose quality was "high" before this
update will mostly remain "high" after, even though its absolute R²
is now higher.

## The α-search

Each per-cohort fit picks the α value that minimizes leave-one-out
MSE across a 25-value logarithmic search grid spanning five
orders of magnitude (0.001 → 1000). The search is computed in
O(N·p²) per α via the hat-matrix LOO shortcut
(Allen 1974; Hastie, Tibshirani & Friedman ESL §7.10 eq 7.65).

The LOO shortcut computes residuals using the full-data
standardization (feature means and standard deviations derived
from all N rows). This differs slightly from a naive LOO that
re-standardizes per fold using only the N-1 retained rows —
typically by less than ~5% on small cohorts, with the gap
shrinking as N grows. The shortcut is preferred because it
preserves the cohort-level feature scaling that the production
prediction itself uses, so the LOO score reflects out-of-sample
behavior at the same scaling the partner sees.

The selected α is displayed inline with the quality bar on the
analysis workbench (`α=0.43`) so the partner can see which cohort
got which regularization. Hover the α label for the one-line
methodology explanation.

A guardrail fires when RidgeCV picks the grid's lowest or
highest α value AND y has non-trivial variance — this signals
the search grid was too narrow for the cohort. Renders as the
`ALPHA_AT_BOUNDARY` chip. Near-constant y legitimately picks the
maximum α (over-regularize toward the cohort mean) and correctly
does NOT fire the chip.

## Diagnostics — five orthogonal checks

Every successful ridge fit is now diagnostically audited against
five checks. Each catches a partner-relevant failure mode that
the others miss:

### 1. Max VIF > 10 → `MULTICOLLINEAR`
Features are linearly redundant; top-driver attribution may be
misleading. Threshold from Kutner et al. (2005) *Applied Linear
Statistical Models* and Hair et al. (2010). Ridge regularization
dampens VIF inflation, so VIF > 10 on a ridge fit is a stronger
signal than on plain OLS.

### 2. Top Cook's D > 4/N → `INFLUENTIAL_OUTLIER`
One peer hospital exerts outsized influence on the fit. Threshold
from Bollen & Jackman (1985). The 4/N convention is small-N-aware
— at N=15 the threshold is 0.27, at N=50 it's 0.08, so it
auto-adjusts for cohort size.

### 3. BP p-value < 0.05 → `HETEROSCEDASTIC`
Residual variance depends on feature values (Breusch & Pagan
1979). The confidence interval is sized correctly on average but
may be too tight or too loose at this specific prediction point.
Computed without scipy via the Wilson-Hilferty chi-squared
survival approximation (Johnson, Kotz & Balakrishnan 1994 vol 1
§17.6); verified to ±0.01 p-value precision against scipy's
exact survival function in `tests/test_b1_bp_precision.py`.

### 4. Max leverage > 2p/N → `HIGH_LEVERAGE`
One peer hospital sits at the edge of the cohort's feature
space. Threshold from Belsley, Kuh & Welsch (1980). Distinct
from Cook's D — leverage is potential influence (geometric
distance in X-space); Cook's D is realized influence (leverage ×
residual). A high-leverage point with a small residual fires
this chip but not Cook's D.

### 5. |t-slope| > 2 → `NONLINEAR_PATTERN`
Residuals show systematic structure when plotted against fitted
values — the linear ridge is missing curvature. Threshold ~95th
percentile of Student's t for N > 15.

## Multi-diagnostic composition

When two or more diagnostics fire on the same fit, the chip
becomes a generic `DIAGNOSTIC_SUSPECT` ("multiple diagnostic
flags") with the specific reasons listed in the tooltip,
ordered tier-severity first then within-tier signal strength.
A multi-diagnostic firing is a genuinely different signal than
any one diagnostic firing — the conjunction suggests the cohort
or feature set isn't well-suited to ridge regression here, not
just borderline-suspect in one dimension.

When only one diagnostic fires, the chip carries that specific
diagnostic's name (preserves headline-scan UX for the common
single-issue case).

## R²-Negative + Cook's D verification

If LOO R² is negative AND Cook's D fires, the predictor
**actually recomputes** LOO R² with the high-Cook's-D row
removed, rather than assuming the outlier caused the negative
R². If R² recovers above zero, the chip is `INFLUENTIAL_OUTLIER`
(hypothesis verified). If R² stays negative, the chip is
`DIAGNOSTIC_SUSPECT` with both reasons in the tooltip (both
issues are real and the partner sees both). Costs one extra
LOO fit in the rare double-fire case; partner-defensibility
improves materially.

## Methodology versioning

Every prediction recorded in the prediction ledger now carries
a `methodology_version` tag: `"pre-b1"` for predictions made
before this deploy, `"b1-tuned-alpha"` for predictions made
under the per-cohort RidgeCV path. The model validation
dashboard defaults to showing only `b1-tuned-alpha` predictions;
a toggle includes the pre-2026-05 legacy rows for historical
comparison. Each threshold-driven categorical signal (quality
label, reliability grade, validation letter grade, validation
color cell) routes through `rcm_mc/analysis/thresholds.py`,
which keys on the row's methodology version.

## Threshold recalibration

The categorical thresholds shifted upward by ~0.05–0.10 R² to
preserve the partner-facing label distribution under the new
methodology. Initial values are simulation-informed placeholders
(typical RidgeCV LOO vs fixed-α R² shift on small-N regression
problems per Hastie/Tibshirani 2008 simulation results). The
exact distribution-preserving recalibration runs after one week
of production observation; updated thresholds replace the
placeholders in a follow-up PR.

Why distribution-preserving recalibration over absolute
threshold preservation: keeping `r² ≥ 0.5 = "high"` would
inflate the "high" share by ~30% (since LOO R² shifts upward
under tuned α), making the categorical signal less informative
to partners. The shift-with-the-distribution approach keeps
the *categorical* signal stable while the *numerical* R² value
reflects the methodological improvement.

## What didn't change

- LOO procedure itself (still leave-one-out, still over the
  full X/y, not the train split).
- Conformal coverage targets (still 90% by default).
- Conformal interval construction.
- Method-selection logic (Ridge → weighted_median →
  benchmark_fallback fallback ladder).
- The seven pre-existing chip variants
  (`pinv_fallback`, `ci_unstable`, `r2_negative`,
  `insufficient_comparables`, `target_features_missing`,
  `no_benchmark`, `fit_exception`).

## Audit trail

Each prediction's audit row in the ledger now records:
- `methodology_version`: `pre-b1` or `b1-tuned-alpha`
- `cohort_alpha`: the RidgeCV-selected α (NULL for non-ridge)
- All seven pre-existing fields (predicted_value, ci_low/high,
  method, model_r2, etc.)

Packet-level provenance (analysis_runs) carries the per-metric
`PredictedMetric.cohort_alpha` and `contributing_sources` so
IC review can trace any chip back to its source diagnostics.

## References

- Allen, D. M. (1974). The relationship between variable selection
  and data augmentation and a method for prediction. *Technometrics*
  16(1): 125–127. (LOO shortcut for ridge.)
- Belsley, D. A., Kuh, E., & Welsch, R. E. (1980). *Regression
  Diagnostics: Identifying Influential Data and Sources of
  Collinearity.* Wiley. (Leverage threshold 2p/N.)
- Bollen, K. A., & Jackman, R. W. (1985). Regression diagnostics:
  An expository treatment of outliers and influential cases.
  *Sociological Methods & Research* 13(4): 510–542. (Cook's D
  threshold 4/N.)
- Breusch, T. S., & Pagan, A. R. (1979). A simple test for
  heteroscedasticity and random coefficient variation.
  *Econometrica* 47: 1287–1294.
- Hair, J. F. et al. (2010). *Multivariate Data Analysis* (7th ed.).
  Pearson. (VIF threshold 10.)
- Hastie, T., Tibshirani, R., & Friedman, J. (2008). *The Elements
  of Statistical Learning* (2nd ed.). Springer. (§7.10 eq 7.65
  for the ridge LOO shortcut; α-tuning impact on R² shift.)
- Johnson, N. L., Kotz, S., & Balakrishnan, N. (1994). *Continuous
  Univariate Distributions* (vol 1, 2nd ed.). Wiley. (§17.6
  Wilson-Hilferty approximation.)
- Kutner, M. H., Nachtsheim, C. J., Neter, J., & Li, W. (2005).
  *Applied Linear Statistical Models* (5th ed.). McGraw-Hill.
  (VIF threshold 10.)
