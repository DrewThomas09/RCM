"""Top-bar design-fidelity guards (handoff: ~/Desktop/top_bar_redesign).

Pins the fidelity fixes that bring the editorial paper top bar closer to the
Claude handoff: the green "?" Guide glyph (so Guide reads live, not washed
out / disabled), the handoff right-zone order (search → Guide → +New →
avatar), a non-truncating short search placeholder, and the absence of any
external prototype scripts/CDNs. Existing Guide/search/avatar behavior hooks
must be preserved.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import _topbar


class TopBarFidelityTests(unittest.TestCase):
    def setUp(self):
        self.html = _topbar("home")

    def test_nav_chevrons_on_sections_not_home(self):
        # Handoff: nav items with a section sub-nav show a dropdown caret;
        # Home (dashboard root) does not.
        pipeline = _topbar("pipeline")
        self.assertEqual(pipeline.count("ck-nav-caret"), 6)  # all but Home (+Source)
        # Home itself carries no caret immediately after its label.
        self.assertNotIn('>Home<span class="ck-nav-caret"', pipeline)
        # The active section's caret renders.
        self.assertIn('class="active">Pipeline<span class="ck-nav-caret"', pipeline)

    def test_guide_has_green_glyph_and_is_not_disabled(self):
        self.assertIn("ck-guide-glyph", self.html)
        self.assertIn(">?</span>Guide</button>", self.html)
        # Guide must be a usable button, never disabled.
        self.assertIn('class="ck-guide-trigger" type="button"', self.html)
        self.assertNotIn("ck-guide-trigger disabled", self.html)
        self.assertNotIn('ck-guide-trigger" disabled', self.html)

    def test_guide_uses_existing_trigger_hook(self):
        self.assertIn("data-ck-guide-open", self.html)
        self.assertIn('aria-controls="ck-guide-panel"', self.html)

    def test_right_zone_order_search_then_guide(self):
        # Handoff order: search · Guide · +New · avatar.
        i_search = self.html.find("ck-search-form")
        i_guide = self.html.find("ck-guide-trigger")
        i_new = self.html.find("ck-newdeal-cta")
        i_av = self.html.find("ck-user-chip")
        self.assertTrue(0 < i_search < i_guide < i_new < i_av,
                        "right zone not in handoff order")

    def test_search_launcher_present_and_not_truncating(self):
        self.assertIn('class="ck-search"', self.html)
        self.assertIn("⌘K", self.html)
        # Short visible placeholder so it never clips in the 220px field;
        # the descriptive text moves to aria-label.
        self.assertIn('placeholder="Search…"', self.html)
        self.assertIn('aria-label="Search deals, hospitals, routes"', self.html)

    def test_new_deal_and_avatar_present(self):
        self.assertIn("ck-newdeal-cta", self.html)
        self.assertIn("+ New deal", self.html)
        self.assertIn("ck-user-chip", self.html)

    def test_no_external_prototype_scripts(self):
        low = self.html.lower()
        for bad in ("unpkg", "react.development", "babel", "cdn.jsdelivr",
                    "react-dom"):
            self.assertNotIn(bad, low)

    def test_wordmark_preserved(self):
        self.assertIn("ck-wordmark", self.html)
        self.assertIn("PE", self.html)


if __name__ == "__main__":
    unittest.main()
