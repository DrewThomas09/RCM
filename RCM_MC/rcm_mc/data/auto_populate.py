"""One-name → pre-populated deal.

An associate types a hospital name. Before Prompt 23 they then spent
8-12 hours looking up the CCN in HCRIS, cross-referencing Care
Compare, pulling the IRS 990 filing, then hand-entering 15+ fields
into the packet builder. Every one of those data sources is already
loaded into the ``hospital_benchmarks`` table by
:mod:`rcm_mc.data.data_refresh` — the platform already *has* the
data. What was missing was the merge, the provenance, and the gap
analysis.

This module is the assembly layer. It does **not** fetch from any
external URL — everything comes out of the existing local SQLite
tables (``hcris`` via the shipped .csv.gz and ``hospital_benchmarks``
from the refresh pipeline).

Primary entry point is :func:`auto_populate` — name/CCN in, a single
:class:`AutoPopulateResult` out with candidates, merged profile +
financials + quality + utilization, per-field source attribution,
and a ranked list of what's still missing.
"""
from __future__ import annotations

import difflib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from . import hcris as _hcris

logger = logging.getLogger(__name__)


# ── Source ordering (higher → more trusted, first to win a merge) ──

# Keyed on the ``source`` column of ``hospital_benchmarks``. Higher
# integer wins when multiple sources carry the same metric for the
# same provider. Partner-observable (we surface the winning source
# in :class:`SourceAttribution`) so disputes are auditable.
_SOURCE_PRIORITY: Dict[str, int] = {
    "HCRIS":         100,
    "CMS_HCRIS":     100,   # alias — older refresh writes used this
    "CMS_CARE_COMPARE": 80,
    "CARE_COMPARE":  80,
    "CMS_UTILIZATION": 70,
    "UTILIZATION":   70,
    "IRS_990":       50,
    "IRS990":        50,
}


def _source_priority(source: str) -> int:
    return _SOURCE_PRIORITY.get(str(source).upper(), 0)


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class HospitalMatch:
    """One candidate from a fuzzy-name search."""
    ccn: str
    name: str
    city: str
    state: str
    bed_count: int
    confidence: float            # SequenceMatcher ratio, 0.0-1.0
    system_affiliation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ccn": self.ccn,
            "name": self.name,
            "city": self.city,
            "state": self.state,
            "bed_count": int(self.bed_count or 0),
            "confidence": float(self.confidence),
            "system_affiliation": self.system_affiliation,
        }


@dataclass
class SourceAttribution:
    """Per-field provenance for the UI.

    Every populated value in :class:`AutoPopulateResult` carries one
    of these so the workbench can render source badges ("HCRIS", "CMS
    Care Compare") alongside the value. ``freshness_days`` drives the
    "data is stale" UI hint at ≥ 365 days.
    """
    field: str
    value: Any
    source: str
    period: str = ""
    freshness_days: int = 0
    confidence: str = "MEDIUM"   # HIGH | MEDIUM | LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "source": self.source,
            "period": self.period,
            "freshness_days": int(self.freshness_days),
            "confidence": self.confidence,
        }


@dataclass
class GapItem:
    """A metric the system couldn't fill from public data.

    Sorted by ``ebitda_sensitivity_rank`` so the associate sees the
    highest-leverage gaps at the top of their to-do list.
    """
    metric_key: str
    display_name: str
    ebitda_sensitivity_rank: int
    why_it_matters: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_key": self.metric_key,
            "display_name": self.display_name,
            "ebitda_sensitivity_rank": int(self.ebitda_sensitivity_rank),
            "why_it_matters": self.why_it_matters,
        }


