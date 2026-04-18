"""Real Estate / Sale-Leaseback Analyzer.

Healthcare deals frequently have undervalued medical office / facility real estate.
Models:
- Current owned vs leased mix
- Market cap rate and implied SLB value
- Lease-vs-own economics
- SLB proceeds and impact on equity MOIC
- Lease term structure and escalators
- Real estate NAV bridge
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Cap rate benchmarks (MOB = medical office building)
# ---------------------------------------------------------------------------

_CAP_RATE_BENCHMARKS = {
    "Class A MOB (on-campus)":    0.055,
    "Class A MOB (off-campus)":   0.062,
    "Class B MOB":                0.072,
    "Ambulatory Surgery Center":  0.065,
    "Dialysis Center":            0.060,
    "Skilled Nursing Facility":   0.090,
    "Behavioral Health Facility": 0.075,
    "Urgent Care":                0.068,
    "Dental Office":              0.070,
    "Class C MOB / Older Stock":  0.085,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PropertyAsset:
    property_id: str
    property_type: str
    sqft: int
    current_ownership: str        # "owned", "leased_from_related", "third_party_leased"
    annual_rent_mm: float         # or NOI if owned
    implied_cap_rate: float
    implied_value_mm: float
    slb_proceeds_mm: float
    notes: str


@dataclass
class LeaseTerm:
    property_id: str
    lease_type: str
    years_remaining: float
    annual_escalator_pct: float
    renewal_options: str
    market_rent_vs_current: float    # current / market
    renewal_risk: str


@dataclass
class SLBScenario:
    scenario: str
    properties_in_scope: int
    total_slb_proceeds_mm: float
    incremental_rent_mm: float
    net_ebitda_impact_mm: float
    debt_paydown_mm: float
    equity_return_mm: float
    implied_moic_lift: float


@dataclass
class RealEstateResult:
    total_sqft: int
    owned_sqft: int
    leased_sqft: int
    current_re_nav_mm: float
    realizable_re_value_mm: float
    current_annual_rent_mm: float
    annual_rent_saved_mm: float
    assets: List[PropertyAsset]
    leases: List[LeaseTerm]
    slb_scenarios: List[SLBScenario]
    weighted_avg_cap_rate: float
    annual_occupancy_cost_pct_rev: float
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


def _cap_rate_for(prop_type: str) -> float:
    return _CAP_RATE_BENCHMARKS.get(prop_type, 0.065)


def _build_assets(
    n_locations: int, avg_sqft: int, sector: str, revenue_mm: float,
) -> List[PropertyAsset]:
    rows = []
    rent_per_sqft = 32    # typical MOB
    noi_per_sqft_owned = 18    # net after opex

    # Determine property type mix based on sector
    if sector in ("ASC", "Surgery Center"):
        prop_type = "Ambulatory Surgery Center"
    elif sector in ("Dialysis", "Kidney Care"):
        prop_type = "Dialysis Center"
    elif sector in ("Skilled Nursing", "Senior Care"):
        prop_type = "Skilled Nursing Facility"
    elif sector in ("Behavioral Health", "Addiction Treatment"):
        prop_type = "Behavioral Health Facility"
    elif sector in ("Urgent Care", "Walk-in Clinics"):
        prop_type = "Urgent Care"
    elif sector in ("Dental",):
        prop_type = "Dental Office"
    else:
        prop_type = "Class A MOB (off-campus)"

    import hashlib
    for i in range(n_locations):
        h = int(hashlib.md5(f"loc{i}".encode()).hexdigest()[:6], 16)
        sqft = avg_sqft + (h % 4000 - 2000)
        # Ownership mix: 35% owned, 50% third-party, 15% related-party
        ownership_bucket = h % 100
        if ownership_bucket < 35:
            ownership = "owned"
            # NOI = square feet × NOI per sqft
            annual_val = sqft * noi_per_sqft_owned / 1_000_000
            cap = _cap_rate_for(prop_type)
            implied_val = annual_val / cap if cap else 0
            slb = implied_val * 0.92    # 8% transaction cost
        elif ownership_bucket < 85:
            ownership = "third_party_leased"
            rent = sqft * rent_per_sqft / 1_000_000
            annual_val = rent
            cap = _cap_rate_for(prop_type)
            implied_val = rent / cap if cap else 0
            slb = 0    # Already leased, no SLB
        else:
            ownership = "leased_from_related"
            rent = sqft * rent_per_sqft * 0.92 / 1_000_000    # slight discount
            annual_val = rent
            cap = _cap_rate_for(prop_type)
            implied_val = rent / cap if cap else 0
            slb = implied_val * 0.90    # can SLB if related-party restructured

        notes = "SLB candidate" if ownership == "owned" else ("Mkt assessment" if ownership == "third_party_leased" else "Related-party review")
        rows.append(PropertyAsset(
            property_id=f"Loc-{i + 1:03d}",
            property_type=prop_type,
            sqft=sqft,
            current_ownership=ownership,
            annual_rent_mm=round(annual_val, 3),
            implied_cap_rate=round(cap, 4),
            implied_value_mm=round(implied_val, 2),
            slb_proceeds_mm=round(slb, 2),
            notes=notes,
        ))
    return rows


def _build_leases(assets: List[PropertyAsset]) -> List[LeaseTerm]:
    rows = []
    import hashlib
    for a in assets:
        if a.current_ownership == "owned":
            continue
        h = int(hashlib.md5(a.property_id.encode()).hexdigest()[:6], 16)
        years_rem = 2 + (h % 12)
        escalator = 0.025 + (h % 20) / 1000
        mkt_ratio = 0.85 + (h % 30) / 100
        renewal_risk = "low" if years_rem > 7 else ("medium" if years_rem > 3 else "high")
        rows.append(LeaseTerm(
            property_id=a.property_id,
            lease_type="Triple Net" if h % 2 == 0 else "Modified Gross",
            years_remaining=round(years_rem, 1),
            annual_escalator_pct=round(escalator, 4),
            renewal_options=f"{1 + (h % 3)} × 5-yr",
            market_rent_vs_current=round(mkt_ratio, 3),
            renewal_risk=renewal_risk,
        ))
    return rows


def _build_slb_scenarios(
    assets: List[PropertyAsset], current_rent: float, ebitda_mm: float, ev_mm: float,
) -> List[SLBScenario]:
    # Scenarios: Owned-only SLB, Owned + related-party, Full optimization
    rows = []

    # Scenario A: Owned-only
    owned = [a for a in assets if a.current_ownership == "owned"]
    slb_a = sum(a.slb_proceeds_mm for a in owned)
    incr_rent_a = sum(a.annual_rent_mm * 1.15 for a in owned)  # SLB rent typically 15% premium over owned NOI
    # Net EBITDA impact: lost NOI minus new rent (net rent will reduce EBITDA since we didn't have "rent" on owned)
    # Actually: owned properties had no rent expense; post-SLB we pay rent
    net_ebitda_a = -incr_rent_a    # all incremental rent is new expense
    debt_paydown_a = slb_a * 0.60    # 60% to debt, 40% to equity distribution
    eq_return_a = slb_a * 0.40
    moic_lift_a = eq_return_a / (ev_mm * 0.45) if ev_mm else 0

    rows.append(SLBScenario(
        scenario="Owned-only SLB (A)",
        properties_in_scope=len(owned),
        total_slb_proceeds_mm=round(slb_a, 1),
        incremental_rent_mm=round(incr_rent_a, 2),
        net_ebitda_impact_mm=round(net_ebitda_a, 2),
        debt_paydown_mm=round(debt_paydown_a, 1),
        equity_return_mm=round(eq_return_a, 1),
        implied_moic_lift=round(moic_lift_a, 3),
    ))

    # Scenario B: Owned + related-party
    related = [a for a in assets if a.current_ownership in ("owned", "leased_from_related")]
    slb_b = sum(a.slb_proceeds_mm for a in related)
    incr_rent_b = sum(a.annual_rent_mm * 1.08 for a in related)
    # For related-party, some rent already being paid - so net is just the premium
    existing_rent_b = sum(a.annual_rent_mm for a in [a for a in assets if a.current_ownership == "leased_from_related"])
    net_ebitda_b = -(incr_rent_b - existing_rent_b)
    debt_paydown_b = slb_b * 0.60
    eq_return_b = slb_b * 0.40
    moic_lift_b = eq_return_b / (ev_mm * 0.45) if ev_mm else 0

    rows.append(SLBScenario(
        scenario="Owned + Related-Party Restructure (B)",
        properties_in_scope=len(related),
        total_slb_proceeds_mm=round(slb_b, 1),
        incremental_rent_mm=round(incr_rent_b, 2),
        net_ebitda_impact_mm=round(net_ebitda_b, 2),
        debt_paydown_mm=round(debt_paydown_b, 1),
        equity_return_mm=round(eq_return_b, 1),
        implied_moic_lift=round(moic_lift_b, 3),
    ))

    # Scenario C: Renegotiate 3rd-party leases down 5%
    third_party = [a for a in assets if a.current_ownership == "third_party_leased"]
    rent_savings = sum(a.annual_rent_mm for a in third_party) * 0.05
    rows.append(SLBScenario(
        scenario="3rd-Party Lease Renegotiation (C)",
        properties_in_scope=len(third_party),
        total_slb_proceeds_mm=0,
        incremental_rent_mm=-rent_savings,
        net_ebitda_impact_mm=round(rent_savings, 2),
        debt_paydown_mm=0,
        equity_return_mm=0,
        implied_moic_lift=round(rent_savings * 11 / (ev_mm * 0.45), 3),    # assume 11x exit
    ))

    # Scenario D: All-in optimization
    total_proceeds = slb_b
    total_ebitda_impact = net_ebitda_b + rent_savings
    rows.append(SLBScenario(
        scenario="All-in Optimization (A + B + C)",
        properties_in_scope=len(related) + len(third_party),
        total_slb_proceeds_mm=round(total_proceeds, 1),
        incremental_rent_mm=round(incr_rent_b - rent_savings, 2),
        net_ebitda_impact_mm=round(total_ebitda_impact, 2),
        debt_paydown_mm=round(total_proceeds * 0.60, 1),
        equity_return_mm=round(total_proceeds * 0.40, 1),
        implied_moic_lift=round((total_proceeds * 0.40 + total_ebitda_impact * 11) / (ev_mm * 0.45), 3),
    ))

    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_real_estate(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    ev_mm: float = 300.0,
    ebitda_mm: float = 25.0,
    n_locations: int = 18,
    avg_sqft_per_location: int = 6500,
) -> RealEstateResult:
    corpus = _load_corpus()

    assets = _build_assets(n_locations, avg_sqft_per_location, sector, revenue_mm)
    leases = _build_leases(assets)
    current_rent = sum(a.annual_rent_mm for a in assets if a.current_ownership != "owned")
    slb_scenarios = _build_slb_scenarios(assets, current_rent, ebitda_mm, ev_mm)

    total_sqft = sum(a.sqft for a in assets)
    owned_sqft = sum(a.sqft for a in assets if a.current_ownership == "owned")
    leased_sqft = total_sqft - owned_sqft

    re_nav = sum(a.implied_value_mm for a in assets if a.current_ownership == "owned")
    realizable = sum(a.slb_proceeds_mm for a in assets)

    # Rent savings from Scenario C
    rent_saved = -slb_scenarios[2].incremental_rent_mm if len(slb_scenarios) >= 3 else 0

    # Weighted avg cap rate
    cap_weighted = sum(a.implied_cap_rate * a.implied_value_mm for a in assets) / sum(a.implied_value_mm for a in assets) if assets else 0.065

    occupancy_cost_pct = current_rent / revenue_mm if revenue_mm else 0

    return RealEstateResult(
        total_sqft=total_sqft,
        owned_sqft=owned_sqft,
        leased_sqft=leased_sqft,
        current_re_nav_mm=round(re_nav, 2),
        realizable_re_value_mm=round(realizable, 2),
        current_annual_rent_mm=round(current_rent, 2),
        annual_rent_saved_mm=round(rent_saved, 2),
        assets=assets,
        leases=leases,
        slb_scenarios=slb_scenarios,
        weighted_avg_cap_rate=round(cap_weighted, 4),
        annual_occupancy_cost_pct_rev=round(occupancy_cost_pct, 4),
        corpus_deal_count=len(corpus),
    )
