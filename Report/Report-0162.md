# Report 0162: Data Flow Trace — `value_plan.yaml` → PE Math

## Scope

Traces `RCM_MC/configs/value_plan.yaml` (Report 0161 mapped) through the PE-math layer. Sister to Reports 0011 (actual.yaml flow), 0102 (data refresh), 0108 (login), 0132 (Idempotency-Key).

## Findings

### Hop-by-hop trace

#### Hop 1 — File on disk

`RCM_MC/configs/value_plan.yaml` (46 lines, per Report 0161). Default-shipped with the wheel per Report 0101 `[tool.setuptools.package-data]`.

#### Hop 2 — CLI flag

Per CLAUDE.md "Running" section + per `rcm-mc` console-script entry (Report 0086 + 0139):

```bash
rcm-mc run --actual configs/actual.yaml --benchmark configs/benchmark.yaml --value-plan configs/value_plan.yaml
```

The `--value-plan` flag accepts the YAML path. CLI argparse stage at `cli.py` (1252 LOC, owed since Report 0003).

#### Hop 3 — `yaml.safe_load`

Caller invokes `yaml.safe_load(open(path))`. Per Report 0011 + 0131 + 0132: `safe_load` is the project standard. Cross-link Report 0131 MR744 (playbook.yaml broken YAML — different file but same loader).

If `value_plan.yaml` parse fails, caller behavior TBD. Per Report 0131: `html_report.py` swallows; `cli.py` likely raises (CLI input error).

#### Hop 4 — Config dict consumed by PE math

The dict shape (per Report 0161):

```python
{
    "name": "Base case: close meaningful RCM gap",
    "gap_closure": {"idr": 0.30, "fwr": 0.40, "stage_mix": 0.25,
                    "dar_clean_days": 0.25, "upr": 0.30, "underpay_recovery": 0.20},
    "gap_closure_by_payer": {"Commercial": {"fwr": 0.50, "idr": 0.35}},
    "operations": {"denial_capacity": {"fte_delta": 2}},
    "costs": {"one_time": 250000, "annual_run_rate": 600000},
    "timeline": {"ramp_months": 12, "horizon_years": 3, "discount_rate": 0.12},
    "deal": {"escrow_percentile": 0.90},
}
```

Likely consumed by:
- `pe/dcf_model.py` (215 LOC per Report 0142 — uses `discount_rate`, `horizon_years`)
- `pe/lbo_model.py` (285 LOC — likely uses `costs`)
- `pe/value_bridge_v2.py` (per Report 0112 `mc/v2_monte_carlo.py` cross-link — uses bridge inputs)
- `rcm/initiatives.py` (per CLAUDE.md — uses `gap_closure` to model initiative outcomes)

#### Hop 5 — Per-payer override merge

`gap_closure_by_payer.Commercial` overrides on top of base `gap_closure`. Likely merged via dict update or per-payer indexing.

**Cross-link Report 0134 deal_overrides** — `deal_overrides.payer_mix.<payer>_share` is a DIFFERENT override mechanism stored in SQLite. Two parallel paths to override the same conceptual values. **Cross-link Report 0161 MR869.**

#### Hop 6 — Linear ramp computation

Per file header line 7: "Timeline uses a linear ramp over `ramp_months`."

**Computation**: `gap_closure_t = gap_closure * min(1, t / ramp_months)`. Linear from 0 → full gap closure over `ramp_months`. Cross-link Report 0093 ml/`temporal_forecaster.py` (different math but same time-series concept).

#### Hop 7 — DCF / NPV

`timeline.discount_rate = 0.12` flows into `dcf_model.py`. NPV computation over `horizon_years = 3` years with monthly steps.

#### Hop 8 — Escrow percentile

`deal.escrow_percentile = 0.90` → 90th-percentile of MC downside used to size deal escrow. Cross-link Report 0117 `mc_simulation_runs` (where MC results land — `result_json` BLOB contains percentile bands).

#### Hop 9 — Output

Per the simulator → packet flow (Reports 0057, 0117, 0133):
- `MonteCarloResult` (per Report 0117) embeds value_plan-driven distribution
- `DealAnalysisPacket` (per Report 0057) consumes value_plan via packet_builder
- `analysis_runs.packet_json` BLOB holds the cached result

