# 02 · Command Center (`/app`) — every number sourced

> The daily landing page. A partner opens PE Desk to `/app` and reads "what should I do today?" off it. This file documents **every block and where each number comes from** — and is candid about which numbers are live, which are Phase-2 placeholders, and which are currently **broken** (rendering `—` due to bugs worth fixing).

**Renderer:** `rcm_mc/ui/chartis/app_page.py` → `render_app_page` (line 80). **Hard 3-query budget per render:**
- `rollup = portfolio_rollup(store)` — portfolio aggregates
- `deals_df = latest_per_deal(store)` — one row per deal (latest snapshot), joined with `deals.name`
- `focused_packet` — the focused deal's `DealAnalysisPacket`, only when `?deal=<id>` is set

It is **not** a packet page by default — its numbers come from **portfolio state in SQLite**, not a per-deal packet (see `01_SYSTEM_FLOW` §4, case C). The page composes ~14 blocks through `editorial_chartis_shell`.

---

## The two data foundations

### `portfolio_rollup(store)` — `portfolio/portfolio_snapshots.py:295`
Aggregates `latest_per_deal` into the dict the dashboard reads:

| Key | Formula | Notes |
|---|---|---|
| `deal_count` | `len(latest_per_deal)` | total deals with a snapshot |
| `stage_funnel` | `{stage: count}` over `DEAL_STAGES` | from `df["stage"].value_counts()` |
| `weighted_moic` | **entry-EV-weighted mean** of per-deal MOIC over deals with `moic`+`irr`+`entry_ev` present, summed in `Decimal` | `None` if no sized deals |
| `weighted_irr` | same EV-weighting, stored as a **fraction** (0.219 = 21.9%) | `None` if none |
| `covenant_trips` | count of deals with `covenant_status == "TRIPPED"` | |
| `covenant_tight` | count with `covenant_status == "TIGHT"` | |
| `concerning_deals` | count with `concerning_signals >= 1` | |

`weighted_dpi` / `weighted_tvpi` **do not exist** anywhere — any UI that references them renders `—`.

### `latest_per_deal(store)` — `portfolio_snapshots.py:270`
One row per deal = the most recent `deal_snapshots` row (sorted desc, deterministic tiebreak on `snapshot_id`). Columns are the full snapshot schema: `stage, created_at, entry_ebitda, entry_multiple, exit_multiple, hold_years, moic, irr, entry_ev, exit_ev, covenant_leverage, covenant_headroom_turns, covenant_status, concerning_signals, favorable_signals, notes` + `name` (joined). **There is no `drift_pct` and no `headline` column** — remember this for the deals table below.

`covenant_status` is derived at snapshot-write time from covenant headroom: `SAFE if headroom>=1.0 turn, TIGHT if >=0, else TRIPPED`.

---

## Block-by-block

### 1. Page head (`editorial_page_head`)
| Element | Source |
|---|---|
| Eyebrow seg 1 | `PORTFOLIO & DILIGENCE` (partner) / `COMMERCIAL DILIGENCE` (consulting mode) |
| Eyebrow seg 2 | **`FUND II`** (partner) / `CLIENT ENGAGEMENT` (consulting) — *cosmetic label, not backed by a fund entity* |
| Title | static `Command center` |
| Meta `ID` / `STATUS` | static `CCF-FUND2` / `LIVE` |
| Meta `AS OF` | `deals_df["created_at"].max()` truncated to ISO date, or `—` when no deals |

### 2. "What this page does" (`render_what_block`)
- **Summary** (left): a static sentence (mode-swapped "hold-period"/"engagement").
- **SOURCES** (right): a **hard-coded** list — `portfolio.db, deal_snapshots, covenant_metrics, initiative_actuals, analysis_runs, generated_exports`. These are static labels, not introspected from live data.

### 3. KPI strip + return hero (`_app_kpi_strip.py`)
**Return hero** (the big number at the top):
- **Weighted MOIC** (38px) = `rollup["weighted_moic"]` → `f"{v:.2f}x"`.
- **Weighted IRR** (secondary) = `rollup["weighted_irr"]` → `f"{v*100:.1f}%"` (only shown when MOIC present).
- **Provenance line** = "Entry-EV-weighted across N sized deals · M excluded for missing EV" where N = `len(deals_df.dropna(subset=[moic,irr,entry_ev]))`.
- **Honest empty state:** no sized deal → big `—` + "Awaiting the first deal with a recorded entry EV…", no fabricated number.

