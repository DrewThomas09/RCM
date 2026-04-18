"""Payer Rate Trend Analysis — payer mix trajectory over time vs corpus returns.

Shows:
- Commercial vs. government payer mix evolution by vintage (2005–2023)
- MOIC correlation with commercial payer percentage
- Payer regime distribution shift over time
- Commercial payer % percentile bands by deal year
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
    for i in range(2, 39):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            key = f"EXTENDED_SEED_DEALS_{i}"
            deals += getattr(mod, key, [])
        except Exception:
            pass
    return deals


from rcm_mc.ui._chartis_kit import P, _MONO, _SANS, chartis_shell, ck_section_header


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _get_comm_pct(d: Dict) -> Optional[float]:
    pm = d.get("payer_mix")
    if isinstance(pm, dict):
        return pm.get("commercial")
    return None


def _get_gov_pct(d: Dict) -> Optional[float]:
    pm = d.get("payer_mix")
    if isinstance(pm, dict):
        mc = pm.get("medicare", 0)
        mcaid = pm.get("medicaid", 0)
        return mc + mcaid
    return None


def _vintage_payer_trend_svg(corpus: List[Dict], w: int = 500, h: int = 180) -> str:
    """Line chart: avg commercial% and avg gov% by year (2005–2023)."""
    year_comm: Dict[int, List[float]] = defaultdict(list)
    year_gov: Dict[int, List[float]] = defaultdict(list)

    for d in corpus:
        yr = d.get("year")
        comm = _get_comm_pct(d)
        gov = _get_gov_pct(d)
        if yr and 2003 <= yr <= 2024:
            if comm is not None:
                year_comm[yr].append(comm)
            if gov is not None:
                year_gov[yr].append(gov)

    years = sorted(set(year_comm.keys()) | set(year_gov.keys()))
    if not years:
        return ""

    comm_avgs = [(yr, sum(year_comm[yr]) / len(year_comm[yr])) for yr in years if year_comm[yr]]
    gov_avgs  = [(yr, sum(year_gov[yr])  / len(year_gov[yr]))  for yr in years if year_gov[yr]]

    pad_l, pad_r, pad_t, pad_b = 36, 16, 10, 24
    cw, ch = w - pad_l - pad_r, h - pad_t - pad_b
    yr_min, yr_max = min(years), max(years)
    val_min, val_max = 0.0, 1.0

    def xp(yr: float) -> float:
        return pad_l + (yr - yr_min) / max(yr_max - yr_min, 1) * cw

    def yp(v: float) -> float:
        return pad_t + (val_max - v) / (val_max - val_min) * ch

    parts: List[str] = []
    # grid
    for pct in [0.2, 0.4, 0.6, 0.8]:
        py = yp(pct)
        parts.append(f'<line x1="{pad_l}" y1="{py:.1f}" x2="{w-pad_r}" y2="{py:.1f}" stroke="{P["border_dim"]}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l-3}" y="{py+3:.1f}" text-anchor="end" fill="{P["text_faint"]}" font-size="8" font-family="{_MONO}" font-variant-numeric="tabular-nums">{int(pct*100)}%</text>')

    for yr in range(yr_min, yr_max + 1, 2):
        px = xp(yr)
        parts.append(f'<line x1="{px:.1f}" y1="{pad_t}" x2="{px:.1f}" y2="{h-pad_b}" stroke="{P["border_dim"]}" stroke-width="1"/>')
        parts.append(f'<text x="{px:.1f}" y="{h-pad_b+10}" text-anchor="middle" fill="{P["text_faint"]}" font-size="7" font-family="{_MONO}">{yr}</text>')

    # commercial line
    if len(comm_avgs) > 1:
        pts = " ".join(f"{xp(yr):.1f},{yp(v):.1f}" for yr, v in comm_avgs)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{P["accent"]}" stroke-width="2"/>')
        for yr, v in comm_avgs:
            parts.append(f'<circle cx="{xp(yr):.1f}" cy="{yp(v):.1f}" r="3" fill="{P["accent"]}"/>')

    # gov line
    if len(gov_avgs) > 1:
        pts = " ".join(f"{xp(yr):.1f},{yp(v):.1f}" for yr, v in gov_avgs)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{P["warning"]}" stroke-width="2"/>')
        for yr, v in gov_avgs:
            parts.append(f'<circle cx="{xp(yr):.1f}" cy="{yp(v):.1f}" r="3" fill="{P["warning"]}"/>')

    # legend
    parts.append(f'<rect x="{w-120}" y="{pad_t}" width="10" height="4" fill="{P["accent"]}"/>')
    parts.append(f'<text x="{w-106}" y="{pad_t+6}" fill="{P["accent"]}" font-size="8" font-family="{_SANS}">Commercial %</text>')
    parts.append(f'<rect x="{w-120}" y="{pad_t+14}" width="10" height="4" fill="{P["warning"]}"/>')
    parts.append(f'<text x="{w-106}" y="{pad_t+20}" fill="{P["warning"]}" font-size="8" font-family="{_SANS}">Gov % (MC+MCD)</text>')

    return f'<svg width="{w}" height="{h}">{"".join(parts)}</svg>'


def _comm_moic_scatter(corpus: List[Dict], w: int = 320, h: int = 200) -> str:
    """Commercial% (x) vs MOIC (y) scatter."""
    points = [
        (_get_comm_pct(d), d["realized_moic"], d.get("deal_name",""))
        for d in corpus
        if _get_comm_pct(d) is not None and d.get("realized_moic") is not None
    ]
    if not points:
        return ""

    pad_l, pad_r, pad_t, pad_b = 36, 12, 10, 24
    cw, ch = w - pad_l - pad_r, h - pad_t - pad_b
    moic_max = max(p[1] for p in points) * 1.05

    def xp(v: float) -> float:
        return pad_l + v * cw

    def yp(v: float) -> float:
        return pad_t + (moic_max - v) / moic_max * ch

    parts: List[str] = []
    for pct in [0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        px = xp(pct)
        parts.append(f'<line x1="{px:.1f}" y1="{pad_t}" x2="{px:.1f}" y2="{h-pad_b}" stroke="{P["border_dim"]}" stroke-width="1"/>')
        parts.append(f'<text x="{px:.1f}" y="{h-pad_b+10}" text-anchor="middle" fill="{P["text_faint"]}" font-size="7" font-family="{_MONO}">{int(pct*100)}%</text>')

    for mv in [1.0, 2.0, 3.0, 4.0]:
        if mv <= moic_max:
            py = yp(mv)
            parts.append(f'<line x1="{pad_l}" y1="{py:.1f}" x2="{w-pad_r}" y2="{py:.1f}" stroke="{P["border_dim"]}" stroke-width="1"/>')
            parts.append(f'<text x="{pad_l-3}" y="{py+3:.1f}" text-anchor="end" fill="{P["text_faint"]}" font-size="7" font-family="{_MONO}">{mv:.1f}×</text>')

    # 2.0x line
    py2 = yp(2.0)
    parts.append(f'<line x1="{pad_l}" y1="{py2:.1f}" x2="{w-pad_r}" y2="{py2:.1f}" stroke="{P["warning"]}" stroke-width="1" stroke-dasharray="3,2"/>')

    for comm, moic, name in points:
        cx = xp(comm)
        cy = yp(moic)
        col = P["positive"] if comm >= 0.5 and moic >= 2.0 else (P["negative"] if moic < 1.5 else P["text_dim"])
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="{col}" fill-opacity="0.7"><title>{html.escape(name[:40])}: comm {comm*100:.0f}%, MOIC {moic:.2f}×</title></circle>')

    parts.append(f'<text x="{pad_l+cw//2}" y="{h-2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="8" font-family="{_SANS}">Commercial Payer %</text>')
    parts.append(f'<text x="10" y="{pad_t+ch//2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="8" font-family="{_SANS}" transform="rotate(-90,10,{pad_t+ch//2})">MOIC</text>')

    return f'<svg width="{w}" height="{h}">{"".join(parts)}</svg>'


def _payer_regime_shift_table(corpus: List[Dict]) -> str:
    """Table of payer regime distribution by 5-year vintage bucket."""
    REGIMES = ["Commercial", "Balanced", "Gov-Mix", "Medicare-Heavy", "Medicaid-Heavy", "Unknown"]

    def _regime(d: Dict) -> str:
        pm = d.get("payer_mix")
        if not isinstance(pm, dict): return "Unknown"
        comm = pm.get("commercial", 0)
        mc   = pm.get("medicare", 0)
        mcaid = pm.get("medicaid", 0)
        if comm  >= 0.55: return "Commercial"
        if mc    >= 0.50: return "Medicare-Heavy"
        if mcaid >= 0.40: return "Medicaid-Heavy"
        if mc + mcaid >= 0.60: return "Gov-Mix"
        return "Balanced"

    def _bucket(yr: Optional[int]) -> str:
        if yr is None:    return "Unknown"
        if yr < 2005:     return "Pre-2005"
        if yr < 2010:     return "2005–2009"
        if yr < 2015:     return "2010–2014"
        if yr < 2020:     return "2015–2019"
        return "2020+"

    BUCKETS = ["Pre-2005", "2005–2009", "2010–2014", "2015–2019", "2020+"]
    bucket_regime: Dict[str, Dict[str, int]] = {b: defaultdict(int) for b in BUCKETS}
    bucket_totals: Dict[str, int] = defaultdict(int)

    for d in corpus:
        b = _bucket(d.get("year"))
        r = _regime(d)
        if b in bucket_regime:
            bucket_regime[b][r] += 1
            bucket_totals[b] += 1

    th = f"padding:4px 8px;font-size:9px;letter-spacing:.06em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P['border']};border-right:1px solid {P['border_dim']}"
    header = f"<tr style='background:{P['panel_alt']}'><th style='{th}'>BUCKET</th><th style='{th};text-align:right'>N</th>"
    for r in REGIMES:
        header += f"<th style='{th};text-align:right'>{html.escape(r)}</th>"
    header += "</tr>"

    rows = ""
    for i, b in enumerate(BUCKETS):
        bg = P["row_stripe"] if i % 2 else P["panel"]
        total = bucket_totals[b]
        row = f"<tr style='background:{bg}'><td style='padding:4px 8px;font-size:11px'>{html.escape(b)}</td>"
        row += f"<td style='padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums'>{total}</td>"
        for r in REGIMES:
            cnt = bucket_regime[b][r]
            pct = cnt / total * 100 if total > 0 else 0
            col = P["accent"] if r == "Commercial" and pct >= 30 else (P["warning"] if r == "Medicare-Heavy" and pct >= 30 else P["text_dim"])
            row += f"<td style='padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{col};font-variant-numeric:tabular-nums'>{f'{pct:.0f}%' if cnt > 0 else '—'}</td>"
        rows += row + "</tr>"

    return f"""<div style="border:1px solid {P['border']};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead>{header}</thead>
