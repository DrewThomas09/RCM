"""Similar States — /state-peers.

A comp-set / origination mode: given one state, find the states whose real
public-data profile is most similar. "If the thesis works in Ohio, where else
looks like Ohio?" Similarity is a transparent, standardized (z-score) Euclidean
distance over the shared metrics both states report — a derived measure clearly
labelled as such, computed only from real data (never a fabricated score).

Built on the shared metric registry / raw extractor in ``state_compare_page``.
States that share too few metrics with the target are listed separately rather
than given a misleading similarity.
"""
from __future__ import annotations

import html as _html
import math
from typing import Dict, List, Tuple

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_page_title
from rcm_mc.ui.data_public.state_compare_page import _METRICS, _VALID, _raw
from rcm_mc.ui.data_public.state_profile_page import _STATE_NAMES

_DEFAULT = "OH"
_MIN_SHARED = 6  # need enough overlapping metrics for a meaningful distance


def _parse_state(params: Dict) -> str:
    raw = (params or {}).get("state", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    s = str(raw).strip().upper()
    return s if s in _VALID else _DEFAULT


def _zstats() -> Dict[str, Tuple[float, float]]:
    """Per-metric (mean, stdev) across all reporting states, for standardizing."""
    raws = [_raw(s) for s in sorted(_VALID)]
    stats: Dict[str, Tuple[float, float]] = {}
    for key, *_rest in _METRICS:
        vals = [r[key] for r in raws if r.get(key) is not None and r[key] == r[key]]
        n = len(vals)
        if n >= 2:
            mean = sum(vals) / n
            var = sum((v - mean) ** 2 for v in vals) / n
            sd = math.sqrt(var)
            if sd > 0:
                stats[key] = (mean, sd)
    return stats


def rank_peers(state: str):
    """Return (peers, thin): peers is [(other_state, distance, n_shared)] sorted
    closest-first; thin is states sharing < _MIN_SHARED metrics with the target."""
    stats = _zstats()
    raws = {s: _raw(s) for s in sorted(_VALID)}
    target = raws.get(state, {})

    def _z(key, val):
        mean, sd = stats[key]
        return (val - mean) / sd

    peers: List[Tuple[str, float, int]] = []
    thin: List[str] = []
    for s in sorted(_VALID):
        if s == state:
            continue
        other = raws[s]
        sq = 0.0; shared = 0
        for key in stats:
            tv = target.get(key); ov = other.get(key)
            if tv is None or ov is None or tv != tv or ov != ov:
                continue
            sq += (_z(key, tv) - _z(key, ov)) ** 2
            shared += 1
        if shared < _MIN_SHARED:
            thin.append(s)
        else:
            # normalize by shared count so coverage differences don't distort
            peers.append((s, math.sqrt(sq / shared), shared))
    peers.sort(key=lambda t: t[1])
    return peers, thin


def peers_dataframe(state: str):
    """Ranked peer table for CSV export: rank, state, distance, shared-metric
    count. States sharing too few metrics are omitted — never given a score."""
    import pandas as _pd
    peers, _thin = rank_peers(state)
    rows = [{"Rank": i, "State": s, "Name": _STATE_NAMES.get(s, s),
             "Distance": round(d, 4), "SharedMetrics": n}
            for i, (s, d, n) in enumerate(peers, start=1)]
    return _pd.DataFrame(rows, columns=["Rank", "State", "Name", "Distance", "SharedMetrics"])


def render_state_peers(params: Dict = None) -> str:
    state = _parse_state(params)
    name = _STATE_NAMES.get(state, state)
    peers, thin = rank_peers(state)
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]

    # picker
    opts = "".join(
        f'<option value="{s}"{" selected" if s == state else ""}>{_html.escape(_STATE_NAMES.get(s,s))} ({s})</option>'
        for s in sorted(_VALID)
    )
    sel = (f'background:{P["panel_alt"]};color:{tp};border:1px solid {border};'
           f'padding:6px 8px;font-family:Inter Tight,sans-serif;font-size:12px;border-radius:2px')
    form = (
        f'<form method="get" action="/state-peers" style="margin-bottom:16px;display:flex;gap:10px;align-items:center">'
        f'<label style="font-size:11px;color:{td}">Most similar to '
        f'<select name="state" onchange="this.form.submit()" style="{sel};margin-left:6px">{opts}</select></label>'
        f'<noscript><button type="submit" style="background:{ac};color:#fff;border:none;padding:7px 16px;'
        f'font-family:JetBrains Mono,monospace;font-size:12px;border-radius:2px;cursor:pointer">Find</button></noscript>'
        f'<a href="/state-peers.csv?state={state}" '
        f'style="font-size:11px;color:{ac};text-decoration:none;margin-left:4px">Export CSV &#8595;</a>'
        f'</form>'
    )

    dmax = max((d for _, d, _ in peers), default=1) or 1
    rows = ""
    for i, (s, dist, shared) in enumerate(peers, start=1):
        bg = P["panel_alt"] if i % 2 == 0 else P["panel"]
        # similarity 0–100 (closer distance → higher); purely a relative display
        sim = max(0, round((1 - dist / dmax) * 100))
        barw = max(2, sim)
        rows += (
            f'<tr>'
            f'<td style="padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:12px;'
            f'color:{td};background:{bg};text-align:right;width:36px">{i}</td>'
            f'<td style="padding:5px 10px;font-size:12px;color:{tp};background:{bg}">'
            f'<a href="/state-profile?state={s}" style="color:{tp};text-decoration:none">{_html.escape(_STATE_NAMES.get(s,s))} '
            f'<span style="color:{fa};font-family:JetBrains Mono,monospace;font-size:10px">{s}</span></a></td>'
            f'<td style="padding:5px 10px;background:{bg};width:40%">'
            f'<div style="height:9px;width:{barw}%;background:{ac};opacity:0.78;border-radius:1px"></div></td>'
            f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
            f'font-size:11px;color:{td};background:{bg}">{dist:.2f}<span style="color:{fa};font-size:9px"> · {shared} metrics</span></td>'
            f'</tr>'
        )

    thin_note = ""
    if thin:
        thin_note = (
            f'<p style="font-size:10px;color:{fa};margin-top:10px">'
            f'Too few shared metrics for a reliable comparison ({len(thin)}): '
            f'{_html.escape(", ".join(thin))} — listed honestly, not scored.</p>'
        )

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title(f"Similar States — {name}", eyebrow="MARKET INTEL", meta=f"States whose real public-data profile is closest to {name}")}
  <p style="font-size:13px;color:{td};max-width:74ch;margin:0 0 14px">
    A comp-set read for origination: which states most resemble <b style="color:{tp}">{_html.escape(name)}</b>
    across PEdesk's real public-data layers? Similarity is a <i>derived</i> measure —
    standardized (z-score) Euclidean distance over the metrics both states report,
    normalized by the number shared. Smaller distance = more alike. It is computed
    only from real data; no score is fabricated, and states sharing too few metrics
    are listed separately.
  </p>
  {form}
  <div style="overflow-x:auto;border:1px solid {border};border-radius:3px">
  <table style="width:100%;border-collapse:collapse">
    <thead><tr>
      <th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">#</th>
      <th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">State</th>
      <th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Similarity</th>
      <th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Distance</th>
    </tr></thead><tbody>{rows}</tbody></table>
  </div>
  {thin_note}
  <p style="font-size:10px;color:{fa};margin-top:10px">
    Derived from real public data (Census/ACS · CMS · HRSA · CDC PLACES · HCAHPS).
    A screening heuristic for building a comp set — not a deal-level judgment.
    Inspect any peer on <a href="/state-profile?state={state}" style="color:{ac};text-decoration:none">State Profile &rarr;</a>
    or compare a shortlist on <a href="/state-compare?states={state}" style="color:{ac};text-decoration:none">State Comparison &rarr;</a>
  </p>
</div>"""
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, f"Similar States — {name}", active_nav="/state-peers")
