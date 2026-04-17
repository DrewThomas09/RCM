# RCM-MC — Full codebase summary

A tour of the whole folder: what each part does, how a request flows
from the browser through the backend to SQLite and back, and how the
pieces compose.

---

## 1 · High-level architecture

```
         ┌──────────────────────────────────────────────────┐
         │                     Partner                      │
         │  Browser  │  CLI (rcm-mc)  │  External cron       │
         └──────────────────────────────────────────────────┘
                │              │              │
                ▼              ▼              ▼
         ┌──────────────┐ ┌────────────┐ ┌────────────┐
         │ HTTP server  │ │  cli.py /  │ │ portfolio_ │
         │ (server.py)  │ │ pe_cli.py  │ │  cmd.py    │
         └──────┬───────┘ └─────┬──────┘ └─────┬──────┘
                │               │              │
                └──────────┬────┴──────────────┘
                           ▼
      ┌────────────────────────────────────────────────┐
      │           Feature modules (~30 files)          │
      │  alerts · cohorts · health_score · deal_owners │
      │  deal_deadlines · watchlist · auth · audit_log │
      │  note_tags · lp_update · job_queue · …         │
      └────────────────────┬───────────────────────────┘
                           ▼
      ┌────────────────────────────────────────────────┐
      │       Simulator + PE-math layer (pre-B101)      │
      │  simulator · pe_math · hold_tracking ·          │
      │  portfolio_snapshots · hcris · irs990 · …       │
      └────────────────────┬───────────────────────────┘
                           ▼
      ┌────────────────────────────────────────────────┐
      │   PortfolioStore (portfolio/store.py)          │
      │   SQLite connection pool, 17 tables,           │
      │   busy_timeout=5000, per-request connection    │
      └────────────────────────────────────────────────┘
```

Every layer calls down; the store never reaches up.

---

## 2 · Top-level folder map

| Path | What's there |
|---|---|
| [rcm_mc/](../rcm_mc/) | The Python package. ~97 modules. |
| [tests/](../tests/) | 123 test files, 1426 passing tests. |
| [docs/](../docs/) | Architecture + partner workflow + this doc. |
| [configs/](../configs/) | Example `actual.yaml` / `benchmark.yaml` inputs. |
| [scenarios/](../scenarios/) | Named scenario preset YAML files. |
| [data_demo/](../data_demo/) | Sample CSVs for a walk-through. |
| [output v1/](../output%20v1/) | Example rendered run output. |
| [demo.py](../demo.py) | One-command demo: seeds + starts server. |
| [run_all.sh](../run_all.sh) | Bash orchestrator for a full end-to-end run. |
| [README.md](../README.md) | Project overview. |
| [pyproject.toml](../pyproject.toml) | Deps + entry points (`rcm-mc` console script). |
| [Dockerfile](../Dockerfile), [docker-compose.yml](../docker-compose.yml) | Containerized deploy. |

---

## 3 · The `rcm_mc/` package, grouped by purpose

### 3.1 — Entry points

| File | Role |
|---|---|
| [`__main__.py`](../rcm_mc/__main__.py) | Makes `python -m rcm_mc` work. |
| [`cli.py`](../rcm_mc/cli.py) | Top-level CLI — `rcm-mc run`, `rcm-mc report`, etc. Dispatches to subcommands. |
| [`portfolio_cmd.py`](../rcm_mc/portfolio_cmd.py) | `rcm-mc portfolio …` — register / list / actuals / alerts / deadlines / owners / users / lp-update / rerun. |
| [`pe_cli.py`](../rcm_mc/pe_cli.py) | `rcm-mc pe …` — PE-math commands (bridge / returns / grid / covenant). |
| [`api.py`](../rcm_mc/api.py) | Programmatic Python entry point. |
| [`server.py`](../rcm_mc/server.py) | The HTTP server. 5700+ lines, routes every `/` and `/api/*` URL. |

### 3.2 — The web application (`server.py` is the whole app)

The server is a single-file `ThreadingHTTPServer` with:

