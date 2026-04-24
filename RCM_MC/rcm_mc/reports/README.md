# Reports

Report generation across multiple formats: HTML, Markdown, PowerPoint, and narrative text. Ranges from the full audit-grade HTML report to the one-page partner brief.

---

## `reporting.py` — Core Reporting Utilities

**What it does:** Shared utility layer for all report generators: distribution summarization, metric label lookups, financial number formatting, summary table building, and matplotlib chart generation.

**How it works:** Provides: `pretty_money(value)` → `"$12.50M"` (2dp dollar format); `summary_table(results)` → pandas DataFrame formatted for terminal or HTML; `plot_ebitda_drag_distribution(result)` → matplotlib figure with drag distribution histogram and P10/P50/P90 markers; `plot_denial_drivers_chart()` → horizontal bar chart; `plot_deal_summary()` → multi-panel deal KPI summary; `waterfall_ebitda_drag()` → bridge waterfall SVG. `METRIC_LABELS` dict maps canonical metric keys to display strings. `strategic_priority_matrix()` ranks initiatives by impact × urgency. `actionable_insights(result)` and `assumption_summary(result)` build the narrative sections. All matplotlib figures are generated server-side as SVG bytes (no browser rendering required).

**Data in:** `SimulationResult` and `DealAnalysisPacket` objects from the analysis layer.

**Data out:** Formatted strings, pandas DataFrames, and matplotlib figures consumed by all other report modules.

---

## `html_report.py` — Client-Ready HTML Report

**What it does:** Generates a complete, client-facing HTML analysis report with executive-facing sections, bridge visualization, and MC distribution charts. Suitable for emailing to management teams.

**How it works:** Sections: executive summary (deal name, key KPIs), bridge waterfall chart (SVG from `reporting.py`), MC distribution histogram and P10/P50/P90 table, risk flags summary, top diligence questions, and next-steps. Uses `_report_css.py` for inline styles and `_report_sections.py` for static HTML scaffolding. All numbers formatted per CLAUDE.md conventions. Wraps in the `_ui_kit.py` shell when served via HTTP, or as a standalone HTML file for email/download.

**Data in:** `DealAnalysisPacket` from `analysis/analysis_store.py`; generated charts from `reporting.py`.

**Data out:** HTML string for `GET /api/deals/<id>/report` and download.

---

## `full_report.py` — Comprehensive Audit-Grade HTML Report

**What it does:** The complete technical report including all input parameters, config reference, numbers source map, and calibration details. Used for internal analyst reference and audit, not client delivery.

**How it works:** Extends `html_report.py` with additional sections: full input config (YAML rendered as HTML table), per-metric source map (observed vs. predicted vs. benchmark), calibration parameters and posterior summaries, provenance graph visualization, backtester coverage stats, and a full-width comparison table of all scenarios. Very long (~50 sections) — paginated in the browser. Uses `infra/provenance.py` manifest for the source map.

**Data in:** `DealAnalysisPacket`; raw config YAML; calibration report from `core/calibration.py`; provenance manifest from `infra/provenance.py`.

**Data out:** Long-form HTML string for `GET /api/deals/<id>/full-report`.

---

## `markdown_report.py` — GitHub-Flavored Markdown Report

**What it does:** The same key sections as `html_report.py` but formatted as GitHub-flavored Markdown. Used for deal notes in GitHub-based deal tracking workflows and for pasting into Notion.

