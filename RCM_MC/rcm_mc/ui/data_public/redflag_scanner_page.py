"""Deal Red-Flag Scanner — /redflag-scanner."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _flags_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Severity","center"),("Category","left"),("Flag","left"),
            ("Target","right"),("Benchmark P50","right"),("Δ vs P50","right"),("Evidence","left"),("Mitigation","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    sc = {"critical": neg, "high": neg, "medium": warn, "low": text_dim}
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cc = sc.get(f.severity, text_dim)
        # Determine display format based on value magnitude
        if f.target_value < 1.5 and f.target_value > 0:
            tv = f"{f.target_value * 100:.1f}%"
            bv = f"{f.benchmark_p50 * 100:.1f}%"
        elif f.target_value > 2000:
            tv = f"{f.target_value:.0f}"
            bv = f"{f.benchmark_p50:.0f}"
        else:
            tv = f"{f.target_value:.2f}"
            bv = f"{f.benchmark_p50:.2f}"
        cells = [
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(f.severity.upper())}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(f.category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(f.flag_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">{tv}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{bv}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cc};font-weight:600">{f.delta_vs_p50 * 100:+.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.evidence)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(f.mitigation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _categories_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Category","left"),("Flags","right"),("Critical","right"),("High","right"),
            ("Medium","right"),("Low","right"),("Weighted Score","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        ws_c = neg if c.weighted_score >= 70 else (warn if c.weighted_score >= 50 else (pos if c.weighted_score < 30 else text_dim))
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.flag_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if c.critical_count > 0 else text_dim}">{c.critical_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg if c.high_count > 0 else text_dim}">{c.high_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn if c.medium_count > 0 else text_dim}">{c.medium_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.low_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ws_c};font-weight:700">{c.weighted_score:.1f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _comps_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Comparable Deal","left"),("Sector","left"),("Year","right"),("MOIC","right"),("Flag Overlap","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        moic_c = pos if c.moic >= 2.5 else (P["warning"] if c.moic >= 1.8 else neg)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.comp_deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{moic_c};font-weight:700">{c.moic:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">{c.flag_overlap_count}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _severity_svg(categories) -> str:
    if not categories: return ""
    w, h = 560, 200
    pad_l, pad_r, pad_t, pad_b = 150, 20, 30, 30
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = 100  # scale up to 100 score
    bg = P["panel"]; neg = P["negative"]; warn = P["warning"]; pos = P["positive"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(categories)
    bar_h = min(20, (inner_h - (n - 1) * 6) / max(n, 1))
    bars = []
    for i, c in enumerate(categories):
        y = 30 + i * (bar_h + 6)
        bw = c.weighted_score / max_v * inner_w
        color = neg if c.weighted_score >= 65 else (warn if c.weighted_score >= 40 else pos)
        bars.append(
            f'<text x="{pad_l - 8}" y="{y + bar_h * 0.7}" fill="{text_dim}" font-size="10" text-anchor="end" font-family="JetBrains Mono,monospace">{_html.escape(c.category[:18])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bar_h:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{pad_l + bw + 4}" y="{y + bar_h * 0.7}" fill="{text_dim}" font-size="10" font-family="JetBrains Mono,monospace;font-weight:700">{c.weighted_score:.1f}</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Red-Flag Severity by Category (weighted score, 0-100)</text></svg>')


def render_redflag_scanner(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    name = params.get("name", "Target Platform Co")
    sector = params.get("sector", "Primary Care")
    ev = _f("ev_mm", 185.0)
    mult = _f("ev_ebitda", 14.5)
    margin = _f("margin", 0.17)
    lev = _f("leverage", 6.2)
    top_payer = _f("top_payer", 0.52)
    hy = _f("hold_years", 4.0)
    year = _i("year", 2024)
    moic = _f("moic", 1.8)

    from rcm_mc.data_public.redflag_scanner import compute_redflag_scanner
    r = compute_redflag_scanner(
        target_name=name, sector=sector, ev_mm=ev, ev_ebitda=mult,
        ebitda_margin=margin, leverage=lev, top_payer_pct=top_payer,
        hold_years=hy, year=year, moic=moic,
    )

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    rec_c = neg if "DO NOT" in r.overall_recommendation else (warn if "CAUTION" in r.overall_recommendation else (acc if "CONDITIONAL" in r.overall_recommendation else pos))

    kpi_strip = (
        ck_kpi_block("Target", r.target_name[:16], "", "") +
        ck_kpi_block("Sector", r.target_sector[:14], "", "") +
        ck_kpi_block("EV", f"${r.target_ev_mm:,.0f}M", "", "") +
        ck_kpi_block("EV/EBITDA", f"{r.target_ev_ebitda:.2f}x", "", "") +
        ck_kpi_block("Total Flags", str(r.total_flags), "", "") +
        ck_kpi_block("Critical", str(r.critical_flags), "", "") +
        ck_kpi_block("Risk Score", str(r.overall_risk_score), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _severity_svg(r.categories)
    flags_tbl = _flags_table(r.flags)
    cat_tbl = _categories_table(r.categories)
    comp_tbl = _comps_table(r.comparable_deals)

    sectors = ["Primary Care", "ASC", "Behavioral Health", "Dermatology", "Orthopedics",
               "Cardiology", "Home Health", "Hospice", "Dental DSO", "Dialysis Center",
               "Physical Therapy", "Oncology", "Women's Health / OB", "Urgent Care"]
    sector_opts = "".join(f'<option value="{_html.escape(s)}"{" selected" if s == sector else ""}>{_html.escape(s)}</option>' for s in sectors)

    form = f"""
