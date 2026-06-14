"""Zero-dep SVG chart generators for the Deal MC result.

Each function takes the DealMCResult (or a slice of it) and returns
an SVG string that renders inline in the UI. No numpy, no
matplotlib, no plotly — pure string templates. Palette is the
editorial chartis (navy ink axis, teal-ink median line, parchment
rule grid) — was originally Bloomberg-dark-mode, which rendered as
light text on the cream parchment background and the user reported
as illegible. Default chart size bumped (640×280 → 920×360) so the
fan + histogram + tornado read at typical viewing distance.
"""
from __future__ import annotations

import itertools
from typing import Any, List, Optional, Sequence, Tuple

from .engine import DealMCResult, StressResult, YearBand

# Editorial type stack — the inline charts used to label everything in
# "Helvetica Neue, Arial" (a browser default that reads as an unstyled
# Excel export). These match the platform's on-screen identity: Source
# Serif for the display kicker, Inter Tight for axis/labels, JetBrains
# Mono for numerics, so the SVG charts look like the rest of the deck.
_SERIF = "Source Serif 4, Georgia, 'Times New Roman', serif"
_SANS = "Inter Tight, system-ui, -apple-system, 'Segoe UI', sans-serif"
_MONO = "JetBrains Mono, ui-monospace, 'SF Mono', monospace"

_DM_UID = itertools.count(1)


def _depth_defs(uid: int) -> str:
    """Per-SVG shadow + sheen primitives so bars/areas read dimensional
    (unique id per render — several of these charts share one deal page)."""
    return (
        f'<defs>'
        f'<filter id="dmsh{uid}" x="-25%" y="-25%" width="150%" height="160%">'
        f'<feDropShadow dx="0" dy="1.2" stdDeviation="1.6" '
        f'flood-color="#0b2341" flood-opacity="0.22"/></filter>'
        f'<linearGradient id="dmv{uid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#ffffff" stop-opacity="0.30"/>'
        f'<stop offset="0.5" stop-color="#ffffff" stop-opacity="0.06"/>'
        f'<stop offset="1" stop-color="#000000" stop-opacity="0.10"/>'
        f'</linearGradient>'
        f'<linearGradient id="dmh{uid}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="#ffffff" stop-opacity="0.26"/>'
        f'<stop offset="0.55" stop-color="#ffffff" stop-opacity="0.05"/>'
        f'<stop offset="1" stop-color="#000000" stop-opacity="0.11"/>'
        f'</linearGradient>'
        f'</defs>'
    )


# Palette tuned for the Chartis dark shell.
# Editorial chartis palette (was dark-mode Bloomberg colors that
# rendered as light text on the cream parchment background —
# user-reported "very very light font on light background").
# All values converted to the editorial tokens used elsewhere:
# navy ink for axis text, teal-ink for the median band, parchment-
# rule grid lines, severity tokens for status.
_PAL = {
    "bg": "transparent",
    "axis": "#1a2332",           # near-ink, dark on light bg
    "grid": "#d6cfc0",           # parchment rule, light-on-light grid
    "text": "#1a2332",           # near-ink for primary text
    "text_dim": "#5d6b7a",       # editorial dim
    "text_faint": "#7a8699",     # editorial faint
    "accent": "#155752",         # teal-ink (median line + bars)
    "positive": "#0a8a5f",       # editorial green
    "negative": "#b5321e",       # editorial brick red
    "warn": "#b8732a",           # editorial bronze
    # Fan-chart band fills, ordered narrow → wide. Tinted teal-ink
    # (matches accent line) so the bands read as part of the same
    # chart family on the parchment background.
    "p50_fill": "rgba(21, 87, 82, 0.55)",
    "p25_75_fill": "rgba(21, 87, 82, 0.30)",
    "p10_90_fill": "rgba(21, 87, 82, 0.12)",
}


def _svg_escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )


def _fmt_money(v: float) -> str:
    if abs(v) >= 1_000_000_000:
        return f"${v/1_000_000_000:.1f}B"
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.0f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:,.0f}"


def _linear(value: float, v_min: float, v_max: float,
            out_min: float, out_max: float) -> float:
    if v_max == v_min:
        return (out_min + out_max) / 2
    frac = (value - v_min) / (v_max - v_min)
    return out_min + frac * (out_max - out_min)


