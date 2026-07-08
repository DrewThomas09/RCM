"""Wound Care — management of chronic and complex non-healing wounds.

Deals-only pattern (no vendored national wound-center file — the honest
geography layer is the sector's deal history, so state breakdown and a CMS
certification trend are omitted rather than fabricated). The qualitative
sections are authored around the reimbursement fact that dominates the sector
today: the explosion of Medicare Part B skin-substitute (CTP) spending and the
CMS payment reform that would reset the office-based economics.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="wound_care",
    name="Wound Care",
    care_setting="Post-acute",
    naics="621111",
    one_line_def=(
        "Diagnosis and treatment of chronic and complex non-healing wounds — "
        "diabetic foot ulcers, venous and arterial leg ulcers, pressure "
        "injuries, and dehisced surgical wounds — delivered in hospital "
        "outpatient wound centers, physician offices, the home, and nursing "
        "facilities, and paid through a patchwork of physician-fee, facility-"
        "fee, hyperbaric, and skin-substitute reimbursement."),
    tam_headline=TamHeadline(
        value=28.1, unit="$B", growth_pct=5.0, basis_label="ACADEMIC",
        basis_note=(
            "Medicare spending on chronic-wound care was estimated at $28.1B "
            "(conservative) to $96.8B annually across ~8.2M beneficiaries "
            "(Nussbaum et al., Value in Health, 2018) — we headline the "
            "conservative lower bound. Growth is the modeled composite of the "
            "TAM/SAM drivers (diabetes/aging demand +, rate +, skin-substitute "
            "payment reform −)."),
    ),
    executive_summary=[
        "One reimbursement story dominates the sector right now: the explosion "
        "of Medicare Part B spending on skin substitutes (cellular/tissue "
        "products, 'CTPs'). An ASP-based payment loophole made applying high-"
        "priced amniotic/placental products in the physician-office setting "
        "extraordinarily margin-rich, and CMS has proposed to reset how they are "
        "paid — potentially gutting the office-based CTP economics. Underwrite "
        "CTP payment reform before anything else.",
        "There are really two businesses under one name. Hospital outpatient "
        "wound centers (a management-company model led by Healogics) bill "
        "facility + professional fees and lean on hyperbaric oxygen; office, "
        "mobile, and SNF wound care bill the physician fee schedule and, until "
        "reform, the CTP margin. Know which model you are buying — the "
        "reimbursement exposure is completely different.",
        "Wound care is one of the most DOJ- and OIG-scrutinized services in "
        "Medicine — medically-unnecessary debridement, hyperbaric oxygen "
        "over-utilization, and skin-substitute schemes have produced repeated "
        "enforcement actions. Compliance history is a first-order diligence "
        "item, not a footnote.",
        "The underlying demand is real, large, and growing: diabetes, obesity, "
        "peripheral arterial and venous disease, and aging drive a rising "
        "chronic-wound burden, and diabetic foot ulcers precede most non-"
        "traumatic amputations — so an outcomes-based platform (healing, "
        "amputation prevention) is defensible independent of any single billing "
        "code.",
        "Consolidation is bifurcated: the HOPD wound-center management layer is "
        "concentrated (Healogics, RestorixHealth), while office/mobile and SNF "
        "wound-physician practices are fragmented and roll-up-able (Vohra leads "
        "SNF) — but the office roll-up thesis is entangled with the very CTP "
        "economics reform is targeting.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral — primary care, podiatry, vascular, hospital discharge",
            "Assessment — wound etiology, vascular status, offloading needs",
            "Debridement + wound-bed preparation (serial visits)",
            "Advanced therapy — skin substitutes/CTPs, NPWT, offloading, HBOT",
            "Infection & comorbidity management (diabetes, PAD, venous disease)",
            "Healing progression tracking toward closure (time-to-heal)",
            "Billing — MPFS (office), OPPS facility fee (HOPD), HBOT, CTP",
            "Outcomes / amputation-prevention reporting",
        ],
        sites_of_care=[
            "Hospital outpatient wound center (HOPD — the management-company "
            "model)",
            "Physician office / clinic (podiatry, vascular, plastics, wound-"
            "certified)",
            "Home & mobile wound care (nurse and physician home visits)",
            "Skilled nursing / LTC facilities (rounding wound physicians)",
        ],
        money_flow=(
            "Wound care is paid through a patchwork that varies entirely by site "
            "of service. In a hospital outpatient wound center, the hospital "
            "bills an OPPS facility fee and the physician bills the fee schedule, "
            "with hyperbaric oxygen therapy (HBOT) a distinct, high-revenue, "
            "heavily-documented line — typically run under a management-company "
            "arrangement that shares the economics with the host hospital. In "
            "the office, home, or nursing facility, the clinician bills the "
            "Medicare Physician Fee Schedule for evaluation, debridement (CPT "
            "11042-11047), and the application of skin substitutes. The economic "
            "swing factor has been those skin substitutes: paid on an average-"
            "sales-price basis, high-priced cellular/tissue products applied in "
            "the non-facility office setting generated outsized margins, driving "
            "explosive Part B utilization — and drawing the CMS payment reform "
            "and enforcement that now hang over the office-based model."),
        key_players=(
            "The hospital-outpatient layer is a management-company oligopoly: "
            "Healogics is the dominant national wound-center manager (hundreds "
            "of centers), with RestorixHealth, Wound Care Advantage, and "
            "SerenaGroup behind it. In skilled nursing, Vohra Wound Physicians "
            "is the national rounding wound-physician group. The office, mobile, "
            "and home-based layer is fragmented across podiatry, vascular, and "
            "wound-certified clinicians — the roll-up whitespace. Adjacent but "
            "distinct are the CTP and device manufacturers (MiMedx, "
            "Organogenesis, Integra, Smith+Nephew, Solventum) whose product "
            "economics the reimbursement reform directly targets."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicare beneficiaries with wounds",
                    "~8.2M beneficiaries",
                    "ACADEMIC · Nussbaum et al. 2018 (Value in Health)"),
            Segment("Medicare chronic-wound spend (all wound types)",
                    "~$28.1B-$96.8B",
                    "ACADEMIC · Nussbaum et al. 2018 (wide range)"),
            Segment("Diabetic foot ulcer share of the burden",
                    "the largest / costliest wound type",
                    "ACADEMIC · diabetic-wound epidemiology"),
            Segment("Medicare Part B skin-substitute (CTP) spend",
                    "grew into the billions — a top-growth Part B line",
                    "GOV · CMS Part B / MedPAC (skin substitutes)"),
            Segment("Hospital outpatient wound centers (managed)",
                    "hundreds of centers under national managers",
                    "INDUSTRY · wound-center management footprint"),
        ],
        growth_drivers=[
            "Diabetes + obesity prevalence — the master demand engine (DFU)",
            "Aging + PAD/venous disease + pressure injuries — rising wound "
            "burden",
            "Advanced-therapy adoption (skin substitutes, NPWT) — utilization "
            "and intensity",
            "Amputation-prevention / limb-salvage focus — clinical + payer pull",
            "Skin-substitute payment reform − — a large negative on office "
            "economics",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare FFS": 0.45,
            "Medicare Advantage": 0.20,
            "Commercial": 0.20,
            "Medicaid / other": 0.15,
        },
        rate_mechanics=[
            "Medicare Physician Fee Schedule (MPFS) — evaluation & management, "
            "debridement (CPT 11042-11047), and skin-substitute application in "
            "the office/home/SNF setting.",
            "Skin substitutes / CTPs — historically paid on average sales price "
            "(ASP+6%) with a large non-facility office margin; the CMS-proposed "
            "reform to a bundled / single-payment approach is the sector's "
            "defining reimbursement risk.",
            "OPPS facility fees — the hospital outpatient wound-center revenue, "
            "shared under a management-company arrangement with the host "
            "hospital.",
            "Hyperbaric Oxygen Therapy (HBOT) — a distinct Part B revenue line "
            "governed by MAC Local Coverage Determinations and heavy "
            "documentation; a favorite audit target.",
            "Negative-pressure wound therapy (NPWT), offloading, and DME — "
            "additional billable modalities under MPFS/DME rules.",
            "MAC Local Coverage Determinations for CTPs — MAC-specific coverage "
            "policies restrict which skin substitutes are covered for which "
            "indications, reshaping product mix by region.",
        ],
        reimbursement_risk=(
            "The dominant, live risk is skin-substitute (CTP) payment reform. "
            "The ASP-based office reimbursement of high-priced cellular/tissue "
            "products drove Part B skin-substitute spending into the billions — "
            "one of the fastest-growing lines in all of Medicare — and CMS has "
            "proposed to reset the payment methodology (toward a bundled or "
            "single rate). For any office, mobile, or SNF wound platform whose "
            "margins ride on CTP application, that reform is potentially "
            "existential and its timing/design is the first thing to model. "
            "Alongside it sit HBOT audit exposure (LCD-driven documentation "
            "denials) and a heavy enforcement backdrop: wound care is among the "
            "most DOJ/OIG-scrutinized services, with repeated actions over "
            "unnecessary debridement, HBOT over-utilization, and CTP schemes."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Physician Fee Schedule (MPFS) — wound services",
                 "Sets office/home/SNF payment for E/M, debridement, and skin-"
                 "substitute application — the price of most non-facility wound "
                 "care.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Skin-substitute / CTP payment reform (CMS proposed rules)",
                 "The proposal to reset skin-substitute payment away from ASP "
                 "toward a bundled/single rate — the single most important "
                 "reimbursement change facing the office-based sector.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Hyperbaric oxygen therapy — MAC Local Coverage Determinations",
                 "MAC-specific coverage and documentation rules for HBOT drive "
                 "denials and audits on a major wound-center revenue line.",
                 "https://www.cms.gov/medicare-coverage-database/"),
            Rule("OIG/DOJ enforcement — wound care fraud & abuse",
                 "Repeated actions over medically-unnecessary debridement, HBOT "
                 "over-utilization, and skin-substitute schemes make compliance "
                 "history first-order diligence.",
                 "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
            Rule("Hospital OPPS — outpatient wound-center facility payment",
                 "Sets the HOPD facility fee that, with the management-company "
                 "split, funds the hospital-based wound-center model.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/hospital-outpatient"),
        ],
        policy_watch=[
            "Skin-substitute/CTP payment-reform final rule — methodology & timing",
            "MAC LCDs restricting covered CTP products and indications",
            "HBOT coverage/audit intensity and documentation standards",
            "OIG/DOJ enforcement trajectory on wound care",
            "Site-of-service payment differentials (office vs HOPD)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Bifurcated. The hospital outpatient wound-center layer is "
            "concentrated under a few national management companies (Healogics "
            "leads), while the office, mobile, home, and SNF wound-physician "
            "layer is highly fragmented across podiatry, vascular, plastics, and "
            "wound-certified clinicians — the roll-up whitespace. There is no "
            "vendored national wound-center file, so geography here is a deal-"
            "history read rather than a facility map."),
        hhi_or_share=(
            "Healogics is the clear leader in managed hospital wound centers and "
            "Vohra in SNF wound physicians; the office/mobile layer has no "
            "dominant player. No public facility census exists to compute an "
            "HHI, so concentration is described qualitatively."),
        consolidation=(
            "Two distinct consolidation stories. The HOPD management model has "
            "long been PE-owned and concentrated (Healogics; RestorixHealth). "
            "The office/mobile/SNF physician layer is an active roll-up target — "
            "but the office thesis is entangled with the skin-substitute "
            "economics that reform is aimed at, so recent underwriting has "
            "shifted from CTP-margin capture toward outcomes, referral density, "
            "and amputation-prevention value."),
        pe_activity=(
            "Sponsor activity spans the Healogics-style HOPD management platform, "
            "SNF and mobile wound-physician roll-ups, and adjacency into CTP/"
            "device products. The CTP-reform overhang has repriced the office "
            "roll-up: platforms built on the skin-substitute arbitrage face a "
            "reset, while those built on diversified reimbursement, healing "
            "outcomes, and hospital/podiatry referral networks are the more "
            "defensible theses."),
        notable_players=[
            "Healogics", "RestorixHealth", "Vohra Wound Physicians",
            "Wound Care Advantage", "SerenaGroup",
            "Organogenesis / MiMedx (CTP products)", "Integra LifeSciences",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Time-to-heal / healing rate", "outcome KPI",
                "The clinical and payer-value metric — faster, more reliable "
                "healing is the defensible basis for referral and rate."),
            Kpi("Skin-substitute (CTP) utilization & product mix", "the swing "
                "variable",
                "Historically the office margin engine; the exposure that CTP "
                "payment reform directly resets."),
            Kpi("HBOT utilization & documentation compliance", "center-specific",
                "A major wound-center revenue line and the top audit target — "
                "utilization must be clinically defensible and fully documented."),
            Kpi("Revenue per visit / per episode", "model-specific",
                "Differs sharply between HOPD facility-fee, office MPFS, and CTP-"
                "heavy models."),
            Kpi("Referral volume & source mix", "network-driven",
                "Podiatry, vascular, primary care, and hospital-discharge "
                "referrals feed the funnel; concentration is a risk."),
            Kpi("Amputation-prevention / limb-salvage rate", "outcome KPI",
                "The high-value clinical outcome that anchors payer and "
                "health-system partnerships."),
        ],
        margin_profile=(
            "Wound-care unit economics are model-dependent and, for office-based "
            "care, in flux. The hospital-outpatient model earns an OPPS facility "
            "fee plus professional fees and HBOT, shared with the host hospital "
            "under a management arrangement — a steadier but lower-take model. "
            "The office, mobile, and SNF model bills the physician fee schedule, "
            "where the application of high-priced skin substitutes has been the "
            "dominant margin driver; that margin is precisely what CMS payment "
            "reform targets, so a CTP-dependent P&L should be stress-tested "
            "against a reset to bundled or single-rate payment. The durable "
            "economics belong to platforms whose value is healing outcomes, "
            "amputation prevention, and referral density — modalities and "
            "outcomes that survive a change in any single billing code."),
    ),
    risks=[
        Risk("Skin-substitute (CTP) payment reform", "High",
             "CMS-proposed reset away from ASP-based office payment is "
             "potentially existential for CTP-margin-dependent office/mobile "
             "platforms."),
        Risk("OIG/DOJ enforcement exposure", "High",
             "Wound care is among the most-scrutinized services — unnecessary "
             "debridement, HBOT, and CTP schemes carry recoupment and False "
             "Claims Act risk."),
        Risk("HBOT audit / LCD denial risk", "Medium",
             "A major wound-center revenue line governed by MAC coverage "
             "policies and heavy documentation — a recurring denial and audit "
             "target."),
        Risk("Referral concentration / network dependence", "Medium",
             "Volume depends on podiatry, vascular, and hospital referral "
             "relationships that may not transfer or may concentrate risk."),
        Risk("Wound-certified clinician labor supply", "Medium",
             "Scarce wound-certified physicians and nurses cap capacity and the "
             "mobile/SNF rounding model."),
        Risk("Site-of-service payment differentials", "Low",
             "Shifts in office-vs-HOPD payment parity can move where care (and "
             "margin) sits."),
    ],
    diligence_questions=[
        "What share of revenue and margin comes from skin-substitute (CTP) "
        "application, and how does the P&L survive the proposed payment reform?",
        "What is the compliance and enforcement history — any OIG/DOJ inquiries, "
        "settlements, or extrapolated recoupment on debridement/HBOT/CTP?",
        "What is HBOT utilization and documentation quality, and the LCD-denial "
        "history by MAC?",
        "Which model is this — HOPD management, office/mobile roll-up, or SNF "
        "wound physicians — and what is the reimbursement exposure of each?",
        "What are the healing-rate and amputation-prevention outcomes versus "
        "benchmarks, and are they measured credibly?",
        "How concentrated are referral sources, and how durable are the "
        "podiatry/vascular/hospital relationships?",
        "What is the payer mix and the trajectory of MA and commercial wound "
        "coverage policies?",
        "For HOPD arrangements, what are the management-contract terms, host-"
        "hospital splits, and change-of-control provisions?",
    ],
    insider_lens=[
        "The office economics were a skin-substitute arbitrage. ASP-based "
        "payment on high-priced CTPs applied in the non-facility office made "
        "wound care one of the fastest-growing Part B lines — and CMS's proposed "
        "reform is aimed squarely at it. For any office/mobile platform, model "
        "the CTP reset first; it can swing the whole thesis.",
        "There are two businesses under one label. Hospital-outpatient wound-"
        "center management (facility fee + HBOT, shared with the host hospital) "
        "and office/SNF/mobile physician practices (MPFS + CTP) have almost "
        "nothing in common on the P&L — never diligence them as one thing.",
        "Wound care is an enforcement magnet. Unnecessary debridement, HBOT "
        "over-utilization, and skin-substitute schemes have produced a long "
        "string of DOJ actions — the compliance program and audit history are "
        "load-bearing, not boilerplate.",
        "HBOT is a documentation minefield. It is a big revenue line governed by "
        "MAC LCDs and famous for audits — a center that leans on hyperbaric "
        "volume without airtight documentation is carrying a recoupment "
        "liability.",
        "The demand is genuinely durable — diabetes, aging, and vascular disease "
        "guarantee a rising wound burden, and diabetic foot ulcers drive most "
        "non-traumatic amputations. The defensible platforms sell outcomes "
        "(healing, limb salvage) and referral density, not a single billing "
        "code that a rule change can erase.",
    ],
    connections=default_connections(
        "wound_care",
        deals_sector="wound_care",
        extra_pages=[
            ("/diligence/tam-sam?template=wound_care",
             "Wound Care sizing + deal history (deals-only deep-dive)"),
        ],
        connectors=[
            ("cms_open_data_part_b_spending_by_drug",
             "CMS Part B spending by drug — skin-substitute (CTP) spend trend"),
            ("cms_open_data_mup_physician_by_provider_service",
             "CMS physician utilization — debridement / HBOT / CTP by provider"),
            ("open_payments_general_payments_2024",
             "Open Payments — CTP/device manufacturer payments to clinicians"),
            ("cdc_data_diabetes_state_burden",
             "CDC — state diabetes burden (the DFU demand driver)"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
            ("npi_provider",
             "NPI Registry — podiatry / vascular / wound-certified clinicians"),
        ],
    ),
    sources=[
        Source("Nussbaum et al. — 'An Economic Evaluation of the Impact, Cost, "
               "and Medicare Policy Implications of Chronic Nonhealing Wounds' "
               "(Value in Health, 2018)", "ACADEMIC",
               "https://www.valueinhealthjournal.com/article/S1098-3015(17)33790-8/fulltext"),
        Source("CMS Medicare Physician Fee Schedule — annual rule (wound "
               "services + skin-substitute payment proposals)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("MedPAC / CMS — Part B skin-substitute (CTP) spending analyses",
               "GOV", "https://www.medpac.gov/"),
        Source("HHS Office of Inspector General — wound care, hyperbaric, and "
               "skin-substitute enforcement & vulnerability reports", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("CMS Medicare Coverage Database — HBOT and CTP Local Coverage "
               "Determinations", "GOV",
               "https://www.cms.gov/medicare-coverage-database/"),
        Source("PE Desk industry deep-dive (deals-only) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=wound_care"),
    ],
    live_figures=live_figures_from_dive("wound_care"),
    trends=(
        "Wound care spent the last several years defined by one number: the "
        "explosion of Medicare Part B spending on skin substitutes. An average-"
        "sales-price payment loophole made applying high-priced cellular/tissue "
        "products in the physician-office setting extraordinarily profitable, "
        "and utilization surged into the billions of dollars — turning a "
        "clinical modality into a billing phenomenon and drawing intense OIG/DOJ "
        "and MedPAC scrutiny. CMS has now proposed to reset how skin substitutes "
        "are paid, which would reprice the office-based model that much of the "
        "recent roll-up activity was built on. Underneath the reimbursement "
        "drama, the clinical demand is large and structurally growing — diabetes, "
        "obesity, peripheral arterial and venous disease, and aging keep "
        "expanding the chronic-wound burden, and diabetic foot ulcers remain the "
        "leading pathway to non-traumatic amputation. The trajectory therefore "
        "splits by model: the hospital-outpatient management layer is stable but "
        "mature, while the office/mobile/SNF layer is being re-underwritten "
        "around outcomes and diversified reimbursement rather than the skin-"
        "substitute margin that reform is about to reset."),
    growth_levers=[
        GrowthLever(
            "Diabetes + obesity prevalence (the DFU engine)",
            "The master demand driver — rising diabetes and obesity expand the "
            "diabetic-foot-ulcer population, the largest and costliest wound "
            "type.",
            "+demographic demand", "GOV"),
        GrowthLever(
            "Aging + vascular disease (PAD, venous, pressure injuries)",
            "Aging and peripheral arterial/venous disease drive venous ulcers, "
            "arterial ulcers, and pressure injuries in the immobile elderly.",
            "+chronic burden", "GOV"),
        GrowthLever(
            "Advanced-therapy adoption (skin substitutes, NPWT, HBOT)",
            "Higher-intensity modalities raise revenue per episode — but the "
            "skin-substitute component is exactly what payment reform targets.",
            "intensity, at reform risk", "ILLUSTRATIVE"),
        GrowthLever(
            "Amputation-prevention / limb-salvage value",
            "Payers and health systems increasingly reward outcomes that avoid "
            "costly amputations — the durable, model-agnostic value.",
            "outcomes pull", "ILLUSTRATIVE"),
        GrowthLever(
            "Skin-substitute (CTP) payment reform",
            "The CMS-proposed reset away from ASP-based office payment is a "
            "large negative on the office/mobile economics that drove recent "
            "utilization.",
            "−(large) office margin", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Diabetes-and-aging-driven chronic-wound prevalence (diabetic "
               "foot ulcers foremost)",
        analysis=(
            "The dominant demand driver is the prevalence of chronic wounds, "
            "which is anchored in diabetes and aging rather than in a "
            "discretionary utilization choice. Roughly 8.2M Medicare "
            "beneficiaries carry a wound (Nussbaum et al.), and diabetic foot "
            "ulcers — a function of the tens of millions of Americans with "
            "diabetes, of whom a meaningful share develop a foot ulcer in their "
            "lifetime — are the largest, costliest, and most dangerous category, "
            "preceding most non-traumatic lower-limb amputations. Obesity, "
            "peripheral arterial disease, venous insufficiency, and immobility-"
            "related pressure injuries add to a demand base that grows with the "
            "aging, increasingly diabetic population. That makes the underlying "
            "volume curve demographic and durable. The complication is that "
            "reported wound-care spending has grown faster than disease "
            "prevalence because of advanced-therapy (skin-substitute) "
            "intensity — so the honest read separates the genuine, growing "
            "clinical volume from the reimbursement-driven utilization that "
            "payment reform is about to correct."),
        basis="ACADEMIC"),
    cost_drivers=[
        CostDriver(
            "Advanced wound products (skin substitutes / CTPs, dressings)",
            "largest & most variable",
            "The dominant cost and revenue swing in office-based care — high-"
            "priced CTPs; the line that payment reform resets. In the office "
            "model this is a pass-through-plus-margin, not a true net cost.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Clinical labor (wound physicians, NPs, nurses)",
            "~25-35% of cost",
            "Wound-certified clinicians and nurses; scarce specialists cap the "
            "mobile/SNF rounding capacity.", "ILLUSTRATIVE"),
        CostDriver(
            "Hyperbaric & procedure capacity (HOPD)",
            "~10-20% of cost",
            "Hyperbaric chambers and procedure suites in the wound-center model "
            "— a fixed capital and staffing base against HBOT revenue.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Logistics / mobile visit costs",
            "~8-12% of cost",
            "For home and SNF wound care, travel and dispatch costs scale with "
            "geographic density.", "ILLUSTRATIVE"),
        CostDriver(
            "Compliance, documentation & billing overhead",
            "~8-12% of cost",
            "Given the audit and enforcement intensity, documentation, coding, "
            "and compliance are a material, load-bearing overhead.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=None,
)

register(REPORT)
