"""Workbench Tooling — htmx + Alpine.js UI enhancements.

Blueprint directive: make the Bloomberg-style workbench more usable.
Options were Perspective (JP Morgan) — heavy WebGL grid — or htmx +
Alpine.js — server-rendered interactivity that fits the stdlib
philosophy. Chose the latter: htmx (~10KB) + Alpine.js (~15KB) load
via CDN, require zero install, add interactivity on top of the
existing server-rendered HTML.

This module ships:

    1. Sortable tables — click column header to sort asc/desc, entirely
       client-side, no server round-trip.
    2. Export controls — CSV / JSON / Print-to-PDF buttons that operate
       on the rendered table DOM.
    3. Number traceability — every numeric cell in a workbench carries a
       `data-source` attribute with the computation's provenance, shown
       as a hover tooltip.
    4. Drill-down rows — click a row to toggle a detail sub-row that
       can show full provenance chain (compute function + source fields
       + methodology note).

The module exposes reusable helpers (`sortable_table`, `numeric_cell`,
`export_toolbar`) that other UI pages can adopt incrementally. The
demo page at /workbench-tooling shows all features against real corpus
data (benchmark curves, named failures, and deal exposures).

Public API
----------
    TooltipSpec                  one data-source tooltip
    ExportFeature                one export button's behavior
    WorkbenchFeature             one UI feature + demo context
    WorkbenchToolingResult       composite output
    sortable_table(rows, ...)    reusable HTML helper
    numeric_cell(value, ...)     reusable HTML helper
    export_toolbar(table_id)     reusable HTML helper
    compute_workbench_tooling()  -> WorkbenchToolingResult
"""
from __future__ import annotations

import html as _html
import importlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WorkbenchFeature:
    feature_id: str
    name: str
    category: str                  # "sorting" / "export" / "drill_down" / "traceability"
    implementation: str            # brief tech note
    client_deps: List[str]         # CDN URLs
    status: str                    # "shipped" / "planned"
    demo_hint: str


@dataclass
class ExportFeature:
    format: str                    # "CSV" / "JSON" / "PDF (browser print)"
    extension: str
    mime_type: str
    implementation_tech: str
    browser_support: str
    notes: str


@dataclass
class TooltipSpec:
    numeric_cell_class: str
    data_attribute: str
    hover_behavior: str
    example_value: str
    example_tooltip: str


@dataclass
class InterpretableNumber:
    """A fully-interpretable number: value + provenance + confidence + counter."""
    display_value: str             # formatted string shown in the cell
    unit: str                      # "$" / "%" / "x" / "mo" / ""
    raw_value: float
    # Provenance (the four dimensions)
    source_module: str             # e.g., "benchmark_curve_library"
    source_function: str           # e.g., "compute_benchmark_library().BC-02"
    calculation: str               # one-line formula / methodology
    vintage: str                   # data-source year / effective date
    # Confidence
    confidence_low: Optional[float]   # lower bound of 80% CI or P25
    confidence_high: Optional[float]  # upper bound of 80% CI or P75
    confidence_method: str            # e.g., "benchmark P25-P75" or "KM 95% CI"
    # Bear-case counter
    bear_case_value: Optional[float]  # what the adversarial engine assigns at P10
    bear_case_context: str            # brief bear-case narrative
    # Explain
    explain_summary: str           # ~200-char longer narrative
    related_modules: List[str]     # modules that feed into this number


@dataclass
class DemoRow:
    """One row of demo data for the demonstration table."""
    curve_id: str
    curve_name: str
    specialty: str
    region: str
    p50: InterpretableNumber        # the "thesis" number with full interpretability
    sample_size: int
    data_source: str


@dataclass
class InterpretabilityDimension:
    dimension: str                 # "Source" / "Calculation" / "Vintage" / "CI" / "Bear Counter" / "Explain"
    covered: bool
    implementation: str
    example: str
    ui_pattern: str                # how it's surfaced in the page


@dataclass
class WorkbenchToolingResult:
    features: List[WorkbenchFeature]
    export_features: List[ExportFeature]
    tooltip_specs: List[TooltipSpec]
    interpretability_dimensions: List[InterpretabilityDimension]
    demo_rows: List[DemoRow]
    htmx_cdn: str
    alpine_cdn: str
    sortable_table_js: str          # inline JS for sortable columns
    export_controls_js: str         # inline JS for export behavior
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# CDN URLs (pin to stable versions)
# ---------------------------------------------------------------------------

