# Healthcare Revenue Leakage Diligence Module — V2 Implementation Plan

> Status: planning → in progress. Owner: diligence module.
> This plan reconciles the V2 product brief against the **existing**
> `rcm_mc/diligence/` ingestion stack (Sessions 1–6) and defines the
> gap-fill build order. The headline finding: most of V2 already
> exists. V2 is **harden + gap-fill + library-parser refactor**, not a
> from-scratch build. That matches the brief's own rule: *use existing
> tools; build the smallest robust architecture.*

---

## 1. Existing architecture summary (what we already have)

The repo already ships a healthcare-claims diligence pipeline under
`rcm_mc/diligence/`, built over 6 sessions, with ~139 passing tests.

### Phase 1 — Ingestion & Normalization (`diligence/ingest/`)
- **`ccd.py`** — the load-bearing data contract: `CanonicalClaim`
  (grain = claim_id × line_number × source_system; ~40 fields incl.
  amounts, payer_raw/canonical/class, CARC `adjustment_reason_codes`,
  lifecycle status/dates), `TransformationLog` (row-level audit),
  `CanonicalClaimsDataset` (deterministic `content_hash`, JSON
  round-trip, `write()`). `CCD_SCHEMA_VERSION = "1.0.0"`.
- **`readers.py`** — CSV/TSV (stdlib), Excel (openpyxl), Parquet
  (pyarrow), and a **hand-rolled X12 837/835 subset** (`read_edi`,
  segments CLM/SV1/DTP/NM1/HI/DRG for 837; CLP/NM1/DTM/CAS/SVC for
  835). Returns `RawRow` + `ReaderResult` (encoding, malformed flag).
- **`ingester.py`** — `ingest_dataset(path) → CanonicalClaimsDataset`.
  ~35-field column-synonym map; multi-EHR rollup; duplicate-resubmit
  detection; **835↔837 remittance reconciliation** (`_reconcile_remittance`,
  by shared claim_id) ; ZBA write-off preservation.
- **`normalize.py`** — date parsing (7 formats), payer resolution
  (163 variants → ~40 canonical + `PayerClass`), CPT/ICD validation.
- **`tuva_bridge.py`** — maps CCD → Tuva Input Layer schema.

### Phase 2 — Benchmarks/analytics (`diligence/benchmarks/`)
- `kpi_engine.py` — Days-in-A/R, First-Pass Denial Rate, A/R>90,
  NRR, Cost-to-Collect, service→bill / bill→cash lag. Each `KPIResult`
  carries value, sample_size, citation, `qualifying_claim_ids`,
  `adjustment_reason_codes`, temporal validity.
- `_ansi_codes.py` — **CARC denial categorization**: `classify_carc` /
  `classify_carc_set` → {FRONT_END, CODING, CLINICAL, PAYER_BEHAVIOR,
  CONTRACTUAL, UNCLASSIFIED} with precedence. ~30 codes mapped.
- `cohort_liquidation.py`, `cash_waterfall.py` (7-step cascade + QoR
  divergence), `contract_repricer.py`.

### Integrity / provenance / UI
- `diligence/integrity/` — 6 guardrails (`preflight.run_ccd_guardrails`).
- `diligence/ccd_bridge.py` — CCD KPIs → packet `observed_metrics`.
- `provenance/` — CCD-derived provenance nodes.
- Routes in `server.py`: `/diligence/ingest` (Phase 1, **fixture
  selector only**), `/diligence/benchmarks`, `/diligence/qoe-memo`
  (draft), `/import` (`rcm_mc/data/edi_parser.py`, a *separate* simpler
  837/835 parser), `/revenue-leakage`.
- Fixtures: `tests/fixtures/messy/` (10) + `tests/fixtures/kpi_truth/`
  (8), each with `expected.json`.

### Repo infra (constraints for V2)
- DB: **SQLite via stdlib `sqlite3`**, idempotent `CREATE TABLE IF NOT
  EXISTS` migrations, `rcm_mc/portfolio/store.py`. No ORM, no Postgres.
