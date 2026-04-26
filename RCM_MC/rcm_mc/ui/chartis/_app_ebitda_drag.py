"""EBITDA drag — stacked horizontal bar + per-component breakdown + paired table.

Spec: docs/design-handoff/EDITORIAL_STYLE_PORT.md §6.8
Reference: docs/design-handoff/reference/04-command-center.html (drag section)

5-segment stacked bar (one segment per drag component) + per-component
rows with swatch + label + % + $. Paired with raw breakdown table.

See module-level conventions in _app_kpi_strip.py docstring (1-6).

──────────────────────────────────────────────────────────────────────
Phase 3 commit 6: real decomposition from packet.ebitda_bridge
──────────────────────────────────────────────────────────────────────

Phase 2 stub returned 5×20% uniform placeholders. Phase 3 wires the
actual ``per_metric_impacts`` from ``DealAnalysisPacket.ebitda_bridge``,
buckets each by ``metric_key``, sums dollars per bucket, computes
percentages.

Bucketing table (verified against real production data at the
commit-6 prefix-review pause point — see Phase 3 review notes):

  metric_key                    → spec component
  ────────────────────────────────────────────────
  denial_rate                   → Denial workflow gap
  first_pass_resolution_rate    → Denial workflow gap
  clean_claim_rate              → Denial workflow gap  [Decision A]
  case_mix_index                → Coding / CDI miss
  days_in_ar                    → A/R aging
  net_collection_rate           → Other (residual)     [Decision B]
  cost_to_collect               → Other (residual)
  *unrecognized*                → Other (logged)

Rationale on Decision A (clean_claim_rate → Denial workflow gap):

  A clean claim is definitionally a denial that didn't happen. The
  dollar saved shows up in denial-rework hours, not in coding-
  intensity audit findings. CDI is the upstream cause but not where
  the lever sits operationally.

Rationale on Decision B (net_collection_rate → Other):

  net_collection_rate is a composite — patient self-pay + payer
  contractual underpayment + bad-debt write-offs + charity-care
  write-offs all roll up here. Misattributing it to "Self-pay
  leakage" would actively mislead partners about which lever to
  pull. Q4.6 (registered in UI_REWORK_PLAN.md) tracks the eventual
  6th-component split into Payer underpayment + Patient self-pay
  once the bridge can decompose this further.

Empty Self-pay bucket policy (Decision C — visible at 0%):

  No metric_keys map to "Self-pay leakage" with current bridge data.
  The bucket renders at 0% on every real packet today rather than
  hiding. Visual rhythm across deals is a feature; "Self-pay: 0%"
  is itself diagnostic ("not a leakage source for this hospital");
  hide-when-empty creates fragile on/off behavior at the rounding
  boundary.

Empty / sparse states (unchanged from Phase 2):
  - No focused deal → "Select a deal above to see drag breakdown."
  - Focused deal with no bridge built yet → "Run the analysis pipeline
    first" with link to /diligence/thesis-pipeline

# TODO(phase 4): recovery quarters + recovery sparkline. Spec §6.8
# mentions both but Phase 3 keeps drag decomposition tight on the
# bucketing wiring; recovery is a separate data path (per-quarter
# realization curve from initiative actuals).
"""
from __future__ import annotations

import html as _html
import logging
from typing import Any, Dict, List, Optional, Tuple

from rcm_mc.ui._chartis_kit_editorial import number_maybe, pair_block


logger = logging.getLogger(__name__)


# 5 canonical drag components per spec §6.8 + cc-data.jsx. Segment
# colors come from the editorial status palette so the stacked bar
# stays editorial-toned (no rainbow / data-vis palette).
_DRAG_COMPONENTS: List[Dict[str, str]] = [
    {"key": "denial",      "label": "Denial workflow gap", "color": "var(--red)"},
    {"key": "coding",      "label": "Coding / CDI miss",   "color": "var(--amber)"},
    {"key": "ar_aging",    "label": "A/R aging",            "color": "var(--blue)"},
    {"key": "self_pay",    "label": "Self-pay leakage",     "color": "var(--teal-deep)"},
    {"key": "other",       "label": "Other",                "color": "var(--muted)"},
]

