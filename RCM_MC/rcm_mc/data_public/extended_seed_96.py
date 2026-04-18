"""Extended seed 96: Autism / ABA therapy / developmental pediatric PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the autism / ABA therapy / developmental pediatric
subsector. The theme covers:

- Applied Behavior Analysis (ABA) therapy platforms delivering
  evidence-based behavioral intervention for autism spectrum disorder
  (ASD) across center-based, in-home, and school-based settings, with
  treatment planning and direct service billed under the ABA CPT code
  set: 97151 (behavior identification assessment by a QHP / BCBA),
  97152 (behavior identification supporting assessment by a technician),
  97153 (adaptive behavior treatment by protocol, the core RBT-
  delivered 1:1 therapy unit), 97154 (group adaptive behavior
  treatment by protocol), 97155 (adaptive behavior treatment with
  protocol modification by a QHP / BCBA), 97156 (family adaptive
  behavior treatment guidance), 97157 (multiple-family group
  adaptive behavior treatment guidance), and 97158 (group adaptive
  behavior treatment with protocol modification). The PE-backed ABA
  roll-up thesis is modeled on the Centerbridge / Behavioral Health
  Works, TPG / LEARN Behavioral, Blackstone / Center for Autism and
  Related Disorders (CARD — subsequent 2023 bankruptcy as a cautionary
  tale on Medicaid rate and staffing economics), Bain / The Stepping
  Stones Group, Onex / ChanceLight Behavioral Health, Audax / Hopebridge,
  Nautic Partners / Invo Healthcare, and FFL Partners / Autism Learning
  Partners PE aggregation playbooks
- Autism services platforms delivering diagnostic evaluation
  (ADOS-2 / ADI-R under a developmental pediatrician or child
  psychologist), multidisciplinary care coordination, and the
  wraparound of ABA with speech / OT / PT and parent training
  services for children ages 18 months through 21 years under state
  autism-mandate commercial coverage and Medicaid coverage
- Developmental pediatrics platforms delivering subspecialty
  diagnostic evaluation and longitudinal care for autism spectrum
  disorder, ADHD, learning disabilities, intellectual disability,
  and developmental delay at academic-affiliated or freestanding
  multidisciplinary clinics
- Pediatric speech / occupational therapy platforms delivering
  pediatric SLP services (CPT 92507 individual speech / language
  treatment, 92508 group treatment, 92523 evaluation of speech /
  language comprehension and expression), pediatric OT services
  (CPT 97165 / 97166 / 97167 OT evaluation, 97530 therapeutic
  activities, 97110 therapeutic exercise), and pediatric PT at
  clinic-based and school-based contract settings
- Early intervention (EI) platforms delivering Part C IDEA
  (Individuals with Disabilities Education Act Part C) birth-to-3
  developmental services under state-contracted EI programs and
  1915(c) HCBS (Home and Community-Based Services) waiver
  authorities, with state Medicaid agencies as the primary payer

Autism / ABA therapy economics are distinguished by a
commercial-heavy payer mix (42-68% commercial driven by state
autism-insurance mandates requiring commercial plans to cover
medically necessary ABA therapy in all 50 states per the Autism
Speaks 50-state mandate tracking), a large Medicaid block
(22-45% reflecting state-mandated Medicaid EPSDT coverage of
ABA and Medicaid managed-care plan administration of ABA
benefits, with state-by-state variance in Medicaid rate
per 15-minute unit of 97153 direct RBT service), and a
small self-pay segment (2-8%) concentrated in wealthy-market
center-based programs operating outside of network for premium
service delivery. The subsector faces specific regulatory and
coverage dynamics: (a) BCBA (Board Certified Behavior Analyst)
credentialing through the BACB (Behavior Analyst Certification
Board) creates a fundamental labor-supply constraint — BCBAs
supervise RBT (Registered Behavior Technician) staff at a
state-mandated supervision ratio (typically 1 BCBA per 10-15
RBTs), and BCBA hiring is the binding capacity constraint on
platform growth; (b) RBT certification (40-hour training course,
competency assessment, BACB registration) creates a high-turnover
front-line labor pool with 40-60% annual turnover driving
continuous training costs; (c) ABA CPT code 97151-97158
time-based billing under commercial plans and Medicaid fee
schedules, with commercial reimbursement typically $80-140 per
15-minute unit of 97153 (direct RBT service) and Medicaid
reimbursement typically $28-55 per 15-minute unit depending on
state — driving the commercial-heavy payer mix preference and
selective Medicaid participation by state; (d) state autism
insurance mandates (Autism Speaks tracks all 50 states — every
state now has some form of ABA coverage mandate for commercial
plans, with meaningful variance in age caps, hour caps, and
self-insured ERISA plan exemptions); (e) 1915(c) HCBS waiver
authorities at the state Medicaid agency level authorizing ABA
and related services for children with developmental disabilities
outside of institutional settings, with state-by-state waiver
design and wait-list dynamics; (f) the 2014 CMS HCBS final rule
on settings requirements tightening on what qualifies as an
HCBS-waiver-eligible service location (community-based, not
institutional); (g) insurance parity under the Mental Health
Parity and Addiction Equity Act (MHPAEA 2008) and its 2013
final rule interpretation extending ABA coverage protections;
(h) appropriate-level-of-service (LOS) medical-necessity review
at commercial-plan utilization-management vendors (Magellan,
Beacon, Optum) creating authorization-management burden on ABA
providers at the 15-25 hours/week versus 25-40 hours/week
intensity tier decision; (i) the 2023 CARD / Center for Autism
and Related Disorders bankruptcy (Blackstone-backed) as a
cautionary tale on Medicaid rate compression, BCBA wage
inflation, RBT turnover economics, and the limits of the PE
roll-up thesis in a labor-constrained state-payer-regulated
subsector; and (j) post-2022 PE multiple compression on ABA
platforms as the CARD bankruptcy and associated reputational
events reset buyer expectations on risk-adjusted exit
multiples. Value creation in PE-backed autism / ABA / developmental
pediatric platforms centers on BCBA recruiting and retention,
RBT training-to-certification pipelines, state-mix optimization
(selecting commercial-mandate-friendly and favorable-Medicaid-
rate states), authorization-management workflow efficiency at
commercial UM vendors, appropriate-level-of-service intensity
tier defense at utilization review, scheduling-density and
clinician-utilization optimization, and consolidation of
independent ABA clinics and multidisciplinary developmental
clinics into regional platforms. Each record captures deal
economics (EV, EV/EBITDA, margins), return profile (MOIC, IRR,
hold period), payer mix, regional footprint, sponsor, realization
status, and a short deal narrative. These records are synthesized
for modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_96 = [
    {
        "company_name": "Bluebird ABA Therapy Network",
        "sector": "ABA Therapy",
        "buyer": "FFL Partners",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 385.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 73.15,
        "ebitda_margin": 0.19,
        "revenue_mm": 385.00,
        "hold_years": 5.5,
        "moic": 2.8,
        "irr": 0.2085,
        "status": "Realized",
        "payer_mix": {"commercial": 0.58, "medicaid": 0.32, "medicare": 0.02, "self_pay": 0.08},
        "comm_pct": 0.58,
        "deal_narrative": (
            "Southeast ABA therapy platform with 68 BCBA-supervised "
            "clinics across Florida, Georgia, North Carolina, and "
            "Tennessee delivering center-based and in-home applied "
            "behavior analysis for children with autism spectrum "
            "disorder ages 2-18. Billing concentrated on the ABA CPT "
            "code set (97151 BCBA assessment, 97152 technician-"
            "supporting assessment, 97153 direct RBT 1:1 therapy as "
            "the core 15-minute unit, 97155 BCBA protocol modification, "
            "97156 family guidance, 97158 group protocol modification). "
            "Long hold rolled up 28 independent ABA clinics on the "
            "Autism Learning Partners / LEARN Behavioral playbook, "
            "grew RBT workforce from 420 to 1,180 front-line "
            "technicians, built BCBA recruiting pipeline to manage "
            "1:12 supervision ratio, navigated state-by-state autism-"
            "mandate commercial coverage and selective Medicaid "
            "participation, and exited to a strategic ABA consolidator "
            "at 2.8x MOIC."
        ),
    },
    {
        "company_name": "Meridian Autism Services Group",
        "sector": "Autism Services",
        "buyer": "Audax Private Equity",
        "year": 2019,
        "region": "Midwest",
        "ev_mm": 215.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 47.30,
        "ebitda_margin": 0.22,
        "revenue_mm": 215.00,
        "hold_years": 5.0,
        "moic": 2.5,
        "irr": 0.2011,
        "status": "Realized",
        "payer_mix": {"commercial": 0.54, "medicaid": 0.38, "medicare": 0.02, "self_pay": 0.06},
        "comm_pct": 0.54,
        "deal_narrative": (
            "Midwest autism services platform with 32 multidisciplinary "
            "clinics across Ohio, Indiana, Michigan, and Illinois "
            "delivering diagnostic evaluation (ADOS-2 / ADI-R under a "
            "developmental pediatrician or child psychologist), ABA "
            "therapy (CPT 97151-97158), speech / language therapy, "
            "occupational therapy, and parent training. Long hold "
            "integrated diagnostic-to-treatment workflow reducing "
            "the typical 6-9 month wait from suspected ASD to ABA "
            "initiation, navigated state autism-mandate commercial "
            "coverage per the Autism Speaks 50-state tracker (Ohio, "
            "Indiana, Michigan all with mandate coverage), managed "
            "Medicaid 1915(c) HCBS waiver participation on the "
            "developmentally-disabled pediatric population, and "
            "exited to a strategic autism consolidator at 2.5x MOIC "
            "before post-2022 multiple compression."
        ),
    },
    {
        "company_name": "Canyon Developmental Pediatrics",
        "sector": "Developmental Pediatrics",
        "buyer": "Linden Capital Partners",
        "year": 2020,
        "region": "West",
        "ev_mm": 145.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 31.90,
        "ebitda_margin": 0.22,
        "revenue_mm": 145.00,
        "hold_years": 4.5,
        "moic": 2.2,
        "irr": 0.1958,
        "status": "Active",
        "payer_mix": {"commercial": 0.62, "medicaid": 0.28, "medicare": 0.02, "self_pay": 0.08},
        "comm_pct": 0.62,
        "deal_narrative": (
            "West Coast developmental pediatrics subspecialty platform "
            "with 18 multidisciplinary clinics across California, "
            "Arizona, and Nevada delivering longitudinal care for "
            "autism spectrum disorder, ADHD, learning disabilities, "
            "intellectual disability, and developmental delay. "
            "Service mix includes developmental-behavioral pediatrician "
            "evaluation (ADOS-2 administration by trained evaluator), "
            "child psychologist neuropsychological testing, referral "
            "and care-coordination into downstream ABA therapy, "
            "speech / OT / PT integration, and school-liaison "
            "advocacy under IDEA Part B IEP planning. Mid-hold "
            "navigates insurance parity under MHPAEA 2008 on "
            "commercial-covered developmental evaluations, state "
            "autism-mandate coverage of diagnostic assessment "
            "protocols, and building appropriate-levels-of-service "
            "protocols for downstream ABA authorization management."
        ),
    },
    {
        "company_name": "Sagebrush Pediatric Therapy Partners",
        "sector": "Speech / Occupational Therapy (Peds)",
        "buyer": "Shore Capital Partners",
        "year": 2019,
        "region": "Southwest",
        "ev_mm": 165.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 34.65,
        "ebitda_margin": 0.21,
        "revenue_mm": 165.00,
        "hold_years": 5.5,
        "moic": 2.6,
        "irr": 0.1942,
        "status": "Realized",
        "payer_mix": {"commercial": 0.52, "medicaid": 0.40, "medicare": 0.02, "self_pay": 0.06},
        "comm_pct": 0.52,
        "deal_narrative": (
            "Southwest pediatric speech / occupational therapy "
            "platform with 42 clinic locations across Texas, "
            "Oklahoma, Arkansas, and New Mexico delivering pediatric "
            "SLP services (CPT 92507 individual speech / language "
            "treatment, 92508 group treatment, 92523 comprehensive "
            "evaluation of speech / language comprehension and "
            "expression), pediatric OT services (CPT 97165 / 97166 / "
            "97167 OT evaluation, 97530 therapeutic activities, "
            "97110 therapeutic exercise), and pediatric PT across "
            "clinic-based and school-contract settings. Long hold "
            "rolled up 18 independent pediatric therapy clinics on "
            "The Stepping Stones Group / Invo Healthcare playbook, "
            "grew school-district contract book on IDEA Part B "
            "IEP-driven therapy service delivery, navigated Texas / "
            "Oklahoma / New Mexico Medicaid fee-schedule dynamics, "
            "and exited to a strategic pediatric therapy platform "
            "at 2.6x MOIC."
        ),
    },
    {
        "company_name": "Harborlight ABA Centers",
        "sector": "ABA Therapy",
        "buyer": "TPG Growth",
        "year": 2017,
        "region": "Northeast",
        "ev_mm": 545.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 120.00,
        "ebitda_margin": 0.22,
        "revenue_mm": 545.00,
        "hold_years": 6.0,
        "moic": 3.2,
        "irr": 0.2181,
        "status": "Realized",
        "payer_mix": {"commercial": 0.64, "medicaid": 0.28, "medicare": 0.02, "self_pay": 0.06},
        "comm_pct": 0.64,
        "deal_narrative": (
            "Northeast ABA therapy platform with 82 center-based and "
            "in-home program locations across Massachusetts, "
            "Connecticut, New York, and New Jersey — four of the "
            "strongest commercial-autism-mandate states per the "
            "Autism Speaks 50-state tracker. Service mix concentrated "
            "on core ABA CPT billing (97151 BCBA assessment at "
            "$160-220/hour, 97153 direct RBT therapy as the "
            "90-95% of revenue-minutes at $80-140 per 15-minute unit "
            "commercial rate, 97155 BCBA protocol modification at "
            "$160-220/hour, 97156 family guidance). Long 6-year "
            "hold built BCBA recruiting pipeline to manage 1:10 "
            "supervision ratio, invested in RBT training infrastructure "
            "to manage 45-55% annual turnover, grew from 620 to "
            "1,620 RBTs, navigated commercial UM vendor "
            "(Magellan / Beacon / Optum) appropriate-levels-of-"
            "service intensity tier authorization management, and "
            "exited to a strategic ABA consolidator at 3.2x MOIC."
        ),
    },
    {
        "company_name": "Redwood Early Intervention Services",
        "sector": "Early Intervention",
        "buyer": "Nautic Partners",
        "year": 2019,
        "region": "West",
        "ev_mm": 115.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 19.55,
        "ebitda_margin": 0.17,
        "revenue_mm": 115.00,
        "hold_years": 5.0,
        "moic": 2.0,
        "irr": 0.1487,
        "status": "Realized",
        "payer_mix": {"commercial": 0.44, "medicaid": 0.44, "medicare": 0.04, "self_pay": 0.08},
        "comm_pct": 0.44,
        "deal_narrative": (
            "West Coast early intervention (EI) platform with 28 "
            "birth-to-3 service delivery locations across California, "
            "Oregon, and Washington operating under IDEA Part C "
            "(Individuals with Disabilities Education Act Part C) "
            "state-contracted EI programs and 1915(c) HCBS (Home "
            "and Community-Based Services) waiver authorities. "
            "Service mix delivers developmental evaluation, "
            "individualized family service plans (IFSPs), in-home "
            "and natural-environment ABA, pediatric SLP, pediatric "
            "OT, and developmental specialist services for children "
            "ages 0-3 with developmental delay or at risk. Long "
            "hold navigated the 2014 CMS HCBS final settings rule "
            "on community-based service-location qualification, "
            "managed state-contract rate dynamics on California "
            "DDS / Oregon EI / Washington ESIT programs, and exited "
            "to a strategic pediatric services platform at 2.0x "
            "MOIC on the challenged margin profile of state-"
            "contracted EI rate economics."
        ),
    },
    {
        "company_name": "Pinewood ABA Behavioral Health",
        "sector": "ABA Therapy",
        "buyer": "Centerbridge Partners",
        "year": 2016,
        "region": "National",
        "ev_mm": 785.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 180.55,
        "ebitda_margin": 0.23,
        "revenue_mm": 785.00,
        "hold_years": 6.5,
        "moic": 3.5,
        "irr": 0.2072,
        "status": "Realized",
        "payer_mix": {"commercial": 0.56, "medicaid": 0.34, "medicare": 0.02, "self_pay": 0.08},
        "comm_pct": 0.56,
        "deal_narrative": (
            "National ABA therapy platform acquired early in the "
            "2015-2022 ABA PE aggregation wave, scaled to 142 "
            "center-based locations and multi-state in-home "
            "programs on the Behavioral Health Works / LEARN "
            "Behavioral playbook. Long 6.5-year hold rolled up "
            "58 independent ABA clinics, grew BCBA workforce "
            "from 180 to 620 board-certified behavior analysts "
            "and RBT workforce to 3,100 certified technicians, "
            "built multi-state authorization-management operations "
            "center handling commercial UM vendor appropriate-"
            "levels-of-service defense at Magellan / Beacon / Optum "
            "on 25-40 hours/week intensity tier requests, and "
            "navigated state-by-state Medicaid rate variance "
            "($28-55 per 15-minute unit of 97153 state-by-state) "
            "via state-mix optimization favoring commercial-"
            "mandate-heavy markets. Exited to a strategic ABA "
            "consolidator at 3.5x MOIC before the 2023 CARD "
            "bankruptcy reset buyer expectations on the subsector."
        ),
    },
    {
        "company_name": "Silverbrook ABA Care Partners",
        "sector": "ABA Therapy",
        "buyer": "Blackstone",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 625.0,
        "ev_ebitda": 17.5,
        "ebitda_mm": 106.25,
        "ebitda_margin": 0.17,
        "revenue_mm": 625.00,
        "hold_years": 3.5,
        "moic": 1.4,
        "irr": 0.1003,
        "status": "Active",
        "payer_mix": {"commercial": 0.50, "medicaid": 0.42, "medicare": 0.02, "self_pay": 0.06},
        "comm_pct": 0.50,
        "deal_narrative": (
            "Southeast ABA therapy platform acquired at peak 2021 "
            "ABA multiples with 94 center-based locations across "
            "Florida, Georgia, Alabama, Mississippi, Louisiana, and "
            "South Carolina. Service mix centered on ABA CPT 97151-"
            "97158 billing across center-based and in-home delivery "
            "with a higher Medicaid mix reflecting southeast state "
            "demographics and Medicaid 1915(c) HCBS waiver "
            "participation. Mid-hold navigating structural headwinds "
            "the 2023 CARD / Center for Autism and Related Disorders "
            "bankruptcy surfaced across the ABA subsector: Medicaid "
            "rate compression on 97153 direct RBT service (some "
            "southeast states at $28-38 per 15-minute unit versus "
            "$90-120 commercial), BCBA wage inflation on post-2021 "
            "labor-market tightness (BCBA average compensation rose "
            "18-25% 2021-2024), RBT turnover at 50-60% annually "
            "driving continuous training cost, and commercial UM "
            "vendor appropriate-levels-of-service intensity-tier "
            "step-downs from 35-40 hours/week requests to 20-25 "
            "hours/week authorizations. Sponsor navigating value-"
            "creation reset on compressed exit multiples."
        ),
    },
    {
        "company_name": "Magnolia Autism & Behavioral Health",
        "sector": "Autism Services",
        "buyer": "Bain Capital Double Impact",
        "year": 2020,
        "region": "Mid-Atlantic",
        "ev_mm": 265.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 58.30,
        "ebitda_margin": 0.22,
        "revenue_mm": 265.00,
        "hold_years": 4.5,
        "moic": 2.1,
        "irr": 0.1769,
        "status": "Active",
        "payer_mix": {"commercial": 0.60, "medicaid": 0.30, "medicare": 0.02, "self_pay": 0.08},
        "comm_pct": 0.60,
        "deal_narrative": (
            "Mid-Atlantic autism services platform with 42 "
            "multidisciplinary clinics across Virginia, Maryland, "
            "Pennsylvania, and DC delivering integrated diagnostic "
            "evaluation (ADOS-2 / ADI-R by developmental "
            "pediatrician or licensed psychologist), ABA therapy "
            "across the CPT 97151-97158 code set, pediatric SLP, "
            "pediatric OT, pediatric PT, and parent training. Mid-"
            "hold grew integrated service-line attach-rate on newly "
            "diagnosed ASD patients (average 3.2 services per child "
            "vs. 1.4 industry baseline), navigated commercial UM "
            "vendor authorization management on 97153 intensity "
            "tier requests, built BCBA-to-RBT 1:10 supervision "
            "structure with strong RBT retention program reducing "
            "turnover from 55% to 38% annually, and is preparing "
            "for sale to a strategic autism platform at a compressed "
            "mid-teens multiple reflecting post-CARD subsector "
            "re-pricing."
        ),
    },
    {
        "company_name": "Ashwood Developmental Center Network",
        "sector": "Developmental Pediatrics",
        "buyer": "Gryphon Investors",
        "year": 2018,
        "region": "Midwest",
        "ev_mm": 95.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 20.90,
        "ebitda_margin": 0.22,
        "revenue_mm": 95.00,
        "hold_years": 5.5,
        "moic": 2.4,
        "irr": 0.1795,
        "status": "Realized",
        "payer_mix": {"commercial": 0.66, "medicaid": 0.24, "medicare": 0.02, "self_pay": 0.08},
        "comm_pct": 0.66,
        "deal_narrative": (
            "Midwest developmental pediatrics subspecialty network "
            "with 14 academic-affiliated multidisciplinary clinics "
            "across Minnesota, Wisconsin, Iowa, and Missouri "
            "delivering fellowship-trained developmental-behavioral "
            "pediatrician evaluation, pediatric neuropsychology "
            "testing, ASD / ADHD / learning disability / "
            "intellectual disability / developmental delay "
            "longitudinal care, and coordination with downstream "
            "ABA / SLP / OT / PT service providers. Long hold "
            "grew from 8 to 14 clinics through targeted tuck-ins "
            "of independent developmental pediatrician practices, "
            "built in-house neuropsychology testing capacity "
            "capturing CPT 96132-96139 evaluation codes, navigated "
            "commercial insurance-parity coverage under MHPAEA 2008 "
            "for developmental evaluations, and exited to a "
            "strategic pediatric multispecialty platform at 2.4x "
            "MOIC."
        ),
    },
    {
        "company_name": "Cypress Pediatric Therapies",
        "sector": "Speech / Occupational Therapy (Peds)",
        "buyer": "Onex Partners",
        "year": 2017,
        "region": "National",
        "ev_mm": 445.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 93.45,
        "ebitda_margin": 0.21,
        "revenue_mm": 445.00,
        "hold_years": 6.0,
        "moic": 3.0,
        "irr": 0.2017,
        "status": "Realized",
        "payer_mix": {"commercial": 0.50, "medicaid": 0.42, "medicare": 0.02, "self_pay": 0.06},
        "comm_pct": 0.50,
        "deal_narrative": (
            "National pediatric speech / occupational therapy "
            "platform with 128 clinic-based locations and 480+ "
            "school-district contracts modeled on the ChanceLight "
            "Behavioral Health / Invo Healthcare / Stepping Stones "
            "Group playbook. Service mix delivers pediatric SLP "
            "(CPT 92507 / 92508 / 92523), pediatric OT (CPT 97165-"
            "97167 evaluation, 97530 therapeutic activities, 97110 "
            "therapeutic exercise), pediatric PT, and school-"
            "contract therapy service delivery under IDEA Part B "
            "IEP / 504 Plan authorities. Long 6-year hold rolled "
            "up 42 independent pediatric therapy clinics, grew "
            "school-contract book from 180 to 480+ districts on "
            "the outsourced-therapy thesis, navigated state "
            "licensure variance for traveling therapists, and "
            "exited to a strategic pediatric platform at 3.0x MOIC "
            "on the combined clinic-and-school service-delivery "
            "scale."
        ),
    },
    {
        "company_name": "Willow Branch ABA Services",
        "sector": "ABA Therapy",
        "buyer": "Great Point Partners",
        "year": 2022,
        "region": "West",
        "ev_mm": 185.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 35.15,
        "ebitda_margin": 0.19,
        "revenue_mm": 185.00,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.56, "medicaid": 0.36, "medicare": 0.02, "self_pay": 0.06},
        "comm_pct": 0.56,
        "deal_narrative": (
            "West Coast ABA therapy platform with 38 center-based "
            "and in-home program locations across California, "
            "Oregon, Washington, and Colorado delivering the full "
            "ABA CPT code set (97151 BCBA assessment, 97152 "
            "technician supporting assessment, 97153 direct RBT "
            "1:1 therapy as the core revenue-minute, 97154 group "
            "therapy by protocol, 97155 BCBA protocol modification, "
            "97156 family guidance, 97157 multi-family group "
            "guidance, 97158 group therapy with protocol "
            "modification). Early hold acquired post-2022 "
            "multiple reset absorbing the 2023 CARD bankruptcy "
            "fallout — BCBA wage inflation on California labor "
            "market (BCBA average at $95-115K with benefits in "
            "metro markets), RBT turnover at 48% annually, "
            "commercial UM vendor authorization-management tightening "
            "on 25-40 hours/week intensity tier requests, and "
            "Medi-Cal / Oregon Health Plan / Washington Apple "
            "Health rate dynamics on Medicaid-participating "
            "locations. Sponsor pursuing value creation via BCBA "
            "retention program and state-mix optimization."
        ),
    },
    {
        "company_name": "Acorn Autism Learning Centers",
        "sector": "Autism Services",
        "buyer": "Webster Equity Partners",
        "year": 2019,
        "region": "Northeast",
        "ev_mm": 325.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 74.75,
        "ebitda_margin": 0.23,
        "revenue_mm": 325.00,
        "hold_years": 5.0,
        "moic": 2.7,
        "irr": 0.2204,
        "status": "Realized",
        "payer_mix": {"commercial": 0.68, "medicaid": 0.22, "medicare": 0.02, "self_pay": 0.08},
        "comm_pct": 0.68,
        "deal_narrative": (
            "Northeast autism learning centers platform with 52 "
            "center-based locations across Massachusetts, "
            "Connecticut, Rhode Island, New Hampshire, and Maine "
            "delivering integrated ABA therapy, autism-specialized "
            "early childhood education, ASD diagnostic evaluation, "
            "and parent training services. Benefited from the "
            "strongest-in-nation autism insurance mandates in "
            "Massachusetts / Connecticut commercial markets per "
            "the Autism Speaks 50-state tracker with robust "
            "commercial coverage of ABA at 25-40 hours/week "
            "intensity tiers. Long hold grew from 22 to 52 "
            "locations, built BCBA workforce to 164 board-"
            "certified analysts with 1:10 RBT supervision ratio, "
            "invested in proprietary ABA curriculum and outcome-"
            "measurement tools, navigated commercial UM vendor "
            "authorization management at Magellan / Beacon / Optum, "
            "and exited to a strategic autism platform at 2.7x "
            "MOIC before the 2023 subsector multiple reset."
        ),
    },
    {
        "company_name": "Prairie Early Start Programs",
        "sector": "Early Intervention",
        "buyer": "Council Capital",
        "year": 2018,
        "region": "Midwest",
        "ev_mm": 65.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 10.40,
        "ebitda_margin": 0.16,
        "revenue_mm": 65.00,
        "hold_years": 4.5,
        "moic": 1.8,
        "irr": 0.1403,
        "status": "Realized",
        "payer_mix": {"commercial": 0.42, "medicaid": 0.45, "medicare": 0.05, "self_pay": 0.08},
        "comm_pct": 0.42,
        "deal_narrative": (
            "Midwest early intervention (EI) platform with 22 "
            "birth-to-3 service delivery locations across Illinois, "
            "Indiana, Ohio, and Kentucky operating under IDEA Part "
            "C state-contracted EI programs and state Medicaid "
            "1915(c) HCBS waiver authorities for children with "
            "developmental disabilities. Service mix delivers "
            "developmental evaluation, individualized family "
            "service plans (IFSPs), in-home and natural-"
            "environment ABA, pediatric SLP, pediatric OT, and "
            "developmental specialist services for the 0-3 age "
            "population. Held through the 2014 CMS HCBS final "
            "settings rule tightening on community-based service-"
            "location qualification and navigated Illinois Early "
            "Intervention / Ohio Help Me Grow / Kentucky First "
            "Steps program rate dynamics. Exited to a strategic "
            "pediatric services consolidator at 1.8x MOIC on the "
            "state-contracted EI rate-economics margin challenge."
        ),
    },
    {
        "company_name": "Juniper Developmental Pediatrics",
        "sector": "Developmental Pediatrics",
        "buyer": "Charlesbank Capital Partners",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 75.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 18.75,
        "ebitda_margin": 0.25,
        "revenue_mm": 75.00,
        "hold_years": 3.5,
        "moic": 1.6,
        "irr": 0.1418,
        "status": "Active",
        "payer_mix": {"commercial": 0.64, "medicaid": 0.26, "medicare": 0.02, "self_pay": 0.08},
        "comm_pct": 0.64,
        "deal_narrative": (
            "Southeast developmental pediatrics platform with 10 "
            "subspecialty clinics across Florida, Georgia, "
            "Tennessee, and North Carolina delivering fellowship-"
            "trained developmental-behavioral pediatrician "
            "evaluation, child psychologist neuropsychology testing "
            "(CPT 96132-96139), ADOS-2 / ADI-R diagnostic "
            "evaluation for autism spectrum disorder, and "
            "coordination with downstream ABA / SLP / OT service "
            "providers. Mid-hold growing multi-state subspecialty "
            "referral footprint, navigating state autism-insurance-"
            "mandate commercial coverage of diagnostic evaluation "
            "per the Autism Speaks 50-state mandate tracker, "
            "building appropriate-levels-of-service recommendation "
            "protocols to support downstream ABA authorization "
            "management at commercial UM vendors (Magellan, Beacon, "
            "Optum), and sponsor targeting tuck-in add-ons ahead of "
            "sale to a regional pediatric multispecialty platform."
        ),
    },
]
