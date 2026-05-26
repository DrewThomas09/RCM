"""The surface-ranking engine (scripts/rank_surfaces.py).

Pins the scoring contract used to decide front-facing nav promotion: scores
stay in range, the Target Screener leads, and the shared kit is never ranked
as a page.
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "rank_surfaces.py"
_spec = importlib.util.spec_from_file_location("rank_surfaces", _SCRIPT)
rank = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rank)


class RankingEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = rank.build_rankings()

    def test_produces_rows(self):
        self.assertGreater(len(self.rows), 50)

    def test_scores_in_range(self):
        for r in self.rows:
            self.assertGreaterEqual(r["effort"], 0.0)
            self.assertLessEqual(r["effort"], 5.0)
            self.assertGreaterEqual(r["useful"], 0.0)
            self.assertLessEqual(r["useful"], 5.0)
            # Usefulness weighted 1.5×, normalized to 0-10.
            expected = round((r["useful"] * 1.5 + r["effort"]) * 10.0 / 12.5, 1)
            self.assertAlmostEqual(r["total"], expected)
            self.assertLessEqual(r["total"], 10.0)

    def test_sorted_descending(self):
        totals = [r["total"] for r in self.rows]
        self.assertEqual(totals, sorted(totals, reverse=True))

    def test_target_screener_is_top_ranked(self):
        # The flagship workbench should lead the ranking.
        self.assertEqual(self.rows[0]["route"], "/target-screener")

    def test_shared_kit_excluded(self):
        mods = {r["module"] for r in self.rows}
        self.assertNotIn("_chartis_kit", mods)

    def test_effort_buckets(self):
        self.assertEqual(rank._effort_score(1600, False), 5.0)
        self.assertEqual(rank._effort_score(1600, True), 5.0)   # capped
        self.assertEqual(rank._effort_score(300, False), 2.0)
        self.assertEqual(rank._effort_score(300, True), 2.5)    # +0.5 tested

    def test_usefulness_caps_at_5(self):
        self.assertLessEqual(
            rank._usefulness_score("green", "diligence", True, True), 5.0)


if __name__ == "__main__":
    unittest.main()