# ── Fan chart ──────────────────────────────────────────────────────

def fan_chart(
    bands: Sequence[YearBand],
    *,
    title: str = "",
    y_label: str = "",
    width: int = 920,
    height: int = 360,
    padding_left: int = 72,
    padding_right: int = 24,
    padding_top: int = 36,
    padding_bottom: int = 42,
    fmt_y=_fmt_money,
) -> str:
    """Projection fan: P10/P25/P50/P75/P90 across years."""
    if not bands:
        return '<svg width="0" height="0"></svg>'
    inner_w = width - padding_left - padding_right
    inner_h = height - padding_top - padding_bottom

    years = [b.year for b in bands]
    y_min = min(b.p10 for b in bands)
    y_max = max(b.p90 for b in bands)
    # Pad the y-axis 8%.
    span = y_max - y_min
    y_max += span * 0.08
    y_min -= span * 0.05

    def sx(y: int) -> float:
        return padding_left + _linear(
            y, years[0], years[-1], 0, inner_w,
        )

    def sy(v: float) -> float:
        return padding_top + inner_h - _linear(
            v, y_min, y_max, 0, inner_h,
        )

    def band_path(
        values_upper: List[float], values_lower: List[float],
    ) -> str:
        pts = []
        for i, y in enumerate(years):
            pts.append(f"{sx(y):.1f},{sy(values_upper[i]):.1f}")
        for i in range(len(years) - 1, -1, -1):
            y = years[i]
            pts.append(f"{sx(y):.1f},{sy(values_lower[i]):.1f}")
        return f'M {" L ".join(pts)} Z'

    p10_90 = band_path(
        [b.p90 for b in bands], [b.p10 for b in bands],
    )
    p25_75 = band_path(
        [b.p75 for b in bands], [b.p25 for b in bands],
    )
    # Median line
    med_pts = " ".join(
        f"{sx(b.year):.1f},{sy(b.p50):.1f}" for b in bands
    )

    # Y-axis ticks (5 values).
    y_ticks = []
    for i in range(5):
        frac = i / 4
        val = y_min + frac * (y_max - y_min)
        y_pos = sy(val)
        y_ticks.append(
            f'<line x1="{padding_left}" x2="{padding_left + inner_w}" '
            f'y1="{y_pos:.1f}" y2="{y_pos:.1f}" '
            f'stroke="{_PAL["grid"]}" stroke-dasharray="2,4" />'
            f'<text x="{padding_left - 8}" y="{y_pos + 3:.1f}" '
            f'fill="{_PAL["text_faint"]}" text-anchor="end" '
            f'font-size="12" font-family="{_MONO}">'
            f'{_svg_escape(fmt_y(val))}</text>'
        )

    # X-axis ticks (year labels).
    x_ticks = []
    for b in bands:
        x = sx(b.year)
        x_ticks.append(
            f'<text x="{x:.1f}" y="{padding_top + inner_h + 16}" '
            f'fill="{_PAL["text_faint"]}" text-anchor="middle" '
            f'font-size="12" font-family="{_MONO}">'
            f'Y{b.year}</text>'
        )

    title_html = (
        f'<text x="{padding_left}" y="20" fill="{_PAL["text_dim"]}" '
        f'font-size="10" font-family="{_SANS}" '
        f'letter-spacing="1.5" text-transform="uppercase" '
        f'font-weight="700">{_svg_escape(title)}</text>'
        if title else ""
    )
    y_label_html = (
        f'<text x="16" y="{padding_top + inner_h/2}" '
        f'fill="{_PAL["text_faint"]}" font-size="10" '
        f'transform="rotate(-90 16 {padding_top + inner_h/2})" '
        f'text-anchor="middle">{_svg_escape(y_label)}</text>'
        if y_label else ""
    )
    # Legend
    legend = (
        f'<g transform="translate({padding_left + inner_w - 200}, {padding_top - 4})" '
        f'font-size="9" font-family="{_SANS}" '
        f'fill="{_PAL["text_faint"]}" letter-spacing="1">'
        f'<rect x="0" y="0" width="12" height="8" '
        f'fill="{_PAL["p10_90_fill"]}" />'
        f'<text x="16" y="7">P10–P90</text>'
        f'<rect x="60" y="0" width="12" height="8" '
        f'fill="{_PAL["p25_75_fill"]}" />'
        f'<text x="76" y="7">P25–P75</text>'
        f'<line x1="128" y1="4" x2="140" y2="4" '
        f'stroke="{_PAL["accent"]}" stroke-width="1.5" />'
        f'<text x="144" y="7">P50</text>'
        f'</g>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;background:{_PAL["bg"]};">'
        f'{title_html}'
        f'{legend}'
        f'<path d="{p10_90}" fill="{_PAL["p10_90_fill"]}" />'
        f'<path d="{p25_75}" fill="{_PAL["p25_75_fill"]}" />'
        f'<polyline points="{med_pts}" fill="none" '
        f'stroke="{_PAL["accent"]}" stroke-width="2" />'
        f'{"".join(y_ticks)}'
        f'{"".join(x_ticks)}'
        f'{y_label_html}'
        f'</svg>'
    )


