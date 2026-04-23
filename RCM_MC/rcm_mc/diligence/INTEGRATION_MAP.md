# SeekingChartis — Full Integration Map

How the pieces fit together across the three sessions, the sibling
projects on disk, and the existing PE Intelligence / packet / bridge
infrastructure.

## Source repositories

Three projects live side-by-side under `Coding Projects/`:

| Path                              | Role                          | License     |
|-----------------------------------|-------------------------------|-------------|
| `RCM_MC/`                         | The product (this package)    | Proprietary |
| `cms_medicare-master/`            | CMS Data API advisory scripts | (no LICENSE) |
| `ChartisDrewIntel-main/`          | Vendored Tuva Project v0.17.1 | Apache 2.0  |

`ChartisDrewIntel-main/` is a directory-renamed but otherwise-unmodified
copy of Tuva — the `dbt_project.yml` still carries
`name: 'the_tuva_project'`, the LICENSE is Apache 2.0, and the README
credits Tuva Health. Its attribution is preserved intact.

## The data flow, end to end

```
Partner uploads raw file(s)
   │
   ▼
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1 — Ingestion & Normalization                             │
│ rcm_mc/diligence/ingest/                                         │
│                                                                 │
│  readers.py    → CSV/TSV/Parquet/Excel/EDI-837/EDI-835           │
│  normalize.py  → dates, payer resolution, CPT/ICD validation     │
│  ingester.py   → multi-EHR rollup, 835 reconcile, ZBA preserve   │
│                                                                 │
│ Output: CanonicalClaimsDataset (CCD) + TransformationLog         │
│         • ccd.json + transformation_log.json on disk             │
│         • deterministic content_hash                             │
└─────────────────────────────────────────────────────────────────┘
   │
   ├────────────────────────────┐
   ▼                            ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│ Optional: Tuva       │  │ PHASE 2 — KPI Benchmarking           │
│ enrichment           │  │ rcm_mc/diligence/benchmarks/          │
│                      │  │                                      │
│ tuva_bridge.py:      │  │  kpi_engine.py  → Days in A/R,       │
│  CCD → Tuva Input    │  │                   FPDR, A/R>90,      │
│  Layer schema        │  │                   CTC, NRR, lag      │
│  (arrow + duckdb)    │  │  cohort_liquidation.py → as_of       │
│                      │  │                   censored curves    │
│ Vendored at:         │  │  _ansi_codes.py → denial categories  │
│  ChartisDrewIntel-   │  │                                      │
│  main/               │  │ Output: KPIBundle + CohortLiquidation │
│                      │  │         CARC Pareto                  │
│ (dbt-core + dbt-     │  └──────────────────────────────────────┘
│  duckdb optional)    │     │
└──────────────────────┘     │
                             ▼
                        ┌──────────────────────────────────────┐
                        │ Gauntlet (MANDATORY BEFORE PACKET)   │
                        │ rcm_mc/diligence/integrity/          │
                        │                                      │
                        │  leakage_audit.py   target-in-peers │
                        │  split_enforcer.py  train/cal/test   │
                        │  distribution_shift.py PSI+KS        │
                        │  temporal_validity.py regulatory     │
                        │                     calendar overlap │
                        └──────────────────────────────────────┘
                             │
                             ▼
                        ┌──────────────────────────────────────┐
                        │ CCD → packet bridge                  │
                        │ rcm_mc/diligence/ccd_bridge.py       │
                        │                                      │
                        │ Priority:                            │
                        │   OVERRIDE (1.0) >                   │
                        │   CCD (1.0) >                        │
                        │   PARTNER_YAML (0.7) >               │
                        │   PREDICTED (≤0.5)                   │
                        │                                      │
                        │ Output: ObservedMetric(source=CCD)   │
                        │         ProvenanceNode(CCD_DERIVED)  │
                        └──────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ DealAnalysisPacket (the Phase 4 spine — unchanged contract)      │
│ rcm_mc/analysis/packet.py                                         │
│                                                                  │
│  observed_metrics[key] = ObservedMetric(...)                     │
│  risk_flags = [ RiskFlag, ... ]                                  │
│  provenance = ProvenanceGraph(nodes, edges)                      │
│  completeness, diligence_questions, bridge outputs, …            │
└──────────────────────────────────────────────────────────────────┘
                             │
                             ▼
             ┌───────────────┴───────────────┐
             ▼                               ▼
┌──────────────────────┐        ┌──────────────────────────┐
│ v1 / v2 bridges      │        │ Monte Carlo / exports    │
│ rcm_mc/pe/            │        │ rcm_mc/mc/, exports/      │
│ (unchanged)          │        │ (unchanged contract)     │
└──────────────────────┘        └──────────────────────────┘
```

