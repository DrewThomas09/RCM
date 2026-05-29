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
from ._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro,
)
from .power_ui import (
    benchmark_chip, bookmark_hint, deal_context_bar,
    export_json_panel, interpret_callout, provenance, sortable_table,
)


# ────────────────────────────────────────────────────────────────────
# Scoped CSS (ck-sa- prefix)
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.ck-sa-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.ck-sa-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.ck-sa-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.ck-sa-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.ck-sa-panel{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 20px;margin-bottom:16px;}}
.ck-sa-callout{{background:{pa};padding:12px 16px;border-left:3px solid {ac};
border-radius:0 3px 3px 0;font-size:12px;color:{td};line-height:1.65;
max-width:900px;margin-top:12px;}}
.ck-sa-callout strong{{color:{tx};font-weight:700;}}
.ck-sa-filter-form{{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;}}
.ck-sa-filter-field{{flex:1 1 240px;}}
.ck-sa-filter-label{{display:block;font-size:10px;color:{tf};letter-spacing:1.2px;
text-transform:uppercase;font-weight:600;margin-bottom:4px;}}
.ck-sa-filter-input{{width:100%;background:{pa};color:{tx};border:1px solid {bd};
padding:8px 10px;border-radius:3px;
font-family:"JetBrains Mono",monospace;font-size:12px;
transition:border-color 120ms ease, box-shadow 120ms ease;}}
.ck-sa-filter-input:focus{{outline:none;border-color:{ac};
box-shadow:0 0 0 2px {ac}33;}}
.ck-sa-filter-btn{{padding:10px 18px;background:{ac};color:#fff;border:0;
border-radius:3px;font-size:11px;letter-spacing:1.2px;text-transform:uppercase;
font-weight:700;cursor:pointer;
transition:background 120ms ease, transform 120ms ease;}}
.ck-sa-filter-btn:hover{{filter:brightness(1.08);transform:translateY(-1px);}}
.ck-sa-filter-btn:active{{transform:translateY(0);filter:brightness(0.95);}}
.ck-sa-ticker-grid{{display:grid;
grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
gap:12px;margin-top:10px;}}
.ck-sa-ticker-card{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:12px 14px;transition:border-color 120ms, transform 120ms;}}
.ck-sa-ticker-card:hover{{border-color:{tf};transform:translateY(-1px);}}
.ck-sa-ticker-head{{display:flex;align-items:baseline;
justify-content:space-between;gap:8px;}}
.ck-sa-ticker-symbol{{font-family:"JetBrains Mono",monospace;
font-weight:700;font-size:17px;color:{tx};letter-spacing:0.5px;}}
.ck-sa-ticker-consensus{{font-size:9px;letter-spacing:1.2px;
text-transform:uppercase;font-weight:700;padding:2px 7px;
border-radius:2px;}}
.ck-sa-ticker-BUY{{background:{po};color:#fff;}}
.ck-sa-ticker-HOLD{{background:{wn};color:#1a1a1a;}}
.ck-sa-ticker-SELL{{background:{ne};color:#fff;}}
.ck-sa-ticker-NONE{{background:{pa};color:{td};border:1px solid {bd};}}
.ck-sa-ticker-name{{font-size:11px;color:{tf};
letter-spacing:0.5px;margin-top:2px;}}
.ck-sa-ticker-mult{{font-family:"JetBrains Mono",monospace;
font-size:22px;font-weight:700;color:{tx};margin-top:8px;
font-variant-numeric:tabular-nums;}}
.ck-sa-ticker-mult-label{{font-size:9px;letter-spacing:1.2px;
text-transform:uppercase;color:{tf};}}
.ck-sa-ticker-meta{{font-size:11px;color:{td};margin-top:8px;
line-height:1.5;}}
.ck-sa-ticker-meta strong{{color:{tx};font-weight:600;}}
.ck-sa-news-item{{padding:10px 0;border-bottom:1px solid {bd};}}
.ck-sa-news-date{{font-size:10px;letter-spacing:1.2px;text-transform:uppercase;
color:{tf};font-family:"JetBrains Mono",monospace;}}
.ck-sa-news-title{{font-size:14px;color:{tx};font-weight:600;
line-height:1.4;margin-top:4px;}}
.ck-sa-news-title a{{color:{tx};text-decoration:none;}}
.ck-sa-news-title a:hover{{color:{ac};}}
.ck-sa-news-meta{{font-size:10px;letter-spacing:1.1px;text-transform:uppercase;
color:{tf};margin-top:4px;}}
.ck-sa-news-summary{{font-size:12px;color:{td};line-height:1.6;
margin-top:6px;max-width:820px;}}
.ck-sa-sentiment-chip{{display:inline-block;padding:1px 7px;border-radius:2px;
font-size:10px;font-weight:700;letter-spacing:1px;margin-right:6px;}}
.ck-sa-sent-positive{{background:{po};color:#fff;}}
.ck-sa-sent-negative{{background:{ne};color:#fff;}}
.ck-sa-sent-neutral{{background:{pa};color:{td};border:1px solid {bd};}}
.ck-sa-tag{{display:inline-block;padding:1px 6px;margin:2px 4px 2px 0;
border-radius:2px;font-size:9.5px;color:{tf};
border:1px solid {bd};font-family:"JetBrains Mono",monospace;
letter-spacing:0.3px;}}
.ck-sa-sector-grid{{display:grid;
grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;}}
.ck-sa-sector-card{{background:{pn};border:1px solid {bd};border-radius:3px;
padding:10px 12px;border-left:3px solid var(--tone);}}
.ck-sa-sector-name{{font-size:11px;color:{tx};font-weight:600;
letter-spacing:0.3px;}}
.ck-sa-sector-sentiment{{font-size:10px;letter-spacing:1.2px;
text-transform:uppercase;color:var(--tone);font-weight:700;
margin-top:4px;}}
.ck-sa-sector-mult{{font-family:"JetBrains Mono",monospace;
font-size:13px;color:{td};margin-top:2px;}}
.ck-sa-tx-row{{padding:12px 0;border-bottom:1px solid {bd};
display:grid;grid-template-columns:100px 1fr 150px 90px;
gap:14px;align-items:baseline;}}
.ck-sa-tx-date{{font-family:"JetBrains Mono",monospace;font-size:11px;
color:{tf};}}
.ck-sa-tx-target{{font-size:13.5px;color:{tx};font-weight:600;}}
.ck-sa-tx-sponsor{{font-size:11px;color:{td};margin-top:3px;}}
.ck-sa-tx-mult{{font-family:"JetBrains Mono",monospace;font-size:15px;
font-weight:700;color:{tx};text-align:right;
font-variant-numeric:tabular-nums;}}
.ck-sa-tx-size{{font-family:"JetBrains Mono",monospace;font-size:11px;
color:{tf};text-align:right;}}
.ck-sa-tx-narrative{{grid-column:2 / -1;font-size:11.5px;color:{td};
line-height:1.55;margin-top:6px;max-width:820px;}}
.ck-sa-tx-specialty{{font-size:9.5px;letter-spacing:1px;
text-transform:uppercase;color:{tf};font-weight:600;}}
.ck-sa-sponsor-row{{display:flex;justify-content:space-between;
padding:6px 0;border-bottom:1px solid {bd};font-size:12px;}}
.ck-sa-sponsor-count{{font-family:"JetBrains Mono",monospace;
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
        f'<div class="ck-sa-ticker-card">'
        f'<div class="ck-sa-ticker-head">'
        f'<div class="ck-sa-ticker-symbol">{html.escape(comp.ticker)}</div>'
        f'<div class="ck-sa-ticker-consensus ck-sa-ticker-{consensus}">'
        f'{consensus}</div>'
        f'</div>'
        f'<div class="ck-sa-ticker-name">{html.escape(comp.name)}</div>'
        f'<div class="ck-sa-ticker-mult" '
        f'style="color:{mult_color};">'
        f'{comp.ev_ebitda_multiple:.1f}×</div>'
        f'<div class="ck-sa-ticker-mult-label">EV / EBITDA TTM</div>'
        f'<div class="ck-sa-ticker-meta">'
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
    return f'<div class="ck-sa-ticker-grid">{cards}</div>'


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
                f'<div class="ck-sa-sector-mult">'
                f'PE median {band["median"]:.1f}× '
                f'(n={band["count"]})</div>'
            )
        cards.append(
            f'<div class="ck-sa-sector-card" style="--tone:{tone};">'
            f'<div class="ck-sa-sector-name">'
            f'{html.escape(sp.replace("_", " "))}</div>'
            f'<div class="ck-sa-sector-sentiment">{label}</div>'
            f'{mult_line}'
            f'</div>'
        )
    return f'<div class="ck-sa-sector-grid">{"".join(cards)}</div>'


def _news_item_row(item: NewsItem) -> str:
    sent = (item.sentiment or "neutral").lower()
    tags = (
        "".join(
            f'<span class="ck-sa-tag">{html.escape(str(t))}</span>'
            for t in (item.tags or [])
        )
    )
    tickers = (
        "".join(
            f'<span class="ck-sa-tag" '
            f'style="color:{P["accent"]};border-color:{P["accent"]};">'
            f'{html.escape(str(t))}</span>'
            for t in (item.tickers or [])
        )
    )
    return (
        f'<div class="ck-sa-news-item">'
        f'<div class="ck-sa-news-date">{html.escape(item.date)}</div>'
        f'<div class="ck-sa-news-title">'
        f'<a href="{html.escape(item.url or "#")}" target="_blank" '
        f'rel="noopener">{html.escape(item.title)}</a></div>'
        f'<div class="ck-sa-news-meta">'
        f'<span class="ck-sa-sentiment-chip ck-sa-sent-{sent}">'
        f'{sent.upper()}</span>'
        f'{html.escape(item.source or "")} · '
        f'{html.escape((item.specialty or "").replace("_", " "))}'
        f'</div>'
        f'<div class="ck-sa-news-summary">'
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
                f'<div class="ck-sa-tx-narrative">'
                f'{html.escape(t.narrative)}</div>'
            )
        rows.append(
            f'<div class="ck-sa-tx-row">'
            f'<div class="ck-sa-tx-date">{html.escape(t.date)}</div>'
            f'<div>'
            f'<div class="ck-sa-tx-target">{html.escape(t.target)}</div>'
            f'<div class="ck-sa-tx-sponsor">'
            f'{html.escape(t.sponsor)} · '
            f'<span class="ck-sa-tx-specialty">'
            f'{html.escape(t.specialty.replace("_", " "))}</span>'
            f'</div>'
            f'</div>'
            f'<div class="ck-sa-tx-mult" style="color:{mult_color};">'
            f'{mult}<span style="font-size:10px;color:{P["text_faint"]};'
            f'font-weight:400;"><br/>EV/EBITDA</span></div>'
            f'<div class="ck-sa-tx-size">{size}<br/>'
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
            f'<div class="ck-sa-sponsor-row">'
            f'<span>{html.escape(sponsor)}</span>'
            f'<span class="ck-sa-sponsor-count">{count}</span>'
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

    # 2026-05-28 batch 24 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    intro = ck_editorial_head(
        eyebrow="Seeking Alpha · Market Intelligence",
        title="Healthcare public-market + PE snapshot.",
        meta=(
            f"{len(comps)} PUBLIC COMPS · "
            f"{len(txs)} PE TRANSACTIONS · "
            f"{len(news)} CURATED HEADLINES · "
            "QUARTERLY REFRESH"
        ),
        lede_italic_phrase="Healthcare public-market + PE snapshot.",
        lede_body=(
            f"{len(comps)} public comps · {len(txs)} PE "
            f"transactions · {len(news)} curated headlines · "
            "refreshed quarterly from public filings + aggregated "
            "analyst consensus."
        ),
    )
    headline_panel = ck_panel(
        f'<p class="ck-section-body">{html.escape(headline)}</p>'
        + interpret_callout("Market read:", plain)
        + (f'<p class="ck-section-body">{mult_chip}</p>'
           if mult_chip else ""),
        title="Latest market read",
    )
    hero = intro + headline_panel

    comps_callout = (
        f'<div class="ck-sa-callout">'
        f'<strong>Source: </strong>'
        f'10-K/10-Q filings, FactSet / CapIQ / Seeking Alpha '
        f'aggregated analyst consensus. Values refresh quarterly; '
        f'click any ticker to see the underlying comp in the '
        f'public-comp library. Multiple color-coding: '
        f'<span class="cad-pos">≥12× premium</span> · '
        f'<span class="cad-warn">8-12× in-line</span> · '
        f'<span class="cad-neg">&lt;8× discount</span>.'
        f'</div>'
    )
    comps_panel = ck_panel(
        _ticker_grid(comps) + comps_callout,
        title="Public healthcare comps · EV/EBITDA TTM + analyst consensus",
    )

    sector_callout = (
        f'<div class="ck-sa-callout">'
        f'Tone = dominant sentiment across curated headlines; '
        f'median multiple is the observed PE transaction EV/EBITDA '
        f'for the sector in the last 6 months. The pairing surfaces '
        f'the gap partners need to see — a sector with positive '
        f'sentiment but compressed multiples often signals a '
        f'buying opportunity.'
        f'</div>'
    )
    sector_panel = ck_panel(
        _sector_heatmap() + sector_callout,
        title="Sector sentiment heatmap · news sentiment × PE deal multiple",
    )

    tx_callout = (
        f'<div class="ck-sa-callout">'
        f'<strong>How to read: </strong>'
        f'Each row is one closed or announced deal with sponsor, '
        f'specialty, deal size and the published EV/EBITDA '
        f'multiple. Use this as a negotiation anchor — partners bid '
        f'into a market that just priced this deal at X× six weeks '
        f'ago. Hover narratives for sponsor thesis and risk '
        f'callouts.'
        f'</div>'
    )
    tx_panel = ck_panel(
        _pe_transactions_block(txs) + tx_callout,
        title="Recent healthcare PE transactions · last 6 months",
    )

    sponsor_callout = (
        f'<div class="ck-sa-callout">'
        f'Sponsors actively deploying capital in healthcare. Useful '
        f'for competitive-bid forecasting — if Welsh Carson or '
        f'Audax is circling the same sector, expect the auction '
        f'floor multiple to widen 50-100bps.'
        f'</div>'
    )
    sponsor_panel = ck_panel(
        _sponsor_leaderboard(activity) + sponsor_callout,
        title="Active sponsors · 12-month deal count",
    )

    news_panel = ck_panel(
        "".join(_news_item_row(n) for n in news[:12]),
        title="Healthcare PE + regulatory headlines · curated feed",
    )

    category_panel = ck_panel(
        _category_multiple_table(bands),
        title="Public-comp category bands — EV/EBITDA by sub-sector",
    )

    filter_form = ck_panel(
        f'<form method="get" action="/market-intel/seeking-alpha" '
        f'class="ck-sa-filter-form">'
        f'<div class="ck-sa-filter-field">'
        f'<label class="ck-sa-filter-label">Filter specialty</label>'
        f'<input name="specialty" value="{html.escape(filter_specialty)}" '
        f'placeholder="e.g. DIALYSIS" class="ck-sa-filter-input"/>'
        f'</div>'
        f'<div class="ck-sa-filter-field">'
        f'<label class="ck-sa-filter-label">Filter sponsor (partial match)</label>'
        f'<input name="sponsor" value="{html.escape(filter_sponsor)}" '
        f'placeholder="e.g. Audax" class="ck-sa-filter-input"/>'
        f'</div>'
        f'<button type="submit" class="ck-sa-filter-btn">'
        f'Apply filters</button>'
        f'</form>',
        title="Filter the snapshot",
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
        + '<div class="ck-sa-wrap">'
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
            '<div class="ck-sa-section-label">'
            'JSON export — full market-intel snapshot</div>',
            payload=payload,
            name="seeking_alpha_snapshot",
        )
        + bookmark_hint()
        + ck_next_section(
            "Apply this market read to a deal",
            "/diligence/deal",
            eyebrow="Continue —",
            italic_word="deal",
        )
        + '</div>'
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, "RCM Diligence — Seeking Alpha Market Intel",
        subtitle="Public comps × PE deal flow × curated news",
    )
