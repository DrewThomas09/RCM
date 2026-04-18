"""Post-Merger Integration Playbook — /pmi-playbook."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _workstreams_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Workstream","left"),("Owner","left"),("Total","right"),("Completed","right"),
            ("On Track","right"),("Status","center"),("Budget ($M)","right"),("Spent ($M)","right"),("Next Milestone","left"),("Due","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    stat_c = {"on track": pos, "ahead": pos, "at risk": warn, "lagging": neg}
    for i, w in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_c.get(w.status, text_dim)
        ot_c = pos if w.on_track_pct >= 0.80 else (warn if w.on_track_pct >= 0.60 else neg)
        over_budget = w.spent_mm > w.budget_mm * 0.95
        sp_c = neg if over_budget else text
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(w.workstream)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(w.owner)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{w.total_milestones}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{w.completed_milestones}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ot_c};font-weight:700">{w.on_track_pct * 100:.0f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(w.status)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${w.budget_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sp_c}">${w.spent_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(w.next_milestone)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(w.due_date)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _synergy_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Synergy Category","left"),("Target ($M)","right"),("Run-Rate ($M)","right"),
            ("% of Target","right"),("Timing","center"),("Risk","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    t_c = {"ahead": pos, "on track": acc, "behind": neg}
    r_c = {"low": pos, "medium": warn, "high": neg}
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = t_c.get(s.timing_status, text_dim)
        rc = r_c.get(s.risk_level, text_dim)
        p_c = pos if s.pct_of_target >= 0.75 else (warn if s.pct_of_target >= 0.55 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.synergy_category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.annualized_target_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.run_rate_achieved_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{s.pct_of_target * 100:.0f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.timing_status)}</span></td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.risk_level)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _milestones_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Horizon","left"),("Target","right"),("Completed","right"),("In Progress","right"),
            ("Slipped","right"),("Completion %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = pos if m.completion_pct >= 0.90 else (acc if m.completion_pct >= 0.80 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(m.horizon)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{m.target_milestones}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{m.completed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{m.in_progress}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{m.slipped}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{m.completion_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _risks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Risk Area","left"),("Description","left"),("Probability","center"),
            ("Impact ($M)","right"),("Mitigation","center"),("Owner","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    p_c = {"high": neg, "medium": warn, "low": text_dim}
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = p_c.get(r.probability, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.risk_area)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.description)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.probability)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${r.impact_mm:,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(r.mitigation_status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(r.owner)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tms_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Function","left"),("Pre-Integration ($M)","right"),("Post-Integration ($M)","right"),
            ("Actual Savings ($M)","right"),("Target Savings ($M)","right"),("Variance %","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        v_c = pos if t.variance_pct >= -0.10 else (P["warning"] if t.variance_pct >= -0.20 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(t.function)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${t.pre_integration_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${t.post_integration_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${t.actual_savings_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${t.targeted_savings_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{v_c};font-weight:700">{t.variance_pct * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_pmi_playbook(params: dict = None) -> str:
    from rcm_mc.data_public.pmi_playbook import compute_pmi_playbook
    r = compute_pmi_playbook()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    synergy_pct = r.run_rate_synergies_mm / r.total_synergies_target_mm if r.total_synergies_target_mm else 0
    budget_util = r.integration_spend_mm / r.integration_budget_mm if r.integration_budget_mm else 0
    prog_c = pos if r.overall_progress_pct >= 0.80 else (acc if r.overall_progress_pct >= 0.65 else P["warning"])

    kpi_strip = (
        ck_kpi_block("Target", r.target_acquisition[:16], "", "") +
        ck_kpi_block("Close Date", r.close_date, "", "") +
        ck_kpi_block("Days Since Close", str(r.days_since_close), "", "") +
        ck_kpi_block("Overall Progress", f"{r.overall_progress_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Synergy Run-Rate", f"${r.run_rate_synergies_mm:,.1f}M", "", "") +
        ck_kpi_block("Synergy Target", f"${r.total_synergies_target_mm:,.1f}M", "", "") +
        ck_kpi_block("Synergy %", f"{synergy_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Budget Util", f"{budget_util * 100:.1f}%", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    w_tbl = _workstreams_table(r.workstreams)
    s_tbl = _synergy_table(r.synergies)
    m_tbl = _milestones_table(r.milestones)
    rsk_tbl = _risks_table(r.risks)
    t_tbl = _tms_table(r.tms)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Post-Merger Integration Playbook</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Workstream tracking · synergy capture · Day 1/100/365 milestones · integration risk register · TMS cost savings — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {prog_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">Integration Status — {_html.escape(r.target_acquisition)}</div>
    <div style="color:{prog_c};font-weight:700;font-size:14px">Day {r.days_since_close} · {r.overall_progress_pct * 100:.1f}% complete · ${r.run_rate_synergies_mm:,.1f}M run-rate synergies ({synergy_pct * 100:.0f}% of target)</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Integration spend ${r.integration_spend_mm:,.1f}M / ${r.integration_budget_mm:,.1f}M budget ({budget_util * 100:.0f}% util)</div>
  </div>
  <div style="{cell}"><div style="{h3}">Workstream Progress &amp; Budget</div>{w_tbl}</div>
  <div style="{cell}"><div style="{h3}">Synergy Capture vs Plan</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Day 1 / Day 100 / Year-End Milestone Tracking</div>{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Integration Risk Register</div>{rsk_tbl}</div>
  <div style="{cell}"><div style="{h3}">TMS — Cost Savings by Function</div>{t_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">PMI Thesis:</strong> Integration {r.overall_progress_pct * 100:.0f}% complete at day {r.days_since_close}.
    Synergy run-rate ${r.run_rate_synergies_mm:,.1f}M vs ${r.total_synergies_target_mm:,.1f}M target ({synergy_pct * 100:.0f}%). Back-office consolidation and supply-chain synergies ahead of plan;
    payer rate improvement and cross-sell revenue synergies behind — high-risk items requiring escalation.
    IT/EHR unification and data-warehouse consolidation are the critical-path blockers for Year-1 milestones.
    Integration spend tracking at {budget_util * 100:.0f}% of budget — on target.
    Historical PE-healthcare integrations capture 65-75% of targeted synergies by month 12; we're tracking toward top of range ex-payer-rate items.
  </div>
</div>"""

    return chartis_shell(body, "PMI Playbook", active_nav="/pmi-playbook")
