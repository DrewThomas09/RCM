# Exports

Document generation and export rendering. Every export path renders from a `DealAnalysisPacket` so numbers cannot drift between formats.

---

## `packet_renderer.py` — Central Export Renderer

**What it does:** Takes a `DealAnalysisPacket` and produces HTML memos, PPTX decks, CSV data tables, JSON blobs, and LP update documents. The single export factory for the entire platform.

**How it works:** Dispatch table keyed on `format` parameter: `html` → renders the analysis workbench summary as a standalone HTML document (with the packet hash and run_id in the footer); `pptx` → calls `pptx_export.py` (requires `python-pptx`); `csv` → flattens the packet's key metrics and bridge outputs into a CSV table; `json` → serializes via `packet.to_json()`; `lp_update` → calls `reports/lp_update.py`. All paths add an audit footer with `run_id`, `built_at`, and the `hash_inputs` string. Graceful fallback: when `python-pptx` is absent, the PPTX path returns a structured `.txt` outline with the same section headings.

**Data in:** `DealAnalysisPacket` from `analysis/analysis_store.py`; format string from the export request.

**Data out:** HTML string / PPTX bytes / CSV string / JSON dict / LP HTML — returned to `server.py` for download or inline display.

---

## `xlsx_renderer.py` — Multi-Sheet Excel Export

**What it does:** Generates a multi-sheet Excel workbook from a `DealAnalysisPacket`. Six tabs: RCM Profile, EBITDA Bridge, Monte Carlo, Risk Flags, Raw Data, Audit.

**How it works:** Uses `openpyxl` (base dependency). Each tab is a separate worksheet function. RCM Profile tab: current vs. target metrics table with conditional formatting (red/amber/green cells based on peer percentile). Bridge tab: lever waterfall with per-lever EBITDA delta and EV impact at 10×/12×/15×. Monte Carlo tab: P5–P95 distribution table + histogram chart. Risk Flags tab: severity-colored risk flag table with trigger values. Raw Data tab: full metrics dict as a flat key/value table. Audit tab: run_id, built_at, hash_inputs, data source timestamps.

**Data in:** `DealAnalysisPacket` (same source as `packet_renderer.py`).

**Data out:** `.xlsx` bytes for download via `GET /api/deals/<id>/export?format=xlsx`.

---

## `diligence_package.py` — One-Click Diligence ZIP

**What it does:** Assembles a complete IC-ready diligence package as a ZIP archive: 9 documents plus a manifest. Used for the "Export to IC" button.

**How it works:** Assembles: (1) Executive summary HTML, (2) EBITDA bridge PDF/HTML, (3) Risk flags matrix HTML, (4) Diligence questionnaire (P0/P1/P2 list) HTML, (5) Comparable hospital analysis CSV, (6) Monte Carlo distribution HTML, (7) Provenance graph HTML, (8) Raw metrics CSV, (9) Manifest JSON with file list and packet hash. All documents generated from the same `DealAnalysisPacket` so numbers are identical across all files. ZIP assembled in-memory using `zipfile.ZipFile`. Export logged to `export_store.py`.

**Data in:** `DealAnalysisPacket`; deal name and analyst from the session.

**Data out:** ZIP bytes for `GET /api/deals/<id>/export?format=zip`; export audit entry in `export_store.py`.

---

## `exit_package.py` — Exit Data Room ZIP

**What it does:** Generates an exit-readiness data package for buyer due diligence: exit memo, value creation summary, and buyer data room checklist.

**How it works:** Assembles: (1) Exit memo HTML (from `reports/exit_memo.py`), (2) Value creation summary (realized vs. underwritten EBITDA improvement), (3) Hold-period operations summary (initiative tracking via `pe/hold_tracking.py`), (4) Updated market analysis, (5) Buyer data room checklist (structured checklist of items to prepare). ZIP assembled in-memory. Logs to `export_store.py`.

**Data in:** Current `DealAnalysisPacket`; hold-period variance data from `pe/hold_tracking.py`; deal lifecycle data from `portfolio/portfolio_snapshots.py`.

**Data out:** Exit package ZIP for `GET /api/deals/<id>/export?format=exit`.

---

## `lp_quarterly_report.py` — Fund-Level LP Quarterly Report

**What it does:** Generates a fund-level quarterly LP report aggregating deployed capital, weighted MOIC, EBITDA growth, and per-deal portfolio cards. Partner-ready HTML and optionally emailed.

**How it works:** Queries `portfolio/store.py` for all active and exited deals. Computes fund-level statistics: deployed capital, MOIC (weighted by invested capital), IRR (TWRR across holds), deal count by stage, portfolio EBITDA growth (current vs. entry). Renders a partner-facing HTML report with a fund summary header, performance attribution breakdown (RCM improvement vs. multiple expansion), and per-deal cards with key metrics and health scores. Uses `ui/_ui_kit.py` shell for consistent styling.

**Data in:** All active deal snapshots from `portfolio/portfolio_snapshots.py`; fund attribution from `pe/fund_attribution.py`.

**Data out:** LP quarterly report HTML for `GET /lp-update` and scheduled email delivery.

---

## `export_store.py` — Export Audit Log

**What it does:** Append-only audit log of every generated export. Tracks what was handed out, when, to whom, in which format, and from which analysis run.

**How it works:** `export_events` table with: `export_id` (UUID), `deal_id`, `format` (html/xlsx/zip/pptx/json/csv), `exported_by` (username), `exported_at`, `run_id` (the analysis run the export was based on), `recipient` (optional — email for LP reports). `log_export()` always inserts. `exports_for_deal(deal_id)` returns the full export history for the deal audit trail. This enables compliance queries like "what was handed to the banker on Nov 14?"

**Data in:** Export metadata from `packet_renderer.py` and other export generators.

**Data out:** Export history for the deal audit trail and compliance queries.

---

## Key Concepts

- **Packet as single source**: Every export renders from the same `DealAnalysisPacket`, eliminating number drift between formats.
- **Audit footers**: Every export prints the packet hash and run_id so stale numbers can be traced to their exact analysis run.
- **Graceful fallback**: When `python-pptx` is not installed, the PPTX path emits a structured `.txt` with the same outline — the platform never throws an import error at export time.
