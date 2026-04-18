"""De Novo Expansion Tracker.

Models greenfield buildout economics for PE-backed platform roll-ups —
a critical alternative to M&A as multiples compress. Tracks:
- Per-site capex and ramp curve
- Break-even timing by site type
- Geographic expansion queue
- Payback / NPV per site
- Organic vs inorganic blend
- Lease vs buy decisions
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class SiteType:
    site_type: str
    buildout_capex_mm: float
    working_cap_mm: float
    total_investment_mm: float
    stabilized_ebitda_mm: float
    ramp_months: int
    payback_years: float
    y1_revenue_mm: float
    y3_revenue_mm: float


@dataclass
class MarketExpansion:
    market: str
    region: str
    population_000: int
    competitor_count: int
    demand_score: int
    target_sites: int
    total_investment_mm: float
    expected_ebitda_mm: float


@dataclass
class RampCurve:
    month: int
    visits_per_day: int
    revenue_mm: float
    expense_mm: float
    ebitda_mm: float
    cumulative_fcf_mm: float


@dataclass
class LeaseVsBuy:
    scenario: str
    upfront_cash_mm: float
    annual_cost_mm: float
    tenure_years: int
    npv_10yr_mm: float
    flexibility_score: int
    ownership_exit_value_mm: float


@dataclass
class OrgInorgBlend:
    category: str
    deals_count: int
    total_investment_mm: float
    ebitda_added_mm: float
    avg_multiple: float
    payback_years: float


@dataclass
class DeNovoResult:
    total_active_sites: int
    total_sites_planned: int
    total_investment_committed_mm: float
    expected_stabilized_ebitda_mm: float
    portfolio_payback_years: float
    site_types: List[SiteType]
    markets: List[MarketExpansion]
    ramp: List[RampCurve]
    lease_buy: List[LeaseVsBuy]
    blend: List[OrgInorgBlend]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 101):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_site_types() -> List[SiteType]:
    items = [
        ("Ambulatory Surgery Center (single-OR)", 4.2, 1.5, 5.7, 1.8, 18, 3.17, 2.5, 6.8),
        ("Ambulatory Surgery Center (multi-OR)", 8.5, 2.8, 11.3, 4.2, 24, 2.69, 4.8, 14.5),
        ("Urgent Care Clinic", 1.2, 0.4, 1.6, 0.55, 12, 2.91, 1.4, 3.5),
        ("Primary Care Clinic (de novo)", 0.85, 0.3, 1.15, 0.38, 18, 3.03, 0.9, 2.4),
        ("Dental Office (de novo)", 1.4, 0.5, 1.9, 0.62, 18, 3.06, 1.2, 3.2),
        ("Dermatology Office", 1.1, 0.4, 1.5, 0.48, 15, 3.13, 1.1, 2.8),
        ("Physical Therapy Clinic", 0.35, 0.15, 0.5, 0.22, 9, 2.27, 0.7, 1.5),
        ("Infusion Suite (attached)", 1.8, 0.6, 2.4, 0.95, 12, 2.53, 2.0, 4.8),
        ("Behavioral Health Office", 0.55, 0.2, 0.75, 0.28, 12, 2.68, 0.85, 1.9),
        ("Fertility Clinic (de novo)", 3.8, 1.2, 5.0, 1.85, 24, 2.70, 3.2, 8.5),
    ]
    rows = []
    for st, capex, wc, total_inv, stab_ebit, ramp, pb, y1r, y3r in items:
        rows.append(SiteType(
            site_type=st, buildout_capex_mm=capex, working_cap_mm=wc,
            total_investment_mm=total_inv, stabilized_ebitda_mm=stab_ebit,
            ramp_months=ramp, payback_years=pb,
            y1_revenue_mm=y1r, y3_revenue_mm=y3r,
        ))
    return rows


def _build_markets() -> List[MarketExpansion]:
    return [
        MarketExpansion("Austin-Round Rock, TX", "Southwest", 2450, 4, 88, 6, 42.5, 14.2),
        MarketExpansion("Phoenix-Mesa, AZ", "West", 5050, 8, 82, 8, 58.5, 18.5),
        MarketExpansion("Nashville, TN", "Southeast", 2100, 5, 85, 5, 35.2, 11.8),
        MarketExpansion("Raleigh-Durham, NC", "Southeast", 2000, 6, 80, 4, 28.5, 9.5),
        MarketExpansion("Tampa-St Pete, FL", "Southeast", 3300, 9, 78, 7, 48.5, 16.2),
        MarketExpansion("Denver-Aurora, CO", "West", 2950, 7, 82, 6, 42.5, 14.8),
        MarketExpansion("Charlotte, NC", "Southeast", 2700, 6, 79, 5, 34.5, 11.5),
        MarketExpansion("Minneapolis-St Paul, MN", "Midwest", 3700, 10, 72, 4, 28.5, 9.2),
        MarketExpansion("Salt Lake City, UT", "West", 1300, 4, 84, 5, 32.5, 10.8),
        MarketExpansion("Columbus, OH", "Midwest", 2150, 7, 75, 4, 26.5, 8.8),
        MarketExpansion("Jacksonville, FL", "Southeast", 1650, 5, 81, 4, 28.0, 9.2),
        MarketExpansion("Las Vegas, NV", "West", 2350, 8, 76, 5, 34.5, 11.2),
    ]


def _build_ramp() -> List[RampCurve]:
    # 24-month ramp for representative ASC
    monthly_visits_ramp = [8, 15, 22, 32, 42, 55, 68, 80, 92, 102, 112, 118,
                           125, 132, 138, 144, 150, 155, 160, 162, 164, 165, 165, 165]
    rows = []
    cum_fcf = -11.3  # initial investment (capex + wc)
    for i, vpd in enumerate(monthly_visits_ramp):
        month = i + 1
        rev = vpd * 22 * 385 / 1000000
        exp = rev * (0.78 if i < 6 else 0.68 if i < 12 else 0.62)
        ebit = rev - exp
        cum_fcf += ebit - 0.05
        rows.append(RampCurve(
            month=month, visits_per_day=vpd,
            revenue_mm=round(rev, 3),
            expense_mm=round(exp, 3),
            ebitda_mm=round(ebit, 3),
            cumulative_fcf_mm=round(cum_fcf, 3),
        ))
    return rows


def _build_lease_buy() -> List[LeaseVsBuy]:
    return [
        LeaseVsBuy("Lease (market rate, 10-year)", 0.45, 0.48, 10, -3.65, 85, 0.0),
        LeaseVsBuy("Lease-to-Own", 1.85, 0.28, 15, -1.85, 72, 3.85),
        LeaseVsBuy("Own (cash purchase)", 8.5, 0.12, 99, 5.85, 45, 9.8),
        LeaseVsBuy("Own (debt-financed 70%)", 2.55, 0.52, 99, 4.12, 52, 9.8),
        LeaseVsBuy("Sale-Leaseback (post-buildout)", -8.5, 0.52, 20, -0.85, 78, 0.0),
    ]


def _build_blend() -> List[OrgInorgBlend]:
    return [
        OrgInorgBlend("Platform Acquisition (Y0)", 1, 285.0, 22.0, 12.95, 4.8),
        OrgInorgBlend("Bolt-On M&A (Y1-Y5)", 14, 185.0, 22.0, 8.41, 4.2),
        OrgInorgBlend("De Novo ASCs (Y1-Y5)", 8, 68.2, 26.4, 2.58, 2.7),
        OrgInorgBlend("De Novo UC / PC Clinics", 12, 17.8, 8.4, 2.12, 2.9),
        OrgInorgBlend("Tuck-In Providers", 18, 14.5, 4.2, 3.45, 4.5),
    ]


def compute_denovo_expansion() -> DeNovoResult:
    corpus = _load_corpus()

    site_types = _build_site_types()
    markets = _build_markets()
    ramp = _build_ramp()
    lease_buy = _build_lease_buy()
    blend = _build_blend()

    total_active = sum(m.target_sites for m in markets[:5])
    total_planned = sum(m.target_sites for m in markets)
    total_inv = sum(m.total_investment_mm for m in markets)
    total_ebit = sum(m.expected_ebitda_mm for m in markets)
    payback = total_inv / total_ebit if total_ebit else 0

    return DeNovoResult(
        total_active_sites=total_active,
        total_sites_planned=total_planned,
        total_investment_committed_mm=round(total_inv, 2),
        expected_stabilized_ebitda_mm=round(total_ebit, 2),
        portfolio_payback_years=round(payback, 2),
        site_types=site_types,
        markets=markets,
        ramp=ramp,
        lease_buy=lease_buy,
        blend=blend,
        corpus_deal_count=len(corpus),
    )
