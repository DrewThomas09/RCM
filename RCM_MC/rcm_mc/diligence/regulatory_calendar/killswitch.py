"""Regulatory kill-switch verdict engine.

Given a target profile + (optional) thesis driver list, produces a
date-ordered timeline of regulatory events and a per-driver
kill-switch verdict with the specific date each kill takes effect.

Partner-facing output:
    "Your thesis driver #1 (MA margin lift) dies on April 12,
    2026 when CMS V28 final rule publishes — 68% of its 5.5 pp
    claimed EBITDA lift is impaired."

Also computes:
    * total expected revenue-impact pct summed across events
    * total expected margin-impact pp summed across events
    * an EBITDA-bridge overlay (per-year $ impact) when target
      revenue + margin are supplied
    * a risk score (0-100) combining kill count + impairment
      severity + days-to-first-kill.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .calendar import (
    REGULATORY_EVENTS, RegulatoryEvent, upcoming_events,
)
from .impact_mapper import (
    DEFAULT_THESIS_DRIVERS, ImpactVerdict, ThesisDriver,
    ThesisImpact, map_event_to_drivers,
)


class KillSwitchVerdict(str, Enum):
    """Overall regulatory-exposure verdict for the thesis."""
    PASS = "PASS"                # no driver impaired > 10%
    CAUTION = "CAUTION"          # 1 driver damaged, none killed
    WARNING = "WARNING"          # multiple damaged OR 1 killed
    FAIL = "FAIL"                # multiple killed


@dataclass
class DriverKillTimeline:
    """Per-driver timeline of impacts sorted by effective date."""
    driver_id: str
    driver_label: str
    expected_lift_pct: float
    impacts: List[ThesisImpact] = field(default_factory=list)
    worst_verdict: ImpactVerdict = ImpactVerdict.UNAFFECTED
    cumulative_impairment_pct: float = 0.0
    residual_lift_pct: float = 0.0
    first_kill_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "driver_id": self.driver_id,
            "driver_label": self.driver_label,
            "expected_lift_pct": self.expected_lift_pct,
            "impacts": [i.to_dict() for i in self.impacts],
            "worst_verdict": self.worst_verdict.value,
            "cumulative_impairment_pct": self.cumulative_impairment_pct,
            "residual_lift_pct": self.residual_lift_pct,
            "first_kill_date": self.first_kill_date,
        }


@dataclass
class EbitdaOverlay:
    """Per-year $ impact on target EBITDA from the regulatory
    calendar.  Feeds directly into the PE EBITDA bridge."""
    year: int
    effective_date_iso: str
    revenue_delta_usd: float
    margin_delta_pp: float
    ebitda_delta_usd: float
    driving_events: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "effective_date_iso": self.effective_date_iso,
            "revenue_delta_usd": self.revenue_delta_usd,
            "margin_delta_pp": self.margin_delta_pp,
            "ebitda_delta_usd": self.ebitda_delta_usd,
            "driving_events": list(self.driving_events),
        }


@dataclass
class RegulatoryExposureReport:
    """Top-level kill-switch output surface."""
    as_of: str
    target_profile: Dict[str, Any]
    horizon_months: int
    events: List[RegulatoryEvent] = field(default_factory=list)
    driver_timelines: List[DriverKillTimeline] = field(default_factory=list)
    ebitda_overlay: List[EbitdaOverlay] = field(default_factory=list)
    verdict: KillSwitchVerdict = KillSwitchVerdict.PASS
    risk_score: float = 0.0
    killed_driver_count: int = 0
    damaged_driver_count: int = 0
    total_expected_revenue_impact_pct: float = 0.0
    total_expected_margin_impact_pp: float = 0.0
    headline: str = ""
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "as_of": self.as_of,
            "target_profile": self.target_profile,
            "horizon_months": self.horizon_months,
            "events": [e.to_dict() for e in self.events],
            "driver_timelines":
                [d.to_dict() for d in self.driver_timelines],
            "ebitda_overlay":
                [o.to_dict() for o in self.ebitda_overlay],
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "killed_driver_count": self.killed_driver_count,
            "damaged_driver_count": self.damaged_driver_count,
            "total_expected_revenue_impact_pct":
                self.total_expected_revenue_impact_pct,
            "total_expected_margin_impact_pp":
                self.total_expected_margin_impact_pp,
            "headline": self.headline,
            "rationale": self.rationale,
        }


# ────────────────────────────────────────────────────────────────────
# Verdict math
# ────────────────────────────────────────────────────────────────────

def _worst_verdict(
    impacts: Sequence[ThesisImpact],
) -> ImpactVerdict:
    order = {
        ImpactVerdict.UNAFFECTED: 0,
        ImpactVerdict.DAMAGED: 1,
        ImpactVerdict.KILLED: 2,
    }
    if not impacts:
        return ImpactVerdict.UNAFFECTED
    return max(impacts, key=lambda i: order[i.verdict]).verdict


def _combine_impairment(impacts: Sequence[ThesisImpact]) -> float:
    """Compound multiple impairments on the same driver.

    Each impact removes a fraction of the *remaining* lift.  Two
    40% impairments stack to 1 - 0.6 × 0.6 = 0.64 cumulative, not
    0.80.  This matches the economic reality — once a driver is
    half-gone, the next hit has a smaller absolute denominator.
    """
    surviving = 1.0
    for imp in impacts:
        if imp.verdict == ImpactVerdict.UNAFFECTED:
            continue
        surviving *= (1.0 - imp.impairment_pct)
    return 1.0 - surviving


def _overall_verdict(
    timelines: Sequence[DriverKillTimeline],
) -> Tuple[KillSwitchVerdict, int, int]:
    killed = sum(
        1 for t in timelines
        if t.worst_verdict == ImpactVerdict.KILLED
    )
    damaged = sum(
        1 for t in timelines
        if t.worst_verdict == ImpactVerdict.DAMAGED
    )
    if killed >= 2:
        verdict = KillSwitchVerdict.FAIL
    elif killed == 1 or damaged >= 2:
        verdict = KillSwitchVerdict.WARNING
    elif damaged == 1:
        verdict = KillSwitchVerdict.CAUTION
    else:
        verdict = KillSwitchVerdict.PASS
    return verdict, killed, damaged


def _risk_score(
    timelines: Sequence[DriverKillTimeline],
    as_of: date,
    horizon_months: int,
) -> float:
    """0-100 risk score combining kill severity and proximity."""
    if not timelines:
        return 0.0
    score = 0.0
    horizon_days = max(horizon_months * 30, 1)
    for t in timelines:
        if t.worst_verdict == ImpactVerdict.KILLED:
            base = 40.0
        elif t.worst_verdict == ImpactVerdict.DAMAGED:
            base = 15.0
        else:
            continue
        # Proximity bonus: a kill that happens in 30 days is
        # worse than one 20 months out.
        if t.first_kill_date:
            try:
                d = date.fromisoformat(t.first_kill_date)
                days_out = max((d - as_of).days, 0)
                prox = 1.0 - (days_out / horizon_days)
                prox = max(0.0, min(1.0, prox))
            except (ValueError, TypeError):
                prox = 0.5
        else:
            prox = 0.5
        score += base * (0.5 + 0.5 * prox)
    return min(100.0, score)


def _ebitda_overlay(
    events: Sequence[RegulatoryEvent],
    target: Mapping[str, Any],
) -> List[EbitdaOverlay]:
    """Convert per-event revenue/margin pct into $ overlay.

    Requires target['revenue_usd'] for the revenue deltas.  If
    not supplied we return margin-only deltas.
    """
    revenue_base = float(target.get("revenue_usd", 0.0) or 0.0)
    ebitda_base = float(target.get("ebitda_usd", 0.0) or 0.0)

    by_year: Dict[int, Dict[str, Any]] = {}
    for ev in events:
        eff = ev.effective_date or ev.publish_date
        year = eff.year
        bucket = by_year.setdefault(year, {
            "rev_delta_pct": 0.0,
            "margin_delta_pp": 0.0,
            "effective_date_iso": eff.isoformat(),
            "driving_events": [],
        })
        bucket["rev_delta_pct"] += ev.expected_revenue_impact_pct
        bucket["margin_delta_pp"] += ev.expected_margin_impact_pp
        bucket["driving_events"].append(ev.event_id)
        # Use the earliest effective date in the year
        if eff.isoformat() < bucket["effective_date_iso"]:
            bucket["effective_date_iso"] = eff.isoformat()

    overlay: List[EbitdaOverlay] = []
    for year in sorted(by_year):
        b = by_year[year]
        revenue_delta_usd = revenue_base * b["rev_delta_pct"]
        # Margin drag applies to the *post-delta* revenue
        margin_delta_pp = b["margin_delta_pp"]
        ebitda_delta_from_margin = (
            (revenue_base + revenue_delta_usd)
            * (margin_delta_pp / 100.0)
        )
        # Direct revenue pass-through assumes the target's incremental
        # revenue carried its base margin.  Use the target margin if
        # supplied, else 15% (hospital-system stdev).
        base_margin_pct = (
            (ebitda_base / revenue_base)
            if revenue_base > 0 else 0.15
        )
        ebitda_delta_from_revenue = (
            revenue_delta_usd * base_margin_pct
        )
        ebitda_delta_usd = (
            ebitda_delta_from_margin + ebitda_delta_from_revenue
        )
        overlay.append(EbitdaOverlay(
            year=year,
            effective_date_iso=b["effective_date_iso"],
            revenue_delta_usd=revenue_delta_usd,
            margin_delta_pp=margin_delta_pp,
            ebitda_delta_usd=ebitda_delta_usd,
            driving_events=b["driving_events"],
        ))
    return overlay


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def _filter_events_for_target(
    events: Sequence[RegulatoryEvent],
    target: Mapping[str, Any],
) -> List[RegulatoryEvent]:
    """Keep events whose affected_specialties intersect the
    target's specialties (or the target has no specialty info —
    then keep them all so the partner can see the universe)."""
    target_sp = set()
    if target.get("specialty"):
        target_sp.add(str(target["specialty"]).upper())
    for s in target.get("specialties") or []:
        target_sp.add(str(s).upper())
    if not target_sp:
        return list(events)
    out: List[RegulatoryEvent] = []
    for ev in events:
        ev_sp = {s.upper() for s in ev.affected_specialties}
        if ev_sp & target_sp:
            out.append(ev)
    return out


def analyze_regulatory_exposure(
    target_profile: Optional[Mapping[str, Any]] = None,
    drivers: Optional[Sequence[ThesisDriver]] = None,
    as_of: Optional[date] = None,
    horizon_months: int = 24,
    include_all_events: bool = False,
) -> RegulatoryExposureReport:
    """Full pipeline: events → per-driver timelines → overlay → verdict.

    ``target_profile`` conventions (all optional):
        specialty / specialties — str or list of str
        ma_mix_pct — 0..1 fraction
        commercial_payer_share — 0..1
        has_hopd_revenue — bool
        has_reit_landlord — bool
        revenue_usd, ebitda_usd — for the overlay

    ``include_all_events=True`` skips target-specialty filtering —
    useful for the universe-view UI.
    """
    as_of = as_of or date.today()
    target = dict(target_profile or {})
    driver_list = list(drivers or DEFAULT_THESIS_DRIVERS)

    events = upcoming_events(as_of=as_of, months_ahead=horizon_months)
    if not include_all_events:
        events = _filter_events_for_target(events, target)

    # Per-driver: collect all ThesisImpacts across events.
    per_driver: Dict[str, DriverKillTimeline] = {}
    for d in driver_list:
        per_driver[d.driver_id] = DriverKillTimeline(
            driver_id=d.driver_id,
            driver_label=d.label,
            expected_lift_pct=d.expected_lift_pct,
            residual_lift_pct=d.expected_lift_pct,
        )

    for ev in events:
        impacts = map_event_to_drivers(ev, driver_list, target)
        for imp in impacts:
            tl = per_driver.get(imp.driver_id)
            if tl is None:
                continue
            if imp.verdict == ImpactVerdict.UNAFFECTED:
                continue
            tl.impacts.append(imp)

    # Second pass: compute roll-up stats per driver.
    total_rev_pct = 0.0
    total_margin_pp = 0.0
    for tl in per_driver.values():
        tl.impacts.sort(
            key=lambda i: i.effective_date or "9999",
        )
        tl.worst_verdict = _worst_verdict(tl.impacts)
        tl.cumulative_impairment_pct = _combine_impairment(
            tl.impacts,
        )
        tl.residual_lift_pct = (
            tl.expected_lift_pct *
            (1.0 - tl.cumulative_impairment_pct)
        )
        killed_impacts = [
            i for i in tl.impacts
            if i.verdict == ImpactVerdict.KILLED
        ]
        if killed_impacts:
            tl.first_kill_date = killed_impacts[0].effective_date
        elif tl.impacts:
            tl.first_kill_date = tl.impacts[0].effective_date

    for ev in events:
        total_rev_pct += ev.expected_revenue_impact_pct
        total_margin_pp += ev.expected_margin_impact_pp

    timelines = sorted(
        per_driver.values(),
        key=lambda t: (
            {ImpactVerdict.KILLED: 0,
             ImpactVerdict.DAMAGED: 1,
             ImpactVerdict.UNAFFECTED: 2}[t.worst_verdict],
            -t.cumulative_impairment_pct,
        ),
    )

    verdict, killed_count, damaged_count = _overall_verdict(
        timelines,
    )
    score = _risk_score(timelines, as_of, horizon_months)
    overlay = _ebitda_overlay(events, target)

    # Partner-facing headline — the literal demo moment.
    killed_first = next(
        (t for t in timelines
         if t.worst_verdict == ImpactVerdict.KILLED), None,
    )
    if killed_first and killed_first.first_kill_date:
        driving_event_id = next(
            (i.event_id for i in killed_first.impacts
             if i.verdict == ImpactVerdict.KILLED), "",
        )
        driving_event_title = next(
            (e.title for e in events
             if e.event_id == driving_event_id), "",
        )
        headline = (
            f"Thesis driver \"{killed_first.driver_label}\" dies "
            f"on {killed_first.first_kill_date} — "
            f"{driving_event_title} impairs "
            f"{killed_first.cumulative_impairment_pct*100:.0f}% "
            f"of its claimed "
            f"{killed_first.expected_lift_pct*100:.1f} pp lift."
        )
    elif damaged_count:
        dmg = next(
            (t for t in timelines
             if t.worst_verdict == ImpactVerdict.DAMAGED), None,
        )
        if dmg:
            headline = (
                f"Thesis driver \"{dmg.driver_label}\" damaged — "
                f"residual lift "
                f"{dmg.residual_lift_pct*100:.1f} pp "
                f"vs claimed "
                f"{dmg.expected_lift_pct*100:.1f} pp."
            )
        else:
            headline = "No thesis drivers materially impaired."
    else:
        headline = (
            "All thesis drivers pass the regulatory calendar "
            "screen — no events damage claimed lift within "
            f"the {horizon_months}-month horizon."
        )

    rationale_parts: List[str] = []
    if killed_count:
        rationale_parts.append(
            f"{killed_count} driver"
            f"{'s' if killed_count != 1 else ''} killed "
            "(>50% lift impaired)."
        )
    if damaged_count:
        rationale_parts.append(
            f"{damaged_count} driver"
            f"{'s' if damaged_count != 1 else ''} damaged "
            "(10-50% lift impaired)."
        )
    if not rationale_parts:
        rationale_parts.append(
            "Every curated event in the horizon leaves the "
            "thesis drivers' claimed lift substantially intact."
        )
    if total_margin_pp:
        rationale_parts.append(
            f"Aggregate expected margin impact "
            f"{total_margin_pp:+.2f} pp across "
            f"{len(events)} event"
            f"{'s' if len(events) != 1 else ''}."
        )
    rationale = " ".join(rationale_parts)

    return RegulatoryExposureReport(
        as_of=as_of.isoformat(),
        target_profile=target,
        horizon_months=horizon_months,
        events=list(events),
        driver_timelines=timelines,
        ebitda_overlay=overlay,
        verdict=verdict,
        risk_score=score,
        killed_driver_count=killed_count,
        damaged_driver_count=damaged_count,
        total_expected_revenue_impact_pct=total_rev_pct,
        total_expected_margin_impact_pp=total_margin_pp,
        headline=headline,
        rationale=rationale,
    )
