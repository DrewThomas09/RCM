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
from rcm_mc.ui._chart_kit import ck_hbar_chart
from rcm_mc.ui.world_geo_map import render_world_map
from rcm_mc.data_public.global_health_markets import (
    SOURCE_NOTE, country_detail, health_exp_values, pe_active_markets,
    ranked_markets, summary_stats,
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
        country_link_template="/markets/country/{iso2}",
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

    # ── Summary stats strip ──────────────────────────────────────────────
    s = summary_stats()

    def _kpi(label, val, sub):
        return (
            '<div style="flex:1;min-width:130px;border:1px solid var(--sc-rule,#c9c1ac);'
            'background:var(--sc-paper,#faf6ec);padding:10px 14px;border-radius:3px;">'
            f'<div style="font-family:var(--sc-mono,monospace);font-size:9.5px;'
            f'letter-spacing:.1em;text-transform:uppercase;color:#8b94a0;">{_html.escape(label)}</div>'
            f'<div style="font-family:var(--sc-serif,serif);font-size:24px;color:var(--sc-navy,#0b2341);'
            f'font-variant-numeric:tabular-nums;">{val}</div>'
            f'<div style="font-size:10.5px;color:#6a7480;margin-top:2px;">{_html.escape(sub)}</div></div>'
        )

    stats = (
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin:4px 0 18px;max-width:680px;">'
        + _kpi("Markets", str(s["n_markets"]), "with health-spend data")
        + _kpi("PE-active", str(s["n_pe_active"]), "sponsor markets")
        + _kpi("Mean spend", f'{s["mean_all"]:.1f}%', "of GDP, all markets")
        + _kpi("PE-active mean", f'{s["mean_pe_active"]:.1f}%', "of GDP")
        + '</div>'
    )

    # ── Comparison graph: ranked health-spend, PE-active toned ───────────
    chart_items = [
        (r["name"], r["health_pct_gdp"], "teal" if r["pe_active"] else "muted")
        for r in rows
    ]
    chart = ck_hbar_chart(
        "Health expenditure as % of GDP — by market",
        chart_items,
        value_fmt=lambda v: f"{v:.1f}%",
        reference=("mean", s["mean_all"]),
        subtitle="Teal = active healthcare-PE market · dashed line = dataset mean",
        source=SOURCE_NOTE,
        label_w=130.0,
    )

    # ── Per-region breakdown ─────────────────────────────────────────────
    rrows = "".join(
        f'<tr><td style="padding:3px 10px;font-size:11px;">{_html.escape(b["region"])}</td>'
        f'<td style="padding:3px 10px;font-size:11px;text-align:right;'
        f'font-family:var(--sc-mono,monospace);">{b["count"]}</td>'
        f'<td style="padding:3px 10px;font-size:11px;text-align:right;'
        f'font-family:var(--sc-mono,monospace);">{b["mean"]:.1f}%</td></tr>'
        for b in s["by_region"]
    )
    region_table = (
        '<div style="border:1px solid var(--sc-rule,#c9c1ac);border-radius:3px;'
        'overflow:hidden;max-width:340px;align-self:flex-start;">'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="background:var(--sc-bone,#f3eddb);">'
        '<th style="padding:5px 10px;text-align:left;font-size:9.5px;text-transform:uppercase;'
        'letter-spacing:.08em;color:#6a7480;">Region</th>'
        '<th style="padding:5px 10px;text-align:right;font-size:9.5px;text-transform:uppercase;'
        'letter-spacing:.08em;color:#6a7480;">Markets</th>'
        '<th style="padding:5px 10px;text-align:right;font-size:9.5px;text-transform:uppercase;'
        'letter-spacing:.08em;color:#6a7480;">Mean %GDP</th>'
        f'</tr></thead><tbody>{rrows}</tbody></table></div>'
    )
    comparison = (
        '<div style="display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start;'
        'margin:18px 0;">'
        f'<div style="flex:2;min-width:320px;">{chart}</div>'
        f'<div style="flex:1;min-width:260px;">'
        '<div style="font-family:var(--sc-mono,monospace);font-size:10px;letter-spacing:.1em;'
        'text-transform:uppercase;color:#5c6878;margin-bottom:8px;">Mean spend by region</div>'
        f'{region_table}</div>'
        '</div>'
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
        + title + intro + stats + map_html + comparison + table + '</div>'
    )
    return chartis_shell(body, "Global healthcare markets",
                         active_nav="/portfolio",
                         subtitle="Health-spend share across the markets PE targets")


def render_country_profile(iso2: str) -> str:
    """Per-market deep dive — /markets/country/<iso2>. Reached by clicking a
    country on the global map. Shows the market's health-spend share, its rank
    among all tracked markets, its region, PE-activity, and a comparison to its
    regional peers. Derived entirely from the curated dataset."""
    d = country_detail(iso2)
    if d is None:
        body = (
            '<div class="ck-page-wrap" style="max-width:720px;margin:0 auto;">'
            + ck_page_title("Market not tracked", eyebrow="INTERNATIONAL",
                            meta=_html.escape((iso2 or "").upper()))
            + '<p style="font-family:var(--sc-serif,serif);font-size:15px;'
            'color:var(--sc-text-dim,#465366);">No health-market data for this '
            'country yet. <a href="/markets/global" style="color:#155752;">'
            'Back to the global map</a>.</p></div>'
        )
        return chartis_shell(body, "Market not tracked", active_nav="/portfolio")

    name = d["name"]
    title = ck_page_title(
        name,
        eyebrow=f"INTERNATIONAL · {d['region']}",
        meta=(f"Health spend {d['health_pct_gdp']:.1f}% of GDP · "
              f"rank {d['rank']}/{d['n_total']} · "
              + ("active healthcare-PE market" if d["pe_active"] else "watch market")),
    )

    def _kpi(label, val, sub):
        return (
            '<div style="flex:1;min-width:140px;border:1px solid var(--sc-rule,#c9c1ac);'
            'background:var(--sc-paper,#faf6ec);padding:10px 14px;border-radius:3px;">'
            f'<div style="font-family:var(--sc-mono,monospace);font-size:9.5px;'
            f'letter-spacing:.1em;text-transform:uppercase;color:#8b94a0;">{_html.escape(label)}</div>'
            f'<div style="font-family:var(--sc-serif,serif);font-size:24px;color:var(--sc-navy,#0b2341);'
            f'font-variant-numeric:tabular-nums;">{val}</div>'
            f'<div style="font-size:10.5px;color:#6a7480;margin-top:2px;">{_html.escape(sub)}</div></div>'
        )

    kpis = (
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 18px;max-width:700px;">'
        + _kpi("Health spend", f'{d["health_pct_gdp"]:.1f}%', "of GDP")
        + _kpi("Global rank", f'#{d["rank"]}', f'of {d["n_total"]} markets')
        + _kpi("Region", d["region"], f'{len(d["region_peers"])} markets tracked')
        + _kpi("PE activity", "Active" if d["pe_active"] else "Watch",
               "healthcare sponsors" if d["pe_active"] else "less sponsor activity")
        + '</div>'
    )

    # Regional peers comparison — this market highlighted.
    peer_items = [
        (r["name"] + (" ◂" if r["iso2"] == d["iso2"] else ""), r["health_pct_gdp"],
         "navy" if r["iso2"] == d["iso2"] else "muted")
        for r in d["region_peers"]
    ]
    peer_chart = ck_hbar_chart(
        f"Health spend % of GDP — {_html.escape(d['region'])} markets",
        peer_items, value_fmt=lambda v: f"{v:.1f}%", source=SOURCE_NOTE,
        subtitle=f"{name} highlighted (navy)", label_w=130.0,
    )

    back = ('<div style="margin:18px 0 6px;"><a href="/markets/global" '
            'style="color:#155752;text-decoration:none;font-size:12px;">'
            '&larr; All global markets</a></div>')

    body = (
        '<div class="ck-page-wrap" style="max-width:900px;margin:0 auto;">'
        + title + kpis + peer_chart + back + '</div>'
    )
    return chartis_shell(body, f"{name} — market profile",
                         active_nav="/portfolio",
                         subtitle="International healthcare-market profile")