- Uploads: `server.py` multipart (`_parse_multipart`), `/upload` +
  `/new-deal/upload`; files written to a temp dir then parsed.
- No background-job system (in-memory queue; CLI for cron).
- Tests: `pytest` + `unittest`; **no mocks of our own code**; real
  HTTP server on a free port for route tests.
- **Zero new *core* runtime deps** without discussion (CLAUDE.md).
  `duckdb`/`dbt`/`pyarrow` already exist as optional `[diligence]`
  extras. `x12-python`, `pyx12`, `tuva` are **not** installed.

---

## 2. V2 goals → existing-code reconciliation

| V2 requirement | Status | Where / gap |
|---|---|---|
| Snapshot upload (files) | Partial | multipart exists; `/diligence/ingest` is fixture-only — must accept uploads |
| ZIP/VDR package upload | **Missing** | new `ingestion/zip_processor.py` |
| File-type + 835/837 + delimiter detection | Partial | `readers` detect by suffix + `ST*835/837`; ISA delimiter detection is implicit — formalize `FileDetectionResult` |
| **Parser adapter layer** | **Missing** | hand-rolled inline parser; build adapter interface + `X12PythonAdapter` + harness + ADR |
| Normalized staging (payers/providers/claims/lines/adjustments) | Done | the **CCD** is this; do NOT rebuild as 5 parallel tables |
| **PHI tokenization** | **Missing** | `patient_id` stored raw; add `security/phi_tokenization.py` |
| Tuva compatibility mapping | Done | `tuva_bridge.py` (+ mapping doc to add) |
| 835↔837 matching w/ confidence + reason + score | Partial | reconciliation matches by claim_id only; add layered `matching/` + `claim_matches` |
| Data Confidence Score (0–100) + issue list | Partial | guardrails + transformation log exist; add scalar score + plain-English summaries + `data_quality_issues` |
| Denial/adjustment categorization | Done | `_ansi_codes.classify_carc*`; extend metadata (preventability/recoverability/EBITDA-relevance) |
| Analytics (denial/payer/CPT/provider) | Partial | KPI engine + waterfall exist; add payer/CPT/provider variance + outlier marts |
| PE-readable findings (title/evidence/impact/confidence/follow-up/caveats) | **Missing** | new `findings/` |
| Follow-up request generator | Partial | `infra/diligence_requests.py` has content; add finding-tailored generator |
| **Markdown diligence memo** | **Missing** | HTML pages only; new `reporting/markdown_memo.py` |
| PHI-safe, conservative-language outputs | Partial | enforce in memo + LLM boundary |
| Use existing libraries / fallback not primary | New | x12-python primary candidate (optional dep), hand-rolled = fallback |
| No live integrations | Done | snapshot-only throughout |

**Bottom line:** ~10 focused gaps. Build them onto the CCD; do not
fork a parallel data model.

---

## 3. Module structure (extend `rcm_mc/diligence/`, repo conventions)

We extend the existing package rather than create a new
`healthcare_snapshot/` top-level (brief says: adapt to repo
conventions). New/changed subpackages:

```
rcm_mc/diligence/
  ingest/            (exists) readers, ccd, ingester, normalize, tuva_bridge
  parsers/           (NEW) adapter interface + library/fallback adapters + harness
    base.py            ParserAdapter protocol + shared dataclasses
    fallback_adapter.py  wraps ingest/readers.read_edi (always available)
    x12_python_adapter.py  optional, behind import guard
    detection.py       FileDetectionResult, ISA delimiter + txn-type detection
    harness.py         runs all adapters over fixtures → comparison report
  ingestion/         (NEW) zip_processor, upload_metadata
  security/          (NEW) phi_tokenization (HMAC), retention policy, audit hook
  matching/          (NEW) layered 837↔835 match → ClaimMatch(confidence/reason/score)
  reconciliation/    (NEW) data_confidence (0–100) + plain-English issue summaries
  analytics/         (NEW) payer_variance, cpt_variance, provider_outliers,
                     denial_preventability, payer_concentration (over CCD + KPIs)
  findings/          (NEW) finding_generator, follow_up_generator, templates
  reporting/         (NEW) markdown_memo (PHI-safe, conservative), memo templates
  store/             (NEW) ccd_store + v2 SQLite tables (see §5)
  benchmarks/        (exists) KPI engine + _ansi_codes (reuse for analytics)
  integrity/         (exists) guardrails (reuse in data confidence)
```

