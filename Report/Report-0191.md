# Report 0191: Config Map — `configs/benchmark.yaml`

## Scope

`RCM_MC/configs/benchmark.yaml` (~150 lines) — 4th of 5 `configs/*.yaml` files mapped (only `initiatives_library.yaml` remains). Sister to Reports 0011 (actual.yaml), 0131 (playbook.yaml broken), 0161 (value_plan.yaml).

## Findings

### Header / data sources

Lines 1-7:
> "Sources: HFMA MAP Keys, AHA market scan, Kodiak benchmarking (HealthLeaders), AKASA/HFMA Cost-to-Collect"
> "Top-decile / best-practice targets. Currency: FY24."

**Industry-benchmark-sourced YAML.** Cross-link Report 0093 ml/README "HFMA MAP Keys" cited similarly.

### Schema (sample of top sections)

| Section | Keys | Note |
|---|---|---|
| `_source_map` | `_default: prior` | provenance-tagging convention |
| `hospital` | `name`, `annual_revenue` | identity |
| `analysis` | `n_sims: 30000`, `seed: 43`, `working_days: 250` | MC config |
| `economics` | `wacc_annual: 0.12` | WACC |
| `operations.denial_capacity` | `enabled`, `fte: 14`, `denials_per_fte_per_day: 13`, backlog dynamics | capacity model |
| `underpayments` | `enabled: true` | feature flag |
| `appeals.stages` | L1/L2/L3 cost + days distributions | appeal-cycle model |

### Distribution syntax

```yaml
cost: {dist: lognormal, mean: 15, sd: 5}
days: {dist: lognormal, mean: 12, sd: 4}
```

**`{dist: lognormal, mean: ..., sd: ...}` is the project's distribution-spec format.** Cross-link Report 0095 + 0129 `core/distributions.py` (`sample_dist`) — this is what `sample_dist` consumes.

### `_source_map` provenance

Line 9-10: `_default: prior` — every value is a "prior" (industry source, not real-cohort). Cross-link Report 0093 ml/README provenance flag pattern + Report 0174 cross-cut.

### Comparison to value_plan.yaml (Report 0161)

| | benchmark.yaml | value_plan.yaml |
|---|---|---|
| Lines | ~150 | 46 |
| Sections | 6+ | 6 |
| Has provenance markers | YES | NO |
| Distribution specs | extensive | none |
| FY pin | YES (FY24) | NO |
| Top-decile targets | YES | partial |

### Readers

`grep "benchmark\.yaml\|benchmark_yaml\|benchmark_path"`: not run this iteration. Per Report 0011: actual.yaml is consumed by simulator. **benchmark.yaml is the comparison target.** Likely consumed by `pe/breakdowns.simulate_compare_with_breakdowns` (per Report 0163 cli.py imports).

### Trust boundary

YAML on disk; partner-supplied or shipped default. Per Report 0162 MR873 medium: `--benchmark path/to.yaml` likely lacks path validation.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR955** | **`benchmark.yaml` parses cleanly** (per Report 0132 prior verification) | (clean) | (clean) |
| **MR956** | **`_source_map` provenance convention is informal** | Per Report 0174 provenance cross-cut: every value here tagged "prior". Cross-link to ProvenanceTag.SYNTHETIC_PRIORS. | (advisory) |
| **MR957** | **FY24 stamp** — implicit staleness signal | If FY25 data is published in 2026, stale benchmark is silent unless someone re-loads. | Medium |

## Dependencies

- **Incoming:** simulator, pe.breakdowns, CLI `--benchmark` flag.
- **Outgoing:** `core/distributions.sample_dist` for the dist spec.

## Open questions / Unknowns

- **Q1.** Per Report 0162 cross-link: does benchmark.yaml feed hash_inputs (Report 0148)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0192** | Data flow trace (in flight). |
| **0193** | Map `initiatives_library.yaml` — last unmapped configs/*.yaml. |

---

Report/Report-0191.md written.
