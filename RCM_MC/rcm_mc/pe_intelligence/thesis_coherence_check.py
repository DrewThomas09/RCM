"""Thesis coherence check — do the pillars fit together?

Partner reflex: "You claim margin expansion AND volume growth of
15% AND labor cost reduction AND quality-metric improvement — how
does that work?" Most decks propose thesis pillars independently.
A partner mentally checks whether they are internally consistent.

This module takes the named thesis claims (each with a quantified
delta) and flags contradictions:

- Volume growth vs labor productivity vs margin expansion.
- Price growth vs payer renegotiation lag.
- Quality improvement vs rapid growth.
- Multiple expansion vs subsector trajectory.
- Roll-up engine vs integration staffing.

Output: a list of named incoherences, each with the pair of
pillars that conflict and the partner's rebuttal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ThesisPillar:
    name: str
    claim_pct: float                      # positive = growth / expansion
    description: str = ""


@dataclass
class Incoherence:
    pair: tuple                            # (pillar_name_a, pillar_name_b)
    severity: str                          # "high" / "medium"
    contradiction: str
    partner_rebuttal: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair": list(self.pair),
            "severity": self.severity,
            "contradiction": self.contradiction,
            "partner_rebuttal": self.partner_rebuttal,
        }


@dataclass
class CoherenceReport:
    pillars: List[ThesisPillar] = field(default_factory=list)
    incoherences: List[Incoherence] = field(default_factory=list)
    coherence_score_0_100: int = 100
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pillars": [
                {"name": p.name, "claim_pct": p.claim_pct,
                 "description": p.description} for p in self.pillars
            ],
            "incoherences": [i.to_dict() for i in self.incoherences],
            "coherence_score_0_100": self.coherence_score_0_100,
            "partner_note": self.partner_note,
        }


def _pillar(pillars: List[ThesisPillar], name: str) -> Optional[ThesisPillar]:
    for p in pillars:
        if p.name == name:
            return p
    return None


def check_coherence(pillars: List[ThesisPillar]) -> CoherenceReport:
    incoherences: List[Incoherence] = []

    volume = _pillar(pillars, "volume_growth")
    margin = _pillar(pillars, "margin_expansion")
    labor = _pillar(pillars, "labor_cost_reduction")
    price = _pillar(pillars, "price_growth")
    quality = _pillar(pillars, "quality_improvement")
    roll_up = _pillar(pillars, "roll_up_closings")
    integration = _pillar(pillars, "integration_investment")
    multiple = _pillar(pillars, "multiple_expansion")

    # Volume + margin without labor increase.
    if volume and margin and volume.claim_pct >= 0.12 \
            and margin.claim_pct >= 0.02 \
            and (labor is None or labor.claim_pct <= 0):
        incoherences.append(Incoherence(
            pair=("volume_growth", "margin_expansion"),
            severity="high",
            contradiction=(
                f"{volume.claim_pct*100:.0f}% volume growth with "
                f"{margin.claim_pct*100:.0f}% margin expansion and no "
                "labor investment is internally inconsistent. Growth "
                "needs capacity; capacity needs labor."),
            partner_rebuttal=(
                "Pick two: you can grow volume, expand margin, or "
                "hold labor flat. You cannot do all three. Show me "
                "the capacity analysis that resolves this."),
        ))

    # Price growth > 5% — rarely compatible with current contracts.
    if price and price.claim_pct >= 0.05:
        incoherences.append(Incoherence(
            pair=("price_growth", "contract_reality"),
            severity="medium",
            contradiction=(
                f"{price.claim_pct*100:.0f}% price growth exceeds "
                "typical healthcare rate-card increases. Usually this "
                "number hides mix-shift rather than true rate growth."),
            partner_rebuttal=(
                "Separate rate cards from mix shift. The number to "
                "model in base case is pure rate 2-3%."),
        ))

    # Quality + rapid growth is classic tension.
    if volume and quality and volume.claim_pct >= 0.15 \
            and quality.claim_pct > 0:
        incoherences.append(Incoherence(
            pair=("volume_growth", "quality_improvement"),
            severity="medium",
            contradiction=(
                f"Rapid volume growth ({volume.claim_pct*100:.0f}%) "
                "typically depresses quality metrics 18-24 months "
                "during ramp. Both improving simultaneously is rare."),
            partner_rebuttal=(
                "Either growth slows in year 1 to preserve quality, "
                "or quality dips then recovers in year 3. Pick which "
                "story matches the deck's quality trajectory."),
        ))

    # Roll-up closings without integration investment.
    if roll_up and roll_up.claim_pct >= 0.10 \
            and (integration is None or integration.claim_pct <= 0.02):
        incoherences.append(Incoherence(
            pair=("roll_up_closings", "integration_investment"),
            severity="high",
            contradiction=(
                "Aggressive roll-up pace without proportional "
                "integration investment produces pro-forma EBITDA "
                "that does not survive audit (AdaptHealth pattern)."),
            partner_rebuttal=(
                "For every dollar of acquired revenue, budget 2-3 "
                "cents of integration spend. If that's not in the "
                "model, the pro-forma is fiction."),
        ))

    # Multiple expansion at face value.
    if multiple and multiple.claim_pct > 0:
        incoherences.append(Incoherence(
            pair=("multiple_expansion", "exit_underwriting"),
            severity="medium",
            contradiction=(
                "Multiple-expansion-dependent MOIC math assumes the "
                "market pays MORE for you at exit than it paid at "
                "entry. That is the weakest leg in any thesis."),
            partner_rebuttal=(
                "Re-underwrite with flat or declining exit multiple. "
                "If the math does not work without expansion, the "
                "math does not work."),
        ))

    # Labor cost reduction WITHOUT tech or process investment.
    tech = _pillar(pillars, "technology_investment")
    process = _pillar(pillars, "process_redesign")
    if labor and labor.claim_pct <= -0.05 \
            and (tech is None or tech.claim_pct <= 0) \
            and (process is None or process.claim_pct <= 0):
        incoherences.append(Incoherence(
            pair=("labor_cost_reduction", "enabling_investment"),
            severity="high",
            contradiction=(
                f"{abs(labor.claim_pct)*100:.0f}% labor cost reduction "
                "without technology or process investment is "
                "headcount cuts. In healthcare, that compresses "
                "quality metrics and triggers clinician flight."),
            partner_rebuttal=(
                "Where is the enabling investment? If this is just "
                "RIFs, we know how this movie ends."),
        ))

    # Score: 100 minus penalties.
    score = 100
    for i in incoherences:
        score -= 20 if i.severity == "high" else 8
    score = max(0, score)

    if score >= 85:
        note = ("Thesis pillars fit together. No coherence issues.")
    elif score >= 60:
        note = (f"Thesis has {len(incoherences)} pillar(s) in tension. "
                "Walk management through the specific contradictions "
                "before IC.")
    else:
        note = (f"Thesis is internally incoherent ({len(incoherences)} "
                "contradictions). The deck has not done the work — "
                "either management is papering over inconsistencies, "
                "or they have not stress-tested the pillars against "
                "each other.")

    return CoherenceReport(
        pillars=list(pillars),
        incoherences=incoherences,
        coherence_score_0_100=score,
        partner_note=note,
    )


def render_coherence_markdown(r: CoherenceReport) -> str:
    lines = [
        "# Thesis coherence check",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Coherence score: **{r.coherence_score_0_100}/100**",
        f"- Pillars checked: {len(r.pillars)}",
        f"- Incoherences found: {len(r.incoherences)}",
        "",
    ]
    if r.incoherences:
        lines.append("## Pillar tensions")
        lines.append("")
        for i in r.incoherences:
            lines.append(f"### {' ↔ '.join(i.pair)} ({i.severity.upper()})")
            lines.append(f"- **Contradiction:** {i.contradiction}")
            lines.append(f"- **Partner rebuttal:** {i.partner_rebuttal}")
            lines.append("")
    return "\n".join(lines)
