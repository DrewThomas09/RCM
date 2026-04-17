# Layer: Infra — HTTP Server, CLI, Storage, Helpers

## TL;DR

Everything that isn't pipeline logic. This layer provides: the HTTP
application (stdlib `http.server`), the CLI dispatcher (`rcm-mc ...`),
the SQLite connection manager, auth (scrypt + sessions + CSRF), audit
log, alerts lifecycle, deal workflow primitives, and the infra
helpers (rate limiter, consistency check, logger, config validator).

## What this layer owns

- `rcm_mc/server.py` — HTTP app (auth, CSRF, rate-limit, audit, route
  dispatch).
- `rcm_mc/cli.py` — top-level CLI with `rcm-mc {run|analysis|data|pe|
  portfolio|serve|...}` dispatch.
- `rcm_mc/portfolio/store.py` — SQLite connection manager.
- `rcm_mc/auth/` — scrypt passwords, sessions, audit log.
- `rcm_mc/alerts/` — alert lifecycle (fire → ack → snooze → escalate).
- `rcm_mc/deals/` — per-deal state (profile, notes, tags, owner,
  deadlines, sim inputs, health score, watchlist).
- `rcm_mc/infra/` — logger, config validator, consistency check, rate
  limiter, small utilities.

## `rcm_mc/server.py` (~7,100 lines)

**Purpose.** One file, one HTTP app. No Flask / FastAPI — just
`http.server.ThreadingHTTPServer` wrapped in `RCMHandler`.

**Why one file.** Every route lives in `do_GET` / `do_POST` /
`_route_*` helpers. Easier to audit than a framework-sprinkled
surface. Startup is instant.

**Key class.** `RCMHandler(BaseHTTPRequestHandler)`.

**Dispatch.**
- `do_GET` — top-level path matcher → calls `_route_dashboard`,
  `_route_deal`, `_route_api`, `_route_analysis_workbench`,
  `_route_exports_lp_update`, etc.
- `do_POST` — same matcher with CSRF gating on session-backed
  callers. `/api/login`, `/api/logout`, `/health` exempt.

**Response helpers.**
- `_send_html(body, status)` — text/html response.
- `_send_json(payload, status)` — NaN-safe JSON encoder with
  pandas/numpy/date/Decimal/bytes coercion.
- `_send_text(body)`, `_send_401()`, `_redirect(loc)`, `_send_file(path)`.
- `_send_csv(filename, rows)`.

**Auth gate.** Every request checks `_auth_ok()` — HTTP Basic OR
session cookie. Session tokens rotate with an ephemeral
per-process `_SERVER_SECRET`; restarting invalidates all sessions
(documented as expected behavior — partners reopen the login tab).

**CSRF.** `_SERVER_SECRET`-keyed HMAC tokens set on login, verified
on every POST. Shell-level JS in `_ui_kit.shell()` auto-patches
every form + `fetch()` call with the token.

**Rate limits.**
- Per-IP login failure log (5 fails per minute → 429).
- `/api/data/refresh/<source>` — 1 per source per hour via
  `rcm_mc.infra.rate_limit.RateLimiter` at module scope.

**Audit.** Every state-changing route calls `_log_audit(action,
target, **detail)` → writes to `audit_events` via
`rcm_mc.auth.audit_log.log_event()`. Silent-failure safe (won't
break user-visible flow), with a breadcrumb written to stderr on
audit-write failure (class-level `_audit_failure_count` +
`_audit_last_failure`).

**Route categories.**
- `/` — dashboard.
- `/login`, `/logout`, `/users`, `/audit` — auth / admin.
- `/deal/<id>` — legacy deal page.
- `/analysis/<id>` — **new Bloomberg workbench**.
- `/compare`, `/cohort/<tag>`, `/alerts`, `/escalations`,
  `/watchlist`, `/owners`, `/deadlines`, `/lp-update`, `/notes`,
  `/variance`, `/ops`, `/jobs` — portfolio-ops pages.
- `/exports/lp-update` — packet-driven portfolio LP update.
- `/api/deals/*` — legacy API (snapshots, actuals, notes, tags,
  owner, deadlines, provenance).
