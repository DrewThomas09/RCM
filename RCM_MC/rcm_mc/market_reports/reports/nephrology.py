"""Nephrology — kidney-care physician practices (the value-based-kidney thesis).

Deals-only deep-dive (no vendored nephrology facility file; ASN workforce data
is aggregate-only). Nephrology's economics are unlike any other physician
specialty: revenue is anchored to dialysis via the Monthly Capitation Payment
(MCP), nephrologists commonly hold dialysis-facility joint-venture stakes and
medical-director agreements, and the dominant investment story is value-based
kidney care — CMS's Kidney Care Choices models and the risk/enablement platforms
(Somatus, Strive, Interwell, Monogram, Evergreen) built to slow CKD progression,
push home dialysis, and increase transplant. The qualitative sections are
authored around the MCP, the dialysis JV/Stark structure, the ETC/KCC models,
and the home-dialysis mandate. Consumes ``nephrology_deep_dive()`` for SOURCED
corpus figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="nephrology",
    name="Nephrology",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices managing kidney disease — chronic kidney disease "
        "(CKD), end-stage renal disease (ESRD/dialysis), transplant, "
        "hypertension, and electrolyte/glomerular disorders — whose revenue is "
        "uniquely anchored to dialysis via the Monthly Capitation Payment, "
        "dialysis-facility joint ventures, and, increasingly, value-based "
        "kidney-care risk contracts under CMS's Kidney Care Choices models."),
    tam_headline=TamHeadline(
        value=130.0, unit="$B", growth_pct=5.0, basis_label="GOV",
        basis_note=(
            "USRDS / CMS put Medicare fee-for-service spending on CKD at ~$85B "
            "and on ESRD at ~$50B (2021, ~$130B+ combined) — the kidney-disease "
            "cost pool the specialty and its value-based models sit on top of, "
            "not the nephrology physician-services slice, which is a fraction. "
            "Growth is the modeled composite of CKD/ESRD prevalence, home-"
            "dialysis mix shift, and rate updates, net of SGLT2/GLP-1-driven "
            "slowing of ESRD incidence."),
    ),
    executive_summary=[
        "Nephrology's revenue is anchored to dialysis, not the office. The "
        "signature mechanic is the Monthly Capitation Payment (MCP) — a per-"
        "patient-per-month fee for managing a dialysis patient, tiered by the "
        "number of face-to-face visits — so a nephrologist's book scales with "
        "the dialysis census, and the specialty's economics are tied to the "
        "dialysis chairs it covers.",
        "Dialysis joint ventures and medical directorships are a second, "
        "structural income stream. Nephrologists commonly co-own dialysis "
        "facilities in JVs with DaVita/Fresenius and hold paid medical-director "
        "agreements — legal under a specific dialysis exception/safe harbor, but "
        "Stark/AKS-sensitive and a first-order diligence item on any nephrology "
        "asset.",
        "The real investment thesis is value-based kidney care, not a fee-for-"
        "service PPM. CMS's Kidney Care Choices (KCC) models and the mandatory "
        "ESRD Treatment Choices (ETC) model let nephrology groups and enablement "
        "platforms take risk on CKD/ESRD populations — the money is in slowing "
        "progression, increasing HOME dialysis and transplant, and cutting "
        "hospitalizations, which is where the enablement companies raised "
        "billions.",
        "Home dialysis and transplant are policy tailwinds with teeth. The 2019 "
        "Advancing American Kidney Health push and the ETC model reward home "
        "modalities and transplant and penalize lagging providers — reshaping "
        "modality mix, which is exactly the lever value-based platforms pull.",
        "The risks are structure- and policy-specific: dialysis JV/Stark "
        "exposure, MCP and dialysis-bundle (ESRD PPS) rate policy, the "
        "execution risk of value-based contracts (attribution, risk adjustment, "
        "actually changing utilization), and the clinical shift as SGLT2 "
        "inhibitors and GLP-1s slow CKD progression and, at the margin, ESRD "
        "incidence.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "CKD identification (labs/eGFR, often via PCP/endocrinology/cardiology "
            "referral) → nephrology consult",
            "CKD management — slow progression (BP/glycemic control, SGLT2/"
            "RAAS therapy), modality education, vascular-access planning",
            "ESRD transition — dialysis initiation (in-center vs HOME) or "
            "transplant referral/listing",
            "Dialysis oversight — Monthly Capitation Payment management, rounding, "
            "medical direction of the facility",
            "Transplant — evaluation, listing, and post-transplant co-management",
            "Value-based overlay — KCC/ETC risk, care navigation, hospitalization "
            "avoidance, home-modality growth",
            "Billing — MCP + E&M + JV facility income + medical-director fees + "
            "value-based shared savings/capitation",
        ],
        sites_of_care=[
            "Nephrology office / clinic (CKD management + E&M)",
            "Dialysis facility (in-center hemodialysis — where MCP and JV income "
            "concentrate)",
            "Patient home (home hemodialysis / peritoneal dialysis — the "
            "policy-favored, growing modality)",
            "Hospital inpatient (AKI, ICU dialysis, inpatient consults)",
            "Transplant center (evaluation, listing, post-transplant care)",
        ],
        money_flow=(
            "Nephrology stacks four income streams around the kidney patient. "
            "First, the Monthly Capitation Payment (MCP): Medicare pays the "
            "nephrologist a per-patient-per-month fee for managing a dialysis "
            "patient, tiered by the number of monthly face-to-face visits (with "
            "separate home-dialysis MCP codes) — the census-driven core of the "
            "book. Second, office E&M for CKD, hypertension, and pre-dialysis "
            "management off the Physician Fee Schedule. Third, dialysis-facility "
            "economics: many nephrologists co-own dialysis units in joint "
            "ventures with the national chains and hold paid medical-director "
            "agreements, so facility profit and directorship fees flow to the "
            "physician-owners under a specific regulatory structure. Fourth, and "
            "increasingly central, value-based contracts: under CMS's Kidney "
            "Care Choices models (and via enablement/risk platforms), groups "
            "earn capitation and shared savings for slowing CKD progression, "
            "shifting patients to home dialysis and transplant, and cutting "
            "hospitalizations. The dialysis treatment itself is paid to the "
            "facility under the ESRD Prospective Payment System bundle — a "
            "separate flow the nephrologist influences but does not bill."),
        key_players=(
            "The independent segment is fragmented among nephrology groups tied "
            "to local dialysis JVs, alongside hospital-employed nephrologists. "
            "The defining capital, though, sits in value-based kidney enablement "
            "and risk platforms — Somatus, Strive Health, Interwell Health "
            "(Fresenius + Cricket + InterWell), Monogram Health, and Evergreen "
            "Nephrology (Rubicon/CVS) — which partner with nephrology groups to "
            "take population risk. On the dialysis side, the DaVita/Fresenius "
            "duopoly runs the facilities the specialty orbits. Adjacent: "
            "transplant centers, home-dialysis-device makers (Fresenius/NxStage, "
            "Baxter, Outset), and the drugmakers (SGLT2/GLP-1, anemia agents) "
            "reshaping CKD progression."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicare FFS spending on CKD (2021)", "~$85.00B",
                    "GOV · USRDS Annual Data Report / CMS"),
            Segment("Medicare FFS spending on ESRD (2021)", "~$50.00B",
                    "GOV · USRDS Annual Data Report / CMS"),
            Segment("US ESRD (dialysis + transplant) patients", "~800K+",
                    "GOV · USRDS prevalence"),
            Segment("US adults with chronic kidney disease", "~35M+ (~1 in 7)",
                    "GOV · CDC CKD surveillance"),
            Segment("Home-dialysis modality share", "growing under ETC/AAKH",
                    "GOV · CMS ESRD / USRDS modality data"),
        ],
        growth_drivers=[
            "CKD/ESRD prevalence — driven by diabetes, hypertension, aging",
            "Value-based kidney care (KCC/ETC) — the capital and margin engine",
            "Home-dialysis + transplant shift — policy-favored modality mix",
            "CKD identification upstream — earlier nephrology engagement",
            "SGLT2/GLP-1 slowing progression — a partial offset to ESRD "
            "incidence",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.70,
            "Commercial": 0.18,
            "Medicaid / other": 0.12,
        },
        rate_mechanics=[
            "Monthly Capitation Payment (MCP) — a per-patient-per-month fee for "
            "managing a dialysis patient, tiered by monthly face-to-face visits, "
            "with distinct codes for home dialysis — the census-driven core of "
            "nephrology revenue.",
            "Medicare Physician Fee Schedule E&M — CKD, hypertension, and "
            "pre-dialysis office management plus inpatient/AKI consults.",
            "Dialysis-facility economics (ESRD PPS bundle) — the treatment is "
            "paid to the FACILITY under a per-treatment bundle; nephrologist-"
            "owners share facility profit via the JV, not a physician claim.",
            "Medical-director agreements — paid facility medical-direction fees, "
            "fair-market-value and safe-harbor-sensitive.",
            "Value-based kidney contracts (KCC: KCF and CKCC options) — "
            "capitation, care-management fees, and shared savings for managing "
            "CKD/ESRD populations, home-modality growth, and transplant.",
            "ESRD Treatment Choices (ETC) model — mandatory in selected regions; "
            "adjusts payment up or down based on home-dialysis and transplant "
            "rates.",
            "Commercial + MA — commercial pays multiples of Medicare; MA "
            "enrollment of ESRD patients (post-21st Century Cures) reshaped "
            "payer mix and value-based opportunity.",
        ],
        reimbursement_risk=(
            "Nephrology's reimbursement risk is concentrated in its unusual "
            "structure. The MCP and the dialysis JV both depend on the dialysis "
            "census and on the ESRD payment regime staying favorable — so ESRD "
            "PPS bundle updates, any change to the MCP tiers, and MA rate policy "
            "for ESRD enrollees move the core economics. The JV and medical-"
            "director income is legal but sits squarely in Stark/AKS territory: "
            "a misvalued directorship or a non-compliant ownership structure is "
            "an existential compliance risk, and it is the first thing a buyer "
            "must confirm. The value-based overlay carries execution risk — "
            "capitation and shared savings only pay if the platform actually "
            "changes utilization (progression, modality, hospitalizations), and "
            "attribution and risk adjustment can swing results. Finally, the "
            "clinical base is shifting: SGLT2 inhibitors and GLP-1s slow CKD "
            "progression and, at the margin, ESRD incidence — good for patients "
            "and for value-based models, but a long-run headwind to the dialysis-"
            "census economics the traditional book relies on. The offset is a "
            "large, aging, diabetic/hypertensive CKD pipeline."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("ESRD Prospective Payment System (ESRD PPS bundle) — annual "
                 "Final Rule",
                 "Sets the per-treatment dialysis bundle paid to the facility — "
                 "the payment regime the whole specialty orbits.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/end-stage-renal-disease-esrd"),
            Rule("Monthly Capitation Payment (MCP) — Physician Fee Schedule ESRD "
                 "codes",
                 "The tiered per-patient-per-month dialysis-management fee — the "
                 "census-driven core of nephrology physician revenue.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Kidney Care Choices (KCC) models — CMS Innovation Center",
                 "The voluntary value-based kidney models (KCF/CKCC) that let "
                 "nephrology groups and platforms take population risk — the "
                 "investment engine.",
                 "https://www.cms.gov/priorities/innovation/innovation-models/kidney-care-choices-kcc-model"),
            Rule("ESRD Treatment Choices (ETC) model — mandatory regions",
                 "Adjusts payment up/down on home-dialysis and transplant "
                 "rates — the policy lever reshaping modality mix.",
                 "https://www.cms.gov/priorities/innovation/innovation-models/esrd-treatment-choices-model"),
            Rule("Physician self-referral (Stark) + AKS dialysis JV / "
                 "medical-director safe harbors",
                 "Governs nephrologist ownership of dialysis facilities and paid "
                 "directorships — the compliance spine of the specialty's "
                 "economics.",
                 "https://oig.hhs.gov/compliance/safe-harbor-regulations/"),
            Rule("21st Century Cures Act — MA enrollment for ESRD",
                 "Opened Medicare Advantage to ESRD patients (2021), reshaping "
                 "payer mix and the value-based opportunity.",
                 "https://www.congress.gov/"),
        ],
        policy_watch=[
            "ESRD PPS bundle updates and any expansion (e.g. oral-drug/"
            "transitional add-on) that shift facility economics",
            "KCC model continuation/redesign and CKCC risk-track economics",
            "ETC model home-dialysis/transplant benchmarks and payment "
            "adjustments",
            "Stark/AKS enforcement on dialysis JVs and medical-director "
            "arrangements",
            "SGLT2/GLP-1 uptake slowing CKD progression and ESRD incidence "
            "(long-run census effect)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Nephrology practice is fragmented among local groups organized "
            "around their dialysis joint ventures, plus hospital-employed "
            "nephrologists. But the competitively decisive layer is not practice "
            "ownership — it is the dialysis duopoly (DaVita/Fresenius) that runs "
            "the facilities and the value-based kidney platforms (Somatus, "
            "Strive, Interwell, Monogram, Evergreen) assembling nephrology "
            "networks to take population risk."),
        hhi_or_share=(
            "No vendored nephrology facility file, so operator concentration in "
            "the physician layer is honestly not measured here. The meaningful "
            "concentration is downstream: the DaVita/Fresenius dialysis duopoly "
            "controls the bulk of US dialysis stations, and a handful of value-"
            "based kidney platforms hold the enablement/risk market."),
        consolidation=(
            "Unlike derm/GI/ortho, nephrology was not rolled up as a fee-for-"
            "service PPM — its economics are tied to dialysis and to value-based "
            "care, so the consolidation ran through (1) the dialysis duopoly's "
            "JV footprint and (2) the value-based kidney platforms that raised "
            "large private capital to partner with nephrology groups. Those "
            "platforms centralize care management, home-modality growth, and "
            "risk-contract infrastructure rather than simply buying practices."),
        pe_activity=(
            "PE/VC activity is dominated by value-based kidney enablement and "
            "risk — one of the most heavily-funded specialty value-based themes, "
            "with billions raised across Somatus, Strive, Interwell, Monogram, "
            "and Evergreen. Diligence centers on the dialysis JV/Stark structure, "
            "the durability and design of the KCC/CKCC and MA risk contracts, "
            "attribution and risk-adjustment mechanics, home-modality execution, "
            "and the long-run effect of progression-slowing drugs on the "
            "dialysis pipeline."),
        notable_players=[
            "Somatus", "Strive Health", "Interwell Health (Fresenius/Cricket)",
            "Monogram Health", "Evergreen Nephrology (Rubicon/CVS)",
            "DaVita & Fresenius (dialysis duopoly / JVs)",
            "Hospital-employed nephrology groups",
            "Home-dialysis device makers (NxStage, Baxter, Outset)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Dialysis census under management (MCP patients)",
                "patients / nephrologist",
                "The census-driven core — MCP revenue scales with the dialysis "
                "patients a physician manages."),
            Kpi("Dialysis JV facility income (% of physician comp)", "material",
                "Facility profit share and medical-director fees can rival or "
                "exceed clinical income — and carry the Stark/AKS exposure."),
            Kpi("Home-dialysis modality share", "% on home HD/PD",
                "The ETC and value-based lever — higher home share improves "
                "quality metrics and model payments."),
            Kpi("Value-based lives + shared-savings yield",
                "PMPM / savings per attributed life",
                "For the value-based book, attributed CKD/ESRD lives and "
                "realized savings are the P&L, not FFS visits."),
            Kpi("Hospitalization rate of managed population",
                "admissions / 1,000",
                "The primary utilization lever value-based kidney care is paid "
                "to reduce."),
            Kpi("Transplant referral / listing rate", "% of eligible",
                "A quality and model-payment driver — and a long-run reducer of "
                "dialysis census."),
            Kpi("Platform economics (FFS vs risk)", "shifting to risk",
                "The margin shape depends on the FFS/JV vs value-based mix — two "
                "very different businesses."),
        ],
        margin_profile=(
            "Traditional nephrology margin is a blend of MCP census revenue, "
            "office E&M, and — often the largest and most sensitive piece — "
            "dialysis-JV facility income and medical-director fees. That mix is "
            "attractive but structurally tied to the dialysis census and to a "
            "Stark/AKS-sensitive ownership arrangement that must be pristine. "
            "The value-based overlay changes the margin shape entirely: it "
            "trades fee-for-service throughput for capitation and shared savings "
            "on attributed CKD/ESRD lives, where the P&L is driven by slowing "
            "progression, growing home dialysis and transplant, and cutting "
            "hospitalizations — high potential margin if the platform can "
            "actually move utilization, but with real execution, attribution, "
            "and risk-adjustment variance. The long-run tension is clinical: the "
            "same progression-slowing drugs that help the value-based models "
            "erode the dialysis-census base the traditional economics depend "
            "on."),
    ),
    risks=[
        Risk("Dialysis JV / medical-director Stark & AKS exposure", "High",
             "Nephrologist ownership of dialysis facilities and paid "
             "directorships are legal but compliance-critical; a misstructured "
             "arrangement is an existential risk."),
        Risk("ESRD PPS bundle & MCP rate policy", "High",
             "The dialysis payment regime and the tiered MCP anchor the "
             "economics; adverse updates hit the core book."),
        Risk("Value-based execution risk (attribution / utilization change)",
             "High",
             "KCC/CKCC and MA risk only pay if the platform slows progression "
             "and cuts hospitalizations — operationally hard and variance-"
             "heavy."),
        Risk("Dialysis-census erosion from progression-slowing drugs", "Medium",
             "SGLT2/GLP-1 uptake slows CKD progression and ESRD incidence — good "
             "clinically, a long-run headwind to census economics."),
        Risk("MA-for-ESRD payer-mix & rate shifts", "Medium",
             "The post-Cures MA shift reshapes payer mix and risk economics for "
             "ESRD populations."),
        Risk("KCC/ETC model continuation & redesign risk", "Medium",
             "The value-based thesis depends on CMS models persisting and "
             "keeping workable risk-track economics."),
        Risk("Nephrologist workforce shortage / retention", "Medium",
             "Weak fellowship fill and an aging workforce constrain growth and "
             "make key physicians decisive."),
    ],
    diligence_questions=[
        "How is the dialysis JV and medical-director structure documented, "
        "fair-market-valued, and safe-harbor-compliant — and what share of "
        "economics does it represent?",
        "What is the dialysis census under MCP management, its modality mix "
        "(in-center vs home), and its trend?",
        "What value-based contracts (KCC/CKCC, MA, commercial) exist — attributed "
        "lives, risk track, PMPM, and shared-savings track record?",
        "What are the managed population's hospitalization rate, home-dialysis "
        "share, and transplant-referral rate versus benchmark?",
        "How exposed is the book to ESRD PPS bundle and MCP rate policy, and to "
        "the MA-for-ESRD shift?",
        "What is the long-run dialysis-census outlook given SGLT2/GLP-1 uptake "
        "and progression slowing?",
        "How concentrated is revenue in a few nephrologists and in specific "
        "dialysis JVs, and what are retention terms?",
        "What is the split between the traditional FFS/JV book and the value-"
        "based book, and how is each valued?",
    ],
    insider_lens=[
        "Nephrology is a dialysis business wearing a physician-practice costume. "
        "The Monthly Capitation Payment, the JV facility income, and the medical-"
        "director fees all key off the dialysis census — so you are really "
        "underwriting the chairs the group covers, not its office visits, and "
        "the DaVita/Fresenius relationship behind them.",
        "The joint venture is the whole compliance story. Nephrologist ownership "
        "of dialysis facilities and paid directorships is legal under a specific "
        "structure, but it lives in Stark/AKS territory — a buyer's first job is "
        "to confirm every JV and directorship is fair-market-valued and safe-"
        "harbor-clean, because a bad one is existential, not a footnote.",
        "The real money moved to value-based care, and it's a different company. "
        "The billions raised in kidney care went to enablement/risk platforms "
        "(Somatus, Strive, Interwell, Monogram, Evergreen) that get paid to slow "
        "progression, grow HOME dialysis, and cut admissions — a population-risk "
        "business, not a fee-for-service roll-up, with its own attribution and "
        "execution risk.",
        "Home dialysis is where policy and profit align. The ETC model and the "
        "value-based contracts both reward home modalities and transplant — the "
        "operators who can actually shift modality mix capture the model "
        "payments, while lagging providers get penalized.",
        "The best drugs for the patient are a slow headwind to the old model. "
        "SGLT2 inhibitors and GLP-1s delay CKD progression and dampen ESRD "
        "incidence — a tailwind for value-based kidney care but a long-run "
        "erosion of the dialysis-census economics the traditional MCP/JV book is "
        "built on. Underwrite which side of that shift the asset sits on.",
    ],
    connections=default_connections(
        "nephrology",
        deals_sector="nephrology",
        extra_pages=[
            ("/industry/nephrology",
             "Industry deep-dive — nephrology deal history + structure"),
            ("/market/dialysis",
             "Adjacent market report — Dialysis (the facilities nephrology "
             "orbits)"),
        ],
        connectors=[
            ("provider_data_dialysis_facilities",
             "CMS Dialysis Facility Compare — the facilities behind MCP/JV "
             "economics"),
            ("cms_open_data_esrd_agg_group_performance",
             "CMS ESRD / KCC aggregate group performance — value-based kidney "
             "read"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — MCP/dialysis-management service "
             "volume"),
            ("cdc_data_places_county_ckd",
             "CDC PLACES — county chronic-kidney-disease prevalence for demand "
             "mapping"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — nephrology workforce supply & enrollment"),
            ("open_payments_ownership_payments_2024",
             "Open Payments — physician ownership & investment (dialysis JV "
             "screen)"),
        ],
    ),
    sources=[
        Source("USRDS — Annual Data Report (CKD & ESRD prevalence, Medicare "
               "spending)", "GOV", "https://usrds-adr.niddk.nih.gov/"),
        Source("CMS — End-Stage Renal Disease Prospective Payment System (ESRD "
               "PPS) annual Final Rule", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/end-stage-renal-disease-esrd"),
        Source("CMS Innovation Center — Kidney Care Choices (KCC) and ESRD "
               "Treatment Choices (ETC) models", "GOV",
               "https://www.cms.gov/priorities/innovation/innovation-models/kidney-care-choices-kcc-model"),
        Source("CDC — Chronic Kidney Disease surveillance", "GOV",
               "https://www.cdc.gov/kidney-disease/php/data-research/"),
        Source("HHS OIG — safe-harbor regulations (dialysis JV / medical "
               "director)", "GOV",
               "https://oig.hhs.gov/compliance/safe-harbor-regulations/"),
        Source("American Society of Nephrology — workforce and policy data",
               "INDUSTRY", "https://www.asn-online.org/"),
        Source("PE Desk industry deep-dive (nephrology) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=nephrology"),
    ],
    live_figures=live_figures_from_dive("nephrology"),
    trends=(
        "Nephrology's trajectory is unlike the procedural physician specialties "
        "because its economics were never really about the office. For decades "
        "the specialty's income keyed off dialysis — the Monthly Capitation "
        "Payment for managing dialysis patients, plus joint-venture ownership of "
        "dialysis facilities and paid medical-director agreements with the "
        "DaVita/Fresenius duopoly. Two forces then reshaped it. First, policy "
        "pushed hard toward home dialysis and transplant: the 2019 Advancing "
        "American Kidney Health initiative and the mandatory ESRD Treatment "
        "Choices model reward home modalities and penalize laggards. Second, and "
        "decisively, value-based kidney care arrived with real capital — CMS's "
        "Kidney Care Choices models let nephrology groups and enablement "
        "platforms take population risk, and Somatus, Strive, Interwell, "
        "Monogram, and Evergreen raised billions to slow CKD progression, grow "
        "home dialysis, and cut hospitalizations. The forward tensions are "
        "structural and clinical: the durability of the CMS models and their "
        "risk economics, continued Stark/AKS scrutiny of dialysis JVs, and a "
        "genuine clinical shift as SGLT2 inhibitors and GLP-1s slow progression "
        "and, at the margin, ESRD incidence — a tailwind for value-based models "
        "but a slow erosion of the dialysis-census base the traditional book "
        "relies on."),
    growth_levers=[
        GrowthLever(
            "Value-based kidney care (KCC/CKCC + MA risk)",
            "Capitation and shared savings for slowing progression, growing home "
            "dialysis/transplant, and cutting admissions — the funded engine.",
            "primary thesis", "GOV"),
        GrowthLever(
            "CKD/ESRD prevalence (diabetes, hypertension, aging)",
            "A large, aging, diabetic/hypertensive population feeds the CKD-to-"
            "ESRD pipeline the specialty manages.",
            "+ mid-single %/yr", "GOV"),
        GrowthLever(
            "Home-dialysis + transplant modality shift",
            "ETC and value-based incentives push home modalities and transplant, "
            "improving model payments for operators who can execute.",
            "+ modality mix", "GOV"),
        GrowthLever(
            "Upstream CKD identification",
            "Earlier nephrology engagement (via labs/PCP/endo/cardio referral) "
            "expands the managed population before dialysis.",
            "+ earlier engagement", "ILLUSTRATIVE"),
        GrowthLever(
            "MCP / dialysis-JV census base",
            "The traditional per-patient-per-month management fee and facility "
            "income scale with the covered dialysis census.",
            "census-linked", "GOV"),
        GrowthLever(
            "Progression-slowing drugs (SGLT2/GLP-1) — long-run offset",
            "Better CKD control helps value-based models but slows ESRD "
            "incidence — a headwind to the dialysis-census economics.",
            "−long-run census", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="CKD-to-ESRD pipeline × the value-based-care shift",
        analysis=(
            "The demand base is chronic kidney disease — roughly 1 in 7 US "
            "adults (35 million-plus), driven by diabetes, hypertension, and "
            "aging — feeding a large ESRD population (800,000-plus on dialysis "
            "or with a transplant) that carries enormous Medicare cost. "
            "Traditionally, volume growth meant more dialysis patients under "
            "management, monetized through the Monthly Capitation Payment and "
            "dialysis-facility joint ventures. The structural shift is that the "
            "value creation is moving upstream and toward risk: value-based "
            "kidney models pay to identify CKD earlier, slow its progression, "
            "shift ESRD patients to home dialysis and transplant, and cut "
            "hospitalizations — so the growth engine is now attributed lives and "
            "realized savings, not just dialysis census. The important offset is "
            "clinical: SGLT2 inhibitors and GLP-1s are beginning to slow "
            "progression and dampen ESRD incidence, which helps the value-based "
            "models but, over a long horizon, softens the dialysis-census base "
            "the traditional economics depend on."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician & advanced-practice clinical labor",
            "~40-50% of cost",
            "Nephrologists and APPs covering clinic, dialysis rounds, and "
            "inpatient consults — the scarce core of an undersupplied "
            "specialty.", "ILLUSTRATIVE"),
        CostDriver(
            "Care-management & navigation team (value-based)",
            "large in risk models",
            "The nurses, care managers, and social workers that make value-based "
            "kidney care work — the cost of actually changing utilization.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Medical claims / total cost of care (risk-bearing)",
            "the risk pool",
            "In capitated/CKCC arrangements, the attributed population's medical "
            "spend IS the cost base — hospitalizations and dialysis dominate "
            "it.", "ILLUSTRATIVE"),
        CostDriver(
            "Dialysis-facility operating cost (JV side)",
            "facility-level",
            "For the JV economics, the dialysis unit's labor, supplies, and "
            "capital — shared with the chain partner.", "ILLUSTRATIVE"),
        CostDriver(
            "G&A, data/analytics, compliance & risk infrastructure",
            "~10-15% of cost",
            "Risk-contract analytics, attribution/risk-adjustment tooling, and "
            "the heavy Stark/AKS compliance overhead on JVs.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No vendored nephrology facility file exists — a nephrology group is a "
        "physician practice, not a Medicare-certified facility — so state "
        "geography for the physician layer is omitted rather than fabricated. "
        "The honest geographic read is the DIALYSIS footprint the specialty "
        "orbits: the vendored CMS Dialysis Facility Compare file (see the "
        "adjacent Dialysis market report and the dialysis-facilities connector) "
        "carries real per-state facility counts, ownership, and the DaVita/"
        "Fresenius chain concentration that shapes nephrology JV economics. "
        "Qualitatively, kidney disease burden concentrates in the Southeast and "
        "in diabetic/hypertensive populations, and the ETC model's mandatory "
        "regions and the value-based platforms' network footprints determine "
        "where the risk-bearing opportunity is live. The CDC PLACES CKD "
        "prevalence connector and the ESRD group-performance connector linked "
        "below map disease burden and value-based performance by geography."),
)

register(REPORT)
