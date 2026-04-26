# Report 0113: Version Drift — Comprehensive `pyproject.toml` ↔ Imports Audit

## Scope

Sweeps all 19 declared dependencies (5 core + 14 in extras + transitive) against actual import-site presence across `rcm_mc/` and `rcm_mc_diligence/`. Closes Report 0101 MR549 + MR550 + Report 0106 follow-up. Sister to Reports 0023 (initial drift), 0046, 0053, 0076, 0083, 0086, 0101, 0106 (per-package).

## Findings

### Declared deps × actual usage matrix

| Package | Pin | Top-level import sites | Lazy import sites | Verdict |
|---|---|---|---|---|
| **Core (line 26-32)** | | | | |
| `numpy>=1.24,<3.0` | strict | many | many | core (Report 0046) |
| `pandas>=2.0,<4.0` | strict | many | many | core (Report 0053) |
| `pyyaml>=6.0,<7.0` | strict | many | many | core (Report 0016) |
| `matplotlib>=3.7,<4.0` | strict | many | many | core (Report 0076) |
| `openpyxl>=3.1,<4.0` | strict | (lazy only) | many | core (Report 0083) |
| **Extras** | | | | |
| `python-pptx>=0.6` (3×) | LOOSE | 0 | 2 lazy | optional (Report 0106) |
| `plotly>=5.0` `[interactive]` | LOOSE | **0** | **0** | **DEAD** |
| `fastapi>=0.100` `[api]` | floor only | 1 (api.py:13, lazy in try) | 0 | **USED** (cross-correction) |
| `uvicorn>=0.23` `[api]` | floor only | 0 | 0 (referenced in api.py docstring) | **launcher-only** |
| `duckdb>=1.0,<2.0` `[diligence]` | strict | 0 | 1 lazy | optional |
| `dbt-core>=1.10,<2.0` `[diligence]` | strict | 0 | 1 lazy (`from dbt.cli.main import dbtRunner`) | optional |
| `dbt-duckdb>=1.10,<2.0` `[diligence]` | strict | 0 | 0 (likely transitive via dbt-core) | optional |
| `pyarrow>=10.0` `[diligence]` | floor only | 0 | 9+ lazy | optional |
| `scipy>=1.11` `[all]` | floor only | 0 | 3 lazy | **USED** (cross-correction) |
| **Dev** | | | | |
| `pytest>=7.0` | floor only | (test runner) | — | dev |
| `pytest-cov>=4.0` | floor only | CI flag only | — | dev |
| `ruff>=0.1` | floor only | pre-commit (Report 0056) | — | dev |
| `mypy>=1.5` | floor only | unverified | — | dev |
| **Implicit transitive** | | | | |
| `pydantic` (via fastapi) | unpinned | api.py:14 (lazy in try) | 0 | **implicit** |

### Cross-correction: Report 0101 MR549 — `[api]` extras

**RETRACTED.** `rcm_mc/api.py` (63 lines) IS a standalone FastAPI app:

```python
"""Step 85: Minimal FastAPI endpoint for programmatic simulation.
Usage:
    pip install fastapi uvicorn
    uvicorn rcm_mc.api:app --host 0.0.0.0 --port 8000
"""
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    app = FastAPI(title="RCM Monte Carlo API", version="0.5.0")
```

It's a **secondary entry-point** — separate from the default `rcm-mc serve` (`http.server` based). Not imported by any other module. Lives as an alternative deployment option.

**CLAUDE.md says: "HTTP via `http.server.ThreadingHTTPServer` — no Flask / FastAPI."** Strictly speaking, **WRONG** — there's a FastAPI variant. CLAUDE.md is talking about the *primary* server only. Doc rot at module-level. **Cross-link Report 0093 MR503 critical doc rot.**

### Cross-correction: Report 0101 MR550 — scipy

**RETRACTED.** scipy IS imported lazily at:
- `core/distributions.py:118` → `from scipy.stats import truncnorm as _tn`
- `reports/reporting.py:266` → `from scipy.stats import gaussian_kde`
- `reports/reporting.py:303` → `from scipy.stats import norm`

Three site-based usages, all `scipy.stats`. Lazy try-import pattern (presumably with numpy fallback). **Used, not vestigial.**

### Cross-correction: Report 0106 follow-up — plotly status

**CONFIRMED DEAD.** Zero `from plotly` / `import plotly` anywhere (top-level OR lazy). The `[interactive] = ["plotly>=5.0"]` extras group is unused. **Closes Report 0106 follow-up Q.**

### NEW FINDING: `pydantic` is an implicit transitive dep

`rcm_mc/api.py:14` imports `pydantic.BaseModel`. **`pydantic` is NOT in pyproject.toml** anywhere — it's pulled in only because `fastapi` depends on it. Installing `fastapi>=0.100` brings pydantic transitively.

