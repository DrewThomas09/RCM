"""Exit Timing + Buyer-Type Fit page at /diligence/exit-timing.

Visualizations partners can't get anywhere else:
    - IRR / MOIC / proceeds curve across years 2-7
    - Buyer-fit radar (Strategic / PE Secondary / IPO / Sponsor Hold)
    - Per-buyer expected-multiple + close-certainty grid
    - Recommended (year, buyer) combo with partner-readable rationale
"""
from __future__ import annotations

import html
import math
from typing import Any, Dict, List, Optional

from ..diligence.exit_timing import (
    BuyerFitScore, BuyerType, ExitCurvePoint,
    ExitRecommendation, ExitTimingReport,
    analyze_exit_timing,
)
from ._chartis_kit import P, chartis_shell
from .power_ui import (
    bookmark_hint, deal_context_bar, export_json_panel, provenance,
)


def _scoped_styles() -> str:
    css = """
.et-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.et-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.et-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.et-callout{{background:{pa};padding:12px 16px;
border-left:3px solid {ac};border-radius:0 3px 3px 0;
font-size:12px;color:{td};line-height:1.65;max-width:880px;margin-top:12px;}}
.et-callout.rec{{border-left-color:{po};color:{tx};font-size:13px;
line-height:1.6;}}
.et-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.et-rec-card{{background:{pn};border:1px solid {po};border-radius:4px;
padding:18px 22px;margin-top:14px;position:relative;overflow:hidden;}}
.et-rec-card::before{{content:"";position:absolute;top:0;left:0;right:0;
height:3px;background:linear-gradient(90deg,{po},{ac});}}
.et-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
gap:14px;margin-top:14px;}}
.et-kpi__label{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
color:{tf};font-weight:600;margin-bottom:3px;}}
.et-kpi__val{{font-size:24px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;}}
.et-panel{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 20px;margin-bottom:16px;}}
.et-buyer-card{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 18px;margin-bottom:12px;
transition:border-color 140ms ease, box-shadow 140ms ease;}}
.et-buyer-card:hover{{border-color:{tf};
box-shadow:0 6px 16px rgba(0,0,0,0.3);}}
.et-buyer-card__head{{display:flex;justify-content:space-between;
align-items:baseline;gap:12px;flex-wrap:wrap;}}
.et-buyer-card__name{{font-size:15px;color:{tx};font-weight:600;}}
.et-buyer-card__fit{{font-size:28px;line-height:1;
font-family:"JetBrains Mono",monospace;font-weight:700;
font-variant-numeric:tabular-nums;}}
.et-buyer-stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));
gap:12px;margin-top:10px;}}
.et-buyer-stat__label{{font-size:9px;letter-spacing:1.2px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.et-buyer-stat__val{{font-size:14px;color:{tx};font-weight:600;
font-family:"JetBrains Mono",monospace;}}
.et-driver-chip{{display:inline-block;padding:3px 9px;margin:3px 4px 3px 0;
border-radius:3px;font-size:10.5px;}}
.et-driver-chip.pos{{color:{po};border:1px solid {po};}}
.et-driver-chip.neg{{color:{ne};border:1px solid {ne};}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# SVG visualizations
# ────────────────────────────────────────────────────────────────────

def _curve_svg(
    curve: List[ExitCurvePoint],
    width: int = 720, height: int = 280,
) -> str:
    """IRR and MOIC overlay chart across candidate years."""
    if not curve:
        return ""
    pad_l, pad_r, pad_t, pad_b = 56, 60, 28, 42
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)

    years = [p.year for p in curve]
    irrs = [p.irr for p in curve]
    moics = [p.moic for p in curve]
    y_min = min(years); y_max = max(years)
    irr_max = max(irrs) * 1.15 if max(irrs) > 0 else 0.3
    moic_max = max(moics) * 1.15 if max(moics) > 0 else 3.0
    if irr_max <= 0:
        irr_max = 0.3

    def x(v):
        return pad_l + (v - y_min) / max(0.001, y_max - y_min) * inner_w

    def y_irr(v):
        return pad_t + inner_h - (v / irr_max) * inner_h

    def y_moic(v):
        return pad_t + inner_h - (v / moic_max) * inner_h

    # Grid lines
    grid = []
    for i in range(4):
        t = i / 3
        y_pix = pad_t + t * inner_h
        grid.append(
            f'<line x1="{pad_l}" y1="{y_pix:.1f}" '
            f'x2="{pad_l + inner_w}" y2="{y_pix:.1f}" '
            f'stroke="{P["border_dim"]}" stroke-width="1" />'
        )
        # Left (IRR) ticks
        irr_v = irr_max * (1 - t)
        grid.append(
            f'<text x="{pad_l - 6}" y="{y_pix + 3:.1f}" '
            f'text-anchor="end" font-size="9" '
            f'fill="{P["text_faint"]}" '
            f'font-family="JetBrains Mono, monospace">'
            f'{irr_v*100:.0f}%</text>'
        )
        # Right (MOIC) ticks
        moic_v = moic_max * (1 - t)
        grid.append(
            f'<text x="{pad_l + inner_w + 6}" y="{y_pix + 3:.1f}" '
            f'text-anchor="start" font-size="9" '
            f'fill="{P["text_faint"]}" '
            f'font-family="JetBrains Mono, monospace">'
            f'{moic_v:.1f}x</text>'
        )

    # IRR line + points
    irr_path = " ".join(
        f"{x(p.year):.1f},{y_irr(p.irr):.1f}" for p in curve
    )
    irr_line = (
        f'<polyline fill="none" stroke="{P["accent"]}" '
        f'stroke-width="2" points="{irr_path}" />'
    )
    irr_dots = "".join(
        f'<circle cx="{x(p.year):.1f}" cy="{y_irr(p.irr):.1f}" '
        f'r="4" fill="{P["accent"]}">'
        f'<title>Year {p.year}: IRR {p.irr*100:.1f}% · MOIC {p.moic:.2f}x · '
        f'proceeds ${p.equity_proceeds_usd:,.0f}</title></circle>'
        for p in curve
    )

    # MOIC line + points (dashed, secondary)
    moic_path = " ".join(
        f"{x(p.year):.1f},{y_moic(p.moic):.1f}" for p in curve
    )
    moic_line = (
        f'<polyline fill="none" stroke="{P["warning"]}" '
        f'stroke-width="2" stroke-dasharray="4,3" points="{moic_path}" />'
    )
    moic_dots = "".join(
        f'<circle cx="{x(p.year):.1f}" cy="{y_moic(p.moic):.1f}" '
        f'r="3.5" fill="{P["warning"]}" opacity="0.8">'
        f'<title>Year {p.year}: MOIC {p.moic:.2f}x</title></circle>'
        for p in curve
    )

    # X-axis year labels
    x_labels = "".join(
        f'<text x="{x(yr):.1f}" y="{pad_t + inner_h + 16:.0f}" '
        f'text-anchor="middle" font-size="10" '
        f'fill="{P["text_faint"]}" '
        f'font-family="JetBrains Mono, monospace">Y{yr}</text>'
        for yr in years
    )

    # Legend
    legend = (
        f'<g transform="translate({pad_l + 10},{pad_t - 14})">'
        f'<line x1="0" y1="0" x2="20" y2="0" stroke="{P["accent"]}" '
        f'stroke-width="2" />'
        f'<text x="26" y="3" font-size="10" fill="{P["text_dim"]}">IRR (left)</text>'
        f'<line x1="110" y1="0" x2="130" y2="0" stroke="{P["warning"]}" '
        f'stroke-width="2" stroke-dasharray="4,3" />'
        f'<text x="136" y="3" font-size="10" fill="{P["text_dim"]}">MOIC (right)</text>'
        f'</g>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;">'
        f'<text x="{pad_l}" y="16" font-size="10" '
        f'fill="{P["text_dim"]}" letter-spacing="1.5" '
        f'font-weight="700" font-family="Helvetica Neue, Arial, sans-serif">'
        f'IRR × MOIC BY EXIT YEAR</text>'
        f'{"".join(grid)}'
        f'{irr_line}{moic_line}'
        f'{irr_dots}{moic_dots}'
        f'{x_labels}'
        f'{legend}'
        f'</svg>'
    )


def _buyer_radar_svg(
    buyers: List[BuyerFitScore],
    width: int = 380, height: int = 380,
) -> str:
    """4-axis radar of buyer-type fit scores."""
    if not buyers:
        return ""
    cx, cy = width / 2, height / 2 + 10
    max_r = min(width, height) * 0.38
    n = len(buyers)

    # Concentric grid
    grid = []
    for pct in (0.25, 0.5, 0.75, 1.0):
        r = max_r * pct
        # Build polygon ring
        pts = []
        for i in range(n):
            angle = math.pi / 2 - (2 * math.pi * i / n)
            pts.append(
                f"{cx + r * math.cos(angle):.1f},"
                f"{cy - r * math.sin(angle):.1f}"
            )
        grid.append(
            f'<polygon fill="none" stroke="{P["border_dim"]}" '
            f'stroke-width="1" points="{" ".join(pts)}" />'
        )

    # Axis spokes + labels
    spokes = []
    labels = []
    for i, b in enumerate(buyers):
        angle = math.pi / 2 - (2 * math.pi * i / n)
        x_out = cx + max_r * math.cos(angle)
        y_out = cy - max_r * math.sin(angle)
        spokes.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x_out:.1f}" y2="{y_out:.1f}" '
            f'stroke="{P["border_dim"]}" stroke-width="1" />'
        )
        # Labels placed a bit outside the max-radius
        lx = cx + (max_r + 18) * math.cos(angle)
        ly = cy - (max_r + 18) * math.sin(angle)
        anchor = (
            "middle" if abs(math.cos(angle)) < 0.3
            else ("start" if math.cos(angle) > 0 else "end")
        )
        labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'font-size="10" fill="{P["text"]}" '
            f'font-family="Helvetica Neue, Arial, sans-serif" '
            f'font-weight="600">{html.escape(b.label.split()[0])}</text>'
            f'<text x="{lx:.1f}" y="{ly + 12:.1f}" text-anchor="{anchor}" '
            f'font-size="9" fill="{P["text_faint"]}" '
            f'font-family="JetBrains Mono, monospace">'
            f'{b.fit_score}/100</text>'
        )

    # Actual score polygon
    score_pts = []
    for i, b in enumerate(buyers):
        angle = math.pi / 2 - (2 * math.pi * i / n)
        r = max_r * (b.fit_score / 100.0)
        score_pts.append(
            f"{cx + r * math.cos(angle):.1f},"
            f"{cy - r * math.sin(angle):.1f}"
        )
    score_poly = (
        f'<polygon fill="{P["accent"]}" fill-opacity="0.25" '
        f'stroke="{P["accent"]}" stroke-width="2" '
        f'points="{" ".join(score_pts)}" />'
    )
    # Score dots
    score_dots = ""
    for i, b in enumerate(buyers):
        angle = math.pi / 2 - (2 * math.pi * i / n)
        r = max_r * (b.fit_score / 100.0)
        score_dots += (
            f'<circle cx="{cx + r * math.cos(angle):.1f}" '
            f'cy="{cy - r * math.sin(angle):.1f}" r="3.5" '
            f'fill="{P["accent"]}">'
            f'<title>{html.escape(b.label)}: {b.fit_score}/100</title>'
            f'</circle>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;">'
        f'<text x="{width/2:.0f}" y="18" text-anchor="middle" '
        f'font-size="10" fill="{P["text_dim"]}" letter-spacing="1.5" '
        f'font-weight="700" font-family="Helvetica Neue, Arial, sans-serif">'
        f'BUYER-TYPE FIT</text>'
        f'{"".join(grid)}'
        f'{"".join(spokes)}'
        f'{score_poly}{score_dots}'
        f'{"".join(labels)}'
        f'</svg>'
    )


# ────────────────────────────────────────────────────────────────────
# Section renderers
# ────────────────────────────────────────────────────────────────────

def _recommendation_block(rec: Optional[ExitRecommendation]) -> str:
    if rec is None:
        return (
            f'<div class="et-callout">'
            f'Insufficient data to compute exit recommendation. Supply '
            f'equity + debt + year-by-year EBITDA median.</div>'
        )
    # MOIC color band: <1.5x red, 1.5-2.5x amber, 2.5x+ green
    moic_color = (
        P["negative"] if rec.expected_moic < 1.5
        else P["warning"] if rec.expected_moic < 2.5
        else P["positive"]
    )
    # IRR color band: <15% red, 15-25% amber, 25%+ green
    irr_color = (
        P["negative"] if rec.expected_irr < 0.15
        else P["warning"] if rec.expected_irr < 0.25
        else P["positive"]
    )

    year_num = provenance(
        f'Y{rec.exit_year}',
        source="ExitRecommendation.exit_year",
        formula="argmax(probability_weighted_irr) filtered to MOIC >= 1.5x",
        detail=(
            "Candidate years 2-7. Partners optimize IRR (not absolute "
            "$), so this year is the one that clears MOIC 1.5x and "
            "maximises IRR × close-certainty."
        ),
    )
    moic_num = provenance(
        f'{rec.expected_moic:.2f}x',
        source="ExitRecommendation.expected_moic",
        formula="terminal_EV / equity_check · adjusted for buyer multiple delta",
        detail=(
            "Expected MOIC at exit. Strategic buyer adds +1.2 turns to "
            "peer median; PE secondary subtracts 0.5 turns; IPO flat."
        ),
    )
    irr_num = provenance(
        f'{rec.expected_irr*100:.1f}%',
        source="ExitRecommendation.expected_irr",
        formula="MOIC^(1/year) - 1",
        detail=(
            "Annualized return. Peer benchmarks: 15% = base, 20% = "
            "strong, 25%+ = elite. PE funds quote IRR as their headline."
        ),
    )
    proceeds_num = provenance(
        f'${rec.probability_weighted_proceeds_usd/1e6:,.1f}M',
        source="equity_proceeds × close_certainty",
        formula="(terminal_EV - remaining_debt) × buyer.close_certainty",
        detail=(
            "Expected-value proceeds — adjusts for the probability "
            "the bid actually clears. Strategic 75% · PE secondary "
            "85% · IPO 55%."
        ),
    )

    return (
        f'<div class="et-rec-card">'
        f'<div class="et-eyebrow">Recommended exit path</div>'
        f'<div style="font-size:20px;color:{P["text"]};font-weight:600;'
        f'margin-top:4px;">{html.escape(rec.summary)}</div>'
        f'<div class="et-kpi-grid">'
        f'<div><div class="et-kpi__label">Year</div>'
        f'<div class="et-kpi__val" style="color:{P["text"]};">'
        f'{year_num}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">optimal hold</div></div>'
        f'<div><div class="et-kpi__label">Expected MOIC</div>'
        f'<div class="et-kpi__val" style="color:{moic_color};">'
        f'{moic_num}</div>'
        f'<div style="font-size:10px;color:{moic_color};margin-top:3px;">'
        f'{"below hurdle" if rec.expected_moic < 1.5 else "acceptable" if rec.expected_moic < 2.5 else "top quintile"}'
        f'</div></div>'
        f'<div><div class="et-kpi__label">Expected IRR</div>'
        f'<div class="et-kpi__val" style="color:{irr_color};">'
        f'{irr_num}</div>'
        f'<div style="font-size:10px;color:{irr_color};margin-top:3px;">'
        f'vs 15% peer base · 20% strong'
        f'</div></div>'
        f'<div><div class="et-kpi__label">Prob-weighted proceeds</div>'
        f'<div class="et-kpi__val" style="color:{P["text"]};">'
        f'{proceeds_num}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};margin-top:3px;">'
        f'expected $, hover for detail</div></div>'
        f'</div>'
        f'<div style="margin-top:14px;padding:10px 14px;'
        f'background:{P["panel_alt"]};border-left:2px solid '
        f'{P["accent"]};border-radius:0 3px 3px 0;font-size:12px;'
        f'color:{P["text_dim"]};line-height:1.6;max-width:880px;">'
        f'<strong style="color:{P["text"]};">Why this choice: </strong>'
        f'{html.escape(rec.rationale)}'
        f'</div>'
        f'</div>'
    )


def _score_band_legend() -> str:
    """Universal score-band legend — 0-40 red / 40-70 amber /
    70-100 green. Used on fit scores + any 0-100 metric."""
    return (
        f'<div style="display:flex;gap:10px;align-items:center;'
        f'flex-wrap:wrap;font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:.5px;margin-top:10px;">'
        f'<span>Score bands:</span>'
        f'<span style="color:{P["negative"]};font-weight:600;">'
        f'◆ 0-40 weak</span>'
        f'<span style="color:{P["warning"]};font-weight:600;">'
        f'◆ 40-70 acceptable</span>'
        f'<span style="color:{P["positive"]};font-weight:600;">'
        f'◆ 70-100 strong</span>'
        f'</div>'
    )


def _buyer_fit_cards(buyers: List[BuyerFitScore]) -> str:
    cards: List[str] = []
    for b in sorted(buyers, key=lambda x: x.fit_score, reverse=True):
        color = (
            P["positive"] if b.fit_score >= 70
            else P["warning"] if b.fit_score >= 50
            else P["negative"] if b.fit_score >= 30
            else P["text_faint"]
        )
        premium_str = (
            f'{b.expected_multiple_turns_delta:+.1f}x'
            if abs(b.expected_multiple_turns_delta) > 0.01
            else "flat"
        )
        favorable_chips = "".join(
            f'<span class="et-driver-chip pos">{html.escape(f)}</span>'
            for f in b.favorable_hits[:3]
        )
        unfavorable_chips = "".join(
            f'<span class="et-driver-chip neg">{html.escape(u)}</span>'
            for u in b.unfavorable_hits[:3]
        )
        cards.append(
            f'<div class="et-buyer-card" style="border-left:3px solid {color};">'
            f'<div class="et-buyer-card__head">'
            f'<div>'
            f'<div class="et-buyer-card__name">{html.escape(b.label)}</div>'
            f'<div style="font-size:11px;color:{P["text_faint"]};'
            f'margin-top:3px;">'
            f'{b.buyer_type.value.replace("_", " ")}</div>'
            f'</div>'
            f'<div class="et-buyer-card__fit" style="color:{color};">'
            f'{b.fit_score}<span style="font-size:12px;opacity:.6;"> / 100</span>'
            f'</div>'
            f'</div>'
            f'<div class="et-buyer-stats">'
            f'<div><div class="et-buyer-stat__label">Multiple delta</div>'
            f'<div class="et-buyer-stat__val">{premium_str}</div></div>'
            f'<div><div class="et-buyer-stat__label">Close certainty</div>'
            f'<div class="et-buyer-stat__val">{b.close_certainty*100:.0f}%</div></div>'
            f'<div><div class="et-buyer-stat__label">Time to close</div>'
            f'<div class="et-buyer-stat__val">{b.time_to_close_months:.0f} mo</div></div>'
            f'</div>'
            f'<div style="font-size:11.5px;color:{P["text_dim"]};'
            f'line-height:1.6;margin-top:10px;">'
            f'{html.escape(b.narrative)}</div>'
            + (f'<div style="margin-top:8px;"><span style="font-size:9px;'
               f'color:{P["text_faint"]};letter-spacing:1.2px;'
               f'text-transform:uppercase;font-weight:600;margin-right:4px;">'
               f'Favorable:</span>{favorable_chips}</div>' if favorable_chips else "")
            + (f'<div style="margin-top:6px;"><span style="font-size:9px;'
               f'color:{P["text_faint"]};letter-spacing:1.2px;'
               f'text-transform:uppercase;font-weight:600;margin-right:4px;">'
               f'Unfavorable:</span>{unfavorable_chips}</div>' if unfavorable_chips else "")
            + '</div>'
        )
    return "".join(cards)


def _curve_table_block(curve: List[ExitCurvePoint]) -> str:
    if not curve:
        return ""
    rows_html = []
    peak_irr = max((p.irr for p in curve), default=0.0)
    for p in curve:
        highlight = (
            f'background:{P["panel_alt"]};'
            if abs(p.irr - peak_irr) < 1e-9 else ""
        )
        rows_html.append(
            f'<tr style="{highlight}">'
            f'<td style="padding:6px 10px;color:{P["text"]};font-weight:600;">Y{p.year}</td>'
            f'<td style="padding:6px 10px;text-align:right;color:{P["text_dim"]};'
            f'font-family:\'JetBrains Mono\',monospace;">'
            f'${p.ebitda_median_usd/1e6:,.1f}M</td>'
            f'<td style="padding:6px 10px;text-align:right;color:{P["text_dim"]};'
            f'font-family:\'JetBrains Mono\',monospace;">'
            f'{p.exit_multiple_assumed:.1f}x</td>'
            f'<td style="padding:6px 10px;text-align:right;color:{P["text"]};'
            f'font-family:\'JetBrains Mono\',monospace;font-weight:600;">'
            f'{p.moic:.2f}x</td>'
            f'<td style="padding:6px 10px;text-align:right;color:{P["positive"]};'
            f'font-family:\'JetBrains Mono\',monospace;font-weight:600;">'
            f'{p.irr*100:.1f}%</td>'
            f'<td style="padding:6px 10px;text-align:right;color:{P["text_dim"]};'
            f'font-family:\'JetBrains Mono\',monospace;">'
            f'${p.equity_proceeds_usd/1e6:,.1f}M</td>'
            f'</tr>'
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:12px;'
        f'margin-top:14px;">'
        f'<thead><tr style="border-bottom:1px solid {P["border"]};">'
        f'<th style="padding:6px 10px;text-align:left;font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:1.3px;text-transform:uppercase;">Year</th>'
        f'<th style="padding:6px 10px;text-align:right;font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:1.3px;text-transform:uppercase;">EBITDA</th>'
        f'<th style="padding:6px 10px;text-align:right;font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:1.3px;text-transform:uppercase;">Multiple</th>'
        f'<th style="padding:6px 10px;text-align:right;font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:1.3px;text-transform:uppercase;">MOIC</th>'
        f'<th style="padding:6px 10px;text-align:right;font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:1.3px;text-transform:uppercase;">IRR</th>'
        f'<th style="padding:6px 10px;text-align:right;font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:1.3px;text-transform:uppercase;">Proceeds</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody></table>'
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def _landing() -> str:
    form = (
        f'<form method="GET" action="/diligence/exit-timing" '
        f'style="max-width:560px;background:{P["panel"]};'
        f'border:1px solid {P["border"]};border-radius:4px;'
        f'padding:20px;margin-bottom:20px;">'
        f'<div style="font-size:10px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:10px;">Inputs</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        f'<div><label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:2px;">Equity check ($)</label>'
        f'<input name="equity_check_usd" value="150000000" '
        f'style="width:100%;padding:5px 7px;background:{P["panel_alt"]};'
        f'color:{P["text"]};border:1px solid {P["border"]};'
        f'font-family:\'JetBrains Mono\',monospace;font-size:11px;"></div>'
        f'<div><label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:2px;">Debt Y0 ($)</label>'
        f'<input name="debt_year0_usd" value="200000000" '
        f'style="width:100%;padding:5px 7px;background:{P["panel_alt"]};'
        f'color:{P["text"]};border:1px solid {P["border"]};'
        f'font-family:\'JetBrains Mono\',monospace;font-size:11px;"></div>'
        f'<div><label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:2px;">Year-0 EBITDA ($)</label>'
        f'<input name="ebitda_year0_usd" value="35000000" '
        f'style="width:100%;padding:5px 7px;background:{P["panel_alt"]};'
        f'color:{P["text"]};border:1px solid {P["border"]};'
        f'font-family:\'JetBrains Mono\',monospace;font-size:11px;"></div>'
        f'<div><label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:2px;">Annual EBITDA growth</label>'
        f'<input name="ebitda_growth" value="0.06" '
        f'style="width:100%;padding:5px 7px;background:{P["panel_alt"]};'
        f'color:{P["text"]};border:1px solid {P["border"]};'
        f'font-family:\'JetBrains Mono\',monospace;font-size:11px;"></div>'
        f'<div><label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:2px;">Peer median multiple (x)</label>'
        f'<input name="peer_median_multiple" value="9.0" '
        f'style="width:100%;padding:5px 7px;background:{P["panel_alt"]};'
        f'color:{P["text"]};border:1px solid {P["border"]};'
        f'font-family:\'JetBrains Mono\',monospace;font-size:11px;"></div>'
        f'<div><label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.2px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:2px;">Sector sentiment</label>'
        f'<select name="sector_sentiment" style="width:100%;padding:5px 7px;'
        f'background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};font-family:inherit;font-size:11px;">'
        f'<option value="">—</option>'
        f'<option value="positive">Positive</option>'
        f'<option value="neutral" selected>Neutral</option>'
        f'<option value="mixed">Mixed</option>'
        f'<option value="negative">Negative</option>'
        f'</select></div>'
        f'</div>'
        f'<button type="submit" style="margin-top:14px;padding:8px 20px;'
        f'background:{P["accent"]};color:{P["panel"]};border:0;'
        f'font-size:10px;letter-spacing:1.5px;text-transform:uppercase;'
        f'font-weight:700;cursor:pointer;border-radius:3px;">'
        f'Compute exit path</button>'
        f'</form>'
    )
    body = (
        _scoped_styles()
        + '<div class="et-wrap">'
        + f'<div style="padding:24px 0 12px 0;">'
        + f'<div class="et-eyebrow">RCM Diligence</div>'
        + f'<div class="et-h1">Exit Timing + Buyer-Type Fit</div>'
        + f'</div>'
        + f'<div class="et-callout">'
        f'<strong style="color:{P["text"]};">What this shows: </strong>'
        f'Given a Deal MC scenario (equity + debt + EBITDA trajectory), '
        f'compute an IRR/MOIC curve across candidate exit years 2-7 '
        f'and score each buyer type (strategic / PE secondary / IPO / '
        f'sponsor-hold-extension) against the target profile. The '
        f'recommended exit combines the highest probability-weighted IRR '
        f'with the buyer type most likely to close.'
        f'</div>'
        + form
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Exit Timing",
        subtitle="When + to whom · predictive exit path",
    )


def render_exit_timing_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}

    def _first(k: str, default: str = "") -> str:
        return (qs.get(k) or [default])[0].strip()

    def _float(k: str, default: Optional[float] = None) -> Optional[float]:
        v = _first(k)
        if not v:
            return default
        try:
            return float(v)
        except ValueError:
            return default

    equity = _float("equity_check_usd")
    debt = _float("debt_year0_usd")
    eb0 = _float("ebitda_year0_usd")
    if not (equity and debt and eb0):
        return _landing()

    growth = _float("ebitda_growth", 0.06) or 0.06
    peer_median = _float("peer_median_multiple", 9.0)
    regulatory = _first("regulatory_verdict") or None
    sentiment = _first("sector_sentiment") or None
    commercial = _float("commercial_payer_share")
    mgmt_score_raw = _first("management_score")
    mgmt_score = int(float(mgmt_score_raw)) if mgmt_score_raw else None
    top_payer = _float("top_1_payer_share")

    # Compound EBITDA trajectory
    eb_by_year: List[float] = []
    for y in range(0, 9):
        eb_by_year.append(eb0 * (1.0 + growth) ** y)

    report = analyze_exit_timing(
        equity_check_usd=equity,
        debt_year0_usd=debt,
        ebitda_median_by_year=eb_by_year,
        peer_median_multiple=peer_median,
        regulatory_verdict=regulatory,
        commercial_payer_share=commercial,
        sector_sentiment=sentiment,
        management_score=mgmt_score,
        top_1_payer_share=top_payer,
    )

    target_name = _first("target_name") or "Target Deal"

    hero = (
        f'<div style="padding:22px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="et-eyebrow">Exit Timing + Buyer Fit</div>'
        f'<div class="et-h1">{html.escape(target_name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};margin-top:4px;">'
        f'{len(report.curve)} candidate exit years · '
        f'{len(report.buyer_fit)} buyer types scored · '
        f'{"sector " + sentiment if sentiment else "no sector sentiment"}'
        f'</div>'
        f'{_recommendation_block(report.recommendation)}'
        f'</div>'
    )

    # Derived interpretation of the curve — name the peak year +
    # what "every extra year" costs in IRR
    peak = report.peak_irr_point
    curve_narrative = ""
    if peak and len(report.curve) >= 2:
        # Delta between peak and the year immediately after
        after = next(
            (p for p in report.curve if p.year == peak.year + 1), None,
        )
        if after is not None:
            delta = (peak.irr - after.irr) * 100
            curve_narrative = (
                f'Peak IRR is year {peak.year} at {peak.irr*100:.1f}%. '
                f'Holding one additional year to Y{after.year} '
                f'{"costs" if delta > 0 else "gains"} '
                f'{abs(delta):.1f} pp of IRR while adding '
                f'{(after.moic - peak.moic):+.2f}x of MOIC. This is '
                f'the partner-facing time-vs-return tradeoff.'
            )
    curve_panel = (
        f'<div class="et-panel">'
        f'{_curve_svg(report.curve)}'
        f'<div style="margin-top:10px;padding:10px 14px;'
        f'background:{P["panel_alt"]};border-left:3px solid '
        f'{P["accent"]};border-radius:0 3px 3px 0;'
        f'font-size:12px;color:{P["text_dim"]};line-height:1.6;'
        f'max-width:880px;">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'X-axis is candidate exit year (hold length in years). '
        f'Blue solid line is <strong style="color:{P["accent"]};">IRR</strong> '
        f'(annualized return, left axis); amber dashed is '
        f'<strong style="color:{P["warning"]};">MOIC</strong> '
        f'(absolute multiple, right axis). The peak of the IRR curve '
        f'is the fund-optimal exit year — holding past it adds MOIC '
        f'but destroys IRR. Hover any point for the exact values.'
        + (f'<br/><br/><strong style="color:{P["text"]};">Implication: '
           f'</strong>{html.escape(curve_narrative)}'
           if curve_narrative else '')
        + f'</div>'
        f'{_curve_table_block(report.curve)}'
        f'</div>'
    )

    # Radar narrative — name the top fit + the worst fit
    sorted_fits = sorted(
        report.buyer_fit, key=lambda b: b.fit_score, reverse=True,
    )
    radar_narrative = ""
    if len(sorted_fits) >= 2:
        top = sorted_fits[0]
        bottom = sorted_fits[-1]
        radar_narrative = (
            f'<strong style="color:{P["text"]};">Top fit: </strong>'
            f'{html.escape(top.label)} at {top.fit_score}/100 · '
            f'<strong style="color:{P["text"]};">Lowest fit: </strong>'
            f'{html.escape(bottom.label)} at {bottom.fit_score}/100. '
            f'Partners should anchor the process on the top-fit channel '
            f'and only run a second process on the #2 if the top fit '
            f'fails to clear reserve.'
        )
    radar_panel = (
        f'<div class="et-panel" style="display:grid;'
        f'grid-template-columns:1fr 1fr;gap:18px;align-items:center;">'
        f'<div>{_buyer_radar_svg(report.buyer_fit)}</div>'
        f'<div style="font-size:12px;color:{P["text_dim"]};line-height:1.65;">'
        f'<div style="padding:10px 14px;background:{P["panel_alt"]};'
        f'border-left:3px solid {P["accent"]};border-radius:0 3px 3px 0;'
        f'margin-bottom:10px;">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'Each vertex is a buyer channel (strategic / PE secondary / '
        f'IPO / sponsor-hold). Outer ring is 100/100 fit. Filled '
        f'polygon area shows where the target scores across all four '
        f'channels — wider polygon = more optionality. '
        f'{radar_narrative}'
        f'</div>'
        f'{_score_band_legend()}'
        f'</div>'
        f'</div>'
    )

    body = (
        _scoped_styles()
        + '<div class="et-wrap">'
        + deal_context_bar(qs, active_surface="exit_timing")
        + export_json_panel(
            hero, payload=report.to_dict(),
            name="exit_timing_report",
        )
        + '<div class="et-section-label">'
          'IRR × MOIC curve — across candidate exit years'
        + '</div>'
        + curve_panel
        + '<div class="et-section-label">'
          'Buyer-type fit — which channel clears the bid'
        + '</div>'
        + radar_panel
        + '<div class="et-section-label">Per-buyer playbook</div>'
        + _buyer_fit_cards(report.buyer_fit)
        + '</div>'
        + bookmark_hint()
    )
    return chartis_shell(
        body, f"Exit Timing — {target_name}",
        subtitle="When + to whom · predictive exit path",
    )
