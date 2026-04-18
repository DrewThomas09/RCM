"""Capital Call & Distribution Schedule Simulator.

Simulates fund-level cash flows over the fund lifecycle:
- Capital commitments from LPs
- Investment period: calls timing, pacing
- Harvest period: distributions timing, magnitude
- J-curve: cumulative NAV vs paid-in capital
- DPI / TVPI / RVPI trajectory
- GP carry waterfall timing
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class QuarterRow:
    year: int
    quarter: int
    period_label: str
    call_mm: float
    distribution_mm: float
    nav_mm: float
    cumulative_called_mm: float
    cumulative_distributed_mm: float
    dpi: float
    tvpi: float
    rvpi: float
    net_cash_flow_mm: float


@dataclass
class LPClass:
    name: str
    commitment_mm: float
    pct_of_fund: float
    hurdle_rate: float
    mgmt_fee: float


@dataclass
class WaterfallTier:
    tier: str                       # "Return of Capital", "Preferred Return", "GP Catch-up", "80/20 Split"
    threshold: str
    lp_share: float
    gp_share: float
    est_timing_year: float
    est_amount_mm: float


@dataclass
class CapitalScheduleResult:
    fund_size_mm: float
    investment_period_years: int
    hold_period_years: int
    total_years: int
    quarters: List[QuarterRow]
    lp_classes: List[LPClass]
    waterfall_tiers: List[WaterfallTier]
    peak_nav_mm: float
    peak_nav_year: int
    trough_jcurve_mm: float
    trough_jcurve_year: float
    final_dpi: float
    final_tvpi: float
    gross_moic: float
    net_moic: float
    gross_irr: float
    net_irr: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 67):
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


def _build_call_pattern(investment_years: int) -> List[float]:
    """Typical PE call pattern: heavy Y1-3, taper Y4-5. Returns quarterly pct of commitments."""
    total_q = investment_years * 4
    # Typical: 20% Y1, 25% Y2, 25% Y3, 20% Y4, 10% Y5
    yearly = [0.20, 0.25, 0.25, 0.20, 0.10][:investment_years]
    # Pad if needed
    while len(yearly) < investment_years:
        yearly.append(0.05)
    # Renormalize
    total = sum(yearly)
    yearly = [y / total for y in yearly]

    quarterly = []
    for y_pct in yearly:
        # Spread quarterly, front-loaded within year
        q_split = [0.35, 0.28, 0.22, 0.15]
        for q in q_split:
            quarterly.append(y_pct * q)
    return quarterly


def _build_distribution_pattern(total_years: int, investment_years: int) -> List[float]:
    """Typical distribution pattern: minimal Y1-3, accelerate Y4-8, taper Y9-10. Returns quarterly."""
    total_q = total_years * 4
    dist = [0.0] * total_q

    # Year 2-3: nominal (2-4%)
    for q in range(4, 12):
        dist[q] = 0.008

    # Year 4-5: accelerating (20%/year)
    for q in range(12, 20):
        dist[q] = 0.05

    # Year 6-8: peak (30%/year)
    for q in range(20, 32):
        dist[q] = 0.075

    # Year 9-10: taper
    for q in range(32, min(40, total_q)):
        dist[q] = 0.04

    # Normalize to 2.8x total paid-in (typical TVPI)
    total_dist = sum(dist)
    if total_dist > 0:
        dist = [d / total_dist * 2.4 for d in dist]

    return dist[:total_q]


def _build_quarters(
    fund_size_mm: float, investment_years: int, total_years: int,
) -> List[QuarterRow]:
    call_pattern = _build_call_pattern(investment_years)
    dist_pattern = _build_distribution_pattern(total_years, investment_years)

    rows = []
    cum_called = 0.0
    cum_dist = 0.0
    current_nav = 0.0

    total_q = total_years * 4

    for q in range(total_q):
        year = q // 4 + 1
        quarter = q % 4 + 1
        period = f"Y{year}Q{quarter}"

        # Capital call
        call_pct = call_pattern[q] if q < len(call_pattern) else 0
        call_mm = fund_size_mm * call_pct
        cum_called += call_mm

        # Distribution
        dist_pct = dist_pattern[q] if q < len(dist_pattern) else 0
        dist_mm = cum_called * dist_pct
        cum_dist += dist_mm

        # NAV: invested capital compounds at implied IRR
        # During invest period, NAV grows as calls come in + appreciation
        # During harvest, NAV decreases as distributions exceed appreciation
        if q < investment_years * 4:
            # Build phase: new calls add to NAV, modest appreciation
            current_nav += call_mm * 1.03 - dist_mm
        else:
            # Harvest: appreciation on remaining NAV, less distributions
            current_nav = current_nav * 1.025 - dist_mm
            current_nav = max(0, current_nav)

        dpi = cum_dist / cum_called if cum_called else 0
        rvpi = current_nav / cum_called if cum_called else 0
        tvpi = dpi + rvpi
        net_cf = dist_mm - call_mm

        rows.append(QuarterRow(
            year=year,
            quarter=quarter,
            period_label=period,
            call_mm=round(call_mm, 2),
            distribution_mm=round(dist_mm, 2),
            nav_mm=round(current_nav, 2),
            cumulative_called_mm=round(cum_called, 2),
            cumulative_distributed_mm=round(cum_dist, 2),
            dpi=round(dpi, 3),
            tvpi=round(tvpi, 3),
            rvpi=round(rvpi, 3),
            net_cash_flow_mm=round(net_cf, 2),
        ))
    return rows


def _build_lp_classes(fund_size_mm: float) -> List[LPClass]:
    classes = [
        ("Public Pension (CalPERS-style)", 0.22, 0.08, 0.015),
        ("Sovereign Wealth Fund", 0.18, 0.08, 0.012),
        ("Endowment / Foundation", 0.14, 0.08, 0.018),
        ("Insurance Company", 0.12, 0.08, 0.015),
        ("Fund of Funds", 0.10, 0.08, 0.020),
        ("Family Office / HNW", 0.14, 0.08, 0.020),
        ("GP Commitment", 0.05, 0.08, 0.0),
        ("Other Institutional", 0.05, 0.08, 0.018),
    ]
    return [LPClass(
        name=n, commitment_mm=round(fund_size_mm * pct, 2),
        pct_of_fund=round(pct, 3), hurdle_rate=hurdle, mgmt_fee=mgmt,
    ) for n, pct, hurdle, mgmt in classes]


def _build_waterfall(fund_size_mm: float, total_distributions: float) -> List[WaterfallTier]:
    """European / Fund-level waterfall."""
    tiers = []
    # Tier 1: Return of Paid-in Capital
    roc = min(fund_size_mm, total_distributions)
    tiers.append(WaterfallTier(
        tier="1. Return of Paid-in Capital",
        threshold="Up to 100% of capital returned",
        lp_share=1.00, gp_share=0.00,
        est_timing_year=5.5,
        est_amount_mm=round(roc, 1),
    ))

    # Tier 2: Preferred Return (8%)
    remaining = total_distributions - roc
    preferred = fund_size_mm * 0.08 * 5    # Approximate 8% hurdle over 5 years
    pref_paid = min(remaining, preferred)
    tiers.append(WaterfallTier(
        tier="2. LP Preferred Return (8%)",
        threshold="Up to 8% IRR hurdle",
        lp_share=1.00, gp_share=0.00,
        est_timing_year=7.0,
        est_amount_mm=round(pref_paid, 1),
    ))

    # Tier 3: GP Catch-up
    remaining = remaining - pref_paid
    catchup = preferred * 0.25    # 25% of preferred
    catchup_paid = min(remaining, catchup)
    tiers.append(WaterfallTier(
        tier="3. GP Catch-up (50/50)",
        threshold="Until GP gets 20% of profits",
        lp_share=0.50, gp_share=0.50,
        est_timing_year=7.2,
        est_amount_mm=round(catchup_paid, 1),
    ))

    # Tier 4: 80/20 Split
    final_split = max(0, remaining - catchup_paid)
    tiers.append(WaterfallTier(
        tier="4. 80/20 Carry Split",
        threshold="All remaining distributions",
        lp_share=0.80, gp_share=0.20,
        est_timing_year=8.5,
        est_amount_mm=round(final_split, 1),
    ))

    return tiers


def _compute_irr(cash_flows: List[float], years: List[float]) -> float:
    """Simple IRR approximation via bisection."""
    if not cash_flows:
        return 0
    # Initial bounds
    lo, hi = -0.5, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        npv = sum(cf / ((1 + mid) ** y) for cf, y in zip(cash_flows, years))
        if abs(npv) < 0.01:
            return mid
        # Adjust
        npv_hi = sum(cf / ((1 + hi) ** y) for cf, y in zip(cash_flows, years))
        if npv * npv_hi < 0:
            lo = mid
        else:
            hi = mid
    return mid


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_capital_schedule(
    fund_size_mm: float = 500.0,
    investment_years: int = 5,
    total_years: int = 10,
) -> CapitalScheduleResult:
    corpus = _load_corpus()

    quarters = _build_quarters(fund_size_mm, investment_years, total_years)
    lp_classes = _build_lp_classes(fund_size_mm)

    total_dist = quarters[-1].cumulative_distributed_mm if quarters else 0
    total_called = quarters[-1].cumulative_called_mm if quarters else 0
    waterfall = _build_waterfall(fund_size_mm, total_dist)

    # Peak NAV
    peak_nav = max(quarters, key=lambda q: q.nav_mm) if quarters else None
    peak_nav_mm = peak_nav.nav_mm if peak_nav else 0
    peak_year = peak_nav.year if peak_nav else 0

    # J-curve trough (cumulative net cash flow)
    cum_cf = 0
    trough = 0
    trough_yr = 0
    for q in quarters:
        cum_cf += q.net_cash_flow_mm
        if cum_cf < trough:
            trough = cum_cf
            trough_yr = q.year + (q.quarter - 1) / 4

    # Returns
    final = quarters[-1] if quarters else None
    final_dpi = final.dpi if final else 0
    final_tvpi = final.tvpi if final else 0
    gross_moic = final_tvpi
    net_moic = gross_moic * 0.82    # Net of fees and carry

    # IRR approximation from aggregate cash flows
    cash_flows = []
    years = []
    for q in quarters:
        cf = q.distribution_mm - q.call_mm
        cash_flows.append(cf)
        years.append((q.year - 1) + (q.quarter - 1) / 4)
    # Add terminal NAV
    if final and final.nav_mm > 0:
        cash_flows.append(final.nav_mm)
        years.append(total_years)

    gross_irr = _compute_irr(cash_flows, years)
    net_irr = gross_irr * 0.78

    return CapitalScheduleResult(
        fund_size_mm=round(fund_size_mm, 1),
        investment_period_years=investment_years,
        hold_period_years=total_years,
        total_years=total_years,
        quarters=quarters,
        lp_classes=lp_classes,
        waterfall_tiers=waterfall,
        peak_nav_mm=round(peak_nav_mm, 1),
        peak_nav_year=peak_year,
        trough_jcurve_mm=round(trough, 1),
        trough_jcurve_year=round(trough_yr, 1),
        final_dpi=round(final_dpi, 2),
        final_tvpi=round(final_tvpi, 2),
        gross_moic=round(gross_moic, 2),
        net_moic=round(net_moic, 2),
        gross_irr=round(gross_irr, 4),
        net_irr=round(net_irr, 4),
        corpus_deal_count=len(corpus),
    )
