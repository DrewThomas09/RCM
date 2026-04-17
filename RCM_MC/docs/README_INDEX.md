# RCM-MC Documentation Index

This is the start-here index for the RCM-MC codebase. If you've never
seen the project before, read the documents below in order.

RCM-MC is a healthcare revenue-cycle diligence and portfolio-operations
platform. PE associates use it to analyze a single hospital deal from
end to end: pull in observed RCM metrics → find comparable hospitals →
predict missing metrics → translate metric changes into EBITDA and
enterprise value → simulate uncertainty → produce a diligence memo.

The system is organized around a **single canonical object, the
`DealAnalysisPacket`** — every UI page, API endpoint, and export
renders from the same packet instance. Nothing renders independently.

## Reading order

1. **[README_GLOSSARY.md](README_GLOSSARY.md)** — every healthcare, PE,
   and internal term used in the codebase, explained from zero.
2. **[README_ARCHITECTURE.md](README_ARCHITECTURE.md)** — how the whole
   system hangs together around the packet. Includes the 12-step
   build pipeline and the cross-layer dependency diagram.
3. **[README_DATA_FLOW.md](README_DATA_FLOW.md)** — end-to-end trace of
   one deal from "register in portfolio" to "export diligence memo."
   Read this after the architecture doc to see how the abstractions
   touch each other in practice.
4. **[README_BUILD_STATUS.md](README_BUILD_STATUS.md)** — what's
   production-grade today, what's weakly calibrated, what's still
   missing. This is the roadmap document.

## Per-layer references

Each file below covers one subsystem in depth. They're designed for
someone modifying that layer who wants a fast on-ramp without reading
every source file.

| Layer | Document | Owns |
|---|---|---|
| Data ingestion | [README_LAYER_DATA.md](README_LAYER_DATA.md) | CMS HCRIS, Care Compare, Utilization, IRS 990 loaders |
| Domain / economics | [README_LAYER_DOMAIN.md](README_LAYER_DOMAIN.md) | Metric ontology + reimbursement engine |
| Analysis spine | [README_LAYER_ANALYSIS.md](README_LAYER_ANALYSIS.md) | `DealAnalysisPacket`, builder, completeness, risk flags, diligence questions |
| Prediction / ML | [README_LAYER_ML.md](README_LAYER_ML.md) | Ridge + conformal predictor, comparables, backtester |
| PE value math | [README_LAYER_PE.md](README_LAYER_PE.md) | EBITDA bridge v1 + v2, deal-math (MOIC / IRR) |
| Monte Carlo | [README_LAYER_MC.md](README_LAYER_MC.md) | Two-source simulator, scenario compare, convergence |
| Provenance | [README_LAYER_PROVENANCE.md](README_LAYER_PROVENANCE.md) | Rich causal DAG + plain-English explainer |
| UI + exports | [README_LAYER_UI_EXPORTS.md](README_LAYER_UI_EXPORTS.md) | Bloomberg workbench, packet-renderer (HTML/PPTX/JSON/CSV) |
| Infra / plumbing | [README_LAYER_INFRA.md](README_LAYER_INFRA.md) | HTTP server, CLI, SQLite store, caching, rate limits |

## Legacy and ancillary docs

These predate the packet-centric refactor but remain accurate for the
parts of the system they cover:

- [ARCHITECTURE.md](ARCHITECTURE.md) — original architecture doc
- [ANALYSIS_PACKET.md](ANALYSIS_PACKET.md) — packet-schema reference
- [BENCHMARK_SOURCES.md](BENCHMARK_SOURCES.md) — HFMA / Kodiak / Crowe calibration sources
- [FULL_SUMMARY.md](FULL_SUMMARY.md) — high-level pitch / partner narrative
- [GETTING_STARTED.md](GETTING_STARTED.md) — partner-facing quick start
- [METRIC_PROVENANCE.md](METRIC_PROVENANCE.md) — provenance design rationale
- [MODEL_IMPROVEMENT.md](MODEL_IMPROVEMENT.md) — earlier model-improvement plan
- [PARTNER_WORKFLOW.md](PARTNER_WORKFLOW.md) — day-in-the-life partner workflow

## One-sentence summary of every source package

| Package | One-sentence summary |
|---|---|
| `rcm_mc/analysis/` | Owns the `DealAnalysisPacket` + the 12-step builder that assembles it. |
| `rcm_mc/domain/` | Economic metric ontology — what every RCM metric *is* and how it connects causally. |
| `rcm_mc/finance/` | Reimbursement engine — how hospital revenue is actually generated, delayed, or lost under different payer structures. |
| `rcm_mc/ml/` | Ridge + conformal predictor, comparable-hospital finder, feature engineering, backtester. |
| `rcm_mc/pe/` | EBITDA bridge (v1 = research-band coefficients; v2 = unit economics), PE deal math (MOIC, IRR, hold-period grid). |
| `rcm_mc/mc/` | Two-source Monte Carlo (prediction × execution uncertainty), scenario comparison, convergence check. |
| `rcm_mc/provenance/` | Per-metric `DataPoint` registry, rich explorable DAG, plain-English explainer. |
| `rcm_mc/data/` | CMS HCRIS / Care Compare / Utilization + IRS 990 ingestion; `hospital_benchmarks` table. |
| `rcm_mc/exports/` | `PacketRenderer` for HTML memo / PPTX / JSON / CSV / DOCX questions + `generated_exports` audit. |
| `rcm_mc/ui/` | Bloomberg-style single-page analyst workbench at `/analysis/<deal_id>`. |
| `rcm_mc/portfolio/` | SQLite connection manager + deal registration + snapshot/digest primitives. |
| `rcm_mc/deals/` | Per-deal state: profile, notes, owner, tags, deadlines, simulation inputs. |
| `rcm_mc/alerts/` | Alert lifecycle (fire → ack → snooze → escalate) + audit. |
| `rcm_mc/auth/` | Scrypt passwords, sessions, audit log. |
| `rcm_mc/scenarios/` | YAML scenario overlay + shocks for the Monte Carlo simulator. |
| `rcm_mc/core/` | Monte Carlo kernel, distributions, RNG, calibration. |
| `rcm_mc/rcm/` | Claim-distribution sampling + initiative effects. |
| `rcm_mc/reports/` | Legacy HTML report, PPTX export, narrative, LP update. |
| `rcm_mc/infra/` | Logger, config validation, consistency check, rate limiter, small utilities. |
| `rcm_mc/server.py` | Top-level HTTP app (stdlib only — no Flask / FastAPI). |
| `rcm_mc/cli.py` | Top-level CLI dispatcher (`rcm-mc analysis`, `rcm-mc data`, etc.). |
