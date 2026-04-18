"""Payer-mix shift cascade — the second canonical cross-module story.

Sister to `rcm_lever_cascade`. When a deck claims a payer-mix
shift (e.g., Medicaid → commercial), the implications cascade:

1. **Mix shift magnitude** — pp of revenue moving between payers.
2. **Effective blended rate change** — commercial pays 1.5-2x
   Medicaid / 1.2-1.4x Medicare per same service.
3. **Revenue impact** — shift × rate delta × volume.
4. **EBITDA impact** — revenue lift × contribution margin.
5. **Exit multiple implication** — commercial-heavier book
   commands a higher multiple (narrow but real).

Partner scrutiny: a claimed 10pp commercial shift without signed
contract wins is a claim, not a thesis. The cascade makes the
math explicit so the partner can ask the right question.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Rough rate premiums relative to Medicare FFS = 1.0x.
RATE_MULTIPLIER = {
    "medicare_ffs": 1.00,
    "medicare_advantage": 1.05,
    "medicaid": 0.65,
    "commercial": 1.60,
    "self_pay": 0.45,
}


@dataclass
class MixShiftInputs:
    deal_name: str = "Deal"
    revenue_m: float = 0.0
    contribution_margin: float = 0.45
    # Current mix (must sum roughly to 1.0):
    current_medicare_ffs_pct: float = 0.25
    current_medicare_advantage_pct: float = 0.15
    current_medicaid_pct: float = 0.20
    current_commercial_pct: float = 0.35
    current_self_pay_pct: float = 0.05
    # Target mix (what management is promising):
    target_medicare_ffs_pct: float = 0.20
    target_medicare_advantage_pct: float = 0.15
    target_medicaid_pct: float = 0.10
    target_commercial_pct: float = 0.50
    target_self_pay_pct: float = 0.05
    years_to_achieve: int = 3
    commercial_contracts_signed: int = 0
    commercial_contracts_in_pipeline: int = 0


@dataclass
class MixShiftStep:
    step: int
    name: str
    description: str
    value: float
    unit: str
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step, "name": self.name,
            "description": self.description,
            "value": self.value, "unit": self.unit,
            "partner_note": self.partner_note,
        }


@dataclass
class MixShiftReport:
    steps: List[MixShiftStep] = field(default_factory=list)
    effective_rate_delta_pct: float = 0.0
    revenue_impact_m: float = 0.0
    ebitda_impact_m: float = 0.0
    multiple_uplift_x: float = 0.0
    credibility_score_0_100: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "effective_rate_delta_pct": self.effective_rate_delta_pct,
            "revenue_impact_m": self.revenue_impact_m,
            "ebitda_impact_m": self.ebitda_impact_m,
            "multiple_uplift_x": self.multiple_uplift_x,
            "credibility_score_0_100": self.credibility_score_0_100,
            "partner_note": self.partner_note,
        }


def _blended_rate(mix: Dict[str, float]) -> float:
    return sum(mix[k] * RATE_MULTIPLIER[k] for k in mix)


def trace_mix_shift(inputs: MixShiftInputs) -> MixShiftReport:
    current_mix = {
        "medicare_ffs": inputs.current_medicare_ffs_pct,
        "medicare_advantage": inputs.current_medicare_advantage_pct,
        "medicaid": inputs.current_medicaid_pct,
        "commercial": inputs.current_commercial_pct,
        "self_pay": inputs.current_self_pay_pct,
    }
    target_mix = {
        "medicare_ffs": inputs.target_medicare_ffs_pct,
        "medicare_advantage": inputs.target_medicare_advantage_pct,
        "medicaid": inputs.target_medicaid_pct,
        "commercial": inputs.target_commercial_pct,
        "self_pay": inputs.target_self_pay_pct,
    }

    current_blended = _blended_rate(current_mix)
    target_blended = _blended_rate(target_mix)
    rate_delta = (target_blended - current_blended) / max(0.01, current_blended)

    commercial_shift_pp = (inputs.target_commercial_pct
                            - inputs.current_commercial_pct) * 100

    steps: List[MixShiftStep] = []

    # Step 1: magnitude.
    steps.append(MixShiftStep(
        step=1, name="mix_shift_magnitude",
        description=(f"Commercial share "
                     f"{inputs.current_commercial_pct*100:.0f}% → "
                     f"{inputs.target_commercial_pct*100:.0f}%"),
        value=round(commercial_shift_pp, 2), unit="pp",
        partner_note=(
            f"{commercial_shift_pp:.1f}pp shift over "
            f"{inputs.years_to_achieve} years. That is "
            f"{commercial_shift_pp / max(inputs.years_to_achieve, 1):.1f}pp "
            "per year of commercial capture. Partner context: >3pp/yr "
            "without signed contract wins is wishful."),
    ))

    # Step 2: effective rate change.
    steps.append(MixShiftStep(
        step=2, name="effective_rate_change",
        description=f"Blended rate multiplier change",
        value=round(rate_delta * 100, 2), unit="pct",
        partner_note=(
            f"Blended effective rate lifts "
            f"{rate_delta*100:.1f}% if mix realizes as pitched. "
            "This assumes commercial rate multipliers hold; if "
            "seller assumes rate increases + mix shift together, "
            "you are double-counting."),
    ))

    # Step 3: revenue impact.
    rev_impact = inputs.revenue_m * rate_delta
    steps.append(MixShiftStep(
        step=3, name="revenue_impact",
        description="Revenue lift from rate change",
        value=round(rev_impact, 2), unit="$M",
        partner_note=(
            f"${rev_impact:,.1f}M of revenue lift at full realization. "
            "Assume 50% realization probability in base case."),
    ))

    # Step 4: EBITDA impact.
    ebitda_impact = rev_impact * inputs.contribution_margin
    steps.append(MixShiftStep(
        step=4, name="ebitda_impact",
        description="EBITDA lift from revenue × contribution margin",
        value=round(ebitda_impact, 2), unit="$M",
        partner_note=(
            f"${ebitda_impact:,.1f}M EBITDA lift at full realization. "
            "This is the exit-multiple-eligible lift (recurring, not "
            "one-time)."),
    ))

    # Step 5: exit multiple uplift.
    # Heuristic: 0.25x multiple uplift per 10pp of commercial shift.
    mult_uplift = (commercial_shift_pp / 10.0) * 0.25
    steps.append(MixShiftStep(
        step=5, name="exit_multiple_uplift",
        description="Exit multiple uplift from richer payer mix",
        value=round(mult_uplift, 2), unit="x",
        partner_note=(
            f"{mult_uplift:.2f}x exit multiple uplift if commercial "
            "shift holds at exit. Partner note: buyers discount "
            "un-contracted mix; actual uplift is ~50% of modeled."),
    ))

    # Credibility score.
    score = 100
    if commercial_shift_pp / max(inputs.years_to_achieve, 1) > 3:
        score -= 30
    if inputs.commercial_contracts_signed == 0 and commercial_shift_pp > 0:
        score -= 25
    if inputs.commercial_contracts_in_pipeline < commercial_shift_pp / 2:
        score -= 15
    score = max(0, score)

    if score < 40:
        note = (f"Mix-shift thesis: {commercial_shift_pp:.1f}pp over "
                f"{inputs.years_to_achieve}y is aggressive AND "
                "contract pipeline is thin. Credibility "
                f"{score}/100 — underwrite at ≤ 25% realization.")
    elif score < 70:
        note = (f"Mix-shift thesis has some contract backing. "
                f"Credibility {score}/100 — underwrite at 50% "
                "realization.")
    elif commercial_shift_pp == 0:
        note = ("No mix shift claimed — model is straight on current "
                "blended rate.")
    else:
        note = (f"Mix-shift thesis is credible ({score}/100) — "
                "signed contracts support the claim. Model at 70-80% "
                "realization.")

    return MixShiftReport(
        steps=steps,
        effective_rate_delta_pct=round(rate_delta * 100, 4),
        revenue_impact_m=round(rev_impact, 2),
        ebitda_impact_m=round(ebitda_impact, 2),
        multiple_uplift_x=round(mult_uplift, 3),
        credibility_score_0_100=score,
        partner_note=note,
    )


def render_mix_shift_markdown(r: MixShiftReport) -> str:
    lines = [
        "# Payer-mix shift cascade",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Effective rate delta: {r.effective_rate_delta_pct:.2f}%",
        f"- Revenue impact: ${r.revenue_impact_m:,.1f}M",
        f"- EBITDA impact: ${r.ebitda_impact_m:,.1f}M",
        f"- Exit multiple uplift: {r.multiple_uplift_x:.2f}x",
        f"- Credibility: **{r.credibility_score_0_100}/100**",
        "",
    ]
    for s in r.steps:
        lines.append(f"## Step {s.step}: {s.name}")
        lines.append(f"- {s.description}: **{s.value}{s.unit}**")
        lines.append(f"- Partner note: {s.partner_note}")
        lines.append("")
    return "\n".join(lines)