@dataclass
class AutoPopulateResult:
    """The complete pre-population package returned to the caller.

    Shape chosen so callers (deal-new CLI, wizard UI, packet builder
    step 2) can consume whichever section they need without having to
    pick apart a monolithic blob.
    """
    query: str = ""
    matches: List[HospitalMatch] = field(default_factory=list)
    selected: Optional[HospitalMatch] = None
    profile: Dict[str, Any] = field(default_factory=dict)
    financials: Dict[str, Any] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    utilization: Dict[str, Any] = field(default_factory=dict)
    benchmark_metrics: Dict[str, float] = field(default_factory=dict)
    sources: List[SourceAttribution] = field(default_factory=list)
    gaps: List[GapItem] = field(default_factory=list)
    coverage_pct: float = 0.0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "matches": [m.to_dict() for m in self.matches],
            "selected": self.selected.to_dict() if self.selected else None,
            "profile": dict(self.profile),
            "financials": dict(self.financials),
            "quality": dict(self.quality),
            "utilization": dict(self.utilization),
            "benchmark_metrics": dict(self.benchmark_metrics),
            "sources": [s.to_dict() for s in self.sources],
            "gaps": [g.to_dict() for g in self.gaps],
            "coverage_pct": float(self.coverage_pct),
            "summary": self.summary,
        }


# ── Fuzzy matching ─────────────────────────────────────────────────

# If the query is all digits (optionally with a leading zero pad)
# we treat it as a CCN lookup.
def _looks_like_ccn(q: str) -> bool:
    stripped = q.strip()
    return stripped.isdigit() and 3 <= len(stripped) <= 6


def _split_state(query: str) -> Tuple[str, Optional[str]]:
    """Parse ``"Acme Regional, CA"`` → ("Acme Regional", "CA"). A
    bare query returns ``(query, None)``."""
    if "," in query:
        name, state = query.rsplit(",", 1)
        state = state.strip().upper()
        if len(state) == 2 and state.isalpha():
            return name.strip(), state
    return query.strip(), None


def _hcris_row_to_match(row: Dict[str, Any], query: str) -> HospitalMatch:
    name = str(row.get("name") or "")
    ratio = difflib.SequenceMatcher(
        None, query.upper(), name.upper(),
    ).ratio() if query else 1.0
    return HospitalMatch(
        ccn=str(row.get("ccn") or ""),
        name=name,
        city=str(row.get("city") or ""),
        state=str(row.get("state") or ""),
        bed_count=int(row.get("beds") or 0),
        confidence=float(ratio),
        system_affiliation=row.get("system_affiliation") or None,
    )


def _fuzzy_match(query: str, limit: int = 3) -> List[HospitalMatch]:
    """Return up to ``limit`` candidates ranked by name-match score.

    Accepts a bare hospital name, a 6-digit CCN, or ``"Name, ST"``.
    Wraps :func:`rcm_mc.data.hcris.lookup_by_name` /
    :func:`lookup_by_ccn` rather than re-implementing the CSV read
    path; the shipped HCRIS archive is what we already search in the
    workbench comparables picker, so we stay consistent.
    """
    if not isinstance(query, str) or not query.strip():
        return []

    if _looks_like_ccn(query):
        row = _hcris.lookup_by_ccn(query.strip())
        if row is None:
            return []
        m = _hcris_row_to_match(row, query)
        m.confidence = 1.0    # exact CCN hit
        return [m]

    name_only, state = _split_state(query)
    raw = _hcris.lookup_by_name(
        name_only, state=state, limit=int(limit) * 3,
    )
    matches = [_hcris_row_to_match(r, name_only) for r in raw]
    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches[:int(limit)]


def search_hospitals(query: str, limit: int = 5) -> List[HospitalMatch]:
    """Public typeahead endpoint used by the wizard UI.

    Kept distinct from :func:`_fuzzy_match` so callers can tune the
    limit without importing the underscore-prefixed helper.
    """
    return _fuzzy_match(query, limit=limit)


# ── Benchmark merge ────────────────────────────────────────────────

