"""Continuation Vehicle Analyzer — GP-led secondary economics.

Models a GP-led continuation vehicle (CV) to extend hold on a trophy asset:
- Strip sale vs single-asset CV vs multi-asset CV
- Pricing (NAV vs premium/discount)
- LP rollover economics
- New LP investors
- GP reset carry and new fund hurdle
- ILPA best-practice alignment
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CVStructure:
    structure_type: str          # "Single-Asset CV", "Multi-Asset CV", "Strip Sale"
    cv_size_mm: float
    existing_lp_rollover_pct: float
    new_investor_commitment_mm: float
    gp_commitment_pct: float
    new_hurdle: float
    new_carry_rate: float
    management_fee: float
    time_to_close_mo: int


@dataclass
class PricingAnalysis:
    methodology: str
    implied_price_mm: float
    discount_to_nav: float
    premium_to_nav: float
    rationale: str


@dataclass
class LPElectionRow:
    lp_class: str
    commitment_mm: float
    option_status_quo: str
    option_rollover: str
    option_sell: str
    typical_election: str


@dataclass
class GPEconomics:
    item: str
    existing_fund_mm: float
    cv_new_mm: float
    delta_mm: float
    notes: str


@dataclass
class ExitAnalysis:
    exit_year: int
    ebitda_mm: float
    exit_multiple: float
    exit_ev_mm: float
    cv_net_equity_mm: float
    cv_moic: float
    cv_irr: float
    lp_rollover_return_mm: float


@dataclass
class ContinuationVehicleResult:
    asset_name: str
    current_nav_mm: float
    hold_years_elapsed: int
    remaining_hold_potential: int
    recommended_structure: str
    structures: List[CVStructure]
    pricing: List[PricingAnalysis]
    lp_elections: List[LPElectionRow]
    gp_economics: List[GPEconomics]
    exit_scenarios: List[ExitAnalysis]
    total_transaction_cost_pct: float
    ilpa_alignment_score: int
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 71):
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


def _build_structures(current_nav: float) -> List[CVStructure]:
    return [
        CVStructure(
            structure_type="Single-Asset Continuation Vehicle",
            cv_size_mm=round(current_nav * 0.95, 1),
            existing_lp_rollover_pct=0.30,
            new_investor_commitment_mm=round(current_nav * 0.66, 1),
            gp_commitment_pct=0.04,
            new_hurdle=0.08,
            new_carry_rate=0.20,
            management_fee=0.010,
            time_to_close_mo=6,
        ),
        CVStructure(
            structure_type="Multi-Asset Continuation Vehicle (portfolio strip)",
            cv_size_mm=round(current_nav * 2.8, 1),
            existing_lp_rollover_pct=0.25,
            new_investor_commitment_mm=round(current_nav * 2.0, 1),
            gp_commitment_pct=0.03,
            new_hurdle=0.08,
            new_carry_rate=0.175,
            management_fee=0.0125,
            time_to_close_mo=9,
        ),
        CVStructure(
            structure_type="Strip Sale (partial secondary)",
            cv_size_mm=round(current_nav * 0.50, 1),
            existing_lp_rollover_pct=0.55,
            new_investor_commitment_mm=round(current_nav * 0.45, 1),
            gp_commitment_pct=0.02,
            new_hurdle=0.08,
            new_carry_rate=0.15,
            management_fee=0.007,
            time_to_close_mo=4,
        ),
        CVStructure(
            structure_type="Non-CV: Direct Secondary Sale (no GP involvement)",
            cv_size_mm=round(current_nav * 0.92, 1),   # typical discount
            existing_lp_rollover_pct=0.0,
            new_investor_commitment_mm=round(current_nav * 0.92, 1),
            gp_commitment_pct=0.0,
            new_hurdle=0.0,
            new_carry_rate=0.0,
            management_fee=0.0,
            time_to_close_mo=3,
        ),
    ]


def _build_pricing(current_nav: float) -> List[PricingAnalysis]:
    return [
        PricingAnalysis(
            methodology="Fairness Opinion (DCF)",
            implied_price_mm=round(current_nav * 1.02, 1),
            discount_to_nav=0,
            premium_to_nav=0.02,
            rationale="Discounted cash flow at 12.5% WACC",
        ),
        PricingAnalysis(
            methodology="Trading Comps + Transaction Comps",
            implied_price_mm=round(current_nav * 0.96, 1),
            discount_to_nav=0.04,
            premium_to_nav=0,
            rationale="4% discount to NAV from comp set; reflects size discount",
        ),
        PricingAnalysis(
            methodology="Third-Party Bid Process",
            implied_price_mm=round(current_nav * 0.95, 1),
            discount_to_nav=0.05,
            premium_to_nav=0,
            rationale="Tertiary bid at 0.95x NAV (market clearing)",
        ),
        PricingAnalysis(
            methodology="Secondary Market Mid",
            implied_price_mm=round(current_nav * 0.92, 1),
            discount_to_nav=0.08,
            premium_to_nav=0,
            rationale="Current secondary market average for healthcare PE",
        ),
    ]


def _build_lp_elections() -> List[LPElectionRow]:
    return [
        LPElectionRow(
            lp_class="Public Pension",
            commitment_mm=22.0,
            option_status_quo="Cash out at strip price",
            option_rollover="Roll into CV",
            option_sell="Sell at market",
            typical_election="Cash out (~80% elect)",
        ),
        LPElectionRow(
            lp_class="Sovereign Wealth Fund",
            commitment_mm=18.0,
            option_status_quo="Cash out",
            option_rollover="Roll forward",
            option_sell="Sell via GP process",
            typical_election="Roll 50%, cash 50%",
        ),
        LPElectionRow(
            lp_class="Endowment / Foundation",
            commitment_mm=14.0,
            option_status_quo="Cash out",
            option_rollover="Roll into CV",
            option_sell="Sell at market",
            typical_election="Roll 70%",
        ),
        LPElectionRow(
            lp_class="Fund of Funds",
            commitment_mm=10.0,
            option_status_quo="Cash out",
            option_rollover="Conditional roll",
            option_sell="Sell at market",
            typical_election="Cash out (~85% elect)",
        ),
        LPElectionRow(
            lp_class="Family Office",
            commitment_mm=14.0,
            option_status_quo="Cash out",
            option_rollover="Roll into CV",
            option_sell="Sell at market",
            typical_election="Roll 60%, cash 40%",
        ),
        LPElectionRow(
            lp_class="Insurance Company",
            commitment_mm=12.0,
            option_status_quo="Cash out",
            option_rollover="Limited roll",
            option_sell="Sell at market",
            typical_election="Cash out (~90% elect)",
        ),
        LPElectionRow(
            lp_class="GP Commitment",
            commitment_mm=5.0,
            option_status_quo="N/A",
            option_rollover="Full roll + new commit",
            option_sell="N/A",
            typical_election="Full rollover (100%)",
        ),
    ]


def _build_gp_economics() -> List[GPEconomics]:
    return [
        GPEconomics(
            item="GP Carry Crystallization",
            existing_fund_mm=22.5,
            cv_new_mm=22.5,
            delta_mm=0.0,
            notes="Existing fund carry locks in at CV close",
        ),
        GPEconomics(
            item="New Carry in CV (reset)",
            existing_fund_mm=0,
            cv_new_mm=18.0,
            delta_mm=18.0,
            notes="Fresh 20% carry on go-forward gains above 8% hurdle",
        ),
        GPEconomics(
            item="Annual Mgmt Fees (CV)",
            existing_fund_mm=0,
            cv_new_mm=3.5,
            delta_mm=3.5,
            notes="100 bps annual on CV NAV",
        ),
        GPEconomics(
            item="GP Rollover Commitment",
            existing_fund_mm=0,
            cv_new_mm=12.0,
            delta_mm=-12.0,
            notes="GP must commit 3-5% of CV",
        ),
        GPEconomics(
            item="Transaction Advisory Fees",
            existing_fund_mm=0,
            cv_new_mm=-4.5,
            delta_mm=-4.5,
            notes="Lawyers, bankers, fairness opinion",
        ),
    ]


def _build_exit_scenarios(current_nav: float) -> List[ExitAnalysis]:
    rows = []
    ebitda_base = current_nav / 11    # assume 11x entry into CV
    for yr_out in [3, 4, 5]:
        # Continued growth at 6%
        final_ebitda = ebitda_base * ((1.06) ** yr_out)
        exit_mult = 12.5    # multiple expansion
        exit_ev = final_ebitda * exit_mult
        # Assume CV starts at 5.5x leverage, pays down
        debt = current_nav * 0.55    # 55% initial debt
        remaining_debt = debt * (1 - 0.08 * yr_out)
        equity = exit_ev - remaining_debt
        moic = equity / current_nav if current_nav else 0
        irr = (moic ** (1 / yr_out) - 1) if moic > 0 else 0
        rollover_return = equity * 0.25    # rollover LPs get their share

        rows.append(ExitAnalysis(
            exit_year=yr_out,
            ebitda_mm=round(final_ebitda, 2),
            exit_multiple=round(exit_mult, 2),
            exit_ev_mm=round(exit_ev, 1),
            cv_net_equity_mm=round(equity, 1),
            cv_moic=round(moic, 2),
            cv_irr=round(irr, 4),
            lp_rollover_return_mm=round(rollover_return, 1),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_continuation_vehicle(
    asset_name: str = "Sample Healthcare Platform",
    current_nav_mm: float = 450.0,
    hold_years_elapsed: int = 5,
) -> ContinuationVehicleResult:
    corpus = _load_corpus()

    structures = _build_structures(current_nav_mm)
    pricing = _build_pricing(current_nav_mm)
    lp_elect = _build_lp_elections()
    gp_econ = _build_gp_economics()
    exits = _build_exit_scenarios(current_nav_mm)

    recommended = structures[0].structure_type    # single-asset typically preferred
    total_tx_cost = 0.025    # ~2.5% of NAV typical all-in

    return ContinuationVehicleResult(
        asset_name=asset_name,
        current_nav_mm=round(current_nav_mm, 1),
        hold_years_elapsed=hold_years_elapsed,
        remaining_hold_potential=4,
        recommended_structure=recommended,
        structures=structures,
        pricing=pricing,
        lp_elections=lp_elect,
        gp_economics=gp_econ,
        exit_scenarios=exits,
        total_transaction_cost_pct=round(total_tx_cost, 4),
        ilpa_alignment_score=78,     # 0-100 on ILPA CV guidelines
        corpus_deal_count=len(corpus),
    )
