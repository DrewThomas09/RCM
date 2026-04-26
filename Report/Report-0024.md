# Report 0024: Cross-Cutting Concern — Logging across `rcm_mc/`

## Scope

This report covers **logging as a cross-cutting concern** across the entire `RCM_MC/rcm_mc/` source tree on `origin/main` at commit `f3f7e7f`. It catalogs:

- The central logger configuration.
- Every place that obtains a logger.
- Every `logger.<level>` call by level.
- Coexisting logger-acquisition patterns and the inconsistencies between them.

Logging was selected because Reports 0020 (packet_builder.py — 100% logger.debug, "all logging silent in production") and 0021 (auth.py — 0 logger calls in security-critical code) flagged production-visibility gaps that span the whole codebase. This report does the cross-cut.

Prior reports reviewed before writing: 0020-0023.

## Findings

### Central logger setup — `infra/logger.py`

20 lines, last touched 2026-04-17 (older than most root files per Report 0002):

```python
"""
Centralized logging for the rcm_mc package.

Usage in any module:
    from .logger import logger
    logger.warning("something happened")
"""
from __future__ import annotations
import logging

logger = logging.getLogger("rcm_mc")        # line 12

if not logger.handlers:
    _handler = logging.StreamHandler()      # default: stderr
    _handler.setFormatter(
        logging.Formatter("[%(levelname)s] rcm_mc: %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)            # line 20
```

Key facts:

- **Named logger:** `"rcm_mc"`.
- **Default level:** `INFO`. Per-module loggers (children) inherit unless overridden.
- **Default handler:** `StreamHandler` → stderr.
- **Format:** `[<LEVEL>] rcm_mc: <message>`.
- **Idempotent:** `if not logger.handlers` guard prevents duplicate handlers on re-import.
- **No file output, no rotation, no remote log shipper.** Pure stderr stream.

### Two competing logger-acquisition patterns

There are **TWO co-existing patterns** for obtaining a logger across the codebase. They produce different logger names and have different inheritance semantics.

| Pattern | Where | Count | Logger name |
|---|---|---:|---|
| **Pattern A — central** | `from .infra.logger import logger` (or `from ..infra.logger import logger`) | **12 files** | `"rcm_mc"` (a single shared named logger) |
| **Pattern B — per-module** | `logger = logging.getLogger(__name__)` | **82 files** | `"rcm_mc.<sub>.<module>"` (one logger per module) |

Pattern A (central):

- `RCM_MC/rcm_mc/__init__.py:3` (`from .infra.logger import logger  # noqa: F401`)
- `analysis/anomaly_detection.py`
- `analysis/compare_runs.py`
- `core/calibration.py`
- `core/simulator.py`
- `data/data_scrub.py`
- `infra/capacity.py`
- `infra/config.py`
- `infra/output_formats.py`
- `infra/run_history.py`
- (2 more)

Pattern B (per-module):

- `RCM_MC/rcm_mc/server.py:34`
- `ui/deal_timeline.py:19`
- `ui/dashboard_v3.py:39`
- `ui/onboarding_wizard.py:35`
- `ui/dashboard_v2.py:16`
- `ui/global_search.py:52`
- `ui/hold_dashboard.py:14`
- `ui/deal_profile_v2.py:48`
- `pe/value_bridge_v2.py:38`
- `pe/value_creation_plan.py:18`
- (72 more)

#### Why this matters

Python's logging hierarchy means **per-module loggers inherit level and handlers from the closest configured ancestor**. Children of `"rcm_mc"` (e.g. `"rcm_mc.server"`, `"rcm_mc.analysis.packet_builder"`) inherit the INFO level and StreamHandler set up in `infra/logger.py`.

**This works because the root `"rcm_mc"` logger is configured at module-import time** (the side-effect at `infra/logger.py:14-20`). Whoever imports `from rcm_mc.infra.logger import logger` *or* whoever causes `rcm_mc/__init__.py:3` to fire (which runs `from .infra.logger import logger`) triggers this side-effect.

The first time anything imports any submodule of `rcm_mc`, Python executes `rcm_mc/__init__.py`, which imports `infra/logger.py`, which configures the named logger. So **all 82 per-module Pattern-B loggers DO see the INFO level + StreamHandler** — but only because of this implicit init-time chain.

