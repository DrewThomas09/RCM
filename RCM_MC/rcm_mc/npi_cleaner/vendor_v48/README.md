# Vendored: NPI_Recovery_and_Cleaner v48

These are the modules from the uploaded `NPI_Recovery_and_Cleaner_v48.zip`.
41 Python modules shipped in the archive. They are wired into the live
`/npi-cleaner` page **only where they can actually run** — see below.

## The archive is incomplete

The delivered zip references 14 internal modules it does **not** contain. Its
own code imports these, so the package cannot be imported or run as a whole:

| Missing module | What it provided | Imported by |
|---|---|---|
| `pipeline` / `run_pipeline` | the full Steps 0–8 recovery orchestrator | `__init__`, `webapp` |
| `entity` | provider-entity crosswalk + HHI | `__init__` |
| `clean_pipeline` | deterministic deep-clean repairs + ledger | `clean_orchestrator` |
| `issue_analysis` | per-issue sizing (rows / dollars / concentration) | `clean_orchestrator` |
| `impute` | value imputation | `backtest` |
| `fill` | tier fill logic | `tiers` |
| `row_consistency` | row-level consistency options | `imputation_options` |
| `common_name` | provider-name normalization | `control_total`, `universe` |
| `npi_channel` / `deficit_diagnostics` | enrollment channel + deficit diag | `npi_enrollment` |
| `rx_bridge` | NDC↔J-code bridge | `ndc_jcode` |
| `specialty_drug` | specialty-drug recovery model | `recovery_model` |
| `run_manifest` / `prettyxl` | Excel report writer + manifest | `report` |
| `bulk` | bulk enrichment | `enrich` |

The CMS **reference-data CSVs** the coding-edit screens read (`ncci_mue_seed.csv`,
the ICD-validity table, PTP pairs, etc.) were also not in the archive.

The original `__init__.py` — which eagerly imports the missing `pipeline` /
`entity` / `report` — is preserved as `npi_recovery/__init__.py.orig`. The
active `__init__.py` is a lazy package marker so the runnable modules can be
imported individually without triggering the broken chain.

## What the live page actually runs

`../vendor_adapter.py` drives the genuine package code for the modules that
import cleanly and need no missing deps or reference data:

- **`field_validators.run_field_validation`** — NPI (length + Luhn), NDC, date,
  money, state and HCPCS field rules with a repairability verdict.
- **`consistency.run_all`** — money ordering (paid ≤ allowed ≤ billed), date
  ordering, provider-role coherence, quantity vs days-supply.
- **`dedup.netting_audit`** — reversal / netting audit.

These run whenever the server has pandas (a declared base dependency). Their
real output shows up on the page under "Coding & consistency screens." A
dependency-free stdlib pass (`../engine.py`) always runs underneath so the page
works even without pandas.

30 of the 41 shipped modules import cleanly (`field_validators`, `dedup`,
`coding_edits`, `consistency`, `suggested_fixes`, `distribution_screens`,
`unit_integrity`, `concentration`, `modifier_economics`, `taxonomy_coherence`,
and 20 more). The remaining 11 are blocked by the missing modules listed above.
`coding_edits` imports fine but its screens return "reference file not found"
until the CMS seed CSVs are supplied.

## To light up the rest

Drop the 14 missing modules and the CMS reference CSVs into
`npi_recovery/`, install pandas/numpy (already base deps), and extend
`vendor_adapter.py` to call `clean_orchestrator.clean_all(...)` and, for the
network recovery path, `run_pipeline(...)`.
