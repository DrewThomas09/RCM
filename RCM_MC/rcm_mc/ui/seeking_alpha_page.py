"""Seeking Alpha / public-market intelligence page.

Route: ``/market-intel/seeking-alpha``

Surfaces the curated public-comp + news + PE-transactions library
as one Bloomberg-tier market-intel dashboard:

    * Public healthcare comps grid (HCA, THC, CYH, UHS, DVA, etc.)
      with EV/EBITDA, price, YTD return, analyst consensus.
    * Sector sentiment heatmap across 10+ specialties.
    * Live-feel headlines with ticker/specialty tags.
    * Recent PE transactions (closed + announced) with sponsor,
      multiple, and narrative.
    * Sponsor leaderboard — who's deployed capital in the last 12 mo.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..market_intel import (
    CategoryBand, PETransaction, PublicComp,
    category_bands, list_companies, list_transactions,
    multiple_band_by_specialty, news_for_target,
    sector_sentiment, sponsor_activity,
)
from ..market_intel.news_feed import NewsItem, _all_items
from ._chartis_kit import P, chartis_shell
from .power_ui import (
    benchmark_chip, bookmark_hint, deal_context_bar,
    export_json_panel, interpret_callout, provenance, sortable_table,
)


# ────────────────────────────────────────────────────────────────────
# Scoped CSS (sa- prefix)
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.sa-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.sa-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.sa-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.sa-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.sa-panel{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 20px;margin-bottom:16px;}}
.sa-callout{{background:{pa};padding:12px 16px;border-left:3px solid {ac};
border-radius:0 3px 3px 0;font-size:12px;color:{td};line-height:1.65;
max-width:900px;margin-top:12px;}}
.sa-ticker-grid{{display:grid;
grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
gap:12px;margin-top:10px;}}
.sa-ticker-card{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:12px 14px;transition:border-color 120ms, transform 120ms;}}
.sa-ticker-card:hover{{border-color:{tf};transform:translateY(-1px);}}
.sa-ticker-head{{display:flex;align-items:baseline;
justify-content:space-between;gap:8px;}}
.sa-ticker-symbol{{font-family:"JetBrains Mono",monospace;
font-weight:700;font-size:17px;color:{tx};letter-spacing:0.5px;}}
.sa-ticker-consensus{{font-size:9px;letter-spacing:1.2px;
text-transform:uppercase;font-weight:700;padding:2px 7px;
border-radius:2px;}}
.sa-ticker-BUY{{background:{po};color:#fff;}}
.sa-ticker-HOLD{{background:{wn};color:#1a1a1a;}}
.sa-ticker-SELL{{background:{ne};color:#fff;}}
.sa-ticker-NONE{{background:{pa};color:{td};border:1px solid {bd};}}
.sa-ticker-name{{font-size:11px;color:{tf};
letter-spacing:0.5px;margin-top:2px;}}
.sa-ticker-mult{{font-family:"JetBrains Mono",monospace;
font-size:22px;font-weight:700;color:{tx};margin-top:8px;
font-variant-numeric:tabular-nums;}}
.sa-ticker-mult-label{{font-size:9px;letter-spacing:1.2px;
text-transform:uppercase;color:{tf};}}
.sa-ticker-meta{{font-size:11px;color:{td};margin-top:8px;
line-height:1.5;}}
.sa-ticker-meta strong{{color:{tx};font-weight:600;}}
.sa-news-item{{padding:10px 0;border-bottom:1px solid {bd};}}
.sa-news-date{{font-size:10px;letter-spacing:1.2px;text-transform:uppercase;
color:{tf};font-family:"JetBrains Mono",monospace;}}
.sa-news-title{{font-size:14px;color:{tx};font-weight:600;
line-height:1.4;margin-top:4px;}}
.sa-news-title a{{color:{tx};text-decoration:none;}}
.sa-news-title a:hover{{color:{ac};}}
.sa-news-meta{{font-size:10px;letter-spacing:1.1px;text-transform:uppercase;
color:{tf};margin-top:4px;}}
.sa-news-summary{{font-size:12px;color:{td};line-height:1.6;
margin-top:6px;max-width:820px;}}
.sa-sentiment-chip{{display:inline-block;padding:1px 7px;border-radius:2px;
font-size:10px;font-weight:700;letter-spacing:1px;margin-right:6px;}}
.sa-sent-positive{{background:{po};color:#fff;}}
.sa-sent-negative{{background:{ne};color:#fff;}}
.sa-sent-neutral{{background:{pa};color:{td};border:1px solid {bd};}}
.sa-tag{{display:inline-block;padding:1px 6px;margin:2px 4px 2px 0;
border-radius:2px;font-size:9.5px;color:{tf};
border:1px solid {bd};font-family:"JetBrains Mono",monospace;
letter-spacing:0.3px;}}
.sa-sector-grid{{display:grid;
grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;}}
.sa-sector-card{{background:{pn};border:1px solid {bd};border-radius:3px;
padding:10px 12px;border-left:3px solid var(--tone);}}
.sa-sector-name{{font-size:11px;color:{tx};font-weight:600;
letter-spacing:0.3px;}}
.sa-sector-sentiment{{font-size:10px;letter-spacing:1.2px;
text-transform:uppercase;color:var(--tone);font-weight:700;
margin-top:4px;}}
.sa-sector-mult{{font-family:"JetBrains Mono",monospace;
font-size:13px;color:{td};margin-top:2px;}}
.sa-tx-row{{padding:12px 0;border-bottom:1px solid {bd};
display:grid;grid-template-columns:100px 1fr 150px 90px;
gap:14px;align-items:baseline;}}
.sa-tx-date{{font-family:"JetBrains Mono",monospace;font-size:11px;
color:{tf};}}
.sa-tx-target{{font-size:13.5px;color:{tx};font-weight:600;}}
.sa-tx-sponsor{{font-size:11px;color:{td};margin-top:3px;}}
.sa-tx-mult{{font-family:"JetBrains Mono",monospace;font-size:15px;
font-weight:700;color:{tx};text-align:right;
font-variant-numeric:tabular-nums;}}
.sa-tx-size{{font-family:"JetBrains Mono",monospace;font-size:11px;
color:{tf};text-align:right;}}
.sa-tx-narrative{{grid-column:2 / -1;font-size:11.5px;color:{td};
line-height:1.55;margin-top:6px;max-width:820px;}}
.sa-tx-specialty{{font-size:9.5px;letter-spacing:1px;
text-transform:uppercase;color:{tf};font-weight:600;}}
.sa-sponsor-row{{display:flex;justify-content:space-between;
padding:6px 0;border-bottom:1px solid {bd};font-size:12px;}}
.sa-sponsor-count{{font-family:"JetBrains Mono",monospace;
font-weight:700;color:{ac};}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# Composed blocks
# ────────────────────────────────────────────────────────────────────

def _ticker_card(comp: PublicComp) -> str:
    consensus = (
        comp.analyst_coverage.consensus
        if comp.analyst_coverage else "NONE"
    )
    pt = (
        f"${comp.analyst_coverage.price_target_usd:.0f}"
        if comp.analyst_coverage and
        comp.analyst_coverage.price_target_usd else "—"
    )
    rc = (
        f"{comp.analyst_coverage.ratings_count}"
        if comp.analyst_coverage and
        comp.analyst_coverage.ratings_count else "—"
    )
    op_margin = (
        f"{comp.operating_margin*100:.1f}%"
        if comp.operating_margin else "—"
    )
    op_color = (
        P["positive"] if (comp.operating_margin or 0) >= 0.15
        else P["warning"] if (comp.operating_margin or 0) >= 0.08
        else P["negative"]
    )
    mult_color = (
        P["positive"] if comp.ev_ebitda_multiple and
        comp.ev_ebitda_multiple >= 12
        else P["warning"] if comp.ev_ebitda_multiple and
        comp.ev_ebitda_multiple >= 8
        else P["negative"]
    )
    return (
        f'<div class="sa-ticker-card">'
        f'<div class="sa-ticker-head">'
        f'<div class="sa-ticker-symbol">{html.escape(comp.ticker)}</div>'
        f'<div class="sa-ticker-consensus sa-ticker-{consensus}">'
        f'{consensus}</div>'
        f'</div>'
        f'<div class="sa-ticker-name">{html.escape(comp.name)}</div>'
        f'<div class="sa-ticker-mult" '
        f'style="color:{mult_color};">'
        f'{comp.ev_ebitda_multiple:.1f}×</div>'
        f'<div class="sa-ticker-mult-label">EV / EBITDA TTM</div>'
        f'<div class="sa-ticker-meta">'
        f'<strong>EV:</strong> ${comp.enterprise_value_usd_bn:,.1f}B · '
        f'<strong>Rev:</strong> ${comp.revenue_ttm_usd_bn:,.1f}B<br/>'
        f'<strong>Op margin:</strong> '
        f'<span style="color:{op_color};font-weight:700;">'
        f'{op_margin}</span> · '
        f'<strong>Debt/EBITDA:</strong> {comp.debt_to_ebitda:.1f}×<br/>'
        f'<strong>Analyst PT:</strong> {pt} ({rc} ratings)'
        f'</div>'
        f'</div>'
    )


def _ticker_grid(comps: List[PublicComp]) -> str:
    cards = "".join(_ticker_card(c) for c in comps)
    return f'<div class="sa-ticker-grid">{cards}</div>'


def _sector_heatmap() -> str:
    """Heatmap of all covered specialties × sentiment × median
    transaction multiple."""
    from ..market_intel.news_feed import _load as _news_load
    news_data = _news_load()
    # Derive per-specialty sentiment counts from the news items
    items = _all_items()
    by_sp_sent: Dict[str, Dict[str, int]] = {}
    for it in items:
        sp = (it.specialty or "").upper()
        if not sp:
            continue
        b = by_sp_sent.setdefault(
            sp, {"positive": 0, "negative": 0, "neutral": 0},
        )
        sent = (it.sentiment or "neutral").lower()
        # Collapse unknown sentiment labels into "neutral" so the
        # heatmap survives unusual YAML content without crashing.
        if sent not in b:
            sent = "neutral"
        b[sent] += 1

    mult_bands = multiple_band_by_specialty()
    all_sp = sorted(set(list(by_sp_sent.keys()) + list(mult_bands.keys())))

    cards: List[str] = []
    for sp in all_sp:
        sc = by_sp_sent.get(sp, {})
        pos = sc.get("positive", 0)
        neg = sc.get("negative", 0)
        if neg > pos and neg >= 2:
            tone = P["negative"]
            label = "NEGATIVE"
        elif pos > neg and pos >= 2:
            tone = P["positive"]
            label = "POSITIVE"
        elif pos or neg:
            tone = P["warning"]
            label = "MIXED"
        else:
            tone = P["text_faint"]
            label = "NEUTRAL"
        band = mult_bands.get(sp)
        mult_line = ""
        if band:
            mult_line = (
                f'<div class="sa-sector-mult">'
                f'PE median {band["median"]:.1f}× '
                f'(n={band["count"]})</div>'
            )
        cards.append(
            f'<div class="sa-sector-card" style="--tone:{tone};">'
            f'<div class="sa-sector-name">'
            f'{html.escape(sp.replace("_", " "))}</div>'
            f'<div class="sa-sector-sentiment">{label}</div>'
            f'{mult_line}'
            f'</div>'
        )
    return f'<div class="sa-sector-grid">{"".join(cards)}</div>'


def _news_item_row(item: NewsItem) -> str:
    sent = (item.sentiment or "neutral").lower()
    tags = (
        "".join(
            f'<span class="sa-tag">{html.escape(str(t))}</span>'
            for t in (item.tags or [])
        )
    )
    tickers = (
        "".join(
            f'<span class="sa-tag" '
            f'style="color:{P["accent"]};border-color:{P["accent"]};">'
            f'{html.escape(str(t))}</span>'
            for t in (item.tickers or [])
        )
    )
    return (
        f'<div class="sa-news-item">'
        f'<div class="sa-news-date">{html.escape(item.date)}</div>'
        f'<div class="sa-news-title">'
        f'<a href="{html.escape(item.url or "#")}" target="_blank" '
        f'rel="noopener">{html.escape(item.title)}</a></div>'
        f'<div class="sa-news-meta">'
        f'<span class="sa-sentiment-chip sa-sent-{sent}">'
        f'{sent.upper()}</span>'
        f'{html.escape(item.source or "")} · '
        f'{html.escape((item.specialty or "").replace("_", " "))}'
        f'</div>'
        f'<div class="sa-news-summary">'
        f'{html.escape((item.summary or "").strip())}</div>'
        f'<div style="margin-top:6px;">{tickers}{tags}</div>'
        f'</div>'
    )


def _pe_transactions_block(txs: List[PETransaction]) -> str:
    rows: List[str] = []
    for t in txs:
        size = f"${t.deal_size_usd_mm:,.0f}M" if t.deal_size_usd_mm else "—"
        mult = (
            f"{t.ev_ebitda_multiple:.1f}×"
            if t.ev_ebitda_multiple else "—"
        )
        mult_color = (
            P["positive"] if t.ev_ebitda_multiple and
            t.ev_ebitda_multiple >= 12
            else P["warning"] if t.ev_ebitda_multiple and
            t.ev_ebitda_multiple >= 9
            else P["negative"]
        )
        narr = ""
        if t.narrative:
            narr = (
                f'<div class="sa-tx-narrative">'
                f'{html.escape(t.narrative)}</div>'
            )
        rows.append(
            f'<div class="sa-tx-row">'
            f'<div class="sa-tx-date">{html.escape(t.date)}</div>'
            f'<div>'
            f'<div class="sa-tx-target">{html.escape(t.target)}</div>'
            f'<div class="sa-tx-sponsor">'
            f'{html.escape(t.sponsor)} · '
            f'<span class="sa-tx-specialty">'
            f'{html.escape(t.specialty.replace("_", " "))}</span>'
            f'</div>'
            f'</div>'
            f'<div class="sa-tx-mult" style="color:{mult_color};">'
            f'{mult}<span style="font-size:10px;color:{P["text_faint"]};'
            f'font-weight:400;"><br/>EV/EBITDA</span></div>'
            f'<div class="sa-tx-size">{size}<br/>'
            f'<span style="font-size:9px;letter-spacing:1.1px;'
            f'text-transform:uppercase;">deal size</span></div>'
            f'{narr}'
            f'</div>'
        )
    return "".join(rows)


def _sponsor_leaderboard(activity: Dict[str, int]) -> str:
    if not activity:
        return (
            f'<div style="font-size:12px;color:{P["text_dim"]};">'
            f'No sponsor activity recorded in the last 12 months.'
            f'</div>'
        )
    rows = []
    for sponsor, count in list(activity.items())[:8]:
        rows.append(
            f'<div class="sa-sponsor-row">'
            f'<span>{html.escape(sponsor)}</span>'
            f'<span class="sa-sponsor-count">{count}</span>'
            f'</div>'
        )
    return "".join(rows)


def _category_multiple_table(
    bands: Dict[str, CategoryBand],
) -> str:
    headers = [
        "Category", "Median EV/EBITDA", "P25", "P75",
        "# Comps", "Latest Review",
    ]
    rows = []
    sort_keys = []
    for cat in sorted(bands):
        b = bands[cat]
        rows.append([
            html.escape(cat.replace("_", " ")),
            f"{b.median_ev_ebitda:.2f}×",
            f"{b.p25_ev_ebitda:.2f}×",
            f"{b.p75_ev_ebitda:.2f}×",
            str(getattr(b, "comp_count", "—")),
            getattr(b, "as_of", "—"),
        ])
        sort_keys.append([
            cat, b.median_ev_ebitda, b.p25_ev_ebitda,
            b.p75_ev_ebitda,
            getattr(b, "comp_count", 0) or 0,
            getattr(b, "as_of", "") or "",
        ])
    return sortable_table(
        headers, rows, sort_keys=sort_keys,
        name="public_comp_category_bands",
        caption=(
            "Public-comp category bands — median EV/EBITDA by "
            "sub-sector, sortable · CSV export wired"
        ),
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def render_seeking_alpha_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}

    # Optional filters
    def first(k: str, d: str = "") -> str:
        return (qs.get(k) or [d])[0].strip()

    filter_specialty = first("specialty").upper()
    filter_sponsor = first("sponsor")

    comps = list_companies()
    txs = list_transactions()
    if filter_specialty:
        txs = [t for t in txs if t.specialty.upper() == filter_specialty]
    if filter_sponsor:
        txs = [
            t for t in txs
            if filter_sponsor.lower() in t.sponsor.lower()
        ]
    news = _all_items()
    if filter_specialty:
        news = [
            n for n in news
            if (n.specialty or "").upper() == filter_specialty
        ]
    bands = category_bands()
    activity = sponsor_activity(lookback_months=12)

    # Interpretation headline
    if txs:
        recent = txs[0]
        mult_bands = multiple_band_by_specialty()
        b = mult_bands.get(recent.specialty)
        rel_ctx = ""
        if b and recent.ev_ebitda_multiple:
            rel = recent.ev_ebitda_multiple - b["median"]
            rel_ctx = (
                f" ({'+' if rel >= 0 else ''}{rel:.1f}× "
                f"vs sector median {b['median']:.1f}×)"
            )
        headline = (
            f"Most recent covered transaction: "
            f"{recent.sponsor} → {recent.target} on "
            f"{recent.date} at "
            f"{(str(recent.ev_ebitda_multiple) + 'x' if recent.ev_ebitda_multiple else 'undisclosed mult')}"
            f"{rel_ctx}."
        )
    else:
        headline = "No transactions match the current filter."

    # Benchmark: peer-median EV/EBITDA across hospital sub-sector
    hospital_mult = None
    hospital_band = bands.get("MULTI_SITE_ACUTE_HOSPITAL")
    if hospital_band:
        hospital_mult = hospital_band.median_ev_ebitda
    mult_chip = (
        benchmark_chip(
            value=hospital_mult,
            peer_low=7.5, peer_high=10.0,
            peer_median=8.8, higher_is_better=True,
            format_spec=".2f", suffix="×",
            label="Hospital peer median",
            peer_label="5-yr norm",
        )
        if hospital_mult else ""
    )

    active_sponsors = ", ".join(list(activity.keys())[:3]) or "—"

    plain = (
        f"Healthcare PE deal flow is currently most active in "
        f"{active_sponsors}. Public hospital comp multiples are "
        f"stabilizing at "
        f"{f'{hospital_mult:.1f}×' if hospital_mult else '~9×'} "
        f"EV/EBITDA — partners underwriting rural/mid-sized "
        f"acquisitions should target entry multiples at a discount "
        f"to that public band given the small-target size penalty."
    )

    hero = (
        f'<div style="padding:22px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="sa-eyebrow">Seeking Alpha · Market Intelligence</div>'
        f'<div class="sa-h1">Healthcare public-market + PE snapshot</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'margin-top:4px;">'
        f'{len(comps)} public comps · {len(txs)} PE transactions · '
        f'{len(news)} curated headlines · refreshed quarterly from '
        f'public filings + aggregated analyst consensus'
        f'</div>'
        f'<div style="font-size:15px;color:{P["text"]};line-height:1.5;'
        f'margin-top:14px;max-width:880px;">'
        f'{html.escape(headline)}'
        f'</div>'
        + interpret_callout("Market read:", plain)
        + (f'<div style="margin-top:16px;">{mult_chip}</div>'
           if mult_chip else "")
        + f'</div>'
    )

    comps_panel = (
        f'<div class="sa-section-label">'
        f'Public healthcare comps · EV/EBITDA TTM + analyst consensus'
        f'</div>'
        f'<div class="sa-panel">'
        f'{_ticker_grid(comps)}'
        f'<div class="sa-callout">'
        f'<strong style="color:{P["text"]};">Source: </strong>'
        f'10-K/10-Q filings, FactSet / CapIQ / Seeking Alpha '
        f'aggregated analyst consensus. Values refresh quarterly; '
        f'click any ticker to see the underlying comp in the '
        f'public-comp library. Multiple color-coding: '
        f'<span style="color:{P["positive"]};">≥12× premium</span> · '
        f'<span style="color:{P["warning"]};">8-12× in-line</span> · '
        f'<span style="color:{P["negative"]};">&lt;8× discount</span>.'
        f'</div>'
        f'</div>'
    )

    sector_panel = (
        f'<div class="sa-section-label">'
        f'Sector sentiment heatmap · news sentiment × PE deal multiple'
        f'</div>'
        f'<div class="sa-panel">'
        f'{_sector_heatmap()}'
        f'<div class="sa-callout">'
        f'Tone = dominant sentiment across curated headlines; '
        f'median multiple is the observed PE transaction EV/EBITDA '
        f'for the sector in the last 6 months. The pairing surfaces '
        f'the gap partners need to see — a sector with positive '
        f'sentiment but compressed multiples often signals a '
        f'buying opportunity.'
        f'</div>'
        f'</div>'
    )

    tx_panel = (
        f'<div class="sa-section-label">'
        f'Recent healthcare PE transactions · last 6 months'
        f'</div>'
        f'<div class="sa-panel">'
        f'{_pe_transactions_block(txs)}'
        f'<div class="sa-callout">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'Each row is one closed or announced deal with sponsor, '
        f'specialty, deal size and the published EV/EBITDA '
        f'multiple. Use this as a negotiation anchor — partners bid '
        f'into a market that just priced this deal at X× six weeks '
        f'ago. Hover narratives for sponsor thesis and risk '
        f'callouts.'
        f'</div>'
        f'</div>'
    )

    sponsor_panel = (
        f'<div class="sa-section-label">'
        f'Active sponsors · 12-month deal count'
        f'</div>'
        f'<div class="sa-panel">'
        f'{_sponsor_leaderboard(activity)}'
        f'<div class="sa-callout">'
        f'Sponsors actively deploying capital in healthcare. Useful '
        f'for competitive-bid forecasting — if Welsh Carson or '
        f'Audax is circling the same sector, expect the auction '
        f'floor multiple to widen 50-100bps.'
        f'</div>'
        f'</div>'
    )

    news_panel = (
        f'<div class="sa-section-label">'
        f'Healthcare PE + regulatory headlines · curated feed'
        f'</div>'
        f'<div class="sa-panel">'
        + "".join(_news_item_row(n) for n in news[:12])
        + f'</div>'
    )

    category_panel = (
        f'<div class="sa-section-label">'
        f'Public-comp category bands — EV/EBITDA by sub-sector</div>'
        f'<div class="sa-panel">'
        f'{_category_multiple_table(bands)}'
        f'</div>'
    )

    filter_form = (
        f'<div class="sa-panel">'
        f'<form method="get" action="/market-intel/seeking-alpha" '
        f'style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;">'
        f'<div style="flex:1 1 240px;">'
        f'<label style="display:block;font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;font-weight:600;'
        f'margin-bottom:4px;">Filter specialty</label>'
        f'<input name="specialty" value="{html.escape(filter_specialty)}" '
        f'placeholder="e.g. DIALYSIS" '
        f'style="width:100%;background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};padding:8px 10px;border-radius:3px;'
        f'font-family:\'JetBrains Mono\',monospace;font-size:12px;"/>'
        f'</div>'
        f'<div style="flex:1 1 240px;">'
        f'<label style="display:block;font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;font-weight:600;'
        f'margin-bottom:4px;">Filter sponsor (partial match)</label>'
        f'<input name="sponsor" value="{html.escape(filter_sponsor)}" '
        f'placeholder="e.g. Audax" '
        f'style="width:100%;background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};padding:8px 10px;border-radius:3px;'
        f'font-family:\'JetBrains Mono\',monospace;font-size:12px;"/>'
        f'</div>'
        f'<button type="submit" '
        f'style="padding:10px 18px;background:{P["accent"]};color:#fff;'
        f'border:0;border-radius:3px;font-size:11px;letter-spacing:1.2px;'
        f'text-transform:uppercase;font-weight:700;cursor:pointer;">'
        f'Apply filters</button>'
        f'</form></div>'
    )

    # Full JSON payload for programmatic access
    payload = {
        "public_comps": [c.to_dict() for c in comps],
        "category_bands": {
            k: v.to_dict() for k, v in bands.items()
        },
        "pe_transactions": [t.to_dict() for t in txs],
        "headlines": [
            {
                "date": n.date, "title": n.title,
                "source": n.source, "url": n.url,
                "sentiment": n.sentiment, "specialty": n.specialty,
                "summary": n.summary, "tickers": list(n.tickers or []),
                "tags": list(n.tags or []),
            } for n in news
        ],
        "sponsor_activity_12mo": activity,
        "multiple_band_by_specialty": multiple_band_by_specialty(),
    }

    body = (
        _scoped_styles()
        + '<div class="sa-wrap">'
        + deal_context_bar(qs, active_surface="")
        + hero
        + filter_form
        + comps_panel
        + sector_panel
        + tx_panel
        + sponsor_panel
        + news_panel
        + category_panel
        + export_json_panel(
            '<div class="sa-section-label" style="margin-top:22px;">'
            'JSON export — full market-intel snapshot</div>',
            payload=payload,
            name="seeking_alpha_snapshot",
        )
        + bookmark_hint()
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Seeking Alpha Market Intel",
        subtitle="Public comps × PE deal flow × curated news",
    )
