"""County Explorer — /county-explorer.

Drill into a state's counties on real public demographics: population, age 65+,
median household income, uninsured rate, and rural share. Extends the
Geographic Intelligence suite one level down from states, using the real
county-level data already committed (County Health Rankings / Census ACS,
3,143 counties) — no new ingestion, no fabrication.

Sortable by any column; a state-total / population-weighted footer gives
context. Counties with a missing value render "—" (never fabricated).
"""
from __future__ import annotations

import html as _html
from typing import Dict, List

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_page_title
from rcm_mc.ui._chart_kit import ck_chart_assets, ck_chart_grid, ck_hbar_chart
from rcm_mc.ui.data_public.state_compare_page import _VALID
from rcm_mc.ui.data_public.state_profile_page import _STATE_NAMES

_DEFAULT = "OH"

# (key, label, formatter, higher_is_better, is_fraction) — drives columns + sort.
_COLS = [
    ("population",               "Population",       lambda x: f"{int(x):,}",   None,  False),
    ("pct_age_65_plus",          "Age 65+",          lambda x: f"{x*100:.1f}%", None,  True),
    ("median_household_income",  "Median HH income", lambda x: f"${x:,.0f}",    True,  False),
    ("uninsured_rate",           "Uninsured",        lambda x: f"{x*100:.1f}%", False, True),
    ("child_poverty_rate",       "Child poverty",    lambda x: f"{x*100:.1f}%", False, True),
    ("pct_rural",                "Rural",            lambda x: f"{x*100:.1f}%", None,  True),
]
_COL_BY_KEY = {c[0]: c for c in _COLS}
_DEFAULT_SORT = "population"


