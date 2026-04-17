"""Synergy modeler — platform + add-on deal arithmetic.

For platform/roll-up deals, partners size synergies at several
levels: revenue (cross-sell), cost (G&A consolidation, RCM scale),
capex avoidance (shared IT, shared supply contracts), and working
capital (DSO/DPO terms improve at scale).

This module provides the partner-prudent arithmetic for those
synergies, plus a haircut schedule — synergies take time, and the
market has consistently shown that announced synergies achieve
~60-75% of plan when actually integrated.

Functions:

- :func:`size_cost_synergies` — % of combined SG&A addressable by
  consolidation.
- :func:`size_revenue_synergies` — cross-sell revenue lift.
- :func:`realization_schedule` — year-by-year synergy ramp.
- :func:`apply_partner_haircut` — conservative partner haircut on
  stated synergies (default 35%).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SynergyInputs:
    platform_revenue: float            # $
    platform_ebitda: float             # $
    addon_revenue: float
    addon_ebitda: float
    addon_sga_pct: float = 0.12        # fraction of revenue
    platform_sga_pct: float = 0.10
    cross_sell_pct: float = 0.05       # of combined revenue
    rcm_margin_uplift_bps: float = 150  # bps from scale
    procurement_savings_pct: float = 0.03   # fraction of COGS
    addon_cogs_pct: float = 0.40
    partner_haircut: float = 0.35      # 35% haircut on stated synergies


@dataclass
class SynergyResult:
    gross_cost_synergies: float
    gross_revenue_synergies: float
    gross_rcm_synergies: float
    gross_procurement_synergies: float
    gross_total: float
    partner_haircut_pct: float
    partner_net_total: float
    combined_ebitda: float
    combined_revenue: float
    implied_pro_forma_margin: float
    year_schedule: List[Dict[str, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_cost_synergies": self.gross_cost_synergies,
            "gross_revenue_synergies": self.gross_revenue_synergies,
            "gross_rcm_synergies": self.gross_rcm_synergies,
            "gross_procurement_synergies": self.gross_procurement_synergies,
            "gross_total": self.gross_total,
            "partner_haircut_pct": self.partner_haircut_pct,
            "partner_net_total": self.partner_net_total,
            "combined_ebitda": self.combined_ebitda,
            "combined_revenue": self.combined_revenue,
            "implied_pro_forma_margin": self.implied_pro_forma_margin,
            "year_schedule": list(self.year_schedule),
        }


# ── Sizing helpers ──────────────────────────────────────────────────

def size_cost_synergies(inputs: SynergyInputs,
                        *, consolidation_pct: float = 0.40) -> float:
    """Estimate cost synergies.

    Assumes ``consolidation_pct`` of addon SG&A is addressable through
    consolidation with the platform. Partners should verify — acute
    care has low SG&A consolidation; MSOs have high.
    """
    addon_sga = inputs.addon_revenue * inputs.addon_sga_pct
    return addon_sga * consolidation_pct


def size_revenue_synergies(inputs: SynergyInputs,
                           *, margin_on_cross_sell: float = 0.30) -> float:
    """Revenue synergies = cross_sell % × combined revenue × margin."""
    combined_rev = inputs.platform_revenue + inputs.addon_revenue
    incremental_rev = combined_rev * inputs.cross_sell_pct
    return incremental_rev * margin_on_cross_sell


def size_rcm_synergies(inputs: SynergyInputs) -> float:
    """RCM-scale margin uplift applies to the addon revenue."""
    return inputs.addon_revenue * (inputs.rcm_margin_uplift_bps / 10_000.0)


def size_procurement_synergies(inputs: SynergyInputs) -> float:
    """Procurement synergies = savings % × addon COGS."""
    addon_cogs = inputs.addon_revenue * inputs.addon_cogs_pct
    return addon_cogs * inputs.procurement_savings_pct


# ── Realization schedule ────────────────────────────────────────────

_DEFAULT_REALIZATION = [0.20, 0.55, 0.85, 1.00, 1.00]  # 5-year ramp


def realization_schedule(
    total_synergies: float,
    *,
    ramp: Optional[List[float]] = None,
) -> List[Dict[str, float]]:
    """Build a year-by-year synergy realization schedule.

    ``ramp`` is a list of cumulative % of run-rate by year. Default
    5-year ramp: 20% y1, 55% y2, 85% y3, 100% y4+.
    """
    ramp = ramp or _DEFAULT_REALIZATION
    out: List[Dict[str, float]] = []
    for i, cumulative_pct in enumerate(ramp, start=1):
        out.append({
            "year": i,
            "cumulative_pct": cumulative_pct,
            "realized_dollars": total_synergies * cumulative_pct,
        })
    return out


# ── Orchestrator ────────────────────────────────────────────────────

def size_synergies(inputs: SynergyInputs,
                   *, consolidation_pct: float = 0.40) -> SynergyResult:
    """Size all synergies, apply partner haircut, build schedule."""
    cost = size_cost_synergies(inputs, consolidation_pct=consolidation_pct)
    rev = size_revenue_synergies(inputs)
    rcm = size_rcm_synergies(inputs)
    procure = size_procurement_synergies(inputs)
    gross = cost + rev + rcm + procure
    net = gross * (1 - inputs.partner_haircut)
    combined_ebitda = inputs.platform_ebitda + inputs.addon_ebitda + net
    combined_revenue = inputs.platform_revenue + inputs.addon_revenue
    margin = (combined_ebitda / combined_revenue
              if combined_revenue > 0 else 0.0)
    schedule = realization_schedule(net)
    return SynergyResult(
        gross_cost_synergies=cost,
        gross_revenue_synergies=rev,
        gross_rcm_synergies=rcm,
        gross_procurement_synergies=procure,
        gross_total=gross,
        partner_haircut_pct=inputs.partner_haircut,
        partner_net_total=net,
        combined_ebitda=combined_ebitda,
        combined_revenue=combined_revenue,
        implied_pro_forma_margin=margin,
        year_schedule=schedule,
    )


def apply_partner_haircut(
    stated_synergy: float,
    *,
    haircut: float = 0.35,
) -> float:
    """Apply a conservative haircut to announced synergies.

    Default 35% — aligned with healthcare-PE roll-up outcomes 2018-2024
    where achieved synergies averaged 60-75% of announced.
    """
    return stated_synergy * (1 - haircut)
