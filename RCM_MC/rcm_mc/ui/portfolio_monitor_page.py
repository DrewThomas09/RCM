"""SeekingChartis Portfolio Monitor — actual vs predicted, early warnings.

Unified view: predicted vs actual by metric, plan tracking, comp-relative
trends, projected vs actual EBITDA bridge, and early warning signals
across the entire portfolio.
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def _sev_badge(sev: str) -> str:
    colors = {"on_track": "var(--cad-pos)", "lagging": "var(--cad-warn)", "off_track": "var(--cad-neg)",
              "SAFE": "var(--cad-pos)", "TIGHT": "var(--cad-warn)", "TRIPPED": "var(--cad-neg)"}
    labels = {"on_track": "On Track", "lagging": "Lagging", "off_track": "Off Track",
              "SAFE": "Safe", "TIGHT": "Tight", "TRIPPED": "Tripped"}
    c = colors.get(sev, "var(--cad-text3)")
    l = labels.get(sev, sev)
    return f'<span style="background:{c};color:#fff;padding:2px 8px;border-radius:3px;font-size:10px;font-weight:600;">{l}</span>'


def render_portfolio_monitor(store: Any) -> str:
    """Render the portfolio monitoring dashboard."""
    import json as _json

    # Load deals
    try:
        with store.connect() as con:
            deals = con.execute(
                "SELECT deal_id, name, profile_json FROM deals WHERE archived_at IS NULL"
            ).fetchall()
    except Exception:
        deals = []

    if not deals:
        return chartis_shell(
            '<div class="cad-card"><p style="color:var(--cad-text3);">'
            'No active deals in portfolio. Import deals to start monitoring.</p></div>',
            "Portfolio Monitor", subtitle="No active deals",
        )

    # Load quarterly actuals
    try:
        with store.connect() as con:
            actuals_rows = con.execute(
                "SELECT deal_id, quarter, kpis_json, plan_kpis_json "
                "FROM quarterly_actuals ORDER BY quarter DESC"
            ).fetchall()
    except Exception:
        actuals_rows = []

    # Load snapshots for covenant tracking
    try:
        with store.connect() as con:
            snapshots = con.execute(
                "SELECT deal_id, stage, snapshot_json, created_at "
                "FROM deal_snapshots ORDER BY created_at DESC"
            ).fetchall()
    except Exception:
        snapshots = []

    # Load health scores
    try:
        with store.connect() as con:
            health_rows = con.execute(
                "SELECT deal_id, score, band FROM deal_health_history "
                "ORDER BY date DESC"
            ).fetchall()
    except Exception:
        health_rows = []

    # Load alerts
    try:
        with store.connect() as con:
            alert_rows = con.execute(
                "SELECT deal_id, severity, kind, message, fired_at "
                "FROM alerts WHERE acked_at IS NULL ORDER BY fired_at DESC LIMIT 30"
            ).fetchall()
    except Exception:
        alert_rows = []

    # ── Assemble deal data ──
    deal_map = {}
    for d in deals:
        did = d[0]
        name = d[1] or did
        profile = _json.loads(d[2]) if d[2] else {}
        deal_map[did] = {
            "name": name, "profile": profile,
            "actuals": [], "latest_health": None,
            "latest_snapshot": None, "alerts": [],
        }

    for ar in actuals_rows:
        did = ar[0]
        if did in deal_map:
            try:
                kpis = _json.loads(ar[2]) if ar[2] else {}
                plan = _json.loads(ar[3]) if ar[3] else {}
            except Exception:
                kpis, plan = {}, {}
            deal_map[did]["actuals"].append({
                "quarter": ar[1], "kpis": kpis, "plan": plan})

    for hr in health_rows:
        did = hr[0]
        if did in deal_map and deal_map[did]["latest_health"] is None:
            deal_map[did]["latest_health"] = {"score": hr[1], "band": hr[2]}

    for sr in snapshots:
        did = sr[0]
        if did in deal_map and deal_map[did]["latest_snapshot"] is None:
            try:
                snap = _json.loads(sr[2]) if sr[2] else {}
            except Exception:
                snap = {}
            deal_map[did]["latest_snapshot"] = {"stage": sr[1], "data": snap}

    for ar in alert_rows:
        did = ar[0]
        if did in deal_map:
            deal_map[did]["alerts"].append({
                "severity": ar[1], "kind": ar[2],
                "message": ar[3], "fired_at": ar[4]})

    n_deals = len(deal_map)
    n_with_actuals = sum(1 for d in deal_map.values() if d["actuals"])
    n_alerts = len(alert_rows)

    # ── Health distribution ──
    green = sum(1 for d in deal_map.values() if d["latest_health"] and d["latest_health"]["band"] == "green")
    amber = sum(1 for d in deal_map.values() if d["latest_health"] and d["latest_health"]["band"] == "amber")
    red = sum(1 for d in deal_map.values() if d["latest_health"] and d["latest_health"]["band"] == "red")
    no_health = n_deals - green - amber - red

    # ── KPIs ──
    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(6,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_deals}</div>'
        f'<div class="cad-kpi-label">Active Deals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_with_actuals}</div>'
        f'<div class="cad-kpi-label">With Actuals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-pos);">{green}</div>'
        f'<div class="cad-kpi-label">Green</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-warn);">{amber}</div>'
        f'<div class="cad-kpi-label">Amber</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-neg);">{red}</div>'
        f'<div class="cad-kpi-label">Red</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-neg);">{n_alerts}</div>'
        f'<div class="cad-kpi-label">Open Alerts</div></div>'
        f'</div>'
    )

    # ── Active alerts ──
    alert_html = ""
    if alert_rows:
        alert_items = ""
        for ar in alert_rows[:10]:
            did = ar[0]
            sev = ar[1]
            sev_color = {"red": "var(--cad-neg)", "amber": "var(--cad-warn)"}.get(sev, "var(--cad-text3)")
            name = deal_map.get(did, {}).get("name", did)
            alert_items += (
                f'<div style="display:flex;gap:10px;padding:8px 0;'
                f'border-bottom:1px solid var(--cad-border);font-size:12.5px;">'
                f'<span style="color:{sev_color};font-weight:700;width:50px;'
                f'text-transform:uppercase;font-size:10px;">{_html.escape(sev)}</span>'
                f'<a href="/deal/{_html.escape(did)}" '
                f'style="color:var(--cad-link);text-decoration:none;width:120px;'
                f'font-weight:500;">{_html.escape(name[:20])}</a>'
                f'<span style="color:var(--cad-text2);flex:1;">{_html.escape(str(ar[3] or "")[:80])}</span>'
                f'</div>'
            )
        alert_html = (
            f'<div class="cad-card" style="border-left:3px solid var(--cad-neg);">'
            f'<h2>Active Alerts ({n_alerts})</h2>'
            f'{alert_items}</div>'
        )

    # ── Deal monitoring table ──
    deal_rows = ""
    for did, ddata in sorted(deal_map.items(), key=lambda x: x[1].get("name", "")):
        name = _html.escape(ddata["name"][:25])
        profile = ddata["profile"]

        # Health
        health = ddata["latest_health"]
        if health:
            h_score = health["score"]
            h_color = {"green": "var(--cad-pos)", "amber": "var(--cad-warn)", "red": "var(--cad-neg)"}.get(health["band"], "var(--cad-text3)")
            health_html = f'<span style="color:{h_color};font-weight:600;">{h_score}</span>'
        else:
            health_html = '<span style="color:var(--cad-text3);">—</span>'

        # Latest actual vs plan
        variance_html = "—"
        status_html = ""
        if ddata["actuals"]:
            latest = ddata["actuals"][0]
            kpis_d = latest["kpis"]
            plan_d = latest["plan"]
            ebitda_actual = kpis_d.get("ebitda", 0)
            ebitda_plan = plan_d.get("ebitda", 0)
            if ebitda_plan and ebitda_plan > 0:
                var_pct = (ebitda_actual - ebitda_plan) / ebitda_plan
                var_color = "var(--cad-pos)" if var_pct >= -0.05 else ("var(--cad-warn)" if var_pct >= -0.15 else "var(--cad-neg)")
                variance_html = f'<span style="color:{var_color};font-weight:600;">{var_pct:+.1%}</span>'
                if var_pct >= -0.05:
                    status_html = _sev_badge("on_track")
                elif var_pct >= -0.15:
                    status_html = _sev_badge("lagging")
                else:
                    status_html = _sev_badge("off_track")
            else:
                variance_html = f'{_fm(ebitda_actual)}'

        # Stage
        stage = ""
        if ddata["latest_snapshot"]:
            stage = _html.escape(str(ddata["latest_snapshot"]["stage"] or "")[:12])

        # Alert count
        n_deal_alerts = len(ddata["alerts"])
        alert_badge = ""
        if n_deal_alerts > 0:
            alert_badge = f'<span style="background:var(--cad-neg);color:#fff;padding:0 5px;border-radius:8px;font-size:10px;">{n_deal_alerts}</span>'

        deal_rows += (
            f'<tr>'
            f'<td><a href="/deal/{_html.escape(did)}" '
            f'style="color:var(--cad-link);text-decoration:none;font-weight:500;">'
            f'{name}</a></td>'
            f'<td style="font-size:11px;">{stage}</td>'
            f'<td class="num">{health_html}</td>'
            f'<td class="num">{variance_html}</td>'
            f'<td>{status_html}</td>'
            f'<td class="num">{len(ddata["actuals"])}</td>'
            f'<td>{alert_badge}</td>'
            f'</tr>'
        )

    deal_table = (
        f'<div class="cad-card">'
        f'<h2>Deal Status Board</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'Real-time status for every active deal. Variance = latest quarterly EBITDA actual vs plan. '
        f'Health score is composite 0-100 (green &ge;80, amber 50-79, red &lt;50).</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Deal</th><th>Stage</th><th>Health</th><th>EBITDA Var</th>'
        f'<th>Status</th><th>Quarters</th><th>Alerts</th>'
        f'</tr></thead><tbody>{deal_rows}</tbody></table></div>'
    )

    # ── Predicted vs Actual by Metric ──
    metric_variances: Dict[str, List[float]] = {}
    for did, ddata in deal_map.items():
        for q_data in ddata["actuals"]:
            for metric in ("ebitda", "npsr", "idr_blended", "fwr_blended", "dar_clean_days"):
                actual = q_data["kpis"].get(metric)
                plan = q_data["plan"].get(metric)
                if actual is not None and plan is not None and plan != 0:
                    var = (actual - plan) / abs(plan)
                    metric_variances.setdefault(metric, []).append(var)

    metric_rows = ""
    for metric, variances in sorted(metric_variances.items()):
        if not variances:
            continue
        avg_var = float(np.mean(variances))
        med_var = float(np.median(variances))
        pct_on_track = float(np.mean([1 if abs(v) < 0.05 else 0 for v in variances]))
        pct_off = float(np.mean([1 if abs(v) >= 0.15 else 0 for v in variances]))
        n = len(variances)

        avg_color = "var(--cad-pos)" if abs(avg_var) < 0.05 else ("var(--cad-warn)" if abs(avg_var) < 0.15 else "var(--cad-neg)")
        labels = {"ebitda": "EBITDA", "npsr": "NPSR", "idr_blended": "Denial Rate",
                  "fwr_blended": "Write-Off Rate", "dar_clean_days": "AR Days"}
        label = labels.get(metric, metric.replace("_", " ").title())

        metric_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{_html.escape(label)}</td>'
            f'<td class="num" style="color:{avg_color};font-weight:600;">{avg_var:+.1%}</td>'
            f'<td class="num">{med_var:+.1%}</td>'
            f'<td class="num" style="color:var(--cad-pos);">{pct_on_track:.0%}</td>'
            f'<td class="num" style="color:var(--cad-neg);">{pct_off:.0%}</td>'
            f'<td class="num">{n}</td>'
            f'</tr>'
        )

    pred_vs_actual = ""
    if metric_rows:
        pred_vs_actual = (
            f'<div class="cad-card">'
            f'<h2>Plan vs Actual by Metric (Cross-Portfolio)</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
            f'Aggregated across all deals with quarterly actuals. Shows systematic over/under-performance. '
            f'Positive variance = beating plan.</p>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Metric</th><th>Mean Var</th><th>Median Var</th><th>On Track</th>'
            f'<th>Off Track</th><th>Obs</th>'
            f'</tr></thead><tbody>{metric_rows}</tbody></table></div>'
        )

    # ── Portfolio health distribution bar ──
    total_h = green + amber + red + no_health
    if total_h > 0:
        g_pct = green / total_h * 100
        a_pct = amber / total_h * 100
        r_pct = red / total_h * 100
        n_pct = no_health / total_h * 100
    else:
        g_pct = a_pct = r_pct = n_pct = 0

    health_bar = (
        f'<div class="cad-card">'
        f'<h2>Portfolio Health Distribution</h2>'
        f'<div style="display:flex;height:28px;border-radius:4px;overflow:hidden;margin-bottom:8px;">'
        f'<div style="width:{g_pct:.0f}%;background:var(--cad-pos);" title="Green: {green}"></div>'
        f'<div style="width:{a_pct:.0f}%;background:var(--cad-warn);" title="Amber: {amber}"></div>'
        f'<div style="width:{r_pct:.0f}%;background:var(--cad-neg);" title="Red: {red}"></div>'
        f'<div style="width:{n_pct:.0f}%;background:var(--cad-border);" title="Unscored: {no_health}"></div>'
        f'</div>'
        f'<div style="display:flex;gap:16px;font-size:12px;">'
        f'<span style="color:var(--cad-pos);">&#9632; Green: {green}</span>'
        f'<span style="color:var(--cad-warn);">&#9632; Amber: {amber}</span>'
        f'<span style="color:var(--cad-neg);">&#9632; Red: {red}</span>'
        f'<span style="color:var(--cad-text3);">&#9632; Unscored: {no_health}</span>'
        f'</div></div>'
    )

    # ── Early warning signals ──
    warnings = []
    for did, ddata in deal_map.items():
        name = ddata["name"]
        # Declining health
        if ddata["latest_health"] and ddata["latest_health"]["band"] == "red":
            warnings.append(("red", name, "Health score in red band — immediate attention required"))
        # EBITDA miss
        if ddata["actuals"]:
            latest = ddata["actuals"][0]
            ea = latest["kpis"].get("ebitda", 0)
            ep = latest["plan"].get("ebitda", 0)
            if ep and ep > 0 and (ea - ep) / ep < -0.15:
                warnings.append(("red", name, f"EBITDA {(ea-ep)/ep:+.0%} vs plan — off track"))
            elif ep and ep > 0 and (ea - ep) / ep < -0.05:
                warnings.append(("amber", name, f"EBITDA {(ea-ep)/ep:+.0%} vs plan — lagging"))
        # Multiple alerts
        if len(ddata["alerts"]) >= 3:
            warnings.append(("amber", name, f"{len(ddata['alerts'])} unresolved alerts"))

    warning_html = ""
    if warnings:
        warning_items = ""
        for sev, name, msg in sorted(warnings, key=lambda w: (0 if w[0] == "red" else 1)):
            sev_color = "var(--cad-neg)" if sev == "red" else "var(--cad-warn)"
            warning_items += (
                f'<div style="display:flex;gap:8px;padding:6px 0;'
                f'border-bottom:1px solid var(--cad-border);font-size:12px;">'
                f'<span style="color:{sev_color};font-weight:700;width:14px;">&#9679;</span>'
                f'<span style="font-weight:500;width:120px;">{_html.escape(name[:20])}</span>'
                f'<span style="color:var(--cad-text2);">{_html.escape(msg)}</span>'
                f'</div>'
            )
        warning_html = (
            f'<div class="cad-card" style="border-left:3px solid var(--cad-warn);">'
            f'<h2>Early Warning Signals ({len(warnings)})</h2>'
            f'{warning_items}</div>'
        )

    # ── Nav ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/portfolio" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Portfolio Overview</a>'
        f'<a href="/alerts" class="cad-btn" style="text-decoration:none;">Alerts</a>'
        f'<a href="/model-validation" class="cad-btn" '
        f'style="text-decoration:none;">Model Validation</a>'
        f'<a href="/predictive-screener" class="cad-btn" '
        f'style="text-decoration:none;">Deal Screener</a>'
        f'<a href="/ml-insights" class="cad-btn" '
        f'style="text-decoration:none;">ML Insights</a>'
        f'</div>'
    )

    body = f'{kpis}{alert_html}{warning_html}{health_bar}{deal_table}{pred_vs_actual}{nav}'

    return chartis_shell(
        body, "Portfolio Monitor",
        active_nav="/portfolio/monitor",
        subtitle=(
            f"{n_deals} deals | {n_with_actuals} with actuals | "
            f"{green} green / {amber} amber / {red} red | {n_alerts} alerts"
        ),
    )
