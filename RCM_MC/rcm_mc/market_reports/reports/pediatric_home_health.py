"""Pediatric PDN — pediatric private-duty nursing for medically-complex kids.

Deals-only deep-dive (state PDN provider rosters are not vendored). Authored
around the structural fact that this is a Medicaid rate-versus-wage spread
business: hourly skilled nursing for ventilator/trach/feeding-tube children,
paid almost entirely by Medicaid under the EPSDT entitlement, where the binding
constraint is nurse supply and the defining revenue governor is authorized hours
that cannot be staffed. Distinct from adult home health's episodic PDGM model
(``home_health``).
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks,
    Kpi, MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule,
    Segment, Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="pediatric_home_health",
    name="Pediatric PDN",
    care_setting="Post-acute",
    naics="621610",
    one_line_def=(
        "Hourly, in-home skilled (RN/LPN) private-duty nursing for medically-"
        "complex, technology-dependent children — ventilator, tracheostomy, "
        "and feeding-tube kids — paid almost entirely by Medicaid under the "
        "EPSDT mandate and billed hourly (shift care), not per episode like "
        "adult home health."),
    tam_headline=TamHeadline(
        value=6.0, unit="$B", growth_pct=8.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US pediatric private-duty-nursing spend — hourly RN/LPN "
            "shift care for medically-complex children, billed almost entirely "
            "to Medicaid under EPSDT. No published benefit-level figure exists, "
            "so this is a composite of medically-complex-child prevalence × "
            "authorized hours × state hourly rates. Growth is the modeled "
            "composite of rising NICU-survival prevalence and wage-driven rate "
            "increases, capped by nurse supply."),
    ),
    executive_summary=[
        "This is a Medicaid rate-versus-wage spread business. The whole thesis "
        "is whether the state's hourly rate covers a competitive nurse wage "
        "plus overhead; when rates lag (as in 2021-22), the agency cannot hire "
        "and authorized hours go unstaffed.",
        "Demand is effectively infinite and durable — a trach/vent child needs "
        "40-112 hours a week for years — so the constraint is 100% nurse "
        "SUPPLY. 'Unstaffed hours' (authorized but unfilled shifts) is the real "
        "revenue governor, not census.",
        "EPSDT is the legal moat. Under Early and Periodic Screening, "
        "Diagnostic and Treatment, states MUST cover medically-necessary "
        "private-duty nursing for children under 21 — the payer cannot cut the "
        "benefit, only the rate and the authorized hours.",
        "You are a price-taker on Medicaid. The state (or its managed-care "
        "plan) sets the hourly RN/LPN rate and authorizes the hours per child, "
        "so rate advocacy — winning state and legislative rate increases — is a "
        "core operating competency, not a nicety.",
        "Aveanna's post-IPO stumble is the case study: a rate/wage squeeze in a "
        "Medicaid-dependent PDN model is a real, sector-wide risk. Consolidation "
        "is active (Aveanna, Care Options for Kids, Team Select, Angels of "
        "Care) but the winners are the ones who can staff.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral — typically from a NICU/PICU discharge or a "
            "medically-complex-care clinic",
            "Medical-necessity determination + Medicaid eligibility (often via "
            "Katie Beckett/TEFRA)",
            "Prior authorization of weekly nursing hours (RN vs LPN) by the "
            "state or MCO",
            "Nurse recruiting, competency check, and case-specific training "
            "(vent/trach)",
            "Staffing / scheduling nurses to the authorized shift hours",
            "Shift delivery in the home + Electronic Visit Verification (EVV) "
            "capture",
            "RN case-management oversight, billing, and reauthorization of "
            "hours",
        ],
        sites_of_care=[
            "The child's home (the overwhelming majority — long-hours shift "
            "care)",
            "School (nurse accompanies the medically-complex child where "
            "authorized)",
            "Transition from hospital NICU/PICU to home (the referral moment)",
        ],
        money_flow=(
            "Revenue is authorized hours × a Medicaid hourly rate, split by "
            "clinician level (a higher RN rate, a lower LPN rate). The state "
            "Medicaid program — directly or through a managed-care plan — sets "
            "that hourly rate and prior-authorizes a weekly hour budget per "
            "child based on medical necessity under the EPSDT entitlement. The "
            "agency bills the authorized, staffed hours and captures the spread "
            "between the state rate and the nurse's wage, net of RN case "
            "management, recruiting, EVV/compliance, and overhead. Because the "
            "rate is fixed by the state and the hours are fixed by "
            "authorization, the only variables the agency controls are nurse "
            "cost and how many authorized hours it can actually staff — so the "
            "P&L is a labor arbitrage governed by nurse supply, and every "
            "authorized-but-unstaffed hour is revenue the agency is entitled to "
            "but cannot bill."),
        key_players=(
            "Aveanna Healthcare is the bellwether — the largest pediatric "
            "home-health/PDN platform (a roll-up of PSA and Epic, now publicly "
            "traded) whose post-IPO struggles with the Medicaid rate/wage "
            "squeeze define the sector's risk narrative. BAYADA (nonprofit) is "
            "a large, respected operator; PE-backed platforms include Care "
            "Options for Kids, Team Select Home Care, Angels of Care Pediatric "
            "Home Health, Phoenix Home Care, and Loving Care, alongside Maxim "
            "Healthcare Services and Pediatric Home Service and a long tail of "
            "regional agencies. The key upstream relationships are the "
            "children's-hospital NICU/PICU discharge planners who drive "
            "referrals."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicaid PDN (EPSDT entitlement)", "~90%+ of revenue",
                    "GOV · Medicaid EPSDT (SSA §1905(r)) benefit"),
            Segment("Managed Medicaid (MCO-administered PDN)",
                    "a growing share as states move LTSS to managed care",
                    "GOV · state Medicaid managed-care programs"),
            Segment("Medically-complex / technology-dependent children",
                    "the durable, high-hours census",
                    "ACADEMIC · pediatric complex-care prevalence research"),
            Segment("Commercial / CSHCN / Title V (small)",
                    "a minor supplemental payer slice",
                    "ILLUSTRATIVE · modeled non-Medicaid PDN share"),
        ],
        growth_drivers=[
            "Rising prevalence of medically-complex children — improving NICU "
            "survival",
            "State Medicaid rate increases (the #1 revenue lever) ~3-5%/yr where "
            "won",
            "Nurse-supply expansion — the binding constraint on realizable "
            "hours",
            "Geographic expansion into higher-rate states + tuck-in M&A",
            "Paid-family-caregiver policies letting more authorized hours get "
            "staffed",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicaid (fee-for-service + managed Medicaid)": 0.92,
            "Commercial / CSHCN / Title V": 0.06,
            "Other (waiver / private)": 0.02,
        },
        rate_mechanics=[
            "Medicaid EPSDT (SSA §1905(r)) — the legal engine: states must "
            "cover medically-necessary private-duty nursing for children under "
            "21; the entitlement basis the whole sector rests on.",
            "State hourly rates by clinician level — a higher RN rate and a "
            "lower LPN rate, set by each state, so economics are state-by-"
            "state.",
            "Prior authorization of hours — the state or MCO authorizes a "
            "weekly hour budget per child; getting and defending those hours is "
            "the revenue driver.",
            "Managed Medicaid — as states move LTSS to MCOs, the plan sets "
            "rates and authorizations, adding a payer layer and "
            "utilization-management friction.",
            "Katie Beckett / TEFRA eligibility — pathways that qualify "
            "disabled children for Medicaid regardless of parental income, "
            "expanding the payable population.",
            "Electronic Visit Verification (EVV) — the 21st Century Cures Act "
            "mandate applies to PDN; unverified shifts are denied.",
        ],
        reimbursement_risk=(
            "The dominant risk is the state rate versus the nurse wage. Because "
            "the agency is a price-taker on a fixed hourly Medicaid rate, a rate "
            "that lags the local RN/LPN wage makes recruiting impossible and "
            "authorized hours go unstaffed — the agency cannot bill hours it "
            "cannot fill, so a rate squeeze compresses both margin AND volume "
            "at once (this is exactly what pressured Aveanna post-IPO). "
            "Managed-Medicaid utilization management adds authorization risk: "
            "hours can be trimmed at reauthorization even when the child's need "
            "is unchanged. EVV denies payment for unverified shifts, and "
            "pediatric PDN's high hours per patient concentrate revenue in a "
            "relatively small census, so losing or under-staffing a few "
            "high-hour cases moves the P&L materially."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicaid EPSDT — private-duty nursing mandate (SSA §1905(r))",
                 "Requires states to cover medically-necessary PDN for children "
                 "under 21 — the entitlement that makes demand durable and the "
                 "benefit non-cuttable (only rate/authorization move).",
                 "https://www.medicaid.gov/medicaid/benefits/early-and-periodic-screening-diagnostic-and-treatment/index.html"),
            Rule("State home-health / nursing-agency licensure",
                 "Licensure, survey, and clinical-supervision rules that gate "
                 "participation and vary by state.",
                 None),
            Rule("Electronic Visit Verification (21st Century Cures Act "
                 "§12006)",
                 "Mandates verification of Medicaid home-nursing visits; "
                 "unverified shifts are denied — a compliance and cash-flow "
                 "constraint.",
                 "https://www.medicaid.gov/medicaid/home-community-based-services/guidance/electronic-visit-verification-evv/index.html"),
            Rule("Nurse Practice Acts / LPN scope + delegation",
                 "State scope-of-practice rules determine which tasks LPNs (the "
                 "lower-cost clinician) can perform for vent/trach children — a "
                 "direct staffing-cost lever.",
                 None),
            Rule("Katie Beckett / TEFRA eligibility pathways",
                 "State options that qualify disabled children for Medicaid "
                 "regardless of family income — expanding the payable "
                 "population and, in some states, paid-family-caregiver "
                 "flexibility.",
                 "https://www.medicaid.gov/medicaid/eligibility/index.html"),
        ],
        policy_watch=[
            "State Medicaid PDN rate actions and rate-methodology reviews (the "
            "core revenue variable)",
            "Managed-Medicaid LTSS carve-in and utilization-management "
            "practices",
            "Paid-family-caregiver policies (many expanded during COVID; "
            "permanence varies by state)",
            "Nurse-workforce initiatives and LPN scope changes",
            "EPSDT enforcement and access litigation (the entitlement's teeth)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Fragmented but visibly consolidating. A large regional long tail "
            "of pediatric nursing agencies sits beneath a handful of scaled, "
            "mostly PE-backed platforms. Because the business is a local nurse-"
            "labor arbitrage, density in a state (and that state's rate) matters "
            "more than national footprint. There is no vendored national PDN "
            "roster, so a computed geographic share is honestly omitted."),
        hhi_or_share=(
            "Aveanna is the largest single platform but the overall base is "
            "dispersed across regional operators; concentration is low and "
            "rising. State-level share matters more than national share given "
            "how state rates and nurse pools drive economics."),
        consolidation=(
            "PE has been the primary consolidator: Aveanna assembled the "
            "category's largest platform (PSA + Epic) before its IPO, and "
            "sponsor-backed roll-ups — Care Options for Kids, Team Select, "
            "Angels of Care — have been building state-level density. The buy-"
            "and-build logic is real (back-office and rate-advocacy leverage), "
            "but the integration prize is a staffing machine, not just census."),
        pe_activity=(
            "Active, and chastened. Early theses priced durable, high-hours "
            "census as near-annuity revenue; Aveanna's post-IPO rate/wage "
            "squeeze reset expectations. Today's diligence centers on the fill "
            "rate (staffed vs authorized hours), the state-rate mix and "
            "trajectory, rate-advocacy track record, and nurse recruiting/"
            "retention — the durability of STAFFED hours, not authorized "
            "backlog."),
        notable_players=[
            "Aveanna Healthcare", "BAYADA Home Health Care",
            "Care Options for Kids", "Team Select Home Care",
            "Angels of Care Pediatric Home Health", "Phoenix Home Care",
            "Maxim Healthcare Services", "Pediatric Home Service",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("State rate vs nurse wage (the spread)", "the whole thesis",
                "If the state hourly rate does not clear a competitive RN/LPN "
                "wage plus overhead, the model cannot staff or profit."),
            Kpi("Staffed vs authorized hours (fill rate)", "the revenue "
                "governor",
                "Authorized hours the agency cannot staff are lost, "
                "non-recoverable revenue — the KPI that separates operators."),
            Kpi("Hours per patient / week", "~40-112 for high-acuity kids",
                "Trach/vent children need long, durable hours for years — "
                "sticky, high-revenue, but concentrated census."),
            Kpi("RN vs LPN staffing mix", "a cost lever",
                "Using LPNs where scope allows lowers wage cost against the "
                "state rate — a direct margin driver."),
            Kpi("Gross margin", "~25-30%",
                "The spread over nurse wages; thin and rate-dependent, so "
                "state mix drives it."),
            Kpi("Agency EBITDA margin", "high-single to low-double digits",
                "Back-office and case-management leverage over a nurse base; "
                "sub-scale or low-rate states run thin."),
        ],
        margin_profile=(
            "Pediatric PDN margin is a labor arbitrage on a fixed state hourly "
            "rate, so it is decided by the rate-versus-wage spread, the RN/LPN "
            "staffing mix, and — above all — the fill rate. Unlike most "
            "services businesses, revenue and margin move together with nurse "
            "supply: a rate that lags wages simultaneously compresses the spread "
            "AND leaves authorized hours unstaffed, so a rate squeeze is a "
            "double hit. Census is durable and high-hours (a single vent child "
            "can represent a large, multi-year revenue line), which makes the "
            "book sticky but concentrated. Scale helps by spreading RN case "
            "management, recruiting, and EVV/compliance across more hours and by "
            "funding professional rate advocacy — but it cannot change a state's "
            "rate or manufacture nurses in a tight market, which is why state "
            "mix and local recruiting decide the outcome."),
    ),
    risks=[
        Risk("Medicaid rate vs nurse wage squeeze", "High",
             "A state rate that lags wages compresses margin and strands "
             "authorized hours unstaffed simultaneously — the Aveanna case "
             "study."),
        Risk("Nurse supply / recruiting & retention", "High",
             "The binding constraint; unstaffed authorized hours are lost "
             "revenue, and pediatric vent/trach nursing is a scarce skill."),
        Risk("Managed-Medicaid utilization management", "Medium",
             "MCOs can trim authorized hours at reauthorization even when need "
             "is unchanged, cutting revenue per child."),
        Risk("Revenue concentration in high-hour cases", "Medium",
             "High hours per patient concentrate revenue in a small census, so "
             "losing or under-staffing a few cases moves the P&L."),
        Risk("EVV / compliance & billing integrity", "Medium",
             "Unverified shifts are denied and pediatric PDN billing invites "
             "audit scrutiny; documentation discipline is underwriting."),
        Risk("Single-state / payer concentration", "Medium",
             "Heavy dependence on one state's rate or one MCO creates outsized "
             "exposure to a single rate or policy action."),
    ],
    diligence_questions=[
        "What is the state-rate mix across the book, and what is the recent "
        "rate-action history and outlook in each state?",
        "What is the fill rate — staffed vs authorized hours — and how has it "
        "trended?",
        "What is the RN vs LPN staffing mix, and how much wage cost could scope-"
        "appropriate LPN use save?",
        "How concentrated is revenue by patient, by state, and by MCO, and what "
        "is the reauthorization risk?",
        "What is nurse turnover, cost-per-hire, and time-to-fill, and what is "
        "the referral pipeline from NICU/PICU discharge?",
        "What is the rate-advocacy track record — has the operator won state or "
        "legislative rate increases?",
        "What is the EVV/compliance posture and the audit / recoupment "
        "history?",
        "What share of authorized hours is currently unstaffed, and what is the "
        "backlog of unmet authorizations (latent, un-billable demand)?",
    ],
    insider_lens=[
        "It is a rate-minus-wage spread wearing a clinical uniform. The entire "
        "question is whether the state's hourly rate clears a competitive nurse "
        "wage plus overhead — everything else is execution on top of that "
        "spread.",
        "Demand is not the constraint; nurses are. You can hold more authorized "
        "hours than you will ever staff, so 'unstaffed hours' — not census — is "
        "the real revenue governor. Always diligence the fill rate.",
        "A rate squeeze is a double hit. When rates lag wages you lose margin on "
        "the hours you staff AND lose volume on the hours you cannot — which is "
        "precisely how a Medicaid-dependent PDN platform (see Aveanna) gets "
        "caught out.",
        "EPSDT is the moat and the ceiling. The benefit cannot be cut — states "
        "must cover medically-necessary PDN for kids — but the state controls "
        "the rate and the authorized hours, so the payer squeezes on price and "
        "utilization, not on eligibility.",
        "Rate advocacy is a core competency. The best operators treat winning "
        "state and legislative rate increases as an operating discipline — it is "
        "the single biggest lever on both margin and staffable volume.",
        "The census is sticky but concentrated. One vent child at 100+ hours a "
        "week for years is a large, durable revenue line — great for retention, "
        "but it means a handful of cases (and whether you can staff them) can "
        "swing the P&L.",
    ],
    connections=default_connections(
        "pediatric_home_health",
        deals_sector="pediatric_home_health",
        extra_pages=[
            ("/market/home_health",
             "Adjacency — the Home Health report (adult episodic PDGM, the "
             "contrast model)"),
            ("/diligence/tam-sam?template=pediatric_home_health",
             "Size it — pediatric-PDN TAM/SAM build (complex-child prevalence × "
             "hours × rate)"),
        ],
        connectors=[
            ("medicaid_data_enrollment_monthly",
             "Medicaid enrollment (monthly) — the child-eligible base under "
             "EPSDT"),
            ("medicaid_data_managed_care_by_state_2024",
             "Medicaid managed care by state — the MCO layer that sets rates & "
             "authorizations"),
            ("bls_qcew_industry_area",
             "BLS QCEW — home-health nursing employment & wages (the binding "
             "labor pool)"),
            ("cdc_data_vsrr_birth_indicators",
             "CDC VSRR birth indicators — the NICU-survival prevalence upstream "
             "of demand"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
        ],
    ),
    sources=[
        Source("CMS / Medicaid.gov — EPSDT benefit and private-duty nursing "
               "coverage for children", "GOV",
               "https://www.medicaid.gov/medicaid/benefits/early-and-periodic-screening-diagnostic-and-treatment/index.html"),
        Source("Medicaid.gov — Electronic Visit Verification (EVV) guidance",
               "GOV",
               "https://www.medicaid.gov/medicaid/home-community-based-services/guidance/electronic-visit-verification-evv/index.html"),
        Source("Pediatrics / academic research on children with medical "
               "complexity (prevalence, home-nursing need)", "ACADEMIC",
               "https://publications.aap.org/pediatrics"),
        Source("Aveanna Healthcare — SEC filings (Medicaid rate/wage dynamics, "
               "the sector bellwether)", "INDUSTRY",
               "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=aveanna"),
        Source("National Association for Home Care & Hospice (NAHC) — pediatric "
               "home-care policy and benchmarking", "INDUSTRY",
               "https://www.nahc.org/"),
        Source("PE Desk industry deep-dive (deals-only) + realized-deal "
               "corpus for pediatric PDN", "INTERNAL",
               "/diligence/tam-sam?template=pediatric_home_health"),
    ],
    live_figures=live_figures_from_dive("pediatric_home_health"),
    trends=(
        "Pediatric private-duty nursing looked, for years, like a near-annuity: "
        "an EPSDT entitlement, durable high-hours census (vent/trach children "
        "needing care for years), and a fragmented base ripe for roll-up. PE "
        "consolidated aggressively — Aveanna built the category's largest "
        "platform and went public in 2021. Then the model's real constraint "
        "asserted itself. As nurse wages spiked in 2021-22 while state Medicaid "
        "rates lagged, agencies could not staff the hours they were authorized "
        "to provide; the spread compressed and volume stranded at once, and "
        "Aveanna's post-IPO reset became the sector's cautionary tale. The "
        "response reframed the playbook: rate advocacy became a core "
        "competency, operators pushed states and legislatures for PDN rate "
        "increases (many succeeded), managed those states' RN/LPN mix, and "
        "leaned on paid-family-caregiver flexibilities that emerged during "
        "COVID. Underneath, demand keeps rising as NICU survival improves the "
        "prevalence of medically-complex children — the entitlement guarantees "
        "the need — but the durable lesson is that this is a nurse-supply and "
        "state-rate business first, and a census-growth business second."),
    growth_levers=[
        GrowthLever(
            "State Medicaid rate increases",
            "The #1 lever — winning higher state/legislative PDN rates lifts "
            "both margin and the wage the agency can offer to staff more "
            "hours.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Medically-complex-child prevalence",
            "Improving NICU survival raises the number of technology-dependent "
            "children needing durable home nursing.",
            "+prevalence", "ACADEMIC"),
        GrowthLever(
            "Nurse-supply expansion",
            "More recruitable RNs/LPNs converts authorized hours into staffed, "
            "billable hours — the binding lever on realizable volume.",
            "capacity-driven", "ILLUSTRATIVE"),
        GrowthLever(
            "Geographic expansion + tuck-in M&A",
            "Entering higher-rate states and rolling up regional agencies "
            "builds state-level density and back-office leverage.",
            "M&A", "ILLUSTRATIVE"),
        GrowthLever(
            "Paid-family-caregiver policies",
            "Allowing trained family members to be paid caregivers staffs hours "
            "that would otherwise go unfilled.",
            "capacity policy", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Medically-complex children × authorized hours — gated by nurse "
               "supply",
        analysis=(
            "The demand base is the population of children with medical "
            "complexity — technology-dependent kids on ventilators, "
            "tracheostomies, and feeding tubes — whose numbers rise "
            "structurally as NICU and PICU survival improves. Each such child "
            "carries very high, very durable authorized hours (often 40-112 "
            "per week for years), and EPSDT legally guarantees coverage, so the "
            "authorized-hour pool grows faster than the pediatric population "
            "itself. But the realizable volume is gated by nurse supply: the "
            "agency can only bill the authorized hours it can staff, and "
            "pediatric vent/trach nursing is a scarce, specialized skill. The "
            "honest read is that prevalence and the entitlement set an ample, "
            "growing ceiling of authorized hours, while nurse recruiting and "
            "the state rate that funds nurse wages set the binding floor of "
            "staffed, billable hours — and the floor is what moves."),
        basis="ACADEMIC"),
    cost_drivers=[
        CostDriver(
            "Nurse wages (RN / LPN)",
            "~70%+ of revenue",
            "The dominant cost and the other side of the spread; the RN/LPN mix "
            "against the state rate is the core margin lever.", "ILLUSTRATIVE"),
        CostDriver(
            "Recruiting & retention",
            "#2 cost driver",
            "Sourcing and keeping scarce pediatric vent/trach nurses is a "
            "large, recurring cost — and the constraint on staffable hours.",
            "ILLUSTRATIVE"),
        CostDriver(
            "RN case management & clinical supervision",
            "~8-12% of revenue",
            "Required oversight of complex pediatric cases, care-plan "
            "management, and family training.", "ILLUSTRATIVE"),
        CostDriver(
            "Scheduling, billing & back office",
            "~8-12% of revenue",
            "Matching nurses to authorized shifts, authorization management, "
            "and Medicaid billing — where scale leverage lives.",
            "ILLUSTRATIVE"),
        CostDriver(
            "EVV & compliance technology",
            "smaller but mandatory",
            "Electronic Visit Verification and documentation compliance — a "
            "condition of Medicaid payment for every shift.", "ILLUSTRATIVE"),
    ],
    # Deals-only vertical: no provider_backed CMS roll, so cms_trend and a
    # computed state_breakdown are intentionally omitted — the renderer shows an
    # honest "unavailable offline" note and the qualitative sections carry the
    # weight.
)

register(REPORT)
