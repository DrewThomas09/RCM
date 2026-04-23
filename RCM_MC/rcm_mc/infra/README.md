# Infra (Infrastructure)

Platform infrastructure: configuration, logging, job queuing, migrations, notifications, backup, provenance, and API support. Provides the cross-cutting services that every other package depends on.

---

## `config.py` — YAML Config Loading and Validation

**What it does:** Loads, validates, and normalizes simulation YAML configuration files. Provides the `load_and_validate()` function that all modules use to read deal configs.

**How it works:** `load_and_validate(path)` reads the YAML, validates required keys (`hospital`, `payers`), checks numeric bounds (denial rate 0–1, DAR >0, revenue >0), normalizes payer names via `core/_calib_schema.py`, and returns a validated config dict. Raises `ConfigValidationError` with a descriptive message on failure. Also provides `write_yaml(path, config)` for writing calibrated configs.

**Data in:** YAML file path from the CLI or packet builder.

**Data out:** Validated config dict consumed by `core/simulator.py`, `pe/pe_integration.py`, and the packet builder.

---

## `logger.py` — Centralized Logger Setup

**What it does:** Configures the `rcm_mc` package logger with a `StreamHandler` at the appropriate level. Provides the `logger` singleton imported by all modules.

**How it works:** `logging.getLogger("rcm_mc")` with a formatted `StreamHandler` (format: `"%(asctime)s %(name)s %(levelname)s %(message)s"`). Level defaults to `INFO`; `--verbose` CLI flag sets `DEBUG`. Imported as `from .infra.logger import logger` in every module.

**Data in:** Log level from CLI flags or environment variable `RCM_LOG_LEVEL`.

**Data out:** Log output to stderr.

---

## `migrations.py` — Schema Migration Registry

**What it does:** Idempotent schema migration registry. On server startup, runs all pending `ALTER TABLE` / `CREATE INDEX` / `CREATE TABLE` migrations in order so the database schema stays current without manual intervention.

**How it works:** `_MIGRATIONS` list of `(version, sql)` tuples. `run_pending_migrations(con)` checks the `schema_migrations` table for the highest applied version, runs all migrations above that version in sequence, updates the table. Each migration is wrapped in a transaction — if one fails, it's rolled back and the error is logged (not raised, to allow the server to start with a warning). Migrations are additive-only: no DROP or destructive changes.

**Data in:** SQLite connection from `portfolio/store.py` on startup.

**Data out:** Applied schema changes; updated `schema_migrations` table.

---

## `job_queue.py` — In-Process Simulation Job Queue

**What it does:** Single-worker in-process job queue for simulation runs. Partners post jobs via the web UI; a background thread processes them and stores results in the `analysis_runs` table.

**How it works:** `collections.deque`-based queue with a single `threading.Thread` worker. `enqueue(job_type, deal_id, params)` appends a `Job` object. The worker thread polls the queue, calls the appropriate handler (`packet_builder.build_packet` for analysis jobs), stores results, and updates the job status in the `jobs` SQLite table. Job states: `pending → running → complete / failed`. On server restart, in-flight jobs are marked `failed` (lost — re-queue by clicking Rerun).

**Data in:** Job enqueue requests from `server.py` route handlers via `POST /api/deals/<id>/analyze`.

**Data out:** Completed `DealAnalysisPacket` in `analysis_runs`; job status for `GET /api/jobs/<id>` polling.

---

## `rate_limit.py` — In-Memory Sliding-Window Rate Limiter

**What it does:** Protects expensive endpoints (CMS data refresh, analysis run, delete operations) from accidental polling loops or abuse.

**How it works:** `RateLimiter(max_hits, window_secs)` — tracks hit timestamps per key (IP address or route) in an in-memory deque. `check(key)` returns `True` if the key has fewer than `max_hits` in the last `window_secs`. Server-level instances: `_REFRESH_RATE_LIMITER` (1 hit / 1 hour per source), `_DELETE_RATE_LIMITER` (10 hits / 1 hour). State is in-memory — resets on server restart. Not suitable for distributed deployments (single-machine only).

