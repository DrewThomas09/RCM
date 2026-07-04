"""Tests for the Texas infusion code-level revenue build + competitor
benchmark surface."""
import unittest

from rcm_mc.diligence.texas_infusion_revenue import (
    cpt_units_and_revenue,
    texas_competitor_benchmark,
)


class CptRevenueTests(unittest.TestCase):
    def setUp(self):
        self.rev = cpt_units_and_revenue()

    def test_revenue_by_code_recomputes_from_units_and_rate(self):
        for c in self.rev["codes"]:
            self.assertEqual(c["revenue"], round(c["units"] * c["rate_nonfac"]))
        # Admin total equals the sum of the per-code revenue.
        self.assertEqual(
            self.rev["totals"]["admin_revenue"],
            round(sum(c["units"] * c["rate_nonfac"]
                      for c in self.rev["codes"])))

    def test_therapeutic_and_biologic_codes_carry_the_line(self):
        by = {c["code"]: c for c in self.rev["codes"]}
        # 96365 (therapeutic) and 96413 (complex biologic) must have units.
        self.assertGreater(by["96365"]["units"], 0)
        self.assertGreater(by["96413"]["units"], 0)

    def test_home_pump_therapies_excluded_from_chair_codes(self):
        rows = {t["therapy"]: t for t in self.rev["therapies"]}
        tpn = next(t for k, t in rows.items() if "Parenteral" in k)
        self.assertFalse(tpn["addressable"])
        self.assertEqual(tpn["annual_visits"], 0)

    def test_gross_revenue_grosses_up_admin(self):
        tot = self.rev["totals"]
        self.assertGreater(tot["gross_revenue_implied"], tot["admin_revenue"])
        self.assertAlmostEqual(
            tot["admin_revenue"] / tot["gross_revenue_implied"],
            tot["admin_share_of_gross"], places=2)


class CompetitorBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.b = texas_competitor_benchmark()

    def test_hhi_matches_named_only_model(self):
        # The benchmark HHI must equal the model's named-only HHI — the
        # fragmented independent pool is atomized, not one firm.
        from rcm_mc.diligence.texas_infusion import _chains, _hhi_named
        self.assertEqual(self.b["hhi"], _hhi_named(_chains()))
        self.assertLess(self.b["hhi"], 1500)  # fragmented

    def test_named_shares_plus_independents_sum_to_one(self):
        total = sum(c["share"] for c in self.b["chains"])
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_players_present_and_texas(self):
        self.assertGreaterEqual(len(self.b["players"]), 5)
        self.assertTrue(all(p.get("tx") for p in self.b["players"]))


class RevenuePageTests(unittest.TestCase):
    def test_page_renders_charts_and_sections(self):
        from rcm_mc.ui.texas_infusion_revenue_page import (
            render_texas_infusion_revenue_page)
        h = render_texas_infusion_revenue_page()
        for needle in (
                "CPT units &amp; revenue by code", "How the units are built",
                "Buy-and-bill revenue bridge", "Texas competitor benchmark",
                "Option Care Health", "96365", "revenue.csv"):
            self.assertIn(needle, h, needle)
        # Revenue-by-code bar + bridge + competitor share at minimum.
        self.assertGreaterEqual(h.count("<svg"), 3)

    def test_route_registered_in_palette(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/diligence/texas-infusion/revenue", routes)

    def test_csv_exports_codes_and_operators(self):
        from rcm_mc.ui.texas_infusion_revenue_page import texas_revenue_csv
        csv = texas_revenue_csv()
        self.assertIn("code,", csv)
        self.assertIn("operator,", csv)
        self.assertIn("96365", csv)


if __name__ == "__main__":
    unittest.main()
