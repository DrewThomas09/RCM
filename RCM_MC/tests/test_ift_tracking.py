"""Tests for the IFT three-lever GROWTH TRACKER (ift_tracking).

These pin the load-bearing contracts of the module:

  * The three levers (PRICE / VOLUME / CONSOLIDATION) each build from the REAL
    ift_analytics / ift_clinical_demand / ift_geo spines — not hardcoded parallel
    copies (the reuse tests assert equality against the source functions).
  * Every displayed figure carries exactly one valid honesty basis
    ({GOV, SOURCED, ACADEMIC, ILLUSTRATIVE}); the modeled composites are
    ILLUSTRATIVE and never mislabelled GOV/SOURCED (the prior fabricated-GOV bug).
  * The GOV Medicare AIF anchors the price lever; the SOURCED demand model /
    HCRIS occupancy / destination supply anchor the volume lever.
  * Consolidation is a SHARE-SHIFT, kept OUT of the organic price×volume compound.
  * Every function degrades — never raises — when a dependency is unavailable.
"""
import unittest

from rcm_mc.market_reports import ift_tracking as t
from rcm_mc.market_reports import ift_analytics as an
from rcm_mc.market_reports import ift_clinical_demand as cd


def _all_components(*levers):
    out = []
    for lev in levers:
        out.extend(lev.components)
    return out


class TestPriceLever(unittest.TestCase):
    def setUp(self):
        self.p = t.price_lever()

    def test_available_and_composite_band(self):
        p = self.p
        self.assertTrue(p.available)
        self.assertLessEqual(p.composite_low_pct, p.composite_central_pct)
        self.assertLessEqual(p.composite_central_pct, p.composite_high_pct)
        # brief: composite ~+2-4%/yr
        self.assertGreaterEqual(p.composite_central_pct, 2.0)
        self.assertLessEqual(p.composite_central_pct, 4.0)

    def test_gov_aif_anchor(self):
        p = self.p
        # CY2025 ~2.4% per the brief; the full trend is present and GOV.
        self.assertEqual(p.aif_latest_year, 2025)
        self.assertAlmostEqual(p.aif_latest_pct, 2.4, places=2)
        self.assertIn((2025, 2.4), p.aif_trend)
        self.assertGreaterEqual(len(p.aif_trend), 5)
        # the AIF component is GOV; the composite component is ILLUSTRATIVE.
        gov = [c for c in p.components if c.basis == t.LABEL_GOV]
        illus = [c for c in p.components if c.basis == t.LABEL_ILLUSTRATIVE]
        self.assertTrue(gov, "price lever must carry a GOV AIF/add-on figure")
        self.assertTrue(illus, "price lever must carry an ILLUSTRATIVE composite")
        self.assertTrue(any("AIF" in c.name or "Inflation Factor" in c.name for c in gov))

    def test_conversion_factor_reused_not_reinvented(self):
        # The CF must be the SAME value ift_analytics.fee_schedule() produces,
        # not a parallel hardcoded copy.
        self.assertEqual(self.p.conversion_factor,
                         an.fee_schedule().conversion_factor)

    def test_composite_component_is_illustrative(self):
        comp = [c for c in self.p.components if c.name.startswith("Composite")]
        self.assertTrue(comp)
        for c in comp:
            self.assertEqual(c.basis, t.LABEL_ILLUSTRATIVE)

    def test_degrades_without_conversion_factor(self):
        # A missing CF (None) still builds an available AIF-anchored lever.
        p = t._price_from(None)
        self.assertTrue(p.available)
        self.assertIsNone(p.conversion_factor)
        for c in p.components:
            self.assertIn(c.basis, t._BASES)


