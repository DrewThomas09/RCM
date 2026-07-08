"""Locum Staffing — locum tenens (temporary physician & APP) staffing.

Deals-only market-report module (a services vertical with no CMS facility file,
so no computed state_breakdown or supply trend; the sector's corpus deal history
is thin offline, so ``live_figures`` may be empty — the report leans on the
qualitative deep sections). The qualitative sections are authored around the two
facts that define locum economics: it is a two-sided marketplace where the
SCARCE side is clinician supply (a warm bench of credentialed, redeployable
providers is the real asset, not client demand), and the gross margin is a
cyclical bill-rate/pay-rate SPREAD — locum tenens is structurally steadier than
the travel-nurse boom-bust because the physician shortage is secular, not
pandemic-driven. The Medicare Q6 substitute-billing rule is the regulatory
feature that makes short-term physician coverage clean for the client.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="locum_staffing",
    name="Locum Staffing",
    care_setting="Other services",
    naics="561320",
    one_line_def=(
        "Locum tenens staffing — the temporary placement of physicians and "
        "advanced-practice providers (NP/PA/CRNA) into hospitals, groups, and "
        "government facilities to fill coverage gaps (vacancies, leaves, "
        "seasonal ramp, new service lines). The agency recruits and credentials "
        "the clinician, bills the facility a bill rate, pays the clinician a "
        "pay rate, and keeps the spread while carrying malpractice, travel, and "
        "licensing."),
    tam_headline=TamHeadline(
        value=8.5, unit="$B", growth_pct=6.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US locum tenens (physician + APP) staffing revenue, the "
            "~$8-9B physician/APP slice within a ~$70B total US healthcare "
            "staffing market (Staffing Industry Analysts). Growth is the "
            "modeled composite — a secular physician-shortage tailwind (AAMC "
            "projects a shortfall of up to ~86K physicians by 2036) net of "
            "post-COVID rate normalization; steadier than travel nursing, whose "
            "pandemic spike and bust are a separate, more volatile market."),
    ),
    executive_summary=[
        "It is a two-sided marketplace where SUPPLY is the scarce side. The "
        "real asset is a warm bench of credentialed, redeployable clinicians "
        "and the relationships that keep them coming back — not client demand, "
        "which the physician shortage guarantees. The winner owns clinician "
        "supply.",
        "Gross margin is a bill-rate/pay-rate SPREAD (~20-35% for locums), and "
        "it is cyclical. The COVID travel-nurse spike showed how fast bill "
        "rates inflate and then collapse — but locum tenens is structurally "
        "steadier because the physician shortage is secular, not pandemic-"
        "driven. Do not underwrite a locums platform on travel-nurse comps.",
        "Credentialing cycle time is the hidden throughput constraint: a placed "
        "provider earns nothing until credentialed and privileged. The "
        "Interstate Medical Licensure Compact and digital credentialing are the "
        "productivity frontier that turns bench into billable days faster.",
        "The Medicare Q6 'locum tenens' rule lets a substitute physician bill "
        "under the regular physician's NPI for up to 60 continuous days — a "
        "regulatory feature that makes short-term physician coverage clean for "
        "the client, and part of why the model exists.",
        "The structural tail risk is 1099 worker classification. Locums are "
        "typically independent contractors; an AB5-style reclassification would "
        "blow up the contractor economics, malpractice structure, and tax "
        "treatment the model rests on.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Clinician sourcing & recruiting — building the supply-side bench by "
            "specialty (the scarce, value-defining side)",
            "Credentialing & licensing — privileging, primary-source "
            "verification, and multi-state licensure (IMLC) — the throughput "
            "gate",
            "Client demand & matching — filling facility vacancies, leaves, "
            "seasonal ramp, and new service lines",
            "Assignment logistics — travel, housing, scheduling, and onboarding "
            "the provider at the site",
            "Malpractice & risk — occurrence/claims-made coverage and tail for "
            "the placed clinician",
            "Billing & redeployment — invoicing the facility on the spread and "
            "re-placing the provider to maximize utilization",
        ],
        sites_of_care=[
            "Hospitals & health systems (hospitalist, ED, surgery, radiology)",
            "Physician groups & clinics (primary care, specialty coverage)",
            "Government — VA, IHS, DoD, and correctional facilities",
            "Rural & critical-access hospitals (structurally supply-short)",
            "Telehealth locums (psychiatry, teleradiology, telestroke)",
        ],
        money_flow=(
            "The agency is paid by the FACILITY client, not by a payer. It bills "
            "a bill rate for each day/hour the clinician works and pays the "
            "clinician a pay rate; the difference — the spread — is the gross "
            "margin (roughly 20-35% for locum tenens). The bill rate has to "
            "cover the clinician's pay plus malpractice insurance, travel and "
            "housing, credentialing and licensing, and the agency's recruiting "
            "and operating overhead. Some demand flows through a Managed "
            "Services Provider (MSP) or Vendor Management System (VMS) that "
            "aggregates a client's contingent-labor spend and takes a fee. "
            "Direct-hire/permanent placement is priced as a one-time fee "
            "(commonly ~20-30% of first-year compensation). Underneath, the "
            "Medicare Q6/fee-for-time rules let the substitute physician's "
            "services be billed under the regular physician's NPI for up to 60 "
            "continuous days, which is what makes short-term physician coverage "
            "economically clean for the client."),
        key_players=(
            "Locum tenens leaders: CHG Healthcare (CompHealth, Weatherby, "
            "Locumsmart), AMN Healthcare (Staff Care; Merritt Hawkins on the "
            "permanent side), LocumTenens.com (Jackson Healthcare), Cross "
            "Country Healthcare, Hayes Locums, and Medical Solutions. The "
            "adjacent travel-nurse and allied market — AMN, Aya Healthcare, "
            "Cross Country, Ingenovis — is larger but far more cyclical. The "
            "acquirable pool is the fragmented long tail of specialty-focused "
            "and regional locum agencies under the scaled platforms."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US locum tenens (physician + APP) staffing revenue",
                    "~$8-9B (modeled)",
                    "INDUSTRY · Staffing Industry Analysts (physician/APP slice)"),
            Segment("Total US healthcare staffing market (all segments)",
                    "~$70B",
                    "INDUSTRY · Staffing Industry Analysts total-market size"),
            Segment("Physician shortage (the demand base)",
                    "up to ~86K physician shortfall by 2036",
                    "INDUSTRY · AAMC physician-workforce projections"),
            Segment("Travel nursing (adjacent, more cyclical)",
                    "COVID spike then sharp normalization",
                    "INDUSTRY · SIA travel-nurse market reads"),
        ],
        growth_drivers=[
            "Physician & APP shortage — aging workforce, retirements, burnout, "
            "and rural/underserved gaps (the secular demand engine)",
            "Coverage needs — vacancies, leaves, seasonal ramp, new service "
            "lines, and EHR go-live backfill",
            "Clinician flexibility shift — more providers choosing 1099 locum "
            "work over employment",
            "Telehealth locums — psychiatry, teleradiology, and telestroke "
            "expand placeable supply and demand",
            "IMLC & digital credentialing — faster multi-state licensing lifts "
            "billable throughput per provider",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Hospitals & health systems": 0.45,
            "Physician groups & clinics": 0.20,
            "Government (VA / IHS / DoD / correctional)": 0.15,
            "Community health / rural & critical-access": 0.12,
            "Telehealth / other": 0.08,
        },
        rate_mechanics=[
            "Bill rate / pay rate spread — the agency bills the facility and "
            "pays the clinician; the spread (~20-35% for locums) is the gross "
            "margin. (Shares above are ILLUSTRATIVE revenue-by-client-segment — "
            "who funds the agency — not an insurance payer mix; the agency "
            "bills no payer.)",
            "Bill rate must cover pay + malpractice + travel/housing + "
            "credentialing + agency overhead — the true cost stack behind the "
            "spread.",
            "MSP / VMS — a managed-services or vendor-management layer aggregates "
            "a client's contingent-labor spend and takes a percentage fee.",
            "Direct-hire / permanent placement — a one-time fee, commonly "
            "~20-30% of first-year compensation.",
            "Medicare Q6 / fee-for-time (reciprocal & locum tenens billing) — "
            "the substitute physician bills under the regular physician's NPI "
            "for up to 60 continuous days; the rule that makes short-term "
            "coverage clean.",
            "Worker classification (1099 vs. W-2) sits under the whole model — "
            "reclassification would change the cost stack and malpractice/tax "
            "structure.",
        ],
        reimbursement_risk=(
            "The revenue risk is spread-cyclicality and supply, not payer rate. "
            "The bill-rate/pay-rate spread inflates when clinician supply is "
            "tight and compresses when it loosens — the travel-nurse market's "
            "COVID spike and 2023-24 collapse is the vivid warning, though locum "
            "tenens is structurally steadier because the physician shortage is "
            "secular. Supply is the binding constraint: the agency cannot bill "
            "what it cannot staff, and credentialing cycle time delays revenue "
            "on every placement. The structural tail risk is worker "
            "reclassification — an AB5-style ruling that recasts 1099 locums as "
            "employees would upend the contractor economics, malpractice "
            "structure, and tax treatment. Client DSO (facilities pay slowly) "
            "and malpractice-cost inflation round out the pressure points."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Q6 / fee-for-time compensation (locum tenens billing)",
                 "Lets a substitute physician's services be billed under the "
                 "regular physician's NPI for up to 60 continuous days — the "
                 "billing feature that makes short-term coverage clean.",
                 "https://www.cms.gov/regulations-and-guidance/guidance/manuals/downloads/clm104c01.pdf"),
            Rule("State medical licensure + Interstate Medical Licensure "
                 "Compact (IMLC)",
                 "Licensure is per-state; the IMLC speeds multi-state licensing "
                 "for eligible physicians — a core operational and throughput "
                 "lever.",
                 "https://www.imlcc.org/"),
            Rule("Credentialing & privileging (Joint Commission / NCQA / CMS)",
                 "Facility credentialing and privileging gate when a placed "
                 "clinician can work — the hidden throughput constraint on "
                 "billable days.",
                 "https://www.jointcommission.org/"),
            Rule("Worker classification (IRS / DOL; CA AB5 & state ABC tests)",
                 "Whether locums are 1099 contractors or employees is the "
                 "structural risk to the model's cost, malpractice, and tax "
                 "economics.",
                 "https://www.dol.gov/agencies/whd/flsa/misclassification"),
            Rule("Malpractice coverage (occurrence vs. claims-made + tail)",
                 "The agency typically carries malpractice for placed "
                 "clinicians; coverage form and tail are a real cost and "
                 "liability consideration.",
                 None),
        ],
        policy_watch=[
            "Worker-classification rulemaking and state ABC-test expansion",
            "IMLC state adoption and APP/nurse licensure-compact expansion",
            "Medicare Q6 substitute-billing policy and any duration changes",
            "Bill-rate normalization post-COVID and MSP/VMS margin pressure",
            "Telehealth cross-state practice and payment-parity rules",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Barbell: a handful of scaled national platforms (CHG, AMN, Jackson/"
            "LocumTenens.com, Cross Country) plus a long tail of specialty-"
            "focused and regional locum agencies. Structure is defined by "
            "specialty supply and client relationships, not geography — and no "
            "facility file exists for a services vertical, so geography is "
            "honestly omitted; the (thin) corpus deal history stands in its "
            "place below."),
        hhi_or_share=(
            "Moderately concentrated at the top of locum tenens specifically, "
            "but 'share' is really share of scarce clinician supply by "
            "specialty. The specialty and regional agency tail is the roll-up "
            "pool."),
        consolidation=(
            "Active PE and strategic roll-up. CHG Healthcare (Leonard Green, "
            "Ares, GIC) is the scaled locum leader; AMN and Cross Country are "
            "public; Jackson Healthcare and Aya are large privately held "
            "platforms; Medical Solutions (Centerbridge/CDPQ) and Ingenovis "
            "(Cornell/Trilantic) consolidated travel and allied. The COVID "
            "travel-nurse boom pulled in capital and then a sharp normalization "
            "reset valuations — locum tenens weathered it better than travel "
            "nursing."),
        pe_activity=(
            "Sponsors like the asset-light, cash-generative marketplace model "
            "and the secular physician-shortage tailwind. The value-creation "
            "levers are: own clinician supply (recruiting engine + redeployment), "
            "compress credentialing cycle time with technology/IMLC, raise "
            "recruiter productivity, and layer an MSP/VMS platform. The caution "
            "is cyclicality — the travel-nurse spike-and-bust is the reminder "
            "not to over-lever a spread that can compress, and to separate the "
            "steadier locum book from volatile travel-nurse comps."),
        notable_players=[
            "CHG Healthcare (CompHealth / Weatherby)", "AMN Healthcare",
            "LocumTenens.com (Jackson Healthcare)", "Cross Country Healthcare",
            "Hayes Locums", "Medical Solutions", "Aya Healthcare (travel)",
            "Ingenovis Health",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Gross margin / spread (bill − pay)", "~20-35% locums",
                "The core economic — cyclical with clinician supply; steadier "
                "for physicians than for travel nurses."),
            Kpi("Provider utilization / days on assignment", "the throughput",
                "Billable days per clinician on the bench — redeployment and "
                "credentialing speed drive it."),
            Kpi("Credentialing cycle time", "the hidden constraint",
                "Days from match to billable — a placed provider earns nothing "
                "until credentialed and privileged."),
            Kpi("Recruiter productivity (placements/recruiter)", "the SG&A lever",
                "Recruiting is the real fixed cost; productivity per recruiter "
                "sets operating leverage."),
            Kpi("Fill rate / time-to-fill", "supply-driven",
                "Share of client orders filled and how fast — a function of "
                "bench depth by specialty."),
            Kpi("Agency EBITDA margin", "~8-18%",
                "Below the gross spread after recruiting, credentialing, "
                "malpractice, and G&A (ILLUSTRATIVE ranges)."),
        ],
        margin_profile=(
            "Locum staffing margin is a spread business run over a recruiting "
            "cost base. Gross margin is the bill-rate/pay-rate spread, which "
            "widens when clinician supply is tight and compresses when it "
            "loosens; operating margin is what survives after the real fixed "
            "cost — recruiting and sales labor — plus credentialing, "
            "malpractice, and travel/housing. The economic levers are therefore "
            "supply-side: a deep, loyal, redeployable clinician bench keeps "
            "utilization and fill rates high, and faster credentialing (IMLC, "
            "digital verification) converts bench to billable days sooner. "
            "Recruiter productivity and a technology/VMS layer are how a "
            "fundamentally labor-brokerage business earns operating leverage — "
            "without them the multiple compresses to 'bodies and phones' "
            "(ILLUSTRATIVE ranges)."),
    ),
    risks=[
        Risk("Bill-rate spread cyclicality", "High",
             "The gross spread inflates and compresses with clinician supply — "
             "the travel-nurse spike-and-bust is the warning; locums are "
             "steadier but not immune."),
        Risk("Clinician supply scarcity", "High",
             "The agency cannot bill what it cannot staff — a thin or "
             "disloyal bench caps fill rate and revenue."),
        Risk("1099 worker reclassification", "High",
             "An AB5-style ruling recasting locums as employees would upend the "
             "contractor cost, malpractice, and tax structure the model rests "
             "on."),
        Risk("Credentialing throughput drag", "Medium",
             "Slow credentialing/privileging delays revenue on every placement "
             "and caps how fast the bench turns billable."),
        Risk("Client concentration & DSO", "Medium",
             "Reliance on a few health-system or government clients, and slow "
             "facility payment, pressure working capital."),
        Risk("Malpractice-cost inflation", "Medium",
             "Rising liability coverage costs on placed clinicians eat into the "
             "spread."),
    ],
    diligence_questions=[
        "What is the gross spread by specialty and its trend through the "
        "post-COVID normalization — and how much is travel-nurse versus locum?",
        "How deep and loyal is the clinician bench by specialty, and what is "
        "the provider redeployment/retention rate?",
        "What is the credentialing cycle time, and how much does IMLC/digital "
        "credentialing shorten time-to-bill?",
        "What is recruiter productivity and the trend in placements per "
        "recruiter (the operating-leverage lever)?",
        "What is the exposure to 1099 worker-classification risk, and how is "
        "malpractice structured?",
        "What is client and specialty concentration, and how much revenue is "
        "government (VA/IHS/DoD) versus commercial?",
        "What is DSO and working-capital intensity given facility payment "
        "cycles?",
        "What technology/VMS layer differentiates the platform from "
        "commoditized body-shop staffing?",
    ],
    insider_lens=[
        "Supply is the scarce side of this marketplace. Client demand is "
        "guaranteed by the physician shortage; what wins is owning clinician "
        "supply — a deep, loyal, redeployable bench and the recruiters who keep "
        "it warm. The asset is the provider relationships, not the client list.",
        "Do not underwrite a locums platform on travel-nurse comps. The "
        "travel-nurse spike-and-bust was a pandemic phenomenon; locum tenens "
        "rides a secular physician shortage and is structurally steadier. "
        "Separate the two books before you believe the growth or the multiple.",
        "Credentialing is the hidden meter. A matched provider earns nothing "
        "until credentialed and privileged, so credentialing cycle time is real "
        "revenue — the IMLC and digital verification are the productivity "
        "frontier that turns bench into billable days.",
        "The Medicare Q6 rule is why short-term physician coverage is clean: a "
        "substitute can bill under the regular physician's NPI for up to 60 "
        "days. It is a regulatory feature the model depends on — and a policy "
        "line worth watching.",
        "The existential wildcard is worker classification. The whole cost, "
        "malpractice, and tax structure assumes 1099 contractors; an AB5-style "
        "reclassification would rewrite the economics overnight — model it as a "
        "tail, not a footnote.",
    ],
    connections=default_connections(
        "locum_staffing",
        deals_sector="staffing",
        extra_pages=[
            ("/diligence/tam-sam?template=locum_staffing",
             "Locum Staffing deep-dive — sizing build + deal history"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI Registry — the clinician supply universe by specialty/taxonomy"),
            ("hrsa_data_hpsa_primary_care",
             "HRSA — primary-care Health Professional Shortage Areas (the "
             "demand map)"),
            ("hrsa_data_hpsa_mental_health",
             "HRSA — mental-health HPSAs (psychiatry, a top locum specialty)"),
            ("bls_qcew_industry_area",
             "BLS QCEW — temporary help services (NAICS 561320) employment & "
             "wages (the staffing labor market)"),
        ],
    ),
    sources=[
        Source("Staffing Industry Analysts (SIA) — US healthcare staffing and "
               "locum tenens market sizing", "INDUSTRY",
               "https://www.staffingindustry.com/"),
        Source("AAMC — The Complexities of Physician Supply and Demand "
               "(workforce projections)", "INDUSTRY",
               "https://www.aamc.org/data-reports/workforce/report/physician-workforce-projections"),
        Source("CMS Medicare Claims Processing Manual — Q6 / fee-for-time "
               "(locum tenens & reciprocal billing)", "GOV",
               "https://www.cms.gov/regulations-and-guidance/guidance/manuals/downloads/clm104c01.pdf"),
        Source("Interstate Medical Licensure Compact Commission (IMLCC)",
               "GOV", "https://www.imlcc.org/"),
        Source("US DOL — worker misclassification / independent-contractor "
               "guidance", "GOV",
               "https://www.dol.gov/agencies/whd/flsa/misclassification"),
        Source("PE Desk industry deep-dive (staffing / locum tenens) + deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=locum_staffing"),
    ],
    live_figures=live_figures_from_dive("locum_staffing"),
    trends=(
        "Locum staffing runs on a secular tailwind with a cyclical margin. The "
        "tailwind is the physician and APP shortage — an aging workforce, "
        "retirements, burnout, and persistent rural and psychiatric gaps that "
        "AAMC projects widening for another decade — which guarantees client "
        "demand and pushes more coverage onto temporary providers. The cyclical "
        "part is the spread: the COVID travel-nurse boom sent bill rates and "
        "staffing revenue to records in 2021-22 and then normalized sharply in "
        "2023-24, hitting the public staffing names. Locum tenens weathered "
        "that better because physician coverage demand is structural rather "
        "than pandemic-driven, and the diligence lesson is to separate the "
        "steadier locum book from volatile travel-nurse comps. The operational "
        "frontier is supply and speed: owning clinician relationships, "
        "compressing credentialing cycle time with the Interstate Medical "
        "Licensure Compact and digital verification, lifting recruiter "
        "productivity, and layering MSP/VMS technology to earn operating "
        "leverage on a fundamentally labor-brokerage business. The policy "
        "wildcard is worker classification — the 1099 structure the model rests "
        "on."),
    growth_levers=[
        GrowthLever(
            "Physician & APP shortage (secular demand)",
            "Aging workforce, retirements, burnout, and rural/psychiatric gaps "
            "push coverage onto temporary providers — the primary engine.",
            "primary", "ACADEMIC"),
        GrowthLever(
            "Coverage & flexibility shift",
            "Vacancies, leaves, seasonal ramp, and more clinicians choosing "
            "1099 flexibility expand both demand and placeable supply.",
            "+ supply/demand", "ILLUSTRATIVE"),
        GrowthLever(
            "Telehealth locums",
            "Psychiatry, teleradiology, and telestroke widen the placeable "
            "supply pool and open cross-state coverage.",
            "+ new supply", "ILLUSTRATIVE"),
        GrowthLever(
            "IMLC & digital credentialing",
            "Faster multi-state licensing and privileging convert bench to "
            "billable days sooner — throughput and margin.",
            "throughput", "ILLUSTRATIVE"),
        GrowthLever(
            "MSP/VMS aggregation & roll-up",
            "Managed-services layers capture more of client contingent-labor "
            "spend; acquiring specialty/regional agencies adds supply.",
            "consolidation", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Physician/APP shortage × credentialed, redeployable supply",
        analysis=(
            "Demand is anchored by a structural workforce gap: AAMC projects a "
            "US physician shortfall of up to roughly 86,000 by 2036, "
            "concentrated in primary care, psychiatry, and the hospital-based "
            "specialties, and worst in rural and critical-access settings. That "
            "shortage — aging physicians, retirements, and burnout — makes "
            "temporary coverage a permanent operating need, not a stopgap, so "
            "the demand side is close to guaranteed. The binding driver of "
            "realized volume is therefore supply, not demand: revenue is the "
            "product of how many credentialed clinicians the agency can field "
            "and how many billable days each works. The levers that actually "
            "move volume are supply-side — recruiting depth by specialty, "
            "provider redeployment and loyalty, and credentialing cycle time "
            "(shortened by the IMLC and digital verification). Telehealth "
            "widens the placeable pool further. Growth accrues to whoever owns "
            "the scarce clinicians and turns them billable fastest."),
        basis="ACADEMIC"),
    cost_drivers=[
        CostDriver(
            "Clinician pay (pass-through)",
            "the largest gross cost",
            "The pay rate paid to the placed provider — a pass-through under "
            "the bill rate; the spread over it is the gross margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Recruiting & sales labor",
            "the real fixed cost / SG&A",
            "The recruiting engine that builds and keeps the clinician bench — "
            "the operating-leverage driver, measured as placements per "
            "recruiter.", "ILLUSTRATIVE"),
        CostDriver(
            "Malpractice insurance",
            "spread-eroding",
            "Coverage (occurrence/claims-made + tail) the agency carries for "
            "placed clinicians — a real, inflation-exposed cost against the "
            "spread.", "ILLUSTRATIVE"),
        CostDriver(
            "Credentialing, licensing & travel/housing",
            "assignment cost",
            "Primary-source verification, multi-state licensing (eased by IMLC), "
            "and the travel and housing that bring a provider on-site.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Technology / VMS platform & marketing",
            "leverage & lead-gen",
            "The VMS/matching platform and clinician-supply marketing that "
            "differentiate a scaled agency from commoditized body-shop staffing.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=None,
    cms_trend=None,
)

register(REPORT)
