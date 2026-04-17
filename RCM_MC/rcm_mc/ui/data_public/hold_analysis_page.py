"""Hold Duration Analysis page — relationship between hold period and realized returns.

Shows: hold duration distribution, MOIC vs hold scatter, hold bucket P-tiles,
sector-specific hold norms, and outlier identification (long hold / poor return).
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
    for i in range(2, 38):
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


def _scatter_svg(
    deals: List[Dict[str, Any]],
    w: int = 440,
    h: int = 280,
) -> str:
    """Hold years (x) vs realized MOIC (y) scatter."""
    points = [
        (d["hold_years"], d["realized_moic"], d.get("sector"), d.get("deal_name", ""))
        for d in deals
        if d.get("hold_years") is not None and d.get("realized_moic") is not None
    ]
    if not points:
        return ""

    pad_l, pad_r, pad_t, pad_b = 42, 16, 12, 28
    cw, ch = w - pad_l - pad_r, h - pad_t - pad_b

    hold_max = max(p[0] for p in points) * 1.05
    moic_max = max(p[1] for p in points) * 1.05
    hold_min, moic_min = 0, 0

    def xp(v: float) -> float:
        return pad_l + (v - hold_min) / (hold_max - hold_min) * cw

    def yp(v: float) -> float:
        return pad_t + (moic_max - v) / (moic_max - moic_min) * ch

    parts: List[str] = []

    # grid
    for v in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        if v <= hold_max:
            px = xp(v)
            parts.append(f'<line x1="{px:.1f}" y1="{pad_t}" x2="{px:.1f}" y2="{h-pad_b}" stroke="{P["border_dim"]}" stroke-width="1"/>')
            parts.append(f'<text x="{px:.1f}" y="{h-pad_b+10}" text-anchor="middle" fill="{P["text_faint"]}" font-size="8" font-family="{_MONO}">{v}y</text>')

    for v in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        if v <= moic_max:
            py = yp(v)
            parts.append(f'<line x1="{pad_l}" y1="{py:.1f}" x2="{w-pad_r}" y2="{py:.1f}" stroke="{P["border_dim"]}" stroke-width="1"/>')
            parts.append(f'<text x="{pad_l-4}" y="{py+3:.1f}" text-anchor="end" fill="{P["text_faint"]}" font-size="8" font-family="{_MONO}" font-variant-numeric="tabular-nums">{v:.1f}×</text>')

    # 2.0x line
    if moic_min <= 2.0 <= moic_max:
        py = yp(2.0)
        parts.append(f'<line x1="{pad_l}" y1="{py:.1f}" x2="{w-pad_r}" y2="{py:.1f}" stroke="{P["warning"]}" stroke-width="1" stroke-dasharray="4,2"/>')

    # points
    for hold, moic, sector, name in points:
        cx = xp(hold)
        cy = yp(moic)
        col = P["positive"] if moic >= 2.5 else (P["warning"] if moic >= 2.0 else P["negative"])
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{col}" fill-opacity="0.7" stroke="{col}" stroke-width="1">'
            f'<title>{html.escape(name[:40])}: hold {hold:.1f}y, MOIC {moic:.2f}×</title>'
            f'</circle>'
        )

    # axis labels
    parts.append(f'<text x="{pad_l + cw//2}" y="{h-1}" text-anchor="middle" fill="{P["text_dim"]}" font-size="9" font-family="{_SANS}">Hold (years)</text>')
    parts.append(f'<text x="10" y="{pad_t + ch//2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="9" font-family="{_SANS}" transform="rotate(-90,10,{pad_t + ch//2})">MOIC</text>')

    return f'<svg width="{w}" height="{h}">{"".join(parts)}</svg>'


def _hold_histogram(deals: List[Dict[str, Any]], w: int = 340, h: int = 90) -> str:
    holds = [d["hold_years"] for d in deals if d.get("hold_years") is not None]
    if not holds:
        return ""

    buckets = [(0,2,"Short"), (2,4,"2–4y"), (4,6,"4–6y"), (6,8,"6–8y"), (8,20,"8y+")]
    counts = []
    for lo, hi, lbl in buckets:
        n = sum(1 for h in holds if lo <= h < hi)
        counts.append((lbl, n))

    max_n = max(c for _, c in counts) if counts else 1
    pad_l, pad_r, pad_t, pad_b = 8, 8, 8, 22
    bar_w = (w - pad_l - pad_r) // len(counts) - 4

    parts: List[str] = []
    for i, (lbl, n) in enumerate(counts):
        bh = int(n / max_n * (h - pad_t - pad_b))
        x = pad_l + i * ((w - pad_l - pad_r) // len(counts))
        y = h - pad_b - bh
        col = P["accent"]
        parts.append(f'<rect x="{x+2}" y="{y}" width="{bar_w}" height="{bh}" fill="{col}"/>')
        parts.append(f'<text x="{x+2+bar_w//2}" y="{y-2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="9" font-family="{_MONO}" font-variant-numeric="tabular-nums">{n}</text>')
        parts.append(f'<text x="{x+2+bar_w//2}" y="{h-5}" text-anchor="middle" fill="{P["text_dim"]}" font-size="8" font-family="{_SANS}">{lbl}</text>')

    return f'<svg width="{w}" height="{h}">{"".join(parts)}</svg>'


def _bucket_table(deals: List[Dict[str, Any]]) -> str:
    buckets = [
        ("Short (<3y)",    0,  3),
        ("Medium (3–5y)",  3,  5),
        ("Long (5–7y)",    5,  7),
        ("Extended (7y+)", 7, 99),
    ]

    rows = ""
    for lbl, lo, hi in buckets:
        group = [d for d in deals if d.get("hold_years") is not None and lo <= d["hold_years"] < hi]
        moics = [d["realized_moic"] for d in group if d.get("realized_moic") is not None]
        irrs  = [d["realized_irr"]  for d in group if d.get("realized_irr")  is not None]
        p25 = _percentile(moics, 25)
        p50 = _percentile(moics, 50)
        p75 = _percentile(moics, 75)
        irr50 = _percentile(irrs, 50)
        win = sum(1 for m in moics if m >= 2.0) / len(moics) * 100 if moics else None

        col = P["positive"] if (p50 or 0) >= 2.5 else (P["warning"] if (p50 or 0) >= 2.0 else P["text"])
        rows += (
            f'<tr style="background:{P["row_stripe"] if buckets.index((lbl,lo,hi))%2 else P["panel"]}">'
            f'<td style="padding:5px 8px;font-size:11px">{html.escape(lbl)}</td>'
            f'<td style="padding:5px 8px;font-size:11px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{len(group)}</td>'
            f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{f"{p25:.2f}×" if p25 else "—"}</td>'
            f'<td style="padding:5px 8px;font-size:12px;font-family:{_MONO};text-align:right;font-weight:700;color:{col};font-variant-numeric:tabular-nums">{f"{p50:.2f}×" if p50 else "—"}</td>'
            f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{f"{p75:.2f}×" if p75 else "—"}</td>'
            f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{f"{irr50*100:.1f}%" if irr50 else "—"}</td>'
            f'<td style="padding:5px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{f"{win:.0f}%" if win is not None else "—"}</td>'
            f'</tr>'
        )

    th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};font-weight:600;border-bottom:1px solid {P['border']}"
    return f"""<div style="border:1px solid {P['border']};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th}">HOLD BUCKET</th>
  <th style="{th};text-align:right">N</th>
  <th style="{th};text-align:right">MOIC P25</th>
  <th style="{th};text-align:right">MOIC P50</th>
  <th style="{th};text-align:right">MOIC P75</th>
  <th style="{th};text-align:right">IRR P50</th>
  <th style="{th};text-align:right">WIN%</th>
