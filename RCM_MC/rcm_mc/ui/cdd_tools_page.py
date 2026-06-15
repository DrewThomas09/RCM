"""CDD Analytics Engines catalog — /cdd/tools.

The /cdd hub is a navigation map over the desk's existing surfaces, but the
rcm_mc.cdd registry (TAM/SAM, PVM bridge, payer mix, HCC/RAF, the McKinsey
profit-pool exhibits, the granular benchmarking reference layer, and the
platform bolsters) had no single surface that renders the engines themselves.
An associate could run them only from the CLI (python -m rcm_mc.cdd). This page
enumerates every registered feature and renders its partner-safe exhibit so the
whole analytics catalog is browsable in the app.

The render uses the audience-aware Exhibit contract: every card shows the
partner view (internal_mode=False), so assumption nodes and internal-only series
never reach this surface. Each feature is rendered defensively so one broken
engine cannot blank the catalog.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Tuple

from rcm_mc.ui._chartis_kit import (
    chartis_shell, ck_page_explainer, ck_page_title, ck_signal_badge,
)

# Feature-id prefix to the human group it belongs to, in display order.
_GROUPS: List[Tuple[str, str, str]] = [
    ("REF-", "Benchmarking reference layer",
     "Chart-ready, sourced benchmark data: quality-measure weights, code and "
     "procedure frequency, compensation, cost structure, prevalence, spending."),
    ("NEW-", "Analytics exhibits",
     "The commercial-diligence analytic engines, from market sizing through "
     "the McKinsey profit-pool exhibits."),
    ("PACK-", "Composite packs",
     "Multi-exhibit diligence packs that chain the engines for one deal."),
    ("BOLSTER-", "Platform engines",
     "Forecasting, anomaly, changepoint, and reconciliation engines that "
     "bolster the analytics core."),
]

_FLAG_TONE = {"risk": "negative", "warn": "warning", "info": "neutral"}
_MAX_POINTS = 6  # cap rows per series so a card stays scannable


def _group_for(feature_id: str) -> int:
    for idx, (prefix, _, _) in enumerate(_GROUPS):
        if feature_id.startswith(prefix):
            return idx
    return len(_GROUPS)  # anything unprefixed falls into a trailing bucket


def _fmt_value(v: Any) -> str:
    """Format a numeric payload value for display, escaped.

    Counts render without decimals, fractional values to at most two places, so
    a percentage, a dollar figure, and a discharge count each read cleanly in
    the same column.
    """
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int,)) or (isinstance(v, float) and float(v).is_integer()):
        return _html.escape(f"{int(v):,}")
    if isinstance(v, float):
        return _html.escape(f"{v:,.2f}")
    return _html.escape(str(v))


def _render_series(series: List[Dict[str, Any]]) -> str:
    blocks = []
    for s in series:
        name = _html.escape(str(s.get("name", "")))
        points = s.get("points", []) or []
        rows = []
        for pt in points[:_MAX_POINTS]:
            label = _html.escape(str(pt.get("label", "")))
            # A point may carry value, or low/high for a range bar.
            if "value" in pt:
                val = _fmt_value(pt.get("value"))
            elif "low" in pt and "high" in pt:
                val = f"{_fmt_value(pt.get('low'))} to {_fmt_value(pt.get('high'))}"
            else:
                val = ""
            rows.append(
                f'<tr><td class="cdt-lbl">{label}</td>'
                f'<td class="cdt-val num">{val}</td></tr>')
        extra = len(points) - _MAX_POINTS
        more = (f'<tr><td class="cdt-more" colspan="2">'
                f'{extra} more not shown</td></tr>') if extra > 0 else ""
        kind = _html.escape(str(s.get("kind", "bar")))
        blocks.append(
            f'<div class="cdt-series">'
            f'<div class="cdt-series-h">{name} '
            f'<span class="cdt-kind">{kind}</span></div>'
            f'<table class="cdt-table">{"".join(rows)}{more}</table>'
            f'</div>')
    return "".join(blocks)


def _render_flags(flags: List[Dict[str, Any]]) -> str:
    if not flags:
        return ""
    badges = []
    for f in flags:
        tone = _FLAG_TONE.get(str(f.get("severity", "info")), "neutral")
        badges.append(ck_signal_badge(str(f.get("code", "")), tone=tone))
    lines = "".join(
        f'<li>{_html.escape(str(f.get("message", "")))}</li>' for f in flags)
    return (f'<div class="cdt-flags">{" ".join(badges)}'
            f'<ul class="cdt-flag-list">{lines}</ul></div>')


def _render_footnote(fn: Dict[str, Any]) -> str:
    if not fn:
        return ""
    source = _html.escape(str(fn.get("source", "")))
    vintage = _html.escape(str(fn.get("vintage", "")))
    assumptions = fn.get("assumptions", []) or []
    items = "".join(f'<li>{_html.escape(str(a))}</li>' for a in assumptions)
    return (f'<div class="cdt-foot">'
            f'<div class="cdt-foot-src">Source: {source} · {vintage}</div>'
            f'<ul class="cdt-foot-asm">{items}</ul></div>')


def _render_card(rendered: Dict[str, Any]) -> str:
    fid = _html.escape(str(rendered.get("feature_id", "")))
    title = _html.escape(str(rendered.get("title", "")))
    audience = _html.escape(str(rendered.get("audience", "both")))
    summary = _html.escape(str(rendered.get("summary", "")))
    series = rendered.get("series", []) or []
    flags = rendered.get("flags", []) or []
    recs = rendered.get("reconciliations", []) or []

    if rendered.get("reconciled", True) and recs:
        rec_badge = ck_signal_badge("reconciled", tone="positive")
    elif recs:
        rec_badge = ck_signal_badge("check reconciliation", tone="warning")
    else:
        rec_badge = ""
    rec_ids = "".join(
        f'<li>{_html.escape(str(r.get("identity", "")))}</li>' for r in recs)
    rec_html = (f'<div class="cdt-rec">{rec_badge}'
                f'<ul class="cdt-rec-list">{rec_ids}</ul></div>') if recs else ""

    return (
        f'<section class="cdt-card" id="{fid}">'
        f'<div class="cdt-card-top">'
        f'<span class="cdt-fid">{fid}</span>'
        f'<span class="cdt-aud">{audience}</span></div>'
        f'<h3 class="cdt-title">{title}</h3>'
        f'<p class="cdt-sum">{summary}</p>'
        f'{_render_series(series)}'
        f'{rec_html}'
        f'{_render_flags(flags)}'
        f'{_render_footnote(rendered.get("footnote"))}'
        f'</section>')


def _catalog() -> Tuple[List[Tuple[str, str, str, List[Dict[str, Any]]]], int]:
    """Render every registered feature into grouped, partner-safe payloads.

    Returns (groups, n_features) where each group is
    (prefix, title, blurb, [rendered_exhibit, ...]). Import is local so a
    missing optional dependency in the registry never breaks page import.
    """
    from rcm_mc.cdd import registry

    buckets: Dict[int, List[Dict[str, Any]]] = {}
    n = 0
    for feat in registry.all_features():
        try:
            rendered = feat.demo().render(internal_mode=False)
        except Exception:  # noqa: BLE001 - one broken engine must not blank the catalog
            continue
        buckets.setdefault(_group_for(feat.feature_id), []).append(rendered)
        n += 1

    groups: List[Tuple[str, str, str, List[Dict[str, Any]]]] = []
    for idx, (prefix, title, blurb) in enumerate(_GROUPS):
        items = sorted(buckets.get(idx, []), key=lambda r: r.get("feature_id", ""))
        if items:
            groups.append((prefix, title, blurb, items))
    return groups, n


def render_cdd_tools(params: dict = None) -> str:
    groups, n_features = _catalog()

    sections = []
    for _, title, blurb, items in groups:
        cards = "".join(_render_card(r) for r in items)
        sections.append(
            f'<section class="cdt-group">'
            f'<h2 class="cdt-group-h">{_html.escape(title)} '
            f'<span class="cdt-group-n">{len(items)}</span></h2>'
            f'<p class="cdt-group-blurb">{_html.escape(blurb)}</p>'
            f'<div class="cdt-grid">{cards}</div>'
            f'</section>')

    page_title = ck_page_title(
        "CDD Analytics Engines",
        eyebrow="DILIGENCE · CDD CATALOG",
        meta=(f"{n_features} registered engines · partner view · "
              "every exhibit carries a sourced footnote and reconciliation"),
    )
    explainer = ck_page_explainer(
        "Every CDD engine, rendered, in one place.",
        "This catalog enumerates the analytics registry and renders each "
        "engine's partner-facing exhibit: the chart-ready series, the "
        "reconciliation that ties the numbers to their source, the diligence "
        "flags, and the sourced footnote. It is the same surface the CLI and "
        "server run, so what you see here is exactly what an exhibit emits.",
    )
    css = """
