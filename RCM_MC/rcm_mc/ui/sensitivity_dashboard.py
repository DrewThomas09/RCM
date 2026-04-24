"""Sensitivity analysis dashboard (Prompt 47).

Renders an interactive HTML page with parameter sliders for PE deal
sensitivity analysis. The page shows a hold-period grid (rows = hold
years 2-7, cols = exit multiples 6-15x, cells = MOIC) and wires to
a deterministic API endpoint that returns bridge + PE math results
without Monte Carlo simulation.

The UI uses the shared shell and dark theme from ``_ui_kit.py``.
Sliders post to ``/api/analysis/<deal_id>/sensitivity`` which returns
a JSON grid of MOIC/IRR values for the full parameter sweep.

Public API:
    render_sensitivity_page(packet) -> str
    compute_sensitivity_grid(params) -> dict
"""
from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Data types ──────────────────────────────────────────────────────────


@dataclass
class SensitivityParams:
    """Parameters for a deterministic sensitivity sweep."""
    entry_ebitda: float = 50.0       # $M
    entry_multiple: float = 10.0     # x
    exit_multiple_range: tuple = (6.0, 15.0)   # min, max
    exit_multiple_step: float = 1.0
    hold_years_range: tuple = (2, 7)           # min, max
    achievement_pct: float = 1.0     # 0-1, fraction of planned uplift
    planned_uplift: float = 10.0     # $M EBITDA uplift at 100%
    organic_growth_pct: float = 0.03
    debt_to_ebitda: float = 5.0      # entry leverage


@dataclass
class GridCell:
    """Single cell in the hold-period x exit-multiple grid."""
    hold_years: int
    exit_multiple: float
    moic: float
    irr: float
    exit_ev: float
    equity_value: float


@dataclass
class SensitivityResult:
    """Full sensitivity grid output."""
    params: Dict[str, Any] = field(default_factory=dict)
    grid: List[GridCell] = field(default_factory=list)
    exit_multiples: List[float] = field(default_factory=list)
    hold_years_list: List[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "params": self.params,
            "exit_multiples": self.exit_multiples,
            "hold_years": self.hold_years_list,
            "grid": [
                {
                    "hold_years": c.hold_years,
                    "exit_multiple": c.exit_multiple,
                    "moic": round(c.moic, 2),
                    "irr": round(c.irr, 4),
                    "exit_ev": round(c.exit_ev, 2),
                    "equity_value": round(c.equity_value, 2),
                }
                for c in self.grid
            ],
        }


# ── Deterministic PE math ───────────────────────────────────────────────


def _simple_irr(invested: float, returned: float, years: float) -> float:
    """Annualised IRR from a single entry/exit — no iteration needed."""
    if invested <= 0 or returned <= 0 or years <= 0:
        return -1.0
    return (returned / invested) ** (1.0 / years) - 1.0


def compute_sensitivity_grid(params: SensitivityParams) -> SensitivityResult:
    """Build the MOIC/IRR grid across hold years x exit multiples.

    All math is deterministic — no Monte Carlo. The EBITDA at exit is:
        exit_ebitda = entry_ebitda * (1 + organic_growth)^hold_years
                    + planned_uplift * achievement_pct

    Equity value = exit_ev - entry_debt. MOIC = equity_value / entry_equity.
    """
    entry_ev = params.entry_ebitda * params.entry_multiple
    entry_debt = params.entry_ebitda * params.debt_to_ebitda
    entry_equity = max(entry_ev - entry_debt, 0.01)  # avoid div-by-zero

    # Build ranges
    em_min, em_max = params.exit_multiple_range
    step = params.exit_multiple_step
    exit_multiples: List[float] = []
    em = em_min
    while em <= em_max + 1e-9:
        exit_multiples.append(round(em, 2))
        em += step

    hy_min, hy_max = params.hold_years_range
    hold_years_list = list(range(hy_min, hy_max + 1))

    cells: List[GridCell] = []
    for hy in hold_years_list:
        # EBITDA at exit
        organic = params.entry_ebitda * ((1 + params.organic_growth_pct) ** hy)
        uplift = params.planned_uplift * params.achievement_pct
        exit_ebitda = organic + uplift

        for em_val in exit_multiples:
            exit_ev = exit_ebitda * em_val
            equity_val = max(exit_ev - entry_debt, 0.0)
            moic = equity_val / entry_equity if entry_equity > 0 else 0.0
            irr = _simple_irr(entry_equity, equity_val, hy)

            cells.append(GridCell(
                hold_years=hy,
                exit_multiple=em_val,
                moic=round(moic, 4),
                irr=round(irr, 4),
                exit_ev=round(exit_ev, 2),
                equity_value=round(equity_val, 2),
            ))

    return SensitivityResult(
        params={
            "entry_ebitda": params.entry_ebitda,
            "entry_multiple": params.entry_multiple,
            "achievement_pct": params.achievement_pct,
            "planned_uplift": params.planned_uplift,
            "organic_growth_pct": params.organic_growth_pct,
            "debt_to_ebitda": params.debt_to_ebitda,
        },
        grid=cells,
        exit_multiples=exit_multiples,
        hold_years_list=hold_years_list,
    )