def _load_benchmark_rows(
    store: Any, provider_id: str,
) -> List[Dict[str, Any]]:
    """Pull every ``hospital_benchmarks`` row for one provider.

    Returns an empty list when the table doesn't exist (e.g. test
    fixtures that never called ``data_refresh``) — callers still get
    a valid ``AutoPopulateResult`` seeded from HCRIS alone.
    """
    try:
        store.init_db()
        with store.connect() as con:
            # Don't hard-depend on the table existing — an install
            # that's never run a refresh still works.
            cols = [
                r["name"] for r in con.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='hospital_benchmarks'",
                ).fetchall()
            ]
            if not cols:
                return []
            rows = con.execute(
                """SELECT source, metric_key, value, text_value, period,
                          loaded_at, quality_flags
                   FROM hospital_benchmarks
                   WHERE provider_id = ?""",
                (str(provider_id),),
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        logger.debug("benchmark fetch failed for %s: %s", provider_id, exc)
        return []
    return [dict(r) for r in rows]


def _freshness_days(loaded_at: str) -> int:
    """How old (in calendar days) is a ``loaded_at`` ISO timestamp?

    Negative values (future timestamps) are clamped to 0 — corrupt
    data shouldn't crash the merge. Unparseable timestamps return 0
    and the caller treats as "freshness unknown".
    """
    if not loaded_at:
        return 0
    try:
        ts = datetime.fromisoformat(str(loaded_at))
    except ValueError:
        return 0
    now = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = (now - ts).days
    return max(0, int(delta))


def _confidence_for(source: str, freshness_days: int) -> str:
    """Label the confidence band for a source+freshness combination."""
    base = _source_priority(source)
    if base >= 100:
        top = "HIGH"
    elif base >= 70:
        top = "MEDIUM"
    else:
        top = "LOW"
    if freshness_days >= 540:
        # Anything older than ~18 months loses a band.
        return {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "LOW"}[top]
    return top


# Fields we surface in each category bucket. Names match what the
# packet builder expects under ``financials`` / ``profile``.
_PROFILE_KEYS = {
    "name", "state", "city", "beds", "bed_count",
    "system_affiliation", "ownership", "zip",
    "medicare_day_pct", "medicaid_day_pct", "commercial_day_pct",
    "self_pay_day_pct", "payer_mix",
}
_FINANCIAL_KEYS = {
    "gross_revenue", "gross_patient_revenue",
    "net_patient_revenue", "net_revenue",
    "operating_expenses", "total_operating_expenses",
    "net_income", "ebitda", "current_ebitda",
    "bad_debt", "total_assets", "total_liabilities",
    "days_cash_on_hand", "ebitda_margin",
}
_QUALITY_KEYS = {
    "star_rating", "readmission_rate", "mortality_rate",
    "patient_experience", "hcahps_overall",
    "safety_composite",
}
_UTILIZATION_KEYS = {
    "total_patient_days", "discharges", "avg_los",
    "case_mix_index", "cmi", "total_inpatient_discharges",
    "emergency_visits", "outpatient_visits", "top_drgs",
}


def _bucket_for(metric_key: str) -> str:
    k = metric_key.lower()
    if k in _FINANCIAL_KEYS:
        return "financials"
    if k in _QUALITY_KEYS:
        return "quality"
    if k in _UTILIZATION_KEYS:
        return "utilization"
    if k in _PROFILE_KEYS:
        return "profile"
    return "benchmark_metrics"


def _merge_all_sources(
    store: Any, ccn: str, hcris_row: Optional[Dict[str, Any]],
) -> Tuple[
    Dict[str, Any], Dict[str, Any], Dict[str, Any],
    Dict[str, Any], Dict[str, float], List[SourceAttribution],
]:
    """Merge HCRIS (shipped) + ``hospital_benchmarks`` into bucketed
    dicts with per-field source attribution.

    Priority: OBSERVED (not here yet) > HCRIS > Care Compare >
    Utilization > IRS 990. Ties broken by fresher ``loaded_at``.
    Returns ``(profile, financials, quality, utilization,
    benchmark_metrics, sources)``.
    """
    profile: Dict[str, Any] = {}
    financials: Dict[str, Any] = {}
    quality: Dict[str, Any] = {}
    utilization: Dict[str, Any] = {}
    benchmark_metrics: Dict[str, float] = {}
    sources: List[SourceAttribution] = []

    # Track which source won each field so we can upgrade when a
    # stronger source appears later.
    winning_priority: Dict[str, int] = {}
    winning_freshness: Dict[str, int] = {}

    def _place(
        field_name: str, value: Any, source: str,
        period: str, freshness_days: int,
    ) -> None:
        if value is None or value == "":
            return
        prio = _source_priority(source)
        existing_prio = winning_priority.get(field_name, -1)
        existing_fresh = winning_freshness.get(field_name, 10_000)
        if prio < existing_prio:
            return
        if prio == existing_prio and freshness_days >= existing_fresh:
            return
        winning_priority[field_name] = prio
        winning_freshness[field_name] = freshness_days
        bucket = {
            "profile": profile, "financials": financials,
            "quality": quality, "utilization": utilization,
            "benchmark_metrics": benchmark_metrics,
        }[_bucket_for(field_name)]
        bucket[field_name] = value
        # Replace prior source attribution for this field — the
        # winning one is the only one users need to see.
        for i, s in enumerate(sources):
            if s.field == field_name:
                sources.pop(i)
                break
        sources.append(SourceAttribution(
            field=field_name, value=value, source=source,
            period=period, freshness_days=freshness_days,
            confidence=_confidence_for(source, freshness_days),
        ))

    # 1. HCRIS shipped row — every key is "HCRIS" source with fiscal
    #    year as period. Bed count + payer-day pcts + operating
    #    financials all live here.
    if hcris_row:
        fy = hcris_row.get("fiscal_year") or ""
        period = f"FY{fy}" if fy else ""
        # HCRIS rows are "current" as of the shipped dataset — we
        # don't have a loaded_at timestamp, so treat as 30-day fresh.
        freshness = 30
        for k, v in hcris_row.items():
            if k in ("_score",):
                continue
            if isinstance(v, (int, float, str, bool)):
                # Translate HCRIS's ``beds`` to both keys so downstream
                # that expects ``bed_count`` picks it up.
                if k == "beds":
                    _place("bed_count", int(v) if v else 0, "HCRIS",
                           period, freshness)
                _place(k, v, "HCRIS", period, freshness)

    # 2. hospital_benchmarks — every source/metric/period row.
    for row in _load_benchmark_rows(store, ccn):
        source = row.get("source") or ""
        metric = row.get("metric_key") or ""
        period = row.get("period") or ""
        freshness = _freshness_days(row.get("loaded_at") or "")
        value: Any = row.get("value")
        if value is None:
            value = row.get("text_value")
        _place(metric, value, source, period, freshness)

    # Derive payer_mix dict from HCRIS day percentages if not
    # otherwise provided.
    if "payer_mix" not in profile:
        mix: Dict[str, float] = {}
        for key_hcris, key_pkt in (
            ("medicare_day_pct", "medicare"),
            ("medicaid_day_pct", "medicaid"),
            ("commercial_day_pct", "commercial"),
            ("self_pay_day_pct", "self_pay"),
        ):
            v = profile.get(key_hcris)
            if v is not None:
                try:
                    mix[key_pkt] = float(v) / 100.0
                except (TypeError, ValueError):
                    continue
        if mix:
            profile["payer_mix"] = mix

    return profile, financials, quality, utilization, benchmark_metrics, sources


# ── Gap computation ────────────────────────────────────────────────

def _compute_gaps(
    benchmark_metrics: Dict[str, float],
    financials: Dict[str, Any],
    quality: Dict[str, Any],
    utilization: Dict[str, Any],
) -> List[GapItem]:
    """Enumerate registry metrics that weren't populated from any
    public source. Sorted by EBITDA sensitivity so the top gap is the
    most valuable thing to ask the seller for."""
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
    except Exception:  # noqa: BLE001
        return []
    try:
        from ..domain.econ_ontology import causal_graph
        graph = causal_graph()
    except Exception:  # noqa: BLE001
        graph = None

    populated_keys = set(benchmark_metrics.keys())
    populated_keys.update(financials.keys())
    populated_keys.update(quality.keys())
    populated_keys.update(utilization.keys())

    gaps: List[GapItem] = []
    for key, meta in RCM_METRIC_REGISTRY.items():
        if key in populated_keys:
            continue
        why = ""
        if graph is not None:
            node = graph.nodes.get(key) if hasattr(graph, "nodes") else None
            if node is not None:
                why = getattr(node, "description", "") or ""
        if not why:
            why = meta.get("display_name") or key
        gaps.append(GapItem(
            metric_key=key,
            display_name=meta.get("display_name") or key,
            ebitda_sensitivity_rank=int(
                meta.get("ebitda_sensitivity_rank") or 99,
            ),
            why_it_matters=str(why),
        ))
    gaps.sort(key=lambda g: g.ebitda_sensitivity_rank)
    return gaps


def _coverage_pct(
    benchmark_metrics: Dict[str, float],
    financials: Dict[str, Any],
    quality: Dict[str, Any],
    utilization: Dict[str, Any],
) -> Tuple[float, int, int]:
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
    except Exception:  # noqa: BLE001
        return 0.0, 0, 0
    total = len(RCM_METRIC_REGISTRY)
    if total == 0:
        return 0.0, 0, 0
    populated_keys = set(benchmark_metrics.keys())
    populated_keys.update(financials.keys())
    populated_keys.update(quality.keys())
    populated_keys.update(utilization.keys())
    hits = sum(1 for k in RCM_METRIC_REGISTRY if k in populated_keys)
    return (hits / total) * 100.0, hits, total


# ── Public entry ──────────────────────────────────────────────────

_AUTO_SELECT_CONFIDENCE = 0.90


def auto_populate(store: Any, query: str) -> AutoPopulateResult:
    """Return a :class:`AutoPopulateResult` for ``query``.

    Flow:
      1. Fuzzy match ``query`` against HCRIS (name / CCN / "name, ST").
      2. If the top match is ≥ 0.90 confidence, auto-select it.
         Otherwise return candidates and let the caller pick.
      3. Merge the HCRIS row + ``hospital_benchmarks`` into the
         bucketed dicts with source attribution.
      4. Compute the gaps against :data:`RCM_METRIC_REGISTRY`.

    Safe for edge cases: empty query → empty result; missing
    benchmarks table → falls back to HCRIS alone; unknown CCN →
    matches=[], selected=None.
    """
    result = AutoPopulateResult(query=str(query or ""))
    matches = _fuzzy_match(result.query, limit=3)
    result.matches = matches
    if not matches:
        result.summary = "No hospitals matched the query."
        return result

    top = matches[0]
    if top.confidence >= _AUTO_SELECT_CONFIDENCE:
        result.selected = top

    # We do merge even when not auto-selected — the wizard shows the
    # top candidate's populated data so the associate can confirm.
    chosen_ccn = top.ccn
    hcris_row = _hcris.lookup_by_ccn(chosen_ccn)
    (
        result.profile, result.financials, result.quality,
        result.utilization, result.benchmark_metrics, result.sources,
    ) = _merge_all_sources(store, chosen_ccn, hcris_row)

    coverage, hits, total = _coverage_pct(
        result.benchmark_metrics, result.financials,
        result.quality, result.utilization,
    )
    result.coverage_pct = coverage
    result.gaps = _compute_gaps(
        result.benchmark_metrics, result.financials,
        result.quality, result.utilization,
    )

    distinct_sources = sorted({s.source for s in result.sources})
    result.summary = (
        f"Populated {hits}/{total} metrics from "
        f"{len(distinct_sources)} source(s): "
        f"{', '.join(distinct_sources) if distinct_sources else 'none'}."
    )
    return result
