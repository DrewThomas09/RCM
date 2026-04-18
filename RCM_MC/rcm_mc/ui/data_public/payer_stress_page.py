"""Payer Mix Stress Tester page — /payer-stress.

Simulates the MOIC impact of payer mix shifts: commercial contract loss,
Medicare rate cuts, Medicaid expansion. Corpus-calibrated via linear
regression of payer % vs realized MOIC.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, Optional

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_section_header, ck_kpi_block,
    ck_fmt_moic, ck_fmt_pct,
)


def _scenario_table(scenarios: list) -> str:
    rows = []
    for s in scenarios:
        delta = s.moic_delta
        stressed = s.stressed_moic
        is_base = s.delta_comm == 0 and s.delta_mcare == 0 and s.delta_mcaid == 0

        if is_base:
            delta_html = '<span class="mn" style="color:var(--ck-text-dim)">baseline</span>'
        elif delta > 0:
            delta_html = f'<span class="mn pos">+{delta:.3f}×</span>'
        else:
            delta_html = f'<span class="mn neg">{delta:.3f}×</span>'

        pct = s.pct_impact
        if is_base:
            pct_html = '—'
        elif pct > 0:
            pct_html = f'<span class="mn pos">+{pct:.1f}%</span>'
        else:
            pct_html = f'<span class="mn neg">{pct:.1f}%</span>'

        moic_color = P["positive"] if stressed >= 3.0 else P["warning"] if stressed >= 2.0 else P["negative"]
        moic_html = f'<span class="mn" style="color:{moic_color}">{stressed:.2f}×</span>'

        row_style = ' style="background:rgba(59,130,246,.07)"' if is_base else ""

        rows.append(
            f"<tr{row_style}>"
            f"<td><strong>{_html.escape(s.label)}</strong></td>"
            f"<td style='font-size:11px;color:var(--ck-text-dim)'>{_html.escape(s.description)}</td>"
            f"<td class='r mn'>"
            f"{'—' if s.delta_comm == 0 else f'{s.delta_comm*100:+.0f}pp'}</td>"
            f"<td class='r mn'>"
            f"{'—' if s.delta_mcare == 0 else f'{s.delta_mcare*100:+.0f}pp'}</td>"
            f"<td class='r mn'>"
            f"{'—' if s.delta_mcaid == 0 else f'{s.delta_mcaid*100:+.0f}pp'}</td>"
            f"<td class='r'>{moic_html}</td>"
            f"<td class='r'>{delta_html}</td>"
            f"<td class='r'>{pct_html}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Scenario</th><th>Description</th>"
        "<th class='r'>Δ Comm</th><th class='r'>Δ Medicare</th>"
        "<th class='r'>Δ Medicaid</th>"
        "<th class='r'>Est. MOIC</th>"
        "<th class='r'>MOIC Delta</th><th class='r'>% Impact</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _waterfall_svg(scenarios: list, width: int = 680, height: int = 200) -> str:
    """Horizontal bar for each scenario showing absolute MOIC with delta marker."""
    if not scenarios:
        return ""
    ml, mr, mt, mb = 100, 20, 10, 25
    W = width - ml - mr
    H = height - mt - mb

    all_moics = [s.stressed_moic for s in scenarios]
    max_v = max(max(all_moics) * 1.1, 4.0)
    bar_h = max(12, H // len(scenarios) - 4)
    row_h = H // len(scenarios)

    def px(v: float) -> int:
        return int(ml + v / max_v * W)

    def py(i: int) -> int:
        return mt + i * row_h + (row_h - bar_h) // 2

    lines = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
    ]

    # Grid
    for gv in [1.0, 2.0, 3.0, 4.0]:
        x = px(gv)
        lines.append(
            f'<line x1="{x}" y1="{mt}" x2="{x}" y2="{mt+H}" '
            f'stroke="{P["border"]}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{x}" y="{mt+H+14}" text-anchor="middle" font-size="9" '
            f'fill="{P["text_faint"]}" font-family="JetBrains Mono,monospace">'
            f'{gv:.0f}×</text>'
        )

    base_moic = scenarios[0].base_moic if scenarios else 2.5
    bx = px(base_moic)
    lines.append(
        f'<line x1="{bx}" y1="{mt}" x2="{bx}" y2="{mt+H}" '
        f'stroke="{P["accent"]}" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>'
    )

    for i, s in enumerate(scenarios):
        y = py(i)
        is_base = s.delta_comm == 0 and s.delta_mcare == 0 and s.delta_mcaid == 0
        v = s.stressed_moic
        bar_color = (
            P["accent"] if is_base
            else P["positive"] if s.moic_delta >= 0
            else P["negative"]
        )
        bw = max(2, px(v) - ml)
        lines.append(
            f'<rect x="{ml}" y="{y}" width="{bw}" height="{bar_h}" '
            f'fill="{bar_color}" opacity="{"0.9" if is_base else "0.7"}" rx="2"/>'
        )
        lines.append(
            f'<text x="{ml - 4}" y="{y + bar_h//2 + 4}" '
            f'text-anchor="end" font-size="10" fill="{P["text_dim"]}" '
            f'font-family="Inter,sans-serif">{_html.escape(s.label)}</text>'
        )
        lines.append(
            f'<text x="{ml + bw + 4}" y="{y + bar_h//2 + 4}" '
            f'font-size="9" fill="{bar_color}" '
            f'font-family="JetBrains Mono,monospace" font-variant-numeric="tabular-nums">'
            f'{v:.2f}×</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def _reg_table(result: Any) -> str:
    rows = []
    for reg in [result.comm_reg, result.mcare_reg, result.mcaid_reg]:
        r2_color = P["positive"] if reg.r2 >= 0.2 else P["warning"] if reg.r2 >= 0.05 else P["text_faint"]
        slope_dir = "+" if reg.slope >= 0 else ""
        rows.append(
            f"<tr>"
            f"<td>{_html.escape(reg.payer)}</td>"
            f"<td class='r mn'>{reg.n}</td>"
            f"<td class='r mn'>{slope_dir}{reg.slope:.4f}</td>"
            f"<td class='r mn'>{reg.intercept:.3f}</td>"
            f"<td class='r mn' style='color:{r2_color}'>{reg.r2:.3f}</td>"
            f"<td class='r mn'>{reg.moic_per_10pct:+.3f}×</td>"
            f"<td class='r'>{ck_fmt_moic(reg.moic_p50)}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Payer</th><th class='r'>N</th><th class='r'>Slope</th>"
        "<th class='r'>Intercept</th><th class='r'>R²</th>"
        "<th class='r'>MOIC / 10pp</th><th class='r'>P50 MOIC</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _payer_slider_form(params: Dict[str, str]) -> str:
    sector = _html.escape(params.get("sector", ""))
    comm = params.get("comm_pct", "0.60")
    mcare = params.get("mcare_pct", "0.25")
    mcaid = params.get("mcaid_pct", "0.10")
    ev_mm = params.get("ev_mm", "")
    return f"""
