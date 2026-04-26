# Report 0110: Error Handling — `infra/consistency_check.py`

## Scope

`RCM_MC/rcm_mc/infra/consistency_check.py` (133 lines) — closes Report 0107 Q1 + half of MR597 high. Sister to Reports 0020 (packet_builder error handling), 0050 (notifications), 0080 (analysis_store).

## Findings

### Module purpose (per docstring lines 1-15)

Startup-time consistency check for the portfolio store. Verifies:
1. Every expected table exists
2. No orphaned `analysis_runs`, `mc_simulation_runs`, `generated_exports` rows (referencing deleted deals)

**Design promise** (line 13-14): "It never raises — partners prefer '10 orphaned rows in mc_simulation_runs' to a startup traceback."

### Try/except inventory — 1 block

```python
130:    try:
131:        importer()
132:    except Exception as exc:  # noqa: BLE001
133:        logger.debug("consistency touch helper failed: %s", exc)
```

**Single try/except.** Inside `_touch_lazy_tables` loop (lines 130-133).

### Analysis of the try/except

| Aspect | Status |
|---|---|
| Bare `except:` | NO — uses `except Exception` |
| Logging | YES — `logger.debug("consistency touch helper failed: %s", exc)` |
| Re-raise | NO — silently swallowed by design |
| `noqa: BLE001` | explicit; documents intent |
| Captures the exc instance | YES — accessible as `exc` in log line |
| Per Report 0020 broad-except discipline | **Compliant** — broad-except + log + noqa is the documented pattern |

**Per docstring lines 113-117:** "Failures here are swallowed — the check is diagnostic, never a blocker." Documented intent.

**DEBUG level is correct here.** Per Report 0024 cross-cut: WARNING/ERROR would noise the ops log; DEBUG is the right severity for a touch-failure that doesn't change behavior.

### CONTRADICTION between docstring claim and actual safety

**Docstring** (line 13): "It never raises."

**Reality** — `check_consistency` (lines 54-107) has NO try/except. If SQLite errors (e.g. `OperationalError: database is locked`, disk-full, permission-denied, corrupt schema), the exception propagates to the caller.

Specifically risky lines:
- 64: `with store.connect() as con:` — connect can throw
- 67-69: `con.execute("SELECT name FROM sqlite_master ...")` — can throw
- 81-97: 3 `con.execute(...)` JOIN queries — can throw

**The "never raises" promise is overstated.** Per Report 0017: portfolio.store has `busy_timeout=5000` so transient lock contention won't bubble — but corrupt-DB / disk errors will. **MR615 below.**

### Schema inventory discoveries

`_EXPECTED_TABLES` (lines 28-37) names 8 tables. Cross-reference with mapped tables:

| Table | Schema-walked report |
|---|---|
| `deals` | Report 0017 ✓ |
| `runs` | Report 0047 ✓ |
| `deal_sim_inputs` | **never** — referenced only |
| `hospital_benchmarks` | Report 0102 ✓ |
| `data_source_status` | Report 0107 ✓ |
| `analysis_runs` | Report 0077 ✓ |
| `mc_simulation_runs` | **never** — discovered via this report |
| `generated_exports` | **never** — discovered via this report |

**3 new SQLite tables discovered**: `deal_sim_inputs`, `mc_simulation_runs`, `generated_exports`. Schema inventory now: 8 mapped + 3 named-but-unwalked = 11 tables identified, ~11+ remain.

### Module discoveries via `_touch_lazy_tables`

`_touch_lazy_tables` (lines 110-133) imports 5 sibling table-ensure helpers:

| Module | Status |
|---|---|
| `rcm_mc.analysis.analysis_store._ensure_table` | reported |
| `rcm_mc.mc.mc_store._ensure_table` | **NEVER REPORTED** — new module |
| `rcm_mc.exports.export_store._ensure_table` | **NEVER REPORTED** — new module |
| `rcm_mc.data.data_refresh._ensure_tables` | Report 0102/0107 ✓ |
| `rcm_mc.deals.deal_sim_inputs._ensure_table` | **NEVER REPORTED** — new module |

**3 NEW unmapped modules discovered**: `mc/mc_store.py`, `exports/export_store.py`, `deals/deal_sim_inputs.py`.

### Lazy-import pattern

Lines 118-128 use `__import__` instead of regular `from X import Y`:

```python
lambda: __import__("rcm_mc.analysis.analysis_store",
                   fromlist=["_ensure_table"])._ensure_table(store),
```

