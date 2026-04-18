"""Entry Multiple Analysis — EV/EBITDA entry multiples across sectors and return correlation.

Shows: EV/EBITDA distribution, sector multiple benchmarks, multiple expansion/contraction
by hold bucket, and a multiple-to-MOIC efficiency chart.
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


def _ev_ebitda(d: Dict) -> Optional[float]:
    ev = d.get("ev_mm")
    eb = d.get("ebitda_at_entry_mm") or d.get("ebitda_mm")
    if ev and eb and eb > 0:
        return ev / eb
    stored = d.get("ev_ebitda")
    return stored if stored and stored > 0 else None


def _multiple_histogram(mults: List[float], w: int = 340, h: int = 90) -> str:
    """Histogram of EV/EBITDA in 2× buckets."""
    if not mults:
        return ""
    buckets = list(range(4, 26, 2))
    counts = [0] * (len(buckets) - 1)
    for v in mults:
        for i in range(len(buckets) - 1):
            if buckets[i] <= v < buckets[i + 1]:
                counts[i] += 1
                break

    max_count = max(counts) if counts else 1
    pad_l, pad_r, pad_t, pad_b = 8, 8, 8, 22
    bar_w = (w - pad_l - pad_r) / len(counts)

    parts: List[str] = []
    for i, (cnt, lo) in enumerate(zip(counts, buckets[:-1])):
        bh = int(cnt / max_count * (h - pad_t - pad_b))
        x = pad_l + i * bar_w
        y = h - pad_b - bh
        col = P["positive"] if lo < 10 else (P["warning"] if lo < 14 else P["negative"])
        parts.append(f'<rect x="{x+1:.1f}" y="{y}" width="{bar_w-2:.1f}" height="{bh}" fill="{col}" fill-opacity="0.8"/>')
        if cnt > 0:
            parts.append(f'<text x="{x+bar_w/2:.1f}" y="{y-2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="7" font-family="{_MONO}">{cnt}</text>')
        parts.append(f'<text x="{x+bar_w/2:.1f}" y="{h-5}" text-anchor="middle" fill="{P["text_faint"]}" font-size="7" font-family="{_MONO}">{lo}–{lo+2}×</text>')

    return f'<svg width="{w}" height="{h}">{"".join(parts)}</svg>'


def _multiple_moic_scatter(corpus: List[Dict], w: int = 340, h: int = 220) -> str:
    """EV/EBITDA entry (x) vs MOIC (y)."""
    points = [
        (_ev_ebitda(d), d["realized_moic"], d.get("sector",""), d.get("deal_name",""))
        for d in corpus
        if _ev_ebitda(d) is not None and d.get("realized_moic") is not None
        and 2 <= (_ev_ebitda(d) or 0) <= 25
    ]
    if not points:
        return ""

    pad_l, pad_r, pad_t, pad_b = 36, 12, 10, 24
    cw, ch = w - pad_l - pad_r, h - pad_t - pad_b
    mult_max = 22.0
    moic_max = max(p[1] for p in points) * 1.05

    def xp(v: float) -> float:
        return pad_l + (v - 4) / (mult_max - 4) * cw

    def yp(v: float) -> float:
        return pad_t + (moic_max - v) / moic_max * ch

    parts: List[str] = []
    for mv in [6, 8, 10, 12, 14, 16, 18, 20]:
        px = xp(mv)
        parts.append(f'<line x1="{px:.1f}" y1="{pad_t}" x2="{px:.1f}" y2="{h-pad_b}" stroke="{P["border_dim"]}" stroke-width="1"/>')
        parts.append(f'<text x="{px:.1f}" y="{h-pad_b+10}" text-anchor="middle" fill="{P["text_faint"]}" font-size="7" font-family="{_MONO}">{mv}×</text>')

    for mv in [1.0, 2.0, 3.0, 4.0]:
        if mv <= moic_max:
            py = yp(mv)
            parts.append(f'<line x1="{pad_l}" y1="{py:.1f}" x2="{w-pad_r}" y2="{py:.1f}" stroke="{P["border_dim"]}" stroke-width="1"/>')
            parts.append(f'<text x="{pad_l-3}" y="{py+3:.1f}" text-anchor="end" fill="{P["text_faint"]}" font-size="7" font-family="{_MONO}">{mv:.1f}×</text>')

    py2 = yp(2.0)
    parts.append(f'<line x1="{pad_l}" y1="{py2:.1f}" x2="{w-pad_r}" y2="{py2:.1f}" stroke="{P["warning"]}" stroke-width="1" stroke-dasharray="3,2"/>')

    for mult, moic, sector, name in points:
        cx = xp(mult)
        cy = yp(moic)
        col = P["positive"] if mult < 10 and moic >= 2.5 else (P["negative"] if mult > 14 and moic < 2.0 else P["text_dim"])
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{col}" fill-opacity="0.65"><title>{html.escape(name[:40])}: {mult:.1f}×, MOIC {moic:.2f}×</title></circle>')

    parts.append(f'<text x="{pad_l+cw//2}" y="{h-2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="8" font-family="{_SANS}">Entry EV/EBITDA</text>')
    parts.append(f'<text x="10" y="{pad_t+ch//2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="8" font-family="{_SANS}" transform="rotate(-90,10,{pad_t+ch//2})">MOIC</text>')

    return f'<svg width="{w}" height="{h}">{"".join(parts)}</svg>'


def _sector_multiple_table(corpus: List[Dict]) -> str:
    sectors: Dict[str, List[float]] = defaultdict(list)
    sector_moic: Dict[str, List[float]] = defaultdict(list)
    for d in corpus:
        sec = d.get("sector")
        mult = _ev_ebitda(d)
        if sec and mult:
            sectors[sec].append(mult)
        if sec and mult and d.get("realized_moic"):
            sector_moic[sec].append(d["realized_moic"])

    rows_data = [(sec, mults) for sec, mults in sectors.items() if len(mults) >= 3]
    rows_data.sort(key=lambda x: -(_percentile(x[1], 50) or 0))

    rows = ""
    for i, (sec, mults) in enumerate(rows_data[:22]):
        bg = P["row_stripe"] if i % 2 else P["panel"]
        p25 = _percentile(mults, 25)
        p50 = _percentile(mults, 50)
        p75 = _percentile(mults, 75)
        moic_p50 = _percentile(sector_moic[sec], 50) if sector_moic[sec] else None

        mult_col = P["positive"] if (p50 or 0) < 10 else (P["warning"] if (p50 or 0) < 14 else P["negative"])
        moic_col = P["positive"] if (moic_p50 or 0) >= 2.5 else (P["warning"] if (moic_p50 or 0) >= 2.0 else P["text"])

        rows += (
            f'<tr style="background:{bg}">'
            f'<td style="padding:4px 8px;font-size:11px">{html.escape(sec[:30])}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{len(mults)}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{f"{p25:.1f}×" if p25 else "—"}</td>'
            f'<td style="padding:4px 8px;font-size:12px;font-family:{_MONO};text-align:right;font-weight:700;color:{mult_col};font-variant-numeric:tabular-nums">{f"{p50:.1f}×" if p50 else "—"}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{f"{p75:.1f}×" if p75 else "—"}</td>'
            f'<td style="padding:4px 8px;font-size:11px;font-family:{_MONO};text-align:right;color:{moic_col};font-variant-numeric:tabular-nums">{f"{moic_p50:.2f}×" if moic_p50 else "—"}</td>'
            f'</tr>'
        )

    th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P['border']}"
    return f"""<div style="border:1px solid {P['border']};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th}">SECTOR</th>
  <th style="{th};text-align:right">N</th>
  <th style="{th};text-align:right">EV/EBITDA P25</th>
  <th style="{th};text-align:right">EV/EBITDA P50</th>
  <th style="{th};text-align:right">EV/EBITDA P75</th>
  <th style="{th};text-align:right">MOIC P50</th>
