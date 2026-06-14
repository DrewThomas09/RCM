"""Tests for episode-of-care grouping + service-line P&L."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.episodes import (
    ClaimLine,
    EpisodeDefinition,
    group_episodes,
)

DEF = EpisodeDefinition(
    anchor_service_lines=frozenset({"inpatient", "surgery"}),
    pre_window_days=0, post_window_days=90,
)


class EpisodeGroupingTests(unittest.TestCase):

    def test_single_anchor_episode(self):
        claims = [
            ClaimLine("p1", 100, 10000.0, "inpatient"),
            ClaimLine("p1", 120, 500.0, "physician"),     # within 90d
            ClaimLine("p1", 150, 300.0, "rehab"),         # within 90d
        ]
        res = group_episodes(claims, DEF)
        self.assertEqual(res.n_episodes, 1)
        self.assertEqual(res.n_claims_assigned, 3)
        self.assertAlmostEqual(res.episodes[0].total_cost, 10800.0)

    def test_claims_outside_window_unassigned(self):
        claims = [
            ClaimLine("p1", 100, 10000.0, "inpatient"),
            ClaimLine("p1", 300, 500.0, "physician"),     # >90d after anchor
        ]
        res = group_episodes(claims, DEF)
        self.assertEqual(res.n_episodes, 1)
        self.assertEqual(res.n_claims_assigned, 1)
        self.assertEqual(res.n_claims_unassigned, 1)

    def test_patient_with_no_anchor_all_unassigned(self):
        claims = [
            ClaimLine("p1", 100, 200.0, "physician"),
            ClaimLine("p1", 110, 150.0, "lab"),
        ]
        res = group_episodes(claims, DEF)
        self.assertEqual(res.n_episodes, 0)
        self.assertEqual(res.n_claims_unassigned, 2)

    def test_overlapping_anchors_merge(self):
        # Two admissions 30 days apart → windows overlap → one episode.
        claims = [
            ClaimLine("p1", 100, 8000.0, "inpatient"),
            ClaimLine("p1", 130, 9000.0, "inpatient"),
            ClaimLine("p1", 140, 400.0, "physician"),
        ]
        res = group_episodes(claims, DEF)
        self.assertEqual(res.n_episodes, 1)
        self.assertEqual(res.episodes[0].n_claims, 3)

    def test_non_overlapping_anchors_separate(self):
        # Two admissions 200 days apart → two episodes.
        claims = [
            ClaimLine("p1", 100, 8000.0, "inpatient"),
            ClaimLine("p1", 400, 9000.0, "inpatient"),
        ]
        res = group_episodes(claims, DEF)
        self.assertEqual(res.n_episodes, 2)

    def test_multiple_patients(self):
        claims = [
            ClaimLine("p1", 100, 10000.0, "surgery"),
            ClaimLine("p2", 100, 12000.0, "inpatient"),
            ClaimLine("p2", 110, 600.0, "physician"),
        ]
        res = group_episodes(claims, DEF)
        self.assertEqual(res.n_episodes, 2)
        self.assertEqual({e.patient_id for e in res.episodes}, {"p1", "p2"})

    def test_service_line_pnl_with_revenue(self):
        claims = [
            ClaimLine("p1", 100, 8000.0, "inpatient", revenue=10000.0),
            ClaimLine("p1", 110, 2000.0, "rehab", revenue=1500.0),
        ]
        res = group_episodes(claims, DEF)
        pnl = {p.service_line: p for p in res.service_line_pnl}
        self.assertIn("inpatient", pnl)
        # Episode revenue 11500 allocated by cost share (8000/10000 vs 2000/10000)
        self.assertGreater(pnl["inpatient"].total_revenue, 0)
        self.assertIsNotNone(pnl["inpatient"].margin)

    def test_cost_percentiles(self):
        claims = [
            ClaimLine(f"p{i}", 100, float(1000 * (i + 1)), "surgery")
            for i in range(10)
        ]
        res = group_episodes(claims, DEF)
        self.assertEqual(res.n_episodes, 10)
        self.assertGreater(res.p90_cost, res.median_cost)

    def test_empty(self):
        res = group_episodes([], DEF)
        self.assertEqual(res.n_episodes, 0)
        self.assertEqual(res.mean_cost, 0.0)

    def test_headline_and_dict(self):
        claims = [ClaimLine("p1", 100, 10000.0, "inpatient")]
        res = group_episodes(claims, DEF)
        self.assertTrue(res.headline)
        self.assertEqual(res.to_dict()["citation_key"], "EP1")


if __name__ == "__main__":
    unittest.main()
