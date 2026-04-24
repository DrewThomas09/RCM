"""Shared types for the real-estate / lease-economics subpackage.

Separate from the regulatory package's ``RegulatoryBand`` on purpose
— real-estate-specific severity labels live in ``StewardRiskTier``.
The two packages bundle together in the Bankruptcy-Survivor Scan
(Prompt I) without either depending on the other.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


class StewardRiskTier(str, Enum):
    LOW      = "LOW"           # 0-1 factors
    MEDIUM   = "MEDIUM"        # 2-3 factors
    HIGH     = "HIGH"          # 4 factors
    CRITICAL = "CRITICAL"      # all 5 factors — full Steward pattern
    UNKNOWN  = "UNKNOWN"       # insufficient data


def load_content(name: str) -> Dict[str, Any]:
    """Load a content YAML from ``content/<name>.yaml``."""
    p = CONTENT_DIR / f"{name}.yaml"
    if not p.exists():
        raise FileNotFoundError(f"real-estate content missing: {p}")
    return yaml.safe_load(p.read_text("utf-8"))


@dataclass
class LeaseLine:
    """One property's lease schedule."""
    property_id: str
    property_type: str              # HOSPITAL | MOB | SNF | ASC | etc.
    base_rent_annual_usd: float
    escalator_pct: float = 0.02      # annual escalator (2% default)
    term_years: int = 10
    renewal_option_years: int = 0
    termination_fee_usd: Optional[float] = None
    guarantor: Optional[str] = None
    landlord: Optional[str] = None
    # Annual revenue the property contributes. Used for rent-as-%-
    # revenue per-property calcs. When None, only portfolio-level
    # rent share is meaningful.
    property_revenue_annual_usd: Optional[float] = None
    # Original lease start — used for "lease duration at signing"
    # in Steward-score.
    commencement_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "property_type": self.property_type,
            "base_rent_annual_usd": self.base_rent_annual_usd,
            "escalator_pct": self.escalator_pct,
            "term_years": self.term_years,
            "renewal_option_years": self.renewal_option_years,
            "termination_fee_usd": self.termination_fee_usd,
            "guarantor": self.guarantor,
            "landlord": self.landlord,
            "property_revenue_annual_usd":
                self.property_revenue_annual_usd,
            "commencement_date": self.commencement_date,
        }


@dataclass
class LeaseSchedule:
    """Portfolio-level lease schedule."""
    lines: List[LeaseLine] = field(default_factory=list)
    as_of: Optional[str] = None
    discount_rate: float = 0.075     # WACC-ish for PV; override per deal


@dataclass
class PropertyRentSummary:
    """One property's rent summary rolled through the hold period."""
    property_id: str
    property_type: str
    base_rent_year1_usd: float
    rent_pv_usd: float
    rent_total_usd: float
    rent_pct_of_revenue: Optional[float]
    benchmark_pct_p75: Optional[float]
    over_benchmark: bool

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class LeaseWaterfall:
    hold_years: int
    total_rent_pv_usd: float
    total_rent_nominal_usd: float
    portfolio_rent_pct_revenue: Optional[float]
    ebitdar_coverage: Optional[float]
    per_property: List[PropertyRentSummary] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hold_years": self.hold_years,
            "total_rent_pv_usd": self.total_rent_pv_usd,
            "total_rent_nominal_usd": self.total_rent_nominal_usd,
            "portfolio_rent_pct_revenue":
                self.portfolio_rent_pct_revenue,
            "ebitdar_coverage": self.ebitdar_coverage,
            "per_property": [p.to_dict() for p in self.per_property],
        }


@dataclass
class StewardScoreResult:
    tier: StewardRiskTier
    factors_hit: List[str]
    factor_count: int
    matching_case_study: Optional[str] = None
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "factors_hit": list(self.factors_hit),
            "factor_count": self.factor_count,
            "matching_case_study": self.matching_case_study,
            "reasoning": self.reasoning,
        }


@dataclass
class CapexWall:
    avg_fixed_asset_age_years: float
    useful_life_years: float
    deferred_capex_backlog_usd: float
    replacement_window_years: int
    annual_recovery_profile_usd: List[float]
    severity: str = "MEDIUM"      # LOW | MEDIUM | HIGH

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class SaleLeasebackBlocker:
    state_code: str
    statute: str
    status: str                    # IN_EFFECT | PHASED | PENDING | NONE
    feasible: bool
    caveats: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()
