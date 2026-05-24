"""Inpatient Rehabilitation Facility (IRF) loaders — IRF vertical.

Reads vendored CMS **IRF Compare** snapshots (`irf_providers.csv` from
General Information + `irf_quality.csv`, the headline measures pivoted from
the Provider Data file, Feb 2026). One-time vendored data; no runtime
network. Medicare-certified IRFs only (~1.2k facilities — a small universe,
so benchmark with care). Public quality only — not commercial revenue.
"""
from __future__ import annotations

import csv
import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_PROVIDERS_CSV = Path(__file__).with_name("irf_providers.csv")
_QUALITY_CSV = Path(__file__).with_name("irf_quality.csv")
_QUALITY_METRICS = ("dtc_rs_rate", "readmission_rsrr", "mspb_score")


@dataclass(frozen=True)
class IrfProvider:
    ccn: str
    provider_name: str
    address: str
    city: str
    state: str
    zip: str
    county: str
    ownership: str
    certification_date: str
    source: str
    source_date: str


def _ns(v): return (v or "").strip().upper()
def _s(v): return (v or "").strip()
def _f(v):
    v = _s(v)
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


@functools.lru_cache(maxsize=1)
def load_irf_providers() -> Dict[str, IrfProvider]:
    out: Dict[str, IrfProvider] = {}
    if not _PROVIDERS_CSV.is_file():
        return out
    with _PROVIDERS_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _s(r.get("ccn"))
            if not ccn:
                continue
            out[ccn] = IrfProvider(
                ccn=ccn, provider_name=_s(r.get("provider_name")),
                address=_s(r.get("address")), city=_s(r.get("city")),
                state=_ns(r.get("state")), zip=_s(r.get("zip")),
                county=_s(r.get("county")), ownership=_s(r.get("ownership")),
                certification_date=_s(r.get("certification_date")),
                source=_s(r.get("source")), source_date=_s(r.get("source_date")),
            )
    return out


@functools.lru_cache(maxsize=1)
def load_irf_quality() -> Dict[str, Dict[str, Optional[float]]]:
    out: Dict[str, Dict[str, Optional[float]]] = {}
    if not _QUALITY_CSV.is_file():
        return out
    with _QUALITY_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _s(r.get("ccn"))
            if not ccn:
                continue
            out[ccn] = {m: _f(r.get(m)) for m in _QUALITY_METRICS}
    return out


def irf_providers_for_state(state: str) -> List[IrfProvider]:
    st = _ns(state)
    return sorted((p for p in load_irf_providers().values() if p.state == st),
                  key=lambda p: p.provider_name)


def irf_provider_by_ccn(ccn: str) -> Optional[IrfProvider]:
    return load_irf_providers().get(_s(ccn))


def load_irf_summary_by_state() -> Dict[str, Dict[str, object]]:
    providers = load_irf_providers()
    quality = load_irf_quality()
    summary: Dict[str, Dict[str, object]] = {}
    for ccn, p in providers.items():
        if not p.state:
            continue
        s = summary.setdefault(p.state, {"facilities": 0, "rated": 0, "_sum": 0.0})
        s["facilities"] = int(s["facilities"]) + 1
        v = (quality.get(ccn) or {}).get("dtc_rs_rate")
        if v is not None:
            s["rated"] = int(s["rated"]) + 1
            s["_sum"] = float(s["_sum"]) + v
    for st, s in summary.items():
        rated = int(s["rated"])
        s["avg_dtc"] = round(float(s["_sum"]) / rated, 1) if rated else None
        del s["_sum"]
    return summary
