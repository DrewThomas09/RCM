"""Care Navigation — guiding members through the healthcare system.

Deals-only pattern (delivered nationally to employer/plan populations —
geography is not the structure read). The defining fact is that the customer is
a self-insured EMPLOYER or a health PLAN, not a patient, and the product is
bought on a per-member-per-month basis to steer members to high-value care,
consolidate point solutions ('point-solution fatigue'), and lower total cost of
care. It is a B2B services-plus-technology business, not a claims-billed medical
one — so the diligence is engagement, retention (NRR), and the hard question of
whether the savings are real. A nascent fee-for-service path is opening via CMS
Principal Illness Navigation / Community Health Integration codes, but employer-
PMPM is the economics. Live SOURCED figures come from
``care_navigation_deep_dive()`` (the corpus is thin here).
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="care_navigation",
    name="Care Navigation",
    care_setting="Ambulatory",
    naics="621999",
    one_line_def=(
        "Services that guide patients and members through the healthcare system "
        "— finding high-value providers, scheduling, benefits and cost/quality "
        "transparency, second opinions, prior-authorization help, and care "
        "coordination — sold predominantly to self-insured employers and health "
        "plans on a per-member-per-month basis, sometimes with savings or "
        "engagement guarantees, and increasingly bundled as a single 'front "
        "door' over a stack of point solutions."),
    tam_headline=TamHeadline(
        value=10.0, unit="$B", growth_pct=12.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US care-navigation / patient-advocacy revenue — covered "
            "lives under navigation contracts × blended PMPM, plus emerging "
            "clinical-navigation fee-for-service (CMS PIN/CHI codes) and Medicaid "
            "care-coordination. This is a TAM/SAM-style build off the self-"
            "insured covered-lives base, not a filed figure; growth is the "
            "modeled composite of employer adoption, point-solution consolidation, "
            "and fiduciary-transparency tailwinds. ILLUSTRATIVE."),
    ),
    executive_summary=[
        "The customer is the employer or health plan, not the patient. Care "
        "navigation is a B2B services-plus-technology business sold on a PMPM "
        "basis to steer members to high-value care and reduce total cost of "
        "care — there is almost no medical claims billing in the core model.",
        "The pitch is consolidation. Employers drowning in point solutions "
        "(diabetes app, MSK app, fertility, mental health, second opinion) want "
        "a single 'front door' that routes members and integrates the stack — so "
        "navigation platforms increasingly compete to BE the front door, not "
        "just a widget behind it.",
        "Engagement and provable savings are the whole diligence. Revenue is "
        "contracted PMPM on covered lives, but renewal depends on whether members "
        "actually engage and whether the vendor can demonstrate ROI — a "
        "notoriously hard, contested measurement. Signed lives are cheap; NRR is "
        "the value.",
        "It's services-heavy, so margins sit below pure SaaS. Nurses, care "
        "coordinators, and advocates deliver the work; technology provides "
        "leverage but doesn't remove the labor. The best economics come from "
        "digital deflection of routine tasks plus retention and seat expansion.",
        "Consolidation is active: Transcarent's take-private of Accolade, "
        "Included Health (Grand Rounds + Doctor On Demand), and PE-backed Quantum "
        "Health point to scale, bundling with virtual care, and payer/employer "
        "distribution as the winning shape.",
        "A tailwind sits in law: the Consolidated Appropriations Act (2021) put "
        "fiduciary, price-transparency, and gag-clause obligations on employer "
        "plan sponsors — increasing demand for navigation and transparency "
        "tools — while nascent CMS PIN/CHI codes open a small clinical-navigation "
        "fee-for-service path.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Employer / health plan contracts navigation for covered lives (PMPM)",
            "Eligibility & claims/benefits data integration and member outreach",
            "Member enrollment & activation (engagement is the first hard step)",
            "Navigation: provider steerage, scheduling, benefits, prior-auth, "
            "second opinions, care coordination",
            "Point-solution routing & integration (the 'front door')",
            "PMPM billing to the sponsor (+ any savings/performance share)",
            "Engagement & savings reporting → renewal, expansion, cross-sell",
        ],
        sites_of_care=[
            "Telephonic / app-based navigation & advocacy (national)",
            "Employer worksite & benefits-enrollment touchpoints",
            "Embedded in health-plan member services / MA supplemental",
            "Clinical navigation embedded in value-based & oncology care",
        ],
        money_flow=(
            "The dominant rail is a per-member-per-month fee paid by a self-"
            "insured employer or a health plan for access to the navigation "
            "service across a covered population, sometimes structured with a "
            "savings guarantee, a performance/at-risk component, or a case rate. "
            "It is not medical reimbursement — there is little to no claims "
            "billing in the core model. Two adjacent rails are emerging: CMS "
            "Principal Illness Navigation and Community Health Integration codes "
            "(introduced in 2024) create a modest fee-for-service path for "
            "clinical navigation of serious illness, and state Medicaid programs "
            "pay for care coordination / targeted case management. The vendor's "
            "economics are therefore a recurring PMPM annuity whose durability "
            "rests on engagement (does the sponsor see value) and whose margin "
            "rests on the cost to serve each engaged member with a services-heavy "
            "delivery model."),
        key_players=(
            "A crowded field of employer-sold navigation/advocacy platforms "
            "(Accolade, now part of Transcarent; Included Health; Quantum Health; "
            "Rightway; Transcarent; Health Advocate; Personify Health), plus "
            "condition-specific and oncology navigation, health-plan-embedded "
            "navigation, and clinical navigation inside value-based groups. "
            "Upstream sit the benefits consultants/brokers who gate employer "
            "distribution, and the point-solution vendors that navigation both "
            "aggregates and competes with to own the member relationship."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Employer-sponsored navigation/advocacy (PMPM)",
                    "the core self-insured book",
                    "ILLUSTRATIVE · covered lives × PMPM"),
            Segment("Health-plan-embedded navigation (incl. MA supplemental)",
                    "payer-distributed",
                    "ILLUSTRATIVE · plan-embedded lives"),
            Segment("Condition-specific / oncology navigation",
                    "clinical, higher-touch",
                    "INDUSTRY · condition-navigation programs"),
            Segment("Clinical navigation FFS (CMS PIN / CHI codes)",
                    "nascent fee-for-service path",
                    "GOV · CMS PIN/CHI 2024 codes"),
            Segment("Medicaid care coordination / targeted case management",
                    "state-paid coordination",
                    "GOV · state Medicaid case-management"),
        ],
        growth_drivers=[
            "Employer healthcare-cost inflation & demand for cost control",
            "Point-solution fatigue → consolidation to a single front door",
            "Fiduciary & price-transparency obligations (CAA 2021)",
            "System complexity & access friction members can't navigate alone",
            "Emerging clinical-navigation reimbursement (CMS PIN/CHI, Medicaid)",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Employer PMPM (self-insured)": 0.65,
            "Health-plan PMPM / embedded": 0.20,
            "Medicaid care coordination / case management": 0.08,
            "Clinical-navigation FFS (CMS PIN/CHI) & other": 0.07,
        },
        rate_mechanics=[
            "PMPM contract — the sponsor pays per covered life for access to "
            "navigation, independent of utilization; the core annuity.",
            "Savings / performance guarantees — some contracts put a portion of "
            "fees at risk against demonstrated savings or engagement targets.",
            "CMS Principal Illness Navigation & Community Health Integration "
            "codes (2024) — a nascent fee-for-service path for clinical "
            "navigation of serious illness / health-related social needs.",
            "Medicaid targeted case management / care coordination — state "
            "programs pay for coordination services, a separate public rail.",
            "Little to no commercial medical claims billing in the core model — "
            "the revenue is contracted B2B fees, not adjudicated claims.",
        ],
        reimbursement_risk=(
            "The core risk is not claim denial — it is engagement, renewal, and "
            "the credibility of the savings story. PMPM paid on covered lives is "
            "only as durable as the utilization and demonstrated ROI that justify "
            "it at the benefits-cycle renewal; low engagement or an unprovable "
            "savings claim turns renewals into price-downs, consolidation losses, "
            "or churn. The emerging CMS PIN/CHI and Medicaid rails are small and "
            "policy-dependent, so they diversify rather than anchor the model. "
            "And because employer distribution runs through benefits consultants "
            "on an annual cycle, revenue is lumpy and relationship-dependent. "
            "Underwrite net revenue retention, engagement, and cost-to-serve — "
            "not headline covered lives or unaudited savings percentages."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Consolidated Appropriations Act, 2021 — plan-fiduciary & "
                 "transparency rules",
                 "Employer fiduciary duty, price-transparency, and gag-clause "
                 "attestation obligations increase demand for navigation and "
                 "transparency tools — the sector's regulatory tailwind.",
                 "https://www.dol.gov/agencies/ebsa"),
            Rule("ERISA (self-insured employer plans)",
                 "Self-insured plans and their vendors operate under ERISA; "
                 "fiduciary and data obligations shape contracting and "
                 "member-facing conduct.",
                 "https://www.dol.gov/agencies/ebsa"),
            Rule("HIPAA privacy & security",
                 "Navigation touches claims, benefits, and clinical data across "
                 "integrations — HIPAA compliance and data-handling are core to "
                 "the operating and diligence posture.",
                 "https://www.hhs.gov/hipaa"),
            Rule("CMS Principal Illness Navigation & Community Health "
                 "Integration codes (2024)",
                 "Open a modest Medicare fee-for-service path for clinical "
                 "navigation of serious illness and health-related social needs.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("State nurse licensure (nurse advice / clinical navigation)",
                 "Where navigation includes clinical advice, the nurse must be "
                 "licensed in the member's state — a multi-state operational "
                 "constraint on the clinical layer.",
                 None),
        ],
        policy_watch=[
            "CAA fiduciary / transparency enforcement and litigation trend",
            "Expansion of CMS PIN/CHI clinical-navigation reimbursement",
            "Medicaid care-coordination / case-management scope changes",
            "Employer 'single front door' RFP consolidation dynamics",
            "Data-access & interoperability rules affecting integrations",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Crowded and consolidating. Employer-sold navigation/advocacy "
            "platforms, condition-specific and oncology navigation, and health-"
            "plan-embedded programs compete for overlapping employer and plan "
            "budgets, differentiated on engagement, clinical depth, point-"
            "solution integration, and demonstrated savings. Benefits consultants "
            "heavily shape which vendors reach employers."),
        hhi_or_share=(
            "Share is diffuse across a mix of scaled platforms and challengers "
            "with no clean public census; the honest anchors are the covered-"
            "lives/engagement lens and the deal history below, not a facility "
            "map, since delivery is national and virtual/telephonic."),
        consolidation=(
            "Active and toward scale plus bundling: Transcarent's take-private of "
            "Accolade, Included Health (the Grand Rounds + Doctor On Demand "
            "merger), and PE-backed Quantum Health illustrate the logic — combine "
            "navigation with virtual care and point-solution aggregation to own "
            "the member 'front door', win larger employer/plan contracts, and "
            "spread the services cost base."),
        pe_activity=(
            "Sponsors are drawn to the recurring PMPM revenue and the "
            "consolidation thesis but wary of long enterprise sales cycles, "
            "services-heavy margins, and the difficulty of proving savings. The "
            "durable thesis favors platforms with high engagement, strong net "
            "revenue retention, a credible ROI methodology, and 'front door' "
            "breadth — not single-feature tools vulnerable to bundling by a "
            "larger navigator."),
        notable_players=[
            "Accolade (Transcarent)", "Included Health", "Quantum Health",
            "Transcarent", "Rightway", "Health Advocate", "Personify Health",
            "Health-plan-embedded & oncology navigation programs",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Engagement / activation rate", "the value gate",
                "Share of covered lives who actually use navigation — what "
                "justifies the PMPM and drives renewal."),
            Kpi("PMPM (per-member-per-month)", "contract pricing",
                "The access-fee rate per covered life; blended with any at-risk "
                "/ savings-share structure."),
            Kpi("Net revenue retention (renewal + expansion)", "durability",
                "Employer/plan renewals, lives and module expansion, versus churn "
                "at the benefits cycle — the enterprise-value metric."),
            Kpi("Cost to serve per engaged member", "the margin lever",
                "Services-heavy delivery cost against fixed PMPM — digital "
                "deflection is the leverage."),
            Kpi("Demonstrated savings / ROI", "the renewal proof",
                "The measured (and contested) total-cost impact that underpins "
                "guarantees and renewals."),
            Kpi("Sales-cycle length & CAC", "distribution efficiency",
                "Long, consultant-mediated enterprise cycles make sales "
                "efficiency a core economic driver."),
        ],
        margin_profile=(
            "Care navigation is a recurring-revenue but services-heavy business: "
            "revenue is fixed PMPM on covered lives, so gross margin turns on the "
            "cost to serve each engaged member (nurses, coordinators, advocates) "
            "and on how much routine work technology can deflect. That puts "
            "margins below pure SaaS and rewards digital engagement, automation, "
            "and retention. Enterprise value is driven by net revenue retention "
            "and the credibility of the savings story, while long consultant-"
            "mediated sales cycles make distribution efficiency a real constraint. "
            "Ranges are ILLUSTRATIVE — underwrite engagement, NRR, and cost-to-"
            "serve, and stress-test the ROI methodology."),
    ),
    risks=[
        Risk("Engagement & savings-proof risk", "High",
             "PMPM durability depends on utilization and demonstrable ROI; low "
             "engagement or unprovable savings undermines renewal and pricing."),
        Risk("Point-solution consolidation / competitive bundling", "High",
             "A larger 'front door' can absorb a point tool; single-feature "
             "navigators risk being bundled away."),
        Risk("Net revenue retention / renewal churn", "High",
             "Revenue concentrates in large employer/plan contracts that renew "
             "competitively on an annual benefits cycle."),
        Risk("Services-heavy margin & cost-to-serve", "Medium",
             "Human-delivered navigation caps margins; scaling engagement without "
             "scaling labor is the operating challenge."),
        Risk("Long, consultant-mediated sales cycles", "Medium",
             "Enterprise distribution through benefits consultants makes growth "
             "lumpy and relationship-dependent."),
        Risk("Data-integration & HIPAA/ERISA compliance", "Medium",
             "The model depends on claims/benefits data integrations; privacy, "
             "security, and fiduciary obligations raise the operating bar."),
    ],
    diligence_questions=[
        "What is the engagement/activation rate, and how does it trend across "
        "launch and renewal cohorts?",
        "What is net revenue retention — renewal, lives/module expansion, and "
        "churn — and how concentrated is revenue in the top contracts?",
        "How is savings/ROI measured, is it independently validated, and how much "
        "revenue is at risk against guarantees?",
        "What is the cost to serve per engaged member, and how much routine work "
        "is deflected digitally versus handled by staff?",
        "How does distribution work — which benefits consultants, and what are "
        "sales-cycle length, win rate, and CAC?",
        "How exposed is the platform to point-solution bundling by a larger "
        "navigator, and what is its integration/front-door breadth?",
        "What clinical services are delivered, and how are nurse licensure, "
        "HIPAA, and ERISA fiduciary obligations handled?",
    ],
    insider_lens=[
        "The buyer is the CFO's benefits budget, not a patient. Everything "
        "follows from that: the sale is a long, consultant-mediated enterprise "
        "cycle; the metric is total cost of care and engagement; and the "
        "'competition' is as much point-solution fatigue as it is other "
        "navigators.",
        "Everyone claims savings; almost no one can prove them cleanly. ROI "
        "attribution in a self-insured plan is genuinely hard — selection "
        "effects, regression to the mean, and comparison-group problems abound. "
        "A credible, independently-validated savings methodology is a real moat; "
        "an unaudited 'X:1 ROI' slide is a red flag.",
        "The land grab is to be the front door. The strategic prize is owning the "
        "member relationship and routing the point solutions behind you — which "
        "is why navigation, virtual care, and advocacy keep merging. A single-"
        "feature tool is a bundling target, not a platform.",
        "It's a services business wearing a software multiple. Nurses and "
        "advocates deliver the value, so gross margins sit below SaaS and scale "
        "with headcount unless digital deflection is real. Diligence the cost to "
        "serve and the automation, not just ARR.",
        "Regulation is quietly the demand engine. The CAA's fiduciary and "
        "transparency obligations made employers responsible for steering members "
        "to high-value care — which is exactly what navigation sells. Read the "
        "compliance backdrop as a tailwind, and the nascent CMS PIN/CHI codes as "
        "optionality, not the base case.",
    ],
    connections=default_connections(
        "care_navigation",
        deals_sector="care_navigation",
        connectors=[
            ("npi_provider",
             "NPI Registry — clinical navigators, care coordinators & advice-line "
             "nurses"),
            ("medicaid_data_managed_care_by_state_2024",
             "Medicaid Managed Care — care-coordination / case-management "
             "adjacency by state"),
            ("cms_open_data_mup_physician_by_provider_service",
             "CMS Physician & Other Practitioners — emerging PIN/CHI navigation "
             "code utilization"),
            ("census_acs_county_profile",
             "Census ACS — employer/covered-population base & social-needs context"),
            ("oig_leie_exclusions",
             "OIG LEIE — exclusion screen for clinical navigation staff"),
        ],
    ),
    sources=[
        Source("U.S. DOL Employee Benefits Security Administration — "
               "Consolidated Appropriations Act (2021) fiduciary & transparency "
               "requirements; ERISA", "GOV",
               "https://www.dol.gov/agencies/ebsa"),
        Source("CMS — Principal Illness Navigation & Community Health "
               "Integration codes (CY2024 Physician Fee Schedule)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("HHS — HIPAA privacy & security rules", "GOV",
               "https://www.hhs.gov/hipaa"),
        Source("KFF Employer Health Benefits Survey — self-insured covered lives "
               "& benefits trends", "INDUSTRY", "https://www.kff.org/"),
        Source("PE Desk industry deep-dive (care navigation) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=care_navigation"),
    ],
    live_figures=live_figures_from_dive("care_navigation"),
    trends=(
        "Care navigation grew up as a response to two employer pains: relentless "
        "healthcare-cost inflation and 'point-solution fatigue' — the sprawl of "
        "single-condition apps and programs employers bolted on through the "
        "2010s. The market's answer has been consolidation toward a single 'front "
        "door' that aggregates those point solutions, steers members to high-"
        "value care, and reports savings. That thesis is playing out in M&A: "
        "Transcarent's take-private of Accolade, the Included Health merger, and "
        "PE-backed Quantum Health all combine navigation with virtual care and "
        "advocacy to own the member relationship and win larger employer/plan "
        "contracts. Regulation reinforces the demand — the Consolidated "
        "Appropriations Act (2021) placed fiduciary and price-transparency "
        "obligations on plan sponsors — while a nascent Medicare fee-for-service "
        "path (CMS PIN/CHI codes) and Medicaid care-coordination add small public "
        "rails to the employer-PMPM core. The persistent tensions are the ones "
        "diligence must resolve: engagement is hard to lift, savings are hard to "
        "prove, sales cycles are long and consultant-mediated, and the services-"
        "heavy delivery model keeps margins below the software multiples the "
        "sector is often valued at."),
    growth_levers=[
        GrowthLever(
            "Employer adoption & point-solution consolidation",
            "Employers replace a sprawl of point tools with a single navigation "
            "front door — the primary covered-lives engine.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Engagement gains",
            "Higher utilization of the same covered lives lifts both sponsor ROI "
            "(renewal) and cross-sell of additional modules.",
            "value multiplier", "ILLUSTRATIVE"),
        GrowthLever(
            "Fiduciary & transparency mandates (CAA 2021)",
            "Legal obligations on plan sponsors to steer to high-value care "
            "structurally increase navigation demand.",
            "regulatory tailwind", "GOV"),
        GrowthLever(
            "Clinical-navigation reimbursement (CMS PIN/CHI, Medicaid)",
            "Emerging fee-for-service and Medicaid coordination rails add revenue "
            "beyond employer PMPM.",
            "diversification", "GOV"),
        GrowthLever(
            "Net revenue retention (renewal + expansion)",
            "Keeping and growing large contracts compounds recurring revenue "
            "without new-logo CAC.",
            "compounding", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Engaged covered lives (contracted lives × activation/utilization)",
        analysis=(
            "As with virtual care, the honest demand meter is not contracted "
            "covered lives but ENGAGED lives — contracted population times the "
            "share that actually activates and uses navigation. Contracted lives "
            "grow with employer adoption, which is driven by healthcare-cost "
            "inflation, point-solution fatigue, and the CAA's fiduciary/"
            "transparency obligations that push sponsors to steer members to "
            "high-value care. But the conversion from a covered life to realized "
            "value is gated by engagement, and the enterprise value is gated by "
            "renewal (net revenue retention). Because distribution runs through "
            "benefits consultants on an annual cycle, growth is lumpy and "
            "relationship-dependent. A credible volume model multiplies "
            "contracted lives by a defensible, cohort-based engagement curve and "
            "a realistic renewal rate — not signed-logo counts or a hoped-for "
            "activation rate."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Navigation labor (nurses, care coordinators, advocates)",
            "#1 — the COGS",
            "Human-delivered navigation is the dominant cost; cost-to-serve per "
            "engaged member against fixed PMPM sets gross margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Enterprise sales & account management (consultant-mediated)",
            "high",
            "Long B2B sales cycles through benefits consultants plus ongoing "
            "account management — a heavy, relationship-driven cost.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Technology platform, data integration & analytics",
            "~15-22% of cost",
            "Claims/benefits/eligibility integrations, routing engines, and "
            "savings analytics — the scalable-deflection layer.", "ILLUSTRATIVE"),
        CostDriver(
            "Point-solution integration & partner management",
            "~8-12% of cost",
            "Wiring and managing the aggregated point solutions behind the front "
            "door — the cost of being the aggregator.", "ILLUSTRATIVE"),
        CostDriver(
            "Compliance, privacy & implementation",
            "~8-12% of cost",
            "HIPAA/ERISA compliance, security, and the resource-heavy employer "
            "onboarding/implementation.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "Navigation is delivered nationally to employer and plan populations, so "
        "a facility map is not the structure read and none is fabricated. The "
        "honest geographic lens is where covered lives concentrate (large self-"
        "insured employer footprints and plan enrollment) and, for the clinical "
        "layer, state nurse-licensure reach; the emerging public rails vary by "
        "state (Medicaid care-coordination) on top of the national employer-PMPM "
        "core. Use the covered-population, Medicaid-coordination, and deal-history "
        "connectors below rather than a provider census."),
)

register(REPORT)
