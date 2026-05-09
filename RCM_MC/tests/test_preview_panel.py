"""tests for ``rcm_mc.ui._ui_kit.preview_panel``.

PROMPTS.md Phase 2 / Prompt 13: a right-rail ghosted preview shown
beside form-only diligence pages so the partner knows what the
eventual output will look like.

Required structure per spec:

* container carries ``data-preview="true"`` (hook for print CSS + QA)
* sketch wrapped in ``.preview-ghost``
* title + caption escaped; sketch passed through unchanged
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import preview_panel


class StructuralAttributes(unittest.TestCase):

    def setUp(self) -> None:
        self.html = preview_panel(
            title="What you'll see",
            sketch_html='<svg viewBox="0 0 100 100"></svg>',
            caption="Sample output — runs in ~10s once you submit.",
        )

    def test_data_preview_attribute(self) -> None:
        self.assertIn('data-preview="true"', self.html)

    def test_sketch_wrapped_in_preview_ghost(self) -> None:
        self.assertIn('class="preview-ghost"', self.html)

    def test_sketch_html_passes_through_unchanged(self) -> None:
        # The whole point of preview_panel is to inject markup;
        # caller-supplied HTML must not be escaped.
        self.assertIn('<svg viewBox="0 0 100 100"></svg>', self.html)

    def test_title_and_caption_present(self) -> None:
        self.assertIn("What you&#x27;ll see", self.html)
        self.assertIn("Sample output", self.html)


class TitleAndCaptionEscaped(unittest.TestCase):

    def test_title_escaped(self) -> None:
        html = preview_panel(
            title="<b>boom</b>",
            sketch_html="",
            caption="ok",
        )
        self.assertNotIn("<b>boom", html.replace("<b>boom</b>", "x"))
        self.assertIn("&lt;b&gt;boom&lt;/b&gt;", html)

    def test_caption_escaped(self) -> None:
        html = preview_panel(
            title="t", sketch_html="", caption="<x>",
        )
        self.assertIn("&lt;x&gt;", html)


class KeywordOnlyAPI(unittest.TestCase):

    def test_positional_call_rejected(self) -> None:
        with self.assertRaises(TypeError):
            preview_panel("t", "<svg/>", "c")  # type: ignore


if __name__ == "__main__":
    unittest.main()
