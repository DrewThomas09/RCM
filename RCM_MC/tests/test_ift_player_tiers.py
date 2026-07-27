"""Tests for the IFT player-tier public-data guidance module."""
from __future__ import annotations

import unittest


class IftPlayerTiersTests(unittest.TestCase):
    def test_four_commercial_tiers_in_rank_order(self):
        from rcm_mc.market_reports.ift_player_tiers import player_tiers
        s = player_tiers()
        self.assertTrue(s.available)
        keys = [t.key for t in s.tiers]
        self.assertEqual(
            keys,
            ["national", "scaled_regional", "subscaled_regional", "mom_and_pop"])
        # ranks are 1..4, strictly increasing
        self.assertEqual([t.rank for t in s.tiers], [1, 2, 3, 4])

    def test_every_tier_carries_the_guidance_fields(self):
        from rcm_mc.market_reports.ift_player_tiers import player_tiers
        for t in player_tiers().tiers:
            for field in (t.npi_fingerprint, t.best_asset, t.sizing_method,
                          t.systematic_bias, t.examples):
                self.assertTrue(field.strip(), f"{t.key} missing a field")

    def test_national_tier_is_the_undercounted_one(self):
        from rcm_mc.market_reports.ift_player_tiers import player_tiers
        nat = next(t for t in player_tiers().tiers if t.key == "national")
        self.assertIn("INVISIBLE", nat.npi_fingerprint)
        self.assertIn("ownership", nat.sizing_method.lower())

    def test_observed_nppes_probe_matches_run7(self):
        from rcm_mc.market_reports.ift_player_tiers import player_tiers
        probe = player_tiers().nppes_probe
        # the load-bearing OBSERVED counts
        self.assertEqual(probe["Global Medical Response*"]["npis"], 0)
        self.assertEqual(probe["Acadian Ambulance*"]["npis"], 12)
        # every probe row names its tier + a note
        for k, row in probe.items():
            self.assertIn(row["tier"],
                          {"national", "scaled_regional",
                           "subscaled_regional", "mom_and_pop"})
            self.assertTrue(str(row["note"]).strip(), k)

    def test_source_label_names_the_basis(self):
        from rcm_mc.market_reports.ift_player_tiers import player_tiers
        sl = player_tiers().source_label
        for chip in ("OBSERVED", "CLAIMED", "DERIVED"):
            self.assertIn(chip, sl)


if __name__ == "__main__":
    unittest.main()
