"""CMS Medicare Claims Processing Manual (Pub 100-04) — /cms-claims-manual."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {"HIGH": P["negative"], "MEDIUM": P["warning"], "LOW": P["accent"]}.get(t, P["text_dim"])


def _relevance_color(r: str) -> str:
    return {"high": P["negative"], "medium": P["warning"], "low": P["text_dim"]}.get(r, P["text_dim"])


def _chapters_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Ch", "right"), ("Title", "left"), ("Claim-Type Scope", "left"),
            ("PE Relevance", "center"), ("Sections", "right"),
            ("Deal Applicability", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = _relevance_color(c.pe_relevance)
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{c.chapter_number}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:300px">{_html.escape(c.chapter_title)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:220px">{_html.escape(c.claim_type_scope)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(c.pe_relevance.upper())}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{c.section_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:540px">{_html.escape(c.typical_deal_applicability)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sections_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Ch / §", "left"), ("Title", "left"), ("Claim Type", "left"),
            ("Summary", "left"), ("Key Mechanic", "left"),
            ("Relev.", "center"), ("Transmittal", "right"),
            ("Diligence Note", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    ranked = sorted(items, key=lambda s: (s.chapter_number, s.section_number))
    for i, s in enumerate(ranked):
        rb = panel_alt if i % 2 == 0 else bg
        rc = _relevance_color(s.pe_relevance)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:700">Ch {s.chapter_number} {_html.escape(s.section_number)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:220px">{_html.escape(s.section_title)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:160px">{_html.escape(s.claim_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(s.summary)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos};max-width:220px">{_html.escape(s.key_billing_mechanic)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:9px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(s.pe_relevance.upper())}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(s.last_transmittal)}<br><span style="font-size:9px">{s.last_revised_year}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px">{_html.escape(s.diligence_note)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _overlays_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal", "left"), ("Year", "right"), ("Provider Type", "left"),
            ("Applicable Ch", "right"), ("Chapters", "left"),
            ("HIGH §", "right"), ("Key Refs", "left"),
            ("Tier", "center"), ("Diligence Summary", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(o.exposure_tier)
        ch_list = ", ".join(f"Ch{x}" for x in o.applicable_chapters[:5])
        refs = ", ".join(o.notable_section_refs)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(o.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{o.deal_year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(o.inferred_provider_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{o.applicable_chapter_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};max-width:160px">{_html.escape(ch_list)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{o.high_relevance_section_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:180px">{_html.escape(refs)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(o.exposure_tier)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:440px">{_html.escape(o.diligence_summary)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_claims_processing_manual(params: dict = None) -> str:
    from rcm_mc.data_public.cms_claims_processing_manual import compute_claims_processing_manual
    r = compute_claims_processing_manual()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    high_rel_chapters = sum(1 for c in r.chapters if c.pe_relevance == "high")
    kpi_strip = (
        ck_kpi_block("Chapters Documented", f"{r.total_chapters_documented}/{r.total_chapters_in_manual}", "Pub 100-04", "") +
        ck_kpi_block("Curated Sections", str(r.total_sections), "", "") +
        ck_kpi_block("HIGH PE-Relevance", str(r.high_pe_relevance_sections), "sections", "") +
        ck_kpi_block("HIGH Chapters", str(high_rel_chapters), "", "") +
        ck_kpi_block("KB Version", r.knowledge_base_version, r.effective_date, "") +
        ck_kpi_block("Corpus Overlays", f"{r.corpus_deals_with_overlay:,}", "deals", "") +
        ck_kpi_block("Manual", "Pub 100-04", "Claims Processing", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    chapters_tbl = _chapters_table(r.chapters)
    sections_tbl = _sections_table(r.sections)
    overlays_tbl = _overlays_table(r.corpus_overlays)
    citations_html = "<br>".join(f"• {_html.escape(c)}" for c in r.source_citations)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Medicare Claims Processing Manual (Pub 100-04) — Codified Knowledge</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_chapters_documented} chapters documented of {r.total_chapters_in_manual} (coverage = {r.total_chapters_documented/r.total_chapters_in_manual*100:.0f}%) · {r.total_sections} curated sections ({r.high_pe_relevance_sections} HIGH PE-relevance) · manual version {_html.escape(r.manual_version)} · KB {r.knowledge_base_version} effective {r.effective_date} · primary source: <a href="{_html.escape(r.manual_base_url)}" style="color:{acc}">CMS.gov Pub 100-04</a></p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Chapter Coverage — PE Relevance by Claim-Type Scope</div>{chapters_tbl}</div>
  <div style="{cell}"><div style="{h3}">Curated Sections — Billing Mechanic + Diligence Note per Section</div>{sections_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top 60 Corpus Deal Overlays — Applicable Chapters by Inferred Provider Type</div>{overlays_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Pub 100-04 vs Pub 100-08:</strong>
    This is the billing handbook — how claims should be correctly submitted and paid.
    Complementary to <code style="color:{acc};font-family:JetBrains Mono,monospace">/cms-pim</code>
    (Pub 100-08 Program Integrity), which defines how auditors challenge those claims.
    Any billing-pattern outlier diligence surfaces should be adjudicated against the
    specific Pub 100-04 section governing that claim type before concluding compliance risk.
    <br><br>
    <strong style="color:{text}">Highest-PE-relevance chapters:</strong>
    Ch 3 (Inpatient Hospital — DRG + outlier + transfer), Ch 4 (OPPS including site-neutral),
    Ch 6 (SNF PDPM), Ch 10 (Home Health PDGM + F2F + HHVBP), Ch 11 (Hospice CHC +
    certification), Ch 12 (Physician E/M + incident-to), Ch 13 (Radiology TC/26 + AUC),
    Ch 14 (MA encounter data + RADV), Ch 17 (Part B drugs ASP), Ch 37 (OPPS packaging + APC).
    <br><br>
    <strong style="color:{text}">Integration points:</strong>
    NCCI Edit Scanner (<code style="color:{acc};font-family:JetBrains Mono,monospace">/ncci-scanner</code>)
    enforces the CPT-pair billing rules codified here. HFMA MAP Keys
    (<code style="color:{acc};font-family:JetBrains Mono,monospace">/hfma-map-keys</code>) reference
    these billing mechanics in their KPI definitions. TEAM Calculator
    (<code style="color:{acc};font-family:JetBrains Mono,monospace">/team-calculator</code>)
    reconciliation mechanics flow through Ch 3 + Ch 4 OPPS processing. Document RAG
    (<code style="color:{acc};font-family:JetBrains Mono,monospace">/rag</code>) indexes these
    sections for cross-module citation-grounded retrieval.
    <br><br>
    <strong style="color:{text}">KB provenance (versioned, cited):</strong>
    <div style="font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px;line-height:1.5;margin-top:4px">
    KB version: {r.knowledge_base_version} · Manual: {_html.escape(r.manual_version)} · Effective: {r.effective_date}<br>
    {citations_html}
    </div>
  </div>
</div>"""

    return chartis_shell(body, "CMS Claims Processing Manual Pub 100-04", active_nav="/cms-claims-manual")
