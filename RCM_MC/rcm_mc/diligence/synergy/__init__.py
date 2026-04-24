"""Synergy realization (Gap 8).

    integration_velocity.py     — time-to-Epic-consolidation + cost
    cross_referral_reality_check.py — sister-practice referral test
"""
from __future__ import annotations

from .cross_referral_reality_check import (
    CrossReferralRealityCheck, check_cross_referral_claim,
)
from .integration_velocity import (
    IntegrationVelocity, estimate_ehr_migration,
)

__all__ = [
    "CrossReferralRealityCheck",
    "IntegrationVelocity",
    "check_cross_referral_claim",
    "estimate_ehr_migration",
]
