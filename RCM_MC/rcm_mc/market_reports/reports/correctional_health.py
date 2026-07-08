"""Correctional Health — medical, mental-health & dental care behind the wall.

Deals-only market-report module (no vendored BJS facility file, so no computed
state_breakdown or supply trend; the sector's corpus deal history is thin, so
``live_figures`` may be empty offline — the report leans on the qualitative
deep sections). The qualitative sections are authored around the two facts that
define correctional health: it is the ONLY care setting with a constitutional
right to care (Estelle v. Gamble — deliberate indifference violates the Eighth
Amendment), which makes litigation the defining risk; and it is an insurance
business — most contracts are capitated (per-inmate-per-month), so the vendor
bears utilization risk on a sick, aging population with catastrophic offsite
hospitalization as the tail. The Medicaid Inmate Exclusion (and the new §1115
reentry-waiver wave that partially breaches it) is the structural payer story.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="correctional_health",
    name="Correctional Health",
    care_setting="Other services",
    one_line_def=(
        "Medical, mental-health, dental, and pharmacy care delivered to "
        "incarcerated people in county/local jails, state prisons, federal "
        "facilities (BOP), and ICE detention — typically contracted to "
        "specialist vendors under capitated (per-inmate-per-month) or "
        "cost-plus agreements, and defined by a constitutional obligation to "
        "provide care under Estelle v. Gamble."),
    tam_headline=TamHeadline(
        value=13.0, unit="$B", growth_pct=4.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled total US correctional-healthcare spend across state DOCs, "
            "county/local jails, and federal facilities. The nearest published "
            "anchor is Pew's state-prison health-spending work (~$8B for state "
            "prisons alone, a dated figure); jails and federal add the rest. "
            "Growth is the modeled composite — a flat-to-declining incarcerated "
            "population offset by rising acuity (aging inmates, chronic disease, "
            "MH/SUD), pharmacy (Hep C, MOUD), and the §1115 reentry shift."),
    ),
    executive_summary=[
        "It is the only care setting with a constitutional right to care. "
        "Estelle v. Gamble (1976) makes deliberate indifference to serious "
        "medical needs an Eighth Amendment violation — so the buyer cannot say "
        "no, but litigation (wrongful death, ADA, mental health) and DOJ "
        "consent decrees are the defining risk, not demand.",
        "Most contracts are capitated (per-inmate-per-month), so the vendor "
        "runs an insurance business: it bears utilization risk on a sick, "
        "aging, high-acuity population, with catastrophic offsite "
        "hospitalization the tail. The 'man-day' rate and the stop-loss "
        "structure are the whole underwrite.",
        "The population is FLAT to declining — incarceration rates have fallen "
        "since the ~2008 peak — so growth is not headcount. It is acuity per "
        "inmate: aging, chronic disease, mental illness, substance use, and "
        "mandated treatments (Hep C cure, medication for opioid use disorder).",
        "Medicaid generally does NOT pay during incarceration (the Medicaid "
        "Inmate Exclusion), so the government/vendor eats nearly all cost. The "
        "new §1115 reentry-waiver wave (CalAIM and ~20+ states) partially "
        "breaches that exclusion for pre-release care — a genuine regime change "
        "for the economics.",
        "This is a distressed, litigation-heavy sector: Wellpath filed Chapter "
        "11 in late 2024 and Corizon's bankruptcy reshaped the field — a "
        "cautionary tale on capitated risk plus liability plus staffing "
        "shortages in remote facilities.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Contract award — competitive procurement by a state DOC, county/"
            "jail authority, or federal agency (often capitated per-inmate)",
            "Intake screening — medical/MH/SUD assessment at booking, "
            "medication continuity, communicable-disease screening",
            "On-site primary & urgent care — clinic, sick call, chronic-disease "
            "management, dental, and 24/7 nursing coverage",
            "Mental health & SUD — psychiatric care, crisis/suicide watch, and "
            "medication for opioid use disorder (MOUD)",
            "Offsite & specialty — community-hospital transfers, specialty "
            "consults, and the catastrophic-cost tail (stop-loss)",
            "Pharmacy — chronic meds, HIV/Hep C, psychotropics, and MOUD "
            "(a fast-rising line)",
            "Reentry / transitions — discharge planning and, under §1115 "
            "waivers, pre-release Medicaid-covered services",
        ],
        sites_of_care=[
            "County & local jails (high churn, short stays, intake-heavy)",
            "State prisons / DOC facilities (longer stays, chronic & geriatric)",
            "Federal (Bureau of Prisons) and ICE detention",
            "Community hospitals & specialists (offsite — the cost tail)",
            "Telehealth (psychiatry, specialty — the access & margin frontier)",
        ],
        money_flow=(
            "The vendor is paid by the GOVERNMENT — a state department of "
            "corrections, a county/jail authority, or a federal agency — not by "
            "a health plan. The dominant structure is capitation: a "
            "per-inmate-per-month (or 'man-day') rate under which the vendor "
            "assumes utilization risk for on-site care and, depending on the "
            "contract, some or all offsite hospitalization, usually with "
            "aggregate and specific stop-loss to cap the catastrophic tail. "
            "Cost-plus and management-fee structures shift utilization risk back "
            "to the government. Crucially, federal Medicaid, Medicare, and "
            "Marketplace coverage are suspended during incarceration under the "
            "Medicaid Inmate Exclusion (with a narrow exception for inpatient "
            "hospital stays over 24 hours in many states), so historically the "
            "government/vendor absorbed nearly all cost. The §1115 reentry "
            "waivers now let Medicaid pay for a limited pre-release benefit — "
            "introducing, for the first time, a third-party payer into a "
            "Medicaid-excluded setting."),
        key_players=(
            "A concentrated set of specialist vendors: Wellpath (the largest, "
            "which filed Chapter 11 in late 2024), Centurion (a Centene-linked "
            "operator), YesCare (the successor to Corizon), VitalCore Health "
            "Strategies, NaphCare, and Armor Health. Several state systems run "
            "care in-house or via academic partnerships (UTMB in Texas, UConn, "
            "UMass). The addressable pool is the contracted-vendor book plus "
            "states considering privatization — but contract wins and losses "
            "are frequently political, not performance-driven."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("State prison healthcare spend (the published anchor)",
                    "~$8B (state prisons; dated)",
                    "GOV/ACADEMIC · Pew Charitable Trusts state-prison health "
                    "spending"),
            Segment("Total US correctional-healthcare spend (all settings)",
                    "~$13B (modeled)",
                    "ILLUSTRATIVE · state + jail + federal build"),
            Segment("Incarcerated population (the volume base)",
                    "~1.9-2.0M incarcerated",
                    "GOV · Bureau of Justice Statistics"),
            Segment("Contracted-vendor vs. in-house / academic split",
                    "concentrated vendor set; states split both ways",
                    "INDUSTRY · sector structure"),
        ],
        growth_drivers=[
            "Aging inmate population + acuity — geriatric, chronic-disease, and "
            "MH/SUD burden raise cost and required services per inmate",
            "Pharmacy — Hepatitis C cure (DAAs), HIV, psychotropics, and MOUD "
            "mandates lift the drug line",
            "§1115 Medicaid reentry waivers — new pre-release Medicaid revenue "
            "and reentry/care-coordination services",
            "Telehealth adoption — expands access in remote facilities and "
            "supports margin",
            "Litigation & political risk — a negative lever pressuring margin "
            "and driving contract turnover",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "State departments of corrections (DOC)": 0.55,
            "County / local jail authorities": 0.30,
            "Federal (BOP / ICE / USMS)": 0.12,
            "Medicaid (inpatient exception / §1115 reentry)": 0.03,
        },
        rate_mechanics=[
            "Capitation / per-inmate-per-month (or 'man-day') — the dominant "
            "model; the vendor bears utilization risk. (Shares above are "
            "ILLUSTRATIVE revenue-by-government-payer — who funds the vendor — "
            "reflecting the settings a diversified book serves.)",
            "Stop-loss — aggregate and specific (per-case) caps that ring-fence "
            "the catastrophic offsite-hospitalization tail; the structure that "
            "makes capitation underwritable.",
            "Cost-plus / management fee — shifts utilization risk back to the "
            "government; common where a government keeps clinical risk.",
            "Medicaid Inmate Exclusion (SSA §1905(a)(A)) — federal Medicaid/"
            "Medicare/Marketplace are suspended during incarceration, except a "
            "narrow inpatient-hospital (>24h) exception in many states.",
            "§1115 reentry waivers + the Medicaid Reentry Act / CAA-2023 "
            "juvenile mandate — Medicaid may now cover a limited pre-release "
            "benefit (up to 90 days), introducing a third-party payer.",
            "Community-hospital offsite care is billed to the vendor/government "
            "at negotiated or chargemaster-adjacent rates — the single biggest "
            "source of cost variance.",
        ],
        reimbursement_risk=(
            "The economic risk is utilization risk plus litigation, not payer "
            "rate. Under capitation the vendor is effectively an insurer for a "
            "population that is sicker, older, and higher-acuity than the "
            "outside world — high rates of chronic disease, mental illness, "
            "substance use, HIV, and Hepatitis C — with catastrophic offsite "
            "hospitalizations as a fat tail that stop-loss only partly tames. A "
            "single wrongful-death verdict, an ADA/mental-health class action, "
            "or a DOJ consent decree can swamp a contract's margin, and "
            "reserves for claims and liability insurance are first-order. The "
            "§1115 reentry waivers help by shifting some pre-release cost to "
            "Medicaid, but add billing and compliance complexity to a workforce "
            "already stretched by staffing shortages in remote facilities."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Estelle v. Gamble, 429 U.S. 97 (1976) — Eighth Amendment",
                 "Deliberate indifference to a prisoner's serious medical needs "
                 "is cruel and unusual punishment — the constitutional duty to "
                 "provide care and the source of the sector's litigation risk.",
                 "https://supreme.justia.com/cases/federal/us/429/97/"),
            Rule("Medicaid Inmate Exclusion (SSA §1905(a)(A))",
                 "Suspends federal Medicaid/Medicare/Marketplace payment during "
                 "incarceration (narrow inpatient exception) — why the "
                 "government/vendor historically absorbed nearly all cost.",
                 "https://www.medicaid.gov/"),
            Rule("§1115 reentry waivers + Medicaid Reentry Act / CAA-2023",
                 "Let Medicaid cover a limited pre-release benefit and mandate "
                 "juvenile pre-release/post-release coverage — the regime change "
                 "in the sector's payer structure.",
                 "https://www.medicaid.gov/medicaid/section-1115-demonstrations/index.html"),
            Rule("NCCHC / ACA accreditation standards",
                 "The National Commission on Correctional Health Care and ACA "
                 "standards are the de-facto quality benchmark and a common "
                 "contract requirement and litigation reference.",
                 "https://www.ncchc.org/"),
            Rule("PLRA + DOJ CRIPA consent decrees; ADA / PREA health duties",
                 "The Prison Litigation Reform Act, DOJ investigations of "
                 "unconstitutional conditions, and ADA/PREA obligations shape "
                 "liability and mandated care.",
                 "https://www.justice.gov/crt/rights-persons-confined-jails-and-prisons"),
        ],
        policy_watch=[
            "§1115 reentry-waiver approvals and go-lives state by state",
            "MOUD (medication for opioid use disorder) access mandates & "
            "litigation",
            "Hepatitis C treatment-access class actions and DAA cost",
            "DOJ CRIPA investigations and new consent decrees",
            "State privatization / in-sourcing decisions and procurement cycles",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "The vendor layer is concentrated — a handful of national "
            "specialists (Wellpath, Centurion, YesCare, VitalCore, NaphCare, "
            "Armor) compete for state DOC and large-jail contracts — but the "
            "overall market is split with in-house and academic operators, and "
            "structured contract-by-contract. No BJS facility file is vendored, "
            "so geography is honestly omitted; the (thin) corpus deal history "
            "stands in its place below."),
        hhi_or_share=(
            "Concentrated among a few national vendors for the large-contract "
            "book, but 'share' is a portfolio of individual government "
            "contracts, and states swing between privatized and in-house "
            "delivery — so measured concentration overstates durability."),
        consolidation=(
            "Consolidated but distressed. Wellpath (backed by H.I.G. Capital) "
            "scaled into the largest operator and then filed Chapter 11 in late "
            "2024 under litigation and cost pressure; Corizon's controversial "
            "bankruptcy (the 'Texas Two-Step' via Tehum Care) reshaped the "
            "field and left YesCare as successor. The sector's history is a "
            "warning on levering a capitated, litigation-exposed business."),
        pe_activity=(
            "PE has owned the major platforms (H.I.G./Wellpath, and the "
            "Corizon lineage), but the recent record — bankruptcies, consent "
            "decrees, and reputational scrutiny — has cooled sponsor appetite. "
            "The thesis (a captive, constitutionally-mandated demand base with "
            "capitated economics) runs headlong into the reality (utilization "
            "risk on a sick population, catastrophic offsite tails, litigation, "
            "staffing shortages, and political contract turnover)."),
        notable_players=[
            "Wellpath (Chapter 11, 2024)", "Centurion", "YesCare (ex-Corizon)",
            "VitalCore Health Strategies", "NaphCare", "Armor Health",
            "UTMB / academic-affiliated systems", "In-house state DOC programs",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Per-inmate-per-month (PIPM) / man-day rate", "contract-set",
                "The capitated price and the core underwrite — must cover a "
                "high-acuity population plus the offsite tail."),
            Kpi("Offsite hospitalization rate & cost", "the variance driver",
                "Community-hospital transfers at high unit cost are the biggest "
                "source of margin variance — stop-loss caps only part."),
            Kpi("Medical loss ratio (capitated contracts)", "the margin lever",
                "Care cost as a share of the capitated rate — the insurance-"
                "style profitability measure."),
            Kpi("Clinical staffing vacancy rate", "chronically high",
                "RN and psychiatry vacancies in remote facilities cap quality, "
                "drive locum premiums, and raise liability."),
            Kpi("Litigation frequency & claims reserves", "portfolio risk",
                "Wrongful-death, ADA, and mental-health claims — the reserve and "
                "insurance line that can swamp a contract."),
            Kpi("Pharmacy cost per inmate", "fast-rising",
                "Hep C DAAs, HIV, psychotropics, and MOUD push the drug line — "
                "often the fastest-growing cost."),
        ],
        margin_profile=(
            "Correctional-health margin is a capitated insurance margin net of "
            "litigation. Revenue is fixed by the per-inmate-per-month rate, so "
            "profitability turns on the medical loss ratio — how well the "
            "vendor manages on-site care, controls the catastrophic offsite "
            "hospitalization tail (via stop-loss and on-site capability), and "
            "absorbs a rising pharmacy line (Hep C, MOUD, psychotropics). "
            "Against that thin operating margin sits an outsized, lumpy "
            "liability cost: claims reserves and insurance for a population with "
            "a constitutional right to care and active plaintiffs' bar. Staffing "
            "shortages in remote facilities force locum premiums that compress "
            "margin further. It is a business where a good clinical and "
            "utilization-management year can be erased by a single verdict or "
            "consent decree (ILLUSTRATIVE)."),
    ),
    risks=[
        Risk("Litigation / Eighth-Amendment liability", "High",
             "Deliberate-indifference, wrongful-death, ADA, and mental-health "
             "claims plus DOJ consent decrees can swamp contract margin — the "
             "defining risk (Wellpath's 2024 bankruptcy is the warning)."),
        Risk("Capitated utilization risk / offsite tail", "High",
             "The vendor insures a sick, aging population; catastrophic offsite "
             "hospitalizations are a fat tail that stop-loss only partly caps."),
        Risk("Clinical staffing shortages (RN, psychiatry)", "High",
             "Vacancies in remote, undesirable facilities cap quality, force "
             "locum premiums, and directly increase liability exposure."),
        Risk("Pharmacy cost inflation (Hep C, MOUD, psychotropics)", "Medium",
             "Mandated Hepatitis C treatment and medication for opioid use "
             "disorder push the fastest-rising cost line."),
        Risk("Political / reputational & contract-turnover risk", "Medium",
             "Privatized prison health draws advocacy and press scrutiny; "
             "contract wins and losses are often political, not performance."),
        Risk("§1115 reentry-waiver implementation complexity", "Medium",
             "New Medicaid pre-release billing helps economics but adds "
             "compliance and operational complexity for a stretched workforce."),
    ],
    diligence_questions=[
        "What is the contract mix (capitated vs. cost-plus), and how is offsite "
        "hospitalization risk shared and stop-loss structured?",
        "What is the litigation history — open matters, consent decrees, claims "
        "frequency — and what reserves and insurance are held?",
        "What is the medical loss ratio and offsite-hospitalization cost trend "
        "by contract?",
        "What are the clinical staffing vacancy rates, and how much is filled "
        "with premium locum/agency labor?",
        "What is the pharmacy cost trajectory (Hep C, MOUD, HIV, psychotropics), "
        "and how is it contractually shared?",
        "What is contract concentration and renewal risk, and how many awards "
        "are politically exposed?",
        "What NCCHC/ACA accreditation status and survey/deficiency history do "
        "the facilities carry?",
        "What is the §1115 reentry-waiver readiness and the revenue/complexity "
        "impact by state?",
    ],
    insider_lens=[
        "It is the only place in America with a constitutional right to "
        "healthcare — Estelle v. Gamble — so the demand is guaranteed but the "
        "liability is the business. A single wrongful-death verdict or DOJ "
        "consent decree can erase a good year, and the plaintiffs' bar is "
        "active. Wellpath's 2024 Chapter 11 is the cautionary tale.",
        "Capitation makes it an insurance company in scrubs. The vendor bears "
        "utilization risk on the sickest population in the country, and the "
        "catastrophic offsite hospitalization is the tail that breaks budgets — "
        "the man-day rate and the stop-loss structure are the entire underwrite.",
        "Growth is acuity, not headcount. Incarceration has been flat to "
        "declining since the 2008 peak, so nobody is underwriting more inmates. "
        "The cost and revenue per inmate rise — aging, chronic disease, mental "
        "illness, and mandated Hep C and opioid treatment.",
        "The Medicaid Inmate Exclusion is quietly cracking. For decades "
        "Medicaid paid nothing during incarceration; the §1115 reentry waivers "
        "(CalAIM first, 20-plus states following) put Medicaid dollars into a "
        "Medicaid-excluded setting for the first time — real upside, and real "
        "new billing complexity.",
        "Staffing, not demand, caps quality and margin. Psychiatrist and RN "
        "vacancies in remote prisons force expensive locum coverage and drive "
        "telehealth adoption — and understaffing is itself a liability "
        "multiplier in a deliberate-indifference world.",
    ],
    connections=default_connections(
        "correctional_health",
        deals_sector="correctional_health",
        extra_pages=[
            ("/diligence/tam-sam?template=correctional_health",
             "Correctional Health deep-dive — sizing build + deal history"),
        ],
        connectors=[
            ("medicaid_data_enrollment_monthly",
             "Medicaid — enrollment (the §1115 reentry-eligible / justice-"
             "involved population surface)"),
            ("medicaid_data_managed_care_by_state_2024",
             "Medicaid — managed care by state (reentry-benefit delivery "
             "context)"),
            ("cdc_data_vsrr_drug_overdose",
             "CDC — provisional drug-overdose data (SUD/MOUD demand context)"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded providers/entities (compliance screen)"),
        ],
    ),
    sources=[
        Source("Estelle v. Gamble, 429 U.S. 97 (1976)", "GOV",
               "https://supreme.justia.com/cases/federal/us/429/97/"),
        Source("Bureau of Justice Statistics — incarceration counts and "
               "correctional statistics", "GOV", "https://bjs.ojp.gov/"),
        Source("Pew Charitable Trusts — state prison health-care spending "
               "research", "ACADEMIC",
               "https://www.pewtrusts.org/en/research-and-analysis/issue-briefs/2017/12/prison-health-care-costs-and-quality"),
        Source("CMS / Medicaid.gov — §1115 reentry demonstrations and the "
               "Medicaid Inmate Exclusion", "GOV",
               "https://www.medicaid.gov/medicaid/section-1115-demonstrations/index.html"),
        Source("National Commission on Correctional Health Care (NCCHC) — "
               "standards", "INDUSTRY", "https://www.ncchc.org/"),
        Source("PE Desk industry deep-dive (correctional health) + deal corpus",
               "INTERNAL",
               "/diligence/tam-sam?template=correctional_health"),
    ],
    live_figures=live_figures_from_dive("correctional_health"),
    trends=(
        "Correctional health is a mature, capitated, litigation-defined sector "
        "reshaping around one policy change. Demand is structurally flat in "
        "headcount — incarceration rates have declined since the 2008 peak — "
        "but rising in intensity: prison populations are aging into geriatric "
        "and chronic-disease care, mental illness and substance use are "
        "pervasive, and mandated treatments (Hepatitis C direct-acting "
        "antivirals, medication for opioid use disorder) push the pharmacy line "
        "up. The capitated model that funds most contracts makes vendors "
        "insurers of this population, with catastrophic offsite hospitalization "
        "the tail — and the recent history is distress: Wellpath's 2024 Chapter "
        "11 and Corizon's bankruptcy exposed how litigation, staffing "
        "shortages, and utilization risk overwhelm thin margins. The structural "
        "change is the §1115 reentry-waiver wave: for the first time since the "
        "Medicaid Inmate Exclusion, Medicaid dollars are entering the setting "
        "for pre-release care, shifting some cost off states and vendors and "
        "creating new reentry and care-coordination services — while adding "
        "compliance complexity. Telehealth adoption, forced by remote-facility "
        "staffing shortages, is the quiet operational tailwind."),
    growth_levers=[
        GrowthLever(
            "Acuity per inmate (aging + chronic + MH/SUD)",
            "A flat-to-declining census that is older and sicker raises required "
            "services and capitated rates per inmate — the primary lever.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Pharmacy (Hep C cure, MOUD, HIV, psychotropics)",
            "Mandated Hepatitis C and opioid-use-disorder treatment plus "
            "psychotropics lift the drug line and the contract rate.",
            "+ pharmacy", "ILLUSTRATIVE"),
        GrowthLever(
            "§1115 Medicaid reentry waivers",
            "Pre-release Medicaid coverage introduces a new payer and new "
            "reentry/care-coordination revenue in a historically excluded "
            "setting.",
            "regime change", "GOV"),
        GrowthLever(
            "Privatization / outsourcing shifts",
            "States moving from in-house to contracted care (or back) reshape "
            "the addressable vendor book — a two-way, politically driven lever.",
            "two-way", "ILLUSTRATIVE"),
        GrowthLever(
            "Litigation & political risk (a negative lever)",
            "Consent decrees, verdicts, and reputational scrutiny pressure "
            "margin and drive contract turnover.",
            "margin drag", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Acuity per inmate (not census) × mandated-treatment expansion",
        analysis=(
            "The demand story is deliberately not a headcount story. The "
            "incarcerated population has been flat to declining since the 2008 "
            "peak, so the driver is what each inmate needs, not how many there "
            "are. Three forces compound the acuity: the population is aging into "
            "geriatric and chronic-disease care (cardiac, diabetes, cancer, "
            "dialysis); mental illness and substance-use disorders are far more "
            "prevalent than in the community; and mandated treatments have "
            "expanded — Hepatitis C direct-acting antivirals (driven by "
            "litigation over access) and medication for opioid use disorder "
            "(state mandates) create standing, high-cost care obligations. Layer "
            "on the §1115 reentry benefit, which adds pre-release services and a "
            "new Medicaid payer. The result is rising cost and revenue per "
            "inmate against a stable-to-shrinking base — a per-capita acuity "
            "curve, underwritten as capitated utilization risk."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "On-site clinical labor (RN, providers, mental health)",
            "~45-55% of cost",
            "The dominant cost — 24/7 nursing, providers, and behavioral-health "
            "staff, inflated by chronic vacancies and locum premiums in remote "
            "facilities.", "ILLUSTRATIVE"),
        CostDriver(
            "Offsite hospitalization & specialty care",
            "the variance tail",
            "Community-hospital transfers and specialty consults at high unit "
            "cost — the biggest source of margin variance, partly capped by "
            "stop-loss.", "ILLUSTRATIVE"),
        CostDriver(
            "Pharmacy (Hep C, HIV, psychotropics, MOUD)",
            "fast-rising line",
            "High-cost mandated therapies — Hepatitis C DAAs and opioid-use-"
            "disorder medication in particular — often the fastest-growing "
            "cost.", "ILLUSTRATIVE"),
        CostDriver(
            "Litigation, liability insurance & claims reserves",
            "lumpy, outsized",
            "Reserves and insurance for deliberate-indifference, wrongful-death, "
            "ADA, and mental-health exposure — a cost that can dwarf operating "
            "margin.", "ILLUSTRATIVE"),
        CostDriver(
            "Staffing-agency / locum premium",
            "structural in remote sites",
            "Filling RN and psychiatry vacancies in undesirable locations with "
            "premium agency labor is a persistent margin drag.", "ILLUSTRATIVE"),
    ],
    state_breakdown=None,
    cms_trend=None,
)

register(REPORT)
