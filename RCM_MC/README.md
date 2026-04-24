# RCM-MC v0.6.0

**Revenue Cycle Management Monte Carlo** -- a healthcare private-equity diligence and portfolio operations platform.

RCM-MC combines Monte Carlo simulation, PE-math (bridge / MOIC / IRR / covenant headroom), and a full-featured web console into a single Python package. Partners use it to screen hospitals, run diligence, track hold-period operations, and prepare IC presentations -- all from one tool with zero external dependencies.

---

## Quick Start

```bash
# 1. Create virtual environment
python3.14 -m venv .venv
source .venv/bin/activate

# 2. Install with all optional deps
pip install -e ".[all]"

# 3. Seed demo data + launch browser
python demo.py

# Or start manually with a fresh database
rcm-mc serve --db portfolio.db --port 8080
```

Open `http://localhost:8080`. The portfolio dashboard appears with deal cards, health scores, and alert badges.

---

## What This Platform Does

### Deal Lifecycle (End-to-End)

```
Screen --> Source --> Diligence --> IC Prep --> Close --> Hold --> Exit
  |          |           |            |          |        |        |
/screen   /source    /new-deal    /analysis   /deal   /hold    /exit
```

| Stage | Page / API | What Happens |
|-------|-----------|--------------|
| **Screen** | `GET /screen` | Paste hospital names, get ranked verdicts with denial/AR/collection scores |
| **Source** | `GET /source?thesis=denial_turnaround` | Thesis-driven origination from 6,000+ HCRIS hospitals |
| **Diligence** | `GET /new-deal` | 5-step wizard: CCN lookup, HCRIS pre-fill, data upload, review, launch |
| **Analyze** | `GET /analysis/<id>` | Bloomberg-style workbench: 7 tabs (Overview, RCM Profile, EBITDA Bridge, Monte Carlo, Scenarios, Risk & Diligence, Provenance) |
| **Compare** | `GET /compare?deals=a,b` | Side-by-side metrics, EBITDA trajectory SVG, radar chart |
| **IC Prep** | `GET /api/deals/<id>/checklist` | Readiness assessment: packet built? notes recorded? plan created? |
| **Memo** | `GET /api/deals/<id>/memo` | AI-generated IC memo with fact-checking (LLM optional) |
| **Track** | `GET /deal/<id>` | Notes, tags, deadlines, health score, variance, initiatives |
| **Alerts** | `GET /alerts` | Fire / ack / snooze / escalate lifecycle with returning-badge |
| **Export** | `GET /api/deals/<id>/package` | One-click ZIP: executive summary, bridge, risk matrix, questions, data |

### Portfolio Operations

| Feature | Location |
|---------|----------|
| Dashboard with funnel + KPIs | `GET /` |
| Health score (0-100) + trend | `GET /api/deals/<id>/health` |
| Cohorts, watchlists, owners | `GET /cohorts`, `GET /watchlist`, `GET /owners` |
| LP digest (partner-ready) | `GET /lp-update` |
| Portfolio Monte Carlo | `GET /portfolio/monte-carlo` |
| Heatmap + geographic map | `GET /portfolio/heatmap`, `GET /portfolio/map` |
| Cross-deal metric matrix | `GET /api/portfolio/matrix` |
| Alerts summary by severity | `GET /api/portfolio/alerts` |

### AI Features

| Feature | Endpoint | Description |
|---------|----------|-------------|
| IC Memo | `GET /api/deals/<id>/memo?llm=1` | LLM-generated sections with fact-checking against packet data |
| Document QA | `GET /api/deals/<id>/qa?q=...` | Search indexed deal documents, return answers with confidence |
| Chat | `POST /api/chat` | Multi-turn conversational interface with tool dispatch |

All three fall back gracefully when no LLM API key is configured.

---

## Architecture

```
Browser / CLI / Cron
        |
        v
   server.py (10K lines)     HTTP app: auth, CSRF, rate-limit, gzip,
        |                     ETags, CORS, CSP, audit logging
        v
   feature packages           alerts/, deals/, portfolio/, auth/,
        |                     ai/, pe/, mc/, analysis/, exports/,
        v                     scenarios/, data/, infra/, ui/
   store.py                   SQLite: single file, WAL mode,
        |                     busy_timeout=5000, FK enforcement
        v
   portfolio.db               One file = entire database
```

### Key Design Decisions

