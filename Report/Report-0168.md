# Report 0168: Entry Point — `rcm-mc data {refresh|status}` CLI Subcommand

## Scope

Traces `rcm-mc data` subcommand from invocation through call stack. Sister to Reports 0018, 0048, 0078, 0102, 0108, 0138 (entry-point traces). Cross-link Report 0163 cli.py public surface.

## Findings

### Layer 1 — Shell

```bash
rcm-mc data refresh [--db p.db] [--source hcris] [--interval-days 30]
rcm-mc data status [--db p.db]
```

Per Report 0086: `rcm-mc` console script → `rcm_mc.cli:main`.

### Layer 2 — `main()` dispatcher (cli.py:1252)

Per Report 0163: `main(argv)` routes argv. At line 1305:
```python
return data_main(argv[1:], prog="rcm-mc data")
```

So `rcm-mc data refresh ...` → `argv[0] == "data"` → calls `data_main(["refresh", ...])`.

### Layer 3 — `data_main()` (cli.py:1130)

```python
def data_main(argv: list, prog: str = "rcm-mc data") -> int:
    """``rcm-mc data {refresh|status} [--source X]``

    Refresh or inspect the four CMS public-data sources that feed the
    hospital_benchmarks table (HCRIS / Care Compare / Utilization /
    IRS 990). ``status`` is read-only; ``refresh`` may hit the network
    unless downloads are cached.
    """
```

**Note**: docstring says **"the four CMS public-data sources"** — but per Report 0102 there are **7** known sources (`KNOWN_SOURCES`). **Stale docstring.** **MR893 below.**

argparse setup:
- subparser `refresh`: `--db`, `--source` (default "all"), `--interval-days` (default 30)
- subparser `status`: `--db` only

Default DB path: `"portfolio.db"` (cwd-relative). Cross-link Report 0118 MR679 high — adds yet another db-default path. **6th distinct default now.**

### Layer 4 — `data_refresh` module (per Report 0102)

```python
from .portfolio.store import PortfolioStore
from .data import data_refresh as dr
store = PortfolioStore(args.db)

if args.action == "status":
    dr.schedule_refresh(store, interval_days=30)
    dr.mark_stale_sources(store)
    rows = dr.get_status(store)
```

For `status`:
1. `schedule_refresh(store, interval_days=30)` — seeds `data_source_status` (per Report 0107)
2. `mark_stale_sources(store)` — flips overdue → STALE
3. `get_status(store)` — read

For `refresh`:
- (TBD past sample) likely calls `dr.refresh_all_sources(store, sources=...)`

### Layer 5 — `data_refresh.refresh_all_sources` (Report 0102)

Per Report 0102 hop 4-9: orchestrates 7 lazy CMS source-refreshers. **The CLI path bypasses HTTP rate-limit** per Report 0102 MR561 / Report 0115 MR648.

### Cross-link to Report 0102

Report 0102 traced the HTTP route `POST /api/data/refresh/<source>`. **This iteration traces the CLI alternative.** Same downstream (`refresh_all_sources` per Report 0102).

**Differences**:
| | HTTP route | CLI |
|---|---|---|
| Rate-limit | YES (1/hr per source) | **NO** |
| Auth | session cookie required | none |
| Caller | partner browser | operator shell |

### Cross-link to Report 0107 + 0123 cron concern

Per Report 0123 + 0107 MR602/MR703: `mark_stale_sources` and `enforce_retention` are operator-invoked, no auto-cron. **`rcm-mc data status` triggers `mark_stale_sources` SIDE EFFECT** — calling status mutates state. Cross-link Report 0017/0107 idempotency.

**MR894 below.**

### Default `--source all`

If user runs `rcm-mc data refresh` without `--source`, all 7 sources refresh sequentially. Per Report 0102 hop 9 + 0144 retry-helper-absent: 7 single-shot fetches. If any fails, MAY skip subsequent (TBD per Report 0144 + 0102 broad-except).

### Path validation on `--db`

Per Report 0137 MR777 + 0136 MR772: path-traversal class concern. `--db /etc/something.db` would be accepted.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR893** | **`data_main` docstring says "four CMS public-data sources"** but per Report 0102 there are **7** | Stale doc. Cross-link Report 0093 MR503 critical doc rot. | Low |
| **MR894** | **`rcm-mc data status` has SIDE EFFECTS** (mark_stale + schedule_refresh) | "Status" is conventionally read-only. Calling status mutates `data_source_status` table. Cross-link Report 0107 + 0123. | **Medium** |
| **MR895** | **CLI path bypasses HTTP rate-limit (Report 0102 MR561 + Report 0115 MR648)** | Carried. Operator shell can hammer CMS. | (carried) |
| **MR896** | **6th distinct DB-path default** (`portfolio.db` cwd-relative in `data_main`) | Cross-link Report 0118 MR679 + Report 0138 MR782 + Report 0163. | High |

## Dependencies

- **Incoming:** developer/operator shell.
- **Outgoing:** PortfolioStore, data_refresh (schedule_refresh + mark_stale_sources + get_status + refresh_all_sources).

## Open questions / Unknowns

- **Q1.** Why does `data_main` default `--db portfolio.db` (cwd-relative) when ServerConfig defaults `~/.rcm_mc/portfolio.db` (Report 0118)?
- **Q2.** Does `refresh` action also have side-effects on top of refresh_all_sources?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0169** | Env-var sweep (in flight). |
| **0170** | Error-handling (in flight). |

---

Report/Report-0168.md written.
