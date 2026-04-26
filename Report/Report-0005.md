# Report 0005: Outgoing Dependency Graph for `rcm_mc/server.py`

## Scope

This report covers the **outgoing-dependency graph for `RCM_MC/rcm_mc/server.py`** on `origin/main` at commit `f3f7e7f`. That is: every package, module, and stdlib component the file pulls in — top-level and lazy. The module was selected because it is the central HTTP entry point and the canonical multi-branch merge battleground (every feature branch that adds a UI page edits this file). Mapping its outgoing imports tells us its blast radius and which subsystem-level signature changes will break it.

Prior reports reviewed before writing: 0001-0004.

## Findings

### File scale

- `RCM_MC/rcm_mc/server.py` — **16,398 lines** (one of the largest single source files in the repo).
- Last modified 2026-04-25 in commit `f3f7e7f`.
- Module docstring (lines 1-23) declares: "Stack: Python stdlib only (`http.server` + `socketserver`). No FastAPI, no Flask, no template engine, no frontend framework." Confirms the deliberate stdlib-only architecture.

### Total imports

- **1,005 import lines** total inside `server.py`.
  - **24 top-level** (lines 25-82, with module-level docstring/blank gaps).
  - **974 in-function (lazy)** imports — the dominant pattern.
  - ~7 misc (string-literal "from …" matches in docstrings — not real imports).

### Top-level imports (lines 25-82, full list)

| Line | Statement | Category |
|---:|---|---|
| 25 | `from __future__ import annotations` | future flag |
| 27 | `import html` | stdlib |
| 28 | `import logging` | stdlib |
| 29 | `import os` | stdlib |
| 30 | `import socketserver` | stdlib |
| 31 | `import sys` | stdlib |
| 32 | `import threading` | stdlib |
| 35 | `import urllib.parse` | stdlib |
| 36 | `import webbrowser` | stdlib |
| 37 | `from http import HTTPStatus` | stdlib |
| 38 | `from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer` | stdlib |
| 39 | `from pathlib import Path` | stdlib |
| 40 | `from typing import Any, Dict, List, Optional, Tuple` | stdlib |
| 42 | `from .infra.rate_limit import RateLimiter` | internal |
| 52 | `import threading as _threading` | stdlib (re-aliased — intentional, used at line 58 for `self._lock = _threading.Lock()` inside a class) |
| 74 | `from .reports import exit_memo as _exit_memo` | internal |
| 75 | `from .portfolio import portfolio_dashboard as _dashboard` | internal |
| 76 | `from .ui._ui_kit import shell` | internal |
| 77 | `from .deals.deal_notes import list_notes, record_note` | internal |
| 78 | `from .deals.deal_tags import add_tag, all_tags, remove_tag, tags_for` | internal |
| 79 | `from .pe.hold_tracking import variance_report` | internal |
| 80 | `from .rcm.initiative_tracking import initiative_variance_report` | internal |
| 81 | `from .portfolio.store import PortfolioStore` | internal |
| 82 | `from .portfolio.portfolio_snapshots import list_snapshots` | internal |

**Top-level summary:** 14 stdlib imports + 1 future flag + 9 internal imports. Zero third-party imports at the top level — confirms the "stdlib HTTP" stance.

### Lazy / in-function imports — categories

| Category | Count of unique targets | Notes |
|---|---:|---|
| **Internal `rcm_mc.*` modules** | **526 unique** | The dominant outgoing surface — see breakdown by subpackage below. |
| Third-party (numpy, pandas, decimal, importlib) | ~5 packages, but 14 distinct alias spellings | Heavy use; alias proliferation discussed under MR29. |
| Stdlib (lazy) | small | Mostly `re`, `json`, `datetime`, `csv`, `gzip`, `io`, `tempfile` — counted but not enumerated here. |

### Internal subpackage usage frequency (top 20)

Count of `from .<subpkg>…` import statements in `server.py`:

| Subpackage | Count |
|---|---:|
| `.ui` | **351** (the dominant — `server.py` is 70%+ a router-to-UI-pages dispatcher) |
| `.deals` | 71 |
| `.data` | 66 |
| `.analysis` | 63 |
| `.infra` | 41 |
| `.pe` | 32 |
| `.portfolio` | 25 |
| `.auth` | 22 |
| `.alerts` | 21 |
| `.reports` | 14 |
| `.ml`, `.finance`, `.diligence` | 13 each |
| `.mc` | 10 |
| `.exports`, `.engagement` | 9 each |
| `.rcm`, `.intelligence`, `.core` | 7 each |
| `.provenance` | 6 |

