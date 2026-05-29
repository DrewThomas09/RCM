"""CMS Innovation Models / APM Tracker — /cms-apm."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_data_cell, ck_page_title, ck_bar_row, ck_value_anchor, ck_source_purpose, ck_illustrative_note


def _programs_chart(items) -> str:
    """Lead chart — APM programs ranked by total payments (tone by status)."""
    def _tone(st):
        s=(st or "").lower()
        if "sunset" in s or "expir" in s: return "warning"
        if "permanent" in s or "active" in s: return "positive"
        return "teal"
    total = sum(p.total_payments_b for p in items) or 1.0
    rows=[ck_bar_row(p.program, f"${p.total_payments_b:,.1f}B",
          p.total_payments_b/total*100.0, tone=_tone(p.status))
          for p in sorted(items, key=lambda p: p.total_payments_b, reverse=True)]
    return ('<div style="margin-bottom:14px">'+"".join(rows)+
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of total APM payments '
            '\u00b7 value = payments ($B) \u00b7 tone = program status</div></div>')



def _status_color(s: str) -> str:
    return {
        "permanent": P["positive"],
        "active": P["accent"],
        "new / ramping": P["warning"],
        "sunset scheduled": P["warning"],
        "sunset": P["negative"],
        "pilot": P["accent"],
        "retired": P["text_dim"],
    }.get(s, P["text_dim"])


def _impact_color(i: str) -> str:
    s = i.lower()
    if "sunset" in s or "cut" in s or "expansion" in s: return P["warning"]
    if "launch" in s or "new" in s: return P["accent"]
    return P["text_dim"]


def _programs_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Program","left"),("Type","left"),("Lives (M)","right"),("Participants","right"),
            ("Payments ($B)","right"),("Risk Structure","left"),("Savings %","right"),
            ("Through","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(p.status)
        sv_c = pos if p.savings_rate_pct >= 3.0 else (acc if p.savings_rate_pct >= 1.5 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.program)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.program_type)}</td>',
            f'{ck_data_cell(f"""{p.lives_covered_m:.2f}""", align="right", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{p.participants:,}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${p.total_payments_b:.1f}B""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.risk_structure)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sv_c};font-weight:700">{p.savings_rate_pct:.2f}%</td>',
            f'{ck_data_cell(f"""{_html.escape(p.active_through)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(p.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exposures_chart(items) -> str:
    """Summary chart — deals ranked by APM revenue exposure (tone by rev share)."""
    def _tone(e):
        if e.apm_share_of_rev_pct >= 0.15: return "warning"
        if e.apm_share_of_rev_pct >= 0.08: return "teal"
        return "navy"
    top = sorted(items, key=lambda e: e.apm_revenue_m, reverse=True)
    total = sum(e.apm_revenue_m for e in top) or 1.0
    rows = [ck_bar_row(f"{e.deal} · {e.sector}",
            f"${e.apm_revenue_m:.1f}M ({e.apm_share_of_rev_pct * 100:.0f}%)",
            e.apm_revenue_m / total * 100.0, tone=_tone(e)) for e in top]
    return ('<div style="margin-bottom:14px">' + "".join(rows) +
            '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
            'font-family:JetBrains Mono,monospace">Bar = share of portfolio APM revenue '
            '· value = APM revenue ($M) + rev share · tone = APM dependence</div></div>')


def _exposures_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal","left"),("Sector","left"),("APM Programs","left"),("Lives (K)","right"),
            ("APM Revenue ($M)","right"),("APM Share of Revenue","right"),("Net Savings ($M)","right"),("Quality Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sh_c = pos if e.apm_share_of_rev_pct >= 0.15 else (acc if e.apm_share_of_rev_pct >= 0.08 else text_dim)
        q_c = pos if e.quality_score >= 87 else (acc if e.quality_score >= 85 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(e.deal)}""", mono=True, weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.sector)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(e.apm_programs)}</td>',
            f'{ck_data_cell(f"""{e.lives_covered_k:.1f}K""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${e.apm_revenue_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sh_c};font-weight:700">{e.apm_share_of_rev_pct * 100:.1f}%</td>',
            f'{ck_data_cell(f"""${e.net_savings_m:.1f}M""", align="right", mono=True, tone="acc")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{q_c};font-weight:700">{e.quality_score:.1f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _trends_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Year","right"),("Program","left"),("Participants","right"),("Spend ($B)","right"),
            ("Savings ($B)","right"),("Savings %","right"),("Quality Score","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{t.year}""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(t.program)}</td>',
            f'{ck_data_cell(f"""{t.participants:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${t.gross_spend_b:.1f}B""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${t.gross_savings_b:.2f}B""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{t.savings_rate_pct:.2f}%""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""{t.quality_score:.1f}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _risk_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Structure","left"),("Upside Share","right"),("Downside Share","right"),("Participants","right"),
            ("Typical Savings %","right"),("Suitability","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.structure)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{r.upside_share_pct:.0f}%""", align="right", mono=True, tone="pos", weight=700)}',
            f'{ck_data_cell(f"""{r.downside_share_pct:.0f}%""", align="right", mono=True)}',
            f'{ck_data_cell(f"""{r.typical_participants:,}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{r.typical_savings_rate_pct:.2f}%""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.suitability)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _calendar_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Event","left"),("Date","right"),("Impact","left"),("Affected Programs","left"),("Portfolio Exposure ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        i_c = _impact_color(c.impact)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.event)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(c.event_date)}""", align="right", mono=True, tone="acc", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{i_c};max-width:340px">{_html.escape(c.impact)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(c.affected_programs)}</td>',
            f'{ck_data_cell(f"""${c.portfolio_exposure_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _payer_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Track","left"),("Programs","right"),("Lives (M)","right"),("Commercial Spread (bps)","right"),
            ("Market Pen %","right"),("Sponsor Activity","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sp_c = pos if p.commercial_spread_bps <= -400 else (acc if p.commercial_spread_bps <= -250 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(p.commercial_ma_track)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{p.programs}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""{p.lives_m:.1f}""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sp_c};font-weight:700">{p.commercial_spread_bps}</td>',
            f'{ck_data_cell(f"""{p.market_penetration_pct:.1f}%""", align="right", mono=True)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(p.sponsor_activity)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _colorado_apm_section() -> str:
    """REAL Colorado APM adoption from CIVHC (public) — %APM / %FFS by payer ×
    year. LIVE-labeled and distinct from the illustrative national overlay
    below. State-specific caveat included; missing (Unknown payer) shows '—'."""
    try:
        from rcm_mc.data import payer_data as _pd
        df = _pd.apm_adoption_by_payer("Total Medical Spending")
    except Exception:
        return ""
    if df is None or not len(df):
        return ""
    hdr = ck_source_purpose(
        purpose=("Gauge value-based-care penetration in Colorado — the share "
                 "of total medical spend flowing through alternative payment "
                 "models vs fee-for-service, by payer and year."),
        universe="cms", confidence="derived",
        source="CIVHC / CO APCD — APM public dataset (FY2026), Total Medical Spending",
        next_action="Compare a target's payer mix to Colorado's APM trajectory")
    yrs = sorted(df["year"].dropna().astype(int).unique().tolist())
    payers = [p for p in df["payer"].unique().tolist()]
    # pivot %APM by payer × year
    head = "".join(f'<th style="padding:4px 10px;text-align:right">{y}</th>' for y in yrs)
    rows = []
    for p in payers:
        cells = []
        for y in yrs:
            m = df[(df["payer"] == p) & (df["year"].astype(int) == y)]
            v = m["pct_apm"].iloc[0] if len(m) else None
            cells.append(f'<td style="padding:4px 10px;text-align:right;'
                         f'font-variant-numeric:tabular-nums">'
                         f'{("%.1f%%" % (v*100)) if (v is not None and v==v) else "—"}</td>')
        rows.append(f'<tr><td style="padding:4px 10px">{_html.escape(str(p))}</td>'
                    + "".join(cells) + "</tr>")
    table = (
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr style="border-bottom:1px solid {P["border"]};color:{P["text_dim"]}">'
        f'<th style="padding:4px 10px;text-align:left">Payer (% of medical spend in APMs)</th>'
        f'{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>')
    # 2026-05-28 batch 32 · Tier-4 trope removal — strip 3px accent.
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:2px;padding:14px 16px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:8px">'
        f'Colorado APM Adoption · LIVE (CIVHC)</div>{hdr}{table}'
        f'<p style="font-size:11px;color:{P["text_dim"]};margin:8px 0 0">'
        f'Real all-payer market data for <b>Colorado</b> (integrated systems '
        f'included). <b>Colorado CIVHC APM data is state-specific and should '
        f'not be generalized nationally</b>; it is market-level, not '
        f'provider-specific.</p></div>')


def _mssp_landscape_section() -> str:
    """REAL national MSSP ACO participation landscape from CMS (public) — ACO
    counts by risk track + top ACOs by participant orgs. LIVE; a participation
    directory, NOT savings/performance and not provider-specific."""
    try:
        from rcm_mc.data import mssp_aco_data as _m
        s = _m.mssp_summary()
        tracks = _m.mssp_track_breakdown()
        top = _m.top_acos_by_participants(10)
    except Exception:
        return ""
    if not s.get("acos"):
        return ""
    hdr = ck_source_purpose(
        purpose=("See the national Medicare Shared Savings Program landscape — "
                 "how many ACOs, their risk tracks, and the largest by "
                 "participant organizations — as value-based-care context."),
        universe="cms", confidence="derived",
        source=f"CMS data.cms.gov · MSSP ACO Participants (PY2026, snapshot {s.get('snapshot_date','')})",
        next_action="Search a provider org in the MSSP directory")
    track_rows = "".join(
        f'<tr><td style="padding:3px 10px">{_html.escape(t["track"])}</td>'
        f'<td style="padding:3px 10px;text-align:right;font-variant-numeric:tabular-nums">{t["acos"]:,}</td></tr>'
        for t in tracks)
    top_rows = "".join(
        f'<tr><td style="padding:3px 10px">{_html.escape(str(a["aco_name"])[:38])}</td>'
        f'<td style="padding:3px 10px;text-align:right;font-variant-numeric:tabular-nums">{a["participants"]:,}</td></tr>'
        for a in top)
    # 2026-05-28 batch 32 · Tier-4 trope removal — strip 3px accent.
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:2px;padding:14px 16px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:8px">'
        f'National MSSP ACO Landscape · LIVE (CMS)</div>{hdr}'
        f'<p style="font-size:12px;color:{P["text_dim"]};margin:4px 0 8px">'
        f'<b style="color:{P["text"]}">{s["acos"]:,}</b> MSSP ACOs · '
        f'<b style="color:{P["text"]}">{s["enhanced_track_acos"]:,}</b> on the '
        f'ENHANCED (full-risk) track · {s["high_revenue_acos"]:,} high-revenue · '
        f'{s["participant_orgs"]:,} participant organizations.</p>'
        f'<div style="display:flex;gap:18px;flex-wrap:wrap">'
        f'<div style="flex:1;min-width:220px"><div style="font-size:10px;'
        f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:4px">ACOs by risk track</div>'
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px"><tbody>{track_rows}</tbody></table></div>'
        f'<div style="flex:1.3;min-width:280px"><div style="font-size:10px;'
        f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:4px">Largest ACOs (by participant orgs)</div>'
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px"><tbody>{top_rows}</tbody></table></div></div>'
        f'<p style="font-size:11px;color:{P["text_dim"]};margin:8px 0 0">'
        f'National CMS participation directory — <b>not</b> savings/performance '
        f'results and <b>not</b> provider-specific. Exec/contact PII excluded on '
        f'ingest.</p></div>')


def render_cms_apm_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.cms_apm_tracker import compute_cms_apm_tracker
    r = compute_cms_apm_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Active Programs", str(r.total_programs), "", "") +
        ck_kpi_block("Lives Covered", f"{r.total_lives_covered_m:.1f}M", "", "") +
        ck_kpi_block("CMS Payments", f"${r.total_apm_payments_b:.1f}B", "", "") +
        ck_kpi_block("Avg Savings Rate", f"{r.avg_savings_rate_pct:.2f}%", "", "") +
        ck_kpi_block("Portfolio APM Revenue", f"${r.total_portfolio_apm_revenue_m:.1f}M", "", "") +
        ck_kpi_block("Deals @ Risk (>10%)", str(sum(1 for e in r.exposures if e.apm_share_of_rev_pct > 0.10)), "", "") +
        ck_kpi_block("Policy Events", str(len(r.calendar)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    p_chart = _programs_chart(r.programs)
    p_tbl = _programs_table(r.programs)
    value_anchor = ck_value_anchor(
        "CMS APM Landscape",
        f"${r.total_apm_payments_b:,.0f}B APM payments",
        delta=f"{r.total_programs} programs \u00b7 {r.avg_savings_rate_pct:.1f}% avg savings \u00b7 {r.total_lives_covered_m:.1f}M lives covered (CMMI public reference)",
        tone="teal",
    )
    portfolio_illustrative = ck_illustrative_note(
        "portfolio APM-exposure figures \u2014 the deal names and revenue shares "
        "below are a worked example, not this portfolio's live data"
    )
    e_tbl = _exposures_table(r.exposures)
    e_chart = _exposures_chart(r.exposures)
    t_tbl = _trends_table(r.trends)
    rs_tbl = _risk_table(r.risk_structures)
    c_tbl = _calendar_table(r.calendar)
    pa_tbl = _payer_table(r.payer_adjacency)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "CMS Innovation Models / APM Tracker",
        eyebrow="CMS APM",
        meta=f"{r.total_programs} active CMS APMs · {r.total_lives_covered_m:.1f}M lives covered · ${r.total_apm_payments_b:.1f}B annual Medicare payments",
    )

    # The program catalog / performance / calendar / risk-structure tables are
    # curated from public CMS Innovation Center (CMMI) program descriptions —
    # program names, structures and timelines are public fact; the figures are
    # curated approximations, not a live CMS feed. The portfolio-exposure and
    # commercial-adjacency halves are a worked example (the "Project ..." deals
    # are not this portfolio's live data) and are scoped illustrative below.
    source_header = ck_source_purpose(
        purpose=("Track which CMS alternative-payment models a target "
                 "participates in and the policy calendar that moves its "
                 "value-based revenue."),
        universe="cms",
        confidence="derived",
        source="CMS Innovation Center (CMMI) program catalog — curated public reference",
        next_action="Attach a deal to map its real APM participation",
        next_href="/diligence/checklist",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {source_header}
  {_mssp_landscape_section()}
  {_colorado_apm_section()}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Program Catalog — CMMI & CMS APMs</div>{p_chart}{p_tbl}</div>
  {portfolio_illustrative}
  <div style="{cell}"><div style="{h3}">Portfolio Exposure — Deals in APMs <span style="color:{P['warning']}">· ILLUSTRATIVE</span></div>{e_chart}{e_tbl}</div>
  <div style="{cell}"><div style="{h3}">Historical Performance — Top Programs</div>{t_tbl}</div>
  <div style="{cell}"><div style="{h3}">Risk Structure Options</div>{rs_tbl}</div>
  <div style="{cell}"><div style="{h3}">2026-2027 Policy Calendar & Portfolio Impact</div>{c_tbl}</div>
  <div style="{cell}"><div style="{h3}">Commercial / MA Value-Based Adjacency <span style="color:{P['warning']}">· ILLUSTRATIVE</span></div>{pa_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-radius:2px;padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">CMS APM landscape (public reference):</strong> {r.total_programs} active CMS APMs cover {r.total_lives_covered_m:.1f}M lives and route ${r.total_apm_payments_b:.1f}B in annual Medicare payments — avg {r.avg_savings_rate_pct:.2f}% savings rate across active programs.
    Policy overhang: ACO REACH sunset 2026-12-31 ($42.5B program ending), PCF sunset 2026-12-31 ($12.8B), BPCI-A sunset 2025-12-31 ($18.5B) — transition paths to MCP, MSSP, and TEAM.
    -2.8% proposed 2026 physician fee schedule conversion-factor cut is the headline FFS pressure for the cycle.
    <br><br><em style="color:{P['warning']}">Illustrative overlay:</em> the portfolio-exposure and commercial-adjacency figures (${r.total_portfolio_apm_revenue_m:.1f}M across {len(r.exposures)} example platforms, the "Project ..." deal names, and the {r.portfolio_share_at_risk_pct * 100:.1f}% at-risk share) are a worked example — attach a real deal to map its actual APM participation.
  </div>
</div>"""

    # NOTE: the source-and-purpose header is composed into `body` above via
    # `source_header` (universe=cms, curated CMMI public reference). PR2c's
    # lighter "universe=illustrative / Hardcoded figures" prepend was removed in
    # the #670→#678 rebase — it both duplicated and contradicted the accurate
    # CMMI framing (the program catalog is real public reference; only the
    # portfolio overlay is illustrative, which is scoped separately).
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "CMS APM Tracker", active_nav="/cms-apm",
        editorial_intro={
            "eyebrow": "CMS APM TRACKER",
            "headline": "What the cms apm tracker page reveals on this deal.",
            "italic_word": "reveals",
        })