**Risk:** If `rcm_mc/__init__.py:3` is removed or reordered, Pattern B loggers would suddenly have no handler and root-level (WARNING) inheritance — potentially silencing INFO/DEBUG that previously appeared and surfacing WARNING that previously didn't.

### Call-level distribution (all 146 calls across `rcm_mc/`)

```
logger.debug         63   (43.2%)  ← silent in production at INFO level
logger.info          38   (26.0%)
logger.warning       35   (24.0%)
logger.error          6   ( 4.1%)
logger.exception      0   ( 0.0%)  ← NEVER logs tracebacks
logger.critical       0   ( 0.0%)
```

Only **6 `logger.error` sites in the entire codebase**:

| File | Line | Context |
|---|---|---|
| `server.py:1916` | unhandled GET handler | `logger.error("unhandled GET %s: %s", self.path, exc)` |
| `server.py:10201` | unhandled POST handler | `logger.error("unhandled POST %s: %s", self.path, exc)` |
| `infra/backup.py:88` | backup file missing | `logger.error("backup file not found: %s", backup)` |
| `infra/backup.py:102` | decompression failure | `logger.error("decompression failed: %s", exc)` |
| `infra/backup.py:112` | integrity check failed | `logger.error("integrity check failed on restored backup")` |
| `infra/backup.py:116` | invalid SQLite db | `logger.error("not a valid SQLite database: %s", exc)` |

