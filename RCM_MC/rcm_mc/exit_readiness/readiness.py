"""Readiness-gap roadmap.

For every archetype the asset doesn't already match, identify the
1-3 specific things the partner needs to fix in the 12-24 months
before sale to credibly run that archetype. Output is a prioritized
list of remediations the partner can drop into a 100-day plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .target import ExitTarget, ExitArchetype


@dataclass
class ReadinessGap:
    archetype: ExitArchetype
    title: str
    description: str
    months_to_remediate: int
    severity: str = "medium"   # low / medium / high


def identify_readiness_gaps(target: ExitTarget) -> List[ReadinessGap]:
    out: List[ReadinessGap] = []

    # Strategic exit gaps
    if target.payer_concentration > 0.5:
        out.append(ReadinessGap(
            archetype=ExitArchetype.STRATEGIC,
            title="Diversify payer mix",
            description=(
                f"Top payer {target.payer_concentration*100:.0f}% — "
                f"strategics discount this. Add 1-2 contracts under "
                f"30% each over 12 months."),
            months_to_remediate=12, severity="high"))

    # IPO scale gap
    if target.ttm_revenue_mm < 200:
        gap = 200 - target.ttm_revenue_mm
        years_at_growth = (
            gap / max(1.0, target.ttm_revenue_mm * target.growth_rate))
        out.append(ReadinessGap(
            archetype=ExitArchetype.IPO,
            title="Reach public-market scale",
            description=(
                f"Revenue ${target.ttm_revenue_mm:.0f}M vs $200M IPO "
                f"floor. At current growth ~{years_at_growth*12:.0f} "
                f"months to scale."),
            months_to_remediate=int(years_at_growth * 12),
            severity="high"))

    # Take-private public-comp gap
    if target.public_comp_multiple < 10:
        out.append(ReadinessGap(
            archetype=ExitArchetype.TAKE_PRIVATE,
            title="Public comp multiple weak",
            description=(
                f"Sector public comps at {target.public_comp_multiple:.1f}x "
                f"— take-private bid would underwhelm. Wait for cycle "
                f"recovery or pursue strategic exit."),
            months_to_remediate=24,
            severity="low"))

    # Secondary PE — physician concentration
    if target.physician_concentration > 0.40:
        out.append(ReadinessGap(
            archetype=ExitArchetype.SECONDARY_PE,
            title="Reduce physician concentration",
            description=(
                f"Top-3 physicians = "
                f"{target.physician_concentration*100:.0f}% revenue. "
                f"Recruit 2-3 partners to dilute below 40% in 18 months."),
            months_to_remediate=18, severity="high"))

    # Margin gap
    if target.ebitda_margin < 0.15:
        out.append(ReadinessGap(
            archetype=ExitArchetype.SECONDARY_PE,
            title="Margin expansion",
            description=(
                f"EBITDA margin {target.ebitda_margin*100:.1f}% below "
                f"the 15% PE comfort floor. Cost-out program over 12 "
                f"months can close the gap."),
            months_to_remediate=12, severity="medium"))

    # Continuation vehicle / div recap leverage check
    leverage = target.net_debt_mm / max(0.1, target.ttm_ebitda_mm)
    if leverage > 4.0:
        out.append(ReadinessGap(
            archetype=ExitArchetype.DIVIDEND_RECAP,
            title="High existing leverage limits recap",
            description=(
                f"Net debt {leverage:.1f}× EBITDA — recap capacity "
                f"limited to incremental ${(5.5 - leverage) * target.ttm_ebitda_mm:.1f}M."),
            months_to_remediate=6, severity="low"))

    # Sort by severity then months
    sev_order = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda g: (sev_order.get(g.severity, 3),
                            g.months_to_remediate))
    return out
