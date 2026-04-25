"""LP-ready disclosure rendering — ISSB IFRS S1/S2 + EDCI summary
in a single text block ready to paste into an LP letter."""
from __future__ import annotations

from typing import List

from .edci import EDCIScorecard


def render_lp_disclosure(scorecard: EDCIScorecard) -> str:
    """Render an LP-ready disclosure markdown block."""
    lines: List[str] = []
    lines.append(f"## ESG Disclosure — {scorecard.company}")
    lines.append("")
    lines.append(
        f"**EDCI maturity band:** {scorecard.maturity_band} "
        f"({scorecard.metric_count} metrics reported)")
    lines.append("")

    if "scope_1_2_kgco2e" in scorecard.metrics:
        lines.append("### Climate (ISSB IFRS S2)")
        lines.append(
            f"- Scope 1+2 emissions: "
            f"{scorecard.metrics['scope_1_2_kgco2e']:,.0f} kgCO2e")
        if "scope_3_kgco2e" in scorecard.metrics:
            lines.append(
                f"- Scope 3 emissions: "
                f"{scorecard.metrics['scope_3_kgco2e']:,.0f} kgCO2e "
                f"(supply chain estimate)")
        lines.append("")

    if "pct_female_workforce" in scorecard.metrics:
        lines.append("### Workforce (ISSB IFRS S1 — General)")
        lines.append(
            f"- Female workforce: "
            f"{scorecard.metrics['pct_female_workforce']*100:.1f}%")
        if "pct_female_management" in scorecard.metrics:
            lines.append(
                f"- Female in management: "
                f"{scorecard.metrics['pct_female_management']*100:.1f}%")
        if "pay_equity_ratio" in scorecard.metrics:
            lines.append(
                f"- Pay equity ratio (female/male): "
                f"{scorecard.metrics['pay_equity_ratio']:.3f}")
        if "voluntary_turnover_rate" in scorecard.metrics:
            lines.append(
                f"- Voluntary turnover: "
                f"{scorecard.metrics['voluntary_turnover_rate']*100:.1f}%")
        lines.append("")

    if "governance_composite" in scorecard.metrics:
        lines.append("### Governance")
        lines.append(
            f"- Composite governance score: "
            f"{scorecard.metrics['governance_composite']:.2f} / 1.00")
        if "board_independence" in scorecard.metrics:
            lines.append(
                f"- Board independence: "
                f"{scorecard.metrics['board_independence']*100:.0f}%")
        lines.append("")

    if scorecard.metrics.get("cybersecurity_attestation"):
        lines.append("### Cybersecurity")
        lines.append("- SOC 2 Type II attestation in place.")
        lines.append("")

    if "work_related_injuries" in scorecard.metrics:
        lines.append(
            f"- Work-related injuries (calendar year): "
            f"{scorecard.metrics['work_related_injuries']}")

    return "\n".join(lines)
