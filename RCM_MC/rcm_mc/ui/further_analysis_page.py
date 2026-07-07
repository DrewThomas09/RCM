"""Further Analysis — the Tableau-style surface over every vendored public
dataset.

Pick a dataset (CMS / CDC / Census / Labor / Markets / derived), a focus, the
measures and a chart type, and the page renders a clean, client-ready chart
you can export to PNG/SVG. Everything is query-string driven, so a configured
view is a shareable URL, and a gallery strip re-renders the same query across
chart types so a partner can pick the right exhibit.

The data engine is ``rcm_mc.diligence.further_analysis``; this module is the
form + layout + chart wiring. No data logic lives here. Rendering follows the
v5 chartis editorial idiom (see ``rcm_mc/ui/README.md``) — the sibling page
``chart_builder_page.py`` established the form/chip/gallery treatment reused
here.
"""
from __future__ import annotations

import html
import urllib.parse
from typing import Any

from ..diligence import further_analysis as fa
from ._chartis_kit import (
    chartis_shell,
    ck_copy_share_link_button,
    ck_data_cell,
    ck_data_table,
    ck_editorial_head,
    ck_empty_state,
    ck_fmt_number,
    ck_page_actions,
    ck_panel,
    ck_provenance_tooltip,
    ck_section_header,
    ck_source_purpose,
)
from .cdd_chart_kit import (
    CHART_TYPES,
    PALETTES,
    SIZE_PRESETS,
    chart_export_toolbar,
    render_cdd_chart,
)

