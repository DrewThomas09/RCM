# Report 0011: Config Map — `RCM_MC/configs/actual.yaml`

## Scope

This report covers **`RCM_MC/configs/actual.yaml`** (136 lines, the canonical simulator-input config) on `origin/main` at commit `f3f7e7f`. For every top-level key, document: meaning, schema (required vs defaulted), default value (if any), and the code paths that read it. Loader + validator are also mapped end-to-end.

`actual.yaml` was chosen because it is the primary user-supplied config — every Monte Carlo run flows through `validate_config(load_yaml(path))`. The companion `benchmark.yaml` shares the same schema and is omitted to keep this iteration focused.

Prior reports reviewed before writing: 0007-0010.

## Findings

### Loader path

```
user invocation:                rcm-mc --actual <path> --benchmark <path> ...
CLI declaration:                RCM_MC/rcm_mc/cli.py:55  --actual required=True
                                RCM_MC/rcm_mc/cli.py:56  --benchmark required=True
load + validate entry:          RCM_MC/rcm_mc/cli.py:339  load_and_validate(args.actual)
load_and_validate impl:         RCM_MC/rcm_mc/infra/config.py:436-437
                                  return validate_config(load_yaml(path))
yaml.safe_load wrapper:         RCM_MC/rcm_mc/infra/config.py:58  load_yaml
schema validator:               RCM_MC/rcm_mc/infra/config.py:200  validate_config
```

`validate_config` enforces required sections, fills defaults, validates distribution specs, and returns the augmented config dict.

### Top-level keys (ordered as they appear in the file)

| Key (line) | Type / shape | Required? | Default | Read by |
|---|---|---|---|---|
| `_source_map` (7) | dict, e.g. `{_default: assumed}` | No | (provenance tagging only) | `RCM_MC/rcm_mc/provenance/*` (not enumerated this iteration) |
| `hospital` (10) | dict | **REQUIRED** | — | `core/simulator.py`, `pe/`, `infra/config.py:207` |
| `hospital.name` (11) | string | No (purely informational) | — | UI rendering, output filenames |
| `hospital.annual_revenue` (12) | int (USD) | **REQUIRED** | — | `core/simulator.py:104` (`R_total = float(cfg["hospital"]["annual_revenue"])`); `infra/config.py:208-209` enforces presence |
| `analysis` (14) | dict | No (defaults filled) | — | — |
| `analysis.n_sims` (15) | int | No | **30000** (`infra/config.py:339`) | `core/simulator.py` Monte Carlo iteration count |
| `analysis.seed` (16) | int | No | **42** (`infra/config.py:340`) | `core/simulator.py` RNG seed (deterministic runs) |
| `analysis.working_days` (17) | int | No | **250** (`infra/config.py:341`) | `core/simulator.py` capacity calculations |
| `economics` (19) | dict | No (defaults filled) | — | — |
| `economics.wacc_annual` (20) | float | No | **0.12** (`infra/config.py:344`) | `core/simulator.py:295` (`wacc = float(cfg["economics"]["wacc_annual"])`) |
| `operations` (22) | dict | No (defaults filled) | — | — |
| `operations.denial_capacity` (23) | dict | No | **`{}`** (`infra/config.py:359`) | `core/simulator.py:297` (`cap = cfg["operations"]["denial_capacity"]`) |
| `operations.denial_capacity.enabled` (24) | bool | No | (assumed False if absent) | simulator capacity branch |
| `operations.denial_capacity.fte` (25) | int | No | (no default; behavior on missing TBD) | simulator capacity calc |
| `operations.denial_capacity.denials_per_fte_per_day` (26) | int | No | (no default) | simulator capacity calc |
| `operations.denial_capacity.backlog` (27) | dict | No | — | simulator backlog branch |
| `operations.denial_capacity.backlog.enabled` (28) | bool | No | (assumed False if absent) | simulator |
| `operations.denial_capacity.backlog.stage_shift_per_x` (29) | float | No | — | simulator backlog effect on stage mix |
| `operations.denial_capacity.backlog.fwr_logit_penalty_per_x` (30) | float | No | — | simulator FWR adjustment |
| `operations.denial_capacity.backlog.days_multiplier_per_x` (31) | float | No | — | simulator A/R day inflation |
| `operations.denial_capacity.backlog.max_over_capacity_x` (32) | float | No | — | simulator cap on backlog effect |
| `operations.underpay_delay_spillover` (implicit, not in this YAML) | float | No | **0.35** (`infra/config.py:427`) | simulator |
| `underpayments` (34) | dict | No (defaults filled) | — | — |
| `underpayments.enabled` (35) | bool | No | **True** (`infra/config.py:431`) | gate on the underpayment branch in simulator |
| `appeals` (37) | dict | **REQUIRED** | — | `infra/config.py:347` enforces presence |
| `appeals.stages` (38) | dict | **REQUIRED** | — | `infra/config.py:348-399` validates; `core/simulator.py:294` reads (`appeals = cfg["appeals"]["stages"]`) |
| `appeals.stages.<L1\|L2\|L3>.cost` (40, 43, 46) | distribution spec | **REQUIRED** per declared stage | — | simulator cost-of-appeal sampling |
| `appeals.stages.<L1\|L2\|L3>.days` (41, 44, 47) | distribution spec | **REQUIRED** per declared stage | — | simulator days-to-appeal sampling |
| `payers` (49) | dict | **REQUIRED** | — | `core/simulator.py:103` (`pconf = cfg["payers"][payer]`); `infra/config.py:217-227` validates and canonicalizes payer names |

