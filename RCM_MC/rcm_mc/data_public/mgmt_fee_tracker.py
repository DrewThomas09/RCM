"""Management Fee Tracker — portfolio-level fee monitoring and LP economics from corpus."""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Fee structure assumptions
# ---------------------------------------------------------------------------

_MGMT_FEE_SCHEDULE = {
    "<$250M": {"rate": 0.020, "offset_pct": 0.80},
    "$250-500M": {"rate": 0.018, "offset_pct": 0.80},
    "$500-1B": {"rate": 0.015, "offset_pct": 0.80},
    ">$1B": {"rate": 0.012, "offset_pct": 0.80},
}

_CARRIED_INTEREST_RATE = 0.20
_PREFERRED_RETURN = 0.08       # 8% hurdle
_GP_CATCH_UP = 0.50           # 50% catch-up after hurdle


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PortfolioPosition:
    company: str
    sector: str
    invested_equity_mm: float
    current_nav_mm: float
    entry_year: int
    hold_years: float
    status: str           # "Active", "Realized", "Partially Realized"
    moic_current: float
    irr_current: float


@dataclass
class FeeCalculation:
    company: str
    committed_capital_mm: float
    invested_equity_mm: float
    mgmt_fee_rate: float
    annual_mgmt_fee_mm: float
    monitoring_fee_mm: float      # deal-level monitoring
    transaction_fee_mm: float     # one-time at close
    total_annual_fees_mm: float
    lp_offset_mm: float           # mgmt fee offset applied to LP
    net_fee_to_lp_mm: float


@dataclass
class CarryCalculation:
    company: str
    invested_equity_mm: float
    distributions_mm: float
    preferred_return_mm: float
    carry_base_mm: float
    carry_amount_mm: float
    lp_net_proceeds_mm: float
    gross_moic: float
    net_moic_to_lp: float


@dataclass
class FundEconomics:
    fund_size_mm: float
    committed_capital_mm: float
    invested_capital_mm: float
    reserve_pct: float
    deployment_pct: float
    total_annual_fees_mm: float
    fee_drag_on_moic: float       # bps MOIC drag from fees
    total_carry_paid_mm: float
    lp_net_moic: float
    gp_moic: float


@dataclass
class MgmtFeeResult:
    positions: List[PortfolioPosition]
    fee_calculations: List[FeeCalculation]
    carry_calculations: List[CarryCalculation]
    fund_economics: FundEconomics
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 59):
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


def _fund_size_bucket(fund_mm: float) -> str:
    if fund_mm < 250:   return "<$250M"
    if fund_mm < 500:   return "$250-500M"
    if fund_mm < 1000:  return "$500-1B"
    return ">$1B"


def _calc_irr(moic: float, hold_years: float) -> float:
    if hold_years <= 0 or moic <= 0:
        return 0.0
    return round((moic ** (1.0 / hold_years)) - 1.0, 4)


def _calc_carry(invested: float, distributions: float, hold_years: float,
                carry_rate: float = 0.20, hurdle: float = 0.08) -> CarryCalculation:
    if invested <= 0:
        return CarryCalculation("", invested, distributions, 0, 0, 0, distributions, 0, 0)

    gross_moic = distributions / invested if invested else 0.0
    preferred_return = invested * ((1 + hurdle) ** hold_years - 1) if hold_years > 0 else 0.0
    carry_base = max(0.0, distributions - invested - preferred_return)
    carry = carry_base * carry_rate
    lp_net = distributions - carry
    net_moic = lp_net / invested if invested else 0.0

    return CarryCalculation(
        company="",
        invested_equity_mm=round(invested, 2),
        distributions_mm=round(distributions, 2),
        preferred_return_mm=round(preferred_return, 2),
        carry_base_mm=round(carry_base, 2),
        carry_amount_mm=round(carry, 2),
        lp_net_proceeds_mm=round(lp_net, 2),
        gross_moic=round(gross_moic, 2),
        net_moic_to_lp=round(net_moic, 2),
    )


# ---------------------------------------------------------------------------
# Default portfolio positions (from corpus sample)
# ---------------------------------------------------------------------------

