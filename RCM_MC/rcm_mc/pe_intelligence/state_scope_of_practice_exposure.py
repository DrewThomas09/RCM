"""State scope-of-practice + CPOM + non-compete + MSO exposure.

Partner statement: "Physician deal footprint tells
you most of the regulatory burden. NPs and PAs
practicing full-scope in one state can't in another.
CPOM-strict states force an MSO/PC structure that
adds complexity and legal risk. Non-compete bans
(CA, OK, MN, ND) make physician retention harder.
Before I get to the tax structure, I want the state
map — what can we legally do in each state this deal
operates in?"

Distinct from:
- `multi_state_regulatory_complexity_scorer` —
  general complexity scoring.
- `medicaid_state_exposure_map` — Medicaid tier map.
- `reps_warranties_scope_negotiator` — R&W scope.

This module gives a **per-state regulatory posture**
across 4 axes:
1. NP/PA full-practice authority (yes / reduced /
   restricted)
2. CPOM (corporate practice of medicine) strictness
3. Non-compete enforceability
4. MSO/PC model required

### Output

For each state in the deal footprint:
- posture across 4 axes
- per-state risk flags
- aggregate exposure (friendly / moderate /
  restrictive / heterogeneous)
- partner note on structural implications
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Per-state postures. Covers major deal-flow states.
# "full_practice" = NP/PA can practice independently
# "reduced" = collaborative agreement required for some acts
# "restricted" = supervisory physician required for most acts
#
# CPOM: "strict" = requires MSO/PC; "moderate" = some
# scope for corporate ownership; "lenient" = no CPOM.
#
# Non-compete: "ban" (CA/MN/ND/OK), "narrow" (limited),
# "enforceable" (standard), "varies" (case-law).
STATE_POSTURES: Dict[str, Dict[str, str]] = {
    "CA": {
        "np_pa_scope": "full_practice",
        "cpom": "strict",
        "noncompete": "ban",
    },
    "NY": {
        "np_pa_scope": "full_practice",
        "cpom": "strict",
        "noncompete": "varies",
    },
    "TX": {
        "np_pa_scope": "reduced",
        "cpom": "strict",
        "noncompete": "narrow",
    },
    "FL": {
        "np_pa_scope": "reduced",
        "cpom": "lenient",
        "noncompete": "enforceable",
    },
    "IL": {
        "np_pa_scope": "reduced",
        "cpom": "strict",
        "noncompete": "narrow",
    },
    "PA": {
        "np_pa_scope": "reduced",
        "cpom": "moderate",
        "noncompete": "enforceable",
    },
    "OH": {
        "np_pa_scope": "reduced",
        "cpom": "lenient",
        "noncompete": "enforceable",
    },
    "GA": {
        "np_pa_scope": "restricted",
        "cpom": "moderate",
        "noncompete": "enforceable",
    },
    "NC": {
        "np_pa_scope": "reduced",
        "cpom": "moderate",
        "noncompete": "enforceable",
    },
    "MI": {
        "np_pa_scope": "reduced",
        "cpom": "strict",
        "noncompete": "narrow",
    },
    "NJ": {
        "np_pa_scope": "reduced",
        "cpom": "strict",
        "noncompete": "enforceable",
    },
    "AZ": {
        "np_pa_scope": "full_practice",
        "cpom": "lenient",
        "noncompete": "enforceable",
    },
    "CO": {
        "np_pa_scope": "full_practice",
        "cpom": "moderate",
        "noncompete": "narrow",
    },
    "WA": {
        "np_pa_scope": "full_practice",
        "cpom": "moderate",
        "noncompete": "narrow",
    },
    "MN": {
        "np_pa_scope": "full_practice",
        "cpom": "moderate",
        "noncompete": "ban",
    },
    "MA": {
        "np_pa_scope": "full_practice",
        "cpom": "moderate",
        "noncompete": "narrow",
    },
    "OR": {
        "np_pa_scope": "full_practice",
        "cpom": "moderate",
        "noncompete": "narrow",
    },
    "ND": {
        "np_pa_scope": "full_practice",
        "cpom": "lenient",
        "noncompete": "ban",
    },
    "OK": {
        "np_pa_scope": "reduced",
        "cpom": "lenient",
        "noncompete": "ban",
    },
}


def _cpom_needs_mso_pc(cpom: str) -> bool:
    return cpom in {"strict", "moderate"}


@dataclass
class StateFootprint:
    state: str
    share_of_npr_pct: float = 0.0


@dataclass
class ScopeOfPracticeInputs:
    footprint: List[StateFootprint] = field(
        default_factory=list)
    is_physician_owned: bool = True


@dataclass
class StateExposure:
    state: str
    in_catalog: bool
    share_of_npr_pct: float
    np_pa_scope: str
    cpom: str
    noncompete: str
    needs_mso_pc_structure: bool
    flags: List[str] = field(default_factory=list)


@dataclass
class ScopeOfPracticeReport:
    state_exposures: List[StateExposure] = field(
        default_factory=list)
    weighted_mso_pc_required_pct: float = 0.0
    weighted_noncompete_ban_pct: float = 0.0
    weighted_full_practice_np_pa_pct: float = 0.0
    verdict: str = "moderate"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_exposures": [
                {"state": s.state,
                 "in_catalog": s.in_catalog,
                 "share_of_npr_pct": s.share_of_npr_pct,
                 "np_pa_scope": s.np_pa_scope,
                 "cpom": s.cpom,
                 "noncompete": s.noncompete,
                 "needs_mso_pc_structure":
                     s.needs_mso_pc_structure,
                 "flags": s.flags}
                for s in self.state_exposures
            ],
            "weighted_mso_pc_required_pct":
                self.weighted_mso_pc_required_pct,
            "weighted_noncompete_ban_pct":
                self.weighted_noncompete_ban_pct,
            "weighted_full_practice_np_pa_pct":
                self.weighted_full_practice_np_pa_pct,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def analyze_scope_of_practice(
    inputs: ScopeOfPracticeInputs,
) -> ScopeOfPracticeReport:
    if not inputs.footprint:
        return ScopeOfPracticeReport(
            partner_note=(
                "No state footprint — map deal sites to "
                "states before analyzing scope-of-"
                "practice."),
        )

    exposures: List[StateExposure] = []
    mso_pc_share = 0.0
    noncompete_ban_share = 0.0
    full_practice_share = 0.0

    for fp in inputs.footprint:
        state = fp.state.upper()
        book = STATE_POSTURES.get(state)
        if book is None:
            exposures.append(StateExposure(
                state=state,
                in_catalog=False,
                share_of_npr_pct=round(
                    fp.share_of_npr_pct, 4),
                np_pa_scope="unknown",
                cpom="unknown",
                noncompete="unknown",
                needs_mso_pc_structure=False,
                flags=["state not in catalog"],
            ))
            continue
        needs_mso_pc = _cpom_needs_mso_pc(book["cpom"])
        flags: List[str] = []
        if book["cpom"] == "strict" and inputs.is_physician_owned:
            flags.append(
                "CPOM-strict state; MSO/PC model "
                "required")
        if book["noncompete"] == "ban":
            flags.append(
                "Non-compete ban — physician "
                "retention requires economic "
                "alignment, not legal bond")
        if book["np_pa_scope"] == "full_practice":
            flags.append(
                "NP/PA full-practice — mid-level "
                "leverage feasible if specialty allows")
        exposures.append(StateExposure(
            state=state,
            in_catalog=True,
            share_of_npr_pct=round(
                fp.share_of_npr_pct, 4),
            np_pa_scope=book["np_pa_scope"],
            cpom=book["cpom"],
            noncompete=book["noncompete"],
            needs_mso_pc_structure=needs_mso_pc,
            flags=flags,
        ))
        if needs_mso_pc:
            mso_pc_share += fp.share_of_npr_pct
        if book["noncompete"] == "ban":
            noncompete_ban_share += fp.share_of_npr_pct
        if book["np_pa_scope"] == "full_practice":
            full_practice_share += fp.share_of_npr_pct

    total_share = sum(
        fp.share_of_npr_pct for fp in inputs.footprint)
    unknown_share = sum(
        e.share_of_npr_pct
        for e in exposures if not e.in_catalog
    )
    known_share = max(0.0, total_share - unknown_share)

    # Classify verdict
    if mso_pc_share >= 0.50 and noncompete_ban_share >= 0.20:
        verdict = "restrictive"
        note = (
            f"{mso_pc_share:.0%} of revenue in CPOM-"
            f"strict states + "
            f"{noncompete_ban_share:.0%} in non-"
            "compete-ban states. MSO/PC structure "
            "mandatory; retention strategy must be "
            "equity-aligned, not legally bonded."
        )
    elif mso_pc_share >= 0.50:
        verdict = "mso_pc_required"
        note = (
            f"{mso_pc_share:.0%} of revenue in CPOM-"
            "strict/moderate states — MSO/PC model "
            "mandatory. Pre-validate structure in R&W; "
            "state-specific counsel needed."
        )
    elif noncompete_ban_share >= 0.30:
        verdict = "retention_critical"
        note = (
            f"{noncompete_ban_share:.0%} of revenue "
            "in non-compete-ban states. Lose the top "
            "physician and lose the book; retention "
            "must be through rollover equity, earn-out, "
            "or comp alignment."
        )
    elif known_share < 0.50:
        verdict = "heterogeneous"
        note = (
            f"Only {known_share:.0%} of footprint in "
            "catalog states. Deal spans "
            "less-studied jurisdictions; add state-"
            "specific counsel time to diligence."
        )
    else:
        verdict = "friendly"
        note = (
            "State footprint is structurally friendly — "
            "CPOM lenience and enforceable non-competes "
            "support standard PE structure."
        )

    return ScopeOfPracticeReport(
        state_exposures=exposures,
        weighted_mso_pc_required_pct=round(
            mso_pc_share, 4),
        weighted_noncompete_ban_pct=round(
            noncompete_ban_share, 4),
        weighted_full_practice_np_pa_pct=round(
            full_practice_share, 4),
        verdict=verdict,
        partner_note=note,
    )


def render_scope_of_practice_markdown(
    r: ScopeOfPracticeReport,
) -> str:
    lines = [
        "# State scope-of-practice exposure",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- CPOM MSO/PC required: "
        f"{r.weighted_mso_pc_required_pct:.0%}",
        f"- Non-compete ban states: "
        f"{r.weighted_noncompete_ban_pct:.0%}",
        f"- NP/PA full-practice share: "
        f"{r.weighted_full_practice_np_pa_pct:.0%}",
        "",
        "| State | Share | NP/PA scope | CPOM | "
        "Non-compete | MSO/PC needed |",
        "|---|---|---|---|---|---|",
    ]
    for s in r.state_exposures:
        lines.append(
            f"| {s.state} | "
            f"{s.share_of_npr_pct:.0%} | "
            f"{s.np_pa_scope} | {s.cpom} | "
            f"{s.noncompete} | "
            f"{'yes' if s.needs_mso_pc_structure else 'no'} |"
        )
    return "\n".join(lines)
