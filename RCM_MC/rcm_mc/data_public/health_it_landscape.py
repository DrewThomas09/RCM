"""Health IT, EHR & interoperability reference data (Group C).

Sourced reference figures: acute-care EHR market share (KLAS), digital-health
venture funding (Rock Health), TEFCA / QHIN designations (ONC / Sequoia
Project), and ambient-AI adoption. Public, named-source figures — NOT this
portfolio — so the page discloses with a research source/purpose header.
The clinical AI / FDA-cleared device detail lives on /clinical-ai.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


VINTAGE = "KLAS end-2024; Rock Health 2024; ONC/TEFCA through 2025"


@dataclass
class EHRVendor:
    name: str
    hospital_share_pct: float
    note: str


@dataclass
class FundingYear:
    year: int
    vc_b: float
    deals: int


@dataclass
class QHIN:
    name: str
    designated: str


@dataclass
class HealthITResult:
    vintage: str
    epic_share_pct: float
    oracle_share_pct: float
    digital_health_vc_b: float
    digital_health_deals: int
    ai_funding_share_pct: float
    qhins_live: int
    vendors: List[EHRVendor] = field(default_factory=list)
    funding: List[FundingYear] = field(default_factory=list)
    qhin_list: List[QHIN] = field(default_factory=list)


def compute_health_it_landscape() -> HealthITResult:
    vendors = [
        EHRVendor("Epic", 42.3, "54.9% of beds; +176 hospitals net in 2024 (record)"),
        EHRVendor("Oracle Health (Cerner)", 22.9, "Net −74 hospitals 2024; Cerner acquired for $28.3B"),
        EHRVendor("Meditech", 14.8, "Net −57 hospitals 2024"),
        EHRVendor("Altera / CPSI / TruBridge / others", 20.0, "Remainder of acute-care market"),
    ]
    funding = [
        FundingYear(2019, 8.2, 0),
        FundingYear(2020, 14.3, 0),
        FundingYear(2021, 29.2, 0),
        FundingYear(2023, 10.8, 503),
        FundingYear(2024, 10.1, 497),
    ]
    qhin_list = [
        QHIN("eHealth Exchange", "2023-12-12"),
        QHIN("Epic Nexus", "2023-12-12"),
        QHIN("Health Gorilla", "2023-12-12"),
        QHIN("KONZA", "2023-12-12"),
        QHIN("MedAllies", "2023-12-12"),
        QHIN("CommonWell", "later"),
        QHIN("Kno2", "later"),
        QHIN("Surescripts", "later"),
    ]
    return HealthITResult(
        vintage=VINTAGE,
        epic_share_pct=42.3,
        oracle_share_pct=22.9,
        digital_health_vc_b=10.1,
        digital_health_deals=497,
        ai_funding_share_pct=37.0,
        qhins_live=len(qhin_list),
        vendors=vendors,
        funding=funding,
        qhin_list=qhin_list,
    )
