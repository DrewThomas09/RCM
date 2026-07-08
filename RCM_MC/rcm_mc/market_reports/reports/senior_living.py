"""Senior Living — private-pay housing-with-services for older adults.

Deals-only deep-dive (NIC MAP inventory is subscription data). Authored around
the structural fact that senior living is two businesses stapled together — real
estate (the building, financed like real estate) and operations (a hospitality-
plus-care business) — paid overwhelmingly out of pocket, with occupancy and rate
(RevPOR) on a fixed cost base driving the whole P&L. Distinct from Medicare/
Medicaid skilled nursing (``snf``).
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks,
    Kpi, MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule,
    Segment, Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="senior_living",
    name="Senior Living",
    care_setting="Post-acute",
    naics="623312",
    one_line_def=(
        "Private-pay, residential housing-with-services for older adults across "
        "independent living, assisted living, and memory care — a real-estate-"
        "plus-operations business paid overwhelmingly out of pocket, distinct "
        "from Medicare/Medicaid skilled nursing."),
    tam_headline=TamHeadline(
        value=100.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US senior-living revenue across independent living, "
            "assisted living, and memory care — roughly 1M+ investment-grade "
            "units at a blended monthly rate near $4,500-6,000. There is no "
            "government payment file to anchor a filed figure (the sector is "
            "private-pay), so this is a composite of NIC-benchmarked inventory "
            "× rate. Growth is the modeled composite of rate (+3-4%) and "
            "occupancy recovery."),
    ),
    executive_summary=[
        "It is two businesses stapled together: real estate (the building, "
        "financed like real estate) and operations (a hospitality-plus-care "
        "business). The deal structure — owner-operator, RIDEA, or triple-net "
        "lease between a REIT and an operator — determines who bears occupancy "
        "risk, and that is the first thing to underwrite.",
        "Occupancy and rate (RevPOR) on a fixed cost base ARE the P&L. The "
        "current thesis is a post-COVID occupancy recovery meeting a "
        "historically low new-construction pipeline — a supply/absorption "
        "setup that supports pricing power.",
        "It is private pay, so demand is exposed to the family's ability to pay "
        "— often funded by selling the parent's home. That makes it somewhat "
        "discretionary and rate-sensitive, unlike entitlement-funded post-acute "
        "care.",
        "Labor is the margin swing. The 2021-23 agency/temp-labor spike gutted "
        "NOI; normalizing labor plus rate growth is the margin-recovery story.",
        "IL, AL, and memory care are different businesses. Independent living "
        "is rent/hospitality (high margin, low care); memory care is high-"
        "acuity, high-labor, high-rate. The blend, and the acuity trend within "
        "a building, drive both margin and staffing.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Lead generation + sales (referral networks, digital, "
            "professional referrers)",
            "Assessment of acuity and level-of-care needs (IL vs AL vs memory "
            "care)",
            "Move-in — a rent/service agreement plus level-of-care charges",
            "Care + hospitality delivery (dining, housekeeping, activities, "
            "personal care, med management)",
            "Level-of-care reassessment as acuity rises (revenue steps up)",
            "Billing — monthly private-pay invoice (rare Medicaid HCBS for some "
            "AL)",
            "Move-out — to skilled nursing, hospital, or death; re-lease the "
            "unit",
        ],
        sites_of_care=[
            "Independent living (IL) — housing + hospitality, minimal care",
            "Assisted living (AL) — housing + ADL support + med management",
            "Memory care (MC) — secured, high-acuity dementia care",
            "Continuing care retirement communities (CCRC / life-plan "
            "communities) — the full continuum on one campus",
        ],
        money_flow=(
            "Revenue is a monthly charge per occupied unit: base rent plus, in "
            "assisted living and memory care, care/level-of-care fees that rise "
            "with acuity. The overwhelming majority is private pay — resident "
            "savings, the proceeds of a home sale, long-term-care insurance, "
            "and VA Aid & Attendance — because Medicare does not pay for "
            "custodial room-and-board and Medicaid HCBS covers only a limited, "
            "lower-acuity slice of assisted living (and never the room-and-"
            "board). Against that revenue sits a largely fixed cost base — the "
            "real estate (debt service or rent) and core staffing — so the P&L "
            "is dominated by occupancy and rate: every incremental occupied "
            "unit at the prevailing rate drops a high margin, and every empty "
            "unit is carried at full cost. Ownership is frequently split "
            "between a REIT/owner (PropCo) and an operator (OpCo) via a RIDEA "
            "structure or a triple-net lease, which allocates that occupancy "
            "risk between the parties."),
        key_players=(
            "Operators run the buildings: Brookdale Senior Living (the largest, "
            "publicly traded), Atria Senior Living, Sunrise Senior Living, Five "
            "Star (AlerisLife), Holiday (Atria/Welltower), Erickson Senior "
            "Living and Life Care Services (CCRCs), Discovery Senior Living, "
            "and Sonida. Health-care REITs own much of the real estate — "
            "Welltower, Ventas, National Health Investors, and Sabra — and "
            "private-equity and real-estate capital (Harrison Street, "
            "Blackstone, KKR) sit across the PropCo/OpCo structures. NIC (the "
            "National Investment Center) is the sector's data and capital-"
            "markets hub."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Independent living (IL)", "rent/hospitality — high margin",
                    "INDUSTRY · NIC MAP inventory & rate benchmarks"),
            Segment("Assisted living (AL)", "housing + ADL care",
                    "INDUSTRY · NIC MAP inventory & rate benchmarks"),
            Segment("Memory care (MC)", "high-acuity, high-rate secured care",
                    "INDUSTRY · NIC MAP inventory & rate benchmarks"),
            Segment("Investment-grade units (national)", "~1M+ units",
                    "ILLUSTRATIVE · modeled from NIC-benchmarked inventory"),
        ],
        growth_drivers=[
            "80+ population wave — the true demand cohort — accelerating into "
            "the late 2020s-2030s",
            "Occupancy recovery from the COVID trough (~+high-single-digit "
            "points off the bottom)",
            "Rate growth ~3-4%/yr, stronger in constrained-supply markets",
            "Historically low new-construction pipeline — a multi-year supply "
            "constraint",
            "Needs-based (AL/MC) demand resilience — care need is less "
            "discretionary than IL",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Private pay (out-of-pocket, LTC insurance, VA)": 0.90,
            "Medicaid HCBS (limited assisted living, no room-and-board)": 0.08,
            "Other (managed/duals demos, etc.)": 0.02,
        },
        rate_mechanics=[
            "Private-pay monthly rate — base rent plus level-of-care fees in "
            "AL/MC; the only truly market-priced post-acute setting, and the "
            "pricing power is real in tight markets.",
            "Level-of-care / acuity-based pricing — care charges step up as a "
            "resident's ADL needs rise, so revenue grows with acuity within a "
            "building.",
            "Medicaid HCBS waivers — cover services (not room-and-board) for a "
            "limited, lower-acuity AL slice in some states, at low rates.",
            "VA Aid & Attendance and long-term-care insurance — meaningful "
            "private-pay supplements that expand affordability.",
            "PropCo/OpCo economics — a RIDEA structure lets the owner "
            "participate in operating upside (and downside); a triple-net "
            "lease fixes rent and pushes occupancy risk to the operator.",
            "No Medicare — Medicare does not pay for custodial senior-living "
            "room-and-board, the defining contrast with skilled nursing.",
        ],
        reimbursement_risk=(
            "Because senior living is private pay, the 'reimbursement' risk is "
            "really demand and pricing risk: occupancy and achievable rate on a "
            "fixed cost base. In a downturn — or when home values soften — the "
            "adult children who fund many move-ins delay or trade down, "
            "pressuring occupancy and rate concessions. The Medicaid HCBS slice "
            "carries the opposite risk (low, state-set rates that barely cover "
            "cost) and is only relevant to lower-acuity AL in certain states. "
            "The capital structure adds financial risk: highly levered real "
            "estate against occupancy-sensitive NOI means interest-rate and "
            "refinancing exposure can matter as much as operations, and a "
            "triple-net operator can be squeezed between fixed rent and soft "
            "occupancy."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("State assisted-living licensure (50 different regimes)",
                 "Assisted living is licensed and surveyed at the STATE level "
                 "with no federal Conditions of Participation — the defining "
                 "regulatory contrast with skilled nursing, and a patchwork "
                 "that shapes staffing, med rules, and M&A.",
                 None),
            Rule("Memory-care licensure / dementia-care endorsements",
                 "Secured memory care often requires a special license or "
                 "endorsement, staffing minimums, and disclosure rules — "
                 "higher regulatory load than standard AL.",
                 None),
            Rule("No federal AL Conditions of Participation (contrast with SNF)",
                 "Unlike nursing homes, assisted living is not federally "
                 "certified — oversight, quality data, and enforcement are "
                 "state-by-state, which materially changes the risk profile.",
                 None),
            Rule("Fair Housing Act / ADA",
                 "Governs admission, accommodation, and discharge; move-out and "
                 "eviction rules are a recurring compliance and reputational "
                 "risk.",
                 "https://www.hud.gov/program_offices/fair_housing_equal_opp"),
            Rule("Medicaid HCBS Settings Rule (where AL takes waiver "
                 "residents)",
                 "For the AL that participates in Medicaid HCBS, the settings "
                 "rule governs what qualifies as community-based and how care "
                 "is delivered.",
                 "https://www.medicaid.gov/medicaid/home-community-based-services/guidance/home-community-based-services-final-regulation/index.html"),
        ],
        policy_watch=[
            "State staffing-ratio and med-administration rule changes for AL/MC",
            "Assisted-living quality-oversight and transparency initiatives",
            "Medicaid HCBS assisted-living waiver capacity and rate actions",
            "Interest-rate / commercial-real-estate financing conditions "
            "(the capital-structure variable)",
            "Middle-market / active-adult product-model regulation as the "
            "sector expands affordability",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Operationally fragmented — even the largest operator runs a "
            "low-single-digit share of national units, and thousands of "
            "regional and single-market operators fill out the base. Ownership "
            "of the real estate is more concentrated in the health-care REITs. "
            "There is no vendored national inventory file (NIC MAP is "
            "subscription data), so a computed geographic share is honestly "
            "omitted — fragmentation on the operating side is the structure."),
        hhi_or_share=(
            "Brookdale is the largest operator but still a low-single-digit "
            "percentage of national inventory; concentration is low on the "
            "operating side and moderately higher on the REIT ownership side. "
            "No dominant national brand controls pricing."),
        consolidation=(
            "Consolidation runs through the capital structure. Health-care "
            "REITs (Welltower, Ventas, NHI, Sabra) assembled large owned "
            "portfolios and contract operations to third-party operators via "
            "RIDEA or triple-net leases; private-equity and real-estate capital "
            "(Harrison Street, Blackstone, KKR, Bain) trade PropCo and OpCo "
            "positions. Operator-level roll-ups exist but are secondary to the "
            "real-estate M&A that dominates the sector's transactions."),
        pe_activity=(
            "Very active, but as a real-estate-plus-operations trade rather "
            "than a pure services roll-up. The live thesis is the post-COVID "
            "occupancy recovery against a starved construction pipeline, plus "
            "buying distressed or under-managed assets at a discount to "
            "replacement cost ahead of the 80+ demographic wave. Diligence "
            "centers on the PropCo/OpCo split, occupancy/rate trajectory, "
            "labor normalization, and the debt structure."),
        notable_players=[
            "Brookdale Senior Living", "Atria Senior Living",
            "Sunrise Senior Living", "Five Star (AlerisLife)",
            "Erickson Senior Living", "Discovery Senior Living",
            "Welltower (REIT)", "Ventas (REIT)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Occupancy", "stabilized ~88-92% target",
                "The single biggest P&L variable on a fixed cost base; "
                "break-even is often ~80-85%."),
            Kpi("RevPOR / monthly rate", "IL/AL ~$3,500-7,000 · MC "
                "~$6,000-10,000+",
                "Revenue per occupied room; memory care commands the highest "
                "rate for the highest acuity."),
            Kpi("Property-level operating (NOI) margin", "~25-35%",
                "Higher for IL (less labor), lower for AL/MC (more care "
                "staffing); the target of the margin-recovery thesis."),
            Kpi("Agency / contract-labor share", "the margin swing",
                "The 2021-23 agency spike gutted NOI; normalization is the "
                "recovery lever."),
            Kpi("Length of stay", "AL ~18-30 months · MC shorter",
                "Drives turnover, re-lease frequency, and sales/marketing "
                "load."),
            Kpi("Move-in / sales velocity", "the occupancy driver",
                "Lead-to-move-in conversion and sales pace determine how fast "
                "occupancy recovers."),
        ],
        margin_profile=(
            "Senior-living margin is occupancy × rate on a largely fixed cost "
            "base — real estate (debt service or rent) plus core staffing — so "
            "operating leverage is high in both directions. A well-occupied "
            "community at a healthy RevPOR earns a mid-to-high-20s to mid-30s "
            "NOI margin; a community carrying empty units or a spike in agency "
            "labor can fall toward break-even on the same fixed base. Product "
            "mix matters: independent living runs a higher margin at lower "
            "labor intensity, while memory care commands the highest rate but "
            "carries the heaviest staffing. Because the exit is frequently a "
            "real-estate transaction, cap rates and the financing environment "
            "shape realized returns as much as operations do."),
    ),
    risks=[
        Risk("Occupancy / demand softness", "High",
             "On a fixed cost base, an occupancy shortfall (or a slow post-"
             "COVID recovery) compresses NOI quickly."),
        Risk("Labor cost / agency reliance", "High",
             "Caregiver and dining/housekeeping labor is the dominant "
             "operating cost; an agency-labor spike gutted margins in "
             "2021-23."),
        Risk("Private-pay affordability / housing-market sensitivity", "Medium",
             "Move-ins are often funded by a home sale or savings, so demand is "
             "discretionary and softens with the housing market."),
        Risk("Capital structure / interest-rate & refinancing", "Medium",
             "Levered real estate against occupancy-sensitive NOI creates rate "
             "and refinancing exposure independent of operations."),
        Risk("New-supply resurgence in a market", "Medium",
             "A local construction wave can undercut occupancy and rate; the "
             "current national pipeline is low but localized supply varies."),
        Risk("State licensure / acuity-creep and staffing rules", "Medium",
             "Rising in-building acuity and tightening state staffing/med rules "
             "raise cost and liability, especially in memory care."),
    ],
    diligence_questions=[
        "What is the deal structure — owner-operator, RIDEA, or triple-net — "
        "and who bears occupancy risk?",
        "What is the occupancy trajectory by community, and how far is each "
        "from stabilized and from break-even?",
        "What is RevPOR and the rate-growth history, and how much pricing power "
        "exists given local supply?",
        "What is the agency/contract-labor share and the trend — is labor "
        "normalizing off the 2021-23 spike?",
        "What is the IL/AL/MC mix and the in-building acuity trend (and its "
        "staffing implications)?",
        "What is the local new-construction pipeline in each market, and what "
        "is the absorption outlook?",
        "What is the debt structure — maturities, rate, and covenants — against "
        "occupancy-sensitive NOI?",
        "What share of revenue touches Medicaid HCBS, and what is the exposure "
        "to low state rates?",
    ],
    insider_lens=[
        "Underwrite the structure before the operations. RIDEA vs triple-net "
        "vs owner-operator decides who eats an occupancy miss — the same "
        "building is a different investment depending on where the risk sits.",
        "It is a fixed-cost box: occupancy and RevPOR are almost the entire "
        "story. The current setup — recovering occupancy meeting the lowest "
        "construction pipeline in years — is a classic absorption trade, market "
        "by market.",
        "The demographics everyone cites are a decade out. The 80+ wave (the "
        "true need age, not the 65+ headline) really lands late this decade "
        "into the 2030s — near-term returns come from occupancy recovery and "
        "starved supply, not the demographic itself yet.",
        "Labor is the margin, full stop. The 2021-23 agency spike showed how "
        "fast a caregiver/dining shortfall converts to NOI loss; the recovery "
        "thesis is really a labor-normalization thesis.",
        "It is discretionary in a way entitlement post-acute is not. Many "
        "move-ins are funded by selling the parent's house, so the housing "
        "market and the adult child's balance sheet are demand inputs — read "
        "senior living partly as a consumer-real-estate business.",
        "IL, AL, and memory care are not one product. IL is a high-margin "
        "hospitality lease; memory care is a high-rate, high-liability care "
        "business. A 'senior living' blended margin can hide very different "
        "underlying economics.",
    ],
    connections=default_connections(
        "senior_living",
        deals_sector="senior_living",
        extra_pages=[
            ("/market/snf",
             "Adjacency — the Skilled Nursing report (the acuity step-up and "
             "move-out destination)"),
            ("/diligence/tam-sam?template=senior_living",
             "Size it — senior-living TAM/SAM build (80+ × penetration × rate)"),
        ],
        connectors=[
            ("census_acs_cbsa_profile",
             "Census ACS (CBSA) — 75+/80+ density & income, the core demand "
             "and affordability read"),
            ("census_acs_county_profile",
             "Census ACS (county) — local senior demand and home-value "
             "affordability"),
            ("bls_qcew_industry_area",
             "BLS QCEW — senior-living / residential-care employment & wages "
             "(the labor swing)"),
            ("cms_open_data_ltc_facility_characteristics",
             "CMS LTC facility characteristics — the institutional-care "
             "reference set"),
            ("provider_data_nursing_home_provider_info",
             "CMS Nursing Home Care Compare — the acuity step-up / move-out "
             "destination"),
        ],
    ),
    sources=[
        Source("NIC — National Investment Center for Seniors Housing & Care "
               "(occupancy, rate, inventory benchmarks)", "INDUSTRY",
               "https://www.nic.org/"),
        Source("Argentum — senior-living industry association (operations, "
               "workforce, policy)", "INDUSTRY", "https://www.argentum.org/"),
        Source("American Health Care Association / NCAL — assisted-living "
               "policy and data", "INDUSTRY", "https://www.ahcancal.org/"),
        Source("Health-care REIT disclosures (Welltower, Ventas) — RIDEA/"
               "triple-net operating and occupancy data", "INDUSTRY",
               "https://www.welltower.com/"),
        Source("GAO / KFF — assisted-living oversight and Medicaid HCBS "
               "assisted-living analysis", "GOV",
               "https://www.gao.gov/"),
        Source("PE Desk industry deep-dive (deals-only) + realized-deal "
               "corpus for senior living", "INTERNAL",
               "/diligence/tam-sam?template=senior_living"),
    ],
    live_figures=live_figures_from_dive("senior_living"),
    trends=(
        "Senior living came out of COVID with a deep occupancy scar and a "
        "labor-cost shock, and the last few years have been a recovery story. "
        "Occupancy fell hard in 2020-21 (memory care and assisted living hit "
        "worst), then clawed back through the mid-2020s; simultaneously an "
        "agency-labor spike in 2021-23 gutted property-level NOI. Two forces "
        "now define the trajectory. First, new construction has run at "
        "historically low levels — rising rates and construction costs starved "
        "the pipeline — setting up a multi-year supply constraint just as "
        "occupancy recovers, which supports rate growth in tight markets. "
        "Second, the demographic tailwind everyone cites is real but still "
        "ahead: the 80+ population (the true need cohort, not the 65+ headline) "
        "accelerates into the late 2020s and 2030s. The capital story is a "
        "real-estate one — REITs, PE, and real-estate funds trading PropCo/OpCo "
        "positions, buying distressed or under-managed assets below replacement "
        "cost. The near-term return driver is occupancy recovery plus labor "
        "normalization on a fixed cost base; the long-term one is the "
        "demographic wave meeting constrained supply."),
    growth_levers=[
        GrowthLever(
            "Occupancy recovery (post-COVID)",
            "Filling units back toward stabilized occupancy on a fixed cost "
            "base drops high-margin revenue — the near-term return driver.",
            "primary near-term", "ILLUSTRATIVE"),
        GrowthLever(
            "Rate growth / pricing power",
            "Private-pay rate increases, stronger where local supply is "
            "constrained, lift RevPOR ahead of cost.",
            "+3-4%/yr rate", "ILLUSTRATIVE"),
        GrowthLever(
            "Constrained new-supply pipeline",
            "Historically low construction limits competing inventory, "
            "protecting occupancy and rate through the recovery.",
            "supply tailwind", "ILLUSTRATIVE"),
        GrowthLever(
            "80+ demographic wave",
            "The true need cohort accelerates late this decade into the 2030s, "
            "enlarging demand structurally.",
            "long-term", "GOV"),
        GrowthLever(
            "Labor normalization",
            "Rolling off the 2021-23 agency-labor spike restores NOI on the "
            "existing revenue base — a margin lever more than a growth one.",
            "margin recovery", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="80+ population × penetration, gated by occupancy absorption and "
               "supply",
        analysis=(
            "The true demand cohort for senior living is the 80+ population — "
            "the age at which ADL dependency and dementia prevalence rise "
            "sharply — not the 65+ figure often quoted. That cohort is set to "
            "accelerate meaningfully from the late 2020s into the 2030s as the "
            "leading edge of the baby boom ages in, structurally enlarging "
            "demand. But realized volume is an absorption story on a fixed "
            "stock of units: near-term growth comes from re-filling the "
            "post-COVID occupancy gap against a starved construction pipeline, "
            "and only later does the demographic wave itself become the binding "
            "driver. Penetration (the share of eligible seniors who choose "
            "congregate housing-with-services) is the swing factor, and it is "
            "sensitive to affordability and the housing market — so demand is "
            "large and rising but partly discretionary."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Care & hospitality labor (caregivers, dining, housekeeping)",
            "the dominant operating cost",
            "The single biggest and most volatile cost; agency/temp labor is "
            "the swing that gutted NOI in 2021-23.", "ILLUSTRATIVE"),
        CostDriver(
            "Real estate (debt service or rent)",
            "the fixed capital cost",
            "Whether owned (debt service) or leased (rent), the building is a "
            "large fixed cost that occupancy must cover — and the source of "
            "rate/refinancing risk.", "ILLUSTRATIVE"),
        CostDriver(
            "Food & dining operations",
            "a material variable cost",
            "Dining is a core amenity and a real input-cost exposure that "
            "scales with occupancy.", "ILLUSTRATIVE"),
        CostDriver(
            "Utilities, maintenance & capex",
            "meaningful for aging buildings",
            "Older communities carry higher upkeep and refresh capex to stay "
            "competitive on move-ins.", "ILLUSTRATIVE"),
        CostDriver(
            "Sales & marketing (move-in generation)",
            "the occupancy investment",
            "Lead generation and sales staffing to drive move-ins — the cost "
            "of buying occupancy, especially during recovery.", "ILLUSTRATIVE"),
    ],
    # Deals-only vertical: no provider_backed CMS roll, so cms_trend and a
    # computed state_breakdown are intentionally omitted — the renderer shows an
    # honest "unavailable offline" note and the qualitative sections carry the
    # weight. The live figures above are the corpus senior-living deals,
    # computed at render.
)

register(REPORT)
