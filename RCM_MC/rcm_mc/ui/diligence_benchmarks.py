"""Phase 2 benchmarks tab renderer.

Three sections, one page:

  1. KPI scorecard — the four HFMA metrics vs benchmark bands.
  2. Cohort liquidation curves — one chart per payer class.
  3. Denial stratification Pareto — root causes sorted by dollars.

Whitespace first. One primary number per section. If a KPI is None
we render "Insufficient data" + the reason — never a fabricated
number.

This module does NOT reach into the CCD file system or trigger a
Phase 1 re-ingest; it is given a :class:`KPIBundle` and a
:class:`CohortLiquidationReport`. A bare call with no bundle renders
a placeholder page explaining how to attach a CCD.
"""
from __future__ import annotations

import html
from typing import Any, Dict, Iterable, List, Optional

from ..diligence.benchmarks import (
    CashWaterfallReport, CohortCell, CohortLiquidationReport,
    CohortStatus, DenialStratRow, DivergenceStatus, KPIBundle, KPIResult,
    QOR_THRESHOLD_IMMATERIAL, QOR_THRESHOLD_WATCH,
    WaterfallCohort, WaterfallStep,
)
from ._chartis_kit import P, chartis_shell


# HFMA benchmark bands. Ranges are partner-facing; sourced from HFMA
# MAP Key 2021 benchmark reports for acute care. A future refinement
# will carry bands by hospital archetype from the brain's archetype
# registry — for now, the acute-hospital defaults are explicit so the
# number an analyst sees is always the one we used to colour the row.
_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "days_in_ar": {
        "label": "Days in A/R",
        "top_quartile_max": 35.0,
        "median": 45.0,
        "bottom_quartile_min": 55.0,
        "unit": "days",
        "better": "lower",
    },
    "first_pass_denial_rate": {
        "label": "First-Pass Denial Rate",
        "top_quartile_max": 0.05,
        "median": 0.10,
        "bottom_quartile_min": 0.15,
        "unit": "pct",
        "better": "lower",
    },
    "ar_aging_over_90": {
        "label": "A/R Aging > 90 Days",
        "top_quartile_max": 0.15,
        "median": 0.25,
        "bottom_quartile_min": 0.35,
        "unit": "pct",
        "better": "lower",
    },
    "cost_to_collect": {
        "label": "Cost to Collect",
        "top_quartile_max": 0.025,
        "median": 0.035,
        "bottom_quartile_min": 0.045,
        "unit": "ratio",
        "better": "lower",
    },
    "net_revenue_realization": {
        "label": "Net Revenue Realization",
        "top_quartile_max": 0.98,     # inverse — top quartile HIGH
        "median": 0.95,
        "bottom_quartile_min": 0.90,
        "unit": "pct",
        "better": "higher",
    },
}


# ── Public entry points ─────────────────────────────────────────────

def render_benchmarks_page(
    bundle: Optional[KPIBundle] = None,
    cohort_report: Optional[CohortLiquidationReport] = None,
    cash_waterfall: Optional[CashWaterfallReport] = None,
) -> str:
    """Render the full Phase 2 page.

    When ``bundle`` is None, render the placeholder that was in
    ``_pages.render_benchmarks_page`` — a partner hasn't attached a
    CCD yet, so there's nothing to compute against.

    ``cash_waterfall`` is optional: when supplied, the Quality of
    Revenue section renders as the headline (section #1) above the
    KPI scorecard. The QoR waterfall is the partner's headline
    exhibit — KPIs and cohorts support it, not the other way
    around. Absent, the section is skipped silently.
    """
    if bundle is None:
        return _placeholder_page()

    body = (
        _hero(bundle)
        + _cash_waterfall_section(cash_waterfall)
        + _kpi_scorecard(bundle)
        + _cohort_section(cohort_report)
        + _denial_pareto(bundle.denial_stratification)
        + _provenance_footer(bundle)
    )
    return chartis_shell(
        body,
        "RCM Diligence — Benchmarks",
        subtitle=f"Phase 2 of 4 · as-of {bundle.as_of_date.isoformat()}",
    )


# ── Section builders ────────────────────────────────────────────────