# ── HTML renderer ───────────────────────────────────────────────────────


def _moic_color(moic: float) -> str:
    """Color-code MOIC cells: green > 2x, amber 1-2x, red < 1x."""
    if moic >= 3.0:
        return "#10B981"
    if moic >= 2.0:
        return "#34D399"
    if moic >= 1.5:
        return "#F59E0B"
    if moic >= 1.0:
        return "#FB923C"
    return "#EF4444"


def render_sensitivity_page(
    packet: Any = None,
    *,
    deal_id: str = "",
    params: Optional[SensitivityParams] = None,
) -> str:
    """Render the sensitivity analysis HTML page.

    If a packet is provided, extract entry EBITDA and planned uplift
    from it. Otherwise use the provided params or defaults.
    """
    if params is None:
        params = SensitivityParams()

    # Extract from packet if available
    if packet is not None:
        if hasattr(packet, "entry_ebitda") and packet.entry_ebitda:
            params.entry_ebitda = float(packet.entry_ebitda)
        if hasattr(packet, "ebitda_bridge"):
            bridge = packet.ebitda_bridge
            if bridge and hasattr(bridge, "total_ebitda_impact"):
                params.planned_uplift = float(bridge.total_ebitda_impact)

    result = compute_sensitivity_grid(params)
    d = result.to_dict()

    # Build the grid table HTML
    table_html = _build_grid_table(result)

    qd = html.escape(deal_id, quote=True)

    body = f"""
<div style="padding:20px; max-width:1200px; margin:0 auto;">
  <h2 style="color:#e2e8f0; margin-bottom:4px;">
    Sensitivity Analysis{' &mdash; ' + html.escape(deal_id) if deal_id else ''}
  </h2>
  <p style="color:#94a3b8; margin-top:0;">
    Deterministic MOIC grid across hold periods and exit multiples.
    Adjust sliders to re-compute.
  </p>

  <div style="background:#111827; border:1px solid #1e293b; border-radius:4px;
              padding:16px; margin-bottom:20px;">
    <h3 style="color:#e2e8f0; margin-top:0;">Parameters</h3>
    <form id="sens-form" method="POST"
          action="/api/analysis/{qd}/sensitivity"
          style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;">

      <label style="color:#94a3b8;">
        Exit Multiple Range: <span id="em-val">
          {params.exit_multiple_range[0]:.0f}x &ndash; {params.exit_multiple_range[1]:.0f}x
        </span><br>
        <input type="range" name="exit_multiple_min" min="4" max="20" step="1"
               value="{params.exit_multiple_range[0]:.0f}"
               style="width:100%;">
        <input type="range" name="exit_multiple_max" min="4" max="20" step="1"
               value="{params.exit_multiple_range[1]:.0f}"
               style="width:100%;">
      </label>

      <label style="color:#94a3b8;">
        Achievement: <span id="ach-val">{params.achievement_pct * 100:.0f}%</span><br>
        <input type="range" name="achievement_pct" min="0" max="100" step="5"
               value="{params.achievement_pct * 100:.0f}"
               style="width:100%;">
      </label>

      <label style="color:#94a3b8;">
        Hold Years: <span id="hy-val">
          {params.hold_years_range[0]} &ndash; {params.hold_years_range[1]}
        </span><br>
        <input type="range" name="hold_years_min" min="1" max="10" step="1"
               value="{params.hold_years_range[0]}"
               style="width:100%;">
        <input type="range" name="hold_years_max" min="1" max="10" step="1"
               value="{params.hold_years_range[1]}"
               style="width:100%;">
      </label>

      <label style="color:#94a3b8;">
        Entry EBITDA ($M):
        <input type="number" name="entry_ebitda" step="0.1"
               value="{params.entry_ebitda:.1f}"
               style="width:100%; background:#0a0e17; color:#e2e8f0;
                      border:1px solid #1e293b; padding:4px;">
      </label>

      <label style="color:#94a3b8;">
        Entry Multiple (x):
        <input type="number" name="entry_multiple" step="0.5"
               value="{params.entry_multiple:.1f}"
               style="width:100%; background:#0a0e17; color:#e2e8f0;
                      border:1px solid #1e293b; padding:4px;">
      </label>

      <label style="color:#94a3b8;">
        Planned Uplift ($M):
        <input type="number" name="planned_uplift" step="0.5"
               value="{params.planned_uplift:.1f}"
               style="width:100%; background:#0a0e17; color:#e2e8f0;
                      border:1px solid #1e293b; padding:4px;">
      </label>

      <div style="grid-column: span 3; text-align:right;">
        <button type="submit"
                style="background:#1F4E78; color:#e2e8f0; border:none;
                       padding:8px 20px; border-radius:4px; cursor:pointer;">
          Re-compute Grid
        </button>
      </div>
    </form>
  </div>

  <div style="background:#111827; border:1px solid #1e293b; border-radius:4px;
              padding:16px;">
    <h3 style="color:#e2e8f0; margin-top:0;">
      MOIC Grid (Hold Years x Exit Multiple)
    </h3>
    {table_html}
  </div>

  <script>
    var data = {json.dumps(d)};
  </script>
</div>
"""
    # Use the shared shell if available
    try:
        from ._ui_kit import shell
        return shell(body, "Sensitivity Analysis", extra_css=_EXTRA_CSS)
    except (ImportError, Exception):
        return f"""<!DOCTYPE html>
<html><head><title>Sensitivity Analysis</title>
<style>{_EXTRA_CSS}</style></head>
<body style="background:#0a0e17; color:#e2e8f0; font-family:system-ui;">
{body}</body></html>"""


