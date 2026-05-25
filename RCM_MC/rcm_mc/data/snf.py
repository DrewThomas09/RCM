"""SNF / Nursing Home loaders (Sector Intelligence — SNF vertical).

Reads vendored CMS **Nursing Home Care Compare — Provider Information**
snapshots (`snf_providers.csv` + `snf_quality.csv`, normalized once from the
official `NH_ProviderInfo` file, Apr 2026). One-time vendored data; **no
runtime network calls**.

Scope/limits: Medicare/Medicaid-certified nursing homes only. The fields are
the publicly-reported CMS values — the four 5-star ratings (overall, health
inspection, staffing, quality-measure), reported staffing hours, certified
beds, average daily residents, Special Focus Facility status, ownership, and
the enforcement-penalty summary (fines, payment denials). "Total amount of
fines" is a regulatory **penalty** figure, NOT facility revenue. Private-pay-
only facilities and commercial economics are not represented.
"""
from __future__ import annotations

import csv
import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_PROVIDERS_CSV = Path(__file__).with_name("snf_providers.csv")
_QUALITY_CSV = Path(__file__).with_name("snf_quality.csv")

_QUALITY_METRICS = (
    "overall_rating", "health_inspection_rating", "staffing_rating",
    "qm_rating", "rn_hprd", "total_nurse_hprd", "total_nurse_turnover_pct",
    "num_fines", "total_fines_usd", "num_payment_denials", "num_penalties",
)


@dataclass(frozen=True)
class SnfProvider:
    ccn: str
    provider_name: str
    address: str
    city: str
    state: str
    zip: str
    county: str
    ownership: str
    certified_beds: Optional[int]
    avg_residents_per_day: Optional[float]
    provider_type: str
    sff_status: str
    abuse_icon: str
    changed_ownership_12mo: str
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
def load_snf_providers() -> Dict[str, SnfProvider]:
    """``{ccn: SnfProvider}`` from the vendored file ({} if missing)."""
    out: Dict[str, SnfProvider] = {}
    if not _PROVIDERS_CSV.is_file():
        return out
    with _PROVIDERS_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _norm_ccn(r.get("ccn", ""))
            if not ccn:
                continue
            out[ccn] = SnfProvider(
                ccn=ccn,
                provider_name=(r.get("provider_name") or "").strip(),
                address=(r.get("address") or "").strip(),
                city=(r.get("city") or "").strip(),
                state=_norm_state(r.get("state", "")),
                zip=(r.get("zip") or "").strip(),
                county=(r.get("county") or "").strip(),
                ownership=(r.get("ownership") or "").strip(),
                certified_beds=_i(r.get("certified_beds", "")),
                avg_residents_per_day=_f(r.get("avg_residents_per_day", "")),
                provider_type=(r.get("provider_type") or "").strip(),
                sff_status=(r.get("sff_status") or "").strip(),
                abuse_icon=(r.get("abuse_icon") or "").strip(),
                changed_ownership_12mo=(r.get("changed_ownership_12mo") or "").strip(),
                certification_date=(r.get("certification_date") or "").strip(),
                source=(r.get("source") or "").strip(),
                source_date=(r.get("source_date") or "").strip(),
            )
    return out


@functools.lru_cache(maxsize=1)
def load_snf_quality() -> Dict[str, Dict[str, Optional[float]]]:
    """``{ccn: {metric: float|None}}`` for the publicly-reported SNF measures."""
    out: Dict[str, Dict[str, Optional[float]]] = {}
    if not _QUALITY_CSV.is_file():
        return out
    with _QUALITY_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            ccn = _norm_ccn(r.get("ccn", ""))
            if not ccn:
                continue
            out[ccn] = {m: _f(r.get(m, "")) for m in _QUALITY_METRICS}
    return out


def snf_providers_for_state(state: str) -> List[SnfProvider]:
    st = _norm_state(state)
    rows = [p for p in load_snf_providers().values() if p.state == st]
    return sorted(rows, key=lambda p: p.provider_name)


