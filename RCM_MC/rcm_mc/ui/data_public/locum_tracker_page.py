"""Locum & Contract Workforce Tracker — /locum-tracker."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_paired_block, ck_page_title


def _roles_paired_rows(roles) -> tuple:
    headers = [
        "Role", "FTE", "Hrs/mo", "Locum $/hr", "Perm $/hr",
        "Premium %", "Agency Fee", "Monthly ($k)",
        "Annual ($M)", "Convert",
    ]
    rows: list = []
    spends: list = []
    for r in roles:
        rows.append([
            r.role,
            f"{r.headcount_fte:.1f}",
            str(r.hours_per_month),
            f"${r.locum_rate_per_hour:,.2f}",
            f"${r.perm_equiv_rate:,.2f}",
            f"{r.rate_premium_pct * 100:.1f}%",
            f"{r.agency_fee_pct * 100:.1f}%",
            f"${r.monthly_spend_k:,.1f}",
            f"${r.annual_spend_mm:,.2f}",
            "YES" if r.conversion_viable else "—",
        ])
        spends.append(r.annual_spend_mm)
    hot = [spends.index(max(spends))] if spends else []
    return headers, rows, hot


def _gaps_table(gaps) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]; pos = P["positive"]
    cols = [("Department","left"),("Open Positions","right"),("Avg Gap (days)","right"),
            ("Locum Coverage","right"),("Uncovered","right"),("Revenue Risk ($M)","right"),("Priority","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    pri_colors = {"critical": neg, "high": warn, "standard": text_dim}
    for i, g in enumerate(gaps):
        rb = panel_alt if i % 2 == 0 else bg
        pc = pri_colors.get(g.priority, text_dim)
        gap_c = neg if g.avg_gap_days > 120 else (warn if g.avg_gap_days > 80 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(g.department)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{g.open_positions}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{gap_c};font-weight:600">{g.avg_gap_days}</td>',
            f'{ck_data_cell(f"""{g.locum_coverage_pct * 100:.1f}%""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{g.uncovered_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${g.revenue_at_risk_mm:,.2f}""", align="right", mono=True, tone="neg", weight=600)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(g.priority)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _convert_table(convs) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Role","left"),("In Pipeline","right"),("Offer Made","right"),("Accepted","right"),
            ("Monthly Savings ($k)","right"),("Annual Savings ($M)","right"),("Conversion Rate","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(convs):
        rb = panel_alt if i % 2 == 0 else bg
        cr_c = pos if c.conversion_rate_pct >= 0.40 else (P["warning"] if c.conversion_rate_pct >= 0.25 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.role)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.in_pipeline_fte}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.perm_offer_made}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{c.accepted_perm}""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${c.monthly_savings_k:,.1f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.annual_savings_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cr_c};font-weight:600">{c.conversion_rate_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _compliance_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Category","left"),("Finding","left"),("Exposure ($k)","right"),
            ("Remediation (days)","right"),("Severity","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    sev_colors = {"high": neg, "medium": warn, "low": text_dim}
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_colors.get(c.severity, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.category)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(c.finding)}""", tone="dim")}',
            f'{ck_data_cell(f"""${c.exposure_k:,.1f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""{c.remediation_days}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.severity)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _scenarios_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Scenario","left"),("Locum Spend ($M)","right"),("Permanent ($M)","right"),
            ("Total Labor ($M)","right"),("Labor/Rev %","right"),("Retention","center"),
            ("Impl (mo)","right"),("Y1 Savings ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    ret_colors = {"elevated": P["negative"], "improved": pos, "stable": acc, "neutral": text_dim}
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        rc = ret_colors.get(s.retention_risk, text_dim)
        sav_c = pos if s.year_one_savings_mm > 0 else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.scenario)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"]}">${s.locum_spend_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${s.permanent_cost_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.total_labor_mm:,.2f}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{s.labor_pct_of_revenue * 100:.1f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.retention_risk)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{s.implementation_months}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sav_c};font-weight:700">${s.year_one_savings_mm:,.2f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _role_spend_svg(roles) -> str:
    if not roles: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 70
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    # Sort by annual spend desc
    sorted_r = sorted(roles, key=lambda r: r.annual_spend_mm, reverse=True)
    max_v = max(r.annual_spend_mm for r in sorted_r) or 1
    bg = P["panel"]; acc = P["accent"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(sorted_r)
    bar_w = (inner_w - (n - 1) * 6) / n
    bars = []
    for i, r in enumerate(sorted_r):
        x = pad_l + i * (bar_w + 6)
        bh = r.annual_spend_mm / max_v * inner_h
        y = (h - pad_b) - bh
        color = neg if r.rate_premium_pct > 0.70 else acc
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{text_dim}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${r.annual_spend_mm:.1f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(r.role[:14])}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{r.headcount_fte:.1f} FTE</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 38}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">+{r.rate_premium_pct * 100:.0f}%</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Annual Locum Spend by Role (red = rate premium &gt;70%)</text></svg>')


