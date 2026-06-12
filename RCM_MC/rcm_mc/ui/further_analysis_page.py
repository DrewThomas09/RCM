"""Further Analysis — the Tableau-style surface over every vendored public
dataset.

Pick a dataset (CMS / CDC / Census / Labor / Markets / derived), a focus, the
measures and a chart type, and the page renders a clean, client-ready chart
you can export to PNG/SVG. Everything is query-string driven, so a configured
view is a shareable URL, and a gallery strip re-renders the same query across
chart types so a partner can pick the right exhibit.

The data engine is ``rcm_mc.diligence.further_analysis``; this module is the
form + layout + chart wiring. No data logic lives here.
"""
from __future__ import annotations

import html
import urllib.parse
from typing import Any, Dict, List, Optional

from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
from .cdd_chart_kit import (
    CHART_TYPES, PALETTES, SIZE_PRESETS, render_cdd_chart, chart_export_toolbar,
)
from ..diligence import further_analysis as fa

_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")


def _qs1(qs: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not qs:
        return default
    v = qs.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return str(v) if v not in (None, "") else default


def _qsbool(qs, key, default=True):
    v = _qs1(qs, key, "")
    if v == "":
        return default
    return v not in ("0", "false", "off", "no")


def _share_url(spec: Dict[str, Any], **overrides: Any) -> str:
    """Build a /further-analysis URL reproducing the current view, with
    optional param overrides (used by the chart-type gallery + chips)."""
    ds = spec["dataset"]
    params: Dict[str, Any] = {
        "dataset": ds.id,
        "measures": ",".join(spec["measures"]),
        "type": spec["chart_type"],
        "sort": spec["sort_key"],
        "asc": "1" if spec["ascending"] else "0",
        "top": str(spec["top_n"]),
    }
    if spec["focus"]:
        params["focus"] = spec["focus"]
    params.update({k: str(v) for k, v in overrides.items()})
    return "/further-analysis?" + urllib.parse.urlencode(params)


def render_further_analysis_page(qs: "Dict[str, Any] | None" = None) -> str:
    spec = fa.resolve_query(qs)
    dataset = spec["dataset"]
    table = spec["table"]
    meta = spec["meta"]

    chart_type = spec["chart_type"]
    if chart_type not in dict(CHART_TYPES):
        chart_type = "bar"
    palette = _qs1(qs, "palette", "Navy–Teal")
    if palette not in PALETTES:
        palette = "Navy–Teal"
    size = _qs1(qs, "size", "L")
    width_px = dict(SIZE_PRESETS).get(size, 920)
    show_values = _qsbool(qs, "values", True)
    legend = _qsbool(qs, "legend", True)

    # Auto title/subtitle/footnote (editable via the form).
    m_labels = ", ".join(m["label"] for m in meta["measures"])
    auto_title = f"{dataset.label} — {m_labels}"
    title = _qs1(qs, "title", "") or auto_title
    focus_name = ""
    if spec["focus"] and dataset.focus_options:
        focus_name = dict(dataset.focus_options).get(spec["focus"],
                                                     spec["focus"])
    auto_sub = (f"By {meta['dim_label'].lower()}"
                + (f" · {focus_name}" if focus_name else "")
                + f" · top {meta['n_rows']}")
    subtitle = _qs1(qs, "subtitle", "") or auto_sub
    footnote = _qs1(qs, "footnote", "") or f"Source: {dataset.source}"

    opts = {
        "title": title, "subtitle": subtitle, "palette": palette,
        "suffix": meta["suffix"], "show_values": show_values,
        "legend": legend, "width_px": width_px, "footnote": footnote,
    }
    chart_svg = render_cdd_chart(chart_type, table, opts)

    # ---- Controls -------------------------------------------------------
    # Dataset select, grouped by category via <optgroup>.
    ds_opts = ""
    for cat in fa.categories():
        ds_opts += f'<optgroup label="{html.escape(cat)}">'
        for d in fa.list_datasets():
            if d.category != cat:
                continue
            sel = " selected" if d.id == dataset.id else ""
            ds_opts += (f'<option value="{d.id}"{sel}>'
                        f'{html.escape(d.label)}</option>')
        ds_opts += "</optgroup>"

    # Focus select (county-grain etc.).
    focus_html = ""
    if dataset.focus_options:
        f_opts = "".join(
            f'<option value="{html.escape(v)}"'
            f'{" selected" if v == spec["focus"] else ""}>'
            f'{html.escape(lab)}</option>'
            for v, lab in dataset.focus_options)
        focus_html = (
            f'<label style="font-size:11px;color:#465366;flex:1;">'
            f'{html.escape(dataset.focus_label or "Focus")}'
            f'<select name="focus" style="width:100%;height:30px;border:1px '
            f'solid #c9c1ac;border-radius:5px;">{f_opts}</select></label>')

    # Measure checkboxes.
    sel_measures = set(spec["measures"])
    meas_boxes = ""
    for m in dataset.measures:
        on = m.key in sel_measures
        meas_boxes += (
            f'<label style="display:flex;align-items:center;gap:6px;'
            f'font-size:11.5px;color:#1a2332;border:1px solid '
            f'{"#0b2341" if on else "#d6cfc0"};border-radius:14px;'
            f'padding:3px 10px;background:{"#eef3f2" if on else "#fff"};'
            f'cursor:pointer;">'
            f'<input type="checkbox" name="measures" value="{m.key}"'
            f'{" checked" if on else ""} style="margin:0;">'
            f'{html.escape(m.label)}'
            f'<span style="font-size:9px;color:#7a8699;letter-spacing:.04em;">'
            f'{fa.measure_suffix(m.fmt) or m.fmt}</span></label>')

    # Sort select (label + each measure).
    sort_opts = (f'<option value="_label"'
                 f'{" selected" if spec["sort_key"] == "_label" else ""}>'
                 f'{html.escape(dataset.dim_label)} (name)</option>')
    for m in dataset.measures:
        sel = " selected" if m.key == spec["sort_key"] else ""
        sort_opts += (f'<option value="{m.key}"{sel}>'
                      f'{html.escape(m.label)}</option>')

    pal_opts = "".join(
        f'<option value="{html.escape(p)}"'
        f'{" selected" if p == palette else ""}>{html.escape(p)}</option>'
        for p in PALETTES)

    # Chart-type chips (submit on click so server re-shapes).
    single = fa._SINGLE_SERIES_TYPES
    chips = ""
    for key, label in CHART_TYPES:
        is_sel = key == chart_type
        tag = " ·1" if key in single else ""
        chips += (
            f'<button type="submit" name="type" value="{key}" '
            f'title="{html.escape(label)}'
            f'{" (single series)" if key in single else ""}" '
            f'style="padding:5px 11px;border-radius:14px;cursor:pointer;'
            f'font-size:11.5px;border:1px solid '
            f'{"#0b2341" if is_sel else "#c9c1ac"};'
            f'background:{"#0b2341" if is_sel else "#fff"};'
            f'color:{"#fff" if is_sel else "#465366"};">'
            f'{html.escape(label)}{tag}</button>')

    def _toggle(name, label, on):
        return (
            f'<label style="font-size:11.5px;color:#465366;display:flex;'
            f'align-items:center;gap:5px;"><input type="checkbox" '
            f'name="{name}" value="1"{" checked" if on else ""}>{label}'
            f'</label>')

    size_opts = "".join(
        f'<option value="{k}"{" selected" if k == size else ""}>{k}</option>'
        for k, _w in SIZE_PRESETS)

    asc_opts = (
        f'<option value="0"{"" if spec["ascending"] else " selected"}>'
        f'High → low</option>'
        f'<option value="1"{" selected" if spec["ascending"] else ""}>'
        f'Low → high</option>')

    form = (
        f'<form method="get" action="/further-analysis">'
        # Row 1: dataset + focus + chart-type chips
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;'
        f'margin-bottom:10px;">'
        f'<label style="font-size:11px;color:#465366;flex:2;min-width:240px;">'
        f'Dataset<select name="dataset" onchange="this.form.submit()" '
        f'style="width:100%;height:30px;border:1px solid #c9c1ac;'
        f'border-radius:5px;">{ds_opts}</select></label>'
        f'{focus_html}'
        f'</div>'
        f'<input type="hidden" name="type" value="{chart_type}">'
        f'<div style="font-size:10px;letter-spacing:.06em;color:#7a8699;'
        f'font-weight:700;margin:6px 0 4px;">CHART TYPE</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">'
        f'{chips}</div>'
        # Row 2: measures
        f'<div style="font-size:10px;letter-spacing:.06em;color:#7a8699;'
        f'font-weight:700;margin:6px 0 4px;">MEASURES '
        f'(pick one or more — single-series charts use the first)</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:7px;margin-bottom:12px;">'
        f'{meas_boxes}</div>'
        # Row 3: sort / top / palette / size
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;'
        f'margin-bottom:10px;">'
        f'<label style="font-size:11px;color:#465366;flex:1;min-width:150px;">'
        f'Sort by<select name="sort" style="width:100%;height:30px;border:1px '
        f'solid #c9c1ac;border-radius:5px;">{sort_opts}</select></label>'
        f'<label style="font-size:11px;color:#465366;width:130px;">Order'
        f'<select name="asc" style="width:100%;height:30px;border:1px solid '
        f'#c9c1ac;border-radius:5px;">{asc_opts}</select></label>'
        f'<label style="font-size:11px;color:#465366;width:90px;">Top N'
        f'<input type="number" name="top" min="1" max="60" '
        f'value="{spec["top_n"]}" style="width:100%;height:30px;border:1px '
        f'solid #c9c1ac;border-radius:5px;padding:0 7px;"></label>'
        f'<label style="font-size:11px;color:#465366;flex:1;min-width:130px;">'
        f'Palette<select name="palette" style="width:100%;height:30px;'
        f'border:1px solid #c9c1ac;border-radius:5px;">{pal_opts}</select>'
        f'</label>'
        f'<label style="font-size:11px;color:#465366;width:78px;">Size'
        f'<select name="size" style="width:100%;height:30px;border:1px solid '
        f'#c9c1ac;border-radius:5px;">{size_opts}</select></label>'
        f'</div>'
        # Row 4: titles
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:8px;">'
        f'<label style="font-size:11px;color:#465366;flex:1;min-width:220px;">'
        f'Title<input type="text" name="title" '
        f'value="{html.escape("" if title == auto_title else title)}" '
        f'placeholder="{html.escape(auto_title)}" style="width:100%;height:30px;'
        f'border:1px solid #c9c1ac;border-radius:5px;padding:0 7px;'
        f'font-family:{_SERIF};"></label>'
        f'<label style="font-size:11px;color:#465366;flex:1;min-width:220px;">'
        f'Subtitle<input type="text" name="subtitle" '
        f'value="{html.escape("" if subtitle == auto_sub else subtitle)}" '
        f'placeholder="{html.escape(auto_sub)}" style="width:100%;height:30px;'
        f'border:1px solid #c9c1ac;border-radius:5px;padding:0 7px;"></label>'
        f'</div>'
        f'<div style="display:flex;gap:14px;align-items:center;margin-top:4px;">'
        f'{_toggle("values", "Show values", show_values)}'
        f'{_toggle("legend", "Legend", legend)}'
        f'<button type="submit" style="margin-left:auto;padding:9px 20px;'
        f'background:#0b2341;color:#fff;border:none;border-radius:5px;'
        f'font-weight:600;cursor:pointer;">Render</button>'
        f'<a href="/further-analysis?dataset={dataset.id}" '
        f'style="font-size:11.5px;color:#1F7A75;">Reset</a>'
        f'</div>'
        f'</form>')

    # ---- Chart-type gallery (same query, every type) --------------------
    gallery = ""
    gtypes = ["bar", "column", "column_stacked", "line", "area", "dot",
              "pie", "donut", "marimekko", "radar", "heatmap", "scatter"]
    for gt in gtypes:
        gsvg = render_cdd_chart(
            gt, table, {"title": dict(CHART_TYPES).get(gt, gt),
                        "palette": palette, "W": 330, "H": 210, "px_h": 180,
                        "legend": False, "show_values": False,
                        "suffix": meta["suffix"]})
        href = _share_url(spec, type=gt)
        gallery += (
            f'<a href="{html.escape(href, quote=True)}" '
            f'style="display:block;border:1px solid '
            f'{"#0b2341" if gt == chart_type else "#d6cfc0"};'
            f'border-radius:6px;padding:4px;background:#fff;'
            f'text-decoration:none;">{gsvg}</a>')

    # ---- Data table (the exact rows behind the chart) -------------------
    thead = "".join(f'<th style="text-align:right;padding:4px 9px;'
                    f'font-size:10px;letter-spacing:.04em;color:#7a8699;">'
                    f'{html.escape(h)}</th>'
                    for h in table["headers"][1:])
    tbody = ""
    for lbl, vals in table["rows"]:
        cells = ""
        for v in vals:
            disp = "—" if v is None else f"{v:,.2f}"
            cells += (f'<td style="text-align:right;padding:4px 9px;'
                      f'font-variant-numeric:tabular-nums;font-size:12px;'
                      f'color:#1a2332;">{disp}</td>')
        tbody += (f'<tr><td style="padding:4px 9px;font-size:12px;'
                  f'color:#1a2332;">{html.escape(lbl)}</td>{cells}</tr>')
    data_table = (
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th style="text-align:left;padding:4px 9px;font-size:10px;'
        f'letter-spacing:.04em;color:#7a8699;">'
        f'{html.escape(table["headers"][0])}</th>{thead}</tr></thead>'
        f'<tbody>{tbody}</tbody></table>')

    body = (
        ck_page_title(
            "Further Analysis",
            eyebrow="UTILITY · DATA EXPLORER",
            meta="Slice every vendored public dataset — CMS, CDC, Census, "
                 "labor, market comps — into client-ready, exportable charts.",
        )
        + ck_source_purpose(
            purpose="Build any chart from the platform's real public data — "
                    "pick a dataset, measures and a chart type, export the "
                    "PNG. Thousands of slices, all from vendored sources.",
            universe=f"{len(fa.list_datasets())} datasets · "
                     f"{len(CHART_TYPES)} chart types",
            source="All series are real vendored public data (CMS / CDC / "
                   "Census / BLS-based / market comps). No synthetic data.",
        )
        + '<div class="ts-wrap" style="max-width:1080px;">'
        + '<div style="border:1px solid #d6cfc0;border-radius:8px;'
          'padding:16px;background:#faf8f3;margin-bottom:16px;">'
        + form
        + '</div>'
        + '<div style="border:1px solid #d6cfc0;border-radius:8px;padding:16px;'
          'background:#fff;text-align:center;">'
        + f'<div id="faOut">{chart_svg}</div>'
        + chart_export_toolbar("faOut", "further-analysis-" + dataset.id)
        + '</div>'
        + '<div style="font-size:10px;letter-spacing:.06em;color:#7a8699;'
          'font-weight:700;margin:18px 0 6px;">SAME QUERY, EVERY CHART '
          '(click to switch)</div>'
        + '<div style="display:grid;grid-template-columns:repeat(auto-fill,'
          'minmax(250px,1fr));gap:10px;">' + gallery + '</div>'
        + '<div style="font-size:10px;letter-spacing:.06em;color:#7a8699;'
          'font-weight:700;margin:18px 0 6px;">DATA BEHIND THE CHART</div>'
        + '<div style="border:1px solid #e4ddca;border-radius:8px;'
          'padding:10px 6px;background:#fff;overflow-x:auto;">'
        + data_table + '</div>'
        + f'<p style="font-size:11.5px;color:#465366;margin-top:14px;'
          f'line-height:1.6;"><strong>{html.escape(dataset.label)}</strong> — '
          f'{html.escape(dataset.note)} Grain: {html.escape(dataset.grain)}. '
          f'JSON: <a href="/api/further-analysis" style="color:#1F7A75;">'
          f'/api/further-analysis</a> (every dataset + measure, machine '
          f'readable).</p>'
        + '</div>')
    return chartis_shell(
        body, "Further Analysis", active_nav="/research",
        subtitle="Data explorer")