</tr></thead>
<tbody>{rows}</tbody>
</table></div>"""


def render_entry_multiple() -> str:
    corpus = _load_corpus()
    has_mult = [d for d in corpus if _ev_ebitda(d) is not None]
    mults = [_ev_ebitda(d) for d in has_mult]

    p25 = _percentile(mults, 25)
    p50 = _percentile(mults, 50)
    p75 = _percentile(mults, 75)
    above14 = sum(1 for v in mults if v >= 14) / len(mults) * 100 if mults else 0

    kpis = "".join(
        f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:8px 14px">'
        f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:3px">{lbl}</div>'
        f'<div style="font-size:16px;font-family:{_MONO};font-variant-numeric:tabular-nums;color:{col}">{val}</div>'
        f'</div>'
        for lbl, val, col in [
            ("WITH MULT DATA",  str(len(has_mult)),                           P["text"]),
            ("EV/EBITDA P25",   f"{p25:.1f}×" if p25 else "—",              P["text"]),
            ("EV/EBITDA P50",   f"{p50:.1f}×" if p50 else "—",              P["positive"] if (p50 or 0) < 12 else P["warning"]),
            ("EV/EBITDA P75",   f"{p75:.1f}×" if p75 else "—",              P["text"]),
            ("≥14× (RICH)",     f"{above14:.0f}%",                           P["negative"] if above14 > 20 else P["text"]),
        ]
    )
    kpi_strip = f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:16px">{kpis}</div>'

    histogram = _multiple_histogram(mults)
    scatter = _multiple_moic_scatter(corpus)
    sector_table = _sector_multiple_table(corpus)

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {ck_section_header("ENTRY MULTIPLE ANALYSIS", f"EV/EBITDA at entry — {len(corpus)} corpus transactions", None)}
  {kpi_strip}

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px">
    <div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:10px">
      <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">EV/EBITDA DISTRIBUTION — 2× BUCKETS</div>
      <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:6px">Green &lt;10×, amber 10–14×, red &gt;14×.</div>
      {histogram}
    </div>
    <div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:10px">
      <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">ENTRY MULTIPLE vs REALIZED MOIC</div>
      <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:6px">Green = low entry + high MOIC. Red = rich entry + low MOIC.</div>
      {scatter}
    </div>
  </div>

  <div>
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:6px;border-bottom:1px solid {P['border']};padding-bottom:4px">
      EV/EBITDA BY SECTOR (min 3 deals with entry multiple)
    </div>
    {sector_table}
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P['text_faint']};font-family:{_SANS}">
    EV/EBITDA computed from ev_mm / ebitda_at_entry_mm when available, else disclosed ev_ebitda field.
    Rich = ≥14× entry. Corpus: {len(corpus)} transactions.
  </div>
</div>"""

    return chartis_shell(body, "Entry Multiple Analysis", active_nav="/entry-multiple",
                         subtitle=f"{len(has_mult)} deals with multiple data")
