"""Underwriting Model — integrated LBO model with corpus-calibrated assumptions."""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Financing assumption tables by size bucket
# ---------------------------------------------------------------------------

_FINANCING: Dict[str, Dict[str, float]] = {
    "<$100M": {
        "senior_leverage":  3.0, "total_leverage": 4.0,
        "equity_pct":       0.50, "cash_interest":  0.065,
        "pik_pct":          0.01, "amort_pct":      0.05,
    },
    "$100-300M": {
        "senior_leverage":  3.5, "total_leverage": 4.75,
        "equity_pct":       0.45, "cash_interest":  0.060,
        "pik_pct":          0.01, "amort_pct":      0.04,
    },
    "$300-700M": {
        "senior_leverage":  4.0, "total_leverage": 5.25,
        "equity_pct":       0.42, "cash_interest":  0.057,
        "pik_pct":          0.01, "amort_pct":      0.035,
    },
    ">$700M": {
        "senior_leverage":  4.5, "total_leverage": 5.75,
        "equity_pct":       0.40, "cash_interest":  0.053,
        "pik_pct":          0.005,"amort_pct":      0.03,
    },
}

_MGMT_FEE_PCT = 0.015   # 1.5% of invested equity per year


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LboSources:
    senior_debt_mm: float
    sub_debt_mm: float
    equity_mm: float
    total_mm: float
    leverage_ratio: float
    equity_pct: float


@dataclass
class LboUses:
    purchase_price_mm: float
    financing_fees_mm: float
    transaction_costs_mm: float
    total_mm: float


@dataclass
class YearProjection:
    year: int
    revenue_mm: float
    ebitda_mm: float
    ebitda_margin: float
    da_mm: float
    ebit_mm: float
    interest_mm: float
    ebt_mm: float
    tax_mm: float
    net_income_mm: float
    capex_mm: float
    change_in_wc_mm: float
    fcf_mm: float
    debt_balance_mm: float
    leverage_ratio: float


@dataclass
class ReturnSummary:
    hold_years: int
    exit_multiple: float
    exit_ev_mm: float
    exit_equity_mm: float
    moic: float
    irr: float
    cash_yield_pct: float   # cumulative FCF / equity invested


@dataclass
class UnderwritingResult:
    sector: str
    ev_mm: float
    ebitda_mm: float
    entry_multiple: float
    size_bucket: str
    sources: LboSources
    uses: LboUses
    projections: List[YearProjection]
    return_scenarios: List[ReturnSummary]
    sensitivity_table: List[Dict]   # rows: exit multiple, cols: hold years
    corpus_p50_moic: float
    corpus_p25_moic: float
    corpus_p75_moic: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 58):
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


def _size_bucket(ev_mm: float) -> str:
    if ev_mm < 100:   return "<$100M"
    if ev_mm < 300:   return "$100-300M"
    if ev_mm < 700:   return "$300-700M"
    return ">$700M"


def _calc_irr(moic: float, hold_years: float) -> float:
    if hold_years <= 0 or moic <= 0:
        return 0.0
    return round((moic ** (1.0 / hold_years)) - 1.0, 4)


def _tax_rate(ebt: float) -> float:
    return max(0.0, ebt * 0.26)


def _build_projections(
    entry_ebitda_mm: float,
    revenue_mm: float,
    ebitda_margin: float,
    debt_mm: float,
    cash_interest_rate: float,
    amort_pct: float,
    rev_growth_pct: float,
    margin_expansion_pp: float,
    capex_pct_rev: float = 0.04,
    wc_pct_rev: float = 0.01,
    hold_years: int = 6,
) -> List[YearProjection]:
    projs = []
    debt = debt_mm
    rev = revenue_mm
    margin = ebitda_margin

    for yr in range(1, hold_years + 1):
        rev = rev * (1 + rev_growth_pct)
        margin = min(margin + margin_expansion_pp / hold_years, 0.45)
        ebitda = rev * margin
        da = rev * 0.025
        ebit = ebitda - da
        interest = debt * cash_interest_rate
        ebt = ebit - interest
        tax = _tax_rate(ebt)
        ni = ebt - tax
        capex = rev * capex_pct_rev
        dwc = rev * wc_pct_rev * 0.5
        fcf = ebitda - interest - tax - capex - dwc
        debt = debt * (1 - amort_pct)
        lev = debt / ebitda if ebitda > 0 else 0.0

        projs.append(YearProjection(
            year=yr,
            revenue_mm=round(rev, 2),
            ebitda_mm=round(ebitda, 2),
            ebitda_margin=round(margin, 4),
            da_mm=round(da, 2),
            ebit_mm=round(ebit, 2),
            interest_mm=round(interest, 2),
            ebt_mm=round(ebt, 2),
            tax_mm=round(tax, 2),
            net_income_mm=round(ni, 2),
            capex_mm=round(capex, 2),
            change_in_wc_mm=round(dwc, 2),
            fcf_mm=round(fcf, 2),
            debt_balance_mm=round(debt, 2),
            leverage_ratio=round(lev, 2),
        ))
    return projs


