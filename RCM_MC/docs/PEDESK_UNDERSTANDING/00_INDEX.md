# PE Desk — Understanding (deep reference)

> This folder is the **deep, in-depth reference** to PE Desk: how the whole system actually works, what's on each page, and **where every number comes from** (the data, the function, the formula). It is built to let you answer detailed questions — from an LP, an IC, or an engineer — without opening the code.
>
> Scope rule: this documents **what is actually in PE Desk and connected** — the pages a user reaches and the numbers they see. It deliberately skips dead/local-only plumbing.

## How to read this set

Read `01_SYSTEM_FLOW` first — it explains the one mechanism (the **DealAnalysisPacket**) that every per-deal number flows through, so the per-page files can just say "this comes from packet section X" and you'll know exactly what that means.

Each per-page file follows the same template:
- **What the page is for** (the partner's job-to-be-done)
- **Route & renderer** (URL → file → function)
- **Every block on the page**, and for each number: **where it comes from** (data source → function → formula), what it means, and how to read it
- **Drill-throughs** (where clicking takes you)
- **Empty / honest states** (what shows when data is missing — and why it's not faked)

## Files

| File | Covers |
|---|---|
| `01_SYSTEM_FLOW.md` | Request → auth → route → packet build (12 steps) → render. The packet anatomy. How a number gets its provenance. The two bridges, the predictor, the simulator at a system level. |
| `02_COMMAND_CENTER.md` | `/app` — the daily landing page. Every block (return hero, KPI strip, morning brief, pipeline funnel, deals table, covenant heatmap, EBITDA drag, initiative tracker, alerts, deliverables) and where each number comes from. |
| `03_DEAL_PAGES.md` | The per-deal surfaces: deal dashboard, profile + EBITDA bridge, partner-review, red-flags, archetype, investability, market-structure, white-space, stress grid, IC packet. Every score and band sourced. |
| `04_DILIGENCE_RCM.md` | The RCM commercial-diligence pipeline: ingest → benchmarks → root-cause → value → QoE memo, the 835/837 snapshot, and the analytic workbenches (denial prediction, payer stress, covenant lab, bridge audit). |
| `05_PORTFOLIO.md` | Portfolio overview, monitor (health + launched-vs-realized), risk-scan, portfolio-analytics, sponsor track record, payer intelligence. |
| `06_SCREENING.md` | Hospital screener, predictive screener, pipeline, deal-screening engine — how candidates are scored and ranked. |
| `07_LIBRARY_CORPUS.md` | The deal library/corpus, comparables, RCM benchmarks, market rates — the empirical base every benchmark rests on. |
| `08_DATA_PUBLIC_MODULES.md` | The ~150 analytic modules — the shared pattern, a grouped catalog, and (critically) **which are live vs curated/illustrative**. |
| `09_HOSPITAL_PAGES.md` | The per-hospital surfaces (`/hospital/<ccn>/*`) — profile, stats, providers, ML/Bayesian, data room, bridge, scenarios. |
| `10_WORKFLOW_OPS.md` | The daily portfolio workflow — alerts lifecycle, cohorts/owners/deadlines/notes/tags, LP digest, audit. |
| `11_METRIC_GLOSSARY.md` | Canonical definitions of every metric name — definition · computation · source · scale. The connective tissue. |

## The one-sentence version

A partner enters (or PE Desk infers from public CMS data) a hospital's operating metrics → those metrics are predicted/calibrated where missing → fed through a 7-lever (and a payer-mix-aware v2) **EBITDA bridge** → wrapped in a two-source **Monte Carlo** → turned into MOIC/IRR/covenant math → all frozen into one **DealAnalysisPacket** → and **every page renders from that packet**, with each number carrying a provenance tag (real CMS / seller / calibrated / modeled / benchmark) so you always know what's measured vs estimated.

---
*Companion high-level map: `../PEDESK_OVERVIEW.md`, `../PEDESK_PAGES.md`, `../PEDESK_ALGORITHMS.md`, `../PEDESK_DATA.md`. This folder is the deeper layer beneath them.*
