"""Reasonableness guards for numeric UI rendering.

Every numeric output in the chartis UI passes through ``render_number``
before hitting the browser. If the value falls outside the partner-
plausible range for that metric, the renderer replaces the raw number
with a red warning pill so a partner sees immediately that something is
off — rather than silently trusting an implausible figure.

Range source of truth
---------------------
Where ``rcm_mc/pe_intelligence/reasonableness.py`` already defines a
band for a metric, we take the UNION of its ``implausible_low`` and
``implausible_high`` thresholds across all regimes / hospital types.
That gives the widest partner-plausible envelope — a point outside
that envelope would trigger IMPLAUSIBLE on at least one band in the
brain, so surfacing it as a UI warning is the right call.

For metrics reasonableness.py does NOT define, we cite a named
industry source (HFMA MAP, FTC merger guidelines, CMS cost reports,
etc.). Every range in the REGISTRY below has a ``source`` citation.

Rule: **never silently clip**. The raw value is always preserved in
the warning pill — the user needs to see what the platform
computed so they can investigate their inputs.
"""
from __future__ import annotations

import html as _html
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .._chartis_kit import P


UNIT_MONEY = "money"    # rendered as $X.XXm or $X.XXb
UNIT_PCT   = "pct"      # rendered as X.X% (input is a fraction 0-1)
UNIT_X     = "x"        # rendered as X.XXx (multiples — MOIC, leverage, EV/EBITDA)
UNIT_NUM   = "num"      # rendered as X,XXX.XX (raw numbers — HHI, counts)
UNIT_DAYS  = "days"     # rendered as X.X days


@dataclass(frozen=True)
class MetricRange:
    """Plausible envelope for a numeric metric.

    ``plausible_min`` / ``plausible_max`` define the partner-comfortable
    range. Values outside this range render as a warning pill.
    ``unit`` determines the number formatter; ``source`` is a citation
    for the range values; ``interpretation`` is a short one-liner on
    what "low" vs "high" means for this metric (optional but useful for
    explainer headers).
    """
    plausible_min: float
    plausible_max: float
    unit: str
    source: str
    interpretation: str = ""


