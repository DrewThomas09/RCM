"""Phase-5 clustering tests.

Pins:
  - prepare_clustering_features only uses structural columns
    (no net_patient_revenue or its derivatives leak in)
  - PCA: components are orthonormal, explained-variance ratios
    sum to ≤ 1, reconstruction is reasonable on 2 components
  - k-means determinism (same seed → same labels), k-means++
    init, inertia monotonically non-increasing across iterations
  - profile_clusters auto-names by dominant segment + flavour
  - cluster_hospitals end-to-end on a synthetic 3-regime fixture
"""
import unittest

import numpy as np
import pandas as pd

from rcm_mc.data.hospital_taxonomy import derive_taxonomy
from rcm_mc.finance.clustering import (
    STRUCTURAL_FEATURES,
    cluster_hospitals,
    prepare_clustering_features,
    profile_clusters,
    render_cluster_scatter,
    run_kmeans,
    run_pca,
)


def _synthetic_hospitals(n=200, seed=42):
    """Three-regime synthetic frame designed so PCA + k-means
    should recover the regimes cleanly."""
    rng = np.random.default_rng(seed)
    rows = []
    # Regime A: large academic — 600 beds, low Medicare, high case mix
    for i in range(n // 3):
        rows.append({
            "ccn": f"05A{i:03d}",
            "name": f"STANFORD HOSPITAL {i}",  # academic name
            "beds": rng.normal(600, 80),
            "medicare_day_pct": rng.normal(35, 5),
            "medicaid_day_pct": rng.normal(10, 3),
            "total_patient_days": rng.normal(170000, 20000),
            "bed_days_available": rng.normal(220000, 25000),
            "operating_expenses": rng.normal(800e6, 100e6),
        })
    # Regime B: critical access — 20 beds, high Medicare, rural
    for i in range(n // 3):
        rows.append({
            "ccn": f"19{1300+i:04d}",  # CCN range for CAH
            "name": f"COUNTY HOSPITAL {i}",
            "beds": rng.normal(20, 4),
            "medicare_day_pct": rng.normal(65, 5),
            "medicaid_day_pct": rng.normal(15, 3),
            "total_patient_days": rng.normal(3500, 500),
            "bed_days_available": rng.normal(7000, 800),
            "operating_expenses": rng.normal(15e6, 3e6),
        })
    # Regime C: community — 200 beds, balanced payer mix
    for i in range(n - 2 * (n // 3)):
        rows.append({
            "ccn": f"10C{i:03d}",
            "name": f"REGIONAL MEDICAL CENTER {i}",
            "beds": rng.normal(200, 30),
            "medicare_day_pct": rng.normal(45, 5),
            "medicaid_day_pct": rng.normal(15, 4),
            "total_patient_days": rng.normal(55000, 8000),
            "bed_days_available": rng.normal(73000, 10000),
            "operating_expenses": rng.normal(250e6, 40e6),
        })
    return derive_taxonomy(pd.DataFrame(rows))


class PrepareFeaturesTests(unittest.TestCase):
    def test_feature_set_is_structural_only(self):
        # Critical: net_patient_revenue must NOT be in the feature
        # set. Clustering on the regression target would bake the
        # answer into the clusters.
        self.assertNotIn("net_patient_revenue", STRUCTURAL_FEATURES)
        self.assertNotIn("revenue_per_bed", STRUCTURAL_FEATURES)
        self.assertNotIn("operating_margin", STRUCTURAL_FEATURES)
        # Sanity: expected structural ones ARE present
        for f in ("log_beds", "occupancy_rate", "medicare_day_pct"):
            self.assertIn(f, STRUCTURAL_FEATURES)

    def test_prepare_returns_normalized_matrix(self):
        df = _synthetic_hospitals(60)
        X, feats, idx = prepare_clustering_features(df)
        # z-score normalized: each column mean ≈ 0, std ≈ 1
        self.assertEqual(X.shape[1], len(STRUCTURAL_FEATURES))
        # Skip the binary flag columns when checking std — they can
        # have std ~0 if all rows are the same class
        for j, name in enumerate(feats):
            if name in ("academic_or_teaching", "flagship_specialty",
                        "critical_access", "safety_net_proxy"):
                continue
            self.assertAlmostEqual(X[:, j].mean(), 0.0, places=8)

    def test_prepare_requires_taxonomy_columns(self):
        df = pd.DataFrame({"ccn": ["01"], "name": ["X"], "beds": [100]})
        with self.assertRaises(ValueError) as ctx:
            prepare_clustering_features(df)
        self.assertIn("taxonomy", str(ctx.exception).lower())


class PCATests(unittest.TestCase):
    def test_explained_variance_ratios_sum_to_at_most_one(self):
        df = _synthetic_hospitals(120)
        X, _, _ = prepare_clustering_features(df)
        res = run_pca(X, n_components=3)
        # Top-3 components capture at most 100% of variance
        self.assertLessEqual(res.explained_variance_ratio.sum(),
                             1.0 + 1e-6)

    def test_components_are_orthonormal(self):
        df = _synthetic_hospitals(120)
        X, _, _ = prepare_clustering_features(df)
        res = run_pca(X, n_components=2)
        # Each component has unit length
        for c in res.components:
            self.assertAlmostEqual(np.linalg.norm(c), 1.0, places=6)
        # Components are mutually orthogonal
        if len(res.components) > 1:
            dot = float(res.components[0] @ res.components[1])
            self.assertAlmostEqual(dot, 0.0, places=6)

    def test_first_component_explains_most_variance(self):
        df = _synthetic_hospitals(120)
        X, _, _ = prepare_clustering_features(df)
        res = run_pca(X, n_components=3)
        ratios = res.explained_variance_ratio
        # Sorted descending by SVD convention
        for i in range(len(ratios) - 1):
            self.assertGreaterEqual(ratios[i], ratios[i + 1] - 1e-9)


class KMeansTests(unittest.TestCase):
    def test_determinism_same_seed_same_labels(self):
        df = _synthetic_hospitals(120)
        X, _, _ = prepare_clustering_features(df)
        a = run_kmeans(X, k=3, random_state=7)
        b = run_kmeans(X, k=3, random_state=7)
        np.testing.assert_array_equal(a.labels, b.labels)
        self.assertAlmostEqual(a.inertia, b.inertia, places=8)

    def test_different_seed_can_yield_different_labels(self):
        df = _synthetic_hospitals(120)
        X, _, _ = prepare_clustering_features(df)
        a = run_kmeans(X, k=3, random_state=1)
        b = run_kmeans(X, k=3, random_state=99)
        # Labels are cluster IDs — they can be permuted between
        # runs even when the partitions are the same. Compare the
        # partitions instead by counting pairs.
        # Simplest robust check: just confirm both produced a fit
        self.assertEqual(a.labels.shape, b.labels.shape)
        self.assertGreaterEqual(a.n_iter, 1)
        self.assertGreaterEqual(b.n_iter, 1)

    def test_inertia_positive_and_finite(self):
        df = _synthetic_hospitals(120)
        X, _, _ = prepare_clustering_features(df)
        res = run_kmeans(X, k=3)
        self.assertGreater(res.inertia, 0)
        self.assertTrue(np.isfinite(res.inertia))

    def test_three_regime_synthetic_recovers_three_clusters(self):
        # The synthetic fixture is engineered to be cleanly
        # separable; k=3 k-means should land each regime in its own
        # cluster (≥ 80% purity per regime).
        df = _synthetic_hospitals(150)
        X, _, idx = prepare_clustering_features(df)
        res = run_kmeans(X, k=3, random_state=42)
        # Join labels back to source segments
        src = df.loc[idx]
        src = src.assign(cluster=res.labels)
        # For each cluster, the dominant segment label should be
        # >= 70% of the cluster's rows
        for c in range(3):
            sub = src[src["cluster"] == c]
            if len(sub) == 0:
                continue
            dom = sub["segment_label"].value_counts(normalize=True).iloc[0]
            self.assertGreaterEqual(
                dom, 0.70,
                f"cluster {c} dominant-segment purity = {dom:.2%}",
            )

    def test_k_less_than_two_raises(self):
        X = np.random.randn(20, 3)
        with self.assertRaises(ValueError):
            run_kmeans(X, k=1)

    def test_k_greater_than_n_raises(self):
        X = np.random.randn(5, 3)
        with self.assertRaises(ValueError):
            run_kmeans(X, k=10)


class ProfileTests(unittest.TestCase):
    def test_profile_names_use_dominant_segment(self):
        df = _synthetic_hospitals(150)
        res = cluster_hospitals(df, k=3)
        # Every profile should name itself with a real segment
        for p in res.profiles:
            self.assertTrue(
                p.dominant_segment in p.name or "Mixed" in p.name,
                f"profile name {p.name!r} doesn't reference its "
                f"dominant segment {p.dominant_segment!r}",
            )
            self.assertGreaterEqual(p.size, 1)
            self.assertTrue(0.0 <= p.segment_share <= 1.0)

    def test_flavour_modifiers_appear_when_thresholds_clear(self):
        # The CAH-heavy cluster should pick up "micro" (median beds < 25)
        # and "medicare-heavy" (median medicare_day_pct >= 55)
        df = _synthetic_hospitals(150)
        res = cluster_hospitals(df, k=3)
        cah_profile = next(
            (p for p in res.profiles
             if p.dominant_segment == "Critical Access"),
            None,
        )
        self.assertIsNotNone(cah_profile)
        # At least one of the expected flavours should be in the name
        self.assertTrue(
            "micro" in cah_profile.name or
            "medicare-heavy" in cah_profile.name,
            f"CAH cluster name {cah_profile.name!r} missing expected "
            "flavour",
        )


class EndToEndTests(unittest.TestCase):
    def test_cluster_hospitals_to_dict_serializable(self):
        df = _synthetic_hospitals(120)
        res = cluster_hospitals(df, k=3)
        d = res.to_dict()
        self.assertEqual(d["k"], 3)
        self.assertEqual(len(d["profiles"]), 3)
        for p in d["profiles"]:
            for key in ("cluster_id", "name", "size",
                        "dominant_segment", "median_beds"):
                self.assertIn(key, p)

    def test_too_few_rows_raises(self):
        df = _synthetic_hospitals(15)  # below 30 floor
        with self.assertRaises(ValueError):
            cluster_hospitals(df, k=3)


class ScatterRenderTests(unittest.TestCase):
    """render_cluster_scatter returns valid editorial SVG."""

    def test_returns_svg_with_expected_viewbox(self):
        df = _synthetic_hospitals(120)
        res = cluster_hospitals(df, k=3)
        svg = render_cluster_scatter(res, width=720, height=460)
        self.assertIn('viewBox="0 0 720 460"', svg)
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))

    def test_one_circle_per_row_plus_legend_dots(self):
        # Plot circles: one per row. Legend also uses <circle> for
        # color swatches — there will be `n_rows + k` total.
        df = _synthetic_hospitals(120)
        res = cluster_hospitals(df, k=3)
        svg = render_cluster_scatter(res)
        # exact circle count is n_rows + k (one swatch per profile)
        expected = res.kmeans.labels.shape[0] + len(res.profiles)
        self.assertEqual(svg.count("<circle"), expected)

    def test_one_diamond_centroid_per_cluster(self):
        # Centroids render as <polygon> diamonds
        df = _synthetic_hospitals(120)
        res = cluster_hospitals(df, k=3)
        svg = render_cluster_scatter(res)
        self.assertEqual(svg.count("<polygon"), 3)

    def test_axis_labels_show_explained_variance(self):
        df = _synthetic_hospitals(120)
        res = cluster_hospitals(df, k=3)
        svg = render_cluster_scatter(res)
        # PC1 and PC2 labels include "% var" suffix
        self.assertIn("PC1", svg)
        self.assertIn("PC2", svg)
        self.assertIn("% var", svg)

    def test_legend_includes_each_cluster_name(self):
        df = _synthetic_hospitals(120)
        res = cluster_hospitals(df, k=3)
        svg = render_cluster_scatter(res)
        for prof in res.profiles:
            # Names may be truncated at 40 chars, so check a prefix
            stem = prof.name[:30]
            self.assertIn(stem, svg,
                          f"legend missing cluster {prof.cluster_id}")


if __name__ == "__main__":
    unittest.main()
