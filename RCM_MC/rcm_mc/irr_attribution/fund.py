"""Fund-level attribution aggregation across realized deals.

ILPA 2.0 Performance Templates (effective Q1 2026) require
attribution at the FUND level, not just per-deal. The existing
``decompose_value_creation`` operates on one DealCashflows. This
module aggregates across a list of deals to produce:

  • Fund total value created (sum of per-deal totals)
  • Per-component fund attribution ($ + share of fund)
  • Per-deal lookthrough rows so the partner can see which deals
    drove which components
  • Vintage-cohort rollup — attribution rolled up by entry-year
    cohort so the LP can see how the fund's value-creation mix
    has shifted across vintages
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from .components import (
    AttributionComponents, AttributionResult, DealCashflows,
)
from .decompose import decompose_value_creation


@dataclass
class FundDealRow:
    """Per-deal lookthrough for the fund-level report."""
    deal_name: str
    entry_year: int
    irr: float
    moic: float
    total_value_created_mm: float
    components: AttributionComponents


@dataclass
class FundAttributionResult:
    """Fund-level aggregated attribution."""
    fund_name: str
    n_deals: int
    total_value_created_mm: float
    fund_components: AttributionComponents = field(
        default_factory=AttributionComponents)
    component_share: Dict[str, float] = field(default_factory=dict)
    deal_rows: List[FundDealRow] = field(default_factory=list)
    vintage_rollup: Dict[int, AttributionComponents] = field(
        default_factory=dict)


def _zero_components() -> AttributionComponents:
    return AttributionComponents()


def _add_components(a: AttributionComponents,
                    b: AttributionComponents) -> AttributionComponents:
    """Element-wise sum of two component dataclasses."""
    return AttributionComponents(
        revenue_growth_organic_mm=(
            a.revenue_growth_organic_mm
            + b.revenue_growth_organic_mm),
        revenue_growth_ma_mm=(
            a.revenue_growth_ma_mm + b.revenue_growth_ma_mm),
        margin_expansion_mm=(
            a.margin_expansion_mm + b.margin_expansion_mm),
        multiple_expansion_mm=(
            a.multiple_expansion_mm + b.multiple_expansion_mm),
        leverage_mm=a.leverage_mm + b.leverage_mm,
        fx_mm=a.fx_mm + b.fx_mm,
        dividend_recap_mm=(
            a.dividend_recap_mm + b.dividend_recap_mm),
        sub_line_credit_mm=(
            a.sub_line_credit_mm + b.sub_line_credit_mm),
        cross_terms_mm=a.cross_terms_mm + b.cross_terms_mm,
        total_value_created_mm=(
            a.total_value_created_mm + b.total_value_created_mm),
    )


def _component_shares(c: AttributionComponents) -> Dict[str, float]:
    """Signed share per component, denominated by absolute total
    so cancelling effects don't break the percentages."""
    denom = (abs(c.revenue_growth_organic_mm)
             + abs(c.revenue_growth_ma_mm)
             + abs(c.margin_expansion_mm)
             + abs(c.multiple_expansion_mm)
             + abs(c.leverage_mm)
             + abs(c.fx_mm)
             + abs(c.dividend_recap_mm)
             + abs(c.sub_line_credit_mm)
             + abs(c.cross_terms_mm)) or 1.0
    return {
        "revenue_growth_organic": round(
            c.revenue_growth_organic_mm / denom, 4),
        "revenue_growth_ma": round(
            c.revenue_growth_ma_mm / denom, 4),
        "margin_expansion": round(
            c.margin_expansion_mm / denom, 4),
        "multiple_expansion": round(
            c.multiple_expansion_mm / denom, 4),
        "leverage": round(c.leverage_mm / denom, 4),
        "fx": round(c.fx_mm / denom, 4),
        "dividend_recap": round(c.dividend_recap_mm / denom, 4),
        "sub_line_credit": round(
            c.sub_line_credit_mm / denom, 4),
        "cross_terms": round(c.cross_terms_mm / denom, 4),
    }


