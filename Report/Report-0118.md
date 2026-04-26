# Report 0118: Config Trace — `RCM_MC_DB` env var (+ PRAGMA closure)

## Scope

Traces `RCM_MC_DB` env var across read sites, defaults, overrides. Closes Report 0117 Q1 + RETRACTS MR673 high (PRAGMA foreign_keys enforcement). Sister to Reports 0019 (server.py env vars), 0028 (RCM_MC_PHI_MODE), 0042 (DOMAIN), 0079 (analysis_store env-free), 0090 (RCM_MC_SESSION_IDLE_MINUTES), 0109 (FORCE_COLOR/NO_COLOR/TERM), 0115 (RCM_MC_DATA_CACHE).

## Findings

### CLOSURE: PortfolioStore.connect() PRAGMA inventory (closes Report 0117 Q1)

`portfolio/store.py:84-107` — `PortfolioStore.connect()`:

```python
con = sqlite3.connect(self.db_path)
con.row_factory = sqlite3.Row
con.execute("PRAGMA busy_timeout = 5000")
# Prompt 21: FK enforcement is off by default in SQLite. We opt
# in on every connection so orphan inserts into
# ``deal_overrides`` / ``analysis_runs`` / ``mc_simulation_runs``
# / ``generated_exports`` raise IntegrityError immediately
# instead of silently creating dangling rows.
con.execute("PRAGMA foreign_keys = ON")
```

**`PRAGMA foreign_keys = ON` IS set on every connection (line 103).** **MR673 RETRACTED.**

The FK on `mc_simulation_runs.deal_id → deals(deal_id) ON DELETE CASCADE` (Report 0117) IS enforced.

**Plus `PRAGMA busy_timeout = 5000`** (5s) — Reports 0017 + 0008 mentioned this; confirmed here.

### NEW unmapped tables (per the FK comment line 100-101)

The PRAGMA comment names **4 tables with FKs**:

| Table | Status |
|---|---|
| `deal_overrides` | **NEW UNMAPPED TABLE** — never reported |
| `analysis_runs` | Report 0077 (possibly missed FK) |
| `mc_simulation_runs` | Report 0117 ✓ |
| `generated_exports` | named (Report 0110, not yet walked) |

**MR677 high**: `deal_overrides` table never reported in 117 prior iterations. Add to schema-walk backlog.

**MR678 medium**: Report 0077 may have missed an FK on `analysis_runs`. Re-verify.

### `RCM_MC_DB` read-site inventory

`grep -n "RCM_MC_DB" RCM_MC/rcm_mc/`:

| Line | File | Pattern |
|---|---|---|
| `server.py:94, 96` | server.py | `db_path: str = os.environ.get("RCM_MC_DB") or os.path.expanduser("~/.rcm_mc/portfolio.db")` |
| `pe_cli.py:277` | pe_cli.py | `default=os.environ.get("RCM_MC_DB") or "portfolio.db"` |
| `ui/comparable_outcomes_page.py:302` | UI page | `db_path = _os.environ.get("RCM_MC_DB", ...)` |
| `ui/sponsor_detail_page.py:216` | UI page | `db_path = _os.environ.get("RCM_MC_DB", "/tmp/rcm_mc.db")` |

**4 read sites.** Per Report 0090: ServerConfig is the canonical config object (5 fields). Other 3 sites read directly via `os.environ.get()`.

### Default fallback inconsistency

| Read site | Default if `RCM_MC_DB` unset |
|---|---|
| server.py:96 (ServerConfig) | `~/.rcm_mc/portfolio.db` (expanded HOME) |
| pe_cli.py:277 (PE CLI) | `portfolio.db` (cwd-relative) |
| ui/comparable_outcomes_page.py:302 | (TBD — partial read) |
| **ui/sponsor_detail_page.py:216** | **`/tmp/rcm_mc.db`** |

**4 different defaults.** `/tmp/rcm_mc.db` is particularly suspect — `/tmp` is ephemeral on most systems. **MR679 below.**

### Write sites

`RCM_MC_DB` is **read-only** in the codebase. Set externally via:
- shell `export RCM_MC_DB=...`
- Docker env (per Report 0033 + 0041)
- systemd unit env (per CLAUDE.md deploy hints)

**No `os.environ["RCM_MC_DB"] = ...` writes anywhere.** Clean.

### Test overrides

Tests typically construct `PortfolioStore(temp_db_path)` directly rather than setting the env var (per Report 0008 portfolio.store coverage). Some tests may use `monkeypatch.setenv("RCM_MC_DB", ...)` — `grep "RCM_MC_DB" tests/` not run this iteration.

### Where it surfaces to users

- **CLI**: `rcm-mc serve --db <path>` overrides; if not provided, falls back to `RCM_MC_DB` env, then default.
- **UI**: certain pages (sponsor_detail, comparable_outcomes) read directly — bypassing ServerConfig. **Architectural inconsistency.** **MR680 below.**

### Cross-link to Report 0090 ServerConfig

