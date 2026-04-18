"""Regulatory stress — model CMS/state rule-change EBITDA impact.

This module goes beyond the static `regulatory_watch.py` registry:
given a deal profile, it computes the $ EBITDA impact of common
regulatory shocks:

- CMS IPPS / OPPS rate cut by N bps.
- Medicaid rate freeze / cut.
- 340B program reduction.
- Site-neutral payment policy expansion.
- SNF VBP withhold acceleration.

These are partner-facing ballparks; the deal team substitutes real
model outputs once they exist.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RegulatoryStressInputs:
    annual_revenue: float
    medicare_revenue_share: float = 0.0    # fraction
    medicaid_revenue_share: float = 0.0
    commercial_revenue_share: float = 0.0
    hopd_revenue_share: float = 0.0        # site-neutral applicable
    share_340b_of_ebitda: float = 0.0      # fraction, e.g. 0.15
    base_ebitda: float = 0.0
    hospital_type: Optional[str] = None


@dataclass
class StressShock:
    scenario: str
    rule: str
    dollar_ebitda_impact: float             # negative = reduces EBITDA
    pct_of_ebitda_impact: float
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "rule": self.rule,
            "dollar_ebitda_impact": self.dollar_ebitda_impact,
            "pct_of_ebitda_impact": self.pct_of_ebitda_impact,
            "partner_note": self.partner_note,
        }


def _pct_of_ebitda(dollars: float, ebitda: float) -> float:
    if ebitda <= 0:
        return 0.0
    return dollars / ebitda


def shock_cms_ipps_cut(
    inputs: RegulatoryStressInputs,
    *,
    bps: int = 100,
) -> StressShock:
    """CMS IPPS rate cut by ``bps``. Hits medicare revenue at 100%
    flow-through to EBITDA."""
    medicare_rev = inputs.annual_revenue * inputs.medicare_revenue_share
    impact = -medicare_rev * (bps / 10_000.0)
    pct = _pct_of_ebitda(impact, inputs.base_ebitda)
    if abs(pct) >= 0.20:
        note = "Material — likely triggers covenant conversation."
    elif abs(pct) >= 0.08:
        note = "Meaningful — trim leverage or accept tighter headroom."
    else:
        note = "Absorbable — budget item."
    return StressShock(
        scenario="cms_ipps_cut",
        rule=f"CMS IPPS down-rate by {bps} bps",
        dollar_ebitda_impact=impact,
        pct_of_ebitda_impact=pct,
        partner_note=note,
    )


def shock_medicaid_freeze(
    inputs: RegulatoryStressInputs,
    *,
    years_frozen: int = 2,
    annual_inflation: float = 0.025,
) -> StressShock:
    """Medicaid rate freeze for ``years_frozen`` years. Impact is the
    foregone inflation.
    """
    medicaid_rev = inputs.annual_revenue * inputs.medicaid_revenue_share
    # Foregone growth is roughly: rev * inflation * years (simple).
    impact = -medicaid_rev * annual_inflation * years_frozen
    pct = _pct_of_ebitda(impact, inputs.base_ebitda)
    note = ("Foregone Medicaid growth stacks over time; base case "
            "should flat-line, not inflate.")
    return StressShock(
        scenario="medicaid_freeze",
        rule=f"Medicaid rate frozen for {years_frozen}yr",
        dollar_ebitda_impact=impact,
        pct_of_ebitda_impact=pct,
        partner_note=note,
    )


def shock_340b_reduction(
    inputs: RegulatoryStressInputs,
    *,
    reduction_pct: float = 0.50,
) -> StressShock:
    """340B program reduction by ``reduction_pct`` (fraction of current
    340B benefit)."""
    loss_ebitda = inputs.base_ebitda * inputs.share_340b_of_ebitda * reduction_pct
    impact = -loss_ebitda
    pct = _pct_of_ebitda(impact, inputs.base_ebitda)
    if inputs.share_340b_of_ebitda >= 0.15:
        note = "Material 340B exposure — build an ex-340B sensitivity."
    else:
        note = "Limited exposure — budget item."
    return StressShock(
        scenario="340b_reduction",
        rule=f"340B benefit cut by {reduction_pct*100:.0f}%",
        dollar_ebitda_impact=impact,
        pct_of_ebitda_impact=pct,
        partner_note=note,
    )


def shock_site_neutral(
    inputs: RegulatoryStressInputs,
    *,
    hopd_rate_compression_pct: float = 0.20,
) -> StressShock:
    """Site-neutral policy compresses HOPD rates by
    ``hopd_rate_compression_pct``."""
    hopd_rev = inputs.annual_revenue * inputs.hopd_revenue_share
    impact = -hopd_rev * hopd_rate_compression_pct
    pct = _pct_of_ebitda(impact, inputs.base_ebitda)
    note = ("Site-neutral policy is a slow squeeze; don't rely on HOPD "
            "rate premium as a forward assumption.")
    return StressShock(
        scenario="site_neutral",
        rule=f"HOPD rate compression by {hopd_rate_compression_pct*100:.0f}%",
        dollar_ebitda_impact=impact,
        pct_of_ebitda_impact=pct,
        partner_note=note,
    )


def shock_snf_vbp_accel(
    inputs: RegulatoryStressInputs,
    *,
    additional_withhold_pct: float = 0.02,
) -> Optional[StressShock]:
    """SNF VBP withhold acceleration — only relevant for SNF/post-acute
    deals."""
    if (inputs.hospital_type or "").lower() not in ("post_acute", "snf"):
        return None
    medicare_rev = inputs.annual_revenue * inputs.medicare_revenue_share
    impact = -medicare_rev * additional_withhold_pct
    pct = _pct_of_ebitda(impact, inputs.base_ebitda)
    note = ("SNF VBP withhold is quality-dependent — facility rating "
            "drives whether this bites.")
    return StressShock(
        scenario="snf_vbp_accel",
        rule=f"Additional SNF VBP withhold {additional_withhold_pct*100:.1f}%",
        dollar_ebitda_impact=impact,
        pct_of_ebitda_impact=pct,
        partner_note=note,
    )


# ── Orchestrator ────────────────────────────────────────────────────

def run_regulatory_stresses(
    inputs: RegulatoryStressInputs,
) -> List[StressShock]:
    """Run every relevant regulatory stress. Returns a list ordered by
    absolute $ impact descending."""
    shocks: List[StressShock] = []
    shocks.append(shock_cms_ipps_cut(inputs, bps=100))
    shocks.append(shock_cms_ipps_cut(inputs, bps=300))
    shocks.append(shock_medicaid_freeze(inputs))
    shocks.append(shock_340b_reduction(inputs))
    shocks.append(shock_site_neutral(inputs))
    snf = shock_snf_vbp_accel(inputs)
    if snf is not None:
        shocks.append(snf)
    shocks.sort(key=lambda s: -abs(s.dollar_ebitda_impact))
    return shocks


def summarize_regulatory_exposure(
    shocks: List[StressShock],
    base_ebitda: float,
) -> Dict[str, Any]:
    """Summarize the regulatory stress panel for the narrative layer."""
    if not shocks:
        return {"headline": "No regulatory stresses evaluated."}
    worst = min(shocks, key=lambda s: s.dollar_ebitda_impact)
    total_negative = sum(s.dollar_ebitda_impact for s in shocks
                         if s.dollar_ebitda_impact < 0)
    return {
        "n_shocks": len(shocks),
        "worst_scenario": worst.scenario,
        "worst_impact_dollars": worst.dollar_ebitda_impact,
        "worst_impact_pct": worst.pct_of_ebitda_impact,
        "total_negative": total_negative,
        "headline": (f"Worst-case reg shock is {worst.scenario}: "
                     f"${worst.dollar_ebitda_impact:,.0f} "
                     f"({worst.pct_of_ebitda_impact*100:.1f}% of EBITDA)."),
    }
