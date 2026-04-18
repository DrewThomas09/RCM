"""HSR antitrust scanner — FTC/DOJ healthcare-PE exposure.

Partner statement: "FTC's healthcare focus has teeth
now. A full second request costs 6-9 months + $15M
legal. A divestiture order costs the thesis. I want
antitrust risk flagged before I sign, not after HSR."

### Why this matters for healthcare PE

Recent enforcement patterns (2022-2026):

- **Physician roll-ups** — FTC challenged "serial
  acquisition" strategies in anesthesia (U.S. Anesthesia
  Partners), dermatology, radiology.
- **Hospital mergers** — both federal and state AG
  challenges on local-market concentration.
- **Payer-provider vertical** — heightened scrutiny
  on MA plan + provider network vertical deals.
- **Non-compete enforcement** — FTC's non-compete rule
  interacts with physician retention strategies.

### 8 antitrust flag detectors

1. **local_market_hhi_gt_2500** — post-transaction HHI
   above 2500 in a local healthcare market = high
   concentration.
2. **top_competitor_share_post_gt_30pct** — combined
   share above 30% triggers Section 7 scrutiny.
3. **sponsor_serial_acquisition_same_specialty** —
   sponsor has > 3 platforms in same specialty /
   geography.
4. **payer_provider_vertical_integration** — vertical
   combination of payer and provider assets.
5. **physician_noncompete_material** — deal relies on
   non-competes that FTC's rule may invalidate.
6. **state_ag_active_review_jurisdiction** — deal
   touches CA / NY / WA / MA (aggressive state AGs).
7. **prior_ftc_action_in_sector** — subsector has
   recent FTC enforcement.
8. **deal_size_above_hsr_threshold** — deal exceeds HSR
   notification threshold ($119.5M in 2026).

### Output

- Risk tier: low / medium / high / very_high.
- Expected days-to-close delta (0 / +30 / +90 / +180+).
- Divestiture probability estimate.
- Named partner counter per flag.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


AGGRESSIVE_STATE_AGS = {"CA", "NY", "WA", "MA"}


@dataclass
class HSRAntitrustInputs:
    local_market_hhi_post: float = 0.0
    top_competitor_share_post_pct: float = 0.0
    sponsor_platforms_in_same_specialty: int = 0
    payer_provider_vertical: bool = False
    physician_noncompete_material: bool = False
    operating_states: List[str] = field(default_factory=list)
    prior_ftc_action_in_sector: bool = False
    deal_size_m: float = 0.0


HSR_NOTIFICATION_THRESHOLD_M: float = 119.5   # 2026 threshold


@dataclass
class AntitrustFlag:
    name: str
    triggered: bool
    partner_counter: str


@dataclass
class HSRAntitrustReport:
    risk_tier: str                         # low/medium/high/very_high
    expected_days_delay: int
    divestiture_probability_pct: float
    triggered_count: int
    flags: List[AntitrustFlag] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_tier": self.risk_tier,
            "expected_days_delay": self.expected_days_delay,
            "divestiture_probability_pct":
                self.divestiture_probability_pct,
            "triggered_count": self.triggered_count,
            "flags": [
                {"name": f.name,
                 "triggered": f.triggered,
                 "partner_counter": f.partner_counter}
                for f in self.flags
            ],
            "partner_note": self.partner_note,
        }


def scan_hsr_antitrust(
    inputs: HSRAntitrustInputs,
) -> HSRAntitrustReport:
    flags: List[AntitrustFlag] = []

    hhi = inputs.local_market_hhi_post >= 2500
    flags.append(AntitrustFlag(
        name="local_market_hhi_gt_2500",
        triggered=hhi,
        partner_counter=(
            "Post-merger HHI ≥ 2500; Section 7 scrutiny "
            "material. Pre-file informal with agency; "
            "model fix-as-a-divestiture."
            if hhi else
            "Post-merger HHI within safe harbor."
        ),
    ))

    share = inputs.top_competitor_share_post_pct >= 0.30
    flags.append(AntitrustFlag(
        name="top_competitor_share_post_gt_30pct",
        triggered=share,
        partner_counter=(
            "Combined local share ≥ 30% = merger-"
            "guidelines presumptive concern. Counter: "
            "define geographic market narrowly or identify "
            "entry competitors."
            if share else
            "Local share below guidelines threshold."
        ),
    ))

    serial = inputs.sponsor_platforms_in_same_specialty > 3
    flags.append(AntitrustFlag(
        name="sponsor_serial_acquisition_same_specialty",
        triggered=serial,
        partner_counter=(
            "Sponsor has > 3 prior platforms in same "
            "specialty — FTC has been pursuing 'serial' "
            "theories (US Anesthesia Partners). Expect "
            "comprehensive data request."
            if serial else
            "No serial-acquisition pattern concern."
        ),
    ))

    vertical = inputs.payer_provider_vertical
    flags.append(AntitrustFlag(
        name="payer_provider_vertical_integration",
        triggered=vertical,
        partner_counter=(
            "Vertical payer-provider integration under "
            "heightened scrutiny. Consider behavioral "
            "remedies + firewall commitments pre-file."
            if vertical else
            "No vertical payer-provider integration."
        ),
    ))

    nc = inputs.physician_noncompete_material
    flags.append(AntitrustFlag(
        name="physician_noncompete_material",
        triggered=nc,
        partner_counter=(
            "Thesis relies on physician non-competes; "
            "FTC non-compete rule may invalidate. Plan "
            "retention via deferred-comp clawbacks."
            if nc else
            "No material reliance on non-competes."
        ),
    ))

    state_ag = any(
        s.upper() in AGGRESSIVE_STATE_AGS
        for s in inputs.operating_states
    )
    flags.append(AntitrustFlag(
        name="state_ag_active_review_jurisdiction",
        triggered=state_ag,
        partner_counter=(
            "Deal touches aggressive state-AG jurisdiction "
            "(CA/NY/WA/MA). Pre-clear state AG + local "
            "regulators; state review adds 60-90 days."
            if state_ag else
            "No aggressive state-AG jurisdiction."
        ),
    ))

    ftc_prior = inputs.prior_ftc_action_in_sector
    flags.append(AntitrustFlag(
        name="prior_ftc_action_in_sector",
        triggered=ftc_prior,
        partner_counter=(
            "Subsector has recent FTC enforcement action. "
            "Agency is informed; expect tailored "
            "information request. Prep remedy package."
            if ftc_prior else
            "No recent FTC action in subsector."
        ),
    ))

    hsr_threshold = (
        inputs.deal_size_m >= HSR_NOTIFICATION_THRESHOLD_M
    )
    flags.append(AntitrustFlag(
        name="deal_size_above_hsr_threshold",
        triggered=hsr_threshold,
        partner_counter=(
            f"Deal size ${inputs.deal_size_m:,.0f}M above "
            f"HSR threshold ${HSR_NOTIFICATION_THRESHOLD_M}M; "
            "HSR notification required with 30-day waiting."
            if hsr_threshold else
            f"Deal below HSR threshold "
            f"${HSR_NOTIFICATION_THRESHOLD_M}M; no "
            "notification required but state review "
            "may apply."
        ),
    ))

    triggered = sum(1 for f in flags if f.triggered)

    # Risk-tier logic.
    # Structural flags (HHI/share) drive tier harder
    # than administrative flags (HSR threshold only).
    high_severity_flags = sum(
        1 for f in flags
        if f.triggered and f.name in {
            "local_market_hhi_gt_2500",
            "top_competitor_share_post_gt_30pct",
            "sponsor_serial_acquisition_same_specialty",
            "payer_provider_vertical_integration",
        }
    )

    if high_severity_flags >= 3 or (
        hhi and share and (vertical or serial)
    ):
        tier = "very_high"
        delay = 270
        divest = 70.0
        note = (
            "Very-high antitrust risk. Expect second "
            "request (6-9 months), material divestiture "
            "probability. Partner: walk unless deal "
            "survives at scale-back."
        )
    elif high_severity_flags >= 2:
        tier = "high"
        delay = 150
        divest = 40.0
        note = (
            "High antitrust risk. Plan 5-6 month close "
            "window, pre-file agency discussion, model "
            "fix-as-a-divestiture scenarios."
        )
    elif high_severity_flags == 1 or triggered >= 3:
        tier = "medium"
        delay = 60
        divest = 15.0
        note = (
            "Medium antitrust risk. Add 60-day cushion "
            "to outside-date; retain antitrust counsel "
            "before LOI."
        )
    elif triggered >= 1:
        tier = "low"
        delay = 30
        divest = 2.0
        note = (
            "Low antitrust risk. HSR process should "
            "complete in 30 days."
        )
    else:
        tier = "low"
        delay = 0
        divest = 0.0
        note = (
            "No antitrust flags detected. Standard close "
            "timeline."
        )

    return HSRAntitrustReport(
        risk_tier=tier,
        expected_days_delay=delay,
        divestiture_probability_pct=divest,
        triggered_count=triggered,
        flags=flags,
        partner_note=note,
    )


def render_hsr_antitrust_markdown(
    r: HSRAntitrustReport,
) -> str:
    lines = [
        "# HSR antitrust scanner",
        "",
        f"**Tier:** `{r.risk_tier}`",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Triggered flags: {r.triggered_count}",
        f"- Expected close delay: "
        f"+{r.expected_days_delay} days",
        f"- Divestiture probability: "
        f"{r.divestiture_probability_pct:.1f}%",
        "",
        "| Flag | Triggered | Partner counter |",
        "|---|---|---|",
    ]
    for f in r.flags:
        check = "✓" if f.triggered else "—"
        lines.append(
            f"| {f.name} | {check} | {f.partner_counter} |"
        )
    return "\n".join(lines)
