"""Payer Concentration Tracker — /payer-concentration."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _payers_table(payers) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]; acc = P["accent"]
    cols = [("Payer","left"),("Type","left"),("Net Rev ($M)","right"),("Share","right"),
            ("YoY","right"),("Expiry","center"),("Denial %","right"),("DAR","right"),
            ("Renewal Risk","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(payers):
        rb = panel_alt if i % 2 == 0 else bg
        share_c = neg if p.revenue_share_pct > 0.20 else (warn if p.revenue_share_pct > 0.12 else text_dim)
        yoy_c = pos if p.yoy_delta_pct > 0.03 else (neg if p.yoy_delta_pct < -0.02 else text_dim)
        den_c = neg if p.denial_rate_pct > 0.10 else (warn if p.denial_rate_pct > 0.07 else text_dim)
        risk_c = neg if p.renewal_risk_score >= 65 else (warn if p.renewal_risk_score >= 40 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(p.payer_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(p.payer_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.annual_net_rev_mm:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{share_c};font-weight:700">{p.revenue_share_pct * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{yoy_c}">{p.yoy_delta_pct * 100:+.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{_html.escape(p.contract_expiry)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{den_c}">{p.denial_rate_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.days_in_ar}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{risk_c};font-weight:600">{p.renewal_risk_score}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(p.status)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _metrics_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Metric","left"),("Value","right"),("Benchmark","right"),("Variance","right"),("Interpretation","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        is_pct = m.metric in ("Top Payer Share", "Top 3 Payer Share (CR3)", "Top 5 Payer Share (CR5)",
                              "Weighted Denial Rate")
        val_disp = f"{m.value * 100:.2f}%" if is_pct else f"{m.value:,.0f}" if m.metric in ("Herfindahl Index (HHI)", "Payer Count") else f"{m.value:,.1f}"
        bench_disp = f"{m.benchmark * 100:.2f}%" if is_pct else f"{m.benchmark:,.0f}" if m.metric in ("Herfindahl Index (HHI)", "Payer Count") else f"{m.benchmark:,.1f}"
        var_disp = f"{m.variance * 100:+.2f}pp" if is_pct else f"{m.variance:+,.0f}" if m.metric in ("Herfindahl Index (HHI)", "Payer Count") else f"{m.variance:+,.1f}"
        # Worse-than-bench = higher (for concentration metrics) except Payer Count where higher is better
        if m.metric == "Payer Count":
            var_c = pos if m.variance > 0 else neg
        else:
            var_c = neg if m.variance > 0 else pos
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{val_disp}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{bench_disp}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{var_c};font-weight:600">{var_disp}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.interpretation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _renewals_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Payer","left"),("Expiry","center"),("Annual Rev ($M)","right"),("Type","left"),
            ("Rate Reset","left"),("Exposure","right"),("Priority","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    pri_c = {"critical": neg, "high": warn, "standard": text_dim}
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        pc = pri_c.get(r.priority, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.payer_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(r.expiry_quarter)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${r.annual_revenue_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(r.contract_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.rate_reset_clause)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">{r.exposure_pct * 100:.1f}%</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{pc};border:1px solid {pc};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.priority)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _denials_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Payer","left"),("Denial %","right"),("Top Reason","left"),
            ("Days to Overturn","right"),("Overturn %","right"),("Write-Off Exposure ($M)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        den_c = neg if d.denials_pct > 0.10 else P["warning"]
        ov_c = pos if d.overturn_success_pct > 0.70 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(d.payer_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{den_c};font-weight:600">{d.denials_pct * 100:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.top_denial_reason)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{d.days_to_overturn}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{ov_c}">{d.overturn_success_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:600">${d.write_off_exposure_mm:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _oon_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; neg = P["negative"]; warn = P["warning"]
    cols = [("Service Line","left"),("OON Volume %","right"),("Avg Coll Rate","right"),
            ("Balance-Bill Risk ($M)","right"),("NSA Impact","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        oon_c = neg if o.oon_volume_pct > 0.20 else (warn if o.oon_volume_pct > 0.10 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(o.service_line)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{oon_c};font-weight:600">{o.oon_volume_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{o.avg_collection_rate * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{warn}">${o.balance_bill_risk_mm:,.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(o.no_surprises_act_impact)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


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
    metrics_tbl = _metrics_table(r.concentration_metrics)
    renewals_tbl = _renewals_table(r.renewals)
    denials_tbl = _denials_table(r.denials)
    oon_tbl = _oon_table(r.oon_exposure)

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

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Payer Concentration Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">CR1/CR3/CR5 · HHI · renewal schedule · denials · NSA OON exposure — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  {form}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Payer Revenue Share Distribution</div>{svg}</div>
  <div style="{cell}"><div style="{h3}">Payer Roster — Share, YoY, Contract Expiry, Denials, Renewal Risk</div>{payers_tbl}</div>
  <div style="{cell}"><div style="{h3}">Concentration Metrics vs Benchmark</div>{metrics_tbl}</div>
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

    return chartis_shell(body, "Payer Concentration", active_nav="/payer-concentration")
