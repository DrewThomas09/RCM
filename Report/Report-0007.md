# Report 0007: Merge-Risk Scan — `feature/workbench-corpus-polish`

## Scope

This report covers a **merge-risk scan of `origin/feature/workbench-corpus-polish`** against `origin/main`. The branch was selected because Report 0006 flagged it as the **largest live branch** (114 files differ, 21 commits ahead, branched 2026-04-18 15:17 from `8c39d2c`). It also touches both `rcm_mc/` and `tests/` — the highest-stakes territory. The branch's last commit is `79c4887` ("feat(ui): editorial reskin + fix 14 pre-existing test failures") on 2026-04-19.

The scan focuses on: total diff scale, schema changes, breaking API/signature changes, dependency version bumps, deleted public functions, structural moves.

Prior reports reviewed before writing: 0001-0006.

## Findings

### Total diff scale — catastrophically divergent

| Metric | Value |
|---|---:|
| Files changed | **3,336** |
| Insertions | +19,476 |
| Deletions | **−376,120** |
| Files added (A) | 111 |
| Files deleted (D) | **3,064** |
| Files renamed (R) | 5 |

This branch is **massively divergent** from main. The 3,064-file deletion count is extraordinary — far above the "21 commits / 114 files-diff" headline I reported in 0006. The reason: `git diff --stat` collapses entries; the `--name-status` output shows the true scale. Most of the 376k-line deletion is what main has *added* since the branch point that workbench-corpus-polish does not have.

**Interpretation:** workbench-corpus-polish was authored on top of an older, smaller version of the repo. Main has continued for 243 commits and added thousands of files (vendor trees, doc reorganization, test fixtures) that the branch is unaware of. A naive merge would either (a) drop those 3,000+ files from main if branches conflict in the branch's favor, or (b) preserve them but force a manual reconciliation across thousands of paths.

### File-extension breakdown of the diff

| Ext | Count | Likely owner |
|---|---:|---|
| `.sql` | 1,284 | `vendor/ChartisDrewIntel/` DBT models + `rcm_mc_diligence/connectors/` (both deleted on this branch) |
| `.py` | 721 | Python source — primary code surface |
| `.md` | 423 | Doc reorganization (added 21 README_LAYER_* docs; deleted 25+ scratch docs) |
| `.png` | 355 | `vendor/cms_medicare/` state-service maps (deleted on branch) |
| `.csv` | 178 | Test fixtures + sample outputs |
| `.yml` | 98 | DBT model definitions + a few CI workflow files |
| `.jpg` | 85 | Demo / screenshot artifacts |
| `.json` | 36 | Various data files |
| `.html` | 35 | Static HTML (likely sample outputs) |
| `.js` | 21 | UI scripts |

### Top 5 single-file deltas

| File | Net change | Action | Significance |
|---|---:|---|---|
| `vendor/ChartisDrewIntel/docs/package-lock.json` | −19,068 lines | deleted | Vendor cleanup. Main has it; branch doesn't. |
| `vendor/ChartisDrewIntel/docs/src/data/dataQualityTests.json` | −9,902 | deleted | Same. |
| `vendor/cms_medicare/cms_output.txt` | −5,410 | deleted | Same. |
| **`RCM_MC/rcm_mc/server.py`** | **+174 / −2,296 (net −2,122)** | modified | **Primary risk surface — branch removes ~2k lines from server.py vs main.** Sample diff shows it removes Heroku/k8s probe support (`/healthz` route alias) and the `RCM_MC_DB` env-var fallback. |
| `RCM_MC/rcm_mc/ui/dashboard_page.py` | −2,591 / +0 | **deleted entirely** | Whole UI page removed. At least 10 module-level functions disappear: `_freshness_bucket`, `_dot`, `_render_analyses_section`, `_workflow_badge_counts`, `_badge`, `_since_yesterday_events`, `_all_insights`, `_chain_concentration_insights`, `_covenant_insights`, `_health_distribution_insights`. |

