# Covenant & Capital Stack Stress Lab

**In one sentence**: tells you per quarter how likely you are to breach your loan covenants over the 5-year hold.

---

## What problem does this solve?

When a PE firm buys a company, they borrow ~60% of the purchase price. The loan comes with "covenants" — rules the borrower must follow (e.g., "debt-to-EBITDA must stay below 6×", "interest coverage must stay above 2.25×"). Break a covenant and the bank can call the loan, force an equity cure, or seize the company.

Partners ask: *"In what quarter does this deal hit a covenant cliff, and how much equity do I need to cure it?"*

Traditional tools build a single base-case DCF. This tool runs **500 synthetic EBITDA paths × 20 quarters × 3-4 covenants** and shows you the breach-probability curve per covenant over time.

---

## How it works

1. **Capital stack modeler**: supports 6 tranche types (Revolver, TLA, TLB, Unitranche, Mezzanine, Seller Note) with floating/fixed rate, custom amortization schedules, commitment fees, lien priority.
2. **EBITDA path reconstruction**: takes the Deal MC's year-by-year p25/p50/p75 bands and reconstructs 500 synthetic lognormal paths using a stdlib-only Beasley-Springer-Moro inverse normal (no scipy).
3. **Quarterly debt schedule**: per-tranche interest + scheduled amort + commitment fees.
4. **Per-quarter covenant test** on each path:
   - Net Leverage (total debt ÷ LTM EBITDA)
   - DSCR (LTM EBITDA ÷ debt service)
   - Interest Coverage (LTM EBITDA ÷ interest)
   - Fixed Charge Coverage (LTM EBITDA − maint capex) ÷ (debt service + taxes)
   - Step-downs supported (e.g., leverage 7.5× opens, steps to 6.0× by Y4)
5. **Equity-cure math**: when a path breaches, compute the $ injection that unbreaches it.
6. **Regulatory overlay**: subtracts the Regulatory Calendar's EBITDA overlay from each path before covenant testing — partners see V28 + site-neutral tightening the Y2 leverage covenant.

---

## Verdict thresholds (PE bank underwriting norms)

| Max breach probability | Verdict |
|------------------------|---------|
| **<10%** | PASS · clears bank norms |
| **10–25%** | WATCH · tight but bankable |
| **25–50%** | WARNING · negotiate cushion at term sheet |
| **>50%** | FAIL · re-price, tighten, or walk |

---

## Public API

```python
from rcm_mc.diligence.covenant_lab import (
    run_covenant_stress,
    default_lbo_stack,
    CapitalStack, DebtTranche, TrancheKind,
    CovenantDefinition, CovenantKind,
    CovenantStressResult,
)

# Default LBO stack
stack = default_lbo_stack(
    total_debt_usd=300_000_000,
    revolver_usd=40_000_000,
    revolver_draw_pct=0.30,
    term_years=6,
)

# Run stress simulation
result = run_covenant_stress(
    ebitda_bands=[
        {"p25": 60e6, "p50": 67.5e6, "p75": 75e6},
        # one dict per year for 5-6 years
    ],
    capital_stack=stack,
    rate_path_annual=[0.055] * 20,
    quarters=20,
    regulatory_overlay_usd_by_year=[0, 0, -9.9e6, -9.95e6, 0],
)
print(result.verdict.value)  # PASS / WATCH / WARNING / FAIL
print(result.headline)
for fb in result.first_breach:
    print(fb.covenant_name, "Q50%:", fb.first_50pct_breach_quarter)
```

---

## Where it plugs in

- **Thesis Pipeline**: auto-runs when Deal MC produces EBITDA bands
- **Bear Case**: 50%+ breach covenants become `[C1]` citation evidence
- **Deal Profile**: tile under FINANCIAL phase
- **Cross-links**: EBITDA seed from HCRIS X-Ray → Covenant Lab with cap structure pre-filled

---

## Files

```
covenant_lab/
├── __init__.py
├── capital_stack.py    # DebtTranche + build_debt_schedule + default_lbo_stack
├── covenants.py        # CovenantDefinition + evaluate_covenant + DEFAULT_COVENANTS
└── simulator.py        # run_covenant_stress + path reconstruction + equity cures
```

---

## Tests

```bash
python -m pytest tests/test_covenant_lab.py -q
# Expected: 17 passed
```