HTMX_CDN = "https://unpkg.com/htmx.org@1.9.12"
ALPINE_CDN = "https://unpkg.com/alpinejs@3.13.7/dist/cdn.min.js"


# ---------------------------------------------------------------------------
# Inline JS — kept small, stdlib-philosophy aligned
# ---------------------------------------------------------------------------

SORTABLE_TABLE_JS = """
// Sortable table — one listener per [data-sortable] table. Click a <th> to sort.
(function(){
  function parseCell(td, type) {
    var v = td.getAttribute('data-sort-value');
    if (v === null || v === undefined) v = td.innerText.trim();
    if (type === 'number') {
      v = v.replace(/[$,%\\s]/g,'').replace(/x$/,'');
      var f = parseFloat(v);
      return isNaN(f) ? -Infinity : f;
    }
    return v.toLowerCase();
  }
  function sortTable(table, colIdx, type, dir) {
    var tbody = table.tBodies[0];
    var rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort(function(a, b) {
      var av = parseCell(a.cells[colIdx], type);
      var bv = parseCell(b.cells[colIdx], type);
      if (av < bv) return dir === 'asc' ? -1 : 1;
      if (av > bv) return dir === 'asc' ? 1 : -1;
      return 0;
    });
    rows.forEach(function(r) { tbody.appendChild(r); });
  }
  document.querySelectorAll('table[data-sortable]').forEach(function(table) {
    var ths = table.querySelectorAll('thead th');
    ths.forEach(function(th, idx) {
      th.style.cursor = 'pointer';
      th.style.userSelect = 'none';
      th.addEventListener('click', function() {
        var type = th.getAttribute('data-sort-type') || 'string';
        var currentDir = th.getAttribute('data-sort-dir') || 'none';
        var newDir = currentDir === 'asc' ? 'desc' : 'asc';
        ths.forEach(function(x) { x.removeAttribute('data-sort-dir'); });
        th.setAttribute('data-sort-dir', newDir);
        sortTable(table, idx, type, newDir);
      });
    });
  });
})();
"""


EXPORT_CONTROLS_JS = """
// Export toolbar — CSV / JSON / Print-to-PDF.
(function(){
  function tableToCSV(tbl) {
    var out = [];
    tbl.querySelectorAll('tr').forEach(function(tr){
      var row = [];
      tr.querySelectorAll('th,td').forEach(function(c){
        var v = c.innerText.replace(/"/g, '""');
        if (v.search(/("|,|\\n)/g) >= 0) v = '"' + v + '"';
        row.push(v);
      });
      out.push(row.join(','));
    });
    return out.join('\\n');
  }
  function tableToJSON(tbl) {
    var headers = [];
    tbl.querySelectorAll('thead th').forEach(function(h){ headers.push(h.innerText.trim()); });
    var rows = [];
    tbl.querySelectorAll('tbody tr').forEach(function(tr){
      var obj = {};
      tr.querySelectorAll('td').forEach(function(td, idx){
        obj[headers[idx] || ('col_' + idx)] = td.innerText.trim();
      });
      rows.push(obj);
    });
    return JSON.stringify(rows, null, 2);
  }
  function download(filename, content, mime) {
    var blob = new Blob([content], { type: mime });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
  document.querySelectorAll('[data-export-target]').forEach(function(btn){
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      var targetId = btn.getAttribute('data-export-target');
      var format = btn.getAttribute('data-export-format');
      var tbl = document.getElementById(targetId);
      if (!tbl) return;
      if (format === 'csv') {
        download(targetId + '.csv', tableToCSV(tbl), 'text/csv;charset=utf-8;');
      } else if (format === 'json') {
        download(targetId + '.json', tableToJSON(tbl), 'application/json');
      } else if (format === 'print') {
        window.print();
      }
    });
  });
})();
"""


# ---------------------------------------------------------------------------
# Feature catalog + demo data
# ---------------------------------------------------------------------------

