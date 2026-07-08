"""Mobile Diagnostics — portable diagnostic services brought to the patient.

Deals-only deep-dive (mobile-provider rosters are not public, so geography is
omitted rather than fabricated; the SOURCED layer is the sector's mobile-
diagnostics deal history). Portable X-ray, mobile ultrasound/echo, EKG/Holter,
vascular Doppler, and bone density are delivered at skilled-nursing and
assisted-living facilities, homes, hospices, and correctional sites by
traveling technologists, with the images read remotely. The qualitative
sections are authored around what makes this subsector unique: the separately
reimbursed TRANSPORTATION component (R0070/R0075) whose per-patient rate FALLS
as you add patients at a stop — making route density the entire business — plus
the SNF consolidated-billing maze and a long fraud-enforcement history.
Consumes ``mobile_diagnostics_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="mobile_diagnostics",
    name="Mobile Diagnostics",
    care_setting="Dx & labs",
    naics="621512",
    one_line_def=(
        "Portable diagnostic services delivered at the patient's location — "
        "portable X-ray, mobile ultrasound/echocardiography, EKG/Holter/"
        "telemetry, vascular Doppler, and bone-density scans — performed at "
        "skilled-nursing and assisted-living facilities, homes, hospices, and "
        "correctional sites by traveling technologists, with the study read "
        "remotely. In Medicare terms it is the portable-X-ray-supplier and "
        "mobile-IDTF model, defined by a separately paid TRANSPORTATION "
        "component."),
    tam_headline=TamHeadline(
        value=2.5, unit="$B", growth_pct=6.5, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US mobile/portable diagnostic services revenue is a niche not "
            "published as a single figure; ~$2.5B is the modeled composite. "
            "The GOV mechanic anchoring it is the Medicare portable-X-ray "
            "transportation component (R0070/R0075) plus the setup (Q0092), "
            "technical, and professional components in the segments below. "
            "Growth is the modeled composite of SNF/ALF census growth and the "
            "avoided-transport value proposition."),
    ),
    executive_summary=[
        "Route density is the entire business. Medicare pays a separately "
        "reimbursed TRANSPORTATION component for portable X-ray — R0070 for a "
        "single patient at a location, R0075 split across patients when "
        "several are seen at one stop — so per-patient transport pay FALLS as "
        "you cluster patients, but logistics margin RISES. The asset is a "
        "technologist and van visiting dense clusters of nursing-home beds, not "
        "the transport code itself.",
        "SNF consolidated billing decides who pays. For a resident in a Part A "
        "skilled-nursing stay, many services are bundled into the SNF's PPS "
        "per-diem, so the mobile provider contracts with the facility rather "
        "than billing Medicare; the X-ray technical component is generally "
        "excluded (separately billable), but the consolidated-billing rules are "
        "a compliance minefield.",
        "This is a fraud-enforcement hotbed. Mobile diagnostics on nursing-home "
        "residents has a decades-long OIG/DOJ history — medically unnecessary "
        "tests, phantom or upcoded transportation, and R0075 multi-patient "
        "billing abuse — so medical-necessity and order documentation are "
        "first-order diligence, not footnotes.",
        "Facility contracts are the moat and the concentration risk. A "
        "preferred-provider relationship with a SNF/ALF chain across a "
        "geography is the whole revenue base; winning a chain builds route "
        "density, losing one is a cliff.",
        "The value pitch is avoided transport. Bringing the X-ray or echo to "
        "the bedside avoids an ambulance ride, an ED visit, and resident "
        "disruption — a real cost saving that facilities, payers, and families "
        "value, and the clinical reason the model persists.",
        "The read is teleradiology in disguise. The mobile provider owns the "
        "technical acquisition and the transportation; the interpretation is "
        "the professional component, usually read remotely — the same TC/PC "
        "split as fixed imaging.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Facility / treating physician orders a bedside study (with indication)",
            "Order + medical-necessity documentation captured",
            "Dispatch routes a technologist + portable unit to the site",
            "Technologist acquires the study at the bedside (technical + transport)",
            "Images/tracings transmitted to a reading physician (professional)",
            "Report returned to the facility / ordering physician; STAT results called",
            "Billing — Medicare Part B claim OR SNF-contract invoice per "
            "consolidated-billing rules",
            "Route optimization + facility contract management for density",
        ],
        sites_of_care=[
            "Skilled-nursing facilities (SNF) — the core demand",
            "Assisted-living & memory-care communities",
            "Patient homes & home-health / hospice patients",
            "Correctional facilities (avoided-transport is acute here)",
            "Group homes / IDD residential settings",
            "The reading room — remote (teleradiology / telecardiology)",
        ],
        money_flow=(
            "Portable X-ray uniquely earns FOUR pieces on a Medicare claim: the "
            "base radiologic procedure, the technical setup component (Q0092), "
            "the professional interpretation, and — distinctively — a "
            "TRANSPORTATION component. Transportation is R0070 when a single "
            "patient is seen at a location and R0075 when multiple patients are "
            "seen on one trip, with the R0075 amount divided among the patients "
            "— so the per-patient transport payment declines as the stop gets "
            "denser even though the trip cost is shared. Mobile ultrasound, "
            "echo, and vascular studies are paid under MPFS with the usual "
            "technical/professional split. The critical wrinkle is SNF "
            "consolidated billing: for a resident in a covered Part A stay, "
            "bundled services are paid to the SNF (which then contracts the "
            "mobile provider privately), while excluded services (typically the "
            "X-ray technical component) are billed to Medicare Part B directly. "
            "The economic engine is patients-per-stop and trips-per-tech against "
            "a fixed technologist, vehicle, and equipment base."),
        key_players=(
            "Highly fragmented and regional, under a few scaled operators. "
            "TridentCare (the former TridentUSA / MobileX, the largest mobile "
            "X-ray/ultrasound/lab provider to SNF/ALF/home) is the national "
            "reference point; DMS Health Technologies, Schryver Medical, and a "
            "long tail of regional mobile-diagnostic companies serve local "
            "SNF/ALF corridors. Reading physicians (teleradiology/"
            "telecardiology) and equipment vendors sit adjacent. The buyers are "
            "nursing-home and assisted-living operators, home-health and hospice "
            "agencies, and correctional health providers."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Portable X-ray (transport R0070/R0075 + Q0092 + TC + PC)",
                    "the defining service line",
                    "GOV · Medicare portable-X-ray components (mechanic)"),
            Segment("Mobile ultrasound / echocardiography",
                    "MPFS TC + PC, growing",
                    "ILLUSTRATIVE · modeled service mix"),
            Segment("EKG / Holter / telemetry & vascular Doppler",
                    "high-frequency bedside cardiology",
                    "ILLUSTRATIVE · modeled service mix"),
            Segment("SNF / ALF resident base",
                    "the core demand population",
                    "ILLUSTRATIVE · SNF/ALF census, directional"),
            Segment("Home / hospice / correctional",
                    "avoided-transport-driven settings",
                    "ILLUSTRATIVE · access-driven demand"),
        ],
        growth_drivers=[
            "SNF / ALF census growth on the aging curve",
            "Avoided-transport ROI (no ambulance, no ED trip)",
            "Shift of diagnostics into lower-cost, at-site settings",
            "Correctional and home-based demand for bedside diagnostics",
            "Transportation-component rate policy + integrity scrutiny as drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.68,
            "Medicaid": 0.14,
            "Commercial / facility contract / self-pay": 0.18,
        },
        rate_mechanics=[
            "Transportation component — R0070 (single patient at a location) "
            "and R0075 (multiple patients on one trip, amount divided among "
            "them); per-patient transport pay falls as the stop gets denser.",
            "Setup component Q0092 — the portable-equipment setup fee, billed "
            "per procedure/patient in addition to the base X-ray code.",
            "Technical + professional split — the X-ray technical component and "
            "the radiologist's professional interpretation (-26); mobile US/echo "
            "follow the MPFS TC/PC structure.",
            "SNF consolidated billing — for Part A SNF residents, bundled "
            "services are paid to the SNF (private mobile-provider contract); "
            "excluded services (typically X-ray TC) bill Medicare Part B.",
            "Physician order + medical necessity + supervision — portable X-ray "
            "requires a treating-physician order and meets the "
            "portable-X-ray-supplier conditions for coverage.",
            "Multiple Procedure Payment Reduction (MPPR) on imaging technical/"
            "professional components applies as in fixed imaging.",
            "Medicare Part B vs facility-contract mix — realized revenue depends "
            "heavily on whether a study is separately billable or bundled.",
        ],
        reimbursement_risk=(
            "The distinctive risk is the transportation component. R0075's "
            "per-patient division means route density is essential to economics, "
            "yet it is precisely the code that OIG and DOJ have policed for "
            "abuse (billing single-patient transport when multiple patients were "
            "seen, phantom trips) — so the very lever that drives margin is the "
            "one under the microscope. SNF consolidated billing adds revenue "
            "risk: misclassifying a bundled service as separately billable is an "
            "overpayment and a compliance finding. Medical-necessity denials on "
            "diagnostics ordered for frail residents are common, and the whole "
            "segment carries elevated audit and False Claims Act exposure. "
            "Finally, MPFS technical/professional rate erosion and any cut to "
            "the transportation or setup components would hit the model's thin, "
            "logistics-driven margins directly."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Portable X-ray supplier Conditions for Coverage "
                 "(42 CFR 486.100-486.110)",
                 "The Medicare conditions a portable-X-ray supplier must meet — "
                 "supervision, personnel, equipment, and order requirements that "
                 "gate coverage and billing.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-486/subpart-C"),
            Rule("Medicare transportation & setup components (R0070/R0075/Q0092)",
                 "The billing rules for portable-X-ray transportation and setup "
                 "— including the R0075 per-patient division that defines the "
                 "economics and the audit exposure.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("SNF consolidated billing (SSA §1888(e); PPS)",
                 "Determines which diagnostic services for Part A residents are "
                 "bundled into the SNF per-diem versus separately billable — the "
                 "line between a facility contract and a Medicare claim.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/skilled-nursing-facility-snf/consolidated-billing"),
            Rule("Anti-Kickback Statute + OIG mobile-diagnostics guidance",
                 "Referral and facility-arrangement rules; OIG has issued "
                 "advisory opinions and enforcement specific to mobile "
                 "diagnostics on nursing-home residents.",
                 "https://oig.hhs.gov/compliance/advisory-opinions/"),
            Rule("Physician order, supervision & medical necessity",
                 "Diagnostic tests require a treating-physician order and "
                 "documented medical necessity — the core of the audit defense "
                 "for frail-resident testing.",
                 "https://www.cms.gov/medicare/regulations-guidance"),
            Rule("State radiologic-technologist licensure & radiation safety",
                 "Mobile units and technologists are licensed and inspected "
                 "under state radiation-control programs.", None),
        ],
        policy_watch=[
            "Transportation-component (R0070/R0075) rate and billing-rule "
            "scrutiny",
            "OIG/DOJ enforcement on mobile-diagnostics medical necessity and "
            "transport upcoding",
            "SNF consolidated-billing exclusion-list changes",
            "MPFS technical/professional rate updates hitting mobile imaging",
            "Any expansion of bundled/at-home diagnostic payment models",
            "State radiologic-technologist and radiation-safety requirements",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Highly fragmented and regional. A national reference operator "
            "(TridentCare) and a few multi-state players sit atop a long tail of "
            "local mobile-diagnostic companies that own SNF/ALF corridors in "
            "their metro. The acquirable pool is that regional operator tail, "
            "where a buyer can knit together adjacent routes and facility "
            "contracts. No public mobile-provider census is vendored, so a "
            "facility-count HHI is honestly omitted."),
        hhi_or_share=(
            "No dominant national owner beyond TridentCare's reference "
            "position; concentration is intensely local — the operator with the "
            "densest facility-contract book and route network in a metro holds "
            "the effective share there. Read it market-by-market, by facility "
            "contracts, not nationally."),
        consolidation=(
            "A roll-up logic built on route density: acquiring adjacent regional "
            "operators adds facility contracts and lets a buyer visit more "
            "patients per trip, improving the transportation-component and "
            "logistics economics. TridentCare's history (including a financial "
            "restructuring) shows both the scale opportunity and the thin-margin "
            "fragility of the model. Home-based-care and SNF-services platforms "
            "eye mobile diagnostics as a tuck-in."),
        pe_activity=(
            "PE plays regional mobile-diagnostic roll-ups where route density, "
            "facility contracts, and back-office/billing scale compound, and as "
            "tuck-ins to broader post-acute and home-based platforms. "
            "Quality-of-earnings centers hard on compliance — medical-necessity "
            "and transportation-billing documentation, consolidated-billing "
            "classification, and OIG/FCA history — alongside facility-contract "
            "concentration and true route density."),
        notable_players=[
            "TridentCare (MobileX)", "DMS Health Technologies",
            "Schryver Medical", "Regional mobile X-ray/ultrasound operators",
            "SNF/ALF-embedded diagnostic providers",
            "Teleradiology/telecardiology read partners",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Patients / stop (route density)", "the core lever",
                "R0075 divides transport pay across patients, but logistics "
                "margin rises with density — clustering beds per stop is the "
                "whole game."),
            Kpi("Trips / technologist / day", "productivity ceiling",
                "Techs, vans, and equipment are fixed; trips and patients per "
                "shift set utilization and margin."),
            Kpi("Revenue / study (blended)",
                "transport + setup + TC + PC (X-ray) / MPFS (US/echo)",
                "Portable X-ray stacks four components; ultrasound/echo follow "
                "the MPFS TC/PC structure."),
            Kpi("Facility contracts / beds under contract", "the demand base",
                "SNF/ALF beds under a preferred-provider contract define route "
                "density and revenue — and the concentration risk."),
            Kpi("Part B vs SNF-contract revenue split", "who pays",
                "Consolidated billing determines whether a study bills Medicare "
                "or invoices the SNF — very different yield and risk."),
            Kpi("Mobile-diagnostics EBITDA margin", "logistics-thin, density-driven",
                "Margins are modest and swing on route density, tech/vehicle "
                "cost, and denial/compliance drag."),
        ],
        margin_profile=(
            "Mobile diagnostics is a logistics business with a thin, "
            "density-driven margin. The fixed cost is the technologist, the "
            "vehicle, and the portable equipment; the marginal patient at an "
            "existing stop is high-contribution even though the R0075 transport "
            "component divides per patient. So the model lives or dies on route "
            "density — patients per stop and stops per tech per day — and on the "
            "facility-contract book that creates that density. Layered on top is "
            "the payer/consolidated-billing mix (separately billable Part B "
            "versus bundled SNF contract) and a heavier-than-usual compliance "
            "and denial drag between gross and net, given the segment's audit "
            "exposure. Scale helps by densifying routes and spreading billing/"
            "compliance overhead, not by changing the per-study economics."),
    ),
    risks=[
        Risk("Medical-necessity denials + False Claims Act exposure", "High",
             "Diagnostics on frail residents draw denials, and the segment has "
             "a long OIG/DOJ history — documentation gaps become FCA risk."),
        Risk("Transportation-component (R0075) billing scrutiny", "High",
             "The per-patient transport division is both the margin lever and "
             "the classic upcoding target — the code driving economics is the "
             "one under audit."),
        Risk("Facility-contract concentration", "High",
             "Revenue and route density ride on SNF/ALF chain contracts; losing "
             "a chain is a step-down in both volume and logistics efficiency."),
        Risk("SNF consolidated-billing misclassification", "Medium",
             "Treating a bundled service as separately billable is an "
             "overpayment and a compliance finding; the rules are intricate."),
        Risk("MPFS / transport-rate erosion", "Medium",
             "Cuts to imaging TC/PC or the transportation/setup components hit "
             "the model's already-thin margins directly."),
        Risk("Technologist labor & vehicle/fuel cost", "Medium",
             "Tech supply, wages, and fleet/fuel costs set the fixed base and "
             "gate how many routes can run."),
    ],
    diligence_questions=[
        "What is true route density — patients per stop and stops per tech per "
        "day — and how much unused route capacity exists?",
        "How concentrated is revenue in the top SNF/ALF chain contracts, and "
        "what are the renewal terms and exclusivity?",
        "What is the Medicare Part B versus SNF-contract revenue split, and is "
        "consolidated billing classified correctly by service?",
        "What is the transportation-component (R0070 vs R0075) billing pattern, "
        "and does it match the actual multi-patient trip data?",
        "What is the medical-necessity and physician-order documentation rate, "
        "and what is the denial and audit history?",
        "What is the OIG/DOJ/UPIC history, and what reserves are held against "
        "potential recoupment or FCA exposure?",
        "What is the service mix (X-ray vs ultrasound/echo vs cardiac), and how "
        "is the professional read sourced and priced?",
        "What is the technologist supply, wage trend, and fleet cost, and how "
        "does it cap route expansion?",
    ],
    insider_lens=[
        "Route density IS the P&L. The R0075 transportation component divides "
        "across patients at a stop, so per-patient transport pay falls with "
        "density — but the fixed tech-and-van cost is shared, so logistics "
        "margin rises. The winning operator clusters the most nursing-home beds "
        "per trip, and the whole M&A logic is stitching adjacent routes and "
        "facility contracts together.",
        "Consolidated billing decides who writes the check. For a Part A SNF "
        "resident, many services are bundled into the SNF's per-diem, so you "
        "contract with the facility instead of billing Medicare; the X-ray "
        "technical component is usually carved out and billed to Part B. Get "
        "that classification wrong and you are looking at overpayments, not "
        "revenue.",
        "This is one of the most enforced niches in diagnostics. Portable "
        "imaging on nursing-home residents has a decades-long fraud history — "
        "unnecessary tests, phantom transport, R0075 upcoding — so the "
        "documentation quality, not the revenue run-rate, is what you are "
        "really buying.",
        "The contract book is the asset and the risk. A preferred-provider "
        "relationship with a SNF or ALF chain builds the dense routes the "
        "economics need; but that same concentration means a single chain "
        "decision can reset the business overnight.",
        "The value story is avoided transport, and it is real. Bringing the "
        "study to the bedside spares an ambulance ride, an ED visit, and a "
        "disoriented resident — a genuine system saving that keeps facilities, "
        "payers, and families bought in, which is why the model endures despite "
        "thin margins and heavy scrutiny.",
    ],
    connections=default_connections(
        "mobile_diagnostics",
        deals_sector="mobile_diagnostics",
        extra_pages=[
            ("/industry/mobile_diagnostics",
             "Industry deep-dive — mobile-diagnostics deal history + structure"),
        ],
        connectors=[
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare utilization by HCPCS — portable-X-ray transport "
             "(R0070/R0075) & setup (Q0092) volume & allowed"),
            ("provider_data_medical_equipment_suppliers",
             "CMS supplier enrollment — mobile diagnostic / DMEPOS suppliers"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — portable-X-ray & mobile-IDTF supplier enrollment"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (mobile-diagnostics "
             "integrity screen)"),
            ("cms_open_data_market_saturation_state_county",
             "CMS Market Saturation — supplier density by county (route "
             "planning)"),
            ("census_acs_cbsa_profile",
             "Census ACS — senior density for SNF/ALF demand corridors"),
        ],
    ),
    sources=[
        Source("Portable X-ray supplier Conditions for Coverage "
               "(42 CFR 486.100-486.110)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-486/subpart-C"),
        Source("CMS — Medicare Physician Fee Schedule & portable-X-ray "
               "transportation/setup components (R0070/R0075/Q0092)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("CMS — SNF consolidated billing (PPS)", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/skilled-nursing-facility-snf/consolidated-billing"),
        Source("HHS OIG — mobile-diagnostics advisory opinions & enforcement "
               "(nursing-home diagnostic services)", "GOV",
               "https://oig.hhs.gov/compliance/advisory-opinions/"),
        Source("American College of Radiology — practice parameters for "
               "portable/mobile imaging", "INDUSTRY", "https://www.acr.org/"),
        Source("PE Desk industry deep-dive (mobile diagnostics) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=mobile_diagnostics"),
    ],
    live_figures=live_figures_from_dive("mobile_diagnostics"),
    trends=(
        "Mobile diagnostics grew up as a service to skilled-nursing and "
        "assisted-living facilities, and its trajectory tracks the post-acute "
        "population and the economics of avoided transport. The clinical pitch "
        "is durable: bringing an X-ray, echo, or EKG to the bedside spares a "
        "frail resident an ambulance transfer and an ED visit, saving the "
        "system money and reducing disruption — so facilities, payers, and "
        "families keep the model alive. Two structural features shaped its "
        "history. First, the transportation component (R0070/R0075) made route "
        "density the core economic lever, driving a roll-up logic where "
        "acquiring adjacent operators and facility contracts lets a technologist "
        "visit more patients per trip. Second, that same transportation code, "
        "and diagnostics on frail residents generally, made the niche one of the "
        "most enforced corners of diagnostics — a long OIG/DOJ record of "
        "unnecessary-testing and transport-upcoding cases repriced the risk and "
        "put compliance at the center of every deal. The scaled reference "
        "operator (TridentCare) has been through both consolidation and "
        "financial restructuring, illustrating the model's density-driven upside "
        "and its thin-margin fragility. The forward story is aging-driven "
        "SNF/ALF census and the shift of diagnostics into lower-cost at-site "
        "settings, against transportation-rate and integrity-enforcement drag."),
    growth_levers=[
        GrowthLever(
            "SNF / ALF census growth",
            "The aging curve lifts the nursing-home and assisted-living resident "
            "base that generates bedside diagnostic demand.",
            "+~2-3%/yr census", "ILLUSTRATIVE"),
        GrowthLever(
            "Avoided-transport ROI",
            "Bedside studies replace ambulance transfers and ED visits — a real "
            "system saving that pulls diagnostics to the at-site setting.",
            "+ site shift", "ILLUSTRATIVE"),
        GrowthLever(
            "Route densification via M&A",
            "Acquiring adjacent operators and facility contracts raises patients "
            "per stop — the primary way scale improves the economics.",
            "+ density", "ILLUSTRATIVE"),
        GrowthLever(
            "Correctional & home-based demand",
            "Settings where transport is especially costly or risky value "
            "bedside diagnostics highly.",
            "+ new settings", "ILLUSTRATIVE"),
        GrowthLever(
            "Transportation-rate + integrity drag",
            "Cuts to the transportation/setup components and OIG/DOJ enforcement "
            "on necessity and transport billing subtract from thin margins.",
            "rate & integrity risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="SNF/ALF resident census × the at-site diagnostic conversion rate",
        analysis=(
            "The dominant demand driver is the post-acute resident base — the "
            "number of skilled-nursing, assisted-living, home-health, hospice, "
            "and correctional patients — multiplied by the share of their "
            "diagnostic needs met at the bedside rather than by transporting the "
            "patient out. The resident base grows steadily on the aging curve, "
            "and the conversion to at-site diagnostics rises because bringing "
            "the study to the patient avoids an ambulance transfer, an ED "
            "encounter, and the risk and disruption of moving a frail resident — "
            "a saving payers and facilities actively want. Demand is largely "
            "non-discretionary once a physician orders the study: it will be "
            "done, and the mobile provider captures it if it holds the facility "
            "contract and can route a technologist there efficiently. The "
            "throttle is not patient demand but medical-necessity documentation "
            "and route capacity — a study must be defensibly ordered, and the "
            "operator must have a technologist and van able to reach a dense "
            "enough cluster to make the trip pay."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Technologist labor", "the largest cost",
            "Traveling radiologic/ultrasound technologists are the core fixed "
            "cost; wages and supply cap how many routes can run.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Vehicles, fuel & fleet", "~15-25% of cost",
            "The van fleet, fuel, maintenance, and dispatch — the logistics "
            "chassis whose efficiency depends on route density.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Portable equipment (X-ray, US, cardiac)", "~10-20% of cost",
            "Portable modalities and their maintenance/depreciation — modest "
            "versus fixed imaging but real.", "ILLUSTRATIVE"),
        CostDriver(
            "Professional read (teleradiology/telecardiology)",
            "~10-15% of cost / revenue",
            "The remote interpretation, usually outsourced — the professional "
            "component the mobile provider does not perform itself.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing, compliance & denials", "~8-15% of net",
            "Complex transport/consolidated-billing coding, medical-necessity "
            "documentation, and a heavier compliance/denial drag than most "
            "diagnostics.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No public mobile-provider census is vendored, so state geography is "
        "omitted rather than fabricated. Qualitatively, mobile-diagnostics "
        "demand concentrates where the SNF/ALF and correctional populations "
        "are densest and where routes can be clustered — metro corridors with "
        "many facilities close together make the transportation economics work, "
        "while sparse rural geographies raise cost per patient. The CMS "
        "market-saturation, supplier-enrollment, and NPI-taxonomy connectors "
        "linked below give a real supplier-density read by county."),
)

register(REPORT)
