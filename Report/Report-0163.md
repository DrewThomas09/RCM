# Report 0163: API Surface — `rcm_mc/cli.py` (FINALLY)

## Scope

Reads `RCM_MC/rcm_mc/cli.py` (1,252 lines) public surface. **Closes 19+ iteration carry-forward** since Report 0003 first noted the file at 1,252 lines. Sister to Reports 0086 (entry-points), 0103 (job_queue), 0139 (cli env-vars).

## Findings

### Public surface

`grep "^def \|^class "` returns:

| Line | Symbol | Public? | Purpose |
|---|---|---|---|
| 38 | `_ensure_outdir(path: str) -> str` | private | helper |
| 44 | `build_arg_parser() -> argparse.ArgumentParser` | **public** | argparse setup |
| 276 | `run_main(argv: Optional[list[str]] = None, prog: str = "rcm-mc") -> None` | **public** | main run entrypoint |
| 999 | `_auto_register_portfolio_snapshot(...)` | private | per Report 0139 — gated by `RCM_MC_NO_PORTFOLIO` |
| 1047 | `_print_run_complete_banner(...)` | private | terminal output |
| 1130 | `data_main(argv: list, prog: str = "rcm-mc data") -> int` | **public** | `rcm-mc data <subcmd>` entry |
| 1196 | `analysis_main(argv: list, prog: str = "rcm-mc analysis") -> int` | **public** | `rcm-mc analysis` entry |
| 1252 | `main(argv: Optional[list[str]] = None) -> int` | **public** | top-level dispatcher |

**5 public functions + 3 private helpers.**

### Top-of-file imports (lines 1-30)

```python
from __future__ import annotations
import argparse, json, os, sys
from typing import Optional
import pandas as pd

from .core.calibration import calibrate_config, write_yaml
from .pe.breakdowns import simulate_compare_with_breakdowns
from .analysis.stress import run_stress_suite
from .reports.html_report import generate_html_report
from .infra.config import load_and_validate
from .data.data_scrub import scrub_simulation_data
from .reports.reporting import (
    strategic_priority_matrix,
    assumption_summary,
    actionable_insights,
    correlation_sensitivity,
    METRIC_LABELS,
    plot_deal_summary,
    plot_denial_drivers_chart,
    plot_ebitda_drag_distribution,
    plot_underpayments_chart,
    pretty_money,
    summary_table,
    waterfall_ebitda_drag,
)
```

### Outgoing dependencies (top-level imports)

| Module | Symbols |
|---|---|
| stdlib | `argparse`, `json`, `os`, `sys`, `typing` |
| third-party | `pandas` |
| `core/calibration` | `calibrate_config`, `write_yaml` |
| `pe/breakdowns` | `simulate_compare_with_breakdowns` |
| `analysis/stress` | `run_stress_suite` |
| `reports/html_report` | `generate_html_report` |
| `infra/config` | `load_and_validate` |
| `data/data_scrub` | `scrub_simulation_data` |
| `reports/reporting` | 12 names imported |

**~22 internal symbols imported at top of file.** Per Report 0103 + 0125 patterns: heavy fanin to internal modules. Cross-link Report 0124 PortfolioStore (237 importers): cli.py is one of those importers.

### NEW unmapped modules discovered (cross-link Report 0091 backlog)

| Module | Status |
|---|---|
| `core/calibration.py` | mentioned by name; never deeply read |
| `pe/breakdowns.py` | Report 0044 doc-gap only; never read |
| `analysis/stress.py` | mentioned; never deeply read |
| `reports/html_report.py` | Report 0131 found `playbook.yaml` swallow; never deeply read |
| `data/data_scrub.py` | **NEW — never reported** |
| `reports/reporting.py` | **NEW — never reported** |

**2 NEWLY-discovered unmapped modules**: `data/data_scrub.py`, `reports/reporting.py`.

### `build_arg_parser()` — argparse surface (line 44)

**232-line function** (line 44 → 276). Sets up the full `rcm-mc` CLI surface. Per Report 0162 + 0139: `--value-plan`, `--actual`, `--benchmark`, `--db`, `--no-portfolio`, etc. flags live here.

