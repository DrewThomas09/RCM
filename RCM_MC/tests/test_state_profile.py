"""State Profile (/state-profile): a single-state dossier showing every real
metric for one state with its national rank. Guards state validation, correct
rank computation (incl. direction), honest unranked handling, and GREEN surface.
"""
import unittest

from rcm_mc.diligence.surface_status import classify_surface
from rcm_mc.ui.data_public.state_profile_page import (
    _DEFAULT,
    _all_ranked,
    _parse_state,
    _us_median,
    profile_dataframe,
    render_state_profile,
)


class StateProfileTests(unittest.TestCase):
    def test_parse_state_validates(self):
        self.assertEqual(_parse_state({"state": ["tx"]}), "TX")
        self.assertEqual(_parse_state({"state": ["ZZ"]}), _DEFAULT)
        self.assertEqual(_parse_state({}), _DEFAULT)

    def test_population_rank_puts_ca_first(self):
        ranked = _all_ranked()
        pop = ranked["population"]
        self.assertEqual(pop[0][0], "CA")  # most populous → rank #1

    def test_lower_is_better_metric_ranks_ascending(self):
        ranked = _all_ranked()
        vals = [v for _, v in ranked["uninsured_acs"]]
        self.assertEqual(vals, sorted(vals))  # lowest uninsured ranks #1

    def test_us_median_robust(self):
        self.assertEqual(_us_median([1, 2, 3]), 2)
        self.assertEqual(_us_median([1, 2, 3, 4]), 2.5)
        self.assertIsNone(_us_median([]))
        self.assertEqual(_us_median([5, None, 1]), 3)  # ignores missing

    def test_page_shows_rank_state_and_median(self):
        h = render_state_profile({"state": ["CA"]})
        self.assertIn("State Profile", h)
        self.assertIn("California", h)
        self.assertIn("National rank", h)
        self.assertIn("vs U.S. median", h)
        self.assertIn("fabricated", h)

    def test_csv_has_vs_median_column(self):
        df = profile_dataframe("CA")
        self.assertIn("VsUSMedianPct", df.columns)
        # population is way above the median → a large positive delta
        vs = df.loc[df["Metric"] == "Population", "VsUSMedianPct"].iloc[0]
        self.assertGreater(vs, 0)

    def test_surface_is_green(self):
        self.assertEqual(classify_surface("/state-profile")["tier"], "green")


if __name__ == "__main__":
    unittest.main()
