"""QoE Deliverable — /qoe. Partner-signed formal QoE document."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _rec_color(rec: str) -> str:
    return {"GREEN": P["positive"], "YELLOW": P["warning"], "RED": P["negative"]}.get(rec, P["text_dim"])


def _walk_category_color(c: str) -> str:
    return {"Reported": P["text_dim"], "One-Time": P["positive"],
            "Run-Rate": P["negative"], "Normalized": P["accent"]}.get(c, P["text_dim"])


def _conf_color(c: str) -> str:
    return {"high": P["positive"], "medium": P["warning"], "low": P["text_dim"]}.get(c, P["text_dim"])


def _cover_block(r) -> str:
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]
    rc = _rec_color(r.overall_recommendation)
    partners = "<br>".join(_html.escape(p) for p in r.partner_names)
    return f"""
<div style="background:{panel};border:1px solid {border};padding:40px 48px;margin-bottom:24px;min-height:360px;display:flex;flex-direction:column;justify-content:space-between">
  <div>
    <div style="font-size:10px;color:{text_dim};letter-spacing:0.16em;text-transform:uppercase;margin-bottom:12px">SEEKINGCHARTIS · HEALTHCARE ADVISORY</div>
    <div style="font-size:30px;font-weight:700;color:{text};font-family:Georgia,'Times New Roman',serif;line-height:1.2;margin-bottom:12px">Quality of Earnings</div>
    <div style="font-size:18px;font-weight:400;color:{text_dim};font-family:Georgia,serif;margin-bottom:30px">{_html.escape(r.report_type)}</div>
    <div style="font-size:20px;font-weight:600;color:{text};font-family:Georgia,serif">{_html.escape(r.deal_name)}</div>
    <div style="font-size:14px;color:{text_dim};margin-top:6px;font-family:Georgia,serif">Prepared for: {_html.escape(r.client_name)}</div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:24px;margin-top:40px;padding-top:24px;border-top:2px solid {border}">
    <div>
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px">Engagement</div>
      <div style="font-family:JetBrains Mono,monospace;font-size:13px;color:{text}">{_html.escape(r.engagement_number)}</div>
    </div>
    <div>
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px">Report Date</div>
      <div style="font-family:JetBrains Mono,monospace;font-size:13px;color:{text}">{_html.escape(r.report_date)}</div>
    </div>
    <div>
      <div style="font-size:10px;color:{text_dim};letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px">Recommendation</div>
      <div style="font-family:JetBrains Mono,monospace;font-size:16px;color:{rc};font-weight:700">{_html.escape(r.overall_recommendation)}</div>
    </div>
  </div>
  <div style="margin-top:30px;padding-top:20px;border-top:1px solid {border}">
    <div style="font-size:10px;color:{text_dim};letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px">Partner Signatures</div>
    <div style="font-family:Georgia,serif;font-size:13px;color:{text};line-height:1.8">{partners}</div>
  </div>
