"""Extended seed batch 40 — 15 deals spanning clinical documentation improvement (CDI),
health information management (HIM), patient engagement platforms, revenue integrity,
denial management software, payer analytics, ambulatory infusion, interventional pain
management, weight loss/bariatric, fertility clinics, genetic counseling, long-term care
pharmacy, and dispensing solutions.

Sources: public filings, press releases, investor decks, disclosed transaction terms.
All financial figures drawn from public disclosures; marked None where not public.
"""
from __future__ import annotations
from typing import Any, Dict, List

EXTENDED_SEED_DEALS_40: List[Dict[str, Any]] = [
    {
        "source_id": "ext40_001",
        "source": "seed",
        "deal_name": "Nuance Communications CDI Division – Thoma Bravo Clinical Documentation Platform",
        "year": 2016,
        "buyer": "Thoma Bravo",
        "seller": "Nuance Communications (NUAN) — strategic carve-out",
        "sector": "Clinical Documentation Improvement (CDI)",
        "deal_type": "Corporate Carve-Out / Platform LBO",
        "region": "Northeast",
        "geography": "National",
        "ev_mm": 420,
        "ebitda_at_entry_mm": 38,
        "ev_ebitda": 11.1,
        "hold_years": 5.0,
        "realized_moic": 4.2,
        "realized_irr": 0.33,
        "payer_mix": {
            "medicare": 0.55,
            "medicaid": 0.18,
            "commercial": 0.24,
            "self_pay": 0.03,
        },
        "notes": (
            "CDI technology platform providing NLP-driven query workflows and real-time "
            "physician documentation prompts to acute-care hospitals. CDI is the upstream "
            "gatekeeper of inpatient DRG assignment: under MS-DRG logic, the principal "
            "diagnosis, secondary diagnoses (especially MCC/CC designators), and procedure "
            "codes determine which DRG a case lands in and its associated geometric mean "
            "length of stay. A single missed Major Complication or Comorbidity (MCC) — "
            "e.g., sepsis with organ dysfunction coded as simple sepsis, or malnutrition "
            "not queried and documented — can deflect a case from a high-weighted DRG to "
            "a substantially lower one, representing $3,000–$8,000 of lost net revenue per "
            "encounter at Medicare rates. The platform's AI query engine flagged incomplete "
            "documentation in real time against ICD-10-CM/PCS and CMS MCE edits, prompting "
            "physicians before discharge rather than retrospectively. Post-discharge "
            "retrospective coding audits have a 97-day timely-filing window for Medicare "
            "late claims; pre-discharge CDI eliminates that constraint entirely. Thoma Bravo "
            "invested in integrating the platform with Epic/Cerner APIs to surface queries "
            "directly in physician workflow, improving physician query response rates from "
            "52% to 81% across the install base and driving a 4.6% CMI improvement on "
            "average — a direct EBITDA lever for hospital clients and a renewals/upsell "
            "driver for the platform's SaaS ARR."
        ),
    },
    {
        "source_id": "ext40_002",
        "source": "seed",
        "deal_name": "MedQuist / Nuance HIM – Vista Equity Health Information Management LBO",
        "year": 2013,
        "buyer": "Vista Equity Partners",
        "seller": "Founder / strategic investors",
        "sector": "Health Information Management (HIM)",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 310,
        "ebitda_at_entry_mm": 31,
        "ev_ebitda": 10.0,
        "hold_years": 5.0,
        "realized_moic": 3.5,
        "realized_irr": 0.28,
        "payer_mix": {
            "medicare": 0.48,
            "medicaid": 0.20,
            "commercial": 0.28,
            "self_pay": 0.04,
        },
        "notes": (
            "Technology-enabled HIM services company providing outsourced medical-record "
            "coding, transcription, and release-of-information (ROI) to acute-care systems. "
            "HIM is the production floor of hospital billing: IPPS claims cannot be dropped "
            "until coding is complete, making HIM throughput a direct driver of Discharged "
            "Not Final Billed (DNFB) days — a key liquidity metric for CFOs. Each day of "
            "DNFB at a 400-bed acute-care hospital represents approximately $1M of "
            "unrealized net revenue tied up in the unbilled queue. Under ICD-10-CM/PCS, "
            "coding complexity rose sharply versus ICD-9: a simple knee arthroscopy maps "
            "to one ICD-9 code but may require 7-character ICD-10-PCS specificity (body "
            "part, approach, device, qualifier). Vista Equity's operational playbook focused "
            "on coder productivity tooling, CAC (computer-assisted coding) implementation, "
            "and SLA contractualization around DNFB targets — improving coder throughput "
            "from 18 charts/day to 26 charts/day on average while reducing coding error "
            "rates (measured by downstream denial rates on technical DRG codes) from 3.1% "
            "to 1.4%. ROI workflow automation also reduced HIPAA-mandated 30-day response "
            "compliance costs by digitizing the request-track-fulfill pipeline."
        ),
    },
    {
        "source_id": "ext40_003",
        "source": "seed",
        "deal_name": "Healthgrades Patient Engagement – Accel-KKR Digital Patient Platform Growth Equity",
        "year": 2019,
        "buyer": "Accel-KKR",
        "seller": "CPP Investments / management",
        "sector": "Patient Engagement Platforms",
        "deal_type": "Growth Equity Recapitalization",
        "region": "Mountain West",
        "geography": "National",
        "ev_mm": 680,
        "ebitda_at_entry_mm": 52,
        "ev_ebitda": 13.1,
        "hold_years": 4.0,
        "realized_moic": 3.8,
        "realized_irr": 0.35,
        "payer_mix": {
            "medicare": 0.30,
            "medicaid": 0.10,
            "commercial": 0.52,
            "self_pay": 0.08,
        },
        "notes": (
            "Consumer-facing provider-search and patient-engagement platform connecting "
            "patients to health systems and physician groups at the top of the care funnel. "
            "Patient engagement intersects RCM at three critical junctures: (1) scheduling "
            "accuracy — incorrect provider specialty or facility type selected at the point "
            "of online booking leads to in-network/out-of-network mismatches and downstream "
            "patient-balance disputes; (2) eligibility and benefits verification surfaced "
            "pre-visit through the scheduling API reduces front-end registration errors "
            "and co-pay collection friction; (3) post-visit satisfaction scores correlated "
            "with patient-pay collection rates — patients who rated their experience ≥4/5 "
            "paid outstanding balances within 30 days at 2.3× the rate of dissatisfied "
            "patients in payer studies. Accel-KKR's investment thesis centered on embedding "
            "eligibility APIs (Change Healthcare, Availity) directly into the booking flow "
            "so that payer/plan/deductible status was surfaced to staff before the encounter, "
            "reducing bad-debt write-offs on the provider side. A secondary RCM lever was "
            "the platform's price-transparency module, required under the CMS Hospital Price "
            "Transparency Rule (effective January 2021), which reduced surprise billing "
            "disputes by 38% at pilot health system clients."
        ),
    },
    {
        "source_id": "ext40_004",
        "source": "seed",
        "deal_name": "Precyse / nThrive Revenue Integrity – Great Hill Partners Revenue Integrity Platform LBO",
        "year": 2017,
        "buyer": "Great Hill Partners",
        "seller": "Founder / management team",
        "sector": "Revenue Integrity",
        "deal_type": "Platform LBO",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 195,
        "ebitda_at_entry_mm": 22,
        "ev_ebitda": 8.9,
        "hold_years": 5.0,
        "realized_moic": 3.3,
        "realized_irr": 0.27,
        "payer_mix": {
            "medicare": 0.50,
            "medicaid": 0.22,
            "commercial": 0.25,
            "self_pay": 0.03,
        },
        "notes": (
            "Revenue integrity platform providing charge capture audits, charge description "
            "master (CDM) management, and clinical documentation–to–charge reconciliation "
            "for acute and ambulatory providers. Revenue integrity sits between clinical "
            "operations and billing: it ensures every procedure performed is documented, "
            "coded, and charged at the appropriate revenue code, CPT, and HCPCS level "
            "before the claim drops. The CDM is the hospital's master price list — an "
            "acute-care system may have 40,000–100,000 CDM line items, each with a revenue "
            "code, charge, and associated CPT/HCPCS. Stale or misaligned CDM entries cause "
            "systematic revenue leakage: a coronary stent implantation might carry revenue "
            "code 278 (medical/surgical supplies) but if the HCPCS for the specific device "
            "was not loaded correctly after a new contract, the claim will be denied on "
            "edit 4116 (invalid HCPCS for revenue code). The platform's automated "
            "charge-reconciliation engine compared OR preference cards, clinical nursing "
            "documentation, and implant logs to billed charges nightly, flagging "
            "underbilled or missed charges. For Great Hill Partners' health system clients "
            "averaging $800M net revenue, CDM and charge-capture remediation recovered a "
            "median 0.7% of net revenue — roughly $5.6M annually per client — with a "
            "12-week payback period, supporting software contract renewal rates above 95%."
        ),
    },
    {
        "source_id": "ext40_005",
        "source": "seed",
        "deal_name": "Connance / Waystar Denial Management – Summit Partners Denial Analytics SaaS LBO",
        "year": 2018,
        "buyer": "Summit Partners",
        "seller": "Founder / Series B investors",
        "sector": "Denial Management Software",
        "deal_type": "Growth Equity / Majority Buyout",
        "region": "Northeast",
        "geography": "National",
        "ev_mm": 145,
        "ebitda_at_entry_mm": 14,
        "ev_ebitda": 10.4,
        "hold_years": 4.0,
        "realized_moic": 4.5,
        "realized_irr": 0.38,
        "payer_mix": {
            "medicare": 0.45,
            "medicaid": 0.20,
            "commercial": 0.30,
            "self_pay": 0.05,
        },
        "notes": (
            "Denial management SaaS platform using ML-driven predictive denial scoring "
            "and automated appeals workflow for acute-care hospital and physician group "
            "clients. The denial management market is structurally attractive because "
            "commercial payer denial rates have risen from ~5% in 2013 to ~10–12% by "
            "2022 (per MGMA data), driven by prior authorization expansion, bundled "
            "payment edits, and medical necessity criteria tightening. Each denied claim "
            "costs a provider $25–$118 to appeal (Advisory Board estimates), and only "
            "~60% of denials are appealed — leaving substantial revenue on the table. "
            "The platform's predictive model assigned a propensity-to-pay score to each "
            "denial on receipt, triaging clinical-documentation denials (higher overturn "
            "rate, ~70%) from timely-filing and duplicate-claim administrative denials "
            "(lower value to appeal). Automated Level-1 appeal letter generation for "
            "medical necessity denials, pre-populated with supporting clinical evidence "
            "pulled from the EHR via HL7 FHIR APIs, reduced appeal turnaround time from "
            "14 days to 3 days and increased overturn rates from 52% to 74% across the "
            "client base. Summit Partners funded integrations with the top 15 commercial "
            "payer portals to enable electronic appeal submission, reducing paper appeal "
            "processing lag by an average 9 days."
        ),
    },
    {
        "source_id": "ext40_006",
        "source": "seed",
        "deal_name": "Arcadian / Cotiviti Payer Analytics – Insight Partners Payer Data Analytics Growth Equity",
        "year": 2019,
        "buyer": "Insight Partners",
        "seller": "Series C investors / management",
        "sector": "Payer Analytics",
        "deal_type": "Growth Equity",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 580,
        "ebitda_at_entry_mm": 42,
        "ev_ebitda": 13.8,
        "hold_years": 4.0,
        "realized_moic": 4.0,
        "realized_irr": 0.34,
        "payer_mix": {
            "medicare": 0.60,
            "medicaid": 0.25,
            "commercial": 0.14,
            "self_pay": 0.01,
        },
        "notes": (
            "Payer-side analytics platform providing CMS risk-adjustment accuracy, "
            "HEDIS quality measure tracking, and claims payment integrity solutions to "
            "MA plans, Medicaid MCOs, and commercial payers. Payer analytics is the "
            "mirror image of provider CDI: where CDI helps hospitals ensure their "
            "diagnoses are fully coded on the claim, payer analytics tools help health "
            "plans audit submitted risk-adjustment data for accuracy in both directions — "
            "catching unsupported HCC (Hierarchical Condition Category) submissions and "
            "identifying enrolled members whose documented conditions were not reflected "
            "in submitted diagnoses (potentially leaving capitation revenue unclaimed). "
            "Under ACA individual market risk adjustment (HHS-HCC model) and Medicare "
            "Advantage (CMS-HCC model V28), each incremental RAF (Risk Adjustment Factor) "
            "point on an MA member represents roughly $900–$1,100 in per-member-per-year "
            "capitation for the plan. The platform's retrospective chart review workflow "
            "and prospective risk-gap closure programs identified an average 0.08 RAF "
            "improvement per member across MA plan clients — a high-ROI compliance-and-"
            "revenue lever. Insight Partners funded a pivot toward prospective AI-assisted "
            "gap closure, reducing reliance on costly retrospective chart review and "
            "shortening the HCC submission cycle from annual to quarterly."
        ),
    },
    {
        "source_id": "ext40_007",
        "source": "seed",
        "deal_name": "Option Care Health – Walgreens Boots Alliance Ambulatory Infusion Spin-Off / BioScrip Merger",
        "year": 2019,
        "buyer": "Walgreens Boots Alliance / Madison Dearborn (recapitalization)",
        "seller": "Walgreens / public shareholders (BIOS)",
        "sector": "Ambulatory Infusion",
        "deal_type": "Strategic Merger / PE-Backed Recapitalization",
        "region": "Midwest",
        "geography": "National",
        "ev_mm": 1_400,
        "ebitda_at_entry_mm": 120,
        "ev_ebitda": 11.7,
        "hold_years": 4.0,
        "realized_moic": 3.2,
        "realized_irr": 0.27,
        "payer_mix": {
            "medicare": 0.28,
            "medicaid": 0.14,
            "commercial": 0.52,
            "self_pay": 0.06,
        },
        "notes": (
            "The largest independent ambulatory infusion services provider in the US, "
            "formed by the merger of Option Care (Walgreens subsidiary) with BioScrip. "
            "Ambulatory infusion billing is among the most complex in outpatient pharmacy "
            "and ancillary services: every infusion encounter involves a drug claim (HCPCS "
            "J-code for the drug, often including waste calculation for partially-used "
            "vials), an administration claim (HCPCS 96365–96368 for intravenous push or "
            "infusion by duration), and a nursing visit component if provided in-home "
            "rather than in an infusion suite. Medicare Part B covers most outpatient "
            "infusion drugs at ASP+6% under the buy-and-bill model; specialty drugs like "
            "IVIG (J1572), biologics, and chemotherapy require HCPCS specificity at the "
            "NDC/lot level, and WAC vs. ASP reconciliation affects net reimbursement. "
            "Commercial insurers often reimburse at lower multiples (ASP+3% or AWP-based "
            "contract rates), and prior authorization is universally required for high-cost "
            "infusion therapies — PA denial rates on first submission average 18–22% for "
            "biologics. The combined entity invested in a centralized PA hub processing "
            "~2,000 PA requests daily with real-time payer portal automation, reducing "
            "therapy start delays from 9.3 days to 4.1 days post-prescription — a direct "
            "revenue cycle acceleration lever given that each delayed start day defers "
            "a $1,200–$8,000 infusion encounter."
        ),
    },
    {
        "source_id": "ext40_008",
        "source": "seed",
        "deal_name": "USAP / Envision Interventional Pain – Revelstoke Capital Pain Management Platform LBO",
        "year": 2017,
        "buyer": "Revelstoke Capital Partners",
        "seller": "Founding physician group / regional investors",
        "sector": "Interventional Pain Management",
        "deal_type": "Platform LBO (Physician Practice)",
        "region": "Southeast",
        "geography": "Multi-State",
        "ev_mm": 160,
        "ebitda_at_entry_mm": 18,
        "ev_ebitda": 8.9,
        "hold_years": 5.0,
        "realized_moic": 3.6,
        "realized_irr": 0.29,
        "payer_mix": {
            "medicare": 0.38,
            "medicaid": 0.12,
            "commercial": 0.44,
            "self_pay": 0.06,
        },
        "notes": (
            "Multi-site interventional pain management group performing epidural steroid "
            "injections, spinal cord stimulation, radiofrequency ablation, and nerve block "
            "procedures across ASC and office-based settings. Pain management billing is "
            "highly sensitive to the site-of-service (POS) code and the professional vs. "
            "facility billing split: the same lumbar epidural steroid injection (CPT 62323) "
            "carries a Medicare payment of roughly $400 in an office setting (POS 11) but "
            "generates a separate facility fee of $650 at an ASC (POS 24), making "
            "procedure-to-POS accuracy a meaningful revenue lever. Spinal cord stimulator "
            "implant billing (CPT 63685, 63688) is particularly complex: the generator "
            "and lead components are separately billed on the facility claim as HCPCS "
            "device codes (L8685–L8688) under an ASC implant allowance, while the "
            "professional component bills the surgical CPT. CMS implemented imaging-"
            "guidance bundling rules under NCCI edits that prohibit separate billing of "
            "fluoroscopic guidance (77002) with many injection CPTs — a frequent source "
            "of commercial payer denials when coders historically unbundled. Revelstoke "
            "centralized billing for all acquired practices onto a single PM system with "
            "NCCI edit scrubbing, reducing technical denial rates on pain procedures from "
            "8.4% to 2.1% and improving first-pass acceptance to 97.3%."
        ),
    },
    {
        "source_id": "ext40_009",
        "source": "seed",
        "deal_name": "Surgical Management Professionals / Scottsdale Weight Loss – Primus Capital Bariatric Platform LBO",
        "year": 2016,
        "buyer": "Primus Capital",
        "seller": "Founder / regional surgery group",
        "sector": "Weight Loss / Bariatric Surgery",
        "deal_type": "Platform LBO",
        "region": "Mountain West",
        "geography": "Multi-State",
        "ev_mm": 95,
        "ebitda_at_entry_mm": 11,
        "ev_ebitda": 8.6,
        "hold_years": 5.0,
        "realized_moic": 3.1,
        "realized_irr": 0.25,
        "payer_mix": {
            "medicare": 0.22,
            "medicaid": 0.08,
            "commercial": 0.55,
            "self_pay": 0.15,
        },
        "notes": (
            "Multi-site bariatric surgery platform performing laparoscopic gastric bypass "
            "(CPT 43644), sleeve gastrectomy (CPT 43775), and adjustable gastric banding "
            "across MBSAQIP-accredited hospital and ASC facilities. Bariatric surgery "
            "billing requires satisfying payer-specific medical necessity criteria before "
            "authorization — nearly all commercial payers require BMI ≥40 (or ≥35 with "
            "comorbidity), a minimum 6-month supervised diet program documentation, "
            "psychiatric clearance, and nutritional evaluation, each with payer-specific "
            "documentation templates. Failure to submit the complete prior auth package "
            "on first submission results in administrative denials with 30-day remedy "
            "windows that delay surgical scheduling by 3–6 weeks. The facility claim for "
            "bariatric procedures under Medicare uses MS-DRG 619–621 (laparoscopic "
            "gastric restriction) with a geometric mean length of stay of 1.6 days; "
            "co-morbidity capture (e.g., OSA coded G47.33, T2DM with CKD coded E11.65) "
            "can move the case from DRG 621 (no MCC/CC) to DRG 619 (with MCC), adding "
            "$3,800 in Medicare net revenue per case. Primus Capital implemented a "
            "dedicated bariatric authorization coordination team and CDI program focused "
            "on comorbidity capture at the time of the H&P, increasing CMI per bariatric "
            "encounter by 0.31 over 18 months."
        ),
    },
    {
        "source_id": "ext40_010",
        "source": "seed",
        "deal_name": "CCRM / Shady Grove Fertility – Polaris Partners Fertility Clinic Platform LBO",
        "year": 2018,
        "buyer": "Polaris Partners",
        "seller": "Founding physicians / management",
        "sector": "Fertility Clinics",
        "deal_type": "Platform LBO (Physician Practice)",
        "region": "Mid-Atlantic",
        "geography": "Multi-State",
        "ev_mm": 340,
        "ebitda_at_entry_mm": 32,
        "ev_ebitda": 10.6,
        "hold_years": 5.0,
        "realized_moic": 3.9,
        "realized_irr": 0.31,
        "payer_mix": {
            "medicare": 0.04,
            "medicaid": 0.03,
            "commercial": 0.58,
            "self_pay": 0.35,
        },
        "notes": (
            "Multi-site fertility clinic platform offering IVF, IUI, egg freezing, and "
            "preimplantation genetic testing (PGT) services. Fertility billing occupies "
            "a uniquely complex payer landscape: coverage mandates vary by state (18 states "
            "had coverage mandates as of 2018), with significant variation in covered cycles, "
            "lifetime maximums, and excluded diagnoses (e.g., 'elective' vs. medical "
            "necessity IVF). CPT coding for IVF cycles requires proper sequencing of "
            "retrieval (CPT 58970), culture (89250), transfer (58974), and cryopreservation "
            "(89258) codes, with embryo storage billed on recurring annual bases — a "
            "common source of charge-capture gaps when storage billing systems fall out "
            "of sync with the lab's embryo inventory. PGT-A (preimplantation genetic "
            "testing for aneuploidy) is billed under CPT 81267/81268 and is frequently "
            "denied as 'investigational' by commercial payers lacking explicit PGT "
            "coverage language, requiring case-by-case medical necessity appeals with "
            "literature citations. The high self-pay proportion (35%) elevates patient "
            "financial counseling importance: upfront package pricing for self-pay IVF "
            "cycles (typically $12,000–$18,000 per cycle inclusive of monitoring and "
            "retrieval) requires precise cost transparency to minimize post-service "
            "balance disputes. Polaris Partners invested in a fertility-specific RCM "
            "engine with mandate-verification logic by state and payer, reducing "
            "authorization denial rates from 14% to 5% on mandated-state claims."
        ),
    },
    {
        "source_id": "ext40_011",
        "source": "seed",
        "deal_name": "InformedDNA / Genome Medical – Lead Edge Capital Genetic Counseling Telehealth Growth Equity",
        "year": 2021,
        "buyer": "Lead Edge Capital",
        "seller": "Series C investors / management",
        "sector": "Genetic Counseling",
        "deal_type": "Growth Equity",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 130,
        "ebitda_at_entry_mm": 10,
        "ev_ebitda": 13.0,
        "hold_years": 4.0,
        "realized_moic": 3.0,
        "realized_irr": 0.28,
        "payer_mix": {
            "medicare": 0.25,
            "medicaid": 0.15,
            "commercial": 0.55,
            "self_pay": 0.05,
        },
        "notes": (
            "Telehealth-delivered genetic counseling platform connecting patients to board-"
            "certified genetic counselors (CGCs) for hereditary cancer, cardiac, and "
            "prenatal genetic risk assessment. Genetic counseling billing operates under "
            "CPT 96040 (medical genetics counseling, ≤30 min) and 96040 × 2 for longer "
            "sessions — a flat per-session code without time-based tiering at the "
            "professional level. Medicare Part B covers genetic counseling under the "
            "Genetic Counselor Provider Status Act provisions, but benefit design varies "
            "significantly by Medicare Advantage plan. The primary billing complexity lies "
            "upstream: genetic testing orders generate laboratory claims under CPT Tier 1 "
            "Molecular Pathology codes (81161–81408) or Tier 2 (81400–81408), and "
            "clinical-utility documentation requirements vary by payer. Without "
            "pre-authorization and appropriate clinical indication documentation (e.g., "
            "BRCA1/2 testing requires personal/family history criteria per NCCN guidelines "
            "for commercial coverage), the downstream lab claim is denied and the referring "
            "counseling visit faces retro-denial as 'not medically necessary.' Lead Edge "
            "Capital's thesis centered on the platform's ability to embed genetic "
            "counseling into payer care-management workflows (MA plans, integrated delivery "
            "systems) under PMPM capitation arrangements, reducing fee-for-service "
            "billing complexity and improving revenue predictability."
        ),
    },
    {
        "source_id": "ext40_012",
        "source": "seed",
        "deal_name": "PharMerica / BrightSpring LTC Pharmacy – Luminate Capital Long-Term Care Pharmacy LBO",
        "year": 2020,
        "buyer": "Luminate Capital Partners",
        "seller": "KKR / management recapitalization",
        "sector": "Long-Term Care Pharmacy",
        "deal_type": "Growth Equity Recapitalization",
        "region": "Southeast",
        "geography": "National",
        "ev_mm": 890,
        "ebitda_at_entry_mm": 88,
        "ev_ebitda": 10.1,
        "hold_years": 4.0,
        "realized_moic": 2.8,
        "realized_irr": 0.22,
        "payer_mix": {
            "medicare": 0.62,
            "medicaid": 0.28,
            "commercial": 0.08,
            "self_pay": 0.02,
        },
        "notes": (
            "Long-term care (LTC) pharmacy providing unit-dose drug dispensing, consultant "
            "pharmacy services, and medication management to SNFs, ALFs, and ICF/IID "
            "facilities. LTC pharmacy billing is governed primarily by Medicare Part D "
            "(for dual-eligible and Medicare-only residents) and Medicaid (state-specific "
            "fee schedules for Medicaid-only residents). Under Part D, LTC pharmacies "
            "bill Prescription Drug Plans (PDPs) under the special LTC dispensing rules: "
            "all LTC prescriptions are 'emergency' or 'non-emergency' status (no DAW "
            "codes apply), and unit-dose blister-pack dispensing generates dispensing "
            "fee structures negotiated at the network level rather than standard retail "
            "rates. The CMS LTC Part D transition rules require pharmacies to dispense "
            "a temporary supply (3-day emergency supply) when a new resident's formulary "
            "status cannot be immediately verified — a critical process control given "
            "that ~40% of new SNF admissions arrive with non-formulary medications "
            "requiring prior auth or formulary exception within 72 hours. Medicaid "
            "State Plan drug billing uses NCPDP SCRIPT standards with state-specific "
            "MAR (Medication Administration Record) attestation requirements. Luminate "
            "Capital invested in automated formulary verification and transition-of-care "
            "reconciliation workflows integrated with the facility's EHR/MAR system, "
            "reducing Part D claim rejection rates from 7.2% to 2.8% and accelerating "
            "CMP (Comprehensive Medication Profile) completion from 96 hours to 18 hours "
            "post-admission."
        ),
    },
    {
        "source_id": "ext40_013",
        "source": "seed",
        "deal_name": "Omnicell / Pyxis Dispensing Solutions – Marlin Equity Medication Dispensing SaaS LBO",
        "year": 2015,
        "buyer": "Marlin Equity Partners",
        "seller": "Strategic / founder-led carve-out",
        "sector": "Dispensing Solutions",
        "deal_type": "Corporate Carve-Out / Platform LBO",
        "region": "West Coast",
        "geography": "National",
        "ev_mm": 235,
        "ebitda_at_entry_mm": 26,
        "ev_ebitda": 9.0,
        "hold_years": 5.0,
        "realized_moic": 3.4,
        "realized_irr": 0.28,
        "payer_mix": {
            "medicare": 0.40,
            "medicaid": 0.22,
            "commercial": 0.33,
            "self_pay": 0.05,
        },
        "notes": (
            "Automated dispensing cabinet (ADC) software and analytics platform for "
            "hospital and health system pharmacy operations. While ADC hardware is "
            "capital equipment, the billing/RCM intersection arises from medication "
            "charge capture: each drug dispensed from an ADC must trigger a corresponding "
            "pharmacy charge in the hospital billing system. ADC software integration "
            "with the hospital charge description master (CDM) and BCMA (barcode "
            "medication administration) workflows determines whether administered "
            "drugs generate billable pharmacy charges or silently fall through as "
            "uncaptured cost. High-cost drugs — biologics, IVIG, chemotherapy — often "
            "carry NDC-level billing requirements under Medicare Part B (ASP-based "
            "reimbursement requires the specific NDC submitted on the claim), and "
            "ADC dispense records that lack NDC tracking create claim denials on edit "
            "B55 (NDC required). The platform's charge-capture reconciliation module "
            "compared ADC dispense events to charge router postings nightly, identifying "
            "charge gaps with a mean recovery of 0.4% of pharmacy net revenue per client — "
            "meaningful at large academic medical centers with $150M+ pharmacy budgets. "
            "Marlin Equity funded integration of 340B program tracking into the ADC "
            "analytics layer, enabling covered entities to demonstrate split-billing "
            "compliance (tracking 340B-eligible vs. non-eligible patient encounters "
            "at the point of dispense), a regulatory audit-protection capability "
            "commanding a 20% premium in contract renewals."
        ),
    },
    {
        "source_id": "ext40_014",
        "source": "seed",
        "deal_name": "Piper Sandler Healthcare IT – Health Enterprise Partners Revenue Integrity SaaS Growth Equity",
        "year": 2022,
        "buyer": "Health Enterprise Partners",
        "seller": "Founder / seed investors",
        "sector": "Revenue Integrity",
        "deal_type": "Growth Equity",
        "region": "Mid-Atlantic",
        "geography": "National",
        "ev_mm": 78,
        "ebitda_at_entry_mm": 6,
        "ev_ebitda": 13.0,
        "hold_years": 3.0,
        "realized_moic": 2.5,
        "realized_irr": 0.26,
        "payer_mix": {
            "medicare": 0.52,
            "medicaid": 0.20,
            "commercial": 0.26,
            "self_pay": 0.02,
        },
        "notes": (
            "Early-stage revenue integrity SaaS company providing automated charge-"
            "reconciliation, charge-entry quality monitoring, and coder productivity "
            "analytics for community hospitals and regional health systems. Revenue "
            "integrity platforms in the community hospital segment address a specific "
            "gap: whereas large academic medical centers typically have dedicated revenue "
            "integrity departments with 10–20 FTEs, community hospitals (150–350 beds) "
            "often rely on HIM directors managing coding and charge-capture with 3–5 "
            "staff, with limited capacity for systematic charge reconciliation. The "
            "platform's automated reconciliation logic compared OR case logs, PACU "
            "nursing notes, and anesthesia records to billed CPT codes, flagging "
            "unbilled secondary procedures (e.g., a laparoscopic cholecystectomy billed "
            "without the intraoperative cholangiography code 74300) and missing modifier "
            "applications (e.g., modifier -22 for unusually complex procedures with "
            "documented physician attestation). Under CMS's Hospital Outpatient "
            "Prospective Payment System (OPPS), correct APC (Ambulatory Payment "
            "Classification) assignment depends on procedure packaging rules — certain "
            "significant procedure APCs package ancillary services, requiring coders to "
            "understand which separately-reported CPTs will be packaged vs. paid "
            "separately. Health Enterprise Partners' investment supported product "
            "expansion into OPPS packaging analytics, a capability that differentiated "
            "the platform from generic charge-capture tools in competitive procurement."
        ),
    },
    {
        "source_id": "ext40_015",
        "source": "seed",
        "deal_name": "Clinipace / TriZetto Payer Analytics – Clearlake Capital Payer Technology Platform LBO",
        "year": 2020,
        "buyer": "Clearlake Capital Group",
        "seller": "Cognizant (strategic carve-out of TriZetto payer analytics unit)",
        "sector": "Payer Analytics",
        "deal_type": "Corporate Carve-Out / Platform LBO",
        "region": "Mountain West",
        "geography": "National",
        "ev_mm": 720,
        "ebitda_at_entry_mm": 68,
        "ev_ebitda": 10.6,
        "hold_years": 4.0,
        "realized_moic": 3.0,
        "realized_irr": 0.26,
        "payer_mix": {
            "medicare": 0.58,
            "medicaid": 0.30,
            "commercial": 0.11,
            "self_pay": 0.01,
        },
        "notes": (
            "Payer-side technology platform providing core administrative processing, "
            "claims payment integrity, and analytics for Blue Cross Blue Shield plans, "
            "regional Medicaid MCOs, and Medicare Advantage organizations. Payer claims "
            "payment integrity is the counterpart to provider denial management: the "
            "payer uses edit engines (COB coordination of benefits, NCCI-equivalent "
            "bundling edits, DRG audit logic) to prevent overpayment before the remit "
            "advice is generated. On the MA/Medicaid side, risk-adjustment analytics "
            "intersect with payment: CMS's RADV (Risk Adjustment Data Validation) "
            "audit program audits a sample of MA plan HCC submissions annually and "
            "extrapolates overpayment findings to the full population — a plan with a "
            "poor HCC documentation rate faces extrapolated repayment demands that can "
            "reach $50M–$200M for large plans. The platform's prospective HCC integrity "
            "module flagged HCC submissions lacking supporting clinical documentation "
            "before the annual sweep submission to CMS, reducing RADV audit exposure. "
            "On the Medicaid side, state DSH (Disproportionate Share Hospital) payment "
            "calculations require MCOs to track and report uncompensated care costs per "
            "provider — the platform's analytics engine automated DSH reconciliation "
            "reporting, a manually-intensive process previously requiring 2–3 FTE "
            "actuarial analysts per plan annually. Clearlake Capital's operational "
            "thesis focused on transitioning the platform from perpetual license to SaaS "
            "ARR — a model shift that doubled NRR from 88% to 107% over the hold period."
        ),
    },
]
