# Report 0010: Orphan Files / Subsystems in `RCM_MC/rcm_mc/`

## Scope

This report covers **`RCM_MC/rcm_mc/` at depth = 1** on `origin/main` at commit `f3f7e7f`. For every top-level `.py` file and every immediate subpackage, count incoming imports from production (`rcm_mc/`) and tests (`tests/`). Files/subpackages with **0 production imports** are flagged as orphan candidates and inspected to determine whether they are reachable via entry points, tested-but-unwired, or genuinely dead.

The scan complements Report 0009 (dead functions inside one file) by working at the file/subpackage level.

Prior reports reviewed before writing: 0006-0009.

## Findings

### Method

For each subpackage `RCM_MC/rcm_mc/<sub>/` and top-level file `RCM_MC/rcm_mc/<x>.py`, run:

```bash
grep -rln "from rcm_mc\.<x>\b\|from \.<x>\b\|import rcm_mc\.<x>" RCM_MC/rcm_mc \
  | grep -v __pycache__ | grep -v "<self>" | wc -l
```

— and the same against `RCM_MC/tests`. Results below.

### Subpackage scan — full table

53 subpackages enumerated. Subpackages with **0 production imports**:

| Subpackage | Prod imports | Test imports | LoC | Verdict |
|---|---:|---:|---:|---|
| **`management/`** | **0** | 1 | 1,010 | **HIGH-PRIORITY ORPHAN** — 8 modules: `executive.py`, `feedback.py`, `optimize.py`, `org_design.py`, `personality.py`, `scorecard.py`, `succession.py`. ~1,000 lines of management/leadership analysis code with **zero production wiring**. |
| **`portfolio_synergy/`** | **0** | 2 | (not measured) | Tested but unwired. 4 modules: `alpha.py`, `diffusion.py`, `sdid.py` + `__init__.py`. Likely research-grade synergy analysis. |
| **`site_neutral/`** | **0** | 1 | (not measured) | Tested but unwired. 5 modules: `asc_opportunity.py`, `codes.py`, `impact.py`, `revenue_at_risk.py` + `__init__.py`. **Possible duplicate** of `rcm_mc/diligence/regulatory/site_neutral_simulator.py` (Report 0004) — needs verification. |

53 subpackages enumerated; 50 have at least one production import. **3 subpackages are flagged.**

(Notable: `data_public/` shows 177 production imports — the largest concentration on the trunk; `portfolio/` shows 33; `analysis/` shows 36; `infra/` shows 31; `data/` shows 31. These are the busiest subsystems.)

### Top-level `.py` file scan

| File | Lines | Prod imports | Test imports | Mtime | Verdict |
|---|---:|---:|---:|---|---|
| **`api.py`** | 63 | **0** | **0** | 2026-04-17 | **ORPHAN as Python module.** Header docstring at line 1-7 describes a Step-85 FastAPI endpoint launched via `uvicorn rcm_mc.api:app`. Referenced as documentation only in `RCM_MC/CHANGELOG.md:125` and `RCM_MC/readME/14_Full_Summary.md:78`. **No code imports it.** Reachable only by manually starting uvicorn against it; no console script declared in `pyproject.toml` for this. Under the optional `[api]` extras (per Report 0003: `fastapi>=0.100`, `uvicorn>=0.23`). |
| `cli.py` | 1,252+ | 2 | 4 | (not measured) | Live — `rcm-mc` console-script target. |
| **`constants.py`** | 206 | **0** | 1 | (not measured) | **HIGH-PRIORITY ORPHAN — anti-pattern.** Self-described as a "Central registry for cross-cutting magic numbers" deduplicated from ~15 modules. **0 production imports** means the consolidation never happened — the 15 modules still have inline literals; this file is only referenced by 1 test that probably verifies the constants exist. The dedup goal was structurally abandoned. |
| `lookup.py` | 17 | **0** | **0** | 2026-04-17 | Reachable via console script `rcm-lookup = "rcm_mc.lookup:main"` (per Report 0003). 0 imports because direct callers go to `rcm_mc.data.lookup` instead (per Report 0009). Shim is structurally redundant beyond providing the entry-point target. |
| `pe_cli.py` | (not measured) | 2 | 2 | (not measured) | Live. |
| `portfolio_cmd.py` | (not measured) | 2 | 8 | (not measured) | Live. |
| `server.py` | 16,398 | 1 | 166 | 2026-04-25 | Live — the main HTTP entry. The single production import is `rcm_mc/__main__.py`. |

