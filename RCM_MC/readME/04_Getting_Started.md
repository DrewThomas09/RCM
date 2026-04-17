# Getting Started

A walk-through from cold start to running the model, changing assumptions, and finding outputs. Assumes no prior terminal experience. Commands are macOS / zsh; on Windows use `python` instead of `python3` if that is how Python is installed.

For **what the model means**, see [ARCHITECTURE.md](ARCHITECTURE.md). For **metric definitions**, see [METRIC_PROVENANCE.md](METRIC_PROVENANCE.md).

---

## 1. Setup (one time)

### Check Python

```bash
python3 --version
```

Expect `Python 3.10` or later. If `command not found`, install from [python.org](https://www.python.org/downloads/).

### Go to the project folder

```bash
cd "/Users/andrewthomas/Desktop/Coding Projects/RCM_MC"
ls
```

You should see `rcm_mc`, `configs`, `tests`, `pyproject.toml`, etc.

### Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt will show `(.venv)`. Each new terminal session: `cd` back here and `source .venv/bin/activate` again.

### Install

```bash
pip install -e .
```

Optional PowerPoint export: `pip install -e ".[pptx]"`. Everything optional: `pip install -e ".[all]"`.

### (Optional) Matplotlib cache fix

If you see `~/.matplotlib` permission warnings:

```bash
export MPLCONFIGDIR="/tmp/mplcache"
```

---

## 2. Build a diligence config (intake wizard)

Instead of editing the 131-field YAML by hand, run the wizard. It asks 11 questions — the fields a diligence analyst actually has — and writes a validated `actual.yaml` with your answers tagged as `observed` in the source map.

```bash
rcm-intake --out actual.yaml
```

Prompts:
1. Template (community hospital, rural critical access, or shipped actual)
2. Hospital / target name
3. Annual NPSR ($)
4. Medicare / Medicaid / Commercial revenue shares (SelfPay = residual)
5. Blended initial denial rate (IDR %)
6. Blended final write-off rate (FWR %)
7. Blended A/R days
8. EBITDA margin %
9. WACC %

Your blended IDR / FWR / DAR are distributed to each payer using the template's relative differences — so Medicare still runs lower than Commercial, but the weighted mean matches what you entered. Everything you don't specify inherits the template's defaults (tagged `prior`).

Hit Enter on any prompt to accept the default. Ctrl+C exits without writing.

## 3. First run

```bash
rcm-mc \
  --actual actual.yaml \
  --benchmark configs/benchmark.yaml \
  --outdir outputs \
  --n-sims 5000 \
  --no-report
```

- `--actual` / `--benchmark` — the two YAML scenarios being compared.
- `--outdir` — where results go (created if missing).
- `--n-sims` — iteration count. Default is 30,000; 5,000 is a fast learning run.
- `--no-report` — skips HTML generation while iterating.

When it finishes:

```bash
ls outputs
```

You should see `summary.csv`, `simulations.csv`, `provenance.json`, and several chart PNGs.

---

## 3. What to open first

| File | How to read it |
|------|----------------|
| `outputs/summary.csv` | Open in Excel / Numbers. Mean, P10, P90 per metric. |
| `outputs/provenance.json` | Text editor. Formulas and run metadata. |
| `outputs/report.html` | Browser — after running without `--no-report`. |
| `outputs/simulations.csv` | Large table, one row per iteration. For pandas / deep analysis. |

---

## 4. Change assumptions

### Edit a YAML config

Open `configs/actual.yaml` in a text editor. Change one thing (e.g. `hospital.annual_revenue` or a payer's `denials.idr` mean). Save. Re-run.

### Lint without simulating

```bash
rcm-mc --actual configs/actual.yaml --benchmark configs/benchmark.yaml --validate-only
```

### See every resolved config key

```bash
rcm-mc --actual configs/actual.yaml --explain-config
```

### Diff two configs

```bash
rcm-mc --actual configs/actual.yaml --benchmark configs/benchmark.yaml \
       --diff configs/actual.yaml configs/benchmark.yaml
```

### Start from a template

```bash
rcm-mc --template community_hospital_500m \
       --benchmark configs/benchmark.yaml \
       --outdir outputs_template --n-sims 3000 --no-report
```

Templates live in `configs/templates/`.

---

## 5. Calibrate from CSV diligence data

Point `--actual-data-dir` at a folder containing `claims_summary*.csv`, `denials*.csv`, `ar_aging*.csv`.

Safe demo (synthetic data):

```bash
rcm-mc \
  --actual configs/actual.yaml \
  --benchmark configs/benchmark.yaml \
  --actual-data-dir data_demo/target_pkg \
  --n-sims 20000 \
  --outdir outputs_demo_calibrated
```

Look for:
- `calibrated_actual.yaml` — what the model actually used.
- `calibration_actual_report.csv` — what changed and why.
- `data_quality_report.json` — ingestion audit.

---

## 6. JSON scenario overlays

Instead of editing YAML by hand, drop a JSON file:

```json
{
  "annual_revenue": 480000000,
  "fte_change": 2
}
```

```bash
rcm-mc --actual configs/actual.yaml --benchmark configs/benchmark.yaml \
       --scenario my_scenario.json --outdir outputs_scenario --no-report
```

Supported keys live in [rcm_mc/scenario_builder.py](../rcm_mc/scenario_builder.py).

---

## 7. Full HTML report

Drop `--no-report`:

```bash
rcm-mc --actual configs/actual.yaml --benchmark configs/benchmark.yaml \
       --outdir outputs --n-sims 15000
```

Open `outputs/report.html`.

For the extended report (initiatives, stress, attribution, narrative methodology):

```bash
rcm-mc ... --full-report
```

---

## 8. Useful flags

| Flag | Purpose |
|------|---------|
| `--outdir DIR` | Output directory (default `outputs`) |
| `--n-sims N` | Iteration count (default 30,000) |
| `--seed N` | Reproducibility (default 42) |
| `--no-report` | Skip HTML |
| `--no-align-profile` | Compare raw configs instead of normalizing benchmark to actual scale/mix |
| `--theme NAME` | `default`, `dark`, `print`, `minimal` |
| `--markdown` | Write `report.md` |
| `--json-output` | Write `summary.json` |
| `--pptx` | Write `report.pptx` (needs `python-pptx`) |
| `--screen` | 1,000-sim screen, one-line output |
| `--trace-iteration N` | Dump one iteration as JSON |
| `--stress` | Stress-test suite → `stress_tests.csv` |
| `--initiatives` | Initiative ranking → `hundred_day_plan.csv` |
| `--attribution` | OAT driver attribution |
| `--value-plan PATH` | Value-creation plan YAML |
| `--pressure-test PATH` | Management plan pressure-test (classification + miss scenarios) |
| `--compare-to DIR` | Diff against prior output directory |
| `--list-runs` | List recent runs from `runs.sqlite` |

Full list: `rcm-mc --help`.

---

## 9. Pressure-test a management plan

Management handed you a value-creation deck? Encode it in a YAML and pressure-test it:

```bash
rcm-mc --actual actual.yaml --benchmark configs/benchmark.yaml \
       --pressure-test scenarios/management_plan_example.yaml \
       --outdir outputs
```

The module:

1. Classifies each target as `conservative` / `stretch` / `aggressive` / `aspirational` based on how far the target moves from the current actual toward the published top-decile benchmark.
2. Runs Monte Carlo at 100% / 75% / 50% / 0% of claimed improvement so the dollar cost of missing is concrete.
3. Cross-references `configs/initiatives_library.yaml` to compare management's horizon against typical ramp times for the matching initiatives.
4. Prints risk flags for compound execution risk (multiple aggressive targets) or timeline mismatches.

Results land in the workbook as **Plan Pressure Test** and **Plan Miss Scenarios** tabs, plus detail CSVs in `outputs/_detail/`.

---

## 10. Tests

```bash
pytest
```

Full run is several minutes. Quick check:

```bash
pytest tests/test_config_validation.py tests/test_provenance.py
```

---

## 10. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Terminal shows `>` and looks stuck | You pasted a markdown code fence. Press Ctrl+C, paste only the command line. |
| `ModuleNotFoundError: rcm_mc` | You're not in the project root, or `pip install -e .` wasn't run. |
| Validation errors | `--validate-only`; fix YAML indentation or required keys. |
| Slow runs | Lower `--n-sims`; add `--no-report` while iterating. |
| Matplotlib warnings | `export MPLCONFIGDIR="/tmp/mplcache"` |
| Out of disk | `simulations.csv` can be large. Lower `--n-sims` or use a fresh `--outdir`. |
