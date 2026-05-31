"""Top-bar hover/focus dropdown menus replace the persistent second-line rail.

Partner-reported issues this pins:
- the old sticky second-line sub-nav rail is gone (it read as a broken second
  bar under the topbar);
- each section nav item (Pipeline/Diligence/Library/Research/Portfolio) now
  carries a hover/focus dropdown menu of its sub-pages;
- the Guide button is styled by the paper-topbar rule (ink text + green "?"),
  not the old white-on-navy override that washed it out.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._chartis_kit import _topbar, chartis_shell, _SUB_NAV


class TopbarDropdownTests(unittest.TestCase):
    def setUp(self):
        self.html = _topbar("research")

    def test_no_persistent_second_line_rail(self):
        # The standalone sub-nav <nav> rail must no longer be emitted.
        self.assertNotIn('<nav class="ck-subnav"', self.html)
        self.assertNotIn('class="ck-subnav-inner"', self.html)

    def test_each_section_item_has_a_dropdown_group_and_menu(self):
        # Five section items (all but Home) → five hover groups + five mega menus.
        self.assertEqual(self.html.count("ck-nav-group"), 6)  # +Source
        self.assertEqual(self.html.count("ck-nav-mega"), 6)  # +Source

    def test_menu_lists_the_sections_subpages(self):
        # The mega-menu surfaces the section's TOP-RANKED surfaces (top-6 +
        # a "More →" link), not every curated _SUB_NAV entry — that's the
        # post-#924 ranked-nav design. Assert it shows exactly the items it
        # ranked in (self-consistent → robust across environments / ranking
        # data) rather than pinning to a specific page that may rank in or out.
        from rcm_mc.ui._chartis_kit import _ranked_subnav_items
        top, has_more = _ranked_subnav_items("research")
        self.assertTrue(top, "research mega-menu surfaced no ranked items")
        for item in top:
            self.assertIn(item["label"], self.html)
        self.assertIn('class="ck-mega-item" role="menuitem"', self.html)
        # PR #1155 removed the "01. 02. …" mono-ordinal prefix; the items
        # are now plain links carrying the label + description.
        # The post-#1155 marker that survives is the per-item body span.
        self.assertIn('class="ck-mega-it-body"', self.html)
        self.assertIn('class="ck-mega-it-label"', self.html)
        if has_more:
            self.assertIn("All Research tools", self.html)  # More → link

    def test_mega_menu_has_featured_left_panel(self):
        # The "cool little thing on the left" — a featured section card: a
        # clickable lede (kicker · headline · pull-quote) linking to the
        # section, plus the "All X tools" CTA below it.
        self.assertIn("ck-mega-feat", self.html)
        self.assertIn("SECTION · RESEARCH", self.html)
        self.assertIn('class="ck-mega-feat" href=', self.html)  # lede is a link
        self.assertIn("All Research tools", self.html)           # explicit CTA

    def test_home_has_no_dropdown(self):
        # Home is the dashboard root — bare link, no group/caret.
        self.assertNotIn('>Home<span class="ck-nav-caret"', self.html)

    def test_caret_count_unchanged(self):
        # Fidelity guard parity: still exactly five carets (one per section).
        self.assertEqual(self.html.count("ck-nav-caret"), 6)  # +Source


class TopbarCssTests(unittest.TestCase):
    def setUp(self):
        self.css = chartis_shell(body="<main/>", title="x")

    def test_dropdown_opens_on_hover_and_focus(self):
        # Hover opens (no-JS fallback); focus opens via the JS controller's
        # `focusin → .is-open` (the old CSS :focus-within rule was removed
        # because it left a focused panel stuck open alongside a hovered one).
        self.assertIn(".ck-nav-group:hover > .ck-nav-menu", self.css)
        self.assertIn(".ck-nav-group.is-open > .ck-nav-menu", self.css)
        self.assertIn("'focusin'", self.css)

    def test_guide_button_is_not_white_on_paper(self):
        # The washed-out white-on-navy override must be gone; the visible
        # ink/green topbar rule governs.
        self.assertNotIn("color:#fff;border:1px solid rgba(255,255,255,.45)",
                         self.css)
        m = re.search(r"\.ck-guide-trigger\s*\{[^}]*\}", self.css)
        self.assertIsNotNone(m)
        self.assertIn("var(--tb-ink)", m.group(0))

    def test_subnav_link_letter_spacing_rule_preserved(self):
        # Reused inside the dropdown; the lock-in rule must still exist.
        self.assertIn(".ck-subnav-link", self.css)

    def test_breadcrumbs_are_not_a_second_bar(self):
        # The breadcrumb strip must not render a full-width bottom-border bar
        # under the topbar (partner-flagged "two bars" look).
        import re
        m = re.search(r"\.ck-breadcrumbs\s*\{[^}]*\}", self.css)
        self.assertIsNotNone(m)
        self.assertNotIn("border-bottom", m.group(0))


if __name__ == "__main__":
    unittest.main()