- `/api/analysis/<id>/*` — **new packet-driven API**:
  - `/` (GET) — full packet JSON.
  - `/section/<name>` (GET) — one section.
  - `/rebuild` (POST) — force rebuild.
  - `/risks`, `/diligence-questions` (GET).
  - `/completeness`, `/predictions` (GET).
  - `/bridge` (POST custom targets), `/sensitivity`, `/targets` (GET).
  - `/simulate` (POST), `/simulate/latest` (GET), `/simulate/compare` (POST).
  - `/export?format=X` (GET).
  - `/provenance` (GET full graph), `/provenance/<metric>` (GET subgraph).
  - `/explain/<metric>` (GET narrative).
- `/api/data/*` — CMS data layer (`/sources`, `/hospitals`,
  `/refresh/<source>`).
- `/api/predict/backtest` — prediction quality across the cohort.

## `rcm_mc/cli.py` (~1,250 lines)

**Purpose.** Top-level `rcm-mc` CLI dispatcher.

**Top-level commands** (see `_TOP_LEVEL_HELP`):
- `rcm-mc run` — legacy Monte Carlo pipeline (simulate → report →
  bundle).
- `rcm-mc intake` — interactive wizard to build `actual.yaml`.
- `rcm-mc lookup` — search CMS HCRIS from the command line.
- `rcm-mc ingest` — seller data pack → canonical CSVs.
- `rcm-mc challenge` — reverse EBITDA solver.
- `rcm-mc deal` — one-command orchestrator: intake → ingest → run.
- `rcm-mc hcris` — rebuild/inspect the shipped HCRIS bundle.
- `rcm-mc pe` — PE deal-math subcommands (bridge, returns, grid,
  covenant).
- `rcm-mc portfolio` — snapshot/list/rollup.
- `rcm-mc serve` — start the HTTP server.
- `rcm-mc analysis <deal_id>` — **new**: build or load the Deal
  Analysis Packet, output JSON.
- `rcm-mc data {refresh|status}` — **new**: CMS data refresh.

## `rcm_mc/portfolio/store.py` (~260 lines)

**Purpose.** The SQLite connection manager. The only module that
talks to SQLite directly; everything else goes through a store
instance.

**Key class.** `PortfolioStore(db_path: str)`.

**Core methods.**
- `connect()` context manager — yields a `sqlite3.Connection` with
  `row_factory=sqlite3.Row` and `busy_timeout=5000`.
- `init_db()` — idempotent `CREATE TABLE IF NOT EXISTS` for the
  baseline tables (`deals`, `runs`).
- `upsert_deal(deal_id, name, profile)`.
- `add_run(deal_id, scenario, cfg, summary_df, notes)` — legacy
  Phase-2 simulator runs.
- `list_deals() -> pd.DataFrame`, `list_runs(deal_id) ->
  pd.DataFrame`, `get_run(run_id) -> RunRecord`.
- `export_priors(out_yaml_path)` — aggregate priors across stored
  runs.

**Invariants.**
- `busy_timeout=5000` on every connection so concurrent handler
  threads retry briefly on a locked database instead of raising
  `sqlite3.OperationalError: database is locked`.
- `PRAGMA foreign_keys=ON` on every connection (Prompt 21). Orphan
  inserts into `deal_overrides`, `analysis_runs`, `mc_simulation_runs`,
  or `generated_exports` now raise `sqlite3.IntegrityError` instead
  of silently creating dangling rows. Cascade rules: `deal_overrides`,
  `analysis_runs`, `mc_simulation_runs` are `ON DELETE CASCADE` (deal
  gone → its scratch data is gone); `generated_exports` is
  `ON DELETE SET NULL` (deal gone → the export audit row stays but
  its `deal_id` nulls out).
- `BEGIN IMMEDIATE` is used inside check-then-write sequences
  (e.g., `auth.delete_user`, `watchlist.toggle_star`).

**Table inventory** (17 tables; each created by the module that owns
it, via the idempotent CREATE pattern):
- `deals`, `runs` — core.
- `deal_snapshots`, `deal_sim_inputs`, `deal_notes`, `deal_tags`,
  `deal_owners`, `deal_deadlines`, `deal_watchlist` — deal workflow.
