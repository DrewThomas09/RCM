"""TEAM Calculator — /team-calculator."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {
        "CRITICAL": P["negative"],
        "HIGH":     P["negative"],
        "MEDIUM":   P["warning"],
        "LOW":      P["accent"],
        "UNAFFECTED": P["text_dim"],
    }.get(t, P["text_dim"])


def _metro_color(t: str) -> str:
    return {
        "Major Metro": P["positive"],
        "Mid-Metro":   P["accent"],
        "Small Metro": P["warning"],
        "Micropolitan": P["text_dim"],
    }.get(t, P["text_dim"])


def _episode_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("ID", "left"), ("Episode", "left"), ("Trigger DRG", "left"),
            ("Anchor LOS", "right"), ("Avg Medicare $", "right"),
            ("Post-Acute %", "right"), ("Annual Vol.", "right"),
            ("Trend", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        trend_c = P["negative"] if e.volume_trend_pct < 0 else pos
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(e.episode_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:260px">{_html.escape(e.episode_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(e.trigger_drg)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.avg_anchor_stay_days:.1f}d</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${e.avg_total_episode_medicare_spend:,.0f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{e.post_acute_pct*100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{e.annual_national_volume:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{trend_c};font-weight:700">{e.volume_trend_pct:+.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cbsa_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("CBSA", "left"), ("CBSA Name", "left"), ("State", "center"),
            ("Population (K)", "right"), ("Hospitals", "right"),
            ("Episode Spend ($M)", "right"), ("Annual Episodes", "right"),
            ("Adj. Factor", "right"), ("Tier", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        mc = _metro_color(c.tier)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.cbsa_code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:360px">{_html.escape(c.cbsa_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.state)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.population_thousands:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.hospitals_in_cbsa}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.baseline_medicare_episode_spend_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.estimated_annual_episodes:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.regional_adjustment_factor:.2f}x</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{mc};border:1px solid {mc};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _risk_schedule_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("PY", "right"), ("Year", "right"), ("Upside Cap", "right"),
            ("Downside Cap", "right"), ("Stop-Loss", "right"),
            ("Quality Wt", "right"), ("Notes", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, y in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">PY{y.py_number}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{y.performance_year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">+{y.upside_cap_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">-{y.downside_cap_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{y.stop_loss_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{y.quality_weight_pct:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:540px">{_html.escape(y.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exposure_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Deal", "left"), ("Year", "right"), ("Buyer", "left"),
            ("Facilities", "right"), ("CBSAs", "left"),
            ("Baseline $M/yr", "right"), ("PY1 Downside", "right"),
            ("PY3 Downside", "right"), ("PY5 Downside", "right"),
            ("Risk Tier", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(e.risk_tier)
        cbsa_str = ", ".join(c.split(",")[0] for c in e.matched_cbsas[:2]) + (
            f" (+{len(e.matched_cbsas)-2})" if len(e.matched_cbsas) > 2 else "")
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:180px">{_html.escape(e.buyer)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{e.inferred_facility_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:220px">{_html.escape(cbsa_str)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${e.annual_at_risk_mm:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${e.py1_downside_exposure_mm:.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${e.py3_downside_exposure_mm:.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${e.py5_downside_exposure_mm:.2f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(e.risk_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_team_calculator(params: dict = None) -> str:
    from rcm_mc.data_public.team_calculator import compute_team_calculator
    r = compute_team_calculator()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("CBSAs Tracked", f"{r.total_cbsas_tracked}", "of 188 mandated", "") +
        ck_kpi_block("Hospitals Mandated", f"{r.total_hospitals_mandated:,}", "in tracked CBSAs", "") +
        ck_kpi_block("Episode Types", f"{len(r.episodes)}", "5 surgical categories", "") +
        ck_kpi_block("National Episode Vol", f"{r.total_national_episode_volume:,}", "Medicare/yr", "") +
        ck_kpi_block("National Spend", f"${r.total_national_episode_spend_b:.1f}B", "per year", "") +
        ck_kpi_block("PY5 Downside", f"${r.total_programwide_downside_exposure_py5_b:.1f}B", "programwide at peak", "") +
        ck_kpi_block("Corpus Deals Exposed", f"{r.total_corpus_deals_exposed}", "of 1,705", "") +
        ck_kpi_block("Corpus PY5 Risk", f"${r.total_corpus_py5_downside_mm:.0f}M", "", "")
    )

    episode_tbl = _episode_table(r.episodes)
    cbsa_tbl = _cbsa_table(r.cbsa_lattice)
    risk_tbl = _risk_schedule_table(r.risk_share_schedule)
    exp_tbl = _exposure_table(r.deal_exposures)

    citations_html = "<br>".join(f"• {_html.escape(c)}" for c in r.regulation_citations)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">TEAM Calculator — Mandatory Bundled-Payment Exposure (188 CBSAs × 5 Surgical Episodes)</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">CMS Transforming Episode Accountability Model (TEAM), finalized via FY 2025 IPPS/LTCH Final Rule · effective {r.effective_date} · KB {r.knowledge_base_version} · {r.total_cbsas_tracked} CBSAs tracked of 188 mandated · ${r.total_national_episode_spend_b:.1f}B national annual episode spend · ${r.total_programwide_downside_exposure_py5_b:.1f}B programwide PY5 downside exposure</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Episode Catalog — 5 Mandatory Surgical Bundle Types</div>{episode_tbl}</div>
  <div style="{cell}"><div style="{h3}">CBSA Lattice — 50 Tracked Core-Based Statistical Areas</div>{cbsa_tbl}</div>
  <div style="{cell}"><div style="{h3}">Risk-Sharing Schedule — 5 Performance Years (2026-2030)</div>{risk_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top 60 Corpus Deal Exposures — Hospital Deals in Mandated CBSAs</div>{exp_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">TEAM Exposure Thesis:</strong>
    The Transforming Episode Accountability Model is the largest mandatory bundled-payment program
    since the original BPCI. Under TEAM, {r.total_cbsas_tracked}-plus CBSAs (of 188 total nationally) mandate
    that every acute-care hospital accept total-cost accountability for the 5 surgical episodes
    + 30-day post-discharge window. Programwide PY5 downside exposure: <strong style="color:{text}">
    ${r.total_programwide_downside_exposure_py5_b:.1f}B/year</strong> at the 15% downside cap.
    <br><br>
    <strong style="color:{text}">Diligence implications:</strong>
    Every hospital deal in the corpus needs to be screened for CBSA overlap. {r.total_corpus_deals_exposed} corpus deals
    currently map to mandated CBSAs with an aggregate PY5 downside exposure of
    <strong style="color:{text}">${r.total_corpus_py5_downside_mm:.0f}M</strong>. This is not a modeled
    stress — it is a statutory obligation beginning 2026-01-01 regardless of deal structure or sponsor
    strategy. Per-hospital PY5 exposure is a direct EBITDA adjustment for underwriting.
    <br><br>
    <strong style="color:{text}">Why this is the single highest-leverage regulatory engine to build:</strong>
    (1) Mandatory, not elective — no workaround via refusing to participate.
    (2) Quantifiable — hospital-specific baseline Medicare episode spend × downside cap is a dollar figure.
    (3) Compound with Named-Failure Library: orthopedic/MSK-heavy targets are most exposed (LEJR + SHFFT
    are the highest-volume episodes).
    (4) Lever for post-close value creation: home-health and SNF integration cut post-acute spend 15-25%,
    which is the margin that determines TEAM reconciliation winners vs losers.
    <br><br>
    <strong style="color:{text}">Knowledge-base provenance (versioned, cited):</strong>
    <div style="font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px;line-height:1.5;margin-top:4px">
    KB version: {r.knowledge_base_version} · Effective: {r.effective_date}<br>
    {citations_html}
    </div>
  </div>
</div>"""

    return chartis_shell(body, "TEAM Calculator", active_nav="/team-calculator")
