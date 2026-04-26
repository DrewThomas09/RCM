# Report 0203: Version Drift — Final Sweep + Cumulative Pin Discipline

## Scope

Cumulative comprehensive cross-check of all dep pins (cross-link Reports 0023, 0046, 0053, 0076, 0083, 0086, 0101, 0106, 0113, 0136, 0143, 0166, 0173, 0196). Sister to all version-drift reports.

## Findings

### Pin-tightness scoreboard (cumulative)

| Pin pattern | Count |
|---|---|
| Strict `>=X,<Y` | numpy, pandas, pyyaml, matplotlib, openpyxl, duckdb, dbt-core, dbt-duckdb (8 packages) |
| Floor only `>=X` | python-pptx, plotly, fastapi, uvicorn, pyarrow, scipy, pytest, pytest-cov, ruff, mypy (10 packages) |
| Unpinned (transitive only) | pydantic, Pillow (2 packages) |

**Per Report 0143 + 0173: 12 of 20 deps loose-pin or unpinned.** **60%.**

### Critical-CVE pin-class mismatch

Per Report 0136 MR770 critical: `pyarrow>=10.0` allows vulnerable 10.x-14.0.0 with RCE.

Per Report 0173: Pillow (transitive) has CVE history; not pinned.

**The deps with WORST CVE history are LEAST tightly pinned.**

### Cross-correction history (cumulative)

| Report | Pin/usage finding |
|---|---|
| 0086 | scripts: 1 → 4 actual |
| 0101 | duckdb in `[diligence]` (now confirmed clean) |
| 0113 | scipy USED (retracted 0101 MR550); fastapi USED (retracted 0101 MR549); plotly DEAD |
| 0136 | pyarrow CVE risk (MR770 critical) |
| 0143 | pytest-cov never run in CI (dead-in-CI MR797) |
| 0166 | duckdb pin clean |
| 0173 | Pillow transitive risk (MR908+909) |
| 0196 | dbt-duckdb pin clean (inherits pyarrow risk) |

### Aggregate findings

**Deps used**: 12 (numpy, pandas, pyyaml, matplotlib, openpyxl, python-pptx, fastapi, scipy, duckdb, dbt-core, dbt-duckdb, pyarrow + Pillow transitive).

**Deps DEAD**: 1 confirmed (`plotly`) + 1 partly-dead (`pytest-cov` not run in CI) = ~1.5.

**Deps with security risk**: 2 (pyarrow + Pillow).

### Recommended remediation list (concrete)

1. `pyarrow>=10.0` → `pyarrow>=18.1,<19.0` (Report 0136 MR770 critical RCE)
2. Add `Pillow>=10.3,<11.0` explicit pin (Report 0173)
3. Add `pydantic>=2.0` explicit pin (Report 0113 MR632)
4. Remove `plotly>=5.0` from `[interactive]` (Report 0113 MR633 dead)
5. Either run `pytest-cov` in CI OR remove from `[dev]` (Report 0143 MR797)
6. Tighten 7+ floor-only pins to add upper-bound (Report 0106 MR591)

**6 concrete remediation items.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR978** | **60% of deps have loose pins (12 of 20)** | Cross-link Reports 0106 MR591 + 0113 MR636 + this. | High (carried) |
| **MR979** | **Worst-CVE deps least pinned**: pyarrow (RCE risk) is floor-only; Pillow (CVE-prone) is transitive | **Inverse-of-prudent pin discipline.** | (carried) |
| **MR980** | **6 concrete pin-remediation items** identified across audit window | Actionable list for a 1-2 hour security PR. | (advisory) |

## Dependencies

- **Incoming:** every install path.
- **Outgoing:** PyPI.

## Open questions / Unknowns

None new — comprehensive scoreboard.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0204** | Cross-cutting (in flight). |

---

Report/Report-0203.md written.
