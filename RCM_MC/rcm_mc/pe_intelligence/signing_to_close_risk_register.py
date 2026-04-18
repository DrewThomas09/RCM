"""Signing-to-close risk register — the 60-120 day watchlist.

Partner statement: "Signing is not closing. Between LOI
and close, the asset can change materially — and every
change costs me either price, structure, or the deal
itself. I keep a running watchlist of what can blow up
in those 90 days."

Distinct from `closing_conditions_list.py` (what
*must be satisfied* at close) — this module is the
**living watchlist** of events that can happen in the
signing-to-close window that change the deal.

### 12 event categories modeled

1. **material_customer_loss** — top-10 customer churn
   discovered in interim period.
2. **key_employee_departure** — Key-15 exit at close
   transition.
3. **quality_incident** — sentinel event, OIG subpoena,
   survey deficiency.
4. **regulatory_rule_final** — CMS rule finalizes during
   interim period.
5. **financing_market_shift** — lender terms move 150
   bps+ between commitment and funding.
6. **qofe_material_adjustment** — final QofE strips > 5%
   of stated EBITDA.
7. **it_cyber_disclosure** — ransomware event or
   undisclosed breach surfaces.
8. **interim_financial_miss** — quarterly actuals below
   bring-down period forecast > 10%.
9. **mac_triggered** — material adverse change event.
10. **competitor_action** — competitor opens new site,
    wins anchor contract.
11. **litigation_surprise** — pending case settlement /
    ruling lands pre-close.
12. **environmental_physical** — discovered contamination,
    asbestos, mold at a physical site.

### Per-event partner data

- **frequency** — partner-judgment likelihood per 10
  healthcare-services deals: high (> 3 of 10) / medium /
  low.
- **severity** — walk_right / reprice_trigger / hold.
- **early_warning_signals** — what the deal team should
  watch.
- **partner_counter_pre_close** — mitigation path.
- **typical_cost_to_buyer_pct** — EBITDA impact if
  realized, as partner ballpark.

### Scanner

`scan_sign_to_close_risks(signals)` returns list of
matched risks given deal context signals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SignToCloseRisk:
    name: str
    description: str
    frequency: str              # "high" / "medium" / "low"
    severity: str               # "walk_right" / "reprice_trigger"
                                # / "hold"
    early_warning_signals: List[str] = field(default_factory=list)
    partner_counter_pre_close: str = ""
    typical_cost_to_buyer_pct: float = 0.0   # pct of EBITDA


RISK_LIBRARY: List[SignToCloseRisk] = [
    SignToCloseRisk(
        name="material_customer_loss",
        description=(
            "Top-10 customer or payer contract drops or "
            "renegotiates material terms during interim "
            "period."
        ),
        frequency="medium",
        severity="reprice_trigger",
        early_warning_signals=[
            "top_10_customer_contract_expiring_interim",
            "customer_concentration_gt_20pct",
            "recent_rfp_activity_in_customer_base",
        ],
        partner_counter_pre_close=(
            "Require interim customer-retention "
            "certification at close; indemnity on material "
            "loss within 6 months post-close."
        ),
        typical_cost_to_buyer_pct=0.08,
    ),
    SignToCloseRisk(
        name="key_employee_departure",
        description=(
            "Key-15 named in rep or closing certificate "
            "signals exit before close."
        ),
        frequency="medium",
        severity="walk_right",
        early_warning_signals=[
            "key_employee_retention_not_signed",
            "key_employee_cashed_out_at_close",
            "no_non_compete_in_place",
        ],
        partner_counter_pre_close=(
            "Signed retention + non-compete at signing, "
            "not close. Walk-right on material key-15 "
            "departure."
        ),
        typical_cost_to_buyer_pct=0.10,
    ),
    SignToCloseRisk(
        name="quality_incident",
        description=(
            "Sentinel event, OIG subpoena, or survey "
            "deficiency disclosed during interim period."
        ),
        frequency="low",
        severity="walk_right",
        early_warning_signals=[
            "open_cms_survey_deficiency",
            "oig_investigation_active",
            "sentinel_event_in_past_12_months",
        ],
        partner_counter_pre_close=(
            "Bring-down quality certification + walk-right "
            "on any open CMS or OIG action."
        ),
        typical_cost_to_buyer_pct=0.15,
    ),
    SignToCloseRisk(
        name="regulatory_rule_final",
        description=(
            "CMS rule (site-neutral, OBBBA, Medicare "
            "Advantage benchmark) finalizes during interim "
            "period with material impact."
        ),
        frequency="medium",
        severity="reprice_trigger",
        early_warning_signals=[
            "pending_cms_rule_in_comment_period",
            "regulatory_calendar_window_overlaps_interim",
            "material_exposure_to_rule",
        ],
        partner_counter_pre_close=(
            "Outside-date trigger on material rule change; "
            "price renegotiation right if rule lands."
        ),
        typical_cost_to_buyer_pct=0.05,
    ),
    SignToCloseRisk(
        name="financing_market_shift",
        description=(
            "Debt markets move materially between commitment "
            "and funding; cost of capital changes."
        ),
        frequency="medium",
        severity="hold",
        early_warning_signals=[
            "commitment_to_funding_window_gt_90_days",
            "private_credit_market_volatile",
            "no_rate_lock_in_commitment",
        ],
        partner_counter_pre_close=(
            "Commitment with MAC trigger only on market-"
            "wide dislocation, not idiosyncratic rate "
            "movement. Pre-negotiate rate lock."
        ),
        typical_cost_to_buyer_pct=0.03,
    ),
    SignToCloseRisk(
        name="qofe_material_adjustment",
        description=(
            "Final QofE strips > 5% of stated EBITDA "
            "between signing and close."
        ),
        frequency="medium",
        severity="reprice_trigger",
        early_warning_signals=[
            "qofe_not_complete_at_signing",
            "stated_ebitda_above_peer_band",
            "aggressive_add_back_schedule",
        ],
        partner_counter_pre_close=(
            "Require QofE substantially complete at LOI "
            "or build price-adjustment mechanism tied to "
            "final QofE delta > 3%."
        ),
        typical_cost_to_buyer_pct=0.08,
    ),
    SignToCloseRisk(
        name="it_cyber_disclosure",
        description=(
            "Ransomware event, PHI breach, or undisclosed "
            "cyber incident surfaces pre-close."
        ),
        frequency="low",
        severity="walk_right",
        early_warning_signals=[
            "cyber_insurance_renewed_late",
            "no_recent_pen_test",
            "ransomware_prior_in_peer_set",
        ],
        partner_counter_pre_close=(
            "Bring-down cyber certification + specific "
            "reps on breaches known / unknown. R&W carve-"
            "out for undisclosed events."
        ),
        typical_cost_to_buyer_pct=0.10,
    ),
    SignToCloseRisk(
        name="interim_financial_miss",
        description=(
            "Quarterly or monthly EBITDA comes in > 10% "
            "below bring-down forecast during interim."
        ),
        frequency="high",
        severity="reprice_trigger",
        early_warning_signals=[
            "forecast_accuracy_history_weak",
            "seasonality_understated",
            "q4_back_loaded_plan",
        ],
        partner_counter_pre_close=(
            "Interim EBITDA bring-down at each measurement "
            "date with automatic re-price or walk on > 10% "
            "miss."
        ),
        typical_cost_to_buyer_pct=0.06,
    ),
    SignToCloseRisk(
        name="mac_triggered",
        description=(
            "Material adverse change event as defined in "
            "purchase agreement occurs during interim."
        ),
        frequency="low",
        severity="walk_right",
        early_warning_signals=[
            "narrow_mac_definition_in_agreement",
            "exogenous_risk_factors_elevated",
        ],
        partner_counter_pre_close=(
            "Narrow MAC definition excluding market-wide "
            "events but including asset-specific "
            "deterioration."
        ),
        typical_cost_to_buyer_pct=0.20,
    ),
    SignToCloseRisk(
        name="competitor_action",
        description=(
            "Competitor opens new site, wins anchor "
            "contract, or launches pricing war during "
            "interim."
        ),
        frequency="medium",
        severity="hold",
        early_warning_signals=[
            "competitive_market_hhi_below_0.20",
            "new_entrant_announced_in_market",
            "payer_steering_to_competitor",
        ],
        partner_counter_pre_close=(
            "Monitor; usually not a walk right but "
            "informs 100-day plan. Adjust day-1 pricing "
            "strategy."
        ),
        typical_cost_to_buyer_pct=0.03,
    ),
    SignToCloseRisk(
        name="litigation_surprise",
        description=(
            "Pending litigation settles or rules adversely "
            "pre-close."
        ),
        frequency="low",
        severity="reprice_trigger",
        early_warning_signals=[
            "pending_litigation_disclosed_as_immaterial",
            "plaintiff_class_action_possible",
            "settlement_discussion_active",
        ],
        partner_counter_pre_close=(
            "Escrow sized to pending litigation exposure. "
            "Specific indemnity carve-out."
        ),
        typical_cost_to_buyer_pct=0.04,
    ),
    SignToCloseRisk(
        name="environmental_physical",
        description=(
            "Environmental contamination, asbestos, mold, "
            "or Phase 2 ESA finding at physical site."
        ),
        frequency="low",
        severity="reprice_trigger",
        early_warning_signals=[
            "phase_1_esa_flags_material",
            "older_physical_plant_gt_40_years",
            "prior_industrial_use_on_site",
        ],
        partner_counter_pre_close=(
            "Phase 2 ESA required pre-close on flagged "
            "sites. Specific indemnity with cap."
        ),
        typical_cost_to_buyer_pct=0.05,
    ),
]


@dataclass
class SignToCloseMatch:
    risk: SignToCloseRisk
    signals_hit: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk": {
                "name": self.risk.name,
                "description": self.risk.description,
                "frequency": self.risk.frequency,
                "severity": self.risk.severity,
                "partner_counter_pre_close":
                    self.risk.partner_counter_pre_close,
                "typical_cost_to_buyer_pct":
                    self.risk.typical_cost_to_buyer_pct,
            },
            "signals_hit": list(self.signals_hit),
        }


@dataclass
class SignToCloseReport:
    matches: List[SignToCloseMatch] = field(default_factory=list)
    walk_right_count: int = 0
    reprice_trigger_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "walk_right_count": self.walk_right_count,
            "reprice_trigger_count":
                self.reprice_trigger_count,
            "partner_note": self.partner_note,
        }


def scan_sign_to_close_risks(
    signals: Dict[str, Any],
) -> SignToCloseReport:
    matches: List[SignToCloseMatch] = []
    for r in RISK_LIBRARY:
        hit = [s for s in r.early_warning_signals
               if bool(signals.get(s, False))]
        if not hit:
            continue
        matches.append(SignToCloseMatch(
            risk=r,
            signals_hit=hit,
        ))
    # Sort by severity then number of signals hit.
    sev_rank = {"walk_right": 2, "reprice_trigger": 1, "hold": 0}
    matches.sort(key=lambda m: (
        -sev_rank.get(m.risk.severity, 0),
        -len(m.signals_hit),
    ))

    walk_rights = sum(1 for m in matches
                       if m.risk.severity == "walk_right")
    reprice = sum(1 for m in matches
                   if m.risk.severity == "reprice_trigger")

    if walk_rights >= 2:
        note = (
            f"{walk_rights} walk-right risks firing. Partner: "
            "demand bring-down certifications at close + "
            "explicit walk-right triggers in the purchase "
            "agreement."
        )
    elif walk_rights == 1:
        note = (
            "1 walk-right risk flagged. Partner: this is the "
            "axis on which the deal can die pre-close — "
            "ensure purchase-agreement walk-right is "
            "explicit."
        )
    elif reprice >= 3:
        note = (
            f"{reprice} re-price trigger risks firing. "
            "Partner: build price-adjustment mechanism into "
            "purchase agreement tied to specific events."
        )
    elif matches:
        note = (
            f"{len(matches)} sign-to-close risks flagged. "
            "Monitor during interim period; document early "
            "warning signals in deal-team review."
        )
    else:
        note = (
            "No sign-to-close risks flagged on current "
            "signals. Standard interim-period discipline "
            "applies."
        )

    return SignToCloseReport(
        matches=matches,
        walk_right_count=walk_rights,
        reprice_trigger_count=reprice,
        partner_note=note,
    )


def list_sign_to_close_risks() -> List[str]:
    return [r.name for r in RISK_LIBRARY]


def render_sign_to_close_markdown(
    r: SignToCloseReport,
) -> str:
    lines = [
        "# Signing-to-close risk register",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Walk-right risks: {r.walk_right_count}",
        f"- Reprice-trigger risks: {r.reprice_trigger_count}",
        f"- Total matches: {len(r.matches)}",
        "",
        "| Risk | Severity | Frequency | Typical cost | "
        "Partner counter |",
        "|---|---|---|---|---|",
    ]
    for m in r.matches:
        risk = m.risk
        lines.append(
            f"| {risk.name} | {risk.severity} | "
            f"{risk.frequency} | "
            f"{risk.typical_cost_to_buyer_pct*100:.0f}% EBITDA | "
            f"{risk.partner_counter_pre_close} |"
        )
    return "\n".join(lines)
