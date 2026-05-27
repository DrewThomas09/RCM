"""State Rankings (/state-rankings): a single-metric screening leaderboard over
all 50 states + DC, built on the shared metric registry. Guards real-value
ranking, correct sort direction, honest handling of states with no data, metric
validation, and GREEN surface classification.
"""
import unittest

from rcm_mc.diligence.surface_status import classify_surface
from rcm_mc.ui.data_public.state_rankings_page import (
    _DEFAULT_METRIC,
    _parse_metric,
    _ranking,
    render_state_rankings,
)


class StateRankingsTests(unittest.TestCase):
    def test_parse_metric_validates(self):
        self.assertEqual(_parse_metric({"metric": ["population"]}), "population")
        self.assertEqual(_parse_metric({"metric": ["bogus"]}), _DEFAULT_METRIC)
        self.assertEqual(_parse_metric({}), _DEFAULT_METRIC)

    def test_ranking_sorts_higher_is_better_descending(self):
        ranked, missing = _ranking("population")
        self.assertTrue(ranked)
        vals = [v for _, v in ranked]
        self.assertEqual(vals, sorted(vals, reverse=True))
        # CA is the most populous state — it should top a population ranking
        self.assertEqual(ranked[0][0], "CA")

    def test_ranking_lower_is_better_ascending(self):
        # uninsured rate: lower is better, so the lowest-burden state ranks #1
        ranked, _ = _ranking("uninsured_acs")
        vals = [v for _, v in ranked]
        self.assertEqual(vals, sorted(vals))

    def test_missing_states_listed_not_ranked(self):
        ranked, missing = _ranking("population")
        ranked_states = {s for s, _ in ranked}
        # no state appears both ranked and missing — never double-counted/faked
        self.assertTrue(ranked_states.isdisjoint(set(missing)))
        # every ranked + missing state is unique and within the 50+DC universe
        self.assertEqual(len(ranked) + len(missing), 51)

    def test_page_renders(self):
        h = render_state_rankings({"metric": ["uninsured_acs"]})
        self.assertIn("State Rankings", h)
        self.assertIn("<table", h)
        self.assertIn("fabricated", h)

    def test_page_leads_with_real_kpi_strip(self):
        # X-Ray pattern: leading KPI strip computed from the real ranking
        # (states ranked / #1 state / national median), not just a table.
        h = render_state_rankings({"metric": ["population"]})
        self.assertIn("ck-kpi-strip", h)
        self.assertIn("States ranked", h)
        self.assertIn("National median", h)

    def test_surface_is_green(self):
        self.assertEqual(classify_surface("/state-rankings")["tier"], "green")


if __name__ == "__main__":
    unittest.main()
