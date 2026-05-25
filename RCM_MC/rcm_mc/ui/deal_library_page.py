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


def _freq_table(title: str, rows: List[Dict[str, Any]],
                link_param: Optional[str] = None) -> str:
    # When link_param is set, each value links to the filtered library view —
    # so "Top sponsors" / "Top states" double as a one-click drill-down.
    disp = []
    for r in rows:
        val = r["value"]
        if link_param and val:
            cell = (f'<a href="/deal-library?{link_param}={_url.quote(str(val))}" '
                    f'style="color:{P["accent"]};text-decoration:none">'
                    f'{_html.escape(str(val))}</a>')
        else:
            cell = _html.escape(str(val)) if val else "—"
        disp.append({"value": cell, "n": r["n"]})
    # ck_table escapes cell content; pre-built anchor must bypass that, so
    # render the small table inline here rather than via ck_table.
    head = (f'<tr><th class="align-left">{_html.escape(title)}</th>'
            f'<th class="align-right">Companies</th></tr>')
    body = "".join(
        f'<tr><td class="align-left">{d["value"]}</td>'
        f'<td class="align-right sc-num">{d["n"]:,}</td></tr>' for d in disp)
    tbl = f'<table class="ck-table ck-dense"><thead>{head}</thead><tbody>{body}</tbody></table>'
    return (f'<div style="flex:1;min-width:220px">'
            f'<div style="font-family:var(--sc-mono);font-size:10px;'
            f'letter-spacing:0.08em;text-transform:uppercase;color:{P["text_dim"]};'
            f'margin-bottom:6px">{_html.escape(title)}</div>{tbl}</div>')


