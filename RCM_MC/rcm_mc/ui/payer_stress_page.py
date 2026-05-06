"""Payer Mix Stress Lab page.

Route: ``/diligence/payer-stress``

Partner-facing surface for stress-testing a target's commercial
payer mix.  Partners paste the mix (name + share + optional
renewal date) and the page returns:

    * Verdict card with risk score, top-1/top-3 concentration,
      HHI index, concentration amplifier.
    * Payer mix donut + concentration gauge.
    * Per-payer stress cards with negotiating leverage, median &
      P10 rate moves, NPR delta, contract renewal date.
    * Yearly NPR impact cone (P10 / P50 / P90).
    * Renewal timeline SVG.
    * Plain-English partner interpretation + cross-links.
"""
from __future__ import annotations

import html
from datetime import date
from typing import Any, Dict, List, Optional

from ..diligence.payer_stress import (
    PAYER_PRIORS, PayerMixEntry, PayerStressReport,
    PayerStressRow, PayerStressVerdict, YearlyNPRImpact,
    default_hospital_mix, run_payer_stress,
)
from ._chartis_kit import P, chartis_shell
from .power_ui import (
    benchmark_chip, bookmark_hint, deal_context_bar,
    export_json_panel, interpret_callout, provenance, sortable_table,
)


# ────────────────────────────────────────────────────────────────────
# Scoped CSS (ps- prefix)
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.ps-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.ps-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.ps-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.ps-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.ps-panel{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 20px;margin-bottom:16px;}}
.ps-callout{{background:{pa};padding:12px 16px;border-left:3px solid {ac};
border-radius:0 3px 3px 0;font-size:12px;color:{td};line-height:1.65;
max-width:900px;margin-top:12px;}}
.ps-verdict-card{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:18px 22px;margin-top:14px;position:relative;overflow:hidden;}}
.ps-verdict-card::before{{content:"";position:absolute;top:0;left:0;right:0;
height:3px;background:linear-gradient(90deg,var(--tone),{ac});}}
.ps-verdict-PASS{{--tone:{po};}}
.ps-verdict-CAUTION{{--tone:{wn};}}
.ps-verdict-WARNING{{--tone:{wn};}}
.ps-verdict-FAIL{{--tone:{ne};}}
.ps-verdict-badge{{display:inline-block;padding:4px 12px;border-radius:3px;
font-size:11px;font-weight:700;letter-spacing:1.3px;text-transform:uppercase;
background:var(--tone);color:#fff;}}
.ps-verdict-headline{{font-size:17px;color:{tx};font-weight:600;
line-height:1.45;margin-top:12px;}}
.ps-verdict-rationale{{font-size:12px;color:{td};line-height:1.55;
margin-top:8px;max-width:900px;}}
.ps-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
gap:14px;margin-top:14px;}}
.ps-kpi__label{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
color:{tf};font-weight:600;margin-bottom:3px;}}
.ps-kpi__val{{font-size:22px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;color:{tx};}}
.ps-kpi__val.neg{{color:{ne};}}
.ps-kpi__val.pos{{color:{po};}}
.ps-payer-card{{background:{pn};border:1px solid {bd};border-radius:4px;
border-left:3px solid var(--tone);padding:14px 18px;margin-bottom:12px;}}
.ps-payer-head{{display:flex;justify-content:space-between;gap:12px;
flex-wrap:wrap;align-items:baseline;}}
.ps-payer-name{{font-size:14.5px;color:{tx};font-weight:600;}}
.ps-payer-share{{font-family:"JetBrains Mono",monospace;font-size:17px;
font-weight:700;color:{tx};font-variant-numeric:tabular-nums;}}
.ps-payer-meta{{font-size:10.5px;color:{tf};text-transform:uppercase;
letter-spacing:1.1px;margin-top:3px;}}
.ps-payer-stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
gap:12px;margin-top:12px;}}
.ps-payer-stat{{font-size:11px;color:{tf};
text-transform:uppercase;letter-spacing:1.1px;font-weight:600;}}
.ps-payer-stat-val{{font-family:"JetBrains Mono",monospace;font-size:15px;
color:{tx};font-weight:700;margin-top:3px;}}
.ps-payer-narrative{{font-size:12px;color:{td};line-height:1.65;
margin-top:10px;max-width:820px;}}
.ps-form-field label{{display:block;font-size:10px;color:{tf};
letter-spacing:1.2px;text-transform:uppercase;font-weight:600;margin-bottom:4px;}}
.ps-form-field input,.ps-form-field textarea{{width:100%;
background:{pa};color:{tx};border:1px solid {bd};padding:8px 10px;
border-radius:3px;font-family:"JetBrains Mono",monospace;font-size:13px;}}
.ps-form-field textarea{{min-height:200px;resize:vertical;line-height:1.6;}}
.ps-form-submit{{margin-top:18px;padding:10px 20px;background:{ac};
color:#fff;border:0;border-radius:3px;font-size:12px;letter-spacing:1.3px;
text-transform:uppercase;font-weight:700;cursor:pointer;}}
.ps-form-submit:hover{{filter:brightness(1.15);}}
.ps-form-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
gap:14px;}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# Visualisations
# ────────────────────────────────────────────────────────────────────

