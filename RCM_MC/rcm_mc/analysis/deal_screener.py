"""Fast deal screening from public data only (Prompt 33-B).

A partner pastes 20 hospital names. The screener auto-populates each,
pulls regulatory context, scores quality + benchmark position, and
returns a ranked table in < 3 seconds per hospital. No ML, no MC —
just the data that's already in the HCRIS bundle + benchmarks.

Primary entry points:
- :func:`screen_deal` — one hospital, returns a :class:`DealScreen`.
- :func:`screen_batch` — many hospitals, sorted by attractiveness.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DealScreen:
    """Quick-look assessment of one hospital as a PE target."""
    query: str = ""
    ccn: str = ""
    name: str = ""
    city: str = ""
    state: str = ""
    bed_count: int = 0
    net_revenue: Optional[float] = None
    payer_mix: Dict[str, float] = field(default_factory=dict)
    quality_score: Optional[float] = None
    regulatory_risk_score: int = 0
    benchmark_position: Dict[str, str] = field(default_factory=dict)
    risk_score: int = 0
    verdict: str = "INSUFFICIENT_DATA"
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "ccn": self.ccn,
            "name": self.name,
            "city": self.city,
            "state": self.state,
            "bed_count": int(self.bed_count or 0),
            "net_revenue": (float(self.net_revenue)
                            if self.net_revenue is not None else None),
            "payer_mix": dict(self.payer_mix),
            "quality_score": (float(self.quality_score)
                               if self.quality_score is not None else None),
            "regulatory_risk_score": int(self.regulatory_risk_score),
            "benchmark_position": dict(self.benchmark_position),
            "risk_score": int(self.risk_score),
            "verdict": self.verdict,
            "narrative": self.narrative,
        }


def screen_deal(query: str, store: Any) -> DealScreen:
    """Auto-populate + score one hospital.

    Returns in < 1 second for a single name. No ML, no MC — just
    registry data and deterministic scoring. Partners use this for
    the "paste 20 names" flow.
    """
    screen = DealScreen(query=query)

    try:
        from ..data.auto_populate import auto_populate
    except Exception as exc:  # noqa: BLE001
        logger.debug("auto_populate unavailable: %s", exc)
        return screen

    result = auto_populate(store, query)
    if not result.matches:
        screen.narrative = "No hospital matched this query."
        return screen

    top = result.selected or result.matches[0]
    screen.ccn = top.ccn
    screen.name = top.name
    screen.city = top.city
    screen.state = top.state
    screen.bed_count = top.bed_count
    screen.payer_mix = dict(result.profile.get("payer_mix") or {})
    screen.net_revenue = result.financials.get("net_revenue") or result.financials.get("net_patient_revenue")

    # Quality score — star_rating if available, else None.
    star = result.quality.get("star_rating")
    if star is not None:
        try:
            screen.quality_score = float(star)
        except (TypeError, ValueError):
            pass

    # Regulatory risk score from the state registry.
    try:
        from ..data.state_regulatory import assess_regulatory
        reg = assess_regulatory(
            screen.state, bed_count=screen.bed_count,
            payer_mix=screen.payer_mix,
        )
        screen.regulatory_risk_score = reg.risk_score
    except Exception:  # noqa: BLE001
        pass

    # Benchmark position per metric: above/at/below P50.
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
        for k, v in result.benchmark_metrics.items():
            meta = RCM_METRIC_REGISTRY.get(k) or {}
            p50 = meta.get("benchmark_p50")
            if p50 is None:
                continue
            try:
                val = float(v)
                if val < float(p50) * 0.95:
                    screen.benchmark_position[k] = "below_p50"
                elif val > float(p50) * 1.05:
                    screen.benchmark_position[k] = "above_p50"
                else:
                    screen.benchmark_position[k] = "at_p50"
            except (TypeError, ValueError):
                continue
    except Exception:  # noqa: BLE001
        pass

    # Composite risk + verdict.
    screen.risk_score = _composite_score(screen)
    screen.verdict = _verdict(screen, result.coverage_pct)
    screen.narrative = _narrative(screen, result.coverage_pct)
    return screen


def _composite_score(s: DealScreen) -> int:
    """0-100 composite where higher = more attractive for PE."""
    score = 50
    if s.bed_count > 100:
        score += 5
    if s.bed_count > 300:
        score += 5
    if s.net_revenue and s.net_revenue > 200_000_000:
        score += 10
    if s.quality_score and s.quality_score >= 3.0:
        score += 10
    elif s.quality_score and s.quality_score <= 2.0:
        score -= 10
    score -= int(s.regulatory_risk_score * 0.3)
    return max(0, min(100, score))


def _verdict(s: DealScreen, coverage: float) -> str:
    if coverage < 10:
        return "INSUFFICIENT_DATA"
    if s.risk_score >= 70:
        return "STRONG_CANDIDATE"
    if s.risk_score >= 50:
        return "WORTH_INVESTIGATING"
    return "PASS"


def _narrative(s: DealScreen, coverage: float) -> str:
    parts: List[str] = []
    parts.append(f"{s.name or s.query}: {s.bed_count} beds in {s.state}.")
    if s.net_revenue:
        parts.append(f"Net revenue ~${s.net_revenue / 1e6:.0f}M.")
    if s.quality_score is not None:
        parts.append(f"Quality: {s.quality_score:.1f} stars.")
    parts.append(f"Screening score: {s.risk_score}/100 → {s.verdict}.")
    return " ".join(parts)


def screen_batch(
    queries: List[str], store: Any, *, limit: int = 50,
) -> List[DealScreen]:
    """Screen multiple hospitals, sorted by attractiveness."""
    results: List[DealScreen] = []
    for q in queries[:int(limit)]:
        if not (q or "").strip():
            continue
        results.append(screen_deal(q.strip(), store))
    results.sort(key=lambda s: s.risk_score, reverse=True)
    return results
