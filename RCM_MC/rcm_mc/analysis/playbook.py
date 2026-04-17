"""Operational playbook builder (Prompt 59).

For each lever in a deal's v2 bridge, find historical deals that share
the same hospital archetype pattern, then compute success rates and
surface the most common initiatives and failure factors. The playbook
gives the deal team a starting point: "hospitals that look like this
one improved denial rates 70% of the time, typically using X and Y."

When fewer than 3 matching historical deals exist the lever is omitted
— the UI shows "insufficient history" rather than a noisy estimate.
"""
from __future__ import annotations

import json
import logging
import zlib
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Dataclasses ────────────────────────────────────────────────────

SUCCESS_THRESHOLD = 0.80  # ≥80% of target = success
MIN_MATCHING_DEALS = 3


@dataclass
class DealOutcome:
    """One historical deal's result for a particular lever."""
    deal_id: str
    initial_value: float
    target_value: float
    achieved_value: float
    months_elapsed: int
    success: bool
    initiatives_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DealOutcome":
        return cls(
            deal_id=str(d.get("deal_id") or ""),
            initial_value=float(d.get("initial_value") or 0),
            target_value=float(d.get("target_value") or 0),
            achieved_value=float(d.get("achieved_value") or 0),
            months_elapsed=int(d.get("months_elapsed") or 0),
            success=bool(d.get("success")),
            initiatives_used=list(d.get("initiatives_used") or []),
        )


@dataclass
class PlaybookEntry:
    """Aggregated guidance for one lever, derived from matching deals."""
    lever: str
    pattern: str
    matching_deals: List[DealOutcome] = field(default_factory=list)
    success_rate: float = 0.0
    avg_achievement_pct: float = 0.0
    common_initiatives: List[str] = field(default_factory=list)
    failure_factors: List[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lever": self.lever,
            "pattern": self.pattern,
            "matching_deals": [d.to_dict() for d in self.matching_deals],
            "success_rate": self.success_rate,
            "avg_achievement_pct": self.avg_achievement_pct,
            "common_initiatives": self.common_initiatives,
            "failure_factors": self.failure_factors,
            "recommendation": self.recommendation,
        }


# ── Pattern classification ─────────────────────────────────────────

_PATTERN_ARCHETYPES = [
    "commercial_heavy_denial",
    "medicare_heavy_ar",
    "rural_access_coding",
    "system_acquisition",
    "high_medicaid_write_off",
    "large_academic_complex",
    "outpatient_dominant",
    "post_merger_integration",
    "specialty_niche",
    "general",
]


def _classify_pattern(metric_key: str, profile: Dict[str, Any]) -> str:
    """Classify a hospital into ~10 archetypes based on profile.

    The profile dict is expected to carry payer-mix percentages,
    bed count, system affiliation flag, and denial/AR summaries.
    Falls back to ``"general"`` when data is insufficient.
    """
    commercial_pct = float(profile.get("commercial_pct") or 0)
    medicare_pct = float(profile.get("medicare_pct") or 0)
    medicaid_pct = float(profile.get("medicaid_pct") or 0)
    denial_rate = float(profile.get("denial_rate") or 0)
    ar_days = float(profile.get("ar_days") or 0)
    beds = int(profile.get("beds") or 0)
    system_affiliated = bool(profile.get("system_affiliated"))
    outpatient_pct = float(profile.get("outpatient_pct") or 0)
    is_academic = bool(profile.get("is_academic"))
    post_merger = bool(profile.get("post_merger"))

    # Order matters — first match wins.
    if commercial_pct > 40 and denial_rate > 10:
        return "commercial_heavy_denial"
    if medicare_pct > 50 and ar_days > 50:
        return "medicare_heavy_ar"
    if beds > 0 and beds < 200:
        return "rural_access_coding"
    if system_affiliated:
        return "system_acquisition"
    if medicaid_pct > 40 and denial_rate > 8:
        return "high_medicaid_write_off"
    if is_academic and beds >= 500:
        return "large_academic_complex"
    if outpatient_pct > 60:
        return "outpatient_dominant"
    if post_merger:
        return "post_merger_integration"
    return "general"


# ── Helpers ────────────────────────────────────────────────────────

def _achievement_pct(initial: float, target: float, achieved: float) -> float:
    """Fraction of target improvement actually achieved.

    Returns 0.0 when the target == initial (no intended improvement).
    Clamps at 0.0 on the low end but does not cap above 1.0 — a deal
    can over-achieve.
    """
    span = target - initial
    if abs(span) < 1e-12:
        return 0.0
    return max(0.0, (achieved - initial) / span)


def _is_success(initial: float, target: float, achieved: float) -> bool:
    return _achievement_pct(initial, target, achieved) >= SUCCESS_THRESHOLD


