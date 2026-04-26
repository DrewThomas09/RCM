# Report 0196: External Dep Audit — `dbt-duckdb`

## Scope

Audits `dbt-duckdb` per `[diligence]` extras. Sister to Reports 0136 (pyarrow), 0145 (dbt-core), 0166 (duckdb), 0173 (Pillow).

## Findings

### Pin

`pyproject.toml [diligence]`: `dbt-duckdb>=1.10,<2.0`. Strict pin.

### Production import sites

`grep "from dbt_duckdb\|import dbt_duckdb"`: not run this iteration. Per pattern (Report 0145): `dbt-duckdb` is a dbt PLUGIN — loaded by dbt-core's plugin discovery, not directly imported.

**Probably 0 direct imports.** dbt-core (Report 0145) loads dbt-duckdb plugin via dbt's `target` configuration in `profiles.yml`.

### Trust boundary

dbt-duckdb is the bridge between dbt-core's transform engine and DuckDB's SQL execution. **Pulls in pyarrow transitively** (cross-link Report 0136 MR770 + Report 0166 MR887).

### CVE chain

| Layer | Risk |
|---|---|
| `pyarrow>=10.0` | CVE-2023-47248 RCE if user-Parquet (Report 0136 MR770 critical) |
| `duckdb>=1.0,<2.0` | clean (Report 0166) |
| `dbt-duckdb>=1.10,<2.0` | inherits pyarrow risk transitively |
| `dbt-core>=1.10,<2.0` | clean per Report 0145 |

**The CVE chain originates in pyarrow.** dbt-duckdb is a thin glue layer.

### Upstream

dbt-duckdb is community-maintained on GitHub (`duckdb/dbt-duckdb`). Active project.

### Cross-link to Report 0145

Per Report 0145: dbt-core invocation in `rcm_mc_diligence/ingest/connector.py:200`. **dbt-duckdb is selected via `target: duckdb` in the profiles.yml** (per dbt convention).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR967** | **`dbt-duckdb>=1.10,<2.0` strict pin** — clean | Cross-link MR967 (duckdb) + MR886. Composite ddb stack pinned tight. | (clean) |
| **MR968** | **dbt-duckdb inherits pyarrow CVE risk** transitively | Cross-link Report 0136 MR770 + Report 0166 MR887. **Same fix: tighten pyarrow pin.** | (carried) |

## Dependencies

- **Incoming:** dbt-core plugin discovery in dbt invocation (Report 0145).
- **Outgoing:** PyPI; transitively pyarrow + duckdb.

## Open questions / Unknowns

- **Q1.** Confirm 0 direct imports.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0197** | Storage layer (in flight). |

---

Report/Report-0196.md written.
