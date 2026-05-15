"""IRR Dispersion Analysis — distribution of realized IRRs across the corpus.

Shows: IRR histogram, IRR vs MOIC scatter, IRR bucket stats,
sector IRR benchmarks, and MOIC/IRR consistency diagnostics.
"""
from __future__ import annotations

import html
import importlib
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional


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


from rcm_mc.ui._chartis_kit import (
    P, _MONO, _SANS, SafeHtml, chartis_shell, ck_fmt_num, ck_fmt_pct,
    ck_kpi_block, ck_paired_block, ck_provenance_tooltip,
    ck_section_header,
)


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _irr_histogram(irrs: List[float], w: int = 720, h: int = 260) -> str:
    """Histogram of IRR values in 5pp buckets.

    Uses viewBox + width 100% so the chart scales with container.
    The 20% hurdle line gets its own labelled gutter at the top of
    the chart instead of overlapping bars; bar bucket labels and
    counts have more breathing room at the larger size.
    """
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
    # Top padding now accommodates a hurdle-label gutter so the
    # dashed line label sits above the chart instead of overlapping
    # the tallest bars.
    pad_l, pad_r, pad_t, pad_b = 14, 14, 30, 36
    bar_w = (w - pad_l - pad_r) / len(counts)

    parts: List[str] = []
    for i, (cnt, lo) in enumerate(zip(counts, buckets[:-1])):
        bh = int(cnt / max_count * (h - pad_t - pad_b))
        x = pad_l + i * bar_w
        y = h - pad_b - bh
        col = P["positive"] if lo >= 20 else (P["warning"] if lo >= 10 else (P["negative"] if lo >= 0 else "#dc2626"))
        parts.append(
            f'<rect x="{x+2:.1f}" y="{y}" width="{bar_w-4:.1f}" '
            f'height="{bh}" fill="{col}" fill-opacity="0.85" rx="1"/>'
        )
        if cnt > 0:
            parts.append(
                f'<text x="{x+bar_w/2:.1f}" y="{y-4}" text-anchor="middle" '
                f'fill="{P["text_dim"]}" font-size="11" '
                f'font-family="{_MONO}">{cnt}</text>'
            )
        # Show every other bucket label at the larger width
        if i % 2 == 0:
            parts.append(
                f'<text x="{x+bar_w/2:.1f}" y="{h-12}" text-anchor="middle" '
                f'fill="{P["text_faint"]}" font-size="11" '
                f'font-family="{_MONO}">{lo}%</text>'
            )

    # 20% hurdle line with a clean labelled gutter above the bars.
    # Position by linear interpolation across the bucket range so the
    # line lands at the boundary between the 15-20 and 20-25 bars.
    hurdle_x = pad_l + (20 - buckets[0]) / (buckets[-1] - buckets[0]) * (w - pad_l - pad_r)
    # Tick mark (small horizontal flag) + label sit in the top gutter
    parts.append(
        f'<line x1="{hurdle_x:.1f}" y1="{pad_t-4}" '
        f'x2="{hurdle_x:.1f}" y2="{h-pad_b}" '
        f'stroke="{P["warning"]}" stroke-width="1.25" '
        f'stroke-dasharray="4,3"/>'
    )
    # Label pill — bone background with warning border, sits at the
    # top of the line so it never overlaps a bar.
    label_text = "20% HURDLE"
    label_w = 72
    label_x = max(pad_l, min(hurdle_x - label_w / 2, w - pad_r - label_w))
    parts.append(
        f'<rect x="{label_x:.1f}" y="6" width="{label_w}" height="18" '
        f'rx="2" fill="#ece5d6" stroke="{P["warning"]}" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{label_x + label_w/2:.1f}" y="19" text-anchor="middle" '
        f'fill="{P["warning"]}" font-size="10" '
        f'font-family="{_MONO}" font-weight="700" '
        f'letter-spacing="0.06em">{label_text}</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;height:auto;display:block;" '
        f'role="img" aria-label="IRR distribution histogram">'
        f'{"".join(parts)}</svg>'
    )


