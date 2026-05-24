"""Home Health agency loaders (Sector Intelligence Phase 2A).

Reads vendored CMS Provider Data Catalog snapshots — `home_health_providers.csv`
and `home_health_quality.csv` (derived from "Home Health Care Agencies",
dataset 6jpm-sxkc). One-time vendored data; **no runtime network calls**.

Scope/limits: Medicare-certified home health agencies only — commercial /
private-pay home care is not represented. Quality fields are the
publicly-reported measures present in that dataset (star rating, timely
initiation, improvement in ambulation/bed-transfer/bathing, discharge to
community); claims-based acute-care-hospitalization / ED-use measures are a
separate CMS dataset (not yet vendored).
"""
from __future__ import annotations

import csv
import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_PROVIDERS_CSV = Path(__file__).with_name("home_health_providers.csv")
_QUALITY_CSV = Path(__file__).with_name("home_health_quality.csv")
# Patient-experience survey (HHCAHPS) — vendored from the CMS facility file.
# Adds the patient-voice dimension the HH vertical previously lacked.
_CAHPS_CSV = Path(__file__).with_name("home_health_cahps.csv")
_CAHPS_METRICS = ("cahps_summary_star", "cahps_professional_star",
                  "cahps_communication_star", "cahps_medicines_star",
                  "cahps_overall_star", "cahps_overall_9_10_pct",
                  "cahps_recommend_pct")


@dataclass(frozen=True)
class HomeHealthProvider:
    ccn: str
    provider_name: str
    address: str
    city: str
    state: str
    zip: str
    ownership: str
    certification_date: str
    source: str
    source_date: str


def _norm_ccn(v: str) -> str:
    return (v or "").strip()


def _norm_state(v: str) -> str:
    return (v or "").strip().upper()


def _f(v: str) -> Optional[float]:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


@functools.lru_cache(maxsize=1)
def load_home_health_providers() -> Dict[str, HomeHealthProvider]:
    """``{ccn: HomeHealthProvider}`` from the vendored file ({} if missing)."""
    out: Dict[str, HomeHealthProvider] = {}
    if not _PROVIDERS_CSV.is_file():
        return out
    with _PROVIDERS_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _norm_ccn(r.get("ccn", ""))
            if not ccn:
                continue
            out[ccn] = HomeHealthProvider(
                ccn=ccn,
                provider_name=(r.get("provider_name") or "").strip(),
                address=(r.get("address") or "").strip(),
                city=(r.get("city") or "").strip(),
                state=_norm_state(r.get("state", "")),
                zip=(r.get("zip") or "").strip(),
                ownership=(r.get("ownership") or "").strip(),
                certification_date=(r.get("certification_date") or "").strip(),
                source=(r.get("source") or "").strip(),
                source_date=(r.get("source_date") or "").strip(),
            )
    return out


@functools.lru_cache(maxsize=1)
def load_home_health_quality() -> Dict[str, Dict[str, Optional[float]]]:
    """``{ccn: {metric: float|None}}`` for the publicly-reported HH measures."""
    out: Dict[str, Dict[str, Optional[float]]] = {}
    if not _QUALITY_CSV.is_file():
        return out
    metrics = ("star_rating", "timely_initiation_pct", "improve_ambulation_pct",
               "improve_bed_transfer_pct", "improve_bathing_pct",
               "discharge_to_community_rate")
    with _QUALITY_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _norm_ccn(r.get("ccn", ""))
            if not ccn:
                continue
            out[ccn] = {m: _f(r.get(m, "")) for m in metrics}
    # Merge the patient-experience (HHCAHPS) measures so they flow through the
    # screener, cross-sector benchmark, and X-Ray alongside the clinical ones.
    # Agencies without a CAHPS row simply carry None for these keys (≈5.4k of
    # 12.4k have no survey data — surfaced honestly, never fabricated).
    cahps = load_home_health_cahps()
    for ccn, row in out.items():
        cr = cahps.get(ccn) or {}
        for m in _CAHPS_METRICS:
            row[m] = cr.get(m)
    return out


@functools.lru_cache(maxsize=1)
def load_home_health_cahps() -> Dict[str, Dict[str, Optional[float]]]:
    """``{ccn: {cahps_metric: float|None}}`` from the vendored HHCAHPS file."""
    out: Dict[str, Dict[str, Optional[float]]] = {}
    if not _CAHPS_CSV.is_file():
        return out
    with _CAHPS_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _norm_ccn(r.get("ccn", ""))
            if not ccn:
                continue
            out[ccn] = {m: _f(r.get(m, "")) for m in _CAHPS_METRICS}
    return out


def home_health_providers_for_state(state: str) -> List[HomeHealthProvider]:
    st = _norm_state(state)
    rows = [p for p in load_home_health_providers().values() if p.state == st]
    return sorted(rows, key=lambda p: p.provider_name)


def load_home_health_summary_by_state() -> Dict[str, Dict[str, object]]:
    """Per-state: agency count, # with a star rating, average star rating.

    Simple counts/averages only — no composite scores invented here.
    """
    providers = load_home_health_providers()
    quality = load_home_health_quality()
    summary: Dict[str, Dict[str, object]] = {}
    for ccn, p in providers.items():
        st = p.state
        if not st:
            continue
        s = summary.setdefault(st, {"agencies": 0, "rated": 0, "_star_sum": 0.0})
        s["agencies"] = int(s["agencies"]) + 1
        star = (quality.get(ccn) or {}).get("star_rating")
        if star is not None:
            s["rated"] = int(s["rated"]) + 1
            s["_star_sum"] = float(s["_star_sum"]) + star
    for st, s in summary.items():
        rated = int(s["rated"])
        s["avg_star_rating"] = round(float(s["_star_sum"]) / rated, 2) if rated else None
        del s["_star_sum"]
    return summary
