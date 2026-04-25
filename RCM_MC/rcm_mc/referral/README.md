# referral/

Referral-graph analysis. Reads claims-derived referral edges to identify leakage, hub physicians, and concentration risk.

| File | Purpose |
|------|---------|
| `graph.py` | Directed weighted graph of (referring_npi → receiving_npi → patient_count) |
| `loader.py` | Builds the graph from the claims feed (or NPPES + utilization fallback) |
| `centrality.py` | PageRank / betweenness centrality to identify hub physicians (whose departure would re-route significant volume) |
| `leakage.py` | "Outbound referrals to non-system providers" — quantifies revenue leakage |
| `simulate.py` | What-if: simulate the impact of a hub physician's departure on downstream volume |

## Used by

- `diligence/physician_attrition/` — hub-physician departure → revenue-at-risk multiplier
- `diligence/value/` — referral-network synergy thesis for tuck-ins