def _sponsor_rollup_card(roll: Dict[str, Any]) -> str:
    if not roll.get("n_total"):
        return ""
    states = " · ".join(f'{s["state"]} {s["n"]}' for s in roll["top_states"]) or "—"
    return (
        f'<div style="border:1px solid {P["border"]};border-left:3px solid '
        f'{P["accent"]};border-radius:2px;padding:12px 16px;margin:14px 0;'
        f'background:{P["panel"] if "panel" in P else "#fff"}">'
        f'<div style="font-family:var(--sc-mono);font-size:10px;'
        f'letter-spacing:0.08em;text-transform:uppercase;color:{P["text_dim"]}">'
        f'Sponsor footprint</div>'
        f'<div style="font-size:18px;font-weight:600;margin:2px 0 6px">'
        f'{_html.escape(roll["sponsor"])}</div>'
        f'<div style="font-family:var(--sc-mono);font-size:12px;color:{P["text_dim"]}">'
        f'<b style="color:{P["text"]}">{roll["n_total"]:,}</b> healthcare companies '
        f'· {roll["n_current"]:,} current · {roll["n_prior"]:,} prior '
        f'· {roll["n_with_revenue"]:,} disclose revenue<br>'
        f'top states: {_html.escape(states)}</div></div>')


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

    # Provenance line from the sources table (if the operator loaded it).
    srcs = dl.sources(store)
    prov = ""
    if srcs:
        files = " · ".join(
            f'{_html.escape(str(s.get("source_file") or "?"))} '
            f'({int(s.get("row_count") or 0):,})' for s in srcs[:6])
        prov = (f'<p style="font-family:var(--sc-mono);font-size:10px;'
                f'color:{P["text_dim"]};margin:8px 0 0">Ingested from '
                f'{len(srcs)} licensed export(s): {files}</p>')

    vert_tbl = _freq_table("Est. verticals (from name)",
                           dl.top_values(store, "healthcare_vertical_est", 10), "vertical")
    freq = ('<div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:14px">'
            + _freq_table("Top sponsors", dl.top_values(store, "sponsor_owner", 10), "sponsor")
            + vert_tbl
            + _freq_table("Top states", dl.top_values(store, "state", 10), "state")
            + "</div>"
            + f'<p style="font-family:var(--sc-mono);font-size:10px;'
              f'color:{P["text_dim"]};margin:6px 2px 0">Vertical is <b>estimated '
              f'from the company name</b> (the licensed industry field is a single '
              f'coarse value); ~76% are unclassified and left blank — it is a '
              f'heuristic tag, not an authoritative classification.</p>'
            + f'<p style="margin:8px 2px 0;font-size:12px">'
              f'<a href="/deal-library/sponsors" style="color:{P["accent"]};'
              f'text-decoration:none">Browse all sponsors →</a>'
              f'<span style="color:{P["text_dim"]};margin:0 10px">·</span>'
              f'<a href="/deal-library/comps" style="color:{P["accent"]};'
              f'text-decoration:none">Disclosed-financial multiples →</a></p>')

    # ── filters / search ──
    search = params.get("search", "")
    state = params.get("state", "")
    sponsor = params.get("sponsor", "")
    vertical = params.get("vertical", "")
    rollup = _sponsor_rollup_card(dl.sponsor_rollup(store, sponsor)) if sponsor else ""
    form = (
        f'<form method="get" action="/deal-library" '
        f'style="display:flex;gap:10px;flex-wrap:wrap;align-items:end;margin:16px 0">'
        + (f'<input type="hidden" name="sponsor" value="{_html.escape(sponsor)}">'
           if sponsor else "")
        + (f'<input type="hidden" name="vertical" value="{_html.escape(vertical)}">'
           if vertical else "")
        + f'<input type="text" name="search" value="{_html.escape(search)}" '
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
    _filters = {}
    if state:
        _filters["state"] = state.upper()
    if sponsor:
        _filters["sponsor_owner"] = sponsor
    if vertical:
        _filters["healthcare_vertical_est"] = vertical
    res = dl.query(
        store,
        filters=_filters or None,
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
        + prov
        + _missingness_strip(miss)
        + freq
        + form
        + rollup
        + table
        + pager
    )
    return chartis_shell(body, title="Deal Library", active_nav="/deal-library")


def render_sponsors_index(store: Any, params: Optional[Dict[str, str]] = None) -> str:
    """/deal-library/sponsors — browsable, searchable index of every sponsor in
    the licensed universe, ranked by # of healthcare companies backed. Each
    sponsor links to its filtered Deal Library view."""
    params = {k: str(v) for k, v in (params or {}).items() if v}
    total_companies = dl.count(store)
    title = ck_page_title(
        "Sponsors — Deal Library",
        eyebrow="SPONSOR ACTIVITY INDEX",
        meta=("Investors backing the sponsor-backed healthcare universe "
              "(VC / accelerator / REIT / PE) · current & prior owners"
              if total_companies else "no export ingested yet"),
    )
    back = (f'<p style="margin:0 0 8px"><a href="/deal-library" '
            f'style="color:{P["accent"]};text-decoration:none;font-size:12px">'
            f'← Deal Library</a></p>')
    if not total_companies:
        empty = ck_empty_state(
            "No sponsors yet",
            "Ingest a licensed export first (see /deal-library).")
        return chartis_shell(back + title + empty, title="Sponsors",
                             active_nav="/deal-library")

    name_like = params.get("q", "")
    try:
        offset = max(0, int(params.get("offset", "0")))
    except ValueError:
        offset = 0
    page_size = 60
    total = dl.sponsor_count(store, name_like=name_like or None)
    rows = dl.sponsor_index(store, limit=page_size, offset=offset,
                            name_like=name_like or None)

    form = (
        f'<form method="get" action="/deal-library/sponsors" '
        f'style="display:flex;gap:10px;align-items:end;margin:14px 0">'
        f'<input type="text" name="q" value="{_html.escape(name_like)}" '
        f'placeholder="Search sponsor name" '
        f'style="padding:7px 9px;border:1px solid {P["border"]};border-radius:2px;'
        f'min-width:280px;font-size:13px">'
        f'<button type="submit" style="padding:8px 16px;background:{P["accent"]};'
        f'color:#fff;border:none;border-radius:2px;font-size:12px;cursor:pointer">'
        f'Search</button>'
        f'<a href="/deal-library/sponsors" style="font-size:12px;'
        f'color:{P["text_dim"]};align-self:center">Clear</a></form>')

    head = ('<tr><th class="align-left">Sponsor</th>'
            '<th class="align-right">Companies</th>'
            '<th class="align-right">Current</th>'
            '<th class="align-right">Prior</th></tr>')
    body_rows = "".join(
        f'<tr><td class="align-left">'
        f'<a href="/deal-library?sponsor={_url.quote(r["sponsor"])}" '
        f'style="color:{P["accent"]};text-decoration:none">'
        f'{_html.escape(r["sponsor"])}</a></td>'
        f'<td class="align-right sc-num">{r["n_total"]:,}</td>'
        f'<td class="align-right sc-num">{r["n_current"]:,}</td>'
        f'<td class="align-right sc-num">{r["n_prior"]:,}</td></tr>'
        for r in rows)
    table = (f'<table class="ck-table ck-dense"><thead>{head}</thead>'
             f'<tbody>{body_rows}</tbody></table>')

    lo, hi = offset + 1, min(offset + page_size, total)
    pager = (f'<div style="display:flex;justify-content:space-between;'
             f'margin-top:10px;font-family:var(--sc-mono);font-size:11px;'
             f'color:{P["text_dim"]}"><span>{total:,} sponsors · showing '
             f'{lo:,}–{hi:,}</span><span>')
    if offset > 0:
        pp = dict(params); pp["offset"] = str(max(0, offset - page_size))
        pager += f'<a href="/deal-library/sponsors?{_url.urlencode(pp)}" style="margin-right:14px">← Prev</a>'
    if hi < total:
        np = dict(params); np["offset"] = str(offset + page_size)
        pager += f'<a href="/deal-library/sponsors?{_url.urlencode(np)}">Next →</a>'
    pager += "</span></div>"

    return chartis_shell(back + title + form + table + pager,
                         title="Sponsors — Deal Library",
                         active_nav="/deal-library")


def _dist_card(label: str, d: Dict[str, Any], suffix: str = "x") -> str:
    if not d.get("n"):
        return (f'<div style="flex:1;min-width:220px;border:1px solid {P["border"]};'
                f'border-radius:2px;padding:12px 16px">'
                f'<div style="font-family:var(--sc-mono);font-size:10px;'
                f'text-transform:uppercase;color:{P["text_dim"]}">{_html.escape(label)}</div>'
                f'<div style="color:{P["text_dim"]};font-size:13px;margin-top:6px">'
                f'no companies disclose this</div></div>')
    return (
        f'<div style="flex:1;min-width:220px;border:1px solid {P["border"]};'
        f'border-left:3px solid {P["accent"]};border-radius:2px;padding:12px 16px">'
        f'<div style="font-family:var(--sc-mono);font-size:10px;'
        f'text-transform:uppercase;color:{P["text_dim"]}">{_html.escape(label)}</div>'
        f'<div style="font-size:20px;font-weight:600;margin:4px 0">'
        f'{d["median"]:.2f}{suffix} <span style="font-size:12px;font-weight:400;'
        f'color:{P["text_dim"]}">median</span></div>'
        f'<div style="font-family:var(--sc-mono);font-size:12px;color:{P["text_dim"]}">'
        f'P25 {d["p25"]:.2f}{suffix} · P75 {d["p75"]:.2f}{suffix} · '
        f'<b style="color:{P["text"]}">n={d["n"]:,}</b></div></div>')


def render_deal_comps(store: Any, params: Optional[Dict[str, str]] = None) -> str:
    """/deal-library/comps — EV/Revenue & EV/EBITDA over the disclosed-financial
    subset (mostly public companies). Honestly scoped: small n, missing excluded
    (never 0), benchmark distribution not a curated comp set or a prediction."""
    params = {k: str(v) for k, v in (params or {}).items() if v}
    total_companies = dl.count(store)
    title = ck_page_title(
        "Comparables — Deal Library",
        eyebrow="DISCLOSED-FINANCIAL MULTIPLES",
        meta=("EV/Revenue & EV/EBITDA for the subset that discloses them"
              if total_companies else "no export ingested yet"),
    )
    back = (f'<p style="margin:0 0 8px"><a href="/deal-library" '
            f'style="color:{P["accent"]};text-decoration:none;font-size:12px">'
            f'← Deal Library</a></p>')
    if not total_companies:
        return chartis_shell(
            back + title + ck_empty_state(
                "No data yet", "Ingest a licensed export first (see /deal-library)."),
            title="Comparables", active_nav="/deal-library")

    summ = dl.multiples_summary(store)
    cards = ('<div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:14px">'
             + _dist_card("EV / Revenue", summ["ev_revenue"])
             + _dist_card("EV / EBITDA", summ["ev_ebitda"])
             + "</div>")
    caveat = (
        f'<p style="font-family:var(--sc-mono);font-size:11px;color:{P["text_dim"]};'
        f'line-height:1.5;margin:10px 0 0">Computed only for companies that '
        f'disclose enterprise value <b>and</b> a positive denominator — a small, '
        f'mostly-public slice of the {total_companies:,}-company universe (the rest '
        f'report no public financials). Missing values are <b>excluded, never '
        f'treated as zero</b>. This is a benchmark distribution over disclosed '
        f'financials — not a curated comp set and not a prediction.</p>')

    try:
        offset = max(0, int(params.get("offset", "0")))
    except ValueError:
        offset = 0
    page_size = 50
    res = dl.companies_with_multiples(store, limit=page_size, offset=offset)
    head = ('<tr><th class="align-left">Company</th><th class="align-left">Ticker</th>'
            '<th class="align-right">EV ($mm)</th><th class="align-right">Revenue ($mm)</th>'
            '<th class="align-right">EV/Rev</th><th class="align-right">EV/EBITDA</th></tr>')
    def fmt(v, suf=""):
        return (f"{v:,.1f}{suf}" if isinstance(v, (int, float)) else "—")
    body = "".join(
        f'<tr><td class="align-left">{_html.escape(str(r["company_name"]))}</td>'
        f'<td class="align-left">{_html.escape(str(r["ticker"] or "—"))}</td>'
        f'<td class="align-right sc-num">{fmt(r["enterprise_value"])}</td>'
        f'<td class="align-right sc-num">{fmt(r["revenue"])}</td>'
        f'<td class="align-right sc-num">{fmt(r["ev_revenue_multiple"],"x")}</td>'
        f'<td class="align-right sc-num">{fmt(r["ev_ebitda_multiple"],"x")}</td></tr>'
        for r in res["rows"])
    table = (f'<table class="ck-table ck-dense"><thead>{head}</thead>'
             f'<tbody>{body}</tbody></table>')
    lo, hi = offset + 1, min(offset + page_size, res["total"])
    pager = (f'<div style="display:flex;justify-content:space-between;margin-top:10px;'
             f'font-family:var(--sc-mono);font-size:11px;color:{P["text_dim"]}">'
             f'<span>{res["total"]:,} with EV+revenue · showing {lo:,}–{hi:,}</span><span>')
    if offset > 0:
        pp = dict(params); pp["offset"] = str(max(0, offset - page_size))
        pager += f'<a href="/deal-library/comps?{_url.urlencode(pp)}" style="margin-right:14px">← Prev</a>'
    if hi < res["total"]:
        np = dict(params); np["offset"] = str(offset + page_size)
        pager += f'<a href="/deal-library/comps?{_url.urlencode(np)}">Next →</a>'
    pager += "</span></div>"

    return chartis_shell(back + title + cards + caveat + table + pager,
                         title="Comparables — Deal Library",
                         active_nav="/deal-library")
