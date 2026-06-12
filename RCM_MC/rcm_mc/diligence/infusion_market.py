"""National infusion-market scan — rank every state for an infusion
roll-up using the SAME real public data the Texas page already uses.

After sizing Texas, the natural next question is "where else?". This
scores all 50 states + DC on the structural factors that make an
ambulatory-infusion / home-infusion roll-up work — a large, MA-steered
senior base, no Certificate-of-Need barrier to de-novo, metro density,
and a commercial-leaning payer base — entirely from real vendored data
(ACS demographics + CMS MA geographic variation) plus the documented
no-CON state list. Every figure is a pure function of those inputs; the
weights are a labeled analyst framework.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

# The ~12 states with NO general Certificate-of-Need regime (documented;
# de-novo ambulatory infusion is unconstrained there). Verify as of the
# engagement — CON law changes.
NON_CON_STATES = {"AZ", "CA", "CO", "ID", "KS", "MN", "ND", "NM",
                  "SD", "TX", "UT", "WY"}

#: Attractiveness weights (sum to 1.0) — a documented analyst framework.
_WEIGHTS = {
    "senior_base": 0.28,      # size of the 65+ infusion-demand base
    "ma_steerage": 0.24,      # MA penetration → site-of-care steerage
    "no_con": 0.18,           # de-novo runway (no CON barrier)
    "density": 0.15,          # metro density → route/chair economics
    "commercial": 0.15,       # commercial-leaning payer base
}


def infusion_state_attractiveness() -> Dict[str, Any]:
    """Score + rank every state for an infusion roll-up. Returns the
    ranked states (each with its component axes) + the methodology."""
    from ..data.county_demographics import demographics_state
    from ..data.ma_data import ma_state
    from .texas_infusion import _US_STATES, _STATE_NAME

    rows: List[Dict[str, Any]] = []
    for code in _US_STATES:
        d = demographics_state(code) or {}
        pop = float(d.get("population") or 0)
        pct65 = float(d.get("pct_age_65_plus") or 0.16)
        rural = float(d.get("pct_rural") or 0.20)
        unins = float(d.get("uninsured_rate") or 0.10)
        income = float(d.get("median_household_income") or 70_000)
        seniors = pop * pct65
        m = ma_state(code) or {}
        ma_enr = float(m.get("ma_enrollment") or 0)
        ma_pen = min(0.95, ma_enr / seniors) if seniors else 0.45
        non_con = code in NON_CON_STATES

        # Axes, each 0–1.
        size_ax = min(1.0, math.log10(max(seniors, 1)) / math.log10(6e6))
        ma_ax = min(1.0, ma_pen / 0.60)
        con_ax = 1.0 if non_con else 0.0
        density_ax = 1.0 - min(rural, 0.50) / 0.50
        commercial_ax = (0.5 * (1 - min(unins, 0.25) / 0.25)
                         + 0.5 * min(income / 90_000, 1.0))
        axes = {"senior_base": size_ax, "ma_steerage": ma_ax,
                "no_con": con_ax, "density": density_ax,
                "commercial": commercial_ax}
        score = 100.0 * sum(axes[k] * w for k, w in _WEIGHTS.items())
        rows.append({
            "code": code, "name": _STATE_NAME.get(code, code),
            "score": round(score, 1), "axes": {k: round(v, 3)
                                               for k, v in axes.items()},
            "seniors": round(seniors), "ma_penetration": round(ma_pen, 3),
            "no_con": non_con, "pct_rural": round(rural, 4),
            "median_income": round(income),
        })
    rows.sort(key=lambda r: -r["score"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    tx = next((r for r in rows if r["code"] == "TX"), None)
    return {
        "states": rows,
        "weights": _WEIGHTS,
        "non_con_states": sorted(NON_CON_STATES),
        "texas": tx,
        "note": ("State infusion-roll-up attractiveness — a weighted blend "
                 "of senior base, MA penetration (site-of-care steerage), "
                 "no-CON de-novo runway, metro density, and commercial "
                 "payer mix. Demographics from ACS (vendored), MA from the "
                 "CMS MA geographic-variation file; the no-CON list and the "
                 "weights are a documented framework — verify CON status as "
                 "of the engagement. Illustrative, not a recommendation."),
    }
