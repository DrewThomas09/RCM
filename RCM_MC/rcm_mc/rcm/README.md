# RCM

Revenue Cycle Management operational modeling: claim distributions, initiative libraries, optimization, tracking, and cross-deal rollup. Bridges the gap between simulated EBITDA impact and the specific operational initiatives a deal team executes.

| File | Purpose |
|------|---------|
| `claim_distribution.py` | Lognormal claim-bucket builder and per-bucket denial rate modeling for the simulation engine |
| `initiatives.py` | Initiative library (8-12 standard RCM initiatives) loaded from `configs/initiatives_library.yaml` with deltas, costs, ramp, and confidence |
| `initiative_optimizer.py` | Ranks initiatives by EBITDA uplift, EV uplift, payback, and confidence using N+1 simulation runs (baseline + each initiative) |
| `initiative_tracking.py` | Hold-period per-initiative quarterly attribution: actual dollar impact vs underwritten plan with variance reporting |
| `initiative_rollup.py` | Cross-deal initiative rollup: aggregates initiative performance across the portfolio to identify systematic playbook issues |

## Key Concepts

- **Initiative library as config**: Standard initiatives are defined in YAML with affected parameters, delta distributions, costs, and ramp curves -- not hard-coded.
- **N+1 optimization**: Each initiative is evaluated by running the full simulation with and without it, producing honest marginal-impact rankings.
- **Portfolio-level pattern recognition**: If 6 of 8 deals running the same initiative are lagging, the problem is the playbook, not the deal.
