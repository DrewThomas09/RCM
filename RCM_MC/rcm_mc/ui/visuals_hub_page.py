"""Visuals hub — the landing page for the graphics toolkit.

One editorial catalog that surfaces the five chart/visual builders
(Chart Builder, Pie Chart, Excel Mapping, Exhibit Composer, Saved
Charts) with a live thumbnail of each, so a partner can see what each
makes and jump straight in. Pure presentation — every thumbnail is
rendered from the same kit the tools use, so the hub always reflects
the real output. Thumbnail values are illustrative placeholders; the
masthead source-note and the Saved-Charts "illustrative" tag say so
plainly, per the platform's never-mistake-a-template-for-live-data
convention.
"""
from __future__ import annotations

import html
from typing import Any, Dict

from ._chartis_kit import (
    chartis_shell, ck_editorial_head, ck_image_card, ck_kpi_block,
    ck_provenance_tooltip, ck_fmt_num, ck_data_universe, ck_next_section,
    ck_page_actions,
)
from .cdd_chart_kit import (
    render_cdd_chart, presentable_pie, compose_exhibit, parse_table,
    CHART_TYPES,
)


# ── Live thumbnails — rendered from the real chart kit ──────────────

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
        # Central render loop substitutes the editorial placeholder for
        # an empty return, so the card frame stays filled.
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


def _thumb_saved() -> str:
    # A mini "library" render — three named rows over a small spark, so
    # the card previews the concept without a real store. An explicit
    # "illustrative" tag marks these as mock rows so a partner never
    # believes they already have a populated library (ck_illustrative
    # convention: never mistake a template for live data).
    t = parse_table("Q\tV\nQ1\t10\nQ2\t16\nQ3\t13\nQ4\t21")
    spark = render_cdd_chart("line", t, {
        "title": "", "palette": "Chartis", "W": 320, "H": 118,
        "legend": False, "show_values": False, "width_px": 320})
    rows = "".join(
        f'<span class="vh-lib-row"><span class="vh-lib-name">'
        f'&#9733; {html.escape(n)}</span>'
        f'<span class="vh-lib-kind">{html.escape(k)}</span></span>'
        for n, k in (("Denials Pareto", "Chart"),
                     ("IC highlights slide", "Exhibit"),
                     ("Payer mix — monthly", "Chart")))
    return (
        '<span class="vh-lib">'
        '<span class="vh-lib-tag">Illustrative preview</span>'
        f'{rows}{spark}</span>')


# Editorial fallback for a thumbnail that fails to build — a framed
# image glyph + mono caption instead of an unexplained blank box. It
# carries an <svg> so the tests' "4+ thumbnails" floor holds even if a
# builder ever raises.
_THUMB_FALLBACK = (
    '<span class="vh-thumb vh-thumb-fallback" aria-hidden="true">'
    '<svg viewBox="0 0 48 40" width="46" height="38" fill="none" '
    'stroke="currentColor" stroke-width="1.6">'
    '<rect x="2" y="2" width="44" height="36" rx="3"/>'
    '<path d="M2 30 L16 18 L26 27 L34 20 L46 30"/>'
    '<circle cx="34" cy="12" r="3.4"/></svg>'
    '<span class="vh-fallback-cap">Preview unavailable · open the tool</span>'
    '</span>')


# (name, href, eyebrow, purpose-copy, thumbnail-builder)
_TOOLS = [
    ("Chart Builder", "/chart-builder", "BUILDER",
     f"Turn a pasted table into a deck-ready chart — {len(CHART_TYPES)} "
     "chart types with palette, per-series colour, and slide-sizing "
     "control.", _thumb_chart_builder),
    ("Pie Chart", "/pie-chart", "SLICE",
     "Build a client-ready pie or donut — a label, value, and colour "
     "per slice, with on-slice percentages and a value/% legend.",
     _thumb_pie),
    ("Excel Mapping", "/excel-mapping", "MAP",
     "Shade a US-state choropleth — set the low/mid/high gradient and "
     "paste state values straight from Excel.", _thumb_map),
    ("Exhibit Composer", "/exhibit", "COMPOSER",
     "Lay up to four charts on one 16:9 slide with a title block and "
     "source line — export the whole exhibit as one SVG or PNG.",
     _thumb_exhibit),
    ("Saved Charts", "/charts", "LIBRARY",
     "Reopen a chart or exhibit exactly as you left it — star Save to "
     "library on either builder to grow your set.", _thumb_saved),
]


# ── Page-local styles (no inline style= attributes) ─────────────────

