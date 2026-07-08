"""Dental / DSO — the consumer-and-commercial dental services roll-up.

Deals-only deep-dive (no CMS dental facility file; dental is largely a
cash-pay-and-commercial market outside Medicare, so no national provider roll is
vendored and geography is omitted rather than fabricated — but the DSO deal
history is real and consumes ``dental_deep_dive()`` for SOURCED corpus figures).
Dental is one of the most mature PE roll-up categories in healthcare: a Dental
Support Organization supplies non-clinical business services to affiliated
practices while the dentist owns the clinical PC under corporate-practice-of-
dentistry law. The qualitative sections are authored around the CDT/PPO fee
mechanics, the structurally-low annual insurance maximum that pushes big cases to
cash, the hygiene-recall flywheel that IS the profit engine, and the pediatric-
Medicaid over-treatment enforcement history (Kool Smiles/Benevis) that is the
sector's reputational third rail.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="dental",
    name="Dental / DSO",
    care_setting="Physician services",
    naics="621210",
    one_line_def=(
        "Outpatient dental care — general/family, pediatric, and specialty "
        "(ortho, oral surgery, endo, perio) — delivered through practices that "
        "increasingly affiliate with a Dental Support Organization (DSO) for "
        "non-clinical business services, paid mostly by commercial dental "
        "insurance and out-of-pocket cash rather than Medicare."),
    tam_headline=TamHeadline(
        value=174.0, unit="$B", growth_pct=3.5, basis_label="GOV",
        basis_note=(
            "US dental-services spending ~$165-175B (CMS National Health "
            "Expenditure Accounts, dental-services line); growth is the modeled "
            "composite of demographic/utilization and price, directional per the "
            "NHE projections — not a single filed forward figure."),
    ),
    executive_summary=[
        "Dental is a consumer-and-commercial market, not a Medicare market. "
        "Payment is CDT-coded off commercial dental PPO fee schedules and "
        "out-of-pocket cash, with Medicaid mainly in pediatrics; traditional "
        "Medicare does not cover routine dental, so the demand is part "
        "insurance-driven and part discretionary.",
        "The DSO is a services layer, not a medical group. Because corporate "
        "practice of dentistry bars non-dentist ownership in most states, the "
        "DSO owns the non-clinical business (billing, HR, procurement, real "
        "estate, marketing, compliance) and the dentist owns the clinical PC — "
        "an MSO/friendly-PC structure. DSO penetration has roughly tripled over a "
        "decade toward a quarter-plus of dentists.",
        "Hygiene is the flywheel. Recurring preventive hygiene recall visits are "
        "the profit engine and the leading indicator: they generate steady "
        "margin themselves and feed the downstream restorative, implant, and "
        "specialty pipeline. New-patient flow and hygiene reappointment rates "
        "predict a practice's trajectory better than a single quarter's revenue.",
        "The annual insurance maximum is a structural feature to underwrite. "
        "Commercial dental plans cap benefits at roughly $1,000-$2,000 a year — a "
        "number largely unchanged for decades — so anything major (implants, "
        "full-mouth, ortho, cosmetics) is effectively cash or patient financing, "
        "which is why case acceptance and in-house financing drive economics.",
        "Consolidation is mature and multiple-sensitive. Heartland, Aspen, "
        "Pacific Dental, Smile Brands, MB2, and dozens of regional platforms have "
        "rolled up a cottage industry; the diligence has shifted from "
        "same-store-count growth to same-store organic growth, dentist "
        "recruiting/retention, and multiple/leverage discipline.",
        "The two concentrated risks are clinical-autonomy litigation and "
        "pediatric-Medicaid over-treatment enforcement. State dental boards and "
        "the Kool Smiles/Benevis precedent make DSO influence over clinical "
        "decisions and Medicaid pediatric volume the sector's legal third rails.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Patient acquisition — marketing, insurance-directory listing, "
            "referrals, and new-patient scheduling",
            "New-patient exam + diagnostic imaging (bitewings/pano/CBCT) + "
            "treatment plan and case presentation",
            "Hygiene recall — recurring prophylaxis/perio-maintenance visits (the "
            "recurring engine and the restorative feeder)",
            "Restorative + operative care — fillings, crowns, root canals, "
            "extractions (the bulk of production)",
            "Specialty care — implants, ortho/clear aligners, oral surgery, "
            "endo, perio (kept in-house to capture the referral)",
            "Insurance verification + CDT coding + claim submission and patient "
            "collections / financing",
            "DSO shared services — procurement, RCM, HR, compliance, and de novo "
            "/ acquisition growth across the platform",
        ],
        sites_of_care=[
            "General / family dental office (the volume base — chairs/operatories)",
            "Pediatric dental office (Medicaid-heavy; EPSDT-driven)",
            "Orthodontic office (largely cash/financed; clear-aligner exposed)",
            "Oral & maxillofacial surgery / implant center (high-value cases)",
            "Endodontic and periodontic specialty offices",
            "DSO-affiliated multi-specialty group practice (one-stop model)",
        ],
        money_flow=(
            "Dental is billed on CDT codes (the ADA's Current Dental Terminology, "
            "not CPT/MPFS) against a commercial dental PPO or indemnity fee "
            "schedule, a discounted DHMO capitation, Medicaid (mainly pediatric "
            "under the EPSDT mandate), or straight cash. Commercial dental plans "
            "carry a low annual maximum — commonly $1,000-$2,000 — that is "
            "largely unchanged for decades, so preventive and small restorative "
            "care runs through insurance while anything major is effectively "
            "out-of-pocket or patient-financed. The practice P&L is a fixed "
            "chair-and-staff chassis: hygienists and assistants run recurring "
            "recall visits (steady margin) that feed a dentist-driven restorative "
            "and specialty pipeline (the high-value production). In the DSO "
            "structure the support organization charges a management fee for "
            "non-clinical services and captures procurement, RCM, and overhead "
            "scale across many offices, while the affiliated dentist owns the "
            "clinical PC — so platform value is same-store organic growth plus "
            "acquisition/de novo, not any one office's collections."),
        key_players=(
            "Scaled DSOs dominate the consolidated tier: Heartland Dental (KKR), "
            "Aspen Dental Management (Leonard Green/Ares), Pacific Dental Services "
            "(physician-owned), Smile Brands, Dental Care Alliance, MB2 Dental "
            "(a doctor-partnership model), Western Dental, North American Dental "
            "Group, and Great Expressions, plus dozens of regional platforms. On "
            "the payer side Delta Dental is the dominant carrier network, with "
            "MetLife, Cigna, Guardian, and UnitedHealthcare; the ADA sets CDT and "
            "practice standards. The acquirable pool is the vast independent "
            "single-doctor and small-group practice base — the cottage industry "
            "the roll-up keeps consolidating."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US dental-services spending", "~$165-175B",
                    "GOV · CMS National Health Expenditure Accounts (dental "
                    "services)"),
            Segment("Out-of-pocket / cash share of dental spend", "~35-40%",
                    "GOV · CMS NHE dental services, payer breakdown (directional)"),
            Segment("Private dental insurance share", "~45-50%",
                    "GOV · CMS NHE dental services, payer breakdown (directional)"),
            Segment("Medicaid / other public share", "~10-15%",
                    "GOV · CMS NHE dental services, payer breakdown (directional)"),
            Segment("DSO-affiliated share of dentists", "~25-30% and rising",
                    "INDUSTRY · ADA Health Policy Institute DSO-affiliation "
                    "estimates (directional)"),
        ],
        growth_drivers=[
            "Population + aging (implants, perio, restorative in older adults)",
            "DSO affiliation growth — independents affiliating for scale & exit",
            "Specialty mix-shift in-house (implants, clear aligners, endo capture)",
            "Discretionary / cosmetic upside (whitening, veneers, aligners)",
            "Medicare Advantage supplemental dental benefit expansion",
            "Consumer-discretionary sensitivity — a recession headwind on "
            "elective care",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial dental (PPO/DHMO/indemnity)": 0.48,
            "Out-of-pocket / cash": 0.37,
            "Medicaid / CHIP (pediatric-heavy)": 0.13,
            "Medicare Advantage / other": 0.02,
        },
        rate_mechanics=[
            "CDT coding on a commercial PPO fee schedule — the ADA's Current "
            "Dental Terminology (not CPT/MPFS); PPO contracts discount off a "
            "usual-customary-reasonable (UCR) rate, and the PPO write-off vs "
            "fee-for-service mix drives realized yield.",
            "Annual benefit maximum (~$1,000-$2,000) — a structurally low, "
            "decades-stale cap that pushes major treatment to cash/financing; the "
            "cap, not medical necessity, often gates when care is done.",
            "DHMO capitation — a per-member fee schedule with copays; lower "
            "reimbursement but predictable volume in some markets.",
            "Medicaid dental (EPSDT) — the pediatric mandate; state-set, "
            "generally low fees, and the segment with the heaviest fraud/over-"
            "treatment enforcement history.",
            "Cash / elective / cosmetic — self-pay implants, ortho, aligners, "
            "whitening, and veneers, plus in-house or third-party patient "
            "financing (CareCredit-style) — the discretionary upside.",
            "DSO management fee — the non-clinical services fee the support "
            "organization charges the affiliated PC; must be structured to "
            "respect corporate-practice-of-dentistry limits.",
        ],
        reimbursement_risk=(
            "Dental's reimbursement risk is unusual because so much of it is "
            "consumer-discretionary rather than fee-schedule: the low, stale "
            "annual insurance maximum means big cases hinge on case acceptance "
            "and patient financing, so a consumer downturn defers elective and "
            "high-value treatment and hits same-store revenue directly. On the "
            "insured side, Delta Dental and the large carriers hold fee-schedule "
            "leverage and PPO write-offs compress realized rates. On the public "
            "side, Medicaid pediatric dental is the enforcement hot zone — the "
            "Kool Smiles/Benevis False Claims Act settlements over medically "
            "unnecessary pediatric procedures are the standing precedent, and any "
            "platform with heavy Medicaid pediatric volume carries over-treatment "
            "and quota-culture scrutiny. Layered on top is corporate-practice-of-"
            "dentistry litigation testing whether the DSO improperly influences "
            "clinical decisions."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Corporate practice of dentistry + DSO/friendly-PC structure",
                 "Most states bar non-dentist ownership of the clinical practice, "
                 "forcing the DSO/MSO-plus-owned-PC structure and constraining "
                 "how far a DSO may influence clinical decisions.",
                 None),
            Rule("State dental board licensure + practice regulation",
                 "State boards license dentists and hygienists, regulate "
                 "advertising and ownership, and enforce the corporate-practice "
                 "line — the primary regulator of the sector.",
                 None),
            Rule("Medicaid EPSDT pediatric dental + False Claims Act "
                 "(Kool Smiles/Benevis precedent)",
                 "The pediatric Medicaid mandate funds the segment, and the "
                 "Benevis/Kool Smiles settlements over medically-unnecessary "
                 "procedures make over-treatment and production quotas FCA risk.",
                 "https://www.justice.gov/opa/pr/dental-management-company-benevis-and-affiliated-kool-smiles-dental-clinics-pay-236-million"),
            Rule("FTC oversight of dental-board self-regulation "
                 "(NC Dental v. FTC, 2015)",
                 "The Supreme Court held a state dental board of practicing "
                 "dentists is not automatically immune from antitrust — limiting "
                 "boards' power to block DSO/non-dentist competition.",
                 "https://www.supremecourt.gov/opinions/14pdf/13-534_19m2.pdf"),
            Rule("Anti-Kickback / Stark on referrals + specialty capture",
                 "In-house specialty referral, ownership arrangements, and any "
                 "government-payer volume implicate AKS/Stark fair-market-value "
                 "and referral rules.",
                 "https://oig.hhs.gov/compliance/advisory-opinions/"),
            Rule("State PE-transaction-review + DSO-disclosure laws",
                 "A growing set of states review private-equity healthcare "
                 "transactions and require DSO registration/ownership disclosure, "
                 "raising the compliance bar on roll-ups.",
                 None),
        ],
        policy_watch=[
            "State PE-transaction-review and DSO-registration/disclosure laws",
            "Medicaid pediatric-dental over-treatment enforcement (post-Benevis)",
            "Corporate-practice-of-dentistry clinical-autonomy litigation",
            "Medicare Advantage supplemental dental benefit scope and rates",
            "Clear-aligner / direct-to-consumer regulation after SmileDirectClub",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Dental remains one of the most fragmented healthcare verticals — a "
            "vast base of independent single-doctor and small-group practices — "
            "even after a decade of aggressive consolidation. DSO affiliation has "
            "climbed toward roughly a quarter-plus of dentists, but the long "
            "independent tail is still the M&A pool, and dentist demographics "
            "(retiring owners, debt-laden new graduates who prefer employment) "
            "keep feeding it."),
        hhi_or_share=(
            "No dominant national owner; the largest DSOs each hold only low-"
            "single-digit shares of US dentists, so national concentration is "
            "low and the structure is fragmentation. No CMS dental facility file "
            "is vendored (dental sits largely outside Medicare), so a computed "
            "chain HHI is honestly omitted — the corpus deal history and ADA HPI "
            "affiliation estimates are the read."),
        consolidation=(
            "Dental is a textbook mature roll-up: Heartland (KKR), Aspen (Leonard "
            "Green/Ares), Pacific Dental, Smile Brands, MB2, and scores of "
            "regional platforms assembled the cottage industry over the 2010s, "
            "and the category has cycled through peak multiples. With rates and "
            "integration costs up, the thesis has shifted from acquisition-count "
            "growth to same-store organic growth, dentist recruiting/retention, "
            "procurement scale, and disciplined leverage."),
        pe_activity=(
            "Among the most PE-penetrated healthcare services categories, with a "
            "deep bench of platforms and add-on programs. Diligence now centers "
            "on same-store organic growth quality (new-patient flow, hygiene "
            "reappointment, case acceptance), associate-dentist retention and "
            "the equity/partnership model, Medicaid-pediatric compliance exposure, "
            "corporate-practice/clinical-autonomy risk, and multiple/leverage "
            "discipline rather than the raw pace of tuck-ins."),
        notable_players=[
            "Heartland Dental (KKR)", "Aspen Dental Management (Leonard "
            "Green/Ares)", "Pacific Dental Services (physician-owned)",
            "Smile Brands", "MB2 Dental (doctor-partnership model)",
            "Dental Care Alliance", "Western Dental", "Delta Dental (dominant "
            "carrier network)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("New patients / month per office", "practice-dependent",
                "The leading indicator of growth; marketing efficiency and "
                "insurance-directory presence drive the top of the funnel."),
            Kpi("Hygiene reappointment rate", "target ~90%+",
                "The recurring engine and restorative feeder — a falling recall "
                "rate is an early warning the whole pipeline will soften."),
            Kpi("Case acceptance rate", "~30-50% of presented",
                "How much diagnosed treatment converts to production; the annual "
                "insurance cap and financing availability gate it."),
            Kpi("Production per provider (dentist / hygienist)", "chair-driven",
                "Output per operatory-hour; chair utilization and specialty mix "
                "set it more than headcount."),
            Kpi("Practice-level EBITDA margin (pre-DSO fee)", "~18-25%",
                "Healthy at the office level before the management fee; hygiene "
                "leverage and payer mix drive the spread."),
            Kpi("Same-store revenue growth", "the value metric",
                "Post-roll-up, organic same-store growth — not acquisition count "
                "— is what a buyer underwrites."),
        ],
        margin_profile=(
            "A dental office is a fixed chair-and-staff chassis: operatories, "
            "hygienists, assistants, front-desk, and a dentist are largely fixed, "
            "so contribution steps up with chair utilization and case acceptance. "
            "The recurring hygiene book carries steady margin and feeds the "
            "high-value restorative and specialty production, so the mix between "
            "preventive recall and big cases sets the P&L. Practice-level EBITDA "
            "runs high-teens-to-mid-twenties before the DSO management fee; the "
            "DSO captures procurement, RCM, and overhead scale on top. Because "
            "much of the high-value work is discretionary and gated by the low "
            "annual insurance maximum, same-store margin is sensitive to consumer "
            "confidence and to how well the office converts diagnosed treatment "
            "into accepted, financed cases."),
    ),
    risks=[
        Risk("Consumer-discretionary / recession sensitivity", "High",
             "The low annual insurance cap makes high-value elective work cash- "
             "or financing-dependent, so downturns defer treatment and hit "
             "same-store revenue directly."),
        Risk("Dentist labor shortage + wage/comp inflation", "High",
             "Recruiting and retaining associate dentists (and hygienists) is the "
             "binding operational constraint; comp inflation compresses the "
             "practice margin the DSO fee sits on."),
        Risk("Medicaid pediatric over-treatment enforcement (Benevis precedent)",
             "High",
             "Heavy Medicaid pediatric volume carries FCA and quota-culture "
             "scrutiny; the Kool Smiles/Benevis settlements are the standing "
             "precedent."),
        Risk("Corporate-practice / clinical-autonomy litigation", "Medium",
             "State boards and plaintiffs test whether the DSO improperly "
             "influences clinical decisions — a structural legal exposure."),
        Risk("Multiple compression + roll-up integration + leverage", "Medium",
             "A mature category that cycled through peak multiples; integration "
             "cost and high-rate leverage pressure returns."),
        Risk("PPO reimbursement compression (Delta/carrier leverage)", "Medium",
             "Dominant dental carriers hold fee-schedule leverage; PPO write-offs "
             "erode realized rates on the insured book."),
    ],
    diligence_questions=[
        "What is the same-store organic revenue growth by cohort, separated "
        "cleanly from acquisition and de novo growth?",
        "What are new-patient flow, hygiene reappointment, and case-acceptance "
        "trends — the leading indicators of the pipeline?",
        "What is the payer mix by office, and how large is the Medicaid-pediatric "
        "exposure and its compliance/over-treatment posture?",
        "What is the associate-dentist and hygienist turnover, compensation, and "
        "equity/partnership structure, and how exposed is production to key-doctor "
        "departure?",
        "How is the DSO/friendly-PC structure documented against corporate-"
        "practice-of-dentistry law in each state, including clinical-autonomy "
        "safeguards?",
        "What is the fee-for-service vs PPO/DHMO/Medicaid mix, the PPO write-off "
        "rate, and the exposure to Delta/dominant carriers?",
        "What is the specialty-capture rate (implants/ortho/endo kept in-house "
        "vs referred out), and the discretionary/cosmetic share of production?",
        "What is the leverage, average acquisition multiple, and de novo ramp "
        "profitability across the platform?",
    ],
    insider_lens=[
        "Hygiene is the whole flywheel. The recurring recall book is not just "
        "steady margin — it is the feeder for every crown, implant, and specialty "
        "referral. Watch the hygiene reappointment rate as the leading indicator; "
        "when recall softens, restorative production follows a quarter or two "
        "later.",
        "The insurance maximum is a business-model constraint, not a footnote. "
        "Dental plans cap benefits around $1,000-$2,000 a year — stale for "
        "decades — so anything major is effectively cash. Case acceptance and "
        "in-house financing, not the fee schedule, decide whether high-value "
        "treatment actually gets done.",
        "The DSO does not practice dentistry, and that line is load-bearing. "
        "Corporate practice of dentistry forces the friendly-PC structure; the "
        "real value the DSO adds is procurement scale, RCM, real estate, and — "
        "above all — recruiting and retaining dentists in a labor-short market. "
        "Where a DSO is seen to steer clinical decisions, the litigation risk is "
        "real.",
        "Pediatric Medicaid is the reputational third rail. Kool Smiles/Benevis "
        "turned production quotas on medically-unnecessary pediatric procedures "
        "into a landmark FCA case. A platform leaning on Medicaid pediatric "
        "volume needs its compliance and clinical-oversight story underwritten "
        "hard.",
        "Same-store, not store count, is the tell. A decade of roll-ups made "
        "acquisition growth cheap to fake and organic growth hard to fake — a "
        "buyer should separate de novo and acquisition from true same-store "
        "growth, because that is what compounds and what the next buyer pays for.",
        "The associate is the asset, and the asset can walk. Debt-laden new "
        "graduates increasingly prefer employment, which fuels the DSO model — "
        "but production concentrates in a few high-output dentists, so retention "
        "economics and the partnership/equity model (MB2-style) are the real "
        "durability question.",
    ],
    connections=default_connections(
        "dental",
        deals_sector="dental",
        extra_pages=[
            ("/industry/dental",
             "Industry deep-dive — DSO deal history + roll-up/compliance read"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — general dentist & dental-specialty (122300000X) "
             "supply and geography"),
            ("open_payments_general_payments_2024",
             "Open Payments — industry payments (implant/device/ortho) to "
             "dentists (relationship screen)"),
            ("bls_qcew_area_industry",
             "BLS QCEW — offices of dentists (NAICS 6212) wage & employment base "
             "for labor-cost mapping"),
            ("census_acs_cbsa_profile",
             "Census ACS — income & age density for de novo site selection and "
             "cash-pay demand"),
            ("medicaid_data_managed_care_by_state_2024",
             "Medicaid managed care by state — pediatric dental (EPSDT) exposure "
             "and rate context"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded providers screen (over-treatment/fraud "
             "diligence)"),
        ],
    ),
    sources=[
        Source("CMS — National Health Expenditure Accounts, dental-services "
               "spending line", "GOV",
               "https://www.cms.gov/data-research/statistics-trends-and-reports/national-health-expenditure-data"),
        Source("ADA Health Policy Institute — dental-spending, workforce, and "
               "DSO-affiliation data", "INDUSTRY",
               "https://www.ada.org/resources/research/health-policy-institute"),
        Source("U.S. DOJ — Benevis / Kool Smiles $23.9M False Claims Act "
               "settlement (pediatric Medicaid over-treatment, 2018)", "GOV",
               "https://www.justice.gov/opa/pr/dental-management-company-benevis-and-affiliated-kool-smiles-dental-clinics-pay-236-million"),
        Source("North Carolina State Board of Dental Examiners v. FTC, 574 U.S. "
               "494 (2015)", "ACADEMIC",
               "https://www.supremecourt.gov/opinions/14pdf/13-534_19m2.pdf"),
        Source("ADA — CDT (Current Dental Terminology) code set and coding "
               "guidance", "INDUSTRY", "https://www.ada.org/publications/cdt"),
        Source("PE Desk industry deep-dive (dental / DSO) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=dental"),
    ],
    live_figures=live_figures_from_dive("dental"),
    trends=(
        "Dental spent the last decade converting a cottage industry into a "
        "consolidated services category. Corporate practice of dentistry keeps "
        "clinical ownership with the dentist, so consolidation ran through the "
        "DSO/friendly-PC structure: a support organization takes the non-clinical "
        "business — procurement, RCM, HR, marketing, real estate — while the "
        "affiliated dentist owns the PC. Heartland, Aspen, Pacific Dental, Smile "
        "Brands, MB2, and scores of regional platforms pushed DSO affiliation "
        "from roughly a tenth of dentists toward a quarter-plus, and the category "
        "cycled through peak multiples. Two structural features shaped the "
        "economics throughout: a decades-stale annual insurance maximum that "
        "makes high-value work discretionary and cash/financing-dependent, and "
        "the hygiene-recall book that recurs and feeds the restorative pipeline. "
        "The forward tension is threefold — a dentist and hygienist labor "
        "shortage that makes recruiting/retention the binding constraint, a "
        "compliance and legal overhang concentrated in Medicaid pediatrics "
        "(Benevis) and corporate-practice/clinical-autonomy litigation, and a "
        "higher-rate environment that shifts the thesis from acquisition-count "
        "growth to disciplined same-store organic growth. Direct-to-consumer "
        "aligners (SmileDirectClub's 2023 collapse) proved the clinical model is "
        "hard to disintermediate."),
    growth_levers=[
        GrowthLever(
            "DSO affiliation / roll-up of independents",
            "Retiring owner-dentists and employment-preferring new graduates keep "
            "feeding acquisition and de novo growth into the consolidated "
            "platforms.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Same-store organic growth (recall + case acceptance)",
            "New-patient flow, hygiene reappointment, and higher case acceptance "
            "lift revenue per office without buying another practice.",
            "+ low-to-mid single %/yr", "ILLUSTRATIVE"),
        GrowthLever(
            "Specialty capture in-house",
            "Adding implants, clear aligners, endo, and oral surgery keeps "
            "high-value referrals inside the platform instead of leaking them "
            "out.",
            "+ margin mix", "ILLUSTRATIVE"),
        GrowthLever(
            "Aging population (implants, perio, restorative)",
            "Older adults retain more teeth and need more implants, perio "
            "maintenance, and restorative care — a durable demographic tailwind.",
            "+ demographic", "GOV"),
        GrowthLever(
            "Medicare Advantage supplemental dental",
            "MA plans increasingly bundle dental benefits, adding a new, "
            "growing (if lower-rate) covered-lives channel.",
            "+ channel", "GOV"),
        GrowthLever(
            "Consumer-discretionary sensitivity",
            "Because major treatment is cash/financing-dependent under the low "
            "insurance cap, downturns defer elective work — a recession "
            "headwind.",
            "cyclical headwind", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Insured/discretionary demand × the hygiene-recall flywheel",
        analysis=(
            "Dental volume is a blend of insurance-covered preventive/restorative "
            "utilization and discretionary self-pay demand, and the engine that "
            "compounds it is the recurring hygiene recall book. Preventive recall "
            "visits recur on a six-month cadence at high reappointment rates, "
            "generate steady margin, and continuously feed the diagnostic and "
            "restorative pipeline — so a practice's growth is best predicted by "
            "new-patient flow into recall and by how well diagnosed treatment "
            "converts to accepted cases. Demographics add a durable tailwind: an "
            "aging population retains more natural teeth and needs more implants, "
            "periodontal maintenance, and restorative care. The two structural "
            "governors are the low, stale annual insurance maximum (which pushes "
            "high-value treatment into cash/financing and makes it discretionary) "
            "and consumer confidence (which moves elective and cosmetic volume). "
            "Unlike a Medicare fee-schedule specialty, dental demand is part "
            "covered utilization and part consumer spending — so case acceptance "
            "and financing, not just a rate update, drive the volume that "
            "actually books."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Clinical + hygiene labor (dentists, hygienists, assistants)",
            "~40-50% of cost",
            "The dominant cost and the binding constraint; dentist/hygienist "
            "shortage and comp inflation directly compress the practice margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Dental supplies + lab fees", "~10-15% of cost",
            "Consumables, implants, crowns, and outsourced lab work; procurement "
            "scale is a core DSO margin lever.", "ILLUSTRATIVE"),
        CostDriver(
            "Occupancy + equipment (chairs, imaging, CBCT)", "~8-12% of cost",
            "The fixed chair-and-imaging chassis; operatory capex and de novo "
            "buildout gate expansion.", "ILLUSTRATIVE"),
        CostDriver(
            "Marketing + patient acquisition", "~5-8% of cost",
            "New-patient flow is bought — directory listings, digital marketing, "
            "and referral programs feed the top of the funnel.", "ILLUSTRATIVE"),
        CostDriver(
            "DSO shared services / G&A + RCM", "~8-12% of cost",
            "The management-fee-funded shared services — RCM, HR, compliance, "
            "and corporate overhead across the platform.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No CMS dental facility roll is vendored because dental sits largely "
        "outside Medicare (it is a commercial-and-cash market), so state "
        "geography is omitted rather than fabricated. The most consequential "
        "geographic variables are the state corporate-practice-of-dentistry "
        "doctrine and DSO-ownership/registration rules (which shape the "
        "friendly-PC structure and how far a DSO may operate), the state dental "
        "board's posture on advertising and non-dentist ownership (post-NC "
        "Dental v. FTC), Medicaid dental fee schedules and EPSDT scope (which "
        "make pediatric-Medicaid economics and compliance state-specific), and "
        "the emerging state PE-transaction-review laws. The NPI-taxonomy, "
        "Open-Payments, BLS wage, ACS-demographic, and Medicaid connectors linked "
        "below map dentist supply, device/implant relationships, labor cost, "
        "de novo demand geography, and pediatric-Medicaid exposure — the honest "
        "footprint read in the absence of a facility file."),
)

register(REPORT)
