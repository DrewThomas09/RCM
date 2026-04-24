# root_cause/

**Phase 3 — Root Cause Analysis.** Phase marker; logic lives distributed across `benchmarks/`, `counterfactual/`, and individual risk modules.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | **Phase 3 marker only.** Currently holds the docstring; actual root-cause logic is distributed across other packages. Future analytics will land here. |

## Why this package is thin

The four-phase RCM Diligence Playbook (Ingestion → Benchmarking → Root Cause → Value Creation) is the **narrative architecture** partners use to organize their work. The package exists to hold that narrative. Actual root-cause math is composition over existing surfaces:

- **Pareto of drivers for an off-benchmark KPI** → built from `benchmarks/kpi_engine` outputs + causal attribution from `analytics/causal_inference.py`
- **ZBA (zero-balance-account) write-off autopsy** → `benchmarks/cash_waterfall.py` walks the claim from gross → realized cash; `finance/denial_drivers.py` decomposes the "why" behind high denial rates
- **One-click-from-KPI-to-underlying-rows** → `provenance/` graph provides the link back to source CCD rows

When a standalone root-cause analytic ships, it lives here.

## Where it plugs in

This is a placeholder. The phase's narrative purpose is served by existing packages; no direct consumers today.