# ── Registry ──────────────────────────────────────────────────────────
#
# Every range below cites either reasonableness.py (with module-file
# reference for traceability) or a named industry source. Ranges pulled
# from reasonableness.py are the UNION of implausible_low/high across
# all regime / hospital_type variants — i.e. the widest partner-
# plausible envelope the brain tolerates.
REGISTRY: Dict[str, MetricRange] = {
    # ── Returns (multiples / %) ─────────────────────────────────────
    "moic": MetricRange(
        plausible_min=0.3, plausible_max=6.0, unit=UNIT_X,
        source="Phase 4 spec (reasonableness.py has no MOIC band; "
               "0.3-6.0x matches Preqin / Pitchbook HC-PE exit distribution).",
        interpretation="Multiple on invested capital. Below 1.0x = loss; "
                       "1.5-3.0x = typical; above 3.0x = home run.",
    ),
    "irr": MetricRange(
        # Widest envelope from _IRR_BANDS in reasonableness.py:219 —
        # across (size, payer_regime), implausible_high tops at 0.55
        # (Commercial-Heavy Micro). implausible_low is 0.0 on most bands,
        # but deals can legitimately have negative IRR on losses, so we
        # widen the lower bound to -0.30 per Phase 4 spec.
        plausible_min=-0.30, plausible_max=0.55, unit=UNIT_PCT,
        source="reasonableness.py:219 _IRR_BANDS (widest union) + "
               "Phase 4 spec lower bound.",
        interpretation="Internal rate of return. Below 15% = weak; "
                       "20-30% = typical target; above 40% = extraordinary.",
    ),
    # ── Operating metrics (hospitals) ────────────────────────────────
    "ebitda_margin": MetricRange(
        # Widest envelope from _MARGIN_BANDS in reasonableness.py:439.
        # ASC implausible_high = 0.55; CAH implausible_low = -0.20.
        plausible_min=-0.20, plausible_max=0.55, unit=UNIT_PCT,
        source="reasonableness.py:439 _MARGIN_BANDS (widest union across "
               "hospital types: ASC ceiling, CAH floor).",
        interpretation="EBITDA as % of revenue. 4-12% = typical acute; "
                       "18-32% = ASC; negative = operating losses.",
    ),
    "exit_multiple": MetricRange(
        # Widest envelope from _MULTIPLE_CEILINGS in reasonableness.py:697
        # across payer regimes. Gov-heavy floor 4.5, commercial-heavy
        # implausible_high 16.5.
        plausible_min=4.5, plausible_max=16.5, unit=UNIT_X,
        source="reasonableness.py:697 _MULTIPLE_CEILINGS (widest union).",
        interpretation="EV/EBITDA at exit. 5-7x = Medicaid-heavy; "
                       "10-13x = commercial; above 13x = rich.",
    ),
    "entry_multiple": MetricRange(
        plausible_min=4.0, plausible_max=16.5, unit=UNIT_X,
        source="reasonableness.py:697 _MULTIPLE_CEILINGS widened by 0.5x "
               "to tolerate competitive entry multiples.",
        interpretation="EV/EBITDA at entry. Similar to exit band; if "
                       "entry > exit, underwriting expects multiple compression.",
    ),
    "ebitda_dollars_m": MetricRange(
        # EBITDA in $M per hospital. Realistic range from HCRIS:
        # small community $2M to mega-system $500M. Single-facility deals
        # ≥$1B EBITDA are implausible; use $2M-800M.
        plausible_min=2.0, plausible_max=800.0, unit=UNIT_MONEY,
        source="HCRIS cost-report distribution 2019-2024 (single-facility "
               "deals; multi-hospital rollups can exceed).",
        interpretation="Annual EBITDA in $M. Below 5M = sub-scale target; "
                       "50-150M = platform deals; above 500M = mega-LBO.",
    ),
    # ── Market structure ────────────────────────────────────────────
    "hhi": MetricRange(
        plausible_min=500.0, plausible_max=10000.0, unit=UNIT_NUM,
        source="FTC/DOJ Horizontal Merger Guidelines (2023). HHI 0-10,000 "
               "is the definitional range; below 500 is indistinguishable "
               "from perfect competition.",
        interpretation="Market concentration index. <1,500 = unconcentrated; "
                       "1,500-2,500 = moderate; >2,500 = highly concentrated.",
    ),
    "cr3": MetricRange(
        plausible_min=0.0, plausible_max=1.0, unit=UNIT_PCT,
        source="Definitional — CR3 is a share-sum, bounded [0, 1].",
        interpretation="Combined share of top-3 players.",
    ),
    "cr5": MetricRange(
        plausible_min=0.0, plausible_max=1.0, unit=UNIT_PCT,
        source="Definitional — CR5 is a share-sum, bounded [0, 1].",
        interpretation="Combined share of top-5 players.",
    ),
    "market_share": MetricRange(
        plausible_min=0.0, plausible_max=1.0, unit=UNIT_PCT,
        source="Definitional — market share is bounded [0, 1].",
        interpretation="Target's share of its primary service area.",
    ),
    # ── Capital structure ───────────────────────────────────────────
    "leverage_multiple": MetricRange(
        plausible_min=0.5, plausible_max=12.0, unit=UNIT_X,
        source="Phase 4 spec. Typical HC-PE LBO: 4.5-7x net debt/EBITDA "
               "(S&P LCD middle-market data). Above 8x is aggressive; "
               "above 10x is covenant-risk territory.",
        interpretation="Net debt / EBITDA. 4-6x = mainstream HC-PE; "
                       ">8x = aggressive / distressed.",
    ),
    "covenant_headroom_pct": MetricRange(
        plausible_min=-0.50, plausible_max=2.00, unit=UNIT_PCT,
        source="Phase 4 spec. Negative = breach; 0-50% = tight; "
               ">100% = abundant cushion (common at close).",
        interpretation="Distance from covenant threshold. Negative = "
                       "already tripped; <25% = tight; >100% = cushioned.",
    ),
    # ── RCM operating metrics ────────────────────────────────────────
    # TODO(phase-7): subsector-aware guards. The ranges below cover the
    # widest partner-plausible envelope across ALL hospital subsectors
    # combined, because the render sites don't currently pass subsector
    # context. A future pass should take (metric, subsector) and look
    # up per-subsector bands (e.g. acute + behavioral + ASC each).
    "denial_rate": MetricRange(
        # Widened in Phase 6D from 0.30 to 0.38 to accommodate
        # behavioral-health segment (HFMA MAP 2024 behavioral band
        # has P75=32%, vs acute-hospital P75=15%). The widened ceiling
        # is calibrated so behavioral P75 renders cleanly while still
        # flagging >40% as operational crisis for any segment.
        plausible_min=0.005, plausible_max=0.38, unit=UNIT_PCT,
        source="HFMA MAP 2024: acute-hospital P25=5% / P50=11% / "
               "P75=15% + behavioral P75=32%. Ceiling set at 38% to "
               "cover both + 6%-headroom. Below 0.5% is implausibly "
               "clean for any hospital segment.",
        interpretation="Initial denial rate. Acute P50 ~11%; "
                       "behavioral P75 ~32%; above 38% = operational "
                       "crisis regardless of subsector.",
    ),
    "days_in_ar": MetricRange(
        plausible_min=15.0, plausible_max=120.0, unit=UNIT_DAYS,
        source="HFMA MAP 2024 (DAR P25=40d, P50=50d, P75=62d). Below 15 "
               "days is implausible for most hospital RCM; above 120 is "
               "near-write-off territory.",
        interpretation="Accounts-receivable days. 40-55 = healthy; "
                       ">70 = problematic; >100 = near collection-crisis.",
    ),
    "clean_claim_rate": MetricRange(
        plausible_min=0.50, plausible_max=0.99, unit=UNIT_PCT,
        source="HFMA MAP 2024 (clean-claim P25=88%, P50=93%, P75=96%). "
               "Below 50% is systemic; above 99% is data-quality flag.",
        interpretation="% of claims accepted on first submission. "
                       ">93% = healthy; <80% = upstream coding issues.",
    ),
    "first_pass_resolution": MetricRange(
        plausible_min=0.30, plausible_max=0.99, unit=UNIT_PCT,
        source="HFMA MAP 2024. First-pass resolution (claims paid without "
               "rework) P50 ~85%. Below 30% = manual-work avalanche.",
        interpretation="% of claims paid without rework. >85% target.",
    ),
    "net_collection_rate": MetricRange(
        plausible_min=0.80, plausible_max=0.99, unit=UNIT_PCT,
        source="HFMA MAP 2024 (P25=92%, P50=96%, P75=98%). Below 80% is "
               "payer-dispute crisis.",
        interpretation="% of net revenue ultimately collected. "
                       "95-98% healthy; <90% = large leakage.",
    ),
    "cost_to_collect": MetricRange(
        plausible_min=0.01, plausible_max=0.10, unit=UNIT_PCT,
        source="HFMA MAP 2024 target band (2-4% of NPR). Above 10% = "
               "RCM-vendor emergency.",
        interpretation="RCM cost / net revenue. HFMA target 2-4%; "
                       ">6% = overstaffed or broken workflow.",
    ),
    "final_writeoff_rate": MetricRange(
        # Widened in Phase 6D from 0.15 to 0.20. Behavioral-health
        # segment has structurally higher bad-debt ratios (Medicaid
        # eligibility churn, self-pay psych admissions) — HFMA MAP
        # 2024 behavioral P75 is 16%. 20% ceiling covers behavioral
        # segment while still flagging >20% as payer-mix failure for
        # any subsector.
        plausible_min=0.001, plausible_max=0.20, unit=UNIT_PCT,
        source="HFMA MAP 2024: acute-hospital P50 ~3% / P75 ~8%; "
               "behavioral-health P75 ~16%. Ceiling set at 20% to "
               "cover behavioral segment + small headroom.",
        interpretation="Permanent write-off as % of billed. Acute "
                       "<5% healthy; behavioral <16%; any subsector "
                       ">20% = payer-mix or eligibility failure.",
    ),
    # ── Revenue / volume ────────────────────────────────────────────
    "npr_m": MetricRange(
        plausible_min=5.0, plausible_max=5000.0, unit=UNIT_MONEY,
        source="Phase 4 spec. Single-facility NPR: $5M (small CAH) to "
               "$5B (mega-system). Below $5M = sub-scale; above $5B = "
               "multi-system rollup, not a single hospital.",
        interpretation="Net patient revenue in $M. $50-200M = community "
                       "hospital; $500M+ = academic medical center.",
    ),
    "patient_volume_annual": MetricRange(
        plausible_min=100.0, plausible_max=100000.0, unit=UNIT_NUM,
        source="HCRIS inpatient-admission distribution. CAH: 100-2,000; "
               "community: 5-25K; academic: 25-60K; mega-system 100K.",
        interpretation="Annual inpatient discharges. Small CAH <1,000; "
                       "community ~10-20K; academic 30-60K.",
    ),
    "bed_count": MetricRange(
        plausible_min=10.0, plausible_max=2500.0, unit=UNIT_NUM,
        source="CMS PoS file 2024. CAH ≤ 25 beds by statute; largest "
               "US facilities ~2,200 beds.",
        interpretation="Staffed beds. <25 = CAH; 100-400 = community; "
                       "400-1,000 = academic; >1,000 = mega-facility.",
    ),
    # ── Case-mix ─────────────────────────────────────────────────────
    "case_mix_index": MetricRange(
        plausible_min=0.5, plausible_max=4.0, unit=UNIT_NUM,
        source="CMS IPPS case-mix index. National average ~1.75; "
               "academic/tertiary up to 2.5+; critical access closer to 1.0.",
        interpretation="Acuity-weighted case mix. 1.0 = average; >2.0 = "
                       "high-acuity; <1.0 = low-acuity CAH or outpatient.",
    ),
    # ── Deal structure ──────────────────────────────────────────────
    "hold_years": MetricRange(
        plausible_min=1.0, plausible_max=10.0, unit=UNIT_NUM,
        source="Preqin PE hold-period distribution 2015-2024. P25=3.5y, "
               "P50=5.0y, P75=7.0y.",
        interpretation="Years from close to exit. 4-6y = typical; "
                       "<2y = quick flip; >8y = zombie / stretched.",
    ),
    "sponsor_ownership_pct": MetricRange(
        plausible_min=0.05, plausible_max=1.0, unit=UNIT_PCT,
        source="Definitional — ownership is bounded [0, 1]; minority "
               "stakes below 5% are not classified as sponsor deals.",
        interpretation="Sponsor's fully-diluted ownership at close.",
    ),
    # ── Scores & grades (0-100 or 0-1) ──────────────────────────────
    "investability_score": MetricRange(
        plausible_min=0.0, plausible_max=100.0, unit=UNIT_NUM,
        source="pe_intelligence/investability_scorer.py — composite 0-100.",
        interpretation="Composite score. >75 = strong; 50-74 = on-the-"
                       "fence; <50 = pass-level.",
    ),
    "consistency_score": MetricRange(
        # data_public/sponsor_track_record.sponsor_consistency_score_raw
        # returns a 0-100 integer (not a 0-1 fraction), so this range
        # matches the backend's actual shape rather than the docstring.
        plausible_min=0.0, plausible_max=100.0, unit=UNIT_NUM,
        source="data_public/sponsor_track_record.py:sponsor_consistency_score_raw "
               "returns 0-100.",
        interpretation="Sponsor consistency. >70 = high; <45 = low.",
    ),
    "data_completeness_pct": MetricRange(
        plausible_min=0.0, plausible_max=1.0, unit=UNIT_PCT,
        source="analysis/completeness.py — coverage fraction.",
        interpretation="% of metrics populated. <70% = patchy packet.",
    ),
    "loss_rate": MetricRange(
        plausible_min=0.0, plausible_max=1.0, unit=UNIT_PCT,
        source="Definitional — fraction of deals below 1.0x MOIC.",
        interpretation="Share of deals returning <1.0x.",
    ),
    "home_run_rate": MetricRange(
        plausible_min=0.0, plausible_max=1.0, unit=UNIT_PCT,
        source="Definitional — fraction of deals ≥3.0x MOIC.",
        interpretation="Share of deals returning ≥3.0x.",
    ),
}


