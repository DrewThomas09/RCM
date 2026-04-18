"""LP quarterly update — what partners write about a portfolio
company at quarter-end.

Partner statement: "The LP letter is the only document
about a deal that every LP reads every quarter. It's
not a pitch — they already committed. It's a
credibility document. Write defensively and the LP
reads between the lines; write plainly about what
worked and what didn't and they trust you on the next
fund. If the mark moved, say why. If a KPI missed
thesis, say so. If Medicare reset, say so. LPs hear
from twenty sponsors a quarter — they can smell
spin."

Distinct from:
- `lp_pitch` — raise-era IR narrative (we want your
  $250M).
- `lp_side_letter_flags` — compliance with MFN / reg
  side letters.
- `board_memo` — internal/board-level commentary.

### What a quarterly LP letter actually contains

Four partner-voice paragraphs + one risks paragraph:

1. **Quarter-in-review** — one direct sentence on
   whether mark moved and why. No hedging.
2. **KPI-vs-thesis** — three numbers tied to the
   original thesis. Mark-to-reality.
3. **What we did this quarter** — concrete operator
   actions, not "focused on execution."
4. **Next quarter** — two specific things we're
   underwriting to deliver.
5. **Risks** — named, not generic. Specific reg event,
   specific payer, specific cost line.

### Tone calibration by mark movement

- **Mark up ≥ 10%** — "measured confidence" not
  victory-lap. Flag what could reverse.
- **Mark flat (±5%)** — plain, operator-focused.
- **Mark down 5-15%** — own the miss. Diagnosis, not
  excuse. Next-quarter plan.
- **Mark down > 15%** — explicit "here's what
  happened, here's what we're doing, here's why we
  still believe the thesis" (or, if thesis is broken,
  say so).

### Partner-voice tells that LPs smell

Bad: "we continue to execute against our thesis,"
"market headwinds," "softness in volumes."
Good: "organic EBITDA grew 8%; acquisition-adjusted
EBITDA grew 14%," "same-store denial rate fell 180
bps," "Medicare sequestration cut $3M; commercial
repricing of the Blues contract offset $4M."

### Output

Five-paragraph letter + tone tag + risks list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LPUpdateInputs:
    company_name: str = "PortCo"
    quarter_label: str = "Q1 2026"
    mark_change_pct: float = 0.0
    prior_mark_m: float = 500.0
    current_mark_m: float = 500.0
    original_thesis_one_liner: str = (
        "roll-up of outpatient specialty practices")
    thesis_kpi_1_label: str = "same-store revenue growth"
    thesis_kpi_1_actual: float = 0.07
    thesis_kpi_1_underwritten: float = 0.08
    thesis_kpi_2_label: str = (
        "EBITDA margin expansion")
    thesis_kpi_2_actual: float = 0.012
    thesis_kpi_2_underwritten: float = 0.015
    thesis_kpi_3_label: str = "same-store denial rate"
    thesis_kpi_3_actual: float = -0.018
    thesis_kpi_3_underwritten: float = -0.025
    quarter_actions: List[str] = field(
        default_factory=lambda: [
            "closed 2 bolt-on acquisitions",
            "renegotiated top-3 payer contract",
        ])
    next_quarter_commits: List[str] = field(
        default_factory=lambda: [
            "launch shared-services RCM platform",
            "sign 1 additional bolt-on LOI",
        ])
    named_risks: List[str] = field(
        default_factory=lambda: [
            "OBBBA outpatient rate cut effective 2026Q3",
            "Aetna MA contract expires 2026-12-31",
        ])
    reg_shock_this_quarter_m: float = 0.0
    reg_shock_description: str = ""
    one_time_item_m: float = 0.0
    one_time_item_description: str = ""


@dataclass
class LPUpdateReport:
    tone_tag: str = "flat"
    quarter_in_review: str = ""
    kpi_vs_thesis: str = ""
    what_we_did: str = ""
    next_quarter: str = ""
    risks_paragraph: str = ""
    full_letter: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tone_tag": self.tone_tag,
            "quarter_in_review":
                self.quarter_in_review,
            "kpi_vs_thesis": self.kpi_vs_thesis,
            "what_we_did": self.what_we_did,
            "next_quarter": self.next_quarter,
            "risks_paragraph": self.risks_paragraph,
            "full_letter": self.full_letter,
            "partner_note": self.partner_note,
        }


def _kpi_sentence(
    label: str, actual: float, plan: float
) -> str:
    delta = actual - plan
    direction = (
        "beat plan" if delta > 0
        else ("missed plan" if delta < 0 else "at plan")
    )
    # formatting: improvement-type KPIs where plan is
    # negative (denial rate going down is good) need
    # sign-flipped interpretation for the reader.
    if plan < 0:
        # plan is e.g. -2.5% denial reduction
        if actual < plan:
            direction = "beat plan"
        elif actual > plan:
            direction = "missed plan"
        else:
            direction = "at plan"

    return (
        f"{label}: "
        f"{actual:+.1%} actual vs. {plan:+.1%} plan — "
        f"{direction}."
    )


def compose_lp_quarterly_update(
    inputs: LPUpdateInputs,
) -> LPUpdateReport:
    mark = inputs.mark_change_pct

    # Tone calibration
    if mark >= 0.10:
        tone = "measured_up"
        opening_frame = (
            f"{inputs.company_name} marked up "
            f"{mark:+.1%} this quarter. The move is "
            "supported by trailing-twelve EBITDA, not a "
            "multiple expansion; we are not revising "
            "the exit case yet."
        )
    elif mark >= -0.05:
        tone = "flat"
        opening_frame = (
            f"{inputs.company_name} was held flat "
            f"({mark:+.1%}). The quarter was a "
            "block-and-tackle quarter — no re-rating "
            "events, operator-focused work."
        )
    elif mark >= -0.15:
        tone = "owned_miss"
        opening_frame = (
            f"{inputs.company_name} was written down "
            f"{mark:+.1%} this quarter. "
        )
        if inputs.reg_shock_this_quarter_m < 0:
            opening_frame += (
                f"Driver: {inputs.reg_shock_description} "
                f"(~${abs(inputs.reg_shock_this_quarter_m):.0f}M "
                "EBITDA impact). We own this call — the "
                "exposure was in our model but we "
                "underweighted timing."
            )
        else:
            opening_frame += (
                "Driver is operator, not market — "
                "execution on the second-half plan "
                "slipped. Diagnosis and response in the "
                "sections below."
            )
    else:
        tone = "thesis_stress"
        opening_frame = (
            f"{inputs.company_name} was written down "
            f"{mark:+.1%} this quarter. This is a "
            "material mark. "
        )
        if inputs.reg_shock_this_quarter_m < 0:
            opening_frame += (
                f"Primary driver: "
                f"{inputs.reg_shock_description} "
                f"(~${abs(inputs.reg_shock_this_quarter_m):.0f}M "
                "EBITDA). The underlying business is "
                "intact; the valuation re-rate reflects "
                "reimbursement reality, not thesis failure."
            )
        else:
            opening_frame += (
                "The drivers are operator and market. We "
                "are walking through whether the original "
                "thesis still holds at the section below."
            )

    # One-time vs recurring discipline
    if inputs.one_time_item_m != 0.0:
        opening_frame += (
            f" One-time item: "
            f"{inputs.one_time_item_description} "
            f"(${inputs.one_time_item_m:+.0f}M, "
            "recurring EBITDA excludes)."
        )

    # KPI paragraph
    kpi_lines = [
        _kpi_sentence(
            inputs.thesis_kpi_1_label,
            inputs.thesis_kpi_1_actual,
            inputs.thesis_kpi_1_underwritten,
        ),
        _kpi_sentence(
            inputs.thesis_kpi_2_label,
            inputs.thesis_kpi_2_actual,
            inputs.thesis_kpi_2_underwritten,
        ),
        _kpi_sentence(
            inputs.thesis_kpi_3_label,
            inputs.thesis_kpi_3_actual,
            inputs.thesis_kpi_3_underwritten,
        ),
    ]
    kpi_paragraph = (
        f"Tracking against the original thesis "
        f"({inputs.original_thesis_one_liner}): "
        + " ".join(kpi_lines)
    )

    # What we did
    if inputs.quarter_actions:
        actions = "; ".join(inputs.quarter_actions)
        did = (
            f"Operator work this quarter: {actions}. "
            "These are the concrete actions — the "
            "trailing-twelve impact flows through "
            "Q2-Q3 reporting."
        )
    else:
        did = (
            "Quarter was administrative: no M&A, no "
            "repricing events. We were building the "
            "integration runway, not spending it."
        )

    # Next quarter
    if inputs.next_quarter_commits:
        nxt = (
            "Next quarter we're underwriting two "
            "specific deliverables: "
            + "; ".join(inputs.next_quarter_commits)
            + ". We'll report actuals against these in "
            "the Q+1 letter."
        )
    else:
        nxt = (
            "Next quarter is continued execution on the "
            "current plan — no new initiatives underwrit-"
            "ten."
        )

    # Risks
    if inputs.named_risks:
        risks_para = (
            "Known risks we're watching: "
            + "; ".join(
                f"({i+1}) {r}" for i, r in
                enumerate(inputs.named_risks)
            )
            + ". We'll flag any of these firming in the "
            "next letter rather than surface it the "
            "quarter it bites."
        )
    else:
        risks_para = (
            "No named specific risks above threshold this "
            "quarter. Regulatory calendar remains the "
            "standing watchlist."
        )

    letter = (
        f"**{inputs.company_name} — {inputs.quarter_label}**\n\n"
        f"{opening_frame}\n\n"
        f"{kpi_paragraph}\n\n"
        f"{did}\n\n"
        f"{nxt}\n\n"
        f"{risks_para}"
    )

    # Partner note: meta-read
    missed = sum(
        1 for (a, p) in (
            (inputs.thesis_kpi_1_actual,
             inputs.thesis_kpi_1_underwritten),
            (inputs.thesis_kpi_2_actual,
             inputs.thesis_kpi_2_underwritten),
        )
        if a < p
    )
    # KPI 3 is improvement-direction; flip
    if (inputs.thesis_kpi_3_actual >
            inputs.thesis_kpi_3_underwritten):
        missed += 1

    if tone in {"thesis_stress", "owned_miss"} and missed >= 2:
        partner_note = (
            "Material mark-down with 2+ KPI misses — "
            "next letter needs a revised thesis or an "
            "explicit exit-timing shift. LPs notice when "
            "two letters in a row use the same 'we're "
            "focused on execution' language."
        )
    elif tone == "measured_up":
        partner_note = (
            "Mark-up quarter — LP read is positive but "
            "LP memory is long. Don't let next quarter's "
            "letter be the soft one; pacing matters."
        )
    else:
        partner_note = (
            "Standard quarter. LPs read this letter in "
            "90 seconds; the plainness is the point."
        )

    return LPUpdateReport(
        tone_tag=tone,
        quarter_in_review=opening_frame,
        kpi_vs_thesis=kpi_paragraph,
        what_we_did=did,
        next_quarter=nxt,
        risks_paragraph=risks_para,
        full_letter=letter,
        partner_note=partner_note,
    )


def render_lp_quarterly_markdown(
    r: LPUpdateReport,
) -> str:
    return (
        "# LP quarterly update\n\n"
        f"_Tone: **{r.tone_tag}**_ — {r.partner_note}\n\n"
        "---\n\n"
        f"{r.full_letter}\n"
    )
