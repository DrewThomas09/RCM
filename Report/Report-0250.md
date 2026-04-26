# Report 0250: Orphan Files — `legacy/`, top-level scripts, `seekingchartis.py`

## Scope

Orphan-file scan across repo-root and `RCM_MC/` non-package paths. Sister to Reports 0220 (orphan in flight earlier), 0190 (12 unmapped subpackages). Also follows up Report 0247 MR1017 cadence (cross-link new `dev/seed.py`).

## Findings

### Orphan classification

**Orphan = not imported, not entry-pointed, not configured, not tested.**

### Top-level structural inventory (repo root `/Users/drewthomas/dev/RCM_MC/`)

```
RCM_MC/      (the active package — main project root)
RCM_MM/      (separate? cross-link Report 0190)
legacy/      (handoff/ + heroku/)
vendor/      (ChartisDrewIntel/, cms_medicare/, README.md)
Report/      (audit reports — this iteration)
ARCHITECTURE_MAP.md, AZURE_DEPLOY.md, CONTRIBUTING.md, DEPLOYMENT_PLAN.md
FILE_INDEX.md, FILE_MAP.md, LICENSE, README.md, WALKTHROUGH.md
```

### `RCM_MM/rcm_mc/` is suspicious

Mirror name to `RCM_MC/rcm_mc/`. Cross-link memory `project_rcm_mc_layout.md` ("doubled-dir at /Users/drewthomas/dev/RCM_MC/RCM_MC/"). **Likely vestigial/wip duplicate.** No prior Report has read `/Users/drewthomas/dev/RCM_MC/RCM_MM/`. **HIGH-PRIORITY discovery (re-flagged from memory).**

### `legacy/` subtree — orphan candidates

| File | Size | mtime | Reference status |
|---|---|---|---|
| `legacy/handoff/CHARTIS_KIT_REWORK.py` | 21KB | 2025-04-25 | **Zero references in active codebase**. Predecessor of `_chartis_kit.py`. |
| `legacy/handoff/verify_rework.py` | 6.3KB | 2025-04-25 | Referenced only in `docs/cycle_summaries/REDESIGN_LOG.md` (3 hits). Audit script, not imported. |
| `legacy/handoff/SeekingChartis Rework (standalone).html` | 2.2MB | 2025-04-25 | **Zero references**. Standalone design artifact. **Largest single file inspected.** |
| `legacy/handoff/HANDOFF_FOR_CURSOR.md` | 8.5KB | 2025-04-25 | Documentation handoff. Standalone. |
| `legacy/handoff/MODULE_ROUTE_MAP.md` | 7.6KB | 2025-04-25 | Documentation. Standalone. |
| `legacy/handoff/chartis_tokens.css` | 6.3KB | 2025-04-25 | Unreferenced — active version lives at `RCM_MC/rcm_mc/ui/static/chartis_tokens.css`. **Orphan css duplicate.** |
| `legacy/heroku/Procfile` | 67B | 2025-04-25 | Mentioned only in CHANGELOG move-note. Heroku entry-point — **orphan post-Heroku**. |
| `legacy/heroku/app.json`, `runtime.txt`, `requirements.txt` | — | 2025-04-25 | Heroku artifacts, intentionally archived. |
| `legacy/heroku/run_local.sh` | 5.2KB | 2025-04-25 | Heroku-era helper, **orphan**. |
| `legacy/heroku/web/` | dir | — | Likely WSGI shim. Orphan post-Heroku. |

**`legacy/` is intentional archival** per CHANGELOG.md:6 ("Moved Heroku artifacts ... → `legacy/heroku/`"). Files are orphans **by design**. Risk: accidental import resurrection.

### `vendor/` orphan candidates

| File | Note |
|---|---|
| `vendor/ChartisDrewIntel/` | Q1 below — never inspected by any prior Report. **HIGH-PRIORITY.** |
| `vendor/cms_medicare/` | Likely CMS data dump per project pattern. |

### Top-level standalone scripts

