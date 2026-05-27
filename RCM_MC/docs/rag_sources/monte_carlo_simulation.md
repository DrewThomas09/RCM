# Monte Carlo Simulation Engine

How PEdesk projects a deal's EBITDA / returns as a distribution rather than a
single point. This explains the backend engine so the Guide can answer "how
does the simulation work / what do P10–P90 mean / how reliable is it".

## What it does
For a deal, the simulator runs N independent trials. Each trial draws the
uncertain inputs (RCM-initiative outcomes such as denial-rate improvement,
days-in-AR reduction, and the resulting revenue/cost effects) from their
modeled distributions, runs the deal math, and records the outcome (e.g.
EBITDA, MOIC). Across all trials you get a distribution, summarized as
percentiles — typically P10 (downside), P50 (median), P90 (upside).

## How it is built (modules)
- `rcm_mc/core/simulator.py` — runs the N trials for a deal.
- `rcm_mc/mc/ebitda_mc.py` — the two-source Monte Carlo that combines the
  RCM-initiative source and the EBITDA source into the outcome distribution.
- Input distributions are calibrated from priors/benchmarks (see the
  prediction-models and provenance cards), not invented per run.

## How to read the outputs
- The spread (P10→P90) is the model's honest uncertainty, not a forecast error
  bar from realized data. A wide band means the inputs are uncertain.
- P50 is the median trial, not "the answer" — read it with the spread.
- More trials tighten the Monte Carlo noise but do NOT reduce the underlying
  input uncertainty.

## Caveats
- Outputs are model estimates over assumed input distributions — they are only
  as good as those assumptions and the deal's input data.
- Correlation between inputs matters; independent draws can understate tail
  risk. Fund-level aggregation uses the correlated portfolio MC
  (/portfolio/monte-carlo).
- Not a realized or audited result. Use for ranging and risk, not as a promise.
