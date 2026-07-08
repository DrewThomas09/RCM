"""Behavioral Health — outpatient mental-health + substance-use treatment.

Deals-only deep-dive (CMS publishes no single national behavioral-health
facility roll, so geography is omitted rather than fabricated; the honest live
layer is the sector's own realized-deal corpus). Consumes
``behavioral_health_deep_dive()`` for SOURCED corpus figures. The qualitative
sections are authored around the two economic engines that actually decide
these deals — clinician labor (the binding constraint) and payer mix (a
Medicaid-heavy safety net vs. a commercial/cash outpatient book) — plus the
parity regime, the CCBHC Medicaid unlock, and the SUD program-integrity legacy.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="behavioral_health",
    name="Behavioral Health",
    care_setting="Behavioral",
    naics="621330",
    one_line_def=(
        "Treatment of mental-health and substance-use disorders across a "
        "continuum — outpatient therapy and medication management, intensive "
        "outpatient (IOP) and partial hospitalization (PHP), residential and "
        "inpatient psychiatric care, opioid-treatment programs, and community "
        "mental-health centers — paid by a fragmented braid of commercial, "
        "Medicaid, Medicare, self-pay, and grant dollars under mental-health "
        "parity."),
    tam_headline=TamHeadline(
        value=280.0, unit="$B", growth_pct=5.0, basis_label="GOV",
        basis_note=(
            "SAMHSA's spending-accounts projection put combined mental-health "
            "and substance-use treatment spending near $280B by 2020 (all "
            "payers, all settings); growth here is the modeled composite of "
            "prevalence/help-seeking (+3.0%), parity + coverage expansion "
            "(+2.0%), telehealth-led access (+1.5%), and rate/labor "
            "pressure (−1.5%)."),
    ),
    executive_summary=[
        "The business is a labor business. Revenue is clinician hours billed, "
        "so the binding constraint is recruiting, credentialing, and retaining "
        "therapists and prescribers — and clinician compensation is the single "
        "largest cost line (roughly half to two-thirds of revenue). A platform "
        "lives or dies on productivity (billable sessions/week), no-show rate, "
        "and clinician churn, not on demand — demand is effectively infinite.",
        "Payer mix defines the whole risk profile. The sickest populations "
        "(serious mental illness, SUD) are Medicaid-funded at thin, "
        "state-set rates; the margin sits in the commercial and cash-pay "
        "outpatient book, where ghost networks and out-of-network billing are "
        "the reality despite parity. A mixed platform is really two businesses.",
        "Mental-health parity (MHPAEA) is strong in statute and weak in "
        "enforcement — the gap between what parity requires and what payers "
        "actually authorize is where utilization-review denials, single-case "
        "agreements, and reimbursement risk live.",
        "CCBHCs are the Medicaid margin unlock. The Certified Community "
        "Behavioral Health Clinic model pays a cost-based prospective daily/"
        "monthly rate instead of fee-for-service piece-work — turning a "
        "chronically underwater safety-net model into a fundable one, and the "
        "demonstration is expanding to every state.",
        "The vertical is extremely fragmented and heavily PE-penetrated across "
        "three distinct plays — outpatient therapy roll-ups, addiction/SUD "
        "residential, and digital-therapy marketplaces — but the 2017-2021 "
        "boom has repriced as labor cost, payer rate cuts, and integration "
        "friction separated the platforms that scaled from the ones that broke.",
        "Telehealth reset the access curve. Behavioral health is the single "
        "largest telehealth category and the flexibilities (including DEA "
        "tele-prescribing of controlled substances) are the swing regulatory "
        "variable for the digital and hybrid models.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Access / intake — referral, screening (PHQ-9/GAD-7), triage to "
            "the right level of care",
            "Eligibility + benefit verification + payer credentialing "
            "(the bottleneck to billing a new clinician)",
            "Assessment / diagnostic evaluation (90791/90792) and treatment "
            "planning",
            "Treatment delivery — psychotherapy, medication management, group/"
            "IOP/PHP, MAT, or residential milieu",
            "Care coordination + measurement-based care (repeat PHQ-9/GAD-7) "
            "and step-up/step-down across levels",
            "Utilization review + prior authorization (the payer gate on "
            "higher levels of care)",
            "Billing — CPT psychotherapy/E&M/per-diem/bundle; denials, appeals, "
            "and out-of-network / single-case agreements",
        ],
        sites_of_care=[
            "Outpatient office / group practice (therapy + med management — the "
            "volume base and the commercial/cash margin pool)",
            "Telehealth / hybrid (the largest telehealth category)",
            "Intensive outpatient (IOP) and partial hospitalization (PHP)",
            "Residential treatment (SUD and mental health — commercial per-diem)",
            "Inpatient psychiatric hospital / unit (acute; IMD-exclusion limited "
            "for adult Medicaid)",
            "Community mental-health center / CCBHC (safety-net, Medicaid PPS)",
            "Opioid-treatment program (OTP — methadone/buprenorphine, weekly "
            "Medicare bundle)",
        ],
        money_flow=(
            "Outpatient behavioral health is billed as clinician time: "
            "psychotherapy CPT codes (90837 for ~60 minutes, 90834 for ~45, "
            "90791 for the intake), medication-management E&M for prescribers, "
            "and add-ons — paid off the Medicare Physician Fee Schedule and "
            "commercial fee schedules, with Medicaid at state-set rates that are "
            "typically the lowest. Higher levels of care price differently: IOP "
            "and PHP bill per-diem or per-session bundles, residential bills a "
            "commercial per-diem, and inpatient psych bills a DRG or per-diem. "
            "Opioid-treatment programs get a bundled weekly Medicare payment "
            "(since 2020). The safety-net alternative to fee-for-service is the "
            "CCBHC prospective payment — a cost-based daily or monthly rate that "
            "covers the whole scope regardless of visit count. Because the "
            "commercial rate for the same therapy hour can be a large multiple "
            "of the Medicaid rate, the payer mix, not the clinical model, sets "
            "the margin — and a meaningful share of the commercial outpatient "
            "market runs out-of-network on self-pay and superbills."),
        key_players=(
            "Outpatient therapy platforms: LifeStance Health (public), Refresh "
            "Mental Health (Optum), Mindpath Health, Thriveworks, and the "
            "clinician-marketplace model (Headway, Grow Therapy, SonderMind, "
            "Alma) that solves credentialing and billing for independent "
            "therapists. Addiction / SUD and psychiatric facility operators: "
            "Acadia Healthcare, Universal Health Services (UHS Behavioral), "
            "BayMark Health Services, Summit BHC, Discovery Behavioral Health, "
            "and Pinnacle Treatment Centers. Safety-net and community: CCBHCs "
            "and nonprofit community mental-health centers. Digital-first: Talkspace, "
            "Brightside, Cerebral (post-enforcement), Path. The acquirable pool is "
            "the vast independent-practice and regional-operator long tail."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Combined MH + SUD treatment spending (all payers)",
                    "~$280.00B", "GOV · SAMHSA spending-accounts projection"),
            Segment("Adults with any mental illness (past year)",
                    "~59M (~23% of adults)",
                    "GOV · SAMHSA NSDUH prevalence"),
            Segment("People needing SUD treatment vs. receiving it",
                    "large unmet-need gap",
                    "GOV · SAMHSA NSDUH treatment gap"),
            Segment("Medicaid share of behavioral-health financing",
                    "single largest payer (~25%)",
                    "GOV · SAMHSA payer-of-behavioral-health estimates"),
            Segment("Behavioral telehealth",
                    "the largest telehealth category",
                    "ILLUSTRATIVE · CMS telehealth-trends, directional"),
        ],
        growth_drivers=[
            "Rising prevalence + destigmatized help-seeking ~3.0%/yr",
            "Parity enforcement + coverage expansion ~2.0%/yr",
            "Telehealth-led access to shortage areas ~1.5%/yr",
            "CCBHC expansion converting safety-net demand into funded volume",
            "Rate/labor pressure −1.5%/yr — clinician wages outrun rate updates",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial / self-pay (out-of-network)": 0.35,
            "Medicaid / MCO": 0.30,
            "Self-pay / cash / grants": 0.23,
            "Medicare / MA": 0.12,
        },
        rate_mechanics=[
            "Psychotherapy CPT time codes (90832/90834/90837) and the "
            "diagnostic evaluation (90791/90792) — the outpatient FFS backbone, "
            "paid off the MPFS (RVU × conversion factor × GPCI) and commercial "
            "fee schedules; Medicaid pays state-set rates that are usually the "
            "lowest of any payer.",
            "Medication-management E&M for prescribers (psychiatrists, PMHNPs), "
            "billed alongside brief therapy add-ons.",
            "IOP / PHP per-diem or per-session bundles for the intermediate "
            "levels of care, gated by payer utilization review.",
            "Residential and inpatient psychiatric per-diem / DRG — commercial "
            "for private residential; the IMD exclusion limits adult Medicaid "
            "coverage in facilities over 16 beds absent an 1115 waiver.",
            "CCBHC prospective payment (PPS) — a cost-based daily or monthly "
            "rate covering the full required scope, decoupled from visit volume "
            "— the safety-net funding model that actually pencils.",
            "OTP weekly bundle — Medicare pays opioid-treatment programs a "
            "bundled weekly rate for the drug plus counseling (since 2020); "
            "Medicaid covers MAT broadly.",
            "Out-of-network / single-case agreements / superbills — a large "
            "share of the commercial outpatient market runs OON on cash with "
            "patient-submitted claims, sidestepping thin in-network rates.",
        ],
        reimbursement_risk=(
            "Two structural risks dominate. First, the parity-enforcement gap: "
            "the Mental Health Parity and Addiction Equity Act requires "
            "behavioral coverage no more restrictive than medical/surgical, but "
            "payers apply non-quantitative treatment limits — utilization "
            "review, medical-necessity criteria, and narrow ('ghost') networks — "
            "that produce denials and step-downs at exactly the higher levels of "
            "care (IOP, PHP, residential) where the revenue concentrates, so a "
            "residential book carries real days-delivered-vs-days-paid leakage. "
            "Second, Medicaid rate risk: the sickest, highest-need populations "
            "are Medicaid-funded at state-set rates that chronically lag "
            "clinician wage inflation, so a Medicaid-heavy platform is squeezed "
            "between a rising labor cost and a legislatively-fixed price. The "
            "SUD segment additionally carries a program-integrity legacy — "
            "'body-brokering,' patient-brokering, and lab-billing abuses drew "
            "enforcement that made source-of-referral and lab economics "
            "first-order diligence items."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Mental Health Parity and Addiction Equity Act (MHPAEA)",
                 "Requires behavioral coverage no more restrictive than medical/"
                 "surgical; the 2024 final rule tightened non-quantitative "
                 "treatment-limit testing — the governing payer-behavior rule.",
                 "https://www.cms.gov/marketplace/private-health-insurance/mental-health-parity-addiction-equity"),
            Rule("42 CFR Part 2 — confidentiality of SUD records",
                 "Special consent/redisclosure rules for substance-use records "
                 "(aligned closer to HIPAA in the 2024 rule) — a compliance and "
                 "data-integration constraint unique to SUD.",
                 "https://www.ecfr.gov/current/title-42/chapter-I/subchapter-A/part-2"),
            Rule("CCBHC certification + PPS (SAMHSA / CMS)",
                 "Defines the Certified Community Behavioral Health Clinic scope "
                 "and its cost-based prospective payment — the safety-net "
                 "funding model expanding to all states.",
                 "https://www.samhsa.gov/certified-community-behavioral-health-clinics"),
            Rule("IMD exclusion + 1115 SUD/SMI demonstration waivers",
                 "Medicaid generally will not pay for adults 21-64 in "
                 "psychiatric/residential facilities over 16 beds; 1115 waivers "
                 "are the workaround that lets residential Medicaid revenue flow.",
                 "https://www.medicaid.gov/medicaid/section-1115-demonstrations"),
            Rule("MAT Act (2023) — DEA X-waiver elimination + DEA tele-"
                 "prescribing",
                 "Removed the buprenorphine X-waiver (any DEA-registered "
                 "prescriber may treat OUD) and the DEA/HHS telemedicine "
                 "controlled-substance flexibilities gate the tele-MAT model.",
                 "https://www.deadiversion.usdoj.gov/"),
        ],
        policy_watch=[
            "MHPAEA 2024 final-rule enforcement and NQTL comparative analyses",
            "CCBHC nationwide demonstration expansion and state adoption pace",
            "DEA final rule on telemedicine prescribing of controlled substances",
            "State licensure of counselors/therapists + interstate compacts "
            "(PSYPACT, Counseling Compact) easing the labor constraint",
            "Medicaid behavioral rate reviews and the 'Ensuring Access' rule",
            "988 / crisis-continuum build-out feeding downstream demand",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Among the most fragmented verticals in healthcare — tens of "
            "thousands of solo and small-group practices, community mental-"
            "health centers, and regional SUD operators, with no owner "
            "approaching national share. Fragmentation is structural: behavioral "
            "care is local, licensure is state-by-state, and the product is a "
            "clinician's time. That is precisely why the roll-up thesis is so "
            "heavily worked — and why credentialing, licensure, and clinician "
            "retention (not demand) are what separate scaled platforms from "
            "stalled ones."),
        hhi_or_share=(
            "No national concentration; even the largest outpatient platform "
            "(LifeStance) holds low-single-digit share of clinicians. There is "
            "no vendored national behavioral-facility file, so operator "
            "concentration is honestly not measured here — the deal corpus "
            "below is the real trading history."),
        consolidation=(
            "Three distinct consolidation plays run in parallel: outpatient "
            "therapy roll-ups (LifeStance, Refresh/Optum, Mindpath, Thriveworks) "
            "aggregating clinicians for payer contracting and back-office scale; "
            "addiction/psychiatric facility platforms (Acadia, UHS, Summit BHC, "
            "BayMark, Discovery, Pinnacle) building residential and inpatient "
            "capacity; and clinician marketplaces (Headway, Grow, SonderMind, "
            "Alma) monetizing credentialing/billing rather than owning the "
            "clinician. The 2017-2021 capital wave repriced hard as labor cost "
            "and payer rate cuts exposed which models actually scale."),
        pe_activity=(
            "Intensely PE-active for a decade, now bifurcated. Outpatient "
            "roll-ups drew heavy sponsor interest but ran into clinician-churn, "
            "credentialing-lag, and integration friction (LifeStance's post-IPO "
            "reset is the cautionary tale). SUD/residential attracted sponsors "
            "on high per-diem margins but carries census volatility, parity/"
            "utilization-review leakage, and a program-integrity legacy. "
            "Diligence has migrated from census growth to clinician retention, "
            "in-network rate durability, and out-of-network dependency."),
        notable_players=[
            "LifeStance Health", "Refresh Mental Health (Optum)",
            "Acadia Healthcare", "Universal Health Services (Behavioral)",
            "Thriveworks", "Mindpath Health", "Headway", "SonderMind",
            "BayMark Health Services", "Summit BHC",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / therapy hour (blended)", "$90-200",
                "Commercial/cash sit well above Medicaid; the blend is a direct "
                "read on payer mix and the single biggest value driver."),
            Kpi("Clinician productivity (billable sessions/week)", "22-30",
                "The output metric — capacity is clinician time, so utilization "
                "of a scarce, salaried resource is the whole game."),
            Kpi("Clinician compensation (% of net revenue)", "50-65%",
                "The dominant cost; W-2 vs 1099 mix and comp model (salary vs "
                "productivity) decide the margin residual."),
            Kpi("No-show / late-cancellation rate", "10-20%",
                "Lost, non-recoverable capacity on a fixed clinician cost — a "
                "few points swing the P&L."),
            Kpi("Clinician annualized turnover", "20-35%+",
                "Retention is existential; churn destroys credentialed, "
                "revenue-producing capacity and reloads the recruiting cost."),
            Kpi("Credentialing lead time (new clinician → billable)",
                "60-150 days",
                "Cash burn before a hire produces revenue; payer-enrollment "
                "speed is a real operational moat."),
            Kpi("Platform EBITDA margin", "10-20% (illustrative)",
                "Outpatient sits in the low-to-mid range; residential SUD can "
                "run higher when full but is far more volatile."),
        ],
        margin_profile=(
            "Behavioral-health economics reduce to a labor-arbitrage identity: "
            "gross margin per clinician-hour is the payer rate minus clinician "
            "compensation, and everything else (real estate, EHR, billing, "
            "supervision) is spread over volume. Because clinician comp runs "
            "half to two-thirds of revenue and demand is effectively unlimited, "
            "margin is set on the cost side — recruit and retain clinicians, "
            "keep them productive, and minimize no-shows — and on the mix side — "
            "the more commercial/cash and the less Medicaid, the higher the "
            "rate per hour. Residential and inpatient invert to a fixed-bed, "
            "occupancy-driven model where census volatility and utilization-"
            "review leakage swing margin. Scale helps most where it accelerates "
            "credentialing and payer contracting, not where it buys buildings."),
    ),
    risks=[
        Risk("Clinician supply, retention, and wage inflation", "High",
             "The binding constraint — turnover and comp inflation destroy "
             "capacity and outrun payer rate updates."),
        Risk("Medicaid rate risk on the highest-need populations", "High",
             "State-set rates lag wages and are legislatively fixed; a "
             "Medicaid-heavy book is structurally squeezed."),
        Risk("Parity / utilization-review denials at higher levels of care",
             "High",
             "IOP/PHP/residential revenue leaks through medical-necessity "
             "denials and forced step-downs despite MHPAEA."),
        Risk("Out-of-network / cash dependency + No Surprises exposure",
             "Medium",
             "Commercial margin that relies on OON billing is vulnerable to "
             "network and balance-billing pressure."),
        Risk("SUD program-integrity legacy (patient/body brokering, lab "
             "billing)", "Medium",
             "Referral-source and lab economics carry enforcement and "
             "reputational tail risk in addiction treatment."),
        Risk("Telehealth / DEA tele-prescribing flexibility reversal",
             "Medium",
             "The digital and hybrid models depend on continued controlled-"
             "substance tele-prescribing and telehealth payment parity."),
    ],
    diligence_questions=[
        "What is the payer mix by service line, and what is the true blended "
        "revenue per clinician-hour — commercial/cash vs Medicaid?",
        "What share of commercial revenue is in-network vs out-of-network/cash, "
        "and how durable are the in-network contracted rates?",
        "What is clinician turnover, tenure distribution, and the ramp/"
        "credentialing lead time from hire to first billable session?",
        "What is clinician productivity (sessions/week) and the no-show rate, "
        "and how are they trending?",
        "For any residential/IOP/PHP: what is the days-delivered-vs-days-paid "
        "gap and the utilization-review denial/appeal history?",
        "Is there CCBHC certification or a path to it, and what would the PPS "
        "rate do to the Medicaid book's economics?",
        "For SUD lines: what are the referral sources, lab arrangements, and "
        "any patient-brokering / kickback exposure under review?",
        "What is the exposure to telehealth payment parity and DEA tele-"
        "prescribing continuation?",
    ],
    insider_lens=[
        "Demand is not the question — capacity is. Waitlists are everywhere; "
        "the scarce input is a credentialed, retained, productive clinician. A "
        "behavioral platform is really a clinician-recruiting-and-retention "
        "machine with a billing engine attached, and the diligence that matters "
        "is on churn and credentialing lead time, not TAM.",
        "The payer mix is two different companies stapled together. The "
        "commercial/cash outpatient book earns real margin; the Medicaid SMI/SUD "
        "book is a mission-and-scale play at thin, fixed rates. Underwrite them "
        "separately — a blended margin hides which one is subsidizing which.",
        "Parity is the law and the loophole at once. MHPAEA guarantees coverage "
        "but payers manage cost through utilization review and narrow networks, "
        "so the real revenue risk on residential/IOP is the authorization, not "
        "the diagnosis. Model days-paid, not days-delivered.",
        "CCBHC quietly changes the safety-net math. A cost-based prospective "
        "rate turns a chronically underwater community model into a fundable "
        "one — a certification (or a credible path to one) can be the most "
        "valuable asset on a Medicaid-heavy platform's balance sheet.",
        "Out-of-network is the hidden margin — and the hidden fragility. A cash/"
        "OON outpatient book prints attractive rates precisely because it "
        "sidesteps thin in-network fee schedules; that same dependency is what "
        "network expansion, No-Surprises rules, and payer pressure erode.",
        "The addiction segment carries history. A decade of patient-brokering, "
        "'body-brokering,' and lab-billing scandals means referral source and "
        "toxicology economics get read the way a hospice's aggregate cap gets "
        "read — as the first thing that can be fraudulent, not the last.",
    ],
    connections=default_connections(
        "behavioral_health",
        deals_sector="behavioral_health",
        extra_pages=[
            ("/industry/behavioral_health",
             "Industry deep-dive — behavioral-health deal history + structure"),
        ],
        connectors=[
            ("hrsa_data_hpsa_mental_health",
             "HRSA Mental-Health HPSAs — the clinician-shortage geography that "
             "sizes unmet demand"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — psychiatrists, psychologists, LCSWs, LPCs, PMHNPs "
             "(the labor supply)"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — psychotherapy & E&M service "
             "volume"),
            ("medicaid_data_sdud_2025",
             "Medicaid State Drug Utilization — buprenorphine/MAT prescribing "
             "as an SUD-demand read"),
            ("cdc_data_vsrr_drug_overdose",
             "CDC provisional overdose deaths — the SUD demand curve"),
            ("cms_open_data_medicare_telehealth_trends",
             "Medicare telehealth trends — behavioral is the largest category"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded providers (SUD program-integrity screen)"),
        ],
    ),
    sources=[
        Source("SAMHSA — Projections of National Expenditures for Mental Health "
               "and Substance Use Disorder Treatment", "GOV",
               "https://www.samhsa.gov/data/"),
        Source("SAMHSA — National Survey on Drug Use and Health (NSDUH), "
               "prevalence and treatment-gap estimates", "GOV",
               "https://www.samhsa.gov/data/data-we-collect/nsduh-national-survey-drug-use-and-health"),
        Source("Mental Health Parity and Addiction Equity Act (MHPAEA) — "
               "final rule and enforcement", "GOV",
               "https://www.cms.gov/marketplace/private-health-insurance/mental-health-parity-addiction-equity"),
        Source("42 CFR Part 2 — Confidentiality of Substance Use Disorder "
               "Patient Records", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-I/subchapter-A/part-2"),
        Source("SAMHSA — Certified Community Behavioral Health Clinics (CCBHC) "
               "criteria and PPS", "GOV",
               "https://www.samhsa.gov/certified-community-behavioral-health-clinics"),
        Source("KFF — Medicaid's role in financing behavioral-health services",
               "INDUSTRY", "https://www.kff.org/"),
        Source("PE Desk industry deep-dive (behavioral health) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=behavioral_health"),
    ],
    live_figures=live_figures_from_dive("behavioral_health"),
    trends=(
        "Behavioral health went from an underfunded, stigmatized backwater to "
        "one of the most heavily capitalized verticals in healthcare over a "
        "single decade, and the arc is now maturing. Three policy shifts set it "
        "up: MHPAEA (2008) put parity into law, the ACA made behavioral an "
        "essential health benefit and expanded Medicaid coverage of the "
        "population that needs it most, and the CCBHC demonstration gave the "
        "safety net a funding model that actually pencils. COVID then reset the "
        "access curve — behavioral became the largest telehealth category "
        "overnight — and unleashed a wave of capital into outpatient roll-ups, "
        "addiction/residential platforms, and clinician marketplaces during "
        "2017-2021. That boom has repriced. The binding constraint turned out "
        "to be clinician labor, not demand: turnover, wage inflation, and "
        "credentialing lag punished platforms that grew faster than they could "
        "staff, while payer rate cuts and utilization-review leakage exposed the "
        "gap between statutory parity and paid claims. The forward story is a "
        "flight to the models that solve labor (marketplaces, hybrid telehealth, "
        "PSYPACT/Counseling-Compact licensure portability) and the funding "
        "unlocks (CCBHC PPS, 988/crisis build-out feeding demand), against a "
        "continuing headwind of Medicaid rate pressure and a DEA tele-"
        "prescribing rule that will make or break the digital-MAT models."),
    growth_levers=[
        GrowthLever(
            "Prevalence + destigmatized help-seeking",
            "Rising diagnosed prevalence and falling stigma pull a larger share "
            "of a large unmet-need pool into treatment — non-discretionary, "
            "demographically broad demand.",
            "+3.0%/yr utilization", "GOV"),
        GrowthLever(
            "Parity enforcement + coverage expansion",
            "MHPAEA's tightened 2024 rule plus Medicaid/ACA coverage of the "
            "highest-need population convert latent demand into paid claims.",
            "+2.0%/yr coverage", "GOV"),
        GrowthLever(
            "Telehealth-led access to shortage areas",
            "Behavioral is the largest telehealth category; virtual and hybrid "
            "models reach HRSA mental-health shortage geographies FFS never did.",
            "+1.5%/yr access", "ILLUSTRATIVE"),
        GrowthLever(
            "CCBHC prospective-payment expansion",
            "A cost-based PPS rate turns safety-net demand into funded volume — "
            "the demonstration is expanding to every state.",
            "Medicaid unlock", "GOV"),
        GrowthLever(
            "Rate + labor pressure drag",
            "Clinician wage inflation outruns Medicaid and commercial rate "
            "updates, compressing the per-hour spread.",
            "−1.5%/yr margin", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Diagnosed prevalence × help-seeking × coverage, gated by "
               "clinician supply",
        analysis=(
            "The demand base is enormous and only partly served: SAMHSA's NSDUH "
            "counts roughly 59 million US adults with any mental illness in a "
            "given year (~23% of adults) and a substance-use treatment gap in "
            "which most people who meet criteria never receive care. Diagnosed "
            "prevalence and help-seeking are both rising as stigma falls and "
            "screening spreads, and coverage expansion (ACA essential benefit, "
            "Medicaid) plus telehealth convert more of that latent need into paid "
            "encounters. Critically, the demand curve is not the binding "
            "constraint — the supply of clinicians is. There are persistent "
            "mental-health professional shortage areas across most of the "
            "country, so realized volume is gated by how fast a platform can "
            "recruit, credential, and retain therapists and prescribers. The "
            "practical implication for underwriting: model growth off staffed "
            "capacity and credentialing throughput, not off the (effectively "
            "unlimited) addressable population."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Clinician compensation (therapists, prescribers)",
            "~50-65% of cost",
            "The dominant line by far. Comp model (salary vs productivity), "
            "W-2 vs 1099 mix, and retention decide the margin residual on every "
            "billed hour.", "ILLUSTRATIVE"),
        CostDriver(
            "Recruiting, credentialing & clinical supervision",
            "~8-15% of cost",
            "The cost of feeding the labor machine — sourcing, payer "
            "enrollment (60-150 day lag before billing), and supervisory hours "
            "for associate-level clinicians.", "ILLUSTRATIVE"),
        CostDriver(
            "Billing, RCM, prior-auth & denials management",
            "~6-12% of cost",
            "Behavioral RCM is denial-heavy — utilization review, "
            "authorizations, and appeals on higher levels of care.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Facilities / real estate (or residential milieu)",
            "~8-15% of cost",
            "Office footprint for outpatient (shrunk by telehealth); for "
            "residential/inpatient, the fixed bed-and-milieu cost that occupancy "
            "must cover.", "ILLUSTRATIVE"),
        CostDriver(
            "Technology (EHR, telehealth, measurement-based care)",
            "~4-8% of cost",
            "The platform layer — EHR, tele-infrastructure, and outcomes "
            "measurement increasingly required by payers.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "There is no vendored national behavioral-health facility roll — the "
        "sector spans licensed outpatient practices, community mental-health "
        "centers, SUD programs, and psychiatric facilities under different "
        "state regimes — so state geography is omitted rather than fabricated. "
        "The variables that actually differ by state are the Medicaid behavioral "
        "rate schedule and managed-care structure, the presence of CCBHC "
        "certification, IMD-waiver status (which gates residential Medicaid "
        "revenue), and the depth of the clinician shortage. The HRSA mental-"
        "health HPSA, NPI-taxonomy, and Medicaid connectors linked below are the "
        "honest way to map clinician supply and payer structure by geography."),
)

register(REPORT)
