"""GPO / Supply Chain Savings Tracker.

Tracks group purchasing organization (GPO) affiliation, supply-chain
spend categories, realized savings, rebate flow, and contract-level
savings vs market reference pricing across portfolio.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class GPOAffiliation:
    gpo_name: str
    parent: str
    portfolio_deals: int
    annual_spend_m: float
    realized_savings_m: float
    savings_rate_pct: float
    rebate_rate_pct: float
    contract_count: int
    tier: str


@dataclass
class SpendCategory:
    category: str
    annual_spend_m: float
    savings_rate_pct: float
    portfolio_savings_m: float
    rebate_pct: float
    top_contract: str


@dataclass
class DealSavings:
    deal: str
    sector: str
    annual_spend_m: float
    gpo: str
    gross_savings_m: float
    rebate_capture_m: float
    net_savings_m: float
    savings_vs_benchmark_pct: float
    compliance_pct: float


@dataclass
class ContractLookup:
    contract: str
    vendor: str
    category: str
    annual_spend_m: float
    portfolio_deals: int
    reference_price_delta_pct: float
    expires: str
    renewal_status: str


@dataclass
class BulkBuyInitiative:
    initiative: str
    sector: str
    deals_participating: int
    aggregated_volume_m: float
    incremental_savings_m: float
    cycle_days: int
    status: str


@dataclass
class PriceInflationWatch:
    category: str
    ytd_price_change_pct: float
    expected_ytd_change_pct: float
    hedging_strategy: str
    portfolio_exposure_m: float


@dataclass
class GPOResult:
    total_annual_spend_m: float
    total_realized_savings_m: float
    average_savings_rate_pct: float
    total_rebates_m: float
    portfolio_deals_covered: int
    contracts_active: int
    affiliations: List[GPOAffiliation]
    categories: List[SpendCategory]
    deals: List[DealSavings]
    contracts: List[ContractLookup]
    bulk_buys: List[BulkBuyInitiative]
    inflation: List[PriceInflationWatch]
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


def _build_affiliations() -> List[GPOAffiliation]:
    return [
        GPOAffiliation("Vizient", "Vizient Inc.", 8, 285.0, 38.5, 0.135, 0.045, 1250, "national tier-1"),
        GPOAffiliation("Premier Healthcare Alliance", "Premier Inc.", 6, 212.0, 26.5, 0.125, 0.040, 985, "national tier-1"),
        GPOAffiliation("HealthTrust (HCA)", "HCA Healthcare", 4, 148.0, 22.5, 0.152, 0.055, 720, "national tier-1"),
        GPOAffiliation("Kinetic Partners (Pension)", "Kinetic", 3, 92.0, 12.5, 0.136, 0.050, 485, "national tier-2"),
        GPOAffiliation("Intalere / Innovatix", "Intalere", 2, 58.0, 7.2, 0.124, 0.038, 320, "national tier-2"),
        GPOAffiliation("ROi (Resource Optimization)", "Mercy / Shared Services", 2, 45.0, 5.8, 0.129, 0.042, 285, "regional"),
        GPOAffiliation("PE-Specific GPO (Umbrella)", "Boutique", 12, 325.0, 52.0, 0.160, 0.060, 1450, "PE specialist"),
        GPOAffiliation("Direct Mfr Contracts (no GPO)", "Direct contracting", 3, 95.0, 9.5, 0.100, 0.000, 85, "direct"),
    ]


def _build_categories() -> List[SpendCategory]:
    return [
        SpendCategory("Pharmacy / Pharmaceuticals", 425.0, 0.085, 36.1, 0.035, "McKesson Pharma 5yr"),
        SpendCategory("Medical/Surgical Supplies", 285.0, 0.145, 41.3, 0.050, "Owens & Minor MS 5yr"),
        SpendCategory("Implants / Devices", 165.0, 0.165, 27.2, 0.055, "Stryker/Zimmer bulk"),
        SpendCategory("Lab Reagents / Supplies", 85.0, 0.120, 10.2, 0.045, "Quest/Roche partnership"),
        SpendCategory("Imaging Contrast / Supplies", 48.0, 0.135, 6.5, 0.050, "Bracco/Bayer imaging 3yr"),
        SpendCategory("Capital Equipment", 95.0, 0.125, 11.9, 0.040, "Philips/GE capital"),
        SpendCategory("IT Hardware & Software", 125.0, 0.095, 11.9, 0.025, "Epic/Oracle Health multi-year"),
        SpendCategory("Food Service / Nutrition", 42.0, 0.110, 4.6, 0.030, "Aramark 3yr"),
        SpendCategory("Environmental Services", 38.0, 0.095, 3.6, 0.025, "Crothall/ABM multi-year"),
        SpendCategory("Linen / Laundry", 25.0, 0.105, 2.6, 0.030, "Alsco/Cintas 3yr"),
        SpendCategory("Security Services", 28.0, 0.085, 2.4, 0.025, "Allied Universal 3yr"),
        SpendCategory("Waste Management / Medical Waste", 18.0, 0.110, 2.0, 0.028, "Stericycle 3yr"),
        SpendCategory("Utilities (Energy)", 65.0, 0.075, 4.9, 0.000, "Engie/Constellation 5yr"),
        SpendCategory("Insurance (Property/Liability)", 42.0, 0.080, 3.4, 0.025, "Marsh aggregated"),
        SpendCategory("Locum / Staffing Services", 75.0, 0.120, 9.0, 0.025, "AMN/CHG Healthcare"),
    ]


def _build_deals() -> List[DealSavings]:
    return [
        DealSavings("Project Cypress — GI Network", "Gastroenterology", 68.5, "Vizient", 9.2, 2.8, 12.0, 0.165, 0.945),
        DealSavings("Project Magnolia — MSK Platform", "MSK / Ortho", 52.0, "Vizient", 8.5, 2.1, 10.6, 0.172, 0.925),
        DealSavings("Project Redwood — Behavioral", "Behavioral Health", 28.5, "Premier", 3.2, 1.0, 4.2, 0.132, 0.890),
        DealSavings("Project Laurel — Derma", "Dermatology", 22.0, "PE-Specific GPO (Umbrella)", 3.5, 1.2, 4.7, 0.185, 0.950),
        DealSavings("Project Cedar — Cardiology", "Cardiology", 58.0, "HealthTrust", 9.5, 3.1, 12.6, 0.190, 0.955),
        DealSavings("Project Willow — Fertility", "Fertility / IVF", 32.5, "PE-Specific GPO (Umbrella)", 5.2, 1.8, 7.0, 0.175, 0.935),
        DealSavings("Project Spruce — Radiology", "Radiology", 42.0, "Vizient", 5.8, 1.6, 7.4, 0.148, 0.918),
        DealSavings("Project Aspen — Eye Care", "Eye Care", 35.0, "PE-Specific GPO (Umbrella)", 6.2, 2.0, 8.2, 0.186, 0.940),
        DealSavings("Project Maple — Urology", "Urology", 18.5, "Premier", 2.5, 0.7, 3.2, 0.155, 0.915),
        DealSavings("Project Ash — Infusion", "Infusion", 85.0, "PE-Specific GPO (Umbrella)", 14.5, 4.8, 19.3, 0.205, 0.945),
        DealSavings("Project Fir — Lab / Pathology", "Lab Services", 48.0, "Vizient", 6.2, 1.9, 8.1, 0.152, 0.925),
        DealSavings("Project Sage — Home Health", "Home Health", 25.0, "Premier", 3.0, 0.9, 3.9, 0.140, 0.900),
        DealSavings("Project Linden — Behavioral", "Behavioral Health", 22.0, "Premier", 2.4, 0.8, 3.2, 0.128, 0.895),
        DealSavings("Project Basil — Dental DSO", "Dental DSO", 45.0, "PE-Specific GPO (Umbrella)", 7.2, 2.5, 9.7, 0.185, 0.925),
        DealSavings("Project Thyme — Specialty Pharm", "Specialty Pharma", 185.0, "Direct Mfr Contracts", 18.5, 0.0, 18.5, 0.100, 0.880),
    ]


def _build_contracts() -> List[ContractLookup]:
    return [
        ContractLookup("McKesson Pharmaceutical", "McKesson", "Pharmacy", 185.0, 12, -0.095, "2027-06-30", "renewing (favorable)"),
        ContractLookup("Cardinal Health Pharma", "Cardinal Health", "Pharmacy", 95.0, 8, -0.072, "2026-12-31", "renewing (flat)"),
        ContractLookup("Owens & Minor Med/Surg", "Owens & Minor", "Med-Surg", 125.0, 10, -0.148, "2028-03-31", "renewed"),
        ContractLookup("Cardinal Health Med-Surg", "Cardinal Health", "Med-Surg", 85.0, 6, -0.135, "2027-09-30", "renewing (favorable)"),
        ContractLookup("Stryker Ortho Implants", "Stryker", "Implants", 82.0, 6, -0.168, "2027-12-31", "active"),
        ContractLookup("Zimmer Biomet Implants", "Zimmer Biomet", "Implants", 58.0, 5, -0.155, "2027-06-30", "active"),
        ContractLookup("Roche Diagnostics", "Roche", "Lab Reagents", 42.0, 5, -0.125, "2028-06-30", "active"),
        ContractLookup("Abbott Lab Reagents", "Abbott", "Lab Reagents", 28.0, 4, -0.118, "2027-09-30", "active"),
        ContractLookup("Bracco Imaging Contrast", "Bracco", "Imaging", 22.0, 5, -0.130, "2027-03-31", "active"),
        ContractLookup("Philips Capital Imaging", "Philips", "Capital", 48.0, 5, -0.122, "2028-06-30", "active"),
        ContractLookup("GE Healthcare Capital", "GE Healthcare", "Capital", 32.0, 4, -0.118, "2027-12-31", "active"),
        ContractLookup("Epic Systems License", "Epic Systems", "IT Software", 65.0, 6, -0.085, "2029-06-30", "active"),
        ContractLookup("Aramark Food/Nutrition", "Aramark", "Food Service", 28.0, 5, -0.105, "2026-12-31", "renewing (slight inflation)"),
        ContractLookup("AMN Locum Staffing", "AMN Healthcare", "Staffing", 38.0, 6, -0.115, "2027-09-30", "active"),
        ContractLookup("Stericycle Medical Waste", "Stericycle", "Waste", 12.0, 8, -0.108, "2027-06-30", "active"),
    ]


def _build_bulk_buys() -> List[BulkBuyInitiative]:
    return [
        BulkBuyInitiative("Aggregated GLP-1 Drug Buy", "Multi-sector (6 deals)", 6, 48.0, 2.2, 90, "active"),
        BulkBuyInitiative("Ortho Implant Bulk Purchase", "MSK (3 deals + Cedar/Cardio)", 4, 82.0, 6.5, 180, "active"),
        BulkBuyInitiative("Lab Reagent Syndicate", "Lab + GI + Cardio (4 deals)", 4, 45.0, 2.8, 120, "active"),
        BulkBuyInitiative("Imaging Capital Refresh", "Radiology + Cardio (3 deals)", 3, 58.0, 4.5, 240, "executing"),
        BulkBuyInitiative("Epic Licensing Consolidation", "6 platforms", 6, 65.0, 5.5, 365, "closing"),
        BulkBuyInitiative("GLP-1 Inventory Hedge (futures)", "Infusion + Endo", 2, 25.0, 1.8, 60, "executed"),
        BulkBuyInitiative("Cyber Insurance Aggregation", "15 deals", 15, 15.0, 2.2, 120, "executing"),
        BulkBuyInitiative("340B Pharmacy Consulting", "FQHC + Specialty Pharm", 3, 8.0, 1.2, 90, "active"),
    ]


def _build_inflation() -> List[PriceInflationWatch]:
    return [
        PriceInflationWatch("Pharmacy / Pharmaceuticals", 3.8, 4.5, "Fixed-price w/ CPI cap + GPO rebates", 425.0),
        PriceInflationWatch("Medical/Surgical Supplies", 5.2, 6.0, "Multi-year contracts + volume commits", 285.0),
        PriceInflationWatch("Implants / Devices", 4.5, 5.5, "Stryker/Zimmer price-hold agreements", 165.0),
        PriceInflationWatch("Lab Reagents / Supplies", 3.2, 4.0, "Long-term price locks", 85.0),
        PriceInflationWatch("Locum / Staffing Services", 8.5, 10.0, "Direct contracts + GPO leverage", 75.0),
        PriceInflationWatch("Utilities (Energy)", 6.8, 8.5, "Fixed-price energy contracts + demand response", 65.0),
        PriceInflationWatch("Insurance (Property/Liability)", 9.5, 12.0, "Captive + aggregated purchasing", 42.0),
        PriceInflationWatch("Food Service / Nutrition", 4.8, 5.5, "Annual RFP + CPI cap", 42.0),
    ]


def compute_gpo_supply_tracker() -> GPOResult:
    corpus = _load_corpus()
    affiliations = _build_affiliations()
    categories = _build_categories()
    deals = _build_deals()
    contracts = _build_contracts()
    bulk_buys = _build_bulk_buys()
    inflation = _build_inflation()

    total_spend = sum(d.annual_spend_m for d in deals)
    total_savings = sum(d.net_savings_m for d in deals)
    avg_rate = total_savings / total_spend if total_spend > 0 else 0
    total_rebates = sum(d.rebate_capture_m for d in deals)
    contracts_active = sum(1 for c in contracts if c.renewal_status in ("active", "renewed"))

    return GPOResult(
        total_annual_spend_m=round(total_spend, 1),
        total_realized_savings_m=round(total_savings, 1),
        average_savings_rate_pct=round(avg_rate, 4),
        total_rebates_m=round(total_rebates, 1),
        portfolio_deals_covered=len(deals),
        contracts_active=contracts_active,
        affiliations=affiliations,
        categories=categories,
        deals=deals,
        contracts=contracts,
        bulk_buys=bulk_buys,
        inflation=inflation,
        corpus_deal_count=len(corpus),
    )
