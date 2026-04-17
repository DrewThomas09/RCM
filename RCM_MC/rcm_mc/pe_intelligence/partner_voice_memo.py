"""Partner-voice IC memo — recommendation-first IC-ready output.

This is NOT a replacement for the existing `ic_memo` renderer.
It is a partner-voice overlay that ingests a packet-like context
+ a PartnerReview and produces:

1. **Recommendation** up top: INVEST / DILIGENCE MORE / PASS.
2. **One-paragraph partner summary** — direct, numbers-first.
3. **Three things that would change my mind** — honest pre-mortem.
4. **Base case | Bull case | Bear case** in three lines.
5. **Deal-killers checklist** — open red flags that must close.

Why a new module: the existing ic_memo is a structured template.
Partners also need a voice-y, one-page "if I had 60 seconds with
the chairman" version. That is this.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Recommendation codes.
REC_INVEST = "INVEST"
REC_DILIGENCE_MORE = "DILIGENCE MORE"
REC_PASS = "PASS"


@dataclass
class PartnerVoiceInputs:
    deal_name: str
    subsector: str = "specialty_practice"
    ebitda_m: float = 0.0
    revenue_m: float = 0.0
    entry_multiple: float = 11.0
    target_moic: float = 2.5
    target_irr: float = 0.20
    # Review-derived inputs:
    red_flag_count: int = 0
    red_flag_high_count: int = 0
    reasonableness_out_of_band_count: int = 0
    valuation_concerns: int = 0
    bear_book_hits: int = 0
    heuristic_hits: int = 0
    # Thesis strength signals:
    has_defensible_organic_growth: bool = False
    has_clear_exit_path: bool = True
    pricing_power_score_0_100: int = 60
    management_score_0_100: int = 70
    # Archetype / historical pattern hits:
    historical_failure_matches: int = 0
    # Cross-module signals:
    cycle_phase: str = "mid_expansion"    # from cycle_timing
    regime: str = "balanced"              # from regime_classifier


@dataclass
class PartnerVoiceMemo:
    deal_name: str
    recommendation: str
    summary: str
    bull_case: str
    base_case: str
    bear_case: str
    change_my_mind: List[str] = field(default_factory=list)
    deal_killers_open: List[str] = field(default_factory=list)
    score_0_100: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "recommendation": self.recommendation,
            "summary": self.summary,
            "bull_case": self.bull_case,
            "base_case": self.base_case,
            "bear_case": self.bear_case,
            "change_my_mind": list(self.change_my_mind),
            "deal_killers_open": list(self.deal_killers_open),
            "score_0_100": self.score_0_100,
            "partner_note": self.partner_note,
        }


def _compute_score(i: PartnerVoiceInputs) -> int:
    """Weighted 0-100 score — higher = more INVEST-leaning."""
    s = 50
    # Red flags drag hard.
    s -= 12 * i.red_flag_high_count
    s -= 3 * (i.red_flag_count - i.red_flag_high_count)
    # Reasonableness + valuation.
    s -= 3 * i.reasonableness_out_of_band_count
    s -= 4 * i.valuation_concerns
    # Bear book + historical failures — partner-heavy weighting.
    s -= 5 * i.bear_book_hits
    s -= 8 * i.historical_failure_matches
    # Thesis strength.
    if i.has_defensible_organic_growth:
        s += 10
    if i.has_clear_exit_path:
        s += 5
    s += int(round((i.pricing_power_score_0_100 - 50) * 0.20))
    s += int(round((i.management_score_0_100 - 50) * 0.20))
    # Regime / cycle tilt.
    if i.cycle_phase == "peak":
        s -= 4
    elif i.cycle_phase == "contraction":
        s -= 6
    elif i.cycle_phase == "early_expansion":
        s += 4
    return max(0, min(100, s))


def _recommendation(score: int, hv_hits: int, killer_open: int) -> str:
    # Hard rules beat score:
    if killer_open >= 2 or hv_hits >= 2:
        return REC_PASS
    if score >= 70 and killer_open == 0:
        return REC_INVEST
    if score <= 35:
        return REC_PASS
    return REC_DILIGENCE_MORE


def _change_my_mind(i: PartnerVoiceInputs) -> List[str]:
    items: List[str] = []
    if i.red_flag_high_count >= 1:
        items.append("Clear resolution path on the high-severity red "
                     "flag(s) — with evidence, not promises.")
    if not i.has_defensible_organic_growth:
        items.append("Evidence of defensible organic growth "
                     "(volume > price) over the prior 2 years.")
    if i.reasonableness_out_of_band_count >= 2:
        items.append("Tighter model assumptions that bring "
                     "out-of-band cells back into peer-median ranges.")
    if i.historical_failure_matches >= 1:
        items.append(f"Explicit mitigation for the "
                      f"{i.historical_failure_matches} historical-"
                      "pattern match(es) — this deal must not look "
                      "like the last one.")
    if i.pricing_power_score_0_100 < 50:
        items.append("Demonstrated pricing power — commercial share "
                     "shift, payer contract wins, or CoE designation.")
    if i.management_score_0_100 < 60:
        items.append("Management assessment improvements — retention "
                     "commitments, key hires, or succession plan.")
    if i.bear_book_hits >= 1:
        items.append("Bear-pattern mitigation — why this is not the "
                     "same outcome.")
    # Always cap at 3; partner asks for three.
    return items[:3]


def _deal_killers_open(i: PartnerVoiceInputs) -> List[str]:
    items: List[str] = []
    if i.red_flag_high_count >= 2:
        items.append(f"{i.red_flag_high_count} high-severity red "
                     "flags outstanding.")
    if i.historical_failure_matches >= 2:
        items.append(f"{i.historical_failure_matches} named historical "
                     "failure patterns match this deal.")
    if i.valuation_concerns >= 3:
        items.append("Multiple valuation concerns — price is not "
                     "supportable without leverage assumption change.")
    if i.cycle_phase == "peak" and i.entry_multiple >= 13:
        items.append("Peak-cycle entry at high multiple — MOIC "
                     "arithmetic depends on multiple expansion that is "
                     "unlikely to materialize.")
    return items


def _bull_case(i: PartnerVoiceInputs) -> str:
    return (
        f"Thesis plays out: organic growth ~{i.target_irr*100-3:.0f}%, "
        f"exit multiple flat at {i.entry_multiple:.1f}x → MOIC "
        f"{i.target_moic + 0.4:.1f}x, IRR "
        f"{i.target_irr*100 + 3:.0f}%."
    )


def _base_case(i: PartnerVoiceInputs) -> str:
    return (
        f"Plan-case growth, multiple compression of ~1x, synergies at "
        f"80% realization → MOIC {i.target_moic:.1f}x, IRR "
        f"{i.target_irr*100:.0f}%."
    )


def _bear_case(i: PartnerVoiceInputs) -> str:
    shock = 0.20 + 0.05 * i.red_flag_high_count
    return (
        f"Recession + {shock*100:.0f}% EBITDA shock, multiple "
        f"compression of 2x → MOIC "
        f"{max(0.0, i.target_moic - 1.0):.1f}x, IRR below cost of "
        "capital."
    )


def _summary(i: PartnerVoiceInputs, rec: str, score: int) -> str:
    if rec == REC_INVEST:
        return (
            f"{i.deal_name} is a ${i.ebitda_m:,.0f}M EBITDA "
            f"{i.subsector} asset at {i.entry_multiple:.1f}x. Score "
            f"{score}/100. Thesis defensible, exit path clear. "
            "Move to final IC with standard closing conditions."
        )
    if rec == REC_PASS:
        return (
            f"{i.deal_name} ({i.subsector}, ${i.ebitda_m:,.0f}M "
            f"EBITDA, {i.entry_multiple:.1f}x) scores {score}/100. "
            "Red flags / pattern-matches / valuation stretch make this "
            "a pass at current price. Re-evaluate on structural "
            "improvement or 10%+ price adjustment."
        )
    return (
        f"{i.deal_name} scores {score}/100 — insufficient conviction "
        "at current information set. Drive diligence to close the "
        "three items listed. Decision within 2 weeks."
    )


def build_partner_memo(inputs: PartnerVoiceInputs) -> PartnerVoiceMemo:
    score = _compute_score(inputs)
    killers = _deal_killers_open(inputs)
    rec = _recommendation(score, inputs.historical_failure_matches,
                           len(killers))
    summary = _summary(inputs, rec, score)
    cmm = _change_my_mind(inputs)

    note = (f"Recommendation **{rec}** at score {score}/100. "
            f"{len(killers)} open deal-killer(s); "
            f"{inputs.historical_failure_matches} historical match(es).")

    return PartnerVoiceMemo(
        deal_name=inputs.deal_name,
        recommendation=rec,
        summary=summary,
        bull_case=_bull_case(inputs),
        base_case=_base_case(inputs),
        bear_case=_bear_case(inputs),
        change_my_mind=cmm,
        deal_killers_open=killers,
        score_0_100=score,
        partner_note=note,
    )


def render_partner_memo_markdown(m: PartnerVoiceMemo) -> str:
    lines = [
        f"# {m.deal_name} — Partner IC Memo",
        "",
        f"## Recommendation: **{m.recommendation}** "
        f"(score {m.score_0_100}/100)",
        "",
        m.summary,
        "",
        "## Case views",
        "",
        f"- **Bull:** {m.bull_case}",
        f"- **Base:** {m.base_case}",
        f"- **Bear:** {m.bear_case}",
    ]
    if m.change_my_mind:
        lines.extend(["", "## Three things that would change my mind",
                       ""])
        for i, c in enumerate(m.change_my_mind, 1):
            lines.append(f"{i}. {c}")
    if m.deal_killers_open:
        lines.extend(["", "## Open deal-killers", ""])
        for k in m.deal_killers_open:
            lines.append(f"- {k}")
    return "\n".join(lines)
