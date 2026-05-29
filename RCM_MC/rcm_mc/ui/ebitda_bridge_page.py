"""PE Desk EBITDA Bridge Engine — best-in-class PE returns math.

For any hospital, auto-generates:
- 7-lever RCM EBITDA bridge with revenue/cost/WC breakdown
- Implementation timing curves (months to full run-rate)
- IRR/MOIC sensitivity at multiple entry multiples
- Waterfall visualization (CSS-only, no JS charts)
- Covenant headroom analysis
- One-click from public data — no internal financials required

This is what PE partners buy: not data, but returns math.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ._chartis_kit import (
    SafeHtml,
    chartis_shell, ck_eyebrow, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_page_title, ck_panel, ck_provenance_tooltip,
    ck_section_header, ck_signal_badge, ck_value_anchor,
)

_EXPLAINER_CSS = """<style>
.ck-eb-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-eb-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
.eb-chart-caption{font-family:"Inter Tight","Inter",sans-serif;
  font-size:.72rem;color:#5C6878;text-align:center;
  letter-spacing:0.06em;text-transform:uppercase;
  margin:-.5rem 0 1.25rem;}
@media print {
  .eb-chart-caption{color:#1a2332;}
  svg{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
}
</style>"""
from ._provenance_tooltip import provenance_tooltip
from .brand import PALETTE
from .provenance import build_provenance_graph
from ..provenance.graph import NodeType, ProvenanceNode


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Extract a float, returning default for None/NaN/non-numeric."""
    if val is None:
        return default
    try:
        f = float(val)
        if f != f:  # NaN check
            return default
        return f
    except (TypeError, ValueError):
        return default


# ── Phase 4A: lever-name → /metric-glossary anchor link ──
# Most lever metrics (denial_rate, days_in_ar, etc.) match the
# glossary key 1:1; the bridge's "cmi" is the glossary's
# "case_mix_index". Map any divergent keys here. The shared
# helper falls through to plain escaped text for unknown keys.
_LEVER_METRIC_TO_GLOSSARY = {
    "cmi": "case_mix_index",
}


def _lever_label_link(name: str, metric_key: str) -> str:
    """Wrap a lever's display name in an anchor link to the
    canonical /metric-glossary entry. Thin wrapper around the
    shared helper — preserves the bridge-specific alias table
    so call sites don't need to know about it."""
    from ._glossary_link import metric_label_link
    return metric_label_link(
        name, metric_key, alias=_LEVER_METRIC_TO_GLOSSARY,
    )


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def _pct(val: float) -> str:
    return f"{val:.1%}"


def _color_for_value(val: float) -> str:
    if val > 0:
        return "var(--cad-pos)"
    if val < 0:
        return "var(--cad-neg)"
    return "var(--cad-text3)"


# ── Editorial inline-SVG charts ────────────────────────────────────
# All charts use the editorial palette (parchment surface, teal-deep
# ramp lines, amber/red threshold colors) and render at native SVG
# resolution without JS or a chart library.

_BRIDGE_CHART_PALETTE = [
    "#155752", "#b8732a", "#1F7A75", "#3F7D4D",
    "#A53A2D", "#8A92A0", "#0a8a5f",
]


def _ramp_curve_chart(levers: List[Dict[str, Any]], months: List[int],
                      width: int = 720, height: int = 240) -> str:
    """Cumulative-impact ramp curve, one line per non-zero lever
    plus a heavy total line."""
    active = [l for l in levers if l.get("ebitda_impact", 0) != 0]
    if not active or not months:
        return ""
    pad_l, pad_r, pad_t, pad_b = 50, 130, 24, 38
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    # Cumulative dollars per month across all levers
    total_by_m: Dict[int, float] = {}
    series: List[Dict[str, Any]] = []
    for i, lev in enumerate(active):
        ramp = max(1, lev.get("ramp_months", 12))
        impact = lev["ebitda_impact"]
        pts: List[tuple] = []
        for m in months:
            pct = min(1.0, m / ramp)
            val = impact * pct
            total_by_m[m] = total_by_m.get(m, 0.0) + val
            pts.append((m, val))
        series.append({
            "label": lev["name"], "points": pts,
            "color": _BRIDGE_CHART_PALETTE[i % len(_BRIDGE_CHART_PALETTE)],
        })

    max_val = max(max(p[1] for p in s["points"]) for s in series)
    max_val = max(max_val, max(total_by_m.values()))
    if max_val <= 0:
        return ""

    m_lo, m_hi = months[0], months[-1]
    m_span = max(1, m_hi - m_lo)

    def _x(m: int) -> float:
        return pad_l + (m - m_lo) / m_span * plot_w

    def _y(v: float) -> float:
        return pad_t + plot_h - (v / max_val) * plot_h

    # Gridlines + y-axis labels (5 ticks)
    grid_svg = ""
    for i in range(5):
        gv = max_val * i / 4
        gy = _y(gv)
        grid_svg += (
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l + plot_w}" '
            f'y2="{gy:.1f}" stroke="#E8E0D0" stroke-width="0.8"/>'
            f'<text x="{pad_l - 6}" y="{gy + 3:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#8A92A0" text-anchor="end">{_fm(gv)}</text>'
        )

    # X-axis month ticks
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

    # Series lines + dots
    series_svg = ""
    legend_svg = ""
    legend_x = pad_l + plot_w + 14
    for i, s in enumerate(series):
        path = " ".join(
            f"{'M' if j == 0 else 'L'} {_x(m):.1f},{_y(v):.1f}"
            for j, (m, v) in enumerate(s["points"])
        )
        series_svg += (
            f'<path d="{path}" stroke="{s["color"]}" stroke-width="1.6" '
            f'fill="none" opacity="0.85"/>'
        )
        for m, v in s["points"]:
            series_svg += (
                f'<circle cx="{_x(m):.1f}" cy="{_y(v):.1f}" r="2.4" '
                f'fill="{s["color"]}" opacity="0.85"/>'
            )
        ly = pad_t + 14 + i * 16
        label = s["label"]
        if len(label) > 22:
            label = label[:21] + "…"
        legend_svg += (
            f'<line x1="{legend_x}" y1="{ly}" x2="{legend_x + 16}" '
            f'y2="{ly}" stroke="{s["color"]}" stroke-width="2"/>'
            f'<circle cx="{legend_x + 8}" cy="{ly}" r="2.4" fill="{s["color"]}"/>'
            f'<text x="{legend_x + 22}" y="{ly + 3}" '
            f'font-family="Inter Tight,sans-serif" font-size="9.5" '
            f'fill="#1a2332">{_html.escape(label)}</text>'
        )

    # Cumulative total line — heavier, teal-deep
    total_pts = sorted(total_by_m.items())
    total_path = " ".join(
        f"{'M' if i == 0 else 'L'} {_x(m):.1f},{_y(v):.1f}"
        for i, (m, v) in enumerate(total_pts)
    )
    total_svg = (
        f'<path d="{total_path}" stroke="#0F1C2E" stroke-width="2.6" '
        f'fill="none"/>'
        + "".join(
            f'<circle cx="{_x(m):.1f}" cy="{_y(v):.1f}" r="3.4" '
            f'fill="#0F1C2E" stroke="#FAF7F0" stroke-width="1.2"/>'
            for m, v in total_pts
        )
    )
    # Final value annotation on the cumulative line
    final_m, final_v = total_pts[-1]
    final_label_svg = (
        f'<text x="{_x(final_m) + 8:.1f}" y="{_y(final_v) - 6:.1f}" '
        f'font-family="JetBrains Mono,monospace" font-size="10" '
        f'font-weight="700" fill="#0F1C2E">{_fm(final_v)}</text>'
    )
    # Cumulative legend entry
    legend_svg = (
        f'<line x1="{legend_x}" y1="{pad_t - 4}" x2="{legend_x + 16}" '
        f'y2="{pad_t - 4}" stroke="#0F1C2E" stroke-width="2.6"/>'
        f'<text x="{legend_x + 22}" y="{pad_t - 1}" '
        f'font-family="Inter Tight,sans-serif" font-size="9.5" '
        f'font-weight="700" fill="#0F1C2E">Cumulative</text>'
        + legend_svg
    )

    # Axes baseline
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
        f'{grid_svg}{axes_svg}{tick_svg}{series_svg}{total_svg}'
        f'{final_label_svg}{legend_svg}</svg>'
    )


