# Report 0139: Env-Var Sweep — `rcm_mc/cli.py`

## Scope

Env-var grep on `RCM_MC/rcm_mc/cli.py` (1,252 lines) — the 14-iteration-deferred file owed since Report 0003. Sister to Reports 0019, 0028, 0042, 0049, 0079, 0090, 0109, 0115, 0118, 0138.

## Findings

### Env-var inventory (cli.py)

`grep -nE "os\.environ|os\.getenv" cli.py`:

| Line | Pattern | Env var |
|---|---|---|
| 1016 | `os.environ.get("RCM_MC_NO_PORTFOLIO") == "1"` | `RCM_MC_NO_PORTFOLIO` |
| 1028 | `os.path.expanduser("~/.rcm_mc/portfolio.db")` | (no env-var, but `~` resolves via HOME/USERPROFILE) |

**Only 1 explicit env-var read** in 1,252 lines. Surprisingly thin — almost all CLI config flows via argparse, not env.

### `RCM_MC_NO_PORTFOLIO` semantics (line 1014-1017)

```python
if bool(getattr(args, "no_portfolio", False)):
    return
if os.environ.get("RCM_MC_NO_PORTFOLIO") == "1":
    return
```

**Belt-and-braces opt-out**: either `--no-portfolio` flag OR `RCM_MC_NO_PORTFOLIO=1` env var skips the portfolio-snapshot registration. Per docstring lines 1011-1012:

> "Degrades silently (stderr warning) on any persistence error — portfolio tracking is a convenience, not a critical path of run."

**Behavior**: when set, `register_snapshot` is skipped. Cross-link Report 0103 (job_queue: `submit_run` has `portfolio_register: bool = True` parameter) — same opt-out at job-queue layer.

### Default fallback

| Source | Default |
|---|---|
| Env var unset | None (key not present → `.get(...) == "1"` is False) |
| Env var set to anything OTHER than `"1"` | NOT triggered (e.g., `RCM_MC_NO_PORTFOLIO=true` does NOT opt out) |
| Env var set to `"1"` | opt-out |

**Strict equality check** — only literal `"1"` triggers the skip. `RCM_MC_NO_PORTFOLIO=true`, `=yes`, `=on` all fail. **MR786 below.**

### What fails if missing

NOTHING fails. The env var is OPT-OUT — its absence is the default behavior (portfolio snapshot recorded).

### Cross-link to env-var registry (Reports 0019, 0028, 0042, 0049, 0079, 0090, 0109, 0115, 0118)

Cumulative env vars known across the project:

| Var | Source report |
|---|---|
| `RCM_MC_DB` | 0090, 0118 |
| `RCM_MC_AUTH` | 0090 (server.py:101 cited) |
| `RCM_MC_PHI_MODE` | 0028 |
| `RCM_MC_SESSION_IDLE_MINUTES` | 0090 |
| **`RCM_MC_NO_PORTFOLIO`** | **0139 (this — but discovered originally Report 0109 line 1016)** |
| `RCM_MC_DATA_CACHE` | 0115 |
| `DOMAIN` | 0042 |
| `FORCE_COLOR`, `NO_COLOR`, `TERM` | 0109 |
| `HOME`, `USERPROFILE` | 0115 |
| `RCM_MC_UI_VERSION` (post-merge) | 0127 |
| `EXPORTS_BASE` (post-merge) | 0127 |
| `CHARTIS_UI_V2` (per Report 0127 _chartis_kit) | 0127 |
| `AZURE_VM_HOST/USER/SSH_KEY` | 0116 deploy.yml |
| `SSH_KEY` (per origin/main divergent deploy.yml) | 0120 |

**~14 env vars total.** CLAUDE.md enumerates **none** (Report 0118 MR681).

### `cli.py` overall surface

1,252 lines. Per Report 0091 #1 backlog ("`cli.py` 1,252 lines — owed since Report 0003"). This iteration covers ONLY env-var sites. Module structure, public API, error handling all unread.

### Importers of cli.py

`grep "from rcm_mc.cli import\|import rcm_mc.cli"` — not run this iteration. Per Report 0103 (`infra/job_queue.py:_default_sim_runner` calls `rcm_mc.cli.run_main`) — at least 1 internal importer.

`pyproject.toml` console-script: `rcm-mc = "rcm_mc.cli:main"` (per Report 0086).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR786** | **`RCM_MC_NO_PORTFOLIO` strict equality `== "1"`** — `=true`/`=yes`/`=on` don't trigger | Operators expecting standard truthy-string semantics get surprised. Should be `os.environ.get(...).lower() in ("1", "true", "yes", "on")`. | Low |
| **MR787** | **cli.py only reads ONE env var in 1,252 lines** — most config via argparse | Closes Report 0091 #1 backlog (env-var aspect only). Module body still 99% unaudited. | (advisory) |

## Dependencies

- **Incoming:** `rcm-mc` console script (per pyproject), `infra/job_queue._default_sim_runner` (per Report 0103).
- **Outgoing:** `os.environ`, `argparse`, many internal modules (TBD — full body unread).

## Open questions / Unknowns

- **Q1.** What's `cli.py`'s argparse surface? How many subcommands?
- **Q2.** Does `cli.py` have other indirectly-env-influencing code paths (e.g. `os.environ.copy()` to subprocesses)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0140** | Error-handling audit (next iteration). |
| **0141** | Security spot-check. |
| **0142** | Read `cli.py` head 100 lines (module structure + argparse setup). |

---

Report/Report-0139.md written.
