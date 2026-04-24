"""NSA IDR Modeler — /nsa-idr."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {"CRITICAL": P["negative"], "HIGH": P["negative"],
            "MEDIUM": P["warning"], "LOW": P["accent"]}.get(t, P["text_dim"])


def _exposure_color(s: str) -> str:
    return {"very high": P["negative"], "high": P["negative"],
            "medium": P["warning"], "low": P["text_dim"]}.get(s, P["text_dim"])


def _codes_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("HCPCS", "left"), ("Descriptor", "left"), ("Specialty", "left"),
            ("Pre-NSA OON", "right"), ("QPA 2025", "right"),
            ("IDR Median 2024", "right"), ("Compression %", "right"),
            ("Vol (M/yr)", "right"), ("Batched?", "center"), ("Notes", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        compr_c = neg if c.effective_compression_pct >= 15 else P["warning"]
        batch_cell = "✓" if c.batching_eligible else "—"
        batch_c = pos if c.batching_eligible else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.hcpcs_code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};max-width:240px">{_html.escape(c.descriptor)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:160px">{_html.escape(c.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${c.pre_nsa_oon_rate_2021:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${c.qpa_2025:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${c.idr_median_award_2024:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{compr_c};font-weight:700">-{c.effective_compression_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.annual_medicare_volume_m:.2f}</td>',
            f'<td style="text-align:center;padding:5px 10px;color:{batch_c};font-family:JetBrains Mono,monospace;font-size:12px;font-weight:700">{batch_cell}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(c.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _profiles_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Specialty", "left"), ("Disputes 2024", "right"),
            ("Provider Win %", "right"), ("Payer Win %", "right"),
            ("Median Award % of QPA", "right"), ("Billed/QPA", "right"),
            ("Batched %", "right"), ("Turnaround Days", "right"),
            ("Dominant Payers", "left"), ("PE Exposure", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        win_c = P["warning"] if p.provider_prevailed_pct >= 30 else P["negative"]
        exp_c = _exposure_color(p.pe_exposure_concentration)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{p.total_idr_disputes_2024:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{win_c};font-weight:700">{p.provider_prevailed_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg}">{p.payer_prevailed_pct:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{p.median_award_pct_of_qpa:.1f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.median_billed_charge_multiple:.1f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.batched_dispute_share_pct:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.typical_turnaround_days}d</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(p.dominant_payer_respondents)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{exp_c};border:1px solid {exp_c};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(p.pe_exposure_concentration.upper())}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _events_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Year", "right"), ("Month", "center"), ("Type", "left"),
            ("Event", "left"), ("Summary", "left"), ("Citation", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{e.year}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(e.month)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(e.event_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:700;max-width:240px">{_html.escape(e.name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};max-width:480px">{_html.escape(e.summary)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:260px">{_html.escape(e.citation)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _exposures_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Deal", "left"), ("Year", "right"), ("Specialty", "left"),
            ("OON Share %", "right"), ("OON Revenue $M", "right"),
            ("Compression %", "right"), ("Annual Loss $M", "right"),
            ("EBITDA Impact $M", "right"), ("Tier", "center"), ("Codes", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, e in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(e.exposure_tier)
        codes = ", ".join(e.primary_nsa_codes_affected[:3])
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(e.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.deal_year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(e.inferred_specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{e.estimated_oon_revenue_share_pct:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${e.estimated_oon_revenue_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">-{e.estimated_nsa_compression_pct:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">-${e.estimated_annual_revenue_loss_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">-${e.estimated_ebitda_impact_mm:,.2f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(e.exposure_tier)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(codes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_nsa_idr_modeler(params: dict = None) -> str:
    from rcm_mc.data_public.nsa_idr_modeler import compute_nsa_idr_modeler
    r = compute_nsa_idr_modeler()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("HCPCS Codes", str(r.total_codes_tracked), "NSA-affected", "") +
        ck_kpi_block("Specialties", str(r.total_specialties_tracked), "hospital-based", "") +
        ck_kpi_block("IDR Disputes 2024", f"{r.total_idr_disputes_covered:,}", "HHS Q-reports", "") +
        ck_kpi_block("Avg Provider Win", f"{r.avg_provider_prevail_pct:.1f}%", "payer-favored 70%+", "") +
        ck_kpi_block("Corpus Exposed", str(r.total_exposed_deals), "hospital-based physician", "") +
        ck_kpi_block("CRITICAL", str(r.critical_exposure_count), "", "") +
        ck_kpi_block("Corpus NSA Loss", f"${r.total_corpus_nsa_compression_mm:,.0f}M", "annual", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    codes_tbl = _codes_table(r.codes)
    profiles_tbl = _profiles_table(r.specialty_profiles)
    events_tbl = _events_table(r.rule_events)
    exposures_tbl = _exposures_table(r.deal_exposures)
    citations_html = "<br>".join(f"• {_html.escape(c)}" for c in r.source_citations)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">NSA IDR Modeler — QPA-Anchored Rate Mechanics</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_codes_tracked} NSA-affected HCPCS × {r.total_specialties_tracked} hospital-based physician specialties · {r.total_idr_disputes_covered:,} total 2024 IDR disputes · provider-win rate averaging {r.avg_provider_prevail_pct:.0f}% (payer-favored 70%+) · {r.critical_exposure_count} CRITICAL corpus exposures · <strong style="color:{acc}">${r.total_corpus_nsa_compression_mm:,.0f}M annual corpus-wide compression</strong> · KB {r.knowledge_base_version}</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">NSA-Affected HCPCS — Pre-NSA OON Rate vs QPA 2025 vs IDR Median Award</div>{codes_tbl}</div>
  <div style="{cell}"><div style="{h3}">Specialty IDR Profiles — Dispute Volume + Provider Win Rate (2024)</div>{profiles_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top Corpus Deal Exposures — Hospital-Based Physician Targets</div>{exposures_tbl}</div>
  <div style="{cell}"><div style="{h3}">NSA / IDR Timeline — Rule Events + Litigation (2020-2025)</div>{events_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">NSA IDR Thesis:</strong>
    The No Surprises Act (effective 2022) banned surprise balance billing for OON services
    at in-network facilities. The IDR process anchors rates to QPA (payer's median in-network
    rate). 2024 HHS data shows providers prevail ~25% of disputes with median awards
    ~10-20% above QPA — a massive compression from pre-NSA OON rates that were typically
    3-6x Medicare. This is THE failure mechanism behind Envision (NF-02), American
    Physician Partners (NF-03), and the Envision-USAP-TeamHealth antitrust cluster (NF-11).
    <br><br>
    <strong style="color:{text}">Corpus exposure:</strong>
    {r.total_exposed_deals} corpus deals match hospital-based physician keywords
    (ED, anesthesia, radiology, pathology, hospitalist, neonatology, air ambulance).
    {r.critical_exposure_count} CRITICAL-tier with estimated annual revenue loss > $50M
    or > 30% of EBITDA. Total corpus-wide NSA compression: <strong style="color:{acc}">
    ${r.total_corpus_nsa_compression_mm:,.0f}M/year</strong>. Any hospital-based physician
    target post-2022 must be modeled against NSA/IDR trajectory — pre-NSA multiples
    permanently impaired.
    <br><br>
    <strong style="color:{text}">Integration:</strong>
    Cross-links to <code style="color:{acc};font-family:JetBrains Mono,monospace">/named-failures</code>
    (NF-02, NF-03, NF-08, NF-11), <code style="color:{acc};font-family:JetBrains Mono,monospace">/cms-claims-manual</code>
    (Ch 12 physician mechanics), <code style="color:{acc};font-family:JetBrains Mono,monospace">/ic-brief</code>
    (hospital-based physician target auto-flags), <code style="color:{acc};font-family:JetBrains Mono,monospace">/rag</code>
    (citation-indexed).
    <br><br>
    <strong style="color:{text}">KB provenance (versioned, cited):</strong>
    <div style="font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px;line-height:1.5;margin-top:4px">
    KB version: {r.knowledge_base_version} · Rule basis: {_html.escape(r.rule_version)} · Effective: {r.effective_date}<br>
    {citations_html}
    </div>
  </div>
</div>"""

    return chartis_shell(body, "NSA IDR Modeler", active_nav="/nsa-idr")