**Implication**: a future `[api] = ["fastapi>=0.100"]` bump that drops pydantic (won't happen but theoretically) would silently break `api.py`. **Should be pinned explicitly.** MR632 below.

### NEW FINDING: `uvicorn` is launcher-only, not imported

`uvicorn` appears in:
- `pyproject.toml:43` — declared in `[api]`
- `rcm_mc/api.py` docstring example: `uvicorn rcm_mc.api:app --host 0.0.0.0 --port 8000`
- ZERO Python imports

`uvicorn` is the WSGI/ASGI server CLI tool. It loads the FastAPI `app` object externally. **No `import uvicorn` needed.** Pin is correct (declared as a runtime dep when `[api]` is installed).

### Cross-link to Report 0086 entry-points

Per Report 0086: 4 console scripts. Per Report 0105: `rcm-intake` is broken (`rcm_mc/intake.py` doesn't exist). Per this report: a 5th entry-point exists via `uvicorn rcm_mc.api:app` — not a console script but a runtime entry.

**Total entry surfaces: 5** (4 declared + 1 ASGI).

### Pin tightness ranking

| Tightness | Packages |
|---|---|
| Strict (`>=X,<Y`) | numpy, pandas, pyyaml, matplotlib, openpyxl, duckdb, dbt-core, dbt-duckdb |
| Loose (`>=X` only) | python-pptx, plotly, fastapi, uvicorn, pyarrow, scipy, pytest, pytest-cov, ruff, mypy |
| Unpinned | pydantic (transitive) |

**8 strict pins; 10 loose; 1 unpinned.** Closer to half-loose. Recommend Report 0106 MR591 ceiling discipline applied broadly — `<2.0` ceiling on every floor-only pin.

### Cross-link to dead-extras pattern

Two dead extras now confirmed:
1. `plotly>=5.0 [interactive]` — never imported
2. `[api]` extras WERE thought dead (Report 0101 MR549) but CONFIRMED ACTIVE via this report. NOT dead.

So per this report: **only `plotly` is fully dead** (and possibly half of `dbt-duckdb` since not directly imported, but dbt-core's plugin system loads it implicitly).

### Tests for `api.py`?

`grep "test.*api\|test_api" RCM_MC/tests/`: not run. Q1.

### CLAUDE.md doc-rot accumulation

This iteration adds **3 more contradictions** to the CLAUDE.md doc-rot inventory (Report 0093 MR503, Report 0103 MR574, Report 0107 MR597, this report):

| CLAUDE.md says | Reality |
|---|---|
| "no Flask/FastAPI" | api.py is a FastAPI app |
| "numpy + pandas + matplotlib are the only runtime deps" | scipy used in 3 lazy sites |
| (5 sub-packages listed) | 54 sub-packages exist (per Report 0101 inventory) |

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR632** | **`pydantic` is an implicit transitive dep, never pinned** | If `fastapi` ever drops pydantic or pins to incompatible version, `api.py` breaks. Pin explicitly: `[api] = ["fastapi>=0.100", "uvicorn>=0.23", "pydantic>=2.0"]`. | **Medium** |
| **MR633** | **`plotly>=5.0 [interactive]` is fully dead** — zero imports | Maintaining a never-imported pin lengthens lockfile + onboarding noise. Remove `[interactive]` extras unless future use is planned. | Low |
| **MR634** | **CLAUDE.md "no FastAPI" is wrong** — `rcm_mc/api.py` is a FastAPI app | Architecture doc claims primary server is http.server; reality has a FastAPI alternative. Onboarding ambiguity. | Medium |
| **MR635** | **CLAUDE.md "only numpy + pandas + matplotlib" claim is incomplete** | scipy is used in 3 lazy sites. Either tighten the claim or update CLAUDE.md. | Low |
| **MR636** | **10 of 19 deps are loose-pin (`>=X` only) without ceiling** | Future major versions auto-install. Pattern flagged for python-pptx (Report 0106 MR591); applies more broadly. | Medium |
| **MR637** | **`api.py` is a 63-line standalone never imported anywhere** | If a developer deletes it as "orphan", they break `uvicorn rcm_mc.api:app` for any user relying on the FastAPI variant. Cross-link Report 0010 orphan-file detection: api.py is structurally orphan but functionally an entry-point. | Medium |
| **MR638** | **`uvicorn` is a launcher-only dep with no `import uvicorn`** | This is correct — uvicorn loads via CLI. But static-analysis "unused dependency" linters will flag it as dead. Worth a comment in pyproject.toml. | Low |

## Dependencies

- **Incoming:** every install (`pip install -e .[dev]`), every CI matrix variant.
- **Outgoing:** PyPI for all listed packages.

## Open questions / Unknowns

- **Q1.** Are there tests for `rcm_mc/api.py` (the FastAPI variant)? `grep "rcm_mc.api\b" tests/` — not yet run.
- **Q2.** Is `dbt-duckdb` actually loaded by dbt's plugin discovery, or is it dead like plotly?
- **Q3.** Does CI test the `[api]` install path (with fastapi + uvicorn) ever?
- **Q4.** Is `mypy>=1.5` actually invoked by pre-commit (Report 0056) or is `dev` extras passive?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0114** | Read `rcm_mc/api.py` body — closes Q1 + opens api.py audit (newly discovered alt entry-point). |
| **0115** | Schema-walk `mc_simulation_runs` (Report 0110 MR616 backlog). |
| **0116** | Verify CI matrix tests `[api]` install (closes Q3). |

---

Report/Report-0113.md written.
Next iteration should: read `rcm_mc/api.py` body — closes Q1 + audits the alt FastAPI entry-point discovered this report.
