"""Virtual Primary Care — longitudinal primary care delivered virtually.

Deals-only pattern (care is delivered virtually — geography is not the structure
read). The defining distinction is longitudinal: VPC is an ongoing virtual PCP
relationship (a named clinician, a panel, chronic-condition management) sold to
employers/health plans on a PMPM basis — NOT the one-off, on-demand telehealth
'urgent' visit. The unit economics turn on engagement (do covered lives actually
use it) and on the two policy switches that gate delivery: state medical
licensure (the clinician must be licensed where the patient sits) and the
DEA/Ryan-Haight controlled-substance telemedicine rules. Live SOURCED figures
(corpus deals, MOIC) come from ``virtual_primary_care_deep_dive()``.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="virtual_primary_care",
    name="Virtual Primary Care",
    care_setting="Ambulatory",
    naics="621399",
    one_line_def=(
        "Longitudinal primary care delivered virtually — an ongoing virtual PCP "
        "relationship (video + asynchronous messaging, a named clinician, a "
        "panel, chronic-condition management), typically sold to self-insured "
        "employers and health plans on a per-member-per-month basis, sometimes "
        "direct-to-consumer as a membership — distinct from one-off on-demand "
        "telehealth urgent visits."),
    tam_headline=TamHeadline(
        value=12.0, unit="$B", growth_pct=11.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US virtual-primary-care revenue — covered lives under VPC "
            "contracts × blended PMPM access fee, plus per-visit fee-for-service "
            "and direct-to-consumer membership. This is a TAM/SAM-style build off "
            "the broader telehealth market, not a filed figure; growth is the "
            "modeled composite of employer adoption, engagement gains, and "
            "value-based expansion, net of the Medicare telehealth-flexibility "
            "policy risk. ILLUSTRATIVE."),
    ),
    executive_summary=[
        "The product is a relationship, not a visit. VPC sells an ongoing "
        "virtual PCP — a named clinician, a panel, longitudinal chronic-"
        "condition management — mostly to self-insured employers and plans on a "
        "PMPM basis. That is a fundamentally different (and stickier) business "
        "than on-demand urgent telehealth.",
        "Engagement is the whole game. Contracts are priced on covered lives, "
        "but value — and renewal — depends on whether members actually enroll, "
        "establish with a clinician, and use the service. The 2020-21 telehealth "
        "boom overpriced access and underpriced engagement; the reckoning "
        "(normalized visit volumes, a multibillion-dollar Livongo goodwill "
        "impairment at Teladoc) reset the sector's expectations.",
        "Two policy switches gate the model. State medical licensure requires "
        "the clinician to be licensed where the PATIENT is located — the #1 "
        "operational constraint for a national panel — and the DEA/Ryan Haight "
        "telemedicine rules govern whether controlled substances (ADHD, "
        "buprenorphine, some weight-management adjuncts) can be prescribed "
        "virtually.",
        "Medicare's telehealth flexibilities are on a legislative cliff. The "
        "pandemic-era waivers (geographic/originating-site, audio-only, home as "
        "an origin) keep getting short extensions rather than a permanent fix — "
        "a recurring policy overhang for any VPC book with Medicare exposure.",
        "The market is consolidating toward hybrid and value-based models: "
        "Amazon's ~$3.9B acquisition of One Medical, Included Health (Grand "
        "Rounds + Doctor On Demand), and virtual-first health plans point to "
        "in-person integration and risk-bearing, not pure video visits.",
        "GLP-1 and cash-pay adjacencies (weight management, men's/women's "
        "health) turbocharged D2C economics but on a different, prescription-"
        "led model — read them separately from the employer-PMPM VPC thesis.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Employer / health plan contracts VPC for covered lives (PMPM)",
            "Member enrollment & activation (the first hard step)",
            "Establish with a virtual PCP / care team (panel assignment)",
            "Async messaging + scheduled video visits + labs/e-prescribing",
            "Chronic-condition management & navigation to in-person/specialty",
            "Claims (where FFS) + PMPM billing to the sponsor",
            "Engagement / outcomes reporting → renewal & expansion",
        ],
        sites_of_care=[
            "Member's home / anywhere (video + asynchronous)",
            "Employer worksite / near-site clinic integration (hybrid)",
            "Partnered in-person primary care & retail clinics (referral)",
            "Home phlebotomy / at-home labs & connected devices",
        ],
        money_flow=(
            "Two rails, often blended. The dominant employer/health-plan model "
            "is a per-member-per-month access fee for the covered population "
            "(sometimes with a savings or engagement guarantee), plus "
            "fee-for-service claims for billable visits where the clinician "
            "bills E/M codes via telehealth (modifier 95, place-of-service 02/10). "
            "The direct-to-consumer model is a subscription/membership plus "
            "cash-pay visits and prescription fees. Risk-bearing and virtual-"
            "first health plans push toward capitation/total-cost-of-care "
            "economics. Because the PMPM is paid on covered lives regardless of "
            "use, the sponsor's ROI — and the vendor's renewal — hinges on "
            "engagement, while the vendor's own margin hinges on clinician "
            "utilization against that same fixed-fee revenue."),
        key_players=(
            "A crowded field spanning employer-sold VPC (Teladoc Primary360, "
            "Included Health, Firefly Health, Galileo, 98point6's licensed "
            "platform), retail/strategic hybrids (Amazon One Medical, "
            "health-system virtual-first offerings), payer-embedded virtual-first "
            "plans, and prescription-led D2C (Ro, Hims & Hers, PlushCare, K "
            "Health). Behind them sit the enablement layer — licensing/credential "
            "networks, e-prescribing and lab logistics, and the friendly-PC / "
            "management-services structures that hold the clinical entity."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Employer-sponsored VPC (PMPM covered lives)",
                    "the core B2B2C book",
                    "ILLUSTRATIVE · covered lives × PMPM"),
            Segment("Health-plan / virtual-first plan embedded VPC",
                    "payer-integrated, risk-leaning",
                    "ILLUSTRATIVE · plan-embedded lives"),
            Segment("Direct-to-consumer membership & cash-pay",
                    "subscription + visit/Rx fees",
                    "INDUSTRY · D2C telehealth membership"),
            Segment("Medicare / Medicare Advantage virtual primary care",
                    "flexibility-cliff exposed",
                    "GOV · Medicare telehealth policy"),
            Segment("Prescription-led adjacencies (GLP-1, men's/women's health)",
                    "fast, but a different model",
                    "INDUSTRY · cash-pay Rx telehealth"),
        ],
        growth_drivers=[
            "Primary-care access shortage (HPSAs) & PCP supply constraints",
            "Employer demand for cost control and a single 'front door'",
            "Consumer convenience & digital-native expectations",
            "Value-based / risk-bearing virtual-first plan designs",
            "Telehealth policy (parity laws) — a tailwind with a Medicare cliff",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Employer / health-plan PMPM (self-insured)": 0.55,
            "Fee-for-service telehealth claims (commercial/MA)": 0.25,
            "Direct-to-consumer membership & cash-pay": 0.15,
            "Medicare / Medicaid": 0.05,
        },
        rate_mechanics=[
            "PMPM access fee — the sponsor pays per covered life for access to "
            "the virtual PCP panel, independent of utilization; the anchor of "
            "the employer model.",
            "Telehealth E/M fee-for-service — clinicians bill office/outpatient "
            "E/M codes rendered via telehealth with modifier 95 and place-of-"
            "service 02 (home) / 10, subject to payer telehealth coverage.",
            "State telehealth parity laws — many states require commercial plans "
            "to cover (and sometimes pay at parity for) telehealth services; the "
            "rules vary state by state.",
            "Medicare telehealth flexibilities — pandemic-era waivers (home as "
            "originating site, geographic waiver, audio-only, expanded eligible "
            "providers) extended in short increments; permanent for behavioral "
            "health, uncertain for the rest (the 'telehealth cliff').",
            "D2C subscription & cash-pay — membership fees plus per-visit and "
            "per-prescription charges; the GLP-1/weight-management wave rides "
            "this rail, not the PMPM one.",
        ],
        reimbursement_risk=(
            "The commercial risk is not claim denial — it is engagement and "
            "renewal. A PMPM book paid on covered lives is only as durable as the "
            "utilization that justifies it to the sponsor; low engagement turns "
            "renewals into price-downs or losses. The policy risk is the Medicare "
            "telehealth cliff (short extensions rather than a permanent rule) and "
            "the DEA telemedicine controlled-substance rules that gate a chunk of "
            "the prescribing (ADHD, buprenorphine). And the D2C prescription "
            "adjacencies (GLP-1) carry their own reimbursement and supply "
            "volatility that should not be conflated with the core employer-PMPM "
            "economics. Underwrite engagement, renewal, and clinician "
            "utilization — not headline covered lives."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("State medical licensure (patient-location rule) & IMLC",
                 "The clinician must be licensed in the state where the PATIENT "
                 "is located — the central operational constraint for a national "
                 "panel; the Interstate Medical Licensure Compact eases, but "
                 "does not eliminate, multi-state licensing.",
                 "https://www.imlcc.org/"),
            Rule("DEA / Ryan Haight Act telemedicine controlled-substance rules",
                 "Govern whether controlled substances (ADHD stimulants, "
                 "buprenorphine, etc.) can be prescribed via telemedicine; the "
                 "post-PHE flexibilities and the pending permanent rule are "
                 "existential for prescribing-heavy models.",
                 "https://www.deadiversion.usdoj.gov/"),
            Rule("Medicare telehealth flexibilities (the cliff)",
                 "Originating-site, geographic, audio-only, and eligible-"
                 "provider waivers extended in short increments — a recurring "
                 "policy overhang for Medicare-exposed VPC.",
                 "https://www.cms.gov/medicare/coverage/telehealth"),
            Rule("State telehealth parity & standard-of-care laws",
                 "Coverage/payment parity and the clinical standard for "
                 "establishing a valid patient relationship vary state by state.",
                 None),
            Rule("Corporate practice of medicine (CPOM) / friendly-PC structures",
                 "Most states bar lay ownership of medical practices; VPC "
                 "operators use MSO / friendly-PC structures whose integrity is a "
                 "core diligence item.",
                 None),
        ],
        policy_watch=[
            "Permanent vs short-term extension of Medicare telehealth waivers",
            "Final DEA telemedicine controlled-substance prescribing rule",
            "State licensure compact expansion & multi-state credentialing",
            "State telehealth parity-law changes (payment vs coverage parity)",
            "GLP-1 telehealth prescribing scrutiny and payer coverage shifts",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Crowded and still shaking out. Employer-sold VPC, retail/strategic "
            "hybrids, payer-embedded virtual-first plans, and prescription-led "
            "D2C all compete for overlapping budgets, with heavy differentiation "
            "on engagement, clinical model, and integration with in-person care. "
            "No single operator owns the category."),
        hhi_or_share=(
            "Share is diffuse across public platforms (Teladoc, Hims & Hers, "
            "Amazon/One Medical), venture-backed challengers, and payer-owned "
            "offerings; no clean market-share census is vendored. The corpus "
            "deal history and the covered-lives/engagement lens below are the "
            "honest anchors — not a facility map, since delivery is virtual."),
        consolidation=(
            "Consolidation is toward hybrid and scale: Amazon's ~$3.9B One "
            "Medical acquisition, Included Health (the Grand Rounds + Doctor On "
            "Demand merger), and payer/retail integration. The logic is that "
            "pure virtual visits commoditize, so winners bundle longitudinal "
            "primary care with in-person access, navigation, and risk — a "
            "'front door' rather than a video widget."),
        pe_activity=(
            "After the 2020-21 boom and the subsequent repricing, capital became "
            "discriminating: sponsors and strategics favor models with proven "
            "engagement, employer/plan contracts with retention, and a path to "
            "value-based economics, and are wary of CAC-heavy D2C without "
            "durable LTV. Diligence centers on engagement, renewal/NRR, clinician "
            "utilization, and the friendly-PC structure — not covered-life "
            "counts."),
        notable_players=[
            "Teladoc Health (Primary360)", "Included Health",
            "Amazon / One Medical", "Firefly Health", "Galileo", "98point6",
            "Hims & Hers", "Ro", "K Health", "PlushCare (Accolade)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Engagement / activation rate", "the value gate",
                "Share of covered lives who enroll and actually use the service "
                "— the number that justifies the PMPM and drives renewal."),
            Kpi("PMPM (per-member-per-month)", "contract pricing",
                "The access-fee rate per covered life; blended with any FFS and "
                "guarantee structure."),
            Kpi("Clinician panel size / utilization", "the cost lever",
                "Visits and messages handled per clinician against fixed PMPM "
                "revenue — the vendor's own margin driver."),
            Kpi("Net revenue retention (employer renewal + expansion)", "durability",
                "Renewals and seat/lives expansion versus churn at the benefits "
                "cycle — the enterprise-value metric."),
            Kpi("CAC / LTV (D2C book)", "membership economics",
                "For direct-to-consumer, acquisition cost against subscription "
                "lifetime value — the historical value trap."),
            Kpi("Total-cost-of-care impact (risk/VBC book)", "the ROI proof",
                "Whether virtual PCP demonstrably lowers downstream spend — the "
                "hard, contested claim under value-based designs."),
        ],
        margin_profile=(
            "The employer-PMPM model is a recurring-revenue services business: "
            "revenue is fixed per covered life, so gross margin turns on "
            "clinician utilization (panel density) and technology leverage, while "
            "enterprise value turns on engagement and renewal. The D2C model is a "
            "marketing-and-fulfillment business whose margin is dominated by "
            "member-acquisition cost against subscription LTV — a very different "
            "shape that the 2020-21 cycle showed can invert. Prescription-led "
            "adjacencies (GLP-1) can be high-velocity but volatile. Ranges are "
            "ILLUSTRATIVE — segment the book by rail before believing a blended "
            "margin."),
    ),
    risks=[
        Risk("Engagement / renewal risk", "High",
             "PMPM paid on covered lives is only durable if members use it; low "
             "engagement turns renewals into price-downs or losses."),
        Risk("Medicare telehealth flexibility cliff", "High",
             "Short-term extensions rather than a permanent rule create recurring "
             "coverage uncertainty for any Medicare-exposed book."),
        Risk("DEA telemedicine controlled-substance rules", "High",
             "The prescribing framework for ADHD/buprenorphine/etc. gates a "
             "meaningful slice of virtual-care volume and revenue."),
        Risk("D2C customer-acquisition economics", "Medium",
             "CAC-heavy direct-to-consumer models can invert if LTV/retention "
             "disappoints — the lesson of the boom-bust cycle."),
        Risk("State licensure & CPOM structure", "Medium",
             "Multi-state licensing constrains the panel, and friendly-PC "
             "structures must withstand corporate-practice scrutiny."),
        Risk("Clinician labor supply & burnout", "Medium",
             "Panel growth is capped by licensed-clinician supply and virtual-"
             "care attrition."),
    ],
    diligence_questions=[
        "What is the engagement/activation rate across the book, and how does it "
        "trend from launch through renewal cohorts?",
        "What is net revenue retention — employer renewal, lives expansion, and "
        "churn — and how concentrated is revenue in the top accounts?",
        "How is revenue split across employer-PMPM, FFS telehealth, and D2C "
        "membership, and what is the margin of each rail?",
        "What is the Medicare/MA exposure, and how would a lapse of the "
        "telehealth flexibilities affect it?",
        "How much prescribing depends on the DEA telemedicine controlled-"
        "substance framework, and what is the contingency if it tightens?",
        "How many states is the clinician panel licensed in, and how robust is "
        "the friendly-PC / MSO structure to CPOM scrutiny?",
        "For any value-based book, what is the demonstrated total-cost-of-care "
        "impact, and how is it measured and attributed?",
    ],
    insider_lens=[
        "Covered lives are a vanity number; engagement is the business. A book "
        "of a million 'access' lives with 3% utilization is worth far less than "
        "half the lives at 25% engagement — because engagement is what the "
        "employer renews and what the clinician actually gets paid to do.",
        "The 2020-21 boom priced access and forgot engagement. The reckoning — "
        "normalized visit volumes and a multibillion-dollar Livongo goodwill "
        "impairment at Teladoc — is the cautionary comp. Assume the market now "
        "underwrites retention and utilization, not signed logos.",
        "Licensure is the invisible ceiling. Because the clinician must be "
        "licensed where the patient sits, a 'national' panel is really a "
        "patchwork of state-licensed clinicians; scaling the panel is a "
        "credentialing operation, and it caps how fast lives convert to visits.",
        "The DEA rules quietly decide which businesses exist. Whole categories — "
        "virtual ADHD care, tele-buprenorphine — live or die on the Ryan Haight "
        "telemedicine framework. Any prescribing-heavy VPC has a regulatory "
        "single-point-of-failure that belongs on the risk page, not a footnote.",
        "Don't blend the GLP-1 rocket into the primary-care engine. The cash-pay "
        "weight-management and men's/women's-health wave is a different, "
        "marketing-led, prescription-fulfillment model with its own supply and "
        "coverage volatility — flattering a blended top line but not the same "
        "durable employer-PMPM asset.",
    ],
    connections=default_connections(
        "virtual_primary_care",
        deals_sector="virtual_primary_care",
        connectors=[
            ("cms_open_data_medicare_telehealth_trends",
             "CMS Medicare Telehealth Trends — utilization by service & modality"),
            ("hrsa_data_hpsa_primary_care",
             "HRSA HPSA — primary-care shortage areas (the access demand base)"),
            ("npi_provider",
             "NPI Registry — primary-care clinician supply & multi-state footprint"),
            ("cms_open_data_mup_physician_by_provider_service",
             "CMS Physician & Other Practitioners — telehealth E/M (mod 95) lines"),
            ("census_acs_cbsa_profile",
             "Census ACS — covered-population & digital-access demographics"),
            ("open_payments_general_payments_2024",
             "CMS Open Payments — industry ties across the clinician panel"),
        ],
    ),
    sources=[
        Source("CMS — Medicare telehealth coverage, flexibilities, and the "
               "telehealth trends data", "GOV",
               "https://www.cms.gov/medicare/coverage/telehealth"),
        Source("DEA / DOJ — Ryan Haight Act telemedicine controlled-substance "
               "prescribing rules", "GOV",
               "https://www.deadiversion.usdoj.gov/"),
        Source("Interstate Medical Licensure Compact — multi-state physician "
               "licensure", "GOV", "https://www.imlcc.org/"),
        Source("KFF / Peterson-KFF Health System Tracker — telehealth "
               "utilization & trends research", "INDUSTRY",
               "https://www.kff.org/"),
        Source("PE Desk industry deep-dive (virtual primary care) + realized-"
               "deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=virtual_primary_care"),
    ],
    live_figures=live_figures_from_dive("virtual_primary_care"),
    trends=(
        "Virtual primary care emerged from the telehealth boom as the attempt to "
        "convert one-off video visits into a longitudinal, employer-paid PCP "
        "relationship. The 2020-21 surge priced euphoria — access and covered "
        "lives — and the 2022-24 reckoning repriced it around engagement: visit "
        "volumes normalized off pandemic peaks, Teladoc took a multibillion-"
        "dollar Livongo goodwill impairment, and CAC-heavy D2C models proved the "
        "LTV was harder than the pitch. The sector's response has been to go "
        "hybrid and value-based — Amazon's ~$3.9B One Medical acquisition, "
        "Included Health's merger, and virtual-first health plans all bundle "
        "longitudinal care with in-person access, navigation, and risk. Two "
        "policy switches sit over everything: the Medicare telehealth-flexibility "
        "cliff (perpetual short extensions) and the DEA telemedicine controlled-"
        "substance rules. Meanwhile the GLP-1 and cash-pay prescription wave "
        "created a parallel, marketing-led D2C economics that flatters top lines "
        "but should be underwritten separately from the durable employer-PMPM "
        "primary-care thesis."),
    growth_levers=[
        GrowthLever(
            "Employer adoption & 'front door' consolidation",
            "Self-insured employers add VPC to control cost and simplify the "
            "member experience — the primary covered-lives engine.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Engagement / activation gains",
            "Higher utilization of the same covered lives lifts both sponsor ROI "
            "(renewal) and billable/FFS volume.",
            "value multiplier", "ILLUSTRATIVE"),
        GrowthLever(
            "Primary-care access shortage",
            "HPSA/PCP scarcity pushes patients and payers toward virtual access "
            "as a supply release valve.",
            "structural demand", "GOV"),
        GrowthLever(
            "Value-based / risk-bearing designs",
            "Virtual-first plans and capitated arrangements expand revenue per "
            "life and align on total-cost-of-care.",
            "monetization", "ILLUSTRATIVE"),
        GrowthLever(
            "Telehealth policy (parity tailwind, Medicare cliff drag)",
            "State parity laws support commercial coverage while the Medicare "
            "flexibility cliff caps the public-program upside.",
            "mixed", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Engaged covered lives (contracted lives × activation/utilization)",
        analysis=(
            "The honest demand meter for VPC is not signed covered lives but "
            "ENGAGED lives — the product of contracted population and the share "
            "that actually enrolls, establishes with a clinician, and uses the "
            "service. Contracted lives grow with employer adoption (driven by "
            "healthcare cost inflation and 'front door' consolidation) and with "
            "the primary-care access shortage that HRSA HPSA data quantifies; but "
            "the conversion from a covered life to a billable visit is gated by "
            "engagement and by clinician licensure in the patient's state. That "
            "is why CMS telehealth-trends and physician telehealth-E/M lines "
            "matter more than logo counts: they measure realized utilization. A "
            "credible volume model multiplies contracted lives by a defensible, "
            "cohort-based engagement curve — not a hoped-for one."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Clinician labor (virtual PCPs, APPs, care team)",
            "#1 — the COGS",
            "Delivering longitudinal care is clinician-time-intensive; panel "
            "utilization against fixed PMPM revenue sets gross margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Member acquisition / enterprise sales (and D2C marketing)",
            "high, model-dependent",
            "Employer sales cycles are long and B2B; D2C CAC can dominate the "
            "P&L and was the boom-era value trap.", "ILLUSTRATIVE"),
        CostDriver(
            "Technology platform & integrations",
            "~12-20% of cost",
            "The video/async platform, EHR, e-prescribing, and payer/employer "
            "data integrations — the scalable-leverage layer.", "ILLUSTRATIVE"),
        CostDriver(
            "Licensing, credentialing & compliance",
            "~8-12% of cost",
            "Multi-state clinician licensing, the friendly-PC/MSO structure, and "
            "telehealth regulatory upkeep.", "ILLUSTRATIVE"),
        CostDriver(
            "Care coordination, labs & fulfillment",
            "~8-12% of cost",
            "At-home labs, connected devices, e-prescribing logistics, and "
            "navigation to in-person/specialty care.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "Care is delivered virtually, so a facility map is not the structure "
        "read and none is fabricated. The honest geographic lens is regulatory "
        "and demographic: the clinician panel's reach is bounded by state "
        "medical licensure (where clinicians are licensed, eased by the "
        "Interstate Medical Licensure Compact), while demand concentrates where "
        "primary-care access is thin (HRSA HPSA primary-care shortage areas) and "
        "where covered, digitally-enabled populations sit. Use the HPSA, NPI-"
        "supply, and CMS telehealth-trends connectors below rather than a "
        "provider census."),
)

register(REPORT)