Per Report 0090: ServerConfig has only 5 fields (`db_path`, `outdir`, `title`, `auth_user`, `auth_pass`). `db_path` is one of them.

**But** `ui/sponsor_detail_page.py:216` and `ui/comparable_outcomes_page.py:302` re-read `RCM_MC_DB` from `os.environ` directly — bypassing the ServerConfig object that `RCMHandler.config` exposes.

If a test sets `ServerConfig.db_path = ...` but doesn't set `os.environ["RCM_MC_DB"]`, those UI pages will read **the wrong DB** silently. **MR680 high.**

### Cross-link to project env-var registry (cumulative)

Env vars discovered across audit:

| Var | Reports | Purpose |
|---|---|---|
| `RCM_MC_DB` | 0090, 0118 (this) | DB path |
| `RCM_MC_AUTH` | 0090 (server.py:101 cited) | HTTP Basic creds |
| `RCM_MC_PHI_MODE` | 0028 | PHI redaction |
| `RCM_MC_SESSION_IDLE_MINUTES` | 0090 | session timeout |
| `RCM_MC_NO_PORTFOLIO` | 0109 (cli.py:1016) | skip portfolio register |
| `RCM_MC_DATA_CACHE` | 0115 | CMS download cache root |
| `DOMAIN` | 0042 | deployment domain |
| `FORCE_COLOR`, `NO_COLOR`, `TERM` | 0109 | terminal styling |
| `HOME`, `USERPROFILE` | 0115 (cache fallback) | OS-default home |

**~10+ env vars.** No central registry; CLAUDE.md doesn't enumerate.

### CLAUDE.md mention

CLAUDE.md "Running" section says:
```
.venv/bin/python -m rcm_mc.portfolio_cmd --db p.db ...
rcm-mc serve --db p.db --port 8080
```

The `--db` flag is the documented path. **Env var `RCM_MC_DB` is implicit** — reads it when `--db` not specified. CLAUDE.md doesn't name the env var.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR673-RETRACTED** | **PRAGMA foreign_keys = ON IS set** at portfolio/store.py:103 — Report 0117 MR673 retracted. | (correction) |
| **MR677** | **`deal_overrides` table never reported** — discovered via PRAGMA comment | Add to schema-walk backlog. **HIGH-PRIORITY**. | **High** |
| **MR678** | **Report 0077 (`analysis_runs`) may have missed an FK** | Per portfolio/store.py:100-101 comment, analysis_runs has an FK that should have been visible. Re-verify. | Medium |
| **MR679** | **4 different defaults for missing `RCM_MC_DB`** | server.py: `~/.rcm_mc/portfolio.db`; pe_cli.py: `portfolio.db` (cwd); sponsor_detail_page.py: `/tmp/rcm_mc.db`. **`/tmp` is ephemeral**. | **High** |
| **MR680** | **2 UI pages re-read `RCM_MC_DB` directly, bypassing ServerConfig** | `ui/sponsor_detail_page.py:216`, `ui/comparable_outcomes_page.py:302`. Test setting `ServerConfig.db_path` would NOT propagate. **Architectural violation** (cross-link Report 0111 MR626 store-only-talks-to-SQLite project-wide pattern). | **High** |
| **MR681** | **No central env-var registry** | ~10+ env vars across the codebase; CLAUDE.md doesn't enumerate them. Onboarding gap. | Medium |
| **MR682** | **`RCM_MC_DB` env var name not documented in CLAUDE.md "Running" section** | Doc only mentions `--db` flag. | Low |
| **MR683** | **`PRAGMA foreign_keys = ON` per-connection — possible perf overhead** | Each `with store.connect():` opens, sets, runs — minor cost. Acceptable; not flagged as blocker. | (advisory) |

## Dependencies

- **Incoming:** server start (`build_server`), CLI (`rcm-mc`, `rcm-mc-pe`), 2 UI pages.
- **Outgoing:** `os.environ`, sqlite3, all SQLite-using modules (per Report 0111 MR626 8+).

## Open questions / Unknowns

- **Q1.** Does Report 0077's `analysis_runs` schema actually have an FK that was missed? Re-read schema body.
- **Q2.** What's in `deal_overrides` — schema, fields, write sites?
- **Q3.** Does `tests/conftest.py` (or similar) set `RCM_MC_DB` for test isolation, or rely on direct PortfolioStore construction?
- **Q4.** What does `ui/comparable_outcomes_page.py:302` do with the db_path — does it construct a fresh PortfolioStore, or use the request's existing one?
- **Q5.** Should the 4 inconsistent defaults be unified (e.g., always `~/.rcm_mc/portfolio.db`)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0119** | Schema-walk `deal_overrides` (closes Q2 + MR677). |
| **0120** | Re-read `analysis_runs` schema for FK (closes Q1 + MR678). |
| **0121** | Read `infra/data_retention.py` (still owed, Report 0117 MR672). |
| **0122** | Map `rcm_mc_diligence/` separate package (carried 13+ iterations). |

---

Report/Report-0118.md written.
Next iteration should: schema-walk `deal_overrides` table (newly discovered, MR677 high) — closes Q2.
