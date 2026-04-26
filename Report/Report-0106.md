# Report 0106: External Dep Audit — `python-pptx`

## Scope

Audits the `python-pptx` dependency across pyproject pins, import sites, extras, and trust boundary. Sister to Reports 0016 (pyyaml), 0046 (numpy), 0053 (pandas), 0076 (matplotlib), 0083 (openpyxl). Closes Report 0101 partial (extras audit).

## Findings

### Pin — three places (per Report 0101)

```toml
pptx = ["python-pptx>=0.6"]                     # line 36
exports = ["python-pptx>=0.6", "openpyxl>=3.1"] # line 42
all = [..., "python-pptx>=0.6", ...]            # line 56
```

**3 declarations, all `python-pptx>=0.6`. No upper bound.** Looser than every other pin in the project (numpy `<3.0`, pandas `<4.0`, matplotlib `<4.0`, openpyxl `<4.0`).

### Production import sites (2)

#### Site 1 — `reports/pptx_export.py:33-34`

```python
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
except ImportError:
    logger.warning("python-pptx not installed; skipping PPTX export. Run: pip install python-pptx")
    return None
```

**Lazy + graceful degradation.** Returns `None` when missing. Caller checks for `None`.

123-line module. Generates 5-slide IC deck from `summary.csv`. Outputs `<outdir>/report.pptx`.

#### Site 2 — `exports/packet_renderer.py:199-200`

```python
try:
    from pptx import Presentation    # type: ignore
    from pptx.util import Inches, Pt  # type: ignore
except ImportError:
    return self._render_pptx_fallback(packet, footer)
```

**Stronger pattern: hand-rolled stdlib OOXML fallback.** Per file lines 264-269 docstring:

> "Hand-built minimal OOXML `.pptx` via stdlib `zipfile`. When `python-pptx` is absent we still produce a file partners [can use]."

**Two-tier degradation:**
1. Tier 1 — `python-pptx` (proper presentation library)
2. Tier 2 — `_render_pptx_fallback` via stdlib `zipfile` (always works)

This is **rare design discipline** — most projects gate features on optional deps; this gates the *quality* of output but never the output itself.

### Test import sites (5)

| File | Purpose |
|---|---|
| `tests/test_export_pipeline.py` | end-to-end |
| `tests/test_packet_exports.py` | per-format |
| `tests/test_exports_end_to_end.py` | full flow |
| `tests/test_xlsx_export.py` | despite name, references pptx |
| `tests/test_full_analysis_workflow.py` | integration |

**5 test files reference pptx.** Cross-link Report 0091 (~280 unmapped tests).

### Server.py wiring (2 routes)

| Site | Use |
|---|---|
| `server.py:7982` | URL builder: `f"{base}/export?format=pptx"` |
| `server.py:8728-8817` | `GET /api/analysis/<id>/export?format=pptx` route handler |
| `server.py:8946` | `from .reports.pptx_export import generate_pptx  # noqa: F401` |

The `noqa: F401` is **suspicious** — F401 is unused-import, but the import IS used 1 line later. Likely the noqa is over-cautious; ruff may still report it because of late-binding.

### CLI wiring

```python
ap.add_argument("--pptx", action="store_true",
                help="Write report.pptx (requires python-pptx).")  # cli.py:260
...
if getattr(args, "pptx", False):                                   # cli.py:909
    from .reports.pptx_export import generate_pptx
```

CLI flag `--pptx`. Lazy in-function import. Help text correctly notes the dep.

### Trust boundary

The codebase **WRITES** pptx; it never **READS** user-uploaded pptx (per `grep "load_workbook\|load_pptx"` not run, but per CLAUDE.md no upload route). 

**Implication:** ZIP-bomb / XML-injection vectors don't apply to user input here. Cross-link Report 0083 MR469 (openpyxl untrusted-xlsx-read concern) — pptx surface is similarly write-only.

### Upstream status

