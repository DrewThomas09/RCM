# UI

Server-rendered HTML pages for the PE Desk web app. The
v5 editorial design system replaces the legacy Bloomberg dark
shell — every partner-facing page builds against `_chartis_kit.py`
and renders through `chartis_shell()`. No external JS framework;
small vanilla-JS shims for CSRF / palette / dropdown / breadcrumbs.

**Design language**: navy `#0b2341` topbar + parchment `#f5f1ea`
body + teal `#155752` accents + near-ink `#1a2332` text. Source
Serif 4 (display + body), Inter Tight (UI + sans), JetBrains Mono
(numerics + eyebrows). Editorial cadence (eyebrow + serif H1 +
meta + body + table) borrowed from chartis.com.

**Top nav**: Home / Pipeline / Diligence / Library / Research /
Portfolio. Each section has a sub-nav rail with pinned secondary
links. Breadcrumbs auto-derive from the request path. Cmd+K
opens a 69-surface command palette over every analytic tool.
A toast/flash system confirms state-changing POSTs.

For a list of every page renderer see [Pages](#pages) below.
For the editorial primitives a new page should reach for see
[Editorial Kit](#editorial-kit-_chartis_kitpy).

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

---

## Editorial Kit (`_chartis_kit.py`)

The chartis-editorial design system that replaces the legacy
Bloomberg dark shell. Every new partner-facing page should
build with these primitives. Pages that don't are scored by
`tools/v5_fidelity_audit.py` (run
`python tools/v5_fidelity_audit.py` to see the leaderboard).

### Shell

| helper | purpose |
|---|---|
| `chartis_shell(body, title, **kwargs)` | Full-page wrapper — navy topbar, italic-serif wordmark, teal accent, breadcrumbs. Drop-in replacement for legacy `shell()`. |

Key kwargs: `active_nav`, `breadcrumbs`, `subtitle`, `extra_css`, `editorial_intro` (cycle 20 — auto-prepends a `ck_section_intro` block), `show_chrome`, `show_sidebar`.

### Editorial primitives — building blocks for new pages

| helper | purpose |
|---|---|
| `ck_eyebrow(text, *, on_navy=False)` | Caps-mono label with teal rule. The chartis cadence anchor. |
| `ck_section_intro(eyebrow, headline, *, italic_word, body)` | Italic-serif highlight headline ("Where the portfolio *needs* attention"). Pairs the eyebrow with a serif h2 + optional body. |
| `ck_section_header(title, eyebrow=None, count=None)` | Smaller than intro — eyebrow + h2 + optional row count badge. |
| `ck_arrow_link(text, href)` | Teal "READ MORE ↗" CTA. |
| `ck_image_card(image_html, eyebrow, title, body, cta_text, cta_href)` | chartis.com-style image-top editorial card. |
| `ck_panel(body, *, title, code)` | White panel with navy header strip + optional `[CODE]` debug tag. |

### Page-level chrome

| helper | purpose |
|---|---|
| `ck_page_title(title, *, eyebrow, meta)` | **The H1 of every editorial page.** Eyebrow + serif title + optional faint mono meta line. Used on /library, /watchlist, /lp-update, /alerts, every /diligence sub-page, /tools, error pages. |
| `ck_empty_state(title, body, *, eyebrow, icon, cta_label, cta_href, tone)` | Editorial empty-state card — eyebrow + icon-in-bone-circle + serif title + body + optional primary CTA. Tone variants: neutral / positive / warning. Sits where a list / table / chart has no data. |

### Severity / status

| helper | purpose |
|---|---|
| `ck_severity_panel(*, tone, label, count, rows_html)` | Toned panel (red / amber / info / positive / neutral) for alerts and escalations. |
| `ck_signal_badge(text, *, tone)` | Inline pill badge — positive / warning / negative / critical / neutral. |
| `ck_affirm_empty(*, headline, body, cta_text, cta_href)` | Affirmative empty-state band — for "all clear" success states. Use `ck_empty_state` for "no data yet"; use this for "nothing to worry about". |

### Insights triplet (`/library`, `/notes`, `/research`, `/escalations`)

| helper | purpose |
|---|---|
| `ck_search_hero(*, action, name, initial, label, placeholder, extra_hidden)` | Navy hero panel with italic "Search" label + circular submit + teal chevron. |
| `ck_filter_sidebar(*, groups, form_action, ...)` | Eyebrow-rail filter list with `<details>` "More" expander when groups exceed `more_threshold`. |
| `ck_results_header(*, count, label, chips, clear_all_href)` | N RESULTS header with active-filter chips (one anchor per chip) + Clear all teal arrow. |
| `render_insights_page(*, action, state, facets, count, body_html, title, intro, ...)` | **Composed helper** — wraps the above three plus `chartis_shell` in one call. Use this for any new content-listing page. Caller provides the items as `body_html`; the chrome is composed for free. |

### Tables / KPIs / cells

| helper | purpose |
|---|---|
| `ck_kpi_block(label, value, sub=None, trend=None, *, code=None)` | Editorial KPI block with optional subtext + trend tone. Accepts the legacy 4-positional form. |
| `ck_kpi_grid(...)` | (use `<div class="ck-kpi-grid">…</div>` directly) |
| `ck_table(rows, columns, *, dense=False)` | Bloomberg-density table with tabular-nums numerics. |
| `ck_data_cell(value, *, align, mono, tone, weight, is_header=False)` | **Cycle 22** — one styled `<td>` (or `<th>`) for the data_public table archetype. Replaces ~200B inline-style attrs with ~30B class attrs. Use this for any new table cell. |

### Numeric formatting

| helper | purpose |
|---|---|
| `ck_fmt_currency(v, *, precision, dash)` | `$450K` / `$1.20M` / `$1.50B` auto-bucketed by magnitude. |
| `ck_fmt_percent(v, *, precision, dash)` | `15.3%` (1 decimal default). |
| `ck_fmt_number(v, *, precision, dash)` | Plain number with thousands separator. |

### Command palette

| helper | purpose |
|---|---|
| `ck_command_palette(modules)` | ⌘K palette popover — feed it the module catalog. Keyboard-driven nav. |

## Migration tools (`tools/`)

| script | purpose |
|---|---|
| `tools/v5_fidelity_audit.py` | Per-renderer chartis-grade scoring. `--md docs/V5_FIDELITY_REPORT.md` to refresh the leaderboard. |
| `tools/bulk_add_intros.py` | Mechanical addition of `editorial_intro` kwarg to existing `chartis_shell` calls. |
| `tools/migrate_inline_cells.py` | Mechanical rewrite of inline-styled `<td>` cells to `ck_data_cell` calls. |
| `tools/azure_smoke.py` | Post-Azure-deploy verification — `/healthz` + `/login` round-trip + `/app` chrome assertion. |

## Authoring conventions

When building a new partner-facing page:

1. **Always use `chartis_shell` or `render_insights_page`** — never roll your own layout.
2. **Open with `ck_page_title`** — every editorial page should start with an H1 block (eyebrow + serif title + meta). Don't ship a bare `<h2>`.
3. **Italic-serif intro is opt-in** — `ck_section_intro` and the `editorial_intro` kwarg are still supported but are hidden by default; they only render when a partner toggles "Tutorial intros: on" in the user dropdown. Don't rely on them for primary chrome.
4. **No inline styles** — use the kit's utility classes (`ck-cell`, `tone-dim`, `ck-kpi-grid` etc.) or write a class in `_CSS_INLINE_FALLBACK`.
5. **Helper-first for tables** — prefer `ck_data_cell` over hand-rolled `<td>`; prefer `ck_table` for simple tables; prefer `render_insights_page` for content-listing pages.
6. **Editorial empty states** — use `ck_empty_state` (icon + title + body + CTA) for "no data yet"; use `ck_affirm_empty` for "nothing to worry about". Never a bare `<p class="muted">No items</p>`.
7. **Hook `active_nav`** — pass the section path (e.g. `active_nav="/diligence/benchmarks"`) so the sub-nav rail's active-pill highlight and breadcrumb chain resolve correctly.
8. **Accept the audit score** — run `python tools/v5_fidelity_audit.py` after adding a new page; aim for ≥70.

For the editorial fidelity rationale (chartis.com cadence, palette, typography), see `docs/CHARTIS_MATCH_NOTES.md`. For the campaign log of what shipped when, see `docs/EDITORIAL_POLISH_LOG.md`.
