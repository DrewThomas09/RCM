"""Add-on fit scorer — should we buy this specific bolt-on?

Different from `ma_pipeline` (which tracks the pipeline generally)
and `ma_integration_scoreboard` (which scores post-close
integration progress). This is the pre-close question: for THIS
specific bolt-on target, is the fit right for THIS platform?

Scored across four dimensions:

- **Strategic fit** — does it extend capability, geography, or
  scale in a direction the platform already needs?
- **Financial fit** — multiple paid vs accretion math, synergy
  math, purchase-price-accretion payback.
- **Integration fit** — compatible ERP, culture signals, physician
  alignment, clinical-leadership reporting lines.
- **Execution fit** — team bandwidth, capex headroom, can we
  close in the timeline the platform needs.

Output: total score 0-100, named top-3 concerns, pass/proceed/
re-evaluate recommendation, and partner note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AddOnContext:
    target_name: str = "Target"
    target_ebitda_m: float = 0.0
    target_revenue_m: float = 0.0
    target_growth_pct: float = 0.05
    target_multiple_paid: float = 8.0
    # Platform state:
    platform_ebitda_m: float = 0.0
    platform_multiple_last_marked: float = 11.0
    platform_open_integrations: int = 0
    platform_mgmt_bandwidth_0_100: int = 70
    platform_capex_headroom_m: float = 10.0
    # Strategic signals:
    extends_geography: bool = False
    extends_service_line: bool = False
    extends_scale_in_existing_line: bool = True
    physician_alignment: bool = True
    erp_compatible: bool = True
    # Execution signals:
    expected_synergies_pct_target_ebitda: float = 0.10
    months_to_close_expected: int = 4
    expected_integration_months: int = 12


@dataclass
class FitDimension:
    dimension: str
    score_0_100: int
    concerns: List[str] = field(default_factory=list)


@dataclass
class AddOnFitReport:
    target_name: str
    overall_score_0_100: int
    strategic: FitDimension
    financial: FitDimension
    integration: FitDimension
    execution: FitDimension
    recommendation: str                    # "proceed" / "re_evaluate" / "pass"
    top_concerns: List[str]
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_name": self.target_name,
            "overall_score_0_100": self.overall_score_0_100,
            "strategic": {
                "dimension": self.strategic.dimension,
                "score_0_100": self.strategic.score_0_100,
                "concerns": list(self.strategic.concerns),
            },
            "financial": {
                "dimension": self.financial.dimension,
                "score_0_100": self.financial.score_0_100,
                "concerns": list(self.financial.concerns),
            },
            "integration": {
                "dimension": self.integration.dimension,
                "score_0_100": self.integration.score_0_100,
                "concerns": list(self.integration.concerns),
            },
            "execution": {
                "dimension": self.execution.dimension,
                "score_0_100": self.execution.score_0_100,
                "concerns": list(self.execution.concerns),
            },
            "recommendation": self.recommendation,
            "top_concerns": list(self.top_concerns),
            "partner_note": self.partner_note,
        }


def _score_strategic(ctx: AddOnContext) -> FitDimension:
    score = 40
    concerns: List[str] = []
    if ctx.extends_geography:
        score += 15
    if ctx.extends_service_line:
        score += 20
    if ctx.extends_scale_in_existing_line:
        score += 20
    if not (ctx.extends_geography or ctx.extends_service_line
            or ctx.extends_scale_in_existing_line):
        concerns.append(
            "Target doesn't clearly extend geography, service line, "
            "or scale. The strategic rationale needs to be more "
            "than 'cheap EBITDA.'")
    if ctx.target_growth_pct < 0.02:
        score -= 5
        concerns.append(
            f"Target growth {ctx.target_growth_pct*100:.1f}% is thin "
            "— adding low-growth bolt-ons dilutes platform CAGR.")
    return FitDimension("strategic", max(0, min(100, score)), concerns)


def _score_financial(ctx: AddOnContext) -> FitDimension:
    score = 50
    concerns: List[str] = []
    # Multiple arbitrage: target multiple vs platform multiple.
    arbitrage = ctx.platform_multiple_last_marked - ctx.target_multiple_paid
    if arbitrage >= 3.0:
        score += 25
    elif arbitrage >= 1.0:
        score += 10
    elif arbitrage <= 0:
        score -= 15
        concerns.append(
            f"Paying {ctx.target_multiple_paid:.1f}x vs platform "
            f"marked at {ctx.platform_multiple_last_marked:.1f}x "
            "— no multiple arbitrage. Pure EBITDA addition at par.")
    if ctx.expected_synergies_pct_target_ebitda >= 0.15:
        score += 15
    elif ctx.expected_synergies_pct_target_ebitda >= 0.05:
        score += 5
    else:
        concerns.append(
            "Thin synergy story; accretion math leans only on "
            "multiple arbitrage.")
    # Target size: too small = not worth the time.
    if ctx.target_ebitda_m < 2.0:
        score -= 15
        concerns.append(
            f"Target EBITDA ${ctx.target_ebitda_m:.1f}M is too small "
            "— team-bandwidth cost often exceeds return.")
    return FitDimension("financial", max(0, min(100, score)), concerns)


def _score_integration(ctx: AddOnContext) -> FitDimension:
    score = 60
    concerns: List[str] = []
    if ctx.erp_compatible:
        score += 10
    else:
        score -= 10
        concerns.append(
            "ERP/system stack is NOT compatible — integration cost "
            "and timeline will be meaningfully higher.")
    if ctx.physician_alignment:
        score += 15
    else:
        score -= 15
        concerns.append(
            "Physician alignment at target is not confirmed. Earn-"
            "out / retention is critical in this case.")
    if ctx.expected_integration_months > 18:
        score -= 10
        concerns.append(
            f"Expected integration {ctx.expected_integration_months}mo "
            "is long — partner-watches the 18-month ceiling.")
    if ctx.platform_open_integrations >= 3:
        score -= 15
        concerns.append(
            f"{ctx.platform_open_integrations} other integrations "
            "still open at the platform — adding another taxes the "
            "PMO beyond capacity.")
    return FitDimension("integration", max(0, min(100, score)), concerns)


def _score_execution(ctx: AddOnContext) -> FitDimension:
    score = 60
    concerns: List[str] = []
    if ctx.platform_mgmt_bandwidth_0_100 < 50:
        score -= 20
        concerns.append(
            f"Management bandwidth "
            f"{ctx.platform_mgmt_bandwidth_0_100}/100 — team is "
            "already stretched. Adding a bolt-on is a stretch "
            "decision, not a financial one.")
    elif ctx.platform_mgmt_bandwidth_0_100 < 70:
        score -= 5
    if ctx.platform_capex_headroom_m < 2.0:
        score -= 15
        concerns.append(
            f"Capex headroom ${ctx.platform_capex_headroom_m:.1f}M "
            "is thin — integration capex may crowd out platform "
            "roadmap.")
    if ctx.months_to_close_expected > 6:
        score -= 5
        concerns.append(
            f"Close timeline {ctx.months_to_close_expected}mo — "
            "longer processes lose management attention.")
    return FitDimension("execution", max(0, min(100, score)), concerns)


def score_add_on(ctx: AddOnContext) -> AddOnFitReport:
    strategic = _score_strategic(ctx)
    financial = _score_financial(ctx)
    integration = _score_integration(ctx)
    execution = _score_execution(ctx)

    overall = int(round(
        0.30 * strategic.score_0_100
        + 0.30 * financial.score_0_100
        + 0.25 * integration.score_0_100
        + 0.15 * execution.score_0_100
    ))

    # Top concerns — pull up to 3 across dimensions.
    all_concerns: List[str] = []
    for d in (strategic, financial, integration, execution):
        all_concerns.extend(d.concerns)
    top_concerns = all_concerns[:3]

    if overall >= 70 and not any(d.score_0_100 < 40
                                   for d in (strategic, financial,
                                              integration, execution)):
        rec = "proceed"
        note = (f"Add-on fit is strong ({overall}/100). Proceed to "
                "LOI with standard closing conditions.")
    elif overall >= 55:
        rec = "re_evaluate"
        note = (f"Add-on is workable ({overall}/100) but has "
                f"specific concerns: "
                f"{'; '.join(top_concerns[:2]) if top_concerns else 'team-bandwidth'}. "
                "Close the specific items before bidding aggressively.")
    else:
        rec = "pass"
        note = (f"Add-on fit is weak ({overall}/100). Too many "
                "concerns across dimensions — pass and focus team "
                "on stronger targets in the pipeline.")

    return AddOnFitReport(
        target_name=ctx.target_name,
        overall_score_0_100=overall,
        strategic=strategic,
        financial=financial,
        integration=integration,
        execution=execution,
        recommendation=rec,
        top_concerns=top_concerns,
        partner_note=note,
    )


def render_add_on_fit_markdown(r: AddOnFitReport) -> str:
    lines = [
        f"# {r.target_name} — Add-on fit",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Overall score: **{r.overall_score_0_100}/100**",
        f"- Recommendation: **{r.recommendation}**",
        "",
        "| Dimension | Score | Concerns |",
        "|---|---:|---|",
    ]
    for d in (r.strategic, r.financial, r.integration, r.execution):
        concerns = "; ".join(d.concerns) if d.concerns else "—"
        lines.append(f"| {d.dimension} | {d.score_0_100} | {concerns} |")
    if r.top_concerns:
        lines.extend(["", "## Top concerns", ""])
        for c in r.top_concerns:
            lines.append(f"- {c}")
    return "\n".join(lines)
