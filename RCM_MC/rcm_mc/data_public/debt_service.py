"""Debt Service Coverage Tracker — DSCR, interest coverage, covenant headroom.

For leveraged buyouts, tracks:
- DSCR (debt service coverage ratio) = EBITDA / (interest + amortization)
- Interest coverage = EBITDA / cash interest
- Covenant headroom against typical package (Total Leverage, Senior Leverage, FCF)
- Stress test: revenue drop, margin compression, rate hikes
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Debt package priors
# ---------------------------------------------------------------------------

_DEBT_PACKAGE_BY_SIZE = {
    "<$100M":   {"sr_leverage": 3.0, "total_leverage": 4.5, "sr_rate": 0.085, "sub_rate": 0.115, "amort_pct": 0.01},
    "$100-250M":{"sr_leverage": 3.5, "total_leverage": 5.0, "sr_rate": 0.080, "sub_rate": 0.110, "amort_pct": 0.01},
    "$250-500M":{"sr_leverage": 4.0, "total_leverage": 5.5, "sr_rate": 0.075, "sub_rate": 0.105, "amort_pct": 0.01},
    "$500M-1B": {"sr_leverage": 4.5, "total_leverage": 6.0, "sr_rate": 0.070, "sub_rate": 0.100, "amort_pct": 0.005},
    ">$1B":     {"sr_leverage": 5.0, "total_leverage": 6.5, "sr_rate": 0.065, "sub_rate": 0.095, "amort_pct": 0.005},
}

# Typical covenant thresholds (max leverage ratios with 20% cushion)
_COVENANT_BY_SIZE = {
    "<$100M":   {"total_lev_cov": 5.0, "sr_lev_cov": 3.5, "dscr_min": 1.20, "int_cov_min": 2.00},
    "$100-250M":{"total_lev_cov": 5.5, "sr_lev_cov": 4.0, "dscr_min": 1.15, "int_cov_min": 1.85},
    "$250-500M":{"total_lev_cov": 6.0, "sr_lev_cov": 4.5, "dscr_min": 1.15, "int_cov_min": 1.75},
    "$500M-1B": {"total_lev_cov": 6.5, "sr_lev_cov": 5.0, "dscr_min": 1.10, "int_cov_min": 1.65},
    ">$1B":     {"total_lev_cov": 7.0, "sr_lev_cov": 5.5, "dscr_min": 1.10, "int_cov_min": 1.55},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DebtTranche:
    label: str
    principal_mm: float
    rate_pct: float
    amort_pct_per_yr: float
    balance_mm: float
    interest_mm: float
    amortization_mm: float


@dataclass
class CovenantStatus:
    label: str
    threshold: float
    current: float
    headroom_pct: float          # % above/below threshold
    status: str                  # "compliant", "tight", "breach"


@dataclass
class CoverageRow:
    year: int
    revenue_mm: float
    ebitda_mm: float
    cash_interest_mm: float
    amortization_mm: float
    total_debt_service_mm: float
    dscr: float
    interest_coverage: float
    total_leverage: float
    sr_leverage: float
    cum_amort_mm: float


@dataclass
class StressScenario:
    label: str
    revenue_shock_pct: float
    margin_shock_pp: float
    rate_shock_bps: int
    stressed_ebitda_mm: float
    stressed_dscr: float
    stressed_total_lev: float
    breach: bool
    breach_description: str


@dataclass
class DebtServiceResult:
    ev_mm: float
    ebitda_mm: float
    entry_multiple: float
    size_bucket: str
    tranches: List[DebtTranche]
    covenants: List[CovenantStatus]
    coverage_schedule: List[CoverageRow]
    stress_scenarios: List[StressScenario]
    equity_pct: float
    blended_rate_pct: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
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


def _size_bucket(ev_mm: float) -> str:
    if ev_mm < 100: return "<$100M"
    if ev_mm < 250: return "$100-250M"
    if ev_mm < 500: return "$250-500M"
    if ev_mm < 1000: return "$500M-1B"
    return ">$1B"


def _build_tranches(ebitda_mm: float, bucket: str) -> List[DebtTranche]:
    pkg = _DEBT_PACKAGE_BY_SIZE[bucket]
    sr_principal = round(ebitda_mm * pkg["sr_leverage"], 2)
    sub_principal = round(ebitda_mm * (pkg["total_leverage"] - pkg["sr_leverage"]), 2)

    sr_interest = round(sr_principal * pkg["sr_rate"], 2)
    sr_amort = round(sr_principal * pkg["amort_pct"], 2)
    sub_interest = round(sub_principal * pkg["sub_rate"], 2)
    sub_amort = 0.0   # sub debt typically non-amortizing, PIK or bullet

    return [
        DebtTranche(
            label="Senior Term Loan",
            principal_mm=sr_principal,
            rate_pct=round(pkg["sr_rate"] * 100, 2),
            amort_pct_per_yr=round(pkg["amort_pct"] * 100, 2),
            balance_mm=sr_principal,
            interest_mm=sr_interest,
            amortization_mm=sr_amort,
        ),
        DebtTranche(
            label="Subordinated / Mezz",
            principal_mm=sub_principal,
            rate_pct=round(pkg["sub_rate"] * 100, 2),
            amort_pct_per_yr=0.0,
            balance_mm=sub_principal,
            interest_mm=sub_interest,
            amortization_mm=sub_amort,
        ),
    ]


def _build_covenants(ebitda_mm: float, tranches: List[DebtTranche], bucket: str) -> List[CovenantStatus]:
    covs = _COVENANT_BY_SIZE[bucket]
    sr = tranches[0].principal_mm
    total = sr + (tranches[1].principal_mm if len(tranches) > 1 else 0)
    total_lev = total / ebitda_mm if ebitda_mm else 0
    sr_lev = sr / ebitda_mm if ebitda_mm else 0
    int_total = sum(t.interest_mm for t in tranches)
    amort_total = sum(t.amortization_mm for t in tranches)
    dscr = ebitda_mm / (int_total + amort_total) if (int_total + amort_total) else 0
    int_cov = ebitda_mm / int_total if int_total else 0

    def _status(current: float, threshold: float, higher_is_better: bool) -> (str, float):
        if higher_is_better:
            head = (current - threshold) / threshold if threshold else 0
            if current < threshold: return ("breach", head)
            if head < 0.15: return ("tight", head)
            return ("compliant", head)
        head = (threshold - current) / threshold if threshold else 0
        if current > threshold: return ("breach", head)
        if head < 0.15: return ("tight", head)
        return ("compliant", head)

    tl_stat, tl_head = _status(total_lev, covs["total_lev_cov"], higher_is_better=False)
    sl_stat, sl_head = _status(sr_lev, covs["sr_lev_cov"], higher_is_better=False)
    dscr_stat, dscr_head = _status(dscr, covs["dscr_min"], higher_is_better=True)
    ic_stat, ic_head = _status(int_cov, covs["int_cov_min"], higher_is_better=True)

    return [
        CovenantStatus("Total Leverage (max)", covs["total_lev_cov"], round(total_lev, 2), round(tl_head, 3), tl_stat),
        CovenantStatus("Senior Leverage (max)", covs["sr_lev_cov"], round(sr_lev, 2), round(sl_head, 3), sl_stat),
        CovenantStatus("DSCR (min)", covs["dscr_min"], round(dscr, 2), round(dscr_head, 3), dscr_stat),
        CovenantStatus("Interest Coverage (min)", covs["int_cov_min"], round(int_cov, 2), round(ic_head, 3), ic_stat),
    ]


def _build_schedule(
    revenue_mm: float, ebitda_mm: float, tranches: List[DebtTranche],
    hold_years: int, growth_pct: float,
) -> List[CoverageRow]:
    rows = []
    sr_bal = tranches[0].principal_mm
    sub_bal = tranches[1].principal_mm if len(tranches) > 1 else 0.0
    sr_rate = tranches[0].rate_pct / 100
    sub_rate = tranches[1].rate_pct / 100 if len(tranches) > 1 else 0.0
    sr_amort_pct = tranches[0].amort_pct_per_yr / 100
    cum_amort = 0.0

    for yr in range(0, hold_years + 1):
        rev = revenue_mm * ((1 + growth_pct) ** yr)
        ebitda_y = ebitda_mm * ((1 + growth_pct) ** yr)

        sr_int = sr_bal * sr_rate
        sub_int = sub_bal * sub_rate
        cash_int = sr_int + sub_int
        amort = sr_bal * sr_amort_pct

        if yr > 0:
            sr_bal = max(0, sr_bal - amort)
            cum_amort += amort

        total_ds = cash_int + amort
        dscr = ebitda_y / total_ds if total_ds else 0
        int_cov = ebitda_y / cash_int if cash_int else 0
        total_lev = (sr_bal + sub_bal) / ebitda_y if ebitda_y else 0
        sr_lev = sr_bal / ebitda_y if ebitda_y else 0

        rows.append(CoverageRow(
            year=yr,
            revenue_mm=round(rev, 1),
            ebitda_mm=round(ebitda_y, 2),
            cash_interest_mm=round(cash_int, 2),
            amortization_mm=round(amort, 2),
            total_debt_service_mm=round(total_ds, 2),
            dscr=round(dscr, 2),
            interest_coverage=round(int_cov, 2),
            total_leverage=round(total_lev, 2),
            sr_leverage=round(sr_lev, 2),
            cum_amort_mm=round(cum_amort, 2),
        ))
    return rows


def _stress_tests(
    revenue_mm: float, ebitda_mm: float, tranches: List[DebtTranche],
    bucket: str, ebitda_margin: float,
) -> List[StressScenario]:
    covs = _COVENANT_BY_SIZE[bucket]
    scenarios = [
        ("Revenue −10%", -0.10, 0.0, 0),
        ("Margin −200bps", 0.0, -0.02, 0),
        ("Rate +150bps", 0.0, 0.0, 150),
        ("Downturn (rev −15%, margin −300bps)", -0.15, -0.03, 0),
        ("Stagflation (rev −8%, margin −150bps, rate +200bps)", -0.08, -0.015, 200),
    ]
    results = []
    for label, rev_shock, margin_shock, rate_bps in scenarios:
        stressed_rev = revenue_mm * (1 + rev_shock)
        stressed_margin = max(0.03, ebitda_margin + margin_shock)
        stressed_ebitda = stressed_rev * stressed_margin
        # Stressed interest
        stressed_int = sum(
            t.principal_mm * (t.rate_pct / 100 + rate_bps / 10000) for t in tranches
        )
        stressed_amort = sum(t.amortization_mm for t in tranches)
        stressed_ds = stressed_int + stressed_amort
        stressed_dscr = stressed_ebitda / stressed_ds if stressed_ds else 0
        total_debt = sum(t.principal_mm for t in tranches)
        stressed_tl = total_debt / stressed_ebitda if stressed_ebitda else 99

        breach = stressed_dscr < covs["dscr_min"] or stressed_tl > covs["total_lev_cov"]
        desc = ""
        if stressed_dscr < covs["dscr_min"]:
            desc = f"DSCR {stressed_dscr:.2f} < {covs['dscr_min']:.2f}"
        elif stressed_tl > covs["total_lev_cov"]:
            desc = f"Total Lev {stressed_tl:.2f}x > {covs['total_lev_cov']:.2f}x cov"

        results.append(StressScenario(
            label=label,
            revenue_shock_pct=round(rev_shock, 3),
            margin_shock_pp=round(margin_shock, 3),
            rate_shock_bps=rate_bps,
            stressed_ebitda_mm=round(stressed_ebitda, 2),
            stressed_dscr=round(stressed_dscr, 2),
            stressed_total_lev=round(stressed_tl, 2),
            breach=breach,
            breach_description=desc,
        ))
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_debt_service(
    ev_mm: float = 300.0,
    entry_multiple: float = 12.0,
    ebitda_margin: float = 0.18,
    hold_years: int = 5,
    revenue_growth_pct: float = 0.05,
) -> DebtServiceResult:
    corpus = _load_corpus()
    ebitda = ev_mm / entry_multiple
    revenue = ebitda / ebitda_margin
    bucket = _size_bucket(ev_mm)

    tranches = _build_tranches(ebitda, bucket)
    covenants = _build_covenants(ebitda, tranches, bucket)
    schedule = _build_schedule(revenue, ebitda, tranches, hold_years, revenue_growth_pct)
    stress = _stress_tests(revenue, ebitda, tranches, bucket, ebitda_margin)

    total_debt = sum(t.principal_mm for t in tranches)
    equity = ev_mm - total_debt
    equity_pct = equity / ev_mm if ev_mm else 0.0
    blended = sum(t.interest_mm for t in tranches) / total_debt if total_debt else 0

    return DebtServiceResult(
        ev_mm=round(ev_mm, 1),
        ebitda_mm=round(ebitda, 2),
        entry_multiple=round(entry_multiple, 2),
        size_bucket=bucket,
        tranches=tranches,
        covenants=covenants,
        coverage_schedule=schedule,
        stress_scenarios=stress,
        equity_pct=round(equity_pct, 3),
        blended_rate_pct=round(blended * 100, 2),
        corpus_deal_count=len(corpus),
    )
