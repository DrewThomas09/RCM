"""Medicare Advantage penetration page — /ma-penetration.

State choropleth + exposure-band table from the curated KFF/CMS cut,
plus a footprint calculator: enter a target's states and get the
average MA penetration of its geography vs the national norm. Renders
from ``rcm_mc.market_intel.ma_penetration``; the map reuses the
excel-mapping real-geography renderer so the two state maps stay
visually identical.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_data_cell, ck_kpi_block, ck_page_explainer,
    ck_page_title,
)
from rcm_mc.ui.excel_mapping_page import _map_svg

_BAND_TONE = {"SATURATED": "neg", "HIGH": "dim", "MODERATE": "dim",
              "LOW": "pos"}
# Parchment → teal → navy: high MA penetration renders dark (heavy
# managed-care exposure), matching how partners read risk maps.
_MAP_COLORS = {"c_low": "#f5f1ea", "c_mid": "#8db5b1", "c_high": "#0b2341"}


def _states_table(states) -> str:
    border = P["border"]; text_dim = P["text_dim"]
    cols = [("State", "left"), ("MA penetration", "right"),
            ("vs national (pp)", "right"), ("Exposure band", "left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid '
        f'{border};font-size:10px;color:{text_dim};letter-spacing:0.05em">'
        f'{c}</th>' for c, a in cols)
    from rcm_mc.market_intel.ma_penetration import national_penetration_pct
    nat = national_penetration_pct()
    trs = []
    for s in states:
        delta = s.penetration_pct - nat
        tone = _BAND_TONE.get(s.band, "dim")
        chip_color = (P["negative"] if s.band == "SATURATED" else
                      P["warning"] if s.band == "HIGH" else
                      P["text_faint"] if s.band == "MODERATE" else
                      P["positive"])
        chip = (f'<span style="display:inline-block;padding:2px 8px;'
                f'font-size:10px;font-family:JetBrains Mono,monospace;'
                f'color:{chip_color};border:1px solid {chip_color};'
                f'border-radius:2px;letter-spacing:0.06em">{s.band}</span>')
        trs.append("<tr>" + "".join([
            ck_data_cell(_html.escape(s.state), mono=True, weight=600),
            ck_data_cell(f"{s.penetration_pct:.1f}%", align="right",
                         mono=True, tone=tone, weight=600),
            ck_data_cell(f"{delta:+.1f}", align="right", mono=True,
                         tone="dim"),
            ck_data_cell(chip),
        ]) + "</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def render_ma_penetration(params: dict = None) -> str:
    params = params or {}
    from rcm_mc.market_intel.ma_penetration import (
        band_counts, footprint_exposure, list_state_penetration,
        national_penetration_pct,
    )
    states = list_state_penetration()
    nat = national_penetration_pct()
    counts = band_counts()

    footprint_raw = (params.get("footprint") or "").replace(",", " ")
    footprint_states = [s for s in footprint_raw.split() if s.strip()]
    fp = footprint_exposure(footprint_states) if footprint_states else None

    panel = P["panel"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]

    top, bottom = states[0], states[-1]
    kpi_strip = (
        ck_kpi_block("National MA share", f"{nat:.1f}%",
                     "of Medicare eligibles", "") +
        ck_kpi_block("Saturated states", str(counts["SATURATED"]),
                     "≥55% penetration", "") +
        ck_kpi_block("Low-MA states", str(counts["LOW"]),
                     "<30% penetration", "") +
        ck_kpi_block("Highest", f"{top.penetration_pct:.1f}%",
                     _html.escape(top.state), "") +
        ck_kpi_block("Lowest", f"{bottom.penetration_pct:.1f}%",
                     _html.escape(bottom.state), "")
    )
    if fp:
        kpi_strip += ck_kpi_block(
            "Footprint exposure", f"{fp['avg_penetration_pct']:.1f}%",
            f"{fp['vs_national_pp']:+.1f}pp vs national · {fp['band']}", "")

    # The excel-mapping renderer takes a cfg dict; values keyed by
    # 2-letter code with an explicit 0-70 domain so the gradient is
    # stable across data refreshes (not data-min/max relative).
    cfg = {
        **_MAP_COLORS,
        "lo": 0.0, "mid": 35.0, "hi": 70.0,
        "values": {s.state: s.penetration_pct for s in states},
    }

    form = f"""
<form method="GET" action="/ma-penetration" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Target footprint (state codes, e.g. "TX FL GA")
    <input name="footprint" value="{_html.escape(" ".join(footprint_states))}"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:220px"/>
  </label>
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Score footprint</button>
</form>"""

    cell = (f"background:{panel};border:1px solid {border};padding:16px;"
            f"margin-bottom:16px")
    h3 = (f"font-size:11px;font-weight:600;letter-spacing:0.08em;"
          f"color:{text_dim};text-transform:uppercase;margin-bottom:10px")

    page_title = ck_page_title(
        "Medicare Advantage Penetration",
        eyebrow="MARKET INTEL · PAYER GEOGRAPHY",
        meta=(f"{len(states)} states + DC · national {nat:.1f}% · "
              f"{counts['SATURATED']} saturated (≥55%) · "
              f"{counts['LOW']} low (<30%)"),
    )
    explainer = ck_page_explainer(
        "MA penetration is the geography-level payer variable.",
        "Where MA dominates, the Medicare book behaves like managed care: "
        "negotiated rates below fee-for-service, prior authorization, "
        "narrow networks, downcoding risk. Where traditional Medicare "
        "holds, the rate environment tracks the CMS fee schedules "
        "directly. Enter a target's state footprint to score its "
        "geographic MA exposure against the national norm. Curated from "
        "the KFF/CMS state cut, rounded to the point — verify against the "
        "current release before IC use.",
    )

    fp_block = ""
    if fp and fp["states"]:
        rows = " · ".join(
            f"{r['state']} {r['penetration_pct']:.0f}%"
            for r in fp["states"])
        fp_block = (
            f'<div style="{cell};border-left:3px solid {P["accent"]}">'
            f'<div style="{h3}">Footprint read</div>'
            f'<div style="font-size:14px;color:{text}">'
            f'{len(fp["states"])}-state footprint averages '
            f'{fp["avg_penetration_pct"]:.1f}% MA penetration '
            f'({fp["vs_national_pp"]:+.1f}pp vs national) — '
            f'{fp["band"]} exposure. {_html.escape(rows)}</div></div>')

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {explainer}
  {form}
  <div class="ck-kpi-grid">{kpi_strip}</div>
  {fp_block}
  <div style="{cell}">
    <div style="{h3}">MA penetration by state (% of Medicare eligibles)</div>
    {_map_svg(cfg)}
  </div>
  <div style="{cell}">
    <div style="{h3}">State exposure table (penetration-descending)</div>
    {_states_table(states)}
  </div>
</div>"""
    return chartis_shell(body, title="MA Penetration",
                         active_nav="/ma-penetration")
