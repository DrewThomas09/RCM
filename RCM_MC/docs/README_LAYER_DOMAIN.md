# Layer: Domain — Economic Ontology + Reimbursement Engine

## TL;DR

Two tightly-linked modules encode the economic substrate every
downstream model sits on. `domain/econ_ontology.py` is the metric
dictionary — what every RCM metric *is* and how it connects
causally. `finance/reimbursement_engine.py` is the payer-structure
engine — how hospital revenue is actually generated, delayed, or lost
under different reimbursement methods.

Together they make the platform able to answer *"why does the same
operational improvement have different value at different hospitals?"*
instead of applying uniform multipliers.

## What this layer owns

- The canonical metric ontology — 26 entries covering every RCM metric
  the system touches.
- The reimbursement taxonomy — 8 archetypes (FFS, DRG, APC, per-diem,
  capitation, case-rate, value-based, cost-based).
- The payer-class model — 6 payer classes, each with default method
  distribution, contractual discount, and collection difficulty.
- Per-metric sensitivity tables routing economic impact through
  revenue / cost / working-capital pathways.

Never touches SQLite. Pure data-and-functions.

## Files

### `rcm_mc/domain/econ_ontology.py` (~550 lines)

**Purpose.** Explicit mapping from metric_key → economic meaning.

**Key enums.**
- `Domain` — 9 top-level domains: `COVERAGE_PAYER_MIX`,
  `REIMBURSEMENT_METHODOLOGY`, `FRONT_END_ACCESS`,
  `MIDDLE_CYCLE_CODING`, `BACK_END_CLAIMS`, `WORKING_CAPITAL`,
  `PROFITABILITY`, `POLICY_REGULATORY`, `MARKET_STRUCTURE`.
- `Directionality` — `HIGHER_IS_BETTER` / `LOWER_IS_BETTER` / `DEPENDS`.
- `FinancialPathway` — `REVENUE` / `COST` / `WORKING_CAPITAL` /
  `RISK` / `MIXED`.
- `ConfidenceClass` — `OBSERVED` / `INFERRED` / `MODELED` /
  `BENCHMARKED` / `DERIVED`.
- `ReimbursementType` — simpler 5-entry version (used by per-metric
  sensitivity; distinct from `finance.ReimbursementMethod`).

**Key dataclasses.**
- `MetricDefinition` — the full record for one metric. Fields:
  `metric_key, display_name, domain, subdomain, economic_mechanism,
  directionality, financial_pathway, confidence_class,
  reimbursement_sensitivity, causal_parents, causal_children,
  mechanism_tags, unit`.
- `MechanismEdge` — one causal link: `(parent, child,
  effect_direction, magnitude_hint, mechanism)`.
- `CausalGraph` — `nodes: dict[key, MetricDefinition]` +
  `edges: list[MechanismEdge]`. Methods: `parents_of(key)`,
  `children_of(key)`, `edges_into(key)`, `edges_out_of(key)`.
- `MetricReimbursementSensitivity` (per-metric sensitivity across
  regimes, 5 weights). Formerly named `ReimbursementProfile` — that
  name is retained as a back-compat alias but new code should use
  `MetricReimbursementSensitivity` so it doesn't collide with
  `finance.ReimbursementProfile` (hospital-level exposure, different
  concept).

**Public functions.**
- `classify_metric(metric_key) -> MetricDefinition` — raises KeyError
  for unknown metrics (loud failure, not silent orphan).
- `causal_graph() -> CausalGraph` — assembles the full DAG (26 nodes,
  43 edges).
- `explain_causal_path(metric_key) -> str` — 200-word plain-English
  narrative used by the workbench tooltip.

**How coefficients were sized.** Every entry was hand-written from
HFMA MAP Keys, AHRQ HCUP docs, CMS IPPS/OPPS rulemaking context,
and KFF coverage research. No ML learned the ontology — it's
curated.

**Example: `denial_rate` entry.**
```python
"denial_rate": _m(
    "denial_rate", "Initial denial rate",
    domain=Domain.BACK_END_CLAIMS, subdomain="denials.aggregate",
    mechanism="Share of submitted claims initially denied ...",
    direction=Directionality.LOWER_IS_BETTER,
    pathway=FinancialPathway.MIXED,
    reimb=_r(ffs=1.0, drg=1.0, cap=0.2, bundled=0.5, vbp=0.7),
    parents=["eligibility_denial_rate", "auth_denial_rate",
             "coding_denial_rate", "medical_necessity_denial_rate",
             "timely_filing_denial_rate", "clean_claim_rate"],
    children=["final_denial_rate", "days_in_ar",
              "net_collection_rate", "cost_to_collect"],
    tags=["rework_cost", "cash_timing", "bad_debt_driver"],
),
```

