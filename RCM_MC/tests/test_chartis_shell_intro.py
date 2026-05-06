"""Test the chartis_shell ``editorial_intro`` kwarg added in cycle 20.

The kwarg auto-prepends a ``ck_section_intro`` block to the body so
existing chartis_shell-using renderers can adopt the chartis cadence
(italic-serif headline + eyebrow + body) with a single 3-line
addition. Cycle 20 lifted 11 pages over the 70 fidelity threshold
this way.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


class ChartisShellEditorialIntroTests(unittest.TestCase):
    def test_no_intro_kwarg_renders_body_verbatim(self):
        # Backward-compat: omitting editorial_intro changes nothing.
        html = chartis_shell("<p>hello</p>", title="X")
        self.assertIn("<p>hello</p>", html)
        # No section-intro emitted
        self.assertNotIn('class="ck-section-intro"', html)

    def test_intro_kwarg_prepends_section_intro(self):
        html = chartis_shell(
            "<p>body</p>", title="X",
            editorial_intro={
                "eyebrow": "TEST",
                "headline": "The platform finds its voice.",
                "italic_word": "finds",
            },
        )
        # Section intro present
        self.assertIn('class="ck-section-intro"', html)
        # Eyebrow + italic word both rendered
        self.assertIn(">TEST</div>", html)
        self.assertIn("<em>finds</em>", html)
        # Body still appears AFTER the intro
        intro_idx = html.index('class="ck-section-intro"')
        body_idx = html.index("<p>body</p>")
        self.assertLess(intro_idx, body_idx)

    def test_intro_kwarg_with_body_text(self):
        html = chartis_shell(
            "<p>x</p>", title="X",
            editorial_intro={
                "eyebrow": "EYEBROW",
                "headline": "Headline.",
                "italic_word": "Headline",
                "body": "Supporting paragraph copy.",
            },
        )
        self.assertIn(">Supporting paragraph copy.</p>", html)

    def test_intro_kwarg_does_not_affect_other_kwargs(self):
        html = chartis_shell(
            "<p>x</p>", title="X",
            subtitle="Sub",
            breadcrumbs=[("Home", "/")],
            editorial_intro={
                "eyebrow": "TEST",
                "headline": "Where the voice resides.",
                "italic_word": "resides",
            },
        )
        # Subtitle still renders
        self.assertIn(">Sub</div>", html)
        # Breadcrumbs still render
        self.assertIn('class="ck-breadcrumbs"', html)
        # Intro still renders
        self.assertIn("<em>resides</em>", html)

    def test_empty_dict_intro_treated_as_none(self):
        # An empty dict is falsy in the kwarg test → no intro emitted.
        html = chartis_shell(
            "<p>body</p>", title="X",
            editorial_intro={},
        )
        self.assertNotIn('class="ck-section-intro"', html)


if __name__ == "__main__":
    unittest.main()
