"""Closing conditions list — sign-to-close risk, partner lens.

Partner statement: "Signing is a commitment. Close is a
ceremony. The conditions list is where we earn our break
rights — or lose them."

Associates write closing-conditions lists mechanically.
Partners read them for three questions:

1. Which conditions are *truly* in our control vs. a third
   party (regulator, lender, landlord, payer)?
2. Which conditions can the seller *fail* without consequence
   (soft bring-downs) vs. which give us a real walk right?
3. Which conditions are time-bombs — things that could go
   wrong specifically *because* of the sign-to-close delay?

This module enumerates the 12-15 conditions that actually
matter on a healthcare-services deal and classifies each by:

- **satisfied_at**: signing / close / both
- **who_controls**: buyer / seller / third_party
- **blocking_risk**: high / medium / low
- **walk_right**: True if our failure-to-satisfy gives us a
  clean walk

Healthcare-specific conditions (CON, state licensure,
Medicare provider number, 340B contracts) are flagged — they
behave differently from generic M&A closing conditions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ClosingCondition:
    name: str
    category: str
    satisfied_at: str        # "signing" / "close" / "both"
    who_controls: str        # "buyer" / "seller" / "third_party"
    blocking_risk: str       # "high" / "medium" / "low"
    walk_right: bool
    partner_note: str


@dataclass
class ClosingConditionsInputs:
    sector: str = "healthcare_services"
    deal_size_m: float = 500.0
    hsr_filing_required: bool = True
    state_regulatory_required: bool = True   # CON, licensure transfer
    payer_consents_material: bool = True     # Medicare / Medicaid / top commercial
    landlord_consents_required: bool = True
    financing_external: bool = True          # debt financing needed
    rw_insurance_proposed: bool = True
    key_employee_retention_required: bool = True
    it_cyber_attestation_required: bool = True
    material_contracts_count: int = 20
    seller_breach_brings_walk: bool = True


@dataclass
class ClosingConditionsReport:
    conditions: List[ClosingCondition] = field(default_factory=list)
    high_risk_count: int = 0
    third_party_dependent_count: int = 0
    walk_right_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conditions": [
                {"name": c.name, "category": c.category,
                 "satisfied_at": c.satisfied_at,
                 "who_controls": c.who_controls,
                 "blocking_risk": c.blocking_risk,
                 "walk_right": c.walk_right,
                 "partner_note": c.partner_note}
                for c in self.conditions
            ],
            "high_risk_count": self.high_risk_count,
            "third_party_dependent_count": self.third_party_dependent_count,
            "walk_right_count": self.walk_right_count,
            "partner_note": self.partner_note,
        }


def build_closing_conditions(
    inputs: ClosingConditionsInputs,
) -> ClosingConditionsReport:
    conds: List[ClosingCondition] = []

    # HSR / antitrust.
    if inputs.hsr_filing_required:
        conds.append(ClosingCondition(
            name="hsr_antitrust_clearance",
            category="regulatory",
            satisfied_at="close",
            who_controls="third_party",
            blocking_risk="high" if inputs.deal_size_m > 400 else "medium",
            walk_right=True,
            partner_note=("FTC second request is the live failure "
                          "mode; > $400M deals get hit more often. "
                          "Model 90-day vs 180-day outside-date cases."),
        ))

    # State regulatory (healthcare).
    if inputs.state_regulatory_required and inputs.sector == "healthcare_services":
        conds.append(ClosingCondition(
            name="state_healthcare_regulatory",
            category="regulatory_healthcare",
            satisfied_at="close",
            who_controls="third_party",
            blocking_risk="high",
            walk_right=True,
            partner_note=("CON transfers + state licensure "
                          "transfers run on agency timelines; one "
                          "hostile state can delay 9 months."),
        ))

    # Medicare provider number transfer.
    if inputs.sector == "healthcare_services":
        conds.append(ClosingCondition(
            name="medicare_provider_number_transfer",
            category="regulatory_healthcare",
            satisfied_at="close",
            who_controls="third_party",
            blocking_risk="medium",
            walk_right=False,
            partner_note=("CHOW filings with MAC can be worked "
                          "around with tie-in agreement; not a "
                          "walk-right but a cash-flow bridge item."),
        ))

    # Payer consents.
    if inputs.payer_consents_material:
        conds.append(ClosingCondition(
            name="payer_contract_consents",
            category="commercial",
            satisfied_at="close",
            who_controls="third_party",
            blocking_risk="medium",
            walk_right=False,
            partner_note=("Top 5 payers: chase consents 60 days "
                          "ahead. Silent-consent provisions in "
                          "contracts save deals."),
        ))

    # Landlord / real estate consents.
    if inputs.landlord_consents_required:
        conds.append(ClosingCondition(
            name="landlord_consents",
            category="real_estate",
            satisfied_at="close",
            who_controls="third_party",
            blocking_risk="low",
            walk_right=False,
            partner_note=("Routine; seller counsel owns. "
                          "Exceptions: anchor leases with "
                          "change-of-control triggers."),
        ))

    # Financing funded.
    if inputs.financing_external:
        conds.append(ClosingCondition(
            name="debt_financing_funded",
            category="financing",
            satisfied_at="close",
            who_controls="third_party",
            blocking_risk="high",
            walk_right=False,   # we typically sign with commitment
            partner_note=("Commitment letter must be clean — no "
                          "financial-out language. If seller "
                          "accepted financing-contingent deal, "
                          "that's our bridge."),
        ))

    # R&W insurance binding.
    if inputs.rw_insurance_proposed:
        conds.append(ClosingCondition(
            name="rw_insurance_bound",
            category="risk_management",
            satisfied_at="signing",
            who_controls="buyer",
            blocking_risk="low",
            walk_right=False,
            partner_note=("Bind at signing. Carriers pull quotes "
                          "at close if anything surfaces in "
                          "interim — our team owns timing."),
        ))

    # Key employee retention / non-competes.
    if inputs.key_employee_retention_required:
        conds.append(ClosingCondition(
            name="key_employee_retention_signed",
            category="people",
            satisfied_at="both",
            who_controls="seller",
            blocking_risk="medium",
            walk_right=True,
            partner_note=("Key-15 employment agreements + non-"
                          "competes at signing; any that drop "
                          "pre-close is a renegotiation trigger."),
        ))

    # No MAC.
    conds.append(ClosingCondition(
        name="no_material_adverse_change",
        category="financial",
        satisfied_at="close",
        who_controls="seller",
        blocking_risk="medium",
        walk_right=True,
        partner_note=("MAC clause is a walk right only if MAC "
                      "definition is narrow. See LOI review — "
                      "broad MAC = no walk right in practice."),
    ))

    # Bring-down of reps.
    conds.append(ClosingCondition(
        name="reps_true_at_closing",
        category="legal",
        satisfied_at="close",
        who_controls="seller",
        blocking_risk="medium",
        walk_right=inputs.seller_breach_brings_walk,
        partner_note=("Bring-down certificate. Partner asks: "
                      "'material accuracy' or 'material "
                      "adverse effect' standard? MAE standard "
                      "gives seller running room."),
    ))

    # Title / no encumbrances.
    conds.append(ClosingCondition(
        name="clean_title_no_liens",
        category="legal",
        satisfied_at="close",
        who_controls="seller",
        blocking_risk="low",
        walk_right=True,
        partner_note=("Title insurance + lien search. Routine "
                      "unless there's a UCC-1 or tax lien we "
                      "missed in diligence."),
    ))

    # IT / cyber attestation.
    if inputs.it_cyber_attestation_required:
        conds.append(ClosingCondition(
            name="it_cyber_attestation",
            category="operational",
            satisfied_at="close",
            who_controls="seller",
            blocking_risk="medium",
            walk_right=False,
            partner_note=("Partner asks for attestation: no "
                          "material breach disclosed to "
                          "regulators; no open ransomware. "
                          "PHI-heavy targets raise the bar."),
        ))

    # Material contracts listed.
    conds.append(ClosingCondition(
        name="material_contracts_disclosed",
        category="legal",
        satisfied_at="signing",
        who_controls="seller",
        blocking_risk="low",
        walk_right=False,
        partner_note=(f"Expecting ~{inputs.material_contracts_count} "
                      "material contracts. Omissions surface "
                      "post-close as indemnity claims."),
    ))

    # Officer certificate.
    conds.append(ClosingCondition(
        name="officers_secretary_certificates",
        category="legal",
        satisfied_at="close",
        who_controls="seller",
        blocking_risk="low",
        walk_right=False,
        partner_note=("Plumbing. Seller's counsel owns; partner "
                      "only cares when a box is blank."),
    ))

    high = sum(1 for c in conds if c.blocking_risk == "high")
    third_party = sum(1 for c in conds if c.who_controls == "third_party")
    walks = sum(1 for c in conds if c.walk_right)

    if high >= 3:
        note = (f"{high} high-risk conditions, {third_party} third-"
                "party dependent. Partner should set outside "
                "date with 60-day cushion + reverse termination "
                "fee protection.")
    elif high >= 1:
        note = (f"{high} high-risk + {third_party} third-party "
                f"dependent, {walks} walk-rights. Standard "
                "closing calendar with weekly condition tracker.")
    else:
        note = (f"Clean close: {walks} walk-rights, no high-risk "
                "conditions. Associates can run the close memo; "
                "partner reviews final.")

    return ClosingConditionsReport(
        conditions=conds,
        high_risk_count=high,
        third_party_dependent_count=third_party,
        walk_right_count=walks,
        partner_note=note,
    )


def render_closing_conditions_markdown(r: ClosingConditionsReport) -> str:
    lines = [
        "# Closing conditions list",
        "",
        f"_{r.partner_note}_",
        "",
        f"- High-risk: {r.high_risk_count}",
        f"- Third-party dependent: {r.third_party_dependent_count}",
        f"- Walk-rights: {r.walk_right_count}",
        "",
        "| Condition | Category | Satisfied at | Who controls | "
        "Risk | Walk right | Partner note |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in r.conditions:
        walk = "yes" if c.walk_right else "no"
        lines.append(
            f"| {c.name} | {c.category} | {c.satisfied_at} | "
            f"{c.who_controls} | {c.blocking_risk} | {walk} | "
            f"{c.partner_note} |"
        )
    return "\n".join(lines)
