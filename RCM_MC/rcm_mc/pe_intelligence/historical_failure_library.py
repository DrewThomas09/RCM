"""Historical failure library — named/dated healthcare-PE disasters.

Bear-book patterns are generic. What partners actually reason from
is specific named incidents: "this looks like Envision 2023" or
"Steward-style REIT sale-leaseback dependency". Each entry here
captures:

- **Name, year, thesis, what went wrong, EBITDA destruction, and
  the packet fields / patterns that would have flagged it.**

The library is opinionated. These are not neutral case studies —
they are the failures a partner internalizes and pattern-matches
against. Use ``match_failures(ctx)`` to scan a packet-like context
dict and return patterns that apply.

Partner voice: terse, numbers-first, no hedging. Each pattern
includes the one-sentence lesson a partner would say in IC.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class FailurePattern:
    name: str
    year: int
    deal_summary: str
    thesis_at_entry: str
    what_went_wrong: str
    ebitda_destruction_pct: float         # approximate impact
    early_warning_signals: List[str] = field(default_factory=list)
    partner_lesson: str = ""
    packet_triggers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "year": self.year,
            "deal_summary": self.deal_summary,
            "thesis_at_entry": self.thesis_at_entry,
            "what_went_wrong": self.what_went_wrong,
            "ebitda_destruction_pct": self.ebitda_destruction_pct,
            "early_warning_signals": list(self.early_warning_signals),
            "partner_lesson": self.partner_lesson,
            "packet_triggers": list(self.packet_triggers),
        }


# Named + dated failure patterns. Year is entry or pivotal year.
# ebitda_destruction_pct is approximate and partner-judged.
FAILURE_LIBRARY: List[FailurePattern] = [
    FailurePattern(
        name="envision_surprise_billing_2023",
        year=2023,
        deal_summary=("KKR acquired Envision Healthcare in 2018 for "
                      "$9.9B, making it the largest physician-staffing "
                      "PE deal. Filed Chapter 11 in May 2023."),
        thesis_at_entry=("Scale in ED / anesthesiology staffing enables "
                          "payer leverage; volume + pricing + efficiency "
                          "underpin 15%+ IRR."),
        what_went_wrong=("No Surprises Act (2022) stripped out-of-"
                          "network balance billing. United and Blue Cross "
                          "walked from in-network contracts. COVID "
                          "elective-volume collapse compounded the damage. "
                          "Revenue dropped ~25% from peak."),
        ebitda_destruction_pct=0.60,
        early_warning_signals=[
            "high_out_of_network_revenue_dependency",
            "contractual_leverage_vs_top_5_payers_thin",
            "legislative_risk_balance_billing",
            "physician_staffing_commodity_risk",
        ],
        partner_lesson=("When a thesis depends on balance billing or "
                        "out-of-network economics, legislative risk kills "
                        "the deal — not if, when."),
        packet_triggers=[
            "subsector == 'physician_staffing'",
            "top_payer_share < 0.15 AND OON share > 0.25",
            "surprise_billing_dependency flag",
        ],
    ),
    FailurePattern(
        name="steward_reit_dependency_2024",
        year=2024,
        deal_summary=("Cerberus spun Steward Health Care to Ralph de la "
                      "Torre; sale-leaseback with MPT. Steward filed "
                      "Chapter 11 in May 2024 amid multi-state hospital "
                      "closures and Mass AG investigation."),
        thesis_at_entry=("REIT sale-leaseback unlocks real-estate value; "
                          "cash payout to sponsor; operating hospitals "
                          "covers rent."),
        what_went_wrong=("MPT rent became unsustainable as operating "
                          "margins compressed; payer mix deteriorated; "
                          "closures triggered state AG action. Rent/EBITDA "
                          "ratio ballooned past 1.0x."),
        ebitda_destruction_pct=0.80,
        early_warning_signals=[
            "hospital_real_estate_sale_leaseback_done",
            "rent_to_ebitda_ratio > 0.50",
            "state_medicaid_heavy_plus_thin_commercial",
            "management_unwillingness_to_close_underperformers",
        ],
        partner_lesson=("Sale-leasebacks in hospitals externalize the "
                        "downside to management teams — look at "
                        "rent/EBITDA, not cash proceeds."),
        packet_triggers=[
            "sale_leaseback_in_thesis",
            "rent_to_ebitda > 0.50",
            "subsector == 'hospital'",
        ],
    ),
    FailurePattern(
        name="prospect_medical_cashflow_2023",
        year=2023,
        deal_summary=("Leonard Green's 2010 $205M Prospect Medical "
                      "buyout ended in bankruptcy filings by hospital "
                      "subsidiaries by 2025; billions in dividend "
                      "recaps extracted through early-decade holds."),
        thesis_at_entry=("Safety-net hospital acquirer with operating "
                          "margin expansion; dividend recaps to return "
                          "cash."),
        what_went_wrong=("Aggressive dividend recaps stripped cash. "
                          "Underinvestment in physical plant. Medicaid "
                          "rate freezes compressed margins. Several "
                          "hospitals failed CMS surveys."),
        ebitda_destruction_pct=0.70,
        early_warning_signals=[
            "multiple_dividend_recaps_first_3_years",
            "capex_reinvestment_below_peer_median",
            "medicaid_payer_mix > 0.40",
            "cms_survey_history_deteriorating",
        ],
        partner_lesson=("Healthcare assets need capex reinvestment. "
                        "Aggressive dividend recaps in safety-net "
                        "hospitals are a slow-motion detonation."),
        packet_triggers=[
            "dividend_recaps_executed >= 2",
            "capex_pct_revenue < 0.03",
            "medicaid_pct > 0.40",
        ],
    ),
    FailurePattern(
        name="hahnemann_bankruptcy_2019",
        year=2019,
        deal_summary=("Paladin Healthcare (Joel Freedman) closed "
                      "Hahnemann University Hospital in Philadelphia "
                      "only 18 months after acquisition."),
        thesis_at_entry=("Real-estate play disguised as operating turnaround."),
        what_went_wrong=("Lacked operating competence; residency program "
                          "disrupted; state intervention; reputation impact "
                          "on other Paladin assets."),
        ebitda_destruction_pct=1.00,
        early_warning_signals=[
            "sponsor_lacks_healthcare_operating_track_record",
            "real_estate_more_valuable_than_operating_enterprise",
            "academic_affiliation_risk",
        ],
        partner_lesson=("Real-estate-motivated healthcare buyouts invite "
                        "regulatory intervention when operations suffer. "
                        "Partners ask: would we keep operating if the "
                        "land were worthless?"),
        packet_triggers=[
            "ev_attributable_to_real_estate > 0.50",
            "academic_medical_center AND sponsor_ops_inexperience",
        ],
    ),
    FailurePattern(
        name="radiology_partners_rate_shock_2022",
        year=2022,
        deal_summary=("Radiology Partners (Starr / NEA / Hellman & "
                      "Friedman) faced major covenant pressure 2022-2023 "
                      "after rate hikes + NSA impact."),
        thesis_at_entry=("Consolidated radiology practices; leverage "
                          "payer scale; technology efficiency."),
        what_went_wrong=("Floating-rate debt + NSA compression + "
                          "aggressive leverage (~7x) collided. Needed "
                          "$400M+ sponsor support round."),
        ebitda_destruction_pct=0.30,
        early_warning_signals=[
            "leverage_at_close > 6.5",
            "floating_rate_debt_unhedged",
            "subsector_exposed_to_NSA",
        ],
        partner_lesson=("Healthcare specialty roll-ups leveraged > 6.5x "
                        "have no cushion for rate + legislative dual "
                        "shocks. Hedge the floaters."),
        packet_triggers=[
            "leverage > 6.5 AND floating_rate_unhedged",
            "subsector IN ('radiology', 'anesthesia', 'ED')",
        ],
    ),
    FailurePattern(
        name="adapthealth_accounting_2021",
        year=2021,
        deal_summary=("Short-seller reports on AdaptHealth (Deerfield / "
                      "others) alleged aggressive accounting and weak "
                      "controls; stock dropped ~40%."),
        thesis_at_entry=("Roll-up of DME suppliers; scale drives payer "
                          "leverage; back-office consolidation."),
        what_went_wrong=("Fragmented ERP; acquired businesses not fully "
                          "integrated; pro-forma EBITDA did not tie to "
                          "GAAP; CEO departed."),
        ebitda_destruction_pct=0.25,
        early_warning_signals=[
            "acquisitions_outpacing_integration",
            "pro_forma_vs_gaap_ebitda_gap > 0.15",
            "multiple_erps_unmerged > 3",
            "audit_firm_change_in_last_2yrs",
        ],
        partner_lesson=("If acquisition pace outstrips integration, the "
                        "pro-forma numbers are fiction until proven "
                        "otherwise. Trust GAAP, haircut pro-forma."),
        packet_triggers=[
            "acquisitions_per_year >= 5 AND platform_age < 3",
            "multiple_erps AND pro_forma_addbacks > 0.15",
        ],
    ),
    FailurePattern(
        name="kindred_at_home_2018",
        year=2018,
        deal_summary=("Humana + TPG + Welsh Carson bought Kindred at "
                      "Home; post-close PDGM (Patient-Driven Groupings "
                      "Model) in 2020 compressed home-health margins."),
        thesis_at_entry=("Aging demographics + value-based-care shift "
                          "drive home-health growth."),
        what_went_wrong=("PDGM reset reimbursement mid-hold; ~150 "
                          "unprofitable branches closed; margin "
                          "compression of 300-400 bps."),
        ebitda_destruction_pct=0.15,
        early_warning_signals=[
            "regulatory_reimbursement_method_change_pending",
            "subsector == 'home_health' AND 2018_to_2020_vintage",
            "cms_rulemaking_docket_open",
        ],
        partner_lesson=("Price regulation changes override operational "
                        "excellence. If CMS is rewriting the payment "
                        "methodology, assume it is coming and model "
                        "30% realization haircut on the transition."),
        packet_triggers=[
            "subsector == 'home_health'",
            "cms_rule_change_expected AND hold_year_overlap",
        ],
    ),
    FailurePattern(
        name="shopko_rx_pharmacy_2019",
        year=2019,
        deal_summary=("Sun Capital's pharmacy-chain strategy collapsed "
                      "after Shopko closure; pharmacy files transferred "
                      "to CVS / Walgreens."),
        thesis_at_entry=("Rural-community pharmacy roll-up with "
                          "generic-dispensing margin expansion."),
        what_went_wrong=("DIR fees ate gross-to-net; PBM rebate squeeze; "
                          "competitive CVS expansion into mail-order; "
                          "parent retail failure contaminated pharmacy "
                          "stream."),
        ebitda_destruction_pct=0.75,
        early_warning_signals=[
            "pharmacy_revenue_pct > 0.50 AND PBM_concentration > 3",
            "DIR_fees_rising_pct_gross",
            "parent_retail_operation_weakening",
        ],
        partner_lesson=("Pharmacy margins are set by 3 PBMs. DIR fees "
                        "will compress gross-to-net every year. If your "
                        "IRR depends on flat DIR fees, re-underwrite."),
        packet_triggers=[
            "pharmacy_revenue_share > 0.40",
            "dir_fee_trend_rising",
        ],
    ),
    FailurePattern(
        name="21st_century_oncology_2017",
        year=2017,
        deal_summary=("Vestar's 21st Century Oncology filed Chapter 11 "
                      "in 2017 following $55M FCA settlement and "
                      "leadership / fraud-allegation turmoil."),
        thesis_at_entry=("Consolidated outpatient oncology with scale "
                          "advantages in IMRT / proton / brachytherapy."),
        what_went_wrong=("FCA settlement; regulatory investigations; "
                          "physician departures; bond default; "
                          "bankruptcy. Reputational contagion to PE "
                          "firm."),
        ebitda_destruction_pct=0.85,
        early_warning_signals=[
            "open_fca_investigation_or_cid",
            "aggressive_billing_patterns_vs_peers",
            "physician_turnover > 0.20",
            "whistleblower_suits_pending",
        ],
        partner_lesson=("FCA exposure in oncology is existential. "
                        "Billing diligence must be forensic, not "
                        "sampling. Whistleblower suits almost never "
                        "get better."),
        packet_triggers=[
            "open_fca_exposure",
            "subsector == 'oncology'",
            "billing_variance_vs_peers > 2_stddev",
        ],
    ),
    FailurePattern(
        name="surgery_partners_leverage_2016",
        year=2016,
        deal_summary=("Bain's Surgery Partners platform faced leverage "
                      "strain as ASC volume growth under-delivered "
                      "underwrite; multiple refinancings and equity "
                      "infusions required."),
        thesis_at_entry=("ASC-led outpatient shift; specialty ortho/"
                          "GI/pain migration from hospitals; M&A engine."),
        what_went_wrong=("ASC volume ramp was slower than underwritten; "
                          "CoC frictions on payor renegotiation; "
                          "physician-partner attrition at acquired sites."),
        ebitda_destruction_pct=0.25,
        early_warning_signals=[
            "asc_volume_assumption_above_peer_median",
            "physician_equity_contingent_on_growth",
            "payer_renegotiation_timing_concentrated",
        ],
        partner_lesson=("ASC volume models that require 5%+ same-site "
                        "growth are aggressive. Flat or -2% is the "
                        "more common outcome. Haircut heavily."),
        packet_triggers=[
            "asc_same_site_growth_assumption > 0.05",
            "subsector == 'outpatient_asc'",
        ],
    ),
]


# Simple packet-field matchers. Each takes a context dict (fields read
# from a packet.to_dict()) and returns True when the pattern triggers.

MatcherFn = Callable[[Dict[str, Any]], bool]


def _get_float(ctx: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        v = ctx.get(key)
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def _get_str(ctx: Dict[str, Any], key: str, default: str = "") -> str:
    v = ctx.get(key)
    return str(v) if v is not None else default


def _get_bool(ctx: Dict[str, Any], key: str, default: bool = False) -> bool:
    return bool(ctx.get(key, default))


def _matchers() -> Dict[str, MatcherFn]:
    # Each pattern name maps to a matcher over context keys.
    return {
        "envision_surprise_billing_2023": lambda ctx: (
            _get_str(ctx, "subsector") == "physician_staffing"
            and (_get_float(ctx, "oon_revenue_share") >= 0.25
                 or _get_bool(ctx, "surprise_billing_dependency"))
        ),
        "steward_reit_dependency_2024": lambda ctx: (
            _get_str(ctx, "subsector") == "hospital"
            and (_get_bool(ctx, "sale_leaseback_in_thesis")
                 or _get_float(ctx, "rent_to_ebitda") >= 0.50)
        ),
        "prospect_medical_cashflow_2023": lambda ctx: (
            _get_str(ctx, "subsector") in ("hospital", "safety_net_hospital")
            and _get_float(ctx, "dividend_recaps_executed") >= 2
            and _get_float(ctx, "capex_pct_revenue", 1.0) < 0.03
        ),
        "hahnemann_bankruptcy_2019": lambda ctx: (
            _get_float(ctx, "ev_attributable_to_real_estate") >= 0.50
            and _get_bool(ctx, "sponsor_ops_inexperience")
        ),
        "radiology_partners_rate_shock_2022": lambda ctx: (
            _get_float(ctx, "leverage") >= 6.5
            and _get_bool(ctx, "floating_rate_unhedged")
        ),
        "adapthealth_accounting_2021": lambda ctx: (
            _get_float(ctx, "acquisitions_per_year") >= 5
            and _get_float(ctx, "platform_age_years", 99.0) < 3
            and _get_float(ctx, "pro_forma_addbacks_pct") >= 0.15
        ),
        "kindred_at_home_2018": lambda ctx: (
            _get_str(ctx, "subsector") == "home_health"
            and _get_bool(ctx, "cms_rule_change_expected")
        ),
        "shopko_rx_pharmacy_2019": lambda ctx: (
            _get_float(ctx, "pharmacy_revenue_share") >= 0.40
            and _get_bool(ctx, "dir_fee_trend_rising")
        ),
        "21st_century_oncology_2017": lambda ctx: (
            _get_str(ctx, "subsector") == "oncology"
            and (_get_bool(ctx, "open_fca_exposure")
                 or _get_float(ctx, "billing_variance_vs_peers") >= 2.0)
        ),
        "surgery_partners_leverage_2016": lambda ctx: (
            _get_str(ctx, "subsector") == "outpatient_asc"
            and _get_float(ctx, "asc_same_site_growth_assumption") > 0.05
        ),
    }


@dataclass
class FailureMatch:
    pattern: FailurePattern
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {"pattern": self.pattern.to_dict(), "reason": self.reason}


def match_failures(ctx: Dict[str, Any]) -> List[FailureMatch]:
    """Scan a packet-like dict; return matching historical failure patterns."""
    matchers = _matchers()
    hits: List[FailureMatch] = []
    for p in FAILURE_LIBRARY:
        m = matchers.get(p.name)
        if m is None:
            continue
        try:
            if m(ctx):
                hits.append(FailureMatch(
                    pattern=p,
                    reason=(f"Packet matches {p.name} signature; "
                            f"{p.partner_lesson}"),
                ))
        except Exception:  # defensive — never break the pipeline
            continue
    return hits


def render_failures_markdown(matches: List[FailureMatch]) -> str:
    if not matches:
        return ("# Historical failure library\n\n"
                "_No historical failure patterns match this deal._")
    lines = [
        "# Historical failure library — pattern matches",
        "",
        "_Partner reads these as \"this deal looks like <X>\". "
        "Treat each as a strong prior against the thesis unless "
        "specifically mitigated in underwrite._",
        "",
    ]
    for m in matches:
        p = m.pattern
        lines.append(f"## {p.name} ({p.year})")
        lines.append(f"- **Thesis at entry:** {p.thesis_at_entry}")
        lines.append(f"- **What went wrong:** {p.what_went_wrong}")
        lines.append(f"- **EBITDA destruction:** "
                     f"~{p.ebitda_destruction_pct*100:.0f}%")
        lines.append(f"- **Partner lesson:** {p.partner_lesson}")
        lines.append("")
    return "\n".join(lines)


def list_all_patterns() -> List[FailurePattern]:
    """Return the full library (callers may render it as reference)."""
    return list(FAILURE_LIBRARY)
