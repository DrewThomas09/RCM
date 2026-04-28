"""Value Creation Plan / 100-Day Plan Tracker page — /value-creation-plan.

Post-close plan tracking: initiative inventory, milestone checkpoints,
category rollup, EBITDA bridge.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _bridge_svg(bridge) -> str:
    if not bridge:
        return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 60, 30, 30, 50
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b

    max_v = max(b.ebitda_mm for b in bridge) * 1.15 or 1

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]; border = P["border"]

    n = len(bridge)
    bar_w = (inner_w - (n - 1) * 12) / n

    colors = [P["text_faint"], acc, P["warning"], pos]

    bars = []
    for i, b in enumerate(bridge):
        x = pad_l + i * (bar_w + 12)
        bh = (b.ebitda_mm / max_v) * inner_h
        y = (h - pad_b) - bh
        color = colors[i % len(colors)]
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.88"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{P["text_dim"]}" font-size="11" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${b.ebitda_mm:,.1f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="10" '
            f'text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(b.stage)}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 28}" fill="{pos if b.delta_from_entry_mm > 0 else text_faint}" '
            f'font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">'
            f'{"+" if b.delta_from_entry_mm > 0 else ""}${b.delta_from_entry_mm:,.1f}M</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">EBITDA Bridge ($M)</text>'
        f'</svg>'
    )


def _checkpoint_svg(checkpoints) -> str:
    """Horizontal bar chart of plan realization at each checkpoint."""
    if not checkpoints:
        return ""
    w = 540
    row_h = 28
    h = len(checkpoints) * row_h + 40
    pad_l = 90
    pad_r = 40
    inner_w = w - pad_l - pad_r

    max_v = max(cp.pct_of_plan for cp in checkpoints) or 1

    bg = P["panel"]; acc = P["accent"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]

    bars = []
    for i, cp in enumerate(checkpoints):
        y = 25 + i * row_h
        bh = 14
        bw = cp.pct_of_plan / max_v * inner_w
        # Color intensity increases
        alpha = 0.55 + (i / len(checkpoints)) * 0.4
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(cp.checkpoint)}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{pos}" opacity="{alpha:.2f}"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" '
            f'font-family="JetBrains Mono,monospace">${cp.ebitda_realized_mm:,.1f}M ({cp.pct_of_plan * 100:.0f}%)</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Cumulative EBITDA Realization by Checkpoint</text>'
        f'</svg>'
    )


def _initiatives_table(initiatives) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {
        "complete": P["positive"], "on_track": P["accent"],
        "at_risk": P["warning"], "delayed": P["negative"], "not_started": P["text_faint"],
    }
    prio_colors = {
        "critical": P["negative"], "high": P["warning"],
        "medium": P["accent"], "low": P["text_faint"],
    }
    cols = [("Category","left"),("Initiative","left"),("Target Day","right"),
            ("Impact ($M)","right"),("Cost ($M)","right"),("Net ($M)","right"),
            ("Progress","right"),("Status","left"),("Owner","left"),("Priority","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, init in enumerate(initiatives):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(init.actual_status, text_dim)
        pc = prio_colors.get(init.priority, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(init.category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(init.name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">Day {init.target_day}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">${init.impact_ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${init.cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${init.net_impact_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sc}">{init.progress_pct * 100:.0f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(init.actual_status.replace("_", " "))}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(init.owner_role)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{init.priority}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _checkpoint_table(checkpoints) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Checkpoint","left"),("Complete","right"),("On Track","right"),
            ("At Risk","right"),("EBITDA Realized ($M)","right"),("% of Plan","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, cp in enumerate(checkpoints):
        rb = panel_alt if i % 2 == 0 else bg
        ar_c = P["negative"] if cp.initiatives_at_risk > 2 else (P["warning"] if cp.initiatives_at_risk > 0 else P["text_dim"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(cp.checkpoint)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{cp.initiatives_completed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"]}">{cp.initiatives_on_track}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ar_c}">{cp.initiatives_at_risk}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${cp.ebitda_realized_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{cp.pct_of_plan * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _category_table(categories) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Category","left"),("# Initiatives","right"),("Gross Impact ($M)","right"),
            ("Cost ($M)","right"),("Net ($M)","right"),("% of Plan","right"),("Avg Progress","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, c in enumerate(categories):
        rb = panel_alt if i % 2 == 0 else bg
        prog_c = pos if c.avg_progress >= 0.6 else (P["accent"] if c.avg_progress >= 0.3 else P["warning"])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.n_initiatives}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${c.total_impact_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${c.total_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">${c.net_impact_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.pct_of_total_plan * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{prog_c};font-weight:600">{c.avg_progress * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _bridge_table(bridge) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Stage","left"),("EBITDA ($M)","right"),("Δ from Entry ($M)","right"),("Margin","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, b in enumerate(bridge):
        rb = panel_alt if i % 2 == 0 else bg
        delta_c = pos if b.delta_from_entry_mm > 0 else P["text_faint"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.stage)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${b.ebitda_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{delta_c};font-weight:600">${b.delta_from_entry_mm:+,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.margin_pct * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_value_creation_plan(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    entry = _f("entry_ebitda", 25.0)
    day = _i("current_day", 200)

    from rcm_mc.data_public.value_creation_plan import compute_value_creation_plan
    r = compute_value_creation_plan(sector=sector, entry_ebitda_mm=entry, current_day=day)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Hold Day", f"Day {r.hold_day}", "", "") +
        ck_kpi_block("Entry EBITDA", f"${r.entry_ebitda_mm:,.2f}M", "", "") +
        ck_kpi_block("Current EBITDA", f"${r.current_ebitda_mm:,.2f}M", "", "") +
        ck_kpi_block("Target EBITDA", f"${r.target_ebitda_mm:,.2f}M", "", "") +
        ck_kpi_block("Exit Projection", f"${r.exit_ebitda_mm:,.2f}M", "", "") +
        ck_kpi_block("Plan Net Value", f"${r.plan_net_value_mm:,.2f}M", "", "") +
        ck_kpi_block("Execution Score", f"{r.execution_score:.0f}", "/100", "") +
        ck_kpi_block("Initiatives", str(len(r.initiatives)), "", "")
    )

    bridge_svg = _bridge_svg(r.ebitda_bridge)
    checkpoint_svg = _checkpoint_svg(r.checkpoints)
    init_tbl = _initiatives_table(r.initiatives)
    cp_tbl = _checkpoint_table(r.checkpoints)
    cat_tbl = _category_table(r.category_rollups)
    bridge_tbl = _bridge_table(r.ebitda_bridge)

    form = f"""
