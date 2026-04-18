"""Payer renegotiation timing — "the payer is coming" trap.

Partner statement: "Every healthcare deck shows payer
mix as a pie chart — 45% commercial, 30% Medicare, 20%
Medicaid. That's the wrong picture. The right picture
is a *calendar*: when does the BCBS contract expire?
When is United's next evergreen cycle? If the top-3
commercial contract expires in year 2 of the hold and
the payer has been posting record MLR, the rate reset
is coming and the exit buyer will model it against us.
The 'payer renegotiation is coming' trap is the most
expensive single pattern in healthcare PE. Model the
contract calendar explicitly."

Distinct from:
- `payer_mix_risk` — static pie-chart concentration.
- `contract_diligence` — generic contract-level
  review checklist.
- `reimbursement_cliff_calendar_2026_2029` —
  regulatory (CMS / state) rate events, not
  commercial payer contracts.
- `reimbursement_bands` — rate bands.

### Partner model

Given a list of top payer contracts with:
- current rate index (baseline = 1.0)
- contract expiration date
- most-likely rate change at renewal (by payer and
  region; partner seeds from their book of MLR /
  posture intel)
- payer's bargaining posture

…project quarter-by-quarter blended payer-rate drift
and the EBITDA impact each quarter of the hold.

### Bargaining posture proxies

A healthy commercial payer going into renewal with a
healthcare provider trending above market rates will
push for a rate cut or flat renewal. Partner's
back-of-envelope cues:

- **aggressive** — payer is a dominant plan in market
  (HHI > 2500) and provider has no network alternative
  (−2% to −5% renewal).
- **firm** — payer large and MLR above target
  (0% to −2%).
- **neutral** — balanced market (0% to +1%).
- **soft** — provider is essential / rare specialty
  (+1% to +3%).

### Output

Per-contract renewal forecast; per-quarter blended
rate drift; per-year EBITDA impact $M; total hold-
period cumulative impact; partner note on whether
exit buyer will see "normalized" rates > current.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional


POSTURE_CUTS = {
    "aggressive": -0.035,
    "firm": -0.015,
    "neutral": 0.005,
    "soft": 0.020,
}


@dataclass
class PayerContract:
    name: str
    payer_mix_pct: float  # share of total NPR
    expiration_date: date
    posture: str = "firm"
    override_rate_change_pct: Optional[float] = None
    already_repriced_locked_in: bool = False


@dataclass
class PayerRenegotiationInputs:
    contracts: List[PayerContract] = field(
        default_factory=list)
    hold_start_date: date = date(2026, 1, 1)
    hold_years: int = 5
    base_npr_m: float = 300.0
    contribution_margin_pct: float = 0.30
    # fraction of the NPR hit that flows to EBITDA
    # (rate cuts hit full, some variable-cost absorption).


@dataclass
class ContractForecast:
    name: str
    expiration_date: date
    renewal_in_hold: bool
    renewal_quarter_offset: int  # Q0..QN of hold
    applied_rate_change_pct: float


@dataclass
class QuarterImpact:
    year: int
    quarter: int
    rate_drift_pct: float
    npr_impact_m: float
    ebitda_impact_m: float


@dataclass
class PayerRenegotiationReport:
    contract_forecasts: List[ContractForecast] = field(
        default_factory=list)
    quarters: List[QuarterImpact] = field(
        default_factory=list)
    total_npr_impact_m: float = 0.0
    total_ebitda_impact_m: float = 0.0
    exit_year_normalized_rate_pct: float = 0.0
    trap_flag: bool = False
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_forecasts": [
                {"name": c.name,
                 "expiration_date":
                     c.expiration_date.isoformat(),
                 "renewal_in_hold": c.renewal_in_hold,
                 "renewal_quarter_offset":
                     c.renewal_quarter_offset,
                 "applied_rate_change_pct":
                     c.applied_rate_change_pct}
                for c in self.contract_forecasts
            ],
            "quarters": [
                {"year": q.year, "quarter": q.quarter,
                 "rate_drift_pct": q.rate_drift_pct,
                 "npr_impact_m": q.npr_impact_m,
                 "ebitda_impact_m": q.ebitda_impact_m}
                for q in self.quarters
            ],
            "total_npr_impact_m": self.total_npr_impact_m,
            "total_ebitda_impact_m":
                self.total_ebitda_impact_m,
            "exit_year_normalized_rate_pct":
                self.exit_year_normalized_rate_pct,
            "trap_flag": self.trap_flag,
            "partner_note": self.partner_note,
        }


def _quarter_of(start: date, target: date) -> int:
    """Offset in quarters from hold start to target.

    Negative if target precedes start. Approximate —
    uses calendar-day division into 91-day buckets;
    good enough for hold-period planning.
    """
    delta_days = (target - start).days
    return delta_days // 91


def project_payer_renegotiations(
    inputs: PayerRenegotiationInputs,
) -> PayerRenegotiationReport:
    total_quarters = inputs.hold_years * 4
    quarter_impacts: List[QuarterImpact] = []
    forecasts: List[ContractForecast] = []

    # For each contract, compute when it renews and the
    # applied rate change. If already repriced and
    # locked, ignore for forward projection.
    for c in inputs.contracts:
        q_offset = _quarter_of(
            inputs.hold_start_date, c.expiration_date
        )
        in_hold = 0 <= q_offset < total_quarters
        if c.already_repriced_locked_in:
            applied = 0.0
        elif c.override_rate_change_pct is not None:
            applied = c.override_rate_change_pct
        else:
            applied = POSTURE_CUTS.get(c.posture, -0.015)
        forecasts.append(ContractForecast(
            name=c.name,
            expiration_date=c.expiration_date,
            renewal_in_hold=in_hold,
            renewal_quarter_offset=q_offset,
            applied_rate_change_pct=applied,
        ))

    # Build per-quarter rate drift by accumulating
    # renewal-date rate step-downs for each contract
    # weighted by payer_mix_pct.
    current_drift = 0.0
    for q in range(total_quarters):
        # Apply each contract's step on its renewal
        # quarter.
        for c, f in zip(inputs.contracts, forecasts):
            if f.renewal_in_hold and f.renewal_quarter_offset == q:
                current_drift += (
                    f.applied_rate_change_pct *
                    c.payer_mix_pct
                )
        year = q // 4 + 1
        quarter = q % 4 + 1
        npr_impact = (
            inputs.base_npr_m * current_drift * 0.25
        )
        ebitda_impact = npr_impact * inputs.contribution_margin_pct
        quarter_impacts.append(QuarterImpact(
            year=year,
            quarter=quarter,
            rate_drift_pct=round(current_drift, 4),
            npr_impact_m=round(npr_impact, 3),
            ebitda_impact_m=round(ebitda_impact, 3),
        ))

    total_npr = sum(q.npr_impact_m for q in quarter_impacts)
    total_ebitda = sum(
        q.ebitda_impact_m for q in quarter_impacts)
    exit_drift = (
        quarter_impacts[-1].rate_drift_pct
        if quarter_impacts else 0.0
    )

    # Trap flag: top-3 payer concentration > 50% AND
    # at least one contract renews in hold AND its
    # rate change is negative AND cumulative exit drift
    # worse than -1%.
    top_concentration = sum(
        c.payer_mix_pct for c in sorted(
            inputs.contracts,
            key=lambda x: x.payer_mix_pct,
            reverse=True,
        )[:3]
    )
    has_neg_in_hold = any(
        f.renewal_in_hold and f.applied_rate_change_pct < 0
        for f in forecasts
    )
    trap = (
        top_concentration > 0.50 and
        has_neg_in_hold and
        exit_drift < -0.01
    )

    if trap:
        note = (
            f"Top-3 payer concentration "
            f"{top_concentration:.0%}; exit-year rate "
            f"drift {exit_drift:+.1%}; cumulative EBITDA "
            f"impact ${total_ebitda:.1f}M over hold. "
            "Exit buyer will model normalized rates "
            "net of renewals — bake this into exit-"
            "case EBITDA or expect multiple contraction."
        )
    elif has_neg_in_hold and exit_drift < -0.01:
        note = (
            f"Rate drift {exit_drift:+.1%} by exit; "
            f"cumulative EBITDA impact "
            f"${total_ebitda:.1f}M. Manageable but "
            "price renewals into exit assumption, do "
            "not leave the buyer to discover them."
        )
    elif exit_drift >= 0:
        note = (
            "No meaningful negative rate drift "
            "projected. Confirm posture assumptions by "
            "payer — if our 'firm' read is actually "
            "'aggressive,' the picture changes."
        )
    else:
        note = (
            f"Modest cumulative EBITDA impact "
            f"${total_ebitda:.1f}M. No flag."
        )

    return PayerRenegotiationReport(
        contract_forecasts=forecasts,
        quarters=quarter_impacts,
        total_npr_impact_m=round(total_npr, 2),
        total_ebitda_impact_m=round(total_ebitda, 2),
        exit_year_normalized_rate_pct=round(
            exit_drift, 4),
        trap_flag=trap,
        partner_note=note,
    )


def render_payer_renegotiation_markdown(
    r: PayerRenegotiationReport,
) -> str:
    flag = "⚠ payer trap" if r.trap_flag else "—"
    lines = [
        "# Payer renegotiation timing",
        "",
        f"_{flag}_ — {r.partner_note}",
        "",
        f"- Cumulative NPR impact: "
        f"${r.total_npr_impact_m:.1f}M",
        f"- Cumulative EBITDA impact: "
        f"${r.total_ebitda_impact_m:.1f}M",
        f"- Exit-year rate drift: "
        f"{r.exit_year_normalized_rate_pct:+.1%}",
        "",
        "## Contract renewals",
        "| Payer | Expires | In hold | Rate change |",
        "|---|---|---|---|",
    ]
    for f in r.contract_forecasts:
        lines.append(
            f"| {f.name} | "
            f"{f.expiration_date.isoformat()} | "
            f"{'✓' if f.renewal_in_hold else '✗'} | "
            f"{f.applied_rate_change_pct:+.1%} |"
        )
    return "\n".join(lines)
