"""LBO debt paydown trajectory — does the debt actually get paid down?

Partner statement: "Sponsors love to talk about
de-leveraging through cash flow. The model shows
3.5× turning into 1.5× by exit. The model also shows
year 1 FCF that doesn't cover the mandatory amort,
year 2 FCF that barely does, and years 3-5 doing all
the work. That's a back-loaded paydown thesis. If
year 3 EBITDA misses, the de-leveraging story breaks
and you're refinancing into a worse market. Show me
the year-by-year FCF, the cash sweep applied, and
the leverage at each year-end. If paydown is back-
loaded, that's a flag."

Distinct from:
- `debt_sizing` — sets the debt at entry.
- `debt_capacity_sizer` — sizes the carrying capacity.
- `covenant_monitor` — current covenant headroom.
- `dividend_recap_analyzer` — dividend recap math.

This module projects the **paydown trajectory**
through the hold:

- per-year FCF (EBITDA − interest − tax − capex − ΔWC)
- mandatory amort applied
- discretionary cash sweep applied
- year-end debt + leverage ratio
- back-loaded flag if > 60% of paydown happens in
  back half

### Output

- per-year `LBOYear` (year, ebitda, fcf, mandatory_amort,
  cash_sweep, ending_debt, leverage_ratio)
- entry_leverage, exit_leverage
- total_paydown
- back_loaded_pct (share of paydown in back half)
- partner_verdict: balanced / back_loaded / concerning_back_loaded
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LBODebtPaydownInputs:
    entry_debt_m: float = 200.0
    entry_ebitda_m: float = 50.0
    annual_ebitda_growth_pct: float = 0.06
    interest_rate_pct: float = 0.085
    cash_tax_rate_pct: float = 0.25
    capex_as_pct_of_ebitda: float = 0.15
    delta_wc_as_pct_of_ebitda_growth: float = 0.10
    mandatory_amort_pct_per_year: float = 0.01  # 1% / yr
    cash_sweep_pct_of_excess_fcf: float = 0.75
    hold_years: int = 5


@dataclass
class LBOYear:
    year: int
    ebitda_m: float
    interest_m: float
    cash_tax_m: float
    capex_m: float
    delta_wc_m: float
    fcf_m: float
    mandatory_amort_m: float
    discretionary_paydown_m: float
    ending_debt_m: float
    leverage_ratio: float


@dataclass
class LBODebtPaydownReport:
    years: List[LBOYear] = field(default_factory=list)
    entry_leverage: float = 0.0
    exit_leverage: float = 0.0
    total_paydown_m: float = 0.0
    back_loaded_pct: float = 0.0
    verdict: str = "balanced"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "years": [
                {"year": y.year,
                 "ebitda_m": y.ebitda_m,
                 "interest_m": y.interest_m,
                 "cash_tax_m": y.cash_tax_m,
                 "capex_m": y.capex_m,
                 "delta_wc_m": y.delta_wc_m,
                 "fcf_m": y.fcf_m,
                 "mandatory_amort_m":
                     y.mandatory_amort_m,
                 "discretionary_paydown_m":
                     y.discretionary_paydown_m,
                 "ending_debt_m": y.ending_debt_m,
                 "leverage_ratio": y.leverage_ratio}
                for y in self.years
            ],
            "entry_leverage": self.entry_leverage,
            "exit_leverage": self.exit_leverage,
            "total_paydown_m": self.total_paydown_m,
            "back_loaded_pct": self.back_loaded_pct,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def project_lbo_debt_paydown(
    inputs: LBODebtPaydownInputs,
) -> LBODebtPaydownReport:
    debt = inputs.entry_debt_m
    ebitda_prev = inputs.entry_ebitda_m
    years: List[LBOYear] = []
    paydown_per_year: List[float] = []

    for y in range(1, inputs.hold_years + 1):
        ebitda = ebitda_prev * (
            1 + inputs.annual_ebitda_growth_pct
        )
        interest = debt * inputs.interest_rate_pct
        # crude cash tax: tax × (ebitda - interest - D&A)
        # using D&A approximated as 50% of capex
        capex = ebitda * inputs.capex_as_pct_of_ebitda
        da_proxy = capex * 0.50
        taxable_income = max(
            0.0, ebitda - interest - da_proxy)
        cash_tax = taxable_income * inputs.cash_tax_rate_pct
        delta_ebitda = ebitda - ebitda_prev
        delta_wc = (
            delta_ebitda *
            inputs.delta_wc_as_pct_of_ebitda_growth
        )
        fcf = (
            ebitda - interest - cash_tax - capex - delta_wc
        )
        mandatory = (
            inputs.entry_debt_m *
            inputs.mandatory_amort_pct_per_year
        )
        mandatory = min(mandatory, debt)
        excess_fcf = max(0.0, fcf - mandatory)
        discretionary = (
            excess_fcf * inputs.cash_sweep_pct_of_excess_fcf
        )
        discretionary = min(
            discretionary, max(0.0, debt - mandatory))
        debt = max(0.0, debt - mandatory - discretionary)
        leverage = debt / max(0.01, ebitda)
        years.append(LBOYear(
            year=y,
            ebitda_m=round(ebitda, 2),
            interest_m=round(interest, 2),
            cash_tax_m=round(cash_tax, 2),
            capex_m=round(capex, 2),
            delta_wc_m=round(delta_wc, 2),
            fcf_m=round(fcf, 2),
            mandatory_amort_m=round(mandatory, 2),
            discretionary_paydown_m=round(
                discretionary, 2),
            ending_debt_m=round(debt, 2),
            leverage_ratio=round(leverage, 2),
        ))
        paydown_per_year.append(mandatory + discretionary)
        ebitda_prev = ebitda

    entry_leverage = (
        inputs.entry_debt_m / max(0.01, inputs.entry_ebitda_m)
    )
    exit_leverage = (
        years[-1].leverage_ratio if years
        else entry_leverage
    )
    total_paydown = sum(paydown_per_year)

    half = inputs.hold_years // 2
    back_half = sum(paydown_per_year[half:])
    back_loaded_pct = (
        back_half / total_paydown
        if total_paydown > 0 else 0.0
    )

    if back_loaded_pct > 0.70:
        verdict = "concerning_back_loaded"
        note = (
            f"{back_loaded_pct:.0%} of paydown in back "
            f"half (years {half+1}-{inputs.hold_years}). "
            "Year 1-2 FCF doesn't move debt — the "
            "de-leveraging story depends on hitting "
            f"year {inputs.hold_years} EBITDA. Refi "
            "risk in years 1-2 if growth slips."
        )
    elif back_loaded_pct > 0.60:
        verdict = "back_loaded"
        note = (
            f"{back_loaded_pct:.0%} of paydown in back "
            "half. Acceptable if EBITDA growth has high "
            "confidence; price refi risk into IRR."
        )
    else:
        verdict = "balanced"
        note = (
            f"Balanced paydown — "
            f"{back_loaded_pct:.0%} in back half. "
            f"Entry {entry_leverage:.1f}× → exit "
            f"{exit_leverage:.1f}× over "
            f"{inputs.hold_years} years on FCF math."
        )

    return LBODebtPaydownReport(
        years=years,
        entry_leverage=round(entry_leverage, 2),
        exit_leverage=round(exit_leverage, 2),
        total_paydown_m=round(total_paydown, 2),
        back_loaded_pct=round(back_loaded_pct, 4),
        verdict=verdict,
        partner_note=note,
    )


def render_lbo_debt_paydown_markdown(
    r: LBODebtPaydownReport,
) -> str:
    lines = [
        "# LBO debt paydown trajectory",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Entry leverage: {r.entry_leverage:.1f}×",
        f"- Exit leverage: {r.exit_leverage:.1f}×",
        f"- Total paydown: ${r.total_paydown_m:.1f}M",
        f"- Back-loaded share: {r.back_loaded_pct:.0%}",
        "",
        "| Yr | EBITDA | Int | Tax | Capex | FCF | "
        "Amort | Sweep | EOY Debt | Lev |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for y in r.years:
        lines.append(
            f"| {y.year} | ${y.ebitda_m:.1f} | "
            f"${y.interest_m:.1f} | "
            f"${y.cash_tax_m:.1f} | "
            f"${y.capex_m:.1f} | ${y.fcf_m:.1f} | "
            f"${y.mandatory_amort_m:.1f} | "
            f"${y.discretionary_paydown_m:.1f} | "
            f"${y.ending_debt_m:.1f} | "
            f"{y.leverage_ratio:.1f}x |"
        )
    return "\n".join(lines)
