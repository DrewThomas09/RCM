"""ClinicalTrials.gov v2 — study normalization + competitive-landscape rollup.

The vendored ``data/clinical_trials.py`` reads a committed phase-count snapshot;
the ``clinicaltrials_search`` scaffold in ``public_api_clients`` hits the live
v2 API but returns raw, deeply-nested study JSON. This module is the missing
middle: flatten a v2 study into a stable record, and roll a set of studies up
into the **pipeline / competitive landscape** view diligence actually wants
(who is running what, at which phase, how much enrollment).

Pure functions over already-fetched study dicts — no network here, so the
whole thing is offline-testable. Live fetching stays in
``public_api_clients.clinicaltrials_search`` (injectable opener). Missing
fields normalize to ``""`` / ``None`` / ``[]``; nothing is fabricated.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional


def _proto(study: Dict[str, Any]) -> Dict[str, Any]:
    p = study.get("protocolSection", study)
    return p if isinstance(p, dict) else {}


def _enrollment(design: Dict[str, Any]) -> Optional[int]:
    info = design.get("enrollmentInfo", {}) if isinstance(design, dict) else {}
    val = info.get("count")
    if val is None:
        return None
    try:
        n = int(val)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def clinicaltrials_normalize(study: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten one v2 study into ``{nct_id, title, sponsor, phase, status,
    conditions, enrollment}``. A study may list several phases; ``phase`` is a
    single joined string (e.g. ``"PHASE2|PHASE3"``) so the raw fidelity is kept
    rather than silently collapsing to one."""
    proto = _proto(study)
    ident = proto.get("identificationModule", {}) or {}
    spons = proto.get("sponsorCollaboratorsModule", {}) or {}
    design = proto.get("designModule", {}) or {}
    status = proto.get("statusModule", {}) or {}
    conds = proto.get("conditionsModule", {}) or {}

    lead = spons.get("leadSponsor", {}) or {}
    phases = design.get("phases", []) or []
    if not isinstance(phases, list):
        phases = [str(phases)]

    return {
        "nct_id": str(ident.get("nctId", "") or ""),
        "title": str(ident.get("briefTitle", "") or ""),
        "sponsor": str(lead.get("name", "") or ""),
        "phase": "|".join(str(p) for p in phases),
        "status": str(status.get("overallStatus", "") or ""),
        "conditions": [str(c) for c in (conds.get("conditions", []) or [])],
        "enrollment": _enrollment(design),
    }


def clinicaltrials_landscape(studies: List[Dict[str, Any]]
                             ) -> List[Dict[str, Any]]:
    """Competitive-landscape rollup by lead sponsor over a set of *raw* v2
    studies. Each row: ``{sponsor, trials, total_enrollment, by_phase}`` where
    ``by_phase`` maps each phase token to a trial count. Sorted by trial count
    desc, then sponsor — a stable, deterministic competitive ranking.

    Enrollment sums only the studies that report a count; a sponsor with all
    counts missing has ``total_enrollment=None`` (distinguishable from a real
    zero) rather than a fabricated total."""
    trials: Dict[str, int] = defaultdict(int)
    enroll_sum: Dict[str, int] = defaultdict(int)
    enroll_seen: Dict[str, bool] = defaultdict(bool)
    by_phase: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for raw in studies:
        rec = clinicaltrials_normalize(raw)
        sponsor = rec["sponsor"] or "(unknown sponsor)"
        trials[sponsor] += 1
        if rec["enrollment"] is not None:
            enroll_sum[sponsor] += rec["enrollment"]
            enroll_seen[sponsor] = True
        for token in (rec["phase"].split("|") if rec["phase"] else ["(no phase)"]):
            by_phase[sponsor][token] += 1

    rows: List[Dict[str, Any]] = []
    for sponsor in trials:
        rows.append({
            "sponsor": sponsor,
            "trials": trials[sponsor],
            "total_enrollment": enroll_sum[sponsor] if enroll_seen[sponsor] else None,
            "by_phase": dict(by_phase[sponsor]),
        })
    rows.sort(key=lambda r: (-r["trials"], r["sponsor"]))
    return rows
