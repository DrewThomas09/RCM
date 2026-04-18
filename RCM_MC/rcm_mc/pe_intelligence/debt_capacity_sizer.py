"""Debt capacity sizer — the partner's sanity check on leverage.

Different from `capital_structure_tradeoff` (which sweeps leverage
vs MOIC) and `debt_sizing` (which computes prudent leverage for a
subsector). This is the partner reflex: "What's the right debt
number for THIS deal, given recurring EBITDA, cash-conversion,
cycle phase, and covenant posture?"

Partner sizes debt by stacking three constraints:

1. **Coverage** — stressed EBITDA / interest ≥ hurdle.
2. **Cash flow** — (EBITDA - capex - taxes) / debt-service ≥
   1.15x.
3. **Cycle discipline** — peak cycle caps leverage 0.5-1.0x
   below neutral; contraction adds 0.5-1.0x headroom.

Recommended debt = min of the three, reported in multiples + $.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DebtSizingInputs:
    recurring_ebitda_m: float = 0.0
    one_time_ebitda_m: float = 0.0
    maintenance_capex_m: float = 0.0
    effective_tax_rate: float = 0.21
    interest_rate: float = 0.095
    stress_ebitda_haircut_pct: float = 0.15
    coverage_hurdle: float = 2.5           # stressed EBITDA / interest
    fcf_dsc_hurdle: float = 1.15           # (ebitda-capex-tax)/debt_svc
    cycle_phase: str = "mid_expansion"
    subsector: str = "specialty_practice"
    covenant_lite_available: bool = False


# Partner-approximated neutral leverage by subsector.
NEUTRAL_LEVERAGE = {
    "hospital": 5.0,
    "safety_net_hospital": 4.0,
    "specialty_practice": 6.0,
    "outpatient_asc": 6.5,
    "home_health": 5.5,
    "dme_supplier": 5.5,
    "physician_staffing": 4.5,
}

CYCLE_ADJUST = {
    "early_expansion": 0.5,
    "mid_expansion": 0.0,
    "peak": -0.75,
    "contraction": 0.5,
}


@dataclass
class DebtSizingReport:
    recommended_leverage_x: float
    recommended_debt_m: float
    coverage_capacity_x: float
    fcf_capacity_x: float
    cycle_cap_x: float
    binding_constraint: str
    covenant_stress_coverage: float
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_leverage_x": self.recommended_leverage_x,
            "recommended_debt_m": self.recommended_debt_m,
            "coverage_capacity_x": self.coverage_capacity_x,
            "fcf_capacity_x": self.fcf_capacity_x,
            "cycle_cap_x": self.cycle_cap_x,
            "binding_constraint": self.binding_constraint,
            "covenant_stress_coverage":
                self.covenant_stress_coverage,
            "partner_note": self.partner_note,
        }


def size_debt_capacity(inputs: DebtSizingInputs) -> DebtSizingReport:
    # Only recurring EBITDA supports debt.
    ebitda = max(0.01, inputs.recurring_ebitda_m)

    # Coverage capacity: stressed EBITDA / (debt × rate) ≥ hurdle
    # → debt ≤ stressed / (hurdle × rate).
    stressed = ebitda * (1 - inputs.stress_ebitda_haircut_pct)
    if inputs.interest_rate > 0 and inputs.coverage_hurdle > 0:
        debt_from_coverage = stressed / (
            inputs.coverage_hurdle * inputs.interest_rate)
    else:
        debt_from_coverage = 0.0
    coverage_cap = debt_from_coverage / ebitda

    # FCF capacity: (EBITDA - capex - taxes) / debt_service ≥ hurdle.
    # debt_service ≈ debt × rate (interest-only approximation).
    pretax_fcf = ebitda - inputs.maintenance_capex_m
    # Tax effect: debt reduces taxable income by interest; use
    # conservative: tax on EBIT-ish. We approximate tax on EBITDA -
    # capex - interest but iteratively. Simpler: use after-tax FCF
    # assuming no shield.
    fcf_after_tax = pretax_fcf * (1 - inputs.effective_tax_rate)
    if inputs.fcf_dsc_hurdle > 0 and inputs.interest_rate > 0:
        debt_from_fcf = fcf_after_tax / (
            inputs.fcf_dsc_hurdle * inputs.interest_rate)
    else:
        debt_from_fcf = 0.0
    fcf_cap = debt_from_fcf / ebitda

    # Cycle-adjusted neutral leverage.
    neutral = NEUTRAL_LEVERAGE.get(inputs.subsector, 5.5)
    adj = CYCLE_ADJUST.get(inputs.cycle_phase, 0.0)
    cycle_cap = max(0.0, neutral + adj)
    if inputs.covenant_lite_available:
        cycle_cap += 0.5

    # Take the min.
    capacities = {
        "coverage": coverage_cap,
        "fcf": fcf_cap,
        "cycle": cycle_cap,
    }
    binding, leverage = min(capacities.items(), key=lambda kv: kv[1])
    leverage = max(0.0, leverage)
    debt_m = leverage * ebitda

    # Covenant stress coverage at recommended debt.
    stressed_coverage = (stressed
                          / max(0.01, debt_m * inputs.interest_rate)
                          if debt_m > 0 else 99.0)

    if leverage < 3.0:
        note = (f"Thin recommended leverage {leverage:.1f}x — deal's "
                "cash flow or coverage can't support more. Either the "
                "seller's model is over-levered, or the deal is less "
                "attractive than it looks.")
    elif binding == "cycle":
        note = (f"Cycle discipline binds at {leverage:.1f}x "
                f"(neutral {neutral:.1f}x + phase adj "
                f"{adj:+.1f}x). Coverage and cash flow support more; "
                "partner sticks to cycle discipline anyway.")
    elif binding == "fcf":
        note = (f"FCF coverage binds at {leverage:.1f}x. Tight "
                "cash flow after capex + tax; consider lower "
                "leverage or covenant-lite structure.")
    else:
        note = (f"Coverage binds at {leverage:.1f}x (stressed "
                f"EBITDA ${stressed:,.1f}M / "
                f"{inputs.coverage_hurdle:.1f}x hurdle). Partner-"
                "prudent cap.")

    return DebtSizingReport(
        recommended_leverage_x=round(leverage, 2),
        recommended_debt_m=round(debt_m, 2),
        coverage_capacity_x=round(coverage_cap, 2),
        fcf_capacity_x=round(fcf_cap, 2),
        cycle_cap_x=round(cycle_cap, 2),
        binding_constraint=binding,
        covenant_stress_coverage=round(stressed_coverage, 2),
        partner_note=note,
    )


def render_debt_sizing_markdown(r: DebtSizingReport) -> str:
    lines = [
        "# Debt capacity sizer",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Recommended leverage: "
        f"**{r.recommended_leverage_x:.2f}x**",
        f"- Recommended debt: ${r.recommended_debt_m:,.1f}M",
        f"- Coverage capacity: {r.coverage_capacity_x:.2f}x",
        f"- FCF capacity: {r.fcf_capacity_x:.2f}x",
        f"- Cycle cap: {r.cycle_cap_x:.2f}x",
        f"- Binding constraint: **{r.binding_constraint}**",
        f"- Stressed coverage at recommendation: "
        f"{r.covenant_stress_coverage:.2f}x",
    ]
    return "\n".join(lines)