def _placeholder_page() -> str:
    body = (
        f'<div style="padding:24px 0 12px 0;">'
        f'  <div style="font-size:11px;color:{P["text_faint"]};letter-spacing:.75px;'
        f'text-transform:uppercase;margin-bottom:6px;">RCM Diligence Workspace</div>'
        f'  <div style="font-size:20px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:8px;">Phase 2 — KPI Benchmarking & Stress Testing</div>'
        f'  <div style="font-size:13px;color:{P["text_dim"]};max-width:720px;'
        f'line-height:1.55;">Attach a Canonical Claims Dataset in '
        f'<a href="/diligence/ingest" style="color:{P["accent"]};">Phase 1</a> '
        f'to populate the KPI scorecard, cohort liquidation curves, and denial '
        f'stratification Pareto on this tab.</div>'
        f'</div>'
    )
    return chartis_shell(body, "RCM Diligence — Benchmarks",
                        subtitle="Phase 2 of 4")


def _hero(bundle: KPIBundle) -> str:
    # Primary number: Days in A/R (the one metric every CFO reads first).
    dar = bundle.days_in_ar
    if dar.value is not None:
        primary_num = f"{dar.value:,.1f}"
        primary_unit = "days"
    else:
        primary_num = "—"
        primary_unit = "insufficient data"
    return (
        f'<div style="padding:32px 0 16px 0;">'
        f'  <div style="font-size:10px;color:{P["text_faint"]};letter-spacing:1px;'
        f'text-transform:uppercase;margin-bottom:12px;">Primary KPI</div>'
        f'  <div style="display:flex;align-items:baseline;gap:12px;">'
        f'    <div style="font-size:56px;color:{P["text"]};font-weight:300;'
        f'font-family:\'JetBrains Mono\',monospace;font-variant-numeric:tabular-nums;">'
        f'{primary_num}</div>'
        f'    <div style="font-size:14px;color:{P["text_dim"]};">{primary_unit} · {html.escape(dar.citation)}</div>'
        f'  </div>'
        f'  <div style="font-size:12px;color:{P["text_faint"]};margin-top:4px;">'
        f'  n={dar.sample_size} · {html.escape(dar.reason or "")}'
        f'  </div>'
        f'</div>'
    )


def _kpi_scorecard(bundle: KPIBundle) -> str:
    cards = [
        _kpi_card("days_in_ar", bundle.days_in_ar),
        _kpi_card("first_pass_denial_rate", bundle.first_pass_denial_rate),
        _kpi_card("ar_aging_over_90", bundle.ar_aging_over_90),
        _kpi_card("cost_to_collect", bundle.cost_to_collect),
        _kpi_card("net_revenue_realization", bundle.net_revenue_realization),
        _lag_card(bundle.lag_service_to_bill, "Service → Bill Lag"),
        _lag_card(bundle.lag_bill_to_cash, "Bill → Cash Lag"),
    ]
    return (
        f'<h2 style="font-size:11px;letter-spacing:1px;text-transform:uppercase;'
        f'color:{P["text_dim"]};margin:32px 0 12px 0;">KPI Scorecard</h2>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));'
        f'gap:12px;">{"".join(cards)}</div>'
    )


def _kpi_card(key: str, kpi: KPIResult) -> str:
    band = _BENCHMARKS.get(key, {})
    label = band.get("label", kpi.name)
    if kpi.value is None:
        value_str = "—"
        color = P["text_faint"]
        band_label = "Insufficient data"
        reason = kpi.reason or ""
    else:
        value_str = _format_value(kpi.value, kpi.unit)
        color = _colour_for(kpi.value, band)
        band_label = _band_label(kpi.value, band)
        reason = f"n={kpi.sample_size}"
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;padding:14px 16px;">'
        f'  <div style="font-size:10px;color:{P["text_faint"]};letter-spacing:.5px;'
        f'text-transform:uppercase;margin-bottom:10px;">{html.escape(label)}</div>'
        f'  <div style="font-family:\'JetBrains Mono\',monospace;'
        f'font-variant-numeric:tabular-nums;font-size:26px;color:{color};">'
        f'{value_str}</div>'
        f'  <div style="font-size:10px;color:{P["text_dim"]};margin-top:6px;">'
        f'{html.escape(band_label)}</div>'
        f'  <div style="font-size:10px;color:{P["text_faint"]};margin-top:4px;">'
        f'{html.escape(reason)}</div>'
        f'</div>'
    )


