"""CDD analytics tools catalog — /cdd/tools.

The ``rcm_mc.cdd`` registry holds the desk's audience-aware analytic
exhibits (TAM/SAM, PVM bridge, payer mix, retention, LTV/CAC, profit
pools, marimekko, contested market-size triangulation, and the rest).
Every one was wired into the registry so the CLI (``python -m
rcm_mc.cdd``) and server could run it, but until now the only browser
surface was the static CDD workflow hub. An associate could not see the
full tool set, run one, and read its exhibit without dropping to the
shell.

This page reads the live registry and renders two surfaces:

- ``/cdd/tools`` lists every registered tool grouped by family, with its
  audience and a one-line identity.
- ``/cdd/tools/<feature_id>`` runs that tool's demo exhibit and renders
  it the way a partner sees it: summary, flags, reconciliation status, a
  chart of the leading series, the underlying data, and the sourced
  footnote. ``?internal=1`` switches to the internal render so an analyst
  can see the assumption nodes the partner view strips.

The page computes nothing itself: it is a faithful window onto whatever
the registry exposes, so a new ``register(...)`` call shows up here with
no edit to this file.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.cdd import registry
from rcm_mc.ui._chartis_kit import (
    chartis_shell, ck_page_explainer, ck_page_title, ck_signal_badge,
    ck_empty_state,
)
from rcm_mc.ui.cdd_chart_kit import render_cdd_chart, chart_export_toolbar


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

# Flag severity -> badge tone. "risk" is the desk's red diligence flag.
_SEVERITY_TONE = {"risk": "negative", "warn": "warning", "info": "neutral"}


def _family(feature_id: str) -> str:
    """Group key: the prefix before the first hyphen (NEW, BOLSTER, PACK)."""
    return feature_id.split("-", 1)[0] if "-" in feature_id else feature_id


_FAMILY_LABEL = {
    "NEW": "Core analytics",
    "BOLSTER": "Hardened estimators",
    "PACK": "Composite packs",
}


def _audience_badge(audience: str) -> str:
    tone = "neutral" if audience == "both" else "warning"
    return ck_signal_badge(audience.upper(), tone=tone)


# ── Index ────────────────────────────────────────────────────────────

def render_cdd_tools_index(params: Optional[Dict[str, Any]] = None) -> str:
    features = registry.all_features()

    groups: Dict[str, List[Any]] = {}
    for feat in features:
        groups.setdefault(_family(feat.feature_id), []).append(feat)

    sections = []
    for fam in sorted(groups, key=lambda k: (k != "NEW", k != "PACK", k)):
        label = _FAMILY_LABEL.get(fam, fam)
        cards = []
        for feat in groups[fam]:
            fid = _html.escape(feat.feature_id)
            cards.append(
                f'<a class="cdt-card" href="/cdd/tools/{fid}">'
                f'<div class="cdt-card-top">'
                f'<span class="cdt-id">{fid}</span>'
                f'{_audience_badge(feat.audience)}</div>'
                f'<div class="cdt-card-title">{_html.escape(feat.title)}</div>'
                f'</a>')
        sections.append(
            f'<section class="cdt-fam">'
            f'<h2 class="cdt-fam-h">{_html.escape(label)} '
            f'<span class="cdt-fam-n">{len(groups[fam])}</span></h2>'
            f'<div class="cdt-grid">{"".join(cards)}</div>'
            f'</section>')

    page_title = ck_page_title(
        "CDD Analytics Tools",
        eyebrow="DILIGENCE · CDD ANALYTICS",
        meta=(f"{len(features)} registered tools · live registry · "
              "each renders an audience-aware, reconciled exhibit"),
    )
    explainer = ck_page_explainer(
        "Every analytic the desk can run, in one catalog.",
        "These are the registered CDD analytics: each one takes sourced "
        "inputs and returns a single exhibit that carries its own flags, a "
        "reconciliation that proves the numbers tie out, and a footnote with "
        "source and vintage. Open a tool to run its demo and read the exhibit "
        "the way a partner sees it. The list is read live from the registry, "
        "so a newly registered tool appears here on its own.",
    )
    css = """