The `.diligence` subpackage shows up 13 times — that's a real, live subsystem hooked into `server.py`, not vestigial. Confirms Discovery A from Report 0004 (the 40-subdirectory `rcm_mc/diligence/` is wired into the runtime).

### Top UI imports (the 351 in `.ui`)

| Module | Imports |
|---|---:|
| `.ui._chartis_kit` | 10 |
| `.ui.regression_page` | 9 |
| `.ui.onboarding_wizard` | 5 |
| `.ui.pe_tools_page` | 4 |
| `.ui.ebitda_bridge_page` | 4 |
| `.ui.deal_comparison` | 4 |
| `.ui.analytics_pages` | 4 |
| `.ui.advanced_tools_page` | 4 |
| (rest: 3 imports each or fewer) | tail |

The Chartis shared shell (`_chartis_kit.py`) is imported 10 times — confirms it as the load-bearing UI primitive. Any branch that changes its API breaks all 10 sites.

### Third-party deps (full count of distinct alias spellings)

- **numpy** imported under 4 aliases:
  - `import numpy as _np`
  - `import numpy as _np_hist`
  - `import numpy as _np_ldp`
  - `import numpy as _np_scr`
- **pandas** imported under 10 aliases:
  - `_pd`, `_pd_analysis`, `_pd_cal`, `_pd_home`, `_pd_hr`, `_pd_port`, `_pd_pres`, `_pd_reg`, `_pd_runs`, plus the canonical `pd`.
- `from decimal import Decimal as _Decimal` — alias on stdlib too.

The alias-per-block pattern is a strong **code smell** — a routine consolidation pass would replace all aliases with a single `_np` / `_pd`. But because this file is so multi-branch-touched, every consolidation diff would conflict with every feature branch's lazy-import block. **The aliases are de facto frozen**.

### Heavy deps verdict

- **Heavy:** `.ui` (351), `.deals` (71), `.data` (66), `.analysis` (63), `.infra` (41), `.pe` (32). Six subpackages account for **624 of the 974 lazy imports = 64%**. These are the parts of the codebase whose API drift will most impact `server.py`.
- **Numpy + pandas runtime cost:** every route handler that lazily imports numpy or pandas pays the import-time cost on first request to that route. Cold-start is amortized; warm responses are fast. Acceptable.
- **Diligence subpackage import count = 13.** `.diligence` is real and wired into the routes. The 40-subdir tree discovered in Report 0004 is not vestigial.

### Unused / redundant imports

- `import threading as _threading` (line 52) — appears redundant with `import threading` (line 32) but is **actually used** at line 58 inside a class definition: `self._lock = _threading.Lock()`. The aliasing is defensive against parameter-shadowing in handler scope. **Not unused.**
- No top-level imports are obviously dead. Did not perform an exhaustive AST analysis to find indirectly unused symbols (deferred — Q1 below).
- Numpy/pandas alias proliferation is a **redundancy** rather than unusedness; consolidation is structurally fine but a multi-branch-merge minefield.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR29** | **Numpy/pandas alias proliferation in lazy-import blocks** | 4 numpy aliases + 10 pandas aliases. If any branch added a new lazy-import block with a *new* alias spelling (e.g. `_pd_audit`), it adds maintenance noise. If two branches both add the same fresh alias spelling for different blocks, they collide. Pre-merge consolidation should be deferred until ALL branches are merged — premature consolidation creates unnecessary conflicts. | Medium |
| **MR30** | **server.py is the merge supersink (526 internal imports)** | Any branch that renames or moves any of the 526 imported `rcm_mc.*` modules will break `server.py`. `feature/deals-corpus` alone restructured `data_public/` heavily; if main also changed `data_public/` (Discovery B in Report 0004), the lazy-import paths in `server.py` may resolve to one tree on one branch and the other tree on another. **Critical pre-merge audit: enumerate every `from .data_public.<x>` lazy import in `server.py` and verify the target module exists on both branches**. | **Critical** |
| **MR31** | **974 lazy imports defer error to runtime** | The lazy-import pattern is good for cold-start but means a broken import (e.g. removed module on one branch, still referenced in `server.py` on another) won't surface until the relevant route is hit in the browser. Tests that don't exercise every route will not catch this. Pre-merge: for every removed module across branches, grep `server.py` for stale references. | **High** |
| **MR32** | `.ui._chartis_kit` is imported 10 times → API surface | Any branch that changes the signature of `chartis_shell()`, `ck_kpi_block()`, or the `P` palette dict breaks 10 import sites in `server.py` plus all `.ui.data_public/*_page.py` consumers (the J2 page on feature/deals-corpus is one of those). | **High** |
| **MR33** | `.diligence` subpackage import count = 13 | Confirms the diligence/ tree is wired live. If feature/deals-corpus added or removed any `.diligence.<x>` import (likely — the J2 detector lives in data_public not diligence on that branch, but other branches may have touched diligence/), `server.py` will conflict. Pre-merge: enumerate every `.diligence.*` lazy-import block in `server.py` and cross-check against `feature/connect-partner-brain-*` and `feature/workbench-corpus-polish` branches. | **High** |
| **MR34** | Top-level imports include very specific symbols (e.g. `list_notes, record_note, add_tag, all_tags, remove_tag, tags_for, variance_report, initiative_variance_report, list_snapshots`) | Any branch that renamed any of these public functions in their respective modules will break `server.py` at module load time (not just at route-handle time). Top-level breakage = entire web app fails to start. Pre-merge: verify all 9 named imports exist on every ahead-of-main branch. | **High** |
| **MR35** | Module is 16,398 lines — diffs will be large | Any branch that adds a route block or modifies a handler will produce a multi-hundred-line diff. Three-way merges of files this size are mechanically error-prone. Recommend per-branch route-block extraction (cherry-pick or rebase patch-by-patch) rather than full-file merge. | Medium |

