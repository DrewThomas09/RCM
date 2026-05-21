# 14 · Research, market intel & the analytic tooling

> The remaining surfaces: the Research section (curated research, market intel, news), the model/quant tooling (scenarios, calibration, quant-lab, model-validation, surrogate, pressure), and the multiple dashboard generations. Rounds out "every page."

---

## Research section
- **`/research`** (`research_page.py`) — a curated research catalog using the "insights" triplet (search hero + filter rail + results); `?q/topic/kind`. Catalog content, not a computation.
- **`/market-intel`** (`market_intel_page.py`) — public healthcare comps + PE news, filterable (category/specialty/EV/revenue/tickers/tags). `/market-intel/seeking-alpha` is a sub-view. Public market context.
- **`/news`**, **`/conferences`** — healthcare PE news + conference catalogs.
- **`/comparable-outcomes`**, **`/regulatory-calendar`**, **`/bear-cases`**, **`/backtest`**, **`/corpus-backtest`** also surface here (covered in §03/§04/§07): the corpus-backtest cross-matches platform forecasts vs corpus realized MOIC/IRR (falls back to corpus self-analysis).

## Model & quant tooling
These are the engine-tuning and validation surfaces — where you inspect/calibrate the math itself rather than a deal.

| Page | What it is |
|---|---|
| **`/model-validation`** | The prediction backtest scorecard: per-metric R², 90%-CI coverage, MAE, grade. Shows the **Accuracy-vs-Reliability scatter** (R² × coverage). **Honest disclaimer:** when no live prediction ledger exists, the scorecard is a *synthetic backtest* on HCRIS data and says so plainly (it does not present synthetic numbers as live validation). |
| **`/models/quality`, `/models/importance`** | Model quality dashboards (R²/coverage; feature importances). |
| **`/quant-lab`** | The quant workbench for the prediction/regression stack. |
| **`/calibration` / `/calibrate`** | Calibrate predictions against priors (`calibration_page.py`) — closes the loop from realized runs back into the simulator priors (`store.export_priors`). `/api/calibration/priors`. |
| **`/scenarios`** | Scenario builder/explorer (`scenarios_page.py`); `/api/scenarios`. |
| **`/surrogate`** | Surrogate-model explorer (`surrogate_page.py`); `/api/surrogate/schema`. |
| **`/pressure`** | Pressure-test view (`?deal_id=`). |
| **`/runs`, `/cli-runs`** | Run history (the `runs` table; `primitives_json` per-payer priors feed calibration). |
| **`/data/refresh`, `/data/catalog`, `/cms-sources`, `/cms-data-browser`** | Data-source admin + CMS catalog/browser; `/admin/data-sources`. |

These read the prediction ledger (`predictions`/`prediction_actuals`/`model_performance_log`), the run history (`runs`), and CMS data — all documented in `PEDESK_DATA` and `PEDESK_ALGORITHMS`.

## Dashboard generations (which homepage you get)
PE Desk has shipped several home/dashboard variants, gated by query flags + auth + the `CHARTIS_UI_V2` env:
- **`/app`** — the editorial Command Center (the current primary; §02). `/` redirects authenticated editorial users here.
- **`/dashboard`** — `dashboard_v3` (default) → auto-upgrades to `v2` when analysis packets exist; `?v2` / `?legacy` select older generations.
- **`/home` / `/seekingchartis`** — a seven-panel partner home (falls back to `command_center` then `home_v2` if the panel set fails — the fallback chain noted in `02`).
- **Anonymous `/`** → the public marketing splash (`marketing_page.py`).

For a partner the practical answer is: **you land on `/app`**. The other generations are legacy/transitional and selectable via flags.

---

## Where these numbers come from
- Research/market-intel/news → curated catalog + public market data (not the deal corpus, not packets).
- Model tooling → the prediction ledger, run history, and CMS data — the same engines documented in `PEDESK_ALGORITHMS`; these pages *inspect* the math rather than produce deal numbers.
- Dashboards → portfolio state (the same `portfolio_rollup`/snapshot reads as `/app`, §02).

---
*This completes the per-surface deep reference (00–14). Material product findings surfaced during the tracing — the `/app` Command Center dead columns and the data_public curated-vs-live split — are noted in `02` and `08` respectively, for separate fix decisions.*
