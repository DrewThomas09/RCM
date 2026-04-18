"""Red-team review — systematically attack the bull case.

Before a partner signs off, they often conduct a mini red-team
exercise: take the thesis, put on the adversarial hat, find the
weakest link, and force the deal team to defend it.

This module produces a structured red-team review of a
:class:`PartnerReview`:

- Three strongest attacks on the bull case.
- Three alternative narratives a sponsor-side opponent would tell.
- Three break-the-deal scenarios.
- An "if I had to pass, why?" paragraph.

Complement to `narrative_styles.compose_skeptic_view` — this module
is longer-form, multi-attack-vector.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .heuristics import SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM
from .partner_review import PartnerReview
from .reasonableness import (
    VERDICT_IMPLAUSIBLE,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
)


@dataclass
class RedTeamAttack:
    vector: str                       # "valuation" | "operating" | "regulatory" | "structure"
    thesis_challenged: str
    attack_statement: str
    proof_needed: str
    severity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vector": self.vector,
            "thesis_challenged": self.thesis_challenged,
            "attack_statement": self.attack_statement,
            "proof_needed": self.proof_needed,
            "severity": self.severity,
        }


@dataclass
class RedTeamReport:
    deal_id: str
    top_attacks: List[RedTeamAttack] = field(default_factory=list)
    alternative_narratives: List[str] = field(default_factory=list)
    break_scenarios: List[str] = field(default_factory=list)
    pass_rationale: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "top_attacks": [a.to_dict() for a in self.top_attacks],
            "alternative_narratives": list(self.alternative_narratives),
            "break_scenarios": list(self.break_scenarios),
            "pass_rationale": self.pass_rationale,
            "partner_note": self.partner_note,
        }


# ── Attack generators ───────────────────────────────────────────────

def _valuation_attack(review: PartnerReview) -> Optional[RedTeamAttack]:
    exit_band = next((b for b in review.reasonableness_checks
                      if b.metric == "exit_multiple"), None)
    if exit_band is None or exit_band.verdict not in (VERDICT_STRETCH,
                                                       VERDICT_OUT_OF_BAND,
                                                       VERDICT_IMPLAUSIBLE):
        return None
    return RedTeamAttack(
        vector="valuation",
        thesis_challenged="Exit multiple assumption",
        attack_statement=(
            "Your exit multiple assumes buyer-universe appetite that may "
            "not exist in 5 years. The 2022 rate environment showed how "
            "fast healthcare multiples compress."),
        proof_needed=("Name three closed comps at or above the modeled "
                      "multiple with comparable payer mix."),
        severity="high",
    )


def _operating_attack(review: PartnerReview) -> Optional[RedTeamAttack]:
    lever_bands = [b for b in review.reasonableness_checks
                   if b.metric.startswith("lever:")
                   and b.verdict in (VERDICT_STRETCH, VERDICT_OUT_OF_BAND,
                                     VERDICT_IMPLAUSIBLE)]
    if not lever_bands:
        return None
    return RedTeamAttack(
        vector="operating",
        thesis_challenged="Lever realization pace",
        attack_statement=(
            "Lever ramp is aggressive versus peer benchmark. Half of "
            "RCM programs we've seen deliver 50-60% of plan; what's "
            "different here?"),
        proof_needed=("Point to a named playbook + capex commitment + "
                      "operating-partner assigned with prior lever experience."),
        severity="high",
    )


def _regulatory_attack(review: PartnerReview) -> Optional[RedTeamAttack]:
    ctx = review.context_summary or {}
    mix = ctx.get("payer_mix") or {}
    norm = {str(k).lower(): float(v) for k, v in mix.items()
            if v is not None}
    total = sum(norm.values())
    if total > 1.5:
        norm = {k: v / 100.0 for k, v in norm.items()}
    govt = norm.get("medicare", 0.0) + norm.get("medicaid", 0.0)
    if govt < 0.50:
        return None
    return RedTeamAttack(
        vector="regulatory",
        thesis_challenged="Government-payer rate stability",
        attack_statement=(
            f"{govt*100:.0f}% government payer mix leaves this deal exposed "
            "to every CMS rule cycle. A 100 bps IPPS trim inside hold is "
            "a realistic scenario."),
        proof_needed=("Model a 100 bps Medicare cut in year 2 without the "
                      "lever plan. Does the deal still clear the hurdle?"),
        severity="medium",
    )


def _structure_attack(review: PartnerReview) -> Optional[RedTeamAttack]:
    leverage = (review.context_summary or {}).get("leverage_multiple")
    if leverage is None or leverage < 5.5:
        return None
    return RedTeamAttack(
        vector="structure",
        thesis_challenged="Capital structure resilience",
        attack_statement=(
            f"At {leverage:.1f}x leverage you're one bad quarter from "
            "a waiver conversation. The lender won't be nice — they "
            "haven't been nice for two years."),
        proof_needed=("Show covenant-headroom under 90% EBITDA scenario "
                      "for eight quarters. Does any quarter breach?"),
        severity="high",
    )


def _concentration_attack(review: PartnerReview) -> Optional[RedTeamAttack]:
    critical = [h for h in review.heuristic_hits if h.severity == SEV_CRITICAL]
    if not critical:
        return None
    return RedTeamAttack(
        vector="concentration",
        thesis_challenged="Critical-risk concentration",
        attack_statement=(
            f"{len(critical)} critical item(s) flagged. Each is deal-"
            "breaking in isolation."),
        proof_needed=("Document explicit mitigation + residual-risk "
                      "acceptance at IC."),
        severity="high",
    )


# ── Orchestrator ────────────────────────────────────────────────────

def build_red_team_report(review: PartnerReview) -> RedTeamReport:
    attacks = [
        fn(review) for fn in (
            _valuation_attack, _operating_attack, _regulatory_attack,
            _structure_attack, _concentration_attack,
        )
    ]
    attacks = [a for a in attacks if a is not None]
    # Sort by severity.
    rank = {"high": 0, "medium": 1, "low": 2}
    attacks.sort(key=lambda a: rank.get(a.severity, 3))
    attacks = attacks[:4]

    alt_narratives: List[str] = []
    if any(a.vector == "valuation" for a in attacks):
        alt_narratives.append(
            "Sponsor-side alternative: 'This is a buy at the right "
            "multiple, not at this one.'"
        )
    if any(a.vector == "operating" for a in attacks):
        alt_narratives.append(
            "Sponsor-side alternative: 'The lever plan is the alpha. "
            "If we don't get 80%+ of lever realization, the deal is "
            "a market-beta bet.'"
        )
    if any(a.vector == "regulatory" for a in attacks):
        alt_narratives.append(
            "Sponsor-side alternative: 'CMS is the third investor here, "
            "and they get a say whether we like it or not.'"
        )

    break_scenarios: List[str] = []
    for a in attacks[:3]:
        if a.vector == "valuation":
            break_scenarios.append(
                "Exit multiples compress 2+ turns and strategic universe "
                "disappears.")
        elif a.vector == "operating":
            break_scenarios.append(
                "Lever realization lands at 50% of plan; EBITDA at exit "
                "is flat.")
        elif a.vector == "regulatory":
            break_scenarios.append(
                "CMS cuts Medicare rate 150 bps in year 2, unwinding the "
                "margin plan.")
        elif a.vector == "structure":
            break_scenarios.append(
                "Covenant breach in year 2 → waiver → rescue equity.")

    # Pass rationale
    if not attacks:
        pass_rationale = ("No obvious reason to pass — this deal survives "
                          "the red-team exercise cleanly.")
    elif len(attacks) >= 3:
        pass_rationale = (
            "I'd pass if the team can't answer three specific questions: "
            + " / ".join(a.proof_needed for a in attacks[:3])
        )
    else:
        pass_rationale = (
            "I'd pass if: " + " OR ".join(a.proof_needed for a in attacks)
        )

    high_count = sum(1 for a in attacks if a.severity == "high")
    if high_count >= 3:
        note = "Red-team exercise surfaces material weaknesses — address each before IC."
    elif high_count >= 1:
        note = "Red-team exercise surfaces weaknesses — prepare responses for IC."
    else:
        note = "Red-team exercise is light — deal survives the adversarial take."

    return RedTeamReport(
        deal_id=review.deal_id or review.deal_name or "(unnamed)",
        top_attacks=attacks,
        alternative_narratives=alt_narratives,
        break_scenarios=break_scenarios,
        pass_rationale=pass_rationale,
        partner_note=note,
    )


def render_red_team_markdown(report: RedTeamReport) -> str:
    lines = [
        f"# Red-team review — {report.deal_id}",
        "",
        f"_{report.partner_note}_",
        "",
        "## Top attacks",
        "",
    ]
    for a in report.top_attacks:
        lines.append(f"- **[{a.severity}] {a.thesis_challenged} ({a.vector}):** "
                     f"{a.attack_statement}")
        lines.append(f"  - _Proof needed:_ {a.proof_needed}")
    if report.alternative_narratives:
        lines.extend(["", "## Alternative narratives", ""])
        for n in report.alternative_narratives:
            lines.append(f"- {n}")
    if report.break_scenarios:
        lines.extend(["", "## Break-the-deal scenarios", ""])
        for b in report.break_scenarios:
            lines.append(f"- {b}")
    lines.extend(["", "## Pass rationale", "", report.pass_rationale])
    return "\n".join(lines)
