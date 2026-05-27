"""Geo Map — /geo-map.

A US choropleth (tile-grid cartogram) view of the Geographic Intelligence
suite: shade all 50 states + DC by any one of the real shared-registry metrics,
for instant geographic pattern recognition. Clicking a state drills into its
State Profile.

100% real public data via the shared ``_METRICS``/``_raw`` layer — states with
no value on record render as "no data" (neutral), never invented. Reuses the
local inline-SVG ``render_us_geo_map`` real geographic map (no external map tiles).
"""
from __future__ import annotations

import html as _html
from typing import Dict

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_page_title
from rcm_mc.ui.us_geo_map import render_us_geo_map
from rcm_mc.ui.data_public.state_compare_page import (
    _METRIC_BY_KEY,
    _METRICS,
    _VALID,
    _raw,
)

_DEFAULT_METRIC = "uninsured_acs"


def _parse_metric(params: Dict) -> str:
    raw = (params or {}).get("metric", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    k = str(raw).strip()
    return k if k in _METRIC_BY_KEY else _DEFAULT_METRIC


def _state_values(key: str) -> Dict[str, float]:
    """{state: real value} for every state reporting the metric (never invented)."""
    out: Dict[str, float] = {}
    for s in sorted(_VALID):
        v = _raw(s).get(key)
        if v is not None and v == v:
            out[s] = float(v)
    return out


def render_geo_map(params: Dict = None) -> str:
    key = _parse_metric(params)
    label, source, fmt, higher = (
        _METRIC_BY_KEY[key][1], _METRIC_BY_KEY[key][2],
        _METRIC_BY_KEY[key][3], _METRIC_BY_KEY[key][4],
    )
    values = _state_values(key)
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]

    opts = "".join(
        f'<option value="{k}"{" selected" if k == key else ""}>{_html.escape(lbl)}</option>'
        for k, lbl, _src, _f, _h in _METRICS
    )
    sel = (f'background:{P["panel_alt"]};color:{tp};border:1px solid {border};'
           f'padding:6px 8px;font-family:Inter Tight,sans-serif;font-size:12px;border-radius:2px')
    form = (
        f'<form method="get" action="/geo-map" style="margin-bottom:14px;display:flex;gap:10px;align-items:center">'
        f'<label style="font-size:11px;color:{td}">Shade states by '
        f'<select name="metric" onchange="this.form.submit()" style="{sel};margin-left:6px">{opts}</select></label>'
        f'<noscript><button type="submit" style="background:{ac};color:#fff;border:none;padding:7px 16px;'
        f'font-family:JetBrains Mono,monospace;font-size:12px;border-radius:2px;cursor:pointer">Map</button></noscript>'
        f'</form>'
    )

    direction = ("lower = lighter (lower is better)" if higher is False
                 else "higher = darker" if higher else "darker = larger")
    cartogram = render_us_geo_map(
        values, metric_label=label, value_format=fmt,
        state_link_template="/state-profile?state={state}",
        empty_message="No data on record for this metric.",
    )

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title("Geo Map", eyebrow="MARKET INTEL", meta=f"All 50 states + DC shaded by a real metric — click a state for its profile")}
  <p style="font-size:13px;color:{td};max-width:74ch;margin:0 0 12px">
    A geographic view of the Geographic Intelligence suite — every state shaded
    by <b style="color:{tp}">{_html.escape(label)}</b> ({_html.escape(source)};
    {direction}). It's the real US geographic map. Click a state to open its full profile. Real public data only;
    states with no value on record show as &ldquo;no data&rdquo;, never invented.
  </p>
  {form}
  {cartogram}
  <p style="font-size:10px;color:{fa};margin-top:12px">
    Source: {_html.escape(source)} (via the shared real-metric layer). Area-level —
    a screening signal, not a deal-level figure. Compare a shortlist on
    <a href="/state-compare" style="color:{ac};text-decoration:none">State Comparison &rarr;</a>,
    rank all states on <a href="/state-rankings?metric={_html.escape(key)}" style="color:{ac};text-decoration:none">State Rankings &rarr;</a>,
    or see every metric's source on <a href="/geo-metrics" style="color:{ac};text-decoration:none">Metrics &amp; Sources &rarr;</a>.
  </p>
</div>"""
    return chartis_shell(body, "Geo Map", active_nav="/geo-map")
