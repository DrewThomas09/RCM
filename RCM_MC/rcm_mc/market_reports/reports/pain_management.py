"""Pain Management — interventional-pain physician practices.

Deals-only deep-dive (no vendored interventional-pain facility file). Pain
management splits into two archetypes with very different risk profiles: the
PE-attractive INTERVENTIONAL model (epidural/facet injections, radiofrequency
ablation, spinal-cord stimulator implants, kyphoplasty — procedure/ASC/OBL-heavy)
and the opioid-legacy MEDICATION-MANAGEMENT model (reputational, DEA, and False-
Claims exposure). The qualitative sections are authored around interventional
procedure economics and ASC/OBL site-of-service, the Local Coverage Determination
(LCD) utilization caps that govern injection frequency, device cost on SCS
implants, the urine-drug-testing / toxicology-lab fraud legacy, and the opioid
regulatory overhang. Consumes ``pain_management_deep_dive()`` for SOURCED corpus
deal figures (this sector has realized deals in our corpus).
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="pain_management",
    name="Pain Management",
    care_setting="Physician services",
    naics="621111",
    one_line_def=(
        "Physician practices treating chronic pain — split between "
        "INTERVENTIONAL pain (epidural/facet injections, radiofrequency "
        "ablation, spinal-cord stimulators, kyphoplasty, performed in office "
        "suites, OBLs, and ASCs) and MEDICATION management (the opioid-legacy "
        "model) — reimbursed under the Medicare Physician Fee Schedule plus "
        "ASC/facility fees and device payment, and tightly governed by Local "
        "Coverage Determinations."),
    tam_headline=TamHeadline(
        value=5.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled addressable pool for US interventional-pain physician "
            "services (injections, RFA, neurostimulation, vertebral "
            "augmentation) — a directional composite, not a filed figure. The "
            "underlying disease burden is vastly larger: the Institute of "
            "Medicine estimated the total US economic cost of chronic pain at "
            "~$560-635B including lost productivity (see market-size segments, "
            "ACADEMIC). Growth is the modeled composite of aging/MSK prevalence, "
            "site-of-service migration, and rate updates net of LCD tightening."),
    ),
    executive_summary=[
        "There are two pain-management businesses, and only one is investable. "
        "The INTERVENTIONAL model — injections, radiofrequency ablation, spinal-"
        "cord stimulators, kyphoplasty — is procedure- and device-driven with "
        "ASC/OBL facility-fee capture, and is what PE buys. The MEDICATION-"
        "management model is the opioid-legacy practice that carries DEA, "
        "reputational, and False-Claims risk — the part diligence must screen "
        "OUT.",
        "Site of service is the value lever. Moving injections, RFA, and even "
        "spinal-cord-stimulator trials/implants into a physician-owned office-"
        "based lab or ASC captures the technical/facility fee the hospital "
        "outpatient department used to earn — the same economic arbitrage that "
        "drove the GI and ortho roll-ups, applied to interventional pain.",
        "Local Coverage Determinations (LCDs) are the governing constraint, not "
        "the fee schedule alone. Medicare Administrative Contractors cap how "
        "many epidural and facet injections and RFAs a patient can receive per "
        "year and require diagnostic blocks before ablation — so utilization, "
        "not just rate, sets the ceiling, and LCD tightening directly compresses "
        "volume.",
        "Urine drug testing is the specialty's original sin. In-office "
        "toxicology labs were a massive historical overbilling and kickback "
        "vector (definitive vs presumptive testing, standing orders), producing "
        "a wave of OIG/DOJ False-Claims cases — a UDT-heavy revenue mix is a "
        "red flag, and its quality is a core diligence question.",
        "The risks are payment, device, and compliance specific: repeated CMS "
        "cuts to injection/RFA reimbursement, LCD utilization tightening, "
        "spinal-cord-stimulator device cost against fixed procedure rates, the "
        "opioid/DEA/PDMP overhang, and the UDT/toxicology and OBL-ownership "
        "Stark/AKS exposure — set against a durable aging-and-MSK demand base "
        "and an opioid-crisis push toward non-opioid interventional therapy.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Referral (PCP/ortho/spine/ED) or self-presentation → pain consult",
            "Evaluation + imaging review (MRI/CT) → diagnosis of pain generator",
            "Conservative care — medication management, PT referral, "
            "interventional plan",
            "Diagnostic/therapeutic injections — epidural steroid, facet/medial-"
            "branch blocks, joint and nerve blocks",
            "Ablative/neuromodulation procedures — radiofrequency ablation, "
            "spinal-cord-stimulator trial and implant, intrathecal pump, "
            "kyphoplasty",
            "Monitoring — for any opioid therapy: PDMP checks, urine drug "
            "testing, controlled-substance agreements",
            "Billing — professional (MPFS) + technical/facility (office/OBL/ASC) "
            "+ device (SCS/pump) + UDT/toxicology",
        ],
        sites_of_care=[
            "Pain-management office / clinic (E&M + in-office injections)",
            "Office-based lab (OBL) / procedure suite — physician-owned "
            "injection/RFA/SCS capacity (the thesis)",
            "Ambulatory surgery center (ASC) — pain codes on the ASC-CPL, "
            "including SCS implants",
            "Hospital outpatient department (HOPD) — the site procedures migrate "
            "FROM",
            "In-office / reference toxicology lab (urine drug testing) — the "
            "compliance-sensitive ancillary",
        ],
        money_flow=(
            "An interventional pain practice stacks professional fees, technical/"
            "facility fees, device payment, and toxicology ancillary revenue. "
            "The physician bills E&M and procedure codes off the Medicare "
            "Physician Fee Schedule; when the injection, radiofrequency ablation, "
            "or spinal-cord-stimulator procedure is done in a physician-owned "
            "office-based lab or ASC, the practice also captures the technical/"
            "facility payment the hospital outpatient department used to earn — "
            "the core site-of-service arbitrage. Neurostimulation and pump "
            "procedures carry separate, substantial DEVICE payment (the implant "
            "can be the largest single line in the case). For any patient on "
            "chronic opioid therapy, urine drug testing generates toxicology "
            "revenue — historically an enormous and heavily-abused ancillary "
            "(definitive vs presumptive testing), now closely watched. What "
            "governs volume is not just the fee: Local Coverage Determinations "
            "cap injection and RFA frequency and set prerequisites (e.g. "
            "diagnostic blocks before ablation), so medical policy and prior "
            "authorization determine how much of the schedule is payable. "
            "Commercial payers pay a multiple of Medicare."),
        key_players=(
            "The independent segment is fragmented among interventional-pain "
            "groups and multispecialty spine/MSK practices, with PE-backed "
            "platforms assembling the interventional model (National Spine & "
            "Pain Centers, various regional roll-ups) alongside spine/ortho "
            "groups that internalize pain. Hospital systems employ a share for "
            "spine-service-line referral. The device makers loom large — "
            "spinal-cord-stimulator and pump manufacturers (Medtronic, Boston "
            "Scientific, Abbott, Nevro) drive a big part of the procedural "
            "economics and physician relationships. Adjacent: toxicology-lab "
            "operators, PT and DME/bracing ancillaries, and the drugmakers on "
            "the medication-management side."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("US chronic-pain total economic cost (incl. productivity)",
                    "~$560-635B",
                    "ACADEMIC · Institute of Medicine, Relieving Pain in "
                    "America (2011)"),
            Segment("US adults with chronic pain", "~50M+ adults",
                    "GOV · CDC / NHIS chronic-pain prevalence"),
            Segment("Interventional-pain physician-services slice",
                    "a fraction of the burden",
                    "ILLUSTRATIVE · modeled addressable share"),
            Segment("Spinal-cord-stimulator implant market (US)",
                    "large device-driven segment",
                    "ILLUSTRATIVE · industry SCS device-market estimates, "
                    "directional"),
            Segment("Pain codes on the ASC Covered Procedures List",
                    "expanding (incl. SCS)",
                    "GOV · CMS ASC-CPL additions"),
        ],
        growth_drivers=[
            "Aging + musculoskeletal/spine-pain prevalence — the demographic "
            "base",
            "Opioid-crisis shift to non-opioid interventional & neuromodulation "
            "therapy",
            "Site-of-service migration to OBLs/ASCs — capturing the facility fee",
            "Neuromodulation (SCS) technology adoption — device-driven procedure "
            "growth",
            "ASC-CPL additions (incl. SCS implants) — widening the ambulatory "
            "set",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.45,
            "Commercial": 0.42,
            "Workers' comp / auto / other": 0.13,
        },
        rate_mechanics=[
            "Medicare Physician Fee Schedule — professional and in-office "
            "technical fees for injections, RFA, and neuromodulation; repeatedly "
            "cut for spinal injections and facet/RFA codes.",
            "Local Coverage Determinations (LCDs) — MAC medical policy caps "
            "epidural/facet injection and RFA frequency and sets prerequisites "
            "(diagnostic blocks before ablation) — the true volume ceiling.",
            "ASC / OBL facility payment — pain codes (including SCS implants) on "
            "the ASC Covered Procedures List paid a packaged facility fee; "
            "office-based labs bill the technical component.",
            "Device / neurostimulator payment — spinal-cord stimulators and "
            "intrathecal pumps carry separate, substantial device payment so "
            "implant-heavy cases are not underwater.",
            "Toxicology / urine drug testing — presumptive vs definitive testing "
            "codes; historically overbilled, now capped and audit-heavy.",
            "Workers'-comp and auto/PIP fee schedules — a meaningful non-Medicare "
            "payer set for pain, with state-specific rules and (for LOP/lien) "
            "collection risk.",
            "Commercial multiples + prior authorization — commercial pays "
            "MPFS-plus multiples but manages injections, RFA, and SCS via prior "
            "auth and medical-necessity criteria.",
        ],
        reimbursement_risk=(
            "Pain management is one of the most policy-exposed physician "
            "specialties. CMS has repeatedly cut reimbursement for spinal "
            "injections and facet/RFA procedures, and — more importantly — Local "
            "Coverage Determinations set hard utilization limits on how many "
            "injections and ablations a patient may receive and require "
            "diagnostic blocks before RFA, so a MAC policy revision can compress "
            "volume overnight regardless of the fee. The device economics cut "
            "both ways: neurostimulation is a growth engine, but the implant can "
            "be the largest line in the case, and fixed procedure rates against "
            "rising device cost squeeze the margin. The ancillary that made pain "
            "practices rich — in-office urine drug testing — is now a liability: "
            "definitive-testing overbilling, standing orders, and lab kickbacks "
            "produced a wave of OIG/DOJ False-Claims settlements, and a UDT-heavy "
            "book is a repricing and enforcement risk. Layer on the opioid/DEA/"
            "PDMP overhang, OBL/ASC-ownership Stark and AKS exposure, prior-"
            "authorization friction, and workers'-comp/lien collection risk, and "
            "the reimbursement picture is a genuine non-opioid demand tailwind "
            "wrapped around unusually dense compliance and medical-policy risk."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Medicare Physician Fee Schedule (annual Final Rule)",
                 "Sets professional/technical RVUs and the conversion factor for "
                 "injections, RFA, and neuromodulation — repeatedly cut for "
                 "pain codes.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("Local Coverage Determinations (LCDs) — MAC pain medical "
                 "policy",
                 "Cap injection/RFA frequency and set prerequisites — the actual "
                 "volume ceiling on interventional pain.",
                 "https://www.cms.gov/medicare-coverage-database/"),
            Rule("Hospital OPPS / ASC Payment System + ASC Covered Procedures "
                 "List",
                 "Sets OBL/ASC facility payment and which pain codes (incl. SCS) "
                 "are ambulatory-payable — the site-of-service arbitrage.",
                 "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
            Rule("Anti-Kickback Statute + Stark (toxicology labs, OBL/ASC "
                 "ownership)",
                 "Governs urine-drug-testing lab arrangements and physician "
                 "ownership of OBLs/ASCs — the specialty's densest compliance "
                 "zone.",
                 "https://oig.hhs.gov/compliance/safe-harbor-regulations/"),
            Rule("CDC Clinical Practice Guideline for Prescribing Opioids "
                 "(2022) + DEA / state PDMP",
                 "Governs the medication-management side — opioid prescribing "
                 "standards, DEA registration, and prescription-drug-monitoring "
                 "checks.",
                 "https://www.cdc.gov/opioids/healthcare-professionals/prescribing/guideline/"),
            Rule("No Surprises Act (out-of-network protections)",
                 "Limits balance billing at facilities/ASCs and out-of-network "
                 "pain arrangements.",
                 "https://www.cms.gov/nosurprises"),
        ],
        policy_watch=[
            "MPFS cuts to injection/facet/RFA codes and conversion-factor "
            "erosion",
            "LCD tightening on injection/RFA frequency and RFA prerequisites — "
            "the volume swing",
            "ASC-CPL additions (more SCS/neuromodulation ambulatory) and site-"
            "neutral debate",
            "OIG/DOJ toxicology-lab and UDT False-Claims enforcement",
            "Opioid prescribing policy, DEA telemedicine controlled-substance "
            "rules, and PDMP mandates",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Pain management is highly fragmented among independent "
            "interventional-pain physicians, multispecialty spine/MSK groups, "
            "and hospital-employed pain physicians, with PE-backed platforms "
            "consolidating the interventional model. The acquirable pool is the "
            "independent interventional group with owned OBL/ASC capacity and a "
            "clean, non-opioid-dependent revenue mix — the medication-heavy "
            "practices are largely un-buyable on compliance grounds."),
        hhi_or_share=(
            "No dominant national owner and no vendored pain-management facility "
            "file, so operator concentration is honestly not measured here. The "
            "concentration that matters commercially is on the DEVICE side — a "
            "few neurostimulator/pump makers (Medtronic, Boston Scientific, "
            "Abbott, Nevro) shape the procedural economics and physician "
            "relationships."),
        consolidation=(
            "PE has actively rolled up interventional pain (National Spine & "
            "Pain Centers and various regional platforms), and spine/ortho "
            "groups increasingly internalize pain as a service line. The model "
            "centralizes the MSO back office, builds OBL/ASC procedural capacity, "
            "adds neuromodulation programs, and — carefully — manages or divests "
            "the toxicology and medication-management exposure. The opioid and "
            "UDT legacy makes reputation and compliance screening a gating step "
            "that has slowed and repriced deals."),
        pe_activity=(
            "An active but reputationally-loaded thesis: the interventional, "
            "non-opioid, ASC/OBL-capturing model is attractive, but buyers must "
            "screen out opioid-mill and toxicology-fraud exposure. Diligence "
            "centers on the revenue mix (interventional vs medication vs UDT), "
            "LCD/utilization durability, SCS device economics, OBL/ASC-ownership "
            "Stark/AKS structure, and any opioid-related legal or DEA history. "
            "Our corpus carries realized pain-management deals — see the SOURCED "
            "figures above and the deal history linked below."),
        notable_players=[
            "National Spine & Pain Centers",
            "Regional interventional-pain platforms",
            "Multispecialty spine/MSK groups (internalized pain)",
            "Hospital-employed pain / spine service lines",
            "Neurostimulator makers (Medtronic, Boston Scientific, Abbott, "
            "Nevro)",
            "Toxicology-lab operators", "Workers'-comp pain networks",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Interventional procedure volume & OBL/ASC utilization",
                "cases / procedure room",
                "The fixed-cost procedural chassis; idle room time is lost, "
                "non-recoverable margin."),
            Kpi("Revenue mix (interventional vs medication vs UDT)",
                "interventional-heavy is the goal",
                "A high interventional / low opioid-and-toxicology mix is both "
                "higher-quality and lower-risk."),
            Kpi("Spinal-cord-stimulator implant volume", "trials → implants",
                "High-value neuromodulation cases — the growth engine — with a "
                "trial-to-permanent conversion funnel."),
            Kpi("Device cost (% of SCS/pump case net revenue)", "large share",
                "The neurostimulator/pump can approach the largest line in the "
                "case on a fixed rate — the implant squeeze."),
            Kpi("Toxicology / UDT revenue (% of total)", "keep low",
                "A high UDT share is a compliance and repricing red flag "
                "(definitive-testing overbilling legacy)."),
            Kpi("Payer mix (commercial / WC vs Medicare)",
                "commercial & WC lift blend",
                "Commercial and workers'-comp pay multiples of Medicare, so mix "
                "drives realized yield."),
            Kpi("Platform EBITDA margin", "high-teens to 20s (illustrative)",
                "Richer where interventional/OBL/SCS volume is built out; "
                "thinner and riskier on a medication/UDT book."),
        ],
        margin_profile=(
            "Interventional pain's margin is procedural and site-of-service "
            "capture: the value is in owning the OBL/ASC where injections, RFA, "
            "and neurostimulation happen and earning the technical/facility fee "
            "the hospital used to keep, plus the professional fee. Neuro"
            "modulation adds high-value cases but the device can eat a large "
            "share of case net revenue on a fixed rate, so implant volume and "
            "device pricing must be managed. The historical margin turbocharger "
            "— in-office urine drug testing — is now a liability rather than an "
            "asset; the durable, defensible margin comes from a clean "
            "interventional mix, not toxicology. The two dominant risks to the "
            "margin are medical policy (MPFS cuts and LCD utilization caps that "
            "compress procedure volume) and compliance (UDT/toxicology and OBL-"
            "ownership exposure) — which is why quality-of-revenue matters more "
            "here than in almost any other physician specialty."),
    ),
    risks=[
        Risk("LCD utilization tightening + MPFS injection/RFA cuts", "High",
             "MAC coverage policy caps injection/RFA frequency and CMS has "
             "repeatedly cut the codes — medical policy, not rate alone, sets "
             "the volume ceiling."),
        Risk("Toxicology / UDT False-Claims & kickback exposure", "High",
             "In-office urine drug testing is a historical overbilling/kickback "
             "vector with a wave of OIG/DOJ cases; a UDT-heavy book is a "
             "repricing and enforcement risk."),
        Risk("Opioid / DEA / reputational overhang (medication model)", "High",
             "The opioid-legacy practice carries DEA, PDMP, litigation, and "
             "reputational risk that can taint an otherwise interventional "
             "asset."),
        Risk("Spinal-cord-stimulator device cost on fixed rates", "Medium",
             "The implant can approach the largest line in the case; fixed "
             "procedure rates against device cost squeeze neuromodulation "
             "margin."),
        Risk("OBL/ASC-ownership Stark & AKS exposure", "Medium",
             "Physician-owned procedure suites and lab arrangements depend on "
             "the in-office ancillary exception and safe-harbor compliance."),
        Risk("Workers'-comp / auto / lien collection risk", "Medium",
             "The non-Medicare payer set carries state-specific rules and, for "
             "LOP/lien work, real collection and timing risk."),
        Risk("Physician retention / key-proceduralist concentration", "Medium",
             "Interventionalists are the EBITDA; post-close comp and retention "
             "are decisive to procedure volume."),
    ],
    diligence_questions=[
        "What is the revenue mix across interventional procedures, medication "
        "management, and urine drug testing — and how clean is it?",
        "What is the toxicology/UDT revenue share and billing pattern "
        "(definitive vs presumptive, standing orders), and what is the audit/"
        "enforcement history?",
        "How exposed is procedure volume to LCD utilization caps and RFA "
        "prerequisites, and what has recent MAC policy done to it?",
        "How is OBL/ASC ownership and any toxicology-lab arrangement structured "
        "against Stark and the AKS safe harbors?",
        "What are spinal-cord-stimulator trial/implant volumes, the trial-to-"
        "permanent conversion, and device cost as a % of case net revenue?",
        "What opioid-prescribing, DEA, PDMP, and litigation history exists — and "
        "is any medication-management exposure being divested?",
        "What is the payer mix (Medicare/commercial/workers'-comp), and what is "
        "the collection experience on WC/lien business?",
        "How concentrated is procedure volume in the top interventionalists, "
        "and what are their retention and compensation terms?",
    ],
    insider_lens=[
        "There are two pain practices and you only want one. The interventional, "
        "non-opioid, ASC/OBL-capturing model is the deal; the medication-"
        "management / opioid-legacy book is a compliance liability — the whole "
        "game in pain diligence is separating the two inside the same tax ID.",
        "Urine drug testing is the tell. In-office toxicology was the ancillary "
        "that made pain practices look spectacular — and it was the biggest "
        "False-Claims vector in the specialty (definitive-testing overbilling, "
        "standing orders, lab kickbacks). A UDT-heavy revenue mix isn't margin, "
        "it's a landmine; underwrite the interventional book without it.",
        "LCDs, not the fee schedule, set the ceiling. Medicare Administrative "
        "Contractors cap how many epidurals, facet blocks, and ablations a "
        "patient can get and require diagnostic blocks before RFA — so a policy "
        "revision can erase volume overnight. Read the local MAC policy, not "
        "just the RVUs.",
        "The stimulator can eat the case. Spinal-cord-stimulator and pump "
        "implants are the growth engine, but the device is often the largest "
        "single line on a fixed rate — a lucrative-looking neuromodulation "
        "program can be thin if trial-to-implant conversion and device pricing "
        "aren't managed.",
        "Non-opioid demand is the real, clean tailwind. The opioid crisis pushed "
        "payers and guidelines toward interventional and neuromodulation "
        "alternatives — the durable growth is in the procedural, device-based "
        "therapies, which is exactly the part of the specialty that is buyable "
        "and defensible.",
    ],
    connections=default_connections(
        "pain_management",
        deals_sector="pain_management",
        extra_pages=[
            ("/industry/pain_management",
             "Industry deep-dive — pain-management deal history + structure"),
        ],
        connectors=[
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare physician utilization — injection/RFA/neurostimulation "
             "service volume"),
            ("cms_open_data_mup_outpatient_by_provider_service",
             "Medicare outpatient utilization — HOPD vs OBL/ASC site-of-service "
             "read"),
            ("open_payments_general_payments_2024",
             "Open Payments — neurostimulator/device-maker payments to pain "
             "physicians"),
            ("open_payments_ownership_payments_2024",
             "Open Payments — physician ownership & investment (OBL/ASC/lab "
             "safe-harbor screen)"),
            ("cms_open_data_mup_partd_prescriber_by_provider",
             "Medicare Part D prescribing — opioid prescribing pattern screen"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — pain-management / interventional workforce supply"),
        ],
    ),
    sources=[
        Source("Institute of Medicine — Relieving Pain in America (2011, "
               "economic cost of chronic pain)", "ACADEMIC",
               "https://www.nationalacademies.org/"),
        Source("CDC — Chronic pain prevalence (NHIS) and Clinical Practice "
               "Guideline for Prescribing Opioids (2022)", "GOV",
               "https://www.cdc.gov/opioids/healthcare-professionals/prescribing/guideline/"),
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule (RVUs, "
               "conversion factor)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("CMS — Medicare Coverage Database (Local Coverage Determinations "
               "for pain procedures)", "GOV",
               "https://www.cms.gov/medicare-coverage-database/"),
        Source("CMS — Hospital OPPS / ASC Payment System + ASC Covered "
               "Procedures List", "GOV",
               "https://www.cms.gov/medicare/payment/prospective-payment-systems/ambulatory-surgical-center-asc"),
        Source("HHS OIG / DOJ — urine-drug-testing and toxicology-lab False-"
               "Claims enforcement", "GOV",
               "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
        Source("PE Desk industry deep-dive (pain management) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=pain_management"),
    ],
    live_figures=live_figures_from_dive("pain_management"),
    trends=(
        "Pain management arrived in the physician-roll-up wave later than derm "
        "and GI and with more reputational baggage, because the specialty spans "
        "two very different businesses. The medication-management model — the "
        "opioid-prescribing practice — became a liability as the opioid crisis, "
        "DEA enforcement, state PDMP mandates, and the 2016/2022 CDC prescribing "
        "guidelines reset the landscape, and in-office urine drug testing, once "
        "the specialty's richest ancillary, turned into a wave of OIG/DOJ False-"
        "Claims cases. The INTERVENTIONAL model moved the opposite direction: the "
        "same opioid backlash pushed payers and guidelines toward non-opioid "
        "injections, radiofrequency ablation, and neuromodulation, and CMS's "
        "additions of pain codes (including spinal-cord-stimulator implants) to "
        "the ASC Covered Procedures List let physician-owned OBLs and ASCs "
        "capture the facility fee — the familiar site-of-service arbitrage. PE "
        "built interventional-pain platforms around that thesis while screening "
        "out opioid and toxicology exposure. The forward tensions are medical "
        "policy and compliance: repeated MPFS cuts and LCD utilization tightening "
        "on injections and RFA, device cost on neurostimulation, and continued "
        "toxicology and OBL-ownership enforcement — set against a durable aging/"
        "MSK demand base and a structural push toward non-opioid therapy."),
    growth_levers=[
        GrowthLever(
            "Site-of-service migration (HOPD → OBL/ASC)",
            "Moving injections, RFA, and SCS implants into physician-owned labs/"
            "ASCs captures the technical/facility fee the hospital used to earn.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Non-opioid interventional shift",
            "The opioid backlash pushes payers and guidelines toward injections, "
            "ablation, and neuromodulation — a clean, favored demand channel.",
            "+ structural", "GOV"),
        GrowthLever(
            "Neuromodulation (SCS) adoption",
            "Spinal-cord-stimulator technology expands the high-value procedural "
            "case set — a device-driven growth engine.",
            "+ device-driven", "ILLUSTRATIVE"),
        GrowthLever(
            "ASC-CPL pain-code expansion (incl. SCS)",
            "CMS adds more pain/neuromodulation codes Medicare will pay in an "
            "ASC, widening the ambulatory-payable set.",
            "+ case set", "GOV"),
        GrowthLever(
            "Aging + MSK/spine-pain prevalence",
            "An aging population with rising musculoskeletal and spine pain "
            "expands the base procedural demand.",
            "+ mid-single %/yr", "GOV"),
        GrowthLever(
            "MPFS cuts / LCD tightening drag",
            "Repeated injection/RFA fee cuts and MAC utilization caps are the "
            "structural headwinds on procedure volume.",
            "policy risk", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Aging + MSK/spine pain × the non-opioid interventional shift",
        analysis=(
            "The demand base is chronic pain — more than 50 million US adults — "
            "growing with an aging, increasingly musculoskeletal-and-spine-"
            "burdened population, which generates a steady flow of injection, "
            "ablation, and neuromodulation candidates. The structural amplifier "
            "is the opioid backlash: guidelines, payers, and public policy now "
            "steer chronic-pain patients away from long-term opioids and toward "
            "non-opioid interventional and device-based therapies, and CMS's "
            "additions of pain codes (including spinal-cord stimulators) to the "
            "ASC Covered Procedures List shift those procedures into physician-"
            "owned ambulatory settings where the practice captures the facility "
            "fee. The critical offset is that volume is not demand-limited but "
            "POLICY-limited: Local Coverage Determinations cap how many "
            "injections and ablations a patient can receive and set prerequisites "
            "for RFA, so MAC medical policy — more than underlying pain "
            "prevalence — determines how much of the demand converts to payable "
            "procedures."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Physician & clinical labor (interventionalists, CRNA/anesthesia, "
            "staff)",
            "~35-45% of cost",
            "Proceduralists and procedural-sedation staff — the scarce, "
            "expensive core and the key-man concentration.", "ILLUSTRATIVE"),
        CostDriver(
            "Devices & implants (SCS, pumps, RFA probes, injectables)",
            "large on neuromodulation cases",
            "Neurostimulators and pumps can approach the largest line in the "
            "case on a fixed rate; RFA probes and injectables add per-case "
            "supply cost.", "ILLUSTRATIVE"),
        CostDriver(
            "OBL/ASC facility & procedure-room chassis",
            "~10-15% of cost",
            "The fixed procedural suite (imaging/fluoroscopy, sedation, build-"
            "out) that gates injection/RFA/SCS capacity.", "ILLUSTRATIVE"),
        CostDriver(
            "Toxicology / lab operating cost (where retained)",
            "compliance-sensitive",
            "In-office UDT/toxicology carries lab operating cost AND outsized "
            "compliance/audit-defense overhead — a reason many divest it.",
            "ILLUSTRATIVE"),
        CostDriver(
            "G&A, billing, prior-auth & compliance (LCD/AKS/opioid)",
            "~12-18% of cost",
            "Heavy prior-authorization on injections/RFA/SCS plus a real "
            "compliance overhead on LCDs, toxicology, and opioid monitoring.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No vendored pain-management facility file exists — an interventional-"
        "pain group is a physician practice/OBL, not a Medicare-certified "
        "facility — so state geography is omitted rather than fabricated. "
        "Qualitatively, the interventional opportunity varies with (1) state "
        "Certificate-of-Need regimes governing new ASCs/procedure suites, (2) "
        "the local Medicare Administrative Contractor's Local Coverage "
        "Determinations, which differ by MAC jurisdiction and directly set "
        "injection/RFA utilization limits, and (3) workers'-comp and auto/PIP "
        "fee schedules and lien (LOP) rules, which are state-specific and shape "
        "the non-Medicare payer mix. Opioid-prescribing and PDMP regimes also "
        "vary by state and bear on the medication-management exposure. The "
        "Medicare physician- and outpatient-utilization connectors and the "
        "Part D opioid-prescribing connector linked below map procedure and "
        "prescribing volume by geography — the honest footprint read for where "
        "interventional demand and compliance risk concentrate."),
)

register(REPORT)
