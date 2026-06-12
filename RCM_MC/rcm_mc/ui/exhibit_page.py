"""Exhibit composer — lay up to 4 charts on one deck slide.

The capstone of the chart suite: configure 1–4 panels (each a chart type
+ a pasted table + a panel title), add a slide eyebrow / title / source,
and it composes a single 16:9 client-ready exhibit you can export as one
SVG / PNG. Each panel is ``t{i}`` type, ``pt{i}`` title, ``d{i}`` data,
``pal{i}`` palette — so a whole slide is a shareable URL.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..data.chart_datasets import build_chart_dataset, list_chart_datasets
from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
from .cdd_chart_kit import (
    CHART_TYPES, PALETTES, parse_table, compose_exhibit,
    chart_export_toolbar,
)

_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")
_N_PANELS = 4

_DEFAULTS = [
    ("column", "Revenue & EBITDA",
     "Year\tRevenue\tEBITDA\n2021\t100\t22\n2022\t130\t31\n2023\t165\t43"),
    ("donut", "Site-of-care mix",
     "Segment\tShare\nAIC\t38\nHome\t30\nHOPD\t22\nOffice\t10"),
    ("waterfall", "EBITDA bridge",
     "Step\tValue\nEntry\t100\nDenials\t18\nMix\t12\nExit\t=130"),
    ("bar", "Operator share",
     "Operator\tShare\nOption Care\t20\nIVX\t9\nOptum\t14\nIndependent\t57"),
]


def _urlq(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(s)


def _qs1(qs: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not qs:
        return default
    v = qs.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return str(v) if v not in (None, "") else default


def render_exhibit_page(qs: "Dict[str, Any] | None" = None) -> str:
    # A dataset pick alone (ds{i}, no pasted d{i}) must also leave
    # example-default mode — otherwise the defaults pre-fill every
    # panel and the dataset load is silently skipped.
    has_qs = bool(qs) and any(
        _qs1(qs, f"d{i}") or _qs1(qs, f"ds{i}") for i in range(_N_PANELS))
    ds_keys = {m["key"] for m in list_chart_datasets()}
    slide_title = _qs1(qs, "title", "Investment Highlights")
    eyebrow = _qs1(qs, "eyebrow", "Commercial Due Diligence")
    source = _qs1(qs, "source", "Source: illustrative")

    panels = []
    forms = []
    for i in range(_N_PANELS):
        ds = _qs1(qs, f"ds{i}", "")
        if ds not in ds_keys:
            ds = ""
        if not has_qs and i < len(_DEFAULTS):
            dt, ptitle, ddata = _DEFAULTS[i]
        else:
            dt = _qs1(qs, f"t{i}", "column")
            ptitle = _qs1(qs, f"pt{i}", "")
            ddata = _qs1(qs, f"d{i}", "")
        if ds and not ddata.strip():
            # Platform data fills an empty panel; pasted/edited data
            # always wins so a loaded table stays editable afterwards.
            d = build_chart_dataset(ds)
            ddata = d["tsv"]
            ptitle = ptitle or d["label"]
            if not _qs1(qs, f"t{i}"):
                dt = d["chart"]
        if dt not in dict(CHART_TYPES):
            dt = "column"
        pal = _qs1(qs, f"pal{i}", "Chartis")
        if pal not in PALETTES:
            pal = "Chartis"
        if ddata.strip():
            panels.append({"type": dt, "title": ptitle,
                           "table": parse_table(ddata), "palette": pal})
        # Panel config form.
        type_opts = "".join(
            f'<option value="{k}"{" selected" if k == dt else ""}>{lab}'
            f'</option>' for k, lab in CHART_TYPES)
        pal_opts = "".join(
            f'<option value="{p}"{" selected" if p == pal else ""}>{p}'
            f'</option>' for p in PALETTES)
        ds_opts = '<option value="">Platform data…</option>' + "".join(
            f'<option value="{m["key"]}"'
            f'{" selected" if m["key"] == ds else ""}>{html.escape(m["label"])}'
            f'</option>' for m in list_chart_datasets())
        edit_link = ""
        if ddata.strip():
            edit_link = (
                f'<a href="/chart-builder?type={dt}&title={_urlq(ptitle)}'
                f'&data={_urlq(ddata)}" style="font-size:10.5px;'
                f'color:#1F7A75;">✎ edit in Chart Builder</a>')
        forms.append(
            f'<div style="border:1px solid #d6cfc0;border-radius:6px;'
            f'padding:11px 13px;background:#fbf9f4;">'
            f'<div style="font-size:10px;letter-spacing:0.06em;'
            f'color:#7a8699;font-weight:700;margin-bottom:5px;display:flex;'
            f'justify-content:space-between;align-items:center;">'
            f'<span>PANEL {i+1}</span>{edit_link}</div>'
            f'<div style="display:flex;gap:8px;margin-bottom:6px;">'
            f'<select name="t{i}" style="flex:1;height:28px;border:1px '
            f'solid #c9c1ac;border-radius:4px;">{type_opts}</select>'
            f'<select name="pal{i}" style="width:96px;height:28px;'
            f'border:1px solid #c9c1ac;border-radius:4px;">{pal_opts}'
            f'</select></div>'
            f'<input type="text" name="pt{i}" value="{html.escape(ptitle)}" '
            f'placeholder="Panel title" style="width:100%;height:28px;'
            f'border:1px solid #c9c1ac;border-radius:4px;padding:0 7px;'
            f'margin-bottom:6px;font-family:{_SERIF};">'
            f'<textarea name="d{i}" rows="4" placeholder="Paste data — or '
            f'leave blank to drop this panel" style="width:100%;'
            f'font-family:ui-monospace,Menlo,monospace;font-size:11.5px;'
            f'border:1px solid #c9c1ac;border-radius:4px;padding:6px;">'
            f'{html.escape(ddata)}</textarea>'
            f'<select name="ds{i}" style="width:100%;height:26px;'
            f'margin-top:5px;border:1px solid #9bc1bc;border-radius:4px;'
            f'font-size:11px;color:#155752;">{ds_opts}</select></div>')

    svg = compose_exhibit(
        panels, title=slide_title, eyebrow=eyebrow, source=source)

    form = (
        f'<form method="get" action="/exhibit">'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1.2fr;'
        f'gap:10px;margin-bottom:12px;">'
        f'<label style="font-size:11px;color:#465366;">Eyebrow'
        f'<input type="text" name="eyebrow" value="{html.escape(eyebrow)}" '
        f'style="width:100%;height:30px;border:1px solid #c9c1ac;'
        f'border-radius:5px;padding:0 8px;"></label>'
        f'<label style="font-size:11px;color:#465366;">Source'
        f'<input type="text" name="source" value="{html.escape(source)}" '
        f'style="width:100%;height:30px;border:1px solid #c9c1ac;'
        f'border-radius:5px;padding:0 8px;"></label>'
        f'<label style="font-size:11px;color:#465366;">Slide title'
        f'<input type="text" name="title" value="{html.escape(slide_title)}" '
        f'style="width:100%;height:30px;border:1px solid #c9c1ac;'
        f'border-radius:5px;padding:0 8px;font-family:{_SERIF};"></label>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">'
        + "".join(forms) + '</div>'
        f'<button type="submit" style="margin-top:12px;padding:10px 20px;'
        f'background:#0b2341;color:#fff;border:none;border-radius:5px;'
        f'font-weight:600;cursor:pointer;">Compose exhibit</button>'
        f'<a href="/exhibit?reset=1" style="margin-left:10px;font-size:'
        f'11.5px;color:#1F7A75;">Reset</a></form>')

    body = (
        ck_page_title(
            "Exhibit Composer",
            eyebrow="UTILITY · MULTI-CHART DECK SLIDE",
            meta="Lay up to 4 charts on one 16:9 slide with a title block "
                 "+ source — export as a single SVG / PNG.",
        )
        + ck_source_purpose(
            purpose="Compose a client-ready exhibit slide from up to four "
                    "charts — pick each panel's type and paste its data.",
            universe="user-supplied",
            source="Your panel inputs. Defaults are example placeholders.",
        )
        + '<div class="ts-wrap" style="max-width:1040px;">'
        + form
        + '<div style="margin-top:18px;border:1px solid #d6cfc0;'
          'border-radius:8px;padding:14px;background:#fff;text-align:center;">'
        + f'<div id="exhibitOut">{svg}</div>'
        + chart_export_toolbar("exhibitOut", "exhibit")
        + '</div></div>')
    return chartis_shell(
        body, "Exhibit Composer", active_nav="/research",
        subtitle="Multi-chart deck slide")