def _lag_card(kpi: KPIResult, label: str) -> str:
    if kpi.value is None:
        value_str, color = "—", P["text_faint"]
        extra = kpi.reason or ""
    else:
        value_str = f"{kpi.value:,.0f}d"
        color = P["text"]
        extra = f"p25={kpi.numerator:,.0f}d  p75={kpi.denominator:,.0f}d  n={kpi.sample_size}"
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;padding:14px 16px;">'
        f'  <div style="font-size:10px;color:{P["text_faint"]};letter-spacing:.5px;'
        f'text-transform:uppercase;margin-bottom:10px;">{html.escape(label)}</div>'
        f'  <div style="font-family:\'JetBrains Mono\',monospace;'
        f'font-variant-numeric:tabular-nums;font-size:26px;color:{color};">{value_str}</div>'
        f'  <div style="font-size:10px;color:{P["text_dim"]};margin-top:6px;">'
        f'{html.escape(extra)}</div>'
        f'</div>'
    )


def _format_value(value: float, unit: str) -> str:
    if unit == "pct":
        return f"{value * 100:,.1f}%"
    if unit == "days":
        return f"{value:,.1f}d"
    if unit == "ratio":
        return f"{value:,.3f}"
    return f"{value:,.2f}"


def _colour_for(value: float, band: Dict[str, Any]) -> str:
    if not band:
        return P["text"]
    better = band.get("better", "lower")
    if better == "lower":
        if value <= band["top_quartile_max"]:
            return P["positive"]
        if value >= band["bottom_quartile_min"]:
            return P["negative"]
        return P["warning"]
    # higher is better
    if value >= band["top_quartile_max"]:
        return P["positive"]
    if value <= band["bottom_quartile_min"]:
        return P["negative"]
    return P["warning"]


def _band_label(value: float, band: Dict[str, Any]) -> str:
    if not band:
        return ""
    better = band.get("better", "lower")
    unit = band.get("unit", "")
    def fmt(v):
        if unit == "pct": return f"{v*100:,.1f}%"
        if unit == "days": return f"{v:,.0f}d"
        if unit == "ratio": return f"{v:,.3f}"
        return f"{v:,.2f}"
    if better == "lower":
        if value <= band["top_quartile_max"]:
            return f"top quartile (≤ {fmt(band['top_quartile_max'])})"
        if value <= band["median"]:
            return f"above median ({fmt(band['median'])})"
        if value <= band["bottom_quartile_min"]:
            return f"below median ({fmt(band['median'])})"
        return f"bottom quartile (≥ {fmt(band['bottom_quartile_min'])})"
    if value >= band["top_quartile_max"]:
        return f"top quartile (≥ {fmt(band['top_quartile_max'])})"
    if value >= band["median"]:
        return f"above median ({fmt(band['median'])})"
    if value >= band["bottom_quartile_min"]:
        return f"below median ({fmt(band['median'])})"
    return f"bottom quartile (≤ {fmt(band['bottom_quartile_min'])})"


def _cohort_section(report: Optional[CohortLiquidationReport]) -> str:
    if report is None:
        return ""
    all_mature = report.mature_cells()
    censored = report.censored_cells()
    rows_html = []
    for cell in all_mature + censored:
        cls_colour = (P["text"] if cell.status == CohortStatus.MATURE
                      else P["text_faint"])
        value_str = (
            f"{(cell.cumulative_liquidation_pct or 0) * 100:,.1f}%"
            if cell.cumulative_liquidation_pct is not None else "—"
        )
        rows_html.append(
            '<tr>'
            f'<td class="mono">{html.escape(cell.cohort_month)}</td>'
            f'<td class="num">{cell.days_since_dos}d</td>'
            f'<td class="num">{cell.cohort_size_claims}</td>'
            f'<td class="num" style="color:{cls_colour};">{value_str}</td>'
            f'<td>{html.escape(cell.status.value)}</td>'
            f'<td style="font-size:10px;color:{P["text_faint"]};">'
            f'{html.escape(cell.reason or "")}</td>'
            '</tr>'
        )
    return (
        f'<h2 style="font-size:11px;letter-spacing:1px;text-transform:uppercase;'
        f'color:{P["text_dim"]};margin:36px 0 12px 0;">Cohort Liquidation</h2>'
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;padding:12px 16px;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};margin-bottom:8px;">'
        f'Mature cohorts: {len(all_mature)}  ·  '
        f'In-flight (censored): {len(censored)}  ·  '
        f'Windows: {", ".join(str(w) + "d" for w in report.window_days)}'
        f'</div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px;">'
        f'<thead><tr style="color:{P["text_dim"]};">'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Cohort</th>'
        f'<th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Window</th>'
        f'<th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Claims</th>'
        f'<th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Liquidation</th>'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Status</th>'
        f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Note</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        f'</table>'
        f'</div>'
    )


