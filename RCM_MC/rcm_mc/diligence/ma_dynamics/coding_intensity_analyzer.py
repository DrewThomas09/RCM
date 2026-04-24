"""Coding-intensity analyzer — Aetna/CVS pattern detector.

Flags patterns that draw FCA attention:

- Add-only retrospective chart review (codes added to prior years
  without corresponding removals)
- HCC capture rates significantly above specialty/regional benchmarks
- Diagnoses documented in unusual care settings (wellness visits
  capturing aggressive chronic conditions)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


@dataclass
class CodingIntensityFinding:
    target_name: str
    capture_rate: float
    benchmark_capture_rate: float
    capture_ratio: float              # target / benchmark
    add_only_retrospective_pct: float
    wellness_visit_hcc_rate: Optional[float]
    severity: str = "LOW"             # LOW | MEDIUM | HIGH | CRITICAL
    fca_exposure_estimate_usd: float = 0.0
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _load_thresholds() -> Dict[str, Any]:
    data = yaml.safe_load(
        (CONTENT_DIR / "v28_hcc_deltas.yaml").read_text("utf-8")
    )
    return data.get("capture_rate_thresholds") or {}


def analyze_coding_intensity(
    *,
    target_name: str,
    target_hcc_capture_rate: float,    # fraction of members with ≥1 HCC
    specialty_benchmark_capture_rate: float,
    add_only_retrospective_pct: float = 0.0,    # 1.0 = all adds, no removals
    wellness_visit_hcc_rate: Optional[float] = None,
    total_ma_revenue_usd: float = 0.0,
) -> CodingIntensityFinding:
    """Run the analyzer. Returns a finding with severity + FCA
    exposure estimate.

    FCA exposure estimate (rough): the capture ratio × 20% of MA
    revenue × 2 (doubled for treble damages under FCA). Only fires
    when the capture ratio is above the CRITICAL threshold —
    partner-quote only."""
    thresholds = _load_thresholds()
    watch_mult = float(
        thresholds.get("specialty_benchmark_multiplier_watch", 1.20)
    )
    critical_mult = float(
        thresholds.get("specialty_benchmark_multiplier_critical", 1.40)
    )

    ratio = (
        target_hcc_capture_rate / specialty_benchmark_capture_rate
        if specialty_benchmark_capture_rate > 0 else 0.0
    )

    # Severity rollup: capture-ratio + add-only share + wellness-visit
    # rate all contribute.
    sev = "LOW"
    if ratio >= critical_mult:
        sev = "HIGH"
    elif ratio >= watch_mult:
        sev = "MEDIUM"
    if add_only_retrospective_pct >= 0.90 and ratio >= watch_mult:
        sev = "CRITICAL"
    elif add_only_retrospective_pct >= 0.75 and ratio >= critical_mult:
        sev = "CRITICAL"
    elif (wellness_visit_hcc_rate is not None
          and wellness_visit_hcc_rate >= 0.6
          and ratio >= critical_mult):
        sev = "CRITICAL"

    fca_estimate = 0.0
    if sev == "CRITICAL" and total_ma_revenue_usd > 0:
        fca_estimate = total_ma_revenue_usd * 0.20 * 2.0

    parts: List[str] = []
    parts.append(
        f"Capture ratio {ratio:.2f}x benchmark"
        f" ({target_hcc_capture_rate:.2f} vs "
        f"{specialty_benchmark_capture_rate:.2f})"
    )
    if add_only_retrospective_pct >= 0.75:
        parts.append(
            f"Add-only retrospective share {add_only_retrospective_pct*100:.0f}% "
            "— Aetna/CVS pattern"
        )
    if wellness_visit_hcc_rate is not None and wellness_visit_hcc_rate >= 0.5:
        parts.append(
            f"Wellness-visit HCC capture {wellness_visit_hcc_rate*100:.0f}%"
        )
    narrative = "; ".join(parts)
    if sev == "CRITICAL":
        narrative += (
            ". FCA exposure estimate includes doubled (treble-damages) "
            "baseline — consult counsel before IC."
        )

    return CodingIntensityFinding(
        target_name=target_name,
        capture_rate=target_hcc_capture_rate,
        benchmark_capture_rate=specialty_benchmark_capture_rate,
        capture_ratio=ratio,
        add_only_retrospective_pct=add_only_retrospective_pct,
        wellness_visit_hcc_rate=wellness_visit_hcc_rate,
        severity=sev,
        fca_exposure_estimate_usd=fca_estimate,
        narrative=narrative,
    )
