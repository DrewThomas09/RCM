# 06 · Screening & sourcing — how candidates are scored

> The front of the funnel: turning ~6,000 public hospitals (and the realized-deal corpus) into a ranked candidate list, with **no internal/seller data** — pure public-data screening. This file traces how each candidate score is produced.

---

## `/predictive-screener` — the deal-sourcing screen
**The killer feature:** filter ~6,000+ hospitals by predicted RCM performance, estimated EBITDA uplift, distress probability, and financial characteristics — all from public data.

- **Universe:** HCRIS hospital filings (`hospital_benchmarks`). `_add_features(df)` derives the screening features and emits a **`data_quality_ok`** flag per row — False when a filing is implausible (opex > 2× revenue, negative revenue, sub-$100K revenue). Junk filings are excluded from "distressed" counts and rankings, so the screen doesn't surface data artifacts as targets.
- **Estimated EBITDA uplift** (the headline rank metric): each hospital's HCRIS-derived RCM metrics (denial proxy, DAR, margin, payer mix) are run through the RCM→EBITDA lever math (the same 7-lever logic as the bridge, §03/`PEDESK_ALGORITHMS` §3) against benchmark-tier targets → a dollar uplift estimate. This is **modeled** (tagged ML/COMPUTED), not measured — it's a sourcing heuristic, not a diligenced number.
- **Distress / margin screens:** operating margin from HCRIS (clamped to credible range); a hospital is "distressed" at margin < −5% **on a credible filing only**.
- **Filters** (query params): region, bed band, max margin, min uplift, sort key. Quick-screen buttons preset common filters (e.g. "SE · 200–400 beds · >$3M uplift").
- **Rows** link through to `/hospital/<ccn>` (profile) and `/ebitda-bridge/<ccn>` (the per-hospital bridge). Selecting a hospital can start a diligence packet.

## `/screen` — the metric screener
A simpler HCRIS metric filter (beds, revenue, margin, payer mix) over the hospital universe — the "filter by the raw numbers" view, vs the predictive screener's "filter by modeled opportunity."

## `/screening/dashboard` — the deal-universe console
A Bloomberg-style filterable universe that scores + filters candidates via query params (a denser, multi-column variant of the screener).

## `/deal-screening` — corpus screening engine
Runs `deal_screening_engine.screen_corpus` over the **realized-deal corpus** and produces a **PASS / WATCH / FAIL** mix against live-tunable thresholds (query params: max composite risk score, max EV/EBITDA, max Medicaid %, etc.). This is a "would these historical deals clear my screen?" calibration tool — it screens the corpus, not live hospitals, so you can sanity-check thresholds against known outcomes.

## `/pipeline` — the tracked funnel
The deals a partner is actively tracking (the `pipeline_hospitals` table), shown as a stage funnel (sourced → IOI → LOI → SPA → closed → hold → exit) with proportional bars + saved searches. This is workflow state, not a model — counts come straight from the pipeline table.

## `/pe-intelligence` — the PE-Brain hub
The entry to the 278-module "Partner Brain" — partner reflexes, the archetype library, the reasonableness matrix, the red-flag catalog. From here a partner drills into a specific deal's `/deal/<id>/partner-review` (§03). This is a navigation/catalog surface, not a number-producing page.

---

## Where these numbers come from — summary
| Page | Source | The key number |
|---|---|---|
| `/predictive-screener`, `/screen`, `/screening/dashboard` | HCRIS (`hospital_benchmarks`) | modeled EBITDA uplift + margin/distress screens (public-data only) |
| `/deal-screening` | realized-deal corpus (`public_deals`) | PASS/WATCH/FAIL vs tunable risk thresholds |
| `/pipeline` | `pipeline_hospitals` table | tracked-deal stage counts (workflow, not modeled) |

> Every screening number is **modeled or measured-public**, never seller data — that's the point of the funnel front: you can build a target list before anyone shares a data room. The badges say ML/COMPUTED/HCRIS so the modeled uplift is never mistaken for a diligenced figure.

---
*Next: `07_LIBRARY_CORPUS.md` — the empirical base every benchmark rests on.*
