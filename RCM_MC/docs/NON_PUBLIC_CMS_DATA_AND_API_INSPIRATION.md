# Non-Public CMS Data, Claims APIs & Open-Source Inspiration

**What this is.** A research reference for the data that sits *one rung past*
the free public aggregate sources the product ships on today — the credentialed
CMS microdata programs, the beneficiary/claims FHIR APIs, the interoperability
mandates that are minting new payer APIs, and the open-source projects whose
*algorithms* we can reimplement natively to climb that rung without taking on
their runtime. It is the written companion to the machine-readable registry in
[`rcm_mc/data_public/nonpublic_cms_registry.py`](../rcm_mc/data_public/nonpublic_cms_registry.py)
and the internal lab it renders at **`/tools/nonpublic-cms`**.

**Why now.** The existing catalogs answer *"what free public data can I pull?"*
([`public_api_catalog.py`](../rcm_mc/data_public/public_api_catalog.py) →
`/data-apis`) and *"what open-source datasets/tooling exists?"*
([`open_data_registry.py`](../rcm_mc/data_public/open_data_registry.py) →
`/tools/open-data`). Neither answers the question a partner asks in confirmatory
diligence: *"the target has (or claims) beneficiary-level Medicare data — what is
that, how would we get it, and what can we build against it?"* This doc is that
answer, and it stays honest about the product's load-bearing invariant: **stdlib
+ numpy + pandas only, no external services, nothing leaves the laptop** (see
[`CLAUDE.md`](../CLAUDE.md)). Beneficiary-level claims and OAuth/DUA feeds
are **not render-path data** — they are an upgrade path documented here, with a
clean line drawn around what may ever run in the hot path.

> **Sourcing & honesty.** Every fact below was sourced from official CMS / HL7 /
> GitHub documentation in July 2026. Values that are fee- or date-sensitive
> (VRDC seat prices, AB2D/DPC onboarding status, exact IG version pins) carry a
> **⚠ verify** flag in the registry and must be confirmed live before anyone
> relies on them. We do not launder an unconfirmed number into an authoritative
> one — the same discipline the codebase applies to synthetic data.

---

## 1. The CMS data disclosure ladder

CMS releases beneficiary data along three rungs of identifiability. Each higher
rung carries more granular data and heavier legal gating. Knowing which rung a
dataset sits on tells you the *time and money* it costs — which is itself a
diligence-planning fact, not a technicality.

| Rung | Product class | Identifiability | Legal instrument | IRB | Fee |
|---|---|---|---|---|---|
| **1 — Public-use** | PUFs, **DE-SynPUF**, aggregate Medicare PUFs | De-identified / synthetic; no PHI | None (open download) | No | Free |
| **2 — Limited Data Set (LDS)** | Standard Analytic Files (SAFs) | Beneficiary-level; HIPAA *direct* identifiers stripped (keeps dates, ZIP) | Signed **LDS DUA** + stated purpose | Generally **no** | Cost-recovery |
| **3 — Research Identifiable File (RIF)** | Standard analytic RIFs, MBSF, via **CCW/VRDC** | Individual-level, fully identifiable / linkable | **RIF DUA** + protocol via **ResDAC** | **Usually required** | High (+ VRDC seat/project fees) |

Two nuances worth stating precisely, because people get them wrong:

- **LDS is still an *identifiable* file class** under CMS policy — it is not a
  PUF. It merely lacks HIPAA *direct* identifiers; it retains dates and ZIP.
- **The gateway is ResDAC**, not a download page. RIF requests it shepherds run
  **~3–5 months** end to end — you cannot get RIF data inside a typical deal
  window. Targets that have it got it through a standing DUA or an ACO/PDP
  program entitlement, and *that* is the diligence question.

