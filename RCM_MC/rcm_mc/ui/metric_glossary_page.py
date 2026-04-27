"""SeekingChartis Metric Glossary — canonical reference page.

Renders every registered metric in `metric_glossary._GLOSSARY`
as an anchor-linkable card. Phase 4A of the v3 transformation
campaign requires that every page mentioning a metric link to
``/metric-glossary#<metric_key>`` — this page is the
destination those links point at.

Public API:
    render_metric_glossary() -> str
"""
from __future__ import annotations

import html as _html
from typing import List

from ._chartis_kit import chartis_shell
from .metric_glossary import (
    MetricDefinition,
    get_metric_definition,
    list_metrics,
)


def _metric_card(m: MetricDefinition) -> str:
    """One metric definition card with id=<key> for anchor linking."""
    units_pill = ""
    if m.units:
        units_pill = (
            f'<span class="pill" style="margin-left:8px;'
            f'font-size:10px;letter-spacing:0.06em;">'
            f'{_html.escape(m.units)}</span>'
        )
    typical = ""
    if m.typical_range:
        typical = (
            f'<div style="font-size:11px;color:var(--cad-text3);'
            f'margin-top:4px;">'
            f'<span class="micro">Typical:</span> '
            f'<span class="num">{_html.escape(m.typical_range)}</span>'
            f'</div>'
        )
    return (
        f'<div class="cad-card" id="{_html.escape(m.key)}" '
        f'style="scroll-margin-top:80px;">'
        f'<h2 style="margin-bottom:6px;">'
        f'{_html.escape(m.label)}{units_pill}</h2>'
        f'<div style="font-size:11px;color:var(--cad-text3);'
        f'font-family:var(--ck-mono,monospace);margin-bottom:10px;">'
        f'{_html.escape(m.key)}</div>'
        f'{typical}'
        f'<div style="margin-top:10px;">'
        f'<span class="micro" style="color:var(--cad-text3);">Definition</span>'
        f'<p style="margin:2px 0 8px;font-size:13px;color:var(--cad-text);">'
        f'{_html.escape(m.definition)}</p>'
        f'<span class="micro" style="color:var(--cad-text3);">Why it matters</span>'
        f'<p style="margin:2px 0 8px;font-size:13px;color:var(--cad-text);">'
        f'{_html.escape(m.why_it_matters)}</p>'
        f'<span class="micro" style="color:var(--cad-text3);">How calculated</span>'
        f'<p style="margin:2px 0;font-size:13px;color:var(--cad-text);">'
        f'{_html.escape(m.how_calculated)}</p>'
        f'</div>'
        f'</div>'
    )


def _toc(keys: List[str]) -> str:
    """Anchor-linked table of contents at the top of the page."""
    items = []
    for key in keys:
        m = get_metric_definition(key)
        if m is None:
            continue
        items.append(
            f'<li style="margin:2px 0;">'
            f'<a href="#{_html.escape(key)}" '
            f'style="color:var(--cad-link);text-decoration:none;">'
            f'{_html.escape(m.label)}</a>'
            f'<span style="color:var(--cad-text3);font-size:10px;'
            f'margin-left:6px;font-family:var(--ck-mono,monospace);">'
            f'{_html.escape(key)}</span>'
            f'</li>'
        )
    return (
        f'<div class="cad-card">'
        f'<h2>Metrics ({len(items)})</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);'
        f'margin-bottom:10px;">'
        f'Canonical reference for every metric on the platform. '
        f'Each card has an anchor — link from any page with '
        f'<code>/metric-glossary#&lt;key&gt;</code>.</p>'
        f'<ul style="list-style:none;padding:0;margin:0;'
        f'columns:2;column-gap:18px;font-size:12px;">'
        f'{"".join(items)}'
        f'</ul>'
        f'</div>'
    )


def render_metric_glossary() -> str:
    """Render the canonical metric reference page."""
    keys = list_metrics()
    cards: List[str] = []
    for key in keys:
        m = get_metric_definition(key)
        if m is None:
            continue
        cards.append(_metric_card(m))

    body = _toc(keys) + "".join(cards)

    return chartis_shell(
        body,
        "Metric Glossary",
        subtitle=f"{len(keys)} metrics — definitions, rationale, formulas",
    )
