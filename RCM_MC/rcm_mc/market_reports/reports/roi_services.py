"""ROI Services — Release of Information / health-information disclosure.

Deals-only pattern (copied from hospice.py): no vendored national facility
file, so geography is honestly omitted and the report leans on the qualitative
deep sections + ``live_figures_from_dive("roi_services")`` for any SOURCED
corpus figures. The defining economics are the REQUESTER MIX (attorney and
insurance requests generate statutory fees; patient and continuity-of-care
requests are fee-capped or free) and the Ciox v. Azar (2020) ruling that
restored market-rate third-party billing — both authored below.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="roi_services",
    name="ROI Services",
    care_setting="Other services",
    naics="561410",
    one_line_def=(
        "Outsourced release of information — the regulated fulfillment of "
        "requests for copies of patient medical records (from attorneys, "
        "insurers, other providers, patients, and disability programs) on "
        "behalf of hospitals and physician practices, governed by HIPAA's "
        "right-of-access rule and state medical-records-fee statutes."),
    tam_headline=TamHeadline(
        value=1.2, unit="$B", growth_pct=4.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US ROI/medical-records-disclosure services market "
            "(~$1.0-1.5B for provider-side disclosure; larger including the "
            "legal/insurance record-retrieval adjacency). No single published "
            "government total exists. Growth is the modeled composite of "
            "litigation and disability-request volume, offset by the Cures Act "
            "electronic-access drag."),
    ),
    executive_summary=[
        "The requester mix IS the business. Attorney and insurance requests pay "
        "statutory per-page/per-request fees (revenue); patient requests are "
        "fee-capped by HIPAA/HITECH; provider-to-provider continuity requests "
        "are free (cost). A book's economics are decided by how it is weighted "
        "across those requester types — not by request count.",
        "Ciox v. Azar (2020) re-legalized the revenue base. The DC District "
        "Court vacated HHS guidance that had extended the patient-rate fee cap "
        "to third-party (attorney/insurer) directives — restoring ROI vendors' "
        "ability to charge market/state-statutory rates for those requests. The "
        "durability of that legal footing is a first-order underwriting item.",
        "The Cures Act information-blocking rule is the existential long-term "
        "threat: mandated free electronic access via portals, APIs, and TEFCA "
        "erodes the per-page paper-fee model — but litigation-grade certified "
        "records with an affidavit are not replaced by a portal download.",
        "Deeply consolidated: Datavant (formerly Ciox Health) dominates, with "
        "MRO, Verisma, ScanSTAT, HealthMark, and Sharecare behind it — the long "
        "tail of local ROI shops is the roll-up pool.",
        "It is a picks-and-shovels business embedded inside provider HIM "
        "operations: sticky and mission-critical, but the customer is cost-"
        "focused, the fees are set by hostile state legislatures, and a single "
        "mis-disclosed record is an OCR penalty and a client-ending event.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "A request for records arrives (attorney, insurer, patient, another "
            "provider, SSA/disability, life insurer)",
            "Authorization + identity verification against HIPAA and state law "
            "(a valid authorization or a permitted disclosure)",
            "Records located and retrieved across EHR + legacy/paper systems",
            "PHI review and redaction (minimum-necessary, sensitive-record "
            "carve-outs — behavioral health, HIV, substance use)",
            "Certification/affidavit of completeness for legal requests",
            "Delivery (secure electronic, portal, or paper) within the "
            "statutory turnaround (HIPAA's 30-day access window)",
            "Invoicing the requester at the statutory/contract fee and "
            "remitting the provider's share",
        ],
        sites_of_care=[
            "Hospital and health-system HIM departments (on-site or remote)",
            "Physician group and specialty-practice records offices",
            "Imaging centers and ancillary providers",
            "Long-term / post-acute and behavioral-health records (sensitive)",
        ],
        money_flow=(
            "ROI vendors are paid by the REQUESTER, not the payer or the "
            "patient's insurer. For attorney and insurance requests, the vendor "
            "charges a per-page and/or per-request fee set by state medical-"
            "records statutes (search/retrieval plus per-page copy fees), "
            "invoices the requester, and remits a contracted share to the "
            "provider whose records were disclosed. For patient requests, HIPAA "
            "and HITECH cap the fee at a reasonable cost-based amount, so those "
            "are low- or no-margin; provider-to-provider continuity-of-care "
            "disclosures are free by rule. The vendor typically embeds staff "
            "inside the provider's HIM operation (or runs it remotely), so the "
            "sale is an outsourcing relationship plus a fee-collection engine "
            "layered on the legal/insurance request stream."),
        key_players=(
            "Consolidated. Datavant (which absorbed Ciox Health, historically "
            "the largest ROI company) is the clear leader; MRO Corp, Verisma "
            "(which acquired ScanSTAT), HealthMark Group, Sharecare Health Data "
            "Services, ChartSwap, and MediCopy fill out the scaled tier. Beneath "
            "them are hundreds of local and regional ROI shops — the fragmented "
            "acquisition pool — plus the provider's own in-house HIM staff that "
            "outsourcing displaces."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Attorney / legal requests",
                    "largest fee pool — litigation-driven",
                    "ILLUSTRATIVE · modeled requester mix; no published split"),
            Segment("Insurance / commercial requests",
                    "second fee pool — claims & underwriting",
                    "ILLUSTRATIVE · modeled requester mix"),
            Segment("Patient / personal requests",
                    "fee-capped (HIPAA/HITECH) — low margin",
                    "GOV · HIPAA 45 CFR 164.524 fee limits"),
            Segment("Provider-to-provider / continuity",
                    "free by rule — a cost of service",
                    "GOV · HIPAA treatment-disclosure rules"),
            Segment("Disability / SSA / government requests",
                    "high-volume, standardized",
                    "ILLUSTRATIVE · modeled requester mix"),
        ],
        growth_drivers=[
            "Litigation and personal-injury request volume — the primary fee "
            "engine",
            "Disability (SSA) and life-insurance underwriting request volume",
            "Provider consolidation → enterprise ROI outsourcing contracts",
            "Ciox v. Azar (2020) fee restoration — market-rate third-party "
            "billing",
            "Cures Act information-blocking / free electronic access — a "
            "structural DRAG on the per-page fee model",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Attorney / legal (fee-generating)": 0.42,
            "Insurance / commercial (fee-generating)": 0.28,
            "Disability / SSA / government": 0.14,
            "Patient / personal (fee-capped)": 0.10,
            "Provider-to-provider / continuity (no fee)": 0.06,
        },
        rate_mechanics=[
            "State medical-records-fee statutes — per-page copy fees plus "
            "search/retrieval and certification fees, capped and structured "
            "differently in every state (the core rate sheet for third-party "
            "requests).",
            "HIPAA right-of-access fee limit (45 CFR 164.524) — patient "
            "requests are capped at a reasonable, cost-based fee; this is NOT a "
            "revenue stream.",
            "Ciox v. Azar (2020) — vacated the extension of the patient-rate "
            "cap to third-party directives, restoring market/statutory pricing "
            "for attorney and insurer requests.",
            "Fee-split / remittance — the vendor typically shares a portion of "
            "collected fees with the provider (or pays for the outsourcing "
            "relationship), so realized net revenue is the collected fee less "
            "the provider remit.",
            "Invoice collection — third-party requesters are billed and "
            "collected on terms; collection rate is a real revenue-quality "
            "variable, not a payer denial.",
        ],
        reimbursement_risk=(
            "Two structural risks dominate. First, the fee regime itself: state "
            "legislatures and privacy advocates periodically tighten per-page "
            "caps, and the HIPAA patient-rate cap already zeroes out the "
            "patient-request slice — so revenue durability depends on the "
            "attorney/insurer fee stream that Ciox v. Azar restored, and on "
            "that ruling's continued footing. Second, the 21st Century Cures Act "
            "information-blocking rule pushes records toward free, electronic, "
            "API-based access (patient portals, TEFCA/QHIN exchange), which "
            "erodes the paper-and-per-page model over time. The mitigant is "
            "that certified, litigation-grade complete records with an affidavit "
            "— the attorney product — are a human-verified legal deliverable a "
            "portal download does not replace."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("HIPAA Privacy Rule — right of access (45 CFR 164.524)",
                 "Governs the 30-day turnaround, the permitted fee for patient "
                 "requests, and the form/format of disclosure — the federal "
                 "backbone of the whole service.",
                 "https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/access/index.html"),
            Rule("Ciox Health, LLC v. Azar (D.D.C. 2020)",
                 "Vacated HHS guidance extending the patient-rate fee cap to "
                 "third-party directives — restoring ROI vendors' ability to "
                 "charge market/state-statutory rates to attorneys and "
                 "insurers.",
                 "https://ecf.dcd.uscourts.gov/"),
            Rule("21st Century Cures Act — information-blocking rule (ONC)",
                 "Prohibits information blocking and mandates electronic access "
                 "via APIs — the structural pressure on the paper/per-page fee "
                 "model and the push toward free portal access.",
                 "https://www.healthit.gov/topic/information-blocking"),
            Rule("State medical-records statutes",
                 "Each state sets its own per-page caps, search/retrieval fees, "
                 "and turnaround — the actual rate sheet for third-party "
                 "requests, and the source of legislative repricing risk.",
                 None),
            Rule("OCR Right-of-Access enforcement initiative",
                 "OCR penalizes providers (and, by extension, their ROI "
                 "vendors) for failing to provide timely records at a "
                 "reasonable cost — the compliance stick that makes accuracy "
                 "and turnaround existential.",
                 "https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/agreements/index.html"),
        ],
        policy_watch=[
            "Cures Act / TEFCA electronic-exchange maturation and its erosion "
            "of per-page fees",
            "Any appeal or codification affecting the Ciox v. Azar fee posture",
            "State-by-state medical-records fee-cap legislation",
            "OCR right-of-access enforcement actions and their fee guidance",
            "42 CFR Part 2 (substance-use records) alignment with HIPAA — "
            "sensitive-record handling",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Consolidated at the top and fragmented at the bottom. A handful of "
            "national platforms serve the large health systems, while hundreds "
            "of local and regional ROI shops still hold physician-practice and "
            "community-hospital books — the classic roll-up tail. No vendored "
            "facility file exists for this services vertical, so a computed HHI "
            "is honestly omitted."),
        hhi_or_share=(
            "Qualitatively concentrated: Datavant/Ciox has long held a "
            "plurality-to-majority position in health-system ROI, with MRO and "
            "Verisma the principal challengers. The physician-practice segment "
            "remains far more fragmented."),
        consolidation=(
            "Persistent roll-up. Ciox Health assembled the leading position "
            "through acquisitions and then merged into Datavant (2021); Verisma "
            "acquired ScanSTAT; sponsors have backed HealthMark and others to "
            "consolidate regional shops. The thesis is standardizing workflow "
            "(auto-redaction, e-delivery, request routing) across a fragmented "
            "base and capturing the legal/insurance fee stream at scale."),
        pe_activity=(
            "Active and long-running. The attributes are recurring, fee-based, "
            "mission-critical HIM work with a fragmented tail to consolidate and "
            "technology to layer. Quality-of-earnings hinges on decomposing "
            "revenue by requester type, testing the durability of the Ciox v. "
            "Azar fee posture, sizing the Cures Act electronic-access drag, and "
            "confirming HIM contract retention and PHI-breach history."),
        notable_players=[
            "Datavant (Ciox Health)", "MRO Corp", "Verisma (ScanSTAT)",
            "HealthMark Group", "Sharecare Health Data Services", "ChartSwap",
            "MediCopy", "ELAP / regional ROI shops",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue per request", "requester-mix-driven",
                "Attorney/insurer requests carry statutory fees; patient and "
                "continuity requests do not — the mix sets the average."),
            Kpi("Requester mix (% fee-generating)", "60-75%",
                "Share of requests from attorneys and insurers — the single "
                "best predictor of book profitability."),
            Kpi("Turnaround time (TAT)", "≤30 days (statutory)",
                "HIPAA's access window; missing it triggers OCR exposure and "
                "client dissatisfaction."),
            Kpi("Cost per request", "labor + redaction driven",
                "Records-tech labor, PHI review/redaction, and delivery — the "
                "lever automation attacks."),
            Kpi("Invoice collection rate", "high-80s to mid-90s %",
                "Third-party requesters are billed on terms; collection is a "
                "real revenue-quality variable."),
            Kpi("PHI breach / error rate", "near-zero required",
                "A mis-disclosure is an OCR penalty and a client-terminating "
                "event — the existential quality metric."),
            Kpi("EBITDA margin", "15-28%",
                "Higher for automated, legal/insurance-weighted books at scale; "
                "lower for patient/continuity-heavy or manual books."),
        ],
        margin_profile=(
            "ROI margin is a requester-mix-times-automation story. The fee "
            "stream comes almost entirely from attorney and insurer requests, "
            "so a book weighted toward those requesters — after the provider "
            "remit — carries the margin, while patient and continuity requests "
            "are a mandated cost of service. Cost is records-tech labor, PHI "
            "review/redaction, and delivery; auto-redaction and e-delivery "
            "technology is the primary margin-expansion lever and the reason "
            "the scaled platforms out-earn manual shops. The swing risk is the "
            "Cures Act shift toward free electronic access, which slowly "
            "compresses the per-page fee base."),
    ),
    risks=[
        Risk("Cures Act / free electronic access erosion", "High",
             "Mandated portal/API access and TEFCA exchange erode the per-page "
             "paper-fee model over the hold period."),
        Risk("Fee-regime / Ciox v. Azar reversal or state fee caps", "High",
             "Revenue depends on market-rate third-party billing; a legal or "
             "legislative reversal repriced the industry once and could again."),
        Risk("PHI breach / mis-disclosure", "High",
             "A single improper disclosure is an OCR penalty and a client-"
             "ending event — the existential operational risk."),
        Risk("HIM contract concentration / churn", "Medium",
             "Enterprise health-system contracts are large and re-bid; loss of "
             "an anchor system is a step-change to revenue."),
        Risk("Automation-driven fee/price pressure", "Medium",
             "As records go electronic and self-service, the value of manual "
             "fulfillment — and its fee — declines."),
        Risk("Labor availability for records/redaction techs", "Low",
             "A tight but manageable labor market; automation is reducing the "
             "headcount dependency."),
    ],
    diligence_questions=[
        "What is the revenue decomposition by requester type (attorney, "
        "insurer, patient, provider-to-provider, SSA), and how is each "
        "trending?",
        "How exposed is revenue to the Ciox v. Azar fee posture, and what is "
        "the state-by-state fee-cap footprint of the book?",
        "What share of the client base has moved (or is moving) to free "
        "electronic/portal access under the Cures Act, and what is the modeled "
        "per-page-fee erosion?",
        "What is HIM client concentration — top-5 and top-10 share — and the "
        "renewal/re-bid history?",
        "What is the PHI-breach and OCR-complaint history, and what controls "
        "and reserves are in place?",
        "What is the automation level (auto-redaction, e-delivery) and the "
        "resulting cost-per-request vs manual peers?",
        "What is the invoice collection rate and aging on third-party "
        "billings?",
        "How is the provider fee-split/remit structured, and how does it affect "
        "net realized revenue?",
    ],
    insider_lens=[
        "Count the requesters, not the requests. Two books with identical "
        "volume can have opposite economics — one weighted to attorney/insurer "
        "fee requests is a profit engine, one weighted to patient and "
        "continuity requests is a cost center. QoE must decompose revenue by "
        "requester type before believing the margin.",
        "Ciox v. Azar is the load-bearing case. The 2020 ruling that vacated "
        "the third-party fee cap restored the industry's revenue base; the "
        "entire fee model for attorney and insurer requests rests on that "
        "footing, so its durability is an underwriting input, not a footnote.",
        "The Cures Act is the slow tide, not the tsunami. Free electronic "
        "access erodes per-page fees gradually, but the certified, litigation-"
        "grade complete record with an affidavit is a legal deliverable a "
        "portal download cannot produce — the attorney product is the moat that "
        "survives interoperability.",
        "It is inside the provider, which is the moat and the leash. Embedding "
        "in a health system's HIM operation makes the relationship sticky and "
        "hard to displace, but the customer is cost-focused and can in-source "
        "or re-bid — retention and switching-cost evidence matter as much as "
        "growth.",
        "One breach ends the relationship. This is a PHI-handling business "
        "before it is a fee business; the improper-disclosure tail risk is "
        "catastrophic and client-terminating, so the controls, audit history, "
        "and insurance are core diligence, not compliance boilerplate.",
    ],
    connections=default_connections(
        "roi_services",
        deals_sector="roi_services",
        connectors=[
            ("npi_provider",
             "NPI registry — the hospital + physician-practice universe (the "
             "ROI customer base)"),
            ("census_acs_county_profile",
             "Census ACS — county population base for records-demand mapping"),
            ("bls_qcew_industry_area",
             "BLS QCEW — document/records services employment & wages (labor "
             "cost)"),
            ("oig_leie_exclusions",
             "OIG LEIE — excluded individuals/entities (integrity screen)"),
        ],
    ),
    sources=[
        Source("HHS — HIPAA right of access guidance (45 CFR 164.524)", "GOV",
               "https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/access/index.html"),
        Source("Ciox Health, LLC v. Azar, No. 18-cv-0040 (D.D.C. 2020)", "GOV",
               "https://ecf.dcd.uscourts.gov/"),
        Source("ONC — 21st Century Cures Act information-blocking rule", "GOV",
               "https://www.healthit.gov/topic/information-blocking"),
        Source("AHIMA — release-of-information and health-information-"
               "management practice standards", "INDUSTRY",
               "https://www.ahima.org/"),
        Source("HHS OCR — Right of Access Initiative enforcement actions",
               "GOV",
               "https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/agreements/index.html"),
        Source("PE Desk industry deep-dive + realized-deal corpus "
               "(ROI / health-information services)", "INTERNAL",
               "/diligence/tam-sam?template=roi_services"),
    ],
    live_figures=live_figures_from_dive("roi_services"),
    trends=(
        "Release of information industrialized over the last decade: local "
        "hospital HIM shops handing paper copies gave way to national platforms "
        "that embed in the provider, standardize the workflow, and monetize the "
        "attorney/insurer request stream. Two forces then defined the "
        "trajectory. First, Ciox v. Azar (2020) vacated the HHS guidance that "
        "had extended the HIPAA patient-rate fee cap to third-party directives — "
        "a repricing event that restored the industry's ability to bill "
        "attorneys and insurers at market/statutory rates and underpins the "
        "current revenue base. Second, the 21st Century Cures Act information-"
        "blocking rule pushed records toward free, electronic, API-based access "
        "through patient portals and TEFCA/QHIN exchange — a slow structural "
        "erosion of the per-page paper fee. Consolidation continued throughout "
        "(Ciox into Datavant; Verisma acquiring ScanSTAT), leaving a scaled top "
        "tier over a fragmented physician-practice tail. The path forward pits "
        "automation-driven margin expansion and the durable legal-record "
        "product against the gradual disappearance of the paper fee."),
    growth_levers=[
        GrowthLever(
            "Litigation & personal-injury request volume",
            "Attorney requests are the primary fee engine; their volume tracks "
            "litigation activity and the aging, higher-utilization population "
            "that generates records.",
            "primary fee driver", "ILLUSTRATIVE"),
        GrowthLever(
            "Disability & insurance underwriting requests",
            "SSA/disability and life-insurance underwriting generate high-"
            "volume, standardized, fee-bearing requests.",
            "steady volume", "ILLUSTRATIVE"),
        GrowthLever(
            "Ciox v. Azar fee restoration",
            "The 2020 ruling restored market-rate third-party billing — a "
            "one-time repricing that lifted the revenue base per request.",
            "revenue-base step-up", "GOV"),
        GrowthLever(
            "Provider outsourcing & consolidation",
            "As health systems consolidate and shed non-core HIM work, "
            "enterprise ROI outsourcing concentrates spend into the scaled "
            "platforms.",
            "share shift to scale", "ILLUSTRATIVE"),
        GrowthLever(
            "Cures Act free electronic access",
            "Mandated portal/API access and TEFCA exchange erode the per-page "
            "fee model — the structural drag on the growth algorithm.",
            "−per-page fee erosion", "GOV"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Fee-generating third-party request volume (attorney + insurer + "
               "disability)",
        analysis=(
            "The dominant demand driver is the volume of fee-generating third-"
            "party requests — attorney/legal, insurance/commercial, and "
            "disability/SSA — because those are the requests that carry a "
            "statutory fee. That volume is a function of underlying litigation "
            "and claims activity, the size and age of the record-generating "
            "patient population, and the number of provider records the vendor "
            "controls (which grows with each HIM outsourcing win). Patient and "
            "continuity-of-care requests grow with total utilization but are "
            "fee-capped or free, so they add cost and workload without adding "
            "fee revenue. The offsetting drag is the Cures Act shift toward free "
            "electronic access, which converts some fee-bearing requests into "
            "self-service portal downloads — trimming the fee base even as raw "
            "request volume rises."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Records-technician labor",
            "~40-55% of cost",
            "The people who intake requests, verify authorizations, retrieve "
            "records, and process disclosures — the headcount automation is "
            "steadily displacing.", "ILLUSTRATIVE"),
        CostDriver(
            "PHI review & redaction",
            "~10-20% of cost",
            "Minimum-necessary review and sensitive-record redaction "
            "(behavioral health, HIV, Part 2 substance use) — the compliance-"
            "critical, error-intolerant step.", "ILLUSTRATIVE"),
        CostDriver(
            "Provider fee-split / remittance",
            "varies by contract",
            "The share of collected fees remitted to the provider whose records "
            "were disclosed — a direct reduction to net realized revenue.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Technology (auto-redaction, e-delivery, routing)",
            "~10-15% of cost",
            "The platform that scales the workflow and is the margin-expansion "
            "lever versus manual shops.", "ILLUSTRATIVE"),
        CostDriver(
            "Compliance, privacy & breach insurance",
            "~5-10% of cost",
            "PHI-handling controls, audit defense, and cyber/breach coverage — "
            "non-negotiable given the catastrophic mis-disclosure tail.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "ROI is delivered nationally and embedded inside provider HIM "
        "operations, so facility geography is not the structure read. The "
        "geographically meaningful layer is the state medical-records-fee "
        "statute map (per-page caps and search/retrieval fees differ in every "
        "state, which shifts revenue per request) and the density of the "
        "provider customer base — mappable via the NPI and Census connectors "
        "below. No national ROI-vendor roster is vendored, so a computed "
        "facility breakdown is honestly omitted."),
)

register(REPORT)
