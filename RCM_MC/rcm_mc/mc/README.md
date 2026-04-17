# MC

Monte Carlo simulation orchestration: deal-level and portfolio-level MC runs, convergence checking, scenario comparison, and result persistence. Builds on top of `core.simulator` to add prediction uncertainty, execution uncertainty, and cross-deal correlation.

| File | Purpose |
|------|---------|
| `ebitda_mc.py` | Two-source Monte Carlo (prediction uncertainty + execution uncertainty) over the RCM EBITDA bridge |
| `v2_monte_carlo.py` | Monte Carlo over the v2 value bridge with additional sampled dimensions: collection realization, denial overturn, per-payer leverage, exit multiple |
| `portfolio_monte_carlo.py` | Correlated MC across all portfolio deals with cross-deal execution correlation, diversification benefit, and tail-risk scenarios |
| `scenario_comparison.py` | Side-by-side MC scenario comparison with pairwise win-probability and recommended-scenario selection |
| `convergence.py` | Running-P50 convergence check: verifies the MC result is stable enough to publish |
| `mc_store.py` | SQLite storage for MC runs, append-only with latest-endpoint support for diffing runs over time |

## Key Concepts

- **Two uncertainty sources**: Prediction uncertainty (where is the target?) and execution uncertainty (will the team hit it?) are sampled independently.
- **Portfolio correlation**: Cross-deal execution correlation (default 0.3 within-family) captures systematic risk that per-deal MC misses.
- **Convergence gating**: Results are flagged as untrustworthy if the running P50 hasn't stabilized within the configured tolerance.
