"""Roll-Up / Platform Economics Analyzer — /rollup-economics."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row


def _synergy_chart(items) -> str:
    """Summary chart — synergy run-rate by category (tone by execution risk)."""
    def _tone(s):
        r = (s.execution_risk or "").lower()
        if r == "low": return "positive"
        if r == "medium": return "teal"
        return "warning"
    top = sorted(items, key=lambda s: s.annual_run_rate_mm, reverse=True)
    total = sum(s.annual_run_rate_mm for s in top) or 1.0
    rows = [ck_bar_row(f"{s.category}",
            f"${s.annual_run_rate_mm:,.1f}M/yr · {s.execution_risk} risk",
            s.annual_run_rate_mm / total * 100.0, tone=_tone(s)) for s in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of synergy run-rate '
            '· value = annual ($M) + execution risk · tone = risk</div></div>')


def _cohorts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Year","left"),("Targets Closed","right"),("Avg Entry Mult","right"),
            ("Avg EV ($M)","right"),("Total Deployed ($M)","right"),
            ("Synergy Capture","right"),("Integ Time (mo)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{c.cohort_year}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.targets_closed}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{c.avg_entry_multiple:.2f}x""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${c.avg_ev_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.total_deployed_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{c.synergy_capture_pct * 100:.1f}%""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""{c.time_to_full_integration_months}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _arb_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Stage","left"),("EBITDA ($M)","right"),("Implied Multiple","right"),
            ("Implied EV ($M)","right"),("Incremental Value ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        val_c = pos if s.incremental_value_mm > 0 else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.stage)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${s.ebitda_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{s.implied_multiple:.2f}x""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${s.implied_ev_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{val_c};font-weight:700">${s.incremental_value_mm:+,.2f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _synergy_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Category","left"),("Annual Run-Rate ($M)","right"),("Capture (mo)","right"),
            ("One-Time Cost ($M)","right"),("Exec Risk","center"),("Confidence","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    risk_c = {"low": text_dim, "medium": warn, "high": neg}
    conf_c = {"low": neg, "medium": warn, "high": pos}
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_c.get(s.execution_risk, text_dim)
        cc = conf_c.get(s.confidence, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.category)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${s.annual_run_rate_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{s.capture_timing_months}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">${s.one_time_cost_mm:,.2f}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.execution_risk)}</span>""", align="center")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.confidence)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _integration_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; warn = P["warning"]
    cols = [("Workstream","left"),("$/Add-On ($k)","right"),("Total Cost ($M)","right"),
            ("Duration (mo)","right"),("Peak FTE","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, ic in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(ic.workstream)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${ic.cost_per_addon_k:,.0f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn};font-weight:600">${ic.total_cost_mm:,.2f}</td>',
            f'{ck_data_cell(f"""{ic.duration_months}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{ic.peak_fte}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _debt_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Stage","left"),("EBITDA ($M)","right"),("Leverage","right"),
            ("Max Debt ($M)","right"),("Equity Check ($M)","right"),("Dry Powder ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        lev_c = neg if d.leverage_multiple >= 6.0 else (acc if d.leverage_multiple >= 5.5 else text_dim)
        dp_c = pos if d.dry_powder_mm > 0 else neg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.stage)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${d.ebitda_mm:,.2f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{lev_c};font-weight:600">{d.leverage_multiple:.2f}x</td>',
            f'{ck_data_cell(f"""${d.max_debt_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${d.equity_check_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dp_c};font-weight:600">${d.dry_powder_mm:+,.2f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _walk_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Period","left"),("Standalone ($M)","right"),("Acquired ($M)","right"),
            ("Synergies ($M)","right"),("Total EBITDA ($M)","right"),("Organic Growth","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, w in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        grow_c = pos if w.organic_growth_pct > 0.08 else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(w.period)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${w.standalone_ebitda_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${w.acquired_ebitda_mm:,.2f}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${w.synergies_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${w.total_ebitda_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{grow_c}">{w.organic_growth_pct * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exit_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; acc = P["accent"]
    cols = [("Scenario","left"),("Exit EBITDA ($M)","right"),("Multiple","right"),
            ("Exit EV ($M)","right"),("Less Debt ($M)","right"),("Equity Proceeds ($M)","right"),
            ("MOIC","right"),("IRR","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if s.moic >= 2.5 else (acc if s.moic >= 1.8 else (text_dim if s.moic >= 1.0 else neg))
        irr_c = pos if s.irr >= 0.20 else (acc if s.irr >= 0.12 else (text_dim if s.irr >= 0 else neg))
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.scenario)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${s.exit_ebitda_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{s.exit_multiple:.2f}x""", align="right", mono=True, tone="acc", weight=600)}',
            f'{ck_data_cell(f"""${s.exit_ev_mm:,.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${s.less_debt_mm:,.2f}""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""${s.equity_proceeds_mm:,.2f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{s.moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{irr_c};font-weight:700">{s.irr * 100:+.1f}%</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _ebitda_walk_svg(walk) -> str:
    if not walk: return ""
    w, h = 560, 240
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 50
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = max(p.total_ebitda_mm for p in walk) or 1
    bg = P["panel"]; pos = P["positive"]; acc = P["accent"]; text = P["text"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(walk)
    bar_w = (inner_w - (n - 1) * 8) / n
    bars = []
    for i, p in enumerate(walk):
        x = pad_l + i * (bar_w + 8)
        # Stacked: standalone (base), acquired (middle), synergies (top)
        total_h = p.total_ebitda_mm / max_v * inner_h
        sa_h = p.standalone_ebitda_mm / max_v * inner_h
        ac_h = p.acquired_ebitda_mm / max_v * inner_h
        sy_h = p.synergies_mm / max_v * inner_h

        base_y = h - pad_b
        bars.append(f'<rect x="{x:.1f}" y="{base_y - sa_h:.1f}" width="{bar_w:.1f}" height="{sa_h:.1f}" fill="{text_dim}" opacity="0.85"/>')
        bars.append(f'<rect x="{x:.1f}" y="{base_y - sa_h - ac_h:.1f}" width="{bar_w:.1f}" height="{ac_h:.1f}" fill="{acc}" opacity="0.85"/>')
        bars.append(f'<rect x="{x:.1f}" y="{base_y - sa_h - ac_h - sy_h:.1f}" width="{bar_w:.1f}" height="{sy_h:.1f}" fill="{pos}" opacity="0.85"/>')

        y_top = base_y - total_h
        bars.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{y_top - 4:.1f}" fill="{text}" font-size="10" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:700">${p.total_ebitda_mm:,.0f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(p.period[:10])}</text>'
        )
    legend = (
        f'<rect x="10" y="{h - 22}" width="10" height="10" fill="{text_dim}"/><text x="24" y="{h - 13}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">standalone</text>'
        f'<rect x="100" y="{h - 22}" width="10" height="10" fill="{acc}"/><text x="114" y="{h - 13}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">acquired</text>'
        f'<rect x="180" y="{h - 22}" width="10" height="10" fill="{pos}"/><text x="194" y="{h - 13}" fill="{text_dim}" font-size="9" font-family="JetBrains Mono,monospace">synergies</text>'
    )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}{legend}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Platform EBITDA Walk — Standalone vs Acquired vs Synergies</text></svg>')


def render_rollup_economics(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    entry_ebitda = _f("entry_ebitda", 12.0)
    exit_ebitda = _f("exit_ebitda", 48.0)
    entry_mult = _f("entry_mult", 9.5)
    exit_mult = _f("exit_mult", 13.5)
    hold = _i("hold", 5)
    addons = _i("addons_per_year", 6)

    from rcm_mc.data_public.rollup_economics import compute_rollup_economics
    r = compute_rollup_economics(
        platform_entry_ebitda_mm=entry_ebitda,
        platform_exit_ebitda_target_mm=exit_ebitda,
        entry_multiple=entry_mult,
        exit_multiple=exit_mult,
        hold_years=hold,
        target_addons_per_year=addons,
    )

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Entry EBITDA", f"${r.platform_entry_ebitda_mm:,.1f}M", "", "") +
        ck_kpi_block("Exit EBITDA", f"${r.platform_exit_ebitda_mm:,.1f}M", "", "") +
        ck_kpi_block("Add-Ons", str(r.total_addons_closed), "", "") +
        ck_kpi_block("Deployed", f"${r.total_deployed_mm:,.0f}M", "", "") +
        ck_kpi_block("Synergies (Run-Rate)", f"${r.total_synergies_mm:,.1f}M", "", "") +
        ck_kpi_block("Multiple Arb", f"${r.multiple_arbitrage_mm:,.0f}M", "", "") +
        ck_kpi_block("Base MOIC", f"{r.base_case_moic:.2f}x", "", "") +
        ck_kpi_block("Base IRR", f"{r.base_case_irr * 100:.1f}%", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _ebitda_walk_svg(r.ebitda_walk)
    cohorts_tbl = _cohorts_table(r.add_on_cohorts)
    arb_tbl = _arb_table(r.multiple_arb)
    syn_tbl = _synergy_table(r.synergies)
    syn_chart = _synergy_chart(r.synergies)
    int_tbl = _integration_table(r.integration_costs)
    debt_tbl = _debt_table(r.debt_capacity)
    walk_tbl = _walk_table(r.ebitda_walk)
    exit_tbl = _exit_table(r.exit_scenarios)

    form = f"""
<form method="GET" action="/rollup-economics" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Entry EBITDA ($M)<input name="entry_ebitda" value="{entry_ebitda}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">Exit Target ($M)<input name="exit_ebitda" value="{exit_ebitda}" type="number" step="2" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">Entry Mult<input name="entry_mult" value="{entry_mult}" type="number" step="0.25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">Exit Mult<input name="exit_mult" value="{exit_mult}" type="number" step="0.25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">Hold (yr)<input name="hold" value="{hold}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/></label>
  <label style="font-size:11px;color:{text_dim}">Add-Ons/yr<input name="addons_per_year" value="{addons}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    total_int_cost = sum(ic.total_cost_mm for ic in r.integration_costs)

    page_title = ck_page_title(
        "Roll-Up / Platform Economics",
        eyebrow="ROLLUP ECONOMICS",
        meta=f"""Multiple arb · add-on cadence · synergy capture · debt capacity · exit waterfall — {r.corpus_deal_count:,} corpus deals""",
    )
    
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Platform EBITDA Walk — Entry → Exit</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Multiple Arbitrage Waterfall</div>{arb_tbl}</div>
  <div style="{cell}"><div style="{h3}">Add-On Cohorts — Deployment Pacing</div>{cohorts_tbl}</div>
  <div style="{cell}"><div style="{h3}">Synergy Capture — Run-Rate &amp; Cost to Achieve</div>{syn_chart}{syn_tbl}</div>
  <div style="{cell}"><div style="{h3}">Integration Cost by Workstream</div>{int_tbl}</div>
  <div style="{cell}"><div style="{h3}">Debt Capacity Trajectory</div>{debt_tbl}</div>
  <div style="{cell}"><div style="{h3}">Year-by-Year EBITDA Walk Detail</div>{walk_tbl}</div>
  <div style="{cell}"><div style="{h3}">Exit Scenario Matrix — Downside, Base, Upside, IPO</div>{exit_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Roll-Up Thesis:</strong> 4x EBITDA growth from ${r.platform_entry_ebitda_mm:,.1f}M → ${r.platform_exit_ebitda_mm:,.1f}M via
    {r.total_addons_closed} add-ons deploying ${r.total_deployed_mm:,.0f}M in aggregate. Multiple arbitrage (${entry_mult:.1f}x → ${exit_mult:.1f}x) creates ${r.multiple_arbitrage_mm:,.0f}M of value;
    synergies add ${r.total_synergies_mm:,.1f}M run-rate. Base-case MOIC {r.base_case_moic:.2f}x / IRR {r.base_case_irr * 100:.1f}% —
    materially dependent on exit multiple. Integration cost ${total_int_cost:,.2f}M is ~{(total_int_cost / r.total_deployed_mm) * 100:.1f}% of deployed capital;
    risks concentrated in EHR unification and cross-sell revenue synergies (high execution risk). Downside exit of 7x produces material equity erosion.
  </div>
</div>"""

    return chartis_shell(body, "Roll-Up Economics", active_nav="/rollup-economics",
        editorial_intro={
            "eyebrow": "ROLLUP ECONOMICS",
            "headline": "What the rollup economics page reveals on this deal.",
            "italic_word": "reveals",
        })
