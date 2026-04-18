"""Reference check framework — structured CEO/CFO reference calls.

Partners tell associates to "call references" — but generic
reference calls miss the signal. Who you call and what you ask
depend on what you're trying to verify.

Structured by relationship type:

- **Board member (current or past)** — governance fit, how they
  handle bad news, strategic thinking.
- **Ex-boss** — work style, how they behaved when the answer
  wasn't obvious.
- **Ex-direct report** — leadership, culture, retention of top
  talent.
- **Customer / payer counterparty** — negotiation style,
  follow-through on commitments.
- **Banker / auditor** — financial rigor, comfort with
  transparency.
- **Peer CEO** — industry reputation, informal network.

This module takes the role being vetted (CEO / CFO / COO /
CMO / etc.) and returns a list of relationship types with 3-4
specific, partner-voice questions per type.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ReferenceQuestion:
    relationship: str
    question: str
    listen_for: str


@dataclass
class ReferenceGroup:
    relationship: str
    priority: str                          # "must_call" / "should_call"
    questions: List[ReferenceQuestion] = field(default_factory=list)


@dataclass
class ReferencePlan:
    role: str
    must_call_count: int
    should_call_count: int
    groups: List[ReferenceGroup] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "must_call_count": self.must_call_count,
            "should_call_count": self.should_call_count,
            "groups": [
                {"relationship": g.relationship,
                 "priority": g.priority,
                 "questions": [
                     {"relationship": q.relationship,
                      "question": q.question,
                      "listen_for": q.listen_for}
                     for q in g.questions]
                 } for g in self.groups
            ],
            "partner_note": self.partner_note,
        }


def _ceo_questions() -> List[ReferenceGroup]:
    return [
        ReferenceGroup(
            relationship="current_or_past_board_member",
            priority="must_call",
            questions=[
                ReferenceQuestion(
                    "current_or_past_board_member",
                    "Describe a time the company was off plan. How "
                    "did the CEO respond to the board?",
                    "Watch for ownership of the problem vs. excuse-"
                    "making; specific numbers vs. vague reassurance."
                ),
                ReferenceQuestion(
                    "current_or_past_board_member",
                    "When you raised a hard strategic question, did "
                    "the CEO return with analysis or a defensive "
                    "answer?",
                    "Partners want CEOs who treat the board as a "
                    "resource, not as a threat."
                ),
                ReferenceQuestion(
                    "current_or_past_board_member",
                    "Would you back this CEO in a new company?",
                    "Anything short of clear yes is a flag."
                ),
            ],
        ),
        ReferenceGroup(
            relationship="ex_direct_report",
            priority="must_call",
            questions=[
                ReferenceQuestion(
                    "ex_direct_report",
                    "What does this CEO do when a key report "
                    "underperforms?",
                    "Watch for pattern: delay + loyalty vs. fast "
                    "honest action."
                ),
                ReferenceQuestion(
                    "ex_direct_report",
                    "Who are the top 3 people this CEO has hired? "
                    "Where are they now?",
                    "Good CEOs build networks of strong people who "
                    "follow them from deal to deal."
                ),
                ReferenceQuestion(
                    "ex_direct_report",
                    "What's the one thing about this CEO you would "
                    "change?",
                    "Silence or 'nothing' is the answer of someone "
                    "reading a script; specific critique is "
                    "authentic."
                ),
            ],
        ),
        ReferenceGroup(
            relationship="peer_ceo",
            priority="should_call",
            questions=[
                ReferenceQuestion(
                    "peer_ceo",
                    "How does this CEO handle competitive dynamics "
                    "— sharp elbows, or clean?",
                    "Reputation travels; a CEO known for dirty plays "
                    "will drag the portfolio company's reputation."
                ),
                ReferenceQuestion(
                    "peer_ceo",
                    "Have you personally co-invested or would you?",
                    "The highest-trust signal in the industry."
                ),
            ],
        ),
        ReferenceGroup(
            relationship="customer_or_payer",
            priority="should_call",
            questions=[
                ReferenceQuestion(
                    "customer_or_payer",
                    "When this organization made a commitment to "
                    "you, did they follow through?",
                    "Execution reputation with counterparties."
                ),
                ReferenceQuestion(
                    "customer_or_payer",
                    "How do they negotiate when there's a problem "
                    "with service delivery?",
                    "Reveals whether the organization is relationship-"
                    "first or transaction-first."
                ),
            ],
        ),
    ]


def _cfo_questions() -> List[ReferenceGroup]:
    return [
        ReferenceGroup(
            relationship="auditor",
            priority="must_call",
            questions=[
                ReferenceQuestion(
                    "auditor",
                    "Describe an accounting policy choice this CFO "
                    "made. What was the rationale?",
                    "Listen for defensible reasoning vs. aggressive "
                    "framing. Auditors see the seam."
                ),
                ReferenceQuestion(
                    "auditor",
                    "How does this CFO respond when you raise an "
                    "issue?",
                    "Professional openness vs. defensiveness is a "
                    "controls-culture tell."
                ),
                ReferenceQuestion(
                    "auditor",
                    "Have you ever had to escalate above this CFO?",
                    "One escalation is a flag; multiple is a "
                    "no-hire."
                ),
            ],
        ),
        ReferenceGroup(
            relationship="bank_syndicate_lead",
            priority="must_call",
            questions=[
                ReferenceQuestion(
                    "bank_syndicate_lead",
                    "Did this CFO meet forecast commitments during "
                    "covenant periods?",
                    "Banks see the real trend before board does."
                ),
                ReferenceQuestion(
                    "bank_syndicate_lead",
                    "Was the monthly / quarterly package accurate "
                    "and on time?",
                    "CFO discipline reveals in delivery cadence."
                ),
            ],
        ),
        ReferenceGroup(
            relationship="ex_direct_report",
            priority="should_call",
            questions=[
                ReferenceQuestion(
                    "ex_direct_report",
                    "Describe a time the CFO changed their mind on "
                    "a number based on analyst work.",
                    "Tests whether the CFO owns the analysis or "
                    "merely signs off."
                ),
            ],
        ),
        ReferenceGroup(
            relationship="ceo_or_cfo_peer",
            priority="should_call",
            questions=[
                ReferenceQuestion(
                    "ceo_or_cfo_peer",
                    "When you presented to the board together, who "
                    "led?",
                    "Strong CFOs are clearly partners to the CEO; "
                    "weak ones are passive."
                ),
            ],
        ),
    ]


def _default_questions(role: str) -> List[ReferenceGroup]:
    """For other roles (COO, CMO, etc.), use ex-boss + ex-direct report."""
    return [
        ReferenceGroup(
            relationship="ex_boss",
            priority="must_call",
            questions=[
                ReferenceQuestion(
                    "ex_boss",
                    f"What's the single biggest result this "
                    f"{role.upper()} drove in their prior role?",
                    "Specific number + timeframe. Vague answers are "
                    "a flag."
                ),
                ReferenceQuestion(
                    "ex_boss",
                    "Would you rehire this person?",
                    "Anything less than clear yes is a flag."
                ),
            ],
        ),
        ReferenceGroup(
            relationship="ex_direct_report",
            priority="must_call",
            questions=[
                ReferenceQuestion(
                    "ex_direct_report",
                    f"Describe how this {role.upper()} handled a "
                    "time when you disagreed with them.",
                    "Open-mindedness vs. authority-dependence."
                ),
            ],
        ),
    ]


def build_reference_plan(role: str) -> ReferencePlan:
    role_lower = role.lower()
    if role_lower == "ceo":
        groups = _ceo_questions()
    elif role_lower == "cfo":
        groups = _cfo_questions()
    else:
        groups = _default_questions(role_lower)

    must = sum(1 for g in groups if g.priority == "must_call")
    should = sum(1 for g in groups if g.priority == "should_call")

    if must >= 3:
        note = (f"{role.upper()} reference plan: {must} must-call "
                f"groups + {should} should-call. Complete the "
                "must-calls before IC; should-calls before final "
                "closing conditions.")
    elif must >= 2:
        note = (f"{role.upper()} plan: {must} must-call + {should} "
                "should-call. Minimum 2 calls per must-call group; "
                "at least one should-call category.")
    else:
        note = (f"{role.upper()} plan generated. Ensure at least 2 "
                "references per relationship type.")

    return ReferencePlan(
        role=role,
        must_call_count=must,
        should_call_count=should,
        groups=groups,
        partner_note=note,
    )


def render_reference_plan_markdown(p: ReferencePlan) -> str:
    lines = [
        f"# {p.role.upper()} reference check plan",
        "",
        f"_{p.partner_note}_",
        "",
        f"- Must-call groups: {p.must_call_count}",
        f"- Should-call groups: {p.should_call_count}",
        "",
    ]
    for g in p.groups:
        lines.append(f"## {g.relationship} ({g.priority})")
        lines.append("")
        for i, q in enumerate(g.questions, 1):
            lines.append(f"{i}. **{q.question}**")
            lines.append(f"   - *Listen for:* {q.listen_for}")
        lines.append("")
    return "\n".join(lines)