- **Auth layer** — `_auth_ok`, `_current_user`, `_session_token`, `_csrf_ok`
- **Middleware** — CSRF gate on POSTs, rate-limited login, audit-log attribution
- **~30 HTML routes** — `/alerts`, `/cohorts`, `/deal/<id>`, `/lp-update`, `/variance`, `/my/<owner>`, `/watchlist`, `/audit`, etc.
- **~55 JSON routes** — `/api/deals/*`, `/api/alerts/*`, `/api/jobs/*`, `/api/me`, `/api/health`, etc.
- **Helpers** — `_render_deal_rerun`, `_health_cell`, `_render_health_sparkline`, `_defang_csv_df`, `_clamp_int`, `_log_audit`, `_send_json`, `_send_csv_df`, `_send_html`

### 3.3 — Portfolio-operations layer (shipped in this session)

Each module owns one table + a thin API.

| Module | Table | What it does |
|---|---|---|
| [`alerts.py`](../rcm_mc/alerts.py) | (none — read-only) | Four evaluators (covenant, variance, cluster, stage-regress) + overdue-deadline integration (B115). `evaluate_all`, `evaluate_active` |
| [`alert_acks.py`](../rcm_mc/alert_acks.py) | `alert_acks` | Ack/snooze individual alert instances. `ack_alert`, `is_acked`, `was_snoozed`, `trigger_key_for` |
| [`alert_history.py`](../rcm_mc/alert_history.py) | `alert_history` | First-seen / last-seen tracking; `record_sightings`, `age_hint`, `days_red` |
| [`cohorts.py`](../rcm_mc/cohorts.py) | (joins deal_tags + snapshots) | `cohort_rollup`, `cohort_detail` — tag-grouped weighted aggregates |
| [`watchlist.py`](../rcm_mc/watchlist.py) | `deal_stars` | `star_deal`, `toggle_star`, `list_starred` (atomic CAS) |
| [`deal_owners.py`](../rcm_mc/deal_owners.py) | `deal_owner_history` | `assign_owner`, `current_owner`, `deals_by_owner`, `all_owners` |
| [`deal_deadlines.py`](../rcm_mc/deal_deadlines.py) | `deal_deadlines` | `add_deadline` (idempotent), `complete_deadline`, `upcoming`, `overdue` |
| [`deal_sim_inputs.py`](../rcm_mc/deal_sim_inputs.py) | `deal_sim_inputs` | Stored `actual.yaml`/`benchmark.yaml` paths per deal for one-click rerun |
| [`deal_notes.py`](../rcm_mc/deal_notes.py) | `deal_notes` | Append-only notes with soft-delete, `search_notes`, `import_notes_csv` |
| [`deal_tags.py`](../rcm_mc/deal_tags.py) | `deal_tags` | Freeform deal tags with normalized case |
| [`note_tags.py`](../rcm_mc/note_tags.py) | `note_tags` | Per-note taxonomy (e.g. `board_meeting`, `blocker`) |
| [`health_score.py`](../rcm_mc/health_score.py) | `deal_health_history` | Composite 0-100 health score with transparent components + trend sparkline |
| [`lp_update.py`](../rcm_mc/lp_update.py) | (pure function) | `build_lp_update_html(store)` — partner-ready digest, used by both HTTP route and CLI |
| [`auth.py`](../rcm_mc/auth.py) | `users`, `sessions` | scrypt password hashing, session tokens, `create_user`, `verify_password`, `create_session`, `change_password` |
| [`audit_log.py`](../rcm_mc/audit_log.py) | `audit_events` | Unified append-only event log; `log_event`, `list_events` (paginated) |
| [`job_queue.py`](../rcm_mc/job_queue.py) | (in-memory) | Single-worker FIFO queue for simulation runs |
| [`portfolio_dashboard.py`](../rcm_mc/portfolio_dashboard.py) | (renders) | Builds the `/` HTML: headline, pulse, health distribution, funnel, filterable table |
| [`portfolio_digest.py`](../rcm_mc/portfolio_digest.py) | (reads snapshots) | `build_digest(store, since=…)` — recent change events |
| [`portfolio_snapshots.py`](../rcm_mc/portfolio_snapshots.py) | `deal_snapshots` | `register_snapshot`, `latest_per_deal`, `portfolio_rollup`, `list_snapshots` |

### 3.4 — Simulator + PE-math layer (pre-existing)

Unchanged in this session but wired into the portfolio layer.

