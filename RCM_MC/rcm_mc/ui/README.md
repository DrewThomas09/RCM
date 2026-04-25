# UI

Server-rendered HTML pages for the web application. All pages use a shared design system (`_ui_kit`) with no external JavaScript framework -- everything is inline CSS/SVG/vanilla JS for offline compatibility.

## Pages

| File | Purpose |
|------|---------|
| `analysis_workbench.py` | Bloomberg-style six-tab analyst workbench for a single deal (Overview, RCM Profile, EBITDA Bridge, Monte Carlo, Risk & Diligence, Provenance) |
| `dashboard_v2.py` | Morning view: four summary cards, "Needs Attention" action list, deal-card grid, and quick-action buttons |
| `dashboard_v3.py` | **Story-driven morning view** (gated on `?v3=1`) — one IC narrative per deal across the daily roster, not a stat dump |
| `deal_profile_v2.py` | **Top-to-bottom investment narrative** in 9 sections (thesis → market → financials → operations → bridge → risk → exit → comps → recommendation) |
| `deal_comparison.py` | Side-by-side deal comparison with radar chart overlay and batch hospital screening page |
| `deal_timeline.py` | Unified vertical activity timeline pulling events from all deal-level state-change tables |
| `hold_dashboard.py` | Hold-period dashboard: initiative progress bars, actuals-vs-plan chart, quarterly scorecard, covenant monitor |
| `onboarding_wizard.py` | Five-step guided wizard: hospital name > auto-populate review > file upload > simulation > workbench |
| `portfolio_heatmap.py` | Portfolio health heatmap: deals as rows, metrics as columns, cells colored by percentile rank with trend arrows |
| `portfolio_map.py` | Geographic US SVG map with deal markers colored by stage, sized by EBITDA opportunity, states shaded by CON status |
| `pressure_page.py` | Pressure test page renderer for management plan stress-testing |
| `scenarios_page.py` | Scenario Explorer page for browsing and applying preset payer-policy shocks |
| `sensitivity_dashboard.py` | Interactive sensitivity page with parameter sliders and hold-period MOIC/IRR grid |
| `settings_pages.py` | Settings pages for custom KPIs, automation rules, and integration configuration |
| `source_page.py` | Deal sourcing page: thesis selector and ranked hospital results table |
| `surrogate_page.py` | Surrogate model page showing training status and feature schema |
| `data_catalog_page.py` | **Full data estate** at `/data/catalog` — every source, last-refresh, row counts, schema-drift status |
| `model_quality_dashboard.py` | **Backtest scoreboard** at `/models/quality` — every Ridge predictor's MAE / coverage / R² across i.i.d. and leave-one-cohort-out CV. TTL-cached |
| `feature_importance_viz.py` | **SVG feature-importance** at `/models/importance` — permutation + standardized-coef per model. TTL-cached |

## Components (cycle additions)

Reusable surface components introduced in the most recent loop cycle so every page renders the same way.

| Component | Purpose |
|-----------|---------|
| `power_table.py` | Sortable / filterable / exportable interactive table — single component used by every list-of-things surface. Server-side thousand-separators (`5,000 of 5,000`). Empty-state copy on every render |
| `power_chart.py` | Interactive SVG chart with hover / click / zoom / export. No Chart.js, no D3 |
| `colors.py` | **Semantic color system** — `positive / negative / watch / neutral / info` tokens. Replaces ad-hoc `#10B981` / `#EF4444` literals; one place to retheme |
| `metric_glossary.py` | Contextual tooltips on every metric drawn from a central glossary |
| `nav.py` | Breadcrumb component + Bloomberg-style keyboard shortcuts (`g d` deals, `g s` screening, `?` help) |
| `loading.py` | Skeleton screens, page-progress bar, inline spinners |
| `empty_states.py` | Empty-state component library with helpful CTAs (no blank pages — every empty state explains *why* and *what to do*) |
| `responsive.py` | Layout utilities for desktop / laptop / tablet breakpoints |
| `theme.py` | Persistent dark / light theme toggle (cookie-backed) |
| `compare.py` | Reusable side-by-side comparison surface with visual diff highlighting |
| `provenance_badge.py` | Click-to-explain provenance icon — shows source, methodology, confidence, as-of date for any modeled number |
| `global_search.py` | Search bar at `/api/global-search` over deals + metrics + analyses + pages |
| `preferences.py` | Per-user favorites, default view, notification preferences |
| `ui_kit.py` | **Canonical button / card / input / KPI helpers** so every form/page uses the same primitives. See [docs/UI_KIT.md](../../docs/UI_KIT.md) |
| `validators.py` | Form input validators with clear inline error messages |

## Foundation

| File | Purpose |
|------|---------|
| `csv_to_html.py` | Styled sortable HTML table renderer for short CSV files in the output folder |
| `json_to_html.py` | Schema-aware HTML renderers for PE JSON payloads (bridge, returns, covenant, hold grid) |
| `text_to_html.py` | Terminal-text-to-HTML converter with ANSI stripping, severity glyph coloring, and auto-linking |
| `_ui_kit.py` | Shared design system: one palette, one CSS bundle, one document shell for all HTML generators |
| `_html_polish.py` | HTML post-processor for numeric auto-alignment in tables across all generators |
| `_workbook_style.py` | Excel workbook styling helpers: header formatting, number formats, source-tag coloring, column widths |

## Key Concepts

- **No external dependencies**: Zero Chart.js, D3, or React — everything renders with inline styles + SVG for offline, email, and Notion compatibility.
- **Shared design system**: `_ui_kit.py` provides a single palette and document shell so visual treatment stays consistent across all pages.
- **Semantic colors not hex literals**: Components reference `colors.semantic.positive` etc., never `#10B981`. Retheming is one edit.
- **Empty states are first-class**: Every list/grid/chart has an empty-state render path with a CTA — never a blank pane.
- **Provenance everywhere**: Any modeled number carries a click-to-explain badge linking to source / methodology / confidence / as-of date.
- **Cache hot pages**: `/models/quality` and `/models/importance` use `infra/cache.ttl_cache` for >100,000× speedup on repeat loads.
