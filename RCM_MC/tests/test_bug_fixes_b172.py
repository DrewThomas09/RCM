"""b172 — top-bar overlap + drop the "Chartis" brand name from the UI.

Two top-bar fixes requested together:

1. **Overlap.** The nav had ``flex:0 1 auto; min-width:0``, which let it shrink
   below its content width so the ``white-space:nowrap`` links spilled
   rightward and overlapped the right zone (mode chip / search / +New). The
   fix drops ``min-width:0`` (so the links stay in flow at their natural width)
   and lets ``.ck-topbar-inner`` wrap — with ``min-height`` (not a hard
   height), the bar GROWS a row instead of overlapping when a width is too
   tight.

2. **Branding.** The consulting workspace mode read "Chartis Consulting" in the
   top-bar mode chip and the settings copy. Renamed to "Consulting" so no
   user-facing surface says "Chartis".
"""
from __future__ import annotations

import unittest


class TestNoChartisInUI(unittest.TestCase):
    def test_mode_labels_have_no_chartis(self):
        from rcm_mc.ui._workspace_mode import MODE_LABELS, CONSULTING
        self.assertEqual(MODE_LABELS[CONSULTING], "Consulting")
        for v in MODE_LABELS.values():
            self.assertNotIn("Chartis", v)

    def test_topbar_consulting_mode_has_no_chartis(self):
        from rcm_mc.ui._workspace_mode import set_workspace_mode
        from rcm_mc.ui._chartis_kit import _topbar
        try:
            set_workspace_mode("consulting")
            html = _topbar("home")
        finally:
            set_workspace_mode("partner")
        self.assertNotIn("Chartis", html)
        self.assertIn("Consulting", html)   # the renamed mode chip

    def test_workspace_settings_page_has_no_chartis(self):
        from rcm_mc.ui.settings_pages import render_workspace_mode_page
        self.assertNotIn("Chartis", render_workspace_mode_page())


class TestTopbarOverlapGuard(unittest.TestCase):
    def test_inner_wraps_and_nav_has_no_min_width_zero(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        sh = chartis_shell("<p>x</p>", "T")
        # The anti-overlap guard: the inner bar wraps (grows) rather than
        # letting items slide on top of each other.
        self.assertIn(".ck-topbar-inner", sh)
        self.assertIn("flex-wrap:wrap", sh)
        # The spill-causing min-width:0 on .ck-nav must be gone.
        self.assertNotIn(".ck-nav { display:flex; flex-wrap:nowrap; gap:0; "
                         "flex:0 1 auto; min-width:0; }", sh)


if __name__ == "__main__":
    unittest.main()
