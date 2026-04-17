"""Side-by-side deal comparison + screening page (Prompt 33-A/C).

Two pages:

1. ``/compare?deals=acme,beta`` — column-per-deal comparison table
   with an SVG radar chart overlay.
2. ``/screen`` — paste hospital names, get a ranked table with
   verdict badges.

Both are server-rendered HTML using the shared ``_ui_kit.shell()``.
"""
from __future__ import annotations

import html
import math
from typing import Any, Dict, List, Optional

from ..analysis.packet import DealAnalysisPacket


# ── Comparison ────────────────────────────────────────────────────

_COMPARE_DIMENSIONS = [
    ("Completeness", lambda p: p.completeness.grade if p.completeness else "—"),
    ("EBITDA impact", lambda p: p.ebitda_bridge.total_ebitda_impact if p.ebitda_bridge else 0),
    ("denial_rate", lambda p: _pm_val(p, "denial_rate")),
    ("days_in_ar", lambda p: _pm_val(p, "days_in_ar")),
    ("net_collection_rate", lambda p: _pm_val(p, "net_collection_rate")),
    ("cost_to_collect", lambda p: _pm_val(p, "cost_to_collect")),
    ("clean_claim_rate", lambda p: _pm_val(p, "clean_claim_rate")),
    ("case_mix_index", lambda p: _pm_val(p, "case_mix_index")),
    ("Risk count", lambda p: len(p.risk_flags or [])),
]

_RADAR_METRICS = [
    "denial_rate", "days_in_ar", "net_collection_rate",
    "cost_to_collect", "clean_claim_rate", "case_mix_index",
]

_PALETTE = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444"]


def _pm_val(p: DealAnalysisPacket, metric: str) -> Optional[float]:
    pm = (p.rcm_profile or {}).get(metric)
    return float(pm.value) if pm is not None else None


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        if abs(v) >= 1e6:
            return f"${v / 1e6:,.1f}M"
        return f"{v:,.2f}"
    return str(v)


def _render_radar(packets: List[DealAnalysisPacket]) -> str:
    """Overlapping radar polygons — one per deal, 6 axes."""
    if not packets:
        return ""
    n_axes = len(_RADAR_METRICS)
    cx, cy, radius = 150, 150, 120
    angle_step = 2 * math.pi / n_axes

    # Collect values per metric across all deals to normalize 0–1.
    all_vals: Dict[str, List[float]] = {m: [] for m in _RADAR_METRICS}
    for p in packets:
        for m in _RADAR_METRICS:
            v = _pm_val(p, m)
            if v is not None:
                all_vals[m].append(v)
    mins = {m: min(vs) if vs else 0 for m, vs in all_vals.items()}
    maxs = {m: max(vs) if vs else 1 for m, vs in all_vals.items()}

    # Axis labels.
    labels = ""
    for i, m in enumerate(_RADAR_METRICS):
        angle = -math.pi / 2 + i * angle_step
        lx = cx + (radius + 18) * math.cos(angle)
        ly = cy + (radius + 18) * math.sin(angle)
        anchor = "middle"
        if lx < cx - 10:
            anchor = "end"
        elif lx > cx + 10:
            anchor = "start"
        labels += (
            f'<text x="{lx:.0f}" y="{ly:.0f}" '
            f'text-anchor="{anchor}" fill="#94a3b8" '
            f'font-size="10">{m.replace("_", " ")}</text>'
        )

    # Polygons.
    polygons = ""
    for idx, p in enumerate(packets):
        color = _PALETTE[idx % len(_PALETTE)]
        pts: List[str] = []
        for i, m in enumerate(_RADAR_METRICS):
            v = _pm_val(p, m)
            lo, hi = mins[m], maxs[m]
            frac = ((v - lo) / (hi - lo)) if v is not None and hi > lo else 0.5
            angle = -math.pi / 2 + i * angle_step
            r = frac * radius
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            pts.append(f"{px:.1f},{py:.1f}")
        polygons += (
            f'<polygon points="{" ".join(pts)}" '
            f'fill="{color}" fill-opacity="0.15" '
            f'stroke="{color}" stroke-width="1.5"/>'
        )

    return (
        f'<svg viewBox="0 0 300 300" width="300" height="300" '
        f'style="display:block;margin:0 auto;">'
        f'{labels}{polygons}</svg>'
    )