**Why?** Two possible reasons:
1. Avoid circular imports (per Report 0022/0052 cycle audits).
2. Defer import until the function is called (lazy fallback if some modules don't exist).

This is **idiosyncratic** — most of the codebase uses regular import statements (per Reports 0001-0103). Possibly the only place using `__import__` for lazy. Q1 below.

### Importers

| File | Use |
|---|---|
| `server.py` | likely startup-call (per docstring "Startup-time") |
| `tests/test_hardening.py` | unit tests |

**Only 2 callers.** Tight surface.

### Coverage of error path

Tests in `test_hardening.py` likely exercise the try/except — Q2 below.

### Design discipline

Despite the docstring overstatement (MR615), the module's actual error-handling discipline is solid:
- 1 try/except, both broad + logged + documented
- No bare `except:`, no `pass`-on-failure, no silent swallows
- Per CLAUDE.md: "Docstrings explain WHY, not WHAT" — line 113-117 docstring explains WHY (diagnostic, never blocker). 

### Cross-link to Report 0107 state machine

This module checks for orphans of `deals`. Per Report 0107: `data_source_status` is per-source (one row per `KNOWN_SOURCES` member); `_EXPECTED_TABLES` includes it. **Closes Report 0107 Q1** — `infra/consistency_check.py` reads `data_source_status` only via the SQL `existing` set check (line 65-69), not by querying its rows.

So `data_source_status` is touched here only to verify the table exists, not to read its contents. **Cross-correct Report 0107**: the read-site isn't a real read of status data, just a schema-level existence check.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR615** | **Module docstring claims "never raises" but `check_consistency` has no try/except around SQLite calls** | OperationalError (database locked beyond busy_timeout, corrupt DB, disk full) propagates to caller. Caller (server.py startup) crashes instead of degrading. Per docstring promise, this is a bug. | **High** |
| **MR616** | **3 NEW unmapped tables** (`deal_sim_inputs`, `mc_simulation_runs`, `generated_exports`) discovered via `_EXPECTED_TABLES` | Add 3 to schema-walk backlog (Report 0091 #11). Total mapped tables now 11; ~11 still in backlog. | High |
| **MR617** | **3 NEW unmapped modules** (`mc/mc_store.py`, `exports/export_store.py`, `deals/deal_sim_inputs.py`) discovered via `_touch_lazy_tables` | Each owns a table; cross-link MR616. **HIGH-PRIORITY**. | **High** |
| **MR618** | **`__import__` lazy-import pattern is idiosyncratic** | Used only here in `_touch_lazy_tables`. Static-analysis tools (ruff, mypy) typically don't follow `__import__` strings. If a sibling module is renamed, this code breaks at runtime, not import-time. | Medium |
| **MR619** | **`_EXPECTED_TABLES` is a hardcoded set, not auto-derived** | A new feature that adds a SQLite table must update both the table-creator AND `_EXPECTED_TABLES`. Easy to forget. | Low |
| **MR620** | **`logger.debug` swallows real failures from missing-helper-module case** | If `rcm_mc.mc.mc_store` is renamed/deleted, `__import__` raises ImportError, caught at line 132 and logged at DEBUG. Production logs (typical INFO+) won't show this. Module appears "missing" silently. | Medium |

## Dependencies

- **Incoming:** server.py (startup call), tests/test_hardening.py.
- **Outgoing:** stdlib (`logging`, `dataclasses`, `typing`); 5 sibling _ensure_table helpers via `__import__`.

## Open questions / Unknowns

- **Q1.** Why `__import__` instead of regular `from ... import`? Is it actually circular-import-related, or just convention?
- **Q2.** Does `tests/test_hardening.py` cover the SQLite-error path on `check_consistency`?
- **Q3.** Where is `check_consistency` called from in server.py? Startup route, on-demand admin route, or both?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0111** | Read `analysis/refresh_scheduler.py` (closes Report 0107 Q2 + other half of MR597). |
| **0112** | Schema-walk `mc_simulation_runs` (discovered this report; Report 0091 backlog). |
| **0113** | Read `mc/mc_store.py` (newly discovered; MR617). |
| **0114** | Map `rcm_mc_diligence/` separate package (carried 9+ iterations). |

---

Report/Report-0110.md written.
Next iteration should: read `analysis/refresh_scheduler.py` to close Report 0107 Q2 + the other half of MR597.
