"""State AG scrutiny on PE healthcare transactions — tracker + deal-delay risk.

Partner statement: "State AGs are the new HSR for
healthcare PE. California AB 3129 now requires notice
for material transactions. Oregon SB 951 bars MSO
structures in some contexts. Illinois, Massachusetts,
Minnesota, and New York have layered on. Each state
has a review window; each has been willing to block
or condition deals. If the footprint crosses these
states, the timeline is different and so is the
structural risk."

Distinct from:
- `hsr_antitrust_healthcare_scanner` — federal HSR /
  FTC / DOJ.
- `state_scope_of_practice_exposure` — CPOM / non-
  compete.

This module tracks the **state-AG review burden** for
healthcare PE transactions across states with
specific notification or oversight laws.

### Tracked states and laws

Each state entry:
- `notification_required` — whether transaction
  must be pre-filed with state
- `review_window_days` — typical AG review window
- `material_threshold_desc` — what triggers
  notification
- `recent_scrutiny_posture` — active / ramping /
  dormant / recent_blocks
- `partner_read` — what to do about it

### Output

Per-state posture for states in deal footprint +
aggregate delay risk + partner note on timeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


AG_STATE_BOOK: Dict[str, Dict[str, Any]] = {
    "CA": {
        "notification_required": True,
        "review_window_days": 90,
        "material_threshold_desc": (
            "AB 3129: material transactions by "
            "healthcare entity ≥ $25M revenue; 90-day "
            "notice + AG review."),
        "recent_scrutiny_posture": "active",
        "partner_read": (
            "Pre-file AB 3129 notice; build 90-day "
            "cushion into sign-to-close; expect "
            "supplemental-info requests."
        ),
    },
    "OR": {
        "notification_required": True,
        "review_window_days": 60,
        "material_threshold_desc": (
            "SB 951: bars MSO control over certain "
            "clinical decisions; transaction notice "
            "for material entity sales."),
        "recent_scrutiny_posture": "ramping",
        "partner_read": (
            "Re-verify MSO/PC structure against OR "
            "SB 951 specifics — prior PE MSO models "
            "may be at risk in-state."
        ),
    },
    "IL": {
        "notification_required": True,
        "review_window_days": 30,
        "material_threshold_desc": (
            "HB 2222: pre-merger notice to AG for "
            "healthcare provider transactions; 30-day "
            "review."),
        "recent_scrutiny_posture": "active",
        "partner_read": (
            "30-day AG review; standard filing path. "
            "No recent blocks but active info "
            "requests."
        ),
    },
    "NY": {
        "notification_required": True,
        "review_window_days": 30,
        "material_threshold_desc": (
            "PHL §4550: healthcare material "
            "transaction notice; 30-day review + "
            "potential extended review."),
        "recent_scrutiny_posture": "active",
        "partner_read": (
            "NY AG increasingly scrutinizes PE roll-"
            "ups; be prepared to defend competitive "
            "effects."
        ),
    },
    "MA": {
        "notification_required": True,
        "review_window_days": 60,
        "material_threshold_desc": (
            "HPC notice: material changes in non-"
            "profit conversion, provider affiliation, "
            "or ownership require HPC review."),
        "recent_scrutiny_posture": "active",
        "partner_read": (
            "MA HPC has recent-block precedent on PE "
            "deals; expect cost-growth-benchmark "
            "scrutiny."
        ),
    },
    "MN": {
        "notification_required": True,
        "review_window_days": 30,
        "material_threshold_desc": (
            "HF 4246: physician practice + outpatient "
            "surgical center transaction notice to AG."),
        "recent_scrutiny_posture": "ramping",
        "partner_read": (
            "New statute; file early. AG building "
            "review playbook; first movers set "
            "precedent."
        ),
    },
    "WA": {
        "notification_required": True,
        "review_window_days": 60,
        "material_threshold_desc": (
            "Notice for nonprofit conversions and "
            "material healthcare mergers."),
        "recent_scrutiny_posture": "dormant",
        "partner_read": (
            "Standard filing; not a current bottleneck."
        ),
    },
    "NV": {
        "notification_required": True,
        "review_window_days": 30,
        "material_threshold_desc": (
            "AB 518: healthcare transaction notice to "
            "AG."),
        "recent_scrutiny_posture": "ramping",
        "partner_read": (
            "New law; file; no scrutiny precedent yet."
        ),
    },
    "NJ": {
        "notification_required": False,
        "review_window_days": 0,
        "material_threshold_desc": (
            "No specific healthcare-transaction notice "
            "law; general AG consumer-protection "
            "jurisdiction."),
        "recent_scrutiny_posture": "dormant",
        "partner_read": (
            "No pre-filing; standard deal timing."
        ),
    },
}


@dataclass
class AGStateFootprint:
    state: str
    share_of_npr_pct: float


@dataclass
class StateAGInputs:
    footprint: List[AGStateFootprint] = field(
        default_factory=list)


@dataclass
class StateAGHit:
    state: str
    in_book: bool
    notification_required: bool
    review_window_days: int
    share_of_npr_pct: float
    recent_scrutiny_posture: str
    material_threshold_desc: str
    partner_read: str


@dataclass
class StateAGReport:
    hits: List[StateAGHit] = field(default_factory=list)
    max_review_window_days: int = 0
    cumulative_notification_share_pct: float = 0.0
    has_recent_blocks: bool = False
    verdict: str = "no_state_ag_exposure"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": [
                {"state": h.state,
                 "in_book": h.in_book,
                 "notification_required":
                     h.notification_required,
                 "review_window_days":
                     h.review_window_days,
                 "share_of_npr_pct":
                     h.share_of_npr_pct,
                 "recent_scrutiny_posture":
                     h.recent_scrutiny_posture,
                 "material_threshold_desc":
                     h.material_threshold_desc,
                 "partner_read": h.partner_read}
                for h in self.hits
            ],
            "max_review_window_days":
                self.max_review_window_days,
            "cumulative_notification_share_pct":
                self.cumulative_notification_share_pct,
            "has_recent_blocks": self.has_recent_blocks,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def track_state_ag_scrutiny(
    inputs: StateAGInputs,
) -> StateAGReport:
    if not inputs.footprint:
        return StateAGReport(
            partner_note=(
                "No state footprint — verify whether "
                "any footprint states have AG "
                "notification laws."
            ),
        )

    hits: List[StateAGHit] = []
    max_window = 0
    notification_share = 0.0
    has_recent_blocks = False
    active_count = 0

    for fp in inputs.footprint:
        state = fp.state.upper()
        book = AG_STATE_BOOK.get(state)
        if book is None:
            # State not in book — assume no specific
            # healthcare AG filing requirement.
            hits.append(StateAGHit(
                state=state,
                in_book=False,
                notification_required=False,
                review_window_days=0,
                share_of_npr_pct=round(
                    fp.share_of_npr_pct, 4),
                recent_scrutiny_posture="unknown",
                material_threshold_desc=(
                    "State not in AG scrutiny book — "
                    "no known healthcare-transaction "
                    "notice requirement."),
                partner_read=(
                    "No known filing requirement; "
                    "confirm with local counsel."),
            ))
            continue

        hits.append(StateAGHit(
            state=state,
            in_book=True,
            notification_required=book["notification_required"],
            review_window_days=book["review_window_days"],
            share_of_npr_pct=round(fp.share_of_npr_pct, 4),
            recent_scrutiny_posture=book["recent_scrutiny_posture"],
            material_threshold_desc=book["material_threshold_desc"],
            partner_read=book["partner_read"],
        ))
        if book["notification_required"]:
            notification_share += fp.share_of_npr_pct
            if book["review_window_days"] > max_window:
                max_window = book["review_window_days"]
        if book["recent_scrutiny_posture"] == "active":
            active_count += 1
        if "recent-block" in book["partner_read"].lower():
            has_recent_blocks = True

    # Verdict logic
    if max_window >= 90 or has_recent_blocks:
        verdict = "high_state_ag_exposure"
        note = (
            f"Longest review window {max_window} days; "
            f"{notification_share:.0%} of revenue in "
            "notice-required states. "
        )
        if has_recent_blocks:
            note += (
                "Recent AG-block precedent in footprint "
                "— structural risk beyond timing delay. "
            )
        note += (
            "Build AG review into sign-to-close "
            "timeline; consider state-specific "
            "counsel."
        )
    elif notification_share > 0.30:
        verdict = "moderate_state_ag_exposure"
        note = (
            f"{notification_share:.0%} of revenue in "
            f"notice-required states; longest review "
            f"{max_window} days. File early; expect "
            "supplemental-info requests."
        )
    elif notification_share > 0:
        verdict = "minor_state_ag_exposure"
        note = (
            f"{notification_share:.0%} of revenue in "
            f"notice-required states; {max_window}-day "
            "review. Standard filing path."
        )
    else:
        verdict = "no_state_ag_exposure"
        note = (
            "No footprint in AG-notice states; "
            "standard deal timing applies."
        )

    return StateAGReport(
        hits=hits,
        max_review_window_days=max_window,
        cumulative_notification_share_pct=round(
            notification_share, 4),
        has_recent_blocks=has_recent_blocks,
        verdict=verdict,
        partner_note=note,
    )


def render_state_ag_markdown(
    r: StateAGReport,
) -> str:
    lines = [
        "# State AG scrutiny",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Max review window: "
        f"{r.max_review_window_days} days",
        f"- Notice-required share: "
        f"{r.cumulative_notification_share_pct:.0%}",
        f"- Recent blocks in footprint: "
        f"{'yes' if r.has_recent_blocks else 'no'}",
        "",
        "| State | Share | Notice | Review days | "
        "Posture |",
        "|---|---|---|---|---|",
    ]
    for h in r.hits:
        lines.append(
            f"| {h.state} | "
            f"{h.share_of_npr_pct:.0%} | "
            f"{'yes' if h.notification_required else 'no'} | "
            f"{h.review_window_days} | "
            f"{h.recent_scrutiny_posture} |"
        )
    return "\n".join(lines)
