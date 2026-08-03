"""PE Desk Data Room — merge seller data with ML predictions.

The differentiating feature: analysts enter actual KPIs from seller
reports, the system Bayesian-updates every prediction, recalculates
the EBITDA bridge, and shows exactly where the seller data confirms
or contradicts our models. Every data point has provenance.

This is the flywheel: every deal's seller data improves future predictions.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ._chartis_kit import (
    chartis_shell, ck_empty_state, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro, ck_source_link,
)
from ._glossary_link import metric_label_link
from ._provenance_tooltip import provenance_tooltip
from ..portfolio.store import PortfolioStore
from .brand import PALETTE
from .provenance import build_provenance_graph


def _fm(val: float) -> str:
    """Money, always 2 decimals (house rule: ``$450.25M``, ``$1,204.50``).

    The pre-fix form printed one decimal at the M/K scales and none at
    the base scale, so the same dollar figure rendered three different
    ways depending on magnitude — the bridge-impact KPIs sat next to
    2dp figures from every other surface.
    """
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.2f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.2f}K"
    return f"${val:,.2f}"


def _fmt_metric(val: float, metric_type: str, unit: str = "") -> str:
    """Format a metric value for display, honouring its declared unit.

    ``unit`` comes from ``_METRIC_DEFINITIONS[metric]["unit"]``. It
    matters because "continuous" covers three different kinds of
    number: dollars (annual_revenue, ebitda), counts
    (total_claims_volume) and plain magnitudes (days, FTEs, index).
    Formatting purely on ``metric_type`` printed a 1.2M-claim volume
    as ``$1.20M`` — a dollar sign on a claim count — and gave counts a
    spurious decimal. Callers that omit ``unit`` keep the legacy
    magnitude-only behaviour.
    """
    if metric_type == "rate":
        return f"{val:.1%}" if abs(val) < 2 else f"{val:.1f}%"
    if metric_type == "continuous":
        if unit == "$":
            return _fm(val)
        if unit == "count":
            return f"{val:,.0f}"
        if abs(val) >= 1e6:
            return _fm(val)
        return f"{val:,.1f}"
    return f"{val:.3f}"


def _fmt_delta(delta: float, metric_type: str, unit: str = "") -> str:
    """Signed delta in the metric's own unit.

    Rates carry the sign inside the percent format; everything else
    formats the magnitude through ``_fmt_metric`` (so dollars keep
    their ``$`` and counts stay integral) and prefixes the sign.
    """
    if metric_type == "rate":
        return f"{delta:+.1%}"
    sign = "+" if delta >= 0 else "-"
    return sign + _fmt_metric(abs(delta), metric_type, unit)


def _calibration_delta_svg(calibrations: List[Any]) -> str:
    """Signed surprise bars: seller data vs ML prediction per metric.

    For every metric with both an ML prior and a seller delta, draw
    the relative surprise (delta / |prediction|) from a center zero
    line — green when the surprise is favorable for the metric's
    direction ("lower is better" denial rate coming in lower), red
    when unfavorable, sorted by magnitude so the thesis-changing
    findings lead. Bars clamp at ±50% with a marker. ML-only metrics
    contribute nothing; no deltas renders nothing.
    """
    rows = []
    for cal in calibrations:
        delta = getattr(cal, "delta_from_prediction", None)
        pred = getattr(cal, "ml_predicted", None)
        if delta is None or not pred:
            continue
        rel = float(delta) / abs(float(pred))
        direction = str(getattr(cal, "direction", "") or "")
        if direction == "lower":
            better = delta < 0
        elif direction == "higher":
            better = delta > 0
        else:
            better = None
        rows.append({
            "label": str(getattr(cal, "label", "—")),
            "rel": rel,
            "better": better,
        })
    if not rows:
        return ""
    rows.sort(key=lambda r: -abs(r["rel"]))

    label_w, half_w, right_w = 200, 220, 70
    row_h, gap, pad_top, pad_bot = 18, 7, 16, 10
    cx0 = label_w + half_w
    width = label_w + 2 * half_w + right_w
    height = pad_top + len(rows) * (row_h + gap) - gap + pad_bot
    clamp = 0.50

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img" '
        f'aria-label="Seller-data surprise vs ML prediction per metric">'
        f'<line x1="{cx0}" y1="{pad_top - 8}" x2="{cx0}" '
        f'y2="{height - pad_bot}" stroke="{PALETTE["border"]}" '
        f'stroke-width="1"/>'
        f'<text x="{cx0}" y="{pad_top - 10}" text-anchor="middle" '
        f'font-size="8.5" fill="{PALETTE["text_muted"]}">ML PREDICTION</text>'
    ]
    for i, r in enumerate(rows):
        y = pad_top + i * (row_h + gap)
        ty = y + row_h / 2 + 3.5
        full_name = r["label"]
        name = full_name
        if len(name) > 28:
            name = name[:27] + "…"
        # A <title> child gives the truncated label a hover tooltip and
        # an accessible name — otherwise a clipped metric is
        # unidentifiable in the chart.
        parts.append(
            f'<text x="{label_w - 8}" y="{ty:.1f}" text-anchor="end" '
            f'font-size="10.5" fill="{PALETTE["text_secondary"]}">'
            f'<title>{_html.escape(full_name)}</title>'
            f'{_html.escape(name)}</text>'
        )
        rel = r["rel"]
        clamped = max(-clamp, min(clamp, rel))
        w = abs(clamped) / clamp * half_w
        tone = (
            PALETTE["positive"] if r["better"] is True
            else PALETTE["negative"] if r["better"] is False
            else PALETTE["text_muted"]
        )
        x = cx0 if rel >= 0 else cx0 - w
        sense = (
            "favorable" if r["better"] is True
            else "unfavorable" if r["better"] is False
            else "neutral direction"
        )
        bar_tip = f"{full_name}: {rel:+.1%} vs ML prediction ({sense})"
        parts.append(
            f'<rect x="{x:.1f}" y="{y}" width="{max(w, 1.5):.1f}" '
            f'height="{row_h}" rx="2" fill="{tone}" fill-opacity="0.8">'
            f'<title>{_html.escape(bar_tip)}</title></rect>'
        )
        val_s = f"{rel:+.1%}" + ("›" if abs(rel) > clamp else "")
        vx = cx0 + w + 6 if rel >= 0 else cx0 - w - 6
        anchor = "start" if rel >= 0 else "end"
        parts.append(
            f'<text x="{vx:.1f}" y="{ty:.1f}" text-anchor="{anchor}" '
            f'font-size="10" font-weight="600" fill="{tone}">{val_s}</text>'
        )
    parts.append("</svg>")
    note = (
        f'<div style="font-size:9.5px;letter-spacing:0.08em;'
        f'color:{PALETTE["text_muted"]};margin-top:4px;">'
        'SIGNED SURPRISE = DELTA ÷ |ML PREDICTION| · GREEN = FAVORABLE '
        'FOR THE METRIC\'S DIRECTION · AXIS CLAMPED AT ±50% (› = BEYOND)'
        "</div>"
    )
    return ck_panel(
        '<p class="ck-section-body">'
        "Every seller-confirmed metric plotted against the model: bars "
        "left/right of the center line show how far the seller's number "
        "landed from our prediction, colored by whether that surprise "
        "helps or hurts the thesis.</p>"
        '<div class="dr-delta-chart">' + "".join(parts) + note + "</div>",
        title="Seller Data vs Model — Signed Surprise",
    )


def render_data_room(
    ccn: str,
    hospital_name: str,
    beds: float,
    state: str,
    ml_predictions: Dict[str, float],
    db_path: str,
    hcris_profile: Optional[Dict[str, Any]] = None,
) -> str:
    """Render the Data Room page for a hospital."""
    from ..data.data_room import (
        _METRIC_DEFINITIONS, _ensure_tables,
        get_entries, calibrate_metrics,
    )

    # Route through PortfolioStore (campaign target 4E) so the read +
    # calibrate write inherit busy_timeout=5000, foreign_keys=ON, and
    # row_factory=Row. PortfolioStore.connect() closes the connection
    # on exit but does NOT auto-commit, so the explicit con.commit()
    # is preserved inside the with-block.
    with PortfolioStore(db_path).connect() as con:
        _ensure_tables(con)
        entries = get_entries(con, ccn)
        calibrations = calibrate_metrics(con, ccn, ml_predictions, beds=beds)
        con.commit()

    n_seller = sum(1 for c in calibrations if c.data_quality != "ml_only")
    n_ml_only = sum(1 for c in calibrations if c.data_quality == "ml_only")
    n_total = len(calibrations)

    # 2026-05-28 batch 21 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    intro = ck_editorial_head(
        eyebrow=f"DATA ROOM · CCN {_html.escape(ccn)}",
        title=(
            f"Data room — {_html.escape(hospital_name)}"
        ),
        meta=(
            f"{n_total} METRIC{'S' if n_total != 1 else ''} · "
            f"{n_seller} SELLER-CONFIRMED · "
            f"{n_ml_only} ML-ONLY · "
            f"{len(entries)} ENTRY POINT"
            f"{'S' if len(entries) != 1 else ''}"
        ),
        lede_italic_phrase="Where seller data meets ML.",
        lede_body=(
            f"{n_seller} seller-confirmed · {n_ml_only} ML-only · "
            f"{len(entries)} data points entered. Each entry triggers "
            "Bayesian recalibration: ML priors update, confidence "
            "intervals narrow, and the EBITDA bridge recalculates."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Total Metrics", f"{n_total}")
        + ck_kpi_block("Seller-Confirmed", f"{n_seller}")
        + ck_kpi_block("ML-Predicted Only", f"{n_ml_only}")
        + ck_kpi_block("Data Points Entered", f"{len(entries)}")
        + ck_kpi_block("Available Metrics", f"{len(_METRIC_DEFINITIONS)}")
        + '</div>'
    )

    # ── Data entry form ──
    metric_options = ""
    for key, defn in sorted(_METRIC_DEFINITIONS.items(), key=lambda x: x[1]["label"]):
        metric_options += (
            f'<option value="{_html.escape(str(key), quote=True)}">'
            f'{_html.escape(defn["label"])} '
            f'({_html.escape(str(defn["unit"]))})</option>'
        )

    # Every control is explicitly bound to its <label> via for/id. The
    # labels were previously floating siblings, so a screen reader
    # announced five unlabelled inputs and clicking a label did not
    # focus its field.
    entry_form = ck_panel(
        '<p class="ck-section-body">'
        'Enter actual KPIs from the seller data room. Each entry triggers Bayesian '
        'recalibration — our ML predictions update, confidence intervals narrow, '
        'and the EBITDA bridge recalculates automatically.</p>'
        f'<form method="POST" action="/data-room/{_html.escape(ccn)}/add" class="dr-entry-form">'
        '<div>'
        '<label class="dr-entry-label" for="dr-f-metric">Metric</label>'
        '<select id="dr-f-metric" name="metric" required class="dr-entry-input">'
        f'{metric_options}</select></div>'
        '<div>'
        '<label class="dr-entry-label" for="dr-f-value">'
        'Value (rates as decimal: 0.12 = 12%)</label>'
        '<input id="dr-f-value" type="number" name="value" step="any" required '
        'class="dr-entry-input"></div>'
        '<div>'
        '<label class="dr-entry-label" for="dr-f-n">Sample Size (claims/months)</label>'
        '<input id="dr-f-n" type="number" name="sample_size" value="100" min="0" '
        'class="dr-entry-input"></div>'
        '<div>'
        '<label class="dr-entry-label" for="dr-f-source">Source</label>'
        '<input id="dr-f-source" type="text" name="source" '
        'placeholder="e.g. Seller Q4 2025 report" class="dr-entry-input"></div>'
        '<div>'
        '<label class="dr-entry-label" for="dr-f-analyst">Analyst</label>'
        '<input id="dr-f-analyst" type="text" name="analyst" '
        'placeholder="Your initials" class="dr-entry-input"></div>'
        '<div class="dr-entry-submit">'
        '<button type="submit" class="cad-btn cad-btn-primary dr-entry-btn">Add Data Point</button></div>'
        '</form>',
        title="Enter Seller Data",
    )

    # Phase 4C: build a ProvenanceGraph for the calibration
    # table's posterior-value tooltips. build_provenance_graph
    # auto-loads the data_room_calibrations table via db_path
    # and produces CALCULATED nodes at observed:<metric> for
    # every metric whose Bayesian posterior was computed —
    # exactly the cells we're about to wrap. ml_predictions is
    # passed through so PREDICTED parents appear when no
    # calibration exists.
    prov_graph = build_provenance_graph(
        ccn=str(ccn),
        hcris_profile=dict(hcris_profile or {}),
        ml_predictions=dict(ml_predictions or {}),
        db_path=db_path,
    )

    # ── Calibration table — the money section ──
    cal_rows = ""
    surprises = []
    _first_tooltip = True
    for cal in sorted(calibrations, key=lambda c: c.label):
        defn = _METRIC_DEFINITIONS.get(cal.metric, {})
        mtype = defn.get("type", "rate")
        unit = str(defn.get("unit", "") or "")

        ml_str = (
            _fmt_metric(cal.ml_predicted, mtype, unit)
            if cal.ml_predicted is not None else "—"
        )
        # Key off data_quality, not truthiness: a genuine seller-reported
        # zero (zero write-offs in the sample) is data, and the old
        # falsy test rendered it as "no seller value".
        seller_str = (
            _fmt_metric(cal.seller_value, mtype, unit)
            if cal.data_quality != "ml_only" and cal.seller_value is not None
            else "—"
        )
        post_str = _fmt_metric(cal.bayesian_posterior, mtype, unit)
        ci_str = (
            f"[{_fmt_metric(cal.ci_low, mtype, unit)}, "
            f"{_fmt_metric(cal.ci_high, mtype, unit)}]"
        )

        # Source badge
        if cal.data_quality == "strong":
            src_badge = '<span style="background:var(--cad-pos);color:#fff;padding:1px 6px;border-radius:2px;font-size:9px;">CONFIRMED</span>'
        elif cal.data_quality in ("moderate", "weak"):
            src_badge = f'<span style="background:var(--cad-warn);color:#fff;padding:1px 6px;border-radius:2px;font-size:9px;">{cal.data_quality.upper()}</span>'
        else:
            src_badge = '<span style="background:var(--cad-border);color:var(--cad-text2);padding:1px 6px;border-radius:2px;font-size:9px;">ML ONLY</span>'

        # Shrinkage bar. The split is the only place the blend weight
        # is stated, so it carries a text alternative — a bare pair of
        # colored divs is invisible to a screen reader and unreadable
        # in print.
        data_pct = max(0, min(100, (1 - cal.shrinkage) * 100))
        shrink_label = (
            f"Seller data weight {data_pct:.1f}% · "
            f"ML prior weight {100 - data_pct:.1f}%"
        )
        shrink_bar = (
            f'<div style="display:flex;height:6px;border-radius:2px;'
            f'overflow:hidden;width:60px;" role="img" '
            f'aria-label="{_html.escape(shrink_label, quote=True)}" '
            f'title="{_html.escape(shrink_label, quote=True)}">'
            f'<div style="width:{data_pct:.0f}%;background:var(--cad-pos);"></div>'
            f'<div style="width:{100 - data_pct:.0f}%;background:var(--cad-warn);"></div></div>'
        )

        # Delta indicator
        delta_str = ""
        if cal.delta_from_prediction is not None:
            delta = cal.delta_from_prediction
            delta_str = _fmt_delta(delta, mtype, unit)
            delta_color = "var(--cad-text2)"
            if cal.direction == "lower" and delta < 0:
                delta_color = "var(--cad-pos)"
            elif cal.direction == "lower" and delta > 0:
                delta_color = "var(--cad-neg)"
            elif cal.direction == "higher" and delta > 0:
                delta_color = "var(--cad-pos)"
            elif cal.direction == "higher" and delta < 0:
                delta_color = "var(--cad-neg)"
            delta_str = f'<span style="color:{delta_color};font-weight:600;">{delta_str}</span>'

            # Track surprises. Carry the metric type/unit and the
            # relative miss: the surprise threshold is relative, so the
            # list must rank on the relative figure too — ranking on the
            # raw delta let a dollar metric (delta in millions) outrank
            # a thesis-breaking denial-rate miss (delta in hundredths).
            if abs(delta) > (abs(cal.ml_predicted or 1) * 0.15):
                direction = "better" if (
                    (cal.direction == "lower" and delta < 0) or
                    (cal.direction == "higher" and delta > 0)
                ) else "worse"
                rel = (
                    delta / abs(cal.ml_predicted)
                    if cal.ml_predicted else None
                )
                surprises.append(
                    (cal.label, delta, direction, rel, mtype, unit)
                )

        # Phase 4C: hover the posterior cell to see the
        # CALCULATED node's prose + upstream (ML prior +
        # seller observation feeding the Bayesian blend).
        _post_tt = provenance_tooltip(
            label=cal.label, value=post_str,
            graph=prov_graph,
            metric_key=getattr(cal, "metric", ""),
            inject_css=_first_tooltip,
        )
        _first_tooltip = False
        cal_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{metric_label_link(cal.label, getattr(cal, "metric", ""))}</td>'
            f'<td class="num">{ml_str}</td>'
            f'<td class="num">{seller_str}</td>'
            f'<td class="num" style="font-weight:600;">{_post_tt}</td>'
            f'<td class="num" style="font-size:11px;">{ci_str}</td>'
            f'<td class="num">{delta_str}</td>'
            f'<td>{shrink_bar}</td>'
            f'<td>{src_badge}</td>'
            f'</tr>'
        )

    _cal_intro = (
        '<p class="ck-section-body">'
        "Each metric shows three values: our ML prediction (prior), the seller's reported value, "
        'and the Bayesian posterior that blends both. With strong seller data (n &gt; 100), '
        'the posterior converges to seller. With weak data, it stays near the ML prediction. '
        'The shrinkage bar shows the weight: green = seller data, amber = ML prior.</p>'
    )
    if cal_rows:
        cal_body = _cal_intro + (
            '<table class="cad-table"><thead><tr>'
            '<th scope="col">Metric</th>'
            '<th scope="col">ML Predicted</th>'
            '<th scope="col">Seller</th>'
            '<th scope="col">Calibrated</th>'
            '<th scope="col">90% CI</th>'
            '<th scope="col">Delta</th>'
            '<th scope="col" title="Blend weight — green share is seller '
            'data, amber share is the ML prior.">Data/Prior</th>'
            '<th scope="col" title="Strength of the seller evidence behind '
            'the calibration.">Evidence</th>'
            f'</tr></thead><tbody>{cal_rows}</tbody></table>'
        )
    else:
        # calibrate_metrics returns nothing when a metric has neither an
        # ML prior nor a seller entry — a brand-new CCN renders every
        # column header over an empty tbody, which reads as a broken
        # table rather than "nothing here yet".
        cal_body = ck_empty_state(
            "No calibrated metrics yet.",
            "Calibration needs at least one side of the blend: an ML "
            "prediction for this hospital, or a seller figure entered "
            "above. Add a data point from the seller's reporting pack "
            "and the posterior, credible interval and EBITDA bridge "
            "recalculate on save.",
            eyebrow="Calibration",
        )
    cal_section = ck_panel(
        cal_body,
        title="Calibrated Metrics · ML Prediction vs Seller Data",
    )

    # ── Surprises ──
    surprise_html = ""
    _surprise_intro = (
        '<p class="ck-section-body">'
        'Metrics where seller data differs from ML prediction by &gt;15%. '
        'These are the diligence findings that change the investment thesis.</p>'
    )
    if surprises:
        surprise_items = ""
        # Rank on the relative miss (falling back to the raw delta only
        # when there is no prior to divide by) so units don't decide the
        # order.
        for label, delta, direction, rel, s_mtype, s_unit in sorted(
            surprises, key=lambda s: -abs(s[3] if s[3] is not None else s[1])
        ):
            icon = "&#9650;" if direction == "better" else "&#9660;"
            cls = "cad-pos" if direction == "better" else "cad-neg"
            # Deltas are in the metric's own unit — printing a 12-day AR
            # miss as "+1200.0%" (the old percent-only format) was simply
            # a wrong number on a partner-facing finding.
            delta_txt = _fmt_delta(delta, s_mtype, s_unit)
            rel_txt = f" · {rel:+.1%} vs model" if rel is not None else ""
            surprise_items += (
                '<div class="dr-surprise-row">'
                f'<span class="{cls}" aria-hidden="true">{icon}</span>'
                f'<span><strong>{_html.escape(label)}</strong></span>'
                f'<span class="{cls}">Seller data is {direction} than predicted '
                f'({_html.escape(delta_txt)} delta{rel_txt})</span></div>'
            )
        surprise_html = ck_panel(
            _surprise_intro + surprise_items,
            title=f"Prediction Surprises ({len(surprises)})",
        )
    elif n_seller > 0:
        # Seller data exists and none of it moved a metric by >15%. That
        # is a finding — the model held up — so say it rather than
        # dropping the section and leaving the partner unsure whether
        # the check ran.
        surprise_html = ck_panel(
            _surprise_intro + ck_empty_state(
                "No prediction surprises.",
                f"All {n_seller} seller-confirmed metric"
                f"{'s' if n_seller != 1 else ''} landed within ±15.0% of "
                "the ML prediction — the model's priors are holding for "
                "this target. Nothing here contradicts the thesis.",
                eyebrow="Surprises",
                tone="positive",
            ),
            title="Prediction Surprises (0)",
        )

    # ── Entry history ──
    _HISTORY_LIMIT = 15
    history_rows = ""
    for e in entries[:_HISTORY_LIMIT]:
        defn = _METRIC_DEFINITIONS.get(e.metric, {})
        mtype = defn.get("type", "rate")
        e_unit = str(defn.get("unit", "") or "")

        # Provenance: the analyst types this field free-hand, and it is
        # very often a public dataset ("CMS HCRIS FY2023", "MedPAC
        # March 2026"). ck_source_link turns the known ones into a link
        # to the dataset itself and escapes everything else, so a
        # partner can always chase the number back to its origin.
        src_full = str(getattr(e, "source", "") or "")
        src_disp = src_full if len(src_full) <= 30 else src_full[:29] + "…"
        src_cell = ck_source_link(src_disp) if src_disp else "—"
        analyst_full = str(getattr(e, "analyst", "") or "")
        analyst_disp = (
            analyst_full if len(analyst_full) <= 10
            else analyst_full[:9] + "…"
        )
        entered = str(getattr(e, "entered_at", "") or "")
        history_rows += (
            f'<tr>'
            f'<td>{metric_label_link(defn.get("label", e.metric), e.metric)}</td>'
            f'<td class="num">{_fmt_metric(e.value, mtype, e_unit)}</td>'
            f'<td class="num">{e.sample_size:,.0f}</td>'
            # title carries the untruncated value — the cell shows at
            # most 30/10 characters and a partner could not otherwise
            # tell "Seller Q4 2025 report (revised)" from
            # "Seller Q4 2025 report (draft)".
            f'<td style="font-size:11px;" '
            f'title="{_html.escape(src_full or "—", quote=True)}">{src_cell}</td>'
            f'<td style="font-size:11px;" '
            f'title="{_html.escape(analyst_full or "—", quote=True)}">'
            f'{_html.escape(analyst_disp) or "—"}</td>'
            f'<td style="font-size:10px;color:var(--cad-text3);" '
            f'title="{_html.escape(entered, quote=True)}">'
            f'{_html.escape(entered[:16])}</td>'
            f'</tr>'
        )

    if history_rows:
        more = ""
        if len(entries) > _HISTORY_LIMIT:
            more = (
                '<p class="ck-section-body" style="margin-top:8px;">'
                f'Showing the {_HISTORY_LIMIT} most recent of '
                f'{len(entries)} entries. Every superseded value is kept '
                'in the audit trail.</p>'
            )
        history_section = ck_panel(
            '<table class="cad-table"><thead><tr>'
            '<th scope="col">Metric</th>'
            '<th scope="col">Value</th>'
            '<th scope="col" title="Sample size behind the value — '
            'claims or months.">n</th>'
            '<th scope="col">Source</th>'
            '<th scope="col">Analyst</th>'
            '<th scope="col">Date (UTC)</th>'
            f'</tr></thead><tbody>{history_rows}</tbody></table>{more}',
            title="Entry History",
        )
    else:
        # The panel used to disappear entirely with no entries, so a
        # partner had no way to tell "nobody has entered anything" from
        # "the history failed to load".
        history_section = ck_panel(
            ck_empty_state(
                "No seller data entered yet.",
                "Every value the deal team keys in above lands here with "
                "its source, the analyst who entered it and a UTC "
                "timestamp — the provenance trail the IC memo cites.",
                eyebrow="Entry history",
            ),
            title="Entry History",
        )

    # ── Bridge impact ──
    bridge_impact = ""
    if n_seller > 0:
        from .ebitda_bridge_page import _compute_bridge
        rev = float((hcris_profile or {}).get("net_patient_revenue", 0) or 0)
        ebitda = float((hcris_profile or {}).get("ebitda", 0) or 0)
        mc = float((hcris_profile or {}).get("medicare_pct", 0.4) or 0.4)

        if rev > 1e6:
            # Build overrides from calibrated values
            overrides = {}
            for cal in calibrations:
                if cal.data_quality != "ml_only":
                    overrides[f"{cal.metric}_current"] = cal.bayesian_posterior

            bridge_ml = _compute_bridge(rev, ebitda, medicare_pct=mc)
            bridge_cal = _compute_bridge(rev, ebitda, medicare_pct=mc, overrides=overrides)

            ml_uplift = bridge_ml["total_ebitda_impact"]
            cal_uplift = bridge_cal["total_ebitda_impact"]
            delta_uplift = cal_uplift - ml_uplift
            # "+$1.20M" reads as a delta; the bare formatter produced
            # "$-1.20M", with the sign stranded after the dollar sign.
            delta_s = ("+" if delta_uplift >= 0 else "-") + _fm(abs(delta_uplift))

            bridge_impact = ck_panel(
                '<p class="ck-section-body">'
                'Seller data changes the EBITDA bridge calculation. Current values from '
                'seller reports replace ML predictions in the bridge.</p>'
                '<div class="ck-kpi-strip">'
                + ck_kpi_block("ML-Only Bridge", _fm(ml_uplift))
                + ck_kpi_block("Calibrated Bridge", _fm(cal_uplift))
                + ck_kpi_block("Delta from Seller Data", delta_s)
                + '</div>'
                # Name the base the bridge is computed on, and link it:
                # revenue / EBITDA / Medicare mix all come off the cost
                # report, not from anything entered on this page.
                '<p class="ck-section-body" style="margin-top:10px;">'
                f'Base net patient revenue {_fm(rev)} and EBITDA '
                f'{_fm(ebitda)} from ' + ck_source_link("CMS HCRIS")
                + f' · Medicare mix {mc:.1%}. '
                f'<a href="/ebitda-bridge/{_html.escape(ccn, quote=True)}">'
                'Open the full seven-lever bridge →</a></p>',
                title="EBITDA Bridge Impact",
            )
        else:
            # Seller data exists but the bridge cannot be computed. Say
            # why — silently dropping the panel looked like the
            # calibration had no effect on value.
            bridge_impact = ck_panel(
                ck_empty_state(
                    "Bridge impact needs a revenue base.",
                    "No HCRIS net patient revenue is on file for this "
                    "CCN, so there is nothing to apply the calibrated "
                    "operating metrics to. Load the cost report for "
                    "this provider and the ML-only and calibrated "
                    "bridges appear here side by side.",
                    eyebrow="EBITDA bridge",
                    # ck_empty_state escapes cta_href itself — pass raw.
                    cta_label="Open the EBITDA bridge",
                    cta_href=f"/ebitda-bridge/{ccn}",
                ),
                title="EBITDA Bridge Impact",
            )

    # ── Nav ──
    # Standard per-deal context ribbon (consistent with every other
    # per-deal surface) replaces the bespoke cad-btn cross-links bar.
    # Data Room isn't one of the ribbon's own slots, so no pill is
    # highlighted — it still gives one-click access to every analysis.
    from .models_page import _model_nav
    deal_ribbon = _model_nav(ccn, active="")

    dr_styles = """
