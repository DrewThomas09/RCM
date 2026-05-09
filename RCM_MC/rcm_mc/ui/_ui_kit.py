"""Compatibility shim — re-exports ``shell`` as chartis_shell.

Historically this module held a light-theme ``BASE_CSS`` + ``shell()``
renderer. Both are dead code after the unify-on-chartis migration
(chore/ui-polish-and-sanity-guards). The legacy ``shell()`` function
is kept as a thin wrapper so callers that still import
``from rcm_mc.ui._ui_kit import shell`` continue to work — they now
render through ``chartis_shell`` like everything else.

Callers that still use this shim:
  - rcm_mc/server.py (top-level import)
  - rcm_mc/ui/csv_to_html.py
  - rcm_mc/ui/text_to_html.py
  - rcm_mc/ui/sensitivity_dashboard.py
  - rcm_mc/ui/json_to_html.py
  - rcm_mc/infra/output_index.py
  - rcm_mc/reports/lp_update.py

Once those migrate to `from rcm_mc.ui._chartis_kit import chartis_shell`
directly, this module can be deleted entirely.
"""
from __future__ import annotations

import html as _html
import math as _math
from typing import Any, Optional

from ._chartis_kit import chartis_shell


def shell(
    body: str,
    title: str,
    *,
    back_href: Optional[str] = None,
    subtitle: Optional[str] = None,
    extra_css: str = "",
    extra_js: str = "",
    generated: bool = True,  # noqa: ARG001 — kept for signature parity
    omit_h1: bool = False,  # noqa: ARG001 — kept for signature parity
) -> str:
    """Legacy ``shell()`` — routes through ``chartis_shell``.

    Historically this function wrapped a body in a light-theme document
    and later delegated to ``shell_v2``. After the chartis unification
    it just calls ``chartis_shell`` with a compatible signature. The
    ``back_href`` argument is rendered as a small breadcrumb link above
    the body content; the ``generated`` and ``omit_h1`` arguments are
    accepted for backward compat but ignored.
    """
    import html as _html
    if back_href:
        body = (
            f'<nav class="breadcrumb" aria-label="Breadcrumb" '
            f'style="margin-bottom:12px;font-size:11px;">'
            f'<a href="{_html.escape(back_href)}" '
            f'style="color:var(--ck-accent);text-decoration:none;">'
            f'&larr; Back to index</a></nav>{body}'
        )
    return chartis_shell(
        body,
        title,
        subtitle=subtitle or "",
        extra_css=extra_css,
        extra_js=extra_js,
    )


# ── format_value() ────────────────────────────────────────────────
#
# P9: silent failure problem. Across Portfolio overview, My Dashboard,
# Heatmap, etc., a metric that is not yet computed renders as ``—`` —
# indistinguishable from a real zero or a calculated dash. Partners
# can't tell if the number is genuinely zero or just unpopulated.
#
# This helper draws the line: ``None`` and ``NaN`` get a styled
# "not yet computed" span; real zeros and real numbers get formatted
# per ``kind``. Callers are expected to migrate one stat block at a
# time; the existing per-page _fmt_money/_fmt_pct helpers can keep
# their dash-on-None behaviour until they're switched over.

_VALID_KINDS = ("money", "percent", "count", "multiple", "text")


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and _math.isnan(value):
        return True
    # pandas NA/NaT: float NaN above covers numpy.nan; pandas.NA has
    # truthiness exception so we can't ``not value``. Detect by name
    # to avoid a hard pandas dependency in this stdlib-only shim.
    cls = type(value).__name__
    if cls in ("NAType", "NaTType"):
        return True
    return False


def _format_money(v: float) -> str:
    # Per CLAUDE.md: financials → 2dp. Auto-pick M/B suffix the way
    # other formatters in the kit do — under $1B in millions, above
    # in billions.
    if abs(v) >= 1_000_000_000:
        return f"${v / 1_000_000_000:,.2f}B"
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:,.2f}M"
    return f"${v:,.2f}"


def _format_percent(v: float) -> str:
    # Per CLAUDE.md: percentages → 1dp. Convention here: caller passes
    # a 0..1 fraction (the dominant pattern in this codebase). If a
    # caller passes a raw percent (e.g. 15.3 for 15.3%), they must
    # divide before calling — keeps the helper unambiguous.
    return f"{v * 100:.1f}%"


def _format_multiple(v: float) -> str:
    # Per CLAUDE.md: multiples → 2dp + "x" suffix.
    return f"{v:.2f}x"


def _format_count(v: Any) -> str:
    # Counts are integers — no decimals, with thousands separator.
    return f"{int(v):,}"


def format_value(
    value: Any,
    *,
    kind: str,
    missing_label: str = "not yet computed",
) -> str:
    """Render a metric value with explicit unpopulated-vs-zero handling.

    ``kind`` selects the formatter — see ``_VALID_KINDS``.

    When ``value`` is ``None`` or NaN, returns a styled span
    ``<span class="muted unpopulated">{missing_label}</span>`` so the
    caller can tell at a glance that the metric has not been computed.
    Real zeros render as ``0``, ``$0.00``, ``0.0%`` etc. — the partner
    can then trust that the absence of a number means "missing", not
    "happens to be zero".
    """
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"format_value(kind={kind!r}) must be one of {_VALID_KINDS}"
        )
    if _is_missing(value):
        return (
            '<span class="muted unpopulated">'
            f'{_html.escape(missing_label)}</span>'
        )
    if kind == "text":
        return _html.escape(str(value))
    try:
        v = float(value)
    except (TypeError, ValueError):
        # Anything that isn't None/NaN but also isn't numeric falls
        # back to escaped text — surface the value rather than hiding
        # the type problem behind a missing-label.
        return _html.escape(str(value))
    if kind == "money":
        return _format_money(v)
    if kind == "percent":
        return _format_percent(v)
    if kind == "multiple":
        return _format_multiple(v)
    # kind == "count"
    return _format_count(v)


# ── kpi_strip() ───────────────────────────────────────────────────
#
# P11: 25+ pages stack KPIs vertically (Library, Alerts, Watchlist,
# Hospital Screener pre-load, IRR Analysis, Hold Analysis, Portfolio
# Analytics, Sponsor Track Record, etc.) — five vertical rows when
# the same five values would read in parallel as a horizontal strip.
#
# This helper renders a CSS-grid row of KPI tiles with consistent
# typography, tone-coloring, and a responsive breakpoint pair so the
# strip degrades to 2 columns at narrow viewports and 1 below 480px.

_VALID_TONES = ("neutral", "positive", "negative", "warning")


def kpi_strip(items: list[dict], *, dense: bool = False) -> str:
    """Render KPIs as a single horizontal row.

    ``items`` is a list of dicts with keys:
      - ``label`` (str, required) — small uppercase eyebrow
      - ``value`` (str, required) — already-formatted display value
        (caller can use ``format_value`` for missing-aware rendering)
      - ``sublabel`` (str, optional) — small muted subtitle
      - ``tone`` (str, optional) — one of ``neutral``, ``positive``,
        ``negative``, ``warning``; drives the value's color

    ``dense=True`` (or len(items) > 5) switches to a tighter typography
    so a six- or eight-tile strip still fits on a 1280px viewport.
    """
    if not items:
        return ""
    n = len(items)
    is_dense = dense or n > 5
    classes = "kpi-strip" + (" kpi-strip-dense" if is_dense else "")
    # Inline grid-template-columns so the column count stays declarative
    # regardless of how many tiles a caller passes; the CSS only owns
    # the responsive breakpoint behaviour.
    style = f'style="grid-template-columns:repeat({n},1fr);"'
    cells = []
    for it in items:
        label = _html.escape(str(it.get("label", "")))
        value = str(it.get("value", ""))  # caller is responsible for safety
        sublabel = it.get("sublabel")
        tone = it.get("tone") or "neutral"
        if tone not in _VALID_TONES:
            tone = "neutral"
        sub_html = (
            f'<div class="kpi-sublabel">{_html.escape(str(sublabel))}</div>'
            if sublabel else ""
        )
        cells.append(
            f'<div class="kpi-item tone-{tone}">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'{sub_html}'
            f'</div>'
        )
    return f'<div class="{classes}" {style}>{"".join(cells)}</div>'


# ── empty_state() ─────────────────────────────────────────────────
#
# P12: a reusable "never show nothing" card. The codebase already
# ships ``rcm_mc.ui.empty_states.empty_state(title, description, ...)``
# with a richer ``EmptyAction`` list and pre-built variants, but its
# vocabulary doesn't match the partner-voice spec PROMPTS.md asks
# for (``body``, ``cta_label``, ``cta_href``). Rather than fork the
# implementation we wrap the canonical one with the spec keyword
# vocabulary so the rest of Phase 2/3 can adopt the simpler signature.

def empty_state(
    *,
    icon: str,
    title: str,
    body: str,
    cta_label: Optional[str] = None,
    cta_href: Optional[str] = None,
) -> str:
    """Reusable empty-state card matching the Watchlist pattern.

    All arguments are keyword-only by design: the field names carry
    meaning (``body`` reads as partner copy, ``description`` reads as
    SaaS copy) and a positional API would tempt callers to forget
    which slot is the icon. Optional ``cta_label`` / ``cta_href``
    must be supplied together; one without the other renders no CTA.
    """
    from .empty_states import empty_state as _impl, EmptyAction  # noqa: E501

    actions: list = []
    if cta_label and cta_href:
        actions.append(EmptyAction(label=cta_label, url=cta_href, primary=True))
    return _impl(
        title=title,
        description=body,
        icon=icon,
        actions=actions,
    )


# ── preview_panel() ───────────────────────────────────────────────
#
# P13: form-only diligence pages (Ingestion, Benchmarks, Bridge Audit,
# Deal Monte Carlo, etc.) display a small form atop 70% empty space.
# A partner has no idea what the eventual output will look like.
# ``preview_panel`` renders a faint right-rail sketch of the result
# next to the form. The ``data-preview="true"`` attribute lets the
# print stylesheet hide previews from print output, and gives QA a
# stable hook for visual-regression filtering.

def preview_panel(*, title: str, sketch_html: str, caption: str) -> str:
    """Right-side ghosted output preview.

    ``title``: e.g. "What you'll see" or "Sample output".
    ``sketch_html``: a faint SVG/HTML preview — caller is responsible
    for HTML safety since the whole point is to inject markup.
    ``caption``: 1-2 sentence muted-italic description below.
    """
    return (
        '<aside class="preview-panel" data-preview="true" '
        'aria-label="Output preview">'
        f'<div class="preview-title">{_html.escape(title)}</div>'
        f'<div class="preview-ghost">{sketch_html}</div>'
        f'<div class="preview-caption">{_html.escape(caption)}</div>'
        '</aside>'
    )