class TestVolumeLever(unittest.TestCase):
    def setUp(self):
        self.v = t.volume_lever()

    def test_available_and_composite_band(self):
        v = self.v
        self.assertTrue(v.available)
        self.assertLessEqual(v.composite_low_pct, v.composite_central_pct)
        self.assertLessEqual(v.composite_central_pct, v.composite_high_pct)
        self.assertGreaterEqual(v.composite_central_pct, 2.0)
        self.assertLessEqual(v.composite_central_pct, 4.0)

    def test_demographic_reused_from_demand_model(self):
        # The demographic tailwind must equal the SOURCED demand model's
        # volume-weighted escalation CAGR (×100), not a parallel copy.
        expected = round(
            cd.registry_summary()["escalation_volume_weighted_cagr"] * 100.0, 1)
        self.assertAlmostEqual(self.v.demographic_cagr_pct, expected, places=1)
        self.assertFalse(self.v.demographic_is_modeled_fallback)

    def test_age_bands_match_pop_model(self):
        pop = cd._pop_growth()
        if not pop:
            self.skipTest("demand_forecast model unavailable offline")
        self.assertTrue(self.v.age_band_cagr_pct)
        for band, cagr in self.v.age_band_cagr_pct:
            self.assertAlmostEqual(
                cagr, round(pop[band]["cagr_5yr"] * 100.0, 1), places=1)

    def test_sourced_occupancy_anchor_reused(self):
        occ = an.occupancy_trend()
        if occ.available:
            self.assertEqual(self.v.occupancy_pct, occ.latest_occupancy)
            # at least one SOURCED component (occupancy / supply)
            sourced = [c for c in self.v.components if c.basis == t.LABEL_SOURCED]
            self.assertTrue(sourced, "volume lever must carry a SOURCED anchor")

    def test_degrades_to_labelled_fallback(self):
        # No demand model, no anchors → labelled ILLUSTRATIVE fallback, no raise.
        v = t._volume_from(None, (), None, None, None, None)
        self.assertTrue(v.available)
        self.assertTrue(v.demographic_is_modeled_fallback)
        self.assertGreater(v.composite_central_pct, 0.0)
        for c in v.components:
            self.assertIn(c.basis, t._BASES)


class TestConsolidationLever(unittest.TestCase):
    def setUp(self):
        self.c = t.consolidation_lever()

    def test_available_and_is_share_shift(self):
        c = self.c
        self.assertTrue(c.available)
        # The whole point: consolidation is a SHARE-SHIFT, not organic growth.
        self.assertTrue(c.is_share_shift)
        self.assertIn("share-shift", c.note.lower())
        self.assertLessEqual(c.share_shift_low_pct, c.share_shift_central_pct)
        self.assertLessEqual(c.share_shift_central_pct, c.share_shift_high_pct)

    def test_ratios_reused_from_health_system_sam(self):
        hs = an.health_system_sam()
        if not hs.available:
            self.skipTest("health_system_sam unavailable offline")
        self.assertEqual(self.c.multi_system_ift_share, hs.multi_system_ift_share)
        self.assertEqual(self.c.addressable_share, hs.addressable_share)
        self.assertEqual(self.c.sam_over_som_multiple, hs.sam_over_som_multiple)

    def test_named_consolidators_public_web(self):
        names = " | ".join(self.c.named_consolidators).lower()
        self.assertTrue(self.c.named_consolidators)
        # public-web operators reused from ift_geo, named honestly
        self.assertIn("ameripro", names)
        self.assertIn("midwest medical transport", names)
        self.assertTrue("gmr" in names or "amr" in names or "global medical" in names)
        self.assertIn("public-web", self.c.consolidators_note.lower())

    def test_all_figures_labelled(self):
        for comp in self.c.components:
            self.assertIn(comp.basis, t._BASES)
        # every reused ratio figure is ILLUSTRATIVE; the footprint anchor SOURCED
        self.assertTrue(any(c.basis == t.LABEL_ILLUSTRATIVE for c in self.c.components))

    def test_degrades_without_sam_spine(self):
        c = t._consolidation_from(None, None, None, None, ())
        self.assertTrue(c.available)
        self.assertTrue(c.is_share_shift)
        for comp in c.components:
            self.assertIn(comp.basis, t._BASES)


