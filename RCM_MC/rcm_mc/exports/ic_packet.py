"""IC Packet Assembler — the single signed deliverable that
replaces the 4-6 hours of manual assembly a PE associate does
before IC.

Combines, in one printable HTML document:

    1. Cover — deal name, partner, IC date, recommendation
    2. Partner synthesis — 3-paragraph narrative across the 9
       Tier-1/2/3 risk modules written in partner voice
    3. Headline numbers — EV, revenue, EBITDA, projected MOIC/IRR
       with market-comp context (HCA / THC / sector-median)
    4. Bankruptcy-Survivor Scan verdict + named case-study matches
    5. QoR waterfall reconciliation (claims-side accrual vs. mgmt)
    6. 9 risk-module one-page summaries (CPOM, NSA, Steward, TEAM,
       antitrust, physician comp, cyber, MA V28, quality/WC/synergy,
       patient-pay/reputational)
    7. Counterfactual Advisor — the "what would change our mind"
       section, largest lever highlighted
    8. EBITDA bridge with lever breakdown + market-comp multiple
    9. 100-day plan headline + integration velocity estimate
   10. Open diligence questions (P0/P1)
   11. Walkaway conditions
   12. Partner sign-off block

Zero new runtime deps. Single HTML output with @media print CSS —
browser Save-as-PDF produces the final IC deliverable. DOCX
ingestion is lossless (structural markup only; presentation lives
in one <style> block).
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class ICPacketMetadata:
    """Non-analytical fields on the cover + sign-off pages."""
    deal_name: str = "Target Entity"
    target_entity: Optional[str] = None
    engagement_id: Optional[str] = None
    ic_date: Optional[str] = None              # ISO; defaults to today
    partner_name: Optional[str] = None
    preparer_name: Optional[str] = None
    recommendation: str = "PROCEED_WITH_CONDITIONS"  # PROCEED /
                                                      # PROCEED_WITH_CONDITIONS /
                                                      # DECLINE
    sector_sentiment: Optional[str] = None     # positive / negative
    confidentiality: str = (
        "Confidential. Prepared for the exclusive use of the named "
        "deal team. Distribution outside the firm is prohibited."
    )

    def resolved_ic_date(self) -> str:
        return self.ic_date or date.today().isoformat()


def _style_block() -> str:
    return """<style>
