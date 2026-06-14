"""Episode-of-care grouping + service-line P&L — numpy + stdlib.

Claim lines are the wrong unit to underwrite on. A PE buyer cares about
the **episode** — an inpatient stay and everything that hangs off it,
a surgical bundle and its 90-day follow-up — because that's the unit
payers bundle, the unit margin accrues to, and the unit an operator can
actually manage. This mart rolls raw claim lines up into
anchor-triggered episodes (the CMS-BPCI shape: a trigger event plus a
pre/post window), then produces cost-per-episode distributions and a
service-line P&L.

Why anchor-triggered (not a fixed calendar bucket):
    An episode should follow the patient's care, not the calendar. An
    admission on Dec 28 with readmission Jan 9 is one clinical episode,
    not two annual ones. Anchoring on a trigger event with a window —
    and merging overlapping windows for the same patient — captures
    that. Claims outside any window are reported as ``unassigned`` (not
    silently dropped) so coverage is visible.

This is the native reimplementation of the slice of the Tuva
``episode`` mart diligence needs; it runs on aggregate claim lines, no
warehouse required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

CITATION_KEY = "EP1"
SOURCE_MODULE = "diligence.episodes"


@dataclass(frozen=True)
class ClaimLine:
    """One claim line. ``day`` is an integer ordinal (days from an
    arbitrary epoch) so windows are simple arithmetic."""
    patient_id: str
    day: int
    amount: float                 # cost / paid amount
    service_line: str
    revenue: Optional[float] = None   # if known, enables margin

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id, "day": self.day,
            "amount": self.amount, "service_line": self.service_line,
            "revenue": self.revenue,
        }


@dataclass(frozen=True)
class EpisodeDefinition:
    """How to trigger and bound an episode."""
    anchor_service_lines: frozenset
    pre_window_days: int = 0
    post_window_days: int = 90
    merge_overlapping: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_service_lines": sorted(self.anchor_service_lines),
            "pre_window_days": self.pre_window_days,
            "post_window_days": self.post_window_days,
            "merge_overlapping": self.merge_overlapping,
        }


@dataclass
class Episode:
    episode_id: str
    patient_id: str
    anchor_service_line: str
    start_day: int
    end_day: int
    n_claims: int
    total_cost: float
    total_revenue: Optional[float]
    service_line_costs: Dict[str, float] = field(default_factory=dict)

    @property
    def margin(self) -> Optional[float]:
        if self.total_revenue is None:
            return None
        return self.total_revenue - self.total_cost

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "patient_id": self.patient_id,
            "anchor_service_line": self.anchor_service_line,
            "start_day": self.start_day, "end_day": self.end_day,
            "n_claims": self.n_claims,
            "total_cost": round(self.total_cost, 2),
            "total_revenue": (
                None if self.total_revenue is None
                else round(self.total_revenue, 2)
            ),
            "margin": None if self.margin is None else round(self.margin, 2),
            "service_line_costs": {
                k: round(v, 2) for k, v in self.service_line_costs.items()
            },
        }


@dataclass
class ServiceLinePnL:
    service_line: str
    total_cost: float
    total_revenue: Optional[float]
    n_claims: int
    margin: Optional[float]
    margin_pct: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_line": self.service_line,
            "total_cost": round(self.total_cost, 2),
            "total_revenue": (
                None if self.total_revenue is None
                else round(self.total_revenue, 2)
            ),
            "n_claims": self.n_claims,
            "margin": None if self.margin is None else round(self.margin, 2),
            "margin_pct": (
                None if self.margin_pct is None else round(self.margin_pct, 4)
            ),
        }


@dataclass
class EpisodeGroupingResult:
    n_episodes: int
    n_claims_assigned: int
    n_claims_unassigned: int
    mean_cost: float
    median_cost: float
    p90_cost: float
    episodes: List[Episode] = field(default_factory=list)
    cost_by_anchor: Dict[str, float] = field(default_factory=dict)
    service_line_pnl: List[ServiceLinePnL] = field(default_factory=list)
    headline: str = ""
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_episodes": self.n_episodes,
            "n_claims_assigned": self.n_claims_assigned,
            "n_claims_unassigned": self.n_claims_unassigned,
            "mean_cost": round(self.mean_cost, 2),
            "median_cost": round(self.median_cost, 2),
            "p90_cost": round(self.p90_cost, 2),
            "episodes": [e.to_dict() for e in self.episodes],
            "cost_by_anchor": {
                k: round(v, 2) for k, v in self.cost_by_anchor.items()
            },
            "service_line_pnl": [p.to_dict() for p in self.service_line_pnl],
            "headline": self.headline,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def _merge_windows(windows: List[List[int]]) -> List[List[int]]:
    """Merge overlapping [start, end] windows. Input pre-sorted by start."""
    merged: List[List[int]] = []
    for w in windows:
        if merged and w[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], w[1])
        else:
            merged.append([w[0], w[1]])
    return merged


def group_episodes(
    claims: Sequence[ClaimLine],
    definition: EpisodeDefinition,
) -> EpisodeGroupingResult:
    """Group claim lines into anchor-triggered episodes of care.

    For each patient, every anchor claim opens a window
    ``[day - pre, day + post]``; overlapping windows merge (when
    enabled) into a single episode; all of that patient's claims
    falling inside a window are assigned to it. Claims outside every
    window are counted as ``unassigned``."""
    by_patient: Dict[str, List[ClaimLine]] = {}
    for c in claims:
        by_patient.setdefault(c.patient_id, []).append(c)

    episodes: List[Episode] = []
    n_assigned = 0
    n_unassigned = 0
    ep_counter = 0

    for pid, pclaims in by_patient.items():
        pclaims = sorted(pclaims, key=lambda c: c.day)
        anchors = [
            c for c in pclaims
            if c.service_line in definition.anchor_service_lines
        ]
        if not anchors:
            n_unassigned += len(pclaims)
            continue

        # Build (window, anchor_line) then merge windows.
        raw = sorted(
            [
                [a.day - definition.pre_window_days,
                 a.day + definition.post_window_days, a.service_line]
                for a in anchors
            ],
            key=lambda w: w[0],
        )
        if definition.merge_overlapping:
            windows = _merge_windows([[w[0], w[1]] for w in raw])
        else:
            windows = [[w[0], w[1]] for w in raw]
        # First anchor line per merged window (window covering its start).
        anchor_line_for = {}
        for w in windows:
            for r in raw:
                if w[0] <= r[0] <= w[1]:
                    anchor_line_for[(w[0], w[1])] = r[2]
                    break

        for w in windows:
            in_ep = [c for c in pclaims if w[0] <= c.day <= w[1]]
            if not in_ep:
                continue
            ep_counter += 1
            sl_costs: Dict[str, float] = {}
            for c in in_ep:
                sl_costs[c.service_line] = sl_costs.get(c.service_line, 0.0) + c.amount
            has_rev = any(c.revenue is not None for c in in_ep)
            total_rev = (
                sum((c.revenue or 0.0) for c in in_ep) if has_rev else None
            )
            episodes.append(Episode(
                episode_id=f"EP{ep_counter:06d}",
                patient_id=pid,
                anchor_service_line=anchor_line_for.get(
                    (w[0], w[1]), next(iter(definition.anchor_service_lines))),
                start_day=w[0], end_day=w[1],
                n_claims=len(in_ep),
                total_cost=sum(c.amount for c in in_ep),
                total_revenue=total_rev,
                service_line_costs=sl_costs,
            ))
            n_assigned += len(in_ep)
        # Patient claims outside all windows.
        in_any = sum(
            1 for c in pclaims
            if any(w[0] <= c.day <= w[1] for w in windows)
        )
        n_unassigned += len(pclaims) - in_any

    costs = np.array([e.total_cost for e in episodes]) if episodes else np.array([])
    mean_c = float(costs.mean()) if costs.size else 0.0
    median_c = float(np.median(costs)) if costs.size else 0.0
    p90_c = float(np.percentile(costs, 90)) if costs.size else 0.0

    cost_by_anchor: Dict[str, float] = {}
    anchor_counts: Dict[str, int] = {}
    for e in episodes:
        cost_by_anchor[e.anchor_service_line] = (
            cost_by_anchor.get(e.anchor_service_line, 0.0) + e.total_cost
        )
        anchor_counts[e.anchor_service_line] = (
            anchor_counts.get(e.anchor_service_line, 0) + 1
        )

    pnl = _service_line_pnl(episodes)
    res = EpisodeGroupingResult(
        n_episodes=len(episodes), n_claims_assigned=n_assigned,
        n_claims_unassigned=n_unassigned,
        mean_cost=mean_c, median_cost=median_c, p90_cost=p90_c,
        episodes=episodes, cost_by_anchor=cost_by_anchor,
        service_line_pnl=pnl,
    )
    res.headline = _headline(res, anchor_counts)
    return res


def _service_line_pnl(episodes: Sequence[Episode]) -> List[ServiceLinePnL]:
    cost: Dict[str, float] = {}
    rev: Dict[str, float] = {}
    has_rev: Dict[str, bool] = {}
    n: Dict[str, int] = {}
    for e in episodes:
        for sl, c in e.service_line_costs.items():
            cost[sl] = cost.get(sl, 0.0) + c
            n[sl] = n.get(sl, 0) + 1
    # Revenue is only available at episode level; attribute proportionally
    # to service lines by their cost share (the standard allocation when
    # line-level revenue isn't itemized).
    for e in episodes:
        if e.total_revenue is None or e.total_cost <= 0:
            continue
        for sl, c in e.service_line_costs.items():
            share = c / e.total_cost
            rev[sl] = rev.get(sl, 0.0) + e.total_revenue * share
            has_rev[sl] = True
    out: List[ServiceLinePnL] = []
    for sl in sorted(cost, key=lambda s: -cost[s]):
        r = rev.get(sl) if has_rev.get(sl) else None
        margin = (r - cost[sl]) if r is not None else None
        mpct = (margin / r) if (margin is not None and r) else None
        out.append(ServiceLinePnL(
            service_line=sl, total_cost=cost[sl], total_revenue=r,
            n_claims=n[sl], margin=margin, margin_pct=mpct,
        ))
    return out


def _headline(res: EpisodeGroupingResult, anchor_counts: Dict[str, int]) -> str:
    if res.n_episodes == 0:
        return "No episodes triggered — no anchor claims found in the data."
    top_anchor = max(anchor_counts, key=anchor_counts.get) if anchor_counts else "—"
    base = (
        f"{res.n_episodes} episodes (mean cost ${res.mean_cost:,.2f}, "
        f"median ${res.median_cost:,.2f}, P90 ${res.p90_cost:,.2f}); "
        f"most common anchor: {top_anchor} ({anchor_counts.get(top_anchor, 0)})."
    )
    neg = [p for p in res.service_line_pnl
           if p.margin is not None and p.margin < 0]
    if neg:
        worst = min(neg, key=lambda p: p.margin)
        base += (
            f" ⚠ {len(neg)} service line(s) margin-negative; worst: "
            f"{worst.service_line} (${worst.margin:,.2f})."
        )
    return base
