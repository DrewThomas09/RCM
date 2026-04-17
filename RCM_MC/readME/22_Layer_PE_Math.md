# Layer: PE — EBITDA Bridges + Deal Math (`rcm_mc/pe/`)

## TL;DR

This is where RCM metric improvements become dollar impact. Two
bridges live side-by-side: **v1** uses research-band-calibrated
coefficients (partner-defensible on a $400M NPR reference hospital,
applied uniformly), **v2** uses unit economics that read the Prompt 2
reimbursement profile so the same lever produces different value
under different payer mixes. Both run on every build; partners
compare outputs.

## What this layer owns

- Value-creation bridge (v1 and v2) from current RCM metrics → target
  RCM metrics → EBITDA + EV delta.
- MOIC + IRR + hold-period grid math.
- Covenant headroom calculation.
- Deal-level value plan (`value_creation.py`, `value_plan.py`).

## Files

### `rcm_ebitda_bridge.py` (~470 lines) — **v1 bridge**

**Purpose.** Research-band-calibrated 7-lever bridge. Every
coefficient is sized against published benchmarks:

| Research input | v1 output (on $400M NPR reference) |
|---|---|
| Denial rate 12 → 5 | $8-15M |
| A/R days 55 → 38 | $5-10M |
| Clean claim 85 → 96 | $1-3M |
| Net collection 92 → 97 | $10-15M |
| Cost to collect 5 → 3 | $4-8M |
| CMI +0.05 | $3-8M |

All 29 regression tests in `tests/test_rcm_ebitda_bridge.py` lock
the output to these bands.

**Key class.** `RCMEBITDABridge(financial_profile: FinancialProfile)`.

**`FinancialProfile` fields.** `gross_revenue`, `net_revenue`,
`total_operating_expenses`, `current_ebitda`, `cost_of_capital_pct`,
`total_claims_volume`, `cost_per_reworked_claim`, `fte_cost_follow_up`,
`claims_per_follow_up_fte`, `payer_mix`, `payer_denial_values`.

**Methods.**
- `compute_bridge(current_metrics, target_metrics, *, ev_multiples) ->
  EBITDABridgeResult` — per-lever impacts, waterfall, EV at 10x/12x/15x.
- `compute_sensitivity_tornado(current_metrics, improvement_scenarios)
  -> TornadoResult` — 1% / 5% / 10% / 20% improvement scans.
- `suggest_targets(current_metrics, comparables, benchmark_percentiles)
  -> TargetRecommendation` — conservative (P50) / moderate (P65) /
  aggressive (P75) tiers + achievability score.

**Seven lever functions** (all private):
- `_lever_denial_rate` — `(delta_pp/100) × net_revenue × 0.35` +
  rework_saved.
- `_lever_days_in_ar` — working capital + bad-debt avoidance.
- `_lever_net_collection_rate` — `delta_pp × net_revenue × 0.60`.
- `_lever_clean_claim_rate` — `delta_pp × claims × cost_per_rework / 100`.
- `_lever_cost_to_collect` — direct opex save.
- `_lever_first_pass_resolution_rate` — rework + 30% FTE savings.
- `_lever_case_mix_index` — `delta_points × medicare_NPR × 0.75/point`.

**Important quirks.**
- Metrics are on the **0-100 percentage-point scale** (`denial_rate
  = 12.0` means 12%, not 0.12).
- Returns `EBITDABridgeResult` from `analysis/packet.py` (defined
  there for JSON-roundtrip reasons).
- Includes `working_capital_released` separately from
  `total_ebitda_impact` so callers never double-count.

### `value_bridge_v2.py` (~680 lines) — **v2 bridge**

**Purpose.** Unit-economics bridge that:
1. Starts from `packet.revenue_realization.collectible_net_revenue`
   (not raw NPSR) so leakage already modeled by the realization path
   isn't double-counted.
