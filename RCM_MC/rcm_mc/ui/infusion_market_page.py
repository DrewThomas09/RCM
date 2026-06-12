"""National infusion-market scan — the page for
``infusion_state_attractiveness``. A state choropleth + ranked table that
answers "where else after Texas?" from real per-state data.
"""
from __future__ import annotations

import html
from typing import Any, Dict

from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
from .excel_mapping_page import _STATE_TILE


def _heat(frac: float) -> str:
    """Light → deep-teal sequential color for a 0–1 fraction."""
    frac = max(0.0, min(1.0, frac))
    c0, c1 = (0xE9, 0xF1, 0xF0), (0x12, 0x5E, 0x59)
    rgb = tuple(round(c0[i] + (c1[i] - c0[i]) * frac) for i in range(3))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

_NAVY = "#0b2341"
_TEAL = "#1F7A75"
_NEG = "#b5321e"
_DIM = "#465366"
_FAINT = "#7a8699"
_POS = "#0a8a5f"
_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")

_AXIS_LABEL = {
    "senior_base": "65+ base", "ma_steerage": "MA steerage",
    "no_con": "No CON", "density": "Density", "commercial": "Commercial",
}


def _choropleth(states, lo, hi) -> str:
    by_code = {s["code"]: s for s in states}
    rng = (hi - lo) or 1
    cell, gap, ncol, nrow = 9.0, 0.7, 11, 8
    tiles = ""
    for code, (r, c) in _STATE_TILE.items():
        s = by_code.get(code)
        if not s:
            continue
        x, y = c * cell, r * cell
        fill = _heat((s["score"] - lo) / rng)
        is_tx = code == "TX"
        stroke = _NEG if is_tx else "#fff"
        sw = 0.9 if is_tx else 0.4
        txt = "#fff" if (s["score"] - lo) / rng > 0.55 else "#1a2332"
        tiles += (
            f'<g><rect x="{x:.1f}" y="{y:.1f}" width="{cell-gap:.1f}" '
            f'height="{cell-gap:.1f}" rx="1.2" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}">'
            f'<title>{html.escape(s["name"])}: {s["score"]:.0f} '
            f'(#{s["rank"]})</title></rect>'
            f'<text x="{x+(cell-gap)/2:.1f}" y="{y+3.4:.1f}" '
            f'text-anchor="middle" font-size="2.7" font-weight="700" '
            f'fill="{txt}">{code}</text>'
            f'<text x="{x+(cell-gap)/2:.1f}" y="{y+6.4:.1f}" '
            f'text-anchor="middle" font-size="2.7" fill="{txt}">'
            f'{s["score"]:.0f}</text></g>')
    return (
        f'<svg viewBox="-1 -1 {ncol*cell+1:.0f} {nrow*cell+1:.0f}" '
        f'width="100%" height="300" role="img" '
        f'aria-label="State infusion attractiveness" '
        f'style="max-width:560px;">{tiles}</svg>')


