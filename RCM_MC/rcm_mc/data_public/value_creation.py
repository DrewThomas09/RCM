"""Value Creation Tracker — EBITDA bridge decomposition and initiative tracking from corpus."""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Value creation lever definitions
# ---------------------------------------------------------------------------

_LEVERS = [
    ("revenue_growth",        "Organic Revenue Growth",         0.30),
    ("ebitda_margin_expansion","EBITDA Margin Expansion",        0.25),
    ("add_on_acquisitions",   "Add-On Acquisitions",            0.20),
    ("multiple_expansion",    "Multiple Expansion",             0.15),
    ("leverage_paydown",      "Debt Paydown / Deleveraging",    0.10),
]

# Typical contribution magnitude by sector (% of total value created)
_LEVER_PROFILE_BY_SECTOR: Dict[str, Dict[str, float]] = {
    "Physician Group": {
        "revenue_growth": 0.28, "ebitda_margin_expansion": 0.22,
        "add_on_acquisitions": 0.30, "multiple_expansion": 0.12, "leverage_paydown": 0.08,
    },
    "Behavioral Health": {
        "revenue_growth": 0.35, "ebitda_margin_expansion": 0.25,
        "add_on_acquisitions": 0.20, "multiple_expansion": 0.10, "leverage_paydown": 0.10,
    },
    "Dental": {
        "revenue_growth": 0.25, "ebitda_margin_expansion": 0.20,
        "add_on_acquisitions": 0.38, "multiple_expansion": 0.10, "leverage_paydown": 0.07,
    },
    "Health IT": {
        "revenue_growth": 0.40, "ebitda_margin_expansion": 0.30,
        "add_on_acquisitions": 0.12, "multiple_expansion": 0.12, "leverage_paydown": 0.06,
    },
    "Home Health": {
        "revenue_growth": 0.32, "ebitda_margin_expansion": 0.28,
        "add_on_acquisitions": 0.20, "multiple_expansion": 0.10, "leverage_paydown": 0.10,
    },
    "default": {
        "revenue_growth": 0.30, "ebitda_margin_expansion": 0.25,
        "add_on_acquisitions": 0.22, "multiple_expansion": 0.13, "leverage_paydown": 0.10,
    },
}

# Typical RCM-specific initiatives and their EBITDA impact
_RCM_INITIATIVES = [
    ("denial_management",  "Denial Rate Reduction",     "Reduces initial denial rate by 3-5pp", 0.08),
    ("coding_improvement", "Coding Accuracy Improvement", "Reduces undercoding, improves case mix", 0.06),
    ("ar_velocity",        "A/R Velocity Improvement",   "Reduces DSO by 8-12 days", 0.04),
    ("prior_auth",         "Prior Auth Automation",      "Reduces admin labor 15-20%", 0.05),
    ("payer_contract",     "Payer Contract Renegotiation","Improves contracted rates 3-8%", 0.07),
    ("billing_outsource",  "Billing Consolidation",      "Consolidates to centralized RCM platform", 0.05),
    ("collections",        "Patient Collections Enhancement","Improves patient pay collection 20-30%", 0.03),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ValueLever:
    lever_id: str
    label: str
    contribution_pct: float      # share of total value created
    ebitda_contribution_mm: float
    ev_contribution_mm: float
    entry_multiple_used: float


@dataclass
class RcmInitiative:
    initiative_id: str
    label: str
    description: str
    ebitda_impact_pct: float     # % of entry EBITDA
    ebitda_impact_mm: float
    year_1_capture: float        # % captured in year 1
    cumulative_npv_mm: float


@dataclass
class PeerValueCreation:
    company: str
    sector: str
    year: int
    ev_mm: float
    entry_multiple: float
    moic: float
    irr: float
    hold_years: float
    implied_rev_growth: float    # derived from MOIC and hold


@dataclass
class ValueCreationResult:
    sector: str
    entry_ebitda_mm: float
    entry_multiple: float
    entry_ev_mm: float
    exit_ebitda_mm: float
    exit_multiple: float
    exit_ev_mm: float
    moic: float
    irr: float
    hold_years: float
    levers: List[ValueLever]
    rcm_initiatives: List[RcmInitiative]
    peers: List[PeerValueCreation]
    total_ebitda_created_mm: float
    total_ev_created_mm: float
    sector_median_moic: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 57):
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


def _sector_key(sector: str) -> str:
    for k in _LEVER_PROFILE_BY_SECTOR:
        if k.lower() in sector.lower() or sector.lower() in k.lower():
            return k
    return "default"