# ── recent_runs() ─────────────────────────────────────────────────
#
# P14: form-only diligence pages today have no continuity — a partner
# who ran a Bridge Audit yesterday has no list of "audits I've run"
# anywhere on the page. ``recent_runs`` is the per-module continuity
# rail that sits beside the form. Empty state is intentionally one
# line, not a full empty-state card, because a populated form +
# preview panel already fill the page; a giant empty card would
# create visual noise.

def recent_runs(
    runs: list[dict],
    *,
    module: str,
    empty_label: Optional[str] = None,
) -> str:
    """Compact list of recent runs of a single diligence module.

    ``runs`` is a list of dicts with keys ``deal_name``, ``ran_at``
    (ISO-ish string), ``href`` (link to the run's detail page) and
    optional ``summary`` (one-line headline result).
    ``module`` names the section header ("Bridge audits", "Monte
    Carlo runs"). ``empty_label`` overrides the default empty copy.
    """
    header = (
        f'<div class="recent-runs-header">Recent {_html.escape(module)}</div>'
    )
    if not runs:
        msg = empty_label or (
            f"No {module} yet — run one above to populate this list."
        )
        return (
            '<section class="recent-runs">'
            f'{header}'
            f'<div class="recent-runs-empty muted">{_html.escape(msg)}</div>'
            '</section>'
        )
    rows = []
    for run in runs:
        deal = _html.escape(str(run.get("deal_name") or "(unnamed)"))
        ran_at = _html.escape(str(run.get("ran_at") or ""))
        href = run.get("href") or "#"
        summary = run.get("summary")
        summary_html = (
            f'<span class="recent-runs-summary">{_html.escape(str(summary))}</span>'
            if summary else ""
        )
        rows.append(
            f'<a class="recent-runs-row" href="{_html.escape(str(href))}">'
            f'<span class="recent-runs-deal">{deal}</span>'
            f'<span class="recent-runs-ts">{ran_at}</span>'
            f'{summary_html}'
            '</a>'
        )
    return (
        '<section class="recent-runs">'
        f'{header}'
        f'<div class="recent-runs-list">{"".join(rows)}</div>'
        '</section>'
    )


# ── data_table() ──────────────────────────────────────────────────
#
# P15: tables across the app have inconsistent styling — some are
# striped, some not; some have sticky headers, some not; sort
# affordances and right-aligned numerics are missing in places.
# ``data_table`` is the standardised body. Values pass through
# ``format_value`` per column kind so missing data renders as
# "not yet computed" instead of an em-dash. Sort is handled
# client-side via a small vanilla-JS routine bound on
# ``table.data-table[data-sortable]``.

_TABLE_KIND_TO_FORMAT = ("money", "percent", "count", "multiple", "text")


def data_table(
    *,
    columns: list[dict],
    rows: list[dict],
    sortable: bool = True,
    sticky_header: bool = True,
    striped: bool = True,
    hover: bool = True,
    dense: bool = False,
    actions: Optional[list[dict]] = None,
    table_id: Optional[str] = None,
) -> str:
    """Render a standardized table.

    ``columns`` is a list of dicts with:
      - ``key`` (str, required) — row-dict lookup key
      - ``label`` (str, required) — header text
      - ``align`` (str, optional) — ``left`` | ``right`` | ``center``
        (defaults: ``right`` for numeric kinds, ``left`` otherwise)
      - ``kind`` (str, optional) — drives ``format_value`` and the
        right-align default; one of ``money``, ``percent``, ``count``,
        ``multiple``, ``text``
      - ``sortable`` (bool, optional) — per-column sort opt-out

    ``rows`` is a list of dicts keyed by ``columns[i]["key"]``.

    Booleans control behaviour flags; the matching CSS lives in the
    shared kit so all data tables look identical without per-page
    duplication.
    """
    table_classes = ["data-table"]
    if sticky_header:
        table_classes.append("sticky-header")
    if striped:
        table_classes.append("striped")
    if hover:
        table_classes.append("hover")
    if dense:
        table_classes.append("dense")
    sortable_attr = ' data-sortable="true"' if sortable else ""
    table_id_attr = ""
    column_picker_html = ""
    if table_id:
        # P50: column picker. The kit JS reads the table_id to scope
        # localStorage keys; columns toggle on/off without a server
        # round-trip. Each <th> gets data-col-key so the JS can
        # show/hide entire columns by index.
        table_id_attr = f' data-table-id="{_html.escape(table_id)}"'
        picker_items = []
        for col in columns:
            key = _html.escape(str(col["key"]))
            label = _html.escape(str(col["label"]))
            picker_items.append(
                f'<label class="column-picker-item">'
                f'<input type="checkbox" class="column-picker-toggle" '
                f'data-col-key="{key}" checked> {label}</label>'
            )
        column_picker_html = (
            '<details class="column-picker">'
            '<summary>Columns</summary>'
            f'<div class="column-picker-menu">{"".join(picker_items)}</div>'
            '</details>'
        )
    header_cells = []
    for col in columns:
        key = _html.escape(str(col["key"]))
        label = _html.escape(str(col["label"]))
        kind = col.get("kind") or "text"
        align = col.get("align") or ("right" if kind in ("money", "percent", "count", "multiple") else "left")
        col_sortable = sortable and col.get("sortable", True)
        sort_class = " sortable" if col_sortable else ""
        sort_marker = (
            '<span class="sort-marker" aria-hidden="true">▲▼</span>'
            if col_sortable else ""
        )
        header_cells.append(
            f'<th class="align-{_html.escape(align)}{sort_class}" '
            f'data-key="{key}" data-col-key="{key}" '
            f'data-kind="{_html.escape(kind)}">'
            f'{label}{sort_marker}</th>'
        )
    # P42: when ``actions`` is supplied, render an extra column with
    # a ``…`` button that reveals per-row action links on hover. The
    # menu is hidden by default so dense tables don't clutter; the
    # CSS owns the show/hide behaviour. ``href_template`` placeholders
    # match Python str.format keys read from the row dict.
    if actions:
        header_cells.append(
            '<th class="align-right" data-key="__actions" '
            'data-kind="text" aria-label="Row actions">'
            '<span aria-hidden="true">⋯</span></th>'
        )
    body_rows = []
    for row in rows:
        cells = []
        for col in columns:
            key = col["key"]
            kind = col.get("kind") or "text"
            align = col.get("align") or ("right" if kind in ("money", "percent", "count", "multiple") else "left")
            raw = row.get(key)
            try:
                rendered = format_value(raw, kind=kind)
            except ValueError:
                rendered = format_value(raw, kind="text")
            num_cls = " sc-num" if kind in ("money", "percent", "count", "multiple") else ""
            col_key_attr = f' data-col-key="{_html.escape(str(key))}"' if table_id else ""
            cells.append(
                f'<td class="align-{_html.escape(align)}{num_cls}"'
                f'{col_key_attr}>{rendered}</td>'
            )
        if actions:
            action_links = []
            for act in actions:
                label = _html.escape(str(act.get("label", "Action")))
                tpl = str(act.get("href_template", "#"))
                try:
                    href = tpl.format(**row)
                except (KeyError, IndexError):
                    href = tpl
                action_links.append(
                    f'<a class="row-action-link" '
                    f'href="{_html.escape(href)}">{label}</a>'
                )
            cells.append(
                '<td class="align-right row-actions-cell">'
                '<div class="row-actions">'
                '<button class="row-actions-toggle" type="button" '
                'aria-label="Open row actions">⋯</button>'
                '<div class="row-actions-menu">'
                f'{"".join(action_links)}'
                '</div></div></td>'
            )
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    table_html = (
        f'<table class="{" ".join(table_classes)}"{sortable_attr}'
        f'{table_id_attr}>'
        f'<thead><tr>{"".join(header_cells)}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table>'
    )
    if column_picker_html:
        return (
            '<div class="data-table-wrap">'
            f'{column_picker_html}'
            f'{table_html}'
            '</div>'
        )
    return table_html


# ── recommendation_block() ────────────────────────────────────────
#
# P16: every analytical page shows data without conclusions. Risk
# Workbench has nine panels of color but no "pass on this deal."
# Bridge Audit shows variance but no "anchor IC at $54M not $67M."
# This block sits at the bottom of analytical pages and forces a
# conclusion. Confidence drives the left-rail color so a partner
# can clock the verdict tone before reading the words.

_VALID_CONFIDENCE = ("high", "medium", "low", "info")


def recommendation_block(
    *,
    verdict: str,
    action: str,
    confidence: str,
    reasoning: list[str],
    dollars: Optional[str] = None,
) -> str:
    """Banded conclusion card for analytical pages.

    ``verdict``: e.g. "Proceed at reduced price" / "Pass" / "Negotiate"
    ``action``: one-sentence specific next step.
    ``confidence``: ``high`` (green) | ``medium`` (amber) | ``low`` (red)
      | ``info`` (muted) — drives the left-rail color.
    ``reasoning``: 2-5 bullets supporting the verdict.
    ``dollars``: optional dollar-anchored implication; rendered as
      the rightmost hero number when supplied.
    """
    if confidence not in _VALID_CONFIDENCE:
        confidence = "info"
    bullets = "".join(
        f"<li>{_html.escape(str(item))}</li>" for item in reasoning
    )
    dollars_html = (
        f'<div class="rec-dollars">{_html.escape(dollars)}</div>'
        if dollars else ""
    )
    return (
        f'<aside class="recommendation-block confidence-{confidence}" '
        'role="note" aria-label="Recommendation">'
        '<div class="rec-rail" aria-hidden="true"></div>'
        '<div class="rec-body">'
        f'<div class="rec-verdict">{_html.escape(verdict)}</div>'
        f'<div class="rec-action">{_html.escape(action)}</div>'
        f'<ul class="rec-reasoning">{bullets}</ul>'
        '</div>'
        f'{dollars_html}'
        '</aside>'
    )


# ── provenance_marker() ───────────────────────────────────────────
#
# P17: every number reads as equally authoritative today. The
# platform's moat is that every value has a typed source
# (USER_INPUT, HCRIS, IRS990, REGRESSION_PREDICTED, BENCHMARK_MEDIAN,
# MONTE_CARLO_P50, CALCULATED). Surfacing the source family inline
# turns invisible rigor into a credibility asset.

# Source → glyph family. Five families per the spec:
#   filled circle  → observed (data we have, no inference)
#   half circle    → predicted (regression with conformal interval)
#   diamond        → simulated (Monte Carlo)
#   triangle       → derived (calculated from other values)
#   open circle    → benchmark (corpus median / quartile)
_PROVENANCE_GLYPHS: dict[str, tuple[str, str]] = {
    # source                  glyph     family
    "USER_INPUT":            ("●", "observed"),
    "HCRIS":                 ("●", "observed"),
    "IRS990":                ("●", "observed"),
    "REGRESSION_PREDICTED":  ("◐", "predicted"),
    "MONTE_CARLO_P50":       ("◆", "simulated"),
    "MONTE_CARLO_P10":       ("◆", "simulated"),
    "MONTE_CARLO_P90":       ("◆", "simulated"),
    "CALCULATED":            ("▴", "derived"),
    "BENCHMARK_MEDIAN":      ("○", "benchmark"),
    "BENCHMARK_P25":         ("○", "benchmark"),
    "BENCHMARK_P75":         ("○", "benchmark"),
}

