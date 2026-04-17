"""Portfolio Scenario Simulator — stress test a custom portfolio against macro scenarios.

Takes a user-defined portfolio (list of sector weights and EV sizes) and simulates
expected MOIC distribution under different scenarios:
  1. Base Case (corpus median conditions)
  2. Recession (government rate cuts, commercial volume drop, multiple compression)
  3. Rate Shock (higher borrowing costs, multiple compression, exit discount)
  4. Payer Shift (commercial→government migration, lower revenue yield)
  5. Bull Case (multiple expansion, commercial rate increases)

Scenario shocks are calibrated against corpus regression of macro variables vs MOIC.
"""
from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 49):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _moic(d: Dict[str, Any]) -> Optional[float]:
    for k in ("moic", "realized_moic"):
        v = d.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = max(0, min(len(s) - 1, int(p * (len(s) - 1))))
    return round(s[idx], 3)


# Scenario macro shocks — calibrated to rough PE literature estimates
# Each entry: (name, moic_multiplier, moic_shift, description)
# moic_multiplier: scales realized MOIC (e.g., 0.90 = 10% reduction)
# moic_shift: absolute additive adjustment (e.g., -0.3 = -0.3x)
SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "base",
        "label": "Base Case",
        "description": "Corpus median conditions — typical healthcare PE environment",
        "moic_mult": 1.00,
        "moic_shift": 0.00,
        "ee_shift": 0.0,
        "color": "#3b82f6",
    },
    {
        "id": "recession",
        "label": "Recession",
        "description": "GDP contraction, volume decline, CMS rate pressure, exit multiple compression −2×",
        "moic_mult": 0.82,
        "moic_shift": -0.30,
        "ee_shift": -2.0,
        "color": "#ef4444",
    },
    {
        "id": "rate_shock",
        "label": "Rate Shock",
        "description": "Fed funds +300bps, leverage costs rise, exit multiples compress −1.5×",
        "moic_mult": 0.88,
        "moic_shift": -0.15,
        "ee_shift": -1.5,
        "color": "#f97316",
    },
    {
        "id": "payer_shift",
        "label": "Payer Shift",
        "description": "Commercial→government migration, Medicare MA growth, revenue yield compression",
        "moic_mult": 0.93,
        "moic_shift": -0.10,
        "ee_shift": 0.0,
        "color": "#f59e0b",
    },
    {
        "id": "bull",
        "label": "Bull Case",
        "description": "Multiple expansion, commercial rate increases, favorable exit environment",
        "moic_mult": 1.12,
        "moic_shift": +0.25,
        "ee_shift": +1.5,
        "color": "#10b981",
    },
]


@dataclass
class PortfolioPosition:
    sector: str
    weight: float        # 0–1, portfolio weight by EV
    ev_mm: float
    base_moic_p50: Optional[float]
    base_moic_p25: Optional[float]
    base_moic_p75: Optional[float]
    n_peers: int


@dataclass
class ScenarioResult:
    scenario_id: str
    label: str
    description: str
    color: str
    portfolio_moic_p25: float
    portfolio_moic_p50: float
    portfolio_moic_p75: float
    position_moics: List[float]   # per-position expected MOIC


@dataclass
class PortfolioSimResult:
    positions: List[PortfolioPosition]
    scenarios: List[ScenarioResult]
    corpus_p50: Optional[float]
    total_ev_mm: float
    n_positions: int


def _sector_moic_stats(corpus: List[Dict[str, Any]], sector: str) -> Tuple[Optional[float], Optional[float], Optional[float], int]:
    """P25, P50, P75 MOIC and n for a given sector from corpus."""
    peers = []
    for d in corpus:
        m = _moic(d)
        if m is None:
            continue
        dsec = (d.get("sector") or "").lower()
        q = sector.lower()
        words = set(q.split())
        dwords = set(dsec.split())
        if q in dsec or (words & dwords):
            peers.append(m)
    if not peers:
        # Fallback to all corpus
        peers = [_moic(d) for d in corpus if _moic(d) is not None]
    peers.sort()
    return (
        _percentile(peers, 0.25),
        _percentile(peers, 0.50),
        _percentile(peers, 0.75),
        len(peers),
    )


def compute_portfolio_sim(
    positions: List[Dict[str, Any]],
) -> PortfolioSimResult:
    """
    positions: list of {"sector": str, "ev_mm": float} dicts
    """
    corpus = _load_corpus()

    all_moics = sorted([_moic(d) for d in corpus if _moic(d) is not None])
    corpus_p50 = _percentile(all_moics, 0.50)

    total_ev = sum(float(p.get("ev_mm") or 0) for p in positions)
    if total_ev <= 0:
        total_ev = 1.0

    # Build position objects
    pos_objs: List[PortfolioPosition] = []
    for p in positions:
        sector = p.get("sector") or "Unknown"
        ev = float(p.get("ev_mm") or 100.0)
        weight = ev / total_ev
        p25, p50, p75, n = _sector_moic_stats(corpus, sector)
        pos_objs.append(PortfolioPosition(
            sector=sector,
            weight=weight,
            ev_mm=ev,
            base_moic_p50=p50,
            base_moic_p25=p25,
            base_moic_p75=p75,
            n_peers=n,
        ))

    # For each scenario, compute weighted-average portfolio MOIC distribution
    scenario_results: List[ScenarioResult] = []
    for sc in SCENARIOS:
        mult = sc["moic_mult"]
        shift = sc["moic_shift"]

        position_moics: List[float] = []
        weighted_p25 = 0.0
        weighted_p50 = 0.0
        weighted_p75 = 0.0

        for pos in pos_objs:
            base_p25 = pos.base_moic_p25 or (corpus_p50 or 2.5) - 0.5
            base_p50 = pos.base_moic_p50 or (corpus_p50 or 2.5)
            base_p75 = pos.base_moic_p75 or (corpus_p50 or 2.5) + 0.5

            stressed_p50 = max(0.5, round(base_p50 * mult + shift, 3))
            stressed_p25 = max(0.3, round(base_p25 * mult + shift * 0.8, 3))
            stressed_p75 = max(0.7, round(base_p75 * mult + shift * 1.2, 3))

            position_moics.append(stressed_p50)
            weighted_p25 += stressed_p25 * pos.weight
            weighted_p50 += stressed_p50 * pos.weight
            weighted_p75 += stressed_p75 * pos.weight

        scenario_results.append(ScenarioResult(
            scenario_id=sc["id"],
            label=sc["label"],
            description=sc["description"],
            color=sc["color"],
            portfolio_moic_p25=round(weighted_p25, 3),
            portfolio_moic_p50=round(weighted_p50, 3),
            portfolio_moic_p75=round(weighted_p75, 3),
            position_moics=position_moics,
        ))

    return PortfolioSimResult(
        positions=pos_objs,
        scenarios=scenario_results,
        corpus_p50=corpus_p50,
        total_ev_mm=total_ev,
        n_positions=len(pos_objs),
    )


# Default example portfolio if no input provided
DEFAULT_PORTFOLIO = [
    {"sector": "Behavioral Health", "ev_mm": 250.0},
    {"sector": "Physician Practice Management", "ev_mm": 400.0},
    {"sector": "Ambulatory Surgery Center", "ev_mm": 180.0},
    {"sector": "Home Health", "ev_mm": 320.0},
    {"sector": "Revenue Cycle Management", "ev_mm": 150.0},
]
