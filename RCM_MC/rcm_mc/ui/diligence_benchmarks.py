"""Phase 2 benchmarks tab renderer.

Four sections, one page:

  1. Hero — Days in A/R vs the HFMA peer median, with the
     "What this shows" partner callout.
  2. Quality of Revenue — management reconciliation, gross-to-cash
     cascade, per-payer-class breakout.
  3. KPI scorecard — the HFMA metrics vs benchmark bands.
  4. Cohort liquidation + denial stratification Pareto.

Whitespace first. One primary number per section. If a KPI is None
we render "Insufficient data" + the reason — never a fabricated
number.

This module does NOT reach into the CCD file system or trigger a
Phase 1 re-ingest; it is given a :class:`KPIBundle` and a
:class:`CohortLiquidationReport`. A bare call with no bundle renders
a placeholder page explaining how to attach a CCD.

Built on the chartis editorial kit: ck_editorial_head masthead,
ck_kpi_block stat tiles, ck_data_table/ck_data_cell tables,
ck_provenance_tooltip on every benchmark-derived number, and
ck_empty_state where a section has nothing to show (never a silent
blank). All tones come from kit CSS vars — no baked hex colors.
"""
from __future__ import annotations

import html
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..diligence.benchmarks import (
    CashWaterfallReport, CohortCell, CohortLiquidationReport,
    CohortStatus, DenialStratRow, DivergenceStatus, KPIBundle, KPIResult,
    QOR_THRESHOLD_IMMATERIAL, QOR_THRESHOLD_WATCH,
    WaterfallCohort, WaterfallStep,
)
from ._chartis_kit import (
    P, chartis_shell, ck_bar_row, ck_data_cell, ck_data_table,
    ck_editorial_head, ck_empty_state, ck_fmt_currency, ck_fmt_percent,
    ck_kpi_block, ck_next_section, ck_page_actions, ck_panel,
    ck_provenance_tooltip, ck_section_header, ck_signal_badge,
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

# Partner-readable one-liners for the [?] tooltip on each KPI label.
_KPI_HELP: Dict[str, str] = {
    "days_in_ar": (
        "Average days from claim submission to final payment — the "
        "working-capital speed of the revenue cycle. Every 10 days of "
        "elevated A/R is roughly 2.7% of annual revenue tied up in "
        "unpaid claims."
    ),
    "first_pass_denial_rate": (
        "Share of claims denied on first adjudication. Elevated rates "
        "flag front-end process problems — eligibility, authorization, "
        "coding — that are usually fixable operational levers."
    ),
    "ar_aging_over_90": (
        "Share of open A/R dollars older than 90 days. Stale "
        "receivables convert at steep discounts; a heavy >90d tail "
        "usually hides unbooked bad debt."
    ),
    "cost_to_collect": (
        "RCM operating cost as a share of cash collected. Read as a "
        "percentage: 3.5% means it costs 3.5 cents to collect a "
        "dollar."
    ),
    "net_revenue_realization": (
        "Realized cash ÷ expected net revenue across mature claim "
        "cohorts — what share of what the hospital expected to "
        "collect actually became cash. Below 88% flags structural "
        "RCM issues."
    ),
}

_HFMA_CITATION = "HFMA MAP Key 2021"


# ── Page-local styles — kit CSS vars only, no baked hexes ──────────

_DB_STYLES = """
<style>
.db-tone-pos{color:var(--sc-positive,#0a8a5f);}
.db-tone-warn{color:var(--sc-warning,#b8732a);}
.db-tone-neg{color:var(--sc-negative,#b5321e);}
.db-tone-dim{color:var(--sc-text-dim,#465366);}
.db-hero .ck-kpi-value{font-size:34px;}
.db-hero .ck-kpi-sub,.db-kpis .ck-kpi-sub{
  color:var(--sc-text-dim,#465366);line-height:1.7;}
.db-hero-note{max-width:72ch;}
.db-mono{font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-variant-numeric:tabular-nums;font-size:11px;
  color:var(--sc-text-dim,#465366);}
.db-figcap{font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-size:11px;color:var(--sc-text-dim,#465366);
  letter-spacing:0.02em;margin:6px 0 10px;max-width:80ch;}
.db-legend{font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-size:11px;color:var(--sc-text-dim,#465366);margin:10px 0 0;}
.db-recon-list{list-style:none;margin:14px 0 0;padding:12px 0 0;
  border-top:1px solid var(--sc-rule,#d6cfc0);
  display:flex;flex-direction:column;gap:8px;}
.db-recon-list li{display:flex;align-items:center;gap:10px;
  flex-wrap:wrap;font-size:12px;}
.db-pareto-svg{width:100%;max-width:720px;height:auto;
  print-color-adjust:exact;-webkit-print-color-adjust:exact;}
.db-provenance{margin-top:40px;padding-top:14px;
  border-top:1px solid var(--sc-rule,#d6cfc0);
  display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;
  font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-size:11px;color:var(--sc-text-dim,#465366);}
</style>
"""


# ── Small formatting helpers ────────────────────────────────────────

def _minus(s: str) -> str:
    """Swap a leading ASCII hyphen for the typographic minus."""
    return "−" + s[1:] if s.startswith("-") else s


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" + ("" if n == 1 else "s")


def _toned(text: str, tone: Optional[str]) -> str:
    """Wrap pre-escaped text in a page tone span (pos/warn/neg/dim)."""
    if tone in ("pos", "warn", "neg", "dim"):
        return f'<span class="db-tone-{tone}">{text}</span>'
    return text


def _deduct(v: float) -> str:
    """Deduction cell: '−$1,600.00', but never '−$0.00' for a zero."""
    return f"−${v:,.2f}" if v > 0 else f"${v:,.2f}"


def _format_value(value: float, unit: str) -> str:
    if unit == "pct":
        return ck_fmt_percent(value)
    if unit == "days":
        return f"{value:,.1f} d"
    if unit == "ratio":
        # Cost-to-collect reads as a % of cash collected, not a bare
        # 3-decimal ratio — partners quote "3.5%", never "0.035".
        return ck_fmt_percent(value)
    return f"{value:,.2f}"


def _tone_for(value: float, band: Dict[str, Any]) -> Optional[str]:
    """Quartile banding → semantic tone key (pos / warn / neg)."""
    if not band:
        return None
    better = band.get("better", "lower")
    if better == "lower":
        if value <= band["top_quartile_max"]:
            return "pos"
        if value >= band["bottom_quartile_min"]:
            return "neg"
        return "warn"
    # higher is better
    if value >= band["top_quartile_max"]:
        return "pos"
    if value <= band["bottom_quartile_min"]:
        return "neg"
    return "warn"


def _band_fmt(v: float, unit: str) -> str:
    if unit in ("pct", "ratio"):
        return f"{v * 100:,.1f}%"
    if unit == "days":
        return f"{v:,.0f} d"
    return f"{v:,.2f}"


def _band_label(value: float, band: Dict[str, Any]) -> str:
    if not band:
        return ""
    better = band.get("better", "lower")
    unit = band.get("unit", "")
    fmt = lambda v: _band_fmt(v, unit)  # noqa: E731
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


def _band_explainer(key: str, kpi: KPIResult) -> str:
    """Provenance copy for a KPI value — the on-page citation for the
    HFMA band that colours it, plus the sample it was computed from."""
    band = _BENCHMARKS.get(key, {})
    if not band:
        return f"Computed from {kpi.sample_size:,} claims in the attached CCD."
    unit = band.get("unit", "")
    better = band.get("better", "lower")
    cmp_top = "≤" if better == "lower" else "≥"
    cmp_bot = "≥" if better == "lower" else "≤"
    return (
        f"HFMA MAP Key 2021 acute-care benchmark: top quartile "
        f"{cmp_top} {_band_fmt(band['top_quartile_max'], unit)}, "
        f"median {_band_fmt(band['median'], unit)}, bottom quartile "
        f"{cmp_bot} {_band_fmt(band['bottom_quartile_min'], unit)} "
        f"({better} is better). Computed from {kpi.sample_size:,} "
        f"claims in the attached CCD."
    )


def _peer_delta_line(kpi_value: float, band: Dict[str, Any]) -> str:
    """'▲ +2.1 pp vs peer median 10.0%' — arrow toned by favorability."""
    peer_median = band.get("median")
    if peer_median is None:
        return ""
    unit = band.get("unit", "")
    better = band.get("better", "lower")
    delta = kpi_value - peer_median
    if unit in ("pct", "ratio"):
        delta_txt = _minus(f"{delta * 100:+.1f}") + " pp"
        peer_txt = f"peer median {peer_median * 100:,.1f}%"
    elif unit == "days":
        delta_txt = _minus(f"{delta:+.1f}") + " d"
        peer_txt = f"peer median {peer_median:,.0f} d"
    else:
        delta_txt = _minus(f"{delta:+.2f}")
        peer_txt = f"peer median {peer_median:,.2f}"
    if delta > 0:
        arrow, favorable = "▲", (better == "higher")
    elif delta < 0:
        arrow, favorable = "▼", (better == "lower")
    else:
        arrow, favorable = "●", True
    arrow_tone = "pos" if favorable else "neg"
    return (
        f'{_toned(arrow, arrow_tone)} {html.escape(delta_txt)} '
        f'vs {html.escape(peer_txt)}'
    )


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
    around. Absent, the section renders a designed empty state.
    """
    if bundle is None:
        return _placeholder_page()

    as_of = bundle.as_of_date.isoformat()
    dar = bundle.days_in_ar
    meta_parts = ["Phase 2 of 4", f"as-of {as_of}"]
    if dar.sample_size:
        meta_parts.append(f"n={dar.sample_size:,} claims")
    meta_parts.append("HFMA MAP Key 2021 bands")
    head = ck_editorial_head(
        eyebrow="RCM DILIGENCE — PHASE 2",
        title="Benchmarks",
        meta=" · ".join(meta_parts),
        lede_italic_phrase="Did billed dollars become cash?",
        lede_body=(
            "Five HFMA KPIs against acute-care peer bands, the "
            "gross-to-cash waterfall, cohort liquidation curves, and "
            "the denial Pareto — the Phase-2 evidence base for the "
            "RCM thesis."
        ),
        source_note=(
            f"HFMA MAP Key 2021 acute-care benchmark bands · "
            f"CCD as-of {as_of}"
        ),
    )
    body = (
        _DB_STYLES
        + head
        + _hero(bundle)
        + _cash_waterfall_section(cash_waterfall)
        + _kpi_scorecard(bundle)
        + _cohort_section(cohort_report)
        + _denial_pareto(bundle.denial_stratification)
        + _provenance_footer(bundle)
        + ck_page_actions()
        + ck_next_section(
            "Open the bridge auditor",
            "/diligence/bridge-audit",
            eyebrow="Up next",
            italic_word="bridge",
        )
    )
    return chartis_shell(
        body,
        "RCM Diligence · Benchmarks",
        active_nav="/diligence/benchmarks",
    )


# ── Section builders ────────────────────────────────────────────────

def _placeholder_page() -> str:
    head = ck_editorial_head(
        eyebrow="RCM DILIGENCE — PHASE 2",
        title="Benchmarks",
        meta="Phase 2 of 4 · no dataset attached",
        lede_italic_phrase="KPI benchmarking and stress testing",
        lede_body=(
            "— attach a Canonical Claims Dataset in Phase 1 to "
            "populate the HFMA KPI scorecard, cohort liquidation "
            "curves, and denial-stratification Pareto on this tab."
        ),
    )
    body = head + ck_empty_state(
        "Attach a Canonical Claims Dataset",
        body=(
            "Phase 2 computes the HFMA KPI scorecard, the "
            "quality-of-revenue cash waterfall, cohort liquidation "
            "curves, and the denial Pareto from the CCD produced by "
            "Phase 1 ingest. No dataset is attached yet."
        ),
        eyebrow="NO DATA YET",
        cta_label="Phase 1: Ingest a CCD",
        cta_href="/diligence/ingest",
    )
    return chartis_shell(
        body, "RCM Diligence · Benchmarks",
        active_nav="/diligence/benchmarks",
        subtitle="Phase 2 of 4",
    )


def _hero(bundle: KPIBundle) -> str:
    # Primary number: Days in A/R (the one metric every CFO reads first).
    dar = bundle.days_in_ar
    band = _BENCHMARKS.get("days_in_ar", {})
    peer_median = band.get("median")
    if dar.value is not None:
        tone = _tone_for(dar.value, band)
        band_label = _band_label(dar.value, band)
        value_html = ck_provenance_tooltip(
            "Days in A/R",
            _toned(html.escape(f"{dar.value:,.1f} d"), tone),
            explainer=_band_explainer("days_in_ar", dar),
            inject_css=True,
        )
        if peer_median is not None:
            delta = dar.value - peer_median
            delta_txt = _minus(f"{delta:+.1f}") + " d"
            arrow = "▲" if delta > 0 else "▼" if delta < 0 else "●"
            arrow_tone = "pos" if delta <= 0 else "neg"
            delta_html = (
                f'{_toned(arrow, arrow_tone)} {html.escape(delta_txt)} '
                f'vs HFMA peer median {peer_median:,.0f} d'
            )
            if delta < 0:
                summary = (
                    f"Claims are converting to cash faster than the "
                    f"HFMA acute-hospital peer median ({peer_median:,.0f} d). "
                    f"This target's working capital efficiency is "
                    f"above average: fewer dollars tied up in unpaid "
                    f"claims than comparable hospitals."
                )
            elif delta > 10:
                summary = (
                    f"Days in A/R is {delta:,.0f} d slower than the "
                    f"HFMA acute-hospital peer median ({peer_median:,.0f} d). "
                    f"Every 10 days of elevated A/R is roughly 2.7% of "
                    f"annual revenue sitting in working capital: an "
                    f"EBITDA-bridge opportunity when modeled at the "
                    f"cost-of-capital rate."
                )
            else:
                summary = (
                    f"Days in A/R is within the HFMA acute-hospital "
                    f"peer median range ({peer_median:,.0f} d ± 10). "
                    f"Working capital is neither a strength nor a bridge "
                    f"lever: look elsewhere (denials, Medicare mix) "
                    f"for upside."
                )
        else:
            delta_html = ""
            summary = ""
        sub_parts = [
            _toned(html.escape(band_label), tone),
            delta_html,
            html.escape(_plural(dar.sample_size, "claim")),
        ]
        sub = "<br>".join(p for p in sub_parts if p)
    else:
        value_html = ck_provenance_tooltip(
            "Days in A/R",
            _toned("—", "dim"),
            explainer=(
                "Days in A/R could not be computed. "
                + (dar.reason or "The CCD lacks the claim lifecycle "
                                 "fields this KPI needs.")
            ),
            inject_css=True,
        )
        sub = _toned("Insufficient data", "dim") + (
            f'<br>{_toned(html.escape(dar.reason), "dim")}'
            if dar.reason else ""
        )
        summary = (
            "The CCD does not contain enough submit-date / paid-date "
            "pairs to compute days-in-A/R. Typically occurs when claim "
            "lifecycle fields weren't extracted from the source EMR."
        )

    summary_html = (
        '<p class="ck-section-body db-hero-note">'
        f'<strong>What this shows: </strong>{html.escape(summary)}</p>'
    ) if summary else ""

    hero_block = ck_kpi_block(
        "Primary KPI · Days in A/R",
        value_html,
        sub=sub,
        help={
            "definition": _KPI_HELP["days_in_ar"],
            "citation": _HFMA_CITATION,
        },
    )
    return (
        f'<div class="ck-kpi-strip db-hero">{hero_block}</div>'
        f'{summary_html}'
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
        ck_section_header(
            "KPI Scorecard", eyebrow="HFMA MAP KEY 2021",
            count=f"{len(cards)} KPIs",
        )
        + f'<div class="ck-kpi-grid db-kpis">{"".join(cards)}</div>'
    )


def _kpi_card(key: str, kpi: KPIResult) -> str:
    band = _BENCHMARKS.get(key, {})
    label = band.get("label", kpi.name)
    unit = band.get("unit", kpi.unit)
    help_block = {
        "definition": _KPI_HELP.get(key, ""),
        "citation": _HFMA_CITATION,
    }
    if kpi.value is None:
        sub = _toned("Insufficient data", "dim") + (
            f'<br>{_toned(html.escape(kpi.reason), "dim")}'
            if kpi.reason else ""
        )
        return ck_kpi_block(label, _toned("—", "dim"), sub=sub,
                            help=help_block)
    tone = _tone_for(kpi.value, band)
    band_label = _band_label(kpi.value, band)
    value_html = ck_provenance_tooltip(
        label,
        _toned(html.escape(_format_value(kpi.value, unit)), tone),
        explainer=_band_explainer(key, kpi),
        inject_css=False,
    )
    # Peer-median delta line: signed delta in native unit with an
    # arrow toned by whether that sign is favorable.
    peer_line = _peer_delta_line(kpi.value, band)
    sub_parts = [
        _toned(html.escape(band_label), tone),
        peer_line,
        html.escape(_plural(kpi.sample_size, "claim")),
    ]
    sub = "<br>".join(p for p in sub_parts if p)
    return ck_kpi_block(label, value_html, sub=sub, help=help_block)


def _lag_card(kpi: KPIResult, label: str) -> str:
    if kpi.value is None:
        value_html = _toned("—", "dim")
        sub = _toned(html.escape(kpi.reason or "Insufficient data"), "dim")
    else:
        value_html = html.escape(f"{kpi.value:,.0f} d")
        sub = html.escape(
            f"p25 {kpi.numerator:,.0f} d · p75 {kpi.denominator:,.0f} d · "
            f"n={kpi.sample_size:,}"
        )
    return ck_kpi_block(label, value_html, sub=sub)


def _cohort_section(report: Optional[CohortLiquidationReport]) -> str:
    header = ck_section_header(
        "Cohort Liquidation", eyebrow="LIQUIDATION CURVES",
        count=(
            f"{len(report.mature_cells())} mature · "
            f"{len(report.censored_cells())} in-flight"
            if report is not None else None
        ),
    )
    if report is None:
        return header + ck_empty_state(
            "No cohort liquidation data yet",
            body=(
                "Cohort liquidation needs claim lifecycle fields — "
                "date of service, payment dates, and paid amounts — "
                "from the Phase 1 ingest. Re-run ingest with lifecycle "
                "extraction enabled to populate liquidation curves by "
                "cohort month."
            ),
            eyebrow="COHORT LIQUIDATION",
            cta_label="Re-run Phase 1 ingest",
            cta_href="/diligence/ingest",
        )
    cells: List[CohortCell] = sorted(
        report.mature_cells() + report.censored_cells(),
        key=lambda c: (c.cohort_month, c.days_since_dos),
    )
    rows_html: List[str] = []
    prev_month: Optional[str] = None
    for cell in cells:
        month_tone = "dim" if cell.cohort_month == prev_month else None
        prev_month = cell.cohort_month
        if cell.cumulative_liquidation_pct is not None:
            pct = cell.cumulative_liquidation_pct
            liq_cell = ck_data_cell(
                ck_fmt_percent(pct), align="right", mono=True,
                bar=max(0.0, min(100.0, pct * 100)),
            )
        else:
            liq_cell = ck_data_cell("—", align="right", mono=True,
                                    tone="dim")
        if cell.status == CohortStatus.MATURE:
            status_badge = ck_signal_badge("Mature", tone="positive")
        elif cell.status == CohortStatus.INSUFFICIENT_DATA:
            status_badge = ck_signal_badge("In-flight", tone="neutral")
        else:
            status_badge = ck_signal_badge(cell.status.value,
                                           tone="neutral")
        rows_html.append(
            "<tr>"
            + ck_data_cell(html.escape(cell.cohort_month), mono=True,
                           tone=month_tone)
            + ck_data_cell(f"{cell.days_since_dos} d", align="right",
                           mono=True)
            + ck_data_cell(f"{cell.cohort_size_claims:,}", align="right",
                           mono=True)
            + liq_cell
            + ck_data_cell(status_badge)
            + ck_data_cell(html.escape(cell.reason or ""), tone="dim")
            + "</tr>"
        )
    if not rows_html:
        rows_html.append(
            '<tr><td colspan="6" class="ck-cell ck-empty-row">'
            '<em>No cohorts</em> in this CCD at as-of '
            f'{report.as_of_date.isoformat()}.</td></tr>'
        )
    windows = ", ".join(f"{w} d" for w in report.window_days)
    table = ck_data_table(
        headers=[
            {"label": "Cohort"},
            {"label": "Window", "align": "right"},
            {"label": "Claims", "align": "right"},
            {"label": "Liquidation", "align": "right"},
            {"label": "Status"},
            {"label": "Note"},
        ],
        rows_html="".join(rows_html),
    )
    intro = (
        '<p class="ck-section-body">'
        'Cumulative cash liquidation by date-of-service cohort at '
        f'{html.escape(windows)} windows. In-flight (censored) cohorts '
        'show claim counts but no rate — never fabricated.</p>'
    )
    return header + ck_panel(intro + table,
                             title="Liquidation by cohort month")


def _cat_label(category: Any) -> str:
    """Normalize a CARC category for display — chart and list share
    this so the same row never renders under two different names."""
    return str(category) if category else "(uncategorized)"


def _denial_pareto_chart(
    row_list: List[DenialStratRow], total: float,
    width: int = 720, height: int = 310,
) -> str:
    """Pareto chart: denial dollars as sorted bars + cumulative-% line.

    The canonical 80/20 view — bars descend by dollar impact, a line
    tracks the running cumulative share, and an 80% reference marks how
    many categories carry the bulk of denials. ``total`` is the sum
    over ALL rows (the same denominator the bar list below uses), so
    the cumulative line and per-bar percentages mean what they say.
    When more than 12 categories exist, the tail is aggregated into a
    final "Other (N)" bar so cumulative still reaches 100%. Empty
    input returns "".
    """
    rows = sorted(row_list, key=lambda r: r.dollars_denied, reverse=True)
    if not rows or total <= 0:
        return ""
    shown = rows[:12]
    rest = rows[12:]
    # (label, dollars, claim_count, is_aggregate)
    bars: List[Tuple[str, float, int, bool]] = [
        (_cat_label(r.category), r.dollars_denied, r.count, False)
        for r in shown
    ]
    if rest:
        bars.append((
            f"Other ({len(rest)})",
            sum(r.dollars_denied for r in rest),
            sum(r.count for r in rest),
            True,
        ))
    max_d = max(d for _, d, _, _ in bars) or 1.0

    pad_l, pad_r, pad_t, pad_b = 64, 64, 26, 64
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(bars)
    slot = plot_w / n
    bw = min(slot * 0.62, 54)

    accent = P["teal"]
    rule = P["rule"]
    txt = P["text_dim"]
    line_c = P["warning"]
    mono = "JetBrains Mono,ui-monospace,monospace"

    def _y(frac: float) -> float:
        return pad_t + (1 - max(0.0, min(1.0, frac))) * plot_h

    parts: List[str] = [
        f'<svg viewBox="0 0 {width} {height}" class="db-pareto-svg" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Denial dollars Pareto with cumulative share of '
        f'all denied dollars">'
    ]
    # Axes.
    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" '
        f'stroke="{rule}" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{pad_l + plot_w}" '
        f'y2="{pad_t + plot_h}" stroke="{rule}" stroke-width="1"/>'
        f'<line x1="{pad_l + plot_w}" y1="{pad_t}" x2="{pad_l + plot_w}" '
        f'y2="{pad_t + plot_h}" stroke="{rule}" stroke-width="1"/>'
    )
    # Axis headers — name the dual scale so bars are never read
    # against the cumulative axis.
    parts.append(
        f'<text x="{pad_l - 8}" y="{pad_t - 12}" text-anchor="end" '
        f'font-size="8.5" font-family="{mono}" fill="{txt}">$ DENIED</text>'
        f'<text x="{pad_l + plot_w + 8}" y="{pad_t - 12}" '
        f'text-anchor="start" font-size="8.5" font-family="{mono}" '
        f'fill="{txt}">CUM %</text>'
    )
    # Left-axis $ anchors (bar scale) + right-axis cumulative anchors.
    parts.append(
        f'<text x="{pad_l - 8}" y="{pad_t + 4}" text-anchor="end" '
        f'font-size="9" font-family="{mono}" fill="{txt}">'
        f'{html.escape(ck_fmt_currency(max_d))}</text>'
        f'<text x="{pad_l - 8}" y="{pad_t + plot_h}" text-anchor="end" '
        f'font-size="9" font-family="{mono}" fill="{txt}">$0</text>'
        f'<text x="{pad_l + plot_w + 8}" y="{pad_t + 4}" '
        f'text-anchor="start" font-size="9" font-family="{mono}" '
        f'fill="{txt}">100%</text>'
        f'<text x="{pad_l + plot_w + 8}" y="{pad_t + plot_h}" '
        f'text-anchor="start" font-size="9" font-family="{mono}" '
        f'fill="{txt}">0%</text>'
    )
    # 80% reference line against the cumulative (right) axis.
    y80 = _y(0.8)
    parts.append(
        f'<line x1="{pad_l}" y1="{y80:.1f}" x2="{pad_l + plot_w}" '
        f'y2="{y80:.1f}" stroke="{line_c}" stroke-width="1" '
        f'stroke-dasharray="4 3" opacity="0.5"/>'
        f'<text x="{pad_l + plot_w + 8}" y="{y80 + 3:.1f}" font-size="9" '
        f'font-family="{mono}" fill="{line_c}">80%</text>'
    )
    # Bars + per-bar $ labels + cumulative line.
    cum = 0.0
    pts: List[str] = []
    tips: List[str] = []
    for i, (cat, dollars, count, is_agg) in enumerate(bars):
        cx = pad_l + slot * i + slot / 2
        bh = dollars / max_d * plot_h
        by = pad_t + plot_h - bh
        cum += dollars / total
        tip = html.escape(
            f"{cat}: ${dollars:,.2f} ({dollars / total:.1%} of total "
            f"denied) · {count} claims · cumulative {cum:.1%}"
        )
        tips.append(tip)
        opacity = "0.45" if is_agg else "0.82"
        parts.append(
            f'<rect x="{cx - bw / 2:.1f}" y="{by:.1f}" width="{bw:.1f}" '
            f'height="{max(bh, 0.5):.1f}" rx="1.5" fill="{accent}" '
            f'opacity="{opacity}"><title>{tip}</title></rect>'
        )
        # Direct $ label above each bar — the bar scale is readable
        # without hunting for the left axis.
        parts.append(
            f'<text x="{cx:.1f}" y="{by - 4:.1f}" text-anchor="middle" '
            f'font-size="8.5" font-family="{mono}" fill="{txt}">'
            f'{html.escape(ck_fmt_currency(dollars))}</text>'
        )
        short = cat[:10] + "…" if len(cat) > 10 else cat
        parts.append(
            f'<text x="{cx:.1f}" y="{pad_t + plot_h + 14:.1f}" '
            f'text-anchor="end" font-size="9" '
            f'font-family="Inter Tight,system-ui,sans-serif" fill="{txt}" '
            f'transform="rotate(-35 {cx:.1f} {pad_t + plot_h + 14:.1f})">'
            f'{html.escape(short)}<title>{html.escape(cat)}</title></text>'
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
    parts.append("</svg>")
    return "".join(parts)


def _denial_pareto(rows: Iterable[DenialStratRow]) -> str:
    row_list = list(rows)
    n_cats = len(row_list)
    header = ck_section_header(
        "Denial Stratification", eyebrow="DENIAL PARETO",
        count=f"{n_cats} categor" + ("y" if n_cats == 1 else "ies"),
    )
    if not row_list:
        return header + ck_empty_state(
            "No denial rows in this CCD",
            body=(
                "The CCD contains no denied claims with CARC "
                "categories — either denials weren't extracted in "
                "Phase 1, or the target genuinely has none. Re-run "
                "ingest with remittance (835) extraction to populate "
                "the Pareto."
            ),
            eyebrow="DENIAL PARETO",
            cta_label="Re-run Phase 1 ingest",
            cta_href="/diligence/ingest",
        )
    # One denominator for everything on this screen: the full total
    # over ALL rows. The chart's cumulative line, its per-bar shares,
    # and the bar list below all divide by this same number.
    total = sum(r.dollars_denied for r in row_list) or 1.0
    sorted_rows = sorted(row_list, key=lambda r: r.dollars_denied,
                         reverse=True)
    chart = _denial_pareto_chart(sorted_rows, total)
    fig = (
        f'{chart}'
        '<p class="db-figcap">How to read: bars = denied $ by CARC '
        'category (left axis; each bar carries its own $ label) · '
        'line = cumulative share of all denied dollars (right axis) · '
        'dashed rule marks 80%.</p>'
    ) if chart else ""
    items: List[str] = []
    for r in sorted_rows:
        share = r.dollars_denied / total
        items.append(ck_bar_row(
            _cat_label(r.category),
            f"{ck_fmt_currency(r.dollars_denied)} · "
            f"{_plural(r.count, 'claim')}",
            share * 100,
        ))
    intro = (
        '<p class="ck-section-body">'
        'ANSI CARC categories by dollar impact. Drill-through to '
        'underlying claim rows is available via '
        '<a href="/diligence/root-cause" class="ck-link">'
        'Phase 3: Root Cause</a>.</p>'
    )
    return header + ck_panel(
        intro + fig + "".join(items),
        title="Pareto by CARC category",
    )


def _cash_waterfall_section(report: Optional[CashWaterfallReport]) -> str:
    """Headline section: Quality of Revenue / Cash Waterfall.

    Renders in this order:
      1. Management reconciliation summary card — IMMATERIAL / WATCH
         / CRITICAL band against management-reported accrual revenue,
         plus the dollar delta.
      2. Top-line realization metrics (cash / gross / cohort counts).
      3. Cohort × step cascade table (ALL-payers) with per-cohort
         reconciliation verdicts pulled into a badge footer.
      4. Per-payer-class breakout — one compact row per payer class
         summarising gross → accrual → cash so a partner sees which
         payer mix is driving the top-line divergence.

    Rendering never fabricates: if a management number was not
    supplied, the card renders "not supplied" and the status is
    UNKNOWN. In-flight cohorts show claim counts but no realization.
    """
    header_count = None
    if report is not None:
        header_count = (
            f"{len(report.mature_cohorts())} mature · "
            f"{len(report.censored_cohorts())} in-flight"
        )
    header = ck_section_header(
        "Quality of Revenue", eyebrow="CASH WATERFALL",
        count=header_count,
    )
    if report is None:
        return header + ck_empty_state(
            "No cash waterfall yet",
            body=(
                "Quality-of-Revenue analysis needs claim lifecycle "
                "fields — gross charges, adjudication steps, and "
                "payment dates — from the Phase 1 ingest. Re-run "
                "ingest with lifecycle extraction enabled to populate "
                "the gross-to-cash cascade."
            ),
            eyebrow="QUALITY OF REVENUE",
            cta_label="Re-run Phase 1 ingest",
            cta_href="/diligence/ingest",
        )
    mature = report.mature_cohorts()
    censored = report.censored_cohorts()

    mgmt_card = _management_reconciliation_card(report)

    # Top-line summary.
    rate = report.total_realization_rate
    if rate is not None:
        realization_html = ck_provenance_tooltip(
            "Realization rate",
            _toned(html.escape(ck_fmt_percent(rate)),
                   _realization_tone(rate)),
            explainer=(
                "Realized cash ÷ gross charges across mature claim "
                "cohorts. HFMA MAP Key 2021 acute-care norms: ≥ 95% "
                "strong, 88–95% watch, below 88% flags structural RCM "
                "issues."
            ),
            inject_css=False,
        )
    else:
        realization_html = _toned("—", "dim")
    sub = (
        f"${report.total_realized_cash_usd:,.2f} of "
        f"${report.total_gross_charges_usd:,.2f} gross · "
        f"{_plural(len(mature), 'mature cohort')}"
        + (f" · {len(censored)} in-flight" if censored else "")
    )
    topline = (
        '<div class="ck-kpi-strip db-kpis">'
        + ck_kpi_block(
            "Realization Rate", realization_html,
            sub=html.escape(sub),
            help={
                "definition": (
                    "Realized cash ÷ gross charges across mature "
                    "claim cohorts. The single number that summarizes "
                    "RCM performance: what % of what the hospital "
                    "billed actually became cash. PE healthcare median "
                    "is ~92-95%; below 88% flags structural RCM issues."
                ),
                "citation": _HFMA_CITATION,
            },
        )
        + '</div>'
    )

    # Cascade table. One row per cohort × step; ALL-payers roll-up.
    # Reconciliation verdicts are pulled OUT of the data rows into a
    # badge footer so the table stays one species of row.
    recon_items: List[str] = []
    if not mature:
        body_rows = (
            '<tr><td colspan="5" class="ck-cell ck-empty-row">'
            '<em>No mature cohorts</em> at as-of '
            f'{report.as_of_date.isoformat()}.</td></tr>'
        )
    else:
        parts: List[str] = []
        for cohort in mature:
            first_row = True
            for s in cohort.steps:
                is_terminal = s.name == "realized_cash"
                is_addback = s.name == "appeals_recovered"
                is_base = s.name == "gross_charges"
                step_tone = ("pos" if is_terminal
                             else "dim" if is_addback else None)
                cell_tone = ("pos" if is_terminal
                             else "dim" if is_addback else None)
                # The opening base and the terminal cash row are levels,
                # not flows — no sign. Zero amounts (e.g. no appeals
                # recovered) show a bare $0.00, never "+$0.00"/"−$0.00".
                sign = ("" if (is_terminal or is_base or s.amount_usd == 0)
                        else "+" if is_addback else "−")
                parts.append(
                    "<tr>"
                    + ck_data_cell(
                        html.escape(cohort.cohort_month), mono=True,
                        tone=None if first_row else "dim")
                    + ck_data_cell(
                        _toned(html.escape(s.label), step_tone),
                        weight=700 if is_terminal else None)
                    + ck_data_cell(
                        f"{sign}${s.amount_usd:,.2f}", align="right",
                        mono=True, tone=cell_tone,
                        weight=700 if is_terminal else None)
                    + ck_data_cell(
                        f"${s.running_balance_usd:,.2f}", align="right",
                        mono=True, tone="dim")
                    + ck_data_cell(
                        f"{s.claim_count:,}", align="right", mono=True,
                        tone="dim")
                    + "</tr>"
                )
                first_row = False
            # Per-cohort divergence verdict (when we have a management
            # number to compare against) → badge footer, not a row.
            if cohort.management_reported_revenue_usd is not None:
                status = cohort.divergence_status
                s_title, _ = _STATUS_COPY.get(
                    status, _STATUS_COPY[DivergenceStatus.UNKNOWN.value])
                s_tone = _STATUS_TONE.get(status, "neutral")
                pct = cohort.qor_divergence_pct or 0.0
                recon_items.append(
                    '<li>'
                    f'<span class="db-mono">'
                    f'{html.escape(cohort.cohort_month)}</span>'
                    + ck_signal_badge(f"Reconciliation · {s_title}",
                                      tone=s_tone)
                    + f'<span class="db-mono">'
                    f'{_minus(f"{pct * 100:+.1f}")}% vs mgmt '
                    f'${cohort.management_reported_revenue_usd:,.2f}'
                    '</span></li>'
                )
        body_rows = "".join(parts)

    cascade_table = ck_data_table(
        headers=[
            {"label": "Cohort"},
            {"label": "Step"},
            {"label": "Amount", "align": "right"},
            {"label": "Running", "align": "right"},
            {"label": "Claims", "align": "right"},
        ],
        rows_html=body_rows,
    )
    recon_html = (
        f'<ul class="db-recon-list">{"".join(recon_items)}</ul>'
        if recon_items else ""
    )
    intro = (
        '<p class="ck-section-body">'
        'Claim-level cascade from gross charges to realized cash, '
        'cohorted by date of service. Cohorts younger than '
        f'{report.realization_window_days} days are marked '
        '<em>insufficient data</em> — never fabricated. Drill-through '
        'to underlying claim_ids is available in '
        '<a href="/diligence/root-cause" class="ck-link">Phase 3</a>.'
        '</p>'
    )
    cascade_panel = ck_panel(
        intro + topline + cascade_table + recon_html,
        title="Gross-to-cash cascade",
    )
    per_class = _per_payer_class_table(report)
    return f"{header}{mgmt_card}{cascade_panel}{per_class}"


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
        f"Divergence ≥ {QOR_THRESHOLD_WATCH*100:,.0f}%: the claims-side "
        f"reconstruction disagrees with management's reported revenue by "
        f"more than the VMG/A&M QoR threshold. Partner-quotable finding.",
    ),
    DivergenceStatus.UNKNOWN.value: (
        "Not supplied",
        "Management-reported accrual revenue was not provided, so no "
        "reconciliation was attempted.",
    ),
}

_STATUS_TONE = {
    DivergenceStatus.IMMATERIAL.value: "positive",
    DivergenceStatus.WATCH.value: "warning",
    DivergenceStatus.CRITICAL.value: "negative",
}


def _realization_tone(rate: Optional[float]) -> Optional[str]:
    """Band a realization rate against the thresholds the QoR help
    copy quotes — colour must be earned from the value, never
    unconditional. ≥95% strong (pos), 88–95% neutral, <88% structural
    concern (neg)."""
    if rate is None:
        return "dim"
    if rate >= 0.95:
        return "pos"
    if rate >= 0.88:
        return None
    return "neg"


def _management_reconciliation_card(report: CashWaterfallReport) -> str:
    """Headline card above the cascade table: divergence band, delta,
    and the human copy a partner can drop into a memo."""
    status = report.total_divergence_status
    title, copy = _STATUS_COPY.get(
        status, _STATUS_COPY[DivergenceStatus.UNKNOWN.value])

    accrual = report.total_accrual_revenue_usd
    mgmt = report.total_management_revenue_usd
    delta = report.total_qor_divergence_usd
    pct = report.total_qor_divergence_pct

    status_badge = ck_signal_badge(
        title, tone=_STATUS_TONE.get(status, "neutral"))
    if status == DivergenceStatus.UNKNOWN.value or mgmt is None:
        numbers_html = (
            '<div class="ck-kpi-strip db-kpis">'
            + ck_kpi_block("Waterfall accrual",
                           html.escape(f"${(accrual or 0):,.2f}"))
            + '</div>'
        )
    else:
        pct_str = (_minus(f"{pct * 100:+.1f}") + "%"
                   if pct is not None else "n/a")
        delta_str = (
            ("+" if (delta or 0) >= 0 else "−")
            + f"${abs(delta or 0):,.2f}"
        )
        numbers_html = (
            '<div class="ck-kpi-strip db-kpis">'
            + ck_kpi_block("Waterfall accrual",
                           html.escape(f"${accrual:,.2f}"))
            + ck_kpi_block("Management accrual",
                           html.escape(f"${mgmt:,.2f}"))
            + ck_kpi_block("Delta",
                           html.escape(f"{delta_str} ({pct_str})"))
            + '</div>'
        )

    return ck_panel(
        '<p class="ck-section-body">'
        f'{status_badge} {html.escape(copy)}</p>'
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
                "<tr>"
                + ck_data_cell(html.escape(pc), mono=True)
                + '<td colspan="6" class="ck-cell tone-dim">'
                f'<em>{_plural(in_flight, "cohort")} in-flight</em> — '
                'insufficient data</td>'
                "</tr>"
            )
            continue
        rate = (t["cash"] / t["gross"]) if t["gross"] > 0 else None
        rate_str = ck_fmt_percent(rate) if rate is not None else "—"
        rows.append(
            "<tr>"
            + ck_data_cell(html.escape(pc), mono=True)
            + ck_data_cell(f'${t["gross"]:,.2f}', align="right", mono=True)
            + ck_data_cell(_deduct(t["contractual"]), align="right",
                           mono=True, tone="dim")
            + ck_data_cell(_deduct(t["denials_net"]), align="right",
                           mono=True, tone="dim")
            + ck_data_cell(_deduct(t["bad_debt"]), align="right",
                           mono=True, tone="dim")
            + ck_data_cell(f'${t["accrual"]:,.2f}', align="right",
                           mono=True)
            + ck_data_cell(rate_str, align="right", mono=True,
                           tone=_realization_tone(rate), weight=600)
            + "</tr>"
        )

    table = ck_data_table(
        headers=[
            {"label": "Payer Class"},
            {"label": "Gross", "align": "right"},
            {"label": "Contractuals", "align": "right"},
            {"label": "Denials (net)", "align": "right"},
            {"label": "Bad Debt", "align": "right"},
            {"label": "Accrual", "align": "right"},
            {"label": "Realization", "align": "right"},
        ],
        rows_html="".join(rows),
    )
    legend = (
        '<p class="db-legend">Realization bands: ≥ 95.0% strong · '
        '88.0–95.0% watch · &lt; 88.0% structural concern — '
        'HFMA MAP Key 2021 acute-care norms.</p>'
    )
    return ck_panel(table + legend, title="By payer class")


def _provenance_footer(bundle: KPIBundle) -> str:
    tv = bundle.days_in_ar.temporal
    events = tv.overlapping_events
    events_html = ""
    if events:
        names = "; ".join(e.name for e in events)
        events_html = ck_signal_badge(
            f"Regulatory overlap: {names}", tone="warning")
    return (
        '<footer class="db-provenance">'
        f'<span>claims range {html.escape(tv.claims_date_min or "n/a")} → '
        f'{html.escape(tv.claims_date_max or "n/a")}</span>'
        f'<span>as-of {bundle.as_of_date.isoformat()}</span>'
        f'<span>provider_id '
        f'{html.escape(bundle.provider_id or "(unassigned)")}</span>'
        '<span>benchmark bands: HFMA MAP Key 2021 (acute care)</span>'
        f'{events_html}'
        '</footer>'
    )
