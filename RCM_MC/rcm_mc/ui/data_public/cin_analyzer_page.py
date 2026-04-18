"""CIN Analyzer — /cin-analyzer."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _providers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Provider Group","left"),("Category","center"),("Providers","right"),("Lives","right"),
            ("Contrib ($M)","right"),("Quality","right"),("Engagement","right"),("Tenure (yr)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        q_c = pos if p.quality_score >= 0.82 else (acc if p.quality_score >= 0.75 else warn)
        e_c = pos if p.engagement_score >= 80 else (acc if p.engagement_score >= 70 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.provider_group)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.specialty_category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.provider_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.attributed_lives:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">${p.annual_contribution_mm:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{q_c};font-weight:700">{p.quality_score:.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c}">{p.engagement_score}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.tenure_years:.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _contracts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Payer","left"),("Type","left"),("Lives","right"),("Premium PPMY","right"),
            ("Shared Savings %","right"),("Quality Weight","right"),("Expected Savings ($M)","right"),("Distribution ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.payer_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.contract_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.attributed_lives:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.annual_premium_pmpy:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.shared_savings_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.quality_weight * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.expected_savings_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.expected_distribution_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _quality_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Measure","left"),("Domain","center"),("Current","right"),("Benchmark","right"),
            ("Gap","right"),("Weight","right"),("Financial Impact ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, q in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        # Check if metric is rate-based (smaller is better for readmission/ED)
        inverse = q.measure in ("Readmission Rate 30-Day", "ED Utilization / 1000")
        if inverse:
            gap = q.benchmark - q.current_performance
        else:
            gap = q.current_performance - q.benchmark
        gap_c = pos if gap > 0 else (warn if gap > -0.05 else neg)
        is_pct = q.current_performance < 1.5
        curr_disp = f"{q.current_performance * 100:.1f}%" if is_pct else f"{q.current_performance:.1f}"
        bench_disp = f"{q.benchmark * 100:.1f}%" if is_pct else f"{q.benchmark:.1f}"
        gap_disp = f"{gap * 100:+.1f}pp" if is_pct else f"{gap:+.1f}"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(q.measure)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(q.domain)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{curr_disp}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{bench_disp}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gap_c};font-weight:600">{gap_disp}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{q.weight * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${q.financial_impact_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _geo_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Market","left"),("Attributed Lives","right"),("PCPs","right"),("Specialists","right"),
            ("Adequacy","center"),("Growth","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    adeq_c = {"strong": pos, "adequate": P["accent"], "gap": warn}
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ac = adeq_c.get(g.adequacy_score, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(g.market)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{g.attributed_lives:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{g.pcp_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{g.specialist_count}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{ac};border:1px solid {ac};border-radius:2px;letter-spacing:0.06em">{_html.escape(g.adequacy_score)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(g.growth_opportunity)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _dist_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Cohort","left"),("Provider Count","right"),("Avg Dist/Provider ($k)","right"),
            ("Quality Bonus ($k)","right"),("Productivity Bonus ($k)","right"),("Total Distribution ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.cohort)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{d.provider_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${d.avg_distribution_per_provider_k:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${d.quality_bonus_k:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${d.productivity_bonus_k:,.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${d.total_distribution_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _compliance_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Regulation","left"),("Status","center"),("Last Review","left"),
            ("Remediation","left"),("Exposure ($k)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    sc = {"compliant": pos, "monitoring": warn, "minor gap": warn, "severe": neg}
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cc = sc.get(c.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.regulation)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.last_review)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.remediation_needed)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if c.exposure_mm > 0 else text_dim}">${c.exposure_mm:,.0f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_cin_analyzer(params: dict = None) -> str:
    params = params or {}

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    providers = _i("providers", 600)
    lives = _i("lives", 250000)

    from rcm_mc.data_public.cin_analyzer import compute_cin_analyzer
    r = compute_cin_analyzer(network_provider_count=providers, total_attributed_lives=lives)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    rating_c = pos if r.cin_value_rating == "trust-grade" else (acc if r.cin_value_rating == "solid" else P["warning"])

    kpi_strip = (
        ck_kpi_block("Network Providers", f"{r.total_providers:,}", "", "") +
        ck_kpi_block("Attributed Lives", f"{r.total_attributed_lives:,}", "", "") +
        ck_kpi_block("Annual Contribution", f"${r.total_annual_contribution_mm:,.2f}M", "", "") +
        ck_kpi_block("Expected Distribution", f"${r.total_expected_distribution_mm:,.2f}M", "", "") +
        ck_kpi_block("Quality Score", f"{r.weighted_quality_score:.3f}", "", "") +
        ck_kpi_block("Network Adequacy", f"{r.network_adequacy_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Rating", r.cin_value_rating.upper(), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    pv_tbl = _providers_table(r.providers)
    ct_tbl = _contracts_table(r.contracts)
    qm_tbl = _quality_table(r.quality_measures)
    gt_tbl = _geo_table(r.geography)
    dst_tbl = _dist_table(r.distributions)
    cm_tbl = _compliance_table(r.compliance)

    form = f"""
<form method="GET" action="/cin-analyzer" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Network Providers<input name="providers" value="{providers}" type="number" step="25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:90px"/></label>
  <label style="font-size:11px;color:{text_dim}">Attributed Lives<input name="lives" value="{lives}" type="number" step="10000" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:100px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_comp_exp = sum(c.exposure_mm for c in r.compliance)
    total_q_upside = sum(q.financial_impact_mm for q in r.quality_measures)

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Clinical Integration Network Analyzer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Provider roster · payer contracts · quality measures · network adequacy · compliance — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Provider Member Roster — Specialty, Lives, Quality, Engagement</div>{pv_tbl}</div>
  <div style="{cell}"><div style="{h3}">Payer Contract Portfolio — Shared Savings &amp; Risk</div>{ct_tbl}</div>
  <div style="{cell}"><div style="{h3}">Quality Measure Performance vs HEDIS/STARS Benchmark</div>{qm_tbl}</div>
  <div style="{cell}"><div style="{h3}">Geographic Coverage &amp; Network Adequacy</div>{gt_tbl}</div>
  <div style="{cell}"><div style="{h3}">Distribution Cohorts — Quality-Weighted Payment</div>{dst_tbl}</div>
  <div style="{cell}"><div style="{h3}">Regulatory Compliance — FTC / Stark / Anti-Kickback / State Insurance</div>{cm_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {rating_c};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">CIN Value Rating: <span style="color:{rating_c}">{_html.escape(r.cin_value_rating.upper())}</span>.</strong>
    {r.total_providers:,} providers across {len(r.geography)} markets support {r.total_attributed_lives:,} attributed lives.
    Quality score {r.weighted_quality_score:.3f} (weight-avg); adequacy {r.network_adequacy_pct * 100:.1f}% of markets.
    Expected ${r.total_expected_distribution_mm:,.2f}M distribution across {len(r.contracts)} payer contracts.
    Quality gap closure represents ${total_q_upside:,.2f}M additional annual shared savings.
    Compliance exposure ${total_comp_exp:,.0f}K on monitoring items — manageable but requires Q1 remediation.
    CINs with strong quality + full risk contracts are fundamentally different from traditional PPO networks — they capture value rather than rent-seek it.
  </div>
</div>"""

    return chartis_shell(body, "CIN Analyzer", active_nav="/cin-analyzer")
