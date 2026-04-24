"""Referral-leakage + provider-concentration diligence (Prompt M, Gap 5).

Two submodules:

    leakage_analyzer.py         — network-retained vs. network-leaked
                                   referral volume
    provider_concentration.py   — revenue-by-top-N-providers + departure
                                   stress tests
"""
from __future__ import annotations

from .leakage_analyzer import (
    LeakageResult, analyze_referral_leakage,
)
from .provider_concentration import (
    ProviderConcentrationResult, DepartureStressResult,
    compute_provider_concentration, stress_test_departures,
)

__all__ = [
    "DepartureStressResult",
    "LeakageResult",
    "ProviderConcentrationResult",
    "analyze_referral_leakage",
    "compute_provider_concentration",
    "stress_test_departures",
]
