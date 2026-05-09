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
# legitimately ship the hex values inside CSS rule bodies.
ALLOWED_PATHS: tuple[str, ...] = (
    "rcm_mc/ui/brand.py",
    "rcm_mc/ui/_chartis_kit_legacy.py",
    "rcm_mc/ui/_chartis_kit_v2.py",
)


# Baseline as of guard introduction. Drop this number whenever a
# module migrates to PALETTE references; never raise without
# justification in the commit message.
HARDCODE_CAP = 562


class BrandHexHardcodeIsCapped(unittest.TestCase):
    """Pin the count of hardcoded dark-mode brand hexes."""

    def test_count_does_not_exceed_cap(self) -> None:
        repo_root = pathlib.Path(__file__).resolve().parent.parent
        pattern = re.compile(
            "|".join(re.escape(h) for h in DARK_BRAND_HEXES),
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
