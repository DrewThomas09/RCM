"""Partner-signed Quality-of-Earnings memo template.

The QoE memo is the document a partner actually puts their name on
at the end of a diligence engagement. It is distinct from the
analyst's workbench: it is the narrative deliverable, signed, that
summarises the headline finding for the deal team and IC.

Zero-dep output: this module emits a single self-contained HTML
string with a ``@media print`` stylesheet. Browsers save-as-PDF
produces a clean, page-broken partner-ready document. DOCX exports
can be produced by opening the HTML in Word; the document uses only
structural markup (h1/h2/p/table) plus inline styles so Word
ingestion is lossless. No python-docx / reportlab dependency is
added.

Inputs (all optional except ``bundle``):

    bundle                 — KPIBundle (required — no memo without KPIs)
    cash_waterfall         — CashWaterfallReport (QoR headline)
    repricing_report       — RepricingReport (contract re-pricer, optional)
    risk_flags             — iterable of RiskFlag-like objects (optional)
    diligence_questions    — iterable of P0/P1 questions (optional)

    deal_name              — deal/engagement display name
    target_entity          — legal entity name on the contract
    engagement_id          — internal reference number
    partner_name           — signing partner
    preparer_name          — managing analyst
    as_of_label            — override for the as-of text
    confidentiality        — footer disclaimer line

The memo is authored in the partner's voice: calm, cited, hedge when
the data is censored or missing, never interpolate.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, List, Mapping, Optional, Sequence

from ..diligence.benchmarks import (
    CashWaterfallReport, DivergenceStatus, KPIBundle, KPIResult,
    QOR_THRESHOLD_IMMATERIAL, QOR_THRESHOLD_WATCH,
)


# ── Metadata dataclass ──────────────────────────────────────────────

@dataclass
class QoEMemoMetadata:
    """Non-analytical fields that sit on the cover + sign-off page."""
    deal_name: Optional[str] = None
    target_entity: Optional[str] = None
    engagement_id: Optional[str] = None
    partner_name: Optional[str] = None
    preparer_name: Optional[str] = None
    as_of_label: Optional[str] = None
    confidentiality: str = (
        "Confidential. Prepared for the exclusive use of the named "
        "deal team. Distribution outside the firm is prohibited."
    )


# ── Public entry point ──────────────────────────────────────────────

def render_qoe_memo_html(
    *,
    bundle: KPIBundle,
    cash_waterfall: Optional[CashWaterfallReport] = None,
    repricing_report: Optional[Any] = None,
    risk_flags: Optional[Iterable[Any]] = None,
    diligence_questions: Optional[Iterable[Any]] = None,
    counterfactuals: Optional[Any] = None,
    metadata: Optional[QoEMemoMetadata] = None,
) -> str:
    """Render the full QoE memo as a printable HTML document.

    ``counterfactuals`` (optional) is a :class:`CounterfactualSet`
    produced by the counterfactual advisor. When supplied, each
    counterfactual renders as an entry in the Open Questions
    section under the 'What Would Change Our Mind' subheading —
    giving partners a signed memo that includes the walkaway /
    offer-modification levers."""
    meta = metadata or QoEMemoMetadata()

    title = meta.deal_name or meta.target_entity or "Target Entity (TBD)"
    as_of = meta.as_of_label or bundle.as_of_date.isoformat()

    sections = [
        _style_block(),
        _cover(title, meta, as_of),
        _executive_summary(bundle, cash_waterfall, meta),
        _qor_section(cash_waterfall),
        _kpi_snapshot(bundle),
        _denial_summary(bundle),
        _repricing_summary(repricing_report),
        _risk_flags_section(risk_flags),
        _diligence_questions_section(diligence_questions),
        _counterfactual_section(counterfactuals),
        _signoff_block(meta),
        _appendix(bundle, cash_waterfall, meta),
    ]

    body = "\n".join(s for s in sections if s)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f'  <title>QoE Memo — {html.escape(title)}</title>\n'
        "</head>\n"
        f'<body>\n{body}\n</body>\n</html>\n'
    )


# ── Section renderers ───────────────────────────────────────────────

def _style_block() -> str:
    return """<style>
/* QoE memo — print-first partner template. Inline styles are
   avoided on structural tags so Word ingestion is lossless; all
   presentation lives in this block. */