def _irr_moic_scatter(deals: List[Dict[str, Any]], w: int = 720, h: int = 460) -> str:
    """IRR (x) vs MOIC (y) scatter with consistency bands.

    Uses viewBox + width 100% so the chart scales with container.
    """
    points = [
        (d["realized_irr"], d["realized_moic"], d.get("hold_years"), d.get("deal_name",""))
        for d in deals
        if d.get("realized_irr") is not None and d.get("realized_moic") is not None
        and -0.3 <= d["realized_irr"] <= 0.8
    ]
    if not points:
        return ""

    pad_l, pad_r, pad_t, pad_b = 60, 20, 22, 44
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
        parts.append(
            f'<line x1="{px:.1f}" y1="{pad_t}" x2="{px:.1f}" y2="{h-pad_b}" '
            f'stroke="{P["border_dim"]}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{px:.1f}" y="{h-pad_b+18}" text-anchor="middle" '
            f'fill="{P["text_faint"]}" font-size="11" '
            f'font-family="{_MONO}">{pct}%</text>'
        )
    for mv in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        if mv <= moic_max:
            py = yp(mv)
            parts.append(
                f'<line x1="{pad_l}" y1="{py:.1f}" x2="{w-pad_r}" y2="{py:.1f}" '
                f'stroke="{P["border_dim"]}" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{pad_l-6}" y="{py+4:.1f}" text-anchor="end" '
                f'fill="{P["text_faint"]}" font-size="11" '
                f'font-family="{_MONO}">{mv:.1f}×</text>'
            )

    # 20% hurdle vertical
    px20 = xp(0.20)
    parts.append(
        f'<line x1="{px20:.1f}" y1="{pad_t}" x2="{px20:.1f}" y2="{h-pad_b}" '
        f'stroke="{P["warning"]}" stroke-width="1.25" stroke-dasharray="4,3"/>'
    )
    # 2.0x horizontal
    if moic_min <= 2.0 <= moic_max:
        py2 = yp(2.0)
        parts.append(
            f'<line x1="{pad_l}" y1="{py2:.1f}" x2="{w-pad_r}" y2="{py2:.1f}" '
            f'stroke="{P["warning"]}" stroke-width="1.25" stroke-dasharray="4,3"/>'
        )

    for irr, moic, hold, name in points:
        cx = xp(irr)
        cy = yp(moic)
        col = P["positive"] if irr >= 0.20 and moic >= 2.0 else (P["negative"] if irr < 0.15 or moic < 1.5 else P["warning"])
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{col}" '
            f'fill-opacity="0.65" stroke="{col}" stroke-width="0.75">'
            f'<title>{html.escape(name[:40])}: IRR {irr*100:.1f}%, '
            f'MOIC {moic:.2f}×</title></circle>'
        )

    parts.append(
        f'<text x="{pad_l+cw//2}" y="{h-6}" text-anchor="middle" '
        f'fill="{P["text_dim"]}" font-size="12" '
        f'font-family="{_SANS}">Realized IRR</text>'
    )
    parts.append(
        f'<text x="16" y="{pad_t+ch//2}" text-anchor="middle" '
        f'fill="{P["text_dim"]}" font-size="12" font-family="{_SANS}" '
        f'transform="rotate(-90,16,{pad_t+ch//2})">MOIC</text>'
    )

    return (
        f'<svg viewBox="0 0 {w} {h}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;height:auto;display:block;" '
        f'role="img" aria-label="IRR vs MOIC scatter">'
        f'{"".join(parts)}</svg>'
    )


def _sector_irr_rows(corpus: List[Dict[str, Any]]) -> tuple:
    """Sector-IRR data for the IRR histogram's paired dataset.

    Returns ``(headers, rows, hot_rows)`` for ``ck_paired_block``.
    Filters to sectors with >=3 realized-IRR observations and sorts
    by P50 IRR descending — so ``hot_rows=[0]`` marks the top sector.
    Caps at 20 rows (same cap as the prior table). Superseded the
    pre-rendered ``_sector_irr_table`` when /irr-dispersion adopted
    the handoff's paired viz+dataset primitive.
    """
    sectors: Dict[str, List[float]] = defaultdict(list)
    for d in corpus:
        if d.get("sector") and d.get("realized_irr") is not None:
            sectors[d["sector"]].append(d["realized_irr"])
    rows_data = [
        (sec, irrs) for sec, irrs in sectors.items() if len(irrs) >= 3
    ]
    rows_data.sort(key=lambda x: -(_percentile(x[1], 50) or 0))

    headers = [
        "Sector", "N", "IRR P25", "IRR P50", "IRR P75", ">20% hurdle",
    ]
    rows: list = []
    for sec, irrs in rows_data[:20]:
        p25 = _percentile(irrs, 25)
        p50 = _percentile(irrs, 50)
        p75 = _percentile(irrs, 75)
        above = sum(1 for v in irrs if v >= 0.20) / len(irrs) * 100
        rows.append([
            sec[:30],
            str(len(irrs)),
            f"{p25 * 100:.1f}%" if p25 else "—",
            f"{p50 * 100:.1f}%" if p50 else "—",
            f"{p75 * 100:.1f}%" if p75 else "—",
            f"{above:.0f}%",
        ])
    return headers, rows, ([0] if rows else [])