# ── MOIC histogram ────────────────────────────────────────────────

def moic_histogram_chart(
    result: DealMCResult,
    *,
    width: int = 920, height: int = 320,
    padding_left: int = 40, padding_right: int = 20,
    padding_top: int = 36, padding_bottom: int = 42,
) -> str:
    buckets = result.moic_histogram
    if not buckets:
        return '<svg width="0" height="0"></svg>'
    uid = next(_DM_UID)
    inner_w = width - padding_left - padding_right
    inner_h = height - padding_top - padding_bottom
    max_prob = max(b.probability for b in buckets) or 1.0
    n = len(buckets)
    bar_w = inner_w / n * 0.8
    gap_w = inner_w / n * 0.2

    def x(i): return padding_left + i * (bar_w + gap_w) + gap_w / 2
    def y(p): return padding_top + inner_h - (p / max_prob) * inner_h

    bars: List[str] = []
    labels: List[str] = []
    for i, b in enumerate(buckets):
        # Color by MOIC tier.
        center = (b.lower + b.upper) / 2
        if center < 1.0:
            color = _PAL["negative"]
        elif center < 2.0:
            color = _PAL["warn"]
        else:
            color = _PAL["positive"]
        bar_height = max(1, padding_top + inner_h - y(b.probability))
        bars.append(
            f'<rect x="{x(i):.1f}" y="{y(b.probability):.1f}" '
            f'width="{bar_w:.1f}" height="{bar_height:.1f}" rx="2" '
            f'fill="{color}" filter="url(#dmsh{uid})" />'
            f'<rect x="{x(i):.1f}" y="{y(b.probability):.1f}" '
            f'width="{bar_w:.1f}" height="{bar_height:.1f}" rx="2" '
            f'fill="url(#dmv{uid})" pointer-events="none" />'
        )
        # Probability label above bar.
        if b.probability > 0.01:
            bars.append(
                f'<text x="{x(i) + bar_w/2:.1f}" y="{y(b.probability) - 4:.1f}" '
                f'fill="{_PAL["text_dim"]}" text-anchor="middle" '
                f'font-size="9" font-family="{_MONO}">'
                f'{b.probability*100:.1f}%</text>'
            )
        labels.append(
            f'<text x="{x(i) + bar_w/2:.1f}" y="{padding_top + inner_h + 14:.1f}" '
            f'fill="{_PAL["text_faint"]}" text-anchor="middle" '
            f'font-size="9" font-family="{_MONO}">'
            f'{b.lower:.1f}–{b.upper:.1f}x</text>'
        )

    # P50 marker line.
    p50 = result.moic_p50
    # Find nearest bucket for positioning.
    p50_x = None
    for i, b in enumerate(buckets):
        if b.lower <= p50 < b.upper:
            frac = (p50 - b.lower) / max(b.upper - b.lower, 0.01)
            p50_x = x(i) + gap_w / 2 + (bar_w + gap_w) * frac - gap_w / 2
            break
    p50_line = ""
    if p50_x is not None:
        p50_line = (
            f'<line x1="{p50_x:.1f}" x2="{p50_x:.1f}" '
            f'y1="{padding_top}" y2="{padding_top + inner_h}" '
            f'stroke="{_PAL["text"]}" stroke-width="1.5" stroke-dasharray="4,3" />'
            f'<text x="{p50_x:.1f}" y="{padding_top - 6}" '
            f'fill="{_PAL["text"]}" text-anchor="middle" '
            f'font-size="12" font-family="{_MONO}" '
            f'font-weight="700">'
            f'P50 {p50:.2f}x</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;">'
        f'{_depth_defs(uid)}'
        f'<text x="{padding_left}" y="20" fill="{_PAL["text_dim"]}" '
        f'font-size="10" font-family="{_SANS}" '
        f'letter-spacing="1.5" font-weight="700">MOIC DISTRIBUTION</text>'
        f'{"".join(bars)}'
        f'{p50_line}'
        f'{"".join(labels)}'
        f'<text x="{padding_left + inner_w}" y="{padding_top + inner_h + 14:.1f}" '
        f'fill="{_PAL["text_faint"]}" text-anchor="end" '
        f'font-size="9" font-family="{_SANS}">'
        f'MOIC (equity exit / equity check)</text>'
        f'</svg>'
    )