def _build_returns(
    equity_mm: float,
    projections: List[YearProjection],
    exit_multiple: float,
) -> List[ReturnSummary]:
    scenarios = []
    for hold in range(3, 8):
        if hold > len(projections):
            break
        p = projections[hold - 1]
        exit_ev = p.ebitda_mm * exit_multiple
        debt_at_exit = p.debt_balance_mm
        exit_equity = exit_ev - debt_at_exit
        cum_fcf = sum(projections[i].fcf_mm for i in range(hold))
        total_proceeds = exit_equity + cum_fcf
        moic = round(total_proceeds / equity_mm, 2) if equity_mm > 0 else 0.0
        irr = _calc_irr(moic, float(hold))
        cash_yield = round(cum_fcf / equity_mm * 100, 1) if equity_mm > 0 else 0.0
        scenarios.append(ReturnSummary(
            hold_years=hold,
            exit_multiple=exit_multiple,
            exit_ev_mm=round(exit_ev, 1),
            exit_equity_mm=round(exit_equity, 1),
            moic=moic,
            irr=irr,
            cash_yield_pct=cash_yield,
        ))
    return scenarios


def _sensitivity(
    equity_mm: float,
    projections: List[YearProjection],
    exit_multiples: List[float],
    hold_years_range: List[int],
) -> List[Dict]:
    rows = []
    for em in exit_multiples:
        row: Dict = {"exit_multiple": em}
        for hold in hold_years_range:
            if hold > len(projections):
                row[f"hold_{hold}"] = None
                continue
            p = projections[hold - 1]
            exit_ev = p.ebitda_mm * em
            exit_eq = exit_ev - p.debt_balance_mm
            cum_fcf = sum(projections[i].fcf_mm for i in range(hold))
            total_proc = exit_eq + cum_fcf
            moic = round(total_proc / equity_mm, 2) if equity_mm > 0 else 0.0
            row[f"hold_{hold}"] = moic
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_underwriting_model(
    sector: str,
    ev_mm: float,
    ebitda_mm: float,
    revenue_mm: Optional[float] = None,
    ebitda_margin: Optional[float] = None,
    rev_growth_pct: float = 8.0,
    margin_expansion_pp: float = 2.0,
    entry_multiple: Optional[float] = None,
    exit_multiple: Optional[float] = None,
) -> UnderwritingResult:
    corpus = _load_corpus()

    if entry_multiple is None:
        entry_multiple = ev_mm / ebitda_mm if ebitda_mm else 10.0
    if ebitda_margin is None:
        ebitda_margin = 0.20
    if revenue_mm is None:
        revenue_mm = ebitda_mm / ebitda_margin if ebitda_margin > 0 else ebitda_mm * 5
    if exit_multiple is None:
        exit_multiple = entry_multiple + 1.0

    sbucket = _size_bucket(ev_mm)
    fin = _FINANCING[sbucket]

    # Sources & Uses
    total_debt = ebitda_mm * fin["total_leverage"]
    senior_debt = ebitda_mm * fin["senior_leverage"]
    sub_debt = total_debt - senior_debt
    equity = ev_mm * fin["equity_pct"]
    # Adjust: sources = uses = EV + fees
    fees = ev_mm * 0.02
    txn_costs = ev_mm * 0.01
    total_uses = ev_mm + fees + txn_costs
    actual_equity = total_uses - total_debt

    sources = LboSources(
        senior_debt_mm=round(senior_debt, 2),
        sub_debt_mm=round(sub_debt, 2),
        equity_mm=round(actual_equity, 2),
        total_mm=round(total_uses, 2),
        leverage_ratio=round(total_debt / ebitda_mm, 2),
        equity_pct=round(actual_equity / total_uses, 3),
    )
    uses = LboUses(
        purchase_price_mm=round(ev_mm, 2),
        financing_fees_mm=round(fees, 2),
        transaction_costs_mm=round(txn_costs, 2),
        total_mm=round(total_uses, 2),
    )

    projections = _build_projections(
        entry_ebitda_mm=ebitda_mm,
        revenue_mm=revenue_mm,
        ebitda_margin=ebitda_margin,
        debt_mm=total_debt,
        cash_interest_rate=fin["cash_interest"],
        amort_pct=fin["amort_pct"],
        rev_growth_pct=rev_growth_pct / 100,
        margin_expansion_pp=margin_expansion_pp / 100,
    )

    return_scenarios = _build_returns(actual_equity, projections, exit_multiple)

    sensitivity = _sensitivity(
        actual_equity, projections,
        exit_multiples=[entry_multiple - 1, entry_multiple, entry_multiple + 1,
                        entry_multiple + 2, entry_multiple + 3],
        hold_years_range=[3, 4, 5, 6, 7],
    )

    # Corpus benchmarks
    sector_deals = [d for d in corpus if
                    sector.lower()[:6] in (d.get("sector") or "").lower() or
                    (d.get("sector") or "").lower()[:6] in sector.lower()]
    if len(sector_deals) < 5:
        sector_deals = corpus
    moics = sorted(d.get("moic", 2.5) for d in sector_deals)
    n = len(moics)
    p25 = moics[n // 4] if n >= 4 else 2.5
    p50 = moics[n // 2] if n else 3.0
    p75 = moics[int(n * 0.75)] if n >= 4 else 3.8

    return UnderwritingResult(
        sector=sector,
        ev_mm=round(ev_mm, 2),
        ebitda_mm=round(ebitda_mm, 2),
        entry_multiple=round(entry_multiple, 1),
        size_bucket=sbucket,
        sources=sources,
        uses=uses,
        projections=projections,
        return_scenarios=return_scenarios,
        sensitivity_table=sensitivity,
        corpus_p50_moic=round(p50, 2),
        corpus_p25_moic=round(p25, 2),
        corpus_p75_moic=round(p75, 2),
        corpus_deal_count=len(corpus),
    )