_DONUT_COLORS = [
    "var(--sc-navy)", "#2563eb", "#0891b2", "#10B981",
    "#8b5cf6", "#ec4899", "#F59E0B", "#ef4444",
    "#64748b", "#334155", "#475569", "#71717a",
]


def _mix_donut_svg(
    rows: List[PayerStressRow], size: int = 260,
) -> str:
    """Payer mix donut chart with concentration ring."""
    import math
    if not rows:
        return ""
    cx = cy = size / 2
    outer_r = size / 2 - 10
    inner_r = outer_r * 0.55
    # Order by share desc
    ordered = sorted(rows, key=lambda r: -r.share_of_npr)
    total = sum(r.share_of_npr for r in ordered) or 1.0

    segments: List[str] = []
    labels: List[str] = []
    start_angle = -90.0
    for i, r in enumerate(ordered):
        frac = r.share_of_npr / total
        sweep = frac * 360.0
        end_angle = start_angle + sweep
        # Outer ring arc path (donut segment via two arcs)
        rad_a = math.radians(start_angle)
        rad_b = math.radians(end_angle)
        x0 = cx + outer_r * math.cos(rad_a)
        y0 = cy + outer_r * math.sin(rad_a)
        x1 = cx + outer_r * math.cos(rad_b)
        y1 = cy + outer_r * math.sin(rad_b)
        ix0 = cx + inner_r * math.cos(rad_a)
        iy0 = cy + inner_r * math.sin(rad_a)
        ix1 = cx + inner_r * math.cos(rad_b)
        iy1 = cy + inner_r * math.sin(rad_b)
        large_arc = 1 if sweep > 180 else 0
        color = _DONUT_COLORS[i % len(_DONUT_COLORS)]
        d = (
            f"M {x0:.1f} {y0:.1f} "
            f"A {outer_r:.1f} {outer_r:.1f} 0 {large_arc} 1 "
            f"{x1:.1f} {y1:.1f} "
            f"L {ix1:.1f} {iy1:.1f} "
            f"A {inner_r:.1f} {inner_r:.1f} 0 {large_arc} 0 "
            f"{ix0:.1f} {iy0:.1f} Z"
        )
        tip = (
            f"{r.payer_name}: {frac*100:.1f}% of NPR "
            f"(${r.npr_attributed_usd/1e6:,.1f}M)"
        )
        segments.append(
            f'<path d="{d}" fill="{color}" '
            f'stroke="{P["panel"]}" stroke-width="1">'
            f'<title>{html.escape(tip)}</title></path>'
        )
        # Label for segments >= 5%
        if frac >= 0.05:
            mid_angle = math.radians(
                (start_angle + end_angle) / 2,
            )
            lx = cx + (outer_r + 14) * math.cos(mid_angle)
            ly = cy + (outer_r + 14) * math.sin(mid_angle)
            anchor = (
                "end" if math.cos(mid_angle) < -0.2
                else "start" if math.cos(mid_angle) > 0.2
                else "middle"
            )
            labels.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" '
                f'text-anchor="{anchor}" font-size="9.5" '
                f'fill="{P["text_faint"]}" '
                f'font-family="JetBrains Mono,monospace">'
                f'{frac*100:.0f}%</text>'
            )
        start_angle = end_angle

    # Center text — top-1 share
    top1 = ordered[0].share_of_npr if ordered else 0.0
    top1_color = (
        P["negative"] if top1 > 0.40
        else P["warning"] if top1 > 0.25
        else P["positive"]
    )
    center_text = (
        f'<text x="{cx}" y="{cy - 6}" text-anchor="middle" '
        f'font-size="10" fill="{P["text_faint"]}" '
        f'letter-spacing="1.3">TOP-1 SHARE</text>'
        f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" '
        f'font-size="26" font-family="JetBrains Mono,monospace" '
        f'font-weight="700" fill="{top1_color}">'
        f'{top1*100:.0f}%</text>'
    )

    return (
        f'<svg viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" '
        f'style="max-width:100%;">'
        + "".join(segments) + "".join(labels) + center_text
        + '</svg>'
    )


