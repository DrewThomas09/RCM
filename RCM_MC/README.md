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

## The modules ship in 5 groups

| Group | Purpose | Lives in |
|-------|---------|----------|
| **Diligence** | Analytic modules (one per partner question) | `rcm_mc/diligence/` |
| **Market intel** | Public comps + PE transactions + news feed | `rcm_mc/market_intel/` |
| **Portfolio ops** | Alerts, deals, health score, deadlines, LP digest | `rcm_mc/portfolio/` + `deals/` + `alerts/` |
| **Financial engines** | Monte Carlo, PE math, bridge, scenarios | `rcm_mc/mc/` + `pe/` + `core/` |
| **UI** | Server-rendered web pages | `rcm_mc/ui/` |

The 7 modules shipped in the most recent cycle are inside `diligence/`:
- `regulatory_calendar/` — CMS/OIG/FTC event kill-switch
- `covenant_lab/` — capital stack × covenant breach MC
- `bridge_audit/` — banker-bridge reality check against priors
- `bear_case/` — IC memo counter-narrative auto-generator
- `payer_stress/` — payer-mix rate-shock stress lab
- `hcris_xray/` — Medicare cost-report peer benchmarking
- `thesis_pipeline/` — 14-step orchestrator over all the above

Each has its own README inside the folder.

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

---

## Status

- **Python**: 3.14
- **Tests**: 258/258 green on new cycle modules · 8,477/8,534 (99.3%) full suite
- **Branch**: `fix/revert-ui-reskin` (merged to `main`)
- **GitHub**: https://github.com/DrewThomas09/RCM