Sources: [CMS Data Available to Researchers](https://www.cms.gov/data-research/cms-data/data-available-researchers) ·
[ResDAC federal regulations](https://resdac.org/articles/federal-regulations-governing-release-cms-data) ·
[CMS RIF DUA Policy Guide (PDF)](https://www.cms.gov/files/document/research-identifiable-file-data-use-agreement-policies.pdf).

---

## 2. Credentialed CMS microdata programs

| Program | Rung / access | Granularity | Parts | API? | Cost | Typical holder |
|---|---|---|---|---|---|---|
| **ResDAC** | Gateway (free advisory) | n/a | — | No | Free | All RIF requesters |
| **CCW / VRDC** | RIF (DUA + often IRB) | Bene-level, enclave | A/B/D + Medicaid | No (in-enclave) | High (seat + project + storage) | Academics, large payers |
| **LDS / SAF** | LDS (DUA, no IRB) | Bene-level, de-ID'd | A/B (D separate) | No (file order) | Moderate fee | RCM benchmarking, diligence |
| **RIF / SAF** | RIF (DUA + IRB) | Bene-level, identifiable | A/B/D + Medicaid | No | High fee | Longitudinal research |
| **CCLF** | ACO entitlement | Bene-level, claim-line | A/B/D | Flat file (BCDA = API) | Free w/ participation | MSSP / REACH ACOs |
| **DE-SynPUF** | Public (rung 1) | Synthetic bene-level | A/B/D (2008–10) | No (download) | Free | Prototyping / testing |

**The one to actually use today: DE-SynPUF.** It is the zero-friction, PHI-free
proxy for building and testing claims pipelines and RCM logic before anyone
commits to the multi-month RIF path. Caveat, stated plainly: it is 2008–2010,
synthetic, and pre-ICD-10 — valid for pipeline tests, **not** for market sizing
or current coding. It pairs with Synthea (§4) as our fixture strategy.

**The one to understand for diligence: CCLF.** For any ACO / value-based target,
CCLF *is* the data asset they already receive monthly. The diligence signal is
not "do they have data" — it's how well they exploit it (care coordination,
financial reconciliation, network-leakage analysis). A target on BCDA (the API,
§3) versus manual CCLF file handling is a data-maturity tell.

Full per-program detail — access model, latency, cost structure, 2025 changes
(LDS dropped beneficiary sex in Apr 2025; older SAFs being retired) — lives in
the registry entries `resdac`, `ccw_vrdc`, `cms_lds`, `cms_rif`, `cclf`,
`de_synpuf`.

---

## 3. CMS beneficiary & claims FHIR APIs

Four Medicare claims APIs exist, differentiated by **consent model** — and which
one a company may legally use is dictated by its business model. This is a
gating diligence question, not a technical preference.

| API | Consent model | FHIR | Auth | Who's eligible | Bulk `$export` |
|---|---|---|---|---|---|
| **Blue Button 2.0** | Individual beneficiary | STU3 (v1) / R4 (v2) | OAuth 2.0 (3-legged) | Registered consumer apps | No |
| **BCDA** | ACO attribution | R4 | SMART Backend Services (JWT) | MSSP / REACH ACOs, APM entities | Yes (`/Group/$export`) |
| **DPC** | Provider ↔ patient treatment | R4 | SMART Backend Services | FFS providers (pilot) | Yes (`/Group/$export`) |
| **AB2D** | Plan enrollment | R4 | OAuth2 via Okta/IDM | Standalone Part D (PDP) sponsors | Yes (`/Patient/$export`) |

Two structural facts make these cheaper to reason about than they look:

- **Shared plumbing.** BCDA, DPC, and AB2D all speak **R4 + FHIR Bulk Data
  (`$export`) + NDJSON + SMART Backend Services**. A target that built robust
  `$export` polling and NDJSON ingestion for one has reusable plumbing for all
  — a genuine engineering asset to credit in diligence.
- **One canonical schema.** All of them serve `ExplanationOfBenefit` +
  `Patient` + `Coverage`. The claims-field → FHIR-EOB mapping is public
  (CMS's [beneficiary-fhir-data](https://github.com/CMSgov/beneficiary-fhir-data),
  CC0), so we can mirror a clean canonical claim schema in pandas without running
  a FHIR server.

**Status flags to verify:** DPC production onboarding was reported **paused** in
2025 (identity-verification rework; sandbox open); AB2D's current active-
onboarding status could not be re-confirmed. Both carry ⚠ verify in the
registry. Blue Button 2.0's per-app rate limit is likewise unconfirmed.

Registry entries: `bluebutton`, `bcda`, `dpc`, `ab2d`, `marketplace_api`.

---

## 4. The interoperability mandates minting new payer APIs

The above APIs are Medicare-run. The larger opportunity is **payer-hosted** FHIR
surfaces created by regulation — and CMS-0057-F is the single biggest RCM
tailwind on the board.

- **CMS-9115-F** (Interoperability & Patient Access, 2020) forced MA, Medicaid/
  CHIP, and FFE-QHP payers to stand up patient-authorized **Patient Access** and
  **Provider Directory** APIs, on named IGs (US Core, **CARIN Blue Button**, Da
  Vinci **PDex** / **Plan-Net**, US Drug Formulary).
- **CMS-0057-F** (Interoperability & Prior Authorization, 2024) is the active
  catalyst. Operational provisions by **Jan 1 2026** (72-hour expedited / 7-day
  standard PA decisions; first public PA metrics due **Mar 31 2026**); four FHIR
  APIs live by **Jan 1 2027** — Patient Access (+PA), **Provider Access**,
  Payer-to-Payer, and the **Prior Authorization API (PARDD)** built on Da Vinci
  **CRD + DTR + PAS**. It converts prior authorization — a top denial / days-in-AR
  driver — into an API-addressable market with a hard 2027 wall. *Diligence lens:
  does a payer-facing target's roadmap map to CRD/DTR/PAS, and does it have
  design partners ahead of the deadline?*

Registry entries: `cms_9115f`, `cms_0057f`, `fhir_bulk`. These are `reference`
status — specs to track, not data to ingest. They connect directly to the
existing [`regulatory_calendar`](../rcm_mc/diligence/regulatory_calendar/) kill-
switch: the 2026/2027 PA deadlines are datable thesis-driver events.

Sources: [CMS-9115-F](https://www.cms.gov/priorities/burden-reduction/overview/interoperability/policies-regulations/cms-interoperability-patient-access-final-rule-cms-9115-f) ·
[CMS-0057-F](https://www.cms.gov/initiatives/burden-reduction/overview/interoperability/policies-regulations/cms-interoperability-prior-authorization-final-rule-cms-0057-f) ·
[FHIR Bulk Data IG](https://hl7.org/fhir/uv/bulkdata/).

---

## 5. Open-source algorithms to reimplement natively

This is where the durable value is. The codebase already made this call twice —
Naive-Bayes instead of scikit-learn, a stdlib inverse-normal instead of scipy,
and the [Tuva + Myelin adoption](TUVA_MYELIN_INTEGRATION.md) (*wrap the idea, not
the dependency*). The research surfaced a cluster of projects that fit our exact
constraint even better than Tuva does.

### The headline find: the `yubin-park` pure-Python ecosystem

Small, algorithm-first, **Apache-2.0**, **zero runtime risk** (pure Python with
bundled CMS/AHRQ reference data). These are almost exactly the modules we would
otherwise hand-build.

| Project | Reusable artifact | Maps onto |
|---|---|---|
| **[hccpy](https://github.com/yubin-park/hccpy)** | CMS-HCC risk adjustment — ICD-10→CC map, hierarchy trumping, interactions, **V28** coefficients (100% weight PY2026) | [`diligence/risk_adjustment`](../rcm_mc/diligence/risk_adjustment/) — our native RAF scorer is currently ~24 of ~115 HCCs; hccpy's bundled CSVs are the path to full coverage |
| **[hcuppy](https://github.com/yubin-park/hcuppy)** | AHRQ HCUP groupers — **CCS/CCSR** (ICD-10 → ~285 categories), **Elixhauser** comorbidity index (+ van Walraven weights), CCI, Utilization Flags | Case-mix adjustment for apples-to-apples peer benchmarking (HCRIS X-Ray, RCM benchmarks) |
| **[drgpy](https://github.com/yubin-park/drgpy)** | Pure-Python **MS-DRG** grouper (approx.) | Inpatient reimbursement estimation & DRG-shift / upcoding analysis — the no-JVM alternative to Myelin |
| **[parse834, ouidxpy, …](https://github.com/yubin-park)** | X12 **834** enrollment parser; Johns Hopkins **Overuse Index** low-value-care ICD-10 flags | ouidxpy → a utilization-quality diligence lens; parse834 → clean EDI-parse pattern (cf. [`data/edi_parser.py`](../rcm_mc/data/edi_parser.py)) |

### The data models & specs (mine the seeds, skip the runtime)

- **[Tuva Project](https://github.com/tuva-health/tuva)** (Apache-2.0) — already
  partly adopted. Its `seeds/value_sets/` (ICD-10, HCPCS, HCC, service
  categories) and data-quality tests are portable to pandas; the dbt runtime is
  not.
- **[OHDSI OMOP CDM](https://github.com/OHDSI/CommonDataModel)** (Apache-2.0) —
  the `cost` and `payer_plan_period` tables and the concept-crosswalk pattern
  (`concept` / `concept_relationship` / `concept_ancestor`) are a reusable
  terminology-mapping model. CDM is just DDL; ATLAS is reference-only.
- **[Myelin / LibrePPS](https://github.com/Bedrock-Billing/Myelin)** (MIT) — the
  editor → grouper → pricer *orchestration* and field-level input schemas are the
  reusable artifact; the pricing math lives in CMS JARs (JVM = high runtime risk).
  *Naming flag:* the repo is `Bedrock-Billing/Myelin`, not `LibrePPS` (org alias).
- **[Synthea](https://github.com/synthetichealth/synthea)** (Apache-2.0) — use
  the pre-generated synthetic outputs as PHI-free fixtures; skip the JVM.
- **[CQL / ELM](https://github.com/cqframework/clinical_quality_language)**
  (Apache-2.0) — if we ever express quality measures natively, ELM's JSON AST is
  the portable target. (`cql-engine` is archived — cite the active repo.)

**A note on CMS official groupers.** CMS does **not** publish MS-DRG / IOCE /
IPPS pricer *source* on GitHub — it ships compiled Java (FY2026 = Java 17). So
there is no `CMSgov/ms-drg-grouper` to reuse; `drgpy` (native approximation) and
Myelin (JVM bridge) are the practical substitutes. Reimplement the deterministic
parts; document any native pricer as an approximation with a swap path to the
certified engine, exactly as [`TUVA_MYELIN_INTEGRATION.md`](TUVA_MYELIN_INTEGRATION.md)
already does for the RAF scorer.

Registry entries: `hccpy`, `hcuppy`, `drgpy`, `yubin_utils`, `tuva`, `omop_cdm`,
`myelin`, `bfd`, `synthea`, `cql`.

---

## 6. Live public APIs — reachable *now*

Three of the candidate integrations are not aspirational — they are real public
APIs that returned real data from this environment during the research pass, and
two already have in-repo clients:

| API | Verified call | Backing client |
|---|---|---|
| **NPPES NPI Registry** | `Mayo Clinic / MN` → NPI 1881018208 | [`nppes_api_client.py`](../rcm_mc/data_public/nppes_api_client.py) |
| **CMS Coverage API** (Medicare Coverage DB) | `dialysis` NCD search → NCD 130.8 / 230.7 | wrapped by the CMS Coverage service |
| **ICD-10-CM/PCS code service** | `end stage renal disease` → N18.6 (HIPAA-valid) | code-lookup / validation |

These are the model for how a `registered` entry graduates to `reachable`: a
stdlib client that fails **closed** (unreachable API → raise, never return
synthetic/partial data), pure URL builders, injectable transport for no-egress
tests — the pattern already established in
[`public_api_clients.py`](../rcm_mc/data_public/public_api_clients.py).

Registry entries: `nppes_api`, `cms_coverage_api`, `icd10_service`.

---

## 7. What to build, in what order

Ranked by **value per unit of effort**, respecting the no-network invariant. The
right first move is rarely "get the most complete data" — it's "the lift you can
ship in weeks for $0 without breaking the posture."

1. **Vendor the `yubin-park` reference data (hccpy V28, hcuppy CCS/Elixhauser).**
   Highest lift-per-effort. Pure Python, Apache-2.0, bundled data, maps straight
   onto `risk_adjustment` and peer benchmarking. No new runtime dep, no network.
   *Ship first.*
2. **DE-SynPUF + Synthea fixture harness.** A PHI-free claims corpus to test any
   grouper/pipeline we reimplement. Unblocks everything downstream. Free, offline.
3. **`drgpy`-style native MS-DRG grouper.** Inpatient reimbursement & upcoding
   analysis without a JVM; documented as an approximation with a Myelin swap path.
4. **A FHIR-EOB canonical claim schema** (mirrored from BFD's mapping) — so that
   *if* a target's BCDA/DPC extract ever lands, our marts already speak it. Schema
   work now, ingestion later.
5. **`cms_coverage_api` / `nppes` client graduation** — surface the already-
   reachable live APIs behind the same fail-closed client pattern, gated to
   environments with outbound access.
6. **Track CMS-0057-F** in the regulatory calendar — the 2026/2027 PA API
   deadlines are datable kill-switch events, no ingestion required.

Deferred by design (documented, not built): LDS/RIF/CCW ingestion (DUA + months +
fees; belongs to a partner with a standing agreement), and any live OAuth/bulk-
FHIR pull (outside the render-path posture — a confirmatory-diligence adapter,
never a hot-path loader).

---

## 8. Where this lives

- **Registry (source of truth):**
  [`rcm_mc/data_public/nonpublic_cms_registry.py`](../rcm_mc/data_public/nonpublic_cms_registry.py)
  — metadata only, no network at import/render, honest `reachable / registered /
  reference` status.
- **Internal lab UI:** `/tools/nonpublic-cms` (+ `/<id>` detail) —
  [`rcm_mc/ui/nonpublic_cms_lab_page.py`](../rcm_mc/ui/nonpublic_cms_lab_page.py).
  Deliberately backend-only, badged WIP, **not** in the front nav (verified by
  test), reachable by direct URL and from the Tools-index footer.
- **Tests:** [`tests/test_nonpublic_cms_lab.py`](../tests/test_nonpublic_cms_lab.py)
  — pins registry well-formedness, honest-status invariants (only the three
  verified APIs may be `reachable`; credentialed microdata may never be), page
  rendering, verify-flag surfacing, and nav isolation.

Related prior art: [`INTEGRATIONS_PLAN.md`](INTEGRATIONS_PLAN.md) (outbound
integrations) · [`DATA_ACQUISITION_STRATEGY.md`](DATA_ACQUISITION_STRATEGY.md)
(public-data acquisition ranking) · [`TUVA_MYELIN_INTEGRATION.md`](TUVA_MYELIN_INTEGRATION.md)
(the wrap-the-idea-not-the-dependency precedent).
