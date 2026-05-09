"""IRR Dispersion Analysis — distribution of realized IRRs across the corpus.

Shows: IRR histogram, IRR vs MOIC scatter, IRR bucket stats,
sector IRR benchmarks, and MOIC/IRR consistency diagnostics.
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
from rcm_mc.data_public.sector_smoothing import (
    bayesian_smooth,
    realization_rate,
    shrinkage_weight,
)


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _irr_histogram(irrs: List[float], w: int = 360, h: int = 100) -> str:
    """Histogram of IRR values in 5pp buckets."""
    if not irrs:
        return ""
    irr_pct = [v * 100 for v in irrs]
    buckets = list(range(-10, 65, 5))
    counts = [0] * (len(buckets) - 1)
    for v in irr_pct:
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
        col = P["positive"] if lo >= 20 else (P["warning"] if lo >= 10 else (P["negative"] if lo >= 0 else "#dc2626"))
        parts.append(f'<rect x="{x+1:.1f}" y="{y}" width="{bar_w-2:.1f}" height="{bh}" fill="{col}" fill-opacity="0.8"/>')
        if cnt > 0:
            parts.append(f'<text x="{x+bar_w/2:.1f}" y="{y-2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="7" font-family="{_MONO}">{cnt}</text>')
        if i % 2 == 0:
            parts.append(f'<text x="{x+bar_w/2:.1f}" y="{h-5}" text-anchor="middle" fill="{P["text_faint"]}" font-size="7" font-family="{_MONO}">{lo}%</text>')

    # 20% hurdle line
    hurdle_x = pad_l + (20 - buckets[0]) / (buckets[-1] - buckets[0]) * (w - pad_l - pad_r)
    parts.append(f'<line x1="{hurdle_x:.1f}" y1="{pad_t}" x2="{hurdle_x:.1f}" y2="{h-pad_b}" stroke="{P["warning"]}" stroke-width="1.5" stroke-dasharray="3,2"/>')
    parts.append(f'<text x="{hurdle_x+3:.1f}" y="{pad_t+10}" fill="{P["warning"]}" font-size="8" font-family="{_SANS}">20% hurdle</text>')

    return f'<svg width="{w}" height="{h}">{"".join(parts)}</svg>'


def _irr_moic_scatter(deals: List[Dict[str, Any]], w: int = 320, h: int = 240) -> str:
    """IRR (x) vs MOIC (y) scatter with consistency bands."""
    points = [
        (d["realized_irr"], d["realized_moic"], d.get("hold_years"), d.get("deal_name",""))
        for d in deals
        if d.get("realized_irr") is not None and d.get("realized_moic") is not None
        and -0.3 <= d["realized_irr"] <= 0.8
    ]
    if not points:
        return ""

    pad_l, pad_r, pad_t, pad_b = 36, 12, 12, 24
    cw, ch = w - pad_l - pad_r, h - pad_t - pad_b

    irr_min, irr_max = -0.05, 0.65
    moic_min, moic_max = 0.5, max(p[1] for p in points) * 1.05

    def xp(v: float) -> float:
        return pad_l + (v - irr_min) / (irr_max - irr_min) * cw

    def yp(v: float) -> float:
        return pad_t + (moic_max - v) / (moic_max - moic_min) * ch

    parts: List[str] = []
    # grid
    for pct in [0, 10, 20, 30, 40, 50, 60]:
        px = xp(pct / 100)
        parts.append(f'<line x1="{px:.1f}" y1="{pad_t}" x2="{px:.1f}" y2="{h-pad_b}" stroke="{P["border_dim"]}" stroke-width="1"/>')
        parts.append(f'<text x="{px:.1f}" y="{h-pad_b+10}" text-anchor="middle" fill="{P["text_faint"]}" font-size="7" font-family="{_MONO}">{pct}%</text>')
    for mv in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        if mv <= moic_max:
            py = yp(mv)
            parts.append(f'<line x1="{pad_l}" y1="{py:.1f}" x2="{w-pad_r}" y2="{py:.1f}" stroke="{P["border_dim"]}" stroke-width="1"/>')
            parts.append(f'<text x="{pad_l-3}" y="{py+3:.1f}" text-anchor="end" fill="{P["text_faint"]}" font-size="7" font-family="{_MONO}">{mv:.1f}×</text>')

    # 20% hurdle vertical
    px20 = xp(0.20)
    parts.append(f'<line x1="{px20:.1f}" y1="{pad_t}" x2="{px20:.1f}" y2="{h-pad_b}" stroke="{P["warning"]}" stroke-width="1" stroke-dasharray="3,2"/>')
    # 2.0x horizontal
    if moic_min <= 2.0 <= moic_max:
        py2 = yp(2.0)
        parts.append(f'<line x1="{pad_l}" y1="{py2:.1f}" x2="{w-pad_r}" y2="{py2:.1f}" stroke="{P["warning"]}" stroke-width="1" stroke-dasharray="3,2"/>')

    for irr, moic, hold, name in points:
        cx = xp(irr)
        cy = yp(moic)
        col = P["positive"] if irr >= 0.20 and moic >= 2.0 else (P["negative"] if irr < 0.15 or moic < 1.5 else P["warning"])
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{col}" fill-opacity="0.65" stroke="{col}" stroke-width="0.5"><title>{html.escape(name[:40])}: IRR {irr*100:.1f}%, MOIC {moic:.2f}×</title></circle>')

    parts.append(f'<text x="{pad_l+cw//2}" y="{h-2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="8" font-family="{_SANS}">Realized IRR</text>')
    parts.append(f'<text x="10" y="{pad_t+ch//2}" text-anchor="middle" fill="{P["text_dim"]}" font-size="8" font-family="{_SANS}" transform="rotate(-90,10,{pad_t+ch//2})">MOIC</text>')

    return f'<svg width="{w}" height="{h}">{"".join(parts)}</svg>'


def _sector_irr_table(corpus: List[Dict[str, Any]]) -> str:
    # Group all corpus deals by sector (not just disclosed-IRR ones)
    # so the survivor-bias / realization-rate diagnostic can be
    # computed honestly. The published IRR distribution still uses
    # only the disclosed-IRR subset, but every row carries a
    # "realized X / N (Y%)" cell so the partner sees what fraction
    # of the sector actually surfaced returns vs how much is silent.
    sector_deals: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in corpus:
        if d.get("sector"):
            sector_deals[d["sector"]].append(d)

    # Corpus-wide IRR prior — used for Bayesian smoothing of small-N
    # sector quantiles. Computed on disclosed-IRR deals only since
    # that's the population the per-sector P50 is drawn from.
    all_disclosed_irrs = [
        d["realized_irr"] for d in corpus if d.get("realized_irr") is not None
    ]
    corpus_irr_p50_prior = _percentile(all_disclosed_irrs, 50)

    # Tighten the publishable threshold from N≥3 to N≥5 disclosed-IRR
    # deals — three is too few to defend a quantile in IC, and the
    # 24% median that surfaced with N=3 thresholds was driven by
    # noise on thin sectors. The footer notes how many sectors got
    # suppressed under the new threshold.
    rows_data: List[Tuple[str, List[float], List[Dict[str, Any]]]] = []
    suppressed_low_n = 0
    for sec, all_deals in sector_deals.items():
        irrs = [d["realized_irr"] for d in all_deals if d.get("realized_irr") is not None]
        if len(irrs) < 5:
            if len(irrs) >= 1:
                suppressed_low_n += 1
            continue
        rows_data.append((sec, irrs, all_deals))
    # Sort by smoothed P50 so high-noise small-N sectors don't top
    # the list with raw outliers.
    rows_data.sort(
        key=lambda x: -(
            bayesian_smooth(_percentile(x[1], 50), len(x[1]), corpus_irr_p50_prior) or 0
        ),
    )

    rows = ""
    for i, (sec, irrs, all_deals) in enumerate(rows_data[:20]):
        bg = P.get("row_stripe", P.get("panel_alt", "#ece6db")) if i % 2 else P["panel"]
        n = len(irrs)
        raw_p50 = _percentile(irrs, 50)
        p25 = _percentile(irrs, 25)
        p75 = _percentile(irrs, 75)
        # Smoothed P50 — pulled toward corpus prior on small N.
        p50 = bayesian_smooth(raw_p50, n, corpus_irr_p50_prior)
        shrink = shrinkage_weight(n) * 100
        shrink_badge = (
            f' <span style="font-size:8px;color:{P["text_faint"]};font-family:{_MONO};">'
            f'(shrunk {shrink:.1f}%)</span>'
            if shrink >= 30 else ""
        )
        above_hurdle = sum(1 for v in irrs if v >= 0.20) / len(irrs) * 100
        col = P["positive"] if (p50 or 0) >= 0.20 else (P["warning"] if (p50 or 0) >= 0.12 else P["negative"])
        # Survivor-bias diagnostic: realized / total in this sector.
        realized, total, real_pct = realization_rate(all_deals)
        real_color = (
            P["positive"] if real_pct >= 60
            else P["warning"] if real_pct >= 30
            else P.get("negative", "#b5321e")
        )
        rows += (
            f'<tr style="background:{bg}">'
            f'<td style="padding:4px 8px;font-size:11px">{html.escape(sec[:30])}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{n}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{real_color};font-variant-numeric:tabular-nums">{realized}/{total} ({real_pct:.1f}%)</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{f"{p25*100:.1f}%" if p25 else "—"}</td>'
            f'<td style="padding:4px 8px;font-size:12px;font-family:{_MONO};text-align:right;font-weight:700;color:{col};font-variant-numeric:tabular-nums">{(f"{p50*100:.1f}%" + shrink_badge) if p50 else "—"}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{f"{p75*100:.1f}%" if p75 else "—"}</td>'
            f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{above_hurdle:.1f}%</td>'
            f'</tr>'
        )

    th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P.get('border', P.get('rule', '#d6cfc3'))}"
    suppressed_note = (
        f'<div style="font-size:10px;color:{P.get("warning", "#b8732a")};'
        f'font-family:{_SANS};margin-top:6px;">'
        f'{suppressed_low_n} sector(s) with 1–4 disclosed IRRs suppressed — '
        f'too thin to defend a published quantile.</div>'
        if suppressed_low_n else ""
    )
    return f"""<div style="border:1px solid {P.get('border', P.get('rule', '#d6cfc3'))};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th}">SECTOR</th>
  <th style="{th};text-align:right">N (IRR)</th>
  <th style="{th};text-align:right">REALIZED</th>
  <th style="{th};text-align:right">IRR P25</th>
  <th style="{th};text-align:right">IRR P50 (smoothed)</th>
  <th style="{th};text-align:right">IRR P75</th>
  <th style="{th};text-align:right">&gt;20% HURDLE</th>
