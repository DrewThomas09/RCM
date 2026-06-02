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

from ._chartis_kit import (
    P, chartis_shell, ck_editorial_head, ck_kpi_block, ck_page_actions,
)
from ..data_public.verified_deals import (
    SECTORS, disclosed_ev_count, verified_deal_count, verified_deals,
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

    deals = verified_deals(sector or None)
    # Sort: disclosed EV first (desc), then by year desc.
    deals = sorted(
        deals,
        key=lambda d: (d.get("ev_usd_mm") is not None, d.get("ev_usd_mm") or 0,
                       d.get("year") or 0),
        reverse=True,
    )
    total = verified_deal_count()
    n_bankrupt = sum(1 for d in verified_deals() if d["outcome"] == "bankrupt")
    n_sectors = len({d["sector"] for d in verified_deals()})

    border = P["border"]; tp = P["text"]; td = P["text_dim"]; fa = P.get("text_faint", td)
    ac = P["accent"]

    head = ck_editorial_head(
        eyebrow="REAL · SOURCED",
        title="Verified Deals",
        meta=f"{total} REAL DEALS · {disclosed_ev_count()} WITH DISCLOSED EV · EVERY ROW SOURCED",
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
        + ck_kpi_block("Disclosed EV", str(disclosed_ev_count()), f"of {total}")
        + ck_kpi_block("Bankruptcies", str(n_bankrupt), "public-record outcomes")
        + ck_kpi_block("Sectors", str(n_sectors), "services verticals")
        + '</div>'
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
    chip_bar = f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px">{chips}</div>'

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
        + head + kpis + chip_bar + table
        + f'<p style="font-size:10px;color:{fa};margin-top:12px">'
        'Curated from public coverage; EV null where undisclosed. This is the '
        'foundation that replaces the synthetic seed corpus across the deal '
        'surfaces as it grows toward full coverage.</p>'
        + '</div>'
    )
    body = body + ck_page_actions()
    return chartis_shell(body, "Verified Deals", active_nav="/verified-deals")