</div>
"""


def _walk_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Category", "left"), ("Line Item", "left"), ("Amount $M", "right"),
            ("Confidence", "center"), ("Rationale", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:8px 12px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        wc = _walk_category_color(a.category)
        cc = _conf_color(a.confidence)
        amt_c = pos if a.amount_mm >= 0 and a.category != "Reported" else (neg if a.amount_mm < 0 else text)
        cells = [
            f'<td style="text-align:left;padding:6px 12px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{wc};border:1px solid {wc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(a.category)}</span></td>',
            f'<td style="text-align:left;padding:6px 12px;font-size:12px;color:{text};font-weight:600;font-family:Georgia,serif;max-width:340px">{_html.escape(a.line_item)}</td>',
            f'<td style="text-align:right;padding:6px 12px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:13px;color:{amt_c};font-weight:700">{a.amount_mm:+.2f}</td>',
            f'<td style="text-align:center;padding:6px 12px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{cc};border:1px solid {cc};border-radius:2px;letter-spacing:0.06em">{_html.escape(a.confidence.upper())}</span></td>',
            f'<td style="text-align:left;padding:6px 12px;font-size:11px;color:{text_dim};font-family:Georgia,serif;line-height:1.5;max-width:540px">{_html.escape(a.rationale)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _section_html(s, idx: int) -> str:
    """Render one QoE section — narrative + optional data_rows."""
    panel = P["panel"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    # Skip section 1 (cover) and 2 (TOC) — rendered separately
    if s.section_number in ("1", "2"):
        return ""

    # Data table rendering for sections with data_rows
    data_block = ""
    if s.data_rows and s.kind in ("data_table", "mixed"):
        # For section 4 (overview) and 7 (EBITDA walk), data is structured
        if s.section_number == "4":
            rows_html = ""
            for r in s.data_rows:
                rows_html += (f'<tr><td style="padding:5px 12px;border-bottom:1px solid {border};'
                              f'font-size:11px;color:{text_dim};width:220px">{_html.escape(r.get("label", ""))}</td>'
                              f'<td style="padding:5px 12px;border-bottom:1px solid {border};'
                              f'font-family:JetBrains Mono,monospace;font-size:12px;color:{text};font-weight:600">'
                              f'{_html.escape(str(r.get("value", "")))}</td></tr>')
            data_block = f'<table style="width:100%;border-collapse:collapse;margin:12px 0;max-width:640px">{rows_html}</table>'

    narrative = s.default_content.replace("\n\n", "</p><p>").replace("\n", "<br>")
    editable_mark = ""
    if s.is_editable:
        editable_mark = (f'<div style="font-size:9px;color:{text_dim};letter-spacing:0.08em;'
                        f'text-transform:uppercase;margin-bottom:6px;font-family:JetBrains Mono,monospace">'
                        f'Partner-editable section — replace or augment below</div>')

    return f"""
<div style="background:{panel};border:1px solid {border};padding:28px 36px;margin-bottom:16px;page-break-inside:avoid">
  <div style="margin-bottom:16px">
    <div style="font-size:10px;color:{text_dim};letter-spacing:0.1em;text-transform:uppercase;margin-bottom:2px">Section {_html.escape(s.section_number)}</div>
    <h2 style="font-size:20px;font-weight:600;color:{text};font-family:Georgia,serif;margin:0">{_html.escape(s.title)}</h2>
  </div>
  {editable_mark}
  <div style="font-family:Georgia,serif;font-size:12px;color:{text};line-height:1.65;max-width:800px"><p>{narrative}</p></div>
  {data_block}
</div>
"""


def render_qoe_deliverable(params: dict = None) -> str:
    from rcm_mc.data_public.qoe_deliverable import compute_qoe_deliverable
    r = compute_qoe_deliverable()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Engagement", r.engagement_number, r.report_date, "") +
        ck_kpi_block("Reported EBITDA", f"${r.reported_ebitda_mm:,.1f}M" if r.reported_ebitda_mm else "—", "per CIM", "") +
        ck_kpi_block("Adjusted EBITDA", f"${r.adjusted_ebitda_mm:,.1f}M" if r.adjusted_ebitda_mm else "—", "QoE", "") +
        ck_kpi_block("EBITDA Quality", f"{r.ebitda_quality_score:.1f}/100", "confidence-weighted", "") +
        ck_kpi_block("Sections", str(len(r.sections)), "", "") +
        ck_kpi_block("Adjustments", str(len(r.ebitda_walk)), "walk items", "") +
        ck_kpi_block("Recommendation", r.overall_recommendation, "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    # Cover + TOC
    toc_items = "".join(
        f'<li style="padding:4px 0;font-family:Georgia,serif;font-size:12px;color:{text}">'
        f'<span style="display:inline-block;width:40px;font-family:JetBrains Mono,monospace;color:{text_dim}">§{_html.escape(s.section_number)}</span>'
        f'{_html.escape(s.title)}</li>'
        for s in r.sections if s.section_number not in ("1", "2")
    )
    toc_block = (
        f'<div style="background:{panel};border:1px solid {border};padding:28px 36px;margin-bottom:16px">'
        f'<h2 style="font-size:18px;font-weight:600;color:{text};font-family:Georgia,serif;margin:0 0 16px 0">Table of Contents</h2>'
        f'<ol style="list-style:none;margin:0;padding:0">{toc_items}</ol>'
        f'</div>'
    )

    cover = _cover_block(r)
    walk_tbl = _walk_table(r.ebitda_walk)
    sections_html = "".join(_section_html(s, i) for i, s in enumerate(r.sections))

    # Print CSS: page-break-inside avoid + hide nav when printing
    print_css = """
