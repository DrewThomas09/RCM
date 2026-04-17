# Deal Analysis Packet

The `DealAnalysisPacket` is the spine of the platform. Every UI page,
every API endpoint, and every export renders from a single packet
instance — nothing renders independently. If the workbench and the
diligence memo disagree on a number, that's a renderer bug, not a
data bug.

This document is the canonical reference for the packet schema. Keep
it in sync with [`rcm_mc/analysis/packet.py`](../rcm_mc/analysis/packet.py)
when the dataclass changes.

---

## Lifecycle

```
PortfolioStore (SQLite)
        │
        ▼
packet_builder.build_analysis_packet()   ← 12-step orchestrator
        │
        ▼
DealAnalysisPacket                       ← frozen dataclass
        │
        ├──► analysis_runs (cache)       ← hashed + JSON-compressed
        ├──► /analysis/<deal_id>         ← workbench HTML
        ├──► /api/analysis/<deal_id>     ← JSON API
        └──► /api/analysis/<deal_id>/export?format=X
```

## Top-level fields

| field | type | notes |
|---|---|---|
| `deal_id` | `str` | Matches `deals.deal_id` in SQLite |
| `deal_name` | `str` | Human-readable name; falls back to deal_id |
| `run_id` | `str` | `YYYYMMDDTHHMMSSZ-<uuid6>`; unique per build |
| `generated_at` | `datetime` | UTC timestamp of build |
| `model_version` | `str` | `PACKET_SCHEMA_VERSION` at build time |
| `scenario_id` | `Optional[str]` | Optional overlay applied during build |
| `as_of` | `Optional[date]` | Report as-of date (for staleness checks) |

## Section 1 — `profile: HospitalProfile`

| field | type |
|---|---|
| `bed_count` | `Optional[int]` |
| `region` | `Optional[str]` |
| `state` | `Optional[str]` |
| `payer_mix` | `dict[str, float]` (fractions, sum ≈ 1.0) |
| `teaching_status` | `Optional[str]` |
| `urban_rural` | `Optional[str]` |
| `system_affiliation` | `Optional[str]` |
| `cms_provider_id` | `Optional[str]` (a.k.a. CCN) |
| `ein` | `Optional[str]` |
| `npi` | `Optional[str]` |
| `name` | `Optional[str]` |

## Section 2 — `observed_metrics: dict[str, ObservedMetric]`

Key is a registry metric key (e.g. `denial_rate`). Every rate metric is
on the **0-100 percentage-point scale** — `denial_rate = 12.0` means 12%.

| field | type |
|---|---|
| `value` | `float` |
| `source` | `str` — `USER_INPUT` / `HCRIS` / `IRS990` / `CARE_COMPARE` / `UTILIZATION` |
| `source_detail` | `str` |
| `as_of_date` | `Optional[date]` |
| `quality_flags` | `list[str]` |

## Section 3 — `completeness: CompletenessAssessment`

Produced by `rcm_mc.analysis.completeness.assess_completeness()`.

| field | type | notes |
|---|---|---|
| `coverage_pct` | `float` | 0-1 |
| `total_metrics` | `int` | registry size |
| `observed_count` | `int` | |
| `missing_fields` | `list[MissingField]` | sorted by EBITDA sensitivity |
| `stale_fields` | `list[StaleField]` | observed_date older than threshold |
| `conflicting_fields` | `list[ConflictField]` | multiple sources disagree |
| `quality_flags` | `list[QualityFlag]` | `OUT_OF_RANGE`, `STALE`, `MISSING_BREAKDOWN`, `BENCHMARK_OUTLIER`, `SUSPICIOUS_CHANGE`, `PAYER_MIX_INCOMPLETE` |
| `missing_ranked_by_sensitivity` | `list[str]` | flat list, most-impactful first |
| `grade` | `str` | A/B/C/D (A = ≥90% coverage AND no critical flags) |
| `status`, `reason` | `SectionStatus` | |

## Section 4 — `comparables: ComparableSet`

| field | type |
|---|---|
| `peers` | `list[ComparableHospital]` (id, similarity_score, similarity_components, fields) |
| `features_used` | `list[str]` |
| `weights` | `dict[str, float]` |
| `robustness_check` | `dict[str, Any]` |

## Section 5 — `predicted_metrics: dict[str, PredictedMetric]`

Only contains metrics NOT in `observed_metrics`. Ridge → weighted median
→ benchmark fallback per the conformal-calibrated predictor
([`rcm_mc/ml/ridge_predictor.py`](../rcm_mc/ml/ridge_predictor.py)).

| field | type |
|---|---|
| `value` | `float` |
| `ci_low`, `ci_high` | `float` — conformal / bootstrap / IQR band |
| `method` | `"ridge_regression"` / `"weighted_median"` / `"benchmark_fallback"` |
| `r_squared` | `float` (0 for non-ridge) |
| `n_comparables_used` | `int` |
| `feature_importances` | `dict[str, float]` (sums to 1.0 for ridge) |
| `provenance_chain` | `list[str]` — upstream observed metric keys |
| `coverage_target` | `float` (typically 0.90) |
| `reliability_grade` | `str` — A/B/C/D |

## Section 6 — `rcm_profile: dict[str, ProfileMetric]`

Observed merged with predicted. One row per metric regardless of source.

| field | type |
|---|---|
| `value` | `float` |
| `source` | `MetricSource` — `OBSERVED` / `PREDICTED` / `BENCHMARK` / `UNKNOWN` |
| `benchmark_percentile` | `Optional[float]` |
| `trend` | `Optional[str]` |
| `quality` | `"high"` / `"medium"` / `"low"` |
| `ci_low`, `ci_high` | CI from the predictor when source=PREDICTED |

