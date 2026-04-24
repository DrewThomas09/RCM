# labor/

**Labor economics diligence** (Prompt M, Gap 2). Three pragmatic sub-analytics covering the highest-value labor-market questions for healthcare PE.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — scope-reduced from original spec; three submodules. |
| `wage_forecaster.py` | **Regional wage-inflation projection.** MSA × role wage-inflation anchors derived from BLS QCEW / OES public aggregates (2024-2026 trend). Licensed BLS pull replaces these for diligence-grade. |
| `staffing_ratio_benchmark.py` | **HCRIS-derived staffing anchors** — nurses-per-occupied-bed, coders-per-10K-claims, etc. Public aggregates refreshed quarterly. |
| `synthetic_fte_detector.py` | **Synthetic-FTE detector.** Reconciles scheduling FTEs vs billing NPIs vs 941 payroll headcount. Flags when billing NPIs exceed scheduled FTEs by >25% — **historical signature of locum inflation or ghost providers**. |

## Synthetic-FTE is a fraud-signature module, not a model

This is reconciliation math, not prediction. Three independent FTE counts should agree:
- **Schedule**: how many clinicians the facility plans
- **Billing NPIs**: how many unique NPIs submit claims  
- **941 headcount**: how many W-2 payroll employees

When billing NPIs > schedule + 25%, the delta is typically either (a) locum spend not on schedule, or (b) ghost providers on billing (fraud). Either way it's a diligence-defining finding.

## Where it plugs in

- **Thesis Pipeline** — labor-cascade trigger when wage inflation >P75 or staffing ratio off-band
- **Labor-shortage cascade** (in `pe_intelligence/labor_shortage_cascade.py`) — nurse turnover → OT → contract labor → margin → quality → reimbursement
- **Bankruptcy-Survivor Scan** — synthetic-FTE finding is one of the 12 deterministic patterns (locum-inflated roster)

## Data sources

- **BLS QCEW / OES** — public wage aggregates (2024-2026 trend)
- **HCRIS** — staffing ratios by hospital type
- **IRS 941 payroll reports** — required seller disclosure; not public

Licensed BLS pull (replacing public aggregates) is the recommended upgrade for dedicated labor-heavy diligence.

## Tests

`tests/test_labor*.py` — wage-inflation projection + staffing-ratio benchmark lookup + synthetic-FTE pattern detection.
