"""Registry of open-source healthcare datasets, APIs, and tooling.

A curated catalog of the open data / open infrastructure sources worth wiring
into PEdesk over time (seeded from the Out-Of-Pocket "Open Source Healthcare"
survey). This is the *backend* source of truth behind the internal
``/tools/open-data`` lab pages — it is intentionally NOT surfaced in the
front nav. Each entry is a candidate integration with its access model,
license, why it matters for healthcare-PE diligence, and the planned
integration shape.

Why a registry (not direct loaders yet): most of these need either credentialed
access (PhysioNet DUAs for MIMIC/eICU), a self-hosted server (FHIR/EHR), or
outbound network + an API key — none of which belong in a render path. The
registry lets us track, link, and stage the work; loaders graduate an entry
from ``registered`` → ``wired`` as they land in an environment that can reach
the source. Nothing here downloads at import time.

Access model:
  open         – freely downloadable, no registration
  api          – open/public HTTP API (may rate-limit)
  credentialed – requires registration / a data-use agreement
  self-host    – you run the server/model yourself
  model        – open (or open-weight) model artifact

Status:
  registered   – cataloged + linked here; no loader yet (the default)
  wired        – a loader/client exists and runs where access is available
"""
from __future__ import annotations

from typing import Dict, List

# Category id -> display label, in render order.
CATEGORIES: List[tuple] = [
    ("datasets", "Open datasets"),
    ("infra", "Data infrastructure & ontologies"),
    ("models", "Open AI models"),
    ("measurement", "Open disease measurement"),
    ("hardware", "Open hardware"),
]