_PROVENANCE_DEFAULT = ("·", "unknown")


def provenance_marker(
    source: str,
    *,
    confidence: Optional[float] = None,
    detail: str = "",
) -> str:
    """Render the inline provenance glyph for a metric.

    ``source`` matches the platform's Source enum string. Unknown
    sources fall back to a small middle-dot so a typo can't crash a
    page render. ``confidence`` (0..1) drives marker opacity so a
    low-confidence prediction reads as a fainter mark. ``detail``
    becomes the native HTML ``title`` attribute (browser tooltip).
    """
    glyph, family = _PROVENANCE_GLYPHS.get(source, _PROVENANCE_DEFAULT)
    style_bits = []
    if confidence is not None:
        # Clamp to [0.3, 1.0] so even very low-confidence markers
        # remain visible at all.
        op = max(0.3, min(1.0, float(confidence)))
        style_bits.append(f"opacity:{op:.2f}")
    style_attr = f' style="{";".join(style_bits)}"' if style_bits else ""
    title_attr = (
        f' title="{_html.escape(detail)}"' if detail else ""
    )
    return (
        f'<span class="prov prov-{family}" '
        f'data-source="{_html.escape(source)}"'
        f'{style_attr}{title_attr}>{glyph}</span>'
    )


# ── metric_with_interval() ────────────────────────────────────────
#
# P33: every predicted metric on the platform has a conformal P10/P90
# interval (85-96% empirical coverage, per the docs) but they are
# invisible in the UI. ``2.80x`` reads no different than an observed
# value. This helper renders the interval inline so a partner can
# clock the uncertainty alongside the point estimate.
#
# Convention: caller passes the same scalar units to ``value``,
# ``p10``, and ``p90``; this helper calls ``format_value`` on each
# with the supplied ``kind``. If either band is missing, fall back
# to rendering just the point estimate — partners shouldn't see
# half-intervals.

def metric_with_interval(
    value: Any,
    *,
    p10: Optional[Any],
    p90: Optional[Any],
    kind: str,
) -> str:
    """Render a predicted metric with its conformal interval inline.

    Output shape: ``2.80x <span class="metric-interval">(P10 1.95x,
    P90 3.85x)</span>``. The interval span is callable via CSS for
    print/contrast tweaks.
    """
    point = format_value(value, kind=kind)
    # If the point is missing, the interval is meaningless — drop it.
    if _is_missing(value):
        return point
    if _is_missing(p10) or _is_missing(p90):
        return point
    lo = format_value(p10, kind=kind)
    hi = format_value(p90, kind=kind)
    return (
        f'{point} <span class="metric-interval">'
        f'(P10 {lo}, P90 {hi})</span>'
    )


# ── caveats_disclosure() ──────────────────────────────────────────
#
# P18: the docs are admirably honest about modeling weaknesses. The
# UI is silent. A partner using Monte Carlo for a $300M decision
# should see "Execution noise is independent across levers; cross-
# lever correlation not modeled." Native ``<details>`` so the
# disclosure works without JavaScript.

def caveats_disclosure(
    caveats: list[str],
    *,
    label: str = "Modeling caveats",
    not_modeled: Optional[list[str]] = None,
) -> str:
    """Collapsed-by-default modeling-caveats disclosure.

    Empty input returns an empty string — analytical pages should
    only render the section when there's something to disclose.

    P75: ``not_modeled`` is an optional second list rendered as a
    "Not yet modeled" subsection. The opposite of black-box AI
    vibes — partners trust tools more when the tools are honest
    about their limits.
    """
    if not caveats and not not_modeled:
        return ""
    sections = []
    if caveats:
        items = "".join(
            f"<li>{_html.escape(str(c))}</li>" for c in caveats
        )
        sections.append(f'<ul>{items}</ul>')
    if not_modeled:
        nm_items = "".join(
            f"<li>{_html.escape(str(c))}</li>" for c in not_modeled
        )
        sections.append(
            '<h4 class="caveats-not-modeled-header">Not yet modeled</h4>'
            f'<ul class="caveats-not-modeled">{nm_items}</ul>'
        )
    return (
        '<details class="caveats-disclosure">'
        f'<summary>{_html.escape(label)}</summary>'
        f'{"".join(sections)}'
        '</details>'
    )


# ── action_button() ───────────────────────────────────────────────
#
# P20: three-tier action weight + cost/consequence signals. Cheap
# actions (filter), expensive actions (run Monte Carlo, ~10s) and
# consequential actions (advance stage, send LP update) all looked
# identical before this. ``action_button`` makes weight, expected
# duration, and consequence explicit.

_VALID_WEIGHTS = ("primary", "secondary", "tertiary")


def action_button(
    *,
    label: str,
    weight: str = "primary",
    expected_seconds: Optional[int] = None,
    consequential: bool = False,
    type: str = "submit",  # noqa: A002 — matches HTML attribute name
    name: Optional[str] = None,
    value: Optional[str] = None,
    href: Optional[str] = None,
) -> str:
    """Render a button whose visual weight matches its real cost.

    ``weight``: ``primary`` | ``secondary`` | ``tertiary`` — selects
      the CSS class so a tertiary "Browse library" doesn't compete
      visually with a primary "Run Monte Carlo".
    ``expected_seconds``: when set, appends a "~Ns" hint and wires a
      data-busy attribute the kit JS swaps on submit so the button
      can disable itself + show "Running…" without per-page wiring.
    ``consequential``: wraps the click in a native confirm() prompt.
      Reserved for actions that change shared state (advance stage,
      send LP update, archive a deal).
    ``href``: when supplied the button renders as an ``<a>`` link
      instead of a ``<button>``; mutually exclusive with ``name`` /
      ``value`` / form ``type``.
    """
    if weight not in _VALID_WEIGHTS:
        weight = "primary"
    classes = [f"btn-{weight}"]
    duration_hint = (
        f' <span class="btn-duration">· ~{int(expected_seconds)}s</span>'
        if expected_seconds else ""
    )
    busy_attr = (
        f' data-expected-seconds="{int(expected_seconds)}"'
        if expected_seconds else ""
    )
    confirm_attr = ""
    if consequential:
        confirm_attr = (
            ' onclick="return confirm(\'This action affects shared '
            'state. Proceed?\');"'
        )
        classes.append("btn-consequential")
    label_html = _html.escape(label) + duration_hint
    cls_attr = ' '.join(classes)
    if href is not None:
        return (
            f'<a class="{cls_attr}" href="{_html.escape(href)}"'
            f'{busy_attr}{confirm_attr}>{label_html}</a>'
        )
    name_attr = f' name="{_html.escape(name)}"' if name else ""
    value_attr = f' value="{_html.escape(value)}"' if value else ""
    return (
        f'<button class="{cls_attr}" type="{_html.escape(type)}"'
        f'{name_attr}{value_attr}{busy_attr}{confirm_attr}>'
        f'{label_html}</button>'
    )


# ── section_header() ──────────────────────────────────────────────
#
# P22: PE Intelligence's right-aligned serif-caps section divider
# ("SEVEN PARTNER REFLEXES", "BRAIN INVENTORIES", "PER-DEAL ROUTES")
# is the single strongest design move in the app. This helper
# promotes it from a one-page treatment to a kit primitive every
# Phase-3 page can reach for.

_VALID_SECTION_ALIGN = ("left", "center", "right")


# P44: canonical question subtitles for analytical pages. The
# partner-voice question framing ("What could break this thesis?",
# "When does your thesis hit a covenant cliff?") is the strongest
# copy in the app. This registry pins the canonical wording per
# route so a renaming sweep doesn't have to re-derive each.
_PAGE_QUESTIONS: dict[str, str] = {
    "/diligence/counterfactual":
        "What would change our mind?",
    "/diligence/payer-stress":
        "How fragile is your payer mix?",
    "/diligence/deal-mc":
        "What's the distribution of outcomes?",
    "/diligence/bear-case":
        "What could break this thesis?",
    "/diligence/regulatory-calendar":
        "Which thesis drivers die, and when?",
    "/diligence/bridge-audit":
        "Is the banker's bridge credible?",
    "/diligence/covenant-stress":
        "When does your thesis hit a covenant cliff?",
    "/diligence/exit-timing":
        "When and to whom should we exit?",
    "/screening/bankruptcy-survivor":
        "Does this match a known failure pattern?",
    "/diligence/comparable-outcomes":
        "What did similar deals actually return?",
}


def partner_question(route: str) -> Optional[str]:
    """Return the canonical partner-voice question subtitle for a
    route, or None if the route has no registered question. Pages
    feed the result straight into ``chartis_shell(subtitle=...)``."""
    return _PAGE_QUESTIONS.get(route)


def form_section(label: str, body_html: str) -> str:
    """P43: group inputs in big forms under an italic-serif subheader.

    Thesis Pipeline / Deal Monte Carlo / Bridge Audit / Covenant
    Stress all have 12-18 field walls of identical inputs. Grouping
    them under semantic subheaders (Identity / Capital / Real Estate
    / Investment, etc.) cuts time-to-comprehension dramatically.

    ``body_html`` is caller-supplied markup, typically a
    ``<div class="form-grid">…</div>`` of fields. Caller is
    responsible for HTML safety on body content.
    """
    return (
        '<section class="form-section">'
        f'<h3 class="form-section-label">{_html.escape(label)}</h3>'
        f'<div class="form-section-body">{body_html}</div>'
        '</section>'
    )


def section_header(label: str, *, align: str = "right") -> str:
    """Serif-caps divider with a 1px rule, right-aligned by default."""
    if align not in _VALID_SECTION_ALIGN:
        align = "right"
    return (
        f'<div class="section-header section-align-{align}">'
        f'<span class="section-header-label">{_html.escape(label)}</span>'
        '</div>'
    )


# ── diligence_phase_nav() ─────────────────────────────────────────
#
# P36: 16+ flat diligence tabs are unscannable. The Diligence front
# page already groups them into four partner-facing phases — Profile
# & Health, Thesis & Playbook, Audit & Stress, Exit & Synthesis.
# This helper carries that grouping into the secondary nav as a
# two-row strip: phase headers on top, active phase's children below.