def _build_features() -> List[WorkbenchFeature]:
    return [
        WorkbenchFeature(
            "FT-01", "Sortable columns (client-side)", "sorting",
            "Vanilla JS listener per table[data-sortable]; sorts from DOM with no server round-trip.",
            [], "shipped",
            "Click any column header on the demo table below; click again to reverse.",
        ),
        WorkbenchFeature(
            "FT-02", "CSV export", "export",
            "DOM-to-CSV serialization + download via Blob URL.",
            [], "shipped",
            "Click the CSV button in the demo toolbar to download the rendered table.",
        ),
        WorkbenchFeature(
            "FT-03", "JSON export", "export",
            "DOM-to-JSON serialization using first-row thead cells as keys.",
            [], "shipped",
            "Click the JSON button to download structured data rows.",
        ),
        WorkbenchFeature(
            "FT-04", "Print-to-PDF", "export",
            "Native window.print() with print-specific CSS for paginated output.",
            [], "shipped",
            "Click the Print button; use browser 'Save as PDF' in the print dialog.",
        ),
        WorkbenchFeature(
            "FT-05", "XLSX export (deferred)", "export",
            "Requires openpyxl (not in current dep set) or browser SheetJS lib. CSV opens natively in Excel as interim.",
            [], "planned",
            "For now, use CSV export — Excel reads it identically.",
        ),
        WorkbenchFeature(
            "FT-06", "Data-source tooltips on every numeric cell", "traceability",
            "Every numeric <td> carries `title=\"source: <module>.<function>()\"` + visible ⓘ hint class.",
            [], "shipped",
            "Hover any numeric value in the demo table to see its provenance.",
        ),
        WorkbenchFeature(
            "FT-07", "Drill-down rows (Alpine.js)", "drill_down",
            "x-data + x-show toggle on a detail sub-row; no server round-trip for expand.",
            [ALPINE_CDN], "shipped",
            "Click the ▸ icon on any demo row to expand a provenance detail panel.",
        ),
        WorkbenchFeature(
            "FT-08", "htmx async refresh (pattern available)", "interactivity",
            "hx-get / hx-post / hx-swap wired into Chartis shell; modules can opt-in for partial refresh.",
            [HTMX_CDN], "shipped",
            "Infrastructure ready; used by future modules for incremental load (e.g., paged corpus query).",
        ),
        WorkbenchFeature(
            "FT-09", "Filtering (planned)", "sorting",
            "Per-column filter input via Alpine.js — scoped to individual tables.",
            [ALPINE_CDN], "planned",
            "Next iteration — Alpine.js wireframe in place.",
        ),
        WorkbenchFeature(
            "FT-10", "Column visibility toggle (planned)", "sorting",
            "Show/hide columns for dense tables.",
            [], "planned",
            "Alpine.js x-show pattern fits this — queued.",
        ),
    ]


def _build_export_features() -> List[ExportFeature]:
    return [
        ExportFeature("CSV", ".csv", "text/csv;charset=utf-8;",
                      "DOM serialization → Blob → <a download>",
                      "All modern browsers",
                      "Opens natively in Excel, Numbers, Google Sheets."),
        ExportFeature("JSON", ".json", "application/json",
                      "Headers-as-keys object per row",
                      "All modern browsers",
                      "Good for programmatic analysis / downstream ingest."),
        ExportFeature("PDF (browser print)", ".pdf", "application/pdf",
                      "window.print() + @media print CSS",
                      "All modern browsers",
                      "Uses native print dialog; user selects 'Save as PDF' destination."),
        ExportFeature("XLSX (deferred)", ".xlsx",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                      "Requires openpyxl or SheetJS (external)",
                      "—",
                      "Not in current dep set. CSV is the interim path; XLSX can be added when openpyxl is approved as a dependency."),
        ExportFeature("PPTX (deferred)", ".pptx",
                      "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                      "Requires python-pptx (external)",
                      "—",
                      "Existing rcm_mc/reports/pptx_export.py handles some PPTX paths; integration with data_public workbench is future work."),
    ]


def _build_tooltip_specs() -> List[TooltipSpec]:
    return [
        TooltipSpec(
            "num data-source",
            "title",
            "Hover shows the exact module + function that computed this number.",
            "$4,650,000",
            "source: benchmark_curve_library.compute_benchmark_library() → BC-04 Executive Compensation (CEO, Large Hospital, West region)",
        ),
        TooltipSpec(
            "num data-source",
            "title",
            "Cell shows the raw numeric plus the methodology note in tooltip.",
            "58.13",
            "source: backtest_harness.compute_verdict() → composite score (0.45·NF + 0.25·NCCI + 0.30·Leverage)",
        ),
        TooltipSpec(
            "num data-source",
            "title",
            "Per-specialty survival curves expose the fit methodology.",
            "median=42mo",
            "source: survival_analysis.compute_survival_analysis() → Emergency Medicine retention, Kaplan-Meier estimator, n=180 synthetic cohort",
        ),
    ]


