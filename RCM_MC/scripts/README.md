# scripts/

Shell scripts for power users. The everyday workflow is `python demo.py` (local) and `vm_setup.sh` (Azure deploy) — these scripts are for analysts who want to drive the full feature surface from the command line.

| Script | Purpose |
|--------|---------|
| `run_all.sh` | Exercise every CLI surface — HCRIS screening, full diligence run (report.html + workbook), PE math standalone, portfolio dashboard + exit memo. Drops everything into `./output v1/` for review |
| `run_everything.sh` | Server-driven feature tour: launches the server, runs tests, walks through the URLs. Modes: `test`, `serve`, `stop`, `check`, `tour` |

## Note on hardcoded paths

`run_everything.sh` has a hardcoded `REPO=` path for one specific developer's machine. If you're running it from a different layout, edit that line first or use `run_all.sh` (which auto-resolves the repo root).

## Why these aren't on the front page anymore

They lived at `RCM_MC/run_all.sh` and `RCM_MC/run_everything.sh` before the Apr 2026 reorg. They were moved here because the front page was getting cluttered with "scripts vs entry points vs config files vs docs" and the canonical entry points are `python demo.py` (dev) and `vm_setup.sh` (prod). These two are advanced.