### `payers.<Name>` schema (per-payer block, lines 49-136)

The YAML defines 4 payers — `Medicare` (line 52), `Medicaid` (line 78), `Commercial` (line 105), `SelfPay` (line 131). Each payer block has the same schema:

| Sub-key | Type | Required? | Default | Notes |
|---|---|---|---|---|
| `revenue_share` | float (0..1) | **REQUIRED** | — | Sum of all `revenue_share` values must total 1.0 (validation at `infra/config.py` `_sum_to_one`). |
| `avg_claim_dollars` | int | **REQUIRED** | — | Average dollar amount per claim. |
| `include_denials` | bool | No | (assumed False if absent — must verify against simulator) | Toggle on the per-payer denial branch. |
| `include_underpayments` | bool | No | (assumed False if absent) | Toggle on the per-payer underpayment branch. |
| `dar_clean_days` | distribution spec | **REQUIRED** if any pipeline reads DAR | — | `normal_trunc {mean, sd, min, max}` shape. |
| `denials.idr` | distribution spec | **REQUIRED if** `include_denials=true` | — | Initial denial rate. `beta {mean, sd, min, max}` shape. |
| `denials.fwr` | distribution spec | **REQUIRED if** `include_denials=true` | — | Final write-off rate. `beta` shape. |
| `denials.denial_mix_concentration` | int | No | — | Dirichlet concentration parameter for denial-type mix. |
| `denials.stage_mix` | dict `{L1:.., L2:.., L3:..}` | No | — | Distribution of denials across appeal stages. |
| `denials.denial_types` | dict | No | — | Per denial-type: share, fwr_odds_mult, stage_bias. Validated structure. |
| `underpayments.upr` | distribution spec | **REQUIRED if** `include_underpayments=true` | — | Underpayment rate. |
| `underpayments.severity` | distribution spec | **REQUIRED** | — | |
| `underpayments.recovery` | distribution spec | **REQUIRED** | — | |
| `underpayments.followup_cost` | distribution spec | **REQUIRED** | — | |
| `underpayments.resolution_days` | distribution spec | **REQUIRED** | — | |

Distribution spec shapes accepted (per `infra/config.py:119` `_validate_dist_spec`):

- `normal_trunc {mean, sd, min, max}`
- `beta {mean, sd, min, max}`
- `lognormal {mean, sd}`
- (others may exist; `_validate_dist_spec` not fully read)

### Validation guarantees enforced by `validate_config`