<style>
.dr-entry-form{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;}
.dr-entry-label{font-size:11px;color:var(--cad-text3);
display:block;margin-bottom:4px;}
.dr-entry-input{width:100%;padding:7px 10px;
border:1px solid var(--cad-border);border-radius:4px;
background:var(--cad-bg3);color:var(--cad-text);
font-size:12px;box-sizing:border-box;
transition:border-color 120ms ease, box-shadow 120ms ease;}
.dr-entry-input:focus{outline:none;border-color:var(--cad-link);
box-shadow:0 0 0 2px rgba(21,87,82,0.18);}
.dr-entry-submit{display:flex;align-items:flex-end;}
.dr-entry-btn{width:100%;}
.dr-surprise-row{display:flex;gap:8px;padding:6px 0;
border-bottom:1px solid var(--cad-border);font-size:12.5px;}
</style>
"""
    next_up = ck_next_section(
        "Run the diligence checklist",
        "/diligence/checklist",
        eyebrow="Up next",
        italic_word="checklist",
    )
    delta_chart = _calibration_delta_svg(calibrations)
    if not delta_chart and calibrations:
        # The chart draws nothing until a metric has BOTH an ML prior
        # and a seller value. With ML-only rows on screen the missing
        # panel looked like a rendering failure, so name the
        # precondition instead.
        delta_chart = ck_panel(
            ck_empty_state(
                "Nothing to compare yet.",
                "The surprise chart plots each metric's seller value "
                "against its ML prediction, so it needs both sides. "
                f"{n_ml_only} metric{'s are' if n_ml_only != 1 else ' is'} "
                "ML-only right now — enter the matching seller figure "
                "above and the bar appears here.",
                eyebrow="Signed surprise",
            ),
            title="Seller Data vs Model — Signed Surprise",
        )
    body = (
        f'{deal_ribbon}{dr_styles}{intro}{kpis}{entry_form}{surprise_html}'
        f'{delta_chart}{bridge_impact}{cal_section}{history_section}{next_up}'
    )

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        f"Data Room — {_html.escape(hospital_name)}",
        subtitle=(
            f"CCN {_html.escape(ccn)} | {n_seller} seller-confirmed | "
            f"{n_ml_only} ML-only | {len(entries)} data points entered"
        ),
    )
