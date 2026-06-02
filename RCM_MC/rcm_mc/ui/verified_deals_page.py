"""Verified Deals — /verified-deals.

Surfaces the hand-curated, fully-sourced real-deal dataset
(``data_public/verified_deals.py``) so a partner can SEE and check the real
deals — every row links to its source. This is the honest counterweight to the
synthetic seed corpus: a growing set of genuine, verifiable healthcare-services
PE/M&A deals (including the public-record bankruptcies that make a corpus
credible). EV shows only where publicly disclosed.
"""
from __future__ import annotations

import html as _html
from typing import Dict, Optional
from urllib.parse import quote

from ._chartis_kit import (
    P, chartis_shell, ck_editorial_head, ck_kpi_block, ck_page_actions,
)
from ..data_public.verified_deals import (
    SECTORS, disclosed_ev_count, disclosed_ev_total_mm, lead_sponsor_counts,
    outcome_counts, verified_deal_count, verified_deals,
)

_SECTOR_LABEL = {
    "hospitals": "Hospitals", "physician_practices": "Physician practices",
    "behavioral_health": "Behavioral health", "home_health_hospice": "Home health & hospice",
    "dental": "Dental / DSO", "dermatology": "Dermatology", "ophthalmology": "Ophthalmology",
    "asc": "ASC", "urgent_care": "Urgent care", "rcm_healthtech": "RCM / health-IT",
    "dialysis": "Dialysis", "other_services": "Other services",
}
_OUTCOME_TONE = {
    "active": P.get("positive", "#0a8a5f"), "exited": P.get("accent", "#155752"),
    "bankrupt": P.get("negative", "#b5321e"), "distressed": P.get("warning", "#b8732a"),
    "unknown": P.get("text_faint", "#7a8699"),
}


def _ev(d: Dict) -> str:
    ev = d.get("ev_usd_mm")
    if ev is None:
        return '<span style="color:%s">undisclosed</span>' % P.get("text_faint", "#7a8699")
    if ev >= 1000:
        return f"${ev / 1000:.1f}B"
    return f"${ev:,.0f}M"