- **Zero external services** -- no Redis, no Postgres, no Docker, no message queue
- **Single-file database** -- one `.db` file contains all deals, runs, alerts, audit events
- **Stdlib HTTP** -- `http.server.ThreadingHTTPServer`, no Flask/FastAPI
- **Server-rendered HTML** -- no SPA, no React, no build step. One shared `shell()` function wraps every page
- **Packet-centric** -- every UI page, API endpoint, and export renders from a single `DealAnalysisPacket` instance
- **Dark mode default** -- CSS custom properties with `@media (prefers-color-scheme: dark)` override

---

## Project Stats

| Metric | Value |
|--------|-------|
| Version | 0.6.0 |
| Python | 3.10+ (developed on 3.14) |
| Tests | **2,883** (all passing) |
| Source files | 241 |
| Test files | 225 |
| Total lines | 78,678 |
| API endpoints | 52 paths, 56 methods |
| HTTP methods | GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS |
| OpenAPI | Full spec at `/api/openapi.json`, Swagger UI at `/api/docs` |
| Security headers | 7 (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, CORS, Vary) |
| Response headers | 5 (X-Request-Id, X-Response-Time, X-API-Version, ETag, Retry-After) |
| Web pages | 15+ |
| Runtime deps | numpy, pandas, pyyaml, matplotlib, openpyxl |

---

## CLI Reference

```bash
# Main Monte Carlo simulation
rcm-mc --actual actual.yaml --benchmark benchmark.yaml --n-sims 10000 --seed 42

# Version
rcm-mc --version

# Portfolio management
rcm-mc portfolio --db p.db list
rcm-mc portfolio --db p.db register --deal-id acme --stage loi --notes "Initial"
rcm-mc portfolio --db p.db users create --username boss --password "Strong!1" --role admin

# Analysis packet
rcm-mc analysis acme --db p.db

# Data refresh (downloads from CMS)
rcm-mc data refresh hcris
rcm-mc data status

# HTTP server
rcm-mc serve --db p.db --port 8080 --host 0.0.0.0
```

---

## Documentation

Documentation is organized into two places:

### User Guide — [readME/](readME/README.md)

26 numbered documents covering every aspect of the platform:

| Document | Contents |
|----------|----------|
| **[readME/README.md](readME/README.md)** | **Master index — start here** |
| [00 Walkthrough Tutorial](readME/00_Walkthrough_Tutorial.md) | 30-minute hands-on tour with copy-paste commands |
| [01 API Reference](readME/01_API_Reference.md) | All 52 endpoints with parameters, responses, examples |
| [02 Configuration & Ops](readME/02_Configuration_and_Operations.md) | Database, auth, deployment, backup, monitoring |
| [03 Developer Guide](readME/03_Developer_Guide.md) | Architecture, testing, coding conventions |
| [04 Getting Started](readME/04_Getting_Started.md) | Installation, first run, basic workflow |
| [05 Architecture](readME/05_Architecture.md) | System design, data flow, design decisions |
| [06 Analysis Packet](readME/06_Analysis_Packet.md) | The canonical `DealAnalysisPacket` dataclass |
| [07 Partner Workflow](readME/07_Partner_Workflow.md) | End-to-end workflow: screen → source → diligence → IC → hold → exit |
| [08–25 Deep-dives](readME/README.md) | Metric provenance, benchmark sources, model improvement, glossary, data flow, build status, layer-by-layer architecture (Analysis / Data / Domain / Infra / MC / ML / PE / Provenance / UI) |

### Reference Specs — [docs/](docs/README.md)

6 canonical reference documents:

| Document | Contents |
|----------|----------|
| [ANALYSIS_PACKET.md](docs/ANALYSIS_PACKET.md) | Every field in `DealAnalysisPacket` with type and builder step |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layer diagram and dependency rules |
| [BENCHMARK_SOURCES.md](docs/BENCHMARK_SOURCES.md) | CMS HCRIS, Care Compare, IRS 990, SEC EDGAR field-by-field |
| [METRIC_PROVENANCE.md](docs/METRIC_PROVENANCE.md) | Metric-to-source traceability with confidence tiers |
| [MODEL_IMPROVEMENT.md](docs/MODEL_IMPROVEMENT.md) | Known limitations and Tier 1–3 improvement roadmap |
| [PE_HEURISTICS.md](docs/PE_HEURISTICS.md) | 275+ PE partner rules, named failure patterns, and thesis-trap detectors |

### Module READMEs — [rcm_mc/](rcm_mc/)

Every source package has its own `README.md` with per-file documentation (what it does, how it works, data sources). See [readME/README.md](readME/README.md) → Source Code READMEs table for the full list.

---

## License

Proprietary. See LICENSE file.