def _legend(rows: List[PayerStressRow]) -> str:
    ordered = sorted(rows, key=lambda r: -r.share_of_npr)
    items = []
    for i, r in enumerate(ordered):
        color = _DONUT_COLORS[i % len(_DONUT_COLORS)]
        items.append(
            f'<div style="display:flex;align-items:baseline;gap:8px;'
            f'padding:5px 0;font-size:12px;color:{P["text_dim"]};">'
            f'<span style="width:10px;height:10px;background:{color};'
            f'display:inline-block;border-radius:2px;"></span>'
            f'<span style="flex:1 1 auto;">'
            f'{html.escape(r.payer_name)}</span>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;'
            f'font-weight:700;color:{P["text"]};">'
            f'{r.share_of_npr*100:.0f}%</span>'
            f'</div>'
        )
    return "".join(items)


def _yearly_cone_chart(
    years: List[YearlyNPRImpact],
    width: int = 820, height: int = 240,
) -> str:
    """NPR-impact cone across the horizon."""
    if not years:
        return ""
    pad_l, pad_r, pad_t, pad_b = 80, 40, 28, 36
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)

    all_vals = []
    for y in years:
        all_vals.extend([
            y.p10_npr_delta_usd, y.p50_npr_delta_usd,
            y.p90_npr_delta_usd,
        ])
    ymin = min(all_vals)
    ymax = max(all_vals)
    # Pad the range
    pad = (ymax - ymin) * 0.10
    ymin -= pad
    ymax += pad
    if ymax - ymin < 1:
        ymax = ymin + 1

    def x(year: int) -> float:
        if len(years) == 1:
            return pad_l + inner_w / 2
        return pad_l + (year - 1) / (len(years) - 1) * inner_w

    def y_pix(v: float) -> float:
        return pad_t + inner_h - (
            (v - ymin) / (ymax - ymin) * inner_h
        )

    # Zero line
    zero_y = y_pix(0.0)
    grid = [
        f'<line x1="{pad_l}" y1="{zero_y:.1f}" '
        f'x2="{pad_l + inner_w}" y2="{zero_y:.1f}" '
        f'stroke="{P["border"]}" stroke-width="1" '
        f'stroke-dasharray="3,3" opacity="0.6"/>',
        f'<text x="{pad_l - 6}" y="{zero_y + 3:.1f}" '
        f'text-anchor="end" font-size="9" '
        f'fill="{P["text_faint"]}" '
        f'font-family="JetBrains Mono,monospace">$0</text>',
    ]
    # P10/P90 band
    p10_pts = [(x(y.year), y_pix(y.p10_npr_delta_usd)) for y in years]
    p90_pts = [(x(y.year), y_pix(y.p90_npr_delta_usd)) for y in years]
    band_path = (
        "M " + " L ".join(f"{px:.1f},{py:.1f}" for px, py in p10_pts)
        + " L " + " L ".join(
            f"{px:.1f},{py:.1f}" for px, py in reversed(p90_pts)
        )
        + " Z"
    )
    p50_d = "M " + " L ".join(
        f"{x(y.year):.1f},{y_pix(y.p50_npr_delta_usd):.1f}"
        for y in years
    )

    # Y-axis labels
    y_labels = []
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        val = ymin + t * (ymax - ymin)
        yp = y_pix(val)
        y_labels.append(
            f'<text x="{pad_l - 6}" y="{yp + 3:.1f}" '
            f'text-anchor="end" font-size="9" '
            f'fill="{P["text_faint"]}" '
            f'font-family="JetBrains Mono,monospace">'
            f'${val/1e6:+.1f}M</text>'
        )

    # Year ticks
    year_ticks = []
    for y in years:
        xc = x(y.year)
        year_ticks.append(
            f'<text x="{xc:.1f}" y="{pad_t + inner_h + 14}" '
            f'text-anchor="middle" font-size="10" '
            f'fill="{P["text_faint"]}" '
            f'font-family="JetBrains Mono,monospace">Y{y.year}</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;height:auto;">'
        f'<rect x="0" y="0" width="{width}" height="{height}" '
        f'fill="{P["panel"]}"/>'
        + "".join(grid)
        + f'<path d="{band_path}" fill="{P["accent"]}" '
        f'opacity="0.22"/>'
        + f'<path d="{p50_d}" stroke="{P["accent"]}" '
        f'stroke-width="2.5" fill="none"/>'
        + "".join(y_labels) + "".join(year_ticks)
        + '</svg>'
    )