Reads as: "Denial rate lives in the back-end claims domain. It's a
composite driven by five specific denial types + clean-claim rate.
Its downstream effects are on final write-offs, AR timing, collection
rate, and operational cost. Economically it matters most under FFS
and DRG (weight 1.0); under capitation it's near-irrelevant
(weight 0.2)."

### `rcm_mc/finance/reimbursement_engine.py` (~690 lines)

**Purpose.** Model how a hospital's payer mix × reimbursement-method
mix determines its economic exposure to any given RCM lever.

**Key enums.**
- `ReimbursementMethod` — 8 archetypes:
  - `FEE_FOR_SERVICE` — claim-by-claim
  - `DRG_PROSPECTIVE` — Medicare IPPS, inpatient DRG
  - `OUTPATIENT_APC` — Medicare OPPS, APC-based
  - `PER_DIEM` — daily rate × LOS
  - `CAPITATION` — PMPM
  - `CASE_RATE_BUNDLE` — episode-based flat payment
  - `VALUE_BASED` — quality-linked
  - `COST_BASED` — CMS cost-report settlement (Critical Access)
- `PayerClass` — 6 classes: `COMMERCIAL`, `MEDICARE_FFS`,
  `MEDICARE_ADVANTAGE`, `MEDICAID`, `SELF_PAY`, `MANAGED_GOVERNMENT`.
- `ProvenanceTag` — 5 kinds: `OBSERVED` / `INFERRED_FROM_PROFILE` /
  `BENCHMARK_DEFAULT` / `ANALYST_OVERRIDE` / `CALCULATED`.

**Key dataclasses.**
- `MethodSensitivity` — per-method table entry. 13 fields encoding
  sensitivity to coding/CDI, auth-denials, eligibility, medical-
  necessity, timely-filing, utilization volume, site-of-care
  migration, LOS, cash-timing-days (DSO), clawback likelihood, and
  `gain_pathway` (revenue / cost_avoidance / working_capital / mixed).
  Values 0.0-1.0 per field.
- `PayerClassProfile` — one payer's slice of revenue. Fields:
  `payer_class, revenue_share, method_distribution, collection_difficulty,
  avg_contractual_discount, provenance`.
- `ReimbursementProfile` — the hospital-level aggregate. Has
  `payer_classes: dict`, `method_weights: dict[method, float]`
  (revenue-weighted aggregate), `inpatient_outpatient_mix`,
  `provenance`. Method: `dominant_method()`.
- `RevenueRealizationPath` — 9-stage decomposition from gross charges
  to final realized cash (contractual, front-end, coding, initial
  denial, final denial, timing drag, bad debt, realized).
- `RevenueAtRiskBreakdown` — one leakage row with `stage`,
  `dollar_amount`, `share_of_gross`, `provenance_tag`.
- `ContractSensitivity` — per-(method, payer) explanation row.

**Tables.**
- `METHOD_SENSITIVITY_TABLE: dict[ReimbursementMethod, MethodSensitivity]`
  — 8 hand-calibrated entries. The domain truth for how each method
  behaves.
- `DEFAULT_PAYER_METHOD_DISTRIBUTION: dict[PayerClass, dict[Method,
  float]]` — per-payer default method mix (sums to 1.0). Every
  inference is tagged `inferred_from_profile` in provenance so the
  UI shows "assumed" vs "observed."

**Public functions.**
- `build_reimbursement_profile(hospital_profile, payer_mix,
  optional_contract_inputs=None) -> ReimbursementProfile` —
  inference + analyst overrides. Heuristic: bed_count<25 swings
  Medicare FFS toward COST_BASED; bed_count<100 leans Medicare
  toward OUTPATIENT_APC.
- `estimate_metric_revenue_sensitivity(metric_key, profile) ->
  dict[revenue|cost|working_capital_sensitivity + confidence +
  explanation]`.