DILIGENCE_PHASES: list[dict] = [
    {
        "key": "profile",
        "label": "Profile & Health",
        "children": [
            {"label": "Checklist",  "href": "/diligence/checklist"},
            {"label": "Ingestion",  "href": "/diligence/ingest"},
            {"label": "Benchmarks", "href": "/diligence/benchmarks"},
            {"label": "HCRIS X-Ray","href": "/diligence/hcris-xray"},
            {"label": "Provider economics", "href": "/diligence/physician-eu"},
        ],
    },
    {
        "key": "thesis",
        "label": "Thesis & Playbook",
        "children": [
            {"label": "Thesis pipeline", "href": "/diligence/thesis-pipeline"},
            {"label": "Root cause", "href": "/diligence/root-cause"},
            {"label": "Value creation", "href": "/diligence/value"},
            {"label": "Counterfactual", "href": "/diligence/counterfactual"},
        ],
    },
    {
        "key": "audit",
        "label": "Audit & Stress",
        "children": [
            {"label": "Risk Workbench",  "href": "/diligence/risk-workbench"},
            {"label": "Bridge Audit",    "href": "/diligence/bridge-audit"},
            {"label": "Payer Stress",    "href": "/diligence/payer-stress"},
            {"label": "Covenant Stress", "href": "/diligence/covenant-stress"},
            {"label": "Deal Monte Carlo","href": "/diligence/deal-mc"},
        ],
    },
    {
        "key": "exit",
        "label": "Exit & Synthesis",
        "children": [
            {"label": "Bear Case",      "href": "/diligence/bear-case"},
            {"label": "Exit Timing",    "href": "/diligence/exit-timing"},
            {"label": "Bankruptcy Scan",
             "href": "/screening/bankruptcy-survivor"},
            {"label": "QoE Memo",       "href": "/diligence/qoe-memo"},
            {"label": "IC Packet",      "href": "/diligence/ic-packet"},
        ],
    },
]


def _phase_for_path(active_path: str) -> Optional[dict]:
    """Look up which phase contains ``active_path``. Returns None if
    the path is not under any phase — caller can fall through to
    rendering all phases without highlighting."""
    for phase in DILIGENCE_PHASES:
        for child in phase["children"]:
            if child["href"] == active_path:
                return phase
    return None


# P39: workflow handoffs. Diligence today drops a partner back on
# the form they just submitted; there's no sense of forward motion.
# This ordered flow + the ``next_step_cta`` helper make the next
# action explicit on every result page.
_DILIGENCE_FLOW: list[dict] = [
    {"key": "ingest",       "label": "Ingestion",
     "href": "/diligence/ingest"},
    {"key": "benchmarks",   "label": "Benchmark KPIs",
     "href": "/diligence/benchmarks"},
    {"key": "root_cause",   "label": "Find root causes",
     "href": "/diligence/root-cause"},
    {"key": "value",        "label": "Build value-creation model",
     "href": "/diligence/value"},
    {"key": "risk",         "label": "Run risk workbench",
     "href": "/diligence/risk-workbench"},
    {"key": "bridge",       "label": "Audit the bridge",
     "href": "/diligence/bridge-audit"},
    {"key": "deal_mc",      "label": "Run Monte Carlo",
     "href": "/diligence/deal-mc"},
    {"key": "bear_case",    "label": "Generate bear case",
     "href": "/diligence/bear-case"},
    {"key": "exit_timing",  "label": "Plan exit timing",
     "href": "/diligence/exit-timing"},
    {"key": "ic_packet",    "label": "Assemble IC packet",
     "href": "/diligence/ic-packet"},
]


def next_step_cta(current_key: str, *, deal_id: Optional[str] = None) -> str:
    """Render the "Next: <module> →" CTA for an analytical result page.

    ``current_key`` matches the ``key`` field of an entry in
    ``_DILIGENCE_FLOW``. Returns the empty string when the current
    step is the last in the flow (or unrecognized) — pages can call
    this unconditionally without producing a stray CTA.
    """
    for i, step in enumerate(_DILIGENCE_FLOW):
        if step["key"] == current_key and i + 1 < len(_DILIGENCE_FLOW):
            nxt = _DILIGENCE_FLOW[i + 1]
            href = nxt["href"]
            if deal_id:
                href = f"{href}?deal_id={deal_id}"
            return action_button(
                label=f"Next: {nxt['label']} →",
                weight="primary",
                href=href,
            )
    return ""


# P57: the four flagship engines and their canonical surfaces. Each
# tile renders a partner-facing card linking to the engine's "hero"
# tab in the workbench. The marketing page can pull screenshots
# from these surfaces directly.
_FLAGSHIP_ENGINES: list[dict] = [
    {
        "key": "monte_carlo",
        "label": "Monte Carlo",
        "headline": "What's the distribution of outcomes?",
        "tab": "monte-carlo",
        "blurb": (
            "10,000-path simulation across denial, multiple, "
            "regulatory, and cyber drivers. Histogram + named "
            "scenario verticals + variance tornado."
        ),
    },
    {
        "key": "pe_math",
        "label": "PE-math",
        "headline": "How does the bridge break down?",
        "tab": "ebitda-bridge",
        "blurb": (
            "7-lever EBITDA bridge with per-lever attribution and "
            "covenant-headroom strip. Live re-render on slider drag."
        ),
    },
    {
        "key": "health",
        "label": "Health & completeness",
        "headline": "How complete is your diligence?",
        "tab": "health",
        "blurb": (
            "0-100 health gauge with per-component breakdown. "
            "P0 / P1 / P2 checklist coverage flags the gaps."
        ),
    },
    {
        "key": "memos",
        "label": "AI memos",
        "headline": "What does the IC memo say?",
        "tab": None,  # /diligence/qoe-memo?preview=1 in the spec
        "blurb": (
            "Auto-generated QoE + IC memo blocks with citation "
            "keys and per-theme narratives. Reproducible artefacts."
        ),
    },
]


def engine_flagship_card(key: str, *, deal_id: Optional[str] = None) -> str:
    """Render a one-engine flagship card. Matches the marketing
    bento-grid spec — large headline question + blurb + a link to
    the engine's hero tab."""
    engine = next((e for e in _FLAGSHIP_ENGINES if e["key"] == key), None)
    if engine is None:
        return ""
    tab = engine.get("tab")
    if deal_id and tab:
        href = f"/analysis/{_html.escape(deal_id)}?tab={tab}"
    elif deal_id:
        href = f"/analysis/{_html.escape(deal_id)}"
    elif key == "memos":
        href = "/diligence/qoe-memo?preview=1"
    else:
        # Without a deal context the card links to the methodology
        # docs for the engine — better than a dead "#" anchor.
        href = "/methodology"
    return (
        '<article class="engine-flagship">'
        f'<div class="engine-flagship-eyebrow">{_html.escape(engine["label"])}</div>'
        f'<h3 class="engine-flagship-headline">{_html.escape(engine["headline"])}</h3>'
        f'<p class="engine-flagship-blurb">{_html.escape(engine["blurb"])}</p>'
        f'<a class="engine-flagship-link" href="{href}">'
        'Open →</a>'
        '</article>'
    )


def metric_with_percentile(
    value: Any,
    *,
    kind: str,
    percentile: Optional[float],
    segment: str = "",
    n: Optional[int] = None,
) -> str:
    """P74: render a metric with its corpus-percentile context.

    Format::

        44.9% (P78 in sector "ASC, vintage 2020-2024, n=84")

    The caller computes the percentile against the relevant
    benchmark distribution; this helper just composes the visible
    string. ``percentile`` is a 0..100 number (P25, P50, P78 etc.).
    Missing percentile drops the context span entirely; missing
    value renders the unpopulated span (no context appended).
    """
    point = format_value(value, kind=kind)
    if _is_missing(value):
        return point
    if _is_missing(percentile):
        return point
    try:
        pct = int(round(float(percentile)))
    except (TypeError, ValueError):
        return point
    pct = max(1, min(99, pct))  # clamp into the meaningful range
    seg = (segment or "corpus").strip()
    n_str = f", n={int(n)}" if n is not None else ""
    return (
        f'{point} <span class="metric-percentile">'
        f'(P{pct} in {_html.escape(seg)}{_html.escape(n_str)})'
        '</span>'
    )


def metric_with_delta(
    value: Any,
    prior_value: Any,
    *,
    kind: str,
    period_label: str = "vs last snapshot",
    higher_is_better: bool = True,
) -> str:
    """P73: render a metric with its delta vs a prior snapshot.

    Format::

        2.80x ▲ +0.15x vs last week

    Tone follows ``higher_is_better`` — for MOIC/IRR/health-score
    higher is better; for denial-rate/days-in-AR lower is better.
    Caller flips the flag accordingly.

    When the prior value is missing, just the point renders. When
    the point is missing, the format_value missing span renders
    and the delta is dropped (a delta against nothing is nonsense).
    """
    point = format_value(value, kind=kind)
    if _is_missing(value) or _is_missing(prior_value):
        return point
    try:
        v = float(value)
        p = float(prior_value)
    except (TypeError, ValueError):
        return point
    diff = v - p
    if diff == 0:
        return point  # no delta to show
    is_improvement = (diff > 0) if higher_is_better else (diff < 0)
    tone = "positive" if is_improvement else "negative"
    arrow = "▲" if diff > 0 else "▼"
    sign = "+" if diff > 0 else ""
    if kind == "percent":
        delta_str = f"{sign}{diff*100:.1f}pp"
    elif kind == "money":
        # Re-use the money formatter for delta absolute scale.
        abs_str = format_value(abs(diff), kind="money")
        # format_value emits e.g. "$13.00M"; prepend sign.
        delta_str = (
            f"+{abs_str}" if diff > 0 else f"-{abs_str}"
        )
    elif kind == "multiple":
        delta_str = f"{sign}{diff:.2f}x"
    elif kind == "count":
        delta_str = f"{sign}{int(diff):,}"
    else:
        delta_str = f"{sign}{diff:.2f}"
    return (
        f'{point} <span class="metric-delta tone-{tone}">'
        f'{arrow} {delta_str}'
        f' <span class="metric-delta-period">{_html.escape(period_label)}</span>'
        '</span>'
    )


