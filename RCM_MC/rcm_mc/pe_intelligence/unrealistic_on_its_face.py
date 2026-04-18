"""Unrealistic-on-its-face detector.

Partner reflex: some deal profiles are red flags on sight, before
any model runs. Example the user named: "a $400M NPR rural
critical-access hospital projecting 28% IRR." That combination is
physically implausible — rural CAH economics + Medicare-dominant
payer mix + small scale cap the achievable IRR well below the
claim.

This module encodes rules a senior partner uses in 30 seconds:

1. **Subsector × payer mix × size × claimed IRR** — impossible
   combos fire a red flag.
2. **Claimed margin outside any peer range** — 22% EBITDA margin
   on a rural hospital is impossible; hospitals are 8-14%.
3. **Claimed growth + subsector maturity** — 25% growth on a
   mature specialty is implausible.
4. **Leverage × coverage combo** — 8x leverage with 3x coverage
   is arithmetic-impossible at market rates.

Each detector fires when a specific threshold is crossed. Output
is a list of `ImplausibilityFinding`s with the named reasoning and
the partner note a senior partner would put in margin: "pass
before we start the model."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FaceInputs:
    subsector: str = ""
    revenue_m: float = 0.0
    ebitda_m: float = 0.0
    ebitda_margin: Optional[float] = None  # computed if None
    medicare_pct: float = 0.0
    medicaid_pct: float = 0.0
    commercial_pct: float = 0.0
    claimed_irr: float = 0.0
    claimed_moic: float = 0.0
    claimed_annual_growth: float = 0.0
    leverage: float = 0.0
    claimed_interest_coverage: float = 0.0
    interest_rate: float = 0.095
    is_rural: bool = False
    is_critical_access: bool = False


@dataclass
class ImplausibilityFinding:
    name: str
    severity: str                         # "high" / "medium"
    claim: str
    reality: str
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "severity": self.severity,
            "claim": self.claim, "reality": self.reality,
            "partner_note": self.partner_note,
        }


def _rural_cah_high_irr(inputs: FaceInputs) -> Optional[ImplausibilityFinding]:
    if (inputs.is_critical_access or inputs.is_rural) \
            and inputs.claimed_irr >= 0.22:
        return ImplausibilityFinding(
            name="rural_cah_irr_implausible", severity="high",
            claim=(f"{inputs.claimed_irr*100:.0f}% IRR on "
                   f"rural/CAH asset at ${inputs.revenue_m:,.0f}M NPR."),
            reality=("Rural critical-access hospitals are cost-based "
                     "reimbursed with essentially no commercial "
                     "leverage. Historical vintage IRRs: mid-single-"
                     "digit to low-teens at BEST. 22%+ is not "
                     "achievable from this profile."),
            partner_note=("Pass before we start the model. Ask "
                          "seller to walk the bridge line-by-line, "
                          "then pass."),
        )
    return None


def _hospital_margin_out_of_range(
    inputs: FaceInputs,
) -> Optional[ImplausibilityFinding]:
    if inputs.subsector in ("hospital", "safety_net_hospital") \
            and inputs.revenue_m > 0:
        margin = (inputs.ebitda_margin if inputs.ebitda_margin is not None
                  else inputs.ebitda_m / max(0.01, inputs.revenue_m))
        if margin >= 0.20:
            return ImplausibilityFinding(
                name="hospital_margin_impossible", severity="high",
                claim=(f"{margin*100:.0f}% EBITDA margin on a hospital."),
                reality=("Hospital EBITDA margins run 8-14% typical; "
                         "top-decile ~ 16%. 20%+ is either non-GAAP "
                         "aggression or a non-hospital asset mis-"
                         "classified."),
                partner_note=("Pass, or demand line-by-line EBITDA "
                              "reconciliation before continuing."),
            )
    return None


def _practice_margin_out_of_range(
    inputs: FaceInputs,
) -> Optional[ImplausibilityFinding]:
    if inputs.subsector == "specialty_practice" and inputs.revenue_m > 0:
        margin = (inputs.ebitda_margin if inputs.ebitda_margin is not None
                  else inputs.ebitda_m / max(0.01, inputs.revenue_m))
        if margin >= 0.35:
            return ImplausibilityFinding(
                name="practice_margin_impossible", severity="medium",
                claim=(f"{margin*100:.0f}% margin on specialty practice."),
                reality=("Specialty-practice margins 18-28% typical; "
                         "35%+ either includes non-operating income or "
                         "is a cash-pay concierge model."),
                partner_note=("Check for cash-pay concentration or "
                              "non-operating EBITDA adds."),
            )
    return None


def _leverage_coverage_math(
    inputs: FaceInputs,
) -> Optional[ImplausibilityFinding]:
    if inputs.leverage >= 7.0 and inputs.claimed_interest_coverage >= 2.5:
        # EBITDA / (debt × rate). For 7x leverage at market rate,
        # coverage would be 1 / (7 × rate).
        implied_max = 1.0 / max(0.01, (inputs.leverage * inputs.interest_rate))
        if inputs.claimed_interest_coverage > implied_max * 1.1:
            return ImplausibilityFinding(
                name="leverage_coverage_impossible", severity="high",
                claim=(f"{inputs.leverage:.1f}x leverage AND "
                       f"{inputs.claimed_interest_coverage:.1f}x "
                       f"interest coverage."),
                reality=(f"At {inputs.leverage:.1f}x and "
                         f"{inputs.interest_rate*100:.1f}% rate, "
                         f"max implied coverage is "
                         f"{implied_max:.2f}x. The claim is "
                         "arithmetic-impossible."),
                partner_note=("Fix the math before IC. Either "
                              "leverage is lower or coverage is "
                              "lower; both cannot be true."),
            )
    return None


def _growth_out_of_range(
    inputs: FaceInputs,
) -> Optional[ImplausibilityFinding]:
    if inputs.subsector in ("hospital", "safety_net_hospital") \
            and inputs.claimed_annual_growth >= 0.12:
        return ImplausibilityFinding(
            name="hospital_growth_implausible", severity="high",
            claim=(f"{inputs.claimed_annual_growth*100:.0f}% annual "
                   "growth on a hospital book."),
            reality=("Hospital volume + price growth is 2-5% in "
                     "mature markets. 10%+ assumes M&A; strip it "
                     "out to see the organic base."),
            partner_note=("Underwrite organic separately from "
                          "inorganic. If the plan shows only "
                          "combined growth, push back."),
        )
    if inputs.subsector == "specialty_practice" \
            and inputs.claimed_annual_growth >= 0.25:
        return ImplausibilityFinding(
            name="practice_growth_implausible", severity="medium",
            claim=(f"{inputs.claimed_annual_growth*100:.0f}% annual "
                   "growth on specialty practice."),
            reality=("Specialty-practice organic growth rarely "
                     "exceeds 10-15% without M&A."),
            partner_note=("Separate organic from acquisition in "
                          "the underwrite."),
        )
    return None


def _medicare_heavy_with_high_margin(
    inputs: FaceInputs,
) -> Optional[ImplausibilityFinding]:
    if inputs.medicare_pct + inputs.medicaid_pct >= 0.70:
        margin = (inputs.ebitda_margin if inputs.ebitda_margin is not None
                  else inputs.ebitda_m / max(0.01, inputs.revenue_m))
        if margin >= 0.18:
            return ImplausibilityFinding(
                name="government_heavy_high_margin_implausible",
                severity="medium",
                claim=(f"{margin*100:.0f}% margin with "
                       f"{(inputs.medicare_pct+inputs.medicaid_pct)*100:.0f}% "
                       "government payer mix."),
                reality=("Government payers price at or below cost on "
                         "many services. 70%+ government mix caps "
                         "mid-teens margins realistically."),
                partner_note=("Walk the margin bridge: is it "
                              "commercial subsidy, non-operating, or "
                              "cost-report aggression?"),
            )
    return None


def _ultra_small_deal_high_irr(
    inputs: FaceInputs,
) -> Optional[ImplausibilityFinding]:
    # Sub-$20M EBITDA deals promising 30%+ IRR are either
    # founder-special or misleading.
    if inputs.ebitda_m > 0 and inputs.ebitda_m <= 20.0 \
            and inputs.claimed_irr >= 0.30:
        return ImplausibilityFinding(
            name="small_deal_extraordinary_irr",
            severity="medium",
            claim=(f"{inputs.claimed_irr*100:.0f}% IRR on "
                   f"${inputs.ebitda_m:.1f}M EBITDA deal."),
            reality=("Sub-$20M EBITDA deals rarely generate 30%+ "
                     "IRR in institutional PE. Verify it isn't "
                     "an IRR on a tiny equity slug."),
            partner_note=("Check the equity base in the IRR math; "
                          "small deals can show inflated IRR on a "
                          "penny of equity but fail to scale."),
        )
    return None


DETECTORS = (
    _rural_cah_high_irr,
    _hospital_margin_out_of_range,
    _practice_margin_out_of_range,
    _leverage_coverage_math,
    _growth_out_of_range,
    _medicare_heavy_with_high_margin,
    _ultra_small_deal_high_irr,
)


@dataclass
class ImplausibilityReport:
    findings: List[ImplausibilityFinding] = field(default_factory=list)
    overall_partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "overall_partner_note": self.overall_partner_note,
        }


def scan_unrealistic(inputs: FaceInputs) -> ImplausibilityReport:
    findings = [f for f in (d(inputs) for d in DETECTORS) if f is not None]
    high = sum(1 for f in findings if f.severity == "high")
    if high >= 2:
        note = (f"{high} high-severity implausibilities — this is a "
                "pass-before-modeling deal.")
    elif high == 1:
        note = ("One high-severity implausibility — address it or "
                "pass before spending diligence hours.")
    elif findings:
        note = (f"{len(findings)} medium-severity implausibilities — "
                "push the seller on specifics.")
    else:
        note = ("No on-its-face implausibilities — deal profile is "
                "internally consistent.")
    return ImplausibilityReport(findings=findings,
                                 overall_partner_note=note)


def render_implausibility_markdown(r: ImplausibilityReport) -> str:
    lines = [
        "# Unrealistic-on-its-face scan",
        "",
        f"_{r.overall_partner_note}_",
        "",
    ]
    for f in r.findings:
        lines.append(f"## {f.name} ({f.severity.upper()})")
        lines.append(f"- **Claim:** {f.claim}")
        lines.append(f"- **Reality:** {f.reality}")
        lines.append(f"- **Partner note:** {f.partner_note}")
        lines.append("")
    return "\n".join(lines)
