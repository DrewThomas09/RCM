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

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_panel,
    ck_section_intro, ck_signal_badge,
)
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
    tones = {
        "on_track": "positive", "SAFE": "positive",
        "lagging": "warning", "TIGHT": "warning",
        "off_track": "negative", "TRIPPED": "negative",
    }
    labels = {"on_track": "On Track", "lagging": "Lagging", "off_track": "Off Track",
              "SAFE": "Safe", "TIGHT": "Tight", "TRIPPED": "Tripped"}
    return ck_signal_badge(labels.get(sev, sev), tone=tones.get(sev, "neutral"))


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
            ck_section_intro(
                eyebrow="PORTFOLIO MONITOR",
                headline="No active deals in portfolio.",
                italic_word="No",
                body="Import deals to start monitoring.",
            ),
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

    # ── Editorial intro + KPI strip ──
    intro = ck_section_intro(
        eyebrow="PORTFOLIO MONITOR",
        headline="What needs the partner's attention this week.",
        italic_word="attention",
        body=(
            f"{n_deals} active deals · {n_with_actuals} with quarterly "
            f"actuals · {green} green / {amber} amber / {red} red · "
            f"{n_alerts} open alerts."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Active Deals", f"{n_deals}")
        + ck_kpi_block("With Actuals", f"{n_with_actuals}")
        + ck_kpi_block("Green", f"{green}")
        + ck_kpi_block("Amber", f"{amber}")
        + ck_kpi_block("Red", f"{red}")
        + ck_kpi_block("Open Alerts", f"{n_alerts}")
        + '</div>'
    )

    # ── Active alerts ──
    alert_html = ""
    if alert_rows:
        alert_items = ""
        for ar in alert_rows[:10]:
            did = ar[0]
            sev = ar[1]
            sev_cls = {"red": "cad-neg", "amber": "cad-warn"}.get(sev, "")
            name = deal_map.get(did, {}).get("name", did)
            alert_items += (
                '<div class="pm-alert-row">'
                f'<span class="pm-alert-sev {sev_cls}">{_html.escape(sev)}</span>'
                f'<a href="/deal/{_html.escape(did)}" class="ck-link pm-alert-name">'
                f'<strong>{_html.escape(name[:20])}</strong></a>'
                f'<span class="pm-alert-msg">{_html.escape(str(ar[3] or "")[:80])}</span>'
                '</div>'
            )
        alert_html = ck_panel(
            alert_items, title=f"Active Alerts ({n_alerts})",
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
            h_cls = {"green": "cad-pos", "amber": "cad-warn", "red": "cad-neg"}.get(health["band"], "")
            health_html = f'<span class="{h_cls}"><strong>{h_score}</strong></span>'
        else:
            health_html = '—'

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
                var_cls = "cad-pos" if var_pct >= -0.05 else ("cad-warn" if var_pct >= -0.15 else "cad-neg")
                variance_html = f'<span class="{var_cls}"><strong>{var_pct:+.1%}</strong></span>'
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
        alert_badge = (
            f'<span class="cad-badge cad-badge-red">{n_deal_alerts}</span>'
            if n_deal_alerts > 0 else ""
        )

        deal_rows += (
            f'<tr>'
            f'<td><a href="/deal/{_html.escape(did)}" class="ck-link"><strong>{name}</strong></a></td>'
            f'<td>{stage}</td>'
            f'<td class="num">{health_html}</td>'
            f'<td class="num">{variance_html}</td>'
            f'<td>{status_html}</td>'
            f'<td class="num">{len(ddata["actuals"])}</td>'
            f'<td>{alert_badge}</td>'
            f'</tr>'
        )

    deal_table = ck_panel(
        '<p class="ck-section-body">'
        'Real-time status for every active deal. Variance = latest quarterly EBITDA actual vs plan. '
        'Health score is composite 0-100 (green ≥80, amber 50-79, red &lt;50).</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Deal</th><th>Stage</th><th>Health</th><th>EBITDA Var</th>'
        '<th>Status</th><th>Quarters</th><th>Alerts</th>'
        f'</tr></thead><tbody>{deal_rows}</tbody></table>',
        title="Deal Status Board",
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

        avg_cls = "cad-pos" if abs(avg_var) < 0.05 else ("cad-warn" if abs(avg_var) < 0.15 else "cad-neg")
        labels = {"ebitda": "EBITDA", "npsr": "NPSR", "idr_blended": "Denial Rate",
                  "fwr_blended": "Write-Off Rate", "dar_clean_days": "AR Days"}
        label = labels.get(metric, metric.replace("_", " ").title())

        metric_rows += (
            f'<tr>'
            f'<td><strong>{_html.escape(label)}</strong></td>'
            f'<td class="num {avg_cls}"><strong>{avg_var:+.1%}</strong></td>'
            f'<td class="num">{med_var:+.1%}</td>'
            f'<td class="num cad-pos">{pct_on_track:.0%}</td>'
            f'<td class="num cad-neg">{pct_off:.0%}</td>'
            f'<td class="num">{n}</td>'
            f'</tr>'
        )

    pred_vs_actual = ""
    if metric_rows:
        pred_vs_actual = ck_panel(
            '<p class="ck-section-body">'
            'Aggregated across all deals with quarterly actuals. Shows systematic over/under-performance. '
            'Positive variance = beating plan.</p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Metric</th><th>Mean Var</th><th>Median Var</th><th>On Track</th>'
            '<th>Off Track</th><th>Obs</th>'
            f'</tr></thead><tbody>{metric_rows}</tbody></table>',
            title="Plan vs Actual by Metric (Cross-Portfolio)",
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

    health_bar = ck_panel(
        '<div class="pm-health-bar">'
        f'<div class="pm-health-pos" style="width:{g_pct:.0f}%;" title="Green: {green}"></div>'
        f'<div class="pm-health-warn" style="width:{a_pct:.0f}%;" title="Amber: {amber}"></div>'
        f'<div class="pm-health-neg" style="width:{r_pct:.0f}%;" title="Red: {red}"></div>'
        f'<div class="pm-health-none" style="width:{n_pct:.0f}%;" title="Unscored: {no_health}"></div>'
        '</div>'
        '<p class="ck-section-body">'
        f'<span class="cad-pos">■ Green: {green}</span> &nbsp; '
        f'<span class="cad-warn">■ Amber: {amber}</span> &nbsp; '
        f'<span class="cad-neg">■ Red: {red}</span> &nbsp; '
        f'<span>■ Unscored: {no_health}</span>'
        '</p>',
        title="Portfolio Health Distribution",
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
            sev_cls = "cad-neg" if sev == "red" else "cad-warn"
            warning_items += (
                '<div class="pm-warn-row">'
                f'<span class="pm-warn-sev {sev_cls}">●</span>'
                f'<span class="pm-warn-name"><strong>{_html.escape(name[:20])}</strong></span>'
                f'<span>{_html.escape(msg)}</span>'
                '</div>'
            )
        warning_html = ck_panel(
            warning_items, title=f"Early Warning Signals ({len(warnings)})",
        )

    # ── Nav ──
    nav = ck_panel(
        '<p class="ck-section-body">'
        '<a href="/portfolio" class="cad-btn cad-btn-primary">Portfolio Overview</a> '
        '<a href="/alerts" class="cad-btn">Alerts</a> '
        '<a href="/model-validation" class="cad-btn">Model Validation</a> '
        '<a href="/predictive-screener" class="cad-btn">Deal Screener</a> '
        '<a href="/ml-insights" class="cad-btn">ML Insights</a>'
        '</p>',
        title="Cross-links",
    )

    pm_styles = """
<style>
.pm-alert-row{display:flex;gap:10px;padding:8px 0;
border-bottom:1px solid var(--cad-border);font-size:12.5px;}
.pm-alert-sev{font-weight:700;width:50px;text-transform:uppercase;font-size:10px;}
.pm-alert-name{width:120px;}
.pm-alert-msg{flex:1;}
.pm-warn-row{display:flex;gap:8px;padding:6px 0;
border-bottom:1px solid var(--cad-border);font-size:12px;}
.pm-warn-sev{font-weight:700;width:14px;}
.pm-warn-name{width:120px;}
.pm-health-bar{display:flex;height:28px;border-radius:4px;
overflow:hidden;margin-bottom:8px;}
.pm-health-pos{background:var(--cad-pos);}
.pm-health-warn{background:var(--cad-warn);}
.pm-health-neg{background:var(--cad-neg);}
.pm-health-none{background:var(--cad-border);}
</style>
"""
    body = f'{pm_styles}{intro}{kpis}{alert_html}{warning_html}{health_bar}{deal_table}{pred_vs_actual}{nav}'

    return chartis_shell(
        body, "Portfolio Monitor",
        active_nav="/portfolio/monitor",
        subtitle=(
            f"{n_deals} deals | {n_with_actuals} with actuals | "
            f"{green} green / {amber} amber / {red} red | {n_alerts} alerts"
        ),
    )
