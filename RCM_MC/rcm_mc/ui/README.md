# UI

Server-rendered HTML pages for the web application. All pages use a shared design system (`_ui_kit`) with no external JavaScript framework -- everything is inline CSS/SVG/vanilla JS for offline compatibility.

| File | Purpose |
|------|---------|
| `analysis_workbench.py` | Bloomberg-style six-tab analyst workbench for a single deal (Overview, RCM Profile, EBITDA Bridge, Monte Carlo, Risk & Diligence, Provenance) |
| `dashboard_v2.py` | Morning view: four summary cards, "Needs Attention" action list, deal-card grid, and quick-action buttons |
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
| `csv_to_html.py` | Styled sortable HTML table renderer for short CSV files in the output folder |
| `json_to_html.py` | Schema-aware HTML renderers for PE JSON payloads (bridge, returns, covenant, hold grid) |
| `text_to_html.py` | Terminal-text-to-HTML converter with ANSI stripping, severity glyph coloring, and auto-linking |
| `_ui_kit.py` | Shared design system: one palette, one CSS bundle, one document shell for all HTML generators |
| `_html_polish.py` | HTML post-processor for numeric auto-alignment in tables across all generators |
| `_workbook_style.py` | Excel workbook styling helpers: header formatting, number formats, source-tag coloring, column widths |

## Key Concepts

- **No external dependencies**: Zero Chart.js, D3, or React -- everything renders with inline styles + SVG for offline, email, and Notion compatibility.
- **Shared design system**: `_ui_kit.py` provides a single palette and document shell so visual treatment stays consistent across all pages.
- **Dark theme workbench**: The analysis workbench uses a dense dark theme (`#0a0e17` background) with JetBrains Mono for numeric cells.