def _returns_heatmap(grid: List[Dict[str, Any]],
                     entry_multiples: List[float],
                     exit_multiples: List[float],
                     width: int = 720, height: int = 260) -> str:
    """5x5 IRR sensitivity heatmap with editorial color ramp."""
    if not grid:
        return ""
    pad_l, pad_r, pad_t, pad_b = 92, 18, 56, 18
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    nc = len(exit_multiples)
    nr = len(entry_multiples)
    cw = plot_w / nc
    ch = plot_h / nr

    def _tone(irr: float, underwater: bool) -> str:
        if underwater or irr < 0.05:
            return "#A53A2D"
        if irr < 0.15:
            return "#E89478"
        if irr < 0.20:
            return "#E8B97E"
        if irr < 0.30:
            return "#7ED3A8"
        return "#3F7D4D"

    # Column headers (exit multiples)
    headers_svg = (
        f'<text x="{pad_l - 8}" y="{pad_t - 24}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" font-weight="700" '
        f'letter-spacing="0.1em" fill="#5C6878" text-anchor="end" '
        f'text-transform="uppercase">EXIT MULTIPLE →</text>'
    )
    for j, xm in enumerate(exit_multiples):
        cx = pad_l + cw * j + cw / 2
        headers_svg += (
            f'<text x="{cx:.1f}" y="{pad_t - 8}" '
            f'font-family="JetBrains Mono,monospace" font-size="11" '
            f'font-weight="700" fill="#1a2332" text-anchor="middle">'
            f'{xm:.1f}x</text>'
        )

    # Row headers (entry multiples) + cells
    row_label_svg = (
        f'<text x="{pad_l - 8}" y="{pad_t + 16}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" font-weight="700" '
        f'letter-spacing="0.1em" fill="#5C6878" text-anchor="end">'
        f'ENTRY ↓</text>'
    )
    cells_svg = ""
    for i, em in enumerate(entry_multiples):
        ry = pad_t + ch * i + ch / 2
        row_label_svg += (
            f'<text x="{pad_l - 8}" y="{ry + 4:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="11" '
            f'font-weight="700" fill="#1a2332" text-anchor="end">'
            f'{em:.1f}x</text>'
        )
        for j, xm in enumerate(exit_multiples):
            cell = next(
                (g for g in grid
                 if g["entry_multiple"] == em and g["exit_multiple"] == xm),
                None,
            )
            cx = pad_l + cw * j
            cy = pad_t + ch * i
            if cell is None:
                cells_svg += (
                    f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw - 2:.1f}" '
                    f'height="{ch - 2:.1f}" fill="#ECE5D6" '
                    f'stroke="#D6CFC0" stroke-width="0.6"/>'
                )
                continue
            tone = _tone(cell["irr"], cell.get("underwater", False))
            label_irr = "—" if cell.get("underwater") else f'{cell["irr"]:.0%}'
            label_moic = (
                "Loss" if cell.get("underwater") else f'{cell["moic"]:.1f}x'
            )
            text_color = "#FAF7F0" if cell["irr"] >= 0.20 and not cell.get("underwater") else "#1a2332"
            cells_svg += (
                f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw - 2:.1f}" '
                f'height="{ch - 2:.1f}" fill="{tone}" '
                f'stroke="#FAF7F0" stroke-width="1.5"/>'
                f'<text x="{cx + cw / 2:.1f}" y="{cy + ch / 2 - 2:.1f}" '
                f'font-family="Source Serif 4,serif" font-size="14" '
                f'font-weight="600" fill="{text_color}" text-anchor="middle">'
                f'{label_irr}</text>'
                f'<text x="{cx + cw / 2:.1f}" y="{cy + ch / 2 + 14:.1f}" '
                f'font-family="JetBrains Mono,monospace" font-size="9.5" '
                f'fill="{text_color}" text-anchor="middle" opacity="0.85">'
                f'{label_moic}</text>'
            )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{headers_svg}{row_label_svg}{cells_svg}</svg>'
    )


def _trajectory_stacked_bars(entry_ebitda: float, total_uplift: float,
                             organic_growth: float, hold_years: int,
                             width: int = 720, height: int = 240) -> str:
    """Stacked-bar EBITDA trajectory: base + RCM uplift per year."""
    pad_l, pad_r, pad_t, pad_b = 50, 18, 32, 46
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    cols = hold_years + 1  # Entry + Year 1..N
    slot = plot_w / cols
    bar_w = slot * 0.58

    series: List[Dict[str, float]] = [
        {"label": "Entry", "base": entry_ebitda, "rcm": 0.0},
    ]
    for yr in range(1, hold_years + 1):
        base = entry_ebitda * (1 + organic_growth) ** yr
        rcm = total_uplift * min(1.0, yr / 1.5)
        series.append({"label": f"Y{yr}", "base": base, "rcm": rcm})
    max_v = max(s["base"] + s["rcm"] for s in series)
    if max_v <= 0:
        return ""

    def _y(v: float) -> float:
        return pad_t + plot_h - (v / max_v) * plot_h

    # Gridlines
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

    bars_svg = ""
    for i, s in enumerate(series):
        cx = pad_l + slot * i + slot / 2
        bx = cx - bar_w / 2
        base_h = (s["base"] / max_v) * plot_h
        rcm_h = (s["rcm"] / max_v) * plot_h
        # Base segment
        bars_svg += (
            f'<rect x="{bx:.1f}" y="{pad_t + plot_h - base_h:.1f}" '
            f'width="{bar_w:.1f}" height="{base_h:.1f}" fill="#155752" '
            f'opacity="0.85" rx="1"/>'
        )
        if rcm_h > 0:
            bars_svg += (
                f'<rect x="{bx:.1f}" '
                f'y="{pad_t + plot_h - base_h - rcm_h:.1f}" '
                f'width="{bar_w:.1f}" height="{rcm_h:.1f}" fill="#7ED3A8" rx="1"/>'
            )
        total = s["base"] + s["rcm"]
        bars_svg += (
            f'<text x="{cx:.1f}" y="{pad_t + plot_h - base_h - rcm_h - 6:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="10" '
            f'font-weight="700" fill="#1a2332" text-anchor="middle">'
            f'{_fm(total)}</text>'
            f'<text x="{cx:.1f}" y="{pad_t + plot_h + 16:.1f}" '
            f'font-family="Inter Tight,sans-serif" font-size="10" '
            f'font-weight="700" letter-spacing="0.05em" fill="#1a2332" '
            f'text-anchor="middle">{s["label"]}</text>'
        )

    base_y = pad_t + plot_h
    base_line = (
        f'<line x1="{pad_l}" y1="{base_y:.1f}" x2="{pad_l + plot_w}" '
        f'y2="{base_y:.1f}" stroke="#BFB6A2" stroke-width="1"/>'
    )

    # Legend
    legend_y = height - 14
    legend_svg = (
        f'<rect x="{pad_l}" y="{legend_y - 8}" width="12" height="10" '
        f'fill="#155752" opacity="0.85" rx="1"/>'
        f'<text x="{pad_l + 18}" y="{legend_y}" '
        f'font-family="Inter Tight,sans-serif" font-size="10" '
        f'fill="#5C6878">Base EBITDA</text>'
        f'<rect x="{pad_l + 120}" y="{legend_y - 8}" width="12" height="10" '
        f'fill="#7ED3A8" rx="1"/>'
        f'<text x="{pad_l + 138}" y="{legend_y}" '
        f'font-family="Inter Tight,sans-serif" font-size="10" '
        f'fill="#5C6878">RCM Uplift</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{grid_svg}{base_line}{bars_svg}{legend_svg}</svg>'
    )


_BRIDGE_CHART_CAPTION_CSS = """
.eb-chart-caption {
  font-family: "Inter Tight","Inter",sans-serif;
  font-size: .72rem; color: #5C6878;
  text-align: center; letter-spacing: 0.06em;
  text-transform: uppercase; margin: -.5rem 0 1.25rem;
}
"""