# Each source: id, name, category, access, license, url, blurb, relevance,
# status, integration (the planned/landed approach).
SOURCES: List[Dict[str, str]] = [
    # ── Open datasets ────────────────────────────────────────────────────
    {
        "id": "mimic", "name": "MIMIC-IV", "category": "datasets",
        "access": "credentialed", "license": "PhysioNet Credentialed Health Data",
        "url": "https://physionet.org/content/mimiciv/",
        "blurb": "De-identified ICU records (vitals, labs, meds, procedures, "
                 "notes) from Beth Israel Deaconess; the OG open clinical dataset "
                 "with a large derived-code ecosystem.",
        "relevance": "Benchmark clinical-acuity and utilization models against a "
                     "credible real-world cohort.",
        "status": "registered", "integration": "loader-stub",
    },
    {
        "id": "aimi", "name": "Stanford AIMI Shared Datasets", "category": "datasets",
        "access": "credentialed", "license": "Stanford AIMI (research)",
        "url": "https://aimi.stanford.edu/shared-datasets",
        "blurb": "AI-ready, annotated medical-imaging repositories (e.g. "
                 "DeepLesion: 32k+ CT scans with annotated tumors).",
        "relevance": "Imaging-AI diligence references; volume/quality priors.",
        "status": "registered", "integration": "link",
    },
    {
        "id": "gnomad", "name": "gnomAD", "category": "datasets",
        "access": "open", "license": "ODbL / open",
        "url": "https://gnomad.broadinstitute.org/",
        "blurb": "700k+ exome/genome sequences for population genomics.",
        "relevance": "Genomics-platform target diligence (allele frequency priors).",
        "status": "registered", "integration": "api-client",
    },
    {
        "id": "openneuro", "name": "OpenNeuro", "category": "datasets",
        "access": "open", "license": "CC0",
        "url": "https://openneuro.org/",
        "blurb": "500+ public neuroimaging datasets (BIDS standard).",
        "relevance": "Neuro device/dx diligence references.",
        "status": "registered", "integration": "link",
    },
    {
        "id": "synthea", "name": "Synthea (synthetic patients)", "category": "datasets",
        "access": "open", "license": "Apache-2.0",
        "url": "https://github.com/synthetichealth/synthea",
        "blurb": "Open-source synthetic patient generator: realistic-but-fake "
                 "longitudinal records, HIPAA-free.",
        "relevance": "Demo seeds + pipeline tests without touching PHI; safe "
                     "fixtures for the data-room and packet flows.",
        "status": "registered", "integration": "loader-stub",
    },
    {
        "id": "open_targets", "name": "Open Targets Platform", "category": "datasets",
        "access": "api", "license": "CC0 / open",
        "url": "https://platform.opentargets.org/",
        "blurb": "Curated target-disease association data (genomics, "
                 "transcriptomics, known drugs) via a public GraphQL API.",
        "relevance": "Biopharma / target-platform diligence: pipeline and "
                     "mechanism evidence.",
        "status": "registered", "integration": "api-client",
    },
    {
        "id": "alphafold", "name": "AlphaFold Protein Structure DB", "category": "datasets",
        "access": "open", "license": "CC-BY-4.0",
        "url": "https://alphafold.ebi.ac.uk/",
        "blurb": "Predicted 3D structures for ~200M proteins (DeepMind/EMBL-EBI).",
        "relevance": "Structure-based drug-platform diligence (tangential).",
        "status": "registered", "integration": "link",
    },
    {
        "id": "cms_claims", "name": "CMS public claims & billing", "category": "datasets",
        "access": "open", "license": "US Gov public domain",
        "url": "https://data.cms.gov/",
        "blurb": "Medicare/Medicaid public-use files: provider utilization, "
                 "spending, billing patterns (the 'DOGE drop' lineage).",
        "relevance": "Core RCM diligence: payer mix, billing anomalies, "
                     "provider revenue cross-checks. (HCRIS/CMS loaders already "
                     "power much of PEdesk; this extends the catalog.)",
        "status": "wired", "integration": "loader-stub",
    },
    {
        "id": "plasticlist", "name": "PlasticList", "category": "datasets",
        "access": "open", "license": "open",
        "url": "https://www.plasticlist.org/",
        "blurb": "Lab results for 18 plastic chemicals across 300+ Bay-Area food "
                 "items, full methodology published.",
        "relevance": "Consumer-health / food-testing thesis color (niche).",
        "status": "registered", "integration": "link",
    },
    # ── Data infrastructure & ontologies ─────────────────────────────────
    {
        "id": "omop", "name": "OMOP Common Data Model", "category": "infra",
        "access": "open", "license": "Apache-2.0 (OHDSI)",
        "url": "https://ohdsi.github.io/CommonDataModel/",
        "blurb": "Standard schema for clinical + claims data so the same analysis "
                 "runs across different databases.",
        "relevance": "Normalize a target's heterogeneous data-room extracts into "
                     "one analyzable shape for diligence.",
        "status": "registered", "integration": "loader-stub",
    },
    {
        "id": "tuva", "name": "Tuva Health data model", "category": "infra",
        "access": "open", "license": "Apache-2.0",
        "url": "https://github.com/tuva-health/tuva",
        "blurb": "Open-source dbt project that standardizes messy claims/clinical "
                 "data into analytics-ready tables (with value sets).",
        "relevance": "Turn raw target claims feeds into clean RCM metrics fast.",
        "status": "registered", "integration": "loader-stub",
    },
    {
        "id": "sagerx", "name": "SageRx", "category": "infra",
        "access": "open", "license": "open",
        "url": "https://github.com/coderxio/sagerx",
        "blurb": "Open medication ontology pulling RxNorm, FDA NDC, and DailyMed "
                 "into clean queryable tables.",
        "relevance": "Drug-spend and formulary normalization for pharmacy/RCM.",
        "status": "registered", "integration": "loader-stub",
    },
    {
        "id": "rxnorm", "name": "RxNorm (RxNav API)", "category": "infra",
        "access": "api", "license": "US Gov / UMLS terms",
        "url": "https://lhncbc.nlm.nih.gov/RxNav/APIs/",
        "blurb": "NLM normalized drug nomenclature + crosswalks via the public "
                 "RxNav REST API.",
        "relevance": "Resolve/standardize drug names in diligence drug-spend data; "
                     "owns the NDC→RxCUI crosswalk other drug sources join to.",
        "status": "wired", "integration": "api-client",
    },
    {
        "id": "fda_ndc", "name": "FDA NDC Directory", "category": "infra",
        "access": "api", "license": "US Gov public domain",
        "url": "https://open.fda.gov/apis/drug/ndc/",
        "blurb": "openFDA API for the National Drug Code directory.",
        "relevance": "Map NDCs to products for pharmacy revenue analysis.",
        "status": "registered", "integration": "api-client",
    },
    {
        "id": "dailymed", "name": "DailyMed", "category": "infra",
        "access": "api", "license": "US Gov public domain",
        "url": "https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm",
        "blurb": "NLM structured product labeling (SPL) web service.",
        "relevance": "Label/indication enrichment for drug data.",
        "status": "registered", "integration": "api-client",
    },
    {
        "id": "blue_button", "name": "CMS Blue Button 2.0", "category": "infra",
        "access": "api", "license": "US Gov (OAuth, beneficiary-authorized)",
        "url": "https://bluebutton.cms.gov/",
        "blurb": "OAuth API that lets Medicare beneficiaries authorize apps to "
                 "pull their Part A/B/D claims as FHIR.",
        "relevance": "Patient-authorized claims ingestion pattern for data rooms.",
        "status": "registered", "integration": "api-client",
    },
    {
        "id": "hapi_fhir", "name": "HAPI FHIR server", "category": "infra",
        "access": "self-host", "license": "Apache-2.0",
        "url": "https://hapifhir.io/",
        "blurb": "The most widely used open-source FHIR server: a common "
                 "store/exchange format between systems.",
        "relevance": "Stand up a FHIR endpoint to normalize target EHR extracts.",
        "status": "registered", "integration": "self-host",
    },
    {
        "id": "metriport", "name": "Metriport", "category": "infra",
        "access": "self-host", "license": "AGPL-3.0 / open-core",
        "url": "https://github.com/metriport/metriport",
        "blurb": "Open-source, self-hostable on-ramp to pull HIE data and convert "
                 "formats to FHIR (with code crosswalking).",
        "relevance": "Bulk clinical-data acquisition for diligence.",
        "status": "registered", "integration": "self-host",
    },
    {
        "id": "open_wearables", "name": "Open Wearables", "category": "infra",
        "access": "self-host", "license": "open",
        "url": "https://github.com/openwearables",
        "blurb": "Self-hosted platform unifying wearable-device data behind one "
                 "API across brands/formats.",
        "relevance": "Remote-monitoring / digital-therapeutics target diligence.",
        "status": "registered", "integration": "self-host",
    },
    {
        "id": "medplum", "name": "Medplum (headless EHR)", "category": "infra",
        "access": "self-host", "license": "Apache-2.0 / open-core",
        "url": "https://github.com/medplum/medplum",
        "blurb": "Open-source headless EHR platform (self-host or hosted).",
        "relevance": "Reference architecture for EHR-native diligence tooling.",
        "status": "registered", "integration": "link",
    },
    {
        "id": "openemr", "name": "OpenEMR", "category": "infra",
        "access": "self-host", "license": "GPL-3.0",
        "url": "https://github.com/openemr/openemr",
        "blurb": "Long-standing open-source EHR/practice-management system.",
        "relevance": "Comp reference for EHR-replacement theses.",
        "status": "registered", "integration": "link",
    },
    {
        "id": "mimilabs", "name": "mimilabs", "category": "infra",
        "access": "open", "license": "open scripts",
        "url": "https://www.mimilabs.ai/",
        "blurb": "Ingests thousands of public CMS/CDC/FDA datasets into a "
                 "queryable warehouse; data-engineering scripts are open source.",
        "relevance": "Shortcut to a broad public-data warehouse for market maps.",
        "status": "registered", "integration": "loader-stub",
    },
    {
        "id": "clinical_nlp", "name": "Clinical NLP (cTAKES / medspaCy / scispaCy)",
        "category": "infra", "access": "open", "license": "Apache-2.0 / MIT",
        "url": "https://github.com/medspacy/medspacy",
        "blurb": "Open NLP pipelines for extracting structure from clinical and "
                 "biomedical free text.",
        "relevance": "Mine unstructured notes in a target's data room.",
        "status": "registered", "integration": "loader-stub",
    },
    # ── Open AI models ───────────────────────────────────────────────────
    {
        "id": "medgemma", "name": "MedGemma", "category": "models",
        "access": "model", "license": "Health AI Developer Foundations terms",
        "url": "https://huggingface.co/google/medgemma-4b-it",
        "blurb": "Google open-weight model over medical text + images (X-ray, "
                 "path, derm, ophthalmology).",
        "relevance": "On-prem clinical reasoning without sending data out.",
        "status": "registered", "integration": "model",
    },
    {
        "id": "meditron", "name": "Meditron", "category": "models",
        "access": "model", "license": "Llama-2 community",
        "url": "https://huggingface.co/epfl-llm/meditron-70b",
        "blurb": "LLM on Llama pretrained on PubMed, with disclosed training data.",
        "relevance": "Open biomedical reasoning baseline.",
        "status": "registered", "integration": "model",
    },
    {
        "id": "monai", "name": "MONAI", "category": "models",
        "access": "model", "license": "Apache-2.0",
        "url": "https://monai.io/",
        "blurb": "Open-source deep-learning framework for medical imaging.",
        "relevance": "Imaging-AI diligence reference stack.",
        "status": "registered", "integration": "link",
    },
    {
        "id": "biomistral", "name": "BioMistral", "category": "models",
        "access": "model", "license": "Apache-2.0",
        "url": "https://huggingface.co/BioMistral/BioMistral-7B",
        "blurb": "Mistral-7B fine-tuned on PubMed Central for biomedical text.",
        "relevance": "Lightweight on-prem biomedical NLP.",
        "status": "registered", "integration": "model",
    },
    # ── Open disease measurement ─────────────────────────────────────────
    {
        "id": "openwillis", "name": "OpenWillis", "category": "measurement",
        "access": "open", "license": "Apache-2.0",
        "url": "https://github.com/bklynhlth/openwillis",
        "blurb": "Python library for digital phenotyping: quantifies facial "
                 "expressivity, voice, and motor function as objective markers.",
        "relevance": "Digital-biomarker / eCOA platform diligence.",
        "status": "registered", "integration": "loader-stub",
    },
    {
        "id": "scikit_dh", "name": "Scikit Digital Health", "category": "measurement",
        "access": "open", "license": "MIT (Pfizer)",
        "url": "https://github.com/PfizerRD/scikit-digital-health",
        "blurb": "Turns raw wearable-sensor data into clinical metrics (gait "
                 "speed, activity, sleep, sit-to-stand).",
        "relevance": "Wearable-endpoint diligence for trial-tech targets.",
        "status": "registered", "integration": "loader-stub",
    },
    # ── Open hardware ────────────────────────────────────────────────────
    {
        "id": "openaps", "name": "Loop / OpenAPS", "category": "hardware",
        "access": "open", "license": "MIT / open",
        "url": "https://openaps.org/",
        "blurb": "Open-source artificial-pancreas software linking CGMs + insulin "
                 "pumps (patient-assumed risk).",
        "relevance": "Diabetes-device ecosystem context.",
        "status": "registered", "integration": "link",
    },
    {
        "id": "enable", "name": "e-NABLE", "category": "hardware",
        "access": "open", "license": "CC / open CAD",
        "url": "https://enablingthefuture.org/",
        "blurb": "Network sharing 3D-printable prosthetic-hand CAD files.",
        "relevance": "Open DME / prosthetics context (niche).",
        "status": "registered", "integration": "link",
    },
    {
        "id": "osl", "name": "Open Source Leg", "category": "hardware",
        "access": "open", "license": "open hardware",
        "url": "https://www.opensourceleg.org/",
        "blurb": "Open hardware + software platform for a powered prosthetic leg.",
        "relevance": "Open DME / prosthetics context (niche).",
        "status": "registered", "integration": "link",
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
    """Counts by integration status (registered / wired)."""
    counts: Dict[str, int] = {}
    for s in SOURCES:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    return counts


def category_label(cid: str) -> str:
    return _CAT_LABEL.get(cid, cid)
