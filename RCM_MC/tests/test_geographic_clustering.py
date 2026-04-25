"""Tests for geographic clustering + hotspot detection."""
from __future__ import annotations

import unittest

import numpy as np


def _hospitals(state, n, *, denial=0.10, dso=45,
               collect=0.96, margin=0.04, seed=7):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        out.append({
            "state": state,
            "denial_rate": denial + rng.normal(0, 0.005),
            "days_in_ar": dso + rng.normal(0, 1),
            "collection_rate":
                collect + rng.normal(0, 0.003),
            "operating_margin":
                margin + rng.normal(0, 0.005),
        })
    return out


class TestAggregation(unittest.TestCase):
    def test_basic_state_aggregation(self):
        from rcm_mc.ml.geographic_clustering import (
            aggregate_by_region,
        )
        hospitals = (
            _hospitals("GA", 5)
            + _hospitals("FL", 8))
        aggs = aggregate_by_region(hospitals)
        self.assertEqual(len(aggs), 2)
        states = {a.region for a in aggs}
        self.assertEqual(states, {"GA", "FL"})
        # All four canonical features present
        for a in aggs:
            for f in ["denial_rate", "days_in_ar",
                      "collection_rate",
                      "operating_margin"]:
                self.assertIn(f, a.metrics)

    def test_min_hospitals_filter(self):
        from rcm_mc.ml.geographic_clustering import (
            aggregate_by_region,
        )
        hospitals = (
            _hospitals("GA", 5)
            + _hospitals("AK", 2))
        aggs = aggregate_by_region(
            hospitals, min_hospitals=3)
        states = {a.region for a in aggs}
        self.assertNotIn("AK", states)

    def test_empty_region_skipped(self):
        from rcm_mc.ml.geographic_clustering import (
            aggregate_by_region,
        )
        hospitals = (
            _hospitals("GA", 5)
            + [{"state": "", "denial_rate": 0.10}])
        aggs = aggregate_by_region(hospitals)
        states = {a.region for a in aggs}
        self.assertEqual(states, {"GA"})


class TestKmeans(unittest.TestCase):
    def test_clusters_separate_groups(self):
        from rcm_mc.ml.geographic_clustering import _kmeans
        rng = np.random.default_rng(7)
        # Two well-separated clusters
        c1 = rng.normal([-3, -3], 0.3, size=(20, 2))
        c2 = rng.normal([3, 3], 0.3, size=(20, 2))
        X = np.concatenate([c1, c2])
        labels, centroids = _kmeans(X, k=2)
        # First 20 should share a label, last 20 share another
        self.assertEqual(len(set(labels[:20])), 1)
        self.assertEqual(len(set(labels[20:])), 1)
        self.assertNotEqual(labels[0], labels[20])

    def test_k_greater_than_n(self):
        from rcm_mc.ml.geographic_clustering import _kmeans
        X = np.array([[1.0, 2.0], [3.0, 4.0]])
        labels, centroids = _kmeans(X, k=5)
        # Each point its own cluster
        self.assertEqual(len(labels), 2)


class TestHotspots(unittest.TestCase):
    def test_underperforming_state_flagged(self):
        from rcm_mc.ml.geographic_clustering import (
            aggregate_by_region, score_hotspots,
        )
        # 3 'normal' states + 1 with much worse RCM
        hospitals = (
            _hospitals("GA", 5, denial=0.08,
                       dso=42, collect=0.97,
                       margin=0.05, seed=1)
            + _hospitals("FL", 5, denial=0.09,
                         dso=44, collect=0.96,
                         margin=0.04, seed=2)
            + _hospitals("TX", 5, denial=0.10,
                         dso=46, collect=0.95,
                         margin=0.03, seed=3)
            + _hospitals("MS", 5, denial=0.20,
                         dso=70, collect=0.85,
                         margin=-0.05, seed=4))
        aggs = aggregate_by_region(hospitals)
        hotspots = score_hotspots(aggs)
        # MS should be the worst (composite_z highest)
        self.assertEqual(hotspots[0].region, "MS")
        self.assertGreater(hotspots[0].composite_z, 1.0)
        self.assertTrue(hotspots[0].is_hotspot)
        # GA should be the best
        self.assertEqual(hotspots[-1].region, "GA")
        self.assertLess(hotspots[-1].composite_z, 0)

    def test_z_score_signs_aligned(self):
        from rcm_mc.ml.geographic_clustering import (
            aggregate_by_region, score_hotspots,
        )
        hospitals = (
            _hospitals("A", 5, denial=0.05, dso=30,
                       collect=0.99, margin=0.10, seed=1)
            + _hospitals("B", 5, denial=0.20, dso=70,
                         collect=0.85, margin=-0.05, seed=2))
        aggs = aggregate_by_region(hospitals)
        hotspots = score_hotspots(aggs)
        # B's denial_rate z-score should be positive (worse)
        b = next(h for h in hotspots if h.region == "B")
        self.assertGreater(b.metric_z_scores["denial_rate"], 0)
        # B's collection_rate z-score should be positive too
        # (lower collection = worse, sign-flipped)
        self.assertGreater(
            b.metric_z_scores["collection_rate"], 0)

    def test_empty_input(self):
        from rcm_mc.ml.geographic_clustering import (
            score_hotspots,
        )
        self.assertEqual(score_hotspots([]), [])

    def test_rank_assigned(self):
        from rcm_mc.ml.geographic_clustering import (
            aggregate_by_region, score_hotspots,
        )
        hospitals = (
            _hospitals("A", 5, seed=1)
            + _hospitals("B", 5, seed=2)
            + _hospitals("C", 5, seed=3))
        aggs = aggregate_by_region(hospitals)
        hotspots = score_hotspots(aggs)
        # Ranks should be 1, 2, 3
        ranks = [h.rank for h in hotspots]
        self.assertEqual(ranks, [1, 2, 3])


