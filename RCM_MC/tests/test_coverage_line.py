"""tests for ``coverage_line`` (P64)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import coverage_line


class FullCoverage(unittest.TestCase):

    def test_no_filter_no_missing_minimal_render(self) -> None:
        html = coverage_line(matched=18, total=18)
        self.assertIn(">18</strong> deals matched", html)
        self.assertNotIn("missing realized data", html)
        self.assertNotIn("Data Catalog", html)


class PartialCoverage(unittest.TestCase):

    def test_filter_desc_in_output(self) -> None:
        html = coverage_line(
            matched=3, total=18,
            filter_desc="Behavioral Health, vintage 2008, $50-100M EV",
        )
        self.assertIn(">3</strong> deals matched", html)
        self.assertIn("18", html)
        self.assertIn("Behavioral Health", html)

    def test_missing_realized_includes_catalog_link(self) -> None:
        html = coverage_line(
            matched=3, total=18,
            filter_desc="Behavioral Health",
            missing_realized=15,
        )
        self.assertIn("15 missing realized data", html)
        self.assertIn('href="/data/catalog"', html)


class CustomCatalogHref(unittest.TestCase):

    def test_catalog_href_overrides_default(self) -> None:
        html = coverage_line(
            matched=1, total=5,
            filter_desc="x",
            missing_realized=2,
            catalog_href="/internal/coverage-map",
        )
        self.assertIn('href="/internal/coverage-map"', html)


class HtmlEscaping(unittest.TestCase):

    def test_filter_desc_escaped(self) -> None:
        html = coverage_line(
            matched=1, total=2,
            filter_desc="<script>alert(1)</script>",
        )
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class EdgeCases(unittest.TestCase):

    def test_zero_matched_renders(self) -> None:
        html = coverage_line(matched=0, total=18, filter_desc="ASC")
        self.assertIn(">0</strong> deals matched", html)

    def test_negative_matched_clamped_to_zero(self) -> None:
        html = coverage_line(matched=-3, total=18, filter_desc="ASC")
        self.assertIn(">0</strong>", html)

    def test_total_less_than_matched_clamped(self) -> None:
        # If a caller's bookkeeping is wrong, total < matched would
        # produce nonsense. The helper clamps total to be at least
        # matched so the output remains coherent.
        html = coverage_line(matched=5, total=2, filter_desc="x")
        self.assertIn(">5</strong> deals matched", html)
        self.assertIn("5 deals matching", html)


if __name__ == "__main__":
    unittest.main()
