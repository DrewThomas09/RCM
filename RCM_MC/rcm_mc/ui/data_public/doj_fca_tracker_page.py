"""DOJ False Claims Act / Qui Tam Tracker — /doj-fca."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _sev_color(s: str) -> str:
    return {"CRITICAL": P["negative"], "HIGH": P["negative"], "MEDIUM": P["warning"]}.get(s, P["text_dim"])


def _alleg_color(a: str) -> str:
    # Muted variants per allegation category
    if "Kickback" in a or "Stark" in a:
        return P["negative"]
    if "Upcoding" in a or "Medical Necessity" in a or "Billing" in a:
        return P["warning"]
    if "Risk Adjustment" in a or "Drug Pricing" in a or "Off-Label" in a:
        return P["accent"]
    return P["text_dim"]


def _settlements_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Case", "left"), ("Defendant", "left"), ("Year", "right"),
            ("Allegation", "left"), ("Provider Type", "left"),
            ("$M", "right"), ("Fed Share", "right"),
            ("Qui Tam", "center"), ("CIA", "center"), ("Citation", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    ranked = sorted(items, key=lambda s: s.settlement_amount_mm, reverse=True)
    for i, s in enumerate(ranked[:60]):
        rb = panel_alt if i % 2 == 0 else bg
        alleg_c = _alleg_color(s.allegation_type)
        qt_label = "✓" if s.qui_tam_source else "—"
        qt_color = pos if s.qui_tam_source else text_dim
        cia_label = f"✓ {s.cia_term_years}yr" if s.cia_imposed else "—"
        cia_color = P["negative"] if s.cia_imposed else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(s.case_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:240px">{_html.escape(s.defendant)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{s.settlement_year}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{alleg_c};max-width:220px">{_html.escape(s.allegation_type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(s.provider_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${s.settlement_amount_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">${s.federal_share_mm:,.1f}M</td>',
            f'<td style="text-align:center;padding:5px 10px;color:{qt_color};font-family:JetBrains Mono,monospace;font-size:11px">{qt_label}</td>',
            f'<td style="text-align:center;padding:5px 10px;color:{cia_color};font-family:JetBrains Mono,monospace;font-size:10px;font-weight:700">{cia_label}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(s.court_citation[:50])}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _provider_rollup_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Provider Type", "left"), ("Cases", "right"),
            ("Total $M", "right"), ("Avg $M", "right"),
            ("CIA Rate", "right"), ("Qui Tam Rate", "right"),
            ("Recent (5yr)", "right"), ("Notable Defendants", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cia_rate = (p.cia_imposed_count / p.settlement_count * 100.0) if p.settlement_count else 0
        qt_rate = (p.qui_tam_initiated_count / p.settlement_count * 100.0) if p.settlement_count else 0
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.provider_type)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.settlement_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.total_settlement_mm:,.0f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">${p.avg_settlement_mm:,.1f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{cia_rate:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{qt_rate:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.recent_settlement_count_5yr}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:440px">{_html.escape(p.notable_defendants)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _alleg_rollup_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]; acc = P["accent"]
    cols = [("Allegation Type", "left"), ("Cases", "right"), ("Total $M", "right"),
            ("CIA Rate", "right"), ("Qui Tam Rate", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, a in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(a["allegation_type"])}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{a["count"]}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${a["total_mm"]:,.0f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{a["cia_rate_pct"]:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{a["qui_tam_rate_pct"]:.0f}%</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _matches_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; neg = P["negative"]
    cols = [("Deal", "left"), ("Year", "right"), ("Matched Defendants", "left"),
            ("FCA $M", "right"), ("Latest Yr", "right"),
            ("CIA Active", "center"), ("Severity", "center"), ("Rationale", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = _sev_color(m.match_severity)
        cia = "✓" if m.cia_active else "—"
        cia_c = neg if m.cia_active else text_dim
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(m.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{m.deal_year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:260px">{_html.escape(", ".join(m.matched_defendants[:3]))}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{neg};font-weight:700">${m.total_exposure_mm:,.0f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{m.max_settlement_year or "—"}</td>',
            f'<td style="text-align:center;padding:5px 10px;color:{cia_c};font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700">{cia}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em;font-weight:700">{_html.escape(m.match_severity)}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:440px">{_html.escape(m.rationale[:300])}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_doj_fca_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.doj_fca_tracker import compute_doj_fca_tracker
    r = compute_doj_fca_tracker()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Settlements", str(r.total_settlements), f"KB {r.knowledge_base_version}", "") +
        ck_kpi_block("Total $", f"${r.total_settlement_amount_b:.2f}B", "aggregate", "") +
        ck_kpi_block("Qui Tam Cases", str(r.total_qui_tam_count), f"of {r.total_settlements}", "") +
        ck_kpi_block("CIAs Imposed", str(r.total_cia_count), "Corporate Integrity Agreements", "") +
        ck_kpi_block("Relator Share $", f"${r.total_relator_share_mm:,.0f}M", "awarded to whistleblowers", "") +
        ck_kpi_block("Corpus Defendant Matches", str(len(r.defendant_matches)), "", "") +
        ck_kpi_block("CRITICAL Matches", str(sum(1 for m in r.defendant_matches if m.match_severity == "CRITICAL")), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    sources_html = "<br>".join(f"• {_html.escape(u)}" for u in r.source_urls)

    settlements_tbl = _settlements_table(r.settlements)
    provider_tbl = _provider_rollup_table(r.provider_type_rollup)
    alleg_tbl = _alleg_rollup_table(r.allegation_type_rollup)
    matches_tbl = _matches_table(r.defendant_matches)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">DOJ False Claims Act + Qui Tam Tracker</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_settlements} curated healthcare FCA settlements 2013-2026 · ${r.total_settlement_amount_b:.2f}B aggregate · {r.total_qui_tam_count} qui tam-initiated · {r.total_cia_count} CIA-imposed · ${r.total_relator_share_mm:,.0f}M relator awards · defendant-match engine surfaces {len(r.defendant_matches)} corpus deals with prior FCA exposure</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Settlement Catalog — Top 60 by $ Amount</div>{settlements_tbl}</div>
  <div style="{cell}"><div style="{h3}">Provider-Type Rollup — Where Enforcement $ Concentrates</div>{provider_tbl}</div>
  <div style="{cell}"><div style="{h3}">Allegation-Type Rollup — The Pattern Library of Fraud Vectors</div>{alleg_tbl}</div>
  <div style="{cell}"><div style="{h3}">Corpus Defendant Matches — Deals with Prior FCA-Named Entities</div>{matches_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">DOJ FCA Thesis:</strong>
    Prior DOJ False Claims Act exposure is among the hardest pre-close red flags in healthcare PE.
    A defendant named in a recent settlement carries ongoing recoupment risk (often 5-year Corporate
    Integrity Agreement monitoring); an unsealed active qui tam is a near-term liability overhang.
    This tracker encodes {r.total_settlements} material healthcare FCA settlements with structured
    fields — defendant, allegation type, provider type, dollar amount, CIA status, relator share.
    Every entry cites the DOJ press release + court case number.
    <br><br>
    <strong style="color:{text}">Pattern insights from the rollup:</strong>
    <strong style="color:{text}">Pharmaceutical manufacturers</strong> lead aggregate $ ({r.provider_type_rollup[0].total_settlement_mm:,.0f}M across {r.provider_type_rollup[0].settlement_count} cases) driven by kickback + off-label + drug-pricing cases.
    <strong style="color:{text}">Hospitals</strong> are second (${r.provider_type_rollup[1].total_settlement_mm:,.0f}M across {r.provider_type_rollup[1].settlement_count}) with upcoding + Stark/AKS + medical-necessity as dominant vectors.
    Qui tam rate is {sum(1 for s in r.settlements if s.qui_tam_source) / r.total_settlements * 100:.0f}% — whistleblowers drive most healthcare FCA activity.
    <br><br>
    <strong style="color:{text}">Integration with diligence workflow:</strong>
    IC Brief (/ic-brief) consumes this tracker — defendant-match triggers a CRITICAL red flag
    automatically. A target whose parent entity appeared in a $100M+ settlement with active CIA
    should rarely clear IC without (a) pre-close OIG self-disclosure, (b) independent compliance
    review of post-settlement remediation, and (c) indemnity cap structure in the SPA.
    <br><br>
    <strong style="color:{text}">KB provenance (versioned, cited):</strong>
    <div style="font-family:JetBrains Mono,monospace;color:{text_dim};font-size:10px;line-height:1.5;margin-top:4px">
    KB version: {r.knowledge_base_version} · Effective: {r.effective_date}<br>
    {sources_html}
    </div>
  </div>
</div>"""

    return chartis_shell(body, "DOJ FCA + Qui Tam Tracker", active_nav="/doj-fca")
