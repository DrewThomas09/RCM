"""Multi-state regulatory complexity — operating footprint drag.

Partner statement: "A deal operating in 5 states is not
5x the complexity — it's 12x. Each state has its own
CON, licensure transfer, MSO rules, non-compete law,
and provider tax. Roll-up theses that 'expand into
adjacent states' often don't price in the compliance
drag."

Each state adds:
- Licensure transfer (CHOW filing, DEA, state Medicaid
  provider number).
- CON (certificate of need) in 35 states for select
  services.
- Non-compete enforceability varies (fully enforceable
  / limited / void).
- Professional-corporation / MSO structure
  requirements.
- Aggressive state AG antitrust review.
- Provider taxes on healthcare revenue.

### 6 dimensions

1. **state_count** — more states = more compliance
   overhead (sub-linear scaling).
2. **con_state_count** — states with CON for the
   asset's service line.
3. **noncompete_void_state_count** — CA / ND / OK /
   MN / CO / etc. where non-competes are void.
4. **mso_structure_required_count** — corporate
   practice of medicine (CPOM) states requiring MSO.
5. **aggressive_ag_count** — CA / NY / WA / MA.
6. **provider_tax_state_count** — CA / NY / OR / TX /
   MI / WA.

### Tier ladder

- **simple** — single-state or ≤ 2 states + no special
  issues.
- **moderate** — 3-4 states OR CON / non-compete /
  MSO issue in ≥ 2 states.
- **complex** — 5-7 states OR ≥ 2 categories of
  state-level issues.
- **very_complex** — 8+ states OR ≥ 3 categories in
  overlapping states.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


# State-level reference data — partner-judgment
# categorizations (simplified for modeling).
CON_STATES = {
    "AL", "AK", "CT", "DE", "DC", "FL", "GA", "HI", "IL",
    "IA", "KY", "ME", "MD", "MA", "MI", "MS", "MO", "MT",
    "NV", "NH", "NJ", "NY", "NC", "OH", "OK", "OR", "RI",
    "SC", "TN", "VT", "VA", "WA", "WV",
}
NONCOMPETE_VOID_STATES = {
    "CA", "ND", "OK", "MN", "CO",
}
MSO_STATES = {
    "CA", "NY", "NJ", "IL", "TX", "MI", "OH", "PA", "WA",
    "CO",
}
AGGRESSIVE_AG_STATES = {"CA", "NY", "WA", "MA"}
PROVIDER_TAX_STATES = {"CA", "NY", "OR", "TX", "MI", "WA"}


@dataclass
class MultiStateInputs:
    operating_states: List[str] = field(default_factory=list)
    service_line_triggers_con: bool = False
    asset_type_requires_mso: bool = True  # most provider assets do


@dataclass
class StateCategory:
    category: str
    state_count: int
    states: List[str]
    partner_comment: str


@dataclass
class MultiStateReport:
    tier: str
    state_count: int
    category_count: int
    categories: List[StateCategory] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "state_count": self.state_count,
            "category_count": self.category_count,
            "categories": [
                {"category": c.category,
                 "state_count": c.state_count,
                 "states": list(c.states),
                 "partner_comment": c.partner_comment}
                for c in self.categories
            ],
            "partner_note": self.partner_note,
        }


def score_multi_state_complexity(
    inputs: MultiStateInputs,
) -> MultiStateReport:
    states_upper = {s.upper() for s in inputs.operating_states}
    state_count = len(states_upper)

    categories: List[StateCategory] = []

    # CON applicable.
    if inputs.service_line_triggers_con:
        con_in = sorted(states_upper & CON_STATES)
        categories.append(StateCategory(
            category="con_requirement",
            state_count=len(con_in),
            states=con_in,
            partner_comment=(
                f"{len(con_in)} state(s) require CON for "
                "this service — material entry friction + "
                "months-long filing cycle."
                if con_in else
                "No CON requirement in operating states."
            ),
        ))

    # Non-compete void states.
    nc_void = sorted(states_upper & NONCOMPETE_VOID_STATES)
    categories.append(StateCategory(
        category="noncompete_void",
        state_count=len(nc_void),
        states=nc_void,
        partner_comment=(
            f"{len(nc_void)} state(s) void non-competes: "
            f"{', '.join(nc_void)}. Plan retention via "
            "deferred-comp clawback."
            if nc_void else
            "No non-compete void states."
        ),
    ))

    # MSO states.
    if inputs.asset_type_requires_mso:
        mso_in = sorted(states_upper & MSO_STATES)
        categories.append(StateCategory(
            category="mso_structure_required",
            state_count=len(mso_in),
            states=mso_in,
            partner_comment=(
                f"{len(mso_in)} state(s) require MSO / "
                "friendly-PC structure: "
                f"{', '.join(mso_in)}. Legal complexity "
                "compounds across states."
                if mso_in else
                "No MSO requirement."
            ),
        ))

    # Aggressive AGs.
    ag = sorted(states_upper & AGGRESSIVE_AG_STATES)
    categories.append(StateCategory(
        category="aggressive_ag_review",
        state_count=len(ag),
        states=ag,
        partner_comment=(
            f"{len(ag)} aggressive state AG "
            f"jurisdiction(s): {', '.join(ag)}. Expect "
            "state-level antitrust review on top of FTC."
            if ag else
            "No aggressive AG jurisdictions."
        ),
    ))

    # Provider tax.
    pt = sorted(states_upper & PROVIDER_TAX_STATES)
    categories.append(StateCategory(
        category="provider_tax",
        state_count=len(pt),
        states=pt,
        partner_comment=(
            f"{len(pt)} provider-tax state(s): "
            f"{', '.join(pt)}. 2-4% revenue tax exposure "
            "per state."
            if pt else
            "No provider-tax states."
        ),
    ))

    # Count categories with ≥ 2 state-overlaps as "issue-cluster".
    issue_categories = sum(
        1 for c in categories if c.state_count >= 2
    )

    # Tier ladder.
    if state_count >= 8 or issue_categories >= 3:
        tier = "very_complex"
        note = (
            f"{state_count} state(s) across {issue_categories} "
            "issue-categories. Partner: retain multi-state "
            "regulatory counsel pre-LOI; price compliance "
            "drag explicitly."
        )
    elif state_count >= 5 or issue_categories >= 2:
        tier = "complex"
        note = (
            f"{state_count} state(s); "
            f"{issue_categories} material issue-category. "
            "Partner: budget for state-by-state legal "
            "workstream."
        )
    elif state_count >= 3 or issue_categories >= 1:
        tier = "moderate"
        note = (
            f"{state_count} state(s); "
            f"{issue_categories} issue-category. Standard "
            "multi-state diligence."
        )
    else:
        tier = "simple"
        note = (
            f"{state_count} state(s); minimal multi-state "
            "complexity."
        )

    return MultiStateReport(
        tier=tier,
        state_count=state_count,
        category_count=issue_categories,
        categories=categories,
        partner_note=note,
    )


def render_multi_state_markdown(
    r: MultiStateReport,
) -> str:
    lines = [
        "# Multi-state regulatory complexity",
        "",
        f"**Tier:** `{r.tier}`",
        "",
        f"_{r.partner_note}_",
        "",
        f"- State count: {r.state_count}",
        f"- Material issue-categories: {r.category_count}",
        "",
        "| Category | States | Partner comment |",
        "|---|---|---|",
    ]
    for c in r.categories:
        lines.append(
            f"| {c.category} | "
            f"{', '.join(c.states) or '—'} | "
            f"{c.partner_comment} |"
        )
    return "\n".join(lines)