def inline_boxplot(
    *,
    p10: Optional[float],
    p25: Optional[float],
    p50: Optional[float],
    p75: Optional[float],
    p90: Optional[float],
    lo: Optional[float] = None,
    hi: Optional[float] = None,
    width: int = 50,
    height: int = 12,
) -> str:
    """P72: tiny inline boxplot for use inside a table cell.

    Renders a 50×12 SVG by default (small enough to share a row
    with text). The IQR is a filled rectangle from p25 to p75; the
    median is a thicker tick; whiskers extend to p10/p90.

    ``lo`` / ``hi`` set the x-axis bounds; if omitted, the helper
    derives them from min(p10) and max(p90) — but a caller passing
    column-wide bounds gets consistent scaling across rows.

    Returns "" when any of the five quantiles is missing.
    """
    quantiles = [p10, p25, p50, p75, p90]
    if any(_is_missing(q) for q in quantiles):
        return ""
    p10v, p25v, p50v, p75v, p90v = (float(q) for q in quantiles)
    if lo is None:
        lo = p10v
    if hi is None:
        hi = p90v
    if hi <= lo:
        # Degenerate — pad a small amount so the helper still renders.
        hi = lo + max(abs(lo), 1.0) * 0.01
    span = hi - lo

    def x(v: float) -> float:
        return (v - lo) / span * width

    pad = 1
    iqr_x = x(p25v) + pad
    iqr_w = max(1.0, x(p75v) - x(p25v))
    whisker_y = height / 2
    return (
        f'<svg class="inline-boxplot" '
        f'viewBox="0 0 {width + 2*pad} {height}" '
        f'width="{width + 2*pad}" height="{height}" '
        'aria-label="distribution boxplot">'
        # Whiskers
        f'<line x1="{x(p10v)+pad:.1f}" y1="{whisker_y}" '
        f'x2="{x(p90v)+pad:.1f}" y2="{whisker_y}" '
        'stroke="currentColor" stroke-width="1"/>'
        # IQR box
        f'<rect x="{iqr_x:.1f}" y="2" '
        f'width="{iqr_w:.1f}" height="{height-4}" '
        'fill="currentColor" fill-opacity="0.25" '
        'stroke="currentColor" stroke-width="1"/>'
        # Median tick
        f'<line x1="{x(p50v)+pad:.1f}" y1="1" '
        f'x2="{x(p50v)+pad:.1f}" y2="{height-1}" '
        'stroke="currentColor" stroke-width="1.5"/>'
        '</svg>'
    )


def calibration_badge(
    coverage: Optional[float],
    *,
    target: float = 0.90,
    n_samples: Optional[int] = None,
) -> str:
    """P71: render an empirical-coverage badge for predicted metrics.

    Format: ``Conformal coverage: 91% (target 90%) over 1,000
    held-out samples.``

    Tone:
      - positive when coverage ≥ target
      - warning when within 5pp of target
      - negative when more than 5pp below target
      - neutral / empty when ``coverage`` is missing
    """
    if _is_missing(coverage):
        return ""
    try:
        cov = float(coverage)
        tgt = float(target)
    except (TypeError, ValueError):
        return ""
    if cov >= tgt:
        tone = "positive"
    elif (tgt - cov) <= 0.05:
        tone = "warning"
    else:
        tone = "negative"
    n_str = ""
    if n_samples is not None:
        try:
            n_str = f" over {int(n_samples):,} held-out samples"
        except (TypeError, ValueError):
            pass
    return (
        f'<div class="calibration-badge tone-{tone}">'
        f'<span class="cb-label">Conformal coverage:</span> '
        f'<span class="cb-value">{cov*100:.1f}%</span>'
        f' <span class="cb-target">(target {tgt*100:.1f}%)</span>'
        f'<span class="cb-detail">{_html.escape(n_str)}</span>'
        '</div>'
    )


def variance_tornado(decomposition: dict) -> str:
    """P70: render a tornado chart of variance contributions.

    Input is a mapping ``{driver_name: contribution}`` where each
    contribution is in [0, 1] and sums to ≈ 1.0 (per the platform's
    Monte Carlo decomposition contract). Output is a horizontal-bar
    HTML block with drivers sorted descending by contribution.

    The bar widths are scaled relative to the largest contribution
    (so the leading driver fills the track) — visual readability
    beats absolute-percent encoding which would max out at ~40%
    for any single driver.
    """
    if not decomposition:
        return ""
    items = [
        (str(name), float(contrib))
        for name, contrib in decomposition.items()
        if contrib is not None
    ]
    if not items:
        return ""
    items.sort(key=lambda kv: kv[1], reverse=True)
    peak = max(c for _, c in items) or 1.0
    rows = []
    for name, contrib in items:
        pct = contrib * 100.0
        bar_w = max(2, int(contrib / peak * 100))
        rows.append(
            '<div class="vt-row">'
            f'<span class="vt-label">{_html.escape(name)}</span>'
            '<span class="vt-track">'
            f'<span class="vt-bar" style="width:{bar_w}%;"></span>'
            '</span>'
            f'<span class="vt-pct">{pct:.1f}%</span>'
            '</div>'
        )
    return (
        '<section class="variance-tornado" '
        'aria-label="Variance decomposition">'
        '<h3 class="vt-header">Where does outcome variance come from?</h3>'
        f'{"".join(rows)}'
        '</section>'
    )


def diligence_complete_banner(
    *,
    p0_coverage: float,
    health_score: float,
    n_critical: int,
    bridge_variance: float,
) -> str:
    """P69: surface "diligence is complete enough" once the
    composite criteria are met.

    The partner-grade move: most tools incentivise more usage; the
    tool that incentivises *correct* usage tells the partner when
    to stop. Conditions:

      - P0 checklist coverage = 100% (i.e. >= 1.0)
      - Health Score >= 90
      - Risk Workbench has zero CRITICAL panels
      - Bridge Audit variance < 10%

    Returns the banner HTML if all four hold; empty string otherwise
    so the caller can include it unconditionally.
    """
    try:
        coverage_ok = float(p0_coverage) >= 1.0
        health_ok = float(health_score) >= 90.0
        critical_ok = int(n_critical) == 0
        variance_ok = float(bridge_variance) < 0.10
    except (TypeError, ValueError):
        return ""
    if not (coverage_ok and health_ok and critical_ok and variance_ok):
        return ""
    return (
        '<aside class="diligence-complete-banner" role="note">'
        '<span class="dcb-eyebrow">DILIGENCE STATUS</span>'
        '<strong class="dcb-headline">Diligence is complete enough.</strong>'
        '<span class="dcb-detail">'
        'Further analysis is unlikely to change the verdict. '
        'Schedule IC.'
        '</span>'
        '</aside>'
    )


def model_verdict(panels: list[dict]) -> dict:
    """P68: derive a one-line model verdict from a list of panel
    dicts. Each panel must carry a ``severity`` ∈ {CRITICAL, RED,
    YELLOW, GREEN}; case-insensitive. Returns a dict with
    ``verdict`` (the badge label), ``tone`` (positive / warning /
    negative / critical), ``summary`` (one-line composition).
    """
    if not panels:
        return {
            "verdict": "AWAITING DILIGENCE",
            "tone": "neutral",
            "summary": "No panels evaluated yet.",
        }
    counts = {"CRITICAL": 0, "RED": 0, "YELLOW": 0, "GREEN": 0}
    for p in panels:
        sev = (p.get("severity") or "").strip().upper()
        if sev in counts:
            counts[sev] += 1
    n_crit = counts["CRITICAL"]
    n_red = counts["RED"]
    n_yellow = counts["YELLOW"]
    n_green = counts["GREEN"]
    if n_crit:
        verdict = "NEEDS PARTNER REVIEW"
        tone = "critical"
    elif n_red:
        verdict = "STRUCTURAL CONCERN — RECOMMEND REPRICING"
        tone = "negative"
    elif n_yellow:
        verdict = "DILIGENCE ACCEPTABLE"
        tone = "warning"
    elif n_green:
        verdict = "DILIGENCE CLEAN"
        tone = "positive"
    else:
        # Panels supplied but none had a recognised severity.
        verdict = "AWAITING DILIGENCE"
        tone = "neutral"
    pieces = []
    if n_crit:
        pieces.append(f"{n_crit} CRITICAL")
    if n_red:
        pieces.append(f"{n_red} RED")
    if n_yellow:
        pieces.append(f"{n_yellow} YELLOW")
    if n_green:
        pieces.append(f"{n_green} GREEN")
    summary = "; ".join(p + " panel" + ("s" if int(p[0]) != 1 else "")
                        for p in pieces) + "."
    return {
        "verdict": verdict, "tone": tone, "summary": summary,
        "counts": counts,
    }


def model_verdict_header(panels: list[dict]) -> str:
    """Render the banner version of ``model_verdict``. Drop on top
    of Risk Workbench so partners clock the verdict tone before
    reading the panels."""
    v = model_verdict(panels)
    return (
        f'<aside class="model-verdict tone-{v["tone"]}" '
        'role="note">'
        '<span class="model-verdict-eyebrow">Model verdict</span>'
        f'<span class="model-verdict-label">{_html.escape(v["verdict"])}</span>'
        f'<span class="model-verdict-summary">{_html.escape(v["summary"])}</span>'
        '</aside>'
    )


def metric_with_dollars(
    value: Any,
    *,
    kind: str,
    dollars_amount: Optional[Any] = None,
    dollars_label: str = "",
) -> str:
    """P65: render a metric followed by its dollar-anchored
    translation in muted text.

    Example::

        metric_with_dollars(0.449, kind="percent",
                            dollars_amount=156_000_000,
                            dollars_label="EBITDA contribution")
        → "44.9% <span class='dollar-context'>($156.00M EBITDA contribution)</span>"

    The dollar translation is the caller's responsibility (the kit
    can't know that 0.449 margin × $347M revenue = $156M EBITDA).
    Caller passes the already-computed dollars and the label that
    explains what the dollars mean.
    """
    point = format_value(value, kind=kind)
    if _is_missing(dollars_amount) or _is_missing(value):
        return point
    dollars_str = format_value(dollars_amount, kind="money")
    label = (
        f" {_html.escape(dollars_label)}" if dollars_label else ""
    )
    return (
        f'{point} <span class="dollar-context">'
        f'({dollars_str}{label})'
        '</span>'
    )


def coverage_line(
    matched: int,
    total: int,
    *,
    filter_desc: str = "",
    missing_realized: int = 0,
    catalog_href: str = "/data/catalog",
) -> str:
    """P64: render the per-filter coverage disclosure below a list.

    Format::

        3 deals matched (corpus has 18 deals matching "<filter_desc>";
        15 missing realized data — see Data Catalog for completeness map).

    The phrase "missing realized data" only renders when
    ``missing_realized > 0``. When ``total <= matched`` (full
    coverage) the phrase collapses to a positive note.
    """
    matched = max(0, int(matched))
    total = max(matched, int(total))
    parts = [f"<strong>{matched}</strong> deals matched"]
    if filter_desc:
        parts.append(
            f' (corpus has {total} deals matching '
            f'<em>{_html.escape(filter_desc)}</em>'
        )
    elif total > matched:
        parts.append(f" (corpus has {total} deals total")
    if missing_realized > 0:
        parts.append(
            f"; {int(missing_realized)} missing realized data — "
            f'see <a href="{_html.escape(catalog_href)}">Data Catalog'
            "</a> for completeness map"
        )
    if filter_desc or total > matched:
        parts.append(")")
    parts.append(".")
    return (
        '<p class="coverage-line muted">'
        + "".join(parts)
        + '</p>'
    )