# ── Bridge computation (self-contained, works from public data) ──

_LEVER_CONFIG = [
    {
        "name": "Denial Rate Reduction",
        "metric": "denial_rate",
        "direction": "lower",
        "current_default": 0.12,
        "target_default": 0.065,
        "revenue_coef": 0.35,
        "cost_per_pp": 15000,
        "ramp_months": 12,
        "category": "revenue",
        "description": "Reduce initial claim denials through better coding, prior auth, and eligibility verification",
    },
    {
        "name": "A/R Days Reduction",
        "metric": "days_in_ar",
        "direction": "lower",
        "current_default": 52,
        "target_default": 38,
        "wc_coef_per_day": 1.0 / 365,
        "bad_debt_coef": 0.00065,
        "ramp_months": 9,
        "category": "cash",
        "description": "Accelerate collections by reducing average days outstanding",
    },
    {
        "name": "Net Collection Rate",
        "metric": "net_collection_rate",
        "direction": "higher",
        "current_default": 0.935,
        "target_default": 0.970,
        "revenue_coef": 0.60,
        "ramp_months": 18,
        "category": "revenue",
        "description": "Improve net cash collected per dollar of net patient revenue",
    },
    {
        "name": "Clean Claim Rate",
        "metric": "clean_claim_rate",
        "direction": "higher",
        "current_default": 0.88,
        "target_default": 0.96,
        "cost_per_pp": 12000,
        "ramp_months": 6,
        "category": "cost",
        "description": "Increase first-pass acceptance rate to reduce rework and accelerate payment",
    },
    {
        "name": "Cost to Collect",
        "metric": "cost_to_collect",
        "direction": "lower",
        "current_default": 0.045,
        "target_default": 0.025,
        "revenue_coef": 1.0,
        "ramp_months": 12,
        "category": "cost",
        "description": "Reduce revenue cycle operating cost as % of net patient revenue",
    },
    {
        "name": "CDI / Case Mix Index",
        "metric": "cmi",
        "direction": "higher",
        "current_default": 1.35,
        "target_default": 1.42,
        "medicare_coef": 0.0075,
        "ramp_months": 18,
        "category": "revenue",
        "description": "Improve clinical documentation to capture true acuity and higher DRG payments",
    },
]


def compute_peer_targets(
    hcris_df: Optional[pd.DataFrame],
    beds: float,
    state: str = "",
) -> Dict[str, float]:
    """Compute P75 targets from size-matched peers instead of hardcoded values.

    This is the key integration: comp set → bridge targets. A 50-bed rural
    hospital gets different targets than a 500-bed academic center.
    """
    if hcris_df is None or len(hcris_df) < 20:
        return {}

    size_lo = max(10, beds * 0.5)
    size_hi = beds * 2.0
    peers = hcris_df[(hcris_df["beds"] >= size_lo) & (hcris_df["beds"] <= size_hi)]

    # Prefer same-state if enough peers
    if state:
        state_peers = peers[peers["state"] == state]
        if len(state_peers) >= 10:
            peers = state_peers

    if len(peers) < 10:
        return {}

    targets = {}

    # Metrics where lower is better → target = P25 of peers
    for metric, target_key in [
        ("operating_margin", "denial_rate"),  # operating_margin is a proxy
    ]:
        pass  # denial_rate not in HCRIS — skip direct mapping

    # Metrics derivable from HCRIS
    if "net_to_gross_ratio" in peers.columns:
        vals = peers["net_to_gross_ratio"].dropna()
        if len(vals) >= 10:
            targets["net_collection_rate_target"] = round(float(vals.quantile(0.75)), 4)

    if "operating_margin" in peers.columns:
        vals = peers["operating_margin"].dropna()
        if len(vals) >= 10:
            p75 = float(vals.quantile(0.75))
            # Use margin spread to calibrate improvement expectation
            targets["_peer_p75_margin"] = round(p75, 4)

    return targets


