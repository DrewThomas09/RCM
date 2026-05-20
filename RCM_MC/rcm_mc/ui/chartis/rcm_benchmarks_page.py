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
    ck_page_title,
    ck_section_header,
)
_EXPLAINER_CSS = """<style>
.ck-rcmb-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-rcmb-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""

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


def _segment_metric_charts(benchmarks: Dict[str, Any]) -> str:
    """Small-multiples SVG grid: one horizontal-bar chart per metric,
    showing each segment's P50 value with P25→P75 error bars.

    Replaces the "huge list of tables" partner-flagged read on
    /rcm-benchmarks. Reading a 7-metric × 8-segment table by row
    is dense; the small-multiples grid gives an at-a-glance shape
    of which segments outperform on each metric. Color codes:
    teal-ink when better than the cross-segment median for that
    metric (with direction respected via `inverted`), brick red
    when worse.
    """
    if not benchmarks:
        return ""
    segments = list(benchmarks.items())
    if not segments:
        return ""

    charts: List[str] = []
    for field, name, unit, inv, is_pct in _METRICS:
        # Collect (segment_label, p25, p50, p75) tuples
        rows = []
        for seg_key, b in segments:
            p25 = getattr(b, f"{field}_p25", None)
            p50 = getattr(b, f"{field}_p50", None)
            p75 = getattr(b, f"{field}_p75", None)
            if p50 is None:
                continue
            rows.append((str(b.label), float(p25 or p50),
                         float(p50), float(p75 or p50)))
        if not rows:
            continue
        # Sort by p50 descending (or ascending if lower-is-better)
        rows.sort(key=lambda r: r[2], reverse=not inv)
        # Cross-segment median for color reference
        sorted_p50s = sorted(r[2] for r in rows)
        mid = sorted_p50s[len(sorted_p50s) // 2]

        # Chart dims
        width = 360
        row_h = 22
        pad_l, pad_r, pad_t, pad_b = 130, 60, 28, 20
        inner_w = width - pad_l - pad_r
        height = pad_t + len(rows) * row_h + pad_b

        # X-axis range: padded around min(p25)/max(p75)
        all_vals = [r[1] for r in rows] + [r[3] for r in rows]
        x_lo = min(all_vals)
        x_hi = max(all_vals)
        span = x_hi - x_lo or max(0.5, x_hi * 0.2)
        x_lo -= span * 0.08
        x_hi += span * 0.08

        def sx(v: float) -> float:
            return pad_l + (v - x_lo) / (x_hi - x_lo) * inner_w

        def _fmt_value(v: float) -> str:
            if is_pct:
                return f"{v:.1f}%"
            if unit == "days":
                return f"{v:.0f}d"
            return f"{v:.2f}"

        # 3 vertical gridlines at quartile-ish positions
        grid = []
        for frac in (0.0, 0.5, 1.0):
            x = pad_l + frac * inner_w
            v = x_lo + frac * (x_hi - x_lo)
            grid.append(
                f'<line x1="{x:.1f}" x2="{x:.1f}" '
                f'y1="{pad_t}" y2="{pad_t + len(rows) * row_h}" '
                f'stroke="#d6cfc0" stroke-dasharray="2,4" />'
                f'<text x="{x:.1f}" y="{pad_t + len(rows) * row_h + 14}" '
                f'fill="#7a8699" text-anchor="middle" font-size="9" '
                f'font-family="JetBrains Mono, monospace">'
                f'{_fmt_value(v)}</text>'
            )

        elements = []
        for i, (label, p25v, p50v, p75v) in enumerate(rows):
            cy = pad_t + i * row_h + row_h / 2
            # Color by direction-aware comparison vs cross-segment median
            if inv:
                better = p50v < mid
            else:
                better = p50v > mid
            color = "#155752" if better else "#b5321e"
            # Error bar (P25 → P75)
            x25 = sx(p25v)
            x50 = sx(p50v)
            x75 = sx(p75v)
            elements.append(
                f'<line x1="{x25:.1f}" x2="{x75:.1f}" '
                f'y1="{cy:.1f}" y2="{cy:.1f}" '
                f'stroke="{color}" stroke-width="2" '
                f'stroke-opacity="0.45" stroke-linecap="round" />'
            )
            # Whisker caps
            elements.append(
                f'<line x1="{x25:.1f}" x2="{x25:.1f}" '
                f'y1="{cy - 4:.1f}" y2="{cy + 4:.1f}" '
                f'stroke="{color}" stroke-width="2" '
                f'stroke-opacity="0.55" />'
                f'<line x1="{x75:.1f}" x2="{x75:.1f}" '
                f'y1="{cy - 4:.1f}" y2="{cy + 4:.1f}" '
                f'stroke="{color}" stroke-width="2" '
                f'stroke-opacity="0.55" />'
            )
            # P50 marker
            elements.append(
                f'<circle cx="{x50:.1f}" cy="{cy:.1f}" r="4" '
                f'fill="{color}" stroke="#fff" stroke-width="1.5">'
                f'<title>{_html.escape(label)}: '
                f'P25 {_fmt_value(p25v)} · '
                f'P50 {_fmt_value(p50v)} · '
                f'P75 {_fmt_value(p75v)}</title>'
                f'</circle>'
            )
            # Segment label (right-aligned in left gutter)
            disp = label if len(label) <= 18 else label[:16] + "…"
            elements.append(
                f'<text x="{pad_l - 8:.1f}" y="{cy + 3:.1f}" '
                f'fill="#1a2332" text-anchor="end" font-size="10" '
                f'font-family="Inter, sans-serif">'
                f'{_html.escape(disp)}</text>'
            )
            # P50 value at right
            elements.append(
                f'<text x="{pad_l + inner_w + 6:.1f}" y="{cy + 3:.1f}" '
                f'fill="{color}" text-anchor="start" font-size="10" '
                f'font-family="JetBrains Mono, monospace" '
                f'font-weight="700">{_fmt_value(p50v)}</text>'
            )

        better_dir = "lower" if inv else "higher"
        title_block = (
            f'<text x="{pad_l:.1f}" y="18" '
            f'fill="#1a2332" text-anchor="start" font-size="12" '
            f'font-family="Inter, sans-serif" font-weight="600">'
            f'{_html.escape(name)}</text>'
            f'<text x="{pad_l + inner_w + 60:.1f}" y="18" '
            f'fill="#7a8699" text-anchor="end" font-size="9" '
            f'font-family="JetBrains Mono, monospace" '
            f'letter-spacing="0.06em">{better_dir} = better</text>'
        )

        chart = (
            f'<svg viewBox="0 0 {width} {height}" '
            f'style="width:100%;max-width:{width}px;'
            f'background:transparent;">'
            f'{title_block}'
            f'{"".join(grid)}'
            f'{"".join(elements)}'
            f'</svg>'
        )
        charts.append(
            f'<div style="background:#fff;border:1px solid '
            f'var(--sc-rule,#d6cfc0);padding:12px;">{chart}</div>'
        )

    return (
        f'<div style="display:grid;'
        f'grid-template-columns:repeat(auto-fit,minmax(360px,1fr));'
        f'gap:10px;margin:8px 0 16px;">'
        f'{"".join(charts)}'
        f'</div>'
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
        breadcrumbs=[
            ("Home", "/app"),
            ("Tools", "/methodology"),
            ("RCM Benchmarks", None),
        ],
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
        breadcrumbs=[
            ("Home", "/app"),
            ("Tools", "/methodology"),
            ("RCM Benchmarks", None),
        ],
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
        breadcrumbs=[
            ("Home", "/app"),
            ("Tools", "/methodology"),
            ("RCM Benchmarks", None),
        ],
            subtitle="No benchmarks",
        )

    # Editorial `render_page_explainer` below carries the source +
    # methodology — dropped the duplicate `intro` paragraph that
    # used to render below it (same content, partner-flagged as
    # redundant "two summaries" on RCM Benchmarks).
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

    # Visual + tabular: small-multiples chart grid (one per metric)
    # above the cross-segment numbers table. Partners read which
    # segments outperform on which metrics at a glance instead of
    # scanning a 7-column-wide table.
    cross_chart = _segment_metric_charts(benchmarks)
    cross_panel = small_panel(
        f"Cross-segment P50 comparison · {n_segments} segments",
        cross_chart + _cross_segment_table(benchmarks),
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

    page_title = ck_page_title(
        "RCM Benchmarks",
        eyebrow="RCM BENCHMARKS",
        meta=f"{n_segments} segments · {len(_METRICS)} metrics · HFMA / Advisory Board priors",
    )
    body = (
        page_title
        + explainer
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

    return chartis_shell(
        body,
        title="RCM Benchmarks",
        active_nav="/rcm-benchmarks",
        breadcrumbs=[
            ("Home", "/app"),
            ("Tools", "/methodology"),
            ("RCM Benchmarks", None),
        ],
        extra_css=_EXPLAINER_CSS,
    )