def platform_health_footer(metrics: Optional[dict] = None) -> str:
    """P62: thin footer rail visible on every page surfacing the
    platform's engineering depth — version, test count, data
    freshness, cache hit rate, model calibration coverage.

    ``metrics`` is a dict with optional keys:
      - ``version``           ("1.0")
      - ``tests_passing``     (int — e.g. 2878)
      - ``hcris_refreshed``   (ISO ts)
      - ``packet_cache_hit``  (0..1 fraction)
      - ``mc_coverage``       (0..1 fraction)

    Each item only renders when its key is supplied. The whole
    footer collapses to nothing when ``metrics`` is None or empty —
    so pages can include it unconditionally.
    """
    metrics = metrics or {}
    if not metrics:
        return ""
    parts = []
    if "version" in metrics:
        parts.append(
            '<span class="ph-item">'
            f'Platform v{_html.escape(str(metrics["version"]))}</span>'
        )
    if "tests_passing" in metrics:
        n = metrics["tests_passing"]
        try:
            n_str = f"{int(n):,}"
        except (TypeError, ValueError):
            n_str = str(n)
        parts.append(
            f'<span class="ph-item">{n_str} tests passing</span>'
        )
    if "hcris_refreshed" in metrics:
        ts = metrics["hcris_refreshed"]
        rel = _relative_time(str(ts))
        parts.append(
            f'<span class="ph-item">HCRIS refreshed '
            f'<span title="{_html.escape(str(ts))}">{_html.escape(rel)}</span>'
            '</span>'
        )
    if "packet_cache_hit" in metrics:
        try:
            v = float(metrics["packet_cache_hit"])
            parts.append(
                f'<span class="ph-item">packet cache {v*100:.1f}% hit</span>'
            )
        except (TypeError, ValueError):
            pass
    if "mc_coverage" in metrics:
        try:
            v = float(metrics["mc_coverage"])
            parts.append(
                f'<span class="ph-item">MC calibration coverage '
                f'{v*100:.1f}%</span>'
            )
        except (TypeError, ValueError):
            pass
    if not parts:
        return ""
    return (
        '<footer class="platform-health-footer" '
        'aria-label="Platform health">'
        f'{" · ".join(parts)}'
        '</footer>'
    )


def packet_footer(
    packet_meta: Optional[dict],
    *,
    rebuild_href: Optional[str] = None,
    download_href: Optional[str] = None,
) -> str:
    """P61: per-page packet metadata footer.

    ``packet_meta`` is a dict-like with at least ``id``,
    ``inputs_hash``, ``last_rebuilt_at``. When ``packet_meta`` is
    None (e.g. the page has no packet because the deal context is
    missing), return the empty string — every analytical page can
    call this unconditionally without producing a stray footer.

    Optional ``rebuild_href`` and ``download_href`` wire the two
    action buttons in the footer. The download link points at the
    packet JSON; the rebuild action is a POST that triggers a
    fresh packet build server-side.
    """
    if not packet_meta:
        return ""
    pid = _html.escape(str(packet_meta.get("id") or "—"))
    inputs_hash = packet_meta.get("inputs_hash") or ""
    if inputs_hash:
        # Show first 8 hex chars + "…" for compactness; full hash is
        # available in the title for copy-paste.
        short = inputs_hash[:12]
        hash_html = (
            f'<span class="packet-hash" title="{_html.escape(inputs_hash)}">'
            f'sha256:{_html.escape(short)}…</span>'
        )
    else:
        hash_html = '<span class="packet-hash muted">no hash</span>'
    last_rebuilt = packet_meta.get("last_rebuilt_at") or ""
    rebuilt_html = (
        f'<span class="packet-rebuilt" title="{_html.escape(last_rebuilt)}">'
        f'{_html.escape(_relative_time(last_rebuilt))}</span>'
        if last_rebuilt else
        '<span class="packet-rebuilt muted">never</span>'
    )
    rebuild_btn = ""
    if rebuild_href:
        rebuild_btn = (
            f'<form class="packet-action" method="POST" '
            f'action="{_html.escape(rebuild_href)}">'
            '<button class="btn-tertiary" type="submit">'
            'Force rebuild</button></form>'
        )
    download_btn = ""
    if download_href:
        download_btn = (
            f'<a class="btn-tertiary packet-download" '
            f'href="{_html.escape(download_href)}">'
            'Download packet JSON</a>'
        )
    return (
        '<footer class="packet-footer">'
        f'<span>Rendered from packet <code>{pid}</code></span>'
        f'<span>· inputs hash {hash_html}</span>'
        f'<span>· last rebuilt {rebuilt_html}</span>'
        f'{rebuild_btn}{download_btn}'
        '</footer>'
    )


def entity_activity_rail(
    db_path: str,
    *,
    entity_id: str,
    limit: int = 10,
) -> str:
    """P60: per-entity activity stream rendered diegetically inside
    the entity's page (deal, diligence module, portfolio).

    Reads from ``audit_events`` filtered by ``target = entity_id``.
    Falls back to a muted "no activity yet" message when the table
    is missing or empty so a fresh-DB demo still renders cleanly.
    """
    import sqlite3
    rows: list[dict] = []
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        try:
            cur = con.execute(
                "SELECT at, actor, action, target FROM audit_events "
                "WHERE target = ? ORDER BY at DESC LIMIT ?",
                (entity_id, int(limit)),
            )
            rows = [dict(r) for r in cur.fetchall()]
        finally:
            con.close()
    except sqlite3.OperationalError:
        rows = []

    if not rows:
        empty = (
            '<div class="activity-rail-empty muted">'
            'No recent activity on this entity.'
            '</div>'
        )
        return (
            '<section class="activity-rail">'
            '<h3 class="activity-rail-header">Activity</h3>'
            f'{empty}'
            '</section>'
        )

    items = []
    for r in rows:
        at = _html.escape(str(r["at"]))
        actor = _html.escape(str(r["actor"]))
        action = _html.escape(str(r["action"]))
        items.append(
            f'<li><span class="activity-ts">{_relative_time(r["at"])}</span>'
            f' · <span class="activity-actor">{actor}</span>'
            f' <span class="activity-action">{action}</span>'
            f'<span class="activity-ts-full" title="{at}"></span></li>'
        )
    full_link = (
        f'<a class="activity-rail-more" '
        f'href="/audit?target={_html.escape(entity_id)}">'
        'View full audit →</a>'
    )
    return (
        '<section class="activity-rail">'
        '<h3 class="activity-rail-header">Activity</h3>'
        f'<ul class="activity-rail-list">{"".join(items)}</ul>'
        f'{full_link}'
        '</section>'
    )


def share_button(
    *,
    entity_type: str,
    entity_id: str,
    share_url: str,
) -> str:
    """P59: per-page Share button. Opens a native browser dialog
    that copies the URL to clipboard and surfaces a small @-mention
    affordance. The persistent storage lives in
    ``rcm_mc.portfolio.team_mentions`` — this helper only renders
    the trigger button + the modal markup; the JS handler is in
    the v2 kit's _SHARE_BUTTON_JS bundle.
    """
    return (
        '<div class="share-button-wrap">'
        '<button class="share-button btn-tertiary" type="button" '
        f'data-share-url="{_html.escape(share_url)}" '
        f'data-share-entity-type="{_html.escape(entity_type)}" '
        f'data-share-entity-id="{_html.escape(entity_id)}">'
        '↗ Share</button>'
        '</div>'
    )


def _relative_time(iso_ts: str) -> str:
    """Render an ISO timestamp as a relative phrase ("14m ago",
    "2d ago"). Falls back to the raw timestamp if it can't parse."""
    if not iso_ts:
        return ""
    try:
        from datetime import datetime, timezone
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - ts
        secs = int(delta.total_seconds())
    except (ValueError, TypeError):
        return iso_ts
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    days = secs // 86400
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def freshness_rail(
    *,
    packet_generated_at: Optional[str] = None,
    hcris_as_of: Optional[str] = None,
    last_rebuilt_at: Optional[str] = None,
    rebuild_href: Optional[str] = None,
) -> str:
    """P58: per-page freshness rail. Rendered in the page header on
    analytical pages so partners can clock how stale the data is
    before reading the numbers.

    Any field that's None is omitted; the rail only shows what's
    available. ``rebuild_href`` makes the rebuild button render —
    when omitted the rail is read-only.
    """
    parts = []
    if packet_generated_at:
        parts.append(
            '<span class="freshness-item">'
            '<span class="freshness-label">Packet:</span> '
            f'<span class="freshness-value" title="{_html.escape(packet_generated_at)}">'
            f'{_html.escape(_relative_time(packet_generated_at))}</span>'
            '</span>'
        )
    if hcris_as_of:
        parts.append(
            '<span class="freshness-item">'
            '<span class="freshness-label">HCRIS:</span> '
            f'<span class="freshness-value">{_html.escape(hcris_as_of)}</span>'
            '</span>'
        )
    if last_rebuilt_at:
        parts.append(
            '<span class="freshness-item">'
            '<span class="freshness-label">Rebuilt:</span> '
            f'<span class="freshness-value" title="{_html.escape(last_rebuilt_at)}">'
            f'{_html.escape(_relative_time(last_rebuilt_at))}</span>'
            '</span>'
        )
    if rebuild_href:
        parts.append(
            '<form class="freshness-rebuild" method="POST" '
            f'action="{_html.escape(rebuild_href)}">'
            '<button class="btn-tertiary" type="submit">Rebuild</button>'
            '</form>'
        )
    if not parts:
        return ""
    return f'<div class="freshness-rail">{"".join(parts)}</div>'


# P79: workbench tabs that map to a live module page. The
# workbench shows the cached/computed result; the module page lets
# a partner re-run with new inputs. The link closes the loop.
_WORKBENCH_TAB_TO_MODULE: dict[str, str] = {
    "overview":      "",  # no live module — overview is a summary
    "rcm-profile":   "/diligence/benchmarks",
    "ebitda-bridge": "/diligence/bridge-audit",
    "monte-carlo":   "/diligence/deal-mc",
    "risk":          "/diligence/risk-workbench",
    "health":        "/diligence/checklist",
    "bear-case":     "/diligence/bear-case",
    "covenant":      "/diligence/covenant-stress",
    "payer":         "/diligence/payer-stress",
    "exit":          "/diligence/exit-timing",
}


def run_live_link(tab_key: str, deal_id: str) -> str:
    """Render the "▶ Run live in module →" deep-link rendered in
    each workbench tab. Returns "" when the tab has no live-module
    counterpart (e.g. the synthesis Overview)."""
    if not deal_id or not tab_key:
        return ""
    target = _WORKBENCH_TAB_TO_MODULE.get(tab_key)
    if not target:
        return ""
    href = f"{target}?deal_id={_html.escape(deal_id)}"
    return (
        f'<a class="run-live-link btn-tertiary" href="{href}">'
        '▶ Run live in module →</a>'
    )