def _payer_card(row: PayerStressRow) -> str:
    """Per-payer stress card, color-coded by median $ delta."""
    tone = (
        P["negative"] if row.median_npr_delta_usd < 0
        else P["positive"] if row.median_npr_delta_usd > 0
        else P["text_faint"]
    )
    renewal = row.contract_renewal_date or "not disclosed"
    rate_color = (
        P["negative"] if row.median_rate_move < 0
        else P["positive"]
    )
    tail_color = (
        P["negative"] if row.p10_rate_move < -0.05
        else P["warning"] if row.p10_rate_move < 0
        else P["positive"]
    )
    cat_label = (
        (row.category or "").replace("_", " ").title()
    )

    # "vs library prior" context — is this payer behaving at, above,
    # or below its typical rate-movement pattern for this target?
    # Pull the library prior for the classified payer to compare.
    from ..diligence.payer_stress import get_payer
    prior_context = ""
    if row.payer_id:
        prior = get_payer(row.payer_id)
        if prior is not None:
            # The simulated median is a cumulative N-year move, so
            # compare to the prior's single-period median × horizon.
            # We approximate horizon from the NPR attributed. For
            # 5-year horizon, expected = 5 × prior median.
            # But since we don't know horizon here, frame directly:
            # "library prior: μ=+1.5%, P10=-4.5% per renewal event"
            prior_context = (
                f'<div style="font-size:10.5px;color:{P["text_faint"]};'
                f'margin-top:4px;letter-spacing:0.3px;">'
                f'Library prior per renewal: '
                f'μ <strong style="color:{P["text_dim"]};">'
                f'{prior.rate_move_median*100:+.1f}%</strong> · '
                f'P25 <strong style="color:{P["negative"]};">'
                f'{prior.rate_move_p25*100:+.1f}%</strong> · '
                f'P75 <strong style="color:{P["positive"]};">'
                f'{prior.rate_move_p75*100:+.1f}%</strong> · '
                f'renewal cadence {int(prior.renewal_prob_12mo*100)}% / '
                f'12mo'
                f'</div>'
            )
    return (
        f'<div class="ps-payer-card" style="--tone:{tone};">'
        f'<div class="ps-payer-head">'
        f'<div class="ps-payer-name">'
        f'{html.escape(row.payer_name)}</div>'
        f'<div class="ps-payer-share">'
        f'{row.share_of_npr*100:.0f}%</div>'
        f'</div>'
        f'<div class="ps-payer-meta">'
        f'{html.escape(cat_label or "Unclassified")} · '
        f'${row.npr_attributed_usd/1e6:,.1f}M NPR · '
        f'leverage {int(row.negotiating_leverage*100)}/100 · '
        f'churn {int(row.churn_prob*100)}% · '
        f'renewal: {html.escape(renewal)}'
        f'</div>'
        + prior_context
        + f'<div class="ps-payer-stats">'
        f'<div><div class="ps-payer-stat">Cum rate move · med</div>'
        f'<div class="ps-payer-stat-val" style="color:{rate_color};">'
        f'{row.median_rate_move*100:+.2f}%</div></div>'
        f'<div><div class="ps-payer-stat">Cum rate move · P10 (tail)</div>'
        f'<div class="ps-payer-stat-val" style="color:{tail_color};">'
        f'{row.p10_rate_move*100:+.2f}%</div></div>'
        f'<div><div class="ps-payer-stat">Cum rate move · P90 (upside)</div>'
        f'<div class="ps-payer-stat-val" style="color:{P["positive"]};">'
        f'{row.p90_rate_move*100:+.2f}%</div></div>'
        f'<div><div class="ps-payer-stat">NPR $ · median</div>'
        f'<div class="ps-payer-stat-val" style="color:{tone};">'
        f'${row.median_npr_delta_usd/1e6:+,.2f}M</div></div>'
        f'<div><div class="ps-payer-stat">NPR $ · P10</div>'
        f'<div class="ps-payer-stat-val" '
        f'style="color:{P["negative"]};">'
        f'${row.p10_npr_delta_usd/1e6:+,.2f}M</div></div>'
        f'</div>'
        f'<div class="ps-payer-narrative">'
        f'{html.escape(row.narrative)}</div>'
        f'</div>'
    )


def _payer_table(report: PayerStressReport) -> str:
    headers = [
        "Payer", "Category", "Share", "NPR Attr",
        "Median Rate Δ", "P10 Rate Δ",
        "Median $Δ", "P10 $Δ",
        "Leverage", "Churn%",
    ]
    rows = []
    sort_keys = []

    def _colored(text: str, color: str) -> str:
        return (
            f'<span style="color:{color};font-weight:700;">'
            f'{html.escape(text)}</span>'
        )

    for r in report.per_payer:
        rate_color = (
            P["negative"] if r.median_rate_move < 0
            else P["positive"] if r.median_rate_move > 0.02
            else P["text_dim"]
        )
        tail_color = (
            P["negative"] if r.p10_rate_move < -0.05
            else P["warning"] if r.p10_rate_move < 0
            else P["positive"]
        )
        delta_color = (
            P["negative"] if r.median_npr_delta_usd < 0
            else P["positive"]
        )
        rows.append([
            html.escape(r.payer_name),
            (r.category or "").replace("_", " ").title(),
            f"{r.share_of_npr*100:.0f}%",
            f"${r.npr_attributed_usd/1e6:,.1f}M",
            _colored(f"{r.median_rate_move*100:+.2f}%", rate_color),
            _colored(f"{r.p10_rate_move*100:+.2f}%", tail_color),
            _colored(
                f"${r.median_npr_delta_usd/1e6:+,.2f}M",
                delta_color,
            ),
            _colored(
                f"${r.p10_npr_delta_usd/1e6:+,.2f}M",
                P["negative"],
            ),
            f"{int(r.negotiating_leverage*100)}",
            f"{int(r.churn_prob*100)}%",
        ])
        sort_keys.append([
            r.payer_name, r.category or "", r.share_of_npr,
            r.npr_attributed_usd, r.median_rate_move,
            r.p10_rate_move, r.median_npr_delta_usd,
            r.p10_npr_delta_usd, r.negotiating_leverage,
            r.churn_prob,
        ])
    return sortable_table(
        headers, rows, sort_keys=sort_keys,
        name="payer_stress_detail",
        caption=(
            "Sortable by any column · each row one payer · "
            "rate moves shown as cumulative 5-year · CSV export wired"
        ),
    )


