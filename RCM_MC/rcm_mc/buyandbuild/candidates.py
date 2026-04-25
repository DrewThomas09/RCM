"""Platform + AddOnCandidate dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Platform:
    """The acquired platform onto which add-ons are layered."""
    platform_id: str
    sector: str
    base_ebitda_mm: float
    base_ev_mm: float
    state: str = ""
    cbsa: str = ""
    base_payer_mix_concentration: float = 0.4   # top payer share


@dataclass
class AddOnCandidate:
    """One acquisition target the partner is considering bolting
    onto the platform."""
    add_on_id: str
    name: str
    sector: str = ""
    state: str = ""
    cbsa: str = ""
    purchase_price_mm: float = 0.0
    standalone_ebitda_mm: float = 0.0
    expected_revenue_synergy_pct: float = 0.05
    expected_cost_synergy_pct: float = 0.08
    closing_risk_pct: float = 0.10              # base case fall-through
    regulatory_topics: List[str] = field(default_factory=list)
    integration_months: int = 12
