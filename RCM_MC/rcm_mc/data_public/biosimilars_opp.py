"""Biosimilars Opportunity Analyzer.

Models biosimilar substitution economics for PE-backed provider platforms
with buy-and-bill exposure (infusion, specialty pharmacy, oncology, rheum).

Key analytics:
- LOE wave schedule (Humira, Stelara, Eylea, etc.)
- Reference drug vs biosimilar pricing spread
- Provider margin capture on switch
- Interchangeable status & pharmacy auto-sub
- ASP+6% buy-and-bill economics
- Medicare Part B demo impact
- Volume forecast post-LOE
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class BiosimilarWave:
    reference_drug: str
    class_area: str
    loe_year: int
    reference_annual_sales_b: float
    biosimilars_launched: int
    interchangeable_approved: bool
    reference_price_decline_pct: float
    biosimilar_adoption_y3_pct: float


@dataclass
class ProductEconomics:
    reference_drug: str
    reference_wac_per_dose: float
    biosimilar_wac_per_dose: float
    asp_plus_6_reference: float
    asp_plus_6_biosimilar: float
    provider_margin_reference: float
    provider_margin_biosimilar: float
    annual_volume_platform: int
    revenue_opportunity_mm: float


@dataclass
class ProviderSite:
    site_type: str
    biologic_volume_annual: int
    biosimilar_adoption_pct: float
    margin_per_dose: float
    annual_biosimilar_margin_mm: float
    growth_y3_pct: float


@dataclass
class InterchangeableStatus:
    biosimilar: str
    reference: str
    interchangeable_date: str
    state_pharmacy_sub_allowed: int
    notification_requirement: str
    automatic_sub_impact: str


@dataclass
class CompetitiveDynamic:
    class_area: str
    biosimilar_count: int
    price_erosion_y1_pct: float
    price_erosion_y3_pct: float
    market_leader_share_y3_pct: float
    provider_negotiating_leverage: str


@dataclass
class BiosimilarsResult:
    total_loe_waves: int
    total_reference_sales_b: float
    total_annual_opportunity_mm: float
    total_margin_mm: float
    weighted_adoption_y3_pct: float
    waves: List[BiosimilarWave]
    economics: List[ProductEconomics]
    sites: List[ProviderSite]
    interchangeable: List[InterchangeableStatus]
    dynamics: List[CompetitiveDynamic]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 99):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_waves() -> List[BiosimilarWave]:
    return [
        BiosimilarWave("Humira (adalimumab)", "Anti-TNF (IBD/Rheum)", 2023, 21.5, 10, True, 0.60, 0.45),
        BiosimilarWave("Stelara (ustekinumab)", "IL-12/23 (IBD/Psoriasis)", 2025, 10.8, 5, False, 0.40, 0.32),
        BiosimilarWave("Eylea (aflibercept)", "Anti-VEGF (Ophthalmology)", 2025, 9.4, 3, False, 0.35, 0.28),
        BiosimilarWave("Avastin (bevacizumab)", "Anti-VEGF (Oncology)", 2019, 7.2, 4, False, 0.68, 0.58),
        BiosimilarWave("Rituxan (rituximab)", "Anti-CD20 (Oncology/Rheum)", 2018, 6.1, 4, False, 0.62, 0.52),
        BiosimilarWave("Herceptin (trastuzumab)", "HER2 (Oncology)", 2019, 7.1, 6, False, 0.65, 0.55),
        BiosimilarWave("Neulasta (pegfilgrastim)", "G-CSF (Oncology)", 2018, 4.5, 5, False, 0.72, 0.62),
        BiosimilarWave("Remicade (infliximab)", "Anti-TNF (IBD)", 2016, 4.9, 4, False, 0.58, 0.48),
        BiosimilarWave("Lantus (insulin glargine)", "Long-Acting Insulin", 2021, 3.2, 2, True, 0.78, 0.75),
        BiosimilarWave("Prolia / Xgeva (denosumab)", "RANK-L (Osteo/Onc)", 2025, 5.8, 3, False, 0.38, 0.30),
    ]


def _build_economics() -> List[ProductEconomics]:
    return [
        ProductEconomics("Humira", 7145.0, 2860.0, 7574.0, 3032.0, 429.0, 172.0, 8500, 2.18),
        ProductEconomics("Stelara", 25600.0, 15360.0, 27136.0, 16282.0, 1536.0, 922.0, 1250, 0.77),
        ProductEconomics("Eylea", 2070.0, 1345.0, 2194.0, 1426.0, 124.0, 81.0, 28000, 1.20),
        ProductEconomics("Avastin", 4815.0, 1540.0, 5104.0, 1632.0, 289.0, 92.0, 18500, 1.70),
        ProductEconomics("Rituxan", 12415.0, 4715.0, 13160.0, 4998.0, 745.0, 283.0, 6200, 1.75),
        ProductEconomics("Herceptin", 7420.0, 2600.0, 7865.0, 2756.0, 445.0, 156.0, 4800, 0.75),
        ProductEconomics("Neulasta", 6985.0, 1955.0, 7404.0, 2072.0, 419.0, 117.0, 12500, 1.46),
        ProductEconomics("Remicade", 1280.0, 540.0, 1357.0, 572.0, 77.0, 32.0, 15200, 0.49),
        ProductEconomics("Prolia / Xgeva", 1250.0, 775.0, 1325.0, 822.0, 75.0, 47.0, 9500, 0.27),
    ]


def _build_sites() -> List[ProviderSite]:
    return [
        ProviderSite("Oncology Infusion Centers", 95000, 0.62, 385.0, 22.67, 0.48),
        ProviderSite("Rheumatology Practice Infusion", 62000, 0.55, 285.0, 9.72, 0.42),
        ProviderSite("GI / IBD Infusion Suites", 48500, 0.58, 325.0, 9.14, 0.45),
        ProviderSite("Ophthalmology Intravitreal", 125000, 0.35, 95.0, 4.16, 0.55),
        ProviderSite("Dermatology Biologics Clinic", 38500, 0.52, 245.0, 4.91, 0.38),
        ProviderSite("Home Infusion Provider", 32000, 0.68, 215.0, 4.68, 0.52),
        ProviderSite("Hospital Outpatient Dept (HOPD)", 148000, 0.45, 165.0, 10.99, 0.32),
        ProviderSite("Specialty Pharmacy Dispensing", 98000, 0.72, 48.0, 3.39, 0.58),
    ]


def _build_interchangeable() -> List[InterchangeableStatus]:
    return [
        InterchangeableStatus("Cyltezo (adalimumab-adbm)", "Humira", "2023-10-15", 48, "none (auto-sub)", "5-8% market share capture from auto-sub"),
        InterchangeableStatus("Semglee (insulin glargine-yfgn)", "Lantus", "2021-07-28", 50, "none", "significant auto-sub impact on retail Rx"),
        InterchangeableStatus("Rezvoglar (insulin glargine-aglr)", "Lantus", "2023-11-16", 48, "notify prescriber", "moderate capture"),
        InterchangeableStatus("Abrilada (adalimumab-afzb)", "Humira", "2024-01-11", 42, "notify prescriber", "growing share"),
        InterchangeableStatus("Hadlima (adalimumab-bwwd)", "Humira", "TBD 2025", 0, "pending", "awaiting decision"),
        InterchangeableStatus("Wyost (denosumab-bbdz)", "Xgeva", "TBD", 0, "pending", "not yet launched"),
    ]


def _build_dynamics() -> List[CompetitiveDynamic]:
    return [
        CompetitiveDynamic("Anti-TNF", 10, 0.18, 0.58, 0.32, "high (10 biosimilars)"),
        CompetitiveDynamic("Anti-VEGF Oncology", 4, 0.22, 0.68, 0.42, "moderate"),
        CompetitiveDynamic("Anti-VEGF Ophthalmology", 3, 0.12, 0.35, 0.52, "low (new wave 2025)"),
        CompetitiveDynamic("IL-12/23", 5, 0.15, 0.40, 0.48, "moderate (emerging)"),
        CompetitiveDynamic("Anti-CD20", 4, 0.25, 0.62, 0.38, "high"),
        CompetitiveDynamic("HER2", 6, 0.28, 0.65, 0.35, "high"),
        CompetitiveDynamic("G-CSF", 5, 0.35, 0.72, 0.32, "very high"),
        CompetitiveDynamic("Long-Acting Insulin", 2, 0.45, 0.78, 0.55, "moderate"),
        CompetitiveDynamic("RANK-L", 3, 0.10, 0.38, 0.58, "low (new 2025)"),
    ]


def compute_biosimilars_opp() -> BiosimilarsResult:
    corpus = _load_corpus()

    waves = _build_waves()
    economics = _build_economics()
    sites = _build_sites()
    interchangeable = _build_interchangeable()
    dynamics = _build_dynamics()

    total_ref = sum(w.reference_annual_sales_b for w in waves)
    total_opp = sum(e.revenue_opportunity_mm for e in economics)
    total_margin = sum(s.annual_biosimilar_margin_mm for s in sites)
    weighted_adopt = sum(w.biosimilar_adoption_y3_pct * w.reference_annual_sales_b for w in waves) / total_ref if total_ref else 0

    return BiosimilarsResult(
        total_loe_waves=len(waves),
        total_reference_sales_b=round(total_ref, 2),
        total_annual_opportunity_mm=round(total_opp, 2),
        total_margin_mm=round(total_margin, 2),
        weighted_adoption_y3_pct=round(weighted_adopt, 4),
        waves=waves,
        economics=economics,
        sites=sites,
        interchangeable=interchangeable,
        dynamics=dynamics,
        corpus_deal_count=len(corpus),
    )
