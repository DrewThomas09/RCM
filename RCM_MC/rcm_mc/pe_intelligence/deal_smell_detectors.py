"""Deal smell detectors — partner pattern-recognition reflexes.

Different from `historical_failure_library` (named/dated real
failures) and `partner_traps_library` (specific pitch claims).
These are SMELLS — partner shorthand when multiple signals
combine into a recognizable pattern.

Examples:

- "Smells like a roll-up running out of bolt-ons."
- "Smells like denials papering over a payer-concentration
  problem."
- "Smells like a founder who wants out, not a founder who wants
  partners."
- "Smells like EBITDA pulled forward to hit a bid deadline."

Each smell fires when its signal combination is present. Partner
reads them as "I've seen this before, and I didn't like it."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SmellContext:
    # Growth / acquisition signals.
    revenue_growth_from_acquisition_pct: float = 0.0
    revenue_growth_organic_pct: float = 0.0
    pipeline_count: int = 10
    platform_age_years: int = 3
    acquisitions_per_year: int = 2
    # Payer / denial signals.
    top_payer_share: float = 0.25
    denial_rate: float = 0.08
    denial_rate_trend: str = "flat"        # "flat"/"rising"/"falling"
    # Founder / transition signals.
    founder_ceo_in_place: bool = False
    founder_retiring_flag: bool = False
    ceo_age_60_plus: bool = False
    management_transitions_last_2yr: int = 0
    # Earnings quality.
    recent_ebitda_jump_pct: float = 0.0    # latest period vs prior
    pro_forma_addbacks_pct: float = 0.0
    close_deadline_weeks: int = 99
    # Structure signals.
    leverage: float = 5.5
    covenant_headroom_pct: float = 0.20
    # Operational.
    key_clinician_departures_12mo: int = 0
    clinician_headcount: int = 100
    # Quality / regulatory.
    cms_survey_issues: bool = False
    litigation_count: int = 0


@dataclass
class DealSmell:
    name: str
    pattern: str
    trigger_signals: List[str]
    partner_commentary: str
    severity: str                           # "low" / "medium" / "high"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "pattern": self.pattern,
            "trigger_signals": list(self.trigger_signals),
            "partner_commentary": self.partner_commentary,
            "severity": self.severity,
        }


# Each detector returns DealSmell or None.

def _rollup_running_out(ctx: SmellContext) -> Optional[DealSmell]:
    if (ctx.acquisitions_per_year >= 5
            and ctx.pipeline_count < 10
            and ctx.platform_age_years >= 3):
        return DealSmell(
            name="rollup_running_out_of_boltons",
            pattern=("Smells like a roll-up running out of bolt-ons."),
            trigger_signals=[
                f"acq/yr={ctx.acquisitions_per_year}",
                f"pipeline={ctx.pipeline_count}",
                f"platform_age={ctx.platform_age_years}y",
            ],
            partner_commentary=(
                "Platforms decelerate when the named-target pipeline "
                "thins. Exit story needs to shift from 'more roll-up' "
                "to 'operating excellence' — which is a different "
                "buyer and a different multiple."),
            severity="high",
        )
    return None


def _denials_paper_over_concentration(
    ctx: SmellContext,
) -> Optional[DealSmell]:
    if (ctx.denial_rate >= 0.09
            and ctx.denial_rate_trend == "rising"
            and ctx.top_payer_share >= 0.35):
        return DealSmell(
            name="denials_paper_over_payer_concentration",
            pattern=("Smells like a denial trend papering over a "
                      "top-payer problem."),
            trigger_signals=[
                f"denial_rate={ctx.denial_rate:.2f}",
                f"denial_trend={ctx.denial_rate_trend}",
                f"top_payer_share={ctx.top_payer_share:.2f}",
            ],
            partner_commentary=(
                "Rising denials concentrated on the dominant payer "
                "mean the payer is tightening the screws. Generic "
                "'RCM improvement' does not solve a single-payer "
                "leverage problem."),
            severity="high",
        )
    return None


def _founder_wants_out(ctx: SmellContext) -> Optional[DealSmell]:
    if (ctx.founder_ceo_in_place
            and (ctx.ceo_age_60_plus or ctx.founder_retiring_flag)):
        return DealSmell(
            name="founder_wants_out",
            pattern=("Smells like a founder who wants OUT, not a "
                      "founder who wants partners."),
            trigger_signals=[
                "founder_ceo_in_place=True",
                f"age_60+={ctx.ceo_age_60_plus}",
                f"retiring_flag={ctx.founder_retiring_flag}",
            ],
            partner_commentary=(
                "Founder exit post-close without a named successor "
                "is the #1 cause of year-1 operating disruption. "
                "Require a named COO/CEO-elect in the retention "
                "package."),
            severity="medium",
        )
    return None


def _ebitda_pulled_forward(
    ctx: SmellContext,
) -> Optional[DealSmell]:
    if (ctx.recent_ebitda_jump_pct >= 0.15
            and ctx.close_deadline_weeks <= 8
            and ctx.pro_forma_addbacks_pct >= 0.10):
        return DealSmell(
            name="ebitda_pulled_forward",
            pattern=("Smells like EBITDA pulled forward to hit the "
                      "bid deadline."),
            trigger_signals=[
                f"recent_ebitda_jump={ctx.recent_ebitda_jump_pct*100:.0f}%",
                f"close_in={ctx.close_deadline_weeks}wks",
                f"pro_forma={ctx.pro_forma_addbacks_pct*100:.0f}%",
            ],
            partner_commentary=(
                "Late-stage EBITDA jumps + aggressive pro-forma "
                "add-backs + a tight close clock is the classic "
                "'dress the numbers' pattern. QofE teeth here — "
                "non-negotiable."),
            severity="high",
        )
    return None


def _covenant_close_to_trip(
    ctx: SmellContext,
) -> Optional[DealSmell]:
    if ctx.leverage >= 6.0 and ctx.covenant_headroom_pct <= 0.10:
        return DealSmell(
            name="covenant_already_tight",
            pattern=("Smells like a deal walking into covenant "
                      "trouble on day 1."),
            trigger_signals=[
                f"leverage={ctx.leverage:.1f}x",
                f"headroom={ctx.covenant_headroom_pct*100:.0f}%",
            ],
            partner_commentary=(
                "Thin covenant headroom at entry + high leverage "
                "means the first bad quarter becomes a lender "
                "conversation. Negotiate covenant-lite or pass."),
            severity="high",
        )
    return None


def _clinician_flight(
    ctx: SmellContext,
) -> Optional[DealSmell]:
    if (ctx.clinician_headcount > 0
            and (ctx.key_clinician_departures_12mo
                 / max(1, ctx.clinician_headcount) >= 0.15)):
        return DealSmell(
            name="clinician_flight_in_progress",
            pattern=("Smells like clinician flight is already "
                      "underway."),
            trigger_signals=[
                f"departures_12mo={ctx.key_clinician_departures_12mo}",
                f"headcount={ctx.clinician_headcount}",
            ],
            partner_commentary=(
                "High recent departures are a leading indicator — "
                "not lagging. Volume / quality / billing follow "
                "6-12 months later. Diligence the WHY before close."),
            severity="high",
        )
    return None


def _organic_declining_under_rollup_wrapper(
    ctx: SmellContext,
) -> Optional[DealSmell]:
    if (ctx.revenue_growth_from_acquisition_pct >= 0.08
            and ctx.revenue_growth_organic_pct <= 0.0):
        return DealSmell(
            name="organic_declining_under_rollup",
            pattern=("Smells like organic revenue is contracting "
                      "under the roll-up wrapper."),
            trigger_signals=[
                f"organic={ctx.revenue_growth_organic_pct*100:.1f}%",
                f"acquisition={ctx.revenue_growth_from_acquisition_pct*100:.1f}%",
            ],
            partner_commentary=(
                "Negative organic growth + positive acquisition "
                "growth is the AdaptHealth pattern — pro-forma "
                "works until buyer sees same-site trend lines. Push "
                "on why core organic is declining."),
            severity="high",
        )
    return None


def _management_turnover_churn(
    ctx: SmellContext,
) -> Optional[DealSmell]:
    if ctx.management_transitions_last_2yr >= 3:
        return DealSmell(
            name="management_churn",
            pattern=("Smells like a management team in churn."),
            trigger_signals=[
                f"transitions_2yr={ctx.management_transitions_last_2yr}",
            ],
            partner_commentary=(
                "3+ C-suite transitions in 2 years is a culture or "
                "performance signal, not a staffing mismatch. "
                "Reference calls are mandatory."),
            severity="medium",
        )
    return None


def _regulatory_soft_issues(ctx: SmellContext) -> Optional[DealSmell]:
    if ctx.cms_survey_issues and ctx.litigation_count >= 2:
        return DealSmell(
            name="quality_compliance_canary",
            pattern=("Smells like quality + compliance are quietly "
                      "decaying."),
            trigger_signals=[
                "cms_survey_issues=True",
                f"litigation_count={ctx.litigation_count}",
            ],
            partner_commentary=(
                "CMS survey issues + multiple litigation is not a "
                "'bad year' — it is a systems decay pattern. Pass "
                "unless a specific remediation owner is identified."),
            severity="medium",
        )
    return None


DETECTORS = (
    _rollup_running_out,
    _denials_paper_over_concentration,
    _founder_wants_out,
    _ebitda_pulled_forward,
    _covenant_close_to_trip,
    _clinician_flight,
    _organic_declining_under_rollup_wrapper,
    _management_turnover_churn,
    _regulatory_soft_issues,
)


@dataclass
class SmellReport:
    smells: List[DealSmell] = field(default_factory=list)
    high_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "smells": [s.to_dict() for s in self.smells],
            "high_count": self.high_count,
            "partner_note": self.partner_note,
        }


def detect_smells(ctx: SmellContext) -> SmellReport:
    smells = [d(ctx) for d in DETECTORS]
    smells = [s for s in smells if s is not None]
    high = sum(1 for s in smells if s.severity == "high")
    if high >= 2:
        note = (f"Multiple high-severity smells "
                f"({high}) — partners call this the "
                "'something isn't right' deal. Pass unless specific "
                "remediation for each is on the table.")
    elif high == 1:
        top = next(s for s in smells if s.severity == "high")
        note = (f"One high smell: '{top.name}'. That alone is "
                "usually enough to push IC back and diligence the "
                "specific signal.")
    elif smells:
        note = (f"{len(smells)} medium smells surfaced — noted, "
                "fold into diligence questions.")
    else:
        note = ("No partner-reflex smells fire — deal passes the "
                "gut-check layer.")
    return SmellReport(smells=smells, high_count=high,
                        partner_note=note)


def render_smells_markdown(r: SmellReport) -> str:
    lines = [
        "# Deal smell detectors",
        "",
        f"_{r.partner_note}_",
        "",
    ]
    for s in r.smells:
        lines.append(f"## {s.name} ({s.severity.upper()})")
        lines.append(f"_{s.pattern}_")
        lines.append("")
        lines.append(f"**Signals:** {', '.join(s.trigger_signals)}")
        lines.append("")
        lines.append(f"**Partner commentary:** {s.partner_commentary}")
        lines.append("")
    return "\n".join(lines)