**HIGH-PRIORITY observation:** The 6 error-level calls are concentrated in just 2 files (server.py + infra/backup.py). **Every other module** (auth, analysis, packet_builder, ui/*, pe/*, ml/*, data/*, etc.) — none log at error level when something goes wrong. They either log at debug, log at warning, or silently swallow (Report 0020 + Report 0021).

### Zero `logger.exception` calls

`logger.exception(...)` is the canonical way to log an exception with traceback inside an `except` block. Across the entire codebase: **0 calls**.

This means **tracebacks are never preserved in logs**. Every error either:
- Surfaces only the `str(exc)` message via `logger.error(..., exc)` (6 sites), OR
- Is silently swallowed (per Report 0020 BLE001 patterns), OR
- Is converted to a `SectionStatus.FAILED` field on the packet (Report 0020 Pattern B).

A production crash or intermittent failure cannot be post-mortem-debugged from the logs alone. **An operator sees `[ERROR] rcm_mc: unhandled GET /deal/abc: KeyError('deal_id')` and has no traceback to find the offending line.**

### Logger-call density per subsystem

(Grep counts; not normalized to LoC.)

| Subsystem | logger calls (estimated) |
|---|---:|
| `infra/` | concentrated (config, capacity, run_history, output_formats, backup) |
| `core/` | calibration, simulator |
| `analysis/` | 20 in `packet_builder.py` (all DEBUG per Report 0020), plus a few in `anomaly_detection`, `compare_runs` |
| `server.py` | unknown count, but contains 2/6 error-level calls |
| `auth/` | **0 in `auth.py`** (Report 0021 MR163) |
| `ui/*` | unknown but heavy (multiple `getLogger(__name__)` sites) |
| `pe/*` | unknown |
| `data_public/*` | unknown — likely sparse (most are corpus seeds) |

### Print statements as alternate output

`print(...)` calls are NOT logging — they're CLI user-facing output. Heavy density in:

- `cli.py` — 88 `print()` sites (the CLI banner, progress messages, results)
- `portfolio_cmd.py` — 24 `print()` sites
- `infra/_terminal.py` — 1 `print()` (the terminal helper)
- `analysis/challenge.py` — 11 sites
- `deals/deal.py` — 21 sites

These are intentional CLI output. **They do NOT route through `infra/logger.py`** — so they don't honor any log-level filter, don't get prefixed with `[LEVEL] rcm_mc:`, and don't go to stderr. They go to stdout where the user expects them.

**Inconsistency risk:** if a feature branch swaps a `print(...)` for a `logger.info(...)`, the formatting changes (gets a `[INFO] rcm_mc: ` prefix), and the output stream changes (stdout → stderr). The user UX shifts.

### No log file, no rotation, no shipper

`infra/logger.py` configures only a `StreamHandler` (stderr). No `RotatingFileHandler`, no `SysLogHandler`, no `JSONFormatter`. Production logs are whatever stderr captures — typically systemd-journal on the Azure VM (per `RCM_MC/deploy/rcm-mc.service`, not yet read), or the docker logs in a container deploy.

**Implication for the audit:** there is no on-disk log file to grep for incidents. Forensic investigation depends on whatever the deploy environment captures from stderr.

### env-var hooks for log-level

`grep "LOG_LEVEL\|LOG_FORMAT\|LOG_FILE"` in `infra/logger.py` and across the codebase — **none.** No env-var lets the operator change log level at runtime. Operators cannot enable DEBUG mode without code change.

### `__init__.py:3` — the load-bearing single line

`RCM_MC/rcm_mc/__init__.py:3` is the only line that ensures `infra/logger.py` runs on package init:

```python
from .infra.logger import logger  # noqa: F401
```

Without this line, the named logger isn't configured until the first explicit `from .infra.logger import logger`. Pattern-B loggers (82 modules) would then be unconfigured — Python's default WARNING level + no handler. Critical infrastructure depends on this single line.

## Cross-pattern inconsistencies

| Inconsistency | Detail | Impact |
|---|---|---|
| **A vs B import pattern** | 12 files use central, 82 use per-module. The central pattern's `logger.error("X")` produces `[ERROR] rcm_mc: X`. The per-module pattern's `logger.error("X")` from `auth.auth` produces `[ERROR] rcm_mc.auth.auth: X` (the LogRecord's `name` field). Format is `%(levelname)s] rcm_mc: %(message)s` — the per-module logger's name is NOT in the format. **Both patterns produce the same prefix in output.** Format is the same; only the LogRecord differs (which only matters if a sink filters by name). | Low |
| **Levels — debug-heavy** | 63/146 = 43% are debug. At INFO level (default) these are silent. **Operators see 38+35+6 = 79 visible calls (54%).** | (already flagged) |
| **logger.exception missing** | 0 of 146 calls preserve tracebacks. | High |
| **logger.warning bunched in some files, absent in others** | auth.py has 0 logger calls (Report 0021); packet_builder.py has 20 (all debug per Report 0020); server.py has many. **The same severity event is logged differently depending on file.** | High |
| **Some files use print() in non-CLI contexts** | Need to spot-check whether any `print()` in non-CLI paths (e.g. UI rendering, analysis pipelines) leaks to stderr. | Medium |
| **No structured logging** | Plain string format `[LEVEL] rcm_mc: X`. No JSON, no key=value pairs, no request ID. **Cannot grep for "all logs for request abc-123".** | Medium |

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR195** | **`__init__.py:3` is the load-bearing single line for logging configuration** | Removing or reordering `from .infra.logger import logger # noqa: F401` would un-configure the central named logger. **All 82 per-module loggers fall back to WARNING level + no handler.** Pre-merge: any branch that touches `__init__.py` must preserve this line. | **High** |
| **MR196** | **Two import patterns drift across branches** | A future branch that adds a new module will pick one pattern. If the convention isn't documented, drift is inevitable. **Recommend: pin Pattern A as canonical via CLAUDE.md update + a pre-commit hook.** | Medium |
| **MR197** | **Zero `logger.exception` calls — tracebacks never logged** | An intermittent production crash is forensically un-debuggable. Recommend: add `logger.exception(...)` in the 6 `logger.error` sites + the 71 server.py BLE001 sites. | **Critical** |
| **MR198** | **63 logger.debug calls silent at INFO** (cross-link Report 0020 MR152) | 43% of all logger calls are dropped in production. The packet_builder error-handling story (Report 0020) is the worst case but pattern-wide. **Recommend: review every logger.debug for a probable upgrade to logger.warning.** | **High** |
| **MR199** | **No env-var override for log level** | Operators cannot enable DEBUG mode at runtime. **Add `RCM_MC_LOG_LEVEL` env var support to `infra/logger.py`.** Cross-link Report 0019 MR149 (no env-var registry). | **High** |
| **MR200** | **No file/rotating handler — production logs depend on systemd or docker** | If the deploy environment doesn't capture stderr properly, logs are lost. | Medium |
| **MR201** | **No structured logging — cannot correlate request → log lines** | server.py emits `X-Request-Id` headers (per Report 0002 README claim) but no logger call binds that ID to a logged event. Forensic analysis requires manual time-window correlation. | **High** |
| **MR202** | **`auth/auth.py` has 0 logger calls** (Report 0021 MR163) | A failed-login spike is invisible in logs. Pre-merge: any branch that disables RateLimiter must add logging here first. | **High** |
| **MR203** | **`feature/workbench-corpus-polish` deletes `dashboard_page.py` (38 BLE001 + N logger calls)** | Per Report 0007 MR46. The branch removes whatever logger.* calls live in that file. Pre-merge: count the deleted logger.* calls to confirm we're not losing operational visibility. | Medium |
| **MR204** | **`print()` statements in non-CLI contexts could leak through to operators** | Need a spot-check that no `print()` leaks from a UI rendering or analysis pipeline. CLI files (cli.py, portfolio_cmd.py) are intentional. | Medium |
| **MR205** | **Mixed-vocabulary log messages** | `[ERROR] rcm_mc: unhandled GET /deal/abc: KeyError('deal_id')` vs `[ERROR] rcm_mc: backup file not found: /tmp/x.db.gz` vs `[WARNING] rcm_mc: ridge predictor unavailable: ...` — there's no convention for module names, error categories, or fields. **Recommend: a logging-conventions doc.** | Low |
| **MR206** | **`logger = logging.getLogger(__name__)` is correct Python idiom but creates 82 distinct logger objects** | Each is a different `Logger` instance. Per-handler attached to `"rcm_mc"` propagates correctly only because Python's logging hierarchy walks `name.split('.')`. If a future branch sets `propagate=False` on any per-module logger, **its messages stop appearing** in the central handler. | Medium |

## Dependencies

- **Incoming:** every module that emits a logger call (146 sites across rcm_mc/, plus 12 files using the central pattern); operators reading stderr / docker logs / systemd journal.
- **Outgoing:** stdlib `logging`. Zero third-party logging libs (no structlog, no loguru, no sentry-sdk).

## Open questions / Unknowns

- **Q1 (this report).** What does the production deploy capture from stderr? `RCM_MC/deploy/rcm-mc.service` (systemd) vs `docker-compose.yml` (docker logs) vs Azure VM journald — each captures stderr differently.
- **Q2.** Is there a `RCM_MC_LOG_LEVEL` env var I missed? Per Report 0019 inventory, no — but a future iteration should grep wider.
- **Q3.** Why is the 0-logger-calls pattern concentrated in auth.py? Was it intentional (security-related "don't leak username via log"), or is it just an oversight?
- **Q4.** Has any feature branch added `logger.exception(...)` calls? If yes, that's the right pattern to encourage.
- **Q5.** Does any test verify logging behavior? `pytest --log-cli-level=DEBUG` or `caplog` fixtures might be in use.
- **Q6.** Are there `print()` calls in UI pages (server.py routes) that leak to operators on stderr instead of HTML response?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0025** | **Audit `auth/audit_log.py`** — owed since Report 0021. Sister to logging in audit-trail context. | Resolves Report 0021 Q1. |
| **0026** | **Read `infra/backup.py`** — has 4 of 6 logger.error sites. The "best-instrumented" file in the codebase by error-logging. | Pattern study. |
| **0027** | **Audit `print()` density in non-CLI files** | Resolves MR204. |
| **0028** | **Cross-branch logger sweep** — does any ahead-of-main branch add `logger.exception` or new `logger.error` sites? | Catches forensic-improvement branches. |
| **0029** | **Read `RCM_MC/deploy/rcm-mc.service`** and `docker-compose.yml` to determine production stderr capture. | Resolves Q1. |
| **0030** | **Add `RCM_MC_LOG_LEVEL` env var support** to `infra/logger.py` (recommendation, not audit). | Resolves MR199. |
| **0031** | **Cross-cut audit: caching** — sister concern. `infra/cache.py` exists per Report 0015. | Companion cross-cut. |

---

Report/Report-0024.md written. Next iteration should: read `infra/backup.py` end-to-end — it carries 4 of the 6 `logger.error` calls in the entire codebase and is therefore the best-instrumented file by error-visibility; understanding its pattern gives the template for elevating other modules from `logger.debug` to `logger.error/warning` (closes Report 0020 MR152, Report 0021 MR163, MR197 here).