### Dependency / packaging changes — `pyproject.toml`

The branch makes **structural changes to `RCM_MC/pyproject.toml`**:

1. **Removes the `diligence` extras** (deletes `duckdb>=1.0,<2.0`, `dbt-core>=1.10,<2.0`, `dbt-duckdb>=1.10,<2.0`, `pyarrow>=10.0`).
2. **Removes the `rcm-mc-diligence` console script** (`rcm-mc-diligence = "rcm_mc_diligence.cli:main"`).
3. **Narrows `[tool.setuptools.packages.find]` from `["rcm_mc*", "rcm_mc_diligence*"]` to `["rcm_mc*"]`** — drops the second package.
4. **Removes the `rcm_mc_diligence` package-data declarations** (5 globs covering the SeekingChartis DBT connector).

**This branch removes the entire `rcm_mc_diligence/` package from the build.** Main currently includes it (Report 0003). Merging workbench-corpus-polish would either:
- Delete `rcm_mc_diligence/` and break the `rcm-mc-diligence` CLI, OR
- Be conflict-resolved in main's favor, in which case the branch's intent is silently ignored.

Pyproject changes do **not** include numpy/pandas version bumps. No upstream version drift in core deps.

### Renamed / moved files (5)

| From | To | Significance |
|---|---|---|
| `.github/workflows/release.yml` | `RCM_MC/.github/workflows/release.yml` | Moves CI workflow into the package directory. **Conflicts with main, which keeps `.github/` at repo root.** |
| `RCM_MC/docs/cycle_summaries/FEATURE_DEALS_CORPUS.md` | `RCM_MC/FEATURE_DEALS_CORPUS.md` | Promotes branch summary to package root. |
| `RCM_MC/rcm_mc/ui/_chartis_kit_legacy.py` | `RCM_MC/rcm_mc/ui/_chartis_kit_dark.py` | UI kit rename. Likely tied to the "editorial reskin." |
| `RCM_MC/scripts/run_all.sh` | `RCM_MC/run_all.sh` | Promotes script. |
| `RCM_MC/scripts/run_everything.sh` | `RCM_MC/run_everything.sh` | Same. Resolves Report 0002 Q3 partially: this branch elevates both run-scripts and removes the `scripts/` indirection. |

### Schema changes

- **No SQLite migrations** detected. No `migrations/`, no `alembic.ini`, no `*.sql` files outside vendor/dbt subtrees. Schema-on-disk is implicit (CREATE TABLE IF NOT EXISTS in `portfolio/store.py` per CLAUDE.md). Verified: `git diff --name-only` for `*.sql` only returns DBT models, not application schema.
- **Dataclass field changes** in `analysis/packet.py` not yet inspected. Future iteration should diff that file specifically.

### Workflow / CI changes

The branch **deletes 3 workflows at repo root** (`.github/workflows/ci.yml`, `deploy.yml`, `regression-sweep.yml`) and adds 1 new one inside the package (`RCM_MC/.github/workflows/ci.yml`, 39 lines). Main retains all 4 root-level workflows (Report 0001). The branch wants to consolidate CI to a single file inside `RCM_MC/`.

### Server.py-specific changes (sample diff)

The first ~30 lines of the `server.py` diff reveal:

- **Line 91-94:** `db_path` declaration — branch removes the Heroku-aware fallback (`os.environ.get("RCM_MC_DB") or os.path.expanduser(...)`) and reverts to a plain `os.path.expanduser("~/.rcm_mc/portfolio.db")`. Branches that ship to Heroku/Docker will break.
- **Line 1700:** Removes `/healthz` from the `pure_path in ("/health", "/healthz", "/login")` allowlist. Kubernetes liveness probes will 401 unless main reinstates this.

Net: this branch **rolls back deploy-target support** that main currently has.

### Tests

