"""Tests for the Medicare rate-environment intelligence layer:
fixture integrity, blended-impact math, and the /rate-environment
page registration."""
from __future__ import annotations

import unittest

from rcm_mc.market_intel.rate_environment import (
    blended_rate_impact, get_setting, list_settings,
)
from rcm_mc.ui.rate_environment_page import render_rate_environment


class FixtureTests(unittest.TestCase):
    def test_core_settings_present(self):
        codes = {s.setting for s in list_settings()}
        for code in ("IPPS", "OPPS", "PFS", "ASC", "SNF", "HH",
                     "HOSPICE", "IRF", "ESRD"):
            self.assertIn(code, codes)

    def test_each_setting_has_three_cycles(self):
        for s in list_settings():
            self.assertEqual(len(s.updates), 3, s.setting)
            for u in s.updates:
                self.assertIn(u.status, ("FINAL", "PROPOSED"), s.setting)

    def test_get_setting_case_insensitive(self):
        self.assertIsNotNone(get_setting("pfs"))
        self.assertIsNone(get_setting("NOPE"))

    def test_compound_math(self):
        s = get_setting("IPPS")
        factor = 1.0
        for u in s.updates:
            factor *= 1 + u.net_update_pct / 100.0
        self.assertAlmostEqual(
            s.three_year_compound_pct(), round((factor - 1) * 100, 1))


class BlendedImpactTests(unittest.TestCase):
    def test_single_setting_blend_equals_its_update(self):
        s = get_setting("SNF")
        impact = blended_rate_impact(10_000_000, {"SNF": 100.0})
        self.assertAlmostEqual(impact.blended_update_pct,
                               round(s.latest().net_update_pct, 2))
        self.assertAlmostEqual(
            impact.revenue_impact_usd,
            round(10_000_000 * s.latest().net_update_pct / 100, 2))

    def test_shares_normalized_so_pct_and_fraction_agree(self):
        a = blended_rate_impact(5_000_000, {"PFS": 60.0, "OPPS": 40.0})
        b = blended_rate_impact(5_000_000, {"PFS": 0.6, "OPPS": 0.4})
        self.assertAlmostEqual(a.blended_update_pct, b.blended_update_pct)
        self.assertAlmostEqual(a.revenue_impact_usd, b.revenue_impact_usd)

    def test_unknown_settings_dropped_not_raised(self):
        impact = blended_rate_impact(1_000_000, {"PFS": 50.0, "XX": 50.0})
        self.assertEqual(len(impact.per_setting), 1)
        self.assertEqual(impact.per_setting[0]["setting"], "PFS")
        # The remaining setting carries the whole (normalized) weight.
        self.assertAlmostEqual(impact.per_setting[0]["share_pct"], 100.0)

    def test_empty_or_zero_mix_is_safe(self):
        impact = blended_rate_impact(1_000_000, {})
        self.assertEqual(impact.revenue_impact_usd, 0.0)
        impact = blended_rate_impact(1_000_000, {"PFS": 0.0})
        self.assertEqual(impact.per_setting, [])

    def test_per_setting_dollars_sum_to_total(self):
        impact = blended_rate_impact(
            60_000_000, {"PFS": 40.0, "OPPS": 25.0, "ASC": 20.0,
                         "IPPS": 15.0})
        self.assertAlmostEqual(
            sum(r["revenue_impact_usd"] for r in impact.per_setting),
            impact.revenue_impact_usd, delta=0.05)


class RateEnvironmentPageTests(unittest.TestCase):
    def test_renders_with_identity(self):
        html = render_rate_environment({})
        self.assertIn("Medicare Rate Environment", html)
        self.assertIn("Net payment updates by setting", html)

    def test_junk_params_fall_back_to_defaults(self):
        html = render_rate_environment({"revenue": "xx", "mix_pfs": "-9"})
        self.assertIn("Medicare Rate Environment", html)

    def test_registered_in_palette_and_breadcrumbs(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/rate-environment", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/rate-environment"),
                         "research")


if __name__ == "__main__":
    unittest.main()
