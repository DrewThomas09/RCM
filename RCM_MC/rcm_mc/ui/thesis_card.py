"""SeekingChartis Investment Thesis Card — 30-second deal answer.

Synthesizes all ML models into a single card that answers:
"Should I pursue this hospital?" Shows investability grade,
EBITDA uplift headline, margin prediction, turnaround probability,
top 3 risks, and top 3 catalysts. Designed to embed directly in
the hospital profile page.

This is the 30-second answer that replaces clicking through 5 pages.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        f = float(val)
        return default if f != f else f
    except (TypeError, ValueError):
        return default


def render_thesis_card(
    ccn: str,
    hcris_df: pd.DataFrame,
    db_path: Optional[str] = None,
) -> str:
    """Render the investment thesis synthesis card.

    Returns HTML string to embed in the hospital profile page.
    Runs all ML models and synthesizes results.
    """
    match = hcris_df[hcris_df["ccn"] == ccn]
    if match.empty:
        return ""

    hospital = match.iloc[0]
    name = str(hospital.get("name", ""))
    state = str(hospital.get("state", ""))
    beds = _safe_float(hospital.get("beds"))
    rev = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    mc = _safe_float(hospital.get("medicare_day_pct"))
    margin = _safe_float(hospital.get("operating_margin"))

    if rev < 1e6:
        return ""

    # Run models (with fallbacks)
    invest_score = 0
    invest_grade = "—"
    invest_rec = ""
    try:
        from ..ml.investability_scorer import compute_investability
        inv = compute_investability(ccn, hcris_df)
        if inv:
            invest_score = inv.total_score
            invest_grade = inv.grade
            invest_rec = inv.recommendation
    except Exception:
        pass

    ebitda_uplift = 0
    margin_improvement = 0
    try:
        from .ebitda_bridge_page import _compute_bridge, _load_data_room_overrides, compute_peer_targets
        dr = _load_data_room_overrides(db_path, ccn) if db_path else {}
        pt = compute_peer_targets(hcris_df, beds, state)
        ebitda = rev - opex
        if ebitda < -rev:
            ebitda = rev * 0.08
        bridge = _compute_bridge(rev, ebitda, medicare_pct=mc or 0.4, overrides=dr, peer_targets=pt)
        ebitda_uplift = bridge.get("total_ebitda_impact", 0)
        margin_improvement = bridge.get("margin_improvement_bps", 0)
    except Exception:
        pass

    margin_pred = None
    turnaround_prob = None
    turnaround_expl = ""
    try:
        from ..ml.margin_predictor import predict_margin
        mp = predict_margin(ccn, hcris_df)
        if mp:
            margin_pred = mp.predicted_margin
            turnaround_prob = mp.turnaround_probability
            turnaround_expl = mp.turnaround_explanation
    except Exception:
        pass

    distress_prob = None
    try:
        from ..ml.distress_predictor import predict_distress
        dp = predict_distress(ccn, hcris_df)
        if dp:
            distress_prob = dp.distress_probability
    except Exception:
        pass

    # Has seller data?
    has_seller = len(_load_data_room_overrides(db_path, ccn)) > 0 if db_path else False

    # Synthesize thesis
    signals = []
    risks = []
    catalysts = []

    # Grade color
    grade_colors = {"A": "var(--cad-pos)", "B": "var(--cad-accent)", "C": "var(--cad-warn)",
                    "D": "var(--cad-neg)", "F": "var(--cad-neg)"}
    gc = grade_colors.get(invest_grade, "var(--cad-text3)")

    # Thesis headline
    if invest_grade in ("A", "B"):
        thesis_type = "Buy"
        thesis_color = "var(--cad-pos)"
    elif invest_grade == "C":
        thesis_type = "Selective"
        thesis_color = "var(--cad-warn)"
    else:
        thesis_type = "Pass"
        thesis_color = "var(--cad-neg)"

    if ebitda_uplift > 5e6:
        catalysts.append(f"RCM uplift of {_fm(ebitda_uplift)} (+{margin_improvement:.0f}bps)")
    if margin > 0.08:
        catalysts.append(f"Strong operating margin ({margin:.1%})")
    elif margin < 0 and turnaround_prob and turnaround_prob > 0.4:
        catalysts.append(f"Turnaround candidate ({turnaround_prob:.0%} probability)")
    if _safe_float(hospital.get("commercial_pct")) > 0.4:
        catalysts.append(f"Strong commercial payer mix ({_safe_float(hospital.get('commercial_pct')):.0%})")
    if _safe_float(hospital.get("occupancy_rate")) > 0.65:
        catalysts.append("High occupancy supports revenue stability")
    if beds > 200:
        catalysts.append("Platform-sized facility")

    if margin < 0:
        risks.append(f"Negative margin ({margin:.1%})")
    if mc and mc > 0.55:
        risks.append(f"High Medicare dependence ({mc:.0%})")
    if distress_prob and distress_prob > 0.4:
        risks.append(f"Elevated distress risk ({distress_prob:.0%})")
    if _safe_float(hospital.get("medicaid_day_pct")) > 0.22:
        risks.append(f"High Medicaid exposure ({_safe_float(hospital.get('medicaid_day_pct')):.0%})")
    if beds < 75:
        risks.append("Small facility — limited scale economies")

    # Build the card
    risk_html = ""
    if risks:
        risk_items = "".join(
            f'<div style="display:flex;gap:6px;padding:2px 0;font-size:11.5px;">'
            f'<span style="color:var(--cad-neg);">&#9660;</span>'
            f'<span style="color:var(--cad-text2);">{_html.escape(r)}</span></div>'
            for r in risks[:3]
        )
        risk_html = f'<div>{risk_items}</div>'

    catalyst_html = ""
    if catalysts:
        cat_items = "".join(
            f'<div style="display:flex;gap:6px;padding:2px 0;font-size:11.5px;">'
            f'<span style="color:var(--cad-pos);">&#9650;</span>'
            f'<span style="color:var(--cad-text2);">{_html.escape(c)}</span></div>'
            for c in catalysts[:3]
        )
        catalyst_html = f'<div>{cat_items}</div>'

    # Seller data indicator
    seller_badge = ""
    if has_seller:
        seller_badge = (
            '<span style="background:#e67e22;color:#fff;padding:1px 6px;border-radius:2px;'
            'font-size:9px;font-weight:600;margin-left:6px;">SELLER DATA</span>'
        )

    # Realization estimate
    realization_pct = None
    realization_grade = ""
    try:
        from ..ml.realization_predictor import predict_realization
        rp = predict_realization(ccn, hcris_df, bridge_uplift=ebitda_uplift)
        if rp:
            realization_pct = rp.expected_realization
            realization_grade = rp.grade
    except Exception:
        pass

    # Margin prediction details
    margin_ci = None
    margin_pctile = None
    try:
        from ..ml.margin_predictor import predict_margin as _pm
        mp_full = _pm(ccn, hcris_df)
        if mp_full:
            margin_ci = (mp_full.ci_low, mp_full.ci_high)
            margin_pctile = mp_full.peer_percentile
    except Exception:
        pass

    uplift_str = f"+{_fm(ebitda_uplift)}" if ebitda_uplift > 0 else "—"
    margin_str = f"+{margin_improvement:.0f}bps" if margin_improvement > 0 else "—"

    # ── Signal bars (mini analytical justification) ──
    def _signal_bar(label: str, value: float, max_val: float, color: str, detail: str) -> str:
        pct = min(100, max(2, value / max_val * 100)) if max_val > 0 else 50
        return (
            f'<div style="display:flex;align-items:center;gap:6px;padding:2px 0;">'
            f'<span style="width:80px;font-size:10px;color:var(--cad-text3);">{_html.escape(label)}</span>'
            f'<div style="flex:1;background:var(--cad-bg3);border-radius:2px;height:6px;">'
            f'<div style="width:{pct:.0f}%;background:{color};border-radius:2px;height:6px;"></div></div>'
            f'<span style="font-size:10px;color:{color};font-weight:600;width:40px;text-align:right;">'
            f'{_html.escape(detail)}</span></div>'
        )

    signal_bars = ""
    # Financial health bar
    fin_score = min(100, max(0, (margin + 0.1) / 0.25 * 100))
    fin_color = "var(--cad-pos)" if margin > 0.03 else ("var(--cad-warn)" if margin > 0 else "var(--cad-neg)")
    signal_bars += _signal_bar("Margin", fin_score, 100, fin_color, f"{margin:.1%}")

    # Realization bar
    if realization_pct is not None:
        r_color = "var(--cad-pos)" if realization_pct >= 0.80 else ("var(--cad-warn)" if realization_pct >= 0.60 else "var(--cad-neg)")
        signal_bars += _signal_bar("Realization", realization_pct * 100, 100, r_color, f"{realization_pct:.0%}")

    # Distress bar (inverted: low distress = good)
    if distress_prob is not None:
        safety = 1 - distress_prob
        d_color = "var(--cad-pos)" if safety > 0.7 else ("var(--cad-warn)" if safety > 0.4 else "var(--cad-neg)")
        signal_bars += _signal_bar("Safety", safety * 100, 100, d_color, f"{safety:.0%}")

    # Occupancy bar
    occ = _safe_float(hospital.get("occupancy_rate"))
    if occ > 0:
        o_color = "var(--cad-pos)" if occ > 0.6 else ("var(--cad-warn)" if occ > 0.4 else "var(--cad-neg)")
        signal_bars += _signal_bar("Occupancy", occ * 100, 100, o_color, f"{occ:.0%}")

    # Peer percentile bar
    if margin_pctile is not None:
        p_color = "var(--cad-pos)" if margin_pctile > 60 else ("var(--cad-neg)" if margin_pctile < 40 else "var(--cad-text2)")
        signal_bars += _signal_bar("Peer Rank", margin_pctile, 100, p_color, f"P{margin_pctile:.0f}")

    # ── Deep dive links ──
    links = (
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">'
        f'<a href="/competitive-intel/{_html.escape(ccn)}" style="font-size:10px;color:var(--cad-link);'
        f'text-decoration:none;padding:2px 6px;border:1px solid var(--cad-border);border-radius:3px;">'
        f'Peer Analysis</a>'
        f'<a href="/ebitda-bridge/{_html.escape(ccn)}" style="font-size:10px;color:var(--cad-link);'
        f'text-decoration:none;padding:2px 6px;border:1px solid var(--cad-border);border-radius:3px;">'
        f'EBITDA Bridge</a>'
        f'<a href="/data-room/{_html.escape(ccn)}" style="font-size:10px;color:var(--cad-link);'
        f'text-decoration:none;padding:2px 6px;border:1px solid var(--cad-border);border-radius:3px;">'
        f'Data Room</a>'
        f'<a href="/ic-memo/{_html.escape(ccn)}" style="font-size:10px;color:var(--cad-link);'
        f'text-decoration:none;padding:2px 6px;border:1px solid var(--cad-border);border-radius:3px;">'
        f'IC Memo</a>'
        f'<a href="/ml-insights/hospital/{_html.escape(ccn)}" style="font-size:10px;color:var(--cad-link);'
        f'text-decoration:none;padding:2px 6px;border:1px solid var(--cad-border);border-radius:3px;">'
        f'ML Detail</a>'
        f'</div>'
    )

    # ── Build the card ──
    return (
        f'<div class="cad-card" style="border-left:4px solid {thesis_color};padding:16px 20px;">'

        # Row 1: Header + Score
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">'
        f'<div>'
        f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:var(--cad-text3);font-weight:600;">INVESTMENT THESIS{seller_badge}</div>'
        f'<div style="font-size:18px;font-weight:700;color:{thesis_color};margin-top:2px;">'
        f'{thesis_type}: {_html.escape(name[:35])}</div></div>'
        f'<div style="text-align:center;">'
        f'<div style="font-size:28px;font-weight:700;color:{gc};font-family:var(--cad-mono);">'
        f'{invest_score:.0f}</div>'
        f'<div style="font-size:9px;color:var(--cad-text3);">/ 100 ({invest_grade})</div>'
        f'</div></div>'

        # Row 2: Key metrics (6 columns now)
        f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;'
        f'margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--cad-border);">'
        f'<div><div style="font-size:14px;font-weight:700;color:var(--cad-pos);">{uplift_str}</div>'
        f'<div style="font-size:9px;color:var(--cad-text3);">EBITDA Uplift</div></div>'
        f'<div><div style="font-size:14px;font-weight:700;">{margin_str}</div>'
        f'<div style="font-size:9px;color:var(--cad-text3);">Margin Δ</div></div>'
        f'<div><div style="font-size:14px;font-weight:700;'
        f'color:{"var(--cad-pos)" if margin > 0 else "var(--cad-neg)"};">{margin:.1%}</div>'
        f'<div style="font-size:9px;color:var(--cad-text3);">Op Margin</div></div>'
        f'<div><div style="font-size:14px;font-weight:700;">{_fm(rev)}</div>'
        f'<div style="font-size:9px;color:var(--cad-text3);">Revenue</div></div>'
        + (f'<div><div style="font-size:14px;font-weight:700;color:{r_color};">{realization_pct:.0%}</div>'
           f'<div style="font-size:9px;color:var(--cad-text3);">Realization</div></div>'
           if realization_pct else
           f'<div><div style="font-size:14px;font-weight:700;">—</div>'
           f'<div style="font-size:9px;color:var(--cad-text3);">Realization</div></div>') +
        (f'<div><div style="font-size:14px;font-weight:700;">P{margin_pctile:.0f}</div>'
         f'<div style="font-size:9px;color:var(--cad-text3);">Peer Rank</div></div>'
         if margin_pctile else
         f'<div><div style="font-size:14px;font-weight:700;">—</div>'
         f'<div style="font-size:9px;color:var(--cad-text3);">Peer Rank</div></div>') +
        f'</div>'

        # Row 3: Signal bars + Catalysts/Risks (side by side)
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">'
        f'<div>'
        f'<div style="font-size:9px;color:var(--cad-text3);font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">SIGNAL STRENGTH</div>'
        f'{signal_bars}</div>'
        f'<div>'
        f'<div style="font-size:9px;color:var(--cad-text3);font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">CATALYSTS</div>'
        f'{catalyst_html}</div>'
        f'<div>'
        f'<div style="font-size:9px;color:var(--cad-text3);font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:3px;">RISKS</div>'
        f'{risk_html}</div>'
        f'</div>'

        # Row 4: Recommendation + Links
        f'<div style="margin-top:8px;padding:6px 10px;background:var(--cad-bg3);'
        f'border-radius:4px;font-size:11.5px;color:var(--cad-text2);line-height:1.5;">'
        f'{_html.escape(invest_rec[:180])}</div>'
        f'{links}'
        f'</div>'
    )
