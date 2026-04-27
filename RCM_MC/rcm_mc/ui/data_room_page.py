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

from ._chartis_kit import chartis_shell
from ..portfolio.store import PortfolioStore
from .brand import PALETTE


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

    # ── KPIs ──
    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(5,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_total}</div>'
        f'<div class="cad-kpi-label">Total Metrics</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-pos);">'
        f'{n_seller}</div>'
        f'<div class="cad-kpi-label">Seller-Confirmed</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-accent);">'
        f'{n_ml_only}</div>'
        f'<div class="cad-kpi-label">ML-Predicted Only</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(entries)}</div>'
        f'<div class="cad-kpi-label">Data Points Entered</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(_METRIC_DEFINITIONS)}</div>'
        f'<div class="cad-kpi-label">Available Metrics</div></div>'
        f'</div>'
    )

    # ── Data entry form ──
    metric_options = ""
    for key, defn in sorted(_METRIC_DEFINITIONS.items(), key=lambda x: x[1]["label"]):
        metric_options += f'<option value="{key}">{_html.escape(defn["label"])} ({defn["unit"]})</option>'

    entry_form = (
        f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
        f'<h2>Enter Seller Data</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:12px;">'
        f'Enter actual KPIs from the seller data room. Each entry triggers Bayesian '
        f'recalibration — our ML predictions update, confidence intervals narrow, '
        f'and the EBITDA bridge recalculates automatically.</p>'
        f'<form method="POST" action="/data-room/{_html.escape(ccn)}/add" '
        f'style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">'
        f'<div>'
        f'<label style="font-size:11px;color:var(--cad-text3);display:block;margin-bottom:4px;">'
        f'Metric</label>'
        f'<select name="metric" required style="width:100%;padding:7px 10px;'
        f'border:1px solid var(--cad-border);border-radius:4px;background:var(--cad-bg3);'
        f'color:var(--cad-text);font-size:12px;">{metric_options}</select></div>'
        f'<div>'
        f'<label style="font-size:11px;color:var(--cad-text3);display:block;margin-bottom:4px;">'
        f'Value (rates as decimal: 0.12 = 12%)</label>'
        f'<input type="number" name="value" step="any" required '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);border-radius:4px;'
        f'background:var(--cad-bg3);color:var(--cad-text);font-size:12px;box-sizing:border-box;"></div>'
        f'<div>'
        f'<label style="font-size:11px;color:var(--cad-text3);display:block;margin-bottom:4px;">'
        f'Sample Size (claims/months)</label>'
        f'<input type="number" name="sample_size" value="100" min="0" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);border-radius:4px;'
        f'background:var(--cad-bg3);color:var(--cad-text);font-size:12px;box-sizing:border-box;"></div>'
        f'<div>'
        f'<label style="font-size:11px;color:var(--cad-text3);display:block;margin-bottom:4px;">'
        f'Source</label>'
        f'<input type="text" name="source" placeholder="e.g. Seller Q4 2025 report" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);border-radius:4px;'
        f'background:var(--cad-bg3);color:var(--cad-text);font-size:12px;box-sizing:border-box;"></div>'
        f'<div>'
        f'<label style="font-size:11px;color:var(--cad-text3);display:block;margin-bottom:4px;">'
        f'Analyst</label>'
        f'<input type="text" name="analyst" placeholder="Your initials" '
        f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);border-radius:4px;'
        f'background:var(--cad-bg3);color:var(--cad-text);font-size:12px;box-sizing:border-box;"></div>'
        f'<div style="display:flex;align-items:flex-end;">'
        f'<button type="submit" class="cad-btn cad-btn-primary" style="width:100%;">'
        f'Add Data Point</button></div>'
        f'</form></div>'
    )

    # ── Calibration table — the money section ──
    cal_rows = ""
    surprises = []
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

        cal_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{_html.escape(cal.label)}</td>'
            f'<td class="num">{ml_str}</td>'
            f'<td class="num">{seller_str}</td>'
            f'<td class="num" style="font-weight:600;">{post_str}</td>'
            f'<td class="num" style="font-size:11px;">{ci_str}</td>'
            f'<td class="num">{delta_str}</td>'
            f'<td>{shrink_bar}</td>'
            f'<td>{src_badge}</td>'
            f'</tr>'
        )

    cal_section = (
        f'<div class="cad-card">'
        f'<h2>Calibrated Metrics — ML Prediction vs Seller Data</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'Each metric shows three values: our ML prediction (prior), the seller\'s reported value, '
        f'and the Bayesian posterior that blends both. With strong seller data (n &gt; 100), '
        f'the posterior converges to seller. With weak data, it stays near the ML prediction. '
        f'The shrinkage bar shows the weight: green = seller data, amber = ML prior.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Metric</th><th>ML Predicted</th><th>Seller</th><th>Calibrated</th>'
        f'<th>90% CI</th><th>Delta</th><th>Data/Prior</th><th>Source</th>'
        f'</tr></thead><tbody>{cal_rows}</tbody></table></div>'
    )

    # ── Surprises ──
    surprise_html = ""
    if surprises:
        surprise_items = ""
        for label, delta, direction in sorted(surprises, key=lambda s: -abs(s[1])):
            icon = "&#9650;" if direction == "better" else "&#9660;"
            color = "var(--cad-pos)" if direction == "better" else "var(--cad-neg)"
            surprise_items += (
                f'<div style="display:flex;gap:8px;padding:6px 0;'
                f'border-bottom:1px solid var(--cad-border);font-size:12.5px;">'
                f'<span style="color:{color};">{icon}</span>'
                f'<span style="font-weight:500;">{_html.escape(label)}</span>'
                f'<span style="color:{color};">Seller data is {direction} than predicted '
                f'({delta:+.1%} delta)</span></div>'
            )
        surprise_html = (
            f'<div class="cad-card" style="border-left:3px solid var(--cad-warn);">'
            f'<h2>Prediction Surprises ({len(surprises)})</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:8px;">'
            f'Metrics where seller data differs from ML prediction by &gt;15%. '
            f'These are the diligence findings that change the investment thesis.</p>'
            f'{surprise_items}</div>'
        )

    # ── Entry history ──
    history_rows = ""
    for e in entries[:15]:
        defn = _METRIC_DEFINITIONS.get(e.metric, {})
        mtype = defn.get("type", "rate")
        history_rows += (
            f'<tr>'
            f'<td>{_html.escape(defn.get("label", e.metric))}</td>'
            f'<td class="num">{_fmt_metric(e.value, mtype)}</td>'
            f'<td class="num">{e.sample_size}</td>'
            f'<td style="font-size:11px;">{_html.escape(e.source[:30])}</td>'
            f'<td style="font-size:11px;">{_html.escape(e.analyst[:10])}</td>'
            f'<td style="font-size:10px;color:var(--cad-text3);">{e.entered_at[:16]}</td>'
            f'</tr>'
        )

    history_section = ""
    if history_rows:
        history_section = (
            f'<div class="cad-card">'
            f'<h2>Entry History</h2>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Metric</th><th>Value</th><th>n</th><th>Source</th><th>Analyst</th><th>Date</th>'
            f'</tr></thead><tbody>{history_rows}</tbody></table></div>'
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

            delta_color = "var(--cad-pos)" if delta_uplift > 0 else "var(--cad-neg)"
            bridge_impact = (
                f'<div class="cad-card" style="border-left:3px solid var(--cad-pos);">'
                f'<h2>EBITDA Bridge Impact</h2>'
                f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
                f'Seller data changes the EBITDA bridge calculation. Current values from '
                f'seller reports replace ML predictions in the bridge.</p>'
                f'<div class="cad-kpi-grid" style="grid-template-columns:1fr 1fr 1fr;">'
                f'<div class="cad-kpi"><div class="cad-kpi-value">{_fm(ml_uplift)}</div>'
                f'<div class="cad-kpi-label">ML-Only Bridge</div></div>'
                f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-pos);">'
                f'{_fm(cal_uplift)}</div>'
                f'<div class="cad-kpi-label">Calibrated Bridge</div></div>'
                f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{delta_color};">'
                f'{_fm(delta_uplift)}</div>'
                f'<div class="cad-kpi-label">Delta from Seller Data</div></div>'
                f'</div></div>'
            )

    # ── Nav ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/hospital/{_html.escape(ccn)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Hospital Profile</a>'
        f'<a href="/ebitda-bridge/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">EBITDA Bridge</a>'
        f'<a href="/ic-memo/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">IC Memo</a>'
        f'<a href="/competitive-intel/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">Competitive Intel</a>'
        f'<a href="/ml-insights/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">ML Analysis</a>'
        f'</div>'
    )

    body = f'{kpis}{entry_form}{surprise_html}{bridge_impact}{cal_section}{history_section}{nav}'

    return chartis_shell(
        body,
        f"Data Room — {_html.escape(hospital_name)}",
        subtitle=(
            f"CCN {_html.escape(ccn)} | {n_seller} seller-confirmed | "
            f"{n_ml_only} ML-only | {len(entries)} data points entered"
        ),
    )
