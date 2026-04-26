# CLAUDE.md

Guidance for AI assistants working on the RCM-MC codebase.

## What this project is

**RCM-MC** is an analytics platform for healthcare private-equity
diligence and portfolio operations. It combines:

- A **Monte Carlo simulator** that projects revenue-cycle-management
  (RCM) initiative outcomes on a healthcare deal.
- A **PE-math layer** that turns simulation outputs into bridge /
  MOIC / IRR / covenant math.
- A **portfolio-operations console** (alerts, cohorts, deal tracking,
  LP reporting, owner/deadline workflow) that a partner uses daily.

Users are PE partners and their associates. Deployment is a Python
package + a built-in HTTP server — no external services, no Docker
required for local use.

## Tech stack

- **Python 3.14** (stdlib-heavy; pandas + numpy + matplotlib are the
  only runtime deps beyond stdlib)
- **SQLite** via `sqlite3` stdlib — ~89 tables across all subpackages
  (core portfolio + data_public/ CMS loaders + ml/ audit/predictions +
  engagement/ + ai/ caching), `busy_timeout=5000`, idempotent
  `CREATE TABLE IF NOT EXISTS` migrations. To enumerate the live
  registry: `grep -rh "CREATE TABLE IF NOT EXISTS" rcm_mc/ | grep -oE
  "EXISTS [a-z_][a-z0-9_]*" | sort -u`
- **HTTP** via `http.server.ThreadingHTTPServer` — no Flask / FastAPI
- **HTML** server-rendered (string concatenation + a shared shell).
  No SPA, no client-side framework. One small vanilla-JS shim for
  CSRF-patching forms.
- **Auth** via stdlib `hashlib.scrypt` + session cookies. No
  third-party identity provider.
- **CLI** via stdlib `argparse`, entry-pointed through
  `rcm-mc` / `rcm-mc portfolio` / `rcm-mc pe`.
- **Tests** via stdlib `unittest`, driven by `pytest`.
  **2,878 passing tests**.

Zero new runtime dependencies have been added in any recent work.

## Architecture

```
Browser / CLI / Cron
        ↓
rcm_mc/server.py         ← HTTP app (auth, CSRF, rate-limit, audit)
rcm_mc/cli.py            ← top-level CLI
rcm_mc/portfolio_cmd.py  ← portfolio subcommands
        ↓
feature subpackages      ← alerts/, deals/, portfolio/, auth/, etc.
        ↓
core + pe + rcm          ← simulator, PE-math, RCM math
        ↓
rcm_mc/portfolio/store.py ← SQLite connection manager
        ↓
SQLite file on disk
```

Every layer calls down, never up. The store is the only module
that talks to SQLite directly.

## Build phases

The product is built in three phases; we are currently polishing
Phase 3.

### Phase 1 — Regression prediction engine *(complete)*
Probabilistic models of per-KPI outcomes (initial-denial rate,
final-write-off, clean-DAR, NPSR). Fit to priors via
`rcm_mc/calibration.py` (moves to `rcm_mc/core/` in the refactor).

### Phase 2 — Monte Carlo EBITDA simulation *(complete)*
- `rcm_mc/simulator.py` runs N simulations per deal.
- `rcm_mc/pe_math.py` computes value-creation bridge, MOIC, IRR,
  covenant headroom.
- Scenario layering via `rcm_mc/scenario_*.py`.

### Phase 4 — Packet-centric analysis *(current)*
Every UI page, API endpoint, and export renders from a single
`DealAnalysisPacket` instance (see
[`docs/ANALYSIS_PACKET.md`](docs/ANALYSIS_PACKET.md)). Nothing renders
independently — this is the load-bearing invariant for audit and UI
consistency. Built by `rcm_mc/analysis/packet_builder.py`, cached in
the `analysis_runs` table, exported via `rcm_mc/exports/packet_renderer.py`.

Key modules added in Phase 4:
- `rcm_mc/analysis/packet.py` — the dataclass + JSON round-trip
- `rcm_mc/analysis/packet_builder.py` — 12-step orchestrator
- `rcm_mc/analysis/completeness.py` — registry + grade
- `rcm_mc/analysis/risk_flags.py`, `diligence_questions.py`
- `rcm_mc/ml/ridge_predictor.py` + `conformal.py`
- `rcm_mc/pe/rcm_ebitda_bridge.py` — 7-lever bridge
- `rcm_mc/mc/ebitda_mc.py` — two-source Monte Carlo
- `rcm_mc/provenance/graph.py` + `explain.py`
- `rcm_mc/exports/packet_renderer.py`
- `rcm_mc/ui/analysis_workbench.py` — Bloomberg-style workbench at `/analysis/<deal_id>`

