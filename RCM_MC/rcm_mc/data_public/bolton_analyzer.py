"""Bolt-on M&A Analyzer — buy-and-build roll-up economics.

Models platform + N bolt-on acquisitions:
- Multiple arbitrage (platform EV/EBITDA - bolt-on EV/EBITDA)
- Synergy phasing (revenue + cost)
- Integration costs
- Pro-forma combined EBITDA and exit valuation
- MOIC/IRR with vs. without bolt-ons
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Sector bolt-on priors from corpus
# ---------------------------------------------------------------------------

_PLATFORM_MULT_BY_SECTOR = {
    "Physician Services": 13.0,
    "Dental": 11.5,
    "Dermatology": 13.5,
    "Ophthalmology": 12.5,
    "Gastroenterology": 13.0,
    "Orthopedics": 12.5,
    "ABA Therapy": 11.0,
    "Behavioral Health": 10.5,
    "Home Health": 9.5,
    "Hospice": 10.0,
    "Pharmacy": 9.0,
    "Urgent Care": 10.5,
    "Veterinary": 14.0,
    "Fertility": 13.5,
    "Radiology": 10.5,
    "Anesthesiology": 10.0,
    "EHR/EMR": 16.0,
    "Healthcare IT": 14.5,
}

_BOLTON_MULT_BY_SECTOR = {
    "Physician Services": 7.5,
    "Dental": 6.5,
    "Dermatology": 7.8,
    "Ophthalmology": 7.2,
    "Gastroenterology": 7.5,
    "Orthopedics": 7.0,
    "ABA Therapy": 6.5,
    "Behavioral Health": 6.0,
    "Home Health": 5.5,
    "Hospice": 5.8,
    "Pharmacy": 5.5,
    "Urgent Care": 6.0,
    "Veterinary": 8.0,
    "Fertility": 7.5,
    "Radiology": 6.5,
    "Anesthesiology": 6.5,
    "EHR/EMR": 9.0,
    "Healthcare IT": 8.5,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BoltOn:
    label: str
    ebitda_mm: float
    purchase_mult: float
    purchase_price_mm: float
    revenue_synergy_pct: float
    cost_synergy_pct: float
    integration_cost_mm: float
    acquire_year: int
    run_rate_synergy_mm: float


@dataclass
class YearlyProjection:
    year: int
    platform_ebitda_mm: float
    bolton_ebitda_mm: float
    synergy_mm: float
    total_ebitda_mm: float
    cumulative_boltons: int


@dataclass
class ReturnScenario:
    label: str                   # "No Bolt-ons", "With Bolt-ons"
    exit_year: int
    exit_ebitda_mm: float
    exit_multiple: float
    exit_ev_mm: float
    exit_equity_mm: float
    invested_equity_mm: float
    moic: float
    irr: float


@dataclass
class MultipleArbitrage:
    platform_mult: float
    avg_bolton_mult: float
    mult_arbitrage: float        # platform - bolton
    blended_entry_mult: float    # weighted by EBITDA
    value_uplift_mm: float       # arbitrage × total bolton EBITDA


@dataclass
class BoltOnResult:
    sector: str
    platform_ev_mm: float
    platform_ebitda_mm: float
    platform_mult: float
    bolt_ons: List[BoltOn]
    projections: List[YearlyProjection]
    multiple_arbitrage: MultipleArbitrage
    scenarios: List[ReturnScenario]
    total_capital_deployed_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 60):
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


def _irr(moic: float, years: float) -> float:
    if years <= 0 or moic <= 0:
        return 0.0
    return (moic ** (1.0 / years)) - 1.0


def _pick_mult(sector: str, default_platform: float, default_bolton: float):
    plat = _PLATFORM_MULT_BY_SECTOR.get(sector, default_platform)
    bolt = _BOLTON_MULT_BY_SECTOR.get(sector, default_bolton)
    return plat, bolt


def _generate_boltons(
    platform_ebitda_mm: float,
    bolton_mult: float,
    n_boltons: int,
    revenue_synergy_pct: float,
    cost_synergy_pct: float,
) -> List[BoltOn]:
    """Generate N bolt-ons at decreasing size profile."""
    boltons = []
    # Bolt-on EBITDA as 15-30% of platform, declining
    sizes = [0.28, 0.22, 0.18, 0.15, 0.12, 0.10, 0.09, 0.08, 0.07, 0.06]
    for i in range(min(n_boltons, len(sizes))):
        pct = sizes[i]
        ebitda = round(platform_ebitda_mm * pct, 2)
        # Bolt-on mult drops slightly as we go further down-market
        mult = bolton_mult * (1.0 - i * 0.015)
        purchase = round(ebitda * mult, 2)
        # Synergies on acquired EBITDA
        rev_syn = round(ebitda * revenue_synergy_pct, 3)
        cost_syn = round(ebitda * cost_synergy_pct, 3)
        total_syn = round(rev_syn + cost_syn, 3)
        # Integration cost: 15% of purchase price
        integration = round(purchase * 0.15, 2)
        boltons.append(BoltOn(
            label=f"Bolt-on {i + 1}",
            ebitda_mm=ebitda,
            purchase_mult=round(mult, 2),
            purchase_price_mm=purchase,
            revenue_synergy_pct=round(revenue_synergy_pct, 3),
            cost_synergy_pct=round(cost_synergy_pct, 3),
            integration_cost_mm=integration,
            acquire_year=1 + (i // 2),   # two per year
            run_rate_synergy_mm=total_syn,
        ))
    return boltons


def _build_projections(
    platform_ebitda_mm: float,
    organic_growth_pct: float,
    boltons: List[BoltOn],
    hold_years: float,
) -> List[YearlyProjection]:
    rows = []
    for yr in range(0, int(hold_years) + 1):
        plat = platform_ebitda_mm * ((1 + organic_growth_pct) ** yr)
        bolt_ebitda = 0.0
        synergy = 0.0
        count = 0
        for b in boltons:
            if yr >= b.acquire_year:
                # bolt-on EBITDA grows at same organic rate post-acquisition
                years_owned = yr - b.acquire_year
                bolt_ebitda += b.ebitda_mm * ((1 + organic_growth_pct) ** years_owned)
                # Synergies phase in over 2 years (50% yr+1, 100% yr+2)
                if years_owned >= 2:
                    synergy += b.run_rate_synergy_mm
                elif years_owned >= 1:
                    synergy += b.run_rate_synergy_mm * 0.5
                count += 1
        total = plat + bolt_ebitda + synergy
        rows.append(YearlyProjection(
            year=yr,
            platform_ebitda_mm=round(plat, 2),
            bolton_ebitda_mm=round(bolt_ebitda, 2),
            synergy_mm=round(synergy, 2),
            total_ebitda_mm=round(total, 2),
            cumulative_boltons=count,
        ))
    return rows


def _build_arbitrage(
    platform_mult: float,
    boltons: List[BoltOn],
    platform_ebitda_mm: float,
) -> MultipleArbitrage:
    if not boltons:
        return MultipleArbitrage(platform_mult, platform_mult, 0.0, platform_mult, 0.0)

    avg_bolton = sum(b.purchase_mult for b in boltons) / len(boltons)
    bolton_total_ebitda = sum(b.ebitda_mm for b in boltons)
    bolton_total_cost = sum(b.purchase_price_mm for b in boltons)
    total_ebitda = platform_ebitda_mm + bolton_total_ebitda
    total_cost = platform_ebitda_mm * platform_mult + bolton_total_cost
    blended = total_cost / total_ebitda if total_ebitda else platform_mult
    arbitrage = platform_mult - avg_bolton
    # Immediate value uplift from multiple arbitrage (applied to bolt-on EBITDA)
    uplift = arbitrage * bolton_total_ebitda

    return MultipleArbitrage(
        platform_mult=round(platform_mult, 2),
        avg_bolton_mult=round(avg_bolton, 2),
        mult_arbitrage=round(arbitrage, 2),
        blended_entry_mult=round(blended, 2),
        value_uplift_mm=round(uplift, 1),
    )


def _build_scenarios(
    platform_ev_mm: float,
    platform_ebitda_mm: float,
    platform_mult: float,
    organic_growth_pct: float,
    boltons: List[BoltOn],
    hold_years: int,
    exit_mult: float,
    equity_pct: float,
) -> List[ReturnScenario]:
    scenarios = []

    # No bolt-ons scenario
    no_boltons_proj = _build_projections(platform_ebitda_mm, organic_growth_pct, [], hold_years)
    exit_ebitda_no = no_boltons_proj[-1].total_ebitda_mm
    exit_ev_no = exit_ebitda_no * exit_mult
    invested_no = platform_ev_mm * equity_pct
    # Exit equity after senior debt paid down
    exit_debt_no = platform_ev_mm * (1 - equity_pct) * 0.7  # 30% amort
    exit_equity_no = exit_ev_no - exit_debt_no
    moic_no = exit_equity_no / invested_no if invested_no else 0.0
    scenarios.append(ReturnScenario(
        label="No Bolt-ons",
        exit_year=hold_years,
        exit_ebitda_mm=round(exit_ebitda_no, 1),
        exit_multiple=round(exit_mult, 2),
        exit_ev_mm=round(exit_ev_no, 1),
        exit_equity_mm=round(exit_equity_no, 1),
        invested_equity_mm=round(invested_no, 1),
        moic=round(moic_no, 2),
        irr=round(_irr(moic_no, hold_years), 4),
    ))

    # With bolt-ons scenario
    with_proj = _build_projections(platform_ebitda_mm, organic_growth_pct, boltons, hold_years)
    exit_ebitda_w = with_proj[-1].total_ebitda_mm
    exit_ev_w = exit_ebitda_w * exit_mult
    # Additional equity for bolt-on purchases (assume 60% debt funded)
    bolton_equity = sum(b.purchase_price_mm for b in boltons) * 0.40
    integration_equity = sum(b.integration_cost_mm for b in boltons)
    invested_w = invested_no + bolton_equity + integration_equity
    exit_debt_w = exit_debt_no + sum(b.purchase_price_mm for b in boltons) * 0.60 * 0.85
    exit_equity_w = exit_ev_w - exit_debt_w
    moic_w = exit_equity_w / invested_w if invested_w else 0.0
    scenarios.append(ReturnScenario(
        label="With Bolt-ons",
        exit_year=hold_years,
        exit_ebitda_mm=round(exit_ebitda_w, 1),
        exit_multiple=round(exit_mult, 2),
        exit_ev_mm=round(exit_ev_w, 1),
        exit_equity_mm=round(exit_equity_w, 1),
        invested_equity_mm=round(invested_w, 1),
        moic=round(moic_w, 2),
        irr=round(_irr(moic_w, hold_years), 4),
    ))

    return scenarios


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_bolton_analyzer(
    sector: str = "Dermatology",
    platform_ebitda_mm: float = 25.0,
    n_boltons: int = 6,
    organic_growth_pct: float = 0.06,
    revenue_synergy_pct: float = 0.03,
    cost_synergy_pct: float = 0.08,
    hold_years: int = 5,
    exit_mult_expansion: float = 0.5,
    equity_pct: float = 0.45,
) -> BoltOnResult:
    corpus = _load_corpus()

    platform_mult, bolton_mult = _pick_mult(sector, 12.0, 6.5)
    platform_ev_mm = round(platform_ebitda_mm * platform_mult, 1)

    boltons = _generate_boltons(
        platform_ebitda_mm=platform_ebitda_mm,
        bolton_mult=bolton_mult,
        n_boltons=n_boltons,
        revenue_synergy_pct=revenue_synergy_pct,
        cost_synergy_pct=cost_synergy_pct,
    )

    projections = _build_projections(
        platform_ebitda_mm, organic_growth_pct, boltons, hold_years
    )

    arbitrage = _build_arbitrage(platform_mult, boltons, platform_ebitda_mm)

    exit_mult = platform_mult + exit_mult_expansion
    scenarios = _build_scenarios(
        platform_ev_mm=platform_ev_mm,
        platform_ebitda_mm=platform_ebitda_mm,
        platform_mult=platform_mult,
        organic_growth_pct=organic_growth_pct,
        boltons=boltons,
        hold_years=hold_years,
        exit_mult=exit_mult,
        equity_pct=equity_pct,
    )

    total_deployed = (
        platform_ev_mm * equity_pct
        + sum(b.purchase_price_mm for b in boltons) * 0.40
        + sum(b.integration_cost_mm for b in boltons)
    )

    return BoltOnResult(
        sector=sector,
        platform_ev_mm=platform_ev_mm,
        platform_ebitda_mm=round(platform_ebitda_mm, 2),
        platform_mult=round(platform_mult, 2),
        bolt_ons=boltons,
        projections=projections,
        multiple_arbitrage=arbitrage,
        scenarios=scenarios,
        total_capital_deployed_mm=round(total_deployed, 1),
        corpus_deal_count=len(corpus),
    )
