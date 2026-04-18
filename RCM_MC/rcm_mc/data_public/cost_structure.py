"""Cost Structure Analyzer — COGS vs SG&A, labor cost, fixed/variable split.

Healthcare services P&L decomposition:
- COGS (supplies, clinical labor, direct costs)
- Operating expense (admin labor, occupancy, IT, professional fees)
- Fixed vs variable classification
- Labor cost benchmarks by sector
- Operating leverage sensitivity (EBITDA Δ per revenue Δ)
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Sector cost structure benchmarks (% of revenue)
# ---------------------------------------------------------------------------

_COST_STRUCTURE_BY_SECTOR = {
    # structure: {clinical_labor, supplies, occupancy, admin_labor, prof_fees, it, other_opex, ebitda_margin}
    "Physician Services": {
        "clinical_labor": 0.42, "supplies": 0.08, "occupancy": 0.06,
        "admin_labor": 0.10, "prof_fees": 0.03, "it": 0.025, "other_opex": 0.06,
        "variable_pct": 0.55,
    },
    "Dental": {
        "clinical_labor": 0.28, "supplies": 0.10, "occupancy": 0.06,
        "admin_labor": 0.09, "prof_fees": 0.02, "it": 0.02, "other_opex": 0.05,
        "variable_pct": 0.52,
    },
    "Dermatology": {
        "clinical_labor": 0.28, "supplies": 0.09, "occupancy": 0.05,
        "admin_labor": 0.08, "prof_fees": 0.02, "it": 0.02, "other_opex": 0.04,
        "variable_pct": 0.55,
    },
    "Home Health": {
        "clinical_labor": 0.58, "supplies": 0.04, "occupancy": 0.02,
        "admin_labor": 0.10, "prof_fees": 0.02, "it": 0.03, "other_opex": 0.06,
        "variable_pct": 0.72,
    },
    "Hospice": {
        "clinical_labor": 0.52, "supplies": 0.07, "occupancy": 0.03,
        "admin_labor": 0.10, "prof_fees": 0.02, "it": 0.025, "other_opex": 0.05,
        "variable_pct": 0.68,
    },
    "Skilled Nursing": {
        "clinical_labor": 0.48, "supplies": 0.05, "occupancy": 0.12,
        "admin_labor": 0.09, "prof_fees": 0.025, "it": 0.02, "other_opex": 0.07,
        "variable_pct": 0.58,
    },
    "ASC": {
        "clinical_labor": 0.28, "supplies": 0.18, "occupancy": 0.06,
        "admin_labor": 0.07, "prof_fees": 0.02, "it": 0.015, "other_opex": 0.04,
        "variable_pct": 0.60,
    },
    "Surgery Center": {
        "clinical_labor": 0.28, "supplies": 0.18, "occupancy": 0.06,
        "admin_labor": 0.07, "prof_fees": 0.02, "it": 0.015, "other_opex": 0.04,
        "variable_pct": 0.60,
    },
    "Behavioral Health": {
        "clinical_labor": 0.55, "supplies": 0.04, "occupancy": 0.07,
        "admin_labor": 0.11, "prof_fees": 0.025, "it": 0.025, "other_opex": 0.06,
        "variable_pct": 0.66,
    },
    "ABA Therapy": {
        "clinical_labor": 0.62, "supplies": 0.03, "occupancy": 0.05,
        "admin_labor": 0.09, "prof_fees": 0.025, "it": 0.02, "other_opex": 0.04,
        "variable_pct": 0.76,
    },
    "Addiction Treatment": {
        "clinical_labor": 0.48, "supplies": 0.04, "occupancy": 0.09,
        "admin_labor": 0.12, "prof_fees": 0.03, "it": 0.02, "other_opex": 0.06,
        "variable_pct": 0.58,
    },
    "Pharmacy": {
        "clinical_labor": 0.16, "supplies": 0.58, "occupancy": 0.03,
        "admin_labor": 0.06, "prof_fees": 0.015, "it": 0.015, "other_opex": 0.04,
        "variable_pct": 0.78,
    },
    "Specialty Pharmacy": {
        "clinical_labor": 0.08, "supplies": 0.72, "occupancy": 0.02,
        "admin_labor": 0.04, "prof_fees": 0.01, "it": 0.015, "other_opex": 0.03,
        "variable_pct": 0.84,
    },
    "Laboratory": {
        "clinical_labor": 0.24, "supplies": 0.24, "occupancy": 0.05,
        "admin_labor": 0.09, "prof_fees": 0.025, "it": 0.04, "other_opex": 0.05,
        "variable_pct": 0.58,
    },
    "Healthcare IT": {
        "clinical_labor": 0.00, "supplies": 0.04, "occupancy": 0.04,
        "admin_labor": 0.48, "prof_fees": 0.03, "it": 0.08, "other_opex": 0.08,
        "variable_pct": 0.35,
    },
    "EHR/EMR": {
        "clinical_labor": 0.00, "supplies": 0.03, "occupancy": 0.04,
        "admin_labor": 0.42, "prof_fees": 0.03, "it": 0.10, "other_opex": 0.08,
        "variable_pct": 0.30,
    },
    "Medical Devices": {
        "clinical_labor": 0.00, "supplies": 0.42, "occupancy": 0.06,
        "admin_labor": 0.14, "prof_fees": 0.03, "it": 0.03, "other_opex": 0.10,
        "variable_pct": 0.65,
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CostLine:
    category: str
    pct_of_revenue: float
    amount_mm: float
    is_variable: bool
    benchmark_pct: float
    delta_vs_benchmark: float


@dataclass
class LaborBreakdown:
    role_type: str
    headcount: int
    avg_comp_k: float
    total_cost_mm: float
    pct_of_revenue: float


@dataclass
class LeverageScenario:
    scenario: str
    revenue_delta_pct: float
    expected_ebitda_delta_pct: float
    leverage_ratio: float
    implied_ebitda_mm: float
    implied_ev_mm: float


@dataclass
class CostStructureResult:
    sector: str
    revenue_mm: float
    cost_lines: List[CostLine]
    labor_breakdown: List[LaborBreakdown]
    leverage_scenarios: List[LeverageScenario]
    total_cogs_mm: float
    total_sga_mm: float
    ebitda_mm: float
    ebitda_margin: float
    variable_cost_pct: float
    fixed_cost_pct: float
    operating_leverage: float          # % EBITDA Δ / % revenue Δ
    total_labor_cost_mm: float
    labor_pct_of_revenue: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 62):
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


def _get_profile(sector: str) -> Dict:
    return _COST_STRUCTURE_BY_SECTOR.get(sector, _COST_STRUCTURE_BY_SECTOR["Physician Services"])


def _build_cost_lines(sector: str, revenue_mm: float) -> List[CostLine]:
    profile = _get_profile(sector)
    items = [
        ("Clinical Labor (COGS)", profile["clinical_labor"], True),
        ("Supplies / COGS", profile["supplies"], True),
        ("Occupancy", profile["occupancy"], False),
        ("Admin Labor", profile["admin_labor"], False),
        ("Professional Fees", profile["prof_fees"], False),
        ("IT / Tech", profile["it"], False),
        ("Other OpEx", profile["other_opex"], True),
    ]
    bench = profile    # use self as benchmark for simplicity
    return [
        CostLine(
            category=cat,
            pct_of_revenue=round(pct, 4),
            amount_mm=round(revenue_mm * pct, 2),
            is_variable=variable,
            benchmark_pct=round(bench.get(cat.lower().replace(" ", "_").replace("(cogs)", "").replace("/", "_").strip(), pct), 4),
            delta_vs_benchmark=0.0,
        )
        for cat, pct, variable in items
    ]


def _build_labor(sector: str, revenue_mm: float) -> List[LaborBreakdown]:
    profile = _get_profile(sector)
    clinical_pct = profile["clinical_labor"]
    admin_pct = profile["admin_labor"]

    # Typical comp bands
    if sector in ("Healthcare IT", "EHR/EMR", "Medical Devices"):
        engineers_cost = revenue_mm * admin_pct * 0.60
        engineers_comp = 185
        engineers_hc = int(engineers_cost * 1000 / engineers_comp) if engineers_comp else 0
        product_cost = revenue_mm * admin_pct * 0.15
        product_hc = int(product_cost * 1000 / 160) if product_cost else 0
        support_cost = revenue_mm * admin_pct * 0.25
        support_hc = int(support_cost * 1000 / 85) if support_cost else 0
        return [
            LaborBreakdown(role_type="Engineers / Dev", headcount=engineers_hc,
                           avg_comp_k=engineers_comp, total_cost_mm=round(engineers_cost, 2),
                           pct_of_revenue=round(engineers_cost / revenue_mm, 4) if revenue_mm else 0),
            LaborBreakdown(role_type="Product / Design", headcount=product_hc,
                           avg_comp_k=160, total_cost_mm=round(product_cost, 2),
                           pct_of_revenue=round(product_cost / revenue_mm, 4) if revenue_mm else 0),
            LaborBreakdown(role_type="Sales / Support / Admin", headcount=support_hc,
                           avg_comp_k=85, total_cost_mm=round(support_cost, 2),
                           pct_of_revenue=round(support_cost / revenue_mm, 4) if revenue_mm else 0),
        ]

    # Clinical services typical mix
    provider_cost = revenue_mm * clinical_pct * 0.58
    provider_comp = 320 if sector in ("Physician Services", "Cardiology", "Orthopedics") else 180
    provider_hc = int(provider_cost * 1000 / provider_comp) if provider_comp else 0
    nurse_cost = revenue_mm * clinical_pct * 0.28
    nurse_hc = int(nurse_cost * 1000 / 95) if nurse_cost else 0
    tech_cost = revenue_mm * clinical_pct * 0.14
    tech_hc = int(tech_cost * 1000 / 65) if tech_cost else 0
    admin_cost = revenue_mm * admin_pct
    admin_hc = int(admin_cost * 1000 / 72) if admin_cost else 0

    return [
        LaborBreakdown(role_type="Providers (MD/DO/NP)", headcount=provider_hc,
                       avg_comp_k=provider_comp, total_cost_mm=round(provider_cost, 2),
                       pct_of_revenue=round(provider_cost / revenue_mm, 4) if revenue_mm else 0),
        LaborBreakdown(role_type="Nursing / Clinical Support", headcount=nurse_hc,
                       avg_comp_k=95, total_cost_mm=round(nurse_cost, 2),
                       pct_of_revenue=round(nurse_cost / revenue_mm, 4) if revenue_mm else 0),
        LaborBreakdown(role_type="Techs / MAs", headcount=tech_hc,
                       avg_comp_k=65, total_cost_mm=round(tech_cost, 2),
                       pct_of_revenue=round(tech_cost / revenue_mm, 4) if revenue_mm else 0),
        LaborBreakdown(role_type="Admin / Billing / Ops", headcount=admin_hc,
                       avg_comp_k=72, total_cost_mm=round(admin_cost, 2),
                       pct_of_revenue=round(admin_cost / revenue_mm, 4) if revenue_mm else 0),
    ]


def _build_leverage_scenarios(
    revenue_mm: float, ebitda_mm: float, variable_pct: float,
    current_margin: float, exit_mult: float,
) -> List[LeverageScenario]:
    rows = []
    # Operating leverage: fixed-cost portion creates margin expansion as revenue scales
    fixed_pct = 1 - variable_pct - current_margin    # the part that doesn't scale
    # Rough operating leverage = % EBITDA change / % revenue change
    # At +10% revenue: new EBITDA = ebitda + 10% * rev * (1 - variable_pct)
    op_lev = ((revenue_mm * 0.10 * (1 - variable_pct)) / ebitda_mm) / 0.10 if ebitda_mm else 1.0

    for label, delta_pct in [("Revenue -10%", -0.10), ("Revenue Flat", 0.0),
                              ("Revenue +10%", 0.10), ("Revenue +20%", 0.20), ("Revenue +30%", 0.30)]:
        new_rev = revenue_mm * (1 + delta_pct)
        ebitda_delta = revenue_mm * delta_pct * (1 - variable_pct)
        new_ebitda = ebitda_mm + ebitda_delta
        ebitda_pct_delta = (new_ebitda - ebitda_mm) / ebitda_mm if ebitda_mm else 0
        new_ev = new_ebitda * exit_mult
        rows.append(LeverageScenario(
            scenario=label,
            revenue_delta_pct=round(delta_pct, 3),
            expected_ebitda_delta_pct=round(ebitda_pct_delta, 3),
            leverage_ratio=round(ebitda_pct_delta / delta_pct, 2) if delta_pct != 0 else 1.0,
            implied_ebitda_mm=round(new_ebitda, 2),
            implied_ev_mm=round(new_ev, 1),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_cost_structure(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    exit_multiple: float = 11.0,
) -> CostStructureResult:
    corpus = _load_corpus()
    profile = _get_profile(sector)

    cost_lines = _build_cost_lines(sector, revenue_mm)
    labor = _build_labor(sector, revenue_mm)

    total_cost_pct = sum(cl.pct_of_revenue for cl in cost_lines)
    ebitda_margin = round(max(0, 1 - total_cost_pct), 4)
    ebitda_mm = revenue_mm * ebitda_margin

    # COGS: clinical_labor + supplies + other_opex (variable portion)
    cogs_pct = profile["clinical_labor"] + profile["supplies"]
    sga_pct = total_cost_pct - cogs_pct

    variable_pct = profile["variable_pct"]
    fixed_pct = 1 - variable_pct - ebitda_margin
    op_leverage = (1 - variable_pct) / ebitda_margin if ebitda_margin else 1.0

    labor_cost = sum(l.total_cost_mm for l in labor)
    labor_pct = labor_cost / revenue_mm if revenue_mm else 0

    scenarios = _build_leverage_scenarios(
        revenue_mm, ebitda_mm, variable_pct, ebitda_margin, exit_multiple
    )

    return CostStructureResult(
        sector=sector,
        revenue_mm=round(revenue_mm, 2),
        cost_lines=cost_lines,
        labor_breakdown=labor,
        leverage_scenarios=scenarios,
        total_cogs_mm=round(revenue_mm * cogs_pct, 2),
        total_sga_mm=round(revenue_mm * sga_pct, 2),
        ebitda_mm=round(ebitda_mm, 2),
        ebitda_margin=round(ebitda_margin, 4),
        variable_cost_pct=round(variable_pct, 4),
        fixed_cost_pct=round(fixed_pct, 4),
        operating_leverage=round(op_leverage, 2),
        total_labor_cost_mm=round(labor_cost, 2),
        labor_pct_of_revenue=round(labor_pct, 4),
        corpus_deal_count=len(corpus),
    )
