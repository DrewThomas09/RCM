# Report 0161: Config Map — `configs/value_plan.yaml`

## Scope

`RCM_MC/configs/value_plan.yaml` (46 lines) — value-creation-plan config. One of 5 YAMLs in `configs/` (per Report 0011 + 0131 + 0132). Only `playbook.yaml` (broken — Report 0131) and `actual.yaml` (Report 0011) previously mapped. **`value_plan.yaml` never reported.**

## Findings

### File header / intent

Per top comment (lines 1-7):
> "Value-creation plan: close a fraction of the Actual-to-Benchmark gap.
> Keep this simple and explainable:
> - `gap_closure` is the fraction of the gap you expect to close (0.0 to 1.0).
> - You can override specific payers in `gap_closure_by_payer`.
> - Costs are deliberately minimal: one-time + annual run-rate.
> - Timeline uses a linear ramp over ramp_months."

**Single-purpose deal-economics scenario.** Defaults represent a "Base case" partner perspective.

### Schema (key inventory)

| Key path | Type | Default | Purpose |
|---|---|---|---|
| `name` | str | `"Base case: close meaningful RCM gap"` | Human-readable label |
| `gap_closure.idr` | float | `0.30` | close 30% of initial denials gap |
| `gap_closure.fwr` | float | `0.40` | close 40% of final write-off rate gap |
| `gap_closure.stage_mix` | float | `0.25` | shift 25% toward benchmark stage mix |
| `gap_closure.dar_clean_days` | float | `0.25` | DSO improvement |
| `gap_closure.upr` | float | `0.30` | underpayment rate |
| `gap_closure.underpay_recovery` | float | `0.20` | recovery rate |
| `gap_closure_by_payer.Commercial.fwr` | float | `0.50` | per-payer override |
| `gap_closure_by_payer.Commercial.idr` | float | `0.35` | per-payer override |
| `operations.denial_capacity.fte_delta` | int | `2` | absolute FTE add |
| `costs.one_time` | int | `250000` | consulting/implementation USD |
| `costs.annual_run_rate` | int | `600000` | annual run-rate USD |
| `timeline.ramp_months` | int | `12` | linear ramp duration |
| `timeline.horizon_years` | int | `3` | analysis horizon |
| `timeline.discount_rate` | float | `0.12` | NPV discount |
| `deal.escrow_percentile` | float | `0.90` | escrow at 90th percentile of downside |

**16 keys across 6 top-level sections.** All have explicit defaults — no required-without-default.

### Validation

Per the YAML structure: ALL `gap_closure` values are bounded `0.0 ≤ x ≤ 1.0` (per comment line 4). **No CHECK constraint; relies on caller validation.**

### YAML parse-test

Per Report 0132 (closes 0131 Q1): `value_plan.yaml` parses cleanly. **Confirmed.**

### Readers

`grep "value_plan" RCM_MC/`: not run this iteration. Per file header + Report 0011 cross-link to `actual.yaml`: this is **CLI input** for `rcm-mc run --value-plan path/to/value_plan.yaml` likely.

### Default-fallback

If `value_plan.yaml` is omitted at runtime, the consumer likely uses `gap_closure = 0` defaults (no improvement) or refuses to run. **Q1 below.**

### Comparison to other configs

| Config | Lines | Status |
|---|---|---|
| `actual.yaml` (Report 0011) | ~150 | mapped |
| `benchmark.yaml` | ~?? | unmapped |
| `playbook.yaml` (Report 0131) | 43 | **BROKEN YAML** (MR744) |
| `initiatives_library.yaml` | ~?? | unmapped |
| **`value_plan.yaml` (this)** | **46** | **mapped** |

**3 of 5 configs now mapped.** 2 remain (`benchmark.yaml`, `initiatives_library.yaml`).

### Cross-link to PE math layer

The keys (`idr`, `fwr`, `dar_clean_days`, `upr`, `underpay_recovery`, `discount_rate`) are PE-math inputs. Per CLAUDE.md Phase 2: `pe_math.py` consumes these. Per Report 0142: `pe/` was partially audited (modules `dcf_model.py`, `lbo_model.py`, etc.); `value_plan.yaml` likely feeds `dcf_model.py` discount + escrow inputs.

### `escrow_percentile: 0.90`

Single-key escrow setting. Per typical PE practice: deal escrow sized at 90th-percentile downside. **Per Report 0061 + cross-link to MC simulator (Report 0117 mc_simulation_runs).**

### Minimal-cost philosophy

Per docstring line 5: "Costs are deliberately minimal: one-time + annual run-rate."

**Strict cost model**: only 2 cost inputs (`one_time`, `annual_run_rate`). No category-by-category cost breakdown. Per CLAUDE.md "Don't add features beyond what the task requires" — disciplined.

### Override pattern

`gap_closure_by_payer.<Payer>` enables per-payer overrides on top of base `gap_closure`. **Sample override**: `Commercial.fwr = 0.50` (vs base `0.40`). Cross-link Report 0134 `deal_overrides.payer_mix.<payer>` overrides — **different mechanism for similar concept.** Both override gap-closure assumptions per payer.

**Inconsistency**: `value_plan.yaml` has its own override schema vs `deal_overrides` table. Two parallel paths.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR869** | **`gap_closure_by_payer` and `deal_overrides.payer_mix.*` are parallel override mechanisms** | Cross-link Report 0134 deal_overrides 5-namespace whitelist (`payer_mix`, `method_distribution`, `bridge`, `ramp`, `metric_target`). value_plan.yaml uses `Commercial`, `Medicare` payer names directly. **Inconsistent naming + storage.** | Medium |
| **MR870** | **`value_plan.yaml` defaults do NOT enforce 0.0-1.0 bounds** | Comment says "0.0 to 1.0" but YAML lacks CHECK. A user-supplied `gap_closure.idr: 1.5` slips through. Caller validation needed. | Low |
| **MR871** | **No `value_plan.yaml` reference in CLAUDE.md "Running" section** | Per Report 0011 actual.yaml is documented; this isn't. Config-doc gap. | Low |
| **MR872** | **`escrow_percentile: 0.90` hardcoded as default** | Some deals warrant 95th or 75th. Default is conservative-medium. Documented per docstring line 7. | (clean) |

## Dependencies

- **Incoming:** likely `rcm-mc run` CLI (per CLAUDE.md), pe_math layer.
- **Outgoing:** YAML file on disk; consumed via `yaml.safe_load`.

## Open questions / Unknowns

- **Q1.** What's the consumer of `value_plan.yaml`? Likely `pe_math.py` or `dcf_model.py`.
- **Q2.** What happens at runtime if file is missing — defaults assumed, or error?
- **Q3.** `gap_closure_by_payer.Commercial` (this YAML) vs `deal_overrides.payer_mix.commercial_share` (deal_overrides) — different naming conventions (Capitalized vs lowercase). Why?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0162** | Data flow trace (in flight). |
| **0163** | Map remaining `benchmark.yaml` + `initiatives_library.yaml` configs. |

---

Report/Report-0161.md written.
