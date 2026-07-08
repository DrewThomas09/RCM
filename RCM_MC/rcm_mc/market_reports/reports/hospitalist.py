"""Hospitalist — inpatient hospital-medicine staffing built on the hospital subsidy.

Deals-only deep-dive (no national physician-practice facility file; SHM workforce
data is aggregate-only, so geography is omitted rather than fabricated). Hospital
medicine is the fastest-grown physician specialty in modern US history, and its
defining economic feature is that professional-fee collections do not cover
physician compensation — so almost every hospital-medicine group runs on a
hospital support payment (subsidy/stipend). The qualitative sections are authored
around the E/M encounter payment math, the APP-leverage staffing model, the
subsidy-per-FTE dynamic that IS the business, the two-midnight / observation
status trap, and the IPC upcoding precedent that hangs over coding aggressiveness.
Consumes ``hospitalist_deep_dive()`` for SOURCED corpus deal figures (empty
offline — the authored, basis-labeled segments carry the sizing).
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="hospitalist",
    name="Hospitalist",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician (and advanced-practice) hospital-medicine groups that provide "
        "general medical care to admitted inpatients — rounding, admissions, "
        "co-management, and discharge — paid on the Medicare/commercial E/M "
        "encounter schedule and, because those collections rarely cover the cost "
        "of coverage, backfilled by a hospital support payment (subsidy)."),
    tam_headline=TamHeadline(
        value=18.0, unit="$B", growth_pct=3.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled from the ~40,000-50,000 practicing US physician hospitalists "
            "(Society of Hospital Medicine, directional) plus the advanced-"
            "practice clinicians on their teams, times professional collections "
            "AND the hospital support payment per FTE — not a single published "
            "figure. Growth is the modeled composite of inpatient-demand growth, "
            "co-management/post-acute expansion, and APP leverage, net of MPFS "
            "conversion-factor drag."),
    ),
    executive_summary=[
        "The subsidy IS the business. Inpatient professional-fee collections do "
        "not cover hospitalist compensation, so nearly every group runs on a "
        "hospital support payment — often well into six figures per FTE per year. "
        "The central asset and risk is the portfolio of hospital contracts and "
        "their stipends, not a fee-for-service P&L.",
        "Hospital medicine is a coverage and throughput service, not a volume "
        "business. The hospital buys 24/7 admitting, rounding, and discharge "
        "capacity plus length-of-stay, throughput, and quality performance — so "
        "the group is paid partly on encounters and partly on operational value "
        "the hospital cannot easily measure.",
        "APP leverage is the cost curve. Nurse practitioners and physician "
        "assistants under the 2024 CMS split/shared-visit rules run a growing "
        "share of encounters at a lower cost per visit; the physician-to-APP "
        "ratio and the night/nocturnist model set the economics of a contract.",
        "Payment is per encounter on the physician fee schedule: initial hospital "
        "care, daily subsequent visits, and discharge-day management, coded by "
        "medical decision-making or time since the 2023 E/M overhaul. The unit "
        "prices are modest and the conversion factor is flat-to-declining, which "
        "is exactly why the subsidy exists.",
        "Unlike anesthesia, radiology, and emergency medicine, hospitalists were "
        "largely NOT balance-billing out of network, so the No Surprises Act was "
        "not the repricing event here. The recurring shocks are MPFS cuts, "
        "coding-audit exposure (the IPC precedent), and physician burnout/turnover "
        "in the highest-attrition specialty.",
        "The roll-up is mature and scrutinized. TeamHealth, Sound Physicians, and "
        "SCP Health scaled national platforms; Envision's 2023 bankruptcy and "
        "state PE-transaction-review laws made subsidy durability, labor cost, and "
        "coding compliance the quality-of-earnings core.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Hospital contracts a group to staff inpatient medicine 24/7 "
            "(exclusive or employed)",
            "Admission / H&P — the hospitalist admits or accepts the ED/transfer "
            "patient and sets status (inpatient vs observation)",
            "Daily rounding — subsequent hospital-care encounters, orders, "
            "consults, and co-management with surgeons/specialists",
            "APP + physician team model — NP/PA see a share of encounters under "
            "split/shared or supervision rules",
            "Care coordination + throughput — length-of-stay management, "
            "discharge planning, and post-acute placement",
            "Discharge-day management + medication reconciliation + the "
            "transition-of-care handoff",
            "Charge capture / coding (MDM or time based) + billing at the "
            "Medicare CF or commercial rate, plus the hospital stipend true-up",
        ],
        sites_of_care=[
            "Acute-care hospital medical floors (the core — the admitting service)",
            "ICU / step-down co-management (with intensivists where present)",
            "Surgical co-management (ortho, neuro, general surgery comanagement)",
            "Observation units (status-sensitive, two-midnight-rule exposed)",
            "Post-acute 'SNFist' coverage (skilled-nursing hospital-medicine)",
            "Nocturnist / cross-cover and telehospitalist night coverage",
        ],
        money_flow=(
            "A hospitalist bills the physician fee schedule per encounter: an "
            "initial hospital-care code on admission (99221-99223), a subsequent "
            "hospital-care code for each rounding day (99231-99233), and a "
            "discharge-day-management code (99238-99239), with observation and "
            "critical-care codes where they apply. Since the 2023 E/M overhaul, "
            "level is chosen by medical decision-making or total time rather than "
            "bullet-point history/exam. The catch is that those collections — "
            "against an inpatient payer mix that is Medicare- and Medicaid-heavy — "
            "do not cover a hospitalist's compensation, so the hospital pays a "
            "support payment (stipend/subsidy) to close the gap and buy the "
            "coverage, length-of-stay, and throughput value it needs. In the PE "
            "structure a management company runs billing, scheduling, and "
            "recruiting across many hospital contracts, so platform value is the "
            "book of contracts, stipends, and labor cost — not any single "
            "hospital's professional revenue. APP leverage (NP/PA under 2024 "
            "split/shared rules) lowers cost per encounter where the model and "
            "state scope-of-practice allow."),
        key_players=(
            "National PE-backed and physician-owned staffers dominate the scaled "
            "tier: Sound Physicians, TeamHealth (Blackstone), SCP Health "
            "(Schumacher), Vituity (physician-owned), and the hospital-medicine "
            "lines inside health systems and the restructured Envision. IPC "
            "Healthcare — 'The Hospitalist Company' — was rolled into TeamHealth "
            "in 2015 and remains the sector's cautionary coding-compliance name. "
            "The counterparties are hospitals and health systems whose support "
            "payments determine group profitability; the acquirable pool is the "
            "independent single-hospital and regional group whose value is a "
            "defensible stipend and low locum reliance."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Practicing US physician hospitalists", "~40,000-50,000",
                    "INDUSTRY · Society of Hospital Medicine (directional)"),
            Segment("APPs (NP/PA) on hospital-medicine teams", "large & rising",
                    "INDUSTRY · SHM State of Hospital Medicine (directional)"),
            Segment("Hospital-medicine groups requiring a support payment",
                    "the large majority",
                    "INDUSTRY · SHM/MGMA support-payment surveys (directional)"),
            Segment("Median hospital support / FTE hospitalist",
                    "six figures / FTE-yr",
                    "INDUSTRY · SHM/MGMA support-per-FTE surveys (directional)"),
            Segment("Encounters / hospitalist / day (day rounder)", "~15-18",
                    "INDUSTRY · SHM State of Hospital Medicine (directional)"),
        ],
        growth_drivers=[
            "Inpatient medical demand ~2-3%/yr — aging, higher acuity admissions",
            "Co-management expansion (surgical, ortho, neuro, oncology comanage)",
            "Post-acute 'SNFist' and transitional-care line extension",
            "APP leverage lowering cost per encounter (a margin, not volume, "
            "lever)",
            "MPFS conversion-factor drift — a flat-to-declining rate headwind",
            "Hospital financial stress capping subsidy growth — the swing risk",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.55,
            "Medicaid": 0.18,
            "Commercial": 0.22,
            "Self-pay / other": 0.05,
        },
        rate_mechanics=[
            "E/M encounter coding — initial hospital care (99221-223), subsequent "
            "hospital care (99231-233), discharge-day management (99238-239), "
            "plus observation and critical-care codes; leveled by MDM or time "
            "since the 2023 E/M overhaul.",
            "MPFS conversion factor × wRVU — the professional-fee price; the "
            "conversion factor is structurally flat-to-declining with no "
            "inflation update, so productivity coding cannot outrun rate cuts.",
            "2024 split/shared-visit rule — for a physician+APP encounter, the "
            "clinician who performs the 'substantive portion' bills it; this "
            "governs how much of the team's work bills at the physician vs APP "
            "rate and is a direct economic lever.",
            "Two-midnight rule + inpatient-vs-observation status — determines "
            "whether the stay bills Part A inpatient or Part B observation, "
            "driving RAC/UR audit exposure and the hospital's own DRG revenue.",
            "Hospital support payment (stipend) — the negotiated true-up that "
            "closes the gap between the cost of coverage and professional "
            "collections; the single biggest revenue lever for most groups.",
            "Value-based / co-management incentives — length-of-stay, "
            "readmission, throughput, and quality bonuses layered into the "
            "hospital contract on top of encounter billing.",
        ],
        reimbursement_risk=(
            "The dominant risk is subsidy dependence: because professional "
            "collections do not cover physician cost, group profit rests on the "
            "hospital support payment — so an expiring, under-negotiated, or "
            "financially-stressed-hospital stipend is an existential exposure, and "
            "hospital margin pressure directly caps subsidy growth. The second is "
            "the coding line: the IPC Healthcare $60M-class False Claims Act "
            "settlement for systematically billing higher-level E/M codes is the "
            "precedent that hangs over any platform whose margin depends on coding "
            "intensity, and the 2023 MDM/time-based E/M rules changed how level is "
            "justified. Layered on are the flat-to-declining MPFS conversion "
            "factor, the observation-vs-inpatient status audit regime, and a labor "
            "market in the highest-burnout specialty where locum reliance can "
            "swing a contract from profit to loss."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Physician Fee Schedule + E/M inpatient coding (2023 "
                 "overhaul)",
                 "Sets the encounter codes, wRVUs, and conversion factor that "
                 "price hospitalist professional work; the 2023 rules moved "
                 "leveling to medical decision-making or total time.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("2024 split/shared visit rule",
                 "For physician+APP encounters, the clinician doing the "
                 "'substantive portion' bills — governs how much team work bills "
                 "at the physician vs APP rate, the core APP-leverage economics.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Two-midnight rule + inpatient/observation status",
                 "Determines Part A inpatient vs Part B observation status, "
                 "driving RAC/UR audit exposure, patient cost-sharing, and the "
                 "hospital's DRG revenue — the hospitalist sets status.",
                 "https://www.cms.gov/medicare/regulations-guidance/manuals"),
            Rule("False Claims Act — E/M upcoding (IPC Healthcare, 2017 $60M "
                 "settlement)",
                 "The precedent that systematically billing higher-level E/M "
                 "codes is FCA exposure; hangs over any coding-intensity thesis.",
                 "https://www.justice.gov/opa/pr/hospitalist-company-pay-60-million-settle-alleged-false-claims-related-billing"),
            Rule("Anti-Kickback / Stark + fair-market-value on hospital subsidies",
                 "The support payment and any medical-directorship arrangement "
                 "must be commercially reasonable and at FMV — a subsidy that "
                 "looks like a referral inducement is compliance risk.",
                 "https://oig.hhs.gov/compliance/advisory-opinions/"),
            Rule("Corporate practice of medicine + state PE-transaction review",
                 "CPOM doctrine forces the MSO/friendly-PC structure, and a "
                 "growing list of states now review private-equity healthcare "
                 "transactions and physician-employment arrangements.",
                 None),
        ],
        policy_watch=[
            "Annual MPFS conversion-factor cuts and the recurring 'doc fix' fight",
            "Split/shared-visit rule revisions and APP scope-of-practice changes",
            "Two-midnight / observation audit posture and RAC activity",
            "State private-equity healthcare-transaction-review laws expanding",
            "Value-based inpatient models (bundles, TEAM model) shifting risk",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "US hospital medicine spans a large tail of independent "
            "single-hospital and regional groups, a set of scaled national "
            "PE-backed and physician-owned platforms, and a growing share of "
            "hospital-employed programs. The employed-vs-contracted split is the "
            "structural swing: when a hospital insources its hospitalists, a "
            "contract vanishes — so the acquirable pool is the independent group "
            "whose value is a defensible stipend, low locum reliance, and stable "
            "physician retention."),
        hhi_or_share=(
            "No single owner is dominant nationally; concentration is local and "
            "contract-specific. No vendored physician-staffing roll captures "
            "operator concentration, so a national chain HHI is honestly omitted — "
            "the corpus deal history and the NPI/utilization connectors below are "
            "the real read."),
        consolidation=(
            "The 2000s-2010s buildout was one of the great specialty roll-ups: "
            "IPC 'The Hospitalist Company' scaled acquisitively before "
            "TeamHealth absorbed it in 2015, and Sound Physicians, SCP Health, "
            "and Vituity assembled national footprints. The thesis has since "
            "shifted from pure contract accumulation toward operational "
            "efficiency — APP leverage, scheduling and census right-sizing, "
            "coding capture, and subsidy negotiation — as MPFS drift and "
            "hospital margin pressure squeezed the model."),
        pe_activity=(
            "Hospital medicine was among the most PE-active staffing verticals "
            "and is now among the most scrutinized. Envision's 2023 bankruptcy "
            "(leverage plus reimbursement exposure) is the cautionary tale, and "
            "diligence centers on subsidy durability and FMV posture, "
            "APP-leverage labor economics, coding compliance (the IPC precedent), "
            "physician retention/burnout, and antitrust and state "
            "transaction-review risk rather than contract-count growth."),
        notable_players=[
            "Sound Physicians", "TeamHealth (Blackstone)",
            "SCP Health (Schumacher Clinical Partners)", "Vituity "
            "(physician-owned)", "Envision Healthcare (restructured — cautionary "
            "tale)", "IPC Healthcare (absorbed by TeamHealth, 2015)",
            "Society of Hospital Medicine (SHM — the specialty body)",
            "Health-system-employed hospital-medicine programs",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Hospital support / subsidy per FTE", "six figures / FTE-yr",
                "The swing variable — the gap between hospitalist compensation "
                "and professional collections, backfilled by the hospital."),
            Kpi("Encounters / provider / day", "~15-18",
                "The productivity target for a day rounder; too high burns out "
                "physicians and hurts throughput, too low bleeds the contract."),
            Kpi("Physician : APP staffing ratio", "model-dependent",
                "Higher APP leverage lowers cost per encounter where "
                "split/shared rules and state scope-of-practice permit."),
            Kpi("wRVU / encounter and wRVUs / FTE-yr", "~4,000-4,500 wRVU/FTE",
                "The professional-productivity base; coding level and case mix "
                "drive it, but the conversion factor is low so subsidy still "
                "carries the P&L."),
            Kpi("Physician turnover / vacancy rate", "elevated (burnout)",
                "Hospital medicine has among the highest attrition; turnover "
                "forces expensive locum backfill that can flip a contract to a "
                "loss."),
            Kpi("Platform EBITDA margin (post-MSO)", "8-15% (illustrative)",
                "Thin, subsidy- and labor-driven; lower than ancillary-rich "
                "specialties because there is almost no ancillary stack."),
        ],
        margin_profile=(
            "Hospitalist economics are labor against a subsidy: there is almost no "
            "ancillary revenue and almost no capital base — the business is "
            "physician and APP time committed to cover a hospital's inpatient "
            "service 24/7. Contribution is professional collections (modest, on a "
            "Medicare/Medicaid-heavy inpatient payer mix) plus the hospital "
            "support payment, minus a clinician labor cost that is nearly the "
            "entire expense. The two levers are the subsidy (negotiated with the "
            "hospital and increasingly hard to grow as hospital margins compress) "
            "and APP leverage (substituting NP/PA encounters where split/shared "
            "rules allow). Because turnover in the highest-burnout specialty forces "
            "locum backfill at a steep premium, a well-retained, well-scheduled "
            "group at a financially healthy hospital is worth far more than "
            "encounter volume alone implies."),
    ),
    risks=[
        Risk("Hospital subsidy dependence / renegotiation", "High",
             "Professional collections do not cover cost, so profit rests on the "
             "stipend; an expiring, under-negotiated, or stressed-hospital "
             "subsidy is existential."),
        Risk("Physician / APP labor cost, burnout and turnover", "High",
             "The highest-attrition specialty; wage inflation and locum backfill "
             "directly compress a thin, labor-dominated margin."),
        Risk("E/M coding-audit exposure (IPC precedent)", "High",
             "Any margin built on coding intensity carries False Claims Act risk; "
             "the IPC $60M settlement is the standing precedent."),
        Risk("MPFS conversion-factor erosion", "Medium",
             "A structurally low, flat-to-declining unit price with no inflation "
             "update squeezes professional collections year after year."),
        Risk("Hospital insourcing / contract loss", "Medium",
             "A hospital that employs its own hospitalists eliminates a contract "
             "outright — contract concentration is a real exposure."),
        Risk("Antitrust + state PE-transaction-review scrutiny", "Medium",
             "Physician-staffing roll-ups and PE healthcare transactions face "
             "rising FTC and state review."),
    ],
    diligence_questions=[
        "What is the hospital support payment by contract — size, term, renewal "
        "date, FMV support, and the counterparty hospital's financial health?",
        "How concentrated is contract revenue, and what is the insourcing risk at "
        "the top facilities?",
        "What is the physician:APP staffing ratio and split/shared-visit posture "
        "by site, and how much margin depends on APP leverage?",
        "What is the physician turnover / vacancy rate and locum reliance, and "
        "what is the premium-labor cost trend?",
        "What is the coding profile (E/M level distribution vs peers) and the "
        "audit/denial and RAC history — any observation-status exposure?",
        "What are the encounters-per-provider-per-day and wRVU/FTE productivity, "
        "and how do they compare to SHM/MGMA benchmarks?",
        "What value-based / co-management incentives and length-of-stay and "
        "readmission commitments sit in the contracts?",
        "What is the physician-compensation and retention structure post-close, "
        "and how exposed is coverage to key-clinician departure?",
    ],
    insider_lens=[
        "The subsidy is the business. Inpatient professional fees do not cover a "
        "hospitalist's pay, so the hospital support payment is where the profit "
        "lives — underwrite the stipend book like a contract portfolio, because "
        "that is what a hospital-medicine platform actually is.",
        "The hospital is not buying encounters, it is buying throughput. Length "
        "of stay, discharge-before-noon, admission velocity, and readmissions are "
        "what a CFO values — a group that improves the hospital's own DRG "
        "economics can defend a bigger subsidy than one that just rounds.",
        "APP leverage is the whole cost curve, and the 2024 split/shared rule "
        "redrew it. Who performs the 'substantive portion' decides whether a "
        "team's work bills at the physician or APP rate — scope-of-practice and "
        "documentation discipline are economic variables, not clinical trivia.",
        "This is not the No Surprises Act specialty. Hospitalists were largely "
        "in-network and did not monetize out-of-network balance billing, so the "
        "NSA barely touched them — the real shocks are MPFS cuts and coding "
        "audits, not surprise-billing reform.",
        "IPC is the ghost in the coding machine. The Hospitalist Company's $60M "
        "upcoding settlement is why a margin that depends on E/M level intensity "
        "is a diligence red flag — pull the E/M distribution against peers before "
        "believing the professional-fee line.",
        "Burnout is a balance-sheet item. Hospital medicine has the specialty's "
        "highest attrition; every departure forces locum backfill at a premium "
        "that can flip a contract underwater — retention and scheduling quality "
        "are underwriting inputs, not soft factors.",
    ],
    connections=default_connections(
        "hospitalist",
        deals_sector="hospitalist",
        extra_pages=[
            ("/industry/hospitalist",
             "Industry deep-dive — hospital-medicine deal history + subsidy read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — hospitalist (208M00000X) & internal-medicine "
             "specialty supply and enrollment"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — inpatient E/M code volumes, "
             "allowed charges & level mix"),
            ("provider_data_hospital_general",
             "CMS Hospital General Information — the hospital counterparties for "
             "coverage contracts & subsidies"),
            ("open_payments_general_payments_2024",
             "Open Payments — industry payments to hospitalists (relationship "
             "screen)"),
            ("bls_qcew_area_industry",
             "BLS QCEW — physician-office & hospital wage/employment base for "
             "labor-cost mapping"),
            ("census_acs_cbsa_profile",
             "Census ACS — 65+ density for inpatient-demand geography"),
        ],
    ),
    sources=[
        Source("Society of Hospital Medicine (SHM) — State of Hospital Medicine "
               "report (workforce, support-per-FTE, productivity)", "INDUSTRY",
               "https://www.hospitalmedicine.org/"),
        Source("MGMA — physician compensation and hospital-support survey data",
               "INDUSTRY", "https://www.mgma.com/"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (E/M, "
               "split/shared, conversion factor)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("CMS — Two-Midnight Rule and inpatient/observation status "
               "guidance", "GOV",
               "https://www.cms.gov/medicare/regulations-guidance/manuals"),
        Source("U.S. DOJ — IPC Healthcare / IPC The Hospitalist Company $60M "
               "False Claims Act settlement (2017)", "GOV",
               "https://www.justice.gov/opa/pr/hospitalist-company-pay-60-million-settle-alleged-false-claims-related-billing"),
        Source("PE Desk industry deep-dive (hospitalist) + realized-deal corpus",
               "INTERNAL",
               "/diligence/tam-sam?template=hospitalist"),
    ],
    live_figures=live_figures_from_dive("hospitalist"),
    trends=(
        "Hospital medicine went from a named specialty in the mid-1990s to the "
        "largest and fastest-grown physician field in the country in barely two "
        "decades — hospitals discovered that a dedicated inpatient service "
        "improved throughput and length of stay, and staffing companies "
        "industrialized the coverage. The economic truth underneath the growth is "
        "that inpatient professional-fee collections never covered physician "
        "compensation, so the hospital support payment became the load-bearing "
        "revenue line, and the business is best understood as selling coverage, "
        "throughput, and quality to a hospital rather than encounters to a payer. "
        "Consolidation ran hard through the 2010s — IPC's acquisitive rise into "
        "TeamHealth, plus Sound Physicians, SCP Health, and Vituity — and then "
        "the model was reset by three forces: a flat-to-declining MPFS conversion "
        "factor, the IPC upcoding settlement that made coding intensity a "
        "compliance risk, and Envision's 2023 bankruptcy that repriced leverage. "
        "The forward tension is labor and subsidy: physician burnout drives the "
        "specialty's highest attrition, APP leverage under the 2024 split/shared "
        "rule is the main cost lever, and hospital margin pressure caps how far "
        "the subsidy — the thing the whole model runs on — can grow."),
    growth_levers=[
        GrowthLever(
            "Inpatient medical demand (aging × acuity)",
            "An aging population with more comorbid, higher-acuity admissions "
            "expands the inpatient census the hospitalist service must cover.",
            "+2-3%/yr encounters", "ILLUSTRATIVE"),
        GrowthLever(
            "Co-management line extension",
            "Surgical, orthopedic, neuro, and oncology co-management adds "
            "encounters and deepens the hospital relationship beyond the medical "
            "floor.",
            "+ scope", "ILLUSTRATIVE"),
        GrowthLever(
            "Post-acute 'SNFist' and transitional care",
            "Extending the hospital-medicine model into skilled-nursing and "
            "transitional care opens an adjacent, subsidy-light revenue line.",
            "+ adjacency", "ILLUSTRATIVE"),
        GrowthLever(
            "APP leverage (split/shared)",
            "Substituting NP/PA encounters under the 2024 split/shared rule "
            "lowers cost per encounter where scope-of-practice permits — a margin "
            "lever, not a volume lever.",
            "cost lever", "GOV"),
        GrowthLever(
            "Hospital support payment growth",
            "The stipend is a revenue line; where a group demonstrably improves "
            "throughput and quality it can negotiate a larger subsidy — but "
            "hospital margin pressure caps it.",
            "swing variable", "ILLUSTRATIVE"),
        GrowthLever(
            "MPFS conversion-factor drag",
            "A structurally low, flat-to-declining unit price with no inflation "
            "update erodes professional collections and forces subsidy reliance.",
            "primary headwind", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Inpatient medical census (aging × acuity × co-management scope)",
        analysis=(
            "Hospitalist demand is derived from the inpatient medical census: the "
            "number of admitted, higher-acuity, comorbid patients who need daily "
            "medical management. An aging population lifts admission rates and "
            "acuity, and scope expansion — surgical and specialty co-management, "
            "observation coverage, and post-acute 'SNFist' models — adds "
            "encounters beyond the traditional medical floor. But more encounters "
            "are not automatically more profit: because professional collections "
            "sit below the cost of the physician who generates them, incremental "
            "volume only adds margin where the hospital subsidy and APP leverage "
            "make the coverage economic. Two structural offsets bound the volume "
            "story — the long-run push to move care out of the inpatient setting "
            "(observation, hospital-at-home, ambulatory management) can shrink the "
            "medical census even as the population ages, and hospital insourcing "
            "can remove a group's access to that census entirely. The demand base "
            "is reliable; the economics turn on subsidy and labor cost, not "
            "encounter count."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Physician compensation", "~55-65% of cost",
            "The dominant cost line; hospitalist comp plus the productivity and "
            "shift structure sets the base the subsidy must cover.",
            "ILLUSTRATIVE"),
        CostDriver(
            "APP (NP/PA) compensation", "~15-20% of cost",
            "The care-team staff; APP leverage lowers blended cost per encounter, "
            "but APP wage inflation is a direct pressure.", "ILLUSTRATIVE"),
        CostDriver(
            "Locum / premium labor", "cyclical / can spike",
            "Backfilling coverage gaps and turnover with locums carries a steep "
            "premium and is the fastest way a contract goes underwater.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing / RCM + MSO overhead", "~8-12% of cost",
            "E/M coding and billing plus the shared-services, scheduling, and "
            "compliance apparatus across many hospital contracts.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Malpractice + benefits", "~5-10% of cost",
            "Professional liability and clinician benefits on a labor-heavy cost "
            "base.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national physician-staffing facility file is vendored — a "
        "hospital-medicine group is a coverage contract, not a Medicare-certified "
        "facility — and SHM workforce data is aggregate-only, so state geography "
        "is omitted rather than fabricated. The most consequential geographic "
        "variables are the state corporate-practice-of-medicine doctrine "
        "(strong-CPOM states force the friendly-PC/MSO structure), the growing "
        "list of states enacting private-equity healthcare-transaction-review "
        "laws, APP scope-of-practice and independent-practice rules (which set "
        "how far APP leverage can go), and local hospital financial health (which "
        "caps subsidy capacity). The NPI-taxonomy, Medicare physician-utilization, "
        "hospital-general, labor-cost, and 65+-density connectors linked below map "
        "hospitalist supply, inpatient E/M utilization, and the hospital "
        "counterparties that generate coverage contracts — the honest footprint "
        "read in the absence of a facility roll."),
)

register(REPORT)