def render_irr_dispersion() -> str:
    corpus = _load_corpus()
    has_irr  = [d for d in corpus if d.get("realized_irr") is not None]
    has_both = [d for d in corpus if d.get("realized_irr") is not None and d.get("realized_moic") is not None]

    irrs  = [d["realized_irr"] for d in has_irr]
    irr_p25 = _percentile(irrs, 25)
    irr_p50 = _percentile(irrs, 50)
    irr_p75 = _percentile(irrs, 75)
    above_hurdle = sum(1 for v in irrs if v >= 0.20) / len(irrs) * 100 if irrs else 0

    # Cycle 42 — port bespoke KPI cards to ck_kpi_block + provenance.
    p50_color = P["positive"] if (irr_p50 or 0) >= 0.20 else P["warning"]
    hurdle_color = P["positive"] if above_hurdle >= 50 else P["warning"]
    p50_value = ck_provenance_tooltip(
        "Realized IRR P50",
        SafeHtml(f'<span style="color:{p50_color}">{ck_fmt_pct(irr_p50)}</span>')
        if irr_p50 else "—",
        explainer=(
            "Median realized internal rate of return at exit "
            "across the corpus deals with disclosed IRR. 20% is "
            "the canonical hurdle - below that the deal didn't "
            "earn carry; well above is the long-tail driving fund "
            "performance."
        ),
    )
    hurdle_value = ck_provenance_tooltip(
        "Above 20% hurdle rate",
        SafeHtml(f'<span style="color:{hurdle_color}">{above_hurdle:.0f}%</span>'),
        explainer=(
            "Share of corpus deals that exited above 20% IRR. "
            "Closer to 50% is healthy across a healthcare PE "
            "vintage; below 30% means the fund is leaning "
            "heavily on a small number of breakouts."
        ),
        inject_css=False,
    )
    kpi_strip = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:16px;">'
        + ck_kpi_block("With IRR Data", ck_fmt_num(len(has_irr)), "of corpus")
        + ck_kpi_block("IRR P25", ck_fmt_pct(irr_p25) if irr_p25 else "—", "lower quartile")
        + ck_kpi_block("IRR P50", p50_value, "median")
        + ck_kpi_block("IRR P75", ck_fmt_pct(irr_p75) if irr_p75 else "—", "upper quartile")
        + ck_kpi_block(">=20% Hurdle", hurdle_value, "share above hurdle")
        + '</div>'
    )

    histogram = _irr_histogram(irrs)
    scatter = _irr_moic_scatter(has_both)
    # Signature paired viz+dataset block: IRR distribution (viz) on
    # the left, its per-sector breakdown on the right, one rule. The
    # histogram is the overall corpus distribution; the sector table
    # is the same corpus sliced — the handoff's pairing intent.
    hist_viz = (
        '<div style="font-family:var(--sc-mono);font-size:9px;'
        'letter-spacing:0.1em;text-transform:uppercase;'
        'color:var(--sc-text-faint);margin-bottom:8px;">'
        'IRR distribution &middot; 5pp buckets</div>'
        f'{histogram}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;">'
        'Dashed = 20% hurdle. Green = above hurdle, '
        'amber 10&ndash;20%, red &lt;10%.</div>'
    )
    sec_headers, sec_rows, sec_hot = _sector_irr_rows(corpus)
    irr_paired = ck_paired_block(
        hist_viz,
        data_label="IRR by sector &middot; >=3 realized deals",
        data_source="deals corpus",
        headers=sec_headers,
        rows=sec_rows,
        hot_rows=sec_hot,
    )

    chart_card_style = (
        f"background:{P['panel_alt']};border:1px solid {P['border']};"
        "padding:18px 20px 20px;border-radius:2px;"
    )
    chart_eyebrow_style = (
        f"font-size:11px;color:{P['text_dim']};font-family:{_MONO};"
        "letter-spacing:0.1em;text-transform:uppercase;font-weight:700;"
        "margin-bottom:8px;"
    )
    chart_caption_style = (
        f"font-size:12px;color:{P['text_faint']};font-family:{_SANS};"
        "line-height:1.5;margin-bottom:14px;"
    )
    body = f"""
<div>
  {ck_section_header("IRR DISPERSION ANALYSIS", f"Realized IRR distribution — {len(corpus)} corpus transactions", None)}
  {kpi_strip}

  {irr_paired}

  <div style="{chart_card_style};margin-top:24px;">
    <div style="{chart_eyebrow_style}">IRR vs MOIC SCATTER — CONSISTENCY CHECK</div>
    <div style="{chart_caption_style}">Dashed lines mark the 20% IRR hurdle and 2.0× MOIC threshold.</div>
    {scatter}
  </div>
  <div style="margin-top:14px;font-size:11px;color:{P['text_faint']};font-family:{_SANS};line-height:1.5">
    IRR = realized internal rate of return at exit as disclosed. Above hurdle = IRR ≥ 20%. Corpus: {len(corpus)} transactions.
  </div>
</div>"""

    return chartis_shell(body, "IRR Dispersion", active_nav="/irr-dispersion",
                         subtitle=f"{len(has_irr)} deals with IRR data",
        editorial_intro={
            "eyebrow": "IRR DISPERSION",
            "headline": "Where the realized returns split apart.",
            "italic_word": "split",
            "body": (
                f"IRR distribution across {len(has_irr)} realized "
                f"corpus deals — quartile cuts and the long tail "
                f"that drives fund performance. Use this to set "
                f"realistic IRR expectations for the current deal "
                f"based on its archetype neighbors."
            ),
        })
