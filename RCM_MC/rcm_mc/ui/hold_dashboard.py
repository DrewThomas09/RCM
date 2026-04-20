"""Hold-period dashboard (Prompt 42).

Route: ``GET /hold/<deal_id>``. Shows the deal team how the asset
is performing against the value creation plan: initiative progress
bars, actuals-vs-plan chart, quarterly scorecard, covenant monitor.
"""
from __future__ import annotations

import html
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _fmt_money(v: float) -> str:
    if abs(v) >= 1e6:
        return f"${v / 1e6:,.1f}M"
    if abs(v) >= 1e3:
        return f"${v / 1e3:,.0f}K"
    return f"${v:,.0f}"


_STATUS_COLORS = {
    "completed": "#0a8a5f",
    "on_track": "#2fb3ad",
    "in_progress": "#b8732a",
    "at_risk": "#b5321e",
    "not_started": "#7a8699",
    "abandoned": "#374151",
}

_HOLD_CSS = """
body.hold-dash { margin:0; padding:0; background:#f5f1ea; color:#1a2332;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;
  font-size:14px; line-height:1.5; }
.hold-wrap { max-width:1100px; margin:0 auto; padding:24px 20px; }
.hold-header { display:flex; align-items:center; gap:20px; margin-bottom:20px; }
.hold-header h1 { font-size:20px; font-weight:600; margin:0; }
.hold-header .dim { color:#465366; font-size:12px; }
.hold-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:16px; }
.hold-card { background:#ffffff; border:1px solid #d6cfc3;
  padding:14px 16px; border-radius:4px; }
.hold-card-title { font-weight:600; margin-bottom:10px; font-size:13px; }
.init-row { display:grid; grid-template-columns:180px 1fr 80px;
  gap:10px; padding:6px 0; border-bottom:1px solid #d6cfc3;
  align-items:center; font-size:12px; }
.init-bar { background:#d6cfc3; height:8px; border-radius:4px; overflow:hidden; }
.init-bar > div { height:100%; border-radius:4px; }
.init-status { font-size:10px; text-transform:uppercase; font-weight:600;
  letter-spacing:.04em; }
.scorecard-table { width:100%; border-collapse:collapse; font-size:12px;
  font-family:"JetBrains Mono",monospace; }
.scorecard-table th { background:#ece6db; color:#465366; padding:6px 8px;
  text-align:center; font-size:10px; text-transform:uppercase;
  letter-spacing:.04em; }
.scorecard-table td { padding:6px 8px; text-align:center;
  border-bottom:1px solid #d6cfc3; }
.cov-light { display:inline-block; width:12px; height:12px;
  border-radius:50%; margin-right:6px; }
"""


def _load_plan(store: Any, deal_id: str):
    try:
        from ..pe.value_creation_plan import load_latest_plan
        return load_latest_plan(store, deal_id)
    except Exception:  # noqa: BLE001
        return None


def _load_actuals(store: Any, deal_id: str) -> List[Dict[str, Any]]:
    try:
        with store.connect() as con:
            rows = con.execute(
                "SELECT quarter, kpis_json, plan_kpis_json "
                "FROM quarterly_actuals WHERE deal_id = ? "
                "ORDER BY quarter",
                (deal_id,),
            ).fetchall()
        return [
            {
                "quarter": r["quarter"],
                "actuals": json.loads(r["kpis_json"] or "{}"),
                "plan": json.loads(r["plan_kpis_json"] or "{}"),
            }
            for r in rows
        ]
    except Exception:  # noqa: BLE001
        return []


def _render_initiative_progress(plan) -> str:
    if plan is None or not plan.initiatives:
        return '<div class="dim" style="padding:8px;">No value creation plan yet.</div>'
    rows: List[str] = []
    for init in plan.initiatives:
        color = _STATUS_COLORS.get(init.status, "#7a8699")
        # Achievement % — rough: status-based for now.
        pct = {
            "completed": 100, "on_track": 70, "in_progress": 40,
            "at_risk": 25, "not_started": 0, "abandoned": 0,
        }.get(init.status, 0)
        rows.append(
            f'<div class="init-row">'
            f'<div>{_esc(init.name[:30])}</div>'
            f'<div class="init-bar"><div style="width:{pct}%;background:{color};"></div></div>'
            f'<div class="init-status" style="color:{color};">{_esc(init.status)}</div>'
            f'</div>'
        )
    return "".join(rows)