- The branch deletes `RCM_MC/tests/fixtures/kpi_truth/` (multiple hospital test cases — at least 8: `hospital_01_clean_acute` through `hospital_08_waterfall_critical`). These are **regression test fixtures** with `claims.csv` + `expected.json` per case. Deletion = lose regression coverage.
- Also deletes `RCM_MC/tests/fixtures/messy/`. Sample sizes not yet enumerated.
- Branch ostensibly "fixes 14 pre-existing test failures" (per commit message) — but the fix may be by deleting failing tests rather than fixing the underlying logic. Future iteration must verify which tests it modifies vs deletes.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR44** | **HIGH-PRIORITY: workbench-corpus-polish is structurally stale** | 3,336 files diff with 3,064 deletions and only 111 additions. Branched 2026-04-18; main has moved forward 243 commits since. Most of the branch's "deletions" represent things main has *added* that the branch never saw. **A regular merge would corrupt main.** Recommendation: do **not** merge — instead, cherry-pick the small set of valuable commits (the 14 test fixes? the editorial reskin? the AI settings page?) onto a fresh branch off current main. | **CRITICAL** |
| **MR45** | **Removes `rcm_mc_diligence/` package** | Branch deletes the second package from `pyproject.toml`: drops the `diligence` extras (4 deps), the `rcm-mc-diligence` console script, the `rcm_mc_diligence*` glob from `packages.find`, and 5 package-data globs. Main currently has all of these. Merge will silently lose the second-package architecture unless the conflict is resolved in main's favor. | **CRITICAL** |
| **MR46** | **Deletes `dashboard_page.py` (2,591 lines, 10+ public-ish functions)** | At least 10 module-level functions disappear. If `server.py` or another UI page imports `from .ui.dashboard_page import ...`, the merge breaks at module-load time. Future iteration must grep all 526 server.py imports against this deletion. | **HIGH** |
| **MR47** | **Server.py loses Heroku/Docker/k8s support** | Diff removes `RCM_MC_DB` env-var fallback (line 91) and `/healthz` probe alias (line 1700). The deploy stack on main (`RCM_MC/deploy/Dockerfile`, `docker-compose.yml`, k8s probes) depends on these. | **HIGH** |
| **MR48** | **Massive doc-reorganization conflict** | Branch deletes 25+ docs from `RCM_MC/docs/cycle_summaries/` and elsewhere, adds 21 new `README_LAYER_*.md` docs. Main has retained or restructured these differently. Mostly merge noise rather than data loss, but reviewers will face a 5,000+ line doc diff. | Medium |
| **MR49** | **Deletes `tests/fixtures/kpi_truth/` regression cases** | At least 8 hospital fixtures with `claims.csv` + `expected.json`. These are **deterministic regression cases** — losing them removes a key testing layer. | **HIGH** |
| **MR50** | **Branch claims "fix 14 pre-existing test failures" but may have fixed them by deletion** | Cannot verify from `--stat` alone. Future iteration must diff the test files to see if fixes are real (assertion changes / logic updates) or evasion (test deleted). | **HIGH** |
| **MR51** | **Workflow file moves (.github/ → RCM_MC/.github/)** | The branch wants `.github/` inside `RCM_MC/`. GitHub Actions only triggers off the **repo-root** `.github/workflows/`. Moving them inside `RCM_MC/` **silently disables CI**. Either main rejects the move, or main also moved them inside (per Report 0002 Q3, still open) — needs verification. | **CRITICAL** |
| **MR52** | **No actual schema changes — but no schema migrations either** | The codebase has no `migrations/` or alembic surface. Schema lives in `CREATE TABLE IF NOT EXISTS` calls. Branch did not introduce migrations and did not modify table schema. **Low risk in this branch — but no schema discipline at the architecture level either.** Worth flagging for any branch that adds new tables: there's no enforced migration ordering. | Medium |
| **MR53** | **Numpy/pandas alias proliferation untouched** | Per Report 0005, server.py has 4 numpy + 10 pandas alias spellings. This branch's server.py deletions may have removed some, kept others, or introduced new ones — diff was not exhaustive in this scope. Future iteration must enumerate the alias delta. | Low |
| **MR54** | **`_chartis_kit_legacy.py → _chartis_kit_dark.py` rename** | A rename plus the editorial reskin means the canonical `_chartis_kit.py` (used 10× by server.py per Report 0005) probably also changed. If this branch has both `_chartis_kit.py` (modified) and `_chartis_kit_dark.py` (renamed from legacy), the export surface is ambiguous. | Medium |

