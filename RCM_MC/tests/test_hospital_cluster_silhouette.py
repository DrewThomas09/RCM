"""Cluster-quality silhouette for hospital archetypes.

The k-means archetypes were presented with no measure of how well the
clusters actually separate — soft, overlapping groupings looked as
definitive as clean ones. This adds a scalable simplified (centroid-based)
silhouette as an honest quality signal, surfaced on /ml-insights so a
partner can tell a sharp archetype boundary from a fuzzy one. Additive
only: it never changes k, labels, or assignments.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from rcm_mc.ml.hospital_clustering import (
    ClusterProfile,
    _simplified_silhouette,
    cluster_hospitals,
    overall_silhouette,
    silhouette_quality_label,
)


class SimplifiedSilhouetteTests(unittest.TestCase):
    def test_well_separated_blobs_score_high(self):
        rng = np.random.default_rng(0)
        X = np.vstack([rng.normal(0, 0.3, (40, 2)),
                       rng.normal(8, 0.3, (40, 2)),
                       rng.normal([0, 8], 0.3, (40, 2))])
        cents = np.array([[0., 0.], [8., 0.], [0., 8.]])
        labels = np.array([0] * 40 + [1] * 40 + [2] * 40)
        s = _simplified_silhouette(X, cents, labels)
        self.assertGreater(float(s.mean()), 0.5)
        self.assertTrue(np.all(s >= -1.0) and np.all(s <= 1.0))

    def test_overlapping_scores_low(self):
        rng = np.random.default_rng(1)
        X = rng.normal(0, 3.0, (150, 2))
        labels = rng.integers(0, 3, 150)
        cents = np.array([X[labels == j].mean(0) for j in range(3)])
        self.assertLess(float(_simplified_silhouette(X, cents, labels).mean()), 0.25)

    def test_single_cluster_is_safe_zero(self):
        X = np.random.default_rng(2).normal(size=(20, 3))
        s = _simplified_silhouette(X, X[:1].mean(0, keepdims=True), np.zeros(20, int))
        self.assertEqual(float(s.sum()), 0.0)

    def test_empty_is_safe(self):
        self.assertEqual(
            _simplified_silhouette(np.zeros((0, 2)), np.zeros((2, 2)), np.array([], int)).shape,
            (0,))


class QualityLabelTests(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(silhouette_quality_label(0.7), "strong separation")
        self.assertEqual(silhouette_quality_label(0.3), "moderate separation")
        self.assertEqual(silhouette_quality_label(0.15), "weak separation")
        self.assertIn("indicative", silhouette_quality_label(0.0))


class OverallSilhouetteTests(unittest.TestCase):
    def test_size_weighted_mean(self):
        profiles = [
            ClusterProfile(0, "a", "A", "", 90, {}, {}, [], "", silhouette=0.8),
            ClusterProfile(1, "b", "B", "", 10, {}, {}, [], "", silhouette=0.0),
        ]
        # 0.8*90/100 = 0.72
        self.assertAlmostEqual(overall_silhouette(profiles), 0.72)

    def test_empty_is_zero(self):
        self.assertEqual(overall_silhouette([]), 0.0)


class ClusterHospitalsAttachesSilhouetteTests(unittest.TestCase):
    def _hcris(self, n=140):
        # Two genuinely separate hospital groups so clustering is meaningful.
        rng = np.random.default_rng(7)
        small = pd.DataFrame({
            "ccn": [f"S{i}" for i in range(n // 2)],
            "name": ["small"] * (n // 2), "state": ["TX"] * (n // 2),
            "beds": rng.normal(40, 5, n // 2),
            "net_patient_revenue": rng.normal(3e7, 3e6, n // 2),
            "operating_margin": rng.normal(-0.05, 0.02, n // 2),
            "medicare_day_pct": rng.normal(0.55, 0.03, n // 2),
            "medicaid_day_pct": rng.normal(0.20, 0.02, n // 2),
            "occupancy_rate": rng.normal(0.35, 0.03, n // 2),
            "revenue_per_bed": rng.normal(7.5e5, 5e4, n // 2),
        })
        large = pd.DataFrame({
            "ccn": [f"L{i}" for i in range(n // 2)],
            "name": ["large"] * (n // 2), "state": ["CA"] * (n // 2),
            "beds": rng.normal(400, 30, n // 2),
            "net_patient_revenue": rng.normal(6e8, 5e7, n // 2),
            "operating_margin": rng.normal(0.10, 0.02, n // 2),
            "medicare_day_pct": rng.normal(0.40, 0.03, n // 2),
            "medicaid_day_pct": rng.normal(0.12, 0.02, n // 2),
            "occupancy_rate": rng.normal(0.70, 0.03, n // 2),
            "revenue_per_bed": rng.normal(1.5e6, 1e5, n // 2),
        })
        return pd.concat([small, large], ignore_index=True)

    def test_profiles_carry_silhouette_and_separated_groups_score_well(self):
        df, profiles = cluster_hospitals(self._hcris(), k=2)
        self.assertTrue(profiles)
        for p in profiles:
            self.assertTrue(-1.0 <= p.silhouette <= 1.0)
        # Two clearly distinct hospital populations → positive overall silhouette.
        self.assertGreater(overall_silhouette(profiles), 0.2)

    def test_silhouette_does_not_change_assignments(self):
        # Additive contract: clustering output (ids + counts) is unchanged by
        # the silhouette computation (it only reads the existing assignment).
        df, profiles = cluster_hospitals(self._hcris(), k=2)
        self.assertEqual(sum(p.n_hospitals for p in profiles),
                         int(df["cluster_id"].notna().sum()))


if __name__ == "__main__":
    unittest.main()
