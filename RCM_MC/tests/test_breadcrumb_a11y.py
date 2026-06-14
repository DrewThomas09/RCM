"""Breadcrumb accessibility.

The breadcrumb is a second <nav> landmark alongside the Primary topbar nav,
so it must be labelled; its "/" separators must not be read aloud; and the
final crumb (the page you're on) must carry aria-current="page".
"""

import unittest

from rcm_mc.ui._chartis_kit import _breadcrumbs


class BreadcrumbA11yTests(unittest.TestCase):
    def setUp(self):
        self.html = _breadcrumbs(
            [("Home", "/"), ("Research", "/research"), ("Market Intel", None)]
        )

    def test_nav_landmark_is_labelled(self):
        self.assertIn('<nav class="ck-breadcrumbs" aria-label="Breadcrumb">', self.html)

    def test_separators_are_hidden_from_assistive_tech(self):
        self.assertIn('<span class="sep" aria-hidden="true">/</span>', self.html)
        # No bare, announced separators remain.
        self.assertNotIn('<span class="sep">/</span>', self.html)

    def test_current_page_crumb_is_marked(self):
        # The trailing href-less crumb is the active page.
        self.assertIn('<span aria-current="page">Market Intel</span>', self.html)

    def test_linked_crumbs_are_plain_anchors(self):
        # Only the current page gets aria-current — not the linked ancestors.
        self.assertIn('<a href="/research">Research</a>', self.html)
        self.assertEqual(self.html.count('aria-current="page"'), 1)

    def test_empty_crumbs_render_nothing(self):
        self.assertEqual(_breadcrumbs(None), "")
        self.assertEqual(_breadcrumbs([]), "")


if __name__ == "__main__":
    unittest.main()
