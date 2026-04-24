# benchmarks/

**Phase 2 — KPI Benchmarking & Stress Testing.** Reads the CCD from Phase 1. Computes HFMA-vocabulary KPIs with cited formulas, cohort liquidation curves with mandatory as-of censoring, and denial stratification by ANSI CARC category.

## Design principle

**Every formula is cited. Every KPI returns either a computed value OR `None + reason` — never an estimate, never an interpolation, never a partial number wearing a full-metric label.** If a partner can't defend the number to a skeptical auditor, the number doesn't ship.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Phase 2 docstring. |
| `kpi_engine.py` | **The HFMA KPI computer.** Every formula cited; returns value-or-(None+reason). The audit-defensible surface every other phase reads. |
| `_ansi_codes.py` | **ANSI CARC → denial category.** Rule-based grouping (front-end / coding / clinical / payer-behavior). **Load-bearing spec assertion**: not an ML classifier — an auditable rule file. |
| `cash_waterfall.py` | **Quality of Revenue output.** Walks every claim gross charges → contractual adjustments → front-end leakage → initial denials (net of appeals) → bad debt → realized cash. Cohorted by date-of-service month. |
| `cohort_liquidation.py` | **Cohort liquidation with mandatory as-of censoring.** Guards the trap: analyst running diligence 2026-03-15 looking at "Jan 2026 cohort at 90 days" would read incomplete data. Refuses to emit a number until the cohort has actually aged past the requested window. |
| `contract_repricer.py` | **Re-prices claims against a structured `ContractSchedule`** (payer × CPT → contracted rate, carve-outs, stop-loss, withhold primitives). Feeds the underpayment-recovery lever in the bridge. |

## The censoring rule

From `cohort_liquidation.py` — the guardrail in prose:

> An analyst running diligence on 2026-03-15 looks at the "January 2026 cohort at 90 days." But `2026-01-15 + 90 days = 2026-04-15` — after the as-of date. Only 60 days have actually elapsed. The KPI is **undefined**, not "estimated."

`integrity/cohort_censoring.py` is the structured guardrail wrapping this math for the preflight gauntlet.

## Where it plugs in

- **Phase 1 ingest** provides the CCD input
- **`diligence/ccd_bridge.py`** converts KPIs → `ObservedMetric`s for `analysis.packet_builder`
- **Thesis Pipeline step 2** (KPI bundle) calls `kpi_engine` directly
- **UI** at `ui/diligence_benchmarks.py` — Phase 2 tab renderer

## Tests

`tests/test_benchmarks*.py` — every formula has a unit test with a fixture input and expected output.
