"""Metric glossary + contextual tooltips.

First-time users see a number and don't know what it means, why
it matters, or how it's calculated. Existing partners forget the
edge cases. The fix is a tooltip on every metric with three
fields:

  • **Definition** — what the metric is in one sentence.
  • **Why it matters** — what decision it informs in PE diligence.
  • **How it's calculated** — the formula or data source.

The card footer adds the typical band, a *clickable* source
dataset (``ck_source_link``, so the partner can verify the number
at its origin), and a deep link to the metric's canonical card on
/metric-glossary.

This module ships a central registry of metric definitions plus
two helpers:

  • ``metric_tooltip(metric_key, label, value)`` — renders a value
    next to a small info icon. Hover reveals the definition card.
  • ``define_metric(metric_key, definition, why, how)`` — registers
    a new metric at runtime so callers can extend the glossary
    without editing this file.

All tooltip mechanics are pure HTML+CSS — no JS. Hover-on-icon
shows the card, position absolute. Works on mobile via tap (CSS
:hover triggers on touch) and on the keyboard via ``:focus-within``
on the focusable icon (WCAG 2.1 SC 1.4.13).

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

from ._chartis_kit import ck_source_link


@dataclass
class MetricDefinition:
    """One canonical metric description.

    ``source`` is the dataset the number actually comes from. It is
    rendered through ``ck_source_link`` so the partner can click
    through to the origin (the "where does this number come from?"
    question the glossary exists to answer). Use a label the
    ``_chartis_kit.SOURCE_URLS`` registry resolves — decorated forms
    like ``"CMS HCRIS Worksheet S-3 Part I"`` resolve by longest
    substring match, so the worksheet detail survives *and* links.
    An unrecognised label falls back to escaped plain text, so a
    non-CMS source (HFMA, MGMA-style standards bodies) is safe to
    name here too.
    """
    key: str
    label: str
    definition: str
    why_it_matters: str
    how_calculated: str
    units: str = ""           # e.g. "%", "$", "days"
    typical_range: str = ""   # e.g. "5-15%" — partner shorthand
    source: str = ""          # e.g. "CMS HCRIS Worksheet G-2"


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
            "rework cost: the highest-leverage RCM lever."),
        how_calculated=(
            "Denied claims / total claims submitted. "
            "Source: HFMA MAP Keys; partner-supplied or "
            "predicted from public-data features."),
        units="%",
        typical_range="5-15% (best in class <5%)",
        source="HFMA MAP Keys"),
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
            "Direct EBITDA leverage: every 1pp reduction "
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
        typical_range="-5% to +12%",
        source="CMS HCRIS Worksheet G-2"),
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
        typical_range="8-18%",
        source="CMS HCRIS Worksheet G-2"),
    "case_mix_index": MetricDefinition(
        key="case_mix_index",
        label="Case Mix Index",
        definition=(
            "Average DRG weight across discharges: a "
            "complexity proxy."),
        why_it_matters=(
            "Each 0.05 CMI uplift ≈ 0.8% of Medicare "
            "revenue. CDI initiatives target this lever."),
        how_calculated=(
            "Σ (DRG weight × discharges) / total "
            "discharges. CMS DRG weights are the rate "
            "table."),
        units="ratio",
        typical_range="1.20-2.50",
        source="CMS MS-DRG weight table"),
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
            ">1.00x typically requires above-average margin "
            "to service. Drives covenant attention."),
        how_calculated=(
            "Long-term debt / NPSR."),
        # A multiple, not a bare ratio — house rule is 2dp + "x".
        units="x",
        typical_range="0.20-1.50x"),
    "interest_coverage": MetricDefinition(
        key="interest_coverage",
        label="Interest Coverage",
        definition=(
            "EBIT divided by interest expense: how many "
            "times over EBIT covers interest."),
        why_it_matters=(
            "Below 2.00x is the credit-attention zone; "
            "<1.50x raises restructuring discussion."),
        how_calculated=(
            "EBIT / interest expense. From HCRIS G-2 + "
            "footnotes."),
        units="x",
        typical_range="2.00-8.00x",
        source="CMS HCRIS Worksheet G-2"),
    # Volume / staffing
    "occupancy_rate": MetricDefinition(
        key="occupancy_rate",
        label="Occupancy Rate",
        definition=(
            "Share of staffed beds occupied: patient days "
            "/ bed-days available."),
        why_it_matters=(
            "Drives fixed-cost absorption. Below 50% the "
            "hospital can't cover overhead; above 80% "
            "constrains throughput."),
        how_calculated=(
            "Total patient days / bed-days available. "
            "Source: HCRIS Worksheet S-3 Part I."),
        units="%",
        typical_range="55-80%",
        source="CMS HCRIS Worksheet S-3 Part I"),
    "fte_per_aob": MetricDefinition(
        key="fte_per_aob",
        label="FTE per AOB",
        definition=(
            "Full-time-equivalent staff per adjusted "
            "occupied bed: the canonical staffing "
            "intensity metric."),
        why_it_matters=(
            ">7.0 = overstaffed (right-sizing opportunity); "
            "<4.5 = lean (often a quality risk)."),
        how_calculated=(
            "Total FTEs / adjusted occupied beds. Source: "
            "HCRIS Worksheet S-3 Part II + S-3 Part I."),
        units="ratio",
        typical_range="4.5-7.0",
        source="CMS HCRIS Worksheet S-3 Parts I-II"),
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
        typical_range="45-60%",
        source="CMS HCRIS Worksheet A"),
    # Payer mix
    "medicare_day_pct": MetricDefinition(
        key="medicare_day_pct",
        label="Medicare Day %",
        definition=(
            "Share of total inpatient days attributed to "
            "Medicare beneficiaries."),
        why_it_matters=(
            "Drives reimbursement index: higher Medicare "
            "% means lower NPR per gross charge (~0.79 vs "
            "1.00 commercial)."),
        how_calculated=(
            "Medicare patient days / total patient days. "
            "Source: HCRIS Worksheet S-3 Part I."),
        units="%",
        typical_range="30-55%",
        source="CMS HCRIS Worksheet S-3 Part I"),
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
        typical_range="10-30%",
        source="CMS HCRIS Worksheet S-3 Part I"),
    # Volume + topline (added loop 114 to cover the
    # competitive_intel and portfolio_overview surfaces that
    # already use metric_label_link for these columns)
    "net_patient_revenue": MetricDefinition(
        key="net_patient_revenue",
        label="Net Patient Revenue",
        definition=(
            "Patient-service revenue net of contractual "
            "allowances and bad debt: the topline line "
            "underwriters anchor every multiple to."),
        why_it_matters=(
            "Primary scale driver. Multiples (EV/NPR, "
            "EV/EBITDA) and lever-impact estimates all "
            "flow from NPR. Trend is the leading "
            "indicator of demand and pricing power."),
        how_calculated=(
            "Gross charges − contractual allowances − "
            "bad debt provision. Source: HCRIS Worksheet "
            "G-3 Line 3 or partner-supplied audited "
            "financials."),
        units="$",
        typical_range="varies by bed count and acuity",
        source="CMS HCRIS Worksheet G-3 Line 3"),
    "revenue_per_bed": MetricDefinition(
        key="revenue_per_bed",
        label="Revenue per Bed",
        definition=(
            "Net patient revenue normalized by licensed "
            "bed count."),
        why_it_matters=(
            "Captures pricing × throughput in one number. "
            "Best-in-class acute hospitals run "
            "$1.5-2.5M/bed; lower suggests under-occupancy "
            "or weak payer mix; higher suggests outpatient "
            "skew or premium markets."),
        how_calculated=(
            "Net patient revenue / licensed beds."),
        units="$/bed",
        typical_range="$0.8M-$2.5M/bed",
        source="CMS HCRIS Worksheets G-3 + S-3"),
    "expense_per_bed": MetricDefinition(
        key="expense_per_bed",
        label="Expense per Bed",
        definition=(
            "Total operating expense normalized by licensed "
            "bed count."),
        why_it_matters=(
            "Cost-density benchmark. High expense/bed with "
            "low revenue/bed signals labor or supply "
            "inefficiency: the synergy diligence target."),
        how_calculated=(
            "Operating expenses / licensed beds. "
            "Source: HCRIS Worksheet G-3."),
        units="$/bed",
        typical_range="$0.7M-$2.0M/bed",
        source="CMS HCRIS Worksheet G-3"),
    "commercial_pct": MetricDefinition(
        key="commercial_pct",
        label="Commercial Payer %",
        definition=(
            "Share of total revenue or patient days "
            "attributable to commercial (non-government) "
            "payers."),
        why_it_matters=(
            "Highest reimbursement index (~1.0). Each pp "
            "of commercial mix lifts NPR/charge directly. "
            "Concentration risk if a single payer >40%."),
        how_calculated=(
            "Commercial revenue / total revenue (or "
            "commercial days / total days)."),
        units="%",
        typical_range="20-50%"),
    "payer_diversity": MetricDefinition(
        key="payer_diversity",
        label="Payer Diversity Index",
        definition=(
            "Inverse-Herfindahl concentration index across "
            "the payer mix; higher = more diverse, lower = "
            "more concentrated."),
        why_it_matters=(
            "Concentration is the silent risk: one "
            "Medicare Advantage contract renegotiation can "
            "move 20% of revenue. Higher diversity = "
            "lower contract-renewal risk."),
        how_calculated=(
            "1 − Σ(payer_share²) across the mix. "
            "Range 0 (single payer) to ~0.8 (very "
            "diverse)."),
        units="index (0-1)",
        typical_range="0.55-0.78 (best-in-class >0.7)"),
    "total_patient_days": MetricDefinition(
        key="total_patient_days",
        label="Total Patient Days",
        definition=(
            "Annual total of inpatient days across all "
            "service lines."),
        why_it_matters=(
            "Volume baseline for occupancy, payer-mix "
            "calculations, and capacity-planning. The "
            "denominator most other partner ratios are "
            "normalized against."),
        how_calculated=(
            "Sum of daily inpatient census across the "
            "fiscal year. Source: HCRIS Worksheet S-3 "
            "Part I."),
        units="days",
        typical_range="varies by bed count",
        source="CMS HCRIS Worksheet S-3 Part I"),
    "net_to_gross_ratio": MetricDefinition(
        key="net_to_gross_ratio",
        label="Net-to-Gross Ratio",
        definition=(
            "Net patient revenue as a fraction of gross "
            "charges: the realization rate."),
        why_it_matters=(
            "Payer-mix-driven; highly stable within a "
            "hospital. Sudden compression signals "
            "contract loss or payer aggression. Wide "
            "variance vs peers (>5pp) warrants a "
            "contract-by-contract walk."),
        how_calculated=(
            "Net patient revenue / gross charges."),
        units="%",
        typical_range="22-38% (acute care)"),
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
    source: str = "",
) -> None:
    """Register a metric at runtime.

    Used by feature modules that ship their own metrics not in
    the core glossary (e.g., a one-off MA penetration % defined
    by the MA enrollment ingest).

    ``source`` is optional but strongly encouraged — it is what
    makes the tooltip's provenance line clickable back to the
    origin dataset. Keyword-only with a default so the ~existing
    callers keep working unchanged.
    """
    _GLOSSARY[key] = MetricDefinition(
        key=key, label=label,
        definition=definition,
        why_it_matters=why_it_matters,
        how_calculated=how_calculated,
        units=units,
        typical_range=typical_range,
        source=source)


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
  border-radius:50%;background:var(--border);color:var(--faint);
  font-size:10px;font-weight:600;line-height:14px;
  text-align:center;cursor:help;font-family:system-ui;
  user-select:none;}
.metric-tt:hover .metric-tt-icon,
.metric-tt:focus-within .metric-tt-icon{background:var(--blue);
  color:var(--blue-soft);}
.metric-tt-icon:focus-visible{outline:2px solid var(--blue);
  outline-offset:2px;}
.metric-tt-card{position:absolute;display:none;left:0;
  top:calc(100% + 6px);background:var(--bg);
  border:1px solid var(--border);border-radius:6px;padding:12px 14px;
  width:280px;font-size:12px;line-height:1.5;
  box-shadow:0 8px 24px rgba(0,0,0,0.5);z-index:1000;
  color:var(--ink);font-weight:normal;}
/* :focus-within keeps the card reachable without a mouse —
   WCAG 2.1 SC 1.4.13 (content on hover or focus). */
.metric-tt:hover .metric-tt-card,
.metric-tt:focus-within .metric-tt-card{display:block;}
.metric-tt-card h4{margin:0 0 6px 0;font-size:12px;
  color:var(--blue-soft);text-transform:uppercase;
  letter-spacing:0.06em;font-weight:600;}
.metric-tt-card p{margin:0 0 8px 0;color:var(--muted);}
.metric-tt-card .tt-section{margin-top:8px;}
.metric-tt-card .tt-section-label{font-size:10px;
  text-transform:uppercase;letter-spacing:0.06em;
  color:var(--teal);font-weight:600;margin-bottom:2px;}
.metric-tt-card .tt-foot{margin-top:8px;padding-top:6px;
  border-top:1px solid var(--border);}
.metric-tt-card .tt-range,
.metric-tt-card .tt-source{display:block;
  color:var(--faint);font-size:11px;}
.metric-tt-card .tt-source{margin-top:3px;}
.metric-tt-card .tt-source a{color:var(--blue-soft);
  text-decoration:none;}
.metric-tt-card .tt-source a:hover,
.metric-tt-card .tt-source a:focus-visible{
  text-decoration:underline;}
.metric-tt-card .tt-more{display:block;margin-top:6px;
  font-size:11px;}
.metric-tt-card .tt-more a{color:var(--blue-soft);
  text-decoration:none;}
.metric-tt-card .tt-more a:hover,
.metric-tt-card .tt-more a:focus-visible{
  text-decoration:underline;}
</style>"""


