"""Cycle timing pricing check — are we paying peak for peak?

Partner discipline: at cycle peak, buyers pay peak multiples on
peak EBITDA. The math is a double-count: normal EBITDA × normal
multiple looks fine, but peak × peak overstates by 2 turns of
multiple or more.

This module:

- Classifies where we are in the cycle (early / mid / peak /
  contraction).
- Tests whether the entry multiple is at or above the subsector
  cycle-average.
- Tests whether the entry EBITDA appears to be at or above the
  2-3 year trailing average (peak EBITDA detection).
- Flags the compound overpayment if BOTH are elevated.
- Produces a recommended entry-multiple haircut if peak × peak.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Partner-approximated subsector cycle-average exit multiples.
SUBSECTOR_CYCLE_AVG_MULT = {
    "hospital": 8.5,
    "specialty_practice": 10.5,
    "outpatient_asc": 12.5,
    "home_health": 11.0,
    "dme_supplier": 9.5,
    "physician_staffing": 8.0,
}


@dataclass
class CyclePricingInputs:
    subsector: str = ""
    cycle_phase: str = "mid_expansion"      # per regime / cycle_timing
    entry_multiple: float = 11.0
    entry_ebitda_m: float = 0.0
    # Look-back data:
    ebitda_3yr_ago_m: float = 0.0
    ebitda_2yr_ago_m: float = 0.0
    ebitda_1yr_ago_m: float = 0.0
    peer_median_multiple: Optional[float] = None  # override if known


@dataclass
class CyclePricingReport:
    multiple_vs_cycle_avg_pct: float
    ebitda_peak_premium_pct: float
    is_peak_multiple: bool
    is_peak_ebitda: bool
    double_peak: bool
    recommended_entry_multiple_haircut_x: float
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "multiple_vs_cycle_avg_pct": self.multiple_vs_cycle_avg_pct,
            "ebitda_peak_premium_pct": self.ebitda_peak_premium_pct,
            "is_peak_multiple": self.is_peak_multiple,
            "is_peak_ebitda": self.is_peak_ebitda,
            "double_peak": self.double_peak,
            "recommended_entry_multiple_haircut_x":
                self.recommended_entry_multiple_haircut_x,
            "partner_note": self.partner_note,
        }


def check_cycle_pricing(inputs: CyclePricingInputs) -> CyclePricingReport:
    # Multiple vs cycle average.
    cycle_avg = inputs.peer_median_multiple \
        if inputs.peer_median_multiple is not None \
        else SUBSECTOR_CYCLE_AVG_MULT.get(inputs.subsector, 10.5)
    mult_premium = (inputs.entry_multiple - cycle_avg) / cycle_avg

    # Is multiple "peak"?
    is_peak_multiple = (
        mult_premium >= 0.10
        and inputs.cycle_phase in ("peak", "mid_expansion")
    )

    # EBITDA vs 3yr trailing average.
    history = [x for x in (inputs.ebitda_3yr_ago_m,
                             inputs.ebitda_2yr_ago_m,
                             inputs.ebitda_1yr_ago_m) if x > 0]
    if history:
        trailing = sum(history) / len(history)
        ebitda_premium = (inputs.entry_ebitda_m - trailing) / trailing
    else:
        ebitda_premium = 0.0
    is_peak_ebitda = ebitda_premium >= 0.15

    double_peak = is_peak_multiple and is_peak_ebitda

    # Recommended haircut: half of multiple premium, expressed in x.
    haircut = 0.0
    if double_peak:
        haircut = (inputs.entry_multiple - cycle_avg) * 0.5
    elif is_peak_multiple:
        haircut = (inputs.entry_multiple - cycle_avg) * 0.25

    if double_peak:
        note = (
            f"**Peak × peak trap**: entry multiple "
            f"{inputs.entry_multiple:.1f}x is {mult_premium*100:.0f}% "
            f"above cycle average; entry EBITDA is "
            f"{ebitda_premium*100:.0f}% above trailing average. "
            "Both at peak compound. Haircut entry multiple by "
            f"~{haircut:.2f}x or pass.")
    elif is_peak_multiple:
        note = (
            f"Multiple is elevated ({inputs.entry_multiple:.1f}x vs "
            f"cycle avg {cycle_avg:.1f}x). EBITDA appears normal — "
            "not peak × peak but partner should walk the exit "
            "multiple assumption.")
    elif is_peak_ebitda:
        note = (
            f"EBITDA appears peak ({ebitda_premium*100:.0f}% above "
            "trailing avg) but multiple is normal. Verify that the "
            "recent EBITDA lift is durable, not cyclical.")
    else:
        note = (
            "Neither multiple nor EBITDA flags as peak. Cycle "
            "timing is not a pricing concern here.")

    return CyclePricingReport(
        multiple_vs_cycle_avg_pct=round(mult_premium * 100, 2),
        ebitda_peak_premium_pct=round(ebitda_premium * 100, 2),
        is_peak_multiple=is_peak_multiple,
        is_peak_ebitda=is_peak_ebitda,
        double_peak=double_peak,
        recommended_entry_multiple_haircut_x=round(haircut, 2),
        partner_note=note,
    )


def render_cycle_pricing_markdown(
    r: CyclePricingReport,
) -> str:
    lines = [
        "# Cycle timing pricing check",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Multiple vs cycle average: "
        f"{r.multiple_vs_cycle_avg_pct:+.1f}%",
        f"- EBITDA vs trailing avg: "
        f"{r.ebitda_peak_premium_pct:+.1f}%",
        f"- Peak multiple: {'yes' if r.is_peak_multiple else 'no'}",
        f"- Peak EBITDA: {'yes' if r.is_peak_ebitda else 'no'}",
        f"- Double peak (trap): "
        f"**{'YES' if r.double_peak else 'no'}**",
        f"- Recommended haircut: "
        f"{r.recommended_entry_multiple_haircut_x:.2f}x",
    ]
    return "\n".join(lines)
