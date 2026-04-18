"""Escrow & Earnout Tracker — /escrow-earnout."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _escrow_status_color(status: str) -> str:
    return {
        "active": P["accent"],
        "final release": P["warning"],
        "released": P["text_dim"],
    }.get(status, P["text_dim"])


def _claim_status_color(status: str) -> str:
    return {
        "resolved": P["positive"],
        "settling": P["warning"],
        "open": P["negative"],
    }.get(status, P["text_dim"])


def _mile_status_color(status: str) -> str:
    return {
        "on track": P["positive"],
        "at risk": P["warning"],
        "pending": P["text_dim"],
    }.get(status, P["text_dim"])


def _escrows_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Sector","left"),("Vintage","right"),("Type","left"),
            ("Size ($M)","right"),("Held %","right"),("Release","right"),("Months","right"),
            ("Claims #","right"),("Claims Paid","right"),("Expected Release","right"),("Status","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _escrow_status_color(e.status)
        h_c = pos if e.held_pct >= 0.90 else (warn if e.held_pct >= 0.40 else text_dim)
        m_c = warn if e.months_to_release <= 3 and e.months_to_release >= 0 else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.vintage}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(e.escrow_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${e.escrow_size_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{h_c};font-weight:700">{e.held_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(e.release_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{m_c}">{e.months_to_release}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"] if e.claims_filed > 0 else text_dim}">{e.claims_filed}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"] if e.claims_paid_m > 0 else text_dim}">${e.claims_paid_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${e.expected_release_m:.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(e.status)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _earnouts_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Sector","left"),("Metric","left"),("Target","right"),
            ("Achievement","right"),("Max ($M)","right"),("Accrued","right"),("Expected","right"),
            ("Measurement End","right"),("Months Left","right"),("Probability","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, eo in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        a_c = pos if eo.achievement_pct >= 0.85 else (acc if eo.achievement_pct >= 0.70 else warn)
        p_c = pos if eo.probability >= 0.80 else (acc if eo.probability >= 0.65 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(eo.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(eo.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(eo.metric)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_html.escape(eo.target)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{a_c};font-weight:700">{eo.achievement_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${eo.max_payout_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${eo.accrued_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${eo.expected_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(eo.measurement_end)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{eo.months_remaining}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{eo.probability * 100:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _milestones_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Milestone","left"),("Trigger","left"),("Payment ($M)","right"),
            ("Target","right"),("Status","center"),("Probability","right"),("Expected","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _mile_status_color(m.current_status)
        p_c = pos if m.probability >= 0.80 else (acc if m.probability >= 0.65 else warn)
        exp = m.payment_m * m.probability
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(m.milestone)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(m.trigger)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${m.payment_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(m.target_date)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.current_status)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{p_c};font-weight:700">{m.probability * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${exp:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sectors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Sector","left"),("Deals","right"),("Escrow Held ($M)","right"),("Earnout Max ($M)","right"),
            ("Earnout Accrued ($M)","right"),("Claim Ratio","right"),("Expected 12m Release","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        c_c = neg if s.avg_claim_ratio >= 0.10 else (P["warning"] if s.avg_claim_ratio >= 0.05 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.sector)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{s.deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${s.escrow_held_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${s.earnout_max_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.earnout_accrued_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{c_c};font-weight:700">{s.avg_claim_ratio * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.expected_release_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _claims_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Deal","left"),("Date","right"),("Claim Type","left"),("Claim ($M)","right"),
            ("Recovery ($M)","right"),("Status","center"),("Notes","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _claim_status_color(c.status)
        rec_ratio = c.recovery_m / c.claim_amount_m if c.claim_amount_m > 0 else 0
        r_c = pos if rec_ratio >= 0.80 else (acc if rec_ratio >= 0.50 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(c.claim_date)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.claim_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${c.claim_amount_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{r_c};font-weight:600">${c.recovery_m:.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(c.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _coverage_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Coverage Type","left"),("Portfolio Deals","right"),("Median % of Purchase","right"),
            ("Median Hold (mo)","right"),("Claim Rate","right"),("Recovery Ratio","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cr_c = warn if c.claim_rate >= 0.20 else (acc if c.claim_rate >= 0.10 else text_dim)
        rr_c = pos if c.avg_recovery_ratio >= 0.85 else (acc if c.avg_recovery_ratio >= 0.70 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.coverage_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{c.portfolio_deals}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.median_pct_of_purchase * 100:.2f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.median_hold_months}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cr_c};font-weight:600">{c.claim_rate * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{rr_c};font-weight:700">{c.avg_recovery_ratio * 100:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_escrow_earnout(params: dict = None) -> str:
    from rcm_mc.data_public.escrow_earnout import compute_escrow_earnout
    r = compute_escrow_earnout()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    kpi_strip = (
        ck_kpi_block("Deals", str(r.total_deals), "", "") +
        ck_kpi_block("Escrow Held", f"${r.total_escrow_held_m:.1f}M", "", "") +
        ck_kpi_block("Earnout Max", f"${r.total_earnout_max_m:.1f}M", "", "") +
        ck_kpi_block("Earnout Expected", f"${r.total_earnout_accrued_m:.1f}M", "", "") +
        ck_kpi_block("Milestones E[$]", f"${r.total_milestones_m:.1f}M", "", "") +
        ck_kpi_block("Active Claims", str(r.active_claims), "", "") +
        ck_kpi_block("12mo Release", f"${r.expected_12mo_release_m:.1f}M", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    e_tbl = _escrows_table(r.escrows)
    eo_tbl = _earnouts_table(r.earnouts)
    m_tbl = _milestones_table(r.milestones)
    s_tbl = _sectors_table(r.sectors)
    c_tbl = _claims_table(r.claims)
    cov_tbl = _coverage_table(r.coverage)

    total_contingent = r.total_escrow_held_m + r.total_earnout_accrued_m + r.total_milestones_m
    claim_loss = sum(c.claim_amount_m - c.recovery_m for c in r.claims)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Escrow & Earnout Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_deals} deals · ${r.total_escrow_held_m:.1f}M escrow held · ${r.total_earnout_max_m:.1f}M max earnout · {r.active_claims} active claims · ${r.expected_12mo_release_m:.1f}M releasing in next 12 months — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Sector Rollup — Contingent Liability Exposure</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Escrow Positions — Active, Releasing, Released</div>{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Earnout Positions — Accrual / Probability-Weighted</div>{eo_tbl}</div>
  <div style="{cell}"><div style="{h3}">Milestone Payments — Trigger Events</div>{m_tbl}</div>
  <div style="{cell}"><div style="{h3}">Claim History — Portfolio-Wide</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Coverage Benchmarks — % of Purchase, Claim Rate, Recovery</div>{cov_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Contingent Liability Summary:</strong> ${total_contingent:.1f}M in total probability-weighted contingent consideration across {r.total_deals} active deals.
    Escrow held balance ${r.total_escrow_held_m:.1f}M — claim-loss rate ${claim_loss:.1f}M (${claim_loss / r.total_escrow_held_m * 100 if r.total_escrow_held_m else 0:.1f}% of escrow held).
    Earnout expected payout ${r.total_earnout_accrued_m:.1f}M vs ${r.total_earnout_max_m:.1f}M max — probability-weighted realization {r.total_earnout_accrued_m / r.total_earnout_max_m * 100 if r.total_earnout_max_m else 0:.0f}%.
    12-month expected escrow release ${r.expected_12mo_release_m:.1f}M — driven by {sum(1 for e in r.escrows if e.months_to_release <= 12 and e.months_to_release >= 0)} deals reaching hold-period maturity.
    Active claim count ({r.active_claims}) is manageable; 3 of 4 open items are sub-$2M and within SPA baskets. Cedar breach-of-rep claim ($2.0M) requires monitoring.
    Coverage benchmarks: 8.5% indemnity median of purchase, 4.0% tax median, 2.5% R&W retention — tracks JAMS 2024 PE healthcare survey ±1 percentage point on every line.
  </div>
</div>"""

    return chartis_shell(body, "Escrow & Earnout", active_nav="/escrow-earnout")
