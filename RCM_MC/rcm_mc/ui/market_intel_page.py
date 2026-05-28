"""Market Intelligence UI at /market-intel.

Three stacked sections:

    1. Public operator comps (HCA / THC / CYH / UHS / EHC / ARDT)
       with EV/EBITDA + EV/Revenue + payer mix, filtered by the
       caller's target category if one is supplied.

    2. Private-market transaction multiples for the target's
       specialty × deal-size.

    3. Healthcare PE news feed filtered to the target's context
       (tickers, specialty, tags).

Optional query params:
    ?category=MULTI_SITE_ACUTE_HOSPITAL
    &specialty=ANESTHESIOLOGY
    &ev_usd=350000000
    &revenue_usd=200000000
    &tickers=HCA,THC
    &tags=nsa,site_neutral
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..market_intel import (
    MultipleBand, NewsItem, PublicComp, category_bands,
    find_comparables, list_companies, news_for_target,
    sector_sentiment, transaction_multiple,
)
from ._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro, ck_source_purpose,
)
from .power_ui import provenance, sortable_table


_SENTIMENT_COLOR = {
    "positive": P["positive"],
    "negative": P["negative"],
    "neutral":  P["text_dim"],
    "mixed":    P["warning"],
}


def _target_scatter_chart(
    comps_dicts: List[Dict[str, Any]],
    target_revenue_usd: Optional[float] = None,
    target_ev_usd: Optional[float] = None,
    width: int = 1100, height: int = 420,
) -> str:
    """SVG scatter: EV/EBITDA (y) vs Revenue TTM (x) for the peer
    set, with the target highlighted if revenue + EV supplied.

    Clean layout — no axes noise, tight tick labels, peer labels
    only on hover (via <title>). Default size enlarged 2026-04-26
    per UX feedback (was 640x240, scatter was unreadably small).
    """
    if not comps_dicts:
        return ""
    pad_l, pad_r, pad_t, pad_b = 80, 32, 36, 52
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)

    xs = [c.get("revenue_ttm_usd_bn") or 0 for c in comps_dicts]
    ys = [c.get("ev_ebitda_multiple") or 0 for c in comps_dicts]
    # Include target in ranges so axis covers both.
    target_rev_bn = (
        target_revenue_usd / 1e9 if target_revenue_usd else None
    )
    target_mult = None
    if target_ev_usd and target_revenue_usd:
        # Approximate implied multiple assuming 12% EBITDA margin
        # (acute hospital system median).  Used for positioning in
        # the scatter; the partner sees the assumption inline.
        implied_ebitda = target_revenue_usd * 0.12
        if implied_ebitda > 0:
            target_mult = target_ev_usd / implied_ebitda
    if target_rev_bn is not None:
        xs = xs + [target_rev_bn]
    if target_mult is not None:
        ys = ys + [target_mult]
    if not any(x > 0 for x in xs) or not any(y > 0 for y in ys):
        return ""

    x_max = max(xs) * 1.1 or 1.0
    x_min = 0.0
    y_max = max(ys) * 1.15 or 1.0
    y_min = min(y for y in ys if y > 0) * 0.85

    def px_x(v): return pad_l + (v - x_min) / (x_max - x_min) * inner_w
    def px_y(v): return pad_t + inner_h - (v - y_min) / (y_max - y_min) * inner_h

    # Grid lines
    grid = []
    for y_t in (y_min, (y_min + y_max) / 2, y_max):
        grid.append(
            f'<line x1="{pad_l}" y1="{px_y(y_t):.1f}" '
            f'x2="{pad_l + inner_w}" y2="{px_y(y_t):.1f}" '
            f'stroke="{P["border_dim"]}" stroke-width="1" />'
            f'<text x="{pad_l - 6:.0f}" y="{px_y(y_t) + 3:.0f}" '
            f'fill="{P["text_faint"]}" text-anchor="end" '
            f'font-size="9" font-family="JetBrains Mono, monospace">'
            f'{y_t:.1f}x</text>'
        )

    # Peer dots
    dots = []
    for c in comps_dicts:
        x = c.get("revenue_ttm_usd_bn") or 0
        y = c.get("ev_ebitda_multiple") or 0
        if x <= 0 or y <= 0:
            continue
        cx = px_x(x)
        cy = px_y(y)
        title = (
            f"{c.get('ticker', '')} · {c.get('name', '')} · "
            f"${x:,.1f}B revenue · {y:.1f}x EV/EBITDA"
        )
        dots.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" '
            f'fill="{P["accent"]}" opacity="0.75">'
            f'<title>{html.escape(title)}</title></circle>'
            f'<text x="{cx + 7:.1f}" y="{cy - 6:.1f}" '
            f'fill="{P["text_faint"]}" font-size="9" '
            f'font-family="JetBrains Mono, monospace">'
            f'{html.escape(c.get("ticker", ""))}</text>'
        )

    # Target marker
    target_marker = ""
    if target_rev_bn is not None and target_mult is not None:
        tx = px_x(target_rev_bn)
        ty = px_y(target_mult)
        target_marker = (
            f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="9" '
            f'fill="none" stroke="{P["warning"]}" stroke-width="2">'
            f'<title>Target · ${target_rev_bn:,.1f}B revenue · '
            f'{target_mult:.1f}x implied EV/EBITDA (12% margin '
            f'assumption)</title></circle>'
            f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="3" '
            f'fill="{P["warning"]}"><title>Target</title></circle>'
            f'<text x="{tx + 12:.1f}" y="{ty + 4:.1f}" '
            f'fill="{P["warning"]}" font-size="10" '
            f'font-family="Helvetica Neue, Arial, sans-serif" '
            f'font-weight="700">TARGET</text>'
        )

    # X axis labels
    x_axis = []
    for x_t in (x_min, x_max / 2, x_max):
        x_axis.append(
            f'<text x="{px_x(x_t):.1f}" y="{pad_t + inner_h + 16:.1f}" '
            f'fill="{P["text_faint"]}" text-anchor="middle" '
            f'font-size="9" font-family="JetBrains Mono, monospace">'
            f'${x_t:,.1f}B</text>'
        )

    note = ""
    if target_marker:
        note = (
            f'<text x="{pad_l}" y="{height - 6:.0f}" '
            f'fill="{P["text_faint"]}" font-size="9.5" '
            f'font-family="Helvetica Neue, Arial, sans-serif" '
            f'font-style="italic">'
            f'Target position uses a 12% EBITDA margin assumption '
            f'(acute hospital median).</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;margin-top:8px;">'
        f'<text x="{pad_l}" y="14" fill="{P["text_dim"]}" '
        f'font-size="10" font-family="Helvetica Neue, Arial, sans-serif" '
        f'font-weight="700" letter-spacing="1.5">'
        f'EV/EBITDA vs REVENUE · PEER SCATTER</text>'
        f'{"".join(grid)}'
        f'{"".join(dots)}'
        f'{target_marker}'
        f'{"".join(x_axis)}'
        f'{note}'
        f'</svg>'
    )


def _hero(category: Optional[str], specialty: Optional[str]) -> str:
    sub_parts = []
    if category:
        sub_parts.append(f"Category: {html.escape(category)}")
    if specialty:
        sent = sector_sentiment(specialty)
        if sent:
            sub_parts.append(f"Sector sentiment: {html.escape(sent)}")
    sub = " · ".join(sub_parts) if sub_parts else (
        "Public-market overlay. Refresh the curated content YAMLs "
        "quarterly from primary filings."
    )
    # 2026-05-28 batch 20 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    return ck_editorial_head(
        eyebrow="MARKET INTELLIGENCE",
        title="Public comps & market context.",
        meta="PUBLIC-MARKET OVERLAY · QUARTERLY REFRESH",
        lede_italic_phrase="Public comps & market context.",
        lede_body=sub,
    )


def _public_comps_section(
    category: Optional[str],
    target_revenue_usd: Optional[float],
    target_ev_usd: Optional[float] = None,
) -> str:
    if category:
        payload = find_comparables(
            target_category=category,
            target_revenue_usd=target_revenue_usd,
        )
        comps_dicts = payload["comps"]
        band = payload["band"]
        if not comps_dicts:
            fallback = (
                f'<div style="color:{P["text_faint"]};font-size:12px;'
                f'font-style:italic;">{html.escape(payload.get("note", ""))}'
                f'</div>'
            )
        else:
            fallback = ""
        # Hydrate back to PublicComp objects for formatting convenience
        # but keep comparing against the dict for display.
    else:
        comps_dicts = [c.to_dict() for c in list_companies()]
        band = None
        fallback = ""

    def _consensus_pill(consensus: str) -> str:
        color = {
            "BUY": P["positive"], "HOLD": P["warning"],
            "SELL": P["negative"], "NONE": P["text_faint"],
        }.get(consensus.upper(), P["text_faint"])
        return (
            f'<span style="display:inline-block;padding:1px 7px;'
            f'border:1px solid {color};color:{color};font-size:9px;'
            f'letter-spacing:1.2px;text-transform:uppercase;'
            f'font-weight:700;border-radius:3px;">'
            f'{html.escape(consensus)}</span>'
        )

    def _surprise_cell(pct: Optional[float]) -> str:
        if pct is None:
            return "—"
        color = (
            P["positive"] if pct > 0.01
            else P["negative"] if pct < -0.01
            else P["text_dim"]
        )
        arrow = "▲" if pct > 0.01 else ("▼" if pct < -0.01 else "●")
        return (
            f'<span style="color:{color};font-family:\'JetBrains Mono\',monospace;">'
            f'{arrow} {pct*100:+.1f}%</span>'
        )

    headers = [
        "Ticker", "Name", "Category", "Market Cap ($bn)",
        "EV ($bn)", "Revenue TTM ($bn)", "EBITDA TTM ($bn)",
        "EV/EBITDA", "EV/Revenue", "Debt/EBITDA",
        "Analyst", "Q surprise",
    ]
    rows = []
    sort_keys = []
    for c in comps_dicts:
        ac = c.get("analyst_coverage") or {}
        el = c.get("earnings_latest") or {}
        consensus = str(ac.get("consensus") or "NONE").upper()
        price_target = ac.get("price_target_usd")
        surprise_pct = el.get("surprise_pct")
        analyst_html = _consensus_pill(consensus)
        if price_target:
            analyst_html += (
                f' <span style="color:{P["text_faint"]};'
                f'font-size:10px;">PT ${price_target:,.0f}</span>'
            )
        rows.append([
            c["ticker"],
            c["name"],
            c["category"],
            f"${c['market_cap_usd_bn']:,.1f}",
            provenance(
                f"${c['enterprise_value_usd_bn']:,.1f}",
                source=f"{c['ticker']} 10-K filing, TTM balance sheet",
                formula="market_cap + total_debt - cash",
            ),
            f"${c['revenue_ttm_usd_bn']:,.2f}",
            f"${c['ebitda_ttm_usd_bn']:,.2f}",
            provenance(
                f"{c['ev_ebitda_multiple']:.2f}x",
                source=(
                    f"{c['ticker']} — derived from 10-K TTM EBITDA "
                    "(CapIQ/Seeking Alpha consensus)"
                ),
                formula="enterprise_value / ebitda_ttm",
            ),
            f"{c['ev_revenue_multiple']:.2f}x",
            (f"{c['debt_to_ebitda']:.2f}x"
             if c.get("debt_to_ebitda") is not None else "—"),
            analyst_html,
            _surprise_cell(surprise_pct),
        ])
        sort_keys.append([
            c["ticker"],
            c["name"],
            c["category"],
            c["market_cap_usd_bn"],
            c["enterprise_value_usd_bn"],
            c["revenue_ttm_usd_bn"],
            c["ebitda_ttm_usd_bn"],
            c["ev_ebitda_multiple"],
            c["ev_revenue_multiple"],
            c.get("debt_to_ebitda") or 0.0,
            consensus,
            surprise_pct if surprise_pct is not None else -9.9,
        ])
    # Use the editorial `ck-table` class instead of the bespoke
    # `rcm-comps-table` so the table inherits chartis typography
    # (mono-uppercase headers, tabular-num numerics, parchment
    # background) and the data-sortable attribute hooks the editorial
    # sort JS. Partner-flagged the legacy form as "weird font + not
    # being sorted".
    table = sortable_table(
        headers, rows,
        name="public_comps",
        sort_keys=sort_keys,
        table_class="ck-table sortable",
    )
    band_html = ""
    if band:
        kpi_strip = (
            '<div class="ck-kpi-strip">'
            + ck_kpi_block(
                "Median EV/EBITDA",
                f'{band["median_ev_ebitda"]:.1f}x',
                sub=f'p25–p75: {band["p25_ev_ebitda"]:.1f}x – {band["p75_ev_ebitda"]:.1f}x',
            )
            + ck_kpi_block(
                "Constituents",
                f"{len(band['constituents'])}",
                sub=", ".join(band["constituents"]),
            )
            + '</div>'
        )
        band_html = ck_panel(
            kpi_strip
            + (f'<p class="ck-eyebrow">{html.escape(band["note"])}</p>'
               if band.get("note") else ""),
            title="Category band",
        )
    scatter = _target_scatter_chart(
        comps_dicts,
        target_revenue_usd=target_revenue_usd,
        target_ev_usd=target_ev_usd,
    )
    scatter_html = ""
    if scatter:
        scatter_html = ck_panel(scatter, title="Target vs comps")
    return ck_panel(
        f'{band_html}{scatter_html}{fallback}{table}',
        title="Public Healthcare Operators",
    )


def _transaction_multiples_section(
    specialty: Optional[str],
    ev_usd: Optional[float],
) -> str:
    if not specialty:
        return ""
    band = transaction_multiple(specialty=specialty, ev_usd=ev_usd)
    if not band:
        return ck_panel(
            '<p class="ck-section-body">'
            f'No transaction-multiple data for {html.escape(specialty)}.</p>',
            title="Private-market transaction multiples",
        )
    ev_range_str = (
        f" · target EV ${ev_usd/1e6:,.0f}M" if ev_usd else ""
    )
    inner = (
        '<p class="ck-eyebrow">'
        f'{html.escape(specialty)} · {html.escape(band.deal_size_band)}{ev_range_str}'
        '</p>'
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Median EV/EBITDA",
            f"{band.p50_ev_ebitda:.1f}x",
            sub=f"p25 {band.p25_ev_ebitda:.1f}x · p75 {band.p75_ev_ebitda:.1f}x",
        )
        + ck_kpi_block(
            "Sample size",
            f"{band.sample_size}",
            sub="deals trailing 12 months",
        )
        + '</div>'
        + (f'<p class="ck-section-body">{html.escape(band.note)}</p>'
           if band.note else "")
    )
    return ck_panel(
        inner, title="Private-market transaction multiple",
    )


def _news_section(
    specialty: Optional[str],
    tickers: Optional[List[str]],
    tags: Optional[List[str]],
) -> str:
    items = news_for_target(
        specialty=specialty, tickers=tickers, tags=tags, limit=12,
    )
    if not items:
        return ""
    rows = []
    for it in items:
        tag_html = "".join(
            f'<span class="mi-tag">{html.escape(t)}</span>'
            for t in it.tags
        )
        sent_cls = {
            "BULLISH": "cad-pos", "BEARISH": "cad-neg",
            "NEUTRAL": "",
        }.get(it.sentiment.upper(), "")
        rows.append(
            '<div class="mi-news-row">'
            '<div class="mi-news-body">'
            f'<div class="ck-eyebrow">{html.escape(it.date)} · '
            f'{html.escape(it.source)}'
            f'{(" · " + html.escape(it.specialty)) if it.specialty else ""}</div>'
            f'<a href="{html.escape(it.url)}" target="_blank" rel="noopener" '
            f'class="mi-news-title">{html.escape(it.title)}</a>'
            f'<div class="mi-news-tags">{tag_html}</div>'
            f'<p class="ck-section-body">{html.escape(it.summary)}</p>'
            '</div>'
            f'<span class="cad-badge {sent_cls}">{html.escape(it.sentiment)}</span>'
            '</div>'
        )
    return ck_panel(
        ''.join(rows),
        title="Healthcare PE News Feed",
    )


def _earnings_calendar_section() -> str:
    """Upcoming earnings snapshot derived from the most recent
    earnings_latest disclosures. Each ticker's next expected
    reporting date is heuristically estimated as last_reported +
    90 days (standard quarterly cadence)."""
    from datetime import date, datetime, timedelta
    comps = list_companies()
    rows: List[Dict[str, Any]] = []
    today = date.today()
    for c in comps:
        el = c.earnings_latest
        if el is None or not el.reported_on:
            continue
        try:
            reported = datetime.strptime(
                str(el.reported_on), "%Y-%m-%d",
            ).date()
        except (ValueError, TypeError):
            continue
        # Next-quarterly estimate: 90d after last report. Real feed
        # would replace this with consensus reporting calendar.
        next_expected = reported + timedelta(days=90)
        days_to = (next_expected - today).days
        rows.append({
            "ticker": c.ticker, "name": c.name,
            "last_period": el.period,
            "last_eps_reported": el.eps_reported,
            "last_surprise_pct": el.surprise_pct,
            "last_reported_on": el.reported_on,
            "next_expected": next_expected.isoformat(),
            "days_to_next": days_to,
            "analyst_consensus": (
                c.analyst_coverage.consensus
                if c.analyst_coverage else "—"
            ),
        })
    # Sort by soonest upcoming (negative days = past-due / recent)
    rows.sort(key=lambda r: r["days_to_next"])

    if not rows:
        return ""

    headers = [
        "Ticker", "Name", "Last period", "Last EPS",
        "Last surprise", "Next expected", "Days to next", "Analyst",
    ]
    table_rows: List[List[str]] = []
    sort_keys: List[List[Any]] = []
    for r in rows:
        surprise_pct = r["last_surprise_pct"]
        surprise_html = "—"
        if surprise_pct is not None:
            color = (
                P["positive"] if surprise_pct > 0.01
                else P["negative"] if surprise_pct < -0.01
                else P["text_dim"]
            )
            arrow = "▲" if surprise_pct > 0.01 else (
                "▼" if surprise_pct < -0.01 else "●"
            )
            surprise_html = (
                f'<span style="color:{color};font-family:\'JetBrains Mono\',monospace;">'
                f'{arrow} {surprise_pct*100:+.1f}%</span>'
            )
        # Color the "days to next" by proximity — red for imminent,
        # amber for < 14d, grey for further out, muted for past-due.
        days = r["days_to_next"]
        if days < 0:
            days_color = P["text_faint"]
            days_label = f"{abs(days)}d ago (reported)"
        elif days <= 7:
            days_color = P["negative"]
            days_label = f"{days}d"
        elif days <= 30:
            days_color = P["warning"]
            days_label = f"{days}d"
        else:
            days_color = P["text_dim"]
            days_label = f"{days}d"
        days_html = (
            f'<span style="color:{days_color};font-family:'
            f'\'JetBrains Mono\',monospace;font-weight:600;">'
            f'{html.escape(days_label)}</span>'
        )
        table_rows.append([
            r["ticker"], r["name"], r["last_period"],
            f"${r['last_eps_reported']:.2f}" if r["last_eps_reported"] else "—",
            surprise_html,
            r["next_expected"],
            days_html,
            r["analyst_consensus"],
        ])
        sort_keys.append([
            r["ticker"], r["name"], r["last_period"],
            r["last_eps_reported"] or 0,
            surprise_pct if surprise_pct is not None else -9.9,
            r["next_expected"],
            days,
            r["analyst_consensus"],
        ])
    table = sortable_table(
        headers, table_rows, name="earnings_calendar",
        sort_keys=sort_keys,
    )
    # Call-out if any are imminent
    imminent = [r for r in rows if 0 <= r["days_to_next"] <= 14]
    imminent_html = ""
    if imminent:
        names = ", ".join(r["ticker"] for r in imminent[:5])
        imminent_html = (
            '<p class="ck-section-body cad-warn">'
            f'<strong>⚠ {len(imminent)} upcoming in next 14 days '
            f'({html.escape(names)})</strong> — hold diligence pricing '
            'decisions until after prints.</p>'
        )
    return ck_panel(
        '<p class="ck-section-body">'
        "Derived from each ticker's most recent earnings report + "
        'standard 90-day quarterly cadence. Real Seeking Alpha / '
        'Yahoo Finance feed would replace the estimate with '
        'consensus-published dates.</p>'
        f'{imminent_html}{table}',
        title="Earnings calendar · next expected reporting dates",
    )


_MI_STYLES = f"""
<style>
.mi-tag{{font-size:9px;padding:1px 6px;background:{P["panel_alt"]};
color:{P["text_faint"]};border-radius:2px;margin-left:4px;}}
.mi-news-row{{padding:12px 0;border-bottom:1px solid {P["border"]};
display:flex;justify-content:space-between;align-items:baseline;gap:10px;}}
.mi-news-body{{flex:1;min-width:0;}}
.mi-news-title{{font-size:14px;color:{P["text"]};font-weight:500;
text-decoration:none;line-height:1.4;display:block;margin-top:2px;}}
.mi-news-tags{{margin-top:4px;}}
.mi-section-label{{font-size:10px;color:{P["text_faint"]};
letter-spacing:1.5px;text-transform:uppercase;font-weight:700;
margin-bottom:10px;}}
</style>
"""


def _geo_intel_section() -> str:
    """Surface the real-data Geographic Intelligence suite on the market-intel
    page — public-market comps + PE deal flow are one lens; real state/metro
    public data is the other. Pure navigation; renders no figures."""
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]
    links = [
        ("Map", "/geo-map", "shade states by any metric"),
        ("Compare", "/state-compare", "states side by side"),
        ("Rank", "/state-rankings", "all states on one metric"),
        ("Profile", "/state-profile", "one state + national rank"),
        ("Metros", "/metro-markets", "real CBSA demographics"),
        ("Counties", "/county-explorer", "drill into a state"),
    ]
    chips = "".join(
        f'<a href="{href}" style="display:inline-block;background:{P["panel_alt"]};'
        f'border:1px solid {border};border-radius:2px;padding:5px 10px;margin:0 6px 6px 0;'
        f'text-decoration:none;color:{ac};font-family:Inter Tight,sans-serif;font-size:12px">'
        f'{lbl} <span style="color:{fa};font-size:10px">· {hint}</span></a>'
        for lbl, href, hint in links
    )
    return (
        f'<div style="background:{P["panel"]};border:1px solid {border};'
        f'border-left:3px solid {ac};padding:14px 16px;margin:0 0 18px">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{td};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">'
        f'Geographic Intelligence · real public data</div>'
        f'<div style="font-size:12px;color:{td};margin-bottom:10px;max-width:72ch">'
        f'The public-market and PE-deal overlay below is one lens; the '
        f'<a href="/geo-intel" style="color:{ac};text-decoration:none;font-weight:600">'
        f'Geographic Intelligence</a> suite is the other — 50 states + DC and 918 metros '
        f'on real Census/ACS · CMS · HRSA · CDC · OIG data (no synthetic values).</div>'
        f'<div>{chips}</div></div>'
    )


def render_market_intel_page(
    *,
    category: Optional[str] = None,
    specialty: Optional[str] = None,
    ev_usd: Optional[float] = None,
    revenue_usd: Optional[float] = None,
    tickers: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> str:
    next_up = ck_next_section(
        "Dig into public-comp + PE deal flow",
        "/market-intel/seeking-alpha",
        eyebrow="Continue —",
        italic_word="deal",
    )
    body = (
        _MI_STYLES
        + _hero(category, specialty)
        + ck_source_purpose(
            purpose="Frame a target against listed public-operator comps and named PE transactions — the public-market read before/around a deal.",
            universe="research",
            confidence="mixed",
            source="Curated public-operator comps (HCA/THC/CYH/UHS/… from SEC filings + analyst aggregators) and a curated PE-transaction library; refreshed quarterly. Public-market context, not your deal's terms.",
            next_action="Pull the full public-comp + PE deal flow",
            next_href="/market-intel/seeking-alpha",
        )
        + _geo_intel_section()
        + _public_comps_section(
            category, revenue_usd, target_ev_usd=ev_usd,
        )
        + _transaction_multiples_section(specialty, ev_usd)
        + _earnings_calendar_section()
        + _news_section(specialty, tickers, tags)
        + next_up
    )
    return chartis_shell(
        body, "RCM Diligence — Market Intelligence",
        active_nav="/market-intel",
        subtitle="Public-market + PE transaction overlay",
    )