**Q1**: enumerate all flags.

### `run_main()` (line 276) — main run

**723-line function** (276 → 999). The bulk of cli.py. **Single mega-function** that orchestrates: load configs → calibrate → simulate → render reports → register snapshot.

**Cross-correction**: cli.py is dominated by ONE 723-line function. **Refactor candidate.** Cross-link Report 0140 packet_builder (1454L, 34 try blocks) — same scale.

### `data_main()` + `analysis_main()` (lines 1130, 1196)

Subcommand dispatchers:
- `rcm-mc data <subcmd>` — likely `refresh`, `status`, etc. (per Report 0102 hop 6)
- `rcm-mc analysis <subcmd>` — likely `build`, `view`, `export`

Each ~50-65 LOC. Per CLAUDE.md "rcm-mc analysis <deal_id>".

### `main()` (line 1252) — TOP-LEVEL dispatcher

**Last function in file** (line 1252+ → end). Routes based on first argv:
- `rcm-mc data ...` → `data_main`
- `rcm-mc analysis ...` → `analysis_main`
- otherwise → `run_main`

### Closes Report 0086 + 0101 entry-point Q

Per Report 0101: `[project.scripts] rcm-mc = "rcm_mc.cli:main"`. **Confirmed**: `main()` at line 1252 is the binary's entry-point.

### Comparison to other entry-point modules

| File | Lines | Public fns |
|---|---|---|
| `seekingchartis.py` (Report 0138) | 84 | 1 (`main`) |
| `rcm_mc/api.py` (Report 0113) | 63 | 0 (FastAPI app) |
| `rcm_mc_diligence/cli.py` (Report 0122) | 252 | 1 (`main`) |
| **`rcm_mc/cli.py` (this)** | **1,252** | **5** |

cli.py is **5-15× larger** than other entry-points. Reflects the breadth of `rcm-mc` subcommands.

### Doc-discipline check

This iteration extracted only the head + function list. **Per-function docstrings** TBD. Per Report 0134 doc-foil pattern: cli.py is in the analysis/orchestrator cluster (likely well-documented).

### Cross-link to Report 0140 packet_builder.py

packet_builder.py: 1,454 LOC, 34 try blocks. cli.py: 1,252 LOC. **Both are mega-orchestrators with high broad-except density per Report 0140 / 0141 pattern.** **Q2**: cli.py error-handling profile?

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR877** | **CLOSURE: cli.py public surface mapped after 19+ iter carry** | 5 public fns, 3 private. Top-level dispatcher pattern: `main` → `run_main`/`data_main`/`analysis_main`. | (closure) |
| **MR878** | **`run_main()` is 723 LOC — single mega-function** | Refactor candidate. Cross-link Report 0140 packet_builder 1454-LOC orchestrator. | Medium |
| **MR879** | **2 NEW unmapped modules discovered** via cli.py imports: `data/data_scrub.py`, `reports/reporting.py` | Add to backlog. | Medium |
| **MR880** | **`build_arg_parser()` is 232 LOC** — likely 30+ argparse flags | Single source of truth for the `rcm-mc` surface. Per Report 0091 documentation gap pattern: full enumeration not in any doc. | High |

## Dependencies

- **Incoming:** `pyproject.toml [project.scripts] rcm-mc`, `infra/job_queue._default_sim_runner` (per Report 0103).
- **Outgoing:** 22+ internal symbols + pandas + stdlib.

## Open questions / Unknowns

- **Q1.** All argparse flags in `build_arg_parser()`?
- **Q2.** Error-handling profile (try/except count) in cli.py — likely high per Report 0140 pattern?
- **Q3.** Per-function docstring density?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0164** | Read `data/data_scrub.py` + `reports/reporting.py` (NEW unmapped per MR879). |
| **0165** | Map cli.py argparse flags (closes Q1, completes the cli.py audit). |
| **0166** | Schema-walk `initiative_actuals` (Report 0157 MR853 carried). |

---

Report/Report-0163.md written.
