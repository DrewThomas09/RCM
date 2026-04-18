"""SeekingChartis Portfolio EBITDA Bridge — aggregate value creation.

Runs the EBITDA bridge for every hospital in the pipeline and
aggregates the results. Shows total uplift, per-deal breakdown,
lever-by-lever attribution, and portfolio-level returns.

This is the managing partner's view: "What's our total value
creation opportunity across the fund?"
"""
from __future__ import annotations

import html as _html
import sqlite3
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ._chartis_kit import chartis_shell
from .brand import PALETTE
from .provenance import source_tag, Source, data_freshness_footer


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


def render_portfolio_bridge(
    hcris_df: pd.DataFrame,
    db_path: str,
) -> str:
    """Render the portfolio-level EBITDA bridge."""
    from ..data.pipeline import list_pipeline, _ensure_tables
    from .ebitda_bridge_page import (
        _compute_bridge, _load_data_room_overrides, compute_peer_targets,
    )

    con = sqlite3.connect(db_path)
    _ensure_tables(con)
    hospitals = list_pipeline(con)
    con.close()

    active = [h for h in hospitals if h.stage not in ("passed",)]

    if not active:
        return chartis_shell(
            '<div class="cad-card">'
            '<h2>No Pipeline Hospitals</h2>'
            '<p style="color:var(--cad-text2);">Add hospitals to the pipeline from the '
            '<a href="/predictive-screener" style="color:var(--cad-link);">Deal Screener</a> '
            'to see the portfolio-level EBITDA bridge.</p></div>',
            "Portfolio Bridge", subtitle="No hospitals in pipeline",
        )

    # Run bridge for each hospital
    deal_results = []
    lever_totals: Dict[str, float] = {}
    total_uplift = 0
    total_revenue = 0
    total_current_ebitda = 0

    for h in active:
        match = hcris_df[hcris_df["ccn"] == h.ccn]
        if match.empty:
            continue

        row = match.iloc[0]
        rev = _safe_float(row.get("net_patient_revenue"))
        opex = _safe_float(row.get("operating_expenses"))
        mc = _safe_float(row.get("medicare_day_pct"), 0.4)
        beds = _safe_float(row.get("beds"), 100)
        state = str(row.get("state", ""))

        if rev < 1e6:
            continue

        ebitda = rev - opex
        if ebitda < -rev:
            ebitda = rev * 0.08

        dr = _load_data_room_overrides(db_path, h.ccn)
        pt = compute_peer_targets(hcris_df, beds, state)
        bridge = _compute_bridge(rev, ebitda, medicare_pct=mc, overrides=dr, peer_targets=pt)

        uplift = bridge["total_ebitda_impact"]
        total_uplift += uplift
        total_revenue += rev
        total_current_ebitda += ebitda

        # Per-lever aggregation
        for lev in bridge["levers"]:
            name = lev["name"]
            lever_totals[name] = lever_totals.get(name, 0) + lev["ebitda_impact"]

        has_seller = len(dr) > 0
        deal_results.append({
            "ccn": h.ccn,
            "name": h.hospital_name,
            "state": h.state,
            "beds": h.beds,
            "stage": h.stage,
            "revenue": rev,
            "current_ebitda": ebitda,
            "current_margin": ebitda / rev if rev > 0 else 0,
            "uplift": uplift,
            "new_ebitda": ebitda + uplift,
            "new_margin": (ebitda + uplift) / rev if rev > 0 else 0,
            "margin_bps": bridge["margin_improvement_bps"],
            "has_seller": has_seller,
            "n_levers": sum(1 for l in bridge["levers"] if l["ebitda_impact"] > 0),
        })

    deal_results.sort(key=lambda d: -d["uplift"])
    n_deals = len(deal_results)
    total_new_ebitda = total_current_ebitda + total_uplift
    avg_margin_improvement = np.mean([d["margin_bps"] for d in deal_results]) if deal_results else 0

    # ── KPIs ──
    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(6,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_deals}</div>'
        f'<div class="cad-kpi-label">Pipeline Deals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fm(total_revenue)}</div>'
        f'<div class="cad-kpi-label">Total Revenue</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fm(total_current_ebitda)}</div>'
        f'<div class="cad-kpi-label">Current EBITDA</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-pos);">'
        f'+{_fm(total_uplift)}</div>'
        f'<div class="cad-kpi-label">Total RCM Uplift</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-pos);">'
        f'{_fm(total_new_ebitda)}</div>'
        f'<div class="cad-kpi-label">Pro Forma EBITDA</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'+{avg_margin_improvement:.0f}bps</div>'
        f'<div class="cad-kpi-label">Avg Margin Lift</div></div>'
        f'</div>'
    )

    # ── Per-deal breakdown ──
    deal_rows = ""
    for d in deal_results:
        ccn = _html.escape(d["ccn"])
        name = _html.escape(d["name"][:25])
        m_color = "var(--cad-pos)" if d["current_margin"] > 0.03 else (
            "var(--cad-warn)" if d["current_margin"] > 0 else "var(--cad-neg)")
        seller_badge = (
            '<span style="background:#e67e22;color:#fff;padding:0 4px;border-radius:2px;'
            'font-size:8px;margin-left:3px;">S</span>' if d["has_seller"] else ""
        )
        stage_color = {
            "screening": "var(--cad-text3)", "outreach": "var(--cad-accent)",
            "loi": "#8b5cf6", "diligence": "var(--cad-warn)",
            "ic": "#e67e22", "closed": "var(--cad-pos)",
        }.get(d["stage"], "var(--cad-text3)")

        deal_rows += (
            f'<tr>'
            f'<td><a href="/ebitda-bridge/{ccn}" '
            f'style="color:var(--cad-link);text-decoration:none;font-weight:500;">'
            f'{name}</a>{seller_badge}</td>'
            f'<td style="font-size:10px;"><span style="color:{stage_color};">'
            f'{_html.escape(d["stage"])}</span></td>'
            f'<td class="num">{_fm(d["revenue"])}</td>'
            f'<td class="num" style="color:{m_color};">{d["current_margin"]:.1%}</td>'
            f'<td class="num" style="color:var(--cad-pos);font-weight:600;">'
            f'+{_fm(d["uplift"])}</td>'
            f'<td class="num">{d["new_margin"]:.1%}</td>'
            f'<td class="num">+{d["margin_bps"]:.0f}bp</td>'
            f'</tr>'
        )

    # Total row
    total_margin = total_current_ebitda / total_revenue if total_revenue > 0 else 0
    new_total_margin = total_new_ebitda / total_revenue if total_revenue > 0 else 0
    deal_rows += (
        f'<tr style="font-weight:700;border-top:2px solid var(--cad-border);">'
        f'<td>Portfolio Total</td><td></td>'
        f'<td class="num">{_fm(total_revenue)}</td>'
        f'<td class="num">{total_margin:.1%}</td>'
        f'<td class="num" style="color:var(--cad-pos);">+{_fm(total_uplift)}</td>'
        f'<td class="num">{new_total_margin:.1%}</td>'
        f'<td class="num">+{avg_margin_improvement:.0f}bp</td>'
        f'</tr>'
    )

    deal_section = (
        f'<div class="cad-card">'
        f'<h2>Per-Deal EBITDA Bridge</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:8px;">'
        f'Each deal\'s bridge computed from HCRIS + Data Room calibrations. '
        f'Click any deal for the full 10-section bridge. '
        f'{source_tag(Source.SELLER)} = has seller data in Data Room.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th><th>Stage</th><th>Revenue</th><th>Margin</th>'
        f'<th>Uplift</th><th>Pro Forma</th><th>Δ Margin</th>'
        f'</tr></thead><tbody>{deal_rows}</tbody></table></div>'
    )

    # ── Lever attribution across portfolio ──
    max_lever = max(lever_totals.values()) if lever_totals else 1
    lever_bars = ""
    for lever_name, total_val in sorted(lever_totals.items(), key=lambda x: -abs(x[1])):
        if total_val == 0:
            continue
        bar_pct = min(100, abs(total_val) / max_lever * 80)
        lever_bars += (
            f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;'
            f'border-bottom:1px solid var(--cad-border);">'
            f'<div style="width:160px;font-size:12px;font-weight:500;">'
            f'{_html.escape(lever_name[:22])}</div>'
            f'<div style="flex:1;background:var(--cad-bg3);border-radius:3px;height:16px;">'
            f'<div style="width:{bar_pct:.0f}%;background:var(--cad-pos);border-radius:3px;'
            f'height:16px;display:flex;align-items:center;justify-content:flex-end;'
            f'padding-right:4px;font-size:10px;color:#fff;font-weight:600;min-width:35px;">'
            f'{_fm(total_val)}</div></div></div>'
        )

    lever_section = (
        f'<div class="cad-card">'
        f'<h2>Portfolio Lever Attribution</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:8px;">'
        f'Total EBITDA uplift by RCM lever, aggregated across {n_deals} pipeline hospitals.</p>'
        f'{lever_bars}'
        f'<div style="display:flex;justify-content:space-between;padding:8px 0;font-weight:700;'
        f'border-top:2px solid var(--cad-border);margin-top:4px;font-size:13px;">'
        f'<span>Total Portfolio Uplift</span>'
        f'<span style="color:var(--cad-pos);">{_fm(total_uplift)}</span></div>'
        f'</div>'
    )

    # ── Portfolio returns (if deployed at 10x across all deals) ──
    # Use only positive-EBITDA deals for meaningful returns
    positive_ebitda = sum(d["current_ebitda"] for d in deal_results if d["current_ebitda"] > 0)
    positive_uplift = sum(d["uplift"] for d in deal_results if d["current_ebitda"] > 0)
    entry_ev = max(positive_ebitda, total_new_ebitda * 0.5) * 10
    leverage = 5.5
    entry_debt = entry_ev * (leverage / (leverage + 1))
    entry_equity = entry_ev - entry_debt
    base_ebitda = max(positive_ebitda, total_new_ebitda * 0.5)
    exit_ebitda = base_ebitda * (1.03 ** 5) + positive_uplift
    for exit_m in (10, 11, 12):
        exit_ev = exit_ebitda * exit_m
        remaining_debt = entry_debt * (0.9 ** 5)
        exit_equity = exit_ev - remaining_debt
        moic = exit_equity / entry_equity if entry_equity > 0 else 0
        try:
            irr = moic ** (1/5) - 1 if moic > 0 else -1
        except (ValueError, OverflowError):
            irr = -1

    returns_section = ""
    if entry_equity > 0:
        ret_rows = ""
        for exit_m in (9.0, 10.0, 11.0, 12.0):
            exit_ev_r = exit_ebitda * exit_m
            rem_debt = entry_debt * (0.9 ** 5)
            exit_eq = exit_ev_r - rem_debt
            moic_r = exit_eq / entry_equity if entry_equity > 0 else 0
            try:
                irr_r = moic_r ** (1/5) - 1 if moic_r > 0 else -1
            except (ValueError, OverflowError):
                irr_r = -1
            irr_color = "var(--cad-pos)" if irr_r >= 0.20 else ("var(--cad-warn)" if irr_r >= 0.15 else "var(--cad-neg)")
            ret_rows += (
                f'<tr>'
                f'<td class="num">{exit_m:.0f}x</td>'
                f'<td class="num">{_fm(exit_ev_r)}</td>'
                f'<td class="num">{_fm(exit_eq)}</td>'
                f'<td class="num" style="font-weight:600;">{moic_r:.2f}x</td>'
                f'<td class="num" style="color:{irr_color};font-weight:600;">{irr_r:.1%}</td>'
                f'</tr>'
            )

        returns_section = (
            f'<div class="cad-card">'
            f'<h2>Portfolio Returns (5-Year, 5.5x Leverage)</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:8px;">'
            f'Assumes all {n_deals} pipeline deals acquired at 10x entry, 3% organic growth, '
            f'10%/yr debt paydown. Entry equity: {_fm(entry_equity)}.</p>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Exit Multiple</th><th>Exit EV</th><th>Exit Equity</th><th>MOIC</th><th>IRR</th>'
            f'</tr></thead><tbody>{ret_rows}</tbody></table></div>'
        )

    # ── Nav ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/pipeline" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Pipeline</a>'
        f'<a href="/portfolio/monitor" class="cad-btn" '
        f'style="text-decoration:none;">Portfolio Monitor</a>'
        f'<a href="/predictive-screener" class="cad-btn" '
        f'style="text-decoration:none;">Deal Screener</a>'
        f'</div>'
    )

    freshness = data_freshness_footer(
        hcris_year=2022, n_hospitals=len(hcris_df),
        has_seller_data=any(d["has_seller"] for d in deal_results),
        n_seller_metrics=sum(1 for d in deal_results if d["has_seller"]),
    )

    body = (
        f'{kpis}'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        f'<div>{deal_section}</div>'
        f'<div>{lever_section}{returns_section}</div></div>'
        f'{nav}{freshness}'
    )

    return chartis_shell(
        body, "Portfolio EBITDA Bridge",
        active_nav="/pipeline",
        subtitle=(
            f"{n_deals} deals | {_fm(total_revenue)} revenue | "
            f"+{_fm(total_uplift)} uplift | "
            f"{total_margin:.1%} → {new_total_margin:.1%} margin"
        ),
    )
