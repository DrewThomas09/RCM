"""Executive + ManagementTeam dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RaterRole(str, Enum):
    BOSS = "boss"           # weight 0.35
    PEER = "peer"           # weight 0.25
    DIRECT_REPORT = "direct_report"  # weight 0.25
    SELF = "self"           # weight 0.05
    EXTERNAL = "external"   # weight 0.10


@dataclass
class Executive:
    """One management team member."""
    person_id: str
    name: str
    role: str                      # CEO / CFO / COO / CRO / etc.
    tenure_years: float = 0.0
    direct_reports: int = 0
    has_pe_experience: bool = False
    rollover_equity_pct: float = 0.0
    notes: str = ""


@dataclass
class ManagementTeam:
    """Top-of-house team being assessed."""
    company_name: str
    executives: List[Executive] = field(default_factory=list)
    total_headcount: int = 0
    org_layers: int = 5            # CEO → IC count of management
                                   # layers
