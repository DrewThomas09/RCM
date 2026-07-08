"""Teleradiology — remote interpretation of diagnostic imaging.

Deals-only deep-dive (teleradiology is delivered remotely — geography is not
the structure read, so it is omitted rather than fabricated; the SOURCED layer
is the radiology trade history the sector shares). This is the PROFESSIONAL
component of imaging — the radiologist's read — delivered from a distant site,
with NO technical component and almost no fixed capital. The qualitative
sections are authored around what actually governs it: the professional-component
(-26) MPFS payment, the bill-and-collect vs fee-per-read business-model fork,
50-state licensure and credentialing, the offshore/preliminary-read rule, and
the structural radiologist shortage. Consumes ``teleradiology_deep_dive()`` for
SOURCED corpus deal figures (the shared radiology trade history).
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="teleradiology",
    name="Teleradiology",
    care_setting="Dx & labs",
    naics="621512",
    one_line_def=(
        "Remote interpretation of diagnostic images — radiologists reading "
        "X-ray, CT, MRI, ultrasound, and nuclear studies from a distant site "
        "for hospitals, emergency departments, and imaging centers. It is the "
        "PROFESSIONAL component of imaging (the read, billed with the -26 "
        "modifier) delivered over the wire, with no technical component and "
        "almost no fixed capital — a radiologist-labor and technology business, "
        "not an equipment business."),
    tam_headline=TamHeadline(
        value=5.0, unit="$B", growth_pct=9.5, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US teleradiology services revenue is not a single published "
            "figure; ~$5B is the modeled slice of the radiology "
            "professional-component market delivered remotely. Reads are paid "
            "under MPFS as the professional component (-26) — the GOV mechanic "
            "in the segments below. Growth is the modeled composite of imaging-"
            "volume growth and the radiologist-shortage-driven shift of reads "
            "off-site (faster than overall imaging)."),
    ),
    executive_summary=[
        "It is a labor business, not an imaging business. Teleradiology owns no "
        "scanners; it owns radiologist capacity and the technology that routes "
        "the right study to the right subspecialist fast. The scarce, expensive "
        "input is the radiologist — reads per radiologist-hour and comp leverage "
        "are the whole P&L.",
        "The radiologist shortage is the structural tailwind. Hospitals and "
        "imaging centers cannot staff nights, weekends, and subspecialty "
        "coverage internally, so they outsource the read — demand that grows "
        "faster than imaging volume itself and is largely non-discretionary.",
        "Two business models with different risk. Bill-and-collect (the group "
        "bills payers the professional component and owns credentialing, "
        "enrollment, and denial risk across many states) versus fee-per-read "
        "service contracts (the facility bills; the teleradiology company is "
        "paid a per-study fee and owns utilization, not payer, risk). Which one "
        "you are buying reshapes the diligence.",
        "50-state licensure and credentialing is the moat and the grind. "
        "Medicare requires the interpreting radiologist be licensed where the "
        "patient is located; a deep multistate license/credentialing base is a "
        "real barrier and a heavy back office (the Interstate Medical Licensure "
        "Compact eases it).",
        "Offshore reads cannot bill Medicare. The classic 'sun-chasing' model "
        "(radiologists abroad reading US nights) can provide only preliminary "
        "reads for US federal payers; the billable final read must be a "
        "US-licensed, US-located radiologist.",
        "AI is the swing factor. Worklist triage and CADe can multiply "
        "radiologist productivity (good for a platform) or, over time, "
        "commoditize routine reads (bad for per-read economics) — the model's "
        "long-run margin hinges on which.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Study acquired at the originating site (hospital/ED/imaging center)",
            "Images pushed to the teleradiology platform / worklist (DICOM)",
            "Routing — matched to a licensed, credentialed, subspecialty radiologist",
            "Radiologist interprets remotely and dictates the report (PC)",
            "Report returned to the ordering site; critical findings called",
            "Preliminary (nighthawk) vs final read designation applied",
            "Professional-component claim billed, or per-read service fee invoiced",
            "Cross-state licensure, credentialing, and enrollment maintained",
        ],
        sites_of_care=[
            "Hospital & emergency-department radiology coverage (nighthawk/24-7)",
            "Freestanding imaging-center overflow & subspecialty reads",
            "Rural / critical-access hospitals without on-site radiologists",
            "Subspecialty reads (neuro, MSK, pediatric, cardiac, breast)",
            "The reading radiologist's home/office workstation (the 'site')",
            "Offshore preliminary-read centers (non-billable for Medicare)",
        ],
        money_flow=(
            "Teleradiology monetizes the PROFESSIONAL component only — there is "
            "no technical component because it owns no equipment. Under the "
            "bill-and-collect model, the interpreting radiologist (via the group "
            "or a reassignment of benefits) bills Medicare and commercial payers "
            "the -26 professional component under the Physician Fee Schedule, so "
            "revenue is realized rate per read net of denials, and the company "
            "must be enrolled and credentialed in every relevant state and plan. "
            "Under the service-contract model, the originating facility bills the "
            "study and pays the teleradiology company a negotiated per-read fee "
            "(or a coverage subscription), so the company carries utilization "
            "risk but not payer risk. Medicare requires the interpreting "
            "physician to be licensed in the state where the patient is located; "
            "offshore radiologists may render only preliminary reads for federal "
            "payers. The economic engine is radiologist productivity — reads per "
            "hour and subspecialty premium — against a comp-heavy, low-capital "
            "cost base."),
        key_players=(
            "The scaled players are the radiology mega-groups and dedicated "
            "teleradiology firms: vRad (now part of Radiology Partners), "
            "Radiology Partners' own teleradiology, StatRad, US Radiology "
            "Specialists' remote reads, Everlight Radiology, and Teleradiology "
            "Solutions, plus many hospital radiology groups running internal "
            "teleradiology. AI vendors (Aidoc, Rad AI, Annalise) increasingly "
            "sit inside the worklist. The buyers are hospitals, health systems, "
            "EDs, and imaging centers that cannot staff coverage themselves."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Professional-component (-26) reads",
                    "the entire revenue basis",
                    "GOV · MPFS professional component (mechanic)"),
            Segment("Nighthawk / after-hours & ED coverage",
                    "the original, still-core demand",
                    "ILLUSTRATIVE · modeled coverage mix"),
            Segment("Subspecialty reads (neuro, MSK, breast, peds, cardiac)",
                    "premium, growing share",
                    "ILLUSTRATIVE · modeled subspecialty mix"),
            Segment("Rural / critical-access coverage",
                    "structural access gap",
                    "ILLUSTRATIVE · access-driven demand"),
            Segment("Fee-per-read service contracts",
                    "the non-payer-risk revenue model",
                    "ILLUSTRATIVE · modeled contract mix"),
        ],
        growth_drivers=[
            "Radiologist shortage — the structural demand engine",
            "Imaging-volume growth (aging, advanced-imaging mix)",
            "Subspecialization — routing studies to the right sub-specialist",
            "Rural/ED access gaps and 24-7 coverage expectations",
            "AI-assisted triage lifting reads-per-radiologist (productivity)",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.50,
            "Medicare / MA": 0.35,
            "Medicaid / self-pay / other": 0.15,
        },
        rate_mechanics=[
            "Professional component only (-26 modifier) under MPFS — the "
            "radiologist's read; there is no technical component to bill.",
            "Bill-and-collect vs service-fee — either the group bills payers the "
            "PC (owning credentialing and denial risk) or the facility bills and "
            "pays a per-read/coverage fee (owning utilization risk).",
            "State-of-patient licensure — the interpreting radiologist must be "
            "licensed where the patient/originating site is located; enrollment "
            "and reassignment of benefits follow.",
            "Preliminary vs final read — nighthawk preliminary reads are "
            "typically over-read (and billed) by the site's radiologist; final "
            "reads are billed by the teleradiologist.",
            "Offshore limitation — radiologists located outside the US may "
            "provide only preliminary reads for Medicare; the billable final "
            "read must be US-licensed and US-located.",
            "Multiple Procedure Payment Reduction (MPPR) applies to the "
            "professional component on multiple studies in a session.",
            "Credentialing by proxy — hospitals may credential distant-site "
            "teleradiologists via the distant site's credentialing (CMS/Joint "
            "Commission telemedicine rules).",
        ],
        reimbursement_risk=(
            "The rate mechanics mirror imaging's professional side: MPFS "
            "budget-neutral conversion-factor cuts and MPPR chronically pressure "
            "the professional-component rate. The model-specific risk is which "
            "revenue model the company runs. Bill-and-collect exposes it to "
            "payer credentialing gaps, out-of-network denials, and 50-state "
            "enrollment complexity — realized yield per read can trail the fee "
            "schedule materially. Service-fee contracts remove payer risk but "
            "concentrate revenue in a handful of hospital-system relationships, "
            "so contract renewal and pricing are the swing. Because the entire "
            "product is physician labor, radiologist compensation inflation in a "
            "shortage market is the dominant margin pressure, and any AI-driven "
            "commoditization of routine reads is the long-run per-read risk."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("State medical licensure (state-of-patient) + Interstate "
                 "Medical Licensure Compact",
                 "The interpreting radiologist must be licensed where the "
                 "patient is located; multistate licensure is the operational "
                 "barrier the Compact partially eases.",
                 "https://www.imlcc.org/"),
            Rule("Medicare enrollment, reassignment & the interpreting-physician "
                 "location rules",
                 "Govern who may bill the professional component and from where; "
                 "offshore reads are preliminary-only for Medicare.",
                 "https://www.cms.gov/medicare/enrollment-renewal"),
            Rule("Credentialing by proxy for telemedicine (42 CFR 482.22 / "
                 "Joint Commission)",
                 "Lets a hospital credential distant-site teleradiologists via "
                 "the distant site's credentialing — the mechanism that makes "
                 "scaled coverage administrable.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-482/section-482.22"),
            Rule("Corporate Practice of Medicine (CPOM) — state doctrines",
                 "Many states restrict corporate ownership of physician "
                 "practices, driving friendly-PC / MSO structures for "
                 "teleradiology groups — a diligence-critical structure.",
                 None),
            Rule("MPFS annual Final Rule (professional component)",
                 "Sets the professional-component RVUs, conversion factor, and "
                 "MPPR that price every read.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
            Rule("ACR Teleradiology Practice Parameter + HIPAA image security",
                 "Professional standards for remote reads and the data-security "
                 "regime for transmitting protected images.",
                 "https://www.acr.org/Clinical-Resources/Practice-Parameters-and-Technical-Standards"),
        ],
        policy_watch=[
            "MPFS conversion-factor cuts hitting the professional component",
            "Interstate Medical Licensure Compact expansion / licensure reform",
            "Telehealth flexibilities and cross-state practice rules",
            "FDA clearance and reimbursement pathway for AI triage/CADe",
            "CPOM enforcement and friendly-PC structure scrutiny",
            "Payer credentialing and out-of-network read-billing limits",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Consolidating fast at the top but still fragmented below. A few "
            "scaled platforms (vRad/Radiology Partners, StatRad, US Radiology) "
            "run national coverage, while many hospital radiology groups operate "
            "internal teleradiology and a long tail of smaller remote-read "
            "groups persists. Because delivery is remote, structure is read by "
            "contract book and radiologist capacity, not geography — a "
            "facility-count HHI is honestly not the right lens."),
        hhi_or_share=(
            "No single dominant owner, but Radiology Partners (which absorbed "
            "vRad) is the largest US aggregator of radiologist capacity. "
            "Concentration is best read as share of contracted reads and "
            "subspecialty coverage depth, not facility count."),
        consolidation=(
            "The defining event was Radiology Partners acquiring vRad, merging "
            "the largest teleradiology platform into the largest radiology "
            "practice — folding remote reads into a national physician "
            "aggregator. US Radiology and other platforms built or bought "
            "teleradiology arms, and health systems increasingly contract "
            "national coverage rather than staff it. Scale in radiologist "
            "capacity, subspecialty depth, and technology is the consolidation "
            "logic."),
        pe_activity=(
            "PE plays teleradiology mostly through the radiology physician "
            "platforms (the professional-component aggregators) and dedicated "
            "remote-read firms, where a technology platform plus scaled "
            "radiologist capacity compounds. Quality-of-earnings centers on "
            "radiologist supply/retention and comp trajectory, contract "
            "concentration and renewal, the bill-and-collect vs service-fee "
            "revenue mix, multistate licensure depth, and the AI productivity/"
            "commoditization question."),
        notable_players=[
            "vRad (Radiology Partners)", "Radiology Partners",
            "StatRad", "US Radiology Specialists (remote)",
            "Everlight Radiology", "Teleradiology Solutions",
            "Hospital radiology groups (internal telerad)",
            "AI worklist vendors (Aidoc, Rad AI)",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Reads / radiologist / shift", "subspecialty & modality-dependent",
                "Radiologist productivity (RVUs/hour) is the core lever; "
                "routing and worklist tools drive it."),
            Kpi("Radiologist comp (% of read revenue)", "the dominant cost",
                "Labor is the largest cost by far in a shortage market — comp "
                "leverage is the whole margin story."),
            Kpi("Subspecialty read premium", "higher rate & retention",
                "Neuro, MSK, breast, peds, and cardiac reads command premium "
                "pricing and stickier contracts."),
            Kpi("Realized yield / read (bill-and-collect)", "net of denials",
                "Multistate credentialing gaps and OON denials pull realized "
                "revenue below the fee schedule."),
            Kpi("Contract concentration", "top-customer % of revenue",
                "Service-fee revenue concentrates in a few hospital systems; "
                "renewal risk is a cliff, not a slope."),
            Kpi("Multistate license depth", "states per radiologist",
                "Broadly-licensed radiologists cover more demand — a real "
                "capacity and back-office asset."),
        ],
        margin_profile=(
            "Teleradiology is a low-capital, comp-heavy labor-and-technology "
            "business: there is no equipment chassis, so the cost base is "
            "radiologist compensation, the platform/PACS/routing technology, "
            "and the licensure/credentialing/billing back office. Margin is "
            "driven by radiologist productivity (reads per hour, subspecialty "
            "premium) and comp leverage against a scarce, expensive labor pool — "
            "when the platform routes efficiently and keeps radiologists near "
            "capacity, contribution is strong; when a shortage forces comp up or "
            "coverage sits idle across time zones, margin compresses. "
            "Bill-and-collect adds denial and credentialing drag between gross "
            "and net; service-fee models trade that for utilization and "
            "contract-renewal risk. AI is the wildcard — a productivity "
            "multiplier improves margin, commoditization erodes per-read price."),
    ),
    risks=[
        Risk("Radiologist supply & compensation inflation", "High",
             "The scarce, expensive input is the radiologist; comp inflation in "
             "a shortage market is the dominant margin pressure and a capacity "
             "ceiling."),
        Risk("Contract concentration / renewal (service-fee model)", "High",
             "Revenue often concentrates in a few hospital-system contracts; "
             "losing one is a step-down, not a trim."),
        Risk("MPFS professional-component rate erosion", "Medium",
             "Budget-neutral conversion-factor cuts and MPPR pressure the "
             "per-read rate that anchors bill-and-collect economics."),
        Risk("Multistate licensure & credentialing complexity", "Medium",
             "50-state licensure, enrollment, and payer credentialing are a "
             "heavy back office; gaps directly suppress billable capacity."),
        Risk("AI commoditization of routine reads", "Medium",
             "If AI substitutes for (rather than augments) routine "
             "interpretation, per-read pricing on high-volume studies could "
             "compress over the hold."),
        Risk("Malpractice & preliminary/final read liability", "Low",
             "Cross-state remote reads carry distributed malpractice exposure "
             "and preliminary-vs-final discrepancy risk."),
    ],
    diligence_questions=[
        "What is the revenue-model split — bill-and-collect versus fee-per-read "
        "service contracts — and how does payer risk sit in each?",
        "What is radiologist headcount, comp trajectory, subspecialty mix, and "
        "retention/attrition in a shortage market?",
        "How concentrated is revenue in the top hospital-system contracts, and "
        "what are the renewal terms and pricing?",
        "What is the multistate licensure and payer-credentialing footprint, "
        "and where are the enrollment gaps suppressing billable capacity?",
        "What is realized yield per read after denials, and what share of reads "
        "are preliminary versus billable final?",
        "What is reads-per-radiologist-hour and how much does the routing/"
        "worklist technology lift it versus peers?",
        "How is the group structured against Corporate Practice of Medicine "
        "(friendly-PC / MSO), and is it compliant in every state served?",
        "What is the AI strategy — productivity multiplier or substitution risk "
        "— and how are AI tools integrated and reimbursed?",
    ],
    insider_lens=[
        "You are underwriting radiologist capacity, not scanners. There is no "
        "equipment moat; the asset is a pool of broadly-licensed, subspecialty "
        "radiologists plus a routing platform that keeps them near capacity. "
        "Comp leverage and reads-per-hour are the entire margin.",
        "The revenue model changes the whole risk profile. Bill-and-collect "
        "means you own 50-state credentialing, enrollment, and denial risk on "
        "the professional component; a service-fee contract hands payer risk to "
        "the hospital but concentrates your revenue in a few renewable "
        "contracts. Confuse the two and you misprice the deal.",
        "The shortage is the business. Hospitals outsource because they cannot "
        "staff nights, weekends, rural sites, and subspecialty coverage — so "
        "demand is structural and non-discretionary, and it grows faster than "
        "imaging volume itself.",
        "Offshore is preliminary-only for Medicare. The sun-chasing model "
        "(radiologists abroad reading US nights) is a coverage tool, not a "
        "billing engine — the billable final read must be a US-licensed, "
        "US-located radiologist, so don't credit offshore capacity as billable.",
        "AI is the two-sided coin. In the platform's hands, triage and CADe "
        "multiply reads per radiologist and defend margin; left to the market, "
        "AI could commoditize routine plain-film and CT reads and compress "
        "per-read price. Which way it cuts over a hold is the real long-run "
        "question.",
    ],
    connections=default_connections(
        "teleradiology",
        deals_sector="radiology",
        extra_pages=[
            ("/industry/teleradiology",
             "Industry deep-dive — radiology deal history + structure"),
        ],
        connectors=[
            ("cms_open_data_medicare_telehealth_trends",
             "CMS Medicare telehealth trends — remote-service utilization "
             "context"),
            ("npi_provider_taxonomy",
             "NPI taxonomy — radiologist enrollment & subspecialty"),
            ("npi_provider_address",
             "NPI address — multistate radiologist licensure/practice footprint"),
            ("cms_open_data_mup_physician_by_provider_service",
             "Medicare utilization by HCPCS — professional-component (-26) read "
             "volume & allowed"),
            ("provider_data_imaging_efficiency_hospital",
             "CMS Outpatient Imaging Efficiency — the study base that gets read"),
            ("open_payments_general_payments_2024",
             "Open Payments — radiologist / vendor relationships"),
        ],
    ),
    sources=[
        Source("CMS — Medicare Physician Fee Schedule annual Final Rule "
               "(professional component, MPPR)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/physician"),
        Source("CMS — Medicare enrollment & interpreting-physician location / "
               "reassignment rules", "GOV",
               "https://www.cms.gov/medicare/enrollment-renewal"),
        Source("Interstate Medical Licensure Compact — multistate physician "
               "licensure", "GOV", "https://www.imlcc.org/"),
        Source("Medicare Conditions of Participation — credentialing by proxy "
               "for telemedicine (42 CFR 482.22)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-482/section-482.22"),
        Source("American College of Radiology — Teleradiology Practice "
               "Parameter", "INDUSTRY",
               "https://www.acr.org/Clinical-Resources/Practice-Parameters-and-Technical-Standards"),
        Source("PE Desk industry deep-dive (radiology) + realized-deal corpus "
               "(shared radiology trade history)", "INTERNAL",
               "/diligence/tam-sam?template=teleradiology"),
    ],
    live_figures=live_figures_from_dive("teleradiology"),
    trends=(
        "Teleradiology began as a nighthawk convenience — a way to cover "
        "emergency reads after hours, often with radiologists chasing daylight "
        "abroad — and became core infrastructure. Two forces drove the shift. "
        "First, a persistent and worsening radiologist shortage: imaging volume "
        "grew (aging, advanced-imaging mix, new indications) faster than the "
        "radiologist workforce, so hospitals and imaging centers could not staff "
        "nights, weekends, rural sites, or subspecialty coverage internally and "
        "outsourced the read. Second, consolidation of radiologist capacity — "
        "Radiology Partners' acquisition of vRad merged the largest "
        "teleradiology platform into the largest radiology physician group, and "
        "other platforms scaled remote reads and subspecialty routing. The "
        "delivery model matured from preliminary over-reads toward billable "
        "final reads and subspecialty coverage, while credentialing-by-proxy and "
        "the Interstate Medical Licensure Compact made national coverage "
        "administrable. The forward story is dominated by two variables: the "
        "radiologist labor market (comp and supply set the margin) and "
        "artificial intelligence, which can either multiply reads per "
        "radiologist or, over time, commoditize routine interpretation."),
    growth_levers=[
        GrowthLever(
            "Radiologist shortage",
            "Imaging volume outgrows the radiologist workforce, so more reads "
            "are pushed off-site — the structural demand engine, growing faster "
            "than imaging itself.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Imaging-volume growth",
            "Aging, advanced-imaging mix, and new indications lift the total "
            "study base that must be read.",
            "+~3%/yr studies", "ILLUSTRATIVE"),
        GrowthLever(
            "Subspecialization",
            "Routing neuro, MSK, breast, pediatric, and cardiac studies to the "
            "right sub-specialist commands premium pricing and stickier "
            "contracts.",
            "+ premium mix", "ILLUSTRATIVE"),
        GrowthLever(
            "Rural / ED access & 24-7 coverage",
            "Critical-access and community hospitals without on-site "
            "radiologists depend on remote coverage.",
            "+ access demand", "ILLUSTRATIVE"),
        GrowthLever(
            "AI-assisted productivity",
            "Worklist triage and CADe raise reads-per-radiologist — a "
            "productivity lever that can defend margin (or, if it substitutes, "
            "compress per-read price).",
            "productivity / risk", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Imaging-study volume × the outsourced-read share",
        analysis=(
            "The dominant demand driver is the total volume of imaging studies "
            "multiplied by the share that gets read remotely rather than "
            "on-site. The study base grows with aging, an advanced-imaging mix "
            "shift, and new indications; the outsourced share grows faster "
            "because the radiologist workforce is not keeping pace — a "
            "structural shortage means hospitals, EDs, rural facilities, and "
            "imaging centers increasingly cannot staff coverage, especially "
            "nights, weekends, and subspecialty. Demand is therefore largely "
            "non-discretionary: a study that has been ordered must be read, and "
            "if no on-site radiologist is available it goes off-site. The "
            "throttle is not patient demand but radiologist capacity — how many "
            "broadly-licensed radiologists the platform can field and how "
            "productively it routes work to them — and, prospectively, how much "
            "AI triage lifts reads per radiologist-hour."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Radiologist compensation", "the dominant cost",
            "Physician labor is by far the largest cost; in a shortage market "
            "comp inflation is the primary margin pressure and the capacity "
            "ceiling.", "ILLUSTRATIVE"),
        CostDriver(
            "Technology platform (PACS, routing, worklist, AI)",
            "~10-20% of cost",
            "The image-transmission, routing, and reporting stack — the "
            "productivity engine and the only meaningful capital.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Licensure, credentialing & enrollment", "~5-10% of cost",
            "Maintaining multistate licenses and payer/hospital credentialing "
            "for every radiologist and market — a defining back-office cost.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing, denials & RCM (bill-and-collect)", "~5-10% of net",
            "Professional-component billing across many states and payers, with "
            "denial and out-of-network drag between gross and net.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Malpractice & compliance", "~3-6% of cost",
            "Cross-state professional-liability coverage and preliminary/final "
            "read quality assurance.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "Teleradiology is delivered remotely, so a facility-by-state map is not "
        "the structure read and geography is omitted rather than fabricated. "
        "What matters geographically is the licensure footprint — where the "
        "group's radiologists are licensed and credentialed determines where it "
        "can bill — and the location of demand (rural and critical-access "
        "hospitals without on-site radiologists). The NPI-taxonomy and NPI-"
        "address connectors linked below give a real read on radiologist "
        "enrollment and multistate reach."),
)

register(REPORT)
