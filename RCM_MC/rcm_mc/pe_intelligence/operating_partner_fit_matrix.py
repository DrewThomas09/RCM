"""Operating partner fit — which ops partner helps this CEO most?

Sponsors keep a bench of operating partners — former CFOs, CEOs,
COOs, CMOs — who help portfolio companies execute. Not every
ops partner matches every portfolio CEO. Partners reflexively
think about the match.

Archetypes of ops partners:

- **Turnaround** — comes in hot when a CEO is struggling; drives
  cost-out and operational rigor.
- **Scaler** — takes a founder-led business from $50M → $200M
  revenue; systems, processes, team building.
- **Healthcare specialist** — deep clinical / regulatory / RCM
  knowledge; essential for payer-mix and coding work.
- **M&A integrator** — knows how to absorb 10+ bolt-ons without
  blowing up pro-forma.
- **Exit specialist** — pre-IPO or late-hold focus; polishes
  systems, builds the story, manages banker relationships.
- **Founder-friendly coach** — low-ego, high-experience, helps
  founder-CEOs stay effective as the business scales.

This module takes the deal archetype, CEO type, and open issues
and returns a ranked ops-partner profile list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


OPS_PARTNER_ARCHETYPES = (
    "turnaround",
    "scaler",
    "healthcare_specialist",
    "mna_integrator",
    "exit_specialist",
    "founder_coach",
)


@dataclass
class OpsPartnerMatch:
    archetype: str
    score_0_100: int
    rationale: str
    ideal_if: str


@dataclass
class OpsPartnerFitContext:
    deal_archetype: str = ""                  # from deal_archetype module
    ceo_tenure_years: float = 3.0
    ceo_is_founder: bool = False
    ceo_first_pe_experience: bool = False
    management_score_0_100: int = 70
    ebitda_trend: str = "stable"              # up / stable / down
    has_open_turnaround_issues: bool = False
    has_mna_pipeline: bool = False
    clinical_complexity_high: bool = False
    hold_quarter: int = 4


@dataclass
class OpsPartnerFitReport:
    ranked_matches: List[OpsPartnerMatch] = field(default_factory=list)
    top_pick: str = ""
    runner_up: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ranked_matches": [
                {"archetype": m.archetype, "score_0_100": m.score_0_100,
                 "rationale": m.rationale, "ideal_if": m.ideal_if}
                for m in self.ranked_matches
            ],
            "top_pick": self.top_pick,
            "runner_up": self.runner_up,
            "partner_note": self.partner_note,
        }


def _score_turnaround(ctx: OpsPartnerFitContext) -> OpsPartnerMatch:
    score = 30
    if ctx.ebitda_trend == "down":
        score += 40
    if ctx.has_open_turnaround_issues:
        score += 25
    if ctx.management_score_0_100 < 55:
        score += 10
    return OpsPartnerMatch(
        archetype="turnaround",
        score_0_100=min(100, score),
        rationale=("Best for declining EBITDA, open operating issues, "
                   "or thin management."),
        ideal_if=("ebitda_trend=down OR open turnaround issues OR "
                  "mgmt score < 55"),
    )


def _score_scaler(ctx: OpsPartnerFitContext) -> OpsPartnerMatch:
    score = 30
    if ctx.ceo_is_founder:
        score += 30
    if ctx.ebitda_trend == "up":
        score += 15
    if ctx.ceo_first_pe_experience:
        score += 10
    if ctx.hold_quarter <= 4:
        score += 10                          # early-hold work
    return OpsPartnerMatch(
        archetype="scaler",
        score_0_100=min(100, score),
        rationale=("Best for founder-led businesses going from "
                   "$50M to $200M; systems + team build-out."),
        ideal_if=("founder CEO with growing EBITDA, first time with PE"),
    )


def _score_healthcare_specialist(
    ctx: OpsPartnerFitContext,
) -> OpsPartnerMatch:
    score = 40
    if ctx.clinical_complexity_high:
        score += 35
    if ctx.deal_archetype in ("payer_mix_shift", "cmi_uplift",
                                "clinical_labor"):
        score += 20
    return OpsPartnerMatch(
        archetype="healthcare_specialist",
        score_0_100=min(100, score),
        rationale=("Clinical / regulatory / RCM depth; essential for "
                   "coding, payer mix, and quality work."),
        ideal_if=("clinical complexity OR payer-mix / CMI uplift "
                  "archetype"),
    )


def _score_mna_integrator(
    ctx: OpsPartnerFitContext,
) -> OpsPartnerMatch:
    score = 30
    if ctx.has_mna_pipeline:
        score += 35
    if ctx.deal_archetype in ("roll_up", "consolidation"):
        score += 25
    if ctx.hold_quarter <= 8:
        score += 5
    return OpsPartnerMatch(
        archetype="mna_integrator",
        score_0_100=min(100, score),
        rationale=("Integration PMO + playbook; essential for "
                   "roll-up platforms with active pipeline."),
        ideal_if="active M&A pipeline + roll-up archetype",
    )


def _score_exit_specialist(
    ctx: OpsPartnerFitContext,
) -> OpsPartnerMatch:
    score = 20
    if ctx.hold_quarter >= 8:
        score += 30
    if ctx.ebitda_trend in ("up", "stable"):
        score += 15
    if ctx.management_score_0_100 >= 70:
        score += 10
    return OpsPartnerMatch(
        archetype="exit_specialist",
        score_0_100=min(100, score),
        rationale=("Polishes systems, builds the story, manages "
                   "banker process — best in hold year 3+."),
        ideal_if="hold quarter ≥ 8 with stable/up EBITDA",
    )


def _score_founder_coach(
    ctx: OpsPartnerFitContext,
) -> OpsPartnerMatch:
    score = 25
    if ctx.ceo_is_founder and ctx.ceo_first_pe_experience:
        score += 40
    elif ctx.ceo_is_founder:
        score += 25
    if ctx.management_score_0_100 >= 65:
        score += 10
    return OpsPartnerMatch(
        archetype="founder_coach",
        score_0_100=min(100, score),
        rationale=("Low-ego senior coach; keeps founder effective as "
                   "the business scales."),
        ideal_if="first-time-with-PE founder CEO",
    )


BUILDERS = {
    "turnaround": _score_turnaround,
    "scaler": _score_scaler,
    "healthcare_specialist": _score_healthcare_specialist,
    "mna_integrator": _score_mna_integrator,
    "exit_specialist": _score_exit_specialist,
    "founder_coach": _score_founder_coach,
}


def match_ops_partners(
    ctx: OpsPartnerFitContext,
) -> OpsPartnerFitReport:
    matches = [b(ctx) for b in BUILDERS.values()]
    matches.sort(key=lambda m: m.score_0_100, reverse=True)
    top = matches[0]
    runner_up = matches[1] if len(matches) > 1 else None

    if top.score_0_100 < 50:
        note = (f"No strong ops-partner fit surfaces (top = "
                f"{top.archetype} at {top.score_0_100}). The bench "
                "isn't purpose-built for this deal's profile; "
                "consider external recruitment.")
    elif runner_up and (top.score_0_100 - runner_up.score_0_100) <= 10:
        note = (f"Close call between {top.archetype} and "
                f"{runner_up.archetype}. Pick {top.archetype} for the "
                "primary role; use {runner_up.archetype} as an "
                "advisory role.")
    else:
        note = (f"{top.archetype} is the clear fit "
                f"({top.score_0_100}/100). Runner-up "
                f"{runner_up.archetype} "
                f"({runner_up.score_0_100}/100).")

    return OpsPartnerFitReport(
        ranked_matches=matches,
        top_pick=top.archetype,
        runner_up=runner_up.archetype if runner_up else "",
        partner_note=note,
    )


def render_ops_partner_match_markdown(
    r: OpsPartnerFitReport,
) -> str:
    lines = [
        "# Operating partner fit matrix",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Top pick: **{r.top_pick}**",
        f"- Runner-up: {r.runner_up}",
        "",
        "| Archetype | Score | Ideal if | Rationale |",
        "|---|---:|---|---|",
    ]
    for m in r.ranked_matches:
        lines.append(
            f"| {m.archetype} | {m.score_0_100} | {m.ideal_if} | "
            f"{m.rationale} |"
        )
    return "\n".join(lines)
