"""Subsector benchmarks — P25/P50/P75 MOIC and IRR by healthcare subsector.

Provides corpus-derived percentile bands that a PE partner uses to
answer: "Is this deal's projected return realistic for this sector?"

The benchmarks are derived from the live corpus, so they improve as
more deals are added. Every value is traceable to a named deal.

Public API:
    SubsectorStats                          dataclass
    compute_subsector_benchmarks(deals)     -> Dict[str, SubsectorStats]
    get_sector_benchmark(deals, sector)     -> Optional[SubsectorStats]
    benchmark_deal_vs_sector(deal, deals)   -> Dict[str, Any]
    subsector_table(stats, sort_by)         -> str
    sector_peer_group(deals, sector, n)     -> List[Dict]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Sector normalization — collapse noisy string variants into canonical labels
# ---------------------------------------------------------------------------

_SECTOR_CANONICAL: Dict[str, str] = {
    # Behavioral health
    "behavioral_health": "Behavioral Health",
    "behavioral health": "Behavioral Health",
    "mental_health": "Behavioral Health",
    "addiction": "Behavioral Health",
    "substance_use": "Behavioral Health",
    "mat": "Behavioral Health",
    "otp": "Behavioral Health",
    # Home health / hospice
    "home_health": "Home Health / Hospice",
    "home health": "Home Health / Hospice",
    "hospice": "Home Health / Hospice",
    "home_community_based": "Home Health / Hospice",
    "hcbs": "Home Health / Hospice",
    # Physician groups
    "physician_group": "Physician Groups",
    "physician group": "Physician Groups",
    "physician_groups": "Physician Groups",
    "emergency_medicine": "Physician Groups",
    "anesthesiology": "Physician Groups",
    "radiology": "Physician Groups",
    "primary_care": "Physician Groups",
    "pediatrics": "Physician Groups",
    "hospitalist": "Physician Groups",
    "ophthalmology": "Physician Groups",
    "cardiology": "Physician Groups",
    "oncology": "Physician Groups",
    "urology": "Physician Groups",
    "gi": "Physician Groups",
    "orthopedics": "Physician Groups",
    "women_health": "Physician Groups",
    "women's_health": "Physician Groups",
    "maternal_care": "Physician Groups",
    "maternal_fetal": "Physician Groups",
    "pain_management": "Physician Groups",
    "neurology": "Physician Groups",
    # Dental
    "dental": "Dental / DSO",
    "dental_dso": "Dental / DSO",
    "dso": "Dental / DSO",
    # Post-acute / SNF / LTACH
    "snf": "Post-Acute / SNF",
    "skilled_nursing": "Post-Acute / SNF",
    "ltach": "Post-Acute / SNF",
    "ltach_post_acute": "Post-Acute / SNF",
    "post_acute": "Post-Acute / SNF",
    "senior_living": "Post-Acute / SNF",
    "memory_care": "Post-Acute / SNF",
    "reit": "Post-Acute / SNF",
    # Ambulatory / ASC
    "asc": "Ambulatory / ASC",
    "ambulatory": "Ambulatory / ASC",
    "urgent_care": "Ambulatory / ASC",
    "ambulatory_surgery": "Ambulatory / ASC",
    # Dialysis
    "dialysis": "Dialysis",
    "renal": "Dialysis",
    "ckd": "Dialysis",
    # Health IT / RCM
    "health_it": "Health IT / RCM",
    "rcm": "Health IT / RCM",
    "health_tech": "Health IT / RCM",
    "ehr": "Health IT / RCM",
    "population_health": "Health IT / RCM",
    "value_based_care": "Health IT / RCM",
    "managed_care_services": "Health IT / RCM",
    # Managed care / insurance
    "managed_care": "Managed Care",
    "insurance": "Managed Care",
    "payer": "Managed Care",
    "ma_plan": "Managed Care",
    "medicare_advantage": "Managed Care",
    # Lab / diagnostics
    "lab": "Lab / Diagnostics",
    "diagnostics": "Lab / Diagnostics",
    "pathology": "Lab / Diagnostics",
    "genomics": "Lab / Diagnostics",
    "imaging": "Lab / Diagnostics",
    "mobile_diagnostics": "Lab / Diagnostics",
    "radiology_imaging": "Lab / Diagnostics",
    # Pharmacy / PBM
    "pharmacy": "Pharmacy / PBM",
    "pbm": "Pharmacy / PBM",
    "specialty_pharmacy": "Pharmacy / PBM",
    "infusion": "Pharmacy / PBM",
    # DME / home health
    "dme": "DME / Home Infusion",
    "dme_home_health": "DME / Home Infusion",
    "home_infusion": "DME / Home Infusion",
    # Physical therapy
    "physical_therapy": "Physical Therapy",
    "pt": "Physical Therapy",
    "rehab": "Physical Therapy",
    # Telehealth / digital
    "telehealth": "Telehealth / Digital Health",
    "digital_health": "Telehealth / Digital Health",
    "telemedicine": "Telehealth / Digital Health",
    # Hospital / health system
    "hospital": "Hospital / Health System",
    "health_system": "Hospital / Health System",
    "acute_care": "Hospital / Health System",
    "rural_hospital": "Hospital / Health System",
    # Other
    "ems": "Other Healthcare Services",
    "occupational_health": "Other Healthcare Services",
    "correctional": "Other Healthcare Services",
    "nemt": "Other Healthcare Services",
    "veterinary": "Other Healthcare Services",
}


def _canonical_sector(raw: Optional[str]) -> str:
    if not raw:
        return "Other Healthcare Services"
    key = raw.lower().strip().replace(" ", "_")
    return _SECTOR_CANONICAL.get(key, _SECTOR_CANONICAL.get(raw.lower().strip(), raw.replace("_", " ").title()))


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class SubsectorStats:
    sector: str
    deal_count: int
    realized_count: int

    moic_p25: Optional[float]
    moic_p50: Optional[float]
    moic_p75: Optional[float]
    moic_mean: Optional[float]
    moic_min: Optional[float]
    moic_max: Optional[float]

    irr_p25: Optional[float]
    irr_p50: Optional[float]
    irr_p75: Optional[float]
    irr_mean: Optional[float]

    median_hold_years: Optional[float]
    median_ev_mm: Optional[float]
    loss_rate: float        # MOIC < 1.0
    home_run_rate: float    # MOIC > 3.0

    # Common deal types in this sector
    top_deal_types: List[str] = field(default_factory=list)
    # Source IDs of the realized deals used
    source_ids: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _pct(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = max(0, min(len(s) - 1, int(p * (len(s) - 1))))
    return round(s[idx], 3)


def _mean(vals: List[float]) -> Optional[float]:
    return round(sum(vals) / len(vals), 3) if vals else None


def compute_subsector_benchmarks(deals: List[Dict[str, Any]]) -> Dict[str, SubsectorStats]:
    """Compute P25/P50/P75 MOIC and IRR benchmarks by healthcare subsector.

    Args:
        deals: List of deal dicts (from corpus.list() or seed lists)

    Returns:
        Dict mapping canonical sector label -> SubsectorStats
    """
    from collections import defaultdict

    sector_buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for deal in deals:
        sector = _canonical_sector(deal.get("sector"))
        sector_buckets[sector].append(deal)

    result: Dict[str, SubsectorStats] = {}

    for sector, sdeal_list in sector_buckets.items():
        moics = [(float(d["realized_moic"]), d.get("source_id", "")) for d in sdeal_list
                 if d.get("realized_moic") is not None]
        irrs = [float(d["realized_irr"]) for d in sdeal_list
                if d.get("realized_irr") is not None]
        holds = [float(d["hold_years"]) for d in sdeal_list
                 if d.get("hold_years") is not None]
        evs = [float(d["ev_mm"]) for d in sdeal_list
               if d.get("ev_mm") is not None]

        moic_vals = [m for m, _ in moics]
        moic_src = [s for _, s in moics]

        # Deal type breakdown
        type_counts: Dict[str, int] = defaultdict(int)
        for d in sdeal_list:
            dt = d.get("deal_type") or "unknown"
            type_counts[dt] += 1
        top_types = [t for t, _ in sorted(type_counts.items(), key=lambda x: -x[1])[:3]]

        loss_rate = sum(1 for m in moic_vals if m < 1.0) / len(moic_vals) if moic_vals else 0.0
        home_run_rate = sum(1 for m in moic_vals if m > 3.0) / len(moic_vals) if moic_vals else 0.0

        result[sector] = SubsectorStats(
            sector=sector,
            deal_count=len(sdeal_list),
            realized_count=len(moic_vals),
            moic_p25=_pct(moic_vals, 0.25),
            moic_p50=_pct(moic_vals, 0.50),
            moic_p75=_pct(moic_vals, 0.75),
            moic_mean=_mean(moic_vals),
            moic_min=round(min(moic_vals), 3) if moic_vals else None,
            moic_max=round(max(moic_vals), 3) if moic_vals else None,
            irr_p25=_pct(irrs, 0.25),
            irr_p50=_pct(irrs, 0.50),
            irr_p75=_pct(irrs, 0.75),
            irr_mean=_mean(irrs),
            median_hold_years=_pct(holds, 0.50),
            median_ev_mm=_pct(evs, 0.50),
            loss_rate=round(loss_rate, 3),
            home_run_rate=round(home_run_rate, 3),
            top_deal_types=top_types,
            source_ids=moic_src,
        )

    return result


def get_sector_benchmark(
    deals: List[Dict[str, Any]],
    sector: str,
) -> Optional[SubsectorStats]:
    """Look up benchmarks for a specific sector string (normalizes automatically)."""
    canonical = _canonical_sector(sector)
    stats = compute_subsector_benchmarks(deals)
    return stats.get(canonical)


def benchmark_deal_vs_sector(
    deal: Dict[str, Any],
    deals: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare a deal's projected / realized return to its sector peers.

    Returns a dict with: sector, deal_moic, p50_moic, percentile_rank,
    vs_p50 (delta), signal (above/at/below), irr signals, peer_count.
    """
    sector = _canonical_sector(deal.get("sector"))
    bench = get_sector_benchmark(deals, sector)

    deal_moic = deal.get("realized_moic")
    if deal_moic is None:
        deal_moic = deal.get("projected_moic")

    result: Dict[str, Any] = {
        "sector": sector,
        "deal_moic": deal_moic,
        "source_id": deal.get("source_id"),
        "deal_name": deal.get("deal_name"),
    }

    if bench is None or bench.realized_count < 3:
        result["signal"] = "insufficient_data"
        return result

    result.update({
        "peer_count": bench.realized_count,
        "moic_p25": bench.moic_p25,
        "moic_p50": bench.moic_p50,
        "moic_p75": bench.moic_p75,
        "irr_p50": bench.irr_p50,
        "loss_rate": bench.loss_rate,
        "home_run_rate": bench.home_run_rate,
    })

    if deal_moic is not None and bench.moic_p50 is not None:
        delta = float(deal_moic) - bench.moic_p50
        result["vs_p50"] = round(delta, 3)

        # Percentile rank within sector
        moic_vals = sorted([float(d["realized_moic"]) for d in deals
                            if d.get("realized_moic") is not None
                            and _canonical_sector(d.get("sector")) == sector])
        rank = sum(1 for m in moic_vals if m <= float(deal_moic)) / len(moic_vals) if moic_vals else None
        result["percentile_rank"] = round(rank, 3) if rank is not None else None

        if deal_moic >= bench.moic_p75:
            result["signal"] = "above_p75"
        elif deal_moic >= bench.moic_p50:
            result["signal"] = "above_median"
        elif deal_moic >= bench.moic_p25:
            result["signal"] = "below_median"
        else:
            result["signal"] = "bottom_quartile"
    else:
        result["signal"] = "no_moic"

    return result


