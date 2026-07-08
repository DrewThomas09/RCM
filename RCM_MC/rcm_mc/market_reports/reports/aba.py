"""ABA / Autism — Applied Behavior Analysis therapy for autism spectrum disorder.

Deals-only deep-dive (no public ABA-provider census; BACB certificant counts
are aggregate-only, so geography is omitted rather than fabricated). Consumes
``aba_deep_dive()`` for SOURCED corpus figures where the corpus tags them. The
qualitative sections are authored around the economics that actually broke the
2017-2021 ABA boom: a technician-delivered, 15-minute-unit service on
prior-authorized hours, where RBT turnover and cancellation rates — not demand
— decide whether a center makes money, and where commercial rate cuts and
Medicaid EPSDT rate variance set the ceiling.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="aba",
    name="ABA / Autism",
    care_setting="Behavioral",
    naics="621340",
    one_line_def=(
        "Applied Behavior Analysis — the evidence-based, medically-necessary "
        "treatment for autism spectrum disorder in which Board Certified "
        "Behavior Analysts (BCBAs) design programs delivered largely by "
        "Registered Behavior Technicians (RBTs) in 15-minute units, in-home or "
        "in center-based clinics, paid by commercial autism mandates and "
        "Medicaid EPSDT."),
    tam_headline=TamHeadline(
        value=6.0, unit="$B", growth_pct=9.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US ABA-services revenue is modeled at ~$5-7B; the anchor is a "
            "GOV prevalence figure (CDC: autism in ~1 in 36 US 8-year-olds) "
            "times realized treatment penetration and payer rates. Growth is "
            "the modeled composite of prevalence/diagnosis (+5.0%), coverage "
            "mandates (+3.0%), and access capacity (+1.0%)."),
    ),
    executive_summary=[
        "ABA is a technician-labor business with a supervisory license on top. "
        "RBTs deliver the direct therapy hours (billed in 15-minute units, CPT "
        "97153); BCBAs assess, design, and supervise (97151/97155/97156). The "
        "economics are a spread between the payer's per-unit rate and the "
        "loaded RBT wage — and RBT turnover (often 50%+ a year) is the single "
        "biggest destroyer of that spread.",
        "Demand is real and rising but capacity-constrained. CDC autism "
        "prevalence has climbed to ~1 in 36 children, every state mandates "
        "commercial coverage, and Medicaid EPSDT requires it for kids — yet "
        "waitlists are long because the constraint is RBT/BCBA supply, not "
        "diagnosed need.",
        "Cancellations and authorized-hours utilization are the quiet P&L. A "
        "child authorized for 30 hours a week who receives 20 (illness, "
        "school, no-shows, staffing gaps) turns a full schedule into a "
        "half-full one on a fixed technician cost — center-based models exist "
        "largely to defend utilization.",
        "The 2017-2021 boom overbuilt and repriced. Sponsor capital chased "
        "prevalence into a wave of roll-ups; then commercial payers cut per-"
        "unit rates, RBT wages rose, and thin margins turned negative — "
        "producing distress, down-rounds, and center closures across several "
        "platforms.",
        "Payer mix is destiny. Commercial autism-mandate rates are higher but "
        "under pressure and heavy on prior authorization; Medicaid EPSDT rates "
        "vary enormously by state and can be below the cost of delivery. The "
        "reimbursement question is per-state and per-payer, not national.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Autism diagnosis (developmental pediatrician / psychologist — the "
            "referral gate and a bottleneck of its own)",
            "Insurance benefit verification + prior authorization for an "
            "assessment",
            "BCBA assessment + treatment plan (97151) — sets authorized "
            "hours/week",
            "Prior authorization of the ongoing hour block (the payer gate on "
            "revenue)",
            "RBT-delivered direct therapy (97153, per 15 min) — in-home or "
            "center-based",
            "BCBA protocol modification + supervision (97155) and caregiver "
            "training (97156)",
            "Progress reporting, reassessment, and reauthorization; billing, "
            "and the cancellation/utilization reconciliation",
        ],
        sites_of_care=[
            "Center-based clinic (defends utilization + supervision ratios — "
            "the preferred model)",
            "In-home therapy (family-preferred, natural environment; harder to "
            "keep RBTs utilized)",
            "School / community settings",
            "Telehealth (parent training and some supervision; limited for "
            "direct RBT therapy)",
        ],
        money_flow=(
            "ABA is billed in 15-minute units against a prior-authorized weekly "
            "hour block. The direct-therapy code (97153), delivered by an RBT, "
            "is the volume and the revenue base; BCBA codes for assessment "
            "(97151), protocol modification/supervision (97155), and caregiver "
            "training (97156) layer on top. Commercial payers — obligated by "
            "state autism-insurance mandates — pay a per-unit rate that is "
            "generally higher than Medicaid but comes with aggressive prior "
            "authorization and periodic rate cuts; Medicaid, obligated by EPSDT "
            "to cover medically-necessary services for children, pays state-set "
            "per-unit rates that swing widely and can fall below delivery cost. "
            "The provider's margin is the per-unit rate minus the loaded RBT "
            "wage (and the BCBA supervision overlaid on it), so realized "
            "profitability is a product of the rate, the RBT wage, and — "
            "decisively — how many of the authorized units actually get "
            "delivered after cancellations and staffing gaps."),
        key_players=(
            "A fragmented field consolidated by sponsor-backed platforms: "
            "LEARN Behavioral, Hopebridge, Autism Learning Partners, Action "
            "Behavior Centers, BlueSprig Pediatrics, Centria Autism, Behavioral "
            "Health Works, Kadiant, Butterfly Effects, and integrated models "
            "like Cortica (medical + ABA). The BACB (Behavior Analyst "
            "Certification Board) sets the BCBA and RBT credentials that define "
            "the labor supply. The acquirable pool is the very long tail of "
            "independent and regional ABA providers; the strategic buyers are "
            "the scaled platforms and, increasingly, payers' own care arms."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US ABA-services revenue (modeled)", "~$5-7B",
                    "ILLUSTRATIVE · prevalence × penetration × rate model"),
            Segment("Autism prevalence in US children", "~1 in 36 (8-yr-olds)",
                    "GOV · CDC ADDM Network surveillance"),
            Segment("States mandating commercial ABA coverage", "all 50",
                    "GOV · state autism-insurance-mandate laws"),
            Segment("Medicaid EPSDT pediatric coverage", "required for <21",
                    "GOV · Medicaid EPSDT benefit"),
            Segment("Direct-therapy delivery (RBT hours)",
                    "the bulk of billed units",
                    "ILLUSTRATIVE · service-model structure, directional"),
        ],
        growth_drivers=[
            "Autism prevalence + earlier diagnosis ~5.0%/yr",
            "Universal commercial mandates + Medicaid EPSDT ~3.0%/yr",
            "Access capacity (RBT/BCBA supply) ~1.0%/yr — the real ceiling",
            "Diagnostic-bottleneck relief (screening, telehealth dx)",
            "Payer rate cuts + wage inflation — a margin, not a volume, drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial (autism mandates)": 0.55,
            "Medicaid / MCO (EPSDT)": 0.40,
            "Self-pay / other": 0.05,
        },
        rate_mechanics=[
            "Adaptive-behavior CPT codes billed in 15-minute units: 97153 "
            "(RBT-delivered direct therapy — the volume), 97151 (BCBA "
            "assessment), 97155 (BCBA protocol modification/supervision), 97156 "
            "(family/caregiver training).",
            "Commercial autism mandates — every state requires commercial plans "
            "to cover ABA; rates are payer-negotiated per unit, higher than "
            "Medicaid but declining and prior-authorization-heavy.",
            "Medicaid EPSDT — federally required coverage of medically-"
            "necessary services for children; per-unit rates are STATE-SET and "
            "vary widely, sometimes below delivery cost.",
            "Prior authorization of the weekly hour block — the payer's primary "
            "utilization lever; reauthorization gates continued revenue.",
            "Supervision-ratio and concurrent-billing rules — payers limit "
            "BCBA-to-RBT ratios and whether supervision can be billed "
            "concurrently with direct therapy.",
            "Cancellation / make-up policy — unbilled cancelled units are lost "
            "revenue on a fixed technician cost; some payers restrict make-up "
            "sessions.",
        ],
        reimbursement_risk=(
            "The reimbursement risk is a two-sided squeeze on a thin per-unit "
            "spread. On price, commercial payers have moved from expanding "
            "coverage to cutting per-unit rates and tightening prior "
            "authorization and supervision-ratio rules, while Medicaid EPSDT "
            "rates are state-set and in many states sit at or below the loaded "
            "cost of an RBT hour — so a Medicaid-heavy book in a low-rate state "
            "can be structurally unprofitable. On volume actually paid, "
            "authorized hours are routinely under-delivered because of "
            "cancellations, RBT vacancies, and children's school/illness "
            "schedules, so a center bills well below its authorized (and "
            "staffed-for) capacity. Layered on top is program-integrity "
            "scrutiny: OIG and payers audit RBT-supervision documentation, "
            "credential currency, and 'ghost' or upcoded units, with recoupment "
            "exposure. The result is a model where the same clinical service can "
            "be a good business or a losing one depending entirely on state, "
            "payer, wage market, and utilization discipline."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("State autism-insurance mandates (all 50 states)",
                 "Require commercial plans to cover ABA — the coverage "
                 "foundation of the commercial book, but the mandated benefit "
                 "does not fix the negotiated per-unit rate.",
                 "https://www.ncsl.org/health/autism-and-insurance-coverage-state-laws"),
            Rule("Medicaid EPSDT (Early and Periodic Screening, Diagnostic and "
                 "Treatment)",
                 "Obligates Medicaid to cover medically-necessary services, "
                 "including ABA, for enrollees under 21 — the pediatric-Medicaid "
                 "mandate, at state-set rates.",
                 "https://www.medicaid.gov/medicaid/benefits/early-and-periodic-screening-diagnostic-and-treatment"),
            Rule("BACB credentialing (BCBA / BCaBA / RBT)",
                 "The Behavior Analyst Certification Board defines the license "
                 "structure and supervision requirements that govern who can "
                 "deliver and bill ABA — and thus the labor supply.",
                 "https://www.bacb.com/"),
            Rule("State licensure of behavior analysts",
                 "A growing majority of states now license BCBAs directly, "
                 "adding a state credential (and enforcement surface) on top of "
                 "BACB certification.",
                 None),
            Rule("OIG / payer audits of ABA billing and supervision",
                 "Scrutiny of RBT-supervision documentation, credential "
                 "currency, concurrent billing, and unit integrity — recoupment "
                 "and exclusion exposure.",
                 "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        ],
        policy_watch=[
            "Commercial per-unit rate trajectory and prior-auth tightening",
            "State Medicaid EPSDT rate reviews (and the low-rate states)",
            "Spread of direct state licensure of behavior analysts",
            "OIG audit activity on RBT supervision and unit documentation",
            "Telehealth allowances for supervision and caregiver training",
            "Diagnostic-capacity policy (who can diagnose autism, how fast)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Highly fragmented and, until recently, rapidly consolidating. "
            "Thousands of independent and regional ABA providers were the "
            "roll-up feedstock for a wave of sponsor-backed platforms; no owner "
            "holds meaningful national share. The fragmentation is a labor "
            "artifact — ABA is delivered locally by scarce, high-turnover "
            "technicians — so scale advantages accrue to recruiting, "
            "credentialing, scheduling, and payer contracting rather than to "
            "brand."),
        hhi_or_share=(
            "No national concentration; the largest platforms hold "
            "low-single-digit shares of a fragmented base. There is no public "
            "ABA-provider census (BACB certificant data is aggregate-only), so "
            "operator concentration is honestly not measured here."),
        consolidation=(
            "The 2017-2021 period was a classic prevalence-driven roll-up: "
            "sponsors (KKR/BlueSprig, Blackstone/Action Behavior Centers, "
            "General Atlantic, TPG, Arsenal/CD&R via Hopebridge, and others) "
            "assembled multi-state platforms. Consolidation logic was real — "
            "center density, supervision leverage, and payer-contract scale — "
            "but the wave outran the labor market and the rate environment, and "
            "several platforms retrenched, closed centers, or restructured."),
        pe_activity=(
            "Once one of the hottest PE theses in healthcare services, now a "
            "cautionary case study in labor-intensive roll-ups. Entry multiples "
            "compressed as commercial rate cuts and RBT wage inflation turned "
            "thin margins negative at the overbuilt platforms. Live diligence "
            "centers on RBT turnover and wage trends, authorized-hours "
            "utilization, payer/state rate exposure, and center-level (not "
            "blended) unit economics."),
        notable_players=[
            "LEARN Behavioral", "Hopebridge", "Autism Learning Partners",
            "Action Behavior Centers", "BlueSprig Pediatrics",
            "Centria Autism", "Behavioral Health Works", "Cortica",
            "Butterfly Effects", "Kadiant",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / billed hour (blended)", "$60-120",
                "Commercial-mandate rates sit above Medicaid EPSDT; the blend "
                "and the state/payer mix set the ceiling on margin."),
            Kpi("RBT annualized turnover", "40-65%+",
                "The defining operating metric — churn destroys trained, "
                "billable technician capacity and reloads recruiting/training "
                "cost."),
            Kpi("Authorized-hours utilization (delivered ÷ authorized)",
                "60-85%",
                "Cancellations, illness, school, and vacancies leave paid units "
                "well below staffed capacity — the quiet margin killer."),
            Kpi("Billable ratio (direct RBT hours ÷ paid RBT hours)",
                "70-85%",
                "Non-billable time (training, admin, drive time for in-home) is "
                "pure cost; center-based models exist to raise this."),
            Kpi("BCBA caseload / supervision ratio", "payer- & state-capped",
                "Determines how much billable RBT volume each supervising "
                "analyst can leverage — and compliance risk if stretched."),
            Kpi("Center-level EBITDA margin", "8-15% (illustrative, volatile)",
                "Ramps with occupancy and utilization; a low-rate/high-wage "
                "market can be structurally breakeven or negative."),
        ],
        margin_profile=(
            "ABA margin is a technician-labor arbitrage that only works at high "
            "utilization. The contribution on a delivered hour is the payer "
            "per-unit rate minus the loaded RBT wage (plus an allocation of "
            "BCBA supervision); that spread is thin to begin with, and it "
            "collapses when authorized hours go undelivered or when RBT turnover "
            "forces overtime, agency labor, and constant retraining. Center-"
            "based delivery raises the billable ratio and supervision leverage "
            "versus in-home, which is why the industry migrated toward centers "
            "— but a center is a fixed cost that empty chairs punish. The single "
            "clearest read on a platform's health is center-level (not blended) "
            "unit economics against its local wage and rate environment; blended "
            "numbers hide the losing centers subsidized by the winning ones."),
    ),
    risks=[
        Risk("RBT / BCBA supply, turnover, and wage inflation", "High",
             "The binding constraint and the top cost line; churn destroys "
             "billable capacity and reloads training cost."),
        Risk("Commercial per-unit rate cuts + prior-auth tightening", "High",
             "Payers moved from expanding coverage to compressing the per-unit "
             "spread the whole model runs on."),
        Risk("Medicaid EPSDT rate variance (low-rate states)", "High",
             "State-set rates can sit below the loaded cost of an RBT hour, "
             "making a Medicaid-heavy book structurally unprofitable."),
        Risk("Authorized-hours under-utilization (cancellations)", "Medium",
             "Delivered units fall well short of authorized/staffed capacity, "
             "eroding margin on a fixed technician cost."),
        Risk("Program-integrity audits (supervision, unit documentation)",
             "Medium",
             "OIG/payer scrutiny of RBT supervision, credential currency, and "
             "unit integrity carries recoupment and exclusion exposure."),
        Risk("Overbuilt-platform integration / distress", "Medium",
             "The 2017-2021 roll-up wave left multi-site platforms with "
             "underperforming centers and integration debt."),
    ],
    diligence_questions=[
        "What is RBT turnover, the loaded RBT wage trend, and the local "
        "recruiting market by center?",
        "What is authorized-hours utilization (delivered ÷ authorized) and the "
        "cancellation rate, and how do they trend?",
        "What is the payer AND state mix, and what is the per-unit rate by "
        "payer/state versus the loaded cost to deliver?",
        "What are center-level unit economics — which centers make money, "
        "which lose it, and why (rate, wage, utilization)?",
        "What is the billable ratio, and how much non-billable time (training, "
        "drive time, admin) is being carried?",
        "What is the BCBA supervision ratio versus payer/state caps, and is any "
        "concurrent-billing or supervision-documentation risk present?",
        "What is the diagnostic-referral pipeline and waitlist, and how "
        "dependent is intake on a few referral sources?",
        "What is the OIG/payer audit history and any recoupment reserve?",
    ],
    insider_lens=[
        "The child is authorized for 30 hours and receives 20. The gap between "
        "authorized and delivered hours — cancellations, illness, school, RBT "
        "vacancies — is where ABA margins quietly die, because the technician is "
        "staffed and paid for the full schedule. Underwrite delivered units, "
        "never authorized ones.",
        "It is a wage-arbitrage business, and the wage moved. The whole model "
        "is a spread between the payer's per-unit rate and the loaded RBT wage; "
        "when RBT wages rose and commercial rates fell in 2022-2023, that spread "
        "inverted at overbuilt platforms — which is why an ABA thesis is really "
        "a bet on the local labor market, not on autism prevalence.",
        "Blended margins lie in ABA. A platform is a portfolio of centers, and "
        "the winners subsidize the losers; the honest read is center-level "
        "economics against each center's local rate and wage, not the "
        "consolidated P&L.",
        "The rate is per-state, not national. Two identical centers can be a "
        "good and a bad business purely because one is in a high commercial-rate "
        "state and the other lives on low Medicaid EPSDT rates — the "
        "reimbursement diligence has to be done state by state and payer by "
        "payer.",
        "The bottleneck upstream is diagnosis. Even with infinite RBTs, volume "
        "is gated by how fast children can get an autism diagnosis from a scarce "
        "developmental pediatrician or psychologist — platforms that solve the "
        "diagnostic front door control their own intake.",
        "Supervision is where compliance and margin collide. Stretching BCBA "
        "caseloads leverages more billable RBT volume per analyst — and is "
        "exactly what payer audits and state licensure rules target. The "
        "efficiency move and the audit risk are the same move.",
    ],
    connections=default_connections(
        "aba",
        deals_sector="behavioral_health",
        extra_pages=[
            ("/industry/aba",
             "Industry deep-dive — ABA / autism deal history + structure"),
        ],
        connectors=[
            ("census_acs_county_profile",
             "Census ACS — child population (under-18) by county, the ABA "
             "demand denominator"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — behavior-analyst & behavioral providers (labor "
             "supply proxy)"),
            ("hrsa_data_hpsa_mental_health",
             "HRSA Mental-Health HPSAs — shortage geography that gates access"),
            ("medicaid_data_managed_care_by_state_2024",
             "Medicaid managed care by state — the EPSDT payer structure that "
             "sets ABA rates"),
            ("cdc_data_disability_dhds",
             "CDC Disability & Health Data System — developmental-disability "
             "prevalence context"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded providers (billing-integrity screen)"),
        ],
    ),
    sources=[
        Source("CDC — Autism and Developmental Disabilities Monitoring (ADDM) "
               "Network prevalence estimates (~1 in 36)", "GOV",
               "https://www.cdc.gov/autism/data-research/"),
        Source("Medicaid — Early and Periodic Screening, Diagnostic and "
               "Treatment (EPSDT) benefit", "GOV",
               "https://www.medicaid.gov/medicaid/benefits/early-and-periodic-screening-diagnostic-and-treatment"),
        Source("NCSL — Autism and insurance coverage: state laws", "GOV",
               "https://www.ncsl.org/health/autism-and-insurance-coverage-state-laws"),
        Source("Behavior Analyst Certification Board (BACB) — credential and "
               "supervision standards", "INDUSTRY", "https://www.bacb.com/"),
        Source("AMA CPT — Category I adaptive-behavior codes (97151-97158)",
               "INDUSTRY", "https://www.ama-assn.org/practice-management/cpt"),
        Source("HHS OIG — reviews of Medicaid/commercial ABA billing and "
               "supervision", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("PE Desk industry deep-dive (ABA / autism) + realized-deal "
               "corpus", "INTERNAL", "/diligence/tam-sam?template=aba"),
    ],
    live_figures=live_figures_from_dive("aba"),
    trends=(
        "ABA's arc is a textbook prevalence-driven boom and reckoning. Rising "
        "CDC autism prevalence (from roughly 1 in 150 in 2000 to about 1 in 36 "
        "today), the completion of commercial coverage mandates across all 50 "
        "states, and the Medicaid EPSDT obligation created a demand backdrop "
        "that looked unlimited — and from about 2017 to 2021 sponsor capital "
        "poured into multi-state roll-ups (BlueSprig, Action Behavior Centers, "
        "Hopebridge, LEARN, Autism Learning Partners, Centria) building center "
        "density on the thesis that prevalence would fill every chair. It did "
        "not pencil the way the models assumed. The service is delivered by "
        "high-turnover RBTs on a thin per-unit spread, and two things moved "
        "against it at once: RBT wages rose sharply in the tight 2022-2023 labor "
        "market while commercial payers pivoted from expanding coverage to "
        "cutting per-unit rates and tightening prior authorization. Combined "
        "with chronic under-utilization of authorized hours, the spread inverted "
        "at overbuilt platforms, producing center closures, restructurings, and "
        "multiple compression. The forward story is a flight to operating "
        "discipline — center-level utilization, RBT retention, and state/payer "
        "rate selection — plus relief on the diagnostic bottleneck and a slow "
        "shift toward integrated (medical + ABA) and outcomes-measured models "
        "that payers will defend."),
    growth_levers=[
        GrowthLever(
            "Autism prevalence + earlier/broader diagnosis",
            "CDC prevalence has risen to ~1 in 36 children and diagnostic "
            "criteria/awareness keep widening the identified pool — the "
            "demographic engine.",
            "+5.0%/yr diagnosed", "GOV"),
        GrowthLever(
            "Universal coverage mandates (commercial + EPSDT)",
            "All 50 states mandate commercial ABA coverage and Medicaid EPSDT "
            "requires it for children — the addressable pool is fully covered "
            "on paper.",
            "+3.0%/yr covered", "GOV"),
        GrowthLever(
            "Access capacity (RBT/BCBA supply)",
            "Realized volume is gated by technician and analyst supply, not "
            "demand — capacity growth is the true throttle on the market.",
            "+1.0%/yr capacity", "ILLUSTRATIVE"),
        GrowthLever(
            "Diagnostic-bottleneck relief",
            "Faster screening and diagnosis (telehealth dx, PCP screening) "
            "shortens the front-door queue that limits intake.",
            "pipeline unlock", "ILLUSTRATIVE"),
        GrowthLever(
            "Rate cuts + wage inflation drag",
            "Commercial per-unit rate compression and RBT wage growth squeeze "
            "the spread — a margin headwind, not a volume one.",
            "−margin", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Autism prevalence in children, gated by RBT/BCBA capacity",
        analysis=(
            "The demand base is pediatric autism prevalence, which the CDC's "
            "ADDM Network now estimates at roughly 1 in 36 US 8-year-olds — up "
            "several-fold since 2000 as diagnostic criteria broadened and "
            "awareness and screening improved. Because ABA is the established "
            "medically-necessary treatment and coverage is universal on paper "
            "(commercial mandates in all 50 states, Medicaid EPSDT for "
            "children), the covered addressable population is very large and "
            "still growing. The binding constraint on realized volume is not "
            "demand but delivery capacity: the supply of RBTs to provide direct "
            "hours and BCBAs to assess and supervise, plus the upstream "
            "diagnostic bottleneck of scarce developmental pediatricians and "
            "psychologists who gate entry. That is why waitlists coexist with "
            "overbuilt centers — the market can be simultaneously under-served "
            "(children waiting) and over-supplied (empty chairs) because the "
            "limiting factor is staffed, utilized technician time in the right "
            "local labor market, not the count of diagnosed children."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "RBT direct-care labor",
            "~45-60% of cost",
            "The dominant, largely-variable cost — the technicians who deliver "
            "billed hours. Wage inflation and turnover-driven overtime/agency "
            "use are the margin swing.", "ILLUSTRATIVE"),
        CostDriver(
            "BCBA supervision & clinical leadership",
            "~15-22% of cost",
            "The licensed layer that designs programs and supervises RBTs — "
            "scarce, expensive, and capped by payer/state supervision ratios.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Recruiting, training & credentialing",
            "~6-12% of cost",
            "The perpetual cost of a 40-65% RBT-turnover machine — sourcing, "
            "RBT certification training, and re-credentialing.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Centers / occupancy",
            "~8-14% of cost",
            "The fixed center chassis that utilization must fill; empty chairs "
            "in a center-based model are pure margin loss.", "ILLUSTRATIVE"),
        CostDriver(
            "Billing, prior-auth & compliance",
            "~5-9% of cost",
            "Authorization-heavy RCM plus supervision-documentation and audit-"
            "defense overhead.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "There is no public ABA-provider census — BACB certificant counts are "
        "aggregate-only and providers are not enumerated in a national CMS file "
        "— so state geography is omitted rather than fabricated. The variables "
        "that genuinely differ by state are the Medicaid EPSDT per-unit rate "
        "(which ranges from workable to below delivery cost), whether the state "
        "licenses behavior analysts directly, the local RBT/BCBA labor market "
        "and wage level, and the commercial mandate's negotiated rate "
        "environment. The Census child-population, NPI-taxonomy, HRSA-shortage, "
        "and Medicaid-managed-care connectors linked below are the honest way to "
        "map demand denominators and payer structure by geography."),
)

register(REPORT)