</tr></thead>
<tbody>{rows}</tbody>
</table></div>{suppressed_note}"""


def render_irr_dispersion() -> str:
    corpus = _load_corpus()
    has_irr  = [d for d in corpus if d.get("realized_irr") is not None]
    has_both = [d for d in corpus if d.get("realized_irr") is not None and d.get("realized_moic") is not None]

    irrs  = [d["realized_irr"] for d in has_irr]
    irr_p25 = _percentile(irrs, 25)
    irr_p50 = _percentile(irrs, 50)
    irr_p75 = _percentile(irrs, 75)
    above_hurdle = sum(1 for v in irrs if v >= 0.20) / len(irrs) * 100 if irrs else 0

    # Survivor-bias diagnostic at the corpus level. The previous
    # KPI strip showed only "WITH IRR DATA" — the more useful
    # framing is "X of Y deals have a disclosed IRR (Z%)" so the
    # partner sees up front that the displayed P50 IRR is computed
    # against a self-selected sample. The 24% median that prompted
    # the audit was driven by exactly this filter (winners are
    # disclosed; failures and ongoing positions are silent).
    realized_irr_pct = (len(has_irr) / len(corpus) * 100) if corpus else 0
    survivor_color = (
        P["positive"] if realized_irr_pct >= 60
        else P["warning"] if realized_irr_pct >= 30
        else P.get("negative", "#b5321e")
    )

    kpis = "".join(
        f'<div style="background:{P["panel_alt"]};border:1px solid {P.get("border", P.get("rule", "#d6cfc3"))};padding:8px 14px">'
        f'<div style="font-size:9px;color:{P["text_dim"]};font-family:{_SANS};letter-spacing:.08em;margin-bottom:3px">{lbl}</div>'
        f'<div style="font-size:16px;font-family:{_MONO};font-variant-numeric:tabular-nums;color:{col}">{val}</div>'
        f'</div>'
        for lbl, val, col in [
            ("CORPUS N",         str(len(corpus)),                                  P["text"]),
            ("DISCLOSED IRR",    f"{len(has_irr)} ({realized_irr_pct:.1f}%)",       survivor_color),
            ("IRR P25",          f"{irr_p25*100:.1f}%" if irr_p25 else "—",          P["text"]),
            ("IRR P50",          f"{irr_p50*100:.1f}%" if irr_p50 else "—",          P["positive"] if (irr_p50 or 0) >= 0.20 else P["warning"]),
            ("IRR P75",          f"{irr_p75*100:.1f}%" if irr_p75 else "—",          P["text"]),
            ("≥20% HURDLE RATE", f"{above_hurdle:.0f}%",                              P["positive"] if above_hurdle >= 50 else P["warning"]),
        ]
    )
    kpi_strip = f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:8px">{kpis}</div>'

    # Survivor-bias caveat — surfaces the structural reason behind
    # the 24% median IRR figure flagged in the partner audit.
    survivor_note = (
        f'<div style="background:{P["panel_alt"]};'
        f'border:1px solid {P.get("border", P.get("rule", "#d6cfc3"))};'
        f'border-left:3px solid {survivor_color};'
        f'padding:8px 14px;margin-bottom:16px;font-size:11px;'
        f'color:{P["text_dim"]};font-family:{_SANS};line-height:1.5">'
        f'<span style="color:{P["text"]};font-weight:600;">Survivor bias caveat:</span> '
        f'IRR is disclosed for <b>{realized_irr_pct:.1f}%</b> of the corpus '
        f'({len(has_irr)} of {len(corpus)} deals). The remaining {len(corpus) - len(has_irr)} deals '
        f'are typically ongoing holds, undisclosed exits, or quietly written-down positions — '
        f'systematically tilted toward negative outcomes. The P50 IRR shown above is computed against '
        f'the disclosed-IRR subset only, so it over-states the true corpus-wide median by the share of '
        f'failures excluded. Per-sector quantiles below pair every benchmark with its sector-level '
        f'realization rate so the survivor effect is auditable.'
        f'</div>'
    )

    histogram = _irr_histogram(irrs)
    scatter = _irr_moic_scatter(has_both)
    sector_table = _sector_irr_table(corpus)

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {ck_section_header("IRR DISPERSION ANALYSIS", f"Realized IRR distribution — {len(corpus)} corpus transactions", None)}
  {kpi_strip}
  {survivor_note}

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px">
    <div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:10px">
      <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">IRR DISTRIBUTION — 5pp BUCKETS</div>
      <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:6px">Dashed line = 20% hurdle rate. Green = above hurdle, amber = 10–20%, red = below 10%.</div>
      {histogram}
    </div>
    <div style="background:{P['panel_alt']};border:1px solid {P['border']};padding:10px">
      <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.08em;margin-bottom:8px">IRR vs MOIC SCATTER — CONSISTENCY CHECK</div>
      <div style="font-size:9px;color:{P['text_faint']};font-family:{_SANS};margin-bottom:6px">Dashed lines = 20% IRR hurdle + 2.0× MOIC threshold.</div>
      {scatter}
    </div>
  </div>

  <div>
    <div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:6px;border-bottom:1px solid {P['border']};padding-bottom:4px">
      IRR BY SECTOR — P25 / P50 / P75 (min 3 deals with disclosed IRR)
    </div>
    {sector_table}
  </div>
  <div style="margin-top:8px;font-size:10px;color:{P['text_faint']};font-family:{_SANS}">
    IRR = realized internal rate of return at exit as disclosed. Above hurdle = IRR ≥ 20%. Corpus: 720 transactions.
  </div>
</div>"""

    return chartis_shell(body, "IRR Dispersion", active_nav="/irr-dispersion",
                         subtitle=f"{len(has_irr)} deals with IRR data")