2. Weights every lever by the hospital's payer mix × reimbursement
   method mix via Prompt 2's `ReimbursementProfile`.
3. Produces **four separate flavors** per lever instead of one
   EBITDA number.
4. Applies the exit multiple **only to recurring EBITDA**. One-time
   cash release reported separately, never inflates EV.

**Key dataclasses.**
- `BridgeAssumptions` — explicit knobs. `exit_multiple=10.0`,
  `cost_of_capital=0.08`, `collection_realization=0.65`,
  `denial_overturn_rate=0.55`, `rework_cost_per_claim=30.0`,
  `cost_per_follow_up_fte=55_000`, `claims_per_follow_up_fte=10_000`,
  `implementation_ramp=1.0`, `confidence_inference_penalty=0.15`,
  `claims_volume`, `net_revenue`.
- `WorkingCapitalEffect` — days_change, cash_release_one_time,
  financing_benefit_annual.
- `RevenueLeakageBreakdown` — stage, baseline_leakage,
  target_leakage, recovered, recovery_confidence.
- `LeverImpact` — `recurring_revenue_uplift`,
  `recurring_cost_savings`, `one_time_working_capital_release`,
  `ongoing_financing_benefit`, `recurring_ebitda_delta`,
  `revenue_leakage`, `working_capital`, `explanation`, `confidence`,
  `pathway_tags`, `provenance`.
- `EbitdaBridgeComponent` — waterfall row (label, value, kind).
- `ValueBridgeResult` — full output: lever_impacts,
  total_recurring_revenue_uplift, total_recurring_cost_savings,
  total_one_time_wc_release, total_financing_benefit,
  total_recurring_ebitda_delta, enterprise_value_delta,
  enterprise_value_from_recurring, cash_release_excluded_from_ev,
  bridge_components, rationale, status, reason.

**Core economic tables.**
- `_PAYER_REVENUE_LEVERAGE` — how much a recovered denied claim is
  worth relative to pure commercial:
  - Commercial 1.0, Medicare Advantage 0.80, Medicare FFS 0.75,
    Managed Government 0.55, Medicaid 0.50, Self-pay 0.40.
  - **This is the mechanism that makes commercial-heavy denial
    recovery worth more than Medicare-heavy recovery.**
- `_DEFAULT_AVOIDABLE_SHARE = 0.39` — `1 − 0.6×0.65` (appeal rate ×
  success rate).
- `_BASELINE_AR_DAYS = 30.0` — below this no additional financing
  benefit.
- `_LOWER_IS_BETTER` — frozenset of ~13 metrics for sign-of-delta
  determination.

**Lever dispatch.** `_LEVER_DISPATCH: dict[metric, fn]` — 18 metric
mappings. 7 denial-style metrics share `_lever_denial_rate`
internally; `case_mix_index` and `cmi` both point at `_lever_cmi`;
everything else has its own function.

**Per-lever economic routing.**
- `_lever_denial_rate` — revenue recovery via `_per_payer_revenue_recovery`
  + per-payer leverage table. Rework cost savings on first-pass
  denials only (not on `final_denial_rate`, where rework is already
  sunk).
- `_lever_days_in_ar` — one-time WC release = `days × (NPR/365) ×
  _timing_weight()`. Timing weight dampens under capitation (0.2)
  and cost-based (0.6); 1.0 for everything else.
- `_lever_net_collection_rate` — pure revenue with method-weighted
  sensitivity.
- `_lever_cost_to_collect` — pure cost save, `delta × net_revenue`.
- `_lever_cmi` — revenue uplift on DRG-exposed share only (DRG
  weight + 0.3×APC weight).
- `_lever_bad_debt` — cost save amplified by self-pay + Medicaid
  exposure.

**Public entry points.**
- `compute_value_bridge(current_metrics, target_metrics,
  reimbursement_profile, assumptions, *, realization, current_ebitda)
  -> ValueBridgeResult`. Fallback to an all-commercial-FFS profile
  when none provided (low confidence).
