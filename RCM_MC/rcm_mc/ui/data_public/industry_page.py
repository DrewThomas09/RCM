"""PEdesk Industry Intelligence pages — /industry and /industry/<slug>.

Renders the licensed-IBISWorld-derived industry intelligence (loaded from
``rcm_mc.data.industry_intel``) as PEdesk editorial dossiers, with explicit
LICENSED-REPORT-DERIVED provenance and a "Public Data Connections" section that
links the industry context to PEdesk's real CMS/HCRIS/provider surfaces.

Honesty: report-derived context is industry-level, not provider-specific, and
forecasts are report-derived (not PEdesk predictions). Every surface shows the
source attribution + data-source boundary labels. No verbatim narrative.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_page_title, ck_source_purpose,
)
from rcm_mc.data import industry_intel as _ii

# Per-industry public-data connections: (label, route, data_source_tag).
_CONNECTIONS: Dict[str, List] = {
    "hospitals": [
        ("HCRIS X-Ray — cost-report margins & structure", "/diligence/hcris-xray", "HCRIS PUBLIC DATA"),
        ("Hospital anchor / vertical profile", "/hospital-anchor", "CMS PUBLIC DATA"),
        ("Reference-based pricing (CO)", "/ref-pricing", "STATE APCD / CIVHC DATA"),
        ("Cost structure", "/cost-structure", "HCRIS PUBLIC DATA"),
        ("Payer stress test", "/payer-stress", "STATE APCD / CIVHC DATA"),
        ("Geographic market intel (demand × supply × consolidation)", "/market-intel/geo", "LICENSED MARKET DATA DERIVED"),
    ],
    "primary-care-doctors": [
        ("Physician productivity (MIPS + HRSA anchored)", "/physician-productivity", "CMS PUBLIC DATA"),
        ("CMS APM / MSSP ACO participation", "/cms-apm", "CMS PUBLIC DATA"),
        ("Quality scorecard (MIPS benchmark)", "/quality-scorecard", "CMS PUBLIC DATA"),
        ("Provider retention (CMS turnover context)", "/provider-retention", "CMS PUBLIC DATA"),
        ("Geographic market intel (demand × supply)", "/market-intel/geo", "LICENSED MARKET DATA DERIVED"),
    ],
    "specialist-doctors": [
        ("Physician productivity (MIPS + HRSA)", "/physician-productivity", "CMS PUBLIC DATA"),
        ("Clinical outcomes (CMS quality-measure)", "/clinical-outcomes", "CMS PUBLIC DATA"),
        ("CMS APM / specialty programs", "/cms-apm", "CMS PUBLIC DATA"),
        ("Geographic market intel (demand × supply)", "/market-intel/geo", "LICENSED MARKET DATA DERIVED"),
    ],
    "outpatient-care-centers": [
        ("Dialysis vertical (CMS Care Compare)", "/dialysis", "CMS PUBLIC DATA"),
        ("Home health / hospice verticals", "/home-health", "CMS PUBLIC DATA"),
        ("Supply chain (FDA drug shortage)", "/supply-chain", "CMS PUBLIC DATA"),
        ("Reference-based pricing (CO)", "/ref-pricing", "STATE APCD / CIVHC DATA"),
        ("Geographic market intel (demand × supply)", "/market-intel/geo", "LICENSED MARKET DATA DERIVED"),
    ],
    "healthcare-social-assistance": [
        ("All sector verticals", "/verticals", "CMS PUBLIC DATA"),
        ("CMS data browser", "/cms-data-browser", "CMS PUBLIC DATA"),
        ("Geographic market intel (demand/supply/consolidation)", "/market-intel/geo", "LICENSED MARKET DATA DERIVED"),
        ("Deal corpus analytics", "/deal-corpus-analytics", "USER DEAL DATA"),
        ("Regulatory calendar", "/regulatory-calendar", "CMS PUBLIC DATA"),
    ],
}

_LICENSE_CHIP = (
    f'<span style="display:inline-block;background:{P["navy"] if "navy" in P else P["accent"]};'
    f'color:#fff;font-size:9px;font-weight:700;letter-spacing:0.08em;padding:2px 8px;'
    f'border-radius:3px;text-transform:uppercase">Licensed report derived</span>'
)


def _tag_chip(tag: str) -> str:
    return (f'<span style="display:inline-block;background:{P["panel_alt"]};'
            f'color:{P["text_dim"]};font-size:9px;font-weight:600;letter-spacing:0.05em;'
            f'border:1px solid {P["border"]};padding:1px 6px;border-radius:3px;'
            f'text-transform:uppercase">{_html.escape(tag)}</span>')


def _fmt_metric(row: dict) -> str:
    unit = row.get("unit", "")
    try:
        v = float(row["value"])
    except (ValueError, KeyError, TypeError):
        return _html.escape(str(row.get("value", "—")))
    if unit == "$M":
        return f"${v/1000:,.1f}bn" if v >= 1000 else f"${v:,.0f}M"
    if unit == "%":
        return f"{v:.1f}%"
    if unit == "units":
        return f"{v:,.0f}"
    return f"{v:,.1f}"


def render_industry_index(params: dict = None) -> str:
    reports = _ii.load_industry_reports()
    rows = ""
    for r in sorted(reports, key=lambda x: x.get("naics_code", "")):
        conns = len(_CONNECTIONS.get(r["slug"], []))
        rows += (
            f'<tr style="border-bottom:1px solid {P["border"]}">'
            f'<td style="padding:10px 12px"><a href="/industry/{_html.escape(r["slug"])}" '
            f'style="color:{P["accent"]};font-weight:600;text-decoration:none">'
            f'{_html.escape(r["title"])}</a></td>'
            f'<td style="padding:10px 12px;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["text_dim"]}">{_html.escape(str(r.get("naics_code","")))}</td>'
            f'<td style="padding:10px 12px;font-size:11px;color:{P["text_dim"]}">{_html.escape(r.get("publication_date",""))}</td>'
            f'<td style="padding:10px 12px;font-size:11px;color:{P["text_dim"]}">{conns} public-data links</td>'
            f'</tr>')
    table = (
        f'<table style="width:100%;border-collapse:collapse;background:{P["panel"]};'
        f'border:1px solid {P["border"]}"><thead>'
        f'<tr style="border-bottom:2px solid {P["border"]};text-align:left;color:{P["text_dim"]};font-size:11px;text-transform:uppercase">'
        f'<th style="padding:10px 12px">Industry</th><th style="padding:10px 12px">NAICS</th>'
        f'<th style="padding:10px 12px">Report</th><th style="padding:10px 12px">PEdesk links</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>')

    body = (
        ck_page_title("Industry Intelligence", eyebrow="INDUSTRY",
                      meta=f"{len(reports)} licensed industry reports · derived structured intelligence")
        + ck_source_purpose(
            purpose="Ground a deal's sector thesis in licensed industry "
                    "intelligence, then validate it against PEdesk's real "
                    "CMS/HCRIS/provider data.",
            universe="licensed-report-derived", confidence="derived",
            source="Licensed IBISWorld industry reports (structured extraction, "
                   "non-verbatim) — industry-level, not provider-specific",
            next_action="Open an industry to see metrics, drivers, and public-data connections")
        + f'<p style="margin:6px 0 16px">{_LICENSE_CHIP}</p>'
        + table)
    return chartis_shell(body, "Industry Intelligence", active_nav="/industry",
                         editorial_intro={
                             "eyebrow": "INDUSTRY INTELLIGENCE",
                             "headline": "Where the licensed industry view meets real public data.",
                             "italic_word": "meets",
                             "body": "Licensed IBISWorld-derived structured intelligence for "
                                     "five healthcare industries, connected to PEdesk's CMS/HCRIS "
                                     "surfaces so you can confirm or challenge the thesis with real data."})


def render_industry(slug: str, params: dict = None) -> str:
    r = _ii.report_by_slug(slug)
    if not r:
        body = ck_page_title("Industry not found", eyebrow="INDUSTRY") + \
            f'<p style="color:{P["text_dim"]}">No industry report for "{_html.escape(str(slug))}". ' \
            f'<a href="/industry" style="color:{P["accent"]}">Back to Industry Intelligence</a>.</p>'
        return chartis_shell(body, "Industry", active_nav="/industry")

    iid = r["industry_id"]
    attribution = f'{_ii.ATTRIBUTION}, {r["report_title"]}, {r.get("publication_date","")}.'
    cell = f"background:{P['panel']};border:1px solid {P['border']};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{P['text_dim']};text-transform:uppercase;margin-bottom:10px"

    # At-a-glance KPIs
    metrics = _ii.load_industry_metrics(iid)
    kpis = ""
    seen = set()
    for mname in ("Revenue", "Profit Margin", "Employment", "Establishments", "Wages", "Enterprises"):
        row = next((x for x in metrics if x["metric_name"] == mname and mname not in seen), None)
        if row:
            seen.add(mname)
            period = row.get("period", "")
            kpis += ck_kpi_block(mname, _fmt_metric(row), period or "", "")
    kpi_block = f'<div class="ck-kpi-grid" style="margin-bottom:16px">{kpis}</div>' if kpis else ""

    # Segments
    segs = _ii.load_industry_segments(iid)
    seg_rows = "".join(
        f'<tr><td style="padding:4px 10px">{_html.escape(s["segment_name"])}</td>'
        f'<td style="padding:4px 10px;text-align:right;font-variant-numeric:tabular-nums">{_fmt_metric({"value":s.get("revenue"),"unit":"$M"})}</td>'
        f'<td style="padding:4px 10px;text-align:right;font-variant-numeric:tabular-nums">{_html.escape(str(s.get("share","")))}%</td></tr>'
        for s in segs)
    seg_panel = (f'<div style="{cell}"><div style="{h3}">Products & Services mix</div>'
                 f'<table style="width:100%;border-collapse:collapse;font-size:12px">'
                 f'<thead><tr style="color:{P["text_dim"]};text-align:left;border-bottom:1px solid {P["border"]}">'
                 f'<th style="padding:4px 10px">Segment</th><th style="padding:4px 10px;text-align:right">Revenue</th>'
                 f'<th style="padding:4px 10px;text-align:right">Share</th></tr></thead>'
                 f'<tbody>{seg_rows}</tbody></table></div>') if segs else ""

    # Drivers
    drivers = _ii.load_industry_drivers(iid)
    drv_rows = "".join(
        f'<li style="margin-bottom:4px"><b>{_html.escape(d["driver"])}</b> '
        f'<span style="color:{P["text_dim"]}">· {_html.escape(d.get("direction",""))}</span></li>'
        for d in drivers)
    drv_panel = (f'<div style="{cell}"><div style="{h3}">Key external drivers</div>'
                 f'<ul style="margin:0;padding-left:18px;font-size:12px">{drv_rows}</ul></div>') if drivers else ""

    # Benchmarks (cost structure)
    bms = _ii.load_industry_benchmarks(iid)
    bm_rows = "".join(
        f'<tr><td style="padding:4px 10px">{_html.escape(b["benchmark_name"])}</td>'
        f'<td style="padding:4px 10px;text-align:right;font-variant-numeric:tabular-nums">{_html.escape(str(b.get("value","")))}%</td>'
        f'<td style="padding:4px 10px;text-align:right;font-variant-numeric:tabular-nums;color:{P["text_dim"]}">{_html.escape(str(b.get("sector_value","") or "—"))}</td></tr>'
        for b in bms)
    bm_panel = (f'<div style="{cell}"><div style="{h3}">Financial benchmarks — cost structure (% of revenue)</div>'
                f'<table style="width:100%;border-collapse:collapse;font-size:12px">'
                f'<thead><tr style="color:{P["text_dim"]};text-align:left;border-bottom:1px solid {P["border"]}">'
                f'<th style="padding:4px 10px">Item</th><th style="padding:4px 10px;text-align:right">Industry</th>'
                f'<th style="padding:4px 10px;text-align:right">Sector</th></tr></thead>'
                f'<tbody>{bm_rows}</tbody></table></div>') if bms else ""

    # Definition / included services
    inc = r.get("included_services", [])
    inc_html = "".join(f'<li>{_html.escape(x)}</li>' for x in inc)
    def_panel = (f'<div style="{cell}"><div style="{h3}">Definition · NAICS {_html.escape(str(r.get("naics_code","")))}</div>'
                 f'<p style="font-size:12px;color:{P["text"]};margin:0 0 8px">{_html.escape(r.get("summary_nonverbatim",""))}</p>'
                 + (f'<div style="{h3}">Included</div><ul style="margin:0;padding-left:18px;font-size:12px">{inc_html}</ul>' if inc else "")
                 + '</div>')

    # Public data connections — the PEdesk value-add
    conns = _CONNECTIONS.get(slug, [])
    conn_rows = "".join(
        f'<li style="margin-bottom:6px">{_tag_chip(tag)} '
        f'<a href="{href}" style="color:{P["accent"]};text-decoration:none">{_html.escape(label)}</a></li>'
        for label, href, tag in conns)
    conn_panel = (f'<div style="{cell};border-left:3px solid {P["accent"]}">'
                  f'<div style="{h3}">Public data connections — validate this thesis with real data</div>'
                  f'<ul style="margin:0;padding-left:18px;font-size:12px;line-height:1.8">{conn_rows}</ul>'
                  f'<p style="font-size:11px;color:{P["text_dim"]};margin:8px 0 0">'
                  f'Industry context is <b>report-derived</b>; these PEdesk surfaces add '
                  f'<b>real CMS/HCRIS/provider</b> data to confirm or challenge it.</p></div>') if conns else ""

    # Diligence questions
    qs = _ii.load_industry_questions(iid)
    q_rows = "".join(f'<li style="margin-bottom:4px">{_html.escape(q["question"])}</li>' for q in qs)
    q_panel = (f'<div style="{cell}"><div style="{h3}">Diligence questions (PEdesk)</div>'
               f'<ul style="margin:0;padding-left:18px;font-size:12px;line-height:1.7">{q_rows}</ul></div>') if qs else ""

    body = (
        ck_page_title(r["title"], eyebrow="INDUSTRY",
                      meta=f'NAICS {r.get("naics_code","")} · {r.get("report_title","")} · {r.get("publication_date","")}')
        + ck_source_purpose(
            purpose="Frame this industry for diligence: market size, mix, drivers, "
                    "cost structure — then validate against real public data.",
            universe="licensed-report-derived", confidence="derived",
            source=attribution + " Non-verbatim PEdesk analysis; industry-level, "
                   "not provider-specific; forecasts are report-derived.",
            next_action="Use the Public Data Connections to confirm with CMS/HCRIS")
        + f'<p style="margin:6px 0 16px">{_LICENSE_CHIP} '
        + f'<a href="/industry/{_html.escape(slug)}/brief" style="margin-left:10px;'
        + f'color:{P["accent"]};font-size:12px;font-weight:600;text-decoration:none">'
        + f'Generate PEdesk brief &rarr;</a></p>'
        + kpi_block + def_panel + seg_panel + drv_panel + bm_panel + conn_panel + q_panel)
    return chartis_shell(body, r["title"], active_nav="/industry")


# ── PEdesk industry brief builder — /industry/<slug>/brief ──────────────────
# Composes PEdesk's OWN industry brief (non-verbatim analysis) by combining the
# licensed-report-derived structured facts with PEdesk's real public-data
# connections. NOT a copy of the report.
def render_industry_brief(slug: str, params: dict = None) -> str:
    r = _ii.report_by_slug(slug)
    if not r:
        body = ck_page_title("Brief not found", eyebrow="INDUSTRY BRIEF") + \
            f'<p style="color:{P["text_dim"]}">No industry report for "{_html.escape(str(slug))}". ' \
            f'<a href="/industry" style="color:{P["accent"]}">Industry Intelligence</a>.</p>'
        return chartis_shell(body, "Industry Brief", active_nav="/industry")

    iid = r["industry_id"]
    metrics = _ii.load_industry_metrics(iid)
    segs = _ii.load_industry_segments(iid)
    drivers = _ii.load_industry_drivers(iid)
    bms = _ii.load_industry_benchmarks(iid)
    qs = _ii.load_industry_questions(iid)
    conns = _CONNECTIONS.get(slug, [])
    attribution = f'{_ii.ATTRIBUTION}, {r["report_title"]}, {r.get("publication_date","")}.'

    sec = f"margin:0 0 18px"
    h = f"font-size:12px;font-weight:700;letter-spacing:0.06em;color:{P['text']};text-transform:uppercase;margin:18px 0 6px;border-bottom:1px solid {P['border']};padding-bottom:4px"
    dim = f"font-size:12px;color:{P['text_dim']};line-height:1.6;margin:0 0 8px"

    def _m(name):
        row = next((x for x in metrics if x["metric_name"] == name), None)
        return _fmt_metric(row) if row else "—"

    largest_cost = max(bms, key=lambda b: float(b.get("value") or 0), default=None)
    top_seg = max(segs, key=lambda s: float(s.get("share") or 0), default=None)

    parts = [f'<div style="{h}">1 · Industry snapshot</div>',
             f'<p style="{dim}">Market revenue {_m("Revenue")} at a {_m("Profit Margin")} profit margin, '
             f'with {_m("Employment")} employees across {_m("Establishments")} establishments '
             f'(period per report). Figures are licensed-report-derived industry aggregates.</p>']

    parts.append(f'<div style="{h}">2 · Market structure</div>')
    parts.append(f'<p style="{dim}">{_html.escape(r.get("summary_nonverbatim","")[:300])} '
                 f'Players: {_html.escape(", ".join(r.get("major_players", [])) or "see report")}.</p>')

    if top_seg:
        parts.append(f'<div style="{h}">3 · Demand & segment mix</div>')
        parts.append(f'<p style="{dim}">Largest segment: <b>{_html.escape(top_seg["segment_name"])}</b> '
                     f'(~{_html.escape(str(top_seg.get("share","")))}% of revenue). '
                     f'{len(segs)} segments extracted.</p>')

    if drivers:
        dl = "".join(f'<li>{_html.escape(d["driver"])} · <span style="color:{P["text_dim"]}">{_html.escape(d.get("direction",""))}</span></li>'
                     for d in drivers[:6])
        parts.append(f'<div style="{h}">4 · Demand drivers & reimbursement pressure</div>')
        parts.append(f'<ul style="{dim};padding-left:18px">{dl}</ul>')

    if bms:
        parts.append(f'<div style="{h}">5 · Financial benchmark view</div>')
        lc = f'{_html.escape(largest_cost["benchmark_name"])} at {largest_cost.get("value")}% of revenue' if largest_cost else "see report"
        parts.append(f'<p style="{dim}">Cost structure (industry, % of revenue): largest line is {lc}. '
                     f'Profit margin {_m("Profit Margin")}. Benchmarks are industry vs sector.</p>')

    if conns:
        cl = "".join(f'<li>{_tag_chip(tag)} <a href="{href}" style="color:{P["accent"]};text-decoration:none">{_html.escape(label)}</a></li>'
                     for label, href, tag in conns)
        parts.append(f'<div style="{h}">6 · CMS / HCRIS validation layer (PEdesk value-add)</div>')
        parts.append(f'<p style="{dim}">Confirm or challenge the report with real public/provider data:</p>')
        parts.append(f'<ul style="{dim};padding-left:18px;line-height:1.9">{cl}</ul>')

    if qs:
        ql = "".join(f'<li>{_html.escape(q["question"])}</li>' for q in qs)
        parts.append(f'<div style="{h}">7 · Diligence questions</div>')
        parts.append(f'<ul style="{dim};padding-left:18px;line-height:1.7">{ql}</ul>')

    parts.append(f'<div style="{h}">8 · Data gaps</div>')
    parts.append(f'<p style="{dim}">Report-derived figures are industry-level. Deal-specific evidence '
                 f'requires the target\'s own financials and the linked CMS/HCRIS/provider data above. '
                 f'Forecasts are report-derived, not PEdesk predictions.</p>')

    parts.append(f'<div style="{h}">9 · Sources</div>')
    parts.append(f'<p style="{dim}">{_html.escape(attribution)} PEdesk public data: CMS / HCRIS / '
                 f'CIVHC / FDA where linked. PEdesk analysis is non-verbatim.</p>')

    body = (
        ck_page_title(f'{r["title"]} — PEdesk Brief', eyebrow="INDUSTRY BRIEF",
                      meta=f'NAICS {r.get("naics_code","")} · {r.get("publication_date","")} · '
                           f'<a href="/industry/{_html.escape(slug)}" style="color:inherit">full dossier</a>')
        + ck_source_purpose(
            purpose="A PEdesk-generated industry brief: licensed industry "
                    "intelligence synthesized with real public-data validation.",
            universe="licensed-report-derived", confidence="derived",
            source=attribution + " Non-verbatim PEdesk synthesis; industry-level, not provider-specific.",
            next_action="Use the CMS/HCRIS validation layer to ground the thesis")
        + f'<p style="margin:6px 0 16px">{_LICENSE_CHIP}</p>'
        + f'<div style="{sec}">{"".join(parts)}</div>')
    return chartis_shell(body, f'{r["title"]} Brief', active_nav="/industry")
