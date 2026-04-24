"""Data model for management diligence.

Keeps the ``Executive`` dataclass minimal — partners typically
collect this by hand from the data room + reference calls.
Optional fields degrade gracefully to neutral priors in the
scorer when not supplied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Role(str, Enum):
    """Standard C-suite roles. Kept small — partners group
    everything else into 'OTHER'."""
    CEO = "CEO"
    CFO = "CFO"
    COO = "COO"
    CCO = "CCO"              # Chief Clinical / Compliance Officer
    CMO = "CMO"              # Chief Medical Officer
    CHRO = "CHRO"
    OTHER = "OTHER"


class ComplevelBand(str, Enum):
    """Where the executive's base+cash comp sits vs specialty FMV."""
    BELOW_P50 = "BELOW_P50"       # below market — retention risk
    P50 = "P50"                    # market median
    P75 = "P75"                    # above market but defensible
    ABOVE_P90 = "ABOVE_P90"       # excessive; Stark risk (clinical)
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ForecastHistory:
    """One period's management guidance vs realized result.

    Partners usually have 3–6 quarters of guidance vs actuals from
    the target's data-room financial packet. This module expects
    percentages as decimals (e.g., 0.02 = management beat guidance
    by 2%; −0.15 = missed by 15%).
    """
    period: str                    # "Q4 2024" / "FY2024" / etc.
    metric: str                    # "EBITDA" / "Revenue" / "NPR"
    guided: float
    actual: float

    @property
    def miss_pct(self) -> Optional[float]:
        """Negative = missed guidance (actual < guided).
        Positive = beat."""
        if self.guided == 0:
            return None
        return (self.actual - self.guided) / abs(self.guided)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period, "metric": self.metric,
            "guided": self.guided, "actual": self.actual,
            "miss_pct": self.miss_pct,
        }


@dataclass(frozen=True)
class PriorRole:
    """Executive's prior role + outcome at that role's employer.

    ``outcome`` values are a controlled vocabulary matched to
    Deal Autopsy outcome labels so the scorer can cross-reference:

        STRONG_EXIT / STRONG_PUBLIC
        IN_PROGRESS             — still active, too early to tell
        DISTRESSED_SALE
        CHAPTER_11
        BANKRUPTCY
        DELISTED
        UNKNOWN
    """
    employer: str
    role: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    outcome: str = "UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class Executive:
    """Profile a partner assembles for one C-suite role."""
    name: str
    role: Role = Role.OTHER
    # Tenure
    years_in_role: Optional[float] = None
    years_at_facility: Optional[float] = None
    # Comp (partner inputs — total cash + equity)
    total_cash_comp_usd: Optional[float] = None
    has_equity_rollover: bool = False
    has_clawback_provisions: bool = False
    performance_weighted_bonus: bool = False
    comp_band: ComplevelBand = ComplevelBand.UNKNOWN
    # Forecast history — usually 3–6 periods
    forecast_history: List[ForecastHistory] = field(default_factory=list)
    # Prior roles + outcomes
    prior_roles: List[PriorRole] = field(default_factory=list)
    # Free-text notes / partner reference-call output
    reference_note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "role": self.role.value,
            "years_in_role": self.years_in_role,
            "years_at_facility": self.years_at_facility,
            "total_cash_comp_usd": self.total_cash_comp_usd,
            "has_equity_rollover": self.has_equity_rollover,
            "has_clawback_provisions": self.has_clawback_provisions,
            "performance_weighted_bonus": self.performance_weighted_bonus,
            "comp_band": self.comp_band.value,
            "forecast_history":
                [f.to_dict() for f in self.forecast_history],
            "prior_roles": [p.to_dict() for p in self.prior_roles],
            "reference_note": self.reference_note,
        }
