"""Unit Economics Analyzer — per-site, per-patient, per-provider economics.

Unpacks aggregate financials into atomic units. Healthcare PE lives on:
- Revenue per location
- Contribution margin per location
- Payback period for new locations (de novo)
- Ramp curve (months to maturity)
- Per-visit profitability
- Per-provider yield
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Sector unit-economics benchmarks
# ---------------------------------------------------------------------------

_SECTOR_UNITS = {
    # revenue_per_location, visits_per_loc/yr, providers_per_loc, capex_per_loc, months_to_maturity,
    # contribution_margin_pct, fixed_cost_per_loc_mm
    "Dermatology": {
        "rev_per_loc_mm": 3.2, "visits_per_loc": 18500, "providers_per_loc": 2.2,
        "capex_per_loc_mm": 0.85, "months_to_maturity": 18,
        "contrib_margin_pct": 0.32, "fixed_cost_per_loc_mm": 0.75,
    },
    "Dental": {
        "rev_per_loc_mm": 2.4, "visits_per_loc": 14000, "providers_per_loc": 1.8,
        "capex_per_loc_mm": 1.05, "months_to_maturity": 24,
        "contrib_margin_pct": 0.30, "fixed_cost_per_loc_mm": 0.65,
    },
    "Ophthalmology": {
        "rev_per_loc_mm": 4.8, "visits_per_loc": 17500, "providers_per_loc": 2.8,
        "capex_per_loc_mm": 1.80, "months_to_maturity": 20,
        "contrib_margin_pct": 0.28, "fixed_cost_per_loc_mm": 1.10,
    },
    "Urgent Care": {
        "rev_per_loc_mm": 2.8, "visits_per_loc": 22000, "providers_per_loc": 3.2,
        "capex_per_loc_mm": 0.95, "months_to_maturity": 15,
        "contrib_margin_pct": 0.22, "fixed_cost_per_loc_mm": 0.95,
    },
    "Physician Services": {
        "rev_per_loc_mm": 3.8, "visits_per_loc": 16000, "providers_per_loc": 2.5,
        "capex_per_loc_mm": 0.55, "months_to_maturity": 20,
        "contrib_margin_pct": 0.24, "fixed_cost_per_loc_mm": 0.80,
    },
    "ASC": {
        "rev_per_loc_mm": 12.5, "visits_per_loc": 5800, "providers_per_loc": 6.5,
        "capex_per_loc_mm": 8.5, "months_to_maturity": 30,
        "contrib_margin_pct": 0.38, "fixed_cost_per_loc_mm": 2.80,
    },
    "Veterinary": {
        "rev_per_loc_mm": 2.1, "visits_per_loc": 9800, "providers_per_loc": 2.2,
        "capex_per_loc_mm": 0.65, "months_to_maturity": 18,
        "contrib_margin_pct": 0.25, "fixed_cost_per_loc_mm": 0.50,
    },
    "Fertility": {
        "rev_per_loc_mm": 8.5, "visits_per_loc": 4200, "providers_per_loc": 3.5,
        "capex_per_loc_mm": 3.2, "months_to_maturity": 30,
        "contrib_margin_pct": 0.32, "fixed_cost_per_loc_mm": 2.10,
    },
    "ABA Therapy": {
        "rev_per_loc_mm": 2.2, "visits_per_loc": 12000, "providers_per_loc": 18,
        "capex_per_loc_mm": 0.35, "months_to_maturity": 24,
        "contrib_margin_pct": 0.18, "fixed_cost_per_loc_mm": 0.45,
    },
    "Home Health": {
        "rev_per_loc_mm": 6.5, "visits_per_loc": 22000, "providers_per_loc": 55,
        "capex_per_loc_mm": 0.25, "months_to_maturity": 30,
        "contrib_margin_pct": 0.14, "fixed_cost_per_loc_mm": 1.10,
    },
    "Behavioral Health": {
        "rev_per_loc_mm": 3.5, "visits_per_loc": 12000, "providers_per_loc": 12,
        "capex_per_loc_mm": 0.55, "months_to_maturity": 24,
        "contrib_margin_pct": 0.20, "fixed_cost_per_loc_mm": 0.85,
    },
    "Gastroenterology": {
        "rev_per_loc_mm": 7.8, "visits_per_loc": 22000, "providers_per_loc": 4.5,
        "capex_per_loc_mm": 2.2, "months_to_maturity": 24,
        "contrib_margin_pct": 0.30, "fixed_cost_per_loc_mm": 1.45,
    },
    "Pharmacy": {
        "rev_per_loc_mm": 5.8, "visits_per_loc": 38000, "providers_per_loc": 3.5,
        "capex_per_loc_mm": 0.55, "months_to_maturity": 12,
        "contrib_margin_pct": 0.18, "fixed_cost_per_loc_mm": 0.80,
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LocationMetric:
    metric: str
    value: float
    unit: str
    benchmark: float
    delta_vs_bench: float
    status: str


@dataclass
class RampMonth:
    month: int
    revenue_pct_of_mature: float
    cumulative_revenue_mm: float
    cumulative_cash_mm: float       # cumulative cash flow (negative in early months)
    breakeven_reached: bool


@dataclass
class VisitProfile:
    category: str                   # "New Patient", "Follow-up", "Procedure", "Ancillary"
    pct_of_visits: float
    avg_reimbursement: float
    avg_cost: float
    contribution_per_visit: float
    annual_volume: int


@dataclass
class ProviderYield:
    role: str
    annual_visits_per_provider: int
    annual_revenue_per_provider_mm: float
    comp_per_provider_k: float
    net_margin_per_provider_mm: float
    roi_multiple: float             # revenue / comp


@dataclass
class SiteScenario:
    scenario: str                   # "Mature Site", "Year 1 New Site", "Underperforming Site"
    revenue_mm: float
    contribution_mm: float
    contribution_margin_pct: float
    cash_flow_mm: float
    years_to_payback: float


@dataclass
class UnitEconomicsResult:
    sector: str
    num_locations: int
    total_revenue_mm: float
    revenue_per_location_mm: float
    payback_years: float
    ramp_curve: List[RampMonth]
    location_metrics: List[LocationMetric]
    visit_profile: List[VisitProfile]
    provider_yield: List[ProviderYield]
    site_scenarios: List[SiteScenario]
    de_novo_irr: float
    new_site_annual_capacity: int
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 64):
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
    return _SECTOR_UNITS.get(sector, _SECTOR_UNITS["Physician Services"])


def _build_ramp_curve(
    months_to_maturity: int, mature_revenue_mm: float,
    contrib_margin_pct: float, capex_mm: float,
) -> List[RampMonth]:
    """S-curve: slow ramp, acceleration, plateau."""
    rows = []
    cum_rev = 0.0
    cum_cash = -capex_mm
    breakeven = False

    for m in range(1, int(months_to_maturity * 1.5) + 1):
        if m <= months_to_maturity:
            # S-curve: faster mid-ramp
            progress = m / months_to_maturity
            pct_mature = (3 * progress ** 2 - 2 * progress ** 3)  # smoothstep
        else:
            pct_mature = 1.0

        monthly_rev = (mature_revenue_mm / 12) * pct_mature
        monthly_cm = monthly_rev * contrib_margin_pct
        cum_rev += monthly_rev
        cum_cash += monthly_cm

        if cum_cash >= 0 and not breakeven:
            breakeven = True

        rows.append(RampMonth(
            month=m,
            revenue_pct_of_mature=round(pct_mature, 3),
            cumulative_revenue_mm=round(cum_rev, 2),
            cumulative_cash_mm=round(cum_cash, 2),
            breakeven_reached=breakeven,
        ))
        if m > months_to_maturity and breakeven and cum_cash > capex_mm * 0.5:
            break
    return rows


def _payback_years(ramp: List[RampMonth], capex: float) -> float:
    for r in ramp:
        if r.cumulative_cash_mm >= 0:
            return round(r.month / 12, 1)
    return round(len(ramp) / 12, 1)


def _build_location_metrics(profile: Dict) -> List[LocationMetric]:
    """Compare against sector median."""
    # Use the profile itself as benchmark for demo; in practice, would compare to actual
    actuals = {
        "Revenue per Location ($M)": profile["rev_per_loc_mm"] * 0.95,
        "Visits per Location": profile["visits_per_loc"] * 0.92,
        "Providers per Location": profile["providers_per_loc"] * 1.05,
        "Revenue per Visit ($)": (profile["rev_per_loc_mm"] * 1_000_000) / profile["visits_per_loc"],
        "Revenue per Provider ($M)": profile["rev_per_loc_mm"] / profile["providers_per_loc"],
        "Contribution Margin %": profile["contrib_margin_pct"] * 100,
    }
    benchmarks = {
        "Revenue per Location ($M)": profile["rev_per_loc_mm"],
        "Visits per Location": profile["visits_per_loc"],
        "Providers per Location": profile["providers_per_loc"],
        "Revenue per Visit ($)": (profile["rev_per_loc_mm"] * 1_000_000) / profile["visits_per_loc"],
        "Revenue per Provider ($M)": profile["rev_per_loc_mm"] / profile["providers_per_loc"],
        "Contribution Margin %": profile["contrib_margin_pct"] * 100,
    }
    rows = []
    for key in actuals:
        actual = actuals[key]
        bench = benchmarks[key]
        delta = (actual - bench) / bench if bench else 0
        status = "above" if actual >= bench * 1.03 else ("benchmark" if actual >= bench * 0.97 else "below")
        unit = key.split("(")[-1].rstrip(")") if "(" in key else ""
        rows.append(LocationMetric(
            metric=key.split(" (")[0],
            value=round(actual, 2),
            unit=unit,
            benchmark=round(bench, 2),
            delta_vs_bench=round(delta, 3),
            status=status,
        ))
    return rows


def _build_visits(profile: Dict) -> List[VisitProfile]:
    visits_per_loc = profile["visits_per_loc"]
    mix = [
        ("New Patient", 0.22, 280, 160),
        ("Follow-up / Established", 0.45, 175, 98),
        ("Procedure", 0.22, 620, 280),
        ("Ancillary / Lab / Imaging", 0.11, 140, 60),
    ]
    rows = []
    for cat, pct, reimb, cost in mix:
        annual = int(visits_per_loc * pct)
        rows.append(VisitProfile(
            category=cat,
            pct_of_visits=round(pct, 3),
            avg_reimbursement=round(reimb, 2),
            avg_cost=round(cost, 2),
            contribution_per_visit=round(reimb - cost, 2),
            annual_volume=annual,
        ))
    return rows


def _build_provider_yield(profile: Dict) -> List[ProviderYield]:
    rev_per_loc = profile["rev_per_loc_mm"]
    providers = profile["providers_per_loc"]
    visits = profile["visits_per_loc"]
    # Split providers by role if sector has mix
    rows = [
        ProviderYield(
            role="Physician / Senior Provider",
            annual_visits_per_provider=int(visits / providers * 1.15),
            annual_revenue_per_provider_mm=round(rev_per_loc / providers * 1.2, 2),
            comp_per_provider_k=round(rev_per_loc / providers * 1.2 * 0.35 * 1000, 0),
            net_margin_per_provider_mm=round(rev_per_loc / providers * 1.2 * 0.25, 2),
            roi_multiple=round(1 / 0.35, 2),
        ),
        ProviderYield(
            role="Mid-level Provider (NP/PA)",
            annual_visits_per_provider=int(visits / providers * 0.88),
            annual_revenue_per_provider_mm=round(rev_per_loc / providers * 0.80, 2),
            comp_per_provider_k=round(rev_per_loc / providers * 0.80 * 0.25 * 1000, 0),
            net_margin_per_provider_mm=round(rev_per_loc / providers * 0.80 * 0.35, 2),
            roi_multiple=round(1 / 0.25, 2),
        ),
    ]
    return rows


def _build_site_scenarios(profile: Dict, capex: float, months_to_mat: int) -> List[SiteScenario]:
    rev = profile["rev_per_loc_mm"]
    cm = profile["contrib_margin_pct"]
    fixed = profile["fixed_cost_per_loc_mm"]

    scenarios = []
    for label, rev_mult, maturity_factor in [
        ("Mature Site (Y3+)", 1.05, 1.0),
        ("Year 1 New Site", 0.40, 0.4),
        ("Year 2 New Site", 0.75, 0.75),
        ("Underperforming Site", 0.68, 1.0),
    ]:
        scen_rev = rev * rev_mult
        contribution = scen_rev * cm - (fixed * maturity_factor * 0.2)   # some fixed cost scaled
        cm_pct = contribution / scen_rev if scen_rev else 0
        # Cash flow = contribution - capex amortization
        capex_amort = capex / 7   # 7-year
        cash = contribution - capex_amort
        payback = round(capex / contribution, 1) if contribution > 0 else 99.0
        scenarios.append(SiteScenario(
            scenario=label,
            revenue_mm=round(scen_rev, 2),
            contribution_mm=round(contribution, 2),
            contribution_margin_pct=round(cm_pct, 3),
            cash_flow_mm=round(cash, 2),
            years_to_payback=payback,
        ))
    return scenarios


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_unit_economics(
    sector: str = "Dermatology",
    num_locations: int = 25,
) -> UnitEconomicsResult:
    corpus = _load_corpus()
    profile = _get_profile(sector)

    rev_per_loc = profile["rev_per_loc_mm"]
    capex = profile["capex_per_loc_mm"]
    months = profile["months_to_maturity"]
    cm_pct = profile["contrib_margin_pct"]

    ramp = _build_ramp_curve(months, rev_per_loc, cm_pct, capex)
    payback = _payback_years(ramp, capex)
    metrics = _build_location_metrics(profile)
    visits = _build_visits(profile)
    providers = _build_provider_yield(profile)
    scenarios = _build_site_scenarios(profile, capex, months)

    # De novo IRR: compute over 10-yr hold
    annual_cash = rev_per_loc * cm_pct
    hold = 10
    total_returned = annual_cash * hold * 0.85 + rev_per_loc * 3.5    # plus terminal value
    de_novo_moic = total_returned / capex if capex else 0
    de_novo_irr = (de_novo_moic ** (1 / hold) - 1) if de_novo_moic > 0 else 0

    total_revenue = rev_per_loc * num_locations

    return UnitEconomicsResult(
        sector=sector,
        num_locations=num_locations,
        total_revenue_mm=round(total_revenue, 1),
        revenue_per_location_mm=round(rev_per_loc, 2),
        payback_years=payback,
        ramp_curve=ramp,
        location_metrics=metrics,
        visit_profile=visits,
        provider_yield=providers,
        site_scenarios=scenarios,
        de_novo_irr=round(de_novo_irr, 4),
        new_site_annual_capacity=int(profile["visits_per_loc"]),
        corpus_deal_count=len(corpus),
    )
