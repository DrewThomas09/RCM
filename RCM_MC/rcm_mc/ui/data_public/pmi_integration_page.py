"""PMI / Post-Merger Integration Scorecard Tracker — /pmi-integration."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _status_color(s: str) -> str:
    return {
        "on track": P["positive"],
        "ahead": P["positive"],
        "on time": P["positive"],
        "early stage": P["accent"],
        "late": P["warning"],
        "behind": P["negative"],
        "at risk": P["negative"],
    }.get(s, P["text_dim"])


def _severity_color(s: str) -> str:
    return {"high": P["negative"], "medium": P["warning"], "low": P["text_dim"]}.get(s, P["text_dim"])


def _difficulty_color(d: str) -> str:
    return {"low": P["positive"], "medium": P["accent"], "high": P["warning"]}.get(d, P["text_dim"])


def _integrations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Platform","left"),("Bolt-On","left"),("Close Date","right"),("Months","right"),
            ("Deal Value ($M)","right"),("Synergy Target ($M)","right"),("Realized ($M)","right"),
            ("Realization %","right"),("Integration Cost ($M)","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(d.integration_status)
        r_c = pos if d.realization_pct >= 0.70 else (acc if d.realization_pct >= 0.45 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(d.platform)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(d.bolt_on)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(d.close_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{d.months_post_close}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${d.deal_value_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${d.synergy_target_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${d.synergy_realized_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{d.realization_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">${d.integration_cost_m:.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(d.integration_status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _workstreams_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Platform","left"),("Bolt-On","left"),("Workstream","left"),("Total","right"),
            ("Complete","right"),("In Progress","right"),("Blocked","right"),
            ("Completion %","right"),("Owner","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, w in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if w.completion_pct >= 0.85 else (acc if w.completion_pct >= 0.70 else warn)
        b_c = neg if w.blocked > 0 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(w.platform)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(w.bolt_on)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(w.workstream)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{w.total_milestones}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{w.completed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{w.in_progress}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{b_c};font-weight:700">{w.blocked}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{w.completion_pct * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(w.owner)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _categories_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Synergy Category","left"),("Deals","right"),("Target ($M)","right"),("Realized ($M)","right"),
            ("Realization %","right"),("Timeline (mo)","right"),("Difficulty","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = _difficulty_color(c.difficulty)
        r_c = pos if c.realization_pct >= 0.70 else (acc if c.realization_pct >= 0.50 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${c.total_target_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.total_realized_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{c.realization_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.typical_timeline_months}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{d_c};border:1px solid {d_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.difficulty)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _risks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Platform","left"),("Bolt-On","left"),("Risk","left"),("Severity","center"),
            ("Workstream","left"),("Mitigation","left"),("Owner","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _severity_color(r.severity)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.platform)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(r.bolt_on)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:360px">{_html.escape(r.risk)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.severity)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(r.workstream)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(r.mitigation)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.owner)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _milestones_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Platform","left"),("Milestone","left"),("Target Date","right"),("Actual Date","right"),
            ("Status","center"),("Variance (days)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(m.status)
        v_c = pos if m.variance_days <= 0 else (P["warning"] if m.variance_days <= 15 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(m.platform)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:380px">{_html.escape(m.milestone)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(m.target_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.actual_date) if m.actual_date else "—"}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.status)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{v_c};font-weight:700">{m.variance_days:+d}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _retention_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Platform","left"),("Bolt-On","left"),("Physicians Retained","right"),("Lost","right"),
            ("Retention %","right"),("Patient Retention %","right"),("Staff Retention %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if r.retention_rate_pct >= 0.95 else (acc if r.retention_rate_pct >= 0.90 else warn)
        p_c = pos if r.key_patients_retained_pct >= 0.95 else (acc if r.key_patients_retained_pct >= 0.92 else warn)
        s_c = pos if r.staff_retention_pct >= 0.90 else (acc if r.staff_retention_pct >= 0.85 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.platform)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(r.bolt_on)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{r.physicians_retained}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"] if r.physicians_lost > 0 else text_dim}">{r.physicians_lost}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{r.retention_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{r.key_patients_retained_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">{r.staff_retention_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_pmi_integration(params: dict = None) -> str:
    from rcm_mc.data_public.pmi_integration import compute_pmi_integration
    r = compute_pmi_integration()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("Integrations", str(r.total_integrations), "", "") +
        ck_kpi_block("Synergy Target", f"${r.total_synergy_target_m:.1f}M", "", "") +
        ck_kpi_block("Realized", f"${r.total_synergy_realized_m:.1f}M", "", "") +
        ck_kpi_block("Realization", f"{r.weighted_realization_pct * 100:.0f}%", "", "") +
        ck_kpi_block("Integration Cost", f"${r.total_integration_cost_m:.1f}M", "", "") +
        ck_kpi_block("On Track", f"{r.on_track_count}/{r.total_integrations}", "", "") +
        ck_kpi_block("Active Risks", str(len(r.risks)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    d_tbl = _integrations_table(r.integrations)
    w_tbl = _workstreams_table(r.workstreams)
    c_tbl = _categories_table(r.synergy_categories)
    rk_tbl = _risks_table(r.risks)
    m_tbl = _milestones_table(r.milestones)
    rt_tbl = _retention_table(r.retention)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    avg_retention = sum(x.retention_rate_pct for x in r.retention) / len(r.retention) if r.retention else 0
    high_risk = sum(1 for risk in r.risks if risk.severity == "high")
    late_milestones = sum(1 for m in r.milestones if m.variance_days > 0)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">PMI / Post-Merger Integration Scorecard</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_integrations} active integrations · ${r.total_synergy_target_m:.1f}M synergy target · ${r.total_synergy_realized_m:.1f}M realized ({r.weighted_realization_pct * 100:.0f}%) · ${r.total_integration_cost_m:.1f}M integration cost · {r.on_track_count}/{r.total_integrations} on track — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Integration Deals — Synergy Realization</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Synergy Categories — Portfolio Aggregate</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Workstream Execution</div>{w_tbl}</div>
  <div style="{cell}"><div style="{h3}">Milestone Schedule</div>{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Active Integration Risks</div>{rk_tbl}</div>
  <div style="{cell}"><div style="{h3}">Physician, Patient & Staff Retention</div>{rt_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">PMI Scorecard Summary:</strong> {r.total_integrations} active integrations tracking ${r.total_synergy_target_m:.1f}M synergy target with {r.weighted_realization_pct * 100:.0f}% realization ({r.on_track_count} on track, {r.total_integrations - r.on_track_count} early-stage or behind).
    Best-realizing categories: Insurance consolidation (79.2%), G&A overhead (78.9%), Tax optimization (73.8%), GPO supply chain (73.0%) — low-difficulty, short-timeline wins being captured.
    Challenging categories: EHR / IT integration (45.9%), Ancillary revenue capture (44.3%), Revenue cycle automation (49.4%), Payer contract consolidation (54.4%) — longer timelines + organizational complexity.
    Highest-synergy deals: Dallas Cardiology (Cedar, $10.5M realized / $16.5M target), Atlanta Endoscopy (Cypress, $8.5M / $12.5M), Phoenix Ortho (Magnolia, $7.2M / $9.5M).
    Retention health: {avg_retention * 100:.1f}% average physician retention across 15 bolt-ons — Pacific Eye (Aspen) 86% is single weakest; 3 physician departures driving remediation.
    Risk profile: {high_risk} high-severity + {sum(1 for risk in r.risks if risk.severity == "medium")} medium-severity active risks; {late_milestones} late milestones — corrective action in place on all items.
    Integration cost ${r.total_integration_cost_m:.1f}M tracks 22% of ${r.total_synergy_target_m:.1f}M target (within 20-25% industry benchmark); Pacific Eye integration cost running slightly elevated.
  </div>
</div>"""

    return chartis_shell(body, "PMI Scorecard", active_nav="/pmi-integration")