# Phase 3 bucketing table — metric_key → spec component key.
# Confirmed against real production data at the commit-6 prefix-review
# pause point. See module docstring for the full rationale on each
# row (especially Decisions A and B for clean_claim_rate +
# net_collection_rate).
_METRIC_KEY_TO_BUCKET: Dict[str, str] = {
    "denial_rate":                "denial",
    "first_pass_resolution_rate": "denial",
    # clean_claim_rate buckets to Denial workflow because the dollar
    # saved is in denial-rework hours; CDI is the upstream cause but
    # not where the lever shows up. (Phase 3 Decision A.)
    "clean_claim_rate":           "denial",
    "case_mix_index":             "coding",
    "days_in_ar":                 "ar_aging",
    # net_collection_rate is a composite — patient self-pay + payer
    # underpayment + write-offs. Buckets to "Other" rather than
    # silently misattributing to Self-pay. Q4.6 tracks the eventual
    # 6th-component decomposition. (Phase 3 Decision B.)
    "net_collection_rate":        "other",
    # cost_to_collect is an OpEx lever, not a revenue lever — fits
    # "Other" by elimination among the 5 spec components.
    "cost_to_collect":            "other",
}


def _bucket_for_metric_key(metric_key: str) -> str:
    """Map a metric_key to its drag component bucket.

    Unrecognized keys fall through to "other" AND emit an INFO-level
    log line so future bridge additions surface as a known signal
    (per Phase 3 review — catches the next bridge metric the moment
    it ships, before it silently rolls into Other and stays hidden).
    """
    bucket = _METRIC_KEY_TO_BUCKET.get(metric_key)
    if bucket is None:
        logger.info(
            "Unrecognized metric_key '%s' bucketed as 'Other' — "
            "consider adding to _METRIC_KEY_TO_BUCKET in "
            "rcm_mc/ui/chartis/_app_ebitda_drag.py",
            metric_key,
        )
        return "other"
    return bucket


def _decompose_drag(
    packet: Optional[Any],
) -> Optional[List[Tuple[str, str, str, float, float]]]:
    """Decompose the bridge into 5 drag components.

    Returns:
        None when no packet OR no bridge OR
        total absolute ebitda_impact == 0 (existing empty-state
        behavior preserved from Phase 2).
        Otherwise: list of 5 tuples (key, label, color, pct, dollars_M)
        in canonical _DRAG_COMPONENTS order. Sum of pcts adds to 1.0
        when at least one bucket has impact; pcts are absolute-value
        weighted (a bucket with -$2M and a bucket with +$2M each
        contribute equally to the bar even though they cancel
        signs).

    The empty Self-pay bucket policy (Decision C — visible at 0%):
        Buckets with zero attributed impact still render — keeps
        the 5-segment chrome consistent across deals so partners
        scanning multiple deals can compare side-by-side without
        the bar shape jumping.
    """
    if packet is None:
        return None
    bridge = getattr(packet, "ebitda_bridge", None)
    if bridge is None:
        return None

    impacts = getattr(bridge, "per_metric_impacts", None) or []
    if not impacts:
        return None

    # Sum dollars per bucket. Use ABSOLUTE values for percentage
    # weighting (a -$2M lever and a +$2M lever each show as equal
    # bar segments — the bar represents WHERE impact concentrates,
    # not net direction). Render the dollar value with sign
    # preserved + tone in number_maybe at the row level.
    bucket_dollars: Dict[str, float] = {c["key"]: 0.0 for c in _DRAG_COMPONENTS}
    bucket_dollars_abs: Dict[str, float] = {c["key"]: 0.0 for c in _DRAG_COMPONENTS}
    for impact in impacts:
        try:
            ebitda_impact = float(getattr(impact, "ebitda_impact", 0.0) or 0.0)
            metric_key = str(getattr(impact, "metric_key", "") or "")
        except (TypeError, ValueError):
            continue
        if not metric_key:
            continue
        bucket = _bucket_for_metric_key(metric_key)
        bucket_dollars[bucket] += ebitda_impact
        bucket_dollars_abs[bucket] += abs(ebitda_impact)

    total_abs = sum(bucket_dollars_abs.values())
    if total_abs <= 0:
        # Defensive: bridge had impacts but they all summed to zero.
        # Existing empty-state-as-data behavior (5 buckets at 0%).
        # Preserves the chrome rather than collapsing.
        return [
            (c["key"], c["label"], c["color"], 0.0, 0.0)
            for c in _DRAG_COMPONENTS
        ]

    return [
        (
            c["key"],
            c["label"],
            c["color"],
            bucket_dollars_abs[c["key"]] / total_abs,
            # Convert to $M for display. The packet stores impact
            # in $; divide by 1e6 for the M suffix in number_maybe.
            bucket_dollars[c["key"]] / 1_000_000,
        )
        for c in _DRAG_COMPONENTS
    ]


