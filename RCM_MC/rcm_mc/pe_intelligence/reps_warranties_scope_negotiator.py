"""Reps & warranties scope — which reps to insist on.

Partner statement: "The cap and deductible get the
attention, but the scope decides what's covered in the
first place. I'd rather have a tight rep on the five
things that matter than a loose rep on everything."

Distinct from:
- `loi_term_sheet_review` — reviews the LOI terms
  (cap, deductible, carveouts).
- `qofe_prescreen` — EBITDA add-back survival.

This module designs **which reps the partner demands**
on a healthcare-services PE deal. Healthcare-specific
reps (HIPAA, Stark, AKS, licensure, OIG, CIA) sit
alongside the standard corporate reps.

### 14 reps modeled

- **Fundamental** (always survives, uncapped / longer
  survival period): organization, authority,
  capitalization, tax-basic.
- **Standard** (12-18 month survival, R&W insurance
  available): financials, litigation, employee, IP,
  contracts.
- **Healthcare-specific** (always demanded in healthcare-
  PE, often seller-resistant): HIPAA, Stark/AKS,
  licensure, OIG exclusion, CIA compliance, clinical-
  quality.

### Output

Per-rep scope recommendation: must-have / standard /
negotiable; who-pays (seller indemnity / R&W
insurance / carve-out); partner commentary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RepRecommendation:
    rep: str
    category: str                          # fundamental / standard /
                                            # healthcare_specific
    priority: str                          # must_have / standard /
                                            # negotiable
    scope_guidance: str
    who_pays: str                          # seller_indemnity / rw_insurance /
                                            # carve_out
    partner_commentary: str


@dataclass
class RepPackageInputs:
    subsector: str = "healthcare_services"
    rw_insurance_in_place: bool = True
    asset_type_is_provider: bool = True
    material_regulatory_audit_history: bool = False
    key_employee_litigation_pending: bool = False
    prior_cyber_incident_disclosed: bool = False


@dataclass
class RepPackageReport:
    recommendations: List[RepRecommendation] = field(default_factory=list)
    must_have_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendations": [
                {"rep": r.rep,
                 "category": r.category,
                 "priority": r.priority,
                 "scope_guidance": r.scope_guidance,
                 "who_pays": r.who_pays,
                 "partner_commentary": r.partner_commentary}
                for r in self.recommendations
            ],
            "must_have_count": self.must_have_count,
            "partner_note": self.partner_note,
        }


def design_reps_warranties_scope(
    inputs: RepPackageInputs,
) -> RepPackageReport:
    recs: List[RepRecommendation] = []

    # Fundamental reps — always must-have, seller indemnity.
    fundamentals = [
        ("organization_and_good_standing",
         "Target is validly organized and in good "
         "standing in each jurisdiction."),
        ("authority_to_execute",
         "Seller has authority to sell; all required "
         "consents in place."),
        ("capitalization",
         "Cap table as represented; no secret equity or "
         "derivative instruments."),
        ("tax_basic",
         "All required returns filed; taxes paid; no "
         "material open audits."),
    ]
    for name, scope in fundamentals:
        recs.append(RepRecommendation(
            rep=name,
            category="fundamental",
            priority="must_have",
            scope_guidance=scope,
            who_pays="seller_indemnity",
            partner_commentary=(
                "Fundamental rep — uncapped seller "
                "indemnity; longer survival."
            ),
        ))

    # Standard reps — R&W insurance covers.
    standards = [
        ("financial_statements",
         "GAAP or agreed-upon-procedures basis; no "
         "material undisclosed liabilities."),
        ("no_conflicts",
         "Transaction doesn't breach material contracts "
         "or trigger acceleration."),
        ("litigation_disclosure",
         "All material pending / threatened litigation "
         "disclosed."),
        ("employee_classification_and_wage_hour",
         "Workers properly classified; no wage-hour "
         "class action."),
        ("ip_ownership",
         "All material IP owned or licensed; no third-"
         "party infringement claims."),
        ("it_systems_and_cybersecurity",
         "Core systems operational; no material breaches "
         "in past 24 months; adequate controls."),
    ]
    for name, scope in standards:
        who_pays = (
            "rw_insurance"
            if inputs.rw_insurance_in_place
            else "seller_indemnity"
        )
        partner_note = (
            "Standard rep; R&W insurance covers above "
            "basket up to policy cap."
            if inputs.rw_insurance_in_place else
            "Standard rep; seller indemnity up to cap. "
            "No R&W insurance."
        )
        # Elevate to must-have if packet flags warn.
        priority = "standard"
        if (name == "employee_classification_and_wage_hour"
                and inputs.key_employee_litigation_pending):
            priority = "must_have"
            partner_note += (
                " Elevated given pending employment "
                "litigation."
            )
        if (name == "it_systems_and_cybersecurity"
                and inputs.prior_cyber_incident_disclosed):
            priority = "must_have"
            who_pays = "carve_out"
            partner_note = (
                "Prior cyber incident — carve out from "
                "R&W insurance; negotiate specific "
                "indemnity with survival."
            )
        recs.append(RepRecommendation(
            rep=name,
            category="standard",
            priority=priority,
            scope_guidance=scope,
            who_pays=who_pays,
            partner_commentary=partner_note,
        ))

    # Healthcare-specific reps — always demanded in
    # healthcare PE.
    if inputs.asset_type_is_provider:
        healthcare_reps = [
            ("hipaa_compliance",
             "HIPAA policies in place; no reportable "
             "breaches in past 24 months; BAAs with "
             "vendors."),
            ("stark_aks_compliance",
             "All referral relationships comply with "
             "Stark / AKS safe harbors; no off-the-"
             "books payments."),
            ("healthcare_licensure",
             "All required facility / clinician licenses "
             "current; no material provider number "
             "issues."),
            ("oig_exclusion_clean",
             "No owner / key employee / physician on OIG "
             "exclusion list."),
            ("cia_compliance",
             "If under CIA, all reporting obligations "
             "met; no material breaches."),
            ("clinical_quality_and_cms_survey",
             "No unresolved CMS survey deficiencies; "
             "current star ratings as represented."),
        ]
        for name, scope in healthcare_reps:
            priority = "must_have"
            who_pays = "seller_indemnity"
            partner_note = (
                "Healthcare-specific rep; survives longer. "
                "R&W insurance often excludes — carve-"
                "out into specific indemnity."
            )
            if (name in ("stark_aks_compliance",
                          "oig_exclusion_clean",
                          "cia_compliance")
                    and inputs.material_regulatory_audit_history):
                partner_note = (
                    "Material regulatory audit history; "
                    "enhance survival + indemnity cap "
                    "for this rep specifically."
                )
            recs.append(RepRecommendation(
                rep=name,
                category="healthcare_specific",
                priority=priority,
                scope_guidance=scope,
                who_pays=who_pays,
                partner_commentary=partner_note,
            ))

    must_have = sum(1 for r in recs
                     if r.priority == "must_have")

    if not inputs.rw_insurance_in_place:
        note = (
            f"{must_have} must-have reps with no R&W "
            "insurance — seller indemnity cap becomes "
            "the deal-defining number. Partner: size "
            "cap to top-3 exposure scenarios."
        )
    elif inputs.material_regulatory_audit_history:
        note = (
            f"{must_have} must-have reps; material "
            "regulatory history → enhance healthcare-rep "
            "survival + specific indemnity. R&W "
            "insurance covers standard scope."
        )
    else:
        note = (
            f"{must_have} must-have reps with R&W "
            "insurance covering standard scope. "
            "Healthcare reps carved into specific "
            "indemnity."
        )

    return RepPackageReport(
        recommendations=recs,
        must_have_count=must_have,
        partner_note=note,
    )


def render_reps_markdown(r: RepPackageReport) -> str:
    lines = [
        "# Reps & warranties scope recommendation",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Must-have reps: {r.must_have_count}",
        f"- Total reps: {len(r.recommendations)}",
        "",
        "| Rep | Category | Priority | Who pays | "
        "Partner commentary |",
        "|---|---|---|---|---|",
    ]
    for rec in r.recommendations:
        lines.append(
            f"| {rec.rep} | {rec.category} | "
            f"{rec.priority} | {rec.who_pays} | "
            f"{rec.partner_commentary} |"
        )
    return "\n".join(lines)
