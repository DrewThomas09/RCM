"""Cross-Dataset Analysis page — /cross-analysis.

Correlate any two of the platform's state-grain public datasets: pick X and Y
measures, get the Pearson r / R² stat block, a scatter with a least-squares
trendline, and the joined state table. The analytical companion to the
single-dataset Further Analysis explorer.
"""
from __future__ import annotations

import html
from typing import Any, Dict, Optional

from ..diligence import cross_analysis as ca
from .cdd_chart_kit import render_cdd_chart


def _fmt_num(v: Optional[float], nd: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:.{nd}f}"


def _ds_select(name: str, selected: str) -> str:
    opts = ""
    for d in ca.state_grain_datasets():
        sel = " selected" if d.id == selected else ""
        opts += (f'<option value="{d.id}"{sel}>'
                 f'{html.escape(d.label)}</option>')
    return (f'<select name="{name}" onchange="this.form.submit()" '
            f'style="width:100%;height:30px;border:1px solid #c9c1ac;'
            f'border-radius:5px;">{opts}</select>')


def _measure_select(name: str, dataset_id: str, selected: str) -> str:
    d = ca.fa.DATASETS.get(dataset_id)
    opts = ""
    if d is not None:
        for m in d.measures:
            sel = " selected" if m.key == selected else ""
            opts += (f'<option value="{m.key}"{sel}>'
                     f'{html.escape(m.label)}</option>')
    return (f'<select name="{name}" onchange="this.form.submit()" '
            f'style="width:100%;height:30px;border:1px solid #c9c1ac;'
            f'border-radius:5px;">{opts}</select>')


def render_cross_analysis_page(qs: "Optional[Dict[str, Any]]" = None) -> str:
    from ._chartis_kit import chartis_shell, ck_kpi_block, ck_page_title

    spec = ca.resolve_query(qs)
    res = spec["result"]
    stats = res.get("stats", {})
    x_meta = res.get("x", {})
    y_meta = res.get("y", {})

    r = stats.get("pearson_r")
    r2 = stats.get("r2")
    n = stats.get("n", 0)
    strength = stats.get("strength") or "—"

    # Stat block.
    r_tone = "pos" if (r is not None and r >= 0) else "neg"
    kpis = (
        '<div class="ck-kpi-row" style="display:flex;flex-wrap:wrap;gap:14px;">'
        + ck_kpi_block("Correlation (r)",
                       f'<span class="mn {r_tone}">{_fmt_num(r)}</span>',
                       html.escape(strength))
        + ck_kpi_block("R²", f'<span class="mn">{_fmt_num(r2)}</span>',
                       "variance explained")
        + ck_kpi_block("States (n)", f'<span class="mn">{n}</span>',
                       "in the join")
        + ck_kpi_block("Fit slope", f'<span class="mn">'
                       f'{_fmt_num(stats.get("slope"), 3)}</span>',
                       "Δy per unit x")
        + '</div>')

    # Scatter chart with trendline.
    chart = ""
    if res.get("ok") and res.get("table", {}).get("rows"):
        opts = {
            "title": "Cross-dataset correlation",
            "subtitle": (f'{html.escape(x_meta.get("label",""))}  ×  '
                         f'{html.escape(y_meta.get("label",""))}'),
            "palette": "Navy–Teal", "width_px": 920, "trendline": True,
            "xsuffix": x_meta.get("suffix", ""),
            "ysuffix": y_meta.get("suffix", ""),
            "footnote": "Each point is a US state. Dashed line = least-squares "
                        "fit. Correlation is not causation.",
        }
        chart = (f'<div style="margin:16px 0;text-align:center;">'
                 f'{render_cdd_chart("scatter", res["table"], opts)}</div>')
    else:
        chart = ('<p style="color:#b8732a;font-size:12.5px;">Not enough paired '
                 'states to correlate (need ≥3 with both values).</p>')

    # Controls.
    controls = (
        '<form method="get" style="display:grid;'
        'grid-template-columns:1fr 1fr;gap:12px 20px;margin:14px 0;'
        'background:#fff;border:1px solid #e6e0d2;border-radius:8px;'
        'padding:14px;">'
        '<div><div style="font-size:10px;letter-spacing:.06em;'
        'text-transform:uppercase;color:#7a8699;margin-bottom:3px;">'
        'X dataset</div>' + _ds_select("x", spec["x_id"]) + '</div>'
        '<div><div style="font-size:10px;letter-spacing:.06em;'
        'text-transform:uppercase;color:#7a8699;margin-bottom:3px;">'
        'Y dataset</div>' + _ds_select("y", spec["y_id"]) + '</div>'
        '<div><div style="font-size:10px;letter-spacing:.06em;'
        'text-transform:uppercase;color:#7a8699;margin-bottom:3px;">'
        'X measure</div>'
        + _measure_select("xm", spec["x_id"], spec["x_measure"]) + '</div>'
        '<div><div style="font-size:10px;letter-spacing:.06em;'
        'text-transform:uppercase;color:#7a8699;margin-bottom:3px;">'
        'Y measure</div>'
        + _measure_select("ym", spec["y_id"], spec["y_measure"]) + '</div>'
        '<noscript><button type="submit" style="grid-column:1/3;">'
        'Update</button></noscript>'
        '</form>')

    # Joined data table.
    rows_html = ""
    for lbl, vals in res.get("table", {}).get("rows", []):
        rows_html += (
            f'<tr style="border-top:1px solid #eee;">'
            f'<td style="padding:4px 8px;">{html.escape(str(lbl))}</td>'
            f'<td style="padding:4px 8px;text-align:right;font-variant-numeric:'
            f'tabular-nums;">{_fmt_num(vals[0])}{html.escape(x_meta.get("suffix",""))}</td>'
            f'<td style="padding:4px 8px;text-align:right;font-variant-numeric:'
            f'tabular-nums;">{_fmt_num(vals[1])}{html.escape(y_meta.get("suffix",""))}</td>'
            f'</tr>')
    table_html = (
        '<details style="margin-top:14px;"><summary style="cursor:pointer;'
        'font-size:11px;letter-spacing:.05em;text-transform:uppercase;'
        'color:#7a8699;">Data behind the chart</summary>'
        '<table style="width:100%;border-collapse:collapse;margin-top:8px;'
        'font-size:12px;">'
        f'<thead><tr style="text-align:left;color:#7a8699;font-size:10px;">'
        f'<th style="padding:4px 8px;">State</th>'
        f'<th style="padding:4px 8px;text-align:right;">'
        f'{html.escape(x_meta.get("label",""))}</th>'
        f'<th style="padding:4px 8px;text-align:right;">'
        f'{html.escape(y_meta.get("label",""))}</th></tr></thead>'
        f'<tbody>{rows_html}</tbody></table></details>')

    intro = (
        '<p style="font-size:12.5px;color:#56606f;max-width:880px;'
        'margin:6px 0 0;">Correlate any two state-grain public datasets on the '
        'state they share. Real public data only; a state missing either value '
        'is dropped from the pair (never zero-filled). Correlation is not '
        'causation — use it to form hypotheses, then drill into the sources.</p>')

    body = (
        ck_page_title("Cross-Dataset Analysis",
                      eyebrow="Correlation engine",
                      meta=f"{len(ca.state_grain_datasets())} joinable "
                           f"state-grain datasets")
        + intro + controls + kpis + chart + table_html)
    return chartis_shell(body, "Cross-Dataset Analysis", active_nav="/research",
                         subtitle="Correlate two public datasets")
