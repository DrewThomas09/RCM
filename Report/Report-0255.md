# Report 0255: Closure — `RCM_MM/` and `vendor/ChartisDrewIntel/` inspections

## Scope

Closes two carried-forward HIGH-priority unmapped areas: `RCM_MM/` (Report 0250 MR1030) and `vendor/ChartisDrewIntel/` (Report 0250 MR1031, Report 0254 Q3 dependent on similar inspections). Sister to Reports 0250 (orphan files), 0251 (pyproject deps), 0136 (pyarrow + diligence stack).

## Findings

### `RCM_MM/` is an empty stub — not vestigial WIP code

```
RCM_MM/
└── rcm_mc/
    └── data_public/   (empty)
```

- Total size on disk: **0 bytes**.
- File count: **0** (only directory entries).
- Git-tracked files under `RCM_MM/`: **0**.

This is the residue of a `mkdir -p RCM_MM/rcm_mc/data_public` somebody ran (likely as scratch space or aborted refactor setup) and never cleaned up. There is no code, no README, no `__init__.py`, nothing to inspect. The audit memory note `project_rcm_mc_layout.md` flagged the doubled directory; closure here downgrades that flag from "possibly vestigial parallel package" to "empty scratch dir, safe to ignore or `rmdir`".

### `vendor/ChartisDrewIntel/` is the Tuva Project (Apache 2.0)

- Top-level layout: `analyses/`, `dbt_project.yml`, `docs/`, `integration_tests/`, `license`, `macros/`, `models/`, `packages.yml`, `scripts/`, `seeds/`, `snapshots/`, `tests/`, `README.md`, `AGENTS.md`.
- README opening line: "[Apache License 2.0](https://opensource.org/licenses/Apache-2.0)" + dbt 1.10+ banner.
- README narrative (lines 5-11): "The Tuva Project is a dbt package for transforming raw healthcare data into analytics-ready data."
- Components: Input Layer, Claims Preprocessing, Core Data Model, Data Marts, Terminology and Value Sets.
- Docs site: `https://www.thetuvaproject.com/`.

This is a vendored copy of the open-source [Tuva Project](https://github.com/tuva-health/tuva), the upstream healthcare-claims dbt package consumed by `rcm_mc_diligence/` via `dbt-core` + `dbt-duckdb` (cross-link Report 0136 — pyarrow imports inside `rcm_mc_diligence/ingest/file_loader.py` are part of this same dbt-driven pipeline).

The 6 `profiles.yml` fixtures under `vendor/ChartisDrewIntel/integration_tests/profiles/` (databricks/bigquery/snowflake/redshift/duckdb/fabric) are CI templates with `env_var()` placeholders only — already verified in iteration 6 (commit `b31aecd`) to contain no real secrets.

**Not proprietary, not internal — pure third-party Apache 2.0 vendor.**

### Implications for MR1030 + MR1031 closure

Both flags downgrade from "HIGH/never inspected" to "(closed/no-action)":

| Flag | New status | Reason |
|---|---|---|
| MR1030 (`RCM_MM/` doubled-dir) | (closed) | Empty stub, 0 tracked files, 0 bytes. |
| MR1031 (`vendor/ChartisDrewIntel/`) | (closed) | Apache 2.0 Tuva Project (claims-transformation dbt package); not proprietary. License compliance: Apache 2.0 is permissive — compatible with the "Proprietary" project license declared in `pyproject.toml:11` provided the LICENSE file is preserved (it is, at `vendor/ChartisDrewIntel/license`). |

### Side observation: `RCM_MM/` should be removed or gitignored

Although nothing is tracked, the empty directory exists on disk. If a contributor accidentally runs `git add RCM_MM/.placeholder` or similar, the stale path leaks into the tree. **Suggested follow-up (low):** add `RCM_MM/` to `.gitignore` or `rmdir RCM_MM/rcm_mc/data_public RCM_MM/rcm_mc RCM_MM/`. Out of scope for this iteration's HIGH-fix burndown.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1056** | **License-attribution check on Tuva Project vendor copy** | Apache 2.0 requires preserving the LICENSE file + NOTICE if any. `vendor/ChartisDrewIntel/license` exists; verify NOTICE is present too. Cross-link `pyproject.toml:11` "Proprietary". | Low |
| **MR1030** | (RETRACTED — closed) `RCM_MM/` is an empty 0-byte scratch dir, not vestigial code | (closure) | (closed) |
| **MR1031** | (RETRACTED — closed) `vendor/ChartisDrewIntel/` is Apache 2.0 Tuva Project, not proprietary | (closure) | (closed) |

## Dependencies

- **Incoming:** `rcm_mc_diligence/` consumes Tuva Project via `dbt-core` + `dbt-duckdb` (per Report 0136 + pyproject `[diligence]` extras).
- **Outgoing:** `RCM_MM/` has none (empty); `vendor/ChartisDrewIntel/` depends on `dbt-core>=1.10`, `dbt-duckdb>=1.10`, `pyarrow>=18.1,<19.0` (post-iteration-3 pin).

## Open questions / Unknowns

- **Q1.** Does Tuva ship a NOTICE file (Apache 2.0 attribution requirement)?
- **Q2.** Should `RCM_MM/` be deleted outright, gitignored, or left as harmless empty dirs?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| (low) | Verify Tuva NOTICE file or note absence in repo LICENSE/README. |
| (low) | Decide `RCM_MM/` fate — delete vs. gitignore vs. leave. |

---

Report/Report-0255.md written.