def _build_grid_table(result: SensitivityResult) -> str:
    """Build the HTML table for the MOIC grid."""
    if not result.grid:
        return "<p style='color:#94a3b8;'>No grid data.</p>"

    # Index cells by (hold_years, exit_multiple)
    lookup: Dict[tuple, GridCell] = {}
    for c in result.grid:
        lookup[(c.hold_years, c.exit_multiple)] = c

    rows = []
    # Header row
    hdr = "<tr><th style='padding:6px 10px; color:#94a3b8;'>Hold \\ Exit</th>"
    for em in result.exit_multiples:
        hdr += f"<th style='padding:6px 10px; color:#94a3b8;'>{em:.1f}x</th>"
    hdr += "</tr>"
    rows.append(hdr)

    for hy in result.hold_years_list:
        row = f"<tr><td style='padding:6px 10px; color:#94a3b8; font-weight:bold;'>{hy}yr</td>"
        for em in result.exit_multiples:
            cell = lookup.get((hy, em))
            if cell:
                color = _moic_color(cell.moic)
                irr_pct = cell.irr * 100
                row += (
                    f"<td style='padding:6px 10px; text-align:center; "
                    f"color:{color}; font-variant-numeric:tabular-nums;' "
                    f"title='IRR: {irr_pct:.1f}%'>"
                    f"{cell.moic:.2f}x</td>"
                )
            else:
                row += "<td style='padding:6px 10px; color:#4b5563;'>-</td>"
        row += "</tr>"
        rows.append(row)

    return (
        "<table style='width:100%; border-collapse:collapse; "
        "font-family:\"JetBrains Mono\",monospace; font-size:13px;'>"
        + "\n".join(rows) +
        "</table>"
    )


_EXTRA_CSS = """
table td, table th {
    border: 1px solid #1e293b;
}
table tr:hover td {
    background: #1e293b;
}
input[type=range] {
    accent-color: #1F4E78;
}
"""


# ── API handler helper ──────────────────────────────────────────────────


def handle_sensitivity_post(form: Dict[str, str]) -> dict:
    """Parse form data and return the sensitivity grid as a dict.

    Called by the server's POST /api/analysis/<deal_id>/sensitivity
    route. All parameters have safe defaults so partial forms work.
    """
    def _float(key: str, default: float) -> float:
        try:
            return float(form.get(key, default))
        except (ValueError, TypeError):
            return default

    def _int(key: str, default: int) -> int:
        try:
            return int(float(form.get(key, default)))
        except (ValueError, TypeError):
            return default

    params = SensitivityParams(
        entry_ebitda=_float("entry_ebitda", 50.0),
        entry_multiple=_float("entry_multiple", 10.0),
        exit_multiple_range=(
            max(1.0, _float("exit_multiple_min", 6.0)),
            max(1.0, _float("exit_multiple_max", 15.0)),
        ),
        hold_years_range=(
            max(1, _int("hold_years_min", 2)),
            max(1, _int("hold_years_max", 7)),
        ),
        achievement_pct=max(0.0, min(1.0, _float("achievement_pct", 100.0) / 100.0)),
        planned_uplift=_float("planned_uplift", 10.0),
        organic_growth_pct=_float("organic_growth_pct", 3.0) / 100.0
        if _float("organic_growth_pct", 3.0) > 1 else _float("organic_growth_pct", 0.03),
        debt_to_ebitda=_float("debt_to_ebitda", 5.0),
    )

    result = compute_sensitivity_grid(params)
    return result.to_dict()
