# PE Desk — System Overview & Map

> **Read this first.** This is the index to the PE Desk documentation set. It explains what PE Desk is, how the pieces connect, and points to the three deep-dive files. Together these four documents map the whole platform so you can answer questions about any page, algorithm, or data source.

| Doc | What it covers |
|---|---|
| **PEDESK_OVERVIEW.md** (this file) | What PE Desk is, architecture, how it connects, how to run it |
| [PEDESK_PAGES.md](PEDESK_PAGES.md) | Every page/route: purpose, data, visuals, drill-throughs |
| [PEDESK_ALGORITHMS.md](PEDESK_ALGORITHMS.md) | Every model/algorithm: method, inputs, outputs, safeguards |
| [PEDESK_DATA.md](PEDESK_DATA.md) | Data sources, SQLite tables, ingestion, provenance/trust tagging |

---

## 1. What PE Desk is

PE Desk is an **analytics platform for healthcare private-equity diligence and portfolio operations**. Users are PE partners and their associates. It does three things:

1. **Screens & diligences hospital deals** from free public data (CMS HCRIS cost reports, Care Compare, IRS 990, a realized-deal corpus) — investability scoring, comparables, red flags, RCM (revenue-cycle) leakage, EBITDA bridges.
2. **Models outcomes** — a Monte Carlo simulator projects RCM-initiative impact on EBITDA; PE-math turns that into value-creation bridge / MOIC / IRR / covenant headroom; a ridge+conformal predictor fills missing metrics with honest 90% intervals.
3. **Runs the portfolio** — alerts, cohorts, deal tracking, health scores, LP reporting, owner/deadline workflow that a partner uses daily.

Deployment is a **Python package + a built-in HTTP server** — no external services, no Docker required for local use. Internal package name is `seekingchartis`; the product brand is **PE Desk** (`rcm_mc/__init__.py`, `__product__ = "PE Desk"`).

> **Terminology:** "PE Desk" = this application = the `rcm_mc` package in this repo. `demo.py` is just a local launcher that boots the same PE Desk server with throwaway sample data — it is **not** a separate app.

## 2. Tech stack

- **Python 3.10+** (stdlib-heavy). Only runtime deps: `numpy`, `pandas`, `matplotlib`, `pyyaml`, `openpyxl`. Optional extras gate heavier features: `[stats]` (scipy, with soft fallbacks), `[api]` (FastAPI), `[pptx]`, `[diligence]` (duckdb/dbt), `[edi]` (X12 parser).
- **HTTP:** stdlib `http.server.ThreadingHTTPServer` — **no Flask/FastAPI/template engine**. (`rcm_mc/api.py` is an *optional* separate FastAPI surface.)
- **Database:** SQLite via stdlib `sqlite3` (~89 tables, `busy_timeout=5000`, idempotent `CREATE TABLE IF NOT EXISTS` migrations).
- **HTML:** server-rendered via string concatenation through one shared shell. **No SPA, no client framework.** Charts are inline SVG. One small vanilla-JS shim auto-patches forms with CSRF tokens.
- **Auth:** stdlib `hashlib.scrypt` + session cookies. No third-party identity provider.
- **CLI:** stdlib `argparse`. **Tests:** stdlib `unittest` driven by `pytest` (~2,878+ passing, suite currently green).

## 3. Layered architecture

Every layer calls **down**, never up. `portfolio/store.py` is the **only** module that touches SQLite.

```
Browser / CLI / Cron
   ↓
rcm_mc/server.py · cli.py · pe_cli.py · portfolio_cmd.py        (entry points)
   ↓
feature subpackages  (alerts/ deals/ portfolio/ auth/ reports/ scenarios/ …)
   ↓
core + pe + rcm      (Monte Carlo simulator · PE-math · RCM math)
   ↓
rcm_mc/portfolio/store.py                                       (SQLite gateway)
   ↓
SQLite file on disk
```