# Page-scoped stylesheet (injected via chartis_shell extra_css). Every rule
# builds on the kit tokens with their canonical fallbacks — no ad-hoc hexes —
# and every interactive control carries :hover + :focus-visible states the
# old inline style attributes could not express.
_PAGE_CSS = """
.fa-wrap{max-width:1080px;}
.fa-kicker{display:flex;align-items:center;gap:8px;font-family:var(--sc-mono,monospace);font-size:10.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--sc-text-dim,#465366);margin:14px 0 3px;}
.fa-kicker::before{content:"";flex:0 0 18px;height:1px;background:var(--green-deep,#154e36);}
.fa-sub{font-family:var(--sc-sans,sans-serif);font-size:11px;color:var(--sc-text-faint,#7a8699);margin:0 0 6px;}
.fa-row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-bottom:10px;}
.fa-field{display:block;font-family:var(--sc-mono,monospace);font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--sc-text-dim,#465366);}
.fa-select,.fa-input{box-sizing:border-box;width:100%;margin-top:4px;height:30px;border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:#fff;color:var(--ink,#16263a);font-family:var(--sc-sans,sans-serif);font-size:12px;}
.fa-select{padding:0 4px;}
.fa-input{padding:0 8px;}
.fa-input-serif{font-family:var(--sc-serif,'Source Serif 4',Georgia,serif);}
.fa-flex1{flex:1;min-width:130px;}
.fa-flex2{flex:2;min-width:240px;}
.fa-minw150{min-width:150px;}
.fa-minw220{flex:1;min-width:220px;}
.fa-w78{width:78px;}
.fa-w90{width:90px;}
.fa-w130{width:130px;}
.fa-chips{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0 6px;}
.fa-chip{display:inline-flex;align-items:center;gap:5px;padding:4px 9px;border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:#fff;color:var(--sc-text-dim,#465366);font-family:var(--sc-mono,monospace);font-size:10px;letter-spacing:.04em;text-transform:uppercase;cursor:pointer;}
.fa-chip:hover{border-color:var(--sc-teal,#155752);color:var(--sc-teal,#155752);}
.fa-chip.is-on{background:var(--sc-navy,#0b2341);border-color:var(--sc-navy,#0b2341);color:var(--sc-on-navy,#e9eef5);}
.fa-chip-tag{font-size:7.5px;letter-spacing:.08em;padding:1px 3px;border:1px solid currentColor;border-radius:2px;opacity:.72;}
.fa-pills{display:flex;flex-wrap:wrap;gap:7px;margin:4px 0 6px;}
.fa-pill{display:inline-flex;align-items:center;gap:6px;padding:4px 11px;border:1px solid var(--sc-rule,#d6cfc0);border-radius:14px;background:#fff;font-family:var(--sc-sans,sans-serif);font-size:11.5px;color:var(--ink,#16263a);cursor:pointer;}
.fa-pill:hover{border-color:var(--sc-teal,#155752);}
.fa-pill.is-on{border-color:var(--sc-navy,#0b2341);background:var(--sc-bone,#ece5d6);}
.fa-pill input{margin:0;accent-color:var(--sc-teal,#155752);}
.fa-pill-unit{font-family:var(--sc-mono,monospace);font-size:10px;letter-spacing:.05em;text-transform:uppercase;color:var(--sc-text-faint,#7a8699);}
.fa-check{display:flex;align-items:center;gap:5px;font-family:var(--sc-sans,sans-serif);font-size:11.5px;color:var(--sc-text-dim,#465366);}
.fa-actions{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-top:8px;}
.fa-btn{margin-left:auto;padding:9px 20px;border:1px solid var(--sc-navy,#0b2341);border-radius:2px;background:var(--sc-navy,#0b2341);color:var(--sc-on-navy,#e9eef5);font-family:var(--sc-sans,sans-serif);font-size:12px;font-weight:600;letter-spacing:.04em;cursor:pointer;}
.fa-btn:hover{background:var(--sc-navy-2,#132e53);border-color:var(--sc-navy-2,#132e53);}
.fa-reset{font-family:var(--sc-mono,monospace);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--sc-teal,#155752);text-decoration:none;}
.fa-reset:hover{color:var(--sc-navy,#0b2341);text-decoration:underline;}
.fa-sr-submit{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);border:0;}
.fa-canvas{text-align:center;}
.fa-gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px;}
.fa-gallery-card{display:block;padding:6px;border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;background:var(--paper-card,#fefcf3);text-decoration:none;}
.fa-gallery-card:hover{border-color:var(--sc-teal,#155752);}
.fa-gallery-card.is-current{border-color:var(--green-deep,#154e36);box-shadow:inset 0 0 0 1px var(--green-deep,#154e36);}
.fa-gallery-cap{display:block;margin-top:4px;text-align:center;font-family:var(--sc-mono,monospace);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--sc-text-faint,#7a8699);}
.fa-gallery-card.is-current .fa-gallery-cap{color:var(--green-deep,#154e36);font-weight:600;}
.fa-gallery-card.is-current .fa-gallery-cap::after{content:" ✓";}
.fa-provline{margin:-4px 0 12px;font-family:var(--sc-mono,monospace);font-size:10.5px;letter-spacing:.04em;color:var(--sc-text-dim,#465366);}
.fa-tablewrap .ck-data-table-scroll{max-height:520px;overflow:auto;margin-top:0;}
.fa-tablewrap .ck-data-table thead th{position:sticky;top:0;z-index:1;background:var(--sc-bone,#ece5d6);}
.fa-tablewrap .ck-data-table tbody tr:hover{background:var(--paper-hi,#fbf6e8);}
.fa-empty-note{font-family:var(--sc-mono,monospace);font-size:10.5px;letter-spacing:.04em;color:var(--sc-text-faint,#7a8699);}
.fa-foot{font-family:var(--sc-sans,sans-serif);font-size:11.5px;color:var(--sc-text-dim,#465366);margin-top:14px;line-height:1.6;max-width:74ch;}
.fa-foot a{font-family:var(--sc-mono,monospace);font-size:10.5px;color:var(--sc-teal,#155752);}
.fa-foot a:hover{color:var(--sc-navy,#0b2341);}
.fa-chip:focus-visible,.fa-btn:focus-visible,.fa-reset:focus-visible,.fa-select:focus-visible,.fa-input:focus-visible,.fa-pill input:focus-visible,.fa-check input:focus-visible,.fa-gallery-card:focus-visible{outline:2px solid var(--sc-teal,#155752);outline-offset:1px;}
"""


def _qs1(qs: dict[str, Any] | None, key: str, default: str = "") -> str:
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


