"""Procurement & Supply Chain Analyzer.

Models medical supply economics for healthcare PE deals:
- Supply spend by category (implants, pharma, commodities)
- GPO (Group Purchasing Org) enrollment and pricing
- Vendor concentration
- Savings opportunities by lever
- CapEx modernization (equipment, imaging)
- Inventory turns
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SpendCategory:
    category: str
    annual_spend_mm: float
    pct_of_revenue: float
    pct_of_total_supply: float
    benchmark_pct_revenue: float
    variance: str
    top_vendor: str
    top_vendor_share: float


@dataclass
class GPOLever:
    lever: str
    current_state: str
    target_state: str
    annual_savings_mm: float
    one_time_cost_mm: float
    timeline_months: int
    risk: str


@dataclass
class VendorRow:
    vendor: str
    category: str
    annual_spend_mm: float
    contract_end: str
    alternatives_available: int
    switching_cost_mm: float
    risk_flag: str


@dataclass
class CapExProject:
    project: str
    one_time_cost_mm: float
    annual_savings_mm: float
    payback_years: float
    strategic_value: str
    priority: str


@dataclass
class InventoryKPI:
    metric: str
    current: float
    benchmark: float
    unit: str
    status: str
    tied_up_capital_mm: float


@dataclass
class SupplyChainResult:
    total_supply_spend_mm: float
    supply_pct_revenue: float
    total_savings_opportunity_mm: float
    ev_uplift_mm: float
    spend_categories: List[SpendCategory]
    gpo_levers: List[GPOLever]
    top_vendors: List[VendorRow]
    capex_projects: List[CapExProject]
    inventory_kpis: List[InventoryKPI]
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 74):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _build_spend(sector: str, revenue_mm: float) -> List[SpendCategory]:
    # Allocation differs by sector
    if sector in ("ASC", "Surgery Center", "Orthopedics"):
        items = [
            ("Implants & Devices", 0.14, "Medtronic", 0.28),
            ("Surgical Supplies", 0.065, "Stryker / B. Braun", 0.18),
            ("Pharma & IV", 0.035, "McKesson", 0.32),
            ("Medical/Surgical Supplies", 0.025, "Cardinal Health", 0.25),
            ("Linen/Housekeeping", 0.008, "Regional", 0.45),
            ("IT / Subscriptions", 0.018, "Epic/Oracle", 0.35),
            ("Office & Admin", 0.006, "Amazon Business", 0.40),
        ]
    elif sector in ("Dialysis", "Kidney Care"):
        items = [
            ("Dialysis Supplies", 0.175, "Fresenius", 0.52),
            ("Pharmaceuticals (ESAs, Iron)", 0.045, "Amgen", 0.48),
            ("Water Treatment", 0.018, "Veolia", 0.38),
            ("Disposables", 0.032, "Baxter", 0.45),
            ("IT / Subscriptions", 0.012, "Various", 0.25),
        ]
    elif sector in ("Pharmacy", "Specialty Pharmacy", "Oncology Pharmacy"):
        items = [
            ("Pharmaceutical Acquisition Cost", 0.68, "AmerisourceBergen/McKesson", 0.55),
            ("Specialty Drugs (Oncology)", 0.18, "Direct Manufacturer", 0.35),
            ("Supplies & Packaging", 0.015, "Cardinal", 0.28),
            ("340B Program Admin", 0.008, "Apexus", 0.65),
            ("IT / Subscriptions", 0.010, "McKesson Connect", 0.45),
        ]
    else:
        items = [
            ("Medical Supplies", 0.045, "Henry Schein", 0.32),
            ("Pharmaceuticals", 0.025, "McKesson", 0.42),
            ("Lab / Diagnostics", 0.020, "Quest/LabCorp", 0.58),
            ("Office & Admin", 0.008, "Amazon Business", 0.35),
            ("IT / Subscriptions", 0.022, "Epic / athenahealth", 0.48),
            ("Marketing & Printing", 0.008, "Various local", 0.22),
            ("Professional Services", 0.012, "KPMG / Big 4", 0.65),
        ]
    total_spend = sum(revenue_mm * pct for _, pct, _, _ in items)

    rows = []
    for cat, pct, vendor, vend_share in items:
        spend = revenue_mm * pct
        benchmark = pct * 0.92   # benchmark 8% lower (best-in-class savings)
        variance = "above" if pct > benchmark * 1.10 else ("benchmark" if pct >= benchmark * 0.95 else "below")
        rows.append(SpendCategory(
            category=cat,
            annual_spend_mm=round(spend, 2),
            pct_of_revenue=round(pct, 4),
            pct_of_total_supply=round(spend / total_spend if total_spend else 0, 3),
            benchmark_pct_revenue=round(benchmark, 4),
            variance=variance,
            top_vendor=vendor,
            top_vendor_share=round(vend_share, 3),
        ))
    return rows


def _build_levers(total_supply_mm: float) -> List[GPOLever]:
    return [
        GPOLever(
            lever="GPO Tier Upgrade (Vizient, Premier)",
            current_state="Mid-tier pricing",
            target_state="Platinum tier w/ volume commitment",
            annual_savings_mm=round(total_supply_mm * 0.035, 2),
            one_time_cost_mm=0.05,
            timeline_months=6,
            risk="low",
        ),
        GPOLever(
            lever="Implant Standardization",
            current_state="3-4 vendors per category",
            target_state="Single-source agreements",
            annual_savings_mm=round(total_supply_mm * 0.058, 2),
            one_time_cost_mm=0.25,
            timeline_months=12,
            risk="medium",
        ),
        GPOLever(
            lever="Generic / Therapeutic Substitution",
            current_state="Brand-preferred in 40% of Rx",
            target_state="Generic-first protocol",
            annual_savings_mm=round(total_supply_mm * 0.022, 2),
            one_time_cost_mm=0.08,
            timeline_months=6,
            risk="low",
        ),
        GPOLever(
            lever="Item Master Optimization",
            current_state="28K SKUs, 18% duplicate",
            target_state="18K SKUs cleaned",
            annual_savings_mm=round(total_supply_mm * 0.015, 2),
            one_time_cost_mm=0.12,
            timeline_months=9,
            risk="low",
        ),
        GPOLever(
            lever="Consigned Inventory Program",
            current_state="On-hand stocking",
            target_state="Consigned for high-value implants",
            annual_savings_mm=round(total_supply_mm * 0.008, 2),
            one_time_cost_mm=0.03,
            timeline_months=4,
            risk="low",
        ),
        GPOLever(
            lever="Direct Manufacturer (DMA)",
            current_state="Distributor pricing",
            target_state="Direct purchase for high-volume SKUs",
            annual_savings_mm=round(total_supply_mm * 0.025, 2),
            one_time_cost_mm=0.15,
            timeline_months=9,
            risk="medium",
        ),
        GPOLever(
            lever="Specialty Pharmacy Contract Leverage",
            current_state="Retail pricing",
            target_state="Manufacturer rebate agreements",
            annual_savings_mm=round(total_supply_mm * 0.018, 2),
            one_time_cost_mm=0.06,
            timeline_months=6,
            risk="medium",
        ),
        GPOLever(
            lever="Managed Print / Office Supply Consolidation",
            current_state="Multiple small vendors",
            target_state="Amazon Business + single MPS vendor",
            annual_savings_mm=round(total_supply_mm * 0.004, 2),
            one_time_cost_mm=0.02,
            timeline_months=3,
            risk="low",
        ),
    ]


def _build_vendors(revenue_mm: float) -> List[VendorRow]:
    return [
        VendorRow("McKesson / Cardinal (Pharma)", "Pharmaceuticals",
                  round(revenue_mm * 0.028, 2), "2026-06-30", 2, 0.45, "medium"),
        VendorRow("Medtronic (Cardio/Ortho Implants)", "Implants",
                  round(revenue_mm * 0.045, 2), "2025-12-31", 3, 0.95, "high"),
        VendorRow("Stryker (Ortho)", "Implants",
                  round(revenue_mm * 0.038, 2), "2026-09-30", 3, 0.75, "high"),
        VendorRow("Henry Schein (Medical-Surgical)", "Medical Supplies",
                  round(revenue_mm * 0.022, 2), "2025-12-31", 4, 0.18, "low"),
        VendorRow("Epic Systems (EHR)", "IT",
                  round(revenue_mm * 0.012, 2), "2028-12-31", 2, 15.0, "critical"),
        VendorRow("Quest Diagnostics (Lab)", "Lab",
                  round(revenue_mm * 0.015, 2), "2026-03-31", 2, 0.22, "low"),
        VendorRow("Baxter International", "IV/Infusion",
                  round(revenue_mm * 0.018, 2), "2026-12-31", 3, 0.35, "medium"),
        VendorRow("Fresenius (Dialysis)", "Dialysis Supplies",
                  round(revenue_mm * 0.024, 2), "2027-06-30", 1, 0.95, "high"),
        VendorRow("B. Braun (Surgical)", "Surgical Supplies",
                  round(revenue_mm * 0.011, 2), "2026-06-30", 4, 0.20, "low"),
        VendorRow("athenahealth (RCM)", "RCM",
                  round(revenue_mm * 0.020, 2), "2027-12-31", 2, 0.80, "medium"),
    ]


def _build_capex(revenue_mm: float) -> List[CapExProject]:
    return [
        CapExProject("MRI Replacement (1.5T → 3T)", 2.2, 0.65, 3.4, "Revenue capacity + quality", "high"),
        CapExProject("Robotic Surgery Platform", 1.8, 0.45, 4.0, "Procedure volume capture", "medium"),
        CapExProject("Imaging Consolidation (4 → 2 vendors)", 0.85, 0.28, 3.0, "Operational simplification", "medium"),
        CapExProject("HVAC / Energy Efficiency (all sites)", 1.2, 0.22, 5.5, "ESG + opex", "low"),
        CapExProject("ADA-Compliance Upgrades", 0.65, 0.0, 99.0, "Regulatory requirement", "high"),
        CapExProject("Digital Check-in Kiosks", 0.38, 0.18, 2.1, "Patient experience + throughput", "medium"),
        CapExProject("Fleet Replacement (mobile units)", 0.42, 0.0, 99.0, "Asset lifecycle", "low"),
        CapExProject("RCM / Finance System Upgrade", 0.95, 0.35, 2.7, "Margin expansion", "high"),
    ]


def _build_inventory() -> List[InventoryKPI]:
    return [
        InventoryKPI("Days Inventory Outstanding", 42, 28, "days", "above-benchmark", 1.8),
        InventoryKPI("Inventory Turns", 8.7, 12.0, "x/year", "below", 0.0),
        InventoryKPI("Obsolescence Rate", 0.028, 0.015, "%", "above", 0.4),
        InventoryKPI("Stockout Rate", 0.022, 0.015, "%", "above", 0.0),
        InventoryKPI("PAR Level Compliance", 0.78, 0.92, "%", "below", 0.0),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_supply_chain(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    exit_multiple: float = 11.0,
) -> SupplyChainResult:
    corpus = _load_corpus()

    spend = _build_spend(sector, revenue_mm)
    total_supply = sum(s.annual_spend_mm for s in spend)
    levers = _build_levers(total_supply)
    vendors = _build_vendors(revenue_mm)
    capex = _build_capex(revenue_mm)
    inventory = _build_inventory()

    total_savings = sum(l.annual_savings_mm for l in levers) + sum(c.annual_savings_mm for c in capex)
    ev_uplift = total_savings * exit_multiple

    return SupplyChainResult(
        total_supply_spend_mm=round(total_supply, 2),
        supply_pct_revenue=round(total_supply / revenue_mm if revenue_mm else 0, 4),
        total_savings_opportunity_mm=round(total_savings, 2),
        ev_uplift_mm=round(ev_uplift, 1),
        spend_categories=spend,
        gpo_levers=levers,
        top_vendors=vendors,
        capex_projects=capex,
        inventory_kpis=inventory,
        corpus_deal_count=len(corpus),
    )