def render_verified_deals(params: Optional[Dict] = None) -> str:
    params = params or {}
    sector = ""
    raw = params.get("sector", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    sector = str(raw).strip().lower()
    if sector not in SECTORS:
        sector = ""

    sponsor = ""
    raw_sp = params.get("sponsor", "")
    if isinstance(raw_sp, list):
        raw_sp = raw_sp[0] if raw_sp else ""
    sponsor = str(raw_sp).strip()[:80]

    deals = verified_deals(sector or None, sponsor or None)
    # Sort: disclosed EV first (desc), then by year desc.
    deals = sorted(
        deals,
        key=lambda d: (d.get("ev_usd_mm") is not None, d.get("ev_usd_mm") or 0,
                       d.get("year") or 0),
        reverse=True,
    )
    total = verified_deal_count()
    oc = outcome_counts()
    n_bankrupt = oc.get("bankrupt", 0)
    n_failures = n_bankrupt + oc.get("distressed", 0)
    n_sectors = len({d["sector"] for d in verified_deals()})
    ev_total_mm = disclosed_ev_total_mm()
    ev_total = (f"${ev_total_mm / 1000:.1f}B" if ev_total_mm >= 1000
                else f"${ev_total_mm:,.0f}M")

    border = P["border"]; tp = P["text"]; td = P["text_dim"]; fa = P.get("text_faint", td)
    ac = P["accent"]

    head = ck_editorial_head(
        eyebrow="REAL · SOURCED",
        title="Verified Deals",
        meta=f"{total} REAL DEALS · {ev_total} DISCLOSED EV · {n_failures} PUBLIC-RECORD FAILURES · EVERY ROW SOURCED",
        lede_italic_phrase="Real deals, every one source-linked.",
        lede_body=(
            "A hand-curated set of genuine US healthcare-services PE / M&A deals "
            "— the honest counterweight to the illustrative seed corpus. Every "
            "row carries a real source (SEC filing, press release, or named "
            "trade/financial coverage); enterprise value is shown only where it "
            "was publicly disclosed (never guessed). Includes the public-record "
            "outcomes — Steward, Envision, Prospect, Cano — that make a corpus "
            "credible. This list grows as we verify more."
        ),
    )

    kpis = (
        '<div class="ck-kpi-grid" style="margin-bottom:18px">'
        + ck_kpi_block("Verified deals", str(total), "real + sourced")
        + ck_kpi_block("Disclosed EV", ev_total, f"across {disclosed_ev_count()} deals")
        + ck_kpi_block("Failures", str(n_failures),
                       f"{n_bankrupt} bankrupt + {oc.get('distressed', 0)} distressed")
        + ck_kpi_block("Sectors", str(n_sectors), "services verticals")
        + '</div>'
    )

    # Outcome mix + sponsor leaderboard — the analytical read on the real set.
    # Bars are inline-styled (no chart-kit asset dependency) so the page stays
    # self-contained. Outcome bars use the same tone map as the table badges.
    def _bar_row(label: str, n: int, denom: int, tone: str, sub: str = "") -> str:
        pct = (n / denom * 100.0) if denom else 0.0
        sub_html = (f'<span style="color:{fa};font-size:9.5px;margin-left:6px">{_html.escape(sub)}</span>'
                    if sub else "")
        return (
            '<div style="display:grid;grid-template-columns:118px 1fr 30px;'
            'align-items:center;gap:9px;margin:5px 0">'
            f'<div style="font-size:11px;color:{tp};text-align:right">{_html.escape(label)}{sub_html}</div>'
            f'<div style="height:13px;background:{P["panel_alt"]};border-radius:2px;overflow:hidden">'
            f'<div style="height:100%;width:{pct:.1f}%;background:{tone};border-radius:2px"></div></div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:{tp};'
            f'text-align:right;font-variant-numeric:tabular-nums">{n}</div>'
            '</div>'
        )

    _OUTCOME_LABEL = {"bankrupt": "Bankrupt", "distressed": "Distressed",
                      "active": "Active", "exited": "Exited", "unknown": "Unknown"}
    om = outcome_counts()
    om_max = max(om.values()) if om else 1
    outcome_bars = "".join(
        _bar_row(_OUTCOME_LABEL.get(k, k), v, om_max, _OUTCOME_TONE.get(k, td))
        for k, v in om.items())
    outcome_panel = (
        f'<div style="border:1px solid {border};border-radius:3px;padding:14px 16px;background:{P["panel"]}">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.06em;'
        f'text-transform:uppercase;color:{td};margin-bottom:10px">Outcome mix</div>'
        + outcome_bars
        + f'<p style="font-size:10.5px;color:{fa};margin:9px 0 0;line-height:1.5">'
        f'{n_failures} of {total} are public-record failures (bankrupt or distressed). '
        'A real track record contains losses — that mix is the point, not a curve '
        'of invented winners.</p>'
        '</div>'
    )

    lsc = list(lead_sponsor_counts().items())[:8]
    ls_max = max((v for _, v in lsc), default=1)
    _sp_active = sponsor.strip().lower()
    sponsor_bars = ""
    for k, v in lsc:
        is_active = bool(_sp_active) and _sp_active in k.lower()
        tone = P.get("positive", ac) if is_active else ac
        q = "sponsor=" + quote(k)
        if sector:
            q = "sector=" + quote(sector) + "&" + q
        href = _html.escape("/verified-deals?" + q, quote=True)
        sponsor_bars += (
            f'<a href="{href}" title="Filter to {_html.escape(k, quote=True)}" '
            f'style="text-decoration:none;display:block">{_bar_row(k, v, ls_max, tone)}</a>'
        )
    sponsor_panel = (
        f'<div style="border:1px solid {border};border-radius:3px;padding:14px 16px;background:{P["panel"]}">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.06em;'
        f'text-transform:uppercase;color:{td};margin-bottom:10px">Most-seen sponsors</div>'
        + sponsor_bars
        + f'<p style="font-size:10.5px;color:{fa};margin:9px 0 0;line-height:1.5">'
        'Lead sponsor per deal (co-sponsors collapsed). <b>Click a sponsor</b> to '
        'filter the table to their real, sourced deals.</p>'
        '</div>'
    )
    analytics = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));'
        'gap:16px;margin-bottom:18px">'
        + outcome_panel + sponsor_panel + '</div>'
    )

    # Sector filter chips.
    def _chip(val: str, label: str) -> str:
        active = (val == sector) or (val == "" and not sector)
        style = (f"background:{ac};color:#fff;border-color:{ac};" if active
                 else f"color:{td};")
        href = "/verified-deals" + (f"?sector={val}" if val else "")
        return (f'<a href="{href}" style="display:inline-block;padding:4px 11px;'
                f'font-family:JetBrains Mono,monospace;font-size:10.5px;'
                f'border:1px solid {border};border-radius:3px;text-decoration:none;'
                f'{style}">{_html.escape(label)}</a>')
    present = sorted({d["sector"] for d in verified_deals()})
    chips = _chip("", "All") + "".join(
        _chip(s, _SECTOR_LABEL.get(s, s)) for s in present)
    # Filter-aware CSV export of the real, sourced set.
    _csv_q = [kv for kv in [
        ("sector=" + quote(sector)) if sector else "",
        ("sponsor=" + quote(sponsor)) if sponsor else "",
    ] if kv]
    csv_href = _html.escape(
        "/verified-deals.csv" + ("?" + "&".join(_csv_q) if _csv_q else ""),
        quote=True)
    csv_link = (
        f'<a href="{csv_href}" style="font-family:JetBrains Mono,monospace;'
        f'font-size:10.5px;color:{ac};text-decoration:none;border:1px solid '
        f'{border};border-radius:3px;padding:4px 10px;">↓ Download CSV</a>')
    chip_bar = (
        '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;'
        f'margin-bottom:16px">{chips}'
        f'<span style="margin-left:auto">{csv_link}</span></div>')

    th = (f'padding:7px 10px;border-bottom:2px solid {border};font-size:10px;'
          f'color:{td};text-transform:uppercase;letter-spacing:0.06em;'
          f'font-family:JetBrains Mono,monospace;text-align:left')
    rows = ""
    for i, d in enumerate(deals):
        bg = P["panel_alt"] if i % 2 else P["panel"]
        oc = _OUTCOME_TONE.get(d["outcome"], td)
        td_s = f'padding:6px 10px;font-size:12px;color:{tp};background:{bg}'
        num_s = (f'padding:6px 10px;font-size:12px;background:{bg};text-align:right;'
                 f'font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums')
        src_title, src_url = d["sources"] if isinstance(d.get("sources"), tuple) else (
            (d.get("source_note", "source"), d.get("source_url", "")))
        rows += (
            '<tr>'
            f'<td style="{td_s};font-weight:600">{_html.escape(d["target"])}'
            f'<div style="font-size:10px;color:{fa};font-weight:400">{_html.escape(d.get("subsector_note",""))}</div></td>'
            f'<td style="{td_s}">{_html.escape(d["sponsor"])}</td>'
            f'<td style="{num_s};color:{tp}">{d["year"]}</td>'
            f'<td style="{num_s};color:{tp}">{_ev(d)}</td>'
            f'<td style="{td_s};color:{td}">{_html.escape(_SECTOR_LABEL.get(d["sector"], d["sector"]))}</td>'
            f'<td style="{td_s}"><span style="font-family:JetBrains Mono,monospace;'
            f'font-size:9.5px;text-transform:uppercase;letter-spacing:.04em;color:{oc};'
            f'border:1px solid {oc};border-radius:2px;padding:1px 7px">{_html.escape(d["outcome"])}</span>'
            + (f'<div style="font-size:10px;color:{fa};margin-top:3px">{_html.escape(d.get("outcome_note",""))}</div>' if d.get("outcome_note") else "")
            + '</td>'
            f'<td style="{td_s}"><a href="{_html.escape(d.get("source_url",""), quote=True)}" '
            f'target="_blank" rel="noopener" style="color:{ac};text-decoration:none;font-size:11px">'
            f'{_html.escape(d.get("source_note","source"))} ↗</a></td>'
            '</tr>'
        )
    # Active-filter indicator (sector and/or sponsor) with a clear affordance.
    if sector or sponsor:
        active_label = " · ".join(x for x in [
            (_SECTOR_LABEL.get(sector, sector) if sector else ""),
            (f"sponsor: {_html.escape(sponsor)}" if sponsor else ""),
        ] if x)
        filter_note = (
            f'<div style="margin-bottom:12px;font-size:11px;color:{td}">'
            f'Showing <b>{len(deals)}</b> of {total} — {active_label} '
            f'<a href="/verified-deals" style="color:{ac};text-decoration:none">'
            '&times; clear</a></div>'
        )
    else:
        filter_note = ""

    if not rows:
        table = (
            f'<div style="border:1px solid {border};border-radius:3px;'
            f'padding:24px 16px;text-align:center;color:{fa};font-size:12px">'
            'No verified deals match this filter yet — the set grows as we source '
            f'more. See all <a href="/verified-deals" style="color:{ac};'
            f'text-decoration:none">{total} deals</a>.</div>'
        )
    else:
        table = (
            f'<div style="overflow-x:auto;border:1px solid {border};border-radius:3px">'
            '<table style="width:100%;border-collapse:collapse">'
            f'<thead><tr><th style="{th}">Target</th><th style="{th}">Sponsor</th>'
            f'<th style="{th};text-align:right">Year</th><th style="{th};text-align:right">EV</th>'
            f'<th style="{th}">Sector</th><th style="{th}">Outcome</th>'
            f'<th style="{th}">Source</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
        )

    body = (
        '<div class="ck-page-wrap">'
        + head + kpis + analytics + chip_bar + filter_note + table
        + f'<p style="font-size:10px;color:{fa};margin-top:12px">'
        'Curated from public coverage; EV null where undisclosed. This is the '
        'foundation that replaces the synthetic seed corpus across the deal '
        'surfaces as it grows toward full coverage.</p>'
        + '</div>'
    )
    body = body + ck_page_actions()
    return chartis_shell(body, "Verified Deals", active_nav="/verified-deals")