# ────────────────────────────────────────────────────────────────────
# Landing form
# ────────────────────────────────────────────────────────────────────

def _default_mix_text() -> str:
    return "\n".join(
        f"{e.payer_name}, {e.share_of_npr*100:.0f}%"
        + (f", {e.contract_renewal_date}"
           if e.contract_renewal_date and
           e.contract_renewal_date != "annual" else "")
        for e in default_hospital_mix()
    )


def _landing(qs: Optional[Dict[str, List[str]]] = None) -> str:
    default = _default_mix_text()
    form = f"""
<form method="get" action="/diligence/payer-stress" class="ps-wrap">
  <div class="ps-panel">
    <div class="ps-section-label" style="margin-top:0;">
      Paste target payer mix</div>
    <div style="font-size:12px;color:{P["text_dim"]};line-height:1.6;
                margin-bottom:12px;max-width:840px;">
      One line per payer. Format: <code>name, share%</code> or
      <code>name, share%, renewal_iso_date</code>. Shares may be
      percentages (34%) or fractions (0.34). Supported payer
      names: UnitedHealthcare, Anthem, Aetna, Cigna, Humana,
      BCBS-[state], Kaiser, Medicare FFS, Medicare Advantage,
      Medicaid FFS, Medicaid managed, Centene, Molina, TRICARE,
      Workers Comp, Self-pay — plus free-text (falls back to
      neutral prior).
    </div>
    <div class="ps-form-field" style="margin-bottom:16px;">
      <label>Payer mix</label>
      <textarea name="mix">{html.escape(default)}</textarea>
    </div>
    <div class="ps-form-grid">
      <div class="ps-form-field"><label>Target name</label>
        <input name="target_name" value="Meadowbrook Regional"/></div>
      <div class="ps-form-field"><label>Total NPR (USD)</label>
        <input name="total_npr_usd" value="450000000"/></div>
      <div class="ps-form-field"><label>Total EBITDA (USD)</label>
        <input name="total_ebitda_usd" value="67500000"/></div>
      <div class="ps-form-field"><label>Horizon (years)</label>
        <input name="horizon_years" value="5"/></div>
      <div class="ps-form-field"><label>Simulation paths</label>
        <input name="n_paths" value="500"/></div>
      <div class="ps-form-field"><label>EBITDA pass-through (0-1)</label>
        <input name="ebitda_pass_through" value="0.70"/></div>
    </div>
    <button class="ps-form-submit" type="submit">
      Run payer stress</button>
  </div>
</form>
"""
    body = (
        _scoped_styles()
        + '<div class="ps-wrap">'
        + deal_context_bar(qs or {}, active_surface="payer")
        + '<div style="padding:22px 0 16px 0;">'
        + '<div class="ps-eyebrow">Payer Mix Stress Lab</div>'
        + '<div class="ps-h1">How fragile is your payer mix?</div>'
        + f'<div class="ps-callout">Stress-tests the target\'s '
        + 'commercial + government payer portfolio against empirical '
        + 'rate-movement priors for 19 major US payers. Produces '
        + 'per-payer rate shock distributions, aggregate NPR impact '
        + 'cone across the hold, concentration penalty, and a '
        + 'cumulative EBITDA-at-risk headline. Data: HFMA / MGMA / '
        + 'AHA sector surveys + public-comp 10-K payer-rate '
        + 'commentary. Refresh priors quarterly.</div>'
        + '</div>'
        + form
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Payer Stress Lab",
        subtitle="Payer mix × rate-movement priors × concentration amp",
    )


# ────────────────────────────────────────────────────────────────────
# Parse bridge-like textarea input
# ────────────────────────────────────────────────────────────────────