body {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 11pt;
    color: #1a1a1a;
    max-width: 7.5in;
    margin: 0 auto;
    padding: 0.75in 0.5in;
    line-height: 1.45;
}
h1 { font-size: 22pt; margin: 0 0 6pt 0; color: #0b2341; font-weight: 700; }
h2 { font-size: 14pt; margin: 18pt 0 4pt 0; color: #0b2341;
     border-bottom: 1px solid #c9b98a; padding-bottom: 2pt; font-weight: 700; }
h3 { font-size: 12pt; margin: 12pt 0 3pt 0; color: #2a2a2a; font-weight: 700; }
p { margin: 4pt 0 8pt 0; }
.eyebrow { font-size: 9pt; letter-spacing: 1.5pt; text-transform: uppercase;
           color: #6b5d3c; font-family: 'Helvetica Neue', Arial, sans-serif; }
.cover { page-break-after: always; padding-top: 2in; }
.cover-meta { margin-top: 1.5in; font-size: 10pt; color: #444; }
.cover-meta table { border: 0; }
.cover-meta td { padding: 3pt 12pt 3pt 0; vertical-align: top; }
.cover-meta td.label { color: #6b5d3c; text-transform: uppercase;
                       font-size: 9pt; letter-spacing: 1pt; }
.headline-card { border-left: 4pt solid #0b2341; padding: 8pt 14pt;
                 margin: 8pt 0 10pt 0; background: #f8f6f0; }
.headline-card.immaterial { border-left-color: #1f7a3a; background: #f0f7f2; }
.headline-card.watch      { border-left-color: #b07c1f; background: #fbf6ec; }
.headline-card.critical   { border-left-color: #b23a2d; background: #fbf0ee; }
.headline-card.unknown    { border-left-color: #6b5d3c; background: #f5f1ea; }
.headline-card .band {
    font-size: 9pt; font-weight: 700; letter-spacing: 1pt;
    text-transform: uppercase;
    font-family: 'Helvetica Neue', Arial, sans-serif;
}
.headline-card .headline { font-size: 13pt; font-weight: 700; margin: 2pt 0 4pt 0; }
.num { font-family: 'Courier New', monospace; }
table.data { width: 100%; border-collapse: collapse; font-size: 10pt;
             margin: 6pt 0 10pt 0; }
table.data th {
    text-align: left; border-bottom: 1pt solid #0b2341;
    padding: 4pt 6pt; font-size: 9pt; letter-spacing: 0.5pt;
    text-transform: uppercase; color: #6b5d3c;
    font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 700;
}
table.data td { padding: 4pt 6pt; border-bottom: 1px solid #e6dfca; }
table.data td.num { font-family: 'Courier New', monospace; text-align: right; }
.signature-block { margin-top: 28pt; padding: 14pt 0;
                   border-top: 1px solid #c9b98a; page-break-inside: avoid; }
.signature-line { display: inline-block; width: 3in;
                  border-bottom: 1pt solid #333; height: 18pt;
                  margin-right: 14pt; }
.footer { font-size: 8pt; color: #6b5d3c; margin-top: 28pt;
          padding-top: 6pt; border-top: 1px solid #c9b98a;
          font-family: 'Helvetica Neue', Arial, sans-serif; }
ul.findings { margin: 4pt 0 8pt 0; padding-left: 20pt; }
ul.findings li { margin: 3pt 0; }
.hedge { font-style: italic; color: #6b5d3c; }

@page { size: Letter; margin: 0.75in 0.5in; }
@media print {
    body { max-width: none; padding: 0; }
    h2 { page-break-after: avoid; }
    .signature-block { page-break-inside: avoid; }
}
</style>"""


def _cover(title: str, meta: QoEMemoMetadata, as_of: str) -> str:
    lines: List[str] = []
    lines.append(
        '<div class="cover">'
        '<div class="eyebrow">Quality of Earnings Memorandum</div>'
        f'<h1>{html.escape(title)}</h1>'
    )
    rows: List[tuple[str, str]] = []
    if meta.target_entity and meta.target_entity != title:
        rows.append(("Target entity", meta.target_entity))
    rows.append(("As-of date", as_of))
    if meta.engagement_id:
        rows.append(("Engagement", meta.engagement_id))
    if meta.partner_name:
        rows.append(("Partner", meta.partner_name))
    if meta.preparer_name:
        rows.append(("Prepared by", meta.preparer_name))
    rows.append(("Deliverable", "Partner-signed QoE memo (v1)"))

    rows_html = "".join(
        f'<tr><td class="label">{html.escape(lab)}</td>'
        f'<td>{html.escape(val)}</td></tr>'
        for lab, val in rows
    )
    lines.append(
        f'<div class="cover-meta"><table>{rows_html}</table></div>'
    )
    lines.append('</div>')
    return "".join(lines)


def _executive_summary(
    bundle: KPIBundle,
    waterfall: Optional[CashWaterfallReport],
    meta: QoEMemoMetadata,
) -> str:
    status = (
        waterfall.total_divergence_status if waterfall is not None
        else DivergenceStatus.UNKNOWN.value
    )
    band_css = status.lower()
    partner_copy = _partner_headline_copy(waterfall)

    # Delta numbers for the card.
    if waterfall is not None and waterfall.total_management_revenue_usd is not None:
        accrual = waterfall.total_accrual_revenue_usd or 0.0
        mgmt = waterfall.total_management_revenue_usd
        delta = waterfall.total_qor_divergence_usd or 0.0
        pct = waterfall.total_qor_divergence_pct or 0.0
        numbers = (
            f'<p class="num">Waterfall accrual '
            f'${accrual:,.0f}  ·  '
            f'Management accrual ${mgmt:,.0f}  ·  '
            f'Delta {"+" if delta >= 0 else "−"}${abs(delta):,.0f} '
            f'({pct*100:+.2f}%)</p>'
        )
    else:
        numbers = (
            '<p class="hedge">Management-reported revenue was not '
            'provided; this memo reports claims-side reconstruction '
            'only.</p>'
        )

    return (
        '<h2>1. Executive Summary</h2>'
        f'<div class="headline-card {band_css}">'
        f'  <div class="band">{html.escape(status)} — QoR Reconciliation</div>'
        f'  <div class="headline">{html.escape(partner_copy["headline"])}</div>'
        f'  <p>{html.escape(partner_copy["body"])}</p>'
        f'  {numbers}'
        '</div>'
    )


def _partner_headline_copy(waterfall: Optional[CashWaterfallReport]) -> dict:
    """Hand-authored partner voice for each banding state."""
    if waterfall is None or waterfall.total_divergence_status == \
            DivergenceStatus.UNKNOWN.value:
        return {
            "headline": "Claims-side reconstruction prepared; "
                        "management comparison not supplied.",
            "body": (
                "This memo contains the claims-side waterfall, KPI "
                "benchmarks, and denial stratification only. A management-"
                "reported revenue figure is required to produce a signed "
                "QoR reconciliation opinion."
            ),
        }
    if waterfall.total_divergence_status == DivergenceStatus.IMMATERIAL.value:
        return {
            "headline": "Management revenue ties to the claims-side "
                        "reconstruction within tolerance.",
            "body": (
                f"The waterfall-derived accrual revenue reconciles to "
                f"management's reported accrual within "
                f"{QOR_THRESHOLD_IMMATERIAL*100:,.0f}%. No partner-quotable "
                f"QoR finding. Recommend proceeding to the operational "
                f"levers in the EBITDA bridge."
            ),
        }
    if waterfall.total_divergence_status == DivergenceStatus.WATCH.value:
        return {
            "headline": "Management revenue diverges from the waterfall "
                        "within the watch band.",
            "body": (
                f"The divergence falls between "
                f"{QOR_THRESHOLD_IMMATERIAL*100:,.0f}% and "
                f"{QOR_THRESHOLD_WATCH*100:,.0f}%. Not a fatal finding, but "
                f"the accrual methodology warrants a follow-up question to "
                f"management before IC. This memo flags it rather than "
                f"resolves it."
            ),
        }
    # CRITICAL
    return {
        "headline": "Material QoR divergence — management revenue does "
                    "not tie to the claims-side reconstruction.",
        "body": (
            f"The waterfall-derived accrual revenue disagrees with "
            f"management's reported accrual by more than the "
            f"{QOR_THRESHOLD_WATCH*100:,.0f}% VMG/A&M QoR threshold. This "
            f"is a headline finding. Recommend a deep-dive on accrual "
            f"methodology, contractual adjustment calculation, and denial "
            f"reserve policy before IC. Do not close without an "
            f"explanation from management."
        ),
    }


def _qor_section(waterfall: Optional[CashWaterfallReport]) -> str:
    if waterfall is None:
        return (
            '<h2>2. Quality of Revenue</h2>'
            '<p class="hedge">No cash waterfall supplied to this memo. '
            'Attach a CashWaterfallReport to render the QoR section.</p>'
        )
    mature = waterfall.mature_cohorts()
    if not mature:
        return (
            '<h2>2. Quality of Revenue</h2>'
            f'<p class="hedge">No cohorts mature at as-of '
            f'{html.escape(waterfall.as_of_date.isoformat())} '
            f'(realization window '
            f'{waterfall.realization_window_days}d). No QoR section can '
            f'be signed on in-flight cohorts.</p>'
        )

    rows: List[str] = []
    for cohort in mature:
        for s in cohort.steps:
            is_terminal = s.name == "realized_cash"
            is_addback = s.name == "appeals_recovered"
            sign = "+" if is_addback else ("" if is_terminal else "−")
            rows.append(
                "<tr>"
                f"<td>{html.escape(cohort.cohort_month)}</td>"
                f"<td>{html.escape(s.label)}</td>"
                f"<td class=\"num\">{sign}${s.amount_usd:,.0f}</td>"
                f"<td class=\"num\">${s.running_balance_usd:,.0f}</td>"
                "</tr>"
            )
    return (
        '<h2>2. Quality of Revenue</h2>'
        "<p>Claim-level cascade from gross charges to realized cash, "
        "cohorted by date of service. Cohorts younger than "
        f"{waterfall.realization_window_days} days are censored and "
        "not included.</p>"
        '<table class="data">'
        "<thead><tr><th>Cohort</th><th>Step</th>"
        "<th>Amount</th><th>Running</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _kpi_snapshot(bundle: KPIBundle) -> str:
    def fmt(kpi: KPIResult) -> str:
        if kpi.value is None:
            return "—"
        if kpi.unit == "pct":
            return f"{kpi.value*100:,.1f}%"
        if kpi.unit == "days":
            return f"{kpi.value:,.1f}d"
        if kpi.unit == "ratio":
            return f"{kpi.value:,.3f}"
        return f"{kpi.value:,.2f}"

    rows = [
        ("Days in A/R", bundle.days_in_ar),
        ("First-Pass Denial Rate", bundle.first_pass_denial_rate),
        ("A/R Aging > 90 Days", bundle.ar_aging_over_90),
        ("Cost to Collect", bundle.cost_to_collect),
        ("Net Revenue Realization", bundle.net_revenue_realization),
    ]
    body: List[str] = []
    for label, kpi in rows:
        note = kpi.reason if kpi.value is None else f"n={kpi.sample_size}"
        body.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td class=\"num\">{fmt(kpi)}</td>"
            f"<td>{html.escape(note or '')}</td>"
            "</tr>"
        )
    return (
        '<h2>3. Revenue-Cycle KPI Snapshot</h2>'
        "<p>HFMA MAP Key metrics computed from the canonical claims "
        "dataset. A value of &quot;—&quot; indicates insufficient data; "
        "this memo does not interpolate.</p>"
        '<table class="data">'
        "<thead><tr><th>Metric</th><th>Value</th><th>Note</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table>"
    )


def _denial_summary(bundle: KPIBundle) -> str:
    rows = list(bundle.denial_stratification or ())
    if not rows:
        return ""
    total = sum(r.dollars_denied for r in rows) or 1.0
    body: List[str] = []
    for r in rows:
        body.append(
            "<tr>"
            f"<td>{html.escape(r.category)}</td>"
            f"<td class=\"num\">${r.dollars_denied:,.0f}</td>"
            f"<td class=\"num\">{r.count}</td>"
            f"<td class=\"num\">{r.dollars_denied/total*100:,.1f}%</td>"
            "</tr>"
        )
    return (
        '<h2>4. Denial Stratification</h2>'
        "<p>ANSI CARC categories by dollar impact.</p>"
        '<table class="data">'
        "<thead><tr><th>Category</th><th>Dollars</th>"
        "<th>Claims</th><th>Share</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table>"
    )


def _repricing_summary(report: Optional[Any]) -> str:
    if report is None:
        return ""
    rollups = getattr(report, "payer_rollups", None) or ()
    if not rollups:
        return ""
    body: List[str] = []
    for rp in rollups:
        payer = getattr(rp, "payer_class", None) or getattr(rp, "payer", "")
        leakage = getattr(rp, "leakage_usd", 0.0) or 0.0
        matched = getattr(rp, "matched_claim_count", 0)
        body.append(
            "<tr>"
            f"<td>{html.escape(str(payer))}</td>"
            f"<td class=\"num\">${leakage:,.0f}</td>"
            f"<td class=\"num\">{matched}</td>"
            "</tr>"
        )
    return (
        '<h2>5. Contract Re-Pricing</h2>'
        "<p>Leakage per payer class from the contract re-pricer. "
        "Positive leakage = contracted rate &gt; paid amount.</p>"
        '<table class="data">'
        "<thead><tr><th>Payer Class</th><th>Leakage</th>"
        "<th>Matched claims</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table>"
    )


def _risk_flags_section(flags: Optional[Iterable[Any]]) -> str:
    if not flags:
        return ""
    items: List[str] = []
    for f in flags:
        title = getattr(f, "title", None) or getattr(f, "category", "Risk")
        detail = (
            getattr(f, "detail", None)
            or getattr(f, "explanation", None)
            or getattr(f, "message", "")
        )
        sev = getattr(f, "severity", None)
        sev_text = sev.value if hasattr(sev, "value") else (
            str(sev) if sev is not None else ""
        )
        sev_prefix = f"<strong>[{html.escape(sev_text)}]</strong> " if sev_text else ""
        items.append(
            f"<li>{sev_prefix}"
            f"<strong>{html.escape(str(title))}</strong> — "
            f"{html.escape(str(detail))}</li>"
        )
    return (
        '<h2>6. Risk Flags</h2>'
        "<p>Partner-facing risks raised during diligence review.</p>"
        f'<ul class="findings">{"".join(items)}</ul>'
    )


def _diligence_questions_section(questions: Optional[Iterable[Any]]) -> str:
    if not questions:
        return ""
    items: List[str] = []
    for q in questions:
        text = getattr(q, "question", None) or getattr(q, "text", str(q))
        priority = getattr(q, "priority", None)
        pri_text = priority.value if hasattr(priority, "value") else (
            str(priority) if priority is not None else ""
        )
        context = getattr(q, "context", None) or getattr(q, "why", "")
        pri_prefix = f"<strong>[{html.escape(pri_text)}]</strong> " if pri_text else ""
        ctx_html = (
            f'<br><span class="hedge">Why it matters: '
            f'{html.escape(str(context))}</span>'
        ) if context else ""
        items.append(
            f"<li>{pri_prefix}{html.escape(str(text))}{ctx_html}</li>"
        )
    return (
        '<h2>7. Open Diligence Questions</h2>'
        "<p>P0 / P1 items requiring management response before IC.</p>"
        f'<ul class="findings">{"".join(items)}</ul>'
    )


def _counterfactual_section(cfs: Optional[Any]) -> str:
    """Render the counterfactual set as a 'What Would Change Our Mind'
    section. When the set is empty (or None), the section is
    suppressed entirely — the memo doesn't need to render an empty
    walkaway list."""
    if cfs is None:
        return ""
    items = getattr(cfs, "items", []) or []
    if not items:
        return ""
    rows: List[str] = []
    for cf in items:
        module = getattr(cf, "module", "") or ""
        orig = getattr(cf, "original_band", "") or ""
        target = getattr(cf, "target_band", "") or ""
        desc = getattr(cf, "change_description", "") or ""
        narrative = getattr(cf, "narrative", "") or ""
        implication = getattr(cf, "deal_structure_implication", "") or ""
        dollar = float(
            getattr(cf, "estimated_dollar_impact_usd", 0) or 0
        )
        feasibility = getattr(cf, "feasibility", "") or ""
        dollar_span = (
            f' Estimated savings: <strong>${dollar:,.0f}</strong>.'
            if dollar > 0 else " Dollar impact: qualitative."
        )
        rows.append(
            f"<li>"
            f"<strong>{html.escape(module)}</strong> "
            f"({html.escape(orig)} → {html.escape(target)}, "
            f"feasibility {html.escape(feasibility)}): "
            f"{html.escape(desc)}<br>"
            f"<span class='hedge'>{html.escape(narrative)}</span>"
            f"<br><span class='hedge'><strong>Deal structure:</strong> "
            f"{html.escape(implication)}</span>"
            f"{dollar_span}"
            f"</li>"
        )
    # Largest-lever callout.
    largest = getattr(cfs, "largest_lever", None)
    header = (
        "<p>Counterfactual analysis: the minimum change that flips "
        "each band to a better state. Partners use this section to "
        "shape offer terms, closing conditions, and walkaway "
        "criteria.</p>"
    )
    if largest is not None and largest.estimated_dollar_impact_usd > 0:
        header += (
            f"<p><strong>Largest lever:</strong> "
            f"{html.escape(largest.module)} — "
            f"{html.escape(largest.change_description)} "
            f"(savings ~${largest.estimated_dollar_impact_usd:,.0f}).</p>"
        )
    return (
        '<h2>8. What Would Change Our Mind</h2>'
        f'{header}'
        f'<ul class="findings">{"".join(rows)}</ul>'
    )


def _signoff_block(meta: QoEMemoMetadata) -> str:
    partner = meta.partner_name or ""
    preparer = meta.preparer_name or ""
    return (
        '<div class="signature-block">'
        '<h3>Partner Sign-Off</h3>'
        '<p>I have reviewed the claims-side reconstruction, the '
        'management reconciliation, and the open diligence items '
        'above. Signing below acknowledges the findings and authorises '
        'the memo for distribution within the named deal team.</p>'
        f'<p style="margin-top:28pt;">'
        f'<span class="signature-line"></span> '
        f'{html.escape(partner) if partner else "Partner signature"}'
        f'</p>'
        f'<p style="margin-top:18pt;">'
        f'<span class="signature-line"></span> Date'
        f'</p>'
        f'<p style="margin-top:18pt;" class="hedge">'
        f'Prepared by {html.escape(preparer) if preparer else "managing analyst"}'
        f'</p>'
        '</div>'
    )


def _appendix(
    bundle: KPIBundle,
    waterfall: Optional[CashWaterfallReport],
    meta: QoEMemoMetadata,
) -> str:
    lines: List[str] = []
    tv = bundle.days_in_ar.temporal
    claims_range = (
        f"{tv.claims_date_min or 'n/a'} → {tv.claims_date_max or 'n/a'}"
    )
    lines.append(
        '<h2>Appendix — Methodology &amp; Provenance</h2>'
        '<p>'
        'KPIs computed per HFMA MAP Key 2021 definitions. '
        'Waterfall accrual formula: gross charges − contractuals − '
        '(initial denials − appeals recovered) − bad debt; matches the '
        'VMG Health / A&amp;M Quality of Revenue convention. '
        'Status bands: IMMATERIAL &lt; '
        f'{QOR_THRESHOLD_IMMATERIAL*100:,.0f}%, WATCH '
        f'{QOR_THRESHOLD_IMMATERIAL*100:,.0f}–{QOR_THRESHOLD_WATCH*100:,.0f}%, '
        f'CRITICAL ≥ {QOR_THRESHOLD_WATCH*100:,.0f}%.'
        '</p>'
    )
    rows = [
        ("Claims date range", claims_range),
        ("As-of date", bundle.as_of_date.isoformat()),
        ("Provider ID", bundle.provider_id or "(unassigned)"),
    ]
    if waterfall is not None:
        rows.append(
            ("Realization window",
             f"{waterfall.realization_window_days} days")
        )
        rows.append(
            ("Mature cohorts", str(len(waterfall.mature_cohorts())))
        )
        rows.append(
            ("In-flight cohorts", str(len(waterfall.censored_cohorts())))
        )
    if meta.engagement_id:
        rows.append(("Engagement", meta.engagement_id))
    body = "".join(
        f'<tr><td>{html.escape(lab)}</td>'
        f'<td class="num">{html.escape(val)}</td></tr>'
        for lab, val in rows
    )
    lines.append(
        '<table class="data">'
        "<thead><tr><th>Item</th><th>Value</th></tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
    )
    lines.append(
        f'<div class="footer">{html.escape(meta.confidentiality)}</div>'
    )
    return "\n".join(lines)
