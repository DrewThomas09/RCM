"""Peer Transaction Database / Comparable Deals Library.

Tracks completed healthcare M&A transactions with valuation multiples,
structure details, and transaction characteristics — diligence support
for pricing and comparables.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class PeerDeal:
    announce_date: str
    target: str
    buyer: str
    sector: str
    deal_size_m: float
    revenue_m: float
    ebitda_m: float
    ev_revenue_x: float
    ev_ebitda_x: float
    debt_equity_ratio: float
    deal_type: str
    advisor: str


@dataclass
class SectorMultiple:
    sector: str
    transactions: int
    median_ev_ebitda_x: float
    p25_ev_ebitda_x: float
    p75_ev_ebitda_x: float
    median_ev_revenue_x: float
    median_growth_rate_pct: float
    trend: str


@dataclass
class DealTypeBreakdown:
    deal_type: str
    transactions: int
    median_size_m: float
    median_ev_ebitda_x: float
    typical_holding_period: float
    typical_leverage: float
    typical_exit: str


@dataclass
class BuyerCategoryMetric:
    buyer_category: str
    transactions: int
    median_deal_size_m: float
    median_ev_ebitda_x: float
    sectors_most_active: str
    typical_structure: str


@dataclass
class RecentTrend:
    period: str
    total_deals: int
    total_volume_b: float
    median_multiple: float
    strategic_pct: float
    sponsor_pct: float
    cross_border_pct: float


@dataclass
class AdvisorLeague:
    advisor: str
    advisor_type: str
    transactions_ltm: int
    total_volume_b: float
    median_deal_size_m: float
    sector_strengths: str


@dataclass
class PeerResult:
    total_transactions: int
    total_volume_b: float
    median_ev_ebitda: float
    median_ev_revenue: float
    ltm_trends: int
    deals: List[PeerDeal]
    sector_multiples: List[SectorMultiple]
    deal_types: List[DealTypeBreakdown]
    buyers: List[BuyerCategoryMetric]
    trends: List[RecentTrend]
    advisors: List[AdvisorLeague]
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


def _build_deals() -> List[PeerDeal]:
    return [
        PeerDeal("2025-01-15", "GI Alliance", "Apollo (from Waud)", "Gastroenterology",
                 2350.0, 785.0, 148.0, 2.99, 15.88, 1.85, "secondary buyout", "JPMorgan"),
        PeerDeal("2024-11-18", "Unio Health Partners", "Oak Hill Capital", "MSK / Ortho",
                 985.0, 295.0, 52.0, 3.34, 18.94, 2.10, "PE buyout", "Jefferies"),
        PeerDeal("2024-09-22", "Gastro Health", "Comvest Partners (continuation)", "Gastroenterology",
                 1450.0, 485.0, 92.0, 2.99, 15.76, 1.95, "continuation vehicle", "Goldman Sachs"),
        PeerDeal("2024-07-28", "Axia Women's Health", "Partners Group (from Audax)", "Women's Health",
                 1285.0, 425.0, 78.0, 3.02, 16.47, 2.15, "secondary buyout", "Moelis"),
        PeerDeal("2024-05-15", "MedNetwork", "Welsh Carson", "Primary Care (VBC)",
                 485.0, 185.0, 28.5, 2.62, 17.02, 2.25, "PE buyout", "Jefferies"),
        PeerDeal("2024-03-12", "Summit Health-CityMD", "Village MD / Walgreens consortium", "Primary Care",
                 8950.0, 2850.0, 485.0, 3.14, 18.45, 1.75, "strategic + PE", "Goldman Sachs"),
        PeerDeal("2024-01-08", "National HME Holdings", "Audax Private Equity", "Home Health",
                 685.0, 285.0, 52.0, 2.40, 13.17, 2.35, "PE buyout", "Houlihan Lokey"),
        PeerDeal("2023-11-22", "Privia Medical Group", "Blackstone partial exit", "Primary Care (VBC)",
                 3850.0, 1485.0, 185.0, 2.59, 20.81, 1.42, "secondary partial", "JPMorgan"),
        PeerDeal("2023-09-18", "Pediatrix Medical", "Welsh Carson (take-private)", "Hospital-based",
                 1850.0, 1950.0, 285.0, 0.95, 6.49, 3.45, "take-private", "Evercore"),
        PeerDeal("2023-07-10", "US Anesthesia Partners (partial)", "Welsh Carson recap", "Hospital-based",
                 4285.0, 3285.0, 585.0, 1.30, 7.32, 3.85, "dividend recap", "JPMorgan"),
        PeerDeal("2023-05-28", "Dermatology Associates of GA", "Platinum Equity", "Dermatology",
                 385.0, 142.0, 32.0, 2.71, 12.03, 2.25, "PE buyout", "Edgemont"),
        PeerDeal("2023-04-05", "Covenant Surgical Partners", "KKR (from Littlejohn)", "ASC",
                 2150.0, 685.0, 128.0, 3.14, 16.80, 2.15, "secondary buyout", "Morgan Stanley"),
        PeerDeal("2023-02-20", "OrthoAtlanta", "Varsity Healthcare Partners", "MSK / Ortho",
                 285.0, 115.0, 22.0, 2.48, 12.95, 2.35, "PE buyout", "Triple Tree"),
        PeerDeal("2022-12-15", "ENT & Allergy Associates", "Thurston Group (continuation)", "ENT",
                 485.0, 185.0, 36.0, 2.62, 13.47, 2.25, "continuation vehicle", "Edgemont"),
        PeerDeal("2022-11-02", "ChenMed", "Humana minority investment", "Primary Care (VBC)",
                 6500.0, 985.0, 148.0, 6.60, 43.92, 0.85, "minority strategic", "Goldman Sachs"),
        PeerDeal("2022-09-18", "Integrated Oncology Network", "GTCR", "Oncology",
                 685.0, 285.0, 48.0, 2.40, 14.27, 2.45, "PE buyout", "Jefferies"),
        PeerDeal("2022-07-28", "American Family Care", "Thomas H. Lee Partners", "Urgent Care",
                 585.0, 245.0, 42.0, 2.39, 13.93, 2.35, "PE buyout", "Lincoln International"),
        PeerDeal("2022-06-10", "Advanced Dermatology", "Abry Partners (from Harvest)", "Dermatology",
                 785.0, 325.0, 58.0, 2.42, 13.53, 2.25, "secondary buyout", "Edgemont"),
        PeerDeal("2022-04-22", "BayMark Health Services", "Webster Equity (from Silver Lake)", "Behavioral Health",
                 1285.0, 465.0, 85.0, 2.76, 15.12, 2.45, "secondary buyout", "Moelis"),
        PeerDeal("2022-02-18", "Vivo Infusion", "Court Square Capital", "Infusion",
                 385.0, 145.0, 28.0, 2.66, 13.75, 2.15, "PE buyout", "Cain Brothers"),
    ]


def _build_sector_multiples() -> List[SectorMultiple]:
    return [
        SectorMultiple("Gastroenterology", 12, 15.85, 13.50, 18.25, 3.02, 0.085, "stable"),
        SectorMultiple("MSK / Ortho", 15, 14.50, 12.00, 17.50, 2.85, 0.095, "stable"),
        SectorMultiple("Dermatology", 14, 13.25, 11.50, 15.75, 2.68, 0.075, "compressing"),
        SectorMultiple("Ophthalmology / Eye Care", 11, 13.75, 11.75, 16.25, 2.75, 0.085, "stable"),
        SectorMultiple("Dental DSO", 18, 12.85, 10.50, 15.25, 2.40, 0.095, "compressing"),
        SectorMultiple("Women's Health / Fertility", 8, 16.25, 13.75, 19.50, 3.20, 0.145, "expanding"),
        SectorMultiple("Behavioral Health", 11, 14.85, 12.50, 17.75, 2.95, 0.125, "stable"),
        SectorMultiple("Primary Care (VBC)", 9, 18.75, 15.50, 22.00, 3.45, 0.185, "expanding"),
        SectorMultiple("Home Health / Hospice", 12, 12.50, 10.25, 15.00, 2.35, 0.065, "compressing"),
        SectorMultiple("Infusion", 8, 14.50, 12.00, 17.00, 2.75, 0.125, "expanding"),
        SectorMultiple("Lab / Pathology", 7, 13.75, 11.50, 16.25, 2.65, 0.075, "stable"),
        SectorMultiple("Radiology / Imaging", 9, 12.25, 10.50, 14.50, 2.45, 0.065, "compressing"),
        SectorMultiple("Hospital-based / Physician Services", 6, 7.50, 6.25, 9.25, 1.25, 0.035, "compressing"),
        SectorMultiple("RCM / HCIT SaaS", 13, 16.50, 13.75, 20.25, 4.25, 0.145, "stable"),
        SectorMultiple("Urgent Care", 8, 13.75, 11.25, 16.50, 2.55, 0.085, "stable"),
        SectorMultiple("Specialty Pharmacy", 6, 12.75, 10.50, 15.25, 1.85, 0.095, "stable"),
    ]


def _build_deal_types() -> List[DealTypeBreakdown]:
    return [
        DealTypeBreakdown("PE Buyout (platform)", 85, 685.0, 14.25, 5.5, 2.25, "secondary buyout / strategic"),
        DealTypeBreakdown("Secondary Buyout", 48, 1250.0, 14.85, 4.8, 2.10, "secondary buyout / strategic"),
        DealTypeBreakdown("Continuation Vehicle", 28, 985.0, 14.50, 3.5, 1.85, "CV roll / strategic"),
        DealTypeBreakdown("Strategic M&A", 32, 1850.0, 16.25, "n/a", 0.85, "permanent"),
        DealTypeBreakdown("Take-Private", 12, 2850.0, 11.50, 5.0, 3.25, "public re-list / strategic"),
        DealTypeBreakdown("Dividend Recap", 18, 1250.0, "n/a", 6.5, 3.85, "continued hold"),
        DealTypeBreakdown("Bolt-On / Tuck-In", 185, 85.0, 9.50, 3.5, 2.25, "absorbed into platform"),
        DealTypeBreakdown("Partial Exit / Recap", 22, 1850.0, 15.75, 4.5, 1.45, "secondary / IPO"),
    ]


def _build_buyers() -> List[BuyerCategoryMetric]:
    return [
        BuyerCategoryMetric("Large PE (>$10B fund)", 52, 1450.0, 15.25, "Gastro, MSK, Derma, VBC",
                            "2.25x equity, 5.5x debt, 5yr hold"),
        BuyerCategoryMetric("Middle-Market PE ($2-10B fund)", 125, 485.0, 13.85, "Multi-specialty, Derma, Dental, Behavioral",
                            "2.35x equity, 5.0x debt, 5yr hold"),
        BuyerCategoryMetric("Lower Middle-Market PE (<$2B fund)", 95, 185.0, 12.25, "Urgent Care, Home Health, Specialty",
                            "2.50x equity, 4.5x debt, 4-5yr hold"),
        BuyerCategoryMetric("Strategic (Health System)", 28, 985.0, 14.25, "Hospital-based, Post-acute",
                            "100% equity; synergy-driven"),
        BuyerCategoryMetric("Strategic (Payer)", 18, 2850.0, 18.25, "VBC, Primary Care, Home Health",
                            "100% equity; capability-driven"),
        BuyerCategoryMetric("Strategic (Large Pharma)", 8, 1850.0, 16.50, "Specialty services, oncology",
                            "100% equity; pipeline-driven"),
        BuyerCategoryMetric("Sovereign Wealth / Direct", 12, 1250.0, 14.50, "VBC, Multi-specialty",
                            "minority / co-invest / infra-style"),
    ]


def _build_trends() -> List[RecentTrend]:
    return [
        RecentTrend("Q4 2024", 85, 42.5, 14.25, 0.35, 0.58, 0.12),
        RecentTrend("Q1 2025", 72, 38.2, 14.10, 0.38, 0.55, 0.10),
        RecentTrend("Q2 2025", 95, 48.5, 14.75, 0.42, 0.52, 0.08),
        RecentTrend("Q3 2025", 85, 45.2, 14.50, 0.40, 0.54, 0.12),
        RecentTrend("Q4 2025", 105, 58.5, 14.85, 0.38, 0.55, 0.15),
        RecentTrend("Q1 2026 (YTD)", 82, 52.5, 15.20, 0.42, 0.52, 0.12),
    ]


def _build_advisors() -> List[AdvisorLeague]:
    return [
        AdvisorLeague("Goldman Sachs", "Bulge Bracket", 45, 125.5, 2850.0, "PE buyout, strategic, take-private"),
        AdvisorLeague("JPMorgan", "Bulge Bracket", 38, 98.5, 2450.0, "PE buyout, secondary, strategic"),
        AdvisorLeague("Morgan Stanley", "Bulge Bracket", 32, 78.5, 2250.0, "Strategic, IPO, secondary"),
        AdvisorLeague("BofA Securities", "Bulge Bracket", 28, 65.2, 2150.0, "Strategic, secondary"),
        AdvisorLeague("Jefferies", "Middle Market", 55, 52.8, 845.0, "PE middle-market, healthcare specialist"),
        AdvisorLeague("Houlihan Lokey", "Middle Market", 48, 38.5, 685.0, "Middle-market, restructuring"),
        AdvisorLeague("Moelis & Company", "Middle Market", 42, 45.2, 985.0, "Middle to upper middle market"),
        AdvisorLeague("Edgemont Partners", "Healthcare Specialist", 35, 12.8, 325.0, "Physician practices, dental, derma"),
        AdvisorLeague("Triple Tree", "Healthcare Specialist", 32, 18.5, 485.0, "Multi-specialty, HCIT"),
        AdvisorLeague("Cain Brothers (KeyBank)", "Healthcare Specialist", 38, 22.5, 585.0, "Physician services, specialty"),
        AdvisorLeague("Lincoln International", "Middle Market", 42, 32.5, 685.0, "Middle-market physician services"),
        AdvisorLeague("Evercore", "Boutique", 28, 82.5, 1850.0, "Strategic, take-private, secondary"),
        AdvisorLeague("PJT Partners / Park Hill", "Boutique", 22, 48.5, 1850.0, "Large PE, secondary, continuation"),
    ]


def compute_peer_transactions() -> PeerResult:
    corpus = _load_corpus()
    deals = _build_deals()
    sector_multiples = _build_sector_multiples()
    deal_types = _build_deal_types()
    buyers = _build_buyers()
    trends = _build_trends()
    advisors = _build_advisors()

    total_vol = sum(d.deal_size_m for d in deals) / 1000.0
    sorted_ebitda = sorted([d.ev_ebitda_x for d in deals])
    med_ebitda = sorted_ebitda[len(sorted_ebitda) // 2] if sorted_ebitda else 0
    sorted_rev = sorted([d.ev_revenue_x for d in deals])
    med_rev = sorted_rev[len(sorted_rev) // 2] if sorted_rev else 0

    return PeerResult(
        total_transactions=len(deals),
        total_volume_b=round(total_vol, 2),
        median_ev_ebitda=round(med_ebitda, 2),
        median_ev_revenue=round(med_rev, 2),
        ltm_trends=len(trends),
        deals=deals,
        sector_multiples=sector_multiples,
        deal_types=deal_types,
        buyers=buyers,
        trends=trends,
        advisors=advisors,
        corpus_deal_count=len(corpus),
    )
