"""Tests for SeekingChartis brand system and shell v2.

BRAND:
 1. Brand dict has all required fields.
 2. Palette has all semantic colors.
 3. Logo SVG is valid.

SHELL V2:
 4. shell_v2 renders with SeekingChartis branding.
 5. Left nav has all 8 items.
 6. Ticker bar renders.
 7. Search input present.
 8. Print CSS hides nav.
 9. Active nav item highlighted.

VERSION:
10. __product__ is SeekingChartis.
11. __version__ is 1.0.0.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.brand import BRAND, PALETTE, TYPOGRAPHY, NAV_ITEMS, LOGO_SVG
from rcm_mc.ui.shell_v2 import shell_v2


class TestBrand(unittest.TestCase):

    def test_brand_fields(self):
        self.assertEqual(BRAND["name"], "SeekingChartis")
        self.assertIn("tagline", BRAND)
        self.assertIn("version", BRAND)
        self.assertIn("footer_text", BRAND)

    def test_palette_semantic_colors(self):
        for key in ("bg", "text_primary", "brand_primary", "positive",
                     "negative", "warning", "ticker_up", "ticker_down"):
            self.assertIn(key, PALETTE)
            self.assertTrue(PALETTE[key].startswith("#"))

    def test_typography(self):
        self.assertIn("font_serif", TYPOGRAPHY)
        self.assertIn("font_sans", TYPOGRAPHY)
        self.assertIn("font_mono", TYPOGRAPHY)

    def test_logo_svg(self):
        self.assertIn("<svg", LOGO_SVG)
        self.assertIn("</svg>", LOGO_SVG)
        self.assertIn("#1F4E78", LOGO_SVG)

    def test_nav_items(self):
        self.assertGreaterEqual(len(NAV_ITEMS), 8)
        labels = [n["label"] for n in NAV_ITEMS if not n.get("separator")]
        self.assertIn("Home", labels)
        self.assertIn("Deal Screener", labels)
        self.assertIn("Market Data", labels)
        self.assertIn("Deals", labels)
        self.assertIn("Regression", labels)
        self.assertIn("Data Sources", labels)


class TestShellV2(unittest.TestCase):

    def test_renders_with_branding(self):
        html = shell_v2("<p>test</p>", "Test Page")
        self.assertIn("SeekingChartis", html)
        self.assertIn("cad-topbar", html)
        self.assertIn("cad-nav", html)

    def test_left_nav_items(self):
        html = shell_v2("<p>test</p>", "Test")
        for nav in NAV_ITEMS:
            self.assertIn(nav["label"], html)
            if not nav.get("separator"):
                self.assertIn(nav["href"], html)

    def test_ticker_renders(self):
        html = shell_v2("<p>test</p>", "Test")
        self.assertIn("cad-ticker", html)
        self.assertIn("HCA", html)

    def test_search_input(self):
        html = shell_v2("<p>test</p>", "Test")
        self.assertIn("cad-search", html)
        self.assertIn('placeholder="Search', html)

    def test_print_css(self):
        html = shell_v2("<p>test</p>", "Test")
        self.assertIn("@media print", html)
        self.assertIn("display: none", html)

    def test_active_nav(self):
        html = shell_v2("<p>test</p>", "Test", active_nav="/settings")
        self.assertIn('class="cad-nav-item active"', html)

    def test_title_in_head(self):
        html = shell_v2("<p>test</p>", "My Page")
        self.assertIn("<title>My Page — SeekingChartis</title>", html)

    def test_alert_badge_js(self):
        html = shell_v2("<p>test</p>", "Test")
        self.assertIn("cad-alert-count", html)
        self.assertIn("/api/alerts/active-count", html)


class TestVersion(unittest.TestCase):

    def test_product_name(self):
        from rcm_mc import __product__
        self.assertEqual(__product__, "SeekingChartis")

    def test_version(self):
        from rcm_mc import __version__
        self.assertEqual(__version__, "1.0.0")


if __name__ == "__main__":
    unittest.main()
