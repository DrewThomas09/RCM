# comparables/

Engine for finding comparable hospitals by structural and financial profile. Drives the peer-set used by every Ridge predictor in `ml/`.

| File | Purpose |
|------|---------|
| `engine.py` | Top-level `find_comparables(target, k=25)` — returns ranked peer list with similarity scores |
| `features.py` | Feature builder: bed count, payer mix vector, region, teaching, urban/rural, system affiliation |
| `mahalanobis.py` | Mahalanobis distance with covariance shrinkage for small peer pools |
| `psm.py` | Propensity-score matching variant for treatment-effect studies |
| `logistic.py` | Logistic-regression similarity (closed-form Newton-IRLS) for binary characteristic vectors |
| `consensus.py` | Combines multiple distance metrics into a single ranking when no one method dominates |

## How it differs from `ml/comparable_finder.py`

- `comparable_finder.py` is the **fast path** used during deal screening + Ridge prediction. Six-dimensional weighted similarity, runs in ~5ms.
- `comparables/` is the **deep path** for treatment-effect studies and counterfactual analysis. Slower (10–50ms), more rigorous. Used by `causal/` and `portfolio_synergy/`.

Don't replace one with the other — they serve different latency / accuracy tradeoffs.
