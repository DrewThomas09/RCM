# RCM-MC Configuration & Operations Guide

Everything you need to deploy, configure, monitor, and maintain RCM-MC in production.

---

## Database

### Location

The database is a single SQLite file. Default: `portfolio.db` in the working directory.

```bash
# Specify on startup
rcm-mc serve --db /data/rcm/portfolio.db --port 8080

# Or via environment
export RCM_MC_DB=/data/rcm/portfolio.db
```

### Schema

Tables are created automatically on first access via `CREATE TABLE IF NOT EXISTS`. Schema changes are managed by the **migration registry** (`rcm_mc/infra/migrations.py`) which runs automatically on server startup.

Key tables:
- `deals` -- deal_id, name, created_at, profile_json, archived_at
- `runs` -- simulation runs linked to deals (FK enforced)
- `deal_notes`, `deal_tags`, `deal_owners`, `deal_deadlines` -- deal metadata
- `analysis_runs` -- cached analysis packets (zlib-compressed JSON)
- `portfolio_snapshots` -- point-in-time deal snapshots for the dashboard
- `audit_events` -- unified audit log (append-only)
- `alert_acks`, `alert_history` -- alert lifecycle
- `webhooks`, `webhook_deliveries` -- webhook config + delivery log
- `custom_metrics` -- user-defined KPIs
- `automation_rules` -- when-this-then-that rules
- `_migrations` -- migration tracking table

### SQLite Settings

Applied on every connection:
- `PRAGMA busy_timeout = 5000` -- wait up to 5s for locks
- `PRAGMA foreign_keys = ON` -- enforce referential integrity
- WAL mode recommended for concurrent reads

### Backup

```bash
# Via API (hot backup, consistent snapshot)
curl http://localhost:8080/api/backup -o backup.db

# Via CLI
cp portfolio.db portfolio_$(date +%Y%m%d).db
```

The `/api/backup` endpoint uses SQLite's native backup API, safe during concurrent writes.

### Migrations

Migrations run automatically on server boot. Check status:

```bash
curl http://localhost:8080/api/migrations
```

Response: `{"total_migrations": 4, "applied": [...], "pending": [], "all_applied": true}`

Current migrations:
1. `deals_archived_at` -- adds archived_at column
2. `audit_events_request_id` -- adds request_id to audit
3. `deal_notes_deleted_at` -- soft-delete for notes
4. `deal_deadlines_owner` -- owner field on deadlines

---

## Authentication

### Modes

1. **Open mode** (default) -- no auth, all endpoints accessible. For local laptop use.
2. **HTTP Basic** -- set via `--auth user:pass` or `RCM_MC_AUTH=user:pass`
3. **Multi-user sessions** -- scrypt passwords, session cookies, CSRF tokens

### Setting Up Multi-User Auth

```bash
# Create admin user
rcm-mc portfolio --db p.db users create --username boss --password "Strong!1" --role admin

# Create analyst
rcm-mc portfolio --db p.db users create --username analyst1 --password "Also!Strong2" --role analyst

# Start with auth enabled
rcm-mc serve --db p.db --auth boss:Strong!1
```

### Session Management

- Sessions stored in SQLite, cleaned up every 100 requests
- CSRF tokens auto-patched by the shell JS on every form submission
- Rate limiting: 5 failed logins per IP per 60 seconds
- Audit log captures all sensitive actions

---

## Server Configuration

### Startup Options

```bash
rcm-mc serve \
  --db /data/portfolio.db \    # Database path
  --port 8080 \                # Listen port
  --host 0.0.0.0 \             # Bind address (0.0.0.0 for network)
  --auth user:pass              # HTTP Basic auth
```

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `RCM_MC_AUTH` | Auth credentials | `user:pass` |
| `RCM_MC_DB` | Database path | `/data/portfolio.db` |
| `ANTHROPIC_API_KEY` | LLM for AI features | `sk-ant-...` |

### Timeouts

- Server socket timeout: 300 seconds
- Per-request timeout: 120 seconds
- SQLite busy_timeout: 5000ms

### Startup Banner

On boot, the server prints:

```
rcm-mc v0.6.0 -- http://127.0.0.1:8080/
  portfolio DB: /data/portfolio.db
  deals:        42
  API docs:     http://127.0.0.1:8080/api/docs
  started in:   234ms
  Ctrl+C to stop
```

---

## Monitoring

### Health Checks

| Endpoint | Use Case | Response |
|----------|----------|----------|
| `GET /health` | Simple liveness | `ok` (text) |
| `GET /ready` | K8s readiness | `{"ready": true}` or 503 |
| `GET /api/health` | Dashboard status | deal count, version, audit failures |
| `GET /api/health/deep` | Deep component check | DB latency, migrations, HCRIS age, disk |
| `HEAD /api/health` | Lightweight probe | Headers only, no body |

