"""
Optional fast surrogate / ML layer — NOT used by the main CLI or report.

Intended use (future):
- Train on many Monte Carlo runs: features = flattened config scalars, target = mean(ebitda_drag).
- Deploy for portfolio screening or interactive “what-if” before running full n_sims.

Guardrails:
- Do not replace simulator output for diligence sign-off.
- Any UI using a surrogate must label outputs as approximate.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def predict_mean_ebitda_drag_stub(_features: Dict[str, float]) -> Optional[float]:
    """
    Placeholder for a trained surrogate. Returns None until a real model is wired.

    Parameters
    ----------
    _features :
        Example keys: payer mix shares, IDR/FWR means by payer, dar_clean means, etc.

    Returns
    -------
    None
        Implementations should return a float prediction when trained.
    """
    return None


def training_data_schema() -> Dict[str, Any]:
    """Document expected columns for a future training export script."""
    return {
        "description": "One row per Monte Carlo run or per config grid point.",
        "suggested_targets": ["mean_ebitda_drag", "p90_ebitda_drag"],
        "suggested_features": [
            "hospital.annual_revenue",
            "payers.Medicare.revenue_share",
            "payers.Commercial.denials.idr.mean",
            "payers.Commercial.denials.fwr.mean",
            "economics.wacc_annual",
        ],
        "source_artifacts": ["simulations.csv", "summary.csv", "provenance.json"],
    }
