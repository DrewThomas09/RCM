# RCM-MC API Reference

Complete reference for all 52 API endpoints (56 methods). Base URL: `http://localhost:8080`.

Interactive docs: **`GET /api/docs`** (Swagger UI) | Machine-readable: **`GET /api/openapi.json`**

---

## Response Headers (All JSON Endpoints)

Every JSON response includes:

| Header | Example | Purpose |
|--------|---------|---------|
| `X-Request-Id` | `a3f09b2c1e4d7890` | 16-char correlation ID for debugging |
| `X-Response-Time` | `4.2ms` | Server-side processing time |
| `X-API-Version` | `2024-01` | API version for future compatibility |
| `Access-Control-Allow-Origin` | `*` | CORS -- all origins allowed |
| `Content-Encoding` | `gzip` | Automatic for responses >1KB when client accepts |
| `Vary` | `Accept-Encoding` | Cache key differentiation for gzip |
| `ETag` | `"a1b2c3d4e5f67890"` | On analysis packet responses (enables 304) |
| `Retry-After` | `42` | On 429 rate-limited responses |

---

## Authentication

When auth is configured (`RCM_MC_AUTH=user:pass` or `--auth user:pass`):
- **Session-based**: `POST /api/login` with `username` + `password`, returns session cookie
- **HTTP Basic**: `Authorization: Basic <base64>` on any request
- **CSRF**: Forms auto-patched via JS; API calls need `X-CSRF-Token` header

When auth is not configured (default for local use), all endpoints are open.

---

## Idempotency

Add `Idempotency-Key: <unique-string>` to any POST request. If the same key is sent again, the cached response is returned without re-executing the operation. Keys are stored in a 1000-entry LRU cache.

---

## Infrastructure Endpoints

### `GET /api`
API route index -- lists all available endpoints.

**Response:**
```json
{
  "endpoints": [
    {"method": "GET", "path": "/api/deals", "summary": "List all deals", "tags": ["Deals"]}
  ],
  "count": 56,
  "docs_url": "/api/docs",
  "openapi_url": "/api/openapi.json"
}
```

### `GET /api/health`
Lightweight health check. Returns deal count, DB status, version.

