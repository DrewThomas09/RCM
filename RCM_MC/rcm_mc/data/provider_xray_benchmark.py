"""CMS Provider X-Ray — multi-peer-set benchmarks + transparent risk indicators.

Deepens the X-Ray with the peer sets the original spec called for — **national,
state, locality, and ownership** percentiles per metric (not just same-state) —
and a **risk-indicator** layer.

Honesty on "predictors": these are **transparent, rule-based leading-risk
indicators computed from the current CMS snapshot — NOT trained predictive
models or forecasts.** Real forecasting needs longitudinal labels PEdesk does
not yet have (single dated snapshots; see PEDESK_PREDICTION_READINESS.md). Every
indicator exposes the components it is built from; none claims a probability,
an outcome, or causation.

Reuses the existing loaders (via cross_sector) and the higher-is-better metric
map (via investable_evidence) — no new data, no external calls.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .cross_sector import SECTOR_BY_ID, SectorSpec
from .investable_evidence import _QUALITY_METRICS

_MIN_N = 5  # below this, percentile / z-score are unreliable → suppressed

# Honest framing surfaced wherever risk indicators are shown.
RISK_INDICATOR_DISCLAIMER = (
    "Risk indicators are transparent, rule-based leading signals computed from "
    "the current CMS snapshot — NOT trained predictive models, probabilities, "
    "or forecasts. Forecasting would require longitudinal labels PEdesk does "
    "not yet have (the data is single-snapshot). Each indicator below shows "
    "the observed components it is built from; none implies causation or an "
    "investment recommendation."
)

ELEVATED, MODERATE, LOW, INSUFFICIENT = "elevated", "moderate", "low", "insufficient"


@dataclass(frozen=True)
class PeerPercentile:
    peer_set: str               # national | state | locality | ownership
    label: str                  # human label incl. the peer descriptor
    percentile: Optional[int]   # 0–100, higher = better; None if suppressed
    peer_n: int
    suppressed: bool            # True when peer_n < _MIN_N


@dataclass(frozen=True)
class MetricBenchmark:
    key: str
    label: str
    suffix: str
    value: Optional[float]
    direction: str              # "higher_is_better"
    percentiles: List[PeerPercentile]
    z_state: Optional[float]    # guarded z-score within the state peer set


@dataclass(frozen=True)
class RiskIndicator:
    name: str
    level: str                  # elevated | moderate | low | insufficient
    basis: str                  # the observed components it is built from


@dataclass
class ProviderBenchmarkBundle:
    sector_id: str
    ccn: str
    metrics: List[MetricBenchmark] = field(default_factory=list)
    risk_indicators: List[RiskIndicator] = field(default_factory=list)
    disclaimer: str = RISK_INDICATOR_DISCLAIMER


def _percentile_rank(sorted_vals: List[float], v: Optional[float]) -> Optional[int]:
    if v is None or not sorted_vals:
        return None
    below = sum(1 for x in sorted_vals if x < v)
    equal = sum(1 for x in sorted_vals if x == v)
    return round(100 * (below + 0.5 * equal) / len(sorted_vals))


def _z(vals: List[float], v: Optional[float]) -> Optional[float]:
    if v is None or len(vals) < _MIN_N:
        return None
    mean = sum(vals) / len(vals)
    sd = math.sqrt(sum((x - mean) ** 2 for x in vals) / len(vals))
    return round((v - mean) / sd, 2) if sd > 0 else None


def _peer_values(quality: Dict, ccns, key: str) -> List[float]:
    return sorted(v for v in ((quality.get(c) or {}).get(key) for c in ccns)
                  if v is not None)


def _peer_pct(quality, ccns, key, value, peer_set, label) -> PeerPercentile:
    vals = _peer_values(quality, ccns, key)
    n = len(vals)
    if n < _MIN_N:
        return PeerPercentile(peer_set, label, None, n, True)
    return PeerPercentile(peer_set, label, _percentile_rank(vals, value), n, False)


def metric_benchmarks(sector_id: str, ccn: str) -> List[MetricBenchmark]:
    """Per-metric percentiles across national / state / locality / ownership."""
    spec: Optional[SectorSpec] = SECTOR_BY_ID.get(sector_id)
    if spec is None:
        return []
    providers = spec.providers_loader()
    quality = spec.quality_loader()
    me = providers.get(ccn)
    if me is None:
        return []
    state = (getattr(me, "state", "") or "").upper()
    loc_attr = spec.locality_attr
    my_loc = (getattr(me, loc_attr, "") or "").strip().lower()
    my_own = (getattr(me, "ownership", "") or "").strip().lower()

    # Pre-bucket CCNs once.
    nat = list(providers)
    st = [c for c, p in providers.items()
          if (getattr(p, "state", "") or "").upper() == state]
    loc = [c for c, p in providers.items()
           if (getattr(p, "state", "") or "").upper() == state
           and (getattr(p, loc_attr, "") or "").strip().lower() == my_loc] if my_loc else []
    own = [c for c, p in providers.items()
           if (getattr(p, "ownership", "") or "").strip().lower() == my_own] if my_own else []

    metrics = _QUALITY_METRICS.get(sector_id,
                                   [(spec.headline_key, spec.headline_label,
                                     spec.headline_suffix)])
    out: List[MetricBenchmark] = []
    own_q = quality.get(ccn) or {}
    loc_label = spec.locality_label
    for key, label, suffix in metrics:
        val = own_q.get(key)
        pcts = [
            _peer_pct(quality, nat, key, val, "national", "National"),
            _peer_pct(quality, st, key, val, "state", f"State · {state}"),
        ]
        if loc:
            pcts.append(_peer_pct(quality, loc, key, val, "locality",
                                  f"{loc_label} · {getattr(me, loc_attr)}"))
        if own and len(own) >= _MIN_N:
            pcts.append(_peer_pct(quality, own, key, val, "ownership",
                                  f"Ownership · {getattr(me, 'ownership')}"))
        out.append(MetricBenchmark(
            key=key, label=label, suffix=suffix, value=val,
            direction="higher_is_better", percentiles=pcts,
            z_state=_z(_peer_values(quality, st, key), val)))
    return out


def _headline_national_pct(benchmarks: List[MetricBenchmark]) -> Optional[PeerPercentile]:
    if not benchmarks:
        return None
    for p in benchmarks[0].percentiles:
        if p.peer_set == "national":
            return p
    return None


def risk_indicators(sector_id: str, ccn: str,
                    benchmarks: List[MetricBenchmark]) -> List[RiskIndicator]:
    """Transparent, rule-based current-state risk indicators (NOT forecasts)."""
    out: List[RiskIndicator] = []

    # 1. Quality position vs national peers (headline metric).
    nat = _headline_national_pct(benchmarks)
    if nat is None or nat.suppressed or nat.percentile is None:
        out.append(RiskIndicator(
            "Quality position", INSUFFICIENT,
            "Headline national peer percentile unavailable "
            f"(only {nat.peer_n if nat else 0} rated peers)."))
    else:
        p = nat.percentile
        lvl = ELEVATED if p < 25 else (MODERATE if p < 50 else LOW)
        out.append(RiskIndicator(
            "Quality position", lvl,
            f"Headline metric at the {p}th national percentile "
            f"(n={nat.peer_n} rated peers)."))

    # 2. Statistical outlier (state z-score on the headline).
    z = benchmarks[0].z_state if benchmarks else None
    if z is None:
        out.append(RiskIndicator("Statistical outlier", INSUFFICIENT,
                                 "z-score requires >=5 state peers with spread."))
    elif z <= -2:
        out.append(RiskIndicator("Statistical outlier", ELEVATED,
                                 f"Headline z-score {z:+.2f} vs state peers — "
                                 "negative outlier (>2 sd below mean)."))
    elif abs(z) >= 1:
        out.append(RiskIndicator("Statistical outlier", MODERATE,
                                 f"Headline z-score {z:+.2f} vs state peers."))
    else:
        out.append(RiskIndicator("Statistical outlier", LOW,
                                 f"Headline z-score {z:+.2f} — within ~1 sd of peers."))

    # 3. Enforcement / staffing (SNF only — where the data exists). Reuses the
    # investable-evidence risk flags rather than re-deriving them.
    if sector_id == "nursing-homes":
        from .investable_evidence import evidence_profile
        ep = evidence_profile(sector_id, ccn)
        flags = [f for f in (ep.risk_flags if ep else []) if f.triggered]
        severe = [f for f in flags if f.name in ("Special Focus Facility", "Abuse icon")]
        if severe:
            out.append(RiskIndicator("Enforcement / staffing", ELEVATED,
                                     "; ".join(f.detail for f in flags)))
        elif flags:
            out.append(RiskIndicator("Enforcement / staffing", MODERATE,
                                     "; ".join(f.detail for f in flags)))
        else:
            out.append(RiskIndicator("Enforcement / staffing", LOW,
                                     "No SFF, abuse, ownership-change, low-staffing, "
                                     "or penalty flags on record."))

    # 4. Evidence confidence (peer sample + metric availability).
    min_n = min((p.peer_n for b in benchmarks for p in b.percentiles
                 if p.peer_set == "state"), default=0)
    missing = sum(1 for b in benchmarks if b.value is None)
    if min_n < _MIN_N:
        out.append(RiskIndicator("Evidence confidence", INSUFFICIENT,
                                 f"Only {min_n} rated state peers — percentile/"
                                 "z-score suppressed; treat as indicative only."))
    elif missing:
        out.append(RiskIndicator("Evidence confidence", MODERATE,
                                 f"{missing} of {len(benchmarks)} metrics not "
                                 "reported for this provider."))
    else:
        out.append(RiskIndicator("Evidence confidence", LOW,
                                 "Headline metrics reported with an adequate peer "
                                 "sample."))
    return out


def provider_benchmark_bundle(sector_id: str, ccn: str) -> ProviderBenchmarkBundle:
    """Full multi-peer-set benchmark + risk-indicator bundle for a provider."""
    bm = metric_benchmarks(sector_id, ccn)
    return ProviderBenchmarkBundle(
        sector_id=sector_id, ccn=ccn, metrics=bm,
        risk_indicators=risk_indicators(sector_id, ccn, bm))
