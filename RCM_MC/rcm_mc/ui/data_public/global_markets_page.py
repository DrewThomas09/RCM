"""Global healthcare markets — /markets/global.

The first international surface: a real world choropleth (vendored Natural
Earth boundaries) shaded by current health expenditure as a share of GDP, with
the most active healthcare-PE markets outlined, plus a ranked table. Health-
spend share is a first-order proxy for addressable-market size — the macro
context for taking a healthcare-PE thesis cross-border.

Honesty: every figure carries the OECD/World Bank provenance note; numbers are
approximate / latest-available, and the map's projection caveat is shown.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import chartis_shell, ck_page_title
from rcm_mc.ui.world_geo_map import render_world_map
from rcm_mc.data_public.global_health_markets import (
    SOURCE_NOTE, health_exp_values, pe_active_markets, ranked_markets,
)


def render_global_markets() -> str:
    rows = ranked_markets()
    values = health_exp_values()
    accent = pe_active_markets()
    n = len(rows)
    n_active = len(accent)

    title = ck_page_title(
        "Global healthcare markets",
        eyebrow="INTERNATIONAL · /markets/global",
        meta=f"{n} markets · health spend % of GDP · {n_active} active PE markets",
    )

    fmt = lambda v: f"{v:.1f}%"  # noqa: E731
    notes = {iso2: rec["region"] for iso2, rec in
             ((r["iso2"], r) for r in rows)}
    map_html = render_world_map(
        values, metric_label="of GDP", value_format=fmt,
        notes=notes, accent=accent, accent_label="active healthcare-PE market",
        legend_label="health spend % GDP",
        caveat_text=(
            "Equirectangular SVG world map (Natural Earth 1:110m boundaries, "
            "public domain). Shading = current health expenditure as % of GDP; "
            "outlined countries are the more active healthcare-PE markets. "
            + SOURCE_NOTE
        ),
    )

    intro = (
        '<p style="font-family:var(--sc-serif,serif);font-size:15px;line-height:1.55;'
        'color:var(--sc-text-dim,#465366);max-width:74ch;margin:6px 0 16px;">'
        'Where healthcare spends, capital follows. This map shades each market '
        'by <em>current health expenditure as a share of GDP</em> — a first-'
        'order proxy for addressable-market size when taking an RCM / services '
        'thesis cross-border. The most active healthcare-PE markets are '
        'outlined in amber.</p>'
    )

    # Ranked table.
    trows = []
    for i, r in enumerate(rows):
        stripe = ' style="background:var(--sc-bone,#f3eddb)"' if i % 2 else ""
        pe = ('<span style="color:#b8842e;font-weight:600;">●</span>'
              if r["pe_active"] else
              '<span style="color:#c9c1ac;">○</span>')
        trows.append(
            f'<tr{stripe}>'
            f'<td style="padding:4px 10px;font-size:11px;text-align:right;'
            f'font-family:var(--sc-mono,monospace);color:#8b94a0;">{i+1}</td>'
            f'<td style="padding:4px 10px;font-size:12px;">{_html.escape(r["name"])}</td>'
            f'<td style="padding:4px 10px;font-size:11px;color:#465366;">{_html.escape(r["region"])}</td>'
            f'<td style="padding:4px 10px;font-size:12px;text-align:right;'
            f'font-family:var(--sc-mono,monospace);">{r["health_pct_gdp"]:.1f}%</td>'
            f'<td style="padding:4px 10px;text-align:center;">{pe}</td>'
            '</tr>'
        )
    table = (
        '<div style="border:1px solid var(--sc-rule,#c9c1ac);border-radius:3px;'
        'overflow:hidden;margin-top:18px;max-width:640px;">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="background:var(--sc-navy,#0b2341);color:#fff;">'
        '<th style="padding:6px 10px;text-align:right;font-size:10px;">#</th>'
        '<th style="padding:6px 10px;text-align:left;font-size:10px;">Market</th>'
        '<th style="padding:6px 10px;text-align:left;font-size:10px;">Region</th>'
        '<th style="padding:6px 10px;text-align:right;font-size:10px;">Health % GDP</th>'
        '<th style="padding:6px 10px;text-align:center;font-size:10px;">PE-active</th>'
        f'</tr></thead><tbody>{"".join(trows)}</tbody></table></div>'
        f'<div style="font-size:10px;color:#8b94a0;margin-top:6px;max-width:640px;">'
        f'● active healthcare-PE market &nbsp;·&nbsp; {_html.escape(SOURCE_NOTE)}</div>'
    )

    body = (
        '<div class="ck-page-wrap" style="max-width:1040px;margin:0 auto;">'
        + title + intro + map_html + table + '</div>'
    )
    return chartis_shell(body, "Global healthcare markets",
                         active_nav="/portfolio",
                         subtitle="Health-spend share across the markets PE targets")
