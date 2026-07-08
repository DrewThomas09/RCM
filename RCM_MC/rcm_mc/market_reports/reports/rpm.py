"""Remote Patient Monitoring (RPM) — a market created by CPT codes.

Deals-only pattern (no facility footprint — RPM has no census). The single most
important fact is that RPM is a *code-created market*: it barely existed until
CMS activated the CPT codes (99453 setup, 99454 device/data, 99457/99458
treatment-management time) and reimbursed them under the Medicare Physician Fee
Schedule. Revenue is therefore 100% a function of those codes surviving,
paying, and being billed compliantly — and the '16 days in 30' data threshold is
the gate. That same explosive, code-driven growth put RPM squarely in the OIG's
program-integrity crosshairs. Live SOURCED figures (corpus deals, MOIC) come
from ``rpm_deep_dive()``; the honest deep read is the CPT-utilization connectors,
not a provider map.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="rpm",
    name="Remote Patient Monitoring (RPM)",
    care_setting="Ambulatory",
    naics="621999",
    one_line_def=(
        "Remote physiologic monitoring — a patient uses connected devices (blood-"
        "pressure cuff, glucometer, weight scale, pulse oximeter) that transmit "
        "readings, and clinical staff review the data and manage the condition — "
        "billed to Medicare/commercial under a specific set of CPT codes (99453/"
        "99454/99457/99458 for RPM; the 98975-series for remote therapeutic "
        "monitoring), usually enabled for physician practices by a device-plus-"
        "software vendor on a revenue-share."),
    tam_headline=TamHeadline(
        value=7.0, unit="$B", growth_pct=9.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US RPM revenue — enrolled patients × billable months × the "
            "blended per-patient-per-month Medicare/commercial payment for the "
            "RPM/RTM code stack. This is a TAM/SAM-style build off CMS CPT "
            "utilization, not a filed market figure. Growth is the modeled "
            "composite of chronic-disease prevalence, practice adoption, and "
            "commercial/Medicaid coverage expansion, net of a program-integrity "
            "and rate-pressure drag. ILLUSTRATIVE."),
    ),
    executive_summary=[
        "RPM is a market that CPT codes created. It was negligible until CMS "
        "activated 99453/99454/99457/99458 and paid them under the MPFS — so the "
        "entire revenue base is a policy artifact that can be repriced or "
        "restricted in any annual rule. Underwrite the codes, not the concept.",
        "The '16 days in 30' rule is the gate. 99454 (device + data) requires at "
        "least 16 days of readings in a 30-day period; a patient who doesn't hit "
        "16 days generates little or no billable revenue that month — so "
        "adherence, not enrollment, is the real KPI.",
        "The stack pays roughly $100-170 per patient per month when fully billed "
        "(setup once, then device + two tiers of management time), so the "
        "business is enrollment × adherence × months-retained × codes-billed — a "
        "recurring, per-patient annuity if, and only if, patients stay engaged.",
        "It's usually an enablement model: a vendor supplies FDA-cleared "
        "devices, the software, and often the monitoring clinical staff to a "
        "physician practice, and takes a revenue share of the Medicare payments "
        "— so the practice bills and the vendor's economics ride on the "
        "practice's patient panel and compliance.",
        "Explosive, code-driven growth made RPM an OIG/program-integrity target. "
        "OIG and MedPAC have flagged rapid RPM spend growth, questionable "
        "enrollment (patients billed who don't need or use monitoring), and "
        "missing-threshold billing — the same 'grew too fast on a new code' "
        "pattern that has repriced other Medicare niches.",
        "Coverage beyond Medicare is uneven: commercial and Medicaid RPM "
        "coverage varies by plan and state, so a book's durability depends "
        "heavily on payer mix and on the survival of the Medicare rates.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Practice identifies chronic patients (HTN, diabetes, CHF, COPD)",
            "Patient consent + enrollment; FDA-cleared device shipped/set up",
            "Setup & education billed once (99453)",
            "Device transmits ≥16 days of readings in 30 → device/data (99454)",
            "Clinical staff review data & manage; time logged (99457/99458)",
            "Practice bills Medicare/commercial; vendor takes revenue share",
            "Retention / adherence management to sustain monthly billing",
        ],
        sites_of_care=[
            "Patient's home (the device + connectivity)",
            "Physician practice / clinic (ordering + billing provider)",
            "Vendor / third-party clinical monitoring center (the staff)",
            "Adjacent: CCM (99490) and RTM (98975-series) stacked on the panel",
        ],
        money_flow=(
            "RPM is billed under the Medicare Physician Fee Schedule by the "
            "ordering practitioner (or under general supervision by clinical "
            "staff): 99453 is a one-time setup/education payment (~$19), 99454 "
            "pays for the device supply and data transmission for a 30-day period "
            "and REQUIRES ≥16 days of readings (~$46-50), and 99457/99458 pay for "
            "the first and each additional 20 minutes of monitoring/management "
            "time per month (~$48 and ~$40). Fully billed, the stack is roughly "
            "$100-170 per patient per month (MPFS national approximations, "
            "locality-adjusted). Remote therapeutic monitoring (RTM, 98975-98981) "
            "extends the model to respiratory/musculoskeletal and self-reported "
            "data. In the dominant enablement model, a vendor provides the "
            "devices, software, and often the monitoring staff and takes a "
            "revenue share of what the practice collects — so the whole chain's "
            "economics rest on enrollment, the 16-day adherence gate, and "
            "retention."),
        key_players=(
            "A fragmented enablement layer of RPM/RTM platform vendors that sell "
            "devices + software + (increasingly) turnkey clinical monitoring to "
            "practices, health systems, and value-based groups, plus the "
            "connected-device manufacturers underneath and a growing set of "
            "chronic-care-management and value-based-care companies that fold RPM "
            "into a broader care model. Because the billing provider is the "
            "practice, 'market share' is really share of enabled practices and "
            "enrolled patients — there is no facility roster and no dominant "
            "national brand."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicare RPM (99453/99454/99457/99458)",
                    "the core, code-created book",
                    "GOV · CMS MPFS RPM codes"),
            Segment("Remote therapeutic monitoring (RTM, 98975-series)",
                    "respiratory/MSK & self-reported extension",
                    "GOV · CMS MPFS RTM codes"),
            Segment("Chronic-care-management stack (CCM 99490 alongside RPM)",
                    "commonly co-billed on the same panel",
                    "GOV · CMS care-management codes"),
            Segment("Commercial / Medicare Advantage RPM",
                    "coverage varies by plan",
                    "ILLUSTRATIVE · commercial coverage patchwork"),
            Segment("Medicaid RPM",
                    "state-by-state coverage",
                    "GOV · state Medicaid RPM policies"),
        ],
        growth_drivers=[
            "Chronic-disease prevalence (hypertension, diabetes, CHF, COPD)",
            "Practice & health-system adoption of the billing model",
            "Value-based care pulling RPM into total-cost management",
            "Commercial & Medicaid coverage expansion",
            "Program-integrity & rate pressure — a real offsetting drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare (MPFS RPM/RTM)": 0.60,
            "Medicare Advantage": 0.15,
            "Commercial": 0.15,
            "Medicaid": 0.10,
        },
        rate_mechanics=[
            "99453 — one-time setup & patient education on the device (~$19, "
            "MPFS national approximation, locality-adjusted).",
            "99454 — device supply + daily recording/transmission for 30 days; "
            "REQUIRES ≥16 days of readings in the period to bill (~$46-50).",
            "99457 — first 20 minutes/month of RPM treatment-management time by "
            "clinical staff/QHP under general supervision (~$48); 99458 — each "
            "additional 20 minutes (~$40).",
            "RTM (98975-98981) — a parallel remote-therapeutic-monitoring family "
            "for respiratory/musculoskeletal and self-reported data, billed by a "
            "broader set of practitioners.",
            "Established-patient, consent, and single-practitioner-per-period "
            "rules — RPM must attach to an ordering relationship, one provider "
            "bills the device code per patient per period, and time must be "
            "documented.",
        ],
        reimbursement_risk=(
            "The risk is unusually concentrated because the revenue IS the code. "
            "First, annual MPFS rulemaking can cut the rates or tighten the "
            "requirements — an existential rather than incremental exposure for a "
            "pure-play. Second, the '16 days in 30' threshold and the time-based "
            "management codes make a large share of enrolled patients "
            "sub-billable in any given month, so realized revenue per enrolled "
            "patient is well below the theoretical stack. Third, and loudest, "
            "program integrity: OIG has flagged rapid RPM growth, enrollment of "
            "patients who don't need or use monitoring, and billing without the "
            "data threshold — with recoupment and False Claims Act exposure. "
            "Underwrite realized (not theoretical) per-patient revenue, the "
            "adherence rate, and the compliance posture, and assume the codes are "
            "under long-run pressure."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("CMS Medicare Physician Fee Schedule — RPM/RTM codes & rules",
                 "The codes, rates, supervision, consent, and documentation "
                 "requirements ARE the market; the annual Final Rule can reprice "
                 "or restrict the entire revenue base.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("'16 days in 30' data-collection requirement (99454)",
                 "The device/data code cannot be billed unless the patient "
                 "transmits ≥16 days of readings in a 30-day period — the gate "
                 "that turns adherence into revenue.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("OIG program-integrity scrutiny of RPM",
                 "OIG work plans and reports flag RPM overutilization, "
                 "questionable enrollment, and threshold non-compliance — the "
                 "defining enforcement risk for the sector.",
                 "https://oig.hhs.gov/reports-and-publications/workplan/"),
            Rule("FDA device clearance (measured physiologic parameter)",
                 "The connected devices must be FDA-cleared for the physiologic "
                 "measure being billed; using a non-cleared device undermines the "
                 "claim.",
                 "https://www.fda.gov/medical-devices"),
            Rule("Supervision, consent & established-patient rules",
                 "RPM must attach to an ordering relationship with patient "
                 "consent; clinical-staff time is billed under general "
                 "supervision, and only one practitioner bills the device code "
                 "per patient per period.",
                 None),
        ],
        policy_watch=[
            "Annual MPFS updates to RPM/RTM rates, thresholds, and supervision",
            "OIG RPM audit findings and False Claims Act enforcement",
            "MedPAC commentary on RPM spend growth and value",
            "Commercial & Medicaid RPM coverage expansion (or retrenchment)",
            "New/expanded RTM and device-specific coding",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Highly fragmented enablement vendors selling devices + software + "
            "monitoring to practices and systems, competing on device breadth, "
            "clinical-staffing depth, billing compliance, and EHR integration. "
            "Because the practice is the billing provider, there is no facility "
            "census and no dominant national operator — 'share' is share of "
            "enabled practices and enrolled patients."),
        hhi_or_share=(
            "No provider roster exists for RPM (it is code-created, not "
            "facility-based), so share is honestly unquantified. The real "
            "structural read is the CMS CPT-utilization data (who bills 99453/"
            "99454/99457/99458 and how much) and the deal history below — not a "
            "map."),
        consolidation=(
            "Consolidation logic is toward turnkey scale (devices + software + "
            "clinical staffing) and toward embedding RPM inside broader chronic-"
            "care-management and value-based-care platforms, where monitoring is "
            "a means to total-cost outcomes rather than a standalone billing "
            "line. Standalone device-only vendors are the most exposed to rate "
            "and integrity pressure."),
        pe_activity=(
            "Sponsor interest rode the code-driven growth curve, then grew more "
            "discriminating as OIG scrutiny and rate risk surfaced. The durable "
            "thesis favors enablement platforms with strong compliance, high "
            "adherence/retention, diversified payer coverage, and a value-based "
            "attach — not pure Medicare-FFS device plays whose entire model is a "
            "single code stack under pressure."),
        notable_players=[
            "RPM/RTM enablement platform vendors (devices + software + monitoring)",
            "Chronic-care-management & value-based-care platforms with RPM attach",
            "Connected-device manufacturers (cuffs, glucometers, scales, pulse ox)",
            "Health-system & physician-group in-house RPM programs",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Realized revenue per enrolled patient-month", "$40-150",
                "Well below the theoretical $100-170 stack because many patients "
                "miss the 16-day gate or the management-time threshold in a "
                "given month."),
            Kpi("Adherence rate (% hitting 16 days/30)", "the billing gate",
                "The share of enrolled patients who transmit enough days to bill "
                "99454 — the true revenue driver, not enrollment."),
            Kpi("Enrollment / activation rate", "panel penetration",
                "Share of eligible chronic patients enrolled and actually using "
                "the device."),
            Kpi("Retention / churn", "annuity durability",
                "Monthly attrition erodes the recurring base; RPM is only an "
                "annuity if patients stay engaged."),
            Kpi("Device cost & amortization", "COGS per patient",
                "Connected-hardware cost spread over the patient's monitored "
                "months — high churn ruins device economics."),
            Kpi("Net revenue after revenue-share", "vendor take",
                "In enablement deals the practice bills; the vendor's economics "
                "are its share of collections, net of devices and staff."),
        ],
        margin_profile=(
            "RPM's theoretical per-patient annuity is attractive, but realized "
            "margin is governed by three leakage points: the 16-day adherence "
            "gate (patients who don't transmit don't bill), churn (which strands "
            "device cost and collapses the annuity), and revenue-share (which "
            "splits the MPFS payment between practice and vendor). Clinical-"
            "monitoring labor and device COGS are the main costs; software is the "
            "scalable-leverage layer. The economics reward high adherence, low "
            "churn, and diversified payer coverage — and punish a book that "
            "chased enrollment counts over engagement. Ranges are ILLUSTRATIVE — "
            "underwrite realized revenue per patient-month and the adherence "
            "curve, not the headline code stack."),
    ),
    risks=[
        Risk("Reimbursement / code-repricing risk", "High",
             "The entire revenue base is the MPFS RPM/RTM codes; an annual rule "
             "cut or requirement tightening is existential for a pure-play."),
        Risk("Program-integrity / OIG enforcement", "High",
             "Rapid growth drew scrutiny of enrollment, threshold compliance, "
             "and necessity — recoupment and False Claims Act exposure."),
        Risk("Adherence / 16-day-gate leakage", "High",
             "A large share of enrolled patients miss the data threshold in a "
             "given month, so realized revenue is far below theoretical."),
        Risk("Churn & device economics", "Medium",
             "Patient attrition strands device cost and collapses the recurring "
             "annuity that the model depends on."),
        Risk("Payer-coverage concentration (Medicare-heavy)", "Medium",
             "Uneven commercial/Medicaid coverage leaves many books dependent on "
             "Medicare rates surviving."),
        Risk("Commoditization / device differentiation", "Low",
             "Connected devices commoditize; durable value is in compliance, "
             "clinical staffing, and value-based attach, not hardware."),
    ],
    diligence_questions=[
        "What is realized revenue per enrolled patient-month (not the theoretical "
        "stack), and how does it trend?",
        "What is the adherence rate — the share of patients hitting 16 days in "
        "30 — and how is it managed?",
        "What is monthly churn, and what are device cost, amortization, and loss "
        "rates against it?",
        "What is the payer mix (Medicare vs MA vs commercial vs Medicaid), and "
        "how exposed is revenue to Medicare rate changes?",
        "What is the compliance posture — consent, 16-day documentation, single-"
        "biller-per-period, supervision — and any audit/OIG history?",
        "Are the devices FDA-cleared for the billed physiologic measure, and how "
        "is that controlled?",
        "In enablement deals, what is the revenue-share and who bears device, "
        "staffing, and compliance risk between vendor and practice?",
    ],
    insider_lens=[
        "The market is the code. RPM did not exist as a business until CMS turned "
        "on 99453/99454/99457/99458 — which means a line in the annual MPFS can "
        "make or break the entire thesis. This is the opposite of a demographic "
        "growth story; it's a reimbursement-policy position.",
        "Enrollment is vanity; adherence is revenue. Because 99454 requires 16 "
        "days of readings in 30, a book with 10,000 'enrolled' patients and poor "
        "transmission adherence bills a fraction of the headline. The real asset "
        "is the adherence curve and the retention, not the enrollment count.",
        "Fast growth on a new code is a fraud magnet, and the regulators know the "
        "pattern. OIG has already flagged RPM enrollment of patients who don't "
        "need it and billing without the data threshold — treat program-"
        "integrity posture as first-order diligence, not compliance boilerplate.",
        "Churn quietly destroys the device economics. RPM is pitched as a "
        "recurring annuity, but every churned patient strands a connected device "
        "and the onboarding cost; a high-churn book has worse unit economics than "
        "the per-patient-per-month math suggests.",
        "Revenue-share hides who really earns the margin. In the enablement "
        "model the practice bills Medicare and the vendor takes a cut — so the "
        "vendor's durable value is compliance, clinical staffing, and stickiness, "
        "not the device. If the practice can swap vendors and keep billing, the "
        "moat is thin.",
    ],
    connections=default_connections(
        "rpm",
        deals_sector="rpm",
        connectors=[
            ("cms_open_data_mup_physician_by_provider_service",
             "CMS Physician & Other Practitioners — RPM CPT (99453/99454/99457/"
             "99458) utilization & payment"),
            ("cms_open_data_medicare_telehealth_trends",
             "CMS Medicare Telehealth Trends — remote-care adoption context"),
            ("openfda_device_510k",
             "openFDA 510(k) — clearance status of connected monitoring devices"),
            ("npi_provider",
             "NPI Registry — ordering practices & practitioners billing RPM"),
            ("oig_leie_exclusions",
             "OIG LEIE — exclusion screen for monitoring clinical staff"),
            ("open_payments_general_payments_2024",
             "CMS Open Payments — device-industry ties to billing practices"),
        ],
    ),
    sources=[
        Source("CMS Medicare Physician Fee Schedule — RPM (99453/99454/99457/"
               "99458) and RTM (98975-series) codes, rates, and requirements",
               "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("HHS Office of Inspector General — RPM program-integrity work "
               "plan items and reports", "GOV",
               "https://oig.hhs.gov/reports-and-publications/workplan/"),
        Source("MedPAC — commentary on remote monitoring spend growth and value",
               "GOV", "https://www.medpac.gov/"),
        Source("FDA — medical-device clearance for connected physiologic "
               "monitors", "GOV", "https://www.fda.gov/medical-devices"),
        Source("PE Desk industry deep-dive (remote patient monitoring) + "
               "realized-deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=rpm"),
    ],
    live_figures=live_figures_from_dive("rpm"),
    trends=(
        "RPM went from near-zero to a real Medicare line item in a few years for "
        "one reason: CMS activated and clarified the CPT codes (99453/99454/"
        "99457/99458), and remote therapeutic monitoring (98975-series) extended "
        "the model. That produced explosive, code-driven growth in enabled "
        "practices and enrolled patients — and, predictably, drew program-"
        "integrity attention. OIG and MedPAC have flagged rapid spend growth, "
        "enrollment of patients who don't need monitoring, and billing without "
        "the '16 days in 30' data threshold; the sector now carries an audit "
        "overhang that reprices standalone Medicare-FFS device plays. The "
        "forward trajectory bifurcates: pure-play device vendors are exposed to "
        "annual MPFS rate risk and integrity scrutiny, while the durable models "
        "embed RPM inside chronic-care-management and value-based-care platforms "
        "where monitoring drives total-cost outcomes rather than a standalone "
        "billing line. Real clinical demand (chronic-disease prevalence) is "
        "large and rising, but the honest read for diligence is realized revenue "
        "per patient-month, adherence, retention, and compliance — because the "
        "revenue base is a policy artifact, not a demographic one."),
    growth_levers=[
        GrowthLever(
            "Practice / health-system adoption of the billing model",
            "Each newly enabled practice unlocks its chronic-patient panel for "
            "enrollment — the primary growth engine.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Chronic-disease prevalence",
            "Hypertension, diabetes, CHF, and COPD prevalence expand the "
            "eligible-patient base for monitoring.",
            "demand base", "GOV"),
        GrowthLever(
            "Value-based-care attach",
            "Risk-bearing groups fold RPM into total-cost management, adding a "
            "durable, outcomes-linked demand beyond FFS billing.",
            "monetization", "ILLUSTRATIVE"),
        GrowthLever(
            "Commercial & Medicaid coverage expansion",
            "Coverage beyond Medicare broadens the payable population and reduces "
            "single-payer dependence.",
            "coverage", "ILLUSTRATIVE"),
        GrowthLever(
            "Program-integrity & rate pressure",
            "OIG scrutiny and annual MPFS repricing remove weak billers and cap "
            "the per-patient economics — a structural offset.",
            "−drag (structural)", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Billable enrolled patient-months (eligible patients × enrollment "
               "× 16-day adherence × retention)",
        analysis=(
            "The true demand meter for RPM is not the count of chronic patients, "
            "nor even enrollments — it is BILLABLE patient-months: eligible "
            "chronic patients, times the share actually enrolled, times the share "
            "who transmit ≥16 days in a 30-day period (the 99454 gate), times "
            "retention across months. Chronic-disease prevalence (hypertension, "
            "diabetes, CHF, COPD) sets the ceiling and CMS CPT-utilization data "
            "shows what is actually billed, but the binding constraints are "
            "practice adoption (who turns on the billing model) and patient "
            "adherence/retention (who keeps transmitting). That is why a credible "
            "volume model discounts the eligible pool heavily for enrollment and "
            "adherence rather than assuming full-stack billing on every chronic "
            "patient — and why realized revenue per patient-month is always well "
            "below the theoretical code stack."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Clinical monitoring labor (nurses/QHP reviewing data)",
            "#1 — the COGS",
            "The 99457/99458 management time is real staff time; in enablement "
            "deals the vendor often supplies it, making it the dominant cost.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Connected-device hardware & logistics",
            "~15-25% of cost",
            "The cuffs, glucometers, scales, and pulse-ox units plus shipping and "
            "setup — churn strands this cost per patient.", "ILLUSTRATIVE"),
        CostDriver(
            "Software platform & EHR/billing integration",
            "~12-20% of cost",
            "Data ingestion, dashboards, and claims integration — the scalable-"
            "leverage layer of the model.", "ILLUSTRATIVE"),
        CostDriver(
            "Enrollment, adherence & retention operations",
            "~10-15% of cost",
            "Onboarding patients and keeping them above the 16-day gate is the "
            "engine that converts enrollment into billable months.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Compliance, coding & audit defense",
            "~8-12% of cost",
            "Consent, 16-day documentation, single-biller rules, and OIG-"
            "readiness — a real cost center given the integrity scrutiny.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "RPM is code-created and has no facility footprint, so no provider map is "
        "fabricated. The honest geographic read is regulatory and epidemiologic: "
        "billable volume concentrates where practices adopt the model and where "
        "chronic-disease prevalence is high, while payability varies by state "
        "Medicaid RPM coverage and by commercial-plan policy on top of the "
        "national Medicare base. Use the CMS CPT-utilization connector (who bills "
        "99453/99454/99457/99458, and where) and the deal history below rather "
        "than a facility census."),
)

register(REPORT)
