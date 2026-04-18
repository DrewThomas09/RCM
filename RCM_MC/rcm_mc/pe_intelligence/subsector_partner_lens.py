"""Subsector partner lens — how partners read each subsector.

Partner statement: "I don't evaluate a home-health deal
like a hospital deal. Different questions on intake,
different ceiling risks, different multiples that hold at
exit."

Generic heuristics are sector-agnostic. Real partners
apply a **subsector lens** that overrides or augments the
generic rules. This module encodes that lens for the 10
healthcare-services subsectors a partner sees on a daily
basis.

### Subsectors covered

1. **hospital_general** — acute care, reimbursement-driven.
2. **specialty_physician_practice** — dermatology, GI,
   ophthalmology, orthopedics.
3. **behavioral_health** — inpatient + outpatient mental
   health, SUD.
4. **home_health** — Medicare-heavy, PDGM-era.
5. **hospice** — Medicare hospice benefit, cap-driven.
6. **ambulatory_surgery_center** — ASC, physician-owned
   typically.
7. **clinical_lab** — reference labs, specialty testing.
8. **dental_office** — general and specialty dentistry.
9. **urgent_care** — walk-in clinics, mostly cash /
   commercial.
10. **durable_medical_equipment** — DME supply, heavily
    Medicare.

### Per-subsector partner data points

- `first_question_on_intake` — the one question a partner
  asks first.
- `structural_ceiling_risk` — what caps the upside.
- `primary_tailwind` / `primary_headwind` — the current
  macro read.
- `reimbursement_reality` — FFS / risk / cap / cash-pay.
- `deal_killer_flag` — signals that trigger a walk.
- `key_exit_multiple_driver` — what justifies a premium
  at exit.
- `typical_ebitda_margin_band` — ballpark peer band.
- `typical_reimbursement_mix_note` — short partner note
  on payer mix posture.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SubsectorLens:
    subsector: str
    first_question_on_intake: str
    structural_ceiling_risk: str
    primary_tailwind: str
    primary_headwind: str
    reimbursement_reality: str
    deal_killer_flags: List[str] = field(default_factory=list)
    key_exit_multiple_driver: str = ""
    typical_ebitda_margin_band: str = ""
    typical_reimbursement_mix_note: str = ""
    partner_voice_summary: str = ""


LENS_LIBRARY: Dict[str, SubsectorLens] = {
    "hospital_general": SubsectorLens(
        subsector="hospital_general",
        first_question_on_intake=(
            "What's your payer mix, and what's your "
            "Medicare reimbursement trend?"
        ),
        structural_ceiling_risk=(
            "Reimbursement compression — DRG / APC cuts "
            "plus payer rate squeeze."
        ),
        primary_tailwind=(
            "Tertiary consolidation premium; academic "
            "integration multiples."
        ),
        primary_headwind=(
            "Labor (RN + travel), site-neutral on HOPD, "
            "state Medicaid rate pressure."
        ),
        reimbursement_reality="FFS with payer mix dependency.",
        deal_killer_flags=[
            "EBITDA margin > 16% — not credible for a hospital",
            "Rural CAH with IRR target > 18%",
            "Sub-100-bed with > 5.5x leverage",
        ],
        key_exit_multiple_driver=(
            "Market-position scarcity + case-mix + "
            "academic affiliation."
        ),
        typical_ebitda_margin_band="6% – 12%",
        typical_reimbursement_mix_note=(
            "Medicare 40%+, Medicaid 15%+, Commercial "
            "30%, Self-pay + Other 15%. Higher Medicare "
            "share = lower exit multiple."
        ),
        partner_voice_summary=(
            "Hospitals are rate-takers on 60% of revenue. "
            "Ops lift matters but reimbursement direction "
            "matters more."
        ),
    ),
    "specialty_physician_practice": SubsectorLens(
        subsector="specialty_physician_practice",
        first_question_on_intake=(
            "Who's the founder, and how much of revenue "
            "comes from their personal referral network?"
        ),
        structural_ceiling_risk=(
            "Founder flight + physician compensation "
            "re-benchmarking post-close."
        ),
        primary_tailwind=(
            "PE rollup premium at sub-scale. Commercial "
            "payer leverage at platform scale."
        ),
        primary_headwind=(
            "Surprise-billing laws, OON regulation, "
            "physician-comp normalization."
        ),
        reimbursement_reality=(
            "FFS primarily; premium cash-pay in select "
            "specialties (derm, ortho)."
        ),
        deal_killer_flags=[
            "Founder > 30% of RVU with no successor",
            "Surprise-billing lawsuit active",
            "Physician non-competes < 2 years in practice contracts",
        ],
        key_exit_multiple_driver=(
            "Platform scale + integrated tech + "
            "standardized comp structure."
        ),
        typical_ebitda_margin_band="15% – 25%",
        typical_reimbursement_mix_note=(
            "Mix varies by specialty. Derm / plastics "
            "trend cash-pay; GI / cardiology trend FFS + "
            "ancillary."
        ),
        partner_voice_summary=(
            "Specialty practice rollups are operator-team "
            "deals. If the team isn't institutional, the "
            "platform won't integrate."
        ),
    ),
    "behavioral_health": SubsectorLens(
        subsector="behavioral_health",
        first_question_on_intake=(
            "What's your licensed capacity utilization, "
            "and what's the staffing / license ratio?"
        ),
        structural_ceiling_risk=(
            "Staffing constraint on capacity expansion. "
            "Licensed-therapist supply is the binding "
            "constraint, not beds or referrals."
        ),
        primary_tailwind=(
            "Mental-health parity enforcement + "
            "pandemic-driven demand + insurance network "
            "expansion."
        ),
        primary_headwind=(
            "Clinician burnout + compensation inflation "
            "+ credentialing delays (6 months per plan)."
        ),
        reimbursement_reality=(
            "Commercial 40-60% / Medicaid 20-40% / "
            "private-pay balance. Some risk contracts "
            "emerging."
        ),
        deal_killer_flags=[
            "Clinician turnover > 30%/year",
            "Payer-panel credentialing > 12 mo to open",
            "Single-state concentration with state cut risk",
        ],
        key_exit_multiple_driver=(
            "Platform network + insurance panel breadth "
            "+ proprietary clinical protocols."
        ),
        typical_ebitda_margin_band="12% – 20%",
        typical_reimbursement_mix_note=(
            "Commercial-heavy for outpatient; Medicaid-"
            "heavy for inpatient / SUD. Parity-law "
            "enforcement expanding commercial coverage."
        ),
        partner_voice_summary=(
            "Behavioral health is a capacity / staffing "
            "problem, not a demand problem. Underwrite "
            "the staffing ramp, not the demand curve."
        ),
    ),
    "home_health": SubsectorLens(
        subsector="home_health",
        first_question_on_intake=(
            "What's your PDGM case-mix, and what's your "
            "LUPA rate trend?"
        ),
        structural_ceiling_risk=(
            "PDGM reimbursement structure + CMS-capped "
            "rate updates + clinician supply."
        ),
        primary_tailwind=(
            "Aging demographics + hospital-at-home + MA "
            "HCBS expansion."
        ),
        primary_headwind=(
            "Low-utilization payment adjustments (LUPA), "
            "behavioral adjustments, documentation "
            "requirements."
        ),
        reimbursement_reality=(
            "Medicare FFS 60%+ with PDGM risk; "
            "increasing MA share with episodic "
            "uncertainty."
        ),
        deal_killer_flags=[
            "Medicare FFS > 80% without MA readiness",
            "LUPA > 12% of episodes",
            "High case-mix concentration in LOW HHRG",
        ],
        key_exit_multiple_driver=(
            "Geographic density + MA contract breadth + "
            "clinical outcomes."
        ),
        typical_ebitda_margin_band="10% – 16%",
        typical_reimbursement_mix_note=(
            "Medicare 60-80% typical; MA 15-30% and "
            "rising; Medicaid balance."
        ),
        partner_voice_summary=(
            "Home-health exit multiples only hold when "
            "MA capability is real. Price off MA-ready "
            "EBITDA, not reported EBITDA."
        ),
    ),
    "hospice": SubsectorLens(
        subsector="hospice",
        first_question_on_intake=(
            "What's your length of stay, and have you "
            "ever hit the Medicare cap?"
        ),
        structural_ceiling_risk=(
            "Medicare hospice aggregate cap + OIG audit "
            "exposure on long-LOS patients."
        ),
        primary_tailwind=(
            "Aging demographics + hospital-at-home + "
            "continued care preference."
        ),
        primary_headwind=(
            "OIG cap audits, PEPPER outliers, MA-hospice "
            "carve-in uncertainty."
        ),
        reimbursement_reality=(
            "Medicare FFS 90%+ with aggregate cap. MA "
            "carve-in pilot emerging."
        ),
        deal_killer_flags=[
            "Long-LOS patient share > 35%",
            "Any settled OIG audit in past 5 years > $5M",
            "Cap hit in any of last 3 years",
        ],
        key_exit_multiple_driver=(
            "Referral source diversification + MA "
            "carve-in contracts + clean audit history."
        ),
        typical_ebitda_margin_band="15% – 22%",
        typical_reimbursement_mix_note=(
            "Medicare 90%+. Cap discipline is the "
            "binding constraint, not payer mix."
        ),
        partner_voice_summary=(
            "Hospice deals live or die on cap discipline "
            "and audit history. Every other metric is "
            "secondary."
        ),
    ),
    "ambulatory_surgery_center": SubsectorLens(
        subsector="ambulatory_surgery_center",
        first_question_on_intake=(
            "What's your case mix, and how many of your "
            "physicians have ownership?"
        ),
        structural_ceiling_risk=(
            "Site-neutral payment + physician-ownership "
            "restrictions + HOPD migration."
        ),
        primary_tailwind=(
            "Site-of-service migration from HOPD + "
            "commercial steering."
        ),
        primary_headwind=(
            "Safe-harbor rules on physician ownership; "
            "payer contracting dependence on MPFS."
        ),
        reimbursement_reality=(
            "Commercial 50%+ / Medicare 25-35% / "
            "Self-pay balance. ASC rates run 40-60% of "
            "HOPD."
        ),
        deal_killer_flags=[
            "< 30% physician ownership (at-risk for shift)",
            "Single specialty + single dominant surgeon",
            "> 40% Medicare mix (site-neutral risk)",
        ],
        key_exit_multiple_driver=(
            "Physician stability + commercial contract "
            "book + case-mix defensibility."
        ),
        typical_ebitda_margin_band="25% – 40%",
        typical_reimbursement_mix_note=(
            "Commercial-heavy. ASC rate arbitrage vs. "
            "HOPD is the core thesis; that arbitrage "
            "narrows with site-neutral."
        ),
        partner_voice_summary=(
            "ASC multiples are about physician retention. "
            "Without the surgeons, there's no case flow."
        ),
    ),
    "clinical_lab": SubsectorLens(
        subsector="clinical_lab",
        first_question_on_intake=(
            "What's your reimbursement per test trend, "
            "and what's your customer concentration?"
        ),
        structural_ceiling_risk=(
            "PAMA cuts + customer concentration + "
            "LCD/NCD reimbursement limits on novel "
            "tests."
        ),
        primary_tailwind=(
            "Precision medicine + genomics + home "
            "testing growth."
        ),
        primary_headwind=(
            "PAMA Medicare-rate cuts (7% + 15% + 15% "
            "phased); commercial follows with lag."
        ),
        reimbursement_reality=(
            "Mix of FFS (routine) + capitated lab "
            "contracts + self-pay (novel tests)."
        ),
        deal_killer_flags=[
            "Top-3 customer > 40% revenue",
            "Novel test with no established CPT",
            "Non-PAMA-compliant reporting",
        ],
        key_exit_multiple_driver=(
            "Test menu depth + contract book + proprietary "
            "genomic content."
        ),
        typical_ebitda_margin_band="18% – 30%",
        typical_reimbursement_mix_note=(
            "Medicare 20-30% / Commercial 50%+ / "
            "Self-pay 5-15%. PAMA cuts compound over 3 "
            "years."
        ),
        partner_voice_summary=(
            "Labs are PAMA-exposed. Price base case off "
            "post-PAMA rate deck, not current."
        ),
    ),
    "dental_office": SubsectorLens(
        subsector="dental_office",
        first_question_on_intake=(
            "What's your dentist-owned vs DSO-employed "
            "ratio, and what's your new-patient flow?"
        ),
        structural_ceiling_risk=(
            "Dentist retention post-close + commercial "
            "dental-insurance fee schedules."
        ),
        primary_tailwind=(
            "DSO rollup multiples + cosmetic / implants "
            "demand + commercial + cash-pay."
        ),
        primary_headwind=(
            "State dental-practice regulations; dentist "
            "burnout + retention; private-credit "
            "saturation."
        ),
        reimbursement_reality=(
            "Mixed commercial dental + cash-pay. "
            "Medicaid dental < 10% typical in adult DSOs."
        ),
        deal_killer_flags=[
            "Owner-dentist age 60+ without succession",
            "Dental-chain cash collections / production < 92%",
            "Heavy reliance on single insurance plan",
        ],
        key_exit_multiple_driver=(
            "Scale + dentist retention + specialty "
            "ancillary (ortho, oral surgery, implants)."
        ),
        typical_ebitda_margin_band="15% – 22%",
        typical_reimbursement_mix_note=(
            "Commercial insurance 50-70%, cash-pay "
            "20-30%, Medicaid 5-15% in adult DSOs."
        ),
        partner_voice_summary=(
            "Dental DSO math only works if dentist "
            "retention is real. Employment agreements + "
            "equity rollover are non-negotiable."
        ),
    ),
    "urgent_care": SubsectorLens(
        subsector="urgent_care",
        first_question_on_intake=(
            "What's your visit volume per clinic-day, "
            "and how much is commercial vs cash-pay?"
        ),
        structural_ceiling_risk=(
            "Volume dependency + telehealth "
            "substitution + retail-clinic "
            "competition."
        ),
        primary_tailwind=(
            "Out-of-hours demand + employer-sponsored "
            "occupational-health contracts."
        ),
        primary_headwind=(
            "Retail-pharmacy clinics + telehealth + "
            "urgent-care saturation in major MSAs."
        ),
        reimbursement_reality=(
            "Commercial 60%+ / Cash-pay 15-20% / "
            "Medicare < 10% / Medicaid balance."
        ),
        deal_killer_flags=[
            "Visit volume declining > 8% / yr",
            "Competing retail-pharmacy clinic within 1 mi",
            "No occupational-health book",
        ],
        key_exit_multiple_driver=(
            "Density + occ-health contracts + "
            "tele-bridge capability."
        ),
        typical_ebitda_margin_band="12% – 18%",
        typical_reimbursement_mix_note=(
            "Commercial-heavy; Medicare < 10%. Cash-pay "
            "sustains when commercial is denied."
        ),
        partner_voice_summary=(
            "Urgent care is a real-estate + volume play. "
            "Price off visits-per-square-foot, not EBITDA."
        ),
    ),
    "durable_medical_equipment": SubsectorLens(
        subsector="durable_medical_equipment",
        first_question_on_intake=(
            "What's your Medicare competitive-bid "
            "exposure, and what's your product-line "
            "concentration?"
        ),
        structural_ceiling_risk=(
            "Medicare competitive-bidding pricing + "
            "OIG audit exposure + payer prior-auth."
        ),
        primary_tailwind=(
            "Aging + home-care shift + remote-patient-"
            "monitoring expansion."
        ),
        primary_headwind=(
            "Competitive-bid rounds cutting Medicare "
            "rates 40-60% in affected product lines."
        ),
        reimbursement_reality=(
            "Medicare 50-70% / Medicaid 10-20% / "
            "Commercial balance. Capped rental "
            "arithmetic on DME."
        ),
        deal_killer_flags=[
            "Top product > 40% revenue (single-SKU risk)",
            "No CMS competitive-bid history",
            "OIG subpoena in past 3 years",
        ],
        key_exit_multiple_driver=(
            "Product-line diversification + payer mix "
            "breadth + operational ops cadence."
        ),
        typical_ebitda_margin_band="10% – 16%",
        typical_reimbursement_mix_note=(
            "Medicare-heavy with CMS bid risk. CPAP, "
            "oxygen, mobility are most bid-exposed."
        ),
        partner_voice_summary=(
            "DME is a Medicare compliance business. "
            "Audit clean + bid diversification = multiple. "
            "Anything else = discount."
        ),
    ),
}


@dataclass
class LensApplication:
    subsector: str
    lens: SubsectorLens
    deal_killer_flags_hit: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsector": self.subsector,
            "lens": {
                "first_question_on_intake":
                    self.lens.first_question_on_intake,
                "structural_ceiling_risk":
                    self.lens.structural_ceiling_risk,
                "primary_tailwind": self.lens.primary_tailwind,
                "primary_headwind": self.lens.primary_headwind,
                "reimbursement_reality":
                    self.lens.reimbursement_reality,
                "key_exit_multiple_driver":
                    self.lens.key_exit_multiple_driver,
                "typical_ebitda_margin_band":
                    self.lens.typical_ebitda_margin_band,
                "typical_reimbursement_mix_note":
                    self.lens.typical_reimbursement_mix_note,
                "partner_voice_summary":
                    self.lens.partner_voice_summary,
            },
            "deal_killer_flags_hit":
                list(self.deal_killer_flags_hit),
            "partner_note": self.partner_note,
        }


def apply_subsector_lens(
    subsector: str,
    signals: Optional[Dict[str, Any]] = None,
) -> LensApplication:
    """Return the lens for a subsector and, if signals are
    provided, check them against the subsector's deal-killer
    flag list."""
    lens = LENS_LIBRARY.get(subsector)
    if lens is None:
        # Fallback minimal lens.
        return LensApplication(
            subsector=subsector,
            lens=SubsectorLens(
                subsector=subsector,
                first_question_on_intake=(
                    "Subsector not modeled. Treat as generic "
                    "healthcare services."
                ),
                structural_ceiling_risk="unknown",
                primary_tailwind="unknown",
                primary_headwind="unknown",
                reimbursement_reality="unknown",
                partner_voice_summary=(
                    f"No subsector lens for '{subsector}'. "
                    "Apply generic heuristics."
                ),
            ),
            partner_note=(
                f"Subsector '{subsector}' not modeled — apply "
                "generic heuristics only."
            ),
        )

    hits: List[str] = []
    if signals:
        for flag in lens.deal_killer_flags:
            # Match loosely: the signal key can be a substring of
            # the flag (bool-valued) OR the flag itself as key.
            if signals.get(flag) or any(
                str(sig).lower() in flag.lower() and val
                for sig, val in signals.items()
                if val
            ):
                hits.append(flag)

    if hits:
        note = (f"{len(hits)} deal-killer flag(s) triggered on "
                f"{subsector}: {hits[0]}. Partner: {lens.partner_voice_summary}")
    else:
        note = (f"Subsector lens applied: {lens.partner_voice_summary}")

    return LensApplication(
        subsector=subsector,
        lens=lens,
        deal_killer_flags_hit=hits,
        partner_note=note,
    )


def list_modeled_subsectors() -> List[str]:
    return sorted(LENS_LIBRARY.keys())


def render_subsector_lens_markdown(
    app: LensApplication,
) -> str:
    lens = app.lens
    lines = [
        f"# Subsector lens — {app.subsector}",
        "",
        f"_{app.partner_note}_",
        "",
        f"**First question on intake:** {lens.first_question_on_intake}",
        "",
        f"- **Ceiling risk:** {lens.structural_ceiling_risk}",
        f"- **Tailwind:** {lens.primary_tailwind}",
        f"- **Headwind:** {lens.primary_headwind}",
        f"- **Reimbursement reality:** {lens.reimbursement_reality}",
        f"- **Typical EBITDA margin:** "
        f"{lens.typical_ebitda_margin_band}",
        f"- **Typical mix note:** "
        f"{lens.typical_reimbursement_mix_note}",
        f"- **Exit multiple driver:** "
        f"{lens.key_exit_multiple_driver}",
        "",
        f"**Partner summary:** {lens.partner_voice_summary}",
        "",
    ]
    if app.deal_killer_flags_hit:
        lines.append("## Deal-killer flags triggered")
        lines.append("")
        for f in app.deal_killer_flags_hit:
            lines.append(f"- {f}")
    else:
        lines.append("## Deal-killer flags: none triggered")
    return "\n".join(lines)
