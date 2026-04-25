"""Tests for responsive layout utilities."""
from __future__ import annotations

import unittest


class TestViewportMeta(unittest.TestCase):
    def test_renders_meta(self):
        from rcm_mc.ui.responsive import viewport_meta
        html = viewport_meta()
        self.assertIn('name="viewport"', html)
        self.assertIn("device-width", html)
        self.assertIn("initial-scale=1", html)


class TestStylesheet(unittest.TestCase):
    def test_includes_breakpoints(self):
        from rcm_mc.ui.responsive import (
            responsive_stylesheet,
        )
        css = responsive_stylesheet()
        self.assertIn("@media", css)
        self.assertIn("max-width: 640px", css)
        self.assertIn("max-width: 1024px", css)

    def test_critical_classes_present(self):
        from rcm_mc.ui.responsive import (
            responsive_stylesheet,
        )
        css = responsive_stylesheet()
        for cls in [
            ".rs-container",
            ".rs-grid",
            ".rs-table-wrap",
            ".rs-kpi-strip",
            ".rs-split-2",
            ".rs-touch-target",
            ".rs-hide-mobile",
            ".rs-show-mobile",
        ]:
            self.assertIn(cls, css)

    def test_overflow_guard_on_body(self):
        """Body has overflow-x:hidden to prevent horizontal
        scroll from a single overflowing child."""
        from rcm_mc.ui.responsive import (
            responsive_stylesheet,
        )
        css = responsive_stylesheet()
        self.assertIn("overflow-x:hidden", css)


class TestContainer(unittest.TestCase):
    def test_wraps_content(self):
        from rcm_mc.ui.responsive import (
            responsive_container,
        )
        html = responsive_container("<p>hello</p>")
        self.assertIn("rs-container", html)
        self.assertIn("<p>hello</p>", html)

    def test_default_no_inline_style(self):
        from rcm_mc.ui.responsive import (
            responsive_container,
        )
        html = responsive_container("inner")
        # Default 1280px → uses class only
        self.assertNotIn("style=", html)

    def test_custom_max_width(self):
        from rcm_mc.ui.responsive import (
            responsive_container,
        )
        html = responsive_container(
            "inner", max_width="900px")
        self.assertIn("max-width:900px", html)


class TestGrid(unittest.TestCase):
    def test_default_min_width(self):
        from rcm_mc.ui.responsive import responsive_grid
        html = responsive_grid("a b c")
        self.assertIn("rs-grid", html)
        # Default 220px sets --rs-min
        self.assertIn("--rs-min:220px", html)
        self.assertIn("a b c", html)

    def test_custom_min_width(self):
        from rcm_mc.ui.responsive import responsive_grid
        html = responsive_grid(
            "x", min_column_width="320px")
        self.assertIn("--rs-min:320px", html)


class TestTableWrap(unittest.TestCase):
    def test_wraps_table(self):
        from rcm_mc.ui.responsive import (
            responsive_table_wrap,
        )
        html = responsive_table_wrap("<table></table>")
        self.assertIn("rs-table-wrap", html)
        self.assertIn("<table></table>", html)


class TestBreakpoints(unittest.TestCase):
    def test_breakpoint_values(self):
        from rcm_mc.ui.responsive import BREAKPOINTS
        # Breakpoints exposed for callers needing them
        # in inline styles
        self.assertIn("tablet_min", BREAKPOINTS)
        self.assertIn("laptop_min", BREAKPOINTS)
        self.assertEqual(
            BREAKPOINTS["tablet_min"], "640px")


if __name__ == "__main__":
    unittest.main()
