# Report 0130: Orphan Files — Top-Level `RCM_MC/` + `vendor/` Sweep

## Scope

Sweeps top-level entries in `RCM_MC/` outside the `rcm_mc/` package, plus `vendor/` at repo root. Sister to Reports 0010, 0040, 0070, 0100. Closes a 130-iteration blind spot.

## Findings

### `RCM_MC/` top-level inventory (untouched by audit until now)

| Entry | Type | Size | Status before this report |
|---|---|---|---|
| `seekingchartis.py` | Python script | 84 lines, 3.2 KB | **never reported** |
| `demo.py` | Python script | 9.3 KB | mentioned in CLAUDE.md, never audited |
| `scripts/run_all.sh` | bash | 230 lines | **never reported** |
| `scripts/run_everything.sh` | bash | 175 lines | **never reported** |
| `tools/build_dep_graph.py` | Python tool | 270 lines | **never reported** |
| `data_demo/` (dir) | data fixtures | — | **never reported** |
| `scenarios/` (top-level — NOT same as `rcm_mc/scenarios/` subpackage) | YAML configs | 2 files + README | **never reported** |
| `readME/` (oddly capitalized) | markdown docs | 27 files | **never reported** |
| `configs/` | YAML | partial (Report 0011: actual.yaml only) | partial |
| `CHANGELOG.md`, `README.md`, `CLAUDE.md` | docs | covered indirectly | partial |
| `pyproject.toml` | config | covered (Reports 0003, 0086, 0101) | ✓ |
| `.dockerignore`, `.gitignore`, `.pre-commit-config.yaml` | configs | partial | partial |

### HIGH-PRIORITY DISCOVERIES

**6+ top-level entries never reported** in 129 prior iterations:
1. `seekingchartis.py` — standalone launcher script
2. `scripts/` (2 bash files)
3. `tools/` (1 Python tool)
4. `data_demo/`
5. `scenarios/` (top-level, distinct from subpackage)
6. `readME/` (27 markdown files)

### `seekingchartis.py` — orphan-by-import, not orphan-by-purpose

```python
#!/usr/bin/env python3
"""SeekingChartis — one command to launch.

Usage:
    python seekingchartis.py
    python seekingchartis.py --port 9090
    python seekingchartis.py --db my_portfolio.db --no-browser

Starts the server and opens the browser automatically.
"""
```

**Standalone launcher script.** 0 importers in `rcm_mc/`. Used via `python seekingchartis.py` directly.

**Critical**: This is a **5th entry-point** to the project — beyond:
- 4 console scripts in pyproject (per Report 0086): `rcm-mc`, `rcm-intake` (broken — Report 0105 MR588), `rcm-lookup`, `rcm-mc-diligence`
- `python -m rcm_mc` (Report 0048)
- `uvicorn rcm_mc.api:app` (Report 0113)
- **`python seekingchartis.py`** ← this report
- **`python demo.py`** ← per CLAUDE.md "demo.py" — see below

**Total entry surfaces NOW: 7+** (Reports 0086 + 0101 + 0113 + 0130).

### `demo.py` (per CLAUDE.md "Demo (seeds, starts server, opens browser)")

CLAUDE.md `Running` section line 156:
```bash
.venv/bin/python demo.py
```

**Documented as the canonical demo entry-point.** Yet never audited body-side. 9.3 KB of Python (likely 200-300 lines).

### `scripts/run_all.sh` + `run_everything.sh` (405 total lines)

Bash scripts, **never audited.** Both at top-level `RCM_MC/scripts/`. Likely test/release/demo orchestration. Per `grep`: referenced in CHANGELOG.md, README.md, CLAUDE.md, `tools/README.md`, `docs/MD_DEMO_SCRIPT.md`.

### `tools/build_dep_graph.py` (270 lines)

Per name: a developer tool that builds a dependency graph (likely the source of the renderer that Report 0097 saw deleted on `feature/pe-intelligence`). Cross-link Report 0097 (which mentioned `print_dep_graph` CLI tool deleted on the stale branch).

### `scenarios/` top-level (separate from `rcm_mc/scenarios/`)

```
RCM_MC/scenarios/
├── README.md
├── commercial_tightening.yaml
└── management_plan_example.yaml
```

**Distinct from `rcm_mc/scenarios/` subpackage** (per Report 0091 Phase 2 list). These are **example YAML scenarios** for users to load. Not Python imports.

### `readME/` (27 markdown files, oddly capitalized)

Files named `00_Walkthrough_Tutorial.md`, `01_API_Reference.md`, `02_Configuration_and_Operations.md`, ... `09_Benchmark_Sources.md`, ... 27 files total.

**Major user-facing documentation directory.** Numeric prefix suggests a tutorial/reference sequence. **Never audited.**

### `data_demo/` directory

```
RCM_MC/data_demo/
├── README.md
└── target_pkg/
```

**Sample data package for demos.** Per pattern, similar to `rcm_mc_diligence/fixtures/` (Report 0122).

