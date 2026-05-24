"""Cross-sector benchmark framework over the six live CMS verticals.

Normalizes the six already-vendored sector loaders (Home Health, Hospice,
SNF, Dialysis, IRF, LTCH) behind one interface so a state can be read across
every sector at once — the computation layer behind "show me the best SNF /
hospice / dialysis / home-health operators in Texas by quality percentile,
ownership profile, and local competition."

Honest by construction:
- Counts, means, quartiles, and percentile *ranks* over the public CMS files
  only. No synthetic data, no fabricated revenue, no external calls.
- "Concentration" is a Herfindahl-style index over **provider-count shares**
  (ownership or locality) — a *composition* proxy, NOT market share: CMS
  public data carries no true volume/revenue/patient denominator.
- Percentile is *peer deviation*, never an investment conclusion or causal
  claim. Every result carries its sample size, missingness, and caveats.
- Headline metrics differ in direction; lower-is-better metrics are excluded
  from the cross-sector headline so a "higher percentile = better" read holds.

This module lives in data/ and only calls other data/ loaders — it never
imports the ui/ layer (which sits above it).
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import dialysis, home_health, hospice, irf, ltch, snf

_UNKNOWN_OWNERSHIP = {"", "-", "—", "n/a", "not available", "not reported"}
_MIN_PERCENTILE_N = 5  # below this, percentile ranks are unreliable


@dataclass(frozen=True)
class SectorSpec:
    """How to read one vertical through the shared cross-sector lens."""
    id: str
    label: str
    route: str
    providers_loader: Callable[[], Dict[str, Any]]
    quality_loader: Callable[[], Dict[str, Dict[str, Optional[float]]]]
    name_attr: str
    locality_attr: str           # "county" for most; "city" for home health
    locality_label: str
    headline_key: str            # higher-is-better headline metric
    headline_label: str
    headline_suffix: str = ""


# Headline metric per vertical is deliberately the higher-is-better signal so
# the cross-sector percentile read is directionally consistent. (Dialysis/IRF/
# LTCH lower-is-better outcome rates stay on their own pages, not here.)
SECTORS: Tuple[SectorSpec, ...] = (
    SectorSpec("home-health", "Home Health", "/home-health",
               home_health.load_home_health_providers,
               home_health.load_home_health_quality,
               "provider_name", "city", "City",
               "star_rating", "Quality star rating"),
    SectorSpec("hospice", "Hospice", "/hospice",
               hospice.load_hospice_providers, hospice.load_hospice_quality,
               "facility_name", "county", "County",
               "care_index_overall", "Hospice Care Index"),
    SectorSpec("nursing-homes", "SNF / Nursing Home", "/nursing-homes",
               snf.load_snf_providers, snf.load_snf_quality,
               "provider_name", "county", "County",
               "overall_rating", "Overall star rating"),
    SectorSpec("dialysis", "Dialysis", "/dialysis",
               dialysis.load_dialysis_providers, dialysis.load_dialysis_quality,
               "facility_name", "county", "County",
               "five_star", "Overall 5-star rating"),
    SectorSpec("inpatient-rehab", "Inpatient Rehab (IRF)", "/inpatient-rehab",
               irf.load_irf_providers, irf.load_irf_quality,
               "provider_name", "county", "County",
               "dtc_rs_rate", "Discharge to community", "%"),
    SectorSpec("long-term-care-hospital", "LTCH", "/long-term-care-hospital",
               ltch.load_ltch_providers, ltch.load_ltch_quality,
               "provider_name", "county", "County",
               "dtc_rs_rate", "Discharge to community", "%"),
)

SECTOR_BY_ID: Dict[str, SectorSpec] = {s.id: s for s in SECTORS}


# ── small pure helpers (kept local to avoid importing the ui/ layer) ─────────

def _own_label(v: Any) -> str:
    s = (str(v) if v is not None else "").strip()
    return "Not reported" if s.lower() in _UNKNOWN_OWNERSHIP else s


def _hhi(shares_counts: List[int]) -> Optional[int]:
    """Herfindahl index (0–10000) over count shares — a composition proxy.

    NOT market share: there is no true volume/revenue denominator in CMS
    public data. Returns None when there is nothing to measure.
    """
    total = sum(shares_counts)
    if total <= 0:
        return None
    return round(sum((100.0 * c / total) ** 2 for c in shares_counts))


def _quantile(sorted_vals: List[float], q: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 2)
    idx = q * (len(sorted_vals) - 1)
    lo, hi = math.floor(idx), math.ceil(idx)
    if lo == hi:
        return round(sorted_vals[int(idx)], 2)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo), 2)


def _percentile_rank(sorted_vals: List[float], v: Optional[float]) -> Optional[int]:
    """Mid-rank percentile of ``v`` within ``sorted_vals`` (0–100)."""
    if v is None or not sorted_vals:
        return None
    below = sum(1 for x in sorted_vals if x < v)
    equal = sum(1 for x in sorted_vals if x == v)
    return round(100 * (below + 0.5 * equal) / len(sorted_vals))


# ── benchmark result ─────────────────────────────────────────────────────────

@dataclass
class SectorStateBenchmark:
    sector_id: str
    sector_label: str
    route: str
    state: str
    provider_count: int
    locality_count: int
    rated_count: int                       # providers with a headline value
    missingness_pct: Optional[float]       # share of providers missing headline
    headline_label: str
    headline_suffix: str
    headline_median: Optional[float]       # state median of headline metric
    national_median: Optional[float]
    state_percentile: Optional[int]        # rank of state median among states
    quartiles: Optional[Dict[str, Any]]    # state-level min/q1/median/q3/max
    ownership_mix: List[Tuple[str, int]]   # [(label, count)] desc
    ownership_hhi: Optional[int]           # composition proxy (0–10000)
    locality_hhi: Optional[int]            # composition proxy (0–10000)
    sample_size: int                       # == rated_count, surfaced explicitly
    caveats: List[str] = field(default_factory=list)


def _national_state_medians(spec: SectorSpec) -> Dict[str, float]:
    """Median headline value per state (states with >=1 rated provider)."""
    providers = spec.providers_loader()
    quality = spec.quality_loader()
    by_state: Dict[str, List[float]] = {}
    for ccn, p in providers.items():
        st = (getattr(p, "state", "") or "").strip().upper()
        if not st:
            continue
        v = (quality.get(ccn) or {}).get(spec.headline_key)
        if v is not None:
            by_state.setdefault(st, []).append(v)
    out: Dict[str, float] = {}
    for st, vals in by_state.items():
        vals.sort()
        m = _quantile(vals, 0.5)
        if m is not None:
            out[st] = m
    return out


def sector_state_benchmark(sector_id: str, state: str) -> Optional[SectorStateBenchmark]:
    """Cross-sector benchmark for one vertical in one state (None if no data)."""
    spec = SECTOR_BY_ID.get(sector_id)
    if spec is None:
        return None
    st = (state or "").strip().upper()
    providers = spec.providers_loader()
    quality = spec.quality_loader()
    members = [(ccn, p) for ccn, p in providers.items()
               if (getattr(p, "state", "") or "").strip().upper() == st]
    if not members:
        return None

    localities = [(getattr(p, spec.locality_attr, "") or "").strip()
                  for _, p in members]
    locality_counts = Counter(loc for loc in localities if loc)

    vals = sorted(v for v in ((quality.get(ccn) or {}).get(spec.headline_key)
                              for ccn, _ in members) if v is not None)
    rated = len(vals)
    count = len(members)
    missingness = round(100 * (count - rated) / count, 1) if count else None

    quartiles = None
    headline_median = None
    if vals:
        headline_median = _quantile(vals, 0.5)
        quartiles = {
            "n": rated, "min": round(vals[0], 2), "max": round(vals[-1], 2),
            "q1": _quantile(vals, 0.25), "median": headline_median,
            "q3": _quantile(vals, 0.75),
        }

    state_medians = _national_state_medians(spec)
    national_vals = sorted(state_medians.values())
    national_median = _quantile(national_vals, 0.5) if national_vals else None
    state_percentile = _percentile_rank(national_vals, state_medians.get(st))

    own = Counter(_own_label(getattr(p, "ownership", "")) for _, p in members)
    ownership_mix = own.most_common()
    ownership_hhi = _hhi([c for _, c in ownership_mix])
    locality_hhi = _hhi(list(locality_counts.values())) if locality_counts else None

    caveats: List[str] = []
    if rated < _MIN_PERCENTILE_N:
        caveats.append(
            f"Only {rated} rated provider(s) in {st} — percentile and median "
            "are unreliable at this sample size.")
    if missingness and missingness >= 25:
        caveats.append(
            f"{missingness:g}% of {st} providers have no headline value — "
            "read the median with that missingness in mind.")
    if locality_hhi is not None and locality_hhi >= 2500:
        caveats.append(
            "Provider counts are concentrated in few localities (composition "
            "proxy, not market share).")
    caveats.append("CMS public quality only — not commercial revenue, payer "
                   "mix, or census; percentile is peer deviation, not a "
                   "recommendation or a causal claim.")

    return SectorStateBenchmark(
        sector_id=spec.id, sector_label=spec.label, route=spec.route, state=st,
        provider_count=count, locality_count=len(locality_counts),
        rated_count=rated, missingness_pct=missingness,
        headline_label=spec.headline_label, headline_suffix=spec.headline_suffix,
        headline_median=headline_median, national_median=national_median,
        state_percentile=state_percentile, quartiles=quartiles,
        ownership_mix=ownership_mix, ownership_hhi=ownership_hhi,
        locality_hhi=locality_hhi, sample_size=rated, caveats=caveats,
    )


def cross_sector_state_summary(state: str) -> List[SectorStateBenchmark]:
    """All six verticals' benchmarks for one state, sectors with data only."""
    out = []
    for spec in SECTORS:
        b = sector_state_benchmark(spec.id, state)
        if b is not None:
            out.append(b)
    return out
