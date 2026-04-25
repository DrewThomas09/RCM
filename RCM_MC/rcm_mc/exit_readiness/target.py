"""ExitTarget + ExitArchetype + ArchetypeResult dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ExitArchetype(str, Enum):
    STRATEGIC = "strategic_corporate"
    SECONDARY_PE = "secondary_pe"
    SPONSOR_TO_SPONSOR = "sponsor_to_sponsor"
    TAKE_PRIVATE = "take_private"
    CONTINUATION = "continuation_vehicle"
    IPO = "ipo"
    DIVIDEND_RECAP = "dividend_recap"


@dataclass
class ExitTarget:
    """The asset being marketed for sale."""
    target_name: str
    sector: str
    ttm_revenue_mm: float
    ttm_ebitda_mm: float
    growth_rate: float = 0.10           # forward revenue CAGR
    ebitda_margin: float = 0.18
    net_debt_mm: float = 0.0
    public_comp_multiple: float = 12.0  # current public sector EV/EBITDA
    private_comp_multiple: float = 11.0
    growth_durability_score: float = 0.7   # 0-1, durability of growth
    cash_pay_share: float = 0.10        # share of revenue from cash-pay
    physician_concentration: float = 0.30  # top-3 physician share
    payer_concentration: float = 0.40   # top payer share
    tags: List[str] = field(default_factory=list)


@dataclass
class ArchetypeResult:
    """Per-archetype exit valuation + supporting math."""
    archetype: ExitArchetype
    enterprise_value_mm: float
    equity_value_mm: float
    implied_multiple: float
    valuation_method: str
    drivers: List[str] = field(default_factory=list)
    confidence: float = 0.5
