# montecarlo_v3/

Advanced Monte Carlo techniques layered on top of the basic engine in `mc/`. Used when the headline simulation needs better tail accuracy or fewer paths.

| File | Technique |
|------|-----------|
| `antithetic.py` | Antithetic-variate sampling — pairs each draw with its mirror to halve variance |
| `control_variates.py` | Control-variate variance reduction — leverages a known-mean correlated quantity |
| `importance.py` | Importance sampling for rare-event tails (covenant breach, distress) |
| `copula.py` | Gaussian / Student-t copulas for correlated driver distributions |
| `sobol.py` | Sobol low-discrepancy sequences — quasi-Monte Carlo for faster convergence |
| `nested.py` | Nested simulation for path-dependent payoffs (e.g., earn-out structures) |
| `healthcare.py` | Healthcare-specific samplers — payer-mix Dirichlet, denial-rate Beta, AR-aging Erlang |

## When to use

`mc/ebitda_mc.py` (the headline two-source MC) uses Beasley-Springer-Moro inverse normal — fast, simple, accurate enough for 90% of cases. `montecarlo_v3/` is the **escape hatch** when you need tighter tail estimates (covenant lab Y4Q3 default probability) or fewer paths (real-time scenario sweeps in the workbench).

All techniques are pure-numpy. No `scipy.stats`.
