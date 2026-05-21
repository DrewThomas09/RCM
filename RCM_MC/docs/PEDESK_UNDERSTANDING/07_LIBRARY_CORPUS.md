# 07 · Library & corpus — the empirical base

> Every benchmark, percentile, comparable, and "P50" in PE Desk ultimately rests on two bodies of data: the **realized-deal corpus** (`public_deals`) and the **CMS public-data benchmarks** (`hospital_benchmarks`). This file documents those surfaces and exactly what they're built from — so when a page says "peer P50 MOIC = 1.9×," you know which deals that came from.

---

## `/library` — the realized-deal corpus
The browsable corpus (`data_public/deals_library_page.py`), ~**1,041 deal entries** loaded into `public_deals`. Each deal: source_id, name, year, buyer, seller, EV ($M), entry EBITDA ($M), hold years, **realized MOIC**, **realized IRR**, payer mix, notes. Filters: sector / regime / MOIC bucket / search. Rows drill to `/library/<source_id>` (corpus-deal detail).

> **Critical provenance fact (must surface to any partner):** the corpus is split — `_SEED_DEALS` (~35) + `extended_seed` are tagged **"real"** (sourced from SEC filings / press releases / investor decks); `extended_seed_2`…`extended_seed_104` are tagged **"synthetic"** (a spot-check found fabrications, so the whole range is flagged synthetic and **must not be shown to partners as real**). The canonical loader `corpus_loader.load_corpus_deals(mode="all"|"real"|"synthetic")` injects a `provenance` field on every row. Any league/benchmark stat inherits this split. (Some docstrings cite "~1,815 deals / ~55 real" — the on-disk count is ~1,041; use the verified number.)

## `/comparables` — comparable transactions
Given a target profile (sector + EV + EBITDA + year), `deal_comparables_enhanced.find_enhanced_comps` returns the most-similar realized deals. **Weighted similarity (0–1):**
```
similarity = 0.30·EV_logscale + 0.30·payer_mix_cosine + 0.20·vintage + 0.20·deal_type_jaccard
  EV_sim      = exp(−|ln(ev_a) − ln(ev_b)|)
  payer_cosine= cosine over [medicare, medicaid, commercial, selfpay]
  vintage     = exp(−|Δyear|/3)
  deal_type   = Jaccard over name tokens
```
Missing dimensions get a neutral 0.5. The page leads with the **Entry-Multiple × Realized-MOIC scatter** (x = EV/EBITDA, y = realized MOIC, y=1.0× break-even line, target's multiple as a dashed vertical; dots green ≥3.0× / red <1.0×, click through to `/library/<source_id>`). Also computes `leverage_adj_moic` (de-levers realized MOIC to a notional 5× benchmark) and peer-group percentiles ranking the target among comps.

## `/comparable-outcomes` (`/diligence/comparable-outcomes`)
Same corpus matching, framed as "what would this trade for?" — surfaces the matched peers + their MOIC/IRR outcome distribution, with a target-MOIC percentile vs peers. Deal names link to `/library/<source_id>`. JSON/CSV/memo exports available.

## `/rcm-benchmarks` — the RCM KPI benchmark bands
P25/P50/P75 bands for the core RCM metrics (denial rate, clean-claim rate, days-in-A/R, net collection rate, write-off, cost-to-collect), **segmented by hospital-type** (`chartis/rcm_benchmarks_page.py` via `data_public/rcm_benchmarks.get_all_benchmarks()`). These bands are the targets the EBITDA bridge's `suggest_targets` reaches for (§03), and the bands the diligence benchmarks tab (§04) compares a target's KPIs against. A small-multiples chart grid renders one bar chart per metric across segments.

## `/market-rates` — reimbursement rates
Market reimbursement rates grouped by sector / payer / region (`data_public/market_rates_page.py`) — the rate context behind the payer-stress and value-bridge-v2 method-mix math.

## `base_rates` (corpus-derived, surfaced across pages)
`data_public/base_rates.py` computes P25/P50/P75 of realized MOIC/IRR **segmented** by size (small <$500M EV, medium $500M–$3B, large >$3B), dominant payer, deal type, and buyer. **Percentiles, not means** — hospital returns are fat-tailed, so a median + IQR is the honest summary. These base rates are what the reasonableness IRR bands (§03) and the value-anchoring on analytic pages are calibrated against.

## CMS public-data benchmarks (`hospital_benchmarks`)
The other empirical base — the unified store of CMS HCRIS / Care Compare / Utilization / IRS 990 / POS / HRRP metrics, keyed `(provider_id, source, metric_key, period)` (full detail in `PEDESK_DATA.md`). This is what makes a hospital analyzable from public data alone: the predictive screener (§06), HCRIS X-Ray (§04), and a deal's initial observed metrics (§01 §6) all read from here. Freshness is tracked in `data_source_status`; refresh via `rcm-mc data refresh`.

---

## The chain, end to end
- A **benchmark P50** on any page → `rcm_benchmarks` or `base_rates` → computed over the corpus / CMS data → percentile, segmented.
- A **comparable's MOIC** → `public_deals` realized-deal corpus → matched by weighted similarity.
- A **hospital's margin/beds/payer-mix** → `hospital_benchmarks` → CMS HCRIS filing.

Every one of these is tagged BENCHMARK / HCRIS / COMPUTED so a partner reading the page knows it's an empirical base rate or a public filing, not a seller claim. And the synthetic slice of the corpus is gated from partner-facing views.

---
*This completes the per-section deep dives. Back to `00_INDEX.md` for navigation; `01_SYSTEM_FLOW.md` for the mechanism that ties the per-deal pages together.*
