"""Metro Markets — /metro-markets.

The real CBSA (metro/micro) level of the Geographic Intelligence suite. Ranks
U.S. Core-Based Statistical Areas on real, derived demographics — population,
age 65+, median household income (a population-weighted estimate), uninsured
rate, and rural share — rolled up from the in-repo county ACS data via the
committed OMB CBSA↔county crosswalk.

This is the real-data answer to the (illustrative) /geo-market white-space
analyzer: every figure here is real and sourced. Median income is a
population-weighted ESTIMATE of member-county medians (labelled). Sortable;
metro/micro filter. Nothing is fabricated.
"""
from __future__ import annotations

import html as _html
from typing import Dict

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_page_title

# (key, label, formatter, is_estimate)
_COLS = [
    ("population",               "Population",       lambda x: f"{int(x):,}",   False),
    ("pct_age_65_plus",          "Age 65+",          lambda x: f"{x*100:.1f}%", False),
    ("median_household_income",  "Median HH income", lambda x: f"${x:,.0f}",    True),
    ("uninsured_rate",           "Uninsured",        lambda x: f"{x*100:.1f}%", False),
    ("child_poverty_rate",       "Child poverty",    lambda x: f"{x*100:.1f}%", False),
    ("pct_rural",                "Rural",            lambda x: f"{x*100:.1f}%", False),
]
_COL_BY_KEY = {c[0]: c for c in _COLS}
_DEFAULT_SORT = "population"
_VALID_TYPES = {"Metropolitan", "Micropolitan"}


