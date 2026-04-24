"""Payer Mix Stress Lab.

Stress-tests a target's commercial payer portfolio: per-payer
rate-move Monte Carlo informed by curated payer-behavior
priors + concentration amplifier + cumulative EBITDA at risk.

Public API::

    from rcm_mc.diligence.payer_stress import (
        PAYER_PRIORS, PayerCategory, PayerMixEntry, PayerPrior,
        PayerStressReport, PayerStressRow, PayerStressVerdict,
        YearlyNPRImpact,
        classify_payer, default_hospital_mix, get_payer,
        list_payers, run_payer_stress,
    )
"""
from __future__ import annotations

from .contract_simulator import (
    PayerMixEntry, PayerStressReport, PayerStressRow,
    PayerStressVerdict, YearlyNPRImpact,
    default_hospital_mix, run_payer_stress,
)
from .payer_library import (
    PAYER_PRIORS, PayerCategory, PayerPrior,
    classify_payer, get_payer, list_payers,
)

__all__ = [
    "PAYER_PRIORS",
    "PayerCategory",
    "PayerMixEntry",
    "PayerPrior",
    "PayerStressReport",
    "PayerStressRow",
    "PayerStressVerdict",
    "YearlyNPRImpact",
    "classify_payer",
    "default_hospital_mix",
    "get_payer",
    "list_payers",
    "run_payer_stress",
]
