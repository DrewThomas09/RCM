"""Cash conversion analysis.

Partners care about how much of EBITDA shows up as free cash flow.
Cash conversion = FCF / EBITDA. Healthcare-PE targets vary by subsector:

- ASC / outpatient: 70-85% (low capex, low WC drag).
- Acute care: 50-65% (capex-heavy, WC-heavy).
- Behavioral: 60-75%.
- Post-acute: 55-70%.

Low cash conversion means the headline EBITDA number overstates the
cash available for debt service and distributions. A 50% conversion
deal at 6x leverage is materially tighter than a 75% conversion deal
at 6x.

Functions:

- :func:`cash_conversion_ratio` — FCF / EBITDA given inputs.
- :func:`expected_conversion_by_subsector` — partner target range.
- :func:`assess_conversion` — verdict + partner note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class CashConversionInputs:
    ebitda: float
    capex: Optional[float] = None
    working_capital_change: Optional[float] = None   # positive = WC absorbed cash
    taxes_paid: Optional[float] = None
    interest_paid: Optional[float] = None


# Per-subsector conversion expectations: (low, mid, high)
_CONVERSION_BY_SECTOR: Dict[str, Tuple[float, float, float]] = {
    "acute_care": (0.50, 0.60, 0.68),
    "asc": (0.70, 0.78, 0.85),
    "behavioral": (0.60, 0.68, 0.75),
    "post_acute": (0.55, 0.63, 0.70),
    "specialty": (0.60, 0.68, 0.75),
    "outpatient": (0.65, 0.73, 0.82),
    "critical_access": (0.40, 0.50, 0.60),
}


def expected_conversion_by_subsector(subsector: str) -> Optional[Tuple[float, float, float]]:
    key = subsector.lower().strip()
    aliases = {
        "hospital": "acute_care", "acute": "acute_care",
        "snf": "post_acute", "ltach": "post_acute", "rehab": "post_acute",
        "psych": "behavioral", "mental_health": "behavioral",
        "clinic": "outpatient", "physician_practice": "outpatient",
        "cah": "critical_access",
    }
    key = aliases.get(key, key)
    return _CONVERSION_BY_SECTOR.get(key)


def cash_conversion_ratio(inputs: CashConversionInputs) -> Optional[float]:
    """Compute simplified FCF-to-EBITDA ratio.

    FCF ≈ EBITDA − capex − Δworking_capital − taxes. Interest is
    below-the-line; it's measured at equity level, not EV level.
    """
    if inputs.ebitda <= 0:
        return None
    fcf = inputs.ebitda
    if inputs.capex is not None:
        fcf -= inputs.capex
    if inputs.working_capital_change is not None:
        fcf -= inputs.working_capital_change
    if inputs.taxes_paid is not None:
        fcf -= inputs.taxes_paid
    return fcf / inputs.ebitda


@dataclass
class ConversionAssessment:
    conversion: Optional[float]
    expected_range: Optional[Tuple[float, float, float]]
    status: str            # "above" | "in_band" | "below" | "unknown"
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversion": self.conversion,
            "expected_range": list(self.expected_range) if self.expected_range else None,
            "status": self.status,
            "partner_note": self.partner_note,
        }


def assess_conversion(
    inputs: CashConversionInputs,
    *,
    subsector: Optional[str] = None,
) -> ConversionAssessment:
    conv = cash_conversion_ratio(inputs)
    if conv is None:
        return ConversionAssessment(
            conversion=None, expected_range=None, status="unknown",
            partner_note="Insufficient data to compute cash conversion.",
        )
    if subsector is None:
        return ConversionAssessment(
            conversion=conv, expected_range=None, status="unknown",
            partner_note=f"Cash conversion is {conv*100:.1f}%. Subsector not provided.",
        )
    band = expected_conversion_by_subsector(subsector)
    if band is None:
        return ConversionAssessment(
            conversion=conv, expected_range=None, status="unknown",
            partner_note=(f"Cash conversion {conv*100:.1f}% — no subsector "
                          "band for comparison."),
        )
    low, mid, high = band
    if conv > high:
        status = "above"
        note = (f"Cash conversion of {conv*100:.1f}% is above the peer "
                "ceiling — check for one-time working-capital release.")
    elif conv >= low:
        status = "in_band"
        note = f"Cash conversion of {conv*100:.1f}% is consistent with peers ({low*100:.0f}–{high*100:.0f}%)."
    else:
        status = "below"
        note = (f"Cash conversion of {conv*100:.1f}% is below the peer floor — "
                "capex or working capital is absorbing EBITDA faster than expected.")
    return ConversionAssessment(
        conversion=conv, expected_range=band,
        status=status, partner_note=note,
    )
