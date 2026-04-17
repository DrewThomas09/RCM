"""SeekingChartis Scenario Modeler — adjust assumptions, see returns impact.

Partners can create named scenarios by adjusting RCM levers, payer mix,
volume, and macro assumptions. Each scenario flows through the EBITDA bridge
and returns engine. Save and compare up to 4 scenarios side-by-side.

Preset scenarios:
- Base Case (ML-predicted targets)
- Conservative (50% of base improvement)
- Aggressive (130% improvement + multiple expansion)
- Downside (rate cut + denial spike)
- Payer Renegotiation (commercial rate uplift)
- Bed Expansion (+50 beds, 18mo ramp)
- Merger Synergy (shared RCM platform)
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs

import numpy as np
import pandas as pd

from .shell_v2 import shell_v2
from .brand import PALETTE
from .ebitda_bridge_page import _compute_bridge, _compute_returns_grid, _fm, _safe_float, _load_data_room_overrides


_PRESET_SCENARIOS = [
    {
        "id": "base",
        "name": "Base Case",
        "description": "ML-predicted targets at P75 peers, 60% gap closure",
        "overrides": {},
        "entry_multiple": 10.0,
        "exit_multiple": 11.0,
        "uplift_factor": 1.0,
        "organic_growth": 0.03,
        "revenue_adj": 1.0,
        "beds_delta": 0,
    },
    {
        "id": "conservative",
        "name": "Conservative",
        "description": "50% of base improvement, flat multiple",
        "overrides": {},
        "entry_multiple": 10.0,
        "exit_multiple": 10.0,
        "uplift_factor": 0.5,
        "organic_growth": 0.02,
        "revenue_adj": 1.0,
        "beds_delta": 0,
    },
    {
        "id": "aggressive",
        "name": "Aggressive",
        "description": "130% improvement, 1x multiple expansion, 4% growth",
        "overrides": {},
        "entry_multiple": 10.0,
        "exit_multiple": 12.0,
        "uplift_factor": 1.3,
        "organic_growth": 0.04,
        "revenue_adj": 1.0,
        "beds_delta": 0,
    },
    {
        "id": "downside",
        "name": "Downside",
        "description": "Medicare rate cut + denial rate spike + margin compression",
        "overrides": {
            "denial_rate_current": 0.15,
            "denial_rate_target": 0.10,
        },
        "entry_multiple": 10.0,
        "exit_multiple": 9.0,
        "uplift_factor": 0.4,
        "organic_growth": 0.01,
        "revenue_adj": 0.95,
        "beds_delta": 0,
    },
    {
        "id": "payer_renego",
        "name": "Payer Renegotiation",
        "description": "Commercial rate uplift +8% from contract renegotiation",
        "overrides": {
            "net_collection_rate_current": 0.92,
            "net_collection_rate_target": 0.975,
        },
        "entry_multiple": 10.0,
        "exit_multiple": 11.0,
        "uplift_factor": 1.15,
        "organic_growth": 0.03,
        "revenue_adj": 1.08,
        "beds_delta": 0,
    },
    {
        "id": "bed_expansion",
        "name": "Bed Expansion (+50)",
        "description": "Add 50 beds over 18 months, proportional revenue growth",
        "overrides": {},
        "entry_multiple": 10.0,
        "exit_multiple": 11.5,
        "uplift_factor": 1.0,
        "organic_growth": 0.05,
        "revenue_adj": 1.15,
        "beds_delta": 50,
    },
    {
        "id": "merger_synergy",
        "name": "Merger Synergy",
        "description": "Shared RCM platform across 2 facilities, 25% cost reduction",
        "overrides": {
            "cost_to_collect_current": 0.045,
            "cost_to_collect_target": 0.018,
            "clean_claim_rate_current": 0.86,
            "clean_claim_rate_target": 0.97,
        },
        "entry_multiple": 11.0,
        "exit_multiple": 12.0,
        "uplift_factor": 1.2,
        "organic_growth": 0.03,
        "revenue_adj": 1.0,
        "beds_delta": 0,
    },
    {
        "id": "medicare_cut",
        "name": "Medicare Rate Cut (-3%)",
        "description": "Medicare reimbursement reduced 3%, partial offset from volume",
        "overrides": {},
        "entry_multiple": 10.0,
        "exit_multiple": 9.5,
        "uplift_factor": 0.7,
        "organic_growth": 0.01,
        "revenue_adj": 0.97,
        "beds_delta": 0,
    },
]


def _run_scenario(
    scenario: Dict[str, Any],
    base_revenue: float,
    base_ebitda: float,
    mc_pct: float,
) -> Dict[str, Any]:
    """Run a single scenario through bridge + returns."""
    adj_revenue = base_revenue * scenario.get("revenue_adj", 1.0)

    bridge = _compute_bridge(
        adj_revenue, base_ebitda,
        medicare_pct=mc_pct,
        overrides=scenario.get("overrides", {}),
    )

    uplift_factor = scenario.get("uplift_factor", 1.0)
    adj_uplift = bridge["total_ebitda_impact"] * uplift_factor

    entry_m = scenario.get("entry_multiple", 10.0)
    exit_m = scenario.get("exit_multiple", 11.0)
    organic = scenario.get("organic_growth", 0.03)

    grid = _compute_returns_grid(
        base_ebitda, adj_uplift,
        [entry_m], [exit_m],
        hold_years=5, organic_growth=organic,
    )

    cell = grid[0] if grid else {}

    return {
        "scenario": scenario,
        "bridge": bridge,
        "adj_uplift": adj_uplift,
        "adj_revenue": adj_revenue,
        "new_ebitda": base_ebitda + adj_uplift,
        "new_margin": (base_ebitda + adj_uplift) / adj_revenue if adj_revenue > 0 else 0,
        "entry_ev": cell.get("entry_ev", 0),
        "entry_equity": cell.get("entry_equity", 0),
        "exit_ev": cell.get("exit_ev", 0),
        "exit_equity": cell.get("exit_equity", 0),
        "moic": cell.get("moic", 0),
        "irr": cell.get("irr", 0),
        "underwater": cell.get("underwater", False),
    }


def render_scenario_modeler(
    ccn: str,
    hcris_df: pd.DataFrame,
    query_string: str = "",
    db_path: Optional[str] = None,
) -> str:
    """Render the scenario modeler page for a hospital."""
    qs = parse_qs(query_string)
    selected_ids = (qs.get("scenarios") or ["base,conservative,aggressive,downside"])[0].split(",")

    match = hcris_df[hcris_df["ccn"] == ccn]
    if match.empty:
        return shell_v2(
            f'<div class="cad-card"><p>Hospital {_html.escape(ccn)} not found.</p></div>',
            "Scenario Modeler",
        )

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    state = str(hospital.get("state", ""))
    beds = _safe_float(hospital.get("beds"))
    rev = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    mc_pct = _safe_float(hospital.get("medicare_day_pct"), 0.4)
    ebitda = rev - opex

    if rev < 1e6:
        return shell_v2(
            f'<div class="cad-card"><p>Insufficient data for {_html.escape(name)}.</p></div>',
            "Scenario Modeler",
        )

    current_margin = ebitda / rev if rev > 0 else 0

    # Run selected scenarios
    selected = [s for s in _PRESET_SCENARIOS if s["id"] in selected_ids]
    if not selected:
        selected = _PRESET_SCENARIOS[:4]

    # Load Data Room calibrations as base overrides for all scenarios
    dr_overrides = _load_data_room_overrides(db_path, ccn) if db_path else {}

    results = []
    for sc in selected:
        # Merge Data Room overrides with scenario-specific overrides
        merged_overrides = {**dr_overrides, **sc.get("overrides", {})}
        merged_sc = {**sc, "overrides": merged_overrides}
        results.append(_run_scenario(merged_sc, rev, ebitda, mc_pct))

    # ── Scenario selector ──
    selector_opts = ""
    for sc in _PRESET_SCENARIOS:
        checked = "checked" if sc["id"] in selected_ids else ""
        selector_opts += (
            f'<label style="display:flex;align-items:center;gap:6px;font-size:12px;'
            f'padding:4px 0;cursor:pointer;">'
            f'<input type="checkbox" name="s" value="{sc["id"]}" {checked}> '
            f'{_html.escape(sc["name"])}'
            f'<span style="color:var(--cad-text3);font-size:10px;">— {_html.escape(sc["description"][:50])}</span>'
            f'</label>'
        )

    selector = (
        f'<div class="cad-card">'
        f'<form method="GET" action="/scenarios/{_html.escape(ccn)}" '
        f'style="display:flex;gap:16px;align-items:flex-start;">'
        f'<div style="flex:1;">'
        f'<h2 style="font-size:13px;margin-bottom:6px;">Select Scenarios</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px;">'
        f'{selector_opts}</div></div>'
        f'<div style="align-self:flex-end;">'
        f'<button type="submit" class="cad-btn cad-btn-primary" '
        f'onclick="var cs=this.form.querySelectorAll(\'input[name=s]:checked\');'
        f'var v=Array.from(cs).map(function(c){{return c.value;}}).join(\',\');'
        f'this.form.action=\'/scenarios/{_html.escape(ccn)}?scenarios=\'+v;'
        f'return true;">Compare</button>'
        f'</div></form></div>'
    )

    # ── Baseline KPIs ──
    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(5,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fm(rev)}</div>'
        f'<div class="cad-kpi-label">Net Revenue</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fm(ebitda)}</div>'
        f'<div class="cad-kpi-label">Current EBITDA</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{current_margin:.1%}</div>'
        f'<div class="cad-kpi-label">Current Margin</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{beds:.0f}</div>'
        f'<div class="cad-kpi-label">Beds</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{mc_pct:.0%}</div>'
        f'<div class="cad-kpi-label">Medicare %</div></div>'
        f'</div>'
    )

    # ── Side-by-side comparison table ──
    n = len(results)
    cols = f'grid-template-columns:180px repeat({n},1fr);'

    def _row(label: str, values: list, fmt_fn=_fm, bold: bool = False) -> str:
        weight = "font-weight:600;" if bold else ""
        cells = "".join(f'<td class="num" style="{weight}">{fmt_fn(v)}</td>' for v in values)
        return f'<tr><td style="color:var(--cad-text3);{weight}">{_html.escape(label)}</td>{cells}</tr>'

    def _color_row(label: str, values: list, fmt_fn=_fm, good_fn=None) -> str:
        cells = ""
        for v in values:
            color = ""
            if good_fn:
                color = f'color:{"var(--cad-pos)" if good_fn(v) else "var(--cad-neg)"};'
            cells += f'<td class="num" style="{color}font-weight:600;">{fmt_fn(v)}</td>'
        return f'<tr><td style="color:var(--cad-text3);">{_html.escape(label)}</td>{cells}</tr>'

    header = '<th></th>' + ''.join(
        f'<th style="font-size:12px;">{_html.escape(r["scenario"]["name"])}</th>' for r in results)

    pct = lambda v: f"{v:.1%}"
    moic_fmt = lambda v: f"{v:.2f}x"

    comparison = (
        f'<div class="cad-card">'
        f'<h2>Scenario Comparison</h2>'
        f'<table class="cad-table"><thead><tr>{header}</tr></thead><tbody>'
        + _row("Adj. Revenue", [r["adj_revenue"] for r in results])
        + _row("EBITDA Uplift", [r["adj_uplift"] for r in results])
        + _row("Pro Forma EBITDA", [r["new_ebitda"] for r in results], bold=True)
        + _color_row("Pro Forma Margin", [r["new_margin"] for r in results],
                      fmt_fn=pct, good_fn=lambda v: v > current_margin)
        + '<tr><td colspan="99" style="border-top:2px solid var(--cad-border);"></td></tr>'
        + _row("Entry Multiple", [r["scenario"]["entry_multiple"] for r in results],
               fmt_fn=lambda v: f"{v:.1f}x")
        + _row("Exit Multiple", [r["scenario"]["exit_multiple"] for r in results],
               fmt_fn=lambda v: f"{v:.1f}x")
        + _row("Entry EV", [r["entry_ev"] for r in results])
        + _row("Entry Equity", [r["entry_equity"] for r in results])
        + _row("Exit EV", [r["exit_ev"] for r in results])
        + _row("Exit Equity", [r["exit_equity"] for r in results])
        + _color_row("MOIC", [r["moic"] for r in results],
                      fmt_fn=moic_fmt, good_fn=lambda v: v >= 2.0)
        + _color_row("IRR", [r["irr"] for r in results],
                      fmt_fn=pct, good_fn=lambda v: v >= 0.20)
        + f'</tbody></table></div>'
    )

    # ── Per-scenario EBITDA bridge breakdown ──
    bridge_panels = ""
    for r in results:
        sc = r["scenario"]
        b = r["bridge"]
        lever_rows = ""
        for lev in b["levers"]:
            if lev["ebitda_impact"] == 0:
                continue
            adj_impact = lev["ebitda_impact"] * sc.get("uplift_factor", 1.0)
            lever_rows += (
                f'<tr>'
                f'<td style="font-size:11px;">{_html.escape(lev["name"][:20])}</td>'
                f'<td class="num" style="font-size:11px;color:var(--cad-pos);">{_fm(adj_impact)}</td>'
                f'</tr>'
            )

        irr = r["irr"]
        irr_color = "var(--cad-pos)" if irr >= 0.20 else ("var(--cad-warn)" if irr >= 0.15 else "var(--cad-neg)")

        bridge_panels += (
            f'<div class="cad-card" style="padding:12px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
            f'<h3 style="font-size:12px;margin:0;">{_html.escape(sc["name"])}</h3>'
            f'<div style="text-align:right;">'
            f'<span style="font-size:16px;font-weight:700;color:{irr_color};'
            f'font-family:var(--cad-mono);">{irr:.0%}</span>'
            f'<span style="font-size:10px;color:var(--cad-text3);margin-left:4px;">IRR</span>'
            f'</div></div>'
            f'<p style="font-size:10px;color:var(--cad-text3);margin-bottom:6px;">'
            f'{_html.escape(sc["description"])}</p>'
            f'<table class="cad-table" style="font-size:11px;">'
            f'{lever_rows}'
            f'<tr style="border-top:1px solid var(--cad-border);font-weight:600;">'
            f'<td>Total Uplift</td>'
            f'<td class="num" style="color:var(--cad-pos);">{_fm(r["adj_uplift"])}</td>'
            f'</tr></table></div>'
        )

    bridge_section = (
        f'<div class="cad-card">'
        f'<h2>Per-Scenario EBITDA Bridge</h2>'
        f'<div style="display:grid;grid-template-columns:repeat({min(n, 4)},1fr);gap:8px;">'
        f'{bridge_panels}</div></div>'
    )

    # ── Timing comparison ──
    months = [0, 6, 12, 18, 24, 36]
    timing_header = '<th>Month</th>' + ''.join(
        f'<th style="font-size:11px;">{_html.escape(r["scenario"]["name"][:15])}</th>' for r in results)
    timing_rows = ""
    for m in months:
        timing_rows += f'<tr><td class="num">M{m}</td>'
        for r in results:
            cumulative = 0
            for lev in r["bridge"]["levers"]:
                ramp = lev["ramp_months"]
                pct = min(1.0, m / ramp) if ramp > 0 else 1.0
                cumulative += lev["ebitda_impact"] * pct * r["scenario"].get("uplift_factor", 1.0)
            color = "var(--cad-pos)" if cumulative > 0 else "var(--cad-text3)"
            timing_rows += f'<td class="num" style="color:{color};font-size:11px;">{_fm(cumulative)}</td>'
        timing_rows += '</tr>'

    timing_section = (
        f'<div class="cad-card">'
        f'<h2>Implementation Timing Comparison</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:8px;">'
        f'Cumulative EBITDA uplift at each milestone across scenarios.</p>'
        f'<table class="cad-table"><thead><tr>{timing_header}'
        f'</tr></thead><tbody>{timing_rows}</tbody></table></div>'
    )

    # ── Nav ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/ebitda-bridge/{_html.escape(ccn)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full EBITDA Bridge</a>'
        f'<a href="/ic-memo/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">IC Memo</a>'
        f'<a href="/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">Hospital Profile</a>'
        f'<a href="/ml-insights/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">ML Analysis</a>'
        f'<a href="/predictive-screener" class="cad-btn" '
        f'style="text-decoration:none;">Deal Screener</a>'
        f'</div>'
    )

    body = f'{selector}{kpis}{comparison}{bridge_section}{timing_section}{nav}'

    best = max(results, key=lambda r: r["irr"])
    return shell_v2(
        body,
        f"Scenario Modeler — {_html.escape(name)}",
        subtitle=(
            f"CCN {_html.escape(ccn)} | {len(results)} scenarios | "
            f"Best: {best['scenario']['name']} ({best['irr']:.0%} IRR, {best['moic']:.1f}x MOIC)"
        ),
    )
