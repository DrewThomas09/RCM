"""RCM Services — outsourced & technology-enabled revenue-cycle management.

Deals-only market-report module (RCM is a B2B services vertical with no CMS
facility file, so no computed state_breakdown or supply trend). Live SOURCED
figures wire from ``rcm_services_deep_dive()`` — the sector's own realized-deal
corpus (health-IT / revenue-cycle trade history). The qualitative sections are
authored around the two facts that define RCM economics: the vendor is paid by
the PROVIDER (contingency % of collections, PEPM, or per-claim — never by
payers), and the whole margin engine is labor arbitrage (offshore back office)
being converted to software (autonomous coding / denials AI) faster than wages
rise, while rising payer friction (denials, downcoding, MA prior-auth) is the
secular demand tailwind.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="rcm_services",
    name="RCM Services",
    care_setting="Other services",
    one_line_def=(
        "Outsourced and technology-enabled revenue-cycle management — the "
        "business of getting healthcare providers paid, end to end: patient "
        "access and eligibility, coding and charge capture, claim submission "
        "and scrubbing, denials management and AR follow-up, and patient "
        "billing and collections. Sold as full end-to-end BPO, modular point "
        "solutions, or software-plus-services, and paid by the provider client "
        "(contingency %, PEPM, or per-claim) rather than by a payer."),
    tam_headline=TamHeadline(
        value=140.0, unit="$B", growth_pct=10.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled total US provider revenue-cycle operating spend (~3-4% "
            "cost-to-collect on national provider net revenue — HFMA MAP "
            "benchmark applied to the CMS NHE provider base). The addressable "
            "prize is the OUTSOURCED + tech-enabled vendor-served slice (a "
            "fraction of the total in-house spend), which industry analysts "
            "size at ~$20-30B and growing ~10-11%/yr. Growth is the modeled "
            "composite of outsourcing penetration + rising payer friction + "
            "automation-driven share gain."),
    ),
    executive_summary=[
        "The vendor is paid by the provider, not the payer. Contingency (a "
        "percent of net collections, typically ~3-9% by scope and specialty) "
        "aligns the vendor to cash; per-claim, PEPM, and FTE/cost-plus models "
        "cover the rest. There is no insurance payer mix on the vendor's own "
        "P&L — the 'client end-market' below is who funds the spend.",
        "Offshore labor arbitrage IS the margin. India/Philippines back-office "
        "delivery (GeBBS, AGS, Access, Omega, Sagility) is the gross-margin "
        "engine; the current thesis is converting that labor to software — "
        "autonomous coding and denials AI — faster than offshore wages inflate "
        "and attrition bites.",
        "Denials are the growth engine because payers keep denying more. MA "
        "prior-auth, downcoding, and payer 'no' rates rise every year, so the "
        "work-per-claim — and the value of denials/AR specialists — rises with "
        "payer friction. RCM is countercyclical to payer behavior.",
        "It is the stickiest services vertical there is: once a vendor runs the "
        "whole revenue cycle, you cannot rip out the thing that collects your "
        "cash. But the transition IN is the risk window — a botched go-live "
        "tanks the client's cash and triggers churn or clawbacks.",
        "One of the most PE-rolled-up sectors in healthcare — R1 RCM taken "
        "private (~$8.9B, TowerBrook + CD&R, 2024), Waystar's 2024 IPO, "
        "Ensemble, FinThrive, GeBBS/AGS under EQT. Diligence centers on the "
        "TRUE automation rate and the aged-AR behavior, not the AI deck.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Patient access — scheduling, registration, eligibility & benefits, "
            "prior authorization, point-of-service estimation & collection",
            "Mid-cycle — clinical documentation integrity (CDI), medical "
            "coding (HCC / DRG / CPT), charge capture, chargemaster (CDM)",
            "Claim production — scrubbing/edits, clearinghouse submission, "
            "electronic remittance (ERA) posting",
            "Denials & AR — denial work/appeals, underpayment recovery, aged-AR "
            "follow-up, secondary/tertiary billing",
            "Patient financial services — statements, self-pay collections, "
            "financial assistance (501(r)), bad-debt placement",
            "Analytics & reporting — KPI dashboards, payer scorecards, and the "
            "contingency-fee reconciliation back to the client",
        ],
        sites_of_care=[
            "Hospital & health-system revenue cycle (end-to-end BPO)",
            "Physician & medical-group billing (contingency % of collections)",
            "Specialty & ambulatory (labs, imaging, ASC, DME, ED groups)",
            "Onshore command centers + offshore delivery (India / Philippines)",
            "Embedded RCM inside a practice-management platform (e.g. athena)",
        ],
        money_flow=(
            "The RCM vendor is paid by the PROVIDER, not by any payer. The "
            "dominant model is contingency — a percent of net collections "
            "(roughly 3-9% depending on scope, specialty, and volume; physician "
            "practices sit higher, huge hospital books lower on volume) — which "
            "aligns the vendor to cash actually recovered. Alternatives are "
            "per-transaction/per-claim fees, per-encounter or PEPM (common for "
            "tech-enabled and software), and FTE-based cost-plus (the classic "
            "offshore arbitrage structure). Underneath, the vendor operates "
            "against the provider's real reimbursement — MPFS/RVUs on the "
            "professional side, OPPS/DRG on the facility side, and negotiated "
            "commercial and Medicare Advantage contracts — so denials, "
            "downcoding, and prior-auth on THAT reimbursement are what the "
            "vendor gets paid to fix. Gross margin is set by the onshore/offshore "
            "labor mix and, increasingly, by how much of the work is automated."),
        key_players=(
            "Scaled end-to-end operators: R1 RCM (TowerBrook + CD&R), Ensemble "
            "Health Partners (Berkshire/Warburg), Conifer Health (Tenet), "
            "Savista (New Mountain). Technology-led: Waystar, FinThrive, "
            "Experian Health, availity (clearinghouse/eligibility), and "
            "athenahealth's embedded physician RCM. Offshore-heavy delivery and "
            "coding: Access Healthcare, GeBBS (EQT), AGS Health (EQT), Omega "
            "Healthcare, Sagility. Denials specialists: Aspirion, Cloudmed "
            "(inside R1), Med-Metrix. The acquirable pool is the enormous long "
            "tail of regional billing companies and specialty-specific vendors "
            "under the scaled platforms."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Total US provider RCM operating spend (in-house + vendor)",
                    "~$140B (modeled)",
                    "ILLUSTRATIVE · ~3-4% cost-to-collect × CMS NHE provider base"),
            Segment("Outsourced end-to-end RCM BPO (vendor-served)",
                    "~$20-30B, growing double-digit",
                    "INDUSTRY · RCM analyst market sizing (Everest/Black Book)"),
            Segment("RCM technology / software (clearinghouse, denials, pt-pay)",
                    "a separate, fast-growing slice",
                    "INDUSTRY · health-IT analyst sizing"),
            Segment("Administrative transaction volume & savings opportunity",
                    "billions of eligibility/claim/PA transactions/yr",
                    "GOV/INDUSTRY · CAQH Index (electronic-transaction adoption)"),
        ],
        growth_drivers=[
            "Outsourcing penetration — in-house revenue cycle shifting to "
            "specialist vendors as provider margins compress (~primary lever)",
            "Rising payer friction — denials, downcoding, MA prior-auth raise "
            "work-per-claim and the value of AR/denials work",
            "Labor-to-automation conversion — autonomous coding + denials AI "
            "expand margin and win share",
            "Patient-responsibility shift — high-deductible plans grow the "
            "self-pay estimation and collections book",
            "M&A land-and-expand — cross-sell modules across an installed base",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Hospitals & health systems": 0.45,
            "Physician & medical groups": 0.30,
            "Specialty & ambulatory (lab/imaging/ASC/DME)": 0.15,
            "Payers / risk-bearing / other": 0.10,
        },
        rate_mechanics=[
            "Contingency — a percent of net collections (~3-9% by scope & "
            "specialty); the dominant, cash-aligned model and the one to "
            "diligence for cherry-picking. (Shares above are ILLUSTRATIVE "
            "revenue-by-client-segment — who funds the vendor — not an "
            "insurance payer mix; the vendor bills no payer.)",
            "Per-transaction / per-claim / per-statement fees — volume-priced, "
            "common for clearinghouse and modular work.",
            "PEPM / per-encounter — recurring subscription pricing typical of "
            "tech-enabled and software offerings.",
            "FTE / cost-plus — the classic offshore labor-arbitrage structure "
            "(price = loaded offshore FTE cost + margin).",
            "The underlying claim reimbursement the vendor operates against — "
            "MPFS/RVUs (professional), OPPS & MS-DRG (facility), and negotiated "
            "commercial/MA rates — is what denials, downcoding, and prior-auth "
            "attach to; the vendor monetizes fixing that friction.",
            "CAQH Index quantifies the per-transaction cost and the savings of "
            "moving eligibility/claims/prior-auth fully electronic — the "
            "efficiency the automation thesis is chasing.",
        ],
        reimbursement_risk=(
            "The vendor's revenue risk is client-side and behavioral, not payer "
            "reimbursement. First, contingency incentive risk: a percent-of-"
            "collections vendor can flatter its own fee by working the easy, "
            "high-yield AR and letting hard or aged claims age out — diligence "
            "the aged-AR (>90 day) trend and small-balance write-off behavior, "
            "not just the headline net-collection rate. Second, transition and "
            "churn risk: RCM is sticky once embedded, but a botched go-live "
            "(staff transition, system cutover) craters the client's cash, and "
            "a J-curve on every new logo means concentrated implementation risk. "
            "Third, the offshore arbitrage is exposed to wage inflation, "
            "attrition, and rupee/peso FX — the automation roadmap is the hedge. "
            "Compliance risk is real where the vendor touches coding (False "
            "Claims Act / upcoding exposure under RAC/TPE audits)."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("HIPAA Privacy & Security Rules (Business Associate liability)",
                 "RCM vendors handle PHI as Business Associates — BAAs, breach "
                 "notification, and OCR enforcement are the core regulatory "
                 "frame; a breach is an existential event.",
                 "https://www.hhs.gov/hipaa/for-professionals/security/index.html"),
            Rule("No Surprises Act — good-faith estimates & patient billing",
                 "Changed front-end estimation, uninsured/self-pay good-faith "
                 "estimates, and out-of-network patient-responsibility workflows "
                 "the RCM vendor runs.",
                 "https://www.cms.gov/nosurprises"),
            Rule("Hospital Price Transparency + Transparency in Coverage",
                 "Machine-readable files and shoppable-service estimates feed "
                 "the patient-estimation and self-pay tooling that is a growing "
                 "RCM module.",
                 "https://www.cms.gov/hospital-price-transparency"),
            Rule("CFPB medical-debt credit-reporting rule + state medical-debt "
                 "laws",
                 "Removing medical debt from credit reports and state limits on "
                 "collection actions weaken the leverage behind patient "
                 "collections — a direct headwind to the self-pay book.",
                 "https://www.consumerfinance.gov/"),
            Rule("False Claims Act + IRS §501(r) financial-assistance rules",
                 "Coding vendors carry FCA/upcoding exposure under RAC/TPE "
                 "audits; 501(r) governs the nonprofit-hospital collections "
                 "workflow (financial assistance before extraordinary actions).",
                 "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        ],
        policy_watch=[
            "CFPB medical-debt rule status and state medical-debt legislation",
            "Payer prior-auth automation mandates (CMS interoperability rule)",
            "AI-in-coding / autonomous-coding oversight and audit expectations",
            "HIPAA Security Rule strengthening (post-Change Healthcare)",
            "No Surprises Act IDR and estimation-workflow changes",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Barbell structure: a handful of scaled end-to-end platforms and "
            "clearinghouses at the top, and a very long tail of regional "
            "billing companies and specialty-specific vendors (a radiology "
            "biller, an ED coder, an anesthesia RCM shop) below. There is no "
            "national facility file for a services vertical, so geography is "
            "honestly omitted; the corpus deal history stands in its place "
            "below."),
        hhi_or_share=(
            "Concentrated at the platform/clearinghouse layer (R1, Waystar, "
            "FinThrive, availity, Ensemble) but atomized across the specialty "
            "and regional billing long tail — the acquirable roll-up pool."),
        consolidation=(
            "One of the most PE-rolled-up sectors in healthcare. R1 RCM was "
            "taken private in 2024 (~$8.9B, TowerBrook + CD&R) after absorbing "
            "Cloudmed and Acclara; Waystar IPO'd in 2024 (EQT/Bain/CPPIB); "
            "Ensemble (Berkshire/Warburg), FinThrive (Clearlake), Savista (New "
            "Mountain), and the offshore platforms GeBBS and AGS Health (both "
            "EQT) all changed hands. Multiples for tech-enabled/software RCM run "
            "well above pure-services BPO."),
        pe_activity=(
            "Sponsors love the recurring, sticky, mission-critical cash-flow "
            "profile plus a fragmented roll-up runway and an automation "
            "margin-expansion story. The value-creation playbook is: buy a "
            "services book, industrialize offshore delivery, layer software/AI "
            "to convert labor to automation, and cross-sell modules across the "
            "base. Diligence has shifted from pure logo growth to the TRUE "
            "automation rate, net revenue retention, and implementation risk."),
        notable_players=[
            "R1 RCM (TowerBrook + CD&R)", "Ensemble Health Partners",
            "Conifer Health (Tenet)", "Savista", "Waystar", "FinThrive",
            "Access Healthcare", "GeBBS (EQT)", "AGS Health (EQT)",
            "Omega Healthcare", "Sagility", "athenahealth (embedded)",
            "Aspirion (denials)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Cost-to-collect (client benchmark)", "~2-4% of net rev",
                "The headline value proposition — best-practice pushes toward "
                "~2.5-3%; the vendor sells the delta versus in-house."),
            Kpi("Net collection rate", "~95-99% of collectible",
                "How much of the legitimately collectible revenue is captured — "
                "the client's core outcome measure."),
            Kpi("Clean-claim / first-pass rate", "~90-98%",
                "Share of claims accepted on first submission — the leading "
                "indicator of downstream denials and rework."),
            Kpi("Initial denial rate", "~5-15%",
                "Rising with payer friction; the denials/AR book grows as this "
                "climbs — the demand engine."),
            Kpi("Days in AR (DSO)", "~35-55 days",
                "Cash-velocity measure; a transition dip here is the classic "
                "botched-go-live signal."),
            Kpi("Vendor EBITDA margin", "BPO ~15-25% / tech ~25-40%",
                "Offshore-heavy services sit higher within BPO; software and "
                "tech-enabled command a premium (ILLUSTRATIVE ranges)."),
        ],
        margin_profile=(
            "RCM vendor margin is labor-mix × automation × retention. Gross "
            "margin is set by how much delivery sits offshore and how much of "
            "the work is automated (autonomous coding, RPA on eligibility/status "
            "checks, denials prediction); the frontier winners convert labor to "
            "software faster than offshore wages rise. Operating margin then "
            "turns on net revenue retention and implementation efficiency — a "
            "sticky enterprise book with 100-115% NRR and clean go-lives "
            "compounds, while a churny SMB book with J-curve losses on every new "
            "logo does not. Software/tech-enabled models carry structurally "
            "higher margins than pure-services BPO (ILLUSTRATIVE)."),
    ),
    risks=[
        Risk("Contingency cherry-picking / aged-AR neglect", "High",
             "Percent-of-collections incentives can flatter the fee while hard "
             "and aged claims age out — the number to audit is the aged-AR "
             "trend, not the headline collection rate."),
        Risk("Implementation / go-live transition failure", "High",
             "A botched staff or system cutover craters the client's cash and "
             "drives churn or clawbacks — concentrated risk on every new logo."),
        Risk("Offshore wage inflation, attrition & FX", "Medium",
             "The arbitrage that IS the margin erodes as India/Philippines wages "
             "and turnover rise; the automation roadmap is the hedge."),
        Risk("Automation over-promise vs. true automation rate", "Medium",
             "'Autonomous coding' is high for simple specialties but "
             "human-in-the-loop for complex inpatient DRG — diligence the real "
             "rate, not the deck."),
        Risk("HIPAA breach / cybersecurity", "High",
             "As a PHI-handling Business Associate a breach is an existential, "
             "reputational, and regulatory event (the Change Healthcare attack "
             "is the cautionary tale)."),
        Risk("Coding / False Claims Act compliance", "Medium",
             "Coding and CDI vendors carry upcoding/FCA exposure under RAC/TPE "
             "audits — a liability that travels with the service."),
        Risk("Patient-collections regulation (CFPB / state medical debt)",
             "Medium",
             "Rules removing medical debt from credit and limiting collection "
             "actions weaken the self-pay book's leverage."),
    ],
    diligence_questions=[
        "What is the pricing-model mix (contingency % vs. PEPM vs. per-claim vs. "
        "FTE), and how does contingency behavior look on aged and small-balance "
        "AR?",
        "What is the TRUE automation rate by function and specialty (autonomous "
        "coding %, RPA coverage), not the marketed rate?",
        "What is net revenue retention, gross retention, and the churn/clawback "
        "history — and what drives churn (price, service, transition)?",
        "What is the onshore/offshore delivery mix, and how exposed is gross "
        "margin to offshore wage inflation and attrition?",
        "What is the implementation track record — go-live cash dips, timelines, "
        "and any client-cash disruptions or disputes?",
        "What is the client-segment and specialty concentration, and how much "
        "revenue sits in the top handful of logos?",
        "What is the HIPAA/security posture (SOC 2 / HITRUST), breach history, "
        "and Business Associate exposure?",
        "Where the vendor touches coding/CDI, what is the FCA/upcoding audit "
        "history and reserve?",
    ],
    insider_lens=[
        "Contingency aligns the vendor to cash — but a clever vendor works the "
        "easy, high-yield AR and lets the hard and aged claims age out, juicing "
        "its own fee while the client's aged-AR quietly rots. Read the aged-AR "
        "curve and the small-balance write-off behavior before you believe the "
        "collection rate.",
        "Offshore labor arbitrage is the whole margin, and it is a melting ice "
        "cube: India/Philippines wages and attrition rise every year. The "
        "winners convert labor to software (autonomous coding, denials AI) "
        "faster than wages climb; the losers are just a cheaper call center.",
        "The business is stickier than almost anything in healthcare services — "
        "you cannot rip out the thing that collects your cash — but the "
        "transition IN is where contracts die. A botched go-live tanks the "
        "client's cash flow and turns a 10-year annuity into a lawsuit.",
        "Denials are the growth engine, and payers keep feeding it. Every year "
        "of more prior-auth, more downcoding, and more MA 'no' raises the "
        "work-per-claim and the value of AR/denials specialists — RCM is long "
        "payer friction.",
        "'Autonomous coding' is real for radiology, path, and EM and mostly a "
        "slide for complex inpatient DRG. The diligence number is the true "
        "human-in-the-loop rate by specialty, because that — not the AI "
        "narrative — is what actually sets gross margin.",
    ],
    connections=default_connections(
        "rcm_services",
        deals_sector="rcm",
        extra_pages=[
            ("/diligence/tam-sam?template=rcm_services",
             "RCM Services deep-dive — sizing build + realized-deal history"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI Registry — the provider client universe by taxonomy/specialty"),
            ("cms_open_data_mup_physician_by_provider_service",
             "CMS Medicare Physician & Other Practitioners — the claim/billing "
             "base RCM operates on"),
            ("cms_open_data_catalog",
             "CMS Open Data — utilization, denials, and program context"),
            ("bls_qcew_industry_area",
             "BLS QCEW — business-support / data-processing employment & wages "
             "(the RCM labor-cost base)"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded entities (billing/FCA compliance screen)"),
        ],
    ),
    sources=[
        Source("HFMA — MAP Keys / cost-to-collect and revenue-cycle "
               "benchmarks", "INDUSTRY", "https://www.hfma.org/"),
        Source("CAQH Index — cost & volume of administrative transactions and "
               "the electronic-adoption savings opportunity", "INDUSTRY",
               "https://www.caqh.org/insights/caqh-index"),
        Source("CMS National Health Expenditure Accounts — provider revenue "
               "base for the cost-to-collect model", "GOV",
               "https://www.cms.gov/data-research/statistics-trends-and-reports/national-health-expenditure-data"),
        Source("HHS Office for Civil Rights — HIPAA Privacy & Security Rule "
               "(Business Associate obligations)", "GOV",
               "https://www.hhs.gov/hipaa/for-professionals/index.html"),
        Source("CFPB — medical debt and credit-reporting rulemaking", "GOV",
               "https://www.consumerfinance.gov/"),
        Source("PE Desk industry deep-dive (health-IT / RCM) + realized-deal "
               "corpus", "INTERNAL", "/diligence/tam-sam?template=rcm_services"),
    ],
    live_figures=live_figures_from_dive("rcm_services"),
    trends=(
        "The RCM trajectory is a labor-to-software transition running under a "
        "widening provider-margin squeeze. As hospital and physician margins "
        "compress against flat Medicare updates and post-2021 wage inflation, "
        "providers outsource the revenue cycle to specialists to protect cash — "
        "the secular penetration lever. On the other side, payers keep raising "
        "friction: Medicare Advantage prior-auth, algorithmic downcoding, and "
        "climbing initial-denial rates raise the work-per-claim, which is "
        "revenue for denials and AR specialists. The defining shift is "
        "automation: the offshore arbitrage that built the industry (India and "
        "Philippines back offices) is being converted to software — autonomous "
        "coding, RPA on eligibility and status checks, and denials prediction — "
        "with the frontier winners industrializing faster than offshore wages "
        "and attrition rise. Capital has poured in and consolidated the top: R1 "
        "taken private, Waystar public, the offshore platforms rolled up under "
        "EQT. The durable value has moved toward tech-enabled and software "
        "models with high net revenue retention, and away from pure-headcount "
        "BPO, while the Change Healthcare cyberattack made security and "
        "resilience a board-level line item."),
    growth_levers=[
        GrowthLever(
            "Outsourcing penetration (in-house → vendor)",
            "Compressed provider margins push revenue-cycle operations from "
            "in-house teams to specialist vendors — the primary secular lever.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Rising payer friction (denials / downcoding / prior-auth)",
            "Every year of more payer 'no' raises work-per-claim and the value "
            "of denials and AR work — RCM is long payer friction.",
            "+ demand/claim", "ILLUSTRATIVE"),
        GrowthLever(
            "Labor-to-automation conversion",
            "Autonomous coding, RPA, and denials AI convert offshore labor to "
            "software — margin expansion plus share gain for the automators.",
            "margin-accretive", "ILLUSTRATIVE"),
        GrowthLever(
            "Patient-responsibility shift (high-deductible plans)",
            "Growing self-pay balances expand the estimation and patient-"
            "collections book, a higher-value front-end module.",
            "+ self-pay book", "ILLUSTRATIVE"),
        GrowthLever(
            "M&A land-and-expand + roll-up",
            "Cross-selling modules across an installed base and acquiring the "
            "specialty/regional long tail compounds revenue per client.",
            "roll-up", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Claim/encounter volume × complexity × outsourcing penetration",
        analysis=(
            "Demand compounds three multiplicands. The base is total US "
            "claim/encounter volume, which grows with healthcare utilization "
            "and the aging population — non-discretionary and steady. On top of "
            "that, complexity per claim rises with payer behavior: more prior "
            "authorization, more downcoding, and higher initial-denial rates "
            "mean more touches, appeals, and AR work per encounter — the payer "
            "friction that turns a flat claim count into a growing workload. The "
            "third and largest lever is outsourcing penetration: as provider "
            "margins compress, revenue-cycle operations shift from in-house "
            "teams to vendors, so the vendor-served share of a growing, more "
            "complex claim base expands. The result is a demand curve that "
            "grows faster than underlying utilization — and one that gets a "
            "second wind, not a headwind, when payers tighten."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Delivery labor (onshore + offshore RCM staff)",
            "~50-65% of cost",
            "The dominant cost — coders, AR reps, patient-access and denials "
            "staff. Offshore mix is the gross-margin lever; automation is the "
            "structural attack on this line.", "ILLUSTRATIVE"),
        CostDriver(
            "Technology & platform",
            "~10-20% of cost",
            "Clearinghouse, RPA, coding/CDI engines, analytics, and cloud — the "
            "capex/opex behind the labor-to-software conversion.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Implementation, transition & client management",
            "~10-15% of cost",
            "Go-live staffing, system cutover, and account management — the "
            "J-curve cost on every new logo and the churn-defense spend.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Compliance & security (HIPAA, SOC 2 / HITRUST, audit)",
            "~5-10% of cost",
            "PHI-handling Business Associate obligations, security attestations, "
            "and coding-audit defense — a rising, non-negotiable line.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Sales, marketing & G&A",
            "~10-15% of cost",
            "Enterprise sales cycles are long and consultative; SG&A leverage "
            "improves as the installed base and cross-sell mature.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=None,
    cms_trend=None,
)

register(REPORT)
