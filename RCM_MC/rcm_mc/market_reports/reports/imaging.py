"""Imaging — freestanding outpatient diagnostic imaging (radiology centers / IDTFs).

Deals-only deep-dive (the IMV imaging-center census is proprietary; no national
all-payer facility roll is vendored, so geography is omitted rather than
fabricated and the SOURCED layer is the sector's radiology deal history).
The qualitative sections are authored around the mechanic that governs this
subsector: the split between the TECHNICAL component (the scan) and the
PROFESSIONAL component (the radiologist's read), and the site-of-service
differential that pays a hospital MORE than a freestanding center for the
identical study — the exact inverse of the ASC arbitrage. Consumes
``imaging_deep_dive()`` for SOURCED corpus deal figures.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="imaging",
    name="Imaging",
    care_setting="Dx & labs",
    naics="621512",
    one_line_def=(
        "Freestanding outpatient diagnostic imaging — X-ray, ultrasound, "
        "mammography, CT, MRI, PET, and nuclear medicine — delivered in "
        "independent imaging centers and Independent Diagnostic Testing "
        "Facilities (IDTFs). Each study splits into a TECHNICAL component (the "
        "scan on the equipment, a facility/practice-expense fee) and a "
        "PROFESSIONAL component (the radiologist's interpretation), billable "
        "globally or separately."),
    tam_headline=TamHeadline(
        value=40.0, unit="$B", growth_pct=5.5, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US freestanding / outpatient diagnostic-imaging services revenue "
            "is commercial-heavy and not a single published figure; ~$40B is "
            "the modeled composite (much larger if hospital-based imaging is "
            "included). The GOV anchor is Medicare Part B imaging spend "
            "(~$8-10B, MPFS/MedPAC, directional) in the segments below. Growth "
            "is the modeled composite of aging-driven volume, advanced-imaging "
            "mix shift, and rate/site-of-service drag."),
    ),
    executive_summary=[
        "Every study is two businesses. The technical component (TC) is the "
        "scan — a capital-intensive, fixed-cost machine business where "
        "utilization is everything; the professional component (PC, the -26 "
        "modifier) is the radiologist's read — a labor business teleradiology "
        "can nationalize. A freestanding center usually bills global (TC+PC); "
        "understanding which half you are buying is the first question.",
        "The site-of-service differential runs BACKWARDS versus the ASC. "
        "Medicare pays a hospital outpatient department (OPPS) more than a "
        "freestanding center (MPFS) for the identical scan, so the arbitrage is "
        "health systems buying freestanding centers to re-bill them as "
        "provider-based (higher) — and site-neutral payment is the tail risk "
        "that compresses it.",
        "Advanced imaging (MRI, CT, PET) is the money. It is a minority of "
        "volume but the majority of revenue and nearly all the capital "
        "intensity; plain film and ultrasound are high-volume, low-dollar "
        "fillers. Modality mix and machine throughput drive the P&L.",
        "Commercial rate and prior authorization decide the outcome. "
        "Commercial payers reimburse a large multiple of Medicare but gate "
        "advanced imaging through radiology benefit managers (eviCore, Carelon/"
        "AIM) — the silent volume tax that denials and peer-to-peer friction "
        "impose is a first-order diligence item.",
        "Self-referral is the demand engine and the regulatory fault line. "
        "Imaging bolted onto ortho, cardiology, and oncology practices via the "
        "in-office ancillary services exception drives captive utilization — "
        "GAO and MedPAC have repeatedly flagged self-referred imaging.",
        "Fragmentation under a few scaled platforms: RadNet, US Radiology "
        "Specialists, SimonMed, RAYUS, Akumin, and Solis lead, but thousands of "
        "independent single- and multi-modality centers and hospital-owned "
        "sites make the acquirable pool deep.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Ordering physician orders a study (with a clinical indication)",
            "Benefit check + prior authorization / RBM approval (advanced imaging)",
            "Scheduling + patient prep (contrast, screening, safety checklist)",
            "Technologist acquires the images on the modality (TC)",
            "Radiologist interprets and dictates the report (PC)",
            "Report routed to the ordering physician; critical results called",
            "Global or split TC/PC claim submitted; RBM/medical-necessity edits",
            "Accreditation + AUC/quality reporting maintained for advanced modalities",
        ],
        sites_of_care=[
            "Freestanding multi-modality imaging center (the platform asset)",
            "Independent Diagnostic Testing Facility (IDTF — Medicare enrollment)",
            "In-office ancillary imaging inside a specialty practice (self-referral)",
            "Hospital outpatient department (OPPS — the higher-paid site)",
            "Mobile / portable units (see Mobile Diagnostics)",
            "The reading room — increasingly remote (see Teleradiology)",
        ],
        money_flow=(
            "A freestanding center bills the study either GLOBALLY (technical + "
            "professional in one claim) or SPLIT — the technical component for "
            "the scan and, with the -26 modifier, the professional component "
            "for the read. Medicare pays under the Physician Fee Schedule "
            "(MPFS): the non-facility rate carries a practice-expense RVU that "
            "funds the equipment, room, tech, and supplies, plus a work RVU for "
            "the radiologist and a malpractice RVU. Hospital outpatient imaging "
            "is instead paid under OPPS, which for the same code is typically "
            "HIGHER — the reverse of the ASC discount. Multiple studies in one "
            "session are cut by the Multiple Procedure Payment Reduction (MPPR) "
            "on both the TC and PC. Commercial payers pay a contracted rate that "
            "is a multiple of Medicare but require prior authorization through a "
            "radiology benefit manager. The economic engine is filling a "
            "high-fixed-cost MRI/CT schedule with well-reimbursed studies against "
            "a largely fixed equipment and staffing base."),
        key_players=(
            "On the facility (technical) side: RadNet (the largest freestanding "
            "operator, Northeast/California/Mid-Atlantic), US Radiology "
            "Specialists (Welsh, Carson), SimonMed, RAYUS Radiology (the former "
            "Center for Diagnostic Imaging), Akumin, and Solis Mammography, plus "
            "extensive hospital-system-owned imaging. On the professional "
            "(read) side, Radiology Partners is the dominant physician "
            "aggregator, with LucidHealth and regional groups; the two sides "
            "increasingly converge. Equipment OEMs (GE HealthCare, Siemens "
            "Healthineers, Philips, Canon) and the RBMs (eviCore, Carelon) sit "
            "adjacent and shape the economics."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicare Part B imaging spend",
                    "~$8-10B (directional)",
                    "GOV · MPFS / MedPAC imaging (directional)"),
            Segment("Advanced imaging (MRI / CT / PET)",
                    "minority of volume, majority of $",
                    "ILLUSTRATIVE · modeled modality revenue mix"),
            Segment("Plain film / X-ray + ultrasound",
                    "high volume, low $ per study",
                    "ILLUSTRATIVE · modeled modality mix"),
            Segment("Women's imaging (screening + diagnostic mammography)",
                    "screening-mandated, high-throughput segment",
                    "ILLUSTRATIVE · industry segment, directional"),
            Segment("Freestanding vs hospital-outpatient split",
                    "hospital paid more for the same study",
                    "GOV · MPFS vs OPPS site differential"),
        ],
        growth_drivers=[
            "Aging population lifts scan volume (oncology, MSK, cardiac, neuro)",
            "Advanced-imaging mix shift (MRI/CT/PET) — higher $ per study",
            "New indications & screening expansion (lung CT, prostate MRI, CCTA)",
            "AI-assisted throughput and reads improving machine utilization",
            "Rate + site-of-service policy (MPFS cuts, site-neutral) as the drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.50,
            "Medicare / MA": 0.35,
            "Medicaid / self-pay / other": 0.15,
        },
        rate_mechanics=[
            "Technical vs Professional split — TC (the scan) and PC (the read, "
            "-26 modifier); a freestanding center bills global or splits, and "
            "the two components trade on entirely different economics.",
            "Medicare Physician Fee Schedule (MPFS) — RVU-based; the "
            "non-facility (freestanding) practice-expense RVU funds the "
            "equipment and technologist. Hospital imaging is paid under OPPS, "
            "typically higher for the same code.",
            "Multiple Procedure Payment Reduction (MPPR) — multiple studies in "
            "a session are discounted on both TC and PC.",
            "Prior authorization / radiology benefit managers (eviCore, "
            "Carelon/AIM) — commercial advanced imaging is gated; denials and "
            "peer-to-peer are a real volume tax.",
            "Deficit Reduction Act of 2005 (DRA) legacy cap — freestanding TC "
            "is capped at the lower of MPFS or OPPS, the historic cut that "
            "reshaped freestanding economics.",
            "Appropriate Use Criteria (AUC) / Clinical Decision Support — the "
            "MPFS AUC mandate for advanced imaging was paused and then rescinded "
            "by CMS; consultation is now voluntary.",
            "MIPPA accreditation — advanced diagnostic imaging must be "
            "accredited (ACR / IAC / TJC) to bill Medicare for the TC.",
        ],
        reimbursement_risk=(
            "Three pressures compound. First, MPFS is a fixed budget-neutral "
            "pool: the annual conversion-factor cuts and RVU rebalancing "
            "chronically pressure imaging rates, and technical-component "
            "reimbursement has trended down for two decades (DRA, MPPR, "
            "equipment-utilization assumptions). Second, the site-of-service "
            "differential is a policy time bomb in reverse — the whole "
            "provider-based premium disappears if CMS moves to site-neutral "
            "payment, which would reprice hospital-acquired centers. Third, "
            "commercial rate durability and RBM friction: payers pay well but "
            "steer, deny, and prior-authorize advanced imaging aggressively, so "
            "realized yield per order is well below the contracted rate. "
            "Self-referred imaging is a standing target for utilization "
            "controls."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("IDTF performance standards (42 CFR 410.33)",
                 "The 17 Medicare supplier standards an Independent Diagnostic "
                 "Testing Facility must meet to enroll and bill the technical "
                 "component — supervision, equipment, and quality gates.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-410/section-410.33"),
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets imaging RVUs, the conversion factor, MPPR, and equipment-"
                 "utilization assumptions — the technical and professional "
                 "prices for freestanding imaging.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Physician self-referral law (Stark) + in-office ancillary "
                 "services exception (42 CFR 411.355(b))",
                 "The exception that lets a specialty practice own and refer to "
                 "its own imaging — the engine of self-referred advanced imaging "
                 "and a standing MedPAC/GAO/OIG focus.",
                 "https://www.cms.gov/medicare/regulations-guidance/physician-self-referral"),
            Rule("MIPPA advanced diagnostic imaging accreditation",
                 "CT, MRI, nuclear medicine, and PET technical components must "
                 "be accredited (ACR / IAC / TJC) to bill Medicare.",
                 "https://www.cms.gov/medicare/regulations-guidance/advanced-diagnostic-imaging-accreditation"),
            Rule("Mammography Quality Standards Act (MQSA) + FDA final rule",
                 "FDA-enforced facility certification and, since 2024, mandatory "
                 "breast-density notification — a compliance and volume driver "
                 "for women's imaging.",
                 "https://www.fda.gov/radiation-emitting-products/mammography-quality-standards-act-and-program"),
            Rule("Appropriate Use Criteria program (rescinded)",
                 "The MPFS AUC/CDS mandate for advanced imaging was paused and "
                 "then withdrawn — watch for any revival as a utilization "
                 "control.", None),
        ],
        policy_watch=[
            "Site-neutral payment (freestanding MPFS vs hospital OPPS) — the "
            "central swing factor for provider-based imaging value",
            "Annual MPFS conversion-factor cuts and imaging RVU rebalancing",
            "RBM prior-authorization scope and any gold-carding relief",
            "Revival of Appropriate Use Criteria / clinical decision support",
            "FDA AI/CADe clearance pathway and reimbursement for AI reads",
            "Self-referral / in-office ancillary imaging scrutiny",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Thousands of freestanding imaging centers plus extensive "
            "hospital-owned and in-office ancillary imaging; a handful of "
            "scaled platforms lead but hold a minority of national volume. The "
            "acquirable pool is the independent single- and multi-modality "
            "center long tail plus tuck-ins around anchor markets. No national "
            "all-payer facility census is vendored, so a facility-count HHI is "
            "honestly omitted."),
        hhi_or_share=(
            "No dominant national owner on the technical side — RadNet, US "
            "Radiology, SimonMed, RAYUS, and Akumin lead but fragment quickly "
            "below them. On the professional side Radiology Partners is the "
            "largest aggregator. Concentration is best read market-by-market, "
            "where a scaled operator can hold a genuine local share."),
        consolidation=(
            "Two parallel roll-ups. On the facility side, PE-backed platforms "
            "(US Radiology under Welsh Carson, RAYUS, Akumin) and the public "
            "RadNet consolidate centers and JV with health systems. On the "
            "professional side, Radiology Partners assembled the largest "
            "physician group. Health systems simultaneously acquire "
            "freestanding centers to capture provider-based billing — a third "
            "consolidator with a payment-arbitrage motive."),
        pe_activity=(
            "Highly active across both halves. Sponsors back facility platforms "
            "(Welsh Carson/US Radiology), professional aggregators (New "
            "Enterprise Associates and others in Radiology Partners), and "
            "women's-imaging and teleradiology roll-ups. Quality-of-earnings "
            "centers on payer-contract durability, RBM denial rates, machine "
            "utilization, radiologist supply/retention, and how much revenue "
            "rides on the provider-based site differential."),
        notable_players=[
            "RadNet", "US Radiology Specialists (Welsh, Carson)",
            "SimonMed Imaging", "RAYUS Radiology", "Akumin",
            "Solis Mammography", "Radiology Partners (professional)",
            "Health-system imaging JVs",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Scans / machine / day", "MRI 10-16, CT 15-25+",
                "Machine throughput on a fixed-cost modality is the core "
                "operating lever; an idle MRI is a fixed-cost bleed."),
            Kpi("Net revenue / study (blended)", "$60 X-ray → $400-1,200+ MRI",
                "Wildly modality-dependent; the blend follows modality and "
                "payer mix — advanced imaging carries the dollars."),
            Kpi("Commercial mix", "45-60% of revenue",
                "The biggest value driver — commercial pays a multiple of "
                "Medicare, but RBM prior auth gates advanced studies."),
            Kpi("Advanced-imaging share of volume", "20-35%",
                "MRI/CT/PET are a minority of studies but the majority of "
                "revenue and nearly all the capital intensity."),
            Kpi("Equipment utilization", ">65-75% target",
                "Empty modality time is unrecoverable; scheduling density and "
                "extended hours are the efficiency levers."),
            Kpi("Imaging-center EBITDA margin (mature)", "20-30%+",
                "High operating leverage on the equipment chassis when "
                "well-utilized and commercial-rich; thin when Medicare-heavy or "
                "under-booked."),
        ],
        margin_profile=(
            "An imaging center is a high-fixed-cost equipment chassis — the "
            "MRI/CT scanners (lease or depreciation), the rooms, technologists, "
            "and the reading arrangement are largely fixed, so contribution "
            "margin steps up sharply with each additional advanced study and "
            "each commercial case. A mature multi-modality center with strong "
            "MRI/CT throughput, a healthy commercial book, and controlled RBM "
            "denials runs low-20s to 30%+ EBITDA; a plain-film-heavy or "
            "under-booked center on the same cost base is far thinner. The "
            "single biggest swing after utilization is whether the center bills "
            "freestanding (MPFS) or provider-based (OPPS) — the same scan can "
            "pay materially more under a hospital's tax ID."),
    ),
    risks=[
        Risk("Site-neutral payment reform", "High",
             "Equalizing freestanding MPFS and hospital OPPS rates would erase "
             "the provider-based premium many centers and health-system JVs "
             "are valued on."),
        Risk("MPFS technical-component rate erosion", "High",
             "Budget-neutral conversion-factor cuts, MPPR, and equipment-"
             "utilization assumptions chronically pressure imaging TC rates."),
        Risk("RBM prior authorization + commercial rate compression", "High",
             "Advanced-imaging denials, peer-to-peer friction, and rate cuts "
             "pull realized yield well below the contracted rate."),
        Risk("Radiologist supply and read-cost inflation", "Medium",
             "A tight radiologist labor market raises the professional-component "
             "cost and can bottleneck turnaround; teleradiology mitigates but "
             "at a price."),
        Risk("Capital intensity + equipment obsolescence", "Medium",
             "Scanners are expensive and depreciate; refresh capex and "
             "contrast-media supply shocks (e.g. the 2022 iodinated-contrast "
             "shortage) hit throughput and cash."),
        Risk("Self-referral / utilization-control policy", "Medium",
             "In-office ancillary imaging is a standing MedPAC/GAO target; "
             "tightening the exception would cut captive volume."),
    ],
    diligence_questions=[
        "What is the modality mix and revenue split (X-ray/US vs MRI/CT/PET), "
        "and what is throughput per machine versus capacity?",
        "What share of revenue is billed provider-based (OPPS) versus "
        "freestanding (MPFS), and how exposed is it to site-neutral reform?",
        "What is the payer mix, what are commercial rates as a multiple of "
        "Medicare, and how durable are the top contracts?",
        "What are RBM prior-authorization approval and denial rates by payer, "
        "and what is realized yield per order after denials?",
        "Is the professional read employed, contracted, or teleradiology, and "
        "what is the radiologist supply/retention picture?",
        "How much volume is self-referred from affiliated specialty practices, "
        "and how exposed is it to Stark/utilization-control changes?",
        "What is the equipment age, lease/owned mix, and refresh capex "
        "schedule, and is every advanced modality accredited (ACR/IAC)?",
        "What is the local competitive density (hospital, other freestanding, "
        "in-office) and the center's share of the referral base?",
    ],
    insider_lens=[
        "The site-of-service arbitrage is inverted. Unlike an ASC, where "
        "freestanding is cheaper, imaging pays a HOSPITAL more than a "
        "freestanding center for the identical scan — so the value play is "
        "flipping a center to provider-based billing under a system's tax ID, "
        "and the tail risk is site-neutral reform taking that premium back.",
        "You are buying a machine schedule, not a building. The MRI and CT "
        "utilization curve is the business; an extra evening block or a faster "
        "protocol drops almost entirely to contribution margin, while an idle "
        "scanner bleeds fixed cost every hour it is dark.",
        "The RBM denial rate is the hidden P&L line. A great gross rate sheet "
        "means little if eviCore or Carelon deny or delay a third of advanced "
        "orders — realized revenue per referral, not the contract rate, is the "
        "number that matters.",
        "The read can leave the building. Because the professional component "
        "splits cleanly from the technical, teleradiology lets a national group "
        "arbitrage radiologist labor and subspecialty coverage — which is why "
        "the professional side (Radiology Partners) consolidated separately "
        "from the centers.",
        "Half of advanced imaging is captive. Ortho, cardiology, and oncology "
        "practices that own their own MRI/CT under the in-office ancillary "
        "exception self-refer — great for volume, but it means the demand is "
        "only as durable as the referral relationship and the Stark exception.",
    ],
    connections=default_connections(
        "imaging",
        deals_sector="radiology",
        extra_pages=[
            ("/industry/imaging",
             "Industry deep-dive — radiology deal history + structure"),
        ],
        connectors=[
            ("provider_data_imaging_efficiency_hospital",
             "CMS Outpatient Imaging Efficiency — appropriate-use / follow-up "
             "measures by facility"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician/supplier utilization by HCPCS — imaging TC/PC "
             "volume & allowed amounts"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — radiology, IDTF, and portable-imaging enrollment"),
            ("open_payments_ownership_payments_2024",
             "Open Payments — physician ownership & investment (self-referral / "
             "JV screen)"),
            ("cms_open_data_market_saturation_cbsa",
             "CMS Market Saturation — provider/supplier density by CBSA"),
            ("census_acs_cbsa_profile",
             "Census ACS — CBSA demographics for imaging-demand mapping"),
        ],
    ),
    sources=[
        Source("MedPAC — Report to Congress, physician & imaging services "
               "(MPFS, site-of-service differential)", "GOV",
               "https://www.medpac.gov/"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "MPPR, equipment utilization)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("IDTF performance standards (42 CFR 410.33)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-410/section-410.33"),
        Source("GAO — Medicare self-referral of advanced imaging services "
               "(utilization findings)", "GOV",
               "https://www.gao.gov/products/gao-12-966"),
        Source("FDA — Mammography Quality Standards Act (MQSA) & 2024 breast-"
               "density final rule", "GOV",
               "https://www.fda.gov/radiation-emitting-products/mammography-quality-standards-act-and-program"),
        Source("American College of Radiology — accreditation & practice "
               "parameters", "INDUSTRY", "https://www.acr.org/"),
        Source("PE Desk industry deep-dive (radiology) + realized-deal corpus",
               "INTERNAL", "/diligence/tam-sam?template=imaging"),
    ],
    live_figures=live_figures_from_dive("imaging"),
    trends=(
        "Imaging spent two decades absorbing technical-component rate cuts — the "
        "Deficit Reduction Act of 2005, the Multiple Procedure Payment "
        "Reduction, and ever-tightening equipment-utilization assumptions — "
        "which pushed volume out of hospitals into lower-cost freestanding "
        "centers and then triggered a wave of consolidation as scale became "
        "the only defense against rate erosion. Two counter-currents now shape "
        "the trajectory. First, health systems reversed part of the migration "
        "by acquiring freestanding centers to capture provider-based (OPPS) "
        "billing, making the site-of-service differential — and the threat of "
        "site-neutral reform — the central valuation swing. Second, the "
        "professional read separated from the scan: Radiology Partners and "
        "teleradiology aggregators nationalized interpretation against a "
        "tightening radiologist labor market. Underneath, demand keeps rising "
        "on aging, new indications (lung-cancer CT screening, prostate MRI, "
        "coronary CTA), and an advanced-imaging mix shift that lifts revenue "
        "per study — while AI-assisted triage and reporting begin to lift "
        "throughput and reads. The forward tension is entirely policy and "
        "payer: MPFS cuts and RBM prior authorization on one side, aging "
        "volume and higher-acuity modalities on the other."),
    growth_levers=[
        GrowthLever(
            "Aging-driven scan volume",
            "The 65+ population lifts oncology, MSK, cardiac, and neuro imaging "
            "volume across all modalities.",
            "+~3%/yr volume", "ILLUSTRATIVE"),
        GrowthLever(
            "Advanced-imaging mix shift (MRI / CT / PET)",
            "Higher-acuity studies replace plain film, raising revenue per "
            "study even when unit volume is flat.",
            "+ revenue/study", "ILLUSTRATIVE"),
        GrowthLever(
            "New indications & screening expansion",
            "Lung-cancer low-dose CT, prostate MRI, coronary CTA, and "
            "theranostic PET open new addressable volume.",
            "+ addressable set", "GOV"),
        GrowthLever(
            "AI-assisted throughput and reads",
            "Worklist triage, protocol automation, and CADe lift machine and "
            "radiologist productivity — a utilization lever.",
            "+ productivity", "ILLUSTRATIVE"),
        GrowthLever(
            "Rate + site-of-service drag",
            "MPFS conversion-factor cuts, MPPR, and any move to site-neutral "
            "payment compress the technical-component and provider-based "
            "premium.",
            "policy risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Ordered-study volume × the advanced-imaging mix shift",
        analysis=(
            "The dominant demand driver is the number of physician-ordered "
            "studies and their migration toward higher-dollar advanced "
            "modalities. Two forces compound: an aging, higher-comorbidity "
            "population lifts the underlying order rate for oncology staging, "
            "MSK, cardiac, and neurologic imaging; and clinical practice keeps "
            "substituting MRI/CT/PET for plain film and opening new screening "
            "indications (lung-cancer CT, prostate MRI, coronary CTA), which "
            "raises revenue per order even where unit counts are flat. The "
            "throttle on that volume is the payer, not the patient: radiology "
            "benefit managers gate advanced imaging with prior authorization, "
            "so realized volume is the ordered volume net of denials and "
            "abandoned peer-to-peers. Self-referred imaging inside specialty "
            "practices adds captive volume that is durable only as long as the "
            "referral relationship and the in-office ancillary exception hold."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Equipment (MRI/CT depreciation or lease) + facility",
            "~25-35% of cost",
            "The fixed chassis — scanner capital and the room. It sets the "
            "utilization break-even and drives refresh capex.", "ILLUSTRATIVE"),
        CostDriver(
            "Technologist & clinical labor", "~20-30% of cost",
            "Registered technologists per modality plus front-office and "
            "scheduling staff — largely fixed by hours open.", "ILLUSTRATIVE"),
        CostDriver(
            "Professional read (radiologist / teleradiology)",
            "~15-25% of cost / revenue",
            "The interpretation, whether employed, contracted, or "
            "teleradiology — a labor cost that rises with radiologist "
            "scarcity.", "ILLUSTRATIVE"),
        CostDriver(
            "Contrast media, film/PACS, and supplies", "~5-10% of cost",
            "Iodinated/gadolinium contrast (subject to supply shocks), PACS/"
            "reporting software, and consumables.", "ILLUSTRATIVE"),
        CostDriver(
            "Billing, RBM/prior-auth, and compliance", "~8-12% of cost",
            "Authorization management, denials/appeals, accreditation, and "
            "MQSA/AUC compliance overhead — heavier than most facility models.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national all-payer imaging-center facility file is vendored (the "
        "IMV census is proprietary), so state geography is omitted rather than "
        "fabricated. Qualitatively, freestanding-imaging density tracks "
        "commercial-payer richness and Certificate-of-Need regimes: non-CON "
        "states (Texas, Arizona, much of the West) saw denser freestanding "
        "build-out, while CON states concentrate ownership and protect "
        "incumbents. The CMS market-saturation and NPI-taxonomy connectors "
        "linked below give a real supplier-density read by CBSA."),
)

register(REPORT)