def _parse_mix_text(text: str) -> List[PayerMixEntry]:
    """Parse 'name, share%, date' lines into PayerMixEntry records."""
    out: List[PayerMixEntry] = []
    for raw in (text or "").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        name = parts[0].strip().strip('"').strip("'")
        share_raw = parts[1].strip().rstrip("%")
        try:
            share = float(share_raw)
            if share > 1.5:
                share = share / 100.0
        except ValueError:
            continue
        renewal = parts[2].strip() if len(parts) > 2 else None
        if renewal and renewal.lower() in ("", "-", "none"):
            renewal = None
        out.append(PayerMixEntry(
            payer_name=name,
            share_of_npr=max(0.0, min(1.0, share)),
            contract_renewal_date=renewal,
        ))
    return out


# ────────────────────────────────────────────────────────────────────
# Verdict card + composed blocks
# ────────────────────────────────────────────────────────────────────

def _verdict_card(report: PayerStressReport) -> str:
    verdict = report.verdict.value
    top1_chip = benchmark_chip(
        value=report.top_1_share * 100,
        peer_low=15, peer_high=30, peer_median=22,
        higher_is_better=False,
        format_spec=".0f", suffix="%",
        label="Top-1 payer share",
        peer_label="healthy diversification band",
    )
    risk_val = provenance(
        f"{report.risk_score:.0f}",
        source="Payer stress risk score",
        formula=(
            "EBITDA-at-risk % × 400 + max(0, top_1-0.20) × 150 "
            "+ (HHI/10000) × 20, clamped 0-100"
        ),
        detail=(
            "Higher = more fragile. Combines dollar tail risk with "
            "payer-mix concentration."
        ),
    )
    plain_map = {
        "PASS": ("Payer mix clears stress — concentration is "
                 "balanced and tail-risk is limited. Proceed at "
                 "standard bid discipline.", "good"),
        "CAUTION": ("Top payer share is elevated. Diligence "
                    "should include a term-sheet review of the "
                    "dominant payer contract for rate-adjustment "
                    "language.", "warn"),
        "WARNING": ("Material concentration + tail risk. "
                    "Negotiate either an earn-out structured on "
                    "payer-mix retention or a price reduction "
                    "equal to the P10 EBITDA drag.", "warn"),
        "FAIL": ("Payer mix is structurally fragile. Either the "
                 "Top-1 share exceeds 40% or the P10 EBITDA drag "
                 "is >10% of run-rate — both are IC-level red "
                 "flags. Partners should walk or require a "
                 "material earn-out.", "bad"),
    }
    plain, tone = plain_map.get(verdict, plain_map["CAUTION"])
    return (
        f'<div class="ps-verdict-card ps-verdict-{verdict}">'
        f'<div class="ps-verdict-badge">{verdict}</div>'
        f'<div class="ps-verdict-headline">'
        f'{html.escape(report.headline)}</div>'
        f'<div class="ps-verdict-rationale">'
        f'{html.escape(report.rationale)}</div>'
        + interpret_callout("Partner action:", plain, tone=tone)
        + f'<div style="margin-top:16px;">{top1_chip}</div>'
        + f'<div class="ps-kpi-grid">'
        f'  <div><div class="ps-kpi__label">Risk Score</div>'
        f'       <div class="ps-kpi__val">{risk_val}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">0-100 · lower = safer</div></div>'
        f'  <div><div class="ps-kpi__label">Top-1 Share</div>'
        f'       <div class="ps-kpi__val '
        f'{"neg" if report.top_1_share > 0.30 else ""}">'
        f'{report.top_1_share*100:.0f}%</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">flag at &gt;30%</div></div>'
        f'  <div><div class="ps-kpi__label">Top-3 Share</div>'
        f'       <div class="ps-kpi__val">'
        f'{report.top_3_share*100:.0f}%</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">flag at &gt;70%</div></div>'
        f'  <div><div class="ps-kpi__label">HHI</div>'
        f'       <div class="ps-kpi__val">'
        f'{report.hhi_index:.0f}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">&gt;2500 = concentrated</div></div>'
        f'  <div><div class="ps-kpi__label">Conc. Amplifier</div>'
        f'       <div class="ps-kpi__val">'
        f'{report.concentration_amplifier:.2f}×</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">volatility multiplier</div></div>'
        f'  <div><div class="ps-kpi__label">P10 EBITDA Impact</div>'
        f'       <div class="ps-kpi__val neg">'
        f'${report.p10_cumulative_ebitda_impact_usd/1e6:+,.1f}M</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">cumulative {report.horizon_years}-yr</div></div>'
        f'</div>'
        f'</div>'
    )


