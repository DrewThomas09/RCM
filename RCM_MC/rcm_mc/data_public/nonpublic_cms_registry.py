"""Registry of non-public CMS data programs, CMS FHIR APIs, and OSS to embed.

The reference table behind ``/tools/nonpublic-cms``. It answers the question the
existing ``public_api_catalog`` (free public datasets) and ``open_data_registry``
(open-source datasets/tooling) do not: **what lives one rung past the free public
data** — the credentialed CMS microdata programs, the beneficiary/claims FHIR
APIs, and the open-source projects whose *algorithms* we can reimplement natively
to move up that rung without taking on their runtime.

Why this exists as its own registry:
  * The product ships on *public aggregate* data with a load-bearing invariant —
    stdlib + numpy + pandas only, no external services, nothing leaves the laptop
    (see ``CLAUDE.md``). Beneficiary-level CMS claims (LDS / RIF / CCLF) and the
    FHIR bulk-export APIs (BCDA / DPC / AB2D) sit *outside* that posture: they need
    a DUA, a credential, or outbound OAuth. They are not render-path data.
  * But they are the natural *upgrade path* for confirmatory diligence, and the
    OSS row is where the durable value is: hccpy / hcuppy / drgpy are pure-Python,
    Apache-2.0, ship their reference data, and encode exactly the CMS/AHRQ
    algorithms this workbench would otherwise hand-build. Same call the codebase
    already made for Tuva and Myelin (adopt the *idea*, not the *dependency*).

This module is **metadata only**. It does NOT fetch anything at import or render
time. Live clients (where an entry graduates to ``reachable``) live in
``public_api_clients.py`` / ``cms_api_client.py`` / ``nppes_api_client.py``.

Access model (how you get in):
  public        – free download / open API, no registration
  api-key       – free API key raises limits; data itself is open
  oauth         – beneficiary- or org-authorized OAuth 2.0
  bulk-fhir     – SMART Backend Services (client-credentials JWT) + FHIR $export
  credentialed  – signed DUA (and often IRB) via ResDAC / EPPE
  entitlement   – access flows from a CMS program agreement (ACO / PDP), not a DUA
  oss           – open-source code/data you self-host or vendor

Status (honest about what runs in-repo today):
  reachable     – a live API we can and do call from this session's environment
                  (verified: NPPES, CMS Coverage, ICD-10 code service).
  registered    – cataloged + linked; no in-repo client/loader yet (the default).
  reference     – study-only: heavy runtime (JVM / warehouse / server). We reuse
                  the schema/algorithm and reimplement natively, never depend on it.

Disclosure-ladder note: CMS releases beneficiary data along three rungs of
identifiability — public-use (PUF / DE-SynPUF) → Limited Data Set (LDS, DUA, no
IRB) → Research Identifiable File (RIF, DUA + usually IRB). Each ``rung`` field
records where an entry sits. LDS is still an *identifiable* file class under CMS
policy (it keeps dates / ZIP) even though HIPAA direct identifiers are stripped.

Every fact here was sourced from official CMS / HL7 / GitHub documentation in
2026-07. Values that are date- or fee-sensitive carry a ``verify`` note rather
than a guessed number — do not treat those as authoritative without a live check.
"""
from __future__ import annotations

from typing import Dict, List

# Category id -> display label, in render order.
CATEGORIES: List[tuple] = [
    ("cms_credentialed", "Credentialed CMS microdata (the disclosure ladder)"),
    ("cms_fhir_api", "CMS beneficiary & claims FHIR APIs"),
    ("cms_mandate", "Interoperability mandates that create payer APIs"),
    ("oss_embed", "Open-source algorithms to reimplement natively"),
    ("live_api", "Live public APIs (reachable from this environment)"),
]

# Access-model -> display label (for UI badges).
ACCESS_LABELS: Dict[str, str] = {
    "public": "Public",
    "api-key": "Free key",
    "oauth": "OAuth (consent)",
    "bulk-fhir": "Bulk FHIR",
    "credentialed": "DUA / credentialed",
    "entitlement": "Program entitlement",
    "oss": "Open source",
}

STATUS_LABELS: Dict[str, str] = {
    "reachable": "Reachable now",
    "registered": "Registered",
    "reference": "Reference-only",
}