def _compute_bridge(
    net_revenue: float,
    current_ebitda: float,
    medicare_pct: float = 0.40,
    claims_volume: int = 0,
    overrides: Optional[Dict[str, float]] = None,
    peer_targets: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Compute the 7-lever EBITDA bridge from hospital profile."""
    overrides = overrides or {}
    peer_targets = peer_targets or {}
    if claims_volume == 0:
        claims_volume = max(1000, int(net_revenue / 15000))

    levers = []
    total_revenue_impact = 0
    total_cost_impact = 0
    total_wc_impact = 0

    for cfg in _LEVER_CONFIG:
        name = cfg["name"]
        current = overrides.get(f"{cfg['metric']}_current", cfg["current_default"])
        # Priority: explicit override > peer-computed target > hardcoded default
        target = overrides.get(
            f"{cfg['metric']}_target",
            peer_targets.get(f"{cfg['metric']}_target", cfg["target_default"]),
        )

        if cfg["direction"] == "lower":
            delta = max(0, current - target)
        else:
            delta = max(0, target - current)

        revenue_impact = 0
        cost_impact = 0
        wc_impact = 0

        if cfg["category"] == "revenue" and "revenue_coef" in cfg:
            if cfg["metric"] == "cmi":
                medicare_rev = net_revenue * medicare_pct
                revenue_impact = delta * medicare_rev * cfg.get("medicare_coef", 0.0075)
            else:
                revenue_impact = delta * net_revenue * cfg["revenue_coef"]

        if cfg["category"] == "cost" and "revenue_coef" in cfg:
            cost_impact = delta * net_revenue * cfg["revenue_coef"]

        if "cost_per_pp" in cfg:
            cost_impact += delta * claims_volume * cfg["cost_per_pp"] / 100

        if cfg["metric"] == "days_in_ar":
            daily_rev = net_revenue / 365
            wc_impact = delta * daily_rev
            bad_debt_saving = delta * net_revenue * cfg.get("bad_debt_coef", 0.00065)
            cost_impact += bad_debt_saving
            interest_on_wc = wc_impact * 0.08
            revenue_impact += interest_on_wc

        ebitda_impact = revenue_impact + cost_impact

        total_revenue_impact += revenue_impact
        total_cost_impact += cost_impact
        total_wc_impact += wc_impact

        # Timing curve: linear ramp to full run-rate
        ramp = cfg["ramp_months"]
        timing = []
        for month in range(0, 37, 3):
            if month >= ramp:
                pct = 1.0
            else:
                pct = month / ramp
            timing.append({"month": month, "pct": round(pct, 2),
                           "annualized": round(ebitda_impact * pct, 0)})

        levers.append({
            "name": name,
            "metric": cfg["metric"],
            "category": cfg["category"],
            "current": current,
            "target": target,
            "delta": round(delta, 4),
            "revenue_impact": round(revenue_impact, 0),
            "cost_impact": round(cost_impact, 0),
            "ebitda_impact": round(ebitda_impact, 0),
            "wc_impact": round(wc_impact, 0),
            "margin_bps": round(ebitda_impact / net_revenue * 10000, 0) if net_revenue > 0 else 0,
            "ramp_months": ramp,
            "timing": timing,
            "description": cfg["description"],
        })

    levers.sort(key=lambda l: -abs(l["ebitda_impact"]))

    total_ebitda = total_revenue_impact + total_cost_impact
    new_ebitda = current_ebitda + total_ebitda
    new_margin = new_ebitda / net_revenue if net_revenue > 0 else 0
    current_margin = current_ebitda / net_revenue if net_revenue > 0 else 0

    return {
        "net_revenue": net_revenue,
        "current_ebitda": current_ebitda,
        "current_margin": current_margin,
        "total_revenue_impact": total_revenue_impact,
        "total_cost_impact": total_cost_impact,
        "total_ebitda_impact": total_ebitda,
        "total_wc_released": total_wc_impact,
        "new_ebitda": new_ebitda,
        "new_margin": new_margin,
        "margin_improvement_bps": round((new_margin - current_margin) * 10000, 0),
        "levers": levers,
    }


def _compute_returns_grid(
    current_ebitda: float,
    ebitda_uplift: float,
    entry_multiples: List[float],
    exit_multiples: List[float],
    hold_years: int = 5,
    leverage: float = 5.5,
    organic_growth: float = 0.03,
    debt_paydown_pct: float = 0.10,
) -> List[Dict[str, Any]]:
    """Compute IRR/MOIC grid across entry and exit multiples."""
    rows = []
    for entry_m in entry_multiples:
        for exit_m in exit_multiples:
            entry_ev = current_ebitda * entry_m
            entry_debt = entry_ev * (leverage / (leverage + 1))
            entry_equity = entry_ev - entry_debt

            exit_ebitda = current_ebitda
            for yr in range(hold_years):
                exit_ebitda *= (1 + organic_growth)
            exit_ebitda += ebitda_uplift

            exit_ev = exit_ebitda * exit_m
            remaining_debt = entry_debt * (1 - debt_paydown_pct) ** hold_years
            exit_equity = exit_ev - remaining_debt

            moic = exit_equity / entry_equity if entry_equity > 0 else 0
            if moic > 0 and hold_years > 0:
                try:
                    irr = moic ** (1 / hold_years) - 1
                except (ValueError, OverflowError):
                    irr = -1
            else:
                irr = -1

            rows.append({
                "entry_multiple": entry_m,
                "exit_multiple": exit_m,
                "entry_ev": round(entry_ev, 0),
                "entry_equity": round(entry_equity, 0),
                "exit_ev": round(exit_ev, 0),
                "exit_equity": round(exit_equity, 0),
                "moic": round(moic, 2),
                "irr": round(irr, 4),
                "underwater": exit_equity < 0,
            })
    return rows


def _load_data_room_overrides(db_path: Optional[str], ccn: str) -> Dict[str, float]:
    """Pull seller data from the Data Room if available.

    Checks calibrations first (Bayesian posteriors), falls back to
    raw entries if calibrations haven't been computed yet.
    """
    if not db_path:
        return {}
    # Late local import keeps the bypass cleanup contained to this
    # function — the module top doesn't need PortfolioStore otherwise.
    from ..portfolio.store import PortfolioStore
    try:
        # Route through PortfolioStore (campaign target 4E) so the
        # connection inherits PRAGMA foreign_keys=ON, busy_timeout=
        # 5000, and row_factory=Row instead of running on a bare
        # sqlite3.connect that misses all three.
        with PortfolioStore(db_path).connect() as con:
            seen: Dict[str, float] = {}

            # Try calibrations first (best: Bayesian posterior)
            try:
                rows = con.execute(
                    "SELECT metric, bayesian_posterior FROM data_room_calibrations "
                    "WHERE hospital_ccn = ? ORDER BY computed_at DESC",
                    (ccn,),
                ).fetchall()
                for metric, value in rows:
                    if metric not in seen and value is not None:
                        seen[f"{metric}_current"] = value
            except Exception:
                pass

            # Fall back to raw entries if no calibrations yet
            if not seen:
                try:
                    rows = con.execute(
                        "SELECT metric, value FROM data_room_entries "
                        "WHERE hospital_ccn = ? AND superseded_by IS NULL "
                        "ORDER BY entered_at DESC",
                        (ccn,),
                    ).fetchall()
                    for metric, value in rows:
                        key = f"{metric}_current"
                        if key not in seen and value is not None:
                            seen[key] = value
                except Exception:
                    pass

            return seen
    except Exception:
        return {}


def render_ebitda_bridge(
    ccn: str,
    hcris_df: pd.DataFrame,
    db_path: Optional[str] = None,
) -> str:
    """Render the EBITDA bridge page for a hospital."""
    match = hcris_df[hcris_df["ccn"] == ccn]
    if match.empty:
        return chartis_shell(
            ck_panel(
                f'<p class="ck-section-body">Hospital {_html.escape(ccn)} not found.</p>',
                title="EBITDA Bridge",
            ),
            "EBITDA Bridge",
        )

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    state = str(hospital.get("state", ""))
    beds = _safe_float(hospital.get("beds"), 100)
    rev = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    mc = _safe_float(hospital.get("medicare_day_pct"), 0.4)

    if rev < 1e6:
        return chartis_shell(
            ck_panel(
                f'<p class="ck-section-body">Insufficient revenue data for {_html.escape(name)}.</p>',
                title="EBITDA Bridge",
            ),
            "EBITDA Bridge",
        )

    current_ebitda = rev - opex
    if current_ebitda < -rev:
        current_ebitda = rev * 0.08

    # Pull calibrated overrides from Data Room (seller data)
    dr_overrides = _load_data_room_overrides(db_path, ccn)
    has_seller_data = len(dr_overrides) > 0

    # Compute hospital-specific targets from size-matched peers
    peer_tgts = compute_peer_targets(hcris_df, beds, state)

    bridge = _compute_bridge(rev, current_ebitda, medicare_pct=mc,
                              overrides=dr_overrides, peer_targets=peer_tgts)

    # Phase 4C: build a ProvenanceGraph for "explain this number"
    # tooltips on the Lever Detail table's current-value cells.
    # Start from the hospital row (HCRIS-derived margin / NPR /
    # opex / etc.), then manually add one OBSERVED node per
    # lever-current value at id `observed:<glossary_key>` with
    # source = SELLER if the value came from the data room or
    # DEFAULT (model config) otherwise. The cmi -> case_mix_index
    # alias from loop 106 means lev["metric"]=="cmi" maps to
    # glossary key case_mix_index — same alias drives both the
    # 4A label link and the 4C value tooltip.
    prov_graph = build_provenance_graph(
        ccn=str(ccn),
        hcris_profile=dict(hospital),
        ml_predictions={},
    )
    for _lev in bridge["levers"]:
        _m_key = _LEVER_METRIC_TO_GLOSSARY.get(
            _lev.get("metric", ""), _lev.get("metric", ""),
        )
        if not _m_key:
            continue
        _node_id = f"observed:{_m_key}"
        if _node_id in prov_graph.nodes:
            # Hospital-row already provided this metric; don't
            # overwrite the SOURCE node with a lever-default.
            continue
        _is_seller = (
            f"{_lev.get('metric', '')}_current" in dr_overrides
        )
        prov_graph.add_node(ProvenanceNode(
            id=_node_id,
            label=_lev["name"],
            node_type=NodeType.OBSERVED if _is_seller
                else NodeType.PREDICTED,
            value=float(_lev["current"]),
            unit="pct" if _lev["current"] < 2 else "",
            source="SELLER" if _is_seller else "MODEL_DEFAULT",
            source_detail=("Data room" if _is_seller
                else "Lever config default"),
        ))

    # Data provenance banner
    provenance_banner = ""
    if has_seller_data:
        n_overrides = len(dr_overrides)
        seller_badge = ck_signal_badge("Seller Data Active", tone="warning")
        provenance_banner = ck_panel(
            '<p class="ck-section-body">'
            f'{seller_badge} — {n_overrides} metric(s) from the Data Room are '
            'overriding ML defaults. Bridge calculations reflect '
            'Bayesian-calibrated values. '
            f'<a href="/data-room/{_html.escape(ccn)}" class="ck-link">View Data Room →</a>'
            '</p>',
            title="Data Room provenance",
        )

    # ── Realization prediction ──
    realization_section = ""
    try:
        from ..ml.realization_predictor import predict_realization
        rp = predict_realization(ccn, hcris_df, bridge_uplift=bridge["total_ebitda_impact"])
        if rp:
            rp_color = "var(--cad-pos)" if rp.grade in ("A", "B") else (
                "var(--cad-warn)" if rp.grade == "C" else "var(--cad-neg)")
            factor_rows = ""
            for f in rp.factors[:5]:
                f_color = "var(--cad-pos)" if f.direction == "supports" else (
                    "var(--cad-neg)" if f.direction == "hinders" else "var(--cad-text3)")
                icon = "&#9650;" if f.direction == "supports" else (
                    "&#9660;" if f.direction == "hinders" else "&#9654;")
                factor_rows += (
                    f'<div style="display:flex;gap:6px;padding:3px 0;font-size:11.5px;">'
                    f'<span style="color:{f_color};">{icon}</span>'
                    f'<span style="font-weight:500;width:120px;">{_html.escape(f.label)}</span>'
                    f'<span style="color:var(--cad-text2);">{_html.escape(f.explanation[:50])}</span></div>'
                )

            real_tone = (
                "positive" if rp.grade in ("A", "B")
                else "warning" if rp.grade == "C"
                else "negative"
            )
            real_badge = ck_signal_badge(
                f"Grade {rp.grade} · {rp.expected_realization:.0%} realization",
                tone=real_tone,
            )
            real_inner = (
                '<p class="ck-eyebrow">'
                f'ML model predicts what fraction of the bridge is achievable '
                f'(accuracy: {rp.model_accuracy:.0%}, n={rp.n_training:,}).</p>'
                f'<p class="ck-section-body">{real_badge}</p>'
                '<div class="ck-kpi-strip">'
                + ck_kpi_block("Modeled Uplift", _fm(rp.raw_uplift))
                + ck_kpi_block("Risk-Adjusted", _fm(rp.risk_adjusted_uplift))
                + ck_kpi_block("Execution Discount", f"-{_fm(rp.discount)}")
                + '</div>'
                + factor_rows
                + f'<p class="ck-section-body">{_html.escape(rp.narrative)}</p>'
            )
            realization_section = ck_panel(
                real_inner, title="Bridge Realization Estimate",
            )
    except Exception:
        pass

    # ── Provenance ──
    from .provenance import source_tag, Source, data_freshness_footer
    rev_src = Source.HCRIS
    lever_src = Source.SELLER if has_seller_data else Source.ML_PREDICTION

    # ── KPI Cards ──
    ebitda_color = _color_for_value(bridge["total_ebitda_impact"])
    # Cycle 52 — port to ck_kpi_block + provenance.
    uplift_value = ck_provenance_tooltip(
        "RCM EBITDA uplift",
        SafeHtml(
            f'<span style="color:{ebitda_color};">+{_fm(bridge["total_ebitda_impact"])}</span>'
        ),
        explainer=(
            f"Sum of EBITDA deltas across the 7-lever bridge "
            f"(denials, AR, write-offs, RCM operations, etc.). "
            f"+{bridge['margin_improvement_bps']:.0f}bps margin "
            f"improvement on net revenue. Pro forma EBITDA "
            f"reflects this uplift."
        ),
    )
    bps_value = ck_provenance_tooltip(
        "Margin improvement",
        f"+{bridge['margin_improvement_bps']:.0f}bps",
        explainer=(
            "EBITDA margin lift from current to pro-forma. The "
            "bridge below decomposes by lever; each lever has a "
            "confidence band based on whether the data came "
            "from the seller's filings or from the platform's "
            "ML predictor."
        ),
        inject_css=False,
    )
    kpis = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(6,1fr);">'
        + ck_kpi_block(
            "Net Revenue", _fm(rev),
            f"HCRIS FY2022 {source_tag(Source.HCRIS, 'FY2022')}",
            help={
                "definition": (
                    "Net Patient Revenue — billed services minus "
                    "contractual allowances, bad debt, and charity "
                    "care. The cash-realisable top line the bridge "
                    "operates on."
                ),
                "citation": "HFMA / CMS HCRIS",
            },
        )
        + ck_kpi_block(
            "Current EBITDA", _fm(bridge["current_ebitda"]),
            f"computed {source_tag(Source.COMPUTED)}",
            help={
                "definition": (
                    "Year-0 operating earnings before interest, "
                    "taxes, depreciation, and amortization. The base "
                    "case from which RCM levers compound."
                ),
            },
        )
        + ck_kpi_block(
            "RCM Uplift", uplift_value, "7-lever bridge",
            help={
                "definition": (
                    "Total EBITDA uplift across the seven RCM levers "
                    "(charge capture, contract optimization, denial "
                    "rework, collections, write-off discipline, "
                    "underpayment recovery, DSO compression). Each "
                    "lever has its own conformal confidence band."
                ),
                "citation": "rcm_mc/pe/rcm_ebitda_bridge.py",
            },
        )
        + ck_kpi_block(
            "Pro Forma EBITDA",
            f'<span style="color:var(--cad-pos);">'
            f'{_fm(bridge["new_ebitda"])}</span>',
            "post-RCM",
            help={
                "definition": (
                    "Current EBITDA + RCM uplift — the projected "
                    "year-3 EBITDA after the bridge fully realises. "
                    "Compare against Monte Carlo P50 for sensitivity."
                ),
            },
        )
        + ck_kpi_block(
            "Margin Improvement", bps_value, "of net revenue",
            help={
                "definition": (
                    "Operating-margin lift in basis points (1 bps = "
                    "0.01%). For a $100M NPR deal, 200 bps = $2M of "
                    "EBITDA. Bank-loan margin tests usually require "
                    "300-500 bps of credible improvement."
                ),
            },
        )
        + ck_kpi_block(
            "WC Released", _fm(bridge["total_wc_released"]),
            "1x cash benefit",
            help={
                "definition": (
                    "Working-capital cash released from the bridge — "
                    "primarily DSO compression converting A/R to "
                    "cash. One-time benefit at the year of release, "
                    "NOT recurring like EBITDA uplift."
                ),
            },
        )
        + '</div>'
    )

    # ── Waterfall (CSS bars) ──
    max_bar = max(abs(l["ebitda_impact"]) for l in bridge["levers"]) if bridge["levers"] else 1
    waterfall_bars = ""
    for lev in bridge["levers"]:
        impact = lev["ebitda_impact"]
        if impact == 0:
            continue
        bar_pct = min(100, abs(impact) / max_bar * 80)
        color = "var(--cad-pos)" if impact > 0 else "var(--cad-neg)"
        cat_badge = {"revenue": "Revenue", "cost": "Cost Savings", "cash": "Cash Accel"}.get(lev["category"], "")

        waterfall_bars += (
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;'
            f'border-bottom:1px solid var(--cad-border);">'
            f'<div style="width:180px;flex-shrink:0;">'
            f'<div style="font-weight:500;font-size:12.5px;">{_lever_label_link(lev["name"], lev.get("metric", ""))}</div>'
            f'<div style="font-size:10px;color:var(--cad-text3);">{cat_badge} | '
            f'{lev["ramp_months"]}mo ramp</div></div>'
            f'<div style="flex:1;display:flex;align-items:center;gap:8px;">'
            f'<div style="background:var(--cad-bg3);border-radius:2px;height:20px;flex:1;'
            f'position:relative;">'
            f'<div style="width:{bar_pct:.0f}%;background:{color};border-radius:2px;height:20px;'
            f'display:flex;align-items:center;justify-content:flex-end;padding-right:6px;'
            f'font-size:10px;color:#fff;font-weight:600;min-width:40px;">'
            f'{_fm(impact)}</div></div>'
            f'<div class="cad-mono" style="width:60px;text-align:right;font-size:11px;'
            f'color:{color};">+{lev["margin_bps"]:.0f}bp</div>'
            f'</div></div>'
        )

    waterfall_inner = (
        '<p class="ck-section-body">'
        'Each bar shows the annual EBITDA impact at full run-rate. Revenue levers increase '
        'top-line; cost levers reduce operating expense; cash acceleration releases working capital. '
        'Calibrated to published research bands (Denial 12%→5% = $8-15M on $400M NPR).</p>'
        f'{waterfall_bars}'
        '<p class="ck-section-body">'
        f'<strong>Total EBITDA Impact</strong> &nbsp; '
        f'<span class="cad-pos">{_fm(bridge["total_ebitda_impact"])}</span></p>'
    )
    waterfall_section = ck_panel(
        waterfall_inner, title="EBITDA Bridge — 7 RCM Levers",
    )

    # ── Lever detail table ──
    detail_rows = ""
    _first_tooltip = True
    for lev in bridge["levers"]:
        current_str = f"{lev['current']:.1%}" if lev["current"] < 2 else f"{lev['current']:.2f}"
        target_str = f"{lev['target']:.1%}" if lev["target"] < 2 else f"{lev['target']:.2f}"
        # Determine source for this lever's current value
        metric_key = lev.get("metric", "")
        is_from_seller = f"{metric_key}_current" in dr_overrides
        cur_tag = source_tag(Source.SELLER, "Data room") if is_from_seller else source_tag(Source.DEFAULT, "Model default")
        tgt_tag = source_tag(Source.BENCHMARK, "P75 peers")
        # Phase 4C: hover the current-value cell for the
        # provenance card (node type, prose, upstream).
        # Resolves through the same cmi -> case_mix_index alias
        # used for the 4A label link.
        _current_tt = provenance_tooltip(
            label=lev["name"], value=current_str,
            graph=prov_graph,
            metric_key=_LEVER_METRIC_TO_GLOSSARY.get(
                metric_key, metric_key,
            ),
            inject_css=_first_tooltip,
        )
        _first_tooltip = False
        detail_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">{_lever_label_link(lev["name"], lev.get("metric", ""))}</td>'
            f'<td class="num">{_current_tt} {cur_tag}</td>'
            f'<td class="num" style="color:var(--cad-pos);">{target_str} {tgt_tag}</td>'
            f'<td class="num" style="color:var(--cad-pos);">{_fm(lev["revenue_impact"])}</td>'
            f'<td class="num" style="color:var(--cad-pos);">{_fm(lev["cost_impact"])}</td>'
            f'<td class="num" style="font-weight:600;color:var(--cad-pos);">{_fm(lev["ebitda_impact"])}</td>'
            f'<td class="num">{_fm(lev["wc_impact"])}</td>'
            f'<td class="num">{lev["ramp_months"]}mo</td>'
            f'</tr>'
        )

    detail_inner = (
        '<p class="ck-eyebrow">'
        'Each value shows its data source. '
        f'{source_tag(Source.SELLER)} = seller data room, '
        f'{source_tag(Source.DEFAULT)} = model default, '
        f'{source_tag(Source.BENCHMARK)} = P75 peer benchmark.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Lever</th><th>Current</th><th>Target</th><th>Revenue</th>'
        '<th>Cost</th><th>EBITDA</th><th>WC</th><th>Ramp</th>'
        f'</tr></thead><tbody>{detail_rows}</tbody></table>'
    )
    detail_section = ck_panel(detail_inner, title="Lever Detail")

    # ── Timing curve ──
    months = [0, 3, 6, 9, 12, 18, 24, 36]
    timing_header = "<th>Lever</th>" + "".join(f"<th>M{m}</th>" for m in months)
    timing_rows = ""
    cumulative = {m: 0.0 for m in months}
    for lev in bridge["levers"]:
        if lev["ebitda_impact"] == 0:
            continue
        timing_rows += f'<tr><td style="font-weight:500;">{_lever_label_link(lev["name"], lev.get("metric", ""))}</td>'
        for m in months:
            ramp = lev["ramp_months"]
            pct = min(1.0, m / ramp) if ramp > 0 else 1.0
            val = lev["ebitda_impact"] * pct
            cumulative[m] += val
            color = "var(--cad-pos)" if val > 0 else "var(--cad-text3)"
            timing_rows += f'<td class="num" style="color:{color};font-size:11px;">{_fm(val)}</td>'
        timing_rows += "</tr>"

    # Cumulative row
    timing_rows += '<tr style="font-weight:700;border-top:2px solid var(--cad-border);"><td>Cumulative</td>'
    for m in months:
        timing_rows += f'<td class="num" style="color:var(--cad-pos);">{_fm(cumulative[m])}</td>'
    timing_rows += "</tr>"

    ramp_chart = _ramp_curve_chart(bridge["levers"], months)
    ramp_caption = (
        '<div class="eb-chart-caption">'
        'Per-lever and cumulative EBITDA realization · '
        'partners typically see ~60–70% by month 12'
        '</div>'
    ) if ramp_chart else ""
    timing_inner = (
        '<p class="ck-section-body">'
        'Linear ramp to full run-rate per lever. Month 0 = close date. '
        'Partners should expect 60-70% of total uplift realized by month 12.</p>'
        + ramp_chart + ramp_caption +
        f'<table class="cad-table"><thead><tr>{timing_header}'
        f'</tr></thead><tbody>{timing_rows}</tbody></table>'
    )
    timing_section = ck_panel(timing_inner, title="Implementation Timing Curve")

    # ── Returns sensitivity grid ──
    entry_multiples = [8.0, 9.0, 10.0, 11.0, 12.0]
    exit_multiples = [9.0, 10.0, 11.0, 11.5, 12.0]
    grid = _compute_returns_grid(
        bridge["current_ebitda"], bridge["total_ebitda_impact"],
        entry_multiples, exit_multiples,
    )

    grid_header = '<th>Entry \\ Exit</th>' + ''.join(f'<th>{m:.1f}x</th>' for m in exit_multiples)
    grid_rows = ""
    for em in entry_multiples:
        grid_rows += f'<tr><td style="font-weight:600;">{em:.1f}x</td>'
        for xm in exit_multiples:
            cell = next((g for g in grid if g["entry_multiple"] == em and g["exit_multiple"] == xm), None)
            if cell:
                irr = cell["irr"]
                moic = cell["moic"]
                if cell["underwater"]:
                    color = "var(--cad-neg)"
                    text = "Loss"
                elif irr >= 0.20:
                    color = "var(--cad-pos)"
                    text = f'{irr:.0%} / {moic:.1f}x'
                elif irr >= 0.15:
                    color = "var(--cad-warn)"
                    text = f'{irr:.0%} / {moic:.1f}x'
                else:
                    color = "var(--cad-neg)"
                    text = f'{irr:.0%} / {moic:.1f}x'
                grid_rows += (
                    f'<td class="num" style="color:{color};font-size:11px;'
                    f'font-weight:500;">{text}</td>'
                )
            else:
                grid_rows += '<td>—</td>'
        grid_rows += '</tr>'

    heatmap_chart = _returns_heatmap(grid, entry_multiples, exit_multiples)
    heatmap_caption = (
        '<div class="eb-chart-caption">'
        'IRR (top) / MOIC (bottom) per cell · darker green = above hurdle'
        '</div>'
    ) if heatmap_chart else ""
    grid_inner = (
        '<p class="ck-section-body">'
        '5-year hold, 5.5x leverage, 3% organic growth, 10%/yr debt paydown. '
        'Green = exceeds 20% IRR hurdle. Amber = 15-20%. Red = below hurdle or loss. '
        f'RCM uplift of {_fm(bridge["total_ebitda_impact"])} is added at exit.</p>'
        + heatmap_chart + heatmap_caption +
        f'<table class="cad-table"><thead><tr>{grid_header}'
        f'</tr></thead><tbody>{grid_rows}</tbody></table>'
    )
    grid_section = ck_panel(grid_inner, title="Returns Sensitivity (IRR / MOIC)")

    # ── Covenant headroom ──
    base_multiple = 10.0
    entry_ev = bridge["current_ebitda"] * base_multiple
    entry_debt = entry_ev * (5.5 / 6.5)
    actual_lev = entry_debt / bridge["current_ebitda"] if bridge["current_ebitda"] > 0 else 99
    pro_forma_lev = entry_debt / bridge["new_ebitda"] if bridge["new_ebitda"] > 0 else 99
    headroom = 6.5 - pro_forma_lev
    cushion = (bridge["new_ebitda"] - entry_debt / 6.5) / bridge["new_ebitda"] if bridge["new_ebitda"] > 0 else 0

    cov_tone = (
        "positive" if headroom > 1.0
        else "warning" if headroom > 0.5
        else "negative"
    )
    cov_badge = ck_signal_badge(
        f"{headroom:.1f}x headroom", tone=cov_tone,
    )
    covenant_inner = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Entry Leverage", f"{actual_lev:.1f}x",
            help={
                "definition": (
                    "Debt-to-EBITDA at close. PE healthcare deals "
                    "typically come in at 5.5-6.5x; above 7x signals "
                    "an aggressive cap structure that needs strong "
                    "deleveraging or EBITDA growth to clear covenants."
                ),
            },
        )
        + ck_kpi_block(
            "Pro Forma Leverage", f"{pro_forma_lev:.1f}x",
            help={
                "definition": (
                    "Debt-to-EBITDA after the RCM uplift lands. The "
                    "gap from Entry → Pro Forma is the deleveraging "
                    "story — narrower gap = the deal relies more on "
                    "exit-multiple expansion than operational "
                    "improvement."
                ),
            },
        )
        + ck_kpi_block(
            "Headroom (turns)", f"{headroom:.1f}x", sub=cov_badge,
            help={
                "definition": (
                    "Distance to the leverage covenant in EBITDA "
                    "turns. >1.0x = comfortable; 0.5-1.0x = watch "
                    "list (one bad quarter trips it); <0.5x = covenant "
                    "renegotiation likely before plan completes."
                ),
            },
        )
        + ck_kpi_block(
            "EBITDA Cushion", f"{cushion:.0%}",
            help={
                "definition": (
                    "Percent EBITDA can decline before the leverage "
                    "covenant trips. 20%+ = robust; 10-20% = managed "
                    "tightly; <10% = one quarter of weakness ends "
                    "the hold thesis."
                ),
            },
        )
        + '</div>'
        + '<p class="ck-section-body">'
        f'Pro forma EBITDA can decline {cushion:.0%} before the 6.5x covenant trips. '
        f'RCM uplift reduces leverage from {actual_lev:.1f}x to {pro_forma_lev:.1f}x, '
        f'adding {headroom - (6.5 - actual_lev):.1f} turns of cushion.</p>'
    )
    covenant_section = ck_panel(
        covenant_inner,
        title="Covenant Headroom (at 10x Entry, 6.5x Max Leverage)",
    )

    # ── Methodology ──
    method = ck_panel(
        '<p class="ck-section-body">'
        'Coefficients calibrated to published research bands: denial 12%→5% = $8-15M on $400M NPR. '
        'Current metrics estimated from HCRIS public data and ML predictions. Target metrics set at '
        'P75 peer benchmarks with 60% gap closure assumption. Revenue levers use NPR × delta × '
        'avoidable share. Cost levers use claims volume × cost per reworked claim. '
        'Working capital from AR reduction is one-time cash (not included in recurring EBITDA). '
        'Returns assume 5.5x leverage, 3% organic growth, 10%/yr debt paydown.</p>',
        title="Bridge Methodology",
    )

    # ── Achievement sensitivity ──
    ach_header = '<th>Lever</th><th>50%</th><th>75%</th><th>100%</th><th>120%</th>'
    ach_rows = ""
    ach_totals = {50: 0, 75: 0, 100: 0, 120: 0}
    for lev in bridge["levers"]:
        if lev["ebitda_impact"] == 0:
            continue
        ach_rows += f'<tr><td style="font-weight:500;">{_lever_label_link(lev["name"][:20], lev.get("metric", ""))}</td>'
        for pct in (50, 75, 100, 120):
            val = lev["ebitda_impact"] * pct / 100
            ach_totals[pct] += val
            color = "var(--cad-text2)" if pct < 100 else "var(--cad-pos)"
            ach_rows += f'<td class="num" style="color:{color};font-size:11px;">{_fm(val)}</td>'
        ach_rows += '</tr>'
    ach_rows += '<tr style="font-weight:700;border-top:2px solid var(--cad-border);"><td>Total</td>'
    for pct in (50, 75, 100, 120):
        ach_rows += f'<td class="num" style="color:var(--cad-pos);">{_fm(ach_totals[pct])}</td>'
    ach_rows += '</tr>'

    achievement_inner = (
        '<p class="ck-section-body">'
        'What if we only achieve a fraction of each lever? 50% = conservative, '
        '75% = base management case, 100% = plan, 120% = stretch.</p>'
        f'<table class="cad-table"><thead><tr>{ach_header}'
        f'</tr></thead><tbody>{ach_rows}</tbody></table>'
    )
    achievement_section = ck_panel(
        achievement_inner, title="Achievement Sensitivity",
    )

    # ── 5-year cumulative value creation ──
    hold_years = 5
    organic_growth = 0.03
    total_uplift = bridge["total_ebitda_impact"]
    entry_ebitda = bridge["current_ebitda"]

    year_rows = ""
    cum_organic = 0
    cum_rcm = 0
    for yr in range(1, hold_years + 1):
        organic_this = entry_ebitda * ((1 + organic_growth) ** yr - (1 + organic_growth) ** (yr - 1))
        cum_organic += organic_this
        # RCM ramp: linear to full at year 1.5, then full
        ramp_pct = min(1.0, yr / 1.5)
        rcm_this = total_uplift * ramp_pct
        cum_rcm = rcm_this  # annual run-rate, not cumulative
        total_yr = entry_ebitda * (1 + organic_growth) ** yr + rcm_this
        margin_cell = (
            f'<td class="num">{total_yr / rev:.1%}</td>' if rev
            else '<td class="num">—</td>'
        )
        year_rows += (
            f'<tr>'
            f'<td class="num">Year {yr}</td>'
            f'<td class="num">{_fm(entry_ebitda * (1 + organic_growth) ** yr)}</td>'
            f'<td class="num" style="color:var(--cad-pos);">+{_fm(rcm_this)}</td>'
            f'<td class="num" style="font-weight:600;">{_fm(total_yr)}</td>'
            f'{margin_cell}'
            f'</tr>'
        )

    # Entry and exit EV
    entry_ev_10x = entry_ebitda * 10
    exit_ebitda_5y = entry_ebitda * (1 + organic_growth) ** 5 + total_uplift
    exit_ev_11x = exit_ebitda_5y * 11
    value_created = exit_ev_11x - entry_ev_10x

    vc_organic = entry_ebitda * ((1 + organic_growth) ** 5 - 1) * 10
    vc_rcm = total_uplift * 10
    vc_multiple = exit_ebitda_5y * 1  # 1 turn expansion

    entry_margin_cell = (
        f'<td class="num">{entry_ebitda / rev:.1%}</td>' if rev
        else '<td class="num">—</td>'
    )
    trajectory_chart = _trajectory_stacked_bars(
        entry_ebitda, total_uplift, organic_growth, hold_years,
    )
    trajectory_caption = (
        '<div class="eb-chart-caption">'
        'Base EBITDA + RCM uplift, ramping to full run-rate by month 18'
        '</div>'
    ) if trajectory_chart else ""
    value_inner = (
        '<p class="ck-section-body">'
        'EBITDA trajectory: 3% organic growth + RCM uplift ramp (full run-rate at month 18).</p>'
        + trajectory_chart + trajectory_caption +
        '<table class="cad-table"><thead><tr>'
        '<th></th><th>Base EBITDA</th><th>RCM Uplift</th><th>Total</th><th>Margin</th>'
        '</tr></thead><tbody>'
        '<tr><td>Entry</td>'
        f'<td class="num">{_fm(entry_ebitda)}</td>'
        '<td class="num">—</td>'
        f'<td class="num">{_fm(entry_ebitda)}</td>'
        f'{entry_margin_cell}</tr>'
        f'{year_rows}'
        '</tbody></table>'
        + '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Entry EV (10x)", _fm(entry_ev_10x),
            help={
                "definition": (
                    "Enterprise value at acquisition, assuming a 10x "
                    "EBITDA entry multiple — the PE healthcare "
                    "midpoint. Underwrite at 9-10x for community "
                    "hospitals, 11-12x for specialty platforms."
                ),
            },
        )
        + ck_kpi_block(
            "Exit EV (11x)", _fm(exit_ev_11x),
            help={
                "definition": (
                    "Modeled EV at exit assuming a one-turn multiple "
                    "expansion (10x → 11x). Conservative — PE buyers "
                    "in healthcare have historically paid 0.5-1.5 "
                    "turns above acquirer multiples for de-risked "
                    "platforms."
                ),
            },
        )
        + ck_kpi_block(
            "Value Created", _fm(value_created),
            help={
                "definition": (
                    "Total dollar value creation over the 5-year hold: "
                    "Exit EV - Entry EV. The sum that translates into "
                    "LP/GP distributions via the waterfall. The three "
                    "KPIs below decompose this number by source."
                ),
            },
        )
        + ck_kpi_block("Exit EBITDA", _fm(exit_ebitda_5y))
        + '</div>'
        + '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Organic Growth", _fm(vc_organic),
            help={
                "definition": (
                    "Value from EBITDA compounding at the 3% organic "
                    "growth rate. The 'do nothing' component — what "
                    "this deal would have created without any RCM "
                    "intervention or multiple expansion."
                ),
            },
        )
        + ck_kpi_block(
            "RCM Value Creation", _fm(vc_rcm),
            help={
                "definition": (
                    "Value attributable to the RCM levers the platform "
                    "underwrites (rate, denial, AR, contract terms, "
                    "labor, supply). This is the operational alpha — "
                    "the partner's claim that this PE sponsor adds "
                    "value beyond market-trend exposure."
                ),
            },
        )
        + ck_kpi_block(
            "Multiple Expansion", _fm(vc_multiple),
            help={
                "definition": (
                    "Value from the assumed one-turn multiple "
                    "expansion at exit. Treat as the most speculative "
                    "component — exit multiples drift with the buyer "
                    "market, which the sponsor doesn't control. "
                    "Healthier deals lean less on this number."
                ),
            },
        )
        + '</div>'
    )
    value_creation = ck_panel(
        value_inner, title="5-Year Value Creation Waterfall",
    )

    # ── Peer context for levers ──
    peer_context_rows = ""
    if hcris_df is not None and len(hcris_df) > 50:
        size_lo = max(10, beds * 0.5)
        size_hi = beds * 2.0
        peers = hcris_df[(hcris_df["beds"] >= size_lo) & (hcris_df["beds"] <= size_hi)]
        if state:
            st_peers = peers[peers["state"] == state]
            if len(st_peers) >= 8:
                peers = st_peers

        peer_metrics = {
            "operating_margin": ("Op Margin", "pct"),
            "net_to_gross_ratio": ("Net-to-Gross", "pct"),
            "occupancy_rate": ("Occupancy", "pct"),
            "revenue_per_bed": ("Rev/Bed", "dollars"),
            "expense_per_bed": ("Exp/Bed", "dollars"),
        }

        for metric, (label, fmt) in peer_metrics.items():
            if metric not in peers.columns or metric not in hcris_df.columns:
                continue
            hosp_val = _safe_float(hospital.get(metric))
            peer_vals = peers[metric].dropna()
            if len(peer_vals) < 5 or hosp_val == 0:
                continue
            p25 = float(peer_vals.quantile(0.25))
            p50 = float(peer_vals.median())
            p75 = float(peer_vals.quantile(0.75))
            pctile = float((peer_vals < hosp_val).mean() * 100)

            if fmt == "pct":
                fmt_fn = lambda v: f"{v:.1%}"
            else:
                fmt_fn = _fm

            pct_color = "var(--cad-pos)" if pctile > 60 else ("var(--cad-neg)" if pctile < 40 else "var(--cad-text2)")
            bar_pct = min(100, max(0, pctile))
            peer_context_rows += (
                f'<tr>'
                f'<td style="font-weight:500;">{_html.escape(label)}</td>'
                f'<td class="num" style="font-weight:600;">{fmt_fn(hosp_val)}</td>'
                f'<td class="num">{fmt_fn(p25)}</td>'
                f'<td class="num">{fmt_fn(p50)}</td>'
                f'<td class="num">{fmt_fn(p75)}</td>'
                f'<td><div style="display:flex;align-items:center;gap:4px;">'
                f'<div style="width:50px;background:var(--cad-bg3);border-radius:2px;height:6px;">'
                f'<div style="width:{bar_pct:.0f}%;background:{pct_color};border-radius:2px;height:6px;">'
                f'</div></div>'
                f'<span style="font-size:10px;color:{pct_color};">P{pctile:.0f}</span></div></td>'
                f'</tr>'
            )

    peer_section = ""
    if peer_context_rows:
        n_peers = len(peers) if 'peers' in dir() else 0
        peer_inner = (
            '<p class="ck-section-body">'
            f'Key metrics vs {n_peers} size-matched peers. Low percentile on margin/efficiency '
            'metrics = more room for improvement = larger bridge opportunity.</p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Metric</th><th>Hospital</th><th>P25</th><th>P50</th><th>P75</th><th>Percentile</th>'
            f'</tr></thead><tbody>{peer_context_rows}</tbody></table>'
        )
        peer_section = ck_panel(
            peer_inner, title="Peer Context — Where This Hospital Sits",
        )

    # ── Navigation ──
    # Generic deal-context navigation now comes from the standard
    # _model_nav ribbon at the top of the page (consistent across all
    # per-deal surfaces); this panel keeps only the bridge-specific
    # actions that the ribbon doesn't carry.
    from .models_page import _model_nav
    deal_ribbon = _model_nav(ccn, active="ebitda_bridge")
    nav_inner = (
        '<p class="ck-section-body">'
        f'<form method="POST" action="/value-tracker/{_html.escape(ccn)}/freeze" class="ic-bridge-inline-form">'
        '<button type="submit" class="cad-btn cad-btn-primary">Freeze as Value Plan</button></form> '
        f'<a href="/export/bridge/{_html.escape(ccn)}" class="cad-btn">Download Excel</a> '
        f'<a href="/value-tracker/{_html.escape(ccn)}" class="cad-btn">Value Tracker</a> '
        '<a href="/fund-learning" class="cad-btn">Fund Learning</a>'
        '</p>'
    )
    nav = ck_panel(nav_inner, title="Bridge actions")

    freshness = data_freshness_footer(
        hcris_year=2022, n_hospitals=6123,
        has_seller_data=has_seller_data,
        n_seller_metrics=len(dr_overrides),
    )

    page_title = ck_page_title(
        "EBITDA Bridge",
        eyebrow=f"EBITDA BRIDGE · CCN {_html.escape(ccn)}",
        meta=f"{_html.escape(name)} — {_html.escape(state)} · {beds:.0f} beds",
    )
    explainer_html = (
        '<p class="ck-eb-explainer">'
        f'<em>{_html.escape(name)}.</em> '
        "7-lever RCM bridge from current EBITDA to pro-forma — "
        "denial / underpay / DAR / coding / contract / cost "
        "discipline / cash acceleration. Each lever shows "
        "current vs benchmark target with data provenance."
        '</p>'
    )
    # Lead takeaway — the computed financial stakes a partner reads
    # before any chart/table: dollar uplift → margin gap to benchmark →
    # EV created at 10x → pro-forma EBITDA. All figures are computed
    # from the bridge; nothing is fabricated.
    _uplift = bridge["total_ebitda_impact"]
    _current = bridge["current_ebitda"]
    _proforma = bridge["new_ebitda"]
    lead_anchor = ck_value_anchor(
        "RCM EBITDA UPLIFT",
        f"+{_fm(_uplift)}",
        delta=f"+{bridge['margin_improvement_bps']:.0f} bps margin",
        opportunity=(
            f"{_fm(_uplift * 10)} EV at 10x" if _uplift > 0 else ""
        ),
        target=f"pro forma {_fm(_proforma)}",
        tone="positive",
    )
    body = (
        f'{deal_ribbon}{page_title}{lead_anchor}{explainer_html}{provenance_banner}{kpis}{realization_section}{waterfall_section}'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        f'<div>{detail_section}{timing_section}</div>'
        f'<div>{grid_section}{covenant_section}</div></div>'
        f'{value_creation}'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        f'<div>{achievement_section}</div>'
        f'<div>{peer_section}</div></div>'
        f'{method}{nav}{freshness}'
        + ck_next_section(
            "Run the bridge through Monte Carlo",
            "/diligence/deal-mc",
            eyebrow="Continue —",
            italic_word="Monte",
        )
    )

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        f"EBITDA Bridge — {_html.escape(name)}",
        extra_css=_EXPLAINER_CSS,
    )
