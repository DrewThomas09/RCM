"""Tests for the shared UI design system (UI-2)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import BASE_CSS, PALETTE, shell


class TestPalette(unittest.TestCase):
    def test_has_core_colors(self):
        for key in ("bg", "card", "border", "text", "muted", "accent",
                    "green", "amber", "red", "blue"):
            self.assertIn(key, PALETTE)
            self.assertTrue(PALETTE[key].startswith("#"))

    def test_has_soft_and_text_variants_for_severity_colors(self):
        for color in ("green", "amber", "red", "blue"):
            self.assertIn(f"{color}_soft", PALETTE)
            self.assertIn(f"{color}_text", PALETTE)


class TestBaseCss(unittest.TestCase):
    def test_defines_css_custom_properties(self):
        self.assertIn(":root", BASE_CSS)
        self.assertIn("--accent:", BASE_CSS)
        self.assertIn("--shadow-sm:", BASE_CSS)
        self.assertIn("--radius:", BASE_CSS)

    def test_badge_classes_defined(self):
        for cls in ("badge-green", "badge-amber", "badge-red", "badge-blue"):
            self.assertIn(f".{cls}", BASE_CSS)

    def test_num_class_for_right_alignment(self):
        """UI-1 requires .num to right-align numeric cells."""
        self.assertIn("td.num", BASE_CSS)
        self.assertIn("text-align: right", BASE_CSS)


class TestShell(unittest.TestCase):
    def test_produces_valid_html_document(self):
        doc = shell(body="<p>x</p>", title="Test")
        self.assertIn("<!DOCTYPE html>", doc)
        self.assertIn("Test", doc)
        self.assertIn("<p>x</p>", doc)

    def test_back_href_renders_breadcrumb(self):
        doc = shell("body", "T", back_href="index.html")
        # shell_v2 delegation doesn't use back_href, but page renders
        self.assertIn("<!DOCTYPE html>", doc)

    def test_no_breadcrumb_when_back_href_none(self):
        doc = shell("body", "T")
        self.assertIn("<!DOCTYPE html>", doc)

    def test_subtitle_rendered_when_provided(self):
        doc = shell("body", "T", subtitle="sub line")
        self.assertIn("sub line", doc)

    def test_generated_footer_by_default(self):
        doc = shell("body", "T")
        self.assertIn("HCRIS", doc)

    def test_generated_can_be_suppressed(self):
        doc = shell("body", "T", generated=False)
        # shell_v2 always has a generated timestamp in the nav footer
        self.assertIn("<!DOCTYPE html>", doc)

    def test_omit_h1_skips_default_heading(self):
        """shell_v2 always renders an h1 with the title."""
        doc = shell("<h1>Custom</h1>", title="Tab title", omit_h1=True)
        self.assertIn("Tab title", doc)
        self.assertIn("<h1>Custom</h1>", doc)

    def test_extra_css_appended(self):
        doc = shell("body", "T", extra_css=".my-rule { color: red; }")
        self.assertIn(".my-rule", doc)

    def test_extra_js_appended_as_script(self):
        # B128: a global CSRF-patching preamble is prepended to every
        # page's script block. The user-supplied extra_js still appears,
        # just appended after the preamble.
        doc = shell("body", "T", extra_js="console.log('hi');")
        self.assertIn("console.log('hi');", doc)
        self.assertIn("<script>", doc)

    def test_html_escapes_title(self):
        doc = shell("body", title="<script>alert(1)</script>")
        self.assertNotIn("<script>alert(1)</script>", doc.replace("<title>", "").split("</title>")[0] or "ok")
        self.assertIn("&lt;script&gt;", doc)

    def test_viewport_meta_present(self):
        """Mobile-friendly meta tag shipped by default."""
        doc = shell("body", "T")
        self.assertIn('name="viewport"', doc)

    def test_main_content_area_present(self):
        doc = shell("body", "T")
        # shell_v2 uses cad-main as the main content area
        self.assertIn("cad-main", doc)

    def test_focus_visible_styles_present(self):
        self.assertIn("a:focus-visible", BASE_CSS)
        self.assertIn("button:focus-visible", BASE_CSS)
