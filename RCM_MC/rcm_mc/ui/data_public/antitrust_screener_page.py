"""Anti-Trust / FTC Review Screener — /antitrust-screener."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _hhi_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Market","left"),("MSA","left"),("Pre-Merger HHI","right"),("Post-Merger HHI","right"),
            ("Δ HHI","right"),("CR3 Share","right"),("Flag","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    flag_c = {"highly concentrated": neg, "moderately concentrated": warn, "unconcentrated": pos}
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        fc = flag_c.get(h.concentration_flag, text_dim)
        d_c = neg if h.delta_hhi >= 200 else (warn if h.delta_hhi >= 100 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(h.market)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(h.msa)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{h.pre_merger_hhi:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">{h.post_merger_hhi:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{d_c};font-weight:700">+{h.delta_hhi}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{h.cr3_share_pct * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{fc};border:1px solid {fc};border-radius:2px;letter-spacing:0.06em">{_html.escape(h.concentration_flag)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _hsr_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Threshold","left"),("Current Value ($M)","right"),("Threshold Value ($M)","right"),
            ("Filing Required","center"),("Waiting Period (days)","right"),("Filing Fee ($k)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        f_c = neg if t.filing_required else pos
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(t.threshold)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${t.current_value_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${t.threshold_value_mm:,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{f_c};font-weight:700">{"REQUIRED" if t.filing_required else "No"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{t.waiting_period_days}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${t.filing_fee_k:,.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _overlaps_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Geography","left"),("Platform Share","right"),("Target Share","right"),("Combined","right"),
            ("Next Competitor","right"),("Severity","center"),("Remediation","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    sev_c = {"severe — likely 2R": neg, "material — monitor": warn, "moderate": warn, "low": text_dim}
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_c.get(o.overlap_severity, text_dim)
        cb_c = neg if o.combined_share_pct >= 50 else (warn if o.combined_share_pct >= 35 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(o.geography)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{o.platform_share_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{o.target_share_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cb_c};font-weight:700">{o.combined_share_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{o.next_competitor_pct:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(o.overlap_severity)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(o.remediation_required)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _case_law_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Case","left"),("Year","right"),("Parties","left"),("Outcome","left"),("Precedent","left"),("Relevance","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = P["negative"] if c.relevance_score >= 85 else (P["warning"] if c.relevance_score >= 65 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.case)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.year}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.parties)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.outcome)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.precedent_for_platform)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{c.relevance_score}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _states_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("State","left"),("Trigger","left"),("Notice (days)","right"),("Fee ($k)","right"),
            ("AG Posture","center"),("Challenge Rate","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    post_c = {"active scrutiny": neg, "active review": warn, "standard review": text_dim, "minimal scrutiny": pos}
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = post_c.get(s.state_ag_posture, text_dim)
        cr_c = neg if s.historical_challenge_rate_pct >= 0.15 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.state)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.review_trigger)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{s.notice_days}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.notification_fee_k:,.1f}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.state_ag_posture)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cr_c};font-weight:600">{s.historical_challenge_rate_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _remediations_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Option","left"),("Description","left"),("Timeline (mo)","right"),
            ("Cost ($M)","right"),("Deal Value Impact","right"),("Probability of Approval","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        p_c = pos if r.probability_of_approval >= 0.80 else (acc if r.probability_of_approval >= 0.55 else neg)
        v_c = neg if r.deal_value_impact_pct >= 0.10 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.option)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.timeline_months}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">${r.financial_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{v_c};font-weight:700">{r.deal_value_impact_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{r.probability_of_approval * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_antitrust_screener(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    deal_size = _f("deal_size", 485.0)

    from rcm_mc.data_public.antitrust_screener import compute_antitrust_screener
    r = compute_antitrust_screener(deal_size_mm=deal_size)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    score_c = neg if r.overall_risk_score >= 65 else (warn if r.overall_risk_score >= 40 else pos)

    kpi_strip = (
        ck_kpi_block("Deal Size", f"${r.deal_size_mm:,.0f}M", "", "") +
        ck_kpi_block("HSR Required", "YES" if r.hsr_required else "NO", "", "") +
        ck_kpi_block("2R Probability", f"{r.second_request_probability * 100:.0f}%", "", "") +
        ck_kpi_block("Overall Risk", f"{r.overall_risk_score}/100", "", "") +
        ck_kpi_block("Timeline (mo)", str(r.recommended_timeline_months), "", "") +
        ck_kpi_block("Markets Screened", str(len(r.hhi_analysis)), "", "") +
        ck_kpi_block("State Reviews", str(len(r.state_reviews)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    form = f"""
<form method="GET" action="/antitrust-screener" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Deal Size ($M)<input name="deal_size" value="{deal_size}" type="number" step="25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:100px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Screen</button>
</form>"""

    h_tbl = _hhi_table(r.hhi_analysis)
    hsr_tbl = _hsr_table(r.hsr_thresholds)
    o_tbl = _overlaps_table(r.overlaps)
    c_tbl = _case_law_table(r.case_law)
    s_tbl = _states_table(r.state_reviews)
    rem_tbl = _remediations_table(r.remediations)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    best_remediation = min(r.remediations, key=lambda x: x.timeline_months + x.financial_cost_mm * 0.5 + x.deal_value_impact_pct * 100 - x.probability_of_approval * 50)
    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Anti-Trust / FTC Review Screener</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">HSR thresholds · HHI / CR3 concentration · market overlap · FTC case law · state-AG posture · remediation options — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {score_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">Screening Verdict</div>
    <div style="color:{score_c};font-weight:700;font-size:14px">Risk {r.overall_risk_score}/100 · Second Request probability {r.second_request_probability * 100:.0f}% · Recommended timeline {r.recommended_timeline_months} months</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Recommended remediation: <strong style="color:{text}">{_html.escape(best_remediation.option)}</strong></div>
  </div>
  <div style="{cell}"><div style="{h3}">HHI / Market Concentration Analysis (MSA-Level)</div>{h_tbl}</div>
  <div style="{cell}"><div style="{h3}">HSR Threshold Analysis</div>{hsr_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Overlap (Platform + Target)</div>{o_tbl}</div>
  <div style="{cell}"><div style="{h3}">FTC Case Law Precedents</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">State-Level Review Exposure</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Remediation Options Matrix</div>{rem_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Anti-Trust Thesis:</strong> ${r.deal_size_mm:,.0f}M deal triggers HSR filing; Second Request probability {r.second_request_probability * 100:.0f}% given {sum(1 for o in r.overlaps if 'severe' in o.overlap_severity)} severe market overlaps in Texas MSAs.
    Post-USAP / Welsh Carson (2023) enforcement era, FTC is scrutinizing serial-acquisition theories against PE platform sponsors — relevance score 95.
    Recommended path: "Restructure deal (exclude 2 overlap markets)" — 92% approval probability, 6-month timeline, 25.8% deal value reduction.
    Alternative divestiture path preserves more value but extends timeline to 12-18 months and introduces execution risk.
    California, New York, Oregon, and Massachusetts notifications required given deal size; Colorado SB 21-003 also applies.
  </div>
</div>"""

    return chartis_shell(body, "Anti-Trust Screener", active_nav="/antitrust-screener")
