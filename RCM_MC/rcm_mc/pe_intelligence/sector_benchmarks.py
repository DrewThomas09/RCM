"""Sector benchmarks — calibrated peer medians by healthcare subsector.

The core reasonableness bands in :mod:`reasonableness` are partner
ranges ("what's defensible"). This module is different — it exposes
central-tendency peer benchmarks ("what a typical peer looks like")
per healthcare subsector, suitable for dashboard surfacing and
comparison anchors.

The primary consumer is the UI / IC memo: "your 9.2% EBITDA margin
vs acute-care median of 7.8% puts you at p60".

Data vintage: 2019-2024 blended AHA + CMS cost reports + industry
surveys + partner-book outcomes. These are medians, not aspirational
targets, and should be refreshed annually.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SectorBenchmark:
    """Per-metric benchmark with p25 / p50 / p75 for a subsector."""
    subsector: str
    metric: str
    unit: str                  # "pct" | "days" | "x" | "usd_m" | "ratio"
    p25: Optional[float] = None
    p50: Optional[float] = None
    p75: Optional[float] = None
    source: str = ""

    def percentile(self, value: float) -> Optional[int]:
        """Estimate a rough percentile for ``value``. Returns 25/50/75 or
        None if insufficient data. This is not a kernel estimate —
        it's a partner-gut placement."""
        if self.p25 is None or self.p50 is None or self.p75 is None:
            return None
        if value < self.p25:
            return 15
        if value <= self.p50:
            return 40
        if value <= self.p75:
            return 65
        return 85

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsector": self.subsector,
            "metric": self.metric,
            "unit": self.unit,
            "p25": self.p25,
            "p50": self.p50,
            "p75": self.p75,
            "source": self.source,
        }


# ── Benchmark registry ───────────────────────────────────────────────
# Keyed by (subsector, metric). Values are partner-calibrated medians
# from healthcare-PE data 2019-2024.

_BENCHMARKS: List[SectorBenchmark] = [
    # Acute care
    SectorBenchmark("acute_care", "ebitda_margin", "pct", 0.04, 0.075, 0.11, "AHA + CMS cost reports"),
    SectorBenchmark("acute_care", "days_in_ar", "days", 42, 50, 62, "HFMA + partner book"),
    SectorBenchmark("acute_care", "initial_denial_rate", "pct", 0.06, 0.09, 0.13, "CMS PEPPER + HFMA"),
    SectorBenchmark("acute_care", "final_writeoff_rate", "pct", 0.025, 0.045, 0.075, "HFMA"),
    SectorBenchmark("acute_care", "clean_claim_rate", "pct", 0.88, 0.92, 0.95, "HFMA MAP keys"),
    SectorBenchmark("acute_care", "case_mix_index", "ratio", 1.25, 1.50, 1.80, "HCRIS Worksheet S-3"),
    SectorBenchmark("acute_care", "bed_occupancy", "pct", 0.55, 0.65, 0.78, "AHA"),

    # Ambulatory Surgery Center
    SectorBenchmark("asc", "ebitda_margin", "pct", 0.18, 0.25, 0.32, "ASCA + industry data"),
    SectorBenchmark("asc", "days_in_ar", "days", 28, 36, 44, "HFMA ASC"),
    SectorBenchmark("asc", "initial_denial_rate", "pct", 0.04, 0.065, 0.10, "ASCA"),
    SectorBenchmark("asc", "cases_per_or_per_day", "ratio", 5.0, 7.0, 9.0, "ASCA"),

    # Behavioral Health
    SectorBenchmark("behavioral", "ebitda_margin", "pct", 0.12, 0.18, 0.25, "NAMI + industry"),
    SectorBenchmark("behavioral", "days_in_ar", "days", 38, 48, 62, "HFMA"),
    SectorBenchmark("behavioral", "initial_denial_rate", "pct", 0.08, 0.12, 0.18, "HFMA"),
    SectorBenchmark("behavioral", "avg_length_of_stay_days", "days", 7, 12, 22, "SAMHSA"),
    SectorBenchmark("behavioral", "census_occupancy", "pct", 0.70, 0.80, 0.88, "Industry"),

    # Post-acute
    SectorBenchmark("post_acute", "ebitda_margin", "pct", 0.06, 0.10, 0.15, "AHCA/NCAL"),
    SectorBenchmark("post_acute", "days_in_ar", "days", 45, 58, 75, "HFMA"),
    SectorBenchmark("post_acute", "occupancy", "pct", 0.78, 0.85, 0.92, "AHCA/NCAL"),
    SectorBenchmark("post_acute", "medicare_mix", "pct", 0.10, 0.22, 0.35, "AHCA/NCAL"),

    # Specialty hospital
    SectorBenchmark("specialty", "ebitda_margin", "pct", 0.11, 0.16, 0.22, "Industry comps"),
    SectorBenchmark("specialty", "days_in_ar", "days", 35, 45, 55, "HFMA"),
    SectorBenchmark("specialty", "initial_denial_rate", "pct", 0.05, 0.08, 0.12, "HFMA"),

    # Outpatient / physician practice
    SectorBenchmark("outpatient", "ebitda_margin", "pct", 0.10, 0.17, 0.25, "MGMA"),
    SectorBenchmark("outpatient", "days_in_ar", "days", 25, 32, 42, "HFMA + MGMA"),
    SectorBenchmark("outpatient", "initial_denial_rate", "pct", 0.07, 0.11, 0.16, "MGMA"),
    SectorBenchmark("outpatient", "rvu_per_provider_per_yr", "ratio", 4800, 6200, 8000, "MGMA"),

    # Critical Access
    SectorBenchmark("critical_access", "ebitda_margin", "pct", 0.00, 0.03, 0.07, "CMS cost reports"),
    SectorBenchmark("critical_access", "days_in_ar", "days", 48, 60, 80, "HFMA"),
    SectorBenchmark("critical_access", "medicare_mix", "pct", 0.45, 0.60, 0.75, "CMS"),
]


