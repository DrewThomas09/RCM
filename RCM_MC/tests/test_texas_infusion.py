"""Texas infusion market — sizing, segmentation, concentration, metros.

Every figure is a pure function of named-source constants + the real
ACS population (via demographics_state / cbsa_demographics), so the
sizing, the HHI, and the metro ranking all recompute and audit.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.texas_infusion import (
    US_POPULATION_2024, build_texas_infusion_analysis,
    texas_infusion_model, texas_metro_breakdown, texas_provider_landscape,
)
from rcm_mc.diligence.tam_sam import compute


class SizingTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_tam_chain_is_population_scaled(self):
        # TX patient base = US 3.2M × (TX pop / US pop).
        demo = self.a["demographics"]
        model = texas_infusion_model(demo["population"])
        base = model.chain[0].value
        expected = round(3_200_000 * demo["population"] / US_POPULATION_2024)
        self.assertEqual(base, expected)
        # TAM = base × 18 × 650, via the verified compute().
        self.assertAlmostEqual(
            compute(model)["tam"], base * 18 * 650, places=0)

    def test_tam_in_expected_billions(self):
        tam = self.a["sizing"]["tam"]
        # TX share ~9% of a ~$37B US market → ~$3.0-3.7B.
        self.assertGreater(tam, 2.5e9)
        self.assertLess(tam, 4.5e9)

    def test_sam_som_nest(self):
        s = self.a["sizing"]
        self.assertLess(s["som"], s["sam"])
        self.assertLess(s["sam"], s["tam"])

    def test_segments_sum_to_one_and_have_fastest(self):
        segs = self.a["sizing"]["segments"]
        self.assertAlmostEqual(
            sum(x["share_of_volume"] for x in segs), 1.0, places=3)
        self.assertTrue(any(x.get("is_fastest") for x in segs))

    def test_site_of_care_hopd_declines(self):
        site = {s["site"]: s for s in self.a["site_of_care"]}
        self.assertAlmostEqual(
            sum(s["share"] for s in self.a["site_of_care"]), 1.0, places=3)
        hopd = next(s for k, s in site.items() if "HOPD" in k)
        self.assertLess(hopd["growth_pct"], 0)        # being steered away
        self.assertLess(hopd["tam_y5"], hopd["tam_today"])

    def test_payer_mix_sums_to_one(self):
        self.assertAlmostEqual(
            sum(p["share"] for p in self.a["payer_mix"]), 1.0, places=3)


class ConcentrationTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_chain_shares_sum_to_one(self):
        self.assertAlmostEqual(
            sum(c["share"] for c in self.a["chains"]), 1.0, places=3)

    def test_hhi_is_fragmented(self):
        # Named-chain HHI well below the DOJ 1500 line → fragmented.
        self.assertLess(self.a["hhi"], 1500)
        self.assertIn("fragment", self.a["hhi_band"])

    def test_hhi_equals_sum_of_squared_named_shares(self):
        named = [c for c in self.a["chains"] if c.get("named")]
        expected = round(sum((c["share"] * 100) ** 2 for c in named), 0)
        self.assertEqual(self.a["hhi"], expected)

    def test_fragmentation_verdict_names_top_operator(self):
        frag = self.a["fragmentation"]
        self.assertIn("Option Care", frag["top_operator"])
        self.assertGreater(frag["independent_pool_share"], 0.4)

    def test_health_system_capacity_is_hopd_share(self):
        hs = self.a["health_system_capacity"]
        hopd = next(s for s in self.a["site_of_care"] if "HOPD" in s["site"])
        self.assertEqual(hs["hopd_share"], hopd["share"])


class ProviderAndMetroTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_provider_counts_population_scaled(self):
        pl = self.a["provider_landscape"]
        tx_share = self.a["tx_population_share"]
        self.assertEqual(pl["home_infusion_locations"], round(800 * tx_share))
        self.assertEqual(pl["ambulatory_infusion_centers"],
                         round(1_600 * tx_share))

    def test_metros_are_the_four_big_ones_ranked(self):
        metros = self.a["metros"]
        self.assertEqual(len(metros), 4)
        names = {m["metro"].split("-")[0] for m in metros}
        self.assertTrue({"Dallas", "Houston", "Austin", "San Antonio"}
                        & names)
        # Ranked descending by attractiveness, ranks 1..4.
        scores = [m["attractiveness"] for m in metros]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([m["rank"] for m in metros], [1, 2, 3, 4])

    def test_metro_demand_uses_real_population(self):
        # Each metro carries a real (multi-hundred-thousand) senior count
        # and a positive referral density.
        for m in self.a["metros"]:
            self.assertGreater(m["seniors"], 100_000)
            self.assertGreater(m["referral_density_per_100k"], 0)
            self.assertGreaterEqual(m["attractiveness"], 0)
            self.assertLessEqual(m["attractiveness"], 100)

    def test_population_growth_present(self):
        g = self.a["population_growth"]
        self.assertEqual(g["tx_pop_gain_2024"], 562_941)
        self.assertGreater(g["tx_senior_growth_pct"], g["tx_pop_growth_pct"])


class PageRenderTests(unittest.TestCase):
    def test_page_renders_all_sections(self):
        from rcm_mc.ui.texas_infusion_page import render_texas_infusion_page
        h = render_texas_infusion_page()
        for needle in (
            "Texas Infusion Market", "driver chain", "therapy form",
            "site of care", "Provider landscape", "Metro attractiveness",
            "Concentration", "Payer mix", "Medicare population",
            "Certificate of Need", "Sources", "562,941",
            "Home-infusion locations", "Competitive read",
        ):
            self.assertIn(needle, h, f"missing section: {needle}")

    def test_route_registered_in_palette(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/diligence/texas-infusion", routes)


if __name__ == "__main__":
    unittest.main()