| Module | Purpose |
|---|---|
| [`simulator.py`](../rcm_mc/simulator.py) | Monte Carlo core — runs N sims per deal |
| [`pe_math.py`](../rcm_mc/pe_math.py) | Value-creation bridge, IRR/MOIC bisection, hold-period grid, covenant check |
| [`pe_integration.py`](../rcm_mc/pe_integration.py) | Auto-wire PE math onto `rcm-mc run` outputs |
| [`hold_tracking.py`](../rcm_mc/hold_tracking.py) | Quarterly actuals + variance reports; `record_quarterly_actuals`, `variance_report`, `portfolio_variance_matrix` |
| [`initiative_tracking.py`](../rcm_mc/initiative_tracking.py) | Per-initiative actual ingest + variance |
| [`remark.py`](../rcm_mc/remark.py) | Re-underwrite: recompute MOIC/IRR from latest TTM |
| [`hcris.py`](../rcm_mc/hcris.py) | HCRIS (hospital cost-report) data loader |
| [`irs990.py`](../rcm_mc/irs990.py) | IRS Form 990 loader (non-profits) |
| [`benchmarks` / `sources.py`](../rcm_mc/sources.py) | External benchmark data sources |
| [`distributions.py`](../rcm_mc/distributions.py) | Probability distributions for MC sampling |
| [`calibration.py`](../rcm_mc/calibration.py) | Fit distributions to priors |
| [`scenario_builder.py`](../rcm_mc/scenario_builder.py), [`scenario_shocks.py`](../rcm_mc/scenario_shocks.py), [`scenario_overlay.py`](../rcm_mc/scenario_overlay.py) | Scenario layering |
| [`value_plan.py`](../rcm_mc/value_plan.py), [`value_creation.py`](../rcm_mc/value_creation.py) | Deal value-plan math |
| [`attribution.py`](../rcm_mc/attribution.py), [`breakdowns.py`](../rcm_mc/breakdowns.py) | Driver decomposition |
| [`anomaly_detection.py`](../rcm_mc/anomaly_detection.py) | Outlier flagging |
| [`stress.py`](../rcm_mc/stress.py), [`pressure_test.py`](../rcm_mc/pressure_test.py) | Stress tests |
| [`surrogate.py`](../rcm_mc/surrogate.py) | Fast surrogate model |

### 3.5 — Rendering / presentation

| File | Output format |
|---|---|
| [`_ui_kit.py`](../rcm_mc/_ui_kit.py) | Shared HTML shell — CSS + page frame. Every `_send_html` uses this. |
| [`_report_css.py`](../rcm_mc/_report_css.py), [`report_themes.py`](../rcm_mc/report_themes.py) | Styling |
| [`reporting.py`](../rcm_mc/reporting.py), [`full_report.py`](../rcm_mc/full_report.py), [`html_report.py`](../rcm_mc/html_report.py) | Multi-page diligence report |
| [`_report_sections.py`](../rcm_mc/_report_sections.py), [`_report_helpers.py`](../rcm_mc/_report_helpers.py) | Section builders |
| [`narrative.py`](../rcm_mc/narrative.py), [`_partner_brief.py`](../rcm_mc/_partner_brief.py) | Prose generation |
| [`exit_memo.py`](../rcm_mc/exit_memo.py) | Exit-readiness memo per deal |
| [`csv_to_html.py`](../rcm_mc/csv_to_html.py), [`json_to_html.py`](../rcm_mc/json_to_html.py), [`text_to_html.py`](../rcm_mc/text_to_html.py), [`markdown_report.py`](../rcm_mc/markdown_report.py) | Format converters |
| [`pptx_export.py`](../rcm_mc/pptx_export.py) | PowerPoint export |
| [`_workbook_style.py`](../rcm_mc/_workbook_style.py) | xlsx styling |
| [`_bundle.py`](../rcm_mc/_bundle.py), [`output_index.py`](../rcm_mc/output_index.py) | Bundled output folder (MANIFEST, etc.) |
| [`output_formats.py`](../rcm_mc/output_formats.py) | Format registry |
| [`transparency.py`](../rcm_mc/transparency.py), [`provenance.py`](../rcm_mc/provenance.py) | Audit of numbers → sources |

### 3.6 — Utility / infra

