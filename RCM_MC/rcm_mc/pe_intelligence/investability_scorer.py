"""Investability scorer — blended opportunity × value × stability composite.

Partners want a single 0..100 number that summarizes "how investable
is this deal" before they open the memo. The score blends three
axes:

- **Opportunity** (30%) — market structure favourability + white-space
  + addressable adjacencies. Scale: rich opportunity = high.
- **Value** (40%) — expected returns (IRR / MOIC) vs peer bands,
  multiple headroom, band verdicts. Scale: attractive price = high.
- **Stability** (30%) — robustness grade from stress grid + regime +
  concentration flags. Scale: low-risk = high.

Each axis is normalized 0..1, then weighted to form a 0..100
composite. The composite maps to a letter grade (A..F) with a partner
note that reads like an analyst briefing.

All inputs come from the other PE-intel modules via a
:class:`InvestabilityInputs` bag, so this module doesn't re-run any
analytics — it composites existing ones.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class InvestabilityInputs:
    # Market structure
    consolidation_play_score: Optional[float] = None      # 0..1 from market_structure
    fragmentation_verdict: Optional[str] = None           # fragmented/consolidating/consolidated

    # White space
    white_space_top_score: Optional[float] = None         # highest-scoring opportunity

    # Value / returns
    projected_irr: Optional[float] = None                 # fraction
    projected_moic: Optional[float] = None
    irr_verdict: Optional[str] = None                     # from reasonableness
    exit_multiple_verdict: Optional[str] = None

    # Stability
    robustness_grade: Optional[str] = None                # from stress_test: A..F
    downside_pass_rate: Optional[float] = None
    regime: Optional[str] = None                          # from regime_classifier
    posture: Optional[str] = None                         # from operating_posture
    n_critical_hits: int = 0
    n_high_hits: int = 0
    n_covenant_breaches: int = 0


@dataclass
class InvestabilityResult:
    score: int                                            # 0..100
    grade: str                                            # A..F
    opportunity_score: float                              # 0..1
    value_score: float                                    # 0..1
    stability_score: float                                # 0..1
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "grade": self.grade,
            "opportunity_score": round(self.opportunity_score, 4),
            "value_score": round(self.value_score, 4),
            "stability_score": round(self.stability_score, 4),
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "partner_note": self.partner_note,
        }


# ── Axis scoring ────────────────────────────────────────────────────

def _opportunity_score(inputs: InvestabilityInputs,
                       strengths: List[str],
                       weaknesses: List[str]) -> float:
    components: List[float] = []
    if inputs.consolidation_play_score is not None:
        components.append(float(inputs.consolidation_play_score))
        if inputs.consolidation_play_score >= 0.60:
            strengths.append(
                f"Fragmented market, consolidation-play score "
                f"{inputs.consolidation_play_score:.2f}")
        elif inputs.consolidation_play_score <= 0.30:
            weaknesses.append(
                f"Limited consolidation upside (score "
                f"{inputs.consolidation_play_score:.2f})")
    if inputs.fragmentation_verdict == "fragmented":
        components.append(0.75)
    elif inputs.fragmentation_verdict == "consolidating":
        components.append(0.55)
    elif inputs.fragmentation_verdict == "consolidated":
        components.append(0.25)
    if inputs.white_space_top_score is not None:
        components.append(float(inputs.white_space_top_score))
        if inputs.white_space_top_score >= 0.65:
            strengths.append(
                f"Clear adjacency (white-space top score "
                f"{inputs.white_space_top_score:.2f})")
    if not components:
        return 0.50  # neutral
    return sum(components) / len(components)


def _value_score(inputs: InvestabilityInputs,
                 strengths: List[str],
                 weaknesses: List[str]) -> float:
    components: List[float] = []
    # IRR verdict translates to 0..1.
    verdict_map = {
        "IN_BAND": 0.75,
        "STRETCH": 0.55,
        "OUT_OF_BAND": 0.30,
        "IMPLAUSIBLE": 0.05,
        "UNKNOWN": 0.50,
    }
    if inputs.irr_verdict:
        components.append(verdict_map.get(inputs.irr_verdict, 0.50))
        if inputs.irr_verdict == "IN_BAND":
            strengths.append("IRR inside peer band")
        elif inputs.irr_verdict == "IMPLAUSIBLE":
            weaknesses.append("IRR implausible per peer band")
    if inputs.exit_multiple_verdict:
        components.append(verdict_map.get(inputs.exit_multiple_verdict, 0.50))
        if inputs.exit_multiple_verdict in ("OUT_OF_BAND", "IMPLAUSIBLE"):
            weaknesses.append("Exit multiple outside peer comps")
    # Raw IRR contribution — a healthy 18-25% target modestly boosts,
    # anything < 10% dampens.
    if inputs.projected_irr is not None:
        if inputs.projected_irr >= 0.22:
            components.append(0.85)
        elif inputs.projected_irr >= 0.15:
            components.append(0.70)
        elif inputs.projected_irr >= 0.10:
            components.append(0.55)
        else:
            components.append(0.30)
            weaknesses.append(
                f"Sub-hurdle IRR ({inputs.projected_irr*100:.1f}%)")
    # MOIC contribution.
    if inputs.projected_moic is not None:
        if inputs.projected_moic >= 2.5:
            components.append(0.80)
            strengths.append(f"MOIC {inputs.projected_moic:.2f}x")
        elif inputs.projected_moic >= 2.0:
            components.append(0.65)
        elif inputs.projected_moic >= 1.5:
            components.append(0.45)
        else:
            components.append(0.25)
            weaknesses.append(f"Low MOIC {inputs.projected_moic:.2f}x")
    if not components:
        return 0.50
    return sum(components) / len(components)


def _stability_score(inputs: InvestabilityInputs,
                     strengths: List[str],
                     weaknesses: List[str]) -> float:
    components: List[float] = []
    grade_map = {"A": 0.95, "B": 0.80, "C": 0.60, "D": 0.35, "F": 0.10}
    if inputs.robustness_grade:
        components.append(grade_map.get(inputs.robustness_grade, 0.50))
        if inputs.robustness_grade in ("A", "B"):
            strengths.append(f"Stress grade {inputs.robustness_grade}")
        elif inputs.robustness_grade in ("D", "F"):
            weaknesses.append(f"Weak stress grade {inputs.robustness_grade}")
    if inputs.downside_pass_rate is not None:
        components.append(float(inputs.downside_pass_rate))
    # Regime
    regime_map = {
        "durable_growth": 0.90,
        "steady": 0.75,
        "emerging_volatile": 0.55,
        "stagnant": 0.45,
        "declining_risk": 0.15,
    }
    if inputs.regime:
        components.append(regime_map.get(inputs.regime, 0.50))
        if inputs.regime == "durable_growth":
            strengths.append("Durable-growth regime")
        elif inputs.regime == "declining_risk":
            weaknesses.append("Declining-risk regime")
    # Posture
    posture_map = {
        "scenario_leader": 0.90,
        "resilient_core": 0.75,
        "balanced": 0.55,
        "growth_optional": 0.45,
        "concentration_risk": 0.25,
    }
    if inputs.posture:
        components.append(posture_map.get(inputs.posture, 0.50))
        if inputs.posture == "concentration_risk":
            weaknesses.append("Concentration-risk posture")
    # Critical flags crush stability.
    if inputs.n_critical_hits > 0:
        components.append(0.05)
        weaknesses.append(f"{inputs.n_critical_hits} critical heuristic hit(s)")
    elif inputs.n_high_hits >= 3:
        components.append(0.35)
        weaknesses.append(f"{inputs.n_high_hits} HIGH-severity hits")
    if inputs.n_covenant_breaches > 0:
        components.append(0.30)
    if not components:
        return 0.50
    return sum(components) / len(components)


def _grade_from_score(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 72:
        return "B"
    if score >= 58:
        return "C"
    if score >= 42:
        return "D"
    return "F"


def _partner_note(score: int, grade: str,
                  strengths: List[str], weaknesses: List[str]) -> str:
    headline = {
        "A": "Strong investability — size up within risk limits.",
        "B": "Credible investability — proceed with discipline on the caveats.",
        "C": "Middle-of-the-road — operating levers must land for this to clear.",
        "D": "Weak investability — address gaps before IC.",
        "F": "Do not underwrite as modeled.",
    }.get(grade, "")
    if strengths and weaknesses:
        return (f"{headline} Composite {score}/100. Strengths: "
                f"{'; '.join(strengths[:3])}. Weaknesses: "
                f"{'; '.join(weaknesses[:3])}.")
    if strengths:
        return f"{headline} Composite {score}/100. Strengths: {'; '.join(strengths[:3])}."
    if weaknesses:
        return f"{headline} Composite {score}/100. Weaknesses: {'; '.join(weaknesses[:3])}."
    return f"{headline} Composite {score}/100."


# ── Orchestrator ────────────────────────────────────────────────────

def score_investability(inputs: InvestabilityInputs) -> InvestabilityResult:
    """Compute the 0..100 composite + grade + strengths/weaknesses."""
    strengths: List[str] = []
    weaknesses: List[str] = []
    opportunity = _opportunity_score(inputs, strengths, weaknesses)
    value = _value_score(inputs, strengths, weaknesses)
    stability = _stability_score(inputs, strengths, weaknesses)
    composite = 0.30 * opportunity + 0.40 * value + 0.30 * stability
    score = int(round(composite * 100))
    grade = _grade_from_score(score)
    note = _partner_note(score, grade, strengths, weaknesses)
    return InvestabilityResult(
        score=score,
        grade=grade,
        opportunity_score=opportunity,
        value_score=value,
        stability_score=stability,
        strengths=strengths,
        weaknesses=weaknesses,
        partner_note=note,
    )


def inputs_from_review(review: Any) -> InvestabilityInputs:
    """Build InvestabilityInputs from a PartnerReview.

    Pulls the upstream analytics fields (regime, market_structure,
    stress_scenarios, operating_posture, white_space) off the
    review, plus hit-severity counts and band verdicts.
    """
    ctx = review.context_summary or {}
    ms = review.market_structure or {}
    ws = review.white_space or {}
    stress = review.stress_scenarios or {}
    regime = (review.regime or {}).get("regime")
    posture = (review.operating_posture or {}).get("posture")

    irr_verdict = next((b.verdict for b in review.reasonableness_checks
                        if b.metric == "irr"), None)
    exit_verdict = next((b.verdict for b in review.reasonableness_checks
                         if b.metric == "exit_multiple"), None)

    ws_top = None
    if ws and isinstance(ws.get("opportunities"), list) and ws["opportunities"]:
        try:
            ws_top = max(float(o.get("score", 0.0)) for o in ws["opportunities"])
        except Exception:
            ws_top = None

    n_critical = sum(1 for h in review.heuristic_hits if h.severity == "CRITICAL")
    n_high = sum(1 for h in review.heuristic_hits if h.severity == "HIGH")
    n_breaches = int(stress.get("n_covenant_breaches") or 0)

    return InvestabilityInputs(
        consolidation_play_score=ms.get("consolidation_play_score"),
        fragmentation_verdict=ms.get("fragmentation_verdict"),
        white_space_top_score=ws_top,
        projected_irr=ctx.get("projected_irr"),
        projected_moic=ctx.get("projected_moic"),
        irr_verdict=irr_verdict,
        exit_multiple_verdict=exit_verdict,
        robustness_grade=stress.get("robustness_grade"),
        downside_pass_rate=stress.get("downside_pass_rate"),
        regime=regime,
        posture=posture,
        n_critical_hits=n_critical,
        n_high_hits=n_high,
        n_covenant_breaches=n_breaches,
    )
