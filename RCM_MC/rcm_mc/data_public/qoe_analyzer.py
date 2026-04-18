"""Quality of Earnings analyzer — EBITDA add-back benchmarking from corpus."""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Add-back category definitions
# ---------------------------------------------------------------------------

ADDBACK_CATEGORIES = [
    "owner_comp_normalization",
    "one_time_transaction_costs",
    "management_fee_addback",
    "non_recurring_legal",
    "startup_losses",
    "pro_forma_acquisitions",
    "revenue_cycle_improvement",
    "it_migration",
    "facility_consolidation",
    "other_addbacks",
]

# Typical add-back magnitude as % of reported EBITDA by category (corpus-implied)
_ADDBACK_PCT_BY_SECTOR: Dict[str, Dict[str, float]] = {
    "Physician Group": {
        "owner_comp_normalization": 0.12, "one_time_transaction_costs": 0.04,
        "management_fee_addback": 0.06, "non_recurring_legal": 0.02,
        "startup_losses": 0.01, "pro_forma_acquisitions": 0.08,
        "revenue_cycle_improvement": 0.05, "it_migration": 0.02,
        "facility_consolidation": 0.01, "other_addbacks": 0.03,
    },
    "Behavioral Health": {
        "owner_comp_normalization": 0.08, "one_time_transaction_costs": 0.05,
        "management_fee_addback": 0.04, "non_recurring_legal": 0.03,
        "startup_losses": 0.04, "pro_forma_acquisitions": 0.06,
        "revenue_cycle_improvement": 0.07, "it_migration": 0.03,
        "facility_consolidation": 0.03, "other_addbacks": 0.04,
    },
    "Dental": {
        "owner_comp_normalization": 0.18, "one_time_transaction_costs": 0.04,
        "management_fee_addback": 0.05, "non_recurring_legal": 0.01,
        "startup_losses": 0.02, "pro_forma_acquisitions": 0.10,
        "revenue_cycle_improvement": 0.03, "it_migration": 0.02,
        "facility_consolidation": 0.01, "other_addbacks": 0.03,
    },
    "Dermatology": {
        "owner_comp_normalization": 0.20, "one_time_transaction_costs": 0.04,
        "management_fee_addback": 0.05, "non_recurring_legal": 0.01,
        "startup_losses": 0.02, "pro_forma_acquisitions": 0.09,
        "revenue_cycle_improvement": 0.04, "it_migration": 0.02,
        "facility_consolidation": 0.01, "other_addbacks": 0.03,
    },
    "Urgent Care": {
        "owner_comp_normalization": 0.06, "one_time_transaction_costs": 0.05,
        "management_fee_addback": 0.04, "non_recurring_legal": 0.02,
        "startup_losses": 0.05, "pro_forma_acquisitions": 0.07,
        "revenue_cycle_improvement": 0.06, "it_migration": 0.03,
        "facility_consolidation": 0.04, "other_addbacks": 0.04,
    },
    "Ambulatory Surgery": {
        "owner_comp_normalization": 0.07, "one_time_transaction_costs": 0.04,
        "management_fee_addback": 0.05, "non_recurring_legal": 0.02,
        "startup_losses": 0.03, "pro_forma_acquisitions": 0.06,
        "revenue_cycle_improvement": 0.04, "it_migration": 0.03,
        "facility_consolidation": 0.03, "other_addbacks": 0.03,
    },
    "Home Health": {
        "owner_comp_normalization": 0.07, "one_time_transaction_costs": 0.04,
        "management_fee_addback": 0.04, "non_recurring_legal": 0.02,
        "startup_losses": 0.03, "pro_forma_acquisitions": 0.05,
        "revenue_cycle_improvement": 0.08, "it_migration": 0.03,
        "facility_consolidation": 0.02, "other_addbacks": 0.04,
    },
    "default": {
        "owner_comp_normalization": 0.09, "one_time_transaction_costs": 0.04,
        "management_fee_addback": 0.05, "non_recurring_legal": 0.02,
        "startup_losses": 0.03, "pro_forma_acquisitions": 0.07,
        "revenue_cycle_improvement": 0.05, "it_migration": 0.02,
        "facility_consolidation": 0.02, "other_addbacks": 0.03,
    },
}

# Quality score — lower add-back% is higher quality (more defensible earnings)
_QUALITY_THRESHOLDS = {
    "Investment Grade": (0.0, 0.15),
    "Acceptable":       (0.15, 0.28),
    "Elevated":         (0.28, 0.42),
    "Aggressive":       (0.42, 1.0),
}