| Check | Line | Guarantee |
|---|---|---|
| `hospital` is a dict | 207 | Required section present |
| `hospital.annual_revenue` exists and is float-castable | 208-209 | Required key |
| Optional `deal` section validation | 214-215 | `_validate_deal_section` if `deal` present |
| `payers` is a dict | 217 | Required |
| Payer names canonicalized | 218-227 | `canonical_payer_name` (line 80) maps aliases |
| Per-payer `revenue_share` sums to 1.0 | not yet read in detail | `_sum_to_one` helper (line 146) |
| `analysis.n_sims/seed/working_days` defaults | 339-341 | 30000 / 42 / 250 |
| `economics.wacc_annual` default | 344 | 0.12 |
| `appeals.stages` exists | 347-348 | Required |
| Per-stage cost+days dist spec validation | 348-399 | Each stage's distributions validated |
| `operations.denial_capacity` defaulted to `{}` | 359-360 | If section absent, empty dict added |
| `operations.underpay_delay_spillover` default | 427 | 0.35 |
| `underpayments.enabled` default | 431 | True |

### Reader fan-out

`validate_config` is called from at least 10 places (production + tests):

| Caller | Line | Purpose |
|---|---|---|
| `RCM_MC/rcm_mc/cli.py:339` | `load_and_validate(args.actual)` | Main CLI |
| `RCM_MC/rcm_mc/cli.py:340` | `load_and_validate(args.benchmark)` | Main CLI (benchmark) |
| `RCM_MC/rcm_mc/api.py` | (orphan per Report 0010) | FastAPI endpoint |
| `RCM_MC/rcm_mc/pe/value_plan.py` | (line not extracted) | Value plan |
| `RCM_MC/rcm_mc/analysis/packet_builder.py` | (line not extracted) | DealAnalysisPacket build |
| `RCM_MC/rcm_mc/analysis/challenge.py` | (line not extracted) | Challenge / pressure-test |
| `RCM_MC/rcm_mc/deals/deal.py` | (line not extracted) | Deal record creation |
| `RCM_MC/rcm_mc/scenarios/scenario_shocks.py` | (line not extracted) | Scenario layering |
| `RCM_MC/rcm_mc/data/intake.py` | (line not extracted) | Interactive intake wizard (broken entry point per Report 0003 MR14) |

### Companion configs (out of scope but related)

`RCM_MC/configs/` contains 4 sibling YAML files that share or extend this schema:

- `benchmark.yaml` (same schema as actual.yaml)
- `playbook.yaml` (initiative playbook)
- `initiatives_library.yaml` (catalog)
- `value_plan.yaml` (value plan)
- `scenario_presets/` (subdir of scenario YAMLs)
- `templates/` (subdir of starter templates — referenced in `cli.py:235` `--template` flag)

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR76** | **`actual.yaml` schema is implicitly defined — no JSON Schema, no Pydantic, no canonical reference** | The schema lives in `infra/config.py:200 validate_config`. Adding a new key requires editing `validate_config` AND the file, and there's no machine-readable schema. **Branches that add new config keys will silently diverge.** Pre-merge: any branch that touches `infra/config.py:validate_config` or adds keys to `configs/*.yaml` needs careful review. | **High** |
| **MR77** | **Defaults are imperative-not-declarative** | `cfg["analysis"].setdefault("n_sims", 30000)` (line 339). A branch that changes the default (e.g. to 50000) silently shifts every existing run that didn't pin `n_sims`. **No migration path.** | **High** |
| **MR78** | **`canonical_payer_name` (line 80) maps aliases** | If a feature branch adds a new payer alias (e.g. "BCBS Federal" → "Commercial"), it's a one-line change in `canonical_payer_name` — but a branch that *removes* an alias breaks every config relying on it. | Medium |
| **MR79** | **No upgrade/migration tooling** | If a future version of the schema is incompatible (e.g. `denials.idr` becomes required), every existing `actual.yaml` in customer hands breaks at validation. No `--migrate-config` CLI flag detected. | Medium |
| **MR80** | **`include_denials` / `include_underpayments` defaults not in the file or validator** | The example `actual.yaml` sets these explicitly per payer. If a branch adds a new payer block without these keys, behavior depends on simulator's `pconf.get("include_denials", ?)` (which I have not yet read) — could be True or False. **Pre-merge: read simulator branches that touch these flags.** | Medium |
| **MR81** | **`infra/config.py:validate_config` is the chokepoint for every config** | 10+ callers including `api.py` (orphan), `data/intake.py` (broken entry point per MR14), and `pressure_test.py`. Any signature/behavior change ripples wide. | **High** |
| **MR82** | **`_source_map` provenance tagging is not enforced** | `_source_map._default: assumed` (line 8) is comment-only — no validator enforces that observed/assumed are the only valid values. Branches could insert invalid tags. | Low |
| **MR83** | **`appeals.stages` has hardcoded names L1/L2/L3 in this file but `infra/config.py:348-399` validates dynamically** | The simulator likely tolerates more or fewer stages, but the example uses L1/L2/L3. A branch that adds L4 (or removes L3) needs to update both the YAML and the simulator stage-iteration code. | Low |

