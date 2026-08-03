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
from ._chartis_kit import (
    chartis_shell, ck_empty_state, ck_page_title, ck_source_link,
    ck_source_purpose,
)
from .saved_charts_page import save_chart_form as _save_chart_form
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


def _and_list(nums: List[int]) -> str:
    """Panel numbers as prose — 1 / 1 and 3 / 1, 3 and 4.

    Empty-state copy names the panels that failed to parse, and a bare
    comma list ("1, 3") reads as a range in a sentence.
    """
    parts = [str(n) for n in nums]
    if len(parts) < 2:
        return parts[0] if parts else ""
    return ", ".join(parts[:-1]) + " and " + parts[-1]


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
    source_qs = _qs1(qs, "source", "")

    panels = []
    forms = []
    ds_sources: List[str] = []   # provenance of platform-loaded panels
    unparsed: List[int] = []     # 1-based panels with data but no rows
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
        ds_note = ""
        if ds and not ddata.strip():
            # Platform data fills an empty panel; pasted/edited data
            # always wins so a loaded table stays editable afterwards.
            d = build_chart_dataset(ds)
            ddata = d["tsv"]
            ptitle = ptitle or d["label"]
            # The dataset's own source line used to be dropped on the
            # floor here, so a slide carrying real CMS aggregates still
            # read "Source: illustrative" — the worst provenance failure
            # a partner-facing exhibit can ship. Carry it instead.
            ds_note = str(d.get("footnote") or "")
            if ds_note and ds_note not in ds_sources:
                ds_sources.append(ds_note)
            if not _qs1(qs, f"t{i}"):
                dt = d["chart"]
        if dt not in dict(CHART_TYPES):
            dt = "column"
        pal = _qs1(qs, f"pal{i}", "Chartis")
        if pal not in PALETTES:
            pal = "Chartis"
        table = parse_table(ddata) if ddata.strip() else None
        if table is not None and table.get("rows"):
            panels.append({"type": dt, "title": ptitle,
                           "table": table, "palette": pal})
        elif table is not None:
            # Data pasted, but nothing parsed — compose_exhibit silently
            # drops the panel, so say so next to the box it came from.
            unparsed.append(i + 1)
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
            # Percent-encoded first (quote() covers " & < >), then escaped
            # for the attribute context — never hand-rolled either way.
            href = (f'/chart-builder?type={dt}&title={_urlq(ptitle)}'
                    f'&data={_urlq(ddata)}')
            edit_link = (
                f'<a href="{html.escape(href, quote=True)}" '
                f'aria-label="Edit panel {i+1} in Chart Builder" '
                f'title="Open this panel’s table in the Chart Builder" '
                f'style="font-size:10.5px;color:#1F7A75;">'
                f'<span aria-hidden="true">✎</span> '
                f'edit in Chart Builder</a>')
        # Either the panel's platform-data provenance (clickable through to
        # the publishing dataset) or a plain reason the panel is missing.
        if i + 1 in unparsed:
            note = ('<div role="note" style="margin-top:5px;font-size:10.5px;'
                    'line-height:1.35;color:#b5321e;">Not on the slide — no '
                    'parseable rows. Expect a header row plus one row per '
                    'category, tab- or comma-separated.</div>')
        elif ds_note:
            note = ('<div style="margin-top:5px;font-size:10.5px;'
                    'line-height:1.35;color:#7a8699;">'
                    + ck_source_link(ds_note, style="color:#155752;")
                    + '</div>')
        else:
            note = ""
        forms.append(
            f'<div style="border:1px solid #d6cfc0;border-radius:6px;'
            f'padding:11px 13px;background:#fbf9f4;">'
            f'<div style="font-size:10px;letter-spacing:0.06em;'
            f'color:#7a8699;font-weight:700;margin-bottom:5px;display:flex;'
            f'justify-content:space-between;align-items:center;">'
            f'<span>PANEL {i+1}</span>{edit_link}</div>'
            f'<div style="display:flex;gap:8px;margin-bottom:6px;">'
            f'<select name="t{i}" aria-label="Panel {i+1} chart type" '
            f'style="flex:1;height:28px;border:1px '
            f'solid #c9c1ac;border-radius:4px;">{type_opts}</select>'
            f'<select name="pal{i}" aria-label="Panel {i+1} palette" '
            f'style="width:96px;height:28px;'
            f'border:1px solid #c9c1ac;border-radius:4px;">{pal_opts}'
            f'</select></div>'
            f'<input type="text" name="pt{i}" '
            f'aria-label="Panel {i+1} title" '
            f'title="{html.escape(ptitle, quote=True) or "Panel title"}" '
            f'value="{html.escape(ptitle)}" '
            f'placeholder="Panel title" style="width:100%;height:28px;'
            f'border:1px solid #c9c1ac;border-radius:4px;padding:0 7px;'
            f'margin-bottom:6px;font-family:{_SERIF};">'
            f'<textarea name="d{i}" rows="4" aria-label="Panel {i+1} data" '
            f'placeholder="Paste data — or '
            f'leave blank to drop this panel" style="width:100%;'
            f'font-family:ui-monospace,Menlo,monospace;font-size:11.5px;'
            f'border:1px solid #c9c1ac;border-radius:4px;padding:6px;">'
            f'{html.escape(ddata)}</textarea>'
            f'<select name="ds{i}" aria-label="Panel {i+1} dataset" '
            f'style="width:100%;height:26px;'
            f'margin-top:5px;border:1px solid #9bc1bc;border-radius:4px;'
            f'font-size:11px;color:#155752;">{ds_opts}</select>'
            f'{note}</div>')

    # An explicit ?source= always wins (the partner typed it); otherwise a
    # platform-loaded panel's own citation beats the "illustrative"
    # placeholder, so the exported slide never mislabels real CMS data.
    source = source_qs or (ds_sources[0] if ds_sources else
                           "Source: illustrative")

    svg = compose_exhibit(
        panels, title=slide_title, eyebrow=eyebrow, source=source)

    # Source line for the HTML page (the SVG keeps flat text so the export
    # stays self-contained): every label routed through ck_source_link, so
    # a cited dataset is one click from its publishing origin.
    src_labels: List[str] = []
    for lab in [source] + ds_sources:
        lab = lab.strip()
        if lab and lab not in src_labels:
            src_labels.append(lab)
    src_html = '<span> · </span>'.join(
        ck_source_link(lab, style="color:#155752;") for lab in src_labels
    ) or '<span>Not stated — add one in the Source box above.</span>'
    caption = (
        '<figcaption style="display:flex;gap:10px;flex-wrap:wrap;'
        'align-items:baseline;justify-content:center;margin-top:8px;'
        'font-size:10.5px;color:#7a8699;text-align:left;">'
        '<span style="letter-spacing:0.06em;font-weight:700;">SOURCE</span>'
        + src_html
        + f'<span style="font-variant-numeric:tabular-nums;">'
          f'{len(panels)} of {_N_PANELS} panels on the slide</span>'
        '</figcaption>')

    if not panels:
        if unparsed:
            nums = _and_list(unparsed)
            lead = (f"Panel {nums} has data" if len(unparsed) == 1
                    else f"Panels {nums} have data")
            why = (f"{lead} but no parseable rows — expect a header row "
                   "plus one row per category, tab- or comma-separated. ")
        else:
            why = ("Paste a table into a panel above, or pick a platform "
                   "dataset, and the composed 16:9 exhibit appears here. ")
        empty = ck_empty_state(
            "Nothing on the slide yet.",
            body=why + "The frame below is the title block only.",
            eyebrow="NO PANELS COMPOSED",
            cta_label="Build a chart first",
            cta_href="/chart-builder",
            icon="◧",
        )
    else:
        empty = ""

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
        + empty
        # <figure>/<figcaption> so the caption is programmatically tied to
        # the exhibit; the SVG inside carries role="img" + the slide title
        # as its accessible name.
        + '<figure style="margin:0;">'
        + f'<div id="exhibitOut">{svg}</div>'
        + caption
        + '</figure>'
        + chart_export_toolbar("exhibitOut", "exhibit")
        + _save_chart_form("/exhibit")
        + '</div></div>')
    return chartis_shell(
        body, "Exhibit Composer", active_nav="/research",
        subtitle="Multi-chart deck slide")
