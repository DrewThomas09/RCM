"""Tests for the added referral graph-structure metrics
(PageRank, Brandes betweenness, label-propagation communities)."""
from __future__ import annotations

import unittest

from rcm_mc.referral import (
    ReferralGraph,
    betweenness_centrality,
    detect_communities,
    pagerank,
)


def _star_into_hub():
    g = ReferralGraph()
    for i in range(5):
        g.add_edge(f"pcp{i}", "H", 10.0)
    return g


class PageRankTests(unittest.TestCase):

    def test_hub_ranks_highest(self):
        pr = pagerank(_star_into_hub())
        self.assertEqual(max(pr, key=pr.get), "H")

    def test_sums_to_one(self):
        pr = pagerank(_star_into_hub())
        self.assertAlmostEqual(sum(pr.values()), 1.0, places=5)

    def test_influence_beats_raw_indegree(self):
        # Both X and Y receive weight 10. But X is fed by a hub that is
        # itself heavily fed; Y by a leaf. X should outrank Y on PageRank.
        g = ReferralGraph()
        g.add_edge("a", "hubfeeder", 100.0)
        g.add_edge("b", "hubfeeder", 100.0)
        g.add_edge("hubfeeder", "X", 10.0)
        g.add_edge("leaf", "Y", 10.0)
        pr = pagerank(g)
        self.assertGreater(pr["X"], pr["Y"])

    def test_empty(self):
        self.assertEqual(pagerank(ReferralGraph()), {})


class BetweennessTests(unittest.TestCase):

    def test_broker_scores_highest(self):
        g = ReferralGraph()
        g.add_edge("A", "B", 1.0)
        g.add_edge("B", "C", 1.0)
        bet = betweenness_centrality(g)
        self.assertGreater(bet["B"], bet["A"])
        self.assertGreater(bet["B"], bet["C"])

    def test_star_hub_no_betweenness(self):
        # In an into-hub star there are no paths *through* any node.
        bet = betweenness_centrality(_star_into_hub())
        self.assertAlmostEqual(bet["H"], 0.0)

    def test_empty(self):
        self.assertEqual(betweenness_centrality(ReferralGraph()), {})


class CommunityTests(unittest.TestCase):

    def test_separates_disconnected_clusters(self):
        g = ReferralGraph()
        g.add_edge("a1", "a2", 5.0)
        g.add_edge("a2", "a1", 5.0)
        g.add_edge("b1", "b2", 5.0)
        g.add_edge("b2", "b1", 5.0)
        comm = detect_communities(g)
        self.assertEqual(comm["a1"], comm["a2"])
        self.assertEqual(comm["b1"], comm["b2"])
        self.assertNotEqual(comm["a1"], comm["b1"])

    def test_deterministic(self):
        g = ReferralGraph()
        for i in range(8):
            g.add_edge(f"n{i}", f"n{i+1}", 1.0)
        self.assertEqual(detect_communities(g, seed=7),
                         detect_communities(g, seed=7))

    def test_empty(self):
        self.assertEqual(detect_communities(ReferralGraph()), {})


if __name__ == "__main__":
    unittest.main()
