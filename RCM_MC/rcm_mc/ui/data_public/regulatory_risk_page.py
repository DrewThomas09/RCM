"""Regulatory Risk Tracker page — /regulatory-risk.

Sector-specific regulatory risk scoring, active CMS/OIG/HRSA event tracking,
materiality schedule, and compliance gap inventory.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _risk_dial_svg(score: int, label: str) -> str:
    """10-segment dial. Segments 1-3 green, 4-6 amber, 7-10 red."""
    import math
    w, h = 280, 170
    cx, cy = w / 2, h - 25
    r_outer, r_inner = 95, 70
    bg = P["panel"]

    segs = []
    for i in range(10):
        start = 180 - i * 18
        end = 180 - (i + 1) * 18
        sr = math.radians(start)
        er = math.radians(end)
        x1o, y1o = cx + r_outer * math.cos(sr), cy - r_outer * math.sin(sr)
        x2o, y2o = cx + r_outer * math.cos(er), cy - r_outer * math.sin(er)
        x1i, y1i = cx + r_inner * math.cos(er), cy - r_inner * math.sin(er)
        x2i, y2i = cx + r_inner * math.cos(sr), cy - r_inner * math.sin(sr)
        if i < 3:
            color = P["positive"]
        elif i < 6:
            color = P["warning"]
        else:
            color = P["negative"]
        if i >= score:
            color = P["border"]
        path = f'M {x1o:.1f} {y1o:.1f} A {r_outer} {r_outer} 0 0 0 {x2o:.1f} {y2o:.1f} L {x1i:.1f} {y1i:.1f} A {r_inner} {r_inner} 0 0 1 {x2i:.1f} {y2i:.1f} Z'
        segs.append(f'<path d="{path}" fill="{color}" opacity="0.9"/>')

    label_color = P["positive"] if score <= 3 else (P["warning"] if score <= 6 else P["negative"])

    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{w}" height="{h}" fill="{bg}"/>'
        + "".join(segs) +
        f'<text x="{cx}" y="{cy - 20}" text-anchor="middle" fill="{P["text"]}" '
        f'font-size="28" font-weight="700" font-family="JetBrains Mono,monospace">{score}</text>'
        f'<text x="{cx}" y="{cy - 3}" text-anchor="middle" fill="{label_color}" '
        f'font-size="11" font-weight="600" letter-spacing="0.08em" font-family="Inter,sans-serif">{_html.escape(label.upper())}</text>'
        f'<text x="10" y="{h - 5}" fill="{P["text_faint"]}" font-size="9" font-family="JetBrains Mono,monospace">LOW</text>'
        f'<text x="{w - 30}" y="{h - 5}" fill="{P["text_faint"]}" font-size="9" font-family="JetBrains Mono,monospace">CRITICAL</text>'
        f'</svg>'
    )


def _risk_factors_table(factors) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    sev_colors = {"high": P["negative"], "medium": P["warning"], "low": P["text_faint"]}
    cols = [("Risk Factor","left"),("Severity","left"),("Description","left"),("Mitigations","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, f in enumerate(factors):
        rb = panel_alt if i % 2 == 0 else bg
        sc = sev_colors.get(f.severity, text_dim)
        cells = [
            f'<td style="text-align:left;padding:6px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};max-width:220px">{_html.escape(f.factor)}</td>',
            f'<td style="text-align:left;padding:6px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{f.severity}</span></td>',
            f'<td style="text-align:left;padding:6px 10px;font-size:10px;color:{text_dim};max-width:380px;line-height:1.5">{_html.escape(f.description)}</td>',
            f'<td style="text-align:left;padding:6px 10px;font-size:10px;color:{text_dim};max-width:280px;line-height:1.5">{_html.escape(f.mitigations)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _events_table(events) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    dir_colors = {"positive": P["positive"], "negative": P["negative"], "mixed": P["warning"]}
    status_colors = {"final": P["negative"], "active": P["warning"], "phase-in": P["warning"],
                     "proposed": P["text_faint"], "enforcement": P["negative"]}
    cols = [("Rule / Event","left"),("Agency","left"),("Effective","right"),("Status","left"),
            ("Direction","left"),("Revenue Impact","right"),("Applies","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, e in enumerate(events):
        rb = panel_alt if i % 2 == 0 else bg
        dc = dir_colors.get(e.direction, text_dim)
        sc = status_colors.get(e.status, text_dim)
        applies_color = P["negative"] if e.applies_to_deal else P["text_faint"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(e.name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(e.agency)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(e.effective_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{e.status}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{dc}">{_html.escape(e.direction)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dc if e.applies_to_deal else text_dim}">{e.revenue_impact_pct * 100:+.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{applies_color};border:1px solid {applies_color};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{"yes" if e.applies_to_deal else "no"}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _materiality_table(schedule) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]
    tier_colors = {"material": P["negative"], "non-material": P["text_faint"]}
    cols = [("Event","left"),("Revenue Impact","right"),("EBITDA Δ","right"),
            ("EV Δ","right"),("Materiality","left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    if not schedule:
        return f'<p style="color:{text_dim};font-size:11px;padding:12px 0">No regulatory events materially apply to this sector.</p>'
    trs = []
    for i, m in enumerate(schedule):
        rb = panel_alt if i % 2 == 0 else bg
        tc = tier_colors.get(m.materiality_tier, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(m.impact_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{m.revenue_impact_pct * 100:+.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">${m.ebitda_impact_mm:+,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">${m.ev_impact_mm:+,.2f}M</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{m.materiality_tier}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def _gaps_table(gaps) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]
    stat_colors = {"compliant": P["positive"], "gap": P["negative"], "unknown": P["warning"]}
    cols = [("Compliance Area","left"),("Requirement","left"),("Status","left"),
            ("Remediation ($M)","right"),("Days to Close","right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols
    )
    trs = []
    for i, g in enumerate(gaps):
        rb = panel_alt if i % 2 == 0 else bg
        sc = stat_colors.get(g.current_status, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(g.area)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(g.requirement)}</td>',
            f'<td style="text-align:left;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{g.current_status}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if g.remediation_cost_mm else text_dim}">${g.remediation_cost_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{g.days_to_close}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (
        f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
    )


def render_regulatory_risk(params: dict = None) -> str:
    params = params or {}
    sector = params.get("sector", "Physician Services") or "Physician Services"

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 80.0)
    margin = _f("margin", 0.18)
    mult = _f("mult", 11.0)
    ev = _f("ev", 250.0)

    from rcm_mc.data_public.regulatory_risk import compute_regulatory_risk
    r = compute_regulatory_risk(
        sector=sector, revenue_mm=revenue, ebitda_margin=margin,
        exit_multiple=mult, ev_mm=ev,
    )

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Sector", sector, "", "") +
        ck_kpi_block("Risk Score", f"{r.risk_score}", "/10", "") +
        ck_kpi_block("Risk Tier", r.risk_label, "", "") +
        ck_kpi_block("Active Events", str(sum(1 for e in r.active_events if e.applies_to_deal)), "", "") +
        ck_kpi_block("Revenue Drag", f"{r.total_revenue_drag_pct * 100:+.1f}%", "", "") +
        ck_kpi_block("EV at Risk", f"${r.total_ev_risk_mm:,.1f}M", "", "") +
        ck_kpi_block("Remediation", f"${r.total_remediation_cost_mm:,.1f}M", "", "") +
        ck_kpi_block("Gaps Identified", str(sum(1 for g in r.compliance_gaps if g.current_status != "compliant")), "", "")
    )

    dial_svg = _risk_dial_svg(r.risk_score, r.risk_label)
    risk_tbl = _risk_factors_table(r.risk_factors)
    event_tbl = _events_table(r.active_events)
    mat_tbl = _materiality_table(r.materiality_schedule)
    gap_tbl = _gaps_table(r.compliance_gaps)

    form = f"""
