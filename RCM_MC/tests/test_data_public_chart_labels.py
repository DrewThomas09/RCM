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
    clinical_outcomes_page,
    competitive_intel_page,
    earnout_page,
    exit_multiple_page,
    growth_runway_page,
    lp_dashboard_page,
    multiple_decomp_page,
    payer_concentration_page,
    provider_retention_page,
    sector_correlation_page,
    supply_chain_page,
    tech_stack_page,
    transition_services_page,
    unit_economics_page,
    value_creation_page,
    value_creation_plan_page,
    vintage_perf_page,
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
    (value_creation_page, "render_value_creation"),
    (multiple_decomp_page, "render_multiple_decomp"),
    (exit_multiple_page, "render_exit_multiple"),
    (clinical_outcomes_page, "render_clinical_outcomes"),
    (competitive_intel_page, "render_competitive_intel"),
    (sector_correlation_page, "render_sector_correlation"),
    (unit_economics_page, "render_unit_economics"),
    (value_creation_plan_page, "render_value_creation_plan"),
]


class TestDataPublicChartLabels(unittest.TestCase):
    def test_all_fixed_pages_render_svg(self):
        for mod, fn in _RENDERERS:
            with self.subTest(page=fn):
                html = getattr(mod, fn)({})
                self.assertIsInstance(html, str)
                self.assertIn("<svg", html)
                # Nothing should leak escaped markup or null sentinels.
                self.assertNotIn("&lt;svg", html)

    def test_growth_runway_share_label_shortened(self):
        """The TAM bar spans the full chart width, so the trailing share
        label had no room — it was shortened from "Current share:" to
        "Share:" (paired with reserved pad_r) to stop the ~100px overflow."""
        html = growth_runway_page.render_growth_runway({})
        self.assertIn("Share:", html)
        self.assertNotIn("Current share:", html)

    def test_transition_timeline_flips_label_anchor(self):
        """Late-timeline milestone labels are flipped to the left of their dot
        (text-anchor=end) so a long name doesn't run off the right edge."""
        html = transition_services_page.render_transition_services({})
        self.assertIn('text-anchor="end"', html)

    def test_deal_flow_heatmap_svgs_are_responsive(self):
        """The two wide year×sector heatmaps used fixed <svg width="{w}">
        (no viewBox), so at a laptop width (~1100px, 2-col page) the right
        edge clipped ~137px. Now responsive (viewBox + width=100%)."""
        from rcm_mc.ui.data_public import deal_flow_heatmap_page as dfh
        html = dfh.render_deal_flow_heatmap()
        self.assertIn("viewBox", html)
        # The wide heatmaps now scale to the column instead of clipping.
        self.assertIn("display:block;max-width:", html)

    def test_vintage_perf_svgs_are_responsive(self):
        """vintage-perf charts used a fixed <svg width="637"> with no viewBox,
        so a narrow column clipped the right edge. They now use viewBox +
        width=100% + max-width so they scale to fit instead of clipping."""
        # Render the chart helpers directly so shell/icon SVGs don't interfere.
        from rcm_mc.data_public.vintage_analytics import compute_vintage_stats
        stats = compute_vintage_stats(vintage_perf_page._load_corpus())
        for fn in ("_moic_bar_chart", "_deal_count_histogram", "_heatmap_svg"):
            svg = getattr(vintage_perf_page, fn)(stats)
            with self.subTest(chart=fn):
                self.assertIn("viewBox", svg)
                self.assertIn("width=\"100%\"", svg)
                self.assertNotRegex(svg, r'<svg width="\d')


if __name__ == "__main__":
    unittest.main()