_TT_CSS_INJECTED = "metric_tt_css_injected"


def _tt_section(label: str, text: str) -> str:
    """One labelled paragraph in the hover card.

    Returns "" for a blank field rather than an empty labelled
    paragraph — a runtime-registered metric (``define_metric``) may
    legitimately leave ``why_it_matters`` or ``how_calculated``
    empty, and a heading with nothing under it reads as a bug to
    the partner.
    """
    if not (text or "").strip():
        return ""
    return (
        '<div class="tt-section">'
        f'<div class="tt-section-label">{_html.escape(label)}</div>'
        f'<p>{_html.escape(text)}</p></div>')


def _tooltip_card(d: MetricDefinition) -> str:
    """The hover card content.

    Footer carries the three things a partner asks next: the
    typical band, the *clickable* source dataset (via
    ``ck_source_link``, so provenance is one click from every
    number on the platform), and a deep link into the canonical
    /metric-glossary card.
    """
    parts = [
        f'<h4>{_html.escape(d.label)}</h4>',
        # Empty-state: a registered-but-undocumented metric still
        # renders a card that says so, rather than a blank panel.
        f'<p>{_html.escape(d.definition)}</p>' if d.definition.strip()
        else '<p>No definition recorded for this metric yet.</p>',
        _tt_section("Why it matters", d.why_it_matters),
        _tt_section("How it's calculated", d.how_calculated),
    ]

    foot: List[str] = []
    if d.typical_range:
        foot.append(
            f'<div class="tt-range">'
            f'Typical range: {_html.escape(d.typical_range)}'
            f'</div>')
    if d.source:
        foot.append(
            f'<div class="tt-source">Source: '
            f'{ck_source_link(d.source)}</div>')
    # Deep link to the canonical card. Own anchor rather than
    # _glossary_link.metric_label_link so the accessible name can
    # name the metric — a page with a dozen tooltips otherwise
    # exposes a dozen identical "Full definition" links.
    foot.append(
        f'<div class="tt-more">'
        f'<a href="/metric-glossary#{_html.escape(d.key)}" '
        f'aria-label="Open the full {_html.escape(d.label)} '
        f'definition in the metric glossary">'
        f'Full definition <span aria-hidden="true">&rarr;</span>'
        f'</a></div>')
    parts.append(f'<div class="tt-foot">{"".join(foot)}</div>')
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
        # title= so a column-clipped value is still readable, and
        # the units the registry knows about travel with it.
        value_title = f"{d.label}: {value}"
        if d.units and d.units not in value:
            value_title += f" ({d.units})"
        value_html = (
            f'<span style="font-variant-numeric:tabular-nums;" '
            f'title="{_html.escape(value_title)}">'
            f'{_html.escape(value)}</span>')

    # The card is display:none, so assistive tech never reads it.
    # Carry the definition on the icon itself and make the icon
    # focusable so keyboard users can open the card at all — the
    # old generic "What does this mean?" label was identical on
    # every icon on the page.
    icon_label = _html.escape(
        f"{d.label} — {d.definition}" if d.definition.strip()
        else f"{d.label} — definition not recorded yet")

    return (
        f'{css}<span class="metric-tt">'
        f'<span>{display_label}</span>'
        f'<span class="metric-tt-icon" role="img" tabindex="0" '
        f'aria-label="{icon_label}">i</span>'
        f'{value_html}'
        f'<span class="metric-tt-card" role="tooltip">'
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
