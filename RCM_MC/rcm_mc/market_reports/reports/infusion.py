"""Infusion — home + alternate-site (ambulatory suite) IV/injectable therapy.

Deals-only vertical (no national CMS infusion-suite facility census exists — the
Medicare Home Infusion Therapy provider file is partial), so this follows the
hospice copy-template: SOURCED corpus figures via ``live_figures_from_dive`` and
authored qualitative sections. The whole report is organized around the two
economic questions that decide an infusion deal — the site-of-care arbitrage
(HOPD → home/suite) that creates the demand, and white-bagging, which decides
whether the provider keeps the drug margin or becomes a chair-rental business.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="infusion",
    name="Infusion",
    care_setting="Pharmacy & infusion",
    naics="621999",
    one_line_def=(
        "Preparation and administration of IV, subcutaneous, and injectable "
        "medications outside the hospital — home infusion (anti-infectives, "
        "TPN, IVIG) delivered by a compounding pharmacy plus nursing, and "
        "ambulatory infusion suites that administer biologics for rheumatology, "
        "GI, neurology, and immunology."),
    tam_headline=TamHeadline(
        value=30.0, unit="$B", growth_pct=9.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US home + alternate-site infusion (drug + service), modeled at "
            "~$30B off the NHIA industry survey base; growth is the modeled "
            "composite of the site-of-care shift, the biologic pipeline, and "
            "rate — not a single filed CMS figure (infusion has no unified "
            "fee-schedule line)."),
    ),
    executive_summary=[
        "Site-of-care arbitrage is the thesis. Payers reimburse the identical "
        "biologic 2-3x higher in the hospital outpatient department than in a "
        "home or ambulatory suite, so they are actively steering volume to the "
        "lower-cost site — that migration, not underlying disease growth, is "
        "the demand engine.",
        "The drug is the revenue; the nursing/service is the cost. Home "
        "infusion is a drug-margin business with a nursing cost center bolted "
        "on, and the Medicare Home Infusion Therapy services benefit (Cures "
        "Act, 2021) notoriously underpays it by tying payment to days a skilled "
        "professional is physically in the home.",
        "White-bagging is the existential margin question. When a payer mandates "
        "its own specialty pharmacy ship the drug, the provider loses the "
        "buy-and-bill spread and is left renting a chair and a nurse — the "
        "single biggest swing factor in ambulatory-suite economics.",
        "Acute versus chronic mix sets the multiple. Anti-infectives and "
        "hydration are episodic and referral-driven off hospital discharge; "
        "IVIG, TPN, and specialty biologics are the recurring annuity that a "
        "buyer pays up for.",
        "One strategic (Option Care Health) plus PBM-owned arms (CVS/Coram, "
        "Optum) sit on top; the acquirable pool is the independent ambulatory "
        "infusion suite and regional home-infusion tail — a hot PE roll-up "
        "(IVX Health, Vivo) built entirely on the site-of-care shift.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral — hospital discharge (acute) or physician order (chronic)",
            "Benefit investigation + prior authorization + patient onboarding",
            "Drug sourcing — buy-and-bill acquisition vs. payer white-bag",
            "Sterile compounding / admixture (USP <797>) at the pharmacy",
            "Administration — home nursing visit or ambulatory-suite chair",
            "Clinical monitoring, lab draws, and therapy management",
            "Billing — drug (J-code / NDC) + administration + pharmacy per-diem",
            "Refill / resupply cadence for the chronic annuity book",
        ],
        sites_of_care=[
            "Patient home (home infusion — nurse-administered or self-infused)",
            "Ambulatory infusion suite (freestanding or physician-office)",
            "Physician-office infusion (in-office ancillary)",
            "Skilled nursing / facility-based infusion",
            "Hospital outpatient department (the high-cost site being displaced)",
        ],
        money_flow=(
            "Two revenue streams that behave very differently. The drug is "
            "billed either buy-and-bill — the provider buys the medication and "
            "bills the payer at Average Sales Price plus an add-on (ASP+6%, cut "
            "to roughly ASP+4.3% by sequestration) — or, increasingly, the "
            "payer white-bags it, shipping the drug from its own specialty "
            "pharmacy so the provider never touches the spread. The service is "
            "billed separately: administration codes (CPT 96365-96379) and, for "
            "home infusion, a pharmacy per-diem plus the Medicare Home Infusion "
            "Therapy per-visit payment that only accrues on days a professional "
            "is physically present. So the P&L is a drug-margin business (when "
            "buy-and-bill survives) sitting on a labor cost center — and the "
            "single biggest determinant of value is whether the payer lets the "
            "provider keep the drug."),
        key_players=(
            "Option Care Health is the scaled national strategic (home + suite) "
            "after the Option Care/BioScrip merger. The PBM-integrated arms — "
            "CVS Health/Coram and Optum Infusion — carry captive volume. "
            "Amerita (BrightSpring), KabaFusion, Soleo Health, and Vivo "
            "Infusion round out home + suite scale, while IVX Health is the "
            "marquee PE-backed ambulatory-suite pure-play. Health systems run "
            "their own infusion to retain biologic revenue. The acquirable "
            "whitespace is the independent suite operator and the regional "
            "home-infusion pharmacy."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Home infusion (anti-infectives, TPN, IVIG, specialty)",
                    "the core home channel",
                    "INDUSTRY · NHIA infusion industry survey"),
            Segment("Ambulatory infusion suites (rheum / GI / neuro / immuno "
                    "biologics)", "fastest-growing site of care",
                    "ILLUSTRATIVE · site-of-care shift model"),
            Segment("Provider-administered (Part B) infused-drug spend",
                    "majority of revenue is the drug",
                    "GOV · CMS Part B drug spending"),
            Segment("Chronic vs. acute therapy mix",
                    "chronic biologics = the annuity",
                    "ILLUSTRATIVE · therapy-mix economics"),
        ],
        growth_drivers=[
            "Site-of-care shift HOPD → home/suite ~+4-6%/yr — the payer engine",
            "Biologic + biosimilar pipeline expanding the infusible drug menu",
            "Chronic prevalence (autoimmune, neuro, immunodeficiency) rising",
            "Aging population lifting home anti-infective and TPN demand",
            "Rate + ASP updates on the drug component ~+2-3%/yr",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial (biologics / autoimmune)": 0.50,
            "Medicare / MA (Part B + HIT benefit)": 0.35,
            "Medicaid / other": 0.15,
        },
        rate_mechanics=[
            "Buy-and-bill — the provider acquires the drug and bills ASP + an "
            "add-on (ASP+6%, ~ASP+4.3% after sequestration); the acquisition-"
            "to-ASP spread is the drug margin.",
            "Administration fees — CPT 96365-96379 for the infusion visit "
            "(initial hour + each additional hour / drug).",
            "Medicare Home Infusion Therapy services benefit (Cures Act, 2021) "
            "— a per-visit payment that only accrues on days a skilled "
            "professional is in the home, leaving non-visit days uncovered.",
            "Part B DME external-infusion-pump benefit — a separate, older "
            "pathway covering the pump plus the drugs on the DME LCD.",
            "White-bagging / brown-bagging — the payer supplies the drug from "
            "its specialty pharmacy, stripping the buy-and-bill spread.",
            "Commercial site-of-care policies — plans mandate the lower-cost "
            "home/suite site (a volume tailwind) while capping the margin.",
        ],
        reimbursement_risk=(
            "The margin risk is white-bagging and payer site-of-care mandates. "
            "A plan that forces its own specialty pharmacy to ship the biologic "
            "removes the buy-and-bill spread that carries the P&L, turning the "
            "provider into a chair-and-nurse rental. Compounding it, the "
            "Medicare HIT services benefit underpays home nursing by tying "
            "payment to professional-present days, and ASP erosion plus "
            "biosimilar substitution shrink the per-unit drug dollar. The "
            "offsetting tailwind — payers steering volume out of the HOPD — is "
            "real, but it commoditizes the site even as it fills the chair."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Home Infusion Therapy services benefit "
                 "(21st Century Cures Act §5012)",
                 "The permanent 2021 per-visit payment for home-infusion "
                 "nursing — and its professional-present-day limitation is the "
                 "structural underpayment operators plan around.",
                 "https://www.cms.gov/medicare/payment/fee-for-service-providers/home-infusion-therapy-services"),
            Rule("Part B external-infusion-pump DME benefit + LCD",
                 "The older DME pathway covering the pump and listed infusion "
                 "drugs; overlaps and competes with the HIT benefit.",
                 "https://www.cms.gov/medicare-coverage-database/"),
            Rule("USP <797> sterile compounding / <800> hazardous drugs",
                 "The sterile-compounding standard the infusion pharmacy must "
                 "meet; a failure is a patient-safety and licensure event.",
                 "https://www.usp.org/compounding"),
            Rule("State white-bagging / brown-bagging restriction laws",
                 "A growing set of state laws limit payer mandates to supply "
                 "the drug — the legislative front line for buy-and-bill.",
                 None),
            Rule("Medicare Part B ASP payment + sequestration",
                 "Sets the ASP+add-on that is the drug margin; the sequester "
                 "cut from +6% toward +4.3% directly compresses it.",
                 "https://www.cms.gov/medicare/payment/part-b-drugs"),
            Rule("Stark / Anti-Kickback in-office ancillary services exception",
                 "Governs physician-office infusion (self-referral of the "
                 "biologic) — structure and FMV are diligence items.",
                 "https://oig.hhs.gov/compliance/physician-education/"),
        ],
        policy_watch=[
            "Legislative fixes to pay the HIT benefit on non-visit days",
            "State white-bagging bans vs. payer site-of-care mandates",
            "Biosimilar adoption reshaping buy-and-bill drug economics",
            "IRA drug-price negotiation touching infused biologics",
            "Site-neutral pressure on HOPD infusion (accelerates the shift)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Structurally fragmented beneath a few scaled names. Home infusion "
            "has one clear strategic (Option Care) plus PBM-owned arms; the "
            "ambulatory-suite segment is early and highly fragmented — a long "
            "tail of independent and physician-owned suites is exactly the PE "
            "roll-up pool."),
        hhi_or_share=(
            "No dominant share in ambulatory suites; Option Care leads home "
            "infusion but the alternate-site market is fragmented. No CMS "
            "facility census exists to compute a defensible national HHI, so it "
            "is honestly omitted."),
        consolidation=(
            "Two consolidation vectors run in parallel: Option Care rolls up "
            "home-infusion and suite assets as the strategic, and sponsors "
            "build ambulatory-suite platforms (IVX Health, Vivo Infusion) on "
            "the site-of-care arbitrage. PBM-insurers (CVS/Coram, Optum) grow "
            "their captive channels. Multiples reflect the recurring biologic "
            "annuity, discounted for white-bagging exposure."),
        pe_activity=(
            "One of the more active pharmacy-services roll-ups. Ambulatory "
            "infusion suites are the headline PE thesis — recurring biologic "
            "census, site-of-care tailwind, and a fragmented base — with IVX "
            "Health and Vivo Infusion the marquee platforms. Diligence now "
            "centers on white-bag exposure and payer contract durability more "
            "than pure census growth."),
        notable_players=[
            "Option Care Health", "CVS Health / Coram", "Optum Infusion",
            "Amerita (BrightSpring)", "KabaFusion", "Soleo Health",
            "IVX Health", "Vivo Infusion",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / chronic patient-month", "$1,000s-$10,000s",
                "Biologic and IVIG therapies carry high monthly drug revenue; "
                "the chronic book is the annuity that sets the multiple."),
            Kpi("Suite chair utilization", "60-85%",
                "For ambulatory suites the fixed-cost chassis (chairs, nurses) "
                "means margin steps up sharply with each additional infusion."),
            Kpi("Drug gross margin (buy-and-bill spread)", "low-teens % of drug",
                "Thin on a percentage basis but large in dollars — and it "
                "evaporates entirely when the payer white-bags the drug."),
            Kpi("Nursing cost / home visit", "$100-200",
                "The controllable cost of home infusion; HIT reimbursement "
                "frequently fails to cover the fully-loaded visit."),
            Kpi("Acute vs. chronic census mix", "chronic = annuity",
                "Chronic recurring therapies command a premium; an acute-heavy "
                "book is episodic and lower-quality earnings."),
            Kpi("Infusion EBITDA margin (illustrative)", "10-18%",
                "A drug-margin-plus-services blend; white-bagging and HIT "
                "underpayment are the swing factors."),
        ],
        margin_profile=(
            "Infusion margin decomposes into a drug spread and a service "
            "margin. In a buy-and-bill world the drug spread (thin percentage, "
            "large dollars) carries the P&L and the nursing/pharmacy cost is "
            "covered by administration and per-diem fees; a well-utilized "
            "ambulatory suite then earns operating leverage on the fixed chair-"
            "and-nurse chassis. Strip out buy-and-bill via white-bagging and "
            "the economics collapse toward chair rental — which is why the "
            "quality of the payer book, not the census, is the margin story."),
    ),
    risks=[
        Risk("White-bagging / payer site-of-care mandates", "High",
             "A payer supplying its own drug removes the buy-and-bill spread "
             "that carries the P&L — the single largest margin risk."),
        Risk("Medicare HIT services underpayment", "Medium",
             "The professional-present-day limitation leaves home-nursing days "
             "uncovered; a legislative fix is uncertain."),
        Risk("ASP erosion + biosimilar substitution", "Medium",
             "Falling drug prices and biosimilar switching shrink the per-unit "
             "drug dollar the spread is taken on."),
        Risk("Referral concentration + AKS exposure", "Medium",
             "Hospital-discharge and physician referral concentration, plus "
             "in-office ancillary and marketing compliance, are diligence "
             "items."),
        Risk("Infusion nursing labor supply", "Medium",
             "Home-infusion and suite nurses are scarce; wage inflation and "
             "staffing caps limit chair utilization and home capacity."),
        Risk("Acute-heavy, episodic earnings quality", "Low",
             "An anti-infective-weighted book is referral-dependent and "
             "non-recurring versus the chronic biologic annuity."),
    ],
    diligence_questions=[
        "What share of drug revenue is buy-and-bill versus white-bagged today, "
        "and what is the trajectory by top payer?",
        "What is the chronic-versus-acute census split, and how recurring is "
        "the biologic book (therapy durability, discontinuation rates)?",
        "For ambulatory suites, what is chair utilization and the fixed-cost "
        "structure per site?",
        "How exposed is the home book to the HIT services underpayment, and "
        "what is the fully-loaded nursing cost per visit?",
        "What is the top-payer concentration, and what site-of-care and "
        "white-bagging terms are in each major contract?",
        "How is referral sourcing structured (hospital discharge, physician), "
        "and does it pass Anti-Kickback / in-office ancillary scrutiny?",
        "What is the drug-margin exposure to biosimilar switching and ASP "
        "erosion across the top therapies?",
    ],
    insider_lens=[
        "The drug is the revenue and the nurse is the cost. An infusion P&L is "
        "a drug-margin business with a labor cost center attached — the "
        "Medicare HIT benefit famously pays the nursing so poorly that home "
        "economics depend on the drug spread, not the visit fee.",
        "White-bagging is the whole ballgame for suites. The day a big payer "
        "mandates its own specialty pharmacy supply the biologic, a buy-and-"
        "bill suite becomes a chair-and-nurse rental at a fraction of the "
        "margin. Underwrite the payer book, not the patient count.",
        "Site-of-care is a payer-driven tailwind, which cuts both ways. The "
        "same plans steering volume into your chairs (because the HOPD costs "
        "them 2-3x) are the ones that will white-bag the drug to capture the "
        "savings themselves.",
        "Chronic beats acute on quality of earnings. IVIG, TPN, and specialty "
        "biologics are recurring annuities; anti-infectives and hydration are "
        "episodic discharge referrals. Two suites with the same revenue can "
        "trade at very different multiples on mix alone.",
        "The ambulatory suite is oncology/dialysis-shaped — chair utilization "
        "plus drug spread — but payer-agnostic across specialties (rheum, GI, "
        "neuro, allergy/immunology), which is its edge and its commoditization "
        "risk at once.",
    ],
    connections=default_connections(
        "infusion",
        deals_sector="infusion",
        connectors=[
            ("cms_open_data_home_infusion_therapy_providers",
             "CMS Home Infusion Therapy providers — Medicare-enrolled HIT "
             "suppliers (the enrolled footprint)"),
            ("cms_open_data_part_b_spending_by_drug",
             "CMS Part B drug spending — infused J-code drug dollars and "
             "ASP trend"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — infusion pharmacy, infusion-nurse, and suite "
             "enrollment"),
            ("open_payments_general_payments_2024",
             "CMS Open Payments — manufacturer ties across infusing physicians "
             "(buy-and-bill relationship screen)"),
            ("census_acs_cbsa_profile",
             "Census ACS — commercially-insured and 65+ catchment for suite "
             "and home-territory mapping"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
        ],
    ),
    sources=[
        Source("National Home Infusion Association (NHIA) — industry survey "
               "and infusion market data", "INDUSTRY",
               "https://nhia.org/"),
        Source("CMS Home Infusion Therapy Services benefit — payment and "
               "coverage (21st Century Cures Act)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-for-service-providers/home-infusion-therapy-services"),
        Source("CMS Medicare Part B Drug Average Sales Price (ASP) files and "
               "Part B drug spending dashboard", "GOV",
               "https://www.cms.gov/medicare/payment/part-b-drugs"),
        Source("USP General Chapter <797> Pharmaceutical Compounding — Sterile "
               "Preparations", "INDUSTRY", "https://www.usp.org/compounding"),
        Source("Health Affairs / peer-reviewed research on site-of-care shift "
               "and infused-drug cost differentials", "ACADEMIC",
               "https://www.healthaffairs.org/"),
        Source("PE Desk industry deep-dive (infusion) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=infusion"),
    ],
    live_figures=live_figures_from_dive("infusion"),
    trends=(
        "Infusion has been reshaped by a decade-long, payer-driven migration "
        "of drug administration out of the hospital outpatient department. As "
        "plans discovered they were paying 2-3x more for the identical biologic "
        "in the HOPD, they began steering members to home infusion and, "
        "increasingly, freestanding ambulatory infusion suites — which turned a "
        "sleepy home-infusion sector into a growth market and spawned a wave of "
        "PE-backed suite platforms (IVX Health, Vivo) on top of the scaled "
        "strategic (Option Care) and PBM-owned arms (CVS/Coram, Optum). Two "
        "counter-currents now define the trajectory. White-bagging and payer "
        "site-of-care mandates threaten the buy-and-bill spread that carries "
        "provider margin, prompting a state-by-state legislative fight; and the "
        "2021 Medicare Home Infusion Therapy services benefit, meant to fix "
        "home-nursing payment, instead entrenched an underpayment by covering "
        "only professional-present days. Underneath, the biologic and "
        "biosimilar pipeline keeps widening the infusible drug menu, so volume "
        "growth is durable even as the per-unit margin is contested."),
    growth_levers=[
        GrowthLever(
            "Site-of-care shift (HOPD → home / suite)",
            "Payers reimburse the same biologic far less outside the hospital, "
            "so they actively move volume to home and ambulatory suites — the "
            "dominant, payer-funded demand engine.",
            "+4-6%/yr site shift", "ILLUSTRATIVE"),
        GrowthLever(
            "Biologic + biosimilar pipeline",
            "New infusible autoimmune, neurology, and immunology therapies (and "
            "biosimilar versions) widen the drug menu a suite can administer.",
            "menu expansion", "ILLUSTRATIVE"),
        GrowthLever(
            "Chronic disease prevalence",
            "Rising autoimmune, neurologic, and immunodeficiency prevalence "
            "grows the recurring chronic-infusion census.",
            "+2-3%/yr prevalence", "ILLUSTRATIVE"),
        GrowthLever(
            "Aging population (home anti-infectives / TPN)",
            "An older population lifts post-discharge home anti-infective, "
            "hydration, and parenteral-nutrition volume.",
            "demographic", "GOV"),
        GrowthLever(
            "Drug rate / ASP updates",
            "The drug component reprices with ASP updates, offset by "
            "sequestration and biosimilar erosion.",
            "+2-3%/yr rate", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Payer-driven site-of-care migration out of the HOPD",
        analysis=(
            "Unlike most subsectors, infusion's dominant demand driver is not "
            "disease incidence but a payer decision. Because commercial plans "
            "and Medicare Advantage reimburse the identical infused biologic "
            "2-3x higher in a hospital outpatient department than in a home or "
            "freestanding suite, they use benefit design, prior authorization, "
            "and outright site-of-care mandates to move members to the cheaper "
            "site. That migration converts existing HOPD infusion volume into "
            "home/suite volume — pure share shift on top of the underlying "
            "growth in chronic autoimmune, neurologic, and immunodeficiency "
            "prevalence that expands the infusible patient pool. The same force "
            "is double-edged: the payer funding the shift is also the party "
            "most motivated to white-bag the drug and keep the savings, so the "
            "volume tailwind and the margin threat share a single root cause."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Drug acquisition (buy-and-bill inventory)",
            "~55-70% of COGS",
            "The largest line by far — the medication itself. Largely a "
            "pass-through against ASP billing, but it drives working-capital "
            "intensity and evaporates from the P&L when a payer white-bags.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Nursing labor (home visits / suite chairs)",
            "the #1 controllable cost",
            "Infusion nurses administer the therapy; scarce supply and wage "
            "inflation cap home capacity and suite chair utilization.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Pharmacy / sterile-compounding operations",
            "~10-15% of cost",
            "Pharmacist labor, USP <797> cleanroom compliance, and admixture "
            "— a fixed clinical-operations base that scale spreads.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Delivery & logistics (home channel)",
            "~5-10% of cost",
            "Cold-chain drug delivery, supply logistics, and route density for "
            "the home book.", "ILLUSTRATIVE"),
        CostDriver(
            "Reimbursement operations + bad debt / denials",
            "~5-10% of cost",
            "Benefit investigation, prior auth, complex drug-plus-service "
            "billing, and denial rework — cost-to-collect is material.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national CMS infusion-suite facility census exists (the Medicare "
        "Home Infusion Therapy provider file is partial), so geography is not "
        "the structural read here — it is omitted rather than fabricated. In "
        "practice the footprint tracks commercial-life density, referral "
        "sources (hospital discharge and physician biologic prescribers), and "
        "suite catchment economics rather than a certified-facility map; use "
        "the corpus deal history and the connector datasets to triangulate "
        "presence by market."),
)

register(REPORT)
