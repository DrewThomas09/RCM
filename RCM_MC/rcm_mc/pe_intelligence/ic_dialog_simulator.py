"""IC dialog simulator — voices challenge each other across rounds.

Partner statement: "When IC works, voices challenge
each other. The skeptic raises a concern; the
operating partner says 'we own that — here's how';
the LP-facing voice asks 'how does this read in the
quarterly?'; the numbers-MD says 'the math doesn't
support either side'; the chair synthesizes. A
monolithic memo doesn't capture this. The dialog
does. The dialog also surfaces: which concerns the
team has actually answered, and which ones nobody on
the team has a real response to."

Distinct from:
- `partner_voice_variants` — produces 5 voice
  paragraphs as separate monoliths.
- `ic_decision_synthesizer` — single recommendation
  + 3 reasons + 3 flip signals.
- `pre_ic_chair_brief` — chair's 4-bullet pre-IC note.

This module simulates a 3-round dialog. Each round,
a voice responds to the previous round's points.
By round 3 the conversation has surfaced where the
team has answers and where it doesn't.

### 3 rounds × 5 voices × challenge-response shape

**Round 1** — opening: each voice gives their first
read on the deal (1 bullet each).

**Round 2** — challenge: each voice picks one prior-
round point and either reinforces or pushes back.

**Round 3** — chair synthesis: chair reconciles the
conversation; identifies (a) consensus points, (b)
unresolved tensions, (c) IC vote-blocking
disagreements.

### Output

3-round transcript + chair synthesis with three
buckets (consensus / unresolved / vote-blocking).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


VOICE_SKEPTIC = "skeptic"
VOICE_OPTIMIST = "optimist"
VOICE_MD_NUMBERS = "md_numbers"
VOICE_OPERATING_PARTNER = "operating_partner"
VOICE_LP_FACING = "lp_facing"
VOICE_CHAIR = "chair"


@dataclass
class ICDialogInputs:
    deal_name: str = "Deal"
    subsector: str = "specialty_practice"
    recurring_ebitda_m: float = 50.0
    target_moic: float = 2.5
    entry_multiple: float = 11.0
    exit_multiple: float = 12.0
    top_risks: List[str] = field(default_factory=list)
    operator_owns_named: List[str] = field(
        default_factory=list)
    qofe_clean: bool = True
    payer_mix_commercial_pct: float = 0.45
    growth_rate: float = 0.08
    leverage_turns: float = 4.5
    management_track_record_strong: bool = True
    historical_failure_match_top: Optional[str] = None


@dataclass
class DialogTurn:
    round_num: int
    voice: str
    point: str
    reacts_to_voice: Optional[str] = None
    reaction_type: str = ""  # "open" / "reinforce" / "pushback"


@dataclass
class ICDialogReport:
    transcript: List[DialogTurn] = field(
        default_factory=list)
    chair_consensus: List[str] = field(
        default_factory=list)
    chair_unresolved: List[str] = field(
        default_factory=list)
    chair_vote_blocking: List[str] = field(
        default_factory=list)
    chair_recommendation: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcript": [
                {"round_num": t.round_num,
                 "voice": t.voice,
                 "point": t.point,
                 "reacts_to_voice": t.reacts_to_voice,
                 "reaction_type": t.reaction_type}
                for t in self.transcript
            ],
            "chair_consensus": self.chair_consensus,
            "chair_unresolved": self.chair_unresolved,
            "chair_vote_blocking":
                self.chair_vote_blocking,
            "chair_recommendation":
                self.chair_recommendation,
            "partner_note": self.partner_note,
        }


def _round1(inputs: ICDialogInputs) -> List[DialogTurn]:
    """Opening round — each voice's first read."""
    turns: List[DialogTurn] = []
    sk = (
        "I'd lead with what breaks this. " +
        (f"The historical match is {inputs.historical_failure_match_top}. "
         if inputs.historical_failure_match_top
         else "") +
        f"Target {inputs.target_moic:.1f}x at "
        f"{inputs.entry_multiple:.1f}× entry — what's "
        "the specific edge?"
    )
    turns.append(DialogTurn(
        round_num=1, voice=VOICE_SKEPTIC,
        point=sk, reaction_type="open"))

    op = (
        f"Growth at {inputs.growth_rate:.0%} on a "
        f"${inputs.recurring_ebitda_m:.0f}M base is "
        "above-market. " +
        ("QofE is clean. " if inputs.qofe_clean else
         "QofE has open items. ") +
        "Multiple expansion pathway is real if we "
        "execute the bolt-ons."
    )
    turns.append(DialogTurn(
        round_num=1, voice=VOICE_OPTIMIST,
        point=op, reaction_type="open"))

    md = (
        f"Recurring EBITDA ${inputs.recurring_ebitda_m:.0f}M × "
        f"exit {inputs.exit_multiple:.1f}× / entry "
        f"{inputs.entry_multiple:.1f}× = "
        f"{inputs.exit_multiple/inputs.entry_multiple:.2f}x "
        "from multiple alone before EBITDA growth or "
        "leverage paydown. The math frame is a "
        "checking-account problem: where does the "
        "EBITDA growth come from?"
    )
    turns.append(DialogTurn(
        round_num=1, voice=VOICE_MD_NUMBERS,
        point=md, reaction_type="open"))

    op_part = (
        "Day-1 inventory: " +
        (", ".join(inputs.operator_owns_named) +
         ". " if inputs.operator_owns_named else
         "no specific 100-day commits named yet — that "
         "by itself is a flag. ") +
        ("Management track record is strong — they've "
         "delivered before. " if inputs.management_track_record_strong
         else "Management is unproven on this scale. ")
    )
    turns.append(DialogTurn(
        round_num=1, voice=VOICE_OPERATING_PARTNER,
        point=op_part, reaction_type="open"))

    lp = (
        f"LP read: {inputs.subsector} platform at "
        f"{inputs.entry_multiple:.1f}× — comparable to "
        "vintage peer deals. If this exits in 5 years "
        f"at {inputs.target_moic:.1f}x, the LP letter "
        "writes itself. If it doesn't — and "
        f"{inputs.leverage_turns:.1f}× leverage means "
        "any miss bites cash flow — the letter is "
        "harder."
    )
    turns.append(DialogTurn(
        round_num=1, voice=VOICE_LP_FACING,
        point=lp, reaction_type="open"))

    return turns