class TestClustering(unittest.TestCase):
    def test_basic_clustering(self):
        from rcm_mc.ml.geographic_clustering import (
            aggregate_by_region, cluster_regions,
        )
        hospitals = (
            _hospitals("A", 5, denial=0.05,
                       margin=0.10, seed=1)
            + _hospitals("B", 5, denial=0.06,
                         margin=0.09, seed=2)
            + _hospitals("C", 5, denial=0.20,
                         margin=-0.05, seed=3)
            + _hospitals("D", 5, denial=0.18,
                         margin=-0.04, seed=4))
        aggs = aggregate_by_region(hospitals)
        clusters = cluster_regions(aggs, n_clusters=2)
        self.assertEqual(len(clusters), 2)
        # Each cluster has a label
        for c in clusters:
            self.assertNotEqual(c.cluster_label, "")
        # All regions assigned
        all_regions = set()
        for c in clusters:
            all_regions.update(c.regions)
        self.assertEqual(
            all_regions, {"A", "B", "C", "D"})
        # Cluster labels ordered: best to worst
        scores = [c.mean_hotspot_score for c in clusters]
        self.assertEqual(scores, sorted(scores))

    def test_cluster_centroid_unscaled(self):
        from rcm_mc.ml.geographic_clustering import (
            aggregate_by_region, cluster_regions,
        )
        hospitals = _hospitals("A", 5, denial=0.10,
                               seed=1) + _hospitals(
            "B", 5, denial=0.20, seed=2)
        aggs = aggregate_by_region(hospitals)
        clusters = cluster_regions(aggs, n_clusters=2)
        # Centroids should be in original scale (denial in
        # 0..1 range)
        for c in clusters:
            denial = c.centroid_metrics["denial_rate"]
            self.assertGreater(denial, 0)
            self.assertLess(denial, 0.5)


class TestHuntingGroundReport(unittest.TestCase):
    def test_full_report(self):
        from rcm_mc.ml.geographic_clustering import (
            find_hunting_grounds,
        )
        hospitals = (
            _hospitals("GA", 8, denial=0.07,
                       dso=40, collect=0.97,
                       margin=0.06, seed=1)
            + _hospitals("FL", 8, denial=0.09,
                         dso=44, collect=0.96,
                         margin=0.04, seed=2)
            + _hospitals("TX", 8, denial=0.11,
                         dso=48, collect=0.95,
                         margin=0.03, seed=3)
            + _hospitals("MS", 8, denial=0.18,
                         dso=68, collect=0.86,
                         margin=-0.04, seed=4))
        report = find_hunting_grounds(
            hospitals, n_clusters=2)
        self.assertEqual(report.region_type, "state")
        self.assertEqual(report.n_regions, 4)
        self.assertEqual(report.n_hospitals_total, 32)
        # MS should be flagged as hotspot
        self.assertGreater(
            sum(1 for h in report.hotspots
                if h.is_hotspot), 0)
        ms = next(h for h in report.hotspots
                  if h.region == "MS")
        self.assertTrue(ms.is_hotspot)
        # Cluster labels attached to hotspots
        for h in report.hotspots:
            self.assertIsNotNone(h.cluster_label)
        # Notes mention hotspot count
        self.assertTrue(any(
            "hotspot" in n for n in report.notes))

    def test_no_regions_meet_floor(self):
        from rcm_mc.ml.geographic_clustering import (
            find_hunting_grounds,
        )
        # Every state has only 1 hospital
        hospitals = (
            _hospitals("GA", 1)
            + _hospitals("FL", 1))
        report = find_hunting_grounds(hospitals)
        self.assertEqual(report.n_regions, 0)
        self.assertTrue(any(
            "min_hospitals_per_region" in n
            for n in report.notes))

    def test_hotspots_sorted_worst_first(self):
        from rcm_mc.ml.geographic_clustering import (
            find_hunting_grounds,
        )
        # Use clearly differentiated metrics so noise on the
        # constant-default features doesn't dominate.
        hospitals = (
            _hospitals("GA", 5, denial=0.05, dso=35,
                       collect=0.98, margin=0.08, seed=1)
            + _hospitals("FL", 5, denial=0.10, dso=45,
                         collect=0.95, margin=0.04,
                         seed=2)
            + _hospitals("MS", 5, denial=0.20, dso=70,
                         collect=0.85, margin=-0.05,
                         seed=3))
        report = find_hunting_grounds(
            hospitals, n_clusters=2)
        # Hotspots sorted: MS first (worst), GA last (best)
        self.assertEqual(
            report.hotspots[0].region, "MS")
        self.assertEqual(
            report.hotspots[-1].region, "GA")


if __name__ == "__main__":
    unittest.main()
