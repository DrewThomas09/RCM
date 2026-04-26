# Report 0166: External Dep Audit — `duckdb`

## Scope

Audits `duckdb` external dep per `[diligence]` extras. Sister to Reports 0136 (pyarrow), 0145 (dbt-core integration), 0143 ([dev] extras).

## Findings

### Pin

`pyproject.toml [diligence]` (Report 0101): `duckdb>=1.0,<2.0`. **Strict pin** with upper bound — cleaner than pyarrow (Report 0136 MR770).

### Production import sites

Per Report 0113 lazy-import sweep:
- `rcm_mc_diligence/ingest/warehouse.py:181` — `import duckdb`
- `rcm_mc/diligence/ingest/tuva_bridge.py:183` — `import duckdb`

**2 sites, both lazy** (inside function bodies). Compliant with `[diligence]`-extras-only design.

### Trust boundary

DuckDB executes SQL against in-memory or file-based databases. Per Report 0145 + 0122: dbt-duckdb pipeline → partner-supplied SQL models → DuckDB → output Parquet.

**Per Report 0136 MR770**: pyarrow CVE applies because user-uploaded Parquet enters pyarrow first. **DuckDB itself**: receives data after pyarrow reads it. **Defense-in-depth**: both layers are vulnerable to malformed input.

### CVE history

DuckDB 1.0+ is recent (released 2024). Limited CVE history because of recency:
- No major CVEs at version 1.0+
- 0.x had occasional issues (pre-1.0 was unstable)
- Project pin `>=1.0` correctly avoids 0.x

**Upstream is well-maintained** (DuckDB Labs).

### Dependency: pyarrow transitive

DuckDB depends on pyarrow for Parquet I/O. Per Report 0136 MR770 + MR773: pyarrow CVE-2023-47248 affects 10.x-14.0.0; project pin `pyarrow>=10.0` allows vulnerable versions.

**Cross-link MR773**: this report re-affirms — duckdb + pyarrow = composite RCE risk.

### dbt-duckdb shim

Per Report 0101 + 0145: dbt-duckdb is the bridge. dbt-core invokes it via plugin discovery; duckdb is the underlying engine.

### Production usage

Per `tuva_bridge.py:183`: DuckDB is used for Tuva-Health.org integration (per Report 0145). Likely runs SQL transforms on partner clinical data.

### `[diligence]` extras only

Without `pip install -e .[diligence]`, duckdb is NOT installed. **Optional dep correctly gated.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR886** | **`duckdb>=1.0,<2.0` pin is strict** — better than `pyarrow>=10.0` (Report 0136 MR770) | Cleaner pin discipline. | (clean) |
| **MR887** | **DuckDB-via-Parquet path inherits pyarrow CVE** | Cross-link Report 0136 MR770 + MR773. duckdb is downstream of pyarrow's Parquet reader. **Mitigated by upgrading pyarrow.** | (carried — same as MR770) |
| **MR888** | **Only 2 lazy-import sites for duckdb** | Tight surface — easy to refactor if needed. | (clean) |

## Dependencies

- **Incoming:** rcm_mc_diligence/ingest/warehouse.py + rcm_mc/diligence/ingest/tuva_bridge.py.
- **Outgoing:** PyPI duckdb (depends on pyarrow transitively).

## Open questions / Unknowns

- **Q1.** Does duckdb expose `read_parquet` to user input directly, or is data pre-validated by pyarrow first?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0167** | Storage layer (in flight). |

---

Report/Report-0166.md written.
