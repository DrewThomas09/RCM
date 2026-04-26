# Report 0136: External Dep Audit — `pyarrow`

## Scope

Audits `pyarrow` external dep — the Apache Arrow Python bindings used by `[diligence]` extras and `rcm_mc/diligence/`. Sister to Reports 0016 (pyyaml), 0046 (numpy), 0053 (pandas), 0076 (matplotlib), 0083 (openpyxl), 0106 (python-pptx), 0113 (comprehensive sweep).

## Findings

### Pin

`pyproject.toml [project.optional-dependencies] diligence` (per Report 0101 line 51):

```toml
diligence = [
    "duckdb>=1.0,<2.0",
    "dbt-core>=1.10,<2.0",
    "dbt-duckdb>=1.10,<2.0",
    "pyarrow>=10.0",
]
```

**`pyarrow>=10.0` — NO upper bound.** Same loose-pin pattern as Report 0106 MR591 (python-pptx) and Report 0113 MR636 (10 of 19 deps loose).

### Production import sites — 6 files, all lazy

`grep -rEn "^\s*(from|import)\s+pyarrow"`:

| File | Lines | Submodules used |
|---|---|---|
| `rcm_mc_diligence/ingest/file_loader.py` | 175, 211, 212, 229, 230, 231, 315, 336 | `pyarrow`, `.compute`, `.csv`, `.parquet` |
| `rcm_mc_diligence/fixtures/synthetic.py` | 188, 189 | `pyarrow`, `.parquet` |
| `rcm_mc/diligence/ingest/readers.py` | 155 | `pyarrow.parquet` |
| `rcm_mc/diligence/ingest/tuva_bridge.py` | 137, 306 | `pyarrow` |
| `tests/fixtures/messy/generate_fixtures.py` | 172, 173 | `pyarrow`, `.parquet` (test) |

**~14 lazy import statements** across 5 files (4 production + 1 test fixture). All wrapped in function bodies (compliant with `[diligence]` optional-extras pattern per Report 0113).

### Submodule usage breakdown

| Submodule | Sites | Use |
|---|---|---|
| `pyarrow` (top-level `pa`) | many | `pa.table`, `pa.concat_tables`, `pa.string()`, `pa.types.is_string`, exception types `pa.lib.ArrowInvalid` / `pa.lib.ArrowTypeError` |
| `pyarrow.parquet` (`papq` / `pq`) | 4+ | `papq.read_table` for Parquet I/O |
| `pyarrow.csv` (`pacsv`) | 1 | CSV reading |
| `pyarrow.compute` (`pc`) | 1 | `pc.cast(col, pa.string())` for type coercion |

### Trust boundary

The code **READS** Parquet + CSV files from disk via `papq.read_table(path)` (line 238 in `file_loader.py`).

**Q1**: Are the parquet/CSV files user-uploaded, or system-generated?

Per `rcm_mc_diligence/` design (Report 0122): the package is "diligence-flow data ingestion." Partner uploads CSV/parquet from EHR exports. **Highly likely user-uploaded.**

If user-uploaded → pyarrow CVEs apply.

### CVE history (CRITICAL FINDING)

| CVE | Affects | Description |
|---|---|---|
| CVE-2023-47248 | pyarrow 0.14.0 - 14.0.0 | Deserialization vulnerability in `pyarrow.ipc` / `pyarrow.parquet` — RCE via crafted Parquet/IPC stream |
| CVE-2024-52338 | pre-18.1.0 | Out-of-bounds read in record-batch reader |

**`pyarrow>=10.0` (current pin) ALLOWS vulnerable 10.x, 11.x, 12.x, 13.x, 14.0.0** — the version range covered by CVE-2023-47248 (RCE).

If `pip install seekingchartis[diligence]` resolves to pyarrow 10.x or 11.x or 12.x or 13.x or 14.0.0 — **REMOTE CODE EXECUTION via crafted partner-uploaded Parquet file**.

**MR770 below — CRITICAL.**

### Error handling discipline (good)

`file_loader.py:195`:
```python
except (pa.lib.ArrowInvalid, pa.lib.ArrowTypeError):
    # Heterogeneous types across clinics (the multi-EHR pattern)
    ...
```

**Narrow exception catch.** Cross-link Report 0020 broad-except discipline. **Good** — catches only the expected pyarrow exceptions, not all-of-Exception.

### Upstream status