- `explain_lever_value(metric, current, target, profile, assumptions,
  *, realization) -> str` — per-lever narrative with pathway
  dominance, profile tilt, and weakness notes.

**25 regression tests** (`tests/test_value_bridge_v2.py`) lock the
10 spec invariants: commercial > Medicare denial value, DRG-heavy
CMI > commercial CMI, self-pay amplifies bad-debt, capitation dampens
denials, days_in_ar → WC dominant, cost_to_collect → pure cost,
net_collection_rate → pure revenue, EV scales with recurring only,
implementation_ramp scales cleanly, provenance on every lever.

### `lever_dependency.py` (~260 lines) — **cross-lever adjustment**

**Purpose.** Fix the double-count problem in the v2 bridge. Many
levers are causally linked through the ontology (e.g.,
`eligibility_denial_rate` is a parent of `denial_rate`); when both
fire, the naive sum over-states EBITDA lift. This module walks the
lever set in topological order and reduces each lever's revenue-
recovery component by the fraction already captured by its parents.

**Key constants.**
- `_MAGNITUDE_OVERLAP = {"strong": 0.60, "moderate": 0.35, "weak": 0.15}`
  — maps the ontology's `MechanismEdge.magnitude_hint` strings to
  numeric overlap fractions.
- `_MAX_TOTAL_OVERLAP = 0.75` — safety cap so a heavily-connected
  child never gets zeroed out entirely.

**Key dataclass.** `DependencyAuditRow` — one row per lever recording:
`lever`, `raw_impact`, `adjustment_pct`, `adjusted_impact`,
`upstream_levers` (list of parent keys that caused the adjustment),
`explanation`.

