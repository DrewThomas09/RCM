# PEdesk Platform Architecture Overview

A bird's-eye view of how PEdesk is built so the Guide can answer "what is
this thing", "how does the platform work", "what's the tech stack", and
"how do I run it".

## What PEdesk is

PEdesk is an **analytics platform for healthcare private-equity diligence
and portfolio operations**. It combines:

- A **Monte Carlo simulator** that projects revenue-cycle-management
  (RCM) initiative outcomes on a healthcare deal.
- A **PE-math layer** that turns simulation outputs into bridge / MOIC
  / IRR / covenant math.
- A **portfolio-operations console** (alerts, cohorts, deal tracking,
  LP reporting, owner/deadline workflow) that a partner uses daily.

Users are PE partners and their associates. Deployment is a Python
package + a built-in HTTP server — no external services, no Docker
required for local use.

## Tech stack

- **Python 3.10+** (stdlib-heavy; pandas + numpy + matplotlib are the
  only runtime deps beyond stdlib).
- **SQLite** via `sqlite3` stdlib — ~89 tables across portfolio + data
  loaders + ml + engagement + assistant. `busy_timeout=5000`, idempotent
  `CREATE TABLE IF NOT EXISTS` migrations.
- **HTTP** via `http.server.ThreadingHTTPServer` — no Flask, no FastAPI.
- **HTML** server-rendered (string concatenation through a shared
  editorial shell). No SPA, no client-side framework. One small
  vanilla-JS shim for CSRF-patching forms and the page-action
  affordances.
- **Auth** via stdlib password hashing + session cookies. No third-party
  identity provider.
- **CLI** via stdlib `argparse`, entry-pointed through `rcm-mc` /
  `rcm-mc portfolio` / `rcm-mc pe`.
- **Tests** via stdlib `unittest`, driven by `pytest`. 2,878+ passing
  tests.

Zero new runtime dependencies have been added in any recent feature
work.

## Architecture layers

```
Browser / CLI / Cron
        ↓
rcm_mc/server.py         ← HTTP app (auth, CSRF, rate-limit, audit)
rcm_mc/cli.py            ← top-level CLI
rcm_mc/portfolio_cmd.py  ← portfolio subcommands
        ↓
feature subpackages      ← alerts/, deals/, portfolio/, auth/, etc.
        ↓
core + pe + rcm          ← simulator, PE-math, RCM math
        ↓
rcm_mc/portfolio/store.py ← SQLite connection manager
        ↓
SQLite file on disk
```

Every layer calls down, never up. The store is the only module that
talks to SQLite directly.

## Build phases

PEdesk has been built in three phases:

### Phase 1 — Regression prediction engine *(complete)*
Probabilistic models of per-KPI outcomes (initial-denial rate,
final-write-off, clean-DAR, NPSR). Fit to priors via the calibration
module.

### Phase 2 — Monte Carlo EBITDA simulation *(complete)*
- `rcm_mc/simulator.py` runs N simulations per deal.
- `rcm_mc/pe_math.py` computes value-creation bridge, MOIC, IRR,
  covenant headroom.
- Scenario layering via `rcm_mc/scenarios/`.

### Phase 4 — Packet-centric analysis *(current — polishing)*
Every UI page, API endpoint, and export renders from a single
`DealAnalysisPacket` instance. Nothing renders independently — this is
the load-bearing invariant for audit and UI consistency. Built by
`rcm_mc/analysis/packet_builder.py`, cached in the `analysis_runs`
table, exported via `rcm_mc/exports/packet_renderer.py`.

Key modules added in Phase 4:
- `rcm_mc/analysis/packet.py` — the dataclass + JSON round-trip
- `rcm_mc/analysis/packet_builder.py` — 12-step orchestrator
- `rcm_mc/analysis/completeness.py` — registry + grade
- `rcm_mc/analysis/risk_flags.py`, `diligence_questions.py`
- `rcm_mc/ml/ridge_predictor.py` + `conformal.py`
- `rcm_mc/pe/rcm_ebitda_bridge.py` — 7-lever bridge
- `rcm_mc/mc/ebitda_mc.py` — two-source Monte Carlo
- `rcm_mc/provenance/graph.py` + `explain.py`
- `rcm_mc/exports/packet_renderer.py`
- `rcm_mc/ui/analysis_workbench.py` — Bloomberg-style workbench at
  `/analysis/<deal_id>`

### Phase 3 — Portfolio intelligence *(in progress — polish)*
Partner-facing operations:
- **Alerts lifecycle**: fire → ack/snooze → history → escalate.
- **Cohorts, watchlists, owners, deadlines, notes, tags**.
- **Health score**: composite 0-100 per deal (see
  `health_score_methodology.md`).
- **LP digest**: `/lp-update`, partner-ready HTML export.
- **Multi-user security**: salted password hashing, sessions, CSRF,
  rate-limited login, unified audit log.

## The honesty invariants

PEdesk enforces several invariants that the Guide should always
respect:

- **Real counts only** — never hard-code numbers; everything reads from
  the data layer.
- **One `<h1>` per page** (a11y).
- **No fabricated numbers anywhere** — empty states render `—` or
  honest "Awaiting data".
- **Conservative formula confidence** — if a metric's exact formula
  isn't documented in source, the entry says so (no inventing math).
- **DATA REQUIRED rule** — pages that need user data say so explicitly
  and refuse to fabricate.
- **Audit log** — every state change is recorded.

These invariants are tested. The Guide is also bound by them:
*PEdesk Guide is read-only and explanatory — never run models, change
assumptions, or make investment recommendations. Do not invent formulas
or data lineage; if a specific is not in the context, say it needs
source documentation.*

## What runs where

- **Local development**: `demo.py` seeds + starts the server.
- **Production**: `rcm-mc serve` on a DigitalOcean droplet behind Caddy.
- **Deploy**: GitHub Actions on merge to main → tests → SSH deploy →
  restart pedesk → healthz check. Auto.
- **Data refresh**: GitHub Actions workflow or manual `rcm-mc data
  refresh-<dataset>` CLI.
- **The Guide (Ollama)**: read-only RAG assistant; sources include
  `manual_page_contexts.py` (per-page context), `metric_registry.py`
  (per-metric context), `data_source_registry.py` (per-dataset
  context), and `docs/rag_sources/` (concept cards like this one).

## Related cards

- `analysis_packet.md` — Phase-4 packet details.
- `process_deal_lifecycle.md` — the workflow.
- `process_source_to_pipeline_to_ic.md` — the partner journey.
- `provenance_and_data_quality.md` — the data trust model.
- `data_freshness_and_provenance.md` — refresh cadences.
- `standard_page_actions.md` — UI affordances.
- `target_screener_workbench.md` — the flagship workbench surface.