<style>
.cdt-group { margin: 26px 0; }
.cdt-group-h { font-size: 20px; margin: 0 0 4px; color: #0b2341; }
.cdt-group-n { font-size: 13px; color: #155752; font-weight: 600; }
.cdt-group-blurb { margin: 0 0 12px; color: #4a5568; font-style: italic; max-width: 74ch; }
.cdt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
.cdt-card { background: #fffdf9; border: 1px solid #d8d2c4; border-radius: 6px; padding: 14px 16px; }
.cdt-card-top { display: flex; justify-content: space-between; align-items: center; }
.cdt-fid { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #155752; letter-spacing: 0.04em; }
.cdt-aud { font-size: 10.5px; text-transform: uppercase; color: #8a8170; letter-spacing: 0.06em; }
.cdt-title { font-size: 15px; color: #0b2341; margin: 4px 0 4px; }
.cdt-sum { font-size: 12.5px; line-height: 1.45; color: #1a2332; margin: 0 0 10px; }
.cdt-series { margin: 8px 0; }
.cdt-series-h { font-size: 11.5px; font-weight: 600; color: #155752; margin-bottom: 3px; }
.cdt-kind { font-size: 10px; color: #8a8170; font-weight: 400; }
.cdt-table { width: 100%; border-collapse: collapse; }
.cdt-table td { font-size: 11.5px; padding: 2px 0; border-bottom: 1px solid #efe9dc; }
.cdt-lbl { color: #1a2332; padding-right: 8px; }
.cdt-val { text-align: right; color: #0b2341; font-variant-numeric: tabular-nums; white-space: nowrap; }
.cdt-more { font-size: 10.5px; color: #8a8170; font-style: italic; }
.cdt-rec, .cdt-flags, .cdt-foot { margin-top: 10px; }
.cdt-rec-list, .cdt-flag-list, .cdt-foot-asm { margin: 5px 0 0; padding-left: 16px; }
.cdt-rec-list li, .cdt-foot-asm li { font-size: 11px; color: #4a5568; line-height: 1.4; }
.cdt-flag-list li { font-size: 11px; color: #1a2332; line-height: 1.4; }
.cdt-foot { border-top: 1px solid #efe9dc; padding-top: 8px; }
.cdt-foot-src { font-size: 10.5px; color: #8a8170; font-family: 'JetBrains Mono', monospace; }
</style>"""
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {explainer}
  {''.join(sections)}
</div>"""
    return chartis_shell(body, title="CDD Analytics Engines",
                         active_nav="/cdd", extra_css=css)
