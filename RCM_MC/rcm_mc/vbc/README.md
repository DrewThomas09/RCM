# vbc/

Value-based-care contract economics. Models risk-adjusted revenue, HCC scoring, and population-health margin under capitated and shared-savings arrangements.

| File | Purpose |
|------|---------|
| `cohort.py` | Patient-cohort builders — attribution, member months, churn |
| `contracts.py` | VBC contract schema — capitation, shared savings/risk, MLR floor, performance bonuses |
| `hcc.py` | HCC (Hierarchical Condition Category) risk scoring with V28 mapping |
| `hierarchical.py` | Hierarchical Bayesian shrinkage for small-cohort PMPM estimates |
| `ltv.py` | Lifetime-value model for attributed members |
| `shrinkage.py` | Empirical-Bayes shrinkage helper used by `hierarchical.py` |

## Sister module: vbc_contracts/

`vbc_contracts/` is the **deal-side** valuator (one VBC contract → IRR contribution). This module is the **portfolio-side** modeling (cohort dynamics across the book).
