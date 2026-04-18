"""Synergy sequencing — when each synergy actually lands.

Partner statement: "Y1 is stabilization, not synergy.
The seller's slides show $12M synergy in Y1 — I know
that's not real. Back-office is Y2. Payer renegotiation
is Y3. If their timing is wrong, their math is wrong."

Distinct from `synergy_credibility_scorer` (is the
synergy real at all?) and `synergy_modeler` (how big?).
This module scores **timing** — does the synergy land
in the year the plan claims?

### 10 synergy categories + typical landing year

- **purchasing_gpo_rebates** — Y1.
- **ancillary_rationalization** — Y1-Y2.
- **capex_rationalization** — Y1-Y2.
- **shared_services_back_office** — Y2-Y3.
- **real_estate_consolidation** — Y2-Y3.
- **revenue_cycle_standardization** — Y2-Y3.
- **physician_comp_normalization** — Y2-Y3.
- **payer_contract_renegotiation** — Y3-Y4.
- **it_ehr_consolidation** — Y3-Y4.
- **cross_sell_upsell** — Y3-Y4.

### Haircut math

If seller's claimed year is **earlier** than the typical
window, partner haircuts. Each year early = 30%
realization haircut. So Y1 claim on a Y3-typical
synergy = 60% haircut.

Claimed year equal to or later than typical = 0%
haircut (seller is being honest about timing).

### Output

Per-synergy haircut + aggregate dollar haircut +
partner note on how mis-timed the plan is.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Typical landing window per synergy category.
# (min_year, max_year) where year 1 = first full year
# post-close. Partners treat close year as Y0 (stabilization).
TYPICAL_LANDING: Dict[str, Tuple[int, int]] = {
    "purchasing_gpo_rebates": (1, 1),
    "ancillary_rationalization": (1, 2),
    "capex_rationalization": (1, 2),
    "shared_services_back_office": (2, 3),
    "real_estate_consolidation": (2, 3),
    "revenue_cycle_standardization": (2, 3),
    "physician_comp_normalization": (2, 3),
    "payer_contract_renegotiation": (3, 4),
    "it_ehr_consolidation": (3, 4),
    "cross_sell_upsell": (3, 4),
}


@dataclass
class ClaimedSynergy:
    category: str
    amount_m: float
    claimed_year: int


@dataclass
class SynergyAssessment:
    category: str
    amount_m: float
    claimed_year: int
    typical_min_year: int
    typical_max_year: int
    haircut_pct: float
    realized_m: float
    partner_commentary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "amount_m": self.amount_m,
            "claimed_year": self.claimed_year,
            "typical_min_year": self.typical_min_year,
            "typical_max_year": self.typical_max_year,
            "haircut_pct": self.haircut_pct,
            "realized_m": self.realized_m,
            "partner_commentary": self.partner_commentary,
        }


@dataclass
class SynergySequencingInputs:
    claimed_synergies: List[ClaimedSynergy] = field(
        default_factory=list
    )


@dataclass
class SynergySequencingReport:
    total_claimed_m: float
    total_realized_m: float
    total_haircut_m: float
    assessments: List[SynergyAssessment] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_claimed_m": self.total_claimed_m,
            "total_realized_m": self.total_realized_m,
            "total_haircut_m": self.total_haircut_m,
            "assessments": [
                a.to_dict() for a in self.assessments
            ],
            "partner_note": self.partner_note,
        }


def _haircut_pct(claimed_year: int,
                  typical_min: int,
                  typical_max: int) -> float:
    """Partners haircut 30% per year earlier than typical.
    Landing at or later than typical_min = 0% haircut."""
    if claimed_year >= typical_min:
        return 0.0
    years_early = typical_min - claimed_year
    return min(0.90, 0.30 * years_early)


def _commentary(category: str, claimed: int,
                 typical_min: int, typical_max: int,
                 haircut: float) -> str:
    if haircut == 0.0:
        return (
            f"{category} claimed Y{claimed}; typical "
            f"Y{typical_min}-Y{typical_max}. Timing "
            "honest."
        )
    years_early = typical_min - claimed
    return (
        f"{category} claimed Y{claimed} but typical is "
        f"Y{typical_min}-Y{typical_max}. {years_early} "
        f"yr(s) early → {haircut*100:.0f}% haircut."
    )


def score_synergy_sequencing(
    inputs: SynergySequencingInputs,
) -> SynergySequencingReport:
    assessments: List[SynergyAssessment] = []
    total_claimed = 0.0
    total_realized = 0.0

    for s in inputs.claimed_synergies:
        window = TYPICAL_LANDING.get(s.category, (2, 3))
        t_min, t_max = window
        hair = _haircut_pct(s.claimed_year, t_min, t_max)
        realized = round(s.amount_m * (1.0 - hair), 2)
        assessments.append(SynergyAssessment(
            category=s.category,
            amount_m=s.amount_m,
            claimed_year=s.claimed_year,
            typical_min_year=t_min,
            typical_max_year=t_max,
            haircut_pct=round(hair, 3),
            realized_m=realized,
            partner_commentary=_commentary(
                s.category, s.claimed_year, t_min, t_max, hair
            ),
        ))
        total_claimed += s.amount_m
        total_realized += realized

    haircut_total = round(total_claimed - total_realized, 2)
    haircut_pct = (
        haircut_total / total_claimed
        if total_claimed > 0 else 0.0
    )

    if haircut_pct >= 0.30:
        note = (
            f"Synergy timing is off by "
            f"{haircut_pct*100:.0f}% — "
            f"${haircut_total:,.1f}M of seller's claim is "
            "mis-sequenced. Partner: rebuild the synergy "
            "ramp with realistic per-category landing."
        )
    elif haircut_pct >= 0.15:
        note = (
            f"${haircut_total:,.1f}M "
            f"({haircut_pct*100:.0f}%) of synergy haircut "
            "for timing. Partner: flag to the team; "
            "re-phase plan."
        )
    elif haircut_total > 0:
        note = (
            f"Minor timing mis-phasing ${haircut_total:,.1f}M. "
            "Partner: accept with adjustment in the "
            "bridge."
        )
    else:
        note = (
            "Synergy timing honest vs. partner-typical "
            "landing. Proceed on face."
        )

    return SynergySequencingReport(
        total_claimed_m=round(total_claimed, 2),
        total_realized_m=round(total_realized, 2),
        total_haircut_m=haircut_total,
        assessments=assessments,
        partner_note=note,
    )


def list_synergy_categories() -> List[str]:
    return list(TYPICAL_LANDING.keys())


def render_synergy_sequencing_markdown(
    r: SynergySequencingReport,
) -> str:
    lines = [
        "# Synergy sequencing scorer",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Claimed: ${r.total_claimed_m:,.1f}M",
        f"- Realized (partner view): "
        f"${r.total_realized_m:,.1f}M",
        f"- Haircut: ${r.total_haircut_m:,.1f}M",
        "",
        "| Category | Claimed Y | Typical Y | Amount | "
        "Haircut | Realized | Partner commentary |",
        "|---|---|---|---|---|---|---|",
    ]
    for a in r.assessments:
        lines.append(
            f"| {a.category} | Y{a.claimed_year} | "
            f"Y{a.typical_min_year}-Y{a.typical_max_year} | "
            f"${a.amount_m:,.1f}M | "
            f"{a.haircut_pct*100:.0f}% | "
            f"${a.realized_m:,.1f}M | "
            f"{a.partner_commentary} |"
        )
    return "\n".join(lines)
