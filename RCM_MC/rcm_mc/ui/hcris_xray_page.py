"""HCRIS-Native Peer X-Ray page.

Route: ``/diligence/hcris-xray``

The MD demo moment: type any hospital name or CCN, get an
instant benchmark against its 20-50 peer hospitals across 15 RCM
/ cost / margin / payer-mix metrics, all sourced from filed
Medicare cost reports. Replaces the $80K/yr CapIQ subscription
for this use case.

Partner-facing visualizations:
    * Target identity card with size cohort + margin band
    * Metric benchmark grid — target vs peer P25 / median / P75
      with variance chip, color-coded by good/bad direction
    * Peer roster table (sortable, exportable)
    * Dataset summary (how many hospitals × states × years covered)
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..diligence.hcris_xray import (
    HospitalMetrics, MetricBenchmark, PeerMatch, XRayReport,
    catalog_by_category, dataset_summary, get_target_history,
    search_hospitals, xray,
)
from ._chartis_kit import P, chartis_shell
from .power_ui import (
    bookmark_hint, deal_context_bar, export_json_panel,
    interpret_callout, provenance, sortable_table,
)


# ────────────────────────────────────────────────────────────────────
# Scoped CSS (hx- prefix)
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.hx-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.hx-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.hx-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.hx-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.hx-panel{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 20px;margin-bottom:16px;}}
.hx-callout{{background:{pa};padding:12px 16px;border-left:3px solid {ac};
border-radius:0 3px 3px 0;font-size:12px;color:{td};line-height:1.65;
max-width:900px;margin-top:12px;}}
.hx-target-card{{background:linear-gradient(135deg,{pn} 0%,{pa} 100%);
border:1px solid {bd};border-left:3px solid {ac};border-radius:4px;
padding:18px 22px;margin-top:14px;}}
.hx-target-name{{font-size:20px;color:{tx};font-weight:600;
letter-spacing:-.2px;}}
.hx-target-ccn{{font-family:"JetBrains Mono",monospace;font-size:11px;
color:{tf};letter-spacing:0.5px;}}
.hx-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:14px;margin-top:14px;}}
.hx-kpi__label{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
color:{tf};font-weight:600;margin-bottom:3px;}}
.hx-kpi__val{{font-size:22px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;color:{tx};}}
.hx-kpi__val.pos{{color:{po};}}
.hx-kpi__val.neg{{color:{ne};}}
.hx-kpi__val.warn{{color:{wn};}}
.hx-metric-row{{display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr 1fr 80px 120px;
gap:12px;padding:10px 10px;border-bottom:1px solid {bd};
font-size:12.5px;color:{td};align-items:center;}}
.hx-metric-row.head{{color:{tf};font-size:9.5px;letter-spacing:1.2px;
text-transform:uppercase;font-weight:700;border-bottom:2px solid {bd};}}
.hx-metric-name{{color:{tx};font-weight:600;}}
.hx-metric-help{{font-size:10px;color:{tf};margin-top:2px;
font-weight:400;line-height:1.4;}}
.hx-metric-val{{font-family:"JetBrains Mono",monospace;font-weight:700;}}
.hx-metric-peer{{font-family:"JetBrains Mono",monospace;color:{td};}}
.hx-cat-title{{font-size:11px;color:{tf};letter-spacing:1.4px;
text-transform:uppercase;font-weight:700;margin:18px 0 6px 0;
padding-bottom:4px;border-bottom:1px solid {bd};}}
.hx-chip{{display:inline-block;padding:2px 7px;border-radius:2px;
font-size:10px;font-weight:700;letter-spacing:1px;
font-family:"JetBrains Mono",monospace;}}
.hx-chip-above{{background:{po};color:#fff;}}
.hx-chip-below{{background:{ne};color:#fff;}}
.hx-chip-inside{{background:{pa};color:{td};border:1px solid {bd};}}
.hx-form-field label{{display:block;font-size:10px;color:{tf};
letter-spacing:1.2px;text-transform:uppercase;font-weight:600;
margin-bottom:4px;}}
.hx-form-field input,.hx-form-field select{{width:100%;
background:{pa};color:{tx};border:1px solid {bd};padding:8px 10px;
border-radius:3px;font-family:"JetBrains Mono",monospace;font-size:13px;}}
.hx-form-submit{{margin-top:18px;padding:10px 20px;background:{ac};
color:#fff;border:0;border-radius:3px;font-size:12px;letter-spacing:1.3px;
text-transform:uppercase;font-weight:700;cursor:pointer;}}
.hx-form-submit:hover{{filter:brightness(1.15);}}
.hx-form-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:14px;}}
.hx-search-result{{display:grid;grid-template-columns:100px 1fr 70px 90px 90px;
gap:10px;padding:6px 8px;border-bottom:1px solid {bd};
font-size:12px;color:{td};align-items:baseline;
text-decoration:none;transition:background 120ms;}}
.hx-search-result:hover{{background:{pa};}}
.hx-search-result .ccn{{font-family:"JetBrains Mono",monospace;
color:{tf};}}
.hx-search-result .nm{{color:{tx};font-weight:600;}}
.hx-search-result .right{{font-family:"JetBrains Mono",monospace;
text-align:right;}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# Composed blocks
# ────────────────────────────────────────────────────────────────────

def _trend_signal_chip(signal: str, history_len: int) -> str:
    if not signal or history_len < 2:
        return ""
    tone_map = {
        "improving": (P["positive"], "TREND · IMPROVING"),
        "deteriorating": (P["negative"], "TREND · DETERIORATING"),
        "flat": (P["text_faint"], "TREND · FLAT"),
    }
    color, label = tone_map.get(
        signal, (P["text_faint"], f"TREND · {signal.upper()}"),
    )
    return (
        f'<span style="display:inline-block;padding:3px 9px;'
        f'margin-left:8px;border-radius:2px;font-size:9.5px;'
        f'font-weight:700;letter-spacing:1.2px;'
        f'background:{color};color:#fff;">'
        f'{label} · {history_len}Y</span>'
    )


def _target_card(
    target: HospitalMetrics,
    trend_signal: str = "",
    history_len: int = 0,
) -> str:
    margin_color_map = {
        "NEGATIVE": P["negative"],
        "THIN": P["warning"],
        "HEALTHY": P["positive"],
        "STRONG": P["positive"],
    }
    margin_color = margin_color_map.get(target.margin_band, P["text_faint"])
    op_margin_val = provenance(
        f"{target.operating_margin_on_npr*100:.1f}%",
        source="HCRIS filing",
        formula="(NPR − operating expenses) ÷ NPR",
        detail=(
            f"Fiscal year {target.fiscal_year}. "
            f"NPR ${target.net_patient_revenue/1e6:,.1f}M; "
            f"opex ${target.operating_expenses/1e6:,.1f}M."
        ),
    )
    trend_chip = _trend_signal_chip(trend_signal, history_len)
    return (
        f'<div class="hx-target-card">'
        f'<div class="hx-target-ccn">CCN {html.escape(target.ccn)} · '
        f'FY{target.fiscal_year} · '
        f'{html.escape(target.city)}, {html.escape(target.state)}</div>'
        f'<div class="hx-target-name">{html.escape(target.name)}'
        f'{trend_chip}</div>'
        f'<div class="hx-kpi-grid">'
        f'  <div><div class="hx-kpi__label">Beds</div>'
        f'       <div class="hx-kpi__val">{target.beds:,}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">{target.size_cohort.replace("_", " ").title()}</div></div>'
        f'  <div><div class="hx-kpi__label">Patient Days</div>'
        f'       <div class="hx-kpi__val">{target.total_patient_days:,.0f}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">{target.occupancy_rate*100:.1f}% occupancy</div></div>'
        f'  <div><div class="hx-kpi__label">Medicare Day Share</div>'
        f'       <div class="hx-kpi__val '
        f'{"warn" if target.is_medicare_heavy else ""}">'
        f'{target.medicare_day_pct*100:.1f}%</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">{"heavy" if target.is_medicare_heavy else "moderate"}</div></div>'
        f'  <div><div class="hx-kpi__label">NPR (filed)</div>'
        f'       <div class="hx-kpi__val">'
        f'${target.net_patient_revenue/1e6:,.1f}M</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">${target.net_revenue_per_bed/1e3:,.0f}K / bed</div></div>'
        f'  <div><div class="hx-kpi__label">Operating Margin</div>'
        f'       <div class="hx-kpi__val" style="color:{margin_color};">'
        f'{op_margin_val}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">{target.margin_band.title()}</div></div>'
        f'  <div><div class="hx-kpi__label">Payer Diversity</div>'
        f'       <div class="hx-kpi__val">{target.payer_diversity_index:.2f}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">1 − HHI of day mix</div></div>'
        f'</div>'
        f'</div>'
    )


def _sparkline(
    values: List[float], higher_is_better: bool,
    width: int = 100, height: int = 28,
) -> str:
    """Tiny inline SVG sparkline. Colored by trend direction vs
    higher_is_better: green for improving, red for deteriorating,
    grey for flat."""
    if not values or len(values) < 2:
        return (
            f'<span style="font-size:10px;color:#64748b;">'
            f'n/a</span>'
        )
    v_min = min(values)
    v_max = max(values)
    span = v_max - v_min or max(abs(v_max), 1e-6)
    pad = 2
    pts: List[str] = []
    for i, v in enumerate(values):
        x = pad + (i / (len(values) - 1)) * (width - 2 * pad)
        y = (
            pad + (1 - (v - v_min) / span) * (height - 2 * pad)
            if span > 0 else height / 2
        )
        pts.append(f"{x:.1f},{y:.1f}")
    delta = values[-1] - values[0]
    if abs(delta) < abs(v_max) * 0.02:
        color = "#94a3b8"                 # flat
    elif (delta > 0) == higher_is_better:
        color = "#10B981"                 # improving
    else:
        color = "#EF4444"                 # deteriorating
    path_d = "M " + " L ".join(pts)
    # Latest-value marker dot
    last_x, last_y = pts[-1].split(",")
    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'style="vertical-align:middle;">'
        f'<path d="{path_d}" stroke="{color}" stroke-width="1.8" '
        f'fill="none" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
        f'<circle cx="{last_x}" cy="{last_y}" r="2.5" '
        f'fill="{color}"/>'
        f'</svg>'
    )


def _metric_history_values(
    history: List[HospitalMetrics], attr: str,
) -> List[float]:
    """Pull one metric attr across target's year history."""
    vals: List[float] = []
    for h in history:
        v = getattr(h, attr, None)
        if v is not None:
            vals.append(float(v))
    return vals


