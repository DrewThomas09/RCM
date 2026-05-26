"""State Profile — /state-profile.

A single-state dossier: every real public-data metric for one state, each shown
with the state's national rank (#k of n ranked) so a partner instantly sees
where it stands. Completes the geographic-intelligence trio with State
Comparison (cross-state) and State Rankings (cross-metric).

Built entirely on the shared metric registry / raw extractor in
``state_compare_page`` — 100% real public data. Metrics with no value on record
for the state show "—" with no rank, and are never fabricated.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Tuple

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_page_title
from rcm_mc.ui.data_public.state_compare_page import (
    _METRIC_BY_KEY,
    _METRICS,
    _VALID,
    _fmt,
    _raw,
)

_DEFAULT = "CA"
_STATE_NAMES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
    "CO":"Colorado","CT":"Connecticut","DE":"Delaware","DC":"District of Columbia",
    "FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois",
    "IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
    "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota",
    "MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
    "NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York",
    "NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon",
    "PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
    "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia",
    "WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming",
}


def _parse_state(params: Dict) -> str:
    raw = (params or {}).get("state", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    s = str(raw).strip().upper()
    return s if s in _VALID else _DEFAULT


def _us_median(vals: List[float]):
    """National median across reporting states — robust to outliers (e.g. CA
    population). Returns None when no state reports the metric."""
    s = sorted(v for v in vals if v is not None and v == v)
    k = len(s)
    if k == 0:
        return None
    mid = k // 2
    return s[mid] if k % 2 else (s[mid - 1] + s[mid]) / 2.0


def _all_ranked() -> Dict[str, List[Tuple[str, float]]]:
    """For every metric, the states that have a value, sorted in the metric's
    natural direction. One _raw pass over the 51 jurisdictions; no fabrication."""
    raws = {s: _raw(s) for s in sorted(_VALID)}
    out: Dict[str, List[Tuple[str, float]]] = {}
    for key, _lbl, _src, _f, higher in _METRICS:
        pairs = [(s, float(r[key])) for s, r in raws.items()
                 if r.get(key) is not None and r[key] == r[key]]
        pairs.sort(key=lambda kv: kv[1], reverse=not (higher is False))
        out[key] = pairs
    return out


def profile_dataframe(state: str):
    """One state's metrics with raw value + national rank, for CSV export.
    Metrics with no value on record get blank value/rank — never fabricated."""
    import pandas as _pd
    ranked = _all_ranked()
    rows = []
    for key, label, source, _f, _h in _METRICS:
        pairs = ranked.get(key, [])
        pos = next((i for i, (s, _) in enumerate(pairs, start=1) if s == state), "")
        val = next((v for s, v in pairs if s == state), "")
        vs = ""
        if val != "":
            med = _us_median([v for _, v in pairs])
            if med:
                vs = round((val - med) / abs(med) * 100.0, 1)
        rows.append({"Metric": label, "Value": val, "VsUSMedianPct": vs,
                     "NationalRank": pos, "Of": len(pairs), "Source": source})
    return _pd.DataFrame(rows, columns=["Metric", "Value", "VsUSMedianPct",
                                        "NationalRank", "Of", "Source"])


def render_state_profile(params: Dict = None) -> str:
    state = _parse_state(params)
    name = _STATE_NAMES.get(state, state)
    ranked = _all_ranked()
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]

    # state picker
    opts = "".join(
        f'<option value="{s}"{" selected" if s == state else ""}>{_html.escape(_STATE_NAMES.get(s,s))} ({s})</option>'
        for s in sorted(_VALID)
    )
    sel = (f'background:{P["panel_alt"]};color:{tp};border:1px solid {border};'
           f'padding:6px 8px;font-family:Inter Tight,sans-serif;font-size:12px;border-radius:2px')
    form = (
        f'<form method="get" action="/state-profile" style="margin-bottom:16px;display:flex;gap:10px;align-items:center">'
        f'<label style="font-size:11px;color:{td}">State '
        f'<select name="state" onchange="this.form.submit()" style="{sel};margin-left:6px">{opts}</select></label>'
        f'<noscript><button type="submit" style="background:{ac};color:#fff;border:none;padding:7px 16px;'
        f'font-family:JetBrains Mono,monospace;font-size:12px;border-radius:2px;cursor:pointer">View</button></noscript>'
        f'<a href="/state-profile.csv?state={state}" '
        f'style="font-size:11px;color:{ac};text-decoration:none;margin-left:4px">Export CSV &#8595;</a>'
        f'</form>'
    )

    pos_c = P["positive"]; warn_c = P["warning"]

    rows = ""
    for i, (key, label, source, _f, higher) in enumerate(_METRICS):
        bg = P["panel_alt"] if i % 2 else P["panel"]
        pairs = ranked.get(key, [])
        n = len(pairs)
        pos = next((idx for idx, (s, _) in enumerate(pairs, start=1) if s == state), None)
        val = next((v for s, v in pairs if s == state), None)
        val_str = _fmt(key, val) if val is not None else "—"
        if pos is None or n == 0:
            rank_cell = '<span style="opacity:0.6">unranked</span>'
        else:
            # contextual phrasing for the directional metrics
            if higher is False:
                hint = "lowest = best"
            elif higher:
                hint = "highest first"
            else:
                hint = "largest first"
            rank_cell = (f'#{pos} <span style="color:{fa}">of {n}</span> '
                         f'<span style="color:{fa};font-size:9px">· {hint}</span>')

        # vs U.S. median — robust to outliers (e.g. CA population). Tinted by
        # the metric's direction: better-than-median = positive, worse = warning;
        # neutral metrics (no inherent good/bad direction) stay un-tinted.
        med = _us_median([v for _, v in pairs])
        if val is None or med is None or med == 0:
            vs_cell = '<span style="opacity:0.55">—</span>'
        else:
            delta = (val - med) / abs(med) * 100.0
            arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "·")
            if higher is None:
                col = td
            else:
                better = (delta > 0) if higher else (delta < 0)
                col = pos_c if delta != 0 and better else (warn_c if delta != 0 else td)
            vs_cell = f'<span style="color:{col}">{arrow} {abs(delta):.0f}%</span>'

        rows += (
            f'<tr>'
            f'<td style="padding:5px 10px;font-size:11px;color:{td};background:{bg}">{_html.escape(label)}</td>'
            f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
            f'font-size:12px;font-variant-numeric:tabular-nums;color:{tp};background:{bg}">{_html.escape(val_str)}</td>'
            f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
            f'font-size:11px;background:{bg};white-space:nowrap">{vs_cell}</td>'
            f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
            f'font-size:11px;color:{td};background:{bg};white-space:nowrap">{rank_cell}</td>'
            f'<td style="padding:5px 10px;font-size:10px;color:{fa};background:{bg}">{_html.escape(source)}</td>'
            f'</tr>'
        )

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title(f"State Profile — {name}", eyebrow="MARKET INTEL", meta=f"Every real public-data metric for {name} ({state}), with its national rank")}
  <p style="font-size:13px;color:{td};max-width:72ch;margin:0 0 14px">
    A single-state dossier across PEdesk's real public-data layers — each metric
    shown with {_html.escape(name)}'s gap to the U.S. median and its national rank
    among the states that report it. Better-than-median is tinted positive, worse
    is tinted amber (neutral metrics are left un-tinted). Every figure is real and
    sourced; metrics with no value on record show &ldquo;&mdash;&rdquo; and are
    left unranked, never fabricated.
  </p>
  {form}
  <div style="overflow-x:auto;border:1px solid {border};border-radius:3px">
  <table style="width:100%;border-collapse:collapse">
    <thead><tr>
      <th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Metric</th>
      <th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">{_html.escape(name)}</th>
      <th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">vs U.S. median</th>
      <th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">National rank</th>
      <th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Source</th>
    </tr></thead><tbody>{rows}</tbody></table>
  </div>
  <p style="font-size:10px;color:{fa};margin-top:10px">
    Sources: Census/ACS · CMS FFS · HRSA HPSA · CMS CHOW · CMS MA · CDC PLACES · CMS HCAHPS.
    Area-level public data — a screening signal, not a deal-level figure.
    Compare states side by side on <a href="/state-compare?states={state}" style="color:{ac};text-decoration:none">State Comparison &rarr;</a>
    or rank all states on one metric in <a href="/state-rankings" style="color:{ac};text-decoration:none">State Rankings &rarr;</a>
  </p>
</div>"""
    return chartis_shell(body, f"State Profile — {name}", active_nav="/state-profile")
