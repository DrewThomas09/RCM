"""Physician specialty economic profiler — the shape per specialty.

Partner statement: "Every specialty has a different
economic shape. An orthopedic surgeon generates 4-6×
revenue of a primary care physician at a similar
share of comp. Dermatology runs 75% commercial; ENT
runs 50/50. Cardiology lives off Medicare and the
case mix is procedure-heavy. Knowing the specialty
shape is partner reflex — when the seller's numbers
diverge from the specialty's typical shape, that's
where to dig."

Distinct from:
- `subsector_partner_lens` — 10 subsectors at the
  business level.
- `physician_compensation_benchmark` — wRVU /
  comp-vs-MGMA bench.
- `physician_comp_normalization_check` — adjustment
  validation.

This module is per-specialty **economic shape**:
revenue per physician, contribution margin band,
typical payer mix, and named risks the partner
applies on sight.

### 12 specialties

orthopedic_surgery / gastroenterology / dermatology /
cardiology / medical_oncology / ob_gyn / urology /
ent / ophthalmology / dental / behavioral / radiology

Per-specialty profile carries:

- `typical_revenue_per_physician_m`
- `typical_contribution_margin_pct`
- `typical_commercial_mix_pct`
- `typical_medicare_mix_pct`
- `procedure_concentration_pct` — share of revenue
  from top procedure family
- `payer_density_concern` — top concern from payer
  side
- `regulatory_concern_top` — sniff-test reg concern
- `named_risk_pattern` — partner's reflex on this
  specialty
- `roll_up_attractiveness` — high / medium / low

### Output

Profile + comparison vs. seller-stated metrics with
flags where seller diverges materially.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SPECIALTY_PROFILES: Dict[str, Dict[str, Any]] = {
    "orthopedic_surgery": {
        "typical_revenue_per_physician_m": 2.4,
        "typical_contribution_margin_pct": 0.45,
        "typical_commercial_mix_pct": 0.55,
        "typical_medicare_mix_pct": 0.30,
        "procedure_concentration_pct": 0.55,
        "payer_density_concern": (
            "BCBS / United negotiate hard on TKA / "
            "spine bundles."),
        "regulatory_concern_top": (
            "OBBBA site-neutral on outpatient ortho "
            "procedures — bundle pricing pressure."),
        "named_risk_pattern": (
            "Loss of top surgeon collapses revenue "
            "concentration; physician-extender model "
            "weakens after departure."),
        "roll_up_attractiveness": "high",
    },
    "gastroenterology": {
        "typical_revenue_per_physician_m": 1.8,
        "typical_contribution_margin_pct": 0.42,
        "typical_commercial_mix_pct": 0.50,
        "typical_medicare_mix_pct": 0.40,
        "procedure_concentration_pct": 0.65,
        "payer_density_concern": (
            "Commercial payers pushing colonoscopy "
            "rates down; ASC site-of-service move "
            "ongoing."),
        "regulatory_concern_top": (
            "Site-neutral on colonoscopy + propofol "
            "anesthesia carve-outs."),
        "named_risk_pattern": (
            "ASC ownership model creates ancillary "
            "revenue; loss of OON fees from anesthesia "
            "post-NSA."),
        "roll_up_attractiveness": "high",
    },
    "dermatology": {
        "typical_revenue_per_physician_m": 1.2,
        "typical_contribution_margin_pct": 0.50,
        "typical_commercial_mix_pct": 0.75,
        "typical_medicare_mix_pct": 0.20,
        "procedure_concentration_pct": 0.40,
        "payer_density_concern": (
            "Commercial payers narrowing networks; "
            "Mohs reimbursement under pressure."),
        "regulatory_concern_top": (
            "OIG audits on Mohs and pathology "
            "billing — coding scrutiny."),
        "named_risk_pattern": (
            "DSO model dilutes physician ownership; "
            "high mid-level (PA/NP) ratio drives "
            "regulatory scrutiny."),
        "roll_up_attractiveness": "high",
    },
    "cardiology": {
        "typical_revenue_per_physician_m": 1.6,
        "typical_contribution_margin_pct": 0.40,
        "typical_commercial_mix_pct": 0.40,
        "typical_medicare_mix_pct": 0.50,
        "procedure_concentration_pct": 0.45,
        "payer_density_concern": (
            "MA plans aggressive on cardiac risk; "
            "VBC contracts growing exposure."),
        "regulatory_concern_top": (
            "TAVR and stent rate cuts via OPPS / "
            "site-neutral expansion."),
        "named_risk_pattern": (
            "Heavy Medicare exposure caps multiple; "
            "interventional sub-specialty drives "
            "revenue concentration."),
        "roll_up_attractiveness": "medium",
    },
    "medical_oncology": {
        "typical_revenue_per_physician_m": 3.0,
        "typical_contribution_margin_pct": 0.30,
        "typical_commercial_mix_pct": 0.40,
        "typical_medicare_mix_pct": 0.55,
        "procedure_concentration_pct": 0.30,
        "payer_density_concern": (
            "Drug margin compression — buy-and-bill "
            "spread thinning; OCM / EOM bundled "
            "pressure."),
        "regulatory_concern_top": (
            "340B program changes; ASP+ rate cuts; "
            "biosimilar disruption."),
        "named_risk_pattern": (
            "EBITDA driven by drug margin, not "
            "physician services — drug-pricing reform "
            "is existential."),
        "roll_up_attractiveness": "medium",
    },
    "ob_gyn": {
        "typical_revenue_per_physician_m": 1.0,
        "typical_contribution_margin_pct": 0.35,
        "typical_commercial_mix_pct": 0.65,
        "typical_medicare_mix_pct": 0.05,
        "procedure_concentration_pct": 0.40,
        "payer_density_concern": (
            "Medicaid maternity exposure; commercial "
            "global-fee compression."),
        "regulatory_concern_top": (
            "State Medicaid maternity bundling; mid-"
            "level scope-of-practice expansion."),
        "named_risk_pattern": (
            "Malpractice premium drag is large; "
            "obstetric coverage scarcity in rural "
            "markets."),
        "roll_up_attractiveness": "medium",
    },
    "urology": {
        "typical_revenue_per_physician_m": 1.5,
        "typical_contribution_margin_pct": 0.40,
        "typical_commercial_mix_pct": 0.45,
        "typical_medicare_mix_pct": 0.45,
        "procedure_concentration_pct": 0.50,
        "payer_density_concern": (
            "Commercial payer rate pressure on TURP "
            "and stone procedures."),
        "regulatory_concern_top": (
            "USPSTF PSA recommendation changes "
            "drive volume swings."),
        "named_risk_pattern": (
            "Aging population drives volume; ASC "
            "ancillary revenue is the upside lever."),
        "roll_up_attractiveness": "high",
    },
    "ent": {
        "typical_revenue_per_physician_m": 1.3,
        "typical_contribution_margin_pct": 0.42,
        "typical_commercial_mix_pct": 0.55,
        "typical_medicare_mix_pct": 0.30,
        "procedure_concentration_pct": 0.45,
        "payer_density_concern": (
            "Commercial pediatric ENT margin "
            "compressing; balloon-sinuplasty under "
            "scrutiny."),
        "regulatory_concern_top": (
            "OIG audits on balloon sinuplasty + "
            "in-office procedures."),
        "named_risk_pattern": (
            "Audiology / hearing aid attached "
            "revenue is volatile; age-band "
            "concentration."),
        "roll_up_attractiveness": "medium",
    },
    "ophthalmology": {
        "typical_revenue_per_physician_m": 1.8,
        "typical_contribution_margin_pct": 0.45,
        "typical_commercial_mix_pct": 0.30,
        "typical_medicare_mix_pct": 0.60,
        "procedure_concentration_pct": 0.55,
        "payer_density_concern": (
            "MA plans pushing risk-share on "
            "intravitreal injections."),
        "regulatory_concern_top": (
            "Anti-VEGF biosimilar disruption; ASC "
            "rate cuts on cataracts."),
        "named_risk_pattern": (
            "Retina sub-specialty drives EBITDA via "
            "drug margin; cataract is volume-driven "
            "Medicare workhorse."),
        "roll_up_attractiveness": "high",
    },
    "dental": {
        "typical_revenue_per_physician_m": 0.9,
        "typical_contribution_margin_pct": 0.30,
        "typical_commercial_mix_pct": 0.55,
        "typical_medicare_mix_pct": 0.05,
        "procedure_concentration_pct": 0.35,
        "payer_density_concern": (
            "Dental insurance maximum benefit caps; "
            "self-pay sensitivity to economy."),
        "regulatory_concern_top": (
            "State Medicaid pediatric dental "
            "audits; CPOM scrutiny on DSO models."),
        "named_risk_pattern": (
            "DSO hub-and-spoke needs density; "
            "specialist (ortho/endo/perio) attached "
            "revenue is the multiplier."),
        "roll_up_attractiveness": "high",
    },
    "behavioral": {
        "typical_revenue_per_physician_m": 0.6,
        "typical_contribution_margin_pct": 0.25,
        "typical_commercial_mix_pct": 0.45,
        "typical_medicare_mix_pct": 0.20,
        "procedure_concentration_pct": 0.30,
        "payer_density_concern": (
            "Commercial parity enforcement; carve-out "
            "MBHO contracts complex."),
        "regulatory_concern_top": (
            "Mental health parity audits; state "
            "Medicaid IMD restrictions."),
        "named_risk_pattern": (
            "Clinician supply is binding constraint "
            "(see 2024 staffing collapse); telehealth "
            "regression risk."),
        "roll_up_attractiveness": "low",
    },
    "radiology": {
        "typical_revenue_per_physician_m": 1.6,
        "typical_contribution_margin_pct": 0.35,
        "typical_commercial_mix_pct": 0.45,
        "typical_medicare_mix_pct": 0.40,
        "procedure_concentration_pct": 0.60,
        "payer_density_concern": (
            "Commercial payers contracting via "
            "narrow networks; teleradiology rate "
            "compression."),
        "regulatory_concern_top": (
            "PAMA imaging rate cuts; appropriate-"
            "use-criteria enforcement."),
        "named_risk_pattern": (
            "Hospital-based group risk: hospital can "
            "switch contract mid-cycle; teleradiology "
            "commoditizes."),
        "roll_up_attractiveness": "medium",
    },
}


@dataclass
class SpecialtyProfileInputs:
    specialty: str = "orthopedic_surgery"
    seller_revenue_per_physician_m: Optional[float] = None
    seller_contribution_margin_pct: Optional[float] = None
    seller_commercial_mix_pct: Optional[float] = None


@dataclass
class SpecialtyDivergence:
    metric: str
    seller_value: float
    typical_value: float
    delta: float
    flag: str  # "above_typical", "below_typical", "in_band"


@dataclass
class SpecialtyProfileReport:
    specialty: str = ""
    profile: Dict[str, Any] = field(default_factory=dict)
    divergences: List[SpecialtyDivergence] = field(
        default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "specialty": self.specialty,
            "profile": self.profile,
            "divergences": [
                {"metric": d.metric,
                 "seller_value": d.seller_value,
                 "typical_value": d.typical_value,
                 "delta": d.delta,
                 "flag": d.flag}
                for d in self.divergences
            ],
            "partner_note": self.partner_note,
        }


def _flag_divergence(
    seller_val: float,
    typical: float,
    tolerance_pct: float = 0.20,
) -> str:
    if typical == 0:
        return "in_band"
    delta = (seller_val - typical) / typical
    if delta > tolerance_pct:
        return "above_typical"
    if delta < -tolerance_pct:
        return "below_typical"
    return "in_band"


def profile_specialty(
    inputs: SpecialtyProfileInputs,
) -> SpecialtyProfileReport:
    profile = SPECIALTY_PROFILES.get(inputs.specialty)
    if profile is None:
        return SpecialtyProfileReport(
            specialty=inputs.specialty,
            profile={},
            divergences=[],
            partner_note=(
                f"Specialty '{inputs.specialty}' not in "
                "catalog. Supported: " +
                ", ".join(SPECIALTY_PROFILES.keys())
            ),
        )

    divergences: List[SpecialtyDivergence] = []

    if inputs.seller_revenue_per_physician_m is not None:
        typical = profile["typical_revenue_per_physician_m"]
        flag = _flag_divergence(
            inputs.seller_revenue_per_physician_m,
            typical,
        )
        divergences.append(SpecialtyDivergence(
            metric="revenue_per_physician_m",
            seller_value=inputs.seller_revenue_per_physician_m,
            typical_value=typical,
            delta=round(
                inputs.seller_revenue_per_physician_m -
                typical, 3),
            flag=flag,
        ))

    if inputs.seller_contribution_margin_pct is not None:
        typical = profile["typical_contribution_margin_pct"]
        flag = _flag_divergence(
            inputs.seller_contribution_margin_pct,
            typical,
        )
        divergences.append(SpecialtyDivergence(
            metric="contribution_margin_pct",
            seller_value=inputs.seller_contribution_margin_pct,
            typical_value=typical,
            delta=round(
                inputs.seller_contribution_margin_pct -
                typical, 3),
            flag=flag,
        ))

    if inputs.seller_commercial_mix_pct is not None:
        typical = profile["typical_commercial_mix_pct"]
        flag = _flag_divergence(
            inputs.seller_commercial_mix_pct,
            typical,
        )
        divergences.append(SpecialtyDivergence(
            metric="commercial_mix_pct",
            seller_value=inputs.seller_commercial_mix_pct,
            typical_value=typical,
            delta=round(
                inputs.seller_commercial_mix_pct -
                typical, 3),
            flag=flag,
        ))

    flagged = [
        d for d in divergences if d.flag != "in_band"]
    if flagged:
        ms = ", ".join(d.metric for d in flagged)
        note = (
            f"{inputs.specialty} profile divergences on: "
            f"{ms}. Where the seller's number is "
            "above-typical, ask what's driving it; "
            "where below, ask what's missing. "
            f"Specialty named risk: "
            f"{profile['named_risk_pattern']}"
        )
    else:
        note = (
            f"{inputs.specialty} profile in-band on "
            "all checked metrics. "
            f"Standing risk to remember: "
            f"{profile['named_risk_pattern']}"
        )

    return SpecialtyProfileReport(
        specialty=inputs.specialty,
        profile=dict(profile),
        divergences=divergences,
        partner_note=note,
    )


def render_specialty_profile_markdown(
    r: SpecialtyProfileReport,
) -> str:
    if not r.profile:
        return (
            "# Physician specialty profile\n\n"
            f"_{r.partner_note}_\n"
        )
    p = r.profile
    lines = [
        "# Physician specialty profile",
        "",
        f"## {r.specialty}",
        "",
        f"_{r.partner_note}_",
        "",
        "## Typical economic shape",
        "",
        f"- Revenue per physician: "
        f"${p['typical_revenue_per_physician_m']:.2f}M",
        f"- Contribution margin: "
        f"{p['typical_contribution_margin_pct']:.0%}",
        f"- Commercial mix: "
        f"{p['typical_commercial_mix_pct']:.0%}",
        f"- Medicare mix: "
        f"{p['typical_medicare_mix_pct']:.0%}",
        f"- Top procedure concentration: "
        f"{p['procedure_concentration_pct']:.0%}",
        f"- Roll-up attractiveness: "
        f"{p['roll_up_attractiveness']}",
        "",
        f"**Payer concern:** {p['payer_density_concern']}",
        "",
        f"**Regulatory concern:** "
        f"{p['regulatory_concern_top']}",
        "",
        f"**Named risk pattern:** "
        f"{p['named_risk_pattern']}",
        "",
    ]
    if r.divergences:
        lines.append("## Divergences vs. typical")
        lines.append("")
        lines.append(
            "| Metric | Seller | Typical | Δ | Flag |")
        lines.append("|---|---|---|---|---|")
        for d in r.divergences:
            lines.append(
                f"| {d.metric} | {d.seller_value} | "
                f"{d.typical_value} | "
                f"{d.delta:+.3f} | {d.flag} |"
            )
    return "\n".join(lines)