def _calc_irr(moic: float, hold_years: float) -> float:
    if hold_years <= 0 or moic <= 0:
        return 0.0
    return round((moic ** (1.0 / hold_years)) - 1.0, 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_value_creation(
    sector: str,
    entry_ebitda_mm: float,
    entry_multiple: float,
    hold_years: float = 5.0,
    ebitda_growth_pct: float = 8.0,
    multiple_expansion: float = 1.5,
) -> ValueCreationResult:
    corpus = _load_corpus()
    skey = _sector_key(sector)
    lever_profile = _LEVER_PROFILE_BY_SECTOR.get(skey, _LEVER_PROFILE_BY_SECTOR["default"])

    entry_ev = entry_ebitda_mm * entry_multiple
    exit_ebitda = entry_ebitda_mm * (1 + ebitda_growth_pct / 100) ** hold_years
    exit_multiple_val = entry_multiple + multiple_expansion
    exit_ev = exit_ebitda * exit_multiple_val

    # EV created
    eq_pct = 0.45
    equity_entry = entry_ev * eq_pct
    equity_exit = exit_ev * eq_pct
    moic = round(equity_exit / equity_entry, 2) if equity_entry > 0 else 0.0
    irr = _calc_irr(moic, hold_years)

    total_ev_created = exit_ev - entry_ev
    total_ebitda_created = exit_ebitda - entry_ebitda_mm

    # Value levers
    levers: List[ValueLever] = []
    for lever_id, label, _ in _LEVERS:
        share = lever_profile.get(lever_id, 0.1)
        ev_contrib = total_ev_created * share
        ebitda_contrib = total_ebitda_created * share
        levers.append(ValueLever(
            lever_id=lever_id,
            label=label,
            contribution_pct=round(share, 3),
            ebitda_contribution_mm=round(ebitda_contrib, 2),
            ev_contribution_mm=round(ev_contrib, 2),
            entry_multiple_used=entry_multiple,
        ))

    # RCM initiatives
    rcm_initiatives: List[RcmInitiative] = []
    for rid, label, desc, impact_pct in _RCM_INITIATIVES:
        impact_mm = round(entry_ebitda_mm * impact_pct, 2)
        y1_capture = 0.40  # 40% in year 1
        npv = round(sum(impact_mm * 0.9 ** yr for yr in range(int(hold_years))), 2)
        rcm_initiatives.append(RcmInitiative(
            initiative_id=rid, label=label, description=desc,
            ebitda_impact_pct=impact_pct,
            ebitda_impact_mm=impact_mm,
            year_1_capture=y1_capture,
            cumulative_npv_mm=npv,
        ))

    # Corpus peers
    sector_deals = [d for d in corpus if
                    sector.lower()[:6] in (d.get("sector") or "").lower() or
                    (d.get("sector") or "").lower()[:6] in sector.lower()]
    if len(sector_deals) < 5:
        sector_deals = corpus

    all_moics = sorted(d.get("moic", 2.5) for d in sector_deals)
    n = len(all_moics)
    sector_med_moic = round(all_moics[n // 2], 2) if n else 3.0

    def _peer(d: dict) -> PeerValueCreation:
        m = d.get("moic") or 2.5
        h = d.get("hold_years") or 4.0
        em = d.get("ev_ebitda") or 10.0
        rev_growth = ((m ** (1 / h)) - 1.0) * 0.6 if h > 0 else 0.0
        return PeerValueCreation(
            company=d.get("company_name", "—"),
            sector=d.get("sector", "—"),
            year=d.get("year", 0),
            ev_mm=d.get("ev_mm", 0.0),
            entry_multiple=round(em, 1),
            moic=round(m, 2),
            irr=round(d.get("irr") or _calc_irr(m, h), 4),
            hold_years=round(h, 1),
            implied_rev_growth=round(rev_growth, 3),
        )

    peers_sorted = sorted(sector_deals, key=lambda d: d.get("moic") or 0, reverse=True)
    peers = [_peer(d) for d in peers_sorted[:15]]

    return ValueCreationResult(
        sector=sector,
        entry_ebitda_mm=round(entry_ebitda_mm, 2),
        entry_multiple=entry_multiple,
        entry_ev_mm=round(entry_ev, 2),
        exit_ebitda_mm=round(exit_ebitda, 2),
        exit_multiple=round(exit_multiple_val, 1),
        exit_ev_mm=round(exit_ev, 2),
        moic=moic,
        irr=irr,
        hold_years=hold_years,
        levers=levers,
        rcm_initiatives=rcm_initiatives,
        peers=peers,
        total_ebitda_created_mm=round(total_ebitda_created, 2),
        total_ev_created_mm=round(total_ev_created, 2),
        sector_median_moic=sector_med_moic,
        corpus_deal_count=len(corpus),
    )
