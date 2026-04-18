"""Sector Correlation Analytics — cross-sector MOIC correlations from the corpus.

Computes vintage-year MOIC time series for each sector and then calculates
pairwise Pearson correlations. Reveals natural diversifiers and correlated sectors
for portfolio construction.

Note: Since deals are discrete events not continuous time series, we bin by
vintage year and compute average MOIC per (sector, year) cell, then correlate
the resulting time vectors. Sectors with fewer than 3 vintage-year observations
are excluded from the correlation matrix.
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
    for i in range(2, 47):
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


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    """Pearson r on aligned paired lists."""
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x < 1e-9 or den_y < 1e-9:
        return None
    return round(num / (den_x * den_y), 3)


@dataclass
class SectorTimeSeries:
    sector: str
    years: List[int]
    avg_moics: List[float]   # avg MOIC per year
    n_deals: int
    overall_moic_p50: Optional[float]


@dataclass
class SectorPair:
    sector_a: str
    sector_b: str
    correlation: float
    n_overlap_years: int


@dataclass
class SectorCorrelationResult:
    sectors: List[str]         # ordered list
    matrix: Dict[Tuple[str, str], float]  # (a, b) -> r
    time_series: List[SectorTimeSeries]
    top_pairs_positive: List[SectorPair]   # most correlated (diversification risk)
    top_pairs_negative: List[SectorPair]   # least correlated / anti-correlated (best diversifiers)
    all_years: List[int]


def compute_sector_correlation(
    min_sector_deals: int = 5,
    min_overlap_years: int = 3,
) -> SectorCorrelationResult:
    corpus = _load_corpus()

    from collections import defaultdict

    # Build (sector, year) -> [moic]
    cell: Dict[Tuple[str, int], List[float]] = defaultdict(list)
    sector_deal_counts: Dict[str, int] = defaultdict(int)

    for d in corpus:
        m = _moic(d)
        if m is None:
            continue
        sec = (d.get("sector") or "Unknown").strip()
        yr = d.get("year")
        if not yr:
            continue
        try:
            yr = int(yr)
        except (TypeError, ValueError):
            continue
        cell[(sec, yr)].append(m)
        sector_deal_counts[sec] += 1

    # Filter to sectors with enough deals
    eligible_sectors = sorted(
        [s for s, n in sector_deal_counts.items() if n >= min_sector_deals]
    )

    all_years = sorted({yr for (sec, yr) in cell if sec in eligible_sectors})

    # Build time series per sector
    ts_map: Dict[str, SectorTimeSeries] = {}
    for sec in eligible_sectors:
        yr_moics = [
            (yr, sum(cell[(sec, yr)]) / len(cell[(sec, yr)]))
            for yr in all_years
            if cell.get((sec, yr))
        ]
        if not yr_moics:
            continue
        years = [ym[0] for ym in yr_moics]
        avg_moics = [ym[1] for ym in yr_moics]
        all_m = sorted([m for yr in all_years for m in cell.get((sec, yr), [])])
        p50_idx = len(all_m) // 2
        ts_map[sec] = SectorTimeSeries(
            sector=sec,
            years=years,
            avg_moics=avg_moics,
            n_deals=sector_deal_counts[sec],
            overall_moic_p50=round(all_m[p50_idx], 3) if all_m else None,
        )

    eligible_with_ts = [s for s in eligible_sectors if s in ts_map]

    # Compute pairwise correlations
    matrix: Dict[Tuple[str, str], float] = {}
    pairs: List[SectorPair] = []

    for i, a in enumerate(eligible_with_ts):
        for j, b in enumerate(eligible_with_ts):
            if i >= j:
                continue
            ts_a = ts_map[a]
            ts_b = ts_map[b]
            # Find overlapping years
            years_a = set(ts_a.years)
            years_b = set(ts_b.years)
            common = sorted(years_a & years_b)
            if len(common) < min_overlap_years:
                continue
            xs = [ts_a.avg_moics[ts_a.years.index(yr)] for yr in common]
            ys = [ts_b.avg_moics[ts_b.years.index(yr)] for yr in common]
            r = _pearson(xs, ys)
            if r is None:
                continue
            matrix[(a, b)] = r
            matrix[(b, a)] = r
            pairs.append(SectorPair(a, b, r, len(common)))

    pairs.sort(key=lambda p: p.correlation)
    top_neg = pairs[:10]
    top_pos = list(reversed(pairs[-10:]))

    return SectorCorrelationResult(
        sectors=eligible_with_ts,
        matrix=matrix,
        time_series=list(ts_map.values()),
        top_pairs_positive=top_pos,
        top_pairs_negative=top_neg,
        all_years=all_years,
    )