# ── Attribution bar chart ─────────────────────────────────────────

def attribution_chart(
    result: DealMCResult,
    *,
    width: int = 920, height: int = 320,
    padding_left: int = 220, padding_right: int = 60,
    padding_top: int = 30, padding_bottom: int = 30,
) -> str:
    if not result.attribution or not result.attribution.contributions:
        return ""
    uid = next(_DM_UID)
    contribs = list(result.attribution.contributions)
    contribs.sort(key=lambda c: -c.share_of_variance)
    unexpl = result.attribution.unexplained_share
    inner_w = width - padding_left - padding_right
    n_bars = len(contribs) + (1 if unexpl > 0 else 0)
    bar_h = (height - padding_top - padding_bottom) / max(n_bars, 1) * 0.75
    gap_h = (height - padding_top - padding_bottom) / max(n_bars, 1) - bar_h

    max_share = max(
        [c.share_of_variance for c in contribs] + [unexpl],
    ) or 1.0

    def y(i): return padding_top + i * (bar_h + gap_h)
    def bar_width(share): return max(1, share / max_share * inner_w)

    bars: List[str] = []
    for i, c in enumerate(contribs):
        w = bar_width(c.share_of_variance)
        bars.append(
            f'<text x="{padding_left - 8}" y="{y(i) + bar_h/2 + 4:.1f}" '
            f'fill="{_PAL["text"]}" text-anchor="end" font-size="11" '
            f'font-family="{_SANS}">'
            f'{_svg_escape(c.driver)}</text>'
            f'<rect x="{padding_left}" y="{y(i):.1f}" rx="2" '
            f'width="{w:.1f}" height="{bar_h:.1f}" '
            f'fill="{_PAL["accent"]}" filter="url(#dmsh{uid})" />'
            f'<rect x="{padding_left}" y="{y(i):.1f}" rx="2" '
            f'width="{w:.1f}" height="{bar_h:.1f}" '
            f'fill="url(#dmh{uid})" pointer-events="none" />'
            f'<text x="{padding_left + w + 6:.1f}" y="{y(i) + bar_h/2 + 4:.1f}" '
            f'fill="{_PAL["text_dim"]}" font-size="10" '
            f'font-family="{_MONO}">'
            f'{c.share_of_variance*100:.1f}%</text>'
        )
    if unexpl > 0:
        idx = len(contribs)
        w = bar_width(unexpl)
        bars.append(
            f'<text x="{padding_left - 8}" y="{y(idx) + bar_h/2 + 4:.1f}" '
            f'fill="{_PAL["text_faint"]}" text-anchor="end" font-size="11" '
            f'font-family="{_SANS}" '
            f'font-style="italic">Unexplained / correlated</text>'
            f'<rect x="{padding_left}" y="{y(idx):.1f}" '
            f'width="{w:.1f}" height="{bar_h:.1f}" '
            f'fill="{_PAL["text_faint"]}" opacity="0.5" />'
            f'<text x="{padding_left + w + 6:.1f}" y="{y(idx) + bar_h/2 + 4:.1f}" '
            f'fill="{_PAL["text_faint"]}" font-size="10" '
            f'font-family="{_MONO}">'
            f'{unexpl*100:.1f}%</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;">'
        f'{_depth_defs(uid)}'
        f'<text x="16" y="18" fill="{_PAL["text_dim"]}" '
        f'font-size="10" font-family="{_SANS}" '
        f'letter-spacing="1.5" font-weight="700">'
        f'VARIANCE ATTRIBUTION · MOIC</text>'
        f'{"".join(bars)}'
        f'</svg>'
    )


