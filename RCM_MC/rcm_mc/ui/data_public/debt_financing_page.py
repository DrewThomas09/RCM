"""Debt Financing / LBO Commitment Tracker — /debt-financing."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _synd_status_color(status: str) -> str:
    return {
        "closed": P["positive"],
        "final allocation": P["accent"],
        "clearing": P["warning"],
        "active marketing": P["warning"],
    }.get(status, P["text_dim"])


def _tier_color(tier: str) -> str:
    return {
        "tier 1": P["positive"],
        "syndication": P["accent"],
        "tier 2": P["warning"],
    }.get(tier, P["text_dim"])


def _facilities_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("Tranche","left"),("Size ($M)","right"),
            ("Lead","left"),("SOFR+","right"),("Floor","right"),("OID","right"),
            ("Tenor","center"),("Call Protection","left"),("Cov-Lite","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cl_c = pos if f.covenant_lite else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(f.deal)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(f.tranche)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${f.size_m:.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.lead_arranger)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{f.sofr_spread_bps}bps</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.floor_bps}bps</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.oid_pts:.2f}pt</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(f.tenor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.call_protection)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{cl_c};font-weight:700">{"YES" if f.covenant_lite else "NO"}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _syndication_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Package ($M)","right"),("Committed ($M)","right"),("Allocation ($M)","right"),
            ("Accounts","right"),("Oversubscribed","right"),("Launch","right"),("Target Close","right"),
            ("Status","center"),("Flex Used (bps)","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _synd_status_color(s.status)
        o_c = pos if s.oversubscribed_x >= 1.5 else (acc if s.oversubscribed_x >= 1.2 else text_dim)
        fl_c = P["negative"] if s.flex_used_bps >= 25 else (warn if s.flex_used_bps > 0 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(s.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">${s.total_package_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${s.committed_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${s.allocation_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{s.accounts_participating}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{o_c};font-weight:700">{s.oversubscribed_x:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.launch_date)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_html.escape(s.target_close)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(s.status)}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{fl_c};font-weight:700">{s.flex_used_bps}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pricing_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Sector","left"),("Segment","left"),("1L SOFR+","right"),("2L SOFR+","right"),
            ("Median Leverage","right"),("Median Int. Cov","right"),("Clearing Rate","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cl_c = pos if p.clearing_rate_pct >= 95 else (acc if p.clearing_rate_pct >= 93 else warn)
        l_c = pos if p.median_leverage <= 5.5 else (acc if p.median_leverage <= 5.8 else warn)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.segment)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{p.median_first_lien_spread}bps</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{p.median_second_lien_spread}bps</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{l_c};font-weight:700">{p.median_leverage:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.median_interest_cov:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{cl_c};font-weight:700">{p.clearing_rate_pct:.1f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _covenants_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; warn = P["warning"]
    cols = [("Deal","left"),("Cov-Lite","center"),("Max Leverage","right"),("At Close","right"),
            ("Headroom","right"),("Int. Cov","right"),("Capex Flex","right"),("RP Basket","right"),("Incr Facility","right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        h_c = pos if c.headroom_pct >= 0.20 else (acc if c.headroom_pct >= 0.15 else warn)
        cl_c = pos if c.cov_lite else warn
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(c.deal)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{cl_c};font-weight:700">{"YES" if c.cov_lite else "NO"}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.max_leverage_covenant:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{c.leverage_at_close:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{h_c};font-weight:700">{c.headroom_pct * 100:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{c.interest_cov_covenant:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.capex_flex_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${c.restricted_payment_basket_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:600">${c.incremental_facility_m:.1f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _flex_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Spread Flex (bps)","right"),("OID Flex (pt)","right"),
            ("Caps Effective","left"),("MFN","center"),("Structure Flex","left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        mfn_c = pos if f.mfn_protection else P["warning"]
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(f.deal)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{f.flex_spread_bps}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.flex_oid_pts:.2f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(f.flex_caps_effective)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{mfn_c};font-weight:700">{"YES" if f.mfn_protection else "NO"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(f.structure_flex)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _lenders_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Lender","left"),("Commitments ($M)","right"),("Deals","right"),("Avg Hold ($M)","right"),
            ("Sectors Active","left"),("Tier","center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, l in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = _tier_color(l.relationship_tier)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(l.lender)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${l.commitments_m:.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{l.deals_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${l.avg_hold_m:.1f}M</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(l.sectors_active)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(l.relationship_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_debt_financing(params: dict = None) -> str:
    from rcm_mc.data_public.debt_financing import compute_debt_financing
    r = compute_debt_financing()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]; warn = P["warning"]

    kpi_strip = (
        ck_kpi_block("Active Financings", str(r.total_financings), "", "") +
        ck_kpi_block("Total Package", f"${r.total_package_m:,.1f}M", "", "") +
        ck_kpi_block("Committed", f"${r.total_committed_m:,.1f}M", "", "") +
        ck_kpi_block("Avg SOFR+", f"{r.avg_sofr_spread}", "bps", "") +
        ck_kpi_block("Cov-Lite %", f"{r.cov_lite_pct * 100:.1f}%", "", "") +
        ck_kpi_block("Avg Leverage", f"{r.avg_leverage:.2f}x", "", "") +
        ck_kpi_block("Facilities", str(len(r.facilities)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    f_tbl = _facilities_table(r.facilities)
    s_tbl = _syndication_table(r.syndications)
    p_tbl = _pricing_table(r.pricing)
    c_tbl = _covenants_table(r.covenants)
    fl_tbl = _flex_table(r.flex)
    l_tbl = _lenders_table(r.lenders)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    clearing_avg = sum(p.clearing_rate_pct for p in r.pricing) / len(r.pricing) if r.pricing else 0
    cov_lite_cnt = sum(1 for f in r.facilities if f.covenant_lite)
    active_marketing = sum(1 for s in r.syndications if s.status in ("clearing", "active marketing", "final allocation"))

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Debt Financing / LBO Commitment Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_financings} active financings · ${r.total_package_m:,.1f}M total package · SOFR+{r.avg_sofr_spread}bps average · {cov_lite_cnt} of {len(r.facilities)} facilities cov-lite ({r.cov_lite_pct * 100:.1f}%) · {active_marketing} in active syndication — {r.corpus_deal_count:,} corpus deals</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Syndication Status — Active Book</div>{s_tbl}</div>
  <div style="{cell}"><div style="{h3}">Facility Detail — Tranches, Pricing, Tenor</div>{f_tbl}</div>
  <div style="{cell}"><div style="{h3}">Covenant Package — Leverage, Headroom, Baskets</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Flex Terms — Pricing Flex & Structure Flex</div>{fl_tbl}</div>
  <div style="{cell}"><div style="{h3}">Sector Clearing Benchmarks — SOFR+ Spread, Leverage, Interest Coverage</div>{p_tbl}</div>
  <div style="{cell}"><div style="{h3}">Lender Book — Relationships & Concentration</div>{l_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Debt Market Summary:</strong> {r.total_financings} active LBO financings sum ${r.total_package_m:,.1f}M in package / ${r.total_committed_m:,.1f}M committed — {r.total_committed_m / r.total_package_m * 100 if r.total_package_m else 0:.1f}% commitment coverage.
    Average pricing SOFR+{r.avg_sofr_spread}bps tracks Lipper Leveraged Loan Index ±25bps; {r.cov_lite_pct * 100:.1f}% cov-lite continues to dominate sponsored middle-market.
    Average leverage at close {r.avg_leverage:.2f}x EBITDA with 16.8% headroom to maintenance covenants — room for modest underperformance without trip.
    {active_marketing} of {len(r.syndications)} deals still in active syndication; {sum(1 for s in r.syndications if s.flex_used_bps > 0)} have triggered pricing flex (avg 37bps) — concentrated in fertility/infusion where market remains choppier.
    Clearing rates average {clearing_avg:.1f}% of launch terms; sector dispersion 92-96.5% with dental DSO (96.0%) and derma (96.5%) clearing cleanest.
    Direct-lender penetration remains elevated (55% of facilities by count) with Apollo, Ares, BXCI, Blue Owl, Golub driving tier-1 hold levels.
  </div>
</div>"""

    return chartis_shell(body, "Debt Financing", active_nav="/debt-financing")
