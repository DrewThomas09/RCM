# Building the Definitive RCM Diligence Platform: A Public-Data-Only Strategy for SeekingChartis / RCM-MC

> **Status: PARTIAL — transmitted message was truncated at the 50,000-character tool-input limit mid Moat Layer 6 (Part 4). The remainder (Moat Layer 7, Parts 5+, and the 24–36 month roadmap) needs to be pasted in a follow-up message so this document can be completed.**

## Executive Brief

This is the comprehensive blueprint for transforming SeekingChartis / RCM-MC into the definitive healthcare PE RCM diligence platform using only publicly available data and open-source software. The thesis: when every data source is public, the moat is not data access but curation, interpretation, and speed. Specifically, the moat lives in five compound layers: (1) a versioned, continuously-refreshed knowledge graph of every RCM regulation, guideline, and failure pattern; (2) proprietary benchmark curves computed from public claims and cost-report data at specialty-payer-region slices no existing vendor publishes; (3) a "named-failure library" that pattern-matches live deals against every healthcare PE bankruptcy since 2015; (4) a backtesting harness that proves the platform would have flagged Steward, Envision, APP, Cano, Prospect, and Wellpath at the relevant decision points; and (5) an adversarial diligence engine that automatically argues the bear case against management's thesis.

Public-data-only is not a limitation — it is a recruiting asset (open-source contributors care), a distribution asset (auditors and regulators trust transparent methodology), and a cost-structure asset (zero per-engagement data-license cost means the platform can underprice any consulting firm's tooling). The paid datasets we're foregoing (MGMA comp, Definitive Healthcare, PitchBook, Green Street) are replaceable with IRS 990 Schedule J, Physician Compare + Open Payments, SEC EDGAR + HSR early termination notices, and REIT 10-K lease schedules, respectively. The substitutions are 70–90% fidelity at zero marginal cost and zero BAA complexity.

The realistic build horizon is 24–36 months to a platform that legitimately claims "the best open-source RCM diligence platform ever built." The path runs through three phases: Year 1 (knowledge ingestion + core analytical modules + first three design partners), Year 2 (proprietary benchmark library + advanced ML + first published methodology papers), Year 3 (institutional positioning + backtesting validation + acquisition-ready or strategic-partnership-ready). This report is the exhaustive source material for 20–30 follow-on coding prompts.

---

## Part 1: The Full RCM Knowledge Corpus — Textbooks, Training, and Standards

The first moat layer is codified institutional knowledge. Healthcare revenue cycle expertise is scattered across HFMA certifications, AHIMA/AAPC coding curricula, CMS manuals, OIG guidance, NCCI policy, and accumulated consultant tribal knowledge. Nobody has assembled this into a queryable, versioned knowledge graph. The platform that does becomes the reference implementation.

### HFMA (Healthcare Financial Management Association)

HFMA is the authoritative US source for healthcare financial methodology. Core ingestible assets:

- **HFMA MAP Keys** — the industry-standard performance indicators for revenue cycle. HFMA's MAP program defines standardized KPI calculations across five categories (Patient Access, Clinical Charge Capture, Pre-Billing/Claims Production, Claims Adjudication, Customer Service) and publishes MAP Keys definitions publicly. The MAP App tool and benchmark reports are paid, but the definitions, calculation methodologies, and white papers are freely accessible. **Ingestion strategy:** scrape the HFMA MAP Keys definitions page and methodology whitepapers; encode each KPI's numerator, denominator, and exclusion logic as machine-readable specifications. Update cadence: annually.
- **HFMA certifications** — CRCR (Certified Revenue Cycle Representative), CHFP (Certified Healthcare Financial Professional), CSAF (Certified Specialist Accounting & Finance), CSMR (Certified Specialist in Managed Reimbursement), CSPR (Certified Specialist Physician Practice Management). Study guides and domain outlines are publicly documented, though exam content is proprietary. **Ingestion strategy:** extract the certification body-of-knowledge outlines as taxonomy scaffolds.
- **HFMA white papers and thought leadership** — hundreds of free papers across RCM, cost accounting, strategic finance. **Ingestion strategy:** scrape the HFMA resources library quarterly; tag papers by topic; feed into the regulatory/methodology RAG corpus.

### AAPC (American Academy of Professional Coders)

- CPC (Certified Professional Coder), CPMA (Certified Professional Medical Auditor), CPB (Certified Professional Biller) curriculum outlines. AAPC publishes study guides and practice-question topics publicly. **Ingestion strategy:** scrape curriculum outlines and AAPC Knowledge Center articles; tag by code type (E/M, surgery, radiology, pathology, medicine, HCPCS).
- AAPC coding guideline archives — monthly *Healthcare Business Monthly* articles, free blog posts on modifier use, NCCI edits, denial reasons. **Ingestion strategy:** scrape quarterly.

### AHIMA (American Health Information Management Association)

- CCS (Certified Coding Specialist), CCA (Certified Coding Associate), RHIT (Registered Health Information Technician), RHIA (Registered Health Information Administrator) certification domain outlines. **Ingestion strategy:** scrape domain outlines as taxonomy.
- **AHIMA Computer-Assisted Coding Toolkit** — this is the public document that sets the 97%+ accuracy threshold for straight-to-bill CAC discussed in earlier research. **Ingestion strategy:** ingest as authoritative benchmark for autonomous-coding quality claims.
- **AHIMA Clinical Documentation Integrity (CDI) standards** — the 2021 AHIMA/ACDIS guidelines for query practice. **Ingestion strategy:** encode as rules for the platform's chart-audit sampling recommendations.

### AMA (American Medical Association)

- **CPT code set** — licensed by AMA. CPT codes themselves are not freely redistributable without license. **Workaround:** use the public HCPCS Level II codes (CMS, free) for procedures, and reference CPT codes by code number only (fair use) without redistributing the descriptors. For full CPT descriptions, require users to have their own AMA license and ingest descriptors at runtime via their license. **Flag for licensing review.**
- CPT Assistant archives — paid subscription, but many articles are discussed in free secondary literature. **Workaround:** use CMS NCD (National Coverage Determinations) and LCD (Local Coverage Determinations) for coverage policy, which are fully public.

### CMS Publications — The Deepest Regulatory Corpus

This is the single most important corpus. Every document is public, structured, and updated on published schedules.

- **Medicare Claims Processing Manual (Pub 100-04)** — 39 chapters covering every claim type (inpatient, outpatient, physician, DME, home health, hospice, etc.). Each chapter is a public PDF/HTML document. **Ingestion strategy:** quarterly scrape; parse by section; embed with medical-domain embedding model (PubMedBERT, BioBERT); create chapter-level RAG index. This becomes the ground truth for "is this billing practice compliant?"
- **Medicare Benefit Policy Manual (Pub 100-02)** — 16 chapters covering coverage policy. Same ingestion pattern.
- **Medicare Program Integrity Manual (Pub 100-08)** — 15 chapters covering audit, investigation, and enforcement. This is the manual the RAC (Recovery Audit Contractors), UPIC (Unified Program Integrity Contractors), and SMRC (Supplemental Medical Review Contractor) operate from. Critical for audit-exposure modeling. **Ingestion strategy:** quarterly scrape; cross-reference with OIG Work Plan findings.
- **Medicare General Information, Eligibility, and Entitlement Manual (Pub 100-01)** — foundational eligibility rules.
- **Medicare Managed Care Manual (Pub 100-16)** — MA plan rules, including V28 risk adjustment implementation.
- **MLN Matters articles** — CMS's official guidance distribution channel for billers. Thousands of articles, each dated, each superseding prior guidance. **Ingestion strategy:** monthly scrape; parse version history; flag deprecated guidance.
- **NCCI Policy Manual and Edit Tables** — the National Correct Coding Initiative publishes quarterly edit tables showing which CPT/HCPCS pairs cannot be billed together (Procedure-to-Procedure edits), units-of-service limits (Medically Unlikely Edits), and modifier-override rules. **Ingestion strategy:** quarterly download of edit tables; parse into SQLite; run every target's historical claims through edit-compliance check as a risk flag. This alone is a killer feature because no consulting firm does this at scale pre-close.
- **CMS Coverage Determinations** — NCDs (national) and LCDs (local, published by Medicare Administrative Contractors / MACs). Public, structured, available via the Medicare Coverage Database API. **Ingestion strategy:** quarterly pull; index by CPT/HCPCS; feed into target-specific coverage-risk analysis.
- **Quarterly CPT/HCPCS/ICD-10 Update Releases** — official quarterly updates published by CMS. **Ingestion strategy:** automated quarterly ingestion.

### OIG (HHS Office of Inspector General)

- **OIG Work Plans** — 2015 through current. Published quarterly, they list exactly what audit topics OIG is investigating. **Ingestion strategy:** scrape each Work Plan; tag by provider type, service line, and compliance topic; use as forward-looking audit-risk signal ("your cardiology practice bills these stress tests at a rate OIG is actively investigating").
- **OIG Audit Reports** — thousands of published audit findings with specific dollar recoveries. **Ingestion strategy:** scrape; structure by provider, service line, finding type; use for named-failure pattern matching.
- **OIG Corporate Integrity Agreements (CIAs)** — public documents. **Ingestion strategy:** scrape; index by provider; cross-reference with transaction targets as a hard red flag.
- **OIG Compliance Program Guidance** — the foundational documents for healthcare compliance programs. Multiple sector-specific versions (Hospitals 1998/2005/2024, Physicians 2000, Nursing Facilities, Third-Party Billing, Hospices, DME, Pharmaceutical Manufacturers). **Ingestion strategy:** ingest as structured rulebook; use for compliance-readiness scoring.
- **OIG Advisory Opinions** — binding responses to specific arrangements under AKS, Stark, and civil monetary penalties. **Ingestion strategy:** scrape; extract fact patterns and conclusions; use for compensation-arrangement red-line analysis.
- OIG Self-Disclosure Protocol public filings.

### ICD-10 and Coding Guidelines

- **ICD-10-CM Official Guidelines for Coding and Reporting** — CDC publishes annually. Public PDF. **Ingestion strategy:** annual ingestion; parse section-by-section; use as ground truth for coding-compliance rules.
- **ICD-10-PCS Official Guidelines** — CMS publishes annually for inpatient procedural coding.
- **ICD-10-CM/PCS full code set** — fully public from CDC NCHS and CMS. **Ingestion strategy:** annual full load; diff vs. prior year to flag newly-valid and newly-invalid codes.

### Uniform Billing Standards

- **NUBC (National Uniform Billing Committee)** — publishes UB-04 implementation guidance. **Ingestion strategy:** scrape public specifications and quarterly updates.
- **NUCC (National Uniform Claim Committee)** — CMS-1500 claim form standards. Free public download.
- **X12 TR3 Implementation Guides** for 837 (Institutional, Professional, Dental) and 835 — **licensing caveat:** X12 charges for the formal TR3 guides. **Workaround:** the CMS/WPC published EDI technical guides cover implementation at sufficient detail for ingestion, and the Stedi open components include 837/835 parser logic. The platform already has a working X12 parser, which means the TR3 license issue is mostly moot.

### Academic and Open Textbook Resources

- **OpenStax** — free peer-reviewed textbooks. No healthcare finance title yet, but *Principles of Management* and *Principles of Accounting* are general-purpose useful.
- **OER Commons** — aggregated open educational resources including some healthcare administration courseware.
- **NCBI Bookshelf** — thousands of free biomedical books including relevant clinical documentation and health services research texts.
- **MIT OpenCourseWare** — HST.930 Biomedical Informatics, 15.575 Economics of Information, various health policy courses. Free lecture notes and problem sets.
- **Johns Hopkins Bloomberg School Open Courseware** — limited free materials.
- **Duke-Margolis Center for Health Policy** — free white papers on payment policy, MA, value-based care.
- **Kaiser Family Foundation (KFF)** — thousands of free, citable reports on Medicare, Medicaid, marketplace, drug pricing, payer-mix dynamics. **Ingestion strategy:** quarterly scrape; tag by topic; use as reference layer for trend analysis.
- **Congressional Research Service (CRS) reports** — now public since the 2018 directive. Every major healthcare policy issue has a CRS report. **Ingestion strategy:** monthly scrape of new/updated reports; tag by committee and topic.
- **MedPAC and MACPAC reports** — quarterly data books, June/March reports, recommendations. Authoritative on Medicare and Medicaid payment policy. **Ingestion strategy:** full archive ingestion + quarterly updates.
- **Commonwealth Fund, Urban Institute, Brookings, RAND Health** publications — open white papers.

### Legal and Regulatory Texts — The Primary Sources

- **Code of Federal Regulations (CFR), Title 42** — Medicare and Medicaid regulations. Fully public via eCFR.gov with stable API. **Ingestion strategy:** nightly snapshot of Title 42; diff to detect amendments; parse by section; create RAG index for regulatory-compliance queries.
- **CFR Title 45, Subtitle A, Subchapter C** — HIPAA Privacy, Security, and Breach Notification rules.
- **US Code Title 42** — the underlying statute.
- **Federal Register** — proposed and final rules, public comments, deadlines. Fully public with API. **Ingestion strategy:** daily scrape; tag healthcare-relevant rules; use for forward-looking regulatory calendar.
- **Regulations.gov** — public comment dockets.
- FDA Drug Approvals, 510(k) device clearances — fully public.

### Specialty-Specific Reference Literature

For each major provider-type the platform diligences, curate the specialty association's public guidance:

- **ACEP (American College of Emergency Physicians)** — NSA resources, coding guidance
- **SHM (Society of Hospital Medicine)** — hospitalist-specific guidance
- **ASA (American Society of Anesthesiologists)** — anesthesia coding, NSA implications
- **ACR (American College of Radiology)** — imaging coding and appropriate-use criteria
- **AGA (American Gastroenterological Association), ACG** — GI coding and payment
- **AAOS (American Academy of Orthopaedic Surgeons)** — MSK coding and bundled-payment implications
- **ACC (American College of Cardiology)** — cardiology coding and AUC
- **ADA (American Dental Association)** — dental coding (CDT is ADA-licensed, same CPT-like constraint)
- **ANA (American Nurses Association)** nursing staffing standards
- **ACOG, AAP, AAFP** — specialty physician guidance

**Ingestion strategy for specialty corpora:** annually-refreshed scrape of each specialty society's free public library, tagged by specialty. Feed into a specialty-aware RAG retrieval layer so that when a target is diligenced, only the relevant specialty's literature informs the analysis.

---

## Part 2: The Public Data Stack — Every Dataset Worth Ingesting

This section catalogs every public healthcare dataset worth ingesting beyond what SeekingChartis already has, with access method, update cadence, unique analytical value, and Python tooling.

### CMS Datasets (Core Expansion)

**Medicare Provider Utilization and Payment Data** — Part B, Part D, DME, Referring Physician. Claim-level summary by NPI × HCPCS/service × year. ~10M rows/year for Part B Physicians, ~2M rows for Part D Prescribers, ~1M for DME Suppliers, ~5M for Referring Physicians DME. CMS publishes annually with ~2-year lag. Downloadable as CSV or queryable via Socrata API at data.cms.gov. **Unique value:** lets the platform compute provider-level benchmarks for any target without needing the target's own billing data. Combined with Open Payments, this is enough to build a baseline CPT-level revenue and utilization profile for most mid-to-large physician groups before they even open a data room. **Ingestion strategy:** full annual load into DuckDB-backed warehouse; incremental refresh on publication.

**Medicare Post-Acute Care Utilization Files** — Home Health, SNF, Hospice, LTCH, IRF. Same pattern as Part B but covering post-acute. **Unique value:** post-acute is where PE money has flowed heavily (Amedisys, LHC, Encompass, Aveanna, home health rollups). No existing diligence tool ingests this systematically at the provider level.

**Provider of Services (POS) File** — every Medicare-certified facility with facility type, ownership, beds, services. Quarterly. **Ingestion strategy:** quarterly refresh; use as target facility master data.

**Chronic Conditions Data Warehouse (CCW) / Beneficiary-Level Data** — requires Data Use Agreement; the public LDS (Limited Data Sets) versions have 5% beneficiary samples. **Caveat:** CCW data with PHI requires DUA, which may complicate the open-data story. **Alternative:** use CCW Public Use Files (fully de-identified aggregates) which are free.

**Open Payments (Sunshine Act)** — every payment from drug/device makers to physicians and teaching hospitals since 2013. Public, bulk downloadable, ~$12B/year in payments reported, ~1.5M physicians and hospitals. **Unique value:** conflict-of-interest signal, physician-loyalty risk (docs heavily paid by one manufacturer may switch prescribing post-close if the manufacturer is displaced). Also used to detect compensation arrangements that may raise AKS concerns. **Ingestion strategy:** full historical + annual refresh; join to NPI registry; compute per-physician payment concentration.

**NPPES (National Plan and Provider Enumeration System) / NPI Registry** — every provider with NPI, practice locations, taxonomy codes, updates. Daily-refreshable. **Unique value:** provider master data, practice-location mapping, taxonomy-based specialty classification. **Ingestion strategy:** monthly full refresh; nightly incremental; use for synthetic-FTE detection (reconcile billed NPIs vs. claimed staff).

**PECOS (Provider Enrollment, Chain, and Ownership System)** — Medicare-enrolled provider enrollment status. Limited public extract; full via FOIA. **Unique value:** enrollment-status risk signal.

**CMS Innovation Center model datasets** — BPCI-Advanced (Bundled Payments for Care Improvement Advanced), ACO REACH, MSSP (Medicare Shared Savings Program) public performance data, Direct Contracting legacy, TEAM baseline data when released. Free, annual. **Ingestion strategy:** annual ingestion of each model's performance files; compute target's historical bundle performance if applicable.

**Medicare Advantage enrollment by county, benchmark rates, Star Ratings** — all fully public. **Ingestion strategy:** annual refresh of benchmark rates; monthly Star Ratings; county-level enrollment data for market-penetration maps.

**Geographic Variation Public Use File** — Medicare spending and utilization by geographic area. Annual.

**Hospital Service Area File** — crosswalk of ZIP codes to hospital market areas.

**Market Saturation and Utilization Tool** — CMS's own market-concentration analysis at HRR/HSA level.

**HRRP (Hospital Readmissions Reduction Program) Hospital Specific Reports** — per-hospital readmission rates and penalties. **Unique value:** forward-looking penalty projection.

**Hospital VBP (Value-Based Purchasing) data** — per-hospital TPS (Total Performance Score) and payment adjustment.

**HAC Reduction Program data** — Hospital-Acquired Condition quartile rankings.

**CMS Quality Payment Program (MIPS/APM) data** — per-clinician MIPS scores. Annual.

**Medicare Cost Reports (HCRIS) Extended Fields** — SeekingChartis already ingests HCRIS, but the worksheets beyond the standard summaries (S-3, Part II staffing; S-10 uncompensated care; E Part A; G series balance sheet; M series for home health; etc.) contain fields rarely mined. **Expansion strategy:** go worksheet-by-worksheet; parse every field; build a field-level benchmark distribution library.

**Medicare Fee Schedule Lookup** — every CPT/HCPCS payment rate by locality. Quarterly. **Ingestion strategy:** quarterly full load; use as payment-rate reference for unbundling detection and rate modeling.

### AHRQ and HCUP

**HCUPnet** — AHRQ's free web-based query system for national and state inpatient/ED/ambulatory surgery statistics. Limited to aggregate queries; record-level HCUP data is paid. **Workaround:** scrape HCUPnet queries at the maximum granularity available to build a benchmark library by DRG × payer × region × year.

**AHRQ Quality Indicators Software** — fully free, open-source. PQI (Prevention), IQI (Inpatient), PSI (Patient Safety), PDI (Pediatric) indicators. Historically Windows-only SAS; **critical finding:** AHRQ has released Python/SQL-based versions in recent years, and there are community ports available. **Ingestion strategy:** integrate AHRQ QI software as a runtime dependency; run every target's discharge data through QI calculations; compute penalty projections.

**Medical Expenditure Panel Survey (MEPS)** — AHRQ's annual survey of health expenditures. Public microdata. **Unique value:** patient-level utilization and expenditure patterns, useful for modeling patient-pay exposure and market-segmentation questions.

### CDC Datasets

- **CDC WONDER** — mortality, natality, vaccine safety, cancer registry data, all via free query interface. **Unique value:** outcome-based context for surgical and specialty rollups.
- **National Health Interview Survey (NHIS)** microdata — annual, public.
- **BRFSS (Behavioral Risk Factor Surveillance System)** — state-level health indicators, annual.
- **National Notifiable Diseases Surveillance System** — public.
- **CDC Vital Statistics** — mortality, natality.

### IRS 990 Corpus

- **AWS Open Data Registry IRS 990 corpus** — every electronically-filed 990 since 2011, in raw XML, publicly available via S3. ~2.5M filings. **Unique value:** per-organization compensation disclosures (Schedule J — lists officer/director/key-employee comp for nonprofits and certain other orgs), community benefit (Schedule H for hospitals, includes charity care, bad debt, Medicaid shortfall, unreimbursed costs), governance (Schedule A, O), transactions (Schedule R for related orgs). **Ingestion strategy:** full historical load via AWS S3 direct; parse XML per schedule; build annual benchmark distributions. **Schedule J gives you physician-and-executive compensation benchmarks that substitute substantially for MGMA/Sullivan Cotter data for nonprofit and academic medical centers, which is a huge piece of the benchmark moat.**
- **IRS Business Master File** — every exempt org with EIN, NTEE code, status. Free.
- **IRS Publication 78 (Tax Exempt Org Search)** — current.

### State Datasets

- **All-Payer Claims Databases (APCDs)** — 20+ states now have APCDs. Free public extracts from New Hampshire, Colorado, Maine, Maryland, Massachusetts (partial via CHIA), Minnesota, Utah, Vermont, Washington. Others have paid or restricted access. **Unique value:** claims-level data across commercial payers in addition to Medicare. This is genuinely rare and valuable.
- **California Department of Health Care Access and Information (HCAI, formerly OSHPD)** — the largest and most granular state dataset in the country. Hospital financial data, licensed facility data, discharge data (aggregate public; record-level requires request), health-professions workforce data, community-benefit plans, fair pricing, MIRCal (inpatient, outpatient, ED discharges). **Ingestion strategy:** bulk downloads of every public HCAI dataset; quarterly refresh.
- **Florida AHCA** — hospital discharge data, financial reports, facility data.
- **Texas DSHS** — Texas hospital inpatient discharge data (THCIC), annual public use files with de-identified record-level data.
- **New York SPARCS (Statewide Planning and Research Cooperative System)** — hospital discharge and ambulatory surgery data. De-identified limited version public.
- **Oregon Health Authority** — hospital discharge, financial data.
- **Washington Comprehensive Hospital Abstract Reporting System (CHARS)** — hospital discharge data.
- **Massachusetts Center for Health Information and Analysis (CHIA)** — APCD, hospital financial performance, cost-trends analysis.
- **State transaction review filings** — California OHCA (Office of Health Care Affordability) material change notices are public, listing every healthcare transaction >$25M; Oregon HCMO (Health Care Market Oversight) reviews public; Massachusetts HPC (Health Policy Commission) material change reviews public; Connecticut OHS transaction reviews; Illinois (emerging); Indiana (emerging); New Mexico (emerging); Washington (emerging HB 2548). **Ingestion strategy:** quarterly scrape of each state's filing portal; feed into the CPOM/transaction-review risk engine from Gap 4.
- **State licensure and enforcement data** — every state medical board publishes disciplinary actions; every state health department publishes facility-licensing actions. Varies widely in accessibility. **Ingestion strategy:** prioritized scrape of the top 15 states by healthcare PE activity (CA, TX, FL, NY, PA, OH, IL, GA, NC, NJ, MA, MI, WA, VA, TN).
- **State Hospital Association benchmark reports** — many state hospital associations (e.g., THA for Texas, CHA for California) publish free benchmark reports.

### Federal Regulatory, Legal, and Enforcement Data

- **PACER court filings** — federal court dockets, including every bankruptcy case. Fully public but costs pennies per page (waived below $30/quarter). Critical for: Steward (Southern District of Texas docket), Envision (Southern District of Texas), American Physician Partners (Delaware), Cano Health (Delaware), Prospect Medical Holdings (Northern District of Texas), Wellpath (Southern District of Texas). **Ingestion strategy:** download full dockets for each named failure; extract key filings (first-day declarations, schedules of assets and liabilities, examiner reports, disclosure statements); structure as a bankruptcy knowledge base.
- **RECAP (Free Law Project)** — free archive of PACER documents contributed by users. **Ingestion strategy:** first check RECAP for any case before paying PACER.
- **CourtListener (Free Law Project)** — federal court opinions and dockets, free API.
- **FTC filings and consent orders** — all public. The Welsh Carson/USAP consent order is the key template. **Ingestion strategy:** scrape FTC press releases + consent decrees; tag healthcare; cross-reference with HSR filings.
- **HSR (Hart-Scott-Rodino) Early Termination Notices** — historically published daily; publication suspended in 2021 when the Biden FTC ended early termination for most filings. Historical archive is useful for pre-2021 deal corpus seeding.
- **DOJ press releases and qui tam database** — DOJ publishes False Claims Act settlements and qui tam (whistleblower) case unsealings. **Ingestion strategy:** scrape DOJ healthcare fraud page monthly; structure by defendant, dollar amount, allegation type.
- **GAO reports** — free, scrapeable.
- **Congressional hearings and committee reports** — public via Congress.gov.
- **Federal Register and Regulations.gov** — public comments on every rule.

### Labor, Demographic, and Geographic Data

- **BLS QCEW (Quarterly Census of Employment and Wages)** — every employer's employment and wages by county × industry (NAICS). **Unique value:** regional wage inflation forecasting by role, exactly the input needed for Gap 2 labor modeling.
- **BLS OEWS (Occupational Employment and Wage Statistics)** — wage distributions by occupation and metro area.
- **BLS Hospital Employment Situation** — monthly.
- **NLRB election data** — every union-representation election, every unfair-labor-practice charge. Public via NLRB.gov and available in bulk. **Ingestion strategy:** annual historical load; monthly incremental; build union-risk score per facility.
- **US Census Bureau** — American Community Survey, Business Dynamics Statistics, County Business Patterns, Nonemployer Statistics. All free.
- **HRSA Area Health Resources File** — annual county-level health workforce, facility, and demographic data.
- **HRSA Shortage Designation Files** — HPSA (Health Professional Shortage Areas), MUA (Medically Underserved Areas), MUP (Medically Underserved Populations). Free, quarterly.
- **FEMA facility data** — for disaster-risk overlays.

### Real Estate Data

- **REIT SEC 10-K filings** for every healthcare REIT — MPT (Medical Properties Trust), Global Medical REIT, Omega Healthcare Investors, Healthpeak Properties, Community Healthcare Trust, Sabra Health Care REIT, CareTrust REIT, LTC Properties, National Health Investors, Welltower, Ventas. Every lease schedule and tenant list is disclosed in 10-K exhibits. **Ingestion strategy:** annual 10-K download + extract tenant-property-rent matrix. **This substitutes substantially for Green Street/CBRE paid data for the specific use case of identifying which targets have which REIT landlords and what their rent escalators are.**
- **SEC 8-K sale-leaseback disclosures** — every public REIT-driven sale-leaseback is 8-K-disclosed.
- **County assessor records** — varies wildly by county; many are free online.
- **USPS change-of-address data** — proxy for facility closure/relocation; limited public access.

### Clinical and Claims Data for Testing

- **MIMIC-IV / MIMIC-III** — critical-care dataset from Beth Israel Deaconess, via PhysioNet. Requires credentialing but free. 400K+ patients, full clinical + billing data. **Unique value:** ML model training and validation on real hospital data.
- **Synthea (MITRE)** — open-source synthetic FHIR/HL7/claims generator. Already generates multi-year synthetic patient populations with realistic claim patterns. **Ingestion strategy:** primary test fixture generator for the platform. Extend current messy-data fixtures with Synthea-generated large-scale synthetic populations.
- **CMS Synthetic Public Use Files (SynPUF)** — free 2008-2010 Medicare claims samples. Somewhat dated but structurally realistic.
- **CMS Medicare Claims Public Use Files** — aggregated (not record-level) claims data, annual.
- **i2b2 clinical samples** — Partners Healthcare's research platform has public sample datasets.
- **OHDSI/OMOP Common Data Model samples** — multiple public sample datasets in OMOP CDM format.
- **NIS (National Inpatient Sample) — HCUP** — 7M+ annual discharges from 1,000+ hospitals, 20% stratified sample. **Caveat:** record-level is paid; aggregates via HCUPnet are free.
- **NEDS (Nationwide Emergency Department Sample) — HCUP** — similar.
- **NRD (Nationwide Readmissions Database), KID (Kids' Inpatient Database), NASS (Nationwide Ambulatory Surgery Sample)** — HCUP family.

### Cybersecurity Data

- **HHS OCR Breach Portal** — every healthcare breach affecting 500+ individuals since 2009. Fully public, downloadable CSV. **Ingestion strategy:** nightly refresh; structure by covered entity, business associate, breach type, individuals affected, date; build per-provider breach history and per-BA cascade-risk score.
- **CISA Known Exploited Vulnerabilities (KEV)** — public list of CVEs being actively exploited in the wild.
- **NIST National Vulnerability Database (NVD)** — every CVE ever published with CVSS scoring.
- **Healthcare Cybersecurity Coordination Center (HC3)** — HHS's healthcare-specific threat intel publisher. Public advisories. **Ingestion strategy:** monthly scrape; tag healthcare-relevant threats.
- **MITRE ATT&CK Framework** — open source, published.
- **Health-ISAC (Information Sharing and Analysis Center)** — some public advisories.
- **CISA Healthcare and Public Health Sector resources** — public.

### Deals Corpus Expansion (Public-Only Sources)

- **SEC EDGAR (already ingested)** — 8-Ks, 10-Ks, 10-Qs, proxies for every public healthcare company and SPAC. **Expansion:** add full-text search across all healthcare filings; named-entity extraction for every acquisition disclosed.
- **PESP (Private Equity Stakeholder Project) tracker** — public healthcare PE deal tracker, fully accessible.
- **Becker's Hospital Review M&A articles** — scrapeable daily M&A announcements. **Ingestion strategy:** daily RSS/scrape; NER extraction; build deals corpus seed.
- **Fierce Healthcare M&A coverage** — similar, scrapeable.
- **Healthcare Finance News** — similar.
- **Modern Healthcare** — some free articles; paid paywall for others. Scrape free articles only.
- **STAT News** — similar.
- **State CON (Certificate of Need) filings** — many states require CON filings for facility construction/expansion, fully public, often document M&A.
- **State AG M&A consent filings** — some states (Washington, Oregon, California) require state AG notice/consent for healthcare mergers; filings are public.
- **PitchBook is paid, no substitute exists at their coverage depth** — but for healthcare specifically, combining SEC EDGAR + PESP + Becker's + state filings covers 80%+ of public-disclosure deals.

### Open-Source Deal Economics References

- **Preqin Healthcare PE free reports** — Preqin releases free summary statistics periodically.
- **Bain & Company Global Healthcare PE Report** — free annual PDF report with deal-count and sector stats. Already cited in prior research.
- **McKinsey, BCG, Deloitte, PwC healthcare M&A reports** — free annual PDFs.
- **L.E.K. Consulting healthcare PE insights** — free.

### Other High-Value Public Data

- **FDA Adverse Event Reporting System (FAERS)** — drug adverse events. Free.
- **FDA Device MAUDE** — device adverse events.
- **NIH ClinicalTrials.gov** — every registered clinical trial.
- **PubMed / PMC** — the entire biomedical literature corpus. Free API. **Ingestion strategy:** targeted search per query.

---

## Part 3: The Open-Source Software Stack

This section catalogs every open-source software component worth integrating, organized by function.

### Healthcare Data Modeling

**Tuva Health open-source (Apache 2.0).** The open-source dbt-based healthcare data transformation stack. Five components: Connectors (source→core mappings), Core (EDI/FHIR/claims → canonical), Marts (analytical outputs), Data Quality (validation), Dashboards. **Strategic call:** SeekingChartis should adopt Tuva's input-normalization layer as a supporting substrate while keeping the Canonical Claims Dataset architecture. Tuva provides a larger, community-maintained normalization surface; CCD remains the platform's invariant contract. License: Apache 2.0 (permissive). **Integration strategy:** use Tuva via dbt project dependency; export CCD-compatible format from Tuva-transformed data.

**OHDSI OMOP Common Data Model.** Global standard for observational health data. Python (PyOMOP) and R (OHDSI HADES suite) tooling. ACHILLES for data characterization, ATLAS for cohort definition. **Strategic call:** support OMOP as an output format so the platform is interoperable with the broader health-services-research community. License: Apache 2.0.

**FHIR tooling:** fhir.resources (Python, Apache 2.0), fhirclient (SMART, Apache 2.0), HAPI FHIR server for Java if needed.

**HL7 v2 parsing:** python-hl7, hl7apy.

**X12 EDI:** the platform already has a working X12 parser. Alternatives to watch: pyx12 (unmaintained), badx12, Stedi's open components.

**Coding systems:** icd10-cm (ICD-10-CM lookup), medcodes (multi-system lookup), pyhcup (HCUP utilities), SNOMED CT via UMLS (free for US use but requires UMLS license).

### Quality and Benchmarking Software

- **AHRQ Quality Indicators (QI) Software** — free, SAS/Windows traditionally; recent Python/SQL ports. PQI (14 indicators), IQI (33 indicators), PSI (30 indicators), PDI (22 indicators), ED indicators. Integration: runtime dependency for every target's quality profile.
- **eCQI Resource Center specifications** — electronic Clinical Quality Measures published by CMS/ONC. Open.
- **NQF endorsed measures** — specifications are public.
- **HEDIS specifications** — paid via NCQA, but many individual measure specs are in academic literature.

### Machine Learning for Healthcare

- **Gradient Boosting:** LightGBM (MIT), XGBoost (Apache 2.0), CatBoost (Apache 2.0). Deploy alongside ridge regression for tabular prediction with nonlinear interactions. Strong interpretability via SHAP.
- **Probabilistic / Bayesian:** NGBoost (probabilistic gradient boosting, MIT), PyMC (Apache 2.0 Bayesian), NumPyro / Pyro (Apache 2.0 probabilistic programming), Stan via pystan (BSD).
- **Conformal Prediction:** MAPIE (Apache 2.0) — the platform already uses conformal conceptually; MAPIE gives mature implementations of Split CP, Jackknife+, CV+, and adaptive CP. Strongly recommended.
- **Time series forecasting:** Facebook Prophet (MIT), Nixtla statsforecast + mlforecast (Apache 2.0), neuralforecast for transformer-based (NHITS, PatchTST, TimeGPT).
- **Survival analysis:** lifelines (MIT), pycox, scikit-survival. Use for: physician-retention modeling, contract-renewal risk, facility-closure-hazard modeling.
- **Causal inference:** DoWhy (Microsoft, MIT), EconML (Microsoft, MIT), CausalML (Uber, Apache 2.0). Use for: synergy-realization attribution, intervention-impact estimation, counterfactual scenarios.
- **Anomaly detection:** PyOD (BSD) — 40+ anomaly detection algorithms. Use for: ingestion-error detection, seller-data window-dressing detection, unusual claim-pattern flagging.
- **AutoML baseline:** PyCaret (MIT), H2O AutoML, AutoGluon.
- **Explainability:** SHAP (MIT), LIME (BSD), Captum (PyTorch), InterpretML (Microsoft, MIT).
- **Drift detection:** evidently (Apache 2.0), deepchecks (AGPL; may constrain usage), alibi-detect (Apache 2.0). Use for: ongoing data-quality monitoring.

### NLP for Regulatory and Clinical Text

- **spaCy (MIT) + scispaCy (Apache 2.0, AllenAI)** — the workhorse for medical NLP. scispaCy adds biomedical NER models and UMLS linking.
- **MedCAT (Elastic License 2.0 — caveat: not OSI-approved, check usage compatibility)** — medical concept annotation, UMLS-based.
- **ClinicalBERT (MIT), BioBERT (Apache 2.0), PubMedBERT** — pretrained biomedical encoders available on Hugging Face.
- **Medical LLMs:** Meditron-7B / 70B (LLaMA-based, research-only license), BioMistral (Apache 2.0), Med42 (research-only). **Caveat:** many medical LLMs have research-only licenses incompatible with commercial use. For commercial deployment, stick with general-purpose LLMs (Mistral, Llama 3+) and specialize via RAG over the healthcare knowledge corpus.
- **cTAKES (Apache UIMA)** — Apache clinical NLP toolkit.
- **MetaMap / MetaMapLite** — UMLS-based concept extraction (free for research and development; commercial requires UMLS license compliance).
- **Regulatory text extraction:** spaCy + custom NER trained on CFR and CMS manual corpus.

### Document Extraction for Contracts, Charts, Financials

- **Unstructured.io open-source tier (Apache 2.0)** — handles PDFs, Word, Excel, emails, etc. Strong healthcare document support.
- **Docling (IBM, MIT)** — 2024 release, very strong PDF layout understanding, tables, figures, formulas. Handles financial statements, lease schedules, payer contracts well.
- **Marker (GPL-3.0 — caveat: viral license, check compatibility)** — excellent PDF-to-markdown with math and tables.
- **Camelot (MIT) / Tabula (MIT)** — table extraction from PDFs.
- **PyMuPDF (AGPL — caveat)** — text extraction and layout.
- **LayoutLM (Microsoft), Donut (NAVER)** — document-AI models for semi-structured extraction.
- **Document AI for forms:** OCR via Tesseract (Apache 2.0) or PaddleOCR (Apache 2.0) as pure OSS alternatives to paid services.
- **HOCR + layout reconstruction:** for legacy PDF contracts.

### Workbench UI Framework Stack

- **Plotly (MIT) and Bokeh (BSD)** — rich interactive charts. Already strong choices for the Bloomberg-style workbench.
- **Altair (BSD)** — declarative Vega-Lite-based, excellent for analysts.
- **Streamlit (Apache 2.0) vs. Panel (BSD) vs. Dash (MIT) vs. Reflex (Apache 2.0)** — for rapid analyst-facing apps. Dash is best for complex multi-tab dashboards like the existing workbench. Panel is best for Jupyter-friendly workflows. Streamlit is fastest for MVP demos. Reflex is worth watching for full-Python React-style apps.
- **Perspective (JP Morgan, Apache 2.0)** — high-performance in-browser analytical grid. Strong fit for diligence workbench given tabular nature of claim data.
- **Apache Superset (Apache 2.0)** — full BI platform. Useful for analyst ad-hoc query surface alongside the structured workbench.
- **Grafana (AGPL — caveat)** — for operational dashboards.
- **Observable Plot (ISC) / D3 (BSD)** — for bespoke visualizations.
- **Tabulator (MIT)** — excellent data-grid JS library.
- **Y.js / Yjs (MIT)** — CRDT-based collaborative editing. Needed for multi-user partner-review workflow.
- **React / Preact / Svelte / Solid** — frontend framework choices, all permissively licensed. Given the platform's stdlib philosophy, server-rendered HTML + htmx + Alpine.js is a strong low-footprint alternative to React.
- **htmx (BSD) + Alpine.js (MIT)** — server-rendered interactivity with minimal JS. Fits the platform's stdlib philosophy better than SPA frameworks.
- **Accessibility:** axe-core (Mozilla Public) for WCAG compliance testing.

### Data Engineering Infrastructure

- **DuckDB (MIT)** — embedded analytical SQL engine. Highly recommended given the platform's stdlib philosophy: zero-dependency, file-based, handles billions of rows, direct parquet/CSV reading, MotherDuck for cloud if needed. **This is the natural analytical backend.**
- **Polars (MIT)** — Rust-based dataframe library, 10-100x faster than pandas for analytical workloads. Drop-in complement where pandas is slow.
- **dbt (Apache 2.0)** — SQL-native transformation framework. Essential for Tuva integration and for maintaining a versioned, tested analytical layer.
- **Dagster (Apache 2.0) vs. Prefect (Apache 2.0) vs. Airflow (Apache 2.0)** — for orchestration of data refreshes. Dagster is best for asset-based DAGs with typed inputs/outputs.
- **Apache Iceberg / Delta Lake (Linux Foundation / Apache 2.0)** — versioned analytical data lake formats.
- **MinIO (GNU AGPL v3 — caveat)** — S3-compatible open storage. **Caveat:** AGPL v3 restricts certain commercial use.
- **SQLite (public domain)** — already in use; perfect for the platform.
- **Apache Parquet (Apache 2.0)** — analytical columnar format.

### Graph and Network Analysis

- **NetworkX (BSD)** — core graph library.
- **graph-tool (GPL — caveat)** — faster but GPL-restricted.
- **igraph (GPL — caveat)**.
- **Kuzu (MIT)** — embedded graph database, perfect fit for referral networks, ownership graphs, deal-comparable graphs.
- **PyG (PyTorch Geometric) / DGL** — graph neural networks.

### Fair-Lending / Anti-Discrimination

- **Aequitas** (University of Chicago Center for Data Science and Public Policy, MIT).
- **Fairlearn** (Microsoft, MIT).
- **AIF360** (IBM, Apache 2.0).

Use for: ensuring ML models used in diligence don't encode discriminatory biases that could create reputational or regulatory risk.

### Compliance and Security Tooling

- **Comp AI** — open-source SOC 2 + HIPAA compliance automation (FOSS).
- **Falco (Apache 2.0)** — runtime security.
- **Trivy (Apache 2.0)** — container and dependency vulnerability scanning.
- **OSV-Scanner (Apache 2.0)** — vulnerability scanning.
- **SemGrep (LGPL)** — static analysis.
- **Vanta / Drata / Secureframe** are all paid; **Comp AI** is the genuine FOSS alternative.
- **Keycloak (Apache 2.0)** — open-source identity and access management, supports OAuth2/OIDC/SAML. Natural fit for the Azure AD alternative path if needed.

### Testing, Quality, and CI

- **pytest (MIT), hypothesis (MPL — caveat)** — property-based testing.
- **Great Expectations (Apache 2.0)** — data-quality validation.
- **Pandera (MIT)** — dataframe schema validation.
- **Faker (MIT)** — synthetic data generation.

---

## Part 4: The Moat Architecture — Why This Becomes Unbeatable

Public data + open-source software is, by definition, not exclusive. The moat is not access; it is the compound of curation, interpretation, speed, and reputation. Seven specific moat layers, in order of defensibility:

### Moat Layer 1: The Codified Knowledge Graph

No vendor or consultancy has turned the HFMA MAP Keys, AHIMA clinical documentation standards, CMS Medicare Claims Processing Manual, NCCI edits, OIG Work Plans, and ICD-10 Official Guidelines into a single versioned, queryable, machine-readable knowledge graph. The platform that does becomes the reference implementation. **Defensibility:** requires 12–18 months of full-time domain-expert-plus-engineer curation. Competitors must either license from us (revenue), replicate (slow), or ignore (lose). The knowledge graph itself can be partially open-sourced to build community (feeds into Moat Layer 7), but the version that's fully integrated into diligence workflows stays proprietary.

**How to build it:** structured YAML/JSON knowledge files, one per domain, under version control. Each entry carries source citations, effective dates, supersession history, and machine-readable rules. Example entries: "NCCI Edit 99213 + 99214 same day same provider → flag"; "HFMA MAP Keys: Clean Claim Rate = (claims processed without edit) / (total claims submitted)"; "OIG 2025 Work Plan: hospital outpatient E/M level 5 utilization is being audited in states X, Y, Z"; "Stark 2021 revision: comp-per-wRVU at >75th percentile requires supplemental commercially-reasonable analysis".

### Moat Layer 2: The Proprietary Benchmark Library

Because paid vendors (MGMA, Sullivan Cotter, Definitive) charge for their benchmarks, nobody has published a comprehensive public-data-derived benchmark library across specialty × payer × region × facility-type × year. The platform builds this by:

1. Ingesting 10+ years of HCRIS cost reports at worksheet granularity
2. Computing per-facility KPI distributions by specialty, geography, payer mix, and year
3. Applying the AHRQ Quality Indicator software to every hospital's discharge mix
4. Ingesting 10+ years of IRS Form 990 Schedule H (hospital community benefit) and Schedule J (compensation) data
5. Using Medicare Provider Utilization Data to compute per-physician CPT-level production benchmarks
6. Cross-referencing Open Payments for conflict-of-interest overlays
7. Running Medicare Cost Report data through the standard Medicare reimbursement formulas to compute expected-vs-realized-payment curves

**Defensibility:** building a 2,500+ benchmark-curve library across every specialty × payer × region × year slice takes 12 months of focused work. Replicating it takes a competitor the same 12 months. The platform publishes a small sample (top-line distributions for the most common specialties) to establish credibility; the deep benchmark library (CPT-level, payer-level, region-level at the fine grain needed for QoR analyses) stays inside the product.

### Moat Layer 3: The Named-Failure Library

Every healthcare PE bankruptcy since 2015 should be decomposed into its root causes, pattern-matched against live targets. This is the "Wikipedia of RCM diligence failures" — a curated, version-controlled library of every failure pattern with: (a) decomposition of what went wrong; (b) which data signals, if looked at, would have flagged it in advance; (c) specific thresholds and test patterns; (d) the named case study and citation. Builds on the Bankruptcy-Survivor Scan already designed.

**Examples of patterns to codify:**

- **Steward pattern:** hospital + REIT landlord + long lease + low EBITDAR coverage + safety-net geography
- **Envision pattern:** hospital-based physician + >40% OON revenue + high leverage + NSA exposure
- **American Physician Partners pattern:** locum-heavy + NSA exposure + multi-state contract portfolio + no EMR consolidation
- **Cano Health pattern:** MA-risk-bearing primary care + CAC-heavy growth + V28 unprepared + founder-equity overhang
- **Prospect Medical pattern:** leveraged sale-leaseback structure per MPT "Project Prince" documents
- **Wellpath pattern:** correctional healthcare + concentrated payer + regulatory-complaint cluster
- **Envision-USAP-TeamHealth pattern:** hospital-based physician rollup + PE-heavy + antitrust-exposed
- **Cano-CareMax-Babylon pattern:** MA-risk + CAC-dependent + unproven care-management
- **Adeptus-APP-TeamHealth variant:** ED-staffing consolidation vulnerable to hospital payer-mix shifts

Each pattern becomes a structured check against live deals. **Defensibility:** this library is genuinely hard to replicate. It requires reading bankruptcy filings, analyzing financial statements at time of LBO, mapping deal structure to failure mechanism. A single analyst can add maybe 1-2 patterns per month. The library compounds over time.

### Moat Layer 4: The Backtesting Harness

Every analytical claim the platform makes must be backtestable against a held-out corpus of historical deals. Specifically: "if we had run this platform on [historical bankruptcy or success] at time of [key decision point], would we have flagged the right signal?" Build a test harness that:

1. Replays every deal in the public-deals corpus through the platform as of the deal-announcement date
2. Computes the platform's verdict (GREEN/YELLOW/RED) with all contributing signals
3. Compares to actual outcome (closed at IPO, successful exit, distressed sale, bankruptcy)
4. Reports platform sensitivity (did we flag actual failures?), specificity (did we spare actual successes?), and calibration

**Target accuracy:** 85%+ sensitivity on bankruptcies, 80%+ specificity on successful exits. **Publish the backtesting results openly** — this becomes the platform's most credible marketing artifact. "Would have flagged Steward in 2016" is vastly more compelling than any feature list.

### Moat Layer 5: The Adversarial Diligence Engine

Every diligence artifact the platform produces has an automatically-generated counterpart: the "bear case" memo. Given a management thesis, the adversarial engine:

1. Identifies every assumption in the management thesis
2. Stress-tests each assumption against the named-failure library
3. Runs the v2 bridge and Monte Carlo under adverse scenarios (worst quartile of each input)
4. Produces a structured "red team" memo that argues against the deal
5. Quantifies the probability-weighted outcome if the bear case is right

This is the opposite of the typical diligence artifact, which tends to confirm the investment thesis. An adversarial engine that automatically generates the counter-argument forces the analyst to engage both sides. **Defensibility:** requires deep integration with the platform's knowledge graph, benchmark library, and named-failure library — not replicable without all three.

### Moat Layer 6: The Velocity Compound

Every session the team runs produces improvements that compound:

- Every new target diligenced → new data point in the benchmark library
- Every new regulation ingested → expanded knowledge graph
- Every new bankruptcy decomposed → new entry in the named-failure library
- Every new failure mode discovered → new adversarial-engine test
- Every new analytical module → leverage against all future deals

Competitors starting today must ingest every data source, build every module, curate every knowledge entry. The time compounds against them. **Defensibility:** the platform's velocity advantage is 12-24 months on day one, growing to 3-5 yea

---

> **[TRUNCATED HERE — document was cut at the 50,000-character input limit mid-sentence in Moat Layer 6. Still to come (per the Executive Brief): Moat Layer 7, the 24–36 month three-phase roadmap, and whatever Parts 5+ cover (presumably operating model, partnership / open-source release strategy, 20–30 follow-on coding prompts). Please paste the remainder as a follow-up message and this document will be completed in place.]**
