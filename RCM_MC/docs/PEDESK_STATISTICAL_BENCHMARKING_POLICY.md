# PEdesk statistical benchmarking policy

How PEdesk turns real datasets into benchmarks/priors **without overclaiming**.
Applies to every distribution, percentile, peer band, or prior surfaced in
diligence (HCRIS peer bands, Colorado payer/RBP context, Deal Library multiples,
drug-shortage category counts, future datasets).

## Allowed statistics

Percentiles (P25 / median / P75), means where appropriate, sample size,
missingness rates, peer groups, trend over real periods, outlier detection,
and missingness-aware priors. Always show **n** and the **missingness rate**
alongside any benchmark.

## Minimum sample sizes (hard rule)

| n | Treatment |
|---|---|
| **n < 5** | **No benchmark.** Show "insufficient sample (n<5)", not a number. |
| **5 ≤ n < 15** | Directional only — render with a **low-confidence** flag. |
| **15 ≤ n < 30** | Usable, **caveated** (show n + spread). |
| **n ≥ 30** | Stronger benchmark; still show n + missingness. |

A peer band / percentile must carry its `n`. If a filter drops the pool below
5, the surface degrades to "insufficient sample", never a fabricated value.

## Missingness

- **Never use a missing value as zero.** Missing → excluded from the statistic
  (and the exclusion is disclosed), or shown as "—".
- **Never silently fill** blanks (no mean/median imputation written into a
  field). If imputation is ever used for a model input, it is labeled ESTIMATED
  with the method.

## Estimates vs observations

- A figure derived from real observed fields is **DERIVED** (show the formula).
- A figure from a peer distribution is a **BENCHMARK** — never call it a
  "prediction" or "forecast" unless a model is **validated** (with held-out
  performance documented). Benchmark distributions are descriptive, not
  predictive.
- A modeled estimate is **ESTIMATED** with source inputs, method, peer group,
  sample size, and confidence — and is never written into an observed/raw
  field.

## "Corpus-calibrated" language

Only use "corpus-calibrated" when the corpus is **real and documented**. The
bundled seed deals are an **illustrative** corpus and must be labeled
seed/illustrative, never presented as real calibration.

## Geography / scope

State-specific data (e.g. Colorado CIVHC) is labeled and **not generalized
nationally**. Provider-level vs market-level is always distinguished. National
product-level data (e.g. FDA shortages) is not presented as provider-specific.

## Applied examples

- HCRIS peer bands: show n in the matched pool; below 5 → no band.
- Deal Library multiples (`/deal-library/comps`): EV/Revenue n=274, EV/EBITDA
  n=135 — usable/caveated, labeled "benchmark distribution, not a prediction".
- Colorado RBP/cost: market context, state-caveated, not facility-specific.
- FDA drug shortages: national counts by category; product-level, not provider.