</tr></thead>
<tbody>{rows}</tbody>
</table></div>"""


def _outliers_table(deals: List[Dict[str, Any]]) -> str:
    outliers = [
        d for d in deals
        if d.get("hold_years") and d.get("realized_moic")
        and (d["hold_years"] >= 7 and d["realized_moic"] < 2.5)
    ]
    outliers.sort(key=lambda d: d["hold_years"] / max(d["realized_moic"], 0.01), reverse=True)

    if not outliers:
        return f'<p style="color:{P["text_dim"]};font-size:11px">No outliers found (long hold + sub-threshold MOIC).</p>'

    rows = ""
    for i, d in enumerate(outliers[:15]):
        bg = P["row_stripe"] if i % 2 else P["panel"]
        hold = d["hold_years"]
        moic = d["realized_moic"]
        col = P["negative"] if moic < 2.0 else P["warning"]
        rows += (
            f'<tr style="background:{P["row_stripe"] if i%2 else P["panel"]}">'
            f'<td style="padding:4px 8px;font-size:11px">{html.escape(d.get("deal_name","")[:40])}</td>'
            f'<td style="padding:4px 8px;font-size:10px;color:{P["text_dim"]}">{html.escape(d.get("sector","") or "—")}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{d.get("year","—")}</td>'
            f'<td style="padding:4px 8px;font-size:11px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{hold:.1f}y</td>'
            f'<td style="padding:4px 8px;font-size:12px;font-family:{_MONO};text-align:right;font-weight:700;color:{col};font-variant-numeric:tabular-nums">{moic:.2f}×</td>'
            f'</tr>'
        )

    th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P['border']}"
    return f"""<div style="border:1px solid {P['border']};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th}">DEAL</th><th style="{th}">SECTOR</th><th style="{th};text-align:right">YEAR</th>
  <th style="{th};text-align:right">HOLD</th><th style="{th};text-align:right">MOIC</th>
