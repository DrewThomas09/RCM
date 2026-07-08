"""Skilled Nursing (SNF) — post-acute skilled + long-term custodial nursing.

Rich-data flagship: consumes ``snf_deep_dive()`` (CMS Nursing Home Care Compare,
~14.7K facilities, 1.57M certified beds) for SOURCED live figures, and authors
the qualitative sections from the operating knowledge of a spread business —
below-cost Medicaid custodial days cross-subsidized by above-cost Medicare/MA
skilled days, wrapped in a REIT-heavy real-estate chassis.
"""
from __future__ import annotations

from .. import (
    CmsTrend, Competition, Connection, CostDriver, GrowthLever, HowItWorks,
    Kpi, MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule,
    Segment, Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="snf",
    name="Skilled Nursing (SNF)",
    care_setting="Post-acute",
    naics="623110",
    one_line_def=(
        "Institutional nursing facilities that provide Medicare-covered "
        "short-stay skilled/rehab care after a hospitalization AND Medicaid-"
        "covered long-term custodial care — a spread business run on a real-"
        "estate chassis, paid a per-diem that differs enormously by payer."),
    tam_headline=TamHeadline(
        value=190.0, unit="$B", growth_pct=4.0, basis_label="GOV",
        basis_note=(
            "US nursing-care-facility expenditure ~$190B (CMS National Health "
            "Expenditure Accounts — nursing care facilities & CCRCs); Medicare "
            "FFS SNF is only ~$28B of it (MedPAC). Growth is the modeled "
            "composite of the TAM/SAM drivers (80+ demand +3.5%, rate +3.0%, "
            "MA/home substitution −2.0%)."),
    ),
    executive_summary=[
        "It is a spread business, not a care business. Medicaid custodial days "
        "(~55% of resident-days) are paid below cost; Medicare and Medicare "
        "Advantage skilled days are paid well above it. The 'quality mix' — the "
        "share of skilled days — is the whole margin, and it is a thin slice of "
        "volume carrying most of the revenue.",
        "The real estate is split from the operations. Most beds sit in a "
        "REIT/propco (Omega, Sabra, CareTrust, Welltower) leased to an opco, so "
        "headline EBITDA is misleading — underwrite EBITDAR and rent coverage, "
        "not the operating margin alone.",
        "Two structural compressors are live at once: Medicare Advantage is "
        "repricing the skilled day downward (prior auth, shorter authorized "
        "length of stay, sub-FFS rates) as MA passes half of Medicare, and the "
        "2024 CMS minimum-staffing rule threatens an existential labor-cost "
        "step-up for rural and Medicaid-heavy facilities.",
        "Agency/contract labor is the silent margin killer post-COVID; the swing "
        "between a facility running on staff nurses and one leaning on travel "
        "agencies is often the difference between profit and loss.",
        "Supply is old and CON-constrained — almost nobody builds new SNFs. The "
        "acquirable market is turnaround and consolidation of a large, aging, "
        "for-profit (~74%) fleet, not de novo growth; ownership scrutiny (PE + "
        "REIT transparency, Special Focus Facilities) raises the compliance bar.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Hospital inpatient stay (the qualifying 3-day stay for Part A)",
            "Discharge planning → SNF admission for skilled/rehab care",
            "MDS assessment → PDPM case-mix classification (5 components)",
            "Skilled therapy + nursing (short-stay rehab, ~20-30 days)",
            "Discharge to community OR conversion to long-term custodial",
            "Long-stay custodial care billed to Medicaid (below-cost per-diem)",
            "Billing — Part A per-diem, MA per-diem, Medicaid per-diem, private",
            "Quality reporting — Five-Star, VBP readmissions, SNF QRP",
        ],
        sites_of_care=[
            "Free-standing skilled nursing facility (the volume base)",
            "Hospital-based SNF / swing beds (rural)",
            "Dual-certified SNF/NF beds (skilled + custodial under one roof)",
            "Sub-acute / ventilator or high-acuity rehab units",
            "CCRC / life-plan community nursing wings",
        ],
        money_flow=(
            "The same bed is paid four very different ways. Medicare Part A pays "
            "a PDPM case-mix per-diem for a short skilled stay (days 1-20 in "
            "full, 21-100 with a daily coinsurance) after a qualifying 3-day "
            "hospital stay — the high-margin payer. Medicare Advantage pays a "
            "negotiated per-diem, usually a discount to FFS, with prior "
            "authorization and a shorter authorized length of stay. Medicaid "
            "pays a state-set custodial per-diem for long-stay residents that is "
            "frequently below the cost of care, with provider taxes, UPL, and "
            "state directed payments quietly making up much of the difference. "
            "Private pay and long-term-care insurance fill the rest. Because the "
            "cost base (nurses, aides, dietary, the building) is largely fixed "
            "per occupied bed, margin is a function of occupancy times quality "
            "mix — how many of those occupied days are skilled rather than "
            "Medicaid."),
        key_players=(
            "The operating layer is regional and fragmented under a few scaled "
            "chains — Ensign Group (the public bellwether), Genesis HealthCare, "
            "Life Care Centers, PruittHealth, Signature HealthCARE, NHC, "
            "Consulate/Raydiant — but the real estate concentrates in a handful "
            "of healthcare REITs (Omega Healthcare, Sabra Health Care, CareTrust "
            "REIT, Welltower, Ventas) that own the buildings and lease them to "
            "operators. Managed-care organizations increasingly sit between the "
            "facility and the Medicare dollar. The PE thesis is opco turnaround "
            "and propco/opco separation, not chair-count growth."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicaid long-stay custodial (share of resident-days)",
                    "~55% of days",
                    "GOV · MedPAC / KFF nursing-facility payer mix"),
            Segment("Medicare FFS + MA skilled (share of resident-days)",
                    "~20% of days, majority of revenue",
                    "GOV · MedPAC nursing-facility chapter"),
            Segment("Medicare FFS SNF program spend",
                    "~$28.0B",
                    "GOV · MedPAC (Medicare FFS SNF)"),
            Segment("Total nursing-care-facility expenditure",
                    "~$190.0B",
                    "GOV · CMS National Health Expenditure Accounts"),
            Segment("Certified nursing facilities (US)",
                    "~14,700 facilities",
                    "SOURCED · CMS Nursing Home Care Compare (our file)"),
        ],
        growth_drivers=[
            "80+/85+ population growth ~3.5%/yr — the demographic demand wave",
            "SNF PPS annual rate updates ~3.0%/yr (market basket + wage index)",
            "MA penetration −2.0%/yr — shorter LOS, sub-FFS rates, prior auth",
            "Home & community rebalancing — Medicaid HCBS shift pulls custodial "
            "census out of the building",
            "Post-COVID occupancy recovery — a one-time tailwind off the trough",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicaid": 0.55,
            "Medicare Advantage": 0.12,
            "Medicare FFS": 0.10,
            "Private pay / LTC insurance / other": 0.23,
        },
        rate_mechanics=[
            "Patient-Driven Payment Model (PDPM) — the Medicare per-diem is a "
            "case-mix blend of five components (PT, OT, SLP, Nursing, NTA) plus "
            "a non-case-mix base; it replaced the RUG-IV therapy-minute model in "
            "Oct 2019, killing the incentive to maximize therapy minutes.",
            "SNF PPS annual update — market basket + productivity + wage index, "
            "with periodic PDPM parity recalibration cuts that claw back "
            "unintended payment growth.",
            "Part A coverage gate — a qualifying 3-day inpatient hospital stay; "
            "days 1-20 paid in full, days 21-100 subject to a daily coinsurance; "
            "the benefit caps at 100 days per spell of illness.",
            "Medicaid custodial per-diem — state-set (price-based, cost-based, "
            "or MDS case-mix); provider taxes, UPL, and state directed payments "
            "materially change the effective rate and are politics-dependent.",
            "Medicare Advantage per-diem — negotiated, typically a discount to "
            "FFS, with prior authorization, concurrent review, and a shorter "
            "authorized length of stay than FFS grants.",
            "SNF Value-Based Purchasing (readmissions withhold, up to ~2%) + "
            "SNF QRP quality reporting (a 2% penalty for non-reporting).",
        ],
        reimbursement_risk=(
            "The dominant risk is the Medicare-Advantage repricing of the "
            "skilled day: as MA passes half of all Medicare enrollment, more of "
            "the high-margin skilled census is paid a sub-FFS negotiated rate, "
            "authorized for fewer days, and gated by prior auth — so the same "
            "clinical stay earns materially less. Underneath sits chronic "
            "Medicaid rate inadequacy: the custodial per-diem often does not "
            "cover cost, leaving margin dependent on state supplemental pools "
            "(provider taxes, directed payments) that can be cut. Layer on the "
            "2024 minimum-staffing rule's labor step-up and PDPM parity "
            "recalibration, and the rate environment points down while the cost "
            "base points up."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("SNF Prospective Payment System / PDPM (SSA §1888(e))",
                 "Sets the Medicare skilled per-diem via case-mix — the price "
                 "of the sector's highest-margin days and the annual rate lever.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/skilled-nursing-facility-snf"),
            Rule("Minimum Staffing Standards for LTC Facilities (CMS, 2024)",
                 "Mandates 3.48 total nurse hours per resident-day (incl. 0.55 "
                 "RN and 2.45 nurse-aide hprd) and 24/7 on-site RN — a potential "
                 "existential cost step-up; under active legal and legislative "
                 "challenge, so treat as an unresolved but first-order swing.",
                 "https://www.cms.gov/newsroom/fact-sheets/medicare-and-medicaid-programs-minimum-staffing-standards-long-term-care-facilities-and-medicaid"),
            Rule("Requirements of Participation (42 CFR 483)",
                 "The survey-and-certification regime — F-tags, immediate "
                 "jeopardy, civil monetary penalties, and the Special Focus "
                 "Facility program gate participation and drive enforcement risk.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-483"),
            Rule("SNF ownership transparency — PE & REIT disclosure (2023)",
                 "CMS now collects and publishes facility ownership including "
                 "private-equity and REIT flags — the compliance/reputational "
                 "backdrop for sponsor-owned nursing homes.",
                 "https://www.cms.gov/newsroom/press-releases/hhs-announces-newly-released-data-track-medicare-nursing-home-ownership"),
            Rule("Five-Star Quality Rating System",
                 "The public 1-5 star composite (health inspections, staffing, "
                 "quality measures) gates MA/ACO referral flow and survey "
                 "attention — low stars are both a demand and an enforcement "
                 "problem.",
                 "https://www.cms.gov/medicare/health-safety-standards/certification-compliance/five-star-quality-rating-system"),
        ],
        policy_watch=[
            "Minimum-staffing-rule litigation and Congressional Review Act / "
            "legislative repeal efforts — the single biggest cost variable",
            "MA prior-authorization and coverage rules (two-midnight, SNF "
            "concurrent review) and the trajectory of MA sub-FFS rates",
            "Medicaid rate adequacy, provider-tax limits, and the '80% to "
            "direct care' Medicaid Access rule",
            "PDPM parity recalibration and future SNF PPS rate cuts",
            "Special Focus Facility program expansion and enforcement intensity",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Roughly 14,700 certified facilities under thousands of operators — "
            "fragmented at the operating layer, with regional chains rather than "
            "a national duopoly. For-profit ownership dominates (measured "
            "directly from our facility file below), and the real estate is "
            "concentrated in a few healthcare REITs that own buildings across "
            "many operators."),
        hhi_or_share=(
            "No dominant national operator — the chain layer is regional. The "
            "for-profit share is measured directly from our provider file below; "
            "the CMS file carries ownership TYPE but no operator name, so "
            "operator HHI is honestly omitted."),
        consolidation=(
            "A mature, CON-constrained, buy-and-turnaround market — new SNF "
            "construction is rare, so growth is acquiring and fixing aging "
            "facilities, not de novo. The decade's headline stories are "
            "distress and restructuring (Genesis, HCR ManorCare/ProMedica, "
            "Consulate) alongside the disciplined public compounder Ensign. "
            "REIT sale-leasebacks fund most transactions; the opco/propco split "
            "is the structuring default."),
        pe_activity=(
            "Sponsor activity centers on opco turnarounds, propco/opco "
            "separation, and regional roll-ups financed by REIT leases. It "
            "operates under a harsh spotlight: academic work linking PE "
            "ownership to worse outcomes, the 2023 ownership-transparency rule, "
            "and heightened survey scrutiny have made ownership structure and "
            "quality history first-order diligence, not footnotes."),
        notable_players=[
            "Ensign Group", "Genesis HealthCare", "Life Care Centers",
            "PruittHealth", "Signature HealthCARE", "National HealthCare (NHC)",
            "Omega Healthcare Investors (REIT)", "CareTrust REIT",
            "Sabra Health Care REIT",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Occupancy", "75-88%",
                "The fixed-cost chassis rewards fill; sub-80% occupancy on a "
                "Medicaid-heavy census is where facilities bleed."),
            Kpi("Quality mix (Medicare + MA % of days)", "12-25% of days",
                "The thin, high-margin slice of census; it carries the majority "
                "of revenue and is the single biggest margin determinant."),
            Kpi("Agency labor (% of nursing hours)", "5-25%+",
                "The post-COVID swing factor — travel-nurse premiums can erase a "
                "facility's operating margin; normalization is a core QoE item."),
            Kpi("Rent coverage (EBITDAR ÷ rent)", "~1.1-1.5x",
                "The REIT-lease world runs on coverage, not headline margin; "
                "thin coverage is a covenant and going-concern flag."),
            Kpi("Operating (opco) EBITDA margin", "2-8% (often lower)",
                "Structurally thin and volatile; many facilities ran negative "
                "post-COVID before occupancy and agency-labor recovery."),
            Kpi("30-day rehospitalization rate", "18-25%",
                "Drives SNF VBP incentive/penalty and MA/ACO referral "
                "willingness — a clinical KPI with direct revenue consequences."),
        ],
        margin_profile=(
            "A SNF is a fixed-cost, real-estate-heavy chassis whose margin is "
            "occupancy times quality mix minus a nursing-labor line that "
            "dominates the cost stack. Because Medicaid custodial days are paid "
            "below cost, the operating P&L only works when enough skilled "
            "(Medicare/MA) days ride on top and when labor is staffed rather "
            "than agency-filled. The propco/opco split means the stable cash is "
            "in the REIT rent, not the opco margin — so EBITDAR and rent "
            "coverage, not headline EBITDA, describe the real economics. A "
            "well-run, high-quality-mix operator with normalized labor can reach "
            "high-single-digit opco margins; a Medicaid-heavy, agency-dependent, "
            "under-occupied facility runs at or below breakeven on the same base."),
    ),
    risks=[
        Risk("2024 minimum-staffing rule labor step-up", "High",
             "3.48 hprd + 24/7 RN could be existential for rural/Medicaid-heavy "
             "facilities that cannot hire or pass through the cost; unresolved "
             "legal/legislative status makes it a large unhedged swing."),
        Risk("Medicare Advantage repricing of skilled days", "High",
             "Rising MA penetration means sub-FFS rates, prior auth, and shorter "
             "authorized LOS on the sector's highest-margin census."),
        Risk("Medicaid rate inadequacy + supplemental-payment fragility",
             "High",
             "Custodial per-diems below cost lean on provider taxes and directed "
             "payments that are state-politics-dependent and can be cut."),
        Risk("Agency / contract labor cost and nursing shortage", "High",
             "Travel-nurse premiums and CNA scarcity cap occupancy and compress "
             "margin; normalization is uncertain."),
        Risk("Survey/enforcement, SFF status, and ownership scrutiny", "Medium",
             "F-tags, immediate jeopardy, CMPs, and PE/REIT transparency raise "
             "compliance and reputational stakes for sponsor owners."),
        Risk("Real-estate leverage / rent-coverage stress", "Medium",
             "Master-lease cross-default and thin coverage turn an operating "
             "wobble into a portfolio-wide problem."),
    ],
    diligence_questions=[
        "What is the quality mix (Medicare + MA share of days AND of revenue) by "
        "facility, and how has it trended as MA penetration rose?",
        "What is agency labor as a percent of nursing hours and dollars, and "
        "what is the credible normalized run-rate?",
        "What is the Medicaid rate methodology by state, and how much of the "
        "effective rate depends on provider taxes / supplemental / directed "
        "payments that could be cut?",
        "What is rent coverage (EBITDAR ÷ rent) and the lease structure — master "
        "lease, cross-default, escalators, renewal?",
        "What is each facility's current nurse-hours-per-resident-day versus the "
        "3.48/0.55 RN thresholds, and the cost to comply?",
        "What are the Five-Star ratings, survey/F-tag history, immediate-"
        "jeopardy citations, CMPs, and any Special Focus status?",
        "What are the MA contract terms — rate versus FFS, authorized LOS, and "
        "denial/appeal rates — and how concentrated is MA exposure?",
        "What is the professional-liability claims history and reserve adequacy, "
        "and the CHOW/licensure transfer risk on close?",
    ],
    insider_lens=[
        "It is a spread business. Below-cost Medicaid custodial days are "
        "subsidized by above-cost Medicare/MA skilled days — the quality mix, "
        "not the headcount, is the asset. A facility with great margins usually "
        "has a great skilled mix, and that mix is exactly what MA is eroding.",
        "The building is not in the EBITDA. Most SNFs are leased from a REIT, so "
        "headline operating margin flatters a business whose stable cash is the "
        "rent. Underwrite EBITDAR and rent coverage, and read the master lease "
        "for cross-default before you believe a portfolio price.",
        "Agency labor is the silent killer. Post-COVID, the gap between a "
        "facility staffed with its own nurses and one leaning on travel agencies "
        "can be the entire operating margin — the whole diligence is whether the "
        "agency line normalizes.",
        "MA does not pay like Medicare. The same skilled day under an MA plan is "
        "worth less, authorized for fewer days, and gated by prior auth. As MA "
        "penetration climbs, the skilled-day economics quietly reprice down "
        "regardless of the PPS rate update.",
        "Supplemental Medicaid money is where the profit hides. Provider taxes, "
        "UPL, and state directed payments often turn a loss into a profit — and "
        "they are a legislative decision away from vanishing. Model the base "
        "rate without them.",
        "Nobody builds SNFs. CON laws and Medicaid economics mean the stock is "
        "old and fixed — this is a turnaround-and-consolidate market, so the "
        "value is operational (occupancy, mix, labor, stars), not de novo "
        "growth.",
    ],
    connections=default_connections(
        "snf",
        deals_sector="post_acute",
        extra_pages=[
            ("/diligence/tam-sam?template=snf",
             "SNF deep-dive — state footprint, beds, ownership, CHOW turnover"),
        ],
        connectors=[
            ("provider_data_nursing_home_provider_info",
             "CMS Nursing Home Care Compare — provider info & Five-Star"),
            ("cms_open_data_pbj_daily_nurse_staffing",
             "CMS Payroll-Based Journal — daily nurse staffing (hprd)"),
            ("cms_open_data_snf_all_owners",
             "CMS SNF All Owners — PE/REIT ownership transparency"),
            ("cms_open_data_snf_cost_report",
             "CMS SNF Cost Report — facility-level cost & margin"),
            ("provider_data_nursing_home_penalties",
             "CMS Nursing Home Penalties — CMPs & payment denials"),
            ("census_acs_cbsa_profile",
             "Census ACS — 80+/senior density for demand mapping"),
        ],
    ),
    sources=[
        Source("MedPAC — Report to Congress, skilled nursing facility services "
               "chapter (payment adequacy, margins, MA impact)", "GOV",
               "https://www.medpac.gov/"),
        Source("CMS SNF Prospective Payment System / PDPM — annual Final Rule",
               "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/skilled-nursing-facility-snf"),
        Source("CMS Minimum Staffing Standards for LTC Facilities — Final Rule "
               "(2024) fact sheet", "GOV",
               "https://www.cms.gov/newsroom/fact-sheets/medicare-and-medicaid-programs-minimum-staffing-standards-long-term-care-facilities-and-medicaid"),
        Source("KFF — Nursing Facilities: payer mix, ownership, and Medicaid "
               "financing", "ACADEMIC", "https://www.kff.org/"),
        Source("Gupta, Howell, Yannelis & Gupta — 'Owner Incentives and "
               "Performance in Healthcare: Private Equity Investment in Nursing "
               "Homes' (NBER)", "ACADEMIC", "https://www.nber.org/papers/w28474"),
        Source("PE Desk industry deep-dive (CMS Nursing Home Care Compare) + "
               "realized-deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=snf"),
    ],
    live_figures=live_figures_from_dive("snf"),
    trends=(
        "The SNF trajectory bends around payment redesign, a demographic wave, "
        "and a payer shift. PDPM (2019) reset the Medicare per-diem away from "
        "therapy minutes toward patient characteristics, ending the old "
        "therapy-maximization playbook. COVID then hollowed out occupancy and "
        "spiked agency labor, and the recovery since has been uneven — occupancy "
        "and labor are both mid-normalization. The structural story underneath "
        "is a squeeze: the 80+ population is growing fast (demand), but Medicare "
        "Advantage now covers half of Medicare and pays the skilled day less, "
        "for fewer days, with prior auth; Medicaid custodial rates chronically "
        "lag cost; and the 2024 minimum-staffing rule threatens a labor-cost "
        "step-up. Supply is old and CON-constrained, so almost no one builds — "
        "the market is turnaround and consolidation on a REIT-owned real-estate "
        "base, with ownership scrutiny (PE + REIT transparency) tightening the "
        "compliance frame."),
    growth_levers=[
        GrowthLever(
            "80+/85+ population growth (the demographic wave)",
            "The oldest-old cohort — the core SNF user — expands structurally as "
            "the boomers age into the highest-utilization years.",
            "+3.5%/yr demand", "GOV"),
        GrowthLever(
            "SNF PPS annual rate updates",
            "The Medicare per-diem steps up with the annual market basket and "
            "wage index, net of PDPM parity recalibration cuts.",
            "+3.0%/yr rate", "ILLUSTRATIVE"),
        GrowthLever(
            "Medicare Advantage penetration",
            "MA now covers half of Medicare and pays the skilled day a sub-FFS "
            "rate for fewer authorized days — a structural margin compressor, "
            "not a volume gain.",
            "−2.0%/yr margin drag", "GOV"),
        GrowthLever(
            "Home & community rebalancing (Medicaid HCBS)",
            "State Medicaid programs keep shifting long-term-care dollars to "
            "home and community settings, pulling custodial census out of the "
            "building.",
            "−1.0%/yr census", "GOV"),
        GrowthLever(
            "Post-COVID occupancy recovery",
            "Occupancy is climbing back from the pandemic trough — a one-time "
            "tailwind on a fixed-cost base until it re-normalizes.",
            "one-time recovery", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="The 80+ population wave, net of site-of-care substitution",
        analysis=(
            "The dominant demand driver is demographic: the 80+ (and especially "
            "85+) population is the core SNF user and is growing faster than the "
            "overall population as the boomer cohort ages, a highly predictable "
            "curve. But unlike dialysis, the SNF demand curve is heavily "
            "offset by substitution. Two forces divert census away from the "
            "building: Medicaid's decades-long rebalancing toward home- and "
            "community-based services for custodial care, and Medicare "
            "Advantage's explicit incentive to keep members out of the SNF or "
            "shorten the stay. The net is a real demographic tailwind that is "
            "substantially neutralized on the way in — so bed demand grows far "
            "more slowly than the 80+ population itself, and the winners take "
            "share (occupancy, quality mix) rather than ride the wave."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Direct-care nursing labor (RN/LPN/CNA)",
            "~50-60% of cost",
            "The dominant, largely fixed cost per occupied bed; the 2024 "
            "staffing rule and CNA scarcity push it up and cap occupancy.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Agency / contract labor premium",
            "swing line, embedded above",
            "The post-COVID margin swing — travel-nurse premiums sit inside the "
            "labor line and can move opco margin by several points; "
            "normalization is the core QoE question.", "ILLUSTRATIVE"),
        CostDriver(
            "Facility occupancy cost / REIT rent (propco)",
            "~10-15% of cost",
            "The real-estate chassis — rent to the REIT is the stable cash in "
            "the structure; coverage (EBITDAR ÷ rent), not margin, is the "
            "constraint.", "ILLUSTRATIVE"),
        CostDriver(
            "Dietary, housekeeping, ancillary & therapy contracts",
            "~10-15% of cost",
            "Hotel and clinical support services, partly variable with census; "
            "therapy is often contracted post-PDPM.", "ILLUSTRATIVE"),
        CostDriver(
            "G&A, insurance (professional liability) & compliance",
            "~8-12% of cost",
            "Corporate overhead plus a heavy professional-liability line and "
            "the survey/compliance apparatus.", "ILLUSTRATIVE"),
    ],
    cms_trend=CmsTrend(
        takeaway=(
            "The certification vintage tells the supply story bluntly: the SNF "
            "build wave crested decades ago and the surviving stock is old — the "
            "fingerprint of a CON-constrained, Medicaid-economics market where "
            "almost no one builds new facilities. Read the newest cohorts not as "
            "growth but as the rare exceptions; the investable action is "
            "turnaround, consolidation, and occupancy/mix improvement on an "
            "aging, fixed fleet, financed against REIT-owned real estate."),
        chart_kind="bars"),
    state_breakdown=(
        "Beds concentrate in the large industrial-Midwest and South states "
        "(Texas and California lead the count), for-profit ownership runs near "
        "three-quarters nationally and peaks even higher in several Southern "
        "states, and supply is shaped as much by state CON regimes and Medicaid "
        "rate methodology as by demography. The CMS file carries ownership TYPE "
        "but no operator name, so operator/chain HHI is honestly omitted — the "
        "structure is regional fragmentation over a REIT-owned real-estate base."),
)

register(REPORT)
