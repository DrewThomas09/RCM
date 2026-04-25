# causal/

Pure-numpy causal-inference substrate. Used by `portfolio_synergy/` and the post-close performance attribution to estimate counterfactual outcomes from observed differences.

| File | Method |
|------|--------|
| `did.py` | Difference-in-Differences — compares treated vs control groups before/after a shock (e.g., a CMS rule change) |
| `sdid.py` | Synthetic Difference-in-Differences — adds unit/time weighting; better when treatment timing varies |
| `synthetic_control.py` | Synthetic Control Method — builds a weighted control unit from donors when DiD's parallel-trends assumption breaks |

## Why these three

DiD answers "did our intervention move the needle?" but assumes the treated and control groups would have moved in parallel absent the treatment. SDID weights units to make that assumption more defensible. SCM is the fallback when there's no good single control unit — it builds one out of a weighted basket of donors. All three are stdlib + numpy; no `econml`, no `causalml`.

## Used by

- `portfolio_synergy/sdid.py` for cross-portfolio playbook lift estimation
- Post-close variance-vs-plan attribution in `pe/hold_tracking.py`
- The "counterfactual" tab in the workbench
