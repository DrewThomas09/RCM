# Report 0002: `RCM_MC/` Package Root Inventory

## Scope

This report covers **`RCM_MC/` at depth = 1** on `origin/main` at commit `f3f7e7f` (which my local main is now at, post-pull). That is: every file and subdirectory directly inside `RCM_MC/`, with sizes, characterized in 1-2 sentences each. It does **not** descend into any of those subdirectories — `rcm_mc/`, `tests/`, `docs/`, `readME/`, etc., are reserved for future iterations. Other top-level repo-root entries (`vendor/`, `legacy/`, `RCM_MM/`, `.github/`, `.claude/`) were inventoried in Report 0001 and are not re-covered here.

Prior reports reviewed before writing: Report 0001 (only one in `Report/` so far).

## Findings

### Files at `RCM_MC/` root (10 files, ~46 KB total)

| Path | Size | Mtime | Purpose |
|---|---:|---|---|
| [`RCM_MC/.dockerignore`](../RCM_MC/.dockerignore) | 1,270 B | 2026-04-25 | Docker build context exclusion list. New in `f3f7e7f` ("chore(deploy): add .dockerignore to keep build context lean"). |
| [`RCM_MC/.gitignore`](../RCM_MC/.gitignore) | 1,059 B | 2026-04-25 | Package-level ignore patterns. **Distinct from repo-root `.gitignore`** — second `.gitignore` is a maintenance hazard worth understanding. |
| [`RCM_MC/.pre-commit-config.yaml`](../RCM_MC/.pre-commit-config.yaml) | 1,468 B / 43 lines | 2026-04-25 | Pre-commit hook config. Contents not yet read line-by-line. |
| [`RCM_MC/CHANGELOG.md`](../RCM_MC/CHANGELOG.md) | 7,880 B / 146 lines | 2026-04-25 | Package changelog. **First line of body**: "## v0.6.1 (2026-04-25) — Repo cleanup + go-live hardening" (line 3). Confirms a v0.6.1 was cut on origin/main today. |
| [`RCM_MC/CLAUDE.md`](../RCM_MC/CLAUDE.md) | 12,043 B / 271 lines | **2026-04-17** | AI-assistant guidance. **Older than every other top-level file** — has not been updated since the initial Phase-4 work. Likely stale relative to the v0.6.1 reality on main. |
| [`RCM_MC/README.md`](../RCM_MC/README.md) | 6,796 B / 152 lines | 2026-04-25 | Package README. Title: "RCM-MC (inside SeekingChartis)" / "Revenue Cycle Management + Monte Carlo". **Different file** from the repo-root `README.md` (36 KB). |
| [`RCM_MC/demo.py`](../RCM_MC/demo.py) | 9,323 B / 258 lines | **2026-04-17** | Runnable demo entry. Header: `"""One-shot demo of the RCM-MC partner-ops stack."""`. Older mtime — not touched in the recent v0.6.1 cleanup pass. |
| [`RCM_MC/pyproject.toml`](../RCM_MC/pyproject.toml) | 3,842 B / 126 lines | 2026-04-25 | Python packaging + dep declaration. Touched in the cleanup commit. |
| [`RCM_MC/seekingchartis.py`](../RCM_MC/seekingchartis.py) | 3,163 B / 84 lines | **2026-04-17** | Top-level executable script. Header: `"""SeekingChartis — one command to launch."""`. Older mtime; pairs with `demo.py`. |
| (no `LICENSE` file at this level) | — | — | License lives at repo root (Report 0001 Q1). |

### Subdirectories at `RCM_MC/` (12 dirs)

