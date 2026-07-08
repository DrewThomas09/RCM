"""IDD Services — long-term supports for intellectual & developmental disability.

Deals-only deep-dive (state IDD provider rosters are not vendored, so geography
is omitted rather than fabricated). Consumes ``idd_services_deep_dive()`` for
SOURCED corpus figures where the corpus tags them. This is a Medicaid-HCBS
long-term-services vertical, so the sections are authored around the real
mechanics that decide these deals: state-set waiver rates, the Direct Support
Professional (DSP) labor crisis, the HCBS Settings Rule and the 2024 'Access'
80/20 rule, and the deinstitutionalization mandate that Olmstead set in motion.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="idd_services",
    name="IDD Services",
    care_setting="Behavioral",
    naics="623210",
    one_line_def=(
        "Long-term supports and services for people with intellectual and "
        "developmental disabilities — residential group homes and supported "
        "living, day habilitation, supported employment, respite, and in-home "
        "personal supports — delivered by Direct Support Professionals and paid "
        "almost entirely by Medicaid home- and community-based-services (HCBS) "
        "waivers at state-set rates."),
    tam_headline=TamHeadline(
        value=90.0, unit="$B", growth_pct=5.0, basis_label="GOV",
        basis_note=(
            "Medicaid long-term services and supports for people with IDD run "
            "on the order of $80-95B/yr (KFF/CMS Medicaid LTSS/HCBS spending, "
            "IDD share), the large majority now community-based rather than "
            "institutional; growth here is the modeled composite of demand + "
            "waiver expansion (+3.5%), rate updates (+2.5%), and DSP-vacancy "
            "capacity drag (−1.0%)."),
    ),
    executive_summary=[
        "This is a Medicaid HCBS business, top to bottom. The overwhelming "
        "payer is Medicaid via 1915(c) (and related) waivers, and the price of "
        "every service — residential day, day-hab unit, supported-employment "
        "hour — is a STATE-SET rate. There is no commercial upside; the entire "
        "revenue line is a political/administrative variable set state by "
        "state.",
        "The Direct Support Professional shortage is the whole operating story. "
        "DSP wages sit near the bottom of the labor market, turnover routinely "
        "runs 40-50%+, and vacancy rates are structural — so overtime and "
        "agency labor eat the margin, and beds/services go unstaffed even when "
        "demand (and waiver funding) exists.",
        "Demand is enormous and waitlisted. Hundreds of thousands of people "
        "sit on state HCBS waiver waiting lists, and the 'aging family "
        "caregiver' cliff — adults with IDD outliving the parents who care for "
        "them — is a durable, non-discretionary demand driver that converts "
        "waitlist into funded placements over time.",
        "Regulation is reshaping the cost floor. The HCBS Settings Rule pushed "
        "services toward integrated, community settings, and CMS's 2024 "
        "'Ensuring Access' rule requires 80% of certain HCBS payments to reach "
        "direct-care-worker compensation — a direct claim on the operator's "
        "margin residual that is the sector's defining policy risk.",
        "A nonprofit-heavy field is consolidating under PE and strategics. "
        "Sevita (formerly The MENTOR Network), RHA, Dungarvin, Redwood, and "
        "BrightSpring/ResCare are assembling multi-state platforms out of a "
        "fragmented, state-by-state provider base — a rate-advocacy and "
        "back-office scale play more than a pricing one.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Eligibility — IDD diagnosis + Medicaid financial/functional "
            "eligibility; enrollment onto a state HCBS waiver (or a waiting "
            "list)",
            "Person-centered service plan + level-of-need assessment set the "
            "authorized service mix and hours",
            "Placement / service authorization — residential setting, day "
            "program, supported employment, in-home supports",
            "Direct Support Professional delivery + case management / service "
            "coordination",
            "Electronic Visit Verification (EVV) + documentation of delivered "
            "units (the billing substrate)",
            "Incident reporting, quality review, and settings-rule compliance",
            "Billing Medicaid at the state-set per-service rate; managed-care "
            "or fee-for-service reconciliation",
        ],
        sites_of_care=[
            "Group home / community residential (24/7 staffed — the revenue "
            "core)",
            "Supported / independent living (fewer staffed hours per person)",
            "Day habilitation & pre-vocational programs",
            "Supported employment (job coaching in community workplaces)",
            "In-home personal supports & respite (family home)",
            "Intermediate Care Facility for Individuals with IDD (ICF/IID — the "
            "institutional, higher-acuity end)",
        ],
        money_flow=(
            "Medicaid is the payer for essentially the entire sector, chiefly "
            "through 1915(c) HCBS waivers (with 1915(i), 1915(k) Community First "
            "Choice, and state-plan variants), plus institutional ICF/IID "
            "funding at the high-acuity end. Each service — a residential day, a "
            "unit of day habilitation, an hour of supported employment or "
            "in-home support — is reimbursed at a rate SET BY THE STATE, "
            "typically as a daily or 15-minute-unit rate, increasingly routed "
            "through Medicaid managed-care organizations. Because the rate is "
            "administratively fixed and the dominant cost is Direct Support "
            "Professional wages, the provider's margin is the thin residual "
            "between a legislated price and a labor market the operator does not "
            "control — and CMS's 'Access' rule now claims 80% of certain HCBS "
            "payments for direct-care compensation, formalizing how little of "
            "the rate is meant to remain. Revenue is therefore a function of "
            "authorized service units actually delivered (which requires staffed "
            "capacity) at rates the operator must lobby the state to raise."),
        key_players=(
            "A historically nonprofit, state-by-state field now consolidated by "
            "a few multi-state platforms: Sevita (formerly The MENTOR Network; "
            "Centerbridge/Vistria), RHA Health Services, Dungarvin, Redwood "
            "Family Care Network, BrightSpring Health Services / ResCare "
            "(public, KKR/Walgreens lineage), AbleLight, and Chimes, alongside "
            "thousands of local nonprofit and for-profit providers. State DD "
            "agencies and Medicaid MCOs are the counterparties; national "
            "advocacy bodies (ANCOR, The Arc) drive the rate and workforce "
            "policy that determines the economics."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicaid LTSS/HCBS spending on IDD (modeled)", "~$80-95B",
                    "GOV · KFF/CMS Medicaid LTSS & HCBS spending (IDD share)"),
            Segment("Community (HCBS) vs. institutional share",
                    "large majority community-based",
                    "GOV · CMS HCBS rebalancing data"),
            Segment("People with IDD receiving LTSS", "well over 1M",
                    "GOV · state DD-agency / KFF service counts"),
            Segment("HCBS waiver waiting list", "hundreds of thousands",
                    "GOV · KFF Medicaid HCBS waiver waiting-list survey"),
            Segment("Residential group-home services", "the revenue core",
                    "ILLUSTRATIVE · service-mix structure, directional"),
        ],
        growth_drivers=[
            "Aging family caregivers → new placements ~3.5%/yr",
            "Waiver-slot expansion converting waitlists into funded volume",
            "State rate updates (workforce-driven) ~2.5%/yr",
            "Deinstitutionalization (Olmstead) shifting ICF to community HCBS",
            "DSP vacancy/turnover −1.0%/yr — capacity, not demand, is the limit",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicaid HCBS waiver / state plan": 0.85,
            "Medicaid ICF/IID (institutional)": 0.08,
            "State / county / private-pay / other": 0.07,
        },
        rate_mechanics=[
            "1915(c) HCBS waiver rates — state-set per-service prices "
            "(residential daily rate, day-hab unit, supported-employment hour, "
            "in-home 15-minute unit); the core reimbursement, fixed by the "
            "state.",
            "Related authorities — 1915(i) state-plan HCBS, 1915(k) Community "
            "First Choice, and 1115 demonstrations — expand or restructure the "
            "covered services and rate methodology.",
            "ICF/IID institutional reimbursement — cost-based/per-diem funding "
            "for the higher-acuity congregate setting.",
            "Medicaid managed-care (MLTSS) — a growing share of states route "
            "IDD services through MCOs that add utilization management and "
            "network contracting on top of the state rate.",
            "CMS 'Ensuring Access' 80/20 rule — requires 80% of Medicaid "
            "payments for certain HCBS (homemaker, home-health-aide, personal "
            "care) to go to direct-care-worker compensation, constraining the "
            "administrative/margin residual.",
            "Electronic Visit Verification (EVV) — the 21st Century Cures Act "
            "mandate that gates billing of in-home/personal-care services to "
            "verified delivery.",
        ],
        reimbursement_risk=(
            "The reimbursement risk is a structural rate-vs-wage squeeze the "
            "operator cannot price around. On price, every service rate is set "
            "by the state and updated legislatively or administratively, "
            "typically lagging the wage inflation that drives the cost base — so "
            "an operator's realized margin depends on rate-setting cycles and "
            "advocacy, not on its own contracting. On cost, the CMS 'Access' "
            "rule's 80/20 requirement earmarks the large majority of certain "
            "HCBS payments for direct-care compensation, formalizing a thin "
            "administrative residual and putting real pressure on multi-site "
            "overhead models. Layered on: the shift of IDD services into "
            "Medicaid managed care introduces utilization management and slower "
            "payment; EVV and the HCBS Settings Rule add compliance cost and can "
            "disallow non-compliant units; and because the whole sector rides "
            "Medicaid, it is exposed to state-budget cycles and any federal "
            "Medicaid financing changes. The offset is that demand is "
            "non-discretionary and politically sympathetic, so rate advocacy — "
            "especially framed around the DSP wage crisis — has real traction."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Olmstead v. L.C. (1999) + the ADA integration mandate",
                 "Held that unjustified institutionalization is discrimination — "
                 "the legal engine of deinstitutionalization and the shift of "
                 "IDD funding from ICFs into community HCBS.",
                 "https://www.ada.gov/olmstead/"),
            Rule("Medicaid HCBS Settings Rule (2014, CMS)",
                 "Requires HCBS to be delivered in integrated, community "
                 "settings with person-centered rights — reshaping residential "
                 "and day-program models and their cost.",
                 "https://www.medicaid.gov/medicaid/home-community-based-services/guidance/home-community-based-services-final-regulation"),
            Rule("CMS 'Ensuring Access to Medicaid Services' rule (2024) — 80/20",
                 "Requires 80% of Medicaid payments for certain HCBS to reach "
                 "direct-care-worker compensation — a direct claim on the "
                 "operator's margin residual and the sector's defining policy "
                 "risk.",
                 "https://www.cms.gov/newsroom/fact-sheets/ensuring-access-medicaid-services-final-rule-cms-2442-f"),
            Rule("Electronic Visit Verification (EVV) — 21st Century Cures Act",
                 "Mandates electronic verification of in-home/personal-care "
                 "service delivery as a condition of Medicaid payment.",
                 "https://www.medicaid.gov/medicaid/home-community-based-services/guidance/electronic-visit-verification-evv"),
            Rule("1915(c) HCBS waivers + state DD-agency licensure",
                 "The waiver authority that funds community IDD services and the "
                 "state licensure, incident-reporting, and quality regime that "
                 "governs operation.",
                 "https://www.medicaid.gov/medicaid/home-community-based-services"),
        ],
        policy_watch=[
            "State implementation of the 2024 'Access' 80/20 rule",
            "State HCBS rate reviews and DSP-wage-driven rate increases",
            "HCBS waiver-slot expansions and waiting-list-reduction initiatives",
            "Shift of IDD services into Medicaid managed care (MLTSS)",
            "Federal Medicaid financing changes and FMAP/redetermination effects",
            "DSP-workforce policy (wage floors, credentialing, registries)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Deeply fragmented and historically nonprofit. Services are "
            "delivered locally under state-specific waiver rules, so the "
            "provider base is thousands of small, state-bound nonprofits and "
            "for-profits — a classic roll-up feedstock. The consolidation logic "
            "is back-office scale, multi-state diversification against single-"
            "state rate risk, and rate-advocacy weight, not pricing power (the "
            "rate is set by the state regardless of scale)."),
        hhi_or_share=(
            "No national concentration; even the largest platforms (Sevita, "
            "BrightSpring, RHA) hold modest shares of a state-fragmented base. "
            "State IDD provider rosters are not vendored, so operator "
            "concentration is honestly not measured here — the deal corpus below "
            "is the real trading history."),
        consolidation=(
            "PE and strategics have been assembling multi-state platforms out of "
            "the nonprofit-heavy field: Sevita (Centerbridge/Vistria), RHA "
            "Health Services, Dungarvin, Redwood Family Care Network, and "
            "BrightSpring/ResCare. The thesis is diversification across state "
            "rate environments, professionalized back office and compliance, and "
            "scale in rate advocacy — with tuck-ins of local providers who lack "
            "the overhead to absorb EVV, settings-rule, and 80/20 compliance."),
        pe_activity=(
            "Active and durable, precisely because demand is non-discretionary "
            "and Medicaid-funded. But the return profile is a spread business at "
            "the mercy of state rates and a broken labor market, so diligence "
            "centers on state-rate trajectory and rate-advocacy track record, "
            "DSP vacancy/turnover and overtime/agency reliance, exposure to the "
            "80/20 rule, and occupancy/utilization of staffed capacity — not on "
            "any pricing lever."),
        notable_players=[
            "Sevita (The MENTOR Network)", "BrightSpring Health Services / "
            "ResCare", "RHA Health Services", "Dungarvin",
            "Redwood Family Care Network", "AbleLight", "Chimes",
            "state nonprofit provider networks",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue / service day or unit", "state-set",
                "The price is a Medicaid waiver rate fixed by the state — the "
                "operator's top line is an administrative variable, not a "
                "negotiation."),
            Kpi("DSP annualized turnover", "40-55%+",
                "The defining operating metric; churn forces overtime and agency "
                "labor and leaves capacity unstaffed."),
            Kpi("DSP vacancy rate", "10-20%+",
                "Structural understaffing caps how much authorized (and funded) "
                "service can actually be delivered."),
            Kpi("Overtime + agency-labor share of DSP hours",
                "the margin swing",
                "Filling vacancies with premium-cost hours is what turns a thin "
                "rate spread negative."),
            Kpi("Residential occupancy / capacity utilization", "85-95%",
                "Fixed group-home cost demands high occupancy; empty licensed "
                "beds are non-recoverable."),
            Kpi("Operating margin", "5-12% (illustrative)",
                "A thin, rate-dependent residual that the 80/20 rule and wage "
                "inflation directly compress."),
        ],
        margin_profile=(
            "IDD-services margin is the residual between a state-set Medicaid "
            "rate and a Direct Support Professional wage bill the operator does "
            "not control — a structurally thin spread. Because DSP labor is the "
            "overwhelming cost and the rate is fixed, profitability turns almost "
            "entirely on labor efficiency: keeping vacancy and turnover low "
            "enough to avoid overtime and agency premiums, and keeping staffed "
            "residential capacity fully occupied. Scale does not raise the price "
            "(the state sets it) but it diversifies single-state rate risk, "
            "spreads compliance overhead (EVV, settings rule), and adds weight to "
            "rate advocacy. The 2024 'Access' 80/20 rule tightens the math "
            "further by earmarking most of certain HCBS payments for direct-care "
            "compensation — good for workers, and a direct compression of the "
            "administrative residual that multi-site platforms live on. The "
            "durable operators are those with the lowest DSP turnover in their "
            "markets and the strongest state rate-setting relationships."),
    ),
    risks=[
        Risk("State-set Medicaid rate risk (rate-vs-wage squeeze)", "High",
             "Rates are administratively fixed and lag wage inflation; the "
             "operator has no pricing lever."),
        Risk("DSP shortage — turnover, vacancy, overtime, agency labor", "High",
             "The binding operating constraint and the dominant cost; premium-"
             "cost hours turn the thin spread negative."),
        Risk("CMS 'Access' 80/20 rule margin compression", "High",
             "Earmarking 80% of certain HCBS payments for direct care directly "
             "claims the administrative/margin residual."),
        Risk("Medicaid budget / financing exposure", "Medium",
             "Riding a single public payer exposes the sector to state-budget "
             "cycles and federal Medicaid financing changes."),
        Risk("Compliance — HCBS Settings Rule, EVV, incident/quality", "Medium",
             "Non-compliance can disallow units and add cost; congregate "
             "settings face integration requirements."),
        Risk("Client-safety / incident and abuse-neglect exposure", "Medium",
             "24/7 care of a vulnerable population carries licensure, "
             "litigation, and reputational tail risk."),
    ],
    diligence_questions=[
        "What is the state mix, and what is each state's rate trajectory and "
        "rate-setting cycle — where is a rate increase (or cut) pending?",
        "What is DSP turnover, vacancy, and the overtime/agency share of hours, "
        "and how do wages compare to the local labor market?",
        "What is residential occupancy and staffed-capacity utilization by "
        "program?",
        "What is the exposure to the 80/20 'Access' rule by service line, and "
        "what does compliance do to the administrative residual?",
        "How much of the book is moving into Medicaid managed care, and what is "
        "the payment-timing and utilization-management effect?",
        "What is the settings-rule and EVV compliance status, and any disallowed "
        "units or corrective actions?",
        "What is the incident/abuse-neglect and licensure-survey history, and "
        "the associated reserves?",
        "What is the rate-advocacy track record and relationships with each "
        "state DD agency?",
    ],
    insider_lens=[
        "There is no commercial upside — the state IS the price. Unlike almost "
        "every other healthcare vertical, IDD services have no commercial payer "
        "to lift the blend; the entire top line is a Medicaid rate set by the "
        "state. A platform's real skill is rate advocacy, and the most valuable "
        "asset is a track record of getting states to move rates.",
        "The business is a bet on a broken labor market. DSP wages sit near "
        "minimum, turnover runs 40-55%, and vacancies are chronic — so the "
        "spread between a fixed rate and an uncontrollable wage is the whole "
        "game, and overtime plus agency labor is where thin margins go to die.",
        "The 80/20 rule is the sleeper. CMS's 'Access' requirement that 80% of "
        "certain HCBS payments reach direct-care workers is celebrated as a "
        "wage win and underweighted as what it is for owners: a formal claim on "
        "most of the rate that squeezes the multi-site overhead model. "
        "Underwrite its phase-in by state and service line.",
        "Demand is the aging-caregiver cliff, and it is inexorable. Adults with "
        "IDD are outliving the parents who have cared for them at home for "
        "decades; each of those transitions converts an unfunded family "
        "arrangement into a funded placement — a durable, non-discretionary, "
        "and politically sympathetic demand engine sitting behind long waiver "
        "waiting lists.",
        "Scale diversifies rate risk; it does not create pricing power. The "
        "roll-up logic here is spreading single-state rate exposure and "
        "compliance overhead and adding advocacy weight — not buying leverage "
        "over a price the state controls regardless of size.",
        "Managed care is quietly changing the counterparty. As states route IDD "
        "services through MLTSS, an operator that dealt only with a state DD "
        "agency now faces MCO utilization management and slower payment — a "
        "working-capital and margin variable that is easy to miss in a "
        "historically fee-for-service book.",
    ],
    connections=default_connections(
        "idd_services",
        deals_sector="behavioral_health",
        extra_pages=[
            ("/industry/idd_services",
             "Industry deep-dive — IDD-services deal history + structure"),
        ],
        connectors=[
            ("medicaid_data_enrollment_monthly",
             "Medicaid enrollment — the payer base for the entire IDD-services "
             "sector"),
            ("medicaid_data_managed_care_by_state_2024",
             "Medicaid managed care by state — the MLTSS structure reshaping "
             "IDD payment"),
            ("cdc_data_disability_dhds",
             "CDC Disability & Health Data System — disability prevalence by "
             "state"),
            ("bls_qcew_industry_area",
             "BLS QCEW — DSP/residential-care wages & employment by area (the "
             "labor market)"),
            ("census_acs_county_profile",
             "Census ACS — disability and population by county, the demand "
             "denominator"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded providers (integrity screen)"),
        ],
    ),
    sources=[
        Source("KFF — Medicaid Home- and Community-Based Services: spending, "
               "enrollment, and waiting lists", "INDUSTRY",
               "https://www.kff.org/medicaid/"),
        Source("CMS — Ensuring Access to Medicaid Services final rule (the "
               "80/20 provision)", "GOV",
               "https://www.cms.gov/newsroom/fact-sheets/ensuring-access-medicaid-services-final-rule-cms-2442-f"),
        Source("CMS — Medicaid HCBS Settings Rule (42 CFR 441)", "GOV",
               "https://www.medicaid.gov/medicaid/home-community-based-services/guidance/home-community-based-services-final-regulation"),
        Source("Olmstead v. L.C., 527 U.S. 581 (1999) — ADA integration "
               "mandate", "GOV", "https://www.ada.gov/olmstead/"),
        Source("ANCOR — State of America's Direct Support Workforce Crisis "
               "(DSP turnover/vacancy)", "INDUSTRY",
               "https://www.ancor.org/"),
        Source("National Core Indicators / state DD-agency service and outcome "
               "data", "INDUSTRY", "https://www.nationalcoreindicators.org/"),
        Source("PE Desk industry deep-dive (IDD services) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=idd_services"),
    ],
    live_figures=live_figures_from_dive("idd_services"),
    trends=(
        "IDD services have been on a decades-long journey out of the "
        "institution and into the community, and the funding and cost structure "
        "have followed. Olmstead (1999) made unjustified institutionalization a "
        "civil-rights violation and, together with the growth of 1915(c) HCBS "
        "waivers, shifted the money from ICF/IID congregate care to community "
        "residential, day, and in-home supports — which are now the large "
        "majority of IDD LTSS spending. The 2014 HCBS Settings Rule pushed "
        "further, requiring integrated, person-centered settings and reshaping "
        "residential and day-program models. Against that steady "
        "community-integration backdrop, two forces now dominate the outlook. "
        "The first is the Direct Support Professional workforce crisis: near-"
        "minimum wages, 40-55% turnover, and chronic vacancies mean funded "
        "services go undelivered for lack of staff, and rate advocacy has "
        "increasingly been framed around DSP pay. The second is CMS's 2024 "
        "'Ensuring Access' rule, whose 80/20 provision earmarks most of certain "
        "HCBS payments for direct-care compensation — a wage win that also "
        "compresses the operator margin residual and will test the multi-site "
        "roll-up model as it phases in. Demand, meanwhile, is inexorable: the "
        "aging-family-caregiver cliff and long waiver waiting lists guarantee a "
        "pipeline of new placements, keeping a nonprofit-rooted field attractive "
        "to the PE and strategic consolidators (Sevita, BrightSpring, RHA, "
        "Dungarvin) assembling state-diversified platforms."),
    growth_levers=[
        GrowthLever(
            "Aging family caregivers → new placements",
            "Adults with IDD outliving parent-caregivers convert unfunded home "
            "arrangements into funded residential/community placements — a "
            "durable demand engine behind the waiting lists.",
            "+3.5%/yr demand", "GOV"),
        GrowthLever(
            "Waiver-slot expansion (waitlist conversion)",
            "State HCBS waiver expansions and waiting-list-reduction initiatives "
            "release funded slots into the market.",
            "+ funded slots", "GOV"),
        GrowthLever(
            "State rate updates (DSP-wage-driven)",
            "Rate advocacy tied to the DSP wage crisis produces state rate "
            "increases that lift the whole top line.",
            "+2.5%/yr rate", "GOV"),
        GrowthLever(
            "Deinstitutionalization (ICF → community)",
            "Olmstead-driven movement of residents from institutions to "
            "community HCBS shifts and grows the addressable community-service "
            "base.",
            "mix shift", "GOV"),
        GrowthLever(
            "DSP vacancy / turnover capacity drag",
            "Chronic understaffing means funded services go undelivered — a "
            "capacity ceiling and a margin cost, not a demand problem.",
            "−1.0%/yr capacity", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Aging family caregivers + waiver-slot supply, gated by DSP "
               "capacity",
        analysis=(
            "The demand base is the population of people with intellectual and "
            "developmental disabilities needing long-term supports — well over a "
            "million receiving Medicaid LTSS, with hundreds of thousands more on "
            "state HCBS waiver waiting lists. The dominant secular driver is "
            "demographic and non-discretionary: a large cohort of adults with "
            "IDD has been cared for at home by aging parents for decades, and as "
            "those caregivers age and die, each transition converts an unfunded "
            "family arrangement into a funded residential or community "
            "placement. That 'aging-caregiver cliff' steadily pressures states "
            "to release waiver slots, so realized volume growth is really a "
            "function of how fast states expand funded capacity against their "
            "waiting lists. The binding constraint on the supply side is not "
            "demand or even funding but the Direct Support Professional "
            "workforce: with 40-55% turnover and double-digit vacancy rates, "
            "operators frequently cannot staff the placements the waivers would "
            "pay for. Underwriting should therefore model growth off funded-"
            "slot releases and staffable capacity in the local labor market, not "
            "off the (very large) count of eligible individuals."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Direct Support Professional wages (+ overtime/agency)",
            "~60-75% of cost",
            "The overwhelming cost line. Near-minimum wages with chronic "
            "vacancies force overtime and agency premiums that are the primary "
            "margin swing.", "ILLUSTRATIVE"),
        CostDriver(
            "Residential facilities / occupancy",
            "~8-14% of cost",
            "The fixed group-home real estate and operating cost that occupancy "
            "must cover; the community-settings rule shapes the footprint.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Case management / service coordination & clinical oversight",
            "~6-10% of cost",
            "Person-centered planning, nursing/behavioral oversight, and "
            "coordination required by the waiver and settings rule.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Compliance, quality, EVV & incident management",
            "~5-9% of cost",
            "Settings-rule compliance, EVV, incident reporting, and quality "
            "review — real, growing overhead that scale spreads.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Administration & G&A",
            "~5-9% of cost",
            "Multi-site management and back office — the residual that the "
            "80/20 'Access' rule directly targets.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "State IDD provider rosters are not vendored — services run under "
        "state-specific 1915(c) waivers with no single national provider file — "
        "so state geography is omitted rather than fabricated. State is, "
        "however, the single most important variable in this sector: each state "
        "sets its own service rates, waiver structure, waiting-list size, "
        "managed-care posture, and DSP wage environment, so a multi-state "
        "platform is a portfolio of independent rate regimes. The Medicaid-"
        "enrollment, Medicaid-managed-care, CDC-disability, and BLS-wage "
        "connectors linked below are the honest way to map the payer base, "
        "demand denominator, and labor market by state."),
)

register(REPORT)