def render_comparison(packets: List[DealAnalysisPacket]) -> str:
    """Column-per-deal table + radar chart. Used by ``GET /compare``."""
    from .shell_v2 import shell_v2

    if not packets:
        body = (
            '<div class="cad-card">'
            '<p style="color:var(--cad-text3);margin-bottom:12px;">No deals selected for comparison.</p>'
            '<a href="/portfolio" class="cad-btn cad-btn-primary" '
            'style="text-decoration:none;">Go to Portfolio to select deals</a>'
            '</div>'
        )
        return shell_v2(body, "Deal Comparison",
                        subtitle="Side-by-side deal analysis")

    header_cells = "".join(
        f'<th>{_esc(p.deal_name or p.deal_id)}</th>'
        for p in packets
    )
    rows_html: List[str] = []
    for dim_name, fn in _COMPARE_DIMENSIONS:
        cells: List[str] = []
        for p in packets:
            v = fn(p)
            cells.append(f'<td class="num">{_fmt(v)}</td>')
        rows_html.append(
            f"<tr><td><strong>{_esc(dim_name)}</strong></td>"
            + "".join(cells) + "</tr>"
        )
    table_html = (
        '<table class="cad-table">'
        f'<thead><tr><th>Dimension</th>{header_cells}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table>'
    )

    radar = _render_radar(packets)

    legend = " ".join(
        f'<span style="color:{_PALETTE[i % len(_PALETTE)]};margin-right:12px;">'
        f'&#9632; {_esc(p.deal_name or p.deal_id)}</span>'
        for i, p in enumerate(packets)
    )

    # KPI summary for each deal
    kpi_cards = ""
    for i, p in enumerate(packets):
        color = _PALETTE[i % len(_PALETTE)]
        dr = _pm_val(p, "denial_rate")
        ar = _pm_val(p, "days_in_ar")
        risk_count = len(p.risk_flags or [])
        grade = p.completeness.grade if p.completeness else "—"
        did = _esc(p.deal_id)
        kpi_cards += (
            f'<div class="cad-card" style="border-left:3px solid {color};">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
            f'<h3>{_esc(p.deal_name or p.deal_id)}</h3>'
            f'<a href="/deal/{did}" class="cad-badge cad-badge-blue" style="text-decoration:none;">Dashboard</a>'
            f'</div>'
            f'<div style="display:flex;gap:16px;font-size:12px;">'
            f'<span>DR: <strong>{_fmt(dr)}</strong></span>'
            f'<span>AR: <strong>{_fmt(ar)}</strong></span>'
            f'<span>Risks: <strong>{risk_count}</strong></span>'
            f'<span>Grade: <strong>{grade}</strong></span>'
            f'</div>'
            f'<div style="display:flex;gap:6px;margin-top:8px;">'
            f'<a href="/models/dcf/{did}" class="cad-badge cad-badge-muted" style="text-decoration:none;">DCF</a>'
            f'<a href="/models/lbo/{did}" class="cad-badge cad-badge-muted" style="text-decoration:none;">LBO</a>'
            f'<a href="/models/bridge/{did}" class="cad-badge cad-badge-muted" style="text-decoration:none;">Bridge</a>'
            f'<a href="/models/denial/{did}" class="cad-badge cad-badge-muted" style="text-decoration:none;">Denial</a>'
            f'</div></div>'
        )

    # Actions
    deal_ids = ",".join(_esc(p.deal_id) for p in packets)
    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/portfolio" class="cad-btn" style="text-decoration:none;">Portfolio</a>'
        f'<a href="/portfolio/regression" class="cad-btn" style="text-decoration:none;">Regression</a>'
        f'<a href="/analysis" class="cad-btn cad-btn-primary" style="text-decoration:none;">Analysis Hub</a>'
        f'</div>'
    )

    body = (
        f'<div style="display:grid;grid-template-columns:{"1fr " * len(packets)};gap:12px;">'
        f'{kpi_cards}</div>'
        f'<div class="cad-card">'
        f'<div style="margin-bottom:12px;font-size:12.5px;">{legend}</div>'
        f'{radar}</div>'
        f'<div class="cad-card">{table_html}</div>'
        f'{actions}'
    )
    return shell_v2(
        body, "Deal Comparison",
        subtitle=f"Comparing {len(packets)} deals",
    )


# ── Screening page ────────────────────────────────────────────────

