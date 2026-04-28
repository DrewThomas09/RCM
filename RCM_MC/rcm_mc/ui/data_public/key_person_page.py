"""Key Person Risk page — /key-person.

Clinical concentration, CEO/top-producer dependence, departure scenarios,
mitigation plans for healthcare PE diligence.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _concentration_gauge_svg(score: float) -> str:
    """Score is 0-100, higher = worse concentration."""
    import math
    w, h = 260, 160
    cx, cy = w / 2, h - 30
    r = 90
    bg = P["panel"]

    # Background arc
    def _arc(start_deg, end_deg, color, width):
        sr = math.radians(180 - start_deg)
        er = math.radians(180 - end_deg)
        x1 = cx + r * math.cos(sr)
        y1 = cy - r * math.sin(sr)
        x2 = cx + r * math.cos(er)
        y2 = cy - r * math.sin(er)
        return (f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 0 0 {x2:.1f} {y2:.1f}" '
                f'fill="none" stroke="{color}" stroke-width="{width}"/>')

    # 3 bands: green 0-40, amber 40-70, red 70-100
    bands = _arc(0, 72, P["positive"], 14) + _arc(72, 126, P["warning"], 14) + _arc(126, 180, P["negative"], 14)

    # Needle
    needle_deg = score / 100 * 180
    needle_r = math.radians(180 - needle_deg)
    nx = cx + (r - 16) * math.cos(needle_r)
    ny = cy - (r - 16) * math.sin(needle_r)
    needle = (
        f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" '
        f'stroke="{P["text"]}" stroke-width="3" stroke-linecap="round"/>'
        f'<circle cx="{cx}" cy="{cy}" r="5" fill="{P["text"]}"/>'
    )

    label = "CRITICAL" if score >= 70 else ("ELEVATED" if score >= 40 else "LOW")
    lcolor = P["negative"] if score >= 70 else (P["warning"] if score >= 40 else P["positive"])

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + bands + needle +
        f'<text x="{cx}" y="{cy - 24}" text-anchor="middle" fill="{P["text"]}" '
        f'font-size="24" font-weight="700" font-family="JetBrains Mono,monospace">{score:.0f}</text>'
        f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" fill="{lcolor}" '
        f'font-size="10" letter-spacing="0.12em" font-weight="600" font-family="Inter,sans-serif">{label}</text>'
        f'<text x="8" y="{h - 5}" fill="{P["text_faint"]}" font-size="9" font-family="JetBrains Mono,monospace">Diversified</text>'
        f'<text x="{w - 80}" y="{h - 5}" fill="{P["text_faint"]}" font-size="9" font-family="JetBrains Mono,monospace">Concentrated</text>'
        f'</svg>'
    )


def _revenue_share_svg(key_persons) -> str:
    if not key_persons:
        return ""
    sorted_kps = sorted(key_persons, key=lambda k: -k.revenue_share_pct)
    w, h = 520, 180
    pad_l, pad_r, pad_t, pad_b = 160, 40, 25, 20
    inner_w = w - pad_l - pad_r
    row_h = 20
    n = len(sorted_kps)
    total_h = n * row_h

    max_share = max(kp.revenue_share_pct for kp in sorted_kps)

    bg = P["panel"]; text_dim = P["text_dim"]; text_faint = P["text_faint"]

    risk_colors = {"high": P["negative"], "medium": P["warning"], "low": P["positive"]}

    bars = []
    for i, kp in enumerate(sorted_kps):
        y = pad_t + i * row_h
        bh = row_h - 6
        bw = kp.revenue_share_pct / max_share * inner_w
        color = risk_colors.get(kp.departure_risk, text_dim)
        bars.append(
            f'<text x="{pad_l - 6}" y="{y + bh - 1}" fill="{text_dim}" font-size="10" '
            f'text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(kp.role[:22])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bh}" fill="{color}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4:.1f}" y="{y + bh - 1}" fill="{P["text_dim"]}" font-size="10" '
            f'font-family="JetBrains Mono,monospace">{kp.revenue_share_pct * 100:.1f}%</text>'
        )

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(bars) +
        f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Revenue Share by Key Person (color = departure risk)</text>'
        f'</svg>'
    )


def _persons_table(persons) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    succ_colors = {
        "identified": P["positive"], "developing": P["accent"],
        "gap": P["warning"], "critical_gap": P["negative"],
    }
    risk_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}
    cols = [("Role","left"),("Anon ID","left"),("Rev Share","right"),("EBITDA Share","right"),
            ("Tenure","right"),("Succession","left"),("Departure Risk","left"),
            ("Rev at Risk ($M)","right"),("Replace Cost ($M)","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, kp in enumerate(persons):
        rb = panel_alt if i % 2 == 0 else bg
        sc = succ_colors.get(kp.succession_status, text_dim)
        rc = risk_colors.get(kp.departure_risk, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(kp.role)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(kp.name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{kp.revenue_share_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{kp.ebitda_share_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{kp.tenure_years:.1f} yr</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(kp.succession_status.replace("_", " "))}</span></td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{kp.departure_risk}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${kp.revenue_at_risk_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${kp.cost_to_replace_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _scenarios_table(scenarios) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]
    dep_colors = {"planned": P["positive"], "unplanned": P["warning"], "adverse (poaching)": P["negative"]}
    cols = [("Role","left"),("Departure Type","left"),("Rev Drop","right"),("EBITDA Drop","right"),
            ("Recovery (mo)","right"),("One-Time Cost","right"),("EV Impact","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, s in enumerate(scenarios):
        rb = panel_alt if i % 2 == 0 else bg
        dc = dep_colors.get(s.departure_type, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(s.role)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{dc};border:1px solid {dc};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.departure_type)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">-{s.revenue_drop_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">-{s.ebitda_drop_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.recovery_months}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${s.one_time_cost_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">${s.ev_impact_mm:+,.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _metrics_table(metrics) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"low": P["positive"], "medium": P["warning"], "high": P["negative"]}
    cols = [("Metric","left"),("Value","right"),("Unit","left"),("Threshold","right"),
            ("Status","left"),("Notes","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(metrics):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(m.status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{m.value:,.1f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.threshold:,.1f}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{m.status}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:260px">{_html.escape(m.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _mitigation_table(mitigations) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    prio_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    cols = [("Lever","left"),("One-Time Cost","right"),("Annual Cost","right"),
            ("Risk Reduction","right"),("Timeline (mo)","right"),("Priority","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, m in enumerate(mitigations):
        rb = panel_alt if i % 2 == 0 else bg
        pc = prio_colors.get(m.priority, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.lever)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${m.cost_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${m.annual_cost_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">{m.risk_reduction_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.timeline_months}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{m.priority}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_key_person(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    margin = _f("margin", 0.18)
    mult = _f("mult", 11.0)

    from rcm_mc.data_public.key_person import compute_key_person
    r = compute_key_person(sector=sector, revenue_mm=revenue, ebitda_margin=margin, exit_multiple=mult)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; neg = P["negative"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Concentration Score", f"{r.concentration_score:.0f}", "/100", "") +
        ck_kpi_block("Key Persons", str(len(r.key_persons)), "", "") +
        ck_kpi_block("Sector", sector, "", "") +
        ck_kpi_block("Revenue at Risk", f"${r.total_revenue_at_risk_mm:,.1f}M", "", "") +
        ck_kpi_block("EV at Risk", f"${r.total_ev_at_risk_mm:,.1f}M", "", "") +
        ck_kpi_block("Critical Gaps", str(sum(1 for kp in r.key_persons if kp.succession_status == "critical_gap")), "", "") +
        ck_kpi_block("High-Risk Persons", str(sum(1 for kp in r.key_persons if kp.departure_risk == "high")), "", "") +
        ck_kpi_block("Mitigation Cost", f"${r.total_mitigation_cost_mm:,.2f}M", "", "")
    )

    gauge_svg = _concentration_gauge_svg(r.concentration_score)
    share_svg = _revenue_share_svg(r.key_persons)
    persons_tbl = _persons_table(r.key_persons)
    scen_tbl = _scenarios_table(r.departure_scenarios)
    metrics_tbl = _metrics_table(r.concentration_metrics)
    mit_tbl = _mitigation_table(r.mitigation_plans)

    form = f"""
