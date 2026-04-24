"""CMS Program Integrity Manual (Pub 100-08) — /cms-pim."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _tier_color(t: str) -> str:
    return {"CRITICAL": P["negative"], "HIGH": P["negative"],
            "MEDIUM": P["warning"], "LOW": P["accent"]}.get(t, P["text_dim"])


def _relevance_color(r: str) -> str:
    return {"high": P["negative"], "medium": P["warning"], "low": P["text_dim"]}.get(r, P["text_dim"])


def _chapters_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Ch", "right"), ("Title", "left"), ("PE Relevance", "center"),
            ("Sections", "right"), ("Primary Contractors", "left"),
            ("Common Diligence Trigger", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        rc = _relevance_color(c.pe_relevance)
        cells = [
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{c.chapter_number}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:320px">{_html.escape(c.chapter_title)}<div style="font-size:10px;color:{text_dim};font-weight:400;margin-top:2px">{_html.escape(c.scope_summary)}</div></td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(c.pe_relevance.upper())}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{c.section_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:180px">{_html.escape(", ".join(c.primary_contractors))}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:540px">{_html.escape(c.common_diligence_trigger)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _sections_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Ch / §", "left"), ("Section Title", "left"), ("Summary", "left"),
            ("Contractors", "left"), ("Enforcement", "left"),
            ("Recovery $M", "right"), ("Last Rev", "right"),
            ("Diligence Note", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, s in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        recov_cell = "—"
        if s.typical_recovery_range_mm:
            low, high = s.typical_recovery_range_mm
            recov_cell = f"${low:.1f}–${high:.1f}M"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:700">Ch {s.chapter_number} {_html.escape(s.section_number)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:260px">{_html.escape(s.section_title)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:340px">{_html.escape(s.summary)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:120px">{_html.escape(", ".join(s.audit_contractor_ids))}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:180px">{_html.escape(s.enforcement_mechanism)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos};font-weight:700">{recov_cell}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{s.last_revised_year}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px">{_html.escape(s.diligence_note)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _contractors_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("ID", "left"), ("Full Name", "left"), ("Scope", "left"),
            ("Statutory Auth.", "left"), ("Remuneration", "left"),
            ("Lookback", "right"), ("Review Focus", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.short_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:280px">{_html.escape(c.full_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(c.geographic_scope)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:220px">{_html.escape(c.statutory_authority)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:200px">{_html.escape(c.remuneration_model)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{c.typical_lookback_years}yr</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:420px">{_html.escape(c.review_scope)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _overlaps_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal", "left"), ("Year", "right"), ("Provider Type", "left"),
            ("Sections Applicable", "right"), ("Critical Refs", "left"),
            ("Contractors in Scope", "left"), ("Est. Exposure", "right"),
            ("Tier", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, o in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        tc = _tier_color(o.exposure_tier)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(o.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{o.deal_year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(o.inferred_provider_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{o.relevant_section_count}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(", ".join(o.critical_section_refs))}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:180px">{_html.escape(", ".join(o.top_contractors))}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${o.aggregate_recovery_exposure_mm:.2f}M</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(o.exposure_tier)}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_program_integrity_manual(params: dict = None) -> str:
    from rcm_mc.data_public.cms_program_integrity_manual import compute_program_integrity_manual
    r = compute_program_integrity_manual()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    high_rel = sum(1 for c in r.chapters if c.pe_relevance == "high")
    kpi_strip = (
        ck_kpi_block("Chapters", str(r.total_chapters), "Pub 100-08", "") +
        ck_kpi_block("Curated Sections", str(r.total_sections), "", "") +
        ck_kpi_block("High PE Relevance", str(high_rel), "chapters", "") +
        ck_kpi_block("Contractors", str(r.total_contractors), "RAC/UPIC/SMRC/CERT/MAC/OIG", "") +
        ck_kpi_block("KB Version", r.knowledge_base_version, r.effective_date, "") +
        ck_kpi_block("Material Overlaps", f"{r.corpus_deals_with_material_overlap:,}", "corpus deals", "") +
        ck_kpi_block("CRITICAL Exposure", str(r.critical_exposure_count), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    chapter_tbl = _chapters_table(r.chapters)
    sections_tbl = _sections_table(r.sections)
    contractors_tbl = _contractors_table(r.contractors)
    overlaps_tbl = _overlaps_table(r.corpus_overlaps)
    citations_html = "<br>".join(f"• {_html.escape(c)}" for c in r.source_citations)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">CMS Program Integrity Manual (Pub 100-08) — Codified Knowledge</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_chapters} chapters · {r.total_sections} curated sections · {r.total_contractors} federal audit contractors · manual version {_html.escape(r.manual_version)} · KB {r.knowledge_base_version} effective {r.effective_date} · primary source: <a href="{_html.escape(r.manual_base_url)}" style="color:{acc}">CMS.gov Pub 100-08</a></p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Manual Structure — 15 Chapters with PE Relevance Rating</div>{chapter_tbl}</div>
  <div style="{cell}"><div style="{h3}">Curated Sections — 33 Audit + Enforcement Provisions with Diligence Notes</div>{sections_tbl}</div>
  <div style="{cell}"><div style="{h3}">Federal Audit Contractors — The Parties Executing Pub 100-08</div>{contractors_tbl}</div>
  <div style="{cell}"><div style="{h3}">Corpus Deal Overlap — Top 60 Deals by Applicable-Section Count</div>{overlaps_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Program Integrity Thesis:</strong>
    Pub 100-08 is the operational handbook that Recovery Audit Contractors (RACs),
    Unified Program Integrity Contractors (UPICs), the Supplemental Medical Review
    Contractor (SMRC), the Comprehensive Error Rate Testing (CERT) contractor, and
    Medicare Administrative Contractors (MACs) use to execute federal audit,
    recovery, and administrative-sanction activity. Codifying it here gives the
    platform ground-truth mechanics for post-close audit exposure estimation —
    distinct from OIG's prospective Work Plan (which says what WILL be audited)
    and DOJ's retrospective FCA (which says what HAS BEEN settled).
    <br><br>
    <strong style="color:{text}">How this module integrates:</strong>
    Cross-links to <code style="color:{acc};font-family:JetBrains Mono,monospace">/ncci-scanner</code>
    (§ 5.3 cardiac stress-test overlap, § 5.6 therapy unit-count), <code style="color:{acc};font-family:JetBrains Mono,monospace">/oig-workplan</code>
    (prospective audit topic → § 5.x operational review), <code style="color:{acc};font-family:JetBrains Mono,monospace">/doj-fca</code>
    (§ 11.2 UPIC → DOJ referral criteria), and <code style="color:{acc};font-family:JetBrains Mono,monospace">/team-calculator</code>
    (§ 6.x MAC overpayment recovery mechanics — TEAM reconciliation runs through
    this workflow). IC Brief (<code style="color:{acc};font-family:JetBrains Mono,monospace">/ic-brief</code>)
    should consume PIM section-overlap as a severity factor in future iterations.
    <br><br>
    <strong style="color:{text}">Highest PE-diligence chapters:</strong>
    Chapters 5 (Specific Items), 6 (Overpayment Recovery), 7 (RAC Audit), 8
    (Administrative Actions), 9 (Exclusions), and 11 (Fraud Investigations) carry
    "high" PE relevance. Chapters 8 and 9 are deal-breaker-level — payment
    suspensions and exclusions can paralyze a leveraged target; any active-
    investigation disclosure is CIM-level escalation.
    <br><br>
    <strong style="color:{text}">KB provenance (versioned, cited):</strong>
    <div style="font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px;line-height:1.5;margin-top:4px">
    KB version: {r.knowledge_base_version} · Manual: {_html.escape(r.manual_version)} · Effective: {r.effective_date}<br>
    {citations_html}
    </div>
  </div>
</div>"""

    return chartis_shell(body, "CMS Program Integrity Manual", active_nav="/cms-pim")
