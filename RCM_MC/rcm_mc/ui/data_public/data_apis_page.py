"""Public-data API catalog page — /data-apis.

Renders the reference table from ``public_api_catalog`` as a client-ready
surface: a KPI strip, a professional CDD chart of API coverage by diligence
question, and per-category source tables with auth / rate-limit / status badges
and links to docs. Metadata only — nothing here fetches at render time.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ...data_public import public_api_catalog as cat


_ACCESS_TONE = {
    "none": ("#0a8a5f", "#e7f3ee"),         # green — no key
    "key-optional": ("#0a8a5f", "#e7f3ee"),
    "key-required": ("#b8732a", "#f6ede2"),  # amber — free key
    "registration": ("#b8732a", "#f6ede2"),
}
_STATUS_TONE = {
    "live-client": ("#0a8a5f", "#e7f3ee"),
    "vendored": ("#155752", "#e6efed"),
    "registered": ("#7a8699", "#eef0f3"),
}


def _badge(text: str, tone: tuple) -> str:
    fg, bg = tone
    return (f'<span style="font-size:9.5px;font-weight:600;letter-spacing:.03em;'
            f'color:{fg};background:{bg};border-radius:10px;padding:2px 8px;'
            f'white-space:nowrap;">{_html.escape(text)}</span>')


def _coverage_chart() -> str:
    from ..cdd_chart_kit import render_cdd_chart
    rows = []
    for _cid, label, members in cat.by_category():
        # Short label so the axis stays readable.
        short = label.split(" & ")[0].split(", ")[0]
        rows.append((short, [len(members)]))
    table = {"headers": ["Diligence question", "APIs"], "rows": rows}
    opts = {
        "title": "Free public-data API coverage by diligence question",
        "subtitle": "Count of cataloged sources answering each CDD question",
        "palette": "Navy–Teal", "suffix": "", "show_values": True,
        "legend": False, "width_px": 920,
        "footnote": "Source: PEdesk public-data API catalog — free / "
                    "key-optional sources only.",
    }
    return render_cdd_chart("column", table, opts)


def _wiring_chart() -> str:
    """Grouped view of what's wired in-repo vs still registered, by question —
    the build roadmap for the data layer."""
    from ..cdd_chart_kit import render_cdd_chart
    rows = []
    for _cid, label, members in cat.by_category():
        short = label.split(" & ")[0].split(", ")[0]
        wired = sum(1 for s in members if s.is_wired)
        registered = sum(1 for s in members if not s.is_wired)
        rows.append((short, [wired, registered]))
    table = {"headers": ["Diligence question", "Available now", "Planned"],
             "rows": rows}
    opts = {
        "title": "Data layer: available now vs. planned",
        "subtitle": "Live client or vendored snapshot vs. cataloged-only",
        "palette": "Navy–Teal", "suffix": "", "show_values": True,
        "legend": True, "width_px": 920,
        "footnote": "Source: PEdesk public-data API catalog.",
    }
    return render_cdd_chart("column", table, opts)


def _source_row(s: cat.ApiSource) -> str:
    access_label = cat.ACCESS_LABELS.get(s.access, s.access)
    status_label = cat.STATUS_LABELS.get(s.status, s.status)
    badges = (_badge(access_label, _ACCESS_TONE.get(s.access, ("#7a8699", "#eef0f3")))
              + " "
              + _badge(status_label, _STATUS_TONE.get(s.status, ("#7a8699", "#eef0f3"))))
    if s.cost == "paywall-micro":
        badges += " " + _badge("microdata $", ("#b5321e", "#f6e7e3"))
    docs = (f'<a href="{_html.escape(s.docs_url)}" target="_blank" '
            f'rel="noopener" style="color:#155752;">docs ↗</a>')
    explore = ""
    if s.explore_route:
        explore = (f'<div style="margin-top:4px;"><a href="'
                   f'{_html.escape(s.explore_route)}" style="font-size:10px;'
                   f'font-weight:600;color:#fff;background:#0b2341;'
                   f'border-radius:10px;padding:2px 9px;text-decoration:none;'
                   f'white-space:nowrap;">Explore →</a></div>')
    records = (f'<div style="font-size:10px;color:#7a8699;">'
               f'{_html.escape(s.records)}</div>' if s.records else "")
    return (
        '<tr style="border-top:1px solid #e6e0d2;vertical-align:top;">'
        f'<td style="padding:9px 10px;">'
        f'<div style="font-weight:600;color:#1a2332;">{_html.escape(s.name)}</div>'
        f'<div style="font-size:10.5px;color:#7a8699;">{_html.escape(s.operator)}</div>'
        f'{records}</td>'
        f'<td style="padding:9px 10px;font-size:11.5px;color:#1a2332;">'
        f'{_html.escape(s.answers)}'
        f'<div style="font-size:10.5px;color:#56606f;margin-top:3px;">'
        f'{_html.escape(s.why)}</div></td>'
        f'<td style="padding:9px 10px;white-space:nowrap;">{badges}{explore}</td>'
        f'<td style="padding:9px 10px;font-size:10.5px;color:#56606f;">'
        f'{_html.escape(s.rate_limit)}'
        f'<div style="font-size:10px;color:#7a8699;margin-top:2px;">'
        f'{_html.escape(s.formats)}</div></td>'
        f'<td style="padding:9px 10px;font-size:10.5px;">{docs}'
        f'<div style="font-family:monospace;font-size:9.5px;color:#9aa0ac;'
        f'word-break:break-all;margin-top:2px;">{_html.escape(s.base_url)}</div>'
        f'</td></tr>')


# Diligence question -> the in-repo Further Analysis datasets that already
# answer it, so the catalog is a two-sided launchpad (external APIs + ready
# charts). Dataset ids are validated against the live registry at render time.
_READY_BY_QUESTION: Dict[str, List[str]] = {
    "provider_universe": ["provider_supply", "consolidation_state",
                          "consolidation_trend", "snf_owners",
                          "postacute_footprint", "oig_exclusions_state",
                          "oig_exclusions_type", "hrsa_shortage"],
    "volume_outcomes": ["hcahps", "mips", "mips_bands", "hcris_state",
                        "postacute_quality", "snf_rating_dist"],
    "drugs_devices": ["partd", "partd_inflation", "drug_shortages",
                      "open_payments", "clinical_trial_phase"],
    "financials": ["hcris_state", "hospital_pricing_power", "cost_of_care",
                   "multiples", "public_comps", "apm_adoption"],
    "demographics_labor": ["state_demographics", "county_demographics",
                           "metro_demographics", "cdc_places", "labor",
                           "ma_penetration", "ma_geo", "snf_turnover"],
    "behavioral_global": [],
}


def _ready_strip(cid: str) -> str:
    """Chips linking to the in-repo explorer charts that answer this question."""
    from ...diligence import further_analysis as fa
    ids = _READY_BY_QUESTION.get(cid, [])
    chips = ""
    for ds_id in ids:
        d = fa.DATASETS.get(ds_id)
        if d is None:
            continue
        chips += (
            f'<a href="/further-analysis?dataset={_html.escape(ds_id)}" '
            f'style="font-size:10.5px;color:#155752;background:#e6efed;'
            f'border:1px solid #cfe0dc;border-radius:12px;padding:2px 9px;'
            f'text-decoration:none;white-space:nowrap;">'
            f'{_html.escape(d.label)} →</a>')
    if not chips:
        return ""
    return (
        '<div style="margin:6px 0 2px;display:flex;flex-wrap:wrap;gap:6px;'
        'align-items:center;">'
        '<span style="font-size:9.5px;font-weight:600;letter-spacing:.05em;'
        'text-transform:uppercase;color:#7a8699;">Ready in-repo</span>'
        + chips + '</div>')


def _category_section(cid: str, label: str, members: List[cat.ApiSource]) -> str:
    rows = "".join(_source_row(s) for s in members)
    ready = _ready_strip(cid)
    head = (
        '<thead><tr style="text-align:left;font-size:10px;'
        'letter-spacing:.06em;text-transform:uppercase;color:#7a8699;">'
        '<th style="padding:6px 10px;">Source</th>'
        '<th style="padding:6px 10px;">Answers / why it matters</th>'
        '<th style="padding:6px 10px;">Access · status</th>'
        '<th style="padding:6px 10px;">Rate limit · format</th>'
        '<th style="padding:6px 10px;">Endpoint</th></tr></thead>')
    return (
        f'<section style="margin:22px 0;">'
        f'<h2 style="font-family:\'Source Serif 4\',serif;font-size:16px;'
        f'color:#0b2341;margin:0 0 4px;">{_html.escape(label)} '
        f'<span style="font-size:11px;color:#7a8699;font-weight:400;">'
        f'({len(members)})</span></h2>'
        f'{ready}'
        f'<table style="width:100%;border-collapse:collapse;'
        f'background:#fff;border:1px solid #e6e0d2;border-radius:8px;'
        f'overflow:hidden;">{head}<tbody>{rows}</tbody></table></section>')


def render_data_apis_page(qs: "Optional[Dict[str, Any]]" = None) -> str:
    from .._chartis_kit import (chartis_shell, ck_kpi_block, ck_page_title)

    summ = cat.summary()
    kpis = (
        '<div class="ck-kpi-row" style="display:flex;flex-wrap:wrap;gap:14px;">'
        + ck_kpi_block("Public APIs", f'<span class="mn">{summ["total"]}</span>',
                       "free / key-optional")
        + ck_kpi_block("Diligence questions",
                       f'<span class="mn">{summ["categories"]}</span>',
                       "coverage areas")
        + ck_kpi_block("Available now",
                       f'<span class="mn pos">{summ["wired"]}</span>',
                       "live client or vendored")
        + ck_kpi_block("No key needed",
                       f'<span class="mn">{summ["no_key"]}</span>',
                       "hit without registration")
        + '</div>')

    intro = (
        '<p style="font-size:12.5px;color:#56606f;max-width:880px;'
        'margin:6px 0 0;">The free, API-accessible public healthcare data worth '
        'using in diligence, organized by the question each source answers. '
        'Status is honest about what is available today: '
        '<b>live client</b> hits the API directly, <b>vendored offline</b> reads '
        'a committed build-time snapshot, <b>registered</b> is cataloged but not '
        'yet connected. NPPES is CMS-operated but listed here as the provider '
        'universe every build starts from.</p>')

    chart = (f'<div style="margin:16px 0;text-align:center;">'
             f'{_coverage_chart()}</div>'
             f'<div style="margin:16px 0;text-align:center;">'
             f'{_wiring_chart()}</div>')

    sections = "".join(
        _category_section(cid, label, members)
        for cid, label, members in cat.by_category())

    body = (
        ck_page_title("Public Data APIs",
                      eyebrow="Diligence data sources",
                      meta=f'{summ["total"]} free sources · '
                           f'{summ["no_key"]} key-optional')
        + kpis + intro + chart + sections)
    return chartis_shell(body, "Public Data APIs", active_nav="/research",
                         subtitle="Free public healthcare-data sources")


def build_data_apis(qs: "Optional[Dict[str, Any]]" = None) -> Dict[str, Any]:
    """JSON-API payload mirroring the catalog for programmatic discovery."""
    def _src(s: cat.ApiSource) -> Dict[str, Any]:
        return {
            "id": s.id, "name": s.name, "operator": s.operator,
            "category": s.category,
            "category_label": cat.category_label(s.category),
            "base_url": s.base_url, "docs_url": s.docs_url,
            "access": s.access, "access_label": cat.ACCESS_LABELS.get(s.access),
            "rate_limit": s.rate_limit, "formats": s.formats, "cost": s.cost,
            "status": s.status, "status_label": cat.STATUS_LABELS.get(s.status),
            "key_required": s.key_required, "is_wired": s.is_wired,
            "client_module": s.client_module or None,
            "explore_route": s.explore_route or None,
            "answers": s.answers, "why": s.why, "records": s.records or None,
        }
    return {
        "summary": cat.summary(),
        "categories": [
            {"id": cid, "label": label,
             "sources": [_src(s) for s in members]}
            for cid, label, members in cat.by_category()
        ],
    }
