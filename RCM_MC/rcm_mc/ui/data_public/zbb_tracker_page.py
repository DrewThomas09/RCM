"""Zero-Based Budgeting Tracker — /zbb-tracker."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row


def _categories_chart(items) -> str:
    """Lead chart — cost categories ranked by remaining savings potential."""
    def _tone(c):
        cap = c.savings_captured_mm + c.savings_potential_mm
        rate = (c.savings_captured_mm / cap) if cap else 0.0
        if rate >= 0.75: return "positive"
        if rate >= 0.45: return "teal"
        return "warning"
    top = sorted(items, key=lambda c: c.savings_potential_mm, reverse=True)
    total = sum(c.savings_potential_mm for c in top) or 1.0
    rows = [ck_bar_row(c.category, f"${c.savings_potential_mm:,.2f}M",
            c.savings_potential_mm / total * 100.0, tone=_tone(c)) for c in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of remaining savings opportunity '
            '· value = potential ($M) · tone = capture progress</div></div>')


def _categories_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Category","left"),("Pre-ZBB ($M)","right"),("Current ($M)","right"),("Target ($M)","right"),
            ("Captured ($M)","right"),("Remaining ($M)","right"),("% of Rev","right"),("Benchmark","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        bench_c = pos if c.pct_of_revenue <= c.benchmark_pct else neg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.category)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${c.pre_zbb_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.current_run_rate_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${c.target_run_rate_mm:,.2f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${c.savings_captured_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${c.savings_potential_mm:,.2f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{c.pct_of_revenue * 100:.2f}%""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{bench_c};font-weight:600">{c.benchmark_pct * 100:.2f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _initiatives_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Initiative","left"),("Category","center"),("Target ($M)","right"),("Captured LTM ($M)","right"),
            ("Capture Rate","right"),("Owner","center"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    stat_c = {"completed": pos, "on track": acc, "lagging": warn, "blocked": neg}
    for i, it in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_c.get(it.status, text_dim)
        r_c = pos if it.capture_rate_pct >= 0.80 else (acc if it.capture_rate_pct >= 0.60 else warn)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(it.initiative)}""", mono=True, weight=600)}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(it.category)}</td>',
            f'{ck_data_cell(f"""${it.annualized_target_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${it.captured_ltm_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:700">{it.capture_rate_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""{_html.escape(it.owner)}""", align="center", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(it.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _waste_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Waste Type","left"),("Description","left"),("Identified ($M)","right"),
            ("Eliminated ($M)","right"),("Recurring","center"),("Owner","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, w in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        r_c = pos if w.recurring else text_dim
        e_c = pos if w.eliminated_mm >= w.identified_mm * 0.90 else acc
        cells = [
            f'{ck_data_cell(f"""{_html.escape(w.waste_type)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(w.description)}</td>',
            f'{ck_data_cell(f"""${w.identified_mm:,.2f}""", align="right", mono=True, tone="neg")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{e_c};font-weight:700">${w.eliminated_mm:,.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{r_c};font-weight:700">{"YES" if w.recurring else "ONE-TIME"}</td>',
            f'{ck_data_cell(f"""{_html.escape(w.remediation_owner)}""", align="center", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _policies_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Policy","left"),("Threshold","left"),("Approval Level","left"),("Enforcement","left"),
            ("Violations LTM","right"),("Savings ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        v_c = neg if p.violations_ltm >= 10 else (warn if p.violations_ltm >= 5 else pos)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.policy)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.threshold)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.approval_level)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.enforcement_status)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{v_c};font-weight:600">{p.violations_ltm}</td>',
            f'{ck_data_cell(f"""${p.savings_from_policy_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _vendors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Category","left"),("Vendors Pre","right"),("Vendors Post","right"),("Spend Pre ($M)","right"),
            ("Spend Post ($M)","right"),("Savings ($M)","right"),("Quality Impact","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, v in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        q_c = pos if "improved" in v.quality_impact else (acc if "same" in v.quality_impact or "maintained" in v.quality_impact else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(v.category)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{v.vendor_count_pre}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""{v.vendor_count_post}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""${v.spend_pre_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${v.spend_post_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${v.savings_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{q_c}">{_html.escape(v.quality_impact)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_zbb_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.zbb_tracker import compute_zbb_tracker
    r = compute_zbb_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    r_c = pos if r.capture_rate_pct >= 0.75 else (acc if r.capture_rate_pct >= 0.55 else P["warning"])

    kpi_strip = (
        ck_kpi_block("Pre-ZBB Baseline", f"${r.total_baseline_mm:,.1f}M", "", "") +
        ck_kpi_block("Current Run-Rate", f"${r.current_run_rate_mm:,.1f}M", "", "") +
        ck_kpi_block("Target Run-Rate", f"${r.target_run_rate_mm:,.1f}M", "", "") +
        ck_kpi_block("Savings Captured", f"${r.total_savings_captured_mm:,.1f}M", "", "") +
        ck_kpi_block("Savings Remaining", f"${r.total_savings_potential_mm:,.1f}M", "", "") +
        ck_kpi_block("Capture Rate", f"{r.capture_rate_pct * 100:.0f}%", "", "") +
        ck_kpi_block("Initiatives", str(len(r.initiatives)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    c_tbl = _categories_table(r.categories)
    c_chart = _categories_chart(r.categories)
    i_tbl = _initiatives_table(r.initiatives)
    w_tbl = _waste_table(r.waste)
    p_tbl = _policies_table(r.policies)
    v_tbl = _vendors_table(r.vendors)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Zero-Based Budgeting Tracker",
        eyebrow="ZBB TRACKER",
        meta=f"""Cost category rebuild · savings initiative portfolio · waste audit · spend policies · vendor rationalization — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {r_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">ZBB Transformation Progress</div>
    <div style="color:{r_c};font-weight:700;font-size:14px">${r.total_savings_captured_mm:,.1f}M captured / ${r.total_savings_captured_mm + r.total_savings_potential_mm:,.1f}M opportunity · {r.capture_rate_pct * 100:.0f}% capture rate</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Run-rate reduced from ${r.total_baseline_mm:,.1f}M → ${r.current_run_rate_mm:,.1f}M · ${r.current_run_rate_mm - r.target_run_rate_mm:,.1f}M remains to target</div>
  </div>
  <div style="{cell}"><div style="{h3}">Cost Category Rebuild — Baseline vs Current vs Target</div>{c_chart}{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Savings Initiative Portfolio</div>{i_tbl}</div>
  <div style="{cell}"><div style="{h3}">Waste Audit Findings</div>{w_tbl}</div>
  <div style="{cell}"><div style="{h3}">Spend Policy &amp; Control Framework</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Vendor Rationalization Results</div>{v_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">ZBB Thesis:</strong> Platform baseline ${r.total_baseline_mm:,.1f}M reduced to ${r.current_run_rate_mm:,.1f}M with ${r.total_savings_captured_mm:,.1f}M captured to date.
    Highest-impact captures: consulting freeze (96%), benefits renegotiation (88%), malpractice pool consolidation (88%).
    Clinical productivity initiative is the lagging workstream at 31% capture — execution challenge requires CMO-led intervention.
    ${r.total_savings_potential_mm:,.1f}M in remaining opportunity — concentrated in clinical labor and contract labor categories.
    Vendor rationalization eliminated 183 redundant vendors across 8 categories, generating ${sum(v.savings_mm for v in r.vendors):,.1f}M annualized savings.
    Waste audit surfaced ${sum(w.identified_mm for w in r.waste):,.2f}M of annual recurring waste; ${sum(w.eliminated_mm for w in r.waste):,.2f}M eliminated to date.
  </div>
</div>"""

    return chartis_shell(body, "ZBB Tracker", active_nav="/zbb-tracker",
        editorial_intro={
            "eyebrow": "ZBB TRACKER",
            "headline": "What the zbb tracker page reveals on this deal.",
            "italic_word": "reveals",
        })