<style>
.cdt-fam { margin: 24px 0; }
.cdt-fam-h { font-size: 18px; margin: 0 0 12px; color: #0b2341; }
.cdt-fam-n { font-family: 'JetBrains Mono', monospace; font-size: 12px;
             color: #155752; background: #e7efe9; border-radius: 10px;
             padding: 1px 8px; margin-left: 6px; vertical-align: middle; }
.cdt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.cdt-card { display: block; background: #fffdf9; border: 1px solid #d8d2c4;
            border-radius: 6px; padding: 13px 15px; text-decoration: none; }
.cdt-card:hover { border-color: #155752; }
.cdt-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.cdt-id { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #155752; font-weight: 600; }
.cdt-card-title { font-size: 14.5px; line-height: 1.35; color: #1a2332; }
</style>"""
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {explainer}
  {"".join(sections)}
</div>"""
    return chartis_shell(body, title="CDD Analytics Tools",
                         active_nav="/cdd/tools", extra_css=css)


# ── Detail ───────────────────────────────────────────────────────────

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


def _num(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _html.escape(str(value))
    if float(value).is_integer() and abs(value) < 1e15:
        return f"{value:,.0f}"
    return f"{value:,.4f}"


def _series_table(series: Dict[str, Any]) -> str:
    points = series.get("points") or []
    if not points:
        return '<p class="cdt-muted">No rows.</p>'
    # Union of keys across points, label first, in first-seen order.
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
    return (f'<table class="cdt-table"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body_rows)}</tbody></table>{more}')


def render_cdd_tool_detail(feature_id: str,
                          params: Optional[Dict[str, Any]] = None) -> str:
    params = params or {}
    internal = str(params.get("internal", "")).strip() in ("1", "true", "yes")

    try:
        feat = registry.get(feature_id)
    except KeyError:
        body = (f'<div class="ck-page-wrap">'
                f'{ck_page_title("Tool not found", eyebrow="DILIGENCE · CDD ANALYTICS")}'
                f'{ck_empty_state("No registered tool with id " + _html.escape(feature_id) + ".", icon="search")}'
                f'<p><a href="/cdd/tools">Back to the tools catalog</a></p></div>')
        return chartis_shell(body, title="CDD tool not found",
                             active_nav="/cdd/tools")

    try:
        exhibit = feat.demo()
        rendered = exhibit.render(internal_mode=internal)
    except Exception as exc:  # noqa: BLE001 - surface the reason, never 500
        body = (f'<div class="ck-page-wrap">'
                f'{ck_page_title(feat.title, eyebrow="DILIGENCE · CDD ANALYTICS · " + _html.escape(feature_id))}'
                f'{ck_empty_state("This tool could not run its demo in this environment: " + _html.escape(str(exc)), icon="alert")}'
                f'<p><a href="/cdd/tools">Back to the tools catalog</a></p></div>')
        return chartis_shell(body, title=feat.title, active_nav="/cdd/tools")

    fn = rendered.get("footnote") or {}
    flags = rendered.get("flags") or []
    recons = rendered.get("reconciliations") or []
    series = rendered.get("series") or []
    reconciled = bool(rendered.get("reconciled"))

    # Header KPI strip.
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

    # Flags.
    if flags:
        items = "".join(
            f'<li>{ck_signal_badge(f.get("severity", "info").upper(), tone=_SEVERITY_TONE.get(f.get("severity"), "neutral"))} '
            f'<span class="cdt-flag-code">{_html.escape(str(f.get("code", "")))}</span> '
            f'{_html.escape(str(f.get("message", "")))}</li>'
            for f in flags)
        flags_html = f'<ul class="cdt-flags">{items}</ul>'
    else:
        flags_html = '<p class="cdt-muted">No flags raised.</p>'

    # Reconciliations.
    if recons:
        rrows = "".join(
            f'<tr><td>{_html.escape(str(r.get("identity", "")))}</td>'
            f'<td class="num">{_num(r.get("lhs"))}</td>'
            f'<td class="num">{_num(r.get("rhs"))}</td>'
            f'<td class="num">{_num(r.get("gap"))}</td>'
            f'<td>{ck_signal_badge("OK" if r.get("ok") else "OFF", tone="positive" if r.get("ok") else "negative")}</td></tr>'
            for r in recons)
        recon_html = (
            '<table class="cdt-table"><thead><tr><th>identity</th>'
            '<th>lhs</th><th>rhs</th><th>gap</th><th>ties</th></tr></thead>'
            f'<tbody>{rrows}</tbody></table>')
    else:
        recon_html = '<p class="cdt-muted">No reconciliation emitted.</p>'

    # Chart of the first chartable series.
    src = " · ".join(x for x in (fn.get("source", ""), fn.get("vintage", "")) if x)
    chart_html = ""
    for s in series:
        svg = _chart_for_series(s, s.get("name", feat.title), src)
        if svg:
            chart_html = (
                '<div class="cdt-chart" id="cdt-chart">'
                f'{chart_export_toolbar("cdt-chart", feature_id)}{svg}</div>')
            break

    # Series tables.
    series_html = "".join(
        f'<h3 class="cdt-sub">{_html.escape(s.get("name", "series"))} '
        f'<span class="cdt-muted">({_html.escape(s.get("kind", "bar"))})</span></h3>'
        f'{_series_table(s)}'
        for s in series)

    # Footnote + assumptions (assumptions only present in internal render).
    fn_assumptions = fn.get("assumptions") or []
    assum_html = ""
    if fn_assumptions:
        assum_html = ('<ul class="cdt-assum">'
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
            '<h3 class="cdt-sub">Assumption nodes '
            '<span class="cdt-muted">(internal)</span></h3>'
            '<table class="cdt-table"><thead><tr><th>label</th><th>value</th>'
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
    summary_html = (f'<p class="cdt-summary">{_html.escape(summary)}</p>'
                    if summary else "")

    css = """
<style>
.cdt-nav { margin: 0 0 14px; font-size: 13px; }
.cdt-nav a { color: #155752; text-decoration: none; }
.cdt-summary { font-size: 15px; color: #1a2332; max-width: 78ch; margin: 6px 0 18px; }
.cdt-kpis { display: flex; gap: 12px; flex-wrap: wrap; margin: 0 0 20px; }
.cdt-kpi { background: #fffdf9; border: 1px solid #d8d2c4; border-radius: 6px; padding: 9px 16px; min-width: 96px; }
.cdt-kpi-l { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #6b7280; }
.cdt-kpi-v { font-family: 'JetBrains Mono', monospace; font-size: 18px; color: #0b2341; }
.cdt-block { margin: 22px 0; }
.cdt-block h2 { font-size: 16px; color: #0b2341; margin: 0 0 10px; border-bottom: 1px solid #e2ddd0; padding-bottom: 5px; }
.cdt-sub { font-size: 14px; color: #155752; margin: 16px 0 6px; }
.cdt-flags { list-style: none; padding: 0; margin: 0; }
.cdt-flags li { margin: 7px 0; font-size: 13.5px; line-height: 1.45; }
.cdt-flag-code { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #b8732a; }
.cdt-table { border-collapse: collapse; width: 100%; font-size: 12.5px; margin: 6px 0; }
.cdt-table th { text-align: left; background: #f0ece1; color: #0b2341; padding: 5px 8px; border: 1px solid #ddd6c8; font-weight: 600; }
.cdt-table td { padding: 4px 8px; border: 1px solid #e6e0d3; }
.cdt-table td.num { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; text-align: right; }
.cdt-muted { color: #6b7280; font-size: 12.5px; }
.cdt-chart { background: #fffdf9; border: 1px solid #d8d2c4; border-radius: 6px; padding: 10px; margin: 6px 0; }
.cdt-assum { font-size: 12.5px; color: #4a5568; }
</style>"""
    body = f"""
<div class="ck-page-wrap">
  <div class="cdt-nav"><a href="/cdd/tools">CDD Analytics Tools</a> / {_html.escape(feature_id)}
    &nbsp;·&nbsp; <a href="{toggle_href}">{toggle_label}</a></div>
  {page_title}
  {summary_html}
  <div class="cdt-kpis">{kpi_html}</div>
  {('<div class="cdt-block"><h2>Exhibit</h2>' + chart_html + '</div>') if chart_html else ''}
  <div class="cdt-block"><h2>Flags</h2>{flags_html}</div>
  <div class="cdt-block"><h2>Reconciliation</h2>{recon_html}</div>
  <div class="cdt-block"><h2>Data</h2>{series_html}{nodes_html}</div>
  <div class="cdt-block"><h2>Source</h2>
    <p class="cdt-muted">{fn_line}</p>{assum_html}</div>
</div>"""
    return chartis_shell(body, title=feat.title, active_nav="/cdd/tools",
                         extra_css=css)


# ── JSON / CSV twins ─────────────────────────────────────────────────

def cdd_tools_catalog() -> List[Dict[str, Any]]:
    """Machine-readable catalog of every registered tool."""
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
