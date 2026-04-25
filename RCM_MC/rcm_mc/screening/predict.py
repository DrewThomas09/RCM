"""Predict per-deal screening metrics.

For each candidate, compute:

  predicted_improvement_pct   the operational-lift % a sponsor
                              could deliver on this asset (0-1)
  predicted_ebitda_uplift_mm  $-equivalent of that lift over a
                              5-year hold
  confidence                  0-1; combines comparable-deal n
                              with regulatory risk
  risk_factors                top 3 flagged risks per the
                              regulatory + concentration models

Inputs come from each candidate's profile dict — no external
data fetched at predict time. The partner runs this against the
deals_corpus or their own watchlist.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import numpy as np


@dataclass
class DealCandidate:
    """Deal in the screening universe — one input row."""
    deal_id: str
    name: str
    sector: str
    state: str = ""
    cbsa: str = ""
    revenue_mm: float = 0.0
    ebitda_mm: float = 0.0
    ebitda_margin: float = 0.0
    growth_rate: float = 0.05
    payer_concentration: float = 0.40       # top payer share
    physician_concentration: float = 0.30
    cash_pay_share: float = 0.10
    out_of_network_share: float = 0.05
    has_pe_history: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreeningResult:
    """Per-deal prediction + risk factors."""
    deal_id: str
    name: str
    sector: str
    revenue_mm: float
    ebitda_mm: float
    predicted_improvement_pct: float
    predicted_ebitda_uplift_mm: float
    confidence: float
    confidence_band: str            # high / medium / low
    risk_factors: List[str] = field(default_factory=list)
    notes: str = ""


# Per-sector base improvement potential (% of EBITDA) — calibrated
# to typical realized PE operational lifts in healthcare.
_SECTOR_BASE_IMPROVEMENT = {
    "physician_group": 0.30,    # 30% lift typical via add-on
                                 # rollup + RCM optimization
    "mso": 0.30,
    "asc": 0.25,
    "behavioral_health": 0.25,
    "skilled_nursing": 0.15,
    "home_health": 0.18,
    "dialysis": 0.10,
    "hospital": 0.12,
    "managed_care": 0.20,
    "imaging": 0.20,
    "lab": 0.18,
    "dental": 0.30,
    "dermatology": 0.30,
    "ophthalmology": 0.30,
}


def _confidence_band(score: float) -> str:
    if score >= 0.70:
        return "high"
    if score >= 0.40:
        return "medium"
    return "low"


def _identify_risk_factors(c: DealCandidate) -> List[str]:
    """Surface the top risk factors flagged by the existing
    regulatory + concentration models."""
    out: List[str] = []
    if c.payer_concentration > 0.55:
        out.append(
            f"Payer concentration {c.payer_concentration*100:.0f}% — "
            "single-payer dependency")
    if c.physician_concentration > 0.40:
        out.append(
            f"Physician concentration "
            f"{c.physician_concentration*100:.0f}% — key-person risk")
    if c.out_of_network_share > 0.10:
        out.append(
            f"OON revenue {c.out_of_network_share*100:.0f}% — No "
            "Surprises Act exposure")
    if c.cash_pay_share > 0.20:
        out.append(
            f"Cash-pay share {c.cash_pay_share*100:.0f}% — non-"
            "recurring revenue risk")
    if c.ebitda_margin < 0.10:
        out.append(
            f"Margin {c.ebitda_margin*100:.1f}% — turnaround case")
    if c.ebitda_mm < 5:
        out.append(
            f"EBITDA ${c.ebitda_mm:.1f}M — sub-scale; narrow buyer "
            "universe")
    if c.has_pe_history:
        out.append(
            "Prior PE ownership — expect picked-over operational "
            "fruit; thinner improvement runway")
    return out[:3]   # cap at 3 for the screening row


def predict_deal_metrics(
    candidate: DealCandidate,
) -> ScreeningResult:
    """Predict screening metrics for one candidate."""
    sec = (candidate.sector or "").lower().replace(" ", "_")
    base = _SECTOR_BASE_IMPROVEMENT.get(sec, 0.18)

    # Modifiers — concentration penalties + scale + history
    improvement = base
    if candidate.has_pe_history:
        improvement *= 0.65        # picked-over
    if candidate.payer_concentration > 0.55:
        improvement *= 0.90        # concentration drag on the
                                    # operational lift
    if candidate.physician_concentration > 0.45:
        improvement *= 0.85
    if candidate.ebitda_margin < 0.10:
        # Turnaround case — UPSIDE on the improvement % (more
        # room to lift) but lower confidence.
        improvement *= 1.30
    if candidate.growth_rate > 0.15:
        improvement *= 1.10        # tailwind from organic growth

    improvement = max(0.0, min(0.60, improvement))

    uplift_mm = candidate.ebitda_mm * improvement

    # Confidence: starts from 0.7, deducted by risks
    risk_factors = _identify_risk_factors(candidate)
    n_risks = len(risk_factors)
    confidence = 0.70 - 0.08 * n_risks
    if candidate.ebitda_mm < 3:
        confidence -= 0.10
    if candidate.has_pe_history:
        confidence += 0.05    # less uncertainty about an asset
                               # with known operational history
    confidence = max(0.0, min(1.0, confidence))

    return ScreeningResult(
        deal_id=candidate.deal_id,
        name=candidate.name,
        sector=candidate.sector,
        revenue_mm=round(candidate.revenue_mm, 2),
        ebitda_mm=round(candidate.ebitda_mm, 2),
        predicted_improvement_pct=round(improvement, 4),
        predicted_ebitda_uplift_mm=round(uplift_mm, 2),
        confidence=round(confidence, 4),
        confidence_band=_confidence_band(confidence),
        risk_factors=risk_factors,
    )


def score_universe(
    candidates: Iterable[DealCandidate],
) -> List[ScreeningResult]:
    """Predict metrics across a universe — sorted by predicted
    EBITDA uplift descending so the partner sees the biggest
    levers first."""
    results = [predict_deal_metrics(c) for c in candidates]
    results.sort(
        key=lambda r: r.predicted_ebitda_uplift_mm, reverse=True)
    return results
