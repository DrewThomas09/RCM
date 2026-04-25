"""Semantic color system — green/red/amber applied consistently.

The existing ``brand.py`` carries the flag-aware brand palette
(navy / teal / parchment for editorial mode, dark bloomberg for
legacy). This module is the **status** palette: green for
above-peer / positive change / good, red for below-peer /
negative change / bad, amber for watch / approaching threshold.

Why a separate module:

  - Brand is identity: 'this is SeekingChartis'.
  - Status is information: 'this number is good vs that number'.
    Status colors stay constant across brand modes — green for
    positive is a universal cue that doesn't depend on whether
    the user has the editorial UI flag on.

Helper functions surface partner-relevant decision logic:

  • ``status_color(value, low, high)`` — value < low → green,
    value > high → red, else amber. For lower_is_better metrics.
  • ``peer_color(value, peer_p50, lower_is_better=False)`` —
    one-shot peer comparison.
  • ``change_color(delta, lower_is_better=False)`` — positive
    delta → green, negative → red, ~zero → neutral.
  • ``severity_color(severity)`` — 'critical'/'high'/'medium'/
    'low' → red/red/amber/neutral.
  • ``status_badge(label, kind)`` — small HTML pill in the
    semantic color, with consistent padding + font.

Public API::

    from rcm_mc.ui.colors import (
        STATUS,
        status_color, peer_color, change_color,
        severity_color, status_badge,
    )
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, Optional


# ── Semantic palette — single source of truth ───────────────
STATUS: Dict[str, str] = {
    # Severity / status
    "positive": "#10b981",   # green — above peer, improving, good
    "negative": "#ef4444",   # red — below peer, declining, bad
    "watch":    "#f59e0b",   # amber — approaching threshold, mid-tier
    "neutral":  "#9ca3af",   # gray — no signal, breakeven
    "info":     "#60a5fa",   # blue — informational accent

    # Background pairs for badges (text on muted bg)
    "positive_bg": "#065f46",
    "positive_fg": "#a7f3d0",
    "negative_bg": "#7f1d1d",
    "negative_fg": "#fecaca",
    "watch_bg":    "#92400e",
    "watch_fg":    "#fde68a",
    "neutral_bg":  "#374151",
    "neutral_fg":  "#9ca3af",
    "info_bg":     "#1e3a8a",
    "info_fg":     "#bfdbfe",
}


# Severity-band mapping. 'critical' and 'high' both render red;
# the partner reads the *label* for severity, the color for the
# urgency cue. Keeping these distinct from the bands lets us
# tweak text without touching color.
_SEVERITY_TO_KIND: Dict[str, str] = {
    "critical": "negative",
    "high":     "negative",
    "medium":   "watch",
    "warning":  "watch",
    "low":      "neutral",
    "info":     "info",
    "ok":       "positive",
}


# Peer-band mapping. Z-score / ratio bands.
_PEER_BANDS = [
    (-1.0, "positive"),    # >1σ better than peer median
    (1.0, "neutral"),       # within ±1σ
    (1e9, "negative"),      # >1σ worse than peer median
]


# ── Helpers ──────────────────────────────────────────────────

def status_color(
    value: Optional[float],
    *,
    low_threshold: float,
    high_threshold: float,
    lower_is_better: bool = True,
) -> str:
    """Pick a status color based on value vs thresholds.

    Default semantics (lower_is_better=True):
      - value < low_threshold → 'positive' (green)
      - value > high_threshold → 'negative' (red)
      - between → 'watch' (amber)

    Set lower_is_better=False to invert (e.g. collection_rate).
    Returns 'neutral' for None.
    """
    if value is None:
        return STATUS["neutral"]
    if lower_is_better:
        if value < low_threshold:
            return STATUS["positive"]
        if value > high_threshold:
            return STATUS["negative"]
        return STATUS["watch"]
    else:
        if value > high_threshold:
            return STATUS["positive"]
        if value < low_threshold:
            return STATUS["negative"]
        return STATUS["watch"]


def peer_color(
    value: Optional[float],
    peer_p50: Optional[float],
    *,
    lower_is_better: bool = True,
    significance_pct: float = 0.10,
) -> str:
    """Compare value to peer median; return semantic color.

    significance_pct: minimum % deviation to count as 'meaningful'
    above/below. Within that band → 'neutral' (in line). Default
    10% — anything inside that range is too small to call.

    For lower_is_better=True (denial rate, DSO):
      - value < p50 × (1 - significance) → 'positive'
      - value > p50 × (1 + significance) → 'negative'
      - within ±significance band → 'neutral'

    Inverted for collection rate / margin (lower_is_better=False).
    """
    if value is None or peer_p50 is None or peer_p50 == 0:
        return STATUS["neutral"]
    ratio = value / peer_p50
    upper = 1.0 + significance_pct
    lower = 1.0 - significance_pct
    if lower <= ratio <= upper:
        return STATUS["neutral"]
    above = ratio > upper
    if lower_is_better:
        return STATUS["negative"] if above else STATUS["positive"]
    return STATUS["positive"] if above else STATUS["negative"]


def change_color(
    delta: Optional[float],
    *,
    lower_is_better: bool = False,
    epsilon: float = 0.0,
) -> str:
    """Color a change/delta value.

    lower_is_better=False (default — money, growth):
      - delta > epsilon → 'positive' (green for growth)
      - delta < -epsilon → 'negative' (red for shrinkage)
      - within ±epsilon → 'neutral'

    Set lower_is_better=True for KPIs where decreases are good
    (denial rate, DSO).
    """
    if delta is None:
        return STATUS["neutral"]
    if -epsilon <= delta <= epsilon:
        return STATUS["neutral"]
    is_increase = delta > 0
    if lower_is_better:
        return (STATUS["negative"] if is_increase
                else STATUS["positive"])
    return (STATUS["positive"] if is_increase
            else STATUS["negative"])


def severity_color(severity: Optional[str]) -> str:
    """Map a severity string to a status color.

    Accepts: critical / high → negative;
             medium / warning → watch;
             low / neutral → neutral;
             info → info; ok → positive.
    Unknown severity → neutral.
    """
    s = (severity or "").strip().lower()
    kind = _SEVERITY_TO_KIND.get(s, "neutral")
    return STATUS[kind]


def severity_kind(severity: Optional[str]) -> str:
    """Like severity_color but returns the canonical kind string
    ('positive' / 'negative' / 'watch' / 'neutral' / 'info').
    Useful for selecting matching bg/fg pairs."""
    s = (severity or "").strip().lower()
    return _SEVERITY_TO_KIND.get(s, "neutral")


def status_badge(
    label: str,
    *,
    kind: str = "neutral",
    size: str = "small",
) -> str:
    """Render a small HTML pill in the semantic color.

    Args:
      label: badge text. HTML-escaped.
      kind: 'positive' / 'negative' / 'watch' / 'neutral' / 'info',
        OR a severity string like 'critical' / 'high' (mapped via
        severity_kind).
      size: 'small' (11px) or 'medium' (13px).

    Returns: a single inline-block <span> with consistent padding
    + tabular-nums.
    """
    if kind in _SEVERITY_TO_KIND:
        kind = _SEVERITY_TO_KIND[kind]
    if kind not in ("positive", "negative",
                    "watch", "neutral", "info"):
        kind = "neutral"
    bg = STATUS[f"{kind}_bg"]
    fg = STATUS[f"{kind}_fg"]
    font_size = "11px" if size == "small" else "13px"
    pad_y = "2" if size == "small" else "3"
    pad_x = "8" if size == "small" else "10"
    return (
        f'<span style="display:inline-block;padding:'
        f'{pad_y}px {pad_x}px;border-radius:4px;'
        f'background:{bg};color:{fg};font-size:{font_size};'
        f'font-variant-numeric:tabular-nums;'
        f'font-weight:500;">{_html.escape(label)}</span>')


def status_dot(kind: str = "neutral",
               size_px: int = 8) -> str:
    """Tiny solid circle in the semantic color — used inline in
    list rows so partner reads a column of dots top-to-bottom."""
    if kind in _SEVERITY_TO_KIND:
        kind = _SEVERITY_TO_KIND[kind]
    if kind not in ("positive", "negative",
                    "watch", "neutral", "info"):
        kind = "neutral"
    return (
        f'<span style="display:inline-block;width:{size_px}px;'
        f'height:{size_px}px;border-radius:50%;background:'
        f'{STATUS[kind]};flex-shrink:0;"></span>')