def _box_plot(
    target_value: float, p25: float, median: float, p75: float,
    peer_values: Optional[List[float]] = None,
    higher_is_better: bool = True,
    width: int = 180, height: int = 28,
) -> str:
    """Small box-plot SVG: whiskers to min/max, box P25-P75, target
    marker as a triangle. Shows where target sits within the peer
    density at a glance."""
    if peer_values:
        lo = min(peer_values)
        hi = max(peer_values)
    else:
        lo = min(p25, target_value)
        hi = max(p75, target_value)
    # Include target value to ensure it renders
    lo = min(lo, target_value) if target_value else lo
    hi = max(hi, target_value) if target_value else hi
    span = hi - lo or max(abs(hi), 1e-6)
    pad_x = 8
    inner = width - 2 * pad_x

    def x(v: float) -> float:
        return pad_x + ((v - lo) / span) * inner

    mid_y = height / 2
    box_h = 10
    box_top = mid_y - box_h / 2
    # Whiskers
    whisker = (
        f'<line x1="{x(lo):.1f}" y1="{mid_y:.1f}" '
        f'x2="{x(hi):.1f}" y2="{mid_y:.1f}" '
        f'stroke="#475569" stroke-width="1"/>'
    )
    # Box
    box = (
        f'<rect x="{x(p25):.1f}" y="{box_top:.1f}" '
        f'width="{max(2, x(p75) - x(p25)):.1f}" '
        f'height="{box_h:.1f}" fill="#334155" '
        f'stroke="#64748b" stroke-width="0.5"/>'
    )
    # Median tick
    med_tick = (
        f'<line x1="{x(median):.1f}" y1="{box_top:.1f}" '
        f'x2="{x(median):.1f}" '
        f'y2="{box_top + box_h:.1f}" '
        f'stroke="#f1f5f9" stroke-width="1.5"/>'
    )
    # Target marker (diamond)
    if target_value is not None:
        tx = x(target_value)
        # Color: green if target better than median per polarity
        if target_value > p75:
            color = "#10B981" if higher_is_better else "#EF4444"
        elif target_value < p25:
            color = "#EF4444" if higher_is_better else "#10B981"
        else:
            color = "#F59E0B"
        target_mark = (
            f'<polygon points="'
            f'{tx:.1f},{mid_y - 7} '
            f'{tx + 5:.1f},{mid_y} '
            f'{tx:.1f},{mid_y + 7} '
            f'{tx - 5:.1f},{mid_y}" '
            f'fill="{color}" stroke="#0f172a" '
            f'stroke-width="0.5">'
            f'<title>Target: {target_value:.3g}</title>'
            f'</polygon>'
        )
    else:
        target_mark = ""
    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'style="vertical-align:middle;">'
        + whisker + box + med_tick + target_mark
        + '</svg>'
    )