## Horizontal overlay: CMS advisory

The CMS advisory pipeline runs **independently** of the CCD flow —
it analyses the Medicare population at the `provider_type` level, not
the deal's own claims. Its output overlays the packet with market-
posture risk flags.

```
CMS Data API  (data.cms.gov)   ──or──   partner-supplied CMS extract
   │
   ▼
┌──────────────────────────────────────────────────────────────────┐
│ rcm_mc/pe/cms_advisory.py                                         │
│                                                                  │
│  standardize_columns  → canonical CMS PUF vocabulary              │
│  screen_providers     → opportunity score (scale/margin/acuity/   │
│                          fragmentation composite)                 │
│  yearly_trends        → YoY payment / services / bene growth      │
│  provider_volatility  → YoY std dev per provider_type             │
│  momentum_profile     → CAGR + consistency (≥ min_years obs)      │
│  regime_classification→ durable_growth / steady_compounders /     │
│                          emerging_volatile / stagnant /           │
│                          declining_risk                           │
│  stress_test          → 6 default scenarios incl. OBBBA + site-   │
│                          neutral; total-payment delta             │
│  consensus_rank       → weighted ensemble: opportunity + growth + │
│                          vol-inverse                              │
└──────────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────────┐
│ rcm_mc/pe/cms_advisory_bridge.py                                  │
│                                                                  │
│  findings_for_provider(provider_type, ...)                       │
│  findings_to_risk_flags(findings) → List[RiskFlag]               │
│                                                                  │
│  Categories:                                                     │
│   • market_posture     (consensus_rank top/bottom quartile)      │
│   • operating_regime   (stagnant/declining_risk → MEDIUM/HIGH)   │
│   • earnings_durability(yoy_payment_volatility ≥ 35%)            │
│   • stress_exposure    (worst scenario ≤ −20%)                   │
└──────────────────────────────────────────────────────────────────┘
   │
   ▼
DealAnalysisPacket.risk_flags.append(...)   ← same packet spine
```

The CMS advisory **is not gated on a CCD being present**. Every deal
gets the advisory overlay keyed on the target's `provider_type` — this
is by design: partners need market context even on deals where no
claims data has been uploaded yet.

## Module ownership matrix

| Concern                            | Module                                                             | Session |
|-----------------------------------|--------------------------------------------------------------------|---------|
| CCD data contract                 | `rcm_mc/diligence/ingest/ccd.py`                                   | 1       |
| File readers                      | `rcm_mc/diligence/ingest/readers.py`                               | 1       |
| Normalizers (dates, payer, CPT)   | `rcm_mc/diligence/ingest/normalize.py`                             | 1       |
| Ingester driver                   | `rcm_mc/diligence/ingest/ingester.py`                              | 1       |
| Messy-fixture library             | `tests/fixtures/messy/`                                            | 1       |
| Target-leakage audit              | `rcm_mc/diligence/integrity/leakage_audit.py`                      | 2       |
| Provider-disjoint splits          | `rcm_mc/diligence/integrity/split_enforcer.py`                     | 2       |
| Distribution shift (PSI + KS)     | `rcm_mc/diligence/integrity/distribution_shift.py`                 | 2       |
| Temporal validity / reg. calendar | `rcm_mc/diligence/integrity/temporal_validity.py`                  | 2       |
| KPI engine (HFMA / AAPC)          | `rcm_mc/diligence/benchmarks/kpi_engine.py`                        | 2       |
| Cohort liquidation w/ censoring   | `rcm_mc/diligence/benchmarks/cohort_liquidation.py`                | 2       |
| ANSI CARC classifier              | `rcm_mc/diligence/benchmarks/_ansi_codes.py`                       | 2       |
| CCD → packet bridge               | `rcm_mc/diligence/ccd_bridge.py`                                   | 2       |
| KPI-truth fixtures                | `tests/fixtures/kpi_truth/`                                        | 2       |
| Tuva Input Layer bridge           | `rcm_mc/diligence/ingest/tuva_bridge.py`                           | 3       |
| CMS advisory scoring              | `rcm_mc/pe/cms_advisory.py`                                        | 3       |
| CMS advisory → packet             | `rcm_mc/pe/cms_advisory_bridge.py`                                 | 3       |
| Benchmarks UI page                | `rcm_mc/ui/diligence_benchmarks.py`                                | 2       |
| Diligence tab stubs               | `rcm_mc/diligence/_pages.py`                                       | 1       |
| Nav (diligence tabs, alerts gone) | `rcm_mc/ui/_chartis_kit.py::_CORPUS_NAV`                           | 1       |
| MetricSource enum + CCD value     | `rcm_mc/analysis/packet.py`                                        | 2       |
| NodeType.CCD_DERIVED              | `rcm_mc/provenance/graph.py`                                       | 2       |