def _render_drag_bar(
    components: List[Tuple[str, str, str, float, float]],
) -> str:
    """5-segment stacked horizontal bar."""
    segments = "".join(
        f'<div class="seg" style="width:{pct * 100:.1f}%;'
        f'background:{color};">{int(pct * 100)}%</div>'
        for _, _, color, pct, _ in components
    )
    return f'<div class="app-drag-bar">{segments}</div>'


def _render_drag_rows(
    components: List[Tuple[str, str, str, float, float]],
) -> str:
    """Per-component rows below the bar."""
    rows = "".join(
        f'<div class="row">'
        f'<div class="swatch" style="background:{color}"></div>'
        f'<div class="label">{_html.escape(label)}</div>'
        f'<div class="pct">{pct * 100:.0f}%</div>'
        f'<div class="v">{number_maybe(dollars, format="ev") if dollars else "—"}</div>'
        '</div>'
        for _, label, color, pct, dollars in components
    )
    return f'<div class="app-drag-rows">{rows}</div>'


def _render_breakdown_table(
    components: List[Tuple[str, str, str, float, float]],
) -> str:
    """Paired right-side raw breakdown table."""
    body = "".join(
        f'<tr><td class="lbl">{_html.escape(label)}</td>'
        f'<td class="r">{pct * 100:.1f}%</td>'
        f'<td class="r">'
        f'{number_maybe(dollars, format="ev") if dollars else "—"}'
        f'</td></tr>'
        for _, label, _, pct, dollars in components
    )
    return (
        '<table>'
        '<thead><tr>'
        '<th>Component</th>'
        '<th class="r">% of drag</th>'
        '<th class="r">$ impact</th>'
        '</tr></thead>'
        f'<tbody>{body}</tbody>'
        '</table>'
    )


def render_ebitda_drag(packet: Optional[Any]) -> str:
    """5-segment stacked drag bar + per-component rows + paired breakdown.

    Args:
        packet: DealAnalysisPacket for the focused deal, or None.
            None means no focused deal — empty-state renders.
            packet without ebitda_bridge attribute means the analysis
            hasn't run — different empty-state with run-the-pipeline
            link.

    Returns:
        Complete <div class="pair">…</div>.
    """
    components = _decompose_drag(packet)

    if components is None:
        if packet is None:
            empty_msg = (
                "Select a deal above to see EBITDA drag breakdown."
            )
        else:
            empty_msg = (
                'No bridge data yet. <a href="/diligence/thesis-pipeline">'
                'Run the analysis pipeline</a> to populate.'
            )
        viz_html = (
            f'<div class="app-drag-empty">{empty_msg}</div>'
        )
        empty_table = (
            '<table>'
            '<thead><tr>'
            '<th>Component</th>'
            '<th class="r">% of drag</th>'
            '<th class="r">$ impact</th>'
            '</tr></thead>'
            '<tbody>'
            '<tr><td colspan="3" class="lbl" style="text-align:center;'
            'padding:1rem 0;font-style:italic;color:var(--muted);">'
            f'{empty_msg}</td></tr>'
            '</tbody>'
            '</table>'
        )
        return pair_block(
            viz_html,
            label="EBITDA DRAG · 5-COMPONENT DECOMP",
            source="ebitda_bridge",
            data_table=empty_table,
        )

    viz_html = (
        f'<h3 style="margin:0 0 .25rem;font-family:\'Source Serif 4\',serif;'
        f'font-weight:400;font-size:1.2rem;color:var(--ink);">Drag decomposition</h3>'
        f'<p style="color:var(--muted);font-size:.82rem;margin:0 0 1rem;">'
        f'Median per-hospital impact across simulations</p>'
        f'{_render_drag_bar(components)}'
        f'{_render_drag_rows(components)}'
    )

    return pair_block(
        viz_html,
        label="EBITDA DRAG · 5-COMPONENT DECOMP",
        source="ebitda_bridge",
        data_table=_render_breakdown_table(components),
    )
