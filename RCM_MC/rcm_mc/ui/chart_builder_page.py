"""Chart Builder — the CDD/Excel chart family, made in the browser.

Pick a chart type, paste a table (Excel paste — headers in row 1, a
category column + one column per series), set a title and a Chartis
palette, and it renders a clean, centered SVG. A gallery strip renders
the same data across every chart type so you can pick the right one.

All rendering is in ``cdd_chart_kit``; this page is the form + layout.
Driven entirely by the query string so a configured chart is a
shareable URL.

Layout is the v5 chartis editorial idiom: ck_editorial_head masthead,
two ck_panel cards (composer + rendered chart), ck_section_header
section heads (matching the sibling tool pages), and one page-scoped
``.cb-*`` stylesheet (no inline style attributes) built on the kit's
CSS custom properties.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, Optional

from ._chartis_kit import (
    chartis_shell, ck_arrow_link, ck_editorial_head, ck_fmt_number,
    ck_page_actions, ck_panel, ck_section_header, ck_source_purpose,
)
from .saved_charts_page import save_chart_form as _save_chart_form
from .cdd_chart_kit import (
    CHART_TYPES, PALETTES, SIZE_PRESETS, TRANSFORM_CALCS, TRANSFORM_GROUPS,
    parse_table, render_cdd_chart, table_to_tsv, transform_table,
    chart_export_toolbar, _series,
)

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


# Chart-type families for the picker. Presentation-only grouping — the
# chips stay <button type="submit" name="type"> either way, so the form
# contract is untouched. Keys missing from CHART_TYPES are skipped;
# CHART_TYPES keys not claimed here land in a trailing "More" row so a
# newly-registered chart type always gets a chip.
_CHIP_GROUPS: list[tuple[str, tuple[str, ...]]] = [
    ("Comparison", ("column", "column_stacked", "column_100", "bar",
                    "bar_stacked", "dot")),
    ("Trend", ("line", "area", "slope", "combo", "smallmult")),
    ("Composition", ("pie", "donut", "waffle", "marimekko")),
    ("Bridge & flow", ("waterfall", "funnel", "tornado")),
    ("Distribution", ("histogram", "boxplot", "pareto")),
    ("Relationship", ("scatter", "bubble", "matrix", "radar", "heatmap")),
    ("Tracking", ("bullet", "gauge", "dumbbell", "gantt")),
]

# How each chart reads the pasted table — the reference copy that used
# to be a 25-line <p> wall, restructured as scannable term/definition
# pairs inside a <details> so the page stays calm.
_FORMAT_NOTES: list[tuple[str, str]] = [
    ("Waterfall", 'One value column of deltas; label a row with '
                  '"total"/"net"/"=" to draw an absolute total bar.'),
    ("Scatter / Bubble", "Columns are X, Y, [size]."),
    ("Pie / Donut / Marimekko", "Use the first value column(s)."),
    ("Pareto", "One value column — sorted bars plus a cumulative-% line "
               "with an 80% marker."),
    ("Histogram", "Bins the first value column (one raw value per row)."),
    ("Box plot", "Each row is a category, each column a sample — "
                 "quartiles are computed for you."),
    ("Dumbbell", "Two value columns = before/after per category."),
    ("Waffle", "The first value column as a 10×10 share grid "
               "(1 cell = 1%)."),
    ("Small multiples", "One mini line panel per series on a shared "
                        "y-scale."),
    ("Everything else", "A category column + one column per series."),
    ("Data shaping", "Runs before the chart: aggregate duplicate labels "
                     "(sum/mean/max/min/count), sort, keep top-N and lump "
                     'the rest into "Other", or switch the values to % of '
                     "total / cumulative / moving average / "
                     "growth-vs-prior / indexed-to-100."),
    ("Annotations", "Drawn on value-axis charts: a reference/target line "
                    "with a label, a dotted average line, and a CAGR tag "
                    "computed first→last on the first series."),
]

# Page-scoped stylesheet (injected via chartis_shell extra_css). Every
# rule is built on the kit tokens with their canonical fallbacks — no
# ad-hoc hexes, and every interactive control gets :hover +
# :focus-visible states the old inline style attributes couldn't carry.
_PAGE_CSS = """
.cb-wrap{max-width:1040px;margin:0 auto;}
.cb-grid{display:grid;grid-template-columns:1.3fr 1fr;gap:22px;align-items:start;}
@media(max-width:900px){.cb-grid{grid-template-columns:1fr;}}
.cb-kicker{display:flex;align-items:center;gap:8px;font-family:var(--sc-mono,monospace);font-size:10.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--sc-text-dim,#465366);margin:0 0 3px;}
.cb-kicker::before{content:"";flex:0 0 18px;height:1px;background:var(--green-deep,#154e36);}
.cb-sub{font-family:var(--sc-sans,sans-serif);font-size:11.5px;color:var(--sc-text-faint,#7a8699);margin:0 0 9px;}
.cb-typegroups{display:flex;flex-direction:column;gap:6px;margin:6px 0 18px;}
.cb-typegroup{display:flex;gap:12px;align-items:flex-start;}
.cb-typegroup-kicker{flex:0 0 96px;text-align:right;padding-top:6px;font-family:var(--sc-mono,monospace);font-size:9.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--sc-text-faint,#7a8699);}
@media(max-width:700px){.cb-typegroup{flex-direction:column;gap:3px;}.cb-typegroup-kicker{flex:none;text-align:left;padding-top:0;}}
.cb-chips{display:flex;flex-wrap:wrap;gap:5px;}
.cb-chip{padding:4px 9px;border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:#fff;color:var(--sc-text-dim,#465366);font-family:var(--sc-mono,monospace);font-size:10px;letter-spacing:.04em;text-transform:uppercase;cursor:pointer;}
.cb-chip:hover{border-color:var(--sc-teal,#155752);color:var(--sc-teal,#155752);}
.cb-chip.sel{background:var(--sc-navy,#0b2341);border-color:var(--sc-navy,#0b2341);color:var(--sc-on-navy,#e9eef5);}
.cb-field{display:block;font-family:var(--sc-mono,monospace);font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--sc-text-dim,#465366);}
.cb-hint{display:block;margin:2px 0 0;font-family:var(--sc-sans,sans-serif);font-size:11px;font-weight:400;letter-spacing:0;text-transform:none;color:var(--sc-text-faint,#7a8699);}
.cb-input,.cb-select,.cb-textarea{box-sizing:border-box;width:100%;margin-top:4px;border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:#fff;color:var(--ink,#16263a);font-family:var(--sc-sans,sans-serif);font-size:12px;}
.cb-input{height:30px;padding:0 8px;}
.cb-select{height:30px;padding:0 4px;}
.cb-textarea{padding:8px;font-family:var(--sc-mono,ui-monospace,Menlo,monospace);line-height:1.5;}
.cb-input-serif{font-family:var(--sc-serif,'Source Serif 4',Georgia,serif);}
.cb-parse-note{margin-top:5px;font-family:var(--sc-mono,monospace);font-size:10.5px;letter-spacing:.03em;font-variant-numeric:tabular-nums;color:var(--sc-text-faint,#7a8699);}
.cb-parse-note.warn{color:var(--sc-warning,#b8732a);}
.cb-check{display:flex;align-items:center;gap:5px;font-family:var(--sc-sans,sans-serif);font-size:11.5px;color:var(--sc-text-dim,#465366);}
.cb-shaping{margin-top:12px;padding:10px 12px;border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:var(--sc-parchment,#f2ede3);}
.cb-row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;}
.cb-flex1{flex:1;min-width:108px;}
.cb-w96{width:96px;}
.cb-w110{width:110px;}
.cb-minw120{flex:1;min-width:120px;}
.cb-opts{display:flex;flex-direction:column;gap:11px;}
.cb-push{margin-left:auto;}
.cb-wauto{width:auto;margin-top:0;}
.cb-colors{display:flex;flex-wrap:wrap;gap:8px;}
.cb-color{display:flex;align-items:center;gap:5px;font-family:var(--sc-sans,sans-serif);font-size:11px;color:var(--sc-text-dim,#465366);}
.cb-color input[type=color]{width:34px;height:26px;padding:0;border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:#fff;cursor:pointer;}
.cb-actions{display:flex;align-items:center;gap:18px;margin-top:4px;}
.cb-btn{padding:9px 20px;border:1px solid var(--sc-navy,#0b2341);border-radius:2px;background:var(--sc-navy,#0b2341);color:var(--sc-on-navy,#e9eef5);font-family:var(--sc-sans,sans-serif);font-size:12px;font-weight:600;letter-spacing:.04em;cursor:pointer;}
.cb-btn:hover{background:var(--sc-navy-2,#132e53);border-color:var(--sc-navy-2,#132e53);}
.cb-reset{font-family:var(--sc-mono,monospace);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--sc-teal,#155752);text-decoration:none;}
.cb-reset:hover{color:var(--sc-navy,#0b2341);text-decoration:underline;}
.cb-section-lede{font-family:var(--sc-serif,Georgia,serif);font-size:14px;line-height:1.55;color:var(--sc-text-dim,#465366);max-width:64ch;margin:0 0 var(--sc-s-6,28px);}
.cb-section-lede em{font-style:italic;color:var(--green-deep,#154e36);}
.cb-ds-chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 var(--sc-s-6,28px);}
.cb-ds-chip{display:inline-flex;align-items:center;gap:7px;padding:6px 12px;border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:var(--paper-card,#fefcf3);color:var(--sc-teal-ink,#0f3d39);font-family:var(--sc-sans,sans-serif);font-size:12px;font-weight:600;text-decoration:none;}
.cb-ds-chip::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--sc-teal,#155752);}
.cb-ds-chip:hover{border-color:var(--sc-teal,#155752);background:#fff;}
.cb-canvas{text-align:center;}
.cb-canvas #chartOut{display:flex;justify-content:center;}
.cb-canvas #chartOut svg{display:block;margin:0 auto;max-width:100%;}
.cb-canvas-actions{margin-top:14px;padding-top:14px;border-top:1px solid var(--sc-rule,#d6cfc0);}
.cb-btn-ghost{margin-left:14px;padding:6px 12px;border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:#fff;color:var(--sc-navy,#0b2341);font-family:var(--sc-sans,sans-serif);font-size:11.5px;font-weight:600;cursor:pointer;}
.cb-btn-ghost:hover{border-color:var(--sc-teal,#155752);color:var(--sc-teal,#155752);}
.cb-hidden{display:none;}
.cb-gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px;}
.cb-gallery-card{display:block;padding:6px;border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:var(--paper-card,#fefcf3);text-decoration:none;}
.cb-gallery-card:hover{border-color:var(--sc-teal,#155752);}
.cb-gallery-card.sel{border-color:var(--sc-navy,#0b2341);box-shadow:inset 0 0 0 1px var(--sc-navy,#0b2341);}
.cb-gallery-cap{display:block;margin-top:4px;text-align:center;font-family:var(--sc-mono,monospace);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--sc-text-faint,#7a8699);}
.cb-notes{margin-top:var(--sc-s-6,28px);border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:var(--paper-card,#fefcf3);}
.cb-notes summary{padding:10px 14px;cursor:pointer;font-family:var(--sc-mono,monospace);font-size:10.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--sc-text-dim,#465366);}
.cb-notes summary:hover{color:var(--sc-teal,#155752);}
.cb-notes[open] summary{border-bottom:1px solid var(--sc-rule,#d6cfc0);}
.cb-notes-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px 26px;margin:0;padding:14px;}
.cb-note dt{font-family:var(--sc-sans,sans-serif);font-size:11.5px;font-weight:600;color:var(--ink,#16263a);}
.cb-note dd{margin:2px 0 0;font-family:var(--sc-serif,Georgia,serif);font-size:13px;line-height:1.5;color:var(--sc-text-dim,#465366);}
.cb-chip:focus-visible,.cb-btn:focus-visible,.cb-btn-ghost:focus-visible,.cb-reset:focus-visible,.cb-ds-chip:focus-visible,.cb-gallery-card:focus-visible,.cb-input:focus-visible,.cb-select:focus-visible,.cb-textarea:focus-visible,.cb-check input:focus-visible,.cb-color input:focus-visible,.cb-notes summary:focus-visible{outline:2px solid var(--sc-teal,#155752);outline-offset:1px;}
"""


def _chip_groups_html(ctype: str) -> str:
    """Grouped chart-type picker. Every chip stays a submit button
    carrying name="type" — clicking one switches the chart without
    losing the rest of the form state."""
    labels = dict(CHART_TYPES)
    claimed: set[str] = set()
    groups: list[tuple[str, list[str]]] = []
    for gname, keys in _CHIP_GROUPS:
        present = [k for k in keys if k in labels]
        claimed.update(present)
        groups.append((gname, present))
    leftover = [k for k, _ in CHART_TYPES if k not in claimed]
    if leftover:
        groups.append(("More", leftover))
    out = ['<div class="cb-typegroups" role="group" '
           'aria-label="Chart type">']
    for gname, keys in groups:
        if not keys:
            continue
        chips = "".join(
            f'<button type="submit" name="type" value="{k}" '
            f'class="cb-chip{" sel" if k == ctype else ""}" '
            f'aria-pressed="{"true" if k == ctype else "false"}">'
            f'{html.escape(labels[k])}</button>'
            for k in keys)
        out.append(
            f'<div class="cb-typegroup">'
            f'<span class="cb-typegroup-kicker">{html.escape(gname)}</span>'
            f'<span class="cb-chips">{chips}</span></div>')
    out.append('</div>')
    return "".join(out)


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
    # Parse feedback for the strip under the textarea — computed on the
    # RAW paste (before shaping) so a malformed paste explains itself
    # instead of silently rendering a distorted chart. Copy avoids the
    # word None: a literal >None< anywhere in page HTML trips the
    # route-walker nan/None-leak gate.
    raw_rows = len(table.get("rows", []))
    raw_series = len(_series(table))
    raw_has_blanks = any(
        v is None for _lab, vals in table.get("rows", []) for v in vals)
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
            f'<label class="cb-color" title="{html.escape(str(lab))}">'
            f'<input type="color" name="sc{i}" '
            f'value="{html.escape(series_colors[i])}">'
            f'{html.escape(str(lab))[:18]}</label>')

    pal_opts = "".join(
        f'<option value="{p}"{" selected" if p == palette else ""}>{p}'
        f'</option>' for p in PALETTES)

    def _toggle(name, label, on):
        return (
            f'<label class="cb-check"><input type="checkbox" '
            f'name="{name}" value="1"{" checked" if on else ""}>{label}'
            f'</label>')

    def _shaping_select(name, label, options, current, cls="cb-flex1"):
        opts_html = "".join(
            f'<option value="{html.escape(v, quote=True)}"'
            f'{" selected" if v == current else ""}>{html.escape(lab)}'
            f'</option>' for v, lab in options)
        return (f'<label class="cb-field {cls}">{label}'
                f'<select name="{name}" class="cb-select">{opts_html}'
                f'</select></label>')

    shaping = (
        '<div class="cb-shaping">'
        '<div class="cb-kicker">DATA SHAPING</div>'
        '<div class="cb-sub">Applied before the chart — no Excel prep '
        'needed.</div>'
        '<div class="cb-row">'
        + _shaping_select("group", "Group duplicate labels",
                          [("", "Off")] + [(g, f"Aggregate: {g}")
                                           for g in TRANSFORM_GROUPS], group)
        + _shaping_select("sort", "Sort by first series",
                          [("", "Keep order"), ("desc", "Largest first"),
                           ("asc", "Smallest first")], sort)
        + (f'<label class="cb-field cb-w96">Top N (+ Other)'
           f'<input type="number" name="topn" min="1" '
           f'max="50" value="{topn if topn else ""}" class="cb-input">'
           f'</label>')
        + _shaping_select("calc", "Calculation",
                          # "Off", never "None": a literal >None< in page HTML
                          # trips the route-walker nan/None-leak gate (same
                          # convention as pie_chart_page / group dropdown above).
                          [("", "Off")] + list(TRANSFORM_CALCS), calc)
        + _toggle("trend", "Trendline + R² (line/scatter)", trend)
        + '</div></div>'
        # Annotations — overlays on the value axis (column/line/combo).
        + '<div class="cb-shaping">'
        '<div class="cb-kicker">ANNOTATIONS</div>'
        '<div class="cb-sub">Overlays for column / bar / line / area / '
        'combo charts.</div>'
        '<div class="cb-row">'
        + (f'<label class="cb-field cb-w110">Reference line at'
           f'<input type="number" step="any" '
           f'name="refval" value="{html.escape(refval_s)}" '
           f'placeholder="e.g. 98" class="cb-input"></label>')
        + (f'<label class="cb-field cb-minw120">Reference label'
           f'<input type="text" name="reflabel" '
           f'value="{html.escape(reflabel)}" placeholder="Target" '
           f'class="cb-input"></label>')
        + _toggle("cagr", "CAGR tag (first→last)", show_cagr)
        + _toggle("avg", "Average line", show_avg)
        + '</div></div>')

    parse_note = (
        f'<div class="cb-parse-note{" warn" if raw_has_blanks else ""}">'
        f'Parsed {ck_fmt_number(raw_rows)} '
        f'row{"s" if raw_rows != 1 else ""} × '
        f'{ck_fmt_number(raw_series)} '
        f'series{" · non-numeric cells ignored" if raw_has_blanks else ""}'
        f'</div>')

    form = (
        '<form method="get" action="/chart-builder">'
        # Marks a real form submit so absent checkboxes read as
        # unchecked (links without fs keep default-on toggles).
        '<input type="hidden" name="fs" value="1">'
        '<div class="cb-kicker">CHART TYPE</div>'
        + _chip_groups_html(ctype)
        + f'<input type="hidden" name="type" value="{ctype}">'
        f'<div class="cb-grid">'
        # Left: data
        f'<div><label class="cb-field">Data'
        f'<span class="cb-hint">Paste from Excel — headers in row 1, a '
        f'category column + one column per series.</span>'
        f'<textarea name="data" rows="9" class="cb-textarea">'
        f'{html.escape(data_text)}</textarea></label>'
        f'{parse_note}'
        f'{shaping}</div>'
        # Right: options
        f'<div class="cb-opts">'
        f'<label class="cb-field">Title'
        f'<input type="text" name="title" value="{html.escape(title)}" '
        f'class="cb-input cb-input-serif"></label>'
        f'<label class="cb-field">Subtitle'
        f'<input type="text" name="subtitle" value="{html.escape(subtitle)}" '
        f'class="cb-input"></label>'
        f'<label class="cb-field">Source / footnote'
        f'<input type="text" name="footnote" value="{html.escape(footnote)}" '
        f'placeholder="Source: …" class="cb-input"></label>'
        f'<div class="cb-row">'
        f'<label class="cb-field cb-flex1">Palette'
        f'<select name="palette" class="cb-select">{pal_opts}</select>'
        f'</label>'
        f'<label class="cb-field cb-w96">Unit'
        f'<input type="text" name="suffix" value="{html.escape(suffix)}" '
        f'placeholder="% or $" class="cb-input"></label>'
        f'<label class="cb-field cb-w110">Histogram bins'
        f'<input type="number" name="bins" min="2" max="24" '
        f'value="{bins if bins else ""}" placeholder="auto" '
        f'class="cb-input"></label>'
        f'</div>'
        f'<div class="cb-row">'
        f'{_toggle("values", "Show values", show_values)}'
        f'{_toggle("legend", "Legend", legend)}'
        f'<label class="cb-check cb-push">Size'
        f'<select name="size" class="cb-select cb-wauto">' + "".join(
            f'<option value="{k}"{" selected" if k == size else ""}>'
            f'{k} · {w}px</option>' for k, w in SIZE_PRESETS)
        + '</select></label></div>'
        + (f'<div><div class="cb-kicker">SERIES COLOURS</div>'
           f'<div class="cb-sub">Override the palette per series — picking '
           f'a new palette re-seeds these.</div>'
           f'<div class="cb-colors">{color_pickers}</div></div>'
           if color_pickers else "")
        + '<div class="cb-actions">'
        '<button type="submit" class="cb-btn">Render chart</button>'
        + f'<a href="/chart-builder?type={ctype}" class="cb-reset">'
        f'Reset to example data</a>'
        f'</div></div></div></form>'
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
            f'class="cb-ds-chip">{html.escape(d["label"])}</a>')
    datasets_strip = (
        ck_section_header(
            "Real CMS aggregates, one click away.",
            eyebrow="PLATFORM DATA")
        + '<p class="cb-section-lede">Load a finished table from the '
          "platform's public-data layer, then shape and restyle it "
          "freely — the configured chart stays <em>a shareable "
          "URL</em>.</p>"
        + f'<div class="cb-ds-chips">{ds_chips}</div>')

    # Gallery — the same data across a few chart types.
    gallery = ""
    gtypes = ["column", "column_stacked", "column_100", "bar", "pareto",
              "line", "area", "waterfall", "pie", "donut", "marimekko",
              "combo"]
    type_labels = dict(CHART_TYPES)
    for gt in gtypes:
        gdata = table
        gsvg = render_cdd_chart(
            gt, gdata, {"title": type_labels.get(gt, gt),
                        "palette": palette, "W": 330, "H": 210,
                        "px_h": 180, "legend": False, "show_values": False})
        glabel = type_labels.get(gt, gt)
        gallery += (
            f'<a href="/chart-builder?type={gt}&palette={palette}&data='
            f'{html.escape(_urlq(data_text), quote=True)}" '
            f'class="cb-gallery-card{" sel" if gt == ctype else ""}" '
            f'aria-label="Switch to {html.escape(glabel, quote=True)}">'
            f'{gsvg}'
            f'<span class="cb-gallery-cap">{html.escape(glabel)}</span>'
            f'</a>')

    # Rendered chart + its quiet action row (export toolbar, send to
    # Exhibit Composer, shaped-TSV copy-out, save-to-library) in one
    # ck_panel so the canvas has a panel identity like every other
    # editorial surface.
    exhibit_href = (
        f'/exhibit?t0={ctype}'
        f'&pt0={_urlq(title or dict(CHART_TYPES).get(ctype, ""))}'
        f'&pal0={_urlq(palette)}'
        + (f'&source={_urlq(footnote)}' if footnote else "")
        + f'&d0={_urlq(table_to_tsv(table))}')
    canvas_body = (
        f'<div class="cb-canvas"><div id="chartOut">{chart_svg}</div>'
        + chart_export_toolbar("chartOut", "chart-" + ctype)
        # The shaped table travels, not the raw paste — what you see is
        # what lands on the slide.
        + '<div class="cb-canvas-actions">'
        + ck_arrow_link("Send to Exhibit Composer (as panel 1)",
                        exhibit_href)
        # The shaped table (group/sort/top-N/calc applied) copies
        # back out as a paste-ready TSV — the Excel round-trip OUT.
        + f'<textarea id="shapedTsv" class="cb-hidden">'
        f'{html.escape(table_to_tsv(table))}</textarea>'
        '<button type="button" class="cb-btn-ghost" onclick="var b=this;'
        'navigator.clipboard.writeText(document.getElementById('
        "'shapedTsv').value).then(function(){var t=b.textContent;"
        'b.textContent=&quot;✓ Copied&quot;;setTimeout(function()'
        '{b.textContent=t;},1200);});">⧉ Copy shaped table'
        '</button>'
        + _save_chart_form("/chart-builder")
        + '</div></div>')

    notes_items = "".join(
        f'<div class="cb-note"><dt>{html.escape(term)}</dt>'
        f'<dd>{html.escape(desc)}</dd></div>'
        for term, desc in _FORMAT_NOTES)
    notes = (
        '<details class="cb-notes">'
        '<summary>Notes · how each chart reads your table</summary>'
        f'<dl class="cb-notes-grid">{notes_items}</dl>'
        '</details>')

    body = (
        ck_editorial_head(
            "RESEARCH · CDD CHART KIT",
            "Chart Builder",
            meta=f"{ck_fmt_number(len(CHART_TYPES))} CHART TYPES · "
                 f"{ck_fmt_number(len(PALETTES))} PALETTES · SHAREABLE URL",
            lede_italic_phrase="Every chart a CDD deck needs,",
            lede_body="rendered from a pasted table — pick a type, shape "
                      "the data, set the palette, and export or send "
                      "straight to the Exhibit Composer.",
            show_legend=False,
        )
        + ck_source_purpose(
            purpose="Build the charts a CDD deck needs from a pasted "
                    "table — pick a type, set colours, done.",
            universe="user-supplied",
            source="Your pasted data. Example tables are placeholders — "
                   "overwrite with your own.",
        )
        + '<div class="cb-wrap">'
        + ck_panel(form, title="Compose the chart",
                   code="GET /chart-builder")
        + datasets_strip
        + ck_panel(canvas_body, title="Rendered chart", code=ctype)
        + ck_section_header(
            "Your data in every chart.", eyebrow="GALLERY")
        + '<p class="cb-section-lede">The same table rendered across the '
          "deck family — click a card to switch the builder to that "
          "type.</p>"
        + f'<div class="cb-gallery">{gallery}</div>'
        + notes
        + ck_page_actions()
        + '</div>')
    return chartis_shell(
        body, "Chart Builder", active_nav="/research",
        subtitle="CDD chart kit", extra_css=_PAGE_CSS)


def _urlq(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(s)