def _parse_state(params: Dict) -> str:
    raw = (params or {}).get("state", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    s = str(raw).strip().upper()
    return s if s in _VALID else _DEFAULT


def _parse_sort(params: Dict) -> str:
    raw = (params or {}).get("sort", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    k = str(raw).strip()
    return k if k in _COL_BY_KEY else _DEFAULT_SORT


def _num(v):
    try:
        return float(v) if v is not None and v == v else None
    except Exception:
        return None


def explorer_rows(state: str, sort_key: str):
    """Return (rows, footer): rows are county dicts sorted by sort_key desc
    (income asc would be odd; we always sort numerically high→low for scanning),
    footer holds state totals/weighted means over the real values."""
    from rcm_mc.data import county_demographics as _d
    counties = _d.counties_for_state(state)
    rows = []
    for c in counties:
        rows.append({
            "name": c.get("county_name", ""),
            **{k: _num(c.get(k)) for k, *_ in _COLS},
        })
    rows.sort(key=lambda r: (r.get(sort_key) is not None, r.get(sort_key) or 0), reverse=True)

    # footer: total population + population-weighted means for the rate columns
    total_pop = sum(r["population"] for r in rows if r["population"]) or 0
    footer: Dict[str, float] = {"population": total_pop}
    for key, _lbl, _f, _h, _frac in _COLS:
        if key == "population":
            continue
        num = sum((r[key] * r["population"]) for r in rows
                  if r.get(key) is not None and r.get("population"))
        den = sum(r["population"] for r in rows
                  if r.get(key) is not None and r.get("population"))
        footer[key] = (num / den) if den else None
    return rows, footer


def county_dataframe(state: str, sort_key: str):
    """County rows as raw numbers for CSV export. Missing values are blank
    cells — never fabricated."""
    import pandas as _pd
    rows, _footer = explorer_rows(state, sort_key)
    out = []
    for r in rows:
        rec = {"County": r["name"]}
        for key, label, _f, _h, _frac in _COLS:
            v = r.get(key)
            rec[label] = v if v is not None else ""
        out.append(rec)
    cols = ["County"] + [lbl for _k, lbl, *_ in _COLS]
    return _pd.DataFrame(out, columns=cols)


def _fmt_pop(v: float) -> str:
    if v is None:
        return "—"
    if v >= 1e6:
        return f"{v / 1e6:.1f}M"
    if v >= 1e3:
        return f"{v / 1e3:.0f}K"
    return f"{int(v):,}"


def _county_kpi_strip(rows, footer, name) -> str:
    """Leading KPI strip (X-Ray pattern) from the real county data: county
    count, total state population, and the largest county. No fabrication —
    derived from the same rows as the table; counties with no population are
    excluded from the 'largest' pick."""
    n = len(rows)
    total_pop = footer.get("population") or 0
    pop_rows = [r for r in rows if r.get("population")]
    top = max(pop_rows, key=lambda r: r["population"], default=None)
    strip = (
        '<div class="ck-kpi-strip" style="margin-bottom:14px">'
        + ck_kpi_block("Counties", str(n))
        + ck_kpi_block("Total population", _fmt_pop(total_pop))
    )
    if top is not None:
        strip += ck_kpi_block(
            "Largest county", _html.escape(str(top.get("name", "—"))),
            sub=_fmt_pop(top["population"]))
    return strip + '</div>'


def _county_top_bar(key: str, rows, footer, n: int = 12) -> str:
    """Top-N counties on one metric as a horizontal ranked bar, with the
    state population-weighted mean as a dashed reference. '' when no data."""
    col = _COL_BY_KEY.get(key)
    if not col:
        return ""
    _k, label, fmt, _h, _frac = col
    present = [(r["name"], r[key]) for r in rows if r.get(key) is not None]
    if not present:
        return ""
    present.sort(key=lambda t: t[1], reverse=True)
    top = present[:n]
    items = [(nm, v, "teal") for nm, v in top]
    mref = footer.get(key)
    ref = ("State wtd-mean", mref) if (mref is not None and mref == mref) else None
    return ck_hbar_chart(
        f"Top {len(top)} counties — {label}", items, value_fmt=fmt,
        reference=ref, subtitle=f"of {len(present)} counties with data",
        source="County Health Rankings / Census ACS",
        chart_id="ckc-county-" + key,
    )


def _county_chart_builder(state, sort_key, cmetric):
    """'+ Chart a metric' control — pick a county metric, render its top-N
    ranked bar. Reuses the current state; submits (GET) to /county-explorer."""
    P_ = P
    td = P_["text_dim"]; ac = P_["accent"]; border = P_["border"]
    sel = (f'background:{P_["panel_alt"]};color:{P_["text"]};border:1px solid {border};'
           f'padding:6px 8px;font-family:Inter Tight,sans-serif;font-size:12px;border-radius:2px')
    opts = "".join(
        f'<option value="{_html.escape(k)}"{" selected" if k == cmetric else ""}>'
        f'{_html.escape(lbl)}</option>' for k, lbl, *_ in _COLS)
    return (
        f'<details class="ce-chart-builder"{" open" if cmetric else ""} '
        f'style="margin:0 0 14px;border:1px solid {border};border-radius:4px;padding:0 14px">'
        f'<summary style="cursor:pointer;padding:10px 0;font-family:JetBrains Mono,monospace;'
        f'font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:{ac}">'
        f'＋ Chart a metric (top counties)</summary>'
        f'<form method="get" action="/county-explorer" style="display:flex;gap:10px;'
        f'align-items:flex-end;flex-wrap:wrap;padding:4px 0 14px">'
        f'<input type="hidden" name="state" value="{state}">'
        f'<input type="hidden" name="sort" value="{_html.escape(sort_key)}">'
        f'<label style="font-size:11px;color:{td}">Metric<br>'
        f'<select name="cmetric" style="{sel};margin-top:4px;min-width:200px">{opts}</select></label>'
        f'<button type="submit" style="background:{ac};color:#fff;border:none;padding:7px 16px;'
        f'font-family:JetBrains Mono,monospace;font-size:12px;border-radius:2px;cursor:pointer">'
        f'Chart top counties</button></form></details>'
    )


def render_county_explorer(params: Dict = None) -> str:
    state = _parse_state(params)
    sort_key = _parse_sort(params)
    name = _STATE_NAMES.get(state, state)
    rows, footer = explorer_rows(state, sort_key)
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]

    opts = "".join(
        f'<option value="{s}"{" selected" if s == state else ""}>{_html.escape(_STATE_NAMES.get(s,s))} ({s})</option>'
        for s in sorted(_VALID)
    )
    sel = (f'background:{P["panel_alt"]};color:{tp};border:1px solid {border};'
           f'padding:6px 8px;font-family:Inter Tight,sans-serif;font-size:12px;border-radius:2px')
    form = (
        f'<form method="get" action="/county-explorer" style="margin-bottom:16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">'
        f'<label style="font-size:11px;color:{td}">State '
        f'<select name="state" onchange="this.form.submit()" style="{sel};margin-left:6px">{opts}</select></label>'
        f'<input type="hidden" name="sort" value="{_html.escape(sort_key)}">'
        f'<a href="/county-explorer.csv?state={state}&sort={_html.escape(sort_key)}" '
        f'style="font-size:11px;color:{ac};text-decoration:none">Export CSV &#8595;</a>'
        f'</form>'
    )

    def _hdr(key, label, align="right"):
        arrow = " &#9660;" if key == sort_key else ""
        href = f"/county-explorer?state={state}&sort={key}" if key else ""
        inner = (f'<a href="{href}" style="color:{td};text-decoration:none">{_html.escape(label)}{arrow}</a>'
                 if key else _html.escape(label))
        return (f'<th style="text-align:{align};padding:6px 10px;border-bottom:2px solid {border};'
                f'font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">{inner}</th>')

    th = _hdr("", "County", "left") + "".join(_hdr(k, lbl) for k, lbl, *_ in _COLS)

    # Max of the sorted column across visible counties — for an inline bar on
    # that column (honest visual of the real values; sorted column only).
    sort_max = max((abs(r[sort_key]) for r in rows
                    if r.get(sort_key) is not None), default=0.0)
    body_rows = ""
    for i, r in enumerate(rows):
        bg = P["panel_alt"] if i % 2 else P["panel"]
        cells = (f'<td style="padding:5px 10px;font-size:11px;color:{tp};background:{bg}">{_html.escape(str(r["name"]))}</td>')
        for key, _lbl, fmt, _h, _frac in _COLS:
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

    # weighted-mean footer
    fcells = (f'<td style="padding:6px 10px;font-size:11px;color:{td};border-top:2px solid {border}">'
              f'{name} — {len(rows)} counties</td>')
    for key, _lbl, fmt, _h, _frac in _COLS:
        v = footer.get(key)
        s = fmt(v) if v is not None else "—"
        lab = "" if key == "population" else " <span style=\"font-size:9px;color:%s\">wtd</span>" % fa
        fcells += (f'<td style="padding:6px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
                   f'font-size:12px;font-variant-numeric:tabular-nums;color:{td};border-top:2px solid {border}">{_html.escape(s)}{lab}</td>')

    # ── Visual summary: top-N counties on the sorted metric (tracks the
    # column you click) + an optional metric the partner charts. Same real
    # rows as the table; each card exports to PNG.
    def _qp(n, d=""):
        v = (params or {}).get(n, d)
        return (v[0] if isinstance(v, list) and v else v if not isinstance(v, list) else d)
    cmetric = str(_qp("cmetric")).strip()
    custom_chart = _county_top_bar(cmetric, rows, footer) if cmetric in _COL_BY_KEY else ""
    default_chart = _county_top_bar(sort_key, rows, footer)
    charts_html = (
        f'<div class="ce-charts" style="margin:4px 0 10px">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;letter-spacing:.06em;'
        f'text-transform:uppercase;color:{td};margin-bottom:8px">Visual summary</div>'
        f'{_county_chart_builder(state, sort_key, cmetric)}'
        f'{ck_chart_grid(custom_chart) if custom_chart else ""}'
        f'{ck_chart_grid(default_chart) if default_chart else ""}</div>'
    )
    body = f"""
<div class="ck-page-wrap">
  {ck_page_title(f"County Explorer — {name}", eyebrow="MARKET INTEL", meta=f"{len(rows)} {name} counties on real Census/ACS demographics — click a column to sort")}
  {_county_kpi_strip(rows, footer, name)}
  <p style="font-size:13px;color:{td};max-width:74ch;margin:0 0 14px">
    Drill into {_html.escape(name)}'s counties on real public demographics
    (County Health Rankings / Census ACS). Click any column to re-sort. The
    footer shows the state total population and population-weighted means.
    Counties missing a value show &ldquo;&mdash;&rdquo;; nothing is fabricated.
  </p>
  {form}
  {charts_html}
  <div style="overflow-x:auto;border:1px solid {border};border-radius:3px">
  <table style="width:100%;border-collapse:collapse">
    <thead><tr>{th}</tr></thead>
    <tbody>{body_rows}</tbody>
    <tfoot><tr>{fcells}</tr></tfoot>
  </table>
  </div>
  <p style="font-size:10px;color:{fa};margin-top:10px">
    Source: County Health Rankings &amp; Roadmaps (republishing U.S. Census Bureau ACS / SAHIE / SAIPE), keyless.
    Area-level survey estimates — market context, not a deal-level figure.
    Roll up to state level on <a href="/state-profile?state={state}" style="color:{ac};text-decoration:none">State Profile &rarr;</a>
    or the <a href="/geo-intel" style="color:{ac};text-decoration:none">Geographic Intelligence</a> suite.
  </p>
</div>"""
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_chart_assets() + ck_page_actions()
    return chartis_shell(body, f"County Explorer — {name}", active_nav="/county-explorer")
