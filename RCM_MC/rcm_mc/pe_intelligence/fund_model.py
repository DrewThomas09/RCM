"""Fund-level model — DPI, TVPI, called capital, carry projections.

Deals roll up into funds. LPs care about DPI (distributions to paid-in),
TVPI (total value to paid-in), and fund-level IRR. This module
models a fund as a list of deals, each with a commitment, hold, and
projected MOIC.

Functions:

- :func:`project_fund` — given a fund definition, project DPI/TVPI/IRR
  by year.
- :func:`fund_vintage_percentile` — roughly place a fund against
  preqin-style quartiles for its vintage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FundDeal:
    deal_id: str
    commitment: float               # $ called for the deal
    hold_years: float
    projected_moic: float
    investment_year: int            # year number (1 = first investment)


@dataclass
class Fund:
    name: str
    fund_size: float
    vintage_year: int
    target_fund_moic: float = 2.0
    management_fee_pct: float = 0.02
    management_fee_years: int = 10
    carry_pct: float = 0.20
    preferred_return_rate: float = 0.08


@dataclass
class FundProjection:
    year: int
    called_capital: float
    distributions_to_date: float
    nav: float
    dpi: float                      # distributions / called
    tvpi: float                     # (distributions + nav) / called
    rvpi: float                     # nav / called

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "called_capital": self.called_capital,
            "distributions_to_date": self.distributions_to_date,
            "nav": self.nav,
            "dpi": self.dpi,
            "tvpi": self.tvpi,
            "rvpi": self.rvpi,
        }


# ── Projection ──────────────────────────────────────────────────────

def project_fund(
    fund: Fund,
    deals: List[FundDeal],
    *,
    horizon_years: int = 12,
) -> List[FundProjection]:
    """Project called capital, distributions, NAV year-by-year.

    Simplifying assumptions:
    - Capital is called the year of investment (no capital-call lag).
    - Each deal exits at investment_year + hold_years, returning
      commitment × projected_moic.
    - Management fees are charged each year on fund_size for
      ``management_fee_years``.
    - NAV tracks the outstanding deals at their commitment (no
      markup/markdown prior to exit — simplified).
    """
    out: List[FundProjection] = []
    called = 0.0
    distributed = 0.0

    for y in range(1, horizon_years + 1):
        # Called from deals this year
        called += sum(d.commitment for d in deals if d.investment_year == y)
        # Management fees
        if y <= fund.management_fee_years:
            called += fund.fund_size * fund.management_fee_pct

        # Distributions from exits this year
        for d in deals:
            exit_year = d.investment_year + int(round(d.hold_years))
            if exit_year == y:
                distributed += d.commitment * d.projected_moic

        # NAV: sum of commitments × MOIC × time-progress for unrealized deals
        nav = 0.0
        for d in deals:
            exit_year = d.investment_year + int(round(d.hold_years))
            if d.investment_year <= y < exit_year:
                progress = (y - d.investment_year) / max(d.hold_years, 1)
                interim_value = d.commitment * (1 + progress * (d.projected_moic - 1))
                nav += interim_value

        dpi = distributed / max(called, 1e-9)
        tvpi = (distributed + nav) / max(called, 1e-9)
        rvpi = nav / max(called, 1e-9)

        out.append(FundProjection(
            year=y, called_capital=called,
            distributions_to_date=distributed,
            nav=nav, dpi=dpi, tvpi=tvpi, rvpi=rvpi,
        ))
    return out


# ── Vintage placement ───────────────────────────────────────────────

# Approximate historical healthcare-PE quartile breaks (Cambridge /
# Preqin directional). Q1 = top-quartile, Q4 = bottom. Placeholder —
# refresh against live Preqin data quarterly.
_QUARTILES = {
    # (metric, vintage_decade) → [Q1_top, Q2_median, Q3_bottom_of_above_median]
    ("tvpi", "2010s"): [2.5, 1.9, 1.5],
    ("tvpi", "2020s"): [2.3, 1.8, 1.4],
    ("dpi", "2010s"): [1.8, 1.2, 0.8],
    ("dpi", "2020s"): [0.9, 0.5, 0.2],
    ("irr", "2010s"): [0.22, 0.15, 0.10],
    ("irr", "2020s"): [0.20, 0.13, 0.08],
}


def _decade(year: int) -> str:
    if year >= 2020:
        return "2020s"
    return "2010s"


def fund_vintage_percentile(
    metric: str,
    value: float,
    vintage_year: int,
) -> Optional[str]:
    """Return rough quartile placement for a fund-level metric.

    Returns "Q1", "Q2", "Q3", or "Q4" (or None if metric unknown).
    """
    decade = _decade(vintage_year)
    breaks = _QUARTILES.get((metric.lower(), decade))
    if breaks is None:
        return None
    # breaks is [top of Q1, median, bottom quartile cutoff]
    if value >= breaks[0]:
        return "Q1"
    if value >= breaks[1]:
        return "Q2"
    if value >= breaks[2]:
        return "Q3"
    return "Q4"


def commentary_for_quartile(quartile: str) -> str:
    return {
        "Q1": "Top-quartile performance.",
        "Q2": "Above-median — tracking toward top-half.",
        "Q3": "Below median — material improvement needed to clear 2.0x target.",
        "Q4": "Bottom quartile — fundraise risk at successor fund.",
    }.get(quartile, "")
