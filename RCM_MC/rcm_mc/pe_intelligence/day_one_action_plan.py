"""Day 1 action plan — lock in value in the first 7 days.

Partner statement: "The 100-day plan gets the press.
The first 7 days get the value. If day 1 is chaos, the
100-day plan is already slipping. I want a checklist
the operating team runs like a pre-flight."

Distinct from:
- `hundred_day_plan` — 100-day workstream plan.
- `management_first_sitdown` — first CEO conversation.
- `first_thirty_minutes` — the first meeting.

This module catalogs **12 specific day-1-to-day-7
actions** that lock in value post-close. Each carries:
- owner (sponsor / CEO / CFO / legal / ops)
- timing (day_1 / week_1)
- risk if delayed

### 12 day-1 actions

1. **ceo_all_hands** — alignment message vs. fear message.
2. **top_customer_communication** — top-10 get a call.
3. **payer_relationship_call** — top payers, reassurance.
4. **banking_transition** — new lender intros + signing
   authority update.
5. **board_reconstitution** — sponsor takes majority.
6. **it_access_handoff** — admin access to systems.
7. **compensation_confirmation** — freeze or confirm
   key-15 comp.
8. **retention_activation** — signed retention agreements
   take effect.
9. **insurance_policy_transition** — D&O / cyber / pro-
   liability transitions.
10. **auditor_transition** — appoint audit firm for
    sponsor-standard schedules.
11. **operating_committee_kickoff** — weekly cadence with
    owners.
12. **regulatory_notice_filings** — CHOW / licensure
    filings begin.

### Output

Full action list with completion status + partner-voice
escalation list for any items not owned or dated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DayOneAction:
    name: str
    owner: str                             # sponsor / ceo / cfo / legal / ops
    timing: str                            # day_1 / day_3 / week_1
    risk_if_delayed: str
    description: str


ACTION_LIBRARY: List[DayOneAction] = [
    DayOneAction(
        name="ceo_all_hands",
        owner="ceo",
        timing="day_1",
        risk_if_delayed=(
            "Rumor fills the vacuum; employees start "
            "updating LinkedIn."
        ),
        description=(
            "CEO addresses full company within 4 hours of "
            "close. Messaging: stability + investment + "
            "sponsor commitment. Not transactional."
        ),
    ),
    DayOneAction(
        name="top_customer_communication",
        owner="ceo",
        timing="day_1",
        risk_if_delayed=(
            "Competitors exploit ownership change; call "
            "day 1 to poach accounts."
        ),
        description=(
            "Top 10 customers / payers get a call from "
            "CEO with 48 hours. Continuity message + "
            "named account manager."
        ),
    ),
    DayOneAction(
        name="payer_relationship_call",
        owner="ceo",
        timing="week_1",
        risk_if_delayed=(
            "Payers use change of control to reopen "
            "contract terms."
        ),
        description=(
            "Top 5 payer relationships get formal "
            "continuity confirmation. Reinforce no change "
            "in contract terms pre-renewal."
        ),
    ),
    DayOneAction(
        name="banking_transition",
        owner="cfo",
        timing="day_1",
        risk_if_delayed=(
            "Wire authorizations lapse; payroll risk."
        ),
        description=(
            "Update signing authority, intro new lender "
            "relationship, confirm drawdowns and wire "
            "approvers."
        ),
    ),
    DayOneAction(
        name="board_reconstitution",
        owner="legal",
        timing="day_1",
        risk_if_delayed=(
            "Old board can still bind the company."
        ),
        description=(
            "Execute board resolution: sponsor majority + "
            "committee appointments (audit / comp / "
            "nom-gov)."
        ),
    ),
    DayOneAction(
        name="it_access_handoff",
        owner="ops",
        timing="day_1",
        risk_if_delayed=(
            "Ex-employees with admin keys retain access."
        ),
        description=(
            "Admin ownership of EHR / ERP / email / "
            "financial systems transferred; former "
            "admins removed."
        ),
    ),
    DayOneAction(
        name="compensation_confirmation",
        owner="cfo",
        timing="day_1",
        risk_if_delayed=(
            "Key-15 interpret silence as threat; flight "
            "risk rises."
        ),
        description=(
            "Confirmation email to key-15 that "
            "compensation is unchanged through fiscal "
            "year; flag any planned changes honestly."
        ),
    ),
    DayOneAction(
        name="retention_activation",
        owner="legal",
        timing="day_1",
        risk_if_delayed=(
            "Retention agreements inoperative; key-15 "
            "can leave without clawback."
        ),
        description=(
            "Retention agreements signed at close take "
            "effect; payments begin per schedule."
        ),
    ),
    DayOneAction(
        name="insurance_policy_transition",
        owner="legal",
        timing="week_1",
        risk_if_delayed=(
            "Coverage gap: claim in interim period has "
            "no carrier."
        ),
        description=(
            "D&O, cyber, professional liability, and "
            "general liability policies transition or "
            "renew with tail coverage for pre-close "
            "events."
        ),
    ),
    DayOneAction(
        name="auditor_transition",
        owner="cfo",
        timing="week_1",
        risk_if_delayed=(
            "First sponsor-standard close takes an "
            "extra month; LP reporting slips."
        ),
        description=(
            "Appoint audit firm matching sponsor "
            "preference; scope first-year audit timing."
        ),
    ),
    DayOneAction(
        name="operating_committee_kickoff",
        owner="sponsor",
        timing="week_1",
        risk_if_delayed=(
            "No operating cadence; 100-day plan has no "
            "governance."
        ),
        description=(
            "Weekly ops committee established with "
            "sponsor lead + CEO + CFO + COO. Scope: "
            "100-day plan owners / metrics / blockers."
        ),
    ),
    DayOneAction(
        name="regulatory_notice_filings",
        owner="legal",
        timing="week_1",
        risk_if_delayed=(
            "CHOW / licensure lag; Medicare billing "
            "risk."
        ),
        description=(
            "Required regulatory change-of-ownership "
            "notices: CMS CHOW, state licensure "
            "transfers, DEA, etc."
        ),
    ),
]


@dataclass
class DayOneInputs:
    actions_done: List[str] = field(default_factory=list)
    actions_owned: List[str] = field(default_factory=list)


@dataclass
class ActionStatus:
    action: DayOneAction
    is_done: bool
    is_owned: bool
    escalation_needed: bool


@dataclass
class DayOneReport:
    total_actions: int
    done_count: int
    unowned_count: int
    escalations: List[str] = field(default_factory=list)
    statuses: List[ActionStatus] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_actions": self.total_actions,
            "done_count": self.done_count,
            "unowned_count": self.unowned_count,
            "escalations": list(self.escalations),
            "statuses": [
                {"action": {
                    "name": s.action.name,
                    "owner": s.action.owner,
                    "timing": s.action.timing,
                    "risk_if_delayed":
                        s.action.risk_if_delayed,
                    "description": s.action.description,
                 },
                 "is_done": s.is_done,
                 "is_owned": s.is_owned,
                 "escalation_needed": s.escalation_needed}
                for s in self.statuses
            ],
            "partner_note": self.partner_note,
        }


def assess_day_one_readiness(
    inputs: DayOneInputs,
) -> DayOneReport:
    statuses: List[ActionStatus] = []
    done = 0
    unowned = 0
    escalations: List[str] = []

    for a in ACTION_LIBRARY:
        is_done = a.name in inputs.actions_done
        is_owned = a.name in inputs.actions_owned or is_done
        escalate = (not is_done) and (not is_owned)
        if is_done:
            done += 1
        if not is_owned:
            unowned += 1
        if escalate:
            escalations.append(
                f"{a.name} ({a.timing}) — {a.risk_if_delayed}"
            )
        statuses.append(ActionStatus(
            action=a,
            is_done=is_done,
            is_owned=is_owned,
            escalation_needed=escalate,
        ))

    total = len(ACTION_LIBRARY)

    if done == total:
        note = (
            "All 12 day-1 actions complete. Partner: "
            "proceed to 100-day plan cadence."
        )
    elif unowned >= 3:
        note = (
            f"{unowned} day-1 actions unowned. Partner: "
            "name an owner for each before close; "
            "silence in week 1 costs weeks in the "
            "100-day plan."
        )
    elif done >= total - 2:
        note = (
            f"{done}/{total} day-1 actions complete. "
            "Close the remaining items within week 1."
        )
    else:
        note = (
            f"{done}/{total} complete, {unowned} unowned. "
            "Partner: run day-1 pre-flight with the "
            "operating team before close."
        )

    return DayOneReport(
        total_actions=total,
        done_count=done,
        unowned_count=unowned,
        escalations=escalations,
        statuses=statuses,
        partner_note=note,
    )


def list_day_one_actions() -> List[str]:
    return [a.name for a in ACTION_LIBRARY]


def render_day_one_plan_markdown(
    r: DayOneReport,
) -> str:
    lines = [
        "# Day 1 action plan",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total actions: {r.total_actions}",
        f"- Complete: {r.done_count}",
        f"- Unowned: {r.unowned_count}",
        "",
        "| Action | Owner | Timing | Done | Owned | "
        "Risk if delayed |",
        "|---|---|---|---|---|---|",
    ]
    for s in r.statuses:
        done = "✓" if s.is_done else ""
        own = "✓" if s.is_owned else ""
        lines.append(
            f"| {s.action.name} | {s.action.owner} | "
            f"{s.action.timing} | {done} | {own} | "
            f"{s.action.risk_if_delayed} |"
        )
    if r.escalations:
        lines.append("")
        lines.append("## Escalations")
        lines.append("")
        for e in r.escalations:
            lines.append(f"- {e}")
    return "\n".join(lines)