def _variance_chip(bm: MetricBenchmark) -> str:
    """Small chip showing variance direction and semantic good/bad."""
    hib = bm.spec.higher_is_better
    if bm.verdict.startswith("above"):
        good = hib
        cls = "above"
    elif bm.verdict.startswith("below"):
        good = not hib
        cls = "below"
    else:
        good = None
        cls = "inside"
    if good is True:
        chip_cls = "hx-chip-above"
        label = "ABOVE PEER"
    elif good is False:
        chip_cls = "hx-chip-below"
        label = "BELOW PEER"
    else:
        chip_cls = "hx-chip-inside"
        label = "IN-BAND"
    return (
        f'<span class="hx-chip {chip_cls}">{label}</span>'
    )


def _metric_row(
    bm: MetricBenchmark,
    history: Optional[List[HospitalMetrics]] = None,
    peer_values: Optional[List[float]] = None,
) -> str:
    # Variance color: good=green, bad=red, neutral
    hib = bm.spec.higher_is_better
    if bm.verdict.startswith("above"):
        var_color = P["positive"] if hib else P["negative"]
    elif bm.verdict.startswith("below"):
        var_color = P["negative"] if hib else P["positive"]
    else:
        var_color = P["text_dim"]

    # Target sparkline across target's filing history
    trend_html = ""
    if history and len(history) >= 2:
        vals = _metric_history_values(history, bm.spec.attr)
        trend_html = _sparkline(vals, hib)
    else:
        trend_html = (
            f'<span style="font-size:9.5px;color:{P["text_faint"]};">'
            f'single year</span>'
        )

    # Distribution box-plot target vs peers
    boxplot_html = _box_plot(
        bm.target_value, bm.peer_p25, bm.peer_median, bm.peer_p75,
        peer_values=peer_values,
        higher_is_better=hib,
    )

    return (
        f'<div class="hx-metric-row">'
        f'<div>'
        f'<div class="hx-metric-name">{html.escape(bm.spec.label)}</div>'
        f'<div class="hx-metric-help">{html.escape(bm.spec.unit_help)}</div>'
        f'</div>'
        f'<div class="hx-metric-val" style="color:{P["text"]};">'
        f'{bm.spec.fmt(bm.target_value)}</div>'
        f'<div class="hx-metric-peer">{bm.spec.fmt(bm.peer_p25)}</div>'
        f'<div class="hx-metric-peer" style="color:{P["text"]};'
        f'font-weight:700;">{bm.spec.fmt(bm.peer_median)}</div>'
        f'<div class="hx-metric-peer">{bm.spec.fmt(bm.peer_p75)}</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{var_color};font-size:12px;">'
        f'{bm.variance_vs_median_pct*100:+.1f}%</div>'
        f'<div style="margin-top:2px;">{_variance_chip(bm)}</div>'
        f'</div>'
        f'<div>{trend_html}{boxplot_html}</div>'
        f'</div>'
    )


