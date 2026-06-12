"""Tests for the Pricing Power analyzer (/pricing-power): elasticity
math, locked-segment handling, and registration."""
from __future__ import annotations

import unittest

from rcm_mc.data_public.pricing_power import (
    SECTORS, SegmentPricing, _curve, compute_pricing_power,
)
from rcm_mc.ui.data_public.pricing_power_page import render_pricing_power


class CurveMathTests(unittest.TestCase):
    def test_volume_response_follows_elasticity(self):
        seg = SegmentPricing("t", 1_000_000, 60.0, -1.0, "")
        curve = _curve(seg)
        up5 = next(p for p in curve.curve if p.price_change_pct == 5.0)
        # ε = -1: (1.05)^-1 - 1 ≈ -4.8% volume.
        self.assertAlmostEqual(up5.volume_change_pct, -4.8, places=1)

    def test_elasticity_boundary_flips_the_optimal_direction(self):
        # The economic boundary: d(EBITDA)/dp at 0 is ε·m + 1, so the
        # optimum flips from increase to cut at ε* = -1/margin. At 60%
        # margin ε* = -1.67: a -1.5 segment still takes an increase, a
        # -2.0 segment optimally cuts.
        inc = _curve(SegmentPricing("t", 1_000_000, 60.0, -1.5, ""))
        cut = _curve(SegmentPricing("t", 1_000_000, 60.0, -2.0, ""))
        self.assertGreater(inc.optimal_price_change_pct, 0)
        self.assertLess(cut.optimal_price_change_pct, 0)

    def test_inelastic_segment_takes_an_increase(self):
        seg = SegmentPricing("t", 1_000_000, 60.0, -0.3, "")
        c = _curve(seg)
        self.assertGreater(c.optimal_price_change_pct, 0)
        self.assertGreater(c.optimal_ebitda_gain_usd, 0)

    def test_locked_segment_has_no_lever(self):
        seg = SegmentPricing("t", 1_000_000, 60.0, -0.3, "",
                             price_locked=True)
        c = _curve(seg)
        self.assertTrue(c.price_locked)
        self.assertEqual(c.optimal_price_change_pct, 0.0)
        self.assertEqual(c.optimal_ebitda_gain_usd, 0.0)
        self.assertEqual(len(c.curve), 1)

    def test_zero_move_is_zero_change(self):
        seg = SegmentPricing("t", 1_000_000, 60.0, -0.8, "")
        zero = next(p for p in _curve(seg).curve
                    if p.price_change_pct == 0.0)
        self.assertEqual(zero.revenue_change_usd, 0.0)
        self.assertEqual(zero.ebitda_change_usd, 0.0)


class ComputeTests(unittest.TestCase):
    def test_blended_elasticity_is_revenue_weighted(self):
        r = compute_pricing_power(SECTORS[0])
        self.assertLess(r.blended_elasticity, 0)

    def test_portfolio_gain_sums_segment_optima(self):
        r = compute_pricing_power(SECTORS[0])
        self.assertAlmostEqual(
            r.portfolio_optimal_ebitda_gain_usd,
            round(sum(s.optimal_ebitda_gain_usd for s in r.segments), 2))

    def test_every_sector_has_a_locked_or_movable_read(self):
        for sector in SECTORS:
            r = compute_pricing_power(sector)
            self.assertTrue(r.headline)
            self.assertGreater(len(r.segments), 1)

    def test_unknown_sector_falls_back(self):
        r = compute_pricing_power("Not A Sector")
        self.assertEqual(r.sector, SECTORS[0])


class PricingPowerPageTests(unittest.TestCase):
    def test_renders_with_identity_and_provenance(self):
        html = render_pricing_power({})
        self.assertIn("Pricing Power Analyzer", html)
        self.assertIn("ck-illus-note", html)
        self.assertIn("Price-response curves", html)

    def test_locked_segment_renders_locked_chip(self):
        html = render_pricing_power({"sector": "Home Health"})
        self.assertIn("LOCKED", html)

    def test_malicious_sector_param_is_neutralized(self):
        html = render_pricing_power({"sector": "<script>x()</script>"})
        self.assertNotIn("<script>x()</script>", html)

    def test_registered_in_palette_and_breadcrumbs(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/pricing-power", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/pricing-power"), "diligence")



class CustomSegmentTests(unittest.TestCase):
    def test_custom_segment_appends_to_book(self):
        html = render_pricing_power({"custom_rev": "10",
                                     "custom_margin": "65",
                                     "custom_eps": "-0.6"})
        self.assertIn("Custom segment (your inputs)", html)

    def test_positive_elasticity_clamped_not_errored(self):
        # ε > 0 is a data-entry error; clamp to 0 (no volume response)
        # rather than modeling a Giffen good or 500ing.
        html = render_pricing_power({"custom_rev": "10",
                                     "custom_eps": "3"})
        self.assertIn("elasticity 0.00", html)

    def test_zero_revenue_means_no_custom_segment(self):
        html = render_pricing_power({"custom_rev": "0"})
        self.assertNotIn("Custom segment (your inputs)", html)

    def test_compute_accepts_extra_segment(self):
        from rcm_mc.data_public.pricing_power import SegmentPricing
        base = compute_pricing_power(SECTORS[0])
        extra = SegmentPricing("X", 5_000_000, 60.0, -0.5, "")
        r = compute_pricing_power(SECTORS[0], extra_segment=extra)
        self.assertEqual(len(r.segments), len(base.segments) + 1)
        self.assertAlmostEqual(r.total_revenue_usd,
                               base.total_revenue_usd + 5_000_000)


class PricingPowerXlsxTests(unittest.TestCase):
    def test_workbook_has_live_elasticity_math_and_locked_rows(self):
        import io
        import zipfile
        from rcm_mc.ui.data_public.pricing_power_page import (
            pricing_power_xlsx,
        )
        data = pricing_power_xlsx({"sector": "Home Health"})
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn(")^D", xml)            # (1+move)^elasticity
        self.assertIn("LOCKED", xml)         # administered segment

    def test_page_links_the_download(self):
        html = render_pricing_power({})
        self.assertIn("/pricing-power.xlsx?sector=", html)

if __name__ == "__main__":
    unittest.main()
