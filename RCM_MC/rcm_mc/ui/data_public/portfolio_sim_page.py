"""Portfolio Scenario Simulator page — /portfolio-sim.

Stress tests a custom portfolio composition against 5 macro scenarios.
User specifies sectors and EV sizes; page computes weighted expected MOIC
distribution per scenario using corpus regression calibration.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_section_header, ck_kpi_block, ck_fmt_moic,
)


def _scenario_chart_svg(scenarios: List[Any], width: int = 640, height: int = 180) -> str:
    """Grouped bar chart: P25/P50/P75 per scenario."""
    if not scenarios:
        return ""
    ml, mr, mt, mb = 60, 20, 12, 28
    W = width - ml - mr
    H = height - mt - mb

    all_p75 = [s.portfolio_moic_p75 for s in scenarios]
    max_v = max(max(all_p75) * 1.1, 4.5)
    bar_w = max(12, W // len(scenarios) - 16)
    group_w = W // len(scenarios)

    def px(v: float) -> int:
        return int(mt + H - v / max_v * H)

    lines = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
    ]

    # Grid
    for gv in [1.0, 2.0, 3.0, 4.0]:
        y = px(gv)
        lines.append(
            f'<line x1="{ml}" y1="{y}" x2="{ml+W}" y2="{y}" '
            f'stroke="{P["border"]}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{ml-4}" y="{y+4}" text-anchor="end" font-size="9" '
            f'fill="{P["text_faint"]}" font-family="JetBrains Mono,monospace">'
            f'{gv:.0f}×</text>'
        )

    for i, sc in enumerate(scenarios):
        cx = ml + i * group_w + group_w // 2

        # P25–P75 band
        y25 = px(sc.portfolio_moic_p25)
        y75 = px(sc.portfolio_moic_p75)
        band_h = max(2, y25 - y75)
        lines.append(
            f'<rect x="{cx - bar_w//2}" y="{y75}" width="{bar_w}" height="{band_h}" '
            f'fill="{sc.color}" opacity="0.25" rx="2"/>'
        )
        # P50 tick
        y50 = px(sc.portfolio_moic_p50)
        lines.append(
            f'<rect x="{cx - bar_w//2}" y="{y50 - 2}" width="{bar_w}" height="4" '
            f'fill="{sc.color}"/>'
        )
        lines.append(
            f'<text x="{cx}" y="{y50 - 6}" text-anchor="middle" font-size="9" '
            f'fill="{sc.color}" font-family="JetBrains Mono,monospace" '
            f'font-variant-numeric="tabular-nums">{sc.portfolio_moic_p50:.2f}×</text>'
        )
        lines.append(
            f'<text x="{cx}" y="{mt + H + 16}" text-anchor="middle" font-size="9" '
            f'fill="{P["text_dim"]}" font-family="Inter,sans-serif">'
            f'{_html.escape(sc.label)}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def _scenario_table(scenarios: List[Any]) -> str:
    rows = []
    base = next((s for s in scenarios if s.scenario_id == "base"), None)
    for sc in scenarios:
        is_base = sc.scenario_id == "base"
        delta = round(sc.portfolio_moic_p50 - (base.portfolio_moic_p50 if base else sc.portfolio_moic_p50), 3)
        delta_html = (
            '<span class="mn" style="color:var(--ck-text-dim)">—</span>'
            if is_base
            else (
                f'<span class="mn pos">+{delta:.3f}×</span>'
                if delta >= 0
                else f'<span class="mn neg">{delta:.3f}×</span>'
            )
        )
        row_bg = f"background:rgba({','.join(str(int(x, 16)) for x in [sc.color[1:3], sc.color[3:5], sc.color[5:7]])},0.06);" if not is_base else ""
        cdim = P["text_dim"]
        rows.append(
            f"<tr style='{row_bg}'>"
            f"<td><span style='color:{sc.color};font-weight:700'>{_html.escape(sc.label)}</span></td>"
            f"<td style='font-size:10px;color:{cdim}'>{_html.escape(sc.description)}</td>"
            f"<td class='r mn' style='color:{cdim}'>{sc.portfolio_moic_p25:.2f}×</td>"
            f"<td class='r mn' style='color:{sc.color}'>{sc.portfolio_moic_p50:.2f}×</td>"
            f"<td class='r mn' style='color:{cdim}'>{sc.portfolio_moic_p75:.2f}×</td>"
            f"<td class='r'>{delta_html}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Scenario</th><th>Description</th>"
        "<th class='r'>P25 MOIC</th><th class='r'>P50 MOIC</th>"
        "<th class='r'>P75 MOIC</th><th class='r'>vs. Base</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _positions_table(positions: List[Any], scenarios: List[Any]) -> str:
    base_sc = next((s for s in scenarios if s.scenario_id == "base"), None)
    rec_sc = next((s for s in scenarios if s.scenario_id == "recession"), None)

    header_extra = ""
    if base_sc:
        header_extra += "<th class='r'>Base MOIC</th>"
    if rec_sc:
        header_extra += "<th class='r'>Recession</th>"

    rows = []
    for i, pos in enumerate(positions):
        base_moic_html = (
            f'<span class="mn">{base_sc.position_moics[i]:.2f}×</span>'
            if base_sc and i < len(base_sc.position_moics) else "—"
        )
        rec_moic = rec_sc.position_moics[i] if rec_sc and i < len(rec_sc.position_moics) else None
        rec_delta = round(rec_moic - (base_sc.position_moics[i] if base_sc else 0), 3) if rec_moic and base_sc else None
        rec_html = (
            f'<span class="mn neg">{rec_delta:+.3f}×</span>'
            if rec_delta is not None else "—"
        )
        rows.append(
            f"<tr>"
            f"<td>{_html.escape(pos.sector)}</td>"
            f"<td class='r mn'>${pos.ev_mm:,.0f}M</td>"
            f"<td class='r mn'>{pos.weight*100:.1f}%</td>"
            f"<td class='r mn'>{pos.n_peers}</td>"
            f"<td class='r'>{base_moic_html}</td>"
            f"<td class='r'>{rec_html}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Sector</th><th class='r'>EV</th><th class='r'>Weight</th>"
        "<th class='r'>Corpus Peers</th>"
        "<th class='r'>Base MOIC</th><th class='r'>Recession Delta</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _portfolio_form(positions_raw: str) -> str:
    return f"""
