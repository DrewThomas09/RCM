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
from ._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_next_section, ck_page_title,
    ck_panel, ck_section_header, ck_section_intro, ck_signal_badge,
)


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

_DB_STYLES = f"""
<style>
.db-card-grid{{display:grid;
grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;}}
.db-kpi-card{{background:{P["panel"]};border:1px solid {P["border"]};
border-radius:4px;padding:14px 16px;}}
.db-kpi-label{{font-size:10px;color:{P["text_faint"]};letter-spacing:.5px;
text-transform:uppercase;margin-bottom:10px;}}
.db-kpi-value{{font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-size:26px;line-height:1;}}
.db-kpi-band{{font-size:10px;margin-top:6px;font-weight:600;}}
.db-kpi-peer{{font-size:10px;margin-top:3px;color:{P["text_faint"]};}}
.db-kpi-reason{{font-size:10px;color:{P["text_faint"]};margin-top:4px;}}
.db-lag-extra{{font-size:10px;color:{P["text_dim"]};margin-top:6px;}}
.db-pareto-row{{margin-bottom:8px;}}
.db-pareto-meta{{display:flex;justify-content:space-between;
font-size:11px;color:{P["text_dim"]};margin-bottom:2px;}}
.db-pareto-track{{background:{P["panel_alt"]};height:4px;border-radius:2px;overflow:hidden;}}
.db-pareto-fill{{background:{P["accent"]};height:100%;}}
</style>
"""


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

    page_title = ck_page_title(
        "Benchmarks",
        eyebrow="RCM DILIGENCE",
        meta=(
            f"Phase 2 of 4 · as-of {bundle.as_of_date.isoformat()}"
        ),
    )
    body = (
        _DB_STYLES
        + page_title
        + _hero(bundle)
        + _cash_waterfall_section(cash_waterfall)
        + _kpi_scorecard(bundle)
        + _cohort_section(cohort_report)
        + _denial_pareto(bundle.denial_stratification)
        + _provenance_footer(bundle)
        + ck_next_section(
            "Open the bridge auditor",
            "/diligence/bridge-audit",
            eyebrow="Continue —",
            italic_word="bridge",
        )
    )
    return chartis_shell(
        body,
        "RCM Diligence — Benchmarks",
        active_nav="/diligence/benchmarks",
        subtitle=f"Phase 2 of 4 · as-of {bundle.as_of_date.isoformat()}",
    )


# ── Section builders ────────────────────────────────────────────────

def _placeholder_page() -> str:
    intro = ck_section_intro(
        eyebrow="RCM Diligence Workspace",
        headline="Phase 2 — KPI Benchmarking & Stress Testing.",
        italic_word="Stress",
        body=(
            "Attach a Canonical Claims Dataset in Phase 1 to "
            "populate the KPI scorecard, cohort liquidation curves, "
            "and denial stratification Pareto on this tab."
        ),
    )
    body = intro + ck_panel(
        '<p class="ck-section-body">'
        '<a href="/diligence/ingest" class="cad-btn cad-btn-primary">'
        '→ Phase 1: Ingest a CCD</a></p>',
        title="Next step",
    )
    return chartis_shell(body, "RCM Diligence — Benchmarks",
                        subtitle="Phase 2 of 4")


def _hero(bundle: KPIBundle) -> str:
    # Primary number: Days in A/R (the one metric every CFO reads first).
    dar = bundle.days_in_ar
    band = _BENCHMARKS.get("days_in_ar", {})
    peer_median = band.get("median")
    if dar.value is not None:
        primary_num = f"{dar.value:,.1f}"
        primary_unit = "days"
        color = _colour_for(dar.value, band)
        band_label = _band_label(dar.value, band)
        if peer_median is not None:
            delta = dar.value - peer_median
            delta_txt = (
                f'{delta:+.1f} days vs HFMA peer median '
                f'{peer_median:.0f}d'
            )
            if delta < 0:
                summary = (
                    f"Claims are converting to cash faster than the "
                    f"HFMA acute-hospital peer median ({peer_median:.0f} days). "
                    f"This target's working capital efficiency is "
                    f"above average — fewer dollars tied up in unpaid "
                    f"claims than comparable hospitals."
                )
            elif delta > 10:
                summary = (
                    f"Days in A/R is {delta:.0f} days slower than the "
                    f"HFMA acute-hospital peer median ({peer_median:.0f} days). "
                    f"Every 10 days of elevated A/R is roughly 2.7% of "
                    f"annual revenue sitting in working capital — an "
                    f"EBITDA-bridge opportunity when modeled at the "
                    f"cost-of-capital rate."
                )
            else:
                summary = (
                    f"Days in A/R is within the HFMA acute-hospital "
                    f"peer median range ({peer_median:.0f}d ± 10). "
                    f"Working capital is neither a strength nor a bridge "
                    f"lever — look elsewhere (denials, Medicare mix) "
                    f"for upside."
                )
        else:
            delta_txt = ""
            summary = ""
    else:
        primary_num = "—"
        primary_unit = "insufficient data"
        color = P["text_faint"]
        band_label = "Insufficient data"
        delta_txt = ""
        summary = (
            "The CCD does not contain enough submit-date / paid-date "
            "pairs to compute days-in-A/R. Typically occurs when claim "
            "lifecycle fields weren't extracted from the source EMR."
        )

    summary_html = (
        '<p class="ck-section-body">'
        f'<strong>What this shows: </strong>{html.escape(summary)}</p>'
    ) if summary else ""

    intro = ck_section_intro(
        eyebrow="Primary KPI · Days in A/R",
        headline=f"{primary_num} {primary_unit}.",
        italic_word=primary_unit,
        body=(
            f"{html.escape(band_label)}"
            + (f" · {html.escape(delta_txt)}" if delta_txt else "")
            + f" · n={dar.sample_size} claims · {html.escape(dar.reason or '')}"
        ),
    )
    return f"{intro}{summary_html}"


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
        ck_section_header("KPI Scorecard", eyebrow="PHASE 2")
        + f'<div class="db-card-grid">{"".join(cards)}</div>'
    )


