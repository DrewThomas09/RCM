"""Guard against hardcoded brand-color hex codes that bypass PALETTE.

The platform supports two color modes — dark (default) and an
editorial light/cream variant — via ``rcm_mc.ui.brand.PALETTE``.
Every page should resolve severity colors through the palette
keys (``PALETTE["negative"]``, ``PALETTE["positive"]``, etc.) so a
mode switch updates every page in lockstep.

Hardcoding the *dark-mode* hex code (``#ef4444``, ``#10b981``,
``#f59e0b``, etc.) breaks the contract: a partner switching to the
editorial light variant sees red-on-cream where the spec wants
``#b5321e`` (a warmer, paper-friendly red). The drift compounds as
new pages copy the pattern.

This guard caps the count of dark-mode brand-hex occurrences
outside of ``brand.py``. Lower the cap as modules migrate.

Allowed locations:
  * ``rcm_mc/ui/brand.py``    — palette definition itself
  * ``rcm_mc/ui/_chartis_kit_legacy.py`` — shipped CSS (may
    reference brand hexes inside a CSS rule body)
  * ``rcm_mc/ui/_chartis_kit_v2.py``     — same

Migration path: replace ``"color:#ef4444"`` literal with
``f"color:{PALETTE['negative']}"`` inside an f-string.
"""
from __future__ import annotations

import pathlib
import re
import unittest


# Dark-mode brand-color hex codes from rcm_mc/ui/brand.py.
# Light-mode hexes are NOT in this set — the editorial variant
# legitimately uses a different palette, and those values appear
# only inside brand.py.
DARK_BRAND_HEXES: tuple[str, ...] = (
    "#ef4444",   # negative
    "#10b981",   # alt-positive (legacy)
    "#22c55e",   # positive
    "#f59e0b",   # warning
    "#1F4E78",   # brand_accent (capital F intentional — historical)
    "#3b82f6",   # info-blue
    "#60a5fa",   # info-blue-light
    "#2d6ba4",   # alt brand_accent
)

# Files exempt from the guard — palette definition, shells that
# legitimately ship the hex values inside CSS rule bodies, and the
# light/dark theme token table (analogous to brand.py — defines the
# theme variables themselves so ``var(--theme-…)`` callers resolve
# correctly).
ALLOWED_PATHS: tuple[str, ...] = (
    "rcm_mc/ui/brand.py",
    "rcm_mc/ui/_chartis_kit_legacy.py",
    "rcm_mc/ui/_chartis_kit_v2.py",
    "rcm_mc/ui/theme.py",
    "rcm_mc/ui/colors.py",
    "rcm_mc/ui/power_chart.py",  # chart sequential palette, not brand semantics
)


# Moat is fully closed: no module under rcm_mc/ outside the
# ALLOWED_PATHS list may emit a dark-mode brand-hex literal.
# Adding a NEW occurrence FAILS this test.
#
# Migration history (this guard's value across the consolidation):
#   575 → 562 → 546 → 522 → 511 → 497 → 464 → 421 → 281 →
#   188 → 97 → 50 → 32 → 4 → 0  (12 ratchet commits)
#
# Three migration patterns supported (all accepted by the guard):
#   1. ``f"…{PALETTE['key']}…"``  — Python f-string interpolation
#   2. ``var(--theme-token,#hex)`` — CSS-variable with fallback
#                                     (the var() reverter strips the
#                                     hex from the count)
#   3. ``PALETTE["key"]`` in module-level dicts / function defaults
HARDCODE_CAP = 0


def _strip_var_fallbacks(src: str) -> str:
    """Remove hex codes that appear as ``var(--foo,#hex)`` fallback
    values — those are harmless safety nets the CSS engine uses when
    the theme variable is undefined (the partner-visible color is
    still driven by the var). Counting them as violations would
    discourage the right pattern for static CSS strings.
    """
    return re.sub(r"var\(--[\w-]+,\s*#[0-9a-fA-F]{3,8}\)", "", src)


class BrandHexHardcodeIsCapped(unittest.TestCase):
    """Pin the count of hardcoded dark-mode brand hexes."""

    def test_count_does_not_exceed_cap(self) -> None:
        repo_root = pathlib.Path(__file__).resolve().parent.parent
        # CSS hex colors are case-insensitive (``#EF4444`` and
        # ``#ef4444`` render identically). The guard catches both
        # casings so contributors can't sidestep by uppercasing.
        pattern = re.compile(
            "|".join(re.escape(h) for h in DARK_BRAND_HEXES),
            re.IGNORECASE,
        )
        hits: list[tuple[str, str]] = []
        for py in (repo_root / "rcm_mc").rglob("*.py"):
            rel = str(py.relative_to(repo_root))
            if rel in ALLOWED_PATHS:
                continue
            try:
                src = py.read_text(encoding="utf-8")
            except OSError:
                continue
            src = _strip_var_fallbacks(src)
            for m in pattern.finditer(src):
                hits.append((rel, m.group(0)))
        count = len(hits)
        self.assertLessEqual(
            count, HARDCODE_CAP,
            f"Hardcoded brand-color hex count ({count}) exceeds cap "
            f"({HARDCODE_CAP}). Use PALETTE['negative'] / "
            f"PALETTE['positive'] / etc. inside f-strings, or "
            f"update HARDCODE_CAP after justifying.\n"
            f"First 10 offenders: {hits[:10]}",
        )


class CapIsTightAgainstActualCount(unittest.TestCase):
    """Soft signal — prompt ratcheting the cap downward as
    migrations land. Allows a 25-hex buffer (one batch's worth)
    so an in-flight migration doesn't fail spuriously."""

    def test_cap_within_window_of_actual(self) -> None:
        repo_root = pathlib.Path(__file__).resolve().parent.parent
        pattern = re.compile(
            "|".join(re.escape(h) for h in DARK_BRAND_HEXES),
            re.IGNORECASE,
        )
        count = 0
        for py in (repo_root / "rcm_mc").rglob("*.py"):
            rel = str(py.relative_to(repo_root))
            if rel in ALLOWED_PATHS:
                continue
            try:
                src = py.read_text(encoding="utf-8")
            except OSError:
                continue
            src = _strip_var_fallbacks(src)
            count += len(pattern.findall(src))
        self.assertLessEqual(
            HARDCODE_CAP - count, 25,
            f"HARDCODE_CAP ({HARDCODE_CAP}) is more than 25 above "
            f"actual count ({count}). Lower the cap to {count} "
            f"in tests/test_brand_color_hardcoding_guard.py to "
            f"lock in the gain.",
        )


if __name__ == "__main__":
    unittest.main()
