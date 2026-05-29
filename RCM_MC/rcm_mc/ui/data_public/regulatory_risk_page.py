"""Regulatory Risk Tracker page — /regulatory-risk.

Sector-specific regulatory risk scoring, active CMS/OIG/HRSA event tracking,
materiality schedule, and compliance gap inventory.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row, ck_value_anchor, ck_illustrative_note


def _materiality_chart(items):
    """Summary chart — regulatory exposures by EV impact (tone by materiality tier)."""
    def _tone(m):
        t = (m.materiality_tier or "").lower()
        if "critical" in t or "high" in t: return "negative"
        if "moderate" in t or "medium" in t: return "warning"
        return "navy"
    top = sorted(items, key=lambda m: abs(m.ev_impact_mm), reverse=True)
    total = sum(abs(m.ev_impact_mm) for m in top) or 1.0
    rows = [ck_bar_row(f"{m.impact_name}",
            f"${m.ev_impact_mm:+,.1f}M EV · ${m.ebitda_impact_mm:+,.1f}M EBITDA · {m.materiality_tier}",
            abs(m.ev_impact_mm) / total * 100.0, tone=_tone(m)) for m in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of regulatory EV exposure '
            '· value = EV + EBITDA impact + tier · tone = materiality tier</div></div>')


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
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
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
            f'{ck_data_cell(f"""{_html.escape(e.name)}""", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(e.agency)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(e.effective_date)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{e.status}</span>""")}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{dc}">{_html.escape(e.direction)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dc if e.applies_to_deal else text_dim}">{e.revenue_impact_pct * 100:+.1f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{applies_color};border:1px solid {applies_color};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{"yes" if e.applies_to_deal else "no"}</span>""")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
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
            f'{ck_data_cell(f"""{_html.escape(m.impact_name)}""", mono=True)}',
            f'{ck_data_cell(f"""{m.revenue_impact_pct * 100:+.1f}%""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""${m.ebitda_impact_mm:+,.2f}M""", align="right", mono=True, tone="neg")}',
            f'{ck_data_cell(f"""${m.ev_impact_mm:+,.2f}M""", align="right", mono=True, tone="neg", weight=600)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{m.materiality_tier}</span>""")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
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
            f'{ck_data_cell(f"""{_html.escape(g.area)}""", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(g.requirement)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;text-transform:uppercase;letter-spacing:0.06em">{g.current_status}</span>""")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"] if g.remediation_cost_mm else text_dim}">${g.remediation_cost_mm:,.2f}</td>',
            f'{ck_data_cell(f"""{g.days_to_close}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (
        f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
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
    mat_chart = _materiality_chart(r.materiality_schedule)
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

    page_title = ck_page_title(
        "Regulatory Risk Tracker",
        eyebrow="REGULATORY RISK",
        meta=f"""Sector-specific regulatory risk — Stark, AKS, HIPAA, OIG, 340B + active CMS/OIG events — {r.corpus_deal_count:,} corpus deals""",
    )
    
    # Lead takeaway — surface the computed regulatory exposure (EV at
    # risk → remediation cost to mitigate), otherwise buried as KPIs
    # #6-7 and in the bottom thesis. All figures come from
    # compute_regulatory_risk(). Tone tracks the risk score so the
    # band reads green/amber/red at a glance.
    _reg_tone = (
        "negative" if r.risk_score >= 7
        else "warning" if r.risk_score >= 4
        else "positive"
    )
    lead_anchor = ck_value_anchor(
        "REGULATORY EXPOSURE",
        f"${r.total_ev_risk_mm:,.1f}M EV at risk",
        delta=f"risk {r.risk_score}/10 · {r.risk_label}",
        opportunity=f"{r.total_revenue_drag_pct * 100:+.1f}% revenue drag",
        target=f"${r.total_remediation_cost_mm:,.1f}M to remediate",
        tone=_reg_tone,
    )

    # Real CMS nursing-home enforcement benchmark — shown for nursing/post-acute
    # sectors (where we have real regulatory-penalty data). Other sectors keep
    # the calculator without a fabricated enforcement anchor.
    cms_panel = ""
    try:
        from rcm_mc.ui.data_public._benchmark_panels import _is_snf_sector
        if _is_snf_sector(sector):
            from rcm_mc.data import snf as _snf
            e = _snf.snf_enforcement_summary()
            if e.get("facilities") and e.get("median_fine_usd"):
                cms_panel = (
                    f'<div style="background:{panel};border:1px solid {border};'
                    f'border-left:3px solid {acc};padding:14px 16px;margin-bottom:16px">'
                    f'<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
                    f'text-transform:uppercase;color:{text_dim};margin-bottom:6px">'
                    f'Regulatory-enforcement benchmark · LIVE (CMS Care Compare, nursing homes)</div>'
                    f'<p style="font-size:12px;color:{text_dim};margin:0 0 8px">'
                    f'Of <b style="color:{text}">{e["facilities"]:,}</b> Medicare/Medicaid '
                    f'nursing homes, <b style="color:{text}">{e["pct_fined"]:.0f}%</b> '
                    f'carry a CMS fine (median <b style="color:{text}">${e["median_fine_usd"]:,}</b>, '
                    f'${e["total_fines_usd"]/1e6:,.0f}M total); '
                    f'{e["pct_payment_denial"]:.0f}% have a payment denial and '
                    f'{e["pct_any_penalty"]:.0f}% any penalty. The real published '
                    f'enforcement base rate for this sector.</p>'
                    f'<p style="font-size:11px;color:{text_dim};margin:0">'
                    f'Real CMS enforcement data (nursing homes) — a sector base rate, '
                    f'<b>not</b> this deal’s exposure. The model below is illustrative, '
                    f'scaled by your inputs.</p></div>')
    except Exception:
        cms_panel = ""

    body = f"""
<div class="ck-page-wrap">

  {page_title}

  {ck_illustrative_note("regulatory figures")}
  {lead_anchor}
  {cms_panel}

  {form}

  <div class="ck-kpi-grid" style="margin-bottom:20px">
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
    {mat_chart}{mat_tbl}
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

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "Regulatory Risk Tracker", active_nav="/regulatory-risk",
        editorial_intro={
            "eyebrow": "REGULATORY RISK",
            "headline": "What the regulatory risk page reveals on this deal.",
            "italic_word": "reveals",
        })