## Dependencies

- **Incoming (who depends on `feature/workbench-corpus-polish`):** the branch's commits would need to be replayed if any of them are kept. No external system depends on this branch directly. The 21 commits live only here and on a copy of `feature/demo-real` (per Report 0006 Q1).
- **Outgoing (what `feature/workbench-corpus-polish` depends on):** the older state of main at branch-point `8c39d2c` (2026-04-18 15:17). Anything added to main since then is invisible to this branch.

## Open questions / Unknowns

- **Q1 (this report).** Of the 21 commits ahead of main on this branch, which produce **unique value** (e.g. an editorial reskin not already done on main, AI settings page, real test fixes) versus which produce **duplicated work** that main has already done differently? Per-commit triage required.
- **Q2.** Is the rename `_chartis_kit_legacy.py → _chartis_kit_dark.py` aligned with `_chartis_kit.py` on main, or does the branch introduce a third UI-kit file? (Main also has `_chartis_kit.py` per Report 0005.)
- **Q3.** Does the deleted `dashboard_page.py` get its functions reabsorbed elsewhere on the branch, or just lost? Need to grep the branch for the 10 deleted function names.
- **Q4.** Are the deleted `kpi_truth/` fixtures used by tests on main? If so, deleting them silently removes coverage — pre-merge audit needs to identify the test names that reference these fixtures.
- **Q5.** Did the branch truly fix 14 test failures, or just delete the failing tests? Diff every modified test file.
- **Q6.** Does `feature/demo-real` (suggested-subset of this branch per Report 0006) carry any of the same risks, or just a corpus-provenance subset?
- **Q7.** What value, if any, is on this branch that should be cherry-picked? Specifically: AI settings page (`feat(ai): connect platform to Claude with /settings/ai status page` — commit `2b99b9d` per earlier listing).

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0008** | **Per-commit walk** of the 21 commits on `feature/workbench-corpus-polish`. Classify each: KEEP (unique value) / DROP (already on main differently) / REVISIT (needs context). | Resolves MR44 + Q1 + Q7. The cherry-pick plan emerges from this. |
| **0009** | **`feature/demo-real` merge-risk scan** (the same scan, much smaller — only 12 files diff). Confirms whether it's strictly a subset of polish per Report 0006 Q1. | Cuts scope: if demo-real ⊂ polish, demo-real can be deleted. |
| **0010** | **Diff `analysis/packet.py` between main and every ahead-of-main branch** to find dataclass field changes. Resolves implicit schema-drift risk. | Per Report 0004 MR24, packet.py is the load-bearing API surface; any field change ripples to 80 tests. |
| **0011** | **Verify `dashboard_page.py` deletion impact** — grep `server.py` and other UI pages for imports of the 10 deleted function names. | Resolves MR46. |
| **0012** | **`rcm_mc/diligence/INTEGRATION_MAP.md`** read — owed since 0004, 0005, 0006. | The diligence subsystem keeps surfacing as a merge risk; reading the integration doc may pre-resolve several questions. |
| **0013** | **Compare CI workflow content** — does `.github/workflows/ci.yml` on main do the same thing as `RCM_MC/.github/workflows/ci.yml` on workbench-corpus-polish? Resolves MR51. | If they're equivalent, the move is harmless; if main's content is richer, the branch's move = regression. |

---

Report/Report-0007.md written. Next iteration should: do a per-commit walk of the 21 commits ahead-of-main on `feature/workbench-corpus-polish` and classify each KEEP / DROP / REVISIT to produce a cherry-pick plan — the structurally-stale branch cannot be merged whole, so per-commit triage is the only safe path forward.