def _yearly_table(years: List[YearlyNPRImpact]) -> str:
    rows = []
    for y in years:
        p10_cls = "neg" if y.p10_npr_delta_usd < 0 else ""
        p50_cls = (
            "pos" if y.p50_npr_delta_usd > 0
            else "neg" if y.p50_npr_delta_usd < 0 else ""
        )
        rows.append(
            f'<tr style="border-bottom:1px solid {P["border"]};">'
            f'<td style="padding:6px 10px;font-family:monospace;">'
            f'Y{y.year}</td>'
            f'<td style="padding:6px 10px;font-family:monospace;'
            f'color:{P["negative"]};">'
            f'${y.p10_npr_delta_usd/1e6:+,.2f}M</td>'
            f'<td style="padding:6px 10px;font-family:monospace;'
            f'color:{P["text"]};">'
            f'${y.p50_npr_delta_usd/1e6:+,.2f}M</td>'
            f'<td style="padding:6px 10px;font-family:monospace;'
            f'color:{P["positive"]};">'
            f'${y.p90_npr_delta_usd/1e6:+,.2f}M</td>'
            f'<td style="padding:6px 10px;font-family:monospace;">'
            f'${y.median_ebitda_impact_usd/1e6:+,.2f}M</td>'
            f'<td style="padding:6px 10px;font-family:monospace;'
            f'color:{P["negative"]};">'
            f'${y.p10_ebitda_impact_usd/1e6:+,.2f}M</td>'
            f'</tr>'
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-size:12.5px;color:{P["text_dim"]};">'
        f'<thead><tr style="color:{P["text_faint"]};font-size:10px;'
        f'letter-spacing:1.2px;text-transform:uppercase;'
        f'font-weight:700;">'
        f'<th style="padding:6px 10px;text-align:left;'
        f'border-bottom:2px solid {P["border"]};">Year</th>'
        f'<th style="padding:6px 10px;text-align:left;'
        f'border-bottom:2px solid {P["border"]};">P10 NPR Δ</th>'
        f'<th style="padding:6px 10px;text-align:left;'
        f'border-bottom:2px solid {P["border"]};">P50 NPR Δ</th>'
        f'<th style="padding:6px 10px;text-align:left;'
        f'border-bottom:2px solid {P["border"]};">P90 NPR Δ</th>'
        f'<th style="padding:6px 10px;text-align:left;'
        f'border-bottom:2px solid {P["border"]};">Median EBITDA Δ</th>'
        f'<th style="padding:6px 10px;text-align:left;'
        f'border-bottom:2px solid {P["border"]};">P10 EBITDA Δ</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def render_payer_stress_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}
    mix_text = (qs.get("mix") or [""])[0].strip()
    if not mix_text:
        return _landing(qs)

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

    mix = _parse_mix_text(mix_text)
    if not mix:
        return chartis_shell(
            _scoped_styles()
            + f'<div class="ps-wrap" style="padding:28px;">'
            + f'<div class="ps-eyebrow">Payer Stress</div>'
            + f'<div class="ps-h1" style="color:{P["negative"]};">'
            + 'Could not parse any payer lines.</div>'
            + f'<div class="ps-callout">Expected format: '
            + '<code>UnitedHealthcare, 34%</code> — one line per '
            + 'payer.</div>'
            + f'<div style="margin-top:18px;">'
            + f'<a href="/diligence/payer-stress" '
            + f'style="color:{P["accent"]};">← Back</a></div></div>',
            "Payer Stress",
        )

    target_name = first("target_name") or "Target"
    total_npr = fnum("total_npr_usd", 450_000_000) or 450_000_000
    total_ebitda = fnum("total_ebitda_usd", 67_500_000)
    horizon = max(1, min(10, fint("horizon_years", 5)))
    n_paths = max(100, min(2000, fint("n_paths", 500)))
    pass_through = max(0.1, min(1.0,
        fnum("ebitda_pass_through", 0.70) or 0.70))

    report = run_payer_stress(
        target_name=target_name,
        mix=mix,
        total_npr_usd=total_npr,
        total_ebitda_usd=total_ebitda,
        horizon_years=horizon,
        n_paths=n_paths,
        ebitda_pass_through=pass_through,
    )

    # Chart plain-English read
    worst_tail = min(
        report.per_payer, key=lambda r: r.p10_rate_move,
    ) if report.per_payer else None
    chart_plain = ""
    if worst_tail and worst_tail.p10_rate_move < -0.05:
        chart_plain = (
            f"The worst-case (P10) rate tail is "
            f"<strong style=\"color:{P['negative']};\">"
            f"{worst_tail.p10_rate_move*100:+.1f}% on "
            f"{html.escape(worst_tail.payer_name)}</strong> "
            f"(share {worst_tail.share_of_npr*100:.0f}%), which alone "
            f"removes "
            f"<strong>${abs(worst_tail.p10_npr_delta_usd)/1e6:,.1f}M</strong> "
            f"of NPR in the downside case. Factor this into the "
            f"P10 EBITDA floor before signing."
        )
    else:
        chart_plain = (
            f"No single payer produces an extreme tail-risk rate "
            f"cut across the simulated paths. The cone is driven "
            f"primarily by diversified year-over-year drift rather "
            f"than single-payer shock."
        )

    hero = (
        f'<div style="padding:22px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="ps-eyebrow">Payer Mix Stress Lab</div>'
        f'<div class="ps-h1">{html.escape(target_name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'margin-top:4px;">'
        f'{len(mix)} payers · {report.n_paths} simulated paths · '
        f'{horizon}-year horizon · '
        f'${total_npr/1e6:,.0f}M total NPR'
        + (f' · {report.unclassified_share*100:.0f}% unclassified'
           if report.unclassified_share > 0.05 else '')
        + f'</div>'
        f'{_verdict_card(report)}'
        f'</div>'
    )

    # Mix visualization — donut + legend
    mix_panel = (
        f'<div class="ps-panel">'
        f'<div class="ps-section-label" style="margin-top:0;">'
        f'Payer mix · concentration snapshot</div>'
        f'<div style="display:flex;gap:24px;align-items:center;'
        f'flex-wrap:wrap;">'
        f'<div>{_mix_donut_svg(report.per_payer)}</div>'
        f'<div style="flex:1 1 260px;min-width:260px;">'
        f'{_legend(report.per_payer)}</div>'
        f'</div>'
        f'<div class="ps-callout">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'Donut shows each payer\'s share of NPR; center shows the '
        f'Top-1 concentration (color: <span style="color:{P["positive"]};'
        f'">&lt;25% green</span> · <span style="color:{P["warning"]};'
        f'">25-40% amber</span> · <span style="color:{P["negative"]};'
        f'">&gt;40% red</span>). HHI above 2500 = concentrated. '
        f'Concentration amplifier multiplies the aggregate '
        f'NPR volatility.'
        f'</div>'
        f'</div>'
    )

    cone_panel = (
        f'<div class="ps-panel">'
        f'<div class="ps-section-label" style="margin-top:0;">'
        f'Aggregate NPR impact · P10/P50/P90 cone</div>'
        f'{_yearly_cone_chart(report.yearly_impact)}'
        + interpret_callout("Plain-English read:", chart_plain)
        + f'<div class="ps-callout">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'Shaded band is the P10-P90 spread of cumulative NPR '
        f'dollar impact in each year; solid line is P50. '
        f'Values above zero = rate tailwind; below = compression. '
        f'The partner-critical reading is the P10 — the downside '
        f'tail that should be absorbed into the Deal MC '
        f'base-case before signing.'
        f'</div>'
        f'<div style="margin-top:10px;">{_yearly_table(report.yearly_impact)}</div>'
        f'</div>'
    )

    cards_panel = (
        f'<div class="ps-section-label">'
        f'Per-payer stress · ranked by NPR share</div>'
        + "".join(_payer_card(p) for p in report.per_payer)
    )

    table_panel = (
        f'<div class="ps-panel">'
        f'<div class="ps-section-label" style="margin-top:0;">'
        f'Sortable detail · CSV-exportable</div>'
        f'{_payer_table(report)}'
        f'</div>'
    )

    cross_link = (
        f'<div class="ps-panel">'
        f'<div class="ps-section-label" style="margin-top:0;">'
        f'Cross-reference</div>'
        f'<div style="font-size:13px;color:{P["text_dim"]};'
        f'line-height:1.7;">'
        f'The P10 EBITDA drag should subtract from '
        f'<a href="/diligence/deal-mc" '
        f'style="color:{P["accent"]};">→ Deal MC</a> base case · '
        f'feed the <a href="/diligence/bridge-audit" '
        f'style="color:{P["accent"]};">→ Bridge Audit</a> '
        f'payer-repricing lever · appear as evidence in the '
        f'<a href="/diligence/bear-case" '
        f'style="color:{P["accent"]};">→ Bear Case</a> · and '
        f'stress-test the '
        f'<a href="/diligence/covenant-stress" '
        f'style="color:{P["accent"]};">→ Covenant Stress Lab</a> '
        f'DSCR numerator.'
        f'</div></div>'
    )

    body = (
        _scoped_styles()
        + '<div class="ps-wrap">'
        + deal_context_bar(qs, active_surface="payer")
        + hero
        + mix_panel
        + cone_panel
        + cards_panel
        + table_panel
        + cross_link
        + export_json_panel(
            '<div class="ps-section-label" style="margin-top:22px;">'
            'JSON export — full payer stress report</div>',
            payload=report.to_dict(),
            name=f"payer_stress_{target_name.replace(' ', '_')}",
        )
        + bookmark_hint()
        + '</div>'
    )
    return chartis_shell(
        body, f"Payer Stress — {target_name}",
        subtitle=(
            f"{report.verdict.value} · "
            f"P10 impact "
            f"${report.p10_cumulative_ebitda_impact_usd/1e6:+,.1f}M"
        ),
    )