def _metrics_by_category(report: XRayReport) -> str:
    """Group metrics by category with a category header per section."""
    by_cat: Dict[str, List[MetricBenchmark]] = {}
    for bm in report.metrics:
        by_cat.setdefault(bm.spec.category, []).append(bm)
    blocks: List[str] = []
    cat_order = [
        "Size", "Payer Mix", "Revenue Cycle",
        "Cost Structure", "Margin",
    ]
    header = (
        f'<div class="hx-metric-row head">'
        f'<div>Metric</div>'
        f'<div>Target</div>'
        f'<div>Peer P25</div>'
        f'<div>Peer Median</div>'
        f'<div>Peer P75</div>'
        f'<div style="text-align:right;">Variance</div>'
        f'<div>Trend · Distribution</div>'
        f'</div>'
    )
    # Pre-compute peer-value pools for the box-plots
    peer_values_by_attr: Dict[str, List[float]] = {}
    for bm in report.metrics:
        vals = []
        for p in report.peers:
            v = getattr(p.hospital, bm.spec.attr, None)
            if v is None:
                continue
            try:
                v = float(v)
            except (ValueError, TypeError):
                continue
            if bm.spec.attr in (
                "occupancy_rate", "contractual_allowance_rate",
                "net_to_gross_ratio", "operating_margin_on_npr",
                "net_income_margin_on_npr", "payer_diversity_index",
            ) and v == 0:
                continue
            vals.append(v)
        peer_values_by_attr[bm.spec.attr] = vals
    for cat in cat_order:
        items = by_cat.get(cat) or []
        if not items:
            continue
        blocks.append(f'<div class="hx-cat-title">{cat}</div>')
        blocks.append(header)
        blocks.append(
            "".join(
                _metric_row(
                    bm,
                    history=report.target_history,
                    peer_values=peer_values_by_attr.get(
                        bm.spec.attr,
                    ),
                )
                for bm in items
            ),
        )
    return "".join(blocks)


def _public_comp_context(target: HospitalMetrics) -> str:
    """Compare target's HCRIS operating margin against public
    hospital-system comps from the Seeking Alpha library.  Answers
    the partner question: "how does this private target look
    vs the public tape?"
    """
    try:
        from ..market_intel.public_comps import list_companies
    except Exception:  # noqa: BLE001
        return ""
    try:
        all_comps = list_companies()
    except Exception:  # noqa: BLE001
        return ""
    # Filter to hospital-system comps
    hosp_comps = [
        c for c in all_comps
        if getattr(c, "category", "").upper() in (
            "MULTI_SITE_ACUTE_HOSPITAL",
            "MULTI_SITE_ACUTE_AND_BEHAVIORAL",
        )
    ]
    if not hosp_comps:
        return ""

    target_margin = target.operating_margin_on_npr
    # Compute public median op margin as peer anchor
    public_margins = [
        c.operating_margin for c in hosp_comps
        if c.operating_margin is not None
    ]
    if not public_margins:
        return ""
    public_median_margin = sorted(public_margins)[
        len(public_margins) // 2
    ]

    # Per-comp rows
    rows: List[str] = []
    for c in sorted(
        hosp_comps,
        key=lambda c: -(c.operating_margin or 0),
    )[:6]:
        mg = c.operating_margin or 0.0
        mg_color = (
            P["positive"] if mg > 0.10
            else P["warning"] if mg > 0.02
            else P["negative"]
        )
        delta = target_margin - mg
        rows.append(
            f'<tr>'
            f'<td style="padding:4px 8px;font-family:\'JetBrains Mono\','
            f'monospace;color:{P["accent"]};">'
            f'{html.escape(c.ticker)}</td>'
            f'<td style="padding:4px 8px;color:{P["text_dim"]};">'
            f'{html.escape(c.name)}</td>'
            f'<td style="padding:4px 8px;text-align:right;'
            f'font-family:\'JetBrains Mono\',monospace;'
            f'color:{mg_color};font-weight:700;">'
            f'{mg*100:+.1f}%</td>'
            f'<td style="padding:4px 8px;text-align:right;'
            f'font-family:\'JetBrains Mono\',monospace;'
            f'color:{P["text_dim"]};">'
            f'{delta*100:+.1f}pp</td>'
            f'<td style="padding:4px 8px;font-family:\'JetBrains Mono\','
            f'monospace;color:{P["text_faint"]};font-size:10px;">'
            f'{c.ev_ebitda_multiple:.1f}×</td>'
            f'</tr>'
        )
    verdict = (
        "beats" if target_margin > public_median_margin
        else "trails"
    )
    delta = abs(target_margin - public_median_margin) * 100
    return (
        f'<div class="hx-panel">'
        f'<div class="hx-section-label" style="margin-top:0;">'
        f'Public market context · Seeking Alpha hospital comps</div>'
        f'<div style="font-size:13px;color:{P["text_dim"]};'
        f'line-height:1.6;margin-bottom:12px;max-width:900px;">'
        f'Target operating margin '
        f'<strong style="color:{P["text"]};">'
        f'{target_margin*100:+.1f}%</strong> '
        f'{verdict} public-comp median '
        f'<strong style="color:{P["text"]};">'
        f'{public_median_margin*100:+.1f}%</strong> by '
        f'{delta:.1f} pp. Public comps trade at a median '
        f'EV/EBITDA of ~9x; target-implied multiple should '
        f'adjust for the margin delta + size discount.'
        f'</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-size:12px;">'
        f'<thead><tr style="color:{P["text_faint"]};font-size:10px;'
        f'letter-spacing:1.2px;text-transform:uppercase;font-weight:700;">'
        f'<th style="padding:6px 8px;text-align:left;'
        f'border-bottom:2px solid {P["border"]};">Ticker</th>'
        f'<th style="padding:6px 8px;text-align:left;'
        f'border-bottom:2px solid {P["border"]};">Company</th>'
        f'<th style="padding:6px 8px;text-align:right;'
        f'border-bottom:2px solid {P["border"]};">Op Margin</th>'
        f'<th style="padding:6px 8px;text-align:right;'
        f'border-bottom:2px solid {P["border"]};">Target Δ</th>'
        f'<th style="padding:6px 8px;text-align:left;'
        f'border-bottom:2px solid {P["border"]};">EV/EBITDA</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        f'<div class="hx-callout">'
        f'Public-hospital comps are curated from 10-K / analyst '
        f'consensus via '
        f'<a href="/market-intel/seeking-alpha" '
        f'style="color:{P["accent"]};">→ Seeking Alpha Market Intel</a>. '
        f'Margin delta × $ of NPR ≈ the EBITDA gap between the '
        f'target and the public bench.'
        f'</div>'
        f'</div>'
    )


