"""tests for ``rcm_mc.ui._ui_kit.empty_state`` (the Phase-2 wrapper).

PROMPTS.md Phase 2 / Prompt 12: a reusable empty-state card that
follows the Watchlist pattern. The wrapper carries the partner-voice
keyword vocabulary (``body``, ``cta_label``, ``cta_href``) over the
canonical ``rcm_mc.ui.empty_states.empty_state`` implementation.

These tests pin the keyword-only contract and the with/without-CTA
branches.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import empty_state


class KeywordOnlyContract(unittest.TestCase):

    def test_all_arguments_are_keyword_only(self) -> None:
        # Positional call must fail — the field names carry meaning
        # and we don't want callers to mix the icon and the title.
        with self.assertRaises(TypeError):
            empty_state("☆", "No deals", "Click below.")  # type: ignore


class RendersCoreContent(unittest.TestCase):

    def setUp(self) -> None:
        self.html = empty_state(
            icon="☆",
            title="No watchlist deals",
            body="Star a deal on its profile to add it here.",
        )

    def test_icon_in_output(self) -> None:
        self.assertIn("☆", self.html)

    def test_title_in_output(self) -> None:
        self.assertIn("No watchlist deals", self.html)

    def test_body_in_output(self) -> None:
        self.assertIn("Star a deal on its profile", self.html)


class CTABehaviour(unittest.TestCase):

    @staticmethod
    def _has_cta_anchor(html: str) -> bool:
        # Match the actual rendered <a class="es-btn …"> element, not
        # the CSS rule text inside the inline <style> block.
        return "<a " in html and 'class="es-btn' in html

    def test_no_cta_when_omitted(self) -> None:
        html = empty_state(
            icon="☆", title="T", body="B",
        )
        self.assertFalse(self._has_cta_anchor(html))

    def test_cta_renders_when_both_label_and_href_given(self) -> None:
        html = empty_state(
            icon="☆", title="T", body="B",
            cta_label="Browse deals", cta_href="/library",
        )
        self.assertTrue(self._has_cta_anchor(html))
        self.assertIn("Browse deals", html)
        self.assertIn('href="/library"', html)

    def test_cta_label_without_href_renders_nothing(self) -> None:
        # The wrapper requires both — half-supplied means no CTA.
        html = empty_state(
            icon="☆", title="T", body="B",
            cta_label="Browse",
        )
        self.assertFalse(self._has_cta_anchor(html))

    def test_cta_href_without_label_renders_nothing(self) -> None:
        html = empty_state(
            icon="☆", title="T", body="B",
            cta_href="/library",
        )
        self.assertFalse(self._has_cta_anchor(html))


class HtmlEscapeOnUserText(unittest.TestCase):

    def test_title_escaped(self) -> None:
        html = empty_state(
            icon="☆", title="<script>alert(1)</script>",
            body="ok",
        )
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_cta_label_escaped(self) -> None:
        html = empty_state(
            icon="☆", title="t", body="b",
            cta_label="<x>", cta_href="/x",
        )
        self.assertNotIn(">a<", html)  # smoke check
        self.assertIn("&lt;x&gt;", html)


if __name__ == "__main__":
    unittest.main()
