"""Stark / AKS red-line detector.

Rule-based flags for configurations that have historically drawn
FCA / DOJ attention. Not legal advice — output is analytic with
statutory cites.

Historical anchors:
    - Tuomey $72.4M (2015): compensation tied to volume of
      anticipated referrals.
    - Adventist $118.7M (2015): per-click arrangements above FMV.
    - Sutter $46.1M (2018): pass-through of referral volume in
      compensation formulas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .comp_ingester import Provider
from .fmv_benchmarks import get_benchmark, percentile_placement


@dataclass
class StarkFinding:
    provider_id: str
    npi: Optional[str]
    finding_code: str              # short label
    severity: str = "MEDIUM"       # LOW | MEDIUM | HIGH | CRITICAL
    statutory_cite: str = ""
    detail: str = ""
    remediation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def check_stark_redline(
    providers: Iterable[Provider],
    *,
    ownership_type: str = "hospital_employed",
    per_click_fmv_hourly_usd: float = 1500.0,
) -> List[StarkFinding]:
    """Scan every provider for red-line signatures."""
    out: List[StarkFinding] = []
    for p in providers:
        # 1) Aggregate comp above p90 with significant directed comp.
        placement = percentile_placement(
            p.total_comp_usd, specialty=p.specialty,
            ownership_type=ownership_type,
        )
        directed_share = (
            p.total_directed_comp_usd / p.total_comp_usd
            if p.total_comp_usd > 0 else 0.0
        )
        if placement == "above_p90" and directed_share >= 0.35:
            out.append(StarkFinding(
                provider_id=p.provider_id, npi=p.npi,
                finding_code="STACKED_ABOVE_P90",
                severity="CRITICAL",
                statutory_cite="42 USC § 1395nn (Stark); 42 USC § 1320a-7b (AKS)",
                detail=(
                    f"Provider's total comp is above 90th percentile "
                    f"for {p.specialty} ({ownership_type}); "
                    f"{directed_share*100:.0f}% is directed comp "
                    f"(stipend + call + admin + productivity)."
                ),
                remediation=(
                    "Obtain a fair-market-value opinion from VMG or "
                    "equivalent independent valuer covering every "
                    "directed-comp component BEFORE close."
                ),
            ))

        # 2) Per-click arrangement above the FMV hourly cap.
        if p.hours_worked_annual and p.hours_worked_annual > 0:
            per_hour = p.total_comp_usd / float(p.hours_worked_annual)
            if per_hour > per_click_fmv_hourly_usd:
                out.append(StarkFinding(
                    provider_id=p.provider_id, npi=p.npi,
                    finding_code="PER_CLICK_ABOVE_FMV",
                    severity="HIGH",
                    statutory_cite="42 CFR § 411.357(d)",
                    detail=(
                        f"Comp-per-hour ${per_hour:,.0f} exceeds the "
                        f"${per_click_fmv_hourly_usd:,.0f}/hr FMV anchor "
                        f"(Adventist $118.7M, 2015)."
                    ),
                    remediation=(
                        "Restructure hour-based component to align "
                        "with specialty-specific FMV study."
                    ),
                ))

        # 3) Collections-based compensation that passes through
        # referral volume. Signal: comp-as-%-of-collections > 60%
        # AND no directed-comp counterweight — means comp moves 1:1
        # with referral-driven collections.
        if (p.collections_annual_usd > 0
            and p.total_comp_usd / p.collections_annual_usd > 0.60
                and directed_share < 0.10):
            out.append(StarkFinding(
                provider_id=p.provider_id, npi=p.npi,
                finding_code="COLLECTIONS_PASS_THROUGH",
                severity="HIGH",
                statutory_cite="42 CFR § 411.354(d)(5) (Stark volume/value)",
                detail=(
                    "Comp scales directly with collections "
                    f"({(p.total_comp_usd/p.collections_annual_usd)*100:.0f}%) "
                    "and is overwhelmingly base-rate — volume/value "
                    "correlation concern. Tuomey/Sutter precedents "
                    "apply."
                ),
                remediation=(
                    "Restructure to wRVU-based comp or add a "
                    "quality-gate scalar that breaks the direct "
                    "collections coupling."
                ),
            ))
    return out
