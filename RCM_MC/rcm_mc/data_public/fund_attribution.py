"""Fund Performance Attribution — IRR decomposition for LP reporting.

Decomposes fund-level IRR into:
- Operational improvements (EBITDA growth)
- Multiple expansion (entry-to-exit multiple delta)
- Leverage effect (debt paydown + interest coverage)
- Market timing (vintage year effect)
- Bolt-on accretion (multiple arbitrage on roll-ups)

Partner and LP-facing — answers "where did the returns come from?"
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AttributionComponent:
    component: str
    contribution_moic_x: float
    contribution_irr_pct: float
    pct_of_total_return: float
    notes: str


@dataclass
class DealAttribution:
    company: str
    sector: str
    vintage: int
    hold_years: float
    entry_ev_mm: float
    exit_ev_mm: float
    ebitda_growth_pct: float
    multiple_expansion_x: float
    leverage_contribution_x: float
    total_moic: float
    total_irr: float


@dataclass
class VintageEffect:
    vintage_year: int
    deal_count: int
    median_moic: float
    median_irr: float
    market_env: str                 # "expansion", "peak", "recession", "recovery"


@dataclass
class FundAttributionResult:
    fund_moic: float
    fund_irr: float
    components: List[AttributionComponent]
    deal_attributions: List[DealAttribution]
    vintage_effects: List[VintageEffect]
    best_performer: Optional[dict]
    worst_performer: Optional[dict]
    avg_ebitda_growth_pct: float
    avg_multiple_expansion_x: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 63):
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


def _median(values: List[float]) -> float:
    if not values:
        return 0
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _irr(moic: float, hold: float) -> float:
    if hold <= 0 or moic <= 0:
        return 0
    return (moic ** (1.0 / hold)) - 1.0


def _vintage_env(year: int) -> str:
    env_map = {
        2012: "recovery", 2013: "expansion", 2014: "expansion", 2015: "expansion",
        2016: "expansion", 2017: "expansion", 2018: "peak", 2019: "peak",
        2020: "recession", 2021: "expansion", 2022: "peak", 2023: "recession", 2024: "recovery",
    }
    return env_map.get(year, "expansion")


def _decompose_deal(d: dict) -> DealAttribution:
    """Decompose a single deal's return."""
    ev = d.get("ev_mm") or 100.0
    moic = d.get("moic") or 2.0
    hold = d.get("hold_years") or 3.0
    ev_ebitda = d.get("ev_ebitda") or 10.0
    entry_ebitda = ev / ev_ebitda if ev_ebitda else 0

    # Simple decomposition: assume 2x exit multiple minimum for growth cases
    # Estimate exit multiple vs entry — assume 15% median multiple expansion
    exit_mult = ev_ebitda * 1.15 if moic > 2.0 else ev_ebitda * 0.95
    # Exit EBITDA implied by MOIC and exit multiple
    exit_ev = ev * moic * 0.95    # net debt paydown residual
    exit_ebitda = exit_ev / exit_mult if exit_mult else entry_ebitda
    ebitda_growth_pct = (exit_ebitda / entry_ebitda - 1) if entry_ebitda else 0

    # Multiple expansion contribution (on exit EBITDA)
    mult_exp_contrib = (exit_mult - ev_ebitda) * exit_ebitda / (ev * 0.45) if (ev * 0.45) else 0

    # Leverage contribution (debt paydown + amortization, rough)
    leverage_contrib = (moic - 1) * 0.18

    return DealAttribution(
        company=d.get("company_name", "—"),
        sector=d.get("sector", "—"),
        vintage=d.get("year", 2020),
        hold_years=round(hold, 1),
        entry_ev_mm=round(ev, 1),
        exit_ev_mm=round(exit_ev, 1),
        ebitda_growth_pct=round(ebitda_growth_pct, 3),
        multiple_expansion_x=round(mult_exp_contrib, 2),
        leverage_contribution_x=round(leverage_contrib, 2),
        total_moic=round(moic, 2),
        total_irr=round(_irr(moic, hold), 4),
    )