# P88: action-anticipation registry. Maps a "just completed"
# module key to a contextual nudge — partner-grade "you might
# want to do X next" without using an LLM.
_NEXT_ACTION_NUDGES: dict[str, dict] = {
    "ingest": {
        "headline": "Run Benchmarks now?",
        "href": "/diligence/benchmarks",
    },
    "bridge_audit": {
        "headline": "Compare to corpus median for this sector?",
        "href": "/diligence/comparable-outcomes",
    },
    "deal_mc": {
        "headline": "Generate the bear case?",
        "href": "/diligence/bear-case",
    },
    "risk_workbench": {
        "headline": "Audit the bridge before IC?",
        "href": "/diligence/bridge-audit",
    },
    "bear_case": {
        "headline": "Assemble the IC packet?",
        "href": "/diligence/ic-packet",
    },
}


_SEVERITY_GLYPHS: dict[str, tuple[str, str, str]] = {
    # severity → (glyph, accessible_label, css_class)
    "safe":      ("●", "safe (filled circle)", "tone-positive"),
    "fresh":     ("●", "fresh (filled circle)", "tone-positive"),
    "excellent": ("●", "excellent (filled circle)", "tone-positive"),
    "green":     ("●", "green (filled circle)", "tone-positive"),
    "tight":     ("◐", "tight (half circle)", "tone-warning"),
    "amber":     ("◐", "amber (half circle)", "tone-warning"),
    "stale":     ("◐", "stale (half circle)", "tone-warning"),
    "yellow":    ("◐", "yellow (half circle)", "tone-warning"),
    "warning":   ("◐", "warning (half circle)", "tone-warning"),
    "hot":       ("▲", "hot (triangle)", "tone-negative"),
    "tripped":   ("▲", "tripped (triangle)", "tone-negative"),
    "red":       ("▲", "red (triangle)", "tone-negative"),
    "critical":  ("▲", "critical (triangle)", "tone-negative"),
    "negative":  ("▲", "negative (triangle)", "tone-negative"),
    "cold":      ("○", "cold (open circle)", "tone-muted"),
    "poor":      ("○", "poor (open circle)", "tone-muted"),
    "no_data":   ("—", "no data (em dash)", "tone-muted"),
    "zero":      ("—", "zero (em dash)", "tone-muted"),
    "overdue":   ("▲", "overdue (triangle)", "tone-negative"),
}


def severity_glyph(severity: str) -> str:
    """P98: render a per-severity glyph alongside the colored badge.

    Print stylesheet (P25) ships pattern fallbacks; the screen view
    benefits from the glyph too — color-blind partners and B&W
    screenshots both stay readable.

    Returns an inline span with the glyph + accessible label.
    Unknown severities fall through to a small middle-dot so a typo
    can't crash a page render.
    """
    spec = _SEVERITY_GLYPHS.get(severity.lower().strip(),
                                ("·", "unknown", "tone-muted"))
    glyph, aria, cls = spec
    return (
        f'<span class="severity-glyph {cls}" '
        f'aria-label="{_html.escape(aria)}" title="{_html.escape(aria)}">'
        f'{glyph}</span>'
    )


def labelled_input(
    name: str,
    *,
    label: str,
    type: str = "text",  # noqa: A002 — matches HTML attribute
    value: Optional[Any] = None,
    placeholder: Optional[str] = None,
    required: bool = False,
    extra_attrs: Optional[dict] = None,
) -> str:
    """P97: every form input gets a real, persistent ``<label>``.

    Placeholders disappear on focus; for partner-grade forms a
    label above the input is non-negotiable. When a ``placeholder``
    is supplied this helper prefixes it with ``e.g., `` so it
    obviously reads as an example rather than instructive text.
    """
    safe_name = _html.escape(name)
    safe_label = _html.escape(label)
    val_attr = ""
    if value is not None and value != "":
        val_attr = f' value="{_html.escape(str(value))}"'
    placeholder_attr = ""
    if placeholder:
        prefixed = (
            placeholder if placeholder.lower().startswith("e.g.")
            else f"e.g., {placeholder}"
        )
        placeholder_attr = f' placeholder="{_html.escape(prefixed)}"'
    required_attr = " required" if required else ""
    extra = ""
    if extra_attrs:
        for k, v in extra_attrs.items():
            extra += f' {_html.escape(k)}="{_html.escape(str(v))}"'
    return (
        '<div class="labelled-input">'
        f'<label for="li-{safe_name}">{safe_label}</label>'
        f'<input id="li-{safe_name}" name="{safe_name}" '
        f'type="{_html.escape(type)}"'
        f'{val_attr}{placeholder_attr}{required_attr}{extra}>'
        '</div>'
    )


def is_demo_mode(
    *,
    username: Optional[str] = None,
    query: Optional[dict] = None,
) -> bool:
    """P91: detect whether to render the demo-mode chrome.

    Two triggers:
      - the logged-in user's username is ``"demo"``
      - the query string carries ``?demo=1``
    """
    if username and username.lower() == "demo":
        return True
    if query:
        v = query.get("demo")
        if v in ("1", "true", True):
            return True
        if isinstance(v, list) and v and v[0] in ("1", "true"):
            return True
    return False


def demo_mode_banner(*, reset_href: Optional[str] = None) -> str:
    """Persistent "DEMO DATA" banner. Caller renders only when
    ``is_demo_mode`` returns True. ``reset_href`` wires the
    "Reset demo data" CTA — when omitted the banner is read-only."""
    reset_btn = ""
    if reset_href:
        reset_btn = (
            f'<form class="demo-reset" method="POST" '
            f'action="{_html.escape(reset_href)}">'
            '<button type="submit" '
            'onclick="return confirm(\'Reset all demo data?\');">'
            'Reset demo data</button></form>'
        )
    return (
        '<div class="demo-mode-banner" role="note">'
        '<span class="demo-mode-eyebrow">Demo data</span>'
        '<span class="demo-mode-detail">'
        'Numbers below are illustrative. Deal names are fictional.'
        '</span>'
        f'{reset_btn}'
        '</div>'
    )


def next_action_nudge(
    *,
    completed_module: str,
    deal_id: str = "",
) -> str:
    """P88: render a contextual "you might want to do X next" nudge
    after completing a diligence module. Returns the empty string
    when ``completed_module`` is unrecognised so caller can include
    unconditionally."""
    spec = _NEXT_ACTION_NUDGES.get(completed_module)
    if not spec:
        return ""
    href = spec["href"]
    if deal_id:
        href = f"{href}?deal_id={_html.escape(deal_id)}"
    return (
        '<aside class="next-action-nudge" role="note">'
        '<span class="nan-eyebrow">Next:</span>'
        f'<a class="nan-link" href="{href}">'
        f'{_html.escape(spec["headline"])} →</a>'
        '</aside>'
    )


def validate_numeric(
    value: Any,
    *,
    plausible_min: float,
    plausible_max: float,
    hard_min: Optional[float] = None,
    hard_max: Optional[float] = None,
    field_label: str = "Value",
) -> dict:
    """P87: classify a numeric input as ``ok`` / ``warning`` / ``error``.

    ``hard_min`` / ``hard_max`` are the impossible-value bounds (e.g.
    revenue can't be negative). Returns ``{"level", "message"}``.
    """
    if value is None or value == "":
        return {"level": "ok", "message": ""}
    try:
        v = float(value)
    except (TypeError, ValueError):
        return {
            "level": "error",
            "message": f"{field_label} is not a number.",
        }
    if hard_min is not None and v < hard_min:
        return {
            "level": "error",
            "message": (
                f"{field_label} = {v:g} is below the impossible-value "
                f"bound ({hard_min:g})."
            ),
        }
    if hard_max is not None and v > hard_max:
        return {
            "level": "error",
            "message": (
                f"{field_label} = {v:g} is above the impossible-value "
                f"bound ({hard_max:g})."
            ),
        }
    if v < plausible_min or v > plausible_max:
        return {
            "level": "warning",
            "message": (
                f"{field_label} = {v:g} is outside the typical range "
                f"({plausible_min:g}–{plausible_max:g})."
            ),
        }
    return {"level": "ok", "message": ""}


def inline_validation_pill(status: dict) -> str:
    """Render a small pill that surfaces the validation level."""
    level = status.get("level") or "ok"
    msg = status.get("message") or ""
    if level == "ok" or not msg:
        return ""
    return (
        f'<span class="validation-pill tone-'
        f'{"negative" if level == "error" else "warning"}" '
        'role="status">'
        f'{_html.escape(msg)}'
        '</span>'
    )


_SECTOR_DEFAULTS: dict[tuple[str, str], Any] = {
    # (sector_lowercase, field_name) → typical default. Values are
    # rough sector medians sourced from the platform's corpus
    # benchmarks; callers should override with deal-specific
    # corpus_median when available.
    ("asc",  "ebitda_margin"):    0.32,
    ("asc",  "growth_rate"):      0.05,
    ("asc",  "exit_multiple"):    11.0,
    ("hospital", "ebitda_margin"): 0.08,
    ("hospital", "growth_rate"):   0.03,
    ("hospital", "exit_multiple"): 8.5,
    ("behavioral_health", "ebitda_margin"): 0.18,
    ("behavioral_health", "growth_rate"):   0.07,
    ("behavioral_health", "exit_multiple"): 9.0,
}


def smart_default(
    field: str,
    *,
    sector: Optional[str] = None,
    last_submission: Any = None,
    corpus_median: Any = None,
    fallback: Any = None,
) -> Any:
    """P86: pick the highest-confidence default for a form field.

    Order:
      1. ``last_submission`` (the user's previous value for this
         field on this form — partner-specific muscle memory)
      2. ``corpus_median`` (the deal's segment median if available)
      3. sector typical value from the registry
      4. ``fallback`` (caller-supplied last resort)

    Returns ``None`` when every source is None — caller renders the
    field empty.
    """
    if last_submission is not None:
        return last_submission
    if corpus_median is not None:
        return corpus_median
    if sector:
        sec_key = sector.strip().lower().replace(" ", "_").replace("-", "_")
        v = _SECTOR_DEFAULTS.get((sec_key, field))
        if v is not None:
            return v
    return fallback