| File | Purpose |
|---|---|
| [`portfolio/store.py`](../rcm_mc/portfolio/store.py) | `PortfolioStore` — SQLite connection context manager, `init_db`, `upsert_deal` |
| [`config.py`](../rcm_mc/config.py) | YAML config loader |
| [`ingest.py`](../rcm_mc/ingest.py), [`intake.py`](../rcm_mc/intake.py), [`data_scrub.py`](../rcm_mc/data_scrub.py) | Input validation + cleansing |
| [`deal.py`](../rcm_mc/deal.py) | Deal-level operations |
| [`logger.py`](../rcm_mc/logger.py) | Logging setup |
| [`rng.py`](../rcm_mc/rng.py) | Deterministic random state |
| [`kernel.py`](../rcm_mc/kernel.py) | Core simulation kernel |
| [`taxonomy.py`](../rcm_mc/taxonomy.py) | Enum-like classifiers |
| [`trace.py`](../rcm_mc/trace.py) | Execution trace for debugging |
| [`_terminal.py`](../rcm_mc/_terminal.py) | Terminal helpers |
| [`_html_polish.py`](../rcm_mc/_html_polish.py) | Post-processing of HTML output |
| [`lookup.py`](../rcm_mc/lookup.py) | Peer / benchmark lookups |
| [`profile.py`](../rcm_mc/profile.py) | Deal profile normalization |
| [`challenge.py`](../rcm_mc/challenge.py) | "Challenge the thesis" exercise generator |
| [`compare_runs.py`](../rcm_mc/compare_runs.py) | Diff two simulation runs |
| [`run_history.py`](../rcm_mc/run_history.py) | Persisted simulation run index |
| [`diligence_requests.py`](../rcm_mc/diligence_requests.py) | DD question generator |
| [`capacity.py`](../rcm_mc/capacity.py) | Capacity modeling |
| [`claim_distribution.py`](../rcm_mc/claim_distribution.py) | Healthcare-claim distribution |
| [`initiatives.py`](../rcm_mc/initiatives.py), [`initiative_optimizer.py`](../rcm_mc/initiative_optimizer.py), [`initiative_rollup.py`](../rcm_mc/initiative_rollup.py) | RCM-initiative math |
| [`portfolio_cli.py`](../rcm_mc/portfolio_cli.py) | Legacy portfolio CLI helpers |
| [`portfolio_synergy.py`](../rcm_mc/portfolio_synergy.py) | Cross-deal synergy calc |
| [`_calib_schema.py`](../rcm_mc/_calib_schema.py), [`_calib_stats.py`](../rcm_mc/_calib_stats.py) | Calibration helpers |

---

## 4 · How a request flows (anatomy of one click)

### Example: partner clicks an **Ack** button on `/alerts`

1. **Browser** submits `<form method="POST" action="/api/alerts/ack">` with `kind`, `deal_id`, `trigger_key`, `snooze_days`, and (auto-injected) `csrf_token`.

2. **`server.do_POST`** ([server.py](../rcm_mc/server.py)):
   - `_auth_ok()` → checks session cookie → `_current_user()` resolves to `{username, role, display_name}`.
   - CSRF gate: matches form `csrf_token` against HMAC of session token (via `_csrf_ok`).
   - Dispatches to `_route_api_post("/api/alerts/ack")`.

3. **Route handler**:
   - `_read_form_body()` (memoized per request).
   - Calls `alert_acks.ack_alert(store, kind=…, deal_id=…, trigger_key=…, snooze_days=…, acked_by=current_user["username"])`.
   - Calls `self._log_audit("alert.ack", target=deal_id, kind=…, ack_id=…)`.
   - Emits 201 with `{"ack_id": N}` (JSON) or 303 redirect to `/alerts` (browser).

4. **`alert_acks.ack_alert`** ([alert_acks.py](../rcm_mc/alert_acks.py)):
   - `_ensure_table(store)` — idempotent CREATE TABLE IF NOT EXISTS.
   - INSERT into `alert_acks` with parameterized SQL.
   - Returns new row id.

5. **`audit_log.log_event`** writes a row to `audit_events`; failures surface to stderr + increment `_audit_failure_count`.

6. **Next page load** of `/alerts`:
   - `alerts.evaluate_active(store)` runs the 4 evaluators, records sightings in `alert_history`, filters out acked instances via `is_acked`, enriches each `Alert` with `first_seen_at` and `returning` flag.
   - HTML template renders rows with colored badges, age hint ("seen 3d ago"), and an ack form.

