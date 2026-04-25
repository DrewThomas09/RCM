# qoe/

Quality-of-Earnings analysis — flags non-recurring items, one-off boosts, accounting noise, and the "earnings adjustments" sellers love to claim.

| File | Purpose |
|------|---------|
| `bridge.py` | EBITDA-bridge from reported → adjusted EBITDA, with line-item realization scoring |
| `detectors.py` | Catalog of named detectors: stub-period gains, billing pull-forwards, accrual flips, cost normalizations |
| `flagger.py` | Top-level orchestrator — runs every detector against the deal P&L, returns ranked flags |
| `isolation_forest.py` | Anomaly detection on monthly P&L lines (pure-numpy isolation forest) |
| `zscore.py` | Period-over-period z-score outlier detection |

## Output

A `QoEReport` with:
- Adjusted EBITDA (range with P25/P50/P75 confidence)
- Top-N adjustment flags (severity, dollar impact, citation)
- "Sustainable run-rate" verdict — is reported EBITDA defensible?

Plugs into `bear_case/` (flags become evidence) and `pe/rcm_ebitda_bridge.py` (the bridge starts from QoE-adjusted EBITDA, not reported).