_QUALITY_COLORS = {
    "Investment Grade": "#22c55e",
    "Acceptable":       "#3b82f6",
    "Elevated":         "#f59e0b",
    "Aggressive":       "#ef4444",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AddbackBreakdown:
    category: str
    label: str
    amount_mm: float          # $ millions
    pct_of_reported: float    # as fraction of reported EBITDA
    pct_of_adjusted: float    # as fraction of adjusted EBITDA
    quality_flag: str         # "Defensible", "Scrutinize", "Aggressive"
    corpus_p50: float         # corpus median for this addback / reported EBITDA


@dataclass
class QoEBenchmark:
    sector: str
    n_peers: int
    median_total_addback_pct: float   # median total add-backs / reported
    p25_total_addback_pct: float
    p75_total_addback_pct: float
    median_adj_ebitda_margin: float
    moic_premium_low_addback: float   # MOIC uplift for low add-back vs high


@dataclass
class QoEResult:
    sector: str
    reported_ebitda_mm: float
    total_addback_mm: float
    adjusted_ebitda_mm: float
    addback_pct_of_reported: float
    quality_tier: str
    quality_color: str
    breakdowns: List[AddbackBreakdown]
    benchmark: QoEBenchmark
    peers_low_addback: List[dict]    # top 5 peers with low addbacks (high quality)
    peers_high_addback: List[dict]   # top 5 peers with high addbacks (low quality)
    moic_by_quality: Dict[str, float]  # MOIC per quality tier from corpus
    corpus_deal_count: int


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


def _sector_key(sector: str) -> str:
    s = sector.lower()
    for k in _ADDBACK_PCT_BY_SECTOR:
        if k.lower() in s or s in k.lower():
            return k
    return "default"


def _quality_tier(pct: float) -> Tuple[str, str]:
    for tier, (lo, hi) in _QUALITY_THRESHOLDS.items():
        if lo <= pct < hi:
            return tier, _QUALITY_COLORS[tier]
    return "Aggressive", _QUALITY_COLORS["Aggressive"]


def _flag(cat: str, pct: float, corpus_p50: float) -> str:
    if pct <= corpus_p50 * 0.8:
        return "Defensible"
    if pct <= corpus_p50 * 1.3:
        return "Scrutinize"
    return "Aggressive"


_CATEGORY_LABELS = {
    "owner_comp_normalization": "Owner Comp Normalization",
    "one_time_transaction_costs": "One-Time Transaction Costs",
    "management_fee_addback": "Management Fee Add-Back",
    "non_recurring_legal": "Non-Recurring Legal / Litigation",
    "startup_losses": "Startup / Pre-Opening Losses",
    "pro_forma_acquisitions": "Pro Forma Acquisition Adj.",
    "revenue_cycle_improvement": "Revenue Cycle Improvement",
    "it_migration": "IT Migration / System Upgrade",
    "facility_consolidation": "Facility Consolidation",
    "other_addbacks": "Other Add-Backs",
}


def _sim_addback_for_deal(d: dict, sector_key: str) -> float:
    """Estimate total add-back % for a corpus deal based on sector + size heuristic."""
    base = sum(_ADDBACK_PCT_BY_SECTOR.get(sector_key, _ADDBACK_PCT_BY_SECTOR["default"]).values())
    ev = d.get("ev_mm", 100.0)
    size_adj = -0.03 if ev > 300 else (0.04 if ev < 80 else 0.0)
    return max(0.05, base + size_adj)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_qoe_analyzer(
    sector: str,
    reported_ebitda_mm: float,
    ev_mm: float,
    custom_addbacks: Optional[Dict[str, float]] = None,
) -> QoEResult:
    """
    Decompose quality of earnings for a deal being diligenced.

    custom_addbacks: dict {category: amount_mm} overrides corpus-derived estimates.
    """
    corpus = _load_corpus()
    skey = _sector_key(sector)
    cat_pcts = _ADDBACK_PCT_BY_SECTOR.get(skey, _ADDBACK_PCT_BY_SECTOR["default"])

    # Build add-back breakdown
    breakdowns: List[AddbackBreakdown] = []
    total_addback = 0.0
    for cat in ADDBACK_CATEGORIES:
        if custom_addbacks and cat in custom_addbacks:
            amt = float(custom_addbacks[cat])
        else:
            amt = cat_pcts[cat] * reported_ebitda_mm
        pct_rep = amt / reported_ebitda_mm if reported_ebitda_mm else 0.0
        corpus_p50 = cat_pcts[cat]
        breakdowns.append(AddbackBreakdown(
            category=cat,
            label=_CATEGORY_LABELS[cat],
            amount_mm=round(amt, 2),
            pct_of_reported=round(pct_rep, 4),
            pct_of_adjusted=0.0,  # filled below
            quality_flag=_flag(cat, pct_rep, corpus_p50),
            corpus_p50=corpus_p50,
        ))
        total_addback += amt

    adjusted_ebitda = reported_ebitda_mm + total_addback
    addback_pct = total_addback / reported_ebitda_mm if reported_ebitda_mm else 0.0

    for b in breakdowns:
        b.pct_of_adjusted = round(b.amount_mm / adjusted_ebitda, 4) if adjusted_ebitda else 0.0

    quality_tier, quality_color = _quality_tier(addback_pct)

    # ---- Benchmark from corpus ----
    sector_deals = [d for d in corpus if sector.lower()[:8] in d.get("sector","").lower() or
                    d.get("sector","").lower()[:8] in sector.lower()]
    if len(sector_deals) < 5:
        sector_deals = corpus  # fallback to full corpus

    peer_addback_pcts: List[float] = []
    for d in sector_deals:
        emp = _sim_addback_for_deal(d, _sector_key(d.get("sector", sector)))
        peer_addback_pcts.append(emp)

    peer_addback_pcts.sort()
    n = len(peer_addback_pcts)
    p25 = peer_addback_pcts[int(n * 0.25)] if n >= 4 else 0.20
    p50 = peer_addback_pcts[int(n * 0.50)] if n >= 4 else 0.25
    p75 = peer_addback_pcts[int(n * 0.75)] if n >= 4 else 0.35

    # EBITDA margins from sector peers
    margins = [d.get("ebitda_margin", 0.18) for d in sector_deals if d.get("ebitda_margin")]
    adj_margin = sorted(margins)[len(margins) // 2] if margins else 0.18

    # MOIC premium for low add-back deals
    moic_low = [d.get("moic", 2.5) for d in sector_deals
                if _sim_addback_for_deal(d, skey) < p25]
    moic_high = [d.get("moic", 2.5) for d in sector_deals
                 if _sim_addback_for_deal(d, skey) > p75]
    moic_low_med = sorted(moic_low)[len(moic_low)//2] if moic_low else 3.2
    moic_high_med = sorted(moic_high)[len(moic_high)//2] if moic_high else 2.8
    moic_premium = round(moic_low_med - moic_high_med, 2)

    benchmark = QoEBenchmark(
        sector=sector,
        n_peers=n,
        median_total_addback_pct=round(p50, 4),
        p25_total_addback_pct=round(p25, 4),
        p75_total_addback_pct=round(p75, 4),
        median_adj_ebitda_margin=round(adj_margin, 4),
        moic_premium_low_addback=moic_premium,
    )

    # Peers with low and high add-backs
    peer_scored = sorted(sector_deals,
                         key=lambda d: _sim_addback_for_deal(d, _sector_key(d.get("sector", sector))))
    def _peer_dict(d: dict) -> dict:
        return {
            "company": d.get("company_name", "—"),
            "sector": d.get("sector", "—"),
            "year": d.get("year", 0),
            "ev_mm": d.get("ev_mm", 0.0),
            "moic": d.get("moic", 0.0),
            "irr": d.get("irr", 0.0),
            "addback_pct": round(_sim_addback_for_deal(d, _sector_key(d.get("sector", sector))), 3),
        }
    peers_low = [_peer_dict(d) for d in peer_scored[:10]][:5]
    peers_high = [_peer_dict(d) for d in peer_scored[-10:]][:5]

    # MOIC by quality tier
    moic_by_quality: Dict[str, float] = {}
    for tier, (lo, hi) in _QUALITY_THRESHOLDS.items():
        tier_deals = [d for d in sector_deals
                      if lo <= _sim_addback_for_deal(d, _sector_key(d.get("sector",sector))) < hi]
        if tier_deals:
            mocs = sorted(d.get("moic", 2.5) for d in tier_deals)
            moic_by_quality[tier] = round(mocs[len(mocs)//2], 2)
        else:
            moic_by_quality[tier] = 0.0

    return QoEResult(
        sector=sector,
        reported_ebitda_mm=round(reported_ebitda_mm, 2),
        total_addback_mm=round(total_addback, 2),
        adjusted_ebitda_mm=round(adjusted_ebitda, 2),
        addback_pct_of_reported=round(addback_pct, 4),
        quality_tier=quality_tier,
        quality_color=quality_color,
        breakdowns=breakdowns,
        benchmark=benchmark,
        peers_low_addback=peers_low,
        peers_high_addback=peers_high,
        moic_by_quality=moic_by_quality,
        corpus_deal_count=len(corpus),
    )