### Subpackages (one line each)
- `core/` — Monte Carlo simulator, kernel, distributions, calibration, RNG.
- `pe/` — PE-math: value-creation bridge, MOIC/IRR, hold tracking, value plan, `rcm_ebitda_bridge` (7-lever), `value_bridge_v2` (payer/method-mix).
- `rcm/` — RCM domain math: claim distribution, initiatives, initiative tracking.
- `data/` — public-data loaders/ingest: HCRIS, IRS 990, CMS sources, NPPES, intake, scrub.
- `data_public/` — the realized-deal corpus + ~290 analytic-engine data modules (each maps to a `ui/data_public/*_page.py`).
- `portfolio/` — `store.py` (sole SQLite gateway), snapshots, dashboard, rollups.
- `deals/` — deal CRUD, notes, tags, owners, deadlines, sim inputs, health score, watchlist.
- `alerts/` — alert lifecycle: fire / ack / snooze / history / escalate.
- `auth/` — scrypt passwords, sessions, RBAC, audit log.
- `reports/` — full/HTML/markdown reports, narrative, exit memo, LP update, PPTX export.
- `scenarios/` — scenario builder, shocks, overlays.
- `analysis/` — **the DealAnalysisPacket** + `packet_builder` + `analysis_store`, completeness, risk flags, diligence questions, stress, cohorts.
- `ml/` — Phase-1 prediction: comparables + Ridge/conformal predictor fills missing RCM metrics.
- `finance/` — regression engine, influence diagnostics, leakage audit, reimbursement substrate.
- `mc/` — two-source Monte Carlo (prediction uncertainty × execution uncertainty), `ebitda_mc`.
- `diligence/` — analyst workspace; 4-phase RCM playbook (ingest/benchmarks/root_cause/value), CCD claims dataset.
- `provenance/` — the data-lineage graph so every displayed number has a traceable story.
- `engagement/` — engagement-scoped RBAC, comments, draft→publish state machine (consulting workflow).
- `pe_intelligence/` — the "Partner Brain": consumes a packet, emits a `PartnerReview` (reasonableness bands, heuristics) **without mutating the underlying calculations**.
- `ui/` — the editorial "Chartis" design system (`_chartis_kit.py`, `chartis/` renderers, `static/chartis_tokens.css`).
- `infra/` — config, logger, trace, job queue, run history, rate limit.
- `exports/` — `packet_renderer.py` exports the packet to files.

> **Doc caveat:** CLAUDE.md's "Package layout" block lists ~18 subpackages but the tree has grown to ~50 (plus a separate `rcm_mc_diligence/`). The ones above are verified; treat CLAUDE.md's list as a subset.

## 4. The load-bearing invariant: the DealAnalysisPacket

`DealAnalysisPacket` (`rcm_mc/analysis/packet.py`, see [docs/ANALYSIS_PACKET.md](ANALYSIS_PACKET.md)) is the **single canonical object for one deal's full analysis**. Its rule, stated in its own docstring: *"UI routes, API endpoints, and exports render from this object — nothing renders independently. If a number shows up on a page, it came from here."*

- Built by `analysis/packet_builder.py` — a 12-step orchestrator. Any failed step is marked `INCOMPLETE`/`FAILED`/`SKIPPED` rather than killing the packet.
- Cached in the `analysis_runs` table (`analysis/analysis_store.py`), keyed on `(deal_id, hash_inputs)`, stored as a JSON blob.
- Exported via `exports/packet_renderer.py`; built offline via `rcm-mc analysis <deal_id>`.
- **Why it matters:** no number drift across pages (a disagreement is a renderer bug, not a data bug), and partners get a frozen "what we knew at time T" snapshot.

## 5. Request pipeline (what `server.py` does per request)

`RCMHandler` on `ThreadingHTTPServer` (~18.6k LOC). Per request:
1. **Request ID + observability** — UUID per request; `X-Request-Id` + `X-Response-Time` headers; `/api/metrics` reports p50/p95/p99.
2. **Auth/session** — session-cookie lookup (7-day sliding TTL + idle timeout); unauthenticated nav redirects to `/login`.
3. **CSRF** — per-process HMAC secret; session POSTs require a `csrf_token` field or `X-CSRF-Token` header (a JS shim auto-patches forms). A small exempt list covers `/api/login`, `/api/logout`, `/health`.
4. **Rate limiting** — guards login, data-refresh (1/hr/source), deletes (10/hr); 10 MB request cap.
5. **Idempotency** — thread-safe LRU dedupes POSTs by key.
6. **Audit log** — every event appended with request_id; sensitive views (`/admin`, `/users`, `/audit`, `/settings`) specifically audited.
7. **gzip + ETags** — responses >1 KB gzipped; packet/JSON GETs send `ETag` / honor `If-None-Match` (304).
8. **Workspace mode** — reads the `ck_workspace_mode` cookie into a per-request contextvar (`partner` default vs `consulting`).
9. **Shell wrapping** — every HTML body is wrapped by `chartis_shell` so all pages share the editorial chrome.

