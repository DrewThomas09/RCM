"""Medical Real Estate / MOB (Medical Office Building) Tracker.

Tracks healthcare real estate exposure across portfolio: MOBs, ASCs,
lab sites, imaging centers, dialysis, behavioral, SNFs — including
rent coverage, cap rates, tenant credit, lease structure.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class PropertyAsset:
    property_name: str
    sector: str
    city: str
    state: str
    sqft: int
    tenant: str
    tenant_credit: str
    annual_rent_m: float
    nnn_or_gross: str
    lease_years_remaining: float
    cap_rate_pct: float
    value_m: float


@dataclass
class SectorExposure:
    sector: str
    property_count: int
    total_sqft: int
    total_rent_m: float
    total_value_m: float
    avg_cap_rate_pct: float
    avg_lease_years: float


@dataclass
class TenantConcentration:
    tenant: str
    tenant_type: str
    credit_rating: str
    properties: int
    total_sqft: int
    annual_rent_m: float
    pct_portfolio_rent: float
    relationship_years: int


@dataclass
class LeaseExpiration:
    year: int
    expiring_leases: int
    expiring_rent_m: float
    weighted_avg_cap_rate: float
    renewal_rate_pct: float


@dataclass
class CapRateBenchmark:
    property_type: str
    p25_cap_rate: float
    median_cap_rate: float
    p75_cap_rate: float
    ytd_trend_bps: int
    regional_dispersion_bps: int


@dataclass
class PropCoStrategy:
    deal: str
    strategy: str
    properties_count: int
    property_value_m: float
    sale_leaseback_proceeds_m: float
    opco_coverage_x: float
    target_investor: str


@dataclass
class REResult:
    total_properties: int
    total_sqft_mm: float
    total_annual_rent_m: float
    total_value_b: float
    weighted_cap_rate_pct: float
    weighted_lease_years: float
    nnn_pct: float
    properties: List[PropertyAsset]
    sectors: List[SectorExposure]
    tenants: List[TenantConcentration]
    expirations: List[LeaseExpiration]
    benchmarks: List[CapRateBenchmark]
    propcos: List[PropCoStrategy]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_properties() -> List[PropertyAsset]:
    return [
        PropertyAsset("Cypress MOB Tower I", "MOB / On-Campus", "Atlanta", "GA", 125000, "Piedmont Healthcare",
                      "A1 (Moody's)", 4.8, "NNN", 8.5, 6.00, 82.5),
        PropertyAsset("Cypress MOB Tower II", "MOB / On-Campus", "Atlanta", "GA", 95000, "Piedmont Healthcare",
                      "A1 (Moody's)", 3.6, "NNN", 7.2, 6.10, 60.5),
        PropertyAsset("Magnolia ASC Center", "ASC", "Dallas", "TX", 45000, "USPI (Tenet)",
                      "BB+ (S&P)", 2.8, "NNN", 12.0, 6.75, 41.5),
        PropertyAsset("Redwood Behavioral HQ", "Behavioral Health", "Philadelphia", "PA", 65000, "Universal Health Services",
                      "BB (S&P)", 2.2, "NNN", 10.5, 7.20, 30.5),
        PropertyAsset("Oak Lab / Pathology", "Lab / Pathology", "Chicago", "IL", 85000, "Quest Diagnostics",
                      "BBB+ (S&P)", 3.5, "NNN", 15.0, 6.50, 53.8),
        PropertyAsset("Pine Dialysis Portfolio", "Dialysis", "Tampa", "FL", 120000, "DaVita",
                      "BB+ (S&P)", 4.2, "NNN", 12.5, 6.80, 61.8),
        PropertyAsset("Laurel Derm Clinic Portfolio", "Physician MOB", "Charlotte", "NC", 42000, "Advanced Dermatology",
                      "N/A (PE-owned)", 1.8, "Modified NNN", 8.0, 7.40, 24.3),
        PropertyAsset("Cedar Cardiology Campus", "MOB / Off-Campus", "Phoenix", "AZ", 58000, "Cardiovascular Associates",
                      "N/A (PE-owned)", 2.5, "NNN", 9.5, 7.25, 34.5),
        PropertyAsset("Willow Fertility Flagship", "Physician MOB", "Austin", "TX", 38000, "Fertility Partners",
                      "N/A (PE-owned)", 1.5, "Modified NNN", 8.5, 7.50, 20.0),
        PropertyAsset("Spruce Imaging Center Network", "Imaging", "Denver", "CO", 55000, "RadNet",
                      "B+ (S&P)", 2.2, "NNN", 11.0, 7.00, 31.5),
        PropertyAsset("Fir Urgent Care Portfolio", "Urgent Care", "Seattle", "WA", 48000, "CareNow (HCA)",
                      "A3 (Moody's)", 2.0, "NNN", 9.0, 6.50, 30.8),
        PropertyAsset("Aspen Vision Centers", "Physician MOB", "Minneapolis", "MN", 42000, "Pacific Eye Partners",
                      "N/A (PE-owned)", 1.6, "Modified NNN", 7.8, 7.35, 21.8),
        PropertyAsset("Ash Infusion Suite Portfolio", "Infusion", "Boston", "MA", 35000, "Option Care Health",
                      "B+ (S&P)", 1.4, "NNN", 10.5, 7.00, 20.0),
        PropertyAsset("Maple Urology Clinic Network", "Physician MOB", "Raleigh", "NC", 40000, "Urology Associates",
                      "N/A (PE-owned)", 1.7, "Modified NNN", 9.0, 7.30, 23.3),
        PropertyAsset("Sage Home Health Dispatch", "Administrative", "Nashville", "TN", 35000, "LHC Group",
                      "BBB (S&P)", 1.2, "Gross", 6.5, 7.75, 15.5),
        PropertyAsset("Linden Behavioral Satellite Network", "Behavioral Health", "Columbus", "OH", 72000, "Acadia Healthcare",
                      "B+ (S&P)", 2.5, "NNN", 11.5, 7.50, 33.3),
        PropertyAsset("Basil Dental DSO Flagship Centers", "Dental MOB", "Indianapolis", "IN", 68000, "Heartland Dental",
                      "N/A (PE-owned)", 2.8, "NNN", 10.0, 7.20, 38.9),
        PropertyAsset("Thyme Specialty Pharmacy Hub", "Specialty Pharma", "Newark", "NJ", 55000, "Accredo (Cigna)",
                      "A (S&P)", 2.2, "NNN", 12.0, 6.40, 34.4),
        PropertyAsset("Hemlock Ortho ASC Center", "ASC", "Miami", "FL", 52000, "United Surgical Partners",
                      "BB+ (S&P)", 3.1, "NNN", 13.0, 6.70, 46.3),
        PropertyAsset("Poplar Nursing / SNF Portfolio", "SNF", "Cleveland", "OH", 105000, "Ensign Group",
                      "BB (S&P)", 3.5, "NNN", 11.5, 8.00, 43.8),
    ]


def _build_sectors(props: List[PropertyAsset]) -> List[SectorExposure]:
    buckets: dict = {}
    for p in props:
        b = buckets.setdefault(p.sector, {"count": 0, "sqft": 0, "rent": 0.0, "value": 0.0, "cap_sum": 0.0, "lease_sum": 0.0})
        b["count"] += 1
        b["sqft"] += p.sqft
        b["rent"] += p.annual_rent_m
        b["value"] += p.value_m
        b["cap_sum"] += p.cap_rate_pct
        b["lease_sum"] += p.lease_years_remaining
    rows = []
    for sector, d in buckets.items():
        acap = d["cap_sum"] / d["count"] if d["count"] else 0
        alease = d["lease_sum"] / d["count"] if d["count"] else 0
        rows.append(SectorExposure(
            sector=sector, property_count=d["count"],
            total_sqft=d["sqft"],
            total_rent_m=round(d["rent"], 1),
            total_value_m=round(d["value"], 1),
            avg_cap_rate_pct=round(acap, 2),
            avg_lease_years=round(alease, 1),
        ))
    return sorted(rows, key=lambda x: x.total_value_m, reverse=True)


def _build_tenants() -> List[TenantConcentration]:
    return [
        TenantConcentration("Piedmont Healthcare", "Health System", "A1 (Moody's)", 2, 220000, 8.4, 0.165, 12),
        TenantConcentration("USPI (Tenet)", "Hospital System", "BB+ (S&P)", 2, 97000, 5.9, 0.115, 15),
        TenantConcentration("DaVita", "Public Company", "BB+ (S&P)", 1, 120000, 4.2, 0.082, 10),
        TenantConcentration("Quest Diagnostics", "Public Company", "BBB+ (S&P)", 1, 85000, 3.5, 0.068, 10),
        TenantConcentration("Ensign Group", "Public Company", "BB (S&P)", 1, 105000, 3.5, 0.068, 8),
        TenantConcentration("Heartland Dental", "PE-backed DSO", "N/A", 1, 68000, 2.8, 0.055, 6),
        TenantConcentration("Universal Health Services", "Public Company", "BB (S&P)", 1, 65000, 2.2, 0.043, 9),
        TenantConcentration("RadNet", "Public Company", "B+ (S&P)", 1, 55000, 2.2, 0.043, 7),
        TenantConcentration("Advanced Dermatology", "PE-backed Platform", "N/A", 1, 42000, 1.8, 0.035, 5),
        TenantConcentration("Acadia Healthcare", "Public Company", "B+ (S&P)", 1, 72000, 2.5, 0.049, 8),
        TenantConcentration("Accredo (Cigna)", "Public Company", "A (S&P)", 1, 55000, 2.2, 0.043, 9),
        TenantConcentration("Cardiovascular Associates", "PE-backed Platform", "N/A", 1, 58000, 2.5, 0.049, 4),
        TenantConcentration("LHC Group", "Public Company", "BBB (S&P)", 1, 35000, 1.2, 0.024, 7),
        TenantConcentration("United Surgical Partners", "Subsidiary", "BB+ (S&P)", 1, 52000, 3.1, 0.061, 12),
        TenantConcentration("Option Care Health", "Public Company", "B+ (S&P)", 1, 35000, 1.4, 0.027, 8),
        TenantConcentration("Pacific Eye Partners", "PE-backed Platform", "N/A", 1, 42000, 1.6, 0.031, 5),
        TenantConcentration("Urology Associates", "PE-backed Platform", "N/A", 1, 40000, 1.7, 0.033, 6),
        TenantConcentration("CareNow (HCA)", "Subsidiary", "A3 (Moody's)", 1, 48000, 2.0, 0.039, 9),
        TenantConcentration("Fertility Partners", "PE-backed Platform", "N/A", 1, 38000, 1.5, 0.029, 5),
    ]


def _build_expirations() -> List[LeaseExpiration]:
    return [
        LeaseExpiration(2026, 0, 0.0, 0.0, 0.0),
        LeaseExpiration(2027, 1, 1.2, 7.75, 0.85),
        LeaseExpiration(2028, 0, 0.0, 0.0, 0.0),
        LeaseExpiration(2029, 2, 3.2, 7.10, 0.85),
        LeaseExpiration(2030, 1, 1.5, 7.50, 0.90),
        LeaseExpiration(2031, 2, 3.7, 7.13, 0.88),
        LeaseExpiration(2032, 3, 5.8, 7.02, 0.92),
        LeaseExpiration(2033, 3, 7.4, 6.87, 0.90),
        LeaseExpiration(2034, 2, 4.6, 6.60, 0.95),
        LeaseExpiration(2035, 2, 5.6, 6.76, 0.90),
        LeaseExpiration(2036, 1, 3.5, 8.00, 0.80),
        LeaseExpiration(2037, 2, 5.2, 6.75, 0.95),
        LeaseExpiration(2038, 1, 3.1, 6.70, 0.95),
    ]


def _build_benchmarks() -> List[CapRateBenchmark]:
    return [
        CapRateBenchmark("MOB / On-Campus (IG tenant)", 5.50, 6.00, 6.50, 25, 50),
        CapRateBenchmark("MOB / Off-Campus (IG tenant)", 6.25, 6.75, 7.25, 25, 75),
        CapRateBenchmark("Physician MOB (PE-owned)", 7.00, 7.40, 7.80, 35, 100),
        CapRateBenchmark("ASC (Strong Credit)", 6.25, 6.75, 7.25, 20, 75),
        CapRateBenchmark("Lab / Pathology (IG)", 6.00, 6.50, 7.00, 15, 50),
        CapRateBenchmark("Imaging / Radiology", 6.50, 7.00, 7.50, 25, 75),
        CapRateBenchmark("Dialysis (DaVita/FMC)", 6.25, 6.75, 7.25, 20, 50),
        CapRateBenchmark("Behavioral Health", 6.75, 7.40, 8.00, 40, 125),
        CapRateBenchmark("SNF / Skilled Nursing", 7.50, 8.00, 8.75, 50, 150),
        CapRateBenchmark("Urgent Care", 6.00, 6.50, 7.00, 20, 75),
        CapRateBenchmark("Dental MOB", 6.75, 7.25, 7.75, 30, 100),
        CapRateBenchmark("Specialty Pharmacy", 6.00, 6.50, 7.00, 15, 50),
    ]


def _build_propcos() -> List[PropCoStrategy]:
    return [
        PropCoStrategy("Project Cypress — GI Network", "Sale-leaseback to MedREIT", 8, 450.0, 425.0, 2.5, "Healthpeak, Welltower, HTA"),
        PropCoStrategy("Project Magnolia — MSK Platform", "PropCo/OpCo separation", 12, 285.0, 265.0, 2.8, "Healthpeak, Diversified Healthcare Trust"),
        PropCoStrategy("Project Redwood — Behavioral", "Sale-leaseback Stage 1", 6, 145.0, 135.0, 1.8, "Medical Properties Trust, PE re-funds"),
        PropCoStrategy("Project Cedar — Cardiology", "Ground lease + building sale", 4, 95.0, 82.0, 3.1, "Healthpeak, Welltower"),
        PropCoStrategy("Project Laurel — Derma", "Build-to-suit + sale-leaseback", 10, 175.0, 165.0, 2.2, "Diversified Healthcare Trust"),
    ]


def compute_medical_realestate() -> REResult:
    corpus = _load_corpus()
    properties = _build_properties()
    sectors = _build_sectors(properties)
    tenants = _build_tenants()
    expirations = _build_expirations()
    benchmarks = _build_benchmarks()
    propcos = _build_propcos()

    total_sqft = sum(p.sqft for p in properties)
    total_rent = sum(p.annual_rent_m for p in properties)
    total_value = sum(p.value_m for p in properties)
    wtd_cap = sum(p.cap_rate_pct * p.value_m for p in properties) / total_value if total_value > 0 else 0
    wtd_lease = sum(p.lease_years_remaining * p.value_m for p in properties) / total_value if total_value > 0 else 0
    nnn = sum(1 for p in properties if "NNN" in p.nnn_or_gross)
    nnn_pct = nnn / len(properties) if properties else 0

    return REResult(
        total_properties=len(properties),
        total_sqft_mm=round(total_sqft / 1_000_000, 2),
        total_annual_rent_m=round(total_rent, 1),
        total_value_b=round(total_value / 1000.0, 2),
        weighted_cap_rate_pct=round(wtd_cap, 2),
        weighted_lease_years=round(wtd_lease, 1),
        nnn_pct=round(nnn_pct, 4),
        properties=properties,
        sectors=sectors,
        tenants=tenants,
        expirations=expirations,
        benchmarks=benchmarks,
        propcos=propcos,
        corpus_deal_count=len(corpus),
    )
