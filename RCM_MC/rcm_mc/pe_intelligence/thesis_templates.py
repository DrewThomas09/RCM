"""Thesis templates — prebuilt narrative scaffolds for common theses.

Partners write IC memos faster when they start from a template.
Common thesis archetypes in healthcare PE:

- **Platform + tuck-ins** — consolidation story in a fragmented subsector.
- **Operational improvement** — RCM / labor / mix levers on an
  otherwise stable business.
- **Scale + margin** — volume-driven margin expansion.
- **Turnaround** — distressed asset with named operator.
- **Strategic exit** — positioning for strategic acquisition at exit.
- **Value-based care** — lives growth + shared-savings thesis.

Each template provides:

- An opening thesis paragraph.
- A suggested bull-case framing.
- A suggested bear-case framing.
- The operating-lever priority stack.
- Five partner-voice questions to prep the IC.

These are starting points — the deal team edits the template's
placeholders and then hands the result to the partner.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ThesisTemplate:
    name: str
    description: str
    opening_paragraph: str
    bull_case_framing: str
    bear_case_framing: str
    lever_priority: List[str] = field(default_factory=list)
    partner_questions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "opening_paragraph": self.opening_paragraph,
            "bull_case_framing": self.bull_case_framing,
            "bear_case_framing": self.bear_case_framing,
            "lever_priority": list(self.lever_priority),
            "partner_questions": list(self.partner_questions),
        }


# ── Template registry ───────────────────────────────────────────────

TEMPLATES: Dict[str, ThesisTemplate] = {
    "platform_rollup": ThesisTemplate(
        name="Platform + tuck-ins",
        description=(
            "Buy a sub-scale platform, standardize the back-office, "
            "execute programmatic M&A in a fragmented subsector."
        ),
        opening_paragraph=(
            "We're underwriting a {subsector} platform at {entry_multiple:.2f}x "
            "with a pipeline of {n_addons} tuck-ins over {hold_years:.0f} years. "
            "The bet is multiple-arbitrage on sub-scale targets plus "
            "back-office consolidation."
        ),
        bull_case_framing=(
            "Fragmented market, clear add-on pipeline, standardized "
            "RCM/G&A extracts 200-300 bps of margin. Exit to a strategic "
            "or upmarket sponsor at a scale premium."
        ),
        bear_case_framing=(
            "Integration bandwidth runs out; synergies miss by 30-40%; "
            "bolt-ons don't fit cultural or systems-wise; exit multiple "
            "doesn't re-rate."
        ),
        lever_priority=[
            "standardize RCM platform",
            "consolidate GPO / procurement",
            "unified EHR + billing",
            "shared service center build",
            "acquisition integration officer",
        ],
        partner_questions=[
            "Who's the integration officer, hired by when?",
            "What's the first-year tuck-in pipeline — 3 named targets?",
            "What's the back-office cost baseline and target?",
            "Where does the exit-multiple premium come from?",
            "What's the integration-delay scenario's MOIC?",
        ],
    ),
    "operational_improvement": ThesisTemplate(
        name="Operational improvement",
        description=(
            "Stable business with named operating levers — RCM, labor, "
            "service-line mix."
        ),
        opening_paragraph=(
            "{subsector} target with a credible operating plan: "
            "{denial_target}% target denial rate (vs {current_denial}%), "
            "{ar_target} AR days (vs {current_ar}), and 150-200 bps of "
            "margin expansion over the hold."
        ),
        bull_case_framing=(
            "Clear lever playbook, experienced operating partner assigned. "
            "Lever math closes the bridge even at a flat exit multiple."
        ),
        bear_case_framing=(
            "Lever realization slips to 50-60% of plan; labor rates rise; "
            "regulatory cut eats the margin lift."
        ),
        lever_priority=[
            "denial-rate reduction via front-end edits",
            "AR aging diagnosis + workflow",
            "labor productivity benchmarking",
            "service-line margin mix",
            "payer contracting refresh",
        ],
        partner_questions=[
            "Name the denial-program owner and the milestone plan.",
            "What's the denial reason-code concentration?",
            "What's the AR-days reduction timing and what capex does it need?",
            "What does MOIC look like at 60% lever realization?",
            "Do we have the operating partner allocated?",
        ],
    ),
    "scale_margin": ThesisTemplate(
        name="Scale + margin",
        description=(
            "Volume-driven expansion with fixed-cost leverage producing "
            "margin lift."
        ),
        opening_paragraph=(
            "{subsector} target with volume momentum — {rev_growth}% revenue "
            "CAGR modeled, producing {margin_exp} bps of margin expansion "
            "from fixed-cost leverage."
        ),
        bull_case_framing=(
            "Market tailwind + sticky customer base + operating leverage."
        ),
        bear_case_framing=(
            "Volume slows; customer churn accelerates; margin expansion "
            "fails to materialize without the volume."
        ),
        lever_priority=[
            "sales pipeline discipline",
            "customer retention / NPS",
            "fixed-cost scaling",
            "pricing power validation",
        ],
        partner_questions=[
            "What's the 3yr average organic growth?",
            "What's the customer cohort retention curve?",
            "What happens to margin at flat volume?",
        ],
    ),
    "turnaround": ThesisTemplate(
        name="Turnaround",
        description=(
            "Distressed asset — sub-peer margins, named operator-CEO, "
            "90-day cash plan."
        ),
        opening_paragraph=(
            "{subsector} target at {current_margin}% EBITDA margin vs "
            "{peer_margin}% peer median. Thesis: restore to peer median "
            "over {hold_years:.0f} years via named operator-CEO."
        ),
        bull_case_framing=(
            "Fixable issues, operator-CEO identified pre-close, cash-"
            "preserved through close. Equity upside is peer-median "
            "restoration, not outperformance."
        ),
        bear_case_framing=(
            "Turnaround takes 18 months longer than planned; covenant "
            "waiver required mid-hold; operator-CEO departs."
        ),
        lever_priority=[
            "cash preservation",
            "CEO transition readiness",
            "service-line rationalization",
            "payer re-contracting",
            "labor efficiency",
        ],
        partner_questions=[
            "Who's the operator-CEO? Is hire signed?",
            "What's the 90-day cash plan?",
            "Which service lines are divested?",
            "Do we need a covenant-lite package at close?",
            "What's the fallback if turnaround fails in year 2?",
        ],
    ),
    "strategic_exit": ThesisTemplate(
        name="Strategic exit positioning",
        description=(
            "Position the asset for strategic acquisition — named acquirer "
            "profile, key capabilities built in hold."
        ),
        opening_paragraph=(
            "{subsector} target positioned for strategic exit. Build "
            "capabilities X, Y, Z during hold; position for strategic "
            "acquirers of type A, B."
        ),
        bull_case_framing=(
            "Multiple strategic acquirers with named synergy rationale; "
            "exit multiple should reflect strategic premium."
        ),
        bear_case_framing=(
            "Strategic market cools; financial-sponsor exit is the only "
            "option; premium doesn't materialize."
        ),
        lever_priority=[
            "build strategic capabilities",
            "document synergy hypotheses",
            "maintain competitive tension pre-exit",
        ],
        partner_questions=[
            "Name 3 strategic acquirers and their synergy rationale.",
            "What does the exit multiple look like without the strategic?",
            "Is there a clear-cut sponsor exit as fallback?",
        ],
    ),
    "value_based_care": ThesisTemplate(
        name="Value-based care",
        description=(
            "Lives growth + shared-savings thesis in a VBC structure."
        ),
        opening_paragraph=(
            "{subsector} VBC operator growing covered lives from "
            "{current_lives} to {target_lives} over {hold_years:.0f} years. "
            "Revenue = lives × PMPM × (1 - MLR) + shared savings."
        ),
        bull_case_framing=(
            "Lives growth is contractible; shared-savings regime is "
            "established; physician incentives aligned."
        ),
        bear_case_framing=(
            "Lives growth stalls; MLR compresses on adverse selection; "
            "shared-savings rule changes mid-hold."
        ),
        lever_priority=[
            "lives growth — contract + channel partners",
            "MLR management — clinical protocols",
            "shared-savings capture — HCC coding",
            "provider-network design",
        ],
        partner_questions=[
            "What's the lives-growth contract backlog?",
            "What's the current MLR trend?",
            "How is HCC coding tracked and audited?",
            "What's the plan if CMS changes shared-savings rules?",
        ],
    ),
}


def get_template(key: str) -> Optional[ThesisTemplate]:
    return TEMPLATES.get(key.lower().strip())


def list_templates() -> List[str]:
    return sorted(TEMPLATES.keys())


def fill_template(
    template: ThesisTemplate,
    fields: Dict[str, Any],
) -> str:
    """Fill the opening paragraph with provided fields.

    Unknown placeholders are replaced with ``{key}`` literal as-is.
    Missing placeholders get a readable default.
    """
    class _Fallback(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"
    try:
        return template.opening_paragraph.format_map(_Fallback(fields))
    except Exception:
        return template.opening_paragraph


def render_template_markdown(template: ThesisTemplate,
                             fields: Optional[Dict[str, Any]] = None) -> str:
    opening = fill_template(template, fields or {})
    parts = [
        f"# Thesis: {template.name}",
        "",
        f"_{template.description}_",
        "",
        "## Opening",
        "",
        opening,
        "",
        "## Bull case",
        "",
        template.bull_case_framing,
        "",
        "## Bear case",
        "",
        template.bear_case_framing,
        "",
        "## Lever priority",
        "",
    ]
    for lever in template.lever_priority:
        parts.append(f"- {lever}")
    parts += ["", "## Partner questions", ""]
    for i, q in enumerate(template.partner_questions, 1):
        parts.append(f"{i}. {q}")
    parts.append("")
    return "\n".join(parts)
