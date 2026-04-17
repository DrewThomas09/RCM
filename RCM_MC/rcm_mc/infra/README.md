# Infra

Platform infrastructure: configuration, logging, job queuing, migrations, notifications, backup, provenance, and API support. Provides the cross-cutting services that every other package depends on.

| File | Purpose |
|------|---------|
| `config.py` | YAML config loading, validation, and canonical payer name normalization |
| `logger.py` | Centralized `rcm_mc` logger with StreamHandler setup |
| `profile.py` | Hospital volume/mix profile alignment between actual and benchmark scenarios |
| `job_queue.py` | In-process simulation job queue with a single worker thread; partners post jobs via the web UI and poll for completion |
| `migrations.py` | Idempotent schema migration registry; runs all pending ALTER TABLE / CREATE INDEX on startup |
| `notifications.py` | Email (stdlib `smtplib`) and Slack (incoming webhooks) notification dispatch with scheduling |
| `backup.py` | Atomic SQLite backup via `VACUUM INTO` + gzip, restore with integrity verification |
| `consistency_check.py` | Startup-time schema and referential integrity verification; reports issues without raising |
| `data_retention.py` | Configurable per-table retention enforcement and GDPR-style data export |
| `automation_engine.py` | Rule-based workflow automation: fires actions on stage changes, metric thresholds, and risk flags |
| `multi_fund.py` | Multi-fund support with fund metadata and deal-to-fund many-to-many assignments |
| `diligence_requests.py` | Maps top modeled drivers to specific data pull requests for validation |
| `openapi.py` | Auto-generated OpenAPI 3.0 spec and `/api/docs` Swagger UI viewer |
| `webhooks.py` | HMAC-SHA256-signed webhook dispatch with three retries and exponential backoff |
| `rate_limit.py` | In-memory sliding-window rate limiter for expensive endpoints |
| `response_cache.py` | TTL-based in-process response cache for expensive JSON endpoints |
| `run_history.py` | SQLite-based run history: auto-appends a row after each CLI run |
| `provenance.py` | Machine-readable run provenance manifest with per-metric lineage |
| `trace.py` | Single-iteration audit trace: expands one MC draw for actual vs benchmark comparison |
| `output_formats.py` | JSON and CSV output format utilities with column documentation |
| `output_index.py` | Auto-generated navigable HTML index for output folders, grouping artifacts by kind |
| `taxonomy.py` | Initiative taxonomy: codes, titles, root causes, and typical levers |
| `transparency.py` | Hospital price transparency MRF file parser producing rate distribution summaries |
| `capacity.py` | Standalone capacity/backlog modeling (unlimited, outsourced, etc.) |
| `_bundle.py` | Diligence-grade deliverable bundle: multi-tab Excel workbook + data requests + organized output folder |
| `_terminal.py` | ANSI terminal styling helpers with automatic color detection (TTY, `NO_COLOR`, `TERM=dumb`) |
