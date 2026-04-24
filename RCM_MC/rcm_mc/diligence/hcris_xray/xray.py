"""Peer-matching engine for HCRIS X-Ray.

Given a target hospital (by CCN or by a manual profile), find the
N best-matching peers from the 17,000+ HCRIS filings and compute
per-metric variance vs the peer median / P25 / P75.

Peer-matching heuristics (weighted):

    * **Bed count** — same size cohort (MICRO / COMMUNITY /
      REGIONAL / ACADEMIC), tight bed-count band (±30%)
    * **Geography** — same state first; same Census region
      fallback; any-region last
    * **Payer mix** — Medicare day share within ±10pp
    * **Fiscal year** — most recent filing year, falling back
      to previous years if not enough peers in same year

The match score is a weighted L1 distance across these features;
lower = better. Returns the top-K peers sorted ascending.

Why these weights: PE partners benchmark against hospitals of the
same operating archetype, not hospitals that happen to have
similar revenue. A 300-bed Alabama community hospital is
comparable to other 275-325-bed community hospitals in the
Southeast with 45-65% Medicare; the $5B Cleveland Clinic is not
a peer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .metrics import (
    HospitalMetrics, METRIC_CATALOG, MetricSpec,
    _size_cohort, compute_metrics,
)


# Census regions — rough US regional grouping for peer fallback
_CENSUS_REGION: Dict[str, str] = {
    # Northeast
    "CT": "NE", "ME": "NE", "MA": "NE", "NH": "NE",
    "RI": "NE", "VT": "NE", "NJ": "NE", "NY": "NE",
    "PA": "NE",
    # Midwest
    "IL": "MW", "IN": "MW", "MI": "MW", "OH": "MW",
    "WI": "MW", "IA": "MW", "KS": "MW", "MN": "MW",
    "MO": "MW", "NE": "MW", "ND": "MW", "SD": "MW",
    # South
    "DE": "S", "FL": "S", "GA": "S", "MD": "S",
    "NC": "S", "SC": "S", "VA": "S", "DC": "S",
    "WV": "S", "AL": "S", "KY": "S", "MS": "S",
    "TN": "S", "AR": "S", "LA": "S", "OK": "S",
    "TX": "S",
    # West
    "AZ": "W", "CO": "W", "ID": "W", "MT": "W",
    "NV": "W", "NM": "W", "UT": "W", "WY": "W",
    "AK": "W", "CA": "W", "HI": "W", "OR": "W",
    "WA": "W",
}


# ────────────────────────────────────────────────────────────────────
# Result types
# ────────────────────────────────────────────────────────────────────

@dataclass
class PeerMatch:
    """One matched peer hospital + the distance to the target."""
    hospital: HospitalMetrics
    distance: float
    same_state: bool
    same_region: bool
    same_size_cohort: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hospital": self.hospital.to_dict(),
            "distance": self.distance,
            "same_state": self.same_state,
            "same_region": self.same_region,
            "same_size_cohort": self.same_size_cohort,
        }


@dataclass
class MetricBenchmark:
    """Per-metric target vs peer stats."""
    spec: MetricSpec
    target_value: float
    peer_p25: float
    peer_median: float
    peer_p75: float
    peer_n: int
    variance_vs_median: float     # signed delta (positive = above median)
    variance_vs_median_pct: float
    verdict: str                  # "above peer" / "inside peer band" / "below peer"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attr": self.spec.attr,
            "label": self.spec.label,
            "category": self.spec.category,
            "higher_is_better": self.spec.higher_is_better,
            "target_value": self.target_value,
            "peer_p25": self.peer_p25,
            "peer_median": self.peer_median,
            "peer_p75": self.peer_p75,
            "peer_n": self.peer_n,
            "variance_vs_median": self.variance_vs_median,
            "variance_vs_median_pct": self.variance_vs_median_pct,
            "verdict": self.verdict,
        }


@dataclass
class XRayReport:
    """Top-level output."""
    target: HospitalMetrics
    peers: List[PeerMatch] = field(default_factory=list)
    metrics: List[MetricBenchmark] = field(default_factory=list)
    target_history: List[HospitalMetrics] = field(default_factory=list)
    headline: str = ""
    above_peer_count: int = 0
    below_peer_count: int = 0
    inside_peer_count: int = 0
    peer_filter_used: str = ""             # description of matching criteria
    trend_signal: str = ""                 # "improving" / "deteriorating" / "flat"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target.to_dict(),
            "peers": [p.to_dict() for p in self.peers],
            "metrics": [m.to_dict() for m in self.metrics],
            "target_history": [
                h.to_dict() for h in self.target_history
            ],
            "headline": self.headline,
            "above_peer_count": self.above_peer_count,
            "below_peer_count": self.below_peer_count,
            "inside_peer_count": self.inside_peer_count,
            "peer_filter_used": self.peer_filter_used,
            "trend_signal": self.trend_signal,
        }


# ────────────────────────────────────────────────────────────────────
# Data loading (cached)
# ────────────────────────────────────────────────────────────────────

_METRICS_CACHE: Optional[List[HospitalMetrics]] = None


def load_all_metrics() -> List[HospitalMetrics]:
    """Load every HCRIS row into HospitalMetrics, cached across calls."""
    global _METRICS_CACHE
    if _METRICS_CACHE is not None:
        return _METRICS_CACHE
    from ...data.hcris import load_hcris
    df = load_hcris()
    out: List[HospitalMetrics] = []
    for row in df.to_dict(orient="records"):
        m = compute_metrics(row)
        # Drop hopelessly-empty rows
        if m.beds <= 0 or m.net_patient_revenue <= 0:
            continue
        out.append(m)
    _METRICS_CACHE = out
    return out


def get_target_history(ccn: str) -> List[HospitalMetrics]:
    """Return all years of HCRIS filings for a single CCN, oldest
    first.  Used for per-metric trend sparklines in the X-Ray UI."""
    if not ccn:
        return []
    out = [h for h in load_all_metrics() if h.ccn == ccn]
    out.sort(key=lambda h: h.fiscal_year)
    return out


def find_hospital(
    query: str,
    state: Optional[str] = None,
    year: Optional[int] = None,
) -> Optional[HospitalMetrics]:
    """Find one hospital by CCN or name substring.

    When multiple filings match (different years), prefer the most
    recent; when multiple hospitals match, prefer state-filtered
    match; else return the first by name.
    """
    q = (query or "").strip()
    if not q:
        return None
    all_m = load_all_metrics()
    candidates: List[HospitalMetrics] = []
    q_upper = q.upper()
    for h in all_m:
        if state and h.state.upper() != state.upper():
            continue
        if year and h.fiscal_year != year:
            continue
        if h.ccn == q:
            candidates.append(h)
        elif q_upper in h.name.upper():
            candidates.append(h)
    if not candidates:
        return None
    # Prefer most recent filing
    candidates.sort(key=lambda h: h.fiscal_year, reverse=True)
    return candidates[0]


# ────────────────────────────────────────────────────────────────────
# Peer matching
# ────────────────────────────────────────────────────────────────────

def _feature_distance(
    target: HospitalMetrics,
    peer: HospitalMetrics,
) -> float:
    """Weighted L1 distance across peer-match features.  Lower is
    more similar.  Returns a positive float (not normalized)."""
    dist = 0.0
    # Bed distance (normalized by target bed count, weight 3)
    if target.beds > 0:
        dist += 3.0 * abs(peer.beds - target.beds) / target.beds
    # Medicare day share distance (weight 2)
    dist += 2.0 * abs(peer.medicare_day_pct - target.medicare_day_pct)
    # Medicaid day share distance (weight 1)
    dist += 1.0 * abs(peer.medicaid_day_pct - target.medicaid_day_pct)
    # Occupancy rate distance (weight 1)
    dist += 1.0 * abs(peer.occupancy_rate - target.occupancy_rate)
    return dist


def find_peers(
    target: HospitalMetrics,
    k: int = 50,
    prefer_same_state: bool = True,
    prefer_same_year: bool = True,
    bed_band_pct: float = 0.30,
) -> Tuple[List[PeerMatch], str]:
    """Find the top-K peer hospitals for the target.

    Filter hierarchy:
        1. Same size cohort AND (beds ± bed_band_pct × target_beds)
        2. Same state (when prefer_same_state=True); broadens to
           same Census region if fewer than 10 peers found
        3. Same fiscal year (when prefer_same_year=True); broadens
           to any year if fewer than 10 peers found
        4. Target itself excluded

    Returns (peers, filter_description).
    """
    all_m = load_all_metrics()
    target_region = _CENSUS_REGION.get(target.state.upper(), "")
    bed_min = target.beds * (1.0 - bed_band_pct)
    bed_max = target.beds * (1.0 + bed_band_pct)

    def _pool(
        require_state: bool, require_region: bool,
        require_year: bool,
    ) -> List[HospitalMetrics]:
        pool: List[HospitalMetrics] = []
        for h in all_m:
            if h.ccn == target.ccn and h.fiscal_year == target.fiscal_year:
                continue
            if h.size_cohort != target.size_cohort:
                continue
            if h.beds < bed_min or h.beds > bed_max:
                continue
            if require_state and h.state.upper() != target.state.upper():
                continue
            if require_region and _CENSUS_REGION.get(
                h.state.upper(), "",
            ) != target_region:
                continue
            if require_year and h.fiscal_year != target.fiscal_year:
                continue
            pool.append(h)
        return pool

    # Progressive broadening
    filter_tiers = [
        (True, True, True, "same-state + same-year"),
        (True, True, False, "same-state, any year"),
        (False, True, True, "same-region + same-year"),
        (False, True, False, "same-region, any year"),
        (False, False, True, "national + same-year"),
        (False, False, False, "national, any year"),
    ]
    pool: List[HospitalMetrics] = []
    filter_desc = ""
    for rs, rr, ry, desc in filter_tiers:
        pool = _pool(rs, rr, ry)
        if len(pool) >= 10:
            filter_desc = desc
            break
    if not pool:
        return [], "no peers found"

    # Rank by feature distance
    scored = [
        (_feature_distance(target, p), p) for p in pool
    ]
    scored.sort(key=lambda t: t[0])
    matches: List[PeerMatch] = []
    for d, p in scored[:k]:
        matches.append(PeerMatch(
            hospital=p,
            distance=d,
            same_state=(p.state.upper() == target.state.upper()),
            same_region=(
                _CENSUS_REGION.get(p.state.upper(), "")
                == target_region
            ),
            same_size_cohort=(p.size_cohort == target.size_cohort),
        ))
    return matches, f"{filter_desc} · {len(pool)} pool, top {len(matches)} shown"


# ────────────────────────────────────────────────────────────────────
# Per-metric benchmark math
# ────────────────────────────────────────────────────────────────────

def _percentile(xs: List[float], q: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    idx = int(q * (len(s) - 1))
    return s[max(0, min(len(s) - 1, idx))]


def compute_benchmarks(
    target: HospitalMetrics,
    peers: List[PeerMatch],
) -> List[MetricBenchmark]:
    """Compute per-metric target-vs-peer comparison."""
    out: List[MetricBenchmark] = []
    for spec in METRIC_CATALOG:
        target_val = float(getattr(target, spec.attr, 0.0) or 0.0)
        peer_vals = [
            float(getattr(p.hospital, spec.attr, 0.0) or 0.0)
            for p in peers
        ]
        # Drop zero/null values that would skew percentiles
        # (especially for ratios where 0 means "undefined")
        if spec.attr in (
            "occupancy_rate", "contractual_allowance_rate",
            "net_to_gross_ratio", "operating_margin_on_npr",
            "net_income_margin_on_npr", "payer_diversity_index",
        ):
            peer_vals = [v for v in peer_vals if v != 0]
        if not peer_vals:
            continue
        p25 = _percentile(peer_vals, 0.25)
        med = _percentile(peer_vals, 0.50)
        p75 = _percentile(peer_vals, 0.75)
        variance = target_val - med
        variance_pct = (
            variance / abs(med) if abs(med) > 1e-9 else 0.0
        )
        if target_val > p75:
            verdict = "above peer P75"
        elif target_val < p25:
            verdict = "below peer P25"
        else:
            verdict = "inside peer P25-P75 band"
        out.append(MetricBenchmark(
            spec=spec,
            target_value=target_val,
            peer_p25=p25,
            peer_median=med,
            peer_p75=p75,
            peer_n=len(peer_vals),
            variance_vs_median=variance,
            variance_vs_median_pct=variance_pct,
            verdict=verdict,
        ))
    return out


# ────────────────────────────────────────────────────────────────────
# Full X-Ray
# ────────────────────────────────────────────────────────────────────

def xray(
    *,
    ccn: Optional[str] = None,
    name: Optional[str] = None,
    state: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    peer_k: int = 50,
    bed_band_pct: float = 0.30,
    manual_target: Optional[HospitalMetrics] = None,
) -> Optional[XRayReport]:
    """One-shot X-Ray: find target → find peers → compute benchmarks.

    At least one of ``ccn``, ``name``, or ``manual_target`` must
    be supplied.
    """
    target: Optional[HospitalMetrics] = manual_target
    if target is None:
        query = ccn or name
        if not query:
            return None
        target = find_hospital(query, state=state, year=fiscal_year)
    if target is None:
        return None

    peers, filter_desc = find_peers(
        target, k=peer_k, bed_band_pct=bed_band_pct,
    )
    benchmarks = compute_benchmarks(target, peers)
    history = get_target_history(target.ccn)

    # Trend signal — direction of operating margin across years
    trend_signal = ""
    if len(history) >= 2:
        first_m = history[0].operating_margin_on_npr
        last_m = history[-1].operating_margin_on_npr
        delta = last_m - first_m
        if abs(delta) < 0.01:
            trend_signal = "flat"
        elif delta > 0:
            trend_signal = "improving"
        else:
            trend_signal = "deteriorating"

    # Verdict rollup
    above = below = inside = 0
    for bm in benchmarks:
        if bm.verdict.startswith("above"):
            # "above peer" is GOOD only when higher_is_better; else BAD
            if bm.spec.higher_is_better:
                above += 1
            else:
                below += 1
        elif bm.verdict.startswith("below"):
            if bm.spec.higher_is_better:
                below += 1
            else:
                above += 1
        else:
            inside += 1

    # Partner-voice headline
    if not peers:
        headline = (
            f"{target.name} ({target.ccn}): no peer group found. "
            f"{target.beds} beds in {target.state} is outside the "
            f"matchable cohort."
        )
    else:
        headline = (
            f"{target.name} ({target.ccn}, "
            f"{target.beds} beds, {target.state}) benchmarked against "
            f"{len(peers)} peer hospitals ({filter_desc}). "
            f"Outperforms peers on {above} metrics · "
            f"underperforms on {below} · "
            f"in-band on {inside}."
        )

    return XRayReport(
        target=target,
        peers=peers,
        metrics=benchmarks,
        target_history=history,
        headline=headline,
        above_peer_count=above,
        below_peer_count=below,
        inside_peer_count=inside,
        peer_filter_used=filter_desc,
        trend_signal=trend_signal,
    )


# ────────────────────────────────────────────────────────────────────
# Aggregate summary stats (used by the landing/search UI)
# ────────────────────────────────────────────────────────────────────

def dataset_summary() -> Dict[str, Any]:
    """Quick summary of the HCRIS dataset for landing pages."""
    all_m = load_all_metrics()
    by_state: Dict[str, int] = {}
    by_year: Dict[int, int] = {}
    by_cohort: Dict[str, int] = {}
    for h in all_m:
        by_state[h.state] = by_state.get(h.state, 0) + 1
        by_year[h.fiscal_year] = by_year.get(h.fiscal_year, 0) + 1
        by_cohort[h.size_cohort] = by_cohort.get(h.size_cohort, 0) + 1
    return {
        "total_rows": len(all_m),
        "states": dict(sorted(
            by_state.items(), key=lambda kv: -kv[1],
        )),
        "years": dict(sorted(
            by_year.items(),
        )),
        "cohorts": dict(sorted(
            by_cohort.items(), key=lambda kv: -kv[1],
        )),
    }


def search_hospitals(
    query: str, limit: int = 20,
    state: Optional[str] = None,
    cohort: Optional[str] = None,
) -> List[HospitalMetrics]:
    """Name / CCN / city substring search for the landing UI."""
    q = (query or "").strip().upper()
    out: List[HospitalMetrics] = []
    for h in load_all_metrics():
        if state and h.state.upper() != state.upper():
            continue
        if cohort and h.size_cohort != cohort:
            continue
        if q:
            if (q not in h.name.upper() and q not in h.ccn
                    and q not in h.city.upper()):
                continue
        out.append(h)
        if len(out) >= limit * 3:
            # Collect a superset; we'll dedupe + sort below
            break
    # Keep one row per CCN (most-recent filing wins)
    dedupe: Dict[str, HospitalMetrics] = {}
    for h in out:
        existing = dedupe.get(h.ccn)
        if existing is None or h.fiscal_year > existing.fiscal_year:
            dedupe[h.ccn] = h
    final = sorted(
        dedupe.values(),
        key=lambda h: (-h.fiscal_year, -h.beds, h.name),
    )[:limit]
    return final
