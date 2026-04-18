"""Cycle timing — market-cycle phase detection for entry / exit timing.

Partners don't always say the word out loud, but every deal memo
has a cycle-timing assumption underneath. This module classifies
the current healthcare-PE market into one of four cycle phases:

- **early_expansion** — multiples low, deal flow high, new entrants.
- **mid_expansion** — multiples rising, competition hot, LPs active.
- **peak** — multiples at highs, competition for every deal, LP
  hesitation starts.
- **contraction** — multiples compressing, deal flow drops, LPs
  pull back.

Inputs are indicator observations — recent comp multiples vs
10-year average, deal-volume trend, interest-rate regime. Output
is a cycle-phase label + partner-voice entry / exit implications.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


PHASE_EARLY_EXPANSION = "early_expansion"
PHASE_MID_EXPANSION = "mid_expansion"
PHASE_PEAK = "peak"
PHASE_CONTRACTION = "contraction"

ALL_PHASES = (
    PHASE_EARLY_EXPANSION, PHASE_MID_EXPANSION,
    PHASE_PEAK, PHASE_CONTRACTION,
)


@dataclass
class CycleInputs:
    current_median_multiple: Optional[float] = None
    ten_year_avg_multiple: Optional[float] = None
    deal_volume_yoy: Optional[float] = None            # fraction change
    lp_commitment_yoy: Optional[float] = None
    fed_funds_rate: Optional[float] = None             # fraction
    fed_funds_direction: Optional[str] = None          # "rising" | "falling" | "flat"
    debt_spread_bps: Optional[float] = None            # vs treasuries


@dataclass
class CycleResult:
    phase: str
    confidence: float                                  # 0..1
    signals: List[str] = field(default_factory=list)
    entry_implication: str = ""
    exit_implication: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "confidence": self.confidence,
            "signals": list(self.signals),
            "entry_implication": self.entry_implication,
            "exit_implication": self.exit_implication,
            "partner_note": self.partner_note,
        }


# ── Classifier ──────────────────────────────────────────────────────

def _multiple_premium(inputs: CycleInputs) -> Optional[float]:
    if (inputs.current_median_multiple is None
            or inputs.ten_year_avg_multiple is None
            or inputs.ten_year_avg_multiple == 0):
        return None
    return (inputs.current_median_multiple / inputs.ten_year_avg_multiple) - 1.0


def classify_cycle(inputs: CycleInputs) -> CycleResult:
    """Classify the current cycle phase from indicators."""
    signals: List[str] = []
    votes = {p: 0.0 for p in ALL_PHASES}

    # Multiple premium vs 10yr avg
    prem = _multiple_premium(inputs)
    if prem is not None:
        signals.append(f"Multiple premium vs 10yr avg: {prem*100:+.1f}%")
        if prem >= 0.15:
            votes[PHASE_PEAK] += 0.45
            votes[PHASE_MID_EXPANSION] += 0.20
        elif prem >= 0.05:
            votes[PHASE_MID_EXPANSION] += 0.40
            votes[PHASE_PEAK] += 0.15
        elif prem > -0.10:
            votes[PHASE_EARLY_EXPANSION] += 0.25
            votes[PHASE_MID_EXPANSION] += 0.10
        else:
            votes[PHASE_CONTRACTION] += 0.45

    # Deal-volume YoY
    if inputs.deal_volume_yoy is not None:
        v = float(inputs.deal_volume_yoy)
        signals.append(f"Deal volume YoY: {v*100:+.1f}%")
        if v >= 0.15:
            votes[PHASE_MID_EXPANSION] += 0.20
            votes[PHASE_PEAK] += 0.15
        elif v >= 0.0:
            votes[PHASE_EARLY_EXPANSION] += 0.15
            votes[PHASE_MID_EXPANSION] += 0.10
        else:
            votes[PHASE_CONTRACTION] += 0.30

    # LP commitment YoY
    if inputs.lp_commitment_yoy is not None:
        v = float(inputs.lp_commitment_yoy)
        signals.append(f"LP commitments YoY: {v*100:+.1f}%")
        if v >= 0.10:
            votes[PHASE_MID_EXPANSION] += 0.15
            votes[PHASE_PEAK] += 0.10
        elif v < -0.10:
            votes[PHASE_CONTRACTION] += 0.30

    # Interest-rate regime
    if inputs.fed_funds_direction == "rising":
        signals.append("Fed funds: rising")
        votes[PHASE_CONTRACTION] += 0.20
        votes[PHASE_PEAK] += 0.15
    elif inputs.fed_funds_direction == "falling":
        signals.append("Fed funds: falling")
        votes[PHASE_EARLY_EXPANSION] += 0.25
        votes[PHASE_MID_EXPANSION] += 0.15

    if inputs.debt_spread_bps is not None:
        s = float(inputs.debt_spread_bps)
        signals.append(f"Debt spread: {s:.0f} bps")
        if s >= 500:
            votes[PHASE_CONTRACTION] += 0.15
        elif s <= 250:
            votes[PHASE_MID_EXPANSION] += 0.10
            votes[PHASE_PEAK] += 0.05

    # Winner.
    total = sum(votes.values())
    if total == 0:
        return CycleResult(
            phase=PHASE_MID_EXPANSION, confidence=0.0, signals=[],
            partner_note="Insufficient indicators to classify cycle.",
        )
    phase = max(votes.items(), key=lambda kv: kv[1])[0]
    confidence = votes[phase] / total

    entry_impl = {
        PHASE_EARLY_EXPANSION: (
            "Entry is structurally favorable — multiples are low and "
            "competition is light. Deploy capital."),
        PHASE_MID_EXPANSION: (
            "Entry is neutral — pick deals on fundamentals, not cycle."),
        PHASE_PEAK: (
            "Entry is unfavorable — pay peak prices for peak cashflow. "
            "Raise the bar on operating alpha."),
        PHASE_CONTRACTION: (
            "Entry is structurally favorable if you can deploy — "
            "distressed and motivated-seller opportunities emerge."),
    }[phase]
    exit_impl = {
        PHASE_EARLY_EXPANSION: (
            "Exits at current multiples are rare — target 3+ year hold "
            "for peak-cycle sale."),
        PHASE_MID_EXPANSION: (
            "Reasonable exit window. Strategic buyers active; IPO market "
            "open."),
        PHASE_PEAK: (
            "Prioritize exits now — wait-and-see means watching multiples "
            "compress during the hold."),
        PHASE_CONTRACTION: (
            "Extend hold if possible — exits into contraction are sponsor-"
            "to-sponsor with price discount."),
    }[phase]

    note = (
        f"Current cycle: {phase} (confidence {confidence*100:.0f}%). "
        f"Entry view: {'favorable' if phase in (PHASE_EARLY_EXPANSION, PHASE_CONTRACTION) else 'careful'}. "
        f"Exit view: {'attractive' if phase in (PHASE_MID_EXPANSION, PHASE_PEAK) else 'avoid'}.")

    return CycleResult(
        phase=phase,
        confidence=round(confidence, 4),
        signals=signals,
        entry_implication=entry_impl,
        exit_implication=exit_impl,
        partner_note=note,
    )


def render_cycle_markdown(result: CycleResult) -> str:
    lines = [
        "# Market cycle timing",
        "",
        f"**Phase:** {result.phase}  ",
        f"**Confidence:** {result.confidence*100:.0f}%",
        "",
        f"_{result.partner_note}_",
        "",
        "## Signals",
        "",
    ]
    for s in result.signals:
        lines.append(f"- {s}")
    lines.extend(["", "## Entry implication", "", result.entry_implication])
    lines.extend(["", "## Exit implication", "", result.exit_implication])
    return "\n".join(lines)
