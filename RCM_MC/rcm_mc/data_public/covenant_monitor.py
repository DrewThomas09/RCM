"""Covenant Monitor — leverage ratio tracking and covenant headroom from corpus."""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Covenant definitions and benchmarks
# ---------------------------------------------------------------------------

# Typical LBO leverage at entry by EV size bucket
_LEVERAGE_BY_SIZE: Dict[str, Dict[str, float]] = {
    "<$100M":    {"debt_ebitda": 4.0, "interest_coverage": 3.5, "senior_debt_ebitda": 3.2},
    "$100-250M": {"debt_ebitda": 4.5, "interest_coverage": 3.2, "senior_debt_ebitda": 3.8},
    "$250-500M": {"debt_ebitda": 5.0, "interest_coverage": 2.8, "senior_debt_ebitda": 4.2},
    ">$500M":    {"debt_ebitda": 5.5, "interest_coverage": 2.5, "senior_debt_ebitda": 4.8},
}

# Typical covenant thresholds (maintenance-tested) by size
_COVENANT_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "<$100M":    {"max_leverage": 5.5, "min_coverage": 2.5, "max_capex_pct_rev": 0.08},
    "$100-250M": {"max_leverage": 6.0, "min_coverage": 2.2, "max_capex_pct_rev": 0.07},
    "$250-500M": {"max_leverage": 6.5, "min_coverage": 2.0, "max_capex_pct_rev": 0.06},
    ">$500M":    {"max_leverage": 7.0, "min_coverage": 1.8, "max_capex_pct_rev": 0.06},
}

# Base rate assumptions for interest calc
_BASE_RATE = 0.052   # SOFR + spread ~530bps all-in
_CAPEX_PCT_REV_DEFAULT = 0.05

# Corpus-implied leverage step-down by hold year
_LEVERAGE_STEP_DOWN = {1: 0.0, 2: -0.4, 3: -0.8, 4: -1.2, 5: -1.6, 6: -2.0}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CovenantStatus:
    name: str
    label: str
    current_value: float
    threshold: float
    headroom: float          # positive = cushion, negative = breach
    headroom_pct: float      # headroom as % of threshold
    status: str              # "Compliant", "Watch", "Breach"
    status_color: str


@dataclass
class LeverageProjection:
    year: int
    debt_ebitda: float
    interest_coverage: float
    ebitda_mm: float
    debt_mm: float
    is_compliant: bool


@dataclass
class CovenantPeer:
    company: str
    sector: str
    year: int
    ev_mm: float
    ev_ebitda: float
    moic: float
    implied_leverage: float


@dataclass
class CovenantMonitorResult:
    ev_mm: float
    ebitda_mm: float
    sector: str
    size_bucket: str
    entry_leverage: float           # Debt/EBITDA at entry
    current_leverage: float         # after amortization
    interest_coverage: float
    covenants: List[CovenantStatus]
    projections: List[LeverageProjection]
    peers_tight: List[CovenantPeer]   # peers with tight coverage
    peers_comfortable: List[CovenantPeer]
    sector_median_leverage: float
    sector_p75_leverage: float
    moic_by_leverage_bucket: Dict[str, float]
    corpus_deal_count: int
    overall_status: str
    overall_color: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 55):
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
    if ev_mm < 100:
        return "<$100M"
    if ev_mm < 250:
        return "$100-250M"
    if ev_mm < 500:
        return "$250-500M"
    return ">$500M"


def _implied_leverage(d: dict) -> float:
    ev = d.get("ev_mm", 100.0)
    ev_ebitda = d.get("ev_ebitda") or 10.0
    if ev_ebitda <= 0:
        return 4.5
    ebitda = ev / ev_ebitda
    sbucket = _size_bucket(ev)
    base = _LEVERAGE_BY_SIZE[sbucket]["debt_ebitda"]
    eq_contribution = 0.40 + max(0.0, (ev_ebitda - 10) * 0.02)
    eq_contribution = min(eq_contribution, 0.55)
    debt_fraction = 1.0 - eq_contribution
    total_debt = ev * debt_fraction
    return round(total_debt / ebitda, 2) if ebitda > 0 else base


def _status(headroom: float, headroom_pct: float) -> Tuple[str, str]:
    if headroom < 0:
        return "Breach", "#ef4444"
    if headroom_pct < 0.15:
        return "Watch", "#f59e0b"
    return "Compliant", "#22c55e"


