"""Occupational Health — employer-paid clinical services outside health plans.

Deals-only pattern (no vendored occ-health clinic census). The defining fact is
that the payers are employers and the workers'-compensation system — a property-
and-casualty line — not health insurers, so demand is a derivative of employment
and hours worked, and pricing is a 50-state workers'-comp fee-schedule patchwork
plus negotiated employer contracts. Live SOURCED figures (deal count, entry
multiple) come from ``occ_health_deep_dive()``.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="occ_health",
    name="Occupational Health",
    care_setting="Ambulatory",
    naics="621498",
    one_line_def=(
        "Employer-paid clinical services delivered outside the traditional "
        "health-insurance channel — work-injury care billed to workers' "
        "compensation, pre-placement and DOT physicals, drug-and-alcohol "
        "screening, medical surveillance, and on-site/near-site employer "
        "clinics."),
    tam_headline=TamHeadline(
        value=18.0, unit="$B", growth_pct=4.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US occupational-health services market — workers'-"
            "compensation medical care plus employer-contracted physicals, "
            "screening, surveillance, and on-site clinics. Workers'-comp "
            "medical benefits alone run in the tens of billions (NASI/NCCI); "
            "occ-health clinic services are a subset plus the employer-direct "
            "book. Demand tracks employment and hours worked (BLS), not "
            "demographics. ILLUSTRATIVE."),
    ),
    executive_summary=[
        "The payer isn't a health plan — it's the employer and the workers'-"
        "compensation system (a property-and-casualty line). Demand tracks "
        "employment, hours worked, and injury frequency — a macro/cyclical "
        "exposure, not a demographic one — and there's almost no patient "
        "collection or commercial adjudication.",
        "There are two very different books under one roof. High-margin, high-"
        "throughput 'occupational' services (pre-employment and DOT physicals, "
        "drug screens, surveillance) are near-cash employer contracts; work-"
        "injury care is lower-margin, paid on state comp fee schedules with "
        "utilization review and slow adjudication.",
        "Reimbursement is a 50-state patchwork. Each state sets its own "
        "workers'-comp medical fee schedule (many benchmarked to a multiple of "
        "Medicare, some to usual-and-customary), so rate and payment velocity "
        "vary market-by-market — geography is a pricing variable, not just a "
        "demand one.",
        "The market has a clear leader — Concentra — plus hospital-affiliated "
        "programs and a long independent tail; the on-site/near-site employer-"
        "clinic model (Premise, Marathon, employer-direct) is the faster-"
        "growing, stickier adjacency.",
        "Employer-contract density is the whole game. The economics turn on "
        "capturing an employer's full bundle across its sites, and on employer "
        "and comp-carrier relationships that are personal and don't transfer "
        "automatically in a deal.",
        "Steady regulatory tailwinds (OSHA/DOT/SAMHSA-mandated exams and "
        "testing) sit under a real cyclical risk: an employment/hours downturn "
        "compresses injury care and pre-employment physicals at the same time.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Employer / broker / comp-carrier contract secured",
            "Employee presents (physical, DOT exam, drug screen, or injury)",
            "Clinical evaluation & treatment",
            "Work-status determination (return-to-work / restrictions)",
            "Case management & follow-up (for injuries)",
            "Billing — employer contract or WC fee schedule",
            "Surveillance / recordkeeping reporting (OSHA / DOT)",
        ],
        sites_of_care=[
            "Freestanding occupational-medicine clinic",
            "On-site employer clinic (at the workplace)",
            "Near-site shared clinic (multi-employer)",
            "Mobile units (surveillance / testing at employer sites)",
            "Urgent-care / occ-med hybrid centers",
        ],
        money_flow=(
            "Two payment rails. Employer-direct services — pre-placement and "
            "DOT physicals, drug and alcohol screening, medical surveillance, "
            "and on-site clinics — are sold on negotiated employer contracts "
            "(per-exam, per-screen, or a fixed on-site staffing fee), collected "
            "quickly with little payer friction. Work-injury care is billed to "
            "workers' compensation and paid on the injured worker's state fee "
            "schedule — frequently set as a percentage of Medicare or a state-"
            "specific rate — subject to utilization review, bill review, and "
            "slower carrier adjudication. There is essentially no patient-"
            "responsibility collection and little commercial-health-plan "
            "billing; the customer is the employer or the comp carrier, not the "
            "patient."),
        key_players=(
            "Concentra is the scaled national platform (freestanding occ-med "
            "centers), having absorbed U.S. HealthWorks; hospital systems run "
            "large occupational-medicine programs as a feeder to their "
            "networks; and a long tail of independent clinics serves local "
            "employers. The on-site/near-site employer-clinic segment (Premise "
            "Health, Marathon Health, and health-system and employer-direct "
            "programs) is a distinct, faster-growing model. Upstream sit the "
            "workers'-comp carriers and third-party administrators, drug-testing "
            "labs (Quest, Labcorp), and DOT/SAMHSA certification "
            "infrastructure."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Work-injury care (workers'-comp medical)",
                    "the largest, fee-schedule-paid book",
                    "INDUSTRY · NCCI / NASI WC medical"),
            Segment("Pre-placement & DOT / physical exams",
                    "high-margin employer-direct",
                    "ILLUSTRATIVE · employer-contract mix"),
            Segment("Drug & alcohol screening",
                    "recurring, mandate-driven",
                    "INDUSTRY · SAMHSA / DOT programs"),
            Segment("Medical surveillance & clinical testing",
                    "OSHA-driven recurring",
                    "GOV · OSHA surveillance standards"),
            Segment("On-site / near-site employer clinics",
                    "fastest-growing, stickiest",
                    "INDUSTRY · employer-clinic trade data"),
        ],
        growth_drivers=[
            "Employment & hours worked (BLS) — the master demand driver",
            "OSHA / DOT-mandated exam and surveillance requirements",
            "Employer cost-control shifting care to on-site / near-site clinics",
            "Drug-testing mandates (DOT / federal / employer policy)",
            "Return-to-work and comp-cost-management demand",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Workers' compensation (state fee schedules)": 0.55,
            "Employer-direct contracts (physicals / screening / on-site)": 0.40,
            "Commercial / other": 0.05,
        },
        rate_mechanics=[
            "State workers'-comp medical fee schedules — each state sets its "
            "own; many benchmark to a multiple of Medicare (roughly ~120-200% "
            "of MPFS), a handful use usual-and-customary or have no schedule — "
            "so the same service is priced differently in every state.",
            "Utilization review & bill review — comp carriers apply UR "
            "(treatment guidelines such as ODG/ACOEM) and bill review; approved "
            "treatment and correct coding gate payment.",
            "Employer service contracts — pre-placement/DOT physicals, drug "
            "screens, and surveillance are negotiated per-unit or bundled; on-"
            "site clinics are a fixed staffing/management fee or cost-plus.",
            "DOT/FMCSA & SAMHSA frameworks — DOT physicals require a certified "
            "medical examiner (National Registry); federal drug testing "
            "requires a certified lab and a Medical Review Officer.",
            "Little to no patient cost-sharing — the employer or comp carrier "
            "pays; there is minimal self-pay collection or commercial-health "
            "adjudication.",
        ],
        reimbursement_risk=(
            "The risk is not denial-heavy commercial billing — it's two-sided. "
            "On the injury book, 50 state fee schedules set the price and "
            "utilization/bill review controls what's paid, so margins and "
            "payment velocity swing by state and by carrier relationship. On "
            "the employer-direct book, pricing is competitive contract renewal "
            "— lose an anchor employer and a clinic's economics change "
            "overnight. And because volume follows employment and hours worked, "
            "an economic downturn compresses injury care and pre-employment "
            "physicals simultaneously — a genuine cyclical exposure most "
            "healthcare services don't carry."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("OSHA recordkeeping & medical-surveillance standards",
                 "Mandate the exams, monitoring, and reporting that generate "
                 "recurring occupational-health demand independent of the "
                 "economic cycle.",
                 "https://www.osha.gov/"),
            Rule("DOT / FMCSA medical examiner requirements (National Registry)",
                 "Commercial drivers require certified-examiner physicals — a "
                 "large, recurring, regulation-driven volume.",
                 "https://www.fmcsa.dot.gov/"),
            Rule("SAMHSA federal drug-testing guidelines & MRO rules",
                 "Govern regulated drug/alcohol screening — the certified-lab "
                 "and Medical-Review-Officer framework behind employer testing.",
                 "https://www.samhsa.gov/"),
            Rule("State workers'-compensation systems & fee schedules",
                 "Set medical pricing, treatment guidelines, and dispute "
                 "resolution state-by-state — the core rate environment for "
                 "injury care.",
                 None),
            Rule("ADA medical-exam limits",
                 "Constrain when and what pre-placement medical inquiries and "
                 "exams are permissible.",
                 "https://www.eeoc.gov/"),
        ],
        policy_watch=[
            "State fee-schedule updates and Medicare-benchmark changes",
            "Workers'-comp treatment-guideline / formulary / UR tightening",
            "Marijuana legalization complicating drug-testing programs",
            "DOT/FMCSA rule changes on driver medical certification",
            "Employer on-site-clinic expansion and comp-cost insourcing",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "A clear national leader (Concentra) atop a fragmented field of "
            "hospital-affiliated occupational-medicine programs and independent "
            "local clinics. Barriers are modest and employer relationships are "
            "local, so the long tail persists even under a national brand."),
        hhi_or_share=(
            "Concentra is the largest freestanding occ-med operator by center "
            "count; beyond it, share is diffuse across hospital programs and "
            "independents. No public occ-health clinic census is vendored, so "
            "precise share is honestly unquantified — the deal history and the "
            "BLS employment base below are the real anchors."),
        consolidation=(
            "Concentra consolidated the freestanding segment (including U.S. "
            "HealthWorks) and separated from Select Medical via a 2024 IPO. "
            "Hospital systems periodically buy or build occ-med as a network "
            "feeder. The livelier consolidation is in on-site/near-site "
            "employer clinics (Premise, Marathon, health-system programs), "
            "where multi-employer scale and technology matter."),
        pe_activity=(
            "Sponsor interest concentrates on (1) regional freestanding occ-med "
            "roll-ups that bolt onto or compete with Concentra, and (2) the on-"
            "site/near-site employer-clinic model, which offers recurring "
            "contracted revenue and employer stickiness. The thesis is "
            "employer-contract density and diversification away from pure comp-"
            "injury cyclicality."),
        notable_players=[
            "Concentra", "Premise Health", "Marathon Health",
            "Hospital-system occupational-medicine programs", "WorkCare",
            "Quest Diagnostics", "Labcorp", "Regional occ-med clinic groups",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Visit mix (physicals/screens vs injury care)", "mix-driven",
                "High-margin employer-direct services vs lower-margin, slower-"
                "paying comp-injury care — the core margin lever."),
            Kpi("Employer-contract density", "revenue / anchor employer",
                "Share of an employer's full bundle captured across its sites — "
                "the stickiness and cross-sell metric."),
            Kpi("Revenue per visit (blended)", "contract vs fee-schedule",
                "Employer-contract pricing vs the WC fee-schedule rate for the "
                "same clinical work."),
            Kpi("Provider productivity (visits/provider/day)", "throughput",
                "Throughput on a fixed clinic cost base is the operating "
                "leverage."),
            Kpi("WC bill-review / payment velocity", "days to pay, paid vs billed",
                "The comp-book working-capital drag and fee-schedule leakage."),
            Kpi("On-site clinic contract retention", "the annuity",
                "Renewal of contracted employer-clinic revenue — the recurring "
                "base a buyer values."),
        ],
        margin_profile=(
            "A freestanding occ-med clinic is a fixed-cost box (providers, "
            "medical assistants, X-ray, space) whose margin is set by "
            "throughput and mix: high-volume, quick-turn physicals and drug "
            "screens are the margin, while comp-injury care is lower-margin and "
            "slower-paying. Employer-contract density lifts utilization and mix "
            "at once. On-site/near-site clinics trade lower per-visit revenue "
            "for contracted, recurring, employer-paid economics and high "
            "retention. Ranges are ILLUSTRATIVE — confirm against the target's "
            "own financials."),
    ),
    risks=[
        Risk("Employment / hours cyclicality", "High",
             "A downturn cuts injury volume and pre-employment physicals "
             "simultaneously; demand is economic, not demographic."),
        Risk("Employer-contract concentration / churn", "High",
             "Losing an anchor employer or a national account resets a clinic's "
             "economics; contracts renew competitively."),
        Risk("50-state fee-schedule & UR exposure", "Medium",
             "Comp medical pricing and payment velocity vary by state and "
             "tighten over time."),
        Risk("Referral / relationship transfer risk", "Medium",
             "Employer and comp-carrier relationships are personal and may not "
             "transfer with the deal."),
        Risk("Drug-testing / regulatory shifts", "Medium",
             "Marijuana legalization and DOT changes can shrink or reshape "
             "mandated screening volumes."),
        Risk("Occ-med labor supply / cost", "Medium",
             "Provider and MA staffing constrains throughput and de novo "
             "growth."),
    ],
    diligence_questions=[
        "What is the split between employer-direct (physicals/screening/on-"
        "site) and WC-injury revenue, and the margin of each?",
        "How concentrated is revenue in the top employers / national accounts, "
        "and what is contract tenure and renewal history?",
        "Across which states does the injury book sit, and how do those fee "
        "schedules and payment velocities compare?",
        "How much revenue is on-site/near-site contracted (recurring) vs "
        "episodic clinic visits?",
        "Do key employer and comp-carrier relationships transfer with the deal, "
        "or are they personal to departing owners/providers?",
        "What is the drug-testing volume exposure to DOT/federal mandates and "
        "to state marijuana-legalization changes?",
        "What is WC bill-review leakage (billed vs paid) and days-to-pay, and "
        "how is utilization review handled?",
    ],
    insider_lens=[
        "The payer isn't a health plan — it's the employer and the workers'-"
        "comp system (a P&C insurance line). That one fact drives everything: "
        "demand is cyclical (employment and hours), pricing is state fee "
        "schedules and employer contracts, and there's almost no patient "
        "collection or commercial adjudication.",
        "There are two businesses under one roof. Physicals and drug screens "
        "are near-cash, high-margin, high-throughput employer work; comp-injury "
        "care is lower-margin, fee-schedule-priced, and slow-paying. The mix — "
        "and how well you cross-sell the full employer bundle — is the quality "
        "of the earnings.",
        "Fee schedules make geography a pricing variable. The same visit is "
        "worth different amounts in different states, and payment velocity "
        "varies too, so a multi-state footprint is a portfolio of different "
        "rate environments, not one market.",
        "The relationships are the asset and they walk. Employer HR/safety "
        "contacts and comp-carrier panels are personal; a national account or a "
        "key medical director leaving can move a book of business. Contract "
        "transfer and retention are the diligence, not the real estate.",
        "On-site clinics are the stickier future. Employers tired of comp costs "
        "are pulling care in-house; the on-site/near-site model trades ticket "
        "size for recurring, contracted, retention-heavy revenue — and "
        "diversifies away from raw comp-injury cyclicality.",
        "Concentra sets the market. Its scale, employer contracts, and national "
        "footprint are the benchmark any roll-up is measured against — and the "
        "reason regional platforms compete on service density and relationships "
        "rather than price.",
    ],
    connections=default_connections(
        "occ_health",
        deals_sector="occ_health",
        connectors=[
            ("bls_qcew_industry_area",
             "BLS QCEW — employment & wages by industry/area (the demand base)"),
            ("census_acs_county_profile",
             "Census ACS — county employment & industry mix"),
            ("npi_provider",
             "NPI Registry — occupational-medicine physicians & clinics"),
            ("cms_open_data_mup_physician_by_provider_service",
             "CMS Physician & Other Practitioners — E/M & exam procedure benchmarks"),
            ("oig_leie_exclusions",
             "OIG LEIE — exclusion screen for clinical staff"),
        ],
    ),
    sources=[
        Source("U.S. Bureau of Labor Statistics — employment, hours, and "
               "occupational injury/illness data", "GOV",
               "https://www.bls.gov/"),
        Source("OSHA — recordkeeping & medical-surveillance standards", "GOV",
               "https://www.osha.gov/"),
        Source("DOT / FMCSA — National Registry of Certified Medical "
               "Examiners", "GOV", "https://www.fmcsa.dot.gov/"),
        Source("National Academy of Social Insurance / NCCI — workers'-"
               "compensation benefits & medical-cost data", "INDUSTRY",
               "https://www.nasi.org/"),
        Source("SAMHSA — federal workplace drug-testing guidelines", "GOV",
               "https://www.samhsa.gov/"),
        Source("PE Desk industry deep-dive (occupational health) + realized-"
               "deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=occ_health"),
    ],
    live_figures=live_figures_from_dive("occ_health"),
    trends=(
        "Occupational health has been quietly repositioning from a comp-injury "
        "clinic business toward an employer-services and on-site-care business. "
        "The cyclical core — work-injury care paid on 50 state workers'-comp "
        "fee schedules — remains, but growth and stickiness have moved to "
        "employer-direct services (physicals, DOT exams, drug screening, "
        "surveillance) and, increasingly, to on-site and near-site employer "
        "clinics as self-insured employers pull care in-house to control comp "
        "and health costs. Concentra consolidated the freestanding segment and "
        "separated from Select Medical in a 2024 IPO, setting the national "
        "benchmark; hospital systems run occ-med as a network feeder; and a "
        "fragmented independent tail persists on local employer relationships. "
        "The steady tailwinds are regulatory (OSHA/DOT/SAMHSA-mandated exams "
        "and testing), and the defining risk is macro: because volume follows "
        "employment and hours worked, a labor-market downturn compresses injury "
        "care and pre-employment physicals at the same time. The livelier "
        "capital is chasing the on-site/near-site model for its recurring, "
        "contracted, employer-paid economics."),
    growth_levers=[
        GrowthLever(
            "Employment & hours worked",
            "Injury volume and pre-employment physicals scale directly with the "
            "working population and hours — the primary, cyclical driver.",
            "primary (cyclical)", "GOV"),
        GrowthLever(
            "Mandated exams & surveillance (OSHA/DOT)",
            "Regulation-driven recurring volume independent of the economic "
            "cycle — the steady base under the swing.",
            "steady base", "GOV"),
        GrowthLever(
            "On-site / near-site employer clinics",
            "Employers insource care for cost control, creating recurring "
            "contracted revenue and stickiness.",
            "fastest-growing", "ILLUSTRATIVE"),
        GrowthLever(
            "Drug & alcohol screening mandates",
            "DOT/federal/employer-policy testing is recurring and regulation-"
            "driven.",
            "recurring", "ILLUSTRATIVE"),
        GrowthLever(
            "Employer-bundle cross-sell",
            "Capturing more of each employer's services lifts revenue per "
            "relationship without new customer acquisition.",
            "density", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Employment and hours worked (injury frequency × workforce size)",
        analysis=(
            "Occupational-health volume is fundamentally an employment "
            "derivative, not a demographic one. Pre-placement physicals and "
            "drug screens rise and fall with hiring; work-injury visits scale "
            "with the number of workers, hours worked, and injury frequency "
            "(BLS tracks recordable injury/illness rates). That makes BLS QCEW "
            "employment and the injury-rate series the true demand meters — and "
            "it makes the sector cyclically exposed in a way most healthcare is "
            "not: a hiring slowdown cuts both new-hire physicals and injury "
            "visits at once, while a tight labor market with heavy hiring and "
            "overtime lifts both. Regulatory mandates (OSHA surveillance, DOT "
            "exams) provide a steadier base underneath the cyclical swing."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Clinical labor (occ-med physicians, APPs, MAs, techs)",
            "~40-50% of cost",
            "The fixed clinic cost; throughput on this base sets the margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Occupancy & clinic footprint (space, X-ray, equipment)",
            "~12-18% of cost",
            "The fixed box; utilization drives the return on it.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing / bill-review / UR handling (RCM)",
            "~8-12% of cost",
            "The comp-book friction cost and where fee-schedule leakage is "
            "managed.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Lab & testing COGS (drug screens, surveillance panels)",
            "~8-12% of cost",
            "Largely a pass-through to reference labs (Quest/Labcorp).",
            "ILLUSTRATIVE"),
        CostDriver(
            "Sales / account management & G&A",
            "~8-12% of cost",
            "Employer contracting and retention is a B2B sales cost, not a "
            "patient-marketing one.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national occupational-health clinic census is vendored, so "
        "geography is not fabricated here. The honest geographic read is two-"
        "layered: demand follows the industrial and employment base (BLS QCEW "
        "by area/industry — manufacturing, logistics, construction, and energy "
        "corridors), while pricing follows each state's workers'-comp fee "
        "schedule, so a multi-state footprint spans different rate "
        "environments. Use the BLS employment and deal-history connectors below "
        "rather than a facility map."),
)

register(REPORT)
