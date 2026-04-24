"""SeekingChartis brand system — single source of truth for all visual identity.

Healthcare PE diligence platform. Every page, export, and audit trail
references this module for brand consistency.

As of Phase 2 of the UI v2 editorial rework, ``PALETTE`` is
**flag-aware**: the same key names resolve to the legacy dark
Bloomberg palette when ``CHARTIS_UI_V2=0`` (default) and to the
editorial navy/teal/parchment palette when ``CHARTIS_UI_V2=1``.
This means every existing page renderer that references
``PALETTE["text_primary"]`` etc. flips with the flag without a
per-page migration.

The mapping is an explicit alias table below so partners can see
exactly which editorial token replaces which legacy token.
"""
from __future__ import annotations

import os
from typing import Any, Dict


BRAND = {
    "name": "SeekingChartis",
    "tagline": "Healthcare diligence, instrument-grade",
    "version": "1.0.0",
    "copyright": "SeekingChartis",
    "footer_text": "SeekingChartis v1.0.0 — Healthcare diligence, instrument-grade",
}

LOGO_SVG = (
    '<svg viewBox="0 0 32 32" width="28" height="28" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M16 2L16 28" stroke="#1F4E78" stroke-width="2.5" stroke-linecap="round"/>'
    '<path d="M10 6C10 6 13 8 16 8C19 8 22 6 22 6" stroke="#1F4E78" stroke-width="2" stroke-linecap="round"/>'
    '<path d="M10 12C10 12 13 14 16 14C19 14 22 12 22 12" stroke="#1F4E78" stroke-width="2" stroke-linecap="round"/>'
    '<path d="M10 18C10 18 13 20 16 20C19 20 22 18 22 18" stroke="#1F4E78" stroke-width="2" stroke-linecap="round"/>'
    '<path d="M12 2L20 2" stroke="#1F4E78" stroke-width="2" stroke-linecap="round"/>'
    '<circle cx="10" cy="3" r="1.5" fill="#3b82f6"/>'
    '<circle cx="22" cy="3" r="1.5" fill="#3b82f6"/>'
    '</svg>'
)

WORDMARK_SVG = (
    '<svg viewBox="0 0 200 24" width="200" height="24" xmlns="http://www.w3.org/2000/svg">'
    '<text x="0" y="18" font-family="Source Serif Pro, Georgia, serif" '
    'font-size="20" font-weight="600" fill="#e2e8f0" letter-spacing="0.5">SeekingChartis</text>'
    '</svg>'
)


# ── Legacy palette (CHARTIS_UI_V2=0) ────────────────────────────────

_PALETTE_LEGACY: Dict[str, str] = {
    # Bloomberg Terminal-inspired professional dark — near-black base,
    # high-contrast data, amber accent for status, blue for links.
    "bg": "#05070b",
    "bg_secondary": "#0b0f16",
    "bg_tertiary": "#131922",
    "border": "#1c2430",
    "border_light": "#2b3646",
    "text_primary": "#e6edf5",
    "text_secondary": "#9aa7b8",
    "text_muted": "#5f6b7c",
    "text_link": "#5b9bd5",
    "brand_primary": "#1a3a5c",
    "brand_accent": "#2d6ba4",
    "accent_amber": "#e8a33d",
    "positive": "#22c55e",
    "negative": "#ef4444",
    "warning": "#f59e0b",
    "neutral": "#5b6abf",
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#ca8a04",
    "low": "#64748b",
    "ticker_up": "#22c55e",
    "ticker_down": "#ef4444",
    "ticker_flat": "#9aa7b8",
    # Secondary vocabulary — same values, aliased to the key names
    # that analysis_workbench, deal pages, and portfolio pages use.
    # Consolidating here so the flag flips every page simultaneously.
    "panel":      "#111827",
    "panel_alt":  "#0f172a",
    "text":       "#e2e8f0",
    "text_dim":   "#94a3b8",
    "text_faint": "#64748b",
    "accent":     "#3b82f6",
    "accent_bright": "#66c8c3",
}


# ── Editorial palette (CHARTIS_UI_V2=1) ─────────────────────────────
#
# Same key names; values mirror the v2 kit's editorial tokens so
# existing page renderers that do ``PALETTE["text_primary"]`` etc.
# pick up navy/teal/parchment without branching on the flag.
#
# The alias map is intentional and reviewable — every legacy key
# points at a specific editorial equivalent. When the two palettes
# disagree on a key's semantic (e.g., dark-theme text_primary is
# light text on black vs. editorial text_primary is dark text on
# parchment), the editorial value is correct for the editorial
# surface. No page branches on this; the kit's ``chartis_shell``
# emits the correct background, so text-on-background contrast
# stays legible.

_PALETTE_V2: Dict[str, str] = {
    # Surfaces — flip completely: dark → parchment/white
    "bg":           "#f5f1ea",   # parchment
    "bg_secondary": "#ece6db",   # bone tint
    "bg_tertiary":  "#ffffff",   # white panels
    "border":       "#d6cfc3",   # hairline on parchment
    "border_light": "#c5bdae",
    # Text — dark text on light now
    "text_primary":   "#1a2332",   # near-ink
    "text_secondary": "#465366",
    "text_muted":     "#7a8699",
    "text_link":      "#0f5e5a",   # dark teal
    # Brand — navy + teal
    "brand_primary":  "#0b2341",   # navy
    "brand_accent":   "#2fb3ad",   # teal
    "accent_amber":   "#b8732a",   # editorial warning tone replaces amber
    # Status — desaturated / print-friendly
    "positive":       "#0a8a5f",
    "negative":       "#b5321e",
    "warning":        "#b8732a",
    "neutral":        "#1d3c69",   # navy_3
    "critical":       "#8a1e0e",
    "high":           "#b5321e",
    "medium":         "#b8732a",
    "low":            "#7a8699",
    # Tickers
    "ticker_up":      "#0a8a5f",
    "ticker_down":    "#b5321e",
    "ticker_flat":    "#7a8699",
    # Secondary vocabulary — maps workbench / deal-page keys onto
    # editorial tokens so the same hex-free renderer flips with
    # the flag.
    "panel":         "#ffffff",   # white panels (was dark #111827)
    "panel_alt":     "#ece6db",   # bone tint     (was very dark #0f172a)
    "text":          "#1a2332",   # near-ink      (was light #e2e8f0)
    "text_dim":      "#465366",   # (was #94a3b8)
    "text_faint":    "#7a8699",   # (was #64748b)
    "accent":        "#0f5e5a",   # dark teal link (was blue #3b82f6)
    "accent_bright": "#2fb3ad",   # bright teal (was #66c8c3 — same family)
}


def _active_palette() -> Dict[str, str]:
    """Return the palette matching ``CHARTIS_UI_V2``. Resolved at
    import time by default; callers that need per-request flipping
    can read this function directly."""
    flag = os.environ.get("CHARTIS_UI_V2", "0") != "0"
    return dict(_PALETTE_V2 if flag else _PALETTE_LEGACY)


# Resolved once at import time. Pages that do
# ``from rcm_mc.ui.brand import PALETTE`` receive whichever palette
# matches the env at process start. This matches existing behaviour
# (PALETTE has always been a module-level dict) and avoids making
# every page re-resolve per request.
PALETTE: Dict[str, str] = _active_palette()


TYPOGRAPHY = {
    "font_serif": "Georgia, 'Times New Roman', serif",
    "font_sans": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "font_mono": "'JetBrains Mono', 'SF Mono', 'Fira Code', 'Consolas', monospace",
}
