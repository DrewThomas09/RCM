"""PE Desk IC Memo Generator — one-click investment committee memo.

Generates a complete, substantive IC memo for any hospital using only
public data and ML models. Saves analysts 20+ hours per deal by
auto-generating every section with real numbers, not templates.

Sections:
1. Target Overview & Thesis
2. Market Context & Competitive Position
3. RCM Performance Analysis with Comps
4. Predicted Improvement Opportunities
5. EBITDA Bridge with Sensitivities
6. Returns Analysis (Base/Bull/Bear)
7. Key Risks & Mitigants
8. Data Sources & Methodology Appendix
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_header, ck_section_intro, ck_signal_badge,
    ck_sticky_toc,
)
from .brand import PALETTE


def _safe_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return default if f != f else f
    except (TypeError, ValueError):
        return default


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def _pct(val: float, decimals: int = 1) -> str:
    return f"{val:.{decimals}%}"


# ── Editorial inline-SVG charts ────────────────────────────────────
# Tiny static SVGs that ride the editorial palette (teal-deep / amber /
# rule color). No JS, no chart library — they substitute for "bland
# table walls" without adding a dependency.

def _peer_margin_dotplot(target_margin: float, peer_margins: List[float],
                         width: int = 720, height: int = 88) -> str:
    """Horizontal dot plot of peer operating margins with target highlighted.

    Visualizes where the target sits in the peer distribution at a glance.
    """
    peers = [m for m in peer_margins if m == m and -1 < m < 1]
    if not peers:
        return ""
    lo = min(min(peers), target_margin) - 0.02
    hi = max(max(peers), target_margin) + 0.02
    span = max(hi - lo, 0.01)

    pad_l, pad_r, pad_t, pad_b = 36, 36, 18, 36
    plot_w = width - pad_l - pad_r
    plot_y = pad_t + (height - pad_t - pad_b) / 2

    def _x(v: float) -> float:
        return pad_l + (v - lo) / span * plot_w

    # Axis ticks: lo, lo+25%, lo+50%, lo+75%, hi (round to nearest 1%)
    tick_vals = [lo + span * f for f in (0, 0.25, 0.5, 0.75, 1.0)]
    ticks_svg = ""
    for tv in tick_vals:
        tx = _x(tv)
        ticks_svg += (
            f'<line x1="{tx:.1f}" y1="{plot_y - 6}" x2="{tx:.1f}" '
            f'y2="{plot_y + 6}" stroke="#BFB6A2" stroke-width="0.8"/>'
            f'<text x="{tx:.1f}" y="{height - pad_b + 18}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#5C6878" text-anchor="middle">{tv * 100:+.1f}%</text>'
        )

    # Median line
    med = sorted(peers)[len(peers) // 2]
    mx = _x(med)
    median_mark = (
        f'<line x1="{mx:.1f}" y1="{plot_y - 14}" x2="{mx:.1f}" '
        f'y2="{plot_y + 14}" stroke="#155752" stroke-width="1.2" '
        f'stroke-dasharray="3,2"/>'
        f'<text x="{mx:.1f}" y="{pad_t + 2}" font-family="Inter Tight,sans-serif" '
        f'font-size="9" font-weight="700" letter-spacing="0.08em" '
        f'fill="#155752" text-anchor="middle">PEER MEDIAN</text>'
    )

    # Peer dots
    dots_svg = ""
    for m in peers:
        dx = _x(m)
        dots_svg += (
            f'<circle cx="{dx:.1f}" cy="{plot_y:.1f}" r="3.6" '
            f'fill="#D6CFC0" stroke="#BFB6A2" stroke-width="0.6"/>'
        )

    # Target marker
    tx = _x(target_margin)
    tone = "#0a8a5f" if target_margin >= med else "#b8732a"
    target_svg = (
        f'<circle cx="{tx:.1f}" cy="{plot_y:.1f}" r="6" '
        f'fill="{tone}" stroke="#FAF7F0" stroke-width="2"/>'
        f'<text x="{tx:.1f}" y="{plot_y - 14}" '
        f'font-family="Inter Tight,sans-serif" font-size="9.5" font-weight="700" '
        f'letter-spacing="0.08em" fill="{tone}" text-anchor="middle">'
        f'TARGET {target_margin * 100:+.1f}%</text>'
    )

    # Axis baseline
    axis_svg = (
        f'<line x1="{pad_l}" y1="{plot_y:.1f}" x2="{pad_l + plot_w}" '
        f'y2="{plot_y:.1f}" stroke="#D6CFC0" stroke-width="1"/>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{axis_svg}{ticks_svg}{dots_svg}{median_mark}{target_svg}'
        f'</svg>'
    )


def _scenario_returns_chart(rows: List[Dict[str, Any]],
                            width: int = 720, height: int = 220) -> str:
    """Side-by-side IRR bars per scenario.

    ``rows`` items: ``{"label", "irr", "moic", "tone"}``.
    """
    if not rows:
        return ""
    max_irr = max(max(r["irr"] for r in rows), 0.30)
    pad_l, pad_r, pad_t, pad_b = 18, 18, 24, 56
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(rows)
    slot = plot_w / n
    bar_w = slot * 0.62

    # Y-axis tick lines at 0/10/20/30%+
    ticks_svg = ""
    for pct in (0, 0.10, 0.20, 0.30, max(0.30, round(max_irr * 10) / 10)):
        if pct > max_irr * 1.05:
            continue
        ty = pad_t + plot_h - (pct / max_irr) * plot_h
        ticks_svg += (
            f'<line x1="{pad_l}" y1="{ty:.1f}" x2="{width - pad_r}" '
            f'y2="{ty:.1f}" stroke="#E8E0D0" stroke-width="0.8"/>'
            f'<text x="{pad_l - 4}" y="{ty + 3:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#8A92A0" text-anchor="end">{pct * 100:.0f}%</text>'
        )

    bars_svg = ""
    for i, r in enumerate(rows):
        cx = pad_l + slot * i + slot / 2
        bx = cx - bar_w / 2
        bh = (r["irr"] / max_irr) * plot_h if max_irr > 0 else 0
        by = pad_t + plot_h - bh
        fill = {
            "pos": "#155752", "warn": "#b8732a", "neg": "#b5321e",
        }.get(r.get("tone", "pos"), "#155752")
        bars_svg += (
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" '
            f'height="{bh:.1f}" fill="{fill}" rx="1"/>'
            f'<text x="{cx:.1f}" y="{by - 6:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="11" '
            f'font-weight="700" fill="#1a2332" text-anchor="middle">'
            f'{r["irr"] * 100:.1f}%</text>'
            f'<text x="{cx:.1f}" y="{height - pad_b + 14:.1f}" '
            f'font-family="Inter Tight,sans-serif" font-size="9" font-weight="700" '
            f'letter-spacing="0.08em" fill="#1a2332" text-anchor="middle">'
            f'{_html.escape(r["label"].upper())}</text>'
            f'<text x="{cx:.1f}" y="{height - pad_b + 28:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9.5" '
            f'fill="#5C6878" text-anchor="middle">'
            f'{r["moic"]:.2f}x MOIC</text>'
        )

    # Axis baseline
    base_y = pad_t + plot_h
    base_svg = (
        f'<line x1="{pad_l}" y1="{base_y:.1f}" x2="{width - pad_r}" '
        f'y2="{base_y:.1f}" stroke="#BFB6A2" stroke-width="1"/>'
    )

    # 20% IRR target reference line
    target_y = pad_t + plot_h - (0.20 / max_irr) * plot_h
    target_svg = (
        f'<line x1="{pad_l}" y1="{target_y:.1f}" x2="{width - pad_r}" '
        f'y2="{target_y:.1f}" stroke="#155752" stroke-width="1" '
        f'stroke-dasharray="4,3" opacity="0.6"/>'
        f'<text x="{width - pad_r - 2}" y="{target_y - 4:.1f}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" font-weight="700" '
        f'letter-spacing="0.08em" fill="#155752" text-anchor="end">'
        f'20% IRR TARGET</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{ticks_svg}{base_svg}{bars_svg}{target_svg}'
        f'</svg>'
    )


# Editorial CSS for ic-memo classes already used in markup but never
# styled — bar charts, two-column grid, target/strong/bear rows.
_IC_MEMO_CSS = """
.ic-memo-grid-2col {
  display: grid; grid-template-columns: 1.25fr 1fr; gap: 2.25rem;
  align-items: start;
}
.ic-memo-bar-row {
  display: grid; grid-template-columns: 180px 1fr; gap: 1rem;
  align-items: center; margin: 0 0 .55rem;
}
.ic-memo-bar-label {
  font-family: "Inter Tight","Inter",sans-serif;
  font-size: .85rem; color: #1a2332; font-weight: 600;
}
.ic-memo-bar-track {
  position: relative; background: #ECE5D6;
  border-radius: 2px; height: 22px; overflow: hidden;
}
.ic-memo-bar-fill {
  background: linear-gradient(90deg, #155752 0%, #1F7A75 100%);
  color: #FAF7F0; height: 100%;
  font-family: "JetBrains Mono",monospace; font-size: .76rem;
  font-weight: 600; display: flex; align-items: center;
  justify-content: flex-end; padding: 0 .6rem;
  white-space: nowrap; box-shadow: 2px 0 0 rgba(15,28,46,.04);
  transition: width .35s ease;
}
.ic-memo-bar-total {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: .9rem 1rem; margin-top: .9rem;
  background: linear-gradient(135deg, #D4E4E2 0%, #FAF7F0 100%);
  border: 1px solid #BFD1CE; border-left: 3px solid #155752;
  border-radius: 2px;
  font-family: "Source Serif 4",Georgia,serif;
  font-size: 1.1rem; color: #1a2332;
}
.ic-memo-bar-total .cad-pos {
  color: #0a8a5f; font-weight: 700; font-size: 1.25rem;
  font-variant-numeric: tabular-nums;
}
.ic-memo-row-target td {
  background: #D4E4E2 !important;
  border-top: 2px solid #155752; border-bottom: 2px solid #155752;
}
.ic-memo-row-strong td {
  background: #ECE5D6 !important; font-weight: 700;
  border-top: 1px solid #BFB6A2;
}
.ic-memo-row-bear td { background: #F7E8E2 !important; }
.ic-memo-chart-caption {
  font-family: "Inter Tight","Inter",sans-serif;
  font-size: .72rem; color: #5C6878;
  text-align: center; letter-spacing: 0.06em;
  text-transform: uppercase; margin: -.5rem 0 1.25rem;
}
@media (max-width: 900px) {
  .ic-memo-grid-2col { grid-template-columns: 1fr; }
  .ic-memo-bar-row { grid-template-columns: 1fr; }
}
"""


def _build_memo_data(ccn: str, hcris_df: pd.DataFrame, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Assemble all data needed for the IC memo from public sources + ML + seller data."""
    match = hcris_df[hcris_df["ccn"] == ccn]
    if match.empty:
        return None

    hospital = match.iloc[0]
    name = str(hospital.get("name", f"Hospital {ccn}"))
    state = str(hospital.get("state", ""))
    county = str(hospital.get("county", ""))
    beds = _safe_float(hospital.get("beds"))
    rev = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    gross = _safe_float(hospital.get("gross_patient_revenue"))
    mc_pct = _safe_float(hospital.get("medicare_day_pct"))
    md_pct = _safe_float(hospital.get("medicaid_day_pct"))
    comm_pct = max(0, 1 - mc_pct - md_pct)
    days = float(hospital.get("total_patient_days", 0) or 0)
    bda = float(hospital.get("bed_days_available", 0) or 0)

    if rev < 1e6:
        return None

    margin = (rev - opex) / rev if rev > 1e5 else 0
    margin = max(-1, min(1, margin))
    ebitda = rev - opex
    occupancy = days / bda if bda > 0 else 0
    n2g = rev / gross if gross > 0 else 0.3
    rev_per_bed = rev / beds if beds > 0 else 0

    # State peers
    state_df = hcris_df[hcris_df["state"] == state] if state else hcris_df
    nat_df = hcris_df

    def _peer_stats(df, col):
        vals = df[col].dropna()
        if len(vals) < 5:
            return {}
        return {"p25": float(vals.quantile(0.25)), "median": float(vals.median()),
                "p75": float(vals.quantile(0.75)), "mean": float(vals.mean())}

    # Bridge computation
    from .ebitda_bridge_page import _compute_bridge, _compute_returns_grid, _load_data_room_overrides
    dr_overrides = _load_data_room_overrides(db_path, ccn) if db_path else {}
    bridge = _compute_bridge(rev, ebitda, medicare_pct=mc_pct, overrides=dr_overrides)

    # Returns scenarios
    base_grid = _compute_returns_grid(ebitda, bridge["total_ebitda_impact"],
                                       [10.0], [10.0, 11.0], hold_years=5)
    bull_grid = _compute_returns_grid(ebitda, bridge["total_ebitda_impact"] * 1.3,
                                       [9.0], [11.0, 12.0], hold_years=5)
    bear_grid = _compute_returns_grid(ebitda, bridge["total_ebitda_impact"] * 0.5,
                                       [11.0], [10.0, 11.0], hold_years=5)

    # Investability
    try:
        from ..ml.investability_scorer import compute_investability
        invest = compute_investability(ccn, hcris_df)
    except Exception:
        invest = None

    # Clustering
    try:
        from ..ml.hospital_clustering import get_hospital_cluster
        cluster = get_hospital_cluster(ccn, hcris_df)
    except Exception:
        cluster = None

    # Distress
    try:
        from ..ml.distress_predictor import predict_distress
        distress = predict_distress(ccn, hcris_df)
    except Exception:
        distress = None

    # Comps
    size_lo = max(10, beds * 0.5)
    size_hi = beds * 2.0
    comps = hcris_df[(hcris_df["beds"] >= size_lo) & (hcris_df["beds"] <= size_hi) & (hcris_df["ccn"] != ccn)]
    state_comps = comps[comps["state"] == state] if state else comps
    if len(state_comps) >= 8:
        comp_df = state_comps
    else:
        comp_df = comps

    return {
        "ccn": ccn, "name": name, "state": state, "county": county,
        "beds": beds, "revenue": rev, "opex": opex, "ebitda": ebitda,
        "margin": margin, "gross": gross, "mc_pct": mc_pct, "md_pct": md_pct,
        "comm_pct": comm_pct, "occupancy": occupancy, "n2g": n2g,
        "rev_per_bed": rev_per_bed, "bridge": bridge,
        "base_grid": base_grid, "bull_grid": bull_grid, "bear_grid": bear_grid,
        "invest": invest, "cluster": cluster, "distress": distress,
        "comp_df": comp_df, "state_df": state_df, "nat_df": nat_df,
        "n_comps": len(comp_df), "n_state": len(state_df),
    }


def render_ic_memo(
    ccn: str,
    hcris_df: pd.DataFrame,
    db_path: Optional[str] = None,
    *,
    print_preview: bool = False,
) -> str:
    """Render a complete IC memo for a hospital.

    ``print_preview`` (set when the route handler sees ``?print=1``)
    applies the ``ck-print-preview`` class to the body, which the
    chartis shell's CSS uses to render the page exactly as it would
    print: hides the topnav, breadcrumbs, TOC, palette, and the
    tour overlay so the partner sees the LP-facing deliverable
    before hitting Cmd+P.
    """
    from .provenance import source_tag, Source

    def _src_tag(src: str) -> str:
        src_map = {"hcris": Source.HCRIS, "ml": Source.ML_PREDICTION,
                   "computed": Source.COMPUTED, "seller": Source.SELLER,
                   "benchmark": Source.BENCHMARK, "default": Source.DEFAULT}
        return source_tag(src_map.get(src, Source.DEFAULT))

    data = _build_memo_data(ccn, hcris_df, db_path=db_path)
    if data is None:
        return chartis_shell(
            f'<div class="cad-card"><p>Hospital {_html.escape(ccn)} not found or has insufficient data.</p></div>',
            "IC Memo", subtitle="Error",
        )

    ts = datetime.now(timezone.utc).strftime("%B %d, %Y")
    sections = []

    # ── HEADER ──
    invest_grade = data["invest"].grade if data["invest"] else "—"
    grade_colors = {"A": "var(--cad-pos)", "B": "var(--cad-accent)", "C": "var(--cad-warn)", "D": "var(--cad-neg)"}
    gc = grade_colors.get(invest_grade, "var(--cad-text3)")

    # Editorial dark-navy hero band — matches the workbench treatment.
    grade_tone_map = {
        "A": "#7ED3A8", "B": "#A6D3F2",
        "C": "#E8B97E", "D": "#E89478",
    }
    grade_color = grade_tone_map.get(invest_grade, "rgba(250, 247, 240, 0.55)")
    # Mode-aware eyebrow: PE-partner IC memo vs Chartis consulting
    # diligence readout. Headline + body are unchanged.
    from ._workspace_mode import current_workspace_mode, CONSULTING
    _is_consulting = current_workspace_mode() == CONSULTING
    _memo_eyebrow = (
        f"COMMERCIAL DILIGENCE READOUT · CCN {_html.escape(ccn)}"
        if _is_consulting
        else f"INVESTMENT COMMITTEE MEMORANDUM · CCN {_html.escape(ccn)}"
    )
    intro = ck_section_intro(
        eyebrow=_memo_eyebrow,
        headline=_html.escape(data["name"]),
        body=(
            f"{_html.escape(data['county'])}, {_html.escape(data['state'])} · "
            f"{data['beds']:.0f} beds · As of {_html.escape(ts)}"
        ),
        italic_word="committee" if not _is_consulting else "diligence",
    )
    grade_kpi = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Investability", _html.escape(invest_grade),
            sub="composite grade A–D",
        )
        + "</div>"
    )
    sections.append(intro + grade_kpi)
    sections.append(
        '<div class="ic-utility no-print">'
        '<div class="ic-utility-inner">'
        '<button onclick="window.print()" class="cad-btn cad-btn-primary">'
        '&#128438; Export PDF</button>'
        f'<a href="/ebitda-bridge/{_html.escape(ccn)}" class="cad-btn">EBITDA Bridge</a>'
        f'<a href="/data-room/{_html.escape(ccn)}" class="cad-btn">Data Room</a>'
        '</div>'
        '</div>'
    )

    # ── 1. TARGET OVERVIEW & THESIS ──
    thesis = "Undervalued" if data["margin"] < 0.05 and data["beds"] > 100 else "Platform Growth" if data["beds"] > 200 else "Turnaround"
    archetype = data["cluster"].label if data["cluster"] else "Community Hospital"
    distress_prob = data["distress"].distress_probability if data["distress"] else 0

    section1_inner = (
        '<div class="ic-memo-grid-2col">'
        '<div class="ck-section-body">'
        f'<p><strong>{_html.escape(data["name"])}</strong> is a {data["beds"]:.0f}-bed '
        f'{_html.escape(archetype.lower())} in {_html.escape(data["county"])}, {_html.escape(data["state"])} '
        f'with {_fm(data["revenue"])} in net patient revenue and a '
        f'{_pct(data["margin"])} operating margin. '
        f'The hospital serves a payer mix of {_pct(data["mc_pct"])} Medicare, '
        f'{_pct(data["md_pct"])} Medicaid, and {_pct(data["comm_pct"])} commercial.</p>'
        f'<p><strong>Thesis: {thesis}.</strong> Our ML models identify '
        f'{_fm(data["bridge"]["total_ebitda_impact"])} in annual EBITDA improvement potential '
        f'from RCM optimization across {len([l for l in data["bridge"]["levers"] if l["ebitda_impact"] > 0])} '
        f'levers, lifting margin from {_pct(data["margin"])} to '
        f'{_pct(data["bridge"]["new_margin"])} '
        f'(+{data["bridge"]["margin_improvement_bps"]:.0f}bps).</p></div>'
        '<div>'
        '<table class="cad-table">'
        f'<tr><td>Net Revenue {_src_tag("hcris")}</td>'
        f'<td class="num"><strong>{_fm(data["revenue"])}</strong></td></tr>'
        f'<tr><td>Current EBITDA {_src_tag("computed")}</td>'
        f'<td class="num">{_fm(data["ebitda"])}</td></tr>'
        f'<tr><td>Operating Margin {_src_tag("computed")}</td>'
        f'<td class="num">{_pct(data["margin"])}</td></tr>'
        f'<tr><td>Occupancy {_src_tag("hcris")}</td>'
        f'<td class="num">{_pct(data["occupancy"])}</td></tr>'
        f'<tr><td>Revenue / Bed {_src_tag("computed")}</td>'
        f'<td class="num">{_fm(data["rev_per_bed"])}</td></tr>'
        f'<tr><td>Net-to-Gross {_src_tag("hcris")}</td>'
        f'<td class="num">{_pct(data["n2g"])}</td></tr>'
        f'<tr><td>Distress Probability {_src_tag("ml")}</td>'
        f'<td class="num">{_pct(distress_prob)}</td></tr>'
        '</table></div></div>'
    )
    sections.append(ck_panel(
        section1_inner,
        title="1. Target Overview & Investment Thesis",
        anchor_id="s1-overview",
    ))

    # ── 2. MARKET CONTEXT ──
    n_st = data["n_state"]
    st_margins = data["state_df"]["operating_margin"].dropna() if "operating_margin" in data["state_df"].columns else pd.Series(dtype=float)
    st_med_margin = float(st_margins.median()) if len(st_margins) > 5 else 0

    comp_margins = data["comp_df"]["operating_margin"].dropna() if "operating_margin" in data["comp_df"].columns else pd.Series(dtype=float)
    comp_med_margin = float(comp_margins.median()) if len(comp_margins) > 3 else 0

    section2_inner = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            f"{_html.escape(data['state'])} Hospitals", f"{n_st}",
        )
        + ck_kpi_block(
            "State Median Margin", _pct(st_med_margin),
        )
        + ck_kpi_block(
            "Comparable Hospitals", f"{data['n_comps']}",
        )
        + '</div>'
        + '<p class="ck-section-body">'
        f'{_html.escape(data["state"])} has {n_st} Medicare-certified hospitals with a '
        f'median operating margin of {_pct(st_med_margin)}. The target\'s margin of '
        f'{_pct(data["margin"])} places it '
        f'{"above" if data["margin"] > st_med_margin else "below"} the state median. '
        f'Among {data["n_comps"]} size-comparable peers ({data["beds"]*0.5:.0f}-{data["beds"]*2:.0f} beds), '
        f'the median margin is {_pct(comp_med_margin)}. '
        f'{("The target’s below-peer margin suggests operational improvement opportunity." if data["margin"] < comp_med_margin else "The target performs in line with or above peers.")}'
        '</p>'
    )
    sections.append(ck_panel(
        section2_inner,
        title="2. Market Context & Competitive Position",
        anchor_id="s2-market",
    ))

    # ── 3. RCM PERFORMANCE ANALYSIS WITH COMPS ──
    comp_rows = ""
    comp_sample = data["comp_df"].nlargest(8, "net_patient_revenue") if len(data["comp_df"]) > 0 else pd.DataFrame()
    for _, row in comp_sample.iterrows():
        c_rev = float(row.get("net_patient_revenue", 0))
        c_margin = float(row.get("operating_margin", 0)) if "operating_margin" in row.index else 0
        c_beds = int(row.get("beds", 0))
        comp_rows += (
            f'<tr>'
            f'<td>{_html.escape(str(row.get("name", ""))[:30])}</td>'
            f'<td>{_html.escape(str(row.get("state", "")))}</td>'
            f'<td class="num">{c_beds}</td>'
            f'<td class="num">{_fm(c_rev)}</td>'
            f'<td class="num">{_pct(c_margin)}</td>'
            f'</tr>'
        )

    # Peer-margin dot plot — visual where-do-we-sit before the table
    peer_margins_list = (
        list(data["comp_df"]["operating_margin"].dropna().values)
        if "operating_margin" in data["comp_df"].columns else []
    )
    peer_chart = (
        _peer_margin_dotplot(data["margin"], peer_margins_list)
        if peer_margins_list else ""
    )
    chart_caption = (
        '<div class="ic-memo-chart-caption">'
        f'Operating margin · target vs. {len(peer_margins_list)} size-matched peers'
        '</div>'
    ) if peer_chart else ""

    section3_inner = (
        '<p class="ck-section-body">'
        f'Comps selected by bed count ({data["beds"]*0.5:.0f}-{data["beds"]*2:.0f}), '
        f'prioritizing same-state peers. {data["n_comps"]} hospitals in the comp set.</p>'
        + peer_chart + chart_caption +
        '<table class="cad-table"><thead><tr>'
        '<th>Hospital</th><th>State</th><th>Beds</th><th>Revenue</th><th>Margin</th>'
        '</tr></thead><tbody>'
        '<tr class="ic-memo-row-target">'
        f'<td><strong>{_html.escape(data["name"][:30])} (Target)</strong></td>'
        f'<td>{_html.escape(data["state"])}</td>'
        f'<td class="num">{data["beds"]:.0f}</td>'
        f'<td class="num">{_fm(data["revenue"])}</td>'
        f'<td class="num">{_pct(data["margin"])}</td></tr>'
        f'{comp_rows}</tbody></table>'
    )
    sections.append(ck_panel(
        section3_inner,
        title="3. RCM Performance Analysis — Comparable Hospitals",
        anchor_id="s3-rcm",
    ))

    # ── 4. PREDICTED IMPROVEMENT OPPORTUNITIES ──
    lever_rows = ""
    for lev in data["bridge"]["levers"]:
        if lev["ebitda_impact"] == 0:
            continue
        lever_rows += (
            f'<tr>'
            f'<td><strong>{_html.escape(lev["name"])}</strong></td>'
            f'<td class="num">{lev["current"]:.1%}</td>'
            f'<td class="num cad-pos">{lev["target"]:.1%}</td>'
            f'<td class="num cad-pos"><strong>{_fm(lev["ebitda_impact"])}</strong></td>'
            f'<td class="num">+{lev["margin_bps"]:.0f}bp</td>'
            f'<td class="num">{lev["ramp_months"]}mo</td>'
            f'</tr>'
        )

    section4_inner = (
        '<p class="ck-section-body">'
        'Improvement targets set at P75 of comparable peers with 60% gap closure assumption. '
        'Coefficients calibrated to published research bands. '
        f'Total EBITDA uplift: <strong>{_fm(data["bridge"]["total_ebitda_impact"])}</strong> '
        f'({data["bridge"]["margin_improvement_bps"]:.0f}bps margin improvement).</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>Lever</th><th>Current</th><th>Target</th><th>EBITDA Impact</th><th>Margin</th><th>Ramp</th>'
        f'</tr></thead><tbody>{lever_rows}</tbody></table>'
    )
    sections.append(ck_panel(
        section4_inner,
        title="4. Predicted Improvement Opportunities",
        anchor_id="s4-predicted",
    ))

    # ── 5. EBITDA BRIDGE ──
    max_bar = max(abs(l["ebitda_impact"]) for l in data["bridge"]["levers"] if l["ebitda_impact"] != 0) or 1
    waterfall = ""
    for lev in data["bridge"]["levers"]:
        if lev["ebitda_impact"] == 0:
            continue
        bar_pct = min(100, abs(lev["ebitda_impact"]) / max_bar * 75)
        waterfall += (
            '<div class="ic-memo-bar-row">'
            f'<div class="ic-memo-bar-label">{_html.escape(lev["name"])}</div>'
            '<div class="ic-memo-bar-track">'
            f'<div class="ic-memo-bar-fill" style="width:{bar_pct:.0f}%;">'
            f'{_fm(lev["ebitda_impact"])}</div></div></div>'
        )

    section5_inner = (
        '<div class="ic-memo-grid-2col">'
        f'<div>{waterfall}'
        '<div class="ic-memo-bar-total">'
        '<span>Total EBITDA Uplift</span>'
        f'<span class="cad-pos">{_fm(data["bridge"]["total_ebitda_impact"])}</span></div></div>'
        '<div>'
        '<table class="cad-table">'
        f'<tr><td>Current EBITDA</td><td class="num">{_fm(data["ebitda"])}</td></tr>'
        '<tr><td>+ RCM Uplift</td>'
        f'<td class="num cad-pos">+{_fm(data["bridge"]["total_ebitda_impact"])}</td></tr>'
        '<tr class="ic-memo-row-strong">'
        f'<td>Pro Forma EBITDA</td><td class="num">{_fm(data["bridge"]["new_ebitda"])}</td></tr>'
        f'<tr><td>Current Margin</td><td class="num">{_pct(data["margin"])}</td></tr>'
        '<tr><td>Pro Forma Margin</td>'
        f'<td class="num cad-pos">{_pct(data["bridge"]["new_margin"])}</td></tr>'
        f'<tr><td>WC Released (1x)</td><td class="num">{_fm(data["bridge"]["total_wc_released"])}</td></tr>'
        '</table></div></div>'
    )
    sections.append(ck_panel(
        section5_inner, title="5. EBITDA Bridge",
        anchor_id="s5-bridge",
    ))

    # ── 6. RETURNS ANALYSIS ──
    def _scenario_row(label, grid, row_cls=""):
        if not grid:
            return ""
        g = grid[0]
        irr_cls = (
            "cad-pos" if g["irr"] > 0.20
            else "cad-warn" if g["irr"] > 0.15
            else "cad-neg"
        )
        cls_attr = f' class="{row_cls}"' if row_cls else ""
        return (
            f'<tr{cls_attr}>'
            f'<td><strong>{label}</strong></td>'
            f'<td class="num">{g["entry_multiple"]:.1f}x</td>'
            f'<td class="num">{g["exit_multiple"]:.1f}x</td>'
            f'<td class="num">{_fm(g["entry_equity"])}</td>'
            f'<td class="num">{_fm(g["exit_equity"])}</td>'
            f'<td class="num"><strong>{g["moic"]:.2f}x</strong></td>'
            f'<td class="num {irr_cls}"><strong>{_pct(g["irr"])}</strong></td>'
            '</tr>'
        )

    scenarios = (
        _scenario_row("Base Case", data["base_grid"][:1]) +
        _scenario_row("Base (11x exit)", data["base_grid"][1:2]) +
        _scenario_row("Bull Case", data["bull_grid"][:1]) +
        _scenario_row("Bull (12x exit)", data["bull_grid"][1:2]) +
        _scenario_row("Bear Case", data["bear_grid"][:1], "ic-memo-row-bear") +
        _scenario_row("Bear (11x exit)", data["bear_grid"][1:2])
    )

    # Editorial scenario chart — IRR bars per case with 20% target line
    scenario_chart_rows = []
    for label, grid, tone in (
        ("Base", data["base_grid"][:1], "warn"),
        ("Bull", data["bull_grid"][:1], "pos"),
        ("Bear", data["bear_grid"][:1], "neg"),
    ):
        if grid:
            g = grid[0]
            tone_resolved = (
                "pos" if g["irr"] > 0.20
                else "warn" if g["irr"] > 0.15
                else "neg"
            )
            scenario_chart_rows.append({
                "label": label, "irr": g["irr"], "moic": g["moic"],
                "tone": tone_resolved,
            })
    scenario_chart = _scenario_returns_chart(scenario_chart_rows)
    scenario_caption = (
        '<div class="ic-memo-chart-caption">'
        'IRR by scenario · dashed line = 20% partner-hurdle benchmark'
        '</div>'
    ) if scenario_chart else ""

    section6_inner = (
        '<p class="ck-section-body">'
        '5-year hold, 5.5x leverage, 3% organic growth, 10%/yr debt paydown. '
        'Base case uses 100% of predicted RCM uplift. Bull case: 130% uplift at lower entry. '
        'Bear case: 50% uplift at higher entry.</p>'
        + scenario_chart + scenario_caption +
        '<table class="cad-table"><thead><tr>'
        '<th>Scenario</th><th>Entry</th><th>Exit</th><th>Equity In</th>'
        '<th>Equity Out</th><th>MOIC</th><th>IRR</th>'
        f'</tr></thead><tbody>{scenarios}</tbody></table>'
    )
    sections.append(ck_panel(
        section6_inner, title="6. Returns Analysis — Scenario Matrix",
        anchor_id="s6-returns",
    ))

    # ── 7. KEY RISKS & MITIGANTS ──
    risks = []
    if data["margin"] < 0:
        risks.append(("Negative operating margin", "RCM uplift bridge shows clear path to profitability; working capital release provides near-term cash cushion", "High"))
    if data["mc_pct"] > 0.55:
        risks.append(("Heavy Medicare dependence", f"Medicare comprises {_pct(data['mc_pct'])} of days; rate updates may lag inflation. Mitigant: CDI/CMI lever directly increases Medicare reimbursement", "Medium"))
    if data["md_pct"] > 0.22:
        risks.append((f"Elevated Medicaid exposure ({_pct(data['md_pct'])})", "Medicaid reimburses below cost in most states. Mitigant: denial reduction lever has highest impact on Medicaid claims", "Medium"))
    if data["occupancy"] < 0.35:
        risks.append(("Low occupancy", f"At {_pct(data['occupancy'])}, fixed costs are spread over fewer patient days. Mitigant: volume growth is an additional upside lever not modeled in base case", "Medium"))
    if distress_prob > 0.5:
        risks.append(("Elevated distress probability", f"Model estimates {_pct(distress_prob)} probability of financial distress. Mitigant: distressed entry pricing (7-9x) compensates for risk", "High"))
    if data["n2g"] < 0.2:
        risks.append(("Low net-to-gross ratio", "Large contractual allowances suggest pricing discipline issues. Mitigant: payer renegotiation is an additional upside lever", "Low"))

    if not risks:
        risks.append(("Standard execution risk", "RCM improvement requires management buy-in and 12-18 month implementation timeline", "Medium"))

    risk_rows = ""
    for risk, mitigant, severity in risks:
        sev_tone = {
            "High": "negative", "Medium": "warning", "Low": "positive",
        }.get(severity, "neutral")
        sev_badge = ck_signal_badge(severity, tone=sev_tone)
        risk_rows += (
            f'<tr>'
            f'<td>{sev_badge}</td>'
            f'<td><strong>{_html.escape(risk)}</strong></td>'
            f'<td>{_html.escape(mitigant)}</td>'
            f'</tr>'
        )

    section7_inner = (
        '<table class="cad-table"><thead><tr>'
        '<th>Severity</th><th>Risk Factor</th><th>Mitigant</th>'
        f'</tr></thead><tbody>{risk_rows}</tbody></table>'
    )
    sections.append(ck_panel(
        section7_inner, title="7. Key Risks & Mitigants",
        anchor_id="s7-risks",
    ))

    # ── 8. DATA SOURCES & METHODOLOGY ──
    state_size_match = len(data["state_df"][data["state_df"]["beds"].between(
        data["beds"] * 0.5, data["beds"] * 2,
    )])
    section8_inner = (
        '<div class="ic-memo-grid-2col">'
        '<div>'
        + ck_section_header("Data Sources", eyebrow="DAT")
        + '<ul class="ck-list">'
        '<li>CMS HCRIS Cost Reports (Medicare-certified hospitals)</li>'
        '<li>CMS Medicare Utilization (DRG-level volumes)</li>'
        '<li>CMS Chronic Conditions (county-level disease prevalence)</li>'
        '<li>HCRIS multi-year trend data (financial time series)</li></ul>'
        + ck_section_header("Comparable Selection", eyebrow="COMP")
        + '<ul class="ck-list">'
        f'<li>{data["n_comps"]} hospitals with {data["beds"]*0.5:.0f}-{data["beds"]*2:.0f} beds</li>'
        f'<li>Same-state prioritization (n={state_size_match})</li>'
        f'<li>Comp margins: P25={_pct(float(comp_margins.quantile(0.25)))} / '
        f'P50={_pct(comp_med_margin)} / P75={_pct(float(comp_margins.quantile(0.75)))}</li></ul>'
        '</div>'
        '<div>'
        + ck_section_header("Bridge Methodology", eyebrow="BRG")
        + '<ul class="ck-list">'
        '<li>Targets: P75 of comparable peers (60% gap closure)</li>'
        '<li>Denial: avoidable share = 35% of delta × NPR</li>'
        '<li>AR: bad debt coefficient = $0.65 per day per $1K NPR</li>'
        '<li>NCR: 60% coefficient on collection rate improvement</li>'
        '<li>CDI: 0.75% of Medicare revenue per 0.01 CMI point</li></ul>'
        + ck_section_header("Returns Assumptions", eyebrow="LBO")
        + '<ul class="ck-list">'
        '<li>Leverage: 5.5x entry (84.6% debt / 15.4% equity)</li>'
        '<li>Organic growth: 3% annual EBITDA growth</li>'
        '<li>Debt paydown: 10% of principal per year</li>'
        '<li>Hold period: 5 years</li></ul>'
        '</div></div>'
        '<p class="ck-eyebrow">'
        f'Generated by PE Desk on {ts}. All predictions use public data only. '
        'Confidence intervals calibrated via split conformal prediction (90% coverage target). '
        'This memo is for informational purposes and does not constitute investment advice.</p>'
    )
    sections.append(ck_panel(
        section8_inner,
        title="8. Data Sources & Methodology Appendix",
        anchor_id="s8-methodology",
    ))

    # ── ACTIONS ──
    actions_inner = (
        '<p class="ck-section-body">'
        f'<a href="/ebitda-bridge/{_html.escape(ccn)}" class="cad-btn cad-btn-primary">Full EBITDA Bridge</a> '
        f'<a href="/ml-insights/hospital/{_html.escape(ccn)}" class="cad-btn">ML Analysis</a> '
        f'<a href="/hospital/{_html.escape(ccn)}" class="cad-btn">Hospital Profile</a> '
        f'<a href="/portfolio/regression/hospital/{_html.escape(ccn)}" class="cad-btn">Statistical Profile</a> '
        '<a href="/predictive-screener" class="cad-btn">Deal Screener</a>'
        '</p>'
    )
    sections.append(ck_panel(
        actions_inner, title="Cross-links",
        anchor_id="s9-crosslinks",
    ))

    # Sticky right-rail table of contents — the IC memo runs ~9
    # sections and partners commonly jump to a specific chapter
    # (Risks, Returns, Bridge) rather than reading top-to-bottom.
    toc = ck_sticky_toc([
        {"id": "s1-overview",    "title": "1. Target Overview"},
        {"id": "s2-market",      "title": "2. Market Context"},
        {"id": "s3-rcm",         "title": "3. RCM Performance"},
        {"id": "s4-predicted",   "title": "4. Improvement Opportunities"},
        {"id": "s5-bridge",      "title": "5. EBITDA Bridge"},
        {"id": "s6-returns",     "title": "6. Returns Analysis"},
        {"id": "s7-risks",       "title": "7. Key Risks & Mitigants"},
        {"id": "s8-methodology", "title": "8. Methodology"},
        {"id": "s9-crosslinks",  "title": "Cross-links"},
    ])
    # Print-preview affordance — partners often want to see the LP-
    # facing deliverable before hitting Cmd+P. ?print=1 wraps the
    # memo in .ck-print-preview which the chartis shell CSS uses to
    # hide chrome, max-width the page, and lighten the panel borders
    # so the on-screen render matches the printed PDF. A small
    # editorial "Exit preview" link sits at the top-right.
    if print_preview:
        body = (
            '<div class="ck-print-preview">'
            '<div class="ck-print-preview-bar">'
            f'<span class="ck-print-preview-meta">Print preview · '
            f'CCN {_html.escape(ccn)}</span>'
            f'<a href="/ic-memo/{_html.escape(ccn)}" '
            'class="ck-print-preview-exit">Exit preview</a>'
            '</div>'
            + "\n".join(sections)
            + '</div>'
        )
    else:
        # Deal-context ribbon (no-print) so a reviewer can jump from the
        # memo to any sibling analysis on the deal; hidden when the memo
        # is printed/exported.
        from .models_page import _model_nav
        deal_ribbon = (
            '<div class="no-print">'
            + _model_nav(ccn, active="ic_memo")
            + '</div>'
        )
        body = (
            deal_ribbon
            + f'<div class="ck-print-preview-cta">'
            f'<a href="/ic-memo/{_html.escape(ccn)}?print=1" '
            'class="ck-link">Preview print version →</a>'
            '</div>'
            '<div class="ck-toc-layout">'
            + toc
            + '<div class="ck-toc-content">'
            + "\n".join(sections)
            + '</div></div>'
            + ck_next_section(
                "Open the IC packet",
                "/diligence/ic-packet",
                eyebrow="Continue —",
                italic_word="packet",
            )
        )

    return chartis_shell(
        body,
        f"IC Memo — {_html.escape(data['name'])}",
        subtitle=(
            f"Investment Committee Memorandum | {_html.escape(data['state'])} | "
            f"{data['beds']:.0f} beds | Grade {invest_grade} | "
            f"EBITDA uplift {_fm(data['bridge']['total_ebitda_impact'])}"
        ),
        extra_css=(
            _IC_MEMO_CSS +
            "@media print { .cad-nav, .cad-topbar, .cad-ticker, .no-print { display: none !important; } "
            ".cad-main { margin: 0 !important; padding: 20px !important; } "
            ".cad-card { break-inside: avoid; } "
            ".ic-memo-bar-fill, .ic-memo-bar-total { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }"
        ),
    )