def _project_leverage(
    entry_leverage: float,
    ebitda_mm: float,
    hold_years: int = 6,
    ebitda_growth: float = 0.05,
    amort_rate: float = 0.04,
) -> List[LeverageProjection]:
    projs = []
    debt = entry_leverage * ebitda_mm
    coverage_threshold = 2.2
    for yr in range(1, hold_years + 1):
        ebitda = ebitda_mm * (1 + ebitda_growth) ** yr
        debt = debt * (1 - amort_rate)
        lev = debt / ebitda if ebitda > 0 else entry_leverage
        interest = debt * _BASE_RATE
        icr = ebitda / interest if interest > 0 else 99.0
        projs.append(LeverageProjection(
            year=yr,
            debt_ebitda=round(lev, 2),
            interest_coverage=round(icr, 2),
            ebitda_mm=round(ebitda, 2),
            debt_mm=round(debt, 2),
            is_compliant=(lev <= 7.0 and icr >= 1.8),
        ))
    return projs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_covenant_monitor(
    sector: str,
    ev_mm: float,
    ebitda_mm: float,
    hold_year: int = 1,
    custom_leverage: Optional[float] = None,
    ebitda_growth_pct: float = 5.0,
) -> CovenantMonitorResult:
    corpus = _load_corpus()
    sbucket = _size_bucket(ev_mm)
    thresholds = _COVENANT_THRESHOLDS[sbucket]
    base_lev = _LEVERAGE_BY_SIZE[sbucket]

    # Entry leverage
    if custom_leverage is not None and custom_leverage > 0:
        entry_lev = custom_leverage
    else:
        eq_pct = 0.40 + max(0.0, ((ev_mm / ebitda_mm) - 10) * 0.02)
        eq_pct = min(eq_pct, 0.55)
        entry_lev = round((ev_mm * (1.0 - eq_pct)) / ebitda_mm, 2)

    # Current leverage after amortization
    amort = 0.04 * hold_year
    ebitda_now = ebitda_mm * (1 + ebitda_growth_pct / 100) ** hold_year
    debt_now = entry_lev * ebitda_mm * (1 - amort)
    current_lev = round(debt_now / ebitda_now, 2) if ebitda_now > 0 else entry_lev

    # Interest coverage
    interest = debt_now * _BASE_RATE
    icr = round(ebitda_now / interest, 2) if interest > 0 else 99.0

    # Capex
    rev_mm = ev_mm / (ev_mm / ebitda_mm) / 0.18 if ebitda_mm > 0 else ev_mm * 2
    capex_pct = _CAPEX_PCT_REV_DEFAULT
    capex_actual_pct = capex_pct

    # Covenant statuses
    def _cov(name: str, label: str, current: float, threshold: float, higher_is_bad: bool = True) -> CovenantStatus:
        if higher_is_bad:
            headroom = threshold - current
            headroom_pct = headroom / threshold if threshold else 0.0
        else:
            headroom = current - threshold
            headroom_pct = headroom / threshold if threshold else 0.0
        status, color = _status(headroom, headroom_pct)
        return CovenantStatus(
            name=name, label=label,
            current_value=round(current, 2),
            threshold=round(threshold, 2),
            headroom=round(headroom, 2),
            headroom_pct=round(headroom_pct, 3),
            status=status, status_color=color,
        )

    covenants = [
        _cov("max_leverage", "Max Total Leverage (Debt/EBITDA)",
             current_lev, thresholds["max_leverage"], higher_is_bad=True),
        _cov("min_coverage", "Min Interest Coverage (EBITDA/Interest)",
             icr, thresholds["min_coverage"], higher_is_bad=False),
        _cov("max_capex", "Max CapEx (% Revenue)",
             capex_actual_pct, thresholds["max_capex_pct_rev"], higher_is_bad=True),
    ]

    # Projections
    projections = _project_leverage(
        entry_lev, ebitda_mm,
        hold_years=6,
        ebitda_growth=ebitda_growth_pct / 100,
    )

    # Overall status
    statuses = [c.status for c in covenants]
    if "Breach" in statuses:
        overall_status, overall_color = "Breach", "#ef4444"
    elif "Watch" in statuses:
        overall_status, overall_color = "Watch", "#f59e0b"
    else:
        overall_status, overall_color = "Compliant", "#22c55e"

    # Corpus peers
    sector_deals = [d for d in corpus if sector.lower()[:6] in d.get("sector","").lower() or
                    d.get("sector","").lower()[:6] in sector.lower()]
    if len(sector_deals) < 5:
        sector_deals = corpus

    peer_levs = [_implied_leverage(d) for d in sector_deals]
    peer_levs_s = sorted(peer_levs)
    n = len(peer_levs_s)
    sector_med_lev = peer_levs_s[n//2] if n else 4.5
    sector_p75_lev = peer_levs_s[int(n * 0.75)] if n else 5.5

    def _peer_dict(d: dict) -> CovenantPeer:
        return CovenantPeer(
            company=d.get("company_name", "—"),
            sector=d.get("sector", "—"),
            year=d.get("year", 0),
            ev_mm=d.get("ev_mm", 0.0),
            ev_ebitda=d.get("ev_ebitda", 0.0),
            moic=d.get("moic", 0.0),
            implied_leverage=_implied_leverage(d),
        )

    peers_sorted = sorted(sector_deals, key=_implied_leverage)
    peers_tight = [_peer_dict(d) for d in peers_sorted[-10:]][:5]
    peers_comfortable = [_peer_dict(d) for d in peers_sorted[:10]][:5]

    # MOIC by leverage bucket
    moic_by_lev: Dict[str, float] = {}
    buckets = [("<4x", 0, 4), ("4-5x", 4, 5), ("5-6x", 5, 6), (">6x", 6, 99)]
    for label, lo, hi in buckets:
        grp = [d.get("moic", 2.5) for d in sector_deals
               if lo <= _implied_leverage(d) < hi]
        if grp:
            grp.sort()
            moic_by_lev[label] = round(grp[len(grp)//2], 2)

    return CovenantMonitorResult(
        ev_mm=round(ev_mm, 2),
        ebitda_mm=round(ebitda_mm, 2),
        sector=sector,
        size_bucket=sbucket,
        entry_leverage=entry_lev,
        current_leverage=current_lev,
        interest_coverage=icr,
        covenants=covenants,
        projections=projections,
        peers_tight=peers_tight,
        peers_comfortable=peers_comfortable,
        sector_median_leverage=round(sector_med_lev, 2),
        sector_p75_leverage=round(sector_p75_lev, 2),
        moic_by_leverage_bucket=moic_by_lev,
        corpus_deal_count=len(corpus),
        overall_status=overall_status,
        overall_color=overall_color,
    )