def _share_url(spec: dict[str, Any], view: dict[str, Any] | None = None,
               **overrides: Any) -> str:
    """Build a /further-analysis URL reproducing the current view, with
    optional param overrides (used by the chart-type gallery + chips).

    ``view`` carries the page-local presentation state (palette, size,
    toggles, custom titles) so a gallery click no longer discards the
    partner's hand-configured styling — the page's whole premise is that
    a configured view is a shareable URL.
    """
    ds = spec["dataset"]
    params: dict[str, Any] = {
        "dataset": ds.id,
        "measures": ",".join(spec["measures"]),
        "type": spec["chart_type"],
        "sort": spec["sort_key"],
        "asc": "1" if spec["ascending"] else "0",
        "top": str(spec["top_n"]),
    }
    if spec["focus"]:
        params["focus"] = spec["focus"]
    if view:
        params["palette"] = view["palette"]
        params["size"] = view["size"]
        # Toggles serialize only when non-default (default is on).
        if not view["values"]:
            params["values"] = "0"
        if not view["legend"]:
            params["legend"] = "0"
        # Custom copy travels only when it differs from the auto text.
        for key in ("title", "subtitle", "footnote"):
            if view.get(key):
                params[key] = view[key]
    params.update({k: str(v) for k, v in overrides.items()})
    return "/further-analysis?" + urllib.parse.urlencode(params)


# ── House numeric contract for the data table ────────────────────────
# Values arrive already scaled into display units by the engine's
# ``_scale`` (pct → 0-100, usd_m → millions, …). The measure ``fmt``
# picks the treatment: dollars 2dp with $, percentages 1dp with %,
# multiples 2dp + "x", integer counts with no decimals.

_UNIT_TAG = {"pct": "%", "pct100": "%", "usd": "$", "usd_m": "$M",
             "usd_b": "$B", "x": "x", "weeks": "wk"}


def _fmt_cell(v: float | None, fmt: str, int_like: bool) -> str | None:
    if v is None:
        return None
    if fmt in ("pct", "pct100"):
        return f"{ck_fmt_number(v, precision=1)}%"
    if fmt in ("usd", "usd_m", "usd_b"):
        sign = "-" if v < 0 else ""
        suffix = {"usd": "", "usd_m": "M", "usd_b": "B"}[fmt]
        return f"{sign}${ck_fmt_number(abs(v), precision=2)}{suffix}"
    if fmt == "x":
        return f"{ck_fmt_number(v, precision=2)}x"
    if fmt == "weeks":
        return f"{ck_fmt_number(v, precision=1)}w"
    # Generic numbers: integer counts get no decimals; genuinely
    # decimal measures (star ratings, rates) keep 2dp.
    return ck_fmt_number(v, precision=0 if int_like else 2)


def _drop_nan(table: dict[str, Any]) -> dict[str, Any]:
    """Map NaN cells to None before the table reaches the chart kit.

    A loader can hand back ``float("nan")`` (e.g. cdc_places), which
    passes the engine's not-None row filter and then crashes the chart
    kit's value formatter (``int(nan)``) — the /further-analysis route
    500'd for that dataset. None is the missing-value contract every
    chart type and this page's own table already honour ("—" cells),
    so normalising here fixes the crash without touching the shared
    engine or chart kit.
    """
    rows = [
        (lbl, [None if isinstance(v, float) and v != v else v
               for v in vals])
        for lbl, vals in table["rows"]
    ]
    return {"headers": table["headers"], "rows": rows}


