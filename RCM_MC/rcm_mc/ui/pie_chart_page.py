"""Pie Chart — type a label, a value, and a colour per slice, get a
clean, client-ready pie or donut. No table paste, no dynamic data: just
fill in the rows and render a presentable static chart for the deck.

Each slice is three fields — ``l{i}`` label, ``v{i}`` value, ``c{i}``
colour — so a configured chart is a shareable URL. Blank rows are
ignored. Rendering is ``cdd_chart_kit.presentable_pie``.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
from .cdd_chart_kit import presentable_pie, PALETTES

_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")
_ROWS = 10
_CHARTIS = PALETTES["Chartis"]

# A clear, client-ready default so the page opens populated.
_DEFAULTS: List[Dict[str, Any]] = [
    {"label": "Segment A", "value": "40", "color": _CHARTIS[0]},
    {"label": "Segment B", "value": "25", "color": _CHARTIS[1]},
    {"label": "Segment C", "value": "20", "color": _CHARTIS[2]},
    {"label": "Segment D", "value": "15", "color": _CHARTIS[3]},
]


def _qs1(qs: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not qs:
        return default
    v = qs.get(key)
    if isinstance(v, list):
        v = v[0] if v else None
    return str(v) if v not in (None, "") else default


def _qsbool(qs, key, default):
    v = _qs1(qs, key, "")
    if v == "":
        return default
    return v not in ("0", "false", "off", "no")


def _collect_slices(qs: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pull slice rows from the qs; fall back to the defaults the first
    time the page is opened (no slice params present)."""
    any_row = any(_qs1(qs, f"l{i}") or _qs1(qs, f"v{i}")
                  for i in range(_ROWS))
    rows: List[Dict[str, Any]] = []
    for i in range(_ROWS):
        if not any_row and i < len(_DEFAULTS):
            d = _DEFAULTS[i]
            rows.append({"label": d["label"], "value": d["value"],
                         "color": d["color"]})
            continue
        label = _qs1(qs, f"l{i}")
        val = _qs1(qs, f"v{i}")
        color = _qs1(qs, f"c{i}") or _CHARTIS[i % len(_CHARTIS)]
        rows.append({"label": label, "value": val, "color": color})
    return rows


