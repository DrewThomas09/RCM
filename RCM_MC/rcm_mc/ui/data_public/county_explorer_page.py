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

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_page_title
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

    body_rows = ""
    for i, r in enumerate(rows):
        bg = P["panel_alt"] if i % 2 else P["panel"]
        cells = (f'<td style="padding:5px 10px;font-size:11px;color:{tp};background:{bg}">{_html.escape(str(r["name"]))}</td>')
        for key, _lbl, fmt, _h, _frac in _COLS:
            v = r.get(key)
            s = fmt(v) if v is not None else "—"
            hl = "font-weight:600;" if key == sort_key and v is not None else ""
            cells += (f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
                      f'font-size:12px;font-variant-numeric:tabular-nums;color:{tp};{hl}background:{bg}">{_html.escape(s)}</td>')
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

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title(f"County Explorer — {name}", eyebrow="MARKET INTEL", meta=f"{len(rows)} {name} counties on real Census/ACS demographics — click a column to sort")}
  <p style="font-size:13px;color:{td};max-width:74ch;margin:0 0 14px">
    Drill into {_html.escape(name)}'s counties on real public demographics
    (County Health Rankings / Census ACS). Click any column to re-sort. The
    footer shows the state total population and population-weighted means.
    Counties missing a value show &ldquo;&mdash;&rdquo;; nothing is fabricated.
  </p>
  {form}
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
    return chartis_shell(body, f"County Explorer — {name}", active_nav="/county-explorer")
