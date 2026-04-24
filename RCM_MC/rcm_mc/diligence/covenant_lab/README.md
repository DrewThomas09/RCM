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

## Files in this module

```
covenant_lab/
├── __init__.py         # Public API re-exports
├── capital_stack.py    # Debt tranches + amort schedule + default LBO stack (379 LOC)
├── covenants.py        # Covenant definitions + per-quarter evaluator (259 LOC)
└── simulator.py        # MC engine + path reconstruction + equity cure math (639 LOC)
```

### `__init__.py` (thin)
Re-exports: `run_covenant_stress`, `default_lbo_stack`, `CapitalStack`, `DebtTranche`, `TrancheKind`, `CovenantDefinition`, `CovenantKind`, `CovenantStressResult`.

### `capital_stack.py` (379 LOC)
Models the **debt side of the balance sheet**. Six tranche kinds (`REVOLVER / TLA / TLB / UNITRANCHE / MEZZANINE / SELLER_NOTE`) with fixed or floating rates, custom amortization schedules, commitment fees on undrawn revolver, lien priority.

Two big building blocks:
- `build_debt_schedule(stack, rate_path_annual, quarters)` — quarterly interest + scheduled principal + fees
- `default_lbo_stack(total_debt_usd, revolver_usd, revolver_draw_pct, term_years)` — a sensible starter stack when the user hasn't specified one

### `covenants.py` (259 LOC)
Covenant definitions + evaluator. Four built-in covenants (`NET_LEVERAGE`, `DSCR`, `INTEREST_COVERAGE`, `FIXED_CHARGE_COVERAGE`) with optional step-down schedules (e.g., leverage starts at 7.5×, tightens to 6.0× by Y4).

Key entry: `evaluate_covenant(covenant, ltm_ebitda, debt, debt_service, interest, maint_capex, quarter_index) → (headroom_ratio, breached: bool)`.

Edit `DEFAULT_COVENANTS` at the bottom to change the standard test set.

### `simulator.py` (639 LOC)
The **Monte Carlo brain**. Takes Deal MC's yearly EBITDA p25/p50/p75 bands → reconstructs 500 lognormal synthetic paths via stdlib Beasley-Springer-Moro inverse normal (no scipy). Runs each path through quarterly debt service × covenant evaluation, tracks per-quarter breach probabilities, computes equity-cure sizes when breached, subtracts Regulatory Calendar's EBITDA overlay before testing.

Key entry: `run_covenant_stress(ebitda_bands, capital_stack, rate_path_annual, quarters, regulatory_overlay_usd_by_year) → CovenantStressResult`.

---

## Adjacent files

- **[`rcm_mc/ui/covenant_lab_page.py`](../../ui/covenant_lab_page.py)** — web page at `/diligence/covenant-lab`
- **[`tests/test_covenant_lab.py`](../../../tests/test_covenant_lab.py)** — 17 tests covering tranche amort, covenant tests, equity-cure math

---

## Tests

```bash
python -m pytest tests/test_covenant_lab.py -q
# Expected: 17 passed
```