- **Project**: [Apache Arrow](https://arrow.apache.org/) — multi-language data interchange.
- **Maintenance**: actively maintained; major release every ~6 months.
- **Latest as of audit**: pyarrow 18.1.0+ (with all known CVEs patched).
- **Not abandoned**: NO.

### Cross-link to Report 0083 trust-boundary finding

Report 0083 (openpyxl): "code WRITES xlsx, doesn't typically READ untrusted xlsx — ZIP-bomb risk LOW."

**This report (pyarrow) finds the OPPOSITE**: the code DOES READ user-uploaded data (Parquet from partner uploads). **Higher attack surface.** Cross-link Report 0083 MR469 — same vulnerability class, different file format, much greater current risk.

### `rcm_mc_diligence/ingest/file_loader.py` — the data-entry point

Per Report 0122: this 347-line module is the **inbound data adapter layer**. It loads partner-supplied data via:
- `_read_one(path, column_overrides)` — single-file read
- `read_files(paths, column_overrides)` (alluded to) — multi-file merge
- `pa.concat_tables(tables, promote_options="default")` — schema-promotion at line 194

If a partner uploads a malicious parquet file → goes straight through `papq.read_table(path)` → pyarrow's parser → potential RCE on vulnerable versions.

### Cross-link to Report 0127 + 0126 (active branch writes)

Per Report 0127: `feat/ui-rework-v3` adds UI for `_app_deliverables` (writes generated_exports). Per Report 0102 hop 6: 7 CMS data-loaders use lazy pyarrow.

**MR770 affects the entire `[diligence]` flow** — installing without `[diligence]` avoids it (since pyarrow not installed). **Production deploys with `[diligence]` MUST upgrade pyarrow.**

### Test coverage

Per Report 0122: `tests/test_diligence_synthesis.py` exists. **Q2**: does it test malformed-Parquet input?

### Cross-link to Report 0113 ML

Report 0113: pyarrow is one of 4 `[diligence]` deps; lazy-imported in 9+ sites. This report adds CVE context. **Closes Report 0106 follow-up** (which proposed audit of pyarrow as transitive deep dep risk).

### `pyarrow>=10.0` is too permissive

Recommended pin: `pyarrow>=18.1,<19.0` (post-CVE-2024-52338 patch + ceiling per Report 0106 MR591 pattern).

### `dbt-duckdb` transitively depends on pyarrow

`dbt-duckdb` requires `pyarrow` as a transitive dep. So even without `[diligence]` declaring pyarrow explicitly, dbt-duckdb pulls it. **The pin needs to be tight wherever pyarrow lands.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR770** | **`pyarrow>=10.0` pin allows vulnerable 10.x-14.0.0 with CVE-2023-47248 (RCE via crafted Parquet)** AND code reads user-uploaded parquet files | **REMOTE CODE EXECUTION attack surface for any partner uploading malicious files.** Tighten to `pyarrow>=18.1,<19.0`. | **CRITICAL** |
| **MR771** | **NO upper bound** on pyarrow pin (cross-link Report 0106 MR591) | Future major-version regressions auto-install. Add `<X.0` ceiling. | High |
| **MR772** | **`rcm_mc_diligence/ingest/file_loader.py` is the user-input data path** — no schema validation pre-pyarrow | A crafted file with abusive metadata triggers pyarrow on first call. No "pre-flight" check (file size limit, magic-byte check). | **High** |
| **MR773** | **`dbt-duckdb` transitively depends on pyarrow** | Even with `[diligence]` un-installed, if dbt is pulled some other way (developer workflow), pyarrow lands. Pin must apply transitively. | Medium |
| **MR774** | **Trust-boundary inversion vs Report 0083 openpyxl** | openpyxl: write-only (low risk). pyarrow: READ user input (high risk). Project should explicitly classify its readers. | Medium |
| **MR775** | **No `safe_load`-equivalent for pyarrow** | Unlike `yaml.safe_load`, pyarrow has no opt-in "untrusted-input mode." All reads are full-trust. | Low |

## Dependencies

- **Incoming:** `[diligence]` extras + transitive via `dbt-duckdb`. 5 production files + 1 test fixture.
- **Outgoing:** PyPI Apache Arrow.

## Open questions / Unknowns

- **Q1.** Are Parquet/CSV files in `rcm_mc_diligence/ingest/file_loader.py` user-uploaded (HTTP POST? CLI flag?) or system-generated only?
- **Q2.** Does any test exercise malformed-Parquet input (security regression test for CVE-2023-47248)?
- **Q3.** Does CI install `[diligence]` extras and run `tests/test_diligence_synthesis.py`?
- **Q4.** Has any actual production deployment installed pyarrow at vulnerable version 10.x-14.0.0?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0137** | Schema-walk `deal_sim_inputs` (last named-but-unwalked, Report 0110 backlog). |
| **0138** | Concrete remediation: bump pyarrow pin to `>=18.1,<19.0` in pyproject.toml. |
| **0139** | Audit `dbt-core` (transitive partner of pyarrow). |
| **0140** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0136.md written.
Next iteration should: schema-walk `deal_sim_inputs` — last named-but-unwalked table (Report 0110 MR616 backlog).