CLI surface: `rcm-mc analysis <deal_id>` (build/load packet),
`rcm-mc data {refresh|status}` (CMS public-data loaders).

### Phase 3 — Portfolio intelligence *(in progress — polish)*
Partner-facing operations:
- **Alerts lifecycle**: fire → ack/snooze → history (age) → escalate
  → returning-badge when snooze expires.
- **Cohorts, watchlists, owners, deadlines, notes, tags**: slicing
  and workflow.
- **Health score**: composite 0-100 per deal with trend sparkline.
- **LP digest**: `/lp-update`, partner-ready HTML export.
- **Simulation queue**: in-memory single-worker queue, per-deal
  rerun shortcut via stored `actual.yaml`/`benchmark.yaml` paths.
- **Multi-user security**: scrypt passwords, sessions, CSRF,
  rate-limited login, unified audit log.

## Coding conventions

### UI
- **Dark mode is the default** — pages should render cleanly on
  dark backgrounds. Primary accent is the Chartis blue
  `var(--accent) = #1F4E78`. Severity palette: green `#10B981`,
  amber `#F59E0B`, red `#EF4444`.
- **Monospace numerics**: use `font-variant-numeric: tabular-nums`
  on every cell/value that is a number so columns align. Already
  built into `_ui_kit.py`'s `.kpi-value` and `.num` classes.
- **Every page uses the shared shell** `rcm_mc/_ui_kit.py::shell()`
  (moves to `rcm_mc/ui/` in the refactor). Never build bespoke
  HTML pages.
- **All forms POST** (never GET for state-changing action) and the
  shared CSRF-patching JS automatically adds the token.

### Number formatting
- **Financial figures → 2 decimal places** (`$450.25M`,
  `$1,204.50`). Never 1 or 3. If the value is an integer count
  (deal count, day count), no decimals.
- **Percentages → 1 decimal place** (`15.3%`, `-4.1%`). Sign
  always shown when the sign carries meaning (`+4.1%` beat,
  `-4.1%` miss). Never 0 or 2 decimals.
- **Multiples → 2 decimal places with `x` suffix** (`2.50x`).
- **Dates → ISO-like** (`2026-04-15`, `2026Q1` for quarter).
  Never US-style `4/15/2026`.
- **Times → UTC ISO** (`2026-04-15T10:00:00+00:00`). Any wall-time
  display uses `date.today()` only via `datetime.now(timezone.utc).date()`.

### Python style
- **No new runtime dependencies** without explicit discussion.
- **Parameterised SQL only** — never f-string values into SQL.
- **`BEGIN IMMEDIATE`** around any check-then-write sequence in
  SQLite (see `deal_deadlines.add_deadline`, `auth.delete_user`,
  `watchlist.toggle_star`).
- **`html.escape()` every user-supplied string** before putting it
  in HTML. Attribute context escapes `"`; content context escapes
  `<>&`.
- **`_clamp_int` every integer query param** — never `int(qs[...])`
  unchecked.
- **Datetimes must be timezone-aware** (`datetime.now(timezone.utc)`)
  unless comparing to other naive times.
- **Private helpers prefix with underscore** (`_ensure_table`,
  `_validate_username`). Module-private state prefixed too
  (`_EVALUATOR_FAILURES`).
- **Docstrings explain *why*, not *what***. The code says what;
  the docstring explains the constraint or the prior incident that
  drove the decision.

### Testing
- **Each feature has a `test_<feature>.py` file** in `tests/`.
- **Bug fixes have `test_bug_fixes_b<N>.py`** and a corresponding
  regression assertion.
- **Multi-step workflows tested end-to-end** via a real HTTP server
  on a free port, using `urllib.request`.
- **No mocks for our own code** — always exercise the real path.
  `unittest.mock` is only acceptable for external stubs (e.g.,
  simulating a failing `log_event` to test silent-failure paths).
- **Tests must be order-independent** — class-level state (e.g.,
  the login-fail log on `RCMHandler`) is reset in `setUp`/`tearDown`.

## Current state

### What works end-to-end (UI + API + CLI)
- Alerts — fire / ack / snooze / age / escalate / returning-badge
- Deal page — snapshot trail, variance, initiatives, notes, tags,
  owner, deadlines, health score + trend sparkline, rerun simulation
