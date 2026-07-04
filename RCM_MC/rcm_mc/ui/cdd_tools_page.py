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
from typing import Any, Dict, List, Optional, Tuple

from rcm_mc.ui._chartis_kit import (
    chartis_shell, ck_empty_state, ck_page_explainer, ck_page_title,
    ck_signal_badge,
)
from rcm_mc.ui.cdd_chart_kit import chart_export_toolbar, render_cdd_chart

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
        f'<a class="cdt-fid" href="/cdd/tools/{fid}">{fid}</a>'
        f'<span class="cdt-aud">{audience}</span></div>'
        f'<h3 class="cdt-title">'
        f'<a class="cdt-title-link" href="/cdd/tools/{fid}">{title}</a></h3>'
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
.cdt-fid { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #155752; letter-spacing: 0.04em; text-decoration: none; }
.cdt-fid:hover { text-decoration: underline; }
.cdt-aud { font-size: 10.5px; text-transform: uppercase; color: #8a8170; letter-spacing: 0.06em; }
.cdt-title { font-size: 15px; color: #0b2341; margin: 4px 0 4px; }
.cdt-title-link { color: #0b2341; text-decoration: none; }
.cdt-title-link:hover { color: #155752; text-decoration: underline; }
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
                         active_nav="/cdd/tools", extra_css=css)


# ── Per-engine drill-down (/cdd/tools/<feature_id>) ──────────────────
#
# The catalog above renders every engine inline. From a card a partner can
# open one engine on its own page to see a chart of the leading series, the
# full data tables, the reconciliation math, and (with ?internal=1) the
# assumption nodes the partner view strips. This is the drill-down the
# single-page catalog cannot show without becoming unscannable.

# Exhibit series kind -> CDD chart-kit chart type. Kinds without a faithful
# 2D chart (a choropleth needs a map) fall back to a column so the numbers
# still render rather than dropping the series.
_KIND_TO_CHART = {
    "bar": "column",
    "line": "line",
    "waterfall": "waterfall",
    "scatter": "scatter",
    "bubble": "bubble",
    "choropleth": "column",
}


def _family(feature_id: str) -> str:
    """Group key: the prefix before the first hyphen (NEW, BOLSTER, PACK, REF)."""
    return feature_id.split("-", 1)[0] if "-" in feature_id else feature_id


def _num(value: Any) -> str:
    """Detail-page number formatting. Keeps four decimals for fractional
    values so a reconciliation gap of 1e-9 does not display as 0.00."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _html.escape(str(value))
    if float(value).is_integer() and abs(value) < 1e15:
        return f"{value:,.0f}"
    return f"{value:,.4f}"


def _chart_for_series(series: Dict[str, Any], title: str,
                      source: str) -> Optional[str]:
    """Render the first chartable series as an SVG, or None when the points
    do not carry a numeric ``value`` per labelled row."""
    points = series.get("points") or []
    rows = []
    for p in points:
        if not isinstance(p, dict) or "value" not in p:
            return None
        val = p.get("value")
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            return None
        label = p.get("label")
        if label is None:
            label = p.get("year", p.get("rank", ""))
        rows.append((str(label), [float(val)]))
    if not rows:
        return None
    chart_type = _KIND_TO_CHART.get(series.get("kind", "bar"), "column")
    table = {"headers": ["category", series.get("name", "value")], "rows": rows}
    return render_cdd_chart(chart_type, table,
                            {"title": title, "source": source})


def _series_table(series: Dict[str, Any]) -> str:
    points = series.get("points") or []
    if not points:
        return '<p class="cdt-muted">No rows.</p>'
    keys: List[str] = []
    for p in points:
        if isinstance(p, dict):
            for k in p:
                if k not in keys:
                    keys.append(k)
    ordered = ([k for k in ("label",) if k in keys]
               + [k for k in keys if k != "label"])
    head = "".join(f"<th>{_html.escape(k)}</th>" for k in ordered)
    body_rows = []
    for p in points[:60]:
        cells = "".join(
            f'<td class="num">{_num(p.get(k)) if isinstance(p, dict) else ""}</td>'
            for k in ordered)
        body_rows.append(f"<tr>{cells}</tr>")
    more = ("" if len(points) <= 60
            else f'<p class="cdt-muted">{len(points) - 60} more rows not shown.</p>')
    return (f'<table class="cdt-dtable"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body_rows)}</tbody></table>{more}')


def render_cdd_tool_detail(feature_id: str,
                          params: Optional[Dict[str, Any]] = None) -> str:
    """One engine's demo exhibit on its own page, partner (default) or
    internal (?internal=1) render. Import of the registry is local so a
    missing optional dependency never breaks page import."""
    from rcm_mc.cdd import registry

    params = params or {}
    internal = str(params.get("internal", "")).strip() in ("1", "true", "yes")

    try:
        feat = registry.get(feature_id)
    except KeyError:
        body = (f'<div class="ck-page-wrap">'
                f'{ck_page_title("Tool not found", eyebrow="DILIGENCE · CDD ANALYTICS")}'
                f'{ck_empty_state("No registered engine with id " + _html.escape(feature_id) + ".", icon="search")}'
                f'<p><a href="/cdd/tools">Back to the engines catalog</a></p></div>')
        return chartis_shell(body, title="CDD tool not found",
                             active_nav="/cdd/tools")

    try:
        exhibit = feat.demo()
        rendered = exhibit.render(internal_mode=internal)
    except Exception as exc:  # noqa: BLE001 - surface the reason, never 500
        body = (f'<div class="ck-page-wrap">'
                f'{ck_page_title(feat.title, eyebrow="DILIGENCE · CDD ANALYTICS · " + _html.escape(feature_id))}'
                f'{ck_empty_state("This engine could not run its demo in this environment: " + _html.escape(str(exc)), icon="alert")}'
                f'<p><a href="/cdd/tools">Back to the engines catalog</a></p></div>')
        return chartis_shell(body, title=feat.title, active_nav="/cdd/tools")

    fn = rendered.get("footnote") or {}
    flags = rendered.get("flags") or []
    recons = rendered.get("reconciliations") or []
    series = rendered.get("series") or []
    reconciled = bool(rendered.get("reconciled"))

    kpis = [
        ("Audience", _html.escape(str(rendered.get("audience", "both")))),
        ("Series", str(len(series))),
        ("Flags", str(len(flags))),
        ("Reconciled", "yes" if reconciled else "no"),
    ]
    kpi_html = "".join(
        f'<div class="cdt-kpi"><div class="cdt-kpi-l">{l}</div>'
        f'<div class="cdt-kpi-v">{v}</div></div>'
        for l, v in kpis)

    if flags:
        items = "".join(
            f'<li>{ck_signal_badge(f.get("severity", "info").upper(), tone=_FLAG_TONE.get(f.get("severity"), "neutral"))} '
            f'<span class="cdt-flag-code">{_html.escape(str(f.get("code", "")))}</span> '
            f'{_html.escape(str(f.get("message", "")))}</li>'
            for f in flags)
        flags_html = f'<ul class="cdt-dflags">{items}</ul>'
    else:
        flags_html = '<p class="cdt-muted">No flags raised.</p>'

    if recons:
        rrows = "".join(
            f'<tr><td>{_html.escape(str(r.get("identity", "")))}</td>'
            f'<td class="num">{_num(r.get("lhs"))}</td>'
            f'<td class="num">{_num(r.get("rhs"))}</td>'
            f'<td class="num">{_num(r.get("gap"))}</td>'
            f'<td>{ck_signal_badge("OK" if r.get("ok") else "OFF", tone="positive" if r.get("ok") else "negative")}</td></tr>'
            for r in recons)
        recon_html = (
            '<table class="cdt-dtable"><thead><tr><th>identity</th>'
            '<th>lhs</th><th>rhs</th><th>gap</th><th>ties</th></tr></thead>'
            f'<tbody>{rrows}</tbody></table>')
    else:
        recon_html = '<p class="cdt-muted">No reconciliation emitted.</p>'

    src = " · ".join(x for x in (fn.get("source", ""), fn.get("vintage", "")) if x)
    chart_html = ""
    for s in series:
        svg = _chart_for_series(s, s.get("name", feat.title), src)
        if svg:
            chart_html = (
                '<div class="cdt-chart" id="cdt-chart">'
                f'{chart_export_toolbar("cdt-chart", feature_id)}{svg}</div>')
            break

    series_html = "".join(
        f'<h3 class="cdt-dsub">{_html.escape(s.get("name", "series"))} '
        f'<span class="cdt-muted">({_html.escape(s.get("kind", "bar"))})</span></h3>'
        f'{_series_table(s)}'
        for s in series)

    fn_assumptions = fn.get("assumptions") or []
    assum_html = ""
    if fn_assumptions:
        assum_html = ('<ul class="cdt-dassum">'
                      + "".join(f"<li>{_html.escape(str(a))}</li>" for a in fn_assumptions)
                      + "</ul>")
    nodes = rendered.get("assumptions") or []  # internal-only assumption nodes
    nodes_html = ""
    if nodes:
        nrows = "".join(
            f'<tr><td>{_html.escape(str(n.get("label", n.get("key", ""))))}</td>'
            f'<td class="num">{_num(n.get("value"))}</td>'
            f'<td>{_html.escape(str(n.get("unit", "")))}</td>'
            f'<td>{_html.escape(str(n.get("source", "")))}</td></tr>'
            for n in nodes)
        nodes_html = (
            '<h3 class="cdt-dsub">Assumption nodes '
            '<span class="cdt-muted">(internal)</span></h3>'
            '<table class="cdt-dtable"><thead><tr><th>label</th><th>value</th>'
            '<th>unit</th><th>source</th></tr></thead>'
            f'<tbody>{nrows}</tbody></table>')

    fn_line = (f'{_html.escape(fn.get("source", "not stated"))} · '
               f'{_html.escape(fn.get("vintage", "not stated"))}'
               + (f' · basis: {_html.escape(fn.get("basis"))}' if fn.get("basis") else ""))

    mode_label = "internal" if internal else "partner"
    toggle_href = (f"/cdd/tools/{_html.escape(feature_id)}"
                   + ("" if internal else "?internal=1"))
    toggle_label = "View partner render" if internal else "View internal render"

    page_title = ck_page_title(
        feat.title,
        eyebrow="DILIGENCE · CDD ANALYTICS · " + _html.escape(feature_id),
        meta=f"{mode_label} render · {len(series)} series · "
             f"{len(flags)} flags · reconciled: {'yes' if reconciled else 'no'}",
    )
    summary = rendered.get("summary") or ""
    summary_html = (f'<p class="cdt-dsummary">{_html.escape(summary)}</p>'
                    if summary else "")

    css = """
<style>
.cdt-dnav { margin: 0 0 14px; font-size: 13px; }
.cdt-dnav a { color: #155752; text-decoration: none; }
.cdt-dsummary { font-size: 15px; color: #1a2332; max-width: 78ch; margin: 6px 0 18px; }
.cdt-kpis { display: flex; gap: 12px; flex-wrap: wrap; margin: 0 0 20px; }
.cdt-kpi { background: #fffdf9; border: 1px solid #d8d2c4; border-radius: 6px; padding: 9px 16px; min-width: 96px; }
.cdt-kpi-l { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #6b7280; }
.cdt-kpi-v { font-family: 'JetBrains Mono', monospace; font-size: 18px; color: #0b2341; }
.cdt-dblock { margin: 22px 0; }
.cdt-dblock h2 { font-size: 16px; color: #0b2341; margin: 0 0 10px; border-bottom: 1px solid #e2ddd0; padding-bottom: 5px; }
.cdt-dsub { font-size: 14px; color: #155752; margin: 16px 0 6px; }
.cdt-dflags { list-style: none; padding: 0; margin: 0; }
.cdt-dflags li { margin: 7px 0; font-size: 13.5px; line-height: 1.45; }
.cdt-flag-code { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #b8732a; }
.cdt-dtable { border-collapse: collapse; width: 100%; font-size: 12.5px; margin: 6px 0; }
.cdt-dtable th { text-align: left; background: #f0ece1; color: #0b2341; padding: 5px 8px; border: 1px solid #ddd6c8; font-weight: 600; }
.cdt-dtable td { padding: 4px 8px; border: 1px solid #e6e0d3; }
.cdt-dtable td.num { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; text-align: right; }
.cdt-muted { color: #6b7280; font-size: 12.5px; }
.cdt-chart { background: #fffdf9; border: 1px solid #d8d2c4; border-radius: 6px; padding: 10px; margin: 6px 0; }
.cdt-dassum { font-size: 12.5px; color: #4a5568; }
</style>"""
    body = f"""
<div class="ck-page-wrap">
  <div class="cdt-dnav"><a href="/cdd/tools">CDD Analytics Engines</a> / {_html.escape(feature_id)}
    &nbsp;·&nbsp; <a href="{toggle_href}">{toggle_label}</a></div>
  {page_title}
  {summary_html}
  <div class="cdt-kpis">{kpi_html}</div>
  {('<div class="cdt-dblock"><h2>Exhibit</h2>' + chart_html + '</div>') if chart_html else ''}
  <div class="cdt-dblock"><h2>Flags</h2>{flags_html}</div>
  <div class="cdt-dblock"><h2>Reconciliation</h2>{recon_html}</div>
  <div class="cdt-dblock"><h2>Data</h2>{series_html}{nodes_html}</div>
  <div class="cdt-dblock"><h2>Source</h2>
    <p class="cdt-muted">{fn_line}</p>{assum_html}</div>
</div>"""
    return chartis_shell(body, title=feat.title, active_nav="/cdd/tools",
                         extra_css=css)


# ── JSON / CSV twins ─────────────────────────────────────────────────

def cdd_tools_catalog() -> List[Dict[str, Any]]:
    """Machine-readable catalog of every registered engine."""
    from rcm_mc.cdd import registry

    out = []
    for feat in registry.all_features():
        out.append({
            "feature_id": feat.feature_id,
            "title": feat.title,
            "audience": feat.audience,
            "family": _family(feat.feature_id),
        })
    return out


def cdd_tools_index_csv(params: Optional[Dict[str, Any]] = None) -> str:
    """CSV of the catalog, defanged for spreadsheet formula injection."""
    def _defang(s: str) -> str:
        s = str(s)
        return ("'" + s) if s[:1] in ("=", "+", "-", "@") else s

    lines = ["feature_id,title,audience,family"]
    for row in cdd_tools_catalog():
        cells = [_defang(row["feature_id"]), _defang(row["title"]),
                 _defang(row["audience"]), _defang(row["family"])]
        lines.append(",".join('"' + c.replace('"', '""') + '"' for c in cells))
    return "\n".join(lines) + "\n"
