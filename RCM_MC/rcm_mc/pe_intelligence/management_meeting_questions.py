"""Management-meeting questions — partner's question set for MM.

Partner statement: "In the Monday management meeting, I
don't ask 'tell me about the business.' I ask the CEO the
three questions where their answer reveals whether the
thesis survives. Different chair for CFO. Different for
COO."

Distinct from:

- `reference_check_framework` — former-peer reference calls
  (past-looking).
- `diligence_checklist_live` — what's answered-by-packet
  vs. needs-MI (framework-level).

This module generates a **role-specific question set** for
an actual management meeting, conditioned on:

- The **thesis** (from thesis_implications_chain) — which
  downstream links are still open?
- **Pattern matches** — which traps / failure patterns
  should we be probing for?
- **Packet gaps** — what's missing from the packet that
  management can answer directly?

Questions carry:
- The question itself (partner voice — direct, no hedging).
- The **listen-for** signal — what reveals good/bad.
- A **follow-up** — the gotcha if the initial answer is
  non-specific.
- A **link** back to the packet gap or thesis concern it
  closes.

Roles covered:
- **CEO** — strategy, defensibility, hiring signal.
- **CFO** — forecast discipline, NWC, covenant posture.
- **COO** — executability, integration, ops cadence.
- **CMO / CMIO** — clinical quality, CMI, regulatory
  audit exposure.
- **CCO / Head of Sales** — pipeline, payer posture.
- **CIO / IT** — data, EHR, cyber.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


ROLES = ("ceo", "cfo", "coo", "cmo", "cco", "cio")


@dataclass
class MMQuestion:
    question: str
    listen_for: str
    follow_up: str = ""
    closes_gap: str = ""       # maps to packet gap / thesis concern
    priority: str = "should_ask"  # "must_ask" / "should_ask"


@dataclass
class MMQuestionSet:
    role: str
    questions: List[MMQuestion] = field(default_factory=list)


@dataclass
class MMInputs:
    thesis: str = ""                       # e.g., "denial_reduction"
    thesis_not_addressed: List[str] = field(default_factory=list)
    thesis_contradicted: List[str] = field(default_factory=list)
    pattern_matches: List[str] = field(default_factory=list)
    packet_gaps: List[str] = field(default_factory=list)
    subsector: str = "healthcare_services"
    roles: List[str] = field(
        default_factory=lambda: ["ceo", "cfo", "coo"]
    )


@dataclass
class MMQuestionPlan:
    role_sets: List[MMQuestionSet] = field(default_factory=list)
    total_questions: int = 0
    must_ask_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_sets": [
                {"role": rs.role,
                 "questions": [
                     {"question": q.question,
                      "listen_for": q.listen_for,
                      "follow_up": q.follow_up,
                      "closes_gap": q.closes_gap,
                      "priority": q.priority}
                     for q in rs.questions
                 ]}
                for rs in self.role_sets
            ],
            "total_questions": self.total_questions,
            "must_ask_count": self.must_ask_count,
            "partner_note": self.partner_note,
        }


# ── Base role questions (always relevant) ──────────────

def _ceo_base() -> List[MMQuestion]:
    return [
        MMQuestion(
            question=("If I asked you to cut a division "
                      "tomorrow, which one would it be and "
                      "why?"),
            listen_for=("CEOs with real strategic clarity "
                        "answer in one sentence. Vague or "
                        "defensive = strategic drift."),
            follow_up=("And if you had to grow one — same "
                       "question."),
            priority="must_ask",
        ),
        MMQuestion(
            question=("Who are your top 3 hires since you "
                      "took the role? Where are they now?"),
            listen_for=("Strong CEOs keep stars. If top "
                        "hires are gone, the team they built "
                        "is gone."),
            priority="must_ask",
        ),
        MMQuestion(
            question=("What's the one number on the board "
                      "dashboard you check first each week?"),
            listen_for=("Reveals the CEO's true operating "
                        "model. Cash, bookings, or NPS says "
                        "something different."),
            priority="should_ask",
        ),
    ]


def _cfo_base() -> List[MMQuestion]:
    return [
        MMQuestion(
            question=("Last 8 quarters: how many times did "
                      "you hit or beat forecast?"),
            listen_for=("Track record. < 5 of 8 is a flag; < 3 "
                        "is an automatic haircut of 15-20% "
                        "on forward plan."),
            priority="must_ask",
        ),
        MMQuestion(
            question=("When was your last covenant measurement "
                      "date, and how much headroom did you have?"),
            listen_for=("Specific numbers. 'Comfortable' is "
                        "not an answer."),
            follow_up=("If EBITDA came in 10% below plan this "
                       "quarter, are you out of compliance?"),
            priority="must_ask",
        ),
        MMQuestion(
            question=("Walk me through the NWC trend line "
                      "over the past 8 quarters."),
            listen_for=("Working capital is where management "
                        "teams bury pressure. Rising DSO + "
                        "rising inventory with flat revenue "
                        "= real problem."),
            priority="should_ask",
        ),
    ]


def _coo_base() -> List[MMQuestion]:
    return [
        MMQuestion(
            question=("Of your top 10 operators, how many "
                      "own a P&L line on the financials?"),
            listen_for=("High number = distributed "
                        "accountability. Low number = the "
                        "plan lives only in the CEO's head."),
            priority="must_ask",
        ),
        MMQuestion(
            question=("What's the one KPI you review daily?"),
            listen_for=("Daily = real operating cadence. "
                        "'We have dashboards' is not an "
                        "answer."),
            priority="should_ask",
        ),
        MMQuestion(
            question=("Which division has the best operating "
                      "cadence? Which has the worst? Why?"),
            listen_for=("Willingness to name weak points. "
                        "COOs who can't name a weak unit are "
                        "political, not operational."),
            priority="should_ask",
        ),
    ]


def _cmo_base() -> List[MMQuestion]:
    return [
        MMQuestion(
            question=("What's your CMI trend line over the "
                      "past 3 years, and what drove the "
                      "change?"),
            listen_for=("Good CMOs know it cold; their "
                        "answer references CDI programs or "
                        "service-line mix shifts."),
            priority="must_ask",
        ),
        MMQuestion(
            question=("Any open RAC or OIG audits, and what "
                      "did the last closed audit find?"),
            listen_for=("Open audits are a walk-right "
                        "question; closed audit findings "
                        "signal future risk."),
            priority="must_ask",
        ),
        MMQuestion(
            question=("CMS star rating trajectory — what "
                      "are you doing to hold or improve?"),
            listen_for=("Specific programs. 'We're focused "
                        "on it' = no program."),
            priority="should_ask",
        ),
    ]


def _cco_base() -> List[MMQuestion]:
    return [
        MMQuestion(
            question=("What's the churn rate on your top 10 "
                      "customers or payers over 3 years?"),
            listen_for=("Concrete number; > 20% churn on top "
                        "10 = commercial health is weaker "
                        "than the P&L suggests."),
            priority="must_ask",
        ),
        MMQuestion(
            question=("Which of your top 5 payer contracts "
                      "are up for renewal in the next 18 "
                      "months?"),
            listen_for=("Specific dates. If renewal timing "
                        "slips, rate exposure rises."),
            priority="must_ask",
        ),
        MMQuestion(
            question=("When you lose a customer or payer, "
                      "what's the most common reason?"),
            listen_for=("Price is a common answer; service "
                        "is a worse answer; 'we don't lose' "
                        "is a fabrication."),
            priority="should_ask",
        ),
    ]


def _cio_base() -> List[MMQuestion]:
    return [
        MMQuestion(
            question=("If I asked to migrate your core "
                      "clinical system tomorrow, how long "
                      "would it take?"),
            listen_for=("< 18 months = well-documented; > 24 "
                        "months = lock-in or data model "
                        "fragility."),
            priority="must_ask",
        ),
        MMQuestion(
            question=("Any material cyber incidents or "
                      "ransomware attempts in the last 2 "
                      "years? Disclosed?"),
            listen_for=("Honest 'no' or detailed 'yes + "
                        "remediation' are both fine. Hedging "
                        "means there was an incident."),
            priority="must_ask",
        ),
        MMQuestion(
            question=("What's your EHR uptime for the past "
                      "12 months?"),
            listen_for=("< 99.5% uptime is an ops drag the "
                        "P&L doesn't show."),
            priority="should_ask",
        ),
    ]


BASE_ROLE_Q_BUILDERS: Dict[str, Any] = {
    "ceo": _ceo_base,
    "cfo": _cfo_base,
    "coo": _coo_base,
    "cmo": _cmo_base,
    "cco": _cco_base,
    "cio": _cio_base,
}


# ── Conditional questions ──────────────────────────────

def _add_thesis_questions(
    role: str, inputs: MMInputs,
) -> List[MMQuestion]:
    """Questions triggered by the chosen thesis + chain status."""
    extra: List[MMQuestion] = []
    thesis = inputs.thesis.lower()
    if thesis == "denial_reduction" and role == "cfo":
        extra.append(MMQuestion(
            question=("Your plan calls for denial rate from "
                      "X% to Y% in Z months. Tell me the "
                      "program: who owns it, what's the "
                      "weekly metric?"),
            listen_for=("Named program with cadence = real. "
                        "'Focus' = not real."),
            follow_up=("How much of year-1 EBITDA uplift is "
                       "one-time A/R release vs. run-rate?"),
            closes_gap="year1_cash_release_share",
            priority="must_ask",
        ))
    if thesis == "payer_mix_shift" and role == "cco":
        extra.append(MMQuestion(
            question=("Which commercial payers have confirmed "
                      "capacity for the volume shift?"),
            listen_for=("Named payers, signed terms. "
                        "'Discussions' = not confirmed."),
            closes_gap="commercial_payer_capacity_confirmed",
            priority="must_ask",
        ))
    if thesis == "rollup_consolidation" and role == "ceo":
        extra.append(MMQuestion(
            question=("How many LOIs are signed today? What's "
                      "the cap rate?"),
            listen_for=("Signed LOIs = pipeline is real. "
                        "'Opportunity universe' = not."),
            closes_gap="signed_lois_count",
            priority="must_ask",
        ))
        extra.append(MMQuestion(
            question=("Of your last 3 integrations, how long "
                      "did each take vs. plan?"),
            listen_for=("On-time = executable. Late = "
                        "plan is optimistic."),
            priority="should_ask",
        ))
    if thesis == "cmi_uplift" and role == "cmo":
        extra.append(MMQuestion(
            question=("How many CDI FTEs do you have, and "
                      "what's their certification mix?"),
            listen_for=("CDI staffing = real uplift program. "
                        "Outsourced = hope."),
            closes_gap="cdi_fte_count",
            priority="must_ask",
        ))
    return extra


def _add_pattern_questions(
    role: str, inputs: MMInputs,
) -> List[MMQuestion]:
    """Questions triggered by specific pattern matches."""
    extra: List[MMQuestion] = []
    for pattern in inputs.pattern_matches:
        if pattern == "fix_denials_in_12_months" and role == "coo":
            extra.append(MMQuestion(
                question=("Seller modeled 700 bps denial "
                          "reduction in 12 months. What does "
                          "the current program deliver "
                          "monthly?"),
                listen_for=("Program numbers with 3-6 months "
                            "of actuals. Anything else is "
                            "forecast."),
                priority="must_ask",
            ))
        if pattern == "high_leverage_thin_coverage" and role == "cfo":
            extra.append(MMQuestion(
                question=("At worst-year EBITDA in your bear "
                          "scenario, what's leverage?"),
                listen_for=("Partner wants specific number "
                            "with basis. 'Fine' is not an "
                            "answer."),
                priority="must_ask",
            ))
        if pattern == "medicare_advantage_will_make_it_up":
            extra.append(MMQuestion(
                question=("Tell me about your MA contracting "
                          "strategy — benchmark rates, risk "
                          "arrangements."),
                listen_for=("Specific benchmarks by plan. "
                            "Vague = seller is waving hands."),
                priority="must_ask",
            ))
        if pattern == "ceo_will_stay_through_close" and role == "ceo":
            extra.append(MMQuestion(
                question=("Walk me through your personal "
                          "commitment on timing — close + "
                          "36 months minimum."),
                listen_for=("Confident = genuine. Hesitation "
                            "= flight risk at close."),
                priority="must_ask",
            ))
    return extra


def _add_packet_gap_questions(
    role: str, inputs: MMInputs,
) -> List[MMQuestion]:
    """Questions driven by explicit gaps in the packet."""
    role_gap_map = {
        "cfo": ["forecast_accuracy_history",
                "covenant_headroom_trend",
                "nwc_volatility"],
        "cmo": ["cmi_trend", "rac_audit_status",
                "cms_star_trend"],
        "ceo": ["retention_top_3_hires",
                "top_strategic_division_pnl"],
        "coo": ["ops_cadence", "kpi_daily_review",
                "division_operating_cadence_gap"],
        "cco": ["top_payer_churn", "payer_renewal_schedule"],
        "cio": ["ehr_migration_estimate",
                "cyber_incident_history",
                "ehr_uptime"],
    }
    extras: List[MMQuestion] = []
    for gap in inputs.packet_gaps:
        if gap in role_gap_map.get(role, []):
            extras.append(MMQuestion(
                question=(f"The packet is missing '{gap}'. "
                          "Can you share the underlying "
                          "data + a 3-year trend?"),
                listen_for=("Quick answer = data exists but "
                            "wasn't shared. Slow answer = "
                            "data doesn't exist."),
                closes_gap=gap,
                priority="should_ask",
            ))
    return extras


# ── Main entry point ──────────────────────────────────

def build_mm_question_plan(inputs: MMInputs) -> MMQuestionPlan:
    role_sets: List[MMQuestionSet] = []
    total = 0
    must_ask = 0
    for role in inputs.roles:
        base_builder = BASE_ROLE_Q_BUILDERS.get(role)
        if base_builder is None:
            continue
        questions: List[MMQuestion] = list(base_builder())
        questions.extend(_add_thesis_questions(role, inputs))
        questions.extend(_add_pattern_questions(role, inputs))
        questions.extend(_add_packet_gap_questions(role, inputs))
        total += len(questions)
        must_ask += sum(1 for q in questions
                         if q.priority == "must_ask")
        role_sets.append(MMQuestionSet(role=role,
                                         questions=questions))

    if must_ask >= 8:
        note = (f"{must_ask} must-ask questions across "
                f"{len(role_sets)} role(s). Block 2 hours "
                "for the meeting — this is a gating session, "
                "not a meet-and-greet.")
    elif must_ask >= 4:
        note = (f"{must_ask} must-ask. Standard management "
                "meeting scope.")
    else:
        note = ("Question volume light; consider splitting "
                "must-asks across a follow-up call.")

    return MMQuestionPlan(
        role_sets=role_sets,
        total_questions=total,
        must_ask_count=must_ask,
        partner_note=note,
    )


def render_mm_plan_markdown(p: MMQuestionPlan) -> str:
    lines = [
        "# Management-meeting question plan",
        "",
        f"_{p.partner_note}_",
        "",
        f"- Total questions: {p.total_questions}",
        f"- Must-ask: {p.must_ask_count}",
        "",
    ]
    for rs in p.role_sets:
        lines.append(f"## {rs.role.upper()}")
        lines.append("")
        for i, q in enumerate(rs.questions, 1):
            marker = "**must-ask**" if q.priority == "must_ask" else ""
            lines.append(f"{i}. {q.question} {marker}")
            lines.append(f"   - *Listen for:* {q.listen_for}")
            if q.follow_up:
                lines.append(f"   - *Follow-up:* {q.follow_up}")
            if q.closes_gap:
                lines.append(f"   - *Closes:* {q.closes_gap}")
            lines.append("")
    return "\n".join(lines)