| File | mtime | Status |
|---|---|---|
| `RCM_MC/seekingchartis.py` (78L viewed; 3.2KB) | 2025-04-17 | **Standalone runnable launcher** (`python seekingchartis.py`). Imports `rcm_mc.server.build_server` + `rcm_mc.__version__`. **Not imported by any other module** (only self-references in own docstring). Pyproject project name is `"seekingchartis"`. **Effectively a public entry-point — NOT an orphan**, but worth flagging it's a 4th launcher next to `cli.py`/`__main__.py`/`demo.py`. |
| `RCM_MC/demo.py` | 2025-04-17 | Referenced by CLAUDE.md "Running" section. NOT orphan. |
| `RCM_MC/scripts/run_all.sh` | 2025-04-25 | 10KB shell. Referenced only in CHANGELOG move-note. **Orphan-likely** unless invoked by CI/cron. **Q2.** |
| `RCM_MC/scripts/run_everything.sh` | 2025-04-25 | 6.3KB shell. Same as above. **Q2.** |
| `RCM_MC/tools/build_dep_graph.py` | 2025-04-25 | Tested by `tests/test_dep_graph_tool.py`. **NOT orphan.** |

### Documentation file orphans (top-level `.md`)

| File | Status |
|---|---|
| `ARCHITECTURE_MAP.md` | Cross-linked from `tools/README.md`. NOT orphan. |
| `AZURE_DEPLOY.md` | Likely active deploy doc. **Q3** — recent Azure CI commits suggest yes. |
| `CONTRIBUTING.md` | Standard. NOT orphan. |
| `DEPLOYMENT_PLAN.md` | **Q4** — possible duplicate of AZURE_DEPLOY.md? |
| `FILE_INDEX.md` + `FILE_MAP.md` | **Two file-index docs at root.** Possible duplication / stale. **Q5.** |
| `WALKTHROUGH.md` | Standalone. Possibly README-alternative. **Q6.** |

### Cross-link Report 0247 MR1017

`RCM_MC/rcm_mc/dev/seed.py` (896L NEW on feat/ui-rework-v3) is **technically orphan on origin/main today** — does not exist there. Will land as part of merge. Cross-link to MR1017.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1030** | **`RCM_MM/` doubled-directory at repo root** | Per memory — likely vestigial/wip parallel package. Cross-link prior memory note. **Never inspected.** | High |
| **MR1031** | **`vendor/ChartisDrewIntel/` never inspected** | Could contain proprietary code, CMS data, or third-party. Q1 below. | High |
| **MR1032** | **`legacy/handoff/CHARTIS_KIT_REWORK.py` (21KB) zero refs** | If a developer accidentally re-imports it, will conflict with active `_chartis_kit_editorial.py`. **Add to .gitignore-style boundary or rename.** | Medium |
| **MR1033** | **5 root-level `.md` files (ARCHITECTURE_MAP, FILE_INDEX, FILE_MAP, DEPLOYMENT_PLAN, WALKTHROUGH) — possible duplication** | Cross-link FILE_INDEX vs FILE_MAP — same purpose? Risk: drift. | Low |
| **MR1034** | **`scripts/run_all.sh` + `run_everything.sh` — no test, no CI ref** | Cross-link CI workflow files (Report 0184). Likely manual-only smoke. | Low |
| **MR1017** | (carried) `dev/seed.py` is orphan on main pre-merge | (closure) | (carried) |

## Dependencies

- **Incoming:** by definition orphans have none in active codebase.
- **Outgoing:** unknown for `RCM_MM/` and `vendor/ChartisDrewIntel/`.

## Open questions / Unknowns

- **Q1.** What does `vendor/ChartisDrewIntel/` contain?
- **Q2.** Are `scripts/run_all.sh` / `run_everything.sh` invoked by CI or cron?
- **Q3.** Is `AZURE_DEPLOY.md` current vs `DEPLOYMENT_PLAN.md`?
- **Q4.** Is `DEPLOYMENT_PLAN.md` superseded?
- **Q5.** Do `FILE_INDEX.md` and `FILE_MAP.md` describe the same repo?
- **Q6.** Is `WALKTHROUGH.md` redundant with README.md?
- **Q7.** Does `RCM_MM/rcm_mc/` contain unique code or a stale clone?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0251** | Inspect `vendor/ChartisDrewIntel/` head — close Q1 (HIGH-PRIORITY). |
| **0252** | Inspect `RCM_MM/` root — close Q7 (HIGH-PRIORITY). |
| **0253** | Read `dev/seed.py` head — close Report 0247 MR1017 (carried). |

---

Report/Report-0250.md written. Next iteration should: inspect `vendor/ChartisDrewIntel/` directory head — never-mapped, possible proprietary code (Q1, MR1031 HIGH).
