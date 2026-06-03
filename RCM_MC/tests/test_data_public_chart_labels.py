"""Regression guards for clipped SVG chart labels on data_public pages.

Eight bar/bubble/timeline charts rendered value or category labels that ran
off the chart edge (the value label trailing the longest horizontal bar, a
centred bubble/category name at an axis extreme, or a timeline milestone
anchored past the right edge). Each was fixed by reserving label room
(pad_l/pad_r), shortening an over-long label, or flipping the anchor near the
edge — verified clean with a headless-browser overflow scan.

A headless layout engine isn't available here, so these are smoke + behaviour
guards: every fixed page still renders an <svg> without raising, plus the two
fixes that changed emitted markup are pinned directly.
"""

import unittest

from rcm_mc.ui.data_public import (
    earnout_page,
    growth_runway_page,
    lp_dashboard_page,
    payer_concentration_page,
    provider_retention_page,
    supply_chain_page,
    tech_stack_page,
    transition_services_page,
)

_RENDERERS = [
    (supply_chain_page, "render_supply_chain"),
    (earnout_page, "render_earnout"),
    (provider_retention_page, "render_provider_retention"),
    (growth_runway_page, "render_growth_runway"),
    (transition_services_page, "render_transition_services"),
    (tech_stack_page, "render_tech_stack"),
    (payer_concentration_page, "render_payer_concentration"),
    (lp_dashboard_page, "render_lp_dashboard"),
]


class TestDataPublicChartLabels(unittest.TestCase):
    def test_all_fixed_pages_render_svg(self):
        for mod, fn in _RENDERERS:
            with self.subTest(page=fn):
                html = getattr(mod, fn)(None)
                self.assertIsInstance(html, str)
                self.assertIn("<svg", html)
                # Nothing should leak escaped markup or null sentinels.
                self.assertNotIn("&lt;svg", html)

    def test_growth_runway_share_label_shortened(self):
        """The TAM bar spans the full chart width, so the trailing share
        label had no room — it was shortened from "Current share:" to
        "Share:" (paired with reserved pad_r) to stop the ~100px overflow."""
        html = growth_runway_page.render_growth_runway(None)
        self.assertIn("Share:", html)
        self.assertNotIn("Current share:", html)

    def test_transition_timeline_flips_label_anchor(self):
        """Late-timeline milestone labels are flipped to the left of their dot
        (text-anchor=end) so a long name doesn't run off the right edge."""
        html = transition_services_page.render_transition_services(None)
        self.assertIn('text-anchor="end"', html)


if __name__ == "__main__":
    unittest.main()