def _round2(
    inputs: ICDialogInputs,
    round1: List[DialogTurn],
) -> List[DialogTurn]:
    """Challenge round — voices push back on each other."""
    turns: List[DialogTurn] = []

    # Skeptic challenges optimist
    sk_target = next(
        (t for t in round1 if t.voice == VOICE_OPTIMIST),
        None)
    sk_msg = (
        "Optimist says growth and multiple expansion. "
        "Below me a clean QofE doesn't get you to "
        f"{inputs.target_moic:.1f}x. Where's the "
        "specific evidence growth holds AND multiple "
        "expands? Two assumptions, both have to land."
    )
    turns.append(DialogTurn(
        round_num=2, voice=VOICE_SKEPTIC,
        point=sk_msg,
        reacts_to_voice=VOICE_OPTIMIST,
        reaction_type="pushback"))

    # Operating partner addresses skeptic
    op_msg = (
        "On the skeptic's edge question: the edge is "
        "operator execution. " +
        ("We have the integration playbook from prior "
         "platforms. "
         if inputs.operator_owns_named
         else "We need to name an operating partner — "
              "without one, the skeptic is right.")
    )
    turns.append(DialogTurn(
        round_num=2, voice=VOICE_OPERATING_PARTNER,
        point=op_msg,
        reacts_to_voice=VOICE_SKEPTIC,
        reaction_type="reinforce" if not
        inputs.operator_owns_named else "pushback"))

    # MD numbers challenges optimist's growth claim
    md_msg = (
        f"Optimist's {inputs.growth_rate:.0%} growth "
        f"on ${inputs.recurring_ebitda_m:.0f}M = "
        f"${inputs.recurring_ebitda_m * inputs.growth_rate:.1f}M "
        "of new EBITDA per year. Over 5 years and at "
        f"{inputs.exit_multiple:.0f}× = "
        f"${inputs.recurring_ebitda_m * inputs.growth_rate * 5 * inputs.exit_multiple:.0f}M "
        "of value. That's the half of MOIC that comes "
        "from EBITDA. The other half is multiple expansion "
        "and de-leverage. The math has to balance."
    )
    turns.append(DialogTurn(
        round_num=2, voice=VOICE_MD_NUMBERS,
        point=md_msg,
        reacts_to_voice=VOICE_OPTIMIST,
        reaction_type="reinforce"))

    # LP voice challenges leverage
    lp_msg = (
        f"On {inputs.leverage_turns:.1f}× leverage: "
        "LPs read covenant headroom in the quarterly. "
        "If we get a covenant amendment in year 2, "
        "that's a footnote. Two amendments, that's a "
        "narrative. Three is a fund-level concern."
    )
    turns.append(DialogTurn(
        round_num=2, voice=VOICE_LP_FACING,
        point=lp_msg,
        reacts_to_voice=VOICE_OPTIMIST,
        reaction_type="pushback"))

    # Optimist responds to all challenges
    op2_msg = (
        "Acknowledging the challenges. The thesis "
        "stands on three legs: organic growth, bolt-on "
        "M&A, and multiple expansion. " +
        ("Even if multiple stays flat, the EBITDA "
         "math gets us to 2.0x. "
         if inputs.target_moic > 2.0 else "") +
        "I am NOT defending top-quartile execution as "
        "base case — I am defending that it is "
        "plausible."
    )
    turns.append(DialogTurn(
        round_num=2, voice=VOICE_OPTIMIST,
        point=op2_msg,
        reacts_to_voice=VOICE_SKEPTIC,
        reaction_type="pushback"))

    return turns