<form method="get" action="/portfolio-sim" class="ck-form">
  <div class="ck-form-group" style="width:100%">
    <label class="ck-label">Portfolio Positions (one per line: Sector Name, EV_$M)</label>
    <textarea name="positions" class="ck-input" rows="6"
      style="width:100%;max-width:600px;height:120px;resize:vertical;font-family:'JetBrains Mono',monospace;font-size:11px"
      placeholder="Behavioral Health, 250&#10;Physician Practice Management, 400&#10;Home Health, 320">{_html.escape(positions_raw)}</textarea>
  </div>
  <div class="ck-form-group" style="margin-top:8px">
    <button type="submit" class="ck-btn">Run Simulation</button>
    <a href="/portfolio-sim" class="ck-link" style="margin-left:12px;font-size:11px">Reset to default</a>
  </div>
</form>"""


def _parse_positions(raw: str) -> List[Dict[str, Any]]:
    positions = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.rsplit(",", 1)
        if len(parts) != 2:
            continue
        sector = parts[0].strip()
        try:
            ev = float(parts[1].strip().replace("$", "").replace("M", "").replace(",", ""))
        except (ValueError, TypeError):
            continue
        if sector and ev > 0:
            positions.append({"sector": sector, "ev_mm": ev})
    return positions


_DEFAULT_RAW = (
    "Behavioral Health, 250\n"
    "Physician Practice Management, 400\n"
    "Ambulatory Surgery Center, 180\n"
    "Home Health, 320\n"
    "Revenue Cycle Management, 150"
)


def render_portfolio_sim(params: Dict[str, str]) -> str:
    from rcm_mc.data_public.portfolio_sim import compute_portfolio_sim, DEFAULT_PORTFOLIO

    raw = params.get("positions", "").strip()
    if raw:
        positions_input = _parse_positions(raw)
        positions_raw = raw
    else:
        positions_input = DEFAULT_PORTFOLIO
        positions_raw = _DEFAULT_RAW

    if not positions_input:
        positions_input = DEFAULT_PORTFOLIO
        positions_raw = _DEFAULT_RAW

    result = compute_portfolio_sim(positions_input)

    base_sc = next((s for s in result.scenarios if s.scenario_id == "base"), None)
    rec_sc = next((s for s in result.scenarios if s.scenario_id == "recession"), None)
    bull_sc = next((s for s in result.scenarios if s.scenario_id == "bull"), None)

    kpi_grid = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Portfolio Positions",
            f'<span class="mn">{result.n_positions}</span>',
            f"${result.total_ev_mm:,.0f}M total EV",
        )
        + ck_kpi_block(
            "Base P50 MOIC",
            ck_fmt_moic(base_sc.portfolio_moic_p50 if base_sc else None),
            "corpus-calibrated",
        )
        + ck_kpi_block(
            "Recession P50 MOIC",
            f'<span class="mn neg">{rec_sc.portfolio_moic_p50:.2f}×</span>' if rec_sc else "—",
            f"delta {rec_sc.portfolio_moic_p50 - base_sc.portfolio_moic_p50:+.2f}×" if rec_sc and base_sc else "",
        )
        + ck_kpi_block(
            "Bull P50 MOIC",
            f'<span class="mn pos">{bull_sc.portfolio_moic_p50:.2f}×</span>' if bull_sc else "—",
            f"delta {bull_sc.portfolio_moic_p50 - base_sc.portfolio_moic_p50:+.2f}×" if bull_sc and base_sc else "",
        )
        + ck_kpi_block(
            "Corpus P50 MOIC",
            ck_fmt_moic(result.corpus_p50),
            "all realized deals",
        )
        + "</div>"
    )

    chart = _scenario_chart_svg(result.scenarios)
    scen_table = _scenario_table(result.scenarios)
    pos_table = _positions_table(result.positions, result.scenarios)

    body = f"""
{_portfolio_form(positions_raw)}
{kpi_grid}
{ck_section_header("Scenario MOIC Distribution", "P25 band + P50 tick per macro scenario")}
<div style="overflow-x:auto;margin-bottom:16px">{chart}</div>
<div style="overflow-x:auto;margin-bottom:24px">{scen_table}</div>
{ck_section_header("Position-Level Detail")}
<div style="overflow-x:auto">{pos_table}</div>
<p style="font-size:11px;color:{P["text_faint"]};margin-top:12px">
  Scenario shocks are calibrated against corpus regression coefficients and PE
  literature estimates (recession −18% MOIC, rate shock −12%, bull +12%).
  Position MOICs are sector median MOIC from corpus peers, stress-adjusted per scenario.
  Not a forward-looking forecast.
</p>
"""

    extra_css = """
.ck-form { margin-bottom: 24px; }
.ck-form-group { display:flex; flex-direction:column; gap:4px; }
.ck-label { font-size:11px; color:var(--ck-text-dim); text-transform:uppercase; letter-spacing:.06em; }
.ck-input {
  background:var(--ck-panel-alt); border:1px solid var(--ck-border);
  color:var(--ck-text); padding:6px 10px; font-size:12px; border-radius:3px;
}
.ck-btn {
  background:var(--ck-accent); color:#fff; border:none; padding:7px 18px;
  font-size:12px; border-radius:3px; cursor:pointer;
}
.ck-btn:hover { filter:brightness(1.15); }
.ck-link { color:var(--ck-accent); text-decoration:none; }
.ck-link:hover { text-decoration:underline; }
"""

    return chartis_shell(
        body=body,
        title="Portfolio Scenario Simulator",
        active_nav="/portfolio-sim",
        subtitle="Stress-test custom portfolio composition against 5 macro scenarios",
        extra_css=extra_css,
    )