def _denial_pareto(rows: Iterable[DenialStratRow]) -> str:
    row_list = list(rows)
    if not row_list:
        return ""
    total = sum(r.dollars_denied for r in row_list) or 1.0
    items = []
    for r in row_list:
        pct = r.dollars_denied / total
        bar_width = max(pct * 100, 2)
        items.append(
            f'<div style="margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:11px;color:{P["text_dim"]};margin-bottom:2px;">'
            f'<span>{html.escape(r.category)}</span>'
            f'<span class="mono">${r.dollars_denied:,.0f}  ·  '
            f'{r.count} claims  ·  {r.pct_of_total_denied*100:,.1f}%</span>'
            f'</div>'
            f'<div style="background:{P["panel_alt"]};height:4px;border-radius:2px;'
            f'overflow:hidden;">'
            f'<div style="background:{P["accent"]};height:100%;width:{bar_width}%;"></div>'
            f'</div>'
            f'</div>'
        )
    return (
        f'<h2 style="font-size:11px;letter-spacing:1px;text-transform:uppercase;'
        f'color:{P["text_dim"]};margin:36px 0 12px 0;">Denial Stratification</h2>'
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;padding:14px 16px;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};margin-bottom:12px;">'
        f'ANSI CARC categories by dollar impact. Drill-through to underlying '
        f'claim rows is available via <a href="/diligence/root-cause" '
        f'style="color:{P["accent"]};">Phase 3 — Root Cause</a>.'
        f'</div>'
        f'{"".join(items)}'
        f'</div>'
    )


