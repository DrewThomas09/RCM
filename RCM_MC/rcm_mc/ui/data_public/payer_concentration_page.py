"""Payer Concentration Tracker — /payer-concentration."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_data_cell, ck_kpi_block, ck_paired_block, ck_page_title,
    ck_bar_row, ck_scatter, ck_value_anchor)


def _payers_scatter(items):
    """Quadrant view — revenue concentration vs denial rate, so the
    'big + high-denial' payers (upper-right) jump out of the roster."""
    import statistics
    pts, shares, denials = [], [], []
    for p in items:
        x = p.revenue_share_pct * 100.0; y = p.denial_rate_pct * 100.0
        tn = ('negative' if p.renewal_risk_score >= 70
              else 'warning' if p.renewal_risk_score >= 45 else 'teal')
        pts.append((x, y, p.payer_name, tn)); shares.append(x); denials.append(y)
    xref = statistics.median(shares) if shares else None
    yref = statistics.median(denials) if denials else None
    return ck_scatter(
        pts, x_label='Revenue share %', y_label='Denial rate %',
        x_ref=xref, y_ref=yref,
        caption='Each dot = a payer · upper-right = high-concentration + high-denial (priority) · tone = renewal risk',
    )


def _payers_chart(items):
    """Summary chart — payer revenue concentration (tone by renewal risk)."""
    def _tone(p):
        if p.renewal_risk_score >= 70: return "negative"
        if p.renewal_risk_score >= 45: return "warning"
        return "teal"
    top = sorted(items, key=lambda p: p.revenue_share_pct, reverse=True)
    rows = [ck_bar_row(f"{p.payer_name} · {p.payer_type}",
            f"{p.revenue_share_pct * 100:.1f}% · ${p.annual_net_rev_mm:,.1f}M · {p.denial_rate_pct * 100:.1f}% denied",
            p.revenue_share_pct * 100.0, tone=_tone(p)) for p in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of net revenue by payer '
            '· value = share + net rev + denial rate · tone = renewal risk</div></div>')


def _metrics_paired_rows(items) -> tuple:
    """Concentration-metrics data for the share-SVG's paired dataset.

    Returns ``(headers, rows, hot_rows)`` for ``ck_paired_block``.
    Mirrors the formatting of the old _metrics_table (now removed):
    percent metrics get pp variance, integer metrics get a comma
    format, others get .1f. ``hot_rows`` marks the worst-variance
    concentration metric — the one most worth a partner's attention.
    """
    headers = ["Metric", "Value", "Benchmark", "Variance", "Interpretation"]
    pct_metrics = {
        "Top Payer Share", "Top 3 Payer Share (CR3)",
        "Top 5 Payer Share (CR5)", "Weighted Denial Rate",
    }
    int_metrics = {"Herfindahl Index (HHI)", "Payer Count"}
    rows: list = []
    bad_scores: list = []
    for m in items:
        if m.metric in pct_metrics:
            val = f"{m.value * 100:.2f}%"
            bench = f"{m.benchmark * 100:.2f}%"
            var = f"{m.variance * 100:+.2f}pp"
        elif m.metric in int_metrics:
            val = f"{m.value:,.0f}"
            bench = f"{m.benchmark:,.0f}"
            var = f"{m.variance:+,.0f}"
        else:
            val = f"{m.value:,.1f}"
            bench = f"{m.benchmark:,.1f}"
            var = f"{m.variance:+,.1f}"
        # "Worse" for concentration = higher variance; for Payer Count
        # = lower variance (more payers is better). Score by signed
        # severity so hot_rows picks the most-concerning row.
        sev = -m.variance if m.metric == "Payer Count" else m.variance
        bad_scores.append(sev)
        rows.append([m.metric, val, bench, var, m.interpretation])
    hot = [bad_scores.index(max(bad_scores))] if bad_scores else []
    return headers, rows, hot


def _payers_table(payers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Payer","left"),("Type","left"),("Net Rev ($M)","right"),("Share","right"),
            ("YoY","right"),("Expiry","center"),("Denial %","right"),("DAR","right"),
            ("Renewal Risk","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(payers):
        rb = panel_alt if i % 2 == 0 else bg
        share_c = neg if p.revenue_share_pct > 0.20 else (warn if p.revenue_share_pct > 0.12 else text_dim)
        yoy_c = pos if p.yoy_delta_pct > 0.03 else (neg if p.yoy_delta_pct < -0.02 else text_dim)
        den_c = neg if p.denial_rate_pct > 0.10 else (warn if p.denial_rate_pct > 0.07 else text_dim)
        risk_c = neg if p.renewal_risk_score >= 65 else (warn if p.renewal_risk_score >= 40 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.payer_name)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(p.payer_type)}""", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${p.annual_net_rev_mm:,.2f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{share_c};font-weight:700">{p.revenue_share_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{yoy_c}">{p.yoy_delta_pct * 100:+.1f}%</td>',
            f'{ck_data_cell(f"""{_html.escape(p.contract_expiry)}""", align="center", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{den_c}">{p.denial_rate_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{p.days_in_ar}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{risk_c};font-weight:600">{p.renewal_risk_score}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.status)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _renewals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Payer","left"),("Expiry","center"),("Annual Rev ($M)","right"),("Type","left"),
            ("Rate Reset","left"),("Exposure","right"),("Priority","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    pri_c = {"critical": neg, "high": warn, "standard": text_dim}
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = pri_c.get(r.priority, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.payer_name)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{_html.escape(r.expiry_quarter)}""", align="center", mono=True)}',
            f'{ck_data_cell(f"""${r.annual_revenue_mm:,.2f}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{_html.escape(r.contract_type)}""", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.rate_reset_clause)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{r.exposure_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.priority)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _denials_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Payer","left"),("Denial %","right"),("Top Reason","left"),
            ("Days to Overturn","right"),("Overturn %","right"),("Write-Off Exposure ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        den_c = neg if d.denials_pct > 0.10 else P["warning"]
        ov_c = pos if d.overturn_success_pct > 0.70 else text_dim
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.payer_name)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{den_c};font-weight:600">{d.denials_pct * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.top_denial_reason)}</td>',
            f'{ck_data_cell(f"""{d.days_to_overturn}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ov_c}">{d.overturn_success_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${d.write_off_exposure_mm:,.2f}""", align="right", mono=True, tone="neg", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _oon_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Service Line","left"),("OON Volume %","right"),("Avg Coll Rate","right"),
            ("Balance-Bill Risk ($M)","right"),("NSA Impact","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        oon_c = neg if o.oon_volume_pct > 0.20 else (warn if o.oon_volume_pct > 0.10 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(o.service_line)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{oon_c};font-weight:600">{o.oon_volume_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""{o.avg_collection_rate * 100:.1f}%""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">${o.balance_bill_risk_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(o.no_surprises_act_impact)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _payer_share_svg(payers) -> str:
    if not payers: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 80
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    sorted_p = sorted(payers, key=lambda p: p.revenue_share_pct, reverse=True)
    max_v = sorted_p[0].revenue_share_pct if sorted_p else 0.01
    bg = P["panel"]; acc = P["accent"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(sorted_p)
    bar_w = (inner_w - (n - 1) * 4) / n
    bars = []
    for i, p in enumerate(sorted_p):
        x = pad_l + i * (bar_w + 4)
        bh = p.revenue_share_pct / max_v * inner_h
        y = (h - pad_b) - bh
        color = neg if p.revenue_share_pct > 0.20 else acc
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{text_dim}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">{p.revenue_share_pct * 100:.1f}%</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="8" text-anchor="end" font-family="JetBrains Mono,monospace" transform="rotate(-35 {x + bar_w / 2} {h - pad_b + 14})">{_html.escape(p.payer_name[:22])}</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Payer Revenue Share (red = >20% single-payer concentration risk)</text></svg>')


def render_payer_concentration(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    revenue = _f("revenue", 250.0)
    top_payer = _f("top_payer", 0.32)

    from rcm_mc.data_public.payer_concentration import compute_payer_concentration
    r = compute_payer_concentration(revenue_mm=revenue, top_payer_pct=top_payer)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    risk_c = neg if r.concentration_risk_label == "concentrated" else (P["warning"] if r.concentration_risk_label == "moderate" else pos)

    kpi_strip = (
        ck_kpi_block("Revenue", f"${r.total_revenue_mm:,.0f}M", "", "") +
        ck_kpi_block("Top Payer", f"{r.top_payer_share_pct * 100:.1f}%", "", "") +
        ck_kpi_block("CR3", f"{r.top3_share_pct * 100:.1f}%", "", "") +
        ck_kpi_block("CR5", f"{r.top5_share_pct * 100:.1f}%", "", "") +
        ck_kpi_block("HHI", f"{r.hhi_index:,}", "", "") +
        ck_kpi_block("Commercial", f"{r.commercial_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Risk Profile", r.concentration_risk_label.upper(), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    svg = _payer_share_svg(r.payers)
    payers_tbl = _payers_table(r.payers)
    payers_chart = _payers_chart(r.payers)
    payers_scatter = _payers_scatter(r.payers)
    renewals_tbl = _renewals_table(r.renewals)
    denials_tbl = _denials_table(r.denials)
    oon_tbl = _oon_table(r.oon_exposure)

    # Signature paired viz+dataset: the payer-share SVG (overall
    # distribution) on the left, the concentration metrics vs
    # benchmark on the right, one outer rule. The SVG shows how
    # concentrated the payer mix is; the table reads the numbers
    # against industry benchmarks. The worst-variance row is
    # highlighted via hot_rows.
    share_viz = (
        f'<div style="font-size:9px;color:{P["text_dim"]};'
        f'font-family:JetBrains Mono,monospace;letter-spacing:0.1em;'
        f'text-transform:uppercase;font-weight:700;margin-bottom:8px;">'
        'Payer revenue share distribution</div>'
        f'{svg}'
    )
    met_headers, met_rows, met_hot = _metrics_paired_rows(r.concentration_metrics)
    concentration_paired = ck_paired_block(
        share_viz,
        data_label="Concentration metrics vs benchmark",
        data_source="data_public/payer_concentration.py",
        headers=met_headers,
        rows=met_rows,
        hot_rows=met_hot,
    )

    form = f"""
<form method="GET" action="/payer-concentration" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)<input name="revenue" value="{revenue}" type="number" step="25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <label style="font-size:11px;color:{text_dim}">Top Payer Share<input name="top_payer" value="{top_payer}" type="number" step="0.02" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    denial_exposure = sum(d.write_off_exposure_mm for d in r.denials)
    total_oon_risk = sum(o.balance_bill_risk_mm for o in r.oon_exposure)

    page_title = ck_page_title(
        "Payer Concentration Tracker",
        eyebrow="PAYER CONCENTRATION",
        meta=f"""CR1/CR3/CR5 · HHI · renewal schedule · denials · NSA OON exposure — {r.corpus_deal_count:,} corpus deals""",
    )
    
    value_anchor = ck_value_anchor(
        "Payer Concentration",
        f"{r.top_payer_share_pct * 100:.1f}% top-payer share",
        delta=f"CR3 {r.top3_share_pct * 100:.0f}% · CR5 {r.top5_share_pct * 100:.0f}% · ${r.total_revenue_mm:,.0f}M revenue",
        tone="negative" if r.top_payer_share_pct >= 0.40 else "warning" if r.top_payer_share_pct >= 0.25 else "teal",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  {concentration_paired}
  <div style="{cell}"><div style="{h3}">Payer Roster — Share, YoY, Contract Expiry, Denials, Renewal Risk</div>{payers_chart}{payers_scatter}{payers_tbl}</div>
  <div style="{cell}"><div style="{h3}">Contract Renewal Calendar — Priority &amp; Exposure</div>{renewals_tbl}</div>
  <div style="{cell}"><div style="{h3}">Payer-Level Denials Analysis — Write-Off Exposure</div>{denials_tbl}</div>
  <div style="{cell}"><div style="{h3}">Out-of-Network Exposure by Service Line — No Surprises Act</div>{oon_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {risk_c};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Payer Risk Thesis:</strong> Concentration profile = <strong style="color:{risk_c}">{_html.escape(r.concentration_risk_label)}</strong>.
    Top payer holds {r.top_payer_share_pct * 100:.1f}% of revenue; top 3 hold {r.top3_share_pct * 100:.1f}%; HHI {r.hhi_index:,}.
    ${denial_exposure:,.2f}M in write-off exposure from denials (${sum(d.write_off_exposure_mm for d in r.denials[:3]):,.2f}M concentrated in top 3 payers).
    ${total_oon_risk:,.2f}M balance-bill risk under No Surprises Act. Material contract renewals in the next 4 quarters demand rate-reset
    strategy and in-parallel 2nd-payer development to reduce CR1 before exit.
  </div>
</div>"""

    return chartis_shell(body, "Payer Concentration", active_nav="/payer-concentration",
        editorial_intro={
            "eyebrow": "PAYER CONCENTRATION",
            "headline": "What the payer concentration page reveals on this deal.",
            "italic_word": "reveals",
        })