def _load_profile(store: Any, deal_id: str) -> Dict[str, Any]:
    """Pull the profile_json for a deal, returning {} on miss."""
    try:
        with store.connect() as con:
            row = con.execute(
                "SELECT profile_json FROM deals WHERE deal_id = ?",
                (deal_id,),
            ).fetchone()
        if row and row["profile_json"]:
            return json.loads(row["profile_json"])
    except Exception:  # noqa: BLE001
        logger.debug("Could not load profile for %s", deal_id)
    return {}


def _load_lever_impacts(store: Any, deal_id: str) -> List[Dict[str, Any]]:
    """Pull v2 bridge lever impacts from the most-recent analysis run."""
    try:
        with store.connect() as con:
            row = con.execute(
                "SELECT packet_json FROM analysis_runs "
                "WHERE deal_id = ? ORDER BY id DESC LIMIT 1",
                (deal_id,),
            ).fetchone()
        if row is None:
            return []
        blob = row["packet_json"]
        if isinstance(blob, (bytes, memoryview)):
            data = json.loads(zlib.decompress(blob).decode())
        else:
            data = json.loads(blob)
        vbr = data.get("value_bridge_result") or {}
        return vbr.get("lever_impacts") or []
    except Exception:  # noqa: BLE001
        logger.debug("Could not load lever impacts for %s", deal_id)
        return []


def _load_value_creation_plan(store: Any, deal_id: str) -> Optional[Dict[str, Any]]:
    """Load the latest value creation plan for a deal."""
    try:
        with store.connect() as con:
            row = con.execute(
                "SELECT plan_json FROM value_creation_plans "
                "WHERE deal_id = ? ORDER BY id DESC LIMIT 1",
                (deal_id,),
            ).fetchone()
        if row is None:
            return None
        blob = row["plan_json"]
        if isinstance(blob, (bytes, memoryview)):
            return json.loads(zlib.decompress(blob).decode())
        return json.loads(blob)
    except Exception:  # noqa: BLE001
        logger.debug("Could not load VCP for %s", deal_id)
        return None


def _load_quarterly_actuals(store: Any, deal_id: str) -> List[Dict[str, Any]]:
    """Return all quarterly actuals rows for a deal."""
    try:
        with store.connect() as con:
            rows = con.execute(
                "SELECT quarter, kpis_json, plan_kpis_json "
                "FROM quarterly_actuals WHERE deal_id = ? ORDER BY quarter",
                (deal_id,),
            ).fetchall()
        return [
            {
                "quarter": r["quarter"],
                "actuals": json.loads(r["kpis_json"] or "{}"),
                "plan": json.loads(r["plan_kpis_json"] or "{}"),
            }
            for r in rows
        ]
    except Exception:  # noqa: BLE001
        logger.debug("Could not load actuals for %s", deal_id)
        return []


def _all_deal_ids(store: Any) -> List[str]:
    """Return every deal_id in the deals table."""
    try:
        with store.connect() as con:
            rows = con.execute("SELECT deal_id FROM deals").fetchall()
        return [r["deal_id"] for r in rows]
    except Exception:  # noqa: BLE001
        return []


def _extract_deal_outcome(
    deal_id: str,
    lever_key: str,
    plan: Optional[Dict[str, Any]],
    actuals: List[Dict[str, Any]],
    lever_impacts: List[Dict[str, Any]],
) -> Optional[DealOutcome]:
    """Build a DealOutcome for one lever on one historical deal."""
    # Find the lever in the bridge
    impact = None
    for li in lever_impacts:
        if li.get("metric_key") == lever_key:
            impact = li
            break
    if impact is None:
        return None

    initial = float(impact.get("current_value") or 0)
    target = float(impact.get("target_value") or 0)

    # Pull the latest actual value for this metric from quarterly actuals
    achieved = initial  # default: no movement
    months = 0
    if actuals:
        latest = actuals[-1]
        actual_kpis = latest.get("actuals") or {}
        if lever_key in actual_kpis:
            achieved = float(actual_kpis[lever_key])
        months = len(actuals) * 3  # each row ~ 1 quarter

    # Extract initiative names from VCP
    initiatives: List[str] = []
    if plan:
        for init in plan.get("initiatives") or []:
            if init.get("lever_key") == lever_key:
                initiatives.append(str(init.get("name") or init.get("initiative_id") or ""))

    success = _is_success(initial, target, achieved)

    return DealOutcome(
        deal_id=deal_id,
        initial_value=initial,
        target_value=target,
        achieved_value=achieved,
        months_elapsed=months,
        success=success,
        initiatives_used=initiatives,
    )


def _infer_failure_factors(outcomes: List[DealOutcome]) -> List[str]:
    """Heuristic failure-factor extraction from unsuccessful deals."""
    factors: List[str] = []
    failures = [o for o in outcomes if not o.success]
    if not failures:
        return factors

    avg_months = sum(f.months_elapsed for f in failures) / len(failures)
    if avg_months < 12:
        factors.append("insufficient_ramp_time")

    no_initiatives = [f for f in failures if not f.initiatives_used]
    if len(no_initiatives) > len(failures) / 2:
        factors.append("no_documented_initiatives")

    # Check for cases where achieved went in wrong direction
    wrong_dir = [
        f for f in failures
        if abs(f.target_value - f.initial_value) > 1e-12
        and (f.achieved_value - f.initial_value) * (f.target_value - f.initial_value) < 0
    ]
    if wrong_dir:
        factors.append("metric_regressed")

    return factors


