"""Claims denial root-cause classifier — what's actually causing the denials.

Partner statement: "12% denial rate means nothing
until you know the composition. If it's 9%
eligibility + 2% prior-auth + 1% other, I'll take
it — that's fixable with a front-end tool in 6
months. If it's 6% medical-necessity + 3% non-
covered + 1% COB + 2% other, that's a different
deal entirely. The category mix IS the thesis."

Distinct from:
- `denial_fix_pace_detector` — given mix, projects
  forward pace.
- `cash_conversion_drift_detector` — trend detector.
- `rcm_vendor_switching_cost_assessor` — transition
  cost.

This module takes observed packet signals and
**classifies** the implied denial root-cause mix
into 4 bands (easy / moderate / hard / structural)
with partner-read on the thesis implications.

### Signal → root-cause inference

Signals that shift probability toward different root
causes:

- **Eligibility problems** (front-end):
  walk-in / non-appointment volume high, registration
  staff turnover high, payer-portal integration
  missing.

- **Prior-authorization** (mid-cycle):
  sub-specialty procedure heavy, commercial payer
  concentration, no centralized auth team.

- **Medical necessity** (back-end, hard):
  complex documentation, physician-driven coding,
  CDI program absent, RAC history.

- **COB / timely filing** (process):
  multi-payer patient base, Medicare secondary
  payer heavy, decentralized billing.

### Output

Per-category probability weight, dominant category,
fix-difficulty verdict, partner note on whether the
thesis underwrites the realistic fix path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


EASY_CATEGORIES = {
    "eligibility_verification",
    "invalid_format",
    "timely_filing",
    "duplicate_claim",
}
MODERATE_CATEGORIES = {
    "prior_authorization",
    "coordination_of_benefits",
}
HARD_CATEGORIES = {
    "medical_necessity",
    "non_covered_service",
}


@dataclass
class DenialClassifierInputs:
    observed_denial_rate_pct: float = 0.10
    # Signals that tilt toward categories:
    walk_in_volume_share: float = 0.20
    """High walk-in → more eligibility problems."""
    registration_staff_turnover_pct: float = 0.25
    commercial_payer_mix_share: float = 0.45
    """Commercial payers drive prior-auth."""
    subspecialty_procedure_share: float = 0.30
    centralized_auth_team: bool = True
    cdi_program_present: bool = False
    rac_audit_history: bool = False
    medicare_secondary_payer_share: float = 0.15
    decentralized_billing: bool = False


@dataclass
class CategoryWeight:
    category: str
    estimated_share_of_denials_pct: float
    fix_difficulty_band: str


@dataclass
class DenialRootCauseReport:
    categories: List[CategoryWeight] = field(
        default_factory=list)
    dominant_category: str = ""
    easy_share_pct: float = 0.0
    moderate_share_pct: float = 0.0
    hard_share_pct: float = 0.0
    fix_difficulty_verdict: str = "moderate"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "categories": [
                {"category": c.category,
                 "estimated_share_of_denials_pct":
                     c.estimated_share_of_denials_pct,
                 "fix_difficulty_band":
                     c.fix_difficulty_band}
                for c in self.categories
            ],
            "dominant_category": self.dominant_category,
            "easy_share_pct": self.easy_share_pct,
            "moderate_share_pct": self.moderate_share_pct,
            "hard_share_pct": self.hard_share_pct,
            "fix_difficulty_verdict":
                self.fix_difficulty_verdict,
            "partner_note": self.partner_note,
        }


def _band(category: str) -> str:
    if category in EASY_CATEGORIES:
        return "easy"
    if category in MODERATE_CATEGORIES:
        return "moderate"
    if category in HARD_CATEGORIES:
        return "hard"
    return "moderate"


def classify_denial_root_causes(
    inputs: DenialClassifierInputs,
) -> DenialRootCauseReport:
    # Base weights (empirical healthcare-services baseline)
    weights: Dict[str, float] = {
        "eligibility_verification": 0.25,
        "prior_authorization": 0.20,
        "timely_filing": 0.08,
        "duplicate_claim": 0.08,
        "coordination_of_benefits": 0.07,
        "invalid_format": 0.07,
        "medical_necessity": 0.20,
        "non_covered_service": 0.05,
    }

    # Signal tilts
    if inputs.walk_in_volume_share > 0.30:
        weights["eligibility_verification"] += 0.10
    if inputs.registration_staff_turnover_pct > 0.30:
        weights["eligibility_verification"] += 0.05
    if inputs.commercial_payer_mix_share > 0.50:
        weights["prior_authorization"] += 0.10
    if inputs.subspecialty_procedure_share > 0.40:
        weights["prior_authorization"] += 0.08
    if not inputs.centralized_auth_team:
        weights["prior_authorization"] += 0.08
    if not inputs.cdi_program_present:
        weights["medical_necessity"] += 0.10
    if inputs.rac_audit_history:
        weights["medical_necessity"] += 0.05
    if inputs.medicare_secondary_payer_share > 0.20:
        weights["coordination_of_benefits"] += 0.05
    if inputs.decentralized_billing:
        weights["timely_filing"] += 0.05
        weights["duplicate_claim"] += 0.05

    # Normalize to sum to 1.0
    total = sum(weights.values())
    for k in list(weights.keys()):
        weights[k] = weights[k] / max(0.01, total)

    categories = [
        CategoryWeight(
            category=k,
            estimated_share_of_denials_pct=round(v, 4),
            fix_difficulty_band=_band(k),
        )
        for k, v in weights.items()
    ]
    categories.sort(
        key=lambda c: c.estimated_share_of_denials_pct,
        reverse=True,
    )

    dominant = categories[0].category
    easy = sum(
        c.estimated_share_of_denials_pct for c in categories
        if c.fix_difficulty_band == "easy"
    )
    moderate = sum(
        c.estimated_share_of_denials_pct for c in categories
        if c.fix_difficulty_band == "moderate"
    )
    hard = sum(
        c.estimated_share_of_denials_pct for c in categories
        if c.fix_difficulty_band == "hard"
    )

    if hard >= 0.35:
        verdict = "structural"
        note = (
            f"Hard-category share {hard:.0%} — medical-"
            "necessity / non-covered dominate. These "
            "are documentation and physician-behavior "
            "problems; 18-24 months to move if CDI "
            "program is introduced and physicians "
            "commit."
        )
    elif hard >= 0.20:
        verdict = "hard"
        note = (
            f"Hard-category share {hard:.0%}; "
            "thesis must fund CDI program and "
            "physician-documentation coaching. Not a "
            "12-month fix."
        )
    elif easy >= 0.50:
        verdict = "easy"
        note = (
            f"Easy-category share {easy:.0%} — "
            "eligibility / format / duplicate / timely "
            "filing dominate. Front-end platform + "
            "training gets material lift in 6 months."
        )
    else:
        verdict = "moderate"
        note = (
            f"Balanced denial mix — easy "
            f"{easy:.0%}, moderate {moderate:.0%}, "
            f"hard {hard:.0%}. Sequence fixes: "
            "front-end first (biggest early wins), "
            "prior-auth centralization next, medical-"
            "necessity is year 2+."
        )

    return DenialRootCauseReport(
        categories=categories,
        dominant_category=dominant,
        easy_share_pct=round(easy, 4),
        moderate_share_pct=round(moderate, 4),
        hard_share_pct=round(hard, 4),
        fix_difficulty_verdict=verdict,
        partner_note=note,
    )


def render_denial_root_cause_markdown(
    r: DenialRootCauseReport,
) -> str:
    lines = [
        "# Claims denial root-cause classification",
        "",
        f"_Verdict: **{r.fix_difficulty_verdict}**_ — "
        f"{r.partner_note}",
        "",
        f"- Dominant category: {r.dominant_category}",
        f"- Easy share: {r.easy_share_pct:.0%}",
        f"- Moderate share: {r.moderate_share_pct:.0%}",
        f"- Hard share: {r.hard_share_pct:.0%}",
        "",
        "| Category | Share | Band |",
        "|---|---|---|",
    ]
    for c in r.categories:
        lines.append(
            f"| {c.category} | "
            f"{c.estimated_share_of_denials_pct:.0%} | "
            f"{c.fix_difficulty_band} |"
        )
    return "\n".join(lines)