Tests under `tests/` (repo convention) as `test_hcrl_*.py` +
fixtures under `tests/fixtures/edi/`.

---

## 4. Parser evaluation strategy

The brief's headline ask. Approach:

1. **Adapter interface** (`parsers/base.py`): `detect(path) →
   FileDetectionResult`, `parse(path) → list[ParsedTransactionSet]`,
   `validate(path) → ValidationReport`, `extract_metadata(path) →
   ParsedFileMetadata`. Internal types are library-independent.
2. **`FallbackSegmentAdapter`** wraps the existing `read_edi` — always
   available, zero new deps, becomes the documented fallback (never the
   primary per acceptance criterion #19).
3. **`X12PythonAdapter`** — evaluate `x12-python`; install only into an
   evaluation venv / optional extras group `[edi]`, behind an import
   guard so core `rcm_mc` keeps zero new hard deps.
4. **`harness.py`** runs every available adapter over the EDI fixtures
   and emits a comparison table (parse/validate success, txn type,
   delimiters, claims/lines/adjustments extracted, error quality,
   runtime, licensing). 
5. **ADR** `docs/adr/healthcare-parser-selection.md` records primary vs
   fallback, gaps, licensing (pyx12=BSD-ish, x12-python=check,
   EDIReader=GPL → reference only), and revisit triggers.

Decision gate: do not deepen analytics until the adapter boundary
produces CCD-compatible output from at least the fallback adapter.

---

## 5. Schema / persistence plan (deviation from brief, documented)

The brief lists 14 relational tables (uploaded_files, edi_*, payers,
providers, patients_tokenized, claims, service_lines, adjustments,
claim_matches, data_quality_issues, analytics_runs, diligence_findings,
generated_memos). Building all 14 would **duplicate the CCD** and
create drift between two sources of truth.

**Decision:** the CCD remains the single source of truth for
claims/lines/adjustments/payers/providers. We persist via additive
SQLite tables (idempotent migrations, repo convention) only where the
UI/workflow needs durable, queryable, cross-run state:

- `hcrl_uploaded_files` — id, project_id, filename, file_type,
  detected_transaction_type, upload/parse/validation status, storage_key,
  retention_policy, uploaded_by, timestamps.
- `hcrl_ccd_runs` — id, project_id, ingest_id, content_hash,
  ccd_json (blob), source_files, created_at. (Fulfils the `ccd_store`
  the `ccd.py` docstring already anticipates.)
- `hcrl_claim_matches` — id, project_id, ccd_run_id, submitted_row_id,
  remittance_row_id, match_confidence, match_reason, match_score,
  review_status.
- `hcrl_data_quality_issues` — id, project_id, ccd_run_id, severity,
  issue_type, entity_type, entity_ref, message, context_json.
- `hcrl_analytics_runs` — id, project_id, ccd_run_id, status,
  input_summary_json, metrics_json, data_confidence_score, created_at.
- `hcrl_diligence_findings` — id, project_id, analytics_run_id,
  finding_type, title, summary, evidence_json, estimated_impact_amount,
  confidence, follow_up_json, limitations_json, created_at.
- `hcrl_generated_memos` — id, project_id, analytics_run_id,
  memo_markdown, memo_status, created_by, created_at.

`claims`/`service_lines`/`adjustments`/`payers`/`providers` are
**read models** derived from the stored CCD on demand (a thin query
layer), not separate base tables. Patient identity is tokenized before
the CCD is ever persisted (see §6); raw MRNs never hit disk.

---

## 6. PHI / security assumptions

- **Tokenize at the normalization boundary**: `security/phi_tokenization.py`
  replaces `patient_id` with `HMAC-SHA256(mrn, per-project salt)`
  before the CCD is built/persisted. Store only the token + a
  non-reversible `source_hash`; never the raw MRN or patient name.
- **No PHI to LLMs**: memo generation consumes a PHI-safe aggregate
  object only (metrics + findings, no claim lines, no member IDs).
- **UI never renders patient-level rows.** Aggregate-only.
- **Retention**: `hcrl_uploaded_files.retention_policy` + a delete path.
- **Audit**: hook the existing audit log if present.
- **User warning** on upload: "Healthcare claims/remittance files may
  contain PHI. Upload de-identified data unless agreements permit."

---

## 7. Test fixture plan

New synthetic fixtures under `tests/fixtures/edi/` (no real PHI;
tokenizable MRNs like `MRN0001`):
clean 835, clean 837P, clean 837I, matched 835/837 pair, auth-denial
heavy, timely-filing denial, payer underpayment, provider outlier,
duplicate claim, missing-NPI, unreconciled-BPR, malformed EDI,
multi-transaction EDI, multi-CAS, provider-level PLB, and a ZIP
bundling several. Each exercises CLP/BPR/CAS/SVC/NM1/DTM (835) and
CLM/SV1/DTP/NM1/HI (837). Reuse the existing `expected.json` pattern.

---

## 8. Build order (loop until acceptance criteria met)

1. Plan (this doc) ✅ + module skeleton (`__init__` stubs).
2. EDI synthetic fixtures + `tests/fixtures/edi/`.
3. Parser adapter interface (`parsers/base.py`) + detection types.
4. `FallbackSegmentAdapter` (wrap `read_edi`) + tests.
5. Parser evaluation harness + evaluate x12-python (optional) → ADR.
6. PHI tokenization + wire into ingester normalize step.
7. SQLite migrations (§5) + `ccd_store` save/load.
8. ZIP/VDR upload processor + upload metadata.
9. Layered 835↔837 matching → `claim_matches` + tests.
10. Data Confidence Score (0–100) + plain-English issue list + tests.
11. Analytics marts (payer/CPT/provider variance + denial preventability).
12. Findings generator (V2 finding structure) + tests.
13. Follow-up request generator (tailored from findings).
14. Markdown memo generator (PHI-safe, conservative) + tests.
15. Tuva mapping doc (`tuva/` mapping table) — abstraction + TODOs.
16. Wire live upload into `/diligence/ingest` + minimal UI screens.
17. Full test pass + lint/typecheck; implementation summary.

Each step ships as its own PR, gated by the relevant `test_hcrl_*` +
existing diligence tests, and the full suite before any
analytics/logic merge (this is backend logic, not presentation — the
fast-lane UI gating does NOT apply here).

---

## 9. Risks & unresolved decisions

- **x12-python fitness/licensing** — unknown until evaluated; fallback
  guarantees we are never blocked. (ADR will record.)
- **New optional dep** — keep x12-python in an `[edi]` extras group;
  core stays zero-new-dep. Confirm with maintainer before making
  primary.
- **Service-line grain** — CCD already is line-grained; "claims vs
  service_lines" split in the brief is satisfied by line_number. No
  separate table.
- **Matching false-positives** — low-confidence matches excluded from
  financial conclusions unless explicitly caveated (acceptance #9).
- **Opportunity language** — never "guaranteed EBITDA"; only
  "potentially preventable / estimated / requires validation."
- **Two ingestion paths** (`diligence/ingest` vs top-level
  `rcm_mc_diligence/` dbt path) — V2 targets the lightweight Python
  path; Tuva/dbt stays optional.