def render_locum_tracker(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    sector = params.get("sector", "Hospital")
    revenue = _f("revenue", 250.0)
    labor_pct = _f("labor_pct", 0.44)

    from rcm_mc.data_public.locum_tracker import compute_locum_tracker
    r = compute_locum_tracker(sector=sector, revenue_mm=revenue, labor_pct_of_revenue=labor_pct)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    kpi_strip = (
        ck_kpi_block("Revenue", f"${r.total_revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("Total Labor", f"${r.total_labor_mm:,.1f}M", "", "") +
        ck_kpi_block("Locum Spend", f"${r.locum_spend_mm:,.2f}M", "", "") +
        ck_kpi_block("Locum / Labor", f"{r.locum_pct_of_labor * 100:.1f}%", "", "") +
        ck_kpi_block("Contract FTE", f"{r.total_contract_fte:,.1f}", "", "") +
        ck_kpi_block("Permanent FTE", f"{r.total_permanent_fte:,.0f}", "", "") +
        ck_kpi_block("Coverage Gaps", str(len(r.gaps)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _role_spend_svg(r.roles)
    role_headers, role_rows, role_hot = _roles_paired_rows(r.roles)
    roles_paired = ck_paired_block(
        svg,
        data_label="Locum Spend by Role · Rate, FTE, Spend, Agency Fee",
        headers=role_headers,
        rows=role_rows,
        data_source=f"{len(r.roles)} contract roles · highest-spend role marked",
        hot_rows=role_hot,
    )
    gaps_tbl = _gaps_table(r.gaps)
    conv_tbl = _convert_table(r.conversions)
    comp_tbl = _compliance_table(r.compliance)
    sc_tbl = _scenarios_table(r.scenarios)

    sectors = ["Hospital", "ASC", "Behavioral Health", "Physician Services", "Outpatient"]
    sector_opts = "".join(f'<option value="{_html.escape(s)}"{" selected" if s == sector else ""}>{_html.escape(s)}</option>' for s in sectors)

    form = f"""
<form method="GET" action="/locum-tracker" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector<select name="sector" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">{sector_opts}</select></label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)<input name="revenue" value="{revenue}" type="number" step="25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">Labor / Rev<input name="labor_pct" value="{labor_pct}" type="number" step="0.01" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_gap_risk = sum(g.revenue_at_risk_mm for g in r.gaps)
    total_conv_savings = sum(c.annual_savings_mm for c in r.conversions)

    page_title = ck_page_title(
        "Locum & Contract Workforce Tracker",
        eyebrow="LOCUM TRACKER",
        meta=f"{sector} sector · ${r.locum_spend_mm:,.2f}M locum spend = {r.locum_pct_of_labor * 100:.1f}% of ${r.total_labor_mm:,.1f}M labor · {r.total_contract_fte:.1f} contract FTE across {len(r.roles)} roles · {len(r.gaps)} coverage gaps at ${total_gap_risk:,.1f}M revenue at risk · ${total_conv_savings:,.2f}M annual savings from permanent conversion",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {roles_paired}
  <div style="{cell}"><div style="{h3}">Coverage Gap Inventory — Revenue At Risk</div>{gaps_tbl}</div>
  <div style="{cell}"><div style="{h3}">Permanent Conversion Pipeline</div>{conv_tbl}</div>
  <div style="{cell}"><div style="{h3}">Compliance Exposure — 1099 / Credentialing / Contract Drift</div>{comp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Workforce Scenario Plans</div>{sc_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Workforce Thesis:</strong> ${r.locum_spend_mm:,.2f}M locum spend = {r.locum_pct_of_labor * 100:.1f}% of ${r.total_labor_mm:,.1f}M labor budget.
    Rate premium averages {sum(rl.rate_premium_pct for rl in r.roles) / len(r.roles) * 100:.0f}% vs permanent; agency fees bleed additional 18-22%.
    Recommended: <strong style="color:{text}">{_html.escape(r.recommended_scenario)}</strong> —
    captures ~${max(s.year_one_savings_mm for s in r.scenarios):,.2f}M in year-1 savings. Coverage gaps carry ${total_gap_risk:,.2f}M revenue-at-risk;
    pipeline supports ${total_conv_savings:,.2f}M ongoing annual savings from permanent conversion.
  </div>
</div>"""

    return chartis_shell(body, "Locum Workforce", active_nav="/locum-tracker",
        editorial_intro={
            "eyebrow": "LOCUM TRACKER",
            "headline": "What the locum tracker page reveals on this deal.",
            "italic_word": "reveals",
        })