**Public functions.**
- `topological_lever_order(metric_keys, graph=None) -> list[str]` —
  Kahn's algorithm on the ontology's `CausalGraph`. Unknown keys go
  at the end. Cycles (shouldn't happen in the shipped ontology) fall
  back to input-preserving order so nothing is silently lost.
- `apply_dependency_adjustment(lever_key, lever_impact,
  already_captured, graph=None) -> (adjusted_impact, audit_row)` —
  unit-level API. Reads `already_captured` (dict of metric_key →
  LeverImpact already processed) and adjusts the child lever
  accordingly.
- `walk_dependency(lever_impacts, graph=None) -> (adjusted_impacts,
  audit_rows)` — top-level entry point. Walks all levers in
  topological order, returns adjusted impacts (caller's original
  order preserved) + parallel audit rows.

**Design rules.**
- **Only `recurring_revenue_uplift` is reduced.** Cost savings, WC
  release, and financing benefit operate through independent
  pathways.
- **`recurring_ebitda_delta` is recomputed** consistently after the
  revenue adjustment.
- **Adjustments only shrink, never inflate.** Monotonicity verified
  by tests.
- **Audit rows sum to explain the full delta** between raw and
  adjusted totals — partners can reconcile the entire trail with
  arithmetic.
- **v1 bridge untouched.** Dependency walk is v2-only. The v1 bridge
  already over-indexes on research-band calibration; adding
  dependency math on top would obscure the calibration signal.

**Where it plugs in.** `value_bridge_v2.compute_value_bridge()` calls
`walk_dependency()` immediately after computing raw impacts, before
aggregating totals or computing EV. `ValueBridgeResult` now carries
both adjusted totals (the authoritative numbers) and raw totals
(for "naive vs adjusted" renderers).

**Example.** On a typical Medicare-heavy hospital with both
`eligibility_denial_rate` (1.5→0.8) and `denial_rate` (12→5) fired,
the raw total shrinks by ~29% because `denial_rate`'s revenue
component is reduced by the ~35% moderate-edge overlap with its
eligibility parent.

### `ramp_curves.py` (~220 lines) — **per-lever implementation ramp**

**Purpose.** Replace the single-scalar `implementation_ramp` with
per-lever-family S-curves. Real PE holds see denial management ramp
in 3-6 months, CDI/coding in 6-12 months, payer renegotiation in
6-18 months. A single scalar overstates Year-1 and understates
Year-3; the curves make the hold-period grid honest.

**Key dataclass.** `RampCurve(lever_family, months_to_25_pct,
months_to_75_pct, months_to_full)`. Frozen, validated — the
constructor raises if the quartile months aren't strictly ordered.
Logistic interpolation is chosen so the curve hits ~25% at
`months_to_25_pct`, ~50% at the midpoint, ~75% at `months_to_75_pct`,
then asymptotes to 1.0 at `months_to_full`. Normalized so `f(0) = 0`
exactly.

**Default curves (`DEFAULT_RAMP_CURVES`).**

| Family | 25% / 75% / 100% month | Notes |
|---|---|---|
| `denial_management` | 3 / 6 / 12 | Well-understood tooling + workflow. |
| `ar_collections` | 2 / 4 / 9 | Fast — mostly automation tuning. |
| `cdi_coding` | 6 / 12 / 18 | Slower — clinician behavior change. |
| `payer_renegotiation` | 6 / 12 / 24 | Slowest — counterparty-driven. |
| `cost_optimization` | 3 / 6 / 12 | Budget-cycle dependent. |
| `default` | 3 / 6 / 12 | Fallback for unmapped metrics. |

**Metric → family map (`METRIC_TO_FAMILY`).** Expands the v1 MC's
family taxonomy to cover every v2 bridge lever: denial variants (7
keys) → `denial_management`; coding / CMI → `cdi_coding`; AR / DNFB
/ clean-claim / first-pass → `ar_collections`; net-collection-rate
→ `payer_renegotiation`; cost-to-collect / bad-debt →
`cost_optimization`.

**Public functions.**
- `ramp_factor(curve, month) -> float` — S-curve multiplier,
  clamped to `[0, 1]`, anchored at 0 and 1 at the endpoints.
- `annual_ramp_factors(curve, hold_years) -> list[float]` —
  monthly-average over each 12-month window. Used by year-by-year
  renderers.
- `apply_ramp_to_lever(lever_impact, factor) -> LeverImpact` —
  scales `recurring_revenue_uplift`, `recurring_cost_savings`,
  `ongoing_financing_benefit` by `factor`; leaves
  `one_time_working_capital_release` alone (WC lands at
  implementation, not at steady state). Recomputes
  `recurring_ebitda_delta` from the three scaled flows.
- `curve_for_metric(metric_key, curves=None) -> RampCurve` —
  resolve-with-fallback to `default`.
- `resolve_ramp_curves(curves)` — normalizer that accepts either
  a dict of `RampCurve` or dict-of-dicts (JSON shape), falling
  back to the defaults.

**Wired into `compute_value_bridge`.** After the cross-lever
dependency walk and before totals aggregation, each lever is scaled
by `ramp_factor(curve, assumptions.evaluation_month)`. At the
default `evaluation_month = 36` every default curve returns 1.0, so
existing callers see *identical output* (identity lock by test).
`ValueBridgeResult` gains `ramp_applied: bool` and
`per_lever_ramp_factors: dict[str, float]` for audit.

**Wired into `V2MonteCarloSimulator`.** `configure(hold_months=...)`
threads the evaluation month through the per-sim `BridgeAssumptions`.
Drop to 6 or 12 for a Year-1 Monte Carlo; leave at 36 for the full
run-rate distribution.

**Relationship to `implementation_ramp`.** Orthogonal. Ramp curves
handle *timing* (when does each lever land); `implementation_ramp`
is a *confidence* scalar applied in each lever function (partner-
driven haircut on the plan). Both multiply.

### Analyst overrides (Prompt 18)

**Where.** `rcm_mc/analysis/deal_overrides.py` (lives under the
analysis layer because it's a packet-build concern, but the keyspace
is PE-layer-shaped). Full reference in [README_LAYER_INFRA.md](README_LAYER_INFRA.md)
under *Analyst overrides*.

**What's overridable from the PE side.**

- `bridge.exit_multiple`, `bridge.cost_of_capital`,
  `bridge.collection_realization`, `bridge.denial_overturn_rate`,
  `bridge.rework_cost_per_claim`, `bridge.implementation_ramp`,
  `bridge.evaluation_month`, `bridge.claims_volume`,
  `bridge.net_revenue`, `bridge.confidence_inference_penalty`,
  `bridge.cost_per_follow_up_fte`, `bridge.claims_per_follow_up_fte`.
- `ramp.<family>.<field>` — per-family S-curve knobs
  (`months_to_25_pct` / `months_to_75_pct` / `months_to_full`).
- `metric_target.<metric>` — swap a bridge lever's target mid-flight.

**CLI.** `rcm-mc pe override {set,list,clear}` — see the infra README
for flags.

**Impact on cache.** Adding an override changes `hash_inputs`, so
the next `get_or_build_packet` rebuilds rather than serving the stale
row. The new packet's `analyst_overrides` field carries the flat
`{key: value}` map that was active at build time.

### `pe_math.py` (~900 lines)

**Purpose.** PE-standard deal math — bridge, MOIC, IRR, covenant,
hold-period sensitivity grid.

**Public dataclasses.**
- `BridgeResult` — organic / RCM / multiple-expansion split that
  reconciles to exit EV exactly.
- `ReturnsResult` — MOIC + annualized IRR + total distributions.
- `CovenantCheck` — headroom turns, breach flag, detail.

**Public functions.**
- `value_creation_bridge(entry_ebitda, uplift, entry_multiple,
  exit_multiple, hold_years, organic_growth_pct=0.0) -> BridgeResult`.
  Reconciles: `entry_ev + organic + rcm + multiple_exp == exit_ev`.
- `compute_returns(entry_equity, exit_proceeds, hold_years, *,
  interim_cash_flows=None) -> ReturnsResult`. Bisection IRR on
  non-integer hold years.
- `hold_period_grid(*, entry_ebitda, uplift_by_year, entry_multiple,
  exit_multiples, hold_years_list, entry_equity, debt_at_entry, ...)
  -> list[dict]`. (Years × exit_multiples) sensitivity table.
- `hold_period_grid_with_mc(*, mc_ebitda_summary, ...) -> list[dict]`
  — Prompt 5 addition: returns P10 / P50 / P90 MOIC + IRR per cell
  from a `DistributionSummary`.
- `returns_from_rcm_bridge(bridge_result, *, entry_multiple,
  exit_multiple, hold_years, ...)` — seam between the v1 bridge's
  `EBITDABridgeResult` and the deal-math layer's `BridgeResult`.
- `covenant_check(...)` — leverage turns vs. covenant threshold.
- `format_bridge/format_returns/format_covenant/format_hold_grid` —
  terminal-friendly renderers.
- `bridge_to_records(b)` — JSON-safe bridge rows.

### `value_creation.py` (~320 lines)

**Purpose.** Top-level "run a value-creation plan" entry point used
by the CLI and legacy simulator path. Wraps the simulator with
plan-applied config.

**Public function.** `run_value_creation(actual_cfg, benchmark_cfg,
plan, *, n_sims, seed, align_profile, ev_multiple) -> dict` — returns
baseline/target simulation results + uplift calcs.

### `value_plan.py` (~150 lines)

**Purpose.** Load + validate the `value_plan.yaml` format used by the
Phase-2 CLI.

### `attribution.py` (~420 lines)

**Purpose.** OAT-style (one-at-a-time) driver-attribution analysis.
Decomposes which simulation driver explains how much of the total
drag. Used by the Phase-2 CLI bundle renderer.

### `hold_tracking.py` (~560 lines)

**Purpose.** Quarterly actuals tracking + variance report for the
portfolio-operations pages. Stores `hold_actuals` per deal × quarter
× KPI.

### `remark.py` (~290 lines)

**Purpose.** Re-underwrite a deal from the latest quarter of actuals.
Produces a new hold-stage snapshot stamped "Re-mark as of YYYYQn."

### `pe_integration.py` (~310 lines)

**Purpose.** Glue between the Phase-2 simulator and the PE-math
layer. Older entry point; `run_value_creation` is the newer surface.

### `breakdowns.py` (~260 lines)

**Purpose.** Payer × stage × driver breakdown computation for the
sensitivity tornado.

### `__init__.py`

Empty — callers import from explicit submodules.

## How the two bridges coexist

```
                     ┌────────────────────────────────┐
                     │ packet_builder.build_analysis   │
                     │ _packet()                       │
                     └──────────────┬─────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │ _build_bridge    │  │ _build_value_    │  │ reimbursement    │
  │                  │  │ bridge_v2        │  │ + realization    │
  │ RCMEBITDABridge  │  │ compute_value_   │  │ (Prompt 2)        │
  │                  │  │ bridge           │  │                   │
  │ research-band    │  │ unit-economics   │  │                   │
  │ coefficients     │  │ + profile-aware  │  │                   │
  │                  │  │ per-lever flavors│  │                   │
  └────────┬─────────┘  └────────┬─────────┘  └──────────────────┘
           │                     │
           ▼                     ▼
  ┌─────────────────┐  ┌──────────────────┐
  │ packet.ebitda_  │  │ packet.value_    │
  │ bridge          │  │ bridge_result    │
  │                 │  │ + leverage_table │
  │                 │  │ + recurring_vs_  │
  │                 │  │   one_time       │
  │                 │  │ + ev_summary     │
  └─────────────────┘  └──────────────────┘
```

**Which should partners trust?**

- **v1** is calibrated against the research table. Use it for the
  "what does the industry say?" benchmark view.
- **v2** is profile-aware. Use it for "what does this specific
  hospital's reimbursement structure say?"

They'll agree on a $400M NPR Medicare-heavy hospital because that's
what v1 was calibrated against. They'll differ on commercial-heavy,
capitation-heavy, and small-outpatient hospitals — that's the point.

Long-term plan is to deprecate v1 once partners validate v2 on
real deals. The research-band tests in v1 stay as a calibration
floor.

## Current state

### Strong points
- **Two independent implementations** catching discrepancies on each
  other. Same fixture hits both; divergences surface as real
  economic differences (not bugs).
- **Recurring vs one-time hygiene.** EV multiple never touches cash
  release. Partners never see inflated EV on timing-only wins.
- **Exit multiple is an explicit input** — no hidden constants.
- 54 bridge tests (29 v1 + 25 v2) lock the economic invariants.

### Weak points (from Prompt 3 summary)
- **Per-payer leverage is static.** Real commercial contracts vary
  ±30% by market. No per-hospital override yet.
- **Appeal-recovery rate is a single scalar** (`_DEFAULT_AVOIDABLE_SHARE
  = 0.39`). Real rates vary by payer × category (MA medical-necessity
  ~35%; commercial eligibility ~85%).
- ~~**No cross-lever dependency modeling.**~~ *Resolved in Prompt 15
  via `lever_dependency.py` — parents walked before children, child
  revenue components reduced by magnitude-hint-derived overlap
  fractions. See `DependencyAuditRow` for the audit trail.*
- **Implementation ramp is a single scalar.** Real ramps differ
  per lever (denial mgmt 3-6mo, CDI 6-12mo, payer renegotiation
  6-18mo).
- **Bad-debt amplifier is linear.** Real dynamics are step-wise
  around 501(r) charity-care triggers.
