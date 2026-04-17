# RCM-MC Documentation

Organized documentation for the RCM-MC healthcare PE diligence platform (v0.6.0).

**New here?** Start with the **[Walkthrough Tutorial](00_Walkthrough_Tutorial.md)** -- a 30-minute hands-on tour that exercises every major feature with copy-paste commands.

---

## How to Use This Folder

Start with the document that matches your role:

| You are a... | Start here |
|--------------|-----------|
| **Anyone (first time)** | **[00 Walkthrough Tutorial](00_Walkthrough_Tutorial.md)** |
| **New user / partner** | [04 Getting Started](04_Getting_Started.md) then [07 Partner Workflow](07_Partner_Workflow.md) |
| **API integrator** | [01 API Reference](01_API_Reference.md) |
| **Ops / deployer** | [02 Configuration and Operations](02_Configuration_and_Operations.md) |
| **Developer** | [03 Developer Guide](03_Developer_Guide.md) then [05 Architecture](05_Architecture.md) |
| **Data scientist** | [06 Analysis Packet](06_Analysis_Packet.md) then [08 Metric Provenance](08_Metric_Provenance.md) |

---

## Document Index

### Core Documentation

| # | File | Description |
|---|------|-------------|
| 01 | [API Reference](01_API_Reference.md) | All 52 API endpoints with parameters, responses, and examples |
| 02 | [Configuration and Operations](02_Configuration_and_Operations.md) | Database, auth, deployment, backup, monitoring, security |
| 03 | [Developer Guide](03_Developer_Guide.md) | Architecture, testing, coding conventions, module map |
| 04 | [Getting Started](04_Getting_Started.md) | Installation, first run, basic workflow |
| 05 | [Architecture](05_Architecture.md) | System design, data flow, design decisions |

### Domain Documentation

| # | File | Description |
|---|------|-------------|
| 06 | [Analysis Packet](06_Analysis_Packet.md) | The canonical DealAnalysisPacket dataclass |
| 07 | [Partner Workflow](07_Partner_Workflow.md) | End-to-end partner usage: screen to exit |
| 08 | [Metric Provenance](08_Metric_Provenance.md) | How each metric traces back to source data |
| 09 | [Benchmark Sources](09_Benchmark_Sources.md) | CMS HCRIS, Care Compare, IRS 990 data pipeline |
| 10 | [Model Improvement](10_Model_Improvement.md) | Monte Carlo model calibration and improvement |
| 11 | [Glossary](11_Glossary.md) | Terms: IDR, FWR, DAR, MOIC, IRR, covenant, etc. |

### Technical Deep-Dives

| # | File | Description |
|---|------|-------------|
| 12 | [Data Flow](12_Data_Flow.md) | How data moves through the system |
| 13 | [Build Status](13_Build_Status.md) | Current build state and test results |
| 14 | [Full Summary](14_Full_Summary.md) | Complete feature inventory |
| 15 | [Documentation Index](15_Documentation_Index.md) | Cross-references across all docs |

### Layer-by-Layer Architecture

| # | File | Description |
|---|------|-------------|
| 16 | [Layer: Analysis](16_Layer_Analysis.md) | Packet builder, completeness, risk flags |
| 17 | [Layer: Data](17_Layer_Data.md) | HCRIS, auto-populate, document reader |
| 18 | [Layer: Domain](18_Layer_Domain.md) | Deals, alerts, portfolio, auth |
| 19 | [Layer: Infrastructure](19_Layer_Infrastructure.md) | Migrations, webhooks, job queue, rate limit |
| 20 | [Layer: Monte Carlo](20_Layer_Monte_Carlo.md) | Simulation engine, v1/v2 bridge |
| 21 | [Layer: Machine Learning](21_Layer_Machine_Learning.md) | Ridge predictor, conformal intervals |
| 22 | [Layer: PE Math](22_Layer_PE_Math.md) | MOIC, IRR, value bridge, ramp curves |
| 23 | [Layer: Provenance](23_Layer_Provenance.md) | Metric lineage tracking |
| 24 | [Layer: UI and Exports](24_Layer_UI_and_Exports.md) | Renderers, workbench, shell system |
| 25 | [Architecture Detailed](25_Architecture_Detailed.md) | Extended architecture documentation |

---

## Source Code READMEs

Each package in `rcm_mc/` has its own README.md describing what that package does:

| Package | Purpose |
|---------|---------|
| `rcm_mc/ai/` | LLM client, memo writer, document QA, conversational chat |
| `rcm_mc/alerts/` | Alert fire, ack, snooze, history, escalation |
| `rcm_mc/analysis/` | Packet builder, completeness, risk flags, deal sourcing |
| `rcm_mc/analytics/` | Causal inference (ITS + DiD), service lines |
| `rcm_mc/auth/` | Authentication, sessions, CSRF, audit log |
| `rcm_mc/core/` | Monte Carlo simulator, kernel, distributions, calibration |
| `rcm_mc/data/` | HCRIS, IRS 990, data ingest, document reader, EDI parser |
| `rcm_mc/deals/` | Notes, tags, owners, deadlines, health score, stages |
| `rcm_mc/domain/` | Custom metrics, domain-specific business logic |
| `rcm_mc/exports/` | Packet renderer (HTML, XLSX, PPTX, CSV, ZIP) |
| `rcm_mc/finance/` | Financial modeling utilities |
| `rcm_mc/infra/` | Migrations, webhooks, OpenAPI, rate limit, job queue |
| `rcm_mc/integrations/` | DealCloud, Salesforce, PMS connectors |
| `rcm_mc/mc/` | Monte Carlo store, portfolio-level MC |
| `rcm_mc/ml/` | Ridge predictor, conformal intervals, ensemble |
| `rcm_mc/pe/` | PE math: MOIC, IRR, bridge, ramp curves, hold tracking |
| `rcm_mc/portfolio/` | Store (SQLite), snapshots, dashboard |
| `rcm_mc/provenance/` | Metric lineage graph, explain narratives |
| `rcm_mc/rcm/` | RCM claim distributions, initiative tracking |
| `rcm_mc/reports/` | Report generators (LP update, exit memo, partner brief) |
| `rcm_mc/scenarios/` | Scenario overlay, preset shocks |
| `rcm_mc/ui/` | Page renderers, shared shell, dark mode CSS |
| `rcm_mc/verticals/` | Adjacent verticals (ASC, MSO, Behavioral Health) |
