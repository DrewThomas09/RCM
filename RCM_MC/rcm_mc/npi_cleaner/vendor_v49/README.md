# Vendored: NPI_Recovery_and_Cleaner v49 (complete)

This is the **complete** v49 program — 95 Python modules, the CMS reference
tables it needs, and the bundled examples. It supersedes the earlier v48 upload,
which was missing 14 of its own internal modules (`pipeline`, `entity`,
`clean_pipeline`, `issue_analysis`, `impute`, the Excel report writer, …) and
all the reference CSVs, and therefore could not import or run.

```
vendor_v49/
├── npi_recovery/            all 95 modules + reference/ CMS tables
│   ├── reference/           ncci_mue_seed.csv, icd10cm_validity_seed.csv,
│   │                        ncci_ptp_sample.csv, nppes_deactivated_seed.csv,
│   │                        jw_jz_single_dose_seed.csv, sad_exclusion_full.csv, …
│   ├── __init__.py          lazy marker (see below)
│   └── __init__.py.full     the package's original eager __init__
├── examples/                sample_claims.xlsx + three example outputs
└── scripts/                 recover_npis.py, make_sample.py, selftest.py
```

Narrative/changelog `.md` files from the archive are intentionally not vendored
— only the program and the data it needs.

## What the `/npi-cleaner` page runs (offline, real v49 code)

`../vendor_adapter.py` drives the genuine deterministic engine:

```
schema.standardize_any(df)          # auto-detect + canonicalize columns
clean_orchestrator.clean_all(std)   # the real v45+ "fix and analyze" pass
```

`clean_all` returns, and the page surfaces:

- **repair_ledger** — safe deterministic repairs applied to a cleaned copy
  (originals preserved).
- **screens** — NCCI **MUE**, **PTP** pairs, **ICD-10/DOS** validity, **age–sex**,
  **JW/JZ** single-dose wastage, **deactivated-NPI**, and the cross-field
  **consistency** checks (money ordering, date ordering, provider-role
  coherence, units vs days-supply) — all against the vendored reference tables.
- **issue_summary** — each issue sized: rows, % rows, **dollar exposure**, % $,
  drug/provider HHI, and a **systematic-vs-random** verdict.
- **suggestions** — a row-level corrections companion (current → suggested,
  fix rule, confidence, safe-to-auto-apply, provenance, $), offered as a CSV
  download and an .xlsx sheet.

On the sample (`examples/sample_claims.xlsx`, 1,200 rows) this runs in ~1.5s
and reports 20 deterministic repairs and an `$1.8M` JW/JZ single-dose wastage
pattern flagged "systematic."

## The lazy `__init__`

The original `__init__.py` (kept as `__init__.py.full`) eagerly imports
`.pipeline` → `.clients` → `requests`. `requests` is not a base RCM dependency,
so the active `__init__.py` is a lazy marker: the offline engine
(`schema` + `clean_orchestrator`) imports with no third-party deps beyond
pandas/numpy, and never touches the network.

## Full networked recovery pipeline (batch/CLI)

The complete Steps 0–8 recovery pipeline — live NPPES enrichment, CMS billers,
Open Payments, 340B, entity resolution, statistical fill/imputation, calibrated
capture, and the multi-tab Excel report — is here too:

```python
# needs: pip install requests   (network access to NPPES + data.cms.gov)
from rcm_mc.npi_cleaner.vendor_v49.npi_recovery.pipeline import run_pipeline
from rcm_mc.npi_cleaner.vendor_v49.npi_recovery import write_report
res = run_pipeline("claims.xlsx", progress=print)   # minutes; constructs live clients
write_report(res, "recovered.xlsx")
```

On the page it is exposed as the opt-in **"Deep recovery"** checkbox, run by
`../deep_pipeline.py` in the background job thread under a wall-clock timeout:
`candidates.build_candidate_pools` warms the CMS data catalog over HTTP no
matter which sub-steps are enabled, so without outbound access the run would
otherwise hang on urllib3 retry-backoff — the watchdog fails the job with a
clear message instead, leaving the fast deterministic results untouched. On
success it offers the multi-tab `write_report` workbook as a download. To run
the same pipeline as a scheduled/CLI job against the app's shared connection,
point its `clients` at `data_public.nppes_api_client` / `cms_api_client`.