## Test coverage summary

| Suite                                        | Tests | Session | Purpose                                  |
|---------------------------------------------|-------|---------|------------------------------------------|
| `test_diligence_ingest.py`                   | 11    | 1       | 10 messy fixtures + cross-cutting invariants |
| `test_diligence_leakage_audit.py`            | 6     | 2       | Target leakage catches                   |
| `test_diligence_split_enforcer.py`           | 10    | 2       | Provider-disjoint splits                 |
| `test_cohort_liquidation_censoring.py`       | 5     | 2       | as_of censoring refuses stale windows    |
| `test_kpi_engine_truth.py`                   | 7     | 2       | Hand-computed KPI values match formulas  |
| `test_distribution_shift.py`                 | 4     | 2       | Dental DSO flags OOD, acute flags IN     |
| `test_ccd_provenance_end_to_end.py`          | 11    | 2       | CCD → KPI → ObservedMetric → provenance  |
| `test_integrations_full_stack.py`            | 14    | 3       | CMS advisory + Tuva bridge + risk flags  |
| **Total diligence + integration**            | **68**| —       | Runs in ~0.5s on a laptop                |

## What an analyst does in practice

1. **Open `/diligence/ingest`**, upload raw files (CSV / Parquet /
   Excel / EDI). Ingester produces a CCD + transformation log.
2. **Open `/diligence/benchmarks`**, see scorecard + cohort
   liquidation + denial Pareto. Numbers that require external
   inputs (Cost to Collect, NRR) show "Insufficient data" with the
   reason — never fabricated.
3. **Packet build** picks up CCD-derived observed_metrics with
   confidence=1.0, overriding any partner YAML. The CMS advisory
   overlay adds market-posture / regime / stress risk flags.
4. **Optional Tuva enrichment** — for partners who need CCSR
   condition categories, HCC risk scores, or readmission flags:
   `write_tuva_input_layer_duckdb(ccd, path)` seeds a DuckDB file in
   Tuva's Input Layer shape. Partner runs `dbt build` against the
   vendored `ChartisDrewIntel-main/` project. Results land in the
   same DuckDB under Tuva's schema prefix.
5. **Phase 3 (next session)** — root cause Pareto + ZBA autopsy will
   consume the CCD's `qualifying_claim_ids` + `adjustment_reason_codes`
   trail to drill through to source rows.

## Key design invariants (across all sessions)

- **No number without provenance.** Every ObservedMetric carries a
  `source` + `source_detail` + confidence. Every KPIResult carries
  sample_size + citation + temporal_validity. Every RiskFlag carries
  trigger_metrics that name the exact table/column.
- **Never fabricate missing data.** KPIs return None + reason.
  Cohort cells return `INSUFFICIENT_DATA`. The UI renders these as
  explicit "insufficient data" strings — no silent imputation.
- **Deterministic under inputs.** `content_hash` on CCD + DQReport
  + ingest_id is stable across runs on identical inputs.
- **Deal-disjoint everything.** Target's own data never leaks into
  peer predictions; split_enforcer guarantees train/cal/test buckets
  share no provider_ids.
- **Dark theme, whitespace first.** Every diligence page renders
  through `chartis_shell`; KPI scorecard has one primary number per
  section; alerts are gone from the analyst nav.
