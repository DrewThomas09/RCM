"""Metric glossary + contextual tooltips.

First-time users see a number and don't know what it means, why
it matters, or how it's calculated. Existing partners forget the
edge cases. The fix is a tooltip on every metric with three
fields:

  • **Definition** — what the metric is in one sentence.
  • **Why it matters** — what decision it informs in PE diligence.
  • **How it's calculated** — the formula or data source.

This module ships a central registry of metric definitions plus
two helpers:

  • ``metric_tooltip(metric_key, label, value)`` — renders a value
    next to a small info icon. Hover reveals the definition card.
  • ``define_metric(metric_key, definition, why, how)`` — registers
    a new metric at runtime so callers can extend the glossary
    without editing this file.

All tooltip mechanics are pure HTML+CSS — no JS. Hover-on-icon
shows the card, position absolute. Works on mobile via tap (CSS
:hover triggers on touch).

Public API::

    from rcm_mc.ui.metric_glossary import (
        MetricDefinition,
        get_metric_definition,
        define_metric,
        metric_tooltip,
        metric_label_with_info,
        list_metrics,
    )
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MetricDefinition:
    """One canonical metric description."""
    key: str
    label: str
    definition: str
    why_it_matters: str
    how_calculated: str
    units: str = ""           # e.g. "%", "$", "days"
    typical_range: str = ""   # e.g. "5-15%" — partner shorthand


# ── Core glossary ────────────────────────────────────────────
# Calibrated against research bands + HFMA MAP Keys + the
# project's existing rcm_ebitda_bridge documentation.

_GLOSSARY: Dict[str, MetricDefinition] = {
    # RCM core
    "denial_rate": MetricDefinition(
        key="denial_rate",
        label="Denial Rate",
        definition=(
            "Share of submitted claims initially denied "
            "by the payer (before appeals)."),
        why_it_matters=(
            "Each 1pp reduction recovers ~35% × NPSR in "
            "avoidable revenue. Denials drive bad debt and "
            "rework cost — the highest-leverage RCM lever."),
        how_calculated=(
            "Denied claims / total claims submitted. "
            "Source: HFMA MAP Keys; partner-supplied or "
            "predicted from public-data features."),
        units="%",
        typical_range="5-15% (best in class <5%)"),
    "days_in_ar": MetricDefinition(
        key="days_in_ar",
        label="Days in A/R",
        definition=(
            "Average days accounts receivable spends "
            "outstanding before collection."),
        why_it_matters=(
            "Each day reduction releases ~NPSR/365 of "
            "working capital. Long DSO ties up cash and "
            "predicts bad debt write-offs."),
        how_calculated=(
            "(AR balance / annual NPSR) × 365. National "
            "median ~45 days; >55 = working-capital "
            "trapped; <38 = best in class."),
        units="days",
        typical_range="38-65 (best <38)"),
    "net_collection_rate": MetricDefinition(
        key="net_collection_rate",
        label="Net Collection Rate",
        definition=(
            "Share of net realizable revenue actually "
            "collected (after contractual allowances)."),
        why_it_matters=(
            "Every 1pp lift drops to EBITDA. Below 95% "
            "signals process leak; <93% is distressed."),
        how_calculated=(
            "Cash collected / (gross charges − contractual "
            "adjustments). Excludes bad debt write-offs."),
        units="%",
        typical_range="92-99% (best ≥97%)"),
    "clean_claim_rate": MetricDefinition(
        key="clean_claim_rate",
        label="Clean Claim Rate",
        definition=(
            "Share of claims accepted on first submission "
            "without rework."),
        why_it_matters=(
            "High clean-claim rate cuts follow-up FTE cost "
            "and shortens AR. Each 1pp lift saves the cost "
            "of one rework × claims volume."),
        how_calculated=(
            "Claims accepted first-pass / total claims "
            "submitted. Front-end coding + eligibility "
            "verification drive this."),
        units="%",
        typical_range="85-96% (best ≥96%)"),
    "cost_to_collect": MetricDefinition(
        key="cost_to_collect",
        label="Cost to Collect",
        definition=(
            "RCM operating cost as a share of net patient "
            "service revenue."),
        why_it_matters=(
            "Direct EBITDA leverage — every 1pp reduction "
            "drops to the bottom line. Above 4% suggests "
            "automation upside."),
        how_calculated=(
            "Total RCM cost (FTEs + tech + outsourced "
            "vendors + bad debt processing) / NPSR."),
        units="%",
        typical_range="2-5% (best ≤3%)"),
    "first_pass_resolution_rate": MetricDefinition(
        key="first_pass_resolution_rate",
        label="First-Pass Resolution",
        definition=(
            "Share of claims paid in full on the first "
            "attempt (no resubmission, no appeal)."),
        why_it_matters=(
            "Catches both denial and underpayment leak. "
            "Each 1pp lift saves rework-cost and shortens "
            "AR aging."),
        how_calculated=(
            "Claims paid in full first-pass / total claims. "
            "Tighter than clean_claim_rate because it "
            "tracks payment, not acceptance."),
        units="%",
        typical_range="80-92%"),
    # Financial / margin
    "operating_margin": MetricDefinition(
        key="operating_margin",
        label="Operating Margin",
        definition=(
            "Operating income as a share of net patient "
            "service revenue."),
        why_it_matters=(
            "The single best summary of asset health. <0% "
            "is distressed; >5% is sustainable; >10% is "
            "best-in-class for community hospitals."),
        how_calculated=(
            "(Net patient revenue − operating expenses) / "
            "net patient revenue. Source: HCRIS Worksheet "
            "G-2."),
        units="%",
        typical_range="-5% to +12%"),
    "ebitda_margin": MetricDefinition(
        key="ebitda_margin",
        label="EBITDA Margin",
        definition=(
            "Earnings before interest, tax, depreciation, "
            "amortization, divided by NPSR."),
        why_it_matters=(
            "PE benchmark for sponsor-quality cash "
            "generation. <8% raises questions; >15% is the "
            "platform-grade band."),
        how_calculated=(
            "EBITDA / NPSR. EBITDA reconstructed from HCRIS "
            "operating income + D&A + lease normalization."),
        units="%",
        typical_range="8-18%"),
    "case_mix_index": MetricDefinition(
        key="case_mix_index",
        label="Case Mix Index",
        definition=(
            "Average DRG weight across discharges — a "
            "complexity proxy."),
        why_it_matters=(
            "Each 0.05 CMI uplift ≈ 0.75% of Medicare "
            "revenue. CDI initiatives target this lever."),
        how_calculated=(
            "Σ (DRG weight × discharges) / total "
            "discharges. CMS DRG weights are the rate "
            "table."),
        units="ratio",
        typical_range="1.20-2.50"),
    # Liquidity / debt
    "days_cash_on_hand": MetricDefinition(
        key="days_cash_on_hand",
        label="Days Cash on Hand",
        definition=(
            "How many days of operating expense the "
            "hospital can cover from current cash."),
        why_it_matters=(
            "<30 days = covenant-trip risk; <15 = "
            "restructuring territory. Above 100 = healthy."),
        how_calculated=(
            "Cash + cash equivalents / (annual operating "
            "expense / 365)."),
        units="days",
        typical_range="30-200 (≥100 healthy)"),
    "debt_to_revenue": MetricDefinition(
        key="debt_to_revenue",
        label="Debt to Revenue",
        definition=(
            "Long-term debt as a multiple of net patient "
            "service revenue."),
        why_it_matters=(
            ">1.0x typically requires above-average margin "
            "to service. Drives covenant attention."),
        how_calculated=(
            "Long-term debt / NPSR."),
        units="ratio",
        typical_range="0.2-1.5x"),
    "interest_coverage": MetricDefinition(
        key="interest_coverage",
        label="Interest Coverage",
        definition=(
            "EBIT divided by interest expense — how many "
            "times over EBIT covers interest."),
        why_it_matters=(
            "Below 2.0x is the credit-attention zone; <1.5x "
            "raises restructuring discussion."),
        how_calculated=(
            "EBIT / interest expense. From HCRIS G-2 + "
            "footnotes."),
        units="x",
        typical_range="2.0-8.0x"),
    # Volume / staffing
    "occupancy_rate": MetricDefinition(
        key="occupancy_rate",
        label="Occupancy Rate",
        definition=(
            "Share of staffed beds occupied — patient days "
            "/ bed-days available."),
        why_it_matters=(
            "Drives fixed-cost absorption. Below 50% the "
            "hospital can't cover overhead; above 80% "
            "constrains throughput."),
        how_calculated=(
            "Total patient days / bed-days available. "
            "Source: HCRIS Worksheet S-3 Part I."),
        units="%",
        typical_range="55-80%"),
    "fte_per_aob": MetricDefinition(
        key="fte_per_aob",
        label="FTE per AOB",
        definition=(
            "Full-time-equivalent staff per adjusted "
            "occupied bed — the canonical staffing "
            "intensity metric."),
        why_it_matters=(
            ">7.0 = overstaffed (right-sizing opportunity); "
            "<4.5 = lean (often a quality risk)."),
        how_calculated=(
            "Total FTEs / adjusted occupied beds. Source: "
            "HCRIS Worksheet S-3 Part II + S-3 Part I."),
        units="ratio",
        typical_range="4.5-7.0"),
    "labor_pct_of_npsr": MetricDefinition(
        key="labor_pct_of_npsr",
        label="Labor % of NPSR",
        definition=(
            "Total labor cost as a share of net patient "
            "service revenue."),
        why_it_matters=(
            ">60% is the labor-pressured band. Right-sizing "
            "or wage normalization typically takes 1-3pp "
            "out."),
        how_calculated=(
            "Total labor cost (Worksheet A col 1+2 + "
            "benefits) / NPSR."),
        units="%",
        typical_range="45-60%"),
    # Payer mix
    "medicare_day_pct": MetricDefinition(
        key="medicare_day_pct",
        label="Medicare Day %",
        definition=(
            "Share of total inpatient days attributed to "
            "Medicare beneficiaries."),
        why_it_matters=(
            "Drives reimbursement index — higher Medicare "
            "% means lower NPR per gross charge (~0.79 vs "
            "1.00 commercial)."),
        how_calculated=(
            "Medicare patient days / total patient days. "
            "Source: HCRIS Worksheet S-3 Part I."),
            units="%",
        typical_range="30-55%"),
    "medicaid_day_pct": MetricDefinition(
        key="medicaid_day_pct",
        label="Medicaid Day %",
        definition=(
            "Share of total inpatient days attributed to "
            "Medicaid beneficiaries."),
        why_it_matters=(
            "Lowest reimbursement index (~0.58). High "
            "Medicaid % drives DSO + denial rate up."),
        how_calculated=(
            "Medicaid patient days / total patient days."),
        units="%",
        typical_range="10-30%"),
}


def get_metric_definition(
    metric_key: str,
) -> Optional[MetricDefinition]:
    """Look up a metric definition by canonical key.

    Returns None for unknown keys — callers fall back to
    rendering the value without a tooltip rather than crashing.
    """
    return _GLOSSARY.get(metric_key)


def define_metric(
    key: str,
    *,
    label: str,
    definition: str,
    why_it_matters: str,
    how_calculated: str,
    units: str = "",
    typical_range: str = "",
) -> None:
    """Register a metric at runtime.

    Used by feature modules that ship their own metrics not in
    the core glossary (e.g., a one-off MA penetration % defined
    by the MA enrollment ingest).
    """
    _GLOSSARY[key] = MetricDefinition(
        key=key, label=label,
        definition=definition,
        why_it_matters=why_it_matters,
        how_calculated=how_calculated,
        units=units,
        typical_range=typical_range)


def list_metrics() -> List[str]:
    """All registered metric keys, sorted."""
    return sorted(_GLOSSARY.keys())


# ── Tooltip rendering ────────────────────────────────────────

# Pure HTML+CSS tooltip — hover the info icon, the card appears.
# Stylesheet is namespaced under .metric-tt and embedded once
# per tooltip (acceptable since the styles are small and this
# avoids a global stylesheet dependency).
_TT_CSS = """
<style>
.metric-tt{position:relative;display:inline-flex;
  align-items:center;gap:6px;}
