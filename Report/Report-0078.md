# Report 0078: Entry Point — `rcm-mc-diligence` (broken)

## Scope

The 4th declared console-script per pyproject.toml:72 (Report 0003): `rcm-mc-diligence = "rcm_mc_diligence.cli:main"`.

## Findings

### Status

Per Report 0003: this entry-point is declared but its `[diligence]` extras + `rcm_mc_diligence` package are **REMOVED on `feature/deals-corpus`** + `feature/workbench-corpus-polish` per Reports 0007 + 0037.

On origin/main: the package + entry-point both still exist.

### Stage 0 — invocation

```
$ rcm-mc-diligence ingest --connector seekingchartis ...
```

Per `rcm_mc_diligence/cli.py:240` (existence verified Report 0003).

### Stage 1 — Console-script wire-up

`pyproject.toml:72` `rcm-mc-diligence = "rcm_mc_diligence.cli:main"`. Setuptools-generated.

### Stage 2 — `rcm_mc_diligence/cli.py:main` (line 240 per Report 0003)

Argparse → ingest subcommand → dispatches into `rcm_mc_diligence.ingest` package.

### Stage 3 — DBT model invocation

Per Report 0003 / 0023, `rcm_mc_diligence/connectors/seekingchartis/` ships dbt_project.yml + models/. The CLI likely invokes `dbt-core` to run the DBT models against a duckdb backend.

### Stage 4 — Output

Persists to a duckdb database. **Separate from rcm-mc's SQLite** — different storage layer entirely.

### Trace

```
$ rcm-mc-diligence ingest --connector seekingchartis ...
       │
       ▼
   pyproject.toml:72 → rcm_mc_diligence.cli:main
       ▼
   rcm_mc_diligence/cli.py:240 main(argv)
       ▼
   argparse → ingest subcommand handler
       ▼
   ingest.* modules (data quality, fixtures, connectors)
       ▼
   dbt-core via dbt-duckdb adapter
       ▼
   duckdb file (separate from portfolio.db)
```

### Critical gap (cross-link)

- **Report 0023 MR183**: `rcm_mc/diligence/ingest/` (different from `rcm_mc_diligence/`!) imports pyarrow which is in [diligence] extras only. **Confusing dual naming.**
- **Reports 0007 + 0037**: feature branches REMOVE the rcm_mc_diligence package entirely. **If those branches merge, this entry point goes away.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR459** | **Two ahead-of-main branches REMOVE rcm-mc-diligence entry point** | If feature/deals-corpus or workbench-corpus-polish merges, this CLI dies. Tooling that depends on it (cron jobs, ingestion scripts) breaks silently. | **Critical** |
| **MR460** | **`rcm_mc/diligence/` (in main) ≠ `rcm_mc_diligence/` (separate package)** | Naming collision. Auditor confusion + future contributor confusion. **Recommend rename.** | **High** |
| **MR461** | **Production Dockerfile installs only core extras (Report 0033)** | This entry-point requires `[diligence]` extras (duckdb + dbt-*). **In production, `rcm-mc-diligence` would fail at import time** with ModuleNotFoundError. **The CLI is effectively dev-only** despite being declared. | **High** |

## Dependencies

- **Incoming:** operator running `rcm-mc-diligence` from CLI.
- **Outgoing:** dbt-core, dbt-duckdb, duckdb, pyarrow (all [diligence] extras).

## Open questions / Unknowns

- **Q1.** Is `rcm-mc-diligence` actually used by anyone?
- **Q2.** Is the `rcm_mc/diligence/ingest/` (in main) a re-implementation of what `rcm_mc_diligence/ingest/` (separate package) does?

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0079** | Env vars (already requested). |

---

Report/Report-0078.md written.

