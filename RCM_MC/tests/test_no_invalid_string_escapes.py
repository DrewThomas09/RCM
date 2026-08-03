"""No Python source may contain an invalid string escape.

This codebase embeds JavaScript in triple-quoted Python literals, and JS is
full of backslashes — regex literals (``/^\\d+$/``), ``\\n`` in template
strings, ``\\.`` in character classes. In a NON-raw Python literal those are
read by Python first:

  * ``\\d`` is not a recognised Python escape, so today it survives with a
    DeprecationWarning — the JS works by luck, and the warning is scheduled
    to become a SyntaxError.
  * ``\\b``, ``\\n``, ``\\t``, ``\\f``, ``\\v`` ARE recognised. Python
    silently converts them to control characters and the browser never sees
    the escape at all. That failure is invisible: no warning, no error, just
    a regex that quietly stops matching.

Two instances were live at once (2026-08-03): ``deal_profile_page._inline_js``
and ``_chartis_kit._PALETTE_JS``, both fixed by prefixing the triple-quoted
literal with ``r``. The second was only noticed because a passing test emitted
the warning in its output — nothing failed. Hence this test.

Fix by making the literal raw, not by deleting the backslash.
"""
from __future__ import annotations

import pathlib
import unittest
import warnings

_PKG = pathlib.Path(__file__).resolve().parents[1] / "rcm_mc"


class NoInvalidEscapes(unittest.TestCase):
    def test_no_module_has_an_invalid_escape_sequence(self):
        offenders = []
        for path in sorted(_PKG.rglob("*.py")):
            try:
                src = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    compile(src, str(path), "exec")
                except SyntaxError:
                    # Syntax is another test's problem; don't double-report.
                    continue
                for w in caught:
                    if "escape sequence" in str(w.message):
                        offenders.append(
                            f"{path.relative_to(_PKG.parent)}:{w.lineno}: "
                            f"{w.message}"
                        )
        self.assertEqual(
            [], offenders,
            f"{len(offenders)} invalid string escape(s). If the literal holds "
            "JavaScript or a regex, prefix the triple-quoted literal with r "
            "to make it raw — do not "
            "delete the backslash, and do not double it, which would put a "
            "literal backslash-backslash into the emitted JS:\n"
            + "\n".join(offenders),
        )


class EmbeddedRegexesSurviveToTheBrowser(unittest.TestCase):
    """Guard the two literals that actually had the bug."""

    def test_palette_js_keeps_its_regex_literals(self):
        from rcm_mc.ui._chartis_kit import _PALETTE_JS
        for fragment in (r"/^\d{6}$/", r"/^\d+$/"):
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment, _PALETTE_JS,
                    "the palette's numeric-shortcut regex did not survive "
                    "into the emitted JS — the literal is no longer raw",
                )

    def test_no_stray_control_characters_in_emitted_js(self):
        # A backspace/formfeed/vertical-tab in served JS is the signature of
        # a \b or \f that Python ate. Newlines and tabs are legitimate
        # formatting, so they are not checked here.
        from rcm_mc.ui._chartis_kit import _PALETTE_JS
        for ch, name in (("\b", r"\b"), ("\f", r"\f"), ("\v", r"\v")):
            with self.subTest(escape=name):
                self.assertNotIn(
                    ch, _PALETTE_JS,
                    f"emitted JS contains a literal {name} control character "
                    "— Python interpreted the escape instead of passing it "
                    "through",
                )


if __name__ == "__main__":
    unittest.main()