def _round3_chair(
    inputs: ICDialogInputs,
    round1: List[DialogTurn],
    round2: List[DialogTurn],
) -> Dict[str, Any]:
    """Chair synthesis."""
    consensus: List[str] = []
    unresolved: List[str] = []
    blocking: List[str] = []

    # Consensus heuristics
    if inputs.qofe_clean:
        consensus.append(
            "QofE is clean — math base is solid.")
    if inputs.management_track_record_strong:
        consensus.append(
            "Management has delivered before — execution "
            "risk reduced.")
    if inputs.payer_mix_commercial_pct >= 0.40:
        consensus.append(
            "Payer mix is commercial-skewed — protected "
            "from FFS pressure.")

    # Unresolved heuristics
    if inputs.target_moic >= 3.0:
        unresolved.append(
            f"{inputs.target_moic:.1f}x target is "
            "top-quartile execution — burden of proof "
            "is on us; the team did NOT close that gap.")
    if not inputs.operator_owns_named:
        unresolved.append(
            "Operating partner has not named specific "
            "100-day commitments — execution edge is "
            "still aspirational.")
    if inputs.growth_rate < 0.05:
        unresolved.append(
            f"Growth assumption "
            f"{inputs.growth_rate:.0%} is sub-platform; "
            "thesis depends on multiple expansion alone.")

    # Vote-blocking heuristics
    if not inputs.qofe_clean:
        blocking.append(
            "QofE not clean — must close before vote.")
    if inputs.leverage_turns > 6.0:
        blocking.append(
            f"{inputs.leverage_turns:.1f}× leverage is "
            "above firm comfort — covenant package "
            "needs banker re-quote.")
    if inputs.historical_failure_match_top:
        blocking.append(
            f"Strong historical match to "
            f"{inputs.historical_failure_match_top} — "
            "address that pattern explicitly before vote.")
    if (inputs.payer_mix_commercial_pct < 0.30 and
            inputs.exit_multiple > 12.0):
        blocking.append(
            "Exit multiple > 12× with < 30% commercial "
            "is a structural mismatch — re-underwrite "
            "exit case.")

    if blocking:
        rec = "DILIGENCE MORE — vote-blocking items"
    elif unresolved:
        rec = (
            "DILIGENCE MORE — unresolved tensions need "
            "answers, not vote-blocking")
    else:
        rec = "INVEST — consensus dialog supports vote"

    chair_summary = (
        f"Chair: {len(consensus)} consensus, "
        f"{len(unresolved)} unresolved, "
        f"{len(blocking)} vote-blocking. {rec}."
    )

    return {
        "consensus": consensus,
        "unresolved": unresolved,
        "blocking": blocking,
        "recommendation": rec,
        "chair_summary": chair_summary,
    }


def simulate_ic_dialog(
    inputs: ICDialogInputs,
) -> ICDialogReport:
    r1 = _round1(inputs)
    r2 = _round2(inputs, r1)
    chair = _round3_chair(inputs, r1, r2)

    transcript = r1 + r2
    transcript.append(DialogTurn(
        round_num=3,
        voice=VOICE_CHAIR,
        point=chair["chair_summary"],
        reaction_type="synthesis",
    ))

    # Partner note
    if chair["blocking"]:
        note = (
            f"IC dialog surfaced "
            f"{len(chair['blocking'])} vote-blocking "
            "item(s). Do not put on the agenda until "
            "addressed."
        )
    elif len(chair["unresolved"]) >= 2:
        note = (
            f"IC dialog left "
            f"{len(chair['unresolved'])} significant "
            "tensions unresolved. Re-prep with "
            "specific responses before voting."
        )
    elif chair["recommendation"].startswith("INVEST"):
        note = (
            "IC dialog resolves cleanly to invest. "
            "All voices' concerns addressed by another "
            "voice; chair can frame the vote."
        )
    else:
        note = (
            "IC dialog inconclusive — gather one more "
            "round of evidence before re-staging."
        )

    return ICDialogReport(
        transcript=transcript,
        chair_consensus=chair["consensus"],
        chair_unresolved=chair["unresolved"],
        chair_vote_blocking=chair["blocking"],
        chair_recommendation=chair["recommendation"],
        partner_note=note,
    )


def render_ic_dialog_markdown(
    r: ICDialogReport,
) -> str:
    lines = [
        "# IC dialog simulation",
        "",
        f"_{r.partner_note}_",
        "",
        f"**Chair recommendation:** {r.chair_recommendation}",
        "",
    ]
    cur_round = 0
    for t in r.transcript:
        if t.round_num != cur_round:
            cur_round = t.round_num
            lines.append(f"## Round {cur_round}")
            lines.append("")
        prefix = (
            f"→ ({t.reacts_to_voice})"
            if t.reacts_to_voice else ""
        )
        lines.append(
            f"- **{t.voice}** {prefix} ({t.reaction_type}): "
            f"{t.point}"
        )
    lines.append("")
    lines.append("## Chair synthesis")
    lines.append("")
    lines.append("**Consensus:**")
    for c in r.chair_consensus:
        lines.append(f"- {c}")
    lines.append("")
    lines.append("**Unresolved:**")
    for u in r.chair_unresolved:
        lines.append(f"- {u}")
    lines.append("")
    lines.append("**Vote-blocking:**")
    for b in r.chair_vote_blocking:
        lines.append(f"- {b}")
    return "\n".join(lines)
