# Report 0001: Repository Root Inventory

## Scope

This report covers the **top level of the repo on `origin/main` at commit `f3f7e7f`** (2026-04-25 — "chore(repo): deep cleanup — RCM_MC root, workflows, 28 subfolder READMEs"). That is: every file and directory at `/Users/drewthomas/dev/RCM_MC/` (the git toplevel), plus a one-line characterization of each. It does **not** cover the contents of `RCM_MC/rcm_mc/` (the package source), `RCM_MC/tests/`, `vendor/cms_medicare/`, or any other branch. Those are reserved for future iterations.

This is the first report in the audit loop. `Report/` did not exist prior to this iteration; it was created here.

## Findings

### Top-level files at repo root

| Path | Size | Role |
|---|---|---|
| [`.gitignore`](../.gitignore) | 1.1 KB | Git ignore patterns. |
| [`LICENSE`](../LICENSE) | 1.1 KB | License text. README and CONTRIBUTING refer to a permissive face, but the file content has not been verified yet — flagged as Q1. |
| [`README.md`](../README.md) | 36 KB | Public-facing front page of the repo. Title: "SeekingChartis / RCM-MC". Begins: "A full-stack healthcare RCM diligence workbench. Runs locally. Calibrated to public-filing data. Turns a banker's book into an IC-ready memo in roughly thirty minutes." Distinct from `RCM_MC/README.md` (the Python package's own README). |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md) | 4.9 KB | Contribution guidelines. Mentions this repo is "a healthcare-PE diligence platform" — content not yet read line-by-line. |
| [`ARCHITECTURE_MAP.md`](../ARCHITECTURE_MAP.md) | 21 KB | Architecture documentation built around GitHub-native Mermaid diagrams. Self-described: "Text-based architecture visualizations using GitHub-native Mermaid. No build step, no HTML, no external dependencies." |
| [`AZURE_DEPLOY.md`](../AZURE_DEPLOY.md) | 7.8 KB | One-page Azure VM deploy quickstart. Self-described: "One page. Five commands. Working server in ~10 minutes." |
| [`DEPLOYMENT_PLAN.md`](../DEPLOYMENT_PLAN.md) | 19 KB | Long-form deploy plan: "Private, password-gated web-app deployment of SeekingChartis / RCM-MC on Azure VM. Assessment + plan — no code written yet." Implies the deploy is partially designed but not fully implemented. |
| [`FILE_INDEX.md`](../FILE_INDEX.md) | 11 KB | Navigable directory of significant files. Self-described as "the map of those maps" (each major directory has its own README). |
| [`FILE_MAP.md`](../FILE_MAP.md) | **261 KB** | Exhaustive file map. Size suggests it is generator-produced; freshness vs. true repo state must be verified — flagged as Q2. |
| [`WALKTHROUGH.md`](../WALKTHROUGH.md) | 19.5 KB | Case-study walkthrough. Self-described: "A real-world scenario, written so a 9th-grader could follow along." |

### Top-level directories at repo root

| Path | Role |
|---|---|
| [`.claude/`](../.claude/) | Claude Code agent configuration: settings.json (project-level), agent definitions, hooks if any. Not strictly part of the codebase but ships with it. |
| `.git/` | Git internals — out of scope. |
| [`.github/`](../.github/) | GitHub Actions workflows directory. Contains `workflows/ci.yml`, `workflows/deploy.yml`, `workflows/regression-sweep.yml`, `workflows/release.yml`. CI surface not yet audited — flagged as Q3. |
| `.pytest_cache/` | Pytest cache, not tracked. Out of scope. |
| [`RCM_MC/`](../RCM_MC/) | **Primary Python package** — contains `pyproject.toml`, the `rcm_mc/` source tree, the `tests/` suite, demo + scenarios + configs, packaged docs. This is the substantive code. Subdirectories visible at one level: `configs`, `data_demo`, `deploy`, `docs`, `rcm_mc`, `rcm_mc_diligence`, `readME`, `scenarios`, `scripts`, `tests`, `tools`. Top-level files inside: `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `demo.py`, `pyproject.toml`, `seekingchartis.py`. |
| [`RCM_MM/`](../RCM_MM/) | **Orphan / mostly-empty placeholder** — contains only `rcm_mc/data_public/` which is itself empty. Likely an iCloud-sync artifact or branch-switch leftover. Not tracked by git in any branch confirmed. Candidate for deletion — flagged as merge risk MR1. |
| [`legacy/`](../legacy/) | Old artifacts. Contains `handoff/` and `heroku/` subdirectories. Probably retained for migration history; no live system depends on it (unverified) — flagged as Q4. |
| [`vendor/`](../vendor/) | Vendored external code/data. Contains `ChartisDrewIntel/` (a DBT project: `dbt_project.yml`, `analyses/`, `models/`, `macros/`, `packages.yml`, `AGENTS.md`, `integration_tests/`, etc.) and `cms_medicare/` (CMS Medicare data + plotting code, including state-level service maps as PNGs). Treated as third-party-style imports, not modified by feature work. |

### Top-level summary numbers

- **10 root markdown files** totaling ~414 KB; **5 GitHub workflows** in `.github/workflows/`.
- **3 substantive top-level directories**: `RCM_MC/`, `vendor/`, `legacy/`. (`RCM_MM/` is empty; the rest are git or build metadata.)
- The bulk of the actual code lives one level deeper at `RCM_MC/rcm_mc/`. That tree has not been entered in this report.
- Trunk = `origin/main` at `f3f7e7f`. 13 other branches exist on origin (12 feature/chore + main); 8 of those have unique commits not yet merged into main. Branch inventory belongs in a future report (proposed Iteration 2).

## Merge risks flagged

| ID | Risk | Detail |
|---|---|---|
| **MR1** | `RCM_MM/` orphan dir | Empty placeholder at repo root. Listed as "Untracked" by git. If merges from `feature/deals-corpus` or other branches re-create files inside it, multiple branches could fight over the same orphan path. Recommendation: confirm `.gitignore` excludes it or delete the empty tree before any merge. |
| **MR2** | `README.md` divergence | `feature/deals-corpus` modified this file (added "Recent change logs" cross-link) on commit `9281474`. Origin/main has been independently revised. Merge will conflict on this file. Resolution likely manual — both edits are additive but in different sections. |
| **MR3** | `CHANGELOG.md` divergence | Same situation — `feature/deals-corpus` added an "Unreleased" section in commit `9281474`. Origin/main has its own changelog progression. Merge will conflict. |
| **MR4** | `FILE_MAP.md` size + staleness | A 261 KB file looks generator-produced. If multiple branches each regenerate it, every merge will surface a near-total file diff that is mostly noise — a humans-cannot-review situation. Recommendation: confirm whether this file is generated, and if so, pin its source-of-truth or `.gitignore` it post-merge. |
| **MR5** | Multiple top-level deploy docs | `DEPLOYMENT_PLAN.md` (19 KB) and `AZURE_DEPLOY.md` (7.8 KB) overlap conceptually. Branches that touch deployment may edit different docs. Risk: deploy guidance silently diverges. Not blocking, but worth pinning a canonical doc. |
| **MR6** | `.github/workflows/` x4 files | If any feature branch added a workflow or modified `regression-sweep.yml` (the most likely candidate given the test-heavy build loop), expect a rebase / merge conflict on workflow YAML. CI definition diffs are easy to merge wrong — flagged as high-care zone. |

(No issues identified at this scope around the `vendor/`, `legacy/`, or `.claude/` trees — they are read-mostly; merge conflicts there would be unusual.)

## Dependencies

- **Incoming (who depends on the repo root):** GitHub Actions workflows (`.github/workflows/*.yml`) execute against this root. Anyone clones this directory expecting `RCM_MC/` to be the main package + `pyproject.toml` to be at `RCM_MC/pyproject.toml`. The Azure deploy plan (`DEPLOYMENT_PLAN.md`) references this layout.
- **Outgoing (what the root depends on):** Git, Python ≥ 3.10 (per `RCM_MC/pyproject.toml`), the runtime deps in `pyproject.toml` (numpy, pandas, pyyaml, matplotlib, openpyxl per the README's project-stats block). External: GitHub-native Mermaid for `ARCHITECTURE_MAP.md` rendering.

## Open questions / Unknowns

- **Q1.** What is the actual license text in `LICENSE`? README + CONTRIBUTING suggest a public face; earlier `RCM_MC/README.md` on a sibling branch said "Proprietary." Determine canonical license posture.
- **Q2.** Is `FILE_MAP.md` (261 KB) generator-produced, and if so by what tool? Find the generator.
- **Q3.** What do the four GitHub workflows do, and which one runs on PR vs. merge vs. release? Map the CI surface so future merges can predict pipeline behavior.
- **Q4.** Is anything in `legacy/` still imported or referenced by live code? `legacy/heroku/` and `legacy/handoff/` look dormant but this has not been verified.
- **Q5.** Why does `RCM_MM/` exist as an empty sibling to `RCM_MC/`? If it is an iCloud sync artifact, it should be removed; if it has a purpose, document it.
- **Q6.** What does `RCM_MC/rcm_mc_diligence/` contain (visible: `connectors/`, `dq/`, `fixtures/`, `ingest/`, plus a CLI)? Is it an alternate diligence pipeline parallel to `RCM_MC/rcm_mc/`? Two top-level packages in one repo is a coupling risk.
- **Q7.** What does `vendor/ChartisDrewIntel/` (a DBT project) connect to in `RCM_MC/rcm_mc/`? Is anything in the Python package consuming DBT model output?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0002** | Branch inventory: enumerate all 14 branches (origin + local), commit counts, divergence vs. main, primary author signal, last-touch date. Identify dead branches vs. live work. | Without this, every merge plan is blind. The audit must produce a branch register. |
| **0003** | `RCM_MC/pyproject.toml` + dependency surface. List every runtime dep, every dev dep, every entry point. Cross-check against actual imports in `RCM_MC/rcm_mc/__init__.py`. | Locks down the dependency contract before any branch merge changes it. Answers part of Q3 (CI runs `pip install -e ".[all]"`). |
| **0004** | `.github/workflows/*.yml` audit (ci.yml, deploy.yml, regression-sweep.yml, release.yml) — what triggers each, what jobs run, what they assert. | Answers Q3. Lets us predict which CI checks gate each merge. |
| **0005** | `RCM_MC/rcm_mc/` package layout: top-level subpackages, what each owns. (Not file-by-file yet — that's the next phase.) | Establishes the map. After this, deeper iterations can target one subpackage at a time. |
| **0006** | Resolve Q6: `RCM_MC/rcm_mc_diligence/` purpose, line count, imports. Is it an active subsystem or vestigial? | Two packages in one repo is a structural unknown that will bite during merge. |

---

Report/Report-0001.md written. Next iteration should: enumerate every branch on origin (commit counts, divergence vs main, last-touch date) so the audit has a canonical branch register before any merge planning begins.
