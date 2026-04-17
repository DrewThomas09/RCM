"""OBBBA + sequestration + site-neutral stress with $ impact.

Partners need dollar-specific regulatory stress, not qualitative
"we might lose a bit." Three live-wire regulatory exposures:

1. **OBBBA (Omnibus Budget Balance & Balance-of-Payments Act)** —
   a stand-in name here for multi-year Medicare cut bundles that
   Congress has repeatedly threatened (BBEDCA, PAYGO-trigger,
   sequestration extension). Model as 2-4% Medicare rate cut.
2. **Sequestration** — standard 2% Medicare cut already in place;
   extension to 4% has been proposed in 2024-2026. Hits fee-for-
   service Medicare linearly.
3. **Site-neutral payment** — CMS / congressional push to equalize
   HOPD rates with ASC / physician-office rates for drug
   administration, imaging, evaluation-management. Impact is
   largest for hospital outpatient departments (HOPDs) of
   acute-care hospitals.

This module takes (payer_mix, subsector, revenue) and returns
the expected dollar EBITDA impact under each named shock, as well
as a combined worst-case scenario.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RegulatoryStressInputs:
    subsector: str
    revenue_m: float
    ebitda_m: float
    medicare_ffs_pct: float = 0.30        # % revenue in Medicare FFS
    medicare_advantage_pct: float = 0.10
    hopd_revenue_pct: float = 0.00        # only relevant for hospitals
    asc_revenue_pct: float = 0.00
    # Margin sensitivity: contribution margin on the impacted revenue.
    contribution_margin: float = 0.50


@dataclass
class RegulatoryShock:
    name: str
    description: str
    revenue_impact_pct: float             # rate cut applied to affected rev
    ebitda_impact_m: float
    ebitda_impact_pct_of_base: float
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "revenue_impact_pct": self.revenue_impact_pct,
            "ebitda_impact_m": self.ebitda_impact_m,
            "ebitda_impact_pct_of_base": self.ebitda_impact_pct_of_base,
            "partner_note": self.partner_note,
        }


@dataclass
class RegulatoryStressReport:
    shocks: List[RegulatoryShock] = field(default_factory=list)
    worst_case_combined_m: float = 0.0
    worst_case_pct: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shocks": [s.to_dict() for s in self.shocks],
            "worst_case_combined_m": self.worst_case_combined_m,
            "worst_case_pct": self.worst_case_pct,
            "partner_note": self.partner_note,
        }


def _impact_m(
    revenue_m: float, exposed_pct: float,
    rate_cut_pct: float, margin: float,
) -> float:
    affected_rev = revenue_m * exposed_pct
    lost_rev = affected_rev * rate_cut_pct
    return lost_rev * margin


def _shock_obbba(inputs: RegulatoryStressInputs) -> RegulatoryShock:
    rate_cut = 0.03                       # 3% mid-range
    ffs = inputs.medicare_ffs_pct
    ma = inputs.medicare_advantage_pct * 0.5  # MA takes partial pass-through
    total_exposed = ffs + ma
    impact = _impact_m(
        inputs.revenue_m, total_exposed, rate_cut,
        inputs.contribution_margin,
    )
    pct = impact / max(0.01, inputs.ebitda_m)
    return RegulatoryShock(
        name="obbba_medicare_cut_3pct",
        description=("3% Medicare cut hits FFS directly and MA via "
                     "partial pass-through."),
        revenue_impact_pct=rate_cut * total_exposed,
        ebitda_impact_m=round(impact, 2),
        ebitda_impact_pct_of_base=round(pct, 4),
        partner_note=(f"OBBBA-style 3% Medicare cut: "
                      f"${impact:,.1f}M EBITDA hit "
                      f"({pct*100:.1f}% of base)."),
    )


def _shock_sequestration(inputs: RegulatoryStressInputs) -> RegulatoryShock:
    rate_cut = 0.02
    total_exposed = inputs.medicare_ffs_pct + 0.5 * inputs.medicare_advantage_pct
    impact = _impact_m(inputs.revenue_m, total_exposed, rate_cut,
                        inputs.contribution_margin)
    pct = impact / max(0.01, inputs.ebitda_m)
    return RegulatoryShock(
        name="sequestration_extended_2pct",
        description=("2% sequestration extension on Medicare FFS + "
                     "50% pass-through MA."),
        revenue_impact_pct=rate_cut * total_exposed,
        ebitda_impact_m=round(impact, 2),
        ebitda_impact_pct_of_base=round(pct, 4),
        partner_note=(f"Sequestration 2% cut: ${impact:,.1f}M EBITDA "
                      f"hit ({pct*100:.1f}% of base)."),
    )


def _shock_site_neutral(inputs: RegulatoryStressInputs) -> RegulatoryShock:
    # Site-neutral is a ~20-25% rate cut on affected HOPD services.
    # Impact scales with hopd_revenue_pct.
    rate_cut = 0.22
    exposed = inputs.hopd_revenue_pct
    impact = _impact_m(inputs.revenue_m, exposed, rate_cut,
                        inputs.contribution_margin)
    pct = impact / max(0.01, inputs.ebitda_m)
    return RegulatoryShock(
        name="site_neutral_hopd",
        description=("22% rate equalization on HOPD services to ASC/"
                     "physician-office rates."),
        revenue_impact_pct=rate_cut * exposed,
        ebitda_impact_m=round(impact, 2),
        ebitda_impact_pct_of_base=round(pct, 4),
        partner_note=(f"Site-neutral on HOPD exposure: "
                      f"${impact:,.1f}M EBITDA hit "
                      f"({pct*100:.1f}% of base)."),
    )


def _shock_state_medicaid_shift(
    inputs: RegulatoryStressInputs,
) -> RegulatoryShock:
    """Represents a blended state Medicaid rate freeze / cut."""
    # Partner-approximated Medicaid share: 0.4 × (1 - medicare - commercial).
    # We don't have Medicaid in inputs; approximate as 0.20 subsector-dependent.
    medicaid_pct = {
        "hospital": 0.22,
        "safety_net_hospital": 0.40,
        "home_health": 0.25,
        "specialty_practice": 0.10,
        "outpatient_asc": 0.08,
    }.get(inputs.subsector, 0.15)
    rate_cut = 0.03
    impact = _impact_m(inputs.revenue_m, medicaid_pct, rate_cut,
                        inputs.contribution_margin)
    pct = impact / max(0.01, inputs.ebitda_m)
    return RegulatoryShock(
        name="state_medicaid_freeze_cut_3pct",
        description=("3% state Medicaid rate freeze / cut; "
                     "subsector-specific exposure."),
        revenue_impact_pct=rate_cut * medicaid_pct,
        ebitda_impact_m=round(impact, 2),
        ebitda_impact_pct_of_base=round(pct, 4),
        partner_note=(f"State Medicaid 3% cut: ${impact:,.1f}M EBITDA "
                      f"hit ({pct*100:.1f}% of base)."),
    )


def stress_regulatory(
    inputs: RegulatoryStressInputs,
) -> RegulatoryStressReport:
    shocks = [
        _shock_obbba(inputs),
        _shock_sequestration(inputs),
        _shock_site_neutral(inputs),
        _shock_state_medicaid_shift(inputs),
    ]
    combined = sum(s.ebitda_impact_m for s in shocks)
    pct = combined / max(0.01, inputs.ebitda_m)

    if pct >= 0.30:
        note = (f"Combined regulatory stress is catastrophic "
                f"(${combined:,.1f}M, {pct*100:.0f}% of base EBITDA). "
                "Thesis cannot tolerate even partial realization of "
                "these; reduce leverage or pass.")
    elif pct >= 0.15:
        note = (f"Combined regulatory stress is material "
                f"(${combined:,.1f}M, {pct*100:.0f}%). Partial "
                "realization is a real risk; model at 50% probability "
                "and check covenant headroom.")
    elif pct >= 0.05:
        note = (f"Combined regulatory stress is manageable "
                f"(${combined:,.1f}M, {pct*100:.0f}%). Monitor; build "
                "into downside case.")
    else:
        note = ("Combined regulatory stress is immaterial. Deal is "
                "largely insulated from named regulatory shocks.")

    return RegulatoryStressReport(
        shocks=shocks,
        worst_case_combined_m=round(combined, 2),
        worst_case_pct=round(pct, 4),
        partner_note=note,
    )


def render_reg_stress_markdown(r: RegulatoryStressReport) -> str:
    lines = [
        "# Regulatory stress — OBBBA / sequestration / site-neutral",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Worst-case combined: ${r.worst_case_combined_m:,.1f}M "
        f"({r.worst_case_pct*100:.1f}% of base EBITDA)",
        "",
        "| Shock | Rev impact | EBITDA hit | % base |",
        "|---|---:|---:|---:|",
    ]
    for s in r.shocks:
        lines.append(
            f"| {s.name} | {s.revenue_impact_pct*100:.2f}% | "
            f"${s.ebitda_impact_m:,.2f}M | "
            f"{s.ebitda_impact_pct_of_base*100:.1f}% |"
        )
    return "\n".join(lines)
