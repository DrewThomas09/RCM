"""Hospitals — general acute-care inpatient and hospital-outpatient care.

Deals-only market-report module (the analytics state/supply-trend helpers cover
the six provider-CSV slugs, and hospitals is not one of them — so no cms_trend
and no computed state_breakdown here). Live SOURCED figures DO wire from
``hospitals_deep_dive()`` (the HCRIS cost-report universe, ~6.1K filers), which
carries real filed net-patient-revenue by state and a mid-size ($250M-$1B NPR)
"pool" read. The qualitative sections are authored around the two prices every
hospital lives on — the Medicare IPPS/OPPS administered rate and the commercial
multiple that cross-subsidizes it — and the Steward/MPT sale-leaseback failure
that reset how sponsors think about hospital real estate.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="hospitals",
    name="Hospitals",
    care_setting="Other services",
    naics="622110",
    one_line_def=(
        "General acute-care hospitals — inpatient admissions plus a growing "
        "hospital-outpatient book — paid a per-discharge Medicare DRG rate "
        "(IPPS), a per-encounter outpatient rate (OPPS), and negotiated "
        "commercial multiples that cross-subsidize the government shortfall."),
    tam_headline=TamHeadline(
        value=1500.0, unit="$B", growth_pct=5.0, basis_label="GOV",
        basis_note=(
            "CMS National Health Expenditure 'Hospital Care' category, ~$1.5T — "
            "the single largest category of US health spending. Growth is the "
            "historical NHE hospital-care trend (~5%/yr), not a modeled "
            "composite."),
    ),
    executive_summary=[
        "A hospital lives on two prices: the administered Medicare/Medicaid "
        "rate (which pays below cost for most services) and the commercial "
        "multiple (often 2-3x Medicare) that cross-subsidizes it. Payer mix — "
        "not volume — is the P&L. A Medicaid- and Medicare-heavy hospital can "
        "run negative margin at the same occupancy a commercial-rich one thrives at.",
        "Median operating margins are thin (low-single-digit, many negative "
        "since 2021). Labor is ~50%+ of cost and the post-COVID nursing-wage "
        "and agency-staffing shock is the proximate cause of the margin "
        "compression — this is an operating-leverage business with almost no "
        "cushion.",
        "Medicare Advantage is the current margin destroyer: prior-auth denials, "
        "downgraded inpatient-to-observation status, and slow-pay push AR and "
        "write-offs up as MA takes share from traditional Medicare — a "
        "first-order diligence item, not a footnote.",
        "PE ownership of hospitals is thin and radioactive after Steward Health "
        "Care: the Cerberus sale-leaseback to Medical Properties Trust monetized "
        "the real estate, loaded the operating company with rent, and ended in "
        "2024 bankruptcy. Hospital real estate is now underwritten as a "
        "liability, not a lever.",
        "Volume is migrating out of the inpatient bed — to hospital-outpatient "
        "departments, ASCs, and the home — while site-neutral payment policy "
        "attacks the outpatient billing premium that migration was supposed to "
        "protect. The asset base and its favored reimbursement are diverging.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Access — ED presentation, physician referral, or scheduled procedure",
            "Registration, insurance verification, and prior authorization",
            "Admission status decision — inpatient vs observation (two-midnight rule)",
            "Care delivery — OR, ICU, med-surg, ancillary (imaging, lab, pharmacy)",
            "Clinical documentation & coding → MS-DRG or outpatient APC assignment",
            "Claim submission — IPPS per-discharge / OPPS per-encounter / commercial",
            "Denials management, appeals, and patient balance collection",
        ],
        sites_of_care=[
            "Inpatient acute beds (med-surg, ICU, telemetry) — the DRG base",
            "Hospital outpatient departments (HOPD) — the provider-based premium",
            "Emergency department (the unscheduled front door and payer-mix sink)",
            "Hospital-owned ASCs, imaging, and physician clinics (the system)",
            "Hospital-at-Home (CMS acute-care-at-home waiver, small but growing)",
        ],
        money_flow=(
            "Medicare pays inpatient stays a fixed per-discharge amount under "
            "the Inpatient Prospective Payment System (IPPS): the MS-DRG base "
            "rate is adjusted by the area wage index and topped by add-ons — "
            "disproportionate-share (DSH), indirect medical education (IME), "
            "new-technology, and outlier payments. Hospital outpatient care is "
            "paid per-encounter under OPPS (APCs). Medicaid pays less, often "
            "supplemented by DSH and state directed/supplemental payments. "
            "Commercial payers pay a negotiated multiple of Medicare — the "
            "cross-subsidy that keeps the lights on — while 340B drug-pricing "
            "discounts are a distinct margin engine for qualifying DSH "
            "hospitals. The net result: government payers cover the majority of "
            "volume below cost, and a shrinking commercial book carries the margin."),
        key_players=(
            "For-profit systems — HCA Healthcare (the scaled operator), Tenet "
            "Healthcare, Community Health Systems. Large nonprofit and "
            "faith-based systems — CommonSpirit, Ascension, Trinity Health, "
            "Providence, Advocate Health, Kaiser Permanente (integrated), and "
            "academic medical centers. Universal Health Services spans acute and "
            "behavioral. On the real-estate side, hospital REITs — Medical "
            "Properties Trust above all — own the ground under many operators via "
            "sale-leaseback. The acquirable pool for sponsors is thin: distressed "
            "community and rural hospitals, nonprofit divestitures, and "
            "management/JV structures rather than outright platform M&A."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Hospital care — total US spend",
                    "~$1.5T (largest NHE category)",
                    "GOV · CMS National Health Expenditure"),
            Segment("Community hospitals (US)", "~5,000 facilities",
                    "INDUSTRY · AHA Hospital Statistics"),
            Segment("Ownership mix — nonprofit / for-profit / government",
                    "~58% / ~24% / ~18%",
                    "INDUSTRY · AHA ownership split"),
            Segment("Inpatient vs outpatient revenue",
                    "outpatient now ~50%+ of hospital revenue",
                    "INDUSTRY · AHA / MedPAC outpatient-shift trend"),
            Segment("HCRIS cost-report filers in our universe",
                    "~6.1K filers (real filed NPR by state)",
                    "SOURCED · CMS HCRIS vendored snapshot"),
        ],
        growth_drivers=[
            "Aging population + acuity growth — utilization ~2-3%/yr",
            "Annual IPPS/OPPS market-basket rate updates ~2.5-3.5%/yr",
            "Outpatient migration — HOPD/ASC/home shift moves the revenue mix",
            "Commercial rate negotiation — the cross-subsidy escalator",
            "Labor cost inflation — a cost driver that outran rate updates post-2021",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.44,
            "Commercial": 0.33,
            "Medicaid": 0.17,
            "Self-pay / other": 0.06,
        },
        rate_mechanics=[
            "Inpatient Prospective Payment System (IPPS) — per-discharge MS-DRG "
            "base rate × wage index, plus DSH, IME, new-tech, and outlier add-ons.",
            "Outpatient Prospective Payment System (OPPS) — per-encounter APC "
            "rates for the hospital-outpatient (provider-based) book.",
            "Two-midnight rule — governs inpatient vs observation status; MA "
            "downgrades to observation are a live revenue leak.",
            "340B drug pricing — steep discounts on outpatient drugs for "
            "qualifying DSH hospitals; a distinct, contested margin engine.",
            "Commercial multiple of Medicare — negotiated 2-3x rates that "
            "cross-subsidize below-cost government payers.",
            "Site-neutral payment — CMS is equalizing HOPD and physician-office "
            "rates for select services, eroding the provider-based premium.",
            "Medicaid DSH and state directed/supplemental payments — a material, "
            "politically exposed slice of safety-net hospital revenue.",
        ],
        reimbursement_risk=(
            "The structural risk is the cross-subsidy math: Medicare and "
            "Medicaid pay below cost for most services, so margin depends on a "
            "commercial book that is shrinking as Medicare Advantage takes "
            "share. MA is the acute pain point — prior-auth denials, "
            "inpatient-to-observation downgrades, and slow-pay inflate AR and "
            "write-offs. Layered on top: threatened DSH cuts, 340B eligibility "
            "and remedy fights, expanding site-neutral payment that attacks the "
            "HOPD premium, the No Surprises Act on out-of-network ED and "
            "hospital-based physicians, and price-transparency compliance. Bad "
            "debt and charity care rise with high-deductible plans and the "
            "post-redetermination Medicaid unwind."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare IPPS / OPPS annual Final Rules",
                 "Set the per-discharge and per-encounter rates and the wage "
                 "index that govern the majority of hospital volume — the single "
                 "most important prices in the sector.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems"),
            Rule("Hospital Conditions of Participation (42 CFR 482)",
                 "Survey-and-certification regime; deficiencies threaten Medicare "
                 "participation and accreditation.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-482"),
            Rule("EMTALA — Emergency Medical Treatment and Labor Act",
                 "Mandates screening and stabilization regardless of ability to "
                 "pay — the structural driver of ED uncompensated care.",
                 "https://www.cms.gov/medicare/regulations-guidance/legislation/emergency-medical-treatment-labor-act"),
            Rule("340B Drug Pricing Program",
                 "Discounted outpatient drugs for DSH/eligible hospitals — a "
                 "major margin source under sustained legislative and manufacturer "
                 "attack.",
                 "https://www.hrsa.gov/opa"),
            Rule("Hospital price transparency + No Surprises Act",
                 "Machine-readable rate posting and out-of-network balance-billing "
                 "limits reshape commercial negotiating leverage and ED billing.",
                 "https://www.cms.gov/nosurprises"),
            Rule("FTC/DOJ merger review + state COPA / AG oversight",
                 "Hospital mergers (including cross-market) and nonprofit "
                 "conversions face antitrust and attorney-general scrutiny.",
                 None),
        ],
        policy_watch=[
            "Site-neutral payment expansion beyond drug administration",
            "Medicare Advantage prior-auth / observation-status rulemaking",
            "340B eligibility, contract-pharmacy, and rebate-model litigation",
            "Medicaid DSH cut schedule and state directed-payment approvals",
            "Post-unwind Medicaid enrollment and its uncompensated-care effect",
            "Nonprofit tax-exemption and community-benefit scrutiny",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Roughly 5,000 community hospitals, but the market is regional, not "
            "national: a hospital competes in its metro/catchment, and local "
            "concentration is often high even where national share is not. "
            "Ownership splits roughly 58% nonprofit, 24% for-profit, 18% "
            "government. Our HCRIS universe below carries the real filed "
            "net-patient-revenue base by state and a size-tier read (HCRIS "
            "publishes no ownership field, so size is the honest structure cut)."),
        hhi_or_share=(
            "National share is low and unconcentrated, but LOCAL market HHI is "
            "the number that matters — many metros are effectively duopolies or "
            "monopolies after decades of merger, which is precisely why the FTC "
            "scrutinizes hospital deals."),
        consolidation=(
            "Three decades of horizontal and cross-market merger have built "
            "large nonprofit and for-profit systems, with the stated thesis of "
            "scale, commercial-rate leverage, and back-office synergy. The FTC "
            "has grown more aggressive, challenging both in-market and "
            "cross-market deals. Vertical integration — hospitals employing "
            "physicians and buying outpatient assets — continues alongside."),
        pe_activity=(
            "Direct sponsor ownership of acute hospitals is limited and, after "
            "Steward, reputationally toxic. The Cerberus/Steward playbook — buy "
            "a distressed system, sell the real estate to Medical Properties "
            "Trust in a sale-leaseback, and extract the proceeds — collapsed "
            "into a 2024 bankruptcy that became the cautionary tale. Live "
            "sponsor activity concentrates in the ecosystem instead: RCM, "
            "staffing, hospital-at-home, ED/hospitalist groups, and real estate, "
            "not the acute operating company itself."),
        notable_players=[
            "HCA Healthcare", "Tenet Healthcare", "Community Health Systems",
            "CommonSpirit Health", "Ascension", "Trinity Health",
            "Advocate Health", "Universal Health Services",
            "Medical Properties Trust (REIT)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Operating margin (median)", "0-3% (many negative post-2021)",
                "Thin and payer-mix-driven; the sector ran negative aggregate "
                "operating margin through the labor shock."),
            Kpi("Salaries & benefits / net patient revenue", "~50-58%",
                "Labor is the dominant cost; the metric that moved most as "
                "nursing wages and agency staffing spiked."),
            Kpi("Case mix index (CMI)", "~1.4-2.0+",
                "Average DRG weight — acuity and documentation intensity; higher "
                "CMI lifts revenue per discharge but draws audit scrutiny."),
            Kpi("Occupancy / adjusted patient days", "~60-70%",
                "Bed utilization; the fixed-cost chassis rewards throughput but "
                "acute occupancy has structurally softened with the outpatient shift."),
            Kpi("Cost per adjusted discharge", "rising faster than rate updates",
                "The unit-cost trend that outran IPPS market-basket increases "
                "post-2021 — the core margin squeeze."),
            Kpi("Payer mix (commercial share)", "the value variable",
                "Commercial share drives margin far more than volume; a few "
                "points of mix is worth more than occupancy gains."),
        ],
        margin_profile=(
            "A hospital is a very-high-fixed-cost chassis — labor, plant, and "
            "on-call specialty coverage are largely fixed — so contribution "
            "steps up with throughput and, decisively, with commercial payer "
            "mix. Because government payers reimburse below cost, the P&L is a "
            "cross-subsidy: the commercial book funds the Medicare/Medicaid "
            "shortfall. That makes margin fragile and mix-sensitive, and it is "
            "why the same occupancy produces a healthy margin in a "
            "commercial-rich suburban system and a loss in a Medicaid-heavy "
            "urban or rural one."),
    ),
    risks=[
        Risk("Commercial-mix erosion (MA growth + payer denials)", "High",
             "MA takes share from traditional Medicare and denies/downgrades "
             "claims, directly compressing the cross-subsidy that carries margin."),
        Risk("Labor cost inflation and clinical staffing shortage", "High",
             "Salaries/benefits are ~50%+ of cost; the nursing-wage and agency "
             "shock drove the sector to negative operating margins."),
        Risk("Real-estate / sale-leaseback leverage (the Steward risk)", "High",
             "Monetizing hospital real estate loads fixed rent onto a thin-margin "
             "operator — the failure mode that bankrupted Steward."),
        Risk("Site-neutral payment + 340B erosion", "Medium",
             "CMS equalizing HOPD and office rates, plus 340B attacks, remove "
             "two of the highest-margin revenue premiums."),
        Risk("Uncompensated care (Medicaid unwind + high-deductible plans)",
             "Medium",
             "EMTALA obligations plus rising bad debt and charity care hit "
             "safety-net and rural hospitals hardest."),
        Risk("Antitrust / regulatory block on consolidation", "Medium",
             "FTC and state AGs increasingly challenge in-market and cross-market "
             "hospital mergers and nonprofit conversions."),
    ],
    diligence_questions=[
        "What is the payer mix by service line, and what is the commercial-rate "
        "trajectory versus the Medicare/Medicaid shortfall?",
        "What is the Medicare Advantage denial, downgrade, and days-in-AR trend, "
        "and what reserves are held against it?",
        "Is the real estate owned, leased, or in a sale-leaseback — and what is "
        "the rent-coverage and lease-escalator exposure?",
        "What share of margin depends on 340B and DSH/supplemental payments, and "
        "what is the exposure to cuts?",
        "How much revenue sits in the provider-based HOPD premium exposed to "
        "site-neutral policy?",
        "What is the salaries-to-NPR ratio and the agency/travel-labor "
        "dependence, and how has it trended since 2021?",
        "What is the local-market HHI and the antitrust posture of any "
        "consolidation thesis?",
        "What is the CMI and coding intensity, and what is the RAC/UPIC audit "
        "and recoupment history?",
    ],
    insider_lens=[
        "The commercial cross-subsidy is the whole game. Government payers cover "
        "most volume below cost; a shrinking commercial book funds the gap. "
        "Underwrite payer mix and the commercial-rate trend, not census — a full "
        "hospital with the wrong mix loses money.",
        "Medicare Advantage is where margin quietly leaks. The denial, "
        "prior-auth, and inpatient-to-observation downgrade machine turns booked "
        "revenue into AR and write-offs; the trend line matters more than the "
        "contract rate.",
        "Hospital real estate is a trap dressed as a lever. Steward proved that "
        "a sale-leaseback converts owned plant into fixed rent on a thin-margin "
        "operator — cash today, insolvency tomorrow. Read the lease before the P&L.",
        "340B is a hidden P&L engine that outsiders miss and that Congress keeps "
        "aiming at. For a DSH hospital, the spread on discounted outpatient drugs "
        "can rival service-line margin — and it is neither stable nor guaranteed.",
        "The asset base and its reimbursement are diverging: volume is leaving "
        "the inpatient bed for HOPD, ASC, and home just as site-neutral policy "
        "strips the outpatient billing premium. A thesis priced on the "
        "provider-based rate is betting against CMS's own direction.",
    ],
    connections=default_connections(
        "hospitals",
        deals_sector="hospital",
        extra_pages=[
            ("/diligence/tam-sam?template=hospitals",
             "Hospitals deep-dive — HCRIS state NPR + size-tier map"),
        ],
        connectors=[
            ("hcris_cost_reports",
             "CMS HCRIS — hospital cost reports (NPR, margins, wage index)"),
            ("provider_data_catalog",
             "CMS Provider Data Catalog — Hospital Care Compare"),
            ("cms_open_data_catalog",
             "CMS Open Data — IPPS/OPPS provider utilization & payment"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA demographics for catchment/payer-mix mapping"),
        ],
    ),
    sources=[
        Source("CMS National Health Expenditure Accounts — Hospital Care "
               "category", "GOV",
               "https://www.cms.gov/data-research/statistics-trends-and-reports/national-health-expenditure-data"),
        Source("MedPAC — Report to Congress, hospital inpatient and outpatient "
               "services chapters", "GOV", "https://www.medpac.gov/"),
        Source("CMS IPPS / OPPS annual Final Rules (rates, wage index, DSH/IME)",
               "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems"),
        Source("American Hospital Association — Hospital Statistics / TrendWatch",
               "INDUSTRY", "https://www.aha.org/"),
        Source("Health Affairs / NEJM research on hospital margins, "
               "consolidation, and 340B", "ACADEMIC", "https://www.healthaffairs.org/"),
        Source("PE Desk industry deep-dive (CMS HCRIS cost-report universe) + "
               "realized-deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=hospitals"),
    ],
    live_figures=live_figures_from_dive("hospitals"),
    trends=(
        "The hospital trajectory bends around three forces. First, the "
        "outpatient migration: procedures and diagnostics have moved steadily "
        "from the inpatient bed to hospital-outpatient departments, ASCs, and "
        "the home, so outpatient is now roughly half of hospital revenue even "
        "as acute occupancy softens — and site-neutral payment policy is now "
        "attacking the very outpatient premium that migration relied on. "
        "Second, the labor shock: the post-COVID nursing-wage and agency-"
        "staffing surge drove salaries above half of net patient revenue and "
        "pushed aggregate operating margins negative in 2022, a compression the "
        "sector has only partly recovered. Third, the payer shift: Medicare "
        "Advantage keeps taking share from traditional Medicare, and its "
        "prior-auth, denial, and observation-downgrade apparatus erodes the "
        "cross-subsidy that keeps thin-margin hospitals solvent. Against that, "
        "sponsor capital learned a hard lesson from Steward — hospital real "
        "estate is a liability to underwrite, not a lever to pull — and has "
        "migrated to the surrounding ecosystem (RCM, staffing, hospital-at-"
        "home) rather than the acute operating company."),
    growth_levers=[
        GrowthLever(
            "Aging population and acuity growth",
            "The 65+ cohort drives admissions, procedural volume, and case-mix "
            "intensity — structural, demographic demand.",
            "+2-3%/yr utilization", "GOV"),
        GrowthLever(
            "IPPS / OPPS market-basket rate updates",
            "The per-discharge and per-encounter administered rates step up with "
            "the annual Final Rules and wage index.",
            "+2.5-3.5%/yr rate", "GOV"),
        GrowthLever(
            "Commercial-rate negotiation (the cross-subsidy escalator)",
            "Negotiated multiples of Medicare are the real revenue lever — where "
            "local market power exists, commercial rates rise faster than costs.",
            "mix- and market-dependent", "ILLUSTRATIVE"),
        GrowthLever(
            "Outpatient / ambulatory build-out",
            "Shifting volume into HOPD, ASC, and clinic settings grows the "
            "outpatient book — though site-neutral policy caps the premium.",
            "revenue-mix shift", "ILLUSTRATIVE"),
        GrowthLever(
            "Labor cost inflation (a negative lever)",
            "Nursing wages and agency staffing outran rate updates after 2021, "
            "converting revenue growth into margin loss.",
            "margin drag", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Population aging × acuity (admissions and procedural intensity)",
        analysis=(
            "The dominant demand driver is demographic: as the 65+ population "
            "grows, so do admissions, surgical volume, and case-mix intensity — "
            "older patients are admitted more often and at higher acuity. That "
            "makes aggregate hospital demand predictable and non-discretionary "
            "for the acute core (emergencies, complex surgery, ICU). Two forces "
            "redirect rather than reduce it: the outpatient migration moves "
            "lower-acuity volume out of the inpatient bed to HOPD, ASC, and "
            "home settings, and Medicare Advantage utilization management "
            "compresses admissions and length of stay at the margin. So the "
            "curve is 'more demand, less of it inpatient' — the total need "
            "rises while the inpatient asset base captures a shrinking share of it."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Clinical labor (nurses, techs, employed physicians, agency)",
            "~50-58% of cost",
            "The dominant and increasingly variable cost; the post-2021 wage and "
            "agency-staffing surge is the proximate cause of margin compression.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Supplies, devices, and drugs",
            "~15-20% of cost",
            "Implants, pharmaceuticals, and med-surg supplies; inflation-exposed, "
            "and where 340B economics (for eligible hospitals) show up.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Facilities, plant, and capital (or rent)",
            "~8-12% of cost",
            "Depreciation and interest on plant — or, in a sale-leaseback, fixed "
            "rent that can overwhelm a thin operating margin (the Steward failure).",
            "ILLUSTRATIVE"),
        CostDriver(
            "Purchased services & IT (incl. RCM)",
            "~8-12% of cost",
            "Outsourced clinical and back-office services, EHR, and revenue-cycle "
            "operations — the ecosystem sponsors actually invest in.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Administration, compliance & bad debt",
            "~8-12% of cost",
            "Corporate overhead, regulatory/compliance load, and the rising "
            "uncompensated-care and denials-management burden.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=None,
    cms_trend=None,
)

register(REPORT)