<tbody>{rows}</tbody>
</table></div>"""


def render_payer_rate_trends() -> str:
    corpus = _load_corpus()
    with_payer = [d for d in corpus if isinstance(d.get("payer_mix"), dict)]

    comm_vals = [_get_comm_pct(d) for d in with_payer if _get_comm_pct(d) is not None]
    gov_vals  = [_get_gov_pct(d)  for d in with_payer if _get_gov_pct(d)  is not None]

    comm_p50 = _percentile(comm_vals, 50)
    gov_p50  = _percentile(gov_vals, 50)

    kpis = "".join(
        f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:8px 14px">'
        f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:3px">{lbl}</div>'
        f'<div style="font-size:16px;font-family:{_MONO};font-variant-numeric:tabular-nums;color:{P["text"]}">{val}</div>'
        f'</div>'
        for lbl, val in [
            ("CORPUS N",          str(len(corpus))),
            ("WITH PAYER DATA",   str(len(with_payer))),
            ("COMM% P50",         f"{comm_p50*100:.0f}%" if comm_p50 else "—"),
            ("GOV% P50",          f"{gov_p50*100:.0f}%"  if gov_p50  else "—"),
        ]
    )
    kpi_strip = f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:16px">{kpis}</div>'

    trend_chart = _vintage_payer_trend_svg(corpus)
    scatter     = _comm_moic_scatter(corpus)
    regime_table = _payer_regime_shift_table(corpus)

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {ck_section_header("PAYER RATE TRENDS", f"Commercial vs. government payer mix evolution — {len(corpus)} transactions", None)}
  {kpi_strip}

  <div style="margin-bottom:20px;background:{P['panel_alt']};border:1px solid {P['border']};padding:12px">
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">PAYER MIX TREND BY VINTAGE YEAR — AVERAGE COMMERCIAL% VS GOV%</div>
    <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:8px">
      Blue = average commercial %. Amber = average government (Medicare + Medicaid) %. Per year, deals with disclosed payer mix.
    </div>
    {trend_chart}
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px">
    <div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:10px">
      <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">COMMERCIAL PAYER % vs REALIZED MOIC</div>
      <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:6px">Dashed = 2.0× MOIC threshold. Higher commercial % generally supports stronger returns.</div>
      {scatter}
    </div>
    <div>
      <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">PAYER REGIME DISTRIBUTION BY VINTAGE BUCKET</div>
      {regime_table}
    </div>
  </div>
</div>"""

    return chartis_shell(body, "Payer Rate Trends", active_nav="/payer-rate-trends",
                         subtitle=f"{len(with_payer)} deals with payer data")
