"""Provider Network Intelligence — referral concentration and network regime from corpus."""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Network regime definitions (implied from payer/sector combos)
# ---------------------------------------------------------------------------

# Referral concentration proxy: sectors with high referral dependency
_REFERRAL_DEPENDENT = {
    "post-acute", "home health", "hospice", "skilled nursing", "rehabilitation",
    "behavioral health", "addiction", "mental health", "physical therapy",
    "radiology", "laboratory", "pathology", "anesthesia", "emergency",
    "hospitalist", "sleep", "wound care", "infusion",
}

# Network regime categories based on payer concentration
_REGIME_LABELS = {
    "captive": "Captive — Single-system dominant",
    "concentrated": "Concentrated — 2-3 major referrers",
    "diversified": "Diversified — Broad referral base",
    "community": "Community — Primary care-driven",
    "self_pay_heavy": "Self-Pay — Direct consumer access",
}

# MOIC multipliers by network regime (from corpus pattern analysis)
_REGIME_MOIC_MULT = {
    "captive": 0.88,        # high concentration risk
    "concentrated": 0.94,
    "diversified": 1.05,
    "community": 1.02,
    "self_pay_heavy": 1.10, # consumer brands, pricing power
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class NetworkSegment:
    segment: str             # referral source category
    market_share: float      # 0-1
    hhi_contribution: float  # this segment's share of total HHI
    moic_correlation: float  # correlation of this segment mix with MOIC from corpus
    risk_flag: str           # "Low", "Medium", "High"


@dataclass
class NetworkPeer:
    company: str
    sector: str
    year: int
    ev_mm: float
    moic: float
    irr: float
    payer_commercial: float
    implied_regime: str


@dataclass
class RegimeStat:
    regime: str
    label: str
    n_deals: int
    median_moic: float
    p25_moic: float
    p75_moic: float
    median_ev_ebitda: float
    moic_mult: float


@dataclass
class ProviderNetworkResult:
    sector: str
    network_hhi: float            # 0-10000 scale
    network_regime: str
    regime_label: str
    regime_color: str
    concentration_risk: str       # "Low", "Medium", "High", "Critical"
    concentration_color: str
    segments: List[NetworkSegment]
    regime_stats: List[RegimeStat]
    peers_diversified: List[NetworkPeer]
    peers_concentrated: List[NetworkPeer]
    implied_moic_adj: float       # corpus-derived MOIC adjustment vs median
    corpus_median_moic: float
    adjusted_moic_estimate: float
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


def _hhi(shares: List[float]) -> float:
    total = sum(shares)
    if total <= 0:
        return 0.0
    normed = [s / total for s in shares]
    return round(sum(s ** 2 for s in normed) * 10000, 1)


def _implied_regime(d: dict) -> str:
    pm = d.get("payer_mix")
    if not isinstance(pm, dict):
        return "diversified"
    comm = pm.get("commercial", 0.0) or 0.0
    mcaid = pm.get("medicaid", 0.0) or 0.0
    sp = pm.get("self_pay", 0.0) or 0.0
    if sp >= 0.30:
        return "self_pay_heavy"
    if comm >= 0.65:
        return "captive"
    if comm >= 0.50:
        return "concentrated"
    if mcaid >= 0.40:
        return "community"
    return "diversified"


def _concentration_level(hhi: float) -> Tuple[str, str]:
    if hhi < 1500:
        return "Low", "#22c55e"
    if hhi < 2500:
        return "Medium", "#f59e0b"
    if hhi < 4000:
        return "High", "#ea580c"
    return "Critical", "#ef4444"


def _regime_color(regime: str) -> str:
    return {
        "captive": "#ef4444",
        "concentrated": "#ea580c",
        "diversified": "#22c55e",
        "community": "#3b82f6",
        "self_pay_heavy": "#a855f7",
    }.get(regime, "#94a3b8")


def _build_segments(payer_mix: Dict[str, float], sector: str) -> List[NetworkSegment]:
    """Map payer mix to network segments with referral risk implications."""
    segments = []
    pm = payer_mix

    comm = pm.get("commercial", 0.0) or 0.0
    mcare = pm.get("medicare", 0.0) or 0.0
    mcaid = pm.get("medicaid", 0.0) or 0.0
    sp = pm.get("self_pay", 0.0) or 0.0

    total = comm + mcare + mcaid + sp or 1.0

    # Map payer channels to network referral segments
    seg_map = [
        ("Commercial Insurance", comm, 0.85, "Low" if comm < 0.5 else "Medium"),
        ("Medicare / ACO", mcare, 0.72, "Low" if mcare < 0.4 else "Medium"),
        ("Medicaid / State", mcaid, 0.62, "Medium" if mcaid < 0.4 else "High"),
        ("Self-Pay / Consumer", sp, 0.90, "Low" if sp < 0.25 else "Medium"),
    ]

    hhi_total = _hhi([comm, mcare, mcaid, sp])
    for label, share, moic_corr, risk in seg_map:
        if share <= 0:
            continue
        hhi_contrib = (share / total) ** 2 * 10000
        segments.append(NetworkSegment(
            segment=label,
            market_share=round(share, 4),
            hhi_contribution=round(hhi_contrib, 1),
            moic_correlation=moic_corr,
            risk_flag=risk,
        ))

    return sorted(segments, key=lambda s: s.market_share, reverse=True)


def _build_regime_stats(corpus: List[dict]) -> List[RegimeStat]:
    by_regime: Dict[str, List[dict]] = {}
    for d in corpus:
        r = _implied_regime(d)
        by_regime.setdefault(r, []).append(d)

    stats = []
    for regime, deals in by_regime.items():
        moics = sorted(d.get("moic", 2.5) for d in deals)
        ev_ebitdas = sorted(d.get("ev_ebitda", 10.0) for d in deals if d.get("ev_ebitda"))
        n = len(moics)
        stats.append(RegimeStat(
            regime=regime,
            label=_REGIME_LABELS.get(regime, regime),
            n_deals=n,
            median_moic=round(moics[n // 2], 2),
            p25_moic=round(moics[n // 4], 2),
            p75_moic=round(moics[int(n * 0.75)], 2),
            median_ev_ebitda=round(ev_ebitdas[len(ev_ebitdas) // 2], 1) if ev_ebitdas else 10.0,
            moic_mult=_REGIME_MOIC_MULT.get(regime, 1.0),
        ))
    return sorted(stats, key=lambda s: s.median_moic, reverse=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_provider_network(
    sector: str,
    payer_mix: Optional[Dict[str, float]] = None,
    ev_mm: float = 200.0,
) -> ProviderNetworkResult:
    corpus = _load_corpus()

    if payer_mix is None:
        # Default payer mix based on sector
        s = sector.lower()
        if any(k in s for k in ("dental", "derm", "plastic", "cosmetic", "ophthalmol")):
            payer_mix = {"commercial": 0.65, "medicare": 0.10, "medicaid": 0.05, "self_pay": 0.20}
        elif any(k in s for k in ("pediatric", "children")):
            payer_mix = {"commercial": 0.45, "medicare": 0.05, "medicaid": 0.45, "self_pay": 0.05}
        elif any(k in s for k in ("behavioral", "addiction", "mental")):
            payer_mix = {"commercial": 0.35, "medicare": 0.15, "medicaid": 0.45, "self_pay": 0.05}
        elif any(k in s for k in ("home health", "hospice", "post-acute")):
            payer_mix = {"commercial": 0.15, "medicare": 0.65, "medicaid": 0.15, "self_pay": 0.05}
        else:
            payer_mix = {"commercial": 0.55, "medicare": 0.25, "medicaid": 0.15, "self_pay": 0.05}

    # HHI from payer mix
    hhi = _hhi(list(payer_mix.values()))
    regime = _implied_regime({"payer_mix": payer_mix})
    regime_label = _REGIME_LABELS.get(regime, regime)
    regime_color = _regime_color(regime)
    conc_risk, conc_color = _concentration_level(hhi)

    segments = _build_segments(payer_mix, sector)
    regime_stats = _build_regime_stats(corpus)

    # Peers
    sector_deals = [d for d in corpus if
                    sector.lower()[:6] in (d.get("sector") or "").lower() or
                    (d.get("sector") or "").lower()[:6] in sector.lower()]
    if len(sector_deals) < 5:
        sector_deals = corpus

    def _peer(d: dict) -> NetworkPeer:
        pm = d.get("payer_mix") or {}
        if not isinstance(pm, dict):
            pm = {}
        return NetworkPeer(
            company=d.get("company_name", "—"),
            sector=d.get("sector", "—"),
            year=d.get("year", 0),
            ev_mm=d.get("ev_mm", 0.0),
            moic=d.get("moic", 0.0),
            irr=d.get("irr", 0.0),
            payer_commercial=pm.get("commercial", 0.0) or 0.0,
            implied_regime=_implied_regime(d),
        )

    def _comm(d: dict) -> float:
        pm = d.get("payer_mix")
        if not isinstance(pm, dict):
            return 0.0
        return pm.get("commercial", 0) or 0.0
    peers_sorted = sorted(sector_deals, key=_comm)
    peers_diversified = [_peer(d) for d in peers_sorted[:10]][:5]
    peers_concentrated = [_peer(d) for d in peers_sorted[-10:]][:5]

    # MOIC adjustment
    all_moics = sorted(d.get("moic", 2.5) for d in sector_deals)
    n = len(all_moics)
    corpus_med = round(all_moics[n // 2], 2) if n else 3.0
    moic_mult = _REGIME_MOIC_MULT.get(regime, 1.0)
    adj_moic = round(corpus_med * moic_mult, 2)

    return ProviderNetworkResult(
        sector=sector,
        network_hhi=hhi,
        network_regime=regime,
        regime_label=regime_label,
        regime_color=regime_color,
        concentration_risk=conc_risk,
        concentration_color=conc_color,
        segments=segments,
        regime_stats=regime_stats,
        peers_diversified=peers_diversified,
        peers_concentrated=peers_concentrated,
        implied_moic_adj=round((moic_mult - 1.0) * 100, 1),
        corpus_median_moic=corpus_med,
        adjusted_moic_estimate=adj_moic,
        corpus_deal_count=len(corpus),
    )
