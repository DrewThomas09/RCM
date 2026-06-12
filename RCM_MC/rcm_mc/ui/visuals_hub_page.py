"""Visuals hub — the landing page for the graphics toolkit.

One place that surfaces the four chart/visual builders (Chart Builder,
Pie Chart, Excel Mapping, Exhibit Composer) with a live thumbnail of
each, so a partner can see what each makes and jump straight in. Pure
presentation — every thumbnail is rendered from the same kit the tools
use, so the hub always reflects the real output.
"""
from __future__ import annotations

import html
from typing import Any, Dict

from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
from .cdd_chart_kit import (
    render_cdd_chart, presentable_pie, compose_exhibit, parse_table,
    CHART_TYPES,
)


def _thumb_chart_builder() -> str:
    t = parse_table("Year\tRevenue\tEBITDA\n2021\t100\t22\n2022\t130\t31\n"
                    "2023\t165\t43\n2024\t210\t58")
    return render_cdd_chart("column", t, {
        "title": "", "palette": "Chartis", "width_px": 340,
        "legend": True, "show_values": False})


def _thumb_pie() -> str:
    return presentable_pie(
        [{"label": "AIC", "value": 38}, {"label": "Home", "value": 30},
         {"label": "HOPD", "value": 22}, {"label": "Office", "value": 10}],
        {"title": "", "donut": True, "width_px": 360})


def _thumb_map() -> str:
    try:
        from .excel_mapping_page import _map_svg, resolve_inputs
        return _map_svg(resolve_inputs(None))
    except Exception:
        return ""


def _thumb_exhibit() -> str:
    panels = [
        {"type": "column", "title": "Revenue",
         "table": parse_table("Y\tR\n2021\t100\n2022\t130\n2023\t165")},
        {"type": "donut", "title": "Mix",
         "table": parse_table("S\tV\nAIC\t38\nHome\t30\nHOPD\t32")},
        {"type": "waterfall", "title": "Bridge",
         "table": parse_table("S\tV\nEntry\t100\nGain\t30\nExit\t=130")},
        {"type": "bar", "title": "Share",
         "table": parse_table("O\tV\nA\t20\nB\t14\nOther\t66")},
    ]
    return compose_exhibit(panels, title="Investment Highlights",
                           eyebrow="CDD", source="Source: illustrative",
                           width_px=360)


_TOOLS = [
    ("Chart Builder", "/chart-builder",
     f"{len(CHART_TYPES)} chart types from a pasted table — column, "
     "stacked, waterfall, funnel, tornado, slope, gantt, heatmap and "
     "more. Per-series colours, palettes, sizing, SVG/PNG export.",
     _thumb_chart_builder),
    ("Pie Chart", "/pie-chart",
     "A client-ready pie or donut — type a label, value, and colour per "
     "slice. On-slice percentages + a value/% legend.", _thumb_pie),
    ("Excel Mapping", "/excel-mapping",
     "A US-state choropleth — set the low/mid/high gradient colours and "
     "a value per state (paste from Excel or edit in Python).", _thumb_map),
    ("Exhibit Composer", "/exhibit",
     "Lay up to four charts on one 16:9 deck slide with a title block + "
     "source — export the whole exhibit as one SVG/PNG.", _thumb_exhibit),
]


def render_visuals_hub_page(qs: "Dict[str, Any] | None" = None) -> str:
    cards = ""
    for name, href, desc, thumb in _TOOLS:
        try:
            svg = thumb()
        except Exception:
            svg = ""
        cards += (
            f'<a href="{html.escape(href, quote=True)}" '
            f'style="display:flex;flex-direction:column;border:1px solid '
            f'#d6cfc0;border-radius:8px;overflow:hidden;background:#fff;'
            f'text-decoration:none;transition:box-shadow .15s;">'
            f'<div style="background:#fbf9f4;border-bottom:1px solid #e4ddca;'
            f'padding:10px;text-align:center;min-height:150px;display:flex;'
            f'align-items:center;justify-content:center;">{svg}</div>'
            f'<div style="padding:12px 15px;">'
            f'<div style="font-family:\'Source Serif 4\',Georgia,serif;'
            f'font-size:16px;font-weight:700;color:#0b2341;">'
            f'{html.escape(name)} <span style="color:#1F7A75;">→</span></div>'
            f'<div style="font-size:12px;color:#465366;line-height:1.55;'
            f'margin-top:4px;">{html.escape(desc)}</div></div></a>')

    body = (
        ck_page_title(
            "Visuals",
            eyebrow="UTILITY · GRAPHICS TOOLKIT",
            meta="Build deck-ready charts, maps, and exhibits — Chartis-"
                 "styled, sized, and one-click exportable.",
        )
        + ck_source_purpose(
            purpose="The graphics toolkit: make the charts, maps, and "
                    "exhibits a CDD deck needs from your own data.",
            universe="user-supplied",
            source="Your data. Thumbnails use example placeholders.",
        )
        + '<div class="ts-wrap" style="max-width:1000px;">'
        + '<div style="display:grid;grid-template-columns:repeat(auto-fill,'
          'minmax(300px,1fr));gap:18px;">' + cards + '</div>'
        + '<p style="font-size:11.5px;color:#7a8699;margin-top:16px;'
          'line-height:1.6;">Every chart figure is your own input — no '
          'fabricated data. All four tools share the Chartis palette and '
          'one-click SVG/PNG export.</p>'
        + '</div>')
    return chartis_shell(
        body, "Visuals", active_nav="/research",
        subtitle="Graphics toolkit")
