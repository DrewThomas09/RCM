"""Org-design scoring — span of control, layers, role clarity.

Three dimensions partners check during diligence:

  span_of_control     average direct reports per manager.
                      Healthcare PE typical: 6-8. <4 = under-
                      utilized managers; >12 = micromanagement
                      collapse.
  layers              CEO → IC count of management layers.
                      Healthcare typical: 5-6 for $100M+
                      platforms. >7 = over-bureaucratic;
                      <4 = reporting-line gaps for a $100M+
                      asset.
  role_clarity        composite of "no dual-hat roles" + "no
                      missing critical functions" + "named CFO/
                      COO if revenue >$50M".

Plus healthcare-specific anti-pattern flags: clinical-leader-
as-COO, dual-hat CFO/CRO at $50M+ revenue, missing CMO at
hospital/MSO platforms, etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .executive import ManagementTeam


@dataclass
class OrgDesignScore:
    """Composite + per-dimension scores + anti-pattern flags."""
    span_of_control: float
    avg_span: float
    layers: int
    layers_score: float
    role_clarity: float
    anti_patterns: List[str] = field(default_factory=list)
    composite: float = 0.0
    band: str = "average"


def _band(composite: float) -> str:
    if composite >= 4.5:
        return "standout"
    if composite >= 4.0:
        return "above_avg"
    if composite >= 3.0:
        return "average"
    if composite >= 2.0:
        return "below_avg"
    return "concerning"


def score_org_design(
    team: ManagementTeam,
    *,
    revenue_mm: float = 0.0,
    sector: str = "",
) -> OrgDesignScore:
    """Score org design + flag healthcare-specific anti-patterns."""
    n_executives = len(team.executives)
    if n_executives == 0:
        return OrgDesignScore(
            span_of_control=0.0, avg_span=0.0, layers=0,
            layers_score=0.0, role_clarity=0.0, composite=0.0)

    # ── Span of control ─────────────────────────────────────
    spans = [e.direct_reports for e in team.executives
             if e.direct_reports > 0]
    avg_span = sum(spans) / len(spans) if spans else 0.0
    if 6 <= avg_span <= 8:
        span_score = 5.0
    elif 4 <= avg_span < 6 or 8 < avg_span <= 10:
        span_score = 4.0
    elif 2 <= avg_span < 4 or 10 < avg_span <= 14:
        span_score = 2.5
    else:
        span_score = 1.5

    # ── Layers ──────────────────────────────────────────────
    layers = team.org_layers
    if 4 <= layers <= 6:
        layers_score = 5.0
    elif layers in (3, 7):
        layers_score = 3.5
    elif layers == 2 or layers == 8:
        layers_score = 2.0
    else:
        layers_score = 1.0

    # ── Role clarity ────────────────────────────────────────
    roles = {e.role.upper() for e in team.executives}
    has_ceo = "CEO" in roles
    has_cfo = "CFO" in roles
    has_coo = "COO" in roles
    role_score = 5.0
    if not has_ceo:
        role_score -= 2.0
    if revenue_mm >= 50 and not has_cfo:
        role_score -= 1.5
    if revenue_mm >= 100 and not has_coo:
        role_score -= 1.0

    # ── Healthcare anti-patterns ───────────────────────────
    anti_patterns: List[str] = []
    sector_l = sector.lower()
    # Dual-hat CFO/CRO above $50M
    cfo_cro_dual = any(
        ("CFO" in e.role.upper() and "CRO" in e.role.upper())
        for e in team.executives
    )
    if cfo_cro_dual and revenue_mm >= 50:
        anti_patterns.append(
            "Dual-hat CFO/CRO at $50M+ revenue — separate the "
            "roles before close.")
        role_score -= 1.0
    # Missing CMO at hospital / MSO platforms
    if (sector_l in ("hospital", "mso", "physician_group")
            and "CMO" not in roles):
        anti_patterns.append(
            f"No CMO named at a {sector_l} platform — clinical-"
            "leadership gap.")
        role_score -= 0.5
    # Clinical leader as COO
    for e in team.executives:
        if e.role.upper() == "COO" and (
                "clinical" in (e.notes or "").lower()
                or "physician" in (e.notes or "").lower()):
            anti_patterns.append(
                "Clinical leader holds COO role — typically "
                "under-resourced for ops execution.")
            role_score -= 0.5
            break

    role_score = max(0.0, role_score)

    composite = (span_score * 0.30
                 + layers_score * 0.30
                 + role_score * 0.40)
    return OrgDesignScore(
        span_of_control=round(span_score, 3),
        avg_span=round(avg_span, 2),
        layers=layers,
        layers_score=round(layers_score, 3),
        role_clarity=round(role_score, 3),
        anti_patterns=anti_patterns,
        composite=round(composite, 3),
        band=_band(composite),
    )
