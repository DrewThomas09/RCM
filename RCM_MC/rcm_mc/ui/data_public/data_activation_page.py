"""Data Activation Center — /data-activation.

One hub that surfaces every DATA REQUIRED analysis: what to upload, the
downloadable import template, who to request the data from, and what the
page computes once activated. Turns the honest "needs your data" pages into
an actionable, navigable checklist. Read-only over real structured registries
(surface_status tiers + activation_registry) — no fabricated values.
"""
from __future__ import annotations

import html as _html
from typing import Dict

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_page_title, ck_kpi_block
from rcm_mc.diligence.activation_registry import (
    ACTIVATIONS, category_label, categories,
)
from rcm_mc.diligence.surface_status import _RED, _DATA_REQUIRED, _NAVY, _GREEN


def _summary_strip() -> str:
    return (
        ck_kpi_block("Live / real data", f"{len(_GREEN)}", "GREEN — CMS/public/your data", "") +
        ck_kpi_block("Calculators", f"{len(_NAVY)}", "NAVY — compute off your inputs", "") +
        ck_kpi_block("Data required", f"{len(_DATA_REQUIRED)}", "activate by uploading your data", "") +
        ck_kpi_block("Deferred", f"{len(_RED)}", "documented reason (no public source)", "")
    )


def _card(a) -> str:
    border = P["border"]; tp = P["text"]; td = P["text_dim"]; fa = P.get("text_faint", td); ac = P["accent"]
    return (
        f'<div style="background:{P["panel"]};border:1px solid {border};border-radius:3px;'
        f'padding:12px 14px;margin-bottom:10px">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px">'
        f'<a href="{_html.escape(a.route)}" style="font-family:var(--sc-serif,Georgia,serif);'
        f'font-size:15px;color:{tp};text-decoration:none">{_html.escape(a.title)} &rarr;</a>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:9px;color:{ac};'
        f'border:1px solid {ac};border-radius:2px;padding:1px 6px;white-space:nowrap">DATA REQUIRED</span></div>'
        f'<div style="font-size:11px;color:{td};margin-top:6px"><b style="color:{tp}">Upload:</b> {_html.escape(a.upload)}</div>'
        f'<div style="font-size:11px;color:{td};margin-top:2px"><b style="color:{tp}">Request from:</b> {_html.escape(a.request_from)}</div>'
        f'<div style="font-size:11px;color:{td};margin-top:2px"><b style="color:{tp}">Activates:</b> {_html.escape(a.activates)}</div>'
        f'<div style="font-size:10px;color:{fa};margin-top:6px;font-family:JetBrains Mono,monospace">'
        f'template: {_html.escape(a.template)} &middot; '
        f'<a href="/import" style="color:{ac};text-decoration:none">go to import &rarr;</a></div>'
        f'</div>'
    )


def render_data_activation(params: Dict = None) -> str:
    border = P["border"]; td = P["text_dim"]
    by_cat: Dict[str, list] = {c: [] for c in categories()}
    for a in ACTIVATIONS:
        by_cat.setdefault(a.category, []).append(a)

    sections = []
    for cat in categories():
        items = by_cat.get(cat, [])
        if not items:
            continue
        cards = "".join(_card(a) for a in sorted(items, key=lambda x: x.title))
        sections.append(
            f'<div style="margin-bottom:20px"><div style="font-family:JetBrains Mono,monospace;'
            f'font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:{td};'
            f'margin-bottom:10px">{_html.escape(category_label(cat))} '
            f'<span style="color:{P["accent"]}">({len(items)})</span></div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px">'
            f'{cards}</div></div>'
        )

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title("Data Activation Center", eyebrow="ACTIVATE", meta=f"{len(ACTIVATIONS)} analyses ready to activate on your own deal/fund data")}
  <p style="font-size:13px;color:{td};max-width:70ch;margin:0 0 16px">
    These analyses have no public-data anchor — they activate on <b>your</b> deal/fund data.
    Each shows exactly what to upload, a downloadable import template, and who to request it from.
    Nothing here is fabricated; upload your data via <a href="/import" style="color:{P['accent']}">Import</a>
    to turn an analysis live.
  </p>
  <div class="ck-kpi-grid" style="grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:20px">{_summary_strip()}</div>
  {"".join(sections)}
</div>"""
    return chartis_shell(body, "Data Activation Center", active_nav="/data-activation")
