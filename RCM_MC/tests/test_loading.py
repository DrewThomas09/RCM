"""Tests for skeleton screens + loading components."""
from __future__ import annotations

import unittest


class TestSkeletonBox(unittest.TestCase):
    def test_basic_render(self):
        from rcm_mc.ui.loading import skeleton_box
        html = skeleton_box(width="120px", height="20px")
        self.assertIn('class="sk"', html)
        self.assertIn("width:120px", html)
        self.assertIn("height:20px", html)
        self.assertIn("<style>", html)

    def test_inline_mode(self):
        from rcm_mc.ui.loading import skeleton_box
        html = skeleton_box(inline=True)
        self.assertIn("display:inline-block", html)

    def test_inject_css_disabled(self):
        from rcm_mc.ui.loading import skeleton_box
        html = skeleton_box(inject_css=False)
        self.assertNotIn("<style>", html)
        self.assertIn('class="sk"', html)


class TestSkeletonText(unittest.TestCase):
    def test_default_three_lines(self):
        from rcm_mc.ui.loading import skeleton_text
        html = skeleton_text()
        # 3 line bars
        self.assertEqual(html.count('class="sk"'), 3)

    def test_zero_lines_returns_empty(self):
        from rcm_mc.ui.loading import skeleton_text
        self.assertEqual(skeleton_text(lines=0), "")

    def test_last_line_shorter(self):
        from rcm_mc.ui.loading import skeleton_text
        html = skeleton_text(
            lines=2, last_line_width="50%")
        # Last line at 50%, first at 100%
        self.assertIn("width:100%", html)
        self.assertIn("width:50%", html)


class TestSkeletonTable(unittest.TestCase):
    def test_basic_render(self):
        from rcm_mc.ui.loading import skeleton_table
        html = skeleton_table(rows=3, cols=4)
        # 3 body rows + 1 header = 4 rows; each has 4 cells
        # so 16 sk spans + skin classes
        self.assertEqual(html.count('class="sk"'), 16)

    def test_no_header(self):
        from rcm_mc.ui.loading import skeleton_table
        html = skeleton_table(
            rows=3, cols=2, with_header=False)
        # 3 rows × 2 cells = 6 sk spans
        self.assertEqual(html.count('class="sk"'), 6)

    def test_zero_returns_empty(self):
        from rcm_mc.ui.loading import skeleton_table
        self.assertEqual(
            skeleton_table(rows=0, cols=4), "")
        self.assertEqual(
            skeleton_table(rows=3, cols=0), "")


class TestSkeletonChart(unittest.TestCase):
    def test_renders_bars(self):
        from rcm_mc.ui.loading import skeleton_chart
        html = skeleton_chart()
        # Chart placeholder has 9 bars
        self.assertEqual(html.count('class="sk"'), 9)


class TestSpinner(unittest.TestCase):
    def test_renders_spinner(self):
        from rcm_mc.ui.loading import loading_spinner
        html = loading_spinner()
        self.assertIn('class="spinner"', html)
        self.assertIn("@keyframes spin", html)

    def test_with_label(self):
        from rcm_mc.ui.loading import loading_spinner
        html = loading_spinner("Loading data…")
        self.assertIn("Loading data", html)

    def test_html_escapes_label(self):
        from rcm_mc.ui.loading import loading_spinner
        html = loading_spinner("<x>")
        self.assertIn("&lt;x&gt;", html)


class TestProgressBar(unittest.TestCase):
    def test_determinate(self):
        from rcm_mc.ui.loading import progress_bar
        html = progress_bar(percent=42)
        self.assertIn("progress-bar-fill", html)
        self.assertIn("width:42.0%", html)
        # No indeterminate-bar div is rendered
        self.assertNotIn(
            '<div class="progress-bar-indet">', html)

    def test_indeterminate(self):
        from rcm_mc.ui.loading import progress_bar
        html = progress_bar(percent=None)
        self.assertIn("progress-bar-indet", html)

    def test_clamps_percent(self):
        from rcm_mc.ui.loading import progress_bar
        html = progress_bar(percent=200)
        self.assertIn("width:100.0%", html)
        html = progress_bar(percent=-50)
        self.assertIn("width:0.0%", html)

    def test_with_label(self):
        from rcm_mc.ui.loading import progress_bar
        html = progress_bar(
            percent=50, label="Processing 4/8")
        self.assertIn("Processing 4/8", html)


class TestLoadingOverlay(unittest.TestCase):
    def test_default_label(self):
        from rcm_mc.ui.loading import loading_overlay
        html = loading_overlay()
        self.assertIn('class="loading-overlay"', html)
        self.assertIn("Loading", html)
        self.assertIn('class="spinner"', html)
        # ARIA role
        self.assertIn('role="status"', html)

    def test_custom_label(self):
        from rcm_mc.ui.loading import loading_overlay
        html = loading_overlay("Crunching numbers…")
        self.assertIn("Crunching numbers", html)


class TestPageProgressBar(unittest.TestCase):
    def test_renders(self):
        from rcm_mc.ui.loading import page_progress_bar
        html = page_progress_bar()
        self.assertIn('id="page-progress"', html)
        # Click listener
        self.assertIn("click", html)
        self.assertIn("pageshow", html)
        # CSS animation classes
        self.assertIn(".active", html)
        self.assertIn(".done", html)

    def test_inject_css_disabled(self):
        from rcm_mc.ui.loading import page_progress_bar
        html = page_progress_bar(inject_css=False)
        self.assertNotIn("<style>", html)
        # JS still emits
        self.assertIn("<script>", html)


if __name__ == "__main__":
    unittest.main()