- **Project:** [scanny/python-pptx](https://github.com/scanny/python-pptx) (Steve Canny, BSD)
- **Latest 0.6.x as of 2024-2025.** Maintained, slow-pace but not abandoned.
- **No major CVE history.** Pure-Python OOXML; no native code, no parser-bug class of issues.
- **0.6 → 1.0 transition** has been long-rumored. **Loose pin (`>=0.6`) means a future 1.0 release auto-installs and could break call sites.** This is the strongest risk.

### `type: ignore` on the import (line 199-200)

`from pptx import Presentation # type: ignore` — explicitly tells mypy to skip checking. **Cross-link Report 0101 MR554** (`mypy ignore_missing_imports=true`). The `type: ignore` is redundant given the global setting, but provides per-line documentation. Defensible.

### Comparison to other extras

| Extra | Used? |
|---|---|
| `interactive` (`plotly>=5.0`) | unaudited |
| `pptx` (`python-pptx>=0.6`) | **YES — 2 production sites + 5 tests** |
| `exports` (subset of pptx + openpyxl) | YES |
| `api` (`fastapi`/`uvicorn`) | NO — Report 0101 MR549 dead |
| `diligence` (duckdb/dbt) | YES — `rcm_mc_diligence/` separate package |
| `all` | union; scipy unused per Report 0101 MR550 |
| `dev` (pytest, ruff, mypy) | YES |

**`pptx` extras is one of the most-used extras** — solid investment.

### Cross-correction to Report 0083

Report 0083 noted openpyxl is duplicated in `[exports]`. **`python-pptx` is even more duplicated** — appears in `[pptx]`, `[exports]`, `[all]` (3 places). Same pattern; same MR468 advisory.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR591** | **`python-pptx>=0.6` has NO upper bound** | Looser than every other pin in pyproject. A future 0.7 / 1.0 release ships → auto-installs → potential breaking changes. **Recommend `<1.0` ceiling.** | **High** |
| **MR592** | **3 declarations of the same package** (in `[pptx]`, `[exports]`, `[all]`) | Per Report 0083 same pattern flagged for openpyxl. Extras-bag duplication. | (advisory) |
| **MR593** | **`type: ignore` on `from pptx import Presentation` is redundant given global `ignore_missing_imports = true`** | Per Report 0101 MR554. Either rely on global OR remove global. | Low |
| **MR594** | **`server.py:8946 noqa: F401` on a USED import** | Either the import is genuinely unused (and the call site uses lazy-import elsewhere — code smell), OR the noqa is incorrect (over-suppression). | Low |
| **MR595** | **`reports/pptx_export.py` does NOT have the stdlib-fallback that `exports/packet_renderer.py` has** | Two pptx-generating modules; only one degrades gracefully via OOXML. Inconsistent. If python-pptx is missing, `cli --pptx` returns None silently. | Medium |
| **MR596** | **No retention or size cap on generated pptx files** | `outdir` accumulates `report.pptx` per run. Cross-link Report 0087 MR487 (audit_events retention). | Low |

## Dependencies

- **Incoming:** server.py × 2 routes, cli.py × 1 flag, exports/packet_renderer.py, reports/pptx_export.py.
- **Outgoing:** PyPI `python-pptx` package; upstream `scanny/python-pptx` GitHub. No transitive deps mapped.

## Open questions / Unknowns

- **Q1.** Does the stdlib-zipfile OOXML fallback in `exports/packet_renderer.py` produce a file PowerPoint can actually open? (Or just a "well-formed enough" zip that crashes on open?)
- **Q2.** Any tests that explicitly assert behavior when `python-pptx` is uninstalled?
- **Q3.** Why does `reports/pptx_export.py` lack the same fallback as `exports/packet_renderer.py`? Should they be unified?
- **Q4.** What does `transitive_deps` for python-pptx look like? Probably `lxml` (XML), `Pillow` (images). **Pillow has CVE history.**

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0107** | Audit `Pillow` (transitive dep of python-pptx; CVE-prone). |
| **0108** | Audit `plotly` (`[interactive]` extra; never imported in any prior report's grep). |
| **0109** | Map `rcm_mc_diligence/` separate package (carried since Report 0101). |
| **0110** | File MR588 + MR591 as bug tickets (concrete remediation work). |

---

Report/Report-0106.md written.
Next iteration should: audit `plotly` (`[interactive]` extra) — confirms whether it's used like pptx or dead like fastapi/uvicorn.
