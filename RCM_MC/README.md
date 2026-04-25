# RCM-MC (inside SeekingChartis)

**Revenue Cycle Management + Monte Carlo**

This is the Python package that does all the work. If you're reading this, you're one level inside the main repo. For the big-picture explanation in plain English, go up one level to [../README.md](../README.md).

This README covers the package-level how-tos for developers.

---

## 30-second start

```bash
# From this directory (RCM_MC/):
python3.14 -m venv ../.venv
source ../.venv/bin/activate
pip install -e ".[all]"
python demo.py
```

Browser opens at `http://localhost:8080`. Done.

---

## What this package is

A Python package (`rcm_mc`) that, when installed, gives you:

1. A **command-line tool** (`rcm-mc`) for scripting / cron
2. A **local HTTP web app** for interactive use
3. A **Python API** if you want to embed it in another tool

### The three doors into the same house

| Want to... | Use... |
|------------|--------|
| Click around a web UI | `python demo.py`, open `http://localhost:8080` |
| Script a batch diligence run | `rcm-mc analysis <deal_id>` |
| Call from your own Python code | `from rcm_mc.diligence.thesis_pipeline import run_thesis_pipeline` |

All three dispatch into the same analytic engines. One source of truth.

---

## The modules ship in 6 groups

| Group | Purpose | Lives in |
|-------|---------|----------|
| **Diligence** | Analytic modules (one per partner question) | `rcm_mc/diligence/` |
| **ML predictors** | Ridge + conformal + ensemble + cohort CV — 25+ models | `rcm_mc/ml/` |
| **Market intel** | Public comps + PE transactions + news feed | `rcm_mc/market_intel/` |
| **Portfolio ops** | Alerts, deals, health score, deadlines, LP digest | `rcm_mc/portfolio/` + `deals/` + `alerts/` |
| **Financial engines** | Monte Carlo, PE math, bridge, scenarios | `rcm_mc/mc/` + `pe/` + `core/` |
| **UI** | Server-rendered web pages + reusable components | `rcm_mc/ui/` |

The 7 diligence modules from the prior cycle still live in `diligence/`:
- `regulatory_calendar/` — CMS/OIG/FTC event kill-switch
- `covenant_lab/` — capital stack × covenant breach MC
- `bridge_audit/` — banker-bridge reality check against priors
- `bear_case/` — IC memo counter-narrative auto-generator
- `payer_stress/` — payer-mix rate-shock stress lab
- `hcris_xray/` — Medicare cost-report peer benchmarking
- `thesis_pipeline/` — orchestrator over all the above

The most recent cycle (Apr 2026) added:
- **4 new public-data ingest modules** in `data/` — CDC PLACES, state APCD, AHRQ HCUP, CMS MA enrollment, plus a unified data catalog at `/data/catalog`
- **13 new ML predictors** in `ml/` — denial rate, days-in-AR, collection rate, forward distress, improvement potential, contract strength, service-line profitability, labor efficiency, volume forecaster, regime detection, ensemble methods, feature importance, geographic clustering, payer-mix cascade. Plus a backtest harness at `/models/quality` and feature-importance viz at `/models/importance`
- **14+ reusable UI components** in `ui/` — `power_table`, `power_chart`, semantic colors, metric tooltips, breadcrumbs + keyboard shortcuts, skeletons, empty states, responsive utilities, theme toggle, comparison surface, provenance badges, global search, preferences, canonical UI kit
- **15 strategic planning docs** in `docs/` — see [docs/README.md](docs/README.md) for the index. Headlines: 6-month product roadmap, 3-cohort beta program plan, business model, competitive landscape, partnerships, multi-asset expansion, multi-user architecture, PHI security, integrations, regulatory roadmap, data acquisition, learning loop, v2 plan, next-cycle plan, MD demo script

Each module has its own README inside the folder.

---

## Running tests

```bash
# The new cycle modules (fast, 8 seconds):
python -m pytest tests/test_hcris_xray.py tests/test_bear_case.py \
  tests/test_payer_stress.py tests/test_bridge_audit.py \
  tests/test_covenant_lab.py tests/test_regulatory_calendar.py \
  tests/test_thesis_pipeline.py tests/test_deal_profile.py \
  tests/test_ic_packet.py tests/test_deal_mc.py \
  tests/test_exit_timing.py tests/test_seeking_alpha.py \
  tests/test_diligence_checklist.py -q

# Should print: 258 passed

# The full suite (slow, ~14 minutes):
python -m pytest tests/ -q --ignore=tests/test_integration_e2e.py

# Should print: 8,477 passed, 57 failed (the 57 are pre-existing
# UI-revert collateral, not cycle-module regressions)
```

---

## The architecture (layer rules)

```
Browser / CLI / Cron
        ↓
rcm_mc/server.py         ← HTTP routing (stdlib http.server)
rcm_mc/cli.py            ← top-level CLI
        ↓
feature subpackages      ← diligence/, market_intel/, portfolio/
        ↓
core + pe + rcm + mc     ← simulator, PE-math, Monte Carlo
        ↓
rcm_mc/portfolio/store.py ← SQLite connection manager
        ↓
SQLite file on disk
```

Every layer calls down, never up. The store is the only module that touches the database directly.

---

## Coding conventions

- **No new runtime deps** without discussion
- **Parameterized SQL only** — never f-string values into SQL
- **`html.escape()` every user-supplied string** before rendering
- **Private helpers prefix with `_`**
- **Docstrings explain WHY, not WHAT** — code says what; docstring explains the constraint or prior incident that drove the decision
- **Financial figures**: 2 decimal places (`$450.25M`). Percentages: 1 decimal (`15.3%`). Multiples: 2 decimals + `x` (`2.50x`).

---

## Where to read more

- **Plain-English overview**: [../README.md](../README.md)
- **Detailed walkthrough**: [../WALKTHROUGH.md](../WALKTHROUGH.md)
- **Developer guide**: [readME/03_Developer_Guide.md](readME/03_Developer_Guide.md)
- **API reference**: [readME/01_API_Reference.md](readME/01_API_Reference.md)
- **Architecture deep-dive**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **6-month product roadmap**: [docs/PRODUCT_ROADMAP_6MO.md](docs/PRODUCT_ROADMAP_6MO.md)
- **Beta program design**: [docs/BETA_PROGRAM_PLAN.md](docs/BETA_PROGRAM_PLAN.md)
- **Strategy index (15 docs)**: [docs/README.md](docs/README.md)
- **ML modules reference**: [rcm_mc/ml/README.md](rcm_mc/ml/README.md)
- **Data sources reference**: [rcm_mc/data/README.md](rcm_mc/data/README.md)
- **UI components reference**: [rcm_mc/ui/README.md](rcm_mc/ui/README.md)

---

## Status

- **Python**: 3.14
- **Tests**: 10,000+ test functions across 452 test files; cycle additions ship with their own resilience suites (empty-data, extreme-value, exports, full-pipeline 10 hospitals)
- **Branch**: `main` (current), `fix/revert-ui-reskin` working
- **Most recent cycle**: 80+ commits — 4 data sources, 13 ML predictors, 14+ UI components, 15 strategy docs, 6-month roadmap
- **GitHub**: https://github.com/DrewThomas09/RCM
