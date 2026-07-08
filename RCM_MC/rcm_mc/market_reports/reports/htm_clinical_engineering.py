"""HTM / Clinical Engineering — medical-device service & lifecycle management.

Deals-only deep-dive (no vendored facility file): maintenance, repair,
inspection, calibration, and lifecycle management of the hospital medical-device
installed base — delivered in-house, by OEMs, or by independent/multivendor
service organizations (ISOs), and increasingly bundled with device
cybersecurity. HTM is a hospital opex cost center, not a payer-reimbursed
service, so the qualitative sections are authored around the in-house/OEM/ISO
three-way structure, BMET labor, OEM access control, right-to-repair, and the
§524B cyber mandate. Geography is honestly omitted; ``cms_trend`` and
``state_breakdown`` are unset and the renderer shows the note.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="htm_clinical_engineering",
    name="HTM / Clinical Engineering",
    care_setting="Other services",
    naics="811210",
    one_line_def=(
        "Maintenance, repair, inspection, calibration, and lifecycle "
        "management of the hospital medical-device installed base — imaging, "
        "patient monitors, infusion pumps, ventilators, lab, and surgical "
        "equipment — delivered in-house, by OEMs, or by independent/multivendor "
        "service organizations (ISOs), and increasingly bundled with "
        "medical-device cybersecurity."),
    tam_headline=TamHeadline(
        value=12.0, unit="$B", growth_pct=7.5, basis_label="ILLUSTRATIVE",
        basis_note=(
            "HTM is a hospital operating-budget cost center, not a "
            "payer-reimbursed service, so there is no CMS line item. The ~$10-15B "
            "US clinical-engineering-services figure is an industry estimate "
            "keyed to the medical-equipment installed base (roughly a "
            "low-single-digit percent of equipment acquisition value); growth "
            "is the modeled composite of installed-base expansion, the "
            "outsourcing shift off OEM, and the device-cybersecurity adjacency."),
    ),
    executive_summary=[
        "HTM is a hospital opex cost center, not a payer-reimbursed service. It "
        "is funded from the health system's operating budget as a share of the "
        "medical-equipment capital base — so demand tracks the installed base "
        "and the CFO's cost-reduction agenda, not CMS rates.",
        "Three delivery models compete for the same work: in-house biomed "
        "departments, OEM service contracts (GE/Philips/Siemens — high-margin "
        "and sticky), and independent/multivendor ISOs that promise 15-30% "
        "savings by consolidating OEM contracts under one vendor. The PE thesis "
        "is the ISO/multivendor shift away from OEM contracts.",
        "The economics are labor plus coverage. A BMET (biomedical equipment "
        "technician) workforce services a device census under uptime SLAs; "
        "density (devices per tech, sites per region) and first-time-fix rate "
        "drive margin, and a national BMET shortage caps growth.",
        "Cybersecurity turned a wrench business into an IT business. Connected "
        "medical devices (IoMT) are now the hospital's largest unmanaged attack "
        "surface; device inventory, patching, and vulnerability management — "
        "propelled by the FDA §524B premarket cyber mandate and legacy-device "
        "risk — are a fast-growing, higher-value HTM adjacency.",
        "Right-to-repair is the regulatory swing factor. OEMs restrict access "
        "to service keys, parts, and manuals; ISOs and hospitals push right to "
        "repair and the FDA has studied third-party servicing — the outcome "
        "directly sets the addressable pool the independents can serve.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Capital equipment acquired (or inherited at go-live)",
            "Inventory & onboarding — nameplate capture, risk classification",
            "Scheduled maintenance / inspection / calibration (PM)",
            "Demand repair (CM) + parts sourcing & OEM escalation",
            "Uptime / SLA reporting to the health system",
            "Cybersecurity inventory, patching & vulnerability management",
            "Capital-replacement planning, end-of-life & disposition",
        ],
        sites_of_care=[
            "Hospital biomed shop (the general device census)",
            "Imaging service — high-value CT/MRI/nuclear (OEM-dominated)",
            "OR / procedural equipment service",
            "Central depot repair + remote monitoring / help desk",
        ],
        money_flow=(
            "The health system pays for HTM out of operating budget — as "
            "internal biomed labor, as OEM service contracts (a fixed annual "
            "fee per device/modality), or as a fee to an ISO/multivendor "
            "provider (a managed-services contract priced as a percentage of "
            "the equipment base, a fixed per-bed/per-device fee, or a "
            "gain-share). The ISO's margin is the spread between the "
            "consolidated contract price and its blended cost of BMET labor, "
            "parts, and OEM escalation — won by substituting in-house or "
            "third-party service for premium OEM contracts. There is no "
            "third-party medical payer; the customer is the hospital CFO."),
        key_players=(
            "OEMs — GE HealthCare, Philips, and Siemens Healthineers hold the "
            "incumbent imaging/high-complexity service base. Multivendor ISOs — "
            "TriMedx (Ascension-founded), Agiliti, Sodexo HTM, Crothall "
            "Healthcare Technology Solutions (Compass), and Renovo Solutions — "
            "compete for whole-hospital programs. Device-cybersecurity "
            "specialists (Claroty/Medigate, Ordr, Asimily, Cynerio) partner "
            "into HTM. A long tail of regional biomed shops and in-house "
            "departments fills the rest."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Imaging equipment service (CT/MRI/nuclear)",
                    "highest-value, OEM-dominated",
                    "ILLUSTRATIVE · industry estimate"),
            Segment("General biomedical (monitors, pumps, ventilators)",
                    "the multivendor core",
                    "ILLUSTRATIVE · industry estimate"),
            Segment("Lab & surgical equipment service",
                    "specialized service book",
                    "ILLUSTRATIVE · industry estimate"),
            Segment("Medical-device cybersecurity / IoMT security",
                    "the fastest-growing adjacency",
                    "ILLUSTRATIVE · industry estimate"),
            Segment("In-house vs. outsourced split",
                    "the outsourcing whitespace",
                    "ILLUSTRATIVE · industry estimate"),
        ],
        growth_drivers=[
            "Installed-base growth & rising device complexity",
            "Hospital cost pressure driving multivendor outsourcing off OEM",
            "IoMT cybersecurity mandates (FDA §524B)",
            "BMET labor shortage (constrains supply, raises price)",
            "Right-to-repair access expanding the serviceable pool",
            "Aging equipment / deferred capital extending service life",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "In-house biomed (hospital opex)": 0.45,
            "OEM service contracts": 0.30,
            "Independent / multivendor ISO": 0.20,
            "Cybersecurity / IT budget": 0.05,
        },
        rate_mechanics=[
            "Managed-services / full-service contract — the ISO charges a fixed "
            "annual fee (per device, per bed, or a percentage of equipment "
            "acquisition value) to manage the whole program; the spread over "
            "blended cost is margin.",
            "OEM service contract — a premium fixed annual fee per "
            "modality/device with parts and OEM engineers bundled; sticky and "
            "high-margin for the OEM.",
            "Time-and-materials / per-repair — demand repairs billed by labor "
            "hour plus parts for non-contract work.",
            "Gain-share / cost-savings guarantee — ISOs guarantee a percentage "
            "reduction versus prior OEM spend and share the savings.",
            "Cybersecurity subscription — device-inventory and "
            "vulnerability-management software/services, a recurring adjacency.",
            "Parts & depot — imaging 'glass' (tubes, coils, detectors), boards, "
            "and depot repair as a margin and access chokepoint the OEM "
            "controls.",
        ],
        reimbursement_risk=(
            "The risk is not payer denials — it is contract structure and "
            "access. Full-service and gain-share contracts transfer "
            "equipment-uptime and parts-cost risk to the ISO; a bad parts year "
            "(imaging glass, an aging fleet) or an SLA miss erodes margin and "
            "triggers penalties. The strategic risk is OEM control: OEMs "
            "restrict service keys, diagnostic software, parts, and training, "
            "and can re-price or lock down access — the FDA's third-party-"
            "servicing review and the right-to-repair fight determine how much "
            "of the installed base the independents can legally and practically "
            "service. Hospital capital cycles swing volume: deferred replacement "
            "extends service demand, while a capital surge can shift work back "
            "to OEM warranty. Shares shown are delivery/funding channels and "
            "are ILLUSTRATIVE."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("CMS Hospital CoP — equipment maintenance + Alternative "
                 "Equipment Maintenance (42 CFR 482.41; S&C 14-07)",
                 "Lets hospitals use risk-based (AEM) maintenance schedules for "
                 "eligible equipment (excluding certain critical/imaging/laser "
                 "devices) — the compliance frame HTM programs operate in.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-482/subpart-C/section-482.41"),
            Rule("Joint Commission — Medical Equipment Management "
                 "(EC.02.04.01 / EC.02.04.03)",
                 "Accreditation standards for the equipment inventory, PM "
                 "completion rates, and high-risk device management — the "
                 "survey exposure that gates a program.",
                 "https://www.jointcommission.org/"),
            Rule("FDA — servicing vs. remanufacturing of medical devices",
                 "The FDA framework distinguishing unregulated third-party "
                 "'servicing' from regulated 'remanufacturing' — the swing rule "
                 "for how much an ISO can legally do.",
                 "https://www.fda.gov/medical-devices/medical-device-servicing/remanufacturing-medical-devices"),
            Rule("FDA §524B cyber-device requirements (Consolidated "
                 "Appropriations Act, 2023)",
                 "Premarket cybersecurity obligations for 'cyber devices' "
                 "(SBOM, patching) — the mandate driving the IoMT-security "
                 "adjacency and legacy-device remediation demand.",
                 "https://www.fda.gov/medical-devices/digital-health-center-excellence/cybersecurity"),
            Rule("Right-to-repair (state laws + FTC 'Nixing the Fix' report)",
                 "Access to parts, tools, and manuals — the determinant of the "
                 "independent-service addressable pool.",
                 "https://www.ftc.gov/reports/nixing-fix-ftc-report-congress-repair-restrictions"),
        ],
        policy_watch=[
            "FDA remanufacturing guidance finalization",
            "Spread of right-to-repair legislation to medical devices",
            "§524B enforcement and legacy-device cyber-risk remediation",
            "CMS AEM scope (which devices are eligible for risk-based PM)",
            "OEM parts/access litigation and antitrust attention",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "A three-way structure: OEMs hold the imaging/high-complexity base, "
            "a handful of national multivendor ISOs compete for whole-hospital "
            "programs, and a long tail of regional/independent biomed shops and "
            "in-house departments fills the rest. Consolidating at the ISO "
            "layer; the independent/in-house tail is unrostered, so a precise "
            "HHI is honestly omitted."),
        hhi_or_share=(
            "OEMs plus a few national ISOs (TriMedx, Agiliti, Sodexo HTM, "
            "Crothall, Renovo) lead; the independent/in-house tail is "
            "fragmented and unrostered — a precise HHI is omitted rather than "
            "fabricated."),
        consolidation=(
            "Active multivendor roll-up — TriMedx, Agiliti (a public roll-up of "
            "Universal Hospital Services and others), Sodexo HTM, Crothall/"
            "Compass, and Renovo buying regional biomed and imaging-service "
            "firms and adding cybersecurity. OEMs defend via bundled service "
            "and access control."),
        pe_activity=(
            "A live PE theme: build a national multivendor platform that "
            "displaces OEM contracts with cost-savings guarantees, add "
            "device-cybersecurity, and roll up regional imaging-service and "
            "biomed shops. Agiliti, TriMedx, and Renovo trace PE lineage. "
            "Quality-of-earnings centers on contract retention, OEM-access "
            "durability, and BMET labor, not device count."),
        notable_players=[
            "TriMedx", "Agiliti", "Sodexo HTM",
            "Crothall Healthcare Technology Solutions", "Renovo Solutions",
            "GE HealthCare / Philips / Siemens Healthineers (OEM service)",
            "Claroty (Medigate) / Ordr / Asimily (IoMT security)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Devices per BMET", "800-1,200",
                "Labor productivity and coverage density — the core margin "
                "lever; you can win contracts faster than you can staff them."),
            Kpi("Equipment uptime / SLA attainment", "contractual",
                "Contract penalties and renewals ride on it."),
            Kpi("First-time-fix rate", "the cost leak",
                "Truck-rolls and OEM escalation are where cost hides; a high "
                "first-time-fix rate is the efficiency signal."),
            Kpi("Cost-of-service ratio (% of equipment acquisition value)",
                "3-7%",
                "The benchmark ISOs must beat to win a whole-hospital program."),
            Kpi("Contract mix (full-service vs. T&M)", "risk-defining",
                "Full-service transfers uptime/parts risk to the vendor; T&M "
                "keeps it with the hospital."),
            Kpi("OEM parts/labor pass-through share", "access-controlled",
                "The cost the ISO can't fully manage because the OEM controls "
                "the parts and keys."),
        ],
        margin_profile=(
            "ISO/multivendor EBITDA margins come from BMET labor density, "
            "first-time-fix, and substituting in-house or third-party service "
            "for OEM contracts. Imaging service (high parts/glass cost) is "
            "lower-margin and OEM-access-constrained, while general biomed and "
            "cybersecurity are higher-margin. Scale spreads depot, engineering, "
            "and parts purchasing. The swing factors are labor productivity, "
            "parts access, and contract structure; ranges are ILLUSTRATIVE."),
    ),
    risks=[
        Risk("OEM access / parts & software lockout", "High",
             "OEM control of service keys, diagnostics, and parts determines "
             "the serviceable pool and the parts cost the ISO can't manage."),
        Risk("BMET labor shortage & wage inflation", "High",
             "A national biomed-technician shortage caps capacity and pressures "
             "margin; hiring lags contract wins."),
        Risk("Contract retention / OEM re-bundling", "Medium",
             "Health systems or OEMs re-take programs at renewal, and a capital "
             "surge can shift work back to OEM warranty."),
        Risk("Right-to-repair / FDA remanufacturing outcome", "Medium",
             "The regulatory swing on how much the independents may legally "
             "service."),
        Risk("Imaging parts-cost (glass) volatility", "Medium",
             "Tubes, coils, and detectors on full-service contracts expose the "
             "vendor to parts-cost spikes."),
        Risk("Cybersecurity liability", "Medium",
             "As HTM takes on device security, breach and remediation exposure "
             "rises."),
    ],
    diligence_questions=[
        "What is the contract retention rate and the renewal calendar — what is "
        "at risk in the next 24 months?",
        "What is the full-service-versus-T&M mix and the SLA-penalty history?",
        "What is the OEM parts/access dependency by modality, especially "
        "imaging?",
        "What is the BMET headcount, vacancy rate, and devices-per-tech?",
        "What is the imaging-service parts-cost trend (glass) on full-service "
        "contracts?",
        "What is the cybersecurity attach rate and capability, and how is it "
        "priced?",
        "What is the cost-of-service ratio versus benchmark, and what savings "
        "have gain-share contracts actually delivered?",
        "What is the customer concentration by IDN, and the AEM-program / Joint "
        "Commission survey history?",
    ],
    insider_lens=[
        "The whole thesis is 'take it off the OEM.' Independents win by "
        "consolidating premium OEM contracts and guaranteeing 15-30% savings — "
        "so the durability of that arbitrage, and the OEM's counter-moves on "
        "access and price, are the deal, not device volume.",
        "OEM access control is the invisible margin. Whoever holds the service "
        "keys, parts, and diagnostic software holds the P&L; an ISO's ability "
        "to service imaging depends on access it doesn't own — exactly what "
        "right-to-repair and the FDA remanufacturing debate will decide.",
        "BMET labor is the binding constraint. You can win contracts faster "
        "than you can hire biomeds; devices-per-tech and first-time-fix — not "
        "the sales pipeline — set how much of the book you can actually service "
        "profitably.",
        "Cybersecurity is quietly the growth story. The connected-device attack "
        "surface turned biomed into IT; the HTM vendor that owns the device "
        "inventory is positioned to own patching and vulnerability "
        "management — a higher-margin, stickier, §524B-mandated adjacency the "
        "pure-wrench shops miss.",
        "Imaging service is a different, worse business than general biomed. "
        "Glass — tubes, coils, detectors — is expensive, OEM-controlled, and on "
        "full-service contracts the vendor eats the parts risk; an "
        "imaging-heavy book looks like revenue but carries OEM-dependent, "
        "low-margin cost.",
    ],
    connections=default_connections(
        "htm_clinical_engineering",
        deals_sector="htm",
        connectors=[
            ("provider_data_hospital_general",
             "CMS Hospital General Information — the health-system customer base"),
            ("openfda_device_recall",
             "openFDA device recalls — the events that drive service demand"),
            ("openfda_device_event",
             "openFDA device adverse events (MAUDE) — maintenance/failure signal"),
            ("provider_data_medical_equipment_suppliers",
             "CMS Medicare medical-equipment suppliers (adjacent device estate)"),
            ("bls_qcew_industry_area",
             "BLS QCEW — electronic & precision equipment repair (NAICS 811210/811219)"),
        ],
    ),
    sources=[
        Source("CMS — Hospital Conditions of Participation, equipment "
               "maintenance (42 CFR 482.41) + AEM policy (S&C 14-07)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-482/subpart-C/section-482.41"),
        Source("FDA — Remanufacturing / servicing of medical devices "
               "(report to Congress + guidance)", "GOV",
               "https://www.fda.gov/medical-devices/medical-device-servicing/remanufacturing-medical-devices"),
        Source("FDA — §524B cyber-device cybersecurity (Consolidated "
               "Appropriations Act, 2023) + premarket guidance", "GOV",
               "https://www.fda.gov/medical-devices/digital-health-center-excellence/cybersecurity"),
        Source("FTC — 'Nixing the Fix' report to Congress on repair "
               "restrictions", "GOV",
               "https://www.ftc.gov/reports/nixing-fix-ftc-report-congress-repair-restrictions"),
        Source("AAMI — Association for the Advancement of Medical "
               "Instrumentation, HTM/BMET standards & benchmarking", "INDUSTRY",
               "https://www.aami.org/"),
        Source("PE Desk industry deep-dive (deals-only; service contracts are "
               "private) + realized-deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=htm_clinical_engineering"),
    ],
    live_figures=live_figures_from_dive("htm_clinical_engineering"),
    trends=(
        "HTM has moved from an in-house cost center toward a consolidating, "
        "outsourced, and increasingly digital services market. The central "
        "trajectory is the multivendor shift: independent service organizations "
        "displace premium OEM contracts by consolidating a hospital's whole "
        "device fleet under one vendor with a 15-30% cost-savings guarantee, "
        "and PE-backed platforms (Agiliti, TriMedx, Renovo, and others) have "
        "rolled up regional biomed and imaging-service firms to scale that "
        "model. Two forces now reshape it. First, cybersecurity: connected "
        "medical devices became the hospital's largest unmanaged attack "
        "surface, and the FDA's §524B mandate plus legacy-device risk turned "
        "device inventory, patching, and vulnerability management into a "
        "higher-value, recurring HTM adjacency. Second, the OEM-access fight: "
        "right-to-repair legislation and the FDA's servicing-versus-"
        "remanufacturing framework will decide how much of the installed base "
        "the independents can legally and practically service. Underneath it "
        "all, a national BMET labor shortage caps how fast any of this can "
        "scale."),
    growth_levers=[
        GrowthLever(
            "Multivendor / ISO outsourcing shift (off OEM)",
            "Independents consolidate OEM contracts under a savings guarantee — "
            "the primary market-share engine.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Medical-device cybersecurity (IoMT)",
            "Device inventory, patching, and vulnerability management — a "
            "higher-margin, recurring, §524B-mandated adjacency.",
            "fastest adjacency", "ILLUSTRATIVE"),
        GrowthLever(
            "Installed-base growth & device complexity",
            "More and more-complex connected devices per bed expand the "
            "serviceable census.",
            "demand base", "ILLUSTRATIVE"),
        GrowthLever(
            "Right-to-repair access expansion",
            "Broader access to parts, keys, and manuals enlarges the pool the "
            "independents can legally service.",
            "pool expansion", "ILLUSTRATIVE"),
        GrowthLever(
            "Regional biomed / imaging roll-up",
            "Consolidating regional shops spreads depot, engineering, and "
            "parts-purchasing scale.",
            "consolidation", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="The hospital medical-device installed base × the outsourcing "
               "(off-OEM) shift",
        analysis=(
            "HTM demand is the product of two things: how many medical devices "
            "sit in hospitals, and how that service work is sourced. The "
            "installed base grows structurally — more monitors, pumps, imaging, "
            "and connected devices per bed, each more complex and more "
            "software-laden than the last — which mechanically expands the "
            "serviceable census and the cybersecurity surface. The faster "
            "lever, though, is the sourcing shift: every dollar a health system "
            "moves from a premium OEM contract to an in-house or multivendor "
            "program is addressable revenue for the independents, and cost "
            "pressure keeps pushing that shift. The two compound — a larger, "
            "more complex base being progressively pulled off the OEM — while "
            "the binding constraint is BMET labor: the work exists faster than "
            "the technicians to do it, which is why devices-per-tech and "
            "first-time-fix, not the pipeline, govern how much of the demand "
            "actually converts to profitable revenue."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "BMET labor & benefits", "~45-55% of cost",
            "The dominant cost and the capacity ceiling; a national "
            "biomedical-technician shortage drives wage inflation.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Parts & OEM escalation (imaging glass)", "~20-30% of cost",
            "Tubes, coils, detectors, and boards — much of it OEM-controlled "
            "and the biggest risk on full-service imaging contracts.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Depot, tools, test equipment & engineering", "infrastructure",
            "Central depot repair, calibration gear, and engineering support "
            "that scale spreads.", "ILLUSTRATIVE"),
        CostDriver(
            "Cybersecurity software / platform", "growing adjacency cost",
            "Device-inventory and vulnerability-management tooling — a cost "
            "that is also a higher-margin revenue line.", "ILLUSTRATIVE"),
        CostDriver(
            "Travel & logistics (multi-site coverage)", "coverage cost",
            "Servicing dispersed sites under uptime SLAs — minimized by "
            "regional route density.", "ILLUSTRATIVE"),
    ],
)

register(REPORT)
