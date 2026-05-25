"""Deal Library page — /deal-library.

Renders the real, licensed company universe ingested from Capital IQ screening
exports (see scripts/ingest_deal_library_exports.py + rcm_mc.data.deal_library).
This is a BENCHMARK reference library — not Pipeline (your live deals) and not
Portfolio (your holdings).

Honesty: financials in this export are sparse (EV/EBITDA ~97% blank, revenue
~74% blank — these are private sponsor-backed companies). Missing renders as
"—", never 0; the page surfaces the missingness rates outright so a user knows
how complete the data is. When no export has been ingested, the page shows an
honest empty state with the ingest command rather than fabricating rows.
"""
from __future__ import annotations

import html as _html
import urllib.parse as _url
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import (
    chartis_shell, ck_page_title, ck_kpi_block, ck_empty_state, ck_table,
    ck_source_purpose, P,
)
from rcm_mc.data import deal_library as dl


def _freq_table(title: str, rows: List[Dict[str, Any]]) -> str:
    body = ck_table(
        [{"value": r["value"], "n": r["n"]} for r in rows],
        [{"key": "value", "label": title, "align": "left"},
         {"key": "n", "label": "Companies", "align": "right", "kind": "number"}],
        dense=True,
    )
    return (f'<div style="flex:1;min-width:220px">'
            f'<div style="font-family:var(--sc-mono);font-size:10px;'
            f'letter-spacing:0.08em;text-transform:uppercase;color:{P["text_dim"]};'
            f'margin-bottom:6px">{_html.escape(title)}</div>{body}</div>')


def _missingness_strip(miss: Dict[str, float]) -> str:
    chips = []
    for f, pct in miss.items():
        tone = (P["negative"] if pct >= 75 else
                P["warning"] if pct >= 40 else P["positive"])
        chips.append(
            f'<span style="font-family:var(--sc-mono);font-size:10px;'
            f'border:1px solid {P["border"]};border-radius:2px;padding:3px 7px;'
            f'color:{P["text_dim"]}">{_html.escape(f)} '
            f'<b style="color:{tone}">{pct:.0f}% missing</b></span>')
    return ('<div style="display:flex;flex-wrap:wrap;gap:6px;margin:10px 0">'
            + "".join(chips) + "</div>")


def _sort_link(params: Dict[str, str], col: str, label: str) -> str:
    cur = params.get("sort_by", "company_name")
    cur_dir = params.get("sort_dir", "asc")
    nxt = "desc" if (cur == col and cur_dir == "asc") else "asc"
    arrow = (" ▲" if (cur == col and cur_dir == "asc")
             else " ▼" if (cur == col and cur_dir == "desc") else "")
    qp = dict(params); qp.update({"sort_by": col, "sort_dir": nxt, "offset": "0"})
    return (f'<a href="/deal-library?{_url.urlencode(qp)}" '
            f'style="color:inherit;text-decoration:none">{_html.escape(label)}{arrow}</a>')