def render_screen_page(
    results: Optional[List[Dict[str, Any]]] = None,
    filters: Optional[Dict[str, str]] = None,
    predefined: Optional[str] = None,
    total_scanned: int = 0,
) -> str:
    """GET /screen — metric-based hospital screener."""
    from .shell_v2 import shell_v2
    from .brand import PALETTE

    filters = filters or {}

    # Predefined screen buttons
    presets = [
        ("turnaround", "Turnaround Targets", "Denial >15%, AR >55 days — biggest improvement opportunity"),
        ("large_cap", "Large Hospitals", "300+ beds, $300M+ revenue — platform acquisitions"),
        ("margin_expansion", "Margin Expansion", "Positive margin, denial 10-18% — room to grow"),
        ("undervalued", "Undervalued", "High beds, low revenue per bed — pricing opportunity"),
        ("small_efficient", "Efficient Small", "<200 beds, AR <45 days — bolt-on candidates"),
    ]
    preset_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">'
    for key, label, desc in presets:
        active = f'background:{PALETTE["brand_accent"]};color:white;border-color:{PALETTE["brand_accent"]};' if predefined == key else ""
        preset_html += (
            f'<a href="/screen?preset={key}" class="cad-btn" '
            f'style="text-decoration:none;{active}" title="{_esc(desc)}">{_esc(label)}</a>'
        )
    preset_html += '</div>'

    # Filter form
    filter_fields = [
        ("min_beds", "Min Beds", filters.get("min_beds", ""), "e.g. 200"),
        ("max_beds", "Max Beds", filters.get("max_beds", ""), "e.g. 500"),
        ("min_revenue", "Min Revenue ($M)", filters.get("min_revenue", ""), "e.g. 100"),
        ("max_margin", "Max Margin (%)", filters.get("max_margin", ""), "e.g. 5 (find struggling)"),
        ("state", "State", filters.get("state", ""), "e.g. AL, TX"),
    ]
    filter_inputs = ""
    for name, label, val, placeholder in filter_fields:
        filter_inputs += (
            f'<div>'
            f'<label style="font-size:11px;color:{PALETTE["text_muted"]};display:block;margin-bottom:2px;">'
            f'{_esc(label)}</label>'
            f'<input name="{name}" value="{_esc(val)}" placeholder="{_esc(placeholder)}" '
            f'style="width:100%;padding:7px 10px;border:1px solid var(--cad-border);'
            f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;"></div>'
        )

    form = (
        f'<div class="cad-card">'
        f'<h2>Filter by Metrics</h2>'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'Find hospitals from {total_scanned:,} HCRIS records by financial and operational criteria. '
        f'Use presets for common screens or build custom filters.</p>'
        f'{preset_html}'
        f'<form method="GET" action="/screen">'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;">'
        f'{filter_inputs}</div>'
        f'<div style="margin-top:12px;">'
        f'<button type="submit" class="cad-btn cad-btn-primary">Run Screen</button></div>'
        f'</form></div>'
    )

    # Results
    results_block = ""
    if results:
        rows_html = ""
        for r in results:
            ccn = _esc(str(r.get("ccn", "")))
            name = _esc(str(r.get("name", ""))[:45])
            state = _esc(str(r.get("state", "")))
            beds = r.get("beds", r.get("bed_count", 0))
            rev = r.get("net_patient_revenue", r.get("revenue", r.get("net_revenue", 0)))
            margin = r.get("operating_margin", 0)
            margin = float(margin) if margin else 0
            margin_color = PALETTE["positive"] if margin > 0.05 else (
                PALETTE["warning"] if margin > 0 else PALETTE["negative"])
            rows_html += (
                f'<tr>'
                f'<td><a href="/hospital/{ccn}" style="font-weight:500;">{name}</a></td>'
                f'<td>{state}</td>'
                f'<td class="num">{int(beds):,}</td>'
                f'<td class="num">${float(rev)/1e6:,.0f}M</td>'
                f'<td class="num" style="color:{margin_color};">{margin:.1%}</td>'
                f'<td style="white-space:nowrap;">'
                f'<a href="/hospital/{ccn}" class="cad-badge cad-badge-blue" '
                f'style="text-decoration:none;">Profile</a> '
                f'<a href="/new-deal?q={ccn}" class="cad-badge cad-badge-green" '
                f'style="text-decoration:none;">Diligence</a></td>'
                f'</tr>'
            )
        results_block = (
            f'<div class="cad-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
            f'<h2>{len(results)} Matches</h2>'
            f'<span style="font-size:12px;color:{PALETTE["text_muted"]};">from {total_scanned:,} hospitals</span>'
            f'</div>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Hospital</th><th>State</th><th>Beds</th><th>NPR</th>'
            f'<th>Margin</th><th>Actions</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div>'
        )

    body = f'{form}{results_block}'
    n = len(results) if results else 0
    sub = f"{n} matches from {total_scanned:,} hospitals" if results else f"Screen {total_scanned:,} HCRIS hospitals by metrics"
    return shell_v2(body, "Hospital Screener", active_nav="/screen", subtitle=sub)