## Dependencies

- **Incoming (who reads `actual.yaml` schema):** all 10+ callers of `load_and_validate` listed above; `cli.py` ingests the path from CLI; `core/simulator.py` ingests the validated dict.
- **Outgoing (what `actual.yaml` depends on):** `_source_map` references the provenance subsystem (`rcm_mc/provenance/*`); distribution specs depend on `core/distributions.py` `sample_dist`; payer canonicalization depends on `infra/config.py:80 canonical_payer_name`.

## Open questions / Unknowns

- **Q1 (this report).** What happens when `include_denials`/`include_underpayments` is absent? Does simulator default to True, False, or raise? Need to read `core/simulator.py` per-payer branches.
- **Q2.** Does `_validate_dist_spec` (line 119) accept any distributions besides `normal_trunc`, `beta`, `lognormal`? Need to read the spec validator.
- **Q3.** Is `_sum_to_one` (line 146) tolerant of small float drift, or does it reject `0.42 + 0.18 + 0.35 + 0.05 = 1.00`? Tolerance is `1e-6` per signature — need to verify `revenue_share` totals validate in practice.
- **Q4.** What does `_resolve_env_vars` (line 36) do? `${VAR}` and `${VAR:default}` substitution in YAML — need to enumerate which keys can use this.
- **Q5.** Is `benchmark.yaml`'s schema strictly identical to `actual.yaml`'s, or are there differences (e.g. fewer required keys)? `validate_config` is shared, suggesting identical, but a `is_benchmark` flag could exist.
- **Q6.** Does any ahead-of-main branch add a new top-level key (e.g. `regulatory:`, `medtech:`)? Pre-merge sweep needed.
- **Q7.** What happens if a YAML uses tab indentation or anchors/aliases? `yaml.safe_load` handles standard YAML; edge cases not tested.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0012** | **Read `infra/config.py:validate_config` end-to-end** (lines 200-435) and produce the canonical schema reference. | The schema is implicit; making it explicit reduces MR76. |
| **0013** | **Read `_validate_dist_spec`** (line 119) to enumerate accepted distributions. | Resolves Q2. |
| **0014** | **Read `core/simulator.py` per-payer branches** to determine default behavior of `include_denials`/`include_underpayments` when absent. | Resolves Q1 / MR80. |
| **0015** | **Cross-branch sweep for new keys in `configs/*.yaml`** — does any ahead-of-main branch add fields the trunk validator doesn't know about? | Resolves Q6. |
| **0016** | **`benchmark.yaml`** — same audit, lighter (mostly to confirm identical schema). | Closes Q5. |
| **0017** | **`scenario_presets/` and `templates/`** subdirs — what are these YAMLs? | Out-of-scope this iteration; necessary for full config-surface map. |

---

Report/Report-0011.md written. Next iteration should: read `infra/config.py:validate_config` end-to-end (lines 200-435) and produce the canonical machine-readable schema reference — directly resolves MR76 (no canonical schema) and answers Q1/Q2/Q3/Q4 in one pass.

