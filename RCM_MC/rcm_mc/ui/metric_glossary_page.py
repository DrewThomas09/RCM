"""PE Desk Metric Glossary — canonical reference page.

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

from ._chartis_kit import (
    chartis_shell, ck_eyebrow, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_provenance_tooltip,
)
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
    copy_link = (
        f'<button type="button" class="mg-copylink" '
        f'data-mg-copylink="{_html.escape(m.key, quote=True)}" '
        f'title="Copy a shareable link to this metric" '
        f'aria-label="Copy link to {_html.escape(m.label, quote=True)}">'
        f'Copy link</button>'
    )
    return (
        f'<div class="cad-card" id="{_html.escape(m.key)}" '
        f'style="scroll-margin-top:80px;">'
        f'<h2 style="margin-bottom:6px;display:flex;align-items:baseline;'
        f'flex-wrap:wrap;gap:8px;">'
        f'<span>{_html.escape(m.label)}{units_pill}</span>{copy_link}</h2>'
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

    metrics_value = ck_provenance_tooltip(
        "Metrics in glossary",
        ck_fmt_num(len(keys)),
        explainer=(
            "The canonical reference set for every numeric the "
            "platform surfaces. Each entry has a definition, "
            "rationale, formula, and the source documents that "
            "support it - the source of truth when a partner asks "
            "'what does this number mean'."
        ),
    )
    kpi_strip = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block("Metrics Defined", metrics_value, "with formulas")
        + ck_kpi_block("Categories", "8", "RCM, PE, ML, ...")
        + '</div>'
    )

    # Clipboard-only "Copy link" affordance: copies the metric's deep link
    # (…/metric-glossary#<key>) so a partner can share a definition. No
    # persistence, no upload; the button hides itself without the API.
    copylink_assets = (
        "<style>"
        ".mg-copylink{margin-left:auto;background:transparent;"
        "border:1px solid var(--cad-border,#d6cfc0);border-radius:3px;"
        "color:var(--cad-text3,#6b6557);font-family:var(--ck-mono,monospace);"
        "font-size:10px;letter-spacing:0.04em;text-transform:uppercase;"
        "padding:2px 8px;cursor:pointer;}"
        ".mg-copylink:hover{border-color:var(--cad-link,#155752);"
        "color:var(--cad-link,#155752);}"
        ".mg-copylink:focus-visible{outline:2px solid var(--cad-link,#155752);"
        "outline-offset:1px;}"
        "</style>"
        "<script>(function(){"
        "var ok=navigator.clipboard&&navigator.clipboard.writeText;"
        "var btns=document.querySelectorAll('[data-mg-copylink]');"
        "if(!ok){btns.forEach(function(b){b.hidden=true;});return;}"
        "btns.forEach(function(btn){btn.addEventListener('click',function(){"
        "var key=btn.getAttribute('data-mg-copylink');"
        "var url=location.origin+location.pathname+'#'+key;"
        "navigator.clipboard.writeText(url).then(function(){"
        "var t=btn.textContent;btn.textContent='Copied';"
        "setTimeout(function(){btn.textContent=t;},1500);},function(){});"
        "});});})();</script>"
    )

    # 2026-05-28 batch 25 · Group D sweep · universal strict 5-block
    # head. Drops the shell editorial_intro= auto-inject in favor
    # of the in-body universal helper.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="METRIC GLOSSARY",
        title="Where every number has a definition.",
        meta=f"{len(keys)} METRICS · DEFINITION + RATIONALE + FORMULA",
        lede_italic_phrase="Where every number has a definition.",
        lede_body=(
            "Cross-reference every number the platform "
            "surfaces — definition, rationale, formula, and "
            "the source documents that back it. Use this as "
            "the canonical answer when a partner asks 'where "
            "does that number come from?'."
        ),
    )

    body = (
        head
        + kpi_strip
        + _toc(keys)
        + "".join(cards)
        + copylink_assets
        + ck_next_section(
            "Open the methodology reference",
            "/methodology",
            eyebrow="Continue —",
            italic_word="methodology",
        )
    )

    return chartis_shell(
        body,
        "Metric Glossary",
        active_nav="/metric-glossary",
        subtitle=f"{len(keys)} metrics — definitions, rationale, formulas",
    )
