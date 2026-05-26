"""State Rankings — /state-rankings.

A deal-origination screening mode: pick any one real public-data metric and
rank all 50 states + DC, highest to lowest (or lowest-first for "less is
better" metrics like uninsured rate or provider-shortage areas), with an
inline bar for scale.

Reuses the shared metric registry and raw extractor in ``state_compare_page``
so the comparison table and this leaderboard never drift. 100% real public
data — states with no value on record for the chosen metric are listed
separately as "no data on record", never given a fabricated number or rank.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_page_title
from rcm_mc.ui.data_public.state_compare_page import (
    _METRIC_BY_KEY,
    _METRICS,
    _VALID,
    _fmt,
    _raw,
)

_DEFAULT_METRIC = "uninsured_acs"


def _parse_metric(params: Dict) -> str:
    raw = (params or {}).get("metric", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    key = str(raw).strip()
    return key if key in _METRIC_BY_KEY else _DEFAULT_METRIC


def _ranking(key: str):
    """Return (ranked, missing): ranked is a list of (state, value) sorted by
    the metric's natural direction; missing is the states with no value."""
    pairs: List = []
    missing: List[str] = []
    for s in sorted(_VALID):
        v = _raw(s).get(key)
        if v is None or v != v:
            missing.append(s)
        else:
            pairs.append((s, float(v)))
    higher_is_better = _METRIC_BY_KEY[key][4]
    # default to descending; for "lower is better" metrics, ascending puts the
    # best (lowest-burden) state first. None (neutral) → descending by size.
    reverse = not (higher_is_better is False)
    pairs.sort(key=lambda kv: kv[1], reverse=reverse)
    return pairs, missing


def rankings_dataframe(key: str):
    """Ranked (state, raw value) table for CSV export. States with no value are
    omitted — never given a fabricated number or rank."""
    import pandas as _pd
    ranked, _missing = _ranking(key)
    label = _METRIC_BY_KEY[key][1]; source = _METRIC_BY_KEY[key][2]
    rows = [{"Rank": i, "State": s, label: v, "Source": source}
            for i, (s, v) in enumerate(ranked, start=1)]
    return _pd.DataFrame(rows, columns=["Rank", "State", label, "Source"])


def render_state_rankings(params: Dict = None) -> str:
    key = _parse_metric(params)
    label, source, _, higher_is_better = (
        _METRIC_BY_KEY[key][1], _METRIC_BY_KEY[key][2],
        _METRIC_BY_KEY[key][3], _METRIC_BY_KEY[key][4],
    )
    ranked, missing = _ranking(key)
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]
    vmax = max((v for _, v in ranked), default=0) or 1

    # metric picker
    opts = "".join(
        f'<option value="{k}"{" selected" if k == key else ""}>{_html.escape(lbl)}</option>'
        for k, lbl, _src, _f, _h in _METRICS
    )
    sel = (f'background:{P["panel_alt"]};color:{tp};border:1px solid {border};'
           f'padding:6px 8px;font-family:Inter Tight,sans-serif;font-size:12px;border-radius:2px')
    form = (
        f'<form method="get" action="/state-rankings" style="margin-bottom:16px;display:flex;gap:10px;align-items:center">'
        f'<label style="font-size:11px;color:{td}">Rank states by '
        f'<select name="metric" onchange="this.form.submit()" style="{sel};margin-left:6px">{opts}</select></label>'
        f'<noscript><button type="submit" style="background:{ac};color:#fff;border:none;padding:7px 16px;'
        f'font-family:JetBrains Mono,monospace;font-size:12px;border-radius:2px;cursor:pointer">Rank</button></noscript>'
        f'<a href="/state-rankings.csv?metric={_html.escape(key)}" '
        f'style="font-size:11px;color:{ac};text-decoration:none;margin-left:4px">Export CSV &#8595;</a>'
        f'</form>'
    )

    direction = ("lower is better — best (lowest) first" if higher_is_better is False
                 else "higher first" if higher_is_better else "largest first")

    rows = ""
    for i, (s, v) in enumerate(ranked, start=1):
        bg = P["panel_alt"] if i % 2 == 0 else P["panel"]
        barw = max(2, round((v / vmax) * 100))
        rows += (
            f'<tr>'
            f'<td style="padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:12px;'
            f'color:{td};background:{bg};text-align:right;width:36px">{i}</td>'
            f'<td style="padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:13px;'
            f'color:{tp};background:{bg};width:48px">{_html.escape(s)}</td>'
            f'<td style="padding:5px 10px;background:{bg};width:46%">'
            f'<div style="height:9px;width:{barw}%;background:{ac};opacity:0.78;border-radius:1px"></div></td>'
            f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
            f'font-size:12px;font-variant-numeric:tabular-nums;color:{tp};background:{bg}">{_html.escape(_fmt(key, v))}</td>'
            f'</tr>'
        )

    miss = ""
    if missing:
        miss = (
            f'<p style="font-size:10px;color:{fa};margin-top:10px">'
            f'No data on record for this metric ({len(missing)}): '
            f'{_html.escape(", ".join(missing))} — listed honestly, not ranked or estimated.</p>'
        )

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title("State Rankings", eyebrow="MARKET INTEL", meta="Screen all 50 states + DC on one real public-data metric")}
  <p style="font-size:13px;color:{td};max-width:72ch;margin:0 0 14px">
    Origination screening across PEdesk's real public-data layers — pick a metric
    and rank every state. Currently ranking by <b style="color:{tp}">{_html.escape(label)}</b>
    ({_html.escape(source)}, {direction}). Every figure is real and sourced; states
    without a value on record are listed separately, never given a fabricated number.
  </p>
  {form}
  <div style="overflow-x:auto;border:1px solid {border};border-radius:3px">
  <table style="width:100%;border-collapse:collapse">
    <thead><tr>
      <th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">#</th>
      <th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">State</th>
      <th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Relative</th>
      <th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">{_html.escape(label)}</th>
    </tr></thead><tbody>{rows}</tbody></table>
  </div>
  {miss}
  <p style="font-size:10px;color:{fa};margin-top:10px">
    Source: {_html.escape(source)}. Area-level public data — a screening signal, not a
    deal-level figure; combine with deal-specific data before any decision.
    Compare a shortlist side by side on <a href="/state-compare" style="color:{ac};text-decoration:none">State Comparison &rarr;</a>
  </p>
</div>"""
    return chartis_shell(body, "State Rankings", active_nav="/state-rankings")
