"""RCM Benchmarks — /rcm-benchmarks.

Industry benchmark library for the core RCM metrics. Calls
``data_public/rcm_benchmarks.get_all_benchmarks()`` which returns a
dict keyed by hospital-type segment (community / academic /
critical_access / ltac / asc / behavioral / physician_group /
home_health) with P25 / P50 / P75 bands for:

  - initial_denial_rate
  - clean_claim_rate
  - days_in_ar
  - collection_rate
  - write_off_pct
  - cost_to_collect
  - denial_overturn_rate

Source: HFMA MAP 2023, Advisory Board 2022 Hospital Benchmarking
Survey, and segment-specific publications cited in each record's
``benchmark_notes`` field.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_section_header,
)
from ._helpers import (
    empty_note,
    render_page_explainer,
    small_panel,
)
from ._sanity import REGISTRY as _METRIC_REGISTRY, render_number


# Map the backend's field-prefix names to the sanity REGISTRY metric
# names. Most line up; the exceptions (write_off_pct / collection_rate)
# use a different name in the registry than the module exposes.
_FIELD_TO_METRIC = {
    "initial_denial_rate":  "denial_rate",
    "clean_claim_rate":     "clean_claim_rate",
    "days_in_ar":           "days_in_ar",
    "collection_rate":      "net_collection_rate",
    "write_off_pct":        "final_writeoff_rate",
    "cost_to_collect":      "cost_to_collect",
    "denial_overturn_rate": "first_pass_resolution",
}


def _render_band_cell(value: Any, field_prefix: str) -> str:
    """Dispatch a rcm_benchmarks cell through the sanity guard when we
    have a registry mapping; otherwise fall back to raw formatting."""
    metric = _FIELD_TO_METRIC.get(field_prefix)
    if metric and metric in _METRIC_REGISTRY:
        return render_number(value, metric)
    # Fallback — shouldn't be reached given the static _METRICS list
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


_METRICS: List[Tuple[str, str, str, str, bool]] = [
    # (field_prefix, display_name, unit, inverted — lower-is-better, is_percentage)
    ("initial_denial_rate",    "Initial Denial Rate",    "%",    True,  True),
    ("clean_claim_rate",       "Clean Claim Rate",       "%",    False, True),
    ("days_in_ar",             "Days in AR",             "days", True,  False),
    ("collection_rate",        "Net Collection Rate",    "%",    False, True),
    ("write_off_pct",          "Write-off %",            "%",    True,  True),
    ("cost_to_collect",        "Cost to Collect",        "%",    True,  True),
    ("denial_overturn_rate",   "Denial Overturn Rate",   "%",    False, True),
]

_SEGMENT_META: Dict[str, str] = {
    "community":         "General acute-care community hospitals · 100-500 beds",
    "academic":          "Teaching hospitals · tertiary + quaternary care",
    "critical_access":   "Rural CAH · < 25 beds · Medicare-heavy",
    "ltac":              "Long-term acute care · complex medical patients",
    "asc":               "Ambulatory surgery centers · outpatient only",
    "behavioral":        "Behavioral health hospitals + inpatient psych",
    "physician_group":   "Physician practice groups · multi-specialty",
    "home_health":       "Home health agencies · PDGM-era",
}


def _fmt_band(value: Any, *, is_pct: bool, digits_pct: int = 1, digits_days: int = 1) -> str:
    try:
        f = float(value)
        if is_pct:
            return f"{f*100:.{digits_pct}f}%"
        return f"{f:.{digits_days}f}"
    except (TypeError, ValueError):
        return "—"


def _segment_card(seg_key: str, b: Any) -> str:
    label = _html.escape(str(b.label))
    blurb = _html.escape(_SEGMENT_META.get(seg_key, ""))
    notes = _html.escape(str(b.benchmark_notes or ""))

    # Build the 7-metric table
    rows = []
    for field, name, unit, inverted, is_pct in _METRICS:
        p25 = getattr(b, f"{field}_p25", None)
        p50 = getattr(b, f"{field}_p50", None)
        p75 = getattr(b, f"{field}_p75", None)
        # Color the P50 band: green if it's the "good" end for this metric
        p50_col = P["text"]
        try:
            p50_f = float(p50)
            # Rank logic: for inverted metrics, lower = better; for others,
            # higher = better. We don't have sector-absolute thresholds, so
            # we just shade the P50 in a neutral color and let the user
            # compare segments. No color on P25/P75.
        except (TypeError, ValueError):
            p50_f = None
        rows.append(
            f'<tr>'
            f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
            f'font-size:11px;">{_html.escape(name)}'
            + (
                f' <span style="color:{P["text_faint"]};font-size:9px;'
                f'margin-left:4px;">↓ better</span>' if inverted else
                f' <span style="color:{P["text_faint"]};font-size:9px;'
                f'margin-left:4px;">↑ better</span>'
            )
            + f'</td>'
            f'<td style="text-align:right;" data-val="{p25 or 0}">'
            f'{_render_band_cell(p25, field)}</td>'
            f'<td style="text-align:right;font-weight:600;" '
            f'data-val="{p50 or 0}">{_render_band_cell(p50, field)}</td>'
            f'<td style="text-align:right;" data-val="{p75 or 0}">'
            f'{_render_band_cell(p75, field)}</td>'
            f'</tr>'
        )
    table = (
        f'<div class="ck-table-wrap"><table class="ck-table">'
        f'<thead><tr><th>Metric</th>'
        f'<th class="num">P25</th><th class="num">P50 · Median</th>'
        f'<th class="num">P75</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )

    return (
        f'<div id="seg-{_html.escape(seg_key)}" style="margin-bottom:18px;">'
        f'<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:6px;">'
        f'<span style="font-family:var(--ck-mono);font-size:12px;'
        f'font-weight:700;color:{P["text"]};letter-spacing:0.04em;text-transform:uppercase;">'
        f'{label}</span>'
        f'<span style="color:{P["text_dim"]};font-size:11px;">{blurb}</span>'
        f'</div>'
        f'{table}'
        + (
            f'<div style="color:{P["text_faint"]};font-size:10px;margin-top:4px;'
            f'font-family:var(--ck-mono);line-height:1.4;">Source: {notes}</div>'
            if notes else ""
        )
        + f'</div>'
    )


def _cross_segment_table(benchmarks: Dict[str, Any]) -> str:
    """Wide table with segments as rows and metric P50s as columns — the
    "how do segments compare" read. Only P50s to keep density manageable.
    """
    headers = "".join(
        f'<th class="num">{_html.escape(name)}'
        + (
            f' <span style="color:{P["text_faint"]};font-size:8px;">(lo good)</span>'
            if inv else
            f' <span style="color:{P["text_faint"]};font-size:8px;">(hi good)</span>'
        )
        + f'</th>'
        for _, name, _, inv, _ in _METRICS
    )
    rows = []
    for seg_key, b in benchmarks.items():
        cells = []
        for field, _, _, _, is_pct in _METRICS:
            p50 = getattr(b, f"{field}_p50", None)
            cells.append(
                f'<td style="text-align:right;" data-val="{p50 or 0}">'
                f'{_render_band_cell(p50, field)}</td>'
            )
        rows.append(
            f'<tr>'
            f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
            f'font-size:11px;font-weight:600;">'
            f'<a href="#seg-{_html.escape(seg_key)}" style="color:{P["accent"]};'
            f'text-decoration:none;">{_html.escape(str(b.label))}</a>'
            f'</td>'
            f'{"".join(cells)}'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr><th>Segment</th>{headers}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def render_rcm_benchmarks(
    store: Any = None,
    current_user: Optional[str] = None,
) -> str:
    try:
        from ...data_public.rcm_benchmarks import get_all_benchmarks
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "RCM benchmarks unavailable",
            empty_note(f"rcm_benchmarks module failed: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            body, title="RCM Benchmarks",
            active_nav="/rcm-benchmarks",
            subtitle="Module unavailable",
        )

    try:
        benchmarks = get_all_benchmarks()
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "RCM benchmarks — load failed",
            empty_note(f"get_all_benchmarks raised: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            body, title="RCM Benchmarks",
            active_nav="/rcm-benchmarks",
            subtitle="Load raised",
        )

    if not benchmarks:
        body = small_panel(
            "RCM benchmarks — empty",
            empty_note("No benchmark data returned."),
            code="NIL",
        )
        return chartis_shell(
            body, title="RCM Benchmarks",
            active_nav="/rcm-benchmarks",
            subtitle="No benchmarks",
        )

    intro = (
        f'<p style="color:{P["text_dim"]};font-size:12px;line-height:1.6;'
        f'margin-bottom:10px;">'
        f'Industry RCM benchmarks for the seven canonical metrics, '
        f'segmented by hospital / facility type. Source data pulled from '
        f'HFMA MAP and Advisory Board surveys (see per-segment notes at '
        f'the bottom of each section).'
        f'</p>'
    )

    n_segments = len(benchmarks)
    kpis = (
        ck_kpi_block("Segments", str(n_segments), "hospital / facility types")
        + ck_kpi_block("Metrics", str(len(_METRICS)), "per segment")
        + ck_kpi_block("Bands", f"{len(_METRICS) * 3}", "P25/P50/P75 values per seg")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    # Jump-link strip
    jump_strip = (
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;">'
        + "".join(
            f'<a href="#seg-{_html.escape(k)}" '
            f'style="background:{P["panel"]};border:1px solid {P["border"]};'
            f'border-radius:2px;padding:4px 8px;font-family:var(--ck-mono);'
            f'font-size:10px;color:{P["accent"]};text-decoration:none;'
            f'letter-spacing:0.04em;">{_html.escape(str(b.label))} &rarr;</a>'
            for k, b in benchmarks.items()
        )
        + f'</div>'
    )

    cross_panel = small_panel(
        f"Cross-segment P50 comparison · {n_segments} segments",
        _cross_segment_table(benchmarks),
        code="XCS",
    )

    segments_html = "".join(
        _segment_card(k, b) for k, b in benchmarks.items()
    )
    segments_panel = (
        f'<div class="ck-panel">'
        f'<div class="ck-panel-title">Per-segment P25/P50/P75 bands '
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};margin-left:8px;">'
        f'SEG</span></div>'
        f'<div style="padding:14px 18px;">{segments_html}</div>'
        f'</div>'
    )

    explainer = render_page_explainer(
        what=(
            "Industry P25/P50/P75 bands for the seven canonical RCM "
            "metrics (initial-denial rate, clean-claim rate, days in "
            "AR, net collection rate, write-off %, cost to collect, "
            "denial-overturn rate) segmented by facility type "
            "(community, academic, CAH, LTAC, ASC, behavioral, "
            "physician group, home health)."
        ),
        scale=(
            "For each metric the P50 is the industry median and the "
            "P25/P75 are the quartile boundaries. Metrics are labelled "
            "'↓ better' when lower values are favourable (denial rate, "
            "days in AR, write-offs, cost to collect) and '↑ better' "
            "otherwise."
        ),
        use=(
            "Use this as the benchmark file when comparing a target's "
            "actuals. A target whose days-in-AR sits above P75 for its "
            "segment is not merely 'high' — it is worse than 75% of "
            "peers, which sizes the recoverable AR opportunity."
        ),
        source=(
            "data_public/rcm_benchmarks.py::get_all_benchmarks; "
            "band values sourced from HFMA MAP 2023, Advisory Board "
            "Hospital Benchmarking Survey 2022, MGMA 2022–2023, ASCA "
            "2023, Waystar 2020–2024, and segment-specific citations "
            "in each record's benchmark_notes field."
        ),
        page_key="rcm-benchmarks",
    )

    body = (
        explainer
        + intro
        + kpi_strip
        + jump_strip
        + ck_section_header(
            "CROSS-SEGMENT COMPARISON",
            "segment medians side-by-side",
        )
        + cross_panel
        + ck_section_header(
            "PER-SEGMENT DETAIL",
            "all 7 metrics × 3 bands per hospital type",
            count=n_segments,
        )
        + segments_panel
    )

    from .._chartis_kit import ck_related_views
    related = ck_related_views([
        ("Payer Intelligence",   "/payer-intelligence"),
        ("Market Data",          "/market-data/map"),
        ("Deal Search",          "/deal-search"),
        ("Portfolio Analytics",  "/portfolio-analytics"),
        ("Sector Intel",         "/sector-intel"),
    ])

    return chartis_shell(
        body + related,
        title="RCM Benchmarks",
        active_nav="/rcm-benchmarks",
        subtitle=f"{n_segments} segments · {len(_METRICS)} metrics · HFMA / Advisory Board priors",
    )