### Observability

| Endpoint | What |
|----------|------|
| `GET /api/metrics` | p50/p95/p99 response times, request count, error count |
| `GET /api/system/info` | Version, Python, platform, DB size, table count |

### Access Logs

Every request emits a structured JSON line to stderr:

```json
{"ts": "2026-04-16T10:00:00+00:00", "request_id": "a3f09b2c1e4d7890",
 "method": "GET", "path": "/api/deals", "status": 200,
 "duration_ms": 4.23, "user_id": "boss", "client": "10.0.0.5"}
```

Sensitive data (password, token, secret, key, auth) is masked in log paths.

### Audit Log

All sensitive actions are recorded in the `audit_events` table:

```bash
# Via API
curl http://localhost:8080/api/deals/acme/audit

# Cleanup old events
# Automatic via audit_log.cleanup_old_events(store, retention_days=365)
```

---

## Security

### HTTP Headers (HTML Responses)

| Header | Value |
|--------|-------|
| Content-Security-Policy | `default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com; ...` |
| X-Content-Type-Options | `nosniff` |
| X-Frame-Options | `DENY` |
| Referrer-Policy | `strict-origin-when-cross-origin` |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` |

### Rate Limiting

| Scope | Limit |
|-------|-------|
| DELETE endpoints | 10/hour per IP |
| Login attempts | 5 failures per 60s per IP |
| Data refresh | 1/hour per source |
| POST body size | 10 MB max |

### CORS

All JSON responses include `Access-Control-Allow-Origin: *`. OPTIONS preflight returns 204 with max-age 86400.

### Input Validation

- All integer query params clamped via `_clamp_int`
- Search queries truncated to 500 chars
- All user strings HTML-escaped before rendering
- CSV exports defanged for Excel formula injection
- Parameterized SQL everywhere (no f-strings in queries)

---

## Webhook Configuration

### Register a Webhook

```bash
curl -X POST http://localhost:8080/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-system.com/hook", "secret": "s3cret", "events": ["deal.created", "deal.deleted"]}'
```

### Test Delivery

```bash
curl http://localhost:8080/api/webhooks/test
# Returns: {"event": "test.ping", "webhooks_matched": 1}
```

### Delivery

- HMAC-SHA256 signature in `X-RCM-Signature` header
- 3 retries with exponential backoff (2^attempt seconds)
- Async delivery (doesn't block the request)
- Full delivery log in `webhook_deliveries` table

---

## Data Sources

### HCRIS (Hospital Cost Report)

- Source: CMS public data (6,000+ hospitals)
- Local cache: `rcm_mc/data/hcris.csv.gz`
- Refresh: `rcm-mc data refresh hcris`
- Staleness warning: automatic at >90 days old
- Check age: `GET /api/system/info` or `hcris_cache_age_days()`

### Other Sources

| Source | Module | Command |
|--------|--------|---------|
| HCRIS | `data/hcris.py` | `rcm-mc data refresh hcris` |
| Care Compare | `data/cms_care_compare.py` | `rcm-mc data refresh care_compare` |
| IRS 990 | `data/irs990_loader.py` | `rcm-mc data refresh irs990` |
| Utilization | `data/cms_utilization.py` | `rcm-mc data refresh utilization` |

---

## File Layout

```
portfolio.db              <-- The database (auto-created)
rcm_mc/
  __init__.py             <-- __version__ = "0.6.0"
  server.py               <-- HTTP server (10K lines)
  cli.py                  <-- CLI entry point
  portfolio_cmd.py        <-- Portfolio subcommands
  pe_cli.py               <-- PE math subcommands
  api.py                  <-- Programmatic API
  core/                   <-- Simulator, kernel, calibration
  pe/                     <-- PE math, bridge, MOIC/IRR
  mc/                     <-- Monte Carlo engine
  analysis/               <-- Packet builder, completeness, risk flags
  data/                   <-- HCRIS, IRS 990, data ingest
  portfolio/              <-- Store, snapshots, dashboard
  deals/                  <-- Notes, tags, owners, deadlines, health
  alerts/                 <-- Alert fire/ack/snooze lifecycle
  auth/                   <-- Auth, sessions, audit log
  ai/                     <-- LLM client, memo writer, QA, chat
  exports/                <-- Renderers (HTML, XLSX, PPTX, CSV, ZIP)
  ui/                     <-- Page renderers (shell, workbench, pages)
  scenarios/              <-- Scenario overlay, shocks
  infra/                  <-- Config, migrations, webhooks, job queue
  reports/                <-- Report generators (LP update, exit memo)
tests/
  test_*.py               <-- 225 test files, 2,883 tests
docs/
  *.md                    <-- Documentation
pyproject.toml            <-- Build config, deps, tool settings
```
