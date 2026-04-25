# buyandbuild/

Tuck-in M&A optimization for buy-and-build platforms. Given a platform deal and a candidate set of add-on targets, picks the optimal acquisition sequence under capital and integration-capacity constraints.

| File | Purpose |
|------|---------|
| `candidates.py` | Candidate target schema and loader |
| `constraints.py` | Capital, EBITDA-multiple, geographic, and integration-capacity constraints |
| `synergy.py` | Per-pair synergy estimator (revenue + cost) |
| `options.py` | Real-options valuation of optional future tuck-ins |
| `optimize.py` | Top-level `optimize_sequence(platform, candidates, budget, hold_years)` |
| `branch_and_bound.py` | Branch-and-bound solver (pure numpy, no `scipy.optimize`) for the integer-programming surface |

## Output

A `BuyAndBuildPlan`: ranked sequence of tuck-ins per year, capital deployment schedule, projected platform EBITDA trajectory, and synergy realization timeline. Feeds the workbench's Buy-and-Build tab and the IC memo's M&A pipeline section.