<form method="GET" action="/regulatory-risk" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
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
  <label style="font-size:11px;color:{text_dim}">Exit Mult
    <input name="mult" value="{mult}" type="number" step="0.5"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">EV ($M)
    <input name="ev" value="{ev}" type="number" step="10"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
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
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Regulatory Risk Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">
      Sector-specific regulatory risk — Stark, AKS, HIPAA, OIG, 340B + active CMS/OIG events — {r.corpus_deal_count:,} corpus deals
    </p>
  </div>

  {form}

  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">
    {kpi_strip}
  </div>

  <div style="display:grid;grid-template-columns:1fr 2fr;gap:16px;margin-bottom:16px">
    <div style="{cell}">
      <div style="{h3}">{_html.escape(sector)} Risk Profile</div>
      {dial_svg}
      <p style="font-size:10px;color:{text_dim};margin-top:12px;line-height:1.5">
        Composite score across Stark/AKS enforcement density, OIG work-plan priority,
        CMS rule change cadence, and corporate-practice litigation activity.
      </p>
    </div>
    <div style="{cell}">
      <div style="{h3}">Active Regulatory Events ({len(r.active_events)} tracked)</div>
      {event_tbl}
    </div>
  </div>

  <div style="{cell}">
    <div style="{h3}">Deal-Applicable Materiality Schedule</div>
    {mat_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Sector Risk Factor Catalog ({len(r.risk_factors)} factors)</div>
    {risk_tbl}
  </div>

  <div style="{cell}">
    <div style="{h3}">Compliance Gap Inventory</div>
    {gap_tbl}
  </div>

  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {neg};
    padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Regulatory Thesis:</strong>
    {_html.escape(sector)} at risk tier <strong style="color:{text}">{r.risk_label}</strong>.
    Cumulative rev drag {r.total_revenue_drag_pct * 100:+.1f}%, implied EV at risk ${r.total_ev_risk_mm:,.1f}M,
    plus ${r.total_remediation_cost_mm:,.1f}M of pre-close remediation spend. Materiality assessed
    at &gt;5% EV threshold.
  </div>

</div>"""

    return chartis_shell(body, "Regulatory Risk Tracker", active_nav="/regulatory-risk")
