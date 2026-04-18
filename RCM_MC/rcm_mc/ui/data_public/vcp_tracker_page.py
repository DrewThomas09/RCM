"""Value Creation Plan (VCP) / 100-Day Plan Tracker — /vcp-tracker."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _status_color(status: str) -> str:
    return {
        "on track": P["accent"],
        "complete": P["positive"],
        "behind": P["negative"],
        "at risk": P["warning"],
    }.get(status, P["text_dim"])


def _plan_color(status: str) -> str:
    return {
        "green": P["positive"],
        "amber": P["warning"],
        "red": P["negative"],
    }.get(status, P["text_dim"])


def _scorecard_color(sc: str) -> str:
    return {"beat": P["positive"], "in line": P["accent"], "miss": P["negative"]}.get(sc, P["text_dim"])


def _levers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Sector","left"),("Category","center"),("Initiative","left"),
            ("Target ($M)","right"),("Realized ($M)","right"),("Realization %","right"),
            ("Status","center"),("Owner","left"),("Target Close","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, l in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(l.status)
        r_c = pos if l.realization_pct >= 0.85 else (acc if l.realization_pct >= 0.65 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(l.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.sector)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(l.lever_category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:340px">{_html.escape(l.initiative)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${l.target_ebitda_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">${l.realized_ebitda_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{l.realization_pct * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(l.status)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(l.owner)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(l.target_completion)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _hundred_day_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Deal","left"),("Days Post-Close","right"),("Total","right"),("Complete","right"),
            ("On Track","right"),("At Risk","right"),("Overdue","right"),("Completion %","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = _plan_color(h.plan_status)
        c_c = pos if h.completion_pct >= 0.85 else (acc if h.completion_pct >= 0.70 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(h.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{h.days_post_close}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{h.total_milestones}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{h.complete}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{h.on_track}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn};font-weight:600">{h.at_risk}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if h.overdue > 0 else text_dim};font-weight:600">{h.overdue}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{h.completion_pct * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{p_c};border:1px solid {p_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(h.plan_status).upper()}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _kpi_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Deal","left"),("Revenue YoY","right"),("EBITDA YoY","right"),("Margin (bps)","right"),
            ("Same-Store Vol","right"),("WC Days Δ","right"),("Budget Achieve","right"),("Scorecard","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, k in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _scorecard_color(k.scorecard)
        r_c = pos if k.revenue_growth_pct >= 0.12 else (acc if k.revenue_growth_pct >= 0.08 else text_dim)
        e_c = pos if k.ebitda_growth_pct >= 0.15 else (acc if k.ebitda_growth_pct >= 0.10 else text_dim)
        b_c = pos if k.ebitda_beat_budget_pct >= 1.0 else neg
        wc_c = pos if k.wc_days_change <= -7 else (acc if k.wc_days_change <= -3 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(k.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">+{k.revenue_growth_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">+{k.ebitda_growth_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">+{k.margin_expansion_bps}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">+{k.same_store_volume_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{wc_c};font-weight:600">{k.wc_days_change:+d}d</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{b_c};font-weight:700">{k.ebitda_beat_budget_pct * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(k.scorecard).upper()}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _interventions_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Deal","left"),("Date","right"),("Type","left"),("Severity","center"),
            ("Rationale","left"),("Outcome","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    sev_c = {"critical": neg, "high": warn, "medium": acc, "low": text_dim}
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c = sev_c.get(r.severity, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(r.intervention_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(r.intervention_type)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{c};border:1px solid {c};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.severity)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(r.rationale)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.outcome)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _bridges_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Lever Category","left"),("Deals","right"),("Target Agg ($M)","right"),
            ("Realized Agg ($M)","right"),("Realization %","right"),("Contribution %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if b.realization_pct >= 0.85 else (acc if b.realization_pct >= 0.65 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(b.lever_category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{b.deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${b.aggregate_target_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${b.aggregate_realized_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{b.realization_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.contribution_to_growth_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _top_init_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Initiative","left"),("Deployed","right"),("Median Realization","right"),("Top Quartile","right"),
            ("Timeline (days)","right"),("Avg EBITDA Lift","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        m_c = pos if t.median_realization_pct >= 0.85 else (acc if t.median_realization_pct >= 0.70 else warn)
        e_c = pos if t.avg_ebitda_lift_pct >= 0.07 else acc
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600;max-width:340px">{_html.escape(t.initiative)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{t.deals_deployed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c};font-weight:700">{t.median_realization_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{t.top_quartile_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.typical_timeline_days}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">+{t.avg_ebitda_lift_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_vcp_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.vcp_tracker import compute_vcp_tracker
    r = compute_vcp_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    kpi_strip = (
        ck_kpi_block("Active Deals", str(r.total_deals), "", "") +
        ck_kpi_block("Target EBITDA Lift", f"${r.total_target_ebitda_m:.1f}M", "", "") +
        ck_kpi_block("Realized", f"${r.total_realized_ebitda_m:.1f}M", "", "") +
        ck_kpi_block("Realization %", f"{r.realization_pct * 100:.1f}%", "", "") +
        ck_kpi_block("On-Track %", f"{r.on_track_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg Days Post-Close", str(r.avg_days_post_close), "d", "") +
        ck_kpi_block("Total Levers", str(len(r.levers)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    l_tbl = _levers_table(r.levers)
    p_tbl = _hundred_day_table(r.hundred_day_plans)
    k_tbl = _kpi_table(r.kpi_scorecards)
    int_tbl = _interventions_table(r.interventions)
    b_tbl = _bridges_table(r.bridges)
    t_tbl = _top_init_table(r.top_initiatives)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    beat_count = sum(1 for k in r.kpi_scorecards if k.scorecard == "beat")
    interv_critical = sum(1 for i in r.interventions if i.severity == "critical")
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Value Creation Plan (VCP) / 100-Day Plan Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_deals} active deals · ${r.total_realized_ebitda_m:.1f}M realized vs ${r.total_target_ebitda_m:.1f}M target ({r.realization_pct * 100:.1f}%) · {r.on_track_pct * 100:.1f}% levers on track or complete · {beat_count} of {len(r.kpi_scorecards)} deals beat budget — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">EBITDA Bridge — Realized by Lever Category</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">100-Day Plan Execution</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">KPI Scorecards — Revenue / EBITDA / Margin / Volume / WC / Budget</div>{k_tbl}</div>
  <div style="{cell}"><div style="{h3}">Individual Value Levers</div>{l_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sponsor Interventions</div>{int_tbl}</div>
  <div style="{cell}"><div style="{h3}">Portfolio-Wide Initiative Benchmarks</div>{t_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">VCP Portfolio Summary:</strong> {r.total_deals} deals executing against ${r.total_target_ebitda_m:.1f}M EBITDA value-creation plan — ${r.total_realized_ebitda_m:.1f}M realized ({r.realization_pct * 100:.1f}%) at average {r.avg_days_post_close} days post-close.
    {r.on_track_pct * 100:.1f}% of levers on track or complete; 5 of 26 levers "behind" are concentrated in RCM migration (Magnolia), payer mix (Redwood), and new-market entry (Willow) — all tractable with incremental resource commitment.
    Commercial and M&A lever categories carry the largest contribution to EBITDA growth — margin expansion averaging 160bps across beat-budget deals supports thesis integrity.
    {beat_count} of {len(r.kpi_scorecards)} portfolio companies beat budget — 3 misses (Redwood, Willow, Ash) have {interv_critical} active sponsor intervention(s) and are showing early response signals.
    Bolt-on M&A (22 deployments, 78% median realization) and back-office consolidation (19 deployments, 89% median) are the highest-reliability value creation plays.
    RCM migration, AI/digital (52-58% realization), and new-market de novo (68%) are the riskiest playbook items — budget 30-40% execution buffer.
  </div>
</div>"""

    return chartis_shell(body, "VCP Tracker", active_nav="/vcp-tracker")