<form method="GET" action="/key-person" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Sector
    <input name="sector" value="{_html.escape(sector)}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:160px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue}" type="number" step="5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Margin
    <input name="margin" value="{margin}" type="number" step="0.01"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Exit Multiple
    <input name="mult" value="{mult}" type="number" step="0.5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Key Person &amp; Clinical Concentration Risk</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      CEO, medical director, top-producer dependency with departure scenarios and mitigation plans for {_html.escape(sector)} — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 2fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">Concentration Score</div>
      {gauge_svg}
      <p style="font-size:10px;color:{text_dim};margin-top:10px;line-height:1.5">
        Blended of revenue HHI, top-3 share, succession gaps, and departure risk flags.
        Above 70 signals material diligence exposure.
      </p>
    </div>
    <div style="{cell}">
      <div style="{h3}">Revenue Share by Key Person</div>
      {share_svg}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Key Person Inventory</div>
    {persons_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Concentration Metrics (Bus Factor, HHI, Succession Gaps)</div>
    {metrics_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Departure Scenarios — Planned / Unplanned / Adverse</div>
    {scen_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Mitigation Plan Options</div>
    {mit_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {neg if r.concentration_score >= 70 else acc};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Key Person Thesis:</strong>
    Concentration score {r.concentration_score:.0f}/100. Revenue at risk from 5 key persons: ${r.total_revenue_at_risk_mm:,.1f}M
    (${r.total_ev_at_risk_mm:,.1f}M of EV). High-priority mitigation deployment: ${r.total_mitigation_cost_mm:,.2f}M.
    Life insurance, non-solicits, and retention bonuses are the highest-ROI first moves.
  </div>

</div>"""

    return chartis_shell(body, "Key Person Risk", active_nav="/key-person")