class TestGrowthBridge(unittest.TestCase):
    def setUp(self):
        self.b = t.growth_bridge()

    def test_available_and_sublevers_embedded(self):
        b = self.b
        self.assertTrue(b.available)
        self.assertIsNotNone(b.price)
        self.assertIsNotNone(b.volume)
        self.assertIsNotNone(b.consolidation)

    def test_market_is_price_times_volume_compound(self):
        b = self.b
        p, v = b.price_central_pct, b.volume_central_pct
        expected = round(((1 + p / 100.0) * (1 + v / 100.0) - 1) * 100.0, 1)
        self.assertAlmostEqual(b.market_growth_central_pct, expected, places=1)
        # compounding, not addition — market exceeds the simple sum minus a hair
        self.assertGreater(b.market_growth_central_pct, 0.0)
        self.assertLessEqual(b.market_growth_low_pct, b.market_growth_central_pct)
        self.assertLessEqual(b.market_growth_central_pct, b.market_growth_high_pct)

    def test_consolidation_is_layered_not_folded(self):
        # Platform growth = organic market growth + consolidation share-shift.
        b = self.b
        self.assertAlmostEqual(
            b.platform_growth_central_pct,
            round(b.market_growth_central_pct
                  + b.consolidation_share_shift_central_pct, 1),
            places=1)
        # Consolidation must ADD to organic growth (a share-gaining platform).
        self.assertGreater(b.platform_growth_central_pct,
                           b.market_growth_central_pct)

    def test_contributions_all_labelled(self):
        for comp in self.b.contributions:
            self.assertIn(comp.basis, t._BASES)
        names = [c.name for c in self.b.contributions]
        self.assertTrue(any("PRICE" in n for n in names))
        self.assertTrue(any("VOLUME" in n for n in names))
        self.assertTrue(any("CONSOLIDATION" in n for n in names))

    def test_degrades_when_organic_levers_unavailable(self):
        # Feed the pure assembler unavailable (real) sub-levers → available=False,
        # no raise, still a labelled result.
        b = t._assemble_bridge(
            t.PriceLever(available=False),
            t.VolumeLever(available=False),
            t.ConsolidationLever(available=False))
        self.assertFalse(b.available)
        self.assertTrue(b.source_label)
        for comp in b.contributions:
            self.assertIn(comp.basis, t._BASES)


class TestHonestyLabelsAcrossModule(unittest.TestCase):
    def test_every_figure_carries_a_valid_basis(self):
        p, v, c, b = (t.price_lever(), t.volume_lever(),
                      t.consolidation_lever(), t.growth_bridge())
        figs = _all_components(p, v, c) + list(b.contributions)
        self.assertTrue(figs)
        for comp in figs:
            self.assertIn(comp.basis, t._BASES,
                          f"{comp.name!r} basis {comp.basis!r} not in {t._BASES}")

    def test_source_labels_lead_with_a_valid_basis(self):
        # A source_label leads with its DOMINANT honest basis, split on ' · '.
        for res in (t.price_lever(), t.volume_lever(),
                    t.consolidation_lever(), t.growth_bridge()):
            head = res.source_label.split(" · ")[0].strip()
            self.assertIn(head, t._BASES,
                          f"source_label must lead with a basis: {res.source_label!r}")
            # the composites are modeled, so they lead ILLUSTRATIVE
            self.assertEqual(head, t.LABEL_ILLUSTRATIVE)

    def test_no_result_is_empty(self):
        for res in (t.price_lever(), t.volume_lever(),
                    t.consolidation_lever(), t.growth_bridge()):
            self.assertTrue(res.available)
            self.assertTrue(res.source_label)
            self.assertTrue(res.headline)
            self.assertTrue(res.note)


class TestDegradeNeverRaise(unittest.TestCase):
    def test_public_functions_never_raise(self):
        # Called repeatedly (also exercising the lru_cache) — must never throw.
        for _ in range(2):
            for fn in (t.price_lever, t.volume_lever,
                       t.consolidation_lever, t.growth_bridge):
                res = fn()
                self.assertIsNotNone(res)
                self.assertIn(res.available, (True, False))
        levers = t.all_levers()
        self.assertEqual(len(levers), 3)


if __name__ == "__main__":
    unittest.main()