def _load_corpus_count() -> int:
    n = 0
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            n += len(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return n


def _build_interpretable_number(
    raw: float,
    unit: str,
    module: str,
    fn: str,
    calc: str,
    vintage: str,
    p25: float,
    p75: float,
    bear: Optional[float],
    bear_ctx: str,
    summary: str,
    related: List[str],
) -> InterpretableNumber:
    if unit == "$":
        if abs(raw) >= 1_000_000:
            disp = f"${raw/1_000_000:,.2f}M"
        elif abs(raw) >= 1_000:
            disp = f"${raw/1_000:,.1f}K"
        else:
            disp = f"${raw:,.2f}"
    elif unit == "%":
        disp = f"{raw:,.2f}%"
    elif unit == "x":
        disp = f"{raw:,.2f}x"
    else:
        disp = f"{raw:,.2f}"
    return InterpretableNumber(
        display_value=disp,
        unit=unit,
        raw_value=raw,
        source_module=module,
        source_function=fn,
        calculation=calc,
        vintage=vintage,
        confidence_low=p25,
        confidence_high=p75,
        confidence_method="benchmark P25-P75",
        bear_case_value=bear,
        bear_case_context=bear_ctx,
        explain_summary=summary,
        related_modules=related,
    )


def _build_demo_rows() -> List[DemoRow]:
    """Pull a handful of benchmark-curve rows as demo data with full interpretability."""
    try:
        from .benchmark_curve_library import compute_benchmark_library
        bench = compute_benchmark_library()
        rows: List[DemoRow] = []
        bc_rows = [r for r in bench.curve_rows if r.curve_id == "BC-02"]
        bc_rows.sort(key=lambda x: x.sample_size, reverse=True)
        for r in bc_rows[:18]:
            p50_n = _build_interpretable_number(
                raw=r.p50,
                unit="$",
                module="benchmark_curve_library",
                fn=f"compute_benchmark_library() → {r.curve_id}",
                calc=(
                    "SUM(total_medicare_payment) / COUNT(DISTINCT npi) from Medicare Util "
                    "warehouse, scaled by CMS GPCI factor for region."
                ),
                vintage=f"source year {r.year}, CMS Provider Utilization Part B",
                p25=r.p25,
                p75=r.p75,
                bear=r.p10,
                bear_ctx=(
                    f"If adversarial scenario materializes (payer-rate compression + volume "
                    f"attrition), expect P10 Medicare revenue ~${r.p10:,.0f}/physician — "
                    f"a ~{((r.p50 - r.p10) / r.p50 * 100):.0f}% compression from base case."
                ),
                summary=(
                    f"Per-physician annual Medicare revenue at the median ({r.region} region, "
                    f"{r.specialty}). Commercial + Medicaid typically adds 1.2-2.4x to this "
                    f"figure for full-revenue estimate. Methodology: {r.methodology_notes[:120]}"
                ),
                related=["medicare_utilization.py (data source)",
                         "ncci_edits.py (denial-rate overlay)",
                         "benchmark_curve_library.py (this curve)"],
            )
            rows.append(DemoRow(
                curve_id=r.curve_id,
                curve_name=r.curve_name[:60],
                specialty=r.specialty or "—",
                region=r.region or "—",
                p50=p50_n,
                sample_size=r.sample_size,
                data_source=(
                    f"benchmark_curve_library.compute_benchmark_library() → "
                    f"BC-02 {r.specialty}/{r.region}/{r.year} (n={r.sample_size})"
                ),
            ))
        return rows
    except Exception as e:
        stub = _build_interpretable_number(
            raw=0.0, unit="", module="error", fn="", calc=str(e),
            vintage="", p25=0, p75=0, bear=None, bear_ctx="", summary=str(e),
            related=[],
        )
        return [DemoRow("ERR", f"Could not load: {e}", "—", "—", stub, 0, str(e))]


def _build_interpretability_dimensions() -> List[InterpretabilityDimension]:
    return [
        InterpretabilityDimension(
            "Source",
            True,
            "title attribute on every numeric cell names the source module.function().",
            "source: benchmark_curve_library.compute_benchmark_library() → BC-02 Cardiology/West/2022",
            "Hover tooltip (HTML title attribute) + inline ⓘ hint on column headers.",
        ),
        InterpretabilityDimension(
            "Calculation",
            True,
            "Every InterpretableNumber exposes a one-line formula/methodology.",
            "SUM(total_medicare_payment) / COUNT(DISTINCT npi) scaled by GPCI factor.",
            "Alpine.js expand panel on row click shows calculation below the number.",
        ),
        InterpretabilityDimension(
            "Vintage",
            True,
            "Every number carries a vintage string (source year + dataset).",
            "source year 2022, CMS Provider Utilization Part B",
            "Rendered as faint sub-text under the number in the expand panel.",
        ),
        InterpretabilityDimension(
            "Confidence Interval",
            True,
            "P25 and P75 rendered inline as sub-text with P50; P10 available for bear-case.",
            "$623K [P25 $485K · P75 $798K]",
            "Visible sub-label under bold P50 using tabular-nums alignment.",
        ),
        InterpretabilityDimension(
            "Bear-Case Counter-Number",
            True,
            "Adversarial P10 rendered next to every thesis (P50) number.",
            "$623K (bear $361K)",
            "Right-adjacent muted-red text next to the thesis number.",
        ),
        InterpretabilityDimension(
            "Explain This Number",
            True,
            "Longer narrative summary via Alpine.js x-show toggle.",
            "Per-physician annual Medicare revenue at the median…",
            "Click ▸ to expand a 3-4 sentence explanation + related-modules list.",
        ),
    ]


# ---------------------------------------------------------------------------
# Reusable HTML helpers (public)
# ---------------------------------------------------------------------------

def numeric_cell(value: Any, unit: str = "", data_source: str = "", align: str = "right") -> str:
    """Render a traceable numeric table cell.

    Generates a <td> with:
      - the formatted value
      - data-source attribute for tooltip
      - data-sort-value attribute for sortable tables
      - tabular-nums styling
    """
    if isinstance(value, float):
        v_str = f"{value:,.2f}"
        sort_val = f"{value}"
    elif isinstance(value, int):
        v_str = f"{value:,}"
        sort_val = f"{value}"
    else:
        v_str = str(value)
        sort_val = v_str
    if unit == "$":
        v_str = "$" + v_str
    elif unit == "%":
        v_str = v_str + "%"
    elif unit == "x":
        v_str = v_str + "x"
    elif unit:
        v_str = v_str + " " + unit
    ds_attr = f'title="source: {_html.escape(data_source, quote=True)}"' if data_source else ""
    return (f'<td style="text-align:{align};padding:5px 10px;font-variant-numeric:tabular-nums;'
            f'font-family:JetBrains Mono,monospace;font-size:11px" '
            f'data-sort-value="{_html.escape(sort_val, quote=True)}" {ds_attr}>{_html.escape(v_str)}</td>')


def export_toolbar(table_id: str) -> str:
    """Render a CSV / JSON / Print toolbar bound to `#table_id`."""
    border = "#1e293b"; acc = "#3b82f6"; text = "#e2e8f0"
    btn_base = (f"display:inline-block;padding:5px 12px;margin-right:6px;"
                f"background:transparent;color:{text};border:1px solid {border};"
                f"border-radius:2px;font-family:JetBrains Mono,monospace;font-size:10px;"
                f"letter-spacing:0.08em;cursor:pointer;text-transform:uppercase;"
                f"font-weight:600")
    return (
        f'<div style="margin-top:12px">'
        f'<button type="button" data-export-target="{table_id}" data-export-format="csv" '
        f'style="{btn_base}">CSV</button>'
        f'<button type="button" data-export-target="{table_id}" data-export-format="json" '
        f'style="{btn_base}">JSON</button>'
        f'<button type="button" data-export-target="{table_id}" data-export-format="print" '
        f'style="{btn_base};border-color:{acc};color:{acc}">Print / PDF</button>'
        f'<span style="font-size:10px;color:#94a3b8;font-family:JetBrains Mono,monospace;'
        f'margin-left:12px">💡 Click column headers to sort · hover numeric cells for data-source tooltip</span>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_workbench_tooling() -> WorkbenchToolingResult:
    return WorkbenchToolingResult(
        features=_build_features(),
        export_features=_build_export_features(),
        tooltip_specs=_build_tooltip_specs(),
        interpretability_dimensions=_build_interpretability_dimensions(),
        demo_rows=_build_demo_rows(),
        htmx_cdn=HTMX_CDN,
        alpine_cdn=ALPINE_CDN,
        sortable_table_js=SORTABLE_TABLE_JS,
        export_controls_js=EXPORT_CONTROLS_JS,
        corpus_deal_count=_load_corpus_count(),
    )