class UnknownMetric(KeyError):
    """Raised when a caller references a metric not in REGISTRY.

    Helpful to catch typos early — an unknown metric name would
    otherwise silently render the raw value without any guard.
    """


def _lookup(metric_name: str) -> MetricRange:
    try:
        return REGISTRY[metric_name]
    except KeyError:
        raise UnknownMetric(
            f"metric {metric_name!r} not in REGISTRY. "
            f"Known metrics: {sorted(REGISTRY.keys())}"
        ) from None


# ── Number formatters ────────────────────────────────────────────────

def _fmt(value: float, unit: str) -> str:
    if unit == UNIT_X:
        return f"{value:.2f}x"
    if unit == UNIT_PCT:
        return f"{value*100:.1f}%"
    if unit == UNIT_MONEY:
        # value is in $M; escalate to $B if large
        if abs(value) >= 1000:
            return f"${value/1000:.2f}B"
        return f"${value:,.1f}M"
    if unit == UNIT_DAYS:
        return f"{value:.1f}d"
    # num: comma-separated integer-ish
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def _fmt_range(mr: MetricRange) -> str:
    return f"{_fmt(mr.plausible_min, mr.unit)}–{_fmt(mr.plausible_max, mr.unit)}"


def _coerce(value: Any) -> Optional[float]:
    """Turn arbitrary input into a float, or None for NaN / unparseable."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


# ── Public API ───────────────────────────────────────────────────────

def render_number(
    value: Any,
    metric_name: str,
    *,
    fmt: Optional[str] = None,
) -> str:
    """Render a numeric value with a reasonableness guard.

    - None / NaN / unparseable → "—"
    - In-range              → clean formatted value
    - Out-of-range          → red pill with the value and a tooltip
                              "Value outside expected range (X–Y).
                              Check inputs."

    ``fmt`` overrides the unit inferred from the registry (rare — use
    only when the caller needs a different unit than the metric's
    default, e.g. rendering a pct metric as a decimal).
    """
    mr = _lookup(metric_name)
    unit = fmt or mr.unit
    f = _coerce(value)
    if f is None:
        return f'<span class="ck-num-nil" style="color:{P["text_faint"]};">—</span>'

    in_range = (mr.plausible_min <= f <= mr.plausible_max)
    formatted = _fmt(f, unit)

    if in_range:
        return (
            f'<span class="ck-num" '
            f'style="font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text"]};">'
            f'{_html.escape(formatted)}</span>'
        )

    # Out-of-range — warning pill. Use the existing chartis warning
    # palette (critical red for implausible values). Tooltip shows the
    # plausible range + a "check inputs" nudge.
    tooltip = (
        f"Value outside expected range "
        f"({_fmt_range(mr)} for {metric_name}). Check inputs."
    )
    return (
        f'<span class="ck-num-bad" '
        f'title="{_html.escape(tooltip)}" '
        f'style="display:inline-block;'
        f'background:rgba(239,68,68,0.15);'
        f'color:{P["negative"]};'
        f'border:1px solid {P["negative"]};'
        f'border-radius:2px;'
        f'padding:0px 5px;'
        f'font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;'
        f'font-weight:600;">'
        f'⚠ {_html.escape(formatted)}</span>'
    )


def is_out_of_range(value: Any, metric_name: str) -> bool:
    """True iff value is non-null AND outside plausible range."""
    mr = _lookup(metric_name)
    f = _coerce(value)
    if f is None:
        return False
    return not (mr.plausible_min <= f <= mr.plausible_max)


def warning_for(value: Any, metric_name: str) -> Optional[str]:
    """Return the tooltip-style warning string for an out-of-range value,
    or None if in-range / nil. Used by JSON API guards to attach a
    ``<metric>_warning`` sibling field."""
    mr = _lookup(metric_name)
    f = _coerce(value)
    if f is None:
        return None
    if mr.plausible_min <= f <= mr.plausible_max:
        return None
    return (
        f"value outside expected range "
        f"{_fmt_range(mr)} for {metric_name}"
    )


# ── Table helper ─────────────────────────────────────────────────────

def render_table_with_guards(
    rows: List[Dict[str, Any]],
    columns: List[Tuple[str, str, str]],
    *,
    row_id_key: Optional[str] = None,
    max_rows: Optional[int] = None,
) -> str:
    """Render a sortable chartis table with per-cell reasonableness
    guards and an aggregate warning banner.

    ``columns`` is a list of ``(row_key, display_label, metric_name)``
    tuples. For columns that are strings (not metrics), pass
    ``metric_name`` as empty string and the cell renders as escaped
    text.

    ``row_id_key`` — if given, the cell values for that key are wrapped
    in a <strong> for scanning. (E.g., the deal name column.)

    Returns the HTML block (panel-free — wrap in your own panel).

    The top of the table renders a banner when ANY cell is out-of-range:
    "⚠ N of M rows contain values outside expected ranges. Flagged
    values shown in red."
    """
    if max_rows is not None:
        rows = list(rows)[:max_rows]

    # First pass — count offending rows.
    bad_rows = 0
    for row in rows:
        for key, _, metric in columns:
            if not metric:
                continue
            if is_out_of_range(row.get(key), metric):
                bad_rows += 1
                break  # one hit per row is enough

    # Banner
    banner = ""
    if bad_rows > 0:
        banner = (
            f'<div class="ck-sanity-banner" style="'
            f'background:rgba(239,68,68,0.10);'
            f'border:1px solid {P["negative"]};'
            f'border-left-width:4px;'
            f'border-radius:3px;'
            f'padding:8px 12px;margin-bottom:10px;'
            f'font-size:11.5px;color:{P["text"]};">'
            f'<span style="color:{P["negative"]};font-weight:700;'
            f'letter-spacing:0.08em;">⚠ {bad_rows} of {len(rows)} rows</span>'
            f' contain values outside expected ranges. '
            f'Flagged values shown in red — hover for the expected band.'
            f'</div>'
        )

    # Header
    header_cells = []
    for _, label, metric in columns:
        numeric = metric and REGISTRY[metric].unit in (
            UNIT_MONEY, UNIT_PCT, UNIT_X, UNIT_NUM, UNIT_DAYS,
        )
        cls = ' class="num"' if numeric else ''
        header_cells.append(f'<th{cls}>{_html.escape(label)}</th>')

    # Body
    body_rows = []
    for row in rows:
        cells = []
        for key, _, metric in columns:
            val = row.get(key)
            if metric:
                unit = REGISTRY[metric].unit
                numeric = unit in (UNIT_MONEY, UNIT_PCT, UNIT_X, UNIT_NUM, UNIT_DAYS)
                cls = ' class="num"' if numeric else ''
                rendered = render_number(val, metric)
                cells.append(f'<td{cls}>{rendered}</td>')
            else:
                # String / badge / unguarded column
                display = _html.escape(str(val)) if val is not None else '—'
                if row_id_key and key == row_id_key:
                    display = f'<strong>{display}</strong>'
                cells.append(f'<td>{display}</td>')
        body_rows.append(f'<tr>{"".join(cells)}</tr>')

    table = (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr>{"".join(header_cells)}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>'
    )
    return banner + table


def metric_explainer(metric_name: str) -> Dict[str, str]:
    """Return a small dict with label/interpretation/source for a metric.

    Used by Phase 3 explainer headers: a page that cites MOIC can emit a
    small tooltip or caption using this dict so the partner sees what
    the number means.
    """
    mr = _lookup(metric_name)
    return {
        "metric": metric_name,
        "range": _fmt_range(mr),
        "unit": mr.unit,
        "source": mr.source,
        "interpretation": mr.interpretation,
    }


# ── JSON response auto-annotation (Phase 4C) ─────────────────────────

# Map alias / common JSON field names onto REGISTRY metric names. Keeps
# the annotator from having to guess when the JSON uses a slightly-
# different name than the registry key.
_JSON_ALIASES: Dict[str, str] = {
    # MOIC aliases
    "median_moic":    "moic",
    "mean_moic":      "moic",
    "moic_p25":       "moic",
    "moic_p50":       "moic",
    "moic_p75":       "moic",
    "moic_p90":       "moic",
    "realized_moic":  "moic",
    "predicted_moic": "moic",
    "base_moic":      "moic",
    "bear_moic":      "moic",
    "bull_moic":      "moic",
    # IRR aliases
    "median_irr":     "irr",
    "mean_irr":       "irr",
    "irr_p25":        "irr",
    "irr_p50":        "irr",
    "irr_p75":        "irr",
    "irr_p90":        "irr",
    "realized_irr":   "irr",
    "predicted_irr":  "irr",
    "base_irr":       "irr",
    "bear_irr":       "irr",
    "bull_irr":       "irr",
    "projected_irr":  "irr",
    # Margin aliases
    "current_margin":      "ebitda_margin",
    "peer_median_margin":  "ebitda_margin",
    "ebitda_margin_p50":   "ebitda_margin",
    "new_ebitda_margin":   "ebitda_margin",
    # Multiple aliases
    "entry_ev_multiple":   "entry_multiple",
    "exit_ev_multiple":    "exit_multiple",
    # Leverage
    "net_debt_to_ebitda":  "leverage_multiple",
    "debt_to_ebitda":      "leverage_multiple",
    # RCM
    "initial_denial_rate": "denial_rate",
    "collection_rate":     "net_collection_rate",
    "write_off_pct":       "final_writeoff_rate",
    # Market structure
    "top_share":           "market_share",
    "top_player_share":    "market_share",
    # Hold period
    "median_hold_years":   "hold_years",
    # Score aliases
    "composite_score":     "investability_score",
}


def _resolve_metric(key: str) -> Optional[str]:
    """Return the REGISTRY metric name for a JSON key, or None."""
    if key in REGISTRY:
        return key
    return _JSON_ALIASES.get(key)


def attach_sanity_warnings(payload: Any) -> Any:
    """Recursively walk a JSON-serialisable structure and, for every
    numeric field whose key maps to a REGISTRY metric, attach a
    sibling ``<key>_warning`` string when the value is out of range.

    Rules:
      - The raw value is never modified. Downstream consumers keep
        the number; the warning is additive only.
      - Dicts are walked; lists of dicts are walked element-wise.
      - Non-dict / non-list values are returned unchanged.
      - A key is considered a metric if it's in REGISTRY (directly) or
        appears in _JSON_ALIASES.

    The annotator is conservative: it only fires when the key matches a
    known metric name. Arbitrary numeric fields with names like
    ``request_id`` or ``count`` are never annotated.
    """
    if isinstance(payload, dict):
        out: Dict[str, Any] = {}
        # First pass — copy the payload
        for k, v in payload.items():
            out[k] = attach_sanity_warnings(v)
        # Second pass — add warning siblings for metric-named numeric keys
        for k, v in list(out.items()):
            if k.endswith("_warning"):
                continue
            metric = _resolve_metric(k)
            if metric is None:
                continue
            msg = warning_for(v, metric)
            if msg is not None and f"{k}_warning" not in out:
                out[f"{k}_warning"] = msg
        return out
    if isinstance(payload, list):
        return [attach_sanity_warnings(item) for item in payload]
    return payload


__all__ = [
    "MetricRange",
    "REGISTRY",
    "UnknownMetric",
    "UNIT_MONEY", "UNIT_PCT", "UNIT_X", "UNIT_NUM", "UNIT_DAYS",
    "render_number",
    "is_out_of_range",
    "warning_for",
    "render_table_with_guards",
    "metric_explainer",
    "attach_sanity_warnings",
]