- Deal lifecycle — create / archive / unarchive / clone / delete
  (cascade across 23 child tables) / pin / validate / IC checklist
- Cohorts, owners, watchlist, deadlines, notes search (+ tag filter)
- Variance drill-down, escalations, LP digest (HTML + download)
- Compare deals (side-by-side + EBITDA trajectory SVG + JSON API)
- Similar deals — find comparable deals by numeric profile distance
- Personal dashboard `/my/<owner>` with pulse + health mix
- Audit log + admin user management + per-deal audit trail
- CSV exports everywhere (defanged for Excel formula injection)
- Bulk import (JSON array + CSV) / bulk operations (archive/delete/tag)
- Database backup (`/api/backup`) + system info (`/api/system/info`)
- Multi-user auth (sessions + CSRF + rate-limit + idempotency keys)
- CORS + gzip compression + ETags + pagination + sorting
- Dark mode CSS + print-friendly workbench + keyboard shortcuts
- 52-path OpenAPI spec (56 methods) + Swagger UI + `/api` route index
- Schema migration registry (auto-run on startup)
- Request observability: p50/p95/p99 + X-Request-Id + X-Response-Time

### What is CLI-only (no UI yet)
All CLI-only items have been closed — every feature has a web
API equivalent. The CLI remains available for scripting/cron.

### What needs UI
All four original UI gaps have been closed:
- ~~Scenario explorer~~ — `/scenarios` page + `/api/scenarios`
- ~~Peer comparison~~ — `/api/deals/<id>/peers`
- ~~Run history~~ — `/runs` page + `/api/runs`
- ~~Calibration~~ — `/calibration` page + `/api/calibration/priors`

### Known limitations (by design)
- Single-machine deployment. No clustering, no Postgres path.
- Session tokens invalidate on server restart (per-process CSRF
  secret). Partners reopen login tab after a restart.
- `live mode` meta-refresh doesn't extend session TTL.
- In-memory job queue; jobs lost on restart. OK for partner-driven
  rerun (they'll just click rerun again) but not for critical cron
  runs — those should go via the CLI directly.

## Package layout (post-refactor)

```
rcm_mc/
├── core/         simulator, kernel, distributions, calibration, rng
├── pe/           pe_math, pe_integration, hold_tracking, value_plan, …
├── rcm/          claim_distribution, initiatives, initiative_*
├── data/         hcris, irs990, sources, lookup, ingest, intake, data_scrub
├── portfolio/    store, portfolio_snapshots, portfolio_dashboard, …
├── deals/        deal, deal_notes, deal_tags, deal_owners, deal_deadlines,
│                 deal_sim_inputs, health_score, note_tags, watchlist
├── alerts/       alerts, alert_acks, alert_history
├── auth/         auth, audit_log
├── reports/      reporting, full_report, html_report, narrative, exit_memo,
│                 _report_sections, _report_helpers, _report_css,
│                 report_themes, _partner_brief, pptx_export,
│                 markdown_report, lp_update
├── ui/           _ui_kit, csv_to_html, json_to_html, text_to_html,
│                 _html_polish, _workbook_style
├── scenarios/    scenario_builder, scenario_shocks, scenario_overlay
├── analysis/     anomaly_detection, stress, pressure_test, surrogate,
│                 compare_runs, challenge, cohorts
├── infra/        config, logger, trace, _terminal, _bundle, output_index,
│                 output_formats, provenance, transparency, job_queue,
│                 run_history, profile, taxonomy, capacity,
│                 diligence_requests
├── __init__.py
├── __main__.py
├── api.py        (top-level programmatic API)
├── cli.py        (`rcm-mc` CLI)
├── pe_cli.py     (`rcm-mc pe` subcommands)
├── portfolio_cmd.py  (`rcm-mc portfolio` subcommands)
└── server.py     (HTTP app)
```

Entry points (`api.py`, `cli.py`, `pe_cli.py`, `portfolio_cmd.py`,
`server.py`, `__main__.py`) **stay at the top level** — they are the
public surface.

## Running

```bash
# Demo (seeds, starts server, opens browser)
.venv/bin/python demo.py

# Real deploy
.venv/bin/python -m rcm_mc.portfolio_cmd --db p.db \
    users create --username boss --password "Strong!1" --role admin
rcm-mc serve --db p.db --port 8080

# Tests
.venv/bin/python -m pytest -q --ignore=tests/test_integration_e2e.py
# → 2878 passed
```
