"""Survival analysis for retention & readmission diligence.

Kaplan-Meier curves (Greenwood SEs, log-log bands, median survival),
the two-group log-rank test, and Cox proportional-hazards regression
(Breslow ties, Newton-Raphson, hazard ratios + concordance + a PH
diagnostic) — all numpy + stdlib. Turns a static readmission/churn
rate into a time-to-event view and tells you which factors drive risk.

See ``README.md`` and ``docs/TUVA_MYELIN_INTEGRATION.md``.
"""
from __future__ import annotations

from .estimators import (
    CoxCovariate,
    CoxResult,
    KMResult,
    LogRankResult,
    cox_ph,
    kaplan_meier,
    logrank_test,
)

__all__ = [
    "CoxCovariate",
    "CoxResult",
    "KMResult",
    "LogRankResult",
    "cox_ph",
    "kaplan_meier",
    "logrank_test",
]