<style>
@media print {
  body { background: white !important; color: black !important; }
  .ck-nav, .ck-bar-top, .no-print { display: none !important; }
  .ck-main { margin: 0 !important; padding: 0 !important; }
  div[style*="page-break-inside"] { page-break-inside: avoid; }
  h2 { page-break-after: avoid; }
  table { page-break-inside: avoid; }
  a { text-decoration: none; color: black; }
}
@page { margin: 0.75in 0.6in; size: letter; }
</style>
"""

    # Export toolbar
    export_tb = (
        f'<div class="no-print" style="margin-bottom:12px;display:flex;gap:8px;align-items:center">'
        f'<button onclick="window.print()" style="background:{acc};color:white;border:none;padding:8px 18px;'
        f'font-family:JetBrains Mono,monospace;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;'
        f'cursor:pointer;font-weight:700">▶ Print / Save as PDF</button>'
        f'<span style="font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace">💡 Cmd+P / Ctrl+P — '
        f'browser "Save as PDF" produces the deliverable. HTML version is also Word-compatible '
        f'(File → Open in Word renders document structure).</span>'
        f'</div>'
    )

    body = f"""
{print_css}
<div style="padding:20px;max-width:900px;margin:0 auto">
  <div class="no-print" style="margin-bottom:14px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">QoE Deliverable — Partner-Signed Formal Document</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Auto-generated from IC Brief layer · 12 sections × {len(r.ebitda_walk)} EBITDA walk items · Chartis/VMG-class formal aesthetic · Print-to-PDF for client delivery · HTML is Word-compatible for partner editing</p>
  </div>
  <div class="no-print" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  {export_tb}
  {cover}
  {toc_block}
  {sections_html}
  <div style="background:{panel};border:1px solid {border};padding:20px 28px;margin-bottom:16px">
    <h2 style="font-size:16px;font-weight:600;color:{text};font-family:Georgia,serif;margin:0 0 12px 0">EBITDA Walk Detail</h2>
    <div style="font-family:Georgia,serif;font-size:11px;color:{text_dim};line-height:1.6;max-width:720px">
      Reported EBITDA ${r.reported_ebitda_mm:,.1f}M → Adjusted EBITDA ${r.adjusted_ebitda_mm:,.1f}M.
      Quality score {r.ebitda_quality_score:.1f}/100 reflects confidence-weighted composition of {len([a for a in r.ebitda_walk if a.confidence == "high"])} high-confidence + {len([a for a in r.ebitda_walk if a.confidence == "medium"])} medium-confidence + {len([a for a in r.ebitda_walk if a.confidence == "low"])} low-confidence adjustments.
    </div>
    {walk_tbl}
  </div>
  <div class="no-print" style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim}">
    <strong style="color:{text}">QoE Deliverable:</strong>
    Auto-composed from IC Brief layer data. 12 canonical QoE sections (Cover, ToC,
    Executive Summary, Transaction Overview, Market Context, Financial Performance,
    QoE Adjustments, RCM Findings, Regulatory Exposure, Risk Assessment, Recommendations,
    Partner Sign-Off). Every partner-editable section flagged explicitly. EBITDA walk
    is algorithmic — run-rate adjustments are driven by NCCI edit density (/ncci-scanner),
    OIG Work Plan overlap (/oig-workplan), government payer share, and entry multiple.
    Commercial rate uplift is scale-driven via platform size.
    <br><br>
    Print-to-PDF uses native browser print dialog with @media print CSS that hides the
    Chartis shell + nav and paginates sections cleanly. For true Word (.docx) export,
    File → Open HTML file in Word renders the document structure with full editability.
    True .docx generation would need python-docx (not in current dep set); HTML-to-Word
    is the interim path.
  </div>
</div>"""

    return chartis_shell(body, f"QoE — {r.deal_name[:40]}", active_nav="/qoe")
