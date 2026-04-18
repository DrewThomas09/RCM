"""Working Capital Analyzer — AR, AP, DSO, cash conversion cycle for healthcare deals.

Core diligence question: How much cash is trapped in working capital?
Models AR days by payer, DSO improvement from RCM initiatives, one-time
cash release from AR cleanup, and ongoing free cash flow yield.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Sector DSO priors from corpus (days)
# ---------------------------------------------------------------------------

_DSO_BY_SECTOR = {
    "Physician Services": 48,
    "Dental": 32,
    "Dermatology": 44,
    "Ophthalmology": 46,
    "Gastroenterology": 52,
    "Orthopedics": 55,
    "ABA Therapy": 58,
    "Behavioral Health": 62,
    "Home Health": 68,
    "Hospice": 55,
    "Pharmacy": 18,
    "Urgent Care": 38,
    "Veterinary": 4,        # mostly self-pay
    "Fertility": 12,        # mostly self-pay
    "Radiology": 58,
    "Anesthesiology": 68,
    "Laboratory": 55,
    "Imaging": 60,
    "Hospital": 52,
    "Surgery Center": 45,
    "DME": 75,
    "Skilled Nursing": 62,
}

_DSO_BY_PAYER = {
    "commercial": 38,
    "medicare": 28,
    "medicaid": 58,
    "self_pay": 95,
    "workers_comp": 72,
    "auto": 88,
}

_DPO_BY_SECTOR = {
    "Pharmacy": 32,
    "DME": 38,
    "Laboratory": 28,
    "default": 35,
}

_INVENTORY_DAYS_BY_SECTOR = {
    "Pharmacy": 22,
    "DME": 38,
    "Laboratory": 12,
    "Imaging": 8,
    "default": 4,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PayerAR:
    payer: str
    pct_of_ar: float
    dso_days: float
    ar_balance_mm: float


@dataclass
class WorkingCapitalBaseline:
    dso_days: float
    dpo_days: float
    inventory_days: float
    ccc_days: float          # cash conversion cycle
    ar_balance_mm: float
    ap_balance_mm: float
    inventory_mm: float
    nwc_mm: float            # net working capital
    nwc_pct_revenue: float   # NWC as % of revenue


@dataclass
class RCMImprovement:
    initiative: str
    dso_reduction_days: float
    cash_release_mm: float    # one-time, from AR cleanup
    ongoing_fcf_impact_mm: float   # annual
    timeline_months: int


@dataclass
class CashBridge:
    year: int
    revenue_mm: float
    ebitda_mm: float
    dso_days: float
    ar_balance_mm: float
    nwc_mm: float
    fcf_mm: float
    cum_cash_released_mm: float


@dataclass
class WorkingCapitalResult:
    sector: str
    revenue_mm: float
    baseline: WorkingCapitalBaseline
    payer_ar: List[PayerAR]
    improvements: List[RCMImprovement]
    cash_bridge: List[CashBridge]
    total_cash_unlock_mm: float
    annual_fcf_uplift_mm: float
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


def _sector_dso(sector: str) -> float:
    return float(_DSO_BY_SECTOR.get(sector, 48))


def _sector_dpo(sector: str) -> float:
    return float(_DPO_BY_SECTOR.get(sector, _DPO_BY_SECTOR["default"]))


def _sector_inv_days(sector: str) -> float:
    return float(_INVENTORY_DAYS_BY_SECTOR.get(sector, _INVENTORY_DAYS_BY_SECTOR["default"]))


def _build_payer_ar(payer_mix: Dict[str, float], ar_balance: float) -> List[PayerAR]:
    # Payer AR mix — weight by payer_mix × payer DSO
    rows = []
    weights = {p: mix * _DSO_BY_PAYER.get(p, 50) for p, mix in payer_mix.items()}
    total_w = sum(weights.values()) or 1.0
    for payer in ["commercial", "medicare", "medicaid", "self_pay"]:
        if payer not in payer_mix:
            continue
        mix = payer_mix[payer]
        if mix <= 0:
            continue
        pct_ar = weights[payer] / total_w
        rows.append(PayerAR(
            payer=payer.replace("_", " ").title(),
            pct_of_ar=round(pct_ar, 3),
            dso_days=float(_DSO_BY_PAYER.get(payer, 50)),
            ar_balance_mm=round(ar_balance * pct_ar, 2),
        ))
    return rows


def _build_baseline(
    sector: str,
    revenue_mm: float,
    dso_override: Optional[float],
    dpo_override: Optional[float],
) -> WorkingCapitalBaseline:
    dso = dso_override if dso_override is not None else _sector_dso(sector)
    dpo = dpo_override if dpo_override is not None else _sector_dpo(sector)
    inv = _sector_inv_days(sector)
    ar_bal = revenue_mm / 365 * dso
    ap_bal = revenue_mm / 365 * dpo * 0.6    # AP on COGS, assume ~60% of revenue
    inv_bal = revenue_mm / 365 * inv * 0.6
    nwc = ar_bal + inv_bal - ap_bal
    nwc_pct = nwc / revenue_mm if revenue_mm else 0.0
    ccc = dso + inv - dpo
    return WorkingCapitalBaseline(
        dso_days=round(dso, 1),
        dpo_days=round(dpo, 1),
        inventory_days=round(inv, 1),
        ccc_days=round(ccc, 1),
        ar_balance_mm=round(ar_bal, 2),
        ap_balance_mm=round(ap_bal, 2),
        inventory_mm=round(inv_bal, 2),
        nwc_mm=round(nwc, 2),
        nwc_pct_revenue=round(nwc_pct, 4),
    )


def _build_improvements(
    baseline_dso: float,
    revenue_mm: float,
    ebitda_mm: float,
) -> List[RCMImprovement]:
    """Standard RCM initiatives with realistic DSO reduction potential."""
    initiatives = [
        ("Denial Mgmt Program", 4.5, 0.012, 6),
        ("Clean Claim Rate ↑", 3.8, 0.008, 4),
        ("Prior Auth Workflow", 2.5, 0.005, 8),
        ("Patient Liability Coll.", 6.2, 0.004, 12),
        ("AR Aging 90+ Cleanup", 5.5, 0.000, 3),   # one-time only
        ("Coding Accuracy ↑", 2.0, 0.006, 6),
        ("Payer Contract Renegot.", 1.5, 0.010, 9),
    ]
    rows = []
    for name, dso_delta, ebitda_pct, months in initiatives:
        # Cash release = (DSO reduction × daily revenue) — one-time
        cash_release = revenue_mm / 365 * dso_delta
        # Ongoing FCF impact: ~ebitda_pct of revenue as margin lift
        ongoing_fcf = revenue_mm * ebitda_pct
        rows.append(RCMImprovement(
            initiative=name,
            dso_reduction_days=round(dso_delta, 1),
            cash_release_mm=round(cash_release, 2),
            ongoing_fcf_impact_mm=round(ongoing_fcf, 2),
            timeline_months=months,
        ))
    return rows


def _build_cash_bridge(
    revenue_mm: float,
    ebitda_mm: float,
    baseline_dso: float,
    dso_target: float,
    improvements: List[RCMImprovement],
    hold_years: int,
    organic_growth_pct: float,
) -> List[CashBridge]:
    rows = []
    total_dso_reduction = baseline_dso - dso_target
    per_year_dso = total_dso_reduction / max(hold_years, 1) * 1.2   # front-loaded
    cum_release = 0.0

    for yr in range(0, hold_years + 1):
        rev = revenue_mm * ((1 + organic_growth_pct) ** yr)
        ebitda_y = ebitda_mm * ((1 + organic_growth_pct) ** yr)
        # Front-load 60% of DSO reduction in years 1-2
        if yr == 0:
            dso = baseline_dso
        elif yr == 1:
            dso = baseline_dso - total_dso_reduction * 0.35
        elif yr == 2:
            dso = baseline_dso - total_dso_reduction * 0.65
        elif yr == 3:
            dso = baseline_dso - total_dso_reduction * 0.85
        else:
            dso = dso_target

        ar = rev / 365 * dso
        ap = rev / 365 * _sector_dpo("") * 0.6
        nwc = ar * 0.85 - ap    # simplified

        # FCF: EBITDA - maintenance capex (2% rev) - tax (25% on EBITDA-I) - ΔNWC
        prev_nwc = rows[-1].nwc_mm if rows else nwc
        delta_nwc = nwc - prev_nwc
        capex = rev * 0.02
        tax = ebitda_y * 0.25
        fcf = ebitda_y - capex - tax - delta_nwc

        if yr > 0 and yr <= 3:
            # Portion of cash release in this year
            cum_release += sum(im.cash_release_mm for im in improvements) / 3

        rows.append(CashBridge(
            year=yr,
            revenue_mm=round(rev, 1),
            ebitda_mm=round(ebitda_y, 1),
            dso_days=round(dso, 1),
            ar_balance_mm=round(ar, 2),
            nwc_mm=round(nwc, 2),
            fcf_mm=round(fcf, 2),
            cum_cash_released_mm=round(cum_release, 2),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_working_capital(
    sector: str = "Physician Services",
    revenue_mm: float = 100.0,
    ebitda_margin: float = 0.18,
    payer_mix: Optional[Dict[str, float]] = None,
    dso_override: Optional[float] = None,
    dso_target: Optional[float] = None,
    hold_years: int = 5,
    organic_growth_pct: float = 0.04,
) -> WorkingCapitalResult:
    corpus = _load_corpus()

    if payer_mix is None:
        payer_mix = {
            "commercial": 0.55, "medicare": 0.25,
            "medicaid": 0.15, "self_pay": 0.05,
        }

    ebitda = revenue_mm * ebitda_margin
    baseline = _build_baseline(sector, revenue_mm, dso_override, None)

    payer_ar = _build_payer_ar(payer_mix, baseline.ar_balance_mm)
    improvements = _build_improvements(baseline.dso_days, revenue_mm, ebitda)

    total_dso_lift = sum(im.dso_reduction_days for im in improvements)
    target = dso_target if dso_target is not None else max(baseline.dso_days - total_dso_lift * 0.60, 12)

    cash_bridge = _build_cash_bridge(
        revenue_mm=revenue_mm,
        ebitda_mm=ebitda,
        baseline_dso=baseline.dso_days,
        dso_target=target,
        improvements=improvements,
        hold_years=hold_years,
        organic_growth_pct=organic_growth_pct,
    )

    total_unlock = sum(im.cash_release_mm for im in improvements) * 0.60  # realize 60%
    annual_fcf_uplift = sum(im.ongoing_fcf_impact_mm for im in improvements) * 0.60

    return WorkingCapitalResult(
        sector=sector,
        revenue_mm=round(revenue_mm, 1),
        baseline=baseline,
        payer_ar=payer_ar,
        improvements=improvements,
        cash_bridge=cash_bridge,
        total_cash_unlock_mm=round(total_unlock, 1),
        annual_fcf_uplift_mm=round(annual_fcf_uplift, 2),
        corpus_deal_count=len(corpus),
    )
