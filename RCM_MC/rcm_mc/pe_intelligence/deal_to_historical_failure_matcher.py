"""Match deal to historical failures — partner's pattern-match reflex.

Partner statement: "Every deal I see, I ask: what
blow-up does this look like? Not for catastrophism —
to pull the specific lesson that applies. The
sponsor who thought MA risk was priced right in 2023
didn't have a bad model; they had an under-updated
pattern library. The partner reading this same deal
last year would have said 'I've seen this movie,
here's the reel.' That's pattern-matching."

Distinct from:
- `failure_archetype_library` / `named_failure_library_v2`
  — the failure catalog.
- `cross_pattern_digest` — integrates failure + bear +
  trap libraries at the module-output level.

This module operates at the **signal-fingerprint**
level. Given a fresh deal's diagnostic signals, it
computes similarity to 20 dated historical failures
and returns the top matches with the specific lesson.

### Matching method

Each historical failure has a fingerprint: a set of
named signal conditions that were true for the
failed deal. The matcher checks the current deal's
signals against each fingerprint and scores by:

- **hits** — number of conditions that match.
- **coverage** — hits / total conditions in fingerprint.
- **specificity** — average rarity of matched conditions
  (rare conditions score higher).

### 20 dated failures with fingerprints

Drawn from the shape of healthcare-PE stress events
2018-2024. These are shape-level pattern anchors, not
forensic recreations of specific sponsor deals.

Each failure carries:
- year, name, one-sentence lesson
- 4-7 signal conditions that triggered the pattern

### Output

Top-3 historical-failure matches + specific-lesson
application to current deal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class HistoricalDealSignals:
    """A loose bag of signals covering 2018-2024 failure patterns.
    Each field is optional; only set signals that apply.
    """
    subsector: str = ""
    ma_risk_contract_assumed: bool = False
    ma_enrollment_ramp_assumed_rapid: bool = False
    behavioral_health: bool = False
    clinician_supply_stretched: bool = False
    home_health: bool = False
    hold_spans_pdgm_transition: bool = False
    out_of_network_billing_heavy: bool = False
    nsa_exposure: bool = False
    primary_care_risk_platform: bool = False
    telehealth: bool = False
    valuation_peak_era: bool = False
    rcm_as_service: bool = False
    top_customer_concentration_pct: float = 0.0
    dental_dso: bool = False
    bolt_on_pace_aggressive: bool = False
    strategic_peak_acquirer_era: bool = False
    ma_benefit_differentiation_assumed: bool = False
    rural_hospital: bool = False
    aca_exchange_dependent: bool = False
    fresh_medicaid_cut_state: bool = False
    standalone_lab_imaging: bool = False
    pama_phase_in_hold: bool = False
    leverage_turns: float = 0.0
    covenant_tight: bool = False
    denial_rate_aggressive_fix_assumed: bool = False
    payer_renegotiation_in_hold: bool = False
    ffs_to_ma_cover_narrative: bool = False
    cmi_coding_aggressive_claim: bool = False
    owner_comp_addback_large: bool = False
    single_physician_top_producer: bool = False
    rural_cah_high_irr_claim: bool = False


@dataclass
class HistoricalFailure:
    name: str
    year: int
    lesson: str
    conditions: List[Tuple[str, Callable[[HistoricalDealSignals], bool]]]
    rarity_weight: float = 1.0
    specific_application: str = ""


_FAILURES: List[HistoricalFailure] = [
    HistoricalFailure(
        name="ma_startup_unwind_2023",
        year=2023,
        lesson=(
            "MA risk contracts look accretive until "
            "enrollment ramp misses OR cost trend spikes; "
            "either leg sinks the platform."
        ),
        conditions=[
            ("ma_risk_contract_assumed",
             lambda s: s.ma_risk_contract_assumed),
            ("rapid_ma_enrollment_ramp",
             lambda s: s.ma_enrollment_ramp_assumed_rapid),
            ("ffs_to_ma_cover_narrative",
             lambda s: s.ffs_to_ma_cover_narrative),
        ],
        rarity_weight=1.2,
        specific_application=(
            "If the current deal's MA growth pipeline "
            "doesn't have a named contract AND cost-trend "
            "assumption < 5%, the 2023 unwind shape "
            "applies."
        ),
    ),
    HistoricalFailure(
        name="behavioral_staffing_collapse_2024",
        year=2024,
        lesson=(
            "Behavioral-health platforms growing through "
            "2023 missed the clinician supply cliff; "
            "volume-based thesis collapsed on empty rooms."
        ),
        conditions=[
            ("behavioral_health",
             lambda s: s.behavioral_health),
            ("clinician_supply_stretched",
             lambda s: s.clinician_supply_stretched),
        ],
        rarity_weight=1.3,
        specific_application=(
            "Confirm current deal's hiring plan against "
            "BLS therapist/counselor supply in the MSA "
            "before underwriting volume growth."
        ),
    ),
    HistoricalFailure(
        name="pdgm_transition_fallout_2020",
        year=2020,
        lesson=(
            "Home-health agencies that missed PDGM coding "
            "shift lost EBITDA overnight; the coding gap "
            "was visible 12 months prior in the data."
        ),
        conditions=[
            ("home_health",
             lambda s: s.home_health),
            ("hold_spans_pdgm_transition",
             lambda s: s.hold_spans_pdgm_transition),
        ],
        rarity_weight=1.0,
        specific_application=(
            "Trace current deal's CDI / coding "
            "preparedness; a PDPM-style shift is "
            "recurring in SNF, and the pattern repeats."
        ),
    ),
    HistoricalFailure(
        name="nsa_platform_rate_shock_2022",
        year=2022,
        lesson=(
            "No Surprises Act compressed OON billing "
            "platforms' rate realization by 30-50% within "
            "12 months; IDR arbitration was not the "
            "backstop the thesis assumed."
        ),
        conditions=[
            ("out_of_network_billing_heavy",
             lambda s: s.out_of_network_billing_heavy),
            ("nsa_exposure",
             lambda s: s.nsa_exposure),
        ],
        rarity_weight=1.2,
        specific_application=(
            "If current deal still has material OON mix, "
            "model rate at QPA floor, not billed charges."
        ),
    ),
    HistoricalFailure(
        name="ma_provider_risk_contract_2023",
        year=2023,
        lesson=(
            "Primary-care platforms assumed MA risk they "
            "couldn't price; MLR blew through 90% within "
            "18 months."
        ),
        conditions=[
            ("primary_care_risk_platform",
             lambda s: s.primary_care_risk_platform),
            ("ma_risk_contract_assumed",
             lambda s: s.ma_risk_contract_assumed),
        ],
        rarity_weight=1.4,
        specific_application=(
            "Confirm platform has actuarial team and "
            "stop-loss reinsurance; otherwise the 2023 "
            "shape is likely."
        ),
    ),
    HistoricalFailure(
        name="tele_health_hype_fade_2023",
        year=2023,
        lesson=(
            "Virtual-care multiples compressed 60-80% "
            "post-COVID surge; the 'stickiness' thesis "
            "didn't survive reimbursement normalization."
        ),
        conditions=[
            ("telehealth",
             lambda s: s.telehealth),
            ("valuation_peak_era",
             lambda s: s.valuation_peak_era),
        ],
        rarity_weight=1.1,
        specific_application=(
            "Price-in permanent reimbursement regression "
            "for telehealth service lines; only platform "
            "services with strong IRL complement hold."
        ),
    ),
    HistoricalFailure(
        name="rcm_vendor_concentration_loss_2022",
        year=2022,
        lesson=(
            "RCM-as-a-service platforms lost single "
            "anchor customer → 40% revenue gone in one "
            "quarter; concentration was the binding "
            "constraint, not growth."
        ),
        conditions=[
            ("rcm_as_service",
             lambda s: s.rcm_as_service),
            ("top_customer_concentration",
             lambda s: s.top_customer_concentration_pct > 0.25),
        ],
        rarity_weight=1.3,
        specific_application=(
            "Top-customer retention risk must be modeled "
            "at < 25% top-1 before any growth thesis."
        ),
    ),
    HistoricalFailure(
        name="dental_dso_over_rollup_2021",
        year=2021,
        lesson=(
            "Dental DSOs over-acquired at top of cycle; "
            "integration debt > platform multiple arb, "
            "and bolt-on multiples rose faster than the "
            "platform's own growth."
        ),
        conditions=[
            ("dental_dso",
             lambda s: s.dental_dso),
            ("bolt_on_pace_aggressive",
             lambda s: s.bolt_on_pace_aggressive),
            ("valuation_peak_era",
             lambda s: s.valuation_peak_era),
        ],
        rarity_weight=1.2,
        specific_application=(
            "Run rollup_arbitrage_math — if multiple-bet "
            "share > 50%, this shape applies."
        ),
    ),
    HistoricalFailure(
        name="strategic_acquisition_peak_2022",
        year=2022,
        lesson=(
            "Strategic buyer paid peak multiple for "
            "healthcare services asset; wrote it down "
            "within 24 months when regulatory + labor "
            "pressure hit."
        ),
        conditions=[
            ("strategic_peak_acquirer_era",
             lambda s: s.strategic_peak_acquirer_era),
            ("valuation_peak_era",
             lambda s: s.valuation_peak_era),
        ],
        rarity_weight=1.0,
        specific_application=(
            "If exit thesis leans on strategic acquirer "
            "at current multiples, stress-test exit "
            "multiple down 2-3 turns."
        ),
    ),
    HistoricalFailure(
        name="ma_benefit_lockout_decay_2018",
        year=2018,
        lesson=(
            "MA 'lock-in' benefits (gym, OTC) stopped "
            "differentiating as all MA plans added them; "
            "retention assumption collapsed."
        ),
        conditions=[
            ("ma_benefit_differentiation_assumed",
             lambda s: s.ma_benefit_differentiation_assumed),
        ],
        rarity_weight=0.9,
        specific_application=(
            "MA retention thesis must be grounded in "
            "clinical-quality differentiation, not OTC "
            "benefit differentiation."
        ),
    ),
    HistoricalFailure(
        name="rural_cah_high_irr_pattern",
        year=2022,
        lesson=(
            "Rural critical-access hospital deals "
            "projecting > 20% IRR consistently missed; "
            "FFS floor + labor structure is unforgiving."
        ),
        conditions=[
            ("rural_cah",
             lambda s: s.rural_hospital),
            ("cah_high_irr_claim",
             lambda s: s.rural_cah_high_irr_claim),
        ],
        rarity_weight=1.3,
        specific_application=(
            "Rural CAH economics cap at 10-14% IRR "
            "realistically — re-underwrite."
        ),
    ),
    HistoricalFailure(
        name="aca_exchange_shock_2018",
        year=2018,
        lesson=(
            "ACA exchange-dependent providers took a "
            "50% enrollment hit when subsidies shifted; "
            "exchange-heavy revenue base is unstable."
        ),
        conditions=[
            ("aca_exchange_dependent",
             lambda s: s.aca_exchange_dependent),
        ],
        rarity_weight=1.0,
        specific_application=(
            "If > 15% of revenue is exchange-dependent, "
            "stress subsidy policy in exit-case."
        ),
    ),
    HistoricalFailure(
        name="state_medicaid_rebasing_2019",
        year=2019,
        lesson=(
            "States that cut Medicaid rates mid-cycle "
            "(e.g., NY, CA) — providers absorbed 3-5% "
            "overnight rate cuts; DSH recapture came next."
        ),
        conditions=[
            ("fresh_medicaid_cut_state",
             lambda s: s.fresh_medicaid_cut_state),
        ],
        rarity_weight=1.1,
        specific_application=(
            "Medicaid-heavy deals in NY/CA/OR must "
            "stress rate cut + DSH at exit."
        ),
    ),
    HistoricalFailure(
        name="pama_lab_phase_in_2024",
        year=2024,
        lesson=(
            "PAMA Phase 4 cut clinical-lab rates by 15%; "
            "standalone lab platforms lost 20%+ EBITDA."
        ),
        conditions=[
            ("standalone_lab_imaging",
             lambda s: s.standalone_lab_imaging),
            ("pama_phase_in_hold",
             lambda s: s.pama_phase_in_hold),
        ],
        rarity_weight=1.2,
        specific_application=(
            "PAMA Phase 5 timing is the same shape — "
            "price in for any lab/imaging deal with hold "
            "into 2027-2029."
        ),
    ),
    HistoricalFailure(
        name="over_leveraged_healthcare_2022",
        year=2022,
        lesson=(
            "6.5× leverage + labor inflation + rate "
            "pressure = covenant breach within 18 months; "
            "not a crash, a slow-walk to restructure."
        ),
        conditions=[
            ("high_leverage",
             lambda s: s.leverage_turns > 6.0),
            ("covenant_tight",
             lambda s: s.covenant_tight),
        ],
        rarity_weight=1.0,
        specific_application=(
            "If current deal > 6.0x with < 20% covenant "
            "headroom, this shape is likely in the bear."
        ),
    ),
    HistoricalFailure(
        name="denial_fix_overpromise_2020",
        year=2020,
        lesson=(
            "Sponsors who promised 300 bps denial fix "
            "in year 1 typically realized 50-80 bps; "
            "medical-necessity denials never moved."
        ),
        conditions=[
            ("denial_rate_aggressive_claim",
             lambda s: s.denial_rate_aggressive_fix_assumed),
        ],
        rarity_weight=1.1,
        specific_application=(
            "See denial_fix_pace_detector — empirical "
            "pace is 55-65 bps/yr achievable; trap fires "
            "above 100."
        ),
    ),
    HistoricalFailure(
        name="payer_renegotiation_miss_2021",
        year=2021,
        lesson=(
            "Top-3 commercial payer renegotiation hit "
            "platforms mid-hold at -3% to -5%; exit "
            "buyers modeled it in and compressed multiples."
        ),
        conditions=[
            ("payer_renegotiation_in_hold",
             lambda s: s.payer_renegotiation_in_hold),
        ],
        rarity_weight=1.1,
        specific_application=(
            "See payer_renegotiation_timing_model — "
            "bake expected cut into exit-case EBITDA."
        ),
    ),
    HistoricalFailure(
        name="cmi_rac_recapture_2019",
        year=2019,
        lesson=(
            "Aggressive CMI uplift thesis attracted RAC "
            "audits; recapture + penalties erased 24 "
            "months of bridge."
        ),
        conditions=[
            ("cmi_coding_aggressive",
             lambda s: s.cmi_coding_aggressive_claim),
        ],
        rarity_weight=1.1,
        specific_application=(
            "CMI claims > 50 bps in year 1 invite RAC "
            "attention; dial to physician-documentation "
            "thesis, not coder-aggressiveness."
        ),
    ),
    HistoricalFailure(
        name="owner_comp_qofe_haircut_2020",
        year=2020,
        lesson=(
            "Large owner-comp normalization add-backs "
            "haircut 40-60% at QofE; pre-LOI value "
            "indication collapsed."
        ),
        conditions=[
            ("owner_comp_addback_large",
             lambda s: s.owner_comp_addback_large),
        ],
        rarity_weight=0.9,
        specific_application=(
            "Pre-LOI pricing should model owner-comp "
            "addback at 50% survival."
        ),
    ),
    HistoricalFailure(
        name="single_producer_physician_walk_2021",
        year=2021,
        lesson=(
            "Platform lost top-1 physician producer 9 "
            "months post-close — 40% revenue walked with "
            "referral book."
        ),
        conditions=[
            ("top_producer_concentration",
             lambda s: s.single_physician_top_producer),
        ],
        rarity_weight=1.2,
        specific_application=(
            "See physician_retention_stress — top-1 loss "
            "acceptable-or-price-in-or-walk triage."
        ),
    ),
]


@dataclass
class HistoricalMatch:
    failure_name: str
    year: int
    hits: int
    coverage: float
    specificity_score: float
    matched_conditions: List[str]
    lesson: str
    specific_application: str


@dataclass
class HistoricalMatchReport:
    matches: List[HistoricalMatch] = field(
        default_factory=list)
    top_matches: List[HistoricalMatch] = field(
        default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        def _dump(m: HistoricalMatch) -> Dict[str, Any]:
            return {
                "failure_name": m.failure_name,
                "year": m.year,
                "hits": m.hits,
                "coverage": m.coverage,
                "specificity_score": m.specificity_score,
                "matched_conditions": m.matched_conditions,
                "lesson": m.lesson,
                "specific_application":
                    m.specific_application,
            }
        return {
            "matches": [_dump(m) for m in self.matches],
            "top_matches": [
                _dump(m) for m in self.top_matches],
            "partner_note": self.partner_note,
        }


def match_to_historical_failures(
    signals: HistoricalDealSignals,
) -> HistoricalMatchReport:
    matches: List[HistoricalMatch] = []
    for f in _FAILURES:
        matched_conditions = []
        for cond_name, predicate in f.conditions:
            if predicate(signals):
                matched_conditions.append(cond_name)
        hits = len(matched_conditions)
        if hits == 0:
            continue
        coverage = hits / max(1, len(f.conditions))
        # Specificity: rarity-weighted coverage
        specificity = coverage * f.rarity_weight
        matches.append(HistoricalMatch(
            failure_name=f.name,
            year=f.year,
            hits=hits,
            coverage=round(coverage, 3),
            specificity_score=round(specificity, 3),
            matched_conditions=matched_conditions,
            lesson=f.lesson,
            specific_application=f.specific_application,
        ))

    # Sort by specificity, descending
    matches.sort(
        key=lambda m: m.specificity_score, reverse=True)
    top = matches[:3]

    if not top:
        note = (
            "No historical-failure pattern matches "
            "fired on current signal set. Either deal is "
            "genuinely novel or signal set is too sparse; "
            "expand signal input before concluding."
        )
    elif top[0].specificity_score >= 0.9:
        note = (
            f"Strong match to "
            f"**{top[0].failure_name}** "
            f"({top[0].year}). "
            f"Lesson: {top[0].lesson} "
            f"Application: {top[0].specific_application} "
            "Treat this as a live pattern on the current "
            "deal."
        )
    elif top[0].specificity_score >= 0.5:
        note = (
            f"Partial match to "
            f"**{top[0].failure_name}** "
            f"({top[0].year}) and 2 others. "
            "Review the top-3 shapes before IC."
        )
    else:
        note = (
            f"Weak match to {len(top)} historical "
            "shapes — signals partially align but none "
            "decisively."
        )

    return HistoricalMatchReport(
        matches=matches,
        top_matches=top,
        partner_note=note,
    )


def render_historical_match_markdown(
    r: HistoricalMatchReport,
) -> str:
    lines = [
        "# Deal-to-historical-failure match",
        "",
        f"_{r.partner_note}_",
        "",
        "## Top matches",
    ]
    for m in r.top_matches:
        lines.append(
            f"### {m.failure_name} ({m.year}) — "
            f"coverage {m.coverage:.0%}, "
            f"specificity {m.specificity_score:.2f}"
        )
        lines.append("")
        lines.append(f"**Lesson:** {m.lesson}")
        lines.append("")
        lines.append(
            f"**Application:** {m.specific_application}")
        lines.append("")
        lines.append(
            "**Matched conditions:** "
            + ", ".join(m.matched_conditions)
        )
        lines.append("")
    return "\n".join(lines)
