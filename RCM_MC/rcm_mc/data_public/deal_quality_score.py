"""Deal quality scoring — data completeness + analytical credibility.

Scores each corpus deal on two axes:
- Completeness: weighted presence of analytically useful fields
- Credibility: internal consistency checks (MOIC/IRR alignment, EV/EBITDA bounds, etc.)

Combined into a 0-100 quality score and A/B/C/D tier.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Field weights for completeness (required-for-any-analysis fields are excluded;
# we only reward *extra* analytical richness beyond the baseline)
_COMPLETENESS_WEIGHTS: Dict[str, int] = {
    "sector":             20,
    "ebitda_at_entry_mm": 18,
    "year":               10,
    "source":              8,
    "ebitda_mm":           8,
    "ev_ebitda":           7,
    "deal_type":           6,
    "region":              6,
    "revenue_mm":          5,
    "geography":           4,
    "state":               3,
    "leverage_pct":        3,
    "notes":               2,
}
_MAX_COMPLETENESS = sum(_COMPLETENESS_WEIGHTS.values())  # 100

# Credibility checks
@dataclass
class CredibilityFlag:
    key: str
    severity: str  # "error" | "warn"
    message: str


@dataclass
class DealQualityScore:
    source_id: str
    deal_name: str
    completeness_raw: int        # 0–100 (points earned)
    completeness_pct: float      # 0.0–1.0
    credibility_raw: int         # 0–100 (starts at 100, deductions applied)
    credibility_pct: float       # 0.0–1.0
    quality_score: float         # 0–100 composite
    tier: str                    # A / B / C / D
    flags: List[CredibilityFlag] = field(default_factory=list)
    missing_fields: List[str]    = field(default_factory=list)


def _irr_from_moic(moic: float, hold: float) -> Optional[float]:
    if moic <= 0 or hold <= 0:
        return None
    return moic ** (1.0 / hold) - 1.0


def _credibility_check(deal: Dict[str, Any]) -> tuple[int, List[CredibilityFlag]]:
    """Return (deduction_points, flags). Starts at 100."""
    flags: List[CredibilityFlag] = []
    deductions = 0

    moic = deal.get("realized_moic")
    irr  = deal.get("realized_irr")
    ev   = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm") or deal.get("ebitda_mm")
    hold = deal.get("hold_years")
    ev_ebitda = deal.get("ev_ebitda")

    # --- MOIC sanity
    try:
        m = float(moic)
        if m <= 0:
            flags.append(CredibilityFlag("moic_negative", "error", f"MOIC={m:.2f}x ≤ 0 — invalid"))
            deductions += 30
        elif m > 20:
            flags.append(CredibilityFlag("moic_extreme", "warn", f"MOIC={m:.2f}x — >20× outlier; verify"))
            deductions += 5
    except (TypeError, ValueError):
        pass

    # --- IRR sanity
    try:
        i = float(irr)
        if i < -1.0:
            flags.append(CredibilityFlag("irr_below_neg100", "error", f"IRR={i*100:.1f}% < -100%"))
            deductions += 20
        elif i > 5.0:
            flags.append(CredibilityFlag("irr_extreme", "warn", f"IRR={i*100:.1f}% > 500%"))
            deductions += 5
    except (TypeError, ValueError):
        pass

    # --- MOIC / IRR alignment
    try:
        m = float(moic); i = float(irr); h = float(hold)
        if h > 0:
            implied_irr = _irr_from_moic(m, h)
            if implied_irr is not None:
                diff = abs(implied_irr - i)
                if diff > 0.25:
                    flags.append(CredibilityFlag(
                        "moic_irr_mismatch", "warn",
                        f"MOIC {m:.1f}x / hold {h:.1f}y implies IRR {implied_irr*100:.1f}% "
                        f"vs reported {i*100:.1f}% (Δ={diff*100:.1f}pp)"
                    ))
                    deductions += 10
    except (TypeError, ValueError):
        pass

    # --- EV sanity
    try:
        e = float(ev)
        if e <= 0:
            flags.append(CredibilityFlag("ev_nonpositive", "error", f"EV={e:.1f}M ≤ 0"))
            deductions += 25
        elif e > 50_000:
            flags.append(CredibilityFlag("ev_implausible", "warn", f"EV={e:.0f}M — unusually large"))
            deductions += 5
    except (TypeError, ValueError):
        pass

    # --- EV/EBITDA reasonableness
    try:
        e_ev = float(ev_ebitda) if ev_ebitda is not None else (float(ev) / float(ebitda) if ev and ebitda else None)
        if e_ev is not None:
            if e_ev < 2 or e_ev > 40:
                flags.append(CredibilityFlag(
                    "ev_ebitda_range", "warn",
                    f"EV/EBITDA={e_ev:.1f}x outside 2–40× typical healthcare PE"
                ))
                deductions += 8
    except (TypeError, ValueError, ZeroDivisionError):
        pass

    # --- Hold years
    try:
        h = float(hold)
        if h <= 0:
            flags.append(CredibilityFlag("hold_nonpositive", "error", f"hold={h:.1f}y ≤ 0"))
            deductions += 15
        elif h > 15:
            flags.append(CredibilityFlag("hold_long", "warn", f"hold={h:.1f}y > 15y — atypical"))
            deductions += 5
    except (TypeError, ValueError):
        pass

    credibility = max(0, 100 - deductions)
    return credibility, flags


def score_deal_quality(deal: Dict[str, Any]) -> DealQualityScore:
    # Completeness
    pts = sum(w for f, w in _COMPLETENESS_WEIGHTS.items() if deal.get(f) is not None)
    missing = [f for f in _COMPLETENESS_WEIGHTS if deal.get(f) is None]
    c_pct = pts / _MAX_COMPLETENESS

    # Credibility
    cred_raw, flags = _credibility_check(deal)
    cred_pct = cred_raw / 100.0

    # Composite: 55% completeness, 45% credibility
    quality = round(55 * c_pct + 45 * cred_pct, 1)

    if quality >= 75:
        tier = "A"
    elif quality >= 55:
        tier = "B"
    elif quality >= 35:
        tier = "C"
    else:
        tier = "D"

    return DealQualityScore(
        source_id=deal.get("source_id", ""),
        deal_name=deal.get("deal_name", ""),
        completeness_raw=pts,
        completeness_pct=c_pct,
        credibility_raw=cred_raw,
        credibility_pct=cred_pct,
        quality_score=quality,
        tier=tier,
        flags=flags,
        missing_fields=missing,
    )


def score_corpus_quality(corpus: List[Dict[str, Any]]) -> List[DealQualityScore]:
    return [score_deal_quality(d) for d in corpus]
