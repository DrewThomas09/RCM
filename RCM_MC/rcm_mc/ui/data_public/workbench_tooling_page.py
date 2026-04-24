"""Workbench Tooling + Interpretability Demo — /workbench-tooling."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _feature_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cat_color = {
        "sorting": P["accent"], "export": P["positive"],
        "drill_down": P["warning"], "traceability": P["accent"],
        "interactivity": P["text_dim"],
    }
    cols = [("ID", "left"), ("Feature", "left"), ("Category", "center"),
            ("Status", "center"), ("Implementation", "left"), ("Demo Hint", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cc = cat_color.get(f.category, text_dim)
        sc = pos if f.status == "shipped" else warn
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(f.feature_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:260px">{_html.escape(f.name)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;letter-spacing:0.06em">{_html.escape(f.category.upper())}</span></td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(f.status.upper())}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(f.implementation)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:300px">{_html.escape(f.demo_hint)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _dimensions_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Dimension", "left"), ("Covered", "center"),
            ("Implementation", "left"), ("Example", "left"), ("UI Pattern", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        covered_label = "✓ YES" if d.covered else "PENDING"
        covered_c = pos if d.covered else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(d.dimension)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{covered_c};font-weight:700">{_html.escape(covered_label)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(d.implementation)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:320px">{_html.escape(d.example)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:360px">{_html.escape(d.ui_pattern)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _demo_row_html(row, idx: int) -> str:
    """Render one demo row + its Alpine.js-driven 'explain' expansion."""
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    rb = panel_alt if idx % 2 == 0 else bg
    p = row.p50
    # Confidence-interval sub-text + bear-case counter
    ci_str = ""
    if p.confidence_low is not None and p.confidence_high is not None:
        if p.unit == "$":
            ci_str = f"[P25 ${p.confidence_low/1000:,.0f}K · P75 ${p.confidence_high/1000:,.0f}K]"
        else:
            ci_str = f"[P25 {p.confidence_low:,.2f} · P75 {p.confidence_high:,.2f}]"
    bear_str = ""
    if p.bear_case_value is not None:
        if p.unit == "$":
            bear_str = f"bear ${p.bear_case_value/1000:,.0f}K"
        else:
            bear_str = f"bear {p.bear_case_value:,.2f}"

    tooltip = (
        f"source: {p.source_module}.{p.source_function}\n"
        f"calc: {p.calculation}\n"
        f"vintage: {p.vintage}\n"
        f"CI: {ci_str}"
    )

    # Main row with Alpine.js toggle
    main_row = (
        f'<tr style="background:{rb};cursor:pointer" x-data="{{ open: false }}" @click="open = !open">'
        f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};width:28px">'
        f'<span x-text="open ? \'▾\' : \'▸\'">▸</span></td>'
        f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(row.curve_id)}</td>'
        f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{acc};font-weight:600">{_html.escape(row.specialty)}</td>'
        f'<td style="text-align:center;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(row.region)}</td>'
        f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:12px;color:{pos};font-weight:700" '
        f'title="{_html.escape(tooltip, quote=True)}" data-sort-value="{p.raw_value}">'
        f'{_html.escape(p.display_value)}'
        f'<div style="font-size:9px;color:{text_dim};font-weight:400;margin-top:1px">{_html.escape(ci_str)}</div>'
        f'</td>'
        f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">{_html.escape(bear_str)}</td>'
        f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{row.sample_size}</td>'
        f'</tr>'
    )

    # Expand row (Alpine x-show)
    related_bullets = "".join(f"<li>{_html.escape(m)}</li>" for m in p.related_modules)
    expand_row = (
        f'<tr style="background:{rb}" x-show="open" x-transition>'
        f'<td colspan="7" style="padding:12px 16px;border-top:1px solid {border};font-size:10px;color:{text_dim};line-height:1.6">'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">'
        f'<div>'
        f'<div style="color:{text};font-weight:700;font-size:10px;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">Provenance</div>'
        f'<div><strong style="color:{text}">Source:</strong> {_html.escape(p.source_module)}.{_html.escape(p.source_function)}</div>'
        f'<div><strong style="color:{text}">Calculation:</strong> {_html.escape(p.calculation)}</div>'
        f'<div><strong style="color:{text}">Vintage:</strong> {_html.escape(p.vintage)}</div>'
        f'<div><strong style="color:{text}">Confidence Method:</strong> {_html.escape(p.confidence_method)}</div>'
        f'</div>'
        f'<div>'
        f'<div style="color:{neg};font-weight:700;font-size:10px;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">Bear Case</div>'
        f'<div>{_html.escape(p.bear_case_context)}</div>'
        f'<div style="color:{text};font-weight:700;font-size:10px;letter-spacing:0.08em;text-transform:uppercase;margin:10px 0 4px 0">Related Modules</div>'
        f'<ul style="margin:0;padding-left:18px;color:{text_dim}">{related_bullets}</ul>'
        f'</div>'
        f'</div>'
        f'<div style="margin-top:12px;padding-top:10px;border-top:1px dashed {border}">'
        f'<div style="color:{text};font-weight:700;font-size:10px;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">Explain This Number</div>'
        f'<div style="color:{text_dim}">{_html.escape(p.explain_summary)}</div>'
        f'</div>'
        f'</td>'
        f'</tr>'
    )
    return main_row + expand_row


def _demo_table(rows) -> str:
    bg = P["panel"]; border = P["border"]; text_dim = P["text_dim"]
    cols = [("", "center"), ("Curve", "left"), ("Specialty", "left"),
            ("Region", "center"), ("Thesis (P50)", "right"),
            ("Bear Case (P10)", "right"), ("N", "right")]
    sort_types = ["string", "string", "string", "string", "number", "number", "number"]
    ths = ""
    for (c, a), st in zip(cols, sort_types):
        ths += (f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
                f'font-size:10px;color:{text_dim};letter-spacing:0.05em" data-sort-type="{st}">'
                f'{_html.escape(c)}</th>')
    body_rows = "".join(_demo_row_html(r, i) for i, r in enumerate(rows))
    return (f'<div style="overflow-x:auto;margin-top:12px">'
            f'<table id="interpretability-demo" data-sortable style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead>'
            f'<tbody>{body_rows}</tbody></table>'
            f'</div>')


def render_workbench_tooling(params: dict = None) -> str:
    from rcm_mc.data_public.workbench_tooling import compute_workbench_tooling, export_toolbar
    r = compute_workbench_tooling()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("UI Features", str(len(r.features)), "sortable/export/drill-down", "") +
        ck_kpi_block("Shipped Features", str(sum(1 for f in r.features if f.status == "shipped")), "", "") +
        ck_kpi_block("Interpretability Dimensions", str(len(r.interpretability_dimensions)), "source/calc/vintage/CI/bear/explain", "") +
        ck_kpi_block("Export Formats", str(len(r.export_features)), "CSV/JSON/PDF + deferred", "") +
        ck_kpi_block("Demo Rows", str(len(r.demo_rows)), "from benchmark library", "") +
        ck_kpi_block("Client Deps", "htmx + Alpine", "via CDN, zero install", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    features_tbl = _feature_table(r.features)
    dimensions_tbl = _dimensions_table(r.interpretability_dimensions)
    demo_tbl = _demo_table(r.demo_rows)
    toolbar_html = export_toolbar("interpretability-demo")

    cdn_scripts = (
        f'<script src="{r.htmx_cdn}" defer></script>'
        f'<script src="{r.alpine_cdn}" defer></script>'
        f'<script>document.addEventListener("DOMContentLoaded",function(){{'
        f'{r.sortable_table_js}{r.export_controls_js}'
        f'}});</script>'
    )

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
{cdn_scripts}
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Workbench Tooling + Interpretability — htmx + Alpine.js</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{len(r.features)} UI features · {len(r.interpretability_dimensions)} interpretability dimensions (source + calculation + vintage + CI + bear-case counter + explain) · sortable columns · CSV/JSON/PDF export · zero new Python deps (CDN-loaded htmx + Alpine.js, ~25KB combined)</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">UI Feature Catalog</div>{features_tbl}</div>
  <div style="{cell}"><div style="{h3}">Six Interpretability Dimensions — Coverage Matrix</div>{dimensions_tbl}</div>
  <div style="{cell}">
    <div style="{h3}">Live Demo — Benchmark Curve BC-02 Per-Physician Medicare Revenue (All Features On)</div>
    <div style="font-size:11px;color:{text_dim};margin-top:4px;margin-bottom:8px">
      <strong style="color:{text}">Try it:</strong> (1) <em>Click any column header</em> to sort asc/desc.
      (2) <em>Hover</em> any green P50 number to see source/calc/vintage/CI in a tooltip.
      (3) <em>Click a row</em> to expand full provenance + bear-case + related modules.
      (4) <em>Click CSV / JSON / Print</em> below the table to export.
    </div>
    {demo_tbl}
    {toolbar_html}
  </div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Interpretability Thesis:</strong>
    A PE analyst looking at a number on this platform should immediately know four things:
    where it came from (<strong>source</strong>), how it was computed (<strong>calculation</strong>),
    when the underlying data is from (<strong>vintage</strong>), and how confident we are
    (<strong>CI</strong>). They should also see what the adversarial engine says is the
    downside scenario (<strong>bear counter-number</strong>) and be able to expand a fuller
    explanation on demand (<strong>explain this number</strong>). All six dimensions are
    shipped here and reusable via <code style="color:{acc};font-family:JetBrains Mono,monospace">workbench_tooling.InterpretableNumber</code>.
    <br><br>
    <strong style="color:{text}">Implementation choices — why htmx + Alpine.js, not Perspective:</strong>
    Perspective (JP Morgan) is a powerful WebGL analytical grid but adds a ~400KB JS bundle
    and a full runtime. htmx + Alpine.js together are ~25KB, load from CDN with no install,
    and fit the platform's stdlib / server-rendered philosophy. Every feature here (sortable
    columns, click-to-expand rows, export buttons) is progressive enhancement on top of the
    existing HTML — the page degrades gracefully if JS is disabled.
    <br><br>
    <strong style="color:{text}">Reusable helpers available in workbench_tooling:</strong>
    <code style="color:{acc};font-family:JetBrains Mono,monospace">numeric_cell(value, unit, data_source)</code> —
    returns a <td> with tabular-nums + data-source tooltip + sort-value. Use it anywhere you
    render a number. <code style="color:{acc};font-family:JetBrains Mono,monospace">export_toolbar(table_id)</code> —
    adds CSV/JSON/Print buttons to any table by id. Both honor the zero-new-Python-dep norm.
    <br><br>
    <strong style="color:{text}">Deferred:</strong>
    XLSX export needs openpyxl (not in current dep set) — CSV is the interim path that Excel
    opens natively. PPTX export: rcm_mc/reports/pptx_export.py already handles some PPTX paths
    via python-pptx; integrating with the data_public workbench layer is future work.
  </div>
</div>"""

    return chartis_shell(body, "Workbench Tooling", active_nav="/workbench-tooling")