def _peer_table(peers: List[PeerMatch]) -> str:
    headers = [
        "CCN", "Hospital", "State", "Beds", "FY",
        "Medicare %", "Op Margin", "NPR ($M)",
        "Distance", "Same-state", "Same-region",
    ]
    rows = []
    sort_keys = []
    for p in peers:
        h = p.hospital
        # Color the op margin by band so analysts spot negative-margin
        # peers instantly when scanning for comparables
        op_color = (
            P["negative"] if h.operating_margin_on_npr < 0
            else P["positive"] if h.operating_margin_on_npr > 0.08
            else P["text_dim"]
        )
        op_cell = (
            f'<span style="color:{op_color};font-weight:700;">'
            f'{h.operating_margin_on_npr*100:+.1f}%</span>'
        )
        ccn_link = (
            f'<a href="/diligence/hcris-xray?ccn={html.escape(h.ccn)}" '
            f'style="color:{P["accent"]};text-decoration:none;'
            f'font-family:\'JetBrains Mono\',monospace;">'
            f'{html.escape(h.ccn)}</a>'
        )
        rows.append([
            ccn_link,
            html.escape(h.name[:45]),
            h.state,
            f"{h.beds:,}",
            str(h.fiscal_year),
            f"{h.medicare_day_pct*100:.1f}%",
            op_cell,
            f"{h.net_patient_revenue/1e6:,.1f}",
            f"{p.distance:.3f}",
            "✓" if p.same_state else "",
            "✓" if p.same_region else "",
        ])
        sort_keys.append([
            h.ccn, h.name, h.state, h.beds, h.fiscal_year,
            h.medicare_day_pct, h.operating_margin_on_npr,
            h.net_patient_revenue,
            p.distance,
            1 if p.same_state else 0,
            1 if p.same_region else 0,
        ])
    return sortable_table(
        headers, rows, sort_keys=sort_keys,
        name="hcris_peer_roster",
        caption=(
            "Peer roster · sorted by feature distance (closest "
            "match first) · CSV export wired"
        ),
    )


def _search_results(hits: List[HospitalMetrics]) -> str:
    if not hits:
        return (
            f'<div style="font-size:12px;color:{P["text_dim"]};'
            f'padding:12px 0;">'
            f'No matches. Try a broader substring, or search by CCN.'
            f'</div>'
        )
    rows: List[str] = []
    rows.append(
        f'<div class="hx-search-result" style="color:{P["text_faint"]};'
        f'font-size:10px;letter-spacing:1.2px;text-transform:uppercase;'
        f'font-weight:700;border-bottom:2px solid {P["border"]};">'
        f'<div>CCN</div><div>Hospital</div>'
        f'<div style="text-align:right;">State</div>'
        f'<div class="right">Beds</div>'
        f'<div class="right">FY</div>'
        f'</div>'
    )
    for h in hits:
        url = f"/diligence/hcris-xray?ccn={html.escape(h.ccn)}"
        rows.append(
            f'<a class="hx-search-result" href="{url}">'
            f'<span class="ccn">{html.escape(h.ccn)}</span>'
            f'<span class="nm">{html.escape(h.name)}</span>'
            f'<span style="text-align:right;">{html.escape(h.state)}</span>'
            f'<span class="right">{h.beds:,}</span>'
            f'<span class="right">{h.fiscal_year}</span>'
            f'</a>'
        )
    return "".join(rows)


