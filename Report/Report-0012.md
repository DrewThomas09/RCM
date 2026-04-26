# Report 0012: Data-Flow Trace — `actual.yaml` → Simulator → Disk

## Scope

This report covers the **end-to-end data-flow trace** of an `actual.yaml` config file from CLI invocation to output artifacts on `origin/main` at commit `f3f7e7f`. The input source was selected because it is the canonical user-supplied input to every Monte Carlo run, just mapped in Report 0011, and tracing it produces a complete spine map of the simulator pipeline. The trace cites every hop with `file:line`.

The trace covers the **production / `cli.py`** path. The CSV-data-dir override (`--actual-data-dir`), interactive intake wizard (`data/intake.py`), and HTTP-form upload (`server.py`) are sister entry points and are noted but not traced in detail this iteration.

Prior reports reviewed before writing: 0008-0011.

## Findings

### Stage 0 — User invocation (CLI)

```
$ rcm-mc --actual configs/actual.yaml --benchmark configs/benchmark.yaml \
         --n-sims 30000 --seed 42 --outdir output/
```

| Hop | File:line | What |
|---|---|---|
| Console-script wire-up | `RCM_MC/pyproject.toml:69` | `rcm-mc = "rcm_mc.cli:main"` |
| Argparse declaration | `RCM_MC/rcm_mc/cli.py:55` | `ap.add_argument("--actual", required=True, help="Path to actual scenario YAML")` |
| Argparse declaration (paired) | `RCM_MC/rcm_mc/cli.py:56` | `ap.add_argument("--benchmark", required=True, help="...")` |

`args.actual` enters as a string path. CLI also accepts `--actual-data-dir` (line 59) for the CSV-driven override, but that is a sister flow.

### Stage 1 — File load (YAML → dict)

| Hop | File:line | What |
|---|---|---|
| Top-level CLI dispatcher | `RCM_MC/rcm_mc/cli.py:339` | `actual_cfg = load_and_validate(args.actual)` (also at `:373`, called twice depending on subcommand) |
| Loader entry | `RCM_MC/rcm_mc/infra/config.py:436` | `def load_and_validate(path: str) -> Dict[str, Any]: return validate_config(load_yaml(path))` |
| Raw YAML load | `RCM_MC/rcm_mc/infra/config.py:58-78` | `load_yaml(path)` opens the file, calls `yaml.safe_load`, then runs `_resolve_env_vars` (line 36) for `${VAR}` / `${VAR:default}` substitution and `_extends` inheritance via `_deep_merge` (line 25). |

After Stage 1, the file is an in-memory `Dict[str, Any]` with env-vars expanded and any `_extends` parent merged.

### Stage 2 — Schema validation + default-fill

| Hop | File:line | What |
|---|---|---|
| Validator entry | `RCM_MC/rcm_mc/infra/config.py:200` | `def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]` |
| Required: `hospital` | `infra/config.py:207` | `_require("hospital" in cfg ...)` |
| Required: `hospital.annual_revenue` | `infra/config.py:208-209` | typed-cast to float |
| Optional: `deal` block validation | `infra/config.py:214-215` | `_validate_deal_section` if present |
| Required: `payers` | `infra/config.py:217-218` | dict + per-payer validation |
| Payer-name canonicalization | `infra/config.py:80, 218-227` | `canonical_payer_name` aliases (e.g. `BCBS` → `Commercial`) |
| Required: `appeals.stages` | `infra/config.py:347-348` | each declared stage validated |
| Per-stage dist-spec validation | `infra/config.py:348-399` | `_validate_dist_spec` (line 119) on every cost+days dist |
| Default fills | `infra/config.py:339-431` | `n_sims=30000, seed=42, working_days=250, wacc_annual=0.12, denial_capacity={}, underpay_delay_spillover=0.35, underpayments.enabled=True` |

After Stage 2, `cfg` is a fully-populated dict ready for Monte Carlo. Per Report 0011 MR76, the schema is implicit in this validator function (no JSON Schema, no Pydantic).

### Stage 3 — Monte Carlo dispatch