The whole round trip: **browser → auth → CSRF → handler → module → store → audit** — takes ~15ms on a laptop.

---

## 5 · The 17 SQLite tables

Created lazily by `_ensure_*_table` functions, migrated forward with
`ALTER TABLE ADD COLUMN` when schemas evolve.

| Table | Owner module | Purpose |
|---|---|---|
| `deals` | store.py | Stable deal IDs + metadata |
| `runs` | store.py | Each simulation run's config + summary |
| `deal_snapshots` | portfolio_snapshots | Append-only stage/MOIC/IRR history |
| `quarterly_actuals` | hold_tracking | KPI actuals + plan per quarter |
| `initiative_actuals` | initiative_tracking | Per-initiative EBITDA impact |
| `deal_notes` | deal_notes | Analyst notes with soft-delete |
| `note_tags` | note_tags | Note taxonomy |
| `deal_tags` | deal_tags | Deal cohort tags |
| `deal_stars` | watchlist | Starred (pinned) deals |
| `deal_owner_history` | deal_owners | Append-only ownership audit |
| `deal_deadlines` | deal_deadlines | Tasks with due_date + owner |
| `deal_sim_inputs` | deal_sim_inputs | Stored actual/benchmark paths per deal |
| `alert_acks` | alert_acks | Acks/snoozes of alert instances |
| `alert_history` | alert_history | First-seen / last-seen per alert instance |
| `deal_health_history` | health_score | One score row per deal per day |
| `users` | auth | Username, scrypt hash, salt, display_name, role |
| `sessions` | auth | Session tokens with expires_at |
| `audit_events` | audit_log | Unified event log (who did what when) |

---

## 6 · Security model (in one picture)

```
Unauth request   →  _auth_ok() → redirects /login (HTML) or 401 (JSON)
                                       │
Login (username + password)            │
  ↓                                    │
  rate-limit check (5/min per IP)      │
  ↓                                    │
  scrypt verify (constant time)        │
  ↓                                    │
  issue rcm_session (HttpOnly)         │
  issue rcm_csrf = HMAC(session, secret) (non-HttpOnly)
  ↓                                    │
Subsequent POSTs  ← CSRF double-submit check ← session cookie
  ↓
Admin-only POSTs  ← role check → 403 if not admin
  ↓
All state-changing handlers
  ↓  _log_audit(actor, action, target, detail)
audit_events  →  /audit admin page + /api/audit/events
```

Every layer has a failure mode that surfaces to operators:
- CSRF fail → `{"code": "CSRF_FAILED"}`
- Rate limited → `{"code": "RATE_LIMITED"}` + 429
- Audit write fail → stderr breadcrumb + counter on `/api/health`
- Evaluator crash → stderr breadcrumb + module-level `EVALUATOR_FAILURES` counter

---

## 7 · How to run it

```bash
# One-command demo (seeds data, starts server, opens browser)
.venv/bin/python demo.py

# Real deploy
.venv/bin/python -m rcm_mc.portfolio_cmd --db p.db \
    users create --username boss --password "Strong!1" --role admin
rcm-mc serve --db p.db --port 8080

# Daily LP digest via cron
0 7 * * * .venv/bin/python -m rcm_mc.portfolio_cmd --db p.db \
    lp-update --out /srv/out/lp_$(date +\%Y\%m\%d).html --days 7
```

---

## 8 · Companion docs

- [PARTNER_WORKFLOW.md](PARTNER_WORKFLOW.md) — every URL, API, CLI
- [ARCHITECTURE.md](ARCHITECTURE.md) — simulator-layer design
- [GETTING_STARTED.md](GETTING_STARTED.md) — first-run walk-through
- [BENCHMARK_SOURCES.md](BENCHMARK_SOURCES.md), [METRIC_PROVENANCE.md](METRIC_PROVENANCE.md) — data provenance

---

## 9 · By the numbers

- **~97** Python modules in `rcm_mc/`
- **~35,100** lines of code
- **1,426** passing tests across **123** test files
- **17** SQLite tables, all created with `CREATE TABLE IF NOT EXISTS` and `busy_timeout=5000`
- **~30** HTML routes, **~55** JSON endpoints, **5** CLI subcommand groups
- **Zero** external dependencies beyond stdlib + pandas/numpy/matplotlib (all pre-existing)
- **32 real bugs** found and fixed across 17 self-audit passes
