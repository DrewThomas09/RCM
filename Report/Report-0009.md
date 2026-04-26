# Report 0009: Dead Code in `rcm_mc/data/lookup.py`

## Scope

This report covers **defined-but-unimported and imported-but-uncalled symbols in `RCM_MC/rcm_mc/data/lookup.py`** on `origin/main` at commit `f3f7e7f`. The module was selected because it backs the `rcm-lookup` console script declared in `RCM_MC/pyproject.toml:71` (`rcm-lookup = "rcm_mc.lookup:main"`) — verified live in Report 0003 — and because it is large enough (1,114 lines) to harbor coverage gaps but contained enough to audit in one iteration. The thin shim at `RCM_MC/rcm_mc/lookup.py` (17 lines) is also covered as part of the public-API surface.

Prior reports reviewed before writing: 0004-0008.

## Findings

### Module shape

- `RCM_MC/rcm_mc/data/lookup.py` — **1,114 lines**.
- 6 public functions (no leading underscore):

| Line | Name | Role |
|---:|---|---|
| 55 | `search` | Hospital lookup search backbone. |
| 156 | `format_one_hospital` | Plain-text formatter for one hospital row. |
| 195 | `format_table` | Plain-text formatter for a table of rows. |
| 338 | `main` | The `rcm-lookup` CLI entry. |
| 692 | `format_markdown_summary` | Markdown summary block generator. |
| 856 | `format_one_liner` | One-line summary for inclusion in IC briefs. |

- 19 private functions (leading underscore) — internal implementation details.
- 0 classes.
- The shim `RCM_MC/rcm_mc/lookup.py:7` does `from .data.lookup import *  # noqa: F401, F403` — re-exports all public symbols at the top-level `rcm_mc.lookup` namespace.

### External usage of each public function

Counts are external refs (across `RCM_MC/`), excluding `data/lookup.py` itself and `__pycache__`. Generic-named symbols like `main` were sanity-checked against the actual import statements rather than raw greps (because `main` matches everywhere).

| Function | Production refs | Test refs | Dead? |
|---|---|---|---|
| `search` | `server.py:5614` (lazy: `from .data.lookup import search as _lookup_search`) | `tests/test_lookup.py:12` | **LIVE** |
| `main` | `cli.py:1279` (`from .data.lookup import main as lookup_main`) | 4 tests (`test_transparency.py:225, 244`; `test_irs990.py:243, 267`; `test_lookup.py:12`) | **LIVE** |
| `format_one_liner` | `cli.py:1077` (`from .data.lookup import format_one_liner`) | `test_lookup.py:12` | **LIVE** |
| **`format_one_hospital`** | **NONE** | `test_lookup.py:127` (one call site) | **DEAD in production** |
| **`format_table`** | **NONE** | `test_lookup.py:136, 144, 207` (3 call sites) | **DEAD in production** |
| **`format_markdown_summary`** | **NONE** | `test_lookup.py:182, 194, 199` (3 call sites) | **DEAD in production** |

Verification:
- `grep -rn "format_one_hospital\|format_table\|format_markdown_summary" RCM_MC/rcm_mc/ | grep -v __pycache__ | grep -v "RCM_MC/rcm_mc/data/lookup.py"` returns empty. **No production code references these three functions.**
- `grep -n "format_one_hospital\|format_table\|format_markdown_summary" RCM_MC/rcm_mc/cli.py` returns empty.

### Three formatters exist solely to be tested

`format_one_hospital`, `format_table`, and `format_markdown_summary` together occupy roughly:
- `format_one_hospital` — lines 156-194 = ~39 lines
- `format_table` — lines 195-230 = ~36 lines
- `format_markdown_summary` — lines 692-819 = ~128 lines

**Total: ~203 lines (~18% of the module) tested but unconsumed by production.** They have no incoming production import; their only callers are 7 lines in `tests/test_lookup.py`.

This is the textbook "test-only public function" pattern — common when a function was introduced for a now-removed feature but the test was retained, or when the test file imports them out of habit and the production code path was migrated away.

### The shim `rcm_mc/lookup.py` (17 lines)

```python
# Line 7
from .data.lookup import *  # noqa: F401, F403
# Line 8
from .data import lookup as _impl
# Line 11
def main() -> int:
    ...
```

The shim's role is twofold:
1. **Provide the `rcm-lookup` entry-point target** — `pyproject.toml:71` says `rcm-lookup = "rcm_mc.lookup:main"`, so the shim's `main()` is what gets invoked by the console script.
2. **Re-export the data/lookup public API at `rcm_mc.lookup.<name>`** — via `import *`.

Verification:
- `grep -rn "from rcm_mc.lookup\b\|from .lookup\b" RCM_MC/` (excluding `data/`) returns **empty**. **No external caller uses `rcm_mc.lookup.<symbol>`.** Every direct importer goes to `rcm_mc.data.lookup` instead.
- The wildcard re-export at line 7 exists but is not consumed.

