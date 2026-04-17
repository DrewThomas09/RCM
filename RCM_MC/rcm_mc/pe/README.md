# PE

Private equity deal math: value creation bridges, returns analysis, debt modeling, waterfall distributions, hold-period tracking, and fund-level attribution. Converts simulated RCM EBITDA uplift into the metrics a PE investment committee underwrites on.

| File | Purpose |
|------|---------|
| `pe_math.py` | Core PE math: value creation bridge, MOIC/IRR computation, and leverage analysis (audit-defensible, stdlib-only) |
| `pe_integration.py` | Auto-compute hook for `rcm-mc run`: materializes bridge, returns, hold grid, and covenant JSON from simulation output |
| `value_bridge_v2.py` | Unit-economics EBITDA bridge (v2): payer-mix-weighted, method-sensitive, with four economic flavors per lever |
| `rcm_ebitda_bridge.py` | Legacy v1 bridge with uniform research-band coefficients; retained as calibration floor with locked regression tests |
| `value_creation.py` | Value creation simulation with linear ramp effects across hold-year scenarios |
| `value_creation_plan.py` | 100-day value creation plan builder: auto-generates initiatives from v2 bridge lever impacts with ramp curves |
| `value_plan.py` | Target config builder for value creation scenarios with distribution-moment validation |
| `attribution.py` | OAT (one-at-a-time) dollar-value attribution by driver bucket (denials, underpayments, AR days, appeals) |
| `breakdowns.py` | Per-payer and per-root-cause breakdown of simulation results |
| `debt_model.py` | Multi-tranche debt trajectory projections: mandatory amortization, cash sweeps, leverage ratios, covenant compliance |
| `fund_attribution.py` | Fund-level value-creation attribution decomposed into RCM improvement, organic growth, and multiple expansion |
| `hold_tracking.py` | Hold-period KPI tracking: actual vs underwritten variance with severity classification and cumulative drift |
| `lever_dependency.py` | Cross-lever dependency adjustment: reduces overlapping revenue recovery from causally linked levers to prevent double-counting |
| `predicted_vs_actual.py` | Predicted-at-diligence vs actual-at-hold comparison with confidence interval coverage analysis |
| `ramp_curves.py` | Per-lever S-curve implementation ramp (logistic interpolation) replacing the single-scalar ramp assumption |
| `remark.py` | Underwrite re-mark: re-underwrites a held deal from its actual EBITDA run-rate and records a before/after snapshot |
| `waterfall.py` | Standard American 4-tier GP/LP waterfall: return of capital, preferred return, GP catch-up, carried interest |

## Key Concepts

- **v1 vs v2 bridge**: The v1 bridge applies uniform coefficients (retained for calibration); v2 weights every lever by payer mix and reimbursement method.
- **Four economic flavors**: Each lever contributes recurring revenue uplift, recurring cost savings, one-time working capital release, and/or ongoing financing benefit.
- **Cross-lever dependency**: Causally linked levers are adjusted in topological order to prevent double-counting revenue recovery.