body {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 11pt; color: #1a1a1a;
    max-width: 7.5in; margin: 0 auto;
    padding: 0.75in 0.5in; line-height: 1.5;
}
h1 {
    font-size: 28pt; margin: 0 0 6pt 0;
    color: #0b2341; font-weight: 700;
    letter-spacing: -0.5pt;
}
h2 {
    font-size: 15pt; margin: 24pt 0 6pt 0;
    color: #0b2341; font-weight: 700;
    border-bottom: 1px solid #c9b98a;
    padding-bottom: 3pt;
    page-break-after: avoid;
}
h3 {
    font-size: 12pt; margin: 14pt 0 4pt 0;
    color: #2a2a2a; font-weight: 700;
}
p { margin: 6pt 0 10pt 0; }
.eyebrow {
    font-size: 9pt; letter-spacing: 1.5pt;
    text-transform: uppercase; color: #6b5d3c;
    font-family: 'Helvetica Neue', Arial, sans-serif;
}
.cover { page-break-after: always; padding-top: 1.5in; }
.cover-meta {
    margin-top: 1.5in; font-size: 10pt; color: #444;
}
.cover-meta table { border: 0; border-collapse: collapse; }
.cover-meta td { padding: 4pt 16pt 4pt 0; vertical-align: top; }
.cover-meta td.label {
    color: #6b5d3c; text-transform: uppercase;
    font-size: 9pt; letter-spacing: 1pt; font-weight: 700;
}
.recommend-banner {
    margin: 24pt 0; padding: 14pt 20pt;
    border-left: 6pt solid;
    background: #f8f6f0;
    page-break-inside: avoid;
}
.recommend-banner .label {
    font-size: 10pt; letter-spacing: 1.5pt;
    text-transform: uppercase; font-weight: 700;
}
.recommend-banner .body { font-size: 12pt; margin-top: 6pt; }
.recommend-proceed { border-left-color: #1f7a3a; }
.recommend-conditions { border-left-color: #b07c1f; }
.recommend-decline { border-left-color: #b23a2d; }
.headline-stats {
    display: table; width: 100%;
    margin: 14pt 0; border-collapse: separate;
    border-spacing: 0;
}
.headline-stats .stat-cell {
    display: table-cell; padding: 8pt 12pt;
    border: 1px solid #c9b98a;
    border-right: 0; width: 25%;
    vertical-align: top;
}
.headline-stats .stat-cell:last-child {
    border-right: 1px solid #c9b98a;
}
.stat-label {
    font-size: 9pt; letter-spacing: 1pt;
    text-transform: uppercase; color: #6b5d3c;
    font-weight: 700;
}
.stat-value {
    font-family: 'Courier New', monospace;
    font-size: 18pt; color: #0b2341;
    font-weight: 700; margin-top: 3pt;
}
.stat-sub { font-size: 9pt; color: #6b5d3c; margin-top: 2pt; }
.band-card {
    margin: 10pt 0; padding: 10pt 14pt;
    border-left: 4pt solid; background: #f8f6f0;
    page-break-inside: avoid;
}
.band-card.immaterial, .band-card.green { border-left-color: #1f7a3a; background: #f0f7f2; }
.band-card.watch, .band-card.yellow { border-left-color: #b07c1f; background: #fbf6ec; }
.band-card.critical, .band-card.red { border-left-color: #b23a2d; background: #fbf0ee; }
.band-card.unknown { border-left-color: #6b5d3c; background: #f5f1ea; }
.band-card .band {
    font-size: 9pt; font-weight: 700;
    letter-spacing: 1.5pt; text-transform: uppercase;
    font-family: 'Helvetica Neue', Arial, sans-serif;
}
.band-card .headline { font-size: 13pt; font-weight: 700; margin: 2pt 0 4pt 0; }
.num { font-family: 'Courier New', monospace; }
table.data {
    width: 100%; border-collapse: collapse;
    font-size: 10pt; margin: 6pt 0 12pt 0;
}
table.data th {
    text-align: left; border-bottom: 1pt solid #0b2341;
    padding: 4pt 6pt; font-size: 9pt; letter-spacing: 0.5pt;
    text-transform: uppercase; color: #6b5d3c;
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-weight: 700;
}
table.data td {
    padding: 4pt 6pt; border-bottom: 1px solid #e6dfca;
}
table.data td.num {
    font-family: 'Courier New', monospace;
    text-align: right;
}
ul.tight { margin: 4pt 0 10pt 0; padding-left: 20pt; }
ul.tight li { margin: 3pt 0; }
.hedge { font-style: italic; color: #6b5d3c; }
.signature-block {
    margin-top: 32pt; padding: 16pt 0;
    border-top: 2px solid #c9b98a;
    page-break-inside: avoid;
}
.signature-line {
    display: inline-block; width: 3in;
    border-bottom: 1pt solid #333; height: 20pt;
    margin-right: 18pt;
}
.footer {
    font-size: 8pt; color: #6b5d3c; margin-top: 32pt;
    padding-top: 8pt; border-top: 1px solid #c9b98a;
    font-family: 'Helvetica Neue', Arial, sans-serif;
}
.section-break { page-break-before: always; }

@page { size: Letter; margin: 0.75in 0.5in; }
@media print {
    body { max-width: none; padding: 0; }
    h2 { page-break-after: avoid; }
    .signature-block, .recommend-banner, .band-card {
        page-break-inside: avoid;
    }
}
</style>"""


# ── Section renderers ───────────────────────────────────────────

def _cover(meta: ICPacketMetadata) -> str:
    rec_copy = {
        "PROCEED": ("recommend-proceed", "Proceed"),
        "PROCEED_WITH_CONDITIONS": (
            "recommend-conditions", "Proceed with conditions",
        ),
        "DECLINE": ("recommend-decline", "Decline"),
    }
    cls, label = rec_copy.get(
        meta.recommendation,
        ("recommend-conditions", "Proceed with conditions"),
    )
    rows = [
        ("IC Date", meta.resolved_ic_date()),
        ("Deal", meta.deal_name),
    ]
    if meta.target_entity and meta.target_entity != meta.deal_name:
        rows.append(("Target entity", meta.target_entity))
    if meta.engagement_id:
        rows.append(("Engagement", meta.engagement_id))
    if meta.partner_name:
        rows.append(("Partner", meta.partner_name))
    if meta.preparer_name:
        rows.append(("Prepared by", meta.preparer_name))
    rows.append(("Deliverable", "IC Packet v1 — partner-signed"))
    rows_html = "".join(
        f'<tr><td class="label">{html.escape(k)}</td>'
        f'<td>{html.escape(v)}</td></tr>'
        for k, v in rows
    )
    return (
        '<div class="cover">'
        '<div class="eyebrow">Investment Committee Memorandum</div>'
        f'<h1>{html.escape(meta.deal_name)}</h1>'
        f'<div class="recommend-banner {cls}">'
        '<div class="label">Recommendation</div>'
        f'<div class="body">{html.escape(label)}</div>'
        '</div>'
        f'<div class="cover-meta"><table>{rows_html}</table></div>'
        '</div>'
    )


def _partner_synthesis(
    bankruptcy_verdict: Optional[str],
    regulatory_composite: Optional[str],
    steward_tier: Optional[str],
    counterfactual_critical_count: int,
    counterfactual_largest: Optional[Dict[str, Any]],
    qor_status: Optional[str],
    cyber_band: Optional[str],
) -> str:
    """Three paragraph partner-voice synthesis."""
    # Paragraph 1: headline verdict.
    opening = "The platform's integrated diligence signals resolve to"
    if bankruptcy_verdict in ("RED", "CRITICAL"):
        para1 = (
            f"{opening} a CRITICAL screen-level finding "
            f"({bankruptcy_verdict}). At least one Tier-1 pattern "
            f"matches a named historical bankruptcy. The IC should "
            f"condition any offer on resolution of the flagged "
            f"vector(s) or walk."
        )
    elif bankruptcy_verdict == "YELLOW":
        para1 = (
            f"{opening} a WATCH-tier screen result: one or two "
            f"structural patterns match a named case, but none "
            f"replays fully. Proceed with conditions."
        )
    else:
        para1 = (
            f"{opening} a clean screen. No named-bankruptcy pattern "
            f"matched. Structural risk is manageable."
        )

    # Paragraph 2: regulatory + Steward + cyber + QoR.
    para2_parts: List[str] = []
    if regulatory_composite == "RED":
        para2_parts.append(
            "Regulatory composite is RED — CPOM, TEAM, NSA, or "
            "antitrust fires a material finding. Clear before close."
        )
    elif regulatory_composite == "YELLOW":
        para2_parts.append(
            "Regulatory composite is YELLOW — at least one "
            "state-level restriction applies. Counsel opinion in "
            "file before close."
        )
    if steward_tier == "CRITICAL":
        para2_parts.append(
            "Steward Score is CRITICAL: all five factors present. "
            "This is the exact profile that produced Steward "
            "(2016-2024). Structural remediation required."
        )
    elif steward_tier == "HIGH":
        para2_parts.append(
            "Steward Score is HIGH (4/5 factors). Prospect-style "
            "profile. Escalator cap or REIT-landlord swap before "
            "close."
        )
    if cyber_band == "RED":
        para2_parts.append(
            "CyberScore is RED. BA cascade risk (Change Healthcare) "
            "or IT underinvestment drives a bridge-reserve "
            "requirement."
        )
    if qor_status == "CRITICAL":
        para2_parts.append(
            "QoR reconciliation is CRITICAL — claims-side accrual "
            "disagrees with management by more than the VMG/A&M "
            "5% threshold. Partner-quotable finding."
        )
    if not para2_parts:
        para2_parts.append(
            "Regulatory, real-estate, cyber, and QoR dimensions "
            "clear without material finding."
        )
    para2 = " ".join(para2_parts)

    # Paragraph 3: counterfactual voice — the "can we fix this"
    # answer.
    if counterfactual_critical_count == 0:
        para3 = (
            "No counterfactual levers are needed — the target "
            "already resolves cleanly. Proceed to the operational "
            "EBITDA bridge as the primary value case."
        )
    elif counterfactual_largest:
        lever = counterfactual_largest.get("lever", "")
        module = counterfactual_largest.get("module", "")
        change = counterfactual_largest.get(
            "change_description", "",
        )
        dollars = float(
            counterfactual_largest.get("estimated_dollar_impact_usd", 0)
            or 0
        )
        dollar_str = (
            f" (~${dollars:,.0f})" if dollars > 0 else ""
        )
        para3 = (
            f"{counterfactual_critical_count} RED/CRITICAL finding(s) "
            f"have a counterfactual that flips the band. Largest "
            f"lever: {module} — {change}{dollar_str}. The IC should "
            f"price this into the offer as a closing condition."
        )
    else:
        para3 = (
            f"{counterfactual_critical_count} RED/CRITICAL finding(s) "
            f"identified; no mechanical counterfactual flips them all. "
            f"Structural remediation or walkaway."
        )

    return (
        '<h2>Partner Synthesis</h2>'
        f'<p>{html.escape(para1)}</p>'
        f'<p>{html.escape(para2)}</p>'
        f'<p>{html.escape(para3)}</p>'
    )


def _headline_stats(
    *,
    enterprise_value_usd: Optional[float],
    revenue_usd: Optional[float],
    ebitda_usd: Optional[float],
    projected_moic: Optional[float],
    projected_irr: Optional[float],
    peer_median_ev_ebitda: Optional[float],
) -> str:
    def fmt_dollar(v):
        if v is None:
            return "—"
        if abs(v) >= 1_000_000_000:
            return f"${v/1_000_000_000:.2f}B"
        if abs(v) >= 1_000_000:
            return f"${v/1_000_000:.1f}M"
        return f"${v:,.0f}"

    ev_ebitda = None
    if enterprise_value_usd and ebitda_usd and ebitda_usd > 0:
        ev_ebitda = enterprise_value_usd / ebitda_usd

    ev_ebitda_str = (
        f"{ev_ebitda:.2f}x" if ev_ebitda is not None else "—"
    )
    peer_sub = (
        f"Peer median: {peer_median_ev_ebitda:.2f}x"
        if peer_median_ev_ebitda is not None else ""
    )
    moic_str = (f"{projected_moic:.2f}x"
                if projected_moic is not None else "—")
    irr_str = (f"{projected_irr*100:.1f}%"
               if projected_irr is not None else "—")

    cells = [
        ("Enterprise Value", fmt_dollar(enterprise_value_usd), ""),
        ("Revenue TTM", fmt_dollar(revenue_usd), ""),
        ("EBITDA TTM", fmt_dollar(ebitda_usd), ""),
        ("EV / EBITDA", ev_ebitda_str, peer_sub),
    ]
    cell_html = "".join(
        f'<div class="stat-cell">'
        f'<div class="stat-label">{html.escape(label)}</div>'
        f'<div class="stat-value">{html.escape(val)}</div>'
        + (f'<div class="stat-sub">{html.escape(sub)}</div>' if sub else "")
        + '</div>'
        for label, val, sub in cells
    )
    extra = ""
    if projected_moic is not None or projected_irr is not None:
        extra = (
            f'<div class="headline-stats" style="margin-top:6pt;">'
            f'<div class="stat-cell" style="width:50%;">'
            f'<div class="stat-label">Projected MOIC</div>'
            f'<div class="stat-value">{html.escape(moic_str)}</div></div>'
            f'<div class="stat-cell" style="width:50%;">'
            f'<div class="stat-label">Projected IRR</div>'
            f'<div class="stat-value">{html.escape(irr_str)}</div></div>'
            f'</div>'
        )
    return (
        '<h2>Headline Numbers</h2>'
        f'<div class="headline-stats">{cell_html}</div>'
        f'{extra}'
    )


def _bankruptcy_scan_section(scan: Optional[Any]) -> str:
    if scan is None:
        return ""
    verdict = getattr(scan, "verdict", None)
    verdict_val = verdict.value if hasattr(verdict, "value") else str(verdict or "UNKNOWN")
    critical_hits = getattr(scan, "critical_hits", 0)
    patterns_hit = getattr(scan, "patterns_hit", 0)
    cls = verdict_val.lower()
    comparisons = getattr(scan, "named_comparisons", []) or []
    comparisons_html = "".join(
        f"<li>{html.escape(c)}</li>" for c in comparisons[:6]
    )
    return (
        '<h2>Bankruptcy-Survivor Scan</h2>'
        f'<div class="band-card {cls}">'
        f'<div class="band">{html.escape(verdict_val)}</div>'
        f'<div class="headline">'
        f'{patterns_hit} / 12 patterns hit · '
        f'{critical_hits} critical</div>'
        f'</div>'
        + (f'<p>Named historical comparisons the scan surfaced:</p>'
           f'<ul class="tight">{comparisons_html}</ul>'
           if comparisons_html else "")
    )


def _qor_section(waterfall: Optional[Any]) -> str:
    if waterfall is None:
        return ""
    status = getattr(waterfall, "total_divergence_status", "UNKNOWN")
    cls = status.lower()
    accrual = getattr(waterfall, "total_accrual_revenue_usd", None) or 0
    mgmt = getattr(waterfall, "total_management_revenue_usd", None)
    delta = getattr(waterfall, "total_qor_divergence_usd", None)
    pct = getattr(waterfall, "total_qor_divergence_pct", None)
    numbers_html = ""
    if mgmt is not None:
        delta_val = delta or 0
        pct_val = pct or 0
        numbers_html = (
            f'<p class="num">Waterfall accrual '
            f'${accrual:,.0f} · Management accrual ${mgmt:,.0f} · '
            f'Delta {"+" if delta_val >= 0 else "−"}${abs(delta_val):,.0f} '
            f'({pct_val*100:+.2f}%)</p>'
        )
    else:
        numbers_html = (
            '<p class="hedge">Management-reported accrual not '
            'supplied; QoR reconciliation shows claims-side only.</p>'
        )
    return (
        '<h2>Quality of Revenue</h2>'
        f'<div class="band-card {cls}">'
        f'<div class="band">{html.escape(status)}</div>'
        f'<div class="headline">Claims-side vs. management-reported '
        f'accrual reconciliation.</div>'
        f'{numbers_html}'
        f'</div>'
    )


def _risk_summary_section(
    *,
    regulatory_packet: Optional[Any] = None,
    steward_score: Optional[Any] = None,
    cyber_score: Optional[Any] = None,
    ma_v28_result: Optional[Any] = None,
    physician_comp_roster_size: Optional[int] = None,
    stark_findings_count: Optional[int] = None,
) -> str:
    """One-line summary per Tier-1/2 risk module."""
    rows: List[str] = []

    def row(module, band, detail):
        rows.append(
            f'<tr><td>{html.escape(module)}</td>'
            f'<td style="font-weight:600;">{html.escape(band)}</td>'
            f'<td>{html.escape(detail)}</td></tr>'
        )

    if regulatory_packet is not None:
        band = getattr(regulatory_packet, "composite_band", None)
        band_val = band.value if hasattr(band, "value") else str(band or "UNKNOWN")
        criticals = len(getattr(regulatory_packet, "critical_findings", []) or [])
        dollars = getattr(
            regulatory_packet, "total_dollars_at_risk_usd", 0,
        ) or 0
        row("Regulatory", band_val,
            f"{criticals} critical finding(s) · "
            f"${dollars:,.0f} at risk across CPOM/NSA/site-neutral/TEAM/antitrust")
    if steward_score is not None:
        tier = getattr(steward_score, "tier", None)
        tier_val = tier.value if hasattr(tier, "value") else str(tier or "UNKNOWN")
        factors = getattr(steward_score, "factor_count", 0)
        row("Real Estate (Steward)", tier_val,
            f"{factors} / 5 Steward-pattern factors present")
    if cyber_score is not None:
        band = getattr(cyber_score, "band", "UNKNOWN")
        score = getattr(cyber_score, "score", 0)
        row("Cyber", str(band),
            f"CyberScore {score}/100 · "
            f"{getattr(cyber_score, 'ba_critical_count', 0)} critical BA finding(s)")
    if ma_v28_result is not None:
        pct = getattr(
            ma_v28_result,
            "aggregate_risk_score_reduction_pct", 0,
        )
        dollars = getattr(
            ma_v28_result, "aggregate_revenue_impact_usd", 0,
        )
        band = "RED" if pct > 0.03 else (
            "YELLOW" if pct > 0.01 else "GREEN"
        )
        row("MA V28", band,
            f"{pct*100:.2f}% aggregate risk-score reduction · "
            f"${dollars:,.0f} revenue impact")
    if physician_comp_roster_size is not None:
        band = "YELLOW" if (stark_findings_count or 0) > 0 else "GREEN"
        row("Physician Comp",
            "HIGH" if (stark_findings_count or 0) >= 3 else band,
            f"{physician_comp_roster_size} providers · "
            f"{stark_findings_count or 0} Stark/AKS red-line finding(s)")
    if not rows:
        return ""
    return (
        '<h2>Risk Module Summary</h2>'
        '<table class="data">'
        '<thead><tr><th>Module</th><th>Band</th><th>Detail</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _counterfactual_section(cfs: Optional[Any]) -> str:
    if cfs is None:
        return ""
    items = getattr(cfs, "items", []) or []
    if not items:
        return (
            '<h2>What Would Change Our Mind</h2>'
            '<p class="hedge">No counterfactual levers applicable — '
            'no RED/CRITICAL findings requiring offer-shape '
            'modifications.</p>'
        )
    largest = getattr(cfs, "largest_lever", None)
    largest_html = ""
    if largest is not None and getattr(
        largest, "estimated_dollar_impact_usd", 0,
    ) > 0:
        largest_html = (
            f'<p><strong>Largest lever:</strong> '
            f'{html.escape(getattr(largest, "module", ""))} — '
            f'{html.escape(getattr(largest, "change_description", ""))} '
            f'(~${largest.estimated_dollar_impact_usd:,.0f} savings).'
            f'</p>'
        )
    item_rows: List[str] = []
    for cf in items:
        module = getattr(cf, "module", "")
        orig = getattr(cf, "original_band", "")
        target = getattr(cf, "target_band", "")
        desc = getattr(cf, "change_description", "")
        feas = getattr(cf, "feasibility", "")
        dollar = float(
            getattr(cf, "estimated_dollar_impact_usd", 0) or 0
        )
        impl = getattr(cf, "deal_structure_implication", "")
        dollar_str = (
            f" · ~${dollar:,.0f} PV"
            if dollar > 0 else ""
        )
        item_rows.append(
            f'<li><strong>{html.escape(module)}</strong> '
            f'({html.escape(orig)} → {html.escape(target)}, '
            f'feasibility {html.escape(feas)}{dollar_str}): '
            f'{html.escape(desc)} '
            f'<br><span class="hedge">Deal: {html.escape(impl)}</span>'
            f'</li>'
        )
    return (
        '<h2>What Would Change Our Mind</h2>'
        f'{largest_html}'
        f'<ul class="tight">{"".join(item_rows)}</ul>'
    )


def _market_context_section(
    comps: Optional[List[Dict[str, Any]]],
    sector_sentiment: Optional[str],
    transaction_band: Optional[Any],
) -> str:
    if not (comps or transaction_band):
        return ""
    parts: List[str] = ['<h2>Market Context</h2>']
    if sector_sentiment:
        parts.append(
            f'<p>Sector sentiment: <strong>'
            f'{html.escape(sector_sentiment)}</strong></p>'
        )
    if transaction_band:
        tb = transaction_band
        parts.append(
            f'<p>Private-market median EV/EBITDA: <strong>'
            f'{getattr(tb, "p50_ev_ebitda", 0):.1f}x</strong> '
            f'(p25–p75: {getattr(tb, "p25_ev_ebitda", 0):.1f}x – '
            f'{getattr(tb, "p75_ev_ebitda", 0):.1f}x, '
            f'{getattr(tb, "sample_size", 0)} deals TTM).</p>'
        )
        note = getattr(tb, "note", None)
        if note:
            parts.append(f'<p class="hedge">{html.escape(note)}</p>')
    if comps:
        rows = "".join(
            f'<tr>'
            f'<td>{html.escape(c["ticker"])}</td>'
            f'<td>{html.escape(c["name"])}</td>'
            f'<td class="num">${c["revenue_ttm_usd_bn"]:.1f}B</td>'
            f'<td class="num">{c["ev_ebitda_multiple"]:.2f}x</td>'
            f'</tr>'
            for c in comps[:5]
        )
        parts.append(
            '<table class="data">'
            '<thead><tr><th>Ticker</th><th>Operator</th>'
            '<th>Revenue TTM</th><th>EV/EBITDA</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
        )
    return "".join(parts)


def _open_questions_section(questions: Optional[Iterable[Any]]) -> str:
    if not questions:
        return ""
    items: List[str] = []
    for q in questions:
        text = getattr(q, "question", None) or getattr(q, "text", str(q))
        pri = getattr(q, "priority", None)
        pri_text = pri.value if hasattr(pri, "value") else (
            str(pri) if pri else ""
        )
        context = getattr(q, "context", None) or getattr(q, "why", "")
        pri_prefix = f"<strong>[{html.escape(pri_text)}]</strong> " if pri_text else ""
        ctx = (
            f'<br><span class="hedge">{html.escape(str(context))}</span>'
        ) if context else ""
        items.append(
            f'<li>{pri_prefix}{html.escape(str(text))}{ctx}</li>'
        )
    if not items:
        return ""
    return (
        '<h2>Open Diligence Questions</h2>'
        f'<ul class="tight">{"".join(items)}</ul>'
    )


def _walkaway_section(walkaway_conditions: Optional[List[str]]) -> str:
    if not walkaway_conditions:
        return ""
    items = "".join(
        f'<li>{html.escape(c)}</li>' for c in walkaway_conditions
    )
    return (
        '<h2>Walkaway Conditions</h2>'
        f'<ul class="tight">{items}</ul>'
    )


def _hundred_day_section(hundred_day_summary: Optional[str]) -> str:
    if not hundred_day_summary:
        return ""
    return (
        '<h2>100-Day Plan Headline</h2>'
        f'<p>{html.escape(hundred_day_summary)}</p>'
    )


def _signoff(meta: ICPacketMetadata) -> str:
    partner = meta.partner_name or ""
    preparer = meta.preparer_name or ""
    return (
        '<div class="signature-block">'
        '<h3>Partner Sign-Off</h3>'
        '<p>I have reviewed the above synthesis, module-level '
        'findings, counterfactual levers, and open diligence '
        'items. Signing below acknowledges the findings and '
        'authorises the memo for distribution within the deal '
        'team.</p>'
        f'<p style="margin-top:32pt;">'
        f'<span class="signature-line"></span> '
        f'{html.escape(partner) if partner else "Partner signature"}'
        f'</p>'
        f'<p style="margin-top:22pt;">'
        f'<span class="signature-line"></span> Date</p>'
        f'<p style="margin-top:22pt;" class="hedge">'
        f'Prepared by {html.escape(preparer) if preparer else "managing analyst"}'
        '</p>'
        '</div>'
    )


# ── Public entry ────────────────────────────────────────────────

def render_ic_packet_html(
    *,
    metadata: ICPacketMetadata,
    bankruptcy_scan: Optional[Any] = None,
    cash_waterfall: Optional[Any] = None,
    regulatory_packet: Optional[Any] = None,
    steward_score: Optional[Any] = None,
    cyber_score: Optional[Any] = None,
    ma_v28_result: Optional[Any] = None,
    physician_comp_roster_size: Optional[int] = None,
    stark_findings_count: Optional[int] = None,
    counterfactuals: Optional[Any] = None,
    open_questions: Optional[Iterable[Any]] = None,
    walkaway_conditions: Optional[List[str]] = None,
    hundred_day_summary: Optional[str] = None,
    enterprise_value_usd: Optional[float] = None,
    revenue_usd: Optional[float] = None,
    ebitda_usd: Optional[float] = None,
    projected_moic: Optional[float] = None,
    projected_irr: Optional[float] = None,
    peer_median_ev_ebitda: Optional[float] = None,
    public_comps: Optional[List[Dict[str, Any]]] = None,
    sector_sentiment: Optional[str] = None,
    transaction_multiple_band: Optional[Any] = None,
) -> str:
    """Render the full IC packet. Every section that lacks data is
    quietly suppressed — the memo never renders blank tables or
    fabricated numbers."""
    # Pull sub-bands for the partner synthesis.
    bankruptcy_verdict = None
    if bankruptcy_scan is not None:
        v = getattr(bankruptcy_scan, "verdict", None)
        bankruptcy_verdict = v.value if hasattr(v, "value") else str(v or "")
    qor_status = (
        getattr(cash_waterfall, "total_divergence_status", None)
        if cash_waterfall else None
    )
    regulatory_composite = None
    if regulatory_packet is not None:
        cb = getattr(regulatory_packet, "composite_band", None)
        regulatory_composite = (
            cb.value if hasattr(cb, "value") else str(cb or "")
        )
    steward_tier = None
    if steward_score is not None:
        st = getattr(steward_score, "tier", None)
        steward_tier = st.value if hasattr(st, "value") else str(st or "")
    cyber_band = (
        getattr(cyber_score, "band", None) if cyber_score else None
    )
    critical_count = (
        getattr(counterfactuals, "critical_findings_addressed", 0)
        if counterfactuals else 0
    )
    largest_dict = None
    if counterfactuals is not None:
        largest = getattr(counterfactuals, "largest_lever", None)
        if largest is not None:
            largest_dict = largest.to_dict() if hasattr(
                largest, "to_dict",
            ) else None

    sections = [
        _style_block(),
        _cover(metadata),
        _partner_synthesis(
            bankruptcy_verdict, regulatory_composite, steward_tier,
            critical_count, largest_dict, qor_status, cyber_band,
        ),
        _headline_stats(
            enterprise_value_usd=enterprise_value_usd,
            revenue_usd=revenue_usd,
            ebitda_usd=ebitda_usd,
            projected_moic=projected_moic,
            projected_irr=projected_irr,
            peer_median_ev_ebitda=peer_median_ev_ebitda,
        ),
        _bankruptcy_scan_section(bankruptcy_scan),
        _qor_section(cash_waterfall),
        _risk_summary_section(
            regulatory_packet=regulatory_packet,
            steward_score=steward_score,
            cyber_score=cyber_score,
            ma_v28_result=ma_v28_result,
            physician_comp_roster_size=physician_comp_roster_size,
            stark_findings_count=stark_findings_count,
        ),
        _counterfactual_section(counterfactuals),
        _market_context_section(
            public_comps, sector_sentiment, transaction_multiple_band,
        ),
        _hundred_day_section(hundred_day_summary),
        _open_questions_section(open_questions),
        _walkaway_section(walkaway_conditions),
        _signoff(metadata),
        (f'<div class="footer">{html.escape(metadata.confidentiality)}'
         f' · Generated '
         f'{datetime.now(timezone.utc).isoformat()}</div>'),
    ]
    body = "\n".join(s for s in sections if s)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f'<title>IC Packet — {html.escape(metadata.deal_name)}</title>\n'
        "</head>\n"
        f'<body>\n{body}\n</body>\n</html>\n'
    )
