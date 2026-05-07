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
    from rcm_mc.data_public.hold_precision_overlay import apply_hold_precision
    deals: List[Dict[str, Any]] = list(_SEED_DEALS)
    for i in range(2, 38):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            key = f"EXTENDED_SEED_DEALS_{i}"
            deals += getattr(mod, key, [])
        except Exception:
            pass
    # Phase 3C: apply month-precision overlay so percentile aggregation
    # doesn't collide on integer-year clusters (the partner-visible
    # symptom: P25 = P50 = 4.0y, which looked like a calculation
    # error). Overlay covers marquee deals only; remainder retain
    # integer-year precision and are flagged accordingly.
    return apply_hold_precision(deals)


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

    # Buckets are right-open at the top to keep edge cases on the right.
    # A trailing 20y+ bucket catches multi-decade restructurings (e.g.
    # Steward's 13.5y and a handful of family-office holds) that the
    # original 0–20 cap silently dropped. After this change every hold
    # in ``deals`` lands in exactly one bucket: bucket totals sum to
    # ``len(holds)`` and the histogram N matches the partner-displayed
    # "with hold data" count, eliminating the previous chart-vs-KPI
    # discrepancy.
    buckets = [
        (0, 2, "<2y"),
        (2, 4, "2–4y"),
        (4, 6, "4–6y"),
        (6, 8, "6–8y"),
        (8, 12, "8–12y"),
        (12, 1000, "12y+"),
    ]
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
    # Buckets are continuous and bounded: every deal with hold + MOIC
    # lands in exactly one bucket. The trailing 12y+ bucket catches
    # multi-decade restructuring holds (Steward, IASIS, prior-era
    # GME-heavy deals) that the original 7-99 ceiling lumped into a
    # single "Extended" group. After this change the bucket Ns sum
    # exactly to len(deals_with_both) — the bug where the table
    # totalled to 168 against a histogram of 328 collapsed because
    # the former filtered to deals-with-MOIC and the latter to
    # deals-with-hold; both are now explicitly labelled.
    buckets = [
        ("Short (<3y)",      0,    3),
        ("Medium (3–5y)",    3,    5),
        ("Long (5–7y)",      5,    7),
        ("Extended (7–12y)", 7,   12),
        ("Restructured (12y+)", 12, 1000),
    ]

    rows = ""
    bucket_total = 0
    for lbl, lo, hi in buckets:
        group = [d for d in deals if d.get("hold_years") is not None and lo <= d["hold_years"] < hi]
        bucket_total += len(group)
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

    # Total row — partner-visible reconciliation that the bucket Ns
    # sum exactly to the input dataset size, no silent drops.
    n_input = sum(
        1 for d in deals
        if d.get("hold_years") is not None and d.get("realized_moic") is not None
    )
    diff = n_input - bucket_total
    rows += (
        f'<tr style="background:{P["panel_alt"]};font-weight:700;border-top:2px solid {P["border"]}">'
        f'<td style="padding:6px 8px;font-size:11px;font-family:{_SANS};letter-spacing:.06em;text-transform:uppercase">Total</td>'
        f'<td style="padding:6px 8px;font-size:11px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{bucket_total}'
        + (f' <span style="color:{P["negative"]};font-size:9px">({diff:+d} unbucketed)</span>' if diff != 0 else '')
        + f'</td>'
        f'<td colspan="5"></td></tr>'
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
    # Two-track outlier definition:
    #   (a) Long hold + sub-threshold MOIC — the original "stuck" deals.
    #   (b) Loss outcomes regardless of hold — MOIC <= 1.0 with negative
    #       IRR. Catches Envision (4.6y, 0.05× MOIC, -44% IRR) which
    #       the original hold-≥7y filter excluded; Envision is one of
    #       the canonical cautionary deals partners expect to see in
    #       any hold-vs-return analysis.
    long_stuck = [
        d for d in deals
        if d.get("hold_years") is not None and d.get("realized_moic") is not None
        and (d["hold_years"] >= 7 and d["realized_moic"] < 2.5)
    ]
    loss = [
        d for d in deals
        if d.get("hold_years") is not None and d.get("realized_moic") is not None
        and d["realized_moic"] <= 1.0
        and (d.get("realized_irr") is None or d["realized_irr"] < 0)
        and d not in long_stuck
    ]
    outliers = long_stuck + loss
    # Sort by stuckness (hold / max(MOIC, 0.01)). Loss deals with
    # MOIC≈0 push to the top, where they belong.
    outliers.sort(
        key=lambda d: d["hold_years"] / max(d["realized_moic"], 0.01),
        reverse=True,
    )

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
    from rcm_mc.data_public.hold_precision_overlay import hold_precision_summary

    corpus = _load_corpus()
    has_hold = [d for d in corpus if d.get("hold_years") is not None]
    has_both = [d for d in corpus if d.get("hold_years") is not None and d.get("realized_moic") is not None]

    holds = [d["hold_years"] for d in has_hold]

    # Phase 3C: percentile precision is now reported to 2 decimals.
    # The integer-year clusters in the seed corpus produced spurious
    # P25=P50=4.0 collisions; the month-precision overlay (covering
    # marquee deals) plus the 2-decimal display means clusters now
    # surface as 4.27 / 4.83 rather than 4.0 / 4.0.
    hold_p50 = _percentile(holds, 50)
    hold_mean = sum(holds) / len(holds) if holds else None
    hold_p25  = _percentile(holds, 25)
    hold_p75  = _percentile(holds, 75)

    # Reconcile the three N counts that were silently disagreeing:
    #   total corpus (all entries, used by header subtitle),
    #   with hold data (drives histogram, percentiles),
    #   with both hold + MOIC (drives scatter, bucket table, outliers).
    n_corpus = len(corpus)
    n_hold = len(has_hold)
    n_both = len(has_both)
    n_no_hold = n_corpus - n_hold
    n_hold_no_moic = n_hold - n_both

    precision = hold_precision_summary(corpus)

    kpis = "".join(
        f'<div style="background:{P["panel_alt"]};border:1px solid {P["border"]};padding:8px 14px">'
        f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:3px">{lbl}</div>'
        f'<div style="font-size:16px;font-family:{_MONO};font-variant-numeric:tabular-nums;color:{P["text"]}">{val}</div>'
        f'</div>'
        for lbl, val in [
            ("CORPUS N",         str(n_corpus)),
            ("WITH HOLD DATA",   str(n_hold)),
            ("HOLD + MOIC",      str(n_both)),
            ("HOLD P25",         f"{hold_p25:.2f}y"  if hold_p25  is not None else "—"),
            ("HOLD P50",         f"{hold_p50:.2f}y"  if hold_p50  is not None else "—"),
            ("HOLD MEAN",        f"{hold_mean:.2f}y" if hold_mean is not None else "—"),
        ]
    )
    kpi_strip = f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:12px">{kpis}</div>'

    # Coverage panel — explicit reconciliation of where the corpus N
    # gets filtered. Without this the partner sees three different
    # totals (header subtitle, histogram, table) and assumes the
    # numbers are wrong; in fact each chart applies a different
    # filter and the discrepancy is structural, not arithmetic.
    coverage_pct_hold = (n_hold / n_corpus * 100) if n_corpus else 0
    coverage_pct_both = (n_both / n_corpus * 100) if n_corpus else 0

    # When the bulk of hold values cluster at integer years, P25 and
    # P50 can land on the same value — that's a real clustering
    # signal, not a calculation bug. Surface it explicitly so the
    # partner reads the equality as data structure rather than as
    # a broken aggregation.
    cluster_note = ""
    if (
        hold_p25 is not None and hold_p50 is not None
        and abs(hold_p25 - hold_p50) < 1e-6
    ):
        cluster_pt = round(float(hold_p50), 2)
        cluster_n = sum(1 for h in holds if abs(h - cluster_pt) < 0.5)
        cluster_note = (
            f' <span style="color:{P.get("warning", "#b8732a")};">'
            f'P25 = P50 = {cluster_pt:.2f}y reflects integer-year '
            f'clustering: {cluster_n} of {len(holds)} deals report '
            f'hold within ±0.5y of {cluster_pt:.0f}y. Month-precision '
            f'overlay covers {precision["month"]} marquee deals; '
            f'sub-year resolution is unavailable for the rest.</span>'
        )

    coverage_panel = (
        f'<div style="background:{P.get("panel_alt", "#ece6db")};'
        f'border:1px solid {P.get("border", P.get("rule", "#d6cfc3"))};'
        f'padding:8px 14px;margin-bottom:16px;font-size:11px;'
        f'color:{P.get("text_dim", "#465366")};font-family:{_SANS};">'
        f'<span style="color:{P["text"]};font-weight:600;">Sample-size reconciliation:</span> '
        f'<b>{n_corpus}</b> total corpus deals · '
        f'<b>{n_hold}</b> with hold data ({coverage_pct_hold:.0f}%; histogram N) · '
        f'<b>{n_both}</b> with hold + realized MOIC ({coverage_pct_both:.0f}%; scatter + bucket-table N) · '
        f'<b>{n_no_hold}</b> ongoing or undisclosed hold · '
        f'<b>{n_hold_no_moic}</b> hold without realized MOIC. '
        f'Hold precision: <b>{precision["month"]}</b> month-precision (public records), '
        f'<b>{precision["year"]}</b> integer-year approximation.'
        f'{cluster_note}'
        f'</div>'
    )

    scatter = _scatter_svg(has_both)
    histogram = _hold_histogram(has_hold)
    table = _bucket_table(has_both)
    outlier_table = _outliers_table(has_both)

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {ck_section_header("HOLD DURATION ANALYSIS", f"Hold period vs return relationship — {n_corpus} corpus transactions", None)}
  {kpi_strip}
  {coverage_panel}

  <div style="display:grid;grid-template-columns:auto 1fr;gap:16px;margin-bottom:20px">
    <div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:10px">
      <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">HOLD (YEARS) vs REALIZED MOIC — SCATTER · N={n_both}</div>
      <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:6px">Dashed line = 2.0× MOIC threshold. Green ≥2.5×, amber 2.0–2.5×, red &lt;2.0×.</div>
      {scatter}
    </div>
    <div>
      <div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:10px;margin-bottom:12px">
        <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">HOLD DURATION DISTRIBUTION · N={n_hold}</div>
        {histogram}
      </div>
      <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:6px">MOIC BY HOLD BUCKET · N={n_both}</div>
      {table}
    </div>
  </div>

  <div>
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:6px;border-bottom:1px solid {P['border']};padding-bottom:4px">
      OUTLIERS — LONG HOLD (≥7y AND MOIC &lt;2.5×) OR REALIZED LOSS (MOIC ≤1.0× AND IRR &lt;0)
    </div>
    {outlier_table}
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P['text_faint']};font-family:{_SANS}">
    Hold = realized holding period at exit (or at Chapter 11 filing where equity was zero'd; e.g. Envision May 2023, Steward May 2024).
    Win rate = deals with MOIC ≥ 2.0×. Outlier criteria expanded to include realized losses regardless of hold,
    so canonical cautionary deals (Steward, Envision) appear in the same panel partners reach for during IC.
  </div>
</div>"""

    return chartis_shell(body, "Hold Duration Analysis", active_nav="/hold-analysis",
                         subtitle=f"{n_corpus} corpus deals · {n_hold} with hold · {n_both} with hold + MOIC")
