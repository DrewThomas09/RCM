"""Data-room gap signal — what the seller isn't showing you.

Partner statement: "The missing documents in a data
room aren't gaps to close. They're telling you what
the seller doesn't want you to see. A missing 3-year
GAAP means they've never been through a real
diligence. A missing top-5 payer contract means the
payer is on notice."

Distinct from `data_room_tracker` (completeness
score + gap list). This module **reads the gaps as
signals** — translates missing documents into partner-
voice inferences about seller readiness, hidden
issues, and process intent.

### 8 gap-signal categories

1. **three_year_gaap_missing** — seller has never been
   audited to PE standard.
2. **qofe_not_yet_engaged** — not QofE-ready, adds 8-12
   weeks.
3. **top_5_payer_contracts_missing** — payer-side
   issue seller is hiding.
4. **cms_survey_deficiencies_missing** — quality
   compliance opacity.
5. **physician_comp_schedule_missing** — can't verify
   normalization claims.
6. **it_cyber_incident_log_missing** — breach history
   uncertain.
7. **open_litigation_detail_missing** — legal exposure
   opacity.
8. **related_party_transaction_schedule_missing** —
   structural adjustments hidden.

### Per-signal partner inference

Each missing category produces:
- `what_it_signals` — partner-voice diagnosis of seller.
- `process_impact` — days of delay or reprice action.
- `partner_counter` — specific ask in response.

### Output

List of fired signals + aggregate process delay +
partner note on aggregate seller-readiness read.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GapSignal:
    name: str
    triggered: bool
    what_it_signals: str
    process_impact_days: int
    partner_counter: str


@dataclass
class DataRoomGapInputs:
    three_year_gaap_missing: bool = False
    qofe_not_yet_engaged: bool = False
    top_5_payer_contracts_missing: bool = False
    cms_survey_deficiencies_missing: bool = False
    physician_comp_schedule_missing: bool = False
    it_cyber_incident_log_missing: bool = False
    open_litigation_detail_missing: bool = False
    related_party_transaction_schedule_missing: bool = False


@dataclass
class DataRoomGapReport:
    signals: List[GapSignal] = field(default_factory=list)
    triggered_count: int = 0
    total_process_delay_days: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signals": [
                {"name": s.name,
                 "triggered": s.triggered,
                 "what_it_signals": s.what_it_signals,
                 "process_impact_days": s.process_impact_days,
                 "partner_counter": s.partner_counter}
                for s in self.signals
            ],
            "triggered_count": self.triggered_count,
            "total_process_delay_days":
                self.total_process_delay_days,
            "partner_note": self.partner_note,
        }


# (signal_name, what_it_signals, process_days, partner_counter)
SIGNAL_CATALOG: List[Any] = [
    (
        "three_year_gaap_missing",
        "Seller has never been through an audit to PE "
        "standard — monthly flash or QuickBooks exports "
        "only. Expect EBITDA restatement at QofE.",
        45,
        "Require seller to engage big-4 QofE pre-LOI; "
        "structure price-adjustment mechanism on QofE-"
        "final delta > 3%.",
    ),
    (
        "qofe_not_yet_engaged",
        "Not QofE-ready. 8-12 weeks added to close, "
        "plus meaningful risk of restatement.",
        60,
        "Make QofE engagement a closing condition; "
        "outside date +60 days minimum.",
    ),
    (
        "top_5_payer_contracts_missing",
        "Payer on notice, disputed terms, OR seller is "
        "hiding a payer concession. Top-5 payer contracts "
        "are load-bearing on the revenue thesis.",
        30,
        "Refuse to advance past IOI without top-5 payer "
        "contracts in data room; each open renewal is a "
        "walk-right.",
    ),
    (
        "cms_survey_deficiencies_missing",
        "Quality compliance opacity. Either clean history "
        "or unresolved deficiency they hope we miss.",
        21,
        "Demand CMS 2567 deficiency reports (past 36 mo) "
        "+ plan of correction status. Unresolved 2567 "
        "triggers retention-condition.",
    ),
    (
        "physician_comp_schedule_missing",
        "Cannot verify physician-comp normalization "
        "claims in the pro-forma. Adjustment is "
        "unsupported.",
        14,
        "Haircut claimed comp normalization by 40% "
        "until physician-level schedule is produced.",
    ),
    (
        "it_cyber_incident_log_missing",
        "Breach history uncertain. HIPAA compliance opaque. "
        "Could be clean or disclosed-too-late.",
        21,
        "Require 24-mo cyber incident log + OCR breach "
        "portal search. Carve cyber rep from R&W on "
        "non-disclosure.",
    ),
    (
        "open_litigation_detail_missing",
        "Pending litigation summary not disclosed. "
        "Indemnity cap sizing is blind.",
        14,
        "Litigation inventory as closing condition; "
        "escrow sized to disclosed matters.",
    ),
    (
        "related_party_transaction_schedule_missing",
        "Related-party transactions (mgmt rent, "
        "ancillary ownership, family vendor relationships) "
        "not itemized. Structural adjustment opacity.",
        14,
        "Require full RPT schedule pre-LOI; each "
        "transaction classified as non-recurring / "
        "market-rate / related-party adjustment.",
    ),
]


def scan_data_room_gaps(
    inputs: DataRoomGapInputs,
) -> DataRoomGapReport:
    signals: List[GapSignal] = []
    triggered = 0
    total_days = 0
    for name, what, days, counter in SIGNAL_CATALOG:
        is_on = getattr(inputs, name, False)
        if is_on:
            triggered += 1
            total_days += days
        signals.append(GapSignal(
            name=name,
            triggered=is_on,
            what_it_signals=what,
            process_impact_days=days if is_on else 0,
            partner_counter=counter if is_on
            else "No gap flagged.",
        ))

    if triggered >= 5:
        note = (
            f"{triggered} data-room gaps; ~{total_days} "
            "days of process impact. Partner: seller is "
            "not QofE-ready or not acting in good faith. "
            "Demand complete data room before advancing "
            "to LOI."
        )
    elif triggered >= 3:
        note = (
            f"{triggered} gaps, ~{total_days} days. "
            "Partner: seller unprepared — slow the process "
            "and demand specifics before underwriting more "
            "hours."
        )
    elif triggered >= 1:
        note = (
            f"{triggered} gap(s), ~{total_days} days. "
            "Standard diligence gap; close via follow-up "
            "data request."
        )
    else:
        note = (
            "Data room appears complete on partner "
            "scanning axis. Proceed to normal diligence "
            "cadence."
        )

    return DataRoomGapReport(
        signals=signals,
        triggered_count=triggered,
        total_process_delay_days=total_days,
        partner_note=note,
    )


def render_data_room_gap_markdown(
    r: DataRoomGapReport,
) -> str:
    lines = [
        "# Data-room gap signal",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Triggered gaps: {r.triggered_count} / "
        f"{len(r.signals)}",
        f"- Process delay: "
        f"~{r.total_process_delay_days} days",
        "",
        "| Gap | Triggered | What it signals | "
        "Partner counter |",
        "|---|---|---|---|",
    ]
    for s in r.signals:
        check = "✓" if s.triggered else "—"
        lines.append(
            f"| {s.name} | {check} | "
            f"{s.what_it_signals} | {s.partner_counter} |"
        )
    return "\n".join(lines)
