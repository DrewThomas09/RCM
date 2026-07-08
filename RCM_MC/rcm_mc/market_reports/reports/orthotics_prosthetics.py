"""Orthotics & Prosthetics (O&P) — custom braces and artificial limbs.

Deals-only pattern (copied from hospice.py): no vendored national facility
file, so geography is honestly omitted and the report leans on the qualitative
deep sections + ``live_figures_from_dive("orthotics_prosthetics")`` for any
SOURCED corpus figures. Unlike the other four in this batch, O&P IS a reimbursed
vertical — devices + fitting are billed as DMEPOS "L-codes" on the Medicare fee
schedule — so the sections are authored around L-code / K-level mechanics, the
custom-vs-off-the-shelf competitive-bidding line, the audit / brace-fraud
history, and the Hanger-led clinic roll-up.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="orthotics_prosthetics",
    name="Orthotics & Prosthetics (O&P)",
    care_setting="Other services",
    naics="339113",
    one_line_def=(
        "The clinical fitting, custom fabrication, and delivery of orthoses "
        "(braces/supports) and prostheses (artificial limbs) for patients with "
        "limb loss, spinal/musculoskeletal conditions, and neuromuscular "
        "deficits — provided by certified prosthetists/orthotists at patient-"
        "care facilities and reimbursed by Medicare and payers as DMEPOS "
        "'L-code' HCPCS."),
    tam_headline=TamHeadline(
        value=6.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled total US O&P market (~$5-7B, devices + patient-care "
            "services). The Medicare O&P slice is published in CMS DMEPOS / "
            "Part B data (a GOV subset, directional). Growth is the modeled "
            "composite of diabetes/dysvascular amputation demand, aging, the "
            "microprocessor-component upgrade cycle, and annual fee-schedule "
            "updates."),
    ),
    executive_summary=[
        "This is a real, reimbursed DMEPOS vertical — the device plus the "
        "fitting are billed together under 'L-code' HCPCS on the Medicare "
        "fee schedule, custom devices paying materially more than off-the-shelf. "
        "That makes it a recurring-Medicare, aging-demand business, unlike the "
        "non-reimbursed services around it.",
        "The K-level is the whole reimbursement game for lower-limb prosthetics. "
        "The K0-K4 functional classification determines which components "
        "Medicare will cover — a K3/K4 rating unlocks microprocessor knees and "
        "energy-storing feet — so audit-defensible documentation of functional "
        "level is the margin, and upcoded K-levels are an audit time bomb.",
        "The custom + certified-clinician requirement is the moat. CMS "
        "competitive bidding can commoditize off-the-shelf orthoses, but custom "
        "prosthetics and orthotics require a certified practitioner and are "
        "exempt — protecting pricing and the roll-up thesis.",
        "Demand is a diabetes / dysvascular story: most lower-limb amputations "
        "are driven by diabetes and peripheral arterial disease, so the base "
        "grows with the diabetes epidemic and aging — durable and non-"
        "discretionary — with trauma and cancer the higher-acuity, workers-"
        "comp/commercial-pay tail.",
        "A classic fragmented roll-up: Hanger (taken private by Patient Square) "
        "is the national clinic platform above a long tail of independent "
        "practices — but the 2019 'Operation Brace Yourself' OTS-brace fraud "
        "takedown tarred the category, so diligence must separate legitimate "
        "custom patient care from mail-order OTS-brace telemarketing.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral from vascular surgery, endocrinology, wound care, ortho, "
            "physiatry, or the VA (O&P is referral-driven)",
            "Clinical evaluation + functional-level (K-level) assessment for "
            "lower-limb prosthetics",
            "Detailed written order + medical-necessity documentation "
            "(audit-critical)",
            "Casting / scanning and custom fabrication (central or in-clinic "
            "lab) or off-the-shelf/prefabricated fitting",
            "Delivery, fitting, alignment, and patient training",
            "Follow-up adjustments, repairs, and component replacement over the "
            "device life",
            "DMEPOS claim on the appropriate L-code(s); prior auth and audit "
            "response as required",
        ],
        sites_of_care=[
            "O&P patient-care clinics (the core setting)",
            "Hospital-based and rehab-affiliated O&P departments",
            "VA / DoD facilities and contracted providers (a major channel)",
            "Central fabrication labs (custom device manufacturing)",
            "Mobile / bedside fitting for post-acute and SNF patients",
        ],
        money_flow=(
            "O&P devices and the professional fitting/fabrication are billed "
            "together as durable medical equipment, prosthetics, orthotics and "
            "supplies (DMEPOS) using HCPCS Level II 'L-codes,' each priced on "
            "the Medicare DMEPOS fee schedule and updated annually. A single "
            "L-code payment bundles the device and the clinical service, and "
            "custom-fabricated devices pay materially more than off-the-shelf or "
            "prefabricated ones. For lower-limb prosthetics the covered "
            "component set is gated by the patient's K-level (K0-K4 functional "
            "classification), which is therefore the single most important "
            "reimbursement determinant. Payers span Medicare (large, especially "
            "for dysvascular/diabetic and older amputees), commercial, Medicaid, "
            "the VA/DoD, and workers' compensation (the best-paying channel, "
            "especially for traumatic amputation). Claims are documentation- and "
            "audit-heavy — detailed written orders, face-to-face requirements, "
            "and proof of medical necessity determine whether the payment "
            "sticks."),
        key_players=(
            "Two tiers. On the patient-care side, Hanger Inc. is the dominant "
            "national O&P clinic chain (~900 clinics, taken private by Patient "
            "Square Capital), with Ottobock and Össur operating patient-care "
            "clinics alongside their device businesses, above a long fragmented "
            "tail of independent regional practices — the roll-up pool. "
            "Upstream, the device manufacturers — Össur, Ottobock, Blatchford, "
            "Fillauer, WillowWood, and College Park — make the feet, knees "
            "(including microprocessor knees like the C-Leg and Rheo), and "
            "myoelectric hands that the clinics fit."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Lower-limb prosthetics",
                    "highest-ticket — K-level-gated components",
                    "ILLUSTRATIVE · modeled segment; L-code-driven"),
            Segment("Custom & prefabricated orthotics (braces)",
                    "largest by volume",
                    "ILLUSTRATIVE · modeled segment"),
            Segment("Upper-limb & myoelectric prosthetics",
                    "specialized, high-value, lower-volume",
                    "ILLUSTRATIVE · modeled segment"),
            Segment("Medicare O&P allowed charges",
                    "published DMEPOS / Part B figure (directional)",
                    "GOV · CMS DMEPOS & Part B spending data"),
            Segment("US persons living with limb loss",
                    "~2M+ and rising with diabetes/PAD",
                    "ACADEMIC · limb-loss epidemiology literature"),
        ],
        growth_drivers=[
            "Diabetes / dysvascular amputation incidence — the primary demand "
            "curve",
            "Aging population and rising musculoskeletal orthotic need",
            "Microprocessor-component upgrade cycle (K3/K4 device mix)",
            "Annual DMEPOS fee-schedule updates (CPI-U-adjusted L-codes)",
            "Off-the-shelf orthotic competitive-bidding inclusion risk (a "
            "pricing DRAG on the OTS segment)",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare (DMEPOS L-codes)": 0.34,
            "Commercial": 0.29,
            "Medicaid": 0.14,
            "VA / DoD / federal": 0.13,
            "Workers' comp / other": 0.10,
        },
        rate_mechanics=[
            "L-code HCPCS on the Medicare DMEPOS fee schedule — each device/"
            "service billed on specific L-codes, updated annually (CPI-U-"
            "adjusted), with custom-fabricated codes paying materially above "
            "off-the-shelf/prefabricated.",
            "K-level functional classification (K0-K4) — gates which lower-limb "
            "prosthetic components Medicare covers; K3/K4 unlocks microprocessor "
            "knees and energy-storing feet — the single biggest reimbursement "
            "determinant.",
            "Custom vs off-the-shelf distinction — custom O&P requires a "
            "certified practitioner and is exempt from DMEPOS competitive "
            "bidding; OTS orthoses are exposed to bidding-driven price cuts.",
            "Documentation & prior authorization — detailed written orders, "
            "face-to-face encounters, and medical-necessity proof (DME MAC LCDs) "
            "gate payment; O&P is a high-audit-rate DMEPOS category.",
            "Payer breadth — commercial, Medicaid, VA/DoD, and workers' comp "
            "each price differently; workers' comp and commercial typically pay "
            "best, especially for traumatic amputation.",
        ],
        reimbursement_risk=(
            "The dominant reimbursement risk is documentation and audit. O&P is "
            "historically one of Medicare's highest improper-payment categories, "
            "and lower-limb prosthetic payment turns on the K-level and the "
            "supporting medical-necessity file — so RAC/UPIC audits, "
            "extrapolated recoupment, and the DME MAC LCD coverage rules "
            "(recall the 2015 draft lower-limb-prosthetic LCD that would have "
            "sharply tightened coverage) are first-order. A second risk is "
            "competitive bidding: CMS has periodically proposed sweeping off-"
            "the-shelf orthoses into the DMEPOS bidding program, which would cut "
            "OTS pricing (custom remains exempt). A third is reputational-"
            "regulatory: the 2019 'Operation Brace Yourself' telemarketing OTS-"
            "brace fraud takedown intensified scrutiny of the brace segment, "
            "even though the fraud lived in mail-order OTS, not custom clinic "
            "O&P."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare DMEPOS fee schedule & L-code coverage (DME MAC LCDs)",
                 "Sets the L-code payment amounts and the Local Coverage "
                 "Determinations (including the K-level rules for lower-limb "
                 "prosthetics) that decide what is covered — the core economic "
                 "rulebook.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/dmepos-fee-schedule"),
            Rule("DMEPOS supplier standards + accreditation & surety bond",
                 "To bill Medicare an O&P provider must be an accredited DMEPOS "
                 "supplier meeting the supplier standards and bond requirement — "
                 "the participation gate.",
                 "https://www.cms.gov/medicare/enrollment-renewal/providers-suppliers/dmepos"),
            Rule("BIPA §427 'qualified provider' rule (long pending)",
                 "The 2000 Benefits Improvement and Protection Act required O&P "
                 "be furnished by qualified (certified/licensed) practitioners "
                 "for payment; CMS never fully implemented it — full "
                 "implementation would favor the certified consolidators.",
                 None),
            Rule("ABC / BOC practitioner certification + state licensure",
                 "The American Board for Certification (ABC) and Board of "
                 "Certification/Accreditation (BOC) certify practitioners and "
                 "accredit facilities; ~20 states license O&P practitioners — "
                 "the credential barrier that defines the custom moat.",
                 "https://www.abcop.org/"),
            Rule("DMEPOS competitive bidding — OTS orthosis inclusion risk",
                 "CMS has proposed including off-the-shelf orthoses in the "
                 "competitive bidding program (custom exempt) — a recurring "
                 "pricing threat to the OTS segment.",
                 "https://www.cms.gov/medicare/payment/durable-medical-equipment-competitive-bidding"),
        ],
        policy_watch=[
            "Any movement on the BIPA §427 qualified-provider rule (a tailwind "
            "for certified roll-ups)",
            "DMEPOS competitive-bidding rounds and OTS-orthosis inclusion",
            "Lower-limb prosthetic LCD / K-level coverage revisions",
            "OIG improper-payment reviews of orthotic braces and prosthetics",
            "Annual DMEPOS fee-schedule updates and any budget-neutrality "
            "adjustments",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "A national platform above a long independent tail. Hanger operates "
            "hundreds of clinics nationwide, but the majority of O&P patient "
            "care is still delivered by independent regional practices and "
            "hospital-based departments — the fragmented roll-up pool. No "
            "vendored O&P facility file exists (ABC/BOC rosters are not "
            "vendored), so a computed HHI is honestly omitted."),
        hhi_or_share=(
            "Qualitatively, Hanger is the clear patient-care leader by clinic "
            "count, with Ottobock and Össur adding clinic footprints alongside "
            "their device dominance; the independent-practice tail remains "
            "large and geographically dispersed."),
        consolidation=(
            "Active roll-up. Hanger assembled the national platform over "
            "decades and was taken private by Patient Square Capital (~$1.25B) "
            "to accelerate consolidation; device makers Össur and Ottobock have "
            "acquired patient-care clinics to integrate downstream. The thesis "
            "is consolidating independent practices, standardizing billing and "
            "audit-defense, leveraging central fabrication, and riding the "
            "diabetic/dysvascular amputation demand curve."),
        pe_activity=(
            "Active. The attributes are recurring Medicare/commercial "
            "reimbursement, an aging/diabetic demand tailwind, a fragmented "
            "independent base, and a certified-clinician + custom-fabrication "
            "moat that protects pricing against competitive bidding. Quality-of-"
            "earnings centers on the K-level documentation and audit history, "
            "the custom-vs-OTS mix, payer mix (workers' comp/commercial upside), "
            "referral-source concentration, and clean separation from any OTS-"
            "brace telemarketing exposure."),
        notable_players=[
            "Hanger Inc. (Patient Square Capital)", "Össur", "Ottobock",
            "Blatchford", "Fillauer", "WillowWood", "College Park",
            "independent regional O&P practices",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue per device", "wide range by device",
                "Lower-limb microprocessor prosthetics bill in the tens of "
                "thousands; custom orthoses far less — the mix sets the "
                "average."),
            Kpi("Custom vs off-the-shelf mix", "custom = moat",
                "Custom devices pay more and are competitive-bidding-exempt; a "
                "custom-weighted book is higher-margin and better-protected."),
            Kpi("K-level mix (K3/K4 share)", "value concentration",
                "Higher functional levels unlock the premium microprocessor "
                "components — the high-value revenue, and the audit focus."),
            Kpi("Payer mix (WC/commercial share)", "margin driver",
                "Workers' comp and commercial pay best; a Medicaid-heavy book "
                "runs thinner."),
            Kpi("Audit / denial rate", "low required",
                "O&P is a high-audit DMEPOS category; denial and extrapolated-"
                "recoupment exposure is a core risk metric."),
            Kpi("Days to delivery", "operational",
                "Fabrication and fitting cycle time affects patient outcomes and "
                "working capital."),
            Kpi("Clinic-level EBITDA margin", "15-22%",
                "At scale with central fabrication and disciplined billing; "
                "lower for subscale, audit-exposed, or OTS-commoditized books."),
        ],
        margin_profile=(
            "O&P clinic margin is a custom-mix, K-level, and payer-mix story. "
            "Revenue per device swings enormously — a microprocessor lower-limb "
            "prosthesis bills in the tens of thousands while a prefabricated "
            "orthosis bills a fraction of that — so the custom vs off-the-shelf "
            "and the K3/K4 component mix drive the top line, while the device "
            "manufacturers capture a meaningful share of COGS. Certified-"
            "practitioner labor, central-fabrication efficiency, and billing/"
            "audit-defense overhead round out the cost base. Workers' comp and "
            "commercial payers lift margin; Medicaid compresses it. Scale helps "
            "through central fabrication and standardized documentation, but the "
            "binding constraint on margin durability is audit defensibility — a "
            "book that cannot substantiate its K-levels and medical necessity is "
            "one extrapolated recoupment away from a very different P&L."),
    ),
    risks=[
        Risk("Audit / documentation & K-level recoupment", "High",
             "O&P is a top improper-payment DMEPOS category; RAC/UPIC audits "
             "and extrapolated recoupment on unsupported K-levels can erase "
             "profit."),
        Risk("DMEPOS competitive bidding on OTS orthoses", "Medium",
             "Inclusion of off-the-shelf orthoses in bidding would cut OTS "
             "pricing (custom exempt) — an OTS-mix-dependent risk."),
        Risk("Reimbursement / LCD coverage tightening", "Medium",
             "A restrictive lower-limb prosthetic LCD (cf. the 2015 draft) or "
             "fee-schedule pressure would compress the high-value segment."),
        Risk("Reputational contagion from OTS-brace fraud", "Medium",
             "The 2019 telemarketing brace-fraud takedown tarred the category; "
             "any OTS-brace/telemarketing exposure is a diligence red flag."),
        Risk("Referral-source concentration", "Medium",
             "O&P is referral-driven (vascular, wound care, VA, ortho); "
             "dependence on a few referrers is a revenue-durability risk."),
        Risk("Certified-practitioner labor supply", "Low",
             "A specialized, credential-gated workforce; scarcity supports the "
             "moat but constrains growth and raises labor cost."),
    ],
    diligence_questions=[
        "What is the custom vs off-the-shelf revenue mix, and how exposed is "
        "the OTS portion to competitive bidding?",
        "What is the K-level distribution on lower-limb prosthetics, and how "
        "audit-defensible is the functional-level documentation?",
        "What is the audit / denial / recoupment history (RAC, UPIC, ADR), and "
        "what reserves are held?",
        "What is the payer mix — Medicare, commercial, Medicaid, VA/DoD, "
        "workers' comp — and the resulting blended margin?",
        "Is there ANY off-the-shelf-brace telemarketing or mail-order exposure "
        "that connects the book to the fraud-tarred segment?",
        "What is referral-source concentration, and how durable are the key "
        "vascular/wound-care/VA/ortho relationships?",
        "What is the central-fabrication footprint and its effect on COGS and "
        "delivery times?",
        "How would full implementation of the BIPA §427 qualified-provider rule "
        "affect the competitive set and the book?",
    ],
    insider_lens=[
        "The K-level is the whole lower-limb reimbursement game. K0-K4 "
        "functional classification decides which components Medicare covers — a "
        "K3/K4 rating unlocks microprocessor knees and energy-storing feet — so "
        "the documentation of functional level, and its audit defensibility, IS "
        "the margin. A book that leans on aggressive K-levels is an audit time "
        "bomb, not a growth story.",
        "Separate the custom clinic from the mail-order brace. The 2019 "
        "'Operation Brace Yourself' takedown ($1.7B) was telemarketed off-the-"
        "shelf braces, not certified custom patient care — but it tarred the "
        "whole category. Diligence must prove the target is legitimate custom "
        "O&P with no OTS-telemarketing exposure.",
        "Custom + certified is the moat CMS itself protects. Competitive "
        "bidding can commoditize off-the-shelf orthoses, but custom prosthetics "
        "and orthotics require a certified practitioner and are exempt — so the "
        "more custom the mix, the more pricing survives the bidding threat. "
        "Underwrite the custom share.",
        "The demand curve is the diabetes epidemic. Most lower-limb amputations "
        "are dysvascular (diabetes + PAD), so the base is a durable, non-"
        "discretionary, growing population — with trauma and cancer the higher-"
        "acuity, workers-comp/commercial-pay tail. Map the book to the diabetes "
        "and vascular-disease geography, not to raw population.",
        "It is a referral business wearing a device label. Volume comes from "
        "vascular surgeons, wound care, endocrinology, the VA, and physiatry — "
        "so referral-source relationships and concentration are the real asset "
        "and the real risk, and the long-pending BIPA §427 qualified-provider "
        "rule, if ever implemented, would hand the certified consolidators a "
        "structural advantage over uncertified billers.",
    ],
    connections=default_connections(
        "orthotics_prosthetics",
        deals_sector="orthotics_prosthetics",
        connectors=[
            ("cms_open_data_mup_dme_by_supplier_service",
             "CMS Medicare DME/supplier procedure summary — L-code volume & "
             "allowed charges (the revenue signal)"),
            ("provider_data_medical_equipment_suppliers",
             "CMS Provider Data — DMEPOS medical-equipment suppliers (the O&P "
             "supplier universe)"),
            ("cdc_data_diabetes_state_burden",
             "CDC — diabetes burden by state (the dysvascular-amputation demand "
             "driver)"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — orthotist/prosthetist & DMEPOS-supplier mapping"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen; "
             "pointed given the brace-fraud history)"),
        ],
    ),
    sources=[
        Source("CMS — DMEPOS fee schedule and L-code coverage (DME MAC LCDs)",
               "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/dmepos-fee-schedule"),
        Source("CMS — Medicare DMEPOS / Part B spending data (O&P allowed "
               "charges)", "GOV",
               "https://data.cms.gov/"),
        Source("American Board for Certification in Orthotics, Prosthetics & "
               "Pedorthics (ABC) — practitioner/facility standards", "INDUSTRY",
               "https://www.abcop.org/"),
        Source("American Orthotic & Prosthetic Association (AOPA) — market and "
               "policy data", "INDUSTRY",
               "https://www.aopanet.org/"),
        Source("HHS OIG — improper-payment reviews of orthotic braces and "
               "prosthetics", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("Limb-loss epidemiology (Ziegler-Graham et al., prevalence of "
               "limb loss in the US)", "ACADEMIC",
               "https://pubmed.ncbi.nlm.nih.gov/18295618/"),
        Source("PE Desk industry deep-dive + realized-deal corpus (orthotics & "
               "prosthetics)", "INTERNAL",
               "/diligence/tam-sam?template=orthotics_prosthetics"),
    ],
    live_figures=live_figures_from_dive("orthotics_prosthetics"),
    trends=(
        "O&P is a reimbursed, demographically-driven vertical consolidating "
        "around a certified-clinician moat. The demand base is expanding on the "
        "diabetes and peripheral-arterial-disease curve — the majority of "
        "lower-limb amputations are dysvascular — layered on an aging "
        "population and a steady microprocessor-component upgrade cycle that "
        "lifts device value at the high (K3/K4) end. Reimbursement runs through "
        "DMEPOS L-codes on the Medicare fee schedule, where the K-level "
        "functional classification gates the covered component set and audit "
        "intensity is high; O&P has repeatedly ranked among Medicare's largest "
        "improper-payment categories, and the 2019 telemarketing brace-fraud "
        "takedown tarred the off-the-shelf segment (though not custom clinic "
        "care). The competitive structure is a national platform — Hanger, "
        "taken private by Patient Square Capital — consolidating a long "
        "independent tail, with device makers Össur and Ottobock integrating "
        "downstream into patient care. The protective throughline is that "
        "custom prosthetics and orthotics require a certified practitioner and "
        "are exempt from competitive bidding, so the more custom the mix the "
        "more durable the pricing. The trajectory rewards audit-defensible, "
        "custom-weighted, workers-comp/commercial-diversified books."),
    growth_levers=[
        GrowthLever(
            "Diabetes / dysvascular amputation demand",
            "Rising diabetes and peripheral-arterial-disease prevalence drives "
            "the majority of lower-limb amputations — the primary, durable "
            "demand engine.",
            "primary demand driver", "GOV"),
        GrowthLever(
            "Aging population & orthotic need",
            "An aging population expands musculoskeletal and neuromuscular "
            "orthotic demand alongside prosthetic need.",
            "+ steady volume", "ILLUSTRATIVE"),
        GrowthLever(
            "Microprocessor-component upgrade cycle",
            "Advancing K3/K4 components (microprocessor knees, energy-storing "
            "feet, myoelectric hands) raise device value and revenue per "
            "prosthesis.",
            "+ revenue per device", "ILLUSTRATIVE"),
        GrowthLever(
            "Fragmented-practice consolidation",
            "Rolling up independent clinics standardizes billing/audit defense "
            "and leverages central fabrication — the core M&A value-creation "
            "lever.",
            "share + margin uplift", "ILLUSTRATIVE"),
        GrowthLever(
            "OTS competitive-bidding pricing pressure",
            "Inclusion of off-the-shelf orthoses in DMEPOS competitive bidding "
            "would cut OTS pricing — the drag on the commoditized segment "
            "(custom exempt).",
            "−OTS pricing", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Dysvascular (diabetes + PAD) lower-limb amputation incidence",
        analysis=(
            "The dominant demand driver is dysvascular lower-limb amputation — "
            "the majority of amputations in the US are caused by diabetes and "
            "peripheral arterial disease rather than trauma. That base grows "
            "with the diabetes epidemic, an aging population, and the vascular "
            "comorbidity burden, making it durable and non-discretionary; it is "
            "also the highest-value O&P work because a lower-limb prosthesis and "
            "its K-level-gated components carry the largest L-code payments. The "
            "trauma and cancer amputation tail is smaller but higher-acuity and "
            "better-paid (workers' comp and commercial). Because the demand is "
            "geographically correlated with diabetes and vascular-disease "
            "prevalence, the CDC diabetes-burden connector below maps the "
            "amputation-demand surface directly. The offsetting policy drag is "
            "not on volume but on price — competitive bidding on off-the-shelf "
            "orthoses — which leaves the custom, certified, amputation-driven "
            "core protected."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Device components / COGS (manufacturer share)",
            "~35-50% of cost",
            "Feet, knees (including microprocessor units), hands, and materials "
            "purchased from the device makers — the largest cost line, "
            "concentrated in high-K-level prosthetics.", "ILLUSTRATIVE"),
        CostDriver(
            "Certified-practitioner clinical labor",
            "~20-30% of cost",
            "Credentialed prosthetists/orthotists who evaluate, fit, and follow "
            "up — the credential-gated workforce that is the moat and a cost.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Central fabrication & materials",
            "~10-15% of cost",
            "Custom device fabrication (in-clinic or central lab) — the "
            "efficiency scale advantage the consolidators pursue.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing, documentation & audit defense",
            "~8-12% of cost",
            "K-level documentation, prior authorization, and RAC/UPIC audit "
            "response — a real and rising overhead given the audit intensity.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Clinic occupancy & patient-care overhead",
            "~8-12% of cost",
            "The physical clinic network and patient-facing overhead across a "
            "dispersed footprint.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "O&P patient care follows amputation and musculoskeletal demand, which "
        "correlates with diabetes and peripheral-arterial-disease prevalence, "
        "so the meaningful geographic layer is the diabetes-burden surface (the "
        "CDC connector below) and the DMEPOS-supplier density (the CMS supplier "
        "and DME-utilization connectors). No national O&P facility file is "
        "vendored (ABC/BOC rosters are not vendored), so a computed facility "
        "breakdown is honestly omitted; the diabetes-burden and DMEPOS-"
        "utilization connectors stand in as the real demand and supply reads."),
)

register(REPORT)