# ── Aliases ─────────────────────────────────────────────────────────

_ALIASES: Dict[str, str] = {
    "acute": "acute_care",
    "hospital": "acute_care",
    "acute_care_hospital": "acute_care",
    "surgery_center": "asc",
    "ambulatory": "asc",
    "ambulatory_surgery": "asc",
    "snf": "post_acute",
    "nursing_home": "post_acute",
    "ltach": "post_acute",
    "rehab": "post_acute",
    "psych": "behavioral",
    "mental_health": "behavioral",
    "substance_abuse": "behavioral",
    "clinic": "outpatient",
    "physician_practice": "outpatient",
    "mso": "outpatient",
    "cah": "critical_access",
}


def _canonical(subsector: str) -> str:
    key = str(subsector or "").lower().strip().replace("-", "_").replace(" ", "_")
    return _ALIASES.get(key, key)


# ── Lookup ───────────────────────────────────────────────────────────

def get_benchmark(subsector: str, metric: str) -> Optional[SectorBenchmark]:
    """Return the benchmark for a (subsector, metric) pair, or None."""
    canonical = _canonical(subsector)
    for b in _BENCHMARKS:
        if b.subsector == canonical and b.metric == metric:
            return b
    return None


def list_metrics_for_subsector(subsector: str) -> List[str]:
    canonical = _canonical(subsector)
    return [b.metric for b in _BENCHMARKS if b.subsector == canonical]


def list_subsectors() -> List[str]:
    return sorted({b.subsector for b in _BENCHMARKS})


# ── Gap analysis ─────────────────────────────────────────────────────

@dataclass
class GapFinding:
    metric: str
    subsector: str
    observed: float
    percentile_estimate: Optional[int]
    gap_to_median: Optional[float]
    direction: str        # "above" | "below" | "at"
    commentary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "subsector": self.subsector,
            "observed": self.observed,
            "percentile_estimate": self.percentile_estimate,
            "gap_to_median": self.gap_to_median,
            "direction": self.direction,
            "commentary": self.commentary,
        }


# Metrics where LOW values are better (lower = better ops).
_LOW_IS_BETTER = {
    "days_in_ar",
    "initial_denial_rate",
    "final_writeoff_rate",
    "avg_length_of_stay_days",
}


def _commentary(metric: str, pct: Optional[int], gap: Optional[float]) -> str:
    if pct is None or gap is None:
        return "Insufficient data for positioning."
    if metric in _LOW_IS_BETTER:
        # Below median = better.
        if pct <= 25:
            return f"Top-quartile on {metric}."
        if pct <= 50:
            return f"Better than peer median on {metric}."
        if pct <= 75:
            return f"Worse than peer median — opportunity exists on {metric}."
        return f"Bottom-quartile on {metric} — a named lever."
    # Higher = better (most metrics).
    if pct >= 75:
        return f"Top-quartile on {metric} — rare advantage."
    if pct >= 50:
        return f"Above peer median on {metric}."
    if pct >= 25:
        return f"Below peer median on {metric} — room to improve."
    return f"Bottom-quartile on {metric} — priority lever."


def compare_to_peers(
    subsector: str,
    observations: Dict[str, float],
) -> List[GapFinding]:
    """Compare a deal's metrics to the subsector benchmark medians.

    Returns one :class:`GapFinding` per metric where a benchmark
    exists. Missing metrics or missing benchmarks are skipped.
    """
    findings: List[GapFinding] = []
    for metric, value in observations.items():
        if value is None:
            continue
        bm = get_benchmark(subsector, metric)
        if bm is None or bm.p50 is None:
            continue
        pct = bm.percentile(float(value))
        gap = float(value) - bm.p50
        if metric in _LOW_IS_BETTER:
            direction = "below" if value < bm.p50 else ("at" if value == bm.p50 else "above")
        else:
            direction = "above" if value > bm.p50 else ("at" if value == bm.p50 else "below")
        findings.append(GapFinding(
            metric=metric,
            subsector=_canonical(subsector),
            observed=float(value),
            percentile_estimate=pct,
            gap_to_median=gap,
            direction=direction,
            commentary=_commentary(metric, pct, gap),
        ))
    findings.sort(key=lambda f: (f.metric,))
    return findings