- `hold_actuals`, `initiative_actuals` — PE tracking.
- `users`, `sessions`, `audit_events`, `login_failures` — auth.
- `alerts`, `alert_acks`, `alert_history` — alerts lifecycle.
- `analysis_runs` — packet cache (Prompt 1).
- `hospital_benchmarks`, `data_source_status` — CMS data (Prompt 7).
- `mc_simulation_runs` — MC cache (Prompt 8).
- `generated_exports` — export audit (Prompt 11).
- `metric_provenance` — legacy provenance registry.
- `deal_overrides` — analyst overrides (Prompt 18; see below).

## Analyst overrides — `rcm_mc/analysis/deal_overrides.py`

**Purpose.** A narrow, validated surface for persisting per-deal
tweaks. Until Prompt 18 the platform accepted overrides at call-time
(``optional_contract_inputs`` on the reimbursement engine,
:class:`BridgeAssumptions` knobs) but had no way to pin them per deal
so subsequent packet builds, API calls, and CLI runs picked them up.

**Table.**

```sql
CREATE TABLE IF NOT EXISTS deal_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    override_key TEXT NOT NULL,
    override_value TEXT NOT NULL,      -- JSON-encoded
    set_by TEXT NOT NULL,
    set_at TEXT NOT NULL,              -- UTC ISO
    reason TEXT,
    UNIQUE(deal_id, override_key)
);
```

**Keyspace (validated on write).**

| Prefix | Shape | Example |
|---|---|---|
| `payer_mix.*` | `payer_mix.<payer>_share` | `payer_mix.commercial_share` |
| `method_distribution.*` | `method_distribution.<payer>.<method>` | `method_distribution.commercial.fee_for_service` |
| `bridge.*` | `bridge.<field>` | `bridge.exit_multiple` |
| `ramp.*` | `ramp.<family>.<field>` | `ramp.denial_management.months_to_full` |
| `metric_target.*` | `metric_target.<metric>` | `metric_target.denial_rate` |

Payer / method / bridge-field / ramp-family / ramp-field lists are
explicit whitelists — an accidental dataclass rename downstream
doesn't silently open the override surface.

**Public functions.** `set_override`, `get_overrides`,
`clear_override`, `list_overrides`, `group_overrides`,
`validate_override_key`. `set_override` does an upsert keyed by
`(deal_id, override_key)`. `group_overrides` splits a flat
`{key: value}` map into the five namespaces so the packet builder
can slot each group into its natural place without knowing the
string-key shape.

**Packet-builder wiring.** `build_analysis_packet` loads overrides
once (step 1b), then:

- `payer_mix.*` rewrites `profile.payer_mix` in place so every
  downstream consumer (risk flags, reimbursement engine, provenance)
  sees the partner-authored mix.
- `method_distribution.*` becomes `optional_contract_inputs` for the
  reimbursement engine. The engine flips the affected payer's
  `method_distribution` provenance to `ProvenanceTag.ANALYST_OVERRIDE`
  automatically.
- `bridge.*` lands in the `financials` dict so the v2 bridge picks
  up the value through its existing keys.
- `ramp.*` overlays on top of `DEFAULT_RAMP_CURVES` and feeds the v2
  bridge + v2 Monte Carlo.
- `metric_target.*` merges under caller-supplied `target_metrics`
  (caller wins by design — a one-off scenario overrides a stored
  default).

The loaded overrides also land on `DealAnalysisPacket.analyst_overrides`
for audit, and are folded into `hash_inputs` so adding or clearing
an override correctly invalidates the `analysis_runs` cache on the
next `get_or_build_packet`.

**CLI.**

```
rcm-mc pe override set <deal_id> <key> <json-value> [--reason "..."] [--set-by ID]
rcm-mc pe override list [<deal_id>] [--json]
rcm-mc pe override clear <deal_id> <key>
```

Uses `$RCM_MC_DB` (or `./portfolio.db`) by default; pass `--db` to
target another file.

**API.**

```
GET    /api/deals/<deal_id>/overrides           # all + audit trail
GET    /api/deals/<deal_id>/overrides/<key>     # one
PUT    /api/deals/<deal_id>/overrides/<key>     # upsert
DELETE /api/deals/<deal_id>/overrides/<key>     # remove
```