| Path | Top-level item count | Purpose |
|---|---:|---|
| [`RCM_MC/.pytest_cache/`](../RCM_MC/.pytest_cache/) | 4 | Pytest cache (contains standard `CACHEDIR.TAG`, `README.md`, `v/`). Tracked? Likely ignored — verify against `.gitignore` (Q1 below). |
| [`RCM_MC/configs/`](../RCM_MC/configs/) | 8 (visible: `README.md`, `actual.yaml`, `benchmark.yaml`, `initiatives_library.yaml`, `playbook.yaml`, `scenario_presets/`, `templates/`, `value_plan.yaml`) | YAML config files for the simulator inputs (actual + benchmark portfolios) and initiative library. Active. |
| [`RCM_MC/data_demo/`](../RCM_MC/data_demo/) | 2 (`README.md`, `target_pkg/`) | Demo data shipped for the demo script. Light contents. |
| [`RCM_MC/deploy/`](../RCM_MC/deploy/) | 5 (`Caddyfile`, `Dockerfile`, `docker-compose.yml`, `rcm-mc.service`, `vm_setup.sh`) | **Production deploy artifacts** — a Caddy reverse-proxy config, a Docker image definition, a docker-compose stack, a systemd service, and a VM bootstrap script. Confirms the Azure VM deploy plan in `DEPLOYMENT_PLAN.md` (repo-root) is wired to real artifacts here. |
| [`RCM_MC/docs/`](../RCM_MC/docs/) | **30** files | Long-form package docs: `ANALYSIS_PACKET.md`, `ARCHITECTURE.md`, `BANKRUPTCY_SURVIVOR_PITCH.md`, `BENCHMARK_SOURCES.md`, `BETA_PROGRAM_PLAN.md`, `BUSINESS_MODEL.md`, `COMPETITIVE_LANDSCAPE.md`, `CYCLE_RETRO.md` + 3 numbered cycle retros, `DATA_ACQUISITION_STRATEGY.md`, `INTEGRATIONS_PLAN.md`, `LEARNING_LOOP.md`, `MD_DEMO_SCRIPT.md`, +14 more. Strategy + architecture documentation. |
| [`RCM_MC/rcm_mc/`](../RCM_MC/rcm_mc/) | **63** items | **The actual Python source tree.** Owns the simulator, PE-math, server, UI, alerts, deals, etc. Substantive area. Reserved for its own report. |
| [`RCM_MC/rcm_mc_diligence/`](../RCM_MC/rcm_mc_diligence/) | 7 (visible: `README.md`, `__init__.py`, `cli.py`, `connectors/`, `dq/`, `fixtures/`, `ingest/`) | **HIGH-PRIORITY DISCOVERY:** A second top-level Python package alongside `rcm_mc/`. Has its own CLI, connectors, data-quality module, fixtures, and ingest pipeline. Two top-level packages in one repo is a structural unknown — answers Q6 from Report 0001 partially (it exists; what it does and whether it is active is still open). |
| [`RCM_MC/readME/`](../RCM_MC/readME/) | **27** files | Numbered user-facing docs (`01_API_Reference.md`, `02_Configuration_and_Operations.md`, … `08_Metric_Provenance.md`, `09_Benchmark_Sources.md`, …). The `readME/` capitalization (mixed case, suspicious if you're on a case-sensitive filesystem and a developer types `readme/`) is intentional but a **footgun in CI**. |
| [`RCM_MC/scenarios/`](../RCM_MC/scenarios/) | 3 (`README.md`, `commercial_tightening.yaml`, `management_plan_example.yaml`) | Scenario YAMLs for the simulator's scenario layering. |
| [`RCM_MC/scripts/`](../RCM_MC/scripts/) | 3 (`README.md`, `run_all.sh`, `run_everything.sh`) | Two shell launchers — `run_all.sh` and `run_everything.sh`. Two near-identically named scripts is a maintenance hazard (Q3 below). |
| [`RCM_MC/tests/`](../RCM_MC/tests/) | **459** items | **The substantive test suite.** Per Report 0001 the README on this branch claims 2,883 passing tests; our prior full sweep on `feature/deals-corpus` ran 4,286 / 314 fail. The shape of tests/ on main is its own report. |
| [`RCM_MC/tools/`](../RCM_MC/tools/) | 3 (`README.md`, `build_dep_graph.py`) | Utility scripts — currently one Python script (`build_dep_graph.py`) for dependency-graph generation. |

### Suspicious / out-of-place items found in this scope

- **No `.DS_Store` files** in `RCM_MC/` at depth ≤ 2 (clean).
- **No `*.tmp`, `*.bak`, `*~`** files (clean).
- **No untracked binaries** at this depth (clean — `git status --short RCM_MC/` returned no output).
- **No huge files** (largest at this level is `CLAUDE.md` at 12 KB; the 261 KB `FILE_MAP.md` lives at repo root, not here).
- However, **two near-name-collisions** worth flagging:
  - `RCM_MC/scripts/run_all.sh` vs `RCM_MC/scripts/run_everything.sh` — one likely supersedes the other.
  - `RCM_MC/docs/CYCLE_RETRO.md`, `CYCLE_RETRO_2.md`, `CYCLE_RETRO_3.md`, `CYCLE_RETRO_4.md` — sequential retros with no apparent index. If a retro is canonical, that should be marked.
- **`RCM_MC/CLAUDE.md` mtime is 2026-04-17**, every other top-level file's mtime is **2026-04-25**. The cleanup commit touched everything *except* CLAUDE.md. Either CLAUDE.md is intentionally pinned (unlikely — it documents the package, which has clearly evolved), or it has been silently left stale. Strong signal that AI-collaborator guidance is out-of-sync with reality on main.

## Merge risks flagged

| ID | Risk | Detail |
|---|---|---|
| **MR7** | `RCM_MC/CHANGELOG.md` divergence | On `origin/main` it now begins with `## v0.6.1 (2026-04-25) — Repo cleanup + go-live hardening` (line 3). On `origin/feature/deals-corpus` (commit `9281474`), I appended an "Unreleased" section ahead of v0.5.0 — but `feature/deals-corpus` was branched before v0.6.1 was cut, so its CHANGELOG starts at `## v0.5.0`. Merge will produce a non-trivial conflict in the first ~10 lines: two separate "next release" headers compete. Recommendation: rewrite the J2 entry under `## v0.6.1` or create `## v0.7.0` on merge. |
| **MR8** | `RCM_MC/README.md` divergence | Different content on main (152 lines) vs `feature/deals-corpus` (177 lines). Both branches added a "Recent change logs" / "Documentation" section. Merge conflict guaranteed; resolution likely manual. |
| **MR9** | `RCM_MC/CLAUDE.md` is stale on main | Last-touch 2026-04-17 — predates 8 days of work on `feature/deals-corpus`. The CLAUDE.md on origin/main describes a smaller world (e.g. Phase-4 packet work, no `data_public/`). When `feature/deals-corpus` merges, CLAUDE.md should be regenerated or carefully edited; otherwise AI assistants will operate from out-of-date guidance. Probably easier to overwrite from feature/deals-corpus's CLAUDE.md content since that one accurately describes the live state. |
| **MR10** | Two top-level Python packages (`rcm_mc/`, `rcm_mc_diligence/`) | If any feature branch extends `rcm_mc_diligence/` and another extends `rcm_mc/`, no direct conflict — but they will reference each other (or duplicate each other). HIGH-PRIORITY: future report must determine whether `rcm_mc_diligence/` imports from or duplicates `rcm_mc/`. Wrong-direction imports during a merge could cause circular imports or shadowed modules. |
| **MR11** | `pyproject.toml` dependency drift | 126 lines on main; touched in the cleanup commit. Any feature branch that added a runtime dep (this is forbidden by `RCM_MC/CLAUDE.md` policy on `feature/deals-corpus`, but should be verified across all 8 ahead-of-main branches) will conflict here. Pre-commit config (`.pre-commit-config.yaml`) is also a likely conflict zone. |
| **MR12** | `RCM_MC/deploy/` artifacts | If a branch modified the Dockerfile or docker-compose.yml (e.g. to wire a new module), conflicts will be subtle (e.g. a new EXPOSE port, a new env var). Deploy YAML conflicts are easy to merge wrong silently. |
| **MR13** | `readME/` capitalization | Mixed-case directory name. On a case-insensitive filesystem (macOS default, Windows), no problem. On case-sensitive (Linux CI runners, the production VM), `readme/` and `readME/` are different dirs. If any branch added files via a lowercased path, the merge will silently miss them on a case-sensitive checkout. |

## Dependencies

- **Incoming (who depends on `RCM_MC/`):** the repo-root `README.md`, `DEPLOYMENT_PLAN.md`, `AZURE_DEPLOY.md`, `WALKTHROUGH.md`, `FILE_INDEX.md`, `ARCHITECTURE_MAP.md` all reference `RCM_MC/` paths. The four GitHub workflows (per Report 0001 Q3) almost certainly target this directory. The `vendor/ChartisDrewIntel/` DBT project may or may not depend on Python data produced here (Report 0001 Q7).
- **Outgoing (what `RCM_MC/` depends on):** Python ≥ 3.10 (per `pyproject.toml`); the runtime deps declared therein (numpy, pandas, pyyaml, matplotlib, openpyxl); the deploy stack (Caddy, Docker, systemd) for the Azure target; nothing visibly imported from `vendor/` or `legacy/` at this scope (but unverified).

## Open questions / Unknowns

- **Q1.** Is `RCM_MC/.pytest_cache/` actually ignored, or accidentally tracked? `RCM_MC/.gitignore` content has not been read yet.
- **Q2.** What is the divergence between `RCM_MC/.gitignore` and the repo-root `.gitignore`? Two ignore files at different levels can hide each other's intent.
- **Q3.** What is the difference between `RCM_MC/scripts/run_all.sh` and `RCM_MC/scripts/run_everything.sh`? Which is canonical?
- **Q4.** Is `RCM_MC/rcm_mc_diligence/` an active subsystem or a vestigial one? Specifically — is it imported anywhere in `RCM_MC/rcm_mc/`, exposed by `pyproject.toml` as an entry point, or invoked by any test?
- **Q5.** Why does `CLAUDE.md` lag 8 days behind every other root file? Was the cleanup commit deliberately a no-op on it?
- **Q6.** What do `run_all.sh` / `run_everything.sh` actually do — do they shell out to `seekingchartis.py`, `demo.py`, `pytest`, or something else?
- **Q7.** Are the 4 sequential `CYCLE_RETRO_*.md` retros canonical history or scratch notes that should be archived to a single `RETROS.md`?
- **Q8.** Does `RCM_MC/.pre-commit-config.yaml` conflict with the absence of a repo-root `.pre-commit-config.yaml`? Pre-commit is usually configured at git-toplevel.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0003** | `RCM_MC/pyproject.toml` line-by-line: every dep, every entry point, every dev extra. Cross-check against actual imports in `RCM_MC/rcm_mc/__init__.py`. | Locks the dependency contract before any branch merge can change it. Answers part of MR11. |
| **0004** | `.github/workflows/*.yml` audit (4 workflows). | Answers Report 0001 Q3 — still open. Predicts which CI checks gate each merge. |
| **0005** | `RCM_MC/rcm_mc_diligence/` subsystem audit — is it active? | Answers Q4. HIGH-PRIORITY because a vestigial second package is a merge minefield. |
| **0006** | `RCM_MC/rcm_mc/` package layout (top-level subpackages only — depth = 1). | Establishes the next layer of the map. After this, deeper iterations target one subpackage at a time. |
| **0007** | Branch register — every origin branch, ahead/behind main, last-touch date, primary author. | Earlier deferred from Iteration 2 by the directory-mapping prompt. Still required before any merge planning. |
| **0008** | `RCM_MC/deploy/` artifacts walkthrough — Dockerfile + docker-compose + systemd unit + Caddyfile + vm_setup.sh. | Future merges may touch deployment; we need the baseline first. Addresses MR12. |

---

Report/Report-0002.md written. Next iteration should: read `RCM_MC/pyproject.toml` line-by-line and lock down the dependency surface (resolves MR11 and answers part of Report 0001 Q2/Q3).

