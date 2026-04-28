"""Test for the ck_results_header editorial helper.

Built per docs/CHARTIS_MATCH_NOTES.md pattern 03 — N RESULTS count
in serif + active-filter chips with one-click remove + a Clear all
arrow link in teal. Closes the chartis.com/insights pattern triplet
(search hero + filter rail + results header) on /library and the
sibling content-listing pages.

Asserts:
  - .ck-results-header wrapper class (CSS hook)
  - count + label render escape-safe + tabular-nums
  - chips-block ABSENT when no chips passed (no zero-state crud)
  - chips-block PRESENT with chips + clear-all when filters active
  - chip remove_href emitted as anchor (not button) — single GET
  - chip-x glyph + sr-only screen-reader label both present
  - clear_all_href omitted when no chips
  - HTML escape on user-controlled chip label / remove_href
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_results_header


class CkResultsHeaderTests(unittest.TestCase):
    def test_minimal_render_emits_header_wrapper(self) -> None:
        html = ck_results_header(count=46)
        self.assertIn('class="ck-results-header"', html)
        self.assertIn('class="ck-results-count"', html)
        self.assertIn('class="ck-results-num', html)
        self.assertIn('class="ck-results-label"', html)

    def test_count_renders_inside_num_span(self) -> None:
        html = ck_results_header(count=46)
        self.assertIn(">46<", html)
        # tabular-nums via shared sc-num utility class
        self.assertIn("sc-num", html)

    def test_default_label_is_results(self) -> None:
        html = ck_results_header(count=12)
        self.assertIn(">Results</span>", html)

    def test_custom_label_renders(self) -> None:
        html = ck_results_header(count=12, label="Deals")
        self.assertIn(">Deals</span>", html)
        self.assertNotIn(">Results</span>", html)

    def test_no_chips_omits_chips_block(self) -> None:
        html = ck_results_header(count=0)
        self.assertNotIn('class="ck-results-chips"', html)
        self.assertNotIn(">Clear all<", html)

    def test_chips_block_renders_with_chips(self) -> None:
        chips = [
            {"label": "Partnerships", "remove_href": "/library"},
            {"label": "Hospitals", "remove_href": "/library?regime=peak"},
        ]
        html = ck_results_header(count=12, chips=chips)
        self.assertIn('class="ck-results-chips"', html)
        self.assertIn(">Partnerships ", html)
        self.assertIn(">Hospitals ", html)

    def test_chip_is_anchor_not_button(self) -> None:
        # Each chip must be a <a class="ck-chip"> so the partner can
        # use Cmd-click / right-click → 'open in new tab' on a link.
        # Buttons would force JS state-management we don't need.
        chips = [{"label": "Partnerships", "remove_href": "/library"}]
        html = ck_results_header(count=12, chips=chips)
        self.assertIn('<a class="ck-chip" href="/library">', html)
        self.assertNotIn('<button class="ck-chip"', html)

    def test_chip_x_glyph_and_screen_reader_label(self) -> None:
        chips = [{"label": "Partnerships", "remove_href": "/library"}]
        html = ck_results_header(count=12, chips=chips)
        self.assertIn('class="ck-chip-x"', html)
        self.assertIn("×", html)  # The glyph itself
        self.assertIn('class="sr-only"', html)
        self.assertIn(" remove filter</span>", html)

    def test_clear_all_appears_only_with_href_and_chips(self) -> None:
        chips = [{"label": "x", "remove_href": "/library"}]
        # With chips + href: appears
        html_a = ck_results_header(count=12, chips=chips, clear_all_href="/library")
        self.assertIn('<a class="ck-arrow" href="/library">Clear all</a>', html_a)
        # With chips, no href: omitted
        html_b = ck_results_header(count=12, chips=chips)
        self.assertNotIn(">Clear all<", html_b)
        # With href but no chips: chips block omitted entirely so
        # clear-all also omitted (it lives inside the chips block)
        html_c = ck_results_header(count=12, clear_all_href="/library")
        self.assertNotIn(">Clear all<", html_c)

    def test_chip_label_html_escape(self) -> None:
        chips = [{"label": "<script>x</script>", "remove_href": "/library"}]
        html = ck_results_header(count=12, chips=chips)
        self.assertNotIn("<script>x</script>", html)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", html)

    def test_chip_remove_href_html_escape(self) -> None:
        # Attribute-context escaping — quotes must be escaped
        chips = [{"label": "x", "remove_href": '/library?q="apollo"'}]
        html = ck_results_header(count=12, chips=chips)
        self.assertNotIn('href="/library?q="apollo""', html)
        self.assertIn("&quot;apollo&quot;", html)

    def test_count_string_renders_unchanged(self) -> None:
        # Caller may pre-format with thousands separator
        html = ck_results_header(count="1,234")
        self.assertIn(">1,234<", html)


if __name__ == "__main__":
    unittest.main()