## Dependencies

- **Outgoing — internal:** **526 unique `rcm_mc.*` modules**. Top six subpackages (`.ui`, `.deals`, `.data`, `.analysis`, `.infra`, `.pe`) account for 64% of imports.
- **Outgoing — third-party:** numpy (4 alias spellings), pandas (10 alias spellings), and `decimal.Decimal` (one alias). All lazy. Zero third-party at top level.
- **Outgoing — stdlib:** 14 stdlib modules at top level + many more lazy (`re`, `json`, `datetime`, `csv`, `gzip`, `io`, `tempfile`, etc.). Stdlib-heavy posture confirmed.
- **Incoming:** `server.py` is invoked by `__main__.py` and by the `rcm-mc` CLI's `serve` subcommand (per pyproject `[project.scripts]` `rcm-mc = "rcm_mc.cli:main"`). It is NOT imported by any other production module — it is a leaf entry point, despite its size.

## Open questions / Unknowns

- **Q1 (this report).** Are any of the 974 lazy imports actually unused in their handler? An AST-based dead-code analysis would surface these. Manual spot-check would take 50+ iterations.
- **Q2.** What is the actual count of distinct lazy-import targets that resolve to a module that exists on origin/main? Need to enumerate and cross-check the 526 list against `find RCM_MC/rcm_mc -name '*.py'`. Some may be stale references to renamed modules.
- **Q3.** Which 13 `.diligence.<x>` imports specifically does `server.py` make? Cataloging these would close part of MR33.
- **Q4.** What are the 351 `.ui.*` imports specifically? A line-by-line listing would tell us which UI pages are reachable through `server.py` routes vs which are orphaned.
- **Q5.** Does the alias proliferation (`_np`, `_np_hist`, …) imply 4 different code blocks were each authored without seeing the others — i.e. a multi-author / multi-AI session signature? If so, this file may have been written by the build loop with very low coordination, raising the risk that the same handler is duplicated under different aliases.
- **Q6.** What does line 52's `import threading as _threading` (immediately after line 32 `import threading`) actually defend against? Is the aliasing protective or just stylistic?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0006** | **Enumerate the 526 unique internal lazy-import targets in `server.py`** and verify each module exists at the path implied. Catalog stale references. | Resolves MR30 + MR31 + Q2. Single biggest pre-merge unknown. |
| **0007** | **Map all 13 `.diligence.<x>` lazy imports in `server.py`** to their target modules. Build the mini incoming-dep graph for the diligence subsystem. | Resolves MR33 + Q3. The diligence/ tree is live but unexplored. |
| **0008** | Read `rcm_mc/diligence/INTEGRATION_MAP.md` (17 KB) — owed since Report 0004's suggested follow-up. | Likely pre-answers many merge-time questions about the diligence subsystem. |
| **0009** | Branch register — every origin branch, ahead/behind main, last-touch date, primary author. Repeatedly owed since 0001. | Required before any merge planning. Cannot be deferred forever. |
| **0010** | Walk `rcm_mc/cli.py` (1,252+ lines, owed since Report 0003). | Maps the CLI surface. Ties into MR14 (broken `rcm-intake` entry point). |
| **0011** | Read `analysis/__init__.py` end-to-end and produce the canonical re-export list. | MR24 mitigation (owed since Report 0004). |

---

Report/Report-0005.md written. Next iteration should: enumerate every one of the 526 unique internal lazy-import targets in `server.py` and verify each resolves to an actual file on origin/main — closes MR30/MR31/Q2 and is the single biggest blocker on merge planning.

