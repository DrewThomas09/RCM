# UI Kit Reference

The recent sprint shipped a layered UI system. This document is the reference
index — start here when you need to know which module to import, what's
already built, and which commit introduced it.

## Layout

```
rcm_mc/ui/
├── colors.py            ← semantic palette (positive/negative/watch)
├── ui_kit.py            ← canonical button / card / input / KPI helpers
├── theme.py             ← dark/light toggle + CSS variables
├── responsive.py        ← viewport meta + breakpoint utilities
├── loading.py           ← skeletons + spinners + page progress bar
├── empty_states.py      ← empty-state cards + 6 pre-built variants
├── nav.py               ← breadcrumbs + keyboard shortcuts (g d / g m)
├── metric_glossary.py   ← 16 metric definitions + hover tooltips
├── provenance_badge.py  ← click-to-see source / confidence
├── validators.py        ← form input validators + clear error messages
├── compare.py           ← side-by-side comparison (visual diff)
├── power_table.py       ← sortable + filterable + exportable table
├── power_chart.py       ← interactive SVG (hover/click/zoom/export)
├── global_search.py     ← / focus, /api/global-search backend
├── data_catalog_page.py ← /data/catalog page
├── model_quality_dashboard.py  ← /models/quality page
├── feature_importance_viz.py   ← /models/importance page
├── dashboard_v3.py      ← /?v3=1 morning view (4-section narrative)
└── deal_profile_v2.py   ← /deal/<id>/profile (9-section IC memo)
```

## When to use what

### I'm rendering a button
→ `ui_kit.button(label, href=..., kind='primary'|'secondary'|'ghost')`.
Don't write inline `style="background:#1f2937;..."` ever again.

### I'm rendering a colored status indicator
→ `colors.status_color(value, low_threshold, high_threshold,
lower_is_better=True)` for threshold-band coloring,
`colors.peer_color(value, peer_p50)` for peer comparison,
`colors.severity_color('critical')` for severity strings,
`colors.status_badge(label, kind)` for HTML pills.

### I'm rendering a wide data table
→ `power_table.render_power_table(table_id, columns, rows)`. Get
sort/filter/search/CSV-export/column-toggle for free.

### I'm rendering a chart
→ `power_chart.render_power_chart(chart_id, series, y_kind=...)`. Hover
tooltips, click-drilldown, drag-to-zoom, SVG/PNG export — no chart libraries
needed.

### A page has no data yet
→ `empty_states.empty_state(title, description, actions=[...])` or one of
the 6 pre-built variants (`no_data_loaded`, `no_packets_built`,
`no_models_trained`, `no_filter_results`, `no_search_results`,
`feature_disabled`).

### A long operation is loading
→ `loading.skeleton_table(rows, cols)` for placeholders;
`loading.page_progress_bar()` for top-of-page Stripe-style indicator;
`loading.loading_overlay(label)` for full-screen modals.

### A form needs input validation
→ `validators.validate_form(spec, values)` returns `FormResult` with
`cleaned` values + per-field `errors` map. Render errors with
`validators.render_field_error(message)` (red, role=alert, HTML-escaped).

### A page should have a back-link
→ `nav.breadcrumb([(label, href), ...])` — last item non-clickable, parents
linked, chevron separators.

### A keyboard shortcut should fire
→ `nav.keyboard_shortcuts()` registers the standard set: `g d` →
dashboard, `g c` → catalog, `g m` → models, `g i` → importance,
`g r` → refresh, `g e` → exports, `?` → help, `/` → focus
search, `Esc` → cancel.

### A metric needs a contextual tooltip
→ `metric_glossary.metric_tooltip(metric_key, value=...)` — 16 metrics
already in the glossary (denial_rate, days_in_ar, net_collection_rate,
clean_claim_rate, cost_to_collect, FPRR, operating_margin, ebitda_margin,
case_mix_index, days_cash_on_hand, debt_to_revenue, interest_coverage,
occupancy_rate, fte_per_aob, labor_pct_of_npsr, payer-mix shares).
Use `metric_glossary.define_metric(...)` to register a new one at runtime.

### A modeled number needs a source/methodology disclosure
→ `provenance_badge.provenance_badge(data_point, value_html=...)`.
Maps `Source` enum → glyph icons; click expands a `<details>` card with
source, methodology, confidence band, sample size, upstream chain.

### Comparing two or more entities
→ `compare.compare_hospitals(hospitals, metrics)` for the canonical
7-metric RCM scan, `compare.compare_scenarios(scenarios, metrics,
reference_index)` for bull/base/bear comparisons. Green ▲ winner arrows
+ signed deltas vs reference column.

### Search across the platform
→ `global_search.render_search_bar()` returns the input + JS that hits
`/api/global-search`. To add new searchable surfaces, append a
source function to `DEFAULT_SOURCES`.

## Cross-cutting infrastructure

### Constants & ranges
`rcm_mc/constants.py` — every cross-cutting magic number with a docstring.
Sanity ranges (DENIAL_RATE_RANGE, DAYS_IN_AR_RANGE, etc.), distress
thresholds, freshness bands, cache TTLs, UI breakpoints, peer comparison
significance band, ML training defaults.

### Caching
`rcm_mc/infra/cache.py` — `ttl_cache(seconds=300)` decorator. Expensive
deterministic operations (model_quality + feature_importance default
panels) cache for 5 min, getting >100,000× speedup on warm hits.