- `compute_revenue_realization_path(current_metrics, profile, *,
  gross_revenue=None, net_revenue=None) -> RevenueRealizationPath` —
  sequential leakage subtraction from gross to realized cash.
- `explain_reimbursement_logic(metric_key, profile) -> str` — plain-
  English tilt narrative (commercial-heavy / Medicare-heavy / self-
  pay-heavy); notes inferred assumptions.

## How it fits the system

```
        ┌──────────────────────────────────────────────┐
        │ rcm_mc/domain/econ_ontology.py                │
        │  METRIC_ONTOLOGY  (26 MetricDefinitions)      │
        │  CausalGraph                                  │
        └──────────────────┬──────────────────────────┘
                           │ consumed by
    ┌──────────────────────┼──────────────────────────────┐
    │                      │                              │
    ▼                      ▼                              ▼
┌───────────────┐  ┌────────────────────────┐  ┌──────────────────┐
│ completeness   │  │ packet_builder         │  │ risk_flags       │
│ registry       │  │ (_attach_ontology)     │  │ diligence_qs     │
└───────────────┘  └────────────────────────┘  └──────────────────┘

        ┌──────────────────────────────────────────────┐
        │ rcm_mc/finance/reimbursement_engine.py        │
        │  METHOD_SENSITIVITY_TABLE (8 methods)          │
        │  DEFAULT_PAYER_METHOD_DISTRIBUTION (6 payers) │
        │  ReimbursementProfile / RevenueRealizationPath│
        └──────────────────┬──────────────────────────┘
                           │ consumed by
    ┌──────────────────────┼──────────────────────────────┐
    │                      │                              │
    ▼                      ▼                              ▼
┌──────────────────┐  ┌─────────────────┐  ┌───────────────────┐
│ packet.          │  │ pe.value_bridge_│  │ explain endpoints │
│ reimbursement_   │  │ v2              │  │ (provenance UI)   │
│ profile          │  │ (unit economics)│  │                    │
│ packet.revenue_  │  │                 │  │                    │
│ realization      │  │                 │  │                    │
│ packet.metric_   │  │                 │  │                    │
│ sensitivity_map  │  │                 │  │                    │
└──────────────────┘  └─────────────────┘  └───────────────────┘
```

## How to add a new metric

1. Add a `MetricDefinition` entry to `METRIC_ONTOLOGY` in
   `econ_ontology.py`. Wire its `causal_parents` and `causal_children`.
2. If the metric should drive a bridge lever, add it to:
   - `_METRIC_SENSITIVITY_MAP` in `reimbursement_engine.py` (fields +
     pathway label)
   - `_LEVER_DISPATCH` in `pe/value_bridge_v2.py` (function mapping)
   - Optionally: `completeness.RCM_METRIC_REGISTRY` with benchmark
     percentiles
3. `classify_metric()` will now loudly fail on older data that
   references the new metric without a definition — keeps ontology
   hygiene strict.

## Current state

### Strong points
- **Explicit mappings, not inference.** Every cell defensible in IC.
- **Dual-layer coverage** — ontology describes *what each metric is*;
  reimbursement engine describes *how it hits the P&L under this
  hospital's payer structure*.
- **Provenance-aware.** Every inferred coefficient tagged so the UI
  can show "inferred from profile" vs "observed."
- **50 total tests** (21 ontology + 29 reimbursement engine) cover
  structure + calibration invariants.

### Weak points (per Prompt 3 summary)
- **Per-payer revenue leverage table** (`_PAYER_REVENUE_LEVERAGE` in
  `value_bridge_v2`) is industry-folklore; commercial contracts vary
  ±30% by market.
- **Default appeal-recovery rate of 0.39** (1 − 0.6×0.65) is a
  national average. Real rates vary by payer × category.
- **Rework cost per claim ($30)** is a single scalar across all
  hospital types.
- **Claims volume inference** ($1,500 per collectible $) is coarse;
  outpatient-heavy hospitals have 3-4× the claim count per NPR $.
- **Medicaid MCO variation** collapses into `MANAGED_GOVERNMENT`.
  State-specific detail (TX vs CA Medicaid MCO distribution) not
  captured.
- **No HCC / risk-adjustment path under capitation.** Capitation's
  coding sensitivity is modeled as 0.40, but real MA HCC capture is
  a significant revenue lever we don't yet decompose.
