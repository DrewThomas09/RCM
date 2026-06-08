"""Regression: format placeholders / double-escaped entities must not
leak into rendered HTML.

- The diligence-checklist editorial headline was a plain string (missing
  the f-prefix), so it rendered the literal "{sector}".
- The demo walkthrough step titles contained "&amp;" in source and were
  html.escape()'d again at render, showing "&amp;" to the user.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.diligence_checklist_page import (
    render_diligence_checklist,
)
from rcm_mc.ui.demo_page import render_demo_page


class TemplateTokenLeakTests(unittest.TestCase):
    def test_checklist_headline_interpolates_sector(self):
        html = render_diligence_checklist({})
        self.assertNotIn("{sector}", html)

    def test_demo_titles_not_double_escaped(self):
        html = render_demo_page()
        self.assertNotIn("&amp;amp;", html)


if __name__ == "__main__":
    unittest.main()
