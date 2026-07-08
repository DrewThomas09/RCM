"""Podiatry — foot & ankle care (DPM) roll-up.

Deals-only deep-dive (no national physician-practice facility file; geography is
omitted rather than fabricated). Podiatry is an early-innings, highly fragmented
specialty roll-up whose economics split three ways: low-acuity routine foot care
(Medicare, documentation-audit-prone), foot & ankle surgery (the ASC/ancillary
upside), and diabetic wound care (the high-dollar, high-risk skin-substitute
business now under a CMS payment overhaul and OIG enforcement). The qualitative
sections are authored around that three-way split, the diabetes demand driver,
the value-based limb-salvage thesis, and the small-practice consolidation
challenge. Consumes ``podiatry_deep_dive()`` for SOURCED corpus deal figures
(none realized in the corpus yet — the report leans on authored substance).
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="podiatry",
    name="Podiatry",
    care_setting="Physician services",
    naics="621391",
    one_line_def=(
        "Physician practices (Doctors of Podiatric Medicine) treating the foot "
        "and ankle — routine/at-risk foot care, diabetic wound care, foot & "
        "ankle surgery, and orthotics/DME — a Medicare-heavy, documentation-heavy "
        "specialty whose economics turn on the case mix among routine care, "
        "surgery, and the high-dollar skin-substitute wound business."),
    tam_headline=TamHeadline(
        value=5.5, unit="$B", growth_pct=4.5, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~18,000-20,000 practicing US podiatrists (APMA "
            "workforce) times the professional fee plus the surgical, DME/"
            "orthotics, and wound-care/skin-substitute ancillaries — not a single "
            "published figure. Growth is the modeled composite of "
            "diabetes-driven volume and ancillary capture, net of a "
            "skin-substitute reimbursement overhaul."),
    ),
    executive_summary=[
        "Podiatry's economics split three ways, and the mix is the risk profile: "
        "low-acuity routine/at-risk foot care (Medicare, documentation-audit-"
        "prone), foot & ankle surgery (the ASC and ancillary upside), and "
        "diabetic wound care (the high-dollar, high-risk skin-substitute "
        "business). Read the mix before the P&L.",
        "Skin substitutes are the elephant. Cellular/tissue products billed "
        "buy-and-bill at ASP have produced eye-watering per-application dollars "
        "and are now the top OIG/DOJ wound-care enforcement target — with CMS "
        "moving to package the payment. A practice whose EBITDA leans on them is "
        "buying a reimbursement cliff.",
        "Diabetes is the demand engine. Roughly 38 million Americans have "
        "diabetes, driving neuropathy, at-risk foot care, ulcers, and the "
        "amputation-prevention work that is podiatry's core non-discretionary "
        "volume.",
        "The value-based angle is real and specific: a diabetic foot ulcer that "
        "becomes an amputation costs the system enormously, so podiatry-led limb "
        "salvage is one of the few specialties with a clean prevention-savings "
        "story for risk contracts (the Upperline thesis).",
        "Consolidation is early innings. Podiatry is highly fragmented with a "
        "small average practice size (many solo and 2-3 DPM offices), so a "
        "platform stitches together many tiny practices — more integration "
        "friction and back-office lift per dollar of EBITDA than a derm or GI "
        "roll-up.",
        "It is Medicare-heavy and documentation-heavy: routine foot care is "
        "covered only with a qualifying systemic condition and the right "
        "class-finding modifiers, so coding discipline and audit defense are core "
        "operating capabilities, not overhead.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral / self-referral (diabetic foot exam, pain, injury, wound)",
            "Office E&M visit + risk stratification (LOPS / at-risk classing)",
            "Routine/at-risk care — nail & callus debridement, preventive exams",
            "Diabetic wound care — debridement, dressings, skin substitutes",
            "Surgery — bunion/hammertoe, fracture, reconstruction (office/ASC)",
            "DME dispensing — therapeutic diabetic shoes, custom orthotics, AFOs",
            "Charge capture, modifier/coverage coding, and collections",
        ],
        sites_of_care=[
            "Physician office / clinic (E&M, routine care, in-office procedures)",
            "Wound-care clinic (diabetic ulcers, debridement, skin substitutes)",
            "Ambulatory surgery center / HOPD (foot & ankle surgery)",
            "Skilled nursing facility / house calls (at-risk foot care rounds)",
            "In-office DME dispensary (diabetic shoes, orthotics, bracing)",
        ],
        money_flow=(
            "A podiatrist earns a professional fee off the Medicare Physician Fee "
            "Schedule for office E&M and procedures — but Medicare covers routine "
            "foot care (nail/callus debridement) only when a qualifying systemic "
            "condition (diabetes/peripheral vascular disease with loss of "
            "protective sensation) is documented with the correct class-finding "
            "modifiers. Around that base sit the ancillaries that carry the "
            "economics: foot & ankle surgery bills an ASC/HOPD facility fee; "
            "diabetic wound care applies cellular/tissue skin substitutes billed "
            "buy-and-bill at ASP (historically very high per-application dollars); "
            "and DME — therapeutic diabetic shoes and custom orthotics — is "
            "dispensed under supplier standards. In a PE structure the payer pays "
            "the physician-owned PC, which pays the MSO a management fee for the "
            "wound program, surgery, DME, billing, and shared services. Because "
            "the specialty is Medicare-heavy and coverage is documentation-gated, "
            "coding discipline is itself a revenue and compliance function."),
        key_players=(
            "Consolidation is early-stage and led by a handful of emerging "
            "platforms — Upperline Health (value-based specialty/podiatry with a "
            "diabetic-limb-salvage thesis) and US Foot & Ankle Specialists "
            "(USFAS) among the most visible — alongside regional podiatry MSOs. "
            "Wound-care management companies and skin-substitute manufacturers "
            "sit upstream and shape the highest-revenue, highest-risk line. The "
            "acquirable pool is the vast independent long tail of small podiatry "
            "practices — the whitespace and the integration challenge at once."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US podiatrists (DPM)", "~18,000-20,000",
                    "INDUSTRY · APMA workforce estimates (directional)"),
            Segment("US adults with diagnosed diabetes", "~38M",
                    "GOV · CDC National Diabetes Statistics Report"),
            Segment("US diabetic foot ulcers (annual)", "millions of cases / yr",
                    "ACADEMIC · diabetic-foot epidemiology literature "
                    "(directional)"),
            Segment("Average podiatry practice size", "small (many solo/2-3 DPM)",
                    "INDUSTRY · APMA practice profile (directional)"),
            Segment("Skin-substitute (CTP) Part B spending", "high-growth, "
                    "under CMS payment review",
                    "GOV · CMS Part B / OIG wound-care spending analyses"),
        ],
        growth_drivers=[
            "Diabetes prevalence + aging — at-risk foot care, ulcers, salvage",
            "Foot & ankle surgery + ASC migration — the facility-fee ancillary",
            "DME/orthotics (diabetic shoes, custom orthotics) — a captured line",
            "Value-based limb-salvage / diabetic-foot risk contracting",
            "Skin-substitute reimbursement overhaul — a structural rate wildcard",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.45,
            "Commercial": 0.33,
            "Medicaid": 0.12,
            "Self-pay / other": 0.10,
        },
        rate_mechanics=[
            "MPFS professional fees for E&M and procedures, with routine foot "
            "care (nail debridement 11720/11721, callus 11055-11057) covered "
            "only for qualifying systemic conditions (diabetes/PVD with loss of "
            "protective sensation) documented with Q7/Q8/Q9 class-finding "
            "modifiers.",
            "Diabetic wound care + cellular/tissue skin substitutes (CTPs) — Part "
            "B buy-and-bill at ASP, historically very high-dollar per application; "
            "CMS is moving to package/bundle skin-substitute payment and OIG is "
            "enforcing aggressively (the biggest reimbursement wildcard).",
            "ASC / hospital-outpatient facility fee for foot & ankle surgery — "
            "the surgical ancillary, with cases migrating toward the ASC.",
            "DME ancillary — therapeutic diabetic shoes/inserts (A5500 series) "
            "and custom orthotics/AFOs, dispensed under DMEPOS supplier standards "
            "and documentation rules.",
            "Commercial multiples of Medicare, plus workers'-compensation fee "
            "schedules for injury cases.",
            "Value-based / limb-salvage risk contracts — emerging arrangements "
            "paying for diabetic-amputation prevention (shared savings on avoided "
            "amputations and hospitalizations).",
        ],
        reimbursement_risk=(
            "Two exposures dominate. First, skin substitutes: the buy-and-bill "
            "CTP business has produced outsized per-application revenue and is now "
            "the top OIG/DOJ wound-care enforcement target, with CMS proposing to "
            "package or bundle the payment — a change that could reprice a "
            "wound-heavy practice's revenue overnight, so any EBITDA leaning on "
            "CTPs must be underwritten as a wildcard, not a run-rate. Second, "
            "routine-foot-care coverage: Medicare pays for nail and callus "
            "debridement only with a qualifying systemic condition and the right "
            "class-finding modifiers, making documentation the difference between "
            "a clean claim and a recoupment — routine foot care is a perennial "
            "audit target. On top sit the usual MPFS conversion-factor drift and "
            "DME documentation scrutiny."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare routine-foot-care coverage rules (systemic-condition "
                 "exception + Q modifiers)",
                 "Routine foot care is generally excluded except for qualifying "
                 "systemic disease with the correct class-finding modifiers — the "
                 "perennial documentation-audit target.",
                 "https://www.cms.gov/medicare-coverage-database/"),
            Rule("Skin-substitute / cellular-tissue-product (CTP) payment policy",
                 "CMS is moving to package/bundle skin-substitute payment; the "
                 "change reprices the highest-revenue, highest-risk wound line.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("OIG / DOJ wound-care and skin-substitute enforcement",
                 "Skin substitutes are a top wound-care fraud target; enforcement "
                 "and False Claims Act exposure make wound-program compliance a "
                 "diligence gate.",
                 "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
            Rule("DMEPOS supplier standards + therapeutic-shoe documentation",
                 "Diabetic shoes and custom orthotics are dispensed under "
                 "supplier standards and documentation rules with their own audit "
                 "exposure.",
                 "https://www.cms.gov/medicare/enrollment-renewal/providers-suppliers/dmepos"),
            Rule("Anti-Kickback Statute / Stark on DME & wound-product "
                 "arrangements",
                 "Governs relationships with skin-substitute manufacturers and "
                 "DME suppliers; FMV and referral integrity are diligence gates.",
                 "https://oig.hhs.gov/compliance/safe-harbor-regulations/"),
            Rule("State podiatric scope-of-practice + CPOM doctrine",
                 "State law defines podiatric scope (foot-only vs ankle/lower "
                 "leg), a licensure variable; corporate-practice rules shape the "
                 "friendly-PA/MSO structure.",
                 None),
        ],
        policy_watch=[
            "CMS skin-substitute payment overhaul (packaging/bundling) — the "
            "biggest ancillary reprice",
            "Continued OIG/DOJ wound-care and routine-foot-care enforcement",
            "Value-based diabetic-limb-preservation contracting expansion",
            "Annual MPFS conversion-factor cuts",
            "State scope-of-practice expansion (ankle/rearfoot surgery)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Podiatry is among the most fragmented physician specialties, with a "
            "small average practice size — many solo and 2-3 DPM offices — and no "
            "dominant national consolidator. That fragmentation is both the "
            "whitespace and the challenge: a platform assembles many tiny "
            "practices, each with modest EBITDA, so integration and back-office "
            "lift per dollar are heavier than in derm or GI."),
        hhi_or_share=(
            "No single owner is remotely dominant nationally; the market is a "
            "long tail of small practices. No vendored physician-practice roll "
            "captures operator concentration, so a chain HHI is honestly omitted "
            "— the sector deal history is thin and the report leans on authored "
            "substance."),
        consolidation=(
            "Consolidation is early innings relative to derm/GI/ortho. The leading "
            "thesis pairs specialty-specific buy-and-build with a value-based "
            "diabetic-foot/limb-salvage angle — Upperline Health is the archetype, "
            "with US Foot & Ankle Specialists and regional MSOs also active. The "
            "operating model captures surgery, DME, and (carefully) wound-care "
            "ancillaries while managing the routine-foot-care documentation risk "
            "and the skin-substitute reimbursement wildcard."),
        pe_activity=(
            "A nascent but rising PE thesis. The differentiated version is "
            "value-based limb preservation — using podiatry to prevent costly "
            "diabetic amputations and hospitalizations and sharing in the "
            "savings — rather than pure fee-for-service ancillary capture. "
            "Diligence centers on the skin-substitute exposure, routine-care "
            "documentation, small-practice integration, and DPM recruiting into a "
            "small training pipeline."),
        notable_players=[
            "Upperline Health (value-based limb salvage)",
            "US Foot & Ankle Specialists (USFAS)",
            "Regional podiatry MSOs", "Independent single/small-group DPMs",
            "Wound-care management companies (upstream)",
            "Skin-substitute manufacturers (upstream)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Encounters / DPM / yr", "high-volume, low-acuity skew",
                "Routine and at-risk foot care drives visit volume; surgery and "
                "wound care carry the higher yield."),
            Kpi("Case-mix split (routine / surgical / wound)",
                "the risk-profile tell",
                "The three-way mix determines both margin and reimbursement risk "
                "exposure before the P&L does."),
            Kpi("Skin-substitute revenue (% of total)", "concentration risk",
                "High CTP dependence is high reimbursement-cliff exposure under "
                "the CMS packaging overhaul and OIG enforcement."),
            Kpi("DME / orthotics ancillary revenue", "documentation-gated",
                "Diabetic shoes and custom orthotics — a captured line with its "
                "own supplier-standard audit exposure."),
            Kpi("Payer mix (Medicare share)", "~45%+ Medicare/MA",
                "A Medicare-heavy, coverage-gated book where documentation "
                "discipline protects revenue."),
            Kpi("Platform EBITDA margin (post-MSO)", "12-18% (illustrative)",
                "Small-practice fragmentation and back-office lift temper margins "
                "versus ancillary-rich specialties."),
        ],
        margin_profile=(
            "Podiatry margin is a function of case mix and compliance. Routine and "
            "at-risk foot care is high-volume, low-acuity, Medicare-heavy work "
            "whose margin depends on clean documentation of the qualifying "
            "systemic condition — a coding discipline, not a growth lever. Foot & "
            "ankle surgery and its ASC facility fee, plus DME/orthotics, add "
            "ancillary margin. Diabetic wound care with skin substitutes can be "
            "the largest revenue line and the largest risk, because the "
            "buy-and-bill CTP economics are precisely what CMS is repricing and "
            "OIG is enforcing. Because the average practice is small, the MSO "
            "back-office lift per dollar of EBITDA is heavier than in "
            "ancillary-rich specialties, so scale economics and integration "
            "discipline — plus the value-based limb-salvage upside — are what make "
            "the roll-up math work."),
    ),
    risks=[
        Risk("Skin-substitute / CTP reimbursement crackdown (CMS + OIG)", "High",
             "CMS payment packaging plus OIG/DOJ enforcement can reprice a "
             "wound-heavy practice's largest revenue line overnight — the biggest "
             "wildcard."),
        Risk("Routine-foot-care coverage & documentation audits", "Medium",
             "Medicare covers routine care only with a qualifying systemic "
             "condition and the right modifiers; weak documentation drives "
             "recoupment."),
        Risk("Small practice size / integration & scalability", "Medium",
             "A long tail of tiny practices means heavy per-dollar back-office "
             "lift and integration friction."),
        Risk("Physician retention / comp model", "Medium",
             "Selling DPMs are the revenue; alignment and the post-close comp "
             "model drive retention, as in any specialty roll-up."),
        Risk("DPM workforce supply (small training pipeline)", "Medium",
             "A limited podiatric-school pipeline constrains de novo and "
             "add-on staffing."),
        Risk("MPFS conversion-factor erosion", "Medium",
             "A structural, no-inflation-update squeeze on the professional fee."),
    ],
    diligence_questions=[
        "What is the case-mix split among routine/at-risk care, surgery, and "
        "wound care, and what does it imply for margin and risk?",
        "What share of revenue and EBITDA is skin-substitute (CTP) buy-and-bill, "
        "and how exposed is it to the CMS packaging overhaul and OIG enforcement?",
        "How clean is the routine-foot-care documentation (qualifying-condition "
        "and class-finding modifiers), and what is the audit/recoupment history?",
        "What is the surgical volume and ASC/facility strategy, and the "
        "DME/orthotics ancillary program and its supplier-standard compliance?",
        "Is there a value-based limb-salvage / diabetic-foot risk book, and how "
        "credible are the savings and quality claims?",
        "How small and how numerous are the constituent practices, and what is "
        "the realistic integration and back-office cost per dollar of EBITDA?",
        "What is the payer mix (Medicare share), and how durable are the top "
        "commercial and workers'-comp contracts?",
        "What is the DPM recruiting and retention plan given the small training "
        "pipeline, and the post-close compensation model?",
    ],
    insider_lens=[
        "Read the case mix before the P&L. Podiatry splits into routine/at-risk "
        "foot care (Medicare, documentation-audit-prone), surgery (the ASC and "
        "ancillary upside), and diabetic wound care (high-dollar, high-risk skin "
        "substitutes) — the mix tells you the risk profile faster than the "
        "financials do.",
        "Skin substitutes are the elephant. Cellular/tissue products billed at "
        "ASP have produced eye-watering per-application dollars and are now the "
        "top OIG/DOJ wound-care target, with CMS moving to package the payment. A "
        "practice whose EBITDA leans on CTPs is buying a reimbursement cliff — "
        "underwrite it as a wildcard, not a run-rate.",
        "The value-based angle is genuinely differentiated. A diabetic foot ulcer "
        "that becomes an amputation costs the system enormously, so podiatry-led "
        "limb salvage is one of the few specialties with a clean "
        "prevention-savings story for risk contracts — the Upperline thesis.",
        "This is a Medicare-heavy, documentation-heavy specialty. Routine foot "
        "care is only covered with a qualifying systemic condition and the right "
        "class-finding modifiers, so coding discipline and audit defense are a "
        "core operating capability, not overhead.",
        "Consolidation is early innings for a structural reason: the average "
        "practice is tiny. A platform stitches together many solo and 2-3 DPM "
        "offices, so the back-office lift and integration friction per dollar of "
        "EBITDA are heavier than in a derm or GI roll-up.",
        "DME is a quiet, rules-heavy ancillary. Diabetic shoes and custom "
        "orthotics carry their own supplier standards and documentation "
        "requirements — a real margin line that draws its own audit attention.",
    ],
    connections=default_connections(
        "podiatry",
        deals_sector="podiatry",
        extra_pages=[
            ("/industry/podiatry",
             "Industry deep-dive — podiatry deal history + foot-&-ankle read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — podiatry (DPM) specialty mix & practice enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — podiatry service & allowed charges"),
            ("cms_open_data_part_b_spending_by_drug",
             "Medicare Part B spending — skin-substitute (CTP) read"),
            ("cms_open_data_mup_dme_by_supplier_service",
             "Medicare DMEPOS — diabetic-shoe & orthotics supplier read"),
            ("open_payments_general_payments_2024",
             "Open Payments — wound-product & device payments to podiatrists"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA age & diabetes-proxy demographics for demand"),
        ],
    ),
    sources=[
        Source("CDC — National Diabetes Statistics Report (diabetes "
               "prevalence)", "GOV",
               "https://www.cdc.gov/diabetes/php/data-research/"),
        Source("CMS — Medicare Coverage Database (routine foot care coverage "
               "rules)", "GOV",
               "https://www.cms.gov/medicare-coverage-database/"),
        Source("CMS — Medicare Physician Fee Schedule + skin-substitute (CTP) "
               "payment policy", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("OIG — wound-care and skin-substitute program-integrity / "
               "enforcement reports", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("American Podiatric Medical Association (APMA) — workforce and "
               "practice data", "INDUSTRY",
               "https://www.apma.org/"),
        Source("Peer-reviewed diabetic-foot literature — ulcer incidence and "
               "amputation-prevention economics", "ACADEMIC",
               "https://diabetesjournals.org/"),
        Source("PE Desk industry deep-dive (podiatry) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=podiatry"),
    ],
    live_figures=live_figures_from_dive("podiatry"),
    trends=(
        "Podiatry is an early-innings specialty roll-up whose economics split "
        "three ways — routine/at-risk foot care, foot & ankle surgery, and "
        "diabetic wound care — and whose trajectory is set by two forces. The "
        "demand engine is diabetes: roughly 38 million Americans have it, driving "
        "neuropathy, at-risk foot care, ulcers, and the amputation-prevention "
        "work that is podiatry's non-discretionary core. The reimbursement story "
        "is the skin substitute: cellular/tissue products billed buy-and-bill at "
        "ASP produced outsized per-application dollars, made wound care the "
        "highest-revenue and highest-risk line, and are now the top OIG/DOJ "
        "wound-care enforcement target with CMS moving to package the payment. "
        "Against that backdrop, the differentiated PE thesis is value-based limb "
        "salvage — Upperline-style diabetic-foot risk contracting that shares in "
        "the savings from prevented amputations — layered on a fragmented base of "
        "very small practices. Consolidation lags derm, GI, and ortho precisely "
        "because average practice size is small, so integration discipline and "
        "the skin-substitute and routine-care documentation risks, not multiple "
        "arbitrage, are the center of the thesis."),
    growth_levers=[
        GrowthLever(
            "Diabetes-driven at-risk & wound volume",
            "Rising diabetes prevalence and aging expand neuropathy, at-risk "
            "foot care, ulcers, and amputation-prevention demand.",
            "primary / + structural volume", "GOV"),
        GrowthLever(
            "Foot & ankle surgery + ASC migration",
            "Capture the facility fee by moving surgical cases into an owned or "
            "JV ambulatory surgery center.",
            "+ facility-fee capture", "ILLUSTRATIVE"),
        GrowthLever(
            "DME / orthotics ancillary",
            "Own the diabetic-shoe and custom-orthotics dispensing the podiatrist "
            "already generates — a captured, documentation-gated line.",
            "+ ancillary margin", "ILLUSTRATIVE"),
        GrowthLever(
            "Value-based limb-salvage contracting",
            "Share in savings from prevented diabetic amputations and "
            "hospitalizations — the differentiated risk-based upside.",
            "risk-based upside", "ILLUSTRATIVE"),
        GrowthLever(
            "Consolidation of a fragmented base",
            "Roll up a long tail of small practices; the challenge is heavy "
            "per-dollar integration lift, not deal supply.",
            "supporting", "ILLUSTRATIVE"),
        GrowthLever(
            "Skin-substitute repricing",
            "The CMS packaging overhaul plus MPFS drift is the structural rate "
            "wildcard/headwind on the highest-revenue line.",
            "rate wildcard", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Diabetes prevalence (neuropathy, at-risk foot care, ulcers)",
        analysis=(
            "The dominant demand driver is diabetes. Roughly 38 million Americans "
            "have diagnosed diabetes, and a large additional population is "
            "prediabetic; diabetic peripheral neuropathy and vascular disease "
            "drive loss of protective sensation, at-risk foot care, foot ulcers, "
            "and — at the severe end — amputation. That demand is "
            "non-discretionary and demographic: it grows with diabetes prevalence "
            "and aging, and it is precisely the coverage-qualifying population for "
            "Medicare routine and wound foot care. It is also the basis of the "
            "value-based thesis, because a diabetic foot ulcer that progresses to "
            "amputation is one of the costliest and most preventable events in "
            "the system, giving podiatry-led limb salvage a clean "
            "prevention-savings story. The credible long-run offset is better "
            "diabetes control (including GLP-1 adoption), which could slow "
            "complication rates — but slowly, over more than a typical hold."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Podiatrist & advanced-practice compensation", "~40-50% of cost",
            "The dominant cost; the post-close comp and alignment model is the "
            "biggest margin lever and retention risk.", "ILLUSTRATIVE"),
        CostDriver(
            "Skin-substitute / wound-product COGS (buy-and-bill)",
            "variable / large gross for wound-heavy practices",
            "The cost side of the highest-revenue, highest-risk line — the CTP "
            "acquisition cost against an ASP payment CMS is repricing.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Clinical & office staff (MAs, wound techs, front office)",
            "~15-20% of cost",
            "The labor running high-volume routine care, wound clinics, and "
            "surgery scheduling.", "ILLUSTRATIVE"),
        CostDriver(
            "DME COGS + facility / occupancy", "~10% of cost",
            "Diabetic-shoe and orthotics acquisition plus clinic and any "
            "surgery-suite real estate.", "ILLUSTRATIVE"),
        CostDriver(
            "MSO back office (billing/RCM, coding, compliance)",
            "~10-15% of cost",
            "Heavier per dollar than ancillary-rich specialties because the base "
            "is many small practices with documentation-intensive coverage.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-practice facility file is vendored — a podiatry "
        "practice is a business, not a Medicare-certified facility — so state "
        "geography is omitted rather than fabricated. The most consequential "
        "geographic variables are state podiatric scope-of-practice law (which "
        "sets whether a DPM can perform ankle/rearfoot surgery and therefore the "
        "surgical ancillary opportunity), the corporate-practice-of-medicine "
        "doctrine that shapes the MSO structure, and local diabetes prevalence "
        "and Medicare Advantage penetration that drive the at-risk and wound "
        "demand. The NPI-taxonomy, Medicare physician-utilization, Part B "
        "skin-substitute, DMEPOS, and demographic connectors linked below map "
        "podiatry supply and diabetic-foot demand — the honest footprint read."),
)

register(REPORT)
