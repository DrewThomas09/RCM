"""tests for ``rcm_mc.ui._ui_kit.form_section``.

PROMPTS.md Phase 3 / Prompt 43: helper that wraps a group of form
inputs under an italic-serif subheader. Used by Thesis Pipeline,
Deal MC, Bridge Audit, Covenant Stress to break their 12-18-field
walls into semantic groups.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import form_section


class StructureAndContent(unittest.TestCase):

    def test_renders_label_and_body(self) -> None:
        html = form_section(
            "Identity",
            '<div class="form-field"><input name="x"></div>',
        )
        self.assertIn("Identity", html)
        self.assertIn('<input name="x">', html)

    def test_uses_section_label_class(self) -> None:
        html = form_section("Identity", "<div></div>")
        self.assertIn("form-section-label", html)

    def test_label_html_escaped(self) -> None:
        html = form_section("<x>", "<div></div>")
        self.assertIn("&lt;x&gt;", html)

    def test_body_passes_through_unchanged(self) -> None:
        # Body is caller-supplied trusted markup — must not be escaped.
        body = '<input type="number" name="rev"><input name="ebt">'
        html = form_section("Capital", body)
        self.assertIn(body, html)


class ProperSemantics(unittest.TestCase):

    def test_uses_section_element(self) -> None:
        html = form_section("Identity", "<div></div>")
        self.assertTrue(html.startswith("<section "))
        self.assertTrue(html.endswith("</section>"))

    def test_uses_h3_for_subheader(self) -> None:
        html = form_section("Identity", "<div></div>")
        self.assertIn("<h3 ", html)


if __name__ == "__main__":
    unittest.main()