7 top-level files audited; 4 are live, **3 are orphan candidates**: `api.py`, `constants.py`, `lookup.py`.

### Orphan inventory summary

| Path | Type | Lines | Reachability |
|---|---|---:|---|
| `rcm_mc/api.py` | file | 63 | uvicorn invocation only; no Python import |
| `rcm_mc/constants.py` | file | 206 | tested but no production consumer |
| `rcm_mc/lookup.py` | file | 17 | console-script entry only |
| `rcm_mc/management/` | subpkg | 1,010+ | tested but no production consumer |
| `rcm_mc/portfolio_synergy/` | subpkg | (n/m) | tested but no production consumer |
| `rcm_mc/site_neutral/` | subpkg | (n/m) | tested but no production consumer; possible dup of `diligence/regulatory/site_neutral_simulator.py` |

**Total orphan surface: 6 entries, ~1,300+ measured lines, plus 2 unmeasured subpackages.**

### Per-file last-modified dates (orphan candidates)

| File | Mtime |
|---|---|
| `RCM_MC/rcm_mc/api.py` | **2026-04-17** (8 days old, predates the "deep cleanup" commit `f3f7e7f` of 2026-04-25) |
| `RCM_MC/rcm_mc/lookup.py` | **2026-04-17** (same vintage as api.py) |
| `RCM_MC/rcm_mc/constants.py` | not stat'd this iteration |
| `RCM_MC/rcm_mc/management/` files | not stat'd this iteration |

The two file-orphans (`api.py`, `lookup.py`) both have a 2026-04-17 mtime — they were not touched by the `f3f7e7f` cleanup. Either intentionally pinned or silently skipped.

### What this audit does NOT cover (deferred)

- **`extended_seed_*.py` files in `data_public/`** — these are loaded by `importlib.import_module(...)` (per Report 0006 footnote) and are NOT reachable by the static `import` grep used here. They look orphan to grep but are wired through dynamic loading. A separate iteration must enumerate dynamic loaders.
- **`RCM_MC/rcm_mc/<sub>/<file>.py` deep orphans** — this iteration only checks the *subpackage* level, not individual files within subpackages. There may be orphan modules buried inside live subpackages.
- **Files inside `vendor/`, `legacy/`, `RCM_MM/`** — out of scope; those are vendor / placeholder / orphan trees per Report 0001.
- **YAML/JSON/SQL/MD configuration files** — only `.py` files were swept this iteration.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR69** | **`rcm_mc/management/` is a 1,000+ LoC subsystem with no production wiring** | 8 modules (executive, feedback, optimize, org_design, personality, scorecard, succession). If a feature branch wires this in (likely candidate: `feature/connect-partner-brain-phase1` since "partner brain" overlaps with management/leadership concepts), the unwired state on main becomes the wrong baseline. **Pre-merge: cross-check whether any ahead-of-main branch imports `rcm_mc.management`**. If yes, this is the staging branch for live work. If no, the subsystem is pure dead code and should be deleted. | **High** |
| **MR70** | **`rcm_mc/site_neutral/` may duplicate `diligence/regulatory/site_neutral_simulator.py`** | Report 0004 surfaced `diligence/regulatory/site_neutral_simulator.py` as a live module. This new finding shows `rcm_mc/site_neutral/` (separate subpackage) is unwired. **Two parallel implementations of the same concept.** Pre-merge: diff the two implementations and pick one to keep. | **High** |
| **MR71** | **`constants.py` consolidation never happened** | The module exists to dedupe magic numbers from ~15 modules, but 0 production code imports it. Either: (a) the consolidation was started and abandoned (the 15 modules still have inline literals), or (b) consumers were planned but never wired. Either way, **a feature branch that adds new constants will likely add them inline rather than to this file**, exacerbating the drift. | Medium |
| **MR72** | **`api.py` is reachable only via uvicorn invocation** | No console-script entry; no Python import. The optional `[api]` extras pin `fastapi>=0.100` + `uvicorn>=0.23`, but no code path actually starts the API. **A feature branch could touch `api.py` and break the FastAPI surface without any test failing**. Pre-merge: confirm whether any ahead-of-main branch touches `api.py`. | Medium |
| **MR73** | **`lookup.py` shim duplication** | The 17-line shim's `main()` exists only to back the `rcm-lookup` console script. Direct callers go to `rcm_mc.data.lookup`. If a feature branch points the console script at `rcm_mc.data.lookup:main` directly and deletes the shim, no functionality is lost — but the merge mechanics need coordination across `pyproject.toml:71` AND `rcm_mc/lookup.py`. | Low |
| **MR74** | **No automated dead-code / orphan detection in CI** | This audit is manual. A feature branch that adds a new orphan subsystem will not trigger any check. Recommend integrating a coverage tool that flags untested modules and a static-import sweep. | Medium |
| **MR75** | **Dynamic-import paths invisible to grep-based audits** | The `extended_seed_*.py` files in `data_public/` are loaded via `importlib.import_module` and therefore look orphan to a static-import grep but are live. Future orphan audits must enumerate all `importlib.import_module(...)` and `__import__(...)` call sites and exclude their string-keyed targets. | Medium |