def percent_slider(
    name: str,
    *,
    label: str,
    default: float = 0.0,
    min_value: float = 0.0,
    max_value: float = 1.0,
    step: float = 0.01,
    distribution: Optional[list[int]] = None,
) -> str:
    """P84: percentage slider with optional distribution preview.

    ``name``: form field name. ``default`` / ``min_value`` /
    ``max_value`` / ``step`` are the value bounds (caller passes
    0..1 fractions). ``distribution`` is an optional list of bucket
    counts (e.g. 20-bucket histogram of corpus values) — when
    provided, a tiny preview chart renders below the slider
    showing where the current value sits.
    """
    safe_name = _html.escape(name)
    safe_label = _html.escape(label)
    preview = ""
    if distribution:
        peak = max(distribution) if distribution else 0
        if peak == 0:
            peak = 1
        gap = 4
        bars = []
        for i, n in enumerate(distribution):
            h_pct = max(2, int(n / peak * 100))
            bars.append(
                f'<g transform="translate({i * gap},0)">'
                f'<rect width="3" height="{h_pct}%" '
                'fill="currentColor" fill-opacity="0.45"/>'
                '</g>'
            )
        svg_w = max(60, len(distribution) * gap)
        preview = (
            f'<svg class="ps-distribution" '
            f'viewBox="0 0 {svg_w} 24" '
            f'width="{svg_w}" height="24" '
            'preserveAspectRatio="none" aria-hidden="true">'
            f'{"".join(bars)}'
            '</svg>'
        )
    return (
        '<div class="percent-slider">'
        f'<label class="ps-label" for="ps-{safe_name}">{safe_label}</label>'
        '<div class="ps-row">'
        f'<input type="range" id="ps-{safe_name}" name="{safe_name}" '
        f'min="{min_value}" max="{max_value}" step="{step}" '
        f'value="{default}" class="ps-input" '
        'oninput="this.nextElementSibling.value='
        "(parseFloat(this.value)*100).toFixed(1) + '%'\">"
        f'<output class="ps-output">{default*100:.1f}%</output>'
        '</div>'
        f'{preview}'
        '</div>'
    )


def workbench_tab_layout(
    tab_key: str,
    *,
    kpis: Optional[list[dict]] = None,
    content_sections: Optional[list[str]] = None,
    recommendation: Optional[str] = None,
    deal_id: str = "",
) -> str:
    """P80-83 composer for the canonical workbench-tab layout.

    A workbench tab follows the same shape regardless of which one
    the partner is on:

      1. KPI strip (top — answers "what's the headline number")
      2. Run-live link (top right — closes the loop to the module)
      3. Content sections (caller-provided HTML — chart, table,
         narrative paragraphs)
      4. Recommendation block (bottom — partner-grade conclusion)

    The full ``analysis_workbench.py`` is a 930-line surface; this
    composer is the reusable shape pages can adopt incrementally.
    """
    parts = []
    parts.append(
        f'<div class="workbench-tab" data-tab="{_html.escape(tab_key)}">'
    )
    if kpis:
        parts.append('<div class="workbench-tab-header">')
        parts.append(kpi_strip(kpis))
        live = run_live_link(tab_key, deal_id)
        if live:
            parts.append(f'<div class="workbench-tab-live">{live}</div>')
        parts.append('</div>')
    if content_sections:
        for section in content_sections:
            parts.append(section)
    if recommendation:
        parts.append(recommendation)
    parts.append('</div>')
    return "".join(parts)


def back_to_workbench(deal_id: str) -> str:
    """P78: small "← Back to workbench" link for diligence-module
    page headers. Reverses the navigation: workbench is home,
    modules are deep dives.

    Empty deal_id returns "" so a module not in deal-context still
    renders cleanly without a dangling link.
    """
    if not deal_id:
        return ""
    href = f"/analysis/{_html.escape(deal_id)}"
    return (
        f'<a class="back-to-workbench btn-tertiary" href="{href}">'
        '← Back to workbench</a>'
    )


def tour_overlay(steps: list[dict]) -> str:
    """P77: N-step tour overlay for first-time visitors.

    Each ``step`` dict has:
      - ``selector`` (CSS selector for the tab/element to highlight)
      - ``title`` (short headline)
      - ``body`` (1-2 sentence description)

    The overlay renders steps sequentially; JS in the v2 kit
    handles next/prev/skip. The container is hidden by default;
    pages opt in by also rendering a ``data-tour="active"`` flag
    on <body> (typically when ``?tour=1`` is in the query).
    """
    if not steps:
        return ""
    items = []
    for i, step in enumerate(steps):
        sel = _html.escape(str(step.get("selector", "body")))
        title = _html.escape(str(step.get("title", "")))
        body = _html.escape(str(step.get("body", "")))
        items.append(
            f'<li class="tour-step" data-step="{i}" '
            f'data-target="{sel}" hidden>'
            f'<h4 class="tour-step-title">{title}</h4>'
            f'<p class="tour-step-body">{body}</p>'
            '</li>'
        )
    return (
        '<div class="tour-overlay" id="tour-overlay" hidden '
        f'data-step-count="{len(steps)}">'
        f'<ol class="tour-steps">{"".join(items)}</ol>'
        '<div class="tour-controls">'
        '<button type="button" class="tour-skip">Skip</button>'
        '<span class="tour-progress" aria-hidden="true"></span>'
        '<button type="button" class="tour-prev" disabled>Back</button>'
        '<button type="button" class="tour-next">Next</button>'
        '</div></div>'
    )


def deal_link(
    deal_id: str,
    *,
    tab: Optional[str] = None,
) -> str:
    """P76: canonical deal hyperlink. Every list-row click in
    Library / Pipeline / Watchlist / Risk Scan / Portfolio should
    use this helper so the click consistently lands on the analysis
    workbench instead of the legacy ``/deal/<id>`` page.

    Returns the URL string (no markup) — caller composes the <a>.
    Empty deal_id returns "#" so a misbuilt list still renders
    rather than producing an obviously-broken href.
    """
    if not deal_id:
        return "#"
    href = f"/analysis/{_html.escape(deal_id)}"
    if tab:
        href += f"?tab={_html.escape(tab)}"
    return href


def workbench_cta(
    deal_id: str,
    *,
    tab: Optional[str] = None,
    label: str = "Open analysis workbench →",
) -> str:
    """Render the primary CTA that promotes the analysis workbench.

    P56: the most-engineered page in the codebase
    (``/analysis/<deal_id>``) should be the central artifact of the
    platform. This helper composes a primary ``action_button`` with
    the workbench href so deal pages, story pages, and IC packets
    all surface the same call-to-action.

    ``tab`` optionally drives the workbench's deep-link query string
    (e.g. ``tab="ebitda-bridge"`` opens the EBITDA Bridge tab).
    """
    if not deal_id:
        return ""
    href = f"/analysis/{_html.escape(deal_id)}"
    if tab:
        href += f"?tab={_html.escape(tab)}"
    return action_button(
        label=label,
        weight="primary",
        href=href,
    )


def bulk_actions_bar(actions: list[dict]) -> str:
    """Sticky-bottom multi-select action bar.

    P49: ack 10 alerts at once, advance 5 deals at once. Caller
    renders `<input type="checkbox" class="bulk-select"
    data-bulk-id="<row id>">` cells per row; the kit JS counts
    checked boxes and reveals this bar when count > 0.

    ``actions`` is a list of dicts with keys ``label`` and
    ``href_template`` (defaults to ``#`` for client-side handlers)
    and optional ``confirm`` (when truthy, wraps the link in a
    native confirm() prompt).

    The bar is rendered hidden by default; the
    ``_BULK_ACTIONS_JS`` block in the v2 kit handles show/hide.
    """
    btns = []
    for a in actions:
        label = _html.escape(str(a.get("label", "Action")))
        href = _html.escape(str(a.get("href_template", "#")))
        confirm_attr = ""
        if a.get("confirm"):
            confirm_attr = (
                ' onclick="return confirm(\'Apply to selected rows?\');"'
            )
        btns.append(
            f'<a class="bulk-action-btn" '
            f'data-bulk-href-template="{href}"{confirm_attr}>'
            f'{label}</a>'
        )
    return (
        '<div class="bulk-actions-bar" id="bulk-actions-bar" hidden>'
        '<span class="bulk-count"><span class="bulk-count-n">0</span> '
        'selected</span>'
        '<div class="bulk-actions-buttons">'
        f'{"".join(btns)}'
        '</div>'
        '<button type="button" class="bulk-clear" '
        'aria-label="Clear selection">×</button>'
        '</div>'
    )


def deal_breadcrumbs(
    active_label: str,
    *,
    deal_id: Optional[str] = None,
    deal_name: Optional[str] = None,
    parent: Optional[tuple[str, str]] = None,
) -> list[dict]:
    """Build a breadcrumb list ready to pass to ``chartis_shell``.

    P38: ``HOME / DILIGENCE / CHECKLIST`` is fine for an unscoped
    page. When the user is in a deal context, the chain should read
    ``HOME / DEAL: PROJECT AURORA / DILIGENCE / CHECKLIST``. This
    helper inserts the deal segment when ``deal_id`` is supplied.

    ``parent`` is an optional ``(label, href)`` tuple for the parent
    section ("DILIGENCE", "/diligence"). ``active_label`` is the
    current page; rendered without an href so it reads as the leaf.
    """
    crumbs: list[dict] = [{"label": "HOME", "href": "/"}]
    if deal_id:
        name_seg = (deal_name or deal_id).upper()
        crumbs.append({
            "label": f"DEAL: {name_seg}",
            "href": f"/deal/{deal_id}",
        })
    if parent is not None:
        plabel, phref = parent
        crumbs.append({"label": plabel.upper(), "href": phref})
    crumbs.append({"label": active_label.upper()})  # no href = leaf
    return crumbs


def diligence_phase_nav(active_path: str = "") -> str:
    """Two-row diligence navigation.

    Row 1: four phase headers; the parent of ``active_path`` reads
      as active. Each phase header links to its first child so a
      partner can click into a phase blind.
    Row 2: child tabs of the active phase. When ``active_path`` is
      empty or unrecognised, the children of the first phase render
      so the page never has a blank secondary row.
    """
    active_phase = _phase_for_path(active_path) or DILIGENCE_PHASES[0]
    phase_links = []
    for phase in DILIGENCE_PHASES:
        is_active = phase["key"] == active_phase["key"]
        cls = "phase-link" + (" active" if is_active else "")
        # Each phase header links to its first child.
        first_child = phase["children"][0]["href"]
        phase_links.append(
            f'<a class="{cls}" href="{_html.escape(first_child)}" '
            f'data-phase="{phase["key"]}">'
            f'{_html.escape(phase["label"])}</a>'
        )
    child_links = []
    for child in active_phase["children"]:
        is_active = child["href"] == active_path
        cls = "child-link" + (" active" if is_active else "")
        child_links.append(
            f'<a class="{cls}" href="{_html.escape(child["href"])}">'
            f'{_html.escape(child["label"])}</a>'
        )
    return (
        '<nav class="diligence-phase-nav" aria-label="Diligence">'
        f'<div class="phase-row">{"".join(phase_links)}</div>'
        f'<div class="child-row">{"".join(child_links)}</div>'
        '</nav>'
    )
