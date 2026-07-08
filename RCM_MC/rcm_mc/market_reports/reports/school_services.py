"""School Services — school-based special-education and behavioral-health services.

Deals-only deep-dive (district contract data is local and not vendored, so
geography is omitted rather than fabricated). Consumes
``school_services_deep_dive()`` for SOURCED corpus figures where the corpus
tags them. This is a staffing-and-teletherapy spread business riding an SLP/OT/
school-psych shortage, so the sections are authored around the IDEA
related-services mandate, the Medicaid 'free care' reversal that unlocked new
billing, the bill-rate-minus-pay-rate spread, and the school-calendar
seasonality that shapes the whole P&L.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="school_services",
    name="School Services",
    care_setting="Behavioral",
    naics="621340",
    one_line_def=(
        "Contracted clinical and related services delivered in K-12 schools — "
        "speech-language pathology, occupational and physical therapy, school "
        "psychology, counseling and behavioral/mental-health support, and "
        "nursing — supplied to districts on-site or via teletherapy to meet "
        "the IEP-mandated 'related services' obligations of IDEA, and "
        "increasingly billed to Medicaid under the expanded school-based-"
        "services rules."),
    tam_headline=TamHeadline(
        value=4.0, unit="$B", growth_pct=9.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "The contracted school-based related-services + behavioral market "
            "is modeled at ~$3-5B; the anchor is a GOV figure (~7.5M US "
            "students, ~15% of enrollment, served under IDEA) times outsourced "
            "penetration and bill rates. Growth is the modeled composite of "
            "special-ed identification (+4.0%), clinician-shortage-driven "
            "outsourcing + teletherapy (+3.0%), and Medicaid 'free-care' "
            "expansion (+2.0%)."),
    ),
    executive_summary=[
        "It is a staffing-spread business at heart. Districts must provide "
        "IDEA-mandated related services (speech, OT, PT, psych, counseling) but "
        "cannot hire enough clinicians, so they contract them in — and the "
        "provider earns the spread between the district (or Medicaid) bill rate "
        "and the clinician pay rate, typically a 30-45% gross margin on the "
        "bill rate.",
        "The clinician shortage is both the constraint and the moat. SLPs, "
        "OTs, and school psychologists are in structural short supply; fill "
        "rate (open requisitions actually staffed) is the core KPI, and "
        "teletherapy is the lever that lets a national provider serve rural and "
        "hard-to-fill districts a local agency cannot.",
        "The demand is legally mandated and counter-cyclical to hiring. IDEA "
        "gives every eligible child an enforceable right to related services on "
        "an IEP, and special-education identification keeps rising (autism, "
        "speech/language, and post-COVID mental-health need) — so demand grows "
        "regardless of district budgets, which must fund the mandate.",
        "Medicaid 'free care' reform is the reimbursement unlock. CMS's "
        "reversal of the free-care policy (2014, expanded 2023) lets schools "
        "bill Medicaid for covered services to all Medicaid-enrolled students, "
        "not just those with an IEP — a materially larger billable base that "
        "changes district willingness to fund and contract services.",
        "The P&L runs on the school calendar. Revenue is concentrated in the "
        "~9-10 month academic year with a summer trough, so seasonality, "
        "contract-renewal timing, and clinician retention across the summer are "
        "structural features every model must absorb.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Student evaluation + IEP / 504 plan specifies mandated related "
            "services and minutes",
            "District identifies a staffing gap it cannot fill with employees",
            "Contract with a school-services provider (staffing, per-student, "
            "or hourly) — often via RFP",
            "Clinician placement (on-site or teletherapy) matched to the "
            "district's caseload and schedule",
            "Service delivery + documentation of IEP minutes and progress",
            "Medicaid school-based-services claiming (where the student is "
            "Medicaid-enrolled and the service is covered)",
            "Billing the district and/or Medicaid; contract renewal for the "
            "next school year",
        ],
        sites_of_care=[
            "On-site in the K-12 school (the traditional model)",
            "Teletherapy / virtual delivery (rural + hard-to-fill roles — the "
            "growth lever)",
            "Early-intervention / preschool special-education settings",
            "Home-based services for eligible students (as IEP requires)",
            "Districts, charter networks, and special-education cooperatives "
            "(the contracting counterparties)",
        ],
        money_flow=(
            "Two revenue mechanisms sit on top of the same clinician hour. The "
            "primary one is the district contract: a school system pays the "
            "provider a bill rate — per hour, per student, or per filled "
            "position — out of its IDEA Part B and state/local education "
            "dollars, and the provider pays the clinician a lower pay rate, "
            "keeping the spread (typically a 30-45% gross margin on the bill "
            "rate for a staffing model). The second, increasingly important, is "
            "Medicaid school-based services: since CMS reversed the 'free care' "
            "policy (2014, broadly expanded in 2023), schools can bill Medicaid "
            "for covered health services delivered to Medicaid-enrolled students "
            "— no longer limited to those with an IEP — plus Medicaid "
            "administrative claiming, which offsets district cost and enlarges "
            "the billable base. Because the underlying obligation (IDEA-mandated "
            "related services) is legally enforceable and unfunded relative to "
            "clinician supply, districts are effectively compelled buyers, and "
            "the provider's economics are the spread on a scarce clinician hour "
            "across the ~9-10 month school year."),
        key_players=(
            "A fragmented staffing/services field consolidating around a few "
            "platforms: Presence (formerly PresenceLearning, the teletherapy "
            "leader), Cross Country Education / Sunbelt Staffing, EBS "
            "Healthcare, ProCare Therapy, Ro Health, TinyEYE, Parallel Learning, "
            "and Huddle Up, alongside large healthcare-staffing firms with K-12 "
            "divisions. Counterparties are school districts, charter networks, "
            "and regional special-education cooperatives; the professional "
            "supply (SLPs, OTs, PTs, school psychologists) is credentialed "
            "through ASHA/AOTA and state education agencies. The acquirable pool "
            "is the long tail of regional staffing agencies and teletherapy "
            "providers."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Contracted school related-services + behavioral (modeled)",
                    "~$3-5B", "ILLUSTRATIVE · outsourced-penetration × bill-rate "
                    "model"),
            Segment("US students served under IDEA", "~7.5M (~15% of K-12)",
                    "GOV · US Dept. of Education / IDEA child count"),
            Segment("Speech-language the largest related-services line",
                    "leading discipline",
                    "GOV · IDEA related-services distribution"),
            Segment("Teletherapy share of delivery", "rising fast",
                    "ILLUSTRATIVE · delivery-model shift, directional"),
            Segment("Medicaid school-based-services billable base",
                    "expanded beyond IEP students",
                    "GOV · CMS free-care reversal (2014/2023)"),
        ],
        growth_drivers=[
            "Rising special-education identification ~4.0%/yr",
            "Clinician shortage → outsourcing + teletherapy ~3.0%/yr",
            "Medicaid 'free-care' expansion enlarging the billable base ~2.0%",
            "Post-COVID student mental-health need + ESSER-seeded demand",
            "IDEA mandate compelling districts to fund unmet services",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "District contract (IDEA Part B + state/local)": 0.70,
            "Medicaid school-based services + admin claiming": 0.25,
            "Grants / ESSER / other": 0.05,
        },
        rate_mechanics=[
            "District staffing/service contracts — bill rate per hour, per "
            "student, or per filled position, funded from IDEA Part B and "
            "state/local education budgets; the provider keeps the bill-rate-"
            "minus-pay-rate spread.",
            "Medicaid school-based services (SBS) — fee-for-service or "
            "cost-reconciled claiming for covered services to Medicaid-enrolled "
            "students; the CMS free-care reversal expanded eligibility beyond "
            "IEP-only students.",
            "Medicaid Administrative Claiming (MAC) — reimbursement for "
            "outreach, coordination, and administrative activities supporting "
            "Medicaid-covered services.",
            "IDEA Part B federal funding — the special-education money that, "
            "with state/local dollars, funds the related-services mandate "
            "districts contract out.",
            "Per-student / per-diem teletherapy models — virtual delivery "
            "priced by caseload or session, extending reach into hard-to-fill "
            "districts.",
            "Seasonal contract structure — revenue keyed to the ~9-10 month "
            "academic year, with extended-school-year (ESY) services a smaller "
            "summer stream.",
        ],
        reimbursement_risk=(
            "The reimbursement picture is unusually favorable on demand and "
            "unusually operational on risk. Demand is legally compelled — IDEA "
            "makes related services an enforceable right — and the Medicaid "
            "free-care reversal enlarged the billable base, so the top-line "
            "drivers are structural tailwinds. The risks are execution and "
            "funding-mix rather than rate collapse. District budgets are the "
            "primary payer and are subject to local funding cycles and the "
            "wind-down of one-time federal ESSER pandemic dollars that inflated "
            "recent behavioral-health spend; Medicaid SBS billing is "
            "administratively complex and varies state to state, with "
            "documentation, provider-qualification, and cost-reconciliation "
            "requirements that can trigger recoupment if mishandled. The "
            "deepest structural exposure is on the supply side: because the "
            "business is a spread on a scarce clinician hour, a tightening SLP/"
            "OT labor market compresses margin (pay rates rise faster than "
            "district bill rates can be renegotiated) even as demand climbs. "
            "Teletherapy mitigates supply risk but carries its own state "
            "licensure and district-acceptance constraints."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Individuals with Disabilities Education Act (IDEA)",
                 "Guarantees a free appropriate public education and mandates "
                 "IEP-specified related services — the enforceable demand "
                 "obligation that compels districts to buy these services.",
                 "https://sites.ed.gov/idea/"),
            Rule("Medicaid 'free care' policy reversal (CMS 2014, expanded 2023)",
                 "Let schools bill Medicaid for covered services to all "
                 "Medicaid-enrolled students, not just IEP students — the "
                 "reimbursement unlock that enlarged the billable base.",
                 "https://www.medicaid.gov/medicaid/financial-management/medicaid-administrative-claiming/schools/index.html"),
            Rule("Section 504 of the Rehabilitation Act / ADA",
                 "Obligates districts to provide accommodations and related "
                 "services to students with disabilities beyond IDEA "
                 "eligibility.",
                 "https://www.ed.gov/laws-and-policy/individuals-disabilities/section-504"),
            Rule("State educator/clinician licensure + ASHA/AOTA certification",
                 "SLPs, OTs, PTs, and school psychologists must hold state "
                 "education-agency credentials and professional certification — "
                 "governing who can deliver and be billed.",
                 None),
            Rule("Teletherapy + interstate licensure (state rules, ASLP-IC)",
                 "State telepractice rules and interstate compacts (e.g. the "
                 "Audiology & Speech-Language Pathology Interstate Compact) "
                 "govern virtual delivery across state lines.",
                 "https://aslpcompact.com/"),
        ],
        policy_watch=[
            "State Medicaid school-based-services expansion after the 2023 CMS "
            "guidance",
            "ESSER pandemic-funding wind-down and its effect on district "
            "behavioral spend",
            "IDEA funding levels and the persistent federal-share shortfall",
            "Teletherapy acceptance rules and interstate-licensure compacts",
            "Special-education identification and mental-health-in-schools "
            "mandates",
            "State educator-shortage and alternative-credentialing policy",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Highly fragmented — thousands of local and regional staffing "
            "agencies, independent contractors, and district in-house programs, "
            "with a handful of national platforms emerging around teletherapy "
            "and multi-state staffing. Fragmentation is a labor artifact: the "
            "service is a credentialed clinician's time delivered to a local "
            "district, so scale advantages accrue to clinician sourcing, "
            "credentialing, scheduling, and — decisively — teletherapy reach "
            "into markets a local agency cannot staff."),
        hhi_or_share=(
            "No national concentration; even the leading platforms hold modest "
            "shares of a fragmented district-by-district market. District "
            "contract data is local and not vendored, so operator concentration "
            "is honestly not measured here — the deal corpus below is the real "
            "trading history."),
        consolidation=(
            "Consolidation is underway around two theses: multi-state staffing "
            "roll-ups (Cross Country Education/Sunbelt, EBS Healthcare, ProCare, "
            "Ro Health) assembling clinician supply and district relationships, "
            "and teletherapy platforms (Presence, TinyEYE, Parallel Learning) "
            "using virtual delivery to scale a national footprint without local "
            "offices. The tailwinds — shortage-driven outsourcing and Medicaid "
            "free-care expansion — make the sector attractive to acquirers of "
            "regional agencies with sticky district contracts."),
        pe_activity=(
            "Active and growing. The thesis is a resilient, mandate-driven "
            "demand base plus a fragmented supply side ripe for roll-up and "
            "teletherapy scale. Diligence centers on clinician fill rate and "
            "retention, the bill-rate-to-pay-rate spread and its trend, district-"
            "contract renewal and concentration, Medicaid-SBS billing execution "
            "by state, and exposure to the ESSER funding cliff in the "
            "behavioral-health lines."),
        notable_players=[
            "Presence (PresenceLearning)", "Cross Country Education / Sunbelt "
            "Staffing", "EBS Healthcare", "ProCare Therapy", "Ro Health",
            "TinyEYE", "Parallel Learning", "Huddle Up",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Bill-rate-to-pay-rate spread (gross margin)",
                "30-45% of bill rate",
                "The core economic engine — the markup on a placed clinician "
                "hour; its trend tracks the clinician labor market."),
            Kpi("Fill rate (requisitions staffed ÷ opened)", "the core KPI",
                "How much contracted demand the provider can actually staff — "
                "the binding constraint in a shortage market."),
            Kpi("Clinician utilization (billable ÷ paid hours)", "70-90%",
                "Non-billable time (travel between schools, documentation) is "
                "pure cost; teletherapy raises it."),
            Kpi("Contract renewal rate", "high when staffed well",
                "District relationships are sticky if fill and quality hold; "
                "renewal timing drives the annual revenue base."),
            Kpi("Teletherapy mix", "rising",
                "Virtual delivery lifts reach, fill rate, and utilization in "
                "hard-to-staff and rural districts."),
            Kpi("Seasonality (academic-year concentration)", "~9-10 months",
                "Revenue concentrates in the school year with a summer trough — "
                "a structural cash-flow and retention feature."),
        ],
        margin_profile=(
            "School-services margin is a staffing spread modulated by "
            "utilization and seasonality. Gross margin is the district (or "
            "Medicaid) bill rate minus the clinician pay rate — typically 30-45% "
            "of the bill rate for a staffing model — earned across the ~9-10 "
            "month academic year, with the summer trough a structural drag on "
            "annualized margin and a retention challenge. The spread is directly "
            "exposed to the clinician labor market: in a tightening SLP/OT/"
            "school-psych market, pay rates rise faster than multi-year district "
            "bill rates can be reset, compressing margin even as demand grows. "
            "The levers that protect and expand margin are fill rate (unstaffed "
            "requisitions earn nothing), clinician utilization (minimizing "
            "non-billable travel and documentation, which teletherapy improves), "
            "and Medicaid-SBS capture (adding a reimbursement stream on top of "
            "the district contract). Tech-enabled and teletherapy-heavy models "
            "run structurally higher margins than pure on-site staffing by "
            "raising utilization and reaching hard-to-fill, higher-rate "
            "districts."),
    ),
    risks=[
        Risk("Clinician shortage — SLP/OT/school-psych supply & pay inflation",
             "High",
             "The binding constraint; rising pay rates compress the spread the "
             "whole model depends on."),
        Risk("District-budget + ESSER funding-cliff exposure", "High",
             "One-time federal pandemic dollars inflated behavioral spend; "
             "their wind-down pressures district contracting."),
        Risk("Medicaid-SBS billing complexity + recoupment", "Medium",
             "State-by-state documentation, provider-qualification, and cost-"
             "reconciliation rules carry audit and recoupment exposure."),
        Risk("Contract concentration + renewal / re-bid risk", "Medium",
             "Revenue can concentrate in large district contracts subject to "
             "annual renewal and competitive RFP re-bid."),
        Risk("Seasonality + summer retention", "Medium",
             "Academic-year revenue concentration and summer clinician "
             "attrition strain cash flow and staffing continuity."),
        Risk("Teletherapy acceptance + interstate licensure", "Low",
             "District willingness to use virtual delivery and cross-state "
             "licensure rules can limit the teletherapy growth lever."),
    ],
    diligence_questions=[
        "What is the bill-rate-to-pay-rate spread by discipline, and how has it "
        "trended against clinician pay inflation?",
        "What is the fill rate (staffed ÷ opened requisitions) and clinician "
        "retention, including across the summer?",
        "What is the district-contract concentration, renewal rate, and re-bid "
        "schedule?",
        "What share of revenue is district-funded vs Medicaid SBS, and how "
        "reliable is the Medicaid billing execution by state?",
        "How exposed are the behavioral-health lines to the ESSER funding "
        "cliff?",
        "What is the teletherapy mix, and what does it do to fill rate, "
        "utilization, and margin?",
        "What is clinician utilization (billable ÷ paid), and how much "
        "non-billable travel/documentation time is carried?",
        "What is the licensure/credentialing compliance posture, including "
        "interstate teletherapy?",
    ],
    insider_lens=[
        "Demand is a legal mandate, not a sales cycle. IDEA gives every "
        "eligible child an enforceable right to the related services on the IEP, "
        "and districts cannot hire enough clinicians to deliver them — so the "
        "district is a compelled buyer, and the real question is never whether "
        "there is demand but whether the provider can staff it.",
        "It is a staffing spread, so the clinician labor market IS the P&L. The "
        "margin is the bill rate minus the pay rate on a scarce SLP or OT hour; "
        "when the shortage tightens, pay rates rise faster than multi-year "
        "district bill rates reset, and the spread quietly compresses even while "
        "demand booms. Underwrite the spread trend, not the headcount growth.",
        "Teletherapy is the moat, not a feature. Virtual delivery lets a "
        "national provider staff rural and hard-to-fill districts a local "
        "agency simply cannot — raising fill rate, utilization, and access to "
        "higher-rate markets. The platforms that scale are the ones that solved "
        "virtual delivery and credentialing, not the ones with the most local "
        "offices.",
        "The Medicaid free-care reversal is an underappreciated unlock. By "
        "letting schools bill Medicaid for covered services to all Medicaid-"
        "enrolled students — not just IEP students — CMS enlarged the billable "
        "base and changed district willingness to fund and contract services. "
        "State-by-state SBS execution is where that money is actually captured.",
        "Watch the ESSER cliff in the behavioral lines. A chunk of recent "
        "school mental-health demand was seeded by one-time federal pandemic "
        "relief; as that money winds down, the durable question is which "
        "behavioral-services revenue converts to recurring district or Medicaid "
        "funding and which evaporates.",
        "The calendar is a balance-sheet fact. Revenue concentrates in the "
        "9-10 month school year with a summer trough, so seasonality, "
        "extended-school-year work, and summer clinician retention are "
        "structural features every model must manage — annualized margins that "
        "ignore the trough overstate the business.",
    ],
    connections=default_connections(
        "school_services",
        deals_sector="behavioral_health",
        extra_pages=[
            ("/industry/school_services",
             "Industry deep-dive — school-services deal history + structure"),
        ],
        connectors=[
            ("census_acs_county_profile",
             "Census ACS — school-age population & disability by county, the "
             "demand denominator"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — SLP, OT, PT, and school-psychology supply (the "
             "labor market)"),
            ("hrsa_data_hpsa_mental_health",
             "HRSA Mental-Health HPSAs — shortage geography that drives "
             "outsourcing + teletherapy"),
            ("medicaid_data_enrollment_monthly",
             "Medicaid enrollment — the child base for school-based-services "
             "billing"),
            ("bls_qcew_industry_area",
             "BLS QCEW — therapy/education-services wages & employment by area"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded providers (billing-integrity screen)"),
        ],
    ),
    sources=[
        Source("US Department of Education — IDEA Part B child count and "
               "related-services data", "GOV", "https://sites.ed.gov/idea/"),
        Source("CMS — Medicaid and School-Based Services (the 'free care' "
               "policy reversal and 2023 guidance)", "GOV",
               "https://www.medicaid.gov/medicaid/financial-management/medicaid-administrative-claiming/schools/index.html"),
        Source("NCES — Digest of Education Statistics (special-education "
               "enrollment and staffing)", "GOV", "https://nces.ed.gov/"),
        Source("ASHA — schools survey and SLP-workforce shortage data",
               "INDUSTRY", "https://www.asha.org/"),
        Source("American Occupational Therapy Association (AOTA) — school "
               "practice and workforce", "INDUSTRY", "https://www.aota.org/"),
        Source("PE Desk industry deep-dive (school services) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=school_services"),
    ],
    live_figures=live_figures_from_dive("school_services"),
    trends=(
        "School-based services grew from a patchwork of local staffing "
        "arrangements into a fast-consolidating, teletherapy-enabled market on "
        "the back of a widening gap between mandated demand and clinician "
        "supply. The demand floor is legal: IDEA guarantees eligible students "
        "the related services written into their IEPs, and special-education "
        "identification has climbed for years — roughly 7.5 million students, "
        "about 15% of K-12 enrollment, now qualify, led by speech/language, "
        "specific learning disabilities, and a rising autism and mental-health "
        "share. Districts cannot hire enough SLPs, OTs, and school "
        "psychologists to meet that obligation, so they contract it out — and "
        "teletherapy, proven at scale during COVID, became the mechanism that "
        "let national providers reach the rural and hard-to-fill districts "
        "local agencies could not staff. Two funding shifts reshaped the "
        "economics: the CMS 'free care' reversal (2014, broadly expanded in "
        "2023) let schools bill Medicaid for covered services to all Medicaid-"
        "enrolled students rather than only IEP students, enlarging the billable "
        "base; and one-time federal ESSER pandemic relief poured money into "
        "school mental health, seeding behavioral-services demand now facing a "
        "wind-down. The forward story is roll-up of a fragmented staffing base, "
        "teletherapy-driven margin and reach, state-by-state Medicaid-SBS "
        "capture, and a clinician labor market whose tightness both fuels the "
        "outsourcing thesis and pressures the spread it runs on."),
    growth_levers=[
        GrowthLever(
            "Rising special-education identification",
            "Growing IDEA-eligible enrollment (autism, speech/language, and "
            "post-COVID mental-health need) expands the mandated caseload "
            "districts must serve.",
            "+4.0%/yr caseload", "GOV"),
        GrowthLever(
            "Clinician shortage → outsourcing + teletherapy",
            "Districts short of SLPs/OTs/school psychologists contract services "
            "in, and teletherapy extends reach into hard-to-staff markets.",
            "+3.0%/yr outsourced", "ILLUSTRATIVE"),
        GrowthLever(
            "Medicaid 'free-care' expansion",
            "Billing Medicaid for covered services to all Medicaid-enrolled "
            "students (not just IEP students) enlarges the reimbursable base.",
            "+2.0%/yr billable base", "GOV"),
        GrowthLever(
            "Post-COVID student mental-health need (ESSER-seeded)",
            "Elevated student mental-health demand, initially funded by "
            "one-time federal relief, expanded the behavioral-services line.",
            "demand pull", "ILLUSTRATIVE"),
        GrowthLever(
            "Clinician pay inflation (spread drag)",
            "A tightening SLP/OT labor market lifts pay rates faster than "
            "district bill rates reset, compressing the staffing spread.",
            "−margin", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="IDEA-mandated special-education caseload, gated by clinician "
               "supply",
        analysis=(
            "The demand base is the population of students entitled to related "
            "services under IDEA — roughly 7.5 million children, about 15% of "
            "US K-12 enrollment, served under the Act, a share that has risen "
            "steadily as autism, speech/language, and mental-health "
            "identification grew and as post-COVID need pushed behavioral "
            "referrals higher. Critically, this demand is legally mandated and "
            "budget-insensitive on the obligation side: a district must provide "
            "the services on a child's IEP regardless of whether it can afford "
            "or staff them, which makes districts compelled buyers when they "
            "cannot hire the clinicians themselves. The binding constraint on "
            "realized volume is therefore the supply of credentialed SLPs, OTs, "
            "PTs, and school psychologists, which is in structural shortage — so "
            "the outsourced market grows as the gap between mandated caseload "
            "and district hiring widens, and teletherapy expands realized volume "
            "by unlocking clinician capacity that on-site delivery cannot reach. "
            "Underwriting should model growth off the mandated-caseload-minus-"
            "district-hiring gap and the provider's fill rate, not off district "
            "budgets alone."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Clinician compensation (SLP/OT/PT/psych pay rates)",
            "~55-68% of cost",
            "The dominant cost and the pay side of the spread; a tightening "
            "labor market raises it faster than bill rates reset.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Recruiting, credentialing & clinician onboarding",
            "~8-14% of cost",
            "Sourcing scarce clinicians and clearing state education-agency "
            "credentialing and background checks before they can bill.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Teletherapy / technology platform",
            "~5-10% of cost",
            "The virtual-delivery, scheduling, and documentation platform that "
            "raises utilization and reach — the margin-and-moat investment.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Non-billable clinician time (travel, documentation, IEP meetings)",
            "utilization drag",
            "Inter-school travel, required documentation, and IEP participation "
            "are paid but not billed — teletherapy compresses this line.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing, Medicaid-SBS compliance & G&A",
            "~6-11% of cost",
            "District invoicing plus the state-specific Medicaid school-based-"
            "services documentation and cost-reconciliation overhead.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "District contract data is local and not vendored — school services are "
        "purchased district by district with no national provider file — so "
        "state geography is omitted rather than fabricated. State is, however, a "
        "real variable: each state sets its Medicaid school-based-services "
        "policy and rates (and how fully it adopted the free-care expansion), "
        "its educator/clinician credentialing rules, and its telepractice and "
        "interstate-compact posture, while the local SLP/OT labor market and "
        "special-education identification rates vary widely. The Census "
        "school-age-population, NPI-taxonomy, HRSA-shortage, and Medicaid-"
        "enrollment connectors linked below are the honest way to map the demand "
        "denominator, clinician supply, and billable base by geography."),
)

register(REPORT)