## Dependencies

- **Incoming (who depends on this audit's results):** any future merge plan; the cleanup PR that would delete dead modules; CI test thresholds.
- **Outgoing (what this audit depends on):** static `grep` over `RCM_MC/rcm_mc/` and `RCM_MC/tests/` for `from rcm_mc.<x>` / `from .<x>` / `import rcm_mc.<x>` patterns. **Does not catch:** dynamic imports, string-keyed module loaders, plugin systems, console-script entry points (those were verified by hand).

## Open questions / Unknowns

- **Q1 (this report).** Are any of the 6 orphan entries imported on **any ahead-of-main branch**? Pre-merge sweep needed for each candidate. Especially: does `feature/connect-partner-brain-phase1` import `rcm_mc.management`?
- **Q2.** Is `rcm_mc/site_neutral/` a strict duplicate of `rcm_mc/diligence/regulatory/site_neutral_simulator.py`, or do the two implementations cover different aspects (e.g. ASC opportunity sizing vs IDR rate compression)?
- **Q3.** What does `tests/` exercise for `management/`, `portfolio_synergy/`, `site_neutral/`? If the tests are present and passing, the modules at least *run* — but tests pinning behavior on production-unwired modules is itself a smell (testing dead code).
- **Q4.** When was each of the 6 orphan entries first added? `git log --diff-filter=A --follow -- <path>` would give the introduction commit. Useful to know whether the orphan was born orphan (architectural false start) or became orphan (caller migrated away).
- **Q5.** Was `constants.py` ever consumed in production? `git log -p -S "from rcm_mc.constants" -- '*.py'` would find historical importers.
- **Q6.** Does any of the 33 `tests/` subdirs orphan-test the production-orphan subpackages? E.g. is there a `tests/test_management/` directory of management-subsystem tests?
- **Q7.** Are there orphan **modules within live subpackages** (deep orphans) that this audit missed? Need a recursive sweep.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0011** | **CONFIG MAP** (already requested as Iteration 11). | Pending. |
| **0012** | **Cross-branch orphan sweep** — does any ahead-of-main branch import `rcm_mc.management`, `portfolio_synergy`, `site_neutral`, `api`, `constants`, `lookup`? | Resolves MR69/MR70/MR71/MR72/MR73 — Q1. Determines whether the orphans are merge-stage or merge-delete. |
| **0013** | **Recursive deep-orphan sweep** — within each live subpackage, find files with 0 incoming imports. | Resolves Q7. The "live subpackage with dead modules inside" case is more common than top-level orphan and harder to detect. |
| **0014** | **Diff `site_neutral/` vs `diligence/regulatory/site_neutral_simulator.py`** — line-by-line. | Resolves MR70/Q2. |
| **0015** | **Dynamic-import enumeration** — find every `importlib.import_module(...)` and `__import__(...)` call site in `RCM_MC/rcm_mc/`. | Resolves MR75 — required to deduce true reachability of `extended_seed_*.py` and similar. |

---

Report/Report-0010.md written.