def _kpi_card(key: str, kpi: KPIResult) -> str:
    band = _BENCHMARKS.get(key, {})
    label = band.get("label", kpi.name)
    unit = band.get("unit", kpi.unit)
    peer_median = band.get("median")
    better = band.get("better", "lower")
    if kpi.value is None:
        value_str = "—"
        color = P["text_faint"]
        band_label = "Insufficient data"
        reason = kpi.reason or ""
        peer_line = ""
    else:
        value_str = _format_value(kpi.value, kpi.unit)
        color = _colour_for(kpi.value, band)
        band_label = _band_label(kpi.value, band)
        reason = f"n={kpi.sample_size} claims"
        # Peer-median delta line.  Shows signed delta in native unit
        # with an arrow indicating whether that sign means good/bad.
        if peer_median is not None:
            delta = kpi.value - peer_median
            if unit == "pct":
                delta_txt = f"{delta*100:+.1f} pp"
                peer_txt = f"peer median {peer_median*100:.1f}%"
            elif unit == "days":
                delta_txt = f"{delta:+.0f}d"
                peer_txt = f"peer median {peer_median:.0f}d"
            elif unit == "ratio":
                delta_txt = f"{delta:+.3f}"
                peer_txt = f"peer median {peer_median:.3f}"
            else:
                delta_txt = f"{delta:+.2f}"
                peer_txt = f"peer median {peer_median:.2f}"
            # Arrow: upward triangle if above median, downward if below.
            # Color the arrow by whether delta is favorable.
            if delta > 0:
                arrow = "▲"
                favorable = (better == "higher")
            elif delta < 0:
                arrow = "▼"
                favorable = (better == "lower")
            else:
                arrow = "●"
                favorable = True
            arrow_cls = "cad-pos" if favorable else "cad-neg"
            peer_line = (
                '<div class="db-kpi-peer">'
                f'<span class="{arrow_cls}">{arrow}</span> '
                f'{html.escape(delta_txt)} vs {html.escape(peer_txt)}</div>'
            )
        else:
            peer_line = ""
    return (
        '<div class="db-kpi-card">'
        f'<div class="db-kpi-label">{html.escape(label)}</div>'
        f'<div class="db-kpi-value" style="color:{color};">{value_str}</div>'
        f'<div class="db-kpi-band" style="color:{color};">{html.escape(band_label)}</div>'
        f'{peer_line}'
        f'<div class="db-kpi-reason">{html.escape(reason)}</div>'
        '</div>'
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
        '<div class="db-kpi-card">'
        f'<div class="db-kpi-label">{html.escape(label)}</div>'
        f'<div class="db-kpi-value" style="color:{color};">{value_str}</div>'
        f'<div class="db-lag-extra">{html.escape(extra)}</div>'
        '</div>'
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
    return ck_panel(
        '<p class="ck-eyebrow">'
        f'Mature cohorts: {len(all_mature)}  ·  '
        f'In-flight (censored): {len(censored)}  ·  '
        f'Windows: {", ".join(str(w) + "d" for w in report.window_days)}'
        '</p>'
        '<table class="cad-table">'
        '<thead><tr>'
        '<th>Cohort</th>'
        '<th class="num">Window</th>'
        '<th class="num">Claims</th>'
        '<th class="num">Liquidation</th>'
        '<th>Status</th>'
        '<th>Note</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table>',
        title="Cohort Liquidation",
    )


_DB_CHART_CAPTION_CSS = (
    ".db-figcap{font-size:11px;color:#6b6456;margin:6px 0 8px;"
    "font-family:'JetBrains Mono',ui-monospace,monospace;"
    "letter-spacing:0.02em;}"
)


def _denial_pareto_chart(
    row_list: List[DenialStratRow], width: int = 720, height: int = 300
) -> str:
    """Pareto chart: denial dollars as sorted bars + cumulative-% line.

    The canonical 80/20 view — bars descend by dollar impact, a line
    tracks the running cumulative share, and an 80% reference marks how
    many categories carry the bulk of denials. Reads the same dollars
    the bar list below shows. Empty input returns "".
    """
    rows = sorted(
        [r for r in row_list if getattr(r, "category", None)],
        key=lambda r: r.dollars_denied, reverse=True,
    )[:12]
    if not rows:
        return ""
    total = sum(r.dollars_denied for r in rows) or 1.0
    max_d = max((r.dollars_denied for r in rows), default=0) or 1.0

    pad_l, pad_r, pad_t, pad_b = 56, 48, 18, 64
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(rows)
    slot = plot_w / n
    bw = min(slot * 0.62, 54)

    accent = P["accent"]
    rule = P["border"]
    txt = P["text_dim"]
    line_c = P["warning"]

    def _y(frac: float) -> float:
        return pad_t + (1 - max(0.0, min(1.0, frac))) * plot_h

    parts: List[str] = [
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Denial dollars Pareto with cumulative share" '
        f'style="width:100%;max-width:{width}px;height:auto;'
        f'print-color-adjust:exact;-webkit-print-color-adjust:exact;">'
    ]
    # Axes.
    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" '
        f'stroke="{rule}" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{pad_l + plot_w}" '
        f'y2="{pad_t + plot_h}" stroke="{rule}" stroke-width="1"/>'
    )
    # 80% reference line.
    y80 = _y(0.8)
    parts.append(
        f'<line x1="{pad_l}" y1="{y80:.1f}" x2="{pad_l + plot_w}" '
        f'y2="{y80:.1f}" stroke="{line_c}" stroke-width="1" '
        f'stroke-dasharray="4 3" opacity="0.5"/>'
        f'<text x="{pad_l + plot_w + 4}" y="{y80 + 3:.1f}" font-size="9.5" '
        f'font-family="JetBrains Mono,ui-monospace,monospace" '
        f'fill="{line_c}">80%</text>'
    )
    # Bars + cumulative line.
    cum = 0.0
    pts: List[str] = []
    tips: List[str] = []
    for i, r in enumerate(rows):
        cx = pad_l + slot * i + slot / 2
        bh = r.dollars_denied / max_d * plot_h
        by = pad_t + plot_h - bh
        cum += r.dollars_denied / total
        tip = html.escape(
            f"{r.category}: ${r.dollars_denied:,.0f} "
            f"({r.dollars_denied / total:.1%}) · {r.count} claims · "
            f"cumulative {cum:.1%}"
        )
        tips.append(tip)
        parts.append(
            f'<rect x="{cx - bw / 2:.1f}" y="{by:.1f}" width="{bw:.1f}" '
            f'height="{max(bh, 0.5):.1f}" rx="1.5" fill="{accent}" '
            f'opacity="0.82"><title>{tip}</title></rect>'
        )
        cat = html.escape(str(r.category)[:10])
        parts.append(
            f'<text x="{cx:.1f}" y="{pad_t + plot_h + 14:.1f}" '
            f'text-anchor="end" font-size="9" '
            f'font-family="Inter Tight,system-ui,sans-serif" fill="{txt}" '
            f'transform="rotate(-35 {cx:.1f} {pad_t + plot_h + 14:.1f})">'
            f'{cat}</text>'
        )
        pts.append(f'{cx:.1f},{_y(cum):.1f}')
    parts.append(
        f'<polyline points="{" ".join(pts)}" fill="none" '
        f'stroke="{line_c}" stroke-width="2"/>'
    )
    for i, p in enumerate(pts):
        x, y = p.split(",")
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="2.6" fill="{line_c}">'
            f'<title>{tips[i]}</title></circle>'
        )
    # Y-axis 0/100% cumulative anchors.
    parts.append(
        f'<text x="{pad_l - 6}" y="{pad_t + 4:.1f}" text-anchor="end" '
        f'font-size="9" font-family="JetBrains Mono,ui-monospace,monospace" '
        f'fill="{txt}">100%</text>'
        f'<text x="{pad_l - 6}" y="{pad_t + plot_h:.1f}" text-anchor="end" '
        f'font-size="9" font-family="JetBrains Mono,ui-monospace,monospace" '
        f'fill="{txt}">0</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _denial_pareto(rows: Iterable[DenialStratRow]) -> str:
    row_list = list(rows)
    if not row_list:
        return ""
    total = sum(r.dollars_denied for r in row_list) or 1.0
    _chart = _denial_pareto_chart(row_list)
    _fig = (
        f'<style>{_DB_CHART_CAPTION_CSS}</style>'
        f'<div class="db-figcap">Denial dollars by category &middot; '
        f'bars = impact, line = cumulative share &middot; 80% reference</div>'
        f'{_chart}'
    ) if _chart else ""
    items = []
    for r in row_list:
        pct = r.dollars_denied / total
        bar_width = max(pct * 100, 2)
        items.append(
            '<div class="db-pareto-row">'
            '<div class="db-pareto-meta">'
            f'<span>{html.escape(r.category)}</span>'
            f'<span class="mono">${r.dollars_denied:,.0f}  ·  '
            f'{r.count} claims  ·  {r.pct_of_total_denied*100:,.1f}%</span>'
            '</div>'
            '<div class="db-pareto-track">'
            f'<div class="db-pareto-fill" style="width:{bar_width}%;"></div>'
            '</div>'
            '</div>'
        )
    return ck_panel(
        '<p class="ck-eyebrow">'
        'ANSI CARC categories by dollar impact. Drill-through to underlying '
        'claim rows is available via '
        '<a href="/diligence/root-cause" class="ck-link">Phase 3 — Root Cause</a>.'
        '</p>'
        f'{_fig}'
        f'{"".join(items)}',
        title="Denial Stratification",
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
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Realization Rate", realization_str,
            sub=(
                f'${report.total_realized_cash_usd:,.0f} of '
                f'${report.total_gross_charges_usd:,.0f} gross · '
                f'{len(mature)} mature cohort(s)'
                + (f", {len(censored)} in-flight" if censored else "")
            ),
            help={
                "definition": (
                    "Realized cash ÷ gross charges across mature "
                    "claim cohorts. The single number that summarizes "
                    "RCM performance — what % of what the hospital "
                    "billed actually became cash. PE healthcare median "
                    "is ~92-95%; below 88% flags structural RCM issues."
                ),
                "citation": "HFMA MAP Key 2021",
            },
        )
        + '</div>'
    )

    # Cascade table. One row per cohort × step; ALL-payers roll-up.
    if not mature:
        body_rows = (
            '<tr><td colspan="5" class="ck-empty-row">'
            '<em>No mature cohorts</em> at as-of '
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

    cascade_panel = ck_panel(
        '<p class="ck-eyebrow">'
        'Claim-level cascade from gross charges to realized cash, cohorted '
        'by date of service. Cohorts younger than '
        f'{report.realization_window_days} days are marked '
        '<em>insufficient data</em> — never fabricated. Drill-through to '
        'underlying claim_ids is available in '
        '<a href="/diligence/root-cause" class="ck-link">Phase 3</a>.'
        '</p>'
        f'{topline}'
        '<table class="cad-table">'
        '<thead><tr>'
        '<th>Cohort</th><th>Step</th>'
        '<th class="num">Amount</th>'
        '<th class="num">Running</th>'
        '<th class="num">n</th>'
        '</tr></thead>'
        f'<tbody>{body_rows}</tbody>'
        '</table>',
        title="Quality of Revenue (Cash Waterfall)",
    )
    return f"{mgmt_card}{cascade_panel}{per_class}"


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

    status_tone = {
        DivergenceStatus.IMMATERIAL.value: "positive",
        DivergenceStatus.WATCH.value: "warning",
        DivergenceStatus.CRITICAL.value: "negative",
    }.get(status, "neutral")
    status_badge = ck_signal_badge(html.escape(status), tone=status_tone)
    if status == DivergenceStatus.UNKNOWN.value or mgmt is None:
        numbers_html = (
            '<p class="ck-eyebrow">'
            'Waterfall accrual: '
            f'<span class="mono">${(accrual or 0):,.0f}</span></p>'
        )
    else:
        pct_str = f"{pct*100:+.1f}%" if pct is not None else "n/a"
        delta_str = f"{'+' if (delta or 0) >= 0 else '−'}${abs(delta or 0):,.0f}"
        numbers_html = (
            '<div class="ck-kpi-strip">'
            + ck_kpi_block("Waterfall accrual", f"${accrual:,.0f}")
            + ck_kpi_block("Management accrual", f"${mgmt:,.0f}")
            + ck_kpi_block("Delta", f"{delta_str} ({pct_str})")
            + '</div>'
        )

    return ck_panel(
        '<p class="ck-section-body">'
        f'{status_badge} <strong>{html.escape(title)}</strong></p>'
        f'<p class="ck-section-body">{html.escape(copy)}</p>'
        f'{numbers_html}',
        title="Management reconciliation",
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
                f'<td colspan="6" class="ck-empty-row">'
                f'<em>{in_flight} cohort(s) in-flight</em> — '
                'insufficient data'
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