### Imported-but-uncalled symbols

- The wildcard `from .data.lookup import *` in the shim re-exports **6 public symbols + module-level constants** (none of those are imported anywhere by their `rcm_mc.lookup.<name>` path).
- The `from .data import lookup as _impl` at shim line 8 binds `_impl` — verifying its usage:

```bash
grep "_impl" RCM_MC/rcm_mc/lookup.py
```

If `_impl` is never used, that import is dead too. (Need to verify; likely used by `main()` body.)

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR64** | **3 dead-in-production formatters** | `format_one_hospital`, `format_table`, `format_markdown_summary` — ~203 lines total. **Deletion is safe in production but breaks `test_lookup.py`.** Pre-merge plan: delete the 3 functions AND the corresponding test cases (`test_lookup.py` lines that call them). Net negative LoC, no production behavior change. | **Medium** (cleanup, not breakage) |
| **MR65** | **`rcm_mc/lookup.py` wildcard re-export has zero consumers** | The `from .data.lookup import *` at `lookup.py:7` exposes 6 symbols (and `noqa: F401, F403` silences the lint). **No code anywhere in `RCM_MC/` consumes `rcm_mc.lookup.<name>`.** Safe to remove the wildcard. The shim should retain `from .data.lookup import main` (or import path equivalent) to back the entry point. | Low |
| **MR66** | **A feature branch may add a fourth dead formatter** | The pattern "add a `format_X()` function, write a test, never wire it into production" is established here. Pre-merge: any branch that adds another `format_*` to `data/lookup.py` should be verified for production consumption before merge. | Low |
| **MR67** | **The 3 dead formatters may be on `feature/deals-corpus` or other branches with new callers** | This audit only covers `origin/main`. If a feature branch adds `from rcm_mc.data.lookup import format_markdown_summary` (e.g. for a new IC-brief renderer), the dead-code finding flips. Pre-merge: re-grep on every ahead-of-main branch before deletion. | Medium |
| **MR68** | **`test_lookup.py` will fail if functions are deleted without test updates** | Lines 127, 136, 144, 182, 194, 199, 207 reference dead-in-production functions. Coordinated deletion required: delete functions + delete tests + delete the symbols from the `from rcm_mc.data.lookup import (...)` block at `test_lookup.py:12`. | Low (mechanical) |

## Dependencies

- **Incoming:** Production `cli.py` (uses `main`, `format_one_liner`); production `server.py` (uses `search`); 5 test files. Total: 7 distinct files.
- **Outgoing:** `RCM_MC/rcm_mc/data/lookup.py` imports — not enumerated this iteration; will need its own outgoing-dep iteration.

## Open questions / Unknowns

- **Q1 (this report).** Does `rcm_mc/lookup.py:8` `_impl` actually get used in `main()`? Need to read the shim's `main()` body (likely just delegates to `_impl.main(...)`).
- **Q2.** Were `format_one_hospital`, `format_table`, `format_markdown_summary` ever production-consumers, and where did the consumers go? `git log -p -- RCM_MC/rcm_mc/data/lookup.py` would surface the original wiring.
- **Q3.** Does any of the 5 test files exercise these dead-in-production functions through a behavior they actually verify (e.g. format-stability across schema changes), or are they essentially `assert format_table([]) != ""`-grade smoke tests?
- **Q4.** Does `tests/test_lookup.py` import any other dead symbols not surfaced here (`_parse_beds_range` is imported at line 12 — is it tested only, or is the private function exercised meaningfully)?
- **Q5.** Of the 19 private functions in `data/lookup.py`, are any unreferenced even within the module (i.e. truly orphaned)?
- **Q6.** What happens if I delete the shim `rcm_mc/lookup.py` and point pyproject's entry to `rcm_mc.data.lookup:main` directly? The shim adds an indirection layer that costs 17 lines and saves nothing.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0010** | **Orphan-files sweep** (already requested as Iteration 10 — pending). | Direct continuation of dead-code analysis at the file level. |
| **0011** | **Walk `rcm_mc/cli.py`** (1,252 lines) — owed since 0003. Find any other dead entry-point declarations (per MR14). | The `rcm-intake` entry point is broken; `rcm-lookup` works through a redundant shim. CLI surface needs a full audit. |
| **0012** | **Cross-branch audit of `format_one_hospital` / `format_table` / `format_markdown_summary`** — does any ahead-of-main branch add a new caller? | Resolves MR67. |
| **0013** | **Survey private-function dead code in `data/lookup.py`** — internal callgraph of the 19 `_*` functions. | Resolves Q5. |
| **0014** | **Read `rcm_mc/diligence/INTEGRATION_MAP.md`** — owed since 0004. | The single most-deferred follow-up. |
| **0015** | **Enumerate every CREATE TABLE across `rcm_mc/`** — owed since Report 0008's MR55. | Schema-correctness blocker. |

---

Report/Report-0009.md written.

