# Architecture

This document is a standalone read for public contributors. For the
in-repo reference with file-level detail see
[`RCM_MC/docs/README_ARCHITECTURE.md`](../RCM_MC/docs/README_ARCHITECTURE.md).

## The one invariant

> Every UI page, every API endpoint, and every export renders from a
> single `DealAnalysisPacket` instance. Nothing renders independently.

If the Bloomberg workbench and the diligence memo disagree on a
number, that's a renderer bug — not a data bug. This is the
load-bearing design commitment that makes outputs audit-defensible.

## The packet

A `DealAnalysisPacket` is a large dataclass (~19 sections)
containing everything known about one deal. Defined in
[`rcm_mc/analysis/packet.py`](../RCM_MC/rcm_mc/analysis/packet.py).

```mermaid
classDiagram
  class DealAnalysisPacket {
    profile : HospitalProfile
    observed_metrics : dict[str, ObservedMetric]
    completeness : CompletenessAssessment
    comparables : list[ComparableHospital]
    predicted_metrics : dict[str, PredictedMetric]
    rcm_profile : dict[str, ProfileMetric]
    reimbursement_profile : ReimbursementProfile
    revenue_realization : RealizationPath
    metric_sensitivity_map : dict[str, MetricSensitivity]
    ebitda_bridge : EBITDABridgeResult
    value_bridge_result : ValueBridgeResult
    leverage_table : list[LeverageRow]
    recurring_vs_one_time_summary : dict
    enterprise_value_summary : dict
    simulation : SimulationSummary
    v2_simulation : dict
    risk_flags : list[RiskFlag]
    diligence_questions : list[DiligenceQuestion]
    provenance : ProvenanceSnapshot
    exports : dict
  }
```

Full schema: [`RCM_MC/docs/ANALYSIS_PACKET.md`](../RCM_MC/docs/ANALYSIS_PACKET.md).

## The 12-step build pipeline

`rcm_mc.analysis.packet_builder.build_analysis_packet()` walks
through 12 sequential steps. Each step is wrapped so a failure in
one section doesn't kill the packet — that section gets
`status=FAILED` with a reason and downstream steps continue.

```mermaid
flowchart TD
  S1[1 · load deal profile<br/>portfolio.store] --> S2[2 · observed metrics<br/>partner input]
  S2 --> S3[3 · completeness<br/>38-metric registry + 6 rules]
  S3 --> S4[4 · comparables<br/>ml.comparable_finder]
  S4 --> S5[5 · predict missing<br/>ml.ridge_predictor]
  S5 --> S6[6 · merge rcm_profile<br/>+ ontology attach]
  S6 --> S6b[6b · reimbursement<br/>+ realization path]
  S6b --> S7[7 · v1 bridge<br/>pe.rcm_ebitda_bridge]
  S7 --> S7b[7b · v2 bridge<br/>pe.value_bridge_v2]
  S7b --> S8[8 · two-source MC<br/>mc.ebitda_mc]
  S8 --> S8b[8b · v2 MC<br/>mc.v2_monte_carlo]
  S8b --> S9[9 · risk flags<br/>6 categories]
  S9 --> S10[10 · provenance graph<br/>rich DAG + flatten]
  S10 --> S11[11 · diligence questions<br/>P0/P1/P2]
  S11 --> S12[12 · assemble packet<br/>cache in analysis_runs]
```

## Cross-layer dependency graph

Rule: every arrow goes **down**. A layer may never import from a
layer below that circles back. This keeps the whole system
intelligible as it grows.

```mermaid
flowchart TD
  pkt[analysis.packet<br/>canonical dataclass]
  bld[analysis.packet_builder<br/>orchestrator]
  dom[domain<br/>econ_ontology, metric registry]
  ml[ml<br/>ridge + conformal + comparables]
  fin[finance<br/>reimbursement_engine, realization]
  pe[pe<br/>bridge v1, bridge v2, pe_math]
  mc[mc<br/>two-source MC, v2 MC, scenarios]
  rf[analysis<br/>risk_flags, diligence_questions]
  prov[provenance<br/>rich graph + flat + explain]
  ui[ui.analysis_workbench<br/>Bloomberg HTML]
  exp[exports.packet_renderer<br/>HTML/PPTX/DOCX/CSV/JSON]
  api[server.py<br/>api endpoints]

  bld --> pkt
  dom --> bld
  ml --> bld
  fin --> bld
  pe --> bld
  mc --> bld
  rf --> bld
  prov --> bld
  pkt --> ui
  pkt --> exp
  pkt --> api
```

## Caching

Every build writes one row to `analysis_runs`:

- `deal_id`
- `hash_inputs` — SHA256 of `(deal_id, observed_metrics, scenario_id,
  as_of, profile)` with `sort_keys=True`
- compressed JSON blob of the full packet

`get_or_build_packet()` checks the cache by
`(deal_id, hash_inputs)` before building — identical inputs return
the exact cached packet. `force_rebuild=True` bypasses the cache.

This is why the reproducibility contract works: identical inputs →
identical packet content (locked by
`tests/test_packet_reproducibility.py`).

## Supporting infrastructure

```mermaid
flowchart LR
  subgraph data-ingestion
    hcris[cms_hcris]
    care[cms_care_compare]
    util[cms_utilization]
    irs[irs990_loader]
    sec[sec_edgar]
  end
  data-ingestion --> benches[(hospital_benchmarks)]
  portfolio[portfolio.store<br/>SQLite 17+ tables] --> benches
  portfolio --> deals[(deals)]
  portfolio --> runs[(analysis_runs)]
  portfolio --> mcruns[(mc_simulation_runs)]
  portfolio --> exports[(generated_exports)]
  portfolio --> snaps[(deal_snapshots)]
  auth[auth + audit<br/>scrypt + CSRF + sessions] --> portfolio
  alerts[alerts + deals workflow<br/>cohorts, owners, deadlines] --> portfolio
```

## Tech-stack invariants

- **Python 3.14** stdlib-heavy (3.10+ supported).
- Runtime deps: `numpy`, `pandas`, `pyyaml`, `matplotlib`,
  `openpyxl`. Optional: `python-pptx`, `python-docx`, `plotly`,
  `scipy` with graceful fallbacks.
- **No `sklearn`.** Ridge + conformal implemented in numpy
  closed-form (~300 lines).
- **No Flask / FastAPI.** Stdlib `http.server.ThreadingHTTPServer`.
- **SQLite** via stdlib `sqlite3`. Every table uses
  `CREATE TABLE IF NOT EXISTS` for idempotent migrations.
- **Auth** via stdlib `hashlib.scrypt` + session cookies.
- **Tests** via stdlib `unittest`, driven by `pytest`.
