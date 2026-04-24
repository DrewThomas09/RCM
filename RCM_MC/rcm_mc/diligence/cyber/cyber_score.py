"""CyberScore composite (0-100) + bridge-reserve lever.

Rolls the submodule outputs into a single 0-100 score displayed on
the DealAnalysisPacket overview alongside EBITDA and EV. Lower =
worse. Banding:

    RED    — score < 40   (blocks full-packet build pending override)
    YELLOW — 40 ≤ score < 65
    GREEN  — score ≥ 65

Bridge reserve: maps the band to a % of revenue reserved in the
v2 bridge's new "cyber risk reserve" lever.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CyberScore:
    score: int                     # 0-100
    band: str                      # GREEN | YELLOW | RED
    bi_expected_loss_usd: float = 0.0
    ba_critical_count: int = 0
    ehr_vendor_risk: Optional[int] = None
    it_capex_severity: str = "LOW"
    block_packet_build: bool = False
    findings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "band": self.band,
            "bi_expected_loss_usd": self.bi_expected_loss_usd,
            "ba_critical_count": self.ba_critical_count,
            "ehr_vendor_risk": self.ehr_vendor_risk,
            "it_capex_severity": self.it_capex_severity,
            "block_packet_build": self.block_packet_build,
            "findings": list(self.findings),
        }


def compose_cyber_score(
    *,
    external_rating: Optional[int] = None,      # 0-100, lower=safer
    ehr_vendor_risk: Optional[int] = None,      # 0-100, lower=safer
    ba_findings: Optional[List[Any]] = None,
    it_capex: Optional[Any] = None,
    bi_loss: Optional[Any] = None,
    annual_revenue_usd: float = 0.0,
) -> CyberScore:
    """Compose the 0-100 CyberScore + packet-blocking flag."""
    # Start from 75 baseline and penalise/credit from there.
    score = 75
    findings: List[str] = []

    # External rating: 0..100 where lower=safer. Apply as a
    # linear credit/penalty. 50 external → neutral.
    if external_rating is not None:
        score -= (external_rating - 50) // 2

    # EHR vendor risk: 50 → neutral; high-risk cuts.
    vendor_penalty = 0
    if ehr_vendor_risk is not None:
        vendor_penalty = (ehr_vendor_risk - 50) // 3
        score -= vendor_penalty

    # BA cascade: each CRITICAL BA finding -15, each HIGH -8.
    ba_crit = 0
    if ba_findings:
        for f in ba_findings:
            sev = getattr(f, "severity", "")
            if sev == "CRITICAL":
                ba_crit += 1
                score -= 15
                findings.append(
                    f"BA cascade CRITICAL: {getattr(f, 'ba_name', '?')}"
                )
            elif sev == "HIGH":
                score -= 8
                findings.append(
                    f"BA cascade HIGH: {getattr(f, 'ba_name', '?')}"
                )

    # IT capex severity.
    capex_sev = "LOW"
    if it_capex is not None:
        capex_sev = getattr(it_capex, "severity", "LOW")
        if capex_sev == "CRITICAL":
            score -= 20
            findings.append(
                "IT capex CRITICAL — EHR overdue + staffing gap"
            )
        elif capex_sev == "HIGH":
            score -= 12
        elif capex_sev == "MEDIUM":
            score -= 5

    # BI expected loss: penalise proportional to revenue.
    bi_exp = 0.0
    if bi_loss is not None:
        bi_exp = float(getattr(bi_loss, "expected_loss_usd", 0) or 0)
        if annual_revenue_usd > 0:
            ratio = bi_exp / annual_revenue_usd
            if ratio >= 0.05:
                score -= 20
                findings.append(
                    f"BI expected loss ${bi_exp:,.0f} is "
                    f"{ratio*100:.1f}% of revenue"
                )
            elif ratio >= 0.02:
                score -= 10

    score = max(0, min(100, score))
    if score < 40:
        band = "RED"
    elif score < 65:
        band = "YELLOW"
    else:
        band = "GREEN"

    block = (band == "RED")
    return CyberScore(
        score=score, band=band,
        bi_expected_loss_usd=bi_exp,
        ba_critical_count=ba_crit,
        ehr_vendor_risk=ehr_vendor_risk,
        it_capex_severity=capex_sev,
        block_packet_build=block,
        findings=findings,
    )


def cyber_bridge_reserve_pct(band: str) -> float:
    """Map the CyberScore band to a % of revenue reserved in the
    v2 bridge's cyber-risk-reserve lever. Default 0 / 1-2% / 5%+."""
    b = (band or "").upper()
    if b == "GREEN":
        return 0.0
    if b == "YELLOW":
        return 0.015      # 1.5%
    if b == "RED":
        return 0.05       # 5%
    return 0.0
