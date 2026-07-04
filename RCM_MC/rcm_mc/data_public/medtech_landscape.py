"""Medical-device & diagnostics industry reference data (Group A).

Sourced national/global reference figures: device-maker revenue (MassDevice
Big 100 / aggregators), segment market sizes, FDA pathway counts (FDA
databases), and the IVD reagent-rental split. Market-size estimates are
flagged as ranges where sources diverge (global medtech $586–695B; IVD
$82–101B) per the report's caveats. Public, named-source figures — NOT this
portfolio — so the page discloses with a research source/purpose header.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


VINTAGE = "2024 revenue (MassDevice Big 100); FDA databases through 2025-2026"


@dataclass
class DeviceCompany:
    name: str
    device_revenue_b: float


@dataclass
class Segment:
    name: str
    market_b: float
    note: str


@dataclass
class FDAPathway:
    name: str
    metric: str
    note: str


@dataclass
class MedtechResult:
    vintage: str
    global_market_low_b: float
    global_market_high_b: float
    us_share_pct: float
    top10_share_pct: float
    rd_intensity_low_pct: float
    rd_intensity_high_pct: float
    ivd_low_b: float
    ivd_high_b: float
    breakthrough_designations: int
    breakthrough_to_market: int
    intuitive_recurring_pct: float
    companies: List[DeviceCompany] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)
    pathways: List[FDAPathway] = field(default_factory=list)


def compute_medtech_landscape() -> MedtechResult:
    companies = [
        DeviceCompany("Medtronic", 33.5),
        DeviceCompany("J&J MedTech", 31.9),
        DeviceCompany("Abbott", 28.3),
        DeviceCompany("Siemens Healthineers", 25.7),
        DeviceCompany("Medline", 25.2),
        DeviceCompany("Stryker", 22.6),
        DeviceCompany("Becton Dickinson", 21.7),
        DeviceCompany("GE HealthCare", 19.7),
        DeviceCompany("Roche Diagnostics", 17.7),
        DeviceCompany("Boston Scientific", 16.7),
        DeviceCompany("Philips", 16.1),
    ]
    segments = [
        Segment("Cardiovascular", 65.0, "TAVR flagship growth; CRM + structural heart"),
        Segment("Orthopedics", 55.0, "Hips/knees/spine; ASP erosion, robotics pull-through"),
        Segment("In Vitro Diagnostics (IVD)", 92.0, "Reagent-rental; reagents ~65–69% of market"),
        Segment("Surgical robotics", 11.0, "Fastest-growing (15–20% CAGR); Intuitive ~60%+ share"),
    ]
    pathways = [
        FDAPathway("510(k)", "~90-day clock", "Substantial equivalence; most Class II; eSTAR mandatory"),
        FDAPathway("PMA", "~30 approvals/yr", "Class III; clinical data + panel; ~1,000 since 1976"),
        FDAPathway("De Novo", "novel low/mod risk", "No predicate; becomes a predicate; median ~312 days"),
        FDAPathway("Breakthrough Devices", "1,284 designations", "198 marketing authorizations; only ~128 reached market"),
    ]
    return MedtechResult(
        vintage=VINTAGE,
        global_market_low_b=586.0,
        global_market_high_b=695.0,
        us_share_pct=39.0,
        top10_share_pct=35.0,
        rd_intensity_low_pct=6.0,
        rd_intensity_high_pct=8.0,
        ivd_low_b=82.0,
        ivd_high_b=101.0,
        breakthrough_designations=1284,
        breakthrough_to_market=128,
        intuitive_recurring_pct=84.0,
        companies=companies,
        segments=segments,
        pathways=pathways,
    )
