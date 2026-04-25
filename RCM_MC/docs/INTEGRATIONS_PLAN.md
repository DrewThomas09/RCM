# Integrations + API Architecture Plan

PE firms don't replace their existing tooling — they layer new
capability onto a stack that already includes Salesforce or DealCloud
for pipeline, Datasite or Intralinks for data rooms, Excel for
every analyst's working layer, Slack for team channels, iLEVEL or
Allvue for portfolio management. The platform's value increases as
it plugs cleanly into that stack rather than asking the firm to
move their workflow.

This document maps the integrations PE firms ask for, ranks them by
value × effort, and designs the API architecture to support them.

## The PE software stack we have to live alongside

| Layer | Tools | Where the platform plugs in |
|---|---|---|
| **CRM / Pipeline** | Salesforce, DealCloud, Affinity, HubSpot | Inbound: deal records create platform deals. Outbound: stage advancements + closed-won update CRM. |
| **Data room** | Intralinks (SS&C), Datasite, iDeals, Firmex | Inbound: drop a CIM PDF / financials, platform extracts metrics (per the CIM extraction plan). Outbound: published memos pushed back into the room for the seller to see. |
| **Portfolio management** | iLEVEL (S&P), Allvue, Backstop | Outbound: post-close monitoring metrics + KPIs feed iLEVEL for LP reporting. |
| **Spreadsheets** | Excel (Microsoft 365), Google Sheets | Bidirectional: pull live platform data into a sheet; write analyst overrides back. |
| **Communication** | Slack, Microsoft Teams, email (Outlook) | Outbound: alerts, notifications, weekly digests. Slack threads on specific deals. |
| **Document collaboration** | SharePoint, Box, Google Drive | Outbound: published IC memos saved here for archive. |
| **Deal-comp data** | PitchBook, S&P CapIQ, Preqin | Inbound: completed transaction multiples for our backtests. |

The common pattern: **inbound data, outbound notifications**. The
platform sits in the middle of a partner's workflow, never replacing
end systems but enriching what flows through them.

## Ranking by PE firm impact / effort

| # | Integration | PE-Firm Impact | Build Effort | Recommend |
|---|---|---|---|---|
| 1 | Excel plugin (read live data + write overrides) | High — every analyst, every day | Medium | **Build** |
| 2 | Slack notifications | High — team-channel alerts | Low | **Build** |
| 3 | Webhooks (generic outbound) | High — enables 80% of integrations | Low | **Build first** |
| 4 | REST API (full read/write) | High — partner-developer self-service | Medium | **Build first** |
| 5 | DealCloud / Salesforce CRM sync | High — pipeline source-of-truth | High | **Build (after API)** |
| 6 | Datasite / Intralinks data room sync | Medium-high — diligence-doc inbound | Medium | **Build** |
| 7 | iLEVEL / Allvue portfolio sync | Medium — post-close LP-reporting | High | Defer to enterprise tier |
| 8 | PitchBook / CapIQ deal-comp inbound | Medium — backtest validity | Low (paid feed) | Defer; cust-licensed pass-through |
| 9 | Microsoft Teams notifications | Low-medium | Low (similar to Slack) | Build alongside Slack |
| 10 | SharePoint / Box archive | Low-medium — convenience | Low | Build later |

The right sequence: **API + webhooks first**, then **Slack / Excel /
data room** (the three highest-leverage user-facing integrations),
then **CRM sync**, then enterprise-tier connectors.

---

## API architecture

### Surface design

The platform already has internal HTTP routes. The integration API
is a separate surface under `/api/v1/*` with three properties:

  1. **Versioned**: `/api/v1/...` so we can evolve without breaking
     consumers.
  2. **Auth-required**: every call needs an API token (separate from
     session cookie).
  3. **Stable contract**: schema changes are additive only;
     deprecation requires 6-month notice + version bump.

### Authentication

Two complementary auth flows:

  - **API tokens** (machine-to-machine): user generates a token in
    `/preferences/api-tokens`. Token format: 32-byte URL-safe
    random, prefixed `rcm_`. Sent via
    `Authorization: Bearer rcm_xxxxx`. Tokens scope to a single
    user's permissions.
  - **OAuth 2** (3rd-party apps): when an external app
    (Salesforce, Slack, Excel plugin) wants to act on behalf of a
    user. Standard OAuth 2 authorization code flow. Tokens have
    finite scope (e.g., `deals:read` vs `deals:write`).

