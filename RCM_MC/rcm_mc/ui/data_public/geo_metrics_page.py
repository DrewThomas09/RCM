"""Geographic Intelligence — Metrics & Sources reference at /geo-metrics.

A transparency reference for the geo suite: every metric the shared registry
exposes, with its real source, scoring direction, and how many of the 51
jurisdictions (50 states + DC) actually report it. Generated directly from the
``_METRICS`` registry and live ``_raw`` coverage, so it can never drift from
what the analysis pages actually use. No data is fabricated — coverage is a
real count of states with a value on record.
"""
from __future__ import annotations

import html as _html
from typing import Dict

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_page_title
from rcm_mc.ui.data_public.state_compare_page import _METRICS, _VALID, _raw


def _coverage() -> Dict[str, int]:
    """Real count of jurisdictions reporting each metric (no fabrication)."""
    raws = [_raw(s) for s in _VALID]
    cov: Dict[str, int] = {}
    for key, *_rest in _METRICS:
        cov[key] = sum(1 for r in raws
                       if r.get(key) is not None and r[key] == r[key])
    return cov


def _direction_label(higher) -> str:
    if higher is True:
        return "Higher is better"
    if higher is False:
        return "Lower is better"
    return "Neutral (context)"


def render_geo_metrics(params=None) -> str:
    cov = _coverage()
    n_total = len(_VALID)
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]
    pos_c = P["positive"]; warn_c = P["warning"]

    rows = ""
    for i, (key, label, source, _f, higher) in enumerate(_METRICS):
        bg = P["panel_alt"] if i % 2 else P["panel"]
        n = cov.get(key, 0)
        dcol = pos_c if higher is True else warn_c if higher is False else td
        cov_col = tp if n == n_total else (warn_c if n < n_total * 0.9 else td)
        rows += (
            f'<tr>'
            f'<td style="padding:5px 10px;font-size:12px;color:{tp};background:{bg}">{_html.escape(label)}</td>'
            f'<td style="padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{td};background:{bg}">{_html.escape(source)}</td>'
            f'<td style="padding:5px 10px;font-size:11px;color:{dcol};background:{bg}">{_direction_label(higher)}</td>'
            f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
            f'font-size:11px;color:{cov_col};background:{bg}">{n} / {n_total}</td>'
            f'</tr>'
        )

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title("Geographic Intelligence — Metrics & Sources", eyebrow="MARKET INTEL", meta=f"Every metric the state analysis modes use, with its real source and coverage")}
  <p style="font-size:13px;color:{td};max-width:74ch;margin:0 0 14px">
    The {len(_METRICS)} metrics behind State Comparison, Rankings, Profile,
    Similar States and County Explorer — each from a real public dataset. This
    table is generated from the shared metric registry and live coverage, so it
    always matches what the pages compute. &ldquo;Coverage&rdquo; is the real
    number of the {n_total} jurisdictions (50 states + DC) that report the
    metric; nothing is fabricated to fill gaps.
  </p>
  <div style="overflow-x:auto;border:1px solid {border};border-radius:3px">
  <table style="width:100%;border-collapse:collapse">
    <thead><tr>
      <th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Metric</th>
      <th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Source</th>
      <th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Direction</th>
      <th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Coverage</th>
    </tr></thead><tbody>{rows}</tbody></table>
  </div>
  <p style="font-size:10px;color:{fa};margin-top:10px">
    Sources are real public datasets (Census/ACS via County Health Rankings · CMS FFS · HRSA HPSA ·
    CMS SNF CHOW · CMS MA · CDC PLACES · CMS HCAHPS · CMS MSSP · OIG LEIE). &ldquo;Neutral&rdquo;
    metrics are raw counts with no inherent good/bad direction (shown as context, not scored).
    Back to the <a href="/geo-intel" style="color:{ac};text-decoration:none">Geographic Intelligence</a> hub.
  </p>
</div>"""
    return chartis_shell(body, "Geographic Intelligence — Metrics", active_nav="/geo-metrics")