| Hop | File:line | What |
|---|---|---|
| Production import | `RCM_MC/rcm_mc/cli.py:31` | `from .core.simulator import simulate_compare` |
| CLI single-run path | `RCM_MC/rcm_mc/cli.py:443` | `df = simulate_compare(actual_cfg, bench_cfg, ...)` |
| CLI breakdown path | `RCM_MC/rcm_mc/cli.py:423` | `df, bds = simulate_compare_with_breakdowns(...)` (when breakdown drivers requested) |
| CLI screen path | `RCM_MC/rcm_mc/cli.py:341-342` | `from .core.simulator import simulate_compare as _sc; df = _sc(actual_cfg, bench_cfg, n_sims=1000, ...)` (lighter run for `rcm-mc --screen`) |

### Stage 4 — Per-iteration Monte Carlo

| Hop | File:line | What |
|---|---|---|
| Outer driver | `RCM_MC/rcm_mc/core/simulator.py:601` | `def simulate(cfg, n_sims, seed, include_payer_drivers=True, progress_callback=None, early_stop=True, registry=None) -> pd.DataFrame` |
| Per-iteration single | `RCM_MC/rcm_mc/core/simulator.py:525` | `def simulate_one(cfg, rng) -> Dict[str, Any]` |
| Payer enumeration | `simulator.py:526` | `payer_names = list(cfg["payers"].keys())` |
| Per-payer pass-1 (sampling) | `simulator.py:527` | `payer_states = [_simulate_payer_pass1(cfg, p, rng) for p in payer_names]` |
| Pass-1 internals | `simulator.py:102-283` | `_simulate_payer_pass1(cfg, payer, rng)` reads `pconf = cfg["payers"][payer]` (line 103) — pulls every payer-level distribution spec for that iteration |
| Pass-2 (capacity/backlog) | `simulator.py:284-524` | `_simulate_payer_pass2(...)` applies operational constraints (denial_capacity, backlog) using `cfg["operations"]` (read at line 297) |
| Top-level reads | `simulator.py:104, 294, 295` | `R_total = cfg["hospital"]["annual_revenue"]` (104); `appeals = cfg["appeals"]["stages"]` (294); `wacc = cfg["economics"]["wacc_annual"]` (295) |

### Stage 5 — Distribution sampling

Every YAML `{dist: beta, mean, sd, ...}` block becomes a numpy sample via:

| Hop | File:line | What |
|---|---|---|
| `sample_dist` | `RCM_MC/rcm_mc/core/distributions.py:147` | `def sample_dist(rng: np.random.Generator, spec: Optional[Dict[str, Any]], size: Optional[int] = None) -> np.ndarray` |

This is the single chokepoint for converting YAML dist specs into numpy arrays. Every payer denial rate, dar_clean_days draw, appeal-cost draw, etc. flows through this one function. Report 0011 Q2 (which dist types are accepted) is the open question on this hop.

### Stage 6 — Output (DataFrame → disk)

After `simulate()` returns a `pd.DataFrame`, the CLI writes artifacts:

| Hop | File:line | What |
|---|---|---|
| Summary CSV write | `cli.py:391` | `report.round(4).to_csv(report_path, index=False)` (writes `summary.csv` to outdir) |
| Calibrated YAML write | `cli.py:393` | `calibrated_path = os.path.join(outdir, "calibrated_actual.yaml")` (the validated config back to disk for reproducibility) |
| Calibrated benchmark | `cli.py:411` | `calibrated_path = os.path.join(outdir, "calibrated_benchmark.yaml")` |
| Anomaly JSON | `cli.py:403` | `json.dump(anom.to_list(), af, indent=2)` |
| Per-driver CSVs | `cli.py:431-437` | `bds["actual"]["payer_denial_type"].to_csv(...)`, etc. (6 driver-breakdown CSVs) |
| Per-assumption CSVs | `cli.py:419` | `assump.round(3).to_csv(os.path.join(outdir, f"assumptions_{name}.csv"))` |
| Index page | `RCM_MC/rcm_mc/infra/output_index.py:282` | `build_output_index(outdir, ...)` writes `index.html` grouping every artifact (called at `:352`, `:357`) |

### End-to-end summary diagram (text)

