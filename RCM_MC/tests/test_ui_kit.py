"""Tests for the shared UI kit (canonical button / card / input)."""
from __future__ import annotations

import unittest


class TestStylesheet(unittest.TestCase):
    def test_emits_all_classes(self):
        from rcm_mc.ui.ui_kit import ui_kit_stylesheet
        css = ui_kit_stylesheet()
        for cls in [
            ".ui-btn", ".ui-btn-primary", ".ui-btn-ghost",
            ".ui-card", ".ui-card-elevated",
            ".ui-input", ".ui-section-h",
            ".ui-kpi", ".ui-kpi-label", ".ui-kpi-value",
        ]:
            self.assertIn(cls, css)

    def test_canonical_colors_present(self):
        from rcm_mc.ui.ui_kit import ui_kit_stylesheet
        css = ui_kit_stylesheet()
        # Surface, border, text colors
        self.assertIn("#1f2937", css)
        self.assertIn("#374151", css)
        self.assertIn("#f3f4f6", css)
        # Primary accent
        self.assertIn("#1e3a8a", css)


class TestButton(unittest.TestCase):
    def test_secondary_default(self):
        from rcm_mc.ui.ui_kit import button
        html = button("Click me")
        self.assertIn('class="ui-btn"', html)
        self.assertNotIn("ui-btn-primary", html)
        self.assertIn("Click me", html)
        self.assertIn('<button', html)

    def test_primary(self):
        from rcm_mc.ui.ui_kit import button
        html = button("Save", kind="primary")
        self.assertIn(
            'class="ui-btn ui-btn-primary"', html)

    def test_ghost(self):
        from rcm_mc.ui.ui_kit import button
        html = button("Cancel", kind="ghost")
        self.assertIn(
            'class="ui-btn ui-btn-ghost"', html)

    def test_link_button(self):
        from rcm_mc.ui.ui_kit import button
        html = button("Open", href="/data/catalog")
        self.assertIn('<a', html)
        self.assertIn('href="/data/catalog"', html)

    def test_button_id(self):
        from rcm_mc.ui.ui_kit import button
        html = button("X", button_id="save-btn")
        self.assertIn('id="save-btn"', html)

    def test_unknown_kind_rejected(self):
        from rcm_mc.ui.ui_kit import button
        with self.assertRaises(ValueError):
            button("X", kind="purple")

    def test_html_escape(self):
        from rcm_mc.ui.ui_kit import button
        html = button("<script>", href="/x")
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;script&gt;", html)


class TestCard(unittest.TestCase):
    def test_default_card(self):
        from rcm_mc.ui.ui_kit import card
        html = card("<p>content</p>")
        self.assertIn('class="ui-card"', html)
        self.assertIn("<p>content</p>", html)

    def test_elevated_card(self):
        from rcm_mc.ui.ui_kit import card
        html = card("x", elevated=True)
        self.assertIn('class="ui-card-elevated"', html)

    def test_custom_padding(self):
        from rcm_mc.ui.ui_kit import card
        html = card("x", padding="24px")
        self.assertIn("padding:24px", html)


class TestInput(unittest.TestCase):
    def test_text_input(self):
        from rcm_mc.ui.ui_kit import input_field
        html = input_field(
            name="q", placeholder="Search…")
        self.assertIn('class="ui-input"', html)
        self.assertIn('type="text"', html)
        self.assertIn('name="q"', html)
        self.assertIn('placeholder="Search…"', html)

    def test_search_input(self):
        from rcm_mc.ui.ui_kit import input_field
        html = input_field(type_="search")
        self.assertIn('type="search"', html)

    def test_unknown_type_rejected(self):
        from rcm_mc.ui.ui_kit import input_field
        with self.assertRaises(ValueError):
            input_field(type_="weird")

    def test_aria_label(self):
        from rcm_mc.ui.ui_kit import input_field
        html = input_field(
            type_="search",
            aria_label="Global search")
        self.assertIn(
            'aria-label="Global search"', html)


class TestSectionHeader(unittest.TestCase):
    def test_renders(self):
        from rcm_mc.ui.ui_kit import section_header
        html = section_header("Top opportunities")
        self.assertIn('class="ui-section-h"', html)
        self.assertIn("Top opportunities", html)


class TestKPICard(unittest.TestCase):
    def test_basic_kpi(self):
        from rcm_mc.ui.ui_kit import kpi_card
        html = kpi_card("Active deals", "5")
        self.assertIn("Active deals", html)
        self.assertIn(">5<", html)
        self.assertIn('class="ui-kpi"', html)
        self.assertIn('class="ui-kpi-label"', html)
        self.assertIn('class="ui-kpi-value"', html)

    def test_kpi_with_sub(self):
        from rcm_mc.ui.ui_kit import kpi_card
        html = kpi_card(
            "Deals", "5", sub="of 8 total")
        self.assertIn("of 8 total", html)
        self.assertIn('class="ui-kpi-sub"', html)

    def test_html_escape(self):
        from rcm_mc.ui.ui_kit import kpi_card
        html = kpi_card("<x>", "<v>", sub="<s>")
        for raw in ("<x>", "<v>", "<s>"):
            self.assertNotIn(raw, html)
        self.assertIn("&lt;x&gt;", html)


if __name__ == "__main__":
    unittest.main()
