"""R&W Insurance Tracker — /rw-insurance."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor

def _policies_chart(items) -> str:
    """Lead chart for the R&W policy table — policies ranked by total
    tower limit so the biggest coverage towers surface first. Bar =
    share of total tower limit; value = tower ($M); tone teal."""
    total = sum(p.total_tower_m for p in items) or 1.0
    rows = []
    for p in sorted(items, key=lambda p: p.total_tower_m, reverse=True):
        rows.append(ck_bar_row(p.deal, f"${p.total_tower_m:,.0f}M",
                               p.total_tower_m / total * 100.0, tone="teal"))
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of total tower limit '
            '\u00b7 value = tower ($M)</div></div>')



def _status_color(s: str) -> str:
    return {
        "resolved (paid)": P["positive"],
        "resolved (settled)": P["positive"],
        "settling": P["warning"],
        "ongoing": P["accent"],
        "active": P["accent"],
        "notified / investigating": P["warning"],
    }.get(s, P["text_dim"])


def _policies_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Policy Type","left"),("Deal Size ($M)","right"),("Primary Limit ($M)","right"),
            ("Total Tower ($M)","right"),("Retention ($M)","right"),("Retention %","right"),("Premium ($M)","right"),
            ("Rate %","right"),("Period (y)","right"),("Primary Carrier","left"),("Broker","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if p.rate_pct <= 0.028 else (acc if p.rate_pct <= 0.032 else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.policy_type)}</td>',
            f'{ck_data_cell(f"""${p.deal_size_m:,.1f}M""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${p.primary_limit_m:.1f}M""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${p.total_tower_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${p.retention_m:.2f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{p.retention_pct * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.premium_m:.2f}M""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{p.rate_pct * 100:.2f}%</td>',
            f'{ck_data_cell(f"""{p.policy_period_years}y""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.primary_carrier)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.broker)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _carriers_chart(items) -> str:
    """Summary chart — carrier limit deployed (concentration; tone by open claims)."""
    def _tone(c):
        if c.open_claims >= 2: return "warning"
        if c.open_claims == 1: return "teal"
        return "navy"
    top = sorted(items, key=lambda c: c.total_limit_deployed_m, reverse=True)
    total = sum(c.total_limit_deployed_m for c in top) or 1.0
    rows = [ck_bar_row(f"{c.carrier} ({c.rating})",
            f"${c.total_limit_deployed_m:,.0f}M · {c.open_claims} open",
            c.total_limit_deployed_m / total * 100.0, tone=_tone(c)) for c in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of limit deployed by carrier '
            '· value = limit ($M) + open claims · tone = claims activity</div></div>')


def _carriers_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Carrier","left"),("Primary","right"),("Excess Layers","right"),("Limit Deployed ($M)","right"),
            ("Avg Rate %","right"),("Open Claims","right"),("Strengths","left"),("Rating","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if c.rating.startswith(("A+","A++")) else (acc if c.rating.startswith("A ") or c.rating.startswith("A-") else text_dim)
        cl_c = P["negative"] if c.open_claims > 0 else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.carrier)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{c.primary_policies}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{c.excess_layers}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${c.total_limit_deployed_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{c.avg_rate_pct * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cl_c};font-weight:700">{c.open_claims}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(c.notable_strengths)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{r_c};font-weight:700">{_html.escape(c.rating)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exclusions_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Deal","left"),("Exclusion Type","left"),("Scope","left"),("Standalone Coverage","left"),
            ("Premium ($M)","right"),("Retention ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.deal)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{neg};font-weight:600">{_html.escape(e.exclusion_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(e.scope)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(e.standalone_coverage)}</td>',
            f'{ck_data_cell(f"""${e.annual_premium_m:.2f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${e.retention_m:.1f}M""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _claims_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Deal","left"),("Claim Date","right"),("Type","left"),("Claimed ($M)","right"),
            ("Paid ($M)","right"),("Carrier","left"),("Status","center"),("Root Cause","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(c.status)
        recovery = c.paid_amount_m / c.claimed_amount_m if c.claimed_amount_m > 0 else 0
        p_c = pos if recovery >= 0.80 else (acc if recovery >= 0.60 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.deal)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(c.claim_date)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.claim_type)}</td>',
            f'{ck_data_cell(f"""${c.claimed_amount_m:.2f}M""", align="right", mono=True, tone="neg", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">${c.paid_amount_m:.2f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.carrier)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status)}</span>""", align="center")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(c.root_cause)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _specialty_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Coverage Type","left"),("Deal","left"),("Limit ($M)","right"),("Retention ($M)","right"),
            ("Premium ($M)","right"),("Rate %","right"),("Period (y)","right"),("Trigger","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.coverage_type)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:600">{_html.escape(s.deal)}</td>',
            f'{ck_data_cell(f"""${s.limit_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${s.retention_m:.2f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.premium_m:.2f}M""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""{s.rate_pct * 100:.2f}%""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{s.period_years}y""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(s.trigger)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benchmarks_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal Size Band","left"),("Typical Primary %","right"),("Typical Retention %","right"),
            ("Median Rate %","right"),("Market Trend","center"),("Typical Tower Layers","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = pos if "softening" in b.market_trend else (acc if "stable" in b.market_trend else P["warning"])
        cells = [
            f'{ck_data_cell(f"""{_html.escape(b.deal_size_band)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{b.typical_primary_limit_pct * 100:.1f}%""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{b.typical_retention_pct * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{b.median_rate_pct * 100:.2f}%""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.market_trend)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{b.typical_tower_layers}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_rw_insurance(params: dict = None) -> str:
    from rcm_mc.data_public.rw_insurance import compute_rw_insurance
    r = compute_rw_insurance()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Policies", str(r.total_policies), "", "") +
        ck_kpi_block("Primary Limit", f"${r.total_primary_limit_m:.1f}M", "", "") +
        ck_kpi_block("Total Tower", f"${r.total_tower_limit_m:,.1f}M", "", "") +
        ck_kpi_block("Total Premium", f"${r.total_premium_m:.1f}M", "", "") +
        ck_kpi_block("Avg Rate", f"{r.weighted_avg_rate_pct * 100:.2f}%", "", "") +
        ck_kpi_block("Avg Retention", f"{r.weighted_avg_retention_pct * 100:.2f}%", "", "") +
        ck_kpi_block("Open Claims", str(r.open_claims), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    p_chart = _policies_chart(r.policies)
    p_tbl = _policies_table(r.policies)
    value_anchor = ck_value_anchor(
        "R&W Insurance Tower",
        f"${r.total_tower_limit_m:,.0f}M tower limit",
        delta=f"{r.total_policies} policies \u00b7 ${r.total_premium_m:,.1f}M premium \u00b7 {r.weighted_avg_rate_pct * 100:.2f}% rate \u00b7 {r.open_claims} open claims",
        tone="navy",
    )
    c_tbl = _carriers_table(r.carriers)
    c_chart = _carriers_chart(r.carriers)
    e_tbl = _exclusions_table(r.exclusions)
    cl_tbl = _claims_table(r.claims)
    s_tbl = _specialty_table(r.specialty)
    b_tbl = _benchmarks_table(r.benchmarks)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_paid = sum(c.paid_amount_m for c in r.claims)
    total_claimed = sum(c.claimed_amount_m for c in r.claims)
    spec_prem = sum(s.premium_m for s in r.specialty)
    page_title = ck_page_title(
        "R&W Insurance / M&A Insurance Tracker",
        eyebrow="RW INSURANCE",
        meta=f"""{r.total_policies} active policies · ${r.total_tower_limit_m:,.1f}M total tower · ${r.total_premium_m:.1f}M premium · {r.weighted_avg_rate_pct * 100:.2f}% weighted rate · {r.weighted_avg_retention_pct * 100:.2f}% avg retention · {r.open_claims} open claims — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Active R&W Policies</div>{p_chart}{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Carrier League Table & Concentration</div>{c_chart}{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Claim Activity</div>{cl_tbl}</div>
  <div style="{cell}"><div style="{h3}">Policy Exclusions & Standalone Coverage</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Specialty Coverages</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Market Benchmarks by Deal Size</div>{b_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">R&W Insurance Program Summary:</strong> {r.total_policies} active policies with ${r.total_tower_limit_m:,.1f}M in coverage tower at ${r.total_premium_m:.1f}M annual premium — weighted {r.weighted_avg_rate_pct * 100:.2f}% rate tracks market ±25bps.
    Carrier concentration: Beazley (6 primary, ${sum(c.total_limit_deployed_m for c in r.carriers if c.carrier == "Beazley"):.0f}M deployed) leads portfolio; AIG/Euclid + Euclid Transactional combined represent 50%+ of primary policies — continuing PE-healthcare market focus.
    Claim experience: ${total_claimed:.1f}M claimed / ${total_paid:.1f}M paid ({total_paid / total_claimed * 100 if total_claimed else 0:.0f}% recovery); {r.open_claims} claims open with ~$9.5M aggregate alleged exposure under active investigation.
    Specialty coverage ${spec_prem:.2f}M annual premium across 10 policies — tax indemnity, contingent liability (FCA/DOJ), and litigation buyouts wrap the 9 known R&W policy exclusions.
    Market benchmarks: $500M-1B+ deal band softening (3.0% → 2.75% median rate); retentions tightening (0.50%); tower layers thickening (7-8 layers standard) — buyers' market for insureds.
    Exclusion footprint concentrated in 9 deals with known regulatory / legal matters — all covered by standalone policies or contingent liability wraps totaling ${sum(e.annual_premium_m for e in r.exclusions):.2f}M annual premium.
  </div>
</div>"""

    return chartis_shell(body, "R&W Insurance", active_nav="/rw-insurance",
        editorial_intro={
            "eyebrow": "RW INSURANCE",
            "headline": "What the rw insurance page reveals on this deal.",
            "italic_word": "reveals",
        })
