# Quant Stack Methods (Bayesian / DEA / Queueing / Survival)

The statistical engines behind the Quant Lab and several analytic surfaces,
each stated honestly so the Guide can explain "what method is this / how
reliable". All numpy-only (no scipy); the normal CDF uses math.erfc.

## Bayesian KPI calibration (`rcm_mc/ml/bayesian_calibration.py`)
- Rate metrics (denial / collection / clean-claim): a real Beta-Binomial
  conjugate posterior. Thin data shrinks toward the peer-group prior; rich data
  converges to the observed rate. The 90% credible interval is the Beta
  posterior's own variance.
- Continuous metrics (AR days, cost-to-collect): a Normal-Normal conjugate mean
  update; the dispersion is read from the spread of the hospital-type priors,
  not a magic constant.
- Read: a "prior_only"/"weak" estimate is shrunk toward peers — the wide
  interval is intentional, not a measured value.

## DEA efficiency frontier (`rcm_mc/ml/efficiency_frontier.py`)
- Output-oriented data-envelopment analysis; scores each provider 0–1 against
  the efficient frontier of peers (inputs → outputs).

## Queueing (`rcm_mc/ml/queueing_model.py`)
- M/M/c (Erlang-C) wait-time / SLA math applied to RCM operations.

## Survival / margin runway (`rcm_mc/ml/survival_analysis.py`)
- NOT Kaplan-Meier / Cox (there is no per-hospital time-to-event/censoring
  data). It fits operating margin vs. year by OLS on the provider's HCRIS
  history and reports P(margin > 0) at horizon t as the normal CDF of the OLS
  prediction interval — so uncertainty widens correctly the further out it
  forecasts. Survival probabilities are model estimates, not actuarial figures.

## Caveats
- All four run over public HCRIS (lagged cost reports), not a specific deal's
  internal data, and inherit HCRIS noise/gaps. They are benchmarks and model
  estimates, not realized outcomes.