Existing scrypt password + session-cookie auth stays as-is for
browser users. The API surface adds these without disrupting it.

### Rate limiting

Per-token: 1000 req/min standard, 100 req/min during cold-start of
a token (first 5 min after generation). Exceeded → 429 with a
`Retry-After` header.

Per-IP: 100 req/min from anonymous (no token), 5000 req/min from
authenticated.

### Endpoint surface

```
GET    /api/v1/deals
GET    /api/v1/deals/{deal_id}
POST   /api/v1/deals
PATCH  /api/v1/deals/{deal_id}
DELETE /api/v1/deals/{deal_id}

GET    /api/v1/deals/{deal_id}/packet
POST   /api/v1/deals/{deal_id}/packet/build
GET    /api/v1/deals/{deal_id}/packet/sections/{section}

GET    /api/v1/deals/{deal_id}/comps
POST   /api/v1/deals/{deal_id}/comps/find

GET    /api/v1/deals/{deal_id}/predictions
GET    /api/v1/deals/{deal_id}/predictions/{metric}

GET    /api/v1/deals/{deal_id}/bridge
POST   /api/v1/deals/{deal_id}/bridge/compute

GET    /api/v1/deals/{deal_id}/scenarios
POST   /api/v1/deals/{deal_id}/scenarios

GET    /api/v1/deals/{deal_id}/risks
GET    /api/v1/deals/{deal_id}/diligence-questions

GET    /api/v1/screening
POST   /api/v1/screening/run

GET    /api/v1/data-sources
GET    /api/v1/models/quality
GET    /api/v1/models/{model_id}/predictions

POST   /api/v1/exports/{format}
       # format ∈ xlsx | docx | pdf | md | json

POST   /api/v1/webhooks
GET    /api/v1/webhooks
DELETE /api/v1/webhooks/{webhook_id}

GET    /api/v1/health
GET    /api/v1/openapi.json   # full spec
```

### Response shape

JSON, snake_case fields. Standard envelope:

```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_xxx",
    "model_version": "v3.2",
    "as_of": "2025-01-15T10:00:00Z"
  }
}
```

Errors: 4xx for client mistakes, 5xx for ours; both with
machine-readable `error.code` + human-readable `error.message`:

```json
{
  "error": {
    "code": "deal_not_found",
    "message": "No deal with ID 'aurora' visible to your token.",
    "details": {"deal_id": "aurora"}
  }
}
```

### Pagination

Cursor-based; default page size 50, max 200. Response includes
`meta.next_cursor` when more available.

### OpenAPI spec

Auto-generated from a single source-of-truth spec at
`/api/v1/openapi.json`. Existing platform `/api/openapi.json`
becomes the v1-public spec. Spec is committed to the repo;
breaking-change linting on PR via spectral or similar.

---

## Webhooks (the integration unlock)

Webhooks make ~80% of integrations possible without building each
one explicitly. Customer registers a URL; platform POSTs JSON
payloads on subscribed events.

### Event taxonomy

```
deal.created
deal.stage_advanced
deal.archived

packet.built
packet.section_updated

prediction.recorded     # from auto_record decorator
prediction.actual_arrived  # when actuals reconcile

alert.fired
alert.acknowledged

comment.posted
comment.mention   # @username triggered notification

risk.flagged
distress.threshold_crossed

drift.detected      # model drift event
```

### Payload shape

```json
{
  "id": "evt_xxx",
  "type": "packet.built",
  "created_at": "2025-01-15T10:00:00Z",
  "data": {
    "deal_id": "aurora",
    "packet_id": "pkt_xxx",
    "completeness_grade": "A",
    "ebitda_uplift_mm": 12.0,
    "url": "https://app.example.com/deal/aurora/profile"
  },
  "delivery_attempt": 1
}
```

### Reliability

- **Signed**: HMAC-SHA256 signature over the payload using the
  webhook's secret, sent in `X-RCM-Signature` header. Receivers
  verify before processing.
- **Retried**: 5 retries with exponential backoff (1m / 5m / 25m
  / 2h / 12h). After 5 failures, webhook is marked unhealthy +
  user notified.
- **Replayable**: customer can re-send any event from the last 7
  days via the `/api/v1/webhooks/{id}/events/{event_id}/replay`
  endpoint.

---

## Per-integration plans (top 4 by impact)

### 1. Excel plugin (Microsoft Office Add-in)

**What it does**: live read of platform data in Excel cells +
write-back of analyst overrides.