### Trust boundary

`value_plan.yaml` is **partner-supplied** (typically). Per Report 0136 + 0137 path-traversal class concerns: does `--value-plan path/to/file.yaml` validate the path?

**Possible attack**: malicious YAML with `!!python/object/apply:os.system ['rm -rf /']` if `yaml.load` were used instead of `yaml.safe_load`.

**Mitigation**: per Report 0131 + 0132 + this iteration: project uses `yaml.safe_load`. **Safe** against deserialization attacks.

But: the file PATH could traverse to `/etc/passwd` etc. Per Report 0137 `deal_sim_inputs` MR777 — same path-traversal class. **Likely no validation in `cli.py` either.**

**MR873 below.**

### Override-mechanism schism (cross-link Report 0161 MR869)

Two parallel paths to override gap-closure assumptions per payer:

| Path | Storage | Schema |
|---|---|---|
| `value_plan.yaml gap_closure_by_payer.Commercial.fwr` | YAML on disk | hardcoded payer names (Commercial, Medicare) |
| `deal_overrides.payer_mix.commercial_share` (Report 0134) | SQLite | strict-validated lowercase |

**Consumer must merge both.** Cross-link Report 0134 `validate_override_key` (strict) vs YAML free-form. **Inconsistency.**

### Where it surfaces to users

- **CLI**: `rcm-mc run --value-plan` flag, file-side configurable.
- **API**: TBD — likely a JSON-body POST that contains the same shape (per Report 0102 pattern).
- **UI**: per Report 0091 partial; specific UI page TBD.

### Cross-link to Report 0058 + Report 0148 hash_inputs

`hash_inputs` (per Report 0148) does NOT include `value_plan` parameters. **A change to `value_plan.yaml` does NOT invalidate the cache.** This is the same Report 0058 MR417 / Report 0148 MR823 high concern. **Re-affirmed.**

If a user changes value_plan from `gap_closure.idr=0.30` to `0.50` and reruns, **the cached packet (which embeds the old value_plan computation) is silently returned**. **MR874 below.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR873** | **`--value-plan path/to/file.yaml` likely lacks path validation** | Cross-link Report 0136 MR772 + Report 0137 MR777. A user could supply `--value-plan /etc/secret.yaml` to inject anything that parses as YAML matching the value_plan shape. | **Medium** |
| **MR874** | **`hash_inputs` (Report 0148) does NOT include value_plan parameters** | Changing value_plan.yaml after a run produces a stale cached packet. **Same risk class as Report 0058 MR417 / 0148 MR823.** **Should add value_plan content-hash to hash_inputs payload.** | **High** |
| **MR875** | **Two parallel override mechanisms** (`value_plan.yaml gap_closure_by_payer` + `deal_overrides.payer_mix`) | Cross-link Report 0161 MR869. Inconsistent naming (`Commercial` vs `commercial`); inconsistent storage (YAML vs SQLite); inconsistent validation (free-form vs strict regex). | (carried) |
| **MR876** | **`yaml.safe_load` discipline holds** — no risk of arbitrary-eval through value_plan.yaml | Cross-link Report 0131 + 0132. Project consistent with safe_load. | (clean) |

## Dependencies

- **Incoming:** `rcm-mc run --value-plan` CLI (likely cli.py), demo.py (Report 0130), tests.
- **Outgoing:** PyYAML's safe_load, pe/dcf_model + pe/lbo_model + pe/value_bridge_v2 + rcm/initiatives.

## Open questions / Unknowns

- **Q1.** Where exactly in `cli.py` is `--value-plan` parsed?
- **Q2.** Does the value_plan get folded into `hash_inputs` somewhere downstream that this audit missed?
- **Q3.** What does `pe/value_bridge_v2.py` (mentioned in Report 0112 mc cross-import) consume from value_plan?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0163** | Read `cli.py` `--value-plan` argparse setup (closes Q1, also chips at the 19+ iter cli.py debt). |
| **0164** | Read `pe/dcf_model.py` (215 LOC, never deeply read per Report 0142). |
| **0165** | Verify Q2 — does anything fold value_plan into hash_inputs? |

---

Report/Report-0162.md written.