def render_further_analysis_page(qs: dict[str, Any] | None = None) -> str:
    spec = fa.resolve_query(qs)
    dataset = spec["dataset"]
    table = _drop_nan(spec["table"])
    meta = spec["meta"]
    has_rows = bool(table["rows"])

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
    auto_foot = f"Source: {dataset.source}"
    footnote = _qs1(qs, "footnote", "") or auto_foot

    # The page-local presentation state a share link must reproduce.
    view = {
        "palette": palette, "size": size,
        "values": show_values, "legend": legend,
        "title": "" if title == auto_title else title,
        "subtitle": "" if subtitle == auto_sub else subtitle,
        "footnote": "" if footnote == auto_foot else footnote,
    }

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
            f'<label class="fa-field fa-flex1">'
            f'{html.escape(dataset.focus_label or "Focus")}'
            f'<select name="focus" class="fa-select">{f_opts}</select>'
            f'</label>')

    # Measure checkboxes.
    sel_measures = set(spec["measures"])
    meas_boxes = ""
    for m in dataset.measures:
        on = m.key in sel_measures
        meas_boxes += (
            f'<label class="fa-pill{" is-on" if on else ""}">'
            f'<input type="checkbox" name="measures" value="{m.key}"'
            f'{" checked" if on else ""}>'
            f'{html.escape(m.label)}'
            f'<span class="fa-pill-unit">'
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

    # Chart-type chips (submit on click so server re-shapes). Each chip
    # is a submit button named ``type``; the current type's hidden input
    # serializes AFTER the chips (see the form below) so a clicked
    # chip's value lands first in the query string and wins the engine's
    # first-occurrence resolution.
    single = fa._SINGLE_SERIES_TYPES
    chips = ""
    for key, label in CHART_TYPES:
        is_sel = key == chart_type
        tag = ('<span class="fa-chip-tag" aria-hidden="true">1-SERIES</span>'
               if key in single else "")
        chips += (
            f'<button type="submit" name="type" value="{key}" '
            f'class="fa-chip{" is-on" if is_sel else ""}" '
            f'aria-pressed="{"true" if is_sel else "false"}" '
            f'title="{html.escape(label)}'
            f'{" (single series)" if key in single else ""}">'
            f'{html.escape(label)}{tag}</button>')

    def _toggle(name, label, on):
        # Checkbox + hidden "0" sentinel AFTER it: checked submits
        # ["1","0"] (first occurrence wins → on), unchecked submits
        # ["0"] → off. Without the sentinel an unchecked box submits
        # nothing and the default-True fallback made these toggles
        # impossible to turn off. Links without the param (gallery,
        # shared URLs) keep the friendly default.
        return (
            f'<label class="fa-check"><input type="checkbox" '
            f'name="{name}" value="1"{" checked" if on else ""}>{label}'
            f'</label>'
            f'<input type="hidden" name="{name}" value="0">')

    size_opts = "".join(
        f'<option value="{k}"{" selected" if k == size else ""}>'
        f'{k} · {w}px</option>'
        for k, w in SIZE_PRESETS)

    asc_opts = (
        f'<option value="0"{"" if spec["ascending"] else " selected"}>'
        f'High → low</option>'
        f'<option value="1"{" selected" if spec["ascending"] else ""}>'
        f'Low → high</option>')

    form = (
        f'<form method="get" action="/further-analysis">'
        # Visually-hidden, name-less default submit. Enter-key implicit
        # submission activates the FIRST submit control in tree order;
        # without this guard it would "click" the first chart-type chip
        # and silently reset the chart type to bar.
        f'<button type="submit" class="fa-sr-submit" tabindex="-1" '
        f'aria-hidden="true"></button>'
        # Row 1: dataset + focus
        f'<div class="fa-row">'
        f'<label class="fa-field fa-flex2">Dataset'
        f'<select name="dataset" onchange="this.form.submit()" '
        f'class="fa-select">{ds_opts}</select></label>'
        f'{focus_html}'
        f'</div>'
        # Row 2: chart-type chips, then the current type as a hidden
        # fallback (order is load-bearing — see the chips comment).
        f'<div class="fa-kicker">Chart type</div>'
        f'<div class="fa-chips" role="group" aria-label="Chart type">'
        f'{chips}</div>'
        f'<input type="hidden" name="type" value="{chart_type}">'
        # Row 3: measures
        f'<div class="fa-kicker">Measures</div>'
        f'<div class="fa-sub">Pick one or more — single-series charts '
        f'use the first.</div>'
        f'<div class="fa-pills">{meas_boxes}</div>'
        # Row 4: sort / top / palette / size
        f'<div class="fa-row">'
        f'<label class="fa-field fa-flex1 fa-minw150">Sort by'
        f'<select name="sort" class="fa-select">{sort_opts}</select></label>'
        f'<label class="fa-field fa-w130">Order'
        f'<select name="asc" class="fa-select">{asc_opts}</select></label>'
        f'<label class="fa-field fa-w90">Top N'
        f'<input type="number" name="top" min="1" max="60" '
        f'value="{spec["top_n"]}" class="fa-input"></label>'
        f'<label class="fa-field fa-flex1">Palette'
        f'<select name="palette" class="fa-select">{pal_opts}</select>'
        f'</label>'
        f'<label class="fa-field fa-w78">Size'
        f'<select name="size" class="fa-select">{size_opts}</select></label>'
        f'</div>'
        # Row 5: titles
        f'<div class="fa-row">'
        f'<label class="fa-field fa-minw220">Title'
        f'<input type="text" name="title" '
        f'value="{html.escape("" if title == auto_title else title)}" '
        f'placeholder="{html.escape(auto_title)}" '
        f'class="fa-input fa-input-serif"></label>'
        f'<label class="fa-field fa-minw220">Subtitle'
        f'<input type="text" name="subtitle" '
        f'value="{html.escape("" if subtitle == auto_sub else subtitle)}" '
        f'placeholder="{html.escape(auto_sub)}" class="fa-input"></label>'
        f'</div>'
        f'<div class="fa-actions">'
        f'{_toggle("values", "Show values", show_values)}'
        f'{_toggle("legend", "Legend", legend)}'
        f'<button type="submit" class="fa-btn">Render</button>'
        f'<a href="/further-analysis?dataset={dataset.id}" class="fa-reset">'
        f'Reset</a>'
        f'</div>'
        f'</form>')

    # ---- Chart panel / empty state --------------------------------------
    if has_rows:
        chart_block = ck_panel(
            f'<div class="fa-canvas"><div id="faOut">{chart_svg}</div>'
            + chart_export_toolbar("faOut", "further-analysis-" + dataset.id)
            + '</div>',
            title="Rendered exhibit", code=chart_type)
    else:
        # A dataset loader can return zero rows offline — never hand the
        # chart kit an empty table (its fallback copy belongs to the
        # paste tool, not this page).
        chart_block = ck_empty_state(
            "No rows for this slice",
            body=(f"The {dataset.label} loader returned no rows for this "
                  "dataset / focus combination — its source extract may "
                  "be unavailable offline. Reset to the default view or "
                  "pick another dataset above."),
            eyebrow="DATA EXPLORER",
            icon="◌",
            cta_label="Reset to default view",
            cta_href=f"/further-analysis?dataset={dataset.id}",
            tone="neutral")

    # ---- Chart-type gallery (same query, other chart types) -------------
    gallery_sec = ""
    if has_rows:
        gtypes = ["bar", "column", "column_stacked", "line", "area", "dot",
                  "pie", "donut", "marimekko", "radar", "heatmap", "scatter"]
        gallery = ""
        for gt in gtypes:
            glabel = dict(CHART_TYPES).get(gt, gt)
            gsvg = render_cdd_chart(
                gt, table, {"title": glabel,
                            "palette": palette, "W": 330, "H": 210,
                            "px_h": 180, "legend": False,
                            "show_values": False,
                            "suffix": meta["suffix"]})
            href = _share_url(spec, view, type=gt)
            cur = " is-current" if gt == chart_type else ""
            gallery += (
                f'<a href="{html.escape(href, quote=True)}" '
                f'class="fa-gallery-card{cur}" '
                f'aria-label="Switch to {html.escape(glabel, quote=True)}">'
                f'{gsvg}'
                f'<span class="fa-gallery-cap">{html.escape(glabel)}</span>'
                f'</a>')
        gallery_sec = (
            ck_section_header("Same query, other chart types",
                              eyebrow="GALLERY", count=len(gtypes))
            + f'<div class="fa-gallery">{gallery}</div>')

    # ---- Data table (the exact rows behind the chart) -------------------
    # Formats follow the house numeric contract per measure fmt; integer
    # count columns drop their decimals, units land in the header.
    fmts = [m["fmt"] for m in meta["measures"]]
    col_int_like: list[bool] = []
    for ci in range(len(fmts)):
        col_vals = [vals[ci] for _, vals in table["rows"]
                    if vals[ci] is not None]
        col_int_like.append(
            bool(col_vals) and all(float(v).is_integer() for v in col_vals))
    headers = [{"label": table["headers"][0], "align": "left"}]
    for m in meta["measures"]:
        unit = _UNIT_TAG.get(m["fmt"], "")
        headers.append({
            "label": f'{m["label"]} ({unit})' if unit else m["label"],
            "align": "right"})
    rows_html = ""
    for lbl, vals in table["rows"]:
        cells = ck_data_cell(html.escape(lbl))
        for v, fmt, int_like in zip(vals, fmts, col_int_like, strict=False):
            disp = _fmt_cell(v, fmt, int_like)
            if disp is None:
                cells += ck_data_cell("—", align="right", mono=True,
                                      tone="dim")
            else:
                cells += ck_data_cell(disp, align="right", mono=True)
        rows_html += f"<tr>{cells}</tr>"

    if spec["sort_key"] == "_label":
        sort_lab = f"{dataset.dim_label} (name)"
    else:
        sort_m = dataset.measure(spec["sort_key"])
        sort_lab = sort_m.label if sort_m else dataset.measures[0].label
    table_sec = (
        ck_section_header("The rows behind the chart",
                          eyebrow="DATA BEHIND THE CHART",
                          count=len(table["rows"]))
        + '<div class="fa-provline">'
        + ck_provenance_tooltip(
            "Query provenance",
            html.escape(f"top {spec['top_n']} · sorted by {sort_lab}"),
            explainer=(
                f"The exact rows plotted above: {dataset.label}, sorted by "
                f"{sort_lab} "
                f"({'ascending' if spec['ascending'] else 'descending'}), "
                f"top {spec['top_n']} kept. Source: {dataset.source}"))
        + '</div>')
    if has_rows:
        table_sec += ('<div class="fa-tablewrap">'
                      + ck_data_table(headers=headers, rows_html=rows_html)
                      + '</div>')
    else:
        table_sec += ('<p class="fa-empty-note">0 rows — adjust the query '
                      'above, or reset to the default view.</p>')

    foot = (
        f'<p class="fa-foot"><strong>{html.escape(dataset.label)}</strong> — '
        f'{html.escape(dataset.note)} Grain: {html.escape(dataset.grain)}. '
        f'JSON: <a href="/api/further-analysis">/api/further-analysis</a> '
        f'(every dataset + measure, machine readable).</p>')

    body = (
        ck_editorial_head(
            "RESEARCH · DATA EXPLORER",
            "Further Analysis",
            meta=(f"{len(fa.list_datasets())} DATASETS · "
                  f"{len(CHART_TYPES)} CHART TYPES · "
                  f"TOP {spec['top_n']} ROWS · SHAREABLE URL"),
            lede_italic_phrase="Slice every vendored public dataset",
            lede_body=(
                "into a client-ready exhibit — pick the measures, sort and "
                "chart type; the configured view is a <em>shareable URL</em> "
                "and the chart exports to SVG or PNG for the deck."),
            actions_html=ck_copy_share_link_button(),
            show_legend=False,
        )
        + ck_source_purpose(
            purpose="Build any chart from the platform's real public data — "
                    "pick a dataset, measures and a chart type, export the "
                    "PNG. Thousands of slices, all from vendored sources.",
            universe="mixed",
            source="All series are real vendored public data (CMS / CDC / "
                   "Census / BLS-based / market comps). No synthetic data.",
        )
        + '<div class="fa-wrap">'
        + ck_panel(form, title="Compose the query",
                   code="GET /further-analysis")
        + chart_block
        + gallery_sec
        + table_sec
        + foot
        + ck_page_actions(share=False)
        + '</div>')
    return chartis_shell(
        body, "Further Analysis", active_nav="/research",
        subtitle="Data explorer", extra_css=_PAGE_CSS)
