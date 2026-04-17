"""Debt sizing — partner-prudent leverage given payer mix and subsector.

Banks underwrite healthcare-PE debt capacity based on:
- Stability of EBITDA (payer mix, regulatory exposure).
- Cyclicality of the subsector.
- Covenant standards (coverage, leverage, FCF sweep).

This module gives the partner a deterministic answer to "what's the
prudent leverage for this deal?" — independent of what the lender is
willing to stretch to.

Outputs:

- :func:`prudent_leverage` — recommended leverage multiple by
  (subsector × payer_regime).
- :func:`max_interest_rate_to_break` — given debt and EBITDA, what
  rate breaks 2.0x interest coverage?
- :func:`covenant_stress_passes` — true iff a stressed EBITDA still
  clears a target leverage / coverage covenant.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


# ── Recommended leverage table ───────────────────────────────────────

_PRUDENT_LEVERAGE: Dict[Tuple[str, str], float] = {
    # Acute care — higher-stability assets can carry more.
    ("acute_care", "commercial_heavy"): 5.5,
    ("acute_care", "balanced"): 5.0,
    ("acute_care", "medicare_heavy"): 4.5,
    ("acute_care", "medicaid_heavy"): 4.0,
    ("acute_care", "govt_heavy"): 3.5,

    # ASC — high-margin but volume-sensitive.
    ("asc", "commercial_heavy"): 6.0,
    ("asc", "balanced"): 5.5,
    ("asc", "medicare_heavy"): 4.5,
    ("asc", "govt_heavy"): 4.0,

    # Behavioral — census volatility warrants conservatism.
    ("behavioral", "commercial_heavy"): 5.0,
    ("behavioral", "balanced"): 4.5,
    ("behavioral", "medicare_heavy"): 4.0,
    ("behavioral", "medicaid_heavy"): 3.5,
    ("behavioral", "govt_heavy"): 3.5,

    # Post-acute — reimbursement compression is structural.
    ("post_acute", "commercial_heavy"): 5.0,
    ("post_acute", "balanced"): 4.5,
    ("post_acute", "medicare_heavy"): 4.0,
    ("post_acute", "medicaid_heavy"): 3.5,
    ("post_acute", "govt_heavy"): 3.0,

    # Specialty — case-mix dependent.
    ("specialty", "commercial_heavy"): 5.5,
    ("specialty", "balanced"): 5.0,
    ("specialty", "medicare_heavy"): 4.0,
    ("specialty", "govt_heavy"): 3.5,

    # Outpatient / MSO — commercial-heavy platforms absorb more.
    ("outpatient", "commercial_heavy"): 5.5,
    ("outpatient", "balanced"): 5.0,
    ("outpatient", "medicare_heavy"): 4.5,
    ("outpatient", "govt_heavy"): 3.5,

    # Critical access — special case, capped low.
    ("critical_access", "commercial_heavy"): 4.0,
    ("critical_access", "balanced"): 3.5,
    ("critical_access", "medicare_heavy"): 3.0,
    ("critical_access", "govt_heavy"): 2.5,
}


def prudent_leverage(subsector: str, payer_regime: str) -> Optional[float]:
    """Return recommended leverage multiple for (subsector, regime).

    Returns None when the pair isn't in the table.
    """
    key = (subsector.lower().strip(), payer_regime.lower().strip())
    return _PRUDENT_LEVERAGE.get(key)


def leverage_headroom(
    modeled_leverage: float,
    *,
    subsector: str,
    payer_regime: str,
) -> Optional[Dict[str, Any]]:
    """Compare a modeled leverage against prudent leverage.

    Returns headroom (positive = room for more debt, negative = too
    levered) plus a partner-voice verdict. None when no prudent
    benchmark exists for the pair.
    """
    prudent = prudent_leverage(subsector, payer_regime)
    if prudent is None:
        return None
    headroom = prudent - modeled_leverage
    if headroom >= 0.5:
        verdict = "conservative"
        note = "Debt capacity to spare — sized below prudent leverage."
    elif headroom >= -0.25:
        verdict = "at_prudent"
        note = "Sized at the partner-prudent leverage ceiling."
    elif headroom >= -1.0:
        verdict = "stretched"
        note = "Modestly above prudent leverage — defensible but trim if possible."
    else:
        verdict = "over_levered"
        note = "Materially over prudent leverage — re-size at close or negotiate covenant-lite terms."
    return {
        "prudent_leverage": prudent,
        "modeled_leverage": modeled_leverage,
        "headroom": headroom,
        "verdict": verdict,
        "partner_note": note,
    }


# ── Coverage sensitivity ─────────────────────────────────────────────

def max_interest_rate_to_break(
    ebitda: float,
    debt: float,
    *,
    coverage_floor: float = 2.0,
) -> Optional[float]:
    """Highest interest rate the deal can sustain before EBITDA/interest
    falls below ``coverage_floor``.

    coverage = EBITDA / (debt * rate) >= floor
    → rate <= EBITDA / (debt * floor).
    """
    if debt <= 0:
        return None
    return ebitda / (debt * coverage_floor)


def covenant_stress_passes(
    stressed_ebitda: float,
    debt: float,
    *,
    leverage_covenant: float,
    coverage_covenant: float,
    interest_rate: float,
) -> Dict[str, Any]:
    """Verify a stressed EBITDA still clears both leverage and
    coverage covenants.

    Returns a dict with boolean pass flags and the actual ratios.
    """
    if debt <= 0:
        return {
            "leverage_ok": True,
            "coverage_ok": True,
            "leverage_ratio": 0.0,
            "coverage_ratio": float("inf"),
            "passes": True,
        }
    if stressed_ebitda <= 0:
        return {
            "leverage_ok": False,
            "coverage_ok": False,
            "leverage_ratio": float("inf"),
            "coverage_ratio": 0.0,
            "passes": False,
        }
    leverage_ratio = debt / stressed_ebitda
    interest = debt * interest_rate
    coverage_ratio = (stressed_ebitda / interest) if interest > 0 else float("inf")
    leverage_ok = leverage_ratio <= leverage_covenant
    coverage_ok = coverage_ratio >= coverage_covenant
    return {
        "leverage_ok": leverage_ok,
        "coverage_ok": coverage_ok,
        "leverage_ratio": leverage_ratio,
        "coverage_ratio": coverage_ratio,
        "passes": leverage_ok and coverage_ok,
    }
