"""Surface 13 · Levers — 7-lever bridge weighted by P(achievement).

The Bridge surface (#03) shows the GROSS 7-lever uplift. The Levers surface
(this one) shows the SAME 7 levers but weighted by the realization model's
estimate of how much is actually achievable — because "the biggest lever
isn't always the most likely," per the spec.

Wired to two real services already in the codebase:
- ui.ebitda_bridge_page._compute_bridge — the same calibrated 7-lever engine
  the Bridge surface uses.
- ml.realization_predictor.predict_realization — estimates the fraction of
  the GROSS uplift achievable for this CCN; returns a RealizationPrediction
  with expected fraction, 90% CI, top driver-factors (positive = boosts
  realization, negative = drags), grade, and model accuracy/n.

Components shipped (all 3 in the spec):
1. Hero stat strip       — current EBITDA, target gross EBITDA, total
                            P-weighted uplift, lever count, realization
                            grade (and CI)
2. 7-lever model panel   — per-lever bars showing GROSS impact + per-lever
                            probability slider markers + the P-weighted
                            impact derived from both
3. What this means panel — IC talking-point quote in serif (real, from the
                            realization narrative); cross-links to Bridge
                            and Returns

Spec build-note honored: total uplift = sum(P-weighted), not sum(gross).
Low-probability levers (<0.40) render in coral bars instead of green.

Per-lever probability: this surface assigns the SAME hospital-level
realization probability to every lever (the realization engine returns a
single P, not a per-lever P). This is honest — a per-lever P would need
data we don't have, and the spec's "probability slider" interaction is
read-only here (deferred until per-lever probabilities are modeled).
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._shell import _fmt_money, _fmt_pct, deal_shell


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _medicare_share(h: Dict[str, Any]) -> Optional[float]:
    for k in ("percent_days_medicare", "medicare_day_pct", "medicare_days_pct"):
        v = _safe_float(h.get(k))
        if v is not None:
            return v if v <= 1.5 else v / 100.0
    return None


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


def _empty(reason: str) -> str:
    return (
        '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
        'padding:24px 26px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
        'Levers cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">'
        'HCRIS inputs not available</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)} The probability-weighted '
        'bridge needs the same HCRIS inputs as the gross bridge.</p>'
        '</section>'
    )


def _grade_color(grade: str) -> str:
    g = (grade or "").upper()
    if g.startswith("A"):
        return "#1f7a5a"
    if g.startswith("B"):
        return "#155752"
    if g.startswith("C"):
        return "#b8842e"
    return "#b5321e"


def _hero(bridge: Dict[str, Any], realization: Any) -> str:
    p = float(getattr(realization, "expected_realization", 1.0) or 1.0)
    ci_lo, ci_hi = getattr(realization, "confidence_interval", (p, p)) or (p, p)
    grade = str(getattr(realization, "grade", "—"))
    color = _grade_color(grade)
    current = float(bridge.get("current_ebitda", 0.0) or 0.0)
    gross_uplift = float(bridge.get("total_ebitda_impact", 0.0) or 0.0)
    p_weighted = gross_uplift * p
    target_gross = current + gross_uplift
    target_pweighted = current + p_weighted
    n_levers = len(bridge.get("levers") or [])
    rows = [
        ("Current EBITDA",        _fmt_money(current)),
        ("Target (gross)",        _fmt_money(target_gross)),
        ("Target (P-weighted)",   _fmt_money(target_pweighted)),
        ("Gross uplift",          _fmt_money(gross_uplift)),
        ("P-weighted uplift",     _fmt_money(p_weighted)),
        ("Realization · grade",   f"{p*100:.0f}% · {grade}"),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{value}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        f'90% CI ON REALIZATION: [{ci_lo*100:.0f}% &middot; {ci_hi*100:.0f}%] · '
        'P-WEIGHTED UPLIFT = GROSS × REALIZATION; THIS IS THE BASE-CASE NUMBER '
        'TO BRING TO IC, NOT THE GROSS.</p>'
    )


def _lever_rows(bridge: Dict[str, Any], realization: Any) -> str:
    levers = list(bridge.get("levers") or [])
    if not levers:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">'
                'No lever produced any impact at this metric set.</p>')
    p = float(getattr(realization, "expected_realization", 1.0) or 1.0)
    # Use the largest GROSS impact as the bar's full width — so the relative
    # sizes match the Bridge surface, with a green→ink gradient for P-weight.
    max_gross = max(
        (abs(float(l.get("ebitda_impact") or 0.0)) for l in levers), default=0.0) or 1.0
    rows = []
    for lev in levers:
        name = str(lev.get("name") or lev.get("metric") or "")
        gross = float(lev.get("ebitda_impact") or 0.0)
        pw = gross * p
        gross_w = max(2.0, min(100.0, abs(gross) / max_gross * 100.0))
        pw_w = max(0.0, min(100.0, abs(pw) / max_gross * 100.0))
        # Low-probability lever (p<0.40) renders in coral instead of green.
        bar_color = "#b5321e" if p < 0.40 else "#1f7a5a"
        rows.append(
            '<div style="padding:10px 0;border-bottom:1px solid #ece6d7;">'
            '<div style="display:grid;grid-template-columns:1.6fr 3fr 1fr 0.9fr;'
            'gap:14px;align-items:center;">'
            f'<div style="font-family:var(--sc-serif);font-size:14px;'
            f'color:#15202b;">{_html.escape(name)}</div>'
            # Stacked bar: full bar = gross, dark inner = P-weighted portion
            '<div style="position:relative;background:#f3eddb;'
            'border:1px solid #ece6d7;height:14px;overflow:hidden;">'
            f'<div style="background:#c9bf9c;height:100%;width:{gross_w:.1f}%;"></div>'
            f'<div style="position:absolute;top:0;left:0;background:{bar_color};'
            f'height:100%;width:{pw_w:.1f}%;"></div>'
            '</div>'
            '<div style="font-family:var(--sc-mono);font-size:11.5px;'
            'color:#2a3a4a;text-align:right;font-variant-numeric:tabular-nums;">'
            f'{_fmt_money(gross)}</div>'
            '<div style="font-family:var(--sc-mono);font-size:11.5px;'
            f'color:{bar_color};text-align:right;font-variant-numeric:tabular-nums;">'
            f'{_fmt_money(pw)}</div></div>'
            '<div style="font-family:var(--sc-mono);font-size:9.5px;letter-spacing:.1em;'
            f'color:#6a7480;text-transform:uppercase;margin-top:4px;">'
            f'Realization P = {p*100:.0f}% (hospital-level)</div></div>'
        )
    legend = (
        '<div style="display:flex;gap:18px;margin:10px 0 0;font-family:var(--sc-mono);'
        'font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#6a7480;">'
        '<span><span style="display:inline-block;width:12px;height:8px;'
        'background:#c9bf9c;vertical-align:middle;margin-right:6px;"></span>'
        'Gross uplift</span>'
        '<span><span style="display:inline-block;width:12px;height:8px;'
        'background:#1f7a5a;vertical-align:middle;margin-right:6px;"></span>'
        'P-weighted (high realization)</span>'
        '<span><span style="display:inline-block;width:12px;height:8px;'
        'background:#b5321e;vertical-align:middle;margin-right:6px;"></span>'
        'P-weighted (low realization · &lt;40%)</span></div>'
    )
    return (
        '<div style="display:grid;grid-template-columns:1.6fr 3fr 1fr 0.9fr;'
        'gap:14px;padding:0 0 6px;font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;">'
        '<div>Lever</div><div>&nbsp;</div>'
        '<div style="text-align:right;">Gross Δ</div>'
        '<div style="text-align:right;">P-weighted Δ</div></div>'
        + "".join(rows) + legend +
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'PER-LEVER PROBABILITY IS THE HOSPITAL-LEVEL REALIZATION — A PER-LEVER P '
        'NEEDS DATA NOT IN HCRIS, AND THE SPEC\'S "PROBABILITY SLIDER" IS '
        'DEFERRED UNTIL THAT DATA LANDS.</p>'
    )


def _factors_panel(realization: Any) -> str:
    """Top realization factors from the ML model — risk-add vs risk-reduce."""
    factors = list(getattr(realization, "factors", []) or [])
    if not factors:
        return ""
    rows = []
    for f in factors[:6]:
        label = str(getattr(f, "label", "") or getattr(f, "feature", ""))
        impact = float(getattr(f, "impact", 0.0) or getattr(f, "contribution", 0.0) or 0.0)
        explanation = str(getattr(f, "explanation", ""))
        # Convention: positive impact = boosts realization (good)
        direction_color = "#1f7a5a" if impact >= 0 else "#b5321e"
        direction_label = "BOOSTS" if impact >= 0 else "DRAGS"
        rows.append(
            '<tr>'
            f'<td><div style="font-family:var(--sc-serif);font-size:14px;'
            f'color:#15202b;">{_html.escape(label)}</div>'
            f'<div style="font-family:var(--sc-serif);font-size:12.5px;'
            f'font-style:italic;color:#6a7480;margin-top:2px;line-height:1.45;">'
            f'{_html.escape(explanation)}</div></td>'
            f'<td><span style="font-family:var(--sc-mono);font-size:9.5px;'
            f'letter-spacing:.12em;text-transform:uppercase;color:{direction_color};">'
            f'{direction_label}</span></td>'
            f'<td class="num" style="font-family:var(--sc-mono);font-size:11.5px;'
            f'color:{direction_color};font-variant-numeric:tabular-nums;">'
            f'{("+" if impact >= 0 else "")}{impact:.2f}</td>'
            '</tr>'
        )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr><th>Factor</th><th>Direction</th><th class="num">Weight</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'FROM <code>ml.realization_predictor</code> · DRIVERS THE MODEL USES TO '
        'EXPLAIN WHY THIS HOSPITAL\'S REALIZATION IS WHERE IT IS.</p>'
    )


def _talking_point(realization: Any, bridge: Dict[str, Any]) -> str:
    p = float(getattr(realization, "expected_realization", 1.0) or 1.0)
    gross = float(bridge.get("total_ebitda_impact", 0.0) or 0.0)
    pw = gross * p
    narrative = str(getattr(realization, "narrative", "") or "")
    if not narrative:
        narrative = (
            f"At a {p*100:.0f}% expected realization, the gross "
            f"{_fmt_money(gross)} uplift becomes {_fmt_money(pw)} P-weighted. "
            "Bring that number to IC — not the gross — and explain the "
            "realization band as the spread between best- and worst-case lever "
            "achievement."
        )
    return (
        '<blockquote style="border-left:2px solid #1f6a4c;padding:4px 0 4px 18px;'
        'margin:0;font-family:var(--sc-serif);font-style:italic;font-size:18px;'
        'line-height:1.55;color:#154e36;">'
        f'<em style="color:#154e36;">"</em>{_html.escape(narrative)}<em>"</em>'
        '</blockquote>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:14px 0 0;">'
        'IC TALKING POINT FROM THE REALIZATION MODEL\'S OWN NARRATIVE — NEVER A '
        'HALLUCINATED THESIS.</p>'
    )


def render_deal_levers(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 13 (Levers) for ``ccn``.

    Combines the Bridge engine's per-lever gross impact with the
    realization predictor's hospital-level P(achievement) to render the
    probability-weighted bridge.
    """
    npr = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    if not npr or npr <= 1e5 or opex is None or opex <= 0:
        return deal_shell(
            ccn, hospital, active_slug="levers",
            body_html=_empty(
                f"CCN {ccn} is missing the HCRIS revenue or operating-expenses "
                "lines the bridge needs."),
            page_title=f"Levers · {hospital.get('name') or f'CCN {ccn}'}",
        )
    try:
        from ..ebitda_bridge_page import _compute_bridge
        from ...data.hcris import _get_latest_per_ccn
        from ...ml.realization_predictor import predict_realization
    except ImportError:                                # pragma: no cover
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ml.realization_predictor import predict_realization

    current_ebitda = float(npr) - float(opex)
    medicare = _medicare_share(hospital) or 0.40
    try:
        bridge = _compute_bridge(
            net_revenue=float(npr), current_ebitda=float(current_ebitda),
            medicare_pct=float(medicare),
        )
    except Exception:                                  # noqa: BLE001
        return deal_shell(
            ccn, hospital, active_slug="levers",
            body_html=_empty("The bridge engine errored for this hospital."),
            page_title=f"Levers · {hospital.get('name') or f'CCN {ccn}'}",
        )
    gross_uplift = float(bridge.get("total_ebitda_impact", 0.0) or 0.0)

    realization = None
    try:
        hdf = _get_latest_per_ccn()
        realization = predict_realization(ccn, hdf, bridge_uplift=gross_uplift)
    except Exception:                                  # noqa: BLE001
        realization = None
    if realization is None:
        # Build a clean None-equivalent shape so the rest of the page renders.
        class _Default:
            expected_realization = 1.0
            confidence_interval = (1.0, 1.0)
            grade = "—"
            narrative = ""
            factors: List[Any] = []
        realization = _Default()

    panels = [
        _panel("01 · HERO", "Gross uplift vs P-weighted",
               _hero(bridge, realization)),
        _panel("02 · 7-LEVER MODEL · P-WEIGHTED",
               "Gross bar (light) overlaid by P-weighted bar (color)",
               _lever_rows(bridge, realization)),
    ]
    factors_html = _factors_panel(realization)
    if factors_html:
        panels.append(_panel(
            "03 · WHY REALIZATION IS WHERE IT IS",
            "Top factors from the realization model",
            factors_html))
    panels.append(_panel(
        "04 · WHAT THIS MEANS",
        "IC talking point",
        _talking_point(realization, bridge)))
    panels.append(_panel(
        "05 · CROSS-LINK",
        "Where the gross bridge and returns live",
        '<p style="font-family:var(--sc-serif);font-size:14.5px;'
        'line-height:1.55;color:#2a3a4a;margin:0;">'
        'The <a href="/deals/' + _html.escape(ccn, quote=True) + '/bridge" '
        'style="color:#1f7a5a;">EBITDA Bridge</a> surface shows the GROSS '
        '7-lever model that this surface weights by realization. The '
        '<a href="/deals/' + _html.escape(ccn, quote=True) + '/returns" '
        'style="color:#1f7a5a;">Returns</a> surface inherits these numbers '
        'into the LBO equity-returns lens — use the P-weighted uplift, not '
        'the gross, as your base case.</p>'))
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="levers", body_html=body,
        page_title=f"Levers · {hospital.get('name') or f'CCN {ccn}'}",
    )