def render_infusion_market_page(qs: "Dict[str, Any] | None" = None) -> str:
    from ..diligence.infusion_market import infusion_state_attractiveness
    a = infusion_state_attractiveness()
    states = a["states"]
    scores = [s["score"] for s in states]
    lo, hi = min(scores), max(scores)
    tx = a["texas"]
    axes = list(_AXIS_LABEL)

    def _row(s, hl=False):
        bg = "background:#fbf3ef;" if hl else ""
        tag = (' <span style="color:%s;font-weight:700;font-size:9px;">TX'
               '</span>' % _NEG) if s["code"] == "TX" else ""
        con = ('<span style="color:%s;font-weight:700;">✓</span>' % _POS
               if s["no_con"] else '<span style="color:%s;">—</span>'
               % _FAINT)
        cells = "".join(
            f'<td class="num" style="padding:3px 7px;text-align:right;'
            f'color:{_DIM};">{s["axes"][ax]*100:.0f}</td>' for ax in axes)
        return (
            f'<tr style="{bg}border-bottom:1px solid #e8e1d0;">'
            f'<td class="num" style="padding:3px 8px;color:{_FAINT};">'
            f'#{s["rank"]}</td>'
            f'<td style="padding:3px 8px;font-weight:600;">'
            f'{html.escape(s["name"])}{tag}</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'font-weight:700;color:{_NAVY};font-family:{_SERIF};">'
            f'{s["score"]:.0f}</td>'
            f'<td style="padding:3px 8px;text-align:center;">{con}</td>'
            f'<td class="num" style="padding:3px 7px;text-align:right;">'
            f'{s["seniors"]/1e6:.1f}M</td>'
            f'<td class="num" style="padding:3px 7px;text-align:right;">'
            f'{s["ma_penetration"]*100:.0f}%</td>{cells}</tr>')
    body_rows = "".join(_row(s) for s in states[:10])
    if tx["rank"] > 10:
        body_rows += ('<tr><td colspan="11" style="text-align:center;'
                      f'color:{_FAINT};font-size:10px;padding:2px;">⋯</td></tr>'
                      + _row(tx, hl=True))
    body_rows += ('<tr><td colspan="11" style="text-align:center;'
                  f'color:{_FAINT};font-size:10px;padding:2px;">⋯</td></tr>'
                  + "".join(_row(s) for s in states[-5:]))
    axis_head = "".join(
        f'<th style="text-align:right;padding:3px 7px;">'
        f'{html.escape(_AXIS_LABEL[ax])}</th>' for ax in axes)
    table = (
        f'<table style="width:100%;border-collapse:collapse;font-size:11.5px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;color:{_FAINT};">'
        f'<th style="text-align:left;padding:3px 8px;">#</th>'
        f'<th style="text-align:left;padding:3px 8px;">State</th>'
        f'<th style="text-align:right;padding:3px 8px;">Score</th>'
        f'<th style="padding:3px 8px;">No-CON</th>'
        f'<th style="text-align:right;padding:3px 7px;">65+</th>'
        f'<th style="text-align:right;padding:3px 7px;">MA</th>'
        f'{axis_head}</tr></thead><tbody>{body_rows}</tbody></table>')

    weights = " · ".join(
        f'{_AXIS_LABEL[k]} {int(w*100)}%' for k, w in a["weights"].items())
    tx_read = (
        f'<div style="margin-top:10px;padding:9px 13px;background:#fbf3ef;'
        f'border-left:3px solid {_NEG};border-radius:0 3px 3px 0;'
        f'font-size:12px;color:#1a2332;line-height:1.55;">'
        f'<strong style="color:{_NEG};">Texas ranks #{tx["rank"]}</strong> '
        f'({tx["score"]:.0f}) — its {tx["seniors"]/1e6:.1f}M senior base + '
        f'{tx["ma_penetration"]*100:.0f}% MA + no-CON status put it among '
        f'the most attractive infusion roll-up markets. '
        f'<a href="/diligence/texas-infusion" style="color:{_NAVY};'
        f'font-weight:600;">Open the full Texas deep-dive →</a></div>')

    body = (
        ck_page_title(
            "Infusion Market Scan — by State",
            eyebrow="DILIGENCE · WHERE ELSE AFTER TEXAS",
            meta=f"51 states ranked · weights: {weights}",
        )
        + ck_source_purpose(
            purpose="Rank every state for an infusion roll-up on the "
                    "structural factors that make one work.",
            universe="illustrative",
            source="ACS demographics (vendored) + CMS MA geographic "
                   "variation + the documented no-CON state list. Weights "
                   "are a labeled framework; verify CON status at "
                   "engagement.",
        )
        + '<div class="ts-wrap" style="max-width:1000px;">'
        + '<div style="display:grid;grid-template-columns:auto 1fr;gap:22px;'
          'align-items:start;">'
        + f'<div>{_choropleth(states, lo, hi)}'
        + f'<div style="font-size:10px;color:{_FAINT};margin-top:4px;">'
          f'Darker = more attractive · ▭ red = Texas</div></div>'
        + f'<div>{table}</div></div>'
        + tx_read
        + f'<p style="font-size:10px;color:{_FAINT};margin-top:12px;'
          f'line-height:1.6;">{html.escape(a["note"])} Component columns '
          f'are each 0–100; Score is the weighted blend.</p>'
        + '</div>')
    return chartis_shell(
        body, "Infusion Market Scan", active_nav="/diligence",
        subtitle="State infusion attractiveness")
