# Report 0099: Dead Code — `domain/custom_metrics.py`

## Scope

`RCM_MC/rcm_mc/domain/custom_metrics.py` (185 lines). Sister to Reports 0009 (lookup.py dead code), 0039 (simulator dead code), 0069 (audit_log dead code). Continues the `domain/` audit chain (Reports 0094, 0095, 0098).

## Findings

### Public symbols inventory

Per `grep -n "^def \|^class " custom_metrics.py`:

| Line | Symbol | Naming | Used externally? |
|---|---|---|---|
| 32 | `class CustomMetric` | public | YES (server.py + test_phase_mn.py) |
| 46 | `def _utcnow_iso` | private | internal only ✓ |
| 50 | `def _ensure_table` | private | internal only ✓ |
| 72 | `def _get_builtin_keys` | private | internal only ✓ |
| 81 | **`def validate_metric_key`** | **public name** | **internal-only — never imported externally** |
| 103 | `def register_custom_metric` | public | YES (server.py + test_phase_mn.py) |
| 154 | `def list_custom_metrics` | public | YES (server.py + ui/settings_pages.py + test_phase_mn.py) |
| 176 | `def delete_custom_metric` | public | YES (server.py + test_phase_mn.py) |

### Cross-codebase usage check (per-symbol grep)

```
CustomMetric           → 2 files (server.py, test_phase_mn.py)
validate_metric_key    → 0 files (NEVER imported externally)
register_custom_metric → 2 files (server.py, test_phase_mn.py)
list_custom_metrics    → 3 files (server.py, ui/settings_pages.py, test_phase_mn.py)
delete_custom_metric   → 2 files (server.py, test_phase_mn.py)
```

### Finding 1 — `validate_metric_key` is public-named but internal-only

`validate_metric_key` (line 81) is **called only from `register_custom_metric` at line 105**. No external import anywhere in `RCM_MC/`. Per CLAUDE.md: "Private helpers prefix with underscore." Should be `_validate_metric_key`.

**Not technically dead** (it's exercised via `register_custom_metric`'s validation path) but **dead from the public-API standpoint** — no caller imports it.

### Finding 2 — UNUSED IMPORTS (5 dead artifacts)

`grep -n "Dict\|field\|asdict\|Optional\|logger"` returns hits ONLY at the import declaration lines:

| Line | Import | Status |
|---|---|---|
| 22 | `from dataclasses import dataclass, field, asdict` | `dataclass` used; **`field` UNUSED**; **`asdict` UNUSED** |
| 24 | `from typing import Any, Dict, List, Optional, Tuple` | `Any`, `List`, `Tuple` used; **`Dict` UNUSED**; **`Optional` UNUSED** |
| 26 | `logger = logging.getLogger(__name__)` | **`logger` defined but NEVER called** |

**5 dead artifacts:**
- `field` (line 22) — never used
- `asdict` (line 22) — never used
- `Optional` (line 24) — never used
- `Dict` (line 24) — never used
- `logger` (line 26) + the `import logging` (line 21) — defined, never called

### Finding 3 — `import logging` (line 21) is functionally dead

`import logging` exists solely to create `logger = logging.getLogger(__name__)` on line 26. But `logger` is never used. Both lines can be removed. Cross-link Report 0024 logging cross-cut: this is a Pattern-A acquired-but-unused logger — silent if a future caller wanted to log here.

### Finding 4 — back-compat name aliasing absent (cross-link Report 0094 MR516)

`finance/reimbursement_engine.py` has a `ReimbursementProfile` clashing with `domain/__init__.py`'s alias. **No similar collision in `custom_metrics.py`** — `CustomMetric` is unique. Clean naming here.

### Finding 5 — exception-handling dead branch

Per `register_custom_metric` (lines 146-151):

```python
        except ValueError:
            con.rollback()
            raise
        except Exception:
            con.rollback()
            raise
```

The two `except` blocks do the same thing. The `except ValueError` is **unreachable** because `except Exception` (a superset) would catch it identically. `ValueError` block is structurally dead. Merge into one `except Exception`.

### Coverage of dead code by tests

- `validate_metric_key` (the indirectly-used internal): exercised by `test_phase_mn.py` BadKey/bad-key/dup tests via `register_custom_metric`. **Test coverage exists** despite no direct import.
- The 5 unused imports + the dead exception branch: not test-detectable; only static analysis would catch.

### Cross-link to Report 0091 tech-debt sweep

Report 0075 noted `auth/` was the "cleanest subsystem audited so far" (0 markers). `domain/` (Reports 0094-0098) felt similarly clean — but this iteration finds **5 unused imports + 1 dead branch + 1 naming-convention violation** in `custom_metrics.py`. Less clean than first impression.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR539** | **5 unused imports + 1 unused `logger` global in `custom_metrics.py` lines 21-26** | Low-impact dead code. Safe to delete. Pre-commit lint should catch (per Report 0056 pre-commit config). | Low |
| **MR540** | **`validate_metric_key` should be `_validate_metric_key` per CLAUDE.md private-helper convention** | Public naming on internal-only function. A branch may import it externally, locking the convention violation. | Low |
| **MR541** | **`register_custom_metric` lines 146-148 `except ValueError` is unreachable (structurally dead)** | Lines 149-151 `except Exception` would handle ValueError identically. Branch refactor risk: someone adds logic to one branch and not the other. | Low |
| **MR542** | **`logger` defined but never used (Pattern-A logger trap)** | If a future commit adds `logger.info(...)` lines without realizing the logger was never wired, it works — but if the import is removed first, the new logging breaks. | Low |
| **MR543** | **Pre-commit hook (per Report 0056) does NOT catch unused imports here** | If pre-commit ran ruff/flake8, lines 21-26 would fail F401. They didn't, so either the hook is missing F401 OR custom_metrics.py is exempted. | **Medium** |

## Dependencies

- **Incoming:** server.py × 3 sites (line 3582, 10475, 14784) + ui/settings_pages.py × 1 (line 20) + test_phase_mn.py × 4-5 import statements.
- **Outgoing:** stdlib only (`re`, `logging`, `dataclasses`, `datetime`, `typing`).

## Open questions / Unknowns

- **Q1.** Why does `validate_metric_key` lack the underscore prefix? Was it ever exported and rolled back?
- **Q2.** Does the pre-commit hook exempt `domain/` from F401 (unused-import) checks, or is it not configured to run F401 at all?
- **Q3.** Should `logger` and `import logging` be removed, or should real log calls be added (per Report 0024 Pattern A vs B)?
- **Q4.** Are there similar dead-imports in the **other 3 `domain/` files**? Not checked this iteration.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0100** | 100-report meta-survey + complete unmapped-subpackage inventory (per Report 0097 MR529). |
| **0101** | Map `rcm_mc/pe_intelligence/` (HIGH-PRIORITY — 4× iterations now). |
| **0102** | Clean up MR539/541 in a single bug-fix commit (per CLAUDE.md "test_bug_fixes_b<N>.py" pattern). |

---

Report/Report-0099.md written.
Next iteration should: 100-report meta-survey (round number; complete unmapped-subpackage inventory).
