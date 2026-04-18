"""Risk Adjustment / HCC Tracker — /risk-adjustment."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _intensity_color(i: str) -> str:
    return {
        "disciplined": P["positive"],
        "standard": P["accent"],
        "high intensity": P["warning"],
        "aggressive": P["negative"],
    }.get(i, P["text_dim"])


def _priority_color(p: str) -> str:
    return {
        "high": P["negative"],
        "medium": P["warning"],
        "low": P["text_dim"],
    }.get(p, P["text_dim"])


def _portfolios_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("MA Lives (K)","right"),("Avg RAF","right"),
            ("Prior RAF","right"),("RAF Trend","right"),("MA Rev ($M)","right"),
            ("$ per RAF pt","right"),("Coding Intensity","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ci_c = _intensity_color(p.coding_intensity)
        t_c = pos if p.raf_trend >= 0.05 else (acc if p.raf_trend >= 0.03 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.ma_lives_k:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{p.avg_raf:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.prior_year_raf:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{t_c};font-weight:700">+{p.raf_trend * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.ma_revenue_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.revenue_per_raf_point_m:.2f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{ci_c};border:1px solid {ci_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.coding_intensity)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _hcc_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("HCC","left"),("Description","left"),("Members (K)","right"),("Open Suspects","right"),
            ("Closure Rate","right"),("Opportunity ($M)","right"),("Priority","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = _priority_color(h.clinical_priority)
        c_c = pos if h.gap_closure_rate_pct >= 0.80 else (acc if h.gap_closure_rate_pct >= 0.70 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(h.hcc)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(h.hcc_description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{h.portfolio_members_k}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn};font-weight:700">{h.open_suspects:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{h.gap_closure_rate_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${h.revenue_opportunity_m:.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{p_c};border:1px solid {p_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(h.clinical_priority)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _coding_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Documentation Score","right"),("MRA Quality","right"),
            ("Auto-Adjudicated %","right"),("Provider Training","right"),
            ("Chart Review Cov","right"),("Prospective Coding","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = pos if c.documentation_score >= 8.5 else (acc if c.documentation_score >= 8.0 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">{c.documentation_score:.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{c.mra_quality_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.auto_adjudicated_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.provider_coding_training_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.chart_review_coverage_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{c.prospective_coding_pct * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _radv_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Deal","left"),("Current RAF","right"),("Extrap Recovery ($M)","right"),
            ("Sample","right"),("Error %","right"),("Likely Payback ($M)","right"),("Max Exposure ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        e_c = P["warning"] if r.error_rate_pct >= 0.06 else (acc if r.error_rate_pct >= 0.04 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{r.current_raf:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${r.radv_extrapolation_recovery_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.audit_sample_size}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{r.error_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${r.likely_payback_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${r.max_exposure_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></name></table></div>').replace('</name>', '')


def _v28_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Category","left"),("Members (K)","right"),("V24 RAF","right"),("V28 RAF","right"),
            ("Delta","right"),("Revenue Impact ($M)","right"),("Mitigation","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(v.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{v.members_affected_k}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{v.v24_raf:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{v.v28_raf:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">{v.raf_delta:+.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${v.revenue_impact_m:+.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(v.mitigation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _programs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Program","left"),("Deals","right"),("Members Engaged (K)","right"),("Gaps Closed","right"),
            ("RAF Uplift","right"),("Revenue Captured ($M)","right"),("Cost per Gap ($K)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.program)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{p.portfolio_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{p.members_engaged_k}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.gaps_closed:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">+{p.raf_uplift:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.revenue_captured_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${p.cost_per_gap_closed:.2f}K</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_risk_adjustment(params: dict = None) -> str:
    from rcm_mc.data_public.risk_adjustment import compute_risk_adjustment
    r = compute_risk_adjustment()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("MA Lives (Total)", f"{r.total_ma_lives_k:,.1f}K", "", "") +
        ck_kpi_block("Weighted RAF", f"{r.weighted_avg_raf:.3f}", "", "") +
        ck_kpi_block("MA Revenue", f"${r.total_ma_revenue_m:,.1f}M", "", "") +
        ck_kpi_block("Gap Opportunity", f"${r.total_raf_gap_opportunity_m:.1f}M", "", "") +
        ck_kpi_block("RADV Max Exposure", f"${r.radv_total_exposure_m:.1f}M", "", "") +
        ck_kpi_block("Avg Coding Discipline", f"{r.avg_coding_intensity_score:.2f}", "/10", "") +
        ck_kpi_block("Deals Exposed", str(r.portfolio_deals_exposed), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    p_tbl = _portfolios_table(r.portfolios)
    h_tbl = _hcc_table(r.hcc_gaps)
    c_tbl = _coding_table(r.coding)
    rd_tbl = _radv_table(r.radv_sim)
    v_tbl = _v28_table(r.v28)
    pr_tbl = _programs_table(r.programs)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    v28_total_impact = sum(v.revenue_impact_m for v in r.v28)
    program_revenue = sum(p.revenue_captured_m for p in r.programs)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Risk Adjustment / HCC Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_ma_lives_k:,.1f}K MA lives · weighted RAF {r.weighted_avg_raf:.3f} · ${r.total_ma_revenue_m:,.1f}M MA revenue · ${r.total_raf_gap_opportunity_m:.1f}M gap opportunity · ${r.radv_total_exposure_m:.1f}M max RADV exposure — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Portfolio RAF Roll-up</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">HCC Gap Analysis — Top Opportunities</div>{h_tbl}</div>
  <div style="{cell}"><div style="{h3}">V28 Model Impact Analysis</div>{v_tbl}</div>
  <div style="{cell}"><div style="{h3}">Gap-Closure Program Performance</div>{pr_tbl}</div>
  <div style="{cell}"><div style="{h3}">Coding Quality & Infrastructure</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">RADV Audit Exposure Simulation</div>{rd_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Risk Adjustment Portfolio Summary:</strong> {r.total_ma_lives_k:,.1f}K MA lives generate ${r.total_ma_revenue_m:,.1f}M revenue at weighted RAF {r.weighted_avg_raf:.3f} — portfolio RAF elevated vs national MA average 1.02 driven by chronic-heavy portfolios (Sage 2.12, Ash 1.95).
    Gap analysis: ${r.total_raf_gap_opportunity_m:.1f}M in unclosed HCC opportunity across 15 top-priority categories; diabetes w/ complications ($18.5M), CHF ($15.8M), COPD ($14.5M) are top three.
    V28 phase-in impact: ${v28_total_impact:.1f}M portfolio headwind — diabetes, CHF, and SUD categories hit hardest; mitigation via specificity coding and documentation uplift.
    Gap-closure programs capture ${program_revenue:.1f}M annual revenue — prospective chart review ($65M) and retrospective chart review ($32M) are highest-ROI programs.
    RADV exposure ${r.radv_total_exposure_m:.1f}M max across {r.portfolio_deals_exposed} portcos — Sage ($22M), Redwood ($12.5M), Linden ($10.5M) concentrated in behavioral + home health.
    Coding intensity distribution: 4 disciplined, 4 standard, 2 high-intensity, 2 aggressive — "aggressive" profiles (Sage, Linden) raise RADV risk; coding discipline initiative scheduled Q2 2026.
  </div>
</div>"""

    return chartis_shell(body, "Risk Adj / HCC", active_nav="/risk-adjustment")