def render_deal_library(store: Any, params: Optional[Dict[str, str]] = None) -> str:
    params = {k: str(v) for k, v in (params or {}).items() if v}
    total = dl.count(store)

    purpose_hdr = ck_source_purpose(
        purpose=("Browse the benchmark universe of sponsor-backed healthcare "
                 "companies ingested from licensed Capital IQ screening exports."),
        universe="mixed", confidence="derived",
        source=("Capital IQ company screening exports (licensed; user-provided) "
                "+ CMS public enrichment where entity-resolved"),
        next_action="Filter to a vertical / sponsor / geography",
    )
    not_note = (
        f'<p style="font-family:var(--sc-mono);font-size:11px;color:{P["text_dim"]};'
        f'margin:6px 0 0">This is a <b>benchmark transaction/company library</b> '
        f'— not your Pipeline (live deals) and not your Portfolio (holdings).</p>')

    title = ck_page_title(
        "Deal Library",
        eyebrow="BENCHMARK COMPANY LIBRARY",
        meta=(f"{total:,} sponsor-backed healthcare companies · licensed "
              f"Capital IQ exports" if total else "no export ingested yet"),
    )

    if not total:
        empty = ck_empty_state(
            "Deal Library is empty",
            "No licensed export has been ingested yet. Drop your Capital IQ "
            "screening exports into data/vendor/deal_library/ and run "
            "scripts/ingest_deal_library_exports.py, then reload.",
        )
        return chartis_shell(title + purpose_hdr + not_note + empty,
                             title="Deal Library", active_nav="/deal-library")

    # ── summary ──
    sources = dl.source_breakdown(store)
    miss = dl.field_missingness(store)
    rev_present = round(100 - miss.get("revenue", 100), 0)
    spons_present = round(100 - miss.get("sponsor_owner", 100), 0)
    kpis = (
        ck_kpi_block("Companies", f"{total:,}")
        + ck_kpi_block("Sources", str(len(sources)),
                       sub=", ".join(s["source_system"] for s in sources)[:40])
        + ck_kpi_block("With sponsor", f"{spons_present:.0f}%",
                       sub="PE owner identified")
        + ck_kpi_block("With revenue", f"{rev_present:.0f}%",
                       sub="rest report no public revenue")
    )

    freq = ('<div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:14px">'
            + _freq_table("Top sponsors", dl.top_values(store, "sponsor_owner", 10))
            + _freq_table("Top verticals", dl.top_values(store, "industry", 10))
            + _freq_table("Top states", dl.top_values(store, "state", 10))
            + "</div>")

    # ── filters / search ──
    search = params.get("search", "")
    state = params.get("state", "")
    form = (
        f'<form method="get" action="/deal-library" '
        f'style="display:flex;gap:10px;flex-wrap:wrap;align-items:end;margin:16px 0">'
        f'<input type="text" name="search" value="{_html.escape(search)}" '
        f'placeholder="Search name / sponsor / vertical" '
        f'style="padding:7px 9px;border:1px solid {P["border"]};border-radius:2px;'
        f'min-width:260px;font-size:13px">'
        f'<input type="text" name="state" value="{_html.escape(state)}" '
        f'placeholder="State (e.g. CA)" maxlength="2" '
        f'style="padding:7px 9px;border:1px solid {P["border"]};border-radius:2px;'
        f'width:120px;font-size:13px;text-transform:uppercase">'
        f'<button type="submit" style="padding:8px 16px;background:{P["accent"]};'
        f'color:#fff;border:none;border-radius:2px;font-size:12px;cursor:pointer">'
        f'Filter</button>'
        f'<a href="/deal-library" style="font-size:12px;color:{P["text_dim"]};'
        f'align-self:center">Clear</a></form>')

    # ── table ──
    try:
        offset = max(0, int(params.get("offset", "0")))
    except ValueError:
        offset = 0
    page_size = 50
    res = dl.query(
        store,
        filters={"state": state.upper()} if state else None,
        search=search or None,
        sort_by=params.get("sort_by", "company_name"),
        sort_dir=params.get("sort_dir", "asc"),
        limit=page_size, offset=offset,
    )
    cols = [
        {"key": "company_name", "label": _sort_link(params, "company_name", "Company"), "align": "left"},
        {"key": "sponsor_owner", "label": _sort_link(params, "sponsor_owner", "Sponsor"), "align": "left"},
        {"key": "industry", "label": "Vertical", "align": "left"},
        {"key": "state", "label": _sort_link(params, "state", "State"), "align": "left"},
        {"key": "revenue", "label": _sort_link(params, "revenue", "Revenue ($mm)"), "align": "right", "kind": "currency"},
        {"key": "completeness_score", "label": _sort_link(params, "completeness_score", "Complete"), "align": "right", "kind": "percent"},
    ]
    # Truncate long verticals for readability; missing stays "—" via ck_table.
    view_rows = []
    for r in res["rows"]:
        rr = dict(r)
        if rr.get("industry"):
            rr["industry"] = str(rr["industry"]).split(";")[0][:34]
        view_rows.append(rr)
    table = ck_table(view_rows, cols, dense=True)

    shown_lo = offset + 1
    shown_hi = min(offset + page_size, res["total"])
    pager = (
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-top:10px;font-family:var(--sc-mono);font-size:11px;color:{P["text_dim"]}">'
        f'<span>Showing {shown_lo:,}–{shown_hi:,} of {res["total"]:,}</span><span>')
    if offset > 0:
        pp = dict(params); pp["offset"] = str(max(0, offset - page_size))
        pager += f'<a href="/deal-library?{_url.urlencode(pp)}" style="margin-right:14px">← Prev</a>'
    if shown_hi < res["total"]:
        np = dict(params); np["offset"] = str(offset + page_size)
        pager += f'<a href="/deal-library?{_url.urlencode(np)}">Next →</a>'
    pager += "</span></div>"

    body = (
        title + purpose_hdr + not_note
        + f'<div class="ck-kpi-grid" style="margin-top:14px">{kpis}</div>'
        + _missingness_strip(miss)
        + freq
        + form
        + table
        + pager
    )
    return chartis_shell(body, title="Deal Library", active_nav="/deal-library")
