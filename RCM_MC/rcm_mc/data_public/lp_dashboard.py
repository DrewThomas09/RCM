"""LP Portfolio Dashboard — fund-level KPIs and vintage curves for LP reporting.

Aggregates corpus deals into a fund-level summary: deployed capital,
DPI/TVPI/RVPI, vintage J-curve, payer concentration, sector exposure,
and loss rate / home-run rate for LP diligence presentations.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VintageRow:
    year: int
    deal_count: int
    total_ev_mm: float
    total_equity_mm: float
    median_moic: float
    p25_moic: float
    p75_moic: float
    median_irr: float
    realized_count: int
    active_count: int
    loss_count: int
    home_run_count: int      # moic >= 3.0x
    tvpi: float              # total_value / paid_in
    dpi: float               # distributions / paid_in (realized only)


@dataclass
class SectorExposure:
    sector: str
    deal_count: int
    total_ev_mm: float
    pct_of_portfolio: float
    median_moic: float
    median_irr: float
    loss_rate: float
    home_run_rate: float


@dataclass
class PayerBucket:
    label: str           # "High Commercial (>70%)", "Balanced (40-70%)", "High Gov (<40%)"
    deal_count: int
    median_moic: float
    median_irr: float
    avg_ev_mm: float
    pct_of_portfolio: float


@dataclass
class FundKPIs:
    total_deals: int
    realized_deals: int
    active_deals: int
    total_ev_deployed_mm: float
    total_equity_deployed_mm: float
    gross_moic: float          # portfolio-level
    net_moic: float            # after 20% carry, 1.5% fees
    tvpi: float
    dpi: float
    rvpi: float
    irr_gross: float
    irr_net: float
    loss_rate: float           # moic < 1.0
    home_run_rate: float       # moic >= 3.0
    avg_hold_years: float
    median_ev_mm: float
    pct_commercial_payer: float


@dataclass
class LPDashboardResult:
    fund_kpis: FundKPIs
    vintage_rows: List[VintageRow]
    sector_exposures: List[SectorExposure]
    payer_buckets: List[PayerBucket]
    top_performers: List[dict]
    bottom_performers: List[dict]
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Corpus loader
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pct(lst: List[float]) -> float:
    return sum(lst) / len(lst) if lst else 0.0


def _median(lst: List[float]) -> float:
    if not lst:
        return 0.0
    s = sorted(lst)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _percentile(lst: List[float], p: float) -> float:
    if not lst:
        return 0.0
    s = sorted(lst)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def _irr(moic: float, hold: float) -> float:
    if hold <= 0 or moic <= 0:
        return 0.0
    return (moic ** (1.0 / hold)) - 1.0


def _equity(d: dict) -> float:
    ev = d.get("ev_mm") or 0.0
    em = d.get("ev_ebitda") or 10.0
    return ev * 0.45


def _comm_pct(d: dict) -> float:
    c = d.get("comm_pct")
    if c is not None and isinstance(c, (int, float)):
        return float(c)
    pm = d.get("payer_mix")
    if isinstance(pm, dict):
        return float(pm.get("commercial", 0.0) or 0.0)
    return 0.45


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _build_fund_kpis(deals: List[dict]) -> FundKPIs:
    if not deals:
        return FundKPIs(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    evs = [d.get("ev_mm") or 100.0 for d in deals]
    equities = [_equity(d) for d in deals]
    moics = [d.get("moic") or 2.0 for d in deals]
    holds = [d.get("hold_years") or 3.0 for d in deals]
    irrs = [_irr(m, h) for m, h in zip(moics, holds)]

    total_equity = sum(equities)
    total_ev = sum(evs)

    # TVPI = total current value / paid-in
    current_values = [eq * moic for eq, moic in zip(equities, moics)]
    total_current = sum(current_values)
    tvpi = total_current / total_equity if total_equity else 0.0

    # DPI = realized distributions / paid-in (treat "Realized" deals)
    realized = [d for d in deals if d.get("status") == "Realized"]
    active = [d for d in deals if d.get("status") != "Realized"]
    realized_eq = sum(_equity(d) for d in realized)
    realized_val = sum(_equity(d) * (d.get("moic") or 2.0) for d in realized)
    dpi = realized_val / total_equity if total_equity else 0.0
    rvpi = tvpi - dpi

    gross_moic = total_current / total_equity if total_equity else 0.0
    # Net: 20% carry on gains above cost, 1.5% annual fee drag
    gains = max(0.0, total_current - total_equity)
    carry = gains * 0.20
    avg_hold = _pct(holds)
    fee_drag = total_equity * 0.015 * avg_hold
    net_value = total_current - carry - fee_drag
    net_moic = net_value / total_equity if total_equity else 0.0

    gross_irr = _irr(gross_moic, avg_hold)
    net_irr = _irr(net_moic, avg_hold)

    losses = sum(1 for m in moics if m < 1.0)
    home_runs = sum(1 for m in moics if m >= 3.0)
    comm_pcts = [_comm_pct(d) for d in deals]

    return FundKPIs(
        total_deals=len(deals),
        realized_deals=len(realized),
        active_deals=len(active),
        total_ev_deployed_mm=round(total_ev, 1),
        total_equity_deployed_mm=round(total_equity, 1),
        gross_moic=round(gross_moic, 2),
        net_moic=round(net_moic, 2),
        tvpi=round(tvpi, 2),
        dpi=round(dpi, 2),
        rvpi=round(rvpi, 2),
        irr_gross=round(gross_irr, 4),
        irr_net=round(net_irr, 4),
        loss_rate=round(losses / len(deals), 3),
        home_run_rate=round(home_runs / len(deals), 3),
        avg_hold_years=round(avg_hold, 1),
        median_ev_mm=round(_median(evs), 1),
        pct_commercial_payer=round(_pct(comm_pcts), 3),
    )


def _build_vintage_rows(deals: List[dict]) -> List[VintageRow]:
    by_year: Dict[int, List[dict]] = {}
    for d in deals:
        yr = d.get("year") or 2020
        by_year.setdefault(yr, []).append(d)

    rows = []
    for yr in sorted(by_year):
        ds = by_year[yr]
        evs = [d.get("ev_mm") or 100.0 for d in ds]
        equities = [_equity(d) for d in ds]
        moics = [d.get("moic") or 2.0 for d in ds]
        holds = [d.get("hold_years") or 3.0 for d in ds]
        irrs = [_irr(m, h) for m, h in zip(moics, holds)]
        total_equity = sum(equities)
        total_current = sum(eq * m for eq, m in zip(equities, moics))
        realized_ds = [d for d in ds if d.get("status") == "Realized"]
        realized_val = sum(_equity(d) * (d.get("moic") or 2.0) for d in realized_ds)
        dpi = realized_val / total_equity if total_equity else 0.0
        tvpi = total_current / total_equity if total_equity else 0.0

        rows.append(VintageRow(
            year=yr,
            deal_count=len(ds),
            total_ev_mm=round(sum(evs), 1),
            total_equity_mm=round(total_equity, 1),
            median_moic=round(_median(moics), 2),
            p25_moic=round(_percentile(moics, 25), 2),
            p75_moic=round(_percentile(moics, 75), 2),
            median_irr=round(_median(irrs), 4),
            realized_count=len([d for d in ds if d.get("status") == "Realized"]),
            active_count=len([d for d in ds if d.get("status") != "Realized"]),
            loss_count=sum(1 for m in moics if m < 1.0),
            home_run_count=sum(1 for m in moics if m >= 3.0),
            tvpi=round(tvpi, 2),
            dpi=round(dpi, 2),
        ))
    return rows


def _build_sector_exposures(deals: List[dict], total_ev: float) -> List[SectorExposure]:
    by_sector: Dict[str, List[dict]] = {}
    for d in deals:
        s = d.get("sector") or "Other"
        by_sector.setdefault(s, []).append(d)

    rows = []
    for sector, ds in sorted(by_sector.items(), key=lambda x: -len(x[1])):
        evs = [d.get("ev_mm") or 100.0 for d in ds]
        moics = [d.get("moic") or 2.0 for d in ds]
        holds = [d.get("hold_years") or 3.0 for d in ds]
        irrs = [_irr(m, h) for m, h in zip(moics, holds)]
        losses = sum(1 for m in moics if m < 1.0)
        home_runs = sum(1 for m in moics if m >= 3.0)
        rows.append(SectorExposure(
            sector=sector,
            deal_count=len(ds),
            total_ev_mm=round(sum(evs), 1),
            pct_of_portfolio=round(sum(evs) / total_ev if total_ev else 0, 3),
            median_moic=round(_median(moics), 2),
            median_irr=round(_median(irrs), 4),
            loss_rate=round(losses / len(ds), 3),
            home_run_rate=round(home_runs / len(ds), 3),
        ))
    return rows[:20]  # top 20 sectors


def _build_payer_buckets(deals: List[dict], total_ev: float) -> List[PayerBucket]:
    buckets: Dict[str, List[dict]] = {
        "High Commercial (>70%)": [],
        "Balanced (40–70%)": [],
        "High Gov (<40%)": [],
    }
    for d in deals:
        cp = _comm_pct(d)
        if cp >= 0.70:
            buckets["High Commercial (>70%)"].append(d)
        elif cp >= 0.40:
            buckets["Balanced (40–70%)"].append(d)
        else:
            buckets["High Gov (<40%)"].append(d)

    rows = []
    for label, ds in buckets.items():
        if not ds:
            continue
        evs = [d.get("ev_mm") or 100.0 for d in ds]
        moics = [d.get("moic") or 2.0 for d in ds]
        holds = [d.get("hold_years") or 3.0 for d in ds]
        irrs = [_irr(m, h) for m, h in zip(moics, holds)]
        rows.append(PayerBucket(
            label=label,
            deal_count=len(ds),
            median_moic=round(_median(moics), 2),
            median_irr=round(_median(irrs), 4),
            avg_ev_mm=round(sum(evs) / len(ds), 1),
            pct_of_portfolio=round(sum(evs) / total_ev if total_ev else 0, 3),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_lp_dashboard(
    sector_filter: str = "",
    vintage_from: int = 0,
    vintage_to: int = 9999,
    min_ev_mm: float = 0.0,
) -> LPDashboardResult:
    all_deals = _load_corpus()

    # Apply filters
    deals = [
        d for d in all_deals
        if (not sector_filter or (d.get("sector") or "").lower() == sector_filter.lower())
        and vintage_from <= (d.get("year") or 2020) <= vintage_to
        and (d.get("ev_mm") or 0.0) >= min_ev_mm
    ]
    if not deals:
        deals = all_deals[:50]

    total_ev = sum(d.get("ev_mm") or 100.0 for d in deals)
    fund_kpis = _build_fund_kpis(deals)
    vintage_rows = _build_vintage_rows(deals)
    sector_exposures = _build_sector_exposures(deals, total_ev)
    payer_buckets = _build_payer_buckets(deals, total_ev)

    # Top/bottom performers by MOIC
    sortable = sorted(
        [d for d in deals if d.get("moic") and d.get("company_name")],
        key=lambda x: x.get("moic", 0.0),
        reverse=True,
    )
    top_performers = [
        {
            "company": d.get("company_name", "—"),
            "sector": d.get("sector", "—"),
            "ev_mm": round(d.get("ev_mm") or 0.0, 1),
            "moic": round(d.get("moic") or 0.0, 2),
            "irr": round(_irr(d.get("moic") or 0.0, d.get("hold_years") or 3.0), 4),
            "hold_years": round(d.get("hold_years") or 0.0, 1),
            "year": d.get("year", 2020),
        }
        for d in sortable[:10]
    ]
    bottom_performers = [
        {
            "company": d.get("company_name", "—"),
            "sector": d.get("sector", "—"),
            "ev_mm": round(d.get("ev_mm") or 0.0, 1),
            "moic": round(d.get("moic") or 0.0, 2),
            "irr": round(_irr(d.get("moic") or 0.0, d.get("hold_years") or 3.0), 4),
            "hold_years": round(d.get("hold_years") or 0.0, 1),
            "year": d.get("year", 2020),
        }
        for d in sortable[-10:][::-1]
    ]

    return LPDashboardResult(
        fund_kpis=fund_kpis,
        vintage_rows=vintage_rows,
        sector_exposures=sector_exposures,
        payer_buckets=payer_buckets,
        top_performers=top_performers,
        bottom_performers=bottom_performers,
        corpus_deal_count=len(all_deals),
    )