# ── Sensitivity tornado ───────────────────────────────────────────

def sensitivity_tornado(
    result: DealMCResult,
    *,
    width: int = 920, height: int = 340,
    padding_left: int = 220, padding_right: int = 40,
    padding_top: int = 30, padding_bottom: int = 36,
) -> str:
    stress = list(result.stress_results)
    if not stress:
        return ""
    uid = next(_DM_UID)
    # Sort by absolute magnitude, largest first.
    stress.sort(key=lambda s: -abs(s.moic_impact))
    n = len(stress)
    bar_h = (height - padding_top - padding_bottom) / max(n, 1) * 0.7
    gap_h = (height - padding_top - padding_bottom) / max(n, 1) - bar_h
    # Center the axis.
    max_abs = max(abs(s.moic_impact) for s in stress) or 1.0
    inner_w = width - padding_left - padding_right
    center_x = padding_left + inner_w / 2

    def y(i): return padding_top + i * (bar_h + gap_h)

    bars: List[str] = []
    for i, s in enumerate(stress):
        w = abs(s.moic_impact) / max_abs * (inner_w / 2)
        # Negative impacts go left (red); positive go right (green).
        if s.moic_impact < 0:
            x = center_x - w
            color = _PAL["negative"]
        else:
            x = center_x
            color = _PAL["positive"]
        bars.append(
            f'<text x="{padding_left - 8}" y="{y(i) + bar_h/2 + 4:.1f}" '
            f'fill="{_PAL["text"]}" text-anchor="end" font-size="11" '
            f'font-family="{_SANS}">'
            f'{_svg_escape(s.shock_label)}</text>'
            f'<rect x="{x:.1f}" y="{y(i):.1f}" rx="2" '
            f'width="{w:.1f}" height="{bar_h:.1f}" '
            f'fill="{color}" filter="url(#dmsh{uid})" />'
            f'<rect x="{x:.1f}" y="{y(i):.1f}" rx="2" '
            f'width="{w:.1f}" height="{bar_h:.1f}" '
            f'fill="url(#dmh{uid})" pointer-events="none" />'
            f'<text x="{(padding_left + inner_w + 6):.1f}" '
            f'y="{y(i) + bar_h/2 + 4:.1f}" '
            f'fill="{_PAL["text_dim"]}" font-size="10" '
            f'font-family="{_MONO}">'
            f'{s.moic_impact:+.2f}x</text>'
        )
    # Center axis
    center_line = (
        f'<line x1="{center_x}" x2="{center_x}" '
        f'y1="{padding_top - 4}" y2="{padding_top + n * (bar_h + gap_h)}" '
        f'stroke="{_PAL["axis"]}" stroke-width="1" />'
    )
    # "Base MOIC" label under center.
    base_moic = stress[0].base_moic if stress else 0.0
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;">'
        f'{_depth_defs(uid)}'
        f'<text x="16" y="18" fill="{_PAL["text_dim"]}" '
        f'font-size="10" font-family="{_SANS}" '
        f'letter-spacing="1.5" font-weight="700">'
        f'SENSITIVITY · ONE-AT-A-TIME SHOCK</text>'
        f'{center_line}'
        f'{"".join(bars)}'
        f'<text x="{center_x}" y="{padding_top + n * (bar_h + gap_h) + 18:.1f}" '
        f'fill="{_PAL["text_faint"]}" text-anchor="middle" '
        f'font-size="10" font-family="{_SANS}">'
        f'Base MOIC {base_moic:.2f}x</text>'
        f'</svg>'
    )