def snf_provider_by_ccn(ccn: str) -> Optional[SnfProvider]:
    return load_snf_providers().get(_norm_ccn(ccn))


def load_snf_summary_by_state() -> Dict[str, Dict[str, object]]:
    """Per-state: facility count, # with an overall rating, avg overall rating.

    Simple counts/averages only — no composite scores invented here.
    """
    providers = load_snf_providers()
    quality = load_snf_quality()
    summary: Dict[str, Dict[str, object]] = {}
    for ccn, p in providers.items():
        st = p.state
        if not st:
            continue
        s = summary.setdefault(st, {"facilities": 0, "rated": 0, "_star_sum": 0.0})
        s["facilities"] = int(s["facilities"]) + 1
        star = (quality.get(ccn) or {}).get("overall_rating")
        if star is not None:
            s["rated"] = int(s["rated"]) + 1
            s["_star_sum"] = float(s["_star_sum"]) + star
    for st, s in summary.items():
        rated = int(s["rated"])
        s["avg_overall_rating"] = (
            round(float(s["_star_sum"]) / rated, 2) if rated else None
        )
        del s["_star_sum"]
    return summary


def _median(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def snf_turnover_summary(state: str = "") -> Dict[str, object]:
    """Real CMS nurse-staff turnover benchmark (Care Compare ``Total nursing
    staff turnover``). National by default; pass a 2-letter ``state`` to scope.

    Turnover here is a **facility-level workforce** measure CMS publishes for
    each nursing home — the share of nursing staff who left in the trailing
    12 months. It is real market context for SNF/nursing-home diligence; it is
    NOT a portfolio-specific retention figure and says nothing about a deal's
    own roster. Missing values stay missing (never coerced to 0). Returns
    ``{n, facilities, median_pct, mean_pct, p25_pct, p75_pct, worst_quartile_pct,
    state}`` with ``None`` where the sample is empty.
    """
    quality = load_snf_quality()
    st = _norm_state(state) if state else ""
    by_ccn_state = {ccn: p.state for ccn, p in load_snf_providers().items()} if st else {}
    vals: List[float] = []
    facilities = 0
    for ccn, q in quality.items():
        if st and by_ccn_state.get(ccn) != st:
            continue
        facilities += 1
        tv = q.get("total_nurse_turnover_pct")
        if tv is not None:
            vals.append(float(tv))
    n = len(vals)
    if not n:
        return {"n": 0, "facilities": facilities, "median_pct": None,
                "mean_pct": None, "p25_pct": None, "p75_pct": None,
                "worst_quartile_pct": None, "state": st or "US"}
    s = sorted(vals)
    p25 = s[int(0.25 * (n - 1))]
    p75 = s[int(0.75 * (n - 1))]
    return {
        "n": n, "facilities": facilities,
        "median_pct": round(_median(vals), 1),
        "mean_pct": round(sum(vals) / n, 1),
        "p25_pct": round(p25, 1), "p75_pct": round(p75, 1),
        "worst_quartile_pct": round(p75, 1),
        "state": st or "US",
    }


def snf_turnover_by_state(top_n: int = 10) -> List[Dict[str, object]]:
    """Per-state median nurse-staff turnover (real CMS), worst first.

    Only states with >=10 facilities reporting turnover are returned, so a
    single facility can't masquerade as a state benchmark. Each row is
    ``{state, facilities_reporting, median_pct}``.
    """
    quality = load_snf_quality()
    prov_state = {ccn: p.state for ccn, p in load_snf_providers().items()}
    buckets: Dict[str, List[float]] = {}
    for ccn, q in quality.items():
        tv = q.get("total_nurse_turnover_pct")
        st = prov_state.get(ccn)
        if tv is None or not st:
            continue
        buckets.setdefault(st, []).append(float(tv))
    rows = [
        {"state": st, "facilities_reporting": len(v),
         "median_pct": round(_median(v), 1)}
        for st, v in buckets.items() if len(v) >= 10
    ]
    rows.sort(key=lambda r: r["median_pct"], reverse=True)
    return rows[:top_n]
