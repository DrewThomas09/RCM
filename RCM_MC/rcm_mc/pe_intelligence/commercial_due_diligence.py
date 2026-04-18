"""Commercial due diligence — market size, share, competitive position.

Partners separate "is the business good" (CDD) from "can we make it
better" (operational DD). CDD answers: how big is the market, how
fast is it growing, who are the competitors, and where does this
target fit?

This module provides scaffolding:

- :func:`market_size_sanity` — checks total addressable market
  numbers against partner-calibrated ceilings for HC subsectors.
- :func:`market_share_check` — target share of TAM.
- :func:`competitive_position` — categorical position based on share
  and differentiation.
- :func:`growth_plausibility` — flags growth assumptions above
  subsector norms.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Subsector TAM ceilings in US $B (partner-calibrated 2024 figures).
_US_TAM_BY_SECTOR: Dict[str, float] = {
    "acute_care": 1400.0,       # $1.4T US hospital market
    "asc": 45.0,
    "behavioral": 180.0,
    "post_acute": 250.0,
    "specialty": 90.0,
    "outpatient": 350.0,
    "critical_access": 15.0,
}

# Subsector long-run real growth (CAGR, partner prior).
_SECTOR_GROWTH: Dict[str, float] = {
    "acute_care": 0.03,
    "asc": 0.07,
    "behavioral": 0.08,
    "post_acute": 0.04,
    "specialty": 0.05,
    "outpatient": 0.06,
    "critical_access": 0.01,
}


@dataclass
class CDDInputs:
    subsector: str
    stated_tam_usd_b: Optional[float] = None        # as stated in memo
    target_revenue_m: Optional[float] = None
    target_market_share: Optional[float] = None     # fraction
    stated_market_growth_pct: Optional[float] = None
    competitive_intensity: Optional[str] = None     # "low" | "moderate" | "high"
    differentiation: Optional[str] = None           # "low" | "moderate" | "high"


@dataclass
class CDDFinding:
    check: str
    status: str                    # "pass" | "flag" | "unknown"
    detail: str
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check,
            "status": self.status,
            "detail": self.detail,
            "partner_note": self.partner_note,
        }


def _subsector_key(s: str) -> str:
    alias = {
        "hospital": "acute_care", "acute": "acute_care",
        "snf": "post_acute", "ltach": "post_acute",
        "psych": "behavioral", "clinic": "outpatient",
        "cah": "critical_access",
    }
    k = s.lower().strip().replace("-", "_").replace(" ", "_")
    return alias.get(k, k)


# ── Checks ──────────────────────────────────────────────────────────

def market_size_sanity(inputs: CDDInputs) -> CDDFinding:
    """Flag TAM claims that exceed the US-subsector ceiling."""
    if inputs.stated_tam_usd_b is None:
        return CDDFinding(
            check="tam_size", status="unknown",
            detail="No TAM figure provided.",
        )
    ceiling = _US_TAM_BY_SECTOR.get(_subsector_key(inputs.subsector))
    if ceiling is None:
        return CDDFinding(
            check="tam_size", status="unknown",
            detail=f"No TAM ceiling registered for '{inputs.subsector}'.",
        )
    if inputs.stated_tam_usd_b > ceiling * 1.2:
        return CDDFinding(
            check="tam_size", status="flag",
            detail=(f"Stated TAM ${inputs.stated_tam_usd_b:.1f}B exceeds "
                    f"the US ceiling for {inputs.subsector} (${ceiling:.1f}B)."),
            partner_note=("TAM inflation is a classic red flag in CDD. "
                          "Press for the bottom-up build."),
        )
    return CDDFinding(
        check="tam_size", status="pass",
        detail=(f"Stated TAM ${inputs.stated_tam_usd_b:.1f}B is within the "
                f"US ceiling for {inputs.subsector} (${ceiling:.1f}B)."),
    )


def market_share_check(inputs: CDDInputs) -> CDDFinding:
    """Compute implied market share from revenue + TAM; flag if
    implausibly high (> 20% of US subsector = not credible without
    a named dominant position)."""
    if (inputs.target_revenue_m is None
            or inputs.stated_tam_usd_b is None
            or inputs.stated_tam_usd_b <= 0):
        return CDDFinding(
            check="market_share", status="unknown",
            detail="Insufficient data for share calculation.",
        )
    implied_share = (inputs.target_revenue_m / 1000.0) / inputs.stated_tam_usd_b
    if implied_share > 0.20:
        return CDDFinding(
            check="market_share", status="flag",
            detail=(f"Implied share {implied_share*100:.1f}% of stated TAM. "
                    "This is dominant-player territory for a healthcare "
                    "subsector."),
            partner_note=("Validate the TAM denominator; dominance is "
                          "rare and usually flagged by antitrust."),
        )
    if implied_share > 0.05:
        return CDDFinding(
            check="market_share", status="pass",
            detail=f"Implied share {implied_share*100:.1f}% — regional leader profile.",
        )
    return CDDFinding(
        check="market_share", status="pass",
        detail=f"Implied share {implied_share*100:.1f}% — fragmented-market participant.",
    )


def growth_plausibility(inputs: CDDInputs) -> CDDFinding:
    """Flag stated market growth that exceeds subsector norm by >3pp."""
    if inputs.stated_market_growth_pct is None:
        return CDDFinding(
            check="growth_plausibility", status="unknown",
            detail="No market growth rate provided.",
        )
    norm = _SECTOR_GROWTH.get(_subsector_key(inputs.subsector))
    if norm is None:
        return CDDFinding(
            check="growth_plausibility", status="unknown",
            detail=f"No growth norm registered for '{inputs.subsector}'.",
        )
    g = float(inputs.stated_market_growth_pct)
    # Accept fraction or percent.
    if g > 1.5:
        g /= 100.0
    if g > norm + 0.03:
        return CDDFinding(
            check="growth_plausibility", status="flag",
            detail=(f"Stated market growth {g*100:.1f}% exceeds "
                    f"{inputs.subsector} norm ({norm*100:.1f}%)."),
            partner_note=("Named demographic or regulatory tailwinds "
                          "should justify deviation from norm."),
        )
    return CDDFinding(
        check="growth_plausibility", status="pass",
        detail=f"Stated growth {g*100:.1f}% is consistent with subsector norm.",
    )


# ── Competitive position ────────────────────────────────────────────

_POSITION_MATRIX: Dict[Tuple[str, str], str] = {
    ("high", "low"): "leader",
    ("high", "moderate"): "leader",
    ("high", "high"): "contested_leader",
    ("moderate", "low"): "solid_challenger",
    ("moderate", "moderate"): "challenger",
    ("moderate", "high"): "contested_challenger",
    ("low", "low"): "niche",
    ("low", "moderate"): "niche_under_pressure",
    ("low", "high"): "weak_position",
}


def competitive_position(inputs: CDDInputs) -> CDDFinding:
    if (not inputs.differentiation or not inputs.competitive_intensity):
        return CDDFinding(
            check="competitive_position", status="unknown",
            detail="Differentiation or competitive intensity not reported.",
        )
    key = (inputs.differentiation.lower().strip(),
           inputs.competitive_intensity.lower().strip())
    position = _POSITION_MATRIX.get(key, "unclear")
    note = {
        "leader": "Well-positioned — defend via scale / network economics.",
        "contested_leader": "Leader in a hot category; watch for multiple compression.",
        "solid_challenger": "Room to grow into leader seat with focused M&A.",
        "challenger": "Mid-pack — differentiation play required.",
        "contested_challenger": "Heavy competition with no clear edge — question thesis.",
        "niche": "Niche is fine if the niche is defensible.",
        "niche_under_pressure": "Niche + competition means margin risk.",
        "weak_position": "Weak position — do not pay strategic value.",
        "unclear": "Competitive position unclear from inputs.",
    }.get(position, "")
    status = "pass" if position in ("leader", "solid_challenger", "niche") else "flag"
    return CDDFinding(
        check="competitive_position", status=status,
        detail=f"Position: {position} (differentiation={inputs.differentiation}, "
               f"intensity={inputs.competitive_intensity}).",
        partner_note=note,
    )


# ── Orchestrator ────────────────────────────────────────────────────

def run_cdd_checks(inputs: CDDInputs) -> List[CDDFinding]:
    """Run every CDD check; return findings."""
    return [
        market_size_sanity(inputs),
        market_share_check(inputs),
        growth_plausibility(inputs),
        competitive_position(inputs),
    ]
