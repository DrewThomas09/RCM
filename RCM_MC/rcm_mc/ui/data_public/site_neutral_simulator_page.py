"""Site-Neutral Payment Simulator — /site-neutral."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {"CRITICAL": P["negative"], "HIGH": P["negative"],
            "MEDIUM": P["warning"], "LOW": P["accent"]}.get(t, P["text_dim"])


def _status_color(s: str) -> str:
    return {"non-excepted": P["negative"], "mid-build": P["warning"],
            "relocated": P["warning"], "excepted": P["positive"],
            "on-campus": P["positive"]}.get(s, P["text_dim"])


def _codes_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("HCPCS", "left"), ("Descriptor", "left"), ("Category", "left"),
            ("OPPS Rate", "right"), ("MPFS Rate", "right"), ("Differential", "right"),
            ("% Diff", "right"), ("Vol (M/yr)", "right"),
            ("Effective", "right"), ("Notes", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    ranked = sorted(items, key=lambda c: c.annual_medicare_volume_m * c.rate_differential, reverse=True)
    for i, c in enumerate(ranked):
        rb = panel_alt if i % 2 == 0 else bg
        diff_c = neg if c.differential_pct >= 50 else (P["warning"] if c.differential_pct >= 25 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.hcpcs_code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};max-width:260px">{_html.escape(c.descriptor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:140px">{_html.escape(c.service_category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.opps_rate_2025:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.mpfs_rate_2025:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">-${c.rate_differential:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{diff_c};font-weight:700">{c.differential_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.annual_medicare_volume_m:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{c.site_neutral_effective_year}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(c.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _pbd_statuses_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Status", "center"), ("Description", "left"), ("Cutoff Mechanic", "left"),
            ("Payment Basis", "left"), ("Grandfathering Rules", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = _status_color(s.status)
        cells = [
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(s.status.upper())}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:280px">{_html.escape(s.description)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px">{_html.escape(s.cutoff_mechanic)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:260px">{_html.escape(s.payment_rate_basis)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:440px">{_html.escape(s.typical_grandfathering_rules)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _events_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Year", "right"), ("Rule / Event", "left"), ("Type", "left"),
            ("Summary", "left"), ("Codes Added", "right"),
            ("10-yr Savings ($B)", "right"), ("Citation", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{e.year}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(e.rule_ref)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.event_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};max-width:480px">{_html.escape(e.summary)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{e.affected_code_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${e.annual_medicare_savings_b:.2f}B</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:280px">{_html.escape(e.citation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exposures_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Deal", "left"), ("Year", "right"), ("Provider Type", "left"),
            ("HOPD Revenue ($M)", "right"), ("SN Cut ($M/yr)", "right"),
            ("% of EBITDA", "right"), ("Categories", "left"), ("Tier", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(e.exposure_tier)
        cats = ", ".join(e.affected_code_categories[:3])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.deal_year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(e.inferred_provider_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${e.estimated_hopd_annual_revenue_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">-${e.estimated_sn_cut_annual_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{e.sn_cut_as_pct_of_ebitda:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(cats)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(e.exposure_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_site_neutral_simulator(params: dict = None) -> str:
    from rcm_mc.data_public.site_neutral_simulator import compute_site_neutral_simulator
    r = compute_site_neutral_simulator()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Codes Tracked", str(r.total_codes_tracked), "site-neutral-affected", "") +
        ck_kpi_block("PBD Statuses", str(len(r.pbd_statuses)), "", "") +
        ck_kpi_block("Rule Events", str(len(r.expansion_events)), "2015-2025", "") +
        ck_kpi_block("Avg Rate Differential", f"{r.avg_differential_pct:.1f}%", "OPPS → MPFS", "") +
        ck_kpi_block("Deals Exposed", str(r.total_deals_exposed), "of corpus", "") +
        ck_kpi_block("CRITICAL Exposure", str(r.critical_exposure_count), "", "") +
        ck_kpi_block("Corpus SN Cut", f"${r.total_corpus_sn_cut_exposure_mm:,.0f}M", "annual", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    codes_tbl = _codes_table(r.affected_codes)
    statuses_tbl = _pbd_statuses_table(r.pbd_statuses)
    events_tbl = _events_table(r.expansion_events)
    exposures_tbl = _exposures_table(r.deal_exposures)
    citations_html = "<br>".join(f"• {_html.escape(c)}" for c in r.source_citations)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Site-Neutral Payment Simulator — Section 603 + OPPS 2024/2025 Expansion</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_codes_tracked} site-neutral-affected HCPCS codes · {len(r.pbd_statuses)} PBD status types · {len(r.expansion_events)} CMS rule events 2015-2025 · {r.total_deals_exposed} corpus deals exposed ({r.critical_exposure_count} CRITICAL) · <strong style="color:{acc}">${r.total_corpus_sn_cut_exposure_mm:,.0f}M annual cut aggregated across corpus</strong> · KB {r.knowledge_base_version}</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Affected HCPCS Codes — OPPS vs MPFS Rate Differential (2025)</div>{codes_tbl}</div>
  <div style="{cell}"><div style="{h3}">PBD Status Mechanics — Excepted vs Non-Excepted vs Mid-Build</div>{statuses_tbl}</div>
  <div style="{cell}"><div style="{h3}">Site-Neutral Expansion Timeline — CMS Rule Events 2015-2025</div>{events_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top 60 Corpus Deal Exposures — HOPD / Imaging / Infusion Targets</div>{exposures_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Site-Neutral Thesis:</strong>
    Section 603 of the Bipartisan Budget Act of 2015 established the principle:
    off-campus provider-based departments acquired after Nov 2, 2015 should be paid the
    same rate as a physician office performing the same service — not the (typically
    2-3x higher) OPPS rate. Every CMS OPPS Final Rule since has expanded the list of
    affected codes.
    <br><br>
    <strong style="color:{text}">Why this matters now:</strong>
    CY2024 OPPS Final Rule (CMS-1786-FC) added 8 codes including the imaging expansion
    that directly drove Akumin's 2023 bankruptcy (NF-16). CY2025 Final Rule adds 4 more.
    Every hospital system with material off-campus PBD footprint, every freestanding
    imaging platform, every infusion-center rollup has quantifiable site-neutral
    exposure that should be modeled pre-close.
    <br><br>
    <strong style="color:{text}">Corpus aggregate exposure:</strong>
    Across {r.total_deals_exposed} exposed corpus deals, annual site-neutral cut totals
    <strong style="color:{acc}">${r.total_corpus_sn_cut_exposure_mm:,.0f}M</strong>. The
    platform-scale exposure is material; individual deal exposures run from 5% to 30%+
    of EBITDA in the CRITICAL tier. The strategic response (ASC conversion, PBD
    consolidation to on-campus, office-based billing) is the 100-day operating lever
    for these deals.
    <br><br>
    <strong style="color:{text}">Integrations:</strong>
    Cross-links to <code style="color:{acc};font-family:JetBrains Mono,monospace">/named-failures</code>
    (NF-16 Akumin pattern), <code style="color:{acc};font-family:JetBrains Mono,monospace">/cms-claims-manual</code>
    Ch 4 § 20.6.11 + Ch 37 (OPPS mechanics), and <code style="color:{acc};font-family:JetBrains Mono,monospace">/rag</code>
    (indexed for citation-grounded retrieval).
    <br><br>
    <strong style="color:{text}">KB provenance (versioned, cited):</strong>
    <div style="font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px;line-height:1.5;margin-top:4px">
    KB version: {r.knowledge_base_version} · Rule basis: {_html.escape(r.rule_version)} · Effective: {r.effective_date}<br>
    {citations_html}
    </div>
  </div>
</div>"""

    return chartis_shell(body, "Site-Neutral Payment Simulator", active_nav="/site-neutral")