.metric-tt-icon{display:inline-block;width:14px;height:14px;
  border-radius:50%;background:#374151;color:#9ca3af;
  font-size:10px;font-weight:600;line-height:14px;
  text-align:center;cursor:help;font-family:system-ui;
  user-select:none;}
.metric-tt:hover .metric-tt-icon{background:#1e3a8a;
  color:#bfdbfe;}
.metric-tt-card{position:absolute;display:none;left:0;
  top:calc(100% + 6px);background:#0f172a;
  border:1px solid #374151;border-radius:6px;padding:12px 14px;
  width:280px;font-size:12px;line-height:1.5;
  box-shadow:0 8px 24px rgba(0,0,0,0.5);z-index:1000;
  color:#f3f4f6;font-weight:normal;}
.metric-tt:hover .metric-tt-card{display:block;}
.metric-tt-card h4{margin:0 0 6px 0;font-size:12px;
  color:#bfdbfe;text-transform:uppercase;
  letter-spacing:0.06em;font-weight:600;}
.metric-tt-card p{margin:0 0 8px 0;color:#d1d5db;}
.metric-tt-card .tt-section{margin-top:8px;}
.metric-tt-card .tt-section-label{font-size:10px;
  text-transform:uppercase;letter-spacing:0.06em;
  color:#60a5fa;font-weight:600;margin-bottom:2px;}
.metric-tt-card .tt-range{display:block;margin-top:6px;
  padding-top:6px;border-top:1px solid #374151;
  color:#9ca3af;font-size:11px;}
</style>"""


_TT_CSS_INJECTED = "metric_tt_css_injected"


def _tooltip_card(d: MetricDefinition) -> str:
    """The hover card content."""
    parts = [
        f'<h4>{_html.escape(d.label)}</h4>',
        f'<p>{_html.escape(d.definition)}</p>',
        '<div class="tt-section">'
        '<div class="tt-section-label">Why it matters</div>'
        f'<p>{_html.escape(d.why_it_matters)}</p></div>',
        '<div class="tt-section">'
        '<div class="tt-section-label">How it\'s calculated</div>'
        f'<p>{_html.escape(d.how_calculated)}</p></div>',
    ]
    if d.typical_range:
        parts.append(
            f'<div class="tt-range">'
            f'Typical range: {_html.escape(d.typical_range)}'
            f'</div>')
    return "".join(parts)


def metric_tooltip(
    metric_key: str,
    *,
    label: Optional[str] = None,
    value: Optional[str] = None,
    inject_css: bool = True,
) -> str:
    """Render a label + tooltip-icon + (optional) value.

    If ``metric_key`` isn't registered, falls back to the label
    alone — partner sees the metric name with no info icon, no
    crash.

    Args:
      metric_key: registry key.
      label: override the registry label (e.g., truncated for
        a narrow column header).
      value: rendered value (formatted by caller). When None,
        only the label + icon are shown.
      inject_css: whether to include the stylesheet. Pages
      rendering many tooltips can disable this on all but the
      first to avoid duplicate <style> blocks.

    Returns: HTML snippet.
    """
    d = get_metric_definition(metric_key)
    if d is None:
        # Graceful fallback — just the label
        bits = [_html.escape(
            label or metric_key.replace("_", " ").title())]
        if value is not None:
            bits.append(f"<span>{_html.escape(value)}</span>")
        return ' '.join(bits)

    display_label = _html.escape(label or d.label)
    css = _TT_CSS if inject_css else ""
    value_html = ""
    if value is not None:
        value_html = (
            f'<span style="font-variant-numeric:tabular-nums;">'
            f'{_html.escape(value)}</span>')

    return (
        f'{css}<span class="metric-tt">'
        f'<span>{display_label}</span>'
        f'<span class="metric-tt-icon" '
        f'aria-label="What does this mean?">i</span>'
        f'{value_html}'
        f'<span class="metric-tt-card">'
        f'{_tooltip_card(d)}</span></span>')


def metric_label_with_info(
    metric_key: str,
    *,
    label: Optional[str] = None,
    inject_css: bool = True,
) -> str:
    """Just the label + info icon (no value). Used on table
    headers."""
    return metric_tooltip(
        metric_key, label=label, value=None,
        inject_css=inject_css)