## 6. UI system — the editorial "Chartis" design

- **Shell:** `chartis_shell(...)` wraps every page. The `/app` Command Center uses `editorial_chartis_shell`. Top nav: **Home / Pipeline / Diligence / Library / Research / Portfolio** (`_SUB_NAV` / `_CORPUS_NAV` in `_chartis_kit.py`).
- **Primitives (`ck_*`):** `ck_page_title`, `ck_kpi_block`, `ck_table`, `ck_scatter`, `ck_bar_row`, `ck_sparkline`, `ck_value_anchor`, `ck_signal_badge`, `ck_empty_state`, `ck_section_intro`, `ck_provenance_tooltip`, `ck_narrative_band`, etc. (full list in `rcm_mc/ui/README.md`).
- **Tokens** (`static/chartis_tokens.css`): parchment background, navy topbar, teal accents, near-ink text; fonts `--sc-serif` (Source Serif 4), `--sc-sans` (Inter Tight), `--sc-mono` (JetBrains Mono); semantic colors `--sc-positive` / `--sc-warning` / `--sc-negative`. Color signals state; hierarchy comes from size/weight.
- **Two-view workspace mode:** same surfaces, audience-specific vocabulary — **PE Partner** ("Fund-level deal operations") vs **Chartis Consulting** ("Commercial diligence for client engagements"). It is **copy-only** — swaps lexicon via `term()`, never page structure.

## 7. How to run PE Desk

**Local (throwaway data):**
```bash
cd /Users/andrewthomas/dev/RCM_MC/RCM_MC
.venv/bin/python demo.py
# opens http://127.0.0.1:8765/login
# login: demo / DemoPass!1   (or andrewthomas@chartis.com / ChartisDemo1)
# temp DB, deleted on Ctrl-C
```

**Persistent (data survives restarts):**
```bash
# one-time: create DB + admin user
.venv/bin/python -m rcm_mc.portfolio_cmd --db p.db users create \
  --username boss --password "Strong!1" --role admin
# start the server
.venv/bin/python -m rcm_mc serve --db p.db --port 8080
# open http://127.0.0.1:8080/login
```

Code changes only take effect after the server is (re)started against the latest code.

### CLI surface
- `rcm-mc serve` — the HTTP app.
- `rcm-mc analysis <deal_id>` — build/load a DealAnalysisPacket.
- `rcm-mc data {status|refresh|refresh-nppes}` — public-data ingestion.
- `rcm-mc pe {bridge|returns|grid|covenant}` — PE-math from the CLI.
- `rcm-mc portfolio {register|list|show|rollup|users …}` — portfolio + user management.

## 8. Build phases (status)
- **Phase 1 — Regression prediction** *(complete)* — `ml/` ridge+conformal fills missing per-KPI metrics from comparable cohorts.
- **Phase 2 — Monte Carlo EBITDA** *(complete)* — `core/simulator.py` + `pe/pe_math.py` + scenario layering + two-source MC in `mc/`.
- **Phase 4 — Packet-centric** *(current)* — the `DealAnalysisPacket` invariant.
- **Phase 3 — Portfolio intelligence** *(polish)* — alerts, cohorts, health score, LP digest, multi-user security.

## 9. Security & known limitations (by design)
- scrypt password hashing; password length capped pre-hash to prevent scrypt DoS.
- Session CSRF secret is per-process → **sessions invalidate on server restart** (partners reopen the login tab).
- **Single-machine SQLite** — no clustering, no Postgres path; `store.py` is the sole DB gateway.
- **In-memory job queue** — single worker; jobs lost on restart (fine for partner-driven reruns; use the CLI for critical/cron runs).
- Parameterised SQL only; `html.escape()` on user strings (with the documented `ck_kpi_block` exemption); CSV exports defanged against Excel formula injection.

---
*Generated from a full codebase mapping. For exact behavior, the code is authoritative — file:line references throughout the deep-dive docs point you there.*
