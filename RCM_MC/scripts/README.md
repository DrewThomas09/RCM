# scripts/

Shell scripts for power users. The everyday workflow is `python demo.py` (local) and `vm_setup.sh` (VM deploy) — these scripts are for analysts who want to drive the full feature surface from the command line.

| Script | Purpose |
|--------|---------|
| `run_all.sh` | Exercise every CLI surface — HCRIS screening, full diligence run (report.html + workbook), PE math standalone, portfolio dashboard + exit memo. Drops everything into `./output v1/` for review |
| `run_everything.sh` | Server-driven feature tour: launches the server, runs tests, walks through the URLs. Modes: `test`, `serve`, `stop`, `check`, `tour` |

## Paths

Both scripts auto-resolve the repo root from their own location
(`BASH_SOURCE`), so they work from any checkout and any cwd.
(`run_everything.sh` used to hardcode one developer's machine —
fixed in the Report-0265 pass; `tests/test_scripts_bash_syntax.py`
now `bash -n`-checks every script here.)

## Why these aren't on the front page anymore

They lived at `RCM_MC/run_all.sh` and `RCM_MC/run_everything.sh` before the Apr 2026 reorg. They were moved here because the front page was getting cluttered with "scripts vs entry points vs config files vs docs" and the canonical entry points are `python demo.py` (dev) and `vm_setup.sh` (prod). These two are advanced.
