"""Tests for ck_narrative_band — the memo-intro narrative summary band.

PR #1 of the two-view Command Center work. The band is shared (used by
both the Chartis Internal and PE Partner compositions later) and is
silent by default, so this PR wires it into no page yet — these tests
pin the component contract and the editorial visual guardrails.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_narrative_band


class CkNarrativeBandTests(unittest.TestCase):
    def test_silent_by_default(self):
        # No text and no empty copy → renders nothing (opt-in band).
        self.assertEqual(ck_narrative_band(), "")
        self.assertEqual(ck_narrative_band(""), "")

    def test_text_renders_italic_paragraph(self):
        html = ck_narrative_band("Eleven hospitals in active diligence.")
        self.assertIn('class="ck-narrative"', html)
        self.assertIn("Eleven hospitals in active diligence.", html)
        # It's a paragraph, not a card/heading.
        self.assertIn("<p ", html)
        self.assertNotIn("<h1", html)
        self.assertNotIn("<h2", html)

    def test_empty_copy_used_when_no_text(self):
        # inject_css=False so we assert on the rendered <p> class, not the
        # stylesheet (which always defines the .is-empty rule).
        html = ck_narrative_band(
            "", empty_copy="No active engagements.", inject_css=False)
        self.assertIn('class="ck-narrative is-empty"', html)
        self.assertIn("No active engagements.", html)

    def test_text_takes_precedence_over_empty_copy(self):
        html = ck_narrative_band(
            "Live summary.", empty_copy="Nothing yet.", inject_css=False)
        self.assertIn("Live summary.", html)
        self.assertNotIn("Nothing yet.", html)
        self.assertNotIn("is-empty", html)

    def test_escapes_user_text(self):
        html = ck_narrative_band('<script>alert(1)</script> & "x"')
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&amp;", html)

    def test_inject_css_toggle(self):
        with_css = ck_narrative_band("x", inject_css=True)
        self.assertIn("<style>", with_css)
        self.assertIn(".ck-narrative", with_css)
        without_css = ck_narrative_band("x", inject_css=False)
        self.assertNotIn("<style>", without_css)
        self.assertIn('class="ck-narrative"', without_css)

    def test_visual_guardrails(self):
        # Part-4 guardrails: editorial register, no dashboard-marketing
        # treatments. The band must be serif + italic, with no card
        # shadow, no orange decoration, no all-caps marketing chrome.
        html = ck_narrative_band("Performance held steady this quarter.")
        low = html.lower()
        self.assertIn("--sc-serif", low)        # serif typography
        self.assertIn("font-style:italic", low)  # italic memo register
        self.assertNotIn("box-shadow", low)      # no floating cards
        self.assertNotIn("#ff", low)             # no bright/orange hex
        self.assertNotIn("ff9900", low)
        self.assertNotIn("text-transform:uppercase", low)  # no all-caps band
        self.assertNotIn("!", html)              # declarative, no exclamation


if __name__ == "__main__":
    unittest.main()
