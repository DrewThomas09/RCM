"""Tax Structure Analyzer page — /tax-structure.

Structure comparison (Stock vs 338 vs F-Reorg), rollover tax, PTE / SALT,
and multi-year after-tax cash flow.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor


def _structure_comparison_svg(structures) -> str:
    if not structures:
        return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 60, 30, 25, 60
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_v = max((abs(s.net_benefit_mm) for s in structures), default=1)
    max_v = max(max_v, 1) * 1.2
    min_v = -max_v

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    neg = P["negative"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    zero_y = (h - pad_b) - (0 - min_v) / (max_v - min_v) * inner_h
    n = len(structures)
    bar_w = (inner_w - (n - 1) * 12) / n

    bars = []
    for i, s in enumerate(structures):
        x = pad_l + i * (bar_w + 12)
        height = abs(s.net_benefit_mm) / (max_v - min_v) * inner_h
        y = zero_y - height if s.net_benefit_mm >= 0 else zero_y
        color = pos if s.net_benefit_mm > 0 else (neg if s.net_benefit_mm < 0 else text_faint)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{height:.1f}" fill="{color}" opacity="0.88"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{P["text_dim"]}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${s.net_benefit_mm:+,.1f}M</text>'
        )
        # Two-line label
        short = s.structure[:16]
        bars.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(short)}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{text_faint}" font-size="8" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">Complexity {s.complexity_score}/10</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{w - pad_r}" y2="{zero_y:.1f}" stroke="{border}" stroke-width="1"/>'
        + "".join(bars)
        + f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Net Benefit ($M) by Structure</text>'
        f'</svg>'
    )


def _allocation_donut_svg(alloc: dict, ev_mm: float) -> str:
    import math
    w, h = 260, 200
    cx, cy = w / 2, h / 2 + 5
    r_outer, r_inner = 80, 55

    bg = P["panel"]; text_dim = P["text_dim"]
    colors = [P["accent"], "#1F7A75", "#a78bfa", P["warning"], P["positive"], P["negative"]]

    total = sum(alloc.values()) or 1
    segs = []
    start = -90
    labels = []
    for i, (key, val) in enumerate(alloc.items()):
        if val <= 0:
            continue
        frac = val / total
        end = start + frac * 360
        sr = math.radians(start)
        er = math.radians(end)
        x1o = cx + r_outer * math.cos(sr)
        y1o = cy + r_outer * math.sin(sr)
        x2o = cx + r_outer * math.cos(er)
        y2o = cy + r_outer * math.sin(er)
        x1i = cx + r_inner * math.cos(er)
        y1i = cy + r_inner * math.sin(er)
        x2i = cx + r_inner * math.cos(sr)
        y2i = cy + r_inner * math.sin(sr)
        large = 1 if (end - start) > 180 else 0
        color = colors[i % len(colors)]
        path = (f'M {x1o:.1f} {y1o:.1f} A {r_outer} {r_outer} 0 {large} 1 {x2o:.1f} {y2o:.1f} '
                f'L {x1i:.1f} {y1i:.1f} A {r_inner} {r_inner} 0 {large} 0 {x2i:.1f} {y2i:.1f} Z')
        segs.append(f'<path d="{path}" fill="{color}" opacity="0.88"/>')
        labels.append((key, val, color, frac))
        start = end

    # Legend below
    legend_svg = ""
    for i, (key, val, color, frac) in enumerate(labels):
        y_leg = 15 + i * 0
    # Just put center label
    total_lbl = (
        f'<text x="{cx}" y="{cy}" text-anchor="middle" fill="{P["text"]}" '
        f'font-size="12" font-weight="600" font-family="JetBrains Mono,monospace">${ev_mm:,.0f}M</text>'
        f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" fill="{text_dim}" '
        f'font-size="9" letter-spacing="0.08em" font-family="Inter,sans-serif">PURCHASE PRICE</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(segs) + total_lbl +
        f'</svg>'
    )


def _alloc_table(alloc: dict, ev_mm: float) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    cols = [("Allocation Bucket","left"),("Amount ($M)","right"),("% of PP","right"),("Tax Treatment","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    treatments = {
        "tangible_assets": "MACRS depreciation (5-39 yr)",
        "workforce_intangible": "15-yr amortization (Sec. 197)",
        "customer_relationships": "15-yr amortization",
        "trade_name": "15-yr amortization",
        "non_compete": "15-yr amortization",
        "goodwill": "15-yr amortization (buyer step-up)",
    }
    trs = []
    for i, (k, v) in enumerate(alloc.items()):
        rb = panel_alt if i % 2 == 0 else bg
        pct = v / ev_mm * 100 if ev_mm else 0
        cells = [
            f'{ck_data_cell(f"""{k.replace("_", " ").title()}""", mono=True)}',
            f'{ck_data_cell(f"""${v:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{pct:.1f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(treatments.get(k, "—"))}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _structure_table(structures, recommended: str) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Structure","left"),("Buyer OK","left"),("Seller OK","left"),("Step-up ($M)","right"),
            ("Annual Shield","right"),("PV Shield","right"),("Seller Tax ($M)","right"),
            ("Net Benefit ($M)","right"),("Complexity","right"),("Notes","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(structures):
        rb = panel_alt if i % 2 == 0 else bg
        is_rec = s.structure == recommended
        row_style = f"background:{rb};outline:{'2px solid ' + pos + ';outline-offset:-2px' if is_rec else 'none'}"
        nb_color = pos if s.net_benefit_mm > 0 else (neg if s.net_benefit_mm < 0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"600" if is_rec else "400"}">{_html.escape(s.structure)}{" ★" if is_rec else ""}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.buyer_preferred)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(s.seller_preferred)}</td>',
            f'{ck_data_cell(f"""${s.goodwill_stepup_mm:,.1f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${s.annual_tax_shield_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.pv_tax_shield_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${s.seller_tax_cost_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{nb_color};font-weight:600">${s.net_benefit_mm:+,.2f}</td>',
            f'{ck_data_cell(f"""{s.complexity_score}/10""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(s.notes)}</td>',
        ]
        trs.append(f'<tr style="{row_style}">{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _pte_table(pte) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("State","left"),("PTE Active","left"),("State Rate","right"),
            ("Entity Ded.","right"),("Fed Savings","right"),("Net Benefit","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, p in enumerate(pte):
        rb = panel_alt if i % 2 == 0 else bg
        ac = pos if p.pte_active else P["text_faint"]
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.state)}""", mono=True)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{ac};border:1px solid {ac};border-radius:2px;letter-spacing:0.06em">{"yes" if p.pte_active else "no"}</span>""")}',
            f'{ck_data_cell(f"""{p.state_rate * 100:.2f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.entity_deduction_mm:,.3f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.federal_savings_mm:,.3f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos if p.net_benefit_mm else text_dim};font-weight:{"600" if p.net_benefit_mm else "400"}">${p.net_benefit_mm:,.3f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _flow_table(flow) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Year","left"),("EBITDA","right"),("Step-up Shield","right"),("Taxable Income","right"),
            ("Fed Tax","right"),("State Tax","right"),("After-Tax Cash","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, f in enumerate(flow):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""Year {f.year}""", mono=True)}',
            f'{ck_data_cell(f"""${f.ebitda_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${f.tax_shield_from_stepup_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${f.taxable_income_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.federal_tax_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${f.state_tax_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${f.after_tax_cash_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_tax_structure(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    ev = _f("ev", 300.0)
    ebitda = _f("ebitda", 25.0)
    hold = _i("hold_years", 5)
    growth = _f("growth", 0.05)
    rollover = _f("rollover_pct", 0.10)
    state = params.get("state", "New York")

    from rcm_mc.data_public.tax_structure import compute_tax_structure
    r = compute_tax_structure(
        ev_mm=ev, ebitda_mm=ebitda, hold_years=hold,
        revenue_growth_pct=growth, rollover_pct=rollover, state=state,
    )

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("EV", f"${r.ev_mm:,.0f}M", "", "") +
        ck_kpi_block("EBITDA", f"${r.ebitda_mm:,.2f}M", "", "") +
        ck_kpi_block("Recommended", r.recommended_structure[:16], "", "") +
        ck_kpi_block("Tax Optimization", f"${r.total_tax_optimization_mm:,.1f}M", "", "") +
        ck_kpi_block("Seller Net", f"${r.seller_net_proceeds_mm:,.1f}M", "", "") +
        ck_kpi_block("Eff. Tax Rate", f"{r.effective_tax_rate * 100:.1f}%", "", "") +
        ck_kpi_block("Rollover Deferred", f"${r.rollover_tax.deferred_gain_mm:,.1f}M", "", "") +
        ck_kpi_block("Imm. Rollover Tax", f"${r.rollover_tax.immediate_tax_mm:,.1f}M", "", "")
    )

    comp_svg = _structure_comparison_svg(r.structure_options)
    donut_svg = _allocation_donut_svg(r.purchase_allocation, r.ev_mm)
    alloc_tbl = _alloc_table(r.purchase_allocation, r.ev_mm)
    struct_tbl = _structure_table(r.structure_options, r.recommended_structure)
    pte_tbl = _pte_table(r.pte_benefits)
    flow_tbl = _flow_table(r.tax_flow)

    form = f"""
<form method="GET" action="/tax-structure" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">EV ($M)
    <input name="ev" value="{ev}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA ($M)
    <input name="ebitda" value="{ebitda}" type="number" step="1"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Hold Years
    <input name="hold_years" value="{hold}" type="number" min="2" max="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:50px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Growth
    <input name="growth" value="{growth}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Rollover %
    <input name="rollover_pct" value="{rollover}" type="number" step="0.05"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">State
    <input name="state" value="{_html.escape(state)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:120px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "Tax Structure Analyzer",
        eyebrow="TAX STRUCTURE",
        meta=f"""Stock vs. 338(h)(10) vs. F-reorg, PTE/SALT, rollover taxation, after-tax cash — {r.corpus_deal_count:,} corpus deals""",
    )
    
    # Lead takeaway — surface the computed tax optimization (savings +
    # the recommended structure), otherwise buried as KPIs #3-4. All
    # figures come from compute_tax_structure().
    lead_anchor = ck_value_anchor(
        "TAX OPTIMIZATION",
        f"${r.total_tax_optimization_mm:,.1f}M tax savings",
        delta=f"{r.effective_tax_rate * 100:.1f}% effective rate",
        opportunity=f"${r.rollover_tax.deferred_gain_mm:,.1f}M rollover deferred",
        target=f"recommended: {r.recommended_structure}",
        tone="teal",
    )

    body = f"""
