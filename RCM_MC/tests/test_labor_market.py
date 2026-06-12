"""Tests for the healthcare labor-market intelligence layer
(/labor-market): fixture integrity, stress math, fragility scoring,
and registration."""
from __future__ import annotations

import unittest

from rcm_mc.market_intel.labor_market import (
    get_role, labor_cost_stress, list_roles,
)
from rcm_mc.ui.labor_market_page import render_labor_market


class FixtureTests(unittest.TestCase):
    def test_core_roles_present(self):
        codes = {r.role for r in list_roles()}
        for code in ("RN", "LPN", "CNA", "MA", "NP_PA", "PHYS_PC",
                     "PHYS_SPEC", "THERAPY", "PHARM", "RCM_ADMIN"):
            self.assertIn(code, codes)

    def test_values_in_plausible_ranges(self):
        for r in list_roles():
            self.assertTrue(15 <= r.median_hourly_usd <= 300, r.role)
            self.assertTrue(0 < r.wage_yoy_pct <= 8, r.role)
            self.assertTrue(0 < r.turnover_pct <= 50, r.role)

    def test_fragility_bounded_and_ordered(self):
        roles = {r.role: r for r in list_roles()}
        for r in roles.values():
            self.assertTrue(0 <= r.fragility_score() <= 100, r.role)
        # The structural read the score exists for: aides are harder to
        # hold than specialist physicians.
        self.assertGreater(roles["CNA"].fragility_score(),
                           roles["PHYS_SPEC"].fragility_score())

    def test_get_role_case_insensitive(self):
        self.assertIsNotNone(get_role("rn"))
        self.assertIsNone(get_role("CEO"))


class StressMathTests(unittest.TestCase):
    def test_single_role_blend_equals_its_wage_growth(self):
        rn = get_role("RN")
        s = labor_cost_stress(10_000_000, {"RN": 100.0})
        self.assertAlmostEqual(s.blended_wage_growth_pct,
                               round(rn.wage_yoy_pct, 2))
        self.assertAlmostEqual(
            s.annual_cost_increase_usd,
            round(10_000_000 * rn.wage_yoy_pct / 100, 2))

    def test_pct_and_fraction_mixes_agree(self):
        a = labor_cost_stress(5_000_000, {"RN": 60.0, "MA": 40.0})
        b = labor_cost_stress(5_000_000, {"RN": 0.6, "MA": 0.4})
        self.assertAlmostEqual(a.blended_wage_growth_pct,
                               b.blended_wage_growth_pct)

    def test_margin_bps_only_with_revenue(self):
        s = labor_cost_stress(10_000_000, {"RN": 100.0})
        self.assertEqual(s.ebitda_margin_impact_bps, 0.0)
        s = labor_cost_stress(10_000_000, {"RN": 100.0},
                              revenue_usd=50_000_000)
        rn = get_role("RN")
        expected = 10_000_000 * rn.wage_yoy_pct / 100 / 50_000_000 * 10_000
        self.assertAlmostEqual(s.ebitda_margin_impact_bps,
                               round(expected, 1))

    def test_unknown_roles_dropped_and_empty_safe(self):
        s = labor_cost_stress(1_000_000, {"RN": 50.0, "XX": 50.0})
        self.assertEqual(len(s.per_role), 1)
        self.assertAlmostEqual(s.per_role[0]["share_pct"], 100.0)
        s = labor_cost_stress(1_000_000, {})
        self.assertEqual(s.annual_cost_increase_usd, 0.0)

    def test_per_role_dollars_sum_to_total(self):
        s = labor_cost_stress(
            32_000_000, {"PHYS_PC": 25, "PHYS_SPEC": 15, "NP_PA": 10,
                         "RN": 15, "MA": 15, "RCM_ADMIN": 20})
        self.assertAlmostEqual(
            sum(r["cost_increase_usd"] for r in s.per_role),
            s.annual_cost_increase_usd, delta=0.05)


class LaborMarketPageTests(unittest.TestCase):
    def test_renders_with_identity(self):
        html = render_labor_market({})
        self.assertIn("Healthcare Labor Market", html)
        self.assertIn("Role economics", html)
        self.assertIn("Wage-inflation stress", html)

    def test_junk_params_fall_back(self):
        html = render_labor_market({"labor": "xx", "mix_rn": "-5"})
        self.assertIn("Healthcare Labor Market", html)

    def test_registered_in_palette_and_breadcrumbs(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/labor-market", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/labor-market"), "research")


if __name__ == "__main__":
    unittest.main()
