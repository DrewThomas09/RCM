"""PE Desk Portfolio Monitor — actual vs predicted, early warnings.

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
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
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


def _value_creation_panel(store: Any) -> str:
    """Launched vs Realized value-creation progress (portfolio-level).

    Definitions (defensible, stated in the panel):
      * **Launched** — the cumulative *underwritten plan* EBITDA impact
        of initiatives that are in execution. An initiative counts as
        launched once it has at least one quarter of recorded actuals
        (that's how the data model records execution). Σ of pro-rated
        plan across held deals.
      * **Realized** — the cumulative *actual* EBITDA impact recorded to
        date: raw run-rate attribution, NOT trailing-twelve-months and
        NOT re-attributed. Σ of actuals across held deals.
      * **Capture rate** — realized ÷ launched.

    Portfolio-level aggregate (per the fund-model decision to stay
    portfolio-level). Honest empty state when no actuals are recorded —
    never a fabricated number.
    """
    try:
        from ..rcm.initiative_rollup import initiative_portfolio_rollup
        df = initiative_portfolio_rollup(store)
    except Exception:  # noqa: BLE001 — panel must never break the page
        return ""

    launched = realized = 0.0
    n_init = 0
    if df is not None and not df.empty:
        for _, r in df.iterrows():
            plan = r.get("cumulative_plan")
            act = r.get("cumulative_actual")
            if plan is not None and plan == plan:  # NaN guard
                launched += float(plan)
            if act is not None and act == act:
                realized += float(act)
            n_init += 1

    if n_init == 0 or launched <= 0:
        return ck_panel(
            '<p class="ck-section-body" style="margin:0;">'
            'No initiative actuals recorded yet. Launched (underwritten '
            'plan in execution) and realized (actual EBITDA captured) '
            'value populate once a deal logs its first quarterly '
            'initiative actual.</p>',
            title="Value Creation · Launched vs Realized",
        )

    capture = realized / launched if launched else 0.0
    pct = max(0.0, min(100.0, capture * 100.0))
    tone = (PALETTE.get("positive") if capture >= 0.85
            else PALETTE.get("warning") if capture >= 0.6
            else PALETTE.get("negative"))
    bar = (
        f'<div style="margin:10px 0 6px;background:var(--sc-bg-elevated,#faf7f0);'
        f'border:1px solid var(--sc-rule,#d6cfc0);border-radius:3px;height:18px;'
        f'overflow:hidden;">'
        f'<div style="width:{pct:.1f}%;height:100%;background:{tone};"></div></div>'
    )
    return ck_panel(
        '<p class="ck-section-body" style="margin:0 0 4px;">'
        f'<strong>{_fm(realized)}</strong> realized of '
        f'<strong>{_fm(launched)}</strong> launched · '
        f'<strong>{capture*100:.0f}%</strong> of the in-execution plan '
        f'captured across {n_init} initiatives.</p>'
        + bar +
        '<p class="ck-section-body" style="font-size:11px;margin:6px 0 0;">'
        '<em>Launched</em> = cumulative underwritten plan of initiatives '
        'in execution (≥1 quarter of actuals). <em>Realized</em> = '
        'cumulative actual EBITDA impact recorded to date (run-rate, not '
        'TTM, not re-attributed). Portfolio-level.</p>',
        title="Value Creation · Launched vs Realized",
    )


def _health_trend_svg(histories: Dict[str, list]) -> str:
    """Health-score trajectories across the portfolio.

    One line per deal with at least two recorded scores (rows are
    (at_date, score), newest first), drawn on a fixed 0–100 axis with
    the band edges at 50 and 80 as guides — direction is the early
    warning the distribution bar can't show. Deals with a single
    snapshot are counted in the caption, not drawn as fake lines.
    Capped at the 8 most-sampled deals; nothing drawable renders "".
    """
    series = []
    n_single = 0
    for name, pts in histories.items():
        if len(pts) < 2:
            n_single += 1
            continue
        ordered = sorted(pts, key=lambda p: p[0])  # oldest → newest
        series.append((name, ordered))
    if not series:
        return ""
    series.sort(key=lambda s: -len(s[1]))
    series = series[:8]

    width, chart_h = 720, 170
    pad_l, pad_r, pad_top, pad_bot = 36, 130, 10, 22
    plot_w = width - pad_l - pad_r
    height = pad_top + chart_h + pad_bot
    tones = ("#0b2341", "#1F7A75", "#b8732a", "#7a8699",
             "#46617e", "#a98545", "#6e8b8a", "#b5321e")

    def _y(score: float) -> float:
        return pad_top + chart_h * (1 - max(0.0, min(100.0, score)) / 100.0)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img" '
        f'aria-label="Health score trend per deal, 0 to 100">'
    ]
    for band_v, band_lbl in ((80, "GREEN ≥80"), (50, "AMBER ≥50")):
        gy = _y(band_v)
        parts.append(
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l + plot_w}" '
            f'y2="{gy:.1f}" stroke="#d6cfc0" stroke-width="1" '
            f'stroke-dasharray="3,3"/>'
            f'<text x="{pad_l - 4}" y="{gy + 3:.1f}" text-anchor="end" '
            f'font-size="8.5" fill="#9b9382">{band_v}</text>'
            f'<text x="{pad_l + 4}" y="{gy - 3:.1f}" font-size="8" '
            f'letter-spacing="1" fill="#9b9382">{band_lbl}</text>'
        )
    max_n = max(len(pts) for _, pts in series)
    label_specs = []  # (label_y, x, tone, text) — placed after the loop
    for si, (name, pts) in enumerate(series):
        tone = tones[si % len(tones)]
        # X positions: evenly spaced by observation index, right-aligned
        # so every line ends at "now".
        n = len(pts)
        xs = [
            pad_l + plot_w * (max_n - n + k) / max(max_n - 1, 1)
            for k in range(n)
        ]
        path = " ".join(
            f'{"M" if k == 0 else "L"} {xs[k]:.1f} {_y(pts[k][1]):.1f}'
            for k in range(n)
        )
        parts.append(
            f'<path d="{path}" fill="none" stroke="{tone}" '
            f'stroke-width="1.8" stroke-opacity="0.85"/>'
        )
        lx, ly = xs[-1], _y(pts[-1][1])
        parts.append(
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3" fill="{tone}"/>'
        )
        short = name if len(name) <= 16 else name[:15] + "…"
        label_specs.append(
            (ly + 3, lx, tone, f"{_html.escape(short)} {pts[-1][1]}"))
    # End-of-line labels collide when final scores are close (e.g. 100
    # vs 97): sort by y and push any label within 12px of the previous
    # one down so every deal name stays legible.
    label_specs.sort(key=lambda s: s[0])
    prev_y = None
    for ty, lx, tone, text in label_specs:
        if prev_y is not None and ty - prev_y < 12:
            ty = prev_y + 12
        prev_y = ty
        parts.append(
            f'<text x="{lx + 6:.1f}" y="{ty:.1f}" font-size="9" '
            f'fill="{tone}">{text}</text>'
        )
    parts.append("</svg>")
    caption_bits = [
        f"{len(series)} DEALS WITH ≥2 SCORES · LINES END AT THE LATEST "
        "SNAPSHOT",
    ]
    if n_single:
        caption_bits.append(
            f"{n_single} DEAL{'S' if n_single != 1 else ''} WITH A SINGLE "
            "SCORE NOT DRAWN")
    note = (
        '<p class="ck-section-body" style="font-size:10px;color:#7a8699;'
        f'letter-spacing:0.06em;">{" · ".join(caption_bits)}</p>'
    )
    return ck_panel(
        "".join(parts) + note,
        title="Health Score Trend",
    )


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
        # 2026-05-28 sweep batch 19 · empty-state path also uses
        # the universal helper so the page shape is consistent
        # whether the partner has data or not.
        from ._chartis_kit import ck_editorial_head
        return chartis_shell(
            ck_editorial_head(
                eyebrow="PORTFOLIO · MONITOR",
                title="No active deals in portfolio.",
                meta="0 ACTIVE · IMPORT TO POPULATE",
                lede_body="Import deals to start monitoring.",
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

    # Load snapshots for covenant tracking. deal_snapshots has no
    # ``snapshot_json`` column (its fields are flat REAL/TEXT columns)
    # — the old SELECT raised into the bare except, so the stage
    # column on this page was always blank.
    try:
        with store.connect() as con:
            snapshots = con.execute(
                "SELECT deal_id, stage, notes, created_at "
                "FROM deal_snapshots ORDER BY created_at DESC"
            ).fetchall()
    except Exception:
        snapshots = []

    # Load health scores. (The column is ``at_date`` — the old
    # ``ORDER BY date`` raised "no such column" into the bare except,
    # so health scores NEVER rendered on this page.)
    try:
        with store.connect() as con:
            health_rows = con.execute(
                "SELECT deal_id, at_date, score, band "
                "FROM deal_health_history ORDER BY at_date DESC"
            ).fetchall()
    except Exception:
        health_rows = []

    # Load alerts — persisted sightings live in alert_history (acks in
    # alert_acks); there is no ``alerts`` table, so the old query
    # always fell into the except and this page never showed alerts.
    try:
        with store.connect() as con:
            alert_rows = con.execute(
                "SELECT h.deal_id, h.severity, h.kind, "
                "h.title AS message, h.last_seen_at AS fired_at "
                "FROM alert_history h LEFT JOIN alert_acks a "
                "ON a.kind = h.kind AND a.deal_id = h.deal_id "
                "AND a.trigger_key = h.trigger_key "
                "WHERE a.ack_id IS NULL "
                "ORDER BY h.last_seen_at DESC LIMIT 30"
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

    health_histories: Dict[str, list] = {}
    for hr in health_rows:
        did = hr[0]
        if did not in deal_map:
            continue
        if deal_map[did]["latest_health"] is None:
            deal_map[did]["latest_health"] = {"score": hr[2], "band": hr[3]}
        health_histories.setdefault(
            deal_map[did]["name"], []).append((str(hr[1]), int(hr[2])))

    for sr in snapshots:
        did = sr[0]
        if did in deal_map and deal_map[did]["latest_snapshot"] is None:
            deal_map[did]["latest_snapshot"] = {"stage": sr[1], "data": {}}

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
    # 2026-05-28 sweep batch 19 · strict 5-block head via the
    # universal kit helper. Replaces ck_section_intro to eliminate
    # the dual-h1 trap and bring this page in line with /portfolio,
    # /pipeline, /home, /day-one, /bear-cases, etc.
    from ._chartis_kit import ck_editorial_head
    intro = ck_editorial_head(
        eyebrow="PORTFOLIO MONITOR",
        title="Portfolio Monitor",
        meta=(
            f"{n_deals} ACTIVE DEAL"
            f"{'S' if n_deals != 1 else ''} · "
            f"{n_with_actuals} WITH ACTUALS · "
            f"{green}G / {amber}A / {red}R · "
            f"{n_alerts} OPEN ALERT"
            f"{'S' if n_alerts != 1 else ''}"
        ),
        lede_body=(
            "The daily read on every held deal: actual vs plan, health "
            "trajectory, and the early warnings that deserve a partner's "
            "attention before the next quarterly close."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Active Deals", f"{n_deals}",
            help={
                "definition": (
                    "Deals still in hold: excludes exited / "
                    "archived. The portfolio surface tracks each "
                    "one's variance vs plan; the bands below split "
                    "them by health."
                ),
            },
        )
        + ck_kpi_block(
            "With Actuals", f"{n_with_actuals}",
            help={
                "definition": (
                    "Deals with at least one quarter of actuals "
                    "loaded. Variance bands only apply to these: "
                    "deals with no actuals yet show neutral until "
                    "Q1 reports."
                ),
            },
        )
        + ck_kpi_block(
            "Green", f"{green}",
            help={
                "definition": (
                    "Deals tracking within 5% of plan on the "
                    "composite health score. No partner action "
                    "needed; the watchlist surfaces these as "
                    "background."
                ),
            },
        )
        + ck_kpi_block(
            "Amber", f"{amber}",
            help={
                "definition": (
                    "Deals tracking 5-15% below plan. Partner sees "
                    "the variance, no escalation required yet: "
                    "the alerts panel below explains the cohort "
                    "drift."
                ),
            },
        )
        + ck_kpi_block(
            "Red", f"{red}",
            help={
                "definition": (
                    "Deals tracking >15% below plan OR covenant-"
                    "headroom narrowing. Triggers escalation to "
                    "the deal-owning partner; LP digest carries a "
                    "narrative on each."
                ),
            },
        )
        + ck_kpi_block(
            "Open Alerts", f"{n_alerts}",
            help={
                "definition": (
                    "Active alerts across the portfolio not yet "
                    "acked or snoozed. Click into /alerts to "
                    "triage: each carries severity, age, and the "
                    "ack form."
                ),
            },
        )
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
                f'<a href="/deal/{_html.escape(did)}" class="ck-link pm-alert-name" '
                f'title="{_html.escape(name)}">'
                f'<strong>{_html.escape(name if len(name) <= 40 else name[:39] + "…")}</strong></a>'
                f'<span class="pm-alert-msg">{_html.escape(str(ar[3] or "")[:80])}</span>'
                '</div>'
            )
        alert_html = ck_panel(
            alert_items, title=f"Active Alerts ({n_alerts})",
        )

    # ── Deal monitoring table ──
    deal_rows = ""
    for did, ddata in sorted(deal_map.items(), key=lambda x: x[1].get("name", "")):
        full_name = ddata["name"]
        name = _html.escape(
            full_name if len(full_name) <= 40 else full_name[:39] + "…")
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

        # Stage — same uppercase chip /portfolio uses, not raw
        # lowercase text.
        stage = ""
        if ddata["latest_snapshot"]:
            stage_raw = _html.escape(
                str(ddata["latest_snapshot"]["stage"] or "")[:12])
            if stage_raw:
                stage = (
                    f'<span class="cad-badge cad-badge-muted">'
                    f'{stage_raw}</span>'
                )

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
    ) + _health_trend_svg(health_histories)

    # ── Early warning signals ──
    warnings = []
    for did, ddata in deal_map.items():
        name = ddata["name"]
        # Declining health
        if ddata["latest_health"] and ddata["latest_health"]["band"] == "red":
            warnings.append(("red", name, "Health score in red band: immediate attention required"))
        # EBITDA miss
        if ddata["actuals"]:
            latest = ddata["actuals"][0]
            ea = latest["kpis"].get("ebitda", 0)
            ep = latest["plan"].get("ebitda", 0)
            if ep and ep > 0 and (ea - ep) / ep < -0.15:
                warnings.append(("red", name, f"EBITDA {(ea-ep)/ep:+.0%} vs plan: off track"))
            elif ep and ep > 0 and (ea - ep) / ep < -0.05:
                warnings.append(("amber", name, f"EBITDA {(ea-ep)/ep:+.0%} vs plan: lagging"))
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
                f'<span class="pm-warn-name" title="{_html.escape(name)}">'
                f'<strong>{_html.escape(name if len(name) <= 40 else name[:39] + "…")}</strong></span>'
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
    next_up = ck_next_section(
        "Open the portfolio risk scan",
        "/portfolio/risk-scan",
        eyebrow="Up next",
        italic_word="risk",
    )
    value_creation = _value_creation_panel(store)

    body = (
        f'{pm_styles}{intro}{kpis}{alert_html}{warning_html}'
        f'{health_bar}{deal_table}{value_creation}{pred_vs_actual}{nav}{next_up}'
    )

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, "Portfolio Monitor",
        active_nav="/portfolio/monitor",
        subtitle=(
            f"{n_deals} deals | {n_with_actuals} with actuals | "
            f"{green} green / {amber} amber / {red} red | {n_alerts} alerts"
        ),
    )