def _cash_waterfall_section(report: Optional[CashWaterfallReport]) -> str:
    """Headline section: Quality of Revenue / Cash Waterfall.

    Renders in this order:
      1. Management reconciliation summary card — IMMATERIAL / WATCH
         / CRITICAL band against management-reported accrual revenue,
         plus the dollar delta.
      2. Top-line realization metrics (cash / gross / cohort counts).
      3. Cohort × step cascade table (ALL-payers).
      4. Per-payer-class breakout — one compact row per payer class
         summarising gross → accrual → cash so a partner sees which
         payer mix is driving the top-line divergence.

    Rendering never fabricates: if a management number was not
    supplied, the card renders "not supplied" and the status is
    UNKNOWN. In-flight cohorts show claim counts but no realization.
    """
    if report is None:
        return ""
    mature = report.mature_cohorts()
    censored = report.censored_cohorts()

    mgmt_card = _management_reconciliation_card(report)

    # Top-line summary.
    realization_str = (
        f"{report.total_realization_rate * 100:,.1f}%"
        if report.total_realization_rate is not None else "—"
    )
    topline = (
        f'<div style="display:flex;align-items:baseline;gap:16px;margin:12px 0 8px 0;">'
        f'  <div style="font-size:10px;color:{P["text_faint"]};letter-spacing:.5px;'
        f'text-transform:uppercase;">Realization Rate</div>'
        f'  <div style="font-size:24px;color:{P["text"]};'
        f'font-family:\'JetBrains Mono\',monospace;font-variant-numeric:tabular-nums;'
        f'font-weight:500;">{realization_str}</div>'
        f'  <div style="font-size:11px;color:{P["text_faint"]};">'
        f'${report.total_realized_cash_usd:,.0f} of ${report.total_gross_charges_usd:,.0f} '
        f'gross · {len(mature)} mature cohort(s)'
        f'{", " + str(len(censored)) + " in-flight" if censored else ""}</div>'
        f'</div>'
    )

    # Cascade table. One row per cohort × step; ALL-payers roll-up.
    if not mature:
        body_rows = (
            f'<tr><td colspan="5" style="padding:12px;color:{P["text_faint"]};'
            f'font-style:italic;">No mature cohorts at as-of '
            f'{report.as_of_date.isoformat()}.</td></tr>'
        )
    else:
        parts: list[str] = []
        for cohort in mature:
            for s in cohort.steps:
                is_terminal = s.name == "realized_cash"
                is_addback = s.name == "appeals_recovered"
                row_colour = (
                    P["positive"] if is_terminal
                    else P["text_dim"] if is_addback
                    else P["text"]
                )
                sign = "+" if is_addback else ("" if is_terminal else "−")
                parts.append(
                    '<tr>'
                    f'<td class="mono">{html.escape(cohort.cohort_month)}</td>'
                    f'<td style="color:{row_colour};">{html.escape(s.label)}</td>'
                    f'<td class="num" style="color:{row_colour};">'
                    f'{sign}${s.amount_usd:,.0f}</td>'
                    f'<td class="num" style="color:{P["text_dim"]};">'
                    f'${s.running_balance_usd:,.0f}</td>'
                    f'<td class="num" style="color:{P["text_faint"]};font-size:10px;">'
                    f'{s.claim_count}</td>'
                    '</tr>'
                )
            # Per-cohort divergence status badge row (when we have a
            # management number to compare against).
            if cohort.management_reported_revenue_usd is not None:
                badge_colour, _ = _status_palette(cohort.divergence_status)
                pct = cohort.qor_divergence_pct or 0.0
                parts.append(
                    '<tr>'
                    f'<td class="mono">{html.escape(cohort.cohort_month)}</td>'
                    f'<td style="color:{badge_colour};font-weight:600;">'
                    f'Reconciliation · {html.escape(cohort.divergence_status)}</td>'
                    f'<td class="num" style="color:{badge_colour};">'
                    f'{pct*100:+.1f}%</td>'
                    f'<td class="num" style="color:{P["text_dim"]};">'
                    f'mgmt ${cohort.management_reported_revenue_usd:,.0f}</td>'
                    f'<td></td>'
                    '</tr>'
                )
        body_rows = "".join(parts)

    per_class = _per_payer_class_table(report)

    return (
        f'<h2 style="font-size:11px;letter-spacing:1px;text-transform:uppercase;'
        f'color:{P["text_dim"]};margin:32px 0 12px 0;">Quality of Revenue (Cash Waterfall)</h2>'
        f'{mgmt_card}'
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;padding:14px 16px;margin-top:12px;">'
        f'  <div style="font-size:11px;color:{P["text_faint"]};margin-bottom:4px;">'
        f'  Claim-level cascade from gross charges to realized cash, cohorted '
        f'by date of service. Cohorts younger than '
        f'{report.realization_window_days} days are marked '
        f'<em>insufficient data</em> — never fabricated. Drill-through to '
        f'underlying claim_ids is available in '
        f'<a href="/diligence/root-cause" style="color:{P["accent"]};">Phase 3</a>.'
        f'  </div>'
        f'  {topline}'
        f'  <table style="width:100%;border-collapse:collapse;font-size:11px;margin-top:8px;">'
        f'    <thead><tr style="color:{P["text_dim"]};">'
        f'      <th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Cohort</th>'
        f'      <th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Step</th>'
        f'      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Amount</th>'
        f'      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Running</th>'
        f'      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">n</th>'
        f'    </tr></thead>'
        f'    <tbody>{body_rows}</tbody>'
        f'  </table>'
        f'</div>'
        f'{per_class}'
    )


# ── QoR helpers ─────────────────────────────────────────────────────

_STATUS_COPY = {
    DivergenceStatus.IMMATERIAL.value: (
        "Reconciled",
        f"Waterfall-derived accrual revenue matches management within "
        f"{QOR_THRESHOLD_IMMATERIAL*100:,.0f}%. No finding.",
    ),
    DivergenceStatus.WATCH.value: (
        "Watch",
        f"Divergence between {QOR_THRESHOLD_IMMATERIAL*100:,.0f}% and "
        f"{QOR_THRESHOLD_WATCH*100:,.0f}%. Worth a follow-up question on "
        f"accrual methodology.",
    ),
    DivergenceStatus.CRITICAL.value: (
        "Critical",
        f"Divergence ≥ {QOR_THRESHOLD_WATCH*100:,.0f}% — the claims-side "
        f"reconstruction disagrees with management's reported revenue by "
        f"more than the VMG/A&M QoR threshold. Partner-quotable finding.",
    ),
    DivergenceStatus.UNKNOWN.value: (
        "Not supplied",
        "Management-reported accrual revenue was not provided, so no "
        "reconciliation was attempted.",
    ),
}


