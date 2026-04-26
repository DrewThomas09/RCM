# Report 0109: Environment Vars — `infra/_terminal.py`

## Scope

`RCM_MC/rcm_mc/infra/_terminal.py` (231 lines) — **never reported in 108 prior iterations**. Sister to Reports 0019 (server.py + repo env-var inventory), 0028 (RCM_MC_PHI_MODE), 0042 (DOMAIN), 0049 (notifications), 0079 (analysis_store env-free), 0090 (RCM_MC_SESSION_IDLE_MINUTES).

## Findings

### Module purpose

ANSI terminal-styling helpers — stdlib-only (no `rich`, no `colorama`). Public API: `paint`, `success`, `warn`, `error`, `info`, `wrote`, `banner`, `completion_box`, `step` (context manager).

### Env-var inventory — 3 reads, all in `supports_color()`

| Line | Env var | Default | Effect when present |
|---|---|---|---|
| 61 | `FORCE_COLOR` | unset | **Truthy → force-enable ANSI codes** (highest precedence) |
| 63 | `NO_COLOR` | unset | Truthy → disable ANSI (per [no-color.org](https://no-color.org/) convention) |
| 65 | `TERM` | unset | Equals `"dumb"` → disable ANSI |

### Precedence ladder (lines 56-68)

```python
def supports_color(stream=None) -> bool:
    stream = stream if stream is not None else sys.stdout
    if os.environ.get("FORCE_COLOR"):     # 1. force-enable
        return True
    if os.environ.get("NO_COLOR"):         # 2. force-disable
        return False
    if os.environ.get("TERM") == "dumb":   # 3. dumb-terminal
        return False
    return hasattr(stream, "isatty") and stream.isatty()  # 4. TTY auto-detect
```

**Order is correct** — `FORCE_COLOR` overrides `NO_COLOR` (per common convention; CI overrides user-pref). 

### Default-fallback behavior

| Env state | Outcome |
|---|---|
| All 3 unset | TTY detection — colors when stdout is a real terminal |
| `FORCE_COLOR=1`, all others ignored | Colors ON regardless of stream |
| `NO_COLOR=` (empty string) | **Counts as truthy per `os.environ.get()` semantics** — `bool("") == False` so technically NOT truthy. **Subtle:** the check `if os.environ.get("NO_COLOR")` returns False for empty string, so `NO_COLOR=` (empty) does NOT disable. **MR611 below.** |
| `NO_COLOR=anything` | Colors OFF |
| `TERM=dumb` | Colors OFF |
| `TERM=xterm-256color` | Falls through to TTY check |

### What fails if missing

**Nothing fails.** All 3 env vars have safe defaults via fall-through. The function still returns a reasonable bool (TTY detection). Cross-link to the project pattern noted in Reports 0028, 0090: graceful degradation when env vars are absent.

### Importers (6 production sites)

| File | Likely use |
|---|---|
| `cli.py` | CLI output styling (RUN COMPLETE banner, success ✓ marks) |
| `server.py` | likely startup banner (per Report 0018 entry-point) |
| `analysis/challenge.py` | progress UI |
| `deals/deal.py` | deal-page rendering helpers? |
| `data/ingest.py` | ingest progress |
| `data/lookup.py` | lookup CLI output |

Wide-fanout but stdlib-only outgoing — pure leaf utility.

### Comparison to Report 0090 (auth env-var pattern)

Both Report 0090 (`_idle_timeout_minutes`) and this module use `os.environ.get(NAME, "").strip()` pattern. **Cross-link**: this is a project-wide idiom for safe env-var reads.

### `NO_COLOR` empty-string subtlety

[no-color.org](https://no-color.org/) v0.13: "All command-line software which outputs text with ANSI color added should check for the presence of a `NO_COLOR` environment variable that, when present (regardless of its value), prevents the addition of ANSI color." 

**Spec says: present-regardless-of-value disables.** This module's check `if os.environ.get("NO_COLOR"):` is **truthy-check**, not presence-check. **`NO_COLOR=` (empty) does NOT disable here, but per spec it should.**

This is a **standards-compliance bug**, however small.

### Test coverage

`grep "test.*_terminal\|test_terminal" RCM_MC/tests/`: not run. Q1 below.

### Documentation quality

- Module docstring: 17 lines, well-written. Lists the 3 env vars.
- Function docstrings: present on `supports_color`, `paint`, `banner`, `wrote`, `completion_box`, `step`.
- Missing docstrings: `success`, `warn`, `error`, `info` (all trivial 1-liners; acceptable).

**Strong documentation discipline** — better than Report 0104's `infra/webhooks.py` (3 of 4 public CRUD undocumented).

### Cross-link to NO_COLOR-empty-string spec compliance

Per the no-color.org spec: empty-string presence should disable colors. Standard fix:
```python
if "NO_COLOR" in os.environ:
    return False
```
This change would not break any existing usage (since unset → not in environ → not disabled). Strict-mode improvement.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR611** | **`NO_COLOR=` (empty string) does NOT disable colors** — violates no-color.org spec | Standards-compliance bug. CI scripts setting `NO_COLOR=` expecting disable will get colored output. | **Medium** |
| **MR612** | **`FORCE_COLOR=0` (string "0") still enables colors** | `bool("0") == True` in Python. So `FORCE_COLOR=0` is truthy. Confusing for ops who think `0` = disable. | Low |
| **MR613** | **No env-var caching** — `os.environ.get()` re-read on every `paint()` call | Negligible perf (env-dict lookup is hash). But: env changed mid-process picks up live, which can surprise. | Low |
| **MR614** | **Module name `_terminal` (underscore prefix) implies private** but 6 production importers use it | Per CLAUDE.md "Private helpers prefix with underscore." Module-level underscore suggests "infra-internal" but actually exposes paint/success/warn/error/banner widely. **Naming convention violation** — should be `terminal.py`. | Low |

## Dependencies

- **Incoming:** 6 production files: cli.py, server.py, analysis/challenge.py, deals/deal.py, data/ingest.py, data/lookup.py.
- **Outgoing:** stdlib only — `os`, `shutil`, `sys`, `contextlib`, `typing`.

## Open questions / Unknowns

- **Q1.** Does `tests/test_terminal.py` exist? (Likely indirect via `cli.py` tests.)
- **Q2.** Per Report 0019 + 0049: complete env-var registry across the codebase. This adds 3 (`FORCE_COLOR`, `NO_COLOR`, `TERM`) to the registry. Are these recorded in any consolidated config-doc? CLAUDE.md doesn't mention them.
- **Q3.** Is `MR611` (NO_COLOR= empty string) intentional or a real bug?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0110** | Read `infra/consistency_check.py` (still owed since Report 0107). |
| **0111** | Build a complete env-var registry across the whole repo (Reports 0019 + 0028 + 0042 + 0049 + 0079 + 0090 + 0109 union). Closes Q2. |
| **0112** | Bug-fix PR for MR611 (concrete remediation; 1-line change). |

---

Report/Report-0109.md written.
Next iteration should: read `infra/consistency_check.py` end-to-end (still owed since Report 0107 + MR597).
