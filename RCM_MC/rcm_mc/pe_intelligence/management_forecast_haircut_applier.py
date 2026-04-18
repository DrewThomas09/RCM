"""Management forecast haircut applier — partner-prudent adjustment.

Partner statement: "Management always forecasts to
the upside. The question isn't whether to haircut —
it's how much, year by year. Year 1 is partly
controllable, so haircut less. Years 2-3 are where
ambition meets reality. Years 4-5 are where every
forecast hockey-sticks. Once you have the management
case, lay the haircut on top, run the IRR, and tell me
where management's number actually leaves us."

Distinct from:
- `management_forecast_reliability` — scores prior
  forecasts vs actuals.
- `qofe_prescreen` — assesses add-back survival.
- `bear_case_generator` — generic bear case.

This module **applies** the haircut. Inputs:
- year-by-year mgmt EBITDA forecast
- a reliability tier (high / medium / low / very_low)
- entry/exit assumptions

Outputs:
- partner-haircut EBITDA per year
- partner-implied exit MOIC and IRR
- delta vs management case (MOIC and IRR)
- partner note on whether the gap is acceptable

### Haircut tiers (per-year haircut % of mgmt growth)

Per-year cumulative haircut applied to management's
incremental growth:

| Tier | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| high | 5% | 8% | 10% | 12% | 15% |
| medium | 10% | 15% | 20% | 25% | 30% |
| low | 20% | 30% | 35% | 40% | 45% |
| very_low | 35% | 45% | 55% | 60% | 65% |

Haircut is applied to the **growth above year 0**:
`partner_yN = year_0 + (mgmt_yN - year_0) × (1 - haircut_yN)`.

### Partner-note tiers

- delta_moic ≤ 0.20× → "haircut absorbable; mgmt forecast credible"
- 0.20-0.50× → "material haircut; price risk into entry"
- > 0.50× → "haircut breaks the underwrite; either tighten
  forecast assumptions with mgmt or pass"
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


HAIRCUT_TIERS: Dict[str, List[float]] = {
    "high": [0.05, 0.08, 0.10, 0.12, 0.15],
    "medium": [0.10, 0.15, 0.20, 0.25, 0.30],
    "low": [0.20, 0.30, 0.35, 0.40, 0.45],
    "very_low": [0.35, 0.45, 0.55, 0.60, 0.65],
}


@dataclass
class ForecastHaircutInputs:
    mgmt_ebitda_y0_m: float = 50.0
    mgmt_ebitda_forecast_m: List[float] = field(
        default_factory=lambda: [55.0, 62.0, 70.0, 78.0, 87.0]
    )
    reliability_tier: str = "medium"
    entry_multiple: float = 11.0
    exit_multiple: float = 12.0
    entry_debt_m: float = 200.0
    exit_debt_m: float = 80.0
    sponsor_equity_in_m: float = 150.0


@dataclass
class HaircutYear:
    year: int
    mgmt_ebitda_m: float
    haircut_pct: float
    partner_ebitda_m: float


@dataclass
class ForecastHaircutReport:
    years: List[HaircutYear] = field(default_factory=list)
    mgmt_exit_ebitda_m: float = 0.0
    partner_exit_ebitda_m: float = 0.0
    mgmt_exit_ev_m: float = 0.0
    partner_exit_ev_m: float = 0.0
    mgmt_exit_equity_m: float = 0.0
    partner_exit_equity_m: float = 0.0
    mgmt_moic: float = 0.0
    partner_moic: float = 0.0
    delta_moic: float = 0.0
    mgmt_irr: float = 0.0
    partner_irr: float = 0.0
    delta_irr: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "years": [
                {"year": y.year,
                 "mgmt_ebitda_m": y.mgmt_ebitda_m,
                 "haircut_pct": y.haircut_pct,
                 "partner_ebitda_m": y.partner_ebitda_m}
                for y in self.years
            ],
            "mgmt_exit_ebitda_m": self.mgmt_exit_ebitda_m,
            "partner_exit_ebitda_m":
                self.partner_exit_ebitda_m,
            "mgmt_exit_ev_m": self.mgmt_exit_ev_m,
            "partner_exit_ev_m": self.partner_exit_ev_m,
            "mgmt_exit_equity_m":
                self.mgmt_exit_equity_m,
            "partner_exit_equity_m":
                self.partner_exit_equity_m,
            "mgmt_moic": self.mgmt_moic,
            "partner_moic": self.partner_moic,
            "delta_moic": self.delta_moic,
            "mgmt_irr": self.mgmt_irr,
            "partner_irr": self.partner_irr,
            "delta_irr": self.delta_irr,
            "partner_note": self.partner_note,
        }


def _moic_to_irr(moic: float, years: int) -> float:
    """IRR from MOIC + hold-years (rough closed-form)."""
    if moic <= 0 or years <= 0:
        return 0.0
    return moic ** (1.0 / years) - 1.0


def apply_management_haircut(
    inputs: ForecastHaircutInputs,
) -> ForecastHaircutReport:
    haircuts = HAIRCUT_TIERS.get(
        inputs.reliability_tier,
        HAIRCUT_TIERS["medium"],
    )
    years: List[HaircutYear] = []
    y0 = inputs.mgmt_ebitda_y0_m

    for i, mgmt_y in enumerate(
        inputs.mgmt_ebitda_forecast_m
    ):
        if i < len(haircuts):
            haircut = haircuts[i]
        else:
            # extrapolate beyond 5 years using last
            # tier value
            haircut = haircuts[-1]
        # haircut applied to growth from year 0
        growth = mgmt_y - y0
        partner_y = y0 + growth * (1.0 - haircut)
        years.append(HaircutYear(
            year=i + 1,
            mgmt_ebitda_m=round(mgmt_y, 2),
            haircut_pct=round(haircut, 3),
            partner_ebitda_m=round(partner_y, 2),
        ))

    n_years = len(years)
    mgmt_exit_ebitda = (
        years[-1].mgmt_ebitda_m if years else y0
    )
    partner_exit_ebitda = (
        years[-1].partner_ebitda_m if years else y0
    )

    mgmt_exit_ev = mgmt_exit_ebitda * inputs.exit_multiple
    partner_exit_ev = (
        partner_exit_ebitda * inputs.exit_multiple
    )
    mgmt_exit_equity = mgmt_exit_ev - inputs.exit_debt_m
    partner_exit_equity = (
        partner_exit_ev - inputs.exit_debt_m
    )

    eq_in = max(1.0, inputs.sponsor_equity_in_m)
    mgmt_moic = mgmt_exit_equity / eq_in
    partner_moic = partner_exit_equity / eq_in

    mgmt_irr = _moic_to_irr(mgmt_moic, n_years)
    partner_irr = _moic_to_irr(partner_moic, n_years)

    delta_moic = mgmt_moic - partner_moic
    delta_irr = mgmt_irr - partner_irr

    if delta_moic <= 0.20:
        note = (
            f"Haircut absorbable: "
            f"{delta_moic:+.2f}x delta. Management "
            "forecast holds within partner-prudent "
            "tolerance — proceed with diligence on the "
            "specific drivers."
        )
    elif delta_moic <= 0.50:
        note = (
            f"Material haircut: "
            f"{delta_moic:+.2f}x MOIC delta "
            f"(IRR {delta_irr:+.1%}). Price the haircut "
            "into entry — counter is "
            f"{(partner_moic / max(0.01, mgmt_moic)):.0%} "
            "of seller's expected enterprise value."
        )
    else:
        note = (
            f"Haircut breaks the underwrite: "
            f"{delta_moic:+.2f}x MOIC delta "
            f"(IRR {delta_irr:+.1%}). Either tighten "
            "forecast assumptions with mgmt — name the "
            "specific lines that get re-baselined — or "
            "pass."
        )

    return ForecastHaircutReport(
        years=years,
        mgmt_exit_ebitda_m=round(mgmt_exit_ebitda, 2),
        partner_exit_ebitda_m=round(
            partner_exit_ebitda, 2),
        mgmt_exit_ev_m=round(mgmt_exit_ev, 2),
        partner_exit_ev_m=round(partner_exit_ev, 2),
        mgmt_exit_equity_m=round(mgmt_exit_equity, 2),
        partner_exit_equity_m=round(
            partner_exit_equity, 2),
        mgmt_moic=round(mgmt_moic, 3),
        partner_moic=round(partner_moic, 3),
        delta_moic=round(delta_moic, 3),
        mgmt_irr=round(mgmt_irr, 4),
        partner_irr=round(partner_irr, 4),
        delta_irr=round(delta_irr, 4),
        partner_note=note,
    )


def render_management_haircut_markdown(
    r: ForecastHaircutReport,
) -> str:
    lines = [
        "# Management forecast haircut",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Mgmt MOIC: {r.mgmt_moic:.2f}x → "
        f"Partner MOIC: {r.partner_moic:.2f}x "
        f"(Δ {r.delta_moic:+.2f}x)",
        f"- Mgmt IRR: {r.mgmt_irr:.1%} → "
        f"Partner IRR: {r.partner_irr:.1%} "
        f"(Δ {r.delta_irr:+.1%})",
        f"- Mgmt exit EV: ${r.mgmt_exit_ev_m:.0f}M → "
        f"Partner exit EV: ${r.partner_exit_ev_m:.0f}M",
        "",
        "| Year | Mgmt EBITDA | Haircut | Partner EBITDA |",
        "|---|---|---|---|",
    ]
    for y in r.years:
        lines.append(
            f"| Y{y.year} | ${y.mgmt_ebitda_m:.2f}M | "
            f"{y.haircut_pct:.0%} | "
            f"${y.partner_ebitda_m:.2f}M |"
        )
    return "\n".join(lines)
