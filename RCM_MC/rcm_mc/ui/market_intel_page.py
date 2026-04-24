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
from ._chartis_kit import P, chartis_shell
from .power_ui import provenance, sortable_table


_SENTIMENT_COLOR = {
    "positive": P["positive"],
    "negative": P["negative"],
    "neutral":  P["text_dim"],
    "mixed":    P["warning"],
}


def _hero(category: Optional[str], specialty: Optional[str]) -> str:
    sub_parts = []
    if category:
        sub_parts.append(f"Category: <strong>{html.escape(category)}</strong>")
    if specialty:
        sent = sector_sentiment(specialty)
        if sent:
            color = _SENTIMENT_COLOR.get(sent, P["text_dim"])
            sub_parts.append(
                f"Sector sentiment: <strong style=\"color:{color};\">"
                f"{html.escape(sent)}</strong>"
            )
    sub = " · ".join(sub_parts) if sub_parts else (
        "Public-market overlay. Refresh the curated content YAMLs "
        "quarterly from primary filings."
    )
    return (
        f'<div style="padding:24px 0 12px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:24px;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;'
        f'font-weight:600;">Market Intelligence</div>'
        f'<div style="font-size:26px;color:{P["text"]};font-weight:600;">'
        f'Public Comps &amp; Market Context</div>'
        f'<div style="font-size:12px;color:{P["text_dim"]};margin-top:6px;">'
        f'{sub}</div>'
        f'</div>'
    )


def _public_comps_section(
    category: Optional[str],
    target_revenue_usd: Optional[float],
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

    headers = [
        "Ticker", "Name", "Category", "Market Cap ($bn)",
        "EV ($bn)", "Revenue TTM ($bn)", "EBITDA TTM ($bn)",
        "EV/EBITDA", "EV/Revenue", "Debt/EBITDA",
    ]
    rows = []
    sort_keys = []
    for c in comps_dicts:
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
        ])
    table = sortable_table(
        headers, rows,
        name="public_comps",
        sort_keys=sort_keys,
        table_class="rcm-comps-table",
    )
    band_html = ""
    if band:
        band_html = (
            f'<div style="background:{P["panel_alt"]};border:1px solid '
            f'{P["border"]};border-left:3px solid {P["accent"]};'
            f'border-radius:4px;padding:12px 16px;margin-bottom:12px;">'
            f'<div style="font-size:10px;color:{P["text_faint"]};'
            f'letter-spacing:1.5px;text-transform:uppercase;'
            f'font-weight:600;margin-bottom:4px;">Category band</div>'
            f'<div style="font-size:14px;color:{P["text"]};">'
            f'Median EV/EBITDA: <strong>{band["median_ev_ebitda"]:.1f}x</strong> · '
            f'p25–p75: {band["p25_ev_ebitda"]:.1f}x – {band["p75_ev_ebitda"]:.1f}x · '
            f'Constituents: {", ".join(band["constituents"])}</div>'
            + (f'<div style="font-size:11px;color:{P["text_dim"]};'
               f'margin-top:6px;line-height:1.5;">{html.escape(band["note"])}'
               f'</div>' if band.get("note") else "")
            + '</div>'
        )
    return (
        f'<div style="margin-bottom:28px;">'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:10px;">Public Healthcare Operators</div>'
        f'{band_html}'
        f'{fallback}'
        f'{table}'
        f'</div>'
    )