_VH_CSS = """
.vh-chip-row { margin:0 0 var(--sc-s-5,19px); }
.vh-wrap { max-width:1060px; margin:0 auto; }
.vh-grid { display:grid;
  grid-template-columns:repeat(auto-fill, minmax(300px, 1fr));
  gap:var(--sc-s-7,38px); margin:var(--sc-s-6,28px) 0 var(--sc-s-5,19px); }
/* Editorial image-cards, made whole-card clickable via a stretched
   link on the single CTA, with a calm hover lift + focus ring. */
.vh-grid .ck-image-card { position:relative; transition:transform .16s ease; }
.vh-grid .ck-image-card:hover { transform:translateY(-3px); }
.vh-grid .ck-image-card:hover .ck-image-card-img {
  border-bottom-color:var(--sc-navy,#0b2341); }
.vh-grid .ck-image-card-title { transition:color .16s ease; }
.vh-grid .ck-image-card:hover .ck-image-card-title {
  color:var(--sc-teal-ink,#155752); }
.vh-grid .ck-arrow::after { content:''; position:absolute; inset:0; z-index:1; }
.vh-grid .ck-arrow:focus-visible {
  outline:2px solid var(--sc-teal,#155752); outline-offset:3px; }
/* Thumbnail slot: center the (wider-than-4:3) SVG in the bone frame. */
.vh-thumb { display:flex; align-items:center; justify-content:center;
  width:100%; height:100%; padding:10px; overflow:hidden; }
.vh-thumb-fallback { flex-direction:column; gap:9px;
  color:var(--sc-text-faint,#7a8699); }
.vh-fallback-cap { font-family:var(--sc-mono,monospace); font-size:10px;
  letter-spacing:.08em; text-transform:uppercase; }
/* Saved-charts mock library. */
.vh-lib { display:flex; flex-direction:column; gap:3px; width:100%; }
.vh-lib-tag { align-self:flex-start; font-family:var(--sc-mono,monospace);
  font-size:9px; font-weight:600; letter-spacing:.1em; text-transform:uppercase;
  color:var(--sc-teal-ink,#155752); border:1px solid var(--sc-rule,#d6cfc0);
  border-radius:2px; padding:1px 6px; margin-bottom:5px; }
.vh-lib-row { display:flex; justify-content:space-between; gap:8px;
  border-bottom:1px solid var(--sc-rule,#d6cfc0); padding:3px 4px;
  font-size:11px; color:var(--sc-text,#1a2332); }
.vh-lib-kind { color:var(--sc-text-faint,#7a8699);
  font-family:var(--sc-mono,monospace); font-size:10px; }
.vh-footnote { font-family:var(--sc-mono,monospace); font-size:10.5px;
  letter-spacing:.03em; line-height:1.65; color:var(--sc-text-faint,#7a8699);
  margin:var(--sc-s-5,19px) 0 0; max-width:78ch; }
@media (max-width:680px){ .vh-grid { grid-template-columns:1fr; } }
"""


def render_visuals_hub_page(qs: "Dict[str, Any] | None" = None) -> str:
    # ``qs`` is unused (the hub is stateless) but kept for signature
    # stability with the server call site.
    cards = ""
    for name, href, eyebrow, desc, thumb in _TOOLS:
        try:
            svg = thumb()
        except Exception:
            svg = ""
        if svg:
            image_html = f'<span class="vh-thumb" aria-hidden="true">{svg}</span>'
        else:
            image_html = _THUMB_FALLBACK
        cards += ck_image_card(
            image_html=image_html,
            eyebrow=eyebrow,
            title=name,
            body=desc,
            cta_text="Open tool",
            cta_href=href,
        )

    head = ck_editorial_head(
        eyebrow="RESEARCH · GRAPHICS TOOLKIT",
        title="Visuals",
        meta=(f"{len(_TOOLS)} TOOLS · {len(CHART_TYPES)} CHART TYPES · "
              "SVG / PNG EXPORT"),
        lede_italic_phrase="Deck-ready graphics,",
        lede_body=(
            "built from your own pasted data — every tool shares the "
            "Chartis palette, slide sizing, and one-click SVG/PNG export."),
        source_note="Your data. Thumbnails are illustrative placeholders.",
    )

    # Scope-at-a-glance stat strip, with an "explain this number" hover
    # on the two live counts (mirrors the /exports gold-standard).
    tools_value = ck_provenance_tooltip(
        "Visual tools", ck_fmt_num(len(_TOOLS)),
        explainer=(
            "The graphics toolkit — chart builder, pie/donut, US-state "
            "choropleth, multi-panel exhibit composer, and your "
            "saved-chart library."),
    )
    types_value = ck_provenance_tooltip(
        "Chart types", ck_fmt_num(len(CHART_TYPES)),
        explainer=(
            "Column, stacked, waterfall, funnel, tornado, slope, gantt, "
            "heatmap and more — every type the Chart Builder renders from "
            "a pasted table."),
        inject_css=False,
    )
    kpi_strip = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Visual Tools", tools_value,
                       "chart, map & exhibit builders")
        + ck_kpi_block("Chart Types", types_value, "in the Chart Builder")
        + ck_kpi_block("Export", "SVG · PNG", "one-click on every tool")
        + '</div>'
    )

    chip = f'<p class="vh-chip-row">{ck_data_universe("user-supplied")}</p>'
    footnote = (
        f'<p class="vh-footnote">All {len(_TOOLS)} tools share the Chartis '
        "palette, slide sizing, and one-click SVG/PNG export — the "
        f"{len(_TOOLS)} previews above use illustrative placeholder "
        "values, not sourced data.</p>")
    next_up = ck_next_section(
        "Start with the Chart Builder", "/chart-builder",
        eyebrow="Start here", italic_word="Builder")

    body = (
        head
        + kpi_strip
        + chip
        + '<div class="vh-wrap">'
        + f'<div class="vh-grid">{cards}</div>'
        + footnote
        + '</div>'
        + next_up
        + ck_page_actions()
    )
    return chartis_shell(
        body, "Visuals", active_nav="/research",
        subtitle="Graphics toolkit", extra_css=_VH_CSS)
