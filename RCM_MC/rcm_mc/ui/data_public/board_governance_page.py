"""Board Governance — /board-governance."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row


def _holdcos_chart(items) -> str:
    """Lead chart — holdco boards ranked by governance score (tone by band)."""
    def _tone(h):
        if h.governance_score >= 85: return "positive"
        if h.governance_score >= 78: return "teal"
        return "warning"
    top = sorted(items, key=lambda h: h.governance_score, reverse=True)
    rows = [ck_bar_row(f"{h.holdco} · {h.sector}", f"{h.governance_score}",
            float(h.governance_score), tone=_tone(h)) for h in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = governance score (0-100 scale) '
            '· tone = score band</div></div>')


_EXPLAINER_CSS = """<style>
.ck-bg-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-bg-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


def _holdcos_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]; warn = P["warning"]
    cols = [("Holdco","left"),("Sector","left"),("Board Size","right"),("Independent","right"),
            ("Indep %","right"),("Diversity %","right"),("Avg Tenure","right"),("Meetings LTM","right"),("Gov Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, h in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        g_c = pos if h.governance_score >= 85 else (acc if h.governance_score >= 78 else warn)
        i_c = pos if h.independence_pct >= 0.45 else (acc if h.independence_pct >= 0.40 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(h.holdco)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(h.sector)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{h.board_size}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{h.independent_directors}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{i_c};font-weight:600">{h.independence_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{h.diversity_pct * 100:.1f}%""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{h.avg_tenure_years:.1f}y""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{h.meetings_ltm}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">{h.governance_score}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _directors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Director","left"),("Holdcos","right"),("Specialty","left"),("Tenure","right"),
            ("Independent","center"),("Diversity","center"),("Committees","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ind_c = pos if d.independent else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.director)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{d.holdcos_served}""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.specialty)}</td>',
            f'{ck_data_cell(f"""{d.tenure_years:.1f}y""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{ind_c};font-weight:700">{"YES" if d.independent else "NO"}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(d.diversity_category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(d.committees)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _committees_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Holdco","left"),("Audit","center"),("Comp","center"),("Nom/Gov","center"),
            ("Risk","center"),("Clinical Quality","center"),("ESG","center"),("Coverage","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        g_c = pos if c.gap_score >= 85 else (acc if c.gap_score >= 70 else P["warning"])
        def cell(has):
            color = pos if has else neg
            return f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{color};font-weight:700">{"✓" if has else "✗"}</td>'
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.holdco)}""", mono=True, weight=600)}',
            cell(c.audit_committee),
            cell(c.compensation_committee),
            cell(c.nominating_gov_committee),
            cell(c.risk_committee),
            cell(c.clinical_quality_committee),
            cell(c.esg_committee),
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{g_c};font-weight:700">{c.gap_score}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sponsors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Sponsor","left"),("Holdcos","right"),("Board Seats","right"),("Observers","right"),
            ("Affiliated Indep","right"),("Effective Voting %","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.sponsor_firm)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{s.holdcos}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{s.total_board_seats}""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{s.observer_seats}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.affiliated_independents}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.effective_voting_pct * 100:.1f}%""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _gaps_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Practice","left"),("Implemented","right"),("Total","right"),("Coverage","right"),
            ("Owner","center"),("Priority","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    p_c = {"complete": pos, "low": text_dim, "medium": warn, "high": neg, "critical": neg}
    for i, g in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = p_c.get(g.priority, text_dim)
        c_c = pos if g.coverage_pct >= 0.90 else (acc if g.coverage_pct >= 0.70 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(g.practice)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{g.holdcos_implemented}""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""{g.holdcos_total}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{g.coverage_pct * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(g.remediation_owner)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(g.priority)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></name></table></div>').replace('</name>', '')


def _comp_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Role","left"),("Median ($k)","right"),("Top Quartile ($k)","right"),
            ("Bottom Quartile ($k)","right"),("Equity %","right"),("Typical Vesting","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.role)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${c.median_comp_k:,.1f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${c.quartile_top_k:,.1f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${c.quartile_bottom_k:,.1f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.equity_pct * 100:.2f}%""", align="right", mono=True, tone="acc", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.typical_vesting)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_board_governance(params: dict = None) -> str:
    from rcm_mc.data_public.board_governance import compute_board_governance
    r = compute_board_governance()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Holdcos", str(r.total_holdcos), "", "") +
        ck_kpi_block("Total Directors", str(r.total_directors), "", "") +
        ck_kpi_block("Avg Board Size", f"{r.avg_board_size:.1f}", "", "") +
        ck_kpi_block("Avg Independence", f"{r.avg_independence_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg Diversity", f"{r.avg_diversity_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg Gov Score", f"{r.avg_governance_score:.1f}", "", "") +
        ck_kpi_block("Committee Types", "6", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    h_tbl = _holdcos_table(r.holdcos)
    h_chart = _holdcos_chart(r.holdcos)
    d_tbl = _directors_table(r.directors)
    c_tbl = _committees_table(r.committees)
    s_tbl = _sponsors_table(r.sponsors)
    g_tbl = _gaps_table(r.gaps)
    comp_tbl = _comp_table(r.compensation)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    critical_gaps = sum(1 for g in r.gaps if g.priority == "high")
    page_title = ck_page_title(
        "Board of Directors / Governance",
        eyebrow="BOARD GOVERNANCE",
        meta=(
            f"{r.total_holdcos} holdco boards · {r.total_directors} director seats · "
            f"independence {r.avg_independence_pct * 100:.1f}% · "
            f"{r.corpus_deal_count:,} corpus deals"
        ),
    )
    bg_explainer = (
        '<p class="ck-bg-explainer">'
        "<em>What the board governance analysis reveals on this deal.</em> "
        "Holdco board composition, director bench, committee coverage, sponsor representation, "
        "governance gaps, and executive compensation benchmarks across the portfolio."
        "</p>"
    )
    body = page_title + bg_explainer + f"""
<div class="ck-page-wrap">
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Holdco Board Composition</div>{h_chart}{h_tbl}</div>
  <div style="{cell}"><div style="{h3}">Bench of Independent Directors</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">Committee Coverage by Holdco</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sponsor Board Representation</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Governance Best-Practice Gaps</div>{g_tbl}</div>
  <div style="{cell}"><div style="{h3}">Executive Compensation Benchmarks</div>{comp_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Governance Thesis:</strong> {r.total_holdcos} holdco boards average {r.avg_board_size:.1f} directors with {r.avg_independence_pct * 100:.1f}% independence (below NYSE majority-independent standard but sufficient for PE-owned).
    Diversity at {r.avg_diversity_pct * 100:.1f}% tracks below public-company benchmarks; remediation required for next-round diligence.
    Committee coverage gaps: ESG committee (16.7% coverage) and Cybersecurity oversight (33.3% coverage) are {critical_gaps} high-priority gaps.
    Bench of 12 recurring independent directors provides cross-pollination and governance institutional memory.
    Sponsor + Management voting share 60% across portfolio; Independent Directors hold 28% — alignment with Delaware Chancery standards.
    Executive compensation median CEO at $485k with 3.5% equity stake (4-year vest) aligns with MGMA / Pearl Meyer PE benchmarks.
  </div>
</div>"""

    return chartis_shell(body, "Board Governance", active_nav="/board-governance",
        extra_css=_EXPLAINER_CSS)
