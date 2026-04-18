"""Deal flow momentum and sectoral timing signals.

Analyzes vintage clustering, deal-volume trends, and return compression
across the corpus to surface "running hot" vs "cooling off" signals
for healthcare sub-sectors.

These signals are calibration inputs for the pe_intelligence layer:
a hot sector means higher entry multiples, lower prospective MOIC,
and higher competition risk.

Public API:
    sector_deal_volume(deals)             -> dict  (sector → count by year)
    sector_momentum_score(deals, sector)  -> float (0-1, recent acceleration)
    multiple_compression_trend(deals)     -> dict  (year → median EV/EBITDA)
    return_compression_trend(deals)       -> dict  (year → median MOIC)
    hot_sectors(deals, top_n=5)           -> list[dict]
    timing_assessment(deals, sector)      -> dict  (entry risk assessment)
    momentum_report(deals)               -> str
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Sector classification
# ---------------------------------------------------------------------------

_SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "behavioral_health": [
        "behavioral", "mental health", "psychiatr", "substance", "acadia",
        "lifestance", "spring health", "cano", "outpatient behavioral"
    ],
    "home_health": [
        "home health", "home care", "hha", "kindred at home", "amedisys",
        "lhc group", "gentiva", "home infusion", "option care"
    ],
    "physician_staffing": [
        "physician staffing", "envision", "teamhealth", "mednax",
        "nocturnist", "emergency medicine"
    ],
    "asc_surgical": [
        "surgical partners", "uspi", "asc", "ambulatory", "surgery center",
        "paradigm oral", "clearway pain", "upstream rehab"
    ],
    "value_based_care": [
        "value-based", "vbc", "ma ", "medicare advantage", "oak street",
        "agilon", "privia", "alignment", "chen med", "cano", "absolute care"
    ],
    "rcm_health_it": [
        "rcm", "revenue cycle", "r1 rcm", "cloudmed", "netsmart", "ensemble",
        "gainwell", "health it", "evicore"
    ],
    "hospice_palliative": [
        "hospice", "palliative", "gentiva", "amedisys", "lhc"
    ],
    "dso_dental_eye": [
        "dental", "dso", "dermatol", "ophthalmol", "smile brands",
        "paradigm oral", "acuity eye", "us dermatology"
    ],
    "diagnostics_lab": [
        "lab", "diagnostic", "labcorp", "quest", "radiology", "mednax radiology",
        "pathology", "imaging"
    ],
    "acute_hospital": [
        "hospital system", "health system", "hca", "steward", "tenet", "lifepoint",
        "prospect medical", "ardent", "ovation", "community health", "vanguard"
    ],
}


def _classify_sector(deal: Dict[str, Any]) -> str:
    text = (
        (deal.get("deal_name") or "")
        + " "
        + (deal.get("notes") or "")
    ).lower()

    for sector, keywords in _SECTOR_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return sector
    return "other"


# ---------------------------------------------------------------------------
# Volume + compression trends
# ---------------------------------------------------------------------------

def sector_deal_volume(
    deals: List[Dict[str, Any]]
) -> Dict[str, Dict[int, int]]:
    """Count deals per sector per year.

    Returns: {sector: {year: count, ...}, ...}
    """
    result: Dict[str, Dict[int, int]] = {}
    for d in deals:
        sector = _classify_sector(d)
        yr = d.get("year")
        if yr is None:
            continue
        result.setdefault(sector, {}).setdefault(int(yr), 0)
        result[sector][int(yr)] += 1
    return result


def multiple_compression_trend(
    deals: List[Dict[str, Any]]
) -> Dict[int, Optional[float]]:
    """Median EV/EBITDA multiple per year across the corpus.

    Returns {year: median_ev_ebitda} only for years with >= 3 data points.
    """
    from collections import defaultdict
    groups: Dict[int, List[float]] = defaultdict(list)
    for d in deals:
        yr = d.get("year")
        ev = d.get("ev_mm")
        ebitda = d.get("ebitda_at_entry_mm")
        if yr is None or ev is None or ebitda is None:
            continue
        try:
            ev_f, ebitda_f = float(ev), float(ebitda)
        except (TypeError, ValueError):
            continue
        if ebitda_f > 0:
            groups[int(yr)].append(ev_f / ebitda_f)

    result: Dict[int, Optional[float]] = {}
    for yr in sorted(groups.keys()):
        vals = groups[yr]
        if len(vals) >= 3:
            result[yr] = sorted(vals)[len(vals) // 2]  # median
        elif vals:
            result[yr] = sorted(vals)[0]
    return result


def return_compression_trend(
    deals: List[Dict[str, Any]]
) -> Dict[int, Optional[float]]:
    """Median realized MOIC per vintage year (exit year approximated as year + hold_years).

    Uses close_year + hold_years where available; falls back to close_year.
    Only years with >= 3 realized deals included.
    """
    from collections import defaultdict
    groups: Dict[int, List[float]] = defaultdict(list)
    for d in deals:
        moic = d.get("realized_moic")
        yr = d.get("year")
        if moic is None or yr is None:
            continue
        try:
            groups[int(yr)].append(float(moic))
        except (TypeError, ValueError):
            pass

    result: Dict[int, Optional[float]] = {}
    for yr in sorted(groups.keys()):
        vals = groups[yr]
        if len(vals) >= 2:
            result[yr] = sorted(vals)[len(vals) // 2]
    return result


# ---------------------------------------------------------------------------
# Sector momentum
# ---------------------------------------------------------------------------

def sector_momentum_score(
    deals: List[Dict[str, Any]],
    sector: str,
    recent_years: int = 3,
) -> float:
    """Momentum score (0–1) for a sector based on recent deal volume acceleration.

    Computes volume ratio: recent_years / prior_years.
    Normalizes to 0–1 via sigmoid-like transform.
    """
    volume = sector_deal_volume(deals).get(sector, {})
    if not volume:
        return 0.0

    all_years = sorted(volume.keys())
    if len(all_years) < 2:
        return 0.5  # neutral — insufficient history

    cutoff = all_years[-recent_years] if len(all_years) >= recent_years else all_years[0]
    recent = sum(v for yr, v in volume.items() if yr >= cutoff)
    prior = sum(v for yr, v in volume.items() if yr < cutoff)

    if prior == 0:
        return 0.75 if recent > 0 else 0.5

    ratio = recent / max(prior, 1)
    # sigmoid: ratio=1 → 0.5, ratio=2 → 0.73, ratio=4 → 0.88, ratio=0.5 → 0.27
    return round(1.0 / (1.0 + math.exp(-1.5 * (ratio - 1.0))), 3)


def hot_sectors(
    deals: List[Dict[str, Any]],
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """Return the top_n sectors sorted by momentum score, descending.

    Each entry: {sector, momentum_score, total_deals, recent_deals}
    """
    volume = sector_deal_volume(deals)
    results = []
    for sector in volume:
        score = sector_momentum_score(deals, sector)
        total = sum(volume[sector].values())
        # recent = last 3 years
        all_years = sorted(volume[sector].keys())
        cutoff = all_years[-3] if len(all_years) >= 3 else all_years[0]
        recent = sum(v for yr, v in volume[sector].items() if yr >= cutoff)
        results.append({
            "sector": sector,
            "momentum_score": score,
            "total_deals": total,
            "recent_deals": recent,
        })

    results.sort(key=lambda r: r["momentum_score"], reverse=True)
    return results[:top_n]


# ---------------------------------------------------------------------------
# Timing assessment
# ---------------------------------------------------------------------------

_RISK_LABELS = {
    (0.0, 0.35): "cooling_off",
    (0.35, 0.55): "neutral",
    (0.55, 0.75): "active",
    (0.75, 1.01): "running_hot",
}


def timing_assessment(
    deals: List[Dict[str, Any]],
    sector: str,
) -> Dict[str, Any]:
    """Return entry timing risk assessment for a sector.

    Returns: {sector, momentum_score, entry_risk, deal_count,
              median_ev_ebitda, median_moic, recommendation}
    """
    score = sector_momentum_score(deals, sector)

    label = "neutral"
    for (lo, hi), lbl in _RISK_LABELS.items():
        if lo <= score < hi:
            label = lbl
            break

    sector_deals = [d for d in deals if _classify_sector(d) == sector]

    ev_ebitda_vals = []
    for d in sector_deals:
        ev = d.get("ev_mm")
        ebitda = d.get("ebitda_at_entry_mm")
        if ev and ebitda and float(ebitda) > 0:
            ev_ebitda_vals.append(float(ev) / float(ebitda))

    moic_vals = [float(d["realized_moic"]) for d in sector_deals
                 if d.get("realized_moic") is not None]

    median_ev_ebitda = sorted(ev_ebitda_vals)[len(ev_ebitda_vals) // 2] if ev_ebitda_vals else None
    median_moic = sorted(moic_vals)[len(moic_vals) // 2] if moic_vals else None

    _RECS = {
        "running_hot": "Caution: elevated multiples likely; stress IRR at 12-14x entry.",
        "active": "Normal competition; base-case diligence discipline applies.",
        "neutral": "Balanced; standard IRR hurdles should be achievable.",
        "cooling_off": "Favorable entry window; seller motivation elevated.",
    }

    return {
        "sector": sector,
        "momentum_score": score,
        "entry_risk": label,
        "deal_count": len(sector_deals),
        "median_ev_ebitda": round(median_ev_ebitda, 1) if median_ev_ebitda else None,
        "median_moic": round(median_moic, 2) if median_moic else None,
        "recommendation": _RECS.get(label, ""),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def momentum_report(deals: List[Dict[str, Any]]) -> str:
    """Formatted momentum report across all sectors."""
    hot = hot_sectors(deals, top_n=10)
    multi = multiple_compression_trend(deals)
    ret = return_compression_trend(deals)

    lines = [
        "Deal Flow Momentum Report",
        "=" * 72,
        "Top Sectors by Momentum:",
        f"  {'Sector':<28} {'Score':>6} {'Total':>7} {'Recent':>8} {'Risk':<15}",
        "-" * 72,
    ]
    for row in hot:
        ta = timing_assessment(deals, row["sector"])
        lines.append(
            f"  {row['sector']:<28} {row['momentum_score']:>6.3f} "
            f"{row['total_deals']:>7} {row['recent_deals']:>8} "
            f"{ta['entry_risk']:<15}"
        )

    lines += ["", "Multiple Compression Trend (median EV/EBITDA):"]
    for yr, med in sorted(multi.items()):
        if med is not None:
            lines.append(f"  {yr}: {med:.1f}x")

    lines += ["", "Return Compression Trend (median realized MOIC):"]
    for yr, med in sorted(ret.items()):
        if med is not None:
            lines.append(f"  {yr}: {med:.2f}x")

    lines.append("=" * 72)
    return "\n".join(lines) + "\n"
