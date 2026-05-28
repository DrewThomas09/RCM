"""Surface 06 · ML Analysis — three lenses on one hospital.

Wired to real ML services already in the codebase:
- intelligence.caduceus_score — composite investability (the same engine
  Profile uses; this surface adds the explainability layer).
- ml.margin_predictor.predict_margin — ridge-regression margin prediction
  with conformal CI, top driver attributions, and the model's R² + n.
- ml.rcm_performance_predictor.predict_hospital_rcm — predicted RCM
  metric performance (denial rate, days in AR, …) with CI brackets and
  peer percentile.
- ml.comparable_finder — nearest peers (the same peer engine Profile uses).

Components shipped (5 of 6 in the handoff):
1. Investability score with 4 component breakdown
2. Margin prediction with CI + top drivers
3. Stat strip (grade, projected margin, peer percentile, model R², n)
4. Nearest peers
6. Predicted RCM performance table

Component 5 (Distress factor contributions) is deferred to Phase 6b — the
`predict_distress` engine needs a trained `TrainedRCMPredictor` instance,
which is not currently cached for production use; training per request
would be too slow. Cross-link to the surface in the "what's next" note
once that pipeline lands.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._shell import _fmt_int, _fmt_money, _fmt_pct, deal_shell


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _panel(eyebrow: str, title: str, body_html: str) -> str:
    return (
        '<section style="background:#fff;border:1px solid #c9c1ac;'
        'padding:20px 22px;margin:0 0 18px;">'
        f'<span style="font-family:var(--sc-mono);font-size:10px;'
        f'letter-spacing:.18em;text-transform:uppercase;color:#1f7a5a;">'
        f'{_html.escape(eyebrow)}</span>'
        f'<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        f'line-height:1.15;margin:6px 0 14px;color:#15202b;">'
        f'{_html.escape(title)}</h3>'
        f'{body_html}</section>'
    )


def _empty(title: str, reason: str) -> str:
    return (
        '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
        'padding:24px 26px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
        'Model output not available</span>'
        f'<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        f'margin:6px 0 12px;color:#15202b;">{_html.escape(title)}</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)}</p>'
        '</section>'
    )


# ───────────────────────── investability ─────────────────────────

def _investability(hospital: Dict[str, Any]) -> str:
    try:
        from ...intelligence.caduceus_score import compute_caduceus_score
    except ImportError:                                # pragma: no cover
        from rcm_mc.intelligence.caduceus_score import compute_caduceus_score
    score_obj = compute_caduceus_score(hospital)
    score = int(getattr(score_obj, "score", 0))
    grade = str(getattr(score_obj, "grade", "—"))
    components = getattr(score_obj, "components", {}) or {}
    breakdown = getattr(score_obj, "breakdown", {}) or {}
    color = "#1f7a5a" if score >= 70 else ("#b8842e" if score >= 30 else "#b5321e")
    rows = []
    for name, pts in components.items():
        bd = breakdown.get(name, "")
        rows.append(
            '<div style="display:grid;grid-template-columns:1.4fr 0.6fr;'
            'gap:10px;align-items:baseline;padding:6px 0;'
            'border-bottom:1px solid #ece6d7;">'
            '<div>'
            f'<div style="font-family:var(--sc-serif);font-size:14.5px;'
            f'color:#15202b;">{_html.escape(str(name).replace("_", " ").title())}</div>'
            f'<div style="font-family:var(--sc-mono);font-size:10.5px;'
            f'color:#6a7480;margin-top:2px;">{_html.escape(str(bd))}</div>'
            '</div>'
            f'<div style="text-align:right;font-family:var(--sc-mono);font-size:13px;'
            f'color:#2a3a4a;font-variant-numeric:tabular-nums;">'
            f'+{float(pts):.1f} pts</div></div>'
        )
    return (
        '<div style="display:grid;grid-template-columns:0.55fr 1fr;gap:24px;'
        'align-items:center;">'
        '<div style="text-align:center;">'
        f'<div style="font-family:var(--sc-serif);font-size:64px;font-weight:400;'
        f'line-height:1;color:{color};">{score}</div>'
        '<div style="font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.18em;'
        'text-transform:uppercase;color:#6a7480;margin-top:6px;">Investability</div>'
        f'<div style="font-family:var(--sc-serif);font-size:18px;margin-top:8px;'
        f'color:{color};">Grade {_html.escape(grade)}</div>'
        '</div>'
        f'<div>{"".join(rows) or "<em>No score components computed.</em>"}</div>'
        '</div>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:14px 0 0;">'
        'COMPOSITE OF MARKET POSITION + FINANCIAL HEALTH + OP QUALITY '
        '(caduceus_score) &mdash; SAME ENGINE THE PROFILE SURFACE USES.</p>'
    )


# ───────────────────────── margin prediction ─────────────────────────

def _margin_prediction(margin_obj: Any) -> str:
    predicted = float(getattr(margin_obj, "predicted_margin", 0.0) or 0.0)
    actual = getattr(margin_obj, "actual_margin", None)
    ci_lo = float(getattr(margin_obj, "ci_low", 0.0) or 0.0)
    ci_hi = float(getattr(margin_obj, "ci_high", 0.0) or 0.0)
    pct = float(getattr(margin_obj, "peer_percentile", 0.0) or 0.0)
    r2 = float(getattr(margin_obj, "model_r2", 0.0) or 0.0)
    n = int(getattr(margin_obj, "n_training", 0) or 0)
    grade = str(getattr(margin_obj, "confidence_grade", "—"))
    drivers = list(getattr(margin_obj, "top_drivers", []) or [])
    # Top drivers
    driver_rows = []
    for d in drivers[:5]:
        label = str(getattr(d, "label", "") or getattr(d, "feature", ""))
        value = float(getattr(d, "value", 0.0) or 0.0)
        contribution = float(getattr(d, "contribution", 0.0) or 0.0)
        direction = str(getattr(d, "direction", ""))
        explanation = str(getattr(d, "explanation", ""))
        bp = contribution * 10000.0
        sign = "+" if bp > 0 else ""
        bar_color = "#1f7a5a" if contribution >= 0 else "#b5321e"
        bar_w = max(2.0, min(100.0, abs(bp) / 200.0 * 100.0))    # 200 bps full bar
        driver_rows.append(
            '<div style="padding:8px 0;border-bottom:1px solid #ece6d7;">'
            '<div style="display:grid;grid-template-columns:1.6fr 3fr 0.8fr;'
            'gap:14px;align-items:center;">'
            f'<div style="font-family:var(--sc-serif);font-size:14px;'
            f'color:#15202b;">{_html.escape(label)} '
            f'<span style="color:#6a7480;font-family:var(--sc-mono);font-size:10.5px;">'
            f'({direction})</span></div>'
            '<div style="background:#f3eddb;border:1px solid #ece6d7;'
            'height:10px;overflow:hidden;">'
            f'<div style="background:{bar_color};height:100%;width:{bar_w:.0f}%;"></div>'
            '</div>'
            '<div style="font-family:var(--sc-mono);font-size:11.5px;'
            'color:#2a3a4a;text-align:right;font-variant-numeric:tabular-nums;">'
            f'{sign}{bp:.0f} bps</div></div>'
            f'<div style="font-family:var(--sc-serif);font-size:12.5px;'
            f'font-style:italic;color:#6a7480;margin-top:4px;line-height:1.45;">'
            f'{_html.escape(explanation)}</div></div>'
        )
    actual_str = _fmt_pct(actual) if actual is not None else "—"
    return (
        '<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        'gap:12px;margin:0 0 14px;">'
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        '<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;margin:0 0 4px;">'
        'Predicted margin</dt>'
        f'<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        'color:#15202b;font-variant-numeric:tabular-nums;">'
        f'{_fmt_pct(predicted)}</dd>'
        '<dd style="font-family:var(--sc-mono);font-size:10.5px;color:#6a7480;'
        'margin-top:4px;font-variant-numeric:tabular-nums;">'
        f'90% CI [{_fmt_pct(ci_lo)} &middot; {_fmt_pct(ci_hi)}]</dd></div>'
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        '<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;margin:0 0 4px;">'
        'Actual margin (HCRIS)</dt>'
        f'<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{actual_str}</dd></div>'
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        '<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;margin:0 0 4px;">'
        'Model fit</dt>'
        f'<dd style="font-family:var(--sc-serif);font-size:18px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">R² {r2:.2f}</dd>'
        f'<dd style="font-family:var(--sc-mono);font-size:10.5px;color:#6a7480;'
        f'margin-top:4px;">n={n:,} · grade {_html.escape(grade)}</dd></div>'
        '</div>'
        + "".join(driver_rows) +
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'TOP 5 DRIVERS BY ABS CONTRIBUTION &middot; <code>EFFECT = COEFFICIENT × '
        'NORMALIZED VALUE</code> &middot; CI IS CONFORMAL (split-conformal '
        'coverage guarantee).</p>'
    )


# ───────────────────────── stat strip ─────────────────────────

def _stat_strip(margin_obj: Any, rcm_obj: Any, score_obj: Any) -> str:
    grade = str(getattr(score_obj, "grade", "—"))
    pct = float(getattr(margin_obj, "peer_percentile", 0.0) or 0.0) if margin_obj else 0.0
    predicted = float(getattr(margin_obj, "predicted_margin", 0.0) or 0.0) if margin_obj else 0.0
    rcm_grade = str(getattr(rcm_obj, "overall_rcm_grade", "—")) if rcm_obj else "—"
    rcm_score = float(getattr(rcm_obj, "overall_rcm_score", 0.0) or 0.0) if rcm_obj else 0.0
    rcm_rec = str(getattr(rcm_obj, "screening_recommendation", "")) if rcm_obj else ""
    rows = [
        ("Investability grade", grade),
        ("Projected margin",    _fmt_pct(predicted)),
        ("Peer percentile",     f"{int(round(pct * 100))}"),
        ("RCM grade",           rcm_grade),
        ("RCM score",           f"{rcm_score:.1f}"),
        ("Screening",           rcm_rec[:36] + ("…" if len(rcm_rec) > 36 else "")),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:17px;margin:0;'
        'color:#15202b;font-variant-numeric:tabular-nums;">'
        f'{_html.escape(value) if isinstance(value, str) else value}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
    )


# ───────────────────────── nearest peers ─────────────────────────

def _nearest_peers(hospital: Dict[str, Any]) -> str:
    try:
        from ...data.hcris import _get_latest_per_ccn
        from ...ml.comparable_finder import find_comparables
    except ImportError:                                # pragma: no cover
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ml.comparable_finder import find_comparables
    try:
        hdf = _get_latest_per_ccn()
        pool = hdf.to_dict("records") if hdf is not None else []
    except Exception:                                  # noqa: BLE001
        pool = []
    peers = find_comparables(hospital, pool, max_results=6) or []
    if not peers:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">'
                'No nearest peers returned.</p>')
    rows = []
    for p in peers:
        peer_ccn = _html.escape(str(p.get("ccn", "")), quote=True)
        peer_name = _html.escape(str(p.get("name", "") or f"CCN {peer_ccn}"))
        state = _html.escape(str(p.get("state", "") or "—"))
        beds = _fmt_int(p.get("beds"))
        sim = p.get("similarity_score")
        sim_str = f"{float(sim):.2f}" if sim is not None else "—"
        rows.append(
            '<tr>'
            f'<td><a href="/deals/{peer_ccn}/profile" '
            f'style="color:#1f7a5a;text-decoration:none;">{peer_name}</a></td>'
            f'<td>{state}</td><td class="num">{beds}</td>'
            f'<td class="num">{sim_str}</td></tr>'
        )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Hospital</th><th>State</th>'
        '<th class="num">Beds</th><th class="num">Similarity</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


# ───────────────────────── predicted RCM performance ─────────────────────────

def _rcm_performance(rcm_obj: Any) -> str:
    predictions = list(getattr(rcm_obj, "predictions", []) or [])
    if not predictions:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">'
                'No RCM predictions for this hospital.</p>')
    rows = []
    for p in predictions:
        metric = str(getattr(p, "metric", "") or "")
        pred = float(getattr(p, "predicted_value", 0.0) or 0.0)
        ci = getattr(p, "confidence_interval", (None, None)) or (None, None)
        pct = float(getattr(p, "peer_percentile", 0.0) or 0.0)
        interp = str(getattr(p, "interpretation", "") or "")
        r2 = float(getattr(p, "model_r2", 0.0) or 0.0)
        n = int(getattr(p, "n_training", 0) or 0)
        # Format the metric value depending on whether the metric name implies %, days, or raw
        if "rate" in metric or "ratio" in metric or "pct" in metric:
            v_fmt, lo_fmt, hi_fmt = (
                _fmt_pct(pred),
                _fmt_pct(ci[0]) if ci[0] is not None else "—",
                _fmt_pct(ci[1]) if ci[1] is not None else "—",
            )
        elif "days" in metric or "ar" in metric:
            v_fmt = f"{pred:.0f} days"
            lo_fmt = f"{ci[0]:.0f}" if ci[0] is not None else "—"
            hi_fmt = f"{ci[1]:.0f}" if ci[1] is not None else "—"
        else:
            v_fmt = f"{pred:,.2f}"
            lo_fmt = f"{ci[0]:,.2f}" if ci[0] is not None else "—"
            hi_fmt = f"{ci[1]:,.2f}" if ci[1] is not None else "—"
        rows.append(
            '<tr>'
            f'<td>{_html.escape(metric.replace("estimated_", "").replace("_", " ").title())}</td>'
            f'<td class="num">{v_fmt}</td>'
            f'<td class="num" style="font-size:11px;color:#6a7480;">[{lo_fmt} · {hi_fmt}]</td>'
            f'<td class="num">{int(round(pct * 100))}</td>'
            f'<td class="num" style="font-size:11px;color:#6a7480;">R² {r2:.2f} · n={n:,}</td>'
            f'<td style="font-family:var(--sc-serif);font-style:italic;color:#6a7480;font-size:12.5px;">'
            f'{_html.escape(interp)}</td>'
            '</tr>'
        )
    overall_grade = str(getattr(rcm_obj, "overall_rcm_grade", "—"))
    overall_rec = str(getattr(rcm_obj, "screening_recommendation", ""))
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Metric</th><th class="num">Predicted</th>'
        '<th class="num">90% CI</th><th class="num">Peer pct</th>'
        '<th class="num">Model</th><th>Read</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        f'<p style="font-family:var(--sc-serif);font-size:13.5px;color:#2a3a4a;'
        'line-height:1.55;margin:10px 0 0;">'
        f'<strong>Overall RCM grade {_html.escape(overall_grade)}</strong>'
        f'{(" &middot; " + _html.escape(overall_rec)) if overall_rec else ""}</p>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:6px 0 0;">'
        'PREDICTIONS FROM <code>predict_hospital_rcm</code> · 90% CI FROM PEER '
        'SAMPLE INTERVAL.</p>'
    )


# ───────────────────────── entry ─────────────────────────

def render_deal_ml(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 06 (ML Analysis) for ``ccn``.

    Three lenses on this hospital: investability, margin prediction,
    predicted RCM performance — plus the nearest-peers panel.
    """
    try:
        from ...data.hcris import _get_latest_per_ccn
        from ...ml.margin_predictor import predict_margin
        from ...ml.rcm_performance_predictor import predict_hospital_rcm
        from ...intelligence.caduceus_score import compute_caduceus_score
    except ImportError:                                # pragma: no cover
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ml.margin_predictor import predict_margin
        from rcm_mc.ml.rcm_performance_predictor import predict_hospital_rcm
        from rcm_mc.intelligence.caduceus_score import compute_caduceus_score
    try:
        hdf = _get_latest_per_ccn()
    except Exception:                                  # noqa: BLE001
        hdf = None

    # Margin prediction — can be slow first time (trains the ridge model on
    # the full HCRIS pool); subsequent calls reuse the trained instance via
    # the engine's own caching. If it fails or returns None, render an
    # honest empty for that panel — never a fabricated margin.
    margin_obj = None
    if hdf is not None and not hdf.empty:
        try:
            margin_obj = predict_margin(ccn, hdf)
        except Exception:                              # noqa: BLE001
            margin_obj = None

    # RCM performance — same honesty rule.
    rcm_obj = None
    if hdf is not None and not hdf.empty:
        try:
            rcm_obj = predict_hospital_rcm(ccn, hdf)
        except Exception:                              # noqa: BLE001
            rcm_obj = None

    score_obj = compute_caduceus_score(hospital)

    panels = [
        _panel("01 · INVESTABILITY", "Composite score + components",
               _investability(hospital)),
        (_panel("02 · MARGIN PREDICTION",
                "Ridge regression with conformal CI",
                _margin_prediction(margin_obj)) if margin_obj else
         _empty("Margin prediction unavailable",
                "The ridge model did not return a prediction for this CCN — "
                "the row may be missing features the model was trained on.")),
        _panel("03 · STAT STRIP", "One-line read across the three lenses",
               _stat_strip(margin_obj, rcm_obj, score_obj)),
        _panel("04 · NEAREST PEERS",
               "6 closest hospitals from the comparable finder",
               _nearest_peers(hospital)),
        (_panel("05 · PREDICTED RCM PERFORMANCE",
                "Per-metric prediction with 90% CI and peer percentile",
                _rcm_performance(rcm_obj)) if rcm_obj else
         _empty("Predicted RCM performance unavailable",
                "predict_hospital_rcm did not return a profile for this CCN.")),
        _panel("06 · WHAT'S NEXT", "Coming in Phase 6b",
               '<p style="font-family:var(--sc-serif);font-size:14.5px;'
               'line-height:1.55;color:#2a3a4a;margin:0;">'
               'The spec\'s "Distress factor contributions" panel needs the '
               '<code>predict_distress</code> engine, which expects a trained '
               '<code>TrainedRCMPredictor</code> — not currently cached for '
               'production. Per-request training would be too slow; it lands '
               'in Phase 6b once a cached predictor pipeline is in place.</p>'),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="ml", body_html=body,
        page_title=f"ML Analysis · {hospital.get('name') or f'CCN {ccn}'}",
    )
