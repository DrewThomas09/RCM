"""Hospice provider loaders (Sector Intelligence Phase 2A).

Reads vendored CMS Provider Data Catalog snapshots — `hospice_providers.csv`
(from "Hospice - General Information", yc9t-dgbk) and `hospice_quality.csv`
(selected HIS measures pivoted from "Hospice - Provider Data", 252m-zfp9).
One-time vendored data; **no runtime network calls**.

Scope/limits: Medicare-certified hospices only. Quality fields are the
publicly-reported HIS measures present in that dataset (composite process,
Hospice Care Index, visits in last days of life, pain screening, treatment
preferences, beliefs/values). CAHPS hospice-survey data is a separate
dataset (not yet vendored). Length-of-stay / live-discharge economics are
not in these public quality files.
"""
from __future__ import annotations

import csv
import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_PROVIDERS_CSV = Path(__file__).with_name("hospice_providers.csv")
_QUALITY_CSV = Path(__file__).with_name("hospice_quality.csv")
# Family-caregiver experience (CAHPS Hospice Survey) — vendored from the CMS
# facility file. Adds the patient/family-voice dimension to the HIS measures.
_CAHPS_CSV = Path(__file__).with_name("hospice_cahps.csv")
_CAHPS_METRICS = ("cahps_summary_star", "cahps_recommend_pct",
                  "cahps_rating_9_10_pct", "cahps_communication_pct",
                  "cahps_symptoms_pct", "cahps_respect_pct",
                  "cahps_timely_pct", "cahps_emotional_pct")

_QUALITY_METRICS = ("composite_process", "care_index_overall", "visits_last_days",
                    "pain_screening", "treatment_preferences", "beliefs_values")


@dataclass(frozen=True)
class HospiceProvider:
    ccn: str
    facility_name: str
    address: str
    city: str
    state: str
    zip: str
    county: str
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
def load_hospice_providers() -> Dict[str, HospiceProvider]:
    """``{ccn: HospiceProvider}`` from the vendored file ({} if missing)."""
    out: Dict[str, HospiceProvider] = {}
    if not _PROVIDERS_CSV.is_file():
        return out
    with _PROVIDERS_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _norm_ccn(r.get("ccn", ""))
            if not ccn:
                continue
            out[ccn] = HospiceProvider(
                ccn=ccn,
                facility_name=(r.get("facility_name") or "").strip(),
                address=(r.get("address") or "").strip(),
                city=(r.get("city") or "").strip(),
                state=_norm_state(r.get("state", "")),
                zip=(r.get("zip") or "").strip(),
                county=(r.get("county") or "").strip(),
                ownership=(r.get("ownership") or "").strip(),
                certification_date=(r.get("certification_date") or "").strip(),
                source=(r.get("source") or "").strip(),
                source_date=(r.get("source_date") or "").strip(),
            )
    return out


@functools.lru_cache(maxsize=1)
def load_hospice_quality() -> Dict[str, Dict[str, Optional[float]]]:
    """``{ccn: {measure: float|None}}`` for the selected HIS measures."""
    out: Dict[str, Dict[str, Optional[float]]] = {}
    if not _QUALITY_CSV.is_file():
        return out
    with _QUALITY_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _norm_ccn(r.get("ccn", ""))
            if not ccn:
                continue
            out[ccn] = {m: _f(r.get(m, "")) for m in _QUALITY_METRICS}
    # Merge the family-caregiver experience (CAHPS) measures so they flow
    # through the screener, cross-sector benchmark, and X-Ray with the HIS
    # process measures. Hospices without a survey carry None (honest).
    cahps = load_hospice_cahps()
    for ccn, row in out.items():
        cr = cahps.get(ccn) or {}
        for m in _CAHPS_METRICS:
            row[m] = cr.get(m)
    return out


@functools.lru_cache(maxsize=1)
def load_hospice_cahps() -> Dict[str, Dict[str, Optional[float]]]:
    """``{ccn: {cahps_metric: float|None}}`` from the vendored CAHPS file."""
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


def hospice_providers_for_state(state: str) -> List[HospiceProvider]:
    st = _norm_state(state)
    rows = [p for p in load_hospice_providers().values() if p.state == st]
    return sorted(rows, key=lambda p: p.facility_name)


def load_hospice_summary_by_state() -> Dict[str, Dict[str, object]]:
    """Per-state: hospice count, # with a Hospice Care Index, avg care index.

    Simple counts/averages only — no composite scores invented here.
    """
    providers = load_hospice_providers()
    quality = load_hospice_quality()
    summary: Dict[str, Dict[str, object]] = {}
    for ccn, p in providers.items():
        st = p.state
        if not st:
            continue
        s = summary.setdefault(st, {"hospices": 0, "rated": 0, "_idx_sum": 0.0})
        s["hospices"] = int(s["hospices"]) + 1
        idx = (quality.get(ccn) or {}).get("care_index_overall")
        if idx is not None:
            s["rated"] = int(s["rated"]) + 1
            s["_idx_sum"] = float(s["_idx_sum"]) + idx
    for st, s in summary.items():
        rated = int(s["rated"])
        s["avg_care_index"] = round(float(s["_idx_sum"]) / rated, 2) if rated else None
        del s["_idx_sum"]
    return summary