<form method="GET" action="/redflag-scanner" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Target Name<input name="name" value="{_html.escape(name)}" type="text" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:140px"/></label>
  <label style="font-size:11px;color:{text_dim}">Sector<select name="sector" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace">{sector_opts}</select></label>
  <label style="font-size:11px;color:{text_dim}">EV ($M)<input name="ev_mm" value="{ev}" type="number" step="10" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">EV/EBITDA<input name="ev_ebitda" value="{mult}" type="number" step="0.5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">EBITDA Margin<input name="margin" value="{margin}" type="number" step="0.01" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">Top Payer %<input name="top_payer" value="{top_payer}" type="number" step="0.05" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">Leverage<input name="leverage" value="{lev}" type="number" step="0.25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">Hold (yr)<input name="hold_years" value="{hy}" type="number" step="0.5" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/></label>
  <label style="font-size:11px;color:{text_dim}">Year<input name="year" value="{year}" type="number" step="1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/></label>
  <label style="font-size:11px;color:{text_dim}">MOIC<input name="moic" value="{moic}" type="number" step="0.1" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:60px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Scan</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Deal Red-Flag Scanner</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Rule-based red-flag detection · corpus-benchmarked · severity-ranked · IC-ready — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {rec_c};padding:14px 18px;margin-bottom:16px;font-size:13px;font-family:JetBrains Mono,monospace">
    <div style="font-size:10px;letter-spacing:0.1em;color:{text_dim};text-transform:uppercase;margin-bottom:6px">IC Recommendation</div>
    <div style="color:{rec_c};font-weight:700;font-size:14px">{_html.escape(r.overall_recommendation)}</div>
    <div style="color:{text_dim};font-size:11px;margin-top:4px">Risk score {r.overall_risk_score}/100 · {r.total_flags} total flags ({r.critical_flags} critical, {r.high_flags} high)</div>
  </div>
  <div style="{cell}"><div style="{h3}">Category-Level Severity</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Full Flag Inventory — Severity-Ranked</div>{flags_tbl}</div>
  <div style="{cell}"><div style="{h3}">Category Rollup</div>{cat_tbl}</div>
  <div style="{cell}"><div style="{h3}">Corpus Comparable Deals (same sector)</div>{comp_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Scanner Methodology:</strong> Each flag compares target metric against {r.corpus_deal_count:,}-deal corpus base rates.
    P50/P90 benchmarks are sector-specific where n≥5; otherwise fall back to full-corpus. Severity is derived from magnitude of deviation from P50.
    This scanner is intended as a pre-IC screen — flags marked critical should be resolved or explicitly accepted in the IC memo before committing capital.
    Use in conjunction with /base-rates for numeric context and /sponsor-heatmap for sponsor-sector pattern check.
  </div>
</div>"""

    return chartis_shell(body, "Red-Flag Scanner", active_nav="/redflag-scanner")