def _to_float(s: str) -> Optional[float]:
    try:
        return float(str(s).replace("%", "").replace("$", "")
                     .replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def render_pie_chart_page(qs: "Dict[str, Any] | None" = None) -> str:
    rows = _collect_slices(qs)
    title = _qs1(qs, "title", "")
    subtitle = _qs1(qs, "subtitle", "")
    suffix = _qs1(qs, "suffix", "")
    donut = _qsbool(qs, "donut", False)
    label_mode = _qs1(qs, "mode", "percent")
    if label_mode not in ("percent", "value", "both", "none"):
        label_mode = "percent"

    slices = [{"label": r["label"], "value": _to_float(r["value"]),
               "color": r["color"]} for r in rows]
    svg = presentable_pie(slices, {
        "title": title or "Pie Chart", "subtitle": subtitle,
        "donut": donut, "label_mode": label_mode, "value_suffix": suffix,
    })

    # Slice input rows.
    row_html = ""
    for i, r in enumerate(rows):
        row_html += (
            f'<div style="display:grid;grid-template-columns:24px 1fr 92px '
            f'52px;gap:8px;align-items:center;margin-bottom:6px;">'
            f'<span style="font-size:11px;color:#7a8699;text-align:right;">'
            f'{i+1}</span>'
            f'<input type="text" name="l{i}" value="{html.escape(r["label"])}" '
            f'placeholder="Label" style="height:30px;border:1px solid '
            f'#c9c1ac;border-radius:5px;padding:0 8px;font-family:{_SERIF};">'
            f'<input type="text" name="v{i}" value="{html.escape(r["value"])}" '
            f'placeholder="Value" inputmode="decimal" style="height:30px;'
            f'border:1px solid #c9c1ac;border-radius:5px;padding:0 8px;'
            f'text-align:right;font-family:{_SERIF};">'
            f'<input type="color" name="c{i}" '
            f'value="{html.escape(r["color"])}" style="width:52px;height:30px;'
            f'border:1px solid #c9c1ac;border-radius:5px;padding:0;'
            f'background:#fff;cursor:pointer;">'
            f'</div>')

    def _toggle(name, label, on):
        return (f'<label style="font-size:12px;color:#465366;display:flex;'
                f'align-items:center;gap:5px;"><input type="checkbox" '
                f'name="{name}" value="1"{" checked" if on else ""}>{label}'
                f'</label>')
    mode_opts = "".join(
        f'<option value="{m}"{" selected" if m == label_mode else ""}>'
        f'{lab}</option>' for m, lab in
        (("percent", "Percent"), ("value", "Value"),
         ("both", "Value · %"), ("none", "None")))

    form = (
        f'<form method="get" action="/pie-chart">'
        f'<div style="display:grid;grid-template-columns:1fr 1.05fr;gap:24px;'
        f'align-items:start;">'
        # Left: slices
        f'<div><div style="font-size:10px;letter-spacing:0.06em;'
        f'color:#7a8699;font-weight:700;margin-bottom:6px;">SLICES — LABEL '
        f'· VALUE · COLOUR</div>'
        f'<div style="display:grid;grid-template-columns:24px 1fr 92px 52px;'
        f'gap:8px;font-size:10px;color:#7a8699;margin-bottom:3px;">'
        f'<span></span><span>Label</span>'
        f'<span style="text-align:right;">Value</span><span>Colour</span>'
        f'</div>{row_html}'
        f'<p style="font-size:11px;color:#7a8699;margin:6px 0 0;">'
        f'Leave a row blank to drop the slice. Values can be any units '
        f'(percent or absolute) — the chart computes shares.</p></div>'
        # Right: options + render
        f'<div style="display:flex;flex-direction:column;gap:10px;">'
        f'<label style="font-size:11px;color:#465366;">Title'
        f'<input type="text" name="title" value="{html.escape(title)}" '
        f'style="width:100%;height:32px;border:1px solid #c9c1ac;'
        f'border-radius:5px;padding:0 8px;font-family:{_SERIF};"></label>'
        f'<label style="font-size:11px;color:#465366;">Subtitle'
        f'<input type="text" name="subtitle" value="{html.escape(subtitle)}" '
        f'style="width:100%;height:32px;border:1px solid #c9c1ac;'
        f'border-radius:5px;padding:0 8px;"></label>'
        f'<div style="display:flex;gap:10px;">'
        f'<label style="font-size:11px;color:#465366;flex:1;">Slice labels'
        f'<select name="mode" style="width:100%;height:32px;border:1px '
        f'solid #c9c1ac;border-radius:5px;">{mode_opts}</select></label>'
        f'<label style="font-size:11px;color:#465366;width:90px;">Unit'
        f'<input type="text" name="suffix" value="{html.escape(suffix)}" '
        f'placeholder="% or $" style="width:100%;height:32px;border:1px '
        f'solid #c9c1ac;border-radius:5px;padding:0 8px;"></label></div>'
        f'{_toggle("donut", "Donut (ring)", donut)}'
        f'<button type="submit" style="margin-top:4px;padding:10px 18px;'
        f'background:#0b2341;color:#fff;border:none;border-radius:5px;'
        f'font-weight:600;cursor:pointer;">Render chart</button>'
        f'<a href="/pie-chart?reset=1" style="font-size:11.5px;'
        f'color:#1F7A75;">Reset</a>'
        f'</div></div></form>')

    body = (
        ck_page_title(
            "Pie Chart",
            eyebrow="UTILITY · CLIENT-READY PIE / DONUT",
            meta="Type a label, value, and colour per slice — get a "
                 "presentable static chart.",
        )
        + ck_source_purpose(
            purpose="Make a clean, deck-ready pie or donut in seconds — "
                    "set each slice's value and colour directly.",
            universe="user-supplied",
            source="Your slice inputs. Defaults are example placeholders.",
        )
        + '<div class="ts-wrap" style="max-width:1000px;">'
        + form
        + '<div style="margin-top:18px;border:1px solid #d6cfc0;'
          'border-radius:8px;padding:18px;background:#fff;text-align:center;">'
        + svg + '</div>'
        + '</div>')
    return chartis_shell(
        body, "Pie Chart", active_nav="/research",
        subtitle="Client-ready pie/donut")