def aggregate_fund_attribution(
    fund_name: str,
    deals: Iterable[DealCashflows],
) -> FundAttributionResult:
    """Aggregate per-deal attribution into a fund-level
    decomposition + per-deal lookthrough + vintage rollup.

    Each deal's components sum into the fund total. Vintage
    rollup buckets deals by entry_year so the partner can see
    how the fund's value-creation mix has shifted across vintages.
    """
    deal_list = list(deals)
    fund_components = _zero_components()
    deal_rows: List[FundDealRow] = []
    vintage_components: Dict[int, AttributionComponents] = (
        defaultdict(_zero_components))

    for cf in deal_list:
        result = decompose_value_creation(cf)
        fund_components = _add_components(
            fund_components, result.components)
        deal_rows.append(FundDealRow(
            deal_name=cf.deal_name,
            entry_year=cf.entry_year,
            irr=result.irr,
            moic=result.moic,
            total_value_created_mm=(
                result.components.total_value_created_mm),
            components=result.components,
        ))
        if cf.entry_year:
            vintage_components[cf.entry_year] = _add_components(
                vintage_components[cf.entry_year],
                result.components)

    # Round fund components for partner readability
    rounded = AttributionComponents(
        revenue_growth_organic_mm=round(
            fund_components.revenue_growth_organic_mm, 2),
        revenue_growth_ma_mm=round(
            fund_components.revenue_growth_ma_mm, 2),
        margin_expansion_mm=round(
            fund_components.margin_expansion_mm, 2),
        multiple_expansion_mm=round(
            fund_components.multiple_expansion_mm, 2),
        leverage_mm=round(fund_components.leverage_mm, 2),
        fx_mm=round(fund_components.fx_mm, 2),
        dividend_recap_mm=round(
            fund_components.dividend_recap_mm, 2),
        sub_line_credit_mm=round(
            fund_components.sub_line_credit_mm, 2),
        cross_terms_mm=round(fund_components.cross_terms_mm, 2),
        total_value_created_mm=round(
            fund_components.total_value_created_mm, 2),
    )
    shares = _component_shares(rounded)

    # Sort deal rows by total value created descending so the
    # partner sees the biggest contributors first
    deal_rows.sort(
        key=lambda r: r.total_value_created_mm, reverse=True)

    # Vintage rollup as an ordered dict by year ascending
    vintage_rollup = {
        year: vintage_components[year]
        for year in sorted(vintage_components.keys())
    }

    return FundAttributionResult(
        fund_name=fund_name,
        n_deals=len(deal_list),
        total_value_created_mm=rounded.total_value_created_mm,
        fund_components=rounded,
        component_share=shares,
        deal_rows=deal_rows,
        vintage_rollup=vintage_rollup,
    )


def format_fund_ilpa(
    result: FundAttributionResult,
) -> Dict[str, object]:
    """Render the fund-level result in ILPA 2.0 Performance
    Template shape — the schema LPs receive in their fund report
    rather than the per-deal schema."""
    c = result.fund_components
    return {
        "fund_name": result.fund_name,
        "n_realized_deals": result.n_deals,
        "fund_total_value_created_mm": (
            result.total_value_created_mm),
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
        },
        "value_creation_share": result.component_share,
        "deal_lookthrough": [
            {
                "deal_name": r.deal_name,
                "entry_year": r.entry_year,
                "irr": r.irr,
                "moic": r.moic,
                "value_created_mm": r.total_value_created_mm,
            }
            for r in result.deal_rows
        ],
        "vintage_rollup": {
            str(year): {
                "revenue_growth_organic": comp.revenue_growth_organic_mm,
                "revenue_growth_ma": comp.revenue_growth_ma_mm,
                "margin_expansion": comp.margin_expansion_mm,
                "multiple_expansion": comp.multiple_expansion_mm,
                "leverage": comp.leverage_mm,
                "total_value_created": comp.total_value_created_mm,
            }
            for year, comp in result.vintage_rollup.items()
        },
        "ilpa_template_version": "2.0",
    }
