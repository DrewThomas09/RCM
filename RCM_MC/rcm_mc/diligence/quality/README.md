# quality/

**Clinical quality projector** (Gap 6) — VBP / HRRP / HAC three-year forward reimbursement-penalty + bonus projector.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Surfaces `QualityPenaltyProjection` + `project_vbp_hrrp`. |
| `vbp_hrrp_projector.py` | **Three-year VBP/HRRP/HAC projector.** Given current Care Compare star rating + HRRP excess-readmission ratios + HAC score → reimbursement impact under current CMS formulas over 3-year horizon. |

## Why this matters

Quality is reimbursement. CMS Value-Based Purchasing (VBP), Hospital Readmissions Reduction Program (HRRP), and Hospital-Acquired Conditions (HAC) programs each impose multi-percent payment adjustments tied to quality metrics. Adjustments lag deterioration by ~18-24 months.

Partner statement: "A deal with a CMS 4-star hospital is worth materially more than a 3-star. The 4→3 star transition is a ~2% revenue hit that shows up 18 months after quality starts to slip."

## Output

`QualityPenaltyProjection`:
- Current-year VBP bonus/penalty $
- HRRP penalty $ (based on excess-readmission ratio)
- HAC penalty $ (top-quartile performers on AHRQ PSI-90 + CAUTI + CLABSI + etc.)
- 3-year forward projection under "quality flat" / "quality improving" / "quality deteriorating" scenarios

## Calibration

Formula inputs from CMS Final Rules for the current fiscal year:
- VBP: 2% of base IPPS payment redistributed per HVBP total performance score
- HRRP: up to 3% penalty based on excess readmissions for 6 targeted conditions
- HAC: 1% penalty for bottom-quartile AHRQ composites

Refresh annually when CMS publishes new Final Rules.

## Where it plugs in

- **Thesis Pipeline** — runs when Care Compare star rating available (via `data/cms_care_compare.py`)
- **Clinical Outcome Leading Indicator Scanner** (`pe_intelligence/clinical_outcome_leading_indicator_scanner.py`) — "quality hits reimbursement 18-24 months after it deteriorates"
- **Deal MC** — quality-based reimbursement adjustments as a driver

## Tests

`tests/test_quality*.py` — penalty math per program + 3-year projection scenarios.
