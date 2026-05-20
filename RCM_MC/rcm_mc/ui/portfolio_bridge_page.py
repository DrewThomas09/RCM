"""PE Desk Portfolio EBITDA Bridge — aggregate value creation.

Runs the EBITDA bridge for every hospital in the pipeline and
aggregates the results. Shows total uplift, per-deal breakdown,
lever-by-lever attribution, and portfolio-level returns.

This is the managing partner's view: "What's our total value
creation opportunity across the fund?"
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..portfolio.store import PortfolioStore
from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro,
)
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


_PB_CHART_CAPTION_CSS = (
    ".pb-figcap{font-size:11px;color:#6b6456;margin:6px 0 8px;"
    "font-family:'JetBrains Mono',ui-monospace,monospace;"
    "letter-spacing:0.02em;}"
)


def _deal_uplift_chart(
    deal_results: List[Dict[str, Any]], width: int = 700, row_h: int = 24
) -> str:
    """Horizontal bars of projected EBITDA uplift per pipeline hospital.

    Surfaces concentration — which deals carry the portfolio's value-
    creation case — sorted descending, tone-faded by rank. Reads the
    same uplift the per-deal table shows. Empty input returns "".
    """
    rows = [d for d in (deal_results or [])
            if d.get("name") and d.get("uplift", 0) > 0]
    rows = sorted(rows, key=lambda d: -d["uplift"])[:12]
    if not rows:
        return ""
    max_up = max((d["uplift"] for d in rows), default=0) or 1.0

    pad_l, pad_r, pad_t = 180, 70, 8
    bar_max = width - pad_l - pad_r
    height = pad_t + row_h * len(rows) + 8

    pos = PALETTE["positive"]
    rule = PALETTE.get("border", "#BFB6A2")
    txt = PALETTE.get("text_secondary", "#4a5568")

    parts: List[str] = [
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Projected EBITDA uplift by pipeline hospital" '
        f'style="width:100%;max-width:{width}px;height:auto;'
        f'print-color-adjust:exact;-webkit-print-color-adjust:exact;">'
    ]
    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t - 2}" x2="{pad_l}" '
        f'y2="{height - 6}" stroke="{rule}" stroke-width="1"/>'
    )
    for i, d in enumerate(rows):
        name = _html.escape(str(d["name"])[:28])
        up = d["uplift"]
        y = pad_t + i * row_h
        w = up / max_up * bar_max
        op = 0.9 - (i / max(len(rows), 1)) * 0.5
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + row_h / 2 + 3:.1f}" '
            f'text-anchor="end" font-size="11" '
            f'font-family="Inter Tight,system-ui,sans-serif" '
            f'fill="{txt}">{name}</text>'
        )
        parts.append(
            f'<rect x="{pad_l}" y="{y + 3:.1f}" width="{max(w, 0.5):.1f}" '
            f'height="{row_h - 8}" rx="2" fill="{pos}" opacity="{op:.2f}"/>'
        )
        parts.append(
            f'<text x="{pad_l + w + 6:.1f}" y="{y + row_h / 2 + 3:.1f}" '
            f'text-anchor="start" font-size="10" '
            f'font-family="JetBrains Mono,ui-monospace,monospace" '
            f'fill="{txt}">+{_fm(up)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def render_portfolio_bridge(
    hcris_df: pd.DataFrame,
    db_path: str,
) -> str:
    """Render the portfolio-level EBITDA bridge."""
    from ..data.pipeline import list_pipeline, _ensure_tables
    from .ebitda_bridge_page import (
        _compute_bridge, _load_data_room_overrides, compute_peer_targets,
    )

    # Route through PortfolioStore (campaign target 4E) so the
    # connection inherits PRAGMA foreign_keys=ON, busy_timeout=
    # 5000, and row_factory=Row instead of running on a bare
    # sqlite3.connect that misses all three.
    with PortfolioStore(db_path).connect() as con:
        _ensure_tables(con)
        hospitals = list_pipeline(con)

    active = [h for h in hospitals if h.stage not in ("passed",)]

    if not active:
        empty_intro = ck_section_intro(
            eyebrow="PORTFOLIO BRIDGE",
            headline="No pipeline hospitals yet.",
            italic_word="No",
            body=(
                "Add hospitals to the pipeline from the Deal "
                "Screener to see the portfolio-level EBITDA bridge."
            ),
        )
        return chartis_shell(
            empty_intro
            + ck_panel(
                '<p class="ck-section-body">'
                '<a href="/predictive-screener" class="cad-btn cad-btn-primary">'
                '→ Deal Screener</a></p>',
                title="Next step",
            ),
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

    # ── Editorial intro + KPI strip ──
    intro = ck_section_intro(
        eyebrow="PORTFOLIO BRIDGE",
        headline="Where the partner sees the whole pipeline at once.",
        italic_word="whole",
        body=(
            f"{n_deals} active pipeline deals · {_fm(total_revenue)} "
            f"revenue · projected +{_fm(total_uplift)} EBITDA uplift "
            f"({total_current_ebitda/total_revenue*100 if total_revenue > 0 else 0:.1f}% → "
            f"{total_new_ebitda/total_revenue*100 if total_revenue > 0 else 0:.1f}% margin)."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Pipeline Deals", f"{n_deals}")
        + ck_kpi_block("Total Revenue", _fm(total_revenue))
        + ck_kpi_block("Current EBITDA", _fm(total_current_ebitda))
        + ck_kpi_block("Total RCM Uplift", f"+{_fm(total_uplift)}")
        + ck_kpi_block("Pro Forma EBITDA", _fm(total_new_ebitda))
        + ck_kpi_block("Avg Margin Lift", f"+{avg_margin_improvement:.0f}bps")
        + '</div>'
    )

    # ── Per-deal breakdown ──
    deal_rows = ""
    for d in deal_results:
        ccn = _html.escape(d["ccn"])
        name = _html.escape(d["name"][:25])
        m_cls = "cad-pos" if d["current_margin"] > 0.03 else (
            "cad-warn" if d["current_margin"] > 0 else "cad-neg")
        seller_badge = (
            '<span class="cad-badge cad-badge-amber">S</span>' if d["has_seller"] else ""
        )

        deal_rows += (
            f'<tr>'
            f'<td><a href="/ebitda-bridge/{ccn}" class="ck-link"><strong>{name}</strong></a> {seller_badge}</td>'
            f'<td>{_html.escape(d["stage"])}</td>'
            f'<td class="num">{_fm(d["revenue"])}</td>'
            f'<td class="num {m_cls}">{d["current_margin"]:.1%}</td>'
            f'<td class="num cad-pos"><strong>+{_fm(d["uplift"])}</strong></td>'
            f'<td class="num">{d["new_margin"]:.1%}</td>'
            f'<td class="num">+{d["margin_bps"]:.0f}bp</td>'
            f'</tr>'
        )

    # Total row
    total_margin = total_current_ebitda / total_revenue if total_revenue > 0 else 0
    new_total_margin = total_new_ebitda / total_revenue if total_revenue > 0 else 0
    deal_rows += (
        '<tr class="cad-row-total">'
        '<td><strong>Portfolio Total</strong></td><td></td>'
        f'<td class="num">{_fm(total_revenue)}</td>'
        f'<td class="num">{total_margin:.1%}</td>'
        f'<td class="num cad-pos"><strong>+{_fm(total_uplift)}</strong></td>'
        f'<td class="num">{new_total_margin:.1%}</td>'
        f'<td class="num">+{avg_margin_improvement:.0f}bp</td>'
        '</tr>'
    )

    _uplift_chart = _deal_uplift_chart(deal_results)
    _uplift_fig = (
        f'<style>{_PB_CHART_CAPTION_CSS}</style>'
        f'<div class="pb-figcap">Projected EBITDA uplift by hospital '
        f'&middot; longest bar = top value-creation case</div>'
        f'{_uplift_chart}'
    ) if _uplift_chart else ""
    deal_section = ck_panel(
        '<p class="ck-section-body">'
        "Each deal's bridge computed from HCRIS + Data Room calibrations. "
        'Click any deal for the full 10-section bridge. '
        f'{source_tag(Source.SELLER)} = has seller data in Data Room.</p>'
        f'{_uplift_fig}'
        '<table class="cad-table"><thead><tr>'
        '<th>Hospital</th><th>Stage</th><th>Revenue</th><th>Margin</th>'
        '<th>Uplift</th><th>Pro Forma</th><th>Δ Margin</th>'
        f'</tr></thead><tbody>{deal_rows}</tbody></table>',
        title="Per-Deal EBITDA Bridge",
    )

    # ── Lever attribution across portfolio ──
    max_lever = max(lever_totals.values()) if lever_totals else 1
    lever_bars = ""
    for lever_name, total_val in sorted(lever_totals.items(), key=lambda x: -abs(x[1])):
        if total_val == 0:
            continue
        bar_pct = min(100, abs(total_val) / max_lever * 80)
        lever_bars += (
            '<div class="pb-bar-row">'
            f'<div class="pb-bar-name">{_html.escape(lever_name[:22])}</div>'
            '<div class="pb-bar-track">'
            f'<div class="pb-bar-fill" style="width:{bar_pct:.0f}%;">'
            f'{_fm(total_val)}</div></div></div>'
        )

    lever_section = ck_panel(
        '<p class="ck-section-body">'
        f'Total EBITDA uplift by RCM lever, aggregated across {n_deals} pipeline hospitals.</p>'
        f'{lever_bars}'
        '<p class="ck-section-body">'
        f'<strong>Total Portfolio Uplift &nbsp; '
        f'<span class="cad-pos">{_fm(total_uplift)}</span></strong></p>',
        title="Portfolio Lever Attribution",
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
            irr_cls = "cad-pos" if irr_r >= 0.20 else ("cad-warn" if irr_r >= 0.15 else "cad-neg")
            ret_rows += (
                f'<tr>'
                f'<td class="num">{exit_m:.0f}x</td>'
                f'<td class="num">{_fm(exit_ev_r)}</td>'
                f'<td class="num">{_fm(exit_eq)}</td>'
                f'<td class="num"><strong>{moic_r:.2f}x</strong></td>'
                f'<td class="num {irr_cls}"><strong>{irr_r:.1%}</strong></td>'
                f'</tr>'
            )

        returns_section = ck_panel(
            '<p class="ck-section-body">'
            f'Assumes all {n_deals} pipeline deals acquired at 10x entry, 3% organic growth, '
            f'10%/yr debt paydown. Entry equity: {_fm(entry_equity)}.</p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Exit Multiple</th><th>Exit EV</th><th>Exit Equity</th><th>MOIC</th><th>IRR</th>'
            f'</tr></thead><tbody>{ret_rows}</tbody></table>',
            title="Portfolio Returns (5-Year, 5.5x Leverage)",
        )

    nav = ck_panel(
        '<p class="ck-section-body">'
        '<a href="/pipeline" class="cad-btn cad-btn-primary">Pipeline</a> '
        '<a href="/portfolio/monitor" class="cad-btn">Portfolio Monitor</a> '
        '<a href="/predictive-screener" class="cad-btn">Deal Screener</a>'
        '</p>',
        title="Cross-links",
    )

    freshness = data_freshness_footer(
        hcris_year=2022, n_hospitals=len(hcris_df),
        has_seller_data=any(d["has_seller"] for d in deal_results),
        n_seller_metrics=sum(1 for d in deal_results if d["has_seller"]),
    )

    pb_styles = """
<style>
.pb-bar-row{display:flex;align-items:center;gap:8px;padding:5px 0;
border-bottom:1px solid var(--cad-border);}
.pb-bar-name{width:160px;font-size:12px;font-weight:500;}
.pb-bar-track{flex:1;background:var(--cad-bg3);border-radius:3px;height:16px;}
.pb-bar-fill{background:var(--cad-pos);border-radius:3px;
height:16px;display:flex;align-items:center;justify-content:flex-end;
padding-right:4px;font-size:10px;color:#fff;font-weight:600;min-width:35px;}
.pb-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
</style>
"""
    next_up = ck_next_section(
        "Open the portfolio monitor",
        "/portfolio/monitor",
        eyebrow="Continue —",
        italic_word="monitor",
    )
    body = (
        f'{pb_styles}{intro}{kpis}'
        '<div class="pb-grid">'
        f'<div>{deal_section}</div>'
        f'<div>{lever_section}{returns_section}</div></div>'
        f'{nav}{freshness}{next_up}'
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