### Theme + responsive
- `theme.theme_init_script()` at the top of `<head>` runs *before* paint
  so users with light-mode preference don't see a dark→light flash.
- `theme.theme_stylesheet()` provides CSS variables for both modes.
- `theme.theme_toggle()` is the user-facing toggle button.
- `responsive.viewport_meta()` is the canonical mobile-friendly tag.
- `responsive.responsive_stylesheet()` provides class-based utilities
  (`.rs-container`, `.rs-grid`, `.rs-table-wrap`, etc.).

## Routing additions (server.py)

| Route | Module |
|---|---|
| `/?v3=1` (or `RCM_MC_DASHBOARD=v3`) | dashboard_v3 |
| `/deal/<id>/profile` | deal_profile_v2 |
| `/data/catalog` | data_catalog_page |
| `/models/quality` | model_quality_dashboard |
| `/models/importance` | feature_importance_viz |
| `/api/global-search?q=...` | global_search.search |

## Testing surface

The recent sprint shipped extensive test coverage. By module:

| Module | Tests | Notes |
|---|---|---|
| colors | 26 | Threshold + peer + change + severity coloring |
| ui_kit | 20 | Button + card + input + KPI helpers |
| theme | 13 | CSS variables + toggle + flash-prevention init script |
| responsive | 11 | Viewport meta + utility classes |
| loading | 21 | Skeletons + spinners + page progress |
| empty_states | 19 | 6 variants + base renderer |
| nav | 15 | Breadcrumbs + shortcut payload |
| metric_glossary | 14 | 16 metrics + tooltip rendering |
| provenance_badge | 13 | 7 sources + confidence bands |
| validators | 36 | 10 single-field + form orchestration |
| compare | 21 | Visual diff + winner arrows |
| power_table | 18 | Sort + filter + export + column toggle |
| power_chart | 16 | Hover + click + zoom + export |
| global_search | 15 | Source plugin + scoring |
| dashboard_v3 | 16 | Hero strip narrative + 4 sections |
| deal_profile_v2 | 15 | 9-section IC memo |
| model_quality_dashboard | 15 | Backtest panel + calibration badges |
| feature_importance_viz | 15 | SVG bar charts |
| data_catalog_page | 10 | Live SQL inventory |
| preferences | 17 | Favorites + custom widgets + notifications |
| constants | 17 | Sanity bounds + breakpoint consistency guard |

Plus end-to-end and resilience suites:

| Suite | Tests | Purpose |
|---|---|---|
| api_endpoints_smoke | 20 | No-500 sweep across routes |
| empty_data_resilience | 21 | Every page handles missing data gracefully |
| extreme_values_resilience | 24 | Giant/tiny/zero/100% inputs to all ML models |
| exports_end_to_end | 12 | Excel/PowerPoint/HTML/Markdown round-trips |
| screening_workflow | 26 | Filter → sort → drill → back |
| ebitda_bridge_workflow | 16 | Build → adjust → compare → export |
| comp_engine_workflow | 21 | Select → view → defend → override |
| data_pipeline_resilience | 18 | Missing/empty/garbage CSV inputs |
| full_pipeline_10_hospitals | 9 | 10 archetypes × full ML pipeline |

## What's intentionally NOT here

- **Brand identity** — `brand.py` owns the SeekingChartis logo, palette,
  typography. Branding is identity; status colors are information. They
  don't share a module.
- **Auth** — `rcm_mc/auth/auth.py` owns multi-user authentication
  (scrypt + sessions + roles). The recent sprint touches `username`
  via `preferences.py` but doesn't change auth.
- **Data ingestion** — `rcm_mc/data/*.py` owns the CMS + Census + CDC
  + APCD + HCUP loaders. The recent sprint added several
  (census_demographics, cdc_places, state_apcd, ahrq_hcup,
  cms_ma_enrollment) but they're separate from the UI kit.
- **ML predictors** — `rcm_mc/ml/*.py` owns the trained models + helpers
  (denial_rate, days_in_ar, collection_rate, forward_distress,
  improvement_potential, regime_detection, payer_mix_cascade,
  geographic_clustering, contract_strength, ensemble_methods,
  service_line_profitability, volume_trend_forecaster). The UI kit
  consumes their outputs, doesn't define them.

## Style invariants enforced by tests

These are the contracts the recent sprint locked in:

1. **No new runtime dependencies.** Pure stdlib + numpy + pandas +
   matplotlib + openpyxl. Every UI helper is HTML+CSS+vanilla JS.
2. **HTML-escape every user-supplied string.** All renderers wrap label
   strings in `html.escape()`; tests verify `<script>` payloads survive
   as `&lt;script&gt;`.
3. **Empty-state copy on every list/chart/dashboard.** No blank pages.
   Tests verify each surface has the expected empty-state phrase.
4. **No 500s on garbage input.** Garbage query strings, special-char
   path components, 1000-char queries — all return 200/4xx, never 500.
5. **Sanity-range clamps on every predictor.** Predictions are bounded
   to plausible economic ranges; tests verify no inf / NaN ever escapes.
6. **Conventional commits.** `type(scope): subject`. Body explains
   *why*, not what — the diff already shows what.

For more detail on any module, read its docstring — every recent file
opens with a paragraph explaining what it ships, why it exists distinct
from any pre-existing module, and the public API it exports.
