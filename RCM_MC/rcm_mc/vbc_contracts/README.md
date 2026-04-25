# vbc_contracts/

Per-contract VBC valuator. Takes a single value-based contract and projects its IRR contribution under stochastic risk-adjusted-revenue distributions.

| File | Purpose |
|------|---------|
| `programs.py` | Catalog of named programs: ACO REACH, MSSP, MA full-risk, MA shared-savings, commercial direct-contracting |
| `valuator.py` | Top-level `value_contract(contract, target)` → distribution of NPV / IRR contributions |
| `bayesian.py` | Bayesian update of the program's PMPM prior given the target's claims history |
| `posterior.py` | Posterior sampling for the per-contract MC |
| `stochastic.py` | Risk-adjusted-revenue stochastic process (mean-reverting with churn jumps) |

## Sister module: vbc/

`vbc/` is the **portfolio-side** book of business (cohort dynamics). This module is the **deal-side** per-contract valuation. Both share the HCC scorer in `vbc/hcc.py`.