<form method="get" action="/payer-stress" class="ck-form">
  <div class="ck-form-row">
    <div class="ck-form-group">
      <label class="ck-label">Sector (optional)</label>
      <input type="text" name="sector" class="ck-input w180"
        placeholder="e.g. Behavioral Health" value="{sector}">
    </div>
    <div class="ck-form-group">
      <label class="ck-label">Entry EV ($M, optional)</label>
      <input type="number" name="ev_mm" class="ck-input w130"
        placeholder="e.g. 300" value="{_html.escape(ev_mm)}" step="10">
    </div>
  </div>
  <div class="ck-form-row" style="margin-top:12px">
    <div class="ck-form-group">
      <label class="ck-label">Commercial % (0–1)</label>
      <input type="number" name="comm_pct" class="ck-input w130"
        value="{_html.escape(comm)}" step="0.05" min="0" max="1">
    </div>
    <div class="ck-form-group">
      <label class="ck-label">Medicare % (0–1)</label>
      <input type="number" name="mcare_pct" class="ck-input w130"
        value="{_html.escape(mcare)}" step="0.05" min="0" max="1">
    </div>
    <div class="ck-form-group">
      <label class="ck-label">Medicaid % (0–1)</label>
      <input type="number" name="mcaid_pct" class="ck-input w130"
        value="{_html.escape(mcaid)}" step="0.05" min="0" max="1">
    </div>
    <div class="ck-form-group" style="align-self:flex-end">
      <button type="submit" class="ck-btn">Run Stress Test</button>
    </div>
  </div>
