"""Portfolio-level lease waterfall.

Given a :class:`LeaseSchedule` (one or more properties with rent +
escalator + term), produce a per-property + portfolio rollup with:

- Year-by-year rent obligation through the hold period (default 10y)
- Present value of obligations at a caller-supplied discount rate
- Rent-as-%-revenue per property (when property_revenue_annual_usd
  is supplied) and portfolio-wide
- EBITDAR coverage ratio (if EBITDAR supplied)

The waterfall does NOT auto-GAAP-ify operating vs. finance lease —
we price nominal rent cash flows and their PV. A caller that needs
GAAP right-of-use / lease-liability accounting runs that separately
against the same inputs; the lease accounting is a computation on
the same cash flows, not a different data model.
"""
from __future__ import annotations

from typing import List, Optional

from .types import (
    LeaseLine, LeaseSchedule, LeaseWaterfall, PropertyRentSummary,
    load_content,
)


def _rent_series_year1_to_hold(
    line: LeaseLine, hold_years: int,
) -> List[float]:
    """Year-by-year rent over the hold period, including escalator.

    Year 1 is the base rent. Each subsequent year is the prior year
    × (1 + escalator). Beyond the lease term, rent stops (we assume
    the deal exits or renegotiates — modeling post-term rent requires
    caller-supplied assumptions and isn't in scope here)."""
    base = float(line.base_rent_annual_usd or 0.0)
    esc = float(line.escalator_pct or 0.0)
    out: List[float] = []
    for y in range(1, hold_years + 1):
        if y > int(line.term_years or hold_years):
            out.append(0.0)
            continue
        # Year 1 = base; year y = base * (1+esc)^(y-1)
        out.append(base * ((1.0 + esc) ** (y - 1)))
    return out


def _pv(cashflows: List[float], discount_rate: float) -> float:
    r = float(discount_rate)
    return sum(
        cf / ((1.0 + r) ** (y + 1))
        for y, cf in enumerate(cashflows)
    )


def _benchmark_pct_p75(property_type: str) -> Optional[float]:
    try:
        content = load_content("specialty_rent_benchmarks")
    except FileNotFoundError:
        return None
    specs = content.get("specialties") or {}
    entry = specs.get(property_type.upper())
    if not entry:
        return None
    rpr = entry.get("rent_pct_revenue") or {}
    val = rpr.get("p75")
    return float(val) if val is not None else None


def compute_lease_waterfall(
    schedule: LeaseSchedule,
    *,
    hold_years: int = 10,
    portfolio_revenue_annual_usd: Optional[float] = None,
    portfolio_ebitdar_annual_usd: Optional[float] = None,
) -> LeaseWaterfall:
    """Roll the schedule up through the hold period.

    ``portfolio_revenue_annual_usd`` drives the portfolio-level
    rent-as-%-revenue number. When absent, per-property shares are
    still computed (when that line has property_revenue_annual_usd)
    but the portfolio share is None.

    ``portfolio_ebitdar_annual_usd`` drives the coverage ratio
    (EBITDAR / annual rent). When absent, returns None.
    """
    discount = schedule.discount_rate
    per_property: List[PropertyRentSummary] = []
    total_pv = 0.0
    total_nominal = 0.0
    year1_rent_total = 0.0

    for line in schedule.lines:
        series = _rent_series_year1_to_hold(line, hold_years)
        pv = _pv(series, discount)
        total = sum(series)
        year1 = series[0] if series else 0.0
        share = None
        if line.property_revenue_annual_usd and line.property_revenue_annual_usd > 0:
            share = year1 / float(line.property_revenue_annual_usd)
        bench = _benchmark_pct_p75(line.property_type)
        over = bool(share is not None and bench is not None and share > bench)
        per_property.append(PropertyRentSummary(
            property_id=line.property_id,
            property_type=line.property_type,
            base_rent_year1_usd=year1,
            rent_pv_usd=pv,
            rent_total_usd=total,
            rent_pct_of_revenue=share,
            benchmark_pct_p75=bench,
            over_benchmark=over,
        ))
        total_pv += pv
        total_nominal += total
        year1_rent_total += year1

    portfolio_share = None
    if portfolio_revenue_annual_usd and portfolio_revenue_annual_usd > 0:
        portfolio_share = year1_rent_total / float(
            portfolio_revenue_annual_usd
        )

    coverage = None
    if portfolio_ebitdar_annual_usd is not None and year1_rent_total > 0:
        coverage = float(portfolio_ebitdar_annual_usd) / year1_rent_total

    return LeaseWaterfall(
        hold_years=hold_years,
        total_rent_pv_usd=total_pv,
        total_rent_nominal_usd=total_nominal,
        portfolio_rent_pct_revenue=portfolio_share,
        ebitdar_coverage=coverage,
        per_property=per_property,
    )
