"""National infusion-market scan — the page for
``infusion_state_attractiveness``. A state choropleth + ranked table that
answers "where else after Texas?" from real per-state data.
"""
from __future__ import annotations

import html
import urllib.parse
from typing import Any, Dict

from ._chartis_kit import chartis_shell, ck_page_title, ck_source_purpose
from .excel_mapping_page import _map_svg

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
    """Real-geography teal choropleth of attractiveness score; Texas
    outlined red as the benchmark market. Shares the Excel Mapping
    renderer so every state map in the product is the same geography."""
    return _map_svg({
        "values": {s["code"]: round(s["score"]) for s in states},
        # Integer legend ticks to match the rounded on-state labels.
        "lo": round(lo), "mid": round((lo + hi) / 2.0), "hi": round(hi),
        "c_low": "#e9f1f0", "c_mid": "#7ea8a5", "c_high": "#125e59",
        "accent": {"TX"}, "accent_color": _NEG,
        "notes": {s["code"]: f'#{s["rank"]} of {len(states)}'
                  for s in states},
        "label_mode": "value", "label_scale": 1.35,
        "max_width_px": 560,
        "aria_label": "State infusion attractiveness (geographic map)",
    })


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

    # Cross-link: open the scores in the Excel Mapping tool, pre-filled,
    # so a partner can restyle / export the map.
    _data = "\n".join(f"{s['code']},{s['score']:.0f}" for s in states)
    _map_qs = urllib.parse.urlencode({
        "data": _data, "low": "#e9f1f0", "mid": "#7bbcb5",
        "high": "#125e59", "lo": f"{lo:.0f}", "hi": f"{hi:.0f}",
        "midv": f"{(lo+hi)/2:.0f}"})
    map_link = (
        f'<p style="font-size:11.5px;margin-top:10px;">'
        f'<a href="/excel-mapping?{html.escape(_map_qs, quote=True)}" '
        f'style="color:{_TEAL};font-weight:600;text-decoration:none;">'
        f'⬈ Open this scan in Excel Mapping (restyle &amp; export the map) '
        f'→</a></p>')

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
        + map_link
        + f'<p style="font-size:10px;color:{_FAINT};margin-top:12px;'
          f'line-height:1.6;">{html.escape(a["note"])} Component columns '
          f'are each 0–100; Score is the weighted blend.</p>'
        + '</div>')
    return chartis_shell(
        body, "Infusion Market Scan", active_nav="/diligence",
        subtitle="State infusion attractiveness")
