"""WCAG contrast-ratio helper.

PROMPTS.md Phase 7 / Prompt 95: cream-on-cream subtitles, grey-on-
cream secondary text below WCAG AA. The acceptance bar is "every
text color × background pair in PALETTE meets WCAG AA"
(≥ 4.5:1 normal, ≥ 3:1 large).

Stdlib-only. The formula is the WCAG 2.0 contrast definition:

    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    where R/G/B are linearised sRGB values.
    contrast = (L_lighter + 0.05) / (L_darker + 0.05)
"""
from __future__ import annotations


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c + c for c in s)
    if len(s) != 6:
        raise ValueError(f"unrecognised hex color: {hex_str!r}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _linearise(c: float) -> float:
    """sRGB → linear-light, per WCAG."""
    c = c / 255.0
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_str: str) -> float:
    r, g, b = _hex_to_rgb(hex_str)
    return (
        0.2126 * _linearise(r)
        + 0.7152 * _linearise(g)
        + 0.0722 * _linearise(b)
    )


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """WCAG contrast ratio between two hex colors. Always ≥ 1."""
    l1 = relative_luminance(fg_hex)
    l2 = relative_luminance(bg_hex)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def passes_aa_normal(fg_hex: str, bg_hex: str) -> bool:
    """WCAG AA threshold for normal-size text."""
    return contrast_ratio(fg_hex, bg_hex) >= 4.5


def passes_aa_large(fg_hex: str, bg_hex: str) -> bool:
    """WCAG AA threshold for large-size text (18pt+ or 14pt+ bold)."""
    return contrast_ratio(fg_hex, bg_hex) >= 3.0
