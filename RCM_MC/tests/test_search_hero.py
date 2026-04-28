"""Test for the ck_search_hero editorial helper.

Built per docs/CHARTIS_MATCH_NOTES.md pattern 01 — navy panel +
italic-serif "Search" label + circular submit icon + teal chevron-
cut corner. The helper drops above content-listing pages
(``/library``, ``/research``, etc.) so the partner sees the same
hero shape as chartis.com/insights.

Asserts:
  - HTML contains the .ck-search-hero wrapper class (CSS hook)
  - italic-serif label renders as a <span> with the .ck-search-hero-label class
  - form action + name + placeholder all escape-safe
  - chevron-cut element present (the Chartis signature detail)
  - circular submit button has aria-label so screen readers announce it
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_search_hero


class CkSearchHeroTests(unittest.TestCase):
    def test_minimal_render_emits_navy_panel_class(self) -> None:
        html = ck_search_hero(action="/library")
        self.assertIn('class="ck-search-hero"', html)
        self.assertIn('class="ck-search-hero-inner"', html)
        self.assertIn('class="ck-search-hero-label"', html)
        self.assertIn('class="ck-search-hero-form"', html)
        self.assertIn('class="ck-search-hero-input"', html)
        self.assertIn('class="ck-search-hero-submit"', html)

    def test_label_default_is_search(self) -> None:
        html = ck_search_hero(action="/library")
        self.assertIn('>Search</span>', html)

    def test_placeholder_default_is_keyword(self) -> None:
        html = ck_search_hero(action="/library")
        self.assertIn('placeholder="Keyword"', html)

    def test_action_attribute_escaped(self) -> None:
        html = ck_search_hero(action='/library?safe=true&x=<script>')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_initial_value_round_trips(self) -> None:
        html = ck_search_hero(action="/library", initial="hospital")
        self.assertIn(' value="hospital"', html)

    def test_chevron_cut_present(self) -> None:
        """The teal triangle clipped to the bottom-right is the
        Chartis signature detail; bridges the navy panel into the
        paper-background results section."""
        html = ck_search_hero(action="/library")
        self.assertIn('class="ck-search-hero-chevron"', html)

    def test_submit_button_has_aria_label(self) -> None:
        """Screen readers announce the circular icon-only button."""
        html = ck_search_hero(action="/library")
        self.assertIn('aria-label="Run search"', html)

    def test_form_role_search(self) -> None:
        """role=search lets assistive tech land here from the
        landmark menu."""
        html = ck_search_hero(action="/library")
        self.assertIn('role="search"', html)

    def test_custom_method_post_supported(self) -> None:
        html = ck_search_hero(action="/notes/search", method="POST")
        self.assertIn('method="POST"', html)


if __name__ == "__main__":
    unittest.main()
