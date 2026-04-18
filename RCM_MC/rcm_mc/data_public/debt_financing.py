"""Debt Financing / LBO Commitment Tracker.

Tracks debt commitment packages across active LBO financings:
underwriters, syndication progress, pricing (SOFR+), flex terms,
covenant structure, and market clearing benchmarks.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class DebtFacility:
    deal: str
    sector: str
    tranche: str
    size_m: float
    lead_arranger: str
    sofr_spread_bps: int
    floor_bps: int
    oid_pts: float
    maturity_years: int
    tenor: str
    call_protection: str
    covenant_lite: bool


@dataclass
class SyndicationStatus:
    deal: str
    total_package_m: float
    committed_m: float
    allocation_m: float
    accounts_participating: int
    oversubscribed_x: float
    launch_date: str
    target_close: str
    status: str
    flex_used_bps: int


@dataclass
class PricingBenchmark:
    sector: str
    segment: str
    median_first_lien_spread: int
    median_second_lien_spread: int
    median_leverage: float
    median_interest_cov: float
    clearing_rate_pct: float


@dataclass
class CovenantPackage:
    deal: str
    cov_lite: bool
    max_leverage_covenant: float
    leverage_at_close: float
    headroom_pct: float
    interest_cov_covenant: float
    capex_flex_m: float
    restricted_payment_basket_m: float
    incremental_facility_m: float


@dataclass
class FlexAnalysis:
    deal: str
    flex_spread_bps: int
    flex_oid_pts: float
    flex_caps_effective: str
    mfn_protection: bool
    structure_flex: str


@dataclass
class LenderBook:
    lender: str
    commitments_m: float
    deals_count: int
    avg_hold_m: float
    sectors_active: str
    relationship_tier: str


@dataclass
class DebtResult:
    total_financings: int
    total_package_m: float
    total_committed_m: float
    avg_sofr_spread: int
    cov_lite_pct: float
    avg_leverage: float
    facilities: List[DebtFacility]
    syndications: List[SyndicationStatus]
    pricing: List[PricingBenchmark]
    covenants: List[CovenantPackage]
    flex: List[FlexAnalysis]
    lenders: List[LenderBook]
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


def _build_facilities() -> List[DebtFacility]:
    return [
        DebtFacility("Project Azalea — GI Network SE", "Gastroenterology", "1L Term Loan B", 450.0, "JPM + BofA",
                     475, 100, 0.50, 7, "7y", "101 soft call 6mo", True),
        DebtFacility("Project Azalea — GI Network SE", "Gastroenterology", "Revolver", 75.0, "JPM",
                     350, 50, 0.0, 5, "5y", "None", False),
        DebtFacility("Project Azalea — GI Network SE", "Gastroenterology", "2L Term Loan", 120.0, "Apollo Direct",
                     750, 100, 1.00, 8, "8y", "103/102/101", False),
        DebtFacility("Project Magnolia — MSK Platform", "MSK / Ortho", "1L TLB", 380.0, "Morgan Stanley",
                     500, 100, 0.75, 7, "7y", "101 soft call 6mo", True),
        DebtFacility("Project Magnolia — MSK Platform", "MSK / Ortho", "Revolver", 60.0, "Morgan Stanley",
                     375, 50, 0.0, 5, "5y", "None", False),
        DebtFacility("Project Cypress — GI Network", "Gastroenterology", "1L TLB", 525.0, "Goldman Sachs",
                     450, 100, 0.25, 7, "7y", "101 soft call 6mo", True),
        DebtFacility("Project Cypress — GI Network", "Gastroenterology", "Delayed Draw", 100.0, "Goldman Sachs",
                     475, 100, 0.50, 7, "7y", "Matches TLB", True),
        DebtFacility("Project Willow — Fertility", "Fertility / IVF", "1L TLB", 290.0, "Jefferies",
                     525, 100, 1.00, 7, "7y", "101 soft call 6mo", True),
        DebtFacility("Project Willow — Fertility", "Fertility / IVF", "Unitranche", 180.0, "Ares Capital",
                     625, 100, 1.25, 7, "7y", "101 soft call 12mo", True),
        DebtFacility("Project Cedar — Cardiology", "Cardiology", "1L TLB", 410.0, "BofA + Citi",
                     475, 100, 0.50, 7, "7y", "101 soft call 6mo", True),
        DebtFacility("Project Cedar — Cardiology", "Cardiology", "Revolver", 75.0, "BofA",
                     375, 50, 0.0, 5, "5y", "None", False),
        DebtFacility("Project Laurel — Dermatology", "Dermatology", "Unitranche", 220.0, "Blackstone Private Credit",
                     600, 100, 1.00, 7, "7y", "101 soft call 12mo", True),
        DebtFacility("Project Spruce — Radiology", "Radiology", "1L TLB", 340.0, "Wells Fargo",
                     500, 100, 0.75, 7, "7y", "101 soft call 6mo", True),
        DebtFacility("Project Aspen — Eye Care", "Eye Care", "Unitranche", 195.0, "Blue Owl Capital",
                     625, 100, 1.00, 7, "7y", "101 soft call 12mo", True),
        DebtFacility("Project Maple — Urology", "Urology", "1L TLB", 165.0, "Deutsche Bank",
                     525, 100, 0.75, 7, "7y", "101 soft call 6mo", True),
        DebtFacility("Project Ash — Infusion", "Infusion", "1L TLB", 485.0, "Credit Suisse + RBC",
                     450, 100, 0.25, 7, "7y", "101 soft call 6mo", True),
        DebtFacility("Project Fir — Lab / Pathology", "Lab Services", "1L TLB", 425.0, "JPM",
                     475, 100, 0.50, 7, "7y", "101 soft call 6mo", True),
        DebtFacility("Project Oak — RCM SaaS", "RCM", "Unitranche", 240.0, "Golub Capital",
                     550, 100, 1.00, 7, "7y", "101 soft call 12mo", True),
    ]


def _build_syndications() -> List[SyndicationStatus]:
    return [
        SyndicationStatus("Project Azalea — GI Network SE", 645.0, 645.0, 480.0, 28, 1.85, "2026-03-15", "2026-04-30", "clearing", 25),
        SyndicationStatus("Project Magnolia — MSK Platform", 440.0, 440.0, 410.0, 24, 1.40, "2026-02-20", "2026-03-25", "closed", 0),
        SyndicationStatus("Project Cypress — GI Network", 625.0, 625.0, 580.0, 32, 1.75, "2026-02-05", "2026-03-15", "closed", 0),
        SyndicationStatus("Project Willow — Fertility", 470.0, 470.0, 325.0, 18, 1.55, "2026-03-01", "2026-04-15", "final allocation", 25),
        SyndicationStatus("Project Cedar — Cardiology", 485.0, 485.0, 455.0, 26, 1.45, "2026-01-20", "2026-02-28", "closed", 0),
        SyndicationStatus("Project Laurel — Dermatology", 220.0, 220.0, 220.0, 8, 1.10, "2026-01-10", "2026-02-10", "closed", 0),
        SyndicationStatus("Project Spruce — Radiology", 340.0, 340.0, 310.0, 22, 1.35, "2026-02-10", "2026-03-20", "closed", 0),
        SyndicationStatus("Project Aspen — Eye Care", 195.0, 195.0, 195.0, 6, 1.00, "2026-03-20", "2026-04-20", "clearing", 0),
        SyndicationStatus("Project Maple — Urology", 165.0, 140.0, 140.0, 12, 1.20, "2026-04-01", "2026-05-15", "active marketing", 0),
        SyndicationStatus("Project Ash — Infusion", 485.0, 485.0, 425.0, 30, 1.60, "2026-02-25", "2026-04-08", "final allocation", 12),
        SyndicationStatus("Project Fir — Lab / Pathology", 425.0, 425.0, 398.0, 28, 1.50, "2026-01-25", "2026-03-10", "closed", 0),
        SyndicationStatus("Project Oak — RCM SaaS", 240.0, 240.0, 240.0, 10, 1.15, "2026-02-15", "2026-03-20", "closed", 0),
    ]


def _build_pricing() -> List[PricingBenchmark]:
    return [
        PricingBenchmark("Physician Services", "Multi-specialty", 475, 750, 5.80, 2.75, 94.2),
        PricingBenchmark("Physician Services", "Specialty", 450, 725, 5.60, 2.85, 95.5),
        PricingBenchmark("Behavioral Health", "Outpatient", 500, 775, 5.50, 2.60, 92.8),
        PricingBenchmark("Home Health", "Medicare-mix", 525, 800, 5.20, 2.50, 91.5),
        PricingBenchmark("Dental DSO", "Scale", 450, 700, 5.75, 2.90, 96.0),
        PricingBenchmark("Fertility / IVF", "Multi-state", 525, 800, 5.40, 2.65, 93.0),
        PricingBenchmark("Dermatology", "Cash + medical", 450, 700, 5.85, 2.95, 96.5),
        PricingBenchmark("Ophthalmology", "Multi-state", 475, 725, 5.50, 2.80, 95.2),
        PricingBenchmark("Radiology", "Teleradiology", 500, 775, 5.30, 2.75, 93.8),
        PricingBenchmark("Infusion", "Specialty drugs", 450, 750, 5.75, 2.85, 94.8),
        PricingBenchmark("Lab Services", "Anatomic pathology", 475, 725, 5.60, 2.85, 94.5),
        PricingBenchmark("RCM / Healthtech SaaS", "PE-backed SaaS", 525, 800, 5.80, 2.55, 92.0),
        PricingBenchmark("GI / Gastro", "Multi-state", 475, 750, 5.70, 2.80, 95.0),
        PricingBenchmark("Cardiology", "Procedural", 475, 750, 5.55, 2.85, 95.2),
        PricingBenchmark("MSK / Ortho", "Multi-specialty", 500, 775, 5.45, 2.75, 94.0),
        PricingBenchmark("Urology", "Multi-specialty", 525, 800, 5.35, 2.70, 93.5),
    ]


def _build_covenants() -> List[CovenantPackage]:
    return [
        CovenantPackage("Project Azalea — GI Network SE", True, 7.50, 6.20, 0.173, 1.75, 25.0, 15.0, 180.0),
        CovenantPackage("Project Magnolia — MSK Platform", True, 7.00, 5.90, 0.157, 1.75, 18.0, 12.0, 120.0),
        CovenantPackage("Project Cypress — GI Network", True, 7.50, 6.40, 0.147, 1.75, 28.0, 18.0, 200.0),
        CovenantPackage("Project Willow — Fertility", True, 7.25, 5.85, 0.193, 1.75, 22.0, 14.0, 140.0),
        CovenantPackage("Project Cedar — Cardiology", True, 7.00, 5.70, 0.186, 1.75, 20.0, 13.0, 150.0),
        CovenantPackage("Project Laurel — Dermatology", True, 7.25, 6.10, 0.159, 1.75, 12.0, 8.0, 90.0),
        CovenantPackage("Project Spruce — Radiology", True, 6.75, 5.40, 0.200, 1.75, 18.0, 10.0, 110.0),
        CovenantPackage("Project Aspen — Eye Care", True, 7.25, 5.80, 0.200, 1.75, 12.0, 8.0, 85.0),
        CovenantPackage("Project Maple — Urology", False, 7.00, 5.75, 0.179, 1.85, 10.0, 7.0, 60.0),
        CovenantPackage("Project Ash — Infusion", True, 7.25, 6.30, 0.131, 1.75, 30.0, 20.0, 200.0),
        CovenantPackage("Project Fir — Lab / Pathology", True, 7.00, 5.85, 0.164, 1.75, 25.0, 16.0, 170.0),
        CovenantPackage("Project Oak — RCM SaaS", True, 7.50, 6.50, 0.133, 1.75, 15.0, 12.0, 120.0),
    ]


def _build_flex() -> List[FlexAnalysis]:
    return [
        FlexAnalysis("Project Azalea — GI Network SE", 50, 0.50, "25bps used, 25bps remaining", True, "±10% tranche sizing"),
        FlexAnalysis("Project Magnolia — MSK Platform", 50, 0.75, "unused", True, "±10% tranche sizing"),
        FlexAnalysis("Project Cypress — GI Network", 50, 0.50, "unused", True, "±10% tranche sizing"),
        FlexAnalysis("Project Willow — Fertility", 75, 1.00, "25bps used", True, "±15% tranche sizing"),
        FlexAnalysis("Project Cedar — Cardiology", 50, 0.75, "unused", True, "±10% tranche sizing"),
        FlexAnalysis("Project Laurel — Dermatology", 50, 0.75, "unused (direct lend)", True, "±10% tranche sizing"),
        FlexAnalysis("Project Spruce — Radiology", 50, 0.75, "unused", True, "±10% tranche sizing"),
        FlexAnalysis("Project Aspen — Eye Care", 75, 1.00, "unused (direct lend)", True, "±15% tranche sizing"),
        FlexAnalysis("Project Maple — Urology", 75, 1.00, "unused (in marketing)", True, "±15% tranche sizing"),
        FlexAnalysis("Project Ash — Infusion", 50, 0.75, "12bps used", True, "±10% tranche sizing"),
        FlexAnalysis("Project Fir — Lab / Pathology", 50, 0.50, "unused", True, "±10% tranche sizing"),
        FlexAnalysis("Project Oak — RCM SaaS", 50, 0.75, "unused (direct lend)", True, "±10% tranche sizing"),
    ]


def _build_lenders() -> List[LenderBook]:
    return [
        LenderBook("Apollo / Apollo Direct Lending", 680.0, 9, 75.6, "MSK, GI, Infusion, Derma", "tier 1"),
        LenderBook("Ares Capital", 540.0, 7, 77.1, "Fertility, Home Health, Dental", "tier 1"),
        LenderBook("Blackstone Private Credit (BXCI)", 495.0, 6, 82.5, "Derma, RCM, Eye Care, Behavioral", "tier 1"),
        LenderBook("Blue Owl Capital", 420.0, 5, 84.0, "Eye Care, MSK, Fertility", "tier 1"),
        LenderBook("Golub Capital", 385.0, 8, 48.1, "RCM, HCIT, Derma, Multi-specialty", "tier 1"),
        LenderBook("JPMorgan Chase", 920.0, 12, 76.7, "Multi-specialty, GI, Lab, Cardiology", "syndication"),
        LenderBook("Bank of America", 745.0, 10, 74.5, "Multi-specialty, Cardiology, GI, Home Health", "syndication"),
        LenderBook("Goldman Sachs", 680.0, 8, 85.0, "GI, MSK, Multi-specialty", "syndication"),
        LenderBook("Morgan Stanley", 585.0, 7, 83.6, "MSK, Derma, Fertility, Eye Care", "syndication"),
        LenderBook("Jefferies", 425.0, 6, 70.8, "Fertility, Behavioral, Derma, Vision", "syndication"),
        LenderBook("Owl Rock (Blue Owl)", 380.0, 5, 76.0, "Eye Care, Behavioral, Derma, RCM", "tier 1"),
        LenderBook("HPS Investment Partners", 340.0, 5, 68.0, "Behavioral, Infusion, Home Health", "tier 1"),
        LenderBook("Antares Capital", 315.0, 5, 63.0, "Multi-specialty, Derma, Home Health", "tier 1"),
        LenderBook("Churchill Asset Management", 285.0, 5, 57.0, "Dental, Derma, MSK, Vision", "tier 1"),
        LenderBook("Monroe Capital", 245.0, 5, 49.0, "MSK, Behavioral, Infusion", "tier 2"),
        LenderBook("Bain Capital Credit", 225.0, 4, 56.3, "MSK, GI, Derma, Fertility", "tier 2"),
    ]


def compute_debt_financing() -> DebtResult:
    corpus = _load_corpus()
    facilities = _build_facilities()
    syndications = _build_syndications()
    pricing = _build_pricing()
    covenants = _build_covenants()
    flex = _build_flex()
    lenders = _build_lenders()

    deals = {f.deal for f in facilities}
    total_package = sum(f.size_m for f in facilities)
    total_committed = sum(s.committed_m for s in syndications)
    avg_spread = sum(f.sofr_spread_bps for f in facilities) / len(facilities) if facilities else 0
    cov_lite_count = sum(1 for f in facilities if f.covenant_lite)
    cov_lite_pct = cov_lite_count / len(facilities) if facilities else 0
    avg_lev = sum(c.leverage_at_close for c in covenants) / len(covenants) if covenants else 0

    return DebtResult(
        total_financings=len(deals),
        total_package_m=round(total_package, 1),
        total_committed_m=round(total_committed, 1),
        avg_sofr_spread=int(round(avg_spread)),
        cov_lite_pct=round(cov_lite_pct, 4),
        avg_leverage=round(avg_lev, 2),
        facilities=facilities,
        syndications=syndications,
        pricing=pricing,
        covenants=covenants,
        flex=flex,
        lenders=lenders,
        corpus_deal_count=len(corpus),
    )
