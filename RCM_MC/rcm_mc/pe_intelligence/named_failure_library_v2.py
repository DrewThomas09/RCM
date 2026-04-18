"""Named failure library V2 — additional named patterns.

Partner statement: "Every named blow-up teaches one
specific lesson. The more you have catalogued, the faster
you pattern-match."

Extends `historical_failure_library.py` (10 patterns)
with 10 additional named patterns the brain uses for
pattern-matching. Each captures a specific failure mode
that a partner has internalized as 'do not let this
shape repeat.'

All patterns here are **illustrative archetypes** framed
around publicly discussed categories of healthcare-PE
stress; the packet-trigger signals are partner-judgment
heuristics, not forensic recreations.

### 10 additional patterns

1. **ma_startup_unwind_2023** — Medicare Advantage
   start-up enrollment collapse.
2. **behavioral_staffing_collapse_2024** — clinician
   supply exhaustion in behavioral health.
3. **pdgm_transition_fallout_2020** — home-health
   agencies that missed the PDGM coding shift.
4. **nsa_platform_rate_shock_2022** — No Surprises Act
   compressing OON-billing platforms.
5. **ma_provider_risk_contract_2023** — primary-care
   platforms assuming MA risk they couldn't price.
6. **tele_health_hype_fade_2023** — virtual-care
   valuations collapsing post-COVID surge.
7. **rcm_vendor_concentration_loss_2022** — RCM-as-a-
   service platforms losing single large anchor.
8. **dental_dso_over_rollup_2021** — dental DSO over-
   acquiring at top of cycle.
9. **strategic_acquisition_peak_2022** — strategic
   buyer paid peak then wrote down.
10. **ma_benefit_lockout_decay_2018** — MA lock-in
    benefit (gym, OTC) losing differentiation value.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class FailurePatternV2:
    name: str
    year: int
    deal_summary: str
    thesis_at_entry: str
    what_went_wrong: str
    ebitda_destruction_pct: float
    early_warning_signals: List[str] = field(default_factory=list)
    partner_lesson: str = ""
    packet_triggers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "year": self.year,
            "deal_summary": self.deal_summary,
            "thesis_at_entry": self.thesis_at_entry,
            "what_went_wrong": self.what_went_wrong,
            "ebitda_destruction_pct":
                self.ebitda_destruction_pct,
            "early_warning_signals":
                list(self.early_warning_signals),
            "partner_lesson": self.partner_lesson,
            "packet_triggers": list(self.packet_triggers),
        }


FAILURE_LIBRARY_V2: List[FailurePatternV2] = [
    FailurePatternV2(
        name="ma_startup_unwind_2023",
        year=2023,
        deal_summary=(
            "PE-backed Medicare Advantage start-up raised "
            "large early growth rounds, then enrollment / "
            "benefit-cost economics caught up."
        ),
        thesis_at_entry=(
            "MA enrollment grows 10%+ CAGR; scale + "
            "bed-consolidator effect drives margin."
        ),
        what_went_wrong=(
            "MA bid math reverts at scale; mandatory "
            "quality bonuses + supplemental benefits "
            "strained unit economics. Star ratings "
            "slipped; revenue per member compressed."
        ),
        ebitda_destruction_pct=0.70,
        early_warning_signals=[
            "Medical-loss ratio rising faster than "
            "enrollment",
            "Star-rating trajectory flat or declining",
            "Supplemental benefits outpacing bid approval",
        ],
        partner_lesson=(
            "MA plan underwriting is bid-math driven. "
            "Do not take enrollment growth as proxy for "
            "margin — measure MLR by cohort vintage."
        ),
        packet_triggers=[
            "ma_plan_platform",
            "mlr_rising_trend",
            "enrollment_outpacing_margin",
        ],
    ),
    FailurePatternV2(
        name="behavioral_staffing_collapse_2024",
        year=2024,
        deal_summary=(
            "Behavioral-health roll-up platform hit "
            "clinician-supply wall; therapist waits "
            "stretched to 8+ weeks, utilization plunged."
        ),
        thesis_at_entry=(
            "Parity enforcement + pandemic demand = "
            "behavioral-health rollup thesis with "
            "national coverage."
        ),
        what_went_wrong=(
            "Therapist supply grew 3%/yr; demand grew "
            "15%+. Platform couldn't recruit fast enough; "
            "incumbent clinicians burned out and quit. "
            "Utilization dropped from 80% to 55%, "
            "collapsing margin."
        ),
        ebitda_destruction_pct=0.45,
        early_warning_signals=[
            "Clinician vacancy > 15%",
            "New-patient wait > 4 weeks",
            "Clinician turnover > 25%/yr",
        ],
        partner_lesson=(
            "In behavioral health, supply is the ceiling, "
            "not demand. Underwrite therapist-hiring "
            "cadence explicitly."
        ),
        packet_triggers=[
            "behavioral_health_platform",
            "clinician_vacancy_gt_15pct",
            "wait_time_gt_4_weeks",
        ],
    ),
    FailurePatternV2(
        name="pdgm_transition_fallout_2020",
        year=2020,
        deal_summary=(
            "Home-health agencies that hadn't adapted "
            "coding / case-mix management for PDGM saw "
            "reimbursement fall 8-15%."
        ),
        thesis_at_entry=(
            "Aging demographics + post-acute shift = "
            "home-health growth; PDGM is just a "
            "reimbursement form change."
        ),
        what_went_wrong=(
            "PDGM required new clinical documentation + "
            "case-mix coding discipline. Agencies without "
            "CDI infrastructure lost 10%+ revenue per "
            "episode; LUPA rates rose."
        ),
        ebitda_destruction_pct=0.35,
        early_warning_signals=[
            "LUPA rate > 10%",
            "Case-mix index below national median",
            "No CDI / ICD-10 training program",
        ],
        partner_lesson=(
            "Reimbursement form changes are operating "
            "changes. Verify CDI infrastructure before "
            "underwriting PDGM-era case-mix stability."
        ),
        packet_triggers=[
            "home_health_platform",
            "lupa_rate_gt_10pct",
            "no_cdi_program",
        ],
    ),
    FailurePatternV2(
        name="nsa_platform_rate_shock_2022",
        year=2022,
        deal_summary=(
            "Out-of-network billing platforms (ED, anes, "
            "radiology, pathology) hit by the No "
            "Surprises Act arbitration rules."
        ),
        thesis_at_entry=(
            "OON billing premium persists despite "
            "legislation; arbitration will favor "
            "providers."
        ),
        what_went_wrong=(
            "NSA's independent-dispute-resolution "
            "process systematically favored payer-"
            "submitted median rates. OON premium "
            "eroded 30-50% in affected specialties; "
            "platform EBITDA reset."
        ),
        ebitda_destruction_pct=0.40,
        early_warning_signals=[
            "OON billing > 25% of revenue",
            "Specialty in NSA-affected category",
            "No in-network contracting strategy",
        ],
        partner_lesson=(
            "Regulatory changes that shift bargaining "
            "power to payers compound with rate-card "
            "anchor effect. Do not assume grandfather."
        ),
        packet_triggers=[
            "oon_billing_gt_25pct",
            "nsa_affected_specialty",
            "emergency_anesthesia_radiology_pathology",
        ],
    ),
    FailurePatternV2(
        name="ma_provider_risk_contract_2023",
        year=2023,
        deal_summary=(
            "Primary-care platforms taking global-risk "
            "MA contracts without actuarial chassis."
        ),
        thesis_at_entry=(
            "Global-risk MA contracts unlock premium "
            "economics; primary-care ownership = MA "
            "insurer-adjacent margin."
        ),
        what_went_wrong=(
            "Providers underestimated medical-cost "
            "volatility + risk-adjustment documentation "
            "rigor. Capitated losses ate into operating "
            "margin; several platforms restated EBITDA."
        ),
        ebitda_destruction_pct=0.55,
        early_warning_signals=[
            "Global-risk MA contracts > 30% revenue",
            "No actuarial team in-house",
            "Risk-adjustment audit exposure",
        ],
        partner_lesson=(
            "Taking MA risk without an actuarial chassis "
            "is a one-shot roll. Partner demands actuarial "
            "integration plan before closing."
        ),
        packet_triggers=[
            "global_risk_ma_gt_30pct",
            "no_actuarial_team",
            "risk_adjustment_audit_exposure",
        ],
    ),
    FailurePatternV2(
        name="tele_health_hype_fade_2023",
        year=2023,
        deal_summary=(
            "Virtual-care valuations compressed 70%+ as "
            "in-person utilization returned post-COVID."
        ),
        thesis_at_entry=(
            "Virtual-care TAM permanently reset upward; "
            "multiple expansion to 20x+ justified."
        ),
        what_went_wrong=(
            "Virtual-visit share settled at 10-15% of "
            "total volumes, not 40%+. Unit economics at "
            "smaller scale weren't competitive with "
            "incumbent outpatient operators."
        ),
        ebitda_destruction_pct=0.60,
        early_warning_signals=[
            "Virtual revenue share > 50%",
            "Exit multiple > 15x assumed at peak",
            "No in-person infrastructure",
        ],
        partner_lesson=(
            "COVID-driven utilization is not secular. "
            "Price virtual platforms off normalized "
            "utilization, not peak."
        ),
        packet_triggers=[
            "virtual_revenue_gt_50pct",
            "peak_covid_base_year",
            "exit_multiple_assumed_gt_15x",
        ],
    ),
    FailurePatternV2(
        name="rcm_vendor_concentration_loss_2022",
        year=2022,
        deal_summary=(
            "RCM-as-a-service platform lost its top-3 "
            "anchor hospital client representing > 30% "
            "of revenue."
        ),
        thesis_at_entry=(
            "Anchor hospital network stable; rolling "
            "3-year contract; expansion into additional "
            "service lines."
        ),
        what_went_wrong=(
            "Hospital system was acquired by health "
            "system with in-house RCM capability. "
            "Contract non-renewed at end of term. "
            "Platform's revenue base fell 30% overnight."
        ),
        ebitda_destruction_pct=0.50,
        early_warning_signals=[
            "Top customer > 25% of revenue",
            "Top-3 customer concentration > 50%",
            "Customer in active M&A conversations",
        ],
        partner_lesson=(
            "Customer concentration in B2B health-"
            "services is a single point of failure. "
            "Price in post-concentration EBITDA or walk."
        ),
        packet_triggers=[
            "rcm_vendor_platform",
            "top_customer_pct_gt_25",
            "top_3_concentration_gt_50pct",
        ],
    ),
    FailurePatternV2(
        name="dental_dso_over_rollup_2021",
        year=2021,
        deal_summary=(
            "Dental DSO acquired aggressively at 10x+ "
            "cash flow; dentist attrition + integration "
            "costs compounded."
        ),
        thesis_at_entry=(
            "DSO consolidation: scale drives margin "
            "through central services + broader "
            "insurance negotiation."
        ),
        what_went_wrong=(
            "Dentists resisted DSO operating model; "
            "senior dentists retired, junior dentists "
            "left for private practice. New-patient "
            "flow dropped 20%. Integration costs "
            "exceeded synergy capture."
        ),
        ebitda_destruction_pct=0.35,
        early_warning_signals=[
            "Dentist attrition > 20%/yr",
            "New-patient flow declining",
            "Acquisition pace > 1/quarter",
        ],
        partner_lesson=(
            "Dental DSO math only works if dentist "
            "retention holds. Rollover + employment "
            "contracts at close are non-negotiable."
        ),
        packet_triggers=[
            "dental_dso_platform",
            "dentist_attrition_gt_20pct",
            "acquisition_pace_high",
        ],
    ),
    FailurePatternV2(
        name="strategic_acquisition_peak_2022",
        year=2022,
        deal_summary=(
            "Strategic buyer acquired healthcare "
            "platform at cycle-peak multiple, then "
            "wrote down within 18 months."
        ),
        thesis_at_entry=(
            "Vertical integration synergies unlock "
            "long-term margin; strategic premium "
            "justified."
        ),
        what_went_wrong=(
            "Integration synergies materialized slower "
            "than modeled; cycle turned; strategic "
            "buyer impaired goodwill."
        ),
        ebitda_destruction_pct=0.30,
        early_warning_signals=[
            "Entry multiple > 16x",
            "Integration synergy bps > 300 in Y1",
            "Goodwill > 70% of purchase price",
        ],
        partner_lesson=(
            "Strategic premium is justified only if "
            "synergies are Y1 identifiable. Post-COVID "
            "strategic premia often reflected "
            "desperation, not thesis."
        ),
        packet_triggers=[
            "strategic_buyer_exit_comp",
            "entry_multiple_gt_16",
            "goodwill_share_gt_70pct",
        ],
    ),
    FailurePatternV2(
        name="ma_benefit_lockout_decay_2018",
        year=2018,
        deal_summary=(
            "MA supplemental-benefit platform (gym, "
            "OTC, meal) lost differentiation as plans "
            "expanded benefit scope."
        ),
        thesis_at_entry=(
            "MA lock-in benefits create sticky member "
            "retention; platform captures the benefit-"
            "delivery spend."
        ),
        what_went_wrong=(
            "MA plans built in-house or partnered "
            "directly with benefit providers. Platform's "
            "intermediary role compressed. Margin "
            "halved as plans insourced."
        ),
        ebitda_destruction_pct=0.50,
        early_warning_signals=[
            "MA plan concentration > 40% of revenue",
            "Benefit scope mirrored by plan insourcing",
            "No proprietary clinical content",
        ],
        partner_lesson=(
            "Intermediary roles in MA benefits compress "
            "as plans scale insourcing. Own the "
            "clinical content, not the delivery channel."
        ),
        packet_triggers=[
            "ma_supplemental_benefit_platform",
            "ma_plan_concentration_gt_40pct",
            "no_proprietary_clinical_content",
        ],
    ),
]


@dataclass
class FailureMatchV2:
    pattern: FailurePatternV2
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern.to_dict(),
            "reason": self.reason,
        }


def _v2_matchers() -> Dict[
    str, Callable[[Dict[str, Any]], bool]
]:
    def _ma_startup(c: Dict[str, Any]) -> bool:
        return (
            bool(c.get("ma_plan_platform", False))
            and (bool(c.get("mlr_rising_trend", False))
                 or bool(c.get("enrollment_outpacing_margin",
                                 False)))
        )

    def _behav_staff(c: Dict[str, Any]) -> bool:
        return (
            bool(c.get("behavioral_health_platform", False))
            and (bool(c.get("clinician_vacancy_gt_15pct",
                             False))
                 or bool(c.get("wait_time_gt_4_weeks",
                                False)))
        )

    def _pdgm(c: Dict[str, Any]) -> bool:
        return (
            bool(c.get("home_health_platform", False))
            and (bool(c.get("lupa_rate_gt_10pct", False))
                 or bool(c.get("no_cdi_program", False)))
        )

    def _nsa(c: Dict[str, Any]) -> bool:
        return (
            float(c.get("oon_billing_pct", 0)) >= 0.25
            or bool(c.get("nsa_affected_specialty", False))
        )

    def _ma_risk(c: Dict[str, Any]) -> bool:
        return (
            float(c.get("global_risk_ma_pct", 0)) >= 0.30
            and bool(c.get("no_actuarial_team", False))
        )

    def _tele(c: Dict[str, Any]) -> bool:
        return (
            float(c.get("virtual_revenue_pct", 0)) > 0.50
            or bool(c.get("peak_covid_base_year", False))
        )

    def _rcm_concentration(c: Dict[str, Any]) -> bool:
        return (
            float(c.get("top_customer_pct", 0)) > 0.25
            or float(c.get("top_3_concentration_pct", 0)) > 0.50
        )

    def _dental(c: Dict[str, Any]) -> bool:
        return (
            bool(c.get("dental_dso_platform", False))
            and (float(c.get("dentist_attrition_pct", 0)) > 0.20
                 or bool(c.get("acquisition_pace_high",
                                 False)))
        )

    def _strategic_peak(c: Dict[str, Any]) -> bool:
        return (
            float(c.get("entry_multiple", 0)) > 16.0
            and float(c.get("goodwill_share_pct", 0)) > 0.70
        )

    def _ma_benefit(c: Dict[str, Any]) -> bool:
        return (
            bool(c.get("ma_supplemental_benefit_platform",
                        False))
            and float(c.get("ma_plan_concentration_pct", 0)
                       ) > 0.40
        )

    return {
        "ma_startup_unwind_2023": _ma_startup,
        "behavioral_staffing_collapse_2024": _behav_staff,
        "pdgm_transition_fallout_2020": _pdgm,
        "nsa_platform_rate_shock_2022": _nsa,
        "ma_provider_risk_contract_2023": _ma_risk,
        "tele_health_hype_fade_2023": _tele,
        "rcm_vendor_concentration_loss_2022":
            _rcm_concentration,
        "dental_dso_over_rollup_2021": _dental,
        "strategic_acquisition_peak_2022": _strategic_peak,
        "ma_benefit_lockout_decay_2018": _ma_benefit,
    }


def match_failures_v2(
    ctx: Dict[str, Any],
) -> List[FailureMatchV2]:
    matchers = _v2_matchers()
    hits: List[FailureMatchV2] = []
    for p in FAILURE_LIBRARY_V2:
        fn = matchers.get(p.name)
        if fn is None:
            continue
        try:
            if fn(ctx):
                hits.append(FailureMatchV2(
                    pattern=p,
                    reason=(
                        f"Packet matches {p.name} signature; "
                        f"{p.partner_lesson}"
                    ),
                ))
        except Exception:
            continue
    return hits


def list_failure_patterns_v2() -> List[str]:
    return [p.name for p in FAILURE_LIBRARY_V2]


def render_failures_v2_markdown(
    matches: List[FailureMatchV2],
) -> str:
    if not matches:
        return (
            "# Historical failure library V2\n\n"
            "_No V2 named patterns match this deal._"
        )
    lines = [
        "# Historical failure library V2 — pattern matches",
        "",
        "_Partner reads these as \"this deal looks like "
        "<X>\". Each is a strong prior against the thesis "
        "unless specifically mitigated._",
        "",
    ]
    for m in matches:
        p = m.pattern
        lines.append(f"## {p.name} ({p.year})")
        lines.append(f"- **Thesis at entry:** {p.thesis_at_entry}")
        lines.append(f"- **What went wrong:** {p.what_went_wrong}")
        lines.append(
            f"- **EBITDA destruction:** "
            f"~{p.ebitda_destruction_pct*100:.0f}%"
        )
        lines.append(f"- **Partner lesson:** {p.partner_lesson}")
        lines.append("")
    return "\n".join(lines)