```
  configs/actual.yaml
        │
        │ rcm-mc --actual ...
        ▼
  cli.py:55  argparse --actual
        │
        ▼
  cli.py:339  load_and_validate(path)
        │
        ▼
  infra/config.py:436  load_and_validate
        │
        ├──► infra/config.py:58  load_yaml      (yaml.safe_load + env-vars + _extends)
        │
        ▼
  infra/config.py:200  validate_config          (required-key check + default fill)
        │
        ▼
  cli.py:443  simulate_compare(actual_cfg, ...)
        │
        ▼
  core/simulator.py:601  simulate(cfg, n_sims, seed, ...)
        │
        │  for i in range(n_sims):
        ▼
  core/simulator.py:525  simulate_one(cfg, rng)
        │
        ├──► simulator.py:102 _simulate_payer_pass1(cfg, payer, rng)
        │     │
        │     └──► distributions.py:147 sample_dist(rng, spec, size)  ← every YAML dist spec
        │
        └──► simulator.py:284 _simulate_payer_pass2(...)               (capacity / backlog)
        │
        ▼
  pd.DataFrame (rows=n_sims, columns=summary metrics)
        │
        ▼
  cli.py:391  to_csv(summary.csv)
  cli.py:393  yaml.dump(calibrated_actual.yaml)
  cli.py:431  to_csv(driver breakdown CSVs)
  cli.py:419  to_csv(assumptions_*.csv)
        │
        ▼
  infra/output_index.py:282  build_output_index(outdir)
        │
        ▼
  outdir/index.html  +  outdir/*.csv  +  outdir/*.yaml  +  outdir/*.json
```

### Sister flows (not traced, but flagged)