def _render_ebitda_chart(actuals_list: List[Dict[str, Any]]) -> str:
    """Inline SVG line chart: actuals (solid blue) vs plan (dashed gray).

    Variance shading: green when above plan, red when below. Simple
    but informative — partners read this at-a-glance in the hold
    dashboard.
    """
    if not actuals_list or len(actuals_list) < 2:
        return ""
    quarters = [q["quarter"] for q in actuals_list]
    actuals = [float(q["actuals"].get("ebitda") or 0) for q in actuals_list]
    plans = [float(q["plan"].get("ebitda") or 0) for q in actuals_list]
    if not any(a > 0 for a in actuals):
        return ""
    all_vals = [v for v in actuals + plans if v > 0]
    if not all_vals:
        return ""
    lo = min(all_vals) * 0.9
    hi = max(all_vals) * 1.1
    span = hi - lo if hi > lo else 1.0
    w, h = 500, 180
    n = len(quarters)
    pad_x, pad_y = 50, 20

    def _x(i: int) -> float:
        return pad_x + i * (w - 2 * pad_x) / max(1, n - 1)

    def _y(v: float) -> float:
        return h - pad_y - ((v - lo) / span) * (h - 2 * pad_y)

    # Variance shading.
    shading = ""
    for i in range(n - 1):
        x1, x2 = _x(i), _x(i + 1)
        a1, a2 = actuals[i], actuals[i + 1]
        p1, p2 = plans[i], plans[i + 1]
        above = (a1 + a2) / 2 >= (p1 + p2) / 2
        color = "#0a8a5f30" if above else "#b5321e30"
        pts = f"{x1},{_y(a1)} {x2},{_y(a2)} {x2},{_y(p2)} {x1},{_y(p1)}"
        shading += f'<polygon points="{pts}" fill="{color}"/>'

    # Lines.
    actual_pts = " ".join(f"{_x(i)},{_y(actuals[i])}" for i in range(n))
    plan_pts = " ".join(f"{_x(i)},{_y(plans[i])}" for i in range(n))

    # X-axis labels.
    labels = ""
    for i, q in enumerate(quarters):
        labels += (
            f'<text x="{_x(i)}" y="{h - 2}" text-anchor="middle" '
            f'fill="#465366" font-size="9">{_esc(q)}</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:{h}px;">'
        f'{shading}'
        f'<polyline points="{plan_pts}" fill="none" stroke="#7a8699" '
        f'stroke-dasharray="4,3" stroke-width="1.5"/>'
        f'<polyline points="{actual_pts}" fill="none" stroke="#2fb3ad" '
        f'stroke-width="2"/>'
        f'{labels}'
        f'<text x="{w - pad_x}" y="14" text-anchor="end" fill="#2fb3ad" '
        f'font-size="10">Actual</text>'
        f'<text x="{w - pad_x}" y="26" text-anchor="end" fill="#7a8699" '
        f'font-size="10">Plan</text>'
        f'</svg>'
    )


def _render_scorecard(actuals_list: List[Dict[str, Any]]) -> str:
    if not actuals_list:
        return '<div class="dim" style="padding:8px;">No quarterly actuals recorded yet.</div>'
    kpis = ["ebitda", "net_patient_revenue", "idr_blended",
            "fwr_blended", "dar_clean_days"]
    header = "".join(f"<th>{k}</th>" for k in kpis)
    rows: List[str] = []
    for q in actuals_list:
        cells: List[str] = []
        for kpi in kpis:
            actual = q["actuals"].get(kpi)
            plan_val = q["plan"].get(kpi)
            if actual is None:
                cells.append('<td class="dim">—</td>')
                continue
            icon = "✓"
            color = "#0a8a5f"
            if plan_val is not None:
                try:
                    var = (float(actual) - float(plan_val)) / max(abs(float(plan_val)), 1e-9)
                    if abs(var) > 0.15:
                        icon = "✗"; color = "#b5321e"
                    elif abs(var) > 0.05:
                        icon = "⚠"; color = "#b8732a"
                except (TypeError, ValueError):
                    pass
            cells.append(
                f'<td style="color:{color};">'
                f'{float(actual):,.1f} {icon}</td>'
            )
        rows.append(
            f'<tr><td style="font-weight:600;">{_esc(q["quarter"])}</td>'
            + "".join(cells) + '</tr>'
        )
    return (
        '<table class="scorecard-table">'
        f'<thead><tr><th>Quarter</th>{header}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def render_hold_dashboard(
    store: Any, deal_id: str, deal_name: str = "",
) -> str:
    from ._chartis_kit import chartis_shell
    plan = _load_plan(store, deal_id)
    actuals = _load_actuals(store, deal_id)

    progress_html = _render_initiative_progress(plan)
    scorecard_html = _render_scorecard(actuals)
    ebitda_chart = _render_ebitda_chart(actuals)
    quarters_held = len(actuals)

    body = (
        f'<div class="hold-wrap">'
        f'<div class="hold-header">'
        f'<span class="dim">{quarters_held} quarter(s) held</span>'
        f'<a href="/analysis/{_esc(deal_id)}" style="color:#2fb3ad;'
        f'text-decoration:none;margin-left:auto;">← Workbench</a>'
        f'</div>'
        f'<div class="hold-grid">'
        f'<div class="hold-card">'
        f'<div class="hold-card-title">Initiative Progress</div>'
        f'{progress_html}</div>'
        f'<div class="hold-card">'
        f'<div class="hold-card-title">Quarterly Scorecard</div>'
        f'{scorecard_html}</div>'
        f'</div>'
        + (f'<div class="hold-card" style="margin-top:12px;">'
           f'<div class="hold-card-title">EBITDA: Actual vs Plan</div>'
           f'{ebitda_chart}</div>' if ebitda_chart else '') +
        '</div>'
    )
    return chartis_shell(
        body,
        f"{deal_name or deal_id} — Hold Period",
        extra_css=_HOLD_CSS,
    )
