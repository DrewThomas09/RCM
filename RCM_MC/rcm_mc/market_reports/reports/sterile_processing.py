"""Sterile Processing — SPD outsourcing & surgical-instrument reprocessing.

Deals-only pattern (copied from hospice.py): no vendored national facility
file, so geography is honestly omitted and the report leans on the qualitative
deep sections + ``live_figures_from_dive("sterile_processing")`` for any SOURCED
corpus figures. The defining fact is that sterile processing is NON-REIMBURSED —
its cost is embedded in the surgical facility fee (OPPS / ASC payment) — so the
value proposition is risk transfer and OR throughput, and the growth engine is
the SPD-technician labor shortage plus the wave of state licensure mandates.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="sterile_processing",
    name="Sterile Processing",
    care_setting="Other services",
    naics="621999",
    one_line_def=(
        "The cleaning, decontamination, inspection, assembly, and "
        "sterilization of reusable surgical instruments and devices — the "
        "Sterile Processing Department every OR depends on — sold to hospitals "
        "and ASCs as managed on-site services, off-site regional reprocessing, "
        "instrument tracking/repair, and FDA-regulated single-use-device "
        "reprocessing."),
    tam_headline=TamHeadline(
        value=2.2, unit="$B", growth_pct=10.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US sterile-processing services + single-use-device "
            "reprocessing market (~$1.5-3.0B; the SUD-reprocessing sub-segment "
            "is ~$1.0-1.5B and growing fastest). No single published government "
            "total exists. Growth is the modeled composite of surgical-volume "
            "growth, ASC migration, the SPD labor shortage, and sustainability-"
            "driven SUD reprocessing."),
    ),
    executive_summary=[
        "It is non-reimbursed and invisible until it fails. Sterile processing "
        "cost is embedded in the surgical facility fee (OPPS / ASC payment), "
        "not separately paid — so this is a B2B managed-service sale whose value "
        "proposition is risk transfer and OR throughput, not reimbursement.",
        "The labor shortage plus state licensure is the growth engine. A chronic "
        "shortage of certified SPD technicians and a spreading wave of state "
        "SPD-technician licensure laws make it harder to staff the department "
        "in-house — pushing hospitals and ASCs to outsource.",
        "ASC migration reshapes the market. As surgery shifts to ambulatory "
        "centers that lack the scale to run a full SPD, ASCs become natural "
        "customers for managed on-site and off-site regional reprocessing.",
        "Single-use-device reprocessing is a different, higher-margin animal: "
        "FDA-regulated as manufacturing, sold on a cost-savings value-share, and "
        "tied to hospital cost-cutting and sustainability mandates — do not "
        "conflate it with managed-labor SPD.",
        "A single sterilization failure is a patient-safety event, a Joint "
        "Commission Immediate-Threat-to-Life citation, and a contract-ending "
        "event — so the quality/defect rate is the existential metric, and the "
        "sale is to the OR director, not supply chain.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Soiled instruments returned from the OR after a case",
            "Decontamination — manual + automated washer-disinfector cleaning",
            "Inspection & function testing (bioburden, damage, completeness)",
            "Assembly into trays/sets per the surgical preference cards",
            "Sterilization — steam autoclave, low-temp (H2O2/EtO) for heat-"
            "sensitive devices; biological-indicator verification",
            "Sterile storage + case-cart delivery back to the OR / ASC",
            "Instrument tracking, loaner-tray management, and repair as "
            "adjacencies",
        ],
        sites_of_care=[
            "Hospital central sterile / SPD (on-site, managed or in-house)",
            "Off-site regional reprocessing center (serving ASCs + hospitals)",
            "Ambulatory surgery centers (on-site micro-SPD or outsourced)",
            "Single-use-device reprocessing plant (FDA-regulated manufacturing)",
            "Endoscope reprocessing suites (ST91-governed, high-scrutiny)",
        ],
        money_flow=(
            "Sterile processing is not separately reimbursed — its cost is "
            "baked into the surgical facility fee the hospital or ASC earns "
            "under OPPS or the ASC payment system. Vendors are therefore paid by "
            "the facility under B2B contracts: managed on-site SPD (labor + "
            "management fee, hospital owns the equipment), full-department "
            "outsourcing (per-tray / per-case / fixed monthly), or off-site "
            "regional reprocessing (per-tray / per-instrument). Single-use-"
            "device reprocessing runs on a distinct model — the reprocessor "
            "collects used SUDs, resterilizes them under FDA clearance, and "
            "sells them back at a discount, sharing the savings with the "
            "hospital. Instrument tracking software, loaner-tray management, and "
            "surgical-instrument repair are recurring adjacencies layered on the "
            "same OR relationship."),
        key_players=(
            "A few scaled players over a fragmented services layer. STERIS is "
            "the gorilla (IMS instrument management, consumables, capital, and "
            "endoscopy via Cantel); Agiliti provides on-site SPD and medical-"
            "equipment management; SPD-360, Sterile Processing Technologies, and "
            "Synergy (now STERIS) run managed departments; Mobile Instrument and "
            "Alcyon handle repair; Censis (Fortive) is the tracking-software "
            "layer. In single-use-device reprocessing the leaders are Stryker "
            "Sustainability Solutions, Innovative Health, and Medline ReNewal. "
            "Beneath them, most hospitals still run SPD in-house — the "
            "outsourcing whitespace."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Managed on-site SPD services",
                    "labor + management — the core outsourcing model",
                    "ILLUSTRATIVE · modeled service-model mix"),
            Segment("Off-site / regional reprocessing",
                    "per-tray hubs — ASC-serving growth",
                    "ILLUSTRATIVE · modeled service-model mix"),
            Segment("Single-use-device (SUD) reprocessing",
                    "~$1.0-1.5B, fastest-growing, FDA-regulated",
                    "ILLUSTRATIVE · modeled sub-segment"),
            Segment("Instrument tracking + loaner management",
                    "recurring software/logistics adjacency",
                    "ILLUSTRATIVE · modeled adjacency"),
            Segment("Surgical-instrument repair",
                    "recurring services adjacency",
                    "ILLUSTRATIVE · modeled adjacency"),
        ],
        growth_drivers=[
            "Surgical case volume ~2-3%/yr — the underlying demand base",
            "ASC migration of surgery — new outsourcing customers without SPD "
            "scale",
            "SPD-technician labor shortage + turnover — the outsourcing trigger",
            "State SPD-technician licensure mandates — raise in-house cost, push "
            "outsourcing",
            "Sustainability + cost-cutting — SUD reprocessing adoption",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Hospital / health-system (managed-service contract)": 0.72,
            "ASC / surgery center (per-tray / off-site)": 0.18,
            "SUD reprocessing value-share / repair / other": 0.10,
        },
        rate_mechanics=[
            "No separate reimbursement — sterile-processing cost is embedded in "
            "the surgical facility fee (hospital OPPS or the ASC payment "
            "system); vendors are paid by the facility, not a payer.",
            "Managed on-site SPD — labor + management fee; the hospital owns the "
            "washers/autoclaves and the vendor runs the department.",
            "Full outsourcing — per-tray, per-case, or fixed monthly fee tied "
            "to surgical throughput.",
            "Off-site regional reprocessing — per-tray / per-instrument, often "
            "serving multiple ASCs from one hub.",
            "SUD reprocessing — the reprocessor sells FDA-cleared reprocessed "
            "single-use devices back at a discount and shares the savings with "
            "the hospital (a value-share, not a fee schedule).",
        ],
        reimbursement_risk=(
            "Because the service is not separately paid, the risk is not a "
            "payer rate cut — it is that the customer funds it from the facility "
            "fee and evaluates it on cost and reliability. The demand base "
            "moves with surgical volume, so a downturn in elective surgery or a "
            "site-of-service shift compresses tray volume. The offsetting "
            "protection is that the value proposition is risk transfer: a "
            "sterilization failure is a patient-safety and accreditation "
            "catastrophe, so hospitals under-staffed by the SPD-tech shortage "
            "increasingly pay to make that risk someone else's problem — and "
            "single-use-device reprocessing is defended by a hard-dollar cost-"
            "savings ROI that survives budget pressure."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("FDA regulation of single-use-device reprocessing",
                 "Third-party SUD reprocessors are regulated as device "
                 "manufacturers — 510(k) clearance and Quality System "
                 "Regulation apply — which is the barrier to entry and the moat "
                 "in that sub-segment.",
                 "https://www.fda.gov/medical-devices/reprocessing-single-use-devices/reprocessing-medical-devices"),
            Rule("ANSI/AAMI ST79 (steam sterilization) & ST91 (endoscopes)",
                 "The consensus standards that define competent reprocessing; "
                 "surveyors cite them, and adherence is the quality baseline "
                 "for any SPD service contract.",
                 "https://www.aami.org/"),
            Rule("Joint Commission + CMS Conditions of Participation surveys",
                 "SPD is a top survey-citation area (immediate-use steam "
                 "sterilization abuse, wet packs, BI failures); a citation can "
                 "be an Immediate Threat to Life and shut an OR.",
                 "https://www.jointcommission.org/"),
            Rule("State SPD-technician licensure / certification mandates",
                 "A spreading wave of state laws (NJ, NY, CT, TN and others) "
                 "requiring certified SPD technicians — raises in-house labor "
                 "cost and is the single biggest outsourcing tailwind.",
                 None),
            Rule("FDA duodenoscope / endoscope-reprocessing safety actions",
                 "The CRE/duodenoscope outbreak saga drove design changes and "
                 "intensified scrutiny of flexible-endoscope reprocessing — a "
                 "high-risk, high-oversight niche.",
                 "https://www.fda.gov/medical-devices/reprocessing-reusable-medical-devices/infections-associated-reprocessed-duodenoscopes"),
        ],
        policy_watch=[
            "Continued spread of state SPD-technician licensure laws",
            "FDA endoscope-reprocessing and single-use-duodenoscope actions",
            "EtO (ethylene oxide) sterilization emissions regulation — capacity "
            "and cost pressure on low-temp sterilization",
            "AAMI standard revisions (ST79/ST91) raising the compliance bar",
            "Sustainability/ESG mandates accelerating SUD reprocessing",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "A scaled top over a fragmented, mostly-in-house base. Managed SPD "
            "and reprocessing services are dominated by a handful of names, but "
            "the majority of hospitals still run sterile processing in-house — "
            "so the real competitive frontier is outsourcing penetration, not "
            "vendor-vs-vendor share. No vendored facility file exists for this "
            "services vertical, so a computed HHI is honestly omitted."),
        hhi_or_share=(
            "Qualitatively, STERIS is the scaled leader across instrument "
            "management, consumables, and endoscopy; Agiliti and specialized "
            "managed-SPD firms compete on the services layer; SUD reprocessing "
            "is a three-player field (Stryker, Innovative Health, Medline). The "
            "in-house department remains the largest 'competitor'."),
        consolidation=(
            "Active. STERIS built scale through acquisitions (Synergy Health, "
            "Cantel Medical); Agiliti was taken private by THL; Fortive acquired "
            "Censis; SUD reprocessors have consolidated around three leaders. "
            "The thesis is aggregating managed-service and repair capacity and "
            "cross-selling tracking, loaner management, and consumables into the "
            "same OR relationship."),
        pe_activity=(
            "Active and thesis-rich. The attributes PE likes: mission-critical, "
            "non-discretionary, recurring, with a labor-shortage-plus-licensure "
            "tailwind driving outsourcing penetration and technology (tracking, "
            "loaner logistics) to layer margin. Quality-of-earnings centers on "
            "the defect/quality record, contract retention, the surgical-volume "
            "exposure, and — for SUD reprocessing — the durability of the FDA-"
            "cleared product line and hospital savings-share economics."),
        notable_players=[
            "STERIS (IMS / Cantel)", "Agiliti", "SPD-360",
            "Sterile Processing Technologies", "Stryker Sustainability Solutions",
            "Innovative Health", "Medline ReNewal", "Censis (Fortive)",
            "Mobile Instrument", "Alcyon Health",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Tray turnaround time", "hours (case-driven)",
                "How fast a soiled set returns sterile — the metric that keeps "
                "the OR's first-case starts on time."),
            Kpi("Instrument defect / IUSS rate", "near-zero required",
                "Immediate-use-steam-sterilization abuse and missing/damaged "
                "instruments — the existential quality and survey metric."),
            Kpi("SPD-technician vacancy / turnover", "elevated",
                "The chronic shortage that both raises cost and drives the "
                "outsourcing decision."),
            Kpi("Cost per tray / per case", "contract-driven",
                "The unit the managed-service and off-site models are priced "
                "on."),
            Kpi("Tray / case volume", "tracks surgical volume",
                "Demand is surgical-volume-linked; ASC migration shifts where "
                "the trays are processed."),
            Kpi("Contract retention", "high when quality holds",
                "Sticky while defect-free; a single failure can end a "
                "relationship."),
            Kpi("EBITDA margin", "12-22% (services); higher for SUD",
                "Managed-labor SPD is labor-dominated; SUD reprocessing carries "
                "higher, regulated-value-share margins."),
        ],
        margin_profile=(
            "Managed-labor SPD margin is a throughput-and-labor story: SPD-"
            "technician labor dominates cost, so productivity (trays per FTE), "
            "vacancy/turnover, and the defect rate determine profitability, and "
            "the value is risk transfer more than cost arbitrage. Off-site "
            "regional reprocessing adds logistics but improves utilization by "
            "pooling ASC demand into one hub. Single-use-device reprocessing is "
            "the higher-margin, structurally different business — FDA-regulated "
            "manufacturing sold on a hard-dollar savings share — and it scales "
            "with hospital cost-cutting and sustainability rather than with the "
            "labor market. Across all models the defect rate is the margin: one "
            "sterilization failure erases the economics of a contract."),
    ),
    risks=[
        Risk("Sterilization failure / quality event", "High",
             "A bioburden miss is a patient-safety event, an Immediate-Threat-"
             "to-Life citation, and a contract-ending failure."),
        Risk("Surgical-volume / elective-procedure downturn", "Medium",
             "Tray demand is surgical-volume-linked; an elective slowdown "
             "compresses throughput and revenue."),
        Risk("SPD-technician labor shortage & wage inflation", "Medium",
             "The shortage is a tailwind for outsourcing demand but a headwind "
             "for the vendor's own labor-dominated cost base."),
        Risk("FDA / regulatory change in SUD reprocessing", "Medium",
             "Tighter 510(k)/QSR requirements or device-design changes can "
             "reset the reprocessable-device list and the savings economics."),
        Risk("EtO sterilization emissions regulation", "Medium",
             "Environmental limits on ethylene-oxide low-temp sterilization "
             "raise cost and constrain capacity for heat-sensitive devices."),
        Risk("In-sourcing / customer concentration", "Medium",
             "A large health-system customer can rebuild in-house SPD; contract "
             "concentration is a step-change risk."),
    ],
    diligence_questions=[
        "What is the defect/quality record — BI failures, IUSS rate, recalls, "
        "survey citations — across the contract base?",
        "What is the revenue split across managed on-site SPD, off-site "
        "reprocessing, SUD reprocessing, tracking, and repair?",
        "How exposed is tray volume to elective surgical volume and to the "
        "hospital-to-ASC site-of-service shift?",
        "What is the SPD-technician staffing model, vacancy/turnover, and wage "
        "trajectory, and how does the state-licensure map affect it?",
        "For SUD reprocessing: what is the FDA-cleared device list, the "
        "savings-share economics, and the collection/volume durability?",
        "What is contract retention, and what is the in-sourcing / re-bid "
        "history with large customers?",
        "What is the EtO / low-temp sterilization capacity exposure to "
        "emissions regulation?",
        "Who is the buyer at each account (OR director vs supply chain), and "
        "how sticky is the relationship?",
    ],
    insider_lens=[
        "The product is risk transfer, not cost savings. Sterile processing is "
        "non-reimbursed and invisible — until a sterilization failure becomes a "
        "patient-safety event and an Immediate-Threat-to-Life citation. "
        "Hospitals outsource to make that catastrophic tail someone else's "
        "problem, so the defect record is the whole equity story.",
        "The labor shortage is the thesis, and the state-licensure map is the "
        "clock. Hospitals cannot hire or retain certified SPD techs, and each "
        "new state licensure law raises the in-house cost — which is exactly "
        "why the outsourcing penetration curve is bending up. Underwrite the "
        "licensure geography, not just current volume.",
        "ASC migration is quietly reshaping the market. Surgery is moving to "
        "ambulatory centers too small to run a full SPD, creating a natural "
        "off-site and managed-service customer base — the growth is in the "
        "regional hub serving a cluster of ASCs, not the big-hospital "
        "department.",
        "SUD reprocessing is a manufacturing business wearing a services label. "
        "It is FDA-regulated as a manufacturer, sold on a hard-dollar savings "
        "share, and defended by sustainability mandates — its economics, "
        "moat, and risks are nothing like managed-labor SPD, and conflating "
        "them misprices the asset.",
        "The buyer is the OR, not procurement. The decision is made by the OR "
        "director and VP of perioperative services on the strength of on-time "
        "first-case starts and never running short a tray — a relationship and "
        "reliability sale that makes the incumbent sticky and the switching "
        "cost real.",
    ],
    connections=default_connections(
        "sterile_processing",
        deals_sector="sterile_processing",
        connectors=[
            ("provider_data_hospital_general",
             "CMS Provider Data — Hospital General Information (the SPD "
             "customer base)"),
            ("provider_data_asc_quality_facility",
             "CMS Provider Data — ASC quality/facility roll (surgical migration "
             "customers)"),
            ("openfda_device_510k",
             "openFDA 510(k) — reprocessed single-use-device clearances (the "
             "SUD-reprocessing moat)"),
            ("openfda_device_recall",
             "openFDA device recalls — sterilization/reprocessing recall signal"),
        ],
    ),
    sources=[
        Source("FDA — Reprocessing of single-use and reusable medical devices",
               "GOV",
               "https://www.fda.gov/medical-devices/reprocessing-single-use-devices/reprocessing-medical-devices"),
        Source("ANSI/AAMI ST79 & ST91 — steam sterilization and flexible-"
               "endoscope reprocessing standards", "INDUSTRY",
               "https://www.aami.org/"),
        Source("HSPA (Healthcare Sterile Processing Association) — SPD "
               "certification and workforce", "INDUSTRY",
               "https://myhspa.org/"),
        Source("The Joint Commission — sterilization & high-level disinfection "
               "survey standards", "INDUSTRY",
               "https://www.jointcommission.org/"),
        Source("FDA — infections associated with reprocessed duodenoscopes",
               "GOV",
               "https://www.fda.gov/medical-devices/reprocessing-reusable-medical-devices/infections-associated-reprocessed-duodenoscopes"),
        Source("PE Desk industry deep-dive + realized-deal corpus (sterile "
               "processing / surgical-support services)", "INTERNAL",
               "/diligence/tam-sam?template=sterile_processing"),
    ],
    live_figures=live_figures_from_dive("sterile_processing"),
    trends=(
        "Sterile processing spent decades as an invisible in-house cost center "
        "and is now an outsourcing market forming in real time. Three forces "
        "converged. First, a chronic and worsening shortage of certified SPD "
        "technicians left hospitals unable to staff their own departments. "
        "Second, a spreading wave of state SPD-technician licensure laws raised "
        "the cost and formalized the credential, tipping the make-vs-buy math "
        "toward outsourcing. Third, the migration of surgery to ambulatory "
        "centers created a new class of customers too small to run a full SPD, "
        "seeding demand for managed on-site micro-departments and off-site "
        "regional reprocessing hubs. Alongside the services layer, single-use-"
        "device reprocessing matured into a distinct, FDA-regulated, "
        "sustainability-driven cost-savings business. Consolidation followed — "
        "STERIS absorbing Synergy and Cantel, Agiliti taken private, Fortive "
        "buying Censis — leaving a scaled top over a still-mostly-in-house base. "
        "The trajectory is rising outsourcing penetration, ASC-hub growth, and "
        "SUD reprocessing expansion, all governed by the non-negotiable defect-"
        "rate that makes reliability the entire value proposition."),
    growth_levers=[
        GrowthLever(
            "SPD-technician labor shortage",
            "A chronic shortage of certified techs makes in-house staffing "
            "infeasible, converting departments into outsourcing customers.",
            "primary outsourcing driver", "ILLUSTRATIVE"),
        GrowthLever(
            "State licensure mandates",
            "New state laws requiring certified SPD technicians raise the "
            "in-house cost and formalize the credential — a regulatory tailwind "
            "for outsourcing.",
            "penetration step-up", "GOV"),
        GrowthLever(
            "ASC surgical migration",
            "Surgery moving to ambulatory centers without SPD scale creates "
            "off-site and managed-service demand at the regional-hub level.",
            "+ new customer base", "ILLUSTRATIVE"),
        GrowthLever(
            "SUD reprocessing adoption",
            "Hospital cost-cutting and sustainability mandates expand the "
            "single-use-device reprocessing base on a hard-dollar savings "
            "share.",
            "fastest sub-segment", "ILLUSTRATIVE"),
        GrowthLever(
            "Surgical case-volume growth",
            "The underlying demand base — tray volume tracks total surgical "
            "cases across hospital and ASC settings.",
            "+2-3%/yr", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Surgical case volume × outsourcing penetration",
        analysis=(
            "Demand is the product of two terms. The first is total surgical "
            "case volume — every case generates instrument trays that must be "
            "reprocessed — which grows with the aging population and the "
            "procedure mix and is redistributed as surgery migrates from "
            "hospitals to ASCs. The second, and the one that actually moves the "
            "addressable market for vendors, is outsourcing penetration: the "
            "share of that tray volume processed by a third party rather than "
            "in-house. Penetration is being pushed up by the certified-SPD-"
            "technician shortage and the spreading state licensure mandates, "
            "which together make in-house staffing costlier and harder — so the "
            "vendor market can grow well faster than surgical volume itself. "
            "Single-use-device reprocessing adds a parallel volume driver tied "
            "to hospital cost-savings and sustainability rather than case count."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "SPD-technician labor",
            "~50-65% of cost (services)",
            "The scarce, credentialed workforce that runs decontamination, "
            "assembly, and sterilization — the dominant cost and the constraint "
            "that drives the whole outsourcing market.", "ILLUSTRATIVE"),
        CostDriver(
            "Equipment, consumables & sterilant",
            "~15-25% of cost",
            "Washer-disinfectors, autoclaves, low-temp (H2O2/EtO) capacity, "
            "wraps, indicators, and enzymatic detergents.", "ILLUSTRATIVE"),
        CostDriver(
            "Quality, compliance & survey defense",
            "~5-10% of cost",
            "ST79/ST91 adherence, biological-indicator monitoring, "
            "documentation, and accreditation-survey readiness — non-negotiable "
            "given the failure tail.", "ILLUSTRATIVE"),
        CostDriver(
            "Logistics (off-site transport / loaner management)",
            "concentrated off-site",
            "Case-cart and tray transport for regional hubs and loaner-"
            "instrument coordination — the cost of pooling ASC demand.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Regulatory / manufacturing overhead (SUD reprocessing)",
            "concentrated in SUD",
            "510(k)/QSR quality-system compliance treats the SUD reprocessor as "
            "a manufacturer — the barrier to entry and a fixed cost of that "
            "sub-segment.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "Managed and off-site sterile processing follows surgical facilities, "
        "not a national vendor roster, so the meaningful geographic layer is "
        "twofold: the density of hospitals and ASCs (the customer base, "
        "mappable via the CMS provider connectors below) and the state SPD-"
        "technician licensure map — the states that have enacted certification "
        "mandates are where in-house cost rises fastest and outsourcing demand "
        "concentrates. No national sterile-processing-vendor facility file is "
        "vendored, so a computed facility breakdown is honestly omitted."),
)

register(REPORT)
