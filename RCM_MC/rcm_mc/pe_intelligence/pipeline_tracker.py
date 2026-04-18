"""Deal pipeline tracker — sourcing funnel stats.

A sponsor's sourcing funnel: sourced → IOI → LOI → exclusive diligence
→ close. Each stage has typical yields; partners track where the
funnel is leaking. This module provides stats + warnings on funnel
health.

Status vocabulary:
- `sourced` — added to pipeline
- `screened` — cleared initial 2-page memo
- `ioi` — indication of interest submitted
- `mgmt_meeting` — meeting taken with management
- `loi` — LOI submitted
- `exclusive` — exclusive diligence entered
- `closed` — deal signed / funded
- `passed` — declined or lost

Partner-prudent yield targets (sponsor-specific; starter values):
sourced→screened 40%, screened→ioi 25%, ioi→meeting 50%,
meeting→loi 35%, loi→exclusive 55%, exclusive→closed 75%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


PIPELINE_STAGES = (
    "sourced", "screened", "ioi", "mgmt_meeting",
    "loi", "exclusive", "closed",
)

TERMINAL_STAGES = ("closed", "passed")


_TARGET_YIELDS = {
    ("sourced", "screened"): 0.40,
    ("screened", "ioi"): 0.25,
    ("ioi", "mgmt_meeting"): 0.50,
    ("mgmt_meeting", "loi"): 0.35,
    ("loi", "exclusive"): 0.55,
    ("exclusive", "closed"): 0.75,
}


@dataclass
class PipelineDeal:
    deal_id: str
    name: str = ""
    current_stage: str = "sourced"
    sector: Optional[str] = None
    ebitda_m: Optional[float] = None
    source: str = ""                       # "banker" | "direct" | "sponsor" | ...
    entry_date: Optional[date] = None
    last_activity_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "name": self.name,
            "current_stage": self.current_stage,
            "sector": self.sector,
            "ebitda_m": self.ebitda_m,
            "source": self.source,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "last_activity_date": (self.last_activity_date.isoformat()
                                   if self.last_activity_date else None),
        }


@dataclass
class FunnelStats:
    n_by_stage: Dict[str, int] = field(default_factory=dict)
    yields: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    healthy: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_by_stage": dict(self.n_by_stage),
            "yields": dict(self.yields),
            "warnings": list(self.warnings),
            "healthy": self.healthy,
        }


# ── Analyzer ────────────────────────────────────────────────────────

def funnel_stats(deals: List[PipelineDeal]) -> FunnelStats:
    """Count deals by stage and compute stage-to-stage yields.

    Yields are computed as (next stage or beyond) / (this stage or beyond).
    "Beyond" means any stage further down the funnel.
    """
    stats = FunnelStats()
    # Count at each stage (including anyone who's moved further).
    stage_index = {s: i for i, s in enumerate(PIPELINE_STAGES)}
    counts_at_or_beyond: Dict[str, int] = {s: 0 for s in PIPELINE_STAGES}
    for d in deals:
        if d.current_stage == "passed":
            continue
        idx = stage_index.get(d.current_stage, 0)
        for i, stage in enumerate(PIPELINE_STAGES):
            if idx >= i:
                counts_at_or_beyond[stage] += 1
    stats.n_by_stage = counts_at_or_beyond

    # Yields between adjacent stages.
    for (src, dst), target in _TARGET_YIELDS.items():
        at_src = counts_at_or_beyond.get(src, 0)
        at_dst = counts_at_or_beyond.get(dst, 0)
        if at_src == 0:
            continue
        y = at_dst / at_src
        stats.yields[f"{src}->{dst}"] = y
        if y < target * 0.6:
            stats.warnings.append(
                f"Yield {src}→{dst}: {y*100:.0f}% (target {target*100:.0f}%) — "
                "funnel is leaking at this stage."
            )
    if stats.warnings:
        stats.healthy = False
    return stats


def stale_deals(
    deals: List[PipelineDeal],
    *,
    today: date,
    days_threshold: int = 60,
) -> List[PipelineDeal]:
    """Return deals whose last activity is more than ``days_threshold``
    days old. Skips terminal stages."""
    out: List[PipelineDeal] = []
    for d in deals:
        if d.current_stage in TERMINAL_STAGES:
            continue
        if d.last_activity_date is None:
            out.append(d)
            continue
        age_days = (today - d.last_activity_date).days
        if age_days >= days_threshold:
            out.append(d)
    return out


def source_mix(deals: List[PipelineDeal]) -> Dict[str, float]:
    """Breakdown of deals by source channel (banker / direct / sponsor).

    Returns fractions summing to 1.0.
    """
    total = 0
    counts: Dict[str, int] = {}
    for d in deals:
        src = (d.source or "unknown").lower()
        counts[src] = counts.get(src, 0) + 1
        total += 1
    if total == 0:
        return {}
    return {k: v / total for k, v in counts.items()}
