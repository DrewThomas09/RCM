# Report 0023: Version Drift — `pyproject.toml` Declarations vs Actual Imports

## Scope

This report covers a **dependency-vs-import audit** comparing what `RCM_MC/pyproject.toml` declares against what the `RCM_MC/rcm_mc/` source tree actually imports on `origin/main` at commit `f3f7e7f`. Categories scanned:

- **Declared but never imported** (dead extras)
- **Imported but never declared** (undeclared deps — install-time risk)
- **Indirect deps** (declared transitively via another package's pull)
- **Pin-vs-floor mismatch** between pyproject and `legacy/heroku/requirements.txt`

`rcm_mc_diligence/` (the separate second package per Report 0003) is in scope where its imports cross-pollinate with the main `rcm_mc/` package. Test deps and dev deps are included.

Prior reports reviewed before writing: 0019-0022.

## Findings

### Declared deps inventory (recap)

From `RCM_MC/pyproject.toml` per Reports 0003 + 0016:

| Section | Packages | Pin |
|---|---|---|
| `[project] dependencies` (core) | `numpy`, `pandas`, `pyyaml`, `matplotlib`, `openpyxl` | `>=1.24,<3.0` / `>=2.0,<4.0` / `>=6.0,<7.0` / `>=3.7,<4.0` / `>=3.1,<4.0` |
| `[interactive]` | `plotly` | `>=5.0` (no upper) |
| `[pptx]` | `python-pptx` | `>=0.6` |
| `[exports]` | `python-pptx`, `openpyxl` | `>=0.6` / `>=3.1` |
| `[api]` | `fastapi`, `uvicorn` | `>=0.100` / `>=0.23` |
| `[diligence]` | `duckdb`, `dbt-core`, `dbt-duckdb`, `pyarrow` | `>=1.0,<2.0` / `>=1.10,<2.0` / `>=1.10,<2.0` / `>=10.0` |
| `[all]` | `openpyxl`, `plotly`, `python-pptx`, `fastapi`, `uvicorn`, `scipy` | (no scipy upper) |
| `[dev]` | `pytest`, `pytest-cov`, `ruff`, `mypy` | `>=7.0` / `>=4.0` / `>=0.1` / `>=1.5` |

`legacy/heroku/requirements.txt` mirrors the 5 core deps with identical pins.

### Method

For each declared dep:

1. `grep -rEn "from <pkg>|import <pkg>\b" RCM_MC/rcm_mc/ | grep -v __pycache__` to count import sites.
2. Distinguish top-of-file (`^from / ^import`) from inside-function (`^[[:space:]]+from / ^[[:space:]]+import`).
3. Note location patterns (which subpackage hosts the imports).

### Per-package import audit

| Declared dep | Imports in `rcm_mc/` | Top-level / Lazy | Verdict |
|---|---:|---|---|
| **numpy** | many (per Report 0005, 4 alias spellings in server.py alone) | both | ✅ heavy use |
| **pandas** | many (10 alias spellings in server.py per Report 0005) | both | ✅ heavy use |
| **pyyaml** (`yaml`) | 24 production files + 10 test files (Report 0016) | mostly top | ✅ widely used |
| **matplotlib** | not yet enumerated; spot-confirmed in `core/` and exports | top | ✅ used |
| **openpyxl** | not yet enumerated; declared core + in `[exports]` extras (intentional dual-list) | top | ✅ used |
| **scipy** | **3 lazy import sites** (per `grep`); the only one verified via Report 0013 is `core/distributions.py:118` (`from scipy.stats import truncnorm`) | lazy only | ⚠️ See MR184 |
| **fastapi** | **1 site** (`api.py:13`, the orphan from Report 0010) | lazy (inside try) | ⚠️ Orphan-only consumer |
| **uvicorn** | **0 imports** | — | ❌ DEAD declaration |
| **plotly** | **0 imports anywhere in `rcm_mc/`** | — | ❌ DEAD declaration |
| **python-pptx** (`pptx`) | 4 sites; verified at `exports/packet_renderer.py:199, 200` (`from pptx import Presentation`, `from pptx.util import Inches, Pt`) | lazy | ✅ used |
| **duckdb** | **1 site in `rcm_mc/` proper** (need to find) — and used by `rcm_mc_diligence/` per pyproject's package-data globs | lazy | ✅ used |
| **dbt-core**, **dbt-duckdb** | **0 sites in `rcm_mc/`**; used by `rcm_mc_diligence/connectors/seekingchartis/` (DBT models, not Python imports) | — | ✅ DBT-only |
| **pyarrow** | **3 sites in `rcm_mc/diligence/ingest/`** (`readers.py:155`, `tuva_bridge.py:137, 306`) | lazy | ⚠️ See MR183 |
| **pytest** | dev — used by all `tests/test_*.py` | top | ✅ |
| **pytest-cov**, **ruff**, **mypy** | dev — used by tooling, not source | (CI only) | ✅ |

### Imported but **NOT** declared (undeclared deps)

| Package | Site | Status |
|---|---|---|
| **`python-docx`** (imported as `docx`) | `RCM_MC/rcm_mc/exports/packet_renderer.py:507` — `from docx import Document   # type: ignore` (lazy, inside try) | **NOT IN ANY EXTRA.** `[pptx]` declares `python-pptx` but not `python-docx`. **Undeclared.** Probably intended to live in `[exports]`. |
| **`pydantic`** | `RCM_MC/rcm_mc/api.py:14` — `from pydantic import BaseModel` (inside `try` block at line 12-21) | **Indirectly declared** via `[api]` (fastapi pulls pydantic). But pyproject doesn't pin pydantic directly — relies on whatever fastapi 0.100+ resolves. Pydantic v1 ↔ v2 are NOT compatible; fastapi 0.100+ uses pydantic v2. If a future pip resolution gives v1, api.py breaks. |

### Declared but **NOT imported** (dead declarations)

| Package | Declaration | Status |
|---|---|---|
| **`plotly`** (`>=5.0`) | `[interactive]` extras + `[all]` | **DEAD.** `grep -rE "from plotly\|import plotly" RCM_MC/rcm_mc/` returns empty. Project declared interactive plotting but never wired it in. Installs `plotly` for users on `[interactive]` or `[all]` and the dep is purely overhead. |
| **`uvicorn`** (`>=0.23`) | `[api]` extras + `[all]` | **DEAD as a Python import.** `uvicorn` is invoked from the **shell** as `uvicorn rcm_mc.api:app` (per `api.py:5` docstring). It's a runtime CLI dep, not an import dep. Acceptable but misleading — typical extras-pinning convention is for `import`-able packages. |

### Pin discipline

| Aspect | Status |
|---|---|
| Major-version upper bounds | Most pins have `,<N` upper bounds (numpy `<3.0`, pandas `<4.0`, pyyaml `<7.0`, matplotlib `<4.0`, openpyxl `<4.0`, duckdb `<2.0`, dbt-core `<2.0`, dbt-duckdb `<2.0`). Good. |
| Missing upper bounds | `plotly>=5.0`, `python-pptx>=0.6`, `fastapi>=0.100`, `uvicorn>=0.23`, `pyarrow>=10.0`, `scipy>=1.11`, `pytest>=7.0`, `pytest-cov>=4.0`, `ruff>=0.1`, `mypy>=1.5` — **10 unbounded pins**. **Risk: a major-version bump on any of these breaks builds without warning.** |
| Lock file | None (per Report 0016 MR115). Only `legacy/heroku/requirements.txt` mirrors core. **No `requirements-lock.txt`**, no `poetry.lock`, no `uv.lock`. Every install resolves to whatever's current at install time. |
| Heroku mirror drift | `legacy/heroku/requirements.txt` matches pyproject's 5 core deps verbatim. **Maintained as documentation but not auto-regenerated** — a future pyproject change wouldn't update Heroku mirror unless a human edits both. |

### Subtle correctness — `pyarrow` cross-package leak

The pyproject comment at lines 44-46 (Report 0003) says:

> "Phase 0.A diligence-ingestion layer. Isolated from core `rcm_mc` — the new code lives in `rcm_mc_diligence/` and wraps Tuva via `dbt-duckdb`. Core `rcm_mc` imports nothing from here."

But **`rcm_mc/diligence/ingest/readers.py:155` and `tuva_bridge.py:137, 306` import `pyarrow`** — and pyarrow is in the `[diligence]` extras only. These files are inside `rcm_mc/diligence/`, which IS part of the core `rcm_mc` package (per `[tool.setuptools.packages.find]` `include = ["rcm_mc*", "rcm_mc_diligence*"]` at pyproject lines 74-75).

**Implication:** the pyproject comment is misleading. `rcm_mc/diligence/ingest/` IS part of the core `rcm_mc` package and DOES require pyarrow. A user installing `pip install rcm-mc` (no extras) gets the source tree but no pyarrow → `ImportError` at first call into `rcm_mc/diligence/ingest/`.

The 3 lazy import sites mean the failure manifests only when the ingest path runs — not at module-load. But the cross-package isolation claim is **invalidated**.

### Subpackage-specific patterns

- `core/distributions.py` — scipy lazy fallback (Report 0013).
- `exports/packet_renderer.py` — `pptx` (4 sites), `docx` (1 site, undeclared per MR186).
- `api.py` — fastapi + pydantic (orphan per Report 0010).
- `diligence/ingest/readers.py`, `diligence/ingest/tuva_bridge.py` — pyarrow.
- `rcm_mc_diligence/` (separate package, not enumerated this iteration) — duckdb + dbt-core + dbt-duckdb + pyarrow.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR183** | **HIGH-PRIORITY: `pyarrow` import in `rcm_mc/diligence/` violates pyproject's isolation claim** | Pyproject lines 44-46 say "core `rcm_mc` imports nothing from here" referring to the diligence extras. But `rcm_mc/diligence/ingest/readers.py:155` and `tuva_bridge.py:137, 306` use `pyarrow` (in `[diligence]` extras). Default install fails on any path through `rcm_mc/diligence/ingest/`. **Fix: either move pyarrow into core deps, OR move `rcm_mc/diligence/ingest/` into `rcm_mc_diligence/` to match the doc.** | **Critical** |
| **MR184** | **`docx` (python-docx) imported but undeclared** | `exports/packet_renderer.py:507`: `from docx import Document  # type: ignore`. **Not in any pyproject extras.** Users running PPTX/DOCX export hit `ImportError`. Either remove the import (if dead-code path) or add `python-docx` to `[exports]` extras. | **High** |
| **MR185** | **`plotly` declared but never imported** | `[interactive]` extra + `[all]` declare `plotly>=5.0`. Zero `import plotly` / `from plotly` in `rcm_mc/`. The dep is dead weight — installed for users on `[all]` for no benefit. **Fix: remove or wire it in.** | Medium |
| **MR186** | **`uvicorn` declared but never imported** | Used only as a shell command (`uvicorn rcm_mc.api:app`). Acceptable but misleading. The `[api]` extras presence implies an importable surface. | Low |
| **MR187** | **`pydantic` not declared directly** | `api.py:14` imports it. Currently pulled transitively via fastapi (which is in `[api]`). If a future pip resolution gives a pydantic version incompatible with fastapi (rare but possible), api.py breaks at import. **Fix: add `pydantic>=2.0,<3.0` to `[api]` extras.** | Medium |
| **MR188** | **10 unbounded version floors** | `plotly>=5.0`, `python-pptx>=0.6`, `fastapi>=0.100`, `uvicorn>=0.23`, `pyarrow>=10.0`, `scipy>=1.11`, `pytest>=7.0`, `pytest-cov>=4.0`, `ruff>=0.1`, `mypy>=1.5`. A major-version bump on any (e.g. fastapi 1.0 with breaking changes) installs cleanly but breaks builds. **Fix: add upper bounds (`<6.0` for plotly, `<1.0` for fastapi, etc.).** | **High** |
| **MR189** | **No lock file for the modern install path** (cross-link MR115) | `legacy/heroku/requirements.txt` mirrors core deps but is the only lock. Modern installs resolve at install time. **Different boxes resolve to different patch versions.** Recommend: generate `requirements-lock.txt` via `pip-compile` and commit. | Medium |
| **MR190** | **`legacy/heroku/requirements.txt` is hand-maintained — drift inevitable** | Per Report 0016: comment claims "mirrors RCM_MC/pyproject.toml [project.dependencies]" but is not auto-regenerated. A pyproject change without a heroku update silently desyncs Heroku from local. Per Report 0007 MR47, `feature/workbench-corpus-polish` removes Heroku support entirely — would resolve this risk. | Medium |
| **MR191** | **`scipy` declared in `[all]` only — affects `core/distributions.py` correctness** | (Cross-link Report 0013 MR93.) `core/distributions.py:118` uses scipy for true `normal_trunc` moments; falls back to clipped moments without scipy. Default install (no `[all]`) silently uses the wrong moments for any `dist_moments({"dist":"normal_trunc",...})` call. | **High** |
| **MR192** | **`fastapi` declared in `[api]` but only used by an orphan file** | `api.py` (per Report 0010 MR72) has 0 imports. Installing `[api]` for a 63-line orphan that nobody calls is misleading. | Low |
| **MR193** | **No `requirements-dev.txt` exists** | `[dev]` extras are the only dev-deps source. New developer must run `pip install -e ".[dev,all]"` — not documented in `RCM_MC/README.md` (per Report 0019 MR146). | Low |
| **MR194** | **Lazy imports + BLE001 hide undeclared-dep failures** | `exports/packet_renderer.py:507` `from docx import Document  # type: ignore` is inside a try block (per Report 0015's pragma audit). The ImportError is silently swallowed — user sees a partial export with no error message. This pattern combined with MR184 creates the perfect silent-failure: undeclared dep + try/except → empty output, no log. | **Critical** |

## Dependencies

- **Incoming (who consumes pyproject deps):** every install via `pip install -e .` or `pip install rcm-mc`; CI workflows; the Azure VM deploy `RCM_MC/deploy/Dockerfile` (not yet read); operators following `RCM_MC/README.md`'s install instructions.
- **Outgoing:** PyPI for the 14 listed packages (5 core + 9 unique extras); transitively their dependency closures (numpy → no transitive; pandas → numpy; matplotlib → numpy + Pillow + others; fastapi → pydantic + starlette + others; pyyaml → libyaml C-bindings).

## Open questions / Unknowns

- **Q1 (this report).** What does `RCM_MC/deploy/Dockerfile` actually `pip install`? Just `pyproject.toml`? With which extras? Determines what production has.
- **Q2.** Is `uvicorn` ever actually invoked in production? The CLI entry point is `rcm-mc serve` which uses stdlib HTTP, not uvicorn.
- **Q3.** When was `plotly` declared? `git log --diff-filter=A --follow -- pyproject.toml` would surface the introduction commit and the original intent.
- **Q4.** Is `python-docx` available as a system-installed package anywhere (e.g. globally on the dev machine), masking the undeclared-dep failure during dev?
- **Q5.** Are there any third-party imports inside `tests/` that aren't in `[dev]`? Tests can quietly require packages.
- **Q6.** Does `rcm_mc_diligence/` use any dep not in `[diligence]` extras?
- **Q7.** What pydantic major version does `fastapi>=0.100` actually pull in production? `pip install ".[api]"` → `pip show pydantic` would tell.
- **Q8.** Are there any feature branches that add a new third-party dep? Cross-branch sweep for `pyproject.toml` diffs would surface this.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0024** | **Read `RCM_MC/deploy/Dockerfile`** + `docker-compose.yml`. | Resolves Q1 — what production actually installs. |
| **0025** | **Cross-branch `pyproject.toml` diff** — does any of the 8 ahead-of-main branches add or remove a dep? | Catches branches like `workbench-corpus-polish` (Report 0007 MR45 already noted it removes the entire `rcm_mc_diligence` package + `[diligence]` extras). |
| **0026** | **Audit `tests/` for third-party imports** outside `[dev]`. | Resolves Q5. |
| **0027** | **Fix MR183 + MR184** with a single PR: move pyarrow into core OR move `rcm_mc/diligence/ingest/` to `rcm_mc_diligence/`; add `python-docx` to `[exports]`. | Both are real install-time bugs. |
| **0028** | **Generate `requirements-lock.txt`** via `pip-compile` and commit. | Resolves MR189 / MR115. |
| **0029** | **Audit `infra/notifications.py` SMTP env var leak** — owed since Report 0019 MR148. | Sister security concern. |
| **0030** | **Audit `auth/audit_log.py`** — owed since Report 0021 Q1. | Closes the auth subsystem map. |

---

Report/Report-0023.md written. Next iteration should: read `RCM_MC/deploy/Dockerfile` + `RCM_MC/deploy/docker-compose.yml` to determine which pyproject extras are actually installed in production deploys — closes Q1 here and tells us whether the MR183 (pyarrow isolation violation) and MR184 (undeclared docx) bugs are reachable in production or only on dev installs.