**How it works:** Mirrors `html_report.py` section structure. Tables are rendered in GFM pipe format. Charts are omitted (Markdown can't embed SVG inline) — replaced with P10/P50/P90 text tables. Metric values in bold for easy scanning. Starts with a YAML frontmatter block for metadata (deal_id, run_id, built_at, analyst).

**Data in:** `DealAnalysisPacket`; no charts generated.

**Data out:** `.md` string for `GET /api/deals/<id>/report?format=md`.

---

## `narrative.py` — Natural-Language Simulation Summary

**What it does:** Generates a 3-paragraph plain-English narrative summarizing the simulation results for a non-technical reader (LP, management team, board member).

**How it works:** Template-driven: paragraph 1 summarizes the deal and key metrics in plain language ("Acme Health is a 350-bed regional hospital currently running a 13.2% denial rate, placing it in the bottom quartile for its peer group."); paragraph 2 explains the improvement opportunity and confidence ("If denial management, AR optimization, and CMI uplift initiatives are executed to plan, EBITDA is projected to improve by $X–$Y at P25–P75, representing a X× MOIC at exit."); paragraph 3 provides risk context ("The primary uncertainty is execution pace on payer renegotiation, which accounts for 38% of the return variance."). All dollar amounts and percentages pulled directly from the packet — no inference.

**Data in:** `DealAnalysisPacket` for metric values, distribution summaries, and variance attribution.

**Data out:** Narrative string for the deal overview page and LP update.

---

## `pptx_export.py` — 5-Slide IC Deck (requires python-pptx)

**What it does:** Generates a 5-slide PowerPoint IC deck: (1) Deal Overview, (2) RCM Profile and Opportunity, (3) EBITDA Bridge, (4) Monte Carlo Returns Distribution, (5) Risk Summary and Diligence Questions.

**How it works:** Requires `python-pptx` (optional dependency). Uses a built-in blank template with Chartis blue accent. Each slide is built programmatically: text boxes for metrics, matplotlib charts embedded as PNG images, tables for the bridge and risk flags. Slide 4 Monte Carlo uses a bar chart of the P10/P25/P50/P75/P90 distribution. Graceful fallback: if `python-pptx` is absent, returns a structured `.txt` outline with the same 5-slide structure.

**Data in:** `DealAnalysisPacket`; matplotlib charts from `reporting.py`.

**Data out:** `.pptx` bytes (or `.txt` fallback) for `GET /api/deals/<id>/export?format=pptx`.

---

## `exit_memo.py` — Exit-Readiness HTML Memo

**What it does:** Partner-ready exit memo: deal facts, hold-period track record, peer percentile benchmarking, remaining RCM opportunity, and exit story narrative.

**How it works:** Sections: deal header (entry date, hold years, entry/current MOIC), realized value creation summary (lever-by-lever actuals vs. underwriting), current metric snapshot vs. entry metrics and peer percentiles, remaining opportunity (what the next buyer gets), exit thesis narrative ("Why exit now: XYZ"), and buyer type fit matrix. Populated from the current packet plus hold-period actuals from `pe/hold_tracking.py` and the deal's snapshot history.

**Data in:** Current `DealAnalysisPacket`; hold-period variance from `pe/hold_tracking.py`; portfolio snapshots from `portfolio/portfolio_snapshots.py`.

**Data out:** Exit memo HTML for `GET /api/deals/<id>/exit-memo`.

---

## `lp_update.py` — Standalone LP Update Builder

**What it does:** Builds the partner-ready LP update HTML page at `GET /lp-update`. One-click quarterly reporting for fund investors.

**How it works:** Aggregates all active and recently exited deals from the portfolio store. Generates: fund-level KPI banner (deployed capital, weighted MOIC, realized MOIC), per-deal cards with health score indicator and key metrics, a pipeline funnel showing deals by stage, and a portfolio EBITDA trajectory SVG. Uses the `ui/_ui_kit.py` shell with `@media print` styles for clean PDF export. The "Download LP Update" button triggers `exports/lp_quarterly_report.py` for the full formatted version.

**Data in:** `portfolio/store.py` all active deals; `portfolio/portfolio_snapshots.py` latest snapshots; `deals/health_score.py`.

**Data out:** LP update HTML for `GET /lp-update`.

---

## `report_themes.py` — CSS Theme System

**What it does:** Defines four CSS themes for HTML reports: default (Chartis dark), light (client-facing), print-optimized (black-and-white for laser printing), and minimal (plain sans-serif for email).

**How it works:** Each theme is a CSS string with custom properties (colors, fonts, spacing). `get_theme(name)` returns the CSS string. Reports accept a `theme` parameter: `html_report.py` defaults to `default`, `full_report.py` to `default`, client-facing exports to `light`. Print theme removes all background colors and sets all text to black for clean laser printing. Minimal theme sets `font-family: Arial, sans-serif` and removes all decorative elements.

**Data in:** Theme name string from the caller.

**Data out:** CSS string injected into report `<style>` blocks.

---

## `_partner_brief.py` — One-Page Partner IC Brief

**What it does:** One-page IC-ready partner brief: headline KPIs, key insights, benchmark gaps, and management plan miss summary. What a partner reads in 3 minutes before IC.

**How it works:** Extracts: top-3 KPI gaps vs. peer median, top-3 risk flags, MC P50 MOIC and confidence band, the biggest variance driver, and two "watch items" from the diligence questions list. Formats as a tight HTML card (no more than one scrollable page). Uses bullet points, not paragraphs — optimized for a 30-second scan.

**Data in:** `DealAnalysisPacket` risk flags, MC summary, completeness gaps, and variance attribution.

**Data out:** HTML card string for the IC prep panel.

---

## `_report_css.py` — Shared Report CSS

**What it does:** Base CSS and `<head>` markup shared across all HTML reports.

**How it works:** Contains: font imports (system fonts only — no external CDN calls), the base CSS reset, `.kpi-value` and `.num` classes (tabular-nums for column alignment), severity color classes (`.red`, `.amber`, `.green`), table styles, and the `@media print` overrides. Bundled as a string constant imported by `html_report.py` and `full_report.py`.

**Data in:** Static CSS string — no runtime inputs.

**Data out:** CSS string injected into the `<head>` of all HTML reports.

---

## `_report_helpers.py` — Standalone Formatting Helpers

**What it does:** Isolated helper functions used across report generators: base64 image encoding, HTML escaping, data URL generation for embedded charts, and number formatting.

**How it works:** `chart_to_data_url(fig)` — converts a matplotlib figure to a base64-encoded PNG data URL for embedding in HTML without external files. `escape_html(s)` — `html.escape()` wrapper. `format_pct(v)` → `"14.5%"`. `format_mm(v)` → `"$12.50M"`. `format_multiple(v)` → `"2.50x"`. All formatting functions are pure (no side effects) and imported by all report modules.

**Data in:** Matplotlib figures; raw numeric values.

**Data out:** Formatted strings and data URLs for report HTML.

---

## `_report_sections.py` — Static HTML Scaffolding

**What it does:** Static HTML/JS scaffolding blocks assembled alongside dynamic data sections in the executive report.

**How it works:** Contains pre-written HTML string constants for: the report header block (logo, title, date, analyst), the footer block (disclaimers, run_id, packet hash), the JS snippet for collapsible sections, and the print-button handler. These static blocks are assembled with the dynamic sections (generated from packet data) to produce the final report.

**Data in:** Static strings — no runtime data inputs.

**Data out:** HTML string constants for report assembly.

---

## Key Concepts

- **Reports are views, not computations**: Every report reads from a pre-built `DealAnalysisPacket` — no recalculation at report time.
- **Consistent formatting**: All reports share the same number formatting helpers from `_report_helpers.py` and CSS from `_report_css.py`.
- **Audit footer on all exports**: Every exported document prints the packet hash and run_id for traceability.