# ────────────────────────────────────────────────────────────────────
# Landing form + search
# ────────────────────────────────────────────────────────────────────

def _landing(qs: Optional[Dict[str, List[str]]] = None) -> str:
    qs = qs or {}
    summary = dataset_summary()

    # Optional inline search
    q = (qs.get("q") or [""])[0].strip()
    state_filter = (qs.get("state") or [""])[0].strip()
    search_block = ""
    if q or state_filter:
        hits = search_hospitals(
            q, limit=20,
            state=state_filter or None,
        )
        search_block = (
            f'<div class="hx-panel">'
            f'<div class="hx-section-label" style="margin-top:0;">'
            f'Search results · {len(hits)} matches'
            f'</div>'
            f'{_search_results(hits)}'
            f'</div>'
        )

    search_form = f"""
<form method="get" action="/diligence/hcris-xray" class="hx-wrap">
  <div class="hx-panel">
    <div class="hx-section-label" style="margin-top:0;">
      Find a hospital · search by name, CCN, or city</div>
    <div class="hx-form-grid">
      <div class="hx-form-field" style="grid-column:span 2;">
        <label>Name / CCN / city substring</label>
        <input name="q" value="{html.escape(q)}" placeholder="e.g. REGIONAL, 010001, DOTHAN"/>
      </div>
      <div class="hx-form-field"><label>State filter (optional)</label>
        <input name="state" value="{html.escape(state_filter)}" placeholder="e.g. AL"/></div>
    </div>
    <button class="hx-form-submit" type="submit">Search HCRIS</button>
  </div>
</form>
"""
    direct_form = f"""
<form method="get" action="/diligence/hcris-xray" class="hx-wrap">
  <div class="hx-panel">
    <div class="hx-section-label" style="margin-top:0;">
      Direct X-Ray · run benchmark by CCN</div>
    <div class="hx-form-grid">
      <div class="hx-form-field">
        <label>CCN (Medicare provider #)</label>
        <input name="ccn" placeholder="e.g. 010001"/>
      </div>
      <div class="hx-form-field">
        <label>Peer pool size (default 25)</label>
        <input name="peer_k" value="25"/>
      </div>
      <div class="hx-form-field">
        <label>Bed band ± (default 30%)</label>
        <input name="bed_band_pct" value="0.30"/>
      </div>
    </div>
    <button class="hx-form-submit" type="submit">Run X-Ray</button>
  </div>
</form>
"""
    stats = (
        f'<div class="hx-panel">'
        f'<div class="hx-section-label" style="margin-top:0;">'
        f'Dataset coverage</div>'
        f'<div style="display:flex;gap:24px;flex-wrap:wrap;'
        f'font-size:12.5px;color:{P["text_dim"]};line-height:1.65;">'
        f'<div><strong style="color:{P["text"]};">'
        f'{summary["total_rows"]:,}</strong> hospital-year filings</div>'
        f'<div><strong style="color:{P["text"]};">'
        f'{len(summary["states"])}</strong> states</div>'
        f'<div><strong style="color:{P["text"]};">'
        f'{len(summary["years"])}</strong> fiscal years</div>'
        f'<div><strong style="color:{P["text"]};">'
        f'{summary["cohorts"].get("COMMUNITY", 0) + summary["cohorts"].get("REGIONAL", 0):,}</strong> '
        f'community + regional-size hospitals</div>'
        f'</div>'
        f'<div class="hx-callout">'
        f'HCRIS is CMS\'s filed Medicare cost-report dataset — '
        f'every Medicare-participating hospital files annually with '
        f'2,500+ fields covering bed count, payer-day mix, patient '
        f'revenue, allowances, operating expenses, and net income. '
        f'The X-Ray engine finds the 25-50 true peer hospitals for '
        f'any target (matched on size cohort, state, payer mix, and '
        f'fiscal year), computes 15 derived RCM / cost / margin '
        f'metrics, and flags where the target lies inside, above, '
        f'or below the peer P25-P75 band.'
        f'</div>'
        f'</div>'
    )

    body = (
        _scoped_styles()
        + '<div class="hx-wrap">'
        + deal_context_bar(qs, active_surface="hcris")
        + '<div style="padding:22px 0 16px 0;">'
        + '<div class="hx-eyebrow">HCRIS-Native Peer X-Ray</div>'
        + '<div class="hx-h1">Benchmark any hospital against its true peers.</div>'
        + '</div>'
        + search_form
        + search_block
        + direct_form
        + stats
        + '</div>'
    )
    return chartis_shell(
        body, "HCRIS X-Ray",
        subtitle=f"{summary['total_rows']:,} Medicare cost reports · 15 metrics",
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def render_hcris_xray_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}

    def first(k: str, d: str = "") -> str:
        return (qs.get(k) or [d])[0].strip()

    def fnum(k: str, d: Optional[float] = None) -> Optional[float]:
        v = first(k)
        if not v:
            return d
        try:
            return float(v)
        except ValueError:
            return d

    def fint(k: str, d: int) -> int:
        v = first(k)
        if not v:
            return d
        try:
            return int(float(v))
        except ValueError:
            return d

    ccn = first("ccn")
    name = first("name")
    if not ccn and not name:
        return _landing(qs)

    peer_k = max(5, min(100, fint("peer_k", 25)))
    bed_band = max(0.05, min(1.0, fnum("bed_band_pct", 0.30) or 0.30))
    state = first("state") or None
    fy_raw = first("fiscal_year")
    fiscal_year: Optional[int] = None
    if fy_raw:
        try:
            fiscal_year = int(float(fy_raw))
        except ValueError:
            fiscal_year = None

    report = xray(
        ccn=ccn or None, name=name or None,
        state=state, fiscal_year=fiscal_year,
        peer_k=peer_k, bed_band_pct=bed_band,
    )
    if report is None:
        return chartis_shell(
            _scoped_styles()
            + f'<div class="hx-wrap" style="padding:28px;">'
            + f'<div class="hx-eyebrow">HCRIS X-Ray</div>'
            + f'<div class="hx-h1" style="color:{P["negative"]};">'
            + 'Hospital not found.</div>'
            + f'<div class="hx-callout">No HCRIS filing matched '
            + f'<code>{html.escape(ccn or name)}</code>. Try '
            + f'searching instead.</div>'
            + f'<div style="margin-top:14px;">'
            + f'<a href="/diligence/hcris-xray" '
            + f'style="color:{P["accent"]};">← Back to search</a>'
            + '</div></div>',
            "HCRIS X-Ray — not found",
        )

    # Plain-English read
    target = report.target
    outperforming = [
        bm for bm in report.metrics
        if (
            bm.verdict.startswith("above") and bm.spec.higher_is_better
        ) or (
            bm.verdict.startswith("below")
            and not bm.spec.higher_is_better
        )
    ]
    underperforming = [
        bm for bm in report.metrics
        if (
            bm.verdict.startswith("below") and bm.spec.higher_is_better
        ) or (
            bm.verdict.startswith("above")
            and not bm.spec.higher_is_better
        )
    ]
    top_over = sorted(
        outperforming,
        key=lambda b: -abs(b.variance_vs_median_pct),
    )[:1]
    top_under = sorted(
        underperforming,
        key=lambda b: -abs(b.variance_vs_median_pct),
    )[:1]
    chart_plain_parts: List[str] = []
    if top_under:
        u = top_under[0]
        chart_plain_parts.append(
            f'Biggest peer gap: '
            f'<strong style="color:{P["negative"]};">'
            f'{u.spec.label}</strong> is '
            f'<strong>{u.spec.fmt(u.target_value)}</strong> vs '
            f'peer median '
            f'<strong>{u.spec.fmt(u.peer_median)}</strong> '
            f'(<strong>{u.variance_vs_median_pct*100:+.1f}%</strong>, '
            f'{u.verdict}).'
        )
    if top_over:
        o = top_over[0]
        chart_plain_parts.append(
            f'Strongest outperformance: '
            f'<strong style="color:{P["positive"]};">'
            f'{o.spec.label}</strong> at '
            f'<strong>{o.spec.fmt(o.target_value)}</strong> vs '
            f'median <strong>{o.spec.fmt(o.peer_median)}</strong> '
            f'(<strong>{o.variance_vs_median_pct*100:+.1f}%</strong>).'
        )
    if not chart_plain_parts:
        chart_plain_parts.append(
            "Target sits squarely inside the peer P25-P75 band "
            "on every measured metric — no outlier signal."
        )
    chart_plain = " ".join(chart_plain_parts)

    hero = (
        f'<div style="padding:22px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="hx-eyebrow">HCRIS-Native Peer X-Ray</div>'
        f'<div class="hx-h1">{html.escape(target.name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'margin-top:4px;">'
        f'{len(report.peers)} peers · {report.peer_filter_used} · '
        f'benchmarked on {len(report.metrics)} metrics'
        f'</div>'
        f'{_target_card(target, trend_signal=report.trend_signal, history_len=len(report.target_history))}'
        + interpret_callout(
            "Plain-English read:", chart_plain,
            tone="bad" if top_under else "good",
        )
        + f'</div>'
    )

    metrics_panel = (
        f'<div class="hx-panel">'
        f'<div class="hx-section-label" style="margin-top:0;">'
        f'Peer benchmark · target vs P25 / median / P75 · '
        f'{report.peer_filter_used}</div>'
        f'{_metrics_by_category(report)}'
        f'<div class="hx-callout">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'Target column is the filed value from the hospital\'s '
        f'most recent Medicare cost report. P25 / median / P75 are '
        f'drawn from the {len(report.peers)} peer hospitals matched '
        f'on size cohort, state, payer mix, and fiscal year. '
        f'Variance is signed % vs peer median; '
        f'<span style="color:{P["positive"]};">green chip</span> '
        f'= better than peers on this metric; '
        f'<span style="color:{P["negative"]};">red chip</span> '
        f'= worse than peers; amber/neutral = inside the P25-P75 band.'
        f'</div>'
        f'</div>'
    )

    peers_panel = (
        f'<div class="hx-panel">'
        f'<div class="hx-section-label" style="margin-top:0;">'
        f'Peer roster</div>'
        f'{_peer_table(report.peers)}'
        f'</div>'
    )

    # Real EBITDA from HCRIS when positive; fallback to 10% placeholder
    # for deals with negative operating margins (common in hospitals)
    actual_ebitda = max(
        target.net_patient_revenue * target.operating_margin_on_npr,
        target.net_patient_revenue * 0.05,
    )
    # Public-comp context — target vs HCA / THC / UHS op margin
    public_comp_block = _public_comp_context(target)

    # Build cross-links with proper URL-encoding. html.escape alone
    # leaves spaces and ampersands unencoded, which crashes downstream
    # http clients that validate the URL path.
    from urllib.parse import urlencode as _urlencode

    def _link(base: str, params: Dict[str, Any]) -> str:
        clean = {k: str(v) for k, v in params.items() if v not in (None, "", 0, 0.0)}
        qs = _urlencode(clean)
        return html.escape(f"{base}?{qs}", quote=True)

    npr = f"{target.net_patient_revenue:.0f}"
    eb = f"{actual_ebitda:.0f}"
    # Reasonable defaults for cap structure so the Deal MC / Bear Case
    # cross-link actually runs without manual cap-structure typing.
    # Entry multiple ≈ peer-median 9.0x for community hospitals.
    # 50/50 equity/debt split is the baseline LBO convention.
    default_entry_multiple = 9.0
    default_ev = actual_ebitda * default_entry_multiple
    default_equity = default_ev * 0.42   # ~42% equity typical for hospital LBO
    default_debt = default_ev * 0.58
    ev_str = f"{default_ev:.0f}"
    equity_str = f"{default_equity:.0f}"
    debt_str = f"{default_debt:.0f}"
    # Pass target CCN through so the Bear Case pipeline auto-runs HCRIS
    ccn = target.ccn
    cross_link = (
        f'<div class="hx-panel">'
        f'<div class="hx-section-label" style="margin-top:0;">'
        f'Cross-reference · pre-seeded with HCRIS-filed NPR, '
        f'operating margin + peer-median 9.0× entry cap structure</div>'
        f'<div style="font-size:13px;color:{P["text_dim"]};'
        f'line-height:1.7;">'
        f'<a href="{_link("/diligence/deal-mc", {"deal_name": target.name, "revenue_usd": npr, "ebitda_usd": eb, "ev_usd": ev_str, "equity_usd": equity_str, "debt_usd": debt_str, "entry_multiple": f"{default_entry_multiple:.1f}"})}" '
        f'style="color:{P["accent"]};">→ Deal MC</a> · '
        f'<a href="{_link("/diligence/payer-stress", {"target_name": target.name, "total_npr_usd": npr, "total_ebitda_usd": eb})}" '
        f'style="color:{P["accent"]};">→ Payer Stress</a> · '
        f'<a href="{_link("/diligence/covenant-stress", {"deal_name": target.name, "ebitda_y0": eb, "total_debt_usd": debt_str})}" '
        f'style="color:{P["accent"]};">→ Covenant Stress</a> · '
        f'<a href="{_link("/diligence/regulatory-calendar", {"target_name": target.name, "specialty": "HOSPITAL", "revenue_usd": npr, "ebitda_usd": eb})}" '
        f'style="color:{P["accent"]};">→ Regulatory Calendar</a> · '
        f'<a href="{_link("/diligence/bear-case", {"deal_name": target.name, "specialty": "HOSPITAL", "revenue_year0_usd": npr, "ebitda_year0_usd": eb, "enterprise_value_usd": ev_str, "equity_check_usd": equity_str, "debt_usd": debt_str, "hcris_ccn": ccn})}" '
        f'style="color:{P["accent"]};">→ Bear Case</a>'
        f'</div>'
        f'<div style="font-size:10.5px;color:{P["text_faint"]};'
        f'margin-top:8px;letter-spacing:0.3px;">'
        f'EV <code>${default_ev/1e6:,.0f}M</code> (9.0× '
        f'${actual_ebitda/1e6:,.1f}M EBITDA) · Equity '
        f'<code>${default_equity/1e6:,.0f}M</code> · Debt '
        f'<code>${default_debt/1e6:,.0f}M</code> · override '
        f'any of these on the destination page.'
        f'</div></div>'
    )

    body = (
        _scoped_styles()
        + '<div class="hx-wrap">'
        + deal_context_bar(qs, active_surface="hcris")
        + hero
        + metrics_panel
        + public_comp_block
        + peers_panel
        + cross_link
        + export_json_panel(
            '<div class="hx-section-label" style="margin-top:22px;">'
            'JSON export — full X-Ray payload</div>',
            payload=report.to_dict(),
            name=f"hcris_xray_{target.ccn}",
        )
        + bookmark_hint()
        + '</div>'
    )
    return chartis_shell(
        body, f"HCRIS X-Ray — {target.name}",
        subtitle=(
            f"CCN {target.ccn} · {target.beds} beds · "
            f"FY{target.fiscal_year}"
        ),
    )
