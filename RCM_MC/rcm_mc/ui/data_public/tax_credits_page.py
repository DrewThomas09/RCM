"""Tax Credits / Incentives Tracker — /tax-credits."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor

def _credits_chart(items) -> str:
    """Lead chart for the tax-credit table — credits ranked by amount
    remaining (unused) so the biggest untapped balances surface first.
    Bar = share of total remaining; value = remaining ($M); tone teal.
    Full credit grid stays directly below.
    """
    total = sum(c.remaining_m for c in items) or 1.0
    ranked = sorted(items, key=lambda c: c.remaining_m, reverse=True)
    rows = []
    for c in ranked:
        rows.append(ck_bar_row(c.credit_name, f"${c.remaining_m:,.1f}M",
                               c.remaining_m / total * 100.0, tone="teal"))
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of total credits '
            'remaining \u00b7 value = remaining ($M)</div></div>')



def _status_color(s: str) -> str:
    return {
        "active": P["positive"],
        "pending": P["accent"],
        "expired": P["text_dim"],
    }.get(s, P["text_dim"])


def _risk_color(r: str) -> str:
    return {"low": P["positive"], "medium": P["accent"], "high": P["warning"]}.get(r, P["text_dim"])


def _credits_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Type","left"),("Credit Name","left"),("Year","right"),
            ("Gross ($M)","right"),("Carryforward ($M)","right"),("Utilized ($M)","right"),
            ("Remaining ($M)","right"),("Expires","right"),("Counsel","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(c.credit_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(c.credit_name)}</td>',
            f'{ck_data_cell(f"""{c.tax_year}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.gross_credit_m:.2f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${c.carryforward_m:.2f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.utilized_m:.2f}M""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${c.remaining_m:.2f}M""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{c.expiration_year}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.counsel)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _state_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("State","center"),("Program","left"),("Type","left"),
            ("Award ($M)","right"),("Period (yrs)","right"),("Annual ($M)","right"),
            ("Obligations","left"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        st_c = _status_color(s.status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:700">{_html.escape(s.state)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:300px">{_html.escape(s.program)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(s.incentive_type)}</td>',
            f'{ck_data_cell(f"""${s.award_m:.2f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{s.period_years}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.annual_value_m:.2f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:300px">{_html.escape(s.obligations)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{st_c};border:1px solid {st_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _qoz_chart(items) -> str:
    """Summary chart — Opportunity Zone projects ranked by capital invested."""
    def _tone(z):
        mult = (z.projected_exit_value_m / z.invested_m) if z.invested_m else 0.0
        if mult >= 2.0: return "positive"
        if mult >= 1.4: return "teal"
        return "navy"
    top = sorted(items, key=lambda z: z.invested_m, reverse=True)
    total = sum(z.invested_m for z in top) or 1.0
    rows = [ck_bar_row(f"{z.project} · {z.deal}",
            f"${z.invested_m:,.1f}M → ${z.projected_exit_value_m:,.1f}M",
            z.invested_m / total * 100.0, tone=_tone(z)) for z in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of QOZ capital invested '
            '· value = invested → projected exit · tone = projected multiple</div></div>')


def _qoz_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Project","left"),("Deal","left"),("QOZ Tract","center"),("Invested ($M)","right"),
            ("Invested Date","right"),("Hold Remaining (yrs)","right"),("Deferred Gain ($M)","right"),
            ("Projected Exit ($M)","right"),("Step-Up Basis","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, z in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = pos if z.step_up_basis_pct >= 1.10 else acc
        cells = [
            f'{ck_data_cell(f"""{_html.escape(z.project)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(z.deal)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(z.qoz_tract)}</td>',
            f'{ck_data_cell(f"""${z.invested_m:.2f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(z.investment_date)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{z.hold_period_remaining_years:.1f}y""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${z.deferred_gain_m:.2f}M""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${z.projected_exit_value_m:.2f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{s_c};font-weight:700">+{(z.step_up_basis_pct - 1.0) * 100:.0f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _wotc_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Annual Hires","right"),("Eligible Hires","right"),("Eligible %","right"),
            ("Annual Credit ($M)","right"),("Credits Since Inception ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, w in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        e_c = pos if w.eligible_rate_pct >= 0.25 else (acc if w.eligible_rate_pct >= 0.18 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(w.deal)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{w.annual_headcount_hired:,}""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{w.eligible_hires}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">{w.eligible_rate_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${w.annual_credit_m:.2f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${w.credits_since_inception_m:.2f}M""", align="right", mono=True, weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tp_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Structure","left"),("Annual Benefit ($M)","right"),
            ("Risk Level","center"),("Documentation","left"),("Counsel","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = _risk_color(t.risk_level)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:340px">{_html.escape(t.structure)}</td>',
            f'{ck_data_cell(f"""${t.annual_tax_benefit_m:.2f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{r_c};border:1px solid {r_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.risk_level)}</span>""", align="center")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.documentation_status)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.counsel)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pipeline_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Opportunity","left"),("Deal","left"),("Credit Type","left"),
            ("Annual Benefit ($M)","right"),("Implementation Cost ($M)","right"),
            ("Probability","right"),("Timeline (mo)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pr_c = pos if p.probability_pct >= 85 else (acc if p.probability_pct >= 65 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.opportunity)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(p.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.credit_type)}</td>',
            f'{ck_data_cell(f"""${p.estimated_annual_benefit_m:.2f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${p.implementation_cost_m:.2f}M""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pr_c};font-weight:700">{p.probability_pct}%</td>',
            f'{ck_data_cell(f"""{p.timeline_months}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_tax_credits(params: dict = None) -> str:
    from rcm_mc.data_public.tax_credits import compute_tax_credits
    r = compute_tax_credits()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Gross Credits", f"${r.total_credits_gross_m:.1f}M", "", "") +
        ck_kpi_block("Utilized", f"${r.total_credits_utilized_m:.1f}M", "", "") +
        ck_kpi_block("Remaining", f"${r.total_credits_remaining_m:.1f}M", "", "") +
        ck_kpi_block("Annual State Incent", f"${r.total_state_incentives_annual_m:.1f}M", "", "") +
        ck_kpi_block("Annual Total Benefit", f"${r.total_annual_benefit_m:.1f}M", "", "") +
        ck_kpi_block("Deals Claiming", str(r.total_deals), "", "") +
        ck_kpi_block("QOZ Projects", str(len(r.opportunity_zones)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    c_chart = _credits_chart(r.credits)
    c_tbl = _credits_table(r.credits)
    value_anchor = ck_value_anchor(
        "Tax Credits",
        f"${r.total_annual_benefit_m:,.1f}M annual benefit",
        delta=f"${r.total_credits_gross_m:,.1f}M gross \u00b7 ${r.total_credits_utilized_m:,.1f}M utilized",
        opportunity=f"${r.total_credits_remaining_m:,.1f}M credits remaining (unused)",
        tone="positive",
    )
    s_tbl = _state_table(r.state_incentives)
    q_tbl = _qoz_table(r.opportunity_zones)
    q_chart = _qoz_chart(r.opportunity_zones)
    w_tbl = _wotc_table(r.wotc)
    tp_tbl = _tp_table(r.transfer_pricing)
    p_tbl = _pipeline_table(r.pipeline)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    pipeline_annual = sum(p.estimated_annual_benefit_m * (p.probability_pct / 100.0) for p in r.pipeline)
    qoz_deferred = sum(z.deferred_gain_m for z in r.opportunity_zones)
    page_title = ck_page_title(
        "Tax Credits / Incentives Tracker",
        eyebrow="TAX CREDITS",
        meta=f"""${r.total_credits_gross_m:.1f}M gross federal credits · ${r.total_state_incentives_annual_m:.1f}M annual state incentives · ${r.total_annual_benefit_m:.1f}M total annual benefit · {r.total_deals} deals claiming · ${pipeline_annual:.1f}M probability-weighted pipeline — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {ck_illustrative_note("figures")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Federal + State Tax Credits (Claimed)</div>{c_chart}{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">State-Level Incentive Programs</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Opportunity Zone Investments</div>{q_chart}{q_tbl}</div>
  <div style="{cell}"><div style="{h3}">WOTC / Workforce Credits</div>{w_tbl}</div>
  <div style="{cell}"><div style="{h3}">Transfer Pricing Structures</div>{tp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Credit Pipeline / Opportunities</div>{p_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Tax Credit Portfolio Summary:</strong> ${r.total_credits_gross_m:.1f}M in claimed federal + state credits across {r.total_deals} deals; ${r.total_credits_remaining_m:.1f}M in carryforward/remaining credits available for future use.
    Largest federal claimants: Project Oak RCM SaaS (R&D $8.5M + $9.8M across 2 years — 20-year carryforward), Project Thyme Specialty Pharm ($3.2M R&D), Project Fir Lab ($2.5M R&D).
    State incentive annual flow ${r.total_state_incentives_annual_m:.1f}M: MA Life Sciences ($0.70M/yr), GA Quality Jobs (Cypress $0.90M/yr), NJ Emerge (Thyme $0.64M/yr), NC JDIG (Laurel $0.50M/yr) — largest.
    QOZ investments ${sum(z.invested_m for z in r.opportunity_zones):.1f}M invested across 9 projects with ${qoz_deferred:.1f}M deferred gain; step-up basis to take effect 2027-2029 (10-year holding requirement).
    WOTC captures ${sum(w.annual_credit_m for w in r.wotc):.2f}M annual credits across 8 deals; Sage Home Health ($2.8M) and Basil Dental ($1.5M) are largest — driven by target-group new-hire profiles.
    Transfer pricing ${sum(t.annual_tax_benefit_m for t in r.transfer_pricing):.1f}M annual benefit — all structures in contemporaneous documentation status; Oak RCM IP licensing structure most actively discussed with IRS (APA pending).
    Pipeline: 10 opportunities with ${pipeline_annual:.1f}M probability-weighted annual benefit — R&D retroactive studies (Cedar + Magnolia, $5.3M combined) and ERC retroactive claims ($3.8M × 60%) top value.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Tax Credits", active_nav="/tax-credits",
        editorial_intro={
            "eyebrow": "TAX CREDITS",
            "headline": "What the tax credits page reveals on this deal.",
            "italic_word": "reveals",
        })