</form>"""


def render_payer_stress(params: Dict[str, str]) -> str:
    from rcm_mc.data_public.payer_stress import compute_payer_stress

    def _flt(k: str, default: float) -> float:
        try:
            return float(params.get(k, default))
        except (TypeError, ValueError):
            return default

    base_comm = _flt("comm_pct", 0.60)
    base_mcare = _flt("mcare_pct", 0.25)
    base_mcaid = _flt("mcaid_pct", 0.10)
    sector = params.get("sector", "")
    ev_mm_raw = params.get("ev_mm")
    ev_mm = None
    try:
        if ev_mm_raw:
            ev_mm = float(ev_mm_raw)
    except (TypeError, ValueError):
        pass

    result = compute_payer_stress(
        base_comm=base_comm,
        base_mcare=base_mcare,
        base_mcaid=base_mcaid,
        sector=sector,
        ev_mm=ev_mm,
    )

    # Find worst / best scenarios (excluding base)
    non_base = [s for s in result.scenarios if not (s.delta_comm == 0 and s.delta_mcare == 0 and s.delta_mcaid == 0)]
    worst = min(non_base, key=lambda s: s.moic_delta, default=None)
    best = max(non_base, key=lambda s: s.moic_delta, default=None)

    kpi_grid = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Corpus Peers",
            f'<span class="mn">{result.n_corpus_peers}</span>',
            f"sector: {_html.escape(sector or 'all')}",
        )
        + ck_kpi_block(
            "Base MOIC Estimate",
            ck_fmt_moic(result.base_moic_estimate),
            f"comm {base_comm*100:.0f}% / mcare {base_mcare*100:.0f}% / mcaid {base_mcaid*100:.0f}%",
        )
        + ck_kpi_block(
            "Corpus P50 MOIC",
            ck_fmt_moic(result.corpus_p50),
            "all realized deals",
        )
        + ck_kpi_block(
            "Worst Scenario",
            f'<span class="mn neg">{worst.moic_delta:+.3f}×</span>' if worst else "—",
            _html.escape(worst.label) if worst else "",
        )
        + ck_kpi_block(
            "Best Scenario",
            f'<span class="mn pos">{best.moic_delta:+.3f}×</span>' if best else "—",
            _html.escape(best.label) if best else "",
        )
        + "</div>"
    )

    chart = _waterfall_svg(result.scenarios)
    scen_table = _scenario_table(result.scenarios)
    reg_table = _reg_table(result)

    body = f"""
{_payer_slider_form(params)}
{kpi_grid}
{ck_section_header("Scenario MOIC Impact", f"{result.n_corpus_peers} peer deals · payer regression-calibrated")}
<div style="overflow-x:auto;margin-bottom:24px">{chart}</div>
<div style="overflow-x:auto;margin-bottom:24px">{scen_table}</div>
{ck_section_header("Regression Coefficients", "Payer share vs. realized MOIC — corpus OLS")}
<div style="overflow-x:auto">{reg_table}</div>
<p style="font-size:11px;color:var(--ck-text-faint);margin-top:12px">
  Note: MOIC estimates are linear approximations from corpus regression.
  R² &lt; 0.10 indicates weak explanatory power — treat as directional, not predictive.
  Corpus data: seed deals only, pre-2023 vintages.
</p>
"""

    extra_css = """
.ck-form { margin-bottom: 24px; }
.ck-form-row { display:flex; flex-wrap:wrap; gap:12px; align-items:flex-start; }
.ck-form-group { display:flex; flex-direction:column; gap:4px; }
.ck-label { font-size:11px; color:var(--ck-text-dim); text-transform:uppercase; letter-spacing:.06em; }
.ck-input {
  background:var(--ck-panel-alt); border:1px solid var(--ck-border);
  color:var(--ck-text); padding:6px 10px; font-size:12px;
  font-family:'JetBrains Mono',monospace; border-radius:3px;
}
.w180 { width:180px; }
.w130 { width:130px; }
.ck-input:focus { outline:1px solid var(--ck-accent); }
.ck-btn {
  background:var(--ck-accent); color:#fff; border:none; padding:7px 18px;
  font-size:12px; border-radius:3px; cursor:pointer; letter-spacing:.04em;
}
.ck-btn:hover { filter:brightness(1.15); }
"""

    return chartis_shell(
        body=body,
        title="Payer Mix Stress Tester",
        active_nav="/payer-stress",
        subtitle="Corpus-calibrated MOIC sensitivity to payer mix shifts",
        extra_css=extra_css,
    )
