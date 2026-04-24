"""Covenant & Capital Structure Stress Lab.

Turns the Deal MC EBITDA cone and the target's debt schedule into
per-quarter covenant-breach probability curves.  Fused with the
Regulatory Calendar overlay, this module answers the partner
question current tools can't: *"In what quarter does the thesis hit
a covenant cliff, and how much equity do I need to cure?"*

Public API::

    from rcm_mc.diligence.covenant_lab import (
        CapitalStack, CovenantDefinition, CovenantStressResult,
        DEFAULT_COVENANTS, DebtTranche, TrancheKind,
        default_lbo_stack, run_covenant_stress,
    )
"""
from __future__ import annotations

from .capital_stack import (
    CapitalStack, DebtTranche, QuarterlyDebtService,
    TrancheKind, TrancheQuarter, build_debt_schedule,
    default_lbo_stack,
)
from .covenants import (
    CovenantDefinition, CovenantKind, CovenantTestResult,
    DEFAULT_COVENANTS, evaluate_covenant,
)
from .simulator import (
    CovenantStressResult, EquityCure, FirstBreachQuarter,
    QuarterlyCovenantCurve, run_covenant_stress,
)

__all__ = [
    "CapitalStack",
    "CovenantDefinition",
    "CovenantKind",
    "CovenantStressResult",
    "CovenantTestResult",
    "DEFAULT_COVENANTS",
    "DebtTranche",
    "EquityCure",
    "FirstBreachQuarter",
    "QuarterlyCovenantCurve",
    "QuarterlyDebtService",
    "TrancheKind",
    "TrancheQuarter",
    "build_debt_schedule",
    "default_lbo_stack",
    "evaluate_covenant",
    "run_covenant_stress",
]