<form method="GET" action="/value-creation-plan" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Entry EBITDA ($M)
    <input name="entry_ebitda" value="{entry}" type="number" step="1"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Current Day
    <input name="current_day" value="{day}" type="number" step="30"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">

  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Value Creation Plan — 100-Day Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Post-close initiative tracking with EBITDA bridge, checkpoint milestones, category rollup — {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">EBITDA Bridge: Entry → Current → Target → Exit</div>
      {bridge_svg}
    </div>
    <div style="{cell}">
      <div style="{h3}">Checkpoint Realization</div>
      {checkpoint_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Category Rollup</div>
    {cat_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Milestone Checkpoints</div>
    {cp_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Initiative Inventory ({len(r.initiatives)} items)</div>
    {init_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">EBITDA Bridge Detail</div>
    {bridge_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">VCP Thesis:</strong>
    ${r.entry_ebitda_mm:,.1f}M entry EBITDA → ${r.target_ebitda_mm:,.1f}M target via ${r.total_plan_impact_mm:,.1f}M gross impact
    across {len(r.initiatives)} initiatives. Current execution score {r.execution_score:.0f}/100 at Day {r.hold_day}.
    Plan net value ${r.plan_net_value_mm:,.1f}M translates to ~${r.plan_net_value_mm * 11:,.0f}M of EV at 11x exit.
  </div>

</div>"""

    return chartis_shell(body, "Value Creation Plan", active_nav="/value-creation-plan")