**Data in:** Rate limit check calls from `server.py` route handlers.

**Data out:** `True` (allow) / `False` (deny with 429) for the calling route.

---

## `openapi.py` — OpenAPI Spec and Swagger UI

**What it does:** Generates the OpenAPI 3.0 spec for all 52 API endpoints and serves the Swagger UI at `GET /api/docs`.

**How it works:** `_OPENAPI_SPEC` is a manually-maintained Python dict (not auto-generated from decorators — the stdlib HTTP handler doesn't support decorators). `get_spec()` returns the spec as a JSON string. `swagger_ui_html()` returns the Swagger UI HTML page with the spec URL inlined. The spec is served at `GET /api/openapi.json`. Covers all GET/POST/PUT/PATCH/DELETE endpoints with request/response schemas and example payloads.

**Data in:** Static spec dict — updated manually when new endpoints are added.

**Data out:** OpenAPI JSON for `GET /api/openapi.json`; Swagger UI for `GET /api/docs`.

---

## `webhooks.py` — HMAC-Signed Webhook Dispatch

**What it does:** Dispatches HMAC-SHA256-signed webhook payloads to configured endpoints on deal events (stage change, new critical alert, analysis complete). Retries on failure with exponential backoff.

**How it works:** `dispatch_webhook(event_type, payload, endpoint_url)` signs the JSON payload with the configured secret (`HMAC-SHA256`), POSTs to the endpoint with a 5-second timeout, retries 3 times with exponential backoff (1s, 2s, 4s). Failures are logged and never re-raised (webhook dispatch is best-effort). Configured endpoints stored in the `webhooks` SQLite table. Used by `infra/automation_engine.py` on workflow events.

**Data in:** Event type and payload dict from the automation engine or alert evaluators; endpoint URLs from the `webhooks` table.

**Data out:** HTTP POST to configured webhook endpoints; dispatch log entry.

---

## `notifications.py` — Email and Slack Notification Dispatch

**What it does:** Sends email (via stdlib `smtplib`) and Slack (via incoming webhooks) notifications for alerts, deadline reminders, and LP report delivery.

**How it works:** `send_email(to, subject, html_body)` — SMTP via `smtplib.SMTP_SSL` using configured `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` env vars. Falls back to `stdout` logging if SMTP is not configured. `send_slack(message, channel)` — HTTP POST to the configured Slack webhook URL. `schedule_notification(event_type, target, delay_hours)` stores a pending notification in the `scheduled_notifications` table; the automation engine processes the queue. Used for: `@-mention` notifications in comments, deadline reminder emails (24h before), LP digest delivery, and critical alert escalations.

**Data in:** Notification requests from `deals/comments.py`, `deals/deal_deadlines.py`, and `alerts/alert_history.py`.

**Data out:** Emails via SMTP; Slack messages via webhook.

---

## `backup.py` — Atomic SQLite Backup

**What it does:** Creates an atomic, gzip-compressed SQLite backup and provides integrity-verified restore.

**How it works:** `create_backup(db_path, backup_dir)` — uses SQLite's `VACUUM INTO 'backup.db'` (atomic, no blocking) to create a clean copy, then gzips it. Returns the backup filename with a UTC timestamp. `restore_backup(backup_path, db_path)` — decompresses, runs `PRAGMA integrity_check`, replaces the live database atomically if the check passes. Serves `GET /api/backup` for on-demand download. Backup files are named `portfolio_YYYYMMDDTHHMMSSZ.db.gz`.

**Data in:** Live SQLite database path; backup directory path.

**Data out:** Gzip-compressed backup file; restore operation on existing database.

---

## `consistency_check.py` — Startup Integrity Verification

**What it does:** Verifies schema and referential integrity on startup without raising (reports issues so the server can start with a warning rather than crashing).

**How it works:** Checks: all expected tables exist, required columns are present (catches partial migrations), FK constraints pass (no orphaned rows), `analysis_runs` can be queried (no corruption). Returns a `ConsistencyReport` with `issues: List[str]`. If issues are found, they are logged at WARNING level and shown on `GET /api/system/info`. Does not block server startup.

**Data in:** SQLite connection from `portfolio/store.py`.

**Data out:** `ConsistencyReport` for `GET /api/system/info`.

---

## `data_retention.py` — Data Retention and GDPR Purge

**What it does:** Configurable per-table retention enforcement and GDPR-compliant data export/purge for analyst and external user data.

**How it works:** `_RETENTION_POLICIES` dict maps table name to retention days (e.g., `audit_events: 2555` = 7 years, `sessions: 30` = 30 days). `enforce_retention(con)` deletes rows older than the policy. `export_user_data(username)` returns all data associated with a username as a JSON blob. `purge_user_data(username)` deletes all personal data while preserving anonymized audit records. Run by a weekly cron trigger or `POST /api/admin/retention`.

**Data in:** SQLite connection; retention policy dict.

**Data out:** Deleted rows; user data export JSON blob.

---

## `automation_engine.py` — Rule-Based Workflow Automation

**What it does:** Fires automated actions on deal events: sends notifications on stage changes, triggers analysis re-runs when override thresholds are exceeded, fires webhooks.

**How it works:** `_AUTOMATION_RULES` list of `(trigger_event, condition_fn, action_fn)` tuples. `fire_event(event_type, deal_id, metadata)` iterates rules matching `event_type`, evaluates `condition_fn(deal_id, metadata, store)`, and calls `action_fn` if True. Example rule: on `stage_change` → `if new_stage == 'ic'` → send IC prep notification. Actions: `send_notification`, `dispatch_webhook`, `enqueue_analysis`. New rules are added by appending to `_AUTOMATION_RULES` — no config file.

**Data in:** Events fired by `deals/deal_stages.py`, `alerts/alerts.py`, and `analysis/deal_overrides.py`.

**Data out:** Notifications via `notifications.py`, webhooks via `webhooks.py`, jobs via `job_queue.py`.

---

## `multi_fund.py` — Multi-Fund Support

**What it does:** Supports running multiple fund portfolios in the same database instance, with deal-to-fund many-to-many assignments and fund-level user scoping.

**How it works:** `funds` and `deal_fund_assignments` tables. `create_fund(name, vintage, strategy)` — adds a fund record. `assign_deal_to_fund(deal_id, fund_id)` — many-to-many assignment. `deals_for_fund(fund_id)` — scoped deal list. User roles can be fund-scoped (a VP for Fund II can't see Fund I deals). The `rbac.py` `check_permission()` function accepts an optional `fund_id` parameter to enforce fund-level scoping.

**Data in:** Fund definitions and deal assignments from admin configuration.

**Data out:** Fund-scoped deal lists and permission checks for multi-fund deployments.

---

## `diligence_requests.py` — Driver-to-Data-Request Mapping

**What it does:** Maps the top modeled RCM drivers to specific data pull requests — "if denial rate is the top driver, here's the exact file we need from the billing team."

**How it works:** Static mapping dict: `{metric_key: DataRequest(description, file_type, contact)}`. `generate_requests(top_drivers)` returns the data requests for a given list of top-driver metrics. Used by `analysis/diligence_questions.py` to add data-room-specific appendices to the diligence question list.

**Data in:** Top driver metrics from `DealAnalysisPacket.variance_attribution`.

**Data out:** `DataRequest` list for the diligence questions appendix.

---

## `response_cache.py` — TTL Response Cache

**What it does:** In-process TTL-based response cache for expensive JSON endpoints (portfolio matrix, comparable analysis, LP report).

**How it works:** `_CACHE` is a dict of `{cache_key: (payload, expires_at)}`. `get(key)` returns the payload if not expired, else `None`. `set(key, payload, ttl_seconds)` stores with expiry. `invalidate(key)` removes a specific key. Cache keys include the deal_id and a hash of the request parameters. Automatic expiry check on `get` — no background sweep needed. Used for `GET /api/portfolio/matrix` (TTL=300s) and comparable analysis (TTL=600s).

**Data in:** Response payloads from expensive computation paths.

**Data out:** Cached responses for subsequent identical requests.

---

## `run_history.py` — CLI Run History

**What it does:** Appends a row to the `run_history` SQLite table after each `rcm-mc run` CLI invocation, tracking when simulations were run and what the key outputs were.

**How it works:** `record_run(config_hash, n_sims, seed, ebitda_p50, moic_p50, output_dir)` inserts a `run_history` row. `list_runs(limit=20)` returns recent runs for the `/runs` CLI command and `/api/runs` endpoint. The run history powers the "what changed since last run?" comparison in `analysis/compare_runs.py`.

**Data in:** Simulation output statistics from `core/kernel.py` or `packet_builder.py`.

**Data out:** Run history rows for the `/runs` page and run comparison.

---

## `provenance.py` — Run Provenance Manifest

**What it does:** Writes a machine-readable JSON provenance manifest for each simulation run, recording which config parameters came from which sources.

**How it works:** Takes the annotated config from `data/sources.py` (with per-field `{value, source, confidence}` tags) and serializes it to `provenance.json` in the run output folder. Also records: git commit hash (if available), Python version, numpy version, seed, timestamp, and a per-metric lineage summary. Used by `reports/full_report.py` for the numbers source map section.

**Data in:** Annotated config dict from `data/sources.py`; system metadata from stdlib.

**Data out:** `provenance.json` in the run output folder; consumed by `full_report.py`.

---

## `trace.py` — Single-Iteration Audit Trace

**What it does:** Expands a single Monte Carlo draw into a detailed step-by-step trace for debugging and analyst explainability. "Show me exactly how draw #47 produced a P50 EBITDA impact of $18M."

**How it works:** Re-runs the simulator with the given seed, intercepts the draw at each step, and records: payer-specific denial rate drawn, DAR-clean-days drawn, claim-level computations, per-bucket EBITDA drag, and final totals. Writes to `trace.json`. Used by the workbench "Explain this draw" button.

**Data in:** Config YAML; specific draw index; seed from the MC run.

**Data out:** `trace.json` with step-by-step computation for the draw.

---

## `output_formats.py` — JSON and CSV Output Utilities

**What it does:** Formats simulation output as JSON or CSV with column documentation. Provides the standard output format for the CLI.

**How it works:** `write_json(result, path)` — serializes `SimulationResult` as indented JSON with a `metadata` section (timestamp, version). `write_csv(result, path)` — flattens key metrics to a single-row CSV for pipeline integration. `COLUMN_DOCS` dict provides column descriptions for the CSV header comment. Used by `cli.py` for the `--output-format` flag.

**Data in:** `SimulationResult` or `DealAnalysisPacket`.

**Data out:** JSON or CSV files in the output directory.

---

## `output_index.py` — HTML Output Folder Index

**What it does:** Generates a navigable HTML index page for simulation output folders, grouping artifacts by kind (reports, charts, data, provenance).

**How it works:** Scans the output directory for known artifact types (`.html`, `.json`, `.csv`, `.png`, `.svg`). Groups into sections: Reports (HTML report, Markdown report), Charts (PNG charts), Data (CSV exports, JSON outputs), Provenance (provenance.json, trace.json). Renders as a self-contained HTML page with `<a>` links. Opened automatically by `demo.py` after a run.

**Data in:** Output directory path; list of files generated by the run.

**Data out:** `index.html` in the output directory.

---

## `profile.py` — Hospital Volume/Mix Profile Alignment

**What it does:** Aligns the volume and payer-mix assumptions between the actual scenario config and the benchmark scenario config, ensuring the comparison is apples-to-apples.

**How it works:** Checks that both configs have the same payer list. If the benchmark uses a different payer-mix distribution than the actual, scales the actual's volumes to match the benchmark's mix proportions (for like-for-like comparison). Returns an `AlignmentReport` noting any adjustments made. Used by `core/kernel.py` before running the simulator.

**Data in:** Actual and benchmark config dicts from `infra/config.py`.

**Data out:** Aligned config pair for `core/kernel.py`.

---

## `taxonomy.py` — Initiative Taxonomy

**What it does:** Provides the standard initiative taxonomy: codes, titles, root cause categories, and typical lever mappings. Used for classifying deals and comparing cross-portfolio playbook performance.

**How it works:** `_INITIATIVE_TAXONOMY` dict maps initiative codes (e.g., `INI_001_DENIAL_MGMT`) to `InitiativeDefinition` objects with title, root cause category, affected metrics, and typical time-to-realization. `classify_initiative(name)` fuzzy-matches a free-text initiative name to the taxonomy. Used by `rcm/initiatives.py` and `pe/value_creation_plan.py`.

**Data in:** Initiative name string for classification; taxonomy dict (static).

**Data out:** `InitiativeDefinition` for initiative tracking and cross-portfolio analytics.

---

## `transparency.py` — Hospital Price Transparency MRF Parser

**What it does:** Parses CMS hospital price transparency Machine-Readable Files (MRFs) to extract negotiated rate distributions for key service lines and procedures.

**How it works:** Downloads the hospital's MRF JSON (URL from the hospital's `price-transparency.json` discovery endpoint). Extracts negotiated rates for the top-20 DRGs by volume (from `data/drg_weights.py`). Computes the distribution of rates across payers (min, P25, P50, P75, max). Returns a `RateDistribution` for each DRG used by `pe_intelligence/` for commercial payer leverage analysis.

**Data in:** Hospital MRF URL from the hospital's public endpoint; DRG list from `data/drg_weights.py`.

**Data out:** `RateDistribution` per DRG for pe_intelligence payer leverage analysis.

---

## `capacity.py` — Capacity and Backlog Modeling

**What it does:** Standalone module for modeling denial-appeals team capacity: queue depth, throughput, and backlog burn-down under different staffing scenarios.

**How it works:** Discrete-time queue simulation (wraps `ml/queueing_model.py` for deal-specific scenarios). `model_capacity(claim_volume, denial_rate, ftes, scenario)` runs the queue model and returns throughput, backlog depth, and estimated time to clear the backlog. Used by the Capacity Planning panel and `analysis/pressure_test.py` to flag when the management plan's timing is unrealistic given current staffing.

**Data in:** Claim volume and denial rate from the deal profile; FTE count from analyst input.

**Data out:** `CapacityModel` result for the pressure test and capacity planning panel.

---

## `_bundle.py` — Diligence-Grade Deliverable Bundle

**What it does:** Assembles a complete, organized diligence deliverable: multi-tab Excel workbook, data request list, and output folder structure ready for IC review.

**How it works:** Creates a timestamped output folder. Calls `exports/xlsx_renderer.py` for the Excel workbook. Generates data request PDFs from `diligence_requests.py`. Writes the HTML report, narrative, and provenance manifest. Returns a `BundleManifest` listing all files and their purposes.

**Data in:** `DealAnalysisPacket`; output directory path.

**Data out:** Organized output folder with all deliverable files.

---

## `_terminal.py` — ANSI Terminal Styling

**What it does:** ANSI terminal styling helpers with automatic color detection. Used by the CLI for colored output (red/amber/green for severity, bold for headers).

**How it works:** Detects color support via: `sys.stdout.isatty()`, `NO_COLOR` environment variable, `TERM=dumb` check. If color is not supported, all styling functions are no-ops. `red(text)`, `amber(text)`, `green(text)`, `bold(text)` wrap text in ANSI codes. `table(rows, headers)` renders a formatted terminal table with column alignment.

**Data in:** Text strings from CLI commands.

**Data out:** ANSI-styled or plain text for terminal output.

---

## Key Concepts

- **Cross-cutting services**: Every other package depends on at least one infra module. Infra modules never import from feature packages — they are the foundation layer.
- **Startup integrity**: `migrations.py` and `consistency_check.py` run on every server start to ensure the schema is current and the data is valid.
- **Best-effort external calls**: Webhooks, notifications, and SMTP failures are logged but never propagate — the platform degrades gracefully when external services are unavailable.