def _build_recommendation(
    lever: str, pattern: str, success_rate: float,
    common_initiatives: List[str], failure_factors: List[str],
) -> str:
    """Plain-English recommendation string."""
    parts = []
    pct = f"{success_rate * 100:.0f}%"
    parts.append(
        f"Historical success rate for {lever} in {pattern} hospitals: {pct}."
    )
    if common_initiatives:
        top = ", ".join(common_initiatives[:3])
        parts.append(f"Most effective initiatives: {top}.")
    if failure_factors:
        factors_str = ", ".join(f.replace("_", " ") for f in failure_factors)
        parts.append(f"Watch for: {factors_str}.")
    if success_rate >= 0.7:
        parts.append("Strong historical precedent — recommend proceeding.")
    elif success_rate >= 0.4:
        parts.append("Mixed results — proceed with enhanced monitoring.")
    else:
        parts.append("Low historical success — consider alternative approaches.")
    return " ".join(parts)


# ── Public API ─────────────────────────────────────────────────────

def build_playbook(store: Any, deal_id: str) -> List[PlaybookEntry]:
    """Build an operational playbook for a deal.

    For each lever in the deal's v2 bridge, finds historical deals
    with the same pattern archetype and computes success statistics.
    Returns an empty list when insufficient history exists.
    """
    profile = _load_profile(store, deal_id)
    lever_impacts = _load_lever_impacts(store, deal_id)
    if not lever_impacts:
        return []

    all_deals = _all_deal_ids(store)
    # Exclude the current deal from the historical pool
    historical_deals = [d for d in all_deals if d != deal_id]

    # Pre-load profiles and classify each historical deal
    deal_patterns: Dict[str, str] = {}
    deal_plans: Dict[str, Optional[Dict[str, Any]]] = {}
    deal_actuals: Dict[str, List[Dict[str, Any]]] = {}
    deal_lever_impacts: Dict[str, List[Dict[str, Any]]] = {}

    for hd in historical_deals:
        hp = _load_profile(store, hd)
        # Use the current lever's metric_key for pattern classification
        # (pattern may vary by metric — a simplification: use first lever)
        deal_patterns[hd] = _classify_pattern("", hp)
        deal_plans[hd] = _load_value_creation_plan(store, hd)
        deal_actuals[hd] = _load_quarterly_actuals(store, hd)
        deal_lever_impacts[hd] = _load_lever_impacts(store, hd)

    entries: List[PlaybookEntry] = []

    for li in lever_impacts:
        lever_key = li.get("metric_key") or ""
        if not lever_key:
            continue

        pattern = _classify_pattern(lever_key, profile)

        # Find historical deals that match this pattern
        matching_outcomes: List[DealOutcome] = []
        for hd in historical_deals:
            hp_pattern = deal_patterns.get(hd, "general")
            if hp_pattern != pattern:
                continue
            outcome = _extract_deal_outcome(
                hd, lever_key,
                deal_plans.get(hd),
                deal_actuals.get(hd, []),
                deal_lever_impacts.get(hd, []),
            )
            if outcome is not None:
                matching_outcomes.append(outcome)

        if len(matching_outcomes) < MIN_MATCHING_DEALS:
            continue

        # Compute statistics
        successes = [o for o in matching_outcomes if o.success]
        success_rate = len(successes) / len(matching_outcomes)

        achievement_pcts = [
            _achievement_pct(o.initial_value, o.target_value, o.achieved_value)
            for o in matching_outcomes
        ]
        avg_achievement = (
            sum(achievement_pcts) / len(achievement_pcts)
            if achievement_pcts else 0.0
        )

        # Common initiatives — rank by frequency across successful deals
        initiative_counts: Dict[str, int] = {}
        for o in successes:
            for ini in o.initiatives_used:
                initiative_counts[ini] = initiative_counts.get(ini, 0) + 1
        common_initiatives = sorted(
            initiative_counts, key=initiative_counts.get, reverse=True  # type: ignore[arg-type]
        )[:5]

        failure_factors = _infer_failure_factors(matching_outcomes)

        recommendation = _build_recommendation(
            lever_key, pattern, success_rate,
            common_initiatives, failure_factors,
        )

        entries.append(PlaybookEntry(
            lever=lever_key,
            pattern=pattern,
            matching_deals=matching_outcomes,
            success_rate=success_rate,
            avg_achievement_pct=avg_achievement,
            common_initiatives=common_initiatives,
            failure_factors=failure_factors,
            recommendation=recommendation,
        ))

    return entries