### `vendor/` — at repo ROOT (not RCM_MC/), 102 MB

| Subdir | Purpose | Status |
|---|---|---|
| `vendor/ChartisDrewIntel/` | partner integration code (per Report 0116 — has own .github/workflows/) | **never deeply mapped** |
| `vendor/cms_medicare/` | 102 MB of CMS medicare plots + data; deleted on `feature/pe-intelligence` per Report 0097 | **never reported** |
| `vendor/README.md` | (not extracted this iteration) | unread |

**`vendor/` is 102 MB.** Per Report 0097: `feature/pe-intelligence` branch deleted ~2,276 of these files (as part of moving them out). On origin/main they still exist. **Massive footprint** but mostly NOT imported from Python (data files + plots).

### Filesystem cruft sweep

`find . -name ".DS_Store" -o -name "*.orig" -o -name "*.bak" -o -name "*.swp"`:

**Empty result.** No filesystem debris. Cross-link Report 0100: clean discipline.

### Cross-link to Report 0091 backlog

Per Report 0091:
- "still unmapped #11" listed `cli.py` + `diligence/` + `data_public/` + many subpackages
- Did NOT list top-level RCM_MC/ scripts or readME/ or scenarios/
- **Backlog updated**: add 6+ top-level entries to the "still unmapped" list

### Genuine orphans (zero references anywhere)

`grep -rln "data_demo\|target_pkg" RCM_MC/ --include="*.py"`: not run this iteration. **`data_demo/` may be an actual orphan.** Q1 below.

### Tests for top-level scripts

| Script | Tests? |
|---|---|
| `seekingchartis.py` | YES — `tests/test_seekingchartis_pages.py` |
| `demo.py` | unverified |
| `scripts/run_all.sh` | unverified |
| `tools/build_dep_graph.py` | unverified |

### Comparison to Report 0100 finding

Report 0100 swept the 13 unmapped subpackages in `rcm_mc/` and found **zero filesystem cruft.** This report extends that to the top-level + vendor/: **also zero cruft.** Strong project discipline.

But: this report finds **6+ unmapped top-level entries** that Report 0100 / 0091 missed. Backlog grows.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR738** | **6+ unmapped top-level entries** in `RCM_MC/` (seekingchartis.py, demo.py, scripts/, tools/, scenarios/ top-level, readME/, data_demo/) | Most are entry-points or user-facing docs that `pyproject.toml` doesn't formally declare. A developer cleaning up may accidentally delete `seekingchartis.py` thinking it's orphan. | **High** |
| **MR739** | **Total entry surfaces: 7+** (4 console scripts + python -m + uvicorn + seekingchartis.py + demo.py) | Cross-link Report 0086 (claimed 4) + 0113 (added 1 ASGI). NOW 7+. **CLAUDE.md should enumerate them all.** | Medium |
| **MR740** | **`vendor/` at repo root is 102 MB** | Per Report 0097: deleted on `feature/pe-intelligence` branch (which is now stale). On origin/main, vendored data persists. Consider whether vendor/ should be `.gitignore`d / released as a separate artifact. | Medium |
| **MR741** | **`readME/` directory has odd capitalization** (`R` then `e`) | Inconsistent with `README.md` (the file). On case-insensitive filesystems (Mac default) `readME/` and `README.md` may collide silently. | Medium |
| **MR742** | **`scenarios/` (top-level) and `rcm_mc/scenarios/` (subpackage) share a name** | Different content but identical name. A developer searching for "scenarios" finds both. Documentation must distinguish. | Low |
| **MR743** | **`tools/build_dep_graph.py` (270L) was DELETED on `feature/pe-intelligence`** per Report 0097 | If main is ever reset to that branch (which Report 0120 MR688 critical concerns), this tool is wiped. Currently safe. | (carried) |

## Dependencies

- **Incoming:** developer/CI invocation of top-level scripts; `vendor/` consumption by mapping/data flow.
- **Outgoing:** none new from this iteration.

## Open questions / Unknowns

- **Q1.** Is `data_demo/target_pkg/` actually used by anything, or true orphan?
- **Q2.** What does `tools/build_dep_graph.py` produce and is its output committed/used?
- **Q3.** Should `vendor/cms_medicare/` (102 MB) be repo-or-LFS or released-artifact?
- **Q4.** Body of `demo.py` and `seekingchartis.py` — what flags do they accept that pyproject doesn't?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0131** | Read `demo.py` (closes Q4 partial) — CLAUDE.md-documented entry-point, never audited. |
| **0132** | Read `seekingchartis.py` body (closes Q4 — 84 lines, fast). |
| **0133** | Read `tools/build_dep_graph.py` (closes Q2). |
| **0134** | Schema-walk `generated_exports` (Report 0127 MR724 — STILL pre-merge requirement, deferred 4+ iterations). |

---

Report/Report-0130.md written.
Next iteration should: read `demo.py` (CLAUDE.md-documented entry-point that has been unmapped for 130 iterations).
