"""SeekingChartis Data Room — merge seller data with ML predictions.

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
    chartis_shell, ck_kpi_block, ck_panel, ck_section_intro,
)
from ._glossary_link import metric_label_link
from ._provenance_tooltip import provenance_tooltip
from ..portfolio.store import PortfolioStore
from .brand import PALETTE
from .provenance import build_provenance_graph


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def _fmt_metric(val: float, metric_type: str) -> str:
    if metric_type == "rate":
        return f"{val:.1%}" if abs(val) < 2 else f"{val:.1f}%"
    if metric_type == "continuous":
        if abs(val) >= 1e6:
            return _fm(val)
        return f"{val:,.1f}"
    return f"{val:.3f}"


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

    intro = ck_section_intro(
        eyebrow=f"DATA ROOM · CCN {_html.escape(ccn)}",
        headline=f"{_html.escape(hospital_name)} — where seller data meets ML.",
        italic_word="meets",
        body=(
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
        metric_options += f'<option value="{key}">{_html.escape(defn["label"])} ({defn["unit"]})</option>'

    entry_form = ck_panel(
        '<p class="ck-section-body">'
        'Enter actual KPIs from the seller data room. Each entry triggers Bayesian '
        'recalibration — our ML predictions update, confidence intervals narrow, '
        'and the EBITDA bridge recalculates automatically.</p>'
        f'<form method="POST" action="/data-room/{_html.escape(ccn)}/add" class="dr-entry-form">'
        '<div>'
        '<label class="dr-entry-label">Metric</label>'
        f'<select name="metric" required class="dr-entry-input">{metric_options}</select></div>'
        '<div>'
        '<label class="dr-entry-label">Value (rates as decimal: 0.12 = 12%)</label>'
        '<input type="number" name="value" step="any" required class="dr-entry-input"></div>'
        '<div>'
        '<label class="dr-entry-label">Sample Size (claims/months)</label>'
        '<input type="number" name="sample_size" value="100" min="0" class="dr-entry-input"></div>'
        '<div>'
        '<label class="dr-entry-label">Source</label>'
        '<input type="text" name="source" placeholder="e.g. Seller Q4 2025 report" class="dr-entry-input"></div>'
        '<div>'
        '<label class="dr-entry-label">Analyst</label>'
        '<input type="text" name="analyst" placeholder="Your initials" class="dr-entry-input"></div>'
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

        ml_str = _fmt_metric(cal.ml_predicted, mtype) if cal.ml_predicted is not None else "—"
        seller_str = _fmt_metric(cal.seller_value, mtype) if cal.seller_value else "—"
        post_str = _fmt_metric(cal.bayesian_posterior, mtype)
        ci_str = f"[{_fmt_metric(cal.ci_low, mtype)}, {_fmt_metric(cal.ci_high, mtype)}]"

        # Source badge
        if cal.data_quality == "strong":
            src_badge = '<span style="background:var(--cad-pos);color:#fff;padding:1px 6px;border-radius:2px;font-size:9px;">CONFIRMED</span>'
        elif cal.data_quality in ("moderate", "weak"):
            src_badge = f'<span style="background:var(--cad-warn);color:#fff;padding:1px 6px;border-radius:2px;font-size:9px;">{cal.data_quality.upper()}</span>'
        else:
            src_badge = '<span style="background:var(--cad-border);color:var(--cad-text2);padding:1px 6px;border-radius:2px;font-size:9px;">ML ONLY</span>'

        # Shrinkage bar
        data_pct = max(0, min(100, (1 - cal.shrinkage) * 100))
        shrink_bar = (
            f'<div style="display:flex;height:6px;border-radius:2px;overflow:hidden;width:60px;">'
            f'<div style="width:{data_pct:.0f}%;background:var(--cad-pos);"></div>'
            f'<div style="width:{100 - data_pct:.0f}%;background:var(--cad-warn);"></div></div>'
        )

        # Delta indicator
        delta_str = ""
        if cal.delta_from_prediction is not None:
            delta = cal.delta_from_prediction
            if mtype == "rate":
                delta_str = f"{delta:+.1%}"
            else:
                delta_str = f"{delta:+,.1f}"
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

            # Track surprises
            if abs(delta) > (abs(cal.ml_predicted or 1) * 0.15):
                direction = "better" if (
                    (cal.direction == "lower" and delta < 0) or
                    (cal.direction == "higher" and delta > 0)
                ) else "worse"
                surprises.append((cal.label, delta, direction))

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

    cal_section = ck_panel(
        '<p class="ck-section-body">'
        "Each metric shows three values: our ML prediction (prior), the seller's reported value, "
        'and the Bayesian posterior that blends both. With strong seller data (n &gt; 100), '
        'the posterior converges to seller. With weak data, it stays near the ML prediction. '
        'The shrinkage bar shows the weight: green = seller data, amber = ML prior.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Metric</th><th>ML Predicted</th><th>Seller</th><th>Calibrated</th>'
        '<th>90% CI</th><th>Delta</th><th>Data/Prior</th><th>Source</th>'
        f'</tr></thead><tbody>{cal_rows}</tbody></table>',
        title="Calibrated Metrics — ML Prediction vs Seller Data",
    )

    # ── Surprises ──
    surprise_html = ""
    if surprises:
        surprise_items = ""
        for label, delta, direction in sorted(surprises, key=lambda s: -abs(s[1])):
            icon = "&#9650;" if direction == "better" else "&#9660;"
            cls = "cad-pos" if direction == "better" else "cad-neg"
            surprise_items += (
                '<div class="dr-surprise-row">'
                f'<span class="{cls}">{icon}</span>'
                f'<span><strong>{_html.escape(label)}</strong></span>'
                f'<span class="{cls}">Seller data is {direction} than predicted '
                f'({delta:+.1%} delta)</span></div>'
            )
        surprise_html = ck_panel(
            '<p class="ck-section-body">'
            'Metrics where seller data differs from ML prediction by &gt;15%. '
            'These are the diligence findings that change the investment thesis.</p>'
            f'{surprise_items}',
            title=f"Prediction Surprises ({len(surprises)})",
        )

    # ── Entry history ──
    history_rows = ""
    for e in entries[:15]:
        defn = _METRIC_DEFINITIONS.get(e.metric, {})
        mtype = defn.get("type", "rate")
        history_rows += (
            f'<tr>'
            f'<td>{metric_label_link(defn.get("label", e.metric), e.metric)}</td>'
            f'<td class="num">{_fmt_metric(e.value, mtype)}</td>'
            f'<td class="num">{e.sample_size}</td>'
            f'<td style="font-size:11px;">{_html.escape(e.source[:30])}</td>'
            f'<td style="font-size:11px;">{_html.escape(e.analyst[:10])}</td>'
            f'<td style="font-size:10px;color:var(--cad-text3);">{e.entered_at[:16]}</td>'
            f'</tr>'
        )

    history_section = ""
    if history_rows:
        history_section = ck_panel(
            '<table class="cad-table"><thead><tr>'
            '<th>Metric</th><th>Value</th><th>n</th><th>Source</th><th>Analyst</th><th>Date</th>'
            f'</tr></thead><tbody>{history_rows}</tbody></table>',
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

            bridge_impact = ck_panel(
                '<p class="ck-section-body">'
                'Seller data changes the EBITDA bridge calculation. Current values from '
                'seller reports replace ML predictions in the bridge.</p>'
                '<div class="ck-kpi-strip">'
                + ck_kpi_block("ML-Only Bridge", _fm(ml_uplift))
                + ck_kpi_block("Calibrated Bridge", _fm(cal_uplift))
                + ck_kpi_block("Delta from Seller Data", _fm(delta_uplift))
                + '</div>',
                title="EBITDA Bridge Impact",
            )

    # ── Nav ──
    nav = ck_panel(
        '<p class="ck-section-body">'
        f'<a href="/hospital/{_html.escape(ccn)}" class="cad-btn cad-btn-primary">Hospital Profile</a> '
        f'<a href="/ebitda-bridge/{_html.escape(ccn)}" class="cad-btn">EBITDA Bridge</a> '
        f'<a href="/ic-memo/{_html.escape(ccn)}" class="cad-btn">IC Memo</a> '
        f'<a href="/competitive-intel/{_html.escape(ccn)}" class="cad-btn">Competitive Intel</a> '
        f'<a href="/ml-insights/hospital/{_html.escape(ccn)}" class="cad-btn">ML Analysis</a>'
        '</p>',
        title="Cross-links",
    )

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
    body = f'{dr_styles}{intro}{kpis}{entry_form}{surprise_html}{bridge_impact}{cal_section}{history_section}{nav}'

    return chartis_shell(
        body,
        f"Data Room — {_html.escape(hospital_name)}",
        subtitle=(
            f"CCN {_html.escape(ccn)} | {n_seller} seller-confirmed | "
            f"{n_ml_only} ML-only | {len(entries)} data points entered"
        ),
    )
