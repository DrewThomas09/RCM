"""ILPA 2.0 Performance Template + LP-narrative rendering.

ILPA 2.0 effective Q1 2026 requires deal-level IRR decomposition
in a standardized format. This module renders the AttributionResult
as both a structured dict (machine-readable) and a markdown
narrative (LP letter-ready).
"""
from __future__ import annotations

from typing import Any, Dict, List

from .components import AttributionResult


def format_ilpa_2_0(result: AttributionResult) -> Dict[str, Any]:
    """Render the attribution as an ILPA 2.0 Performance Template
    section. Returns a dict matching the published ILPA schema."""
    c = result.components
    return {
        "investment_name": result.deal_name,
        "entry_equity_mm": result.entry_equity_mm,
        "exit_equity_mm": result.exit_equity_mm,
        "gross_irr": result.irr,
        "gross_moic": result.moic,
        "value_creation_attribution": {
            "revenue_growth_organic": c.revenue_growth_organic_mm,
            "revenue_growth_inorganic": c.revenue_growth_ma_mm,
            "margin_expansion": c.margin_expansion_mm,
            "multiple_expansion": c.multiple_expansion_mm,
            "debt_paydown_leverage": c.leverage_mm,
            "fx_translation": c.fx_mm,
            "dividend_recap": c.dividend_recap_mm,
            "subscription_line_credit": c.sub_line_credit_mm,
            "cross_terms_residual": c.cross_terms_mm,
            "total_value_created": c.total_value_created_mm,
        },
        "value_creation_share": result.component_share,
        "ilpa_template_version": "2.0",
    }


def render_lp_narrative(result: AttributionResult) -> str:
    """LP-letter markdown narrative paragraph + attribution table."""
    c = result.components
    lines: List[str] = []
    lines.append(f"## {result.deal_name} — Performance Attribution")
    lines.append("")
    lines.append(
        f"Gross IRR: **{result.irr*100:.1f}%** · "
        f"Gross MOIC: **{result.moic:.2f}x**")
    lines.append(
        f"Entry equity: ${result.entry_equity_mm:.1f}M → "
        f"Exit equity: ${result.exit_equity_mm:.1f}M")
    lines.append("")
    lines.append("### Value Creation Attribution (ILPA 2.0)")
    lines.append("")
    lines.append("| Component | $M | Share |")
    lines.append("|---|---:|---:|")
    rows = [
        ("Revenue growth — organic",
         c.revenue_growth_organic_mm,
         result.component_share["revenue_growth_organic"]),
        ("Revenue growth — M&A",
         c.revenue_growth_ma_mm,
         result.component_share["revenue_growth_ma"]),
        ("Margin expansion",
         c.margin_expansion_mm,
         result.component_share["margin_expansion"]),
        ("Multiple expansion",
         c.multiple_expansion_mm,
         result.component_share["multiple_expansion"]),
        ("Leverage / debt paydown",
         c.leverage_mm,
         result.component_share["leverage"]),
        ("Dividend recap",
         c.dividend_recap_mm,
         result.component_share["dividend_recap"]),
        ("Sub-line credit savings",
         c.sub_line_credit_mm,
         result.component_share["sub_line_credit"]),
        ("FX translation",
         c.fx_mm,
         result.component_share["fx"]),
        ("Cross-terms (residual)",
         c.cross_terms_mm,
         result.component_share["cross_terms"]),
    ]
    for label, dollars, share in rows:
        sign = "+" if dollars > 0 else ("−" if dollars < 0 else " ")
        lines.append(
            f"| {label} | {sign}${abs(dollars):.1f}M | "
            f"{share*100:+.1f}% |")
    lines.append("|---|---|---|")
    lines.append(
        f"| **Total value created** | "
        f"**${c.total_value_created_mm:.1f}M** | 100.0% |")
    lines.append("")

    # Narrative bullets
    revenue_total = c.revenue_growth_organic_mm + c.revenue_growth_ma_mm
    if revenue_total > 0:
        rev_share = revenue_total / max(
            1.0, abs(c.total_value_created_mm))
        organic_share = (c.revenue_growth_organic_mm
                         / max(0.1, revenue_total))
        lines.append(
            f"- Revenue growth contributed **${revenue_total:.0f}M** "
            f"({rev_share*100:.0f}% of value), "
            f"of which **{organic_share*100:.0f}%** organic and "
            f"**{(1-organic_share)*100:.0f}%** from add-on M&A.")

    if c.margin_expansion_mm > 0:
        lines.append(
            f"- Margin expansion contributed "
            f"**${c.margin_expansion_mm:.0f}M** "
            f"({c.margin_expansion_mm / max(1.0, abs(c.total_value_created_mm))*100:.0f}%).")

    if c.multiple_expansion_mm > 0:
        lines.append(
            f"- Multiple expansion contributed "
            f"**${c.multiple_expansion_mm:.0f}M** "
            f"({c.multiple_expansion_mm / max(1.0, abs(c.total_value_created_mm))*100:.0f}%) "
            f"— note vintage / cycle dependence.")

    return "\n".join(lines)
