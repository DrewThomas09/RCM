"""IC decision synthesizer — one partner-voice recommendation from many signals.

Partner reflex at IC: digest every module output (scorecard,
QoD, bear case, margin of safety, pattern library, coherence,
cascade results) into a SINGLE recommendation with the three
reasons for it and the three signals that could flip it.

This is the module that connects the brain. It does not re-run
other modules — it consumes their outputs via a `SignalBundle`
and reasons across them.

The output is IC-ready:

- **Recommendation** — INVEST / DILIGENCE MORE / PASS.
- **Three reasons FOR** — drawn from strongest positive signals.
- **Three flip-the-call signals** — what would change the
  recommendation.
- **"If I were chair, I'd say"** — the partner-voice opening
  line.
- **Pre-IC diligence must-close** — which gaps are IC-blocking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


REC_INVEST = "INVEST"
REC_DILIGENCE_MORE = "DILIGENCE MORE"
REC_PASS = "PASS"


@dataclass
class ICSignalBundle:
    """Pre-computed outputs from other brain modules."""
    deal_name: str = "Deal"
    # Scorecard (partner_scorecard):
    scorecard_all_pass: bool = False
    scorecard_failed_dimensions: List[str] = field(default_factory=list)
    # Quality of diligence (quality_of_diligence_scorer):
    qod_ic_ready: bool = False
    qod_weakest_dimension: str = ""
    qod_overall_pct: float = 0.80
    # Bear case:
    bear_moic: float = 2.0
    bear_probability_weighted_moic: float = 2.2
    bear_top_driver: Optional[str] = None
    # Margin of safety:
    safety_thin_levers: List[str] = field(default_factory=list)
    safety_combined_shock_moic: float = 1.5
    # Unrealistic-on-its-face:
    face_high_implausibilities: int = 0
    # Historical failure matches:
    historical_pattern_matches: List[str] = field(default_factory=list)
    # Partner traps:
    partner_trap_names: List[str] = field(default_factory=list)
    # Thesis coherence:
    coherence_score_0_100: int = 85
    # Cross-module insights (count of high-severity):
    connective_high_insight_count: int = 0
    # Cycle timing:
    cycle_double_peak: bool = False
    # Strengths:
    has_defensible_organic_growth: bool = True
    has_clear_exit_story: bool = True
    management_score_0_100: int = 70
    pricing_power_score_0_100: int = 60


@dataclass
class ICDecision:
    deal_name: str
    recommendation: str
    reasons_for: List[str] = field(default_factory=list)
    flip_the_call_signals: List[str] = field(default_factory=list)
    must_close_before_ic: List[str] = field(default_factory=list)
    chair_opening_line: str = ""
    score_0_100: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "recommendation": self.recommendation,
            "reasons_for": list(self.reasons_for),
            "flip_the_call_signals": list(self.flip_the_call_signals),
            "must_close_before_ic": list(self.must_close_before_ic),
            "chair_opening_line": self.chair_opening_line,
            "score_0_100": self.score_0_100,
            "partner_note": self.partner_note,
        }


def _compute_score(s: ICSignalBundle) -> int:
    score = 50
    # Heavy positives:
    if s.scorecard_all_pass:
        score += 12
    if s.has_defensible_organic_growth:
        score += 8
    if s.has_clear_exit_story:
        score += 5
    if s.qod_ic_ready:
        score += 6
    if s.coherence_score_0_100 >= 80:
        score += 6
    score += int(round((s.management_score_0_100 - 50) * 0.15))
    score += int(round((s.pricing_power_score_0_100 - 50) * 0.12))

    # Heavy negatives:
    score -= 10 * len(s.scorecard_failed_dimensions)
    score -= 12 * s.face_high_implausibilities
    score -= 8 * len(s.historical_pattern_matches)
    score -= 5 * len(s.partner_trap_names)
    score -= 7 * s.connective_high_insight_count
    score -= 5 * len(s.safety_thin_levers)
    if s.cycle_double_peak:
        score -= 10
    if s.safety_combined_shock_moic < 1.0:
        score -= 15
    if s.bear_moic < 1.0:
        score -= 12
    elif s.bear_moic < 1.5:
        score -= 5
    if not s.qod_ic_ready:
        score -= 5

    return max(0, min(100, score))


def _recommendation(s: ICSignalBundle, score: int) -> str:
    # Hard rules beat score:
    if s.face_high_implausibilities >= 1:
        return REC_PASS
    if len(s.historical_pattern_matches) >= 2:
        return REC_PASS
    if len(s.scorecard_failed_dimensions) >= 2:
        return REC_PASS
    if s.safety_combined_shock_moic < 1.0 and s.bear_moic < 1.0:
        return REC_PASS
    if not s.qod_ic_ready:
        return REC_DILIGENCE_MORE
    if score >= 72 and len(s.scorecard_failed_dimensions) == 0:
        return REC_INVEST
    if score <= 40:
        return REC_PASS
    return REC_DILIGENCE_MORE


def _reasons_for(s: ICSignalBundle) -> List[str]:
    reasons: List[str] = []
    if s.scorecard_all_pass:
        reasons.append("Passes all 7 partner must-haves — scale, "
                        "team, market, unit economics, balance "
                        "sheet, exit path, thesis integrity.")
    if s.has_defensible_organic_growth:
        reasons.append("Defensible organic growth, not acquisition-"
                        "dependent.")
    if s.bear_moic >= 1.5 and s.safety_combined_shock_moic >= 1.3:
        reasons.append(f"Bear case survivable at {s.bear_moic:.2f}x "
                        "MOIC; combined-shock analysis clears "
                        "principal.")
    if s.coherence_score_0_100 >= 80:
        reasons.append("Thesis pillars are internally coherent; no "
                        "load-bearing contradictions.")
    if s.management_score_0_100 >= 75 and s.pricing_power_score_0_100 >= 60:
        reasons.append("Strong management + real pricing power — "
                        "a team that can execute the thesis, not "
                        "just describe it.")
    if s.has_clear_exit_story:
        reasons.append("Exit story is articulable today — banker's "
                        "pitch writes itself on the strengths.")
    return reasons[:3]


def _flip_the_call(s: ICSignalBundle) -> List[str]:
    signals: List[str] = []
    if s.scorecard_failed_dimensions:
        signals.append(
            f"Closing {s.scorecard_failed_dimensions[0]} from failing "
            "to passing on the partner scorecard.")
    if s.historical_pattern_matches:
        signals.append(
            f"Structural mitigation for {s.historical_pattern_matches[0]} "
            "that changes the risk profile vs the original deal.")
    if s.bear_moic < 1.5:
        signals.append(
            "Bear case above 1.5x via multiple expansion at exit or "
            "accelerated organic growth demonstrated in years 1-2.")
    if s.safety_thin_levers:
        signals.append(
            f"Widened safety margin on {s.safety_thin_levers[0]} — "
            "either price reduction or conservative reunderwrite.")
    if not s.qod_ic_ready:
        signals.append(
            f"Completing diligence on {s.qod_weakest_dimension or 'the weakest dimension'} "
            "to lift IC-ready posture.")
    if s.partner_trap_names:
        signals.append(
            f"Disarming the '{s.partner_trap_names[0]}' thesis trap "
            "with packet-specific evidence, not narrative.")
    if s.connective_high_insight_count >= 1:
        signals.append(
            "Resolving the cross-module stacked-risk pattern "
            "(multiple signals co-occurring).")
    return signals[:3]


def _must_close(s: ICSignalBundle) -> List[str]:
    items: List[str] = []
    if s.face_high_implausibilities >= 1:
        items.append("Resolve the packet implausibilities before any "
                     "IC conversation — these are math-level gates.")
    if not s.qod_ic_ready and s.qod_weakest_dimension:
        items.append(
            f"Close {s.qod_weakest_dimension} diligence to ≥ 80% "
            f"(currently overall {s.qod_overall_pct*100:.0f}%).")
    if s.historical_pattern_matches:
        items.append(
            f"Document explicit mitigations for "
            f"{', '.join(s.historical_pattern_matches[:2])} — "
            "named, not narrative.")
    if s.cycle_double_peak:
        items.append("Reunderwrite entry multiple against cycle "
                     "average; peak × peak is the partner's least-"
                     "forgivable mistake.")
    return items


def _chair_line(s: ICSignalBundle, rec: str) -> str:
    if rec == REC_PASS:
        if s.face_high_implausibilities >= 1:
            return ("\"Math doesn't work on the packet's face; "
                    "pass before we spend another hour.\"")
        if len(s.historical_pattern_matches) >= 2:
            return (f"\"This is {s.historical_pattern_matches[0]} "
                    "with a different logo. Pass.\"")
        if len(s.scorecard_failed_dimensions) >= 2:
            return (f"\"We fail on {', '.join(s.scorecard_failed_dimensions[:2])}. "
                    "Any one is a pass; two is a pass twice. Next.\"")
        return ("\"The bear case loses money and the base case is "
                "load-bearing on aggressive assumptions. I'll write "
                "the rejection letter.\"")
    if rec == REC_INVEST:
        return (f"\"{s.deal_name} is a buy. Scorecard clean, bear "
                "survivable, coherence intact. Move to final IC "
                "with standard closing conditions.\"")
    # DILIGENCE MORE
    return ("\"I'm not ready to recommend — but I don't want to "
            f"pass. Close {s.qod_weakest_dimension or 'the listed gaps'} "
            "in two weeks and bring it back.\"")


def synthesize_ic_decision(s: ICSignalBundle) -> ICDecision:
    score = _compute_score(s)
    rec = _recommendation(s, score)
    reasons = _reasons_for(s)
    flips = _flip_the_call(s)
    must = _must_close(s)
    chair = _chair_line(s, rec)

    note = (f"Synthesized recommendation: **{rec}** (score "
            f"{score}/100). "
            f"{len(reasons)} reasons FOR; {len(flips)} flip-the-call "
            f"signals; {len(must)} items must close before IC.")

    return ICDecision(
        deal_name=s.deal_name,
        recommendation=rec,
        reasons_for=reasons,
        flip_the_call_signals=flips,
        must_close_before_ic=must,
        chair_opening_line=chair,
        score_0_100=score,
        partner_note=note,
    )


def render_ic_decision_markdown(d: ICDecision) -> str:
    lines = [
        f"# {d.deal_name} — IC decision",
        "",
        f"## Recommendation: **{d.recommendation}** "
        f"(score {d.score_0_100}/100)",
        "",
        f"_{d.partner_note}_",
        "",
        "## Chair opening line",
        "",
        d.chair_opening_line,
        "",
    ]
    if d.reasons_for:
        lines.extend(["## Three reasons FOR", ""])
        for i, r in enumerate(d.reasons_for, 1):
            lines.append(f"{i}. {r}")
        lines.append("")
    if d.flip_the_call_signals:
        lines.extend(["## Three signals that would flip the call", ""])
        for i, f in enumerate(d.flip_the_call_signals, 1):
            lines.append(f"{i}. {f}")
        lines.append("")
    if d.must_close_before_ic:
        lines.extend(["## Must-close before IC", ""])
        for item in d.must_close_before_ic:
            lines.append(f"- {item}")
    return "\n".join(lines)