`PUT` expects `{"value": ..., "reason": "..."}` and records the
authenticated session user as `set_by` (falls back to `"api"` when
there's no session, e.g. HTTP-Basic scripts).

## `rcm_mc/auth/` (~500 lines total)

- `auth.py` — scrypt password hash + verification, session token
  issuance (`sessions` table, SQLite-backed so tokens survive
  restart), CSRF secret, rate-limited login. Prompt 21 added
  `cleanup_expired_sessions(store) -> int` — called once on
  `build_server` and every 100 requests from the handler.
- `audit_log.py` — `log_event(store, *, actor, action, target,
  detail, request_id=None)` → `audit_events` table. The
  `request_id` column (Prompt 21) correlates an audit row back to
  the handler's per-request UUID4 so sensitive actions can be
  traced to the exact HTTP call via the JSON access log.
  `list_events(store, *, limit)`.

## Observability — structured per-request logging (Prompt 21)

Every request gets a 16-hex-char `request_id` assigned in
`RCMHandler.handle_one_request`. On response, `log_message` emits a
single JSON line to stderr:

```json
{"ts": "2026-04-15T10:00:00+00:00", "request_id": "abc…",
 "method": "GET", "path": "/api/deals", "status": 200,
 "duration_ms": 7.3, "user_id": "analyst",
 "client": "127.0.0.1"}
```

`/health` and `/favicon.ico` are skipped so polling dashboards don't
flood stderr. Audit writes threaded through `_log_audit` pass the
request_id into `log_event`, letting `audit_events` rows correlate
1-to-1 with the access-log line that produced them.

## Packet-cache schema-version gate (Prompt 21)

`analysis_runs` already stored `model_version` for every cached
packet. `get_or_build_packet` now filters cache hits on
`model_version = PACKET_SCHEMA_VERSION` (the constant lives in
`analysis/packet.py`). A code change that bumps the constant
auto-invalidates every prior blob — old rows stay on disk for audit
but aren't served. Prior behaviour (unconditional hash hit) is
available by calling `find_cached_packet` without
`schema_version=…`.

## `rcm_mc/alerts/` (~700 lines total)

- `alerts.py` — `evaluate_active(store)`, `evaluate_all(store)` —
  the alert-rule engine.
- `alert_acks.py` — ack/snooze/expire workflow.
- `alert_history.py` — retention + "returning after snooze" badge
  logic.

## `rcm_mc/deals/` (~1,800 lines total)

Per-deal state modules; each owns one table.

- `deal.py` — the `rcm-mc deal new` orchestrator.
- `deal_notes.py` — freeform notes with tag + full-text search.
- `deal_tags.py` — deal-level tags.
- `deal_owners.py` — owner assignment + `deals_by_owner`.
- `deal_deadlines.py` — date-backed reminders, `overdue()`,
  `upcoming(days=14)`.
- `deal_sim_inputs.py` — per-deal paths to `actual.yaml` +
  `benchmark.yaml` for the Phase-2 simulator rerun button.
- `deal_tags.py`, `note_tags.py` — tagging schemas.
- `watchlist.py` — per-user star toggles.
- `health_score.py` — composite 0-100 health with trend sparkline.

## `rcm_mc/infra/` (various sizes)

- `config.py` — YAML config validation (`load_and_validate`,
  `validate_config`).
- `logger.py` — stdlib logging wrapper.
- `consistency_check.py` — **new**. `check_consistency(store) ->
  ConsistencyReport` verifies expected tables exist + flags orphan
  rows in `analysis_runs` / `mc_simulation_runs` / `generated_exports`.
  Never raises.
- `rate_limit.py` — **new**. `RateLimiter(max_hits, window_secs)`
  thread-safe sliding window. Used on `/api/data/refresh`.
- `provenance.py` — older provenance helpers (pre-registry).
- `transparency.py` — transparency-coverage file scanner.
- `job_queue.py` — in-memory single-worker queue (Phase-2 sim reruns).
- `run_history.py` — per-run persistence.
- `trace.py` — sim trace JSON writer.
- `_terminal.py` — `banner()`, `info()`, `success()`, `warn()`
  terminal output helpers.
- `_bundle.py`, `output_index.py`, `output_formats.py` — Phase-2
  bundle renderer.
- `profile.py` — hospital-profile alignment helpers.
- `taxonomy.py`, `capacity.py`, `diligence_requests.py` — domain
  helpers.

## `rcm_mc/portfolio/` (beyond `store.py`)

- `portfolio_snapshots.py` — stage lifecycle (pipeline → diligence →
  IC → hold → exit). `portfolio_rollup()` aggregate.
- `portfolio_dashboard.py` — dashboard data assembly.
- `portfolio_digest.py` — change-since-date digest.
- `portfolio_synergy.py` — cross-deal synergy analysis.
- `portfolio_cli.py` — subcommands.

## `rcm_mc/core/` (various)

Phase-2 simulator kernel (pre-dates the packet-centric refactor):
- `simulator.py` — main Monte Carlo kernel (not the same as
  `rcm_mc/mc/ebitda_mc.py`; this one models claim-level denials).
- `distributions.py` — stdlib distribution samplers.
- `kernel.py` — core Monte Carlo loop.
- `calibration.py` — prior fitting from data.
- `rng.py` — RNG wrappers.
- `_calib_schema.py`, `_calib_stats.py` — calibration support.

## `rcm_mc/rcm/`

Phase-2 claim-distribution math:
- `claim_distribution.py` — lognormal claim bucketing, denial rates
  by bucket.
- `initiatives.py`, `initiative_*.py` — RCM initiative effects.

## `rcm_mc/scenarios/`

Phase-2 scenario overlays:
- `scenario_builder.py` — build a scenario from shocks.
- `scenario_overlay.py` — `apply_scenario(config, scenario)` pure
  function.
- `scenario_shocks.py` — shock primitives.

## How it fits the system

```
┌──────────────────────────────────────────────────────┐
│                                                        │
│    HTTP  ◀──  server.py  (ThreadingHTTPServer)         │
│    CLI   ◀──  cli.py  (argparse dispatcher)            │
│                                                        │
└─────────────────────────┬────────────────────────────┘
                          │
                          ▼
                ┌──────────────────────────┐
                │ feature subpackages       │
                │  alerts/, deals/,         │
                │  portfolio/, auth/,       │
                │  analysis/, exports/,     │
                │  provenance/, ml/, mc/,   │
                │  pe/, ui/, data/,         │
                │  finance/, domain/        │
                └──────────────┬───────────┘
                               │
                               ▼
              ┌──────────────────────────────┐
              │ portfolio.store.PortfolioStore│ ← only direct SQLite caller
              │  .connect() / .init_db()      │
              └──────────────┬───────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  SQLite file   │ ← 17 tables
                    └────────────────┘
```

Every layer calls down, never up. The store is the **only** module
that talks to SQLite directly — all domain logic goes through it.

## Current state

### Strong points
- **Stdlib-heavy.** HTTP, SQLite, scrypt, CSRF, rate-limit,
  threading — all stdlib. Zero framework dep.
- **One-file server keeps routing auditable.** 7K lines is large but
  the `_route_*` decomposition keeps per-route surface small.
- **Every state-changing route audits.** `audit_events` survives
  server restarts; partners can answer "who did what" without logs.
- **Idempotent schema.** Every table is CREATE IF NOT EXISTS; no
  migrations, no ordering dependencies.
- **Consistency check + rate limiter** added in the hardening pass
  (see [README_BUILD_STATUS.md](README_BUILD_STATUS.md)).

### Weak points
- **Session tokens don't survive restart.** Per-process CSRF secret
  rotates; partners have to log in again after a restart.
- **In-memory job queue.** Phase-2 sim-rerun jobs lost on restart.
  OK for partner-driven rerun (they'll click again) but not for
  critical cron flows.
- **Per-request logging is not structured.** `log_message()` writes
  a compact stderr line; no request_id threading, no response-time
  histogram.
- **No production deployment config.** No systemd unit, no Docker
  entrypoint script, no graceful-shutdown handler. Single-machine
  deploy is the documented baseline.
- **Foreign-key enforcement off.** `PRAGMA foreign_keys=ON` not
  enabled; orphan rows possible (detected by `consistency_check`
  but not prevented).
- **Filesystem artifact (unresolved).** `rcm_mc/data/lookup.py` is
  currently at `rcm_mc/data/lookup 2.py` — a macOS Finder duplicate
  rename. Breaks 9 tests in the lookup / transparency / IRS990 /
  CLI paths. Trivial to fix (`mv "lookup 2.py" lookup.py`) but has
  sat open for several prompts waiting on explicit authorization.