def _build_components(deals: List[dict]) -> List[AttributionComponent]:
    if not deals:
        return []
    attrs = [_decompose_deal(d) for d in deals]

    # Aggregate contributions
    avg_moic = sum(a.total_moic for a in attrs) / len(attrs)
    avg_irr = sum(a.total_irr for a in attrs) / len(attrs)
    avg_growth = sum(a.ebitda_growth_pct for a in attrs) / len(attrs)
    avg_mult_exp = sum(a.multiple_expansion_x for a in attrs) / len(attrs)
    avg_leverage = sum(a.leverage_contribution_x for a in attrs) / len(attrs)

    # Total return over cost = avg_moic - 1
    total_gain = avg_moic - 1

    # Split gain into components
    # Typical healthcare PE: operational 55%, multiple expansion 20%, leverage 25%
    op_contrib = avg_growth * 0.9    # operational leverage in MOIC terms
    mult_contrib = avg_mult_exp
    lev_contrib = avg_leverage
    markets_contrib = total_gain - op_contrib - mult_contrib - lev_contrib
    bolton_contrib = op_contrib * 0.22    # part of operational that's from bolt-ons

    # Normalize remaining to bolton/market
    remaining = total_gain - (op_contrib - bolton_contrib) - mult_contrib - lev_contrib - bolton_contrib
    market_timing = max(0, remaining)

    def _moic_to_irr(m_contrib, hold):
        # Approximate IRR contribution from a MOIC contribution over avg hold
        if m_contrib <= 0:
            return 0
        return (((1 + m_contrib) ** (1 / hold)) - 1) * 100

    avg_hold = sum(a.hold_years for a in attrs) / len(attrs) if attrs else 4.0
    irr_pct = avg_irr * 100

    rows = []
    for name, contrib, notes in [
        ("Operational Improvements (EBITDA growth)",
         op_contrib - bolton_contrib,
         f"Organic EBITDA growth ~{avg_growth * 100:.1f}%; margin expansion"),
        ("Bolt-on Accretion",
         bolton_contrib,
         "Multiple arbitrage + synergies from roll-ups"),
        ("Multiple Expansion",
         mult_contrib,
         f"Exit multiple ~{avg_mult_exp + 11:.1f}x vs entry"),
        ("Leverage Effect (Debt Paydown)",
         lev_contrib,
         "Amortization + EBITDA growth reduces net debt"),
        ("Market Timing / Vintage",
         market_timing,
         "Vintage year, sector cycle tailwinds/headwinds"),
    ]:
        pct_of_total = contrib / total_gain if total_gain > 0 else 0
        rows.append(AttributionComponent(
            component=name,
            contribution_moic_x=round(contrib, 2),
            contribution_irr_pct=round(_moic_to_irr(contrib, avg_hold), 2),
            pct_of_total_return=round(pct_of_total, 3),
            notes=notes,
        ))
    return rows


def _vintage_effects(deals: List[dict]) -> List[VintageEffect]:
    by_year: Dict[int, List[dict]] = {}
    for d in deals:
        yr = d.get("year") or 2020
        by_year.setdefault(yr, []).append(d)

    rows = []
    for yr in sorted(by_year):
        ds = by_year[yr]
        moics = [d.get("moic") or 2.0 for d in ds]
        holds = [d.get("hold_years") or 3.0 for d in ds]
        irrs = [_irr(m, h) for m, h in zip(moics, holds)]
        rows.append(VintageEffect(
            vintage_year=yr,
            deal_count=len(ds),
            median_moic=round(_median(moics), 2),
            median_irr=round(_median(irrs), 4),
            market_env=_vintage_env(yr),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_fund_attribution(
    sector_filter: str = "",
    vintage_from: int = 0,
    vintage_to: int = 9999,
    sample_size: int = 50,
) -> FundAttributionResult:
    all_deals = _load_corpus()

    # Apply filters
    deals = [
        d for d in all_deals
        if (not sector_filter or (d.get("sector") or "").lower() == sector_filter.lower())
        and vintage_from <= (d.get("year") or 2020) <= vintage_to
    ]
    if not deals:
        deals = all_deals[:sample_size]

    # Sort by MOIC for top/bottom extraction; take sample for detail table
    deals_sorted = sorted(deals, key=lambda d: d.get("moic") or 0, reverse=True)
    sample = deals_sorted[:sample_size]

    components = _build_components(deals)
    deal_attrs = [_decompose_deal(d) for d in sample]
    vintage_effects = _vintage_effects(deals)

    moics = [d.get("moic") or 2.0 for d in deals]
    holds = [d.get("hold_years") or 3.0 for d in deals]
    fund_moic = sum(moics) / len(moics) if moics else 0
    irrs = [_irr(m, h) for m, h in zip(moics, holds)]
    fund_irr = sum(irrs) / len(irrs) if irrs else 0

    # Best / worst
    best_d = deals_sorted[0] if deals_sorted else None
    worst_d = deals_sorted[-1] if deals_sorted else None
    best = {
        "company": best_d.get("company_name", "—"),
        "sector": best_d.get("sector", "—"),
        "moic": round(best_d.get("moic") or 0, 2),
        "irr": round(_irr(best_d.get("moic") or 0, best_d.get("hold_years") or 3), 4),
    } if best_d else None
    worst = {
        "company": worst_d.get("company_name", "—"),
        "sector": worst_d.get("sector", "—"),
        "moic": round(worst_d.get("moic") or 0, 2),
        "irr": round(_irr(worst_d.get("moic") or 0, worst_d.get("hold_years") or 3), 4),
    } if worst_d else None

    avg_growth = sum(a.ebitda_growth_pct for a in deal_attrs) / len(deal_attrs) if deal_attrs else 0
    avg_mult = sum(a.multiple_expansion_x for a in deal_attrs) / len(deal_attrs) if deal_attrs else 0

    return FundAttributionResult(
        fund_moic=round(fund_moic, 2),
        fund_irr=round(fund_irr, 4),
        components=components,
        deal_attributions=deal_attrs,
        vintage_effects=vintage_effects,
        best_performer=best,
        worst_performer=worst,
        avg_ebitda_growth_pct=round(avg_growth, 3),
        avg_multiple_expansion_x=round(avg_mult, 2),
        corpus_deal_count=len(all_deals),
    )