def _transaction_multiples_section(
    specialty: Optional[str],
    ev_usd: Optional[float],
) -> str:
    if not specialty:
        return ""
    band = transaction_multiple(specialty=specialty, ev_usd=ev_usd)
    if not band:
        return (
            f'<div style="margin-bottom:28px;">'
            f'<div style="font-size:10px;color:{P["text_faint"]};'
            f'letter-spacing:1.5px;text-transform:uppercase;'
            f'font-weight:700;margin-bottom:10px;">'
            f'Private-market transaction multiples</div>'
            f'<div style="color:{P["text_faint"]};font-size:12px;'
            f'font-style:italic;">No transaction-multiple data for '
            f'{html.escape(specialty)}.</div></div>'
        )
    ev_range_str = (
        f" · target EV ${ev_usd/1e6:,.0f}M" if ev_usd else ""
    )
    return (
        f'<div style="background:{P["panel"]};border:1px solid '
        f'{P["border"]};border-left:3px solid {P["accent"]};'
        f'border-radius:4px;padding:14px 18px;margin-bottom:28px;">'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:6px;">Private-market transaction multiple</div>'
        f'<div style="font-size:14px;color:{P["text"]};margin-bottom:6px;">'
        f'{html.escape(specialty)} · {html.escape(band.deal_size_band)}'
        f'{ev_range_str}</div>'
        f'<div style="font-size:20px;color:{P["text"]};font-weight:700;'
        f'font-family:\'JetBrains Mono\',monospace;">'
        + provenance(
            f'{band.p50_ev_ebitda:.1f}x',
            source=f'Mertz Taggart / PitchBook healthcare aggregate '
                   f'({band.sample_size} deals trailing 12 months)',
            formula='median EV/EBITDA of clears in size-band',
            detail=(f'p25: {band.p25_ev_ebitda:.1f}x · '
                    f'p75: {band.p75_ev_ebitda:.1f}x'),
        )
        + f' <span style="font-size:11px;color:{P["text_faint"]};'
          f'font-family:inherit;font-weight:400;letter-spacing:.5px;">'
          f'(p25 {band.p25_ev_ebitda:.1f}x · p75 {band.p75_ev_ebitda:.1f}x)'
          f'</span></div>'
          + (f'<div style="font-size:11px;color:{P["text_dim"]};'
             f'margin-top:8px;line-height:1.5;">{html.escape(band.note)}'
             f'</div>' if band.note else '')
          + f'<div style="font-size:10px;color:{P["text_faint"]};'
          f'margin-top:8px;">Sample: {band.sample_size} deals trailing '
          f'12 months</div>'
        f'</div>'
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
        sent_color = _SENTIMENT_COLOR.get(it.sentiment, P["text_dim"])
        tag_html = "".join(
            f'<span style="font-size:9px;padding:1px 6px;background:'
            f'{P["panel_alt"]};color:{P["text_faint"]};border-radius:2px;'
            f'margin-left:4px;">{html.escape(t)}</span>'
            for t in it.tags
        )
        rows.append(
            f'<div style="padding:12px 0;border-bottom:1px solid '
            f'{P["border"]};">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:baseline;gap:10px;">'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1px;text-transform:uppercase;font-weight:600;'
            f'margin-bottom:2px;">{html.escape(it.date)} · '
            f'{html.escape(it.source)}'
            f'{(" · " + html.escape(it.specialty)) if it.specialty else ""}'
            f'</div>'
            f'<a href="{html.escape(it.url)}" target="_blank" '
            f'rel="noopener" style="font-size:14px;color:{P["text"]};'
            f'font-weight:500;text-decoration:none;line-height:1.4;">'
            f'{html.escape(it.title)}</a>'
            f'<div style="margin-top:4px;">{tag_html}</div>'
            f'<div style="font-size:11px;color:{P["text_dim"]};'
            f'line-height:1.5;margin-top:6px;">{html.escape(it.summary)}'
            f'</div></div>'
            f'<span style="font-size:9px;letter-spacing:1px;'
            f'text-transform:uppercase;font-weight:700;color:{sent_color};'
            f'padding:2px 6px;background:{P["panel_alt"]};border-radius:2px;'
            f'white-space:nowrap;">{html.escape(it.sentiment)}</span>'
            f'</div></div>'
        )
    return (
        f'<div style="margin-bottom:28px;">'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:10px;">Healthcare PE News Feed</div>'
        f'<div style="background:{P["panel"]};border:1px solid '
        f'{P["border"]};border-radius:4px;padding:4px 20px;">'
        f'{"".join(rows)}'
        f'</div></div>'
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
    body = (
        _hero(category, specialty)
        + _public_comps_section(category, revenue_usd)
        + _transaction_multiples_section(specialty, ev_usd)
        + _news_section(specialty, tickers, tags)
    )
    return chartis_shell(
        body, "RCM Diligence — Market Intelligence",
        subtitle="Public-market + PE transaction overlay",
    )
