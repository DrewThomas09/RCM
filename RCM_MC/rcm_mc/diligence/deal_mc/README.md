# deal_mc/

**Deal-level Monte Carlo** — the EBITDA + MOIC + IRR distribution engine that integrates every risk module's output. Models the full hold-period EBITDA path, not just Phase-1 drag.

## What it does

For each Monte Carlo trial, draws:
- `organic_growth_rate ~ N(μ, σ)` — revenue CAGR
- `denial_rate_improvement_pp ~ N` — RCM-lever uplift
- `regulatory_headwind_usd` — fed from Regulatory Calendar
- `lease_escalator_pct ~ N`
- `physician_attrition` — fed from P-PAM
- `cyber_incident_probability` — fed from CyberScore
- `v28_coding_compression` — fed from MA dynamics
- `exit_multiple ~ N` — multiple expansion / compression prior

Per trial: compound these drivers over the 5-year hold → terminal EBITDA → exit EV (EBITDA × exit_multiple) → proceeds → MOIC + IRR.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — "FULL hold-period EBITDA path." |
| `engine.py` | **The MC brain.** Draws drivers, compounds paths, produces MOIC/IRR/proceeds distributions. Seeded for reproducibility. |
| `charts.py` | **Zero-dep SVG chart generators.** Pure string templates — no numpy/matplotlib/plotly. Charts inline in the UI. |

## Outputs

`DealMCResult` carries:
- MOIC / IRR / proceeds distributions (P10 / P50 / P90)
- `P(MOIC<1×)` — probability of losing money
- Driver-attribution decomposition (Sobol-style first-order indices, stdlib-only)
- Sensitivity tornado

## Where it plugs in

- **Thesis Pipeline step 17** — runs 1,500+ trials
- **Covenant Lab** reads P25/P50/P75 EBITDA bands and reconstructs 500 lognormal paths
- **Bear Case** reads `P(MOIC<1×)` + P10 MOIC tail → `[M1]` evidence
- **Exit Timing** reads the year-by-year EBITDA trajectory for its Y2-Y7 curve

## Config

Trials configurable via `n_runs` (default 1,500). Hold period default 5yr. Driver distributions live in `DealScenario` dataclass.

## Tests

`tests/test_deal_mc.py` — driver-distribution contracts, convergence bands, attribution math.
