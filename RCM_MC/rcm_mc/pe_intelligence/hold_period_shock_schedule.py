"""Hold-period shock schedule — year-by-year regulatory EBITDA hit.

Partner statement: "I don't need the worst-case total. I
need the worst *year*. The covenant trips on one year's
EBITDA, not on the five-year NPV."

Existing modules produce point-in-time shocks:

- `obbba_sequestration_stress` — each shock returns a single
  dollar + percent-of-base impact.
- `healthcare_regulatory_calendar` — lists events by
  effective year.
- `regulatory_stress` — individual shock functions
  (CMS IPPS cut, Medicaid freeze, 340B reduction, etc.).

What partners actually want during diligence is the **year-
by-year trajectory** — which shocks land in which year of
the hold, what's the cumulative EBITDA erosion by year, and
what's the *worst single year*. Covenant trip risk isn't
about the cumulative NPV; it's about the year EBITDA drops
below the leverage-trip threshold.

This module composes multi-shock, multi-year impact:

1. Caller specifies a **hold window** (start year, length).
2. Caller specifies which shocks are expected to land in
   which year (default: partner-judgment schedule).
3. For each year, the module sums the impact of shocks
   landing that year and the residual from prior years.
4. Residual is configurable — OBBBA-style cuts are
   **permanent** (no recovery); short-term shocks may
   dissipate.

Output highlights:

- **Year-by-year EBITDA floor** relative to base.
- **Worst single-year EBITDA** and the covenant ratio
  implication (leverage × year-worst EBITDA).
- **Partner note**: covenant trip / re-price / thesis
  survives, depending on severity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .obbba_sequestration_stress import (
    RegulatoryStressInputs,
    RegulatoryShock,
    _shock_obbba,
    _shock_sequestration,
    _shock_site_neutral,
    _shock_state_medicaid_shift,
)


# Default partner-judgment schedule of when each shock lands.
# Years relative to hold start (0 = close year).
# Each entry: (shock_name, relative_year, is_permanent, probability).
DEFAULT_SCHEDULE: List[Tuple[str, int, bool, float]] = [
    ("obbba_medicare_cut_3pct", 0, True, 0.70),
    ("sequestration_extended_2pct", 1, True, 0.85),
    ("site_neutral_hopd", 2, True, 0.50),
    ("state_medicaid_shift", 3, True, 0.55),
]


SHOCK_BUILDERS: Dict[str, Callable[[RegulatoryStressInputs],
                                    RegulatoryShock]] = {
    "obbba_medicare_cut_3pct": _shock_obbba,
    "sequestration_extended_2pct": _shock_sequestration,
    "site_neutral_hopd": _shock_site_neutral,
    "state_medicaid_shift": _shock_state_medicaid_shift,
}


@dataclass
class HoldShockInputs:
    """Regulatory stress inputs + hold window + optional schedule."""
    stress: RegulatoryStressInputs = field(
        default_factory=lambda: RegulatoryStressInputs(
            subsector="hospital", revenue_m=500.0, ebitda_m=75.0,
        )
    )
    hold_start_year: int = 2026
    hold_years: int = 5
    schedule: Optional[List[Tuple[str, int, bool, float]]] = None
    leverage_multiple: float = 5.5        # for covenant trip calc
    covenant_max_leverage: float = 7.0


@dataclass
class ShockYear:
    year: int
    shocks_landing: List[str] = field(default_factory=list)
    annual_new_impact_m: float = 0.0
    cumulative_impact_m: float = 0.0
    ebitda_floor_m: float = 0.0
    leverage_at_year_m: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "shocks_landing": list(self.shocks_landing),
            "annual_new_impact_m": self.annual_new_impact_m,
            "cumulative_impact_m": self.cumulative_impact_m,
            "ebitda_floor_m": self.ebitda_floor_m,
            "leverage_at_year_m": self.leverage_at_year_m,
        }


@dataclass
class HoldShockSchedule:
    years: List[ShockYear] = field(default_factory=list)
    worst_year: Optional[int] = None
    worst_year_ebitda_m: float = 0.0
    worst_year_leverage: float = 0.0
    covenant_trip_year: Optional[int] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "years": [y.to_dict() for y in self.years],
            "worst_year": self.worst_year,
            "worst_year_ebitda_m": self.worst_year_ebitda_m,
            "worst_year_leverage": self.worst_year_leverage,
            "covenant_trip_year": self.covenant_trip_year,
            "partner_note": self.partner_note,
        }


def build_hold_shock_schedule(
    inputs: HoldShockInputs,
) -> HoldShockSchedule:
    schedule = inputs.schedule or DEFAULT_SCHEDULE
    base_ebitda = max(0.01, inputs.stress.ebitda_m)
    # Initial debt is leverage × base EBITDA.
    debt_m = inputs.leverage_multiple * base_ebitda

    # Expected-value impact per shock (probability × modeled $M).
    shock_impacts: Dict[str, Tuple[float, bool]] = {}
    for name, _rel_year, is_permanent, prob in schedule:
        builder = SHOCK_BUILDERS.get(name)
        if builder is None:
            continue
        shock = builder(inputs.stress)
        shock_impacts[name] = (
            shock.ebitda_impact_m * prob,
            is_permanent,
        )

    # Map absolute year → list of landing shocks.
    by_year: Dict[int, List[str]] = {}
    for name, rel_year, _is_permanent, _prob in schedule:
        by_year.setdefault(inputs.hold_start_year + rel_year, [])
        by_year[inputs.hold_start_year + rel_year].append(name)

    years: List[ShockYear] = []
    cumulative = 0.0
    for y_offset in range(inputs.hold_years):
        year = inputs.hold_start_year + y_offset
        landing = by_year.get(year, [])
        annual_new = 0.0
        for name in landing:
            impact, is_permanent = shock_impacts.get(
                name, (0.0, True)
            )
            annual_new += impact
        cumulative += annual_new
        ebitda_floor = max(0.0, base_ebitda - cumulative)
        leverage_at_year = debt_m / max(0.01, ebitda_floor)
        years.append(ShockYear(
            year=year,
            shocks_landing=list(landing),
            annual_new_impact_m=round(annual_new, 2),
            cumulative_impact_m=round(cumulative, 2),
            ebitda_floor_m=round(ebitda_floor, 2),
            leverage_at_year_m=round(leverage_at_year, 2),
        ))

    # Worst year = lowest EBITDA floor (= highest leverage).
    worst_year_obj = min(years, key=lambda y: y.ebitda_floor_m,
                          default=None)
    worst_year = worst_year_obj.year if worst_year_obj else None
    worst_ebitda = (worst_year_obj.ebitda_floor_m
                    if worst_year_obj else 0.0)
    worst_leverage = (worst_year_obj.leverage_at_year_m
                      if worst_year_obj else 0.0)

    # Covenant trip detection.
    covenant_trip = None
    for y in years:
        if y.leverage_at_year_m > inputs.covenant_max_leverage:
            covenant_trip = y.year
            break

    if covenant_trip is not None:
        note = (f"Covenant trip projected in {covenant_trip}: "
                f"leverage reaches "
                f"{next(y for y in years if y.year == covenant_trip).leverage_at_year_m:.2f}x "
                f"vs. {inputs.covenant_max_leverage:.1f}x max. "
                "Partner: widen cov package or re-price equity.")
    elif worst_leverage > inputs.covenant_max_leverage * 0.9:
        note = (f"Worst-year leverage {worst_leverage:.2f}x "
                f"approaches covenant ceiling "
                f"{inputs.covenant_max_leverage:.1f}x. Partner: "
                "stress the schedule with higher shock "
                "probabilities.")
    elif cumulative / max(0.01, base_ebitda) > 0.15:
        note = (f"Cumulative regulatory erosion "
                f"${cumulative:,.1f}M "
                f"({cumulative/base_ebitda*100:.0f}% of base "
                "EBITDA). Partner: bake into base case, not "
                "bear.")
    else:
        note = (f"Regulatory shocks contained at "
                f"${cumulative:,.1f}M cumulative. Partner: "
                "standard stress; proceed on current thesis.")

    return HoldShockSchedule(
        years=years,
        worst_year=worst_year,
        worst_year_ebitda_m=round(worst_ebitda, 2),
        worst_year_leverage=round(worst_leverage, 2),
        covenant_trip_year=covenant_trip,
        partner_note=note,
    )


def render_hold_shock_schedule_markdown(
    s: HoldShockSchedule,
) -> str:
    lines = [
        "# Hold-period regulatory shock schedule",
        "",
        f"_{s.partner_note}_",
        "",
        f"- Worst year: {s.worst_year} "
        f"(EBITDA ${s.worst_year_ebitda_m:,.1f}M, "
        f"leverage {s.worst_year_leverage:.2f}x)",
        f"- Covenant trip year: "
        f"{s.covenant_trip_year or 'none projected'}",
        "",
        "| Year | Shocks landing | Annual $M | Cumulative $M | "
        "EBITDA floor | Leverage |",
        "|---|---|---|---|---|---|",
    ]
    for y in s.years:
        shocks = ", ".join(y.shocks_landing) or "—"
        lines.append(
            f"| {y.year} | {shocks} | "
            f"{y.annual_new_impact_m:,.1f} | "
            f"{y.cumulative_impact_m:,.1f} | "
            f"{y.ebitda_floor_m:,.1f} | "
            f"{y.leverage_at_year_m:.2f}x |"
        )
    return "\n".join(lines)