# Each source is an all-string dict. Required keys (validated in tests):
#   id, name, category, access, url, blurb, relevance, status, integration
# Optional, rendered on the detail page when present:
#   rung, granularity, parts, latency, cost, api, license, notes, verify
SOURCES: List[Dict[str, str]] = [
    # ── Credentialed CMS microdata — the disclosure ladder ───────────────
    {
        "id": "resdac", "name": "ResDAC (Research Data Assistance Center)",
        "category": "cms_credentialed", "access": "credentialed",
        "rung": "Gateway (free advisory)",
        "url": "https://resdac.org/",
        "blurb": "CMS-funded (University of Minnesota) front door for Limited Data "
                 "Set and Research Identifiable File requests: scoping help, data "
                 "dictionaries, variable docs, cohort/cost tools. Not a dataset.",
        "relevance": "The mandatory path to any beneficiary-level Medicare claims. "
                     "Its ~3-5 month request cycle is itself a diligence-planning "
                     "constraint — you cannot get RIF data inside a deal timeline.",
        "granularity": "n/a (advisory)", "cost": "Free",
        "latency": "RIF requests it shepherds run ~3-5 months",
        "api": "No — advisory portal; requests route into CMS EPPE.",
        "status": "registered", "integration": "link",
        "notes": "CMS is mid-transition (new DMP self-attestation forms, EPPE); "
                 "larger structural changes flagged for 2026+.",
    },
    {
        "id": "ccw_vrdc", "name": "CCW / VRDC (Chronic Conditions Warehouse)",
        "category": "cms_credentialed", "access": "credentialed",
        "rung": "RIF (rung 3) — enclave",
        "url": "https://www2.ccwdata.org/",
        "blurb": "The Chronic Conditions Data Warehouse and its cloud analytics "
                 "enclave (Virtual Research Data Center). Analysts work inside a "
                 "secure remote desktop; output is reviewed before export.",
        "relevance": "Gold standard for longitudinal national claims — payer mix, "
                     "condition prevalence, site-of-service shift, referral/leakage "
                     "modelling. A big-check, long-horizon resource, not quick-turn.",
        "granularity": "Beneficiary-level, in-enclave",
        "parts": "A / B / D + Medicaid (T-MSIS)",
        "cost": "High — annual project fee + per-user seats + infra "
                "(storage sold in ~500 GB blocks)",
        "latency": "Same 3-5 month DUA cycle to gain access",
        "api": "No external API — analysis runs inside the enclave.",
        "status": "registered", "integration": "link",
        "verify": "Exact 2025-26 seat/project/storage dollar amounts unconfirmed; "
                  "structure verified, line items not. See ResDAC fee list.",
    },
    {
        "id": "cms_lds", "name": "CMS Limited Data Set (LDS) / Standard Analytic Files",
        "category": "cms_credentialed", "access": "credentialed",
        "rung": "LDS (rung 2) — DUA, generally no IRB",
        "url": "https://www.cms.gov/data-research/files-for-order/limited-data-set-lds-files",
        "blurb": "Beneficiary-level claims with HIPAA direct identifiers removed: "
                 "Standard Analytic Files by claim type (Inpatient, Outpatient, "
                 "SNF, HHA, Hospice, Carrier, DME) plus enrollment/summary files.",
        "relevance": "The most practical beneficiary-level file for benchmarking "
                     "charges, utilization, and service-line patterns without full "
                     "RIF overhead. Common in RCM benchmarking + mid-tier diligence.",
        "granularity": "Beneficiary-level, de-identified (keeps dates/ZIP)",
        "parts": "A / B (Part D ordered separately)",
        "cost": "Cost-recovery fee (priced via LDS Worksheet)",
        "latency": "Weeks-to-months (DUA -> fee -> delivery)",
        "api": "No — file delivery after DUA.",
        "status": "registered", "integration": "link",
        "notes": "As of Apr 2025 beneficiary sex dropped from SAFs; from 7/2025 CMS "
                 "is retiring older quarterly SAFs / MBSF beyond a 2-yr window.",
    },
    {
        "id": "cms_rif", "name": "CMS Research Identifiable Files (RIF)",
        "category": "cms_credentialed", "access": "credentialed",
        "rung": "RIF (rung 3) — DUA + usually IRB",
        "url": "https://resdac.org/cms-research-identifiable-request-process-timeline",
        "blurb": "Individual-level, fully identifiable Medicare/Medicaid claims, "
                 "linkable across time and sources for true longitudinal studies. "
                 "Delivered as files or accessed inside the VRDC.",
        "relevance": "The only route to person-level longitudinal tracking (episode "
                     "construction, readmissions, cross-provider journeys). Deepest "
                     "diligence, but rarely feasible in a deal window without a "
                     "partner holding a standing DUA.",
        "granularity": "Beneficiary-level, identifiable",
        "parts": "A / B / D + Medicaid (T-MSIS)",
        "cost": "High cost-recovery fees",
        "latency": "~3-5 months processing",
        "api": "No — file delivery or VRDC enclave.",
        "status": "registered", "integration": "link",
    },
    {
        "id": "cclf", "name": "CCLF — Claim & Claim Line Feed (SSP ACOs)",
        "category": "cms_credentialed", "access": "entitlement",
        "rung": "ACO entitlement (bene-level)",
        "url": "https://www.cms.gov/files/document/cclf-information-packet.pdf",
        "blurb": "Monthly beneficiary-level, claim-and-line file package delivered "
                 "to MSSP / ACO REACH participants for their assigned FFS "
                 "beneficiaries: 5 Part A files, 3 Part B, 1 Part D, plus demo, "
                 "MBI cross-reference, and summary files.",
        "relevance": "The actual data asset an ACO/value-based target already "
                     "receives. In diligence, how well the target exploits its CCLF "
                     "(care coordination, reconciliation, leakage) is the signal.",
        "granularity": "Beneficiary-level, claim-line",
        "parts": "A / B / D", "cost": "Free with ACO participation",
        "latency": "Monthly flat-file delivery",
        "api": "Flat file; BCDA is the FHIR-API alternative to the same data.",
        "status": "registered", "integration": "link",
    },
    {
        "id": "de_synpuf", "name": "DE-SynPUF (synthetic public-use file)",
        "category": "cms_credentialed", "access": "public",
        "rung": "Public-use (rung 1)",
        "url": "https://www.cms.gov/data-research/statistics-trends-and-reports/"
               "medicare-claims-synthetic-public-use-files/"
               "cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf",
        "blurb": "CMS 2008-2010 synthetic beneficiary-level records (5 file types: "
                 "Beneficiary Summary, Inpatient, Outpatient, Carrier, PDE) that "
                 "structurally mimic real claims. Free, no DUA. OMOP variant on AWS.",
        "relevance": "The zero-friction proxy for building and testing "
                     "claims-processing pipelines and RCM logic before committing "
                     "to the multi-month RIF path. Safe, PHI-free fixtures.",
        "granularity": "Synthetic beneficiary-level (2008-2010 vintage)",
        "parts": "A / B / D", "cost": "Free",
        "latency": "Instant download",
        "api": "No — static file (OMOP CDM variant available).",
        "status": "registered", "integration": "loader-stub",
        "notes": "Old + synthetic + pre-ICD-10: valid for pipeline tests, NOT for "
                 "real market sizing or current coding.",
    },

    # ── CMS beneficiary & claims FHIR APIs ───────────────────────────────
    {
        "id": "bluebutton", "name": "Blue Button 2.0 API",
        "category": "cms_fhir_api", "access": "oauth",
        "url": "https://bluebutton.cms.gov/api-documentation/",
        "blurb": "Beneficiary-authorized Medicare claims (Parts A/B/D) as FHIR "
                 "ExplanationOfBenefit + Patient + Coverage, for a single consenting "
                 "beneficiary at a time. v1 = STU3, v2 = R4 (CARIN Blue Button IG). "
                 "Public synthetic sandbox (~30k synthetic beneficiaries).",
        "relevance": "The consumer-consent model — powers patient-facing / care-"
                     "navigation apps. In diligence it's a product capability to "
                     "assess in consumer-health targets, not a population feed.",
        "granularity": "Single consenting beneficiary",
        "parts": "A / B / D", "cost": "Free",
        "api": "Yes — REST FHIR + OAuth 2.0. No $export.",
        "status": "registered", "integration": "api-client",
        "verify": "Current published per-app rate limit unconfirmed.",
    },
    {
        "id": "bcda", "name": "BCDA — Beneficiary Claims Data API",
        "category": "cms_fhir_api", "access": "bulk-fhir",
        "url": "https://bcda.cms.gov/",
        "blurb": "Bulk FHIR ($export) feed of an MSSP/REACH ACO's attributed "
                 "population's Medicare Parts A/B/D claims as NDJSON "
                 "(ExplanationOfBenefit, Patient, Coverage). Adjudicated weekly; "
                 "REACH ACOs also get partially-adjudicated claims daily.",
        "relevance": "The canonical population-level Medicare claims pipe for VBC "
                     "entities. An ACO target using BCDA vs manual CCLF handling "
                     "signals data maturity; data rights are a core moat item.",
        "granularity": "ACO's attributed population (bene-level bulk)",
        "parts": "A / B / D", "cost": "Free (ACO entitlement)",
        "api": "Yes — /Group/$export & /Patient/$export, SMART Backend Services.",
        "status": "registered", "integration": "api-client",
        "notes": "Same underlying data domain as CCLF, delivered by API. "
                 "Reference server: github.com/CMSgov/bcda-app (Go, public domain).",
    },
    {
        "id": "dpc", "name": "DPC — Data at the Point of Care",
        "category": "cms_fhir_api", "access": "bulk-fhir",
        "url": "https://dpc.cms.gov/",
        "blurb": "Bulk FHIR claims (Parts A/B/D) for a provider's own patient "
                 "roster via /Group/$export — flowing under HIPAA treatment purpose, "
                 "no beneficiary authorization. Original FFS Medicare only.",
        "relevance": "Roster/treatment-driven (vs BCDA's attribution) — fills "
                     "patient-history gaps at the point of care for provider groups "
                     "outside value-based contracts.",
        "granularity": "Provider's active roster (bene-level bulk)",
        "parts": "A / B / D", "cost": "Free",
        "api": "Yes — Bulk FHIR (pilot).",
        "status": "registered", "integration": "api-client",
        "verify": "Production onboarding reported PAUSED in 2025 (identity/onboarding "
                  "rework); sandbox open. Confirm status before relying on it.",
    },
    {
        "id": "ab2d", "name": "AB2D — Claims Data to Part D Sponsors",
        "category": "cms_fhir_api", "access": "bulk-fhir",
        "url": "https://ab2d.cms.gov/",
        "blurb": "Bulk FHIR Medicare Parts A & B claims for a standalone Part D "
                 "sponsor's enrollees (gives PDPs the medical-claims picture they "
                 "otherwise lack). NDJSON, /Patient/$export. Tokens expire in 30 min.",
        "relevance": "Enables medication-therapy-management and adherence analytics "
                     "for Part D plans. Narrow audience (standalone PDP), so a "
                     "constrained addressable integration.",
        "granularity": "PDP sponsor's enrollees (bene-level bulk)",
        "parts": "A / B", "cost": "Free (sponsor entitlement)",
        "api": "Yes — Bulk FHIR via Okta/IDM OAuth2.",
        "status": "registered", "integration": "api-client",
        "verify": "2025-26 active-onboarding status not re-confirmed (primary page "
                  "returned 403 to the research fetcher).",
    },
    {
        "id": "marketplace_api", "name": "CMS Marketplace API",
        "category": "cms_fhir_api", "access": "api-key",
        "url": "https://developer.cms.gov/marketplace-api/",
        "blurb": "Custom JSON REST (not FHIR) powering HealthCare.gov: QHP plan "
                 "premiums/benefits/cost-sharing, provider in-network coverage, and "
                 "drug/formulary coverage (drug -> RxCUI -> plan/tier lookup).",
        "relevance": "Lower for hospital RCM; high for insurtech, broker/enrollment, "
                     "and price-transparency targets whose surface is ACA plan or "
                     "formulary/network comparison.",
        "granularity": "Plan / provider / formulary",
        "cost": "Free (API key, rate-limited)",
        "api": "Yes — JSON REST (API key).",
        "status": "registered", "integration": "api-client",
        "notes": "Machine-readable QHP provider/formulary bulk files published "
                 "separately: github.com/CMSgov/QHP-provider-formulary-APIs.",
    },

    # ── Interoperability mandates that create payer APIs ─────────────────
    {
        "id": "cms_9115f", "name": "CMS-9115-F — Interoperability & Patient Access",
        "category": "cms_mandate", "access": "oauth",
        "url": "https://www.cms.gov/priorities/burden-reduction/overview/"
               "interoperability/policies-regulations/"
               "cms-interoperability-patient-access-final-rule-cms-9115-f",
        "blurb": "2020 final rule requiring MA, Medicaid/CHIP, and FFE QHP payers "
                 "to stand up a patient-authorized Patient Access API (adjudicated "
                 "claims + clinical) and a Provider Directory API.",
        "relevance": "Created the payer-side FHIR surface. Named IGs (US Core, CARIN "
                     "Blue Button, Da Vinci PDex / Plan-Net, US Drug Formulary) are "
                     "the schema every payer-facing target must speak.",
        "api": "Payer-hosted FHIR APIs (US Core / CARIN / PDex IGs).",
        "status": "reference", "integration": "spec",
        "verify": "Exact US Core version pinned per API in current rule text — "
                  "confirm against live regulation.",
    },
    {
        "id": "cms_0057f", "name": "CMS-0057-F — Interoperability & Prior Auth",
        "category": "cms_mandate", "access": "bulk-fhir",
        "url": "https://www.cms.gov/initiatives/burden-reduction/overview/"
               "interoperability/policies-regulations/"
               "cms-interoperability-prior-authorization-final-rule-cms-0057-f",
        "blurb": "2024 final rule. Operational PA provisions by Jan 1 2026 (72h "
                 "expedited / 7d standard decisions, public PA metrics from Mar 31 "
                 "2026); four FHIR APIs live by Jan 1 2027 — Patient Access (+PA), "
                 "Provider Access, Payer-to-Payer, and Prior Authorization (PARDD).",
        "relevance": "The single biggest 2026-27 tailwind for payer interoperability "
                     "and PA-automation. Converts prior authorization — a top RCM "
                     "denial/days-in-AR driver — into an API-addressable market with "
                     "a hard 2027 wall. Assess a target's CRD/DTR/PAS roadmap.",
        "api": "Da Vinci CRD + DTR + PAS (the PA trio); FHIR Bulk for Provider Access.",
        "status": "reference", "integration": "spec",
        "notes": "Does not cover Part D drug PA or commercial group plans.",
    },
    {
        "id": "fhir_bulk", "name": "FHIR Bulk Data ($export / Flat FHIR)",
        "category": "cms_mandate", "access": "bulk-fhir",
        "url": "https://hl7.org/fhir/uv/bulkdata/",
        "blurb": "HL7 standard behind BCDA/DPC/AB2D and CMS-0057-F Provider Access: "
                 "async $export at System/Patient/Group level -> NDJSON via signed "
                 "URLs, paired with SMART Backend Services (client-credentials JWT).",
        "relevance": "The technical lingua franca for population claims extraction. "
                     "A target with robust $export polling + NDJSON ingestion + "
                     "SMART Backend onboarding has reusable plumbing across every "
                     "CMS/payer bulk API — a genuine engineering asset.",
        "api": "Standard: $export + SMART Backend Services.",
        "status": "reference", "integration": "spec",
    },

    # ── Open-source algorithms to reimplement natively ───────────────────
    {
        "id": "hccpy", "name": "hccpy — CMS-HCC risk adjustment",
        "category": "oss_embed", "access": "oss", "license": "Apache-2.0",
        "url": "https://github.com/yubin-park/hccpy",
        "blurb": "Pure-Python CMS Hierarchical Condition Categories: ICD-10 -> CC "
                 "mapping, hierarchy-trumping logic, demographic/interaction terms, "
                 "score aggregation. Ships V22/V23/V24/V28/ESRD/RxHCC coefficient "
                 "CSVs. V28 is 100% weight for PY2026, so it's current.",
        "relevance": "Core to risk-adjusted revenue analysis, MA revenue modelling, "
                     "and RAF-integrity / coding-intensity diligence. Maps directly "
                     "onto the existing diligence/risk_adjustment module.",
        "api": "n/a (library)", "cost": "Free",
        "status": "reference", "integration": "reimplement-native",
        "notes": "No runtime risk — pure Python, data bundled. The coefficient/"
                 "hierarchy files are the exact reusable artifact.",
    },
    {
        "id": "hcuppy", "name": "hcuppy — AHRQ HCUP groupers",
        "category": "oss_embed", "access": "oss", "license": "Apache-2.0",
        "url": "https://github.com/yubin-park/hcuppy",
        "blurb": "Pure-Python port of AHRQ HCUP tools: CCS/CCSR (ICD-10 -> ~285 "
                 "clinical categories), Elixhauser comorbidity index (+ van Walraven "
                 "/ readmission weights), Chronic Condition Indicator, Utilization "
                 "Flags, Procedure Class.",
        "relevance": "Case-mix adjustment, cohort building, comorbidity burden, "
                     "service-line analysis. Elixhauser is a staple denominator "
                     "adjuster for apples-to-apples peer benchmarking.",
        "api": "n/a (library)", "cost": "Free",
        "status": "reference", "integration": "reimplement-native",
        "notes": "No runtime risk — pure Python + bundled mappings.",
    },
    {
        "id": "drgpy", "name": "drgpy — MS-DRG assignment",
        "category": "oss_embed", "access": "oss", "license": "Apache-2.0",
        "url": "https://github.com/yubin-park/drgpy",
        "blurb": "Pure-Python MS-DRG grouper: assigns DRGs from diagnosis + "
                 "procedure combinations. The lightweight alternative to CMS's "
                 "official Java grouper for inpatient reimbursement estimation.",
        "relevance": "Inpatient reimbursement estimation and DRG-shift / upcoding "
                     "analysis in diligence, without a JVM.",
        "api": "n/a (library)", "cost": "Free",
        "status": "reference", "integration": "reimplement-native",
        "verify": "Approximates the official grouper (no full MCE edits); confirm "
                  "the fiscal-year version it encodes before using for pricing.",
    },
    {
        "id": "yubin_utils", "name": "yubin-park claims utilities (parse834, ouidxpy…)",
        "category": "oss_embed", "access": "oss", "license": "Apache-2.0",
        "url": "https://github.com/yubin-park",
        "blurb": "A cluster of small pure-Python claims tools: parse834 (X12 834 "
                 "enrollment parser), ouidxpy (Johns Hopkins Overuse Index of "
                 "low-value-care ICD-10 flags), dxitemspy (diagnostic classification), "
                 "hcup_sid_formatter, anonymizer (PHI hashing).",
        "relevance": "ouidxpy's overuse flags are directly a utilization-quality "
                     "diligence lens; parse834 is a clean pattern for EDI parsing "
                     "without a heavyweight X12 dependency (cf. data/edi_parser.py).",
        "api": "n/a (libraries)", "cost": "Free",
        "status": "reference", "integration": "reimplement-native",
        "notes": "pharmpy in the same org relies on the external RxNav API at "
                 "runtime — treat as data-model reference only, not a pure library.",
    },
    {
        "id": "tuva", "name": "Tuva Project — claims data model & value sets",
        "category": "oss_embed", "access": "oss", "license": "Apache-2.0",
        "url": "https://github.com/tuva-health/tuva",
        "blurb": "dbt claims data model (eligibility / medical_claim / pharmacy_claim "
                 "marts), data-quality tests, service-category grouping, and "
                 "terminology value sets (ICD-10, HCPCS, HCC, service categories) "
                 "in seeds/value_sets/.",
        "relevance": "The reference blueprint for a claims analytics layer; the DQ "
                     "framework is a diligence checklist in code. Already partly "
                     "adopted (see docs/TUVA_MYELIN_INTEGRATION.md) — mine the seeds, "
                     "not the dbt runtime.",
        "api": "n/a (dbt package)", "cost": "Free",
        "status": "reference", "integration": "reimplement-native",
        "notes": "Needs dbt + a warehouse to run; the seed CSVs are portable to "
                 "pandas.",
    },
    {
        "id": "omop_cdm", "name": "OHDSI OMOP CDM + Athena vocabularies",
        "category": "oss_embed", "access": "oss", "license": "Apache-2.0",
        "url": "https://github.com/OHDSI/CommonDataModel",
        "blurb": "The OMOP Common Data Model DDL (person, condition_occurrence, "
                 "drug_exposure, visit_occurrence, cost, payer_plan_period) plus the "
                 "Standardized Vocabularies (SNOMED/RxNorm/ICD/CPT crosswalks) from "
                 "Athena. The cost & payer_plan_period tables are claims/RCM-relevant.",
        "relevance": "A rigorous, documented model for normalizing heterogeneous "
                     "claims/clinical data across acquisition targets; the "
                     "concept-crosswalk pattern is reusable for terminology mapping.",
        "api": "n/a (schema + vocab)", "cost": "Free (Athena needs free registration)",
        "status": "reference", "integration": "reimplement-native",
        "notes": "CDM is just DDL (portable). ATLAS needs a WebAPI server — "
                 "reference only.",
    },
    {
        "id": "myelin", "name": "Myelin (LibrePPS) — CMS grouper/pricer bridge",
        "category": "oss_embed", "access": "oss", "license": "MIT",
        "url": "https://github.com/Bedrock-Billing/Myelin",
        "blurb": "Python (JPype) bridge to the official CMS Java groupers (MS-DRG, "
                 "HHA, IRF), editors (MCE, IOCE), and pricers (IPPS, OPPS, IPF, IRF, "
                 "LTCH, SNF, Hospice, ESRD, FQHC). Auto-downloads CMS JARs.",
        "relevance": "The editor -> grouper -> pricer orchestration and field-level "
                     "input schemas are the reusable artifact; reimplement the "
                     "deterministic parts (as drgpy does) rather than depend on it.",
        "api": "n/a (JVM bridge)", "cost": "Free",
        "status": "reference", "integration": "swap-adapter",
        "verify": "Repo is Bedrock-Billing/Myelin (MIT), not 'LibrePPS' — LibrePPS "
                  "is the org alias. High runtime risk: JVM 17+, JPype, JAR download.",
    },
    {
        "id": "bfd", "name": "CMSgov BFD — claims-to-FHIR mapping",
        "category": "oss_embed", "access": "oss", "license": "CC0-1.0",
        "url": "https://github.com/CMSgov/beneficiary-fhir-data",
        "blurb": "The Beneficiary FHIR Data server (Java, public domain) behind Blue "
                 "Button / BCDA / DPC. Serves Medicare enrollment + claims as FHIR "
                 "ExplanationOfBenefit.",
        "relevance": "The claims-field -> FHIR EOB mapping is the reusable artifact: "
                     "it defines a clean canonical claim schema to mirror in pandas "
                     "even without running the server.",
        "api": "n/a (server)", "cost": "Free",
        "status": "reference", "integration": "spec",
        "notes": "Full server app — reference-only; reuse the FHIR resource shapes.",
    },
    {
        "id": "synthea", "name": "Synthea — synthetic patients & claims",
        "category": "oss_embed", "access": "oss", "license": "Apache-2.0",
        "url": "https://github.com/synthetichealth/synthea",
        "blurb": "Generates synthetic-but-realistic patient records and claims "
                 "(FHIR/C-CDA/CSV) via disease-progression state machines. JVM to "
                 "run, but pre-generated datasets (incl. OMOP on AWS) let you consume "
                 "outputs with zero Java.",
        "relevance": "Test fixtures for the data-room / packet flows without PHI. "
                     "Complements DE-SynPUF for pipeline testing (cross-refs the "
                     "existing open_data_registry 'synthea' entry).",
        "api": "n/a (generator)", "cost": "Free",
        "status": "reference", "integration": "loader-stub",
        "notes": "Use the outputs, skip the runtime.",
    },
    {
        "id": "cql", "name": "CQL / ELM — quality-measure logic",
        "category": "oss_embed", "access": "oss", "license": "Apache-2.0",
        "url": "https://github.com/cqframework/clinical_quality_language",
        "blurb": "The Clinical Quality Language spec + CQL->ELM translator. ELM is a "
                 "language-neutral JSON AST for clinical/quality logic; eCQMs are "
                 "value-set-driven measures expressed in it.",
        "relevance": "If we express quality measures (HEDIS-like) natively, ELM is "
                     "the portable representation to target; the JVM engine is "
                     "reference-only.",
        "api": "n/a (spec/translator)", "cost": "Free",
        "status": "reference", "integration": "spec",
        "notes": "cqframework/cql-engine is archived — cite the active "
                 "clinical_quality_language repo instead.",
    },

    # ── Live public APIs reachable from this environment (verified) ──────
    {
        "id": "nppes_api", "name": "NPPES NPI Registry API",
        "category": "live_api", "access": "public",
        "url": "https://npiregistry.cms.gov/api-page",
        "blurb": "CMS NPPES v2.1 registry: every US provider (NPI-1 individuals, "
                 "NPI-2 organizations) by name, location, specialty (taxonomy), "
                 "organization. Verified live this session (Mayo Clinic lookup "
                 "returned NPI 1881018208).",
        "relevance": "The provider universe every CDD build starts from — market "
                     "structure, roll-up mapping, physician rosters, entity "
                     "resolution. Already wired: data_public/nppes_api_client.py.",
        "granularity": "Provider-level", "cost": "Free (no key)",
        "api": "Yes — public JSON REST, 200/req, up to 1,200 paged.",
        "status": "reachable", "integration": "api-client",
    },
    {
        "id": "cms_coverage_api", "name": "CMS Coverage API (Medicare Coverage DB)",
        "category": "live_api", "access": "public",
        "url": "https://api.coverage.cms.gov/",
        "blurb": "National + local Medicare coverage documents (NCDs, LCDs, "
                 "articles, NCAs). Verified live this session (a 'dialysis' NCD "
                 "search returned NCD 130.8 / 230.7).",
        "relevance": "Part-B coverage exposure by procedure/DME/lab: which policies "
                     "govern a target's service lines, and what recent coverage "
                     "changes threaten a thesis driver (feeds regulatory_calendar).",
        "granularity": "Coverage document", "cost": "Free",
        "api": "Yes — public REST (wrapped by the CMS_Coverage MCP server).",
        "status": "reachable", "integration": "api-client",
    },
    {
        "id": "icd10_service", "name": "ICD-10-CM / PCS code service",
        "category": "live_api", "access": "public",
        "url": "https://www.cms.gov/medicare/coding-billing/icd-10-codes",
        "blurb": "ICD-10-CM (diagnosis) + ICD-10-PCS (inpatient procedure) 2026 "
                 "code sets with descriptions, HIPAA-billability validation, and "
                 "hierarchy navigation. Verified live this session ('end stage renal "
                 "disease' -> N18.6, HIPAA-valid).",
        "relevance": "The coding backbone for every claims/grouper analytic — "
                     "validates and enriches diagnosis/procedure codes feeding HCC, "
                     "DRG, and service-line logic.",
        "granularity": "Code-level", "cost": "Free",
        "api": "Yes — reachable via the ICD-10_Codes MCP server this session.",
        "status": "reachable", "integration": "api-client",
    },
]

_BY_ID = {s["id"]: s for s in SOURCES}
_CAT_LABEL = dict(CATEGORIES)


def all_sources() -> List[Dict[str, str]]:
    """Every registered source (stable order)."""
    return list(SOURCES)


def get(source_id: str) -> Dict[str, str]:
    """One source by id, or {} if unknown."""
    return dict(_BY_ID.get(source_id, {}))


def by_category() -> List[tuple]:
    """[(category_id, label, [sources...]), ...] in render order."""
    out = []
    for cid, label in CATEGORIES:
        items = [s for s in SOURCES if s["category"] == cid]
        if items:
            out.append((cid, label, items))
    return out


def status_counts() -> Dict[str, int]:
    """Counts by integration status (reachable / registered / reference)."""
    counts: Dict[str, int] = {}
    for s in SOURCES:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    return counts


def category_label(cid: str) -> str:
    return _CAT_LABEL.get(cid, cid)
