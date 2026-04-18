"""Module Index — /module-index."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block
from rcm_mc.ui.chartis._helpers import render_page_explainer


def _modules_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Module","left"),("Category","center"),("Phase","center"),("Persona","center"),
            ("Description","left"),("Route","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        corpus_ind = pos if m.corpus_dependent else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.name)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(m.category)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(m.lifecycle_phase)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(m.primary_persona)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.description)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}"><a href="{m.route}" style="color:{acc};text-decoration:none">{_html.escape(m.route)}</a></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _categories_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Category","left"),("Module Count","right"),("Lifecycle Phases","left"),("Example Modules","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{c.module_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{_html.escape(c.lifecycle_phases)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.example_modules)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _phases_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Lifecycle Phase","left"),("Module Count","right"),("Primary Output","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.phase)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{p.module_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.primary_output)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _personas_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Persona","left"),("Module Count","right"),("Top Modules","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.persona)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{p.module_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.top_modules)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_module_index(params: dict = None) -> str:
    from rcm_mc.data_public.module_index import compute_module_index
    r = compute_module_index()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    corpus_dep = sum(1 for m in r.modules if m.corpus_dependent)

    kpi_strip = (
        ck_kpi_block("Total Modules", str(r.total_modules), "", "") +
        ck_kpi_block("Categories", str(r.categories), "", "") +
        ck_kpi_block("Corpus-Dependent", str(corpus_dep), "", "") +
        ck_kpi_block("Lifecycle Phases", str(len(r.phase_rollups)), "", "") +
        ck_kpi_block("Personas", str(len(r.persona_usage)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "") +
        ck_kpi_block("Platform Scale", "IC-grade", "", "") +
        ck_kpi_block("Last Module Added", "Module 82", "", "")
    )

    m_tbl = _modules_table(r.modules)
    c_tbl = _categories_table(r.category_rollups)
    p_tbl = _phases_table(r.phase_rollups)
    ps_tbl = _personas_table(r.persona_usage)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Seeking Chartis Module Index</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_modules} analytical modules across {r.categories} categories · searchable catalog mapping route, category, lifecycle phase, and persona — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Full Module Catalog</div>{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Category Rollup</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Lifecycle Phase Distribution</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Primary Persona Usage</div>{ps_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Module Index:</strong> This page is the platform's map of itself.
    Every analytical module is tagged with: (1) category — the diligence dimension it covers,
    (2) lifecycle phase — where in sourcing/diligence/portfolio/exit it's used,
    (3) primary persona — analyst for data catalogs, associate for screeners and roll-ups, principal for capital-structure and IC decisions.
    {corpus_dep} modules derive benchmarks from the live corpus ({r.corpus_deal_count:,} deals); the remainder are reference catalogs or playbooks.
    Use this index to onboard new team members or run a self-audit of diligence coverage before submitting an IC memo.
  </div>
</div>"""

    explainer = render_page_explainer(
        what=(
            "Browsable catalog of every analytical module on the "
            "platform, tagged by diligence category, lifecycle phase "
            "(sourcing / diligence / portfolio / exit), primary "
            "persona, route, and whether it depends on the live "
            "corpus."
        ),
        source="data_public/module_index.py (module catalog).",
        page_key="module-index",
    )
    return chartis_shell(explainer + body, "Module Index", active_nav="/module-index")