**The 8 KPI cells** (`_value_for_kpi`):
| Cell | Source | Live? |
|---|---|---|
| Active deals | `rollup["deal_count"]` (⚠ **total**, not active-only despite the tooltip) | ✅ live |
| Weighted MOIC | `rollup["weighted_moic"]` (green ≥2.0x) | ✅ live |
| Weighted IRR | `rollup["weighted_irr"]` (green ≥20% / amber ≥15% / red) | ✅ live |
| Covenants at risk | `covenant_trips + covenant_tight` | ✅ live |
| Avg EBITDA drag | — | ⚠ **placeholder** (Phase-2 stub) |
| Avg DAR drag | — | ⚠ **placeholder** |
| Initiatives tracked | — | ⚠ **placeholder** |
| Avg days cash | — | ⚠ **placeholder** |

Cells 5–8 are explicit Phase-2 placeholders (the per-deal aggregates aren't in `portfolio_rollup` yet). Sparklines are globally off. The paired "7-QUARTER TRACK" table currently renders **only the current quarter's** weighted MOIC (one row), recomputed inline.

### 4. Quick access (`render_quick_access`)
Eight **static** cards (no data, no queries) linking to: `/analysis`, `/portfolio/heatmap`, `/diligence/ic-packet`, `/diligence/hcris-xray`, `/diligence/bridge-audit`, `/payer-intelligence`, `/ops`, `/module-index`.

### 5. Morning brief (`render_morning_brief`) — 4 glance panels
- **FNL (Pipeline funnel)** — bar per stage from `rollup["stage_funnel"]`. **Fixed (PR #497):** the panel's stage list was stale (`sourcing/screened/diligence/ic`) so `sourced`/`spa` deals were dropped; it now imports the canonical `DEAL_STAGES`.
- **CVN (Covenant status)** — Tripped / Tight / Safe bars; `safe = deal_count − trips − tight`.
- **SIG (Signal scan)** — Concerning vs Clean; `concerning = rollup["concerning_deals"]`.
- **DLS (Recent deals)** — up to 6 deals by `created_at` desc; name → `/deal/<id>`, stage, MOIC.

### 6. Metric catalog (`render_metric_catalog`) — "every number on this page"
A 4-column cross-reference (RETURNS / RCM DRAG / COVENANTS / INITIATIVES).
- **Simplified (PR #500):** the catalog now shows only the live **RETURNS** column (Weighted MOIC + IRR from the rollup). The deal-level RCM-DRAG / COVENANTS / INITIATIVES columns and DPI/TVPI were dropped — they couldn't be sourced from the data the catalog receives (covenant data lives in `covenant_metrics`, initiative variance needs `store`, DPI/TVPI are never computed), and that deal-level data is already shown live in the dedicated EBITDA-drag / covenant-heatmap / initiative-tracker blocks below.

### 7. Pipeline funnel (`render_pipeline_funnel`)
- Viz: one clickable bar per `DEAL_STAGES` stage; width = stage count / max stage count; click → `/app?stage=<stage>`.
- Paired conversion table: per stage, **conversion-to-prior** = `count / prior_stage_count`; first stage and zero-prior → `—`.
- Empty: "No deals yet" + zero-width bars.

### 8. Deals table (`render_deals_table`)
One row per deal (stage-filtered by `?stage=`). Columns and sources:
| Column | Source | Notes |
|---|---|---|
| Deal | `name` | links the whole row → `/app?deal=<id>` |
| Stage | `stage` | pill |
| EV | `entry_ev` | `$…M/B` |
| MOIC | `moic` | `x.xx` |
| IRR | `irr` | `%` |
| Covenant | `covenant_status` | SAFE/WATCH/TRIP pill |


> **Fixed (PR #498):** the table previously also had **Drift** and **Headline** columns that always rendered blank (the snapshot schema has neither field). They've been dropped — the table is now these 6 live columns.

### 9. Focused-deal bar (`render_focused_deal_bar`)
Hidden entirely unless `?deal=<id>`. Shows the focused deal's stage / EV / MOIC / IRR (from `focused_row`), export buttons (`/api/analysis/<id>/export?format=html|xlsx|json`), and prev/next switcher across held deals.

### 10. Covenant heatmap (`render_covenant_heatmap`) — 6 covenants × 8 quarters
- **Primary source:** the `covenant_metrics` table via `list_covenant_history(store, deal_id, name, limit=8)`. Each cell's band comes from `band_for_metric(value, threshold, watch_threshold, direction)` — direction-aware (lower-better vs higher-better). Cell label is the value in the covenant's unit (`x`/`d`/`%`).
- **Net Leverage legacy fallback:** when no `covenant_metrics` rows, reads `deal_snapshots.covenant_leverage` (last 8) and bands it `<=6.0 safe / <=6.5 watch / else trip`.
- Only Net Leverage is wired by default; a footnote says "X of 6 covenants tracked." Empty: "Select a deal…" / "Awaiting first quarterly snapshot."
- ⚠ The `source` tag reads `deal_snapshots` but the primary path is actually `covenant_metrics`.

### 11. EBITDA drag (`render_ebitda_drag`) — 5-component decomposition
Requires a focused deal's packet. **Correctly uses dataclass attribute access** (unlike the metric catalog).
- Reads `packet.ebitda_bridge.per_metric_impacts` (list of `MetricImpact{metric_key, ebitda_impact}`).
- Routes each impact into 5 buckets: Denial workflow gap (`denial_rate`, `first_pass_resolution_rate`, `clean_claim_rate`), Coding-CDI miss (`case_mix_index`), A/R aging (`days_in_ar`), Self-pay leakage (currently no key maps here → always 0%), Other.
- Per bucket: `pct = |bucket$| / Σ|impacts|`; dollars keep sign. Stacked bar + paired table.
- Empty: "Select a deal…" / "No bridge data yet. Run the analysis pipeline."

### 12. Initiative tracker (`render_initiative_tracker`)
Two modes:
- **Focused deal:** per-initiative variance from `initiative_variance_report(store, deal_id)` (cumulative actual vs library-plan EBITDA, `variance_pct`). **Fixed (PR #497):** the renderer previously read `actual_cumulative_M`/`plan_cumulative_M`/`initiative_name` (columns the report never emits), so rows showed zeroed actuals + blank names; it now reads the real `cumulative_actual`/`cumulative_plan`/`initiative_id` columns and resolves names from the initiatives library.
- **No focused deal (cross-portfolio):** `cross_portfolio_initiative_variance(store)` over held deals, trailing 4 quarters — per initiative: `n_deals`, `mean_variance_pct`, `total_actual_M`, `is_playbook_gap` (mean ≤ −10% AND ≥2 deals). Sorted by |mean variance|, top 10. This mode works correctly.

### 13. Alerts (`render_alerts`)
Cross-deal active alerts from `evaluate_active(store)` (each `Alert{kind, severity, deal_id, title, detail}`). Per card: severity icon + title + detail + a CTA routed by kind (covenant→Variance, drift→Playbook, stale→Source). Empty: affirmative "All clear. No active alerts. Last evaluated <UTC now>."

### 14. Deliverables (`render_deliverables`)
Recent export manifest. **Primary:** `generated_exports` table (`list_exports`, format/filepath/size/date). **Fallback:** recent `analysis_runs` rows when no exports. Cards link to `/exports/<path>` or `/analysis/<id>?run=<run_id>`. Empty: "No deliverables generated yet."

---

## Live vs placeholder vs broken — the honest summary

**Fully live (real data):** return hero (Weighted MOIC/IRR + provenance), KPI cells 1–4, pipeline funnel + conversion, morning brief (CVN/SIG/DLS), deals table (Deal/Stage/EV/MOIC/IRR/Covenant), covenant heatmap (Net Leverage; others when `covenant_metrics` populated), EBITDA drag (focused), cross-portfolio initiative tracker, alerts, deliverables.

**Phase-2 placeholders (intentionally `—`):** KPI cells 5–8 (Avg EBITDA drag / DAR drag / Initiatives tracked / Avg days cash), the 7-quarter sparkline track.

**Fixed since the first pass** (found while documenting):
- ✅ **Deals table** Drift + Headline columns dropped (PR #498) — no backing fields, can't be computed in budget.
- ✅ **Focused initiative tracker** now reads the real `cumulative_actual`/`cumulative_plan`/`initiative_id` columns + resolves names (PR #497).
- ✅ **Morning-brief FNL** now uses the canonical `DEAL_STAGES` so `sourced`/`spa` show (PR #497).

- ✅ **Metric catalog** simplified to the live RETURNS column (PR #500); the un-sourceable deal columns + DPI/TVPI were dropped. The deal-level data is shown live in the dedicated blocks below.

**All `/app` dead-column defects found during this documentation pass are now resolved.**

---
*Next: `03_DEAL_PAGES.md` — the per-deal surfaces, where the numbers DO come from a packet.*
