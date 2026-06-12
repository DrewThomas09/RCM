"""Chart Builder — the CDD/Excel chart family, made in the browser.

Pick a chart type, paste a table (Excel paste — headers in row 1, a
category column + one column per series), set a title and a Chartis
palette, and it renders a clean, centered SVG. A gallery strip renders
the same data across every chart type so you can pick the right one.

All rendering is in ``cdd_chart_kit``; this page is the form + layout.
Driven entirely by the query string so a configured chart is a
shareable URL.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, Optional

from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
from .saved_charts_page import save_chart_form as _save_chart_form
from .cdd_chart_kit import (
    CHART_TYPES, PALETTES, SIZE_PRESETS, TRANSFORM_CALCS, TRANSFORM_GROUPS,
    parse_table, render_cdd_chart, table_to_tsv, transform_table,
    chart_export_toolbar, _series,
)

_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")

# Sensible example tables per chart family (overwrite with your own).
_EXAMPLE_TS = ("Year\tRevenue\tEBITDA\n2021\t100\t22\n2022\t130\t31\n"
               "2023\t165\t43\n2024\t210\t58")
_EXAMPLE_PIE = "Segment\tShare\nAIC\t38\nHome\t30\nHOPD\t22\nOffice\t10"
_EXAMPLE_WF = ("Step\tValue\nEntry EBITDA\t100\nDenial recovery\t18\n"
               "Throughput\t25\nPayer mix\t12\nExit EBITDA\t=155")
_EXAMPLE_SCATTER = ("Company\tGrowth\tMargin\tRevenue\nApex\t12\t22\t40\n"
                    "Meridian\t8\t28\t60\nVertex\t20\t15\t25\n"
                    "Keystone\t15\t30\t80")
_EXAMPLE_FUNNEL = ("Stage\tValue\nTAM\t3360\nSAM\t1950\nSOM\t420\n"
                   "Year-1 capture\t95")
_EXAMPLE_TORNADO = ("Driver\tImpact\nChair utilization\t114\n"
                    "Commercial mix\t47\nDrug spread\t31\n"
                    "Nurse productivity\t-28\nDenials\t-19")
_EXAMPLE_RADAR = ("Attribute\tTarget\tBenchmark\nScale\t8\t6\n"
                  "Margin\t6\t9\nGrowth\t9\t5\nQuality\t7\t8\nRisk\t5\t7")
_EXAMPLE_BULLET = ("KPI\tActual\tTarget\nClean-claim %\t96\t98\n"
                   "Denial %\t8\t6\nDAR (days)\t45\t40")
_EXAMPLE_SLOPE = ("Metric\tEntry\tExit\nEBITDA margin\t18\t26\n"
                  "Denial rate\t12\t6\nDAR days\t52\t41")
_EXAMPLE_GANTT = ("Workstream\tStart\tEnd\nRCM diagnostic\t0\t4\n"
                  "Denials program\t2\t9\nPayer renegotiation\t4\t12\n"
                  "Systems migration\t6\t16")
_EXAMPLE_PARETO = ("Denial reason\tCount\nPrior auth\t340\nEligibility\t210\n"
                   "Coding\t160\nTimely filing\t90\nMedical necessity\t60\n"
                   "Other\t40")
_EXAMPLE_HIST = ("Account\tDAR days\nA1\t34\nA2\t41\nA3\t38\nA4\t52\n"
                 "A5\t47\nA6\t44\nA7\t39\nA8\t61\nA9\t46\nA10\t43\n"
                 "A11\t55\nA12\t37\nA13\t49\nA14\t42")
_EXAMPLE_BOX = ("Site\tJan\tFeb\tMar\tApr\tMay\tJun\n"
                "North\t42\t45\t39\t48\t44\t41\n"
                "Central\t55\t49\t61\t58\t52\t57\n"
                "South\t38\t36\t41\t35\t39\t37")
_EXAMPLE_DUMBBELL = ("Metric\tEntry\tExit\nEBITDA margin\t18\t26\n"
                     "Clean-claim %\t88\t96\nCollections %\t91\t97\n"
                     "Commercial mix\t34\t41")


def _example_for(ctype: str) -> str:
    if ctype in ("pie", "donut", "waffle"):
        return _EXAMPLE_PIE
    if ctype == "waterfall":
        return _EXAMPLE_WF
    if ctype in ("scatter", "bubble", "matrix"):
        return _EXAMPLE_SCATTER
    if ctype == "funnel":
        return _EXAMPLE_FUNNEL
    if ctype == "tornado":
        return _EXAMPLE_TORNADO
    if ctype == "radar":
        return _EXAMPLE_RADAR
    if ctype == "bullet":
        return _EXAMPLE_BULLET
    if ctype == "slope":
        return _EXAMPLE_SLOPE
    if ctype == "gantt":
        return _EXAMPLE_GANTT
    if ctype == "pareto":
        return _EXAMPLE_PARETO
    if ctype == "histogram":
        return _EXAMPLE_HIST
    if ctype == "boxplot":
        return _EXAMPLE_BOX
    if ctype == "dumbbell":
        return _EXAMPLE_DUMBBELL
    return _EXAMPLE_TS


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


def render_chart_builder_page(qs: "Dict[str, Any] | None" = None) -> str:
    ctype = _qs1(qs, "type", "column")
    if ctype not in dict(CHART_TYPES):
        ctype = "column"
    palette = _qs1(qs, "palette", "Chartis")
    if palette not in PALETTES:
        palette = "Chartis"
    title = _qs1(qs, "title", "")
    subtitle = _qs1(qs, "subtitle", "")
    suffix = _qs1(qs, "suffix", "")
    # Unchecked checkboxes simply vanish from a GET submit, so default-
    # True toggles could never be turned OFF (the absent param fell back
    # to True). The form carries a hidden fs=1 marker; when present,
    # absence means unchecked. Gallery / dataset / shared links don't
    # carry fs, so they keep the friendly defaults.
    submitted = _qs1(qs, "fs", "") == "1"
    show_values = _qsbool(qs, "values", not submitted)
    legend = _qsbool(qs, "legend", not submitted)
    footnote = _qs1(qs, "footnote", "")
    size = _qs1(qs, "size", "M")
    width_px = dict(SIZE_PRESETS).get(size, 720)
    data_text = _qs1(qs, "data", "")
    if not data_text.strip():
        data_text = _example_for(ctype)
    table = parse_table(data_text)
    # Data shaping — the Excel prep steps as dropdowns.
    group = _qs1(qs, "group", "")
    if group not in TRANSFORM_GROUPS:
        group = ""
    sort = _qs1(qs, "sort", "")
    if sort not in ("asc", "desc"):
        sort = ""
    calc = _qs1(qs, "calc", "")
    if calc not in dict(TRANSFORM_CALCS):
        calc = ""
    topn_s = _qs1(qs, "topn", "")
    try:
        topn = max(1, min(50, int(topn_s))) if topn_s.strip() else 0
    except ValueError:
        topn = 0
    trend = _qsbool(qs, "trend", False)
    # Annotations — drawn on the chart over value axes.
    refval_s = _qs1(qs, "refval", "")
    try:
        refval: "float | None" = float(refval_s) if refval_s.strip() \
            else None
    except ValueError:
        refval = None
    reflabel = _qs1(qs, "reflabel", "")
    show_cagr = _qsbool(qs, "cagr", False)
    show_avg = _qsbool(qs, "avg", False)
    bins_s = _qs1(qs, "bins", "")
    try:
        bins = max(2, min(24, int(bins_s))) if bins_s.strip() else 0
    except ValueError:
        bins = 0
    if group or sort or calc or topn:
        table = transform_table(table, {
            "group": group or None, "sort": sort or None,
            "top_n": topn or None, "calc": calc or None})
    # Per-series colour overrides (sc{i}); blanks fall back to the palette.
    base_pal = PALETTES.get(palette, PALETTES["Chartis"])
    series = _series(table)
    n_series = max(len(series), len(table.get("rows", [])) if ctype in
                   ("pie", "donut", "funnel", "tornado", "dot", "matrix",
                    "marimekko") else 0)
    series_colors = []
    for i in range(max(n_series, 1)):
        c = _qs1(qs, f"sc{i}", "")
        series_colors.append(c or base_pal[i % len(base_pal)])
    opts = {
        "title": title or dict(CHART_TYPES).get(ctype, ""),
        "subtitle": subtitle, "palette": palette, "suffix": suffix,
        "show_values": show_values, "legend": legend, "width_px": width_px,
        "colors": series_colors, "footnote": footnote, "trendline": trend,
        "ref_value": refval, "ref_label": reflabel,
        "show_cagr": show_cagr, "show_avg": show_avg,
        "bins": bins or None,
    }
    chart_svg = render_cdd_chart(ctype, table, opts)

    # Per-series / per-category colour pickers.
    color_labels = ([s["name"] for s in series]
                    if ctype not in ("pie", "donut", "funnel", "tornado",
                                     "dot", "matrix", "marimekko")
                    else [r[0] for r in table.get("rows", [])])
    color_pickers = ""
    for i, lab in enumerate(color_labels[:10]):
        color_pickers += (
            f'<label style="display:flex;align-items:center;gap:5px;'
            f'font-size:11px;color:#465366;">'
            f'<input type="color" name="sc{i}" '
            f'value="{html.escape(series_colors[i])}" style="width:34px;'
            f'height:26px;border:1px solid #c9c1ac;border-radius:4px;'
            f'padding:0;background:#fff;cursor:pointer;">'
            f'{html.escape(str(lab))[:18]}</label>')

    # Chart-type selector (chips).
    chips = ""
    for key, label in CHART_TYPES:
        sel = key == ctype
        chips += (
            f'<button type="submit" name="type" value="{key}" '
            f'style="padding:5px 11px;border-radius:14px;cursor:pointer;'
            f'font-size:11.5px;border:1px solid '
            f'{"#0b2341" if sel else "#c9c1ac"};'
            f'background:{"#0b2341" if sel else "#fff"};'
            f'color:{"#fff" if sel else "#465366"};">{html.escape(label)}'
            f'</button>')

    pal_opts = "".join(
        f'<option value="{p}"{" selected" if p == palette else ""}>{p}'
        f'</option>' for p in PALETTES)

    def _toggle(name, label, on):
        return (
            f'<label style="font-size:11.5px;color:#465366;display:flex;'
            f'align-items:center;gap:5px;"><input type="checkbox" '
            f'name="{name}" value="1"{" checked" if on else ""}>{label}'
            f'</label>')

    _sel = ('height:28px;border:1px solid #c9c1ac;border-radius:5px;'
            'width:100%;font-size:11.5px;')

    def _shaping_select(name, label, options, current):
        opts_html = "".join(
            f'<option value="{html.escape(v, quote=True)}"'
            f'{" selected" if v == current else ""}>{html.escape(lab)}'
            f'</option>' for v, lab in options)
        return (f'<label style="font-size:10.5px;color:#465366;flex:1;'
                f'min-width:108px;">{label}'
                f'<select name="{name}" style="{_sel}">{opts_html}'
                f'</select></label>')

    shaping = (
        '<div style="margin-top:8px;border:1px solid #d6cfc0;'
        'border-radius:6px;padding:8px 10px;background:#faf7f0;">'
        '<div style="font-size:10px;letter-spacing:0.06em;color:#7a8699;'
        'font-weight:700;margin-bottom:5px;">DATA SHAPING (applied before '
        'the chart — no Excel prep needed)</div>'
        '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:'
        'flex-end;">'
        + _shaping_select("group", "Group duplicate labels",
                          [("", "Off")] + [(g, f"Aggregate: {g}")
                                           for g in TRANSFORM_GROUPS], group)
        + _shaping_select("sort", "Sort by first series",
                          [("", "Keep order"), ("desc", "Largest first"),
                           ("asc", "Smallest first")], sort)
        + (f'<label style="font-size:10.5px;color:#465366;width:96px;">'
           f'Top N (+ Other)<input type="number" name="topn" min="1" '
           f'max="50" value="{topn if topn else ""}" style="{_sel}'
           f'padding:0 6px;"></label>')
        + _shaping_select("calc", "Calculation",
                          [("", "None")] + list(TRANSFORM_CALCS), calc)
        + _toggle("trend", "Trendline + R² (line/scatter)", trend)
        + '</div></div>'
        # Annotations — overlays on the value axis (column/line/combo).
        + '<div style="margin-top:8px;border:1px solid #d6cfc0;'
        'border-radius:6px;padding:8px 10px;background:#faf7f0;">'
        '<div style="font-size:10px;letter-spacing:0.06em;color:#7a8699;'
        'font-weight:700;margin-bottom:5px;">ANNOTATIONS (column / bar / '
        'line / area / combo)</div>'
        '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:'
        'flex-end;">'
        + (f'<label style="font-size:10.5px;color:#465366;width:110px;">'
           f'Reference line at<input type="number" step="any" '
           f'name="refval" value="{html.escape(refval_s)}" '
           f'placeholder="e.g. 98" style="{_sel}padding:0 6px;"></label>')
        + (f'<label style="font-size:10.5px;color:#465366;flex:1;'
           f'min-width:120px;">Reference label'
           f'<input type="text" name="reflabel" '
           f'value="{html.escape(reflabel)}" placeholder="Target" '
           f'style="{_sel}padding:0 6px;"></label>')
        + _toggle("cagr", "CAGR tag (first→last)", show_cagr)
        + _toggle("avg", "Average line", show_avg)
        + '</div></div>')

    form = (
        f'<form method="get" action="/chart-builder">'
        # Marks a real form submit so absent checkboxes read as
        # unchecked (links without fs keep default-on toggles).
        f'<input type="hidden" name="fs" value="1">'
        f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;">'
        f'{chips}</div>'
        f'<input type="hidden" name="type" value="{ctype}">'
        f'<div style="display:grid;grid-template-columns:1.3fr 1fr;gap:18px;'
        f'align-items:start;">'
        # Left: data
        f'<div><label style="font-size:11px;color:#465366;font-weight:600;">'
        f'Data (paste from Excel — headers in row 1, category column + one '
        f'column per series)'
        f'<textarea name="data" rows="9" style="width:100%;margin-top:4px;'
        f'font-family:ui-monospace,Menlo,monospace;font-size:12px;'
        f'border:1px solid #c9c1ac;border-radius:5px;padding:8px;">'
        f'{html.escape(data_text)}</textarea></label>'
        f'{shaping}</div>'
        # Right: options
        f'<div style="display:flex;flex-direction:column;gap:9px;">'
        f'<label style="font-size:11px;color:#465366;">Title'
        f'<input type="text" name="title" value="{html.escape(title)}" '
        f'style="width:100%;height:30px;border:1px solid #c9c1ac;'
        f'border-radius:5px;padding:0 7px;font-family:{_SERIF};"></label>'
        f'<label style="font-size:11px;color:#465366;">Subtitle'
        f'<input type="text" name="subtitle" value="{html.escape(subtitle)}" '
        f'style="width:100%;height:30px;border:1px solid #c9c1ac;'
        f'border-radius:5px;padding:0 7px;"></label>'
        f'<label style="font-size:11px;color:#465366;">Source / footnote'
        f'<input type="text" name="footnote" value="{html.escape(footnote)}" '
        f'placeholder="Source: …" style="width:100%;height:30px;border:1px '
        f'solid #c9c1ac;border-radius:5px;padding:0 7px;"></label>'
        f'<div style="display:flex;gap:10px;">'
        f'<label style="font-size:11px;color:#465366;flex:1;">Palette'
        f'<select name="palette" style="width:100%;height:30px;'
        f'border:1px solid #c9c1ac;border-radius:5px;">{pal_opts}</select>'
        f'</label>'
        f'<label style="font-size:11px;color:#465366;width:88px;">Unit'
        f'<input type="text" name="suffix" value="{html.escape(suffix)}" '
        f'placeholder="% or $" style="width:100%;height:30px;'
        f'border:1px solid #c9c1ac;border-radius:5px;padding:0 7px;"></label>'
        f'<label style="font-size:11px;color:#465366;width:88px;">'
        f'Bins (hist.)'
        f'<input type="number" name="bins" min="2" max="24" '
        f'value="{bins if bins else ""}" placeholder="auto" '
        f'style="width:100%;height:30px;border:1px solid #c9c1ac;'
        f'border-radius:5px;padding:0 7px;"></label>'
        f'</div>'
        f'<div style="display:flex;gap:14px;margin-top:2px;align-items:center;">'
        f'{_toggle("values", "Show values", show_values)}'
        f'{_toggle("legend", "Legend", legend)}'
        f'<label style="font-size:11px;color:#465366;display:flex;gap:5px;'
        f'align-items:center;margin-left:auto;">Size'
        f'<select name="size" style="height:28px;border:1px solid #c9c1ac;'
        f'border-radius:5px;">' + "".join(
            f'<option value="{k}"{" selected" if k == size else ""}>{k}'
            f'</option>' for k, _w in SIZE_PRESETS)
        + '</select></label></div>'
        + (f'<div style="margin-top:4px;"><div style="font-size:10px;'
           f'letter-spacing:0.06em;color:#7a8699;font-weight:700;'
           f'margin-bottom:4px;">SERIES COLOURS (override the palette)</div>'
           f'<div style="display:flex;flex-wrap:wrap;gap:8px;">'
           f'{color_pickers}</div></div>' if color_pickers else "")
        + f'<button type="submit" style="margin-top:6px;padding:9px 18px;'
        f'background:#0b2341;color:#fff;border:none;border-radius:5px;'
        f'font-weight:600;cursor:pointer;">Render chart</button>'
        f'<a href="/chart-builder?type={ctype}" style="font-size:11.5px;'
        f'color:#1F7A75;">Reset to example data</a>'
        f'</div></div></form>'
        # When the palette changes, re-seed the per-series colour pickers
        # so the dropdown stays meaningful (pickers otherwise override it).
        f'<script>var CKPAL={json.dumps(PALETTES)};'
        f'document.addEventListener("change",function(e){{'
        f'if(e.target&&e.target.name==="palette"){{'
        f'var c=CKPAL[e.target.value]||[];'
        f'document.querySelectorAll(\'input[name^="sc"]\').forEach('
        f'function(inp,i){{if(c.length)inp.value=c[i%c.length];}});}}}});'
        f'</script>')

    # Platform data — one-click real CMS aggregates (built in the data
    # layer, cached per process; each link carries a finished table).
    from ..data.chart_datasets import build_chart_dataset, list_chart_datasets
    ds_chips = ""
    for m in list_chart_datasets():
        d = build_chart_dataset(m["key"])
        href = (f'/chart-builder?type={d["chart"]}'
                f'&title={_urlq(d["label"])}'
                f'&footnote={_urlq(d["footnote"])}'
                f'&data={_urlq(d["tsv"])}')
        ds_chips += (
            f'<a href="{html.escape(href, quote=True)}" '
            f'style="padding:5px 11px;border-radius:14px;font-size:11.5px;'
            f'border:1px solid #9bc1bc;background:#fff;color:#155752;'
            f'text-decoration:none;">{html.escape(d["label"])}</a>')
    datasets_strip = (
        '<div style="margin-top:14px;">'
        '<div style="font-size:10px;letter-spacing:0.06em;color:#7a8699;'
        'font-weight:700;margin-bottom:6px;">PLATFORM DATA — REAL CMS '
        'AGGREGATES (one click to load, then shape and restyle freely)'
        '</div>'
        '<div style="display:flex;flex-wrap:wrap;gap:6px;">'
        + ds_chips + '</div></div>')

    # Gallery — the same data across a few chart types.
    gallery = ""
    gtypes = ["column", "column_stacked", "column_100", "bar", "pareto",
              "line", "area", "waterfall", "pie", "donut", "marimekko",
              "combo"]
    for gt in gtypes:
        gdata = table
        gsvg = render_cdd_chart(
            gt, gdata, {"title": dict(CHART_TYPES).get(gt, gt),
                        "palette": palette, "W": 330, "H": 210,
                        "px_h": 180, "legend": False, "show_values": False})
        gallery += (
            f'<a href="/chart-builder?type={gt}&palette={palette}&data='
            f'{html.escape(_urlq(data_text), quote=True)}" '
            f'style="display:block;border:1px solid '
            f'{"#0b2341" if gt == ctype else "#d6cfc0"};border-radius:6px;'
            f'padding:4px;background:#fff;text-decoration:none;">{gsvg}</a>')

    body = (
        ck_page_title(
            "Chart Builder",
            eyebrow="UTILITY · CDD CHART KIT",
            meta="The Excel chart family — column, stacked, waterfall, "
                 "marimekko, bubble & more — Chartis-styled.",
        )
        + ck_source_purpose(
            purpose="Build the charts a CDD deck needs from a pasted "
                    "table — pick a type, set colours, done.",
            universe="user-supplied",
            source="Your pasted data. Example tables are placeholders — "
                   "overwrite with your own.",
        )
        + '<div class="ts-wrap" style="max-width:1040px;">'
        + form
        + datasets_strip
        + '<div style="margin-top:18px;border:1px solid #d6cfc0;'
          'border-radius:8px;padding:16px;background:#fff;text-align:center;">'
        + f'<div id="chartOut">{chart_svg}</div>'
        + chart_export_toolbar("chartOut", "chart-" + ctype)
        # The shaped table travels, not the raw paste — what you see is
        # what lands on the slide.
        + (f'<div style="margin-top:8px;"><a href="/exhibit?t0={ctype}'
           f'&pt0={_urlq(title or dict(CHART_TYPES).get(ctype, ""))}'
           f'&pal0={_urlq(palette)}'
           + (f'&source={_urlq(footnote)}' if footnote else "")
           + f'&d0={_urlq(table_to_tsv(table))}" '
           f'style="font-size:12px;color:#155752;font-weight:600;">'
           f'→ Send to Exhibit Composer (as panel 1)</a></div>')
        + _save_chart_form("/chart-builder")
        + '</div>'
        + '<div style="font-size:10px;letter-spacing:0.06em;color:#7a8699;'
          'font-weight:700;margin:18px 0 6px;">GALLERY — YOUR DATA IN EVERY '
          'CHART (click to switch)</div>'
        + '<div style="display:grid;grid-template-columns:repeat(auto-fill,'
          'minmax(250px,1fr));gap:10px;">' + gallery + '</div>'
        + '<div style="font-size:12px;color:#465366;line-height:1.7;'
          'margin-top:16px;"><div style="font-size:10px;letter-spacing:'
          '0.06em;color:#7a8699;font-weight:700;margin-bottom:3px;">NOTES'
          '</div><p><strong>Waterfall:</strong> one value column of deltas; '
          'label a row with "total"/"net"/"=" to draw an absolute total '
          'bar. <strong>Scatter/Bubble:</strong> columns are X, Y, [size]. '
          '<strong>Pie/Donut/Marimekko:</strong> use the first value '
          'column(s). <strong>Pareto:</strong> one value column — sorted '
          'bars + cumulative-% line with an 80% marker. '
          '<strong>Histogram:</strong> bins the first value column (one '
          'raw value per row). <strong>Box plot:</strong> each row is a '
          'category, each column a sample — quartiles are computed for '
          'you. <strong>Dumbbell:</strong> two value columns = '
          'before/after per category. Everything else takes a category '
          'column + one column per series. <strong>Waffle:</strong> the '
          'first value column as a 10×10 share grid (1 cell = 1%). '
          '<strong>Small multiples:</strong> one mini line panel per '
          'series on a shared y-scale. <strong>Data shaping</strong> '
          'runs before the chart: aggregate duplicate labels '
          '(sum/mean/max/min/count), sort, keep top-N and lump the rest '
          'into "Other", or switch the values to % of total / cumulative '
          '/ moving average / growth-vs-prior / indexed-to-100. '
          '<strong>Annotations</strong> draw on value-axis charts: a '
          'reference/target line with a label, a dotted average line, '
          'and a CAGR tag computed first→last on the first series.'
          '</p></div>'
        + '</div>')
    return chartis_shell(
        body, "Chart Builder", active_nav="/research",
        subtitle="CDD chart kit")


def _urlq(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(s)