<div class="ck-page-wrap">

  {page_title}

  {lead_anchor}

  {form}

  <div class="ck-kpi-grid" style="margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1.3fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Purchase Price Allocation</div>
      {donut_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Structure Net Benefit Comparison</div>
      {comp_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Structure Comparison Detail</div>
    {struct_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Purchase Price Allocation Detail</div>
    {alloc_tbl}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">PTE / SALT Cap Benefits by State</div>
      {pte_tbl}
    </div>
    <div style="{cell}">
      <div style="{h3}">Rollover Tax Detail</div>
      <div style="font-family:JetBrains Mono,monospace;font-size:11px;color:{text};line-height:2">
        <div><span style="color:{text_dim}">Rollover value:</span> ${r.rollover_tax.rollover_value_mm:,.2f}M</div>
        <div><span style="color:{text_dim}">Deferred gain:</span> ${r.rollover_tax.deferred_gain_mm:,.2f}M</div>
        <div><span style="color:{text_dim}">Recognized (cash) gain:</span> ${r.rollover_tax.recognized_gain_mm:,.2f}M</div>
        <div><span style="color:{text_dim}">Immediate tax:</span> ${r.rollover_tax.immediate_tax_mm:,.2f}M</div>
        <div><span style="color:{text_dim}">Effective rate:</span> {r.rollover_tax.effective_tax_rate * 100:.1f}%</div>
        <div style="margin-top:10px;padding-top:8px;border-top:1px solid {border};font-size:10px;color:{text_dim};line-height:1.5">
          Partial rollover (boot-free if qualified) defers gain on contributed equity. Practical deferral
          often 85-95% of transaction value under §351 / §368 reorg rules.
        </div>
      </div>
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">After-Tax Cash Flow (Recommended Structure)</div>
    {flow_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Tax Thesis:</strong>
    Recommended structure: <strong style="color:{text}">{_html.escape(r.recommended_structure)}</strong>.
    Total optimization opportunity ${r.total_tax_optimization_mm:,.1f}M across step-up shield, PTE benefits,
    and rollover deferral. Modeled for {_html.escape(state)} with {hold}-year hold and {growth * 100:.0f}% revenue growth.
  </div>

</div>"""

    return chartis_shell(body, "Tax Structure Analyzer", active_nav="/tax-structure",
        editorial_intro={
            "eyebrow": "TAX STRUCTURE",
            "headline": "What the tax structure page reveals on this deal.",
            "italic_word": "reveals",
        })
