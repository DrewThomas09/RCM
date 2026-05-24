"""Dialysis facility loaders (Sector Intelligence — Dialysis vertical).

Reads vendored CMS **Dialysis Facility Compare — Listing by Facility**
snapshots (`dialysis_providers.csv` + `dialysis_quality.csv`, normalized once
from the official `DFC_FACILITY` file, Mar 2026). One-time vendored data;
**no runtime network calls**.

Scope/limits: Medicare-certified dialysis facilities only. Fields are the
publicly-reported CMS values — the overall five-star rating, dialysis-station
count, ownership/chain, modality offerings, and the risk-adjusted outcome
rates (mortality, hospitalization, readmission, transfusion). The outcome
rates are **lower-is-better** and risk-adjusted estimates with confidence
intervals — not commercial revenue, not a quality verdict in isolation.
"""
from __future__ import annotations

import csv
import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_PROVIDERS_CSV = Path(__file__).with_name("dialysis_providers.csv")
_QUALITY_CSV = Path(__file__).with_name("dialysis_quality.csv")
# Patient experience (ICH CAHPS in-center hemodialysis survey) — vendored from
# the CMS facility file. Adds the patient-voice dimension to the clinical rates.
_CAHPS_CSV = Path(__file__).with_name("dialysis_cahps.csv")
_CAHPS_METRICS = ("cahps_facility_star", "cahps_nephrologist_comm_star",
                  "cahps_center_care_star", "cahps_information_star",
                  "cahps_nephrologist_star", "cahps_staff_star")

_QUALITY_METRICS = (
    "five_star", "mortality_rate", "hospitalization_rate",
    "readmission_rate", "transfusion_rate",
)


@dataclass(frozen=True)
class DialysisProvider:
    ccn: str
    facility_name: str
    address: str
    city: str
    state: str
    zip: str
    county: str
    ownership: str
    chain_owned: str
    chain_org: str
    dialysis_stations: Optional[int]
    offers_in_center_hd: str
    offers_peritoneal: str
    offers_home_hd: str
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


def _i(v: str) -> Optional[int]:
    f = _f(v)
    return int(f) if f is not None else None


@functools.lru_cache(maxsize=1)
def load_dialysis_providers() -> Dict[str, DialysisProvider]:
    """``{ccn: DialysisProvider}`` from the vendored file ({} if missing)."""
    out: Dict[str, DialysisProvider] = {}
    if not _PROVIDERS_CSV.is_file():
        return out
    with _PROVIDERS_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _norm_ccn(r.get("ccn", ""))
            if not ccn:
                continue
            out[ccn] = DialysisProvider(
                ccn=ccn,
                facility_name=(r.get("facility_name") or "").strip(),
                address=(r.get("address") or "").strip(),
                city=(r.get("city") or "").strip(),
                state=_norm_state(r.get("state", "")),
                zip=(r.get("zip") or "").strip(),
                county=(r.get("county") or "").strip(),
                ownership=(r.get("ownership") or "").strip(),
                chain_owned=(r.get("chain_owned") or "").strip(),
                chain_org=(r.get("chain_org") or "").strip(),
                dialysis_stations=_i(r.get("dialysis_stations", "")),
                offers_in_center_hd=(r.get("offers_in_center_hd") or "").strip(),
                offers_peritoneal=(r.get("offers_peritoneal") or "").strip(),
                offers_home_hd=(r.get("offers_home_hd") or "").strip(),
                certification_date=(r.get("certification_date") or "").strip(),
                source=(r.get("source") or "").strip(),
                source_date=(r.get("source_date") or "").strip(),
            )
    return out


@functools.lru_cache(maxsize=1)
def load_dialysis_quality() -> Dict[str, Dict[str, Optional[float]]]:
    """``{ccn: {metric: float|None}}`` for the publicly-reported measures."""
    out: Dict[str, Dict[str, Optional[float]]] = {}
    if not _QUALITY_CSV.is_file():
        return out
    with _QUALITY_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _norm_ccn(r.get("ccn", ""))
            if not ccn:
                continue
            out[ccn] = {m: _f(r.get(m, "")) for m in _QUALITY_METRICS}
    # Merge the patient-experience (ICH CAHPS) star ratings so they flow
    # through the screener, cross-sector benchmark, and X-Ray with the clinical
    # rates. Facilities without a survey carry None (honest).
    cahps = load_dialysis_cahps()
    for ccn, row in out.items():
        cr = cahps.get(ccn) or {}
        for m in _CAHPS_METRICS:
            row[m] = cr.get(m)
    return out


@functools.lru_cache(maxsize=1)
def load_dialysis_cahps() -> Dict[str, Dict[str, Optional[float]]]:
    """``{ccn: {cahps_metric: float|None}}`` from the vendored ICH-CAHPS file."""
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


def dialysis_providers_for_state(state: str) -> List[DialysisProvider]:
    st = _norm_state(state)
    rows = [p for p in load_dialysis_providers().values() if p.state == st]
    return sorted(rows, key=lambda p: p.facility_name)


def dialysis_provider_by_ccn(ccn: str) -> Optional[DialysisProvider]:
    return load_dialysis_providers().get(_norm_ccn(ccn))


def load_dialysis_summary_by_state() -> Dict[str, Dict[str, object]]:
    """Per-state: facility count, # with a five-star rating, avg five-star."""
    providers = load_dialysis_providers()
    quality = load_dialysis_quality()
    summary: Dict[str, Dict[str, object]] = {}
    for ccn, p in providers.items():
        st = p.state
        if not st:
            continue
        s = summary.setdefault(st, {"facilities": 0, "rated": 0, "_star_sum": 0.0})
        s["facilities"] = int(s["facilities"]) + 1
        star = (quality.get(ccn) or {}).get("five_star")
        if star is not None:
            s["rated"] = int(s["rated"]) + 1
            s["_star_sum"] = float(s["_star_sum"]) + star
    for st, s in summary.items():
        rated = int(s["rated"])
        s["avg_five_star"] = round(float(s["_star_sum"]) / rated, 2) if rated else None
        del s["_star_sum"]
    return summary
