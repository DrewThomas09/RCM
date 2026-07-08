"""Inpatient Rehab (IRF) — intensive post-acute rehabilitation hospitals & units.

Rich-data flagship: consumes ``irf_deep_dive()`` (CMS Inpatient Rehabilitation
Facility Compare, ~1.2K facilities) for SOURCED live figures. The qualitative
sections are authored around the two rules that define the sector — the 60%
Rule that gates IRF classification and the 3-hour therapy-intensity standard —
plus the conspicuously high Medicare margin that keeps site-neutral reform in
view.
"""
from __future__ import annotations

from .. import (
    CmsTrend, Competition, Connection, CostDriver, GrowthLever, HowItWorks,
    Kpi, MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule,
    Segment, Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="irf",
    name="Inpatient Rehab (IRF)",
    care_setting="Post-acute",
    naics="622310",
    one_line_def=(
        "Hospital-level intensive rehabilitation for patients recovering from "
        "stroke, brain and spinal-cord injury, major trauma, amputation, and "
        "similar conditions — free-standing rehab hospitals and acute-hospital "
        "rehab units, paid a Medicare per-discharge case-mix rate and gated by "
        "the 60% Rule and the 3-hour therapy standard."),
    tam_headline=TamHeadline(
        value=8.5, unit="$B", growth_pct=3.5, basis_label="GOV",
        basis_note=(
            "Medicare FFS IRF spending ~$8.5B across ~380K stays (MedPAC); "
            "total IRF revenue including MA and commercial is larger. Growth is "
            "the modeled composite of the TAM/SAM drivers (demand +3.0%, rate "
            "+2.5%, MA/SNF substitution −1.5%)."),
    ),
    executive_summary=[
        "Two rules define the business. The 60% Rule requires that at least 60% "
        "of an IRF's admissions carry one of 13 qualifying conditions to be paid "
        "as an IRF, and the 3-hour rule requires patients to need and tolerate "
        "~3 hours of therapy a day — so admissions are a compliance-driven case-"
        "mix problem, not just a clinical one.",
        "Medicare pays per discharge, not per diem, on a case-mix (CMG) basis — "
        "and the Medicare margin is among the highest in all of post-acute "
        "(MedPAC has flagged low-to-mid double digits), which is precisely why "
        "site-neutral payment reform between IRF and SNF is a standing threat.",
        "The near-term volume risk is Medicare Advantage steering: MA plans "
        "prefer to route rehab-eligible patients to lower-cost SNFs, so as MA "
        "penetration rises, IRF referral volume for the marginal patient is "
        "under pressure.",
        "Unlike the frozen SNF stock, IRF supply is still being built — the "
        "recent certification cohort is heavy, the fingerprint of de novo and "
        "health-system-JV expansion led by the national rehab operators.",
        "The sector is concentrated by post-acute standards: Encompass Health "
        "dominates free-standing IRFs, Select Medical runs rehab hospitals "
        "largely through health-system JVs, and the balance is hospital-based "
        "units — the acquirable independent pool is comparatively thin.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Acute hospitalization (stroke, trauma, SCI, major surgery)",
            "Pre-admission screening — is the patient IRF-appropriate?",
            "IRF admission + IRF-PAI assessment → CMG case-mix classification",
            "Interdisciplinary rehab: ~3 hrs/day therapy, rehab-physician led",
            "Individualized plan of care toward a community-discharge goal",
            "Discharge to community (the quality measure) or to a lower setting",
            "Billing — Medicare IRF PPS per-discharge, MA/commercial per case",
            "Quality reporting — IRF QRP + discharge-to-community rate",
        ],
        sites_of_care=[
            "Free-standing inpatient rehabilitation hospital (the growth base)",
            "Acute-hospital rehabilitation unit (a distinct-part IRF unit)",
            "Health-system JV rehab hospital (operator + hospital partner)",
            "Specialty rehab (brain injury, spinal cord, pediatric) programs",
        ],
        money_flow=(
            "Medicare pays a single prospective amount per discharge under the "
            "IRF PPS, set by the patient's Case-Mix Group (from the IRF-PAI "
            "assessment) with comorbidity tiers, then adjusted for length-of-"
            "stay outliers and facility factors (wage index, rural, low-income, "
            "teaching). Because payment is per discharge and the cost base "
            "(therapists, rehab physicians, rehab nursing, the building) is "
            "largely fixed, margin is a function of case mix, length of stay "
            "management, and throughput. Medicare Advantage and commercial "
            "payers pay negotiated per-case or per-diem amounts, usually with "
            "authorization and often steering the patient toward a cheaper SNF "
            "alternative. The 60% Rule sits on top of all of it: the facility "
            "must keep its qualifying-condition mix above the threshold to be "
            "paid as an IRF at all."),
        key_players=(
            "Encompass Health is the clear national leader in free-standing "
            "IRFs, a public company with well over 150 rehab hospitals. Select "
            "Medical operates rehabilitation hospitals largely through joint "
            "ventures with health systems (and specialty brands like Kessler). "
            "ScionHealth (the former Kindred hospital business) and a long tail "
            "of hospital-based rehab units hold the rest. The growth model is de "
            "novo development and health-system JV, not roll-up of independents "
            "— which is why the acquirable independent pool is thin relative to "
            "other post-acute verticals."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicare FFS IRF program spend",
                    "~$8.5B",
                    "GOV · MedPAC (Medicare FFS IRF)"),
            Segment("Annual Medicare IRF stays",
                    "~380,000 stays",
                    "GOV · MedPAC IRF chapter"),
            Segment("Medicare share of IRF payer mix",
                    "~60%+ (FFS + MA)",
                    "GOV · MedPAC / CMS IRF utilization"),
            Segment("Certified IRFs (US)",
                    "~1,200 facilities",
                    "SOURCED · CMS IRF Compare (our file)"),
            Segment("Free-standing vs hospital-unit split",
                    "roughly half free-standing, half units",
                    "GOV · CMS IRF provider file"),
        ],
        growth_drivers=[
            "Aging + stroke/neuro incidence ~3.0%/yr — the clinical demand base",
            "IRF PPS annual rate updates ~2.5%/yr (market basket + wage index)",
            "MA/SNF substitution −1.5%/yr — plans steer marginal patients to SNF",
            "De novo + health-system JV expansion — a live supply-add lever",
            "Site-neutral reform risk — a standing negative on the rate outlook",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare FFS": 0.58,
            "Medicare Advantage": 0.14,
            "Commercial": 0.18,
            "Medicaid / other": 0.10,
        },
        rate_mechanics=[
            "IRF Prospective Payment System — a per-discharge payment set by "
            "the Case-Mix Group (CMG) from the IRF-PAI, with comorbidity tiers, "
            "short-stay/outlier adjustments, and facility factors (wage index, "
            "rural, low-income percentage, teaching).",
            "The 60% Rule (compliance threshold) — at least 60% of admissions "
            "must have one of 13 qualifying conditions for the facility to be "
            "classified and paid as an IRF; it governs the entire admissions mix.",
            "The 3-hour therapy-intensity standard plus coverage requirements — "
            "rehab-physician oversight, pre-admission screening, an interdisci-"
            "plinary team, and an individualized plan of care gate payment.",
            "IRF PPS annual update — market basket + productivity + wage index.",
            "IRF Quality Reporting Program — a 2% payment penalty for non-"
            "reporting; discharge-to-community and functional-outcome measures.",
            "Medicare Advantage / commercial — negotiated per-case or per-diem "
            "with authorization and site-of-care steering toward SNF.",
        ],
        reimbursement_risk=(
            "The structural risk is site-neutral payment reform. IRF Medicare "
            "margins are conspicuously high and much of the historical joint-"
            "replacement volume already migrated to SNFs after earlier "
            "tightening; MedPAC and CMS continue to study paying IRF and SNF "
            "more similarly for overlapping conditions, which would compress the "
            "sector's premium. The near-term risk is Medicare Advantage: plans "
            "authorize the cheaper SNF alternative, pay IRF a sub-FFS negotiated "
            "rate, and pressure length of stay. And the perennial audit risk is "
            "medical necessity — RAC/UPIC reviews challenging whether admitted "
            "patients were truly IRF-appropriate rather than SNF-appropriate, "
            "with recoupment on denied stays."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("IRF Prospective Payment System (SSA §1886(j))",
                 "Sets the per-discharge case-mix rate — the price of every "
                 "Medicare stay and the annual rate lever.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/inpatient-rehabilitation-facility"),
            Rule("The 60% Rule / IRF classification (42 CFR 412.29)",
                 "Requires ≥60% of admissions to carry one of 13 qualifying "
                 "conditions — the single rule that dictates the admissions "
                 "strategy and the classification that unlocks IRF payment.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-412"),
            Rule("IRF coverage requirements — 3-hour rule & documentation",
                 "Intensity-of-therapy, rehab-physician oversight, pre-admission "
                 "screening, and plan-of-care rules that drive medical-necessity "
                 "audits and denials.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/inpatient-rehabilitation-facility"),
            Rule("Site-neutral payment (policy)",
                 "The standing proposal to pay IRF and SNF more similarly for "
                 "overlapping conditions — the biggest long-run threat to the "
                 "IRF rate premium.",
                 "https://www.medpac.gov/"),
            Rule("IRF Quality Reporting Program (IRF QRP)",
                 "Functional-outcome and discharge-to-community reporting; a 2% "
                 "penalty for non-compliance gates the full update.",
                 "https://www.cms.gov/medicare/quality/inpatient-rehabilitation-facility"),
        ],
        policy_watch=[
            "Site-neutral IRF/SNF payment proposals and MedPAC recommendations",
            "MA site-of-care steering and prior-authorization rules",
            "RAC/UPIC medical-necessity audit intensity on IRF admissions",
            "60%-Rule qualifying-condition list revisions",
            "IRF PPS market-basket and outlier-threshold changes",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "More concentrated than most of post-acute: roughly 1,200 IRFs, but "
            "a single operator (Encompass Health) leads the free-standing "
            "segment, Select Medical runs rehab hospitals largely via JV, and "
            "the balance is hospital-based units. The for-profit share our file "
            "measures below is lower than SNF because so many IRFs are non-"
            "profit hospital units."),
        hhi_or_share=(
            "Encompass Health is the clear free-standing leader; the CMS file "
            "carries ownership TYPE but no operator name, so operator HHI is "
            "honestly omitted — but the sector is materially less fragmented "
            "than SNF or home health."),
        consolidation=(
            "Growth is de novo development and health-system joint venture, not "
            "roll-up of independents. Encompass builds and JVs; Select expands "
            "through system partnerships; ScionHealth carries the former Kindred "
            "footprint. There is comparatively little independent whitespace to "
            "acquire, so the platform question is development capacity and JV "
            "pipeline rather than tuck-in sourcing."),
        pe_activity=(
            "The platform layer is largely public (Encompass) or "
            "sponsor-adjacent through Select Medical's history and the "
            "TPG/Welsh Carson-era Kindred lineage now in ScionHealth. Sponsor "
            "angles are health-system JV development, specialty-rehab niches, "
            "and real-estate structures rather than classic buy-and-build — the "
            "60% Rule and the concentrated operator layer limit fragmentation "
            "plays."),
        notable_players=[
            "Encompass Health", "Select Medical (rehab hospitals)",
            "ScionHealth", "Kessler Institute (Select JV)",
            "Shirley Ryan AbilityLab", "Health-system rehab units",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Average length of stay (ALOS)", "~12-14 days",
                "The per-discharge model rewards efficient LOS management "
                "against a fixed daily cost of therapy and nursing."),
            Kpi("Case-mix index (CMG)", "facility-specific",
                "Higher-acuity case mix earns more per discharge but must stay "
                "inside the 60%-Rule qualifying-condition envelope."),
            Kpi("60%-Rule compliance margin", "≥60% qualifying",
                "The classification gate — how much headroom the admissions mix "
                "carries above the threshold is a core operating constraint."),
            Kpi("Discharge-to-community rate", "risk-standardized",
                "The headline quality measure (IRF QRP) — it drives referrer "
                "and payer confidence and is public on Care Compare."),
            Kpi("Occupancy", "~65-80%",
                "Fixed-cost leverage rewards fill, but the 3-hour standard caps "
                "how sick or frail an occupant can be."),
            Kpi("Medicare margin", "low-to-mid double digits",
                "Among the highest in post-acute — the reason site-neutral "
                "reform keeps re-appearing."),
        ],
        margin_profile=(
            "An IRF is a high-fixed-cost hospital: rehab physicians, a large "
            "therapist and rehab-nursing complement, and the building are "
            "largely fixed, so contribution steps up with each appropriately "
            "admitted, efficiently managed discharge. Because Medicare pays per "
            "discharge, the levers are case mix (within the 60%-Rule envelope), "
            "length-of-stay efficiency, and throughput/occupancy. Medicare "
            "margins are structurally strong relative to other post-acute "
            "settings — a well-run IRF earns a healthy operating margin — but "
            "that very strength is the standing invitation to site-neutral "
            "reform, and MA-mix growth dilutes the premium case by case."),
    ),
    risks=[
        Risk("Site-neutral payment reform (IRF vs SNF)", "High",
             "The high Medicare margin is the target; paying IRF closer to SNF "
             "for overlapping conditions would compress the sector's premium."),
        Risk("Medicare Advantage site-of-care steering", "High",
             "MA plans route marginal rehab patients to cheaper SNFs and pay "
             "IRF sub-FFS with authorization — a rising volume and rate drag."),
        Risk("Medical-necessity audits (RAC/UPIC) & 60%-Rule compliance",
             "Medium",
             "Denials challenging whether admissions were IRF-appropriate, and "
             "the classification threshold itself, carry recoupment risk."),
        Risk("Therapist and rehab-nursing labor supply", "Medium",
             "PT/OT/SLP and specialized nursing shortages raise the fixed cost "
             "and cap admissions to the 3-hour standard."),
        Risk("Concentrated operator layer / thin whitespace", "Medium",
             "Encompass/Select dominance and health-system JV control leave "
             "little independent supply to acquire."),
        Risk("Referral dependence on acute hospitals", "Low",
             "Volume flows from acute discharge relationships; disruption to "
             "those channels (or system self-referral into owned SNFs) diverts "
             "cases."),
    ],
    diligence_questions=[
        "What is the 60%-Rule compliance history and headroom by facility, and "
        "how is the qualifying-condition mix managed?",
        "What is the payer mix trend, and how fast is MA displacing FFS on the "
        "marginal admission?",
        "What is the medical-necessity denial and appeal history (RAC/UPIC), "
        "and what reserves are held against recoupment?",
        "What is the case-mix index, ALOS, and discharge-to-community rate "
        "versus peers, and are they durable?",
        "How exposed is the rate outlook to site-neutral reform for the "
        "facility's specific condition mix (e.g. joint replacement, stroke)?",
        "What is the therapist and rehab-nursing staffing model, agency "
        "reliance, and wage trajectory?",
        "For JV facilities, what are the governance, term, and change-of-"
        "control provisions with the health-system partner?",
        "What is the de novo / development pipeline, and what are the ramp "
        "economics and CON exposure by state?",
    ],
    insider_lens=[
        "The 60% Rule runs admissions. Deciding who to admit is a compliance-"
        "driven case-mix problem — the facility must keep qualifying conditions "
        "above 60% or lose IRF classification entirely, so admissions strategy "
        "is a regulatory exercise wearing clinical clothes.",
        "The high Medicare margin is a feature and a liability. IRF is one of "
        "the best-paid post-acute settings, which is exactly why site-neutral "
        "reform keeps coming back — underwrite the premium as at-risk, not as "
        "permanent.",
        "MA is the slow leak. Every point of MA penetration routes another "
        "marginal rehab patient to a SNF instead of an IRF and pays the ones "
        "who do come a sub-FFS rate — the FFS-margin comparables flatter a "
        "future the payer mix is eroding.",
        "The recurring fight is 'IRF-appropriate vs SNF-appropriate.' Medical-"
        "necessity denials turn on whether the admitted patient truly needed "
        "hospital-level rehab; a clean pre-admission-screening and documentation "
        "discipline is worth real money in audit defense.",
        "This is a build story, not a buy story. Unlike SNF, IRF supply is "
        "still expanding through de novo and health-system JV — so the platform "
        "asset is development and partnership capability, and the scarce "
        "independent target trades at a premium.",
    ],
    connections=default_connections(
        "irf",
        deals_sector="post_acute",
        extra_pages=[
            ("/diligence/tam-sam?template=irf",
             "IRF deep-dive — state footprint, ownership, discharge-to-community"),
        ],
        connectors=[
            ("provider_data_irf_general",
             "CMS IRF Compare — facility list & quality measures"),
            ("cms_open_data_mup_inpatient_by_provider",
             "CMS Medicare inpatient utilization by provider"),
            ("provider_data_hospital_general",
             "CMS Hospital General Info — acute referral-source mapping"),
            ("census_acs_cbsa_profile",
             "Census ACS — senior/stroke-risk demography for demand mapping"),
            ("npi_provider",
             "NPI Registry — rehab physicians (PM&R) & facilities"),
        ],
    ),
    sources=[
        Source("MedPAC — Report to Congress, inpatient rehabilitation facility "
               "services chapter (margins, payment adequacy, site-neutral)",
               "GOV", "https://www.medpac.gov/"),
        Source("CMS IRF Prospective Payment System — annual Final Rule (CMG, "
               "market basket, wage index)", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/inpatient-rehabilitation-facility"),
        Source("IRF classification / the 60% Rule (42 CFR 412.29)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-412"),
        Source("CMS IRF Quality Reporting Program — discharge-to-community and "
               "functional-outcome measures", "GOV",
               "https://www.cms.gov/medicare/quality/inpatient-rehabilitation-facility"),
        Source("Encompass Health / Select Medical public filings — the "
               "free-standing IRF operating and JV model", "INDUSTRY",
               "https://investor.encompasshealth.com/"),
        Source("PE Desk industry deep-dive (CMS IRF Compare) + realized-deal "
               "corpus", "INTERNAL", "/diligence/tam-sam?template=irf"),
    ],
    live_figures=live_figures_from_dive("irf"),
    trends=(
        "IRF has been the quiet grower of post-acute. Where SNF supply is frozen "
        "and hospice was rolled up, IRF has kept adding capacity — the recent "
        "certification cohort is heavy, reflecting de novo and health-system-JV "
        "expansion led by Encompass Health and Select Medical. The demand base "
        "is clinical and aging-driven (stroke, neuro, trauma), and Medicare "
        "margins have stayed strong, which is both the attraction and the "
        "vulnerability: the sector's premium is the standing target of site-"
        "neutral reform, and Medicare Advantage is chipping at volume by steering "
        "marginal patients to SNFs and paying sub-FFS. The through-line is a "
        "well-run, concentrated, still-expanding setting whose economics are "
        "excellent today and structurally exposed to a payer that would rather "
        "pay less — so the trajectory question is how durable the premium is "
        "across a hold, not whether demand shows up."),
    growth_levers=[
        GrowthLever(
            "Aging + stroke/neuro/trauma incidence",
            "The core clinical demand base grows with the aging population and "
            "the incidence of the qualifying conditions IRFs treat.",
            "+3.0%/yr demand", "GOV"),
        GrowthLever(
            "IRF PPS annual rate updates",
            "The per-discharge rate steps up with the annual market basket and "
            "wage index.",
            "+2.5%/yr rate", "ILLUSTRATIVE"),
        GrowthLever(
            "De novo + health-system JV expansion",
            "The live supply lever — national operators add rehab hospitals via "
            "development and system partnerships, the sector's main growth "
            "engine.",
            "primary volume add", "ILLUSTRATIVE"),
        GrowthLever(
            "MA / SNF site-of-care substitution",
            "Managed care routes marginal rehab-eligible patients to cheaper "
            "SNFs and pays IRF sub-FFS — a volume and margin drag.",
            "−1.5%/yr", "GOV"),
        GrowthLever(
            "Site-neutral reform risk",
            "The standing proposal to pay IRF closer to SNF for overlapping "
            "conditions caps the long-run rate ceiling.",
            "rate-ceiling risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Qualifying-condition incidence (stroke, neuro, trauma) net of "
               "MA/SNF diversion",
        analysis=(
            "IRF demand is clinically specific: it is driven by the incidence of "
            "the 60%-Rule qualifying conditions — stroke, brain and spinal-cord "
            "injury, major multiple trauma, amputation, hip fracture, and "
            "progressive neurological disease — which rises with the aging "
            "population and is largely non-discretionary once the acute event "
            "occurs. What makes IRF volume different from a pure demographic "
            "curve is the referral decision at acute discharge: for a meaningful "
            "band of patients, a SNF is a clinically defensible cheaper "
            "alternative, and Medicare Advantage explicitly steers those "
            "patients there. So the dominant driver is qualifying-condition "
            "incidence, but the realized volume is that incidence times the "
            "share of eligible patients who are actually routed to an IRF rather "
            "than a SNF — a share the payer is actively trying to shrink."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Therapy labor (PT/OT/SLP)",
            "~30-40% of cost",
            "The 3-hour standard makes therapist staffing the defining cost; "
            "PT/OT/SLP scarcity and wage inflation directly gate admissions.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Rehab nursing",
            "~20-25% of cost",
            "Hospital-level nursing for a medically complex rehab census — a "
            "large, largely fixed labor line.", "ILLUSTRATIVE"),
        CostDriver(
            "Rehab-physician / medical direction",
            "~8-12% of cost",
            "Required physician oversight (PM&R) is a coverage condition and a "
            "fixed professional cost.", "ILLUSTRATIVE"),
        CostDriver(
            "Facility / occupancy (owned or leased)",
            "~10-15% of cost",
            "Hospital-grade real estate; de novo capex and, for JV facilities, "
            "the partner economics shape the fixed base.", "ILLUSTRATIVE"),
        CostDriver(
            "Supplies, ancillary services & G&A",
            "~10-15% of cost",
            "Rehab equipment, diagnostics, and corporate overhead plus the "
            "compliance/QRP apparatus.", "ILLUSTRATIVE"),
    ],
    cms_trend=CmsTrend(
        takeaway=(
            "The IRF certification vintage looks nothing like SNF's frozen "
            "stock: the recent build cohort is the heaviest in the roll, the "
            "fingerprint of a setting that is still expanding through de novo "
            "development and health-system joint ventures. Read the recent "
            "cohorts as the live growth signal — capacity is being added by the "
            "national operators, not just recycled — which is the structural "
            "reason IRF is a build-and-partner story rather than the turnaround-"
            "and-consolidate story SNF has become."),
        chart_kind="bars"),
    state_breakdown=(
        "IRFs cluster in the large Sun Belt and populous states (Texas and "
        "Florida lead the count), with for-profit ownership near 44% nationally "
        "— lower than SNF because so many IRFs are non-profit hospital-based "
        "units — and higher for-profit concentration in states where the "
        "national free-standing operators have built out. The CMS file carries "
        "ownership TYPE but no operator name, so operator concentration "
        "(Encompass/Select leadership) is described qualitatively rather than "
        "computed as an HHI."),
)

register(REPORT)
