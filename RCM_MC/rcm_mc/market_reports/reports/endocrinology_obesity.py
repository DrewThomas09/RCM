"""Endocrinology & Obesity — diabetes/metabolic physician practices in the
GLP-1 era.

Deals-only deep-dive (no vendored endocrinology facility file; workforce data
is aggregate-only). Endocrinology is a cognitive, E&M-heavy, ancillary-light,
chronically UNDERSUPPLIED specialty whose whole investment story was rewritten
by GLP-1 anti-obesity drugs and by value-based cardiometabolic/diabetes care.
The qualitative sections are authored around the anti-obesity-drug coverage gap
(Medicare Part D statutory exclusion), the cash-pay vs telehealth obesity
models, the thin in-office ancillary set (DEXA, thyroid ultrasound/FNA, CGM,
CCM/RPM for diabetes), and the workforce shortage that caps organic growth.
Consumes ``endocrinology_obesity_deep_dive()`` for SOURCED corpus figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="endocrinology_obesity",
    name="Endocrinology & Obesity",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices treating diabetes, thyroid, pituitary/adrenal, "
        "bone/osteoporosis, and lipid/metabolic disorders — plus the fast-"
        "growing obesity-medicine segment reshaped by GLP-1 drugs — an E&M-"
        "heavy, ancillary-light, workforce-short cognitive specialty reimbursed "
        "under the Medicare Physician Fee Schedule with a large and volatile "
        "cash-pay obesity overlay."),
    tam_headline=TamHeadline(
        value=306.0, unit="$B", growth_pct=7.0, basis_label="ACADEMIC",
        basis_note=(
            "American Diabetes Association 'Economic Costs of Diabetes in the "
            "U.S. in 2022' (Diabetes Care, 2024) puts DIRECT medical costs at "
            "~$306.60B ($412.90B including lost productivity). That is the "
            "disease-cost anchor, not the physician-services slice, which is a "
            "fraction; growth is the modeled composite of diabetes prevalence, "
            "the GLP-1/obesity-medicine wave, and rate updates."),
    ),
    executive_summary=[
        "Endocrinology is a cognitive, low-margin, ancillary-light specialty — "
        "the opposite of the derm/GI/ortho procedural roll-ups. Revenue is "
        "overwhelmingly evaluation-and-management (E&M) off the Physician Fee "
        "Schedule, with a thin ancillary set (DEXA bone density, thyroid "
        "ultrasound and fine-needle biopsy, CGM interpretation, chronic-care "
        "management). There is no big facility-fee arbitrage to capture.",
        "The specialty is structurally UNDERSUPPLIED. Fellowship fill rates are "
        "weak, a large share of endocrinologists are near retirement, and "
        "demand (diabetes, obesity, thyroid) is exploding — so access is the "
        "binding constraint. That undersupply is a moat for incumbents but caps "
        "organic provider growth and pressures compensation.",
        "GLP-1 drugs (semaglutide, tirzepatide) rewrote the obesity thesis. "
        "Demand is enormous, but the money is in the DRUG and its channel, not "
        "the office visit — and Medicare Part D is statutorily barred from "
        "covering drugs used for weight loss, so obesity medicine runs largely "
        "cash-pay or through telehealth/DTC platforms rather than classic "
        "insurance-billed physician practices.",
        "The durable institutional thesis is value-based cardiometabolic and "
        "diabetes care, not a fee-for-service PPM. Diabetes is the archetypal "
        "chronic-care-management population; payers and CMS reward tighter "
        "control (fewer admissions, slower progression to CKD/ESRD), and "
        "enablement/risk platforms are forming around that — an aligned but "
        "operationally hard bet layered on FFS.",
        "The key risks are payment-structure and drug-policy specific: MPFS "
        "conversion-factor erosion on a fee already low in cognitive specialties, "
        "the unresolved anti-obesity-drug coverage question, the compounded-"
        "GLP-1 crackdown as FDA shortages resolve, and the reputational/quality "
        "risk of low-touch DTC prescribing.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral (PCP/hospital) or self-presentation → endocrinology or "
            "obesity-medicine consult",
            "Diagnostics — labs (A1c, TSH/thyroid panel, lipids, hormone "
            "assays), DEXA, thyroid ultrasound ± fine-needle aspiration",
            "Diagnosis + individualized plan (insulin/oral agents, GLP-1/"
            "incretin therapy, thyroid/adrenal management, weight-loss program)",
            "Longitudinal management — frequent E&M follow-up, medication "
            "titration, continuous glucose monitor (CGM) and pump management",
            "Chronic-care / remote monitoring (CCM, RPM, diabetes coaching, "
            "dietitian/CDCES education)",
            "For obesity — lifestyle program, anti-obesity medication, and "
            "referral for metabolic/bariatric surgery when indicated",
            "Billing — professional E&M (MPFS) + limited in-office technical "
            "fees; obesity often cash-pay or DTC-platform",
        ],
        sites_of_care=[
            "Endocrinology office / clinic (E&M + labs + DEXA + thyroid US/FNA)",
            "Dedicated obesity-medicine / weight-management clinic (often "
            "cash-pay)",
            "Telehealth / DTC obesity platform (GLP-1 prescribing at scale)",
            "Hospital inpatient endocrine consult (inpatient glycemic "
            "management, DKA, thyroid storm) — a referral, not a revenue center",
            "Diabetes education / CDCES program (accredited DSMES)",
        ],
        money_flow=(
            "Endocrinology revenue is dominated by professional evaluation-and-"
            "management fees billed off the Medicare Physician Fee Schedule — "
            "this is a cognitive specialty, so throughput and coding intensity "
            "of complex diabetes and endocrine visits drive the book. The thin "
            "ancillary layer adds bone-density (DEXA) scans, thyroid ultrasound "
            "and fine-needle-aspiration biopsy, in-office point-of-care labs, "
            "and continuous-glucose-monitor and insulin-pump interpretation, "
            "plus chronic-care-management (CCM) and remote-monitoring (RPM) "
            "codes for the diabetes population. Commercial payers pay a multiple "
            "of Medicare. Obesity medicine is the exception to the FFS model: "
            "because Medicare Part D cannot pay for drugs used for weight loss "
            "and commercial coverage of anti-obesity medication is patchy, much "
            "of obesity care is cash-pay — program/membership fees plus the "
            "patient's out-of-pocket drug spend — or delivered through DTC "
            "telehealth platforms that monetize the prescription and the drug "
            "channel more than the visit."),
        key_players=(
            "The independent segment is dominated by hospital-employed "
            "endocrinologists and small independent groups — there is no "
            "national fee-for-service endocrinology PPM at the scale of GI or "
            "ortho, because the ancillary/procedural economics do not support "
            "the classic model. The active capital is on two adjacencies: "
            "value-based/enablement platforms taking risk on diabetes and "
            "cardiometabolic populations, and the obesity/GLP-1 channel — DTC "
            "telehealth (Ro, Hims & Hers, Noom, Found, Calibrate, WeightWatchers/"
            "Sequence) and employer/health-plan obesity programs. Adjacent: "
            "drugmakers (Novo Nordisk, Eli Lilly), CGM/device makers (Dexcom, "
            "Abbott, Insulet, Medtronic Diabetes), and diabetes digital-health "
            "vendors."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US diabetes direct medical cost (2022)", "~$306.60B",
                    "ACADEMIC · ADA, Diabetes Care (2024)"),
            Segment("US diabetes total economic cost incl. productivity",
                    "~$412.90B",
                    "ACADEMIC · ADA, Diabetes Care (2024)"),
            Segment("Adults with diagnosed diabetes (US)", "~38M+",
                    "GOV · CDC National Diabetes Statistics Report"),
            Segment("Adult obesity prevalence (US)", "~40%+ of adults",
                    "GOV · CDC NHANES / BRFSS"),
            Segment("Endocrinology physician-services + obesity-medicine slice",
                    "a fraction of the disease cost",
                    "ILLUSTRATIVE · modeled addressable share"),
        ],
        growth_drivers=[
            "Diabetes + prediabetes prevalence — the demographic/metabolic base",
            "GLP-1 / incretin anti-obesity wave — demand shock across the field",
            "Obesity prevalence ~40%+ of adults — a vast under-treated pool",
            "CGM / pump / digital-diabetes adoption — recurring technical fees",
            "Value-based cardiometabolic and diabetes risk contracts",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.45,
            "Commercial": 0.38,
            "Medicaid / self-pay (incl. cash obesity)": 0.17,
        },
        rate_mechanics=[
            "Medicare Physician Fee Schedule — professional E&M is the core; "
            "endocrinology is a cognitive specialty, so revenue tracks visit "
            "volume and complex-visit coding, not procedures.",
            "In-office technical fees — DEXA bone-density, thyroid ultrasound "
            "and FNA biopsy, and point-of-care labs — a thin ancillary layer "
            "vs procedural specialties.",
            "Chronic-care management (CCM) and remote-monitoring (RPM) codes — "
            "diabetes is the archetypal CCM population; recurring per-month "
            "management revenue when built out.",
            "CGM and insulin-pump management — device supply runs through the "
            "DME/pharmacy benefit; the practice bills interpretation and "
            "training codes.",
            "Anti-obesity medication coverage gap — Medicare Part D is "
            "statutorily prohibited from covering drugs used for weight loss, "
            "so obesity care is largely cash-pay or DTC; GLP-1s ARE covered for "
            "diabetes and (for Wegovy) established cardiovascular-risk "
            "reduction.",
            "Intensive Behavioral Therapy for Obesity (IBT, HCPCS G0447) — "
            "Medicare covers it, but only in the primary-care setting, which "
            "curtails specialist billing of the benefit.",
            "Commercial multiples + prior authorization — commercial pays "
            "MPFS-plus, but GLP-1 and specialty-drug prior-auth and step-therapy "
            "gate access heavily.",
        ],
        reimbursement_risk=(
            "Endocrinology carries the cognitive-specialty squeeze in its purest "
            "form: revenue is professional E&M off a Physician Fee Schedule "
            "whose conversion factor is flat-to-declining in nominal terms while "
            "labor costs rise, and there is little procedural or facility-fee "
            "margin to offset it. The obesity opportunity is real but sits on an "
            "unstable payment base — the Part D statutory exclusion of weight-"
            "loss drugs means the largest demand wave in the specialty's history "
            "does not translate cleanly into insurance-billed physician revenue, "
            "and it pushes care into cash-pay and DTC channels whose durability "
            "depends on drug pricing, coverage-policy reform (the long-pending "
            "Treat and Reduce Obesity Act and CMS coverage proposals), and the "
            "compounded-GLP-1 crackdown as FDA shortages resolve. Layer on GLP-1 "
            "prior-authorization and step-therapy friction, CGM/DME coverage "
            "rules, and the reputational and quality risk of low-touch DTC "
            "prescribing, and the reimbursement picture is a strong demand "
            "signal wrapped around a fragile and policy-sensitive payment "
            "structure."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets the E&M and in-office technical RVUs and the conversion "
                 "factor — the core price of a cognitive specialty's revenue.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Medicare Part D anti-obesity-drug statutory exclusion "
                 "(SSA §1860D-2(e)(2))",
                 "Part D cannot cover drugs used for weight loss — the single "
                 "biggest constraint on monetizing the GLP-1 obesity wave "
                 "through insurance.",
                 "https://www.cms.gov/medicare/coverage/prescription-drug-coverage"),
            Rule("Treat and Reduce Obesity Act (TROA) + CMS AOM coverage "
                 "proposals",
                 "The pending legislative/rulemaking path to Medicare/Medicaid "
                 "coverage of anti-obesity medications — the swing factor for "
                 "the whole obesity business model.",
                 "https://www.congress.gov/"),
            Rule("FDA drug-shortage list + 503A/503B compounding of GLP-1s",
                 "As semaglutide/tirzepatide leave the shortage list, mass "
                 "compounding becomes impermissible — repricing the cheap-"
                 "compounded-GLP-1 telehealth model.",
                 "https://www.accessdata.fda.gov/scripts/drugshortages/"),
            Rule("Corporate practice of medicine + telehealth prescribing "
                 "rules (state boards)",
                 "Govern the DTC obesity platforms' physician arrangements and "
                 "the standard of care for remote GLP-1 prescribing.",
                 None),
            Rule("Stark / Anti-Kickback (in-office ancillary exception)",
                 "Governs self-referral to owned DEXA, ultrasound, and labs and "
                 "any drug/device referral relationships.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
        ],
        policy_watch=[
            "Medicare/Medicaid anti-obesity-drug coverage (TROA + CMS "
            "rulemaking) — the decisive obesity-model variable",
            "MPFS conversion-factor cuts and E&M revaluation (cognitive-"
            "specialty exposure)",
            "FDA shortage resolution and the 503A/503B GLP-1 compounding "
            "crackdown",
            "GLP-1 net pricing, rebates, and IRA drug-price negotiation of "
            "diabetes agents",
            "State medical-board and FTC scrutiny of DTC weight-loss "
            "prescribing quality",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Endocrinology is fragmented among hospital-employed physicians and "
            "small independent groups, with no dominant national fee-for-service "
            "platform — the ancillary-light, cognitive economics never supported "
            "a GI/ortho-style roll-up. The concentration that exists is on the "
            "adjacencies: a handful of scaled value-based kidney/cardiometabolic "
            "and diabetes-enablement companies, and a few large DTC obesity "
            "platforms. The 'acquirable pool' of classic FFS endocrinology is "
            "thin and rarely the thesis on its own."),
        hhi_or_share=(
            "No dominant national owner and no vendored endocrinology facility "
            "file, so operator concentration is honestly not measured here. The "
            "meaningful concentration sits in the obesity-DTC channel and the "
            "diabetes/cardiometabolic value-based platforms, not in office-based "
            "practice ownership."),
        consolidation=(
            "Unlike the procedural specialties, endocrinology has not been rolled "
            "up as a fee-for-service PPM. Capital has instead flowed to (1) "
            "value-based diabetes/cardiometabolic and kidney-adjacent enablement "
            "and risk platforms and (2) the obesity/GLP-1 channel — DTC "
            "telehealth and employer/health-plan weight-management programs. "
            "Where classic practices consolidate, it is usually into "
            "multispecialty groups or health systems for referral capture, not "
            "into a standalone endocrinology platform."),
        pe_activity=(
            "PE/VC interest is high but aimed at the drug channel and value-based "
            "care rather than office-based practice ownership. The obesity wave "
            "drew large DTC and digital-health investment; diabetes/"
            "cardiometabolic risk drew enablement capital. Diligence centers on "
            "channel durability (coverage policy, drug pricing, compounding "
            "crackdown), clinical quality of remote prescribing, and — for the "
            "value-based bets — attribution, risk adjustment, and the ability to "
            "actually change utilization."),
        notable_players=[
            "Ro (obesity/GLP-1 DTC)", "Hims & Hers (weight-loss program)",
            "Noom / Found / Calibrate", "WeightWatchers (Sequence)",
            "Employer & health-plan obesity programs",
            "Diabetes value-based / enablement platforms",
            "Hospital-employed endocrinology groups",
            "CGM & device makers (Dexcom, Abbott, Insulet)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Provider productivity (wRVUs / physician)", "vs MGMA benchmark",
                "A cognitive-specialty book — throughput and complex-visit "
                "coding are the professional-fee engine."),
            Kpi("Ancillary revenue (% of total)", "low (single-digit to ~20%)",
                "DEXA, thyroid US/FNA, labs, CCM/RPM — thin vs procedural "
                "specialties; the structural margin ceiling."),
            Kpi("New-patient access / wait time", "often weeks to months",
                "Undersupply is the binding growth constraint; open access = "
                "captured demand."),
            Kpi("CCM / RPM enrolled diabetes panel", "% of eligible enrolled",
                "Recurring per-member management revenue — the main organic "
                "margin lever in FFS."),
            Kpi("Cash-pay obesity program yield", "membership + drug spend",
                "For obesity medicine, cash program fees and drug-channel "
                "economics, not insurance E&M, drive the P&L."),
            Kpi("Payer mix (commercial vs Medicare)", "commercial lifts blend",
                "Commercial pays a multiple of Medicare, so mix drives realized "
                "yield per visit."),
            Kpi("Platform EBITDA margin", "modest (illustrative)",
                "Thinner than procedural specialties on an FFS book; the obesity "
                "and value-based overlays change the shape entirely."),
        ],
        margin_profile=(
            "The FFS endocrinology margin is thin by construction: revenue is "
            "professional E&M on a low, flat conversion factor with a small "
            "ancillary tail, and the scarce, expensive physician is the whole "
            "engine — so margin is a function of access (filling the schedule), "
            "coding integrity on complex diabetes/endocrine visits, and how much "
            "recurring CCM/RPM management revenue the practice builds on its "
            "diabetes panel. The obesity overlay inverts the shape — cash-pay "
            "program fees and drug-channel economics can be materially more "
            "profitable than insurance-billed visits, but they ride on drug "
            "pricing and coverage policy that can move fast. The value-based "
            "overlay changes it again, trading fee-for-service throughput for "
            "shared savings on avoided admissions and slowed disease "
            "progression."),
    ),
    risks=[
        Risk("Anti-obesity-drug coverage gap (Part D exclusion)", "High",
             "The largest demand wave in the specialty does not convert to "
             "insurance-billed revenue; the whole obesity model rides on "
             "unresolved coverage policy."),
        Risk("MPFS conversion-factor erosion (cognitive-specialty squeeze)",
             "High",
             "A flat professional fee with almost no procedural/facility offset "
             "structurally caps FFS margin."),
        Risk("Compounded-GLP-1 crackdown as FDA shortages resolve", "High",
             "The cheap-compounded-semaglutide DTC model becomes impermissible "
             "as drugs leave the shortage list, repricing that channel."),
        Risk("DTC prescribing quality / reputational & regulatory risk",
             "Medium",
             "Low-touch remote GLP-1 prescribing invites state-board, FTC, and "
             "payer scrutiny and clinical-quality challenge."),
        Risk("Endocrinologist workforce shortage / retention", "Medium",
             "Undersupply both protects incumbents and caps organic growth; "
             "recruiting and comp are decisive."),
        Risk("GLP-1 net pricing, rebates & IRA drug-price negotiation",
             "Medium",
             "Drug-price shifts reshape the cash-pay and coverage math the "
             "obesity model depends on."),
        Risk("Value-based execution risk (attribution / utilization change)",
             "Medium",
             "Diabetes/cardiometabolic risk contracts only pay if the platform "
             "actually changes utilization — operationally hard."),
    ],
    diligence_questions=[
        "What share of revenue is FFS E&M versus ancillary (DEXA/US/labs/CCM) "
        "versus cash-pay obesity — and how policy-sensitive is each?",
        "For the obesity book, what is the mix of cash program fees, insurance-"
        "billed visits, and drug-channel economics, and how exposed is it to "
        "coverage/compounding policy?",
        "How is any DTC prescribing structured against state medical-board and "
        "corporate-practice rules, and what is the clinical-quality posture?",
        "What is the CCM/RPM penetration of the diabetes panel and its "
        "recurring revenue trend?",
        "What is provider access/wait time, and how much projected growth "
        "assumes hiring into a workforce-short specialty?",
        "What value-based diabetes/cardiometabolic contracts exist, and what is "
        "the attribution, risk-adjustment, and savings track record?",
        "What is the payer mix and commercial-rate position, and how exposed is "
        "the book to GLP-1 prior-auth and step-therapy?",
        "How concentrated is revenue in a few physicians, and what are their "
        "retention and compensation terms?",
    ],
    insider_lens=[
        "The GLP-1 boom is a drug-channel story, not an office-visit story. The "
        "demand is historic, but Medicare cannot pay for weight-loss drugs and "
        "commercial coverage is patchy — so the money sits in the prescription "
        "and the cash-pay channel, which is why the winners look like DTC "
        "telehealth and pharma, not endocrinology PPMs.",
        "Endocrinology is the specialty PE keeps looking at and passing on. "
        "It's cognitive and ancillary-light, so there's no facility-fee or "
        "procedure arbitrage to underwrite a classic roll-up — the real "
        "institutional bet is value-based diabetes/cardiometabolic care, which "
        "is a different (and harder) business.",
        "Undersupply is the quiet moat. Fellowship fill is weak and the "
        "workforce is aging while diabetes and obesity explode, so access is "
        "the constraint — an endocrinology asset's value is often just its "
        "captured, un-fillable demand, but that same shortage means you cannot "
        "grow it by hiring.",
        "Watch the compounding cliff. A large slice of the low-price GLP-1 "
        "telehealth volume rode the FDA shortage that let pharmacies compound "
        "semaglutide/tirzepatide; as those drugs leave the shortage list, that "
        "channel's unit economics reset — underwrite the post-shortage world, "
        "not the shortage-era run-rate.",
        "Diabetes is the best CCM/RPM population in medicine, and it's under-"
        "monetized in most practices. The organic margin lever in FFS "
        "endocrinology is enrolling the diabetes panel into chronic-care and "
        "remote-monitoring management — recurring revenue hiding in plain sight.",
    ],
    connections=default_connections(
        "endocrinology_obesity",
        deals_sector="endocrinology",
        extra_pages=[
            ("/industry/endocrinology_obesity",
             "Industry deep-dive — endocrinology & obesity deal history + "
             "structure"),
        ],
        connectors=[
            ("cms_open_data_mup_partd_prescriber_by_provider_drug",
             "Medicare Part D prescribing — GLP-1/insulin/thyroid drug volume "
             "by provider"),
            ("cms_open_data_part_d_spending_by_drug",
             "Part D spending by drug — Ozempic/Wegovy/Mounjaro spend & trend"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — E&M, DEXA, thyroid US/FNA "
             "service volume"),
            ("cdc_data_places_county",
             "CDC PLACES — county diabetes & obesity prevalence for demand "
             "mapping"),
            ("open_payments_general_payments_2024",
             "Open Payments — Novo/Lilly & device-maker payments to "
             "endocrinologists"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — endocrinology & obesity-medicine workforce supply"),
        ],
    ),
    sources=[
        Source("American Diabetes Association — Economic Costs of Diabetes in "
               "the U.S. in 2022 (Diabetes Care, 2024)", "ACADEMIC",
               "https://diabetesjournals.org/care"),
        Source("CDC — National Diabetes Statistics Report", "GOV",
               "https://www.cdc.gov/diabetes/php/data-research/"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "conversion factor)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("CMS — Medicare Part D coverage rules and anti-obesity-drug "
               "exclusion guidance", "GOV",
               "https://www.cms.gov/medicare/coverage/prescription-drug-coverage"),
        Source("FDA — Drug Shortages database (semaglutide/tirzepatide status)",
               "GOV", "https://www.accessdata.fda.gov/scripts/drugshortages/"),
        Source("Endocrine Society / American Association of Clinical "
               "Endocrinology — workforce and practice data", "INDUSTRY",
               "https://www.endocrine.org/"),
        Source("PE Desk industry deep-dive (endocrinology & obesity) + "
               "realized-deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=endocrinology_obesity"),
    ],
    live_figures=live_figures_from_dive("endocrinology_obesity"),
    trends=(
        "Endocrinology spent two decades as a quiet, undersupplied cognitive "
        "specialty that private equity admired and avoided — the ancillary-"
        "light economics never supported a fee-for-service roll-up the way "
        "in-office procedures and imaging did for GI, ortho, and derm. Two "
        "forces changed the conversation. First, GLP-1/incretin anti-obesity "
        "drugs turned obesity medicine into the fastest-growing demand story in "
        "healthcare — but because Medicare Part D is statutorily barred from "
        "covering weight-loss drugs and commercial coverage is patchy, the value "
        "accrued to the drug and its channel (DTC telehealth, cash-pay programs, "
        "and pharma) rather than to insurance-billed endocrinology practices. "
        "Second, value-based cardiometabolic and diabetes care matured: diabetes "
        "is the archetypal chronic-care population, and payers and CMS built "
        "risk and enablement models that reward tighter control and slower "
        "progression to kidney and cardiovascular disease. The forward tensions "
        "are all policy and pricing — whether Medicare/Medicaid ever cover anti-"
        "obesity drugs (TROA and CMS rulemaking), how the compounded-GLP-1 "
        "crackdown reshapes DTC as shortages resolve, and how GLP-1 net pricing "
        "and IRA negotiation move the cash-pay math — set against a relentless "
        "diabetes/obesity prevalence tailwind and a workforce that cannot grow "
        "fast enough to serve it."),
    growth_levers=[
        GrowthLever(
            "GLP-1 / incretin anti-obesity wave",
            "A historic demand shock — but monetized mainly through the drug "
            "channel and cash-pay/DTC programs, not insurance-billed visits.",
            "primary demand shock", "ILLUSTRATIVE"),
        GrowthLever(
            "Diabetes & prediabetes prevalence",
            "An aging, increasingly obese population expands the diabetes and "
            "metabolic patient base — the durable E&M and CCM engine.",
            "+ mid-single %/yr", "GOV"),
        GrowthLever(
            "CCM / RPM on the diabetes panel",
            "Enrolling the chronic-diabetes population into recurring chronic-"
            "care and remote-monitoring management — the main FFS margin lever.",
            "+ recurring", "ILLUSTRATIVE"),
        GrowthLever(
            "Value-based cardiometabolic / diabetes risk",
            "Shared savings and management fees for controlling high-cost "
            "diabetes and cardiometabolic populations — a second revenue engine.",
            "+ VBC", "ILLUSTRATIVE"),
        GrowthLever(
            "Anti-obesity-drug coverage reform",
            "If Medicare/Medicaid and commercial plans broadly cover AOMs, "
            "obesity medicine could shift from cash-pay toward billable "
            "physician revenue — a step-change, currently unresolved.",
            "policy optionality", "ILLUSTRATIVE"),
        GrowthLever(
            "MPFS conversion-factor / coverage drag",
            "A flat professional fee and the Part D weight-loss exclusion are "
            "the structural headwinds capping FFS conversion of demand.",
            "policy risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Diabetes + obesity prevalence × the GLP-1 treatment wave",
        analysis=(
            "The demand base is the intersection of two epidemics — diabetes "
            "(more than 38 million diagnosed US adults and rising) and obesity "
            "(over 40% of adults) — layered with a treatment revolution in "
            "GLP-1/incretin drugs that has, for the first time, put highly "
            "effective pharmacotherapy at the center of obesity care. That "
            "creates enormous, still-largely-untreated demand for metabolic "
            "management. The catch is that demand does not flow evenly into "
            "physician-services revenue: diabetes generates billable E&M, "
            "ancillary, and CCM/RPM volume, while obesity's GLP-1 demand is "
            "throttled by the Medicare Part D weight-loss exclusion and patchy "
            "commercial coverage, diverting it into cash-pay and DTC channels. "
            "Compounding the mismatch, the endocrinology workforce is "
            "structurally short, so access — not underlying demand — is the "
            "binding constraint on how much of the wave any given practice can "
            "actually serve."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician & advanced-practice clinical labor",
            "~45-55% of cost",
            "The scarce, expensive cognitive core; in an undersupplied "
            "specialty, recruiting and retention are the dominant cost and "
            "constraint.", "ILLUSTRATIVE"),
        CostDriver(
            "Support staff, diabetes educators (CDCES) & dietitians",
            "~15-20% of cost",
            "The care-team overhead behind education, CCM/RPM, and program "
            "delivery — expands with value-based and obesity programs.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Drug / pharmacy acquisition (cash-pay & buy-and-bill)",
            "varies by model",
            "For cash-pay obesity and any buy-and-bill therapy, drug "
            "acquisition can be the single largest line — a channel cost, not a "
            "traditional practice cost.", "ILLUSTRATIVE"),
        CostDriver(
            "G&A, billing, prior-auth & patient acquisition",
            "~12-18% of cost",
            "Heavy GLP-1/specialty prior-authorization workload; DTC models "
            "additionally carry large marketing/customer-acquisition cost.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Ancillary equipment (DEXA, ultrasound, POC labs)",
            "~5-10% of cost",
            "The modest capital chassis behind the thin ancillary layer plus "
            "CGM/pump support infrastructure.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No vendored endocrinology facility file exists — an endocrinology or "
        "obesity practice is a physician office, not a Medicare-certified "
        "facility — so state geography is omitted rather than fabricated. "
        "Qualitatively, the footprint is shaped less by facility regulation than "
        "by (1) the endocrinologist workforce shortage, which is acute in rural "
        "and many Southern/Mountain states where diabetes and obesity "
        "prevalence is highest — a demand/supply mismatch the DTC obesity "
        "platforms exist to arbitrage — and (2) state Medicaid and commercial "
        "coverage of anti-obesity medication and telehealth prescribing rules, "
        "which vary widely and directly gate the obesity business model. The CDC "
        "PLACES county prevalence connector and the Medicare Part D prescriber "
        "and physician-utilization connectors linked below map diabetes/obesity "
        "burden and GLP-1/endocrine service volume by geography — the honest "
        "footprint read for where demand and undersupply are most severe."),
)

register(REPORT)