def sector_peer_group(
    deals: List[Dict[str, Any]],
    sector: str,
    n: int = 10,
) -> List[Dict[str, Any]]:
    """Return the n most comparable deals in the sector, by realized MOIC descending."""
    canonical = _canonical_sector(sector)
    peers = [d for d in deals if _canonical_sector(d.get("sector")) == canonical
             and d.get("realized_moic") is not None]
    peers.sort(key=lambda d: float(d["realized_moic"]), reverse=True)
    return peers[:n]


# ---------------------------------------------------------------------------
# Output formatter
# ---------------------------------------------------------------------------

def subsector_table(
    stats: Dict[str, SubsectorStats],
    sort_by: str = "moic_p50",
    min_realized: int = 2,
) -> str:
    """Formatted table of subsector benchmarks, sorted by sort_by field."""
    rows = [s for s in stats.values() if s.realized_count >= min_realized]

    def key_fn(s: SubsectorStats) -> float:
        v = getattr(s, sort_by, None)
        return float(v) if v is not None else -999.0

    rows.sort(key=key_fn, reverse=True)

    lines = [
        f"{'Sector':<28} {'N':>4} {'P25':>7} {'P50':>7} {'P75':>7} {'IRR P50':>8} {'Loss%':>6} {'HR%':>5}",
        "-" * 77,
    ]
    for s in rows:
        p25 = f"{s.moic_p25:.2f}x" if s.moic_p25 is not None else "  —  "
        p50 = f"{s.moic_p50:.2f}x" if s.moic_p50 is not None else "  —  "
        p75 = f"{s.moic_p75:.2f}x" if s.moic_p75 is not None else "  —  "
        irr = f"{s.irr_p50:.1%}" if s.irr_p50 is not None else "  —  "
        loss = f"{s.loss_rate:.0%}"
        hr = f"{s.home_run_rate:.0%}"
        lines.append(
            f"{s.sector[:27]:<28} {s.realized_count:>4} {p25:>7} {p50:>7} {p75:>7} {irr:>8} {loss:>6} {hr:>5}"
        )

    return "\n".join(lines) + "\n"
