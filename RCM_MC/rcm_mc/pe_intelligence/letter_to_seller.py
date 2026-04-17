"""Letter to the seller (banker) — partner-voice written response.

Partners write (or have their team write) a letter back to the
banker after a deal goes final. It serves two purposes:

- **On a pass** — constructive framing matters. The banker runs
  5 processes a year and remembers who was dismissive. A good
  pass letter names what the partner liked AND the specific
  reasons the deal didn't clear the internal bar.
- **On a move-forward** — clean, specific, what closing-week
  conditions the partner needs met.

This module takes the IC decision + a few context items and
produces a letter-ready paragraph set. Tone is direct but
respectful — no platitudes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LetterContext:
    deal_name: str
    banker_firm: str = ""
    banker_contact: str = ""
    ic_recommendation: str = "PASS"        # INVEST / PASS / DILIGENCE MORE
    things_we_liked: List[str] = field(default_factory=list)
    reasons_for_pass: List[str] = field(default_factory=list)
    conditions_for_move_forward: List[str] = field(default_factory=list)
    price_we_could_support_m: Optional[float] = None
    asking_price_m: Optional[float] = None
    would_revisit: bool = True


@dataclass
class Letter:
    recipient: str
    subject: str
    salutation: str
    body_paragraphs: List[str]
    signoff: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recipient": self.recipient,
            "subject": self.subject,
            "salutation": self.salutation,
            "body_paragraphs": list(self.body_paragraphs),
            "signoff": self.signoff,
        }


def _salutation(ctx: LetterContext) -> str:
    if ctx.banker_contact:
        return f"Dear {ctx.banker_contact},"
    return "Dear colleagues,"


def _subject(ctx: LetterContext) -> str:
    if ctx.ic_recommendation == "PASS":
        return f"{ctx.deal_name}: passing with thanks"
    if ctx.ic_recommendation == "INVEST":
        return f"{ctx.deal_name}: moving to final IC"
    return f"{ctx.deal_name}: additional diligence"


def _body_pass(ctx: LetterContext) -> List[str]:
    paras: List[str] = []
    # Opening.
    paras.append(
        f"Thank you for the opportunity on {ctx.deal_name}. We've "
        "spent meaningful time with the materials and appreciate "
        "the thoughtful packaging.")

    # Things we liked.
    if ctx.things_we_liked:
        liked = ("We were particularly drawn to: "
                  + "; ".join(ctx.things_we_liked[:3]) + ".")
        paras.append(liked)

    # Reasons for pass.
    if ctx.reasons_for_pass:
        reasons = ("After our full review, we're not in a position "
                    "to move forward. The specific concerns are: "
                    + "; ".join(ctx.reasons_for_pass[:3]) + ".")
        paras.append(reasons)
    else:
        paras.append(
            "After our full review, we're not in a position to move "
            "forward — the deal doesn't line up with our current "
            "portfolio priorities.")

    # Price framing.
    if (ctx.price_we_could_support_m is not None
            and ctx.asking_price_m is not None):
        gap_pct = ((ctx.asking_price_m - ctx.price_we_could_support_m)
                   / max(0.01, ctx.asking_price_m))
        if gap_pct > 0.10:
            paras.append(
                f"For context, our underwriting supports a price "
                f"around ${ctx.price_we_could_support_m:,.0f}M vs the "
                f"${ctx.asking_price_m:,.0f}M ask "
                f"({gap_pct*100:.0f}% gap) — closing that gap would "
                "likely require structure or earn-outs we don't "
                "typically use.")

    # Revisit.
    if ctx.would_revisit:
        paras.append(
            "We'd welcome the chance to revisit if circumstances "
            "change — particularly if the diligence process surfaces "
            "specifics on the items above.")
    paras.append(
        "Please keep us in mind for future processes; we appreciate "
        "the time your team invested.")
    return paras


def _body_invest(ctx: LetterContext) -> List[str]:
    paras: List[str] = []
    paras.append(
        f"We're moving forward on {ctx.deal_name} to final IC. Thank "
        "you for running a tight process.")
    if ctx.conditions_for_move_forward:
        paras.append(
            "Prior to final IC, we'd like to close on the following "
            "items: " + "; ".join(ctx.conditions_for_move_forward[:5])
            + ".")
    paras.append(
        "We will reach out separately on timing for final diligence "
        "sessions and structure discussions. Looking forward to "
        "continuing.")
    return paras


def _body_diligence(ctx: LetterContext) -> List[str]:
    paras: List[str] = []
    paras.append(
        f"We're interested in {ctx.deal_name} but not yet ready to "
        "move to final IC. There are specific items we'd like to "
        "diligence further before we can commit.")
    if ctx.conditions_for_move_forward:
        paras.append(
            "Specifically: "
            + "; ".join(ctx.conditions_for_move_forward[:5]) + ".")
    paras.append(
        "If the team has bandwidth for additional sessions, we'd "
        "like to schedule them in the next 10-14 days. Decision to "
        "follow on the back of that work.")
    return paras


def compose_letter(ctx: LetterContext) -> Letter:
    if ctx.ic_recommendation == "INVEST":
        body = _body_invest(ctx)
    elif ctx.ic_recommendation == "DILIGENCE MORE":
        body = _body_diligence(ctx)
    else:
        body = _body_pass(ctx)

    return Letter(
        recipient=(f"{ctx.banker_contact} / {ctx.banker_firm}"
                    if ctx.banker_firm else ctx.banker_contact),
        subject=_subject(ctx),
        salutation=_salutation(ctx),
        body_paragraphs=body,
        signoff=("Best regards,\nThe deal team"),
    )


def render_letter_markdown(letter: Letter) -> str:
    lines = [
        f"# Subject: {letter.subject}",
        "",
        f"_To: {letter.recipient}_",
        "",
        letter.salutation,
        "",
    ]
    for p in letter.body_paragraphs:
        lines.append(p)
        lines.append("")
    lines.append(letter.signoff)
    return "\n".join(lines)