def _parse_sort(params: Dict) -> str:
    raw = (params or {}).get("sort", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    k = str(raw).strip()
    return k if k in _COL_BY_KEY else _DEFAULT_SORT


def _parse_type(params: Dict) -> str:
    raw = (params or {}).get("type", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    t = str(raw).strip().title()
    return t if t in _VALID_TYPES else "Metropolitan"


def metro_rows(area_type: str, sort_key: str, limit: int = 100):
    from rcm_mc.data import cbsa_demographics as _c
    rows = _c.cbsa_list(area_type)
    rows = [r for r in rows if r.get(sort_key) is not None]
    rows.sort(key=lambda r: r.get(sort_key) or 0, reverse=True)
    return rows[:limit]


def metro_dataframe(area_type: str, sort_key: str):
    import pandas as _pd
    rows = metro_rows(area_type, sort_key, limit=10_000)
    out = []
    for r in rows:
        rec = {"CBSA": r["cbsa_title"], "Type": r["area_type"], "Counties": r["county_count"]}
        for key, label, _f, _est in _COLS:
            v = r.get(key)
            rec[label] = v if v is not None else ""
        out.append(rec)
    cols = ["CBSA", "Type", "Counties"] + [lbl for _k, lbl, *_ in _COLS]
    return _pd.DataFrame(out, columns=cols)


def _fmt_pop(v) -> str:
    if v is None:
        return "—"
    if v >= 1e6:
        return f"{v / 1e6:.1f}M"
    if v >= 1e3:
        return f"{v / 1e3:.0f}K"
    return f"{int(v):,}"


def _metro_kpi_strip(rows, area_type: str) -> str:
    """Leading KPI strip (X-Ray pattern) from the real CBSA rows: market count,
    total population covered, and the largest market by population. No
    fabrication; markets without a population value are excluded from the
    'largest' pick and the total."""
    n = len(rows)
    pop_rows = [r for r in rows if r.get("population")]
    total_pop = sum(r["population"] for r in pop_rows)
    top = max(pop_rows, key=lambda r: r["population"], default=None)
    strip = (
        '<div class="ck-kpi-strip" style="margin-bottom:14px">'
        + ck_kpi_block(f"{area_type} areas", str(n))
        + ck_kpi_block("Population covered", _fmt_pop(total_pop))
    )
    if top is not None:
        strip += ck_kpi_block(
            "Largest market", _html.escape(str(top.get("cbsa_title", "—"))),
            sub=_fmt_pop(top["population"]))
    return strip + '</div>'


def render_metro_markets(params: Dict = None) -> str:
    sort_key = _parse_sort(params)
    area_type = _parse_type(params)
    rows = metro_rows(area_type, sort_key)
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]

    # controls
    sel = (f'background:{P["panel_alt"]};color:{tp};border:1px solid {border};'
           f'padding:6px 8px;font-family:Inter Tight,sans-serif;font-size:12px;border-radius:2px')
    type_opts = "".join(
        f'<option value="{t}"{" selected" if t == area_type else ""}>{t}</option>'
        for t in ("Metropolitan", "Micropolitan")
    )
    form = (
        f'<form method="get" action="/metro-markets" style="margin-bottom:16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">'
        f'<label style="font-size:11px;color:{td}">Area type '
        f'<select name="type" onchange="this.form.submit()" style="{sel};margin-left:6px">{type_opts}</select></label>'
        f'<input type="hidden" name="sort" value="{_html.escape(sort_key)}">'
        f'<a href="/metro-markets.csv?type={area_type}&sort={_html.escape(sort_key)}" '
        f'style="font-size:11px;color:{ac};text-decoration:none">Export CSV &#8595;</a>'
        f'</form>'
    )

    def _hdr(key, label, align="right"):
        arrow = " &#9660;" if key == sort_key else ""
        inner = (f'<a href="/metro-markets?type={area_type}&sort={key}" style="color:{td};text-decoration:none">{_html.escape(label)}{arrow}</a>'
                 if key else _html.escape(label))
        return (f'<th style="text-align:{align};padding:6px 10px;border-bottom:2px solid {border};'
                f'font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">{inner}</th>')

    th = (_hdr("", "CBSA", "left") + _hdr("", "Counties")
          + "".join(_hdr(k, lbl) for k, lbl, *_ in _COLS))

    # Max of the sorted column across visible rows — for an inline magnitude
    # bar on that column (honest visual of the real values; sorted column only
    # to keep the wide table readable).
    sort_max = max((abs(r[sort_key]) for r in rows
                    if r.get(sort_key) is not None), default=0.0)
    body_rows = ""
    for i, r in enumerate(rows):
        bg = P["panel_alt"] if i % 2 else P["panel"]
        cells = (f'<td style="padding:5px 10px;font-size:12px;color:{tp};background:{bg}">{_html.escape(str(r["cbsa_title"]))}</td>'
                 f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;font-size:11px;color:{fa};background:{bg}">{r["county_count"]}</td>')
        for key, _lbl, fmt, _est in _COLS:
            v = r.get(key)
            s = fmt(v) if v is not None else "—"
            hl = "font-weight:600;" if key == sort_key and v is not None else ""
            bar = ""
            if key == sort_key and v is not None and sort_max > 0:
                bw = max(2, round(abs(v) / sort_max * 100))
                bar = (f'<div style="height:3px;width:{bw}%;background:{ac};opacity:0.5;'
                       f'margin:3px 0 0 auto;border-radius:1px"></div>')
            cells += (f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
                      f'font-size:12px;font-variant-numeric:tabular-nums;color:{tp};{hl}background:{bg}">{_html.escape(s)}{bar}</td>')
        body_rows += f"<tr>{cells}</tr>"

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title("Metro Markets", eyebrow="MARKET INTEL", meta=f"{len(rows)} U.S. {area_type.lower()} areas on real CBSA demographics — click a column to sort")}
  {_metro_kpi_strip(rows, area_type)}
  <p style="font-size:13px;color:{td};max-width:74ch;margin:0 0 14px">
    The metro level of the Geographic Intelligence suite — U.S. Core-Based
    Statistical Areas ranked on real, derived demographics rolled up from county
    Census/ACS data via the OMB CBSA delineation. This is the real-data
    counterpart to the illustrative /geo-market white-space analyzer; every
    figure here is sourced. Median income is a population-weighted
    <b style="color:{tp}">estimate</b> of member-county medians; nothing is fabricated.
  </p>
  {form}
  <div style="overflow-x:auto;border:1px solid {border};border-radius:3px">
  <table style="width:100%;border-collapse:collapse">
    <thead><tr>{th}</tr></thead><tbody>{body_rows}</tbody>
  </table>
  </div>
  <p style="font-size:10px;color:{fa};margin-top:10px">
    Source: OMB CBSA delineation (U.S. Census, July 2023) × County Health Rankings / Census ACS county demographics.
    Population is a real sum; rates are population-weighted means; median income is a population-weighted estimate.
    Roll down to counties on <a href="/county-explorer" style="color:{ac};text-decoration:none">County Explorer &rarr;</a>
    or up to states via the <a href="/geo-intel" style="color:{ac};text-decoration:none">Geographic Intelligence</a> hub.
  </p>
</div>"""
    return chartis_shell(body, "Metro Markets", active_nav="/metro-markets")
