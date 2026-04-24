"""High-Deductible Health Plan segmentation.

HDHP members produce outsized patient-responsibility balances.
Recovery on patient balances is a fraction of insurer-paid
recovery, so the share of HDHP members in the payer mix is a
leading indicator of bad-debt reserve.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


# Typical HDHP balance recovery rate vs insurer-paid (industry
# aggregates — HDHP members recover at ~30-50% vs insurer-paid ~95%).
HDHP_RECOVERY_RATE_BENCHMARK = 0.40
INSURER_RECOVERY_RATE_BENCHMARK = 0.95


@dataclass
class HDHPExposure:
    hdhp_member_share: float
    est_bad_debt_delta_usd: float        # vs. non-HDHP baseline
    patient_responsibility_dollars_usd: float
    severity: str                         # LOW | MEDIUM | HIGH

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def segment_patient_pay_exposure(
    *,
    hdhp_member_share: float,
    total_patient_responsibility_usd: float,
) -> HDHPExposure:
    """Compute the incremental bad-debt exposure from HDHP members.

    Formula: hdhp_responsibility × (insurer_rate - hdhp_rate).
    That's the gap between what a non-HDHP-equivalent book would
    have recovered and what the HDHP-heavy book actually recovers.
    """
    hdhp_responsibility = (
        total_patient_responsibility_usd * float(hdhp_member_share)
    )
    recovery_gap = INSURER_RECOVERY_RATE_BENCHMARK - HDHP_RECOVERY_RATE_BENCHMARK
    delta = hdhp_responsibility * recovery_gap
    if hdhp_member_share >= 0.40:
        sev = "HIGH"
    elif hdhp_member_share >= 0.20:
        sev = "MEDIUM"
    else:
        sev = "LOW"
    return HDHPExposure(
        hdhp_member_share=float(hdhp_member_share),
        est_bad_debt_delta_usd=delta,
        patient_responsibility_dollars_usd=hdhp_responsibility,
        severity=sev,
    )
