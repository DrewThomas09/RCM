"""PE Desk Financial Models — browser-rendered DCF, LBO, 3-Statement.

Renders financial model outputs as rich HTML tables instead of raw JSON.
Accessed via /models/dcf/<deal_id>, /models/lbo/<deal_id>, /models/financials/<deal_id>.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    SafeHtml,
    chartis_shell,
    ck_eyebrow,
    ck_kpi_block,
    ck_next_section,
    ck_provenance_tooltip,
)
from .brand import PALETTE


def _model_nav(deal_id: str, active: str = "") -> str:
    """Editorial deal-context ribbon — model + view shortcuts.

    Replaces the old Bloomberg-dark + amber-on-black treatment that
    looked alien against the editorial parchment. Now reads as a
    horizontal pill rail with the same hairline + bone-on-hover feel
    as the rest of the v5 chrome.
    """
    did = html.escape(deal_id)
    groups = [
        ("PRF", "Profile", f"/hospital/{did}", "profile"),
        ("MEM", "IC Memo", f"/ic-memo/{did}", "ic_memo"),
        ("BRG", "Bridge", f"/ebitda-bridge/{did}", "ebitda_bridge"),
        ("CI", "Comp Intel", f"/competitive-intel/{did}", "comp_intel"),
        ("SCN", "Scenarios", f"/scenarios/{did}", "scenarios"),
        ("AI", "ML", f"/ml-insights/hospital/{did}", "ml"),
        ("DCF", "DCF", f"/models/dcf/{did}", "dcf"),
        ("LBO", "LBO", f"/models/lbo/{did}", "lbo"),
        ("FIN", "3-Stmt", f"/models/financials/{did}", "financials"),
        ("MKT", "Market", f"/models/market/{did}", "market"),
        ("DEN", "Denial", f"/models/denial/{did}", "denial"),
        ("RET", "Returns", f"/models/returns/{did}", "returns"),
        ("LVR", "Levers", f"/models/bridge/{did}", "bridge"),
        ("WFL", "Waterfall", f"/models/waterfall/{did}", "waterfall"),
        ("PLY", "Playbook", f"/models/playbook/{did}", "playbook"),
        ("TRD", "Trends", f"/models/trends/{did}", "trends"),
        ("PRED", "Predicted", f"/models/predicted/{did}", "predicted"),
        ("MEM2", "Memo", f"/models/memo/{did}", "memo"),
    ]
    items = []
    for code, label, href, key in groups:
        is_active = " active" if key == active else ""
        items.append(
            f'<a href="{href}" class="ck-model-pill{is_active}">'
            f'<span class="ck-model-pill-code">{code}</span>'
            f'<span class="ck-model-pill-label">{html.escape(label)}</span>'
            f'</a>'
        )
    return (
        '<style>'
        '.ck-model-rail{display:flex;flex-wrap:wrap;align-items:center;'
        'gap:6px;padding:10px 14px;margin:0 0 18px;'
        'background:#fff;border:1px solid var(--sc-rule,#d6cfc0);'
        'border-radius:2px;box-shadow:var(--sc-shadow-1);}'
        '.ck-model-rail-back{display:inline-flex;align-items:center;gap:6px;'
        'padding:5px 12px;margin-right:6px;'
        'background:var(--sc-bone,#ece5d6);'
        'border:1px solid var(--sc-rule,#d6cfc0);border-radius:2px;'
        'font-family:var(--sc-mono,JetBrains Mono,monospace);'
        'font-size:10.5px;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:var(--sc-text-dim,#465366);'
        'text-decoration:none;}'
        '.ck-model-rail-back:hover{background:var(--sc-navy,#0b2341);'
        'color:#fff;border-color:var(--sc-navy,#0b2341);}'
        '.ck-model-pill{display:inline-flex;align-items:center;gap:6px;'
        'padding:5px 10px;border:1px solid transparent;border-radius:2px;'
        'text-decoration:none;color:var(--sc-text-dim,#465366);'
        'font-family:var(--sc-sans,Inter,sans-serif);'
        'transition:background 0.12s,color 0.12s,border-color 0.12s;}'
        '.ck-model-pill:hover{background:var(--sc-bone,#ece5d6);'
        'color:var(--sc-navy,#0b2341);'
        'border-color:var(--sc-rule,#d6cfc0);}'
        '.ck-model-pill.active{background:var(--sc-navy,#0b2341);'
        'color:#fff;border-color:var(--sc-navy,#0b2341);}'
        '.ck-model-pill-code{font-family:var(--sc-mono,JetBrains Mono,monospace);'
        'font-size:9.5px;font-weight:700;letter-spacing:0.1em;'
        'padding:1px 5px;background:var(--sc-bone,#ece5d6);'
        'color:var(--sc-text-dim,#465366);border-radius:2px;}'
        '.ck-model-pill:hover .ck-model-pill-code{'
        'background:#fff;color:var(--sc-navy,#0b2341);}'
        '.ck-model-pill.active .ck-model-pill-code{'
        'background:var(--sc-teal,#155752);color:#fff;}'
        '.ck-model-pill-label{font-size:11px;font-weight:600;'
        'letter-spacing:0.04em;}'
        '</style>'
        '<nav class="ck-model-rail" aria-label="Deal model navigation">'
        f'<a href="/deal/{did}" class="ck-model-rail-back">&larr; Deal</a>'
        + "".join(items) +
        '</nav>'
    )


def _fmt_m(val: Any) -> str:
    """Format as $XM."""
    if val is None:
        return "—"
    try:
        v = float(val)
        if abs(v) >= 1e9:
            return f"${v / 1e9:,.1f}B"
        return f"${v / 1e6:,.1f}M"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(val: Any, *, is_fraction: bool = False) -> str:
    """Format a number as a percentage.

    Args:
        val: numeric value (or None / non-numeric → "—").
        is_fraction: when True, ``val`` is always treated as a fraction
            and formatted with ``"{:.1%}"`` regardless of magnitude.
            Use this for fields where the source unit is unambiguous —
            e.g. ``LBOReturns.irr`` is always a fraction, so an IRR of
            1.3022 renders as 130.2% instead of being mis-classified
            by the abs-less-than-one auto-detect.
        Default (False) preserves the legacy auto-detect: values with
            ``abs(v) < 1`` are treated as fractions, otherwise as
            already-percentage. Used for free-form display of cells
            whose unit can't be assumed.
    """
    if val is None:
        return "—"
    try:
        v = float(val)
        if is_fraction:
            return f"{v:.1%}"
        if abs(v) < 1:
            return f"{v:.1%}"
        return f"{v:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_x(val: Any) -> str:
    if val is None:
        return "—"
    try:
        return f"{float(val):.2f}x"
    except (TypeError, ValueError):
        return "—"


# ── Editorial inline-SVG trajectory chart ──────────────────────────
# DCF projection chart — revenue + EBITDA + FCF lines over the
# explicit-period years. Same vocabulary as ic_memo / ebitda_bridge:
# parchment palette, navy / teal / amber lines, no JS, no chart libs.

def _projection_trajectory_chart(projections: List[Dict[str, Any]],
                                 width: int = 720,
                                 height: int = 220) -> str:
    """Multi-line trajectory chart for DCF projection rows.

    Lines: Revenue (navy), EBITDA (teal), FCF (amber).
    Year markers on x-axis, dollar gridlines on y-axis.
    """
    if not projections:
        return ""
    series_defs = [
        ("Revenue",  "revenue",         "#0b2341"),
        ("EBITDA",   "ebitda",          "#155752"),
        ("FCF",      "free_cash_flow",  "#b8732a"),
    ]
    # Pull (year, value) per series
    series: List[Dict[str, Any]] = []
    all_vals: List[float] = []
    for label, key, color in series_defs:
        pts: List[tuple] = []
        for p in projections:
            yr = p.get("year")
            v = p.get(key)
            if yr is None or v is None:
                continue
            try:
                pts.append((float(yr), float(v)))
            except (TypeError, ValueError):
                continue
        if pts:
            series.append({"label": label, "points": pts, "color": color})
            all_vals.extend(v for _, v in pts)
    if not series or not all_vals:
        return ""

    pad_l, pad_r, pad_t, pad_b = 56, 110, 28, 36
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    years = sorted({y for s in series for y, _ in s["points"]})
    y_lo, y_hi = years[0], years[-1]
    y_span = max(1, y_hi - y_lo)
    v_lo = min(0.0, min(all_vals))
    v_hi = max(all_vals)
    v_span = v_hi - v_lo if v_hi != v_lo else max(abs(v_hi), 1)

    def _x(y: float) -> float:
        return pad_l + (y - y_lo) / y_span * plot_w

    def _y(v: float) -> float:
        return pad_t + plot_h - (v - v_lo) / v_span * plot_h

    # Y-axis gridlines + value labels (5 ticks)
    grid_svg = ""
    for i in range(5):
        gv = v_lo + v_span * i / 4
        gy = _y(gv)
        grid_svg += (
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l + plot_w}" '
            f'y2="{gy:.1f}" stroke="#E8E0D0" stroke-width="0.8"/>'
            f'<text x="{pad_l - 6}" y="{gy + 3:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#8A92A0" text-anchor="end">{_fmt_m(gv)}</text>'
        )

    # X-axis year ticks
    tick_svg = ""
    for y in years:
        tx = _x(y)
        tick_svg += (
            f'<line x1="{tx:.1f}" y1="{pad_t + plot_h}" x2="{tx:.1f}" '
            f'y2="{pad_t + plot_h + 4}" stroke="#BFB6A2" stroke-width="0.8"/>'
            f'<text x="{tx:.1f}" y="{pad_t + plot_h + 16}" '
            f'font-family="JetBrains Mono,monospace" font-size="9.5" '
            f'fill="#5C6878" text-anchor="middle">Y{int(y)}</text>'
        )

    # Series lines + dots
    lines_svg = ""
    legend_svg = ""
    legend_x = pad_l + plot_w + 16
    for i, s in enumerate(series):
        pts = sorted(s["points"], key=lambda p: p[0])
        path = " ".join(
            f"{'M' if j == 0 else 'L'} {_x(y):.1f},{_y(v):.1f}"
            for j, (y, v) in enumerate(pts)
        )
        lines_svg += (
            f'<path d="{path}" stroke="{s["color"]}" stroke-width="2" '
            f'fill="none"/>'
        )
        for y, v in pts:
            lines_svg += (
                f'<circle cx="{_x(y):.1f}" cy="{_y(v):.1f}" r="3" '
                f'fill="{s["color"]}" stroke="#FAF7F0" stroke-width="1.2"/>'
            )
        ly = pad_t + 8 + i * 18
        legend_svg += (
            f'<line x1="{legend_x}" y1="{ly}" x2="{legend_x + 18}" '
            f'y2="{ly}" stroke="{s["color"]}" stroke-width="2.4"/>'
            f'<circle cx="{legend_x + 9}" cy="{ly}" r="3" fill="{s["color"]}"/>'
            f'<text x="{legend_x + 24}" y="{ly + 3}" '
            f'font-family="Inter Tight,sans-serif" font-size="10.5" '
            f'font-weight="600" fill="#1a2332">{s["label"]}</text>'
        )

    # Axes
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


_MODELS_CHART_CAPTION_CSS = """
<style>
.mdl-chart-caption {
  font-family: "Inter Tight","Inter",sans-serif;
  font-size: .72rem; color: #5C6878;
  text-align: center; letter-spacing: 0.06em;
  text-transform: uppercase; margin: -.5rem 0 1.25rem;
}
@media print {
  .mdl-chart-caption { color: #1a2332; }
  svg { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
"""


def _lbo_deleveraging_chart(annual: List[Dict[str, Any]],
                            width: int = 720,
                            height: int = 240) -> str:
    """LBO deleveraging trajectory — leverage line + EBITDA bars per year.

    Two superimposed series on a shared x-axis (years):
    - Bars (background): EBITDA per year, light teal
    - Line (foreground): leverage ratio per year, tone-coded
      (teal-deep <3x · teal <4.5x · amber <6x · red ≥7.5x)
    - Dashed 6.5x covenant line for reference
    """
    if not annual:
        return ""
    rows: List[Dict[str, float]] = []
    for yr in annual[:7]:
        try:
            y = int(yr.get("year"))
        except (TypeError, ValueError):
            continue
        try:
            ebitda = float(yr.get("ebitda") or 0)
        except (TypeError, ValueError):
            ebitda = 0
        lev = yr.get("leverage") or yr.get("net_debt_ebitda")
        try:
            lev_v = float(lev) if lev is not None else None
        except (TypeError, ValueError):
            lev_v = None
        rows.append({"year": y, "ebitda": ebitda, "leverage": lev_v})
    rows.sort(key=lambda r: r["year"])
    if not rows:
        return ""

    pad_l, pad_r, pad_t, pad_b = 56, 56, 26, 38
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(rows)
    slot = plot_w / max(n, 1)
    bar_w = slot * 0.55

    ebitda_max = max((r["ebitda"] for r in rows), default=0)
    lev_max = max((r["leverage"] or 0 for r in rows), default=0)
    lev_max = max(lev_max, 7.0)  # always show the 6.5x covenant line

    def _x(i: int) -> float:
        return pad_l + slot * i + slot / 2

    def _y_eb(v: float) -> float:
        return pad_t + plot_h - (v / ebitda_max if ebitda_max else 0) * plot_h

    def _y_lev(v: float) -> float:
        return pad_t + plot_h - (v / lev_max if lev_max else 0) * plot_h

    # Left y-axis (EBITDA $) labels
    grid_svg = ""
    for i in range(5):
        gv = ebitda_max * i / 4
        gy = pad_t + plot_h - (i / 4) * plot_h
        grid_svg += (
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{pad_l + plot_w}" '
            f'y2="{gy:.1f}" stroke="#E8E0D0" stroke-width="0.8"/>'
            f'<text x="{pad_l - 6}" y="{gy + 3:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#8A92A0" text-anchor="end">{_fmt_m(gv)}</text>'
        )

    # Right y-axis (leverage x) labels
    right_axis_svg = ""
    for i in range(5):
        lv = lev_max * i / 4
        gy = pad_t + plot_h - (i / 4) * plot_h
        right_axis_svg += (
            f'<text x="{pad_l + plot_w + 6}" y="{gy + 3:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#8A92A0" text-anchor="start">{lv:.1f}x</text>'
        )

    # 6.5x covenant reference
    cov_y = _y_lev(6.5)
    covenant_svg = (
        f'<line x1="{pad_l}" y1="{cov_y:.1f}" x2="{pad_l + plot_w}" '
        f'y2="{cov_y:.1f}" stroke="#A53A2D" stroke-width="1" '
        f'stroke-dasharray="4,3" opacity="0.7"/>'
        f'<text x="{pad_l + plot_w - 4}" y="{cov_y - 4:.1f}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" '
        f'font-weight="700" letter-spacing="0.06em" '
        f'fill="#A53A2D" text-anchor="end">6.5x COVENANT</text>'
    )

    # EBITDA bars + year labels
    bars_svg = ""
    for i, r in enumerate(rows):
        cx = _x(i)
        bx = cx - bar_w / 2
        by = _y_eb(r["ebitda"])
        bh = (pad_t + plot_h) - by
        bars_svg += (
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" '
            f'height="{bh:.1f}" fill="#D4E4E2" stroke="#BFD1CE" '
            f'stroke-width="0.6" rx="1"/>'
            f'<text x="{cx:.1f}" y="{pad_t + plot_h + 14:.1f}" '
            f'font-family="Inter Tight,sans-serif" font-size="10" '
            f'font-weight="700" fill="#1a2332" text-anchor="middle">'
            f'Y{r["year"]}</text>'
        )

    # Leverage line + tone-coded dots
    lev_pts = [(i, r["leverage"]) for i, r in enumerate(rows) if r["leverage"] is not None]
    line_svg = ""
    dots_svg = ""
    if lev_pts:
        path = " ".join(
            f"{'M' if j == 0 else 'L'} {_x(i):.1f},{_y_lev(v):.1f}"
            for j, (i, v) in enumerate(lev_pts)
        )
        line_svg = (
            f'<path d="{path}" stroke="#0F1C2E" stroke-width="2.4" '
            f'fill="none"/>'
        )
        for i, v in lev_pts:
            tone = (
                "#155752" if v < 3
                else "#1F7A75" if v < 4.5
                else "#b8732a" if v < 6
                else "#A53A2D"
            )
            dots_svg += (
                f'<circle cx="{_x(i):.1f}" cy="{_y_lev(v):.1f}" r="4.5" '
                f'fill="{tone}" stroke="#FAF7F0" stroke-width="1.5"/>'
                f'<text x="{_x(i):.1f}" y="{_y_lev(v) - 9:.1f}" '
                f'font-family="JetBrains Mono,monospace" font-size="9.5" '
                f'font-weight="700" fill="{tone}" text-anchor="middle">'
                f'{v:.1f}x</text>'
            )

    # Axes
    base_y = pad_t + plot_h
    axes_svg = (
        f'<line x1="{pad_l}" y1="{base_y:.1f}" x2="{pad_l + plot_w}" '
        f'y2="{base_y:.1f}" stroke="#BFB6A2" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" '
        f'y2="{base_y:.1f}" stroke="#BFB6A2" stroke-width="1"/>'
        f'<line x1="{pad_l + plot_w}" y1="{pad_t}" '
        f'x2="{pad_l + plot_w}" y2="{base_y:.1f}" '
        f'stroke="#BFB6A2" stroke-width="1"/>'
    )

    # Axis-label eyebrows
    eyebrow_svg = (
        f'<text x="{pad_l - 6}" y="{pad_t - 8}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" '
        f'font-weight="700" letter-spacing="0.08em" '
        f'fill="#5C6878" text-anchor="end">EBITDA ($)</text>'
        f'<text x="{pad_l + plot_w + 6}" y="{pad_t - 8}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" '
        f'font-weight="700" letter-spacing="0.08em" '
        f'fill="#5C6878" text-anchor="start">LEVERAGE</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{grid_svg}{axes_svg}{eyebrow_svg}{bars_svg}{covenant_svg}'
        f'{line_svg}{dots_svg}{right_axis_svg}</svg>'
    )


def render_dcf_page(deal_id: str, deal_name: str, dcf: Dict[str, Any]) -> str:
    """Render DCF model as a full browser page."""
    assumptions = dcf.get("assumptions", {})
    projections = dcf.get("projections", [])
    ev = dcf.get("enterprise_value", 0)
    pv_cf = dcf.get("pv_cash_flows", 0)
    pv_term = dcf.get("pv_terminal", 0)
    tv = dcf.get("terminal_value", 0)

    # KPIs
    # Cycle 39 — port DCF KPI strip to ck_kpi_block + provenance.
    ev_value = ck_provenance_tooltip(
        "DCF enterprise value",
        _fmt_m(ev),
        explainer=(
            "PV of explicit-period free cash flows + PV of terminal "
            "value, discounted at WACC. Sensitive to terminal "
            "growth and WACC assumptions in the sensitivity grid "
            "below."
        ),
    )
    wacc_value = ck_provenance_tooltip(
        "Weighted average cost of capital",
        _fmt_pct(assumptions.get("wacc")),
        explainer=(
            "Cost-of-equity (CAPM with healthcare beta) blended "
            "with after-tax cost of debt at the deal's target "
            "leverage. Lower WACC = higher EV - the sensitivity "
            "grid shows the effect of +/-1% shifts."
        ),
        inject_css=False,
    )
    kpis = (
        f'<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Enterprise Value", ev_value, "PV of FCF + terminal",
            help={
                "definition": (
                    "DCF-derived enterprise value = present value of "
                    "explicit-period free cash flows + present value "
                    "of the terminal-value chunk. The sum every PE "
                    "underwriting compares to the entry multiple × "
                    "trailing EBITDA."
                ),
            },
        )
        + ck_kpi_block("PV of Cash Flows", _fmt_m(pv_cf), "explicit period")
        + ck_kpi_block(
            "PV of Terminal", _fmt_m(pv_term), "Gordon growth",
            help={
                "definition": (
                    "Present value of the terminal lump — what the "
                    "business is worth after year 5/10. Healthy DCFs "
                    "have <70% of EV in the terminal; >80% means "
                    "you're underwriting the exit multiple, not the "
                    "explicit-period cash flows."
                ),
            },
        )
        + ck_kpi_block(
            "Terminal Value", _fmt_m(tv), "exit-year FCF / (WACC - g)",
            help={
                "definition": (
                    "Undiscounted terminal — exit-year free cash flow "
                    "÷ (WACC − terminal growth). Sensitive: a 50bp "
                    "shift in either input swings terminal by 10-15%. "
                    "Worth checking against trading-comp multiples "
                    "for sanity."
                ),
            },
        )
        + ck_kpi_block(
            "WACC", wacc_value, "discount rate",
            help={
                "definition": (
                    "Weighted average cost of capital — blended cost "
                    "of equity and debt. PE healthcare typically uses "
                    "9-11% for community hospitals, 11-13% for "
                    "specialty platforms. Below 8% in current rate "
                    "environment is hard to defend."
                ),
            },
        )
        + ck_kpi_block(
            "Terminal Growth",
            _fmt_pct(assumptions.get("terminal_growth")),
            "perpetual FCF growth",
            help={
                "definition": (
                    "Assumed perpetual FCF growth past the explicit "
                    "period. Cap at long-run nominal GDP (2.5-3%); "
                    "above 4% implies the business grows faster than "
                    "the economy forever, which is implausible for "
                    "any mature business."
                ),
            },
        )
        + f'</div>'
    )

    # Projections table
    proj_rows = ""
    for p in projections:
        yr = p.get("year", "")
        proj_rows += (
            f'<tr>'
            f'<td class="num" style="font-weight:600;">Year {yr}</td>'
            f'<td class="num">{_fmt_m(p.get("revenue"))}</td>'
            f'<td class="num">{_fmt_m(p.get("ebitda"))}</td>'
            f'<td class="num">{_fmt_pct(p.get("ebitda_margin"))}</td>'
            f'<td class="num">{_fmt_m(p.get("free_cash_flow"))}</td>'
            f'<td class="num">{_fmt_m(p.get("pv_fcf"))}</td>'
            f'</tr>'
        )
    proj_chart = _projection_trajectory_chart(projections)
    proj_caption = (
        '<div class="mdl-chart-caption">'
        'Revenue · EBITDA · FCF across the explicit projection period'
        '</div>'
    ) if proj_chart else ""
    proj_table = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Cash Flow Projections</h2>'
        f'<span class="cad-section-code">PROJ</span></div>'
        + proj_chart + proj_caption +
        f'<table class="cad-table crosshair"><thead><tr>'
        f'<th>Year</th><th>Revenue</th><th>EBITDA</th>'
        f'<th>Margin</th><th>FCF</th><th>PV(FCF)</th>'
        f'</tr></thead><tbody>{proj_rows}</tbody></table></div>'
    ) if proj_rows else ""

    # Sensitivity matrix with heatmap cells
    sensitivity = dcf.get("sensitivity", {})
    sens_html = ""
    if sensitivity:
        matrix = sensitivity.get("wacc_x_growth", sensitivity.get("matrix", []))
        if isinstance(matrix, list) and matrix:
            # First compute min/max across all cells for heatmap scaling
            all_vals = []
            for row in matrix[:8]:
                for cell in (row.get("values", []) if isinstance(row, dict) else []):
                    v = cell.get("ev", cell.get("value", 0)) if isinstance(cell, dict) else cell
                    try:
                        all_vals.append(float(v))
                    except (TypeError, ValueError):
                        pass
            vmin = min(all_vals) if all_vals else 0
            vmax = max(all_vals) if all_vals else 1
            vrange = (vmax - vmin) or 1

            rows_h = ""
            for row in matrix[:8]:
                cells = ""
                for cell in (row.get("values", []) if isinstance(row, dict) else []):
                    v = cell.get("ev", cell.get("value", 0)) if isinstance(cell, dict) else cell
                    try:
                        pos = (float(v) - vmin) / vrange
                    except (TypeError, ValueError):
                        pos = 0.5
                    # reverse: high EV = green (heat-1), low EV = red (heat-5)
                    if pos > 0.8: heat = "cad-heat-1"
                    elif pos > 0.6: heat = "cad-heat-2"
                    elif pos > 0.4: heat = "cad-heat-3"
                    elif pos > 0.2: heat = "cad-heat-4"
                    else: heat = "cad-heat-5"
                    cells += f'<td class="num {heat}" style="font-weight:600;">{_fmt_m(v)}</td>'
                label = row.get("wacc", row.get("label", "")) if isinstance(row, dict) else ""
                rows_h += (
                    f'<tr><td class="num" style="font-weight:700;background:'
                    f'{PALETTE["bg_tertiary"]};">{_fmt_pct(label)}</td>{cells}</tr>'
                )

            sens_html = (
                f'<div class="cad-card">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
                f'<h2 style="margin:0;">Sensitivity: WACC × Terminal Growth</h2>'
                f'<span class="cad-section-code">SENS</span></div>'
                f'<p style="font-family:var(--cad-mono);font-size:10.5px;'
                f'letter-spacing:0.06em;color:{PALETTE["text_muted"]};'
                f'text-transform:uppercase;margin-bottom:8px;">'
                f'Enterprise value · green = high EV · red = low EV</p>'
                f'<table class="cad-table"><thead><tr><th>WACC ↓ / Growth →</th>'
                f'</tr></thead><tbody>{rows_h}</tbody></table></div>'
            )

    # Assumptions panel
    assume_items = ""
    for k, v in assumptions.items():
        if k in ("wacc", "terminal_growth"):
            continue
        assume_items += (
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
            f'border-bottom:1px solid {PALETTE["border"]};font-family:var(--cad-mono);'
            f'font-size:11px;letter-spacing:0.04em;">'
            f'<span style="color:{PALETTE["text_muted"]};text-transform:uppercase;">'
            f'{html.escape(k.replace("_", " "))}</span>'
            f'<span style="color:{PALETTE["text_primary"]};font-weight:600;">'
            f'{_fmt_m(v) if isinstance(v, (int, float)) and abs(float(v)) > 1000 else html.escape(str(v))}</span>'
            f'</div>'
        )
    assume_section = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Assumptions</h2>'
        f'<span class="cad-section-code">ASSM</span></div>'
        f'<div>{assume_items}</div></div>'
    ) if assume_items else ""

    # Actions
    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{html.escape(deal_id)}/dcf" class="cad-btn" '
        f'style="text-decoration:none;">Raw JSON</a>'
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">LBO Model</a>'
        f'<a href="/models/financials/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">3-Statement</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    # Interpretation — what this means
    wacc = float(assumptions.get("wacc", 0.10))
    growth = float(assumptions.get("terminal_growth", 0.025))
    tv_pct = pv_term / ev * 100 if ev > 0 else 0
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Interpretation</h2>'
        f'<span class="cad-section-code">INT</span></div>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>At a WACC of <strong>{wacc:.1%}</strong> and terminal growth of '
        f'<strong>{growth:.1%}</strong>, enterprise value is <strong>{_fmt_m(ev)}</strong>. '
        f'Terminal value accounts for <strong>{tv_pct:.0f}%</strong> of total EV — '
        f'{"typical range (60-80%)" if 55 < tv_pct < 85 else "consider sensitivity to terminal assumptions"}.</p>'
        f'<p style="margin-top:8px;"><strong>Next steps:</strong> '
        f'Check the <a href="/models/lbo/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">LBO model</a> '
        f'to see equity returns at this entry price, or the '
        f'<a href="/models/bridge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">EBITDA bridge</a> '
        f'to model value creation levers.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "dcf")
    next_up = ck_next_section(
        "Open the LBO model",
        f"/models/lbo/{html.escape(deal_id)}",
        eyebrow="Continue —",
        italic_word="LBO",
    )
    body = f'{_MODELS_CHART_CAPTION_CSS}{nav}{kpis}{proj_table}{interp}{sens_html}{assume_section}{actions}{next_up}'
    return chartis_shell(body, f"DCF — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"Enterprise Value: {_fmt_m(ev)}",
                    editorial_intro={
                        "eyebrow": "DCF MODEL",
                        "headline": "What the cash flows are worth.",
                        "italic_word": "worth",
                        "body": (
                            "Discounted free-cash-flow valuation with a "
                            "WACC + terminal-multiple sensitivity grid. "
                            "Pair this with the LBO and 3-statement "
                            "models for a full investment-committee view."
                        ),
                    })


def render_lbo_page(deal_id: str, deal_name: str, lbo: Dict[str, Any]) -> str:
    """Render LBO model as a full browser page."""
    returns = lbo.get("returns", {})
    sources = lbo.get("sources_and_uses", {})
    schedule = lbo.get("debt_schedule", [])
    annual = lbo.get("annual_projections", [])

    irr = returns.get("irr", 0)
    hold_years = lbo.get("hold_years", returns.get("hold_years", 5))
    moic = returns.get("moic", 0)
    entry_ev = sources.get("total_sources", 0) or lbo.get("entry_ev", 0)
    exit_ev = returns.get("exit_ev", 0)
    equity_invested = sources.get("equity", 0) or returns.get("equity_invested", 0)

    irr_color = PALETTE["positive"] if irr and irr > 0.20 else (
        PALETTE["warning"] if irr and irr > 0.15 else PALETTE["negative"])

    # Cycle 39 — port LBO KPI strip + add IRR provenance.
    irr_value = ck_provenance_tooltip(
        "Levered IRR to equity",
        SafeHtml(f'<span style="color:{irr_color};">{_fmt_pct(irr)}</span>'),
        explainer=(
            "Internal rate of return to the LP equity check over "
            "a {hold}yr hold. >20% green, 15-20% amber, below "
            "15% negative. Sensitive to exit multiple, leverage, "
            "and EBITDA growth — all tunable below."
        ).replace('{hold}', str(hold_years)),
    )
    moic_value = ck_provenance_tooltip(
        "Multiple of invested capital",
        _fmt_x(moic),
        explainer=(
            "Total equity proceeds at exit divided by equity "
            "invested at entry. 2.5x is the rough industry "
            "median over a 5-year hold; 3x+ is a strong outcome."
        ),
        inject_css=False,
    )
    kpis = (
        f'<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "IRR", irr_value, "to equity over hold",
            help={
                "definition": (
                    "LBO-modeled internal rate of return on the equity "
                    "check. PE healthcare target is 20%+ at the gross "
                    "level; below 15% won't clear the hurdle. Sensitive "
                    "to hold period — short holds need higher MOIC to "
                    "hit the same IRR."
                ),
            },
        )
        + ck_kpi_block(
            "MOIC", moic_value, "exit / entry equity",
            help={
                "definition": (
                    "Multiple on invested capital — exit proceeds ÷ "
                    "entry equity check. Less sensitive to hold period "
                    "than IRR; a 2.5x in 5yrs and 2.5x in 7yrs return "
                    "the same dollars to the LP but very different "
                    "IRRs."
                ),
            },
        )
        + ck_kpi_block(
            "Entry EV", _fmt_m(entry_ev), "sources of capital",
            help={
                "definition": (
                    "Total enterprise value at acquisition — debt + "
                    "equity sources. The check the deal pays for the "
                    "business; structured at the entry-multiple × "
                    "trailing EBITDA."
                ),
            },
        )
        + ck_kpi_block(
            "Exit EV", _fmt_m(exit_ev), "year-{hold} terminal".replace('{hold}', str(hold_years)),
            help={
                "definition": (
                    "Modeled enterprise value at exit, year " + str(hold_years) +
                    ". Built from exit-year EBITDA × exit multiple. "
                    "Healthier LBOs grow EBITDA enough that even with "
                    "no multiple expansion, the equity multiplies."
                ),
            },
        )
        + ck_kpi_block(
            "Equity Invested", _fmt_m(equity_invested), "LP check",
            help={
                "definition": (
                    "Total LP equity at close — the denominator for "
                    "both IRR and MOIC. Typical PE healthcare deal "
                    "puts in 30-40% equity, with the rest from senior + "
                    "second-lien debt."
                ),
            },
        )
        + f'</div>'
    )

    # Sources & Uses
    su_html = ""
    if sources:
        total_s = sources.get("total_sources", 0) or sum(
            float(v) for k, v in sources.items()
            if k != "total_sources" and isinstance(v, (int, float))
        )
        su_rows = ""
        for k, v in sources.items():
            if k == "total_sources":
                continue
            try:
                pct = float(v) / total_s * 100 if total_s else 0
            except (TypeError, ValueError):
                pct = 0
            su_rows += (
                f'<tr><td style="font-weight:600;">{html.escape(k.replace("_", " ").title())}</td>'
                f'<td class="num">{_fmt_m(v)}</td>'
                f'<td class="num">{pct:.1f}%</td>'
                f'<td><div class="cad-bar" style="width:100%;">'
                f'<div class="cad-bar-fill" style="width:{pct:.0f}%;background:{PALETTE["brand_accent"]};"></div>'
                f'</div></td></tr>'
            )
        su_html = (
            f'<div class="cad-card">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Sources &amp; Uses</h2>'
            f'<span class="cad-section-code">S&amp;U</span>'
            f'<span style="font-family:var(--cad-mono);font-size:10px;'
            f'letter-spacing:0.08em;color:{PALETTE["text_muted"]};'
            f'text-transform:uppercase;margin-left:auto;">'
            f'Total · {_fmt_m(total_s)}</span></div>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Item</th><th>Amount</th><th>%</th><th>Distribution</th>'
            f'</tr></thead><tbody>{su_rows}</tbody></table></div>'
        )

    # Annual projections with leverage heatmap
    annual_html = ""
    if annual:
        ann_rows = ""
        for yr in annual[:7]:
            lev = yr.get("leverage") or yr.get("net_debt_ebitda")
            try:
                lev_v = float(lev) if lev is not None else None
            except (TypeError, ValueError):
                lev_v = None
            if lev_v is None:
                heat = ""
            elif lev_v < 3: heat = "cad-heat-1"
            elif lev_v < 4.5: heat = "cad-heat-2"
            elif lev_v < 6: heat = "cad-heat-3"
            elif lev_v < 7.5: heat = "cad-heat-4"
            else: heat = "cad-heat-5"
            ann_rows += (
                f'<tr>'
                f'<td class="num" style="font-weight:700;color:{PALETTE["accent_amber"]};">Y{yr.get("year", "")}</td>'
                f'<td class="num">{_fmt_m(yr.get("revenue"))}</td>'
                f'<td class="num">{_fmt_m(yr.get("ebitda"))}</td>'
                f'<td class="num">{_fmt_m(yr.get("debt_balance") or yr.get("total_debt"))}</td>'
                f'<td class="num">{_fmt_m(yr.get("interest_expense") or yr.get("interest"))}</td>'
                f'<td class="num {heat}" style="font-weight:600;">{_fmt_x(lev)}</td>'
                f'</tr>'
            )
        delev_chart = _lbo_deleveraging_chart(annual)
        delev_caption = (
            '<div class="mdl-chart-caption">'
            'EBITDA growth (bars) + leverage trajectory (line) · '
            'dashed 6.5x covenant line'
            '</div>'
        ) if delev_chart else ""
        annual_html = (
            f'<div class="cad-card">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Annual Projections</h2>'
            f'<span class="cad-section-code">ANN</span>'
            f'<span style="font-family:var(--cad-mono);font-size:10px;'
            f'letter-spacing:0.08em;color:{PALETTE["text_muted"]};'
            f'text-transform:uppercase;margin-left:auto;">'
            f'Leverage · green &lt;3x · red &gt;7.5x</span></div>'
            + delev_chart + delev_caption +
            f'<table class="cad-table crosshair"><thead><tr>'
            f'<th>Year</th><th>Revenue</th><th>EBITDA</th>'
            f'<th>Debt</th><th>Interest</th><th>Leverage</th>'
            f'</tr></thead><tbody>{ann_rows}</tbody></table></div>'
        )

    # Returns waterfall
    waterfall_html = ""
    if returns:
        wf_rows = ""
        for k, v in returns.items():
            if k in ("irr", "moic"):
                continue
            wf_rows += (
                f'<tr><td style="font-weight:600;">{html.escape(k.replace("_", " ").title())}</td>'
                f'<td class="num">{_fmt_m(v) if isinstance(v, (int, float)) and abs(float(v)) > 1000 else _fmt_pct(v) if isinstance(v, float) and abs(v) < 10 else html.escape(str(v))}</td></tr>'
            )
        waterfall_html = (
            f'<div class="cad-card">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<h2 style="margin:0;">Returns Waterfall</h2>'
            f'<span class="cad-section-code">WFL</span></div>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Component</th><th>Value</th>'
            f'</tr></thead><tbody>{wf_rows}</tbody></table></div>'
        )

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{html.escape(deal_id)}/lbo" class="cad-btn" '
        f'style="text-decoration:none;">Raw JSON</a>'
        f'<a href="/models/dcf/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">DCF Model</a>'
        f'<a href="/models/financials/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">3-Statement</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    # Interpretation
    irr_assessment = (
        "exceeds the typical 20% hurdle — strong candidate" if irr and irr > 0.20
        else "meets the 15-20% range — acceptable with operational upside" if irr and irr > 0.15
        else "below 15% hurdle — requires significant value creation thesis" if irr
        else "could not be computed"
    )
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {irr_color};">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Interpretation</h2>'
        f'<span class="cad-section-code" style="color:{irr_color};border-color:{irr_color};">INT</span></div>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>At <strong>{_fmt_x(moic)}</strong> MOIC and <strong>{_fmt_pct(irr)}</strong> IRR '
        f'over <strong>{hold_years:.0f} years</strong>, this deal {irr_assessment}.</p>'
        f'<p style="margin-top:8px;"><strong>Key drivers:</strong> '
        f'Check the <a href="/models/bridge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">EBITDA bridge</a> '
        f'to identify highest-probability levers, the '
        f'<a href="/models/debt/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">debt schedule</a> '
        f'for leverage trajectory, or the '
        f'<a href="/models/challenge/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">challenge solver</a> '
        f'to see what breaks the deal.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "lbo")
    next_up = ck_next_section(
        "Open the returns waterfall",
        f"/models/waterfall/{html.escape(deal_id)}",
        eyebrow="Continue —",
        italic_word="waterfall",
    )
    body = f'{_MODELS_CHART_CAPTION_CSS}{nav}{kpis}{su_html}{annual_html}{interp}{waterfall_html}{actions}{next_up}'
    return chartis_shell(body, f"LBO — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle=f"IRR: {_fmt_pct(irr)} | MOIC: {_fmt_x(moic)}",
                    editorial_intro={
                        "eyebrow": "LBO MODEL",
                        "headline": "What the leverage returns to equity.",
                        "italic_word": "returns",
                        "body": (
                            "Sources and uses, debt amortization, and "
                            "the equity waterfall through a 5-year hold. "
                            "Tune leverage and exit multiple to see "
                            "where the deal stops working."
                        ),
                    })


def render_financials_page(deal_id: str, deal_name: str, model: Dict[str, Any]) -> str:
    """Render 3-statement model as a full browser page."""

    def _statement_table(title: str, items: Any) -> str:
        if not items:
            return ""
        if isinstance(items, dict):
            items = items.get("line_items", items.get("items", []))
        if not isinstance(items, list):
            return ""
        rows = ""
        for item in items:
            label = html.escape(str(item.get("label", item.get("line_item", ""))))
            value = item.get("value", item.get("amount", 0))
            source = item.get("source", "")
            indent = item.get("indent", 0)
            bold = item.get("is_total", False) or item.get("bold", False)
            style = f'padding-left:{12 + indent * 16}px;'
            if bold:
                style += 'font-weight:700;'
            src_badge = ""
            if source:
                src_cls = {
                    "HCRIS": "cad-badge-green",
                    "deal_profile": "cad-badge-blue",
                    "benchmark": "cad-badge-amber",
                    "computed": "cad-badge-muted",
                }.get(source, "cad-badge-muted")
                src_badge = f' <span class="cad-badge {src_cls}" style="font-size:9px;">{html.escape(source)}</span>'
            rows += (
                f'<tr>'
                f'<td style="{style}">{label}{src_badge}</td>'
                f'<td class="num">{_fmt_m(value)}</td>'
                f'</tr>'
            )
        return (
            f'<div class="cad-card">'
            f'<h2>{html.escape(title)}</h2>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Line Item</th><th>Amount</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )

    is_section = _statement_table(
        "Income Statement",
        model.get("income_statement", model.get("is", [])),
    )
    bs_section = _statement_table(
        "Balance Sheet",
        model.get("balance_sheet", model.get("bs", [])),
    )
    cf_section = _statement_table(
        "Cash Flow Statement",
        model.get("cash_flow", model.get("cf", [])),
    )

    # Summary KPIs — cycle 39 ports to ck_kpi_block.
    summary = model.get("summary", {})
    kpis = ""
    if summary:
        kpi_blocks = []
        for k, v in list(summary.items())[:6]:
            value_str = (
                _fmt_m(v) if isinstance(v, (int, float)) and abs(float(v)) > 1000
                else _fmt_pct(v) if isinstance(v, float) and abs(v) < 1
                else html.escape(str(v))
            )
            kpi_blocks.append(ck_kpi_block(
                k.replace("_", " ").title(),
                value_str,
            ))
        kpis = f'<div class="ck-kpi-grid">{"".join(kpi_blocks)}</div>'
        kpis += '</div>'

    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/api/deals/{html.escape(deal_id)}/financials" class="cad-btn" '
        f'style="text-decoration:none;">Raw JSON</a>'
        f'<a href="/models/dcf/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">DCF Model</a>'
        f'<a href="/models/lbo/{html.escape(deal_id)}" class="cad-btn" '
        f'style="text-decoration:none;">LBO Model</a>'
        f'<a href="/analysis/{html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Full Analysis</a></div>'
    )

    # Interpretation
    interp = (
        f'<div class="cad-card" style="border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<h2>What This Means</h2>'
        f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'<p>This 3-statement model reconstructs the hospital\'s income statement, balance sheet, '
        f'and cash flow from HCRIS cost report data. Each line item is tagged with its data source: '
        f'<span class="cad-badge cad-badge-green" style="font-size:9px;">HCRIS</span> (actual reported), '
        f'<span class="cad-badge cad-badge-blue" style="font-size:9px;">deal_profile</span> (user input), '
        f'<span class="cad-badge cad-badge-amber" style="font-size:9px;">benchmark</span> (industry estimate), '
        f'<span class="cad-badge cad-badge-muted" style="font-size:9px;">computed</span> (derived).</p>'
        f'<p style="margin-top:6px;">Use this to identify data quality: lines tagged "benchmark" are '
        f'estimates that should be validated during diligence. Request actual data for these items '
        f'via <a href="/models/questions/{html.escape(deal_id)}" style="color:{PALETTE["text_link"]};">'
        f'diligence questions</a>.</p>'
        f'</div></div>'
    )

    nav = _model_nav(deal_id, "financials")
    next_up = ck_next_section(
        "Open the DCF model",
        f"/models/dcf/{html.escape(deal_id)}",
        eyebrow="Continue —",
        italic_word="DCF",
    )
    body = f'{nav}{kpis}{is_section}{bs_section}{interp}{cf_section}{actions}{next_up}'
    return chartis_shell(body, f"Financials — {html.escape(deal_name)}",
                    active_nav="/analysis",
                    subtitle="3-statement model reconstructed from HCRIS + deal profile",
                    editorial_intro={
                        "eyebrow": "FINANCIAL MODEL",
                        "headline": "What the three statements tell each other.",
                        "italic_word": "tell",
                        "body": (
                            "Income statement, balance sheet, and cash "
                            "flow reconstructed from HCRIS plus deal "
                            "profile. The places these don't tie tell "
                            "you what the seller is hiding."
                        ),
                    })
