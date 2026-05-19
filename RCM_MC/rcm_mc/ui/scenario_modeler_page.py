"""PE Desk Scenario Modeler — adjust assumptions, see returns impact.

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

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro,
)
from .brand import PALETTE
from .ebitda_bridge_page import _compute_bridge, _compute_returns_grid, _fm, _safe_float, _load_data_room_overrides


_SM_CHART_CAPTION_CSS = """
<style>
.sm-chart-caption {
  font-family: "Inter Tight","Inter",sans-serif;
  font-size: .72rem; color: #5C6878;
  text-align: center; letter-spacing: 0.06em;
  text-transform: uppercase; margin: -.5rem 0 1.25rem;
}
@media print {
  .sm-chart-caption { color: #1a2332; }
  svg { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
"""

_SM_LINE_PALETTE = ["#155752", "#b8732a", "#1F7A75", "#A53A2D",
                    "#3F7D4D", "#8A92A0", "#0b2341"]


def _scenario_timing_chart(results: List[Dict[str, Any]],
                           months: List[int],
                           width: int = 720, height: int = 250) -> str:
    """Multi-line cumulative-uplift curves, one line per scenario.

    Each scenario's cumulative EBITDA uplift is plotted across the
    milestone months; the legend ties color → scenario name.
    """
    if not results or not months:
        return ""
    series: List[Dict[str, Any]] = []
    all_vals: List[float] = []
    for i, r in enumerate(results):
        pts: List[tuple] = []
        for m in months:
            cumulative = 0.0
            for lev in r["bridge"]["levers"]:
                ramp = lev["ramp_months"]
                frac = min(1.0, m / ramp) if ramp > 0 else 1.0
                cumulative += (
                    lev["ebitda_impact"] * frac
                    * r["scenario"].get("uplift_factor", 1.0)
                )
            pts.append((m, cumulative))
            all_vals.append(cumulative)
        series.append({
            "name": r["scenario"]["name"],
            "points": pts,
            "color": _SM_LINE_PALETTE[i % len(_SM_LINE_PALETTE)],
        })
    max_v = max(all_vals) if all_vals else 0
    if max_v <= 0:
        return ""

    pad_l, pad_r, pad_t, pad_b = 56, 150, 24, 36
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    m_lo, m_hi = months[0], months[-1]
    m_span = max(1, m_hi - m_lo)

    def _x(m: int) -> float:
        return pad_l + (m - m_lo) / m_span * plot_w

    def _y(v: float) -> float:
        return pad_t + plot_h - (v / max_v) * plot_h

    grid_svg = ""
    for i in range(5):
        gv = max_v * i / 4
        gy = _y(gv)
        grid_svg += (
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l + plot_w}" '
            f'y2="{gy:.1f}" stroke="#E8E0D0" stroke-width="0.8"/>'
            f'<text x="{pad_l - 6}" y="{gy + 3:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#8A92A0" text-anchor="end">{_fm(gv)}</text>'
        )

    tick_svg = ""
    for m in months:
        tx = _x(m)
        tick_svg += (
            f'<line x1="{tx:.1f}" y1="{pad_t + plot_h}" x2="{tx:.1f}" '
            f'y2="{pad_t + plot_h + 4}" stroke="#BFB6A2" stroke-width="0.8"/>'
            f'<text x="{tx:.1f}" y="{pad_t + plot_h + 16}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#5C6878" text-anchor="middle">M{m}</text>'
        )

    lines_svg = ""
    legend_svg = ""
    legend_x = pad_l + plot_w + 14
    for i, s in enumerate(series):
        path = " ".join(
            f"{'M' if j == 0 else 'L'} {_x(m):.1f},{_y(v):.1f}"
            for j, (m, v) in enumerate(s["points"])
        )
        lines_svg += (
            f'<path d="{path}" stroke="{s["color"]}" stroke-width="2" '
            f'fill="none"/>'
        )
        for m, v in s["points"]:
            lines_svg += (
                f'<circle cx="{_x(m):.1f}" cy="{_y(v):.1f}" r="2.4" '
                f'fill="{s["color"]}"/>'
            )
        ly = pad_t + 10 + i * 16
        nm = s["name"]
        if len(nm) > 18:
            nm = nm[:17] + "…"
        legend_svg += (
            f'<line x1="{legend_x}" y1="{ly}" x2="{legend_x + 16}" '
            f'y2="{ly}" stroke="{s["color"]}" stroke-width="2.4"/>'
            f'<circle cx="{legend_x + 8}" cy="{ly}" r="2.4" fill="{s["color"]}"/>'
            f'<text x="{legend_x + 22}" y="{ly + 3}" '
            f'font-family="Inter Tight,sans-serif" font-size="9.5" '
            f'fill="#1a2332">{_html.escape(nm)}</text>'
        )

    axes_svg = (
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{pad_l + plot_w}" '
        f'y2="{pad_t + plot_h}" stroke="#BFB6A2" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" '
        f'y2="{pad_t + plot_h}" stroke="#BFB6A2" stroke-width="1"/>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{grid_svg}{axes_svg}{tick_svg}{lines_svg}{legend_svg}</svg>'
    )


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
        return chartis_shell(
            ck_panel(
                f'<p class="ck-section-body">Hospital {_html.escape(ccn)} not found.</p>',
                title="Scenario Modeler",
            ),
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
        return chartis_shell(
            ck_panel(
                f'<p class="ck-section-body">Insufficient data for {_html.escape(name)}.</p>',
                title="Scenario Modeler",
            ),
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
            '<label class="sm-scenario-opt">'
            f'<input type="checkbox" name="s" value="{sc["id"]}" {checked}> '
            f'{_html.escape(sc["name"])}'
            f'<span class="sm-scenario-desc">— {_html.escape(sc["description"][:50])}</span>'
            f'</label>'
        )

    selector = ck_panel(
        f'<form method="GET" action="/scenarios/{_html.escape(ccn)}" class="sm-scenario-form">'
        '<div class="sm-scenario-list">'
        f'<div class="sm-scenario-grid">{selector_opts}</div></div>'
        '<div class="sm-scenario-submit">'
        '<button type="submit" class="cad-btn cad-btn-primary" '
        f'onclick="var cs=this.form.querySelectorAll(\'input[name=s]:checked\');'
        f'var v=Array.from(cs).map(function(c){{return c.value;}}).join(\',\');'
        f'this.form.action=\'/scenarios/{_html.escape(ccn)}?scenarios=\'+v;'
        'return true;">Compare</button>'
        '</div></form>',
        title="Select Scenarios",
    )

    intro = ck_section_intro(
        eyebrow=f"SCENARIO MODELER · CCN {_html.escape(ccn)}",
        headline=f"{_html.escape(name)} — adjust assumptions, compare returns.",
        italic_word="compare",
        body=(
            f"{len(selected)} scenarios running against the same "
            f"baseline ({_fm(rev)} revenue · {_fm(ebitda)} current "
            "EBITDA). Each scenario flows through the bridge + "
            "returns engine and surfaces side-by-side."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Net Revenue", _fm(rev),
            help={
                "definition": (
                    "Pre-shock NPR — the baseline against which every "
                    "scenario in the comparison table is differenced. "
                    "Each column shows how the scenario moves this "
                    "number under its assumed shocks."
                ),
            },
        )
        + ck_kpi_block(
            "Current EBITDA", _fm(ebitda),
            help={
                "definition": (
                    "Pre-shock Y0 EBITDA. Compare to the per-scenario "
                    "EBITDA columns below to see absolute and "
                    "percentage delta under each stress."
                ),
            },
        )
        + ck_kpi_block(
            "Current Margin", f"{current_margin:.1%}",
            help={
                "definition": (
                    "Operating margin at baseline (EBITDA / NPR). "
                    "Bank covenants test margins around base; the "
                    "scenarios compress this number — partners read "
                    "the column with the lowest margin as the "
                    "covenant-stress case."
                ),
            },
        )
        + ck_kpi_block("Beds", f"{beds:.0f}")
        + ck_kpi_block(
            "Medicare %", f"{mc_pct:.0%}",
            help={
                "definition": (
                    "Share of inpatient days paid by Medicare. "
                    "Drives sensitivity to CMS rate updates and to "
                    "the regulatory-calendar scenarios — higher "
                    "Medicare = more exposure to federal reimbursement "
                    "changes."
                ),
            },
        )
        + '</div>'
    )

    # ── Side-by-side comparison table ──
    n = len(results)
    cols = f'grid-template-columns:180px repeat({n},1fr);'

    def _row(label: str, values: list, fmt_fn=_fm, bold: bool = False) -> str:
        wt_open = "<strong>" if bold else ""
        wt_close = "</strong>" if bold else ""
        cells = "".join(f'<td class="num">{wt_open}{fmt_fn(v)}{wt_close}</td>' for v in values)
        return f'<tr><td>{wt_open}{_html.escape(label)}{wt_close}</td>{cells}</tr>'

    def _color_row(label: str, values: list, fmt_fn=_fm, good_fn=None) -> str:
        cells = ""
        for v in values:
            cls = ""
            if good_fn:
                cls = "cad-pos" if good_fn(v) else "cad-neg"
            cells += f'<td class="num {cls}"><strong>{fmt_fn(v)}</strong></td>'
        return f'<tr><td>{_html.escape(label)}</td>{cells}</tr>'

    header = '<th></th>' + ''.join(
        f'<th>{_html.escape(r["scenario"]["name"])}</th>' for r in results)

    pct = lambda v: f"{v:.1%}"
    moic_fmt = lambda v: f"{v:.2f}x"

    comparison = ck_panel(
        '<table class="cad-table"><thead><tr>'
        f'{header}</tr></thead><tbody>'
        + _row("Adj. Revenue", [r["adj_revenue"] for r in results])
        + _row("EBITDA Uplift", [r["adj_uplift"] for r in results])
        + _row("Pro Forma EBITDA", [r["new_ebitda"] for r in results], bold=True)
        + _color_row("Pro Forma Margin", [r["new_margin"] for r in results],
                      fmt_fn=pct, good_fn=lambda v: v > current_margin)
        + '<tr><td colspan="99" class="sm-divider"></td></tr>'
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
        + '</tbody></table>',
        title="Scenario Comparison",
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
                f'<td>{_html.escape(lev["name"][:20])}</td>'
                f'<td class="num cad-pos">{_fm(adj_impact)}</td>'
                f'</tr>'
            )

        irr = r["irr"]
        irr_cls = "cad-pos" if irr >= 0.20 else ("cad-warn" if irr >= 0.15 else "cad-neg")

        bridge_panels += ck_panel(
            '<p class="ck-section-body">'
            f'<strong class="{irr_cls}">{irr:.0%}</strong> IRR &nbsp; · &nbsp; '
            f'{_html.escape(sc["description"])}</p>'
            '<table class="cad-table">'
            f'{lever_rows}'
            '<tr class="sm-total-row">'
            '<td><strong>Total Uplift</strong></td>'
            f'<td class="num cad-pos"><strong>{_fm(r["adj_uplift"])}</strong></td>'
            '</tr></table>',
            title=_html.escape(sc["name"]),
        )

    bridge_section = ck_panel(
        f'<div class="sm-bridge-grid sm-bridge-grid-{min(n, 4)}">'
        f'{bridge_panels}</div>',
        title="Per-Scenario EBITDA Bridge",
    )

    # ── Timing comparison ──
    months = [0, 6, 12, 18, 24, 36]
    timing_header = '<th>Month</th>' + ''.join(
        f'<th>{_html.escape(r["scenario"]["name"][:15])}</th>' for r in results)
    timing_rows = ""
    for m in months:
        timing_rows += f'<tr><td class="num">M{m}</td>'
        for r in results:
            cumulative = 0
            for lev in r["bridge"]["levers"]:
                ramp = lev["ramp_months"]
                pct = min(1.0, m / ramp) if ramp > 0 else 1.0
                cumulative += lev["ebitda_impact"] * pct * r["scenario"].get("uplift_factor", 1.0)
            cls = "cad-pos" if cumulative > 0 else ""
            timing_rows += f'<td class="num {cls}">{_fm(cumulative)}</td>'
        timing_rows += '</tr>'

    timing_chart = _scenario_timing_chart(results, months)
    timing_caption = (
        '<div class="sm-chart-caption">'
        'Cumulative EBITDA uplift by milestone · one line per scenario'
        '</div>'
    ) if timing_chart else ""
    timing_section = ck_panel(
        '<p class="ck-section-body">'
        'Cumulative EBITDA uplift at each milestone across scenarios.</p>'
        + timing_chart + timing_caption +
        '<table class="cad-table"><thead><tr>'
        f'{timing_header}</tr></thead><tbody>{timing_rows}</tbody></table>',
        title="Implementation Timing Comparison",
    )

    # ── Nav ──
    nav = ck_panel(
        '<p class="ck-section-body">'
        f'<a href="/ebitda-bridge/{_html.escape(ccn)}" class="cad-btn cad-btn-primary">Full EBITDA Bridge</a> '
        f'<a href="/ic-memo/{_html.escape(ccn)}" class="cad-btn">IC Memo</a> '
        f'<a href="/hospital/{_html.escape(ccn)}" class="cad-btn">Hospital Profile</a> '
        f'<a href="/ml-insights/hospital/{_html.escape(ccn)}" class="cad-btn">ML Analysis</a> '
        '<a href="/predictive-screener" class="cad-btn">Deal Screener</a>'
        '</p>',
        title="Cross-links",
    )

    sm_styles = """
<style>
.sm-scenario-form{display:flex;gap:16px;align-items:flex-start;}
.sm-scenario-list{flex:1;}
.sm-scenario-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 16px;}
.sm-scenario-opt{display:flex;align-items:center;gap:6px;font-size:12px;
padding:4px 0;cursor:pointer;}
.sm-scenario-desc{color:var(--cad-text3);font-size:10px;}
.sm-scenario-submit{align-self:flex-end;}
.sm-divider{border-top:2px solid var(--cad-border);}
.sm-bridge-grid{display:grid;gap:8px;}
.sm-bridge-grid-1{grid-template-columns:1fr;}
.sm-bridge-grid-2{grid-template-columns:repeat(2,1fr);}
.sm-bridge-grid-3{grid-template-columns:repeat(3,1fr);}
.sm-bridge-grid-4{grid-template-columns:repeat(4,1fr);}
.sm-total-row td{border-top:1px solid var(--cad-border);}
</style>
"""
    next_up = ck_next_section(
        "Open the EBITDA bridge for this CCN",
        f"/ebitda-bridge/{_html.escape(ccn)}",
        eyebrow="Continue —",
        italic_word="bridge",
    )
    body = (
        f'{sm_styles}{_SM_CHART_CAPTION_CSS}{intro}{selector}{kpis}{comparison}'
        f'{bridge_section}{timing_section}{nav}{next_up}'
    )

    best = max(results, key=lambda r: r["irr"])
    return chartis_shell(
        body,
        f"Scenario Modeler — {_html.escape(name)}",
        subtitle=(
            f"CCN {_html.escape(ccn)} | {len(results)} scenarios | "
            f"Best: {best['scenario']['name']} ({best['irr']:.0%} IRR, {best['moic']:.1f}x MOIC)"
        ),
    )