### `GET /api/health/deep`
Component-level health check with DB latency, migration status, HCRIS data freshness, disk usage.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.6.0",
  "checks": {
    "db": {"status": "ok", "latency_ms": 0.42},
    "migrations": {"status": "ok", "applied": 4, "pending": 0},
    "hcris_data": {"status": "ok", "age_days": 12.3},
    "disk": {"status": "ok", "db_size_mb": 4.56}
  }
}
```

### `GET /ready`
Kubernetes readiness probe. Returns `{"ready": true}` or 503.

### `GET /api/metrics`
Request observability: p50/p95/p99 response times, request count, error count.

### `GET /api/system/info`
Version, Python version, platform, DB path, DB size, table count, deal count.

### `GET /api/migrations`
Schema migration status: total, applied, pending, all_applied flag.

### `GET /api/backup`
Downloads a full SQLite database backup as `rcm_mc_backup.db`. Uses SQLite's native backup API for a consistent snapshot.

---

## Deal Endpoints

### `GET /api/deals`
Paginated deal list from portfolio snapshots.

**Query params:**
- `limit` (int, default 100, max 1000)
- `offset` (int, default 0)
- `sort` (string: name, created_at, deal_id, stage, moic, irr, entry_ebitda, covenant_status)
- `dir` (string: asc or desc, default desc)
- `include_archived` (string: "1" to include)

**Response:**
```json
{
  "deals": [...],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

### `DELETE /api/deals/{deal_id}`
Delete a deal and ALL associated data (cascade across 23 child tables). Rate-limited: 10 deletes/hour per IP.

### `GET /api/deals/{deal_id}/summary`
Lightweight summary: name, stage, health score, trend, archived status.

### `GET /api/deals/{deal_id}/health`
Health score (0-100) with component breakdown showing each deduction.

### `GET /api/deals/{deal_id}/completeness`
Profile completeness vs the 38-metric RCM registry. Returns grade (A/B/C/D), coverage %, present count, missing keys.

### `GET /api/deals/{deal_id}/validate`
Data quality check: profile sparseness, bed_count validity, naming.

### `GET /api/deals/{deal_id}/checklist`
IC prep readiness: deal registered? analysis built? notes recorded? plan created? health score computed? Returns `ready_for_ic: true/false`.

### `GET /api/deals/{deal_id}/counts`
Badge counts in one call: notes, tags, overrides, stage, health score + band.

### `GET /api/deals/{deal_id}/timeline`
Activity timeline with filtering.

**Query params:** `days` (1-365, default 90), `type` (event type filter), `limit` (max results)

### `GET /api/deals/{deal_id}/notes`
Paginated notes list. **Query params:** `limit`, `offset`

### `GET /api/deals/{deal_id}/tags`
Array of tag strings for the deal.

### `GET /api/deals/{deal_id}/stage`
Current stage + full stage history (newest first).

### `GET /api/deals/{deal_id}/audit`
Filtered audit events for this deal. **Query params:** `limit` (default 50)

### `GET /api/deals/{deal_id}/similar`
Find deals with similar numeric profiles (normalized distance scoring). **Query params:** `limit` (1-20, default 5)

### `GET /api/deals/{deal_id}/peers`
Side-by-side metric comparisons (target vs peer with delta) for bed_count, denial_rate, days_in_ar, net_collection_rate, cost_to_collect, clean_claim_rate.

### `GET /api/deals/{deal_id}/diffs`
Field-level changes between consecutive snapshots. Shows `{from, to}` for each changed field.

### `GET /api/deals/{deal_id}/overrides`
List analyst overrides for a deal.

### `PUT /api/deals/{deal_id}/overrides/{key}`
Set one override. Body: `{"value": ..., "reason": "..."}`.

### `DELETE /api/deals/{deal_id}/overrides/{key}`
Remove one override.

### `PATCH /api/deals/{deal_id}/profile`
Merge individual fields into a deal's profile. Body: `{"field_name": value}`.

### `POST /api/deals/{deal_id}/archive`
Soft-delete (set archived_at). Deal hidden from dashboard by default.

### `POST /api/deals/{deal_id}/unarchive`
Restore an archived deal.

### `POST /api/deals/{deal_id}/pin`
Pin deal to dashboard top (adds "pinned" tag).

### `POST /api/deals/{deal_id}/unpin`
Remove pin.

### `POST /api/deals/{deal_id}/duplicate`
Clone deal with new ID. Body: `{"new_deal_id": "...", "new_name": "..."}`.

### `GET /api/deals/{deal_id}/export-links`
All available export URLs for a deal (HTML, JSON, CSV, XLSX, PPTX, package, provenance, risks, sensitivity).

### `GET /api/deals/{deal_id}/package`
Generate and download a full diligence ZIP bundle in one call.

### `GET /api/deals/{deal_id}/report`
HTML summary report: health badge, stage, tags, recent notes, links to analysis + package.

---

## AI Endpoints

### `GET /api/deals/{deal_id}/memo`
Generate a diligence memo. **Query params:** `llm=1` to use LLM (default: template-based).

**Response:**
```json
{
  "sections": {"executive_summary": {"text": "...", "fact_checks_passed": true}},
  "fact_check_warnings": [],
  "llm_used": false,
  "cost_usd": 0.0
}
```

### `GET /api/deals/{deal_id}/qa`
Document QA. **Query params:** `q` (required, max 500 chars).

### `POST /api/chat`
Conversational AI with multi-turn sessions. Body: `{"message": "...", "session_id": "..."}`.

---

## Bulk / Import Endpoints

### `POST /api/deals/import`
Import deals from JSON array. Body: `[{"deal_id": "...", "name": "...", "profile": {...}}]`. Max 500.

### `POST /api/deals/import-csv`
Import deals from CSV text. Body: raw CSV with `deal_id,name,...` header.

### `POST /api/deals/bulk`
Batch operations. Body: `{"action": "archive|unarchive|delete|tag", "deal_ids": [...], "tag": "..."}`. Max 100.

### `POST /api/portfolio/register`
Register a portfolio snapshot. Body: `{"deal_id": "...", "stage": "loi|spa|...", "notes": "..."}`.

---

## Portfolio Endpoints

### `GET /api/portfolio/summary`
Fund-level rollup: deal count, stage funnel, weighted MOIC/IRR, covenant status, active/critical alerts.

### `GET /api/portfolio/health`
Health score band distribution (green/amber/red/unknown) + average score.

### `GET /api/portfolio/matrix`
Cross-deal metric matrix. **Query params:** `metrics` (comma-separated, optional filter).

### `GET /api/portfolio/alerts`
Alert counts by severity, by kind, by deal, top 10 most-alerted deals.

### `GET /api/portfolio/attribution`
Fund-level performance attribution.

### `GET /portfolio/monte-carlo`
Correlated portfolio Monte Carlo simulation.

### `GET /api/export/portfolio.csv`
Download portfolio summary as CSV.

---

## Search Endpoints

### `GET /api/deals/search`
Search deals by name or ID (case-insensitive). **Query params:** `q`, `limit` (default 20).

### `GET /api/search`
Cross-deal full-text search across notes, overrides, and metadata. **Query params:** `q`, `limit`.

### `GET /api/data/hospitals`
Fuzzy hospital search (typeahead) from HCRIS data. **Query params:** `q`, `limit`.

### `GET /api/deals/stats`
Aggregate counts: total, active, archived, stage distribution.

---

## Settings Endpoints

### `GET /api/automations`
List automation rules (including 5 presets).

### `GET /api/metrics/custom`
List custom metrics.

### `POST /api/metrics/custom`
Register a custom metric. Body: `{"metric_key": "...", "display_name": "...", "unit": "pct", "directionality": "higher_is_better"}`.

### `DELETE /api/metrics/custom/{metric_key}`
Delete a custom metric.

### `GET /api/webhooks`
List registered webhooks.

### `POST /api/webhooks`
Register a webhook. Body: `{"url": "...", "secret": "...", "events": ["deal.created"]}`.

### `GET /api/webhooks/test`
Send a synchronous `test.ping` event to all active webhooks. Verify your webhook URL works.

### `GET /api/scenarios`
List preset payer policy shock scenarios.

### `GET /api/calibration/priors`
Per-payer prior means (IDR, FWR, DAR) from stored simulation runs.

### `GET /api/surrogate/schema`
Surrogate model training data schema and model status.

---

## Analysis Endpoints

### `GET /api/analysis/{deal_id}`
Build or return cached analysis packet. Returns full `DealAnalysisPacket` JSON with ETag support.

**Query params:** `scenario`, `as_of` (YYYY-MM-DD), `force=1`.

Supports conditional GET: send `If-None-Match: <etag>` to get 304 Not Modified.

### `GET /api/analysis/{deal_id}/export`
Export analysis. **Query params:** `format` (html, json, csv, xlsx, pptx, package, questions).

### `POST /api/analysis/{deal_id}/simulate/v2`
Run v2 Monte Carlo simulation.

### `POST /api/analysis/{deal_id}/simulate/compare`
Compare named MC scenarios side-by-side.

---

## Webhook Events

The following events fire to configured webhooks:

| Event | When |
|-------|------|
| `deal.deleted` | Deal permanently deleted |
| `deal.archived` | Deal soft-deleted |
| `deal.created` | Deal cloned via duplicate |
| `test.ping` | Manual test via `/api/webhooks/test` |

Delivery: HMAC-SHA256 signed (`X-RCM-Signature` header), 3 retries with exponential backoff, async by default.