def _build_default_positions(corpus: List[dict]) -> List[PortfolioPosition]:
    # Sample 8 active positions from corpus
    active = [d for d in corpus if d.get("moic") and d.get("moic") < 3.5 and d.get("hold_years", 0) < 4]
    if not active:
        active = corpus[:8]
    sample = active[:8]

    positions = []
    for d in sample:
        ev = d.get("ev_mm", 100.0)
        em = d.get("ev_ebitda") or 10.0
        ebitda = ev / em if em else 10.0
        eq_pct = 0.45
        invested = ev * eq_pct
        hold = d.get("hold_years") or 3.0
        moic = d.get("moic") or 2.5
        irr = d.get("irr") or _calc_irr(moic, hold)
        nav = invested * moic * 0.75  # partial realization proxy

        positions.append(PortfolioPosition(
            company=d.get("company_name", "—"),
            sector=d.get("sector", "—"),
            invested_equity_mm=round(invested, 2),
            current_nav_mm=round(nav, 2),
            entry_year=d.get("year", 2020),
            hold_years=round(hold, 1),
            status="Active",
            moic_current=round(moic, 2),
            irr_current=round(irr, 4),
        ))
    return positions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_mgmt_fee_tracker(
    fund_size_mm: float = 500.0,
    positions: Optional[List[dict]] = None,
) -> MgmtFeeResult:
    corpus = _load_corpus()

    if positions is None:
        pos_objects = _build_default_positions(corpus)
    else:
        pos_objects = [PortfolioPosition(**p) for p in positions]

    sbucket = _fund_size_bucket(fund_size_mm)
    fee_sched = _MGMT_FEE_SCHEDULE[sbucket]
    fee_rate = fee_sched["rate"]
    offset_pct = fee_sched["offset_pct"]

    # Fee calculations per position
    fee_calcs: List[FeeCalculation] = []
    carry_calcs: List[CarryCalculation] = []
    total_invested = sum(p.invested_equity_mm for p in pos_objects)

    for pos in pos_objects:
        annual_mgmt = pos.invested_equity_mm * fee_rate
        monitoring = pos.invested_equity_mm * 0.005 * 0.10  # 50bps monitoring, 10% allocated
        txn_fee = pos.invested_equity_mm * 0.005            # 50bps transaction fee (annualized)
        total_fees = annual_mgmt + monitoring + txn_fee
        lp_offset = annual_mgmt * offset_pct
        net_fee = total_fees - lp_offset

        fee_calcs.append(FeeCalculation(
            company=pos.company,
            committed_capital_mm=round(pos.invested_equity_mm * 1.15, 2),
            invested_equity_mm=pos.invested_equity_mm,
            mgmt_fee_rate=fee_rate,
            annual_mgmt_fee_mm=round(annual_mgmt, 3),
            monitoring_fee_mm=round(monitoring, 3),
            transaction_fee_mm=round(txn_fee, 3),
            total_annual_fees_mm=round(total_fees, 3),
            lp_offset_mm=round(lp_offset, 3),
            net_fee_to_lp_mm=round(net_fee, 3),
        ))

        # Carry calculation
        distributions = pos.invested_equity_mm * pos.moic_current
        cc = _calc_carry(pos.invested_equity_mm, distributions, pos.hold_years)
        cc.company = pos.company
        carry_calcs.append(cc)

    # Fund-level economics
    total_annual_fees = sum(f.total_annual_fees_mm for f in fee_calcs)
    total_carry = sum(c.carry_amount_mm for c in carry_calcs)
    total_distributions = sum(c.distributions_mm for c in carry_calcs)
    lp_net_total = sum(c.lp_net_proceeds_mm for c in carry_calcs)

    gross_moic = total_distributions / total_invested if total_invested else 0.0
    net_moic = lp_net_total / total_invested if total_invested else 0.0
    fee_drag = gross_moic - net_moic

    gp_total = total_carry + total_annual_fees * len(pos_objects) * 0.5  # rough
    gp_moic = gp_total / (fund_size_mm * 0.02) if fund_size_mm > 0 else 0.0

    fund_econ = FundEconomics(
        fund_size_mm=fund_size_mm,
        committed_capital_mm=round(total_invested * 1.15, 2),
        invested_capital_mm=round(total_invested, 2),
        reserve_pct=round(1 - total_invested / (fund_size_mm * 0.85), 3),
        deployment_pct=round(total_invested / fund_size_mm, 3),
        total_annual_fees_mm=round(total_annual_fees, 2),
        fee_drag_on_moic=round(fee_drag, 3),
        total_carry_paid_mm=round(total_carry, 2),
        lp_net_moic=round(net_moic, 2),
        gp_moic=round(gp_moic, 2),
    )

    return MgmtFeeResult(
        positions=pos_objects,
        fee_calculations=fee_calcs,
        carry_calculations=carry_calcs,
        fund_economics=fund_econ,
        corpus_deal_count=len(corpus),
    )