- **CSV override:** `cli.py:59 --actual-data-dir` reads CSVs and auto-marks fields as `observed` in the source-map. Calibrates the YAML before validation.
- **Interactive intake wizard:** `RCM_MC/rcm_mc/data/intake.py:619 main()` writes a fresh `actual.yaml` from 11 prompts. Entry point declared at `pyproject.toml:70` — but the entry-point path is broken (Report 0003 MR14: `rcm-intake = "rcm_mc.intake:main"` references a module that doesn't exist; actual main lives at `rcm_mc.data.intake`).
- **HTTP upload:** `server.py:291` and `server.py:12745` render an HTML form with `placeholder="/path/to/actual.yaml"`. The path is then loaded by the same `load_and_validate` chokepoint.
- **API endpoint:** `RCM_MC/rcm_mc/api.py` (orphan per Report 0010 — not imported anywhere) declares a FastAPI handler that also calls `validate_config`. Reachable only via direct uvicorn invocation.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR84** | **Three load sites for `actual.yaml` schema (`cli.py`, `api.py`, `server.py`)** | All three call `load_and_validate` from `infra/config.py:436`. A branch that changes the loader signature ripples to all three, but only one is well-tested (`cli.py`). Since `api.py` is an orphan (Report 0010 MR72), changes can break it silently. | **High** |
| **MR85** | **CSV override path (`--actual-data-dir`) re-fills YAML before validation** | `cli.py:387` triggers a separate code path that auto-marks fields as `observed`. If a feature branch changes the source-map shape (`_source_map`), the CSV override may inject incompatible values. Pre-merge: read `cli.py:387-410` end-to-end. | Medium |
| **MR86** | **`sample_dist` is the single sampling chokepoint** | `core/distributions.py:147`. Any branch that adds a new distribution shape (e.g. `mixture`, `empirical`) to `_validate_dist_spec` (config.py:119) MUST also add the case to `sample_dist`. Two-place edit; easy to half-do. | **High** |
| **MR87** | **Output writers are scattered across `cli.py:391-437`** | At least 9 distinct `to_csv` / `json.dump` / `yaml.safe_dump` call sites in `cli.py` (lines 391, 393, 403, 410, 411, 419, 431-437). A branch that adds a new output artifact must also wire it into `build_output_index` (output_index.py:282) so it appears in the index — easy to forget; index drift = silent UX regression. | Medium |
| **MR88** | **`calibrated_actual.yaml` and `calibrated_benchmark.yaml` written into outdir** | Round-trip artifacts written at `cli.py:393, 411`. Their schema must match the input schema; if a branch changes the input schema, `yaml.safe_dump` of the validated dict will produce a "calibrated" file the *next* run cannot re-load (because the schema is incompatible). Closed-loop regression risk. | **High** |
| **MR89** | **`build_output_index` discovers artifacts by glob** | `infra/output_index.py:282` builds the index from filesystem state. A branch that renames a file (e.g. `summary.csv` → `simulation_summary.csv`) breaks the index entry but produces no Python error — silent UX regression. | Medium |
| **MR90** | **The pipeline is single-threaded with no shared mutable state — but `numpy.random.Generator` is constructed once** | `simulator.py:601` accepts `seed` and constructs an RNG at top. Per-iteration `rng` is presumably forked. If a branch refactors RNG sharing, determinism (every run with `seed=42` must produce identical output) can break silently. **No deterministic-output regression test currently visible.** | **High** |
| **MR91** | **Three sister flows (`api.py`, `intake`, `server.py`) duplicate validation** | All three call `load_and_validate`, but each has its own pre-processing layer (`api.py` for HTTP, `intake.py` for interactive prompts, `server.py:12745` for HTML form). A branch that changes the YAML shape must update all three pre-processors. **`intake.py` already has the broken entry-point bug** (MR14). | **High** |

## Dependencies

- **Incoming (who consumes the data this flow produces):** every downstream PE-math module (bridge, MOIC, IRR), the analysis packet (`analysis/packet_builder.py`), the report renderers, the persisted run records (`portfolio/store.py:add_run`).
- **Outgoing (what this flow depends on):** YAML library (`pyyaml` — pinned in `pyproject.toml:29`), numpy (for sampling), pandas (for the output DataFrame), filesystem (write to outdir).

## Open questions / Unknowns

- **Q1 (this report).** What does `--actual-data-dir` (`cli.py:59`) do exactly? It auto-marks fields as `observed` — but the transform from CSV columns to YAML keys is a separate pipeline that I have not yet read.
- **Q2.** Does `sample_dist` (line 147) accept `empirical` or other shapes I haven't enumerated? Answers Q2 from Report 0011 too.
- **Q3.** Is the `seed` propagated deterministically through every per-iteration RNG fork? If a branch breaks determinism, what regression test would catch it?
- **Q4.** Does `build_output_index` validate that *all expected* artifacts exist? Or does it silently render a partial index when a writer fails?
- **Q5.** What does `_resolve_env_vars` (config.py:36) do for nested keys? Does it recurse, or only top-level?
- **Q6.** What's the round-trip relationship between `actual.yaml` (input) and `calibrated_actual.yaml` (output)? Are they bit-for-bit identical aside from default-fill, or are there other transforms?
- **Q7.** Is the `provenance/` subsystem (per `_source_map._default: assumed`) wired through this flow, or is it consulted independently? When a downstream renderer asks "where did this number come from?" — what's the lookup path?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0013** | **Read `core/simulator.py:simulate_one` and `_simulate_payer_pass1` end-to-end.** | Closes the per-iteration logic of the trace. Resolves Q3. |
| **0014** | **Read `core/distributions.py:sample_dist` and `_validate_dist_spec`.** | Resolves Q2 / MR86. Single line to enumerate dist shapes accepted. |
| **0015** | **Read `infra/output_index.py:build_output_index`.** | Resolves Q4 / MR89. Tells us what the index discovery does. |
| **0016** | **Read `cli.py:387-410` `--actual-data-dir` CSV-override path.** | Resolves Q1 / MR85. |
| **0017** | **Read `provenance/*` subsystem.** | Resolves Q7. |
| **0018** | **Read `core/calibration.py`** — Report 0011 noted it calls `yaml.safe_load(yaml.safe_dump(base_cfg))` for deep-copy. Calibration is a sister transform. | Round-trip coverage. |

---

Report/Report-0012.md written. Next iteration should: read `core/distributions.py:sample_dist` (line 147) end-to-end and enumerate every distribution shape accepted, closing MR86 and Report 0011 Q2 in one stroke.