## Section 7 — `ebitda_bridge: EBITDABridgeResult`

Produced by `RCMEBITDABridge.compute_bridge()` against the moderate-tier
targets. Every coefficient is calibrated to the research band
([BENCHMARK_SOURCES.md](./BENCHMARK_SOURCES.md)).

| field | type |
|---|---|
| `current_ebitda`, `target_ebitda`, `total_ebitda_impact` | `float` |
| `new_ebitda_margin` | `float` |
| `ebitda_delta_pct`, `margin_improvement_bps` | |
| `per_metric_impacts` | `list[MetricImpact]` — one per lever |
| `waterfall_data` | `list[(label, value)]` |
| `sensitivity_tornado` | `list[dict]` |
| `working_capital_released` | `float` — one-time cash, NOT EBITDA |
| `ev_impact_at_multiple` | `dict[str, float]` — e.g. `{"10x": 130_000_000}` |

Each `MetricImpact` carries `current_value`, `target_value`,
`revenue_impact`, `cost_impact`, `ebitda_impact`, `margin_impact_bps`,
`working_capital_impact`, and `upstream_metrics: list[str]` for the
provenance graph.

## Section 8 — `simulation: Optional[SimulationSummary]`

From the two-source Monte Carlo ([`rcm_mc/mc/ebitda_mc.py`](../rcm_mc/mc/ebitda_mc.py)).
Combines:
- **Prediction uncertainty** (conformal CI from the ridge predictor)
- **Execution uncertainty** (beta distribution per lever family)

| field | type |
|---|---|
| `n_sims`, `seed` | `int` |
| `ebitda_uplift`, `moic`, `irr` | `PercentileSet(p10/p25/p50/p75/p90)` |
| `probability_of_covenant_breach` | `float` 0-1 |
| `variance_contribution_by_metric` | `dict[str, float]` (sums to 1.0) |
| `convergence_check` | `dict` from `mc.convergence.check_convergence` |

## Section 9 — `risk_flags: list[RiskFlag]`

Six categories: `OPERATIONAL`, `REGULATORY`, `PAYER`, `CODING`,
`DATA_QUALITY`, `FINANCIAL`. Severity ladder:
`CRITICAL` > `HIGH` > `MEDIUM` > `LOW`.

| field | type |
|---|---|
| `category` | `str` |
| `severity` | `RiskSeverity` |
| `title`, `detail` | `str` — headline + narrative |
| `trigger_metrics` | `list[str]` |
| `ebitda_at_risk` | `Optional[float]` — populated when the bridge sized it |

See [`rcm_mc/analysis/risk_flags.py`](../rcm_mc/analysis/risk_flags.py)
for the detection rules (e.g., `denial_rate > 10%` → CRITICAL,
Medicaid > 25% → OBBBA flag).

## Section 10 — `provenance: ProvenanceSnapshot`

> *Back-compat: old name* `ProvenanceGraph` *still works via a
> module-level alias.*

Flattened snapshot of the rich graph built by
`rcm_mc.provenance.graph.build_rich_graph()`. Every metric value
appears as a `DataNode`:

| field | type |
|---|---|
| `metric` | `str` — id like `observed:denial_rate`, `bridge:total`, `mc:ebitda_p50` |
| `value` | `float` |
| `source` | `str` — where it came from |
| `source_detail` | `str` |
| `confidence` | `float` 0-1 |
| `upstream` | `list[str]` — parent metric ids |

`ProvenanceSnapshot` has `nodes: dict[str, DataNode]`. The richer DAG
(typed edges, NodeType enum, cycle detection) is rebuilt on demand at
`/api/analysis/<deal_id>/provenance` via `build_rich_graph(packet)`.

## Section 11 — `diligence_questions: list[DiligenceQuestion]`

| field | type |
|---|---|
| `question` | `str` — always quotes specific trigger values |
| `category` | same taxonomy as risk flags |
| `priority` | `P0` / `P1` / `P2` |
| `trigger` | `str` — e.g. `"denial_rate=14.5%"` |
| `context` | `str` — why it matters for valuation |

Generated by [`rcm_mc/analysis/diligence_questions.py`](../rcm_mc/analysis/diligence_questions.py).
P0 = blocker for IC; P1 = confirm before signing; P2 = nice-to-have.

## Section 12 — `exports: dict[str, str]`

`{format: filepath_or_marker}`. Default values are the sentinel
`"render_on_demand"` — actual files land in the `generated_exports`
audit table when `/api/analysis/<deal_id>/export?format=X` is called.

---

## Reproducibility contract

Same inputs → same packet content (run_id and generated_at differ).
Input hash: `hash_inputs(deal_id, observed_metrics, scenario_id, as_of, profile)`
with `sort_keys=True` so dict ordering is stable. See
[`tests/test_packet_reproducibility.py`](../tests/test_packet_reproducibility.py).

## Caching

`analysis_runs` table stores zlib-compressed JSON blobs keyed on
`(deal_id, hash_inputs)`. `get_or_build_packet()` hits this cache
unless `force_rebuild=True`. Hash changes when observed metrics,
scenario overlay, as-of date, or profile change.

## Export audit

Every export writes to `generated_exports` with:
`deal_id`, `analysis_run_id`, `format`, `filepath`, `generated_at`,
`generated_by`, `file_size_bytes`, `packet_hash`. The footer of every
rendered format also prints run_id + input hash so partners can trace
a printed memo back to the exact analysis run that produced it.

## When to update this doc

- Adding a new section → add an entry above + a registry entry + a
  builder step.
- Changing a field's type or default → update the table row and the
  contract test in [`tests/test_analysis_packet.py`](../tests/test_analysis_packet.py).
- Bumping `PACKET_SCHEMA_VERSION` → note the change here with a date.
