"""Per-deal asset + portfolio snapshot dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PortfolioAsset:
    """One portfolio company with its plan + actual track."""
    deal_id: str
    name: str
    sector: str
    entry_year: int = 0
    held_years: float = 0.0
    entry_ebitda_mm: float = 0.0
    plan_ebitda_mm: float = 0.0          # current year's plan
    actual_ebitda_mm: float = 0.0        # current year's actual
    plan_revenue_mm: float = 0.0
    actual_revenue_mm: float = 0.0
    # The comparable-deal MOIC at acquisition — the partner's
    # external-validity reference for whether the asset is
    # tracking peer-group expectations.
    comparable_moic_p50: Optional[float] = None
    comparable_moic_p25: Optional[float] = None
    # Implied current MOIC from latest valuation marks (or
    # NAV if held). Compared against comparable_moic_p50 for
    # the comp-relative trend signal.
    current_moic: Optional[float] = None


@dataclass
class PortfolioSnapshot:
    """Top-level container for the partner's whole book."""
    fund_name: str
    snapshot_date: str = ""    # ISO YYYY-MM-DD
    assets: List[PortfolioAsset] = field(default_factory=list)
