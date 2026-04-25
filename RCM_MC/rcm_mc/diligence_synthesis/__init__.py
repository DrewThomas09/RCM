"""Diligence synthesis — runs every packet against one target.

This is the glue layer that turns the 8 stand-alone packets into
a single IC-ready output. Given a target dossier (deal name +
sector + states + EBITDA + optional cohort + optional financial
panel), this module:

  1. Hits the pricing foundation for the target's NPIs
  2. Runs PayerNegotiationSimulator on key codes
  3. Runs VBC LTV (Bridge v3) on the cohort if present
  4. Runs ReferralNetworkPacket if a referral graph is supplied
  5. Runs RegulatoryRiskPacket against the supplied corpus
  6. Runs QoE-AutoFlagger on the financial panel
  7. Runs BuyAndBuildOptimizer on add-on candidates
  8. Runs ExitReadinessPacket against the exit-target profile
  9. Runs VBC-ContractValuator on cohort × programs

Each module fails open — if a section's inputs aren't present,
it returns ``None`` and the synthesis result documents the gap
in ``missing_inputs``. The partner can't get a half-broken result.

Public API::

    from rcm_mc.diligence_synthesis import (
        DiligenceDossier,
        run_full_diligence,
        SynthesisResult,
    )
"""
from .dossier import DiligenceDossier, SynthesisResult
from .runner import run_full_diligence

__all__ = [
    "DiligenceDossier",
    "SynthesisResult",
    "run_full_diligence",
]