**User flow**:
1. Analyst opens Excel, finds the "RCM-MC" ribbon (installed
   from Microsoft AppSource).
2. Click "Connect" → OAuth flow opens browser, returns token.
3. In a cell: `=RCM_DEAL("aurora", "ebitda_target_mm")` →
   live value pulled from the platform.
4. Range-functions: `=RCM_BRIDGE_TABLE("aurora")` returns the
   per-lever EBITDA bridge as a multi-cell array.
5. Override flow: analyst types a value into an
   override-marked cell → Excel plugin POSTs to
   `/api/v1/deals/{deal_id}/overrides` → next refresh shows
   the override is sticky.

**Build effort**: 6-8 weeks. Three pieces — Office Add-in
(JavaScript/HTML, deployed via Microsoft AppSource), API endpoints
to support the function calls (mostly already in the v1 surface),
auth flow.

**Why it matters**: Excel is where the analyst lives. A platform
the analyst can pull into their own workbook gets used 10× more
than one they have to leave Excel to visit.

### 2. Slack integration

**What it does**: alerts + notifications + slash commands.

**User flow**:
1. Admin connects Slack workspace via OAuth at
   `/integrations/slack`.
2. Per-channel routing rules ('alerts to #deals-active;
   distress flags to #partner-review').
3. Slash commands:
   - `/rcm deal aurora` → returns a card with current packet
     summary
   - `/rcm screen sector=asc state=tx` → returns top 5 candidates
   - `/rcm health` → portfolio summary
4. Notifications: every webhook event the user subscribes to
   becomes a Slack message in the configured channel, with
   action buttons (Ack alert / Open deal / Snooze).

**Build effort**: 3-4 weeks. Slack's API is well-documented;
mostly UI + event-fanout work.

**Why it matters**: PE shops live in Slack. Notifications that
land in Slack get triaged in real-time; emails sit unread for
days.

### 3. Data room ingestion (Datasite / Intralinks)

**What it does**: when a partner gets a CIM in Datasite, the
platform pulls it automatically and runs the CIM-extraction
pipeline (per the next-cycle plan).

**User flow**:
1. Admin connects Datasite via OAuth.
2. Per-deal mapping: 'this Datasite room maps to this RCM-MC
   deal'.
3. New documents in the room trigger webhook → platform
   downloads + runs CIM extraction pipeline → extracted values
   land in `DealCandidate`.
4. Analyst sees the deal already populated when they open
   it on the platform.

**Build effort**: 6-8 weeks. Datasite + Intralinks have private
APIs; deeper integration partnership work. Initial v1 supports
Datasite only; Intralinks v2.

**Why it matters**: closes the loop between 'banker sends a
CIM' and 'analyst has a screening result' — currently a 4-8 hour
manual gap.

### 4. CRM sync (DealCloud + Salesforce)

**What it does**: bidirectional pipeline state sync.

**User flow**:
1. Admin connects DealCloud (or Salesforce) via OAuth.
2. Per-firm mapping: which CRM stages map to which RCM-MC
   pipeline stages.
3. New deal in CRM → webhook → platform creates matching deal.
4. Stage advanced in platform → webhook → CRM updates.
5. Closed-won → CRM marks; platform archives + initiates
   portfolio-monitoring sync.

**Build effort**: 8-10 weeks per CRM. DealCloud has good APIs;
Salesforce is a deeper integration with managed-package work.

**Why it matters**: removes the duplicate-data-entry pain
('we updated the deal in CRM AND in RCM-MC AND in our spreadsheet'
becomes 'updated in CRM, propagated automatically').

---

## Build sequence

### Phase 1 — Foundation (4 weeks)

1. **Week 1**: API tokens + per-token rate limiting.
2. **Week 2**: OpenAPI spec finalized + spectral linting in CI.
3. **Week 3**: Webhooks subsystem (registration / delivery /
   retry / signing / replay).
4. **Week 4**: API documentation site (auto-generated from
   OpenAPI) + Postman collection.

### Phase 2 — Core endpoints (6 weeks)

1. **Weeks 1-2**: Deal CRUD + packet endpoints.
2. **Weeks 3-4**: Predictions + bridge + scenarios endpoints.
3. **Weeks 5-6**: Screening + exports + risks/diligence-questions
   endpoints.

### Phase 3 — High-impact integrations (10 weeks)

1. **Weeks 1-3**: Slack integration (lower risk; well-documented
   API).
2. **Weeks 4-9**: Excel Office Add-in (Microsoft AppSource
   submission cycle takes 1-2 weeks of those).
3. **Week 10**: OAuth 2 flow hardening based on Slack + Excel
   feedback.

### Phase 4 — Data room + CRM (12 weeks)

1. **Weeks 1-6**: Datasite integration (priority — most-cited
   data-room vendor among PE firms).
2. **Weeks 7-12**: DealCloud sync (priority — most-cited PE-
   specific CRM).

### Phase 5 — Enterprise add-ons (8 weeks)

1. **Weeks 1-4**: Salesforce managed package.
2. **Weeks 5-8**: iLEVEL or Allvue post-close sync.

**Total: 40 weeks across 5 phases.** Parallelized across two
engineers: ~22 weeks.

---

## Pricing tier mapping

| Integration | Tier |
|---|---|
| API tokens (read-only) | Pro |
| API tokens (write) | Pro |
| Webhooks | Pro |
| Excel plugin | Pro |
| Slack | Pro |
| Datasite | Pro |
| Microsoft Teams | Pro (after Slack) |
| DealCloud sync | Enterprise |
| Salesforce sync | Enterprise (managed package) |
| iLEVEL / Allvue | Enterprise |
| OAuth-as-3rd-party (we authorize partner apps) | Enterprise |
| Custom webhook events / private API endpoints | Enterprise |

The Pro tier needs to ship with workable integrations or it loses
to Bloomberg + manual workflows. Enterprise differentiation comes
from the high-effort ones — CRM, portfolio management, custom
flows — that justify the $150K+ base.

---

## API stability commitments

PE-customer trust requires explicit guarantees:

1. **Backward compatibility**: existing v1 endpoints + response
   shapes will not break for the lifetime of v1. New fields can
   be added to responses; existing fields cannot be removed.
2. **Deprecation timeline**: deprecated endpoints continue to work
   for 6 months after deprecation announcement, with clear
   `Sunset` and `Deprecation` headers.
3. **Version cadence**: at most one major version per 18 months.
   v2 ships when v1's accumulated migration cost outweighs its
   continued maintenance.
4. **Status page**: `/api/v1/health` always lives at this URL;
   public uptime + incidents page surfaces every degradation.

These commitments turn into contract terms for Enterprise
customers.

---

## Build vs partner

For each integration above, a strategic question: build ourselves
or partner with a connector vendor (Workato / Zapier / Tray.io /
Boomi)?

  - **Build ourselves**: Excel, Slack, Datasite, DealCloud — the
    most-used integrations by PE customers, justify direct
    investment.
  - **Connector partner**: Microsoft Teams, SharePoint, Google
    Workspace, niche CRMs — long tail. Listing on Workato /
    Zapier reaches 1000s of customers without our build cost.
  - **Hybrid**: webhook system serves both — we build first-party
    Slack/Excel/etc. AND publish a Zapier connector on top of
    the webhook system. Customer chooses the depth they want.

Recommendation: build the top-4 first-party + publish a Zapier
connector once the v1 API stabilizes. The connector hits 90% of
the long tail without us writing 50 separate integrations.

---

## Security review

Every integration introduces attack surface:

- **API tokens**: scope-limit + revocation + per-token audit log.
  Tokens shown once at generation; never retrievable later.
- **OAuth**: state parameter mandatory; PKCE for public clients;
  redirect-URL whitelisting per app.
- **Webhooks**: signed payloads (HMAC-SHA256) so receivers verify
  origin; rotate secrets on demand.
- **3rd-party app review**: every app requesting OAuth scopes goes
  through our review (manual for v1; automated for v2). Apps
  showing up in `/integrations` listing are vetted.

Enterprise customers get additional controls: IP-allowlist on
tokens, mandatory MFA for OAuth-bearing accounts, longer audit-log
retention.

---

## What we don't try to build

- **A no-code workflow builder** like Workato or Zapier
  internally. That's a different product company; we'd lose
  focus. Publishing connectors *to* those platforms is the
  right move.
- **A full BI tool**. Tableau and Power BI win every time.
  Provide good API access + pre-built data model exports;
  customers point their BI tool at us.
- **A CRM**. PE firms have CRMs. We sync, we don't replace.
- **A document management system**. SharePoint / Box / Google
  Drive own this. We push docs there.

The platform's job is the **diligence math + workflow on top**.
The job of integrations is to make sure that workflow plugs
cleanly into the firm's existing tools — not to replace them.
