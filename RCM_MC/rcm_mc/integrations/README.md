# Integrations

External system integrations for CRM sync, data export, and deal-tracking workflow connectivity.

---

## `integration_hub.py` — CRM Sync and Portfolio Export

**What it does:** Standardized portfolio CSV export and webhook-based CRM sync to DealCloud, Salesforce, and Google Sheets.

**How it works:** `export_portfolio_csv(store)` — generates a flat CSV of all active deals with key metrics, MOIC estimates, health scores, and stage for import into any CRM. `sync_to_dealcloud(store, api_key)` — maps the portfolio store's deal records to DealCloud's deal object schema and PATCHes each record via the DealCloud REST API. `sync_to_salesforce(store, credentials)` — uses the Salesforce REST API (OAuth2 flow) to upsert deals into the configured Salesforce opportunity object. `push_to_google_sheets(store, sheet_id, api_key)` — pushes the portfolio CSV to a Google Sheet via the Sheets API. All sync operations are idempotent (upsert by deal_id). Failures are logged and do not propagate.

**Data in:** `portfolio/store.py` deal data; external API credentials from environment variables or the settings page.

**Data out:** CSV file for download; API upsert calls to DealCloud/Salesforce/Google Sheets.

---

## `pms/` — PMS (Portfolio Management System) Connectors

**What it does:** Connectors for specialized healthcare PE portfolio management systems. Placeholder subdirectory for fund-specific PMS integrations.

**How it works:** Structure is defined; individual connector implementations are added per fund based on their PMS vendor (Allvue, Cobalt, Investran). Each connector implements a `PMSConnector` interface with `push_deal(deal_id)`, `push_portfolio()`, and `pull_actuals()` methods.

**Data in:** Deal data from `portfolio/store.py`.

**Data out:** Formatted deal records to the fund's PMS system.

---

## Key Concepts

- **Integration as optional acceleration**: All integrations are additive — the platform works fully without any external CRM or PMS connected.
- **Idempotent sync**: All sync operations upsert rather than insert, so re-running never creates duplicates in the external system.
