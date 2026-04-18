"""Operating Partner / CEO Rolodex Tracker — /operating-partners."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _status_color(s: str) -> str:
    return {
        "performing": P["positive"],
        "exceeding": P["positive"],
        "early tenure": P["accent"],
        "new hire": P["accent"],
        "looking": P["accent"],
        "available immediately": P["positive"],
        "available": P["positive"],
        "advising": P["accent"],
        "in role": P["text_dim"],
    }.get(s, P["text_dim"])


def _stage_color(s: str) -> str:
    return {
        "offer stage": P["positive"],
        "finalist interviews": P["positive"],
        "final interviews": P["positive"],
        "candidate sourcing": P["accent"],
        "early sourcing": P["warning"],
    }.get(s, P["text_dim"])


def _partners_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Partner","left"),("Title","left"),("Sector Expertise","left"),("Prior CEO","left"),
            ("Deals","right"),("Boards","right"),("Hours LTM","right"),("Retainer ($M)","right"),
            ("Comp Structure","left"),("Tenure (yrs)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.title)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sector_expertise)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(p.prior_ceo_roles)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{p.active_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.board_seats}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{p.engagement_hours_ltm:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${p.retainer_annual_m:.2f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.compensation_structure)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.tenure_years}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _placements_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Executive","left"),("Deal","left"),("Role","left"),("Placement Date","right"),
            ("Source","left"),("Comp ($M)","right"),("Equity %","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(e.status)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(e.executive)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(e.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(e.role)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(e.placement_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.source)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${e.comp_package_m:.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{e.equity_pct * 100:.2f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _searches_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Role","left"),("Deal","left"),("Sector","left"),("Launched","right"),
            ("Stage","center"),("Candidates","right"),("Target Close","right"),("Search Firm","left"),("Comp Range","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        st_c = _stage_color(s.stage)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.role)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(s.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.launched)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{st_c};border:1px solid {st_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.stage)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{s.candidates}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.target_close)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.search_firm)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos}">{_html.escape(s.comp_range_m)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _bench_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Executive","left"),("Specialty","left"),("Status","center"),("Prior Roles","right"),
            ("Relationship (yrs)","right"),("Willingness","right"),("Last Interview","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(b.active_status)
        w_c = pos if b.willingness_score >= 9.0 else (acc if b.willingness_score >= 8.0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(b.executive)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(b.specialty)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.active_status)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{b.prior_roles}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.relationship_tenure_years}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{w_c};font-weight:700">{b.willingness_score:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(b.last_interview)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _engagement_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Operating Partner","left"),("Deal","left"),("Focus","left"),("Hours LTM","right"),
            ("Value Creation ($M)","right"),("Outcome Score","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        o_c = pos if e.outcome_score >= 8.7 else (acc if e.outcome_score >= 8.0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(e.operating_partner)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600">{_html.escape(e.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(e.focus_area)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{e.hours_ltm:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${e.value_creation_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{o_c};font-weight:700">{e.outcome_score:.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _comp_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Role","left"),("Sector/Segment","left"),("P25 Base ($K)","right"),("Median Base ($K)","right"),
            ("P75 Base ($K)","right"),("Bonus %","right"),("Equity %","right"),("Vest (yrs)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.role)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.p25_base_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${c.median_base_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${c.p75_base_k:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{c.median_bonus_pct:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{c.median_equity_pct:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.typical_vest_years}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_operating_partners(params: dict = None) -> str:
    from rcm_mc.data_public.operating_partners import compute_operating_partners_tracker
    r = compute_operating_partners_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Operating Partners", str(r.total_operating_partners), "", "") +
        ck_kpi_block("Exec Placements", str(r.total_exec_placements), "", "") +
        ck_kpi_block("Active Searches", str(r.active_searches), "", "") +
        ck_kpi_block("Bench Roster", str(r.total_bench_count), "", "") +
        ck_kpi_block("Engagement LTM", f"{r.total_engagement_hours_ltm:,}h", "", "") +
        ck_kpi_block("Value Creation", f"${r.total_value_creation_m:.1f}M", "", "") +
        ck_kpi_block("Comp Benchmarks", str(len(r.comp)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    p_tbl = _partners_table(r.partners)
    pl_tbl = _placements_table(r.placements)
    s_tbl = _searches_table(r.searches)
    b_tbl = _bench_table(r.bench)
    e_tbl = _engagement_table(r.engagement)
    c_tbl = _comp_table(r.comp)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    avg_outcome = sum(e.outcome_score for e in r.engagement) / len(r.engagement) if r.engagement else 0

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Operating Partner / CEO Rolodex Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_operating_partners} operating partners · {r.total_exec_placements} exec placements LTM · {r.active_searches} active searches · {r.total_bench_count} bench roster · {r.total_engagement_hours_ltm:,} engagement hours · ${r.total_value_creation_m:.1f}M value creation attributed — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Operating Partner Roster</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Recent Executive Placements (LTM)</div>{pl_tbl}</div>
  <div style="{cell}"><div style="{h3}">Active Executive Searches</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Bench Roster — Cultivated Executives</div>{b_tbl}</div>
  <div style="{cell}"><div style="{h3}">Operating Partner Engagement & Value Creation</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Executive Compensation Benchmarks</div>{c_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Operating Partner Program Summary:</strong> {r.total_operating_partners} dedicated operating partners deliver {r.total_engagement_hours_ltm:,} hours LTM across portfolio with ${r.total_value_creation_m:.1f}M value creation attributed — {r.total_value_creation_m / r.total_engagement_hours_ltm * 1000 if r.total_engagement_hours_ltm else 0:.1f}K value per hour.
    Average outcome score {avg_outcome:.2f}/10 across {len(r.engagement)} active engagements; top performers Sarah Chen (Oak/RCM SaaS, 9.2), Thomas Yang (Laurel/Derma bolt-on PMI, 9.1), Dr. Rebecca Liu (Cypress/GI ASC integration, 9.0).
    {r.total_exec_placements} executive placements in LTM across CEO, CFO, COO, CMO, CCO, CTO, CHRO roles; average CEO comp package $1.65M base + 3.5% equity tracks top-quartile Pearl Meyer PE healthcare benchmarks.
    {r.active_searches} searches currently in flight — 3 at finalist/offer stage (Project Azalea CEO, Project Terra CGO, Project Horizon CFO); 5 in candidate sourcing for Q2-Q3 2026 closes.
    Bench roster of {r.total_bench_count} cultivated executives with average 8.6/10 willingness score; 6 available immediately across MSK, oncology, derma, HCIT, urology — meaningful reach for urgent placements.
    Compensation benchmarks 14 role/sector combinations — CEO median $1.25M base / 4% equity for multi-specialty platforms; CFO $750K / 1.5% equity for $500M-$1B platforms; CTO $950K / 2.25% for HCIT/RCM.
  </div>
</div>"""

    return chartis_shell(body, "Operating Partners", active_nav="/operating-partners")
