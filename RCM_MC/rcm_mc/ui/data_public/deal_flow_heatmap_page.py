"""Deal Flow Heatmap page — year × sector activity matrix.

Shows deal count per (year, sector) cell as a color-intensity heatmap.
Identifies which sectors saw peak activity by vintage, useful for
understanding market cycle timing and sectoral concentration risk.
"""
from __future__ import annotations

import html
import importlib
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    deals: List[Dict[str, Any]] = list(_SEED_DEALS)
    for i in range(2, 36):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            key = f"EXTENDED_SEED_DEALS_{i}"
            deals += getattr(mod, key, [])
        except Exception:
            pass
    return deals


from rcm_mc.ui._chartis_kit import P, _MONO, _SANS, chartis_shell, ck_section_header


def _heatmap_svg(
    years: List[int],
    sectors: List[str],
    matrix: Dict[Tuple[int, str], int],
    max_count: int,
    cell_w: int = 28,
    cell_h: int = 18,
    pad_l: int = 160,
    pad_t: int = 40,
) -> str:
    w = pad_l + len(years) * cell_w + 8
    h = pad_t + len(sectors) * cell_h + 16

    parts: List[str] = []

    # year headers (rotated)
    for j, yr in enumerate(years):
        x = pad_l + j * cell_w + cell_w // 2
        parts.append(
            f'<text x="{x}" y="{pad_t-4}" text-anchor="middle" '
            f'fill="{P["text_dim"]}" font-size="8" font-family="{_MONO}" '
            f'font-variant-numeric="tabular-nums">{yr}</text>'
        )

    for i, sector in enumerate(sectors):
        y_top = pad_t + i * cell_h
        y_mid = y_top + cell_h // 2

        # sector label
        trunc = sector[:24]
        parts.append(
            f'<text x="{pad_l-6}" y="{y_mid+4}" text-anchor="end" '
            f'fill="{P["text_dim"]}" font-size="9" font-family="{_SANS}">'
            f'{html.escape(trunc)}</text>'
        )

        for j, yr in enumerate(years):
            count = matrix.get((yr, sector), 0)
            x_left = pad_l + j * cell_w
            # intensity: 0 = dark bg, max = bright accent
            intensity = (count / max_count) ** 0.6 if max_count > 0 and count > 0 else 0

            if count == 0:
                fill = P["panel"]
                stroke = P["border_dim"]
            elif intensity < 0.25:
                fill = "#0d1a2e"
                stroke = P["border"]
            elif intensity < 0.55:
                fill = "#1a3a5c"
                stroke = P["border"]
            elif intensity < 0.80:
                fill = "#1e5a8e"
                stroke = P["border"]
            else:
                fill = P["accent"]
                stroke = "#1d4ed8"

            parts.append(
                f'<rect x="{x_left+1}" y="{y_top+1}" width="{cell_w-2}" height="{cell_h-2}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="0.5">'
                f'<title>{html.escape(sector)} {yr}: {count} deal{"s" if count != 1 else ""}</title>'
                f'</rect>'
            )
            if count > 0:
                text_col = P["text"] if intensity >= 0.4 else P["text_dim"]
                parts.append(
                    f'<text x="{x_left+cell_w//2}" y="{y_mid+4}" text-anchor="middle" '
                    f'fill="{text_col}" font-size="8" font-family="{_MONO}" '
                    f'font-variant-numeric="tabular-nums">{count}</text>'
                )

    return f'<svg width="{w}" height="{h}" style="display:block">{"".join(parts)}</svg>'


