"""Workforce Planning Analyzer — hiring, turnover, comp inflation, labor mix.

Critical for healthcare deals (labor = 40-60% of cost base):
- Hiring plan across roles with ramp time
- Turnover cost (replacement, training, productivity loss)
- Comp inflation by role
- Labor mix optimization (MDs vs NPs vs MAs)
- Agency/contract labor reduction
- Benefits load analysis
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Role benchmarks
# ---------------------------------------------------------------------------

_ROLE_BENCHMARKS = {
    "Physician (PCP)":       {"base_comp_k": 275, "benefits_pct": 0.22, "turnover_pct": 0.14,
                              "time_to_productivity_mo": 6, "comp_inflation": 0.055},
    "Physician (Specialist)":{"base_comp_k": 445, "benefits_pct": 0.20, "turnover_pct": 0.10,
                              "time_to_productivity_mo": 4, "comp_inflation": 0.048},
    "Nurse Practitioner":    {"base_comp_k": 128, "benefits_pct": 0.26, "turnover_pct": 0.15,
                              "time_to_productivity_mo": 3, "comp_inflation": 0.062},
    "Physician Assistant":   {"base_comp_k": 125, "benefits_pct": 0.26, "turnover_pct": 0.14,
                              "time_to_productivity_mo": 3, "comp_inflation": 0.058},
    "Registered Nurse (RN)": {"base_comp_k": 82, "benefits_pct": 0.28, "turnover_pct": 0.22,
                              "time_to_productivity_mo": 2, "comp_inflation": 0.072},
    "Licensed Practical Nurse":{"base_comp_k": 56, "benefits_pct": 0.28, "turnover_pct": 0.26,
                              "time_to_productivity_mo": 1, "comp_inflation": 0.068},
    "Medical Assistant":     {"base_comp_k": 42, "benefits_pct": 0.30, "turnover_pct": 0.32,
                              "time_to_productivity_mo": 1, "comp_inflation": 0.055},
    "Front Desk / Check-in": {"base_comp_k": 38, "benefits_pct": 0.30, "turnover_pct": 0.38,
                              "time_to_productivity_mo": 1, "comp_inflation": 0.048},
    "Billing / RCM Staff":   {"base_comp_k": 56, "benefits_pct": 0.28, "turnover_pct": 0.22,
                              "time_to_productivity_mo": 2, "comp_inflation": 0.052},
    "Technologist / Tech":   {"base_comp_k": 72, "benefits_pct": 0.28, "turnover_pct": 0.18,
                              "time_to_productivity_mo": 2, "comp_inflation": 0.056},
    "Administrator":         {"base_comp_k": 115, "benefits_pct": 0.25, "turnover_pct": 0.12,
                              "time_to_productivity_mo": 4, "comp_inflation": 0.045},
    "Director / VP":         {"base_comp_k": 210, "benefits_pct": 0.22, "turnover_pct": 0.10,
                              "time_to_productivity_mo": 6, "comp_inflation": 0.045},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RoleInventory:
    role: str
    current_fte: int
    target_fte: int
    open_positions: int
    agency_fte: int
    base_comp_k: float
    all_in_comp_k: float
    annual_spend_mm: float
    turnover_rate: float
    turnover_cost_mm: float
    comp_inflation_pct: float


@dataclass
class HiringPlan:
    quarter: str
    role: str
    hires_planned: int
    hires_to_date: int
    cost_per_hire_k: float
    total_quarter_cost_mm: float
    productivity_delay_cost_mm: float


@dataclass
class LaborInitiative:
    initiative: str
    scope_roles: str
    annual_savings_mm: float
    one_time_cost_mm: float
    timeline_months: int
    risk: str


@dataclass
class AgencyReduction:
    role: str
    current_agency_fte: float
    target_agency_fte: float
    premium_pct: float
    current_agency_cost_mm: float
    target_agency_cost_mm: float
    savings_mm: float


@dataclass
class WorkforceResult:
    sector: str
    total_fte: int
    open_positions: int
    agency_fte: int
    total_labor_cost_mm: float
    labor_pct_of_revenue: float
    blended_turnover_rate: float
    total_annual_turnover_cost_mm: float
    role_inventory: List[RoleInventory]
    hiring_plan: List[HiringPlan]
    initiatives: List[LaborInitiative]
    agency_reductions: List[AgencyReduction]
    total_initiative_savings_mm: float
    ev_impact_from_labor_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 69):
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


def _role_mix_for_sector(sector: str, total_fte: int) -> Dict[str, int]:
    """Return default role mix by sector, scaling to total_fte."""
    mixes = {
        "Primary Care": {"Physician (PCP)": 0.14, "Nurse Practitioner": 0.12, "Medical Assistant": 0.22,
                          "Front Desk / Check-in": 0.16, "Billing / RCM Staff": 0.08,
                          "Registered Nurse (RN)": 0.10, "Administrator": 0.04, "Director / VP": 0.02,
                          "Physician Assistant": 0.12},
        "Physician Services": {"Physician (PCP)": 0.08, "Physician (Specialist)": 0.10,
                                "Nurse Practitioner": 0.08, "Medical Assistant": 0.18,
                                "Front Desk / Check-in": 0.14, "Billing / RCM Staff": 0.08,
                                "Registered Nurse (RN)": 0.14, "Technologist / Tech": 0.10,
                                "Administrator": 0.06, "Director / VP": 0.02, "Physician Assistant": 0.02},
        "Home Health": {"Registered Nurse (RN)": 0.38, "Licensed Practical Nurse": 0.18,
                         "Medical Assistant": 0.08, "Administrator": 0.06, "Director / VP": 0.03,
                         "Billing / RCM Staff": 0.12, "Front Desk / Check-in": 0.08, "Physician (PCP)": 0.02,
                         "Nurse Practitioner": 0.05},
        "ASC": {"Physician (Specialist)": 0.08, "Registered Nurse (RN)": 0.32,
                "Technologist / Tech": 0.18, "Front Desk / Check-in": 0.08,
                "Billing / RCM Staff": 0.10, "Administrator": 0.08, "Director / VP": 0.03,
                "Medical Assistant": 0.13},
        "Dialysis": {"Registered Nurse (RN)": 0.35, "Licensed Practical Nurse": 0.12,
                      "Technologist / Tech": 0.22, "Medical Assistant": 0.08,
                      "Front Desk / Check-in": 0.08, "Administrator": 0.06, "Director / VP": 0.03,
                      "Billing / RCM Staff": 0.06},
    }
    default = mixes.get(sector, mixes["Physician Services"])
    return {role: int(total_fte * pct) for role, pct in default.items()}


def _build_role_inventory(mix: Dict[str, int], revenue_mm: float) -> List[RoleInventory]:
    rows = []
    import hashlib
    for role, current in mix.items():
        bench = _ROLE_BENCHMARKS.get(role)
        if not bench or current == 0:
            continue
        # Target: current + 8% growth
        target = int(current * 1.08)
        open_pos = max(0, target - current)
        # Agency: ~5-12% for nursing, 0% for others
        h = int(hashlib.md5(role.encode()).hexdigest()[:6], 16)
        if "Nurse" in role:
            agency = int(current * (0.05 + (h % 10) / 100))
        else:
            agency = 0

        base = bench["base_comp_k"]
        all_in = base * (1 + bench["benefits_pct"])
        spend = current * all_in / 1000    # $MM
        turnover_cost = current * bench["turnover_pct"] * (all_in * 0.65 / 1000)   # ~65% of annual comp per replacement

        rows.append(RoleInventory(
            role=role,
            current_fte=current,
            target_fte=target,
            open_positions=open_pos,
            agency_fte=agency,
            base_comp_k=base,
            all_in_comp_k=round(all_in, 1),
            annual_spend_mm=round(spend, 2),
            turnover_rate=round(bench["turnover_pct"], 3),
            turnover_cost_mm=round(turnover_cost, 2),
            comp_inflation_pct=round(bench["comp_inflation"], 3),
        ))
    return rows


def _build_hiring_plan(inventory: List[RoleInventory]) -> List[HiringPlan]:
    rows = []
    quarters = ["Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026"]
    # Distribute open positions across quarters
    for role_inv in inventory:
        if role_inv.open_positions == 0:
            continue
        per_q = max(1, role_inv.open_positions // 4)
        for i, q in enumerate(quarters):
            planned = per_q if i < 3 else role_inv.open_positions - per_q * 3
            planned = max(0, planned)
            if planned == 0:
                continue
            # Cost per hire: typically 15-25% of annual comp
            cost_per_hire = role_inv.all_in_comp_k * 0.20
            qtr_cost = planned * cost_per_hire / 1000
            bench = _ROLE_BENCHMARKS.get(role_inv.role, {"time_to_productivity_mo": 2})
            prod_delay = planned * role_inv.all_in_comp_k * (bench["time_to_productivity_mo"] / 12) / 1000

            rows.append(HiringPlan(
                quarter=q,
                role=role_inv.role,
                hires_planned=planned,
                hires_to_date=int(planned * 0.3) if i == 0 else 0,
                cost_per_hire_k=round(cost_per_hire, 1),
                total_quarter_cost_mm=round(qtr_cost, 3),
                productivity_delay_cost_mm=round(prod_delay, 3),
            ))
    return rows[:30]    # cap display


def _build_initiatives(inventory: List[RoleInventory], total_labor: float) -> List[LaborInitiative]:
    rows = [
        LaborInitiative(
            initiative="Agency / Contract Labor Elimination",
            scope_roles="RNs, LPNs",
            annual_savings_mm=round(total_labor * 0.028, 2),
            one_time_cost_mm=round(total_labor * 0.004, 2),
            timeline_months=9,
            risk="medium",
        ),
        LaborInitiative(
            initiative="Retention Program (stay-bonus, SIP)",
            scope_roles="All clinical",
            annual_savings_mm=round(total_labor * 0.018, 2),
            one_time_cost_mm=round(total_labor * 0.008, 2),
            timeline_months=3,
            risk="low",
        ),
        LaborInitiative(
            initiative="Care Team Redesign (more NP/PA, less MD)",
            scope_roles="Physicians, NPs, PAs",
            annual_savings_mm=round(total_labor * 0.035, 2),
            one_time_cost_mm=round(total_labor * 0.012, 2),
            timeline_months=15,
            risk="high",
        ),
        LaborInitiative(
            initiative="Front-Desk Automation (self-check-in)",
            scope_roles="Front Desk / Check-in",
            annual_savings_mm=round(total_labor * 0.012, 2),
            one_time_cost_mm=round(total_labor * 0.005, 2),
            timeline_months=6,
            risk="low",
        ),
        LaborInitiative(
            initiative="Benefits Plan Consolidation",
            scope_roles="All roles",
            annual_savings_mm=round(total_labor * 0.016, 2),
            one_time_cost_mm=round(total_labor * 0.002, 2),
            timeline_months=12,
            risk="medium",
        ),
        LaborInitiative(
            initiative="RCM Staff Productivity Program",
            scope_roles="Billing / RCM",
            annual_savings_mm=round(total_labor * 0.008, 2),
            one_time_cost_mm=round(total_labor * 0.003, 2),
            timeline_months=6,
            risk="low",
        ),
        LaborInitiative(
            initiative="Compensation Benchmarking + Right-Sizing",
            scope_roles="All",
            annual_savings_mm=round(total_labor * 0.012, 2),
            one_time_cost_mm=round(total_labor * 0.002, 2),
            timeline_months=6,
            risk="medium",
        ),
    ]
    return rows


def _build_agency_reductions(inventory: List[RoleInventory]) -> List[AgencyReduction]:
    rows = []
    for inv in inventory:
        if inv.agency_fte == 0:
            continue
        premium = 0.55    # agency typically 55% premium over FTE
        current_cost = inv.agency_fte * inv.all_in_comp_k * (1 + premium) / 1000
        target_agency = int(inv.agency_fte * 0.30)    # reduce 70%
        target_cost = target_agency * inv.all_in_comp_k * (1 + premium) / 1000
        savings = current_cost - target_cost
        rows.append(AgencyReduction(
            role=inv.role,
            current_agency_fte=inv.agency_fte,
            target_agency_fte=target_agency,
            premium_pct=round(premium, 3),
            current_agency_cost_mm=round(current_cost, 2),
            target_agency_cost_mm=round(target_cost, 2),
            savings_mm=round(savings, 2),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_workforce_planning(
    sector: str = "Physician Services",
    total_fte: int = 280,
    revenue_mm: float = 80.0,
    exit_multiple: float = 11.0,
) -> WorkforceResult:
    corpus = _load_corpus()

    mix = _role_mix_for_sector(sector, total_fte)
    inventory = _build_role_inventory(mix, revenue_mm)
    hiring_plan = _build_hiring_plan(inventory)

    total_labor = sum(inv.annual_spend_mm for inv in inventory)
    initiatives = _build_initiatives(inventory, total_labor)
    agency = _build_agency_reductions(inventory)

    total_fte_built = sum(inv.current_fte for inv in inventory)
    open_pos = sum(inv.open_positions for inv in inventory)
    agency_fte = sum(inv.agency_fte for inv in inventory)
    total_turnover_cost = sum(inv.turnover_cost_mm for inv in inventory)
    total_initiative_savings = sum(i.annual_savings_mm for i in initiatives)

    blended_turnover = sum(inv.turnover_rate * inv.current_fte for inv in inventory) / total_fte_built if total_fte_built else 0
    labor_pct = total_labor / revenue_mm if revenue_mm else 0

    ev_impact = total_initiative_savings * exit_multiple

    return WorkforceResult(
        sector=sector,
        total_fte=total_fte_built,
        open_positions=open_pos,
        agency_fte=agency_fte,
        total_labor_cost_mm=round(total_labor, 2),
        labor_pct_of_revenue=round(labor_pct, 4),
        blended_turnover_rate=round(blended_turnover, 4),
        total_annual_turnover_cost_mm=round(total_turnover_cost, 2),
        role_inventory=inventory,
        hiring_plan=hiring_plan,
        initiatives=initiatives,
        agency_reductions=agency,
        total_initiative_savings_mm=round(total_initiative_savings, 2),
        ev_impact_from_labor_mm=round(ev_impact, 1),
        corpus_deal_count=len(corpus),
    )