def _status_palette(status: str) -> tuple[str, str]:
    """Return ``(text_colour, tint_background)`` for a status label."""
    if status == DivergenceStatus.IMMATERIAL.value:
        return P["positive"], "rgba(16,185,129,.12)"
    if status == DivergenceStatus.WATCH.value:
        return P["warning"], "rgba(245,158,11,.14)"
    if status == DivergenceStatus.CRITICAL.value:
        return P["negative"], "rgba(239,68,68,.14)"
    return P["text_faint"], P["panel_alt"]


def _management_reconciliation_card(report: CashWaterfallReport) -> str:
    """Headline card above the cascade table: divergence band, delta,
    and the human copy a partner can drop into a memo."""
    status = report.total_divergence_status
    title, copy = _STATUS_COPY.get(status, _STATUS_COPY[DivergenceStatus.UNKNOWN.value])
    colour, tint = _status_palette(status)

    accrual = report.total_accrual_revenue_usd
    mgmt = report.total_management_revenue_usd
    delta = report.total_qor_divergence_usd
    pct = report.total_qor_divergence_pct

    if status == DivergenceStatus.UNKNOWN.value or mgmt is None:
        numbers_html = (
            f'<div style="font-size:11px;color:{P["text_faint"]};">'
            f'Waterfall accrual: <span class="mono" style="color:{P["text_dim"]};">'
            f'${(accrual or 0):,.0f}</span>'
            f'</div>'
        )
    else:
        pct_str = f"{pct*100:+.1f}%" if pct is not None else "n/a"
        delta_str = f"{'+' if (delta or 0) >= 0 else '−'}${abs(delta or 0):,.0f}"
        numbers_html = (
            f'<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:11px;'
            f'color:{P["text_dim"]};margin-top:2px;">'
            f'  <div>Waterfall accrual '
            f'<span class="mono" style="color:{P["text"]};">${accrual:,.0f}</span></div>'
            f'  <div>Management accrual '
            f'<span class="mono" style="color:{P["text"]};">${mgmt:,.0f}</span></div>'
            f'  <div>Delta '
            f'<span class="mono" style="color:{colour};">{delta_str} '
            f'({pct_str})</span></div>'
            f'</div>'
        )

    return (
        f'<div style="background:{tint};border:1px solid {colour};'
        f'border-left:3px solid {colour};border-radius:4px;'
        f'padding:14px 18px;margin-top:4px;">'
        f'  <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
        f'    <div style="font-size:10px;color:{colour};font-weight:700;'
        f'letter-spacing:1.5px;text-transform:uppercase;">{html.escape(status)}</div>'
        f'    <div style="font-size:15px;color:{P["text"]};font-weight:600;">'
        f'{html.escape(title)}</div>'
        f'  </div>'
        f'  <div style="font-size:12px;color:{P["text_dim"]};max-width:780px;'
        f'line-height:1.5;">{html.escape(copy)}</div>'
        f'  {numbers_html}'
        f'</div>'
    )


