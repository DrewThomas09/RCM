"""Portfolio-level metric monitor (Prompt 36).

Compares each deal's latest analysis packet to its prior version,
flags new risks and threshold crossings. Feeds the heatmap UI so
partners see "what changed since last week" without clicking into
each deal individually.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DealDelta:
    """What changed between the latest and previous packet for one deal."""
    deal_id: str
    deal_name: str = ""
    new_risks: List[str] = field(default_factory=list)
    resolved_risks: List[str] = field(default_factory=list)
    metric_changes: Dict[str, float] = field(default_factory=dict)
    grade_change: str = ""    # "B→A", "A→B", "" if unchanged

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "new_risks": list(self.new_risks),
            "resolved_risks": list(self.resolved_risks),
            "metric_changes": dict(self.metric_changes),
            "grade_change": self.grade_change,
        }


def compute_deltas(store: Any) -> List[DealDelta]:
    """Compare the two most recent packets per deal.

    Returns a :class:`DealDelta` for every deal that has at least
    two analysis runs. Deals with only one run produce a delta with
    all-empty change lists — they'll appear in the heatmap but
    without directional arrows.
    """
    try:
        from ..analysis.analysis_store import list_packets, load_packet_by_id
    except Exception:  # noqa: BLE001
        return []

    rows = list_packets(store)
    by_deal: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        by_deal.setdefault(r["deal_id"], []).append(r)

    deltas: List[DealDelta] = []
    for deal_id, deal_rows in by_deal.items():
        deal_rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        latest = load_packet_by_id(store, deal_rows[0]["id"])
        if latest is None:
            continue
        d = DealDelta(
            deal_id=deal_id,
            deal_name=latest.deal_name or deal_id,
        )
        if len(deal_rows) >= 2:
            prior = load_packet_by_id(store, deal_rows[1]["id"])
            if prior is not None:
                d = _diff_packets(latest, prior)
        deltas.append(d)
    return deltas


def _diff_packets(latest, prior) -> DealDelta:
    d = DealDelta(
        deal_id=latest.deal_id,
        deal_name=latest.deal_name or latest.deal_id,
    )
    # Risk delta.
    latest_titles = {f.title for f in (latest.risk_flags or [])}
    prior_titles = {f.title for f in (prior.risk_flags or [])}
    d.new_risks = sorted(latest_titles - prior_titles)
    d.resolved_risks = sorted(prior_titles - latest_titles)

    # Grade change.
    lg = getattr(latest.completeness, "grade", "")
    pg = getattr(prior.completeness, "grade", "")
    if lg and pg and lg != pg:
        d.grade_change = f"{pg}→{lg}"

    # Metric value changes.
    for key, pm in (latest.rcm_profile or {}).items():
        prior_pm = (prior.rcm_profile or {}).get(key)
        if prior_pm is None:
            continue
        try:
            delta = float(pm.value) - float(prior_pm.value)
        except (TypeError, ValueError):
            continue
        if abs(delta) > 1e-9:
            d.metric_changes[key] = delta
    return d
