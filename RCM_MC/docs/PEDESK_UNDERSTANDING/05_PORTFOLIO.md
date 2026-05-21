# 05 · Portfolio — operations & corpus benchmarking

> The Portfolio section spans two number-families (see `01_SYSTEM_FLOW` §4): **portfolio-operations** pages read live portfolio state from SQLite (`deals`, `deal_snapshots`, `alerts`, `initiative_actuals`); **corpus-benchmarking** pages query the realized-deal corpus (`public_deals`). This file traces both.

---

## `/portfolio` — overview + regression
Lists the active deals (`store.list_deals()`) with a portfolio-level OLS regression (see `PEDESK_ALGORITHMS` §7). The regression is a **diagnostic, in-sample** tool: it shows which features correlate with an outcome across the deals, with pinv-based standard errors (so collinear HCRIS features don't produce NaN SEs) and VIFs. Coefficients render in a forest plot (diverging bars with 95% CI whiskers; non-significant ones faded).

## `/portfolio/monitor` — health + value creation
- **Health distribution bar** — proportional green/amber/red/no-health over the active deals, from each deal's latest health band (`compute_health`, §03).
- **Plan vs Actual by metric (cross-portfolio)** — aggregated EBITDA-bridge variance vs plan across deals with quarterly actuals.
- **Value Creation — Launched vs Realized** (this is the panel added in the analytics work):
  - **Launched** = Σ cumulative *underwritten plan* EBITDA of initiatives in execution (an initiative counts as launched once it has ≥1 quarter of recorded actuals). Source: `initiative_portfolio_rollup(store)` summing `cumulative_plan`.
  - **Realized** = Σ cumulative *actual* EBITDA impact recorded (raw run-rate; **not** TTM, **not** re-attributed). Source: same rollup summing `cumulative_actual`.
  - **Capture rate** = realized / launched, with a progress bar (green ≥85% / amber ≥60% / red below). Honest empty state when no actuals exist.
- **Alerts** — open alerts. Empty: "All deals on track."

## `/portfolio/risk-scan` — the morning cross-portfolio scan
One row per active deal with: health score + band, covenant status, open-alert count, snapshot freshness (days since last snapshot), and overdue deadlines — sortable/filterable so the partner triages the book in one screen. CSV at `/api/portfolio/risk-scan.csv`. All values come from the per-deal portfolio store modules (`health_score`, `covenant_metrics`, `alerts`, `deal_snapshots`, `deal_deadlines`).

## `/portfolio-analytics` — corpus structure
A corpus-scope analytics dashboard (queries `public_deals`):
- **Corpus scorecard** — MOIC P25/P50/mean/P75, vintage-year count, etc.
- **Vintage cohorts** — median realized MOIC by vintage year (SVG bar; home-run vintages read at a glance).
- **Deals by type** — count/share per deal type + **median-MOIC-by-type bars** (which archetype returns best; tone ≥2.5× positive / ≥1.5× warning / else negative).
- **Return distribution**, **concentration** (top sponsors/sectors), **payer-mix sensitivity**, **outlier detection**.

## `/sponsor-track-record` & `/sponsor-league` — the sponsor league table
Both rank every sponsor from the corpus (`data_public/sponsor_track_record.py`). Per sponsor: deal/realized counts, MOIC P25/P50/mean/P75, IRR median, hold years, **loss rate** (MOIC<1), **home-run rate** (MOIC>3), and the **consistency score (0–100)**:
```
consistency = 0.40·moic_score + loss_penalty + irr_score + cred_score
  moic_score   = min(100, (median_moic/2.0)·50)
  loss_penalty = 25·(1 − loss_rate)
  irr_score    = min(20, (median_irr/0.20)·20)   (neutral 10 if no IRR)
  cred_score   = min(15, n_deals·3)
```
`/sponsor-league` also leads with the **Return-vs-Consistency scatter** (P50 MOIC vs consistency, dashed refs at median consistency + 2.0×, dots colored green ≥2.0×-zero-loss / red ≥20% loss-rate). Each dot **and** each table row links through to `/diligence/sponsor-detail?sponsor=<name>` (that page shows the sponsor's realized-MOIC distribution + vintage timeline + per-deal list).

> Provenance caveat: the corpus is ~1,041 deal entries; only the ~55 "real" ones are partner-safe — the synthetic slice (extended_seed_2…104) is gated. League stats over the corpus inherit that split.

## `/payer-intelligence` — does payer mix predict outcomes?
From `data_public/payer_intelligence.compute_payer_intelligence(corpus)`:
- Corpus-wide payer-mix averages (commercial / medicare / medicaid / self-pay).
- **Correlation** of commercial %, medicaid %, self-pay % against realized MOIC — the "does payer mix predict outcomes" read.
- **Four payer-mix regime bands** (Gov-heavy / Balanced / Commercial-mix / Commercial) each with MOIC P25/P50/P75, IRR median, deal count, loss rate. This is the empirical basis for the reasonableness-band payer regimes used on the deal pages (§03).

---

## Where these numbers come from — summary
| Page | Number family | Source |
|---|---|---|
| `/portfolio`, `/portfolio/risk-scan` | portfolio-ops | live `deals`/`deal_snapshots`/`alerts`/`health_score` |
| `/portfolio/monitor` value creation | portfolio-ops | `initiative_actuals` via `initiative_portfolio_rollup` |
| `/portfolio-analytics`, sponsor, payer | corpus | `public_deals` realized-deal corpus |

---
*Next: `06_SCREENING.md` — how candidate hospitals are scored and ranked.*
