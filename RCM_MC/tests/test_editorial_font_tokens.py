"""Guards against in-app editorial pages falling back to the old font.

The editorial shells load Source Serif 4 / Inter Tight, and CSS should
reach them via the ``--sc-serif`` / ``--sc-sans`` tokens (with Georgia /
Inter only as the no-webfont fallback). A few in-app surfaces used to
hardcode ``font-family:Georgia,serif`` / ``font-family:Inter,sans-serif``
WITHOUT the token, so they rendered in Georgia even though Source Serif 4
was loaded — the "some pages have the old font" report.

These were tokenized to ``var(--sc-serif,Georgia,serif)`` /
``var(--sc-sans,Inter,sans-serif)``. This test pins that fix: the
in-app surfaces below must not regress to a bare, untokenized literal.

Standalone print/PDF/download surfaces (bankruptcy print view, the
report themes) are intentionally excluded — they ship without the
webfont, so Georgia is the deliberate, correct fallback there.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1] / "rcm_mc"

# (relative path, regex that must NOT match — a bare untokenized literal)
_IN_APP_SURFACES = [
    # IC packet body style is injected into the shell-wrapped /diligence/
    # ic-packet page via extra_css, so its literal leaks into the editorial
    # page. (The standalone download re-derives Georgia from the fallback.)
    ("exports/ic_packet.py", r"font-family:\s*Georgia,\s*'Times New Roman',\s*serif"),
    ("ui/ic_packet_page.py", r"font-family:Georgia,serif"),
    ("ui/bear_case_page.py", r"font-family:Georgia,serif"),
    ("diligence/bear_case/generator.py", r"font-family:Georgia,serif"),
    ("ui/data_public/sector_correlation_page.py", r"font-family:Inter,sans-serif"),
]


class EditorialFontTokenTests(unittest.TestCase):
    def test_in_app_surfaces_have_no_bare_old_font(self) -> None:
        for rel, pattern in _IN_APP_SURFACES:
            text = (_ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(file=rel):
                self.assertIsNone(
                    re.search(pattern, text),
                    f"{rel} hardcodes an untokenized font ({pattern}) — "
                    "wrap it in var(--sc-serif,...) / var(--sc-sans,...) so "
                    "the editorial webfont is used in-app",
                )

    def test_tokenized_form_is_present(self) -> None:
        # Sanity: the tokenized replacements are actually there, so this
        # file can't pass just because someone deleted the declarations.
        checks = [
            ("exports/ic_packet.py", "var(--sc-serif, Georgia, 'Times New Roman', serif)"),
            ("ui/ic_packet_page.py", "var(--sc-serif,Georgia,serif)"),
            ("ui/bear_case_page.py", "var(--sc-serif,Georgia,serif)"),
            ("diligence/bear_case/generator.py", "var(--sc-serif,Georgia,serif)"),
            ("ui/data_public/sector_correlation_page.py", "var(--sc-sans,Inter,sans-serif)"),
        ]
        for rel, needle in checks:
            text = (_ROOT / rel).read_text(encoding="utf-8")
            with self.subTest(file=rel):
                self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