def _moic_heat_svg(
    years: List[int],
    sectors: List[str],
    moic_matrix: Dict[Tuple[int, str], float],
    count_matrix: Dict[Tuple[int, str], int],
    cell_w: int = 32,
    cell_h: int = 18,
    pad_l: int = 160,
    pad_t: int = 40,
) -> str:
    """Heatmap of median MOIC per (year, sector) cell."""
    vals = [v for v in moic_matrix.values() if v > 0]
    if not vals:
        return ""
    vmax = max(vals)

    w = pad_l + len(years) * cell_w + 8
    h = pad_t + len(sectors) * cell_h + 16

    parts: List[str] = []
    for j, yr in enumerate(years):
        x = pad_l + j * cell_w + cell_w // 2
        parts.append(f'<text x="{x}" y="{pad_t-4}" text-anchor="middle" fill="{P["text_dim"]}" font-size="8" font-family="{_MONO}" font-variant-numeric="tabular-nums">{yr}</text>')

    for i, sector in enumerate(sectors):
        y_top = pad_t + i * cell_h
        y_mid = y_top + cell_h // 2
        trunc = sector[:24]
        parts.append(f'<text x="{pad_l-6}" y="{y_mid+4}" text-anchor="end" fill="{P["text_dim"]}" font-size="9" font-family="{_SANS}">{html.escape(trunc)}</text>')

        for j, yr in enumerate(years):
            cnt = count_matrix.get((yr, sector), 0)
            moic = moic_matrix.get((yr, sector), 0)
            x_left = pad_l + j * cell_w

            if cnt == 0 or moic == 0:
                fill = P["panel"]
                stroke = P["border_dim"]
                text_col = "transparent"
                label = ""
            else:
                ratio = min(1.0, moic / 4.0)
                if moic >= 3.0:
                    fill = P["positive"]
                    stroke = "#059669"
                elif moic >= 2.5:
                    fill = "#1a4a2e"
                    stroke = P["border"]
                elif moic >= 2.0:
                    fill = "#1a3a20"
                    stroke = P["border"]
                elif moic >= 1.5:
                    fill = P["panel_alt"]
                    stroke = P["border"]
                else:
                    fill = "#2a1010"
                    stroke = P["border"]
                text_col = P["text"] if moic >= 2.5 else P["text_dim"]
                label = f"{moic:.1f}"

            parts.append(f'<rect x="{x_left+1}" y="{y_top+1}" width="{cell_w-2}" height="{cell_h-2}" fill="{fill}" stroke="{stroke}" stroke-width="0.5"><title>{html.escape(sector)} {yr}: MOIC {moic:.2f}× ({cnt} deals)</title></rect>')
            if label:
                parts.append(f'<text x="{x_left+cell_w//2}" y="{y_mid+4}" text-anchor="middle" fill="{text_col}" font-size="8" font-family="{_MONO}" font-variant-numeric="tabular-nums">{label}</text>')

    return f'<svg width="{w}" height="{h}" style="display:block">{"".join(parts)}</svg>'