def _per_payer_class_table(report: CashWaterfallReport) -> str:
    """Per-payer-class summary table. One row per class: gross,
    contractuals, denials (net of appeals), bad debt, accrual,
    realized, and realization rate. Payers with only in-flight
    cohorts show "in-flight" instead of numbers."""
    if not report.cohorts_by_payer_class:
        return ""

    def _class_totals(cohorts: List[WaterfallCohort]) -> Optional[Dict[str, float]]:
        mature = [c for c in cohorts if c.status == CohortStatus.MATURE]
        if not mature:
            return None
        totals = {
            "gross": 0.0, "contractual": 0.0, "front_end": 0.0,
            "denials_net": 0.0, "bad_debt": 0.0,
            "accrual": 0.0, "cash": 0.0,
        }
        step_lookup = {
            "contractual_adjustments": "contractual",
            "front_end_leakage": "front_end",
            "bad_debt": "bad_debt",
        }
        for c in mature:
            totals["gross"] += c.gross_charges_usd
            totals["cash"] += c.realized_cash_usd
            totals["accrual"] += (c.accrual_revenue_usd or 0.0)
            init_denied = 0.0
            recovered = 0.0
            for s in c.steps:
                key = step_lookup.get(s.name)
                if key is not None:
                    totals[key] += s.amount_usd
                elif s.name == "initial_denials_gross":
                    init_denied += s.amount_usd
                elif s.name == "appeals_recovered":
                    recovered += s.amount_usd
            totals["denials_net"] += max(init_denied - recovered, 0.0)
        return totals

    rows: List[str] = []
    for pc in sorted(report.cohorts_by_payer_class.keys()):
        cohorts = report.cohorts_by_payer_class[pc]
        t = _class_totals(cohorts)
        if t is None:
            in_flight = len([c for c in cohorts
                             if c.status == CohortStatus.INSUFFICIENT_DATA])
            rows.append(
                '<tr>'
                f'<td class="mono" style="color:{P["text"]};">{html.escape(pc)}</td>'
                f'<td colspan="6" style="color:{P["text_faint"]};font-style:italic;">'
                f'{in_flight} cohort(s) in-flight — insufficient data'
                f'</td>'
                '</tr>'
            )
            continue
        rate = (t["cash"] / t["gross"]) if t["gross"] > 0 else None
        rate_str = f"{rate*100:,.1f}%" if rate is not None else "—"
        rows.append(
            '<tr>'
            f'<td class="mono" style="color:{P["text"]};">{html.escape(pc)}</td>'
            f'<td class="num">${t["gross"]:,.0f}</td>'
            f'<td class="num" style="color:{P["text_dim"]};">'
            f'−${t["contractual"]:,.0f}</td>'
            f'<td class="num" style="color:{P["text_dim"]};">'
            f'−${t["denials_net"]:,.0f}</td>'
            f'<td class="num" style="color:{P["text_dim"]};">'
            f'−${t["bad_debt"]:,.0f}</td>'
            f'<td class="num" style="color:{P["text"]};">${t["accrual"]:,.0f}</td>'
            f'<td class="num" style="color:{P["positive"]};">{rate_str}</td>'
            '</tr>'
        )

    return (
        f'<div style="margin-top:16px;background:{P["panel"]};'
        f'border:1px solid {P["border"]};border-radius:4px;padding:14px 16px;">'
        f'  <div style="font-size:10px;color:{P["text_faint"]};letter-spacing:1px;'
        f'text-transform:uppercase;margin-bottom:8px;">By Payer Class</div>'
        f'  <table style="width:100%;border-collapse:collapse;font-size:11px;">'
        f'    <thead><tr style="color:{P["text_dim"]};">'
        f'      <th style="text-align:left;padding:6px 8px;border-bottom:1px solid {P["border"]};">Payer Class</th>'
        f'      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Gross</th>'
        f'      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Contractuals</th>'
        f'      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Denials (net)</th>'
        f'      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Bad Debt</th>'
        f'      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Accrual</th>'
        f'      <th style="text-align:right;padding:6px 8px;border-bottom:1px solid {P["border"]};">Realization</th>'
        f'    </tr></thead>'
        f'    <tbody>{"".join(rows)}</tbody>'
        f'  </table>'
        f'</div>'
    )


def _provenance_footer(bundle: KPIBundle) -> str:
    tv = bundle.days_in_ar.temporal
    events = tv.overlapping_events
    events_str = ""
    if events:
        names = "; ".join(e.name for e in events)
        events_str = (
            f'<span style="color:{P["warning"]};">'
            f'regulatory overlap: {html.escape(names)}</span>'
        )
    return (
        f'<div style="margin-top:40px;padding-top:16px;border-top:1px solid {P["border"]};'
        f'color:{P["text_faint"]};font-size:10px;font-family:\'JetBrains Mono\',monospace;">'
        f'claims range: {html.escape(tv.claims_date_min or "n/a")} → '
        f'{html.escape(tv.claims_date_max or "n/a")}  ·  '
        f'as_of: {bundle.as_of_date.isoformat()}  ·  '
        f'provider_id: {html.escape(bundle.provider_id or "(unassigned)")}  '
        f'{events_str}'
        f'</div>'
    )