</tr></thead><tbody>{rows}</tbody></table></div>"""


def render_hold_analysis() -> str:
    corpus = _load_corpus()
    has_hold = [d for d in corpus if d.get("hold_years") is not None]
    has_both = [d for d in corpus if d.get("hold_years") is not None and d.get("realized_moic") is not None]

    holds = [d["hold_years"] for d in has_hold]
    moics_all = [d["realized_moic"] for d in has_both]

    hold_p50 = _percentile(holds, 50)
    hold_mean = sum(holds) / len(holds) if holds else None
    hold_p25  = _percentile(holds, 25)
    hold_p75  = _percentile(holds, 75)

    kpis = "".join(
        f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:8px 14px">'
        f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:3px">{lbl}</div>'
        f'<div style="font-size:16px;font-family:{_MONO};font-variant-numeric:tabular-nums;color:{P["text"]}">{val}</div>'
        f'</div>'
        for lbl, val in [
            ("CORPUS N",         str(len(corpus))),
            ("WITH HOLD DATA",   str(len(has_hold))),
            ("HOLD P25",         f"{hold_p25:.1f}y"  if hold_p25  else "—"),
            ("HOLD P50",         f"{hold_p50:.1f}y"  if hold_p50  else "—"),
            ("HOLD P75",         f"{hold_p75:.1f}y"  if hold_p75  else "—"),
            ("HOLD MEAN",        f"{hold_mean:.1f}y" if hold_mean else "—"),
        ]
    )
    kpi_strip = f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:16px">{kpis}</div>'

    scatter = _scatter_svg(has_both)
    histogram = _hold_histogram(has_hold)
    table = _bucket_table(has_both)
    outlier_table = _outliers_table(has_both)

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {ck_section_header("HOLD DURATION ANALYSIS", f"Hold period vs return relationship — {len(corpus)} corpus transactions", None)}
  {kpi_strip}

  <div style="display:grid;grid-template-columns:auto 1fr;gap:16px;margin-bottom:20px">
    <div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:10px">
      <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">HOLD (YEARS) vs REALIZED MOIC — SCATTER</div>
      <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:6px">Dashed line = 2.0× MOIC threshold. Green ≥2.5×, amber 2.0–2.5×, red &lt;2.0×.</div>
      {scatter}
    </div>
    <div>
      <div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:10px;margin-bottom:12px">
        <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">HOLD DURATION DISTRIBUTION</div>
        {histogram}
      </div>
      <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:6px">MOIC BY HOLD BUCKET</div>
      {table}
    </div>
  </div>

  <div>
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:6px;border-bottom:1px solid {P['border']};padding-bottom:4px">
      OUTLIERS — LONG HOLD (≥7y) WITH MOIC &lt;2.5×
    </div>
    {outlier_table}
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P['text_faint']};font-family:{_SANS}">
    Hold = realized holding period at exit. Win rate = deals with MOIC ≥ 2.0×. Outlier = hold ≥7y AND MOIC &lt;2.5×.
  </div>
</div>"""

    return chartis_shell(body, "Hold Duration Analysis", active_nav="/hold-analysis",
                         subtitle=f"{len(has_hold)} deals with hold data")