def render_deal_flow_heatmap(min_sector_deals: int = 3) -> str:
    corpus = _load_corpus()

    # build year × sector matrices
    count_matrix: Dict[Tuple[int, str], int] = defaultdict(int)
    moic_sum: Dict[Tuple[int, str], float] = defaultdict(float)
    moic_count: Dict[Tuple[int, str], int] = defaultdict(int)

    sector_totals: Dict[str, int] = defaultdict(int)
    year_totals: Dict[int, int] = defaultdict(int)

    for d in corpus:
        yr = d.get("year")
        sec = d.get("sector")
        if not yr or not sec:
            continue
        count_matrix[(yr, sec)] += 1
        sector_totals[sec] += 1
        year_totals[yr] += 1
        moic = d.get("realized_moic")
        if moic is not None:
            moic_sum[(yr, sec)] += moic
            moic_count[(yr, sec)] += 1

    # filter sectors by minimum deal count
    active_sectors = sorted(
        [s for s, n in sector_totals.items() if n >= min_sector_deals],
        key=lambda s: -sector_totals[s],
    )[:25]

    all_years = sorted(year_totals.keys())

    # clip to 2000–2024
    years = [y for y in all_years if 2000 <= y <= 2024]

    max_count = max((count_matrix.get((y, s), 0) for y in years for s in active_sectors), default=1)

    # median MOIC matrix
    moic_matrix: Dict[Tuple[int, str], float] = {}
    for (yr, sec), total in moic_sum.items():
        cnt = moic_count.get((yr, sec), 0)
        if cnt > 0:
            moic_matrix[(yr, sec)] = total / cnt

    heat_svg = _heatmap_svg(years, active_sectors, dict(count_matrix), max_count)
    moic_svg = _moic_heat_svg(years, active_sectors, moic_matrix, dict(count_matrix))

    # sector activity bar
    bar_items = ""
    max_sec = max(sector_totals.values()) if sector_totals else 1
    for sec in active_sectors[:20]:
        n = sector_totals[sec]
        bar_w = int(n / max_sec * 180)
        moic_sec = [d["realized_moic"] for d in corpus if d.get("sector") == sec and d.get("realized_moic") is not None]
        moic_med = sorted(moic_sec)[len(moic_sec)//2] if moic_sec else None
        moic_str = f"{moic_med:.2f}×" if moic_med else "—"
        moic_col = P["positive"] if (moic_med or 0) >= 2.5 else P["text_dim"]
        bar_items += (
            f'<tr><td style="padding:3px 8px;font-size:10px;white-space:nowrap">{html.escape(sec[:30])}</td>'
            f'<td style="padding:3px 8px"><svg width="180" height="10">'
            f'<rect x="0" y="2" width="{bar_w}" height="6" fill="{P["accent"]}"/>'
            f'</svg></td>'
            f'<td style="padding:3px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{n}</td>'
            f'<td style="padding:3px 8px;font-size:10px;font-family:{_MONO};color:{moic_col};text-align:right;font-variant-numeric:tabular-nums">{moic_str}</td>'
            f'</tr>'
        )

    th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P['border']}"
    sector_bar_table = f"""<table style="border-collapse:collapse;width:100%">
<thead><tr><th style="{th}">SECTOR</th><th style="{th}">DEAL VOLUME</th><th style="{th};text-align:right">N</th><th style="{th};text-align:right">MOIC MED</th></tr></thead>
<tbody>{bar_items}</tbody></table>"""

    # color legend
    legend = (
        f'<div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;font-size:9px;font-family:{_SANS}">'
        f'<span style="color:{P["text_dim"]}">COUNT INTENSITY:</span>'
        + "".join(
            f'<span><span style="display:inline-block;width:14px;height:10px;background:{bg};border:1px solid {P["border"]};vertical-align:middle"></span>'
            f'<span style="color:{P["text_dim"]};margin-left:3px">{lbl}</span></span>'
            for bg, lbl in [
                (P["panel"], "0"), ("#0d1a2e", "1"), ("#1a3a5c", "2–3"), ("#1e5a8e", "4–5"), (P["accent"], "6+")
            ]
        )
        + f'</div>'
    )
    moic_legend = (
        f'<div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;font-size:9px;font-family:{_SANS}">'
        f'<span style="color:{P["text_dim"]}">MOIC COLOR:</span>'
        + "".join(
            f'<span><span style="display:inline-block;width:14px;height:10px;background:{bg};border:1px solid {P["border"]};vertical-align:middle"></span>'
            f'<span style="color:{P["text_dim"]};margin-left:3px">{lbl}</span></span>'
            for bg, lbl in [
                ("#2a1010", "<1.5×"), (P["panel_alt"], "1.5–2.0×"), ("#1a3a20", "2.0–2.5×"), ("#1a4a2e", "2.5–3.0×"), (P["positive"], "≥3.0×")
            ]
        )
        + f'</div>'
    )

    min_filter_links = " ".join(
        f'<a href="/deal-flow-heatmap?min_deals={n}" style="font-size:11px;font-family:{_MONO};color:{P["accent"] if min_sector_deals==n else P["text_dim"]};text-decoration:none;padding:2px 7px;border:1px solid {P["border"] if min_sector_deals!=n else P["accent"]}">{n}+</a>'
        for n in [1, 2, 3, 5, 8]
    )

    body = f"""
<div style="padding:16px 20px;max-width:1600px">
  {ck_section_header("DEAL FLOW HEATMAP", f"Year × sector activity matrix — {len(corpus)} transactions, {len(active_sectors)} active sectors", None)}

  <div style="display:flex;gap:8px;align-items:center;margin-bottom:14px">
    <span style="font-size:10px;color:{P['text_dim']};font-family:{_SANS}">MIN SECTOR DEALS:</span>
    {min_filter_links}
  </div>

  <div style="margin-bottom:20px">
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:8px;border-bottom:1px solid {P['border']};padding-bottom:4px">DEAL COUNT HEATMAP — DARKER = MORE ACTIVE</div>
    {legend}
    <div style="overflow-x:auto;background:{P['panel_alt']};border:1px solid {P['border']};padding:12px">
      {heat_svg}
    </div>
  </div>

  <div style="margin-bottom:20px">
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:8px;border-bottom:1px solid {P['border']};padding-bottom:4px">MEDIAN MOIC HEATMAP — GREEN = STRONG RETURNS</div>
    {moic_legend}
    <div style="overflow-x:auto;background:{P['panel_alt']};border:1px solid {P['border']};padding:12px">
      {moic_svg}
    </div>
  </div>

  <div>
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:8px;border-bottom:1px solid {P['border']};padding-bottom:4px">SECTOR ACTIVITY RANKING</div>
    <div style="border:1px solid {P['border']};overflow-x:auto">
      {sector_bar_table}
    </div>
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P['text_faint']};font-family:{_SANS}">
    Only deals with disclosed sector and year are shown. MOIC median shown per cell when ≥1 deal with disclosed return. Corpus: 705 transactions.
  </div>
</div>"""

    return chartis_shell(body, "Deal Flow Heatmap", active_nav="/deal-flow-heatmap",
                         subtitle=f"{len(active_sectors)} sectors × {len(years)} years")
